# -*- coding: utf-8 -*-
"""HTML 邮件生成模块

负责将 GitHub Trending、Hacker News、少数派、钛媒体 数据构建成 HTML 邮件内容。
"""

from renderers.html_renderer import HtmlRenderer

_renderer = HtmlRenderer()


def build_email_html(daily_repos, weekly_repos, hn_stories, sspai_items=None, tmtpost_items=None, content_items=None):
    """生成 HTML 邮件内容（兼容旧签名，内部使用 HtmlRenderer）。"""
    items = []
    for repo in daily_repos or []:
        items.append({
            "source": "GitHub Trending Daily",
            "title": repo.get("full_name", ""),
            "url": repo.get("url", ""),
            "chinese_summary": repo.get("ai_summary", ""),
            "backend_focus": repo.get("backend_focus", ""),
        })
    for repo in weekly_repos or []:
        items.append({
            "source": "GitHub Trending Weekly",
            "title": repo.get("full_name", ""),
            "url": repo.get("url", ""),
            "chinese_summary": repo.get("ai_summary", ""),
            "backend_focus": repo.get("backend_focus", ""),
        })
    for story in hn_stories or []:
        items.append({
            "source": "Hacker News",
            "title": story.get("title", ""),
            "url": story.get("url", ""),
            "chinese_summary": story.get("ai_summary", ""),
            "backend_focus": story.get("backend_focus", ""),
        })
    for item in sspai_items or []:
        items.append({
            "source": "少数派",
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "published_at": item.get("published_at", ""),
            "chinese_summary": item.get("chinese_summary", ""),
            "backend_focus": item.get("backend_focus", ""),
        })
    for item in tmtpost_items or []:
        items.append({
            "source": "钛媒体",
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "published_at": item.get("published_at", ""),
            "chinese_summary": item.get("chinese_summary", ""),
            "backend_focus": item.get("backend_focus", ""),
        })
    items.extend(content_items or [])

    rendered = _renderer.render(items, channel="email")
    return rendered.body
