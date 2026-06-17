# Tech Trend Spider 来源

source id 必须与线上 `GET https://agently.top/api/sources` 返回值保持一致。

| Source id | 用户可见来源 | Latest API | 能力边界 |
| --- | --- | --- | --- |
| `github-daily` | GitHub Trending 日榜 | `GET /sources/github-daily/latest` | 读取已采集的 GitHub Trending 日榜快照，不是 GitHub 代码搜索。 |
| `github-weekly` | GitHub Trending 周榜 | `GET /sources/github-weekly/latest` | 读取已采集的 GitHub Trending 周榜快照，不是 GitHub 代码搜索。 |
| `hacker-news` | Hacker News Top Stories | `GET /sources/hacker-news/latest` | 读取已采集的 HN 热门内容快照；是否包含评论由后端采集结果决定。 |
| `linux-do` | Linux.do 技术日报 | `GET /sources/linux-do/latest` | 读取 `news.linuxe.top` 技术日报摘要和原帖索引快照，不是完整原帖抓取。 |
| `v2ex` | V2EX 热帖 | `GET /sources/v2ex/latest` | 读取已采集的 V2EX 热帖快照；是否包含回复由后端采集结果决定。 |
| `tldr-ai` | TLDR AI 最新一期 | `GET /sources/tldr-ai/latest` | 读取已采集的 TLDR AI 最新一期快照。 |
| `openai` | OpenAI News | `GET /sources/openai/latest` | 读取已采集的 OpenAI 官方新闻快照。 |
| `anthropic` | Anthropic News | `GET /sources/anthropic/latest` | 读取已采集的 Anthropic 官方 newsroom 快照。 |
| `infoq` | InfoQ AI Development | `GET /sources/infoq/latest` | 读取已采集的 InfoQ AI 相关内容快照。 |

## 本地 Topic 过滤

`topic` 过滤发生在 API 返回之后。使用关键词匹配 `items` 中的可用字段，例如标题、URL、原始摘要、中文摘要、后端关注点、内容片段，以及 `meta` 中的字符串值。

不要把它描述成源站搜索。如果用户需要真正的上游搜索，应作为单独实现需求处理。

## 不支持的产品层

不要把本 Skill 描述为以下能力：

- 直接调用本仓库 Python 模块。
- 直接爬取源站。
- 触发后端重新采集。
- 发送邮件或管理调度。
- 管理 Redis、归档、前端或部署。
