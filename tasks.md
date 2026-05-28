# Tasks: 新增 TLDR AI 中文内容接入

- Spec 审批: 2026-05-28
- YOLO Mode: Off

---

## Task 1: 新建 tldr_ai.py — TLDR AI 抓取 + 中文整理 [DONE]
- 涉及文件: 新建 `tldr_ai.py`
- [x] 从 `https://ai.tldr.tech/` 获取最新 issue 链接
- [x] 抓取最新 issue 页面并解析标题、链接、摘要、分类
- [x] 默认保留前 8 条内容
- [x] 通过 GitHub Models API 生成中文整理
- [x] 未配置 `GITHUB_TOKEN` 时降级展示英文摘要并标注原因
- 验证: PASSED

---

## Task 2: 更新 config.py — 新增 TLDR AI 配置项 [DONE]
- 涉及文件: `config.py`
- [x] 新增 `TLDR_AI_HOME_URL`
- [x] 新增 `TLDR_AI_TOP_COUNT`
- [x] 新增 `TLDR_AI_MAX_RETRIES`
- 验证: PASSED

---

## Task 3: 更新 main.py — 接入第三数据源 [DONE]
- 涉及文件: `main.py`
- [x] 在 HN 阶段后新增 TLDR AI 阶段
- [x] 调用 `fetch_latest_tldr_ai_issue` 和 `ai_translate_tldr_ai`
- [x] 所有数据源失败才退出
- [x] 邮件标题更新为 `GitHub + HN + TLDR AI 热点报告 - {date}`
- 验证: PASSED

---

## Task 4: 更新 email_builder.py — 新增 TLDR AI 邮件板块 [DONE]
- 涉及文件: `email_builder.py`
- [x] `build_email_html` 新增 `tldr_items` 参数
- [x] 新增 `TLDR AI 今日精选` 表格
- [x] 页脚数据来源增加 TLDR AI
- [x] 无数据提示兼容三数据源
- 验证: PASSED

---

## Task 5: 更新 README.md — 同步使用说明 [DONE]
- 涉及文件: `README.md`
- [x] 更新项目名、功能说明、文件结构
- [x] 新增 TLDR AI 可选配置项
- 验证: PASSED

---

## Task 6: 验证 [DONE]
- [x] 所有模块 import 成功
- [x] HTML 生成成功，单独 TLDR AI 数据可展示
- [x] 实际请求 TLDR AI 官方归档页并解析至少 1 条内容
- [x] 未配置 `GITHUB_TOKEN` 时中文整理流程可降级
- 验证: PASSED

---

# Tasks: 新增 Hacker News Top 10 + 评论总结功能

- Spec 审批: 2026-05-03
- YOLO Mode: Off

---

## Task 1: 更新 config.py — 新增 HN 配置项 [DONE]
- 涉及文件: `config.py`
- [x] 在文件末尾新增 HN 配置区块
- [x] 新增配置项:
  - `HN_API_BASE = "https://hacker-news.firebaseio.com/v0"`
  - `HN_TOP_COUNT = 10`
  - `HN_COMMENTS_PER_STORY = 10`
  - `HN_MAX_RETRIES = 5`
  - `HN_CONCURRENT_WORKERS = 10`
- 验证: PASSED

---

## Task 2: 抽出 email_sender.py — 邮件发送模块 [DONE]
- 涉及文件: 新建 `email_sender.py`
- [x] 从 `github_trending.py` 提取 `_parse_recipients`, `send_email`, `send_failure_notify`
- [x] `send_email` 新增 `subject` 参数
- 验证: PASSED

---

## Task 3: 抽出 email_builder.py — HTML 邮件生成模块 [DONE]
- 涉及文件: 新建 `email_builder.py`
- [x] 提取 `_escape_html`, 重命名 `_build_github_table`
- [x] 新增 `_build_hn_table` (# | 标题/链接 | 分数 | 评论数 | AI 总结)
- [x] 扩展 `build_email_html(daily_repos, weekly_repos, hn_stories)`
- [x] 并列板块布局 + section-divider + 独立容错
- 验证: PASSED

---

## Task 4: 新建 hacker_news.py — HN 数据获取 + AI 总结 [DONE]
- 涉及文件: 新建 `hacker_news.py`
- [x] `fetch_hn_top_stories` - Firebase API + ThreadPoolExecutor 并发
- [x] `fetch_all_comments` - 每帖 Top 10 顶级评论
- [x] `ai_summarize_hn` - 一次性 AI 总结
- [x] `_html_to_text` - HTML 转纯文本 + 截断
- [x] `_call_hn_ai_api` - 独立 AI 调用（max_tokens=8000）
- 验证: PASSED (实际 API 调用成功获取数据)

---

## Task 5: 重构 github_trending.py — 仅保留 GitHub 爬虫 + AI 总结 [DONE]
- 涉及文件: `github_trending.py`
- [x] 删除 HTML 生成、邮件发送、main 函数
- [x] 保留 fetch_trending, ai_summarize, _call_ai_api
- [x] 清理无用 import
- [x] 日志配置移至 main.py
- 验证: PASSED

---

## Task 6: 新建 main.py — 主入口协调全流程 [DONE]
- 涉及文件: 新建 `main.py`
- [x] 全局日志配置
- [x] GitHub 阶段: 爬取 daily/weekly + AI 总结
- [x] HN 阶段: fetch_hn_top_stories + fetch_all_comments + ai_summarize_hn
- [x] 独立容错: 任一成功即发邮件，全部失败发通知
- [x] 邮件标题: "GitHub + HN 热点报告 - {date}"
- 验证: PASSED

---

## Task 7: 更新 .env.example 和 README.md [DONE]
- [x] `.env.example`: 新增 HN 可选配置注释
- [x] `README.md`: 更新功能说明、文件结构、运行方式、可选配置表
- 验证: PASSED

---

## Task 8: 端到端测试验证 [DONE]
- [x] 所有 6 个模块 import 成功，无循环依赖
- [x] HN API 实际调用成功（获取 3 个帖子 + 8 条评论）
- [x] HTML 生成正确（含 GitHub section + HN section）
- 验证: ALL PASSED

---

## Commit Message 草稿

```
feat: 新增 Hacker News Top 10 热点 + 评论总结功能

- 新增 hacker_news.py: 通过 Firebase API 获取 HN Top Stories 和评论
- 新增 email_builder.py: HTML 邮件模板生成（GitHub + HN 并列板块）
- 新增 email_sender.py: SMTP 邮件发送模块
- 新增 main.py: 主入口，协调 GitHub + HN + AI + 邮件全流程
- 重构 github_trending.py: 仅保留 GitHub 爬虫和 AI 总结
- 更新 config.py: 新增 HN 相关配置项
- 独立容错机制: GitHub 和 HN 任一成功即发邮件
- 使用 ThreadPoolExecutor 并发获取 HN 数据
```
