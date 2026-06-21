def test_rss_config_file_exists():
    from pathlib import Path
    assert Path("config/rss.yaml").exists()
