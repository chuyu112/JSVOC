import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, wait
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.llm.llm_gateway import LLMGateway, LLMGatewayRequest, LLMGatewayResponse
from app.models.project import Project
from app.models.topic import Topic
from app.prompts.topic_prompt import (
    TOPICS_MODULE,
    TOPICS_OUTPUT_SCHEMA,
    TOPICS_PROMPT_VERSION,
    build_topic_prompts,
)
from app.schemas.topic import TopicBatchGenerateRequest, TopicCreate, TopicGenerateRequest
from app.services import account_strategy_context_service, credit_service, project_service


TOPIC_COPY_MAX_LENGTH = 200


class TopicGeneration:
    def __init__(self, topics: list[Topic], gateway_result: LLMGatewayResponse):
        self.topics = topics
        self.gateway_result = gateway_result


def generate_topics(
    db: Session,
    payload: TopicGenerateRequest,
    user_id: int,
    project: Project | None = None,
) -> TopicGeneration | None:
    project = project or project_service.get_project_for_user(db, payload.project_id, user_id)
    if project is None:
        return None

    strategy_context = account_strategy_context_service.get_latest_account_strategy_context(
        db,
        payload.project_id,
    )
    account_package_extras: dict[str, Any] = {}
    if strategy_context is not None and strategy_context.context_data:
        account_package_extras = strategy_context.context_data.get("account_package_extras") or {}
    system_prompt, user_prompt = build_topic_prompts(
        project,
        strategy_context,
        payload.platform,
        payload.goal,
        payload.content_format,
        payload.count,
        payload.existing_titles,
        payload.topic_index,
        get_project_topics(db, project.id, limit=50),
        payload.persona_reference_image_uploaded,
        benchmark_samples=project.benchmark_samples,
        account_package_extras=account_package_extras,
    )
    gateway_result = LLMGateway().generate(
        db=db,
        project_id=project.id,
        user_id=user_id,
        prompt_version=TOPICS_PROMPT_VERSION,
        request=LLMGatewayRequest(
            module_name=TOPICS_MODULE,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=TOPICS_OUTPUT_SCHEMA,
            temperature=payload.temperature,
            metadata={
                "project_id": project.id,
                "platform": payload.platform,
                "goal": payload.goal,
                "content_format": payload.content_format,
                "count": payload.count,
                "existing_titles": payload.existing_titles,
                "topic_index": payload.topic_index,
                "generation_batch_id": payload.generation_batch_id,
                "generation_target_count": payload.generation_target_count,
                "persona_reference_image_uploaded": payload.persona_reference_image_uploaded,
                "industry": project.industry,
                "product": project.product,
                "account_strategy_context_id": strategy_context.id if strategy_context else None,
            },
        ),
    )
    if not gateway_result.success:
        return TopicGeneration(topics=[], gateway_result=gateway_result)

    topic_inputs = normalize_topics(gateway_result.data, payload)
    topics = create_topics(db, topic_inputs)
    return TopicGeneration(topics=topics, gateway_result=gateway_result)


BATCH_SIZE = 4
BATCH_CONCURRENCY = 3
BATCH_TIMEOUT_SECONDS = 60


