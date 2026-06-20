# -*- coding: utf-8 -*-
"""
微信公众号 API 服务。

负责 access_token 管理、图片上传、草稿箱发布。
"""

import io
import json
import logging
import mimetypes
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from PIL import Image

from publishers.wechat.config import WechatConfig

logger = logging.getLogger(__name__)


class WechatService:
    """微信公众号 API 封装。"""

    _instance: "WechatService | None" = None

    def __new__(cls, *args, **kwargs):
        """单例模式，全局共享 access_token。"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config: WechatConfig | None = None):
        if self._initialized and config is None:
            return
        self.config = config or WechatConfig.from_env()
        self._access_token: str | None = None
        self._token_expires_at: float = 0
        self._session = requests.Session()
        self._initialized = True

    @classmethod
    def get_instance(cls, config: WechatConfig | None = None) -> "WechatService":
        return cls(config)

    def _request(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        """发送请求并解析 JSON。

        重要: 微信公众号 draft/add 接口对 content 字段不做 JSON 二次解码,
        requests.post(json=...) 走 ensure_ascii=True 会把中文编码为 \\uXXXX
        字面字符串,被微信存进草稿后渲染成乱码。统一用 utf-8 字节发送。
        """
        try:
            if method == "POST" and "json" in kwargs:
                import json as _json
                body_bytes = _json.dumps(kwargs.pop("json"), ensure_ascii=False).encode("utf-8")
                kwargs.setdefault("data", body_bytes)
                kwargs.setdefault("headers", {})["Content-Type"] = "application/json; charset=utf-8"
            resp = self._session.request(method, url, timeout=60, **kwargs)
            resp.raise_for_status()
            data = resp.json()
            errcode = data.get("errcode")
            if errcode and errcode != 0:
                errmsg = data.get("errmsg", "Unknown error")
                raise RuntimeError(f"WeChat API error {errcode}: {errmsg}")
            return data
        except requests.RequestException as e:
            logger.error("WeChat API request failed: %s", e)
            raise

    def get_access_token(self) -> str:
        """
        获取微信公众号 access_token，带缓存。

        Token 有效期 7200 秒，系统在过期前 5 分钟自动刷新。
        """
        now = time.time()
        if self._access_token and now < self._token_expires_at:
            return self._access_token

        if not self.config.app_id or not self.config.app_secret:
            raise ValueError("WECHAT_APP_ID 和 WECHAT_APP_SECRET 必须配置")

        url = (
            f"{self.config.base_url}/cgi-bin/token"
            f"?grant_type=client_credential"
            f"&appid={self.config.app_id}"
            f"&secret={self.config.app_secret}"
        )
        data = self._request("GET", url)
        self._access_token = data["access_token"]
        expires_in = data.get("expires_in", 7200)
        # 提前 5 分钟过期，避免边界问题
        self._token_expires_at = now + expires_in - 300
        logger.info("WeChat access_token 已刷新，有效期 %d 秒", expires_in)
        return self._access_token

    def _process_image(self, image_source: str | bytes, max_size_bytes: int = 2 * 1024 * 1024) -> tuple[bytes, str, str]:
        """
        处理图片：下载/读取、格式转换、压缩。

        Args:
            image_source: 图片 URL、本地路径或二进制数据。
            max_size_bytes: 最大文件大小，超过则压缩。

        Returns:
            (file_bytes, filename, content_type)
        """
        if isinstance(image_source, str) and image_source.startswith(("http://", "https://")):
            resp = self._session.get(image_source, timeout=60)
            resp.raise_for_status()
            file_bytes = resp.content
            parsed = urlparse(image_source)
            filename = Path(parsed.path).name or "image.jpg"
            content_type = resp.headers.get("Content-Type", "")
        elif isinstance(image_source, str) and image_source.startswith("data:"):
            # Base64 data URL
            match = re.match(r"^data:([A-Za-z-+\/]+);base64,(.+)$", image_source)
            if not match:
                raise ValueError("Invalid data URL format")
            content_type = match.group(1)
            file_bytes = match.group(2).encode()
            ext = mimetypes.guess_extension(content_type) or ".jpg"
            filename = f"base64_upload_{int(time.time())}{ext}"
        elif isinstance(image_source, str):
            path = Path(image_source)
            if not path.exists():
                raise FileNotFoundError(f"Image not found: {image_source}")
            with open(path, "rb") as f:
                file_bytes = f.read()
            filename = path.name
            content_type, _ = mimetypes.guess_type(str(path))
        elif isinstance(image_source, bytes):
            file_bytes = image_source
            filename = f"upload_{int(time.time())}.jpg"
            content_type = "image/jpeg"
        else:
            raise TypeError("image_source must be URL, path, base64 string or bytes")

        content_type = content_type or "image/jpeg"
        if not filename:
            filename = "image.jpg"

        # 使用 Pillow 打开并处理
        try:
            img = Image.open(io.BytesIO(file_bytes))
            img = img.convert("RGB")

            # 如果原格式是 webp/avif/heif，强制转为 jpeg
            fmt = img.format.lower() if img.format else ""
            if fmt in ("webp", "avif", "heif") or "jpeg" not in content_type.lower():
                filename = re.sub(r"\.(webp|avif|heif|png|gif|bmp)$", ".jpg", filename, flags=re.I)
                if not filename.lower().endswith(".jpg"):
                    filename += ".jpg"
                content_type = "image/jpeg"

            # 压缩过大的图片
            output = io.BytesIO()
            quality = 90
            img.save(output, format="JPEG", quality=quality)
            while output.tell() > max_size_bytes and quality > 50:
                output = io.BytesIO()
                quality -= 10
                img.save(output, format="JPEG", quality=quality)

            file_bytes = output.getvalue()
        except Exception as e:
            logger.warning("Pillow 处理图片失败，使用原始数据: %s", e)

        return file_bytes, filename, content_type

    def upload_image_to_cdn(self, image_source: str | bytes) -> str:
        """
        上传图片到微信 CDN，返回微信可访问的 URL。

        用于正文图片替换。
        """
        file_bytes, filename, content_type = self._process_image(image_source)
        access_token = self.get_access_token()
        url = f"{self.config.base_url}/cgi-bin/media/uploadimg?access_token={access_token}"

        files = {"media": (filename, io.BytesIO(file_bytes), content_type)}
        data = self._request("POST", url, files=files)
        cdn_url = data.get("url")
        if not cdn_url:
            raise RuntimeError("WeChat uploadimg did not return url")
        logger.info("图片已上传至微信 CDN: %s", cdn_url)
        return cdn_url

    def upload_material(self, image_source: str | bytes) -> dict[str, Any]:
        """
        上传图片到微信素材库，返回 media_id 和 url。

        用于封面图。
        """
        file_bytes, filename, content_type = self._process_image(image_source)
        access_token = self.get_access_token()
        url = (
            f"{self.config.base_url}/cgi-bin/material/add_material"
            f"?access_token={access_token}"
            f"&type=image"
        )

        files = {"media": (filename, io.BytesIO(file_bytes), content_type)}
        data = self._request("POST", url, files=files)
        logger.info("素材已上传至微信素材库: media_id=%s", data.get("media_id"))
        return data

    def process_html_images(self, html: str) -> tuple[str, str | None, list[str]]:
        """
        处理 HTML 中的图片：上传到微信 CDN 并替换 src。

        Returns:
            (processed_html, first_media_id, all_media_ids)
            first_media_id 用于封面图兜底；all_media_ids 用于图文模式。
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        first_media_id: str | None = None
        all_media_ids: list[str] = []

        for idx, img in enumerate(soup.find_all("img")):
            src = img.get("src", "")
            if not src:
                continue

            try:
                # 对于外链图片，上传到微信 CDN
                if src.startswith(("http://", "https://")) or src.startswith("data:"):
                    cdn_url = self.upload_image_to_cdn(src)
                    img["src"] = cdn_url

                    # 同时上传素材库获取 media_id（封面图/图文列表使用）
                    material = self.upload_material(src)
                    media_id = material.get("media_id")
                    if media_id:
                        all_media_ids.append(media_id)
                        if first_media_id is None:
                            first_media_id = media_id
                else:
                    # 本地路径也尝试上传
                    material = self.upload_material(src)
                    media_id = material.get("media_id")
                    url = material.get("url", src)
                    img["src"] = url
                    if media_id:
                        all_media_ids.append(media_id)
                        if first_media_id is None:
                            first_media_id = media_id
            except Exception as e:
                logger.warning("处理 HTML 图片失败 (src=%s): %s", src[:80], e)
                # 保留原 src，不中断流程

        return str(soup), first_media_id, all_media_ids

    def publish_draft(self, title: str, content: str, thumb_media_id: str,
                      author: str = "", digest: str = "",
                      content_source_url: str = "") -> dict[str, Any]:
        """
        发布草稿到微信公众号草稿箱。

        API: POST /cgi-bin/draft/add
        """
        access_token = self.get_access_token()
        url = f"{self.config.base_url}/cgi-bin/draft/add?access_token={access_token}"

        article = {
            "title": title,
            "content": content,
            "thumb_media_id": thumb_media_id,
            "need_open_comment": 1,
            "only_fans_can_comment": 0,
        }
        if author:
            article["author"] = author
        if digest:
            article["digest"] = digest
        if content_source_url:
            article["content_source_url"] = content_source_url

        payload = {"articles": [article]}
        data = self._request("POST", url, json=payload)
        logger.info("微信公众号草稿已创建: media_id=%s", data.get("media_id"))
        return data
