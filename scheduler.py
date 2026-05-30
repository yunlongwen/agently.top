# -*- coding: utf-8 -*-
"""
FastAPI 进程内采集调度器。

生产环境应使用单 worker 运行 uvicorn，避免多个 worker 同时启动调度器。
"""

import logging
import threading
import time
from datetime import datetime, timedelta

from config import (
    SPIDER_RUN_ON_STARTUP,
    SPIDER_SCHEDULE_TIMES,
    SPIDER_SCHEDULER_ENABLED,
)

logger = logging.getLogger(__name__)

_scheduler_thread = None
_stop_event = threading.Event()
_run_lock = threading.Lock()


def parse_schedule_times(value):
    """解析 HH:MM,HH:MM 格式的每日调度时间。"""
    result = []
    for item in (value or "").split(","):
        text = item.strip()
        if not text:
            continue
        hour_text, minute_text = text.split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            raise ValueError("调度时间超出范围: {}".format(text))
        result.append((hour, minute))

    if not result:
        raise ValueError("至少需要配置一个调度时间")
    return sorted(set(result))


def start_scheduler():
    """启动后台调度线程。"""
    global _scheduler_thread

    if not SPIDER_SCHEDULER_ENABLED:
        logger.info("内置采集调度已关闭")
        return

    if _scheduler_thread and _scheduler_thread.is_alive():
        logger.info("内置采集调度已在运行")
        return

    try:
        schedule_times = parse_schedule_times(SPIDER_SCHEDULE_TIMES)
    except ValueError as e:
        logger.error("内置采集调度配置无效: %s", e)
        return
    _stop_event.clear()
    _scheduler_thread = threading.Thread(
        target=_scheduler_loop,
        args=(schedule_times,),
        name="spider-scheduler",
        daemon=True,
    )
    _scheduler_thread.start()
    logger.info("内置采集调度已启动: %s", SPIDER_SCHEDULE_TIMES)

    if SPIDER_RUN_ON_STARTUP:
        trigger_spider_async("startup")


def stop_scheduler():
    """停止后台调度线程。"""
    _stop_event.set()
    if _scheduler_thread and _scheduler_thread.is_alive():
        _scheduler_thread.join(timeout=5)
    logger.info("内置采集调度已停止")


def trigger_spider_async(reason):
    """异步触发一次采集。"""
    thread = threading.Thread(
        target=_run_spider_with_lock,
        args=(reason,),
        name="spider-runner",
        daemon=True,
    )
    thread.start()
    return thread


def _scheduler_loop(schedule_times):
    while not _stop_event.is_set():
        next_run_at = _next_run_time(datetime.now(), schedule_times)
        wait_seconds = max(1, int((next_run_at - datetime.now()).total_seconds()))
        logger.info("下一次采集时间: %s", next_run_at.isoformat(timespec="seconds"))
        if _stop_event.wait(wait_seconds):
            break
        _run_spider_with_lock("schedule", next_run_at)


def _run_spider_with_lock(reason, scheduled_time=None):
    if not _run_lock.acquire(blocking=False):
        logger.warning("已有采集任务运行中，跳过本次触发: %s", reason)
        return False

    try:
        logger.info("开始执行采集任务: %s", reason)
        from main import run_spider

        return run_spider(scheduled_time=scheduled_time)
    except Exception as e:
        logger.exception("采集任务异常: %s", e)
        return False
    finally:
        _run_lock.release()


def _next_run_time(now, schedule_times):
    for hour, minute in schedule_times:
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate > now:
            return candidate

    first_hour, first_minute = schedule_times[0]
    tomorrow = now + timedelta(days=1)
    return tomorrow.replace(
        hour=first_hour,
        minute=first_minute,
        second=0,
        microsecond=0,
    )
