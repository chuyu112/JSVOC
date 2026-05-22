from typing import Any

from sqlalchemy.orm import Session

from app.llm.llm_gateway import LLMGateway, LLMGatewayRequest, LLMGatewayResponse
from app.prompts.execution_plan_prompt import (
    EXECUTION_PLAN_MODULE,
    EXECUTION_PLAN_OUTPUT_SCHEMA,
    EXECUTION_PLAN_PROMPT_VERSION,
    build_execution_plan_prompts,
)
from app.schemas.execution_plan import ExecutionPlanGenerateRequest, ExecutionPlanResult
from app.services import account_strategy_context_service, project_service


class ExecutionPlanGeneration:
    def __init__(self, result: ExecutionPlanResult, gateway_result: LLMGatewayResponse):
        self.result = result
        self.gateway_result = gateway_result


def generate_execution_plan(
    db: Session,
    payload: ExecutionPlanGenerateRequest,
) -> ExecutionPlanGeneration | None:
    project = project_service.get_project(db, payload.project_id)
    if project is None:
        return None

    strategy_context = account_strategy_context_service.get_latest_account_strategy_context(
        db,
        payload.project_id,
    )
    system_prompt, user_prompt = build_execution_plan_prompts(
        project,
        strategy_context,
        payload.cycle,
        payload.daily_time,
    )
    gateway_result = LLMGateway().generate(
        db=db,
        project_id=project.id,
        prompt_version=EXECUTION_PLAN_PROMPT_VERSION,
        request=LLMGatewayRequest(
            module_name=EXECUTION_PLAN_MODULE,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=EXECUTION_PLAN_OUTPUT_SCHEMA,
            temperature=payload.temperature,
            metadata={
                "project_id": project.id,
                "cycle": payload.cycle,
                "daily_time": payload.daily_time,
                "platforms": project.platforms,
                "industry": project.industry,
                "product": project.product,
                "account_strategy_context_id": strategy_context.id if strategy_context else None,
            },
        ),
    )
    if not gateway_result.success:
        return ExecutionPlanGeneration(
            result=ExecutionPlanResult(cycle=payload.cycle, weekly_plan=[], daily_plan=[]),
            gateway_result=gateway_result,
        )

    return ExecutionPlanGeneration(
        result=normalize_execution_plan(gateway_result.data, payload.cycle),
        gateway_result=gateway_result,
    )


def normalize_execution_plan(data: Any, fallback_cycle: str) -> ExecutionPlanResult:
    if not isinstance(data, dict):
        data = {}

    weekly_plan = []
    for index, item in enumerate(ensure_list(data.get("weekly_plan")), start=1):
        if not isinstance(item, dict):
            item = {"goal": str(item)}
        weekly_plan.append(
            {
                "week": ensure_int(item.get("week"), index),
                "goal": str(item.get("goal") or item.get("weekly_goal") or ""),
                "focus": str(item.get("focus") or item.get("content_direction") or ""),
                "key_tasks": ensure_string_list(item.get("key_tasks") or item.get("tasks")),
            }
        )

    daily_plan = []
    for index, item in enumerate(ensure_list(data.get("daily_plan")), start=1):
        if not isinstance(item, dict):
            item = {"task": str(item)}
        daily_plan.append(
            {
                "day": ensure_int(item.get("day"), index),
                "task": str(item.get("task") or item.get("daily_task") or ""),
                "topic": str(item.get("topic") or item.get("content_direction") or ""),
                "shooting_task": str(
                    item.get("shooting_task") or item.get("shooting_suggestion") or ""
                ),
                "review_metrics": ensure_string_list(
                    item.get("review_metrics") or item.get("review_metric")
                ),
            }
        )

    normalized = {
        "cycle": str(data.get("cycle") or fallback_cycle),
        "weekly_plan": weekly_plan,
        "daily_plan": daily_plan,
        "notes": ensure_string_list(data.get("notes")),
    }
    return ExecutionPlanResult.model_validate(normalized)


def ensure_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def ensure_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [item.strip() for item in value.replace("、", "，").split("，") if item.strip()]
    if value is None:
        return []
    return [str(value)]


def ensure_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback
