from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.llm.llm_gateway import LLMGateway, LLMGatewayRequest, LLMGatewayResponse
from app.models.hot_copy import HotCopyMaterial, HotCopyRewrite
from app.models.project import Project
from app.prompts.hot_copy_prompt import (
    HOT_COPY_ANALYSIS_MODULE,
    HOT_COPY_ANALYSIS_OUTPUT_SCHEMA,
    HOT_COPY_ANALYSIS_PROMPT_VERSION,
    HOT_COPY_REWRITE_MODULE,
    HOT_COPY_REWRITE_OUTPUT_SCHEMA,
    HOT_COPY_REWRITE_PROMPT_VERSION,
    build_hot_copy_analysis_prompts,
    build_hot_copy_rewrite_prompts,
)
from app.schemas.hot_copy import HotCopyMaterialManualCreate, HotCopyRewriteRequest
from app.services import credit_service, project_service


REDIANBAO_NOT_CONNECTED_MESSAGE = "热点宝数据源暂未接入，请先使用手动输入。"


def list_materials(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 50,
) -> list[HotCopyMaterial]:
    statement = (
        select(HotCopyMaterial)
        .where(HotCopyMaterial.user_id == user_id)
        .order_by(HotCopyMaterial.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def get_material_for_user(
    db: Session,
    material_id: int,
    user_id: int,
) -> HotCopyMaterial | None:
    statement = select(HotCopyMaterial).where(
        HotCopyMaterial.id == material_id,
        HotCopyMaterial.user_id == user_id,
    )
    return db.scalars(statement).first()


def create_manual_material(
    db: Session,
    payload: HotCopyMaterialManualCreate,
    user_id: int,
) -> HotCopyMaterial:
    project_id = validate_project_id(db, payload.project_id, user_id)
    material = HotCopyMaterial(
        user_id=user_id,
        project_id=project_id,
        platform=payload.platform,
        source_type="manual",
        source_url=payload.source_url,
        account_name=payload.account_name,
        account_home_url=payload.account_home_url,
        cover_url=payload.cover_url,
        title=payload.title,
        original_script=payload.original_script,
        metrics_json=payload.metrics_json,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


def analyze_material(
    db: Session,
    material_id: int,
    user_id: int,
) -> tuple[HotCopyMaterial, dict[str, Any], int | None]:
    material = require_material(db, material_id, user_id)
    credit_service.ensure_sufficient_credits(db, user_id, credit_service.TEXT_GENERATION_COST)

    system_prompt, user_prompt = build_hot_copy_analysis_prompts(material)
    result = LLMGateway().generate(
        db=db,
        project_id=material.project_id,
        user_id=user_id,
        prompt_version=HOT_COPY_ANALYSIS_PROMPT_VERSION,
        request=LLMGatewayRequest(
            module_name=HOT_COPY_ANALYSIS_MODULE,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=HOT_COPY_ANALYSIS_OUTPUT_SCHEMA,
            temperature=0.25,
            metadata={
                "material_id": material.id,
                "title": material.title,
                "platform": material.platform,
            },
        ),
    )
    if not result.success:
        raise gateway_error(result)

    analysis = ensure_dict(result.data)
    material.analysis_json = analysis
    db.add(material)
    credit_service.charge_credits(
        db,
        user_id=user_id,
        cost=credit_service.TEXT_GENERATION_COST,
        reason="hot_copy_analysis",
        reference_type="generation_record",
        reference_id=result.generation_record_id,
        metadata={"material_id": material.id},
        commit=False,
    )
    db.commit()
    db.refresh(material)
    return material, analysis, result.generation_record_id


def rewrite_material(
    db: Session,
    material_id: int,
    payload: HotCopyRewriteRequest,
    user_id: int,
) -> tuple[HotCopyRewrite, dict[str, Any], int | None]:
    material = require_material(db, material_id, user_id)
    project = get_optional_project(db, payload.project_id or material.project_id, user_id)
    project_id = project.id if project is not None else None
    credit_service.ensure_sufficient_credits(db, user_id, credit_service.TEXT_GENERATION_COST)

    system_prompt, user_prompt = build_hot_copy_rewrite_prompts(material, project, payload)
    result = LLMGateway().generate(
        db=db,
        project_id=project_id,
        user_id=user_id,
        prompt_version=HOT_COPY_REWRITE_PROMPT_VERSION,
        request=LLMGatewayRequest(
            module_name=HOT_COPY_REWRITE_MODULE,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=HOT_COPY_REWRITE_OUTPUT_SCHEMA,
            temperature=0.35,
            metadata={
                "material_id": material.id,
                "project_id": project_id,
                "rewrite_mode": payload.rewrite_mode,
                "duration": payload.duration,
                "conversion_goal": payload.conversion_goal,
                "product": payload.product or (project.product if project is not None else None),
            },
        ),
    )
    if not result.success:
        raise gateway_error(result)

    output = ensure_dict(result.data)
    rewrite = HotCopyRewrite(
        material_id=material.id,
        user_id=user_id,
        project_id=project_id,
        rewrite_mode=payload.rewrite_mode,
        duration=payload.duration,
        conversion_goal=payload.conversion_goal,
        input_json=payload.model_dump(mode="json"),
        output_json=output,
        generation_record_id=result.generation_record_id,
    )
    db.add(rewrite)
    credit_service.charge_credits(
        db,
        user_id=user_id,
        cost=credit_service.TEXT_GENERATION_COST,
        reason="hot_copy_rewrite",
        reference_type="generation_record",
        reference_id=result.generation_record_id,
        metadata={"material_id": material.id, "project_id": project_id},
        commit=False,
    )
    db.commit()
    db.refresh(rewrite)
    return rewrite, output, result.generation_record_id


def redianbao_reserved_response() -> dict[str, Any]:
    return {
        "connected": False,
        "message": REDIANBAO_NOT_CONNECTED_MESSAGE,
        "items": [],
    }


def validate_project_id(
    db: Session,
    project_id: int | None,
    user_id: int,
) -> int | None:
    project = get_optional_project(db, project_id, user_id)
    return project.id if project is not None else None


def get_optional_project(
    db: Session,
    project_id: int | None,
    user_id: int,
) -> Project | None:
    if project_id is None:
        return None

    project = project_service.get_project_for_user(db, project_id, user_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return project


def require_material(
    db: Session,
    material_id: int,
    user_id: int,
) -> HotCopyMaterial:
    material = get_material_for_user(db, material_id, user_id)
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="爆款素材不存在")
    return material


def gateway_error(result: LLMGatewayResponse) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=result.error or "爆款文案生成失败",
    )


def ensure_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
