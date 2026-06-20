# -*- coding: utf-8 -*-
"""
发布器插件包。

使用方式：
    from publishers import registry
    from publishers.base import Publisher

    registry.auto_discover()
    for publisher in registry.list_enabled():
        result = publisher.publish(content, options)
"""

from publishers.base import Publisher
from publishers.registry import PublisherRegistry, registry

__all__ = ["Publisher", "PublisherRegistry", "registry"]

# 自动发现并注册内置发布器
registry.auto_discover(__name__)
