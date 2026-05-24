from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.gateway_provider import GatewayProvider
from app.schemas.gateway_provider import GatewayProviderCreate, GatewayProviderUpdate


VALID_CAPABILITIES = {"chat", "image", "video"}


def create_gateway_provider(
    db: Session,
    provider_in: GatewayProviderCreate,
) -> GatewayProvider:
    data = provider_in.model_dump()
    if provider_in.is_default or not _has_enabled_provider(db, provider_in.capability):
        _unset_default_for_capability(db, provider_in.capability)
        data["is_default"] = True

    provider = GatewayProvider(**data)
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


def get_gateway_provider(db: Session, provider_id: int) -> GatewayProvider | None:
    return db.get(GatewayProvider, provider_id)


def get_gateway_providers(
    db: Session,
    capability: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[GatewayProvider]:
    statement = select(GatewayProvider).order_by(
        GatewayProvider.capability.asc(),
        GatewayProvider.is_default.desc(),
        GatewayProvider.created_at.desc(),
    )
    if capability is not None:
        statement = statement.where(GatewayProvider.capability == capability)

    statement = statement.offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def update_gateway_provider(
    db: Session,
    provider: GatewayProvider,
    provider_in: GatewayProviderUpdate,
) -> GatewayProvider:
    old_capability = provider.capability
    update_data = provider_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(provider, field, value)

    if provider.is_default:
        _unset_default_for_capability(db, provider.capability, exclude_id=provider.id)

    if update_data.get("is_enabled") is False and provider.is_default:
        provider.is_default = False

    if old_capability != provider.capability:
        _unset_default_for_capability(db, old_capability, exclude_id=provider.id)

    provider.updated_at = datetime.utcnow()
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


def delete_gateway_provider(db: Session, provider: GatewayProvider) -> None:
    db.delete(provider)
    db.commit()


def set_default_gateway_provider(db: Session, provider: GatewayProvider) -> GatewayProvider:
    provider.is_enabled = True
    provider.is_default = True
    provider.updated_at = datetime.utcnow()
    _unset_default_for_capability(db, provider.capability, exclude_id=provider.id)
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


def get_default_gateway_provider(
    db: Session,
    capability: str,
) -> GatewayProvider | None:
    statement = (
        select(GatewayProvider)
        .where(
            GatewayProvider.capability == capability,
            GatewayProvider.is_enabled.is_(True),
            GatewayProvider.is_default.is_(True),
        )
        .order_by(GatewayProvider.updated_at.desc(), GatewayProvider.id.desc())
        .limit(1)
    )
    return db.scalars(statement).first()


def _has_enabled_provider(db: Session, capability: str) -> bool:
    statement = (
        select(GatewayProvider.id)
        .where(
            GatewayProvider.capability == capability,
            GatewayProvider.is_enabled.is_(True),
        )
        .limit(1)
    )
    return db.scalar(statement) is not None


def _unset_default_for_capability(
    db: Session,
    capability: str,
    exclude_id: int | None = None,
) -> None:
    statement = update(GatewayProvider).where(GatewayProvider.capability == capability)
    if exclude_id is not None:
        statement = statement.where(GatewayProvider.id != exclude_id)

    db.execute(statement.values(is_default=False, updated_at=datetime.utcnow()))
