import json
from typing import Any

from app.models.account_strategy_context import AccountStrategyContext
from app.models.hot_copy import HotCopyMaterial
from app.models.project import Project
from app.schemas.hot_copy import HotCopyRewriteRequest


HOT_COPY_ANALYSIS_MODULE = "hot_copy_analysis"
HOT_COPY_REWRITE_MODULE = "hot_copy_rewrite"
HOT_COPY_ANALYSIS_PROMPT_VERSION = "hot-copy-analysis-v2"
HOT_COPY_REWRITE_PROMPT_VERSION = "hot-copy-rewrite-v2"

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
        "structure_type": {
            "type": "string",
            "enum": ["talking_head", "drama", "mixed"],
            "description": "视频结构类型: talking_head=单人怼脸口播, drama=多场景剧情, mixed=混剪/其他",
        },
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
        "scene_breakdown": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "scene_no": {"type": "integer"},
                    "setting": {"type": "string"},
                    "characters": {"type": "string"},
                    "action": {"type": "string"},
                    "dialogue": {"type": "string"},
                    "shot_type": {"type": "string"},
                    "image_prompt": {"type": "string"},
                },
            },
        },
    },
}


def build_hot_copy_analysis_prompts(material: HotCopyMaterial) -> tuple[str, str]:
    metrics_text = json.dumps(material.metrics_json or {}, ensure_ascii=False, indent=2)
    system_prompt = (
        "你是短视频爆款文案拆解顾问。只返回合法 JSON，不要 Markdown。"
        "你只能分析结构、钩子、情绪、信任和转化动作，不要复制原文，不要搬运原视频画面，"
        "不要指导逐字改写或洗稿。JSON 字段名按约定使用英文；除 structure_type 枚举值外，所有字段值必须使用中文。"
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
1. 只输出 JSON，字段必须包含 hook、structure、emotion_triggers、trust_builders、conversion_points、risk_notes、structure_type。
2. JSON 字段名按要求保留英文；structure_type 必须输出 talking_head、drama 或 mixed；除此之外所有字段值、说明、列表内容必须全中文，不要输出英文提示词或英文营销术语。
3. structure_type 必须根据文案特征判断：
   - talking_head: 单人面对镜头输出观点，文案密度高、信息型强、场景单一
   - drama: 多角色对话、有场景切换、动作描述丰富、情节驱动
   - mixed: 混剪、vlog、无法明确归入前两类的其他形式
4. rewrite_brief 可选，用一句话说明可借鉴的结构，不要包含原文句子。
5. 风险提醒必须明确禁止照搬原作者原句、搬运画面、冒用账号人设。
""".strip()
    return system_prompt, user_prompt


def _build_strategy_context_text(strategy_context: AccountStrategyContext | None) -> str:
    if strategy_context is None:
        return ""
    lines = ["--- 精准人设资料 ---"]
    if strategy_context.account_positioning:
        lines.append(f"账号定位: {strategy_context.account_positioning}")
    if strategy_context.persona:
        lines.append(f"核心人设: {strategy_context.persona}")
    if strategy_context.content_style:
        lines.append(f"内容风格: {strategy_context.content_style}")
    if strategy_context.content_columns:
        try:
            cols = json.dumps(strategy_context.content_columns, ensure_ascii=False)
            lines.append(f"内容栏目: {cols}")
        except Exception:
            pass
    if strategy_context.trust_design:
        try:
            trust = json.dumps(strategy_context.trust_design, ensure_ascii=False)
            lines.append(f"信任设计: {trust}")
        except Exception:
            pass
    if strategy_context.conversion_path:
        try:
            conv = json.dumps(strategy_context.conversion_path, ensure_ascii=False)
            lines.append(f"转化路径: {conv}")
        except Exception:
            pass
    if strategy_context.platform_strategies:
        try:
            plat = json.dumps(strategy_context.platform_strategies, ensure_ascii=False)
            lines.append(f"平台策略: {plat}")
        except Exception:
            pass
    if strategy_context.target_user_profile:
        try:
            prof = json.dumps(strategy_context.target_user_profile, ensure_ascii=False)
            lines.append(f"目标用户画像: {prof}")
        except Exception:
            pass
    extras = strategy_context.context_data.get("account_package_extras") if isinstance(strategy_context.context_data, dict) else None
    if extras:
        if extras.get("tone_principles"):
            lines.append(f"语调原则: {extras['tone_principles']}")
        if extras.get("persona_layers"):
            lines.append(f"人设层次: {extras['persona_layers']}")
        if extras.get("content_structure_template"):
            lines.append(f"内容结构模板: {extras['content_structure_template']}")
    lines.append("---")
    return "\n".join(lines)


def build_hot_copy_rewrite_prompts(
    material: HotCopyMaterial,
    project: Project | None,
    payload: HotCopyRewriteRequest,
    strategy_context: AccountStrategyContext | None = None,
    structure_type: str = "talking_head",
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

    strategy_text = _build_strategy_context_text(strategy_context)

    product = payload.product or (project.product if project is not None else "未提供")
    target_customer = payload.target_customer or (project.target_audience if project is not None else "未提供")
    account_persona = payload.account_persona or (project.personal_intro if project is not None else "未提供")
    if structure_type == "drama":
        system_prompt = (
            "你是短视频剧情二创文案策划。只返回合法 JSON，不要 Markdown。"
            "必须基于爆款结构进行原创重写，不能复制原文句子，不能搬运原视频画面，不能冒用原作者身份。"
            "JSON 字段名按约定使用英文，但所有字段值必须使用中文。"
        )
        type_specific_requirements = """
- 此素材为剧情类，script 必须使用剧本格式（场景标题 + 人物动作 + 台词）。
- 必须额外输出 scene_breakdown 数组，每个场景包含：scene_no（序号）、setting（场景地点）、characters（出场人物）、action（动作描述）、dialogue（台词）、shot_type（建议景别如特写/中景/远景）、image_prompt（用于 AI 生图的分镜参考提示词，必须全中文）。
- 明确提示：剧情类视频不适合数字人口播，需要用户自行拍摄或找演员演绎。
""".strip()
    elif structure_type == "mixed":
        system_prompt = (
            "你是短视频二创文案策划。只返回合法 JSON，不要 Markdown。"
            "必须基于爆款结构进行原创重写，不能复制原文句子，不能搬运原视频画面，不能冒用原作者身份。"
            "JSON 字段名按约定使用英文，但所有字段值必须使用中文。"
        )
        type_specific_requirements = """
- 此素材为混剪/综合类，script 保持口播或解说稿形式，shot_suggestions 可以包含素材拼接建议。
""".strip()
    else:
        system_prompt = (
            "你是短视频口播二创文案策划。只返回合法 JSON，不要 Markdown。"
            "必须基于爆款结构进行原创重写，不能复制原文句子，不能搬运原视频画面，不能冒用原作者身份。"
            "JSON 字段名按约定使用英文，但所有字段值必须使用中文。"
        )
        type_specific_requirements = """
- 此素材为口播类，script 必须是可直接对着镜头念的口播稿，语气自然、有节奏感。
- shot_suggestions 为简单分镜建议（如"前3秒特写钩子"、"中段产品展示"等）。
""".strip()

    user_prompt = f"""
请把热门素材改写成一条可拍摄的原创文案。

改写参数:
- 平台: {material.platform}
- 结构类型: {structure_type}
- 改写强度: {payload.rewrite_mode}
- 时长: {payload.duration}
- 转化目标: {payload.conversion_goal}
- 产品/服务: {product}
- 目标客户: {target_customer}
- 账号人设: {account_persona}

项目上下文:
{project_context}

{strategy_text}

素材标题:
{material.title}

原始口播，仅用于理解结构，禁止复制原句:
{material.original_script}

拆解结果:
{analysis_text}

要求:
1. 只输出 JSON，字段必须包含 title、hook、script、shot_suggestions、conversion_script、risk_notes。
2. JSON 字段名按要求保留英文，所有字段值、脚本、台词、分镜、风险提醒、生图提示词必须全中文。
3. image_prompt 必须是中文自然语言画面描述，不要输出英文关键词、英文逗号分隔词、英文摄影术语或中英混写。
4. script 必须是原创，可直接拍摄，围绕产品、目标客户和账号人设展开。
5. 保留可借鉴的钩子类型和结构节奏，但换成自己的场景、表达、证据和转化动作。
6. 必须深度融合上述"精准人设资料"中的账号定位、核心人设、内容风格、语调原则，让文案听起来就是这个账号本人说的，不是通用 AI 味。
7. 风险提醒必须包含不要照搬原句、不要使用原视频画面、不要承诺绝对效果。
{type_specific_requirements}
""".strip()
    return system_prompt, user_prompt
