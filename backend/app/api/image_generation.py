import base64
import logging
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import SessionLocal, get_db
from app.models.user import User
from app.schemas.generation_task import GenerationTaskCreate, GenerationTaskSubmitResponse
from app.schemas.image_generation import (
    GeneratedImage,
    ImageEditRequest,
    ImageGenerateRequest,
    ImageGenerateResponse,
    ImagePromptEnhanceRequest,
    ImagePromptEnhanceResponse,
)
from app.services import (
    credit_service,
    digital_asset_service,
    generation_record_service,
    generation_task_service,
    image_prompt_enhancement_service,
    image_generation_service,
    project_service,
    storage_service,
)


router = APIRouter(tags=["image-generation"])
logger = logging.getLogger(__name__)

MAX_REMOTE_IMAGE_BYTES = 16 * 1024 * 1024


def success_response(data: object, message: str = "") -> dict[str, object]:
    return {"success": True, "data": data, "message": message}


def image_generation_error_message(exc: Exception) -> str:
    if isinstance(exc, ValueError):
        return str(exc)
    if isinstance(exc, httpx.TimeoutException):
        return f"image generation timeout: {exc}"
    if isinstance(exc, httpx.HTTPStatusError):
        response_text = exc.response.text[:500] if exc.response is not None else ""
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        return f"image generation provider failed {status_code}: {response_text}"
    if isinstance(exc, httpx.RequestError):
        return f"image generation provider request failed: {exc}"
    return f"image generation failed: {exc}"


def maybe_create_generation_record_from_task(db: Session, task: Any) -> None:
    try:
        generation_record_service.create_generation_record_from_task(db, task)
    except Exception:  # noqa: BLE001 - history persistence must not change task outcome.
        db.rollback()
        logger.exception("image generation history persistence failed", extra={"task_id": getattr(task, "id", None)})


def extract_generated_image_content(image: GeneratedImage) -> tuple[bytes, str]:
    if image.b64_json:
        return base64.b64decode(image.b64_json), "image/png"
    if image.data_url and image.data_url.startswith("data:") and "," in image.data_url:
        header, encoded = image.data_url.split(",", 1)
        mime_type = header.split(";", 1)[0].replace("data:", "", 1) or "image/png"
        return base64.b64decode(encoded), mime_type
    if image.url:
        if not image.url.lower().startswith(("http://", "https://")):
            raise RuntimeError("generated image url must use http or https scheme")
        with httpx.stream("GET", image.url, timeout=30) as response:
            response.raise_for_status()
            mime_type = response.headers.get("Content-Type", "image/png").split(";", 1)[0].strip() or "image/png"
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > MAX_REMOTE_IMAGE_BYTES:
                    raise RuntimeError(
                        f"generated image exceeds {MAX_REMOTE_IMAGE_BYTES} bytes limit"
                    )
                chunks.append(chunk)
        return b"".join(chunks), mime_type
    raise RuntimeError("generated image payload is missing usable content")


def maybe_persist_generated_images_to_oss(
    db: Session,
    payload: ImageGenerateRequest | ImageEditRequest,
    result: ImageGenerateResponse,
    *,
    user_id: int,
) -> ImageGenerateResponse:
    if not storage_service.is_oss_configured():
        return result

    project = None
    owner_user_id = user_id
    if payload.project_id is not None:
        project = project_service.get_project(db, payload.project_id)
        if project is None or project.user_id is None:
            return result
        owner_user_id = project.user_id

    persisted_images: list[GeneratedImage] = []
    for image in result.images:
        content, mime_type = extract_generated_image_content(image)
        object_key = storage_service.build_generated_image_object_key(
            user_id=owner_user_id,
            project_id=project.id if project is not None else None,
            mime_type=mime_type,
        )
        object_key = storage_service.upload_bytes(
            object_key=object_key,
            content=content,
            content_type=mime_type,
        )
        signed_url, expires_at = storage_service.sign_get_url(object_key)
        asset = digital_asset_service.create_image_asset(
            db,
            user_id=owner_user_id,
            project=project,
            prompt=payload.prompt,
            generation_record_id=None,
            oss_object_key=object_key,
            mime_type=mime_type,
            file_size=len(content),
            asset_metadata={
                "provider": result.provider,
                "model": result.model,
                "quality": payload.quality,
                "size": payload.size,
            },
        )
        persisted_images.append(
            GeneratedImage(
                url=signed_url,
                asset_id=asset.id,
                oss_object_key=object_key,
                mime_type=mime_type,
                signed_url_expires_at=expires_at,
            )
        )

    result.images = persisted_images
    return result


