# -*- coding: utf-8 -*-
"""
钛媒体 (tmtpost.com) 模块测试

覆盖：内联 RSS 解析 + 实时抓取 canary 测试。
"""

import sys
import unittest

sys.path.insert(0, ".")

from spiders.tmtpost import fetch_tmtpost_items, _parse_tmtpost_rss  # noqa: E402
from core.content_items import CATEGORY_AI_NEWS, SOURCE_TMTPOST, _tmtpost_to_items  # noqa: E402


SAMPLE_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>钛媒体：引领未来商业与生活新知</title>
    <link>http://www.tmtpost.com</link>
    <description>钛媒体致力于成为全球财经科技信息服务平台</description>
    <item>
      <title>OpenAI 推出 GPT-6 多模态版本</title>
      <link>https://www.tmtpost.com/8032000.html</link>
      <description>OpenAI 今日宣布 GPT-6 多模态版本正式开放 API，支持 100 万上下文。</description>
      <pubDate>Wed, 17 Jun 2026 18:00:00 +0800</pubDate>
      <dc:creator>钛媒体 AI 频道</dc:creator>
    </item>
    <item>
      <title>英伟达 Q2 财报：数据中心业务大涨</title>
      <link>https://www.tmtpost.com/8032001.html</link>
      <description>英伟达 Q2 财报超预期，数据中心业务同比增长 200%。</description>
      <pubDate>Wed, 17 Jun 2026 17:00:00 +0800</pubDate>
      <dc:creator>钛媒体 财经</dc:creator>
    </item>
    <item>
      <title>中国 AI 创业公司融资周报</title>
      <link>https://www.tmtpost.com/8032002.html</link>
      <description>本周国内 AI 创业公司累计融资 30 亿元。</description>
      <pubDate>Wed, 17 Jun 2026 16:00:00 +0800</pubDate>
    </item>
  </channel>
</rss>
"""


class TestParseTmtpostRss(unittest.TestCase):
    """_parse_tmtpost_rss 离线解析测试"""

    def test_parses_items(self):
        items = _parse_tmtpost_rss(SAMPLE_RSS_XML, "https://www.tmtpost.com/rss")
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]["title"], "OpenAI 推出 GPT-6 多模态版本")
        self.assertEqual(items[0]["url"], "https://www.tmtpost.com/8032000.html")
        self.assertIn("Wed, 17 Jun 2026", items[0]["published_at"])
        self.assertIn("GPT-6", items[0]["summary"])
        # dc:creator 应该被捕获
        self.assertEqual(items[0]["author"], "钛媒体 AI 频道")
        # 第二个条目的 author
        self.assertEqual(items[1]["author"], "钛媒体 财经")
        # 第三个条目没有 author，字段应不存在或为空
        self.assertFalse(items[2].get("author"))

    def test_skips_item_without_link(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <item>
              <title>无链接条目</title>
              <description>应被丢弃</description>
              <pubDate>Wed, 17 Jun 2026 18:00:00 +0800</pubDate>
            </item>
            <item>
              <title>有链接条目</title>
              <link>https://www.tmtpost.com/abc.html</link>
              <description>保留</description>
              <pubDate>Wed, 17 Jun 2026 17:00:00 +0800</pubDate>
            </item>
          </channel>
        </rss>"""
        items = _parse_tmtpost_rss(xml, "https://www.tmtpost.com/rss")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "有链接条目")

    def test_invalid_xml_returns_empty(self):
        items = _parse_tmtpost_rss("not xml at all", "https://www.tmtpost.com/rss")
        self.assertEqual(items, [])

    def test_html_description_stripped(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <item>
              <title>HTML 描述条目</title>
              <link>https://www.tmtpost.com/htmldesc.html</link>
              <description><![CDATA[<p>这是<strong>HTML</strong>段落<br>还有链接</p>]]></description>
              <pubDate>Wed, 17 Jun 2026 18:00:00 +0800</pubDate>
            </item>
          </channel>
        </rss>"""
        items = _parse_tmtpost_rss(xml, "https://www.tmtpost.com/rss")
        self.assertEqual(len(items), 1)
        # 文本应已被 BeautifulSoup 去掉 HTML 标签
        self.assertNotIn("<", items[0]["summary"])
        self.assertNotIn("strong", items[0]["summary"])


class TestFetchTmtpostItemsLive(unittest.TestCase):
    """fetch_tmtpost_items 实时抓取 canary 测试"""

    def test_live_canary(self):
        # Live canary: hits the real tmtpost.com/rss
        # 如果这个测试在 CI 失败，说明 tmtpost RSS 入口或结构发生了变化
        items = fetch_tmtpost_items(count=3, max_retries=2)
        self.assertGreaterEqual(
            len(items), 1,
            "tmtpost.com/rss 应至少返回 1 条内容，请检查 RSS 地址或网络",
        )
        for item in items:
            self.assertTrue(item.get("title"), "每条 item 必须有非空 title")
            self.assertTrue(item.get("url"), "每条 item 必须有非空 url")
            self.assertIn("tmtpost.com", item["url"])


class TestTmtpostToItems(unittest.TestCase):
    """_tmtpost_to_items 数据适配测试"""

    def test_normal_conversion(self):
        tmtpost_items = [{
            "title": "测试条目",
            "url": "https://www.tmtpost.com/8032000.html",
            "summary": "摘要内容",
            "published_at": "Wed, 17 Jun 2026 18:00:00 +0800",
            "category": "",
            "author": "钛媒体 AI 频道",
            "chinese_summary": "中文摘要",
            "backend_focus": "后端关注",
        }]
        items = _tmtpost_to_items(tmtpost_items)
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["source"], SOURCE_TMTPOST)
        self.assertEqual(item["category"], CATEGORY_AI_NEWS)
        self.assertEqual(item["title"], "测试条目")
        self.assertEqual(item["url"], "https://www.tmtpost.com/8032000.html")
        self.assertEqual(item["chinese_summary"], "中文摘要")
        self.assertEqual(item["backend_focus"], "后端关注")
        self.assertEqual(item["meta"]["author"], "钛媒体 AI 频道")

    def test_empty_and_none(self):
        self.assertEqual(_tmtpost_to_items([]), [])
        self.assertEqual(_tmtpost_to_items(None), [])

    def test_no_author(self):
        items = _tmtpost_to_items([{
            "title": "无作者",
            "url": "https://www.tmtpost.com/1.html",
            "summary": "s",
        }])
        self.assertNotIn("author", items[0]["meta"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
