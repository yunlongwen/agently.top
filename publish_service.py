# -*- coding: utf-8 -*-
"""
每日发布编排服务。

负责在采集完成后，根据配置自动调用各个启用的发布器。
"""

import json
import logging
from datetime import datetime
from typing import Any

from config import (
    ADMIN_API_TOKEN,
    PUBLISH_ENABLED,
    PUBLISH_SCHEDULE_TIMES,
    WECHAT_CONTENT_SOURCE_URL,
    WECHAT_DEFAULT_AUTHOR,
    WECHAT_DEFAULT_DIGEST,
    WECHAT_DEFAULT_TITLE,
)
from publishers import registry
from wechat_article_builder import build_daily_markdown

logger = logging.getLogger(__name__)


def _parse_schedule_times(value: str) -> set[str]:
    """解析 HH:MM,HH:MM 格式的调度时间。"""
    result = set()
    for item in (value or "").split(","):
        text = item.strip()
        if not text:
            continue
        try:
            hour_text, minute_text = text.split(":", 1)
            hour = int(hour_text)
            minute = int(minute_text)
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                result.add("{:02d}:{:02d}".format(hour, minute))
        except ValueError:
            logger.warning("忽略无效的发布调度时间: %s", item)
    return result


def _normalize_time(scheduled_time: Any) -> str:
    """把调度时间规整为 HH:MM。"""
    if scheduled_time is None:
        return ""
    if hasattr(scheduled_time, "strftime"):
        return scheduled_time.strftime("%H:%M")
    text = str(scheduled_time).strip()
    if len(text) >= 5:
        return text[:5]
    return text


def _resolve_content_source_url(items: list[dict]) -> str:
    """
    确定微信公众号文章底部「阅读原文」跳转 URL。

    优先级：
    1. 环境变量 WECHAT_CONTENT_SOURCE_URL
    2. 当日第一条资讯的 url
    3. 站点首页兜底
    """
    if WECHAT_CONTENT_SOURCE_URL:
        return WECHAT_CONTENT_SOURCE_URL
    for item in items or []:
        url = (item.get("url") or "").strip()
        if url:
            return url
    return "https://agently.top/"


def _should_publish_at(scheduled_time: Any) -> bool:
    """判断当前调度时间是否应该执行发布。"""
    if not PUBLISH_SCHEDULE_TIMES:
        # 未单独配置，跟随每次采集后发布
        return True

    allowed_times = _parse_schedule_times(PUBLISH_SCHEDULE_TIMES)
    if not allowed_times:
        return True

    current_time = _normalize_time(scheduled_time)
    return current_time in allowed_times


def publish_daily(items: list[dict], scheduled_time: Any = None) -> dict[str, Any]:
    """
    每日发布编排入口。

    Args:
        items: 统一信息项列表。
        scheduled_time: 触发本次发布的调度时间（用于判断是否在允许时间段）。

    Returns:
        dict: 各发布器的执行结果。
    """
    results = {"published_at": datetime.now().isoformat(), "publishers": {}}

    if not PUBLISH_ENABLED:
        logger.info("发布编排已关闭（PUBLISH_ENABLED=false）")
        results["skipped"] = True
        results["reason"] = "PUBLISH_ENABLED=false"
        return results

    if not _should_publish_at(scheduled_time):
        normalized = _normalize_time(scheduled_time)
        logger.info("当前调度时间 %s 不在 PUBLISH_SCHEDULE_TIMES 中，跳过发布", normalized)
        results["skipped"] = True
        results["reason"] = f"time {normalized} not in publish schedule"
        return results

    # 触发自动发现（如果尚未执行）
    if not registry.list_all():
        registry.auto_discover("publishers")

    enabled_publishers = registry.list_enabled()
    if not enabled_publishers:
        logger.info("没有启用的发布器")
        results["skipped"] = True
        results["reason"] = "no enabled publishers"
        return results

    date_text = datetime.now().strftime("%Y-%m-%d")
    markdown_content = build_daily_markdown(items, date_text=date_text)

    common_options = {
        "display_date": date_text,
        "title": WECHAT_DEFAULT_TITLE.replace("{date}", date_text),
        "author": WECHAT_DEFAULT_AUTHOR,
        "digest": WECHAT_DEFAULT_DIGEST,
        "content_source_url": _resolve_content_source_url(items),
    }

    for publisher in enabled_publishers:
        publisher_id = publisher.id
        logger.info("开始执行发布器: %s", publisher.name)
        try:
            result = publisher.publish(markdown_content, options=common_options)
            results["publishers"][publisher_id] = result
            logger.info("发布器 %s 执行成功: %s", publisher_id, result)
        except Exception as e:
            logger.exception("发布器 %s 执行失败: %s", publisher_id, e)
            results["publishers"][publisher_id] = {
                "success": False,
                "error": str(e),
            }

    return results


def publish_to(publisher_id: str, items: list[dict] | None = None,
               content: str | None = None, options: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    手动触发指定发布器。

    Args:
        publisher_id: 发布器 ID，如 wechat。
        items: 信息项列表。若提供则自动生成 Markdown；与 content 二选一。
        content: 直接传入的内容（Markdown/HTML）。
        options: 发布选项。

    Returns:
        dict: 发布结果。
    """
    if not registry.list_all():
        registry.auto_discover("publishers")

    publisher = registry.get(publisher_id)
    if not publisher:
        return {"success": False, "error": f"Unknown publisher: {publisher_id}"}

    if items and not content:
        date_text = datetime.now().strftime("%Y-%m-%d")
        content = build_daily_markdown(items, date_text=date_text)
        if "content_source_url" not in options:
            options["content_source_url"] = _resolve_content_source_url(items)
    elif not content:
        content = ""

    options = options or {}
    if "title" not in options:
        date_text = datetime.now().strftime("%Y-%m-%d")
        options["title"] = WECHAT_DEFAULT_TITLE.replace("{date}", date_text)
    if "author" not in options:
        options["author"] = WECHAT_DEFAULT_AUTHOR
    if "digest" not in options:
        options["digest"] = WECHAT_DEFAULT_DIGEST

    return publisher.publish(content, options=options)


def get_publish_status() -> dict[str, Any]:
    """获取当前发布器状态。"""
    if not registry.list_all():
        registry.auto_discover("publishers")

    return {
        "publish_enabled": PUBLISH_ENABLED,
        "publish_schedule_times": PUBLISH_SCHEDULE_TIMES,
        "admin_token_configured": bool(ADMIN_API_TOKEN),
        "publishers": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "enabled": p.is_enabled(),
            }
            for p in registry.list_all()
        ],
    }


def is_admin_authorized(ip: str, token: str) -> bool:
    """判断管理接口是否已授权。"""
    from stats import _is_private_ip

    if ADMIN_API_TOKEN:
        return token == ADMIN_API_TOKEN
    # 未配置 token 时，仅允许内网访问
    return _is_private_ip(ip)


# 导入内置发布器，确保 auto_discover 能找到它们
# 放在文件末尾避免循环导入
from publishers import wechat  # noqa: F401,E402
