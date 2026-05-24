from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.project_reference_image import ProjectReferenceImageCreate, ProjectReferenceImageRead
from app.services import project_reference_image_service, project_service


router = APIRouter(prefix="/api/projects", tags=["reference-images"])


def success_response(data: object, message: str = "") -> dict[str, object]:
    return {"success": True, "data": data, "message": message}


@router.post("/{project_id}/reference-images")
def create_reference_image(
    project_id: int,
    payload: ProjectReferenceImageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    project = project_service.get_project_for_user(db, project_id, current_user.id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    allowed_types = {"persona", "product", "location"}
    ref_type = payload.reference_image_type.strip().lower()
    if ref_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的参考图类型，仅允许: {', '.join(allowed_types)}",
        )

    current_count = project_reference_image_service.count_reference_images_by_project_and_type(
        db, project_id, ref_type
    )
    if current_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="每类参考图最多上传 3 张",
        )

    image = project_reference_image_service.create_reference_image(
        db,
        project_id=project_id,
        reference_image_type=ref_type,
        source_image_base64=payload.source_image_base64,
        source_image_mime=payload.source_image_mime,
        source_image_filename=payload.source_image_filename,
    )
    return success_response(
        ProjectReferenceImageRead.model_validate(image).model_dump(mode="json"),
        "参考图上传成功",
    )


@router.get("/{project_id}/reference-images")
def list_reference_images(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    project = project_service.get_project_for_user(db, project_id, current_user.id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    images = project_reference_image_service.list_reference_images_by_project(db, project_id)
    return success_response(
        [ProjectReferenceImageRead.model_validate(img).model_dump(mode="json") for img in images]
    )


@router.delete("/{project_id}/reference-images/{image_id}")
def delete_reference_image(
    project_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    project = project_service.get_project_for_user(db, project_id, current_user.id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    image = project_reference_image_service.get_reference_image_for_project(db, image_id, project_id)
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="参考图不存在")

    project_reference_image_service.delete_reference_image(db, image)
    return success_response(None, "参考图删除成功")
