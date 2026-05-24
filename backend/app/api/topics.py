from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.topic import (
    TopicBatchGenerateRequest,
    TopicBatchGenerateResponse,
    TopicFavoriteUpdate,
    TopicGenerateRequest,
    TopicGenerateResponse,
    TopicRead,
)
from app.services import credit_service, project_service, topic_service


router = APIRouter(tags=["topics"])


def success_response(data: object, message: str = "") -> dict[str, object]:
    return {"success": True, "data": data, "message": message}


@router.post("/api/creation/topics/generate")
def generate_topics_api(
    payload: TopicGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    project = project_service.get_project_for_user(db, payload.project_id, current_user.id)
    generation = topic_service.generate_topics(db, payload, current_user.id, project=project)
    if generation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    gateway_result = generation.gateway_result
    if not gateway_result.success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=gateway_result.error or "选题生成失败",
        )
    if not generation.topics:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="选题生成未返回可用内容，请重试",
        )

    response = TopicGenerateResponse(
        topics=[TopicRead.model_validate(topic) for topic in generation.topics],
        generation_record_id=gateway_result.generation_record_id,
        provider=gateway_result.provider,
        model=gateway_result.model,
        usage=gateway_result.usage,
        latency_ms=gateway_result.latency_ms,
    )
    credit_cost = credit_service.topic_generation_cost(gateway_result.usage)
    credit_service.charge_credits(
        db,
        user_id=current_user.id,
        cost=credit_cost,
        reason="topic_generation",
        reference_type="generation_record",
        reference_id=gateway_result.generation_record_id,
        metadata={
            "module": "topic",
            "topic_count": len(generation.topics),
            "total_tokens": credit_service.token_usage_total(gateway_result.usage),
        },
    )
    return success_response(response.model_dump(mode="json"), "选题生成成功")


@router.post("/api/creation/topics/generate-batch")
def generate_topics_batch_api(
    payload: TopicBatchGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    project = project_service.get_project_for_user(db, payload.project_id, current_user.id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    result = topic_service.generate_topics_batch(db, payload, current_user.id)
    topics = result.get("topics", [])
    if not topics:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="批量选题生成未返回可用内容，请重试",
        )

    response = TopicBatchGenerateResponse(
        topics=[TopicRead.model_validate(topic) for topic in topics],
        generated_count=result["generated_count"],
        target_count=result["target_count"],
        provider=result["provider"],
        model=result["model"],
        latency_ms=result["latency_ms"],
    )
    usage = result.get("usage") if isinstance(result.get("usage"), dict) else {}
    credit_cost = credit_service.topic_generation_cost(usage)
    credit_service.charge_credits(
        db,
        user_id=current_user.id,
        cost=credit_cost,
        reason="topic_batch_generation",
        reference_type="topic_batch",
        metadata={
            "module": "topic_batch",
            "generated_count": result["generated_count"],
            "total_tokens": credit_service.token_usage_total(usage),
        },
    )
    return success_response(response.model_dump(mode="json"), "批量选题生成成功")


@router.get("/api/projects/{project_id}/topics")
def list_project_topics(
    project_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    project = project_service.get_project_for_user(db, project_id, current_user.id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    topics = topic_service.get_project_topics(db, project_id, skip=skip, limit=limit)
    return success_response([TopicRead.model_validate(topic).model_dump(mode="json") for topic in topics])


@router.patch("/api/topics/{topic_id}/favorite")
def update_topic_favorite(
    topic_id: int,
    payload: TopicFavoriteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    topic = topic_service.get_topic_for_user(db, topic_id, current_user.id)
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="选题不存在")

    topic = topic_service.update_topic_favorite(db, topic.id, payload.is_favorite)
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="选题不存在")

    return success_response(TopicRead.model_validate(topic).model_dump(mode="json"), "选题已更新")


@router.delete("/api/topics/{topic_id}")
def delete_topic(
    topic_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    topic = topic_service.get_topic_for_user(db, topic_id, current_user.id)
    if topic is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="选题不存在")

    deleted = topic_service.delete_topic(db, topic.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="选题不存在")

    return success_response({"id": topic_id}, "选题已删除")
