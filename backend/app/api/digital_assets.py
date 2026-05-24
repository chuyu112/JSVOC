from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.digital_asset import DigitalAssetRead
from app.services import digital_asset_service, storage_service


router = APIRouter(prefix="/api/digital-assets", tags=["digital-assets"])


def success_response(data: object, message: str = "") -> dict[str, object]:
    return {"success": True, "data": data, "message": message}


def serialize_asset(asset: object) -> dict[str, object]:
    payload = DigitalAssetRead.model_validate(asset).model_dump(mode="json")
    object_key = payload.get("oss_object_key")
    if object_key and storage_service.is_oss_configured():
        access_url, expires_at = storage_service.sign_get_url(str(object_key))
        payload["access_url"] = access_url
        payload["access_url_expires_at"] = expires_at
    return payload


@router.get("")
def list_digital_assets(
    asset_type: str | None = Query(default=None, min_length=1, max_length=40),
    project_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    assets = digital_asset_service.list_digital_assets(
        db,
        user_id=current_user.id,
        asset_type=asset_type,
        source_project_id=project_id,
        skip=offset,
        limit=limit,
    )
    return success_response([serialize_asset(asset) for asset in assets])


@router.get("/{asset_id}")
def get_digital_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    asset = digital_asset_service.get_digital_asset_for_user(db, asset_id, current_user.id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="数字资产不存在")
    return success_response(serialize_asset(asset))


@router.delete("/{asset_id}")
def delete_digital_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    asset = digital_asset_service.get_digital_asset_for_user(db, asset_id, current_user.id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="数字资产不存在")
    digital_asset_service.delete_digital_asset(db, asset)
    return success_response(None, "删除成功")
