from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import SessionLocal
from app.models.llm_channel import LLMChannel
from app.schemas.llm_channel import LLMChannelCreate, LLMChannelRead, LLMChannelUpdate


def list_channels(db: Session) -> list[LLMChannel]:
    return list(db.scalars(select(LLMChannel).order_by(LLMChannel.id.asc())).all())


def get_channel_or_404(db: Session, channel_id: int) -> LLMChannel:
    channel = db.get(LLMChannel, channel_id)
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="LLM channel not found")
    return channel


def get_active_channel(db: Session) -> LLMChannel | None:
    return db.scalars(select(LLMChannel).where(LLMChannel.is_active.is_(True))).first()


def create_channel(db: Session, payload: LLMChannelCreate) -> LLMChannel:
    if payload.is_active:
        deactivate_all_channels(db)
    channel = LLMChannel(
        name=payload.name,
        provider=payload.provider,
        base_url=payload.base_url,
        api_key=payload.api_key,
        model=payload.model,
        is_active=payload.is_active,
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel


def update_channel(db: Session, channel: LLMChannel, payload: LLMChannelUpdate) -> LLMChannel:
    if payload.name is not None:
        channel.name = payload.name
    if payload.provider is not None:
        channel.provider = payload.provider
    if payload.base_url is not None:
        channel.base_url = payload.base_url
    if payload.api_key is not None and payload.api_key.strip():
        channel.api_key = payload.api_key.strip()
    if payload.model is not None:
        channel.model = payload.model
    if payload.is_active is not None:
        if payload.is_active:
            deactivate_all_channels(db)
            channel.is_active = True
        else:
            channel.is_active = False
    db.commit()
    db.refresh(channel)
    return channel


def activate_channel(db: Session, channel: LLMChannel) -> LLMChannel:
    deactivate_all_channels(db)
    channel.is_active = True
    db.commit()
    db.refresh(channel)
    return channel


def delete_channel(db: Session, channel: LLMChannel) -> None:
    db.delete(channel)
    db.commit()


def deactivate_all_channels(db: Session) -> None:
    db.execute(update(LLMChannel).values(is_active=False))


def serialize_channel(channel: LLMChannel) -> LLMChannelRead:
    return LLMChannelRead(
        id=channel.id,
        name=channel.name,
        provider=channel.provider,
        base_url=channel.base_url,
        model=channel.model,
        is_active=channel.is_active,
        has_api_key=bool(channel.api_key.strip()),
        created_at=channel.created_at,
        updated_at=channel.updated_at,
    )


def settings_for_channel(channel: LLMChannel, settings: Settings | None = None) -> Settings:
    base = settings or get_settings()
    return base.model_copy(
        update={
            "llm_provider": channel.provider,
            "llm_base_url": channel.base_url,
            "llm_api_key": channel.api_key,
            "llm_model": channel.model,
        }
    )


def get_effective_llm_settings(
    db: Session | None = None,
    settings: Settings | None = None,
) -> Settings:
    base = settings or get_settings()
    if db is not None:
        active = get_active_channel(db)
        return settings_for_channel(active, base) if active is not None else base

    with SessionLocal() as local_db:
        active = get_active_channel(local_db)
        return settings_for_channel(active, base) if active is not None else base
