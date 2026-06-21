# Milestone A 设计文档：扩展信息源与国内多渠道推送

> 日期：2026-06-21  
> 范围：Milestone A（扩大流量与用户触达）  
> 状态：待审阅

---

## 1. 背景与目标

### 1.1 当前项目现状

Agently.top 目前已具备：

- 9 大信息源自动采集（GitHub Trending 日/周榜、Hacker News、Linux.do、少数派、钛媒体、OpenAI、Anthropic、InfoQ AI）
- AI 中文摘要（MiniMax-M3 / OpenAI 兼容接口）
- 微信公众号草稿发布、邮件订阅推送
- Vue 3 卡片流前端、FastAPI 只读接口、RSS/API 输出
- 轻量访问统计

### 1.2 本次迭代目标

按用户确定的优先级 **A（扩大触达）→ B（提升粘性）→ D（生态壁垒）→ C（降本稳态）**，Milestone A 聚焦：

1. **扩展信息源**：RSS 自定义输入 + 国内可访问的新源（V2EX、36kr、少数派 Matrix、ModelScope、arXiv 可选）。
2. **统一渲染层**：把邮件、微信公众号、各渠道推送的渲染逻辑抽象出来，避免重复。
3. **国内多渠道推送**：飞书、企业微信、钉钉、微信公众号模板消息、QQ Bot、微博、WPS 协作。

### 1.3 核心约束

- 部署服务器**不能使用网络代理**。
- 所有新增源和推送渠道必须能在**国内服务器裸连稳定访问**。
- 海外源（arXiv、TechCrunch、Telegram、Slack 等）仅作为可选项，默认关闭。

---

## 2. 总体架构

### 2.1 模块划分

```
agently.top/
├── sources/                          # 爬虫按源组织
│   ├── base.py                       # SourceSpider 抽象基类
│   ├── github_trending.py            # 现有
│   ├── hacker_news.py
│   ├── linux_do_news.py
│   ├── sspai.py
│   ├── tmtpost.py
│   ├── official_ai_sources.py
│   ├── rss.py                        # A1: RSS 聚合输入
│   ├── v2ex.py                       # A2: V2EX
│   ├── thirty_six_kr_venture.py      # A2: 36kr 创投
│   ├── sspai_matrix.py               # A2: 少数派 Matrix
│   ├── modelscope.py                 # A2: ModelScope 魔搭
│   └── arxiv.py                      # A2: arXiv（默认关闭）
├── renderers/                        # A5: 统一渲染层
│   ├── base.py
│   ├── markdown_renderer.py
│   ├── html_renderer.py
│   ├── plain_renderer.py
│   └── feishu_card_renderer.py
├── publishers/                       # 推送渠道
│   ├── base.py
│   ├── wechat_official.py            # 现有：公众号文章
│   ├── email.py                      # 现有：邮件
│   ├── feishu.py                     # A3: 飞书
│   ├── wechat_work.py                # A3: 企业微信
│   ├── dingtalk.py                   # A3: 钉钉
│   ├── wechat_template.py            # A3: 公众号模板消息
│   ├── qq_bot.py                     # A3: QQ Bot
│   ├── weibo.py                      # A3: 微博
│   ├── wps_xiezuo.py                 # A3: WPS 协作
│   └── telegram.py                   # A3: Telegram（可选）
├── models/content_item.py            # 统一数据模型
├── source_registry.py                # 源注册表
├── publish_service.py                # 发布编排
├── config.py                         # 配置加载
└── docs/superpowers/specs/           # 设计文档
```

### 2.2 数据流

