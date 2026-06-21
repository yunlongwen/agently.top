# -*- coding: utf-8 -*-
"""按源异步调度器 v2。"""

import asyncio
import logging
import threading
from datetime import datetime, timedelta

from app_config import get_source_interval, load_app_config
from source_registry import SOURCE_DEFINITIONS

logger = logging.getLogger(__name__)

_stop_event = asyncio.Event()
_scheduler_thread: threading.Thread | None = None


def parse_interval(value: str) -> timedelta:
    import re
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


def run_source(source_id: str) -> bool:
    """执行单源采集。返回是否成功。"""
    from main import run_spider
    logger.info("[调度] 执行来源: %s", source_id)
    try:
        run_spider(scheduled_time=datetime.now())
        return True
    except Exception as e:
        logger.exception("[调度] 来源 %s 执行失败: %s", source_id, e)
        return False


async def schedule_source(source_id: str, interval: timedelta):
    while not _stop_event.is_set():
        run_source(source_id)
        try:
            await asyncio.wait_for(_stop_event.wait(), timeout=interval.total_seconds())
        except asyncio.TimeoutError:
            pass


async def scheduler_loop():
    config = load_app_config()
    tasks = []
    for source in SOURCE_DEFINITIONS:
        interval = get_source_interval(source["id"], source.get("display_priority", "medium"), config)
        tasks.append(asyncio.create_task(schedule_source(source["id"], interval)))
    await asyncio.gather(*tasks, return_exceptions=True)


def _run_scheduler_in_thread():
    asyncio.run(scheduler_loop())


def start_scheduler_v2():
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        return
    _stop_event.clear()
    _scheduler_thread = threading.Thread(target=_run_scheduler_in_thread, name="scheduler-v2", daemon=True)
    _scheduler_thread.start()
    logger.info("[调度] v2 异步调度器已启动")


def stop_scheduler_v2():
    _stop_event.set()
    if _scheduler_thread and _scheduler_thread.is_alive():
        _scheduler_thread.join(timeout=5)
    logger.info("[调度] v2 异步调度器已停止")
