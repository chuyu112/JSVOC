"""HeyGem local service client for digital human video generation.

HeyGem must be running locally via Docker, e.g.:
    docker-compose up -d

GitHub: https://github.com/GuijiAI/HeyGem.ai
API Docs: http://localhost:<port>/docs (Swagger UI)

Typical endpoints (check /docs after starting):
    POST /api/v1/videos  - Generate video (multipart: audio + video/face_image)
    POST /api/v1/generate - Alternative endpoint
    GET  /api/v1/tasks/{id} - Check task status
"""

import logging
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_HEYGEM_URL = "http://127.0.0.1:3000"


class HeyGemClient:
    """Client for local HeyGem service."""

    def __init__(self, base_url: str | None = None) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.hey_gem_url or DEFAULT_HEYGEM_URL).rstrip("/")
        self.client = httpx.Client(timeout=600.0)

    def _post(
        self, path: str, data: dict[str, Any] | None = None, files: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            resp = self.client.post(url, data=data, files=files)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "application/json" in content_type:
                return {"success": True, "json": resp.json()}
            return {"success": True, "content": resp.content, "headers": dict(resp.headers)}
        except httpx.ConnectError as exc:
            logger.error("HeyGem connection failed: %s", exc)
            raise RuntimeError(
                f"HeyGem 服务未启动，请确认本地服务运行在 {self.base_url}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            logger.error("HeyGem error: %s - %s", exc.response.status_code, exc.response.text[:200])
            raise RuntimeError(f"HeyGem 返回错误: {exc.response.status_code}") from exc

    def generate_video(
        self,
        avatar_video_path: str,
        audio_path: str,
    ) -> bytes:
        """Generate digital human video driven by audio.

        Tries common endpoint patterns:
            /api/v1/videos, /api/v1/generate, /generate

        Args:
            avatar_video_path: Path to the avatar reference video (driving video).
            audio_path: Path to the driving audio (from CozyVoice TTS).

        Returns:
            MP4 video bytes.
        """
        avatar_path = Path(avatar_video_path)
        audio_file = Path(audio_path)

        if not avatar_path.exists():
            raise FileNotFoundError(f"Avatar video not found: {avatar_video_path}")
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio not found: {audio_path}")

        files = {
            "video": (avatar_path.name, avatar_path.read_bytes(), "video/mp4"),
            "audio": (audio_file.name, audio_file.read_bytes(), "audio/wav"),
        }

        # Try common endpoint patterns
        for endpoint in ["/api/v1/videos", "/api/v1/generate", "/generate"]:
            try:
                result = self._post(endpoint, files=files)
                if result.get("content"):
                    return result["content"]
                # Some versions return JSON with download URL
                json_data = result.get("json", {})
                if "video_url" in json_data or "download_url" in json_data:
                    video_url = json_data.get("video_url") or json_data.get("download_url")
                    resp = self.client.get(video_url, timeout=300.0)
                    resp.raise_for_status()
                    return resp.content
            except Exception:
                continue

        raise RuntimeError("HeyGem 所有生成端点均失败，请检查服务日志")

    def health_check(self) -> bool:
        """Check if HeyGem service is reachable."""
        for path in ["/health", "/docs", "/"]:
            try:
                resp = self.client.get(f"{self.base_url}{path}", timeout=5.0)
                if resp.status_code == 200:
                    return True
            except Exception:
                continue
        return False
