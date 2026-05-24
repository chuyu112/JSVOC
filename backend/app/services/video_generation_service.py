import logging
import time
from collections.abc import Callable
from typing import Any

import httpx

from app.core.config import Settings, get_settings
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
    on_provider_task_created: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    started_at = time.perf_counter()
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
            "provider": "seedance",
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
                "provider": "seedance",
                "model": model,
                "task_id": task_id,
                "status": "submitted",
                "raw_response": body,
                "latency_ms": elapsed_ms(started_at),
            }
        )

    result = poll_video_task(base_url, api_key, task_id, started_at, max_seconds=VIDEO_MAX_POLL_SECONDS)
    return {
        "provider": "seedance",
        "model": model,
        "video_url": result.get("video_url"),
        "task_id": task_id,
        "status": result.get("status", "unknown"),
        "latency_ms": elapsed_ms(started_at),
        "raw_response": result.get("raw_response"),
    }


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


def get_video_task_result(task_id: str) -> dict[str, Any]:
    settings = get_settings()
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
