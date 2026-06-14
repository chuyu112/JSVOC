import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote, urlparse

import httpx

from app.core.config import Settings, get_settings
from app.services.gpu_worker_client import GPUWorkerClient
from app.services import storage_service

logger = logging.getLogger(__name__)

# Make Evil0ctal crawlers importable inside the container
sys.path.insert(0, "/opt")

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

MAX_DOUYIN_MEDIA_BYTES = 200 * 1024 * 1024


# Lazy importer for Evil0ctal HybridCrawler
_hybrid_crawler_class = None


def _get_hybrid_crawler():
    global _hybrid_crawler_class
    if _hybrid_crawler_class is None:
        try:
            from crawlers.hybrid.hybrid_crawler import HybridCrawler
            _hybrid_crawler_class = HybridCrawler
            logger.info("Evil0ctal HybridCrawler loaded successfully")
        except Exception as exc:
            logger.warning("Failed to load Evil0ctal HybridCrawler: %s", exc)
            _hybrid_crawler_class = False
    return _hybrid_crawler_class


_douyin_web_crawler_class = None


def _get_douyin_web_crawler():
    global _douyin_web_crawler_class
    if _douyin_web_crawler_class is None:
        try:
            from crawlers.douyin.web.web_crawler import DouyinWebCrawler

            _douyin_web_crawler_class = DouyinWebCrawler
        except Exception as exc:
            logger.warning("Failed to load DouyinWebCrawler: %s", exc)
            _douyin_web_crawler_class = False
    return _douyin_web_crawler_class


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@dataclass
class VideoParseResult:
    title: str
    original_script: str
    account_name: str | None = None
    cover_url: str | None = None
    platform: str = "unknown"
    source_url: str = ""


@dataclass
class DownloadedMedia:
    path: str
    content: bytes
    content_type: str


def identify_platform(url: str) -> str:
    if DOUYIN_PATTERN.search(url):
        return "douyin"
    if XIAOHONGSHU_PATTERN.search(url):
        return "xiaohongshu"
    if SHIPINHAO_PATTERN.search(url):
        return "shipinhao"
    return "unknown"


def _normalize_url(url: str) -> str:
    url = url.strip()
    if url.startswith("//"):
        return "https:" + url
    if not url.startswith("http://") and not url.startswith("https://"):
        return "https://" + url
    return url


def parse_video_link(url: str, settings: Settings | None = None) -> VideoParseResult:
    settings = settings or get_settings()
    url = _normalize_url(url)
    platform = identify_platform(url)

    if settings.video_parser_api_url.strip():
        return _parse_via_external_api(url, platform, settings)

    if platform == "douyin":
        # Try direct parsing first, fallback to Douyin_TikTok_Download_API
        try:
            return _parse_douyin_link(url)
        except RuntimeError:
            logger.info("Direct Douyin parse failed, trying Douyin_TikTok_Download_API")
            try:
                from app.services.douyin_api_client import DouyinAPIClient
                client = DouyinAPIClient(settings.douyin_api_url)
                data = client.parse_video(url)
                return VideoParseResult(
                    title=data.get("title", "未识别标题")[:200],
                    original_script=data.get("title", ""),
                    account_name=data.get("author", None),
                    cover_url=data.get("cover", None),
                    platform="douyin",
                    source_url=url,
                )
            except Exception as exc:
                logger.warning("DouyinAPI fallback also failed: %s", exc)
                raise RuntimeError(
                    "抖音链接解析失败。请:\n"
                    "1. 确认链接正确\n"
                    "2. 运行 deploy_douyin_api.bat 部署解析服务\n"
                    "3. 或使用本地上传功能"
                ) from exc
    if platform == "xiaohongshu":
        return _parse_xiaohongshu_link(url)

    raise RuntimeError(
        f"暂不支持该平台自动解析（{platform}），请使用本地上传或手动输入文案。"
    )


