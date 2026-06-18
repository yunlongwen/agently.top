# -*- coding: utf-8 -*-
"""
轻量访问统计：1x1 GIF 上报 + Redis 计数。

数据模型（全部用 Redis）：
- stats:uv:<YYYY-MM-DD>           HyperLogLog  (PFADD)            独立访客
- stats:pv:<YYYY-MM-DD>           String       (INCR)             当日总 PV
- stats:pv:<YYYY-MM-DD>:<path>    String       (INCR)             各路径 PV
- stats:paths:<YYYY-MM-DD>        SortedSet    (ZINCRBY)          热门页面 Top
- stats:referers:<YYYY-MM-DD>     SortedSet    (ZINCRBY)          来源域名 Top
- stats:bots:<YYYY-MM-DD>         String       (INCR)             识别为 bot 的次数

去重规则：
- 一天内同一 IP+UA 组合只计一次 UV（用 ip|ua 的 md5 作为 HLL 元素）
- 同 IP 在 30 分钟内同 path 不重复计 PV（用 SortedSet 做滑动窗口）

Bot 识别：UA 含 googlebot / bingbot / baiduspider / yandex / headless /
phantomjs / curl / wget / python-requests / ahrefs / semrush 等。
"""

import hashlib
import ipaddress
import logging
import re
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta
from urllib.parse import urlparse

from config import (
    REDIS_KEY_PREFIX,
    STATS_API_TOKEN,
    STATS_ENABLED,
    STATS_PRIVATE_CIDRS,
    STATS_RETENTION_DAYS,
)
from redis_client import get_redis_client

logger = logging.getLogger(__name__)

# 1x1 透明 GIF (43 字节, 适用于所有浏览器)
TRANSPARENT_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff"
    b"\x00\x00\x00!\xf9\x04\x00\x00\x00\x00\x00,"
    b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D"
    b"\x01\x00;"
)

# 路径白名单:长度上限,防止有人拿 /api/track 写超长 path 占存储
MAX_PATH_LEN = 200
MAX_REF_LEN = 200
# 排除自身内部访问造成的循环
INTERNAL_REF_PREFIX = "/api/track"

# Bot 关键词(覆盖主流搜索引擎爬虫 + 常见 HTTP 客户端)
BOT_PATTERNS = re.compile(
    r"(bot|crawler|spider|slurp|bingpreview|facebookexternalhit|"
    r"headless|phantom|selenium|playwright|puppeteer|"
    r"curl|wget|httpie|python-requests|go-http-client|okhttp|"
    r"ahrefs|semrush|mj12|dotbot|petal|duckduck|yandex|sogou|360spider|"
    r"bytespider|amazonbot|applebot)",
    re.IGNORECASE,
)

# 进程内滑动窗口:同 IP+PATH 在 WINDOW_SEC 秒内只计一次 PV
WINDOW_SEC = 30 * 60
_window_lock = threading.Lock()
_window: dict = {}


def _key(*parts):
    """拼 Redis key,带全局前缀。"""
    return "{}:{}".format(REDIS_KEY_PREFIX, ":".join(parts))


def _is_bot(ua: str) -> bool:
    if not ua:
        return False
    return bool(BOT_PATTERNS.search(ua))


def _normalize_path(path: str) -> str:
    """截断 + 去尾部斜杠,降低基数。"""
    if not path:
        return "/"
    if len(path) > MAX_PATH_LEN:
        path = path[:MAX_PATH_LEN]
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return path or "/"


def _referer_host(referer: str) -> str:
    """从 referer 提 host;空 / 同源 / 内部 / 超长 全部归一为 (direct)。"""
    if not referer:
        return "(direct)"
    if referer.startswith("/") or referer.startswith(INTERNAL_REF_PREFIX):
        return "(direct)"
    try:
        u = urlparse(referer if "://" in referer else "http://" + referer)
    except Exception:
        return "(direct)"
    host = (u.hostname or "").lower()
    if not host or len(host) > MAX_REF_LEN:
        return "(direct)"
    return host


def _within_window(ip: str, path: str) -> bool:
    """进程内滑动窗口:返回 True 表示 30 分钟内已计过,本次跳过 PV。"""
    now = time.time()
    with _window_lock:
        # 清理过期条目(避免无界增长)
        if len(_window) > 50000:
            cutoff = now - WINDOW_SEC
            stale = [k for k, t in _window.items() if t < cutoff]
            for k in stale:
                _window.pop(k, None)
        k = "{}|{}".format(ip, path)
        last = _window.get(k, 0)
        if now - last < WINDOW_SEC:
            return True
        _window[k] = now
        return False


