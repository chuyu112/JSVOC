import json
from typing import Any

from app.models.account_strategy_context import AccountStrategyContext
from app.models.project import Project


ACCOUNT_PACKAGE_MODULE = "account_package"
ACCOUNT_PACKAGE_PROMPT_VERSION = "v1"

ACCOUNT_PACKAGE_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "account_positioning",
        "persona",
        "target_user_profile",
        "account_names",
        "bios",
        "content_columns",
        "trust_design",
        "conversion_path",
        "platform_strategies",
    ],
    "properties": {
        "account_positioning": {
            "type": "string",
            "description": "一句专业、聚焦、可作为报告主标题的账号核心定位。",
        },
        "persona": {
            "type": "string",
            "description": "一段可直接展示的人设包装说明，突出表达风格、可信背书和差异化。",
        },
        "target_user_profile": {
            "type": "object",
            "description": "按 core_audience、needs、concerns 等键组织，值可以是字符串或字符串数组。",
        },
        "account_names": {
            "type": "array",
            "items": {"type": "string"},
            "description": "账号名称建议数组，每项是一个完整名称，不要把多个名称写在同一字符串里。",
        },
        "bios": {
            "type": "object",
            "description": "平台名到账号简介的映射，例如 {'抖音': '...', '小红书': '...'}。",
        },
        "content_columns": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "description", "frequency", "examples"],
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "frequency": {"type": "string"},
                    "examples": {"type": "array", "items": {"type": "string"}},
                },
            },
            "description": "内容栏目对象数组，每项包含栏目名、说明、建议频率和参考选题。",
        },
        "trust_design": {
            "type": "array",
            "items": {"type": "string"},
            "description": "信任背书设计数组，每项是一个具体动作或证据。",
        },
        "conversion_path": {
            "type": "array",
            "items": {"type": "string"},
            "description": "转化路径步骤数组，按用户从公域看到内容到私域成交的顺序排列。",
        },
        "platform_strategies": {
            "type": "object",
            "description": "平台名到平台策略的映射，键名应与 bios 使用的平台名一致。",
        },
        "series_positioning": {
            "type": "string",
            "description": "系列整体定位。ONLY IF 对标账号有明确系列感才写；如果没有，可以省略或写'无固定系列'。",
        },
        "persona_layers": {
            "type": "object",
            "description": "人设层次。展示专业身份之外的真实生活面，让观众看到 profession 背后那个真实的人。比如：除了是老板，还是父亲/母亲、要照顾家庭、有业余爱好、会焦虑、会累。不是每个账号都需要戏剧化反差，但每个人都应该有生活真实感。",
            "properties": {
                "professional": {"type": "string", "description": "专业身份"},
                "personal": {"type": "string", "description": "生活身份/真实面"},
                "daily_life": {"type": "string", "description": "日常真实场景"},
            },
        },
        "tone_principles": {
            "type": "array",
            "items": {"type": "string"},
            "description": "语气原则列表。基于对标账号的表达特征提炼，有几条写几条，不要凑数。",
        },
        "material_pool": {
            "type": "object",
            "description": "素材池。ONLY IF 对标账号的内容风格需要书、剧、旅行、运动等生活素材才输出；纯卖货号可以省略。",
            "properties": {
                "books": {"type": "array", "items": {"type": "string"}},
                "tv_shows": {"type": "array", "items": {"type": "string"}},
                "movies": {"type": "array", "items": {"type": "string"}},
                "travel": {"type": "array", "items": {"type": "string"}},
                "sports": {"type": "array", "items": {"type": "string"}},
            },
        },
        "publishing_rhythm": {
            "type": "string",
            "description": "发布节奏建议。",
        },
        "content_structure_template": {
            "type": "string",
            "description": "内容结构模板。如果有对标账号的标志性内容结构（如'白天一幕 + 睡前独白'），必须输出；如果没有，写'无固定结构'。",
        },
        "rubric_notes": {
            "type": "object",
            "description": "对标样本分析笔记（cheat-learn-from）。当提供了 benchmark_samples 时必须输出，记录从样本中提取的模式、高表现因子、以及应用到本项目的具体建议。",
            "properties": {
                "high_performance_patterns": {"type": "array", "items": {"type": "string"}, "description": "高表现样本的共同特征"},
                "low_performance_warnings": {"type": "array", "items": {"type": "string"}, "description": "中低表现样本的避雷点"},
                "style_transfer_notes": {"type": "array", "items": {"type": "string"}, "description": "对标风格迁移到本项目的具体建议"},
                "content_ratio_reasoning": {"type": "string", "description": "60/30/10 配比的推理说明"},
            },
        },
    },
}


def account_strategy_context_to_prompt_data(context: AccountStrategyContext) -> dict[str, Any]:
    return {
        "account_positioning": context.account_positioning,
        "persona": context.persona,
        "target_user_profile": context.target_user_profile,
        "account_names": context.account_names,
        "bios": context.bios,
        "content_columns": context.content_columns,
        "trust_design": context.trust_design,
        "conversion_path": context.conversion_path,
        "platform_strategies": context.platform_strategies,
    }


def build_account_package_prompts(
    project: Project,
    previous_context: AccountStrategyContext | None = None,
) -> tuple[str, str]:
    platforms = "、".join(project.platforms)
    system_prompt = (
        "你是短视频账号策略专家。请基于项目档案生成账号包装方案，"
        "必须输出 JSON，字段必须包含 account_positioning、persona、target_user_profile、"
        "account_names、bios、content_columns、trust_design、conversion_path、platform_strategies。"
        "account_names、trust_design、conversion_path 必须是字符串数组，"
        "content_columns 必须是对象数组，每项包含 name、description、frequency、examples，"
        "bios、platform_strategies、target_user_profile 必须是对象，便于前端直接渲染为标签、"
        "描述列表和 Bento 卡片。内容必须具体、可执行，避免空泛口号。"
    )
    user_prompt = f"""
项目档案：
- 项目名称：{project.project_name}
- 行业：{project.industry}
- 细分行业：{project.sub_industry or "未填写"}
- 产品：{project.product}
- 个人简介：{project.personal_intro}
- 目标客户：{project.target_audience}
- 发布平台：{platforms}
- 当前阶段：{project.current_stage}

生成要求：
1. 账号定位、人设、信任背书和转化路径都要结合项目档案。
2. bios 和 platform_strategies 必须体现不同平台差异。
3. content_columns 必须输出对象数组，每个对象包含 name、description、frequency、examples。
4. 数组字段必须逐项拆开，不要把多个建议合并在一个长字符串里。
5. 对象字段使用清晰键名，平台字段直接用平台中文名。
6. 输出只返回 JSON，不要输出 Markdown。
"""
    if previous_context is not None:
        previous_context_json = json.dumps(
            account_strategy_context_to_prompt_data(previous_context),
            ensure_ascii=False,
            indent=2,
        )
        user_prompt += f"""

Existing fused account package:
{previous_context_json}

Merge and fusion requirements:
1. Treat the existing account package above as the accumulated result from prior generations.
2. Merge its strong points with the new generation instead of replacing everything.
3. Deduplicate account names, content columns, trust points, conversion paths, and platform tactics.
4. Keep the final answer coherent as one complete account package, not a simple list of multiple versions.
5. If the new idea conflicts with the existing package, keep the version that better fits the project file and target audience.
"""

    return system_prompt, user_prompt.strip()
