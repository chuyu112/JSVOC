from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class HotVideoSearchRequest(BaseModel):
    project_id: int | None = Field(default=None, gt=0)
    platform: str = Field(default="抖音", min_length=1, max_length=40)
    keyword: str = Field(min_length=1, max_length=200)
    search_focus: str = Field(default="同赛道热门视频", min_length=1, max_length=80)
    count: int = Field(default=8, ge=1, le=12)
    web_search_context_size: Literal["low", "medium", "high"] = "medium"

    @field_validator("keyword", "platform", "search_focus")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value cannot be blank")
        return cleaned


class HotVideoItem(BaseModel):
    title: str = ""
    platform: str = ""
    creator: str = ""
    source_url: str = ""
    source_title: str = ""
    publish_time: str = ""
    metrics: dict[str, Any] = Field(default_factory=dict)
    why_trending: str = ""
    hook: str = ""
    structure: list[str] = Field(default_factory=list)
    remake_angle: str = ""
    rewrite_brief: str = ""
    risk_notes: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class HotVideoSearchResponse(BaseModel):
    items: list[HotVideoItem]
    provider: str
    model: str
    usage: dict[str, Any]
    sources: list[dict[str, Any]] = Field(default_factory=list)
    latency_ms: int
    generation_record_id: int | None = None
