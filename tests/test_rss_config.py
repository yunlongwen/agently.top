from pathlib import Path


def test_rss_config_file_exists():
    assert Path("config/sources.yaml").exists()


def test_load_rss_config():
    from sources.rss_config import load_rss_config, list_enabled_rss_sources
    cfg = load_rss_config("config/sources.yaml")
    assert cfg["enabled"] is True
    sources = list_enabled_rss_sources(cfg)
    assert any(s["id"] == "rss-qbitai" for s in sources)
    assert all(s.get("enabled", True) for s in sources)


def test_get_rss_request_options():
    from sources.rss_config import load_rss_config, get_rss_request_options
    cfg = load_rss_config("config/sources.yaml")
    options = get_rss_request_options(cfg)
    assert options["timeout"] == 10
    assert options["retries"] == 2
    assert "User-Agent" in options["headers"]
