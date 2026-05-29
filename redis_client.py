# -*- coding: utf-8 -*-
"""
Redis 进程级连接池。
"""

import logging

from config import (
    REDIS_SOCKET_TIMEOUT_SECONDS,
    REDIS_URL,
)

logger = logging.getLogger(__name__)

_redis_client = None
_redis_pool = None


def get_redis_client():
    """获取进程级 Redis client，底层复用连接池。"""
    global _redis_client
    global _redis_pool

    if _redis_client is not None:
        return _redis_client

    try:
        import redis
    except ImportError:
        logger.warning("未安装 redis 依赖，跳过 Redis 读写")
        return None

    try:
        _redis_pool = redis.ConnectionPool.from_url(
            REDIS_URL,
            socket_timeout=REDIS_SOCKET_TIMEOUT_SECONDS,
            socket_connect_timeout=REDIS_SOCKET_TIMEOUT_SECONDS,
        )
        _redis_client = redis.Redis(connection_pool=_redis_pool)
        return _redis_client
    except Exception as e:
        logger.warning("创建 Redis 连接池失败: %s", e)
        _redis_client = None
        _redis_pool = None
        return None
