from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_admin_user
from app.db.session import get_db
from app.llm.llm_gateway import LLMGateway, LLMGatewayRequest
from app.models.user import User
from app.schemas.llm_channel import LLMChannelCreate, LLMChannelTestResult, LLMChannelUpdate
from app.services import llm_channel_service


router = APIRouter(prefix="/api/admin/llm-channels", tags=["admin-llm-channels"])


def success_response(data: object, message: str = "") -> dict[str, object]:
    return {"success": True, "data": data, "message": message}


@router.get("")
def list_llm_channels(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
) -> dict[str, object]:
    del admin_user
    channels = llm_channel_service.list_channels(db)
    return success_response([llm_channel_service.serialize_channel(item).model_dump(mode="json") for item in channels])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_llm_channel(
    payload: LLMChannelCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
) -> dict[str, object]:
    del admin_user
    channel = llm_channel_service.create_channel(db, payload)
    return success_response(llm_channel_service.serialize_channel(channel).model_dump(mode="json"), "channel created")


@router.patch("/{channel_id}")
def update_llm_channel(
    channel_id: int,
    payload: LLMChannelUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
) -> dict[str, object]:
    del admin_user
    channel = llm_channel_service.get_channel_or_404(db, channel_id)
    updated = llm_channel_service.update_channel(db, channel, payload)
    return success_response(llm_channel_service.serialize_channel(updated).model_dump(mode="json"), "channel updated")


@router.post("/{channel_id}/activate")
def activate_llm_channel(
    channel_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
) -> dict[str, object]:
    del admin_user
    channel = llm_channel_service.get_channel_or_404(db, channel_id)
    active = llm_channel_service.activate_channel(db, channel)
    return success_response(llm_channel_service.serialize_channel(active).model_dump(mode="json"), "channel activated")


@router.delete("/{channel_id}")
def delete_llm_channel(
    channel_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
) -> dict[str, object]:
    del admin_user
    channel = llm_channel_service.get_channel_or_404(db, channel_id)
    llm_channel_service.delete_channel(db, channel)
    return success_response({"id": channel_id}, "channel deleted")


@router.post("/{channel_id}/test")
def test_llm_channel(
    channel_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
) -> dict[str, object]:
    channel = llm_channel_service.get_channel_or_404(db, channel_id)
    settings = llm_channel_service.settings_for_channel(channel)
    gateway = LLMGateway(settings=settings)
    result = gateway.generate(
        db=db,
        user_id=admin_user.id,
        prompt_version="admin-channel-test",
        request=LLMGatewayRequest(
            module_name="admin_channel_test",
            system_prompt="You are a concise API health check responder.",
            user_prompt='Return JSON exactly like {"ok": true}.',
            temperature=0,
            max_tokens=64,
        ),
    )
    message = "channel test succeeded" if result.success else result.error or "channel test failed"
    data = LLMChannelTestResult(
        success=result.success,
        provider=result.provider,
        model=result.model,
        message=message,
        latency_ms=result.latency_ms,
        error=result.error,
    )
    return success_response(data.model_dump(mode="json"), message)
