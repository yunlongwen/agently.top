#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 SMTP 发送邮件

使用前确保环境变量已配置：
  export SMTP_USER="your@163.com"
  export SMTP_PASSWORD="your_auth_code"
  export MAIL_TO="receiver@qq.com"
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header

# 尝试读取 .env 文件
def load_env_file():
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('export '):
                    line = line[7:]  # 去掉 'export '
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key not in os.environ:
                        os.environ[key] = value

load_env_file()

# 从环境变量读取配置
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.163.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
MAIL_FROM = os.environ.get("MAIL_FROM", SMTP_USER)
MAIL_TO = os.environ.get("MAIL_TO", "")

if not SMTP_USER or not SMTP_PASSWORD or not MAIL_TO:
    print("请先配置环境变量: SMTP_USER, SMTP_PASSWORD, MAIL_TO")
    print("例如: export SMTP_USER='your@163.com'")
    exit(1)

print(f"SMTP_SERVER: {SMTP_SERVER}")
print(f"SMTP_PORT: {SMTP_PORT}")
print(f"SMTP_USER: {SMTP_USER}")
print(f"MAIL_FROM: {MAIL_FROM}")
print(f"MAIL_TO: {MAIL_TO}")


def _create_smtp_connection():
    """根据端口创建 SMTP 连接（SSL 或 STARTTLS）"""
    if SMTP_PORT == 587:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
        server.starttls()
    else:
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30)
    return server


def test_simple_text():
    """测试 1: 发送纯文本邮件"""
    print("测试 1: 纯文本邮件...")

    msg = MIMEText("这是一封测试邮件（纯文本）", "plain", "utf-8")
    msg["Subject"] = "测试邮件 - 纯文本"
    msg["From"] = MAIL_FROM
    msg["To"] = MAIL_TO

    try:
        with _create_smtp_connection() as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(MAIL_FROM, [MAIL_TO], msg.as_string())
        print("✅ 测试 1 成功")
        return True
    except Exception as e:
        print("❌ 测试 1 失败: {}".format(e))
        return False


def test_html_email():
    """测试 2: 发送 HTML 邮件"""
    print("\n测试 2: HTML 邮件...")

    html_content = """
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body>
        <h1>测试邮件</h1>
        <p>这是一封 <strong>HTML</strong> 测试邮件。</p>
        <p>包含中文：你好世界！</p>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "测试邮件 - HTML"
    msg["From"] = MAIL_FROM
    msg["To"] = MAIL_TO

    text_part = MIMEText("请使用支持 HTML 的邮件客户端。", "plain", "utf-8")
    html_part = MIMEText(html_content, "html", "utf-8")
    msg.attach(text_part)
    msg.attach(html_part)

    try:
        with _create_smtp_connection() as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(MAIL_FROM, [MAIL_TO], msg.as_string())
        print("✅ 测试 2 成功")
        return True
    except Exception as e:
        print("❌ 测试 2 失败: {}".format(e))
        return False


def test_chinese_subject():
    """测试 3: 中文主题邮件"""
    print("\n测试 3: 中文主题邮件...")

    msg = MIMEText("测试中文主题", "plain", "utf-8")
    msg["Subject"] = Header("GitHub Trending 热点报告 - 2026-02-24", "utf-8")
    msg["From"] = MAIL_FROM
    msg["To"] = MAIL_TO

    try:
        with _create_smtp_connection() as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(MAIL_FROM, [MAIL_TO], msg.as_string())
        print("✅ 测试 3 成功")
        return True
    except Exception as e:
        print("❌ 测试 3 失败: {}".format(e))
        return False


def test_full_html_with_chinese():
    """测试 4: 完整 HTML + 中文主题"""
    print("\n测试 4: 完整 HTML + 中文主题...")

    html_content = """
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h1 style="color: #0366d6;">🔥 GitHub Trending 热点报告</h1>
        <table border="1" style="border-collapse: collapse; width: 100%;">
            <tr style="background: #0366d6; color: white;">
                <th>项目</th>
                <th>Stars</th>
            </tr>
            <tr>
                <td>test/repo</td>
                <td>1,234</td>
            </tr>
        </table>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header("GitHub Trending 热点报告 - 2026-02-24", "utf-8")
    msg["From"] = MAIL_FROM
    msg["To"] = MAIL_TO

    text_part = MIMEText("请使用支持 HTML 的邮件客户端查看此邮件。", "plain", "utf-8")
    html_part = MIMEText(html_content, "html", "utf-8")
    msg.attach(text_part)
    msg.attach(html_part)

    try:
        with _create_smtp_connection() as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(MAIL_FROM, [MAIL_TO], msg.as_string())
        print("✅ 测试 4 成功")
        return True
    except Exception as e:
        print("❌ 测试 4 失败: {}".format(e))
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("163 邮箱 SMTP 测试")
    print("=" * 60)

    results = []
    results.append(("纯文本", test_simple_text()))
    results.append(("HTML", test_html_email()))
    results.append(("中文主题", test_chinese_subject()))
    results.append(("完整测试", test_full_html_with_chinese()))

    print("\n" + "=" * 60)
    print("测试结果汇总:")
    for name, success in results:
        status = "✅" if success else "❌"
        print("{} {}".format(status, name))
    print("=" * 60)
