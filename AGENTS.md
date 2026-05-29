# AGENTS.md

本文件为本仓库的 AI 协作约定。所有自动化助手在读取、修改或评审本项目时必须遵守。

## 项目概览

这是一个 Python 脚本型 AI 后端专项信息源聚合项目。主流程每天抓取 GitHub Trending、Hacker News、TLDR AI、OpenAI、Anthropic、InfoQ AI Development 等信息源，通过 GitHub Models API 生成中文摘要，输出 HTML 邮件，并生成统一 JSON 文件供后续后端落 Redis 或其他存储使用。

当前不是 Web 服务，也不直接写 Redis；`output/latest.json` 是后续后端接入点。

## 主要入口与模块

- `main.py`: 主入口，协调所有信息源抓取、AI 摘要、JSON 写出和邮件发送。
- `config.py`: 环境变量配置中心，所有可调参数都应从这里读取。
- `github_trending.py`: GitHub Trending daily / weekly 抓取和项目摘要。
- `hacker_news.py`: Hacker News Top Stories、评论抓取和社区讨论摘要。
- `tldr_ai.py`: TLDR AI 最新一期抓取和中文整理。
- `official_ai_sources.py`: OpenAI、Anthropic、InfoQ AI Development 信息源抓取。
- `content_items.py`: 统一信息项模型、跨来源 JSON 适配、统一 AI 摘要、JSON 输出。
- `email_builder.py`: HTML 邮件内容生成。
- `email_sender.py`: SMTP 邮件发送。
- `test_email.py`: SMTP 发送测试脚本。

## 运行方式

安装依赖：

```bash
pip3 install -r requirements.txt
```

本地运行时先确保环境变量已生效。常见方式：

```bash
source ~/.bash_profile
LOG_FILE=/private/tmp/github-trending-spider-run.log python3 main.py
```

服务器定时任务参考：

```bash
source ~/.bash_profile && cd /root/work/workspace/gitee/github-trending-spider && /usr/bin/python3 main.py
```

默认日志路径是 `/root/logs/github-python/trending.log`。本地没有该目录时，应通过 `LOG_FILE` 指向可写路径。

## 环境变量约定

敏感信息只能通过环境变量配置，不要写入代码、README 示例真实值或提交记录。

核心变量：

- `GITHUB_TOKEN`: GitHub Models API token，需要 `models:read` 权限。
- `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_TO`: SMTP 邮件发送配置。
- `LOG_FILE`: 日志路径。
- `OUTPUT_JSON_PATH`: 统一 JSON 输出路径，默认 `output/latest.json`。

数量变量：

- `GITHUB_TRENDING_TOP_COUNT`: GitHub daily / weekly 各获取前 N 个仓库，默认 10。
- `HN_TOP_COUNT`: Hacker News 获取前 N 个帖子，默认 10。
- `HN_COMMENTS_PER_STORY`: 每帖获取前 N 条顶级评论，默认 10。
- `TLDR_AI_TOP_COUNT`: TLDR AI 获取前 N 条内容，默认 10。
- `OPENAI_NEWS_COUNT`: OpenAI 获取前 N 条内容，默认 10。
- `ANTHROPIC_NEWS_COUNT`: Anthropic 获取前 N 条内容，默认 10。
- `INFOQ_AI_NEWS_COUNT`: InfoQ 获取前 N 条内容，默认 10。

数量配置遵循“最多取 N 条”：如果配置为 100，但源头实际只解析到 14 条，则只展示 14 条。

## 输出与忽略文件

- `output/latest.json`: 运行生成的统一信息项 JSON，供后续后端读取。
- `output/email_preview.html`: 可用于本地预览邮件效果。
- `output/` 已在 `.gitignore` 中忽略，运行产物不要提交。
- `.env` 已忽略，真实密钥不要提交。
- `.task/` 已忽略，用于存放 AI 任务计划和任务记录。

## 任务文件规则

以后所有新任务计划、任务拆解、执行清单、阶段性记录，都必须写入 `.task/` 目录，不要再新增或扩写根目录任务文件。

生成新任务文件之前，必须先参考已有任务记录，按以下顺序读取：

1. 根目录 `tasks.md`: 当前 AI 后端专项信息源 v1 的完整实施历史。
2. `.task/tasks.md`: 更早的 HN 与 TLDR AI 接入历史。
3. `.task/` 下其他同类任务文件: 如果存在，优先参考同主题最近任务。

