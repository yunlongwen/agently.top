# -*- coding: utf-8 -*-
"""
GitHub Trending Spider + Hacker News 配置文件

使用说明：
1. 复制此文件并根据实际情况修改配置
2. 确保不要将含有真实密钥的配置文件提交到版本控制

环境变量优先级高于默认值，推荐通过环境变量配置敏感信息。
"""

import os


def _get_bool_env(name, default=False):
    """读取布尔环境变量。"""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


# =========================================================================
# AI 接口配置（OpenAI 兼容协议）
# =========================================================================

# API Key。对接自定义 OpenAI 兼容网关时使用。
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# API 基础地址，结尾不要带 /chat/completions，调用方会拼接。
OPENAI_BASE_URL = os.environ.get(
    "OPENAI_BASE_URL", "https://api.openai.com/v1"
)

# 使用的模型名，由网关支持的模型决定。
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

# 兼容旧名：未设置 OPENAI_* 时可从 GITHUB_TOKEN / AI_API_URL / AI_MODEL 读取。
if not OPENAI_API_KEY:
    OPENAI_API_KEY = os.environ.get("GITHUB_TOKEN", "")
if OPENAI_BASE_URL == "https://api.openai.com/v1":
    _legacy_base = os.environ.get("AI_API_URL")
    if _legacy_base:
        OPENAI_BASE_URL = _legacy_base
if OPENAI_MODEL == "gpt-4o-mini":
    _legacy_model = os.environ.get("AI_MODEL")
    if _legacy_model:
        OPENAI_MODEL = _legacy_model

# 旧名别名，保留以防其它模块或脚本仍按旧名 import。
GITHUB_TOKEN = OPENAI_API_KEY
AI_API_URL = OPENAI_BASE_URL
AI_MODEL = OPENAI_MODEL

# =========================================================================
# GitHub Trending 配置
# =========================================================================

# GitHub Trending 每日/每周分别获取前 N 个仓库
GITHUB_TRENDING_TOP_COUNT = int(os.environ.get("GITHUB_TRENDING_TOP_COUNT", "10"))

# =========================================================================
# 邮件配置 (163 邮箱 SMTP)
# =========================================================================

# 163 邮箱 SMTP 服务器
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.163.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
# 163 邮箱账号（发件人邮箱）
SMTP_USER = os.environ.get("SMTP_USER", "")
# 163 邮箱 SMTP 授权码（不是邮箱密码！）
# 获取方式：163邮箱 → 设置 → POP3/SMTP/IMAP → 开启 → 获取授权码
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")

# 发件人邮箱地址（通常与 SMTP_USER 相同）
MAIL_FROM = os.environ.get("MAIL_FROM", SMTP_USER)

# 收件人邮箱地址
MAIL_TO = os.environ.get("MAIL_TO", "727987105@qq.com, wenbo.chang@huolala.cn")

# 按调度时间指定收件人，JSON 对象格式：
# {"07:50":"a@example.com,b@example.com","15:50":["c@example.com"]}
MAIL_TO_BY_TIME = os.environ.get("MAIL_TO_BY_TIME", "")

# =========================================================================
# 日志配置
# =========================================================================

# 日志文件路径
LOG_FILE = os.environ.get(
    "LOG_FILE",
    "/root/logs/github-python/trending.log",
)

# =========================================================================
# Hacker News 配置
# =========================================================================

# HN 官方 Firebase API 基础地址
HN_API_BASE = os.environ.get(
    "HN_API_BASE", "https://hacker-news.firebaseio.com/v0"
)

# 获取前 N 个热门帖子
HN_TOP_COUNT = int(os.environ.get("HN_TOP_COUNT", "10"))

# 每个帖子获取前 N 条顶级评论
HN_COMMENTS_PER_STORY = int(os.environ.get("HN_COMMENTS_PER_STORY", "10"))

# HN 请求最大重试次数
HN_MAX_RETRIES = int(os.environ.get("HN_MAX_RETRIES", "5"))

# 并发请求线程数
HN_CONCURRENT_WORKERS = int(os.environ.get("HN_CONCURRENT_WORKERS", "10"))

# =========================================================================
# Linux.do 技术日报配置
# =========================================================================

# Linux.do 技术聚合日报页面。只读取该页面摘要和原帖索引，不抓取原帖正文。
LINUX_DO_NEWS_URL = os.environ.get(
    "LINUX_DO_NEWS_URL", "https://news.linuxe.top/"
)

# Linux.do 原帖卡片最多展示 N 条；0 表示全部解析到的条目。
LINUX_DO_MAX_ITEMS = int(os.environ.get("LINUX_DO_MAX_ITEMS", "0"))

# Linux.do 请求最大重试次数
LINUX_DO_MAX_RETRIES = int(os.environ.get("LINUX_DO_MAX_RETRIES", "5"))

# =========================================================================
# 少数派 (sspai.com) 配置
# =========================================================================

# 少数派 官方 RSS
SSPAI_FEED_URL = os.environ.get("SSPAI_FEED_URL", "https://sspai.com/feed")

# 少数派 获取前 N 条内容
SSPAI_TOP_COUNT = int(os.environ.get("SSPAI_TOP_COUNT", "10"))

# 少数派 请求最大重试次数
SSPAI_MAX_RETRIES = int(os.environ.get("SSPAI_MAX_RETRIES", "5"))

# =========================================================================
# 钛媒体 (tmtpost.com) 配置
# =========================================================================

# 钛媒体 官方 RSS
TMTPOST_FEED_URL = os.environ.get("TMTPOST_FEED_URL", "https://www.tmtpost.com/rss")

# 钛媒体 获取前 N 条内容
TMTPOST_TOP_COUNT = int(os.environ.get("TMTPOST_TOP_COUNT", "10"))

# 钛媒体 请求最大重试次数
TMTPOST_MAX_RETRIES = int(os.environ.get("TMTPOST_MAX_RETRIES", "5"))

# =========================================================================
# 官方 AI / AI 工程实践信息源配置
# =========================================================================

# OpenAI 官方新闻页
OPENAI_NEWS_URL = os.environ.get(
    "OPENAI_NEWS_URL", "https://openai.com/news/"
)

# OpenAI 官方新闻 RSS
OPENAI_NEWS_RSS_URL = os.environ.get(
    "OPENAI_NEWS_RSS_URL", "https://openai.com/news/rss.xml"
)

# OpenAI 获取前 N 条内容
OPENAI_NEWS_COUNT = int(os.environ.get("OPENAI_NEWS_COUNT", "10"))

# Anthropic 官方新闻页
ANTHROPIC_NEWS_URL = os.environ.get(
    "ANTHROPIC_NEWS_URL", "https://www.anthropic.com/news"
)

# Anthropic 获取前 N 条内容
ANTHROPIC_NEWS_COUNT = int(os.environ.get("ANTHROPIC_NEWS_COUNT", "10"))

# InfoQ AI Development RSS
INFOQ_AI_RSS_URL = os.environ.get(
    "INFOQ_AI_RSS_URL", "https://feed.infoq.com/ai-development/news"
)

# InfoQ AI Development 页面
INFOQ_AI_PAGE_URL = os.environ.get(
    "INFOQ_AI_PAGE_URL", "https://www.infoq.com/ai-development/"
)

# InfoQ 相关 RSS 列表。InfoQ AI Development 单个 news feed 当前条目较少，
# 所以默认聚合 AI Development / Artificial Intelligence / Generative AI。
INFOQ_AI_RSS_URLS = os.environ.get(
    "INFOQ_AI_RSS_URLS",
    "https://feed.infoq.com/ai-development/news,"
    "https://feed.infoq.com/ai-development/articles,"
    "https://feed.infoq.com/artificial_intelligence/news,"
    "https://feed.infoq.com/artificial_intelligence/articles,"
    "https://feed.infoq.com/generative-ai/news,"
    "https://feed.infoq.com/generative-ai/articles",
)