def run_image_generation_task(task_id: int, mode: str, payload_data: dict[str, Any], user_id: int) -> None:
    db = SessionLocal()
    try:
        generation_task_service.mark_generation_task_running(db, task_id)
        payload_model = (
            ImageEditRequest.model_validate(payload_data)
            if mode == "edit"
            else ImageGenerateRequest.model_validate(payload_data)
        )
        if mode == "edit":
            result = image_generation_service.edit_image(payload_model, db=db)
        else:
            result = image_generation_service.generate_image(payload_model, db=db)

        if not result.images:
            raise RuntimeError("image provider returned no usable images")
        result = maybe_persist_generated_images_to_oss(db, payload_model, result, user_id=user_id)
        task = generation_task_service.mark_generation_task_succeeded(db, task_id, result.model_dump(mode="json"))
        if task is not None:
            maybe_create_generation_record_from_task(db, task)
    except Exception as exc:  # noqa: BLE001 - background tasks must persist failures instead of raising.
        db.rollback()
        logger.warning("image generation task failed", extra={"task_id": task_id, "mode": mode, "error": str(exc)})
        try:
            task = generation_task_service.mark_generation_task_failed(db, task_id, image_generation_error_message(exc))
            if task is not None:
                maybe_create_generation_record_from_task(db, task)
            credit_service.refund_generation_task_credits(
                db,
                task_id,
                reason=f"{mode}_image_generation_failed",
            )
        except Exception:  # noqa: BLE001 - swallow secondary failures to avoid leaking sessions.
            db.rollback()
            logger.exception("image generation task failure persistence failed", extra={"task_id": task_id})
    finally:
        db.close()


def submit_image_generation_task(
    db: Session,
    background_tasks: BackgroundTasks,
    *,
    user_id: int,
    task_type: str,
    mode: str,
    payload: ImageGenerateRequest | ImageEditRequest,
) -> dict[str, object]:
    credit_cost = credit_service.image_generation_cost(payload.n, mode=mode)
    credit_service.ensure_sufficient_credits(db, user_id, credit_cost)
    task = generation_task_service.create_generation_task(
        db,
        GenerationTaskCreate(
            task_type=task_type,
            project_id=payload.project_id,
            input_data=payload.model_dump(mode="json"),
        ),
        user_id=user_id,
    )
    transaction = credit_service.charge_credits(
        db,
        user_id=user_id,
        cost=credit_cost,
        reason=f"{mode}_image_generation",
        reference_type="generation_task",
        reference_id=task.id,
        metadata={"task_type": task_type, "mode": mode, "image_count": payload.n},
    )
    task = generation_task_service.attach_credit_charge(
        db,
        task.id,
        credit_cost=credit_cost,
        credit_transaction_id=transaction.id if transaction else None,
    ) or task
    background_tasks.add_task(run_image_generation_task, task.id, mode, task.input_data, user_id)
    data = GenerationTaskSubmitResponse(
        task_id=task.id,
        task_type=task.task_type,
        status=task.status,
        credit_cost=credit_cost,
    )
    return success_response(data.model_dump(mode="json"), "image task queued")


