from datetime import datetime

from pydantic import BaseModel, Field


class ProjectReferenceImageCreate(BaseModel):
    reference_image_type: str = Field(min_length=1, max_length=20)
    source_image_base64: str = Field(min_length=1, max_length=20_000_000)
    source_image_mime: str = Field(default="image/png", min_length=1, max_length=80)
    source_image_filename: str = Field(default="source.png", min_length=1, max_length=160)


class ProjectReferenceImageRead(BaseModel):
    id: int
    project_id: int
    reference_image_type: str
    source_image_base64: str
    source_image_mime: str
    source_image_filename: str
    created_at: datetime

    class Config:
        from_attributes = True
