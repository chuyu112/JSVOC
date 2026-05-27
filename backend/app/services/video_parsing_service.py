import json
import logging
import re
import tempfile
import time
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

DOUYIN_PATTERN = re.compile(
    r"(?:https?://)?(?:v\.douyin\.com|www\.douyin\.com/video/|douyin\.com/video/)([\w/-]+)",
    re.IGNORECASE,
)
XIAOHONGSHU_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.xiaohongshu\.com/explore/|xhslink\.com/|xiaohongshu\.com/discovery/item/)([\w/-]+)",
    re.IGNORECASE,
)
SHIPINHAO_PATTERN = re.compile(
    r"(?:https?://)?(?:channels\.weixin\.qq\.com/|weixin\.qq\.com/)([\w/-]+)",
    re.IGNORECASE,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}


@dataclass
class VideoParseResult:
    title: str
    original_script: str
    account_name: str | None = None
    cover_url: str | None = None
    platform: str = "unknown"
    source_url: str = ""


def identify_platform(url: str) -> str:
    if DOUYIN_PATTERN.search(url):
        return "douyin"
    if XIAOHONGSHU_PATTERN.search(url):
        return "xiaohongshu"
    if SHIPINHAO_PATTERN.search(url):
        return "shipinhao"
    return "unknown"


def parse_video_link(url: str, settings: Settings | None = None) -> VideoParseResult:
    settings = settings or get_settings()
    platform = identify_platform(url)

    if settings.video_parser_api_url.strip():
        return _parse_via_external_api(url, platform, settings)

    if platform == "douyin":
        return _parse_douyin_link(url)
    if platform == "xiaohongshu":
        return _parse_xiaohongshu_link(url)

    raise RuntimeError(
        f"暂不支持该平台自动解析（{platform}），请使用本地上传或手动输入文案。"
    )


def parse_video_upload(
    file_content: bytes,
    filename: str,
    content_type: str,
    settings: Settings | None = None,
) -> VideoParseResult:
    settings = settings or get_settings()

    if not settings.asr_api_url.strip():
        raise RuntimeError(
            "视频上传 ASR 服务未配置，请手动输入文案或联系管理员配置 ASR_API_URL。"
        )

    suffix = _guess_suffix(filename, content_type)
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name

    try:
        return _transcribe_via_asr_api(tmp_path, filename, settings)
    finally:
        import os

        try:
            os.remove(tmp_path)
        except OSError:
            pass


def _parse_via_external_api(
    url: str, platform: str, settings: Settings
) -> VideoParseResult:
    api_url = settings.video_parser_api_url.strip().rstrip("/")
    api_key = settings.video_parser_api_key.strip()

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {"url": url, "platform": platform}

    started_at = time.perf_counter()
    try:
        response = httpx.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=30.0,
            follow_redirects=True,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "External video parser API returned error",
            extra={
                "url": url,
                "api_url": api_url,
                "status_code": exc.response.status_code,
                "response": exc.response.text[:300],
            },
        )
        raise RuntimeError(
            f"视频解析服务返回错误（{exc.response.status_code}），请稍后重试或使用本地上传。"
        ) from exc
    except httpx.RequestError as exc:
        logger.warning(
            "External video parser API request failed",
            extra={"url": url, "api_url": api_url, "error": str(exc)},
        )
        raise RuntimeError(
            "视频解析服务请求失败，请检查网络或稍后重试。"
        ) from exc

    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        raise RuntimeError("视频解析服务返回格式异常") from exc

    latency_ms = int((time.perf_counter() - started_at) * 1000)
    logger.info(
        "External video parser succeeded",
        extra={"url": url, "latency_ms": latency_ms},
    )

    return VideoParseResult(
        title=_first_text(data, "title", "desc", "description") or "未识别标题",
        original_script=_first_text(data, "original_script", "script", "text", "content", "desc", "description") or "",
        account_name=_first_text(data, "account_name", "author", "creator", "nickname") or None,
        cover_url=_first_text(data, "cover_url", "cover", "thumbnail") or None,
        platform=platform,
        source_url=url,
    )


