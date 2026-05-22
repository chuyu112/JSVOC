from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.generation_record import GenerationRecord
from app.schemas.generation_record import GenerationRecordCreate


def create_generation_record(
    db: Session,
    record_in: GenerationRecordCreate,
) -> GenerationRecord:
    record = GenerationRecord(**record_in.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_generation_record(db: Session, record_id: int) -> GenerationRecord | None:
    return db.get(GenerationRecord, record_id)


def get_generation_records(
    db: Session,
    project_id: int | None = None,
    module_name: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[GenerationRecord]:
    statement = select(GenerationRecord).order_by(GenerationRecord.created_at.desc())
    if project_id is not None:
        statement = statement.where(GenerationRecord.project_id == project_id)
    if module_name is not None:
        statement = statement.where(GenerationRecord.module_name == module_name)

    statement = statement.offset(skip).limit(limit)
    return list(db.scalars(statement).all())
