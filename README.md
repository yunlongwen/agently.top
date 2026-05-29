# AI 后端专项信息源 Spider

每日自动爬取 GitHub Trending、Hacker News、TLDR AI、OpenAI、Anthropic 和 InfoQ AI Development，通过 AI 生成中文总结，写出统一 JSON、按来源永久归档，并写入 Redis 作为 3 天热数据缓存。项目同时提供 FastAPI 只读接口和 Vue 前端资讯流页面。

## 功能

- 爬取 GitHub Trending **每日热点** 和 **每周热点** (默认各 Top 10)
- 爬取 **Hacker News Top 10** 热门帖子及评论 (通过官方 Firebase API)
- 爬取 **TLDR AI 最新一期** 精选内容 (通过官方归档页)
- 爬取 **OpenAI News** 官方最新内容
- 爬取 **Anthropic Newsroom** 官方最新内容
- 爬取 **InfoQ AI Development** 最新工程实践内容 (优先 RSS)
- 通过 GitHub Models API (GPT-4o) 生成中文总结
- GitHub 总结：像资深同事推荐，说清痛点、对比优势、后端怎么用
- HN 总结：【主题】+【社区精华】+【争议/亮点】，具体引用评论者观点
- TLDR AI 总结：面向后端工程师的中文快报，关注工程落地和可操作行动
- OpenAI / Anthropic / InfoQ 总结：中文摘要 + 后端行动点（到 API/SDK 级别）
- 生成 HTML 表格邮件，支持多收件人
- 生成统一 JSON：默认 `output/latest.json`
- 按来源生成永久归档：`output/<source>/<YYYY-MM-DD>/<batch>.json`
- 写入 Redis 最新快照，默认 TTL 3 天
- 提供 FastAPI 只读 API，支持 Redis 缺失时降级读取磁盘最新归档
- 提供 Vue 前端工程资讯流页面
- 六个信息源独立容错，任一成功即写出 JSON、归档并刷新 Redis
- 邮件默认关闭，可通过配置开启
- 启动后端 API 后由 Python 进程内调度器定时执行采集
- API 访问日志：记录每次请求的 IP、路径、耗时、状态码
- 每小时输出访问统计：总请求数、独立 IP、热门接口、平均耗时

## 部署

### 1. 克隆 & 安装

```bash
git clone https://github.com/wenbochang888/github-trending-spider.git
cd github-trending-spider
pip3 install -r requirements.txt
```

前端依赖：

```bash
cd frontend
npm install
```

### 2. 配置环境变量

编辑 `~/.bash_profile`，在末尾追加：

```bash
# AI Backend Sources Spider
export GITHUB_TOKEN="ghp_你的token"
export SMTP_USER="changwenbo141@163.com"
export SMTP_PASSWORD="你的163授权码"
export MAIL_TO="727987105@qq.com"
export SEND_EMAIL_ENABLED=false
export REDIS_URL="redis://localhost:6379/0"
export SPIDER_SCHEDULER_ENABLED=true
export SPIDER_SCHEDULE_TIMES="07:50,15:50,23:50"
export SPIDER_RUN_ON_STARTUP=false
```

生效：

```bash
source ~/.bash_profile
```