def _parse_douyin_link(url: str) -> VideoParseResult:
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=15.0, follow_redirects=True)
        resp.raise_for_status()
    except httpx.RequestError as exc:
        raise RuntimeError("抖音页面抓取失败，请使用本地上传或手动输入") from exc

    text = resp.text

    render_data_match = re.search(
        r'<script id="RENDER_DATA" type="application/json">(.+?)</script>',
        text,
        re.DOTALL,
    )
    if render_data_match:
        raw = render_data_match.group(1)
        try:
            decoded = unquote(raw)
            data = json.loads(decoded)
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = {}

        aweme_detail = _deep_get(data, "app", "videoDetail", "awemeDetail") or _deep_get(
            data, "app", "videoInfo", "awemeDetail"
        )
        if not aweme_detail:
            aweme_detail = _deep_get(data, "awemeDetail") or _deep_get(data, "aweme_detail")

        if aweme_detail:
            title = _deep_get(aweme_detail, "desc") or ""
            if not title:
                title = _deep_get(aweme_detail, "share_info", "share_title") or "未识别标题"

            author = _deep_get(aweme_detail, "author", "nickname") or ""
            cover = _deep_get(aweme_detail, "video", "cover", "url_list", 0) or ""
            if not cover:
                cover = _deep_get(aweme_detail, "video", "dynamicCover", "url_list", 0) or ""

            return VideoParseResult(
                title=title,
                original_script=title,
                account_name=author or None,
                cover_url=cover or None,
                platform="douyin",
                source_url=url,
            )

    og_title_match = re.search(r'<meta property="og:title" content="([^"]+)"', text)
    og_desc_match = re.search(r'<meta property="og:description" content="([^"]+)"', text)
    og_image_match = re.search(r'<meta property="og:image" content="([^"]+)"', text)

    title = (og_title_match.group(1) if og_title_match else "") or "未识别标题"
    desc = og_desc_match.group(1) if og_desc_match else ""

    return VideoParseResult(
        title=title,
        original_script=desc or title,
        account_name=None,
        cover_url=og_image_match.group(1) if og_image_match else None,
        platform="douyin",
        source_url=url,
    )


def _parse_xiaohongshu_link(url: str) -> VideoParseResult:
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=15.0, follow_redirects=True)
        resp.raise_for_status()
    except httpx.RequestError as exc:
        raise RuntimeError("小红书页面抓取失败，请使用本地上传或手动输入") from exc

    text = resp.text

    initial_match = re.search(
        r'window\.__INITIAL_STATE__\s*=\s*({.+?});?\s*</script>',
        text,
        re.DOTALL,
    )
    if initial_match:
        try:
            data = json.loads(initial_match.group(1))
        except json.JSONDecodeError:
            data = {}

        note = _deep_get(data, "note", "noteDetailMap") or _deep_get(data, "noteDetailMap")
        if isinstance(note, dict):
            first_key = next(iter(note.keys())) if note else None
            if first_key:
                detail = note[first_key].get("note") if isinstance(note[first_key], dict) else None
                if detail:
                    title = detail.get("title") or "未识别标题"
                    desc = detail.get("desc") or ""
                    author = _deep_get(detail, "user", "nickname") or ""
                    cover = _deep_get(detail, "imageList", 0, "urlDefault") or ""
                    return VideoParseResult(
                        title=title,
                        original_script=desc or title,
                        account_name=author or None,
                        cover_url=cover or None,
                        platform="xiaohongshu",
                        source_url=url,
                    )

    og_title_match = re.search(r'<meta property="og:title" content="([^"]+)"', text)
    og_desc_match = re.search(r'<meta property="og:description" content="([^"]+)"', text)
    og_image_match = re.search(r'<meta property="og:image" content="([^"]+)"', text)

    title = (og_title_match.group(1) if og_title_match else "") or "未识别标题"
    desc = og_desc_match.group(1) if og_desc_match else ""

    return VideoParseResult(
        title=title,
        original_script=desc or title,
        account_name=None,
        cover_url=og_image_match.group(1) if og_image_match else None,
        platform="xiaohongshu",
        source_url=url,
    )


def _transcribe_via_asr_api(
    file_path: str, filename: str, settings: Settings
) -> VideoParseResult:
    api_url = settings.asr_api_url.strip().rstrip("/")
    api_key = settings.asr_api_key.strip()

    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    with open(file_path, "rb") as f:
        files = {"file": (filename, f, "application/octet-stream")}
        response = httpx.post(
            api_url,
            headers=headers,
            files=files,
            timeout=120.0,
        )

    response.raise_for_status()
    data = response.json()

    text = _first_text(data, "text", "transcript", "result", "content") or ""
    if not text:
        raise RuntimeError("ASR 服务未返回有效文案")

    return VideoParseResult(
        title=f"上传视频-{uuid.uuid4().hex[:8]}",
        original_script=text,
        account_name=None,
        cover_url=None,
        platform="unknown",
        source_url="",
    )


def _guess_suffix(filename: str, content_type: str) -> str:
    known_types = {
        "video/mp4": ".mp4",
        "video/quicktime": ".mov",
        "video/x-matroska": ".mkv",
        "video/webm": ".webm",
        "video/avi": ".avi",
    }
    if content_type in known_types:
        return known_types[content_type]
    if "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in {"mp4", "mov", "mkv", "webm", "avi", "flv", "m4v"}:
            return f".{ext}"
    return ".mp4"


def _first_text(data: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if value is not None:
            text = str(value).strip()
            if text:
                return text
    return ""


def _deep_get(obj: Any, *keys: str | int) -> Any:
    current = obj
    for key in keys:
        if current is None:
            return None
        if isinstance(key, int):
            if isinstance(current, list) and 0 <= key < len(current):
                current = current[key]
            else:
                return None
        elif isinstance(current, dict):
            current = current.get(key)
        else:
            return None
    return current
