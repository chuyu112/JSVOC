from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.hot_copy import (
    HotCopyAnalysisResponse,
    HotCopyMaterialManualCreate,
    HotCopyMaterialRead,
    HotCopyRedianbaoSearchRequest,
    HotCopyRewriteRequest,
    HotCopyRewriteResponse,
)
from app.services import hot_copy_service


router = APIRouter(tags=["hot_copy"])


def success_response(data: object, message: str = "") -> dict[str, object]:
    return {"success": True, "data": data, "message": message}


def failure_response(data: object, message: str) -> dict[str, object]:
    return {"success": False, "data": data, "message": message}


@router.post("/api/hot-copy/materials/manual", status_code=201)
def create_manual_material(
    payload: HotCopyMaterialManualCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    material = hot_copy_service.create_manual_material(db, payload, current_user.id)
    data = HotCopyMaterialRead.model_validate(material).model_dump(mode="json")
    return success_response(data, "爆款素材已保存")


@router.get("/api/hot-copy/materials")
def list_materials(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    materials = hot_copy_service.list_materials(db, current_user.id, skip=skip, limit=limit)
    data = [HotCopyMaterialRead.model_validate(material).model_dump(mode="json") for material in materials]
    return success_response(data)


@router.get("/api/hot-copy/materials/{material_id}")
def get_material(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    material = hot_copy_service.require_material(db, material_id, current_user.id)
    data = HotCopyMaterialRead.model_validate(material).model_dump(mode="json")
    return success_response(data)


@router.post("/api/hot-copy/materials/{material_id}/analyze")
def analyze_material(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    material, analysis, generation_record_id = hot_copy_service.analyze_material(db, material_id, current_user.id)
    response = HotCopyAnalysisResponse(
        material=HotCopyMaterialRead.model_validate(material),
        analysis=analysis,
        generation_record_id=generation_record_id,
    )
    return success_response(response.model_dump(mode="json"), "爆点拆解完成")


@router.post("/api/hot-copy/materials/{material_id}/rewrite")
def rewrite_material(
    material_id: int,
    payload: HotCopyRewriteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    rewrite, output, generation_record_id = hot_copy_service.rewrite_material(
        db,
        material_id,
        payload,
        current_user.id,
    )
    response = HotCopyRewriteResponse.model_validate(
        {
            "rewrite": rewrite,
            "output": output,
            "generation_record_id": generation_record_id,
        }
    )
    return success_response(response.model_dump(mode="json"), "文案仿写完成")


@router.post("/api/hot-copy/redianbao/search")
def search_redianbao(
    payload: HotCopyRedianbaoSearchRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    _ = payload
    _ = current_user
    return failure_response(
        hot_copy_service.redianbao_reserved_response(),
        hot_copy_service.REDIANBAO_NOT_CONNECTED_MESSAGE,
    )
