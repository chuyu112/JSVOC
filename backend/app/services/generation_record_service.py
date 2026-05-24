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


def get_generation_record_for_user(db: Session, record_id: int, user_id: int) -> GenerationRecord | None:
    statement = select(GenerationRecord).where(
        GenerationRecord.id == record_id,
        GenerationRecord.user_id == user_id,
    )
    return db.scalars(statement).first()


def get_generation_records(
    db: Session,
    user_id: int | None = None,
    project_id: int | None = None,
    module_name: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[GenerationRecord]:
    statement = select(GenerationRecord).order_by(GenerationRecord.created_at.desc())
    if user_id is not None:
        statement = statement.where(GenerationRecord.user_id == user_id)
    if project_id is not None:
        statement = statement.where(GenerationRecord.project_id == project_id)
    if module_name is not None:
        statement = statement.where(GenerationRecord.module_name == module_name)

    statement = statement.offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def get_project_generation_records_by_modules(
    db: Session,
    project_id: int,
    module_names: list[str],
) -> list[GenerationRecord]:
    if not module_names:
        return []
    statement = select(GenerationRecord).where(
        GenerationRecord.project_id == project_id,
        GenerationRecord.module_name.in_(module_names),
    )
    return list(db.scalars(statement).all())


def delete_generation_records_by_ids(db: Session, record_ids: list[int]) -> None:
    if not record_ids:
        return
    records = list(
        db.scalars(select(GenerationRecord).where(GenerationRecord.id.in_(record_ids))).all()
    )
    for record in records:
        db.delete(record)
    db.commit()