# InfoQ AI Development 获取前 N 条内容
INFOQ_AI_NEWS_COUNT = int(os.environ.get("INFOQ_AI_NEWS_COUNT", "10"))

# 官方 AI 信息源请求最大重试次数
OFFICIAL_AI_MAX_RETRIES = int(os.environ.get("OFFICIAL_AI_MAX_RETRIES", "5"))

# 统一 JSON 输出路径，后续可由后端读取后写入 Redis
OUTPUT_JSON_PATH = os.environ.get("OUTPUT_JSON_PATH", "output/latest.json")

# 按来源归档输出目录。归档结构：
# output/<source>/<YYYY-MM-DD>/<batch>.json
OUTPUT_ARCHIVE_DIR = os.environ.get("OUTPUT_ARCHIVE_DIR", "output")

# =========================================================================
# Redis / API 配置
# =========================================================================

# Redis 作为 3 天热数据缓存；磁盘归档是长期事实源。
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
REDIS_KEY_PREFIX = os.environ.get(
    "REDIS_KEY_PREFIX", "github-trending-spider"
)
REDIS_SNAPSHOT_TTL_SECONDS = int(
    os.environ.get("REDIS_SNAPSHOT_TTL_SECONDS", str(3 * 24 * 60 * 60))
)
REDIS_SOCKET_TIMEOUT_SECONDS = float(
    os.environ.get("REDIS_SOCKET_TIMEOUT_SECONDS", "2")
)

# API 单来源最多返回条数，避免公开只读接口返回过大。
API_MAX_ITEMS_PER_SOURCE = int(os.environ.get("API_MAX_ITEMS_PER_SOURCE", "100"))
API_CORS_ORIGINS = os.environ.get("API_CORS_ORIGINS", "")

# =========================================================================
# 访问统计配置（轻量自建：1x1 GIF 上报 + Redis 计数）
# =========================================================================

# 是否启用访问统计上报接口 /api/track。
STATS_ENABLED = _get_bool_env("STATS_ENABLED", True)

# 统计数据保留天数。HyperLogLog / SortedSet 会在每天凌晨 3:00 由清理任务自动回收。
STATS_RETENTION_DAYS = int(os.environ.get("STATS_RETENTION_DAYS", "30"))

# /api/stats/summary 管理接口的访问令牌。空字符串表示仅允许内网访问。
STATS_API_TOKEN = os.environ.get("STATS_API_TOKEN", "")

# 是否允许生产环境的 /api/track 被 Nginx / CDN 缓存（默认 false：每次都打后端）。
STATS_TRACK_CACHEABLE = _get_bool_env("STATS_TRACK_CACHEABLE", False)

# 内网 CIDR 列表，用于 STATS_API_TOKEN 为空时的隐式放行。
STATS_PRIVATE_CIDRS = os.environ.get(
    "STATS_PRIVATE_CIDRS",
    "127.0.0.0/8,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16",
)

# =========================================================================
# 分层记忆系统配置
# =========================================================================

# 是否启用分层记忆系统。关闭后每日生成不读取/写入记忆。
MEMORY_ENABLED = _get_bool_env("MEMORY_ENABLED", True)

# 每日趋势记忆（L1）保留天数。
MEMORY_DAILY_TTL_DAYS = int(os.environ.get("MEMORY_DAILY_TTL_DAYS", "7"))

# 主题追踪记忆（L2）保留天数。
MEMORY_TOPIC_TTL_DAYS = int(os.environ.get("MEMORY_TOPIC_TTL_DAYS", "30"))

# 编辑决策记忆（L3）保留天数。
MEMORY_EDITORIAL_TTL_DAYS = int(os.environ.get("MEMORY_EDITORIAL_TTL_DAYS", "14"))

# 注入摘要 prompt 的历史上下文最大主题数。
MEMORY_CONTEXT_MAX_TOPICS = int(os.environ.get("MEMORY_CONTEXT_MAX_TOPICS", "5"))

# 是否使用 LLM 做主题匹配（true 更准但增加调用成本）。
# false 时使用本地关键词 Jaccard 相似度降级。
MEMORY_LLM_ENABLED = _get_bool_env("MEMORY_LLM_ENABLED", False)

