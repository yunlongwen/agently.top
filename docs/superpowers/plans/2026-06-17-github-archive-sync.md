# 采集后归档到 archive 分支 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 采集流程跑完后,把 `output/` 镜像到 `archive/` 并经 git worktree 提交推送到当前仓库的 `archive` 分支,实现异地备份 + 可追溯历史,master 不受污染。

**Architecture:** 新增 `archive_sync.py`,在 `main.py:run_spider()` 末尾(`persist_source_snapshots` 之后)调用。用 git worktree 把 archive 分支检出到 `.archive-worktree/`,在 worktree 内完成 rsync 镜像 + commit + push,主工作区零干扰。归档步骤整体 try/except,失败只告警。

**Tech Stack:** Python 3.9+ 标准库(`subprocess`/`shutil`/`pathlib`)、git(worktree)、rsync(可选,降级 shutil)、`unittest`(项目测试框架)。

**对应 spec:** `docs/superpowers/specs/2026-06-17-github-archive-sync-design.md`

**测试运行约定(全计划统一):** 所有测试从项目根目录跑,用项目现有 unittest 模式:
```bash
python3 tests/test_archive_sync.py
```
(测试文件含 `sys.path.insert(0, ".")` 与 `unittest.main()`,可直接执行。)

**实现细化(相对 spec 4.4):** 说明文档以 **`ARCHIVE.md`** 置于 **worktree 根**(而非 `archive/` 子目录内,且避开 master 已有的 `README.md`),避免被 rsync `--delete` 镜像删除——更稳健,语义不变。

---

## 文件结构

| 文件 | 责任 | 动作 |
|---|---|---|
| `config.py` | 归档推送配置项 | 修改:追加配置节 |
| `archive_sync.py` | 归档核心逻辑(worktree/同步/提交/推送) | 新建 |
| `tests/test_archive_sync.py` | 归档模块单测 | 新建 |
| `main.py` | 采集主流程 | 修改:`run_spider` 末尾接入归档 |
| `.gitignore` | 忽略 worktree 目录 | 修改:追加一行 |
| `AGENTS.md` | 协作约定 | 修改:补归档分支说明 |

---

## Task 1: 添加归档配置项与 .gitignore

**Files:**
- Modify: `config.py`(在文件末尾追加)
- Modify: `.gitignore`(追加一行)

- [ ] **Step 1: 在 `config.py` 末尾追加归档配置节**

在 `config.py` 最后一行(`EMAIL_SEND_TIMES = ...`)之后追加:

```python

# =========================================================================
# 采集后归档推送配置(把 output/ 镜像推送到 archive 分支)
# =========================================================================

# 是否启用采集后归档推送。默认关闭,显式开启以避免开发环境误推。
ARCHIVE_GIT_ENABLED = _get_bool_env("ARCHIVE_GIT_ENABLED", False)

# 归档分支名
ARCHIVE_GIT_BRANCH = os.environ.get("ARCHIVE_GIT_BRANCH", "archive")

# worktree 检出目录(相对仓库根)
ARCHIVE_GIT_WORKTREE = os.environ.get("ARCHIVE_GIT_WORKTREE", ".archive-worktree")

# worktree 内承载归档数据的子目录名
ARCHIVE_GIT_DIR = os.environ.get("ARCHIVE_GIT_DIR", "archive")

# 推送目标 remote
ARCHIVE_GIT_REMOTE = os.environ.get("ARCHIVE_GIT_REMOTE", "origin")
```

- [ ] **Step 2: 在 `.gitignore` 追加 worktree 目录**

在 `.gitignore` 末尾追加:

```text

# 归档 worktree(git worktree 检出目录,不入版本控制)
.archive-worktree/
```

- [ ] **Step 3: 验证配置可导入且默认值正确**

Run:
```bash
python3 -c "from config import ARCHIVE_GIT_ENABLED, ARCHIVE_GIT_BRANCH, ARCHIVE_GIT_WORKTREE, ARCHIVE_GIT_DIR, ARCHIVE_GIT_REMOTE; assert ARCHIVE_GIT_ENABLED is False; assert ARCHIVE_GIT_BRANCH=='archive'; print('config ok')"
```
Expected: 输出 `config ok`

