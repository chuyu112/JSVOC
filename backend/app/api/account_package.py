import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.llm.llm_gateway import LLMGateway, LLMGatewayRequest
from app.prompts.account_package_prompt import (
    ACCOUNT_PACKAGE_MODULE,
    ACCOUNT_PACKAGE_OUTPUT_SCHEMA,
    ACCOUNT_PACKAGE_PROMPT_VERSION,
    build_account_package_prompts,
)
from app.schemas.account_strategy_context import (
    AccountPackageGenerateRequest,
    AccountPackageResult,
    AccountStrategyContextCreate,
    AccountStrategyContextRead,
)
from app.services import account_strategy_context_service, project_service


router = APIRouter(prefix="/api/strategy/account-package", tags=["account-package"])


def success_response(data: object, message: str = "") -> dict[str, object]:
    return {"success": True, "data": data, "message": message}


@router.post("/generate")
def generate_account_package(
    payload: AccountPackageGenerateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    project = project_service.get_project(db, payload.project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    system_prompt, user_prompt = build_account_package_prompts(project)
    gateway_result = LLMGateway().generate(
        db=db,
        project_id=project.id,
        prompt_version=ACCOUNT_PACKAGE_PROMPT_VERSION,
        request=LLMGatewayRequest(
            module_name=ACCOUNT_PACKAGE_MODULE,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=ACCOUNT_PACKAGE_OUTPUT_SCHEMA,
            temperature=payload.temperature,
            metadata={
                "project_id": project.id,
                "platforms": project.platforms,
                "industry": project.industry,
                "product": project.product,
            },
        ),
    )

    if not gateway_result.success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=gateway_result.error or "账号包装生成失败",
        )

    package_result = normalize_account_package(gateway_result.data)
    context = account_strategy_context_service.create_account_strategy_context(
        db,
        AccountStrategyContextCreate(
            project_id=project.id,
            generation_record_id=gateway_result.generation_record_id,
            content_style="真实、专业、可信、接地气",
            trust_points=package_result.trust_design,
            monetization_paths=package_result.conversion_path,
            execution_stage=project.current_stage,
            context_data={
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
            },
            **package_result.model_dump(),
        ),
    )

    return success_response(
        {
            "account_package": package_result.model_dump(mode="json"),
            "context": AccountStrategyContextRead.model_validate(context).model_dump(mode="json"),
            "generation_record_id": gateway_result.generation_record_id,
            "provider": gateway_result.provider,
            "model": gateway_result.model,
            "usage": gateway_result.usage,
            "latency_ms": gateway_result.latency_ms,
        },
        "账号包装方案生成成功",
    )


def normalize_account_package(data: Any) -> AccountPackageResult:
    if not isinstance(data, dict):
        data = {}

    normalized = {
        "account_positioning": ensure_string(data.get("account_positioning")),
        "persona": ensure_string(data.get("persona")),
        "target_user_profile": data.get("target_user_profile") or {},
        "account_names": ensure_string_list(data.get("account_names")),
        "bios": ensure_string_dict(data.get("bios")),
        "content_columns": ensure_string_list(data.get("content_columns")),
        "trust_design": ensure_string_list(data.get("trust_design")),
        "conversion_path": ensure_string_list(data.get("conversion_path")),
        "platform_strategies": ensure_dict(data.get("platform_strategies")),
    }
    return AccountPackageResult.model_validate(normalized)


def ensure_string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def ensure_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def ensure_string_dict(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        return {str(key): str(item) for key, item in value.items()}
    return {}


def ensure_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}
