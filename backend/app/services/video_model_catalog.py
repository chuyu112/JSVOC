from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings


SEEDANCE_2_KEY = "seedance-2.0"
SEEDANCE_2_FAST_KEY = "seedance-2.0-fast"

DEFAULT_SEEDANCE_2_ENDPOINT = "doubao-seedance-2-0-260128"
DEFAULT_SEEDANCE_2_FAST_ENDPOINT = "doubao-seedance-2-0-fast-260128"


@dataclass(frozen=True)
class VideoModelSpec:
    key: str
    label: str
    value: str
    kind: str
    resolutions: tuple[str, ...]
    pricing_yuan_per_second: dict[str, float]
    available: bool
    disabled_reason: str | None = None


def video_model_catalog(settings: Settings | None = None) -> list[VideoModelSpec]:
    settings = settings or get_settings()
    enabled = enabled_video_model_keys(settings)
    standard_endpoint = settings.video_generation_seedance_2_endpoint.strip() or DEFAULT_SEEDANCE_2_ENDPOINT
    fast_endpoint = settings.video_generation_seedance_fast_endpoint.strip() or DEFAULT_SEEDANCE_2_FAST_ENDPOINT

    return [
        VideoModelSpec(
            key=SEEDANCE_2_KEY,
            label="Seedance 2.0",
            value=standard_endpoint,
            kind="standard",
            resolutions=("480p", "720p", "1080p"),
            pricing_yuan_per_second={"480p": 7 / 15, "720p": 1.0, "1080p": 37 / 15},
            available=SEEDANCE_2_KEY in enabled,
            disabled_reason=None if SEEDANCE_2_KEY in enabled else "当前账号未启用 Seedance 2.0 标准版 endpoint",
        ),
        VideoModelSpec(
            key=SEEDANCE_2_FAST_KEY,
            label="Seedance 2.0 Fast",
            value=fast_endpoint,
            kind="fast",
            resolutions=("480p", "720p"),
            pricing_yuan_per_second={"480p": 5.6 / 15, "720p": 0.8},
            available=SEEDANCE_2_FAST_KEY in enabled,
            disabled_reason=None if SEEDANCE_2_FAST_KEY in enabled else "当前账号未启用 Seedance 2.0 Fast endpoint",
        ),
    ]


def enabled_video_model_keys(settings: Settings) -> set[str]:
    configured = settings.video_generation_enabled_models.strip()
    if not configured:
        return {SEEDANCE_2_KEY, SEEDANCE_2_FAST_KEY}
    return {item.strip() for item in configured.split(",") if item.strip()}


def resolve_video_model_endpoint(value: str | None, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    requested = (value or "").strip()
    if not requested:
        first_enabled = next((spec for spec in video_model_catalog(settings) if spec.available), None)
        if first_enabled is not None:
            return first_enabled.value
        requested = settings.video_generation_model.strip()
    if not requested:
        return settings.video_generation_seedance_2_endpoint.strip() or DEFAULT_SEEDANCE_2_ENDPOINT
    requested = normalize_model_key(requested)

    for spec in video_model_catalog(settings):
        if requested in {spec.key, spec.value}:
            return spec.value

    return requested


def video_model_availability(value: str | None, settings: Settings | None = None) -> tuple[bool, str | None]:
    requested = normalize_model_key((value or "").strip())
    if not requested:
        return True, None

    for spec in video_model_catalog(settings):
        if requested in {spec.key, spec.value}:
            return spec.available, spec.disabled_reason

    return False, "不支持的视频模型，请使用 Seedance 2.0 或 Seedance 2.0 Fast"


def video_model_pricing(value: str | None, settings: Settings | None = None) -> dict[str, float] | None:
    requested = normalize_model_key((value or "").strip())
    for spec in video_model_catalog(settings):
        if requested in {spec.key, spec.value}:
            return spec.pricing_yuan_per_second
    return None


def normalize_model_key(value: str) -> str:
    aliases = {
        "seedance-2-0": SEEDANCE_2_KEY,
        "seedance-2-0-fast": SEEDANCE_2_FAST_KEY,
        "doubao-seedance-2-0-fast-260128": SEEDANCE_2_FAST_KEY,
        "doubao-seedance-2-0-260128": SEEDANCE_2_KEY,
    }
    return aliases.get(value, value)
