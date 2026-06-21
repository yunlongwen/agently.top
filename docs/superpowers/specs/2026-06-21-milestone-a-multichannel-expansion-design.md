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

1. **扩展信息源**：RSS 自定义输入 + 国内可访问的新源（量子位、极客公园、机器之心、36kr、Solidot、开源中国、V2EX，arXiv 可选）。
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
│   ├── rss.py                        # A1: RSS 聚合输入（含所有新增 RSS 源）
│   └── arxiv.py                      # A2: arXiv API（可选，默认关闭）
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

### 2.3 前端展示策略：优先级与折叠

#### 目标

主页按来源优先级展开显示，低优先级来源默认收起，用户点击后展开，避免信息过载。**风格必须与现有 Vue 3 卡片流保持一致**。

#### 设计原则

- **风格一致**：沿用现有配色、卡片圆角、阴影、字体、间距，不引入新设计系统。
- **配置驱动**：优先级分级、默认展开/折叠状态、分组标签全部写入配置文件，不硬编码在 Vue 组件里。
- **向后兼容**：旧版 `SOURCE_DISPLAY_MAP` 等映射表保留，新字段为扩展而非替换。

#### 配置示例

```yaml
# config.yaml
frontend:
  source_groups:
    - key: "core"
      label: "核心源"
      display_priority: "high"
      default_expanded: true
    - key: "extended"
      label: "扩展源"
      display_priority: "medium"
      default_expanded: false
    - key: "optional"
      label: "可选源"
      display_priority: "low"
      default_expanded: false
```

```python
# source_registry.py
SOURCE_DEFINITIONS = [
    {"id": "github-daily", "name": "GitHub Trending 日榜", "category": "open-source", "display_priority": "high"},
    {"id": "rss-qbitai", "name": "量子位", "category": "ai-news", "display_priority": "high"},
    {"id": "rss-geekpark", "name": "极客公园", "category": "tech", "display_priority": "medium"},
    # ...
]
```

#### 前端实现

- 前端从 `/api/sources` 读取来源列表及其 `display_priority`。
- 根据 `config.frontend.source_groups` 对来源分组并渲染折叠面板。
- 默认展开/折叠状态来自配置，用户手动状态保存在 `localStorage`。
- 首次访问按配置展开；刷新后优先使用用户历史状态。

```vue
<!-- frontend/src/App.vue 示例，风格与现有卡片一致 -->
<template>
  <div class="source-group" v-for="group in sourceGroups" :key="group.key">
    <div class="group-header" @click="toggleGroup(group.key)">
      <h2 class="text-lg font-semibold">{{ group.label }}</h2>
      <span class="toggle-icon">{{ isExpanded(group.key) ? '−' : '+' }}</span>
    </div>
    <transition name="fade">
      <div v-show="isExpanded(group.key)" class="cards-grid">
        <source-card
          v-for="source in group.sources"
          :key="source.id"
          :source="source"
        />
      </div>
    </transition>
  </div>
</template>
```

**禁止**：在模板或脚本中硬编码来源 ID、优先级、默认展开状态。

### 2.4 实时性、去重与防浪费策略

#### 1. 实时性

- **按源优先级配置采集周期**：来源按 `display_priority` 分为高/中/低三档，每档有独立默认间隔；单个源可通过 `source_schedule.overrides.{source_id}` 覆盖。
- **默认值与现有项目保持一致**：三档默认间隔均为当前项目默认间隔（8 小时，即每天 3 次），不在代码中写死具体小时数。
- **RSS 源按 published 时间触发**：每次只处理 `published_at` 在最新检查时间之后的条目。
- **前端显示"最后更新"时间戳**：让用户感知内容新鲜度。