(说明:纯配置声明,布尔解析复用已验证的 `_get_bool_env`,此处用导入断言而非 unittest。)

- [ ] **Step 4: 编译校验**

Run: `python3 -m py_compile config.py`
Expected: 无输出(编译通过)

- [ ] **Step 5: Commit**

```bash
git add config.py .gitignore
git commit -m "feat: 新增采集后归档推送配置项"
```

---

## Task 2: 创建 archive_sync.py 骨架与 subprocess 辅助

**Files:**
- Create: `archive_sync.py`
- Create: `tests/test_archive_sync.py`

- [ ] **Step 1: 创建 `archive_sync.py`,写入模块头与辅助函数**

完整文件内容:

```python
# -*- coding: utf-8 -*-
"""
采集后把 output/ 归档镜像推送到 archive 分支。

通过 git worktree 在独立目录提交,主工作区(master)不受影响。
任何失败只记录日志,不影响采集主流程。
"""

import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from config import (
    ARCHIVE_GIT_BRANCH,
    ARCHIVE_GIT_DIR,
    ARCHIVE_GIT_ENABLED,
    ARCHIVE_GIT_REMOTE,
    ARCHIVE_GIT_WORKTREE,
    OUTPUT_ARCHIVE_DIR,
)

logger = logging.getLogger(__name__)


def _run(cmd, cwd=None):
    """运行任意命令,返回 (returncode, stdout, stderr),均去除首尾空白。"""
    proc = subprocess.run(list(cmd), cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _run_git(args, cwd=None):
    """运行 git 命令,cwd 非 None 时加 -C 指定工作目录。"""
    cmd = ["git"]
    if cwd is not None:
        cmd += ["-C", str(cwd)]
    return _run(cmd + list(args))


def _repo_root():
    """返回当前 git 仓库根目录(基于 cwd 探测)。"""
    code, stdout, stderr = _run_git(["rev-parse", "--show-toplevel"])
    if code != 0:
        raise RuntimeError("无法定位 git 仓库根目录: {}".format(stderr))
    return Path(stdout)
```

- [ ] **Step 2: 创建 `tests/test_archive_sync.py`,写入公共 fixture 与辅助函数测试**

完整文件内容:

```python
# -*- coding: utf-8 -*-
"""
archive_sync 模块测试用例。

用临时目录搭建本地 git 仓库 + bare remote,不依赖真实 GitHub。
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, ".")

from archive_sync import _run_git, _repo_root  # noqa: E402


def _git(args, cwd):
    """测试用:以 check 模式跑 git,失败直接抛错。"""
    subprocess.run(["git"] + list(args), cwd=str(cwd), check=True, capture_output=True, text=True)


def _make_repo(tmp_path):
    """在 tmp_path 下建一个带初始提交与 bare remote 的仓库,返回 (repo, remote)。"""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init"], repo)
    _git(["config", "user.email", "test@example.com"], repo)
    _git(["config", "user.name", "Test"], repo)
    (repo / "README.md").write_text("root\n", encoding="utf-8")
    _git(["add", "-A"], repo)
    _git(["commit", "-m", "init"], repo)

    remote = tmp_path / "remote.git"
    _git(["init", "--bare", str(remote)], tmp_path)
    _git(["remote", "add", "origin", str(remote)], repo)
    _git(["push", "-u", "origin", "master"], repo)
    return repo, remote


class TestRunGit(unittest.TestCase):
    def test_run_git_returns_version(self):
        code, stdout, _ = _run_git(["--version"])
        self.assertEqual(code, 0)
        self.assertIn("git version", stdout)

    def test_repo_root_locates_cwd_repository(self):
        root = _repo_root()
        self.assertTrue(root.exists())
        self.assertEqual(root.resolve(), Path(".").resolve())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 运行测试,确认通过**

Run: `python3 tests/test_archive_sync.py`
Expected: `OK` (2 个测试通过;TestRepoRoot 依赖当前已在 git 仓库内运行)

- [ ] **Step 4: Commit**

```bash
git add archive_sync.py tests/test_archive_sync.py
git commit -m "feat: 新增 archive_sync 模块骨架与 git 辅助函数"
```

---

## Task 3: 实现 _ensure_worktree(创建/复用 worktree 与 archive 分支)

**Files:**
- Modify: `archive_sync.py`(追加函数)
- Modify: `tests/test_archive_sync.py`(追加测试类)

- [ ] **Step 1: 在 `archive_sync.py` 的 `_repo_root` 之后追加**

```python
ARCHIVE_README = """# Archive 分支

本分支由采集流程自动写入,存放 `output/` 的镜像归档数据。

- 目录结构:`archive/<source_id>/<YYYY-MM-DD>/<batch>.json` + `archive/latest.json`
- 生成频率:跟随采集调度(默认每天 3 次)
- 请勿手动编辑;数据由 `archive_sync.py` 维护
"""


