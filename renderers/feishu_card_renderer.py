# -*- coding: utf-8 -*-
"""
飞书交互卡片渲染器。

将信息项列表渲染为飞书（Lark）消息卡片 JSON 格式，
供飞书机器人通过 webhook 发送。
"""

import json
import logging
from datetime import datetime
from typing import Any

from renderers.base import Renderer, RenderedContent

logger = logging.getLogger(__name__)


class FeishuCardRenderer(Renderer):
    def render(self, items: list[dict], channel: str = "feishu", options: dict[str, Any] | None = None) -> RenderedContent:
        options = options or {}
        date_text = options.get("date_text") or datetime.now().strftime("%Y-%m-%d")
        title = options.get("title") or f"Agently 每日速览 · {date_text}"

        elements = []
        for idx, item in enumerate(items[:20], 1):
            text = f"{idx}. {item.get('title', '无标题')}\n{item.get('chinese_summary') or item.get('original_summary') or ''}".strip()
            elements.append({
                "tag": "div",
                "text": {"tag": "plain_text", "content": text[:500]},
            })
            url = item.get("url")
            if url:
                elements.append({
                    "tag": "action",
                    "actions": [{
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "阅读原文"},
                        "type": "primary",
                        "url": url,
                    }],
                })

        card = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                },
                "elements": elements or [{"tag": "div", "text": {"tag": "plain_text", "content": "今日暂无内容"}}],
            },
        }
        body = json.dumps(card, ensure_ascii=False)
        return RenderedContent(
            channel=channel,
            format="feishu_card",
            title=title,
            body=body,
            excerpt=title,
            metadata={"item_count": len(items)},
        )
