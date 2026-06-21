# -*- coding: utf-8 -*-
"""
统一信息源注册表。

前端、API、Redis key 和磁盘归档都使用稳定 source id。
"""

SOURCE_GITHUB_DAILY_ID = "github-daily"
SOURCE_GITHUB_WEEKLY_ID = "github-weekly"
SOURCE_HACKER_NEWS_ID = "hacker-news"
SOURCE_LINUX_DO_ID = "linux-do"
SOURCE_SSPAI_ID = "sspai"
SOURCE_TMTPOST_ID = "tmtpost"
SOURCE_OPENAI_ID = "openai"
SOURCE_ANTHROPIC_ID = "anthropic"
SOURCE_INFOQ_ID = "infoq"

SOURCE_DEFINITIONS = [
    {
        "id": SOURCE_GITHUB_DAILY_ID,
        "name": "GitHub Daily",
        "label": "GitHub 日榜",
        "content_source": "GitHub Trending Daily",
        "category": "开源趋势",
        "display_priority": "high",
    },
    {
        "id": SOURCE_GITHUB_WEEKLY_ID,
        "name": "GitHub Weekly",
        "label": "GitHub 周榜",
        "content_source": "GitHub Trending Weekly",
        "category": "开源趋势",
        "display_priority": "low",
    },
    {
        "id": SOURCE_LINUX_DO_ID,
        "name": "Linux.do",
        "label": "Linux.do 技术日报",
        "content_source": "Linux.do",
        "category": "社区讨论",
        "display_priority": "high",
    },
    {
        "id": SOURCE_HACKER_NEWS_ID,
        "name": "Hacker News",
        "label": "Hacker News",
        "content_source": "Hacker News",
        "category": "社区讨论",
        "display_priority": "high",
    },
    {
        "id": SOURCE_SSPAI_ID,
        "name": "Sspai",
        "label": "少数派",
        "content_source": "少数派",
        "category": "AI 快讯",
        "display_priority": "medium",
    },
    {
        "id": SOURCE_TMTPOST_ID,
        "name": "Tmtpost",
        "label": "钛媒体",
        "content_source": "钛媒体",
        "category": "AI 快讯",
        "display_priority": "medium",
    },
    {
        "id": SOURCE_OPENAI_ID,
        "name": "OpenAI",
        "label": "OpenAI",
        "content_source": "OpenAI",
        "category": "AI 官方更新",
        "display_priority": "low",
    },
    {
        "id": SOURCE_ANTHROPIC_ID,
        "name": "Anthropic",
        "label": "Anthropic",
        "content_source": "Anthropic",
        "category": "AI 官方更新",
        "display_priority": "low",
    },
    {
        "id": SOURCE_INFOQ_ID,
        "name": "InfoQ",
        "label": "InfoQ AI",
        "content_source": "InfoQ AI Development",
        "category": "AI 工程实践",
        "display_priority": "medium",
    },
]

SOURCE_BY_ID = {
    source["id"]: source
    for source in SOURCE_DEFINITIONS
}
SOURCE_BY_CONTENT_SOURCE = {
    source["content_source"]: source
    for source in SOURCE_DEFINITIONS
}


def get_source_by_id(source_id):
    """按稳定 source id 获取来源定义。"""
    return SOURCE_BY_ID.get(source_id)


def get_source_by_content_source(content_source):
    """按统一内容项里的 source 字段获取来源定义。"""
    return SOURCE_BY_CONTENT_SOURCE.get(content_source)
