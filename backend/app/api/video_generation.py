import base64
import binascii
import json
import logging
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import SessionLocal, get_db
from app.models.generation_task import GenerationTask
from app.models.user import User
from app.schemas.generation_task import GenerationTaskCreate, GenerationTaskRead, GenerationTaskSubmitResponse
from app.services import (
    credit_service,
    digital_asset_service,
    generation_record_service,
    generation_task_service,
    project_service,
    storage_service,
    video_generation_service,
)
from app.services.video_model_catalog import (
    resolve_video_model_endpoint,
    video_model_availability,
    video_model_catalog,
)


router = APIRouter(tags=["video-generation"])
logger = logging.getLogger(__name__)

MAX_REMOTE_VIDEO_BYTES = 256 * 1024 * 1024
MAX_INLINE_REFERENCE_MEDIA_BYTES = 64 * 1024 * 1024
REFERENCE_MEDIA_MIME_PREFIXES = {
    "image": "image/",
    "video": "video/",
    "audio": "audio/",
}
REFERENCE_MEDIA_FOLDERS = {
    "image": "images",
    "video": "videos",
    "audio": "audios",
}
REFERENCE_MEDIA_DEFAULT_MIMES = {
    "image": "image/png",
    "video": "video/mp4",
    "audio": "audio/mpeg",
}


def success_response(data: object, message: str = "") -> dict[str, object]:
    return {"success": True, "data": data, "message": message}


def video_generation_provider_error_message(response_text: str) -> str | None:
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError:
        payload = None

    error_payload = payload.get('error') if isinstance(payload, dict) else None
    error_code = str(error_payload.get('code') or '') if isinstance(error_payload, dict) else ''
    error_message = str(error_payload.get('message') or '') if isinstance(error_payload, dict) else response_text
    combined = f'{error_code} {error_message} {response_text}'.lower()

    if (
        error_code == 'InputImageSensitiveContentDetected.PrivacyInformation'
        or 'inputimagesensitivecontentdetected.privacyinformation' in combined
        or 'input image may contain real person' in combined
    ):
        return (
            '参考图未通过火山审核：输入参考图疑似包含真实人物或隐私信息。'
            '任务已停止，积分已自动退回。请更换无真实人物、无隐私信息的参考图，'
            '或先用生图生成非真人分镜图后再生视频。'
        )

    if 'copyright restrictions' in combined or 'copyright' in error_code.lower():
        return (
            '输出视频未通过火山审核：可能涉及版权限制。任务已停止，积分已自动退回。'
            '请换用更通用的描述，避免品牌、明星或受版权保护的画面。'
        )

    return None

def video_generation_error_message(exc: Exception) -> str:
    if isinstance(exc, ValueError):
        return str(exc)
    if isinstance(exc, httpx.TimeoutException):
        return f"video generation timeout: {exc}"
    if isinstance(exc, httpx.HTTPStatusError):
        response_text = exc.response.text[:500] if exc.response is not None else ""
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        provider_message = video_generation_provider_error_message(response_text)
        if provider_message:
            return provider_message
        return f"video generation provider failed {status_code}: {response_text}"
    if isinstance(exc, httpx.RequestError):
        return f"video generation provider request failed: {exc}"
    return f"video generation failed: {exc}"


def maybe_create_generation_record_from_task(db: Session, task: GenerationTask) -> None:
    try:
        generation_record_service.create_generation_record_from_task(db, task)
    except Exception:  # noqa: BLE001 - history persistence must not change task outcome.
        db.rollback()
        logger.exception("video generation history persistence failed", extra={"task_id": task.id})