```
┌─────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│  信息源      │────▶│ content_items.py    │────▶│  Redis / 磁盘   │
│ (含 RSS 输入)│     │ summarize + 统一字段  │     │   归档存储       │
└─────────────┘     └─────────────────────┘     └─────────────────┘
                                                        │
                              ┌───────────────────────┼───────────────┐
                              ▼                       ▼               ▼
                        ┌──────────┐            ┌──────────┐    ┌────────────┐
                        │ API/RSS  │            │ 渲染层    │    │ 记忆/统计   │
                        │ 只读输出  │            │ Markdown │    │            │
                        └──────────┘            │ HTML     │    └────────────┘
                                                │ Plain    │
                                                │ Feishu   │
                                                │ Card     │
                                                └────┬─────┘
                                                     │
                              ┌──────────────────────┼──────────────────────┐
                              ▼                      ▼                      ▼
                        ┌──────────┐          ┌──────────┐           ┌──────────┐
                        │  邮件     │          │ 微信公众号 │           │  飞书     │
                        │  HTML    │          │  Markdown │           │  卡片     │
                        └──────────┘          └──────────┘           └──────────┘
                              ▲                      ▲                      ▲
                              └──────────────────────┴──────────────────────┘
                                                   │
                                            ┌──────────┐
                                            │ 企业微信/ │
                                            │ 钉钉/模板 │
                                            │ QQ/微博   │
                                            └──────────┘
```

---

## 3. A5：统一渲染层

### 3.1 设计原则

- 内容与渠道解耦：渲染器只生成标准格式，publisher 只负责 transport。
- 参考 TrendRadar 的「渠道格式指南」：每个渠道有支持的格式、长度限制、转义规则。
- 向后兼容：现有 `email_builder.py` 和 `wechat_article_builder.py` 保留 facade，内部转发到新渲染器。

### 3.2 核心接口

```python
# renderers/base.py
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Literal

@dataclass
class RenderedContent:
    channel: str
    format: Literal["markdown", "html", "plain", "feishu_card"]
    title: str
    body: str
    excerpt: str
    metadata: dict

class Renderer(ABC):
    @abstractmethod
    def render(self, items: list[ContentItem], channel: str, options: dict | None = None) -> RenderedContent:
        ...
```

### 3.3 渲染器列表

| 渲染器 | 输出 | 用途 |
|---|---|---|
| `MarkdownRenderer` | Markdown | 微信公众号、Telegram、企业微信、钉钉 |
| `HtmlRenderer` | HTML | 邮件、Web 页面（Markdown → HTML） |
| `PlainRenderer` | 纯文本 | Bark、短信、降级场景 |
| `FeishuCardRenderer` | JSON 卡片 | 飞书群机器人 |

### 3.4 渠道格式指南

```python
CHANNEL_FORMAT_GUIDE = {
    "wechat": {"format": "markdown", "max_length": None},
    "email": {"format": "html", "max_length": None},
    "telegram": {"format": "markdown", "max_length": 4096, "escape_chars": "_ *[]()~`>#+-=|{}.!"},
    "feishu": {"format": "feishu_card", "max_length": 30000},
    "wechat_work": {"format": "markdown", "max_length": 4096},
    "dingtalk": {"format": "markdown", "max_length": 20000},
    "bark": {"format": "plain", "max_length": 200},
}
```

### 3.5 超长处理

当内容超过渠道限制时：

1. 保留标题 + 前 N 条高相关条目。
2. 末尾追加「查看完整日报：https://agently.top」。
3. 不拆成多条消息，避免打扰。

### 3.6 迁移路径

- `email_builder.py` → 调用 `HtmlRenderer.render(..., channel="email")`，再包邮件头。
- `wechat_article_builder.py` → 调用 `MarkdownRenderer.render(..., channel="wechat")`。
- 老文件保留 1 个版本作为 facade。

---

## 4. A1：RSS 输入源

### 4.1 设计目标

让用户可以在配置里添加任意 RSS/Atom 源，项目把它当成普通源处理，经 AI 摘要后进入统一分发流程。

### 4.2 默认推荐源（国内可访问）

参考 aihot.today 的源组合，默认内置国内友好 RSS：

```yaml
rss:
  enabled: true
  global_max_age_days: 3
  sources:
    - id: "qbitai"
      name: "量子位"
      url: "https://www.qbitai.com/feed"
      category: "ai-news"
      max_age_days: 2
      max_items: 10

    - id: "geekpark"
      name: "极客公园"
      url: "https://www.geekpark.net/rss"
      category: "tech"

    - id: "jiqizhixin"
      name: "机器之心"
      url: "https://www.jiqizhixin.com/rss"
      category: "ai-news"

    - id: "v2ex-tech"
      name: "V2EX 技术"
      url: "https://www.v2ex.com/feed/tab/tech.xml"
      category: "community"

    - id: "sspai-matrix"
      name: "少数派 Matrix"
      url: "https://sspai.com/matrix"  # 无官方 RSS，需用 HTML 解析
      category: "tech"
      use_html_parser: true

    # 海外源默认关闭，需用户自建 RSSHub 或确认可访问后开启
    - id: "arxiv-daily"
      name: "arXiv AI 论文"
      url: "https://rsshub.app/arxiv/query/AI"
      category: "paper"
      enabled: false