```yaml
# config.yaml 示例
source_schedule:
  # 三挡默认间隔，默认值均等于现有项目间隔（8h），可随时整体调整
  default_intervals:
    high: 8h
    medium: 8h
    low: 8h

  # 单个源覆盖默认间隔，实现高频实时采集
  overrides:
    hacker-news: 1h
    v2ex: 1h
    linux-do: 1h
    rss-qbitai: 2h
    rss-jiqizhixin: 2h
    github-daily: 6h
    github-weekly: 1d
    rss-arxiv: 6h
```

```python
# config.py
DEFAULT_INTERVALS = config.get(
    "source_schedule.default_intervals",
    {"high": "8h", "medium": "8h", "low": "8h"}
)
OVERRIDES = config.get("source_schedule.overrides", {})


def get_source_interval(source_id: str, priority: str) -> timedelta:
    if source_id in OVERRIDES:
        return parse_interval(OVERRIDES[source_id])
    return parse_interval(DEFAULT_INTERVALS.get(priority, "8h"))
```

#### 2. 去重

- **单源去重**：基于 `guid` / `url` 在 A1 中实现。
- **跨源去重（A1 阶段基础版）**：对同一 URL 只保留一条。
- **跨源去重（B 阶段增强）**：基于标题相似度 + URL 归一化识别同一事件的不同报道。

```python
def normalize_url(url: str) -> str:
    # 移除跟踪参数、#fragment，统一 https
    ...

def is_duplicate_url(url: str) -> bool:
    return redis.sismember("global:seen_urls", normalize_url(url))
```

#### 3. 防浪费

- **无新内容不推送**：如果某次采集没有任何新条目，不向渠道发送空消息。
- **低质量过滤**：标题为空、正文过短、内容重复的条目不进入摘要流程。
- **按渠道控制频率**：每个渠道独立记录最后一次成功发布时间，避免重复推送相同批次。

```python
# publish_service.py
async def publish_daily():
    items = await content_store.get_latest_items()
    if not items:
        logger.info("no new items, skip publishing")
        return
    ...
```

#### 4. 实时性指标

- 主页显示每个来源的"X 分钟前更新"。
- 推送消息里标注"今日更新 N 条"。
- 后台记录每个源的"最新条目时间"，超过阈值标为 stale。

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

    - id: "jiqizhixin"
      name: "机器之心"
      url: "https://www.jiqizhixin.com/rss"
      category: "ai-news"

    - id: "v2ex-tech"
      name: "V2EX 技术"
      url: "https://www.v2ex.com/feed/tab/tech.xml"
      category: "community"
      fetch_interval_hours: 1

    - id: "geekpark"
      name: "极客公园"
      url: "https://www.geekpark.net/rss"
      category: "tech"
      fetch_interval_hours: 2

    # 海外源默认关闭，需用户自建 RSSHub 或确认可访问后开启
    - id: "arxiv-daily"
      name: "arXiv AI 论文"
      url: "https://rsshub.app/arxiv/query/AI"
      category: "paper"
      enabled: false
      fetch_interval_hours: 6
```

### 4.3 去重与 Freshness

1. **guid 优先去重**：RSS 条目通常有 `guid` 或 `id`。
2. **url 兜底去重**：没有 guid 时用 URL。
3. **跨源 URL 去重**：归一化 URL 后写入全局 `global:seen_urls`（见 2.4）。
4. **时间过滤**：超过 `max_age_days` 的文章直接丢弃。
5. **跨标题去重**：B 阶段补充（基于标题相似度识别同一事件的不同报道）。

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

## 5. A2：源实时性优化

### 5.1 目标

确保消息最新、实时，避免无效采集和浪费。不同源按更新频率配置不同采集周期，无新内容时不触发摘要和推送。

### 5.2 按源优先级配置采集频率

与 2.4 一致，来源按 `display_priority` 分为高/中/低三档，默认间隔均为现有项目间隔（8h），并允许按源覆盖：

```yaml
source_schedule:
  default_intervals:
    high: 8h
    medium: 8h
    low: 8h

  overrides:
    # 社区类：更新快，可配置为每小时采集
    hacker-news: 1h
    v2ex: 1h
    linux-do: 1h

    # 媒体 RSS
    rss-qbitai: 2h
    rss-jiqizhixin: 2h
    rss-geekpark: 2h
    rss-36kr: 2h
    rss-solidot: 2h
    rss-oschina: 2h

    # 日更类
    github-daily: 6h
    github-weekly: 1d
    openai: 6h
    anthropic: 6h
    infoq: 6h

    # 可选/低频
    rss-arxiv: 6h
