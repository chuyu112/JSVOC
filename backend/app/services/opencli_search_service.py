import json
import shlex
import subprocess
import time
from typing import Any

from app.core.config import Settings, get_settings
from app.models.project import Project
from app.schemas.hot_video import HotVideoSearchRequest


def search_hot_video_sources(
    payload: HotVideoSearchRequest,
    project: Project | None,
    *,
    settings: Settings | None = None,
) -> tuple[list[dict[str, Any]], int]:
    settings = settings or get_settings()
    template = settings.opencli_hot_video_search_command.strip()
    if not template:
        return [], 0

    query = build_search_query(payload, project)
    try:
        command = render_command_template(
            template,
            {
                "query": query,
                "keyword": payload.keyword,
                "platform": payload.platform,
                "focus": payload.search_focus,
                "count": str(payload.count),
                "project": project.project_name if project else "",
            },
        )
    except KeyError as exc:
        raise RuntimeError(f"OpenCLI command template has unknown placeholder: {exc}") from exc

    started_at = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=settings.opencli_search_timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"OpenCLI timed out after {settings.opencli_search_timeout_seconds} seconds") from exc
    latency_ms = int((time.perf_counter() - started_at) * 1000)

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()[:500]
        raise RuntimeError(detail or f"OpenCLI exited with code {completed.returncode}")

    results = parse_opencli_output(completed.stdout)
    return results[: payload.count], latency_ms


def build_search_query(payload: HotVideoSearchRequest, project: Project | None) -> str:
    parts = [payload.platform, payload.keyword, payload.search_focus, "热门视频"]
    if project is not None:
        parts.extend(
            [
                project.project_name,
                project.industry,
                project.sub_industry or "",
                project.product,
            ]
        )
    return " ".join(part.strip() for part in parts if part and part.strip())


def render_command_template(template: str, values: dict[str, str]) -> str:
    quoted = {key: shlex.quote(value) for key, value in values.items()}
    quoted.update({f"{key}_raw": value for key, value in values.items()})
    return template.format(**quoted)


def parse_opencli_output(output: str) -> list[dict[str, Any]]:
    content = output.strip()
    if not content:
        return []
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return parse_plain_output(content)
    return normalize_entries(extract_entries(parsed))


def parse_plain_output(content: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for line in content.splitlines():
        text = line.strip(" -\t")
        if text:
            items.append({"title": text, "source_title": text})
    return items


def extract_entries(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if not isinstance(value, dict):
        return []
    for key in ("items", "videos", "results", "data", "list", "records"):
        nested = value.get(key)
        if isinstance(nested, list):
            return nested
        extracted = extract_entries(nested)
        if extracted:
            return extracted
    return [value]


def normalize_entries(entries: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for entry in entries:
        if isinstance(entry, str):
            item = {"title": entry, "source_title": entry}
        elif isinstance(entry, dict):
            item = {
                "title": first_text(entry, "title", "name", "video_title", "text", "content"),
                "platform": first_text(entry, "platform", "site"),
                "creator": first_text(entry, "creator", "author", "account", "user", "nickname"),
                "source_url": first_text(entry, "source_url", "url", "link", "href"),
                "source_title": first_text(entry, "source_title", "page_title", "title", "name"),
                "publish_time": first_text(entry, "publish_time", "published_at", "date", "time"),
                "metrics": entry.get("metrics") if isinstance(entry.get("metrics"), dict) else {},
                "summary": first_text(entry, "summary", "description", "snippet", "content", "text"),
            }
        else:
            continue
        if item.get("title") or item.get("source_url"):
            normalized.append(item)
    return normalized


def first_text(entry: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = entry.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text[:500]
    return ""
