# -*- coding: utf-8 -*-
"""
渲染器抽象基类与统一输出类型。

所有渲染器（Markdown、HTML、纯文本、飞书卡片等）都应继承 Renderer，
并返回 RenderedContent 统一结构，供各发布渠道消费。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal


@dataclass
class RenderedContent:
    """统一渲染输出结构。

    Attributes:
        channel: 目标发布渠道标识，如 wechat、email、feishu。
        format: 内容格式类型。
        title: 渲染后的标题。
        body: 渲染后的完整内容体。
        excerpt: 内容摘要（通常用于预览或摘要字段）。
        metadata: 附加元数据，如 item_count、source_list 等。
    """
    channel: str
    format: Literal["markdown", "html", "plain", "feishu_card"]
    title: str
    body: str
    excerpt: str
    metadata: dict


class Renderer(ABC):
    """统一渲染器抽象基类。"""

    @abstractmethod
    def render(self, items: list[dict], channel: str, options: dict | None = None) -> RenderedContent:
        """
        将信息项列表渲染为统一输出格式。

        Args:
            items: 统一信息项列表。
            channel: 目标发布渠道标识。
            options: 可选渲染配置，如 date_text、title、memory_insights 等。

        Returns:
            RenderedContent: 渲染后的统一输出。
        """
        ...
