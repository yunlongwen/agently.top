# -*- coding: utf-8 -*-
"""
Renderer 单元测试。

TDD 流程：
1. 先写失败测试（RED）
2. 实现最小代码使测试通过（GREEN）
"""

import os
import sys

# 避免启动 scheduler / Redis
os.environ.setdefault("SPIDER_SCHEDULER_ENABLED", "false")
os.environ.setdefault("STATS_ENABLED", "false")
os.environ.setdefault("PUBLISH_ENABLED", "false")
os.environ.setdefault("WECHAT_PUBLISH_ENABLED", "false")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/99")


def test_rendered_content_dataclass():
    from renderers.base import RenderedContent
    rc = RenderedContent(channel="wechat", format="markdown", title="t", body="b", excerpt="e", metadata={})
    assert rc.channel == "wechat"
    assert rc.format == "markdown"
    assert rc.title == "t"
    assert rc.body == "b"
    assert rc.excerpt == "e"
    assert rc.metadata == {}


def test_rendered_content_format_literal():
    from renderers.base import RenderedContent
    # 有效 format
    rc = RenderedContent(channel="x", format="html", title="t", body="b", excerpt="e", metadata={})
    assert rc.format == "html"
    rc2 = RenderedContent(channel="x", format="plain", title="t", body="b", excerpt="e", metadata={})
    assert rc2.format == "plain"
    rc3 = RenderedContent(channel="x", format="feishu_card", title="t", body="b", excerpt="e", metadata={})
    assert rc3.format == "feishu_card"


def test_renderer_is_abstract():
    from renderers.base import Renderer
    import inspect
    assert inspect.isabstract(Renderer)
    assert hasattr(Renderer, "render")


def test_markdown_renderer_returns_rendered_content():
    from renderers.markdown_renderer import MarkdownRenderer
    renderer = MarkdownRenderer()
    result = renderer.render([], channel="wechat")
    assert result.channel == "wechat"
    assert result.format == "markdown"
    assert "Agently" in result.title
    assert result.metadata["item_count"] == 0


def test_markdown_renderer_with_items():
    from renderers.markdown_renderer import MarkdownRenderer
    renderer = MarkdownRenderer()
    items = [
        {
            "source": "github-daily",
            "title": "Test Repo",
            "url": "https://github.com/test/repo",
            "chinese_summary": "中文摘要",
            "backend_focus": "后端看点",
        }
    ]
    result = renderer.render(items, channel="wechat")
    assert result.channel == "wechat"
    assert result.format == "markdown"
    assert "Test Repo" in result.body
    assert "中文摘要" in result.body
    assert "后端看点" in result.body
    assert "https://github.com/test/repo" in result.body
    assert result.metadata["item_count"] == 1


def test_markdown_renderer_custom_title_and_date():
    from renderers.markdown_renderer import MarkdownRenderer
    renderer = MarkdownRenderer()
    result = renderer.render([], channel="email", options={"title": "Custom Title", "date_text": "2026-06-20"})
    assert result.title == "Custom Title"
    assert "2026-06-20" not in result.title  # title is exactly as provided
    assert result.channel == "email"


def test_markdown_renderer_default_title_contains_date():
    from renderers.markdown_renderer import MarkdownRenderer
    from datetime import datetime
    renderer = MarkdownRenderer()
    result = renderer.render([], channel="wechat")
    today = datetime.now().strftime("%Y-%m-%d")
    assert f"Agently 每日速览 · {today}" == result.title


def test_markdown_renderer_memory_insights():
    from renderers.markdown_renderer import MarkdownRenderer
    renderer = MarkdownRenderer()
    result = renderer.render([], channel="wechat", options={"memory_insights": "近期趋势回顾"})
    assert "近期趋势回顾" in result.body


def test_markdown_renderer_groups_by_source():
    from renderers.markdown_renderer import MarkdownRenderer
    renderer = MarkdownRenderer()
    items = [
        {"source": "source-a", "title": "Item A1"},
        {"source": "source-b", "title": "Item B1"},
        {"source": "source-a", "title": "Item A2"},
    ]
    result = renderer.render(items, channel="wechat")
    # 来源分组标题应出现
    assert "## source-a" in result.body
    assert "## source-b" in result.body
    # 序号应从 1 开始每组内
    assert "### 1. Item A1" in result.body
    assert "### 2. Item A2" in result.body
    assert "### 1. Item B1" in result.body


def test_markdown_renderer_excerpt_is_body_prefix():
    from renderers.markdown_renderer import MarkdownRenderer
    renderer = MarkdownRenderer()
    result = renderer.render([], channel="wechat")
    assert result.excerpt == result.body[:200]


def test_markdown_renderer_no_duplicate_backend_focus():
    """backend_focus 与 summary 相同时，不应重复输出。"""
    from renderers.markdown_renderer import MarkdownRenderer
    renderer = MarkdownRenderer()
    items = [
        {
            "source": "test",
            "title": "T",
            "chinese_summary": "相同内容",
            "backend_focus": "相同内容",
        }
    ]
    result = renderer.render(items, channel="wechat")
    # 只应出现一次 "相同内容"（在 summary 中），不应出现 "后端看点"
    assert result.body.count("相同内容") == 1
    assert "后端看点" not in result.body


def test_markdown_renderer_empty_items():
    from renderers.markdown_renderer import MarkdownRenderer
    renderer = MarkdownRenderer()
    result = renderer.render(None, channel="wechat")
    assert result.metadata["item_count"] == 0
    assert "Agently" in result.title