def extract_video_content(video_url: str) -> tuple[bytes, str]:
    if not video_url.lower().startswith(("http://", "https://")):
        raise RuntimeError("generated video url must use http or https scheme")
    with httpx.stream("GET", video_url, timeout=60) as response:
        response.raise_for_status()
        mime_type = (
            response.headers.get("Content-Type", "video/mp4").split(";", 1)[0].strip()
            or "video/mp4"
        )
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_bytes():
            total += len(chunk)
            if total > MAX_REMOTE_VIDEO_BYTES:
                raise RuntimeError(
                    f"generated video exceeds {MAX_REMOTE_VIDEO_BYTES} bytes limit"
                )
            chunks.append(chunk)
    return b"".join(chunks), mime_type


def is_http_url(value: str) -> bool:
    return value.lower().startswith(("http://", "https://"))


def decode_inline_reference_media(value: str, media_kind: str) -> tuple[bytes, str]:
    if not value.startswith("data:") or "," not in value:
        raise ValueError("reference media must be an http(s) URL or base64 data URL")

    header, encoded = value.split(",", 1)
    header_lower = header.lower()
    if ";base64" not in header_lower:
        raise ValueError("reference media data URL must be base64 encoded")

    mime_type = header[5:].split(";", 1)[0].strip().lower()
    mime_type = mime_type or REFERENCE_MEDIA_DEFAULT_MIMES[media_kind]
    expected_prefix = REFERENCE_MEDIA_MIME_PREFIXES[media_kind]
    if not mime_type.startswith(expected_prefix):
        raise ValueError(f"{media_kind} reference media must use {expected_prefix} MIME type")

    try:
        content = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("reference media data URL is not valid base64") from exc

    if len(content) > MAX_INLINE_REFERENCE_MEDIA_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="reference media is too large; please upload a smaller file",
        )
    return content, mime_type


def prepare_reference_media_url(
    *,
    value: str | None,
    media_kind: str,
    user_id: int,
    project_id: int | None,
) -> str | None:
    if not value:
        return None

    cleaned = value.strip()
    if is_http_url(cleaned):
        return cleaned

    try:
        content, mime_type = decode_inline_reference_media(cleaned, media_kind)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not storage_service.is_oss_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OSS is required before using uploaded reference media for video generation",
        )

    object_key = storage_service.build_reference_media_object_key(
        user_id=user_id,
        project_id=project_id,
        media_kind=REFERENCE_MEDIA_FOLDERS[media_kind],
        mime_type=mime_type,
    )
    object_key = storage_service.upload_bytes(
        object_key=object_key,
        content=content,
        content_type=mime_type,
    )
    signed_url, _ = storage_service.sign_get_url(object_key)
    return signed_url


def prepare_reference_media_urls(
    *,
    values: list[str] | None,
    media_kind: str,
    user_id: int,
    project_id: int | None,
) -> list[str]:
    prepared: list[str] = []
    for value in values or []:
        url = prepare_reference_media_url(
            value=value,
            media_kind=media_kind,
            user_id=user_id,
            project_id=project_id,
        )
        if url:
            prepared.append(url)
    return prepared


def prepare_video_payload_reference_media(
    payload: "VideoGenerateRequest",
    *,
    user_id: int,
) -> None:
    payload.first_frame = prepare_reference_media_url(
        value=payload.first_frame,
        media_kind="image",
        user_id=user_id,
        project_id=payload.project_id,
    )
    payload.last_frame = prepare_reference_media_url(
        value=payload.last_frame,
        media_kind="image",
        user_id=user_id,
        project_id=payload.project_id,
    )
    payload.reference_media = prepare_reference_media_url(
        value=payload.reference_media,
        media_kind="image",
        user_id=user_id,
        project_id=payload.project_id,
    )
    payload.reference_medias = prepare_reference_media_urls(
        values=payload.reference_medias,
        media_kind="image",
        user_id=user_id,
        project_id=payload.project_id,
    )
    payload.reference_images = prepare_reference_media_urls(
        values=payload.reference_images,
        media_kind="image",
        user_id=user_id,
        project_id=payload.project_id,
    )
    payload.reference_videos = prepare_reference_media_urls(
        values=payload.reference_videos,
        media_kind="video",
        user_id=user_id,
        project_id=payload.project_id,
    )
    payload.reference_audios = prepare_reference_media_urls(
        values=payload.reference_audios,
        media_kind="audio",
        user_id=user_id,
        project_id=payload.project_id,
    )


