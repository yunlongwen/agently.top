def test_source_spider_abstract():
    from sources.base import SourceSpider
    import inspect
    assert inspect.isabstract(SourceSpider)


def test_rss_spider_parses_feed():
    import datetime as dt
    from unittest.mock import patch, MagicMock
    from sources.rss import RssSpider

    fake_feed = MagicMock()
    fake_feed.entries = [
        {
            "title": "Test Title",
            "link": "https://example.com/1",
            "published_parsed": (2026, 6, 20, 10, 0, 0, 0, 0, 0),
            "summary": "summary",
            "id": "guid-1",
        }
    ]

    mock_resp = MagicMock()
    mock_resp.content = b"<rss></rss>"
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.get", return_value=mock_resp):
        with patch("feedparser.parse", return_value=fake_feed):
            spider = RssSpider({
                "id": "rss-test", "name": "Test", "url": "https://example.com/feed",
                "category": "Test", "display_priority": "medium", "max_age_days": 7, "max_items": 10
            })
            items = spider.fetch()

    assert len(items) == 1
    assert items[0]["title"] == "Test Title"
