from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TopicGenerateRequest(BaseModel):
    project_id: int = Field(gt=0)
    platform: str = Field(default="抖音", min_length=1, max_length=40)
    goal: str = Field(default="获客", min_length=1, max_length=80)
    count: int = Field(default=20, ge=1, le=100)
    temperature: float = Field(default=0.7, ge=0, le=2)


class TopicCreate(BaseModel):
    project_id: int
    title: str
    content_type: str
    platform: str
    goal: str
    selling_point: str | None = None
    score: int = Field(default=0, ge=0, le=100)
    topic_data: dict[str, Any] = Field(default_factory=dict)


class TopicRead(TopicCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TopicGenerateResponse(BaseModel):
    topics: list[TopicRead]
    generation_record_id: int | None
    provider: str
    model: str
    usage: dict[str, Any]
    latency_ms: int
