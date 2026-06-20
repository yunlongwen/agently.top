# -*- coding: utf-8 -*-
"""
微信公众号发布器。

实现 Publisher 接口，对外提供 publish() 方法。
"""

import logging
import re
from datetime import datetime
from typing import Any

from config import WECHAT_GENERATE_COVER_BY_LLM, WECHAT_DEFAULT_COVER_URL
from publishers.base import Publisher
from publishers.wechat.config import WechatConfig
from publishers.wechat.renderer import WechatRenderer
from publishers.wechat.service import WechatService

logger = logging.getLogger(__name__)


class WechatPublisher(Publisher):
    """微信公众号发布器。"""

    def __init__(self, config: WechatConfig | None = None):
        self._config = config or WechatConfig.from_env()
        self._service = WechatService.get_instance(self._config)
        self._renderer = WechatRenderer()

    @property
    def id(self) -> str:
        return "wechat"

    @property
    def name(self) -> str:
        return "微信公众号"

    @property
    def description(self) -> str:
        return "发布到微信公众号草稿箱"

    def is_enabled(self) -> bool:
        import config as app_config
        return getattr(app_config, "WECHAT_PUBLISH_ENABLED", False) and self._config.is_valid()

    def publish(self, content: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        发布内容到微信公众号草稿箱。

        Args:
            content: Markdown 或 HTML 内容。
            options: 可选参数 title, author, digest, display_date, thumb_media_id。
        """
        options = options or {}
        title = options.get("title") or self._build_title(options.get("display_date"))
        author = options.get("author") or self._config.author
        digest = options.get("digest") or self._config.digest

        logger.info("开始发布到微信公众号: %s", title)

        # 1. 判断是否为 HTML，不是则渲染
        is_html = bool(re.search(r"<\/(p|div|section|h[1-6]|table|ul|ol)>", content, re.I))
        if not is_html:
            html_content = self._renderer.convert(content)
        else:
            html_content = content

        # 2. 清理多余空白和 &nbsp;
        html_content = self._clean_html(html_content)

        # 3. 处理图片上传
        try:
            processed_html, first_media_id, _ = self._service.process_html_images(html_content)
        except Exception as e:
            logger.error("处理正文图片失败: %s", e)
            processed_html = html_content
            first_media_id = None

        # 4. 封面图 media_id
        thumb_media_id = options.get("thumb_media_id")
        if not thumb_media_id:
            thumb_media_id = first_media_id
        if not thumb_media_id:
            thumb_media_id = self._resolve_thumb_media_id(title, digest, content)

        if not thumb_media_id:
            raise RuntimeError("无法获取封面图 media_id")

        # 5. 发布草稿
        result = self._service.publish_draft(
            title=title,
            content=processed_html,
            thumb_media_id=thumb_media_id,
            author=author,
            digest=digest,
            content_source_url=options.get("content_source_url", ""),
        )

        return {
            "success": True,
            "media_id": result.get("media_id"),
            "title": title,
            "publisher": self.id,
        }

    def _resolve_thumb_media_id(self, title: str, digest: str, content: str) -> str | None:
        """获取封面图 media_id：优先使用默认封面图，其次 LLM 生成，最后兜底 URL。"""
        # 4.1 优先使用默认品牌封面图
        if WECHAT_DEFAULT_COVER_URL:
            try:
                material = self._service.upload_material(WECHAT_DEFAULT_COVER_URL)
                media_id = material.get("media_id")
                if media_id:
                    logger.info("默认封面图已上传，media_id=%s", media_id)
                    return media_id
            except Exception as e:
                logger.warning("上传默认封面图失败: %s", e)

        # 4.2 尝试 LLM 生成封面
        if WECHAT_GENERATE_COVER_BY_LLM:
            try:
                from cover_generator import generate_cover_image
                image_bytes = generate_cover_image(title=title, digest=digest, content=content)
                material = self._service.upload_material(image_bytes)
                media_id = material.get("media_id")
                if media_id:
                    logger.info("LLM 生成封面图已上传，media_id=%s", media_id)
                    return media_id
            except Exception as e:
                logger.warning("LLM 生成封面失败: %s", e)

        # 4.3 兜底 URL
        try:
            fallback = self._service.upload_material(self._config.fallback_logo_url)
            return fallback.get("media_id")
        except Exception as e:
            logger.error("上传兜底封面图失败: %s", e)
            return None

    def _build_title(self, display_date: str | None = None) -> str:
        """构建标题。"""
        template = self._config.title or "Agently.top 每日 AI 资讯 - {date}"
        date_text = display_date or datetime.now().strftime("%Y-%m-%d")
        return template.replace("{date}", date_text)

    @staticmethod
    def _clean_html(html: str) -> str:
        """清理 HTML 中的多余空白。"""
        html = html.replace("&nbsp;", " ")
        # 合并连续空白
        html = re.sub(r"\s{2,}", " ", html)
        return html.strip()


# 模块级实例，供注册表自动发现
publisher = WechatPublisher()
