from pydantic import BaseModel, Field
from datetime import datetime


class DigitalHumanAvatarBase(BaseModel):
    name: str
    avatar_type: str = "preset"
    thumbnail_url: str | None = None
    video_url: str | None = None
    gender: str | None = None
    config_json: dict = Field(default_factory=dict)
    is_active: bool = True


class DigitalHumanAvatarCreate(DigitalHumanAvatarBase):
    pass


class DigitalHumanAvatarRead(DigitalHumanAvatarBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class DigitalHumanVoiceBase(BaseModel):
    name: str
    voice_type: str = "preset"
    sample_url: str | None = None
    gender: str | None = None
    config_json: dict = Field(default_factory=dict)
    is_active: bool = True


class DigitalHumanVoiceCreate(DigitalHumanVoiceBase):
    pass


class DigitalHumanVoiceRead(DigitalHumanVoiceBase):
    id: int
    user_id: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class DigitalHumanVideoBase(BaseModel):
    project_id: int | None = None
    script_id: int | None = None
    voice_id: int | None = None
    avatar_id: int | None = None
    title: str
    video_url: str | None = None
    audio_url: str | None = None
    duration: float | None = None
    status: str = "pending"
    config_json: dict = Field(default_factory=dict)
    error_message: str | None = None
    credit_cost: int | None = None


class DigitalHumanVideoCreate(BaseModel):
    project_id: int
    script_id: int
    voice_id: int
    avatar_id: int
    with_subtitle: bool = True
    with_bgm: bool = False
    resolution: str = "1080p"


class DigitalHumanVideoRead(DigitalHumanVideoBase):
    id: int
    user_id: int | None = None
    task_id: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class DigitalHumanVideoGenerateResponse(BaseModel):
    task_id: int
    video_id: int
    status: str
    message: str
