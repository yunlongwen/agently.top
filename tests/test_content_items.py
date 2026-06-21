# -*- coding: utf-8 -*-
"""Tests for content_items module."""


def test_build_all_content_items_includes_rss():
    from core.content_items import build_all_content_items
    rss_items = [
        {"source": "rss-test", "category": "c", "title": "T", "url": "https://t", "published_at": "", "original_summary": "s", "chinese_summary": "", "backend_focus": "", "meta": {}},
    ]
    items = build_all_content_items([], [], [], [], [], [], rss_items=rss_items)
    assert any(i["source"] == "rss-test" for i in items)
