"""Social publish API for multi-platform video distribution."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.social_publish_service import SocialPublishService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["social-publish"])


def success_response(data: object, message: str = "") -> dict[str, object]:
    return {"success": True, "data": data, "message": message}


def failure_response(data: object, message: str) -> dict[str, object]:
    return {"success": False, "data": data, "message": message}


@router.get("/api/social-publish/platforms")
def list_platforms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """List supported social platforms and their login status."""
    service = SocialPublishService()
    platforms = service.get_platforms()
    return success_response(platforms)


@router.post("/api/social-publish/publish", status_code=201)
def publish_video(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """Publish a video to multiple social platforms.

    Body:
        {
            "video_url": "https://.../video.mp4",
            "title": "视频标题",
            "platforms": ["douyin", "bilibili", "xiaohongshu"],
            "tags": ["翡翠", "珠宝"],
            "description": "视频描述"
        }
    """
    video_url = payload.get("video_url", "")
    title = payload.get("title", "")
    platforms = payload.get("platforms", [])
    tags = payload.get("tags", [])
    description = payload.get("description", "")

    if not video_url or not platforms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="video_url and platforms are required",
        )

    service = SocialPublishService()
    try:
        results = service.publish(
            video_path=video_url,  # Note: may need to download first if it's a URL
            title=title,
            platforms=platforms,
            tags=tags,
            description=description,
        )
        return success_response(results, "分发任务已提交")
    except Exception as exc:
        logger.exception("Social publish failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分发失败: {exc}",
        ) from exc
