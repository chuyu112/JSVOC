from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.llm.llm_gateway import LLMGateway, LLMGatewayRequest


router = APIRouter(prefix="/api/llm", tags=["llm-test"])


class LLMTestGenerateRequest(BaseModel):
    project_id: int | None = None
    module_name: str = Field(default="account_package", min_length=1, max_length=80)
    system_prompt: str = "你是一个短视频账号策略助手，请输出结构化 JSON。"
    user_prompt: str = "请生成一个用于验证 LLM Gateway 的示例结果。"
    output_schema: dict[str, Any] | None = None
    temperature: float = Field(default=0.7, ge=0, le=2)
    metadata: dict[str, Any] = Field(default_factory=dict)
    prompt_version: str | None = "test-v1"


@router.post("/test-generate")
def test_generate(
    payload: LLMTestGenerateRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    gateway = LLMGateway()
    result = gateway.generate(
        db=db,
        project_id=payload.project_id,
        prompt_version=payload.prompt_version,
        request=LLMGatewayRequest(
            module_name=payload.module_name,
            system_prompt=payload.system_prompt,
            user_prompt=payload.user_prompt,
            output_schema=payload.output_schema,
            temperature=payload.temperature,
            metadata=payload.metadata,
        ),
    )

    return {
        "success": result.success,
        "data": result.model_dump(mode="json"),
        "message": "" if result.success else result.error or "LLM Gateway 调用失败",
    }
