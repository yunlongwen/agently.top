import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

import feedparser
import requests

from sources.base import SourceSpider
from sources.rss_config import get_rss_request_options, load_rss_config

logger = logging.getLogger(__name__)


UTM_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"}


def _parse_published(entry: dict) -> str:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        dt = datetime(*parsed[:6], tzinfo=timezone.utc)
        return dt.isoformat()
    return ""


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    # Strip fragment
    fragment = ""
    # Remove common tracking query parameters
    filtered_query = [
        (k, v) for k, v in parse_qsl(parsed.query) if k not in UTM_PARAMS
    ]
    query = urlencode(filtered_query)
    return urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, query, fragment)
    )


class RssSpider(SourceSpider):
    def __init__(self, source_def: dict[str, Any], request_options: dict[str, Any] | None = None):
        self._def = source_def
        self._request_options = request_options or {}

    @property
    def source_id(self) -> str:
        return self._def["id"]

    @property
    def name(self) -> str:
        return self._def["name"]

    @property
    def display_priority(self) -> str:
        return self._def.get("display_priority", "medium")

    @property
    def category(self) -> str:
        return self._def.get("category", "")

    @property
    def enabled(self) -> bool:
        return self._def.get("enabled", True)

    def fetch(self) -> list[dict[str, Any]]:
        url = self._def["url"]
        timeout = self._request_options.get("timeout", 10)
        retries = self._request_options.get("retries", 2)
        headers = self._request_options.get("headers", {})

        last_exception = None
        for attempt in range(retries + 1):
            try:
                resp = requests.get(url, headers=headers, timeout=timeout)
                resp.raise_for_status()
                feed = feedparser.parse(resp.content)
                break
            except Exception as e:
                last_exception = e
                logger.warning("RSS 源 %s 请求失败（第 %d 次）: %s", self.source_id, attempt + 1, e)
                time.sleep(1)
        else:
            logger.error("RSS 源 %s 连续失败 %d 次: %s", self.source_id, retries + 1, last_exception)
            return []

        max_age_days = self._def.get("max_age_days", 3)
        max_items = self._def.get("max_items", 10)
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

        items = []
        # 扫描最多 max_items * 2 条，因为部分会被 max_age_days 过滤掉
        for entry in feed.entries[:max_items * 2]:
            published_at = _parse_published(entry)
            if published_at:
                try:
                    pub_dt = datetime.fromisoformat(published_at)
                    if pub_dt < cutoff:
                        continue
                except Exception:
                    pass

            title = (entry.get("title") or "").strip()
            url = _normalize_url(entry.get("link") or "")
            summary = (entry.get("summary") or entry.get("description") or "").strip()
            guid = entry.get("id") or url

            if not title or not url:
                continue

            items.append({
                "source": self.source_id,
                "category": self.category,
                "title": title,
                "url": url,
                "published_at": published_at,
                "original_summary": summary[:500],
                "chinese_summary": "",
                "backend_focus": "",
                "meta": {"guid": guid},
            })

            if len(items) >= max_items:
                break

        return items


def build_all_rss_spiders(config_or_path: str | dict | None = None) -> list["RssSpider"]:
    if isinstance(config_or_path, dict):
        cfg = config_or_path
    else:
        cfg = load_rss_config(config_or_path)
    request_options = get_rss_request_options(cfg)
    return [RssSpider(s, request_options) for s in cfg.get("rss", {}).get("sources", []) if s.get("enabled", True)]
