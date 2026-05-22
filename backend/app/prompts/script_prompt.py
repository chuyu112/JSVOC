from typing import Any

from app.models.account_strategy_context import AccountStrategyContext
from app.models.project import Project
from app.models.topic import Topic


SCRIPT_MODULE = "script"
SCRIPT_PROMPT_VERSION = "v1"

SCRIPT_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "title",
        "hook",
        "script_content",
        "shot_suggestions",
        "subtitle_points",
        "conversion_script",
        "comment_guidance",
        "private_message_guidance",
    ],
    "properties": {
        "title": {"type": "string"},
        "hook": {"type": "string"},
        "script_content": {"type": "string"},
        "shot_suggestions": {"type": "array", "items": {"type": "string"}},
        "subtitle_points": {"type": "array", "items": {"type": "string"}},
        "conversion_script": {"type": "string"},
        "comment_guidance": {"type": "string"},
        "private_message_guidance": {"type": "string"},
    },
}


def build_script_prompts(
    project: Project,
    topic: Topic,
    strategy_context: AccountStrategyContext | None,
    platform: str,
    script_type: str,
    duration: str,
    goal: str,
) -> tuple[str, str]:
    platforms = "、".join(project.platforms)
    topic_data = topic.topic_data or {}
    context_text = "暂无账号包装上下文，请仅基于项目档案和选题生成。"
    if strategy_context is not None:
        context_text = f"""
- 账号定位：{strategy_context.account_positioning}
- 人设：{strategy_context.persona}
- 内容栏目：{"、".join(strategy_context.content_columns)}
- 信任设计：{"、".join(strategy_context.trust_design)}
- 转化路径：{"、".join(strategy_context.conversion_path)}
- 平台策略：{strategy_context.platform_strategies}
""".strip()

    system_prompt = (
        "你是短视频文案导演。请基于已保存选题生成可直接拍摄的短视频文案。"
        "必须输出 JSON，字段必须包含 title、hook、script_content、shot_suggestions、"
        "subtitle_points、conversion_script、comment_guidance、private_message_guidance。"
        "内容必须具体到行业、产品、人物、场景、镜头和转化动作，禁止空泛表达。"
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

账号策略上下文：
{context_text}

已保存选题：
- 选题 ID：{topic.id}
- 标题：{topic.title}
- 内容类型：{topic.content_type}
- 平台：{topic.platform}
- 目标：{topic.goal}
- 用户痛点：{topic_data.get("user_pain_point", "")}
- 开头钩子：{topic_data.get("hook", "")}
- 拍摄建议：{topic_data.get("shooting_suggestion", "")}
- 转化方式：{topic_data.get("conversion_method", "")}

文案参数：
- 平台：{platform}
- 写法：{script_type}
- 时长：{duration}
- 目标：{goal}

生成要求：
1. 文案必须基于上述已保存选题，不要另起一个无关选题。
2. 正文口播要适合 {duration}，能直接照着拍。
3. 必须体现翡翠、四会、源头市场、避坑、客户咨询或成交引导。
4. shot_suggestions 要按镜头顺序列出拍摄动作。
5. subtitle_points 要列出可直接上字幕的重点短句。
6. conversion_script、comment_guidance、private_message_guidance 都要给具体话术。
7. 输出只返回 JSON，不要输出 Markdown。
"""
    return system_prompt, user_prompt.strip()
