# -*- coding: utf-8 -*-
"""
Markdown 渲染器实现。

将统一信息项列表渲染为 Markdown 格式，支持按来源分组、
AI 摘要展示、后端看点。每条不再带「阅读原文」链接，
跳转链接由发布渠道（如微信公众号）通过底部"阅读原文"或
其他渠道机制承载。
"""

import logging
from datetime import datetime
from typing import Any

from renderers.base import Renderer, RenderedContent

logger = logging.getLogger(__name__)


class MarkdownRenderer(Renderer):
    """Markdown 格式渲染器。"""

    def render(self, items: list[dict], channel: str = "markdown", options: dict[str, Any] | None = None) -> RenderedContent:
        """
        渲染信息项为 Markdown 格式。

        Args:
            items: 统一信息项列表。
            channel: 目标发布渠道标识。
            options: 可选配置项，支持：
                - date_text: 日期文本，默认使用当前日期。
                - title: 自定义标题，默认生成 "Agently 每日速览 · {date_text}"。
                - memory_insights: 可选的近期趋势回顾文本。

        Returns:
            RenderedContent: 渲染后的 Markdown 内容。
        """
        options = options or {}
        date_text = options.get("date_text") or datetime.now().strftime("%Y-%m-%d")
        title = options.get("title") or f"Agently 每日速览 · {date_text}"

        lines = [f"# {title}", ""]
        lines.append(
            "> 每天自动聚合 GitHub Trending、Hacker News、国内 AI 媒体等高质量信息源，"
            "由 AI 生成中文摘要，帮助你快速掌握前沿动态。"
        )
        lines.append("")

        if options.get("memory_insights"):
            lines.append(options["memory_insights"])
            lines.append("")

        grouped = {}
        for item in items or []:
            source = item.get("source", "unknown")
            grouped.setdefault(source, []).append(item)

        for source_id, source_items in grouped.items():
            lines.append(f"## {source_id}")
            lines.append("")
            for idx, item in enumerate(source_items, 1):
                title_item = (item.get("title") or "无标题").strip()
                url = (item.get("url") or "").strip()
                summary = (item.get("chinese_summary") or item.get("original_summary") or "").strip()
                backend_focus = (item.get("backend_focus") or "").strip()
                lines.append(f"### {idx}. {title_item}")
                if summary:
                    lines.append("")
                    lines.append(summary)
                if backend_focus and backend_focus != summary:
                    lines.append("")
                    lines.append(f"> 后端看点：{backend_focus}")
                lines.append("")

        body = "\n".join(lines)
        return RenderedContent(
            channel=channel,
            format="markdown",
            title=title,
            body=body,
            excerpt=body[:200],
            metadata={"item_count": len(items or [])},
        )
