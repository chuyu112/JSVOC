from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.llm.llm_gateway import LLMGateway, LLMImageGatewayRequest


router = APIRouter(prefix="/api/images", tags=["images"])


class ImageGenerateRequest(BaseModel):
    project_id: int | None = None
    prompt: str = Field(min_length=1)
    model: str | None = None
    size: str = "1024x1024"
    n: int = Field(default=1, ge=1, le=4)
    response_format: str | None = None


@router.post("/generate")
def generate_image(
    payload: ImageGenerateRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    result = LLMGateway().generate_image(
        db=db,
        project_id=payload.project_id,
        request=LLMImageGatewayRequest(
            prompt=payload.prompt,
            model=payload.model,
            size=payload.size,
            n=payload.n,
            response_format=payload.response_format,
            metadata={"project_id": payload.project_id},
        ),
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result.error or "图片生成失败",
        )

    return {
        "success": True,
        "data": {
            "images": result.data.get("images", []) if isinstance(result.data, dict) else [],
            "generation_record_id": result.generation_record_id,
            "provider": result.provider,
            "model": result.model,
            "usage": result.usage,
            "latency_ms": result.latency_ms,
        },
        "message": "",
    }
