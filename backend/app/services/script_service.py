from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.llm.llm_gateway import LLMGateway, LLMGatewayRequest, LLMGatewayResponse
from app.models.project import Project
from app.models.script import Script
from app.models.topic import Topic
from app.prompts.script_prompt import (
    SCRIPT_MODULE,
    SCRIPT_OUTPUT_SCHEMA,
    SCRIPT_PROMPT_VERSION,
    build_script_prompts,
)
from app.schemas.script import ScriptCreate, ScriptGenerateRequest
from app.services import account_strategy_context_service, digital_asset_service, project_service


class ScriptGeneration:
    def __init__(self, script: Script | None, gateway_result: LLMGatewayResponse | None = None):
        self.script = script
        self.gateway_result = gateway_result


def generate_script(
    db: Session,
    payload: ScriptGenerateRequest,
    user_id: int,
    project: Project | None = None,
    topic: Topic | None = None,
) -> ScriptGeneration | None:
    project = project or project_service.get_project_for_user(db, payload.project_id, user_id)
    if project is None:
        return None

    topic = topic or db.get(Topic, payload.topic_id)
    if topic is None or topic.project_id != project.id:
        return ScriptGeneration(script=None)

    platform = payload.platform or topic.platform
    strategy_context = account_strategy_context_service.get_latest_account_strategy_context(
        db,
        project.id,
    )
    system_prompt, user_prompt = build_script_prompts(
        project,
        topic,
        strategy_context,
        platform,
        payload.script_type,
        payload.duration,
        payload.goal,
        get_topic_scripts(db, topic.id, limit=10),
    )
    gateway_result = LLMGateway().generate(
        db=db,
        project_id=project.id,
        user_id=user_id,
        prompt_version=SCRIPT_PROMPT_VERSION,
        request=LLMGatewayRequest(
            module_name=SCRIPT_MODULE,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=SCRIPT_OUTPUT_SCHEMA,
            temperature=payload.temperature,
            max_tokens=4000,
            metadata={
                "project_id": project.id,
                "topic_id": topic.id,
                "topic_title": topic.title,
                "platform": platform,
                "script_type": payload.script_type,
                "duration": payload.duration,
                "goal": payload.goal,
                "industry": project.industry,
                "product": project.product,
                "account_strategy_context_id": strategy_context.id if strategy_context else None,
            },
        ),
    )
    if not gateway_result.success:
        return ScriptGeneration(script=None, gateway_result=gateway_result)

    script_in = normalize_script(gateway_result.data, payload, topic, platform)
    script = create_script(db, script_in)
    digital_asset_service.create_script_asset(
        db,
        user_id=user_id,
        project=project,
        script=script,
        generation_record_id=gateway_result.generation_record_id,
    )
    return ScriptGeneration(script=script, gateway_result=gateway_result)


def create_script(db: Session, script_in: ScriptCreate) -> Script:
    script = Script(**script_in.model_dump())
    db.add(script)
    db.commit()
    db.refresh(script)
    return script


def get_topic_scripts(
    db: Session,
    topic_id: int,
    skip: int = 0,
    limit: int = 100,
) -> list[Script]:
    statement = (
        select(Script)
        .where(Script.topic_id == topic_id)
        .order_by(Script.created_at.desc(), Script.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def get_project_scripts(
    db: Session,
    project_id: int,
    skip: int = 0,
    limit: int = 100,
) -> list[Script]:
    statement = (
        select(Script)
        .where(Script.project_id == project_id)
        .order_by(Script.created_at.desc(), Script.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def normalize_script(
    data: Any,
    payload: ScriptGenerateRequest,
    topic: Topic,
    platform: str,
) -> ScriptCreate:
    if not isinstance(data, dict):
        data = {}

    raw_rubric = data.get("rubric") or {}
    script_data = {
        "hook": str(data.get("hook") or ""),
        "subtitle_points": ensure_string_list(data.get("subtitle_points")),
        "comment_guidance": str(data.get("comment_guidance") or ""),
        "private_message_guidance": str(data.get("private_message_guidance") or ""),
        "duration": payload.duration,
        "goal": payload.goal,
        "rubric": {
            "er": _ensure_int_score(raw_rubric.get("er")),
            "sr": _ensure_int_score(raw_rubric.get("sr")),
            "hp": _ensure_int_score(raw_rubric.get("hp")),
            "ql": _ensure_int_score(raw_rubric.get("ql")),
            "na": _ensure_int_score(raw_rubric.get("na")),
            "ab": _ensure_int_score(raw_rubric.get("ab")),
            "sat": _ensure_int_score(raw_rubric.get("sat")),
        },
    }
    return ScriptCreate(
        project_id=payload.project_id,
        topic_id=payload.topic_id,
        title=str(data.get("title") or topic.title),
        script_type=payload.script_type,
        platform=platform,
        script_content=str(data.get("script_content") or ""),
        shot_suggestions=ensure_string_list(data.get("shot_suggestions")),
        conversion_script=str(data.get("conversion_script") or ""),
        script_data=script_data,
    )


def ensure_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [item.strip() for item in value.replace("、", "，").split("，") if item.strip()]
    if value is None:
        return []
    return [str(value)]


def _ensure_int_score(value: Any) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return 0
    return min(5, max(0, score))
