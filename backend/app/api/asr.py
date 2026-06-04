"""ASR API: upload video/audio -> transcribe to text."""

import logging
import os
import tempfile
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
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


@router.post("/api/asr/transcribe", status_code=201)
def transcribe_video(
    file: UploadFile = File(...),
    language: str = "zh",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """Upload a video/audio file and transcribe to text.

    Returns:
        {
            "text": "完整文案",
            "segments": [{"start": 0.0, "end": 3.5, "text": "..."}],
            "duration": 45.6,
            "language": "zh"
        }
    """
    settings = get_settings()

    # Save uploaded file
    suffix = os.path.splitext(file.filename or "upload.mp4")[1] or ".mp4"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file.file.read())
        media_path = tmp.name

    audio_path: str | None = None
    try:
        # Extract audio if video
        if suffix.lower() in (".mp4", ".mov", ".avi", ".mkv", ".webm"):
            logger.info("Extracting audio from video: %s", media_path)
            audio_path = _extract_audio(media_path)
        else:
            audio_path = media_path

        # Transcribe with Whisper
        logger.info("Transcribing audio: %s", audio_path)
        client = GPUWorkerClient.from_settings(settings)
        result = client.transcribe(audio_path, language=language)

        # Save generation record
        record = GenerationRecord(
            user_id=current_user.id,
            module_name="asr",
            input_data={"filename": file.filename, "language": language},
            output_data=result,
            model_provider="local",
            model_name="faster-whisper",
            latency_ms=0,
        )
        db.add(record)
        db.commit()

        return success_response(result, "转写完成")

    except Exception as exc:
        logger.exception("ASR failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"转写失败: {exc}",
        ) from exc
    finally:
        for path in (media_path, audio_path):
            if path and path != media_path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