# 记忆数据磁盘根目录。
MEMORY_OUTPUT_DIR = os.environ.get("MEMORY_OUTPUT_DIR", "output/memory")

# =========================================================================
# 内置采集调度配置
# =========================================================================

# 启动 API 后是否启用进程内定时采集。
SPIDER_SCHEDULER_ENABLED = _get_bool_env("SPIDER_SCHEDULER_ENABLED", True)

# 每天运行时间，24 小时制，逗号分隔。
SPIDER_SCHEDULE_TIMES = os.environ.get(
    "SPIDER_SCHEDULE_TIMES", "07:50,15:50,23:50"
)

# API 启动时是否立即跑一次采集。
SPIDER_RUN_ON_STARTUP = _get_bool_env("SPIDER_RUN_ON_STARTUP", False)

# =========================================================================
# 邮件发送开关
# =========================================================================

# 默认不发送邮件；开启后仅在 EMAIL_SEND_TIMES 指定的调度时间发送。
SEND_EMAIL_ENABLED = _get_bool_env("SEND_EMAIL_ENABLED", False)

# 允许发送邮件的每日调度时间，24 小时制，逗号分隔。
# 采集仍按 SPIDER_SCHEDULE_TIMES 执行；未配置 MAIL_TO_BY_TIME 时用这里控制哪些调度批次发邮件。
EMAIL_SEND_TIMES = os.environ.get("EMAIL_SEND_TIMES", "07:50")

# =========================================================================
# 多平台发布配置
# =========================================================================

# 是否启用自动发布编排。关闭后 main.py 采集完成不会触发任何发布器。
PUBLISH_ENABLED = _get_bool_env("PUBLISH_ENABLED", False)

# 允许执行发布的每日调度时间，24 小时制，逗号分隔。
# 为空时表示跟随 SPIDER_SCHEDULE_TIMES（每次采集后都尝试发布）。
PUBLISH_SCHEDULE_TIMES = os.environ.get("PUBLISH_SCHEDULE_TIMES", "")

# 管理员 API Token，用于 /api/admin/publish/* 等管理接口鉴权。
# 为空时仅允许内网访问（同 STATS_API_TOKEN 逻辑）。
ADMIN_API_TOKEN = os.environ.get("ADMIN_API_TOKEN", "")

# =========================================================================
# 微信公众号发布配置
# =========================================================================

# 是否启用微信公众号发布。
WECHAT_PUBLISH_ENABLED = _get_bool_env("WECHAT_PUBLISH_ENABLED", False)

# 微信公众号 AppID 与 AppSecret。
WECHAT_APP_ID = os.environ.get("WECHAT_APP_ID", "")
WECHAT_APP_SECRET = os.environ.get("WECHAT_APP_SECRET", "")

# 默认文章标题、作者、摘要。标题中 {date} 会被替换为当前日期。
WECHAT_DEFAULT_TITLE = os.environ.get("WECHAT_DEFAULT_TITLE", "Agently.top 每日 AI 资讯 - {date}")
WECHAT_DEFAULT_AUTHOR = os.environ.get("WECHAT_DEFAULT_AUTHOR", "Agently")
WECHAT_DEFAULT_DIGEST = os.environ.get("WECHAT_DEFAULT_DIGEST", "")

# 默认封面图 URL（品牌背景图），用于公众号列表页展示。
# 当 WECHAT_GENERATE_COVER_BY_LLM=true 时，LLM 生成的封面会以此图为底图叠加。
WECHAT_DEFAULT_COVER_URL = os.environ.get(
    "WECHAT_DEFAULT_COVER_URL",
    "https://agently.top/agently_cover.jpg",
)
WECHAT_API_BASE_URL = os.environ.get("WECHAT_API_BASE_URL", "https://api.weixin.qq.com")

# 封面图兜底 URL，当正文无图片时使用。
WECHAT_FALLBACK_LOGO_URL = os.environ.get(
    "WECHAT_FALLBACK_LOGO_URL",
    "https://agently.top/android-chrome-192x192.png",
)

