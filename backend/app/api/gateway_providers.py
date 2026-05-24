from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.admin_auth import require_admin
from app.core.config import get_settings
from app.db.session import get_db
from app.models.gateway_provider import GatewayProvider
from app.schemas.gateway_provider import (
    GatewayProviderCreate,
    GatewayProviderDefaultRead,
    GatewayProviderRead,
    GatewayProviderUpdate,
)
from app.services import gateway_provider_service


router = APIRouter(
    prefix="/api/admin/gateway-providers",
    tags=["gateway-providers"],
    dependencies=[Depends(require_admin)],
)


def success_response(data: object, message: str = "") -> dict[str, object]:
    return {"success": True, "data": data, "message": message}


def serialize_provider(provider: GatewayProvider) -> dict[str, Any]:
    api_key = provider.api_key or ""
    return GatewayProviderRead(
        id=provider.id,
        capability=provider.capability,  # type: ignore[arg-type]
        name=provider.name,
        provider=provider.provider,
        base_url=provider.base_url,
        model=provider.model,
        is_enabled=provider.is_enabled,
        is_default=provider.is_default,
        config=provider.config or {},
        has_api_key=bool(api_key),
        api_key_mask=mask_api_key(api_key),
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    ).model_dump(mode="json")


def mask_api_key(api_key: str) -> str | None:
    if not api_key:
        return None
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return f"{api_key[:4]}...{api_key[-4:]}"


@router.get("")
def list_gateway_providers(
    capability: str | None = Query(default=None, pattern="^(chat|image|video)$"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    providers = gateway_provider_service.get_gateway_providers(
        db,
        capability=capability,
        skip=skip,
        limit=limit,
    )
    return success_response([serialize_provider(provider) for provider in providers])


@router.get("/defaults")
def list_gateway_provider_defaults(db: Session = Depends(get_db)) -> dict[str, object]:
    defaults = []
    for capability in ("chat", "image", "video"):
        provider = gateway_provider_service.get_default_gateway_provider(db, capability)
        defaults.append(serialize_default(capability, provider))
    return success_response(defaults)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_gateway_provider(
    payload: GatewayProviderCreate,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    provider = gateway_provider_service.create_gateway_provider(db, payload)
    return success_response(serialize_provider(provider), "网关 Provider 已创建")


@router.get("/{provider_id}")
def get_gateway_provider(provider_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    provider = gateway_provider_service.get_gateway_provider(db, provider_id)
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider 不存在")

    return success_response(serialize_provider(provider))


@router.put("/{provider_id}")
def update_gateway_provider(
    provider_id: int,
    payload: GatewayProviderUpdate,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    provider = gateway_provider_service.get_gateway_provider(db, provider_id)
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider 不存在")

    updated_provider = gateway_provider_service.update_gateway_provider(db, provider, payload)
    return success_response(serialize_provider(updated_provider), "网关 Provider 已更新")


@router.delete("/{provider_id}")
def delete_gateway_provider(provider_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    provider = gateway_provider_service.get_gateway_provider(db, provider_id)
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider 不存在")

    gateway_provider_service.delete_gateway_provider(db, provider)
    return success_response(None, "网关 Provider 已删除")


@router.post("/{provider_id}/set-default")
def set_default_gateway_provider(
    provider_id: int,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    provider = gateway_provider_service.get_gateway_provider(db, provider_id)
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider 不存在")

    updated_provider = gateway_provider_service.set_default_gateway_provider(db, provider)
    return success_response(serialize_provider(updated_provider), "默认 Provider 已切换")


def serialize_default(capability: str, provider: GatewayProvider | None) -> dict[str, Any]:
    if provider is not None:
        return GatewayProviderDefaultRead(
            capability=capability,  # type: ignore[arg-type]
            source="database",
            provider_config=GatewayProviderRead.model_validate(serialize_provider(provider)),
            fallback=None,
        ).model_dump(mode="json")

    settings = get_settings()
    fallback = None
    if capability == "chat":
        fallback = {
            "provider": settings.llm_provider,
            "base_url": settings.llm_base_url,
            "model": settings.llm_model,
            "timeout_seconds": settings.llm_timeout_seconds,
        }

    return GatewayProviderDefaultRead(
        capability=capability,  # type: ignore[arg-type]
        source="environment" if fallback else "none",
        provider_config=None,
        fallback=fallback,
    ).model_dump(mode="json")
