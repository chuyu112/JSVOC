from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.generation_record import GenerationRecord
from app.models.generation_task import GenerationTask
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


def create_generation_record_from_task(db: Session, task: GenerationTask) -> GenerationRecord:
    existing = get_generation_record_for_task(db, task)
    if existing is not None:
        return existing

    result_data = task.result_data if isinstance(task.result_data, dict) else {}
    provider, model = _task_provider_model(task, result_data)
    record_in = GenerationRecordCreate(
        user_id=task.user_id,
        project_id=task.project_id,
        module_name=task.task_type,
        input_data=_task_input_data(task),
        output_data=_task_output_data(task, result_data),
        model_provider=provider,
        model_name=model,
        prompt_version="generation-task-v1",
        token_usage=_task_token_usage(result_data),
        latency_ms=_task_latency_ms(task, result_data),
    )
    return create_generation_record(db, record_in)


def get_generation_record_for_task(db: Session, task: GenerationTask) -> GenerationRecord | None:
    statement = select(GenerationRecord).where(
        GenerationRecord.user_id == task.user_id,
        GenerationRecord.module_name == task.task_type,
    )
    if task.project_id is None:
        statement = statement.where(GenerationRecord.project_id.is_(None))
    else:
        statement = statement.where(GenerationRecord.project_id == task.project_id)

    records = db.scalars(statement).all()
    for record in records:
        input_data = record.input_data if isinstance(record.input_data, dict) else {}
        metadata = input_data.get("metadata") if isinstance(input_data.get("metadata"), dict) else {}
        if metadata.get("generation_task_id") == task.id:
            return record
    return None


def _task_input_data(task: GenerationTask) -> dict[str, Any]:
    input_data = dict(task.input_data) if isinstance(task.input_data, dict) else {}
    existing_metadata = input_data.get("metadata") if isinstance(input_data.get("metadata"), dict) else {}
    input_data["metadata"] = {
        **existing_metadata,
        "generation_task_id": task.id,
        "task_type": task.task_type,
        "task_status": task.status,
        "credit_cost": task.credit_cost,
        "credit_transaction_id": task.credit_transaction_id,
        "started_at": _format_datetime(task.started_at),
        "completed_at": _format_datetime(task.completed_at),
    }
    return input_data


def _task_output_data(task: GenerationTask, result_data: dict[str, Any]) -> dict[str, Any]:
    success = task.status == "succeeded"
    failure_reason = None if success else (task.error_message or "generation task failed without an error message")
    return {
        "success": success,
        "status": task.status,
        "data": result_data,
        "error": failure_reason,
        "failure_reason": failure_reason,
        "generation_task_id": task.id,
    }


def _task_provider_model(task: GenerationTask, result_data: dict[str, Any]) -> tuple[str, str]:
    input_data = task.input_data if isinstance(task.input_data, dict) else {}
    options = input_data.get("options") if isinstance(input_data.get("options"), dict) else {}

    provider = str(result_data.get("provider") or "").strip()
    model = str(result_data.get("model") or options.get("model") or "").strip()
    if not provider:
        provider = "seedance" if task.task_type == "video_generate" else "image_generation"
    if not model:
        model = "seedance" if task.task_type == "video_generate" else "gpt-image-2"
    return provider[:80], model[:120]


def _task_token_usage(result_data: dict[str, Any]) -> dict[str, Any]:
    usage = result_data.get("usage")
    return usage if isinstance(usage, dict) else {}


def _task_latency_ms(task: GenerationTask, result_data: dict[str, Any]) -> int | None:
    latency = result_data.get("latency_ms")
    if isinstance(latency, (int, float)) and latency >= 0:
        return int(latency)
    if task.started_at is None or task.completed_at is None:
        return None
    try:
        return max(0, int((task.completed_at - task.started_at).total_seconds() * 1000))
    except TypeError:
        return None


def _format_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


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
