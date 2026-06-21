# -*- coding: utf-8 -*-
"""
HTML 渲染器实现。

将统一信息项列表渲染为 HTML 格式，适用于邮件等渠道。
"""

import logging
from datetime import datetime
from typing import Any

from renderers.base import Renderer, RenderedContent

logger = logging.getLogger(__name__)


class HtmlRenderer(Renderer):
    """HTML 格式渲染器。"""

    def render(self, items: list[dict], channel: str = "email", options: dict[str, Any] | None = None) -> RenderedContent:
        """
        渲染信息项为 HTML 格式。

        Args:
            items: 统一信息项列表。
            channel: 目标发布渠道标识。
            options: 可选配置项，支持：
                - date_text: 日期文本，默认使用当前日期。
                - title: 自定义标题，默认生成 "AI 后端专项信息源报告 - {date_text}"。

        Returns:
            RenderedContent: 渲染后的 HTML 内容。
        """
        options = options or {}
        date_text = options.get("date_text") or datetime.now().strftime("%Y-%m-%d")
        title = options.get("title") or f"AI 后端专项信息源报告 - {date_text}"

        rows = [
            "<!DOCTYPE html>",
            '<html><head><meta charset="utf-8">',
            "<style>",
            "  body { font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; color: #24292e; padding: 20px; max-width: 1000px; margin: 0 auto; }",
            "  h1 { color: #0366d6; border-bottom: 2px solid #e1e4e8; padding-bottom: 10px; }",
            "  h2 { color: #24292e; margin-top: 30px; }",
            "  table { border-collapse: collapse; width: 100%; margin: 15px 0; }",
            "  th { background-color: #0366d6; color: white; padding: 10px 12px; text-align: left; font-size: 13px; }",
            "  td { padding: 10px 12px; border-bottom: 1px solid #e1e4e8; font-size: 13px; vertical-align: top; }",
            "  tr:nth-child(even) { background-color: #f6f8fa; }",
            "  a { color: #0366d6; text-decoration: none; }",
            "  .summary { color: #586069; line-height: 1.5; }",
            "</style>",
            "</head><body>",
            f"<h1>{title}</h1>",
        ]

        if not items:
            rows.append("<p>今日暂无内容。</p>")
        else:
            rows.extend([
                "<table>",
                "<tr><th>#</th><th>来源</th><th>标题</th><th>发布时间</th><th>中文摘要</th><th>后端看点</th></tr>",
            ])
            for i, item in enumerate(items, 1):
                title = str(item.get("title") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                url = item.get("url") or ""
                source = str(item.get("source") or "").replace("&", "&amp;").replace("<", "&lt;")
                published = str(item.get("published_at") or "").replace("<", "&lt;")
                summary = str(item.get("chinese_summary") or item.get("original_summary") or "").replace("&", "&amp;").replace("<", "&lt;")
                backend = str(item.get("backend_focus") or "").replace("&", "&amp;").replace("<", "&lt;")
                rows.append(
                    f"<tr><td>{i}</td><td>{source}</td>"
                    f'<td><a href="{url}">{title}</a></td>'
                    f"<td>{published}</td><td class=\"summary\">{summary}</td><td class=\"summary\">{backend}</td></tr>"
                )
            rows.append("</table>")

        rows.extend([
            '<div class="footer"><p>此邮件由 Agently 自动生成。</p></div>',
            "</body></html>",
        ])
        body = "\n".join(rows)
        return RenderedContent(
            channel=channel,
            format="html",
            title=title,
            body=body,
            excerpt=body[:200],
            metadata={"item_count": len(items)},
        )
