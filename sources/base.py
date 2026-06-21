# sources/base.py
from abc import ABC, abstractmethod
from typing import Any


class SourceSpider(ABC):
    @property
    @abstractmethod
    def source_id(self) -> str:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def fetch(self) -> list[dict[str, Any]]:
        """返回统一内容项列表。"""
        ...

    @property
    def display_priority(self) -> str:
        return "medium"

    @property
    def category(self) -> str:
        return ""

    @property
    def enabled(self) -> bool:
        return True