```

### 5.3 调度器改造

当前 `scheduler.py` 是进程内定时器，默认每天 3 次。改造为支持按源独立调度：

```python
# scheduler.py
async def run_scheduler():
    for source_id, interval in SOURCE_SCHEDULE.items():
        asyncio.create_task(schedule_source(source_id, interval))

async def schedule_source(source_id: str, interval: timedelta):
    while True:
        await run_source(source_id)
        await asyncio.sleep(interval.total_seconds())
```

### 5.4 无新内容跳过

每个源采集后：

1. 对比最新条目时间 / guid / url。
2. 如果全部已存在，跳过摘要和存储。
3. 记录 "last_no_update_at"，避免频繁空跑。

```python
async def run_source(source_id: str):
    items = await fetch_source(source_id)
    new_items = [i for i in items if not is_seen(i)]
    if not new_items:
        logger.info(f"{source_id}: no new items, skip")
        return
    await summarize_and_store(new_items)
```

### 5.5 前端实时性展示

- 每个来源卡片显示 "X 分钟前更新"。
- 来源按最后更新时间排序（可选）。
- 超过 24 小时未更新的源标灰/提示 stale。

### 5.6 防浪费策略

- **不采集已禁用的源**。
- **不采集 unhealthy 源**，每天恢复检测一次。
- **不推送空内容**：publish_service 在 items 为空时直接返回。
- **控制单次摘要 Token 消耗**：单批次条目数上限，避免源爆发时成本失控。

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
| A1 | RSS 输入源 + 国内默认源（量子位/极客公园/机器之心/36kr/Solidot/开源中国/V2EX/arXiv 可选） | 4d | 无 |
| A2 | 源实时性优化：按源调度、无新内容跳过、前端实时性展示 | 3d | A1 |
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
| 36kr / 机器之心 RSS 反爬（需 UA/重定向） | A1 部分源采集失败 | feedparser 请求时带浏览器 UA，跟随 302 |
| 企业微信/钉钉 webhook 签名规则变更 | A3 需要更新 | 抽象签名逻辑，便于维护 |
| 个人微信协议风险 | 封号 | 默认关闭，文档提示风险 |
| arXiv 国内访问不稳定 | A1 可选源不可用 | 默认关闭，用户自建 RSSHub |
| 高频采集导致 API 成本上升 | A2 成本增加 | 无新内容跳过 + 单批次条目上限 |
| 前端 App.vue 已接近 2000 行 | A5 后前端改造困难 | B 阶段拆分组件，本次仅做最小改动 |

---

## 12. 验收标准

- [ ] 用户可配置 RSS 源，新增源次日可看到中文摘要卡片。
- [ ] 默认 RSS 源（量子位、极客公园、机器之心、36kr、Solidot、开源中国、V2EX）在国内无代理服务器稳定采集。
- [ ] 高频源（Hacker News / V2EX / Linux.do）支持每小时采集。
- [ ] 无新内容时跳过摘要和推送，不发送空消息。
- [ ] 主页按优先级默认展开/折叠来源，用户状态可保留。
- [ ] 飞书、企业微信、钉钉可发送测试消息。
- [ ] 微信公众号模板消息可发送。
- [ ] 现有邮件和微信公众号文章输出与原版本一致。
- [ ] 单源或渠道失败不影响整体。
- [ ] 渲染层单元测试覆盖率 ≥80%。