def _is_worktree(path):
    """判断路径是否是一个已检出的 git worktree。"""
    path = Path(path)
    return path.exists() and (path / ".git").exists()


def _local_branch_exists(repo_root, branch):
    code, _, _ = _run_git(["rev-parse", "--verify", branch], cwd=repo_root)
    return code == 0


def _remote_branch_exists(repo_root, remote, branch):
    code, stdout, _ = _run_git(["ls-remote", "--heads", remote, branch], cwd=repo_root)
    return code == 0 and bool(stdout)


def _pick_base(repo_root, remote):
    """挑选创建 archive 分支的起点,优先 remote/master。"""
    for candidate in ["{}/master".format(remote), "master", "HEAD"]:
        code, _, _ = _run_git(["rev-parse", "--verify", candidate], cwd=repo_root)
        if code == 0:
            return candidate
    return "HEAD"


def _ensure_readme(worktree_path):
    """首次创建 worktree 后,在根目录写入说明文件 ARCHIVE.md。

    用 ARCHIVE.md 而非 README.md,避免覆盖 master 继承下来的源码 README。
    """
    readme = Path(worktree_path) / "ARCHIVE.md"
    if readme.exists():
        return
    readme.write_text(ARCHIVE_README, encoding="utf-8")


def _ensure_worktree(repo_root, worktree_path, branch, remote):
    """确保 worktree 与 archive 分支存在,返回 worktree 绝对路径。

    - worktree 已存在:直接复用。
    - 分支已存在于本地或远端:检出该分支。
    - 否则:基于 remote/master(回退 master/HEAD)新建分支。
    """
    worktree_path = Path(worktree_path).resolve()

    if _is_worktree(worktree_path):
        return worktree_path

    if _local_branch_exists(repo_root, branch):
        code, _, err = _run_git(
            ["worktree", "add", str(worktree_path), branch], cwd=repo_root,
        )
    elif _remote_branch_exists(repo_root, remote, branch):
        code, _, err = _run_git(
            ["worktree", "add", str(worktree_path), "{}/{}".format(remote, branch)],
            cwd=repo_root,
        )
    else:
        base = _pick_base(repo_root, remote)
        code, _, err = _run_git(
            ["worktree", "add", "-b", branch, str(worktree_path), base], cwd=repo_root,
        )

    if code != 0:
        raise RuntimeError("创建 worktree 失败: {}".format(err))

    _ensure_readme(worktree_path)
    return worktree_path
```

- [ ] **Step 2: 在 `tests/test_archive_sync.py` 的 `TestRunGit` 之后、`if __name__` 之前追加测试类**

```python
from archive_sync import _ensure_worktree  # noqa: E402


