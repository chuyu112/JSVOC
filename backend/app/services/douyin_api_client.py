"""Client for Douyin_TikTok_Download_API (local).

GitHub: https://github.com/Evil0ctal/Douyin_TikTok_Download_API
Endpoint: GET /api/hybrid/video_data?url=...
"""

import logging
import tempfile
import os
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_API_URL = "http://127.0.0.1:80"


class DouyinAPIClient:
    """Client for Douyin video download API."""

    def __init__(self, base_url: str | None = None) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.douyin_api_url or DEFAULT_API_URL).rstrip("/")
        self.client = httpx.Client(timeout=60.0)

    def parse_video(self, url: str) -> dict[str, Any]:
        """Parse Douyin video URL and return video info.

        Returns:
            {
                "title": "...",
                "author": "...",
                "desc": "...",
                "video_url": "...",
                "cover_url": "...",
            }
        """
        api_url = f"{self.base_url}/api/hybrid/video_data"
        resp = self.client.get(api_url, params={"url": url})
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 200:
            raise RuntimeError(data.get("msg", "解析失败"))

        video_data = data.get("data", {})

        # Extract video URL (prefer download_addr, fallback to play_addr)
        video_url = ""
        v = video_data.get("video", {})
        download = v.get("download_addr")
        if isinstance(download, dict):
            urls = download.get("url_list", [])
            if urls:
                video_url = urls[0]

        if not video_url:
            play = v.get("play_addr")
            if isinstance(play, dict):
                urls = play.get("url_list", [])
                if urls:
                    video_url = urls[0]

        # Cover
        cover_url = ""
        cover = video_data.get("cover")
        if isinstance(cover, dict):
            urls = cover.get("url_list", [])
            if urls:
                cover_url = urls[0]

        return {
            "title": video_data.get("desc", "")[:200],
            "author": video_data.get("author", {}).get("nickname", ""),
            "desc": video_data.get("desc", ""),
            "video_url": video_url,
            "cover_url": cover_url,
            "aweme_id": str(video_data.get("aweme_id", "")),
        }

    def download_video(self, video_url: str) -> str:
        """Download video to temp file, return path."""
        suffix = ".mp4"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            with self.client.stream("GET", video_url, headers={
                "Referer": "https://www.douyin.com/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }) as resp:
                resp.raise_for_status()
                for chunk in resp.iter_bytes():
                    tmp.write(chunk)
            return tmp.name

    def health_check(self) -> bool:
        try:
            resp = self.client.get(f"{self.base_url}/docs", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False
