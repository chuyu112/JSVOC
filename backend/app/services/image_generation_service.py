import base64
import binascii
import logging
import time
from io import BytesIO
from typing import Any

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import Settings, get_settings
from app.schemas.image_generation import (
    GeneratedImage,
    ImageEditRequest,
    ImageReferenceInput,
    ImageGenerateRequest,
    ImageGenerateResponse,
)


IMAGE_MODEL = "gpt-image-2"
IMAGE_TIMEOUT_SECONDS = 180.0
IMAGE_REQUEST_ATTEMPTS = 2
RETRYABLE_IMAGE_STATUS_CODES = {502, 503, 504}
SUPPORTED_EDIT_IMAGE_MIMES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
MAX_PROVIDER_MULTIPART_IMAGE_BYTES = 600_000
MIN_PROVIDER_IMAGE_BYTES = 60_000
logger = logging.getLogger(__name__)


def generate_image(payload: ImageGenerateRequest) -> ImageGenerateResponse:
    settings = get_settings()
    started_at = time.perf_counter()
    provider = settings.llm_provider.strip().lower().replace("-", "_") or "unknown"
    endpoint = image_generations_url(settings)
    headers = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"

    request_body: dict[str, Any] = {
        "model": IMAGE_MODEL,
        "prompt": payload.prompt,
        "n": payload.n,
        "size": payload.size,
        "quality": payload.quality,
    }

    response = post_image_request_with_retry(
        endpoint,
        headers=headers,
        json=request_body,
        timeout=max(float(settings.llm_timeout_seconds), IMAGE_TIMEOUT_SECONDS),
    )
    response.raise_for_status()
    body = response.json()

    images = [normalize_image(item) for item in body.get("data") or [] if isinstance(item, dict)]
    return ImageGenerateResponse(
        provider=provider,
        model=body.get("model") or IMAGE_MODEL,
        images=images,
        usage=body.get("usage") or {},
        latency_ms=elapsed_ms(started_at),
    )


def edit_image(payload: ImageEditRequest) -> ImageGenerateResponse:
    references = image_references_for_payload(payload)
    files = prepare_edit_image_files(references)

    settings = get_settings()
    started_at = time.perf_counter()
    provider = settings.llm_provider.strip().lower().replace("-", "_") or "unknown"
    endpoint = image_edits_url(settings)
    headers = {}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"

    data = {
        "model": IMAGE_MODEL,
        "prompt": build_image_edit_prompt(payload),
        "n": str(payload.n),
        "size": payload.size,
        "quality": payload.quality,
    }

    response = post_image_request_with_retry(
        endpoint,
        headers=headers,
        data=data,
        files=files,
        timeout=max(float(settings.llm_timeout_seconds), IMAGE_TIMEOUT_SECONDS),
    )
    response.raise_for_status()
    body = response.json()

    images = [normalize_image(item) for item in body.get("data") or [] if isinstance(item, dict)]
    return ImageGenerateResponse(
        provider=provider,
        model=body.get("model") or IMAGE_MODEL,
        images=images,
        usage=body.get("usage") or {},
        latency_ms=elapsed_ms(started_at),
    )


def image_generations_url(settings: Settings) -> str:
    base_url = strip_url_method_prefix(settings.llm_base_url).rstrip("/")
    if not base_url:
        raise ValueError("LLM_BASE_URL is required for image generation")
    if base_url.endswith("/images/generations"):
        return base_url
    if base_url.endswith("/chat/completions"):
        return f"{base_url[: -len('/chat/completions')]}/images/generations"
    if base_url.endswith("/v1"):
        return f"{base_url}/images/generations"
    return f"{base_url}/v1/images/generations"


def image_edits_url(settings: Settings) -> str:
    base_url = strip_url_method_prefix(settings.llm_base_url).rstrip("/")
    if not base_url:
        raise ValueError("LLM_BASE_URL is required for image editing")
    if base_url.endswith("/images/edits"):
        return base_url
    if base_url.endswith("/images/generations"):
        return f"{base_url[: -len('/images/generations')]}/images/edits"
    if base_url.endswith("/chat/completions"):
        return f"{base_url[: -len('/chat/completions')]}/images/edits"
    if base_url.endswith("/v1"):
        return f"{base_url}/images/edits"
    return f"{base_url}/v1/images/edits"


