# -*- coding: utf-8 -*-
"""
把统一信息项构建成微信公众号 Markdown 文章。
"""

import logging
from datetime import datetime

from config import WECHAT_CONTENT_MAX_LENGTH, WECHAT_MAX_ITEMS_PER_SOURCE, WECHAT_SOURCE_WHITELIST
from source_registry import SOURCE_BY_ID

logger = logging.getLogger(__name__)


def _parse_source_whitelist() -> set[str] | None:
    """解析来源白名单。"""
    value = (WECHAT_SOURCE_WHITELIST or "").strip()
    if not value:
        return None
    return {item.strip() for item in value.split(",") if item.strip()}


def build_daily_markdown(items: list[dict], date_text: str | None = None,
                         memory_insights: str | None = None) -> str:
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
    whitelist = _parse_source_whitelist()
    max_per_source = max(WECHAT_MAX_ITEMS_PER_SOURCE, 1)

    # 按来源分组并限制条数
    grouped: dict[str, list[dict]] = {}
    for item in items or []:
        source_id = item.get("source", "")
        source_def = SOURCE_BY_ID.get(source_id)
        if not source_def:
            # 尝试用 content_source 反查
            from source_registry import get_source_by_content_source
            source_def = get_source_by_content_source(source_id)
            if source_def:
                source_id = source_def["id"]

        if source_def and whitelist and source_id not in whitelist:
            continue

        grouped.setdefault(source_id, []).append(item)

    # 限制每个来源条数
    for source_id in list(grouped.keys()):
        grouped[source_id] = grouped[source_id][:max_per_source]

    # 按 SOURCE_BY_ID 顺序输出
    ordered_sources = [s["id"] for s in SOURCE_BY_ID.values()]

    lines: list[str] = []
    lines.append(f"# Agently 每日速览 · {date_text}")
    lines.append("")
    lines.append("> 📝 **原创声明**：本文内容由 Agently 平台通过 AI 技术自动聚合、摘要并生成，"
                "非商业转载，仅供技术学习参考。所有原始信息源链接已标注，"
                "版权归原作者及发布平台所有。")
    lines.append("")
    lines.append("> 每天自动聚合 GitHub Trending、Hacker News、少数派、钛媒体、OpenAI、Anthropic 等高质量 AI 信息源，"
                "由 AI 生成中文摘要，帮助你快速掌握前沿动态。")
    lines.append("")

    if memory_insights:
        lines.append(memory_insights)
        lines.append("")

    total_items = 0
    for source_id in ordered_sources:
        source_items = grouped.get(source_id, [])
        if not source_items:
            continue

        source_def = SOURCE_BY_ID.get(source_id)
        source_label = source_def["label"] if source_def else source_id
        source_category = source_def["category"] if source_def else ""

        lines.append(f"## {source_label}")
        if source_category:
            lines.append(f"<small>{source_category}</small>")
        lines.append("")

        for idx, item in enumerate(source_items, 1):
            title = item.get("title", "无标题").strip()
            url = item.get("url", "").strip()
            summary = (item.get("chinese_summary") or item.get("original_summary") or "").strip()
            backend_focus = (item.get("backend_focus") or "").strip()

            lines.append(f"### {idx}. {title}")
            if summary:
                lines.append("")
                lines.append(summary)
            if backend_focus and backend_focus != summary:
                lines.append("")
                lines.append(f"> 💬 **后端看点**：{backend_focus}")
            if url:
                lines.append("")
                lines.append(f"[阅读原文 →]({url})")
            lines.append("")
            total_items += 1

    if total_items == 0:
        lines.append("*今日暂无符合发布条件的资讯。*")

    markdown_text = "\n".join(lines)

    # 截断到最大长度
    if len(markdown_text) > WECHAT_CONTENT_MAX_LENGTH:
        logger.warning(
            "Markdown 长度 %d 超过限制 %d，已截断",
            len(markdown_text),
            WECHAT_CONTENT_MAX_LENGTH,
        )
        truncated = markdown_text[:WECHAT_CONTENT_MAX_LENGTH]
        # 尽量在段落结束后截断
        last_break = truncated.rfind("\n\n")
        if last_break > WECHAT_CONTENT_MAX_LENGTH * 0.8:
            truncated = truncated[:last_break]
        markdown_text = truncated + "\n\n*（内容过长，剩余部分已省略）*"

    return markdown_text
