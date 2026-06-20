# -*- coding: utf-8 -*-
"""
微信公众号发布器配置。
"""

from dataclasses import dataclass


@dataclass
class WechatConfig:
    """微信公众号配置。"""

    app_id: str
    app_secret: str
    title: str = ""
    author: str = ""
    digest: str = ""
    base_url: str = "https://api.weixin.qq.com"
    fallback_logo_url: str = "https://agently.top/android-chrome-192x192.png"

    @classmethod
    def from_env(cls) -> "WechatConfig":
        """从 config 模块的环境变量构建配置。"""
        import config

        return cls(
            app_id=getattr(config, "WECHAT_APP_ID", ""),
            app_secret=getattr(config, "WECHAT_APP_SECRET", ""),
            title=getattr(config, "WECHAT_DEFAULT_TITLE", "Agently.top 每日 AI 资讯 - {date}"),
            author=getattr(config, "WECHAT_DEFAULT_AUTHOR", "Agently"),
            digest=getattr(config, "WECHAT_DEFAULT_DIGEST", ""),
            base_url=getattr(config, "WECHAT_API_BASE_URL", "https://api.weixin.qq.com"),
            fallback_logo_url=getattr(config, "WECHAT_FALLBACK_LOGO_URL", "https://agently.top/android-chrome-192x192.png"),
        )

    def is_valid(self) -> bool:
        """配置是否有效。"""
        return bool(self.app_id and self.app_secret)
