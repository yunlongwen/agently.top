# -*- coding: utf-8 -*-

def test_all_sources_have_display_priority():
    from source_registry import SOURCE_DEFINITIONS
    for s in SOURCE_DEFINITIONS:
        assert "display_priority" in s
        assert s["display_priority"] in ("high", "medium", "low")
