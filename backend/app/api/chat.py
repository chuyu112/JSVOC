from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.llm.llm_gateway import LLMGateway, LLMGatewayRequest


router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class ChatGenerateRequest(BaseModel):
    project_id: int | None = None
    messages: list[ChatMessage] = Field(min_length=1)
    temperature: float = Field(default=0.7, ge=0, le=2)


@router.post("")
def chat(
    payload: ChatGenerateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    result = LLMGateway().generate(
        db=db,
        project_id=payload.project_id,
        prompt_version="chat-v1",
        request=LLMGatewayRequest(
            module_name="chat",
            messages=[message.model_dump() for message in payload.messages],
            temperature=payload.temperature,
            metadata={"project_id": payload.project_id},
        ),
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result.error or "聊天调用失败",
        )

    return {
        "success": True,
        "data": {
            "content": result.content,
            "data": result.data,
            "generation_record_id": result.generation_record_id,
            "provider": result.provider,
            "model": result.model,
            "usage": result.usage,
            "latency_ms": result.latency_ms,
        },
        "message": "",
    }
