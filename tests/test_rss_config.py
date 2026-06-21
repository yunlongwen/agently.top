def test_rss_config_file_exists():
    from pathlib import Path
    assert Path("config/rss.yaml").exists()


def test_load_rss_config():
    from sources.rss_config import load_rss_config, list_enabled_rss_sources
    cfg = load_rss_config("config/rss.yaml")
    assert cfg["rss"]["enabled"] is True
    sources = list_enabled_rss_sources(cfg)
    assert any(s["id"] == "rss-qbitai" for s in sources)
    assert all(s.get("enabled", True) for s in sources)
