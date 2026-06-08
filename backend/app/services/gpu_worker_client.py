from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings


class GPUWorkerClient:
    def __init__(self, asr_api_url: str, api_key: str = "") -> None:
        self.asr_api_url = asr_api_url.strip()
        self.api_key = api_key.strip()

    @classmethod
    def from_settings(cls, settings: Settings) -> "GPUWorkerClient":
        return cls(
            asr_api_url=settings.asr_api_url,
            api_key=settings.asr_api_key,
        )

    def transcribe(self, file_path: str, *, language: str = "zh") -> dict[str, Any]:
        if not self.asr_api_url:
            raise RuntimeError("ASR_API_URL is required for video transcription")

        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        path = Path(file_path)
        with path.open("rb") as file_obj:
            response = httpx.post(
                self.asr_api_url,
                headers=headers,
                data={"language": language},
                files={"file": (path.name, file_obj, "application/octet-stream")},
                timeout=300.0,
            )
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise RuntimeError("ASR service returned an invalid response")
        return body