def generate_topics_batch(
    db: Session,
    payload: TopicBatchGenerateRequest,
    user_id: int,
) -> dict[str, Any]:
    project = project_service.get_project_for_user(db, payload.project_id, user_id)
    if project is None:
        return {
            "topics": [],
            "generated_count": 0,
            "target_count": payload.target_count,
            "provider": "",
            "model": "",
            "latency_ms": 0,
        }

    import math
    import uuid

    existing = get_project_topics(db, payload.project_id, limit=200)
    existing_titles = [t.title for t in existing][:100]

    provider = ""
    model = ""
    total_tokens = 0

    if payload.target_count <= 10:
        batch_size = 3
    elif payload.target_count <= 20:
        batch_size = 4
    else:
        batch_size = 5

    start_time = time.time()
    all_topics: list[Topic] = []
    batch_id = str(uuid.uuid4())[:8]
    round_num = 0

    while len(all_topics) < payload.target_count:
        round_num += 1
        remaining = payload.target_count - len(all_topics)
        worker_count = min(BATCH_CONCURRENCY, math.ceil(remaining / batch_size))

        futures = []
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            for i in range(worker_count):
                sub_payload = TopicGenerateRequest(
                    project_id=payload.project_id,
                    platform=payload.platform,
                    goal=payload.goal,
                    content_format=payload.content_format,
                    count=batch_size,
                    temperature=payload.temperature,
                    topic_index=round_num * BATCH_CONCURRENCY + i + 1,
                    existing_titles=list(existing_titles)[-100:],
                    persona_reference_image_uploaded=payload.persona_reference_image_uploaded,
                    generation_batch_id=batch_id,
                    generation_target_count=payload.target_count,
                )
                futures.append(
                    executor.submit(_generate_topics_worker, sub_payload, user_id)
                )

            done, _not_done = wait(futures, timeout=BATCH_TIMEOUT_SECONDS)

        round_topics: list[Topic] = []
        for future in done:
            try:
                result = future.result(timeout=5)
                if result and result.gateway_result.success:
                    round_topics.extend(result.topics)
                    total_tokens += credit_service.token_usage_total(result.gateway_result.usage)
                    if not provider:
                        provider = result.gateway_result.provider
                        model = result.gateway_result.model
            except Exception:
                pass

        if not round_topics:
            break

        all_topics.extend(round_topics)
        existing_titles.extend([t.title for t in round_topics])
        existing_titles = existing_titles[-200:]

        if time.time() - start_time > BATCH_TIMEOUT_SECONDS * 2:
            break

    all_topics = all_topics[: payload.target_count]

    elapsed = int((time.time() - start_time) * 1000)

    return {
        "topics": all_topics,
        "generated_count": len(all_topics),
        "target_count": payload.target_count,
        "provider": provider or "openai_compatible",
        "model": model or "gpt-5.5",
        "latency_ms": elapsed,
        "usage": {"total_tokens": total_tokens},
    }


def _generate_topics_worker(
    payload: TopicGenerateRequest,
    user_id: int,
) -> TopicGeneration | None:
    with SessionLocal() as db:
        return generate_topics(db, payload, user_id)


def create_topics(db: Session, topics_in: list[TopicCreate]) -> list[Topic]:
    topics = [Topic(**topic_in.model_dump()) for topic_in in topics_in]
    db.add_all(topics)
    db.commit()
    for topic in topics:
        db.refresh(topic)
    return topics


