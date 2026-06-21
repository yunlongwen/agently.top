# app_config.py
import logging
import re
from datetime import timedelta
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


def load_app_config(path: str | Path | None = None) -> dict:
    path = Path(path or DEFAULT_CONFIG_PATH)
    if not path.exists():
        return _default_config()
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or _default_config()


def _default_config() -> dict:
    return {
        "frontend": {
            "source_groups": [
                {"key": "core", "label": "核心源", "display_priority": "high", "default_expanded": True},
                {"key": "extended", "label": "扩展源", "display_priority": "medium", "default_expanded": False},
                {"key": "optional", "label": "可选源", "display_priority": "low", "default_expanded": False},
            ]
        },
        "source_schedule": {
            "default_intervals": {"high": "8h", "medium": "8h", "low": "8h"},
            "overrides": {},
        },
    }


def _parse_interval(value: str) -> timedelta:
    value = str(value).strip().lower()
    match = re.match(r"^(\d+)\s*([hdm])$", value)
    if not match:
        raise ValueError(f"无效间隔格式: {value}")
    number, unit = int(match.group(1)), match.group(2)
    if unit == "h":
        return timedelta(hours=number)
    if unit == "d":
        return timedelta(days=number)
    if unit == "m":
        return timedelta(minutes=number)
    raise ValueError(f"无效间隔单位: {unit}")


def get_source_interval(source_id: str, priority: str, config: dict | None = None) -> timedelta:
    cfg = config or load_app_config()
    schedule = cfg.get("source_schedule", {})
    overrides = schedule.get("overrides", {})
    if source_id in overrides:
        return _parse_interval(overrides[source_id])
    defaults = schedule.get("default_intervals", {"high": "8h", "medium": "8h", "low": "8h"})
    return _parse_interval(defaults.get(priority, "8h"))


def get_frontend_source_groups(config: dict | None = None) -> list[dict]:
    cfg = config or load_app_config()
    return cfg.get("frontend", {}).get("source_groups", [])