def record_track(ip: str, ua: str, path: str, referer: str) -> bool:
    """
    记录一次页面访问。

    Args:
        ip: 客户端 IP(已由调用方从 X-Forwarded-For 解析)
        ua: User-Agent
        path: 页面路径
        referer: 来源 URL

    Returns:
        bool: True 表示成功记录,False 表示跳过(bot / 禁用 / 窗口内重复)
    """
    if not STATS_ENABLED:
        return False

    if _is_bot(ua):
        _incr_bots()
        return False

    path_n = _normalize_path(path)
    ref_host = _referer_host(referer)

    if _within_window(ip, path_n):
        return False

    client = get_redis_client()
    if client is None:
        return False

    today = datetime.now().strftime("%Y-%m-%d")
    uv_element = "{}|{}".format(ip, ua)
    uv_hash = hashlib.md5(uv_element.encode("utf-8", errors="ignore")).hexdigest()

    try:
        pipe = client.pipeline()
        pipe.pfadd(_key("uv", today), uv_hash)
        pipe.incr(_key("pv", today))
        pipe.incr(_key("pv", today, path_n))
        pipe.zincrby(_key("paths", today), 1, path_n)
        pipe.zincrby(_key("referers", today), 1, ref_host)
        # 30 天过期,HLL / ZSET / 计数 key 全部覆盖
        for k in (
            _key("uv", today),
            _key("pv", today),
            _key("pv", today, path_n),
            _key("paths", today),
            _key("referers", today),
            _key("bots", today),
        ):
            pipe.expire(k, (STATS_RETENTION_DAYS + 1) * 86400)
        pipe.execute()
        return True
    except Exception as e:
        logger.warning("记录访问统计失败: %s", e)
        return False


def _incr_bots():
    """bot 计数走单独 key,失败不影响主流程。"""
    client = get_redis_client()
    if client is None:
        return
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        client.incr(_key("bots", today))
        client.expire(_key("bots", today), (STATS_RETENTION_DAYS + 1) * 86400)
    except Exception:
        pass


def _is_private_ip(ip: str) -> bool:
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if addr.is_loopback or addr.is_private or addr.is_link_local:
        return True
    for cidr in STATS_PRIVATE_CIDRS.split(","):
        cidr = cidr.strip()
        if not cidr:
            continue
        try:
            if addr in ipaddress.ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue
    return False


def is_authorized(ip: str, token: str) -> bool:
    """
    检查调用方是否有权访问 /api/stats/summary。

    优先匹配 STATS_API_TOKEN,否则只要 IP 在内网段就放行。
    """
    if STATS_API_TOKEN:
        return bool(token) and token == STATS_API_TOKEN
    return _is_private_ip(ip)


def _safe_int(v, default=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def get_summary(days: int = 7, top_n: int = 10):
    """
    读取最近 days 天的访问汇总,返回结构化数据。

    Returns:
        dict: {
            "days": days,
            "today": {"date": "YYYY-MM-DD", "uv": int, "pv": int, "bots": int},
            "trend": [{"date": "...", "uv": int, "pv": int}, ...],  # 含今天往前
            "top_paths": [{"path": ..., "pv": int}, ...],
            "top_referers": [{"host": ..., "pv": int}, ...],
        }
        Redis 不可用时返回 None,调用方应降级返回 503。
    """
    if not STATS_ENABLED:
        return None
    client = get_redis_client()
    if client is None:
        return None

    days = max(1, min(days, STATS_RETENTION_DAYS))
    today = datetime.now()
    date_list = [
        (today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)
    ]

    try:
        pipe = client.pipeline()
        for d in date_list:
            pipe.pfcount(_key("uv", d))
            pipe.get(_key("pv", d))
            pipe.get(_key("bots", d))
        raw = pipe.execute()
    except Exception as e:
        logger.warning("读取访问统计失败: %s", e)
        return None

    trend = []
    for i, d in enumerate(date_list):
        uv = _safe_int(raw[i * 3], 0)
        pv = _safe_int(raw[i * 3 + 1], 0)
        bots = _safe_int(raw[i * 3 + 2], 0)
        trend.append({"date": d, "uv": uv, "pv": pv, "bots": bots})

    today_entry = trend[0]
    today_entry["bots"] = today_entry.get("bots", 0)

    top_paths = []
    top_referers = []
    try:
        path_pairs = client.zrevrange(
            _key("paths", date_list[0]), 0, top_n - 1, withscores=True
        )
        for member, score in path_pairs:
            top_paths.append({"path": member, "pv": int(score)})
        ref_pairs = client.zrevrange(
            _key("referers", date_list[0]), 0, top_n - 1, withscores=True
        )
        for member, score in ref_pairs:
            top_referers.append({"host": member, "pv": int(score)})
    except Exception as e:
        logger.warning("读取 Top 列表失败: %s", e)

    return {
        "days": days,
        "generated_at": today.strftime("%Y-%m-%dT%H:%M:%S"),
        "today": today_entry,
        "trend": trend,
        "top_paths": top_paths,
        "top_referers": top_referers,
    }