# Tasks: AI 后端专项信息源 v1

- Spec 审批: 2026-05-29
- YOLO Mode: Off

---

## Task 1: 新增统一信息项与 JSON 输出 [DONE]
- 涉及文件: `content_items.py`
- [x] 定义统一信息项字段: source, category, title, url, published_at, original_summary, chinese_summary, backend_focus
- [x] 提供 6 个来源到统一信息项的适配逻辑
- [x] 提供统一 AI 摘要逻辑
- [x] 写出 `output/latest.json`
- 验证: PASSED

---

## Task 2: 新增 OpenAI / Anthropic / InfoQ 信息源 [DONE]
- 涉及文件: `official_ai_sources.py`, `config.py`
- [x] 抓取 OpenAI News 最近内容
- [x] 抓取 Anthropic Newsroom 最近内容
- [x] 通过 InfoQ AI Development RSS 抓取工程实践内容
- [x] 新增可配置 URL、数量和重试次数
- 验证: PASSED

---

## Task 3: 接入主流程 [DONE]
- 涉及文件: `main.py`
- [x] 6 个源独立抓取、独立容错
- [x] 任一源成功即可继续
- [x] 新增官方 AI / AI 工程实践摘要阶段
- [x] 同时生成邮件和统一 JSON
- 验证: PASSED

---

## Task 4: 更新邮件模板 [DONE]
- 涉及文件: `email_builder.py`
- [x] 保留 GitHub / HN / TLDR AI 原有展示
- [x] 新增 OpenAI 官方更新板块
- [x] 新增 Anthropic 官方更新板块
- [x] 新增 InfoQ AI Development 工程实践板块，并展示 InfoQ 页面链接
- [x] 页脚同步 6 个数据来源
- 验证: PASSED

---

## Task 4.1: 调整 InfoQ 数据源覆盖范围 [DONE]
- 涉及文件: `official_ai_sources.py`, `config.py`, `README.md`
- [x] 解释单个 `ai-development/news` RSS 当前只返回 1 条内容
- [x] 改为聚合 AI Development / Artificial Intelligence / Generative AI 多个官方 RSS
- [x] 保留 InfoQ AI Development 页面配置和邮件页面链接
- 验证: PASSED

---

## Task 5: 文档同步 [DONE]
- 涉及文件: `README.md`, `.gitignore`
- [x] README 同步 6 个信息源
- [x] README 说明统一 JSON 输出和 Redis 预留边界
- [x] `.gitignore` 忽略运行时 `output/`
- 验证: PASSED

---

## Task 6: 验证 [DONE]
- [x] Python 编译检查通过
- [x] 邮件 HTML 生成检查通过
- [x] 统一 JSON 写出检查通过
- [x] 新源单模块抓取在当前环境中执行验证
- 验证: PASSED

---

## Task 7: 信息源数量环境变量化 [DONE]
- 涉及文件: `config.py`, `github_trending.py`, `README.md`, `.env.example`
- [x] 新增 `GITHUB_TRENDING_TOP_COUNT`
- [x] 将 TLDR AI / OpenAI / Anthropic / InfoQ 默认数量调整为 10
- [x] 保留 HN 默认 10
- [x] README 和 `.env.example` 说明数量配置规则：配置值大于实际可抓取数量时，只展示实际数量
- 验证: PASSED