# 文末「阅读原文」跳转 URL。
# 未配置时，自动使用当日第一条资讯的 url；若当日无资讯则使用站点首页。
WECHAT_CONTENT_SOURCE_URL = os.environ.get("WECHAT_CONTENT_SOURCE_URL", "")

# 正文最大字符数限制（微信图文素材内容上限约 20000 字，这里留有余量）。
WECHAT_CONTENT_MAX_LENGTH = int(os.environ.get("WECHAT_CONTENT_MAX_LENGTH", "15000"))

# 每日发布的条目来源白名单，逗号分隔 source id；为空表示所有来源。
# 示例：github-daily,hacker-news,openai,anthropic
WECHAT_SOURCE_WHITELIST = os.environ.get("WECHAT_SOURCE_WHITELIST", "")

# 每个来源最多取 N 条用于发布。
WECHAT_MAX_ITEMS_PER_SOURCE = int(os.environ.get("WECHAT_MAX_ITEMS_PER_SOURCE", "5"))

# =========================================================================
# 封面图生成配置
# =========================================================================

# 当正文无图时，是否调用 LLM 生成封面。
WECHAT_GENERATE_COVER_BY_LLM = _get_bool_env("WECHAT_GENERATE_COVER_BY_LLM", False)

# LLM 生成封面时使用的提示词模板。
WECHAT_COVER_PROMPT_TEMPLATE = os.environ.get(
    "WECHAT_COVER_PROMPT_TEMPLATE",
    "根据以下文章标题和摘要，设计一张科技资讯日报的封面。请返回：\n"
    "1. 一句简短的视觉描述（用于图片生成提示词）\n"
    "2. 主色调 HEX（如 #07C160）\n"
    "3. 背景色 HEX（如 #0A0A0A 或 #FFFFFF）\n"
    "4. 一个 2-4 个字的封面主题词\n"
    "严格按 JSON 返回，不要多余文字：\n"
    '{"prompt": "...", "primary_color": "#07C160", "background_color": "#0A0A0A", "keyword": "AI日报"}',
)

# 图片生成 API 配置（可选）。如果配置，会优先尝试调用 /images/generations 生成真实图片。
# 留空则直接使用 Pillow 绘制文字封面。
IMAGE_GEN_API_URL = os.environ.get("IMAGE_GEN_API_URL", "")
IMAGE_GEN_API_KEY = os.environ.get("IMAGE_GEN_API_KEY", OPENAI_API_KEY)
IMAGE_GEN_MODEL = os.environ.get("IMAGE_GEN_MODEL", "dall-e-3")
IMAGE_GEN_SIZE = os.environ.get("IMAGE_GEN_SIZE", "1024x1024")

# Pillow 文字封面默认配置
COVER_IMAGE_WIDTH = int(os.environ.get("COVER_IMAGE_WIDTH", "900"))
COVER_IMAGE_HEIGHT = int(os.environ.get("COVER_IMAGE_HEIGHT", "500"))


# =========================================================================
# 采集后归档推送配置(把 output/ 镜像推送到 archive 分支)
# =========================================================================

# 是否启用采集后归档推送。默认关闭,显式开启以避免开发环境误推。
ARCHIVE_GIT_ENABLED = _get_bool_env("ARCHIVE_GIT_ENABLED", False)

# 归档分支名
ARCHIVE_GIT_BRANCH = os.environ.get("ARCHIVE_GIT_BRANCH", "archive")

# worktree 检出目录(相对仓库根)
ARCHIVE_GIT_WORKTREE = os.environ.get("ARCHIVE_GIT_WORKTREE", ".archive-worktree")

# worktree 内承载归档数据的子目录名
ARCHIVE_GIT_DIR = os.environ.get("ARCHIVE_GIT_DIR", "archive")

# 推送目标 remote
ARCHIVE_GIT_REMOTE = os.environ.get("ARCHIVE_GIT_REMOTE", "origin")