@router.post("/api/creation/images/generate")
def generate_image_api(
    payload: ImageGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    if payload.project_id is not None:
        project = project_service.get_project_for_user(db, payload.project_id, current_user.id)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    credit_cost = credit_service.image_generation_cost(payload.n, mode="generate")
    credit_service.ensure_sufficient_credits(db, current_user.id, credit_cost)
    try:
        result = image_generation_service.generate_image(payload, db=db)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"图片生成超时: {exc}",
        ) from exc
    except httpx.HTTPStatusError as exc:
        response_text = exc.response.text[:500] if exc.response is not None else ""
        upstream_status = exc.response.status_code if exc.response is not None else "unknown"
        logger.warning(
            "image generation upstream status error",
            extra={
                "endpoint": str(exc.request.url) if exc.request is not None else "",
                "status_code": upstream_status,
                "response_prefix": response_text,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"图片生成渠道失败 {upstream_status}: {response_text}",
        ) from exc
    except httpx.RequestError as exc:
        logger.warning(
            "image generation upstream request failed",
            extra={"endpoint": str(exc.request.url) if exc.request is not None else "", "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"图片生成渠道请求失败: {exc}",
        ) from exc

    if not result.images:
        logger.warning("image generation upstream returned no usable images")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="图片生成渠道未返回可用图片",
        )
    result = maybe_persist_generated_images_to_oss(db, payload, result, user_id=current_user.id)
    credit_service.charge_credits(
        db,
        user_id=current_user.id,
        cost=credit_cost,
        reason="generate_image",
        reference_type="image_generation",
        metadata={"mode": "generate", "image_count": payload.n, "provider": result.provider, "model": result.model},
    )
    return success_response(result.model_dump(mode="json"), "图片生成成功")


@router.post("/api/creation/images/generate/async")
def generate_image_async_api(
    payload: ImageGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    if payload.project_id is not None:
        project = project_service.get_project_for_user(db, payload.project_id, current_user.id)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return submit_image_generation_task(
        db,
        background_tasks,
        user_id=current_user.id,
        task_type="image_generate",
        mode="generate",
        payload=payload,
    )


@router.post("/api/creation/images/edit")
def edit_image_api(
    payload: ImageEditRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    if payload.project_id is not None:
        project = project_service.get_project_for_user(db, payload.project_id, current_user.id)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    credit_cost = credit_service.image_generation_cost(payload.n, mode="edit")
    credit_service.ensure_sufficient_credits(db, current_user.id, credit_cost)
    try:
        result = image_generation_service.edit_image(payload, db=db)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"图片编辑超时: {exc}",
        ) from exc
    except httpx.HTTPStatusError as exc:
        response_text = exc.response.text[:500] if exc.response is not None else ""
        upstream_status = exc.response.status_code if exc.response is not None else "unknown"
        logger.warning(
            "image edit upstream status error",
            extra={
                "endpoint": str(exc.request.url) if exc.request is not None else "",
                "status_code": upstream_status,
                "response_prefix": response_text,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"图生图渠道失败 {upstream_status}: {response_text}",
        ) from exc
    except httpx.RequestError as exc:
        logger.warning(
            "image edit upstream request failed",
            extra={"endpoint": str(exc.request.url) if exc.request is not None else "", "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"图生图渠道请求失败: {exc}",
        ) from exc

    if not result.images:
        logger.warning("image edit upstream returned no usable images")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="图生图渠道未返回可用图片",
        )
    result = maybe_persist_generated_images_to_oss(db, payload, result, user_id=current_user.id)
    credit_service.charge_credits(
        db,
        user_id=current_user.id,
        cost=credit_cost,
        reason="edit_image",
        reference_type="image_generation",
        metadata={"mode": "edit", "image_count": payload.n, "provider": result.provider, "model": result.model},
    )
    return success_response(result.model_dump(mode="json"), "图片生成成功")


@router.post("/api/creation/images/edit/async")
def edit_image_async_api(
    payload: ImageEditRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    if payload.project_id is not None:
        project = project_service.get_project_for_user(db, payload.project_id, current_user.id)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return submit_image_generation_task(
        db,
        background_tasks,
        user_id=current_user.id,
        task_type="image_edit",
        mode="edit",
        payload=payload,
    )


@router.post("/api/creation/images/enhance-prompt")
def enhance_image_prompt_api(
    payload: ImagePromptEnhanceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    project = None
    if payload.project_id is not None:
        project = project_service.get_project_for_user(db, payload.project_id, current_user.id)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    try:
        result = image_prompt_enhancement_service.enhance_image_prompt(
            db,
            payload=payload,
            project=project,
            user_id=current_user.id,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return success_response(ImagePromptEnhanceResponse.model_validate(result).model_dump(mode="json"), "提示词优化成功")
