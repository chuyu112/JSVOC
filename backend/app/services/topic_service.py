from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.llm.llm_gateway import LLMGateway, LLMGatewayRequest, LLMGatewayResponse
from app.models.topic import Topic
from app.prompts.topic_prompt import (
    TOPICS_MODULE,
    TOPICS_OUTPUT_SCHEMA,
    TOPICS_PROMPT_VERSION,
    build_topic_prompts,
)
from app.schemas.topic import TopicCreate, TopicGenerateRequest
from app.services import account_strategy_context_service, project_service


class TopicGeneration:
    def __init__(self, topics: list[Topic], gateway_result: LLMGatewayResponse):
        self.topics = topics
        self.gateway_result = gateway_result


def generate_topics(db: Session, payload: TopicGenerateRequest) -> TopicGeneration | None:
    project = project_service.get_project(db, payload.project_id)
    if project is None:
        return None

    strategy_context = account_strategy_context_service.get_latest_account_strategy_context(
        db,
        payload.project_id,
    )
    system_prompt, user_prompt = build_topic_prompts(
        project,
        strategy_context,
        payload.platform,
        payload.goal,
        payload.count,
    )
    gateway_result = LLMGateway().generate(
        db=db,
        project_id=project.id,
        prompt_version=TOPICS_PROMPT_VERSION,
        request=LLMGatewayRequest(
            module_name=TOPICS_MODULE,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=TOPICS_OUTPUT_SCHEMA,
            temperature=payload.temperature,
            metadata={
                "project_id": project.id,
                "platform": payload.platform,
                "goal": payload.goal,
                "count": payload.count,
                "industry": project.industry,
                "product": project.product,
                "account_strategy_context_id": strategy_context.id if strategy_context else None,
            },
        ),
    )
    if not gateway_result.success:
        return TopicGeneration(topics=[], gateway_result=gateway_result)

    topic_inputs = normalize_topics(gateway_result.data, payload)
    topics = create_topics(db, topic_inputs)
    return TopicGeneration(topics=topics, gateway_result=gateway_result)


def create_topics(db: Session, topics_in: list[TopicCreate]) -> list[Topic]:
    topics = [Topic(**topic_in.model_dump()) for topic_in in topics_in]
    db.add_all(topics)
    db.commit()
    for topic in topics:
        db.refresh(topic)
    return topics


def get_project_topics(
    db: Session,
    project_id: int,
    skip: int = 0,
    limit: int = 100,
) -> list[Topic]:
    statement = (
        select(Topic)
        .where(Topic.project_id == project_id)
        .order_by(Topic.created_at.desc(), Topic.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def normalize_topics(data: Any, payload: TopicGenerateRequest) -> list[TopicCreate]:
    raw_topics = []
    if isinstance(data, dict):
        raw_topics = ensure_list(data.get("topics"))
    elif isinstance(data, list):
        raw_topics = data

    topics: list[TopicCreate] = []
    for index, item in enumerate(raw_topics[: payload.count], start=1):
        if not isinstance(item, dict):
            item = {"title": str(item)}

        topic_data = {
            "user_pain_point": str(item.get("user_pain_point") or ""),
            "hook": str(item.get("hook") or ""),
            "shooting_suggestion": str(item.get("shooting_suggestion") or ""),
            "conversion_method": str(item.get("conversion_method") or ""),
        }
        topics.append(
            TopicCreate(
                project_id=payload.project_id,
                title=str(item.get("title") or f"选题 {index}"),
                content_type=str(item.get("content_type") or "选题"),
                platform=str(item.get("platform") or payload.platform),
                goal=str(item.get("goal") or payload.goal),
                selling_point=str(item.get("selling_point") or item.get("conversion_method") or ""),
                score=ensure_score(item.get("score")),
                topic_data=topic_data,
            )
        )

    return topics


def ensure_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def ensure_score(value: Any) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return 0
    return min(100, max(0, score))
