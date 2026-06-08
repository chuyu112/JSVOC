import logging
import time
from collections.abc import Callable
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.services import llm_channel_service
from app.services.video_model_catalog import resolve_video_model_endpoint

logger = logging.getLogger(__name__)

VIDEO_REQUEST_ATTEMPTS = 2
RETRYABLE_VIDEO_STATUS_CODES = {502, 503, 504}
VIDEO_POLL_INTERVAL_SECONDS = 5.0
VIDEO_MAX_POLL_SECONDS = 1200.0


def generate_video(
    prompt: str,
    options: dict[str, Any] | None = None,
    first_frame: str | None = None,
    last_frame: str | None = None,
    reference_media: str | None = None,
    reference_medias: list[str] | None = None,
    reference_images: list[str] | None = None,
    reference_videos: list[str] | None = None,
    reference_audios: list[str] | None = None,
    reference_image_names: list[str] | None = None,
    on_provider_task_created: Callable[[dict[str, Any]], None] | None = None,
    db: Session | None = None,
) -> dict[str, Any]:
    settings = llm_channel_service.get_effective_video_settings(db, get_settings()) if db is not None else get_settings()
    started_at = time.perf_counter()
    provider = video_provider(settings)
    base_url = video_base_url(settings)
    api_key = video_api_key(settings)
    if not api_key:
        raise ValueError("VIDEO_GENERATION_API_KEY or ARK_API_KEY is required for video generation")
    model = resolve_video_model_endpoint(
        str((options or {}).get("model") or ""),
        settings,
    )

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    endpoint = f"{base_url.rstrip('/')}/api/v3/contents/generations/tasks"

    prompt = build_video_reference_prompt(
        prompt,
        reference_image_names=reference_image_names,
        reference_images=reference_images,
    )

    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    if reference_media:
        content.append({"type": "image_url", "image_url": {"url": reference_media}, "role": "reference_image"})
    if reference_medias:
        for url in reference_medias:
            content.append({"type": "image_url", "image_url": {"url": url}, "role": "reference_image"})
    if reference_images:
        for url in reference_images:
            content.append({"type": "image_url", "image_url": {"url": url}, "role": "reference_image"})
    if reference_videos:
        for url in reference_videos:
            content.append({"type": "video_url", "video_url": {"url": url}, "role": "reference_video"})
    if reference_audios:
        for url in reference_audios:
            content.append({"type": "audio_url", "audio_url": {"url": url}, "role": "reference_audio"})
    if first_frame:
        content.append({"type": "image_url", "image_url": {"url": first_frame}, "role": "reference_image"})
    if last_frame:
        content.append({"type": "image_url", "image_url": {"url": last_frame}, "role": "reference_image"})

    request_body: dict[str, Any] = {
        "model": model,
        "content": content,
    }

    if options:
        mapped: dict[str, Any] = {}
        for k, v in options.items():
            if k in ("first_frame", "last_frame", "reference_media", "reference_medias", "reference_images", "reference_videos", "reference_audios", "mode", "count", "timeout_hours", "advanced_open", "web_search"):
                continue
            if k == "with_sound":
                mapped["generate_audio"] = v
            elif k == "duration_seconds" and options.get("duration_mode") == "seconds":
                mapped["duration"] = v
            elif k == "duration_mode":
                continue
            else:
                mapped[k] = v
        if "watermark" not in mapped:
            mapped["watermark"] = False
        request_body.update(mapped)

    response = post_video_request_with_retry(
        endpoint,
        headers=headers,
        json=request_body,
        timeout=float(settings.video_generation_timeout_seconds),
    )
    response.raise_for_status()
    body = response.json()

    task_id = body.get("id")
    if not task_id:
        return {
            "provider": provider,
            "model": model,
            "video_url": None,
            "task_id": None,
            "status": "unknown",
            "latency_ms": elapsed_ms(started_at),
            "raw_response": body,
        }

    if on_provider_task_created is not None:
        on_provider_task_created(
            {
                "provider": provider,
                "model": model,
                "task_id": task_id,
                "status": "submitted",
                "raw_response": body,
                "latency_ms": elapsed_ms(started_at),
            }
        )

    result = poll_video_task(base_url, api_key, task_id, started_at, max_seconds=VIDEO_MAX_POLL_SECONDS)
    return {
        "provider": provider,
        "model": model,
        "video_url": result.get("video_url"),
        "task_id": task_id,
        "status": result.get("status", "unknown"),
        "latency_ms": elapsed_ms(started_at),
        "raw_response": result.get("raw_response"),
    }


def build_video_reference_prompt(
    prompt: str,
    *,
    reference_image_names: list[str] | None = None,
    reference_images: list[str] | None = None,
) -> str:
    cleaned_prompt = prompt.strip()
    image_count = len(reference_images or [])
    if image_count < 1:
        return cleaned_prompt

    names = normalized_reference_image_names(reference_image_names, image_count)
    prompt_has_reference_mentions = any(name in cleaned_prompt for name in names)
    if not prompt_has_reference_mentions and "@图片" not in cleaned_prompt:
        return cleaned_prompt

    rules = [
        "视频参考图绑定规则：",
        "如果提示词出现 @图片1、@图片2 等引用，必须严格按下方同名参考图绑定主体、人物、货品或场景。",
        "例：@图片1 跟 @图片2 打架 = 让 @图片1 的主体和 @图片2 的主体发生打架动作，不要把两张图混成同一个主体。",
        "保持每张参考图的主体身份、外观、服装/产品特征和关键视觉差异；动作可以按提示词重新编排。",
    ]
    rules.extend(f"{name}：第 {index} 张参考图片。" for index, name in enumerate(names, start=1))
    return f"{cleaned_prompt}\n\n" + "\n".join(rules)