```

### 4.3 去重与 Freshness

1. **guid 优先去重**：RSS 条目通常有 `guid` 或 `id`。
2. **url 兜底去重**：没有 guid 时用 URL。
3. **时间过滤**：超过 `max_age_days` 的文章直接丢弃。
4. **跨源去重**：A1 阶段不做，B 阶段补充。

去重存储复用 Redis：

```python
def is_rss_item_seen(source_id: str, guid: str) -> bool:
    return redis.exists(f"rss:seen:{source_id}:{guid}")

def mark_rss_item_seen(source_id: str, guid: str, ttl_days: int = 7):
    redis.setex(f"rss:seen:{source_id}:{guid}", ttl_days * 86400, "1")
```

### 4.4 采集流程

1. 读取 `rss.sources` 配置。
2. 对每个源并发请求（限制并发数 5）。
3. 用 `feedparser` 解析 RSS/Atom。
4. 过滤：`max_age_days` + `keywords`。
5. 去重：`guid/url`。
6. 标记已见。
7. 送入 `summarize_content_items()`。
8. 按 `source_id` 归档到 `output/rss-{id}/{date}/`。

### 4.5 网络适配

- 无代理，所有源必须国内裸连可访问。
- 超时 10s，重试 2 次。
- 单个源连续失败 3 次自动禁用。
- 提供 `scripts/check_source_connectivity.py` 脚本，部署前检测源可用性。

### 4.6 错误处理

- 单个 RSS 源失败不影响整体。
- 解析异常记录原始 feed 前 500 字符。
- 失败源在前端/日志中标记为 unhealthy。

---

## 5. A2：新增信息源

### 5.1 原计划与调整后

| 原计划 | 调整后 | 原因 |
|---|---|---|
| V2EX | ✅ V2EX RSS | 国内稳定 |
| Product Hunt | ✅ 36kr 创投 + 少数派 Matrix | 国内产品/创业动态替代 |
| HuggingFace Papers | ✅ ModelScope 魔搭社区 | 国内模型开源动态 |
| arXiv | ⚠️ arXiv API（默认关闭） | 国内直连不稳定 |

### 5.2 V2EX

- 数据源：`https://www.v2ex.com/feed/tab/tech.xml`
- 方式：`feedparser` 解析 RSS
- 字段：title、url、summary、author

### 5.3 36kr 创投

- 数据源：36kr 站内栏目页面（如 `https://36kr.com/information/technology`）或其实际 RSS 地址
- 方式：优先 RSS，如无稳定 RSS 则使用 HTML 解析
- 过滤：category 为「创投」「AI」「科技」的文章
- 备注：具体 RSS URL 需在实现前实测确认，建议先用 `scripts/check_source_connectivity.py` 验证

### 5.4 少数派 Matrix

- 数据源：`https://sspai.com/matrix`
- 方式：优先 RSS，如无则复用现有 `sspai.py` 的 HTML 解析

### 5.5 ModelScope 魔搭社区

- 数据源：`https://www.modelscope.cn/headlines` 或官方 API
- 方式：HTML 解析或 API
- 价值：覆盖国内大模型开源、模型更新、数据集发布

### 5.6 arXiv（可选）