def maybe_persist_video_to_oss(
    db: Session,
    project_id: int | None,
    result: dict[str, Any],
    options: dict[str, Any] | None = None,
    *,
    user_id: int,
) -> dict[str, Any]:
    project = None
    owner_user_id = user_id
    if project_id is not None:
        project = project_service.get_project(db, project_id)
        if project is None or project.user_id is None:
            return result
        owner_user_id = project.user_id

    video_url = result.get("video_url")
    if not video_url:
        return result

    if not storage_service.is_oss_configured():
        return create_remote_video_asset(
            db,
            project,
            result,
            options,
            user_id=owner_user_id,
            reason="oss_not_configured",
        )

    try:
        content, mime_type = extract_video_content(video_url)
        object_key = storage_service.build_generated_video_object_key(
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
        asset_metadata = {
            "provider": result.get("provider"),
            "model": result.get("model"),
            "task_id": result.get("task_id"),
        }
        if options:
            if options.get("resolution"):
                asset_metadata["resolution"] = options["resolution"]
            if options.get("ratio"):
                asset_metadata["ratio"] = options["ratio"]
            if options.get("duration_mode"):
                asset_metadata["duration_mode"] = options["duration_mode"]
            if options.get("duration_seconds"):
                asset_metadata["duration_seconds"] = options["duration_seconds"]
        asset = digital_asset_service.create_image_asset(
            db,
            user_id=owner_user_id,
            project=project,
            prompt=result.get("prompt", ""),
            generation_record_id=None,
            oss_object_key=object_key,
            mime_type=mime_type,
            file_size=len(content),
            asset_metadata=asset_metadata,
            asset_type="video",
            access_url=signed_url,
            access_url_expires_at=expires_at,
        )
        result["video_url"] = signed_url
        result["asset_id"] = asset.id
        result["oss_object_key"] = object_key
        result["signed_url_expires_at"] = expires_at
    except Exception as exc:  # noqa: BLE001
        logger.warning("failed to persist video to OSS", extra={"project_id": project_id, "error": str(exc)})
        result = create_remote_video_asset(
            db,
            project,
            result,
            options,
            user_id=owner_user_id,
            reason="oss_persist_failed",
        )

    return result


def create_remote_video_asset(
    db: Session,
    project: object | None,
    result: dict[str, Any],
    options: dict[str, Any] | None = None,
    *,
    user_id: int,
    reason: str,
) -> dict[str, Any]:
    video_url = result.get("video_url")
    if not video_url:
        return result

    asset_metadata = build_video_asset_metadata(result, options)
    asset_metadata["storage_status"] = reason
    asset = digital_asset_service.create_image_asset(
        db,
        user_id=user_id,
        project=project,
        prompt=result.get("prompt", ""),
        generation_record_id=None,
        oss_object_key=None,
        mime_type="video/mp4",
        file_size=None,
        asset_metadata=asset_metadata,
        asset_type="video",
        access_url=str(video_url),
        access_url_expires_at=None,
    )
    result["asset_id"] = asset.id
    result["storage_status"] = reason
    return result


def build_video_asset_metadata(
    result: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> dict[str, object]:
    asset_metadata: dict[str, object] = {
        "provider": result.get("provider"),
        "model": result.get("model"),
        "task_id": result.get("task_id"),
    }
    if options:
        if options.get("resolution"):
            asset_metadata["resolution"] = options["resolution"]
        if options.get("ratio"):
            asset_metadata["ratio"] = options["ratio"]
        if options.get("duration_mode"):
            asset_metadata["duration_mode"] = options["duration_mode"]
        if options.get("duration_seconds"):
            asset_metadata["duration_seconds"] = options["duration_seconds"]
    return asset_metadata


def run_video_generation_task(
    task_id: int,
    prompt: str,
    project_id: int | None,
    user_id: int,
    options: dict[str, Any] | None,
    first_frame: str | None = None,
    last_frame: str | None = None,
    reference_media: str | None = None,
    reference_medias: list[str] | None = None,
    reference_images: list[str] | None = None,
    reference_videos: list[str] | None = None,
    reference_audios: list[str] | None = None,
) -> None:
    db = SessionLocal()
    try:
        generation_task_service.mark_generation_task_running(db, task_id)

        def persist_provider_task(provider_task: dict[str, Any]) -> None:
            generation_task_service.update_generation_task_result_data(db, task_id, provider_task)

        result = video_generation_service.generate_video(
            prompt,
            options,
            first_frame=first_frame,
            last_frame=last_frame,
            reference_media=reference_media,
            reference_medias=reference_medias,
            reference_images=reference_images,
            reference_videos=reference_videos,
            reference_audios=reference_audios,
            on_provider_task_created=persist_provider_task,
            db=db,
        )
        result.setdefault("prompt", prompt)
        if not result.get("video_url"):
            raise RuntimeError("video provider returned no usable video")
        result = maybe_persist_video_to_oss(db, project_id, result, options, user_id=user_id)
        task = generation_task_service.mark_generation_task_succeeded(db, task_id, result)
        if task is not None:
            maybe_create_generation_record_from_task(db, task)
    except Exception as exc:  # noqa: BLE001 - background tasks must persist failures instead of raising.
        db.rollback()
        logger.warning("video generation task failed", extra={"task_id": task_id, "error": str(exc)})
        try:
            task = generation_task_service.mark_generation_task_failed(db, task_id, video_generation_error_message(exc))
            if task is not None:
                maybe_create_generation_record_from_task(db, task)
            credit_service.refund_generation_task_credits(
                db,
                task_id,
                reason="video_generation_failed",
            )
        except Exception:  # noqa: BLE001 - swallow secondary failures to avoid leaking sessions.
            db.rollback()
            logger.exception("video generation task failure persistence failed", extra={"task_id": task_id})
    finally:
        db.close()


def recover_interrupted_video_generation_tasks() -> int:
    db = SessionLocal()
    recovered = 0
    try:
        tasks = db.scalars(
            select(GenerationTask).where(
                GenerationTask.task_type == "video_generate",
                GenerationTask.status == "running",
                GenerationTask.result_data.is_not(None),
            )
        ).all()
        for task in tasks:
            result_data = task.result_data if isinstance(task.result_data, dict) else {}
            provider_task_id = result_data.get("task_id")
            if not provider_task_id:
                continue

            try:
                provider_result = video_generation_service.get_video_task_result(str(provider_task_id), db=db)
                status_value = str(provider_result.get("status") or "").lower()
                merged_result = {
                    **result_data,
                    **provider_result,
                    "provider": result_data.get("provider") or "seedance",
                    "model": result_data.get("model"),
                    "task_id": provider_task_id,
                }
                input_data = task.input_data if isinstance(task.input_data, dict) else {}
                prompt = input_data.get("prompt") or merged_result.get("prompt") or ""
                options = input_data.get("options") if isinstance(input_data.get("options"), dict) else {}
                merged_result["prompt"] = prompt

                if status_value in ("succeeded", "completed", "success"):
                    if not merged_result.get("video_url"):
                        raise RuntimeError("video provider returned no usable video")
                    merged_result = maybe_persist_video_to_oss(
                        db,
                        task.project_id,
                        merged_result,
                        options,
                        user_id=task.user_id,
                    )
                    updated_task = generation_task_service.mark_generation_task_succeeded(db, task.id, merged_result)
                    if updated_task is not None:
                        maybe_create_generation_record_from_task(db, updated_task)
                    recovered += 1
                elif status_value in ("failed", "error", "cancelled"):
                    updated_task = generation_task_service.mark_generation_task_failed(
                        db,
                        task.id,
                        str(provider_result.get("error_message") or "video provider task failed"),
                    )
                    if updated_task is not None:
                        maybe_create_generation_record_from_task(db, updated_task)
                    credit_service.refund_generation_task_credits(
                        db,
                        task.id,
                        reason="video_generation_failed",
                    )
                    recovered += 1
                else:
                    generation_task_service.update_generation_task_result_data(db, task.id, merged_result)
            except Exception as exc:  # noqa: BLE001 - recovery should not block application startup.
                db.rollback()
                logger.warning("video generation task recovery failed", extra={"task_id": task.id, "error": str(exc)})
        return recovered
    finally:
        db.close()


class VideoGenerateRequest(BaseModel):
    project_id: int | None = Field(default=None, ge=1)
    prompt: str = Field(min_length=1, max_length=4000)
    options: dict[str, Any] = Field(default_factory=dict)
    first_frame: str | None = Field(default=None, max_length=10_000_000)
    last_frame: str | None = Field(default=None, max_length=10_000_000)
    reference_media: str | None = Field(default=None, max_length=50_000_000)
    reference_medias: list[str] = Field(default_factory=list)
    reference_images: list[str] = Field(default_factory=list)
    reference_videos: list[str] = Field(default_factory=list)
    reference_audios: list[str] = Field(default_factory=list)


class VideoModelRead(BaseModel):
    key: str
    label: str
    value: str
    kind: str
    resolutions: list[str]
    pricing_yuan_per_second: dict[str, float]
    available: bool
    disabled_reason: str | None = None


@router.get("/api/creation/videos/models")
def list_video_models_api(
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    del current_user
    models = [
        VideoModelRead(
            key=spec.key,
            label=spec.label,
            value=spec.value,
            kind=spec.kind,
            resolutions=list(spec.resolutions),
            pricing_yuan_per_second=spec.pricing_yuan_per_second,
            available=spec.available,
            disabled_reason=spec.disabled_reason,
        ).model_dump(mode="json")
        for spec in video_model_catalog()
    ]
    return success_response(models)


@router.post("/api/creation/videos/generate/async")
def generate_video_async_api(
    payload: VideoGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    if payload.project_id is not None:
        project = project_service.get_project_for_user(db, payload.project_id, current_user.id)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    payload.options = normalize_video_options(payload.options)
    validate_video_model_access(payload.options)
    prepare_video_payload_reference_media(payload, user_id=current_user.id)

    try:
        credit_cost = credit_service.video_generation_cost(payload.options)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    credit_service.ensure_sufficient_credits(db, current_user.id, credit_cost)
    task = generation_task_service.create_generation_task(
        db,
        GenerationTaskCreate(
            task_type="video_generate",
            project_id=payload.project_id,
            input_data=payload.model_dump(mode="json"),
        ),
        user_id=current_user.id,
    )
    transaction = credit_service.charge_credits(
        db,
        user_id=current_user.id,
        cost=credit_cost,
        reason="video_generation",
        reference_type="generation_task",
        reference_id=task.id,
        metadata={"options": payload.options},
    )
    task = generation_task_service.attach_credit_charge(
        db,
        task.id,
        credit_cost=credit_cost,
        credit_transaction_id=transaction.id if transaction else None,
    ) or task
    background_tasks.add_task(
        run_video_generation_task,
        task.id,
        payload.prompt,
        payload.project_id,
        current_user.id,
        payload.options,
        payload.first_frame,
        payload.last_frame,
        payload.reference_media,
        payload.reference_medias,
        payload.reference_images,
        payload.reference_videos,
        payload.reference_audios,
    )
    data = GenerationTaskSubmitResponse(
        task_id=task.id,
        task_type=task.task_type,
        status=task.status,
        credit_cost=credit_cost,
    )
    return success_response(data.model_dump(mode="json"), "video task queued")


def validate_video_model_access(options: dict[str, Any]) -> None:
    model = str((options or {}).get("model") or "").strip()
    available, disabled_reason = video_model_availability(model)
    if not available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=disabled_reason or "video model is not enabled",
        )


def normalize_video_options(options: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(options or {})
    normalized["model"] = resolve_video_model_endpoint(str(normalized.get("model") or ""))
    selected = next(
        (spec for spec in video_model_catalog() if normalized["model"] in {spec.key, spec.value}),
        None,
    )
    if selected and normalized.get("resolution") not in selected.resolutions:
        normalized["resolution"] = selected.resolutions[0]
    return normalized


_SEEDANCE_SYSTEM_PROMPT = """You are a Seedance Video Director specialized in luxury jewelry cinematography.

Follow this 6-step director formula:
[Subject], [Action], in [Environment], camera [Camera Movement], style [Style], avoid [Constraints]

Rules:
- ONE camera move only. Never combine zoom, pan, orbit in one shot.
- Separate camera direction from subject action.
- Use specific cinematography terms: dolly, pan, tilt, tracking, push-in, static.
- Cut filler adjectives like "beautiful" or "amazing". Every word must direct the model.
- Keep prompts 60-100 words. Hard ceiling 120 words.
- For Image-to-Video: describe ONLY motion, camera, lighting shifts, and mood. Add "preserve composition and colors".
- Use positive constraints ("avoid jitter") not traditional negative prompting syntax.
- Use degree adverbs to control intensity: slowly, gently, subtly.
- Pacing words matter: slow, smooth, stable calm jitter. Avoid "fast" unless necessary.

Jewelry material keywords (inject if the user mentions the material):
- Jade: translucent emerald green, warm inner glow, smooth polish, Eastern elegance | avoid plastic shine, synthetic dye, neon green
- Diamond: brilliant fire and scintillation, crisp facets, pure clarity, rainbow dispersion | avoid cloudy milky, yellow tint, dull surface
- Gold: warm buttery luster, rich amber reflection, polished finish | avoid brassy cheap look, coppery red tint
- Pearl: soft iridescent luster, orient glow, smooth skin, creamy white | avoid chalky dull, plastic bead, yellowed aged

Output ONLY the enhanced prompt as a single paragraph. No markdown, no code blocks, no explanations."""


class EnhancePromptRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    material_hint: str | None = Field(default=None, max_length=80)


class EnhancePromptResponse(BaseModel):
    enhanced_prompt: str


@router.post("/api/creation/videos/enhance-prompt")
def enhance_prompt_api(
    payload: EnhancePromptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    from app.llm.llm_gateway import LLMGateway, LLMGatewayRequest

    user_prompt = f"Enhance this video generation prompt for Seedance:\n\n{payload.prompt}"
    if payload.material_hint:
        user_prompt += f"\n\nMaterial focus: {payload.material_hint}"

    gateway = LLMGateway()
    result = gateway.generate(
        db=db,
        user_id=current_user.id,
        request=LLMGatewayRequest(
            module_name="seedance_prompt_enhance",
            system_prompt=_SEEDANCE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.5,
            max_tokens=800,
            metadata={
                "raw_prompt": payload.prompt,
                "material_hint": payload.material_hint or "",
            },
        ),
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result.error or "prompt enhancement failed",
        )

    enhanced = ""
    if isinstance(result.data, dict):
        enhanced = str(result.data.get("enhanced_prompt") or "").strip()
    if not enhanced:
        enhanced = result.content.strip()
    # Strip markdown fences if the model ignored instructions
    if enhanced.startswith("```"):
        lines = enhanced.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        enhanced = "\n".join(lines).strip()

    return success_response({"enhanced_prompt": enhanced})
