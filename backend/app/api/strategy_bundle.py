from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.llm.llm_gateway import LLMGateway, LLMGatewayRequest
from app.models.user import User
from app.prompts.strategy_bundle_prompt import (
    STRATEGY_BUNDLE_MODULE,
    STRATEGY_BUNDLE_OUTPUT_SCHEMA,
    STRATEGY_BUNDLE_PROMPT_VERSION,
    build_strategy_bundle_prompts,
)
from app.schemas.account_strategy_context import (
    AccountStrategyContextCreate,
    AccountStrategyContextRead,
)
from app.schemas.execution_plan import (
    ExecutionPlanGenerateRequest,
    ExecutionPlanGenerateResponse,
)
from app.services import (
    account_strategy_context_service,
    credit_service,
    generation_record_service,
    project_service,
)
from app.services.account_package_normalizer import (
    extract_account_package_extras,
    normalize_account_package,
)
from app.services.execution_plan_service import normalize_execution_plan


router = APIRouter(
    prefix="/api/strategy/account-package-execution-plan",
    tags=["strategy-bundle"],
)


def success_response(data: object, message: str = "") -> dict[str, object]:
    return {"success": True, "data": data, "message": message}


@router.get("/projects/{project_id}/latest")
def get_latest_account_package(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    project = project_service.get_project_for_user(db, project_id, current_user.id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    context = account_strategy_context_service.get_latest_account_strategy_context(db, project_id)
    if context is None:
        return success_response({}, "暂无账号包装数据")

    context_data = context.context_data or {}
    execution_plan = context_data.get("execution_plan") or {}
    extras = context_data.get("account_package_extras") or {}

    return success_response(
        {
            "id": context.id,
            "account_positioning": context.account_positioning,
            "persona": context.persona,
            "target_user_profile": context.target_user_profile,
            "account_names": context.account_names,
            "bios": context.bios,
            "content_columns": context.content_columns,
            "trust_design": context.trust_design,
            "conversion_path": context.conversion_path,
            "platform_strategies": context.platform_strategies,
            "content_style": context.content_style,
            "trust_points": context.trust_points,
            "monetization_paths": context.monetization_paths,
            "execution_stage": context.execution_stage,
            "created_at": context.created_at.isoformat() if context.created_at else None,
            "execution_plan": execution_plan,
            "series_positioning": extras.get("series_positioning"),
            "persona_layers": extras.get("persona_layers"),
            "tone_principles": extras.get("tone_principles"),
            "material_pool": extras.get("material_pool"),
            "publishing_rhythm": extras.get("publishing_rhythm"),
            "content_structure_template": extras.get("content_structure_template"),
            "rubric_notes": context_data.get("rubric_notes"),
        }
    )


@router.post("/generate")
def generate_account_package_and_execution_plan(
    payload: ExecutionPlanGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    project = project_service.get_project_for_user(db, payload.project_id, current_user.id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    old_contexts = account_strategy_context_service.get_project_account_strategy_contexts(db, project.id)
    old_context_ids = [context.id for context in old_contexts]
    old_record_ids = sorted(
        {
            *[
                context.generation_record_id
                for context in old_contexts
                if context.generation_record_id is not None
            ],
            *[
                record.id
                for record in generation_record_service.get_project_generation_records_by_modules(
                    db,
                    project.id,
                    ["strategy_bundle", "account_package", "execution_plan"],
                )
            ],
        }
    )

    system_prompt, user_prompt = build_strategy_bundle_prompts(
        project,
        payload.cycle,
        payload.daily_time,
        benchmark_samples=project.benchmark_samples,
    )
    gateway_result = LLMGateway().generate(
        db=db,
        project_id=project.id,
        user_id=current_user.id,
        prompt_version=STRATEGY_BUNDLE_PROMPT_VERSION,
        request=LLMGatewayRequest(
            module_name=STRATEGY_BUNDLE_MODULE,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=STRATEGY_BUNDLE_OUTPUT_SCHEMA,
            temperature=payload.temperature,
            max_tokens=8000,
            metadata={
                "project_id": project.id,
                "cycle": payload.cycle,
                "daily_time": payload.daily_time,
                "platforms": project.platforms,
                "industry": project.industry,
                "product": project.product,
            },
        ),
    )

    if not gateway_result.success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=gateway_result.error or "账号包装和执行计划生成失败",
        )

    account_package_data, execution_plan_data = split_bundle_data(gateway_result.data)
    package_result = normalize_account_package(account_package_data)
    package_extras = extract_account_package_extras(account_package_data)
    execution_plan = normalize_execution_plan(execution_plan_data, payload.cycle)

    context_data: dict[str, Any] = {
        "project": {
            "project_name": project.project_name,
            "industry": project.industry,
            "sub_industry": project.sub_industry,
            "product": project.product,
            "personal_intro": project.personal_intro,
            "target_audience": project.target_audience,
            "platforms": project.platforms,
            "current_stage": project.current_stage,
        },
        "gateway": {
            "provider": gateway_result.provider,
            "model": gateway_result.model,
            "usage": gateway_result.usage,
            "latency_ms": gateway_result.latency_ms,
            "generation_record_id": gateway_result.generation_record_id,
        },
        "execution_plan": execution_plan.model_dump(mode="json"),
    }
    if package_extras:
        context_data["account_package_extras"] = package_extras
    if package_result.rubric_notes:
        context_data["rubric_notes"] = package_result.rubric_notes

    context = account_strategy_context_service.create_account_strategy_context(
        db,
        AccountStrategyContextCreate(
            project_id=project.id,
            generation_record_id=gateway_result.generation_record_id,
            content_style="真实、专业、可信、接地气",
            trust_points=package_result.trust_design,
            monetization_paths=package_result.conversion_path,
            execution_stage=project.current_stage,
            context_data=context_data,
            **package_result.model_dump(),
        ),
    )

    account_strategy_context_service.delete_account_strategy_contexts_by_ids(db, old_context_ids)
    generation_record_service.delete_generation_records_by_ids(db, old_record_ids)

    response = ExecutionPlanGenerateResponse(
        execution_plan=execution_plan,
        generation_record_id=gateway_result.generation_record_id,
        provider=gateway_result.provider,
        model=gateway_result.model,
        usage=gateway_result.usage,
        latency_ms=gateway_result.latency_ms,
    )
    credit_cost = credit_service.strategy_generation_cost(gateway_result.usage)
    credit_service.charge_credits(
        db,
        user_id=current_user.id,
        cost=credit_cost,
        reason="strategy_bundle_generation",
        reference_type="generation_record",
        reference_id=gateway_result.generation_record_id,
        metadata={
            "module": "strategy_bundle",
            "project_id": project.id,
            "total_tokens": credit_service.token_usage_total(gateway_result.usage),
        },
    )

    return success_response(
        {
            "account_package": package_result.model_dump(mode="json"),
            "execution_plan": response.execution_plan.model_dump(mode="json"),
            "context": AccountStrategyContextRead.model_validate(context).model_dump(mode="json"),
            "generation_record_id": gateway_result.generation_record_id,
            "provider": gateway_result.provider,
            "model": gateway_result.model,
            "usage": gateway_result.usage,
            "latency_ms": gateway_result.latency_ms,
            "rubric_notes": package_result.rubric_notes,
        },
        "账号包装和执行计划生成成功",
    )


def split_bundle_data(data: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(data, dict):
        return {}, {}

    account_package = data.get("account_package")
    execution_plan = data.get("execution_plan")
    return (
        account_package if isinstance(account_package, dict) else {},
        execution_plan if isinstance(execution_plan, dict) else {},
    )
