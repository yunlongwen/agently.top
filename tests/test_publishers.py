# -*- coding: utf-8 -*-
"""
发布器插件与发布服务单元测试。
"""

import os
import sys
import unittest
from datetime import datetime

# 避免启动 scheduler / Redis
os.environ.setdefault("SPIDER_SCHEDULER_ENABLED", "false")
os.environ.setdefault("STATS_ENABLED", "false")
os.environ.setdefault("PUBLISH_ENABLED", "false")
os.environ.setdefault("WECHAT_PUBLISH_ENABLED", "false")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/99")

from publishers import registry
from publishers.base import Publisher
from publishers.wechat.config import WechatConfig
from publishers.wechat.renderer import WechatRenderer
from builders.wechat_article_builder import build_daily_markdown
from infrastructure.cover_generator import _draw_text_cover, _validate_hex, _is_dark


class DummyPublisher(Publisher):
    """测试用发布器。"""

    def __init__(self):
        self.published = []

    @property
    def id(self):
        return "dummy"

    @property
    def name(self):
        return "Dummy"

    def is_enabled(self):
        return True

    def publish(self, content, options=None):
        self.published.append({"content": content, "options": options or {}})
        return {"success": True, "publisher": self.id}


class TestPublisherFramework(unittest.TestCase):

    def setUp(self):
        # 清空注册表，避免其他测试影响
        registry._publishers.clear()

    def tearDown(self):
        registry._publishers.clear()

    def test_register_and_get(self):
        p = DummyPublisher()
        registry.register(p)
        self.assertEqual(registry.get("dummy"), p)
        self.assertEqual(len(registry.list_enabled()), 1)

    def test_auto_discover_wechat(self):
        registry.auto_discover("publishers")
        self.assertIn("wechat", [p.id for p in registry.list_all()])
        # 未配置凭证，不应启用
        self.assertEqual(len(registry.list_enabled()), 0)


class TestWechatRenderer(unittest.TestCase):

    def test_convert_basic(self):
        renderer = WechatRenderer()
        html = renderer.convert("# Title\n\nParagraph with `code`.")
        self.assertIn("Title", html)
        self.assertIn("<code", html)
        self.assertIn("#07C160", html)

    def test_convert_table(self):
        renderer = WechatRenderer()
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        html = renderer.convert(md)
        self.assertIn("<table", html)
        self.assertIn("<td", html)


class TestWechatConfig(unittest.TestCase):

    def test_is_valid(self):
        cfg = WechatConfig(app_id="x", app_secret="y")
        self.assertTrue(cfg.is_valid())

        cfg2 = WechatConfig(app_id="", app_secret="")
        self.assertFalse(cfg2.is_valid())


class TestArticleBuilder(unittest.TestCase):

    def test_build_daily_markdown(self):
        items = [
            {
                "source": "github-daily",
                "category": "开源趋势-每日热点",
                "title": "Test Repo",
                "url": "https://github.com/test/repo",
                "published_at": "2026-06-20",
                "original_summary": "summary",
                "chinese_summary": "中文摘要",
                "backend_focus": "后端看点",
                "meta": {},
            }
        ]
        md = build_daily_markdown(items, "2026-06-20")
        self.assertIn("Test Repo", md)
        self.assertIn("中文摘要", md)
        self.assertIn("后端看点", md)
        self.assertIn("https://github.com/test/repo", md)


class TestCoverGenerator(unittest.TestCase):

    def test_validate_hex(self):
        self.assertEqual(_validate_hex("#07C160"), "#07C160")
        self.assertEqual(_validate_hex("invalid"), "#07C160")
        self.assertEqual(_validate_hex("#07C16", "#FFFFFF"), "#FFFFFF")

    def test_is_dark(self):
        self.assertTrue(_is_dark("#0A0A0A"))
        self.assertFalse(_is_dark("#FFFFFF"))

    def test_draw_text_cover(self):
        image_bytes = _draw_text_cover(
            title="Agently.top 每日 AI 资讯",
            date_text="2026-06-20",
            keyword="AI日报",
            primary_color="#07C160",
            background_color="#0A0A0A",
        )
        self.assertGreater(len(image_bytes), 1000)
        # 简单校验 JPEG 文件头
        self.assertTrue(image_bytes.startswith(b"\xff\xd8"))


if __name__ == "__main__":
    unittest.main()
