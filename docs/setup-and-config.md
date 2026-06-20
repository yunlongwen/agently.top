# Agently.top 部署与配置指南

本文档包含 Agently.top 的完整部署、配置、架构说明与日常运维。若只想了解项目是什么，请先看根目录的 [README.md](../README.md)。

---

## 目录

- [信息源](#信息源)
- [核心功能](#核心功能)
- [架构](#架构)
- [API 接口](#api-接口)
- [部署](#部署)
- [环境变量完整列表](#环境变量完整列表)
- [日志排查](#日志排查)
- [开发约定](#开发约定)

---

## 信息源

| ID | 名称 | 类型 | 说明 |
|---|---|---|---|
| `github-daily` / `github-weekly` | GitHub Trending | 开源趋势 | 日榜/周榜各前 N 个仓库 |
| `hacker-news` | Hacker News | 社区讨论 | Top Stories + 顶级评论 |
| `linux-do` | Linux.do 技术日报 | 社区讨论 | 技术聚合日报 |
| `sspai` | 少数派 | 中文科技 | RSS 抓取 + AI 总结 |
| `tmtpost` | 钛媒体 | 中文商业科技 | RSS 抓取 + AI 总结 |
| `openai` / `anthropic` | 官方 News | 厂商一手 | 官方博客/新闻页 |
| `infoq` | InfoQ AI Development | 工程实践 | 聚合 AI Development / AI / Generative AI 多 RSS |

每个源**独立抓取、独立容错**，单一源失败不影响其他源输出。

---

## 核心功能

### 1. 自动采集与摘要
- 定时从 9 大信息源抓取内容
- 通过 OpenAI 兼容接口（默认 `MiniMax-M3`）生成中文摘要 + 开发关注点
- 统一数据模型：`source/category/title/url/published_at/original_summary/chinese_summary/backend_focus`

### 2. 分层记忆系统
- L1 每日趋势记忆、L2 主题追踪记忆、L3 编辑决策记忆
- 让每日生成具备跨天上下文，自动识别跟进报道与趋势演变
- 默认使用本地关键词/Jaccard 匹配，可开启 LLM 增强匹配

### 3. 数据存储
- **磁盘归档**: `output/<source>/<YYYY-MM-DD>/<batch>.json`
- **Redis 热缓存**: 3 天 TTL，API 优先读取 Redis，降级读磁盘
- **Git 归档推送**: 采集后自动推送到 `archive` 分支（可选）

### 4. Web 服务
- **FastAPI 只读接口**: `/api/sources`, `/api/sources/{id}/latest`, `/api/rss.xml`
- **Vue 3 前端**: 卡片式资讯流，Nginx 静态托管
- **访问统计**: 轻量自建统计，每小时汇总 UV/PV/Referer

### 5. 微信公众号发布
- 自动发布到微信公众号草稿箱
- 支持 AI 生成封面图（LLM 生成 + Pillow 文字封面兜底）
- 支持固定摘要、原创声明，降低内容违规风险
- 支持每个来源条数限制，控制单篇内容总量

### 6. 邮件推送（可选）
- Agently 企业邮箱（阿里企业邮箱）SMTP 发送每日摘要邮件
- 支持 SSL(465) 和 STARTTLS(587) 两种连接方式
- 支持按调度时间指定不同收件人

---

## 架构

```
采集层:  main.py
        ├─ github_trending / hacker_news / linux_do_news
        ├─ sspai / tmtpost
        └─ official_ai_sources (openai / anthropic / infoq)
摘要层:  content_items.summarize_content_items  (统一调用 AI)
记忆层:  memory_service.py  →  output/memory/  +  Redis
数据层:  content_store.py  →  output/<source>/<date>/<batch>.json  +  Redis
服务层:  api.py  (FastAPI 只读)  +  scheduler.py  (进程内定时)
发布层:  publish_service.py  +  publishers/wechat/  (微信公众号)
展示层:  frontend/  (Vue 3)  →  dist/  →  Nginx 静态托管
```

---

## API 接口

```bash
# 来源列表
curl https://agently.top/api/sources

# 单源最新快照（命中 Redis，3 天内）
curl https://agently.top/api/sources/github-daily/latest

# 访问统计汇总（需 token）
curl "https://agently.top/api/stats/summary?days=7&token=YOUR_TOKEN"

# 健康检查
curl https://agently.top/api/health

# RSS 总 feed
curl https://agently.top/api/rss.xml
```

返回结构统一为 `{generated_at, source, item_count, items[]}`，每条 item 含 `title` / `url` / `chinese_summary` / `backend_focus` 等字段。完整字段说明见 [`docs/rss-api-guide.md`](rss-api-guide.md)。

---

## 部署

### 环境要求
- Python 3.11+（推荐，3.8 有类型注解兼容问题）
- Node.js + npm（前端构建）
- Redis（热数据缓存）
- Nginx（反向代理 + 静态托管）
- 中文字体（封面图生成）: `google-noto-sans-cjk-ttc-fonts`

### 1. 安装依赖

```bash
# Python 依赖
pip3 install -r requirements.txt

# 中文字体（封面图需要）
# CentOS/RHEL:
yum install -y google-noto-sans-cjk-ttc-fonts
# Ubuntu/Debian:
# apt-get install -y fonts-noto-cjk

# 前端依赖
cd frontend && npm install
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填写核心配置。完整变量列表见下一节。

```bash
cp .env.example .env
```

核心必填项示例：

```bash
# AI 接口（必须）
export OPENAI_API_KEY="sk-..."
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4o-mini"

# Redis
export REDIS_URL="redis://localhost:6379/0"

# 微信公众号发布（可选）
export WECHAT_PUBLISH_ENABLED=true
export WECHAT_APP_ID="wx..."
export WECHAT_APP_SECRET="..."
export WECHAT_DEFAULT_TITLE="Agently 每日速览 - {date}"
export WECHAT_DEFAULT_DIGEST="AI 开发资讯每日速览 · 9 大源要点速读"
export WECHAT_MAX_ITEMS_PER_SOURCE=3
export WECHAT_DEFAULT_COVER_URL="https://agently.top/agently_cover.jpg"

# 邮件推送（可选，Agently 企业邮箱）
export SMTP_SERVER="smtp.qiye.aliyun.com"
export SMTP_PORT="465"
export SMTP_USER="ai@agently.top"
export SMTP_PASSWORD="your-password"
export MAIL_FROM="Agently AI <ai@agently.top>"
export MAIL_TO="recipient@example.com"
export SEND_EMAIL_ENABLED=true
export EMAIL_SEND_TIMES="08:30"

# 访问统计 token
export STATS_API_TOKEN="your-secret-token"
export ADMIN_API_TOKEN="your-secret-token"
```

### 3. 一键部署脚本

```bash
# 前端构建 + 部署到 Nginx
bash scripts/deploy.sh

# 或仅构建不拉代码
bash scripts/deploy.sh --build-only
```

### 4. systemd 服务配置（推荐）

创建 `/etc/systemd/system/agently-api.service`：

```ini
[Unit]
Description=Agently.top API Service
After=network.target redis.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/workspace/agently.top
EnvironmentFile=/etc/agently/agently-api.env
ExecStart=/usr/bin/python3.11 -m uvicorn api:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**注意**: `EnvironmentFile` 需要使用 systemd 格式（无 `export` 前缀，无注释），从 `.env` 转换：

```bash
# 创建 systemd 环境文件目录
mkdir -p /etc/agently

# 转换 .env 为 systemd 格式（去掉 export 和注释）
grep "^export" .env | sed 's/export //' > /etc/agently/agently-api.env

# 启动并启用开机自启
systemctl daemon-reload
systemctl enable agently-api.service
systemctl start agently-api.service
```

### 5. Nginx 配置

参考配置见 `nginx/agently.top.conf`（或服务器面板生成的配置），关键部分：

```nginx
server {
    listen 80;
    listen 443 ssl;
    server_name agently.top;
    root /root/workspace/agently.top/frontend/dist;

    # API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 前端路由
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### 6. 封面图生成

首次部署或更新品牌图时：

```bash
# 生成 900x500 品牌封面图
python3 scripts/generate_cover.py

# 图片会自动保存到 frontend/public/agently_cover.jpg
# 构建前端时会自动复制到 dist 目录
```

---

## 环境变量完整列表

详见 [`.env.example`](../.env.example)。下表列出主要变量：

### 核心配置
| 变量 | 说明 | 默认值 |
|---|---|---|
| `OPENAI_API_KEY` | AI 接口 API Key | 必填 |
| `OPENAI_BASE_URL` | AI 接口基础地址 | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | 使用的模型 | `gpt-4o-mini` |
| `REDIS_URL` | Redis 连接地址 | `redis://localhost:6379/0` |
| `LOG_FILE` | 日志文件路径 | `/root/logs/github-python/trending.log` |

### 采集配置
| 变量 | 说明 | 默认值 |
|---|---|---|
| `GITHUB_TRENDING_TOP_COUNT` | GitHub 日榜/周榜各取前 N | 10 |
| `HN_TOP_COUNT` | Hacker News 取前 N 帖 | 10 |
| `HN_COMMENTS_PER_STORY` | 每帖取前 N 条评论 | 10 |
| `SSPAI_TOP_COUNT` | 少数派取前 N 条 | 10 |
| `TMTPOST_TOP_COUNT` | 钛媒体取前 N 条 | 10 |
| `OPENAI_NEWS_COUNT` | OpenAI 取前 N 条 | 10 |
| `ANTHROPIC_NEWS_COUNT` | Anthropic 取前 N 条 | 10 |
| `INFOQ_AI_NEWS_COUNT` | InfoQ 取前 N 条 | 10 |
| `SPIDER_SCHEDULE_TIMES` | 采集调度时间 | `07:50,15:50,23:50` |
| `SPIDER_SCHEDULER_ENABLED` | 是否启用定时采集 | `true` |

### 微信公众号发布
| 变量 | 说明 | 默认值 |
|---|---|---|
| `WECHAT_PUBLISH_ENABLED` | 启用微信发布 | `false` |
| `WECHAT_APP_ID` | 微信公众号 AppID | 空 |
| `WECHAT_APP_SECRET` | 微信公众号 AppSecret | 空 |
| `WECHAT_DEFAULT_TITLE` | 默认标题模板 | `Agently 每日速览 - {date}` |
| `WECHAT_DEFAULT_AUTHOR` | 作者名 | `Agently` |
| `WECHAT_DEFAULT_DIGEST` | 固定摘要（避免微信自动抽取） | 空 |
| `WECHAT_MAX_ITEMS_PER_SOURCE` | 每来源最多条数 | 5 |
| `WECHAT_DEFAULT_COVER_URL` | 默认封面图 URL | 空 |
| `WECHAT_GENERATE_COVER_BY_LLM` | 是否用 LLM 生成封面 | `false` |
| `PUBLISH_SCHEDULE_TIMES` | 发布调度时间 | 空（跟随采集） |
| `PUBLISH_ENABLED` | 启用发布编排 | `false` |

### 邮件配置
| 变量 | 说明 | 默认值 |
|---|---|---|
| `SMTP_SERVER` | SMTP 服务器地址 | `smtp.qiye.aliyun.com` |
| `SMTP_PORT` | SMTP 端口 (465/587) | `465` |
| `SMTP_USER` | Agently 企业邮箱账号 | 空 |
| `SMTP_PASSWORD` | 邮箱密码 | 空 |
| `MAIL_FROM` | 发件人显示名称 | `Agently AI <ai@agently.top>` |
| `MAIL_TO` | 收件人邮箱 | 空 |
| `SEND_EMAIL_ENABLED` | 启用邮件发送 | `false` |
| `EMAIL_SEND_TIMES` | 邮件发送时间 | `08:30` |

### 归档与统计
| 变量 | 说明 | 默认值 |
|---|---|---|
| `ARCHIVE_GIT_ENABLED` | 启用 git 归档推送 | `false` |
| `STATS_ENABLED` | 启用访问统计 | `true` |
| `STATS_API_TOKEN` | 统计接口 token | 空 |
| `ADMIN_API_TOKEN` | 管理接口 token | 空 |

### 分层记忆系统
| 变量 | 说明 | 默认值 |
|---|---|---|
| `MEMORY_ENABLED` | 启用分层记忆 | `true` |
| `MEMORY_DAILY_TTL_DAYS` | L1 每日记忆 TTL | 7 |
| `MEMORY_TOPIC_TTL_DAYS` | L2 主题记忆 TTL | 30 |
| `MEMORY_EDITORIAL_TTL_DAYS` | L3 编辑决策记忆 TTL | 14 |
| `MEMORY_CONTEXT_MAX_TOPICS` | 摘要上下文最大主题数 | 5 |
| `MEMORY_LLM_ENABLED` | 使用 LLM 做主题匹配 | `false` |

---

## 日志排查

```bash
# 查看访问日志
grep "\[访问\]" /root/logs/github-python/trending.log

# 查看数据来源追踪（Redis/磁盘）
grep "\[数据\]" /root/logs/github-python/trending.log

# 查看每小时统计汇总
grep "\[统计\]" /root/logs/github-python/trending.log

# 查看 API 服务日志
journalctl -u agently-api.service -f

# 查看微信发布日志
grep "WeChat" /root/logs/github-python/trending.log
```

---

## 开发约定

- 新增信息源时，应优先选择官方 RSS/API；HTML 页面解析只能作为兜底
- 每个信息源必须独立容错，不能因单个源失败导致其他源无法输出
- 新增来源必须适配到 `content_items.py` 的统一字段
- AI 摘要失败或缺少 `OPENAI_API_KEY` 时，必须保留原始标题、链接和原文摘要
- 不要把运行生成的 `output/`、日志、`.env`、缓存文件加入版本控制
