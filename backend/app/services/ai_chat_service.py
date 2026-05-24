import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.llm.llm_gateway import LLMGateway, LLMGatewayRequest, LLMGatewayResponse
from app.models.generation_record import GenerationRecord
from app.schemas.ai_chat import (
    AIChatConversationSummary,
    AIChatHistoryTurn,
    AIChatRequest,
    AIChatResponse,
)
from app.services import credit_service


AI_CHAT_MODULE = "ai_chat"
AI_CHAT_PROMPT_VERSION = "ai-chat-v1"
LEGACY_CONVERSATION_ID = "legacy"
LEGACY_CONVERSATION_TITLE = "历史聊天"


def generate_ai_chat_reply(
    db: Session,
    *,
    payload: AIChatRequest,
    user_id: int,
) -> AIChatResponse:
    credit_service.ensure_sufficient_credits(
        db,
        user_id,
        credit_service.AI_CHAT_MIN_GENERATION_COST,
    )
    conversation_id = normalize_conversation_id(payload.conversation_id)
    conversation_title = normalize_conversation_title(payload.conversation_title, payload.message)
    gateway_result = LLMGateway().generate(
        db=db,
        project_id=None,
        user_id=user_id,
        prompt_version=AI_CHAT_PROMPT_VERSION,
        request=LLMGatewayRequest(
            module_name=AI_CHAT_MODULE,
            system_prompt=build_system_prompt(web_search=payload.web_search),
            user_prompt=build_user_prompt(payload),
            temperature=0.55,
            max_tokens=1800,
            web_search=payload.web_search,
            metadata={
                "message": payload.message,
                "conversation_id": conversation_id,
                "conversation_title": conversation_title,
                "history_count": len(payload.history),
                "web_search": payload.web_search,
            },
        ),
    )
    if not gateway_result.success:
        raise RuntimeError(gateway_result.error or "AI chat failed")

    reply = extract_reply(gateway_result)
    if not reply:
        raise RuntimeError("AI chat returned empty reply")

    credit_cost = credit_service.ai_chat_generation_cost(gateway_result.usage)
    credit_service.charge_credits(
        db,
        user_id=user_id,
        cost=credit_cost,
        reason="ai_chat_generation",
        reference_type="generation_record",
        reference_id=gateway_result.generation_record_id,
        metadata={
            "module": AI_CHAT_MODULE,
            "total_tokens": credit_service.token_usage_total(gateway_result.usage),
            "web_search": payload.web_search,
            "conversation_id": conversation_id,
        },
    )

    return AIChatResponse(
        reply=reply,
        provider=gateway_result.provider,
        model=gateway_result.model,
        usage=gateway_result.usage,
        sources=gateway_result.sources,
        latency_ms=gateway_result.latency_ms,
        generation_record_id=gateway_result.generation_record_id,
        conversation_id=conversation_id,
        conversation_title=conversation_title,
    )


def list_ai_chat_conversations(
    db: Session,
    *,
    user_id: int,
    limit: int = 50,
) -> list[AIChatConversationSummary]:
    records = get_recent_ai_chat_records(db, user_id=user_id, limit=max(limit * 12, 200))
    summaries: dict[str, AIChatConversationSummary] = {}

    for record in records:
        turn = generation_record_to_history_turn(record)
        if turn is None:
            continue

        existing = summaries.get(turn.conversation_id)
        if existing is None:
            summaries[turn.conversation_id] = AIChatConversationSummary(
                conversation_id=turn.conversation_id,
                title=turn.conversation_title,
                last_user_message=turn.user_message,
                last_assistant_message=turn.assistant_message,
                turn_count=1,
                created_at=record.created_at,
                updated_at=record.created_at,
            )
            continue

        existing.turn_count += 1
        if record.created_at < existing.created_at:
            existing.created_at = record.created_at

    ordered = sorted(summaries.values(), key=lambda item: item.updated_at, reverse=True)
    return ordered[:limit]


def list_ai_chat_history(
    db: Session,
    *,
    user_id: int,
    limit: int = 20,
    conversation_id: str | None = None,
) -> list[AIChatHistoryTurn]:
    records = get_recent_ai_chat_records(db, user_id=user_id, limit=max(limit * 12, 200))
    normalized_conversation_id = (
        normalize_conversation_id(conversation_id) if conversation_id is not None else None
    )

    turns: list[AIChatHistoryTurn] = []
    for record in records:
        turn = generation_record_to_history_turn(record)
        if turn is None:
            continue
        if normalized_conversation_id is not None and turn.conversation_id != normalized_conversation_id:
            continue
        turns.append(turn)
        if len(turns) >= limit:
            break

    return list(reversed(turns))


