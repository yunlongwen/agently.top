# -*- coding: utf-8 -*-
"""
发布器抽象基类。

所有发布渠道（微信公众号、邮件、GitHub、RSS 等）都应实现此接口，
并由 PublisherRegistry 统一发现与管理。
"""

from abc import ABC, abstractmethod
from typing import Any


class Publisher(ABC):
    """统一发布器接口。"""

    @property
    @abstractmethod
    def id(self) -> str:
        """发布器唯一标识，如 wechat、email、github。"""
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        """发布器可读名称。"""
        raise NotImplementedError

    @property
    def description(self) -> str:
        """发布器描述。"""
        return ""

    @abstractmethod
    def is_enabled(self) -> bool:
        """当前发布器是否已启用。"""
        raise NotImplementedError

    @abstractmethod
    def publish(self, content: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        发布内容。

        Args:
            content: 待发布内容。通常为 Markdown 或 HTML。
            options: 发布选项，如 title、author、digest、thumb_media_id 等。

        Returns:
            dict: 必须包含 success(bool)；成功时可包含 media_id、url、title 等。
        """
        raise NotImplementedError

    def get_item_url(self, item: dict[str, Any]) -> str:
        """（可选）从内容项中提取外部访问链接。"""
        return item.get("url", "")
