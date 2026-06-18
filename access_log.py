# -*- coding: utf-8 -*-
"""
API 访问日志中间件 + 每小时访问统计。

日志标签说明：
- [访问] 每次请求的实时记录
- [统计] 每小时输出一次汇总数据
"""

import logging
import threading
import time
from collections import defaultdict
from datetime import datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)

# =========================================================================
# 内存统计计数器
# =========================================================================

_stats_lock = threading.Lock()
_stats = {
    "总请求数": 0,
    "错误请求数": 0,
    "累计耗时ms": 0,
    "IP计数": defaultdict(int),
    "接口计数": defaultdict(int),
    "统计起始时间": datetime.now().strftime("%H:%M"),
}
_stats_thread = None


def _reset_stats():
    """重置统计计数器。"""
    _stats["总请求数"] = 0
    _stats["错误请求数"] = 0
    _stats["累计耗时ms"] = 0
    _stats["IP计数"] = defaultdict(int)
    _stats["接口计数"] = defaultdict(int)
    _stats["统计起始时间"] = datetime.now().strftime("%H:%M")


def _dump_stats():
    """输出当前统计摘要到日志并重置。"""
    with _stats_lock:
        total = _stats["总请求数"]
        if total == 0:
            _reset_stats()
            return

        errors = _stats["错误请求数"]
        avg_latency = int(_stats["累计耗时ms"] / total) if total else 0
        unique_ips = len(_stats["IP计数"])
        period_start = _stats["统计起始时间"]
        period_end = datetime.now().strftime("%H:%M")

        # 热门接口 Top 5
        top_paths = sorted(
            _stats["接口计数"].items(), key=lambda x: x[1], reverse=True
        )[:5]
        top_paths_text = ", ".join(
            "{}={}次".format(path, count) for path, count in top_paths
        )

        # 活跃 IP Top 5
        top_ips = sorted(
            _stats["IP计数"].items(), key=lambda x: x[1], reverse=True
        )[:5]
        top_ips_text = ", ".join(
            "{}={}次".format(ip, count) for ip, count in top_ips
        )

        logger.info(
            "[统计] 时段=%s~%s | 总请求=%d | 独立IP数=%d | 平均耗时=%dms | 错误数=%d",
            period_start, period_end, total, unique_ips, avg_latency, errors,
        )
        if top_paths_text:
            logger.info("[统计] 热门接口: %s", top_paths_text)
        if top_ips_text:
            logger.info("[统计] 活跃IP: %s", top_ips_text)

        _reset_stats()


def _stats_loop():
    """后台线程：每小时输出一次统计摘要。"""
    while True:
        time.sleep(3600)
        _dump_stats()


def start_stats_reporter():
    """启动后台统计报告线程。"""
    global _stats_thread
    if _stats_thread and _stats_thread.is_alive():
        return
    _stats_thread = threading.Thread(
        target=_stats_loop,
        name="access-stats-reporter",
        daemon=True,
    )
    _stats_thread.start()
    logger.info("[统计] 后台统计线程已启动，每小时输出一次访问汇总")


# =========================================================================
# 获取客户端真实 IP
# =========================================================================

def _get_client_ip(request: Request) -> str:
    """
    获取客户端真实 IP。

    优先读取 Nginx 传递的 X-Forwarded-For，
    如果没有则使用直连 IP。
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # X-Forwarded-For 格式: "客户端IP, 代理1, 代理2"，取第一个
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    if request.client:
        return request.client.host
    return "未知IP"


# =========================================================================
# FastAPI 中间件
# =========================================================================

class AccessLogMiddleware(BaseHTTPMiddleware):
    """
    记录每次 API 请求的访问日志。

    日志内容：来源IP、请求路径、响应状态码、耗时、客户端标识。
    同时更新内存统计计数器。
    """

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        client_ip = _get_client_ip(request)
        method = request.method
        path = request.url.path

        # 执行请求
        response = await call_next(request)

        # 计算耗时
        latency_ms = int((time.time() - start_time) * 1000)
        status_code = response.status_code
        user_agent = request.headers.get("user-agent", "未知客户端")

        # 访问统计上报接口单独走自己的记录逻辑,不在这里输出
        # 否则每个 PV 都会写一行日志,PV 高时日志爆炸
        is_track = path == "/api/track"

        # 输出访问日志（中文格式）
        if not is_track:
            logger.info(
                "[访问] 来源IP=%s | 请求=%s %s | 状态码=%d | 耗时=%dms | 客户端=%s",
                client_ip, method, path, status_code, latency_ms, user_agent,
            )

        # 更新统计计数器
        with _stats_lock:
            _stats["总请求数"] += 1
            _stats["累计耗时ms"] += latency_ms
            _stats["IP计数"][client_ip] += 1
            _stats["接口计数"][path] += 1
            if status_code >= 400:
                _stats["错误请求数"] += 1

        return response
