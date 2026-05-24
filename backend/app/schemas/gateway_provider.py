from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


GatewayCapability = Literal["chat", "image", "video"]


class GatewayProviderBase(BaseModel):
    capability: GatewayCapability
    name: str = Field(min_length=1, max_length=120)
    provider: str = Field(min_length=1, max_length=80)
    base_url: str | None = None
    api_key: str | None = None
    model: str = Field(min_length=1, max_length=160)
    is_enabled: bool = True
    is_default: bool = False
    config: dict[str, Any] = Field(default_factory=dict)


class GatewayProviderCreate(GatewayProviderBase):
    pass


class GatewayProviderUpdate(BaseModel):
    capability: GatewayCapability | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    provider: str | None = Field(default=None, min_length=1, max_length=80)
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = Field(default=None, min_length=1, max_length=160)
    is_enabled: bool | None = None
    is_default: bool | None = None
    config: dict[str, Any] | None = None


class GatewayProviderRead(BaseModel):
    id: int
    capability: GatewayCapability
    name: str
    provider: str
    base_url: str | None
    model: str
    is_enabled: bool
    is_default: bool
    config: dict[str, Any]
    has_api_key: bool
    api_key_mask: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GatewayProviderDefaultRead(BaseModel):
    capability: GatewayCapability
    source: str
    provider_config: GatewayProviderRead | None = None
    fallback: dict[str, Any] | None = None
