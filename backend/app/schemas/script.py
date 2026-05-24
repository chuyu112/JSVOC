from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScriptGenerateRequest(BaseModel):
    project_id: int = Field(gt=0)
    topic_id: int = Field(gt=0)
    platform: str | None = Field(default=None, max_length=40)
    script_type: str = Field(default="聊观点", min_length=1, max_length=80)
    duration: str = Field(default="60秒", min_length=1, max_length=40)
    goal: str = Field(default="私信获客", min_length=1, max_length=80)
    temperature: float = Field(default=0.7, ge=0, le=2)


class ScriptCreate(BaseModel):
    project_id: int
    topic_id: int
    title: str
    script_type: str
    platform: str
    script_content: str
    shot_suggestions: list[str] = Field(default_factory=list)
    conversion_script: str
    script_data: dict[str, Any] = Field(default_factory=dict)


class ScriptRead(ScriptCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScriptGenerateResponse(BaseModel):
    script: ScriptRead
    generation_record_id: int | None
    provider: str
    model: str
    usage: dict[str, Any]
    latency_ms: int
