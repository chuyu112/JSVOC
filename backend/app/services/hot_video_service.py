import json
from typing import Any

from sqlalchemy.orm import Session

from app.llm.llm_gateway import LLMGateway, LLMGatewayRequest, LLMGatewayResponse
from app.models.project import Project
from app.schemas.hot_video import HotVideoItem, HotVideoSearchRequest, HotVideoSearchResponse
from app.services import opencli_search_service, project_service


HOT_VIDEO_MODULE = "hot_video_search"
HOT_VIDEO_PROMPT_VERSION = "hot-video-search-v1"


HOT_VIDEO_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "platform": {"type": "string"},
                    "creator": {"type": "string"},
                    "source_url": {"type": "string"},
                    "source_title": {"type": "string"},
                    "publish_time": {"type": "string"},
                    "metrics": {"type": "object"},
                    "why_trending": {"type": "string"},
                    "hook": {"type": "string"},
                    "structure": {"type": "array", "items": {"type": "string"}},
                    "remake_angle": {"type": "string"},
                    "rewrite_brief": {"type": "string"},
                    "risk_notes": {"type": "array", "items": {"type": "string"}},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
            },
        }
    },
    "required": ["items"],
}


def search_hot_videos(
    db: Session,
    *,
    payload: HotVideoSearchRequest,
    user_id: int,
) -> HotVideoSearchResponse:
    project: Project | None = None
    if payload.project_id is not None:
        project = project_service.get_project_for_user(db, payload.project_id, user_id)
        if project is None:
            raise ValueError("项目不存在")

    gateway = LLMGateway()
    search_provider = gateway.settings.hot_video_search_provider.strip().lower() or "auto"
    opencli_results: list[dict[str, Any]] = []
    opencli_latency_ms = 0
    if search_provider in {"auto", "opencli"}:
        if search_provider == "opencli" and not gateway.settings.opencli_hot_video_search_command.strip():
            raise RuntimeError("OpenCLI 热门视频搜索未配置 OPENCLI_HOT_VIDEO_SEARCH_COMMAND")
        try:
            opencli_results, opencli_latency_ms = opencli_search_service.search_hot_video_sources(
                payload,
                project,
                settings=gateway.settings,
            )
        except RuntimeError as exc:
            if search_provider == "opencli":
                raise RuntimeError(f"OpenCLI 热门视频搜索失败: {exc}") from exc
            opencli_results = []
            opencli_latency_ms = 0

    using_opencli = bool(opencli_results)
    gateway_result = gateway.generate(
        db=db,
        project_id=project.id if project else None,
        user_id=user_id,
        prompt_version=HOT_VIDEO_PROMPT_VERSION,
        request=LLMGatewayRequest(
            module_name=HOT_VIDEO_MODULE,
            system_prompt=build_system_prompt(),
            user_prompt=build_user_prompt(payload, project, opencli_results if using_opencli else None),
            output_schema=HOT_VIDEO_OUTPUT_SCHEMA,
            temperature=0.35,
            max_tokens=2600,
            web_search=not using_opencli,
            web_search_context_size=payload.web_search_context_size,
            metadata={
                "project_id": payload.project_id,
                "platform": payload.platform,
                "keyword": payload.keyword,
                "search_focus": payload.search_focus,
                "count": payload.count,
                "search_provider": "opencli" if using_opencli else "llm_web_search",
                "opencli_result_count": len(opencli_results),
            },
        ),
    )
    if not gateway_result.success:
        raise RuntimeError(gateway_result.error or "热门视频搜索失败")

    items = normalize_hot_video_items(gateway_result.data, gateway_result, payload)
    usage = dict(gateway_result.usage or {})
    if using_opencli:
        usage.setdefault("search_provider", "opencli")
        usage.setdefault("opencli_latency_ms", opencli_latency_ms)
    sources = gateway_result.sources or sources_from_opencli_results(opencli_results)

    return HotVideoSearchResponse(
        items=items,
        provider=gateway_result.provider,
        model=gateway_result.model,
        usage=usage,
        sources=sources,
        latency_ms=gateway_result.latency_ms,
        generation_record_id=gateway_result.generation_record_id,
    )


def build_system_prompt() -> str:
    return (
        "你是 JSVOC 的短视频爆款研究员，负责把公开视频搜索结果拆成可复用的创作策略。"
        "必须使用中文输出。必须基于联网搜索结果，不要编造具体播放量、点赞量、作者或链接。"
        "如果搜索结果没有明确数据，metrics 字段留空或写 unknown。"
        "重点不是搬运原视频，而是做合规拆解：钩子、结构、情绪、转化点、二创角度。"
        "输出必须是严格 JSON，形如 {\"items\": [...]}。"
    )


