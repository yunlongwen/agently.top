# -*- coding: utf-8 -*-
"""
统一信息源注册表。

前端、API、Redis key 和磁盘归档都使用稳定 source id。
来源定义统一读取自 config/sources.yaml，.env 中不再保留源级参数。
"""

from pathlib import Path

import yaml

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "config" / "sources.yaml"

SOURCE_GITHUB_DAILY_ID = "github-daily"
SOURCE_GITHUB_WEEKLY_ID = "github-weekly"
SOURCE_HACKER_NEWS_ID = "hacker-news"
SOURCE_LINUX_DO_ID = "linux-do"
SOURCE_SSPAI_ID = "sspai"
SOURCE_TMTPOST_ID = "tmtpost"
SOURCE_OPENAI_ID = "openai"
SOURCE_ANTHROPIC_ID = "anthropic"
SOURCE_INFOQ_ID = "infoq"


def load_sources_config(path=None):
    """加载 config/sources.yaml，返回顶层 sources 字典。"""
    path = Path(path or DEFAULT_PATH)
    if not path.exists():
        raise FileNotFoundError("消息源配置文件不存在: {}".format(path))
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("sources", {})


def _normalize_source(source, kind):
    """统一来源字段，补全缺省值并标记种类。"""
    if not isinstance(source, dict):
        return None
    s = dict(source)
    s["kind"] = kind
    s.setdefault("enabled", True)
    s.setdefault("label", s.get("name", s["id"]))
    s.setdefault("content_source", s.get("name", s["id"]))
    s.setdefault("display_priority", "medium")
    s.setdefault("category", "")
    return s


def _load_source_definitions():
    """从 YAML 加载内置源与 RSS 源，合并为统一注册表。"""
    cfg = load_sources_config()
    definitions = []

    for s in cfg.get("builtin", []):
        ns = _normalize_source(s, "builtin")
        if ns:
            definitions.append(ns)

    rss_section = cfg.get("rss", {}) or {}
    for s in rss_section.get("sources", []):
        ns = _normalize_source(s, "rss")
        if ns:
            definitions.append(ns)

    return definitions


SOURCE_DEFINITIONS = _load_source_definitions()

SOURCE_BY_ID = {
    source["id"]: source
    for source in SOURCE_DEFINITIONS
}
SOURCE_BY_CONTENT_SOURCE = {
    source["content_source"]: source
    for source in SOURCE_DEFINITIONS
    if source.get("content_source")
}


def get_source_by_id(source_id):
    """按稳定 source id 获取来源定义。"""
    return SOURCE_BY_ID.get(source_id)


def get_source_by_content_source(content_source):
    """按统一内容项里的 source 字段获取来源定义。"""
    return SOURCE_BY_CONTENT_SOURCE.get(content_source)


def get_source_config(source_id, key=None, default=None):
    """获取某个来源的源级配置（config 块）。

    Args:
        source_id: 来源稳定 id
        key: 可选，只取 config 中某个键
        default: 键不存在时返回的默认值

    Returns:
        dict 或单个配置值
    """
    source = SOURCE_BY_ID.get(source_id)
    if not source:
        return default if key else {}
    config = source.get("config", {}) or {}
    if key:
        return config.get(key, default)
    return config