参考时重点看：任务标题粒度、涉及文件、勾选项写法、验证记录、是否有历史遗留问题。不要重复规划已经完成的内容。

命名格式：

```text
.task/YYYY-MM-DD_N-short-slug.md
```

示例：

```text
.task/2026-05-29_1-add-source-count-config.md
.task/2026-05-29_2-fix-infoq-feed.md
```

要求：

- 每个独立需求使用单独任务文件。
- 同一天多个任务用 `_1`, `_2`, `_3` 区分。
- 文件名 slug 使用英文小写和连字符，表达任务主题。
- 任务文件内至少记录：目标、涉及文件、执行步骤、验证结果、遗留问题。
- 根目录 `tasks.md` 只视为历史记录；新任务不要继续写入该文件。

## 当前任务历史摘要

当前仓库已有两批主要任务记录，可作为后续任务拆解模板。

### `.task/tasks.md` 历史任务

- 新增 Hacker News Top 10 + 评论总结功能：
  - 新增 `hacker_news.py`，通过 HN Firebase API 获取 Top Stories 和评论。
  - 抽出 `email_sender.py`、`email_builder.py`，让邮件发送和 HTML 生成从 GitHub 爬虫中解耦。
  - 新建 `main.py` 作为统一入口，协调 GitHub + HN + AI + 邮件流程。
  - 引入独立容错：GitHub 和 HN 任一成功即可发送邮件。
- 新增 TLDR AI 中文内容接入：
  - 新增 `tldr_ai.py`，从 TLDR AI 官方归档页解析最新 issue。
  - 接入 TLDR AI 阶段，支持未配置 `GITHUB_TOKEN` 时降级展示英文摘要。
  - 更新邮件模板和 README，形成 GitHub + HN + TLDR AI 三源日报。

### 根目录 `tasks.md` 当前任务

- AI 后端专项信息源 v1：
  - 新增 `content_items.py`，统一字段为 `source/category/title/url/published_at/original_summary/chinese_summary/backend_focus`。
  - 新增 `official_ai_sources.py`，接入 OpenAI、Anthropic、InfoQ AI Development。
  - `main.py` 调整为 6 个源独立抓取、独立容错，同时生成邮件和 `output/latest.json`。
  - `email_builder.py` 保留 GitHub/HN/TLDR AI 旧展示，并新增 OpenAI、Anthropic、InfoQ 分板块展示。
  - InfoQ 单个 `ai-development/news` feed 当前条目少，已改为聚合 AI Development、Artificial Intelligence、Generative AI 多个官方 RSS。
  - 数量配置环境变量化：`GITHUB_TRENDING_TOP_COUNT`、`HN_TOP_COUNT`、`TLDR_AI_TOP_COUNT`、`OPENAI_NEWS_COUNT`、`ANTHROPIC_NEWS_COUNT`、`INFOQ_AI_NEWS_COUNT` 等。

后续任务若涉及新增源、调整邮件、调整 JSON 结构或改运行配置，必须先对照以上历史，复用已有模块边界，不要重新设计主流程。

## 开发约定

- 优先保持脚本结构简单，不引入 Flask/FastAPI，除非需求明确要求站点服务。
- 新增信息源时，应优先选择官方 RSS/API；HTML 页面解析只能作为兜底。
- 每个信息源必须独立容错，不能因单个源失败导致其他源无法输出。
- 新增来源必须适配到 `content_items.py` 的统一字段：
  - `source`
  - `category`
  - `title`
  - `url`
  - `published_at`
  - `original_summary`
  - `chinese_summary`
  - `backend_focus`
- AI 摘要失败或缺少 `GITHUB_TOKEN` 时，必须保留原始标题、链接和原文摘要，并给出明确降级文案。
- 不要把运行生成的 `output/`、日志、`.env`、缓存文件加入版本控制。

## 验证建议

基础检查：

```bash
python3 -m py_compile main.py config.py github_trending.py hacker_news.py tldr_ai.py official_ai_sources.py content_items.py email_builder.py email_sender.py
```

本地完整运行：

```bash
source ~/.bash_profile && LOG_FILE=/private/tmp/github-trending-spider-run.log python3 main.py
```

如果只想验证邮件模板或 JSON 写出，优先使用小样本构造测试，避免频繁发送真实邮件。

## 沟通与安全

- 回答用户时默认使用中文。
- 对不确定点先询问，不要猜测。
- 修改前先查代码事实，避免凭 README 或记忆判断。
- 任何真实 token、邮箱授权码、密码只允许报告“已设置/未设置/长度”，不要明文输出。