def normalized_reference_image_names(reference_image_names: list[str] | None, image_count: int) -> list[str]:
    names: list[str] = []
    for index in range(image_count):
        raw_name = (reference_image_names or [])[index] if index < len(reference_image_names or []) else ""
        cleaned = str(raw_name or "").strip()
        if not cleaned:
            cleaned = f"图片{index + 1}"
        names.append(cleaned if cleaned.startswith("@") else f"@{cleaned}")
    return names


def poll_video_task(
    base_url: str,
    api_key: str,
    task_id: str,
    started_at: float,
    max_seconds: float = VIDEO_MAX_POLL_SECONDS,
) -> dict[str, Any]:
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    endpoint = f"{base_url.rstrip('/')}/api/v3/contents/generations/tasks/{task_id}"
    deadline = time.perf_counter() + max_seconds

    while time.perf_counter() < deadline:
        resp = httpx.get(endpoint, headers=headers, timeout=60.0)
        resp.raise_for_status()
        body = resp.json()

        status = _extract_task_status(body)
        if status in ("succeeded", "completed", "success"):
            video_url = _extract_video_url(body)
            return {"status": status, "video_url": video_url, "raw_response": body}
        if status in ("failed", "error", "cancelled"):
            error_msg = _extract_error_message(body)
            raise RuntimeError(f"video generation task failed: {error_msg}")

        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            break
        sleep_time = min(VIDEO_POLL_INTERVAL_SECONDS, remaining)
        time.sleep(sleep_time)

    raise TimeoutError("video generation task polling timed out")


def get_video_task_result(task_id: str, db: Session | None = None) -> dict[str, Any]:
    settings = llm_channel_service.get_effective_video_settings(db, get_settings()) if db is not None else get_settings()
    base_url = video_base_url(settings)
    api_key = video_api_key(settings)
    if not api_key:
        raise ValueError("VIDEO_GENERATION_API_KEY or ARK_API_KEY is required for video generation")
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    endpoint = f"{base_url.rstrip('/')}/api/v3/contents/generations/tasks/{task_id}"
    resp = httpx.get(endpoint, headers=headers, timeout=60.0)
    resp.raise_for_status()
    body = resp.json()

    status = _extract_task_status(body)
    if status in ("succeeded", "completed", "success"):
        return {
            "status": status,
            "video_url": _extract_video_url(body),
            "raw_response": body,
        }
    if status in ("failed", "error", "cancelled"):
        return {
            "status": status,
            "error_message": _extract_error_message(body),
            "raw_response": body,
        }
    return {
        "status": status or "running",
        "raw_response": body,
    }


def post_video_request_with_retry(
    endpoint: str,
    *,
    headers: dict[str, str],
    timeout: float,
    json: dict[str, Any],
) -> httpx.Response:
    last_request_error: httpx.RequestError | None = None
    for attempt in range(VIDEO_REQUEST_ATTEMPTS):
        try:
            response = httpx.post(endpoint, headers=headers, json=json, timeout=timeout)
        except httpx.RequestError as exc:
            last_request_error = exc
            if attempt + 1 < VIDEO_REQUEST_ATTEMPTS:
                continue
            raise

        if response.status_code in RETRYABLE_VIDEO_STATUS_CODES and attempt + 1 < VIDEO_REQUEST_ATTEMPTS:
            logger.warning(
                "video request retrying after transient upstream status",
                extra={
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "attempt": attempt + 1,
                    "attempts": VIDEO_REQUEST_ATTEMPTS,
                    "response_prefix": response.text[:300],
                },
            )
            continue
        response.raise_for_status()
        return response

    if last_request_error is not None:
        raise last_request_error
    raise RuntimeError("video request retry loop exited without a response")


def video_base_url(settings: Settings) -> str:
    url = settings.video_generation_base_url.strip()
    url = strip_url_method_prefix(url).rstrip("/")
    if not url:
        raise ValueError("VIDEO_GENERATION_BASE_URL is required for video generation")
    if url.endswith("/api/v3/contents/generations/tasks"):
        return url[: -len("/api/v3/contents/generations/tasks")]
    if url.endswith("/chat/completions"):
        return url[: -len("/chat/completions")]
    if url.endswith("/v1"):
        return url[: -len("/v1")]
    return url


def video_provider(settings: Settings) -> str:
    provider = settings.llm_provider.strip().lower().replace("-", "_")
    if provider in {"seedance_video", "ark_video"}:
        return "seedance_video"
    return "seedance"


def video_api_key(settings: Settings) -> str:
    return settings.video_generation_api_key.strip() or settings.ark_api_key.strip()


def strip_url_method_prefix(value: str) -> str:
    cleaned = value.strip()
    parts = cleaned.split(maxsplit=1)
    if len(parts) == 2 and parts[0].upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
        return parts[1].strip()
    return cleaned


def _extract_task_status(body: dict[str, Any]) -> str:
    status = body.get("status") or body.get("task_status") or body.get("state") or ""
    return str(status).lower().strip()


def _extract_video_url(body: dict[str, Any]) -> str | None:
    content = body.get("content") or body.get("result") or body.get("output") or {}
    if isinstance(content, list) and content:
        content = content[0]
    if isinstance(content, dict):
        url = content.get("video_url") or content.get("url") or content.get("file_url")
        if url:
            return str(url)
    return body.get("video_url") or body.get("url") or None


def _extract_error_message(body: dict[str, Any]) -> str:
    error = body.get("error") or body.get("message") or body.get("reason") or ""
    if isinstance(error, dict):
        return str(error.get("message") or error.get("reason") or "")
    return str(error) or "unknown error"


def elapsed_ms(started_at: float) -> int:
    return int((time.perf_counter() - started_at) * 1000)
