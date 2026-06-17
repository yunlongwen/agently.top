# RSS API 使用指南

本文说明本项目对外提供的 RSS 总订阅接口如何使用，以及其他系统如何接入。

## 接口概览

RSS 接口地址：

```text
GET /api/rss.xml
```

当前线上项目页面地址：

```text
https://www.gdufe888.top/ai/
```

当前线上 RSS 订阅地址应使用：

```text
https://www.gdufe888.top/api/rss.xml
```

本接口返回标准 RSS 2.0 XML，响应类型为：

```text
application/rss+xml; charset=utf-8
```

## 数据来源

RSS 接口不会触发实时爬虫，也不会修改任何数据。它只读取当前项目已经生成好的最新快照：

1. 优先读取 Redis 中的 3 天热数据缓存。
2. Redis 不可用或没有数据时，自动降级读取磁盘归档。
3. 将所有已注册来源的最新内容合并为一个总 RSS feed。

当前总订阅会聚合项目中已注册的信息源，例如：

- GitHub Trending 日榜
- GitHub Trending 周榜
- Hacker News
- Linux.do
- V2EX
- TLDR AI
- OpenAI
- Anthropic
- InfoQ AI

如果某个来源当前没有数据，该来源会被跳过，不影响其他来源输出。

## 快速验证

本地启动 API 服务后，可以用下面的命令验证：

```bash
curl -i http://localhost:8000/api/rss.xml
```

只查看 XML 内容：

```bash
curl http://localhost:8000/api/rss.xml
```

保存为本地文件：

```bash
curl http://localhost:8000/api/rss.xml -o feed.xml
```

线上部署后，可以用下面的命令验证：

```bash
curl -i https://www.gdufe888.top/api/rss.xml
```

检查返回结果时重点看：

- HTTP 状态码是 `200`
- `Content-Type` 是 `application/rss+xml; charset=utf-8`
- 内容包含 `<rss version="2.0">`
- 内容包含 `<channel>`
- 有数据时包含多个 `<item>`

## RSS 字段说明

RSS 输出字段来自项目已有的统一内容项，不会新增爬虫字段。

| RSS 字段 | 含义 | 来源字段 |
| --- | --- | --- |
| `channel/title` | RSS 订阅标题 | 固定为 `Agently.top` |
| `channel/description` | RSS 订阅说明 | 固定为 `AI 与技术资讯聚合摘要` |
| `channel/lastBuildDate` | 本次 feed 中最新内容时间 | 各条目的发布时间或快照生成时间 |
| `item/title` | 内容标题 | `title` |
| `item/link` | 原文链接 | `url` |
| `item/description` | 内容摘要 | 优先 `chinese_summary`，为空时用 `original_summary` |
| `item/pubDate` | 发布时间 | 优先 `published_at`，无法解析时用快照 `generated_at` |
| `item/guid` | 条目唯一标识 | 优先 `url`，没有 URL 时由来源和标题生成 |
| `item/category` | 分类 | `category` 和来源展示名称 |

## 给 RSS 阅读器使用

如果使用 Feedly、Inoreader、NetNewsWire、Follow 等 RSS 阅读器，直接添加完整订阅地址即可：

```text
https://www.gdufe888.top/api/rss.xml
```

阅读器会定期请求该接口，并根据 `item/guid` 判断哪些内容是新内容。

## 给后端系统使用

其他后端系统可以把 `/api/rss.xml` 当作只读数据源，定时拉取并解析 XML。

建议接入方式：

1. 每 10 到 30 分钟拉取一次即可，不需要高频请求。
2. 使用 `item/guid` 或 `item/link` 做去重。
3. 使用 `item/pubDate` 做排序和增量判断。
4. 不要依赖 RSS 中的条目数量固定不变，来源没有数据时条目会减少。
5. 请求失败时保留上一次成功解析的数据，不要清空本地展示。

Python 示例：

```python
import feedparser

feed = feedparser.parse("https://www.gdufe888.top/api/rss.xml")

for entry in feed.entries:
    print(entry.title)
    print(entry.link)
    print(entry.get("published", ""))
    print(entry.get("summary", ""))
```

Node.js 示例：

```javascript
import Parser from "rss-parser";

const parser = new Parser();
const feed = await parser.parseURL("https://www.gdufe888.top/api/rss.xml");

for (const item of feed.items) {
  console.log(item.title);
  console.log(item.link);
  console.log(item.pubDate);
  console.log(item.contentSnippet);
}
```

## 给前端或低代码系统使用

如果前端页面、低代码平台或自动化工具支持 RSS URL，直接填写完整订阅地址：

```text
https://www.gdufe888.top/api/rss.xml
```

如果系统只支持 JSON，不建议前端直接解析 RSS XML。更推荐继续使用项目已有 JSON API：

```text
GET /api/sources
GET /api/sources/{source_id}/latest
```

RSS 更适合订阅和系统间通用集成，JSON API 更适合本项目前端精细展示。

## 常见问题

### 请求 RSS 会不会立即触发爬虫？

不会。RSS API 只读取已有快照，不触发 GitHub、HN、OpenAI、InfoQ 等来源的实时抓取。

### Redis 不可用时 RSS 会不会不可用？

通常不会。接口会沿用现有读取逻辑，Redis 不可用时降级读取磁盘归档。如果 Redis 和磁盘归档都没有数据，则返回合法的空 RSS。

### 为什么只有一个总订阅，没有单来源订阅？

第一版按简单原则只提供总订阅，方便外部系统一次接入全部信息。如果后续需要按来源订阅，可以再扩展类似 `/api/rss/{source_id}.xml` 的接口。

### RSS 里的摘要是中文吗？

优先使用项目已有的 `chinese_summary`。如果该字段为空，会回退到 `original_summary`。

### 外部系统应该用哪个字段做唯一键？

优先使用 `guid`。当前实现中，原文 URL 存在时 `guid` 等于 URL；没有 URL 时，系统会根据来源和标题生成稳定标识。

## 运维注意事项

- RSS API 是公开只读接口，部署时可以和现有 `/api/` 路由一起通过 Nginx 暴露。
- 如果外部系统请求量较大，建议在 Nginx 或网关层加短缓存，例如 1 到 5 分钟。
- 如果发现 RSS 长时间没有新内容，优先检查采集任务是否正常运行，而不是 RSS 接口本身。
- 日志中可以搜索 `[RSS]` 观察请求次数、输出来源数和条目数。