- 数据源：`http://export.arxiv.org/api/query?search_query=cs.AI&sortBy=submittedDate`
- 方式：`feedparser` 解析 arXiv API
- 默认：`enabled=false`

### 5.7 source_registry 注册

```python
SOURCE_DEFINITIONS = [
    # ... 现有源 ...
    {"id": "v2ex", "name": "V2EX", "category": "community"},
    {"id": "36kr-venture", "name": "36氪创投", "category": "business"},
    {"id": "sspai-matrix", "name": "少数派 Matrix", "category": "tech"},
    {"id": "modelscope", "name": "ModelScope", "category": "ai-model"},
    {"id": "arxiv", "name": "arXiv AI", "category": "paper", "default_enabled": False},
]
```

---

## 6. A3：国内多渠道推送

### 6.1 渠道清单

| 渠道 | 接入方式 | 优先级 | 说明 |
|---|---|---|---|
| 飞书群机器人 | Webhook | P0 | 国内团队主流 |
| 企业微信群机器人 | Webhook | P0 | 国内企业主流 |
| 钉钉群机器人 | Webhook | P0 | 国内企业主流 |
| 微信公众号模板消息 | 公众号 API | P0 | 轻量触达 |
| WPS 协作机器人 | Webhook | P1 | 办公场景 |
| QQ Bot | 官方 API / NapCat | P1 | 开发者社群 |
| 微博自动发布 | 微博开放平台 | P1 | 公开传播 |
| 个人微信 | WeChaty / ilink | P1 | 风险高，默认关闭 |
| Telegram | Bot API | P2 | 海外用户，可选 |
| Slack / Discord / LINE / Matrix | 各平台 API | P2 | 国内不稳定，暂不支持 |

### 6.2 架构

所有渠道继承 `Publisher` 基类，只负责 transport：

```python
# publishers/base.py
@dataclass
class PublishResult:
    success: bool
    channel: str
    message_id: str | None
    error: str | None

class Publisher(ABC):
    id: str
    name: str

    @abstractmethod
    async def is_enabled(self) -> bool: ...

    @abstractmethod
    async def publish(self, content: RenderedContent) -> PublishResult: ...
```

### 6.3 各 Publisher 要点

#### 飞书

- 调用 Webhook，msg_type = `interactive`。
- 需要 `timestamp + secret` HMAC-SHA256 签名。
- 渲染器生成 Feishu Card JSON。

#### 企业微信

- Webhook，msgtype = `markdown`。
- 企业微信 markdown 子集有限，渲染器需适配。

#### 钉钉

- Webhook，msgtype = `markdown` / `action_card`。
- 需要签名验证。

#### 微信公众号模板消息

- 调用公众号模板消息 API。
- 模板示例：来源、标题、摘要。
- 点击跳转网页版完整日报。

#### QQ Bot

- 官方 QQ Bot HTTP API 或 NapCat/OneBot WebSocket。
- 发布到指定群。

#### 微博

- 微博开放平台 API。
- 发布图文/链接微博。

#### WPS 协作

- Webhook 推送。

### 6.4 发布编排

```python
# publish_service.py
async def publish_daily():
    items = await content_store.get_latest_items()
    rendered = {
        "email": html_renderer.render(items, "email"),
        "wechat": markdown_renderer.render(items, "wechat"),
        "feishu": feishu_card_renderer.render(items, "feishu"),
        "wechat_work": markdown_renderer.render(items, "wechat_work"),
        "dingtalk": markdown_renderer.render(items, "dingtalk"),
        # ... 其他渠道
    }

    for publisher in registry.get_enabled_publishers():
        content = rendered[publisher.id]
        result = await publisher.publish(content)
        logger.info(f"published to {publisher.id}: {result.success}")
```

### 6.5 错误处理

- 单个渠道失败不影响其他渠道。
- 每个渠道独立重试 3 次。
- 失败后记录日志，可在前端/管理后台查看。

---

## 7. 错误处理与降级策略

### 7.1 源层

