# -*- coding: utf-8 -*-
"""
主采集流程单元测试。
"""

import os
from unittest.mock import patch, MagicMock

os.environ.setdefault("SPIDER_SCHEDULER_ENABLED", "false")
os.environ.setdefault("STATS_ENABLED", "false")
os.environ.setdefault("PUBLISH_ENABLED", "false")
os.environ.setdefault("WECHAT_PUBLISH_ENABLED", "false")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/99")
os.environ.setdefault("SEND_EMAIL_ENABLED", "false")


def test_run_spider_calls_rss_spiders():
    # Patch 所有外部采集函数，返回空列表；仅让 GitHub daily 返回一条数据以通过空检查
    dummy_repo = {
        "full_name": "test/repo",
        "url": "https://github.com/test/repo",
        "description": "test",
        "language": "Python",
        "stars": 1,
        "forks": 0,
        "stars_period": "",
    }
    with patch("github_trending.fetch_trending", side_effect=lambda since: [dummy_repo] if since == "daily" else []):
        with patch("github_trending.ai_summarize", return_value=[dummy_repo]):
            with patch("hacker_news.fetch_hn_top_stories", return_value=[]):
                with patch("hacker_news.fetch_all_comments", return_value=[]):
                    with patch("hacker_news.ai_summarize_hn", return_value=[]):
                        with patch("linux_do_news.fetch_linux_do_daily_items", return_value=[]):
                            with patch("linux_do_news.ai_summarize_linux_do_items", return_value=[]):
                                with patch("sspai.fetch_sspai_items", return_value=[]):
                                    with patch("sspai.ai_summarize_sspai_items", return_value=[]):
                                        with patch("tmtpost.fetch_tmtpost_items", return_value=[]):
                                            with patch("tmtpost.ai_summarize_tmtpost_items", return_value=[]):
                                                with patch("official_ai_sources.fetch_openai_news", return_value=[]):
                                                    with patch("official_ai_sources.fetch_anthropic_news", return_value=[]):
                                                        with patch("official_ai_sources.fetch_infoq_ai_development", return_value=[]):
                                                            with patch("content_items.summarize_content_items", return_value=[]):
                                                                with patch("content_items.write_content_json"):
                                                                    with patch("content_store.persist_source_snapshots"):
                                                                        with patch("memory_service.MemoryService") as MockMemoryService:
                                                                            instance = MagicMock()
                                                                            instance.enabled = False
                                                                            MockMemoryService.return_value = instance
                                                                            with patch("sources.rss.build_all_rss_spiders", return_value=[]) as mock_build_all_rss_spiders:
                                                                                from main import run_spider

                                                                                result = run_spider()

                                                                                mock_build_all_rss_spiders.assert_called_once()
                                                                                assert result is True
