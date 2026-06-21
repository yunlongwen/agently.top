# -*- coding: utf-8 -*-
"""Tests for dedup module."""


def test_normalize_url_strips_fragment_and_tracking():
    from dedup import normalize_url
    assert normalize_url("https://example.com/a?utm_source=x#section") == "https://example.com/a"


def test_filter_new_items():
    from dedup import filter_new_items
    items = [
        {"url": "https://example.com/a"},
        {"url": "https://example.com/b"},
    ]
    seen = {"https://example.com/a"}
    new_items = filter_new_items(items, seen=seen)
    assert len(new_items) == 1
    assert new_items[0]["url"] == "https://example.com/b"