- 单个源失败：记录 warning，不影响整体。
- 连续失败 3 次：自动标记 unhealthy，下次跳过。
- 每天尝试恢复一次 unhealthy 源。

### 7.2 渲染层

- HTML/Markdown 渲染失败：fallback 到纯文本。
- 超长内容：自动截断并附加完整日报链接。

### 7.3 渠道层

- 单个渠道失败：不影响其他渠道。
- 重试 3 次后放弃，记录错误。

---

## 8. 测试策略

### 8.1 单元测试

- 每个 spider：用 `pytest` + `responses`/`aioresponses` mock HTTP。
- 每个 renderer：快照测试，确保输出稳定。
- 每个 publisher：mock 对应平台 API。

### 8.2 集成测试

- 本地启动 Redis + API，跑完整采集→渲染→发布流程。
- 使用测试频道/测试群验证各渠道。

### 8.3 回归测试

- 现有邮件和微信公众号输出与原版 diff 一致。
- 单源失败不影响整体。

---

## 9. 里程碑与排期

| 阶段 | 内容 | 预估工时 | 依赖 |
|---|---|---|---|
| A5 | 统一渲染层 + 现有渠道迁移 | 5d | 无 |
| A1 | RSS 输入源 + 国内默认源 | 4d | 无 |
| A2 | V2EX / 36kr / 少数派 Matrix / ModelScope / arXiv 可选 | 5d | 无 |
| A3 | 飞书 / 企业微信 / 钉钉 / 公众号模板消息 | 5d | A5 |
| A3+ | QQ Bot / 微博 / WPS 协作 / Telegram | 5d | A5 |
| 联调 & 测试 | 全链路集成测试、文档、部署脚本 | 4d | 以上全部 |

**Milestone A 总计：约 4 周（单人全速）**。

---

## 10. 参考仓库

- [TrendRadar](https://github.com/sansan0/TrendRadar)：渠道格式指南、超长消息分批、多渠道推送、AI 兴趣筛选。
- [newsnow](https://github.com/ourongxing/newsnow)：实时热榜架构、MCP Server、源管理。
- [CloudFlare-AI-Insight-Daily](https://github.com/justlovemaki/CloudFlare-AI-Insight-Daily)：信息源组合（论文/社媒/开源/新闻）。
- [hacker-news-digest](https://github.com/polyrabbit/hacker-news-digest)：HN 摘要、配图、RSS、GitHub Pages 部署。
- [github-trending-spider](https://github.com/wenbochang888/github-trending-spider)：与当前项目架构相似的 Skill 设计。
- [cc-connect](https://github.com/chenhg5/cc-connect/blob/main/README.zh-CN.md)：国内聊天平台接入参考（企业微信、钉钉、飞书、QQ、WPS 协作、微博、个人微信）。
- [aihot.today](https://aihot.today/)：源组合参考（量子位、极客公园、36kr、TechCrunch、arXiv 等）。

---

## 11. 风险与待决策

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| 36kr / 少数派 Matrix RSS 不稳定 | A2 延迟 | 准备 HTML 解析 fallback |
| 企业微信/钉钉 webhook 签名规则变更 | A3 需要更新 | 抽象签名逻辑，便于维护 |
| 个人微信协议风险 | 封号 | 默认关闭，文档提示风险 |
| arXiv 国内访问不稳定 | A2 可选源不可用 | 默认关闭，用户自建 RSSHub |
| 前端 App.vue 已接近 2000 行 | A5 后前端改造困难 | B 阶段拆分组件 |

---

## 12. 验收标准

- [ ] 用户可配置 RSS 源，次日看到中文摘要卡片。
- [ ] V2EX、36kr、少数派 Matrix、ModelScope 在国内无代理服务器稳定采集。
- [ ] 飞书、企业微信、钉钉可发送测试消息。
- [ ] 微信公众号模板消息可发送。
- [ ] 现有邮件和微信公众号文章输出与原版本一致。
- [ ] 单个源或渠道失败不影响整体。
- [ ] 渲染层单元测试覆盖率 ≥80%。
