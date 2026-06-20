# -*- coding: utf-8 -*-
"""
发布器注册表。

负责自动发现并管理所有 Publisher 实现。
"""

import importlib
import inspect
import logging
import pkgutil
from typing import Any

from publishers.base import Publisher

logger = logging.getLogger(__name__)


class PublisherRegistry:
    """发布器注册表。"""

    def __init__(self):
        self._publishers: dict[str, Publisher] = {}

    def register(self, publisher: Publisher) -> None:
        """注册一个发布器实例。"""
        if not isinstance(publisher, Publisher):
            raise TypeError("publisher must be an instance of Publisher")
        self._publishers[publisher.id] = publisher
        logger.info("发布器已注册: %s (%s)", publisher.id, publisher.name)

    def get(self, publisher_id: str) -> Publisher | None:
        """按 ID 获取发布器。"""
        return self._publishers.get(publisher_id)

    def list_all(self) -> list[Publisher]:
        """返回所有已注册发布器。"""
        return list(self._publishers.values())

    def list_enabled(self) -> list[Publisher]:
        """返回所有已启用的发布器。"""
        return [p for p in self._publishers.values() if p.is_enabled()]

    def auto_discover(self, package_name: str = "publishers") -> None:
        """
        自动发现指定包下的发布器插件。

        约定：
        - 直接子模块（如 publishers/email_publisher.py）需导出名为 Publisher 的类，
          或在模块级调用 registry.register(...)。
        - 子包（如 publishers/wechat/）需导出名为 Publisher 的类，
          或在 __init__.py 中调用 registry.register(...)。
        """
        try:
            package = importlib.import_module(package_name)
        except ImportError as e:
            logger.warning("自动发现发布器失败: 无法导入 %s: %s", package_name, e)
            return

        prefix = package.__name__ + "."
        for _, module_name, is_pkg in pkgutil.iter_modules(
            package.__path__, prefix  # type: ignore[arg-type]
        ):
            try:
                module = importlib.import_module(module_name)
            except Exception as e:
                logger.warning("导入发布器模块 %s 失败: %s", module_name, e)
                continue

            # 优先使用模块中显式实例化的 publisher 对象
            if hasattr(module, "publisher") and isinstance(module.publisher, Publisher):
                self.register(module.publisher)
                continue

            # 否则查找名为 Publisher 的类并自动实例化
            if hasattr(module, "Publisher"):
                cls = module.Publisher
                if inspect.isclass(cls) and issubclass(cls, Publisher) and cls is not Publisher:
                    try:
                        instance = cls()
                        self.register(instance)
                    except Exception as e:
                        logger.warning("实例化发布器 %s 失败: %s", cls.__name__, e)
                    continue

            logger.debug("模块 %s 未找到可注册发布器", module_name)


# 全局注册表实例
registry = PublisherRegistry()
