"""Client for local Douyin_TikTok_Download_API service.

GitHub: https://github.com/Evil0ctal/Douyin_TikTok_Download_API
Deploy: run deploy_douyin_api.bat
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_API_URL = "http://127.0.0.1:9000"


class DouyinAPIClient:
    """Client for Douyin video download API."""

    def __init__(self, base_url: str = DEFAULT_API_URL) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=30.0)

    def parse_video(self, url: str) -> dict[str, Any]:
        """Parse Douyin video URL and return download info.

        Args:
            url: Douyin share link, e.g. https://v.douyin.com/xxxxx

        Returns:
            Dict with video_url, title, author, etc.
        """
        api_url = f"{self.base_url}/api"
        try:
            resp = self.client.get(api_url, params={"url": url})
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "success":
                raise RuntimeError(data.get("message", "解析失败"))

            return data.get("data", {})
        except httpx.ConnectError as exc:
            raise RuntimeError(
                f"抖音解析API未启动，请先运行 deploy_douyin_api.bat"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"解析API返回错误: {exc.response.status_code}") from exc

    def health_check(self) -> bool:
        """Check if API service is running."""
        try:
            resp = self.client.get(f"{self.base_url}/docs", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False
