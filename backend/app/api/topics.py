from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.topic import TopicGenerateRequest, TopicGenerateResponse, TopicRead
from app.services import project_service, topic_service


router = APIRouter(tags=["topics"])


def success_response(data: object, message: str = "") -> dict[str, object]:
    return {"success": True, "data": data, "message": message}


@router.post("/api/creation/topics/generate")
def generate_topics_api(
    payload: TopicGenerateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    generation = topic_service.generate_topics(db, payload)
    if generation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    gateway_result = generation.gateway_result
    if not gateway_result.success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=gateway_result.error or "选题生成失败",
        )

    response = TopicGenerateResponse(
        topics=[TopicRead.model_validate(topic) for topic in generation.topics],
        generation_record_id=gateway_result.generation_record_id,
        provider=gateway_result.provider,
        model=gateway_result.model,
        usage=gateway_result.usage,
        latency_ms=gateway_result.latency_ms,
    )
    return success_response(response.model_dump(mode="json"), "选题生成成功")


@router.get("/api/projects/{project_id}/topics")
def list_project_topics(
    project_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    project = project_service.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    topics = topic_service.get_project_topics(db, project_id, skip=skip, limit=limit)
    return success_response([TopicRead.model_validate(topic).model_dump(mode="json") for topic in topics])
