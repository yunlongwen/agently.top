import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "config" / "sources.yaml"


def load_rss_config(path: str | Path | None = None) -> dict:
    """加载 config/sources.yaml 中的 rss 段落。"""
    path = Path(path or DEFAULT_PATH)
    if not path.exists():
        raise FileNotFoundError("RSS 配置文件不存在: {}".format(path))
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("sources", {}).get("rss", {}) or {}


def list_enabled_rss_sources(config: dict) -> list[dict]:
    """从 rss 段落中提取启用的 RSS 源列表。"""
    if not config.get("enabled", False):
        return []
    sources = config.get("sources", []) or []
    return [s for s in sources if s.get("enabled", True)]


def get_rss_request_options(config: dict) -> dict:
    """从 rss 段落中提取全局请求选项。"""
    return config.get("request", {"timeout": 10, "retries": 2, "headers": {}})
