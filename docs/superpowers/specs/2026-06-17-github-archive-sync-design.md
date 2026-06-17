# 采集后自动归档到 archive 分支 — 设计文档

- 日期:2026-06-17
- 状态:已确认,待实现
- 关联模块:`main.py`、`content_store.py`、`config.py`、新增 `archive_sync.py`

## 1. 背景与动机

当前采集流程把归档数据落在服务器磁盘 `output/<source>/<YYYY-MM-DD>/<batch>.json`,Redis 作为 3 天热缓存。磁盘归档是事实源,但只存在于**单一服务器**上,没有异地备份,也没有可追溯、可回看的版本化历史。

本设计在采集流程末尾新增一步:把 `output/` 镜像到当前仓库的 `archive/` 目录,经 git worktree 提交并推送到 `archive` 分支。从而同时获得:

- **异地备份**:数据进入 GitHub,服务器磁盘损坏不丢历史。
- **可追溯历史**:每次采集一个 commit,能回看任意时点的快照。
- **源码与数据解耦**:数据全部隔离在 `archive` 分支,`master` 保持纯源码历史,不被数据提交污染。

## 2. 目标与非目标

### 目标
- 采集流程跑完后,自动把 `output/` 同步到 `archive/` 并推送到 `archive` 分支。
- 触发方式:跟随采集(复用现有 scheduler,一天 3 次),不新增独立定时器。
- master 工作区不受任何影响(不切换分支、不改动运行中的代码)。
- 归档步骤失败不影响采集本身、邮件发送和 API 服务。

### 非目标
- 不改造现有 `output/` 写盘与 Redis 逻辑(`content_store.py` 不变)。
- 不做数据压缩、git LFS 或历史清理(数据量小,日级累积,YAGNI)。
- 不做多实例并发推送的强一致性方案(单 worker 单实例场景,push 冲突用 rebase 重试兜底)。
- 不把归档功能暴露为 API 接口。

## 3. 总体设计

新增独立模块 `archive_sync.py`,在 `main.py:run_spider()` 的 `persist_source_snapshots` 之后调用。利用 **git worktree** 把 `archive` 分支检出到一个独立目录 `.archive-worktree/`,在该目录内完成同步、提交、推送,主工作区(master)全程不切换分支。

核心不变量:
- `master` 工作区永远不被 archive 流程切换分支或修改文件。
- `output/` 仍是运行时事实源;`archive/` 是它的 git 化镜像(只存在于 worktree 与 `archive` 分支)。
- 归档步骤是「尽力而为」:失败只告警,不中断主流程。

## 4. 详细设计

### 4.1 组件

| 组件 | 职责 |
|---|---|
| `archive_sync.py`(新增) | 核心模块。对外暴露 `sync_archive_to_git(item_count=None)` |
| `config.py`(改) | 新增归档相关环境变量 |
| `main.py`(改) | `run_spider()` 在 `persist_source_snapshots` 成功后调用 sync,独立 try/except |
| `.gitignore`(改) | 加入 `.archive-worktree/` |
| `tests/test_archive_sync.py`(新增) | 本地临时 git 仓库 fixture 单测 |

`archive_sync.py` 内部函数划分(单一职责,便于测试):

- `sync_archive_to_git(item_count=None)`:总入口,编排以下步骤,任何异常吞掉并 log。
- `_ensure_worktree(worktree_path, branch, remote)`:确保 worktree 与分支存在(首次创建),返回 worktree 路径。
- `_sync_output(output_dir, archive_dir)`:镜像 `output/` 到 `archive/`(rsync 优先,shutil 降级)。
- `_commit_and_push(worktree_path, branch, remote, item_count)`:在 worktree 内 `git add -A`、有变更才 commit、push。

### 4.2 数据流

```
run_spider()
  ├─ ...(现有采集、AI 摘要)...
  ├─ write_content_json()        → output/latest.json
  ├─ persist_source_snapshots()  → output/<source>/<date>/<batch>.json + Redis
  └─ try: sync_archive_to_git(item_count=len(content_items))   ← 新增
       except Exception: logger.warning(...)                   ← 不影响返回值
```

`sync_archive_to_git` 内部:

```
ensure .archive-worktree/ 存在
  ├─ 不存在 → git worktree add .archive-worktree -b archive <base>
  └─ 存在  → 若 remote 已有 archive 分支: git -C .archive-worktree pull --rebase
rsync -a --delete output/ → .archive-worktree/archive/
cd .archive-worktree
git add -A
git diff --cached --quiet? → 是:跳过 commit(空变更)
                            → 否:git commit -m "archive: <YYYY-MM-DD HH:MM> (<N> items)"
git push origin archive
  └─ 失败 → git pull --rebase origin archive → 重试 push 一次 → 仍失败则 log 跳过
```

### 4.3 配置项(写进 `config.py`,均有默认值)

| 变量 | 默认 | 说明 |
|---|---|---|
| `ARCHIVE_GIT_ENABLED` | `false` | 总开关。显式开启,避免开发环境误推 |
| `ARCHIVE_GIT_BRANCH` | `archive` | 归档分支名 |
| `ARCHIVE_GIT_WORKTREE` | `.archive-worktree` | worktree 检出目录(相对仓库根) |
| `ARCHIVE_GIT_DIR` | `archive` | worktree 内承载归档的子目录名 |
| `ARCHIVE_GIT_REMOTE` | `origin` | 推送目标 remote |

`ARCHIVE_GIT_ENABLED` 用现有 `_get_bool_env()` 读取。

