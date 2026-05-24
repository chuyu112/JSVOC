from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TopicGenerateRequest(BaseModel):
    project_id: int = Field(gt=0)
    platform: str = Field(default="抖音", min_length=1, max_length=40)
    goal: str = Field(default="获客", min_length=1, max_length=80)
    content_format: str = Field(default="video", min_length=1, max_length=40)
    count: int = Field(default=10, ge=1, le=10)
    temperature: float = Field(default=0.7, ge=0, le=2)
    existing_titles: list[str] = Field(default_factory=list, max_length=1000)
    topic_index: int | None = Field(default=None, ge=1, le=100)
    generation_batch_id: str | None = Field(default=None, min_length=1, max_length=80)
    generation_target_count: int | None = Field(default=None, ge=1, le=100)
    persona_reference_image_uploaded: bool = False


class TopicCreate(BaseModel):
    project_id: int
    title: str
    content_type: str
    platform: str
    goal: str
    selling_point: str | None = None
    score: int = Field(default=0, ge=0, le=100)
    is_favorite: bool = False
    topic_data: dict[str, Any] = Field(default_factory=dict)


class TopicRead(TopicCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TopicFavoriteUpdate(BaseModel):
    is_favorite: bool


class TopicGenerateResponse(BaseModel):
    topics: list[TopicRead]
    generation_record_id: int | None
    provider: str
    model: str
    usage: dict[str, Any]
    latency_ms: int


class TopicBatchGenerateRequest(BaseModel):
    project_id: int = Field(gt=0)
    platform: str = Field(default="抖音", min_length=1, max_length=40)
    goal: str = Field(default="获客", min_length=1, max_length=80)
    content_format: str = Field(default="video", min_length=1, max_length=40)
    target_count: int = Field(default=15, ge=1, le=30)
    temperature: float = Field(default=0.7, ge=0, le=2)
    persona_reference_image_uploaded: bool = False


class TopicBatchGenerateResponse(BaseModel):
    topics: list[TopicRead]
    generated_count: int
    target_count: int
    provider: str
    model: str
    latency_ms: int
