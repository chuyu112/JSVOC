from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project_reference_image import ProjectReferenceImage


def create_reference_image(
    db: Session,
    *,
    project_id: int,
    reference_image_type: str,
    source_image_base64: str,
    source_image_mime: str,
    source_image_filename: str,
) -> ProjectReferenceImage:
    image = ProjectReferenceImage(
        project_id=project_id,
        reference_image_type=reference_image_type,
        source_image_base64=source_image_base64,
        source_image_mime=source_image_mime,
        source_image_filename=source_image_filename,
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


def list_reference_images_by_project(
    db: Session,
    project_id: int,
) -> list[ProjectReferenceImage]:
    statement = (
        select(ProjectReferenceImage)
        .where(ProjectReferenceImage.project_id == project_id)
        .order_by(ProjectReferenceImage.created_at.asc())
    )
    return list(db.scalars(statement).all())


def count_reference_images_by_project_and_type(
    db: Session,
    project_id: int,
    reference_image_type: str,
) -> int:
    statement = select(ProjectReferenceImage).where(
        ProjectReferenceImage.project_id == project_id,
        ProjectReferenceImage.reference_image_type == reference_image_type,
    )
    return len(list(db.scalars(statement).all()))


def get_reference_image_for_project(
    db: Session,
    image_id: int,
    project_id: int,
) -> ProjectReferenceImage | None:
    statement = select(ProjectReferenceImage).where(
        ProjectReferenceImage.id == image_id,
        ProjectReferenceImage.project_id == project_id,
    )
    return db.scalars(statement).first()


def delete_reference_image(db: Session, image: ProjectReferenceImage) -> None:
    db.delete(image)
    db.commit()
