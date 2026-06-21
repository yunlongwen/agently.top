# -*- coding: utf-8 -*-
"""URL 归一化与去重。"""

import re
from urllib.parse import urlencode, urlparse, parse_qsl


TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "fbclid", "gclid"}


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qsl(parsed.query)
    filtered = [(k, v) for k, v in query if k.lower() not in TRACKING_PARAMS]
    query_str = urlencode(filtered)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}" + (f"?{query_str}" if query_str else "")


def filter_new_items(items: list[dict], seen: set[str]) -> list[dict]:
    new_items = []
    for item in items:
        url = normalize_url(item.get("url", ""))
        if url in seen:
            continue
        seen.add(url)
        new_items.append(item)
    return new_items


def filter_duplicate_items(items: list[dict]) -> list[dict]:
    seen = set()
    return filter_new_items(items, seen)
