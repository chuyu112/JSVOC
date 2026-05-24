from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DigitalAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    asset_type: str
    source_project_id: int | None = None
    project_snapshot: dict[str, Any] = Field(default_factory=dict)
    title: str
    preview_text: str | None = None
    content_text: str | None = None
    generation_record_id: int | None = None
    oss_object_key: str | None = None
    mime_type: str | None = None
    file_size: int | None = None
    asset_metadata: dict[str, Any] = Field(default_factory=dict)
    access_url: str | None = None
    access_url_expires_at: int | None = None
    created_at: datetime
