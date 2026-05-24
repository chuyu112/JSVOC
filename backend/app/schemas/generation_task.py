from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


GenerationTaskStatus = Literal["queued", "running", "succeeded", "failed"]


class GenerationTaskCreate(BaseModel):
    task_type: str = Field(min_length=1, max_length=80)
    project_id: int | None = Field(default=None, ge=1)
    input_data: dict[str, Any] = Field(default_factory=dict)


class GenerationTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_type: str
    status: GenerationTaskStatus
    user_id: int | None
    project_id: int | None
    input_data: dict[str, Any]
    result_data: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    credit_cost: int | None = None
    credit_transaction_id: int | None = None


class GenerationTaskSubmitResponse(BaseModel):
    task_id: int
    task_type: str
    status: GenerationTaskStatus
    credit_cost: int | None = None
