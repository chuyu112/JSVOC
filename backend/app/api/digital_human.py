import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.digital_human_avatar import DigitalHumanAvatar
from app.models.digital_human_video import DigitalHumanVideo
from app.models.digital_human_voice import DigitalHumanVoice
from app.models.script import Script
from app.models.user import User
from app.schemas.digital_human import (
    DigitalHumanAvatarRead,
    DigitalHumanVideoCreate,
    DigitalHumanVideoRead,
    DigitalHumanVideoGenerateResponse,
    DigitalHumanVoiceRead,
)
from app.services import digital_human_service, storage_service
from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["digital-human"])


def success_response(data: object, message: str = "") -> dict[str, object]:
    return {"success": True, "data": data, "message": message}


def failure_response(data: object, message: str) -> dict[str, object]:
    return {"success": False, "data": data, "message": message}


# ─── Avatars ───────────────────────────────────────────────

@router.get("/api/digital-human/avatars")
def list_avatars(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """List preset digital human avatars."""
    stmt = (
        select(DigitalHumanAvatar)
        .where(DigitalHumanAvatar.is_active == True)
        .order_by(DigitalHumanAvatar.id)
    )
    avatars = db.execute(stmt).scalars().all()
    data = [DigitalHumanAvatarRead.model_validate(a).model_dump(mode="json") for a in avatars]
    return success_response(data)


# ─── Voices ────────────────────────────────────────────────

@router.get("/api/digital-human/voices")
def list_voices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """List preset voices + user's cloned voices."""
    stmt = (
        select(DigitalHumanVoice)
        .where(
            (DigitalHumanVoice.is_active == True)
            & (
                (DigitalHumanVoice.voice_type == "preset")
                | (DigitalHumanVoice.user_id == current_user.id)
            )
        )
        .order_by(DigitalHumanVoice.id)
    )
    voices = db.execute(stmt).scalars().all()
    data = [DigitalHumanVoiceRead.model_validate(v).model_dump(mode="json") for v in voices]
    return success_response(data)


@router.post("/api/digital-human/voices/clone", status_code=201)
def clone_voice(
    name: str,
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """Upload a 3-second audio sample to clone a voice."""
    settings = get_settings()
    try:
        file_content = audio.file.read()
        object_key = storage_service.upload_bytes(
            object_key=storage_service.build_reference_media_object_key(
                user_id=current_user.id,
                media_kind="audios",
                mime_type=audio.content_type or "audio/wav",
            ),
            content=file_content,
            content_type=audio.content_type or "audio/wav",
            settings=settings,
        )
        signed_url, _ = storage_service.sign_get_url(object_key, settings=settings)

        voice = DigitalHumanVoice(
            user_id=current_user.id,
            name=name,
            voice_type="cloned",
            sample_url=signed_url,
            config_json={"oss_object_key": object_key},
        )
        db.add(voice)
        db.commit()
        db.refresh(voice)

        data = DigitalHumanVoiceRead.model_validate(voice).model_dump(mode="json")
        return success_response(data, "声音克隆样本已保存")
    except Exception as exc:
        logger.exception("Voice clone failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"声音克隆失败: {exc}",
        ) from exc


# ─── Videos ────────────────────────────────────────────────

@router.get("/api/digital-human/videos")
def list_videos(
    project_id: int | None = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """List generated digital human videos."""
    stmt = select(DigitalHumanVideo).where(DigitalHumanVideo.user_id == current_user.id)
    if project_id is not None:
        stmt = stmt.where(DigitalHumanVideo.project_id == project_id)
    stmt = stmt.order_by(desc(DigitalHumanVideo.created_at)).limit(limit).offset(offset)
    videos = db.execute(stmt).scalars().all()
    data = [DigitalHumanVideoRead.model_validate(v).model_dump(mode="json") for v in videos]
    return success_response(data)


@router.get("/api/digital-human/videos/{video_id}")
def get_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """Get a single digital human video."""
    video = db.get(DigitalHumanVideo, video_id)
    if not video or video.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="视频不存在")
    data = DigitalHumanVideoRead.model_validate(video).model_dump(mode="json")
    return success_response(data)


@router.post("/api/digital-human/videos/generate", status_code=201)
def generate_video(
    payload: DigitalHumanVideoCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """Submit a digital human video generation task."""
    # Validate script exists and belongs to user
    script = db.get(Script, payload.script_id)
    if not script:
        raise HTTPException(status_code=404, detail="文案不存在")

    # Validate avatar exists
    avatar = db.get(DigitalHumanAvatar, payload.avatar_id)
    if not avatar:
        raise HTTPException(status_code=404, detail="数字人形象不存在")

    # Validate voice exists
    voice = db.get(DigitalHumanVoice, payload.voice_id)
    if not voice:
        raise HTTPException(status_code=404, detail="声音不存在")

    try:
        result = digital_human_service.create_generation_task(
            db=db,
            user_id=current_user.id,
            payload=payload,
            script=script,
        )

        # Trigger async worker
        from app.services.digital_human_worker import run_digital_human_video_task
        background_tasks.add_task(
            run_digital_human_video_task,
            task_id=result["task_id"],
            video_id=result["video_id"],
            script_content=script.script_content,
            voice_id=payload.voice_id,
            avatar_id=payload.avatar_id,
            config={
                "with_subtitle": payload.with_subtitle,
                "with_bgm": payload.with_bgm,
                "resolution": payload.resolution,
            },
            user_id=current_user.id,
            project_id=payload.project_id,
        )

        return success_response(
            DigitalHumanVideoGenerateResponse(**result).model_dump(mode="json"),
            "数字人视频生成任务已提交",
        )
    except Exception as exc:
        logger.exception("Digital human video generation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成任务提交失败: {exc}",
        ) from exc
