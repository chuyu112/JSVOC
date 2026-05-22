from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GenerationRecordCreate(BaseModel):
    user_id: int | None = None
    project_id: int | None = None
    module_name: str = Field(min_length=1, max_length=80)
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    model_provider: str = Field(min_length=1, max_length=80)
    model_name: str = Field(min_length=1, max_length=120)
    prompt_version: str | None = Field(default=None, max_length=40)
    token_usage: dict[str, Any] = Field(default_factory=dict)
    latency_ms: int | None = Field(default=None, ge=0)


class GenerationRecordRead(GenerationRecordCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
