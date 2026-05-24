from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.generation_record import GenerationRecordRead
from app.services import generation_record_service


router = APIRouter(prefix="/api/generation-records", tags=["generation-records"])


def success_response(data: object, message: str = "") -> dict[str, object]:
    return {"success": True, "data": data, "message": message}


@router.get("")
def list_generation_records(
    project_id: int | None = Query(default=None, gt=0),
    module_name: str | None = Query(default=None, min_length=1, max_length=80),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    records = generation_record_service.get_generation_records(
        db,
        project_id=project_id,
        module_name=module_name,
        skip=offset,
        limit=limit,
    )
    return success_response(
        [GenerationRecordRead.model_validate(record).model_dump(mode="json") for record in records]
    )


@router.get("/{record_id}")
def get_generation_record(record_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    record = generation_record_service.get_generation_record(db, record_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="生成记录不存在")

    return success_response(GenerationRecordRead.model_validate(record).model_dump(mode="json"))
