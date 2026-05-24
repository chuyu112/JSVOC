from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.generation_task import GenerationTaskRead
from app.services import generation_task_service


router = APIRouter(prefix="/api/generation-tasks", tags=["generation-tasks"])


def success_response(data: object, message: str = "") -> dict[str, object]:
    return {"success": True, "data": data, "message": message}


@router.get("")
def list_generation_tasks(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    tasks = generation_task_service.list_generation_tasks_for_user(
        db,
        user_id=current_user.id,
        limit=limit,
    )
    return success_response([GenerationTaskRead.model_validate(task).model_dump(mode="json") for task in tasks])


@router.get("/{task_id}")
def get_generation_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    task = generation_task_service.get_generation_task_for_user(db, task_id, current_user.id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="generation task not found")
    return success_response(GenerationTaskRead.model_validate(task).model_dump(mode="json"))
