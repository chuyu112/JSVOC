from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.topic import Topic
from app.schemas.script import ScriptGenerateRequest, ScriptGenerateResponse, ScriptRead
from app.services import project_service, script_service


router = APIRouter(tags=["scripts"])


def success_response(data: object, message: str = "") -> dict[str, object]:
    return {"success": True, "data": data, "message": message}


@router.post("/api/creation/scripts/generate")
def generate_script_api(
    payload: ScriptGenerateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    generation = script_service.generate_script(db, payload)
    if generation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    if generation.script is None and generation.gateway_result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="选题不存在")

    gateway_result = generation.gateway_result
    if gateway_result is None or not gateway_result.success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(gateway_result.error if gateway_result else None) or "文案生成失败",
        )

    response = ScriptGenerateResponse(
        script=ScriptRead.model_validate(generation.script),
        generation_record_id=gateway_result.generation_record_id,
        provider=gateway_result.provider,
        model=gateway_result.model,
        usage=gateway_result.usage,
        latency_ms=gateway_result.latency_ms,
    )
    return success_response(response.model_dump(mode="json"), "文案生成成功")


@router.get("/api/topics/{topic_id}/scripts")
def list_topic_scripts(
    topic_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="选题不存在")

    scripts = script_service.get_topic_scripts(db, topic_id, skip=skip, limit=limit)
    return success_response([ScriptRead.model_validate(script).model_dump(mode="json") for script in scripts])


@router.get("/api/projects/{project_id}/scripts")
def list_project_scripts(
    project_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    project = project_service.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    scripts = script_service.get_project_scripts(db, project_id, skip=skip, limit=limit)
    return success_response([ScriptRead.model_validate(script).model_dump(mode="json") for script in scripts])