def import_douyin_profile_videos(source_url: str, *, count: int = 30) -> dict[str, Any]:
    url = _normalize_url(source_url)
    crawler_cls = _get_douyin_web_crawler()
    if not crawler_cls:
        raise RuntimeError("抖音主页解析器未加载，请检查服务器爬虫依赖。")

    async def _fetch() -> dict[str, Any]:
        crawler = crawler_cls()
        sec_user_id = await crawler.get_sec_user_id(url)
        if not sec_user_id:
            raise RuntimeError("未能从抖音链接提取主页用户 ID。")
        profile_response = await crawler.handler_user_profile(sec_user_id)
        posts_response = await crawler.fetch_user_post_videos(sec_user_id, 0, max(1, min(count, 50)))
        return normalize_douyin_profile_import(
            source_url=url,
            sec_user_id=sec_user_id,
            profile_response=profile_response,
            posts_response=posts_response,
        )

    return _run_async(_fetch())


def normalize_douyin_profile_import(
    *,
    source_url: str,
    sec_user_id: str,
    profile_response: dict[str, Any],
    posts_response: dict[str, Any],
) -> dict[str, Any]:
    user = _deep_get(profile_response, "user") or _deep_get(profile_response, "user_info") or {}
    if not isinstance(user, dict):
        user = {}

    aweme_list = _deep_get(posts_response, "aweme_list") or _deep_get(posts_response, "aweme_list_v2") or []
    if not isinstance(aweme_list, list):
        aweme_list = []

    videos = [_normalize_douyin_aweme(item) for item in aweme_list if isinstance(item, dict)]
    total = len(videos)
    qualified = sum(1 for item in videos if item["desc_qualified"])
    percent = round((qualified / total * 100), 2) if total else 0.0

    return {
        "profile": {
            "sec_user_id": sec_user_id or _first_text(user, "sec_uid", "sec_user_id", "uid"),
            "nickname": _first_text(user, "nickname", "unique_id"),
            "avatar_url": _first_url(user, "avatar_thumb", "avatar_medium", "avatar_larger"),
            "signature": _first_text(user, "signature"),
            "follower_count": _first_int(user, "follower_count"),
            "total_favorited": _first_int(user, "total_favorited"),
            "aweme_count": _first_int(user, "aweme_count"),
            "source_url": source_url,
        },
        "videos": videos,
        "desc_quality": {
            "total": total,
            "qualified": qualified,
            "qualified_percent": percent,
        },
        "pagination": {
            "has_more": bool(posts_response.get("has_more")),
            "max_cursor": posts_response.get("max_cursor"),
        },
    }


def is_desc_qualified(desc: str, *, min_chars: int = 80) -> bool:
    cleaned = re.sub(r"\s+", "", desc or "")
    if len(cleaned) < min_chars:
        return False
    sentence_marks = len(re.findall(r"[。！？!?\n]", desc or ""))
    return sentence_marks >= 2


def _normalize_douyin_aweme(item: dict[str, Any]) -> dict[str, Any]:
    desc = _first_text(item, "desc")
    statistics = item.get("statistics") if isinstance(item.get("statistics"), dict) else {}
    aweme_id = _first_text(item, "aweme_id", "id")
    return {
        "aweme_id": aweme_id,
        "video_url": _first_text(item, "share_url") or (f"https://www.douyin.com/video/{aweme_id}" if aweme_id else ""),
        "media_url": _extract_douyin_media_url(item),
        "audio_url": _extract_douyin_audio_url(item),
        "desc": desc,
        "desc_qualified": is_desc_qualified(desc),
        "create_time": item.get("create_time"),
        "cover_url": _first_nested_url(item, ("video", "cover"), ("video", "dynamic_cover"), ("video", "origin_cover")),
        "metrics": {
            "digg_count": _first_int(statistics, "digg_count"),
            "comment_count": _first_int(statistics, "comment_count"),
            "share_count": _first_int(statistics, "share_count"),
            "collect_count": _first_int(statistics, "collect_count"),
            "play_count": _first_int(statistics, "play_count"),
        },
    }