### 4.4 worktree 初始化与生命周期

- **首次创建**:仓库根执行 `git worktree add <worktree> -b <branch> <base>`。
  - `<base>` 优先 `origin/master`,失败回退本地 `master`,再回退 `HEAD`。
  - 若 `<branch>` 在 remote 已存在但本地无 worktree:改为 `git worktree add <worktree> <branch>`,随后 `git -C <worktree> pull --rebase <remote> <branch>` 同步远端历史。
- **复用**:worktree 目录已存在且为有效 worktree,直接使用。
- **首次在 `<worktree>/<archive_dir>/` 放置 `README.md`**:说明本分支用途、目录结构、由谁生成、生成频率,便于他人浏览。
- `.archive-worktree/` 加入 `.gitignore`,主工作区不跟踪它。

### 4.5 同步机制

- **首选 rsync**:`rsync -a --delete <output>/ <archive>/`。`output/` 是累积归档、永不删除历史,因此 `--delete` 安全(仅让 `archive/` 与 `output/` 保持镜像一致;`latest.json` 每次覆盖,各 source 按日期批次累积)。
- **降级 shutil**:运行环境无 rsync(如精简容器)时,用 Python `shutil` 实现等价镜像——先删 `archive/` 再 `shutil.copytree(output, archive)`。通过 `shutil.which("rsync")` 探测决定走哪条路径。

### 4.6 commit 与 push 策略

- **commit 粒度**:每次采集一个 commit。
- **跳过空提交**:`git add -A` 后用 `git diff --cached --quiet` 判断,无变更则不 commit(避免无意义空提交)。
- **commit message**:`archive: <YYYY-MM-DD HH:MM> (<N> items)`,`N` 来自传入的 `item_count`,缺省时省略条数。
- **push**:`git push <remote> <branch>`。失败时 `git pull --rebase <remote> <branch>` 后重试一次;仍失败则 `logger.warning` 跳过,等下次采集。

### 4.7 错误处理与降级

- `sync_archive_to_git` 整体包在 try/except,任何异常只 `logger.warning`,**绝不向上抛出**。
- `main.py` 调用处再包一层 try/except 作为双保险,确保归档逻辑永远不影响 `run_spider` 返回值和后续邮件。
- 开关关闭(`ARCHIVE_GIT_ENABLED=false`):直接返回,仅 log 一行「归档推送已关闭」。

## 5. 文件变更清单

- 新增 `archive_sync.py`
- 新增 `tests/test_archive_sync.py`
- 修改 `config.py`:追加归档配置节
- 修改 `main.py`:`run_spider` 在 `persist_source_snapshots` 后调用 sync
- 修改 `.gitignore`:追加 `.archive-worktree/`
- (可选)修改 `AGENTS.md` / `README.md`:文档说明归档分支用途

## 6. 测试策略

仿现有 `tests/` 风格(`test_*.py`,`unittest` 或 `pytest` 均可,与现有一致)。用 `tempfile` 构造隔离环境,**不依赖真实 GitHub**:

- 用 `git init --bare` 建一个本地 bare repo 作为 remote。
- 用 `tempfile` 建工作仓库,`git remote add` 指向 bare repo。
- 构造 `output/` 内容(含 `latest.json` 与若干 source 归档),调用 `sync_archive_to_git`。
- 断言:
  1. 首次同步后 `archive` 分支存在,bare repo 收到 push。
  2. `<worktree>/archive/` 内容与 `output/` 一致。
  3. 新增文件后再调用,产生**新 commit**(commit 数 +1)。
  4. 无变更时再调用,**不产生空 commit**(commit 数不变)。
  5. `sync` 内部抛异常时被吞掉、不向上传播(可用 monkeypatch 制造 rsync/push 失败验证)。
  6. `ARCHIVE_GIT_ENABLED=false` 时直接跳过,不创建 worktree。

worktree 路径、remote 等通过环境变量注入测试值,避免污染真实仓库目录。

## 7. 前提条件(部署时确认)

- 运行环境具备对 `agently.top` 仓库的写权限(SSH key 已加入 GitHub 账号;当前 push remote 为 `git@ssh.github.com:yunlongwen/agently.top.git`)。
- 首次开启前确认本地仓库能 `git push origin`。
- 服务器装有 `rsync`(否则自动降级 shutil,功能等价)。
- 生产仍为单 worker uvicorn(归档同步非线程安全的多实例场景不在本期范围)。

## 8. 验收标准

- 开启 `ARCHIVE_GIT_ENABLED=true` 后,每次采集后 `archive` 分支多一个 commit,内容为本次 `output/` 镜像。
- master 分支提交历史不含任何数据 commit。
- archive 流程不改动 master 工作区的任何源码文件;主工作区仅多出被 gitignore 的 `.archive-worktree/`。
- 人为制造推送失败(如断网/无权限)时,采集流程仍正常完成、邮件正常发送,仅日志有 warning。
- 全部新增单测通过。

## 9. 风险与权衡

- **仓库体积长期增长**:每天约几百 KB,一年 ~100MB 级。当前可接受;若未来成为问题,再评估历史清理或迁移独立仓库(届时可平滑迁移,因为数据已在独立分支)。
- **master vs 独立分支**:已选独立分支,源码历史不被污染,代价是 `archive/` 不在 master 上直接可见(需切到 `archive` 分支或 GitHub 上浏览该分支)——符合设计目标。
- **rsync 依赖**:通过 shutil 降级消除硬依赖。
