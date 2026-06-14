"""Async worker for digital human video generation.

Runs the full pipeline:
    CozyVoice TTS → HeyGem digital human → FFmpeg compose → OSS upload
"""

import logging
import os
import tempfile
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.digital_human_video import DigitalHumanVideo
from app.models.script import Script
from app.services import (
    credit_service,
    generation_record_service,
    generation_task_service,
    storage_service,
)
from app.services.cozy_voice_service import CozyVoiceClient
from app.services.hey_gem_service import HeyGemClient
from app.services.video_compose_service import VideoComposeService

logger = logging.getLogger(__name__)

# Temp dir for intermediate files
_TEMP_DIR = tempfile.gettempdir()


def _temp_path(prefix: str, suffix: str) -> str:
    import uuid as _uuid
    return os.path.join(_TEMP_DIR, f"{prefix}_{_uuid.uuid4().hex[:8]}{suffix}")


def run_digital_human_video_task(
    task_id: int,
    video_id: int,
    script_content: str,
    voice_id: int,
    avatar_id: int,
    config: dict[str, Any],
    user_id: int,
    project_id: int | None,
) -> None:
    """Background task: generate digital human video end-to-end."""
    db = SessionLocal()
    settings = get_settings()

    try:
        generation_task_service.mark_generation_task_running(db, task_id)

        # Update video status
        video = db.get(DigitalHumanVideo, video_id)
        if video:
            video.status = "running"
            db.commit()

        # ── Step 1: CozyVoice TTS ──────────────────────────────
        logger.info("[DH Task %s] Step 1: CozyVoice TTS", task_id)
        cozy = CozyVoiceClient()

        # TODO: get voice sample path from voice_id
        # For now, use preset TTS
        audio_bytes = cozy.tts_with_preset(script_content)
        audio_path = _temp_path("dh_audio", ".wav")
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)
        logger.info("[DH Task %s] TTS done: %s", task_id, audio_path)

        # ── Step 2: HeyGem digital human ───────────────────────
        logger.info("[DH Task %s] Step 2: HeyGem digital human", task_id)
        heygem = HeyGemClient()

        # TODO: get avatar video path from avatar_id
        # For now, placeholder
        avatar_video_path = _temp_path("dh_avatar", ".mp4")
        # In real scenario, this would be the avatar's reference video
        # If avatar doesn't have a local video, we need to handle that

        # Generate raw digital human video
        raw_video_bytes = heygem.generate_video(avatar_video_path, audio_path)
        raw_video_path = _temp_path("dh_raw", ".mp4")
        with open(raw_video_path, "wb") as f:
            f.write(raw_video_bytes)
        logger.info("[DH Task %s] HeyGem done: %s", task_id, raw_video_path)

        # ── Step 3: FFmpeg compose ─────────────────────────────
        logger.info("[DH Task %s] Step 3: FFmpeg compose", task_id)
        composer = VideoComposeService()
        final_video_path = _temp_path("dh_final", ".mp4")

        final_path = composer.compose(
            video_path=raw_video_path,
            subtitle_text=script_content if config.get("with_subtitle") else "",
            output_path=final_video_path,
            bgm_path=None,  # TODO: support BGM
            resolution=config.get("resolution", "1080p"),
        )
        logger.info("[DH Task %s] Compose done: %s", task_id, final_path)

        # ── Step 4: Upload to OSS ──────────────────────────────
        logger.info("[DH Task %s] Step 4: Upload to OSS", task_id)
        with open(final_path, "rb") as f:
            video_bytes = f.read()

        object_key = storage_service.upload_bytes(
            object_key=storage_service.build_reference_media_object_key(
                user_id=user_id,
                project_id=project_id,
                media_kind="videos",
                mime_type="video/mp4",
            ),
            content=video_bytes,
            content_type="video/mp4",
            settings=settings,
        )
        signed_url, expires_at = storage_service.sign_get_url(object_key, settings=settings)
        logger.info("[DH Task %s] Upload done: %s", task_id, object_key)

        # ── Step 5: Update records ─────────────────────────────
        result_data = {
            "video_url": signed_url,
            "oss_object_key": object_key,
            "oss_url_expires_at": expires_at,
        }

        if video:
            video.status = "success"
            video.video_url = signed_url
            db.commit()

        task = generation_task_service.mark_generation_task_succeeded(db, task_id, result_data)
        if task is not None:
            _maybe_create_generation_record(db, task)

        logger.info("[DH Task %s] Completed successfully", task_id)

    except Exception as exc:
        db.rollback()
        logger.exception("[DH Task %s] Failed", task_id)
        error_msg = str(exc)[:2000]

        if video := db.get(DigitalHumanVideo, video_id):
            video.status = "failed"
            video.error_message = error_msg
            db.commit()

        try:
            generation_task_service.mark_generation_task_failed(db, task_id, error_msg)
        except Exception:
            pass

        # Refund credits if charged
        try:
            task = db.get(GenerationTask, task_id)
            if task and task.credit_transaction_id:
                credit_service.refund_generation_task_credits(db, task_id)
        except Exception:
            logger.exception("Credit refund failed for task %s", task_id)

    finally:
        db.close()
        # Cleanup temp files
        for path in [audio_path, raw_video_path, final_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass


def _maybe_create_generation_record(db: Session, task: Any) -> None:
    try:
        generation_record_service.create_generation_record_from_task(db, task)
    except Exception:
        db.rollback()
        logger.exception("History persistence failed for digital human task %s", getattr(task, "id", None))
