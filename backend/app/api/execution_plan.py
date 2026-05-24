from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.execution_plan import (
    ExecutionPlanGenerateRequest,
    ExecutionPlanGenerateResponse,
)
from app.services.execution_plan_service import generate_execution_plan


router = APIRouter(prefix="/api/strategy/execution-plan", tags=["execution-plan"])


def success_response(data: object, message: str = "") -> dict[str, object]:
    return {"success": True, "data": data, "message": message}


@router.post("/generate")
def generate_execution_plan_api(
    payload: ExecutionPlanGenerateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    generation = generate_execution_plan(db, payload)
    if generation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    gateway_result = generation.gateway_result
    if not gateway_result.success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=gateway_result.error or "执行计划生成失败",
        )

    response = ExecutionPlanGenerateResponse(
        execution_plan=generation.result,
        generation_record_id=gateway_result.generation_record_id,
        provider=gateway_result.provider,
        model=gateway_result.model,
        usage=gateway_result.usage,
        latency_ms=gateway_result.latency_ms,
    )
    return success_response(response.model_dump(mode="json"), "执行计划生成成功")
