"""Social auto upload service for multi-platform video distribution.

Wraps the social-auto-upload library (dreammis/social-auto-upload).
GitHub: https://github.com/dreammis/social-auto-upload

Supported platforms:
    - 抖音 (douyin)
    - 视频号 (shipinhao)
    - B站 (bilibili)
    - 小红书 (xiaohongshu)
    - 快手 (kuaishou)
    - TikTok (tiktok)

Usage:
    1. Install: pip install social-auto-upload playwright
    2. Login once per platform (saves cookies)
    3. Call publish() with video path and metadata
"""

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SOCIAL_UPLOAD_DIR = "C:\\social-auto-upload"


class SocialPublishService:
    """Multi-platform video publishing service."""

    def __init__(self, base_dir: str = SOCIAL_UPLOAD_DIR) -> None:
        self.base_dir = Path(base_dir)
        self.accounts_dir = self.base_dir / "accounts"
        self.accounts_dir.mkdir(parents=True, exist_ok=True)

    def is_installed(self) -> bool:
        """Check if social-auto-upload is installed."""
        return self.base_dir.exists() and (self.base_dir / "social_auto_upload").exists()

    def is_logged_in(self, platform: str) -> bool:
        """Check if a platform has saved cookies."""
        cookie_file = self.accounts_dir / f"{platform}.json"
        return cookie_file.exists()

    def publish(
        self,
        video_path: str,
        title: str,
        platforms: list[str],
        tags: list[str] | None = None,
        description: str = "",
        schedule: str | None = None,
    ) -> dict[str, Any]:
        """Publish video to multiple platforms.

        Args:
            video_path: Path to the video file.
            title: Video title.
            platforms: List of platform names, e.g. ["douyin", "bilibili"].
            tags: List of hashtags, e.g. ["翡翠", "珠宝"].
            description: Video description.
            schedule: Optional schedule time (YYYY-MM-DD HH:MM).

        Returns:
            Dict with results per platform.
        """
        if not self.is_installed():
            raise RuntimeError(
                "social-auto-upload 未安装。"
                "请先运行 install_social_upload.bat"
            )

        if not Path(video_path).exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        results: dict[str, Any] = {}

        for platform in platforms:
            if not self.is_logged_in(platform):
                results[platform] = {
                    "success": False,
                    "error": f"未登录 {platform}，请先运行登录脚本保存 Cookie",
                }
                continue

            try:
                result = self._publish_to_platform(
                    platform=platform,
                    video_path=video_path,
                    title=title,
                    tags=tags or [],
                    description=description,
                    schedule=schedule,
                )
                results[platform] = {"success": True, "data": result}
            except Exception as exc:
                logger.exception("Publish to %s failed", platform)
                results[platform] = {"success": False, "error": str(exc)}

        return results

    def _publish_to_platform(
        self,
        platform: str,
        video_path: str,
        title: str,
        tags: list[str],
        description: str,
        schedule: str | None,
    ) -> dict[str, Any]:
        """Publish to a single platform using social-auto-upload."""
        # Build CLI command
        cmd = [
            sys.executable,
            "-m",
            "social_auto_upload.cli",
            "upload",
            "--platform", platform,
            "--file", video_path,
            "--title", title,
            "--account", str(self.accounts_dir / f"{platform}.json"),
        ]

        if tags:
            cmd.extend(["--tags", ",".join(tags)])
        if description:
            cmd.extend(["--desc", description])
        if schedule:
            cmd.extend(["--schedule", schedule])

        # Run in social-auto-upload directory
        result = subprocess.run(
            cmd,
            cwd=str(self.base_dir),
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Upload failed: {result.stderr}")

        return {"output": result.stdout, "platform": platform}

    def get_platforms(self) -> list[dict[str, Any]]:
        """Get list of supported platforms and their login status."""
        platforms = [
            {"key": "douyin", "name": "抖音", "available": True},
            {"key": "shipinhao", "name": "视频号", "available": True},
            {"key": "bilibili", "name": "B站", "available": True},
            {"key": "xiaohongshu", "name": "小红书", "available": True},
            {"key": "kuaishou", "name": "快手", "available": True},
            {"key": "tiktok", "name": "TikTok", "available": True},
        ]
        for p in platforms:
            p["logged_in"] = self.is_logged_in(p["key"])
        return platforms
