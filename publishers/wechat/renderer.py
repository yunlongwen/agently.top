# -*- coding: utf-8 -*-
"""
Markdown 转微信公众号 HTML。

参考 PrismFlowAgent 的 WechatRenderer，使用 Python markdown 库 + 后处理实现。
"""

import logging
import re

import markdown
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class WechatRenderer:
    """Markdown 转微信风格 HTML。"""

    # 微信绿
    PRIMARY_COLOR = "#07C160"
    # 深色代码块背景
    CODE_BG = "#282c34"
    CODE_TEXT = "#abb2bf"
    # 正文文字
    TEXT_COLOR = "#333333"
    # 次要文字
    SECONDARY_COLOR = "#666666"
    # 引用边框
    QUOTE_BORDER = "#07C160"
    # 链接颜色
    LINK_COLOR = "#576b95"

    def __init__(self):
        self._md = markdown.Markdown(
            extensions=[
                "extra",  # 表格、缩进代码、abbr、def_list、footnotes
                "fenced_code",
                "nl2br",
            ]
        )

    def convert(self, text: str) -> str:
        """把 Markdown 文本转换为微信 HTML。"""
        if not text:
            return ""

        # 先使用 markdown 库渲染基础 HTML
        self._md.reset()
        html = self._md.convert(text)

        # 后处理为微信风格
        html = self._apply_wechat_styles(html)
        return html

    def _apply_wechat_styles(self, html: str) -> str:
        """应用微信样式。"""
        soup = BeautifulSoup(html, "html.parser")

        # 整体容器
        wrapper = soup.new_tag(
            "section",
            style=(
                "font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', "
                "'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;"
                f" color: {self.TEXT_COLOR};"
                " font-size: 16px;"
                " line-height: 1.75;"
                " padding: 0 8px;"
            ),
        )

        # 把 soup 中所有顶层子节点移到 wrapper 中
        for child in list(soup.children):
            if getattr(child, "name", None):
                wrapper.append(child.extract())
        soup.append(wrapper)

        # 标题样式
        for h1 in wrapper.find_all("h1"):
            h1["style"] = (
                f"color: {self.PRIMARY_COLOR};"
                " font-size: 22px;"
                " font-weight: 700;"
                " margin: 24px 0 16px;"
                " padding-bottom: 8px;"
                f" border-bottom: 2px solid {self.PRIMARY_COLOR};"
            )

        for h2 in wrapper.find_all("h2"):
            h2["style"] = (
                f"background-color: {self.PRIMARY_COLOR};"
                " color: #ffffff;"
                " font-size: 18px;"
                " font-weight: 600;"
                " padding: 10px 14px;"
                " margin: 22px 0 14px;"
                " border-radius: 6px;"
                " box-shadow: 0 2px 6px rgba(0,0,0,0.1);"
            )

        for h3 in wrapper.find_all("h3"):
            h3["style"] = (
                f"color: {self.PRIMARY_COLOR};"
                " font-size: 17px;"
                " font-weight: 600;"
                " margin: 18px 0 10px;"
                " padding-left: 10px;"
                f" border-left: 4px solid {self.PRIMARY_COLOR};"
            )

        # 段落
        for p in wrapper.find_all("p"):
            existing = p.get("style", "")
            p["style"] = existing + " margin: 14px 0;" if existing else "margin: 14px 0;"

        # 引用块
        for blockquote in wrapper.find_all("blockquote"):
            blockquote["style"] = (
                f"border-left: 4px solid {self.QUOTE_BORDER};"
                " background-color: #f7f7f7;"
                " padding: 12px 16px;"
                " margin: 16px 0;"
                " border-radius: 0 6px 6px 0;"
                f" color: {self.SECONDARY_COLOR};"
            )

        # 代码块
        for pre in wrapper.find_all("pre"):
            pre["style"] = (
                f"background-color: {self.CODE_BG};"
                " padding: 14px;"
                " border-radius: 8px;"
                " overflow-x: auto;"
                " margin: 16px 0;"
                " font-size: 14px;"
                " line-height: 1.6;"
            )
            code = pre.find("code")
            if code:
                code["style"] = (
                    f"color: {self.CODE_TEXT};"
                    " font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;"
                    " white-space: pre;"
                    " background: transparent;"
                )

        # 行内代码
        for code in wrapper.find_all("code"):
            if code.parent and code.parent.name != "pre":
                code["style"] = (
                    f"background-color: {self.CODE_BG};"
                    f" color: {self.CODE_TEXT};"
                    " padding: 2px 5px;"
                    " border-radius: 4px;"
                    " font-size: 14px;"
                    " font-family: 'SFMono-Regular', Consolas, monospace;"
                )

        # 图片
        for img in wrapper.find_all("img"):
            img["style"] = (
                "max-width: 100%;"
                " display: block;"
                " margin: 16px auto;"
                " border-radius: 8px;"
                " box-shadow: 0 2px 8px rgba(0,0,0,0.08);"
            )

        # 链接
        for a in wrapper.find_all("a"):
            a["style"] = (
                f"color: {self.LINK_COLOR};"
                " text-decoration: none;"
                " border-bottom: 1px solid rgba(87,107,149,0.3);"
            )

        # 列表
        for ul in wrapper.find_all("ul"):
            ul["style"] = "margin: 12px 0; padding-left: 24px;"
        for ol in wrapper.find_all("ol"):
            ol["style"] = "margin: 12px 0; padding-left: 24px;"
        for li in wrapper.find_all("li"):
            li["style"] = "margin: 6px 0;"

        # 表格
        for table in wrapper.find_all("table"):
            table["style"] = (
                "width: 100%;"
                " border-collapse: collapse;"
                " margin: 16px 0;"
                " font-size: 14px;"
            )
        for th in wrapper.find_all("th"):
            th["style"] = (
                f"background-color: {self.PRIMARY_COLOR};"
                " color: #ffffff;"
                " padding: 10px;"
                " text-align: left;"
                " border: 1px solid #e0e0e0;"
            )
        for td in wrapper.find_all("td"):
            td["style"] = (
                " padding: 10px;"
                " border: 1px solid #e0e0e0;"
            )

        # 分割线
        for hr in wrapper.find_all("hr"):
            hr["style"] = (
                "border: none;"
                " border-top: 1px solid #e0e0e0;"
                " margin: 24px 0;"
            )

        # 加粗数字高亮
        self._highlight_numbers(wrapper)

        return str(soup)

    def _highlight_numbers(self, soup: BeautifulSoup) -> None:
        """高亮文本中的数字，如 H100、GB300、100亿。"""
        pattern = re.compile(r"\b([A-Z]*\d+[A-Z]*\d*)\b")
        for text_node in soup.find_all(string=True):
            if text_node.parent and text_node.parent.name in ("pre", "code", "a"):
                continue
            new_text = pattern.sub(
                lambda m: f'<span style="color: {self.PRIMARY_COLOR}; font-weight: 600;">{m.group(1)}</span>',
                str(text_node),
            )
            if new_text != str(text_node):
                text_node.replace_with(BeautifulSoup(new_text, "html.parser"))