def build_image_edit_prompt(payload: ImageEditRequest) -> str:
    references = image_references_for_payload(payload)
    reference_types = normalized_reference_types(reference_types_for_payload(payload))
    type_label = "、".join(reference_type_label(item) for item in reference_types)
    rules = [
        f"参考图类型：{type_label}。",
        "术语定义：人设图只定义账号人物/出镜人物，包括脸、年龄感、发型、体型、气质和穿搭风格。",
        "术语定义：货品图只定义商品，包括形状、颜色、材质、纹理、比例、证书或关键细节。",
        "术语定义：场景图只定义拍摄环境，包括档口、公司、桌面、柜台、灯光、陈列方式和空间氛围。",
        "必须按下面的参考图名称绑定用途，不要把人设图、货品图、场景图混用。",
        "人设和场景有多张参考图时，第 1 张为主参考，其余只作为补充，不要把多张图混合成新的人脸或新场景。"
        if {"persona", "location"} & set(reference_types)
        else "",
        "货品有多张参考图时，所有参考图都要综合参考，全面理解货品的形状、颜色、材质、纹理、比例和关键细节。"
        if "product" in reference_types
        else "",
        *reference_image_order_rules(references),
    ]

    if "persona" in reference_types:
        rules.append(
            "人设参考图已提供：可以生成新的人、货、场组合；人物必须以参考图人物为唯一人设依据，"
            "不要凭文字另造年龄、长相或身份。"
        )
    else:
        rules.append(
            "未提供人设参考图：重点生成货品主体和场景，不要生成可识别的人设本人、姓名昵称对应人物、正脸或创始人本人。"
        )

    if "product" in reference_types:
        rules.append("货品参考图已提供：参考货品主体、形制、颜色、质感和关键细节，生成新的货品呈现。")
    if "location" in reference_types:
        rules.append("场景参考图已提供：参考场景空间、档口/公司环境、陈列关系和自然光氛围。")
    if "persona" not in reference_types and {"product", "location"} & set(reference_types):
        rules.append("如需人物，只允许非人设手模/工作人员的手部、背影或局部动作服务货品展示。")

    filtered_rules = [rule for rule in rules if rule]
    return f"{payload.prompt.strip()}\n\n图生图参考约束：\n" + "\n".join(f"- {rule}" for rule in filtered_rules)


def post_image_request_with_retry(
    endpoint: str,
    *,
    headers: dict[str, str],
    timeout: float,
    json: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    files: list[tuple[str, tuple[str, bytes, str]]] | None = None,
) -> httpx.Response:
    last_request_error: httpx.RequestError | None = None
    for attempt in range(IMAGE_REQUEST_ATTEMPTS):
        request_kwargs: dict[str, Any] = {
            "headers": headers,
            "timeout": timeout,
        }
        if json is not None:
            request_kwargs["json"] = json
        if data is not None:
            request_kwargs["data"] = data
        if files is not None:
            request_kwargs["files"] = files

        try:
            response = httpx.post(endpoint, **request_kwargs)
        except httpx.RequestError as exc:
            last_request_error = exc
            if attempt + 1 < IMAGE_REQUEST_ATTEMPTS:
                continue
            raise

        if response.status_code in RETRYABLE_IMAGE_STATUS_CODES and attempt + 1 < IMAGE_REQUEST_ATTEMPTS:
            logger.warning(
                "image request retrying after transient upstream status",
                extra={
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "attempt": attempt + 1,
                    "attempts": IMAGE_REQUEST_ATTEMPTS,
                    "response_prefix": response.text[:300],
                },
            )
            continue
        response.raise_for_status()
        return response

    if last_request_error is not None:
        raise last_request_error
    raise RuntimeError("image request retry loop exited without a response")


def reference_image_order_rules(references: list[ImageReferenceInput]) -> list[str]:
    if not references:
        return ["未收到参考图文件。"]

    rules = []
    counts = {"persona": 0, "product": 0, "location": 0}
    for image in references:
        counts[image.reference_image_type] += 1
        label = reference_type_label(image.reference_image_type)
        image_name = reference_image_name(image.reference_image_type, counts[image.reference_image_type])
        filename = image.source_image_filename or image_name
        rules.append(f"{image_name}：{label}，文件名 {filename}。")
    return rules


def normalized_reference_types(reference_types: list[str]) -> list[str]:
    allowed = {"persona", "product", "location"}
    result: list[str] = []
    for item in reference_types or ["product"]:
        normalized = item.strip().lower()
        if normalized in allowed and normalized not in result:
            result.append(normalized)
    return result or ["product"]


def reference_type_label(reference_type: str) -> str:
    labels = {
        "persona": "人设参考图",
        "product": "货品参考图",
        "location": "场景参考图",
    }
    return labels.get(reference_type, reference_type)


def reference_image_name(reference_type: str, index: int) -> str:
    labels = {
        "persona": "人设图",
        "product": "货品图",
        "location": "场景图",
    }
    return f"{labels.get(reference_type, '参考图')}{index}"


def image_references_for_payload(payload: ImageEditRequest) -> list[ImageReferenceInput]:
    if payload.reference_images:
        return payload.reference_images
    if not payload.source_image_base64:
        return []

    reference_type = normalized_reference_types(payload.reference_image_types)[0]
    return [
        ImageReferenceInput(
            reference_image_type=reference_type,  # type: ignore[arg-type]
            source_image_base64=payload.source_image_base64,
            source_image_mime=payload.source_image_mime,
            source_image_filename=payload.source_image_filename,
        )
    ]


