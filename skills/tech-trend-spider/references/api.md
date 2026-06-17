# Tech Trend Spider API

默认 API base：`https://agently.top/api`

`https://agently.top/` 是前端页面入口，不是 API base。

## 已核验可用接口

| 用途 | 方法和路径 | 示例完整 URL |
| --- | --- | --- |
| 健康检查 | `GET /health` | `https://agently.top/api/health` |
| 来源列表 | `GET /sources` | `https://agently.top/api/sources` |
| 单来源最新快照 | `GET /sources/{source_id}/latest` | `https://agently.top/api/sources/github-daily/latest` |

## 暂不依赖的接口

| 路径 | 状态 |
| --- | --- |
| `GET /rss.xml` | 线上当前返回 404，不要在 Skill 中作为可用入口。 |

## 调用规则

- 安装方不需要本仓库源码，只需要能发起 HTTP GET 请求。
- 用户指定单个来源时，直接请求 `GET /sources/{source_id}/latest`。
- 用户指定多个来源时，逐个请求对应 latest API。
- 用户说“全部”“都看一下”时，先请求 `GET /sources` 获取 source id 列表，再逐个请求 latest API。
- `count` 和 `topic` 都在 API 返回后本地处理，不传给后端。
- API 返回什么摘要就展示什么；Skill 不重新生成摘要。
- API 返回空 `items` 时，说明该来源暂无可用快照。