class TestEnsureWorktree(unittest.TestCase):
    def test_creates_worktree_and_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = _make_repo(Path(tmp))
            worktree = repo / ".archive-worktree"
            result = _ensure_worktree(repo, worktree, "archive", "origin")
            self.assertTrue((worktree / ".git").exists())
            self.assertEqual(result, worktree.resolve())
            # archive 分支已在本地存在
            code, _, _ = _run_git(["rev-parse", "--verify", "archive"], cwd=repo)
            self.assertEqual(code, 0)
            # ARCHIVE.md 已写入 worktree 根
            self.assertTrue((worktree / "ARCHIVE.md").exists())

    def test_idempotent_on_second_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = _make_repo(Path(tmp))
            worktree = repo / ".archive-worktree"
            _ensure_worktree(repo, worktree, "archive", "origin")
            # 第二次调用不抛异常(worktree 已存在直接复用)
            _ensure_worktree(repo, worktree, "archive", "origin")
            self.assertTrue((worktree / ".git").exists())
```

(把 `from archive_sync import _ensure_worktree` 这行追加到文件顶部已有的 import 区,即紧跟 `from archive_sync import _run_git, _repo_root` 之后。)

- [ ] **Step 3: 运行测试,确认新测试通过**

Run: `python3 tests/test_archive_sync.py`
Expected: `OK` (TestRunGit 2 个 + TestEnsureWorktree 2 个,共 4 个通过)

- [ ] **Step 4: Commit**

```bash
git add archive_sync.py tests/test_archive_sync.py
git commit -m "feat: 实现 _ensure_worktree 创建与复用归档 worktree"
```

---

## Task 4: 实现 _sync_output(rsync 镜像 + shutil 降级)

**Files:**
- Modify: `archive_sync.py`(追加函数)
- Modify: `tests/test_archive_sync.py`(追加测试类)

- [ ] **Step 1: 在 `archive_sync.py` 的 `_ensure_worktree` 之后追加**

```python
def _has_rsync():
    return shutil.which("rsync") is not None


def _rsync_mirror(src, dst):
    """用 rsync 镜像 src -> dst(--delete 保持一致)。"""
    Path(dst).mkdir(parents=True, exist_ok=True)
    code, _, stderr = _run([
        "rsync", "-a", "--delete",
        "{}/".format(str(src).rstrip("/")),
        "{}/".format(str(dst).rstrip("/")),
    ])
    if code != 0:
        raise RuntimeError("rsync 镜像失败: {}".format(stderr))


def _shutil_mirror(src, dst):
    """无 rsync 时的纯 Python 镜像:删目标后整体拷贝。"""
    src = Path(src)
    dst = Path(dst)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _sync_output(output_dir, archive_dir):
    """镜像 output/ 到 archive/。rsync 优先,缺失时降级 shutil。"""
    output_dir = Path(output_dir)
    archive_dir = Path(archive_dir)
    if not output_dir.exists():
        raise RuntimeError("output 目录不存在: {}".format(output_dir))
    if _has_rsync():
        _rsync_mirror(output_dir, archive_dir)
    else:
        _shutil_mirror(output_dir, archive_dir)
