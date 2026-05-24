from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.hot_video import HotVideoSearchRequest
from app.services import hot_video_service


router = APIRouter(tags=["hot_videos"])


def success_response(data: object, message: str = "") -> dict[str, object]:
    return {"success": True, "data": data, "message": message}


@router.post("/api/creation/hot-videos/search")
def search_hot_videos_api(
    payload: HotVideoSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    try:
        response = hot_video_service.search_hot_videos(
            db,
            payload=payload,
            user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc) or "热门视频搜索失败",
        ) from exc

    return success_response(response.model_dump(mode="json"), "热门视频搜索完成")
