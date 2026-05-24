from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AccountPackageGenerateRequest(BaseModel):
    project_id: int = Field(gt=0)
    temperature: float = Field(default=0.7, ge=0, le=2)


class AccountPackageResult(BaseModel):
    account_positioning: str
    persona: str
    target_user_profile: dict[str, Any]
    account_names: list[str]
    bios: dict[str, str]
    content_columns: list[Any]
    trust_design: list[str]
    conversion_path: list[str]
    platform_strategies: dict[str, Any]
    rubric_notes: dict[str, Any] = Field(default_factory=dict)


class AccountStrategyContextCreate(AccountPackageResult):
    project_id: int
    generation_record_id: int | None = None
    content_style: str | None = None
    trust_points: list[str] = Field(default_factory=list)
    monetization_paths: list[str] = Field(default_factory=list)
    execution_stage: str | None = None
    context_data: dict[str, Any] = Field(default_factory=dict)


class AccountStrategyContextRead(AccountStrategyContextCreate):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
