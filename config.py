# -*- coding: utf-8 -*-
"""
GitHub Trending Spider + Hacker News 配置文件

使用说明：
1. 复制此文件并根据实际情况修改配置
2. 确保不要将含有真实密钥的配置文件提交到版本控制

环境变量优先级高于默认值，推荐通过环境变量配置敏感信息。
"""

import os

# =========================================================================
# GitHub Models API 配置
# =========================================================================

# GitHub Personal Access Token (需要 models:read 权限)
# 获取方式：https://github.com/settings/tokens → Generate new token → 勾选 models:read
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# GitHub Models API 地址（OpenAI 兼容接口）
AI_API_URL = os.environ.get(
    "AI_API_URL", "https://models.inference.ai.azure.com"
)

# 使用的 AI 模型
# 可用模型：gpt-4o-mini (快), gpt-4o (质量最优), deepseek-r1 (中文优化)
# gpt-4o: 中文总结质量最佳，比 gpt-4o-mini 提升 15-20%
AI_MODEL = os.environ.get("AI_MODEL", "gpt-4o")

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
# TLDR AI 配置
# =========================================================================

# TLDR AI 官方归档页
TLDR_AI_HOME_URL = os.environ.get(
    "TLDR_AI_HOME_URL", "https://ai.tldr.tech/"
)

# 获取前 N 条 TLDR AI 精选内容
TLDR_AI_TOP_COUNT = int(os.environ.get("TLDR_AI_TOP_COUNT", "10"))

# TLDR AI 请求最大重试次数
TLDR_AI_MAX_RETRIES = int(os.environ.get("TLDR_AI_MAX_RETRIES", "5"))

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