def build_user_prompt(
    payload: HotVideoSearchRequest,
    project: Project | None,
    search_results: list[dict[str, Any]] | None = None,
) -> str:
    project_context = "无项目上下文"
    if project is not None:
        project_context = (
            f"项目名：{project.project_name}\n"
            f"行业：{project.industry} / {project.sub_industry or ''}\n"
            f"产品：{project.product}\n"
            f"人设/简介：{project.personal_intro}\n"
            f"目标客户：{project.target_audience}\n"
            f"运营平台：{'、'.join(project.platforms)}\n"
            f"账号阶段：{project.current_stage}"
        )

    search_context = ""
    if search_results:
        rows = []
        for index, result in enumerate(search_results, start=1):
            rows.append(
                "\n".join(
                    [
                        f"{index}. title: {result.get('title', '')}",
                        f"   url: {result.get('source_url', '')}",
                        f"   source_title: {result.get('source_title', '')}",
                        f"   creator: {result.get('creator', '')}",
                        f"   publish_time: {result.get('publish_time', '')}",
                        f"   metrics: {json.dumps(result.get('metrics') or {}, ensure_ascii=False)}",
                        f"   summary: {result.get('summary', '')}",
                    ]
                )
            )
        search_context = (
            "\n公开搜索结果（来自 OpenCLI，必须优先基于这些事实拆解；"
            "没有给出的播放量、点赞量、作者和链接不要编造）：\n"
            + "\n".join(rows)
            + "\n"
        )

    return f"""
请搜索并拆解近期与以下条件相关的热门短视频素材。

项目上下文：
{project_context}
{search_context}

搜索条件：
- 平台：{payload.platform}
- 关键词：{payload.keyword}
- 研究重点：{payload.search_focus}
- 返回数量：{payload.count}

每条结果输出字段：
- title：视频/素材标题或搜索结果标题
- platform：平台
- creator：作者/账号名，未知则空字符串
- source_url：可核对链接，必须来自搜索结果，未知则空字符串
- source_title：来源页面标题
- publish_time：发布时间，未知则空字符串
- metrics：播放、点赞、评论、收藏等公开指标；没有公开数据就留空对象
- why_trending：为什么可能热门，必须结合搜索结果和短视频规律
- hook：可学习的开头钩子
- structure：3-6 步内容结构
- remake_angle：结合本项目可以怎么二创/洗稿，不能照搬原文
- rewrite_brief：可以交给文案模块继续生成的洗稿简报
- risk_notes：版权、隐私、平台风险提醒
- tags：3-8 个标签

只输出 JSON，不要 Markdown。
"""


def sources_from_opencli_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    seen: set[str] = set()
    for result in results:
        url = clean_text(result.get("source_url", ""), 800)
        title = clean_text(result.get("source_title") or result.get("title") or "OpenCLI source")
        if not url and not title:
            continue
        key = url or title
        if key in seen:
            continue
        seen.add(key)
        sources.append({"url": url, "title": title, "provider": "opencli"})
    return sources


def normalize_hot_video_items(
    data: Any,
    result: LLMGatewayResponse,
    payload: HotVideoSearchRequest,
) -> list[HotVideoItem]:
    raw_items = extract_raw_items(data)
    if not raw_items and isinstance(result.content, str):
        raw_items = extract_raw_items({"text": result.content})

    items: list[HotVideoItem] = []
    for raw in raw_items[: payload.count]:
        if not isinstance(raw, dict):
            raw = {"title": str(raw)}
        item = HotVideoItem(
            title=clean_text(first_value(raw, "title", "video_title", "name")),
            platform=clean_text(first_value(raw, "platform")) or payload.platform,
            creator=clean_text(first_value(raw, "creator", "account", "author")),
            source_url=clean_text(first_value(raw, "source_url", "url", "link")),
            source_title=clean_text(first_value(raw, "source_title", "source", "page_title")),
            publish_time=clean_text(first_value(raw, "publish_time", "published_at", "date")),
            metrics=raw.get("metrics") if isinstance(raw.get("metrics"), dict) else {},
            why_trending=clean_text(first_value(raw, "why_trending", "reason", "analysis")),
            hook=clean_text(first_value(raw, "hook", "opening", "opening_hook")),
            structure=to_string_list(first_value(raw, "structure", "content_structure", "steps")),
            remake_angle=clean_text(first_value(raw, "remake_angle", "rewrite_angle", "adaptation")),
            rewrite_brief=clean_text(first_value(raw, "rewrite_brief", "brief", "script_brief")),
            risk_notes=to_string_list(first_value(raw, "risk_notes", "risks", "risk")),
            tags=to_string_list(first_value(raw, "tags", "keywords")),
        )
        if item.title or item.source_url or item.remake_angle:
            items.append(item)
    return items


def extract_raw_items(data: Any) -> list[Any]:
    if isinstance(data, list):
        return data
    if isinstance(data, str):
        parsed = parse_json_text(data)
        return extract_raw_items(parsed)
    if not isinstance(data, dict):
        return []
    for key in ("items", "videos", "results", "hot_videos", "list"):
        value = data.get(key)
        if isinstance(value, list):
            return value
        nested = extract_raw_items(value)
        if nested:
            return nested
    for key in ("data", "result", "output", "content", "text"):
        nested = extract_raw_items(data.get(key))
        if nested:
            return nested
    return []


def parse_json_text(value: str) -> Any:
    content = value.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        if len(lines) >= 2:
            if lines[-1].strip().startswith("```"):
                content = "\n".join(lines[1:-1]).strip()
            else:
                content = "\n".join(lines[1:]).strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {}


def first_value(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = item.get(key)
        if value is not None:
            return value
    return None


def clean_text(value: Any, limit: int = 500) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1]


def to_string_list(value: Any, limit: int = 8) -> list[str]:
    if isinstance(value, list):
        values = value
    elif value is None or value == "":
        values = []
    else:
        values = [value]
    return [clean_text(item, 240) for item in values if clean_text(item, 240)][:limit]
