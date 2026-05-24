from datetime import datetime

from pydantic import BaseModel, Field, field_validator


SUPPORTED_LLM_CHANNEL_PROVIDERS = {
    "mock",
    "openai_compatible",
    "dataeye",
    "moyu",
    "anthropic_compatible",
}


def normalize_provider(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_")
    if normalized == "gpt_api":
        normalized = "openai_compatible"
    if normalized not in SUPPORTED_LLM_CHANNEL_PROVIDERS:
        raise ValueError(f"unsupported provider: {value}")
    return normalized


class LLMChannelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    provider: str = Field(min_length=1, max_length=60)
    base_url: str = Field(default="", max_length=1000)
    api_key: str = Field(default="", max_length=2000)
    model: str = Field(min_length=1, max_length=160)
    is_active: bool = False

    @field_validator("provider")
    @classmethod
    def _validate_provider(cls, value: str) -> str:
        return normalize_provider(value)

    @field_validator("name", "base_url", "api_key", "model")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        return value.strip()


class LLMChannelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    provider: str | None = Field(default=None, min_length=1, max_length=60)
    base_url: str | None = Field(default=None, max_length=1000)
    api_key: str | None = Field(default=None, max_length=2000)
    model: str | None = Field(default=None, min_length=1, max_length=160)
    is_active: bool | None = None

    @field_validator("provider")
    @classmethod
    def _validate_provider(cls, value: str | None) -> str | None:
        return normalize_provider(value) if value is not None else None

    @field_validator("name", "base_url", "api_key", "model")
    @classmethod
    def _strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class LLMChannelRead(BaseModel):
    id: int
    name: str
    provider: str
    base_url: str
    model: str
    is_active: bool
    has_api_key: bool
    created_at: datetime
    updated_at: datetime


class LLMChannelTestResult(BaseModel):
    success: bool
    provider: str
    model: str
    message: str
    latency_ms: int = 0
    error: str | None = None
