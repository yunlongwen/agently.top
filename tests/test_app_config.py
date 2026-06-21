def test_load_app_config():
    from app_config import load_app_config, get_source_interval
    cfg = load_app_config()
    assert "frontend" in cfg
    assert "source_schedule" in cfg
    assert get_source_interval("any", "high").total_seconds() == 8 * 3600
