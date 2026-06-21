# -*- coding: utf-8 -*-
"""
邮件发送模块

负责 SMTP 邮件发送和失败通知。
"""

import logging
import smtplib
from datetime import datetime
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import (
    MAIL_FROM,
    MAIL_TO,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_SERVER,
    SMTP_USER,
)

logger = logging.getLogger(__name__)


def _parse_recipients(recipients=None):
    """解析 MAIL_TO 配置，支持多收件人（逗号分隔）。"""
    value = MAIL_TO if recipients is None else recipients
    if isinstance(value, str):
        return [r.strip() for r in value.split(",") if r.strip()]
    return value if isinstance(value, list) else [value]


def send_email(html_content, subject, recipients=None):
    """
    通过 SMTP 发送 HTML 邮件。

    为防收件人互相看到邮箱地址，每个收件人单独发送一封邮件。

    Args:
        html_content: HTML 邮件正文
        subject: 邮件主题
        recipients: 收件人列表，默认读取 MAIL_TO

    Returns:
        bool: 是否所有邮件都发送成功
    """
    recipients = _parse_recipients(recipients)
    if not recipients:
        logger.warning("没有收件人，跳过邮件发送")
        return False

    text_part = MIMEText("请使用支持 HTML 的邮件客户端查看此邮件。", "plain", "utf-8")
    html_part = MIMEText(html_content, "html", "utf-8")

    try:
        if SMTP_PORT == 587:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30)

        with server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            all_success = True
            for recipient in recipients:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = Header(subject, "utf-8")
                msg["From"] = MAIL_FROM
                msg["To"] = recipient
                msg.attach(text_part)
                msg.attach(html_part)
                try:
                    server.sendmail(MAIL_FROM, [recipient], msg.as_string())
                    logger.info("邮件发送成功！收件人: %s", recipient)
                except Exception as e:
                    logger.error("发送邮件给 %s 失败: %s", recipient, e)
                    all_success = False
            return all_success
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP 认证失败，请检查邮箱账号和授权码")
    except smtplib.SMTPException as e:
        logger.error("SMTP 错误: %s", e)
    except Exception as e:
        logger.error("邮件发送异常: %s", e)

    return False


def send_failure_notify(error_msg, recipients=None):
    """当主流程失败时，给每个收件人单独发送一封失败通知邮件。"""
    recipients = _parse_recipients(recipients)
    if not recipients:
        logger.warning("没有收件人，跳过失败通知邮件")
        return False

    today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body = (
        "GitHub + HN 热点报告 Spider 运行失败\n\n"
        "时间: {}\n"
        "错误: {}\n\n"
        "请检查服务器日志: /root/logs/github-python/trending.log".format(today, error_msg)
    )

    try:
        if SMTP_PORT == 587:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30)

        with server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            all_success = True
            for recipient in recipients:
                msg = MIMEText(body, "plain", "utf-8")
                msg["Subject"] = Header("[FAIL] GitHub + HN Spider - {}".format(today), "utf-8")
                msg["From"] = MAIL_FROM
                msg["To"] = recipient
                try:
                    server.sendmail(MAIL_FROM, [recipient], msg.as_string())
                except Exception as e:
                    logger.error("发送失败通知给 %s 失败: %s", recipient, e)
                    all_success = False
            if all_success:
                logger.info("失败通知邮件已发送")
            return all_success
    except Exception as e:
        logger.error("发送失败通知邮件也失败了: %s", e)

    return False
