# -*- coding: utf-8 -*-
"""Tests for content_items module."""


def test_build_all_content_items_includes_rss():
    from core.content_items import build_all_content_items
    rss_items = [
        {"source": "rss-test", "category": "c", "title": "T", "url": "https://t", "published_at": "", "original_summary": "s", "chinese_summary": "", "backend_focus": "", "meta": {}},
    ]
    items = build_all_content_items([], [], [], [], [], [], rss_items=rss_items)
    assert any(i["source"] == "rss-test" for i in items)


def test_build_all_content_items_filters_irrelevant():
    """AI 标记为「与工程无关」的条目不应进入归档 / 邮件 / 公众号。"""
    from core.content_items import build_all_content_items

    sspai_irrelevant = [
        {"title": "纯生活消费", "url": "https://sspai/1", "summary": "x", "chinese_summary": "与工程无关", "backend_focus": "无"},
    ]
    sspai_relevant = [
        {"title": "AI 工具评测", "url": "https://sspai/2", "summary": "x", "chinese_summary": "详细介绍……", "backend_focus": "上手成本"},
    ]
    github_irrelevant = [
        {"full_name": "x/y", "html_url": "https://gh/x", "description": "原生客户端", "language": "Swift",
         "ai_summary": "macOS 原生 AI 视频编辑器", "backend_focus": "与开发工作无关"},
    ]
    rss_irrelevant = [
        {"source": "rss-x", "title": "噪音", "url": "https://rss/1",
         "original_summary": "", "chinese_summary": "与工程无关", "backend_focus": "无", "meta": {}},
    ]

    items = build_all_content_items(
        daily_repos=[],
        weekly_repos=[],
        hn_stories=[],
        sspai_items=sspai_irrelevant + sspai_relevant,
        tmtpost_items=[],
        ai_source_items=[],
        linux_do_items=[],
        rss_items=rss_irrelevant,
    )

    titles = {i["title"] for i in items}
    assert "纯生活消费" not in titles
    assert "噪音" not in titles
    assert "AI 工具评测" in titles
    # 无 github 项（被 filter 掉了）


def test_build_all_content_items_keeps_normal_items():
    """正常条目（chinese_summary 正常 + backend_focus 非「无」/非「与开发工作无关」/非负向开头）保留。"""
    from core.content_items import build_all_content_items

    sspai = [
        {"title": "A", "url": "u", "summary": "x", "chinese_summary": "正常摘要", "backend_focus": "关注点：API 升级"},
    ]
    items = build_all_content_items([], [], [], sspai, [], [], linux_do_items=[], rss_items=[])
    assert len(items) == 1
    assert items[0]["title"] == "A"


def test_is_irrelevant_negative_prefix():
    """backend_focus 以「营销大于实质」/「与工程无关」/「与开发工作无关」开头 → 过滤。"""
    from core.content_items import _is_irrelevant_item

    assert _is_irrelevant_item({"chinese_summary": "正常", "backend_focus": "营销大于实质，无需行动。本次仅是合作案例展示"})
    assert _is_irrelevant_item({"chinese_summary": "正常", "backend_focus": "与工程无关，纯桌面端工具"})
    assert not _is_irrelevant_item({"chinese_summary": "正常", "backend_focus": "本次为营销大于实质的反面案例，需要跟进"})
    assert not _is_irrelevant_item({"chinese_summary": "正常", "backend_focus": "如果内容是营销大于实质才需警惕；这里给出工程建议"})
