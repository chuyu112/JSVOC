"""Digital human video generation orchestration service."""

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.digital_human_video import DigitalHumanVideo
from app.models.generation_task import GenerationTask
from app.schemas.digital_human import DigitalHumanVideoCreate

logger = logging.getLogger(__name__)

# Cost in credits per video
VIDEO_GENERATION_COST = 35


def create_generation_task(
    db: Session,
    user_id: int,
    payload: DigitalHumanVideoCreate,
    script: Any,
) -> dict[str, Any]:
    """Create a digital human video generation task and enqueue it."""
    settings = get_settings()

    # 1. Create the video record
    video = DigitalHumanVideo(
        user_id=user_id,
        project_id=payload.project_id,
        script_id=payload.script_id,
        voice_id=payload.voice_id,
        avatar_id=payload.avatar_id,
        title=script.title or "未命名数字人视频",
        status="queued",
        config_json={
            "with_subtitle": payload.with_subtitle,
            "with_bgm": payload.with_bgm,
            "resolution": payload.resolution,
            "script_content": script.script_content,
        },
        credit_cost=VIDEO_GENERATION_COST,
    )
    db.add(video)
    db.flush()

    # 2. Create generation task for async processing
    task = GenerationTask(
        task_type="digital_human_video",
        status="queued",
        user_id=user_id,
        project_id=payload.project_id,
        input_data={
            "video_id": video.id,
            "script_id": payload.script_id,
            "voice_id": payload.voice_id,
            "avatar_id": payload.avatar_id,
            "config": video.config_json,
        },
        credit_cost=VIDEO_GENERATION_COST,
    )
    db.add(task)
    db.flush()

    # Link task to video
    video.task_id = task.id
    db.commit()
    db.refresh(video)

    return {
        "task_id": task.id,
        "video_id": video.id,
        "status": "queued",
        "message": "数字人视频生成任务已加入队列",
    }
