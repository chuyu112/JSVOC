import json
from typing import Any

from app.models.account_strategy_context import AccountStrategyContext
from app.models.project import Project
from app.models.script import Script
from app.models.topic import Topic
from app.prompts.formatting import format_prompt_list


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
        "rubric": {
            "type": "object",
            "properties": {
                "er": {"type": "integer", "minimum": 0, "maximum": 5},
                "sr": {"type": "integer", "minimum": 0, "maximum": 5},
                "hp": {"type": "integer", "minimum": 0, "maximum": 5},
                "ql": {"type": "integer", "minimum": 0, "maximum": 5},
                "na": {"type": "integer", "minimum": 0, "maximum": 5},
                "ab": {"type": "integer", "minimum": 0, "maximum": 5},
                "sat": {"type": "integer", "minimum": 0, "maximum": 5},
            },
        },
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
    existing_scripts: list[Script] | None = None,
) -> tuple[str, str]:
    platforms = "、".join(project.platforms)
    topic_data = topic.topic_data or {}
    context_text = "暂无账号包装上下文，请仅基于项目档案和选题生成。"
    if strategy_context is not None:
        context_text = f"""
- 账号定位：{strategy_context.account_positioning}
- 人设：{strategy_context.persona}
- 内容栏目：{format_prompt_list(strategy_context.content_columns)}
- 信任设计：{format_prompt_list(strategy_context.trust_design)}
- 转化路径：{format_prompt_list(strategy_context.conversion_path)}
- 平台策略：{strategy_context.platform_strategies}
""".strip()
    existing_script_text = "None"
    if existing_scripts:
        existing_script_text = json.dumps(
            [
                {
                    "title": script.title,
                    "script_type": script.script_type,
                    "platform": script.platform,
                    "script_content": script.script_content,
                    "shot_suggestions": script.shot_suggestions,
                    "conversion_script": script.conversion_script,
                    "script_data": script.script_data,
                }
                for script in existing_scripts[:10]
            ],
            ensure_ascii=False,
            indent=2,
        )

    system_prompt = (
        "你是短视频文案导演。只返回合法 JSON，不要 Markdown。字段必须包含 title、hook、"
        "script_content、shot_suggestions、subtitle_points、conversion_script、comment_guidance、private_message_guidance、"
        "rubric。"
        "\n\n"
        "【内容配比规则 — 严格执行】\n"
        "- 对标账号风格（女性成长vlog/日常日记/情绪独白/强反差人设）：占60%，是主骨架\n"
        "- 行业内容（产品、客户、行业观察）：占30%，是主人公的日常素材和背景\n"
        "- 自由发散（书、剧、旅行、运动、生活观察、发散思考）：占10%，避免模板化\n"
        "行业占比绝对不能超过30%，不能做成行业科普或纯卖货文案。\n"
        "\n"
        "【写作风格规则 — 必须遵守】\n"
        "1. 节奏：像跟朋友聊天，不要像写报告。长短句交错。用逗号制造口语停顿。单句段落制造停顿和重量。\n"
        "2. 个人声音：用'我也遇到过这个'来连接个人经验和公共话题。分享真实的失败，不只是成功。\n"
        "3. 判断：有立场。明确表达喜欢和不喜欢，但用'我被这个打动了'而不是'你应该这样做'。\n"
        "4. 情感真实：用'...'表示拖长/震惊/无语。自嘲。直接兴奋。不要抽象描述情绪('我很震惊')，用身体记忆('我愣了一秒')。\n"
        "5. 文化升华：聊完具体事后，自然连接到更大的文化/哲学引用。不是强行升华，是'聊着聊着想到了这个'。\n"
        "6. 回环/Callback：早期埋钩子，后期变体回归。把信息流变成连贯作品。\n"
        "7. 反向论证：先满足读者预期，再打破它。'你以为 prompt 工程很复杂？其实就是复制粘贴。'制造顿悟感。\n"
        "\n"
        "【绝对禁止 — 出现即暴露 AI 生成】\n"
        "禁止过渡词：首先...其次...最后、综上所述、值得注意的是、不难发现、让我们来看看、接下来让我们。\n"
        "禁止元话语：说白了、意味着什么？、这意味着、本质上、换句话说、不可否认。\n"
        "禁止开头：在当今AI快速发展的时代、随着技术的不断进步。\n"
        "禁止标点习惯：冒号'：'换成逗号；破折号'——'换成逗号或句号；双引号\"\"换成「」或不加。\n"
        "禁止结构陷阱：超过3个观点不要列 bullet，用散文叙述；超过2行不要加粗；不要用'比如有一次...'这种虚构例子。\n"
        "\n"
        "【结构模板】\n"
        "[开头] 具体事件/场景，永远不要宏大叙事\n"
        "  ↓\n"
        "[背景] 简要科普，聊天式，不是讲座式\n"
        "  ↓\n"
        "[核心] 几段，每段一个明确观点，至少一个具体场景/对话/人物，个人连接，'回归主线'句拉回漂移内容\n"
        "  ↓\n"
        "[升华] 连接到更大的文化/哲学引用\n"
        "  ↓\n"
        "[结尾] 引用 / 短留白 / 行动号召 / 信念陈述 / callback\n"
        "\n"
        "【7 维度内容评分 — 每个文案都评】\n"
        "- ER (互动率): 能否引发评论、收藏、互动？\n"
        "- SR (分享率): 是否具备社交货币？\n"
        "- HP (钩子强度): 前 3 秒的抓力。\n"
        "- QL (制作质量): 画面、光线、执行的可实现性。\n"
        "- NA (叙事结构): 是否有 setup → tension → release。\n"
        "- AB (可信度): 具体细节、真实体验、数据支撑。\n"
        "- SAT (完播满足): 结尾是否兑现承诺。\n"
        "每个维度 0-5 分，输出 rubric 对象。\n"
    )
    user_prompt = f"""
项目: {project.project_name} / {project.industry} / {project.sub_industry or "未填写"}
产品: {project.product}
个人简介: {project.personal_intro}
目标客户: {project.target_audience}
账号上下文: {context_text}

选题: {topic.title}
类型/平台/目标: {topic.content_type} / {topic.platform} / {topic.goal}
用户痛点: {topic_data.get("user_pain_point", "")}
开头钩子: {topic_data.get("hook", "")}
拍摄建议: {topic_data.get("shooting_suggestion", "")}
转化方式: {topic_data.get("conversion_method", "")}

参数: 平台={platform}; 写法={script_type}; 时长={duration}; 目标={goal}

要求:
1. 只围绕这个选题写一条可拍摄文案。
2. script_content 控制在 600 字内，直接口播。必须遵守上述写作风格规则和禁止列表。
3. shot_suggestions 给 4-6 个镜头动作。
4. subtitle_points 给 4-6 条短字幕。
5. 转化、评论、私信都给具体话术。
6. 输出 rubric 对象，包含 er、sr、hp、ql、na、ab、sat 七个整数（0-5）。
7. 只返回 JSON。
"""
    if existing_scripts:
        user_prompt += f"""

Existing fused scripts for this topic:
{existing_script_text}

Merge and fusion requirements:
1. Treat the existing scripts above as accumulated script drafts for this topic.
2. Merge strong hooks, scene order, proof points, and conversion wording into one improved script.
3. Do not simply rewrite the previous script with synonyms; add a stronger opening, clearer shots, or better conversion path.
4. Keep the final answer as one complete shooting-ready script.
"""
    return system_prompt, user_prompt.strip()
