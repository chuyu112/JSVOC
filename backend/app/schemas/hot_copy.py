from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


HotCopyPlatform = Literal["douyin", "xiaohongshu", "shipinhao"]
RewriteMode = Literal["light", "medium", "strong"]
RewriteDuration = Literal["30s", "60s", "90s"]


class HotCopyMaterialManualCreate(BaseModel):
    project_id: int | None = Field(default=None, gt=0)
    platform: HotCopyPlatform = "douyin"
    source_url: str | None = Field(default=None, max_length=1000)
    account_name: str | None = Field(default=None, max_length=120)
    account_home_url: str | None = Field(default=None, max_length=1000)
    cover_url: str | None = Field(default=None, max_length=1000)
    title: str = Field(min_length=1, max_length=240)
    original_script: str = Field(min_length=1, max_length=12000)
    metrics_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title", "original_script", mode="before")
    @classmethod
    def strip_required_string(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("source_url", "account_name", "account_home_url", "cover_url", mode="before")
    @classmethod
    def strip_optional_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return value


class HotCopyMaterialAutoCreate(BaseModel):
    project_id: int | None = Field(default=None, gt=0)
    source_url: str | None = Field(default=None, max_length=1000)
    platform: HotCopyPlatform = "douyin"

    @field_validator("source_url", mode="before")
    @classmethod
    def strip_optional_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return value


class HotCopyMaterialRead(BaseModel):
    id: int
    user_id: int
    project_id: int | None = None
    platform: str
    source_type: str
    source_url: str | None = None
    account_name: str | None = None
    account_home_url: str | None = None
    cover_url: str | None = None
    title: str
    original_script: str
    metrics_json: dict[str, Any] = Field(default_factory=dict)
    analysis_json: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HotCopyAnalysisResponse(BaseModel):
    material: HotCopyMaterialRead
    analysis: dict[str, Any]
    generation_record_id: int | None = None


class HotCopyRewriteRequest(BaseModel):
    project_id: int | None = Field(default=None, gt=0)
    rewrite_mode: RewriteMode = "medium"
    duration: RewriteDuration = "60s"
    conversion_goal: str = Field(default="私信获客", min_length=1, max_length=80)
    product: str | None = Field(default=None, max_length=200)
    target_customer: str | None = Field(default=None, max_length=200)
    account_persona: str | None = Field(default=None, max_length=200)

    @field_validator("conversion_goal", mode="before")
    @classmethod
    def strip_required_string(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("product", "target_customer", "account_persona", mode="before")
    @classmethod
    def strip_optional_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return value


class HotCopyRewriteRead(BaseModel):
    id: int
    material_id: int
    user_id: int
    project_id: int | None = None
    rewrite_mode: str
    duration: str
    conversion_goal: str
    input_json: dict[str, Any] = Field(default_factory=dict)
    output_json: dict[str, Any] = Field(default_factory=dict)
    generation_record_id: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HotCopyRewriteResponse(BaseModel):
    rewrite: HotCopyRewriteRead
    output: dict[str, Any]
    generation_record_id: int | None = None


class HotCopyRedianbaoSearchRequest(BaseModel):
    keyword: str = Field(min_length=1, max_length=200)
    platform: HotCopyPlatform = "douyin"
    count: int = Field(default=30, ge=30, le=100)

    @field_validator("keyword", mode="before")
    @classmethod
    def strip_keyword(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value
