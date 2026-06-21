import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "config" / "rss.yaml"


def load_rss_config(path: str | Path | None = None) -> dict:
    path = Path(path or DEFAULT_PATH)
    if not path.exists():
        raise FileNotFoundError(f"RSS 配置文件不存在: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def list_enabled_rss_sources(config: dict) -> list[dict]:
    rss = config.get("rss", {})
    if not rss.get("enabled", False):
        return []
    sources = rss.get("sources", []) or []
    return [s for s in sources if s.get("enabled", True)]


def get_rss_request_options(config: dict) -> dict:
    rss = config.get("rss", {})
    return rss.get("request", {"timeout": 10, "retries": 2, "headers": {}})
