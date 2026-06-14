"""CozyVoice local service client for TTS and voice cloning."""

import logging
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

DEFAULT_COZYVOICE_URL = "http://127.0.0.1:50000"


class CozyVoiceClient:
    """Client for local CozyVoice service.

    CozyVoice must be running locally, e.g.:
        python api.py --port 50000

    GitHub: https://github.com/FunAudioLLM/CosyVoice
    """

    def __init__(self, base_url: str | None = None) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.cozy_voice_url or DEFAULT_COZYVOICE_URL).rstrip("/")
        self.client = httpx.Client(timeout=300.0)

    def _post(self, path: str, data: dict[str, Any] | None = None, files: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            resp = self.client.post(url, data=data, files=files)
            resp.raise_for_status()
            return {"success": True, "content": resp.content, "headers": dict(resp.headers)}
        except httpx.ConnectError as exc:
            logger.error("CozyVoice connection failed: %s", exc)
            raise RuntimeError(
                f"CozyVoice 服务未启动，请确认本地服务运行在 {self.base_url}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            logger.error("CozyVoice error: %s - %s", exc.response.status_code, exc.response.text[:200])
            raise RuntimeError(f"CozyVoice 返回错误: {exc.response.status_code}") from exc

    def clone_voice(
        self,
        text: str,
        prompt_audio_path: str,
        prompt_text: str | None = None,
    ) -> bytes:
        """Zero-shot voice cloning with a 3-second sample.

        GitHub: https://github.com/FunAudioLLM/CosyVoice
        Endpoint: POST /inference_zero_shot
        Params: tts_text, prompt_text, prompt_wav (file)

        Args:
            text: Text to synthesize (tts_text).
            prompt_audio_path: Path to the 3-second reference audio (prompt_wav).
            prompt_text: Transcript of the reference audio (optional but recommended).

        Returns:
            WAV audio bytes.
        """
        path = Path(prompt_audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Prompt audio not found: {prompt_audio_path}")

        files = {
            "prompt_wav": (path.name, path.read_bytes(), "audio/wav"),
        }
        data: dict[str, Any] = {"tts_text": text}
        if prompt_text:
            data["prompt_text"] = prompt_text

        result = self._post("/inference_zero_shot", data=data, files=files)
        return result["content"]

    def tts_with_preset(
        self,
        text: str,
        voice_id: str = "default",
    ) -> bytes:
        """TTS using a preset voice.

        GitHub: https://github.com/FunAudioLLM/CosyVoice
        Endpoint: POST /inference_sft
        Params: tts_text, spk_id

        Args:
            text: Text to synthesize (tts_text).
            voice_id: Preset speaker id (spk_id).

        Returns:
            WAV audio bytes.
        """
        data = {"tts_text": text, "spk_id": voice_id}
        result = self._post("/inference_sft", data=data)
        return result["content"]

    def health_check(self) -> bool:
        """Check if CozyVoice service is reachable."""
        try:
            resp = self.client.get(f"{self.base_url}/health", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False