def transcribe_douyin_profile_video(
    *,
    media_url: str,
    aweme_id: str,
    title: str = "",
    user_id: int,
    project_id: int | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    clean_media_url = media_url.strip()
    if not clean_media_url:
        raise ValueError("media_url is required")
    _validate_douyin_media_url(clean_media_url)
    if not storage_service.is_oss_configured(settings):
        raise RuntimeError("OSS is not configured for Douyin ASR media persistence")

    downloaded = _download_douyin_media(clean_media_url)
    audio_path: str | None = None
    try:
        object_key = storage_service.build_reference_media_object_key(
            user_id=user_id,
            project_id=project_id,
            media_kind="videos",
            mime_type=downloaded.content_type,
        )
        object_key = storage_service.upload_bytes(
            object_key=object_key,
            content=downloaded.content,
            content_type=downloaded.content_type,
            settings=settings,
        )
        signed_url, expires_at = storage_service.sign_get_url(object_key, settings=settings)

        audio_path = _extract_audio_for_asr(downloaded.path)
        client = GPUWorkerClient.from_settings(settings)
        try:
            result = client.transcribe(audio_path, language="zh")
        except httpx.ConnectError as exc:
            raise RuntimeError(
                "ASR service connection failed; check GPU Worker or ASR_API_URL"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"ASR service returned error: {exc.response.status_code}") from exc

        text = str(result.get("text") or "").strip()
        if not text:
            raise RuntimeError("ASR service returned empty text")

        return {
            "aweme_id": aweme_id,
            "title": title,
            "text": text,
            "segments": result.get("segments") or [],
            "duration": result.get("duration"),
            "source_video_oss_key": object_key,
            "source_video_url": signed_url,
            "source_video_url_expires_at": expires_at,
        }
    finally:
        for path in (audio_path, downloaded.path):
            if path:
                try:
                    os.remove(path)
                except OSError:
                    pass


def parse_video_upload(
    file_content: bytes,
    filename: str,
    content_type: str,
    settings: Settings | None = None,
) -> VideoParseResult:
    settings = settings or get_settings()

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
    # First try Evil0ctal HybridCrawler (open-source parser with A-Bogus signatures)
    crawler_cls = _get_hybrid_crawler()
    if crawler_cls:
        try:
            crawler = crawler_cls()
            result = _run_async(crawler.hybrid_parsing_single_video(url, minimal=True))
            if result and isinstance(result, dict):
                desc = result.get("desc") or ""
                author_info = result.get("author") or {}
                author_name = ""
                if isinstance(author_info, dict):
                    author_name = author_info.get("nickname") or ""

                cover_data = result.get("cover_data") or {}
                cover = ""
                if isinstance(cover_data, dict):
                    cover_obj = cover_data.get("cover") or {}
                    if isinstance(cover_obj, dict):
                        cover = cover_obj.get("url_list", [""])[0] if cover_obj.get("url_list") else ""

                return VideoParseResult(
                    title=desc[:200] if desc else "未识别标题",
                    original_script=desc,
                    account_name=author_name or None,
                    cover_url=cover or None,
                    platform="douyin",
                    source_url=url,
                )
        except Exception as exc:
            logger.warning("Evil0ctal parser failed for %s: %s", url, exc)
            # Fall through to direct scraping

    # Fallback: direct scraping via RENDER_DATA
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

    title = (og_title_match.group(1) if og_title_match else "")
    desc = og_desc_match.group(1) if og_desc_match else ""
    if not title.strip() and not desc.strip():
        raise RuntimeError("抖音链接未解析到标题或原文，请使用本地上传或手动输入文案。")

    return VideoParseResult(
        title=title or "未识别标题",
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

    title = (og_title_match.group(1) if og_title_match else "")
    desc = og_desc_match.group(1) if og_desc_match else ""
    if not title.strip() and not desc.strip():
        raise RuntimeError("小红书链接未解析到标题或原文，请使用本地上传或手动输入文案。")

    return VideoParseResult(
        title=title or "未识别标题",
        original_script=desc or title,
        account_name=None,
        cover_url=og_image_match.group(1) if og_image_match else None,
        platform="xiaohongshu",
        source_url=url,
    )


def _transcribe_via_asr_api(
    file_path: str, filename: str, settings: Settings
) -> VideoParseResult:
    client = GPUWorkerClient.from_settings(settings)
    try:
        result = client.transcribe(file_path, language="zh")
    except httpx.ConnectError as exc:
        raise RuntimeError(
            "ASR 服务连接失败，请检查 GPU Worker 是否运行或 ASR_API_URL 配置是否正确。"
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"ASR 服务返回错误: {exc.response.status_code}") from exc

    text = result.get("text", "")
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


def _extract_douyin_media_url(item: dict[str, Any]) -> str:
    video = item.get("video") if isinstance(item.get("video"), dict) else {}
    bit_rates = video.get("bit_rate")
    if isinstance(bit_rates, list):
        ordered = sorted(
            [rate for rate in bit_rates if isinstance(rate, dict)],
            key=lambda rate: _first_int(rate.get("play_addr") if isinstance(rate.get("play_addr"), dict) else {}, "data_size")
            or _first_int(rate, "bit_rate")
            or 10**12,
        )
        for rate in ordered:
            if str(rate.get("format") or "").lower() not in {"", "mp4"}:
                continue
            url = _first_url_from_value(rate.get("play_addr"))
            if url:
                return url
    return _first_nested_url(item, ("video", "play_addr"))


def _extract_douyin_audio_url(item: dict[str, Any]) -> str:
    bit_rate_audio = _deep_get(item, "video", "bit_rate_audio")
    if not isinstance(bit_rate_audio, list):
        return ""
    for audio_item in bit_rate_audio:
        url = _first_url_from_value(_deep_get(audio_item, "audio_meta", "url_list"))
        if url:
            return url
    return ""


def _first_url_from_value(value: Any) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, list):
        for item in value:
            found = _first_url_from_value(item)
            if found:
                return found
    if isinstance(value, dict):
        urls = value.get("url_list")
        if isinstance(urls, list):
            for item in urls:
                found = _first_url_from_value(item)
                if found:
                    return found
        for key in ("main_url", "backup_url", "fallback_url"):
            found = _first_url_from_value(value.get(key))
            if found:
                return found
    return ""


def _validate_douyin_media_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http and https media URLs are supported")
    host = (parsed.hostname or "").lower()
    allowed = (
        host == "douyin.com"
        or host.endswith(".douyin.com")
        or host == "iesdouyin.com"
        or host.endswith(".iesdouyin.com")
        or host == "douyinvod.com"
        or host.endswith(".douyinvod.com")
    )
    if not allowed:
        raise ValueError("Only Douyin media URLs are supported")


def _download_douyin_media(url: str) -> DownloadedMedia:
    suffix = _guess_media_suffix(url, "video/mp4")
    content = bytearray()
    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name
            with httpx.stream(
                "GET",
                url,
                headers={**HEADERS, "Referer": "https://www.douyin.com/"},
                timeout=60.0,
                follow_redirects=True,
            ) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0].strip() or "video/mp4"
                for chunk in response.iter_bytes():
                    if not chunk:
                        continue
                    content.extend(chunk)
                    if len(content) > MAX_DOUYIN_MEDIA_BYTES:
                        raise RuntimeError("Douyin media is too large for ASR download")
                    tmp.write(chunk)
        return DownloadedMedia(path=tmp_path, content=bytes(content), content_type=content_type)
    except Exception:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise


def _extract_audio_for_asr(video_path: str) -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        audio_path = tmp.name
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                video_path,
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                audio_path,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180,
        )
        return audio_path
    except Exception:
        try:
            os.remove(audio_path)
        except OSError:
            pass
        raise


def _guess_media_suffix(url: str, content_type: str) -> str:
    lowered_type = content_type.lower()
    if "quicktime" in lowered_type:
        return ".mov"
    if "webm" in lowered_type:
        return ".webm"
    if "audio" in lowered_type or "m4a" in lowered_type:
        return ".m4a"
    path = urlparse(url).path.lower()
    for suffix in (".mp4", ".mov", ".m4v", ".webm", ".m4a"):
        if path.endswith(suffix):
            return suffix
    return ".mp4"


def _first_text(data: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if value is not None:
            text = str(value).strip()
            if text:
                return text
    return ""


def _first_int(data: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = data.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
    return 0


def _first_url(data: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            urls = value.get("url_list")
            if isinstance(urls, list) and urls:
                first = urls[0]
                if isinstance(first, str) and first.strip():
                    return first.strip()
    return ""


def _first_nested_url(data: dict[str, Any], *paths: tuple[str, ...]) -> str:
    for path in paths:
        value = _deep_get(data, *path)
        if isinstance(value, dict):
            found = _first_url({"value": value}, "value")
            if found:
                return found
        if isinstance(value, str) and value.strip():
            return value.strip()
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
