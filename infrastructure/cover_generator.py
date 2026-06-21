# -*- coding: utf-8 -*-
"""
封面图生成器。

支持两种模式：
1. 调用 LLM 生成提示词，再调用图片生成 API（如 DALL-E）获取真实图片。
2. 使用 Pillow 绘制文字封面（默认降级方案，无需图片生成 API）。
"""

import io
import json
import logging
import os
import re
from datetime import datetime
from typing import Any

import requests
from PIL import Image, ImageDraw, ImageFont

from config import (
    COVER_IMAGE_HEIGHT,
    COVER_IMAGE_WIDTH,
    IMAGE_GEN_API_KEY,
    IMAGE_GEN_API_URL,
    IMAGE_GEN_MODEL,
    IMAGE_GEN_SIZE,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    WECHAT_COVER_PROMPT_TEMPLATE,
    WECHAT_GENERATE_COVER_BY_LLM,
)

logger = logging.getLogger(__name__)


def _call_text_llm(prompt: str, max_tokens: int = 500) -> str:
    """调用配置的文字 LLM。"""
    if not OPENAI_API_KEY:
        raise RuntimeError("未配置 OPENAI_API_KEY，无法调用 LLM")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": "你是一个科技资讯封面设计师。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": max_tokens,
    }

    resp = requests.post(
        f"{OPENAI_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"].strip()
    return content


def _extract_json(text: str) -> dict[str, Any] | None:
    """从 LLM 返回文本中提取 JSON。"""
    # 尝试匹配 markdown 代码块
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        text = match.group(1)
    else:
        # 尝试匹配最外层大括号
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)
        else:
            return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _generate_cover_design(title: str, digest: str) -> dict[str, Any]:
    """调用 LLM 生成封面设计方案。"""
    prompt = WECHAT_COVER_PROMPT_TEMPLATE + f"\n\n标题：{title}\n摘要：{digest[:500]}"
    logger.info("正在调用 LLM 生成封面设计方案...")
    content = _call_text_llm(prompt)
    logger.debug("LLM 封面设计返回: %s", content)

    design = _extract_json(content) or {}
    return {
        "prompt": design.get("prompt", "科技 AI 资讯日报封面"),
        "primary_color": _validate_hex(design.get("primary_color", "#07C160")),
        "background_color": _validate_hex(design.get("background_color", "#0A0A0A")),
        "keyword": design.get("keyword", "AI日报"),
    }


def _validate_hex(value: str, default: str = "#07C160") -> str:
    """校验 HEX 颜色格式。"""
    if value and re.match(r"^#[0-9A-Fa-f]{6}$", str(value)):
        return str(value)
    return default


def _try_generate_real_image(prompt: str) -> bytes | None:
    """尝试调用图片生成 API 获取真实图片。"""
    if not IMAGE_GEN_API_URL:
        return None
    if not IMAGE_GEN_API_KEY:
        logger.warning("已配置 IMAGE_GEN_API_URL 但缺少 IMAGE_GEN_API_KEY，跳过图片生成")
        return None

    url = f"{IMAGE_GEN_API_URL.rstrip('/')}/images/generations"
    headers = {
        "Authorization": f"Bearer {IMAGE_GEN_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": IMAGE_GEN_MODEL,
        "prompt": prompt,
        "n": 1,
        "size": IMAGE_GEN_SIZE,
    }

    try:
        logger.info("正在调用图片生成 API: %s", url)
        resp = requests.post(url, headers=headers, json=payload, timeout=180)
        resp.raise_for_status()
        data = resp.json()
        image_url = data["data"][0]["url"]
        logger.info("图片生成成功，正在下载: %s", image_url[:80])
        image_resp = requests.get(image_url, timeout=60)
        image_resp.raise_for_status()
        return image_resp.content
    except Exception as e:
        logger.warning("图片生成 API 调用失败: %s", e)
        return None


def _draw_text_cover(title: str, date_text: str, keyword: str,
                     primary_color: str, background_color: str) -> bytes:
    """使用 Pillow 绘制文字封面。"""
    width, height = COVER_IMAGE_WIDTH, COVER_IMAGE_HEIGHT

    # 创建背景
    img = Image.new("RGB", (width, height), background_color)
    draw = ImageDraw.Draw(img)

    # 尝试加载字体，失败则使用默认字体
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
        "C:/Windows/Fonts/simhei.ttf",  # 黑体
        "C:/Windows/Fonts/simsun.ttc",  # 宋体
        "/System/Library/Fonts/PingFang.ttc",  # macOS
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",  # Linux
    ]
    font_large = None
    font_medium = None
    font_small = None

    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                font_large = ImageFont.truetype(font_path, 72)
                font_medium = ImageFont.truetype(font_path, 40)
                font_small = ImageFont.truetype(font_path, 32)
                break
            except Exception:
                continue

    if font_large is None:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # 绘制装饰性几何图形
    draw.rectangle([0, 0, width, 12], fill=primary_color)
    draw.rectangle([width - 200, height - 200, width, height], fill=primary_color + "33")

    # 主题词
    bbox = draw.textbbox((0, 0), keyword, font=font_small)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) / 2, 80), keyword, font=font_small, fill=primary_color)

    # 标题（自动换行）
    wrapped_title = _wrap_text(draw, title, font_large, width - 120)
    draw.text((60, 160), wrapped_title, font=font_large, fill="#FFFFFF" if _is_dark(background_color) else "#1A1A1A")

    # 日期
    bbox = draw.textbbox((0, 0), date_text, font=font_medium)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) / 2, height - 100), date_text, font=font_medium, fill=primary_color)

    # 底部品牌
    brand = "Agently.top"
    bbox = draw.textbbox((0, 0), brand, font=font_small)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) / 2, height - 50), brand, font=font_small, fill="#888888")

    output = io.BytesIO()
    img.save(output, format="JPEG", quality=90)
    return output.getvalue()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    """简单的中文文本换行。"""
    lines = []
    current_line = ""
    for char in text:
        test_line = current_line + char
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = char
    if current_line:
        lines.append(current_line)
    return "\n".join(lines[:3])  # 最多 3 行


def _is_dark(hex_color: str) -> bool:
    """判断颜色是否为深色背景。"""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    return brightness < 128


def generate_cover_image(title: str, digest: str = "", content: str = "") -> bytes:
    """
    生成封面图。

    Args:
        title: 文章标题。
        digest: 摘要。
        content: 正文内容，用于给 LLM 更多上下文。

    Returns:
        图片二进制数据（JPEG）。
    """
    if not WECHAT_GENERATE_COVER_BY_LLM:
        raise RuntimeError("WECHAT_GENERATE_COVER_BY_LLM 未启用")

    # 准备给 LLM 的摘要文本
    context = digest or content[:300] or title

    # 1. 调用 LLM 获取设计方案
    design = _generate_cover_design(title, context)

    # 2. 尝试生成真实图片
    image_bytes = _try_generate_real_image(design["prompt"])
    if image_bytes:
        return image_bytes

    # 3. 降级：Pillow 绘制文字封面
    date_text = datetime.now().strftime("%Y-%m-%d")
    logger.info("使用 Pillow 绘制文字封面")
    return _draw_text_cover(
        title=title,
        date_text=date_text,
        keyword=design["keyword"],
        primary_color=design["primary_color"],
        background_color=design["background_color"],
    )
