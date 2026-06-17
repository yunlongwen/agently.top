# -*- coding: utf-8 -*-
"""
少数派 (sspai.com) 模块测试

覆盖：内联 RSS 解析 + 实时抓取 canary 测试。
"""

import sys
import unittest

sys.path.insert(0, ".")

from sspai import fetch_sspai_items, _parse_sspai_rss  # noqa: E402
from content_items import CATEGORY_AI_NEWS, SOURCE_SSPAI, _sspai_to_items  # noqa: E402


SAMPLE_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>少数派</title>
    <link>https://sspai.com</link>
    <description>少数派 RSS</description>
    <item>
      <title>模糊算法让图像更清晰？游戏里的「抗锯齿」到底在做什么</title>
      <link>https://sspai.com/post/110720</link>
      <description>前言随意启动一款3D游戏，打开图形设置界面，你大概率能发现一个选项——「抗锯齿」。</description>
      <pubDate>Wed, 17 Jun 2026 16:30:00 +0800</pubDate>
    </item>
    <item>
      <title>watchOS 27 首个开发者测试版一览</title>
      <link>https://sspai.com/post/110958</link>
      <description>AI 之外，watchOS 27 中还有这些新功能。</description>
      <pubDate>Wed, 17 Jun 2026 15:00:00 +0800</pubDate>
    </item>
    <item>
      <title>macOS 新版 Spotlight 实用技巧</title>
      <link>https://sspai.com/post/110999</link>
      <description>Spotlight 提速与启动器改造。</description>
      <pubDate>Wed, 17 Jun 2026 14:00:00 +0800</pubDate>
    </item>
  </channel>
</rss>
"""


class TestParseSspaiRss(unittest.TestCase):
    """_parse_sspai_rss 离线解析测试"""

    def test_parses_items(self):
        items = _parse_sspai_rss(SAMPLE_RSS_XML, "https://sspai.com/feed")
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]["title"], "模糊算法让图像更清晰？游戏里的「抗锯齿」到底在做什么")
        self.assertEqual(items[0]["url"], "https://sspai.com/post/110720")
        self.assertIn("Wed, 17 Jun 2026", items[0]["published_at"])
        self.assertIn("抗锯齿", items[0]["summary"])

    def test_skips_item_without_link(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <item>
              <title>无链接条目</title>
              <description>应被丢弃</description>
              <pubDate>Wed, 17 Jun 2026 16:30:00 +0800</pubDate>
            </item>
            <item>
              <title>有链接条目</title>
              <link>https://sspai.com/post/abc</link>
              <description>保留</description>
              <pubDate>Wed, 17 Jun 2026 15:00:00 +0800</pubDate>
            </item>
          </channel>
        </rss>"""
        items = _parse_sspai_rss(xml, "https://sspai.com/feed")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "有链接条目")

    def test_invalid_xml_returns_empty(self):
        items = _parse_sspai_rss("not xml at all", "https://sspai.com/feed")
        self.assertEqual(items, [])

    def test_html_description_stripped(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <item>
              <title>HTML 描述条目</title>
              <link>https://sspai.com/post/htmldesc</link>
              <description><![CDATA[<p>这是<strong>HTML</strong>段落<br>还有链接</p>]]></description>
              <pubDate>Wed, 17 Jun 2026 16:30:00 +0800</pubDate>
            </item>
          </channel>
        </rss>"""
        items = _parse_sspai_rss(xml, "https://sspai.com/feed")
        self.assertEqual(len(items), 1)
        # 文本应已被 BeautifulSoup 去掉 HTML 标签
        self.assertNotIn("<", items[0]["summary"])
        self.assertNotIn("strong", items[0]["summary"])


class TestFetchSspaiItemsLive(unittest.TestCase):
    """fetch_sspai_items 实时抓取 canary 测试"""

    def test_live_canary(self):
        # Live canary: hits the real sspai.com/feed
        # 如果这个测试在 CI 失败，说明 sspai RSS 入口或结构发生了变化
        items = fetch_sspai_items(count=3, max_retries=2)
        self.assertGreaterEqual(
            len(items), 1,
            "sspai.com/feed 应至少返回 1 条内容，请检查 RSS 地址或网络",
        )
        for item in items:
            self.assertTrue(item.get("title"), "每条 item 必须有非空 title")
            self.assertTrue(item.get("url"), "每条 item 必须有非空 url")
            self.assertIn("sspai.com", item["url"])


class TestSspaiToItems(unittest.TestCase):
    """_sspai_to_items 数据适配测试"""

    def test_normal_conversion(self):
        sspai_items = [{
            "title": "测试条目",
            "url": "https://sspai.com/post/1",
            "summary": "摘要内容",
            "published_at": "Wed, 17 Jun 2026 16:30:00 +0800",
            "category": "",
            "chinese_summary": "中文摘要",
            "backend_focus": "后端关注",
        }]
        items = _sspai_to_items(sspai_items)
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["source"], SOURCE_SSPAI)
        self.assertEqual(item["category"], CATEGORY_AI_NEWS)
        self.assertEqual(item["title"], "测试条目")
        self.assertEqual(item["url"], "https://sspai.com/post/1")
        self.assertEqual(item["chinese_summary"], "中文摘要")
        self.assertEqual(item["backend_focus"], "后端关注")
        self.assertEqual(item["meta"]["feed_url"], "https://sspai.com/post/1")

    def test_empty_and_none(self):
        self.assertEqual(_sspai_to_items([]), [])
        self.assertEqual(_sspai_to_items(None), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
