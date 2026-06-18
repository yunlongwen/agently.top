# Agently.top

多源 AI / 开源 / 科技信息聚合 · 每日自动采集 · 中文智能摘要 · 卡片式资讯流

线上地址：[https://agently.top](https://agently.top)

## 它是什么

每天从 9 个信息源（GitHub Trending 日榜/周榜、Hacker News、Linux.do、少数派、钛媒体、OpenAI、Anthropic、InfoQ AI）抓取最新内容，通过 OpenAI 兼容接口（默认 `MiniMax-M3`）生成中文摘要 + 后端行动点，写入磁盘归档 + Redis 热数据，前端展示成卡片流。

## 快速开始

```bash
# 安装
git clone https://github.com/yunlongwen/agently.top.git
cd agently.top
pip3 install -r requirements.txt

# 配置（必须）
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"  # 或自建网关
export OPENAI_MODEL="gpt-4o-mini"

# 跑一次采集
python3 main.py

# 启动 API + 前端
python3 -m uvicorn api:app --host 0.0.0.0 --port 8000 &
cd frontend && npm install && npm run build
```

## 信息源

| ID | 名称 | 类型 |
|---|---|---|
| `github-daily` / `github-weekly` | GitHub Trending | 开源趋势 |
| `hacker-news` | Hacker News | 社区讨论 |
| `linux-do` | Linux.do 技术日报 | 社区讨论 |
| `sspai` | 少数派 | 中文科技 |
| `tmtpost` | 钛媒体 | 中文商业科技 |
| `openai` / `anthropic` | 官方 News | 厂商一手 |
| `infoq` | InfoQ AI Development | 工程实践 |

每个源独立抓取、独立容错，单一源失败不影响其他源输出。

## API

```bash
# 来源列表
curl https://agently.top/api/sources

# 单源最新快照（命中 Redis，3 天内）
curl https://agently.top/api/sources/github-daily/latest

# 健康检查
curl https://agently.top/api/health
```

返回结构统一为 `{generated_at, source, item_count, items[]}`，每条 item 含 `title` / `url` / `chinese_summary` / `backend_focus` 等字段。完整字段说明见 [`docs/rss-api-guide.md`](docs/rss-api-guide.md)。

另外提供总 RSS：`https://agently.top/api/rss.xml`

## 架构

```
采集层:  main.py
        ├─ github_trending / hacker_news / linux_do_news
        ├─ sspai / tmtpost
        └─ official_ai_sources (openai / anthropic / infoq)
摘要层:  content_items.summarize_content_items  (统一调用 AI)
数据层:  content_store.py  →  output/<source>/<date>/<batch>.json  +  Redis
服务层:  api.py  (FastAPI 只读)  +  scheduler.py  (进程内定时)
展示层:  frontend/  (Vue 3)  →  dist/  →  Nginx 静态托管
```

## 部署

服务器上一键脚本（拉代码 + 构建前端 + 部署 Nginx）：

```bash
bash scripts/deploy.sh
```

后端服务：

```bash
bash scripts/start_backend.sh
```

详见 `scripts/` 目录。所有可调参数都通过 `config.py` 中的环境变量注入，完整列表见源码。

## 归档与历史

每次采集会写入 `output/<source>/<YYYY-MM-DD>/<batch>.json`，并自动 git 推送到 `archive` 分支（需 `ARCHIVE_GIT_ENABLED=true`）。前端提供历史日期抽屉可查看任意历史快照。

## License

[MIT](LICENSE)
