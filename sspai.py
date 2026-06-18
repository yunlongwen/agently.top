# -*- coding: utf-8 -*-
"""
少数派 (sspai.com) 数据获取 + 中文总结模块

通过 少数派 官方 RSS 抓取最近内容，调用 AI 生成中文摘要和后端关注点。
"""

import html
import json
import logging
import re
import time
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

from config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    SSPAI_FEED_URL,
    SSPAI_MAX_RETRIES,
    SSPAI_TOP_COUNT,
)

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.5",
}


def fetch_sspai_items(count=None, max_retries=None):
    """
    抓取 少数派 (sspai.com) RSS 最近内容。

    Args:
        count: 保留前 N 条，默认使用 SSPAI_TOP_COUNT 配置
        max_retries: 最大重试次数，默认使用 SSPAI_MAX_RETRIES 配置

    Returns:
        list[dict]: 每个 dict 包含 title, url, summary, published_at, category
    """
    if count is None:
        count = SSPAI_TOP_COUNT
    if max_retries is None:
        max_retries = SSPAI_MAX_RETRIES

    rss_text = _fetch_text(SSPAI_FEED_URL, max_retries)
    if not rss_text:
        return []

    items = _parse_sspai_rss(rss_text, SSPAI_FEED_URL)
    logger.info("少数派 RSS: 解析到 %d 条内容", len(items))
    return items[:count]


def _fetch_text(url, max_retries):
    """请求 RSS 文本，失败时按重试策略降级。"""
    for attempt in range(max_retries):
        try:
            logger.info("正在获取少数派 RSS %s (第 %d 次尝试)", url, attempt + 1)
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            logger.warning("获取少数派 RSS 失败: %s", e)
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))

    logger.error("获取少数派 RSS 失败，已达最大重试次数: %s", url)
    return ""


def _parse_sspai_rss(rss_text, source_url):
    """解析 少数派 RSS item 列表。"""
    try:
        root = ET.fromstring(rss_text)
    except ET.ParseError as e:
        logger.error("解析少数派 RSS 失败: %s", e)
        return []

    items = []
    for node in root.findall(".//item"):
        title = _clean_text(_node_text(node, "title"))
        link = _clean_text(_node_text(node, "link"))
        # sspai 同时使用 pubDate 和 dc:date，优先 pubDate
        pub_date = _clean_text(_node_text(node, "pubDate")) or _clean_text(_node_text(node, "dc:date"))
        description = _clean_html(_node_text(node, "description"))
        rss_category = _clean_text(_node_text(node, "category"))

        if not title or not link:
            continue

        items.append({
            "title": title,
            "url": link,
            "summary": description,
            "published_at": pub_date,
            "category": rss_category,
        })

    return items


def _node_text(node, child_name):
    child = node.find(child_name)
    return child.text if child is not None and child.text else ""


def _clean_text(text):
    return re.sub(r"\s+", " ", html.unescape(text or "")).strip()


def _clean_html(raw_html):
    """从 HTML 摘要中提取纯文本并截断。"""
    text = html.unescape(raw_html or "")
    soup = BeautifulSoup(text, "html.parser")
    return _limit_text(_clean_text(soup.get_text(" ", strip=True)), 500)


def _limit_text(text, max_len):
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "..."


