# -*- coding: utf-8 -*-
"""
core.source_registry 单元测试。
"""

from pathlib import Path


def test_source_definitions_loaded_from_yaml():
    from core.source_registry import SOURCE_DEFINITIONS
    ids = [s["id"] for s in SOURCE_DEFINITIONS]
    assert "github-daily" in ids
    assert "hacker-news" in ids
    assert "rss-qbitai" in ids
    assert "rss-v2ex-tech" in ids


def test_all_sources_have_display_priority():
    from core.source_registry import SOURCE_DEFINITIONS
    for s in SOURCE_DEFINITIONS:
        assert "display_priority" in s
        assert s["display_priority"] in ("high", "medium", "low")


def test_builtin_and_rss_kinds():
    from core.source_registry import SOURCE_DEFINITIONS
    kinds = {s["id"]: s["kind"] for s in SOURCE_DEFINITIONS}
    assert kinds["github-daily"] == "builtin"
    assert kinds["rss-qbitai"] == "rss"


def test_get_source_by_id():
    from core.source_registry import get_source_by_id
    source = get_source_by_id("sspai")
    assert source is not None
    assert source["category"] == "AI 快讯"


def test_get_source_by_content_source():
    from core.source_registry import get_source_by_content_source
    source = get_source_by_content_source("Linux.do")
    assert source["id"] == "linux-do"


def test_get_source_config():
    from core.source_registry import get_source_config
    assert get_source_config("hacker-news", "top_count") == 10
    assert get_source_config("infoq", "count") == 10
    assert isinstance(get_source_config("infoq", "rss_urls"), list)
    assert get_source_config("missing-source", "key", "default") == "default"
    assert get_source_config("missing-source") == {}


def test_rss_sources_have_normalized_defaults():
    from core.source_registry import SOURCE_DEFINITIONS
    rss = [s for s in SOURCE_DEFINITIONS if s["kind"] == "rss"]
    assert rss
    for s in rss:
        assert s.get("label")
        assert s.get("content_source")
        assert s.get("category")


def test_default_config_path_exists():
    assert Path("config/sources.yaml").exists()
