"""ASR API: upload video/audio or paste Douyin link -> transcribe to text."""

import logging
import os
import tempfile
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.generation_record import GenerationRecord
from app.models.user import User
from app.services import generation_record_service, storage_service
from app.services.gpu_worker_client import GPUWorkerClient
from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["asr"])


def success_response(data: object, message: str = "") -> dict[str, object]:
    return {"success": True, "data": data, "message": message}


def _extract_audio(video_path: str) -> str:
    """Extract audio from video using ffmpeg."""
    import subprocess

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        audio_path = tmp.name

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            audio_path,
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=180,
    )
    return audio_path


def _transcribe_file(media_path: str, language: str, settings: Any) -> dict[str, Any]:
    """Transcribe a media file with Whisper, returning result dict."""
    # Extract audio if video
    suffix = os.path.splitext(media_path)[1].lower()
    audio_path: str | None = None
    try:
        if suffix in (".mp4", ".mov", ".avi", ".mkv", ".webm"):
            audio_path = _extract_audio(media_path)
        else:
            audio_path = media_path

        client = GPUWorkerClient.from_settings(settings)
        return client.transcribe(audio_path, language=language)
    finally:
        if audio_path and audio_path != media_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except OSError:
                pass


# ─── Upload route ───────────────────────────────────────────

@router.post("/api/asr/transcribe", status_code=201)
def transcribe_upload(
    file: UploadFile = File(...),
    language: str = "zh",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """Upload a video/audio file and transcribe to text."""
    settings = get_settings()

    suffix = os.path.splitext(file.filename or "upload.mp4")[1] or ".mp4"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file.file.read())
        media_path = tmp.name

    try:
        result = _transcribe_file(media_path, language, settings)

        record = GenerationRecord(
            user_id=current_user.id,
            module_name="asr",
            input_data={"filename": file.filename, "language": language, "source": "upload"},
            output_data=result,
            model_provider="local",
            model_name="faster-whisper",
            latency_ms=0,
        )
        db.add(record)
        db.commit()

        return success_response(result, "转写完成")
    except Exception as exc:
        logger.exception("ASR upload failed")
        raise HTTPException(status_code=500, detail=f"转写失败: {exc}") from exc
    finally:
        if os.path.exists(media_path):
            try:
                os.remove(media_path)
            except OSError:
                pass


# ─── URL route: paste Douyin link → auto-download → transcribe ─

class AsrUrlRequest(BaseModel):
    url: str
    language: str = "zh"


@router.post("/api/asr/transcribe-url", status_code=201)
def transcribe_from_url(
    payload: AsrUrlRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """Paste a Douyin link, auto-download video and transcribe to text."""
    from app.services.douyin_api_client import DouyinAPIClient

    settings = get_settings()
    video_path: str | None = None

    try:
        # Step 1: Parse Douyin link
        douyin = DouyinAPIClient()
        info = douyin.parse_video(payload.url)
        if not info.get("video_url"):
            raise RuntimeError("未能获取视频下载链接")

        logger.info("Douyin parsed: title=%s author=%s", info["title"][:40], info["author"])

        # Step 2: Download video
        video_path = douyin.download_video(info["video_url"])
        logger.info("Video downloaded: %s", video_path)

        # Step 3: Transcribe
        result = _transcribe_file(video_path, payload.language, settings)

        # Save record
        record = GenerationRecord(
            user_id=current_user.id,
            module_name="asr",
            input_data={
                "url": payload.url,
                "language": payload.language,
                "title": info["title"],
                "author": info["author"],
                "source": "douyin_url",
            },
            output_data=result,
            model_provider="local",
            model_name="faster-whisper",
            latency_ms=0,
        )
        db.add(record)
        db.commit()

        return success_response(
            {
                **result,
                "meta": {
                    "title": info["title"],
                    "author": info["author"],
                    "cover_url": info.get("cover_url", ""),
                },
            },
            "链接解析+转写完成",
        )
    except Exception as exc:
        logger.exception("ASR from URL failed")
        raise HTTPException(status_code=500, detail=f"链接转写失败: {exc}") from exc
    finally:
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except OSError:
                pass