def ai_summarize_sspai_items(items):
    """
    调用 AI 对 少数派 条目生成中文摘要和后端关注点。

    Args:
        items: 少数派 条目列表

    Returns:
        list[dict]: 每个条目新增 chinese_summary 和 backend_focus 字段
    """
    if not items:
        return items

    if not OPENAI_API_KEY:
        logger.warning("未配置 OPENAI_API_KEY，跳过少数派 AI 总结")
        for item in items:
            item["chinese_summary"] = "（未配置 AI Token，无法生成中文摘要）{}".format(
                item.get("summary", "")
            )
            item["backend_focus"] = "（未配置 AI Token，无法生成后端关注点）"
        return items

    item_lines = []
    for i, item in enumerate(items, 1):
        item_lines.append(
            "{}. 标题: {}\n   分类: {}\n   链接: {}\n   发布时间: {}\n   原文摘要: {}".format(
                i,
                item.get("title", ""),
                item.get("category", "") or "N/A",
                item.get("url", ""),
                item.get("published_at", ""),
                item.get("summary", ""),
            )
        )

    prompt = (
        "以下是少数派 (sspai.com) 的最新内容。少数派是中文科技/数字产品/效率工具社区，"
        "读者通常关注 macOS/iOS/跨平台效率、自动化、开发者工具、AI 写作与生产力。\n\n"
        "请为每条生成：\n"
        "- chinese_summary（60-100 字）：一句话说清这篇内容在讲什么 + 跟后端工程师/AI 工程师的关联\n"
        "- backend_focus（30-50 字）：对工程实践的具体启发、可借鉴的思路或工具，能落地最好\n\n"
        "写作要求：\n"
        "- 区分「真的新工具/新方法」和「产品体验式种草」，后者直接说「了解即可」\n"
        "- 跟后端/AI 工程无关的纯生活消费内容，直接在 chinese_summary 里标注「与后端工程无关」\n"
        "- backend_focus 要具体到工具名、API、配置项或工作流环节，避免空话\n\n"
        "请严格按照以下 JSON 格式返回，不要包含任何多余内容：\n"
        '{{"summaries": [{{"index": 1, "chinese_summary": "中文摘要", "backend_focus": "后端关注点"}}, ...]}}\n\n'
        "内容列表：\n{}"
    ).format("\n\n".join(item_lines))

    try:
        summaries = _call_sspai_ai_api(prompt)
        if summaries:
            for item in summaries:
                idx = item.get("index", 0) - 1
                if 0 <= idx < len(items):
                    items[idx]["chinese_summary"] = item.get("chinese_summary", "")
                    items[idx]["backend_focus"] = item.get("backend_focus", "")
    except Exception as e:
        logger.error("少数派 AI 总结失败: %s", e)

    for item in items:
        if not item.get("chinese_summary"):
            item["chinese_summary"] = "（AI 摘要生成失败）{}".format(item.get("summary", ""))
        if not item.get("backend_focus"):
            item["backend_focus"] = "（AI 后端关注点生成失败）"

    return items


def _call_sspai_ai_api(prompt, max_retries=10):
    """
    调用 OpenAI 兼容接口进行 少数派 内容总结。

    Returns:
        list[dict] | None: 解析后的 summaries 列表
    """
    headers = {
        "Authorization": "Bearer {}".format(OPENAI_API_KEY),
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "你是一个面向后端工程师的少数派内容筛选员。"
                           "你的任务是把少数派上跟后端工程、AI 工程、效率工具相关的内容"
                           "用中文整理成 30 秒能读完的速记，剔除种草、消费向文章。"
                           "请始终返回有效 JSON。",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 6000,
    }

    for attempt in range(max_retries):
        try:
            logger.info("调用 AI API 进行少数派总结 (第 %d 次尝试)...", attempt + 1)
            resp = requests.post(
                "{}/chat/completions".format(OPENAI_BASE_URL),
                headers=headers,
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            logger.info("少数派 AI 响应长度: %d 字符", len(content))
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            parsed = json.loads(content)
            return parsed.get("summaries", [])
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status == 429:
                wait = 60 * (attempt + 1)
                logger.warning("少数派 API 限流，等待 %d 秒后重试...", wait)
                time.sleep(wait)
            else:
                logger.error("少数派 AI API HTTP 错误 %d: %s", status, e)
                if attempt < max_retries - 1:
                    time.sleep(10)
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error("解析少数派 AI 响应失败: %s", e)
            if attempt < max_retries - 1:
                time.sleep(5)
        except Exception as e:
            logger.error("少数派 AI API 调用异常: %s", e)
            if attempt < max_retries - 1:
                time.sleep(10)

    return None
