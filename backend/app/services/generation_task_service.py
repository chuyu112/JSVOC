import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.datetime_utils import utcnow_naive
from app.models.generation_task import GenerationTask
from app.schemas.generation_task import GenerationTaskCreate


logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_generation_task(
    db: Session,
    payload: GenerationTaskCreate,
    *,
    user_id: int | None = None,
) -> GenerationTask:
    task = GenerationTask(
        task_type=payload.task_type,
        status="queued",
        user_id=user_id,
        project_id=payload.project_id,
        input_data=payload.input_data,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_generation_task(db: Session, task_id: int) -> GenerationTask | None:
    return db.get(GenerationTask, task_id)


def get_generation_task_for_user(db: Session, task_id: int, user_id: int) -> GenerationTask | None:
    task = get_generation_task(db, task_id)
    if task is None or task.user_id != user_id:
        return None
    return task


def list_generation_tasks_for_user(
    db: Session,
    *,
    user_id: int,
    limit: int = 10,
) -> list[GenerationTask]:
    return list(
        db.scalars(
            select(GenerationTask)
            .where(GenerationTask.user_id == user_id)
            .order_by(GenerationTask.created_at.desc(), GenerationTask.id.desc())
            .limit(limit)
        ).all()
    )


def mark_generation_task_running(db: Session, task_id: int) -> GenerationTask | None:
    task = get_generation_task(db, task_id)
    if task is None:
        return None
    task.status = "running"
    now = _utcnow()
    task.started_at = now
    task.updated_at = now
    db.commit()
    db.refresh(task)
    return task


def mark_generation_task_succeeded(db: Session, task_id: int, result_data: dict) -> GenerationTask | None:
    task = get_generation_task(db, task_id)
    if task is None:
        return None
    task.status = "succeeded"
    task.result_data = result_data
    task.error_message = None
    now = _utcnow()
    task.completed_at = now
    task.updated_at = now
    db.commit()
    db.refresh(task)
    return task


def mark_generation_task_failed(db: Session, task_id: int, error_message: str) -> GenerationTask | None:
    task = get_generation_task(db, task_id)
    if task is None:
        return None
    task.status = "failed"
    task.error_message = error_message[:2000]
    now = _utcnow()
    task.completed_at = now
    task.updated_at = now
    db.commit()
    db.refresh(task)
    return task


def update_generation_task_result_data(db: Session, task_id: int, result_data: dict) -> GenerationTask | None:
    task = get_generation_task(db, task_id)
    if task is None:
        return None
    existing = task.result_data if isinstance(task.result_data, dict) else {}
    task.result_data = {**existing, **result_data}
    task.updated_at = utcnow_naive()
    db.commit()
    db.refresh(task)
    return task


def attach_credit_charge(
    db: Session,
    task_id: int,
    *,
    credit_cost: int,
    credit_transaction_id: int | None,
) -> GenerationTask | None:
    task = get_generation_task(db, task_id)
    if task is None:
        return None
    task.credit_cost = credit_cost
    task.credit_transaction_id = credit_transaction_id
    task.updated_at = _utcnow()
    db.commit()
    db.refresh(task)
    return task


def fail_stale_generation_tasks(
    db: Session,
    *,
    max_age_minutes: int = 60,
    error_message: str = "生成任务已超时或服务重启中断，请重新生成。",
) -> int:
    cutoff = utcnow_naive() - timedelta(minutes=max_age_minutes)
    tasks = db.scalars(
        select(GenerationTask).where(
            GenerationTask.status.in_(("queued", "running")),
            GenerationTask.updated_at < cutoff,
        )
    ).all()
    if not tasks:
        return 0

    now = utcnow_naive()
    for task in tasks:
        task.status = "failed"
        task.error_message = error_message[:2000]
        task.completed_at = now
        task.updated_at = now
    db.commit()
    from app.services.generation_record_service import create_generation_record_from_task

    for task in tasks:
        try:
            create_generation_record_from_task(db, task)
        except Exception:  # noqa: BLE001 - stale cleanup must not fail because history mirroring failed.
            db.rollback()
            logger.exception("stale generation task history persistence failed", extra={"task_id": task.id})
    return len(tasks)
