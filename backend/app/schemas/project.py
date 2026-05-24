from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    project_name: str = Field(min_length=1, max_length=120)
    industry: str = Field(min_length=1, max_length=80)
    sub_industry: str | None = Field(default=None, max_length=120)
    product: str = Field(min_length=1, max_length=200)
    personal_intro: str = Field(min_length=1)
    target_audience: str = Field(min_length=1)
    platforms: list[str] = Field(default_factory=list)
    benchmark_accounts: list[dict[str, str]] = Field(default_factory=list)
    benchmark_samples: list[dict[str, Any]] = Field(default_factory=list)
    current_stage: str = Field(min_length=1, max_length=80)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    project_name: str | None = Field(default=None, min_length=1, max_length=120)
    industry: str | None = Field(default=None, min_length=1, max_length=80)
    sub_industry: str | None = Field(default=None, max_length=120)
    product: str | None = Field(default=None, min_length=1, max_length=200)
    personal_intro: str | None = Field(default=None, min_length=1)
    target_audience: str | None = Field(default=None, min_length=1)
    platforms: list[str] | None = None
    benchmark_accounts: list[dict[str, str]] | None = None
    benchmark_samples: list[dict[str, Any]] | None = None
    current_stage: str | None = Field(default=None, min_length=1, max_length=80)


class ProjectRead(ProjectBase):
    id: int
    user_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
