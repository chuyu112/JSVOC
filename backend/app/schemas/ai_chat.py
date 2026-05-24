from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class AIChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("content cannot be blank")
        return cleaned


class AIChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[AIChatMessage] = Field(default_factory=list, max_length=20)
    web_search: bool = False
    conversation_id: str | None = Field(default=None, max_length=80)
    conversation_title: str | None = Field(default=None, max_length=4000)

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("message cannot be blank")
        return cleaned


class AIChatResponse(BaseModel):
    reply: str
    provider: str
    model: str
    usage: dict[str, Any]
    sources: list[dict[str, Any]] = Field(default_factory=list)
    latency_ms: int
    generation_record_id: int | None = None
    conversation_id: str
    conversation_title: str


class AIChatHistoryTurn(BaseModel):
    generation_record_id: int
    conversation_id: str
    conversation_title: str
    user_message: str
    assistant_message: str
    provider: str
    model: str
    web_search: bool = False
    latency_ms: int | None = None
    created_at: datetime


class AIChatConversationSummary(BaseModel):
    conversation_id: str
    title: str
    last_user_message: str
    last_assistant_message: str
    turn_count: int
    created_at: datetime
    updated_at: datetime