def reference_types_for_payload(payload: ImageEditRequest) -> list[str]:
    if payload.reference_images:
        return [image.reference_image_type for image in payload.reference_images]
    return payload.reference_image_types


def prepare_edit_image_files(references: list[ImageReferenceInput]) -> list[tuple[str, tuple[str, bytes, str]]]:
    if not references:
        return []

    target_per_image = max(
        MIN_PROVIDER_IMAGE_BYTES,
        MAX_PROVIDER_MULTIPART_IMAGE_BYTES // max(len(references), 1),
    )
    files: list[tuple[str, tuple[str, bytes, str]]] = []
    for image in references:
        mime = validated_image_mime(image.source_image_mime)
        raw = decode_base64_image(image.source_image_base64)
        prepared_bytes, prepared_mime = prepare_provider_reference_image(raw, mime, target_per_image)
        filename = provider_reference_filename(image.source_image_filename, prepared_mime)
        files.append(("image", (filename, prepared_bytes, prepared_mime)))
    return files


def prepare_provider_reference_image(raw: bytes, mime: str, target_bytes: int) -> tuple[bytes, str]:
    if len(raw) <= target_bytes:
        return raw, mime

    try:
        with Image.open(BytesIO(raw)) as opened:
            image = ImageOps.exif_transpose(opened)
            if image.mode not in {"RGB", "L"}:
                background = Image.new("RGB", image.size, (255, 255, 255))
                if image.mode in {"RGBA", "LA"}:
                    background.paste(image.convert("RGBA"), mask=image.convert("RGBA").getchannel("A"))
                    image = background
                else:
                    image = image.convert("RGB")
            elif image.mode != "RGB":
                image = image.convert("RGB")

            best = encode_jpeg_under_limit(image, target_bytes)
    except UnidentifiedImageError as exc:
        raise ValueError("reference image must be a readable PNG, JPEG, or WebP file") from exc

    if len(best) > target_bytes:
        raise ValueError("reference image is too large; please upload fewer or clearer compressed reference images")
    return best, "image/jpeg"


def encode_jpeg_under_limit(image: Image.Image, target_bytes: int) -> bytes:
    current = resize_image_to_max_side(image, 1280)
    best = encode_jpeg(current, quality=82)

    for max_side in (1280, 1120, 960, 800, 640, 512):
        current = resize_image_to_max_side(image, max_side)
        for quality in (82, 74, 66, 58, 50, 42, 34, 28):
            candidate = encode_jpeg(current, quality=quality)
            if len(candidate) < len(best):
                best = candidate
            if len(candidate) <= target_bytes:
                return candidate
    return best


def resize_image_to_max_side(image: Image.Image, max_side: int) -> Image.Image:
    width, height = image.size
    longest = max(width, height)
    if longest <= max_side:
        return image.copy()

    ratio = max_side / float(longest)
    new_size = (max(1, int(width * ratio)), max(1, int(height * ratio)))
    return image.resize(new_size, Image.Resampling.LANCZOS)


def encode_jpeg(image: Image.Image, *, quality: int) -> bytes:
    output = BytesIO()
    image.save(output, format="JPEG", quality=quality, optimize=True, progressive=True)
    return output.getvalue()


def provider_reference_filename(filename: str, mime: str) -> str:
    cleaned = (filename or "reference").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    stem = cleaned.rsplit(".", 1)[0] if "." in cleaned else cleaned
    extension = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }.get(mime, "jpg")
    return f"{stem or 'reference'}.{extension}"


def strip_url_method_prefix(value: str) -> str:
    cleaned = value.strip()
    parts = cleaned.split(maxsplit=1)
    if len(parts) == 2 and parts[0].upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
        return parts[1].strip()
    return cleaned


def decode_base64_image(value: str) -> bytes:
    encoded = value.strip()
    if "," in encoded and encoded.lower().startswith("data:"):
        encoded = encoded.split(",", 1)[1]

    try:
        return base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("source_image_base64 must be valid base64") from exc


def validated_image_mime(value: str) -> str:
    mime = value.strip().lower()
    if mime not in SUPPORTED_EDIT_IMAGE_MIMES:
        raise ValueError("图生图参考图仅支持 PNG、JPEG、WebP 格式")
    return "image/jpeg" if mime == "image/jpg" else mime


def normalize_image(item: dict[str, Any]) -> GeneratedImage:
    b64_json = item.get("b64_json")
    url = item.get("url")
    data_url = item.get("data_url")
    if b64_json and not data_url:
        data_url = f"data:image/png;base64,{b64_json}"
    return GeneratedImage(
        b64_json=b64_json if isinstance(b64_json, str) else None,
        url=url if isinstance(url, str) else None,
        data_url=data_url if isinstance(data_url, str) else None,
    )


def elapsed_ms(started_at: float) -> int:
    return int((time.perf_counter() - started_at) * 1000)
