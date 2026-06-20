# -*- coding: utf-8 -*-
"""
分层记忆服务单元测试。
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

# 避免启动 scheduler / Redis
os.environ.setdefault("SPIDER_SCHEDULER_ENABLED", "false")
os.environ.setdefault("STATS_ENABLED", "false")
os.environ.setdefault("PUBLISH_ENABLED", "false")
os.environ.setdefault("WECHAT_PUBLISH_ENABLED", "false")
os.environ.setdefault("MEMORY_ENABLED", "true")
os.environ.setdefault("MEMORY_LLM_ENABLED", "false")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/99")

from memory_service import MemoryService


def _mock_get_redis_client():
    """测试用：模拟 Redis 不可用。"""
    return None


class TestMemoryService(unittest.TestCase):

    def setUp(self):
        # 强制使用磁盘模式，避免连接真实 Redis 超时
        import memory_service as ms_module
        self._original_get_redis_client = ms_module.get_redis_client
        ms_module.get_redis_client = _mock_get_redis_client

        self.temp_dir = tempfile.mkdtemp()
        self.service = MemoryService(output_dir=self.temp_dir, redis_client=None, enabled=True)

    def tearDown(self):
        import shutil
        import memory_service as ms_module
        ms_module.get_redis_client = self._original_get_redis_client
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_disabled_service_returns_empty(self):
        svc = MemoryService(output_dir=self.temp_dir, redis_client=None, enabled=False)
        self.assertEqual(svc.build_context([]), "")
        self.assertEqual(svc.build_memory_insights(), "")
        self.assertEqual(svc.save_daily_memory([])["saved"], [])

    def test_item_hash_stable(self):
        item = {
            "source": "openai",
            "title": "GPT-5 Released",
            "url": "https://openai.com/gpt-5",
        }
        h1 = MemoryService._item_hash(item)
        h2 = MemoryService._item_hash(item)
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 16)

    def test_extract_keywords(self):
        items = [
            {"title": "Claude API 新增 Tool Use 功能", "chinese_summary": "Anthropic 发布 Claude 3.5 更新。"},
        ]
        kws = MemoryService._extract_keywords(items)
        self.assertIn("Claude", kws)
        self.assertIn("Anthropic", kws)

    def test_jaccard_similarity(self):
        self.assertEqual(MemoryService._jaccard_similarity(set(), set()), 0.0)
        self.assertEqual(MemoryService._jaccard_similarity({"a", "b"}, {"a", "b"}), 1.0)
        self.assertEqual(MemoryService._jaccard_similarity({"a", "b"}, {"b", "c"}), 1 / 3)

    def test_save_and_load_daily_memory(self):
        date_text = "2026-06-20"
        items = [
            {
                "source": "openai",
                "title": "GPT-5 发布",
                "chinese_summary": "OpenAI 发布 GPT-5，支持多模态。",
                "url": "https://openai.com/gpt-5",
            }
        ]
        result = self.service.save_daily_memory(items, date_text=date_text)
        self.assertIn("openai", result["saved"])

        # 检查磁盘文件
        daily_file = Path(self.temp_dir) / "daily" / f"{date_text}.json"
        self.assertTrue(daily_file.exists())

    def test_topic_memory_merge_by_keywords(self):
        """相同关键词的报道应合并到同一主题。"""
        date_text = "2026-06-20"
        items = [
            {
                "source": "openai",
                "title": "GPT-5 大模型发布",
                "chinese_summary": "OpenAI 发布 GPT-5 大语言模型，支持多模态。",
                "url": "https://openai.com/gpt-5",
            },
            {
                "source": "anthropic",
                "title": "GPT-5 大模型性能评测",
                "chinese_summary": "Anthropic 分析 GPT-5 大语言模型性能表现。",
                "url": "https://anthropic.com/gpt-5-bench",
            },
        ]
        result = self.service.update_topic_memory(items, date_text=date_text)
        # 两个 item 关键词高度重合，应该合并为一个主题
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["merged"], 1)

    def test_build_context_with_history(self):
        """先保存昨日主题，再为今日 items 构建上下文。"""
        yesterday = "2026-06-19"
        today = "2026-06-20"

        # 昨日主题
        yesterday_items = [
            {
                "source": "openai",
                "title": "Claude API 更新",
                "chinese_summary": "Anthropic 更新 Claude API。",
                "url": "https://anthropic.com/claude-api",
            }
        ]
        self.service.save_daily_memory(yesterday_items, date_text=yesterday)
        self.service.update_topic_memory(yesterday_items, date_text=yesterday)

        # 今日相同主题
        today_items = [
            {
                "source": "openai",
                "title": "Claude API 再次更新",
                "chinese_summary": "Anthropic 再次更新 Claude API，新增功能。",
                "url": "https://anthropic.com/claude-api-2",
            }
        ]
        context = self.service.build_context(today_items, days=3)
        self.assertIn("Claude", context)

    def test_build_memory_insights(self):
        """跨天主题应生成趋势回顾。"""
        date1 = "2026-06-19"
        date2 = "2026-06-20"
        items = [
            {
                "source": "openai",
                "title": "GPT-5 发布",
                "chinese_summary": "OpenAI 发布 GPT-5。",
                "url": "https://openai.com/gpt-5",
            }
        ]
        self.service.save_daily_memory(items, date_text=date1)
        self.service.update_topic_memory(items, date_text=date1)
        self.service.update_topic_memory(items, date_text=date2)

        insights = self.service.build_memory_insights(days=3)
        self.assertTrue(insights)
        self.assertIn("GPT", insights)

    def test_editorial_memory(self):
        date_text = "2026-06-20"
        decisions = [
            {
                "item_hash": "abc123",
                "action": "include",
                "reason": "重要更新",
                "related_topic_id": "topic_xxx",
            }
        ]
        result = self.service.save_editorial_memory(decisions, date_text=date_text)
        self.assertTrue(result["saved"])

        editorial_file = Path(self.temp_dir) / "editorial" / f"{date_text}.json"
        self.assertTrue(editorial_file.exists())

    def test_fallback_topic_extraction_without_llm(self):
        items = [
            {"title": "Claude API 更新", "chinese_summary": "Anthropic 更新 Claude API。", "url": "https://a.com"},
            {"title": "Claude 3.5 发布", "chinese_summary": "Anthropic 发布 Claude 3.5。", "url": "https://b.com"},
        ]
        topics = self.service._fallback_topic_extraction(items)
        self.assertTrue(topics)
        # 至少有一个主题包含 Claude
        self.assertTrue(any("Claude" in t["topic"] for t in topics))


if __name__ == "__main__":
    unittest.main()
