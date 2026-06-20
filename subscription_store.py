# -*- coding: utf-8 -*-
"""
邮件订阅者管理。

提供订阅邮箱的持久化存储与读取，订阅者会在定时邮件发送时自动合并到收件人列表。
"""

import json
import logging
import os
import re

from config import OUTPUT_ARCHIVE_DIR

logger = logging.getLogger(__name__)

SUBSCRIBERS_FILE = os.path.join(OUTPUT_ARCHIVE_DIR, "subscribers.json")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_email(email):
    """清洗并标准化邮箱地址。"""
    if not email or not isinstance(email, str):
        return ""
    return email.strip().lower()


def is_valid_email(email):
    """校验邮箱格式是否合法。"""
    return bool(_EMAIL_RE.match(_normalize_email(email)))


def load_subscribers():
    """
    读取所有订阅邮箱。

    Returns:
        list[str]: 去重后的邮箱列表
    """
    if not os.path.exists(SUBSCRIBERS_FILE):
        return []
    try:
        with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            seen = set()
            result = []
            for item in data:
                email = _normalize_email(item)
                if email and is_valid_email(email) and email not in seen:
                    seen.add(email)
                    result.append(email)
            return result
    except Exception as e:
        logger.warning("读取订阅者列表失败: %s", e)
    return []


def add_subscriber(email):
    """
    添加一个订阅邮箱。

    Args:
        email: 邮箱地址

    Returns:
        tuple[bool, str]: (是否成功, 状态说明)
    """
    email = _normalize_email(email)
    if not email:
        return False, "empty_email"
    if not is_valid_email(email):
        return False, "invalid_email"

    subscribers = load_subscribers()
    if email in subscribers:
        return True, "already_subscribed"

    subscribers.append(email)
    try:
        os.makedirs(os.path.dirname(SUBSCRIBERS_FILE), exist_ok=True)
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            json.dump(subscribers, f, ensure_ascii=False, indent=2)
        logger.info("新增邮件订阅者: %s", email)
        return True, "subscribed"
    except Exception as e:
        logger.error("保存订阅者失败: %s", e)
        return False, "save_failed"
