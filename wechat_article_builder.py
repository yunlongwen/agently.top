# -*- coding: utf-8 -*-
"""
把统一信息项构建成微信公众号 Markdown 文章。
"""

import logging
from datetime import datetime

from config import WECHAT_CONTENT_MAX_LENGTH, WECHAT_MAX_ITEMS_PER_SOURCE, WECHAT_SOURCE_WHITELIST
from renderers.markdown_renderer import MarkdownRenderer
from core.source_registry import SOURCE_BY_ID

logger = logging.getLogger(__name__)

_renderer = MarkdownRenderer()


def _parse_source_whitelist() -> set[str] | None:
    """解析来源白名单。"""
    value = (WECHAT_SOURCE_WHITELIST or "").strip()
    if not value:
        return None
    return {item.strip() for item in value.split(",") if item.strip()}


def _filter_items_for_publish(items: list[dict]) -> list[dict]:
    """按微信公众号白名单和每来源条数限制过滤信息项。"""
    whitelist = _parse_source_whitelist()
    max_per_source = max(WECHAT_MAX_ITEMS_PER_SOURCE, 1)

    grouped: dict[str, list[dict]] = {}
    for item in items or []:
        source_id = item.get("source", "")
        source_def = SOURCE_BY_ID.get(source_id)
        if not source_def:
            from core.source_registry import get_source_by_content_source
            source_def = get_source_by_content_source(source_id)
            if source_def:
                source_id = source_def["id"]

        if source_def and whitelist and source_id not in whitelist:
            continue

        grouped.setdefault(source_id, []).append(item)

    for source_id in list(grouped.keys()):
        grouped[source_id] = grouped[source_id][:max_per_source]

    ordered_sources = [s["id"] for s in SOURCE_BY_ID.values()]
    filtered: list[dict] = []
    for source_id in ordered_sources:
        filtered.extend(grouped.get(source_id, []))
    return filtered


def build_daily_markdown(items, date_text=None, memory_insights=None):
    """
    把统一信息项列表构建成微信公众号 Markdown。

    Args:
        items: content_items 列表。
        date_text: 日期文本，如 2026-06-20。
        memory_insights: 可选的近期趋势回顾文本。

    Returns:
        Markdown 字符串。
    """
    date_text = date_text or datetime.now().strftime("%Y-%m-%d")
    filtered = _filter_items_for_publish(items)

    rendered = _renderer.render(
        filtered,
        channel="wechat",
        options={
            "date_text": date_text,
            "memory_insights": memory_insights,
            "title": f"Agently.top 每日 AI 资讯 - {date_text}",
        },
    )
    body = rendered.body

    if len(body) > WECHAT_CONTENT_MAX_LENGTH:
        logger.warning(
            "Markdown 长度 %d 超过限制 %d，已截断",
            len(body),
            WECHAT_CONTENT_MAX_LENGTH,
        )
        truncated = body[:WECHAT_CONTENT_MAX_LENGTH]
        last_break = truncated.rfind("\n\n")
        if last_break > WECHAT_CONTENT_MAX_LENGTH * 0.8:
            truncated = truncated[:last_break]
        body = truncated + "\n\n*（内容过长，剩余部分已省略）*"

    return body
