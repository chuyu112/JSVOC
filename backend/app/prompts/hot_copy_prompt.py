import json
from typing import Any

from app.models.hot_copy import HotCopyMaterial
from app.models.project import Project
from app.schemas.hot_copy import HotCopyRewriteRequest


HOT_COPY_ANALYSIS_MODULE = "hot_copy_analysis"
HOT_COPY_REWRITE_MODULE = "hot_copy_rewrite"
HOT_COPY_ANALYSIS_PROMPT_VERSION = "hot-copy-analysis-v1"
HOT_COPY_REWRITE_PROMPT_VERSION = "hot-copy-rewrite-v1"

HOT_COPY_ANALYSIS_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "hook",
        "structure",
        "emotion_triggers",
        "trust_builders",
        "conversion_points",
        "risk_notes",
    ],
    "properties": {
        "hook": {"type": "string"},
        "structure": {"type": "array", "items": {"type": "string"}},
        "emotion_triggers": {"type": "array", "items": {"type": "string"}},
        "trust_builders": {"type": "array", "items": {"type": "string"}},
        "conversion_points": {"type": "array", "items": {"type": "string"}},
        "risk_notes": {"type": "array", "items": {"type": "string"}},
        "rewrite_brief": {"type": "string"},
    },
}

HOT_COPY_REWRITE_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "title",
        "hook",
        "script",
        "shot_suggestions",
        "conversion_script",
        "risk_notes",
    ],
    "properties": {
        "title": {"type": "string"},
        "hook": {"type": "string"},
        "script": {"type": "string"},
        "shot_suggestions": {"type": "array", "items": {"type": "string"}},
        "conversion_script": {"type": "string"},
        "risk_notes": {"type": "array", "items": {"type": "string"}},
    },
}


def build_hot_copy_analysis_prompts(material: HotCopyMaterial) -> tuple[str, str]:
    metrics_text = json.dumps(material.metrics_json or {}, ensure_ascii=False, indent=2)
    system_prompt = (
        "你是短视频爆款文案拆解顾问。只返回合法 JSON，不要 Markdown。"
        "你只能分析结构、钩子、情绪、信任和转化动作，不要复制原文，不要搬运原视频画面，"
        "不要指导逐字改写或洗稿。"
    )
    user_prompt = f"""
请拆解这条热门口播素材，输出可用于合规二创的结构化分析。

素材信息:
- 平台: {material.platform}
- 账号: {material.account_name or "未提供"}
- 标题: {material.title}
- 指标: {metrics_text}

原始口播:
{material.original_script}

要求:
1. 只输出 JSON，字段必须包含 hook、structure、emotion_triggers、trust_builders、conversion_points、risk_notes。
2. rewrite_brief 可选，用一句话说明可借鉴的结构，不要包含原文句子。
3. 风险提醒必须明确禁止照搬原作者原句、搬运画面、冒用账号人设。
""".strip()
    return system_prompt, user_prompt


def build_hot_copy_rewrite_prompts(
    material: HotCopyMaterial,
    project: Project | None,
    payload: HotCopyRewriteRequest,
) -> tuple[str, str]:
    analysis_text = json.dumps(material.analysis_json or {}, ensure_ascii=False, indent=2)
    project_context = "未绑定项目，请只基于素材结构和用户输入改写。"
    if project is not None:
        platforms = "、".join(project.platforms or [])
        project_context = f"""
- 项目名: {project.project_name}
- 行业: {project.industry}
- 细分行业: {project.sub_industry or "未填写"}
- 产品/服务: {project.product}
- 个人简介: {project.personal_intro}
- 目标客户: {project.target_audience}
- 发布平台: {platforms}
- 账号阶段: {project.current_stage}
""".strip()

    product = payload.product or (project.product if project is not None else "未提供")
    target_customer = payload.target_customer or (project.target_audience if project is not None else "未提供")
    account_persona = payload.account_persona or (project.personal_intro if project is not None else "未提供")
    system_prompt = (
        "你是短视频口播二创文案策划。只返回合法 JSON，不要 Markdown。"
        "必须基于爆款结构进行原创重写，不能复制原文句子，不能搬运原视频画面，不能冒用原作者身份。"
    )
    user_prompt = f"""
请把热门素材改写成一条可拍摄的原创口播文案。

改写参数:
- 平台: {material.platform}
- 改写强度: {payload.rewrite_mode}
- 时长: {payload.duration}
- 转化目标: {payload.conversion_goal}
- 产品/服务: {product}
- 目标客户: {target_customer}
- 账号人设: {account_persona}

项目上下文:
{project_context}

素材标题:
{material.title}

原始口播，仅用于理解结构，禁止复制原句:
{material.original_script}

拆解结果:
{analysis_text}

要求:
1. 只输出 JSON，字段必须包含 title、hook、script、shot_suggestions、conversion_script、risk_notes。
2. script 必须是原创口播，可直接拍摄，围绕产品、目标客户和账号人设展开。
3. 保留可借鉴的钩子类型和结构节奏，但换成自己的场景、表达、证据和转化动作。
4. 风险提醒必须包含不要照搬原句、不要使用原视频画面、不要承诺绝对效果。
""".strip()
    return system_prompt, user_prompt
