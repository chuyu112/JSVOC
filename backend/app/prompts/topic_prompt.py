from typing import Any

from app.models.account_strategy_context import AccountStrategyContext
from app.models.project import Project


TOPICS_MODULE = "topics"
TOPICS_PROMPT_VERSION = "v1"

TOPICS_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["topics"],
    "properties": {
        "topics": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "title",
                    "content_type",
                    "platform",
                    "goal",
                    "user_pain_point",
                    "hook",
                    "shooting_suggestion",
                    "conversion_method",
                    "score",
                ],
                "properties": {
                    "title": {"type": "string"},
                    "content_type": {"type": "string"},
                    "platform": {"type": "string"},
                    "goal": {"type": "string"},
                    "selling_point": {"type": "string"},
                    "user_pain_point": {"type": "string"},
                    "hook": {"type": "string"},
                    "shooting_suggestion": {"type": "string"},
                    "conversion_method": {"type": "string"},
                    "score": {"type": "integer"},
                },
            },
        }
    },
}


def build_topic_prompts(
    project: Project,
    strategy_context: AccountStrategyContext | None,
    platform: str,
    goal: str,
    count: int,
) -> tuple[str, str]:
    platforms = "、".join(project.platforms)
    context_text = "暂无账号包装上下文，请仅基于项目档案生成。"
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
        "你是短视频选题策划专家。请基于项目档案、账号策略、平台和内容目标生成短视频选题。"
        "必须输出 JSON，顶层字段为 topics。每个选题必须包含 title、content_type、platform、goal、"
        "user_pain_point、hook、shooting_suggestion、conversion_method、score。"
        "选题必须具体到行业、产品、场景、用户痛点和转化动作，禁止空泛表达。"
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

生成参数：
- 指定平台：{platform}
- 内容目标：{goal}
- 选题数量：{count}

生成要求：
1. 必须生成 {count} 个选题。
2. 每个选题都要适配 {platform}，goal 使用 {goal}。
3. 选题要具体体现项目的行业、产品、个人简介、目标客户和信任点。
4. 每个 hook 要能直接作为短视频开头第一句话。
5. shooting_suggestion 要说明怎么拍，包含画面、人物或实物动作。
6. conversion_method 要说明评论、私信或咨询承接方式。
7. score 使用 0-100 整数。
8. 输出只返回 JSON，不要输出 Markdown。
"""
    return system_prompt, user_prompt.strip()
