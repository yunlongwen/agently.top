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


def test_build_all_rss_spiders_with_loaded_config():
    from sources.rss_config import load_rss_config
    from sources.rss import build_all_rss_spiders

    cfg = load_rss_config("config/sources.yaml")
    spiders = build_all_rss_spiders(cfg)

    source_ids = {spider.source_id for spider in spiders}
    # 当前网络环境可用的 RSS 源
    assert "rss-qbitai" in source_ids
    assert "rss-36kr" in source_ids
    assert "rss-solidot" in source_ids
    assert "rss-oschina" in source_ids
    # 2026-06-22 禁用：极客公园(www 443 超时)、机器之心(无 RSS 端点)、V2EX(网络不可达)
    assert "rss-geekpark" not in source_ids
    assert "rss-jiqizhixin" not in source_ids
    assert "rss-v2ex-tech" not in source_ids
    # arxiv 始终未启用
    assert "rss-arxiv" not in source_ids