def get_project_topics(
    db: Session,
    project_id: int,
    skip: int = 0,
    limit: int = 100,
) -> list[Topic]:
    statement = (
        select(Topic)
        .where(Topic.project_id == project_id)
        .order_by(Topic.is_favorite.desc(), Topic.created_at.desc(), Topic.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def get_topic(db: Session, topic_id: int) -> Topic | None:
    return db.get(Topic, topic_id)


def get_topic_for_user(db: Session, topic_id: int, user_id: int) -> Topic | None:
    statement = (
        select(Topic)
        .join(Project, Topic.project_id == Project.id)
        .where(Topic.id == topic_id, Project.user_id == user_id)
    )
    return db.scalars(statement).first()


def update_topic_favorite(db: Session, topic_id: int, is_favorite: bool) -> Topic | None:
    topic = get_topic(db, topic_id)
    if topic is None:
        return None

    topic.is_favorite = is_favorite
    db.add(topic)
    db.commit()
    db.refresh(topic)
    return topic


def delete_topic(db: Session, topic_id: int) -> bool:
    topic = get_topic(db, topic_id)
    if topic is None:
        return False

    db.delete(topic)
    db.commit()
    return True


def normalize_topics(data: Any, payload: TopicGenerateRequest) -> list[TopicCreate]:
    raw_topics = extract_raw_topics(data)

    topics: list[TopicCreate] = []
    for index, item in enumerate(raw_topics[: payload.count], start=1):
        if not isinstance(item, dict):
            item = {"title": str(item)}

        title = limit_topic_copy(first_value(item, "title", "topic", "topic_title") or f"选题 {index}")
        content_type = str(first_value(item, "content_type", "type", "category") or "选题")
        raw_rubric = item.get("rubric") or {}
        raw_hkr = item.get("hkr") or {}
        topic_data = {
            "content_format": payload.content_format,
            "user_pain_point": limit_topic_copy(
                first_value(item, "user_pain_point", "pain_point", "user_pain", "pain") or ""
            ),
            "hook": limit_topic_copy(
                first_value(item, "hook", "opening_hook", "opening", "first_sentence") or ""
            ),
            "shooting_suggestion": limit_topic_copy(
                first_value(item, "shooting_suggestion", "shooting_task", "shooting_advice") or ""
            ),
            "conversion_method": limit_topic_copy(
                first_value(item, "conversion_method", "conversion_path", "conversion") or ""
            ),
            "shooting_script": limit_topic_copy(
                first_value(item, "shooting_script", "video_script", "script", "拍摄脚本") or ""
            ),
            "seedance_video_prompt": limit_topic_copy(
                normalize_visual_prompt(
                    first_value(
                        item,
                        "seedance_video_prompt",
                        "seedance_prompt",
                        "seedance_prompt",
                        "video_prompt",
                    )
                    or "",
                    payload.content_format,
                    title,
                    content_type,
                    payload.persona_reference_image_uploaded,
                )
            ),
            "image_prompt": limit_topic_copy(
                normalize_visual_prompt(
                    first_value(item, "image_prompt", "image_generation_prompt", "picture_prompt") or "",
                    payload.content_format,
                    title,
                    content_type,
                    payload.persona_reference_image_uploaded,
                )
            ),
            "image_edit_prompt": limit_topic_copy(
                normalize_visual_prompt(
                    first_value(
                        item,
                        "image_edit_prompt",
                        "image_to_image_prompt",
                        "reference_image_prompt",
                    )
                    or "",
                    payload.content_format,
                    title,
                    content_type,
                    payload.persona_reference_image_uploaded,
                )
            ),
            "rubric": {
                "er": _ensure_int_score(raw_rubric.get("er")),
                "sr": _ensure_int_score(raw_rubric.get("sr")),
                "hp": _ensure_int_score(raw_rubric.get("hp")),
                "ql": _ensure_int_score(raw_rubric.get("ql")),
                "na": _ensure_int_score(raw_rubric.get("na")),
                "ab": _ensure_int_score(raw_rubric.get("ab")),
                "sat": _ensure_int_score(raw_rubric.get("sat")),
            },
            "hkr": {
                "h": _ensure_int_score(raw_hkr.get("h")),
                "k": _ensure_int_score(raw_hkr.get("k")),
                "r": _ensure_int_score(raw_hkr.get("r")),
            },
        }
        topics.append(
            TopicCreate(
                project_id=payload.project_id,
                title=title,
                content_type=content_type,
                platform=str(item.get("platform") or payload.platform),
                goal=str(item.get("goal") or payload.goal),
                selling_point=limit_topic_copy(
                    first_value(item, "selling_point", "value_point")
                    or topic_data["conversion_method"]
                    or ""
                ),
                score=ensure_score(item.get("score")),
                topic_data=topic_data,
            )
        )

    return topics


def normalize_visual_prompt(
    value: Any,
    content_format: str,
    title: str,
    content_type: str,
    persona_reference_image_uploaded: bool,
) -> str:
    prompt = str(value or "").strip()
    if persona_reference_image_uploaded:
        return prompt
    if content_format not in {"video_spoken", "video_script", "video", "image", "image_to_image"}:
        return prompt
    if not prompt:
        return ""
    if not contains_persona_visual_cue(prompt):
        return prompt
    return build_non_persona_visual_prompt(title, content_type, content_format)


def contains_persona_visual_cue(prompt: str) -> bool:
    text = prompt.strip()
    if re.search(r"\d{2}\s*岁.{0,12}(女性|男性|女士|男士|女人|男人|姐姐|大姐|哥|大哥)", text):
        return True
    if re.search(r"[一二三四五六七八九十]{2,3}\s*岁.{0,12}(女性|男性|女士|男士|女人|男人|姐姐|大姐|哥|大哥)", text):
        return True
    if re.search(r"（[^）]{0,20}(姐|哥|老师|老板|创始人|本人|人设)[^）]{0,20}）", text):
        return True
    return any(
        term in text
        for term in (
            "人设本人",
            "本人出镜",
            "本人正脸",
            "创始人本人",
            "老板本人",
            "苹果姐",
        )
    )


def build_non_persona_visual_prompt(title: str, content_type: str, content_format: str) -> str:
    mode_hint = {
        "video": "短视频画面",
        "image": "图片画面",
        "image_to_image": "参考图改图画面",
    }.get(content_format, "画面")
    return (
        f"{mode_hint}：围绕“{title}”呈现货品主体、真实场景、道具、光线和细节，突出{content_type}；"
        "如需出现人物，只使用非人设手模/工作人员的手部、背影或局部动作，"
        "不得出现人设本人、姓名、昵称、年龄、正脸或可识别身份。"
    )


def limit_topic_copy(value: Any, max_length: int = TOPIC_COPY_MAX_LENGTH) -> str:
    text = str(value or "").strip()
    if len(text) < max_length:
        return text
    return text[: max_length - 1]


def extract_raw_topics(data: Any) -> list[Any]:
    if isinstance(data, list):
        return data
    if isinstance(data, str):
        parsed = parse_json_text(data)
        parsed_topics = extract_raw_topics(parsed)
        if parsed_topics:
            return parsed_topics
        return extract_jsonish_topics(data)
    if not isinstance(data, dict):
        return []

    for key in ("topics", "topic_list", "topic_ideas", "items", "list"):
        if key not in data:
            continue
        value = data.get(key)
        if isinstance(value, list):
            return value
        if is_topic_like(value):
            return [value]
        nested = extract_raw_topics(value)
        if nested:
            return nested

    for key in ("data", "result", "output", "content", "text"):
        nested = extract_raw_topics(data.get(key))
        if nested:
            return nested

    if is_topic_like(data):
        return [data]
    return []


def parse_json_text(value: str) -> Any:
    content = strip_markdown_json_fence(value.strip())
    extracted = extract_first_json_value(content)
    if extracted is None:
        return {}

    try:
        return json.loads(extracted)
    except json.JSONDecodeError:
        return {}


def strip_markdown_json_fence(content: str) -> str:
    if not content.startswith("```"):
        return content

    lines = content.splitlines()
    if len(lines) >= 2 and lines[0].startswith("```"):
        if lines[-1].strip().startswith("```"):
            return "\n".join(lines[1:-1]).strip()
        return "\n".join(lines[1:]).strip()
    return content


def extract_first_json_value(content: str) -> str | None:
    starts = [index for index in (content.find("{"), content.find("[")) if index >= 0]
    if not starts:
        return None

    start = min(starts)
    opener = content[start]
    closer = "}" if opener == "{" else "]"
    depth = 0
    in_string = False
    escaped = False

    for index in range(start, len(content)):
        char = content[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return content[start : index + 1]

    return None


def extract_jsonish_topics(value: str) -> list[dict[str, Any]]:
    content = strip_markdown_json_fence(value.strip())
    objects = extract_jsonish_objects(content)
    topics: list[dict[str, Any]] = []
    for item in objects:
        topic = parse_jsonish_topic_object(item)
        if is_topic_like(topic):
            topics.append(topic)
    return topics


def extract_jsonish_objects(content: str) -> list[str]:
    topics_index = content.find('"topics"')
    if topics_index < 0:
        return []

    array_start = content.find("[", topics_index)
    if array_start < 0:
        return []

    objects: list[str] = []
    depth = 0
    start: int | None = None
    in_string = False
    escaped = False
    for index in range(array_start + 1, len(content)):
        char = content[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    objects.append(content[start : index + 1])
                    start = None
        elif char == "]" and depth == 0:
            break

    return objects


def parse_jsonish_topic_object(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass

    topic: dict[str, Any] = {}
    for key in (
        "title",
        "content_type",
        "platform",
        "goal",
        "selling_point",
        "user_pain_point",
        "hook",
        "shooting_suggestion",
        "conversion_method",
        "score",
    ):
        value = extract_jsonish_field(content, key)
        if value is not None:
            topic[key] = ensure_score(value) if key == "score" else value
    return topic


def extract_jsonish_field(content: str, key: str) -> str | None:
    quoted = re.search(rf'"{re.escape(key)}"\s*:\s*"((?:\\.|[^"\\])*)"', content, re.DOTALL)
    if quoted:
        return quoted.group(1).replace('\\"', '"').strip()

    unquoted = re.search(
        rf'"{re.escape(key)}"\s*:\s*(.*?)(?=,\s*"[\w_+"\u4e00-\u9fff]+"\s*:|\n\s*}}|}})',
        content,
        re.DOTALL,
    )
    if not unquoted:
        return None

    value = unquoted.group(1).strip().rstrip(",").strip()
    if not value:
        return None
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    return value.strip()


def is_topic_like(value: Any) -> bool:
    return isinstance(value, dict) and bool(
        {"title", "topic", "topic_title", "hook", "user_pain_point", "shooting_suggestion"}
        & set(value.keys())
    )


def first_value(item: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = item.get(key)
        if value is not None:
            return value
    return None


def ensure_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def ensure_score(value: Any) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return 0
    return min(100, max(0, score))


def _ensure_int_score(value: Any) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return 0
    return min(5, max(0, score))
