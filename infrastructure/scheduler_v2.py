# -*- coding: utf-8 -*-
"""按源异步调度器 v2。"""

import asyncio
import logging
import threading
from datetime import datetime, timedelta

from app_config import get_source_interval, load_app_config
from config import EMAIL_SEND_TIMES
from core.source_registry import SOURCE_DEFINITIONS

logger = logging.getLogger(__name__)

_stop_event = asyncio.Event()
_scheduler_thread: threading.Thread | None = None
_daily_email_thread: threading.Thread | None = None
_email_run_lock = threading.Lock()
_email_stop_event = threading.Event()


def run_source(source_id: str) -> bool:
    """执行单源采集。

    返回 True 表示 run_spider 返回真值且未抛出异常，
    返回 False 表示 run_spider 返回假值或执行过程中抛出异常。

    TODO(Phase 2): 当前仍调用整体 run_spider()，会执行所有来源。
    这是 Phase 1 的已知简化（见计划 brief）。后续应引入 run_source_only(source_id)
    实现真正的按源采集，避免每次 tick 都全量运行。
    """
    from main import run_spider
    logger.info("[调度] 执行来源: %s", source_id)
    try:
        # scheduled_time=None：标记为「非定时调度触发」，
        # _email_send_decision 会判定不发送邮件。
        # 邮件发送由每天 7:50 的独立线程负责。
        return bool(run_spider(scheduled_time=None))
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
        if not source.get("enabled", True):
            continue
        if source.get("kind") != "builtin":
            continue
        interval = get_source_interval(source["id"], source.get("display_priority", "medium"), config)
        tasks.append(asyncio.create_task(schedule_source(source["id"], interval)))
    await asyncio.gather(*tasks, return_exceptions=True)


def _run_scheduler_in_thread():
    asyncio.run(scheduler_loop())


def _parse_email_send_times(value):
    """解析 HH:MM,HH:MM 格式。"""
    result = []
    for item in (value or "").split(","):
        text = item.strip()
        if not text:
            continue
        hour_text, minute_text = text.split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            raise ValueError("邮件发送时间超出范围: {}".format(text))
        result.append((hour, minute))
    return sorted(set(result))


def _next_email_trigger(now, send_times):
    """计算下一次邮件发送触发的 datetime。"""
    for hour, minute in send_times:
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate > now:
            return candidate
    first_hour, first_minute = send_times[0]
    tomorrow = now + timedelta(days=1)
    return tomorrow.replace(
        hour=first_hour, minute=first_minute, second=0, microsecond=0,
    )


def _run_daily_email_loop(send_times):
    """每天在 EMAIL_SEND_TIMES 触发的时刻跑一次 run_spider 并发送邮件。"""
    while not _email_stop_event.is_set():
        now = datetime.now()
        next_run = _next_email_trigger(now, send_times)
        wait_seconds = max(1, int((next_run - now).total_seconds()))
        logger.info(
            "[邮件调度] 下一次邮件采集时间: %s",
            next_run.isoformat(timespec="seconds"),
        )
        if _email_stop_event.wait(wait_seconds):
            break
        if not _email_run_lock.acquire(blocking=False):
            logger.warning("[邮件调度] 已有采集任务运行中，跳过本次邮件触发")
            continue
        try:
            from main import run_spider

            logger.info(
                "[邮件调度] 开始执行: %s",
                datetime.now().isoformat(timespec="seconds"),
            )
            # 传入具体时刻，让 _email_send_decision 命中 EMAIL_SEND_TIMES 判定
            run_spider(scheduled_time=next_run)
        except Exception as e:
            logger.exception("[邮件调度] 执行异常: %s", e)
        finally:
            _email_run_lock.release()


def start_scheduler_v2():
    """启动 v2 调度器 + 邮件专用调度线程。"""
    global _scheduler_thread
    global _daily_email_thread

    if _scheduler_thread and _scheduler_thread.is_alive():
        logger.info("[调度] v2 异步调度器已在运行")
    else:
        _stop_event.clear()
        _scheduler_thread = threading.Thread(
            target=_run_scheduler_in_thread, name="scheduler-v2", daemon=True,
        )
        _scheduler_thread.start()
        logger.info("[调度] v2 异步调度器已启动")

    # 邮件专用线程：每天在 EMAIL_SEND_TIMES 配置的时刻跑一次 run_spider
    try:
        send_times = _parse_email_send_times(EMAIL_SEND_TIMES)
    except ValueError as e:
        logger.error("[邮件调度] EMAIL_SEND_TIMES 配置无效: %s", e)
        return

    if not send_times:
        logger.info("[邮件调度] EMAIL_SEND_TIMES 为空，不启动邮件调度")
        return

    if _daily_email_thread and _daily_email_thread.is_alive():
        logger.info("[邮件调度] 邮件专用调度已在运行")
        return

    _daily_email_thread = threading.Thread(
        target=_run_daily_email_loop,
        args=(send_times,),
        name="daily-email-scheduler",
        daemon=True,
    )
    _daily_email_thread.start()
    logger.info("[邮件调度] 每天 %s 触发邮件的调度线程已启动", EMAIL_SEND_TIMES)


def stop_scheduler_v2():
    """停止 v2 调度器 + 邮件专用线程。"""
    _stop_event.set()
    _email_stop_event.set()
    for thread in (_scheduler_thread, _daily_email_thread):
        if thread and thread.is_alive():
            thread.join(timeout=5)
    logger.info("[调度] v2 调度器与邮件调度线程已停止")