```

- [ ] **Step 2: 在 `tests/test_archive_sync.py` 追加测试类**

(顶部 import 区追加 `from archive_sync import _sync_output`)

```python
class TestSyncOutput(unittest.TestCase):
    def _make_output(self, tmp):
        output = Path(tmp) / "output"
        (output / "github-daily" / "2026-06-17").mkdir(parents=True)
        (output / "github-daily" / "2026-06-17" / "01.json").write_text("{}", encoding="utf-8")
        (output / "latest.json").write_text("{}", encoding="utf-8")
        return output

    def test_mirrors_output_to_archive_via_shutil(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = self._make_output(tmp)
            archive = Path(tmp) / "archive"
            with patch("archive_sync._has_rsync", return_value=False):
                _sync_output(output, archive)
            self.assertTrue((archive / "latest.json").exists())
            self.assertTrue((archive / "github-daily" / "2026-06-17" / "01.json").exists())

    def test_uses_rsync_when_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = self._make_output(tmp)
            archive = Path(tmp) / "archive"
            with patch("archive_sync._has_rsync", return_value=True), \
                 patch("archive_sync._run") as mock_run:
                mock_run.return_value = (0, "", "")
                _sync_output(output, archive)
            invoked = [call.args[0] for call in mock_run.call_args_list]
            self.assertTrue(any(cmd[0] == "rsync" for cmd in invoked))
```

- [ ] **Step 3: 运行测试,确认通过**

Run: `python3 tests/test_archive_sync.py`
Expected: `OK` (累计 6 个通过)

- [ ] **Step 4: Commit**

```bash
git add archive_sync.py tests/test_archive_sync.py
git commit -m "feat: 实现 _sync_output 镜像 output 到 archive(rsync+shutil 降级)"
```

---

## Task 5: 实现 _commit_and_push(提交 + 推送 + 冲突重试)

**Files:**
- Modify: `archive_sync.py`(追加函数)
- Modify: `tests/test_archive_sync.py`(追加测试类)

- [ ] **Step 1: 在 `archive_sync.py` 的 `_sync_output` 之后追加**

```python
def _commit_message(item_count):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    if item_count is not None:
        return "archive: {} ({} items)".format(timestamp, item_count)
    return "archive: {}".format(timestamp)


def _commit_and_push(worktree_path, branch, remote, item_count):
    """在 worktree 内 add -> commit(仅当有变更)-> push。

    push 失败时 pull --rebase 后重试一次,仍失败则抛异常。
    返回 True 表示产生了新提交;False 表示无变更跳过。
    """
    _run_git(["add", "-A"], cwd=worktree_path)

    code, _, _ = _run_git(["diff", "--cached", "--quiet"], cwd=worktree_path)
    if code == 0:
        return False  # 无暂存变更

    message = _commit_message(item_count)
    code, _, err = _run_git(["commit", "-m", message], cwd=worktree_path)
    if code != 0:
        raise RuntimeError("归档 commit 失败: {}".format(err))

    code, _, err = _run_git(["push", remote, branch], cwd=worktree_path)
    if code != 0:
        _run_git(["pull", "--rebase", remote, branch], cwd=worktree_path)
        code, _, err = _run_git(["push", remote, branch], cwd=worktree_path)
        if code != 0:
            raise RuntimeError("归档 push 失败: {}".format(err))
    return True
```

- [ ] **Step 2: 在 `tests/test_archive_sync.py` 追加测试类**

(顶部 import 区追加 `from archive_sync import _commit_and_push`;`_ensure_worktree` 已在 Task 3 导入)

```python
class TestCommitAndPush(unittest.TestCase):
    def _setup(self, tmp):
        repo, remote = _make_repo(Path(tmp))
        worktree = repo / ".archive-worktree"
        _ensure_worktree(repo, worktree, "archive", "origin")
        return repo, remote, worktree

    def test_commits_and_pushes_new_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, remote, worktree = self._setup(tmp)
            archive = worktree / "archive"
            archive.mkdir()
            (archive / "01.json").write_text("{}", encoding="utf-8")
            pushed = _commit_and_push(worktree, "archive", "origin", item_count=5)
            self.assertTrue(pushed)
            # bare remote 已收到 archive 分支
            code, stdout, _ = _run_git(["ls-remote", "--heads", "origin", "archive"], cwd=repo)
            self.assertTrue(stdout.strip())

    def test_skips_commit_when_no_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, remote, worktree = self._setup(tmp)
            # 首次:提交 README(_ensure_worktree 写入)
            _commit_and_push(worktree, "archive", "origin", item_count=1)
            # 再次:无新变更,应跳过
            pushed = _commit_and_push(worktree, "archive", "origin", item_count=1)
            self.assertFalse(pushed)
```

- [ ] **Step 3: 运行测试,确认通过**

Run: `python3 tests/test_archive_sync.py`
Expected: `OK` (累计 8 个通过)

- [ ] **Step 4: Commit**

```bash
git add archive_sync.py tests/test_archive_sync.py
git commit -m "feat: 实现 _commit_and_push 提交推送归档到 archive 分支"
```

---

## Task 6: 实现 sync_archive_to_git 总入口(开关 + 异常吞掉)

**Files:**
- Modify: `archive_sync.py`(追加函数)
- Modify: `tests/test_archive_sync.py`(追加测试类)

- [ ] **Step 1: 在 `archive_sync.py` 末尾追加总入口**

```python
def sync_archive_to_git(item_count=None, repo_root=None):
    """采集后把 output/ 归档并推送到 archive 分支。

    任何异常只记录 warning 并返回 False,绝不影响采集主流程。
    repo_root 默认探测当前仓库,测试可显式注入。
    """
    if not ARCHIVE_GIT_ENABLED:
        logger.info("归档推送已关闭(ARCHIVE_GIT_ENABLED=false)")
        return False

    try:
        root = Path(repo_root) if repo_root is not None else _repo_root()
        worktree_path = _ensure_worktree(
            root / ARCHIVE_GIT_WORKTREE,
            ARCHIVE_GIT_BRANCH,
            ARCHIVE_GIT_REMOTE,
        )
        archive_dir = worktree_path / ARCHIVE_GIT_DIR
        _sync_output(root / OUTPUT_ARCHIVE_DIR, archive_dir)
        _commit_and_push(worktree_path, ARCHIVE_GIT_BRANCH, ARCHIVE_GIT_REMOTE, item_count)
        logger.info("归档已推送到 %s 分支", ARCHIVE_GIT_BRANCH)
        return True
    except Exception as e:  # noqa: BLE001 归档是尽力而为,吞掉所有异常
        logger.warning("归档推送失败(不影响采集): %s", e)
        return False
```

- [ ] **Step 2: 在 `tests/test_archive_sync.py` 追加测试类**

(顶部 import 区追加 `from archive_sync import sync_archive_to_git`)

```python
class TestSyncArchiveToGit(unittest.TestCase):
    def test_pushes_archive_when_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, remote = _make_repo(Path(tmp))
            output = repo / "output"
            (output / "tldr-ai" / "2026-06-17").mkdir(parents=True)
            (output / "tldr-ai" / "2026-06-17" / "01.json").write_text("{}", encoding="utf-8")
            (output / "latest.json").write_text("{}", encoding="utf-8")
            with patch("archive_sync.ARCHIVE_GIT_ENABLED", True), \
                 patch("archive_sync._repo_root", return_value=repo), \
                 patch("archive_sync._has_rsync", return_value=False):
                result = sync_archive_to_git(item_count=1)
            self.assertTrue(result)
            code, stdout, _ = _run_git(["ls-remote", "--heads", "origin", "archive"], cwd=repo)
            self.assertTrue(stdout.strip())

    def test_skips_when_disabled(self):
        with patch("archive_sync.ARCHIVE_GIT_ENABLED", False):
            result = sync_archive_to_git()
        self.assertFalse(result)

    def test_swallows_exceptions(self):
        with patch("archive_sync.ARCHIVE_GIT_ENABLED", True), \
             patch("archive_sync._repo_root", side_effect=RuntimeError("boom")):
            result = sync_archive_to_git()  # 不得抛出
        self.assertFalse(result)
```

- [ ] **Step 3: 运行测试,确认通过**

Run: `python3 tests/test_archive_sync.py`
Expected: `OK` (累计 11 个通过)

- [ ] **Step 4: Commit**

```bash
git add archive_sync.py tests/test_archive_sync.py
git commit -m "feat: 实现 sync_archive_to_git 总入口(开关+异常吞掉)"
```

---

## Task 7: 集成到 main.py 采集主流程

**Files:**
- Modify: `main.py`(`run_spider` 内,`persist_source_snapshots` 块之后)

- [ ] **Step 1: 在 `main.py` 的 `persist_source_snapshots` try/except 块之后插入归档调用**

定位 `main.py` 中这段(约 326–332 行):

```python
    logger.info("--- 写出来源归档并刷新 Redis ---")
    try:
        store_result = persist_source_snapshots(content_items)
        logger.info("来源快照处理完成: %s", store_result)
    except Exception as e:
        logger.error("来源快照处理失败: %s", e)
        errors.append("来源快照处理失败: {}".format(e))
```

在其**之后**、`# ==========================\n    # 生成邮件并发送` 之前插入:

```python
    # ==========================
    # 归档推送到 archive 分支(失败不影响主流程)
    # ==========================
    try:
        from archive_sync import sync_archive_to_git
        sync_archive_to_git(item_count=len(content_items))
    except Exception as e:
        logger.warning("归档推送异常(不影响采集): %s", e)
```

- [ ] **Step 2: 编译校验**

Run: `python3 -m py_compile main.py archive_sync.py`
Expected: 无输出

- [ ] **Step 3: 全量回归测试**

Run: `python3 tests/test_archive_sync.py`
Expected: `OK` (11 个通过;本任务不新增测试,见说明)

(说明:`run_spider` 是大量网络 IO 的集成函数,现有项目亦不为 `main.py` 写单测;归档逻辑已由 Task 2–6 的 11 个单测覆盖,集成点仅 5 行调用,靠 py_compile + 手动验证即可。)

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: 采集流程末尾接入归档推送"
```

---

## Task 8: 文档补充与全量验证

**Files:**
- Modify: `AGENTS.md`(补归档分支说明)

- [ ] **Step 1: 在 `AGENTS.md` 的「主要入口与模块」列表中补充 `archive_sync.py`**

在 `AGENTS.md` 的模块列表(含 `scheduler.py`、`email_builder.py` 等条目的那段)末尾追加一行:

```text
- `archive_sync.py`: 采集后把 `output/` 镜像推送到 `archive` 分支(git worktree,默认关闭,`ARCHIVE_GIT_ENABLED` 控制)。
```

- [ ] **Step 2: 在 `AGENTS.md` 环境变量约定中补充归档开关**

在「核心变量」或「数量变量」段后追加一小节:

```text
归档推送变量:

- `ARCHIVE_GIT_ENABLED`: 是否在采集后把 `output/` 推送到 `archive` 分支,默认 false。
- `ARCHIVE_GIT_BRANCH`: 归档分支名,默认 archive。
- `ARCHIVE_GIT_WORKTREE`: worktree 检出目录,默认 .archive-worktree。
- `ARCHIVE_GIT_DIR`: worktree 内归档子目录,默认 archive。
- `ARCHIVE_GIT_REMOTE`: 推送 remote,默认 origin。
```

- [ ] **Step 3: 全模块编译校验**

Run:
```bash
python3 -m py_compile main.py config.py archive_sync.py
```
Expected: 无输出

- [ ] **Step 4: 全量测试**

Run:
```bash
python3 tests/test_archive_sync.py
```
Expected: `OK` (11 个通过)

- [ ] **Step 5: Commit**

```bash
git add AGENTS.md
git commit -m "docs: AGENTS.md 补充归档推送说明"
```

---

## 部署启用(实现完成后由用户操作)

1. 确认运行环境有对 `agently.top` 的 SSH 写权限(push remote 为 `git@ssh.github.com:yunlongwen/agently.top.git`)。
2. 在 `.env` / 启动环境设置 `export ARCHIVE_GIT_ENABLED=true`。
3. 重启后端进程(`bash scripts/start_backend.sh`)。
4. 等待下一次采集(或临时设 `SPIDER_RUN_ON_STARTUP=true` 触发一次),观察日志出现「归档已推送到 archive 分支」。
5. 在 GitHub 仓库切到 `archive` 分支确认 `archive/` 数据与 README。

## 验收标准对照(spec 第 8 节)

- 开启开关后每次采集 archive 分支多一个 commit(由 Task 5/6 测试覆盖)。
- master 不含数据 commit(归档全程在 worktree/archive 分支)。
- 主工作区仅多出被 gitignore 的 `.archive-worktree/`(Task 1 加 ignore)。
- 推送失败时采集正常完成(Task 6 `test_swallows_exceptions` + main.py 双层 try/except)。
- 全部单测通过(Task 2–6 共 11 个)。