> GitHub Token 获取：[https://github.com/settings/tokens](https://github.com/settings/tokens) -> Generate new token -> 勾选 `models:read`

### 3. 测试采集

```bash
python3 main.py
```

生成 `output/latest.json`、`output/<source>/<YYYY-MM-DD>/<batch>.json` 并刷新 Redis 就说明采集成功。日志在 `/root/logs/github-python/trending.log`。

### 4. 启动后端 API （本地调试）

```bash
python3 -m uvicorn api:app --host 0.0.0.0 --port 8000
```

启动后端后会同时启动 FastAPI 和 Python 进程内采集调度器，默认每天 `07:50`、`15:50`、`23:50` 采集一次。生产环境请保持 uvicorn 单 worker 运行，避免多个 worker 同时启动多套调度器。

### 5. 启动前端 （本地调试）

```bash
npm run serve
```

## 文件结构

```
github-trending-spider/
├── main.py              # 主入口，协调全流程
├── github_trending.py   # GitHub Trending 爬虫 + AI 总结
├── hacker_news.py       # Hacker News API 获取 + 评论抓取 + AI 总结
├── tldr_ai.py           # TLDR AI 最新一期抓取 + 中文整理
├── official_ai_sources.py # OpenAI / Anthropic / InfoQ 抓取
├── content_items.py     # 统一信息项、AI 摘要和 JSON 输出
├── content_store.py     # 按来源归档、Redis 最新快照、磁盘降级读取
├── redis_client.py      # Redis 进程级连接池
├── scheduler.py         # FastAPI 进程内采集调度器
├── source_registry.py   # 来源 ID 与展示信息注册表
├── api.py               # FastAPI 公开只读接口
├── access_log.py        # API 访问日志中间件 + 每小时统计
├── email_builder.py     # HTML 邮件模板生成
├── email_sender.py      # SMTP 邮件发送
├── config.py            # 配置中心（从环境变量读取）
├── test_email.py        # SMTP 邮件发送测试
├── frontend/            # Vue 3 + Vue CLI 前端资讯流
├── scripts/             # 后端、前端、本地联调启动脚本
├── requirements.txt     # Python 依赖
└── README.md            # 本文件
```

## 可选配置项

以下配置均有默认值，通过环境变量覆盖：


| 环境变量                         | 默认值                                                                                      | 说明                                 |
| ---------------------------- | ---------------------------------------------------------------------------------------- | ---------------------------------- |
| `GITHUB_TRENDING_TOP_COUNT`  | 10                                                                                       | GitHub Daily/Weekly 各获取前 N 个仓库     |
| `HN_TOP_COUNT`               | 10                                                                                       | HN 获取前 N 个热门帖子                     |
| `HN_COMMENTS_PER_STORY`      | 10                                                                                       | 每帖获取前 N 条顶级评论                      |
| `HN_MAX_RETRIES`             | 5                                                                                        | HN 请求最大重试次数                        |
| `HN_CONCURRENT_WORKERS`      | 10                                                                                       | 并发请求线程数                            |
| `TLDR_AI_HOME_URL`           | [https://ai.tldr.tech/](https://ai.tldr.tech/)                                           | TLDR AI 官方归档页                      |
| `TLDR_AI_TOP_COUNT`          | 10                                                                                       | TLDR AI 获取前 N 条精选内容                |
| `TLDR_AI_MAX_RETRIES`        | 5                                                                                        | TLDR AI 请求最大重试次数                   |
| `OPENAI_NEWS_URL`            | [https://openai.com/news/](https://openai.com/news/)                                     | OpenAI 官方新闻页                       |
| `OPENAI_NEWS_RSS_URL`        | [https://openai.com/news/rss.xml](https://openai.com/news/rss.xml)                       | OpenAI 官方新闻 RSS                    |
| `OPENAI_NEWS_COUNT`          | 10                                                                                       | OpenAI 获取前 N 条内容                   |
| `ANTHROPIC_NEWS_URL`         | [https://www.anthropic.com/news](https://www.anthropic.com/news)                         | Anthropic 官方新闻页                    |
| `ANTHROPIC_NEWS_COUNT`       | 10                                                                                       | Anthropic 获取前 N 条内容                |
| `INFOQ_AI_RSS_URL`           | [https://feed.infoq.com/ai-development/news](https://feed.infoq.com/ai-development/news) | InfoQ AI Development 单个 RSS（兼容旧配置） |
| `INFOQ_AI_PAGE_URL`          | [https://www.infoq.com/ai-development/](https://www.infoq.com/ai-development/)           | InfoQ AI Development 页面            |
| `INFOQ_AI_RSS_URLS`          | 多个 InfoQ AI 相关 feed                                                                      | InfoQ 聚合 RSS 列表                    |
| `INFOQ_AI_NEWS_COUNT`        | 10                                                                                       | InfoQ 获取前 N 条内容                    |
| `OFFICIAL_AI_MAX_RETRIES`    | 5                                                                                        | 官方 AI 信息源请求最大重试次数                  |
| `OUTPUT_JSON_PATH`           | output/latest.json                                                                       | 统一 JSON 输出路径                       |
| `OUTPUT_ARCHIVE_DIR`         | output                                                                                   | 按来源归档根目录                           |
| `REDIS_URL`                  | redis://localhost:6379/0                                                                 | Redis 连接地址                         |
| `REDIS_SNAPSHOT_TTL_SECONDS` | 259200                                                                                   | Redis 来源快照 TTL，默认 3 天              |
| `REDIS_KEY_PREFIX`           | github-trending-spider                                                                   | Redis key 前缀                       |
| `API_MAX_ITEMS_PER_SOURCE`   | 100                                                                                      | API 单来源最多返回条数                      |
| `API_CORS_ORIGINS`           | 空                                                                                        | API 跨域白名单，逗号分隔；同域部署可不配             |
| `SEND_EMAIL_ENABLED`         | false                                                                                    | 是否在每次采集成功后发送邮件                     |
| `SPIDER_SCHEDULER_ENABLED`   | true                                                                                     | 启动 API 后是否启用进程内定时采集                |
| `SPIDER_SCHEDULE_TIMES`      | 07:50,15:50,23:50                                                                        | 每天采集时间，24 小时制，逗号分隔                 |
| `SPIDER_RUN_ON_STARTUP`      | false                                                                                    | API 启动时是否立即采集一次                    |
| `AI_MODEL`                   | gpt-4o                                                                                   | AI 模型                              |


数量配置遵循“最多取 N 条”：例如配置 `INFOQ_AI_NEWS_COUNT=100`，但当前源只解析到 14 条，就只展示 14 条。

## 统一 JSON 输出

运行后会输出 `output/latest.json`，结构如下：

```json
{
  "generated_at": "2026-05-29T08:00:00",
  "item_count": 1,
  "items": [
    {
      "source": "OpenAI",
      "category": "AI 官方更新",
      "title": "示例标题",
      "url": "https://openai.com/news/...",
      "published_at": "May 29, 2026",
      "original_summary": "原文摘要",
      "chinese_summary": "中文摘要",
      "backend_focus": "后端工程师关注点"
    }
  ]
}
```

## 按来源归档与 Redis

每次采集会额外按来源写出批次快照：

```text
output/github-daily/2026-05-29/01.json
output/github-weekly/2026-05-29/01.json
output/hacker-news/2026-05-29/01.json
output/tldr-ai/2026-05-29/01.json
output/openai/2026-05-29/01.json
output/anthropic/2026-05-29/01.json
output/infoq/2026-05-29/01.json
```

当天多次运行时批次号递增为 `02.json`、`03.json`。磁盘归档永久保留；Redis 只保存每个来源的最新快照，默认 3 天过期。API 读取顺序是 Redis 优先，Redis 缺失或不可用时读取磁盘最新批次。

Redis URL 配置示例：

```bash
# 无密码
export REDIS_URL="redis://localhost:6379/0"

# 有密码，无用户名
export REDIS_URL="redis://:password@localhost:6379/0"

# Redis ACL 用户名 + 密码
export REDIS_URL="redis://username:password@localhost:6379/0"
```

如果密码包含 `@`、`:`、`/`、`#` 等特殊字符，需要先做 URL encode。例如 `p@ss:word` 应写成 `p%40ss%3Aword`。

Redis client 使用进程级连接池复用连接；每次 API 请求不会重新创建连接池。

## API

```bash
# 健康检查
curl http://localhost:8000/api/health

# 来源列表
curl http://localhost:8000/api/sources

# 单来源最新数据
curl http://localhost:8000/api/sources/github-daily/latest
```

第一版 API 只开放公开只读 GET 查询，不提供公开采集、写入或发邮件接口。线上建议在 Nginx 层配置限流和缓存。

## 内置定时采集

启动 `./scripts/start_backend.sh` 后，FastAPI 进程会自动启动后台调度器。默认配置为：

```bash
export SPIDER_SCHEDULER_ENABLED=true
export SPIDER_SCHEDULE_TIMES="07:50,15:50,23:50"
export SPIDER_RUN_ON_STARTUP=false
```

如需启动后立即跑一次采集，可设置：

```bash
export SPIDER_RUN_ON_STARTUP=true
```

不再需要 Linux cron。若将来要用多 worker 部署 API，需要把调度器拆成独立进程或增加分布式锁，否则多个 worker 会重复执行采集。

## 前端

前端位于 `frontend/`，技术栈为 Vue 3 + Vue CLI。开发环境下 `/api` 会代理到 `http://localhost:8000`。

页面标题为**每日AI前沿信息**，侧边栏来源标签由前端 `SOURCE_DISPLAY_MAP` 覆盖显示（不改后端注册表）：


| 来源 ID         | 侧边栏显示          |
| ------------- | -------------- |
| github-daily  | 今日开源热榜         |
| github-weekly | 本周开源精选         |
| hacker-news   | 硅谷社区热议         |
| tldr-ai       | AI 速报精选        |
| openai        | OpenAI 最新动态    |
| anthropic     | Anthropic 最新动态 |
| infoq         | AI 工程实践        |


每条内容卡片只展示标题 + 中文摘要 + 「阅读原文 →」链接。Topbar 右侧标注「⏱ 每 8 小时更新」。

```bash
cd frontend
npm install
npm run serve
```

构建：

```bash
cd frontend
npm run build
```

## 故障排查

```bash
# 查看日志
cat /root/logs/github-python/trending.log

# 查看 API 访问记录
grep "\[访问\]" /root/logs/github-python/trending.log

# 查看数据从 Redis 还是磁盘读取
grep "\[数据\]" /root/logs/github-python/trending.log

# 查看每小时统计汇总
grep "\[统计\]" /root/logs/github-python/trending.log

# 查看 Redis 降级情况
grep "磁盘归档" /root/logs/github-python/trending.log

# 查看某个 IP 的所有访问
grep "来源IP=123.45.67.89" /root/logs/github-python/trending.log

# 检查环境变量是否生效
echo $GITHUB_TOKEN
echo $SMTP_PASSWORD
```

基础编译检查：

```bash
python3 -m py_compile main.py config.py github_trending.py hacker_news.py tldr_ai.py official_ai_sources.py content_items.py content_store.py redis_client.py scheduler.py source_registry.py api.py access_log.py email_builder.py email_sender.py
```

## 线上启动与更新

### 后端后台启动

`scripts/start_backend.sh` 会自动完成加载环境变量、安装依赖、停止旧后端进程、后台启动新后端进程和日志写入。直接执行即可，不会阻塞当前终端：

```bash
cd /root/work/workspace/gitee/github-trending-spider
bash scripts/start_backend.sh
```

查看后端是否已经监听 `8000`：

```bash
ss -lntp | grep 8000
```

查看后端日志：

```bash
tail -f /root/logs/github-python/backend.out
```

### 修改后端代码后的重启步骤

```bash
cd /root/work/workspace/gitee/github-trending-spider
git pull
bash scripts/start_backend.sh
ss -lntp | grep 8000
tail -f /root/logs/github-python/backend.out
```

脚本会把应用日志写到 `/root/logs/github-python/trending.log`，把后端启动输出写到 `/root/logs/github-python/backend.out`。

### 修改前端代码后的更新步骤

前端由 Nginx 托管 `frontend/dist/`，修改前端代码后需要重新构建产物：

```bash
cd /root/work/workspace/gitee/github-trending-spider
git pull
cd frontend
npm install
npm run build
```

确认构建后的资源路径包含 `/ai/`：

```bash
cat dist/index.html
```

如果只改了前端业务代码并重新生成了 `frontend/dist/`，通常不需要重启 Nginx；刷新浏览器访问 `https://www.gdufe888.top/ai/` 即可。

### 修改 Nginx 配置后的生效步骤

只有修改 `/usr/local/nginx/conf/nginx.conf` 时，才需要测试并重新加载 Nginx：

```bash
/usr/local/nginx/sbin/nginx -t
/usr/local/nginx/sbin/nginx -s reload
```

当前线上访问链路：

```text
https://www.gdufe888.top/ai/     -> Nginx 静态托管 frontend/dist/
https://www.gdufe888.top/api/... -> Nginx 反代到 127.0.0.1:8000 FastAPI
```

