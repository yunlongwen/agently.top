# AI 后端专项信息源 Spider

每日自动爬取 GitHub Trending、Hacker News、TLDR AI、OpenAI、Anthropic 和 InfoQ AI Development，通过 AI 生成中文总结，合并为 HTML 邮件，并输出统一 JSON 文件供后续后端落 Redis 使用。

## 功能

- 爬取 GitHub Trending **每日热点** 和 **每周热点** (默认各 Top 10)
- 爬取 **Hacker News Top 10** 热门帖子及评论 (通过官方 Firebase API)
- 爬取 **TLDR AI 最新一期** 精选内容 (通过官方归档页)
- 爬取 **OpenAI News** 官方最新内容
- 爬取 **Anthropic Newsroom** 官方最新内容
- 爬取 **InfoQ AI Development** 最新工程实践内容 (优先 RSS)
- 通过 GitHub Models API (GPT-4o) 生成中文总结
- GitHub 总结：项目功能、特点、适用场景
- HN 总结：帖子主题 + 评论区核心观点/争议点
- TLDR AI 总结：英文 AI 快讯转为面向后端/AI 工程师的中文整理
- OpenAI / Anthropic / InfoQ 总结：中文摘要 + 后端工程师关注点
- 生成 HTML 表格邮件，支持多收件人
- 生成统一 JSON：默认 `output/latest.json`
- 六个信息源独立容错，任一成功即发送邮件并输出 JSON
- 支持 crontab 定时执行

## 部署

### 1. 克隆 & 安装

```bash
git clone https://github.com/wenbochang888/github-trending-spider.git
cd github-trending-spider
pip3 install -r requirements.txt
```

### 2. 配置环境变量

编辑 `~/.bash_profile`，在末尾追加：

```bash
# AI Backend Sources Spider
export GITHUB_TOKEN="ghp_你的token"
export SMTP_USER="changwenbo141@163.com"
export SMTP_PASSWORD="你的163授权码"
export MAIL_TO="727987105@qq.com"
```

生效：

```bash
source ~/.bash_profile
```

> GitHub Token 获取：https://github.com/settings/tokens -> Generate new token -> 勾选 `models:read`

### 3. 测试

```bash
python3 main.py
```

收到邮件并生成 `output/latest.json` 就说明成功。日志在 `/root/logs/github-python/trending.log`。

### 4. 定时任务

```bash
crontab -e
```

加一行：

```
0 8 * * * source ~/.bash_profile && cd /root/work/workspace/gitee/github-trending-spider && /usr/bin/python3 main.py
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
├── email_builder.py     # HTML 邮件模板生成
├── email_sender.py      # SMTP 邮件发送
├── config.py            # 配置中心（从环境变量读取）
├── test_email.py        # SMTP 邮件发送测试
├── requirements.txt     # Python 依赖
└── README.md            # 本文件
```

## 可选配置项

以下配置均有默认值，通过环境变量覆盖：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `GITHUB_TRENDING_TOP_COUNT` | 10 | GitHub Daily/Weekly 各获取前 N 个仓库 |
| `HN_TOP_COUNT` | 10 | HN 获取前 N 个热门帖子 |
| `HN_COMMENTS_PER_STORY` | 10 | 每帖获取前 N 条顶级评论 |
| `HN_MAX_RETRIES` | 5 | HN 请求最大重试次数 |
| `HN_CONCURRENT_WORKERS` | 10 | 并发请求线程数 |
| `TLDR_AI_HOME_URL` | https://ai.tldr.tech/ | TLDR AI 官方归档页 |
| `TLDR_AI_TOP_COUNT` | 10 | TLDR AI 获取前 N 条精选内容 |
| `TLDR_AI_MAX_RETRIES` | 5 | TLDR AI 请求最大重试次数 |
| `OPENAI_NEWS_URL` | https://openai.com/news/ | OpenAI 官方新闻页 |
| `OPENAI_NEWS_RSS_URL` | https://openai.com/news/rss.xml | OpenAI 官方新闻 RSS |
| `OPENAI_NEWS_COUNT` | 10 | OpenAI 获取前 N 条内容 |
| `ANTHROPIC_NEWS_URL` | https://www.anthropic.com/news | Anthropic 官方新闻页 |
| `ANTHROPIC_NEWS_COUNT` | 10 | Anthropic 获取前 N 条内容 |
| `INFOQ_AI_RSS_URL` | https://feed.infoq.com/ai-development/news | InfoQ AI Development 单个 RSS（兼容旧配置） |
| `INFOQ_AI_PAGE_URL` | https://www.infoq.com/ai-development/ | InfoQ AI Development 页面 |
| `INFOQ_AI_RSS_URLS` | 多个 InfoQ AI 相关 feed | InfoQ 聚合 RSS 列表 |
| `INFOQ_AI_NEWS_COUNT` | 10 | InfoQ 获取前 N 条内容 |
| `OFFICIAL_AI_MAX_RETRIES` | 5 | 官方 AI 信息源请求最大重试次数 |
| `OUTPUT_JSON_PATH` | output/latest.json | 统一 JSON 输出路径 |
| `AI_MODEL` | gpt-4o | AI 模型 |

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

当前阶段不直接写 Redis。后续后端可以读取该 JSON 后写入 Redis，也可以将 `write_content_json` 替换为 Redis writer。

## 故障排查

```bash
# 查看日志
cat /root/logs/github-python/trending.log

# 检查环境变量是否生效
echo $GITHUB_TOKEN
echo $SMTP_PASSWORD
```
