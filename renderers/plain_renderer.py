# -*- coding: utf-8 -*-
"""
纯文本渲染器实现。

将统一信息项列表渲染为纯文本格式，适用于 Bark 等轻量渠道。
"""

import logging
from datetime import datetime
from typing import Any

from renderers.base import Renderer, RenderedContent

logger = logging.getLogger(__name__)


class PlainRenderer(Renderer):
    """纯文本格式渲染器。"""

    def render(self, items: list[dict], channel: str = "plain", options: dict[str, Any] | None = None) -> RenderedContent:
        """
        渲染信息项为纯文本格式。

        Args:
            items: 统一信息项列表。
            channel: 目标发布渠道标识。
            options: 可选配置项，支持：
                - date_text: 日期文本，默认使用当前日期。
                - title: 自定义标题，默认生成 "Agently 每日速览 · {date_text}"。
                - max_length: 最大长度限制，默认 500。

        Returns:
            RenderedContent: 渲染后的纯文本内容。
        """
        options = options or {}
        date_text = options.get("date_text") or datetime.now().strftime("%Y-%m-%d")
        title = options.get("title") or f"Agently 每日速览 · {date_text}"
        max_length = options.get("max_length", 500)

        lines = [title, ""]
        for idx, item in enumerate(items or [], 1):
            line = f"{idx}. {item.get('title', '无标题')}"
            url = item.get("url")
            if url:
                line += f" ({url})"
            lines.append(line)

        body = "\n".join(lines)
        if len(body) > max_length:
            body = body[:max_length].rsplit("\n", 1)[0] + "\n…"

        return RenderedContent(
            channel=channel,
            format="plain",
            title=title,
            body=body,
            excerpt=body[:100],
            metadata={"item_count": len(items or [])},
        )
