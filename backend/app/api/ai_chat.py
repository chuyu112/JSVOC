from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai_chat import AIChatRequest
from app.services import ai_chat_service


router = APIRouter(tags=["ai_chat"])


def success_response(data: object, message: str = "") -> dict[str, object]:
    return {"success": True, "data": data, "message": message}


@router.post("/api/ai-chat")
def create_ai_chat_reply(
    payload: AIChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    try:
        response = ai_chat_service.generate_ai_chat_reply(
            db,
            payload=payload,
            user_id=current_user.id,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc) or "AI聊天失败",
        ) from exc

    return success_response(response.model_dump(mode="json"), "AI聊天完成")


@router.get("/api/ai-chat/history")
def list_ai_chat_history(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    turns = ai_chat_service.list_ai_chat_history(
        db,
        user_id=current_user.id,
        limit=limit,
    )
    return success_response([turn.model_dump(mode="json") for turn in turns])


@router.get("/api/ai-chat/conversations")
def list_ai_chat_conversations(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    conversations = ai_chat_service.list_ai_chat_conversations(
        db,
        user_id=current_user.id,
        limit=limit,
    )
    return success_response([item.model_dump(mode="json") for item in conversations])


@router.get("/api/ai-chat/conversations/{conversation_id}/history")
def list_ai_chat_conversation_history(
    conversation_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    turns = ai_chat_service.list_ai_chat_history(
        db,
        user_id=current_user.id,
        limit=limit,
        conversation_id=conversation_id,
    )
    return success_response([turn.model_dump(mode="json") for turn in turns])