def get_recent_ai_chat_records(db: Session, *, user_id: int, limit: int) -> list[GenerationRecord]:
    statement = (
        select(GenerationRecord)
        .where(
            GenerationRecord.user_id == user_id,
            GenerationRecord.module_name == AI_CHAT_MODULE,
        )
        .order_by(GenerationRecord.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def generation_record_to_history_turn(record: GenerationRecord) -> AIChatHistoryTurn | None:
    input_data = record.input_data if isinstance(record.input_data, dict) else {}
    output_data = record.output_data if isinstance(record.output_data, dict) else {}
    if output_data.get("success") is False:
        return None

    user_message = extract_user_message_from_input(input_data)
    assistant_message = extract_assistant_message_from_output(output_data)
    if not user_message or not assistant_message:
        return None

    metadata = input_data.get("metadata") if isinstance(input_data.get("metadata"), dict) else {}
    conversation_id = normalize_conversation_id(metadata.get("conversation_id"))
    conversation_title = normalize_record_conversation_title(metadata, user_message)
    return AIChatHistoryTurn(
        generation_record_id=record.id,
        conversation_id=conversation_id,
        conversation_title=conversation_title,
        user_message=user_message,
        assistant_message=assistant_message,
        provider=record.model_provider,
        model=record.model_name,
        web_search=bool(metadata.get("web_search")),
        latency_ms=record.latency_ms,
        created_at=record.created_at,
    )


def normalize_conversation_id(value: Any) -> str:
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            return cleaned[:80]
    return LEGACY_CONVERSATION_ID


def normalize_conversation_title(value: str | None, fallback_message: str) -> str:
    if isinstance(value, str) and value.strip():
        return compact_text(value, 40)
    return compact_text(fallback_message, 40)


def normalize_record_conversation_title(metadata: dict[str, Any], fallback_message: str) -> str:
    conversation_title = metadata.get("conversation_title")
    if isinstance(conversation_title, str) and conversation_title.strip():
        return compact_text(conversation_title, 40)

    conversation_id = normalize_conversation_id(metadata.get("conversation_id"))
    if conversation_id == LEGACY_CONVERSATION_ID:
        return LEGACY_CONVERSATION_TITLE
    return compact_text(fallback_message, 40)


def extract_user_message_from_input(input_data: dict[str, Any]) -> str:
    metadata = input_data.get("metadata") if isinstance(input_data.get("metadata"), dict) else {}
    raw_message = metadata.get("message")
    if isinstance(raw_message, str) and raw_message.strip():
        return raw_message.strip()

    user_prompt = input_data.get("user_prompt")
    if not isinstance(user_prompt, str):
        return ""

    marker = "当前问题："
    marker_index = user_prompt.rfind(marker)
    if marker_index >= 0:
        return user_prompt[marker_index + len(marker) :].strip()
    return ""


def extract_assistant_message_from_output(output_data: dict[str, Any]) -> str:
    content = output_data.get("content")
    data = output_data.get("data")

    if isinstance(content, str) and content.strip() and not content.strip().startswith(("{", "[")):
        return content.strip()

    reply_from_data = extract_text_from_data(data)
    if reply_from_data:
        return reply_from_data

    if isinstance(content, str) and content.strip():
        reply_from_content_json = extract_text_from_json_string(content)
        if reply_from_content_json:
            return reply_from_content_json
        return content.strip()

    return ""


def extract_text_from_data(data: Any) -> str:
    if not isinstance(data, dict):
        return ""
    for key in ("reply", "answer", "text"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def extract_text_from_json_string(value: str) -> str:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return ""
    return extract_text_from_data(parsed)


def build_system_prompt(*, web_search: bool = False) -> str:
    prompt = (
        "你是 JPASP 短视频运营中心的 AI 聊天助手。"
        "你服务于账号策略、项目档案、账号包装、执行计划、选题、文案、生图提示词、生视频提示词和数字资产管理。"
        "回复必须使用中文，直接、可执行、少空话。"
        "如果用户的问题需要到某个功能模块继续处理，直接指出模块名称和下一步动作。"
        "不要编造后台数据、任务状态或资产记录；没有上下文时明确说明需要用户补充或到对应模块查询。"
    )
    if web_search:
        prompt += "联网搜索已开启。涉及实时信息时必须基于搜索结果回答；不确定时说明来源限制，并尽量给出可核对的来源。"
    return prompt


def build_user_prompt(payload: AIChatRequest) -> str:
    history_lines = []
    for item in payload.history[-20:]:
        role = "用户" if item.role == "user" else "助手"
        history_lines.append(f"{role}: {compact_text(item.content, 1200)}")

    history_text = "\n".join(history_lines) if history_lines else "无"
    return (
        "以下是当前聊天上下文，请基于上下文回答最后一个问题。\n\n"
        f"历史对话：\n{history_text}\n\n"
        f"当前问题：\n{payload.message}"
    )


def compact_text(value: str, limit: int) -> str:
    cleaned = " ".join(value.strip().split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit]}..."


def extract_reply(result: LLMGatewayResponse) -> str:
    content = result.content.strip()
    if content and not content.startswith("{") and not content.startswith("["):
        return content

    data = result.data
    if isinstance(data, dict):
        for key in ("reply", "answer", "text"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        if data and content.startswith("{"):
            return format_dict_reply(data)
    return content


def format_dict_reply(data: dict[str, Any]) -> str:
    for key, value in data.items():
        if isinstance(value, (str, int, float)) and str(value).strip():
            return str(value).strip()
    return ""
