import json
from typing import Any

from app.models.account_strategy_context import AccountStrategyContext
from app.models.project import Project
from app.models.topic import Topic
from app.prompts.formatting import format_prompt_list


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
                    "shooting_script": {"type": "string"},
                    "spoken_script": {"type": "string"},
                    "seedance_video_prompt": {"type": "string"},
                    "image_prompt": {"type": "string"},
                    "image_edit_prompt": {"type": "string"},
                    "score": {"type": "integer"},
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
                    "hkr": {
                        "type": "object",
                        "properties": {
                            "h": {"type": "integer", "minimum": 0, "maximum": 5},
                            "k": {"type": "integer", "minimum": 0, "maximum": 5},
                            "r": {"type": "integer", "minimum": 0, "maximum": 5},
                        },
                    },
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
    content_format: str,
    count: int,
    existing_titles: list[str] | None = None,
    topic_index: int | None = None,
    existing_topics: list[Topic] | None = None,
    persona_reference_image_uploaded: bool = False,
    benchmark_samples: list[dict[str, Any]] | None = None,
    account_package_extras: dict[str, Any] | None = None,
) -> tuple[str, str]:
    platforms = "、".join(project.platforms)
    context_text = "暂无账号包装上下文，请仅基于项目档案生成。"
    if strategy_context is not None:
        extras = account_package_extras or {}
        enrich_parts = [
            f"- 账号定位：{strategy_context.account_positioning}",
            f"- 人设：{strategy_context.persona}",
            f"- 内容栏目：{format_prompt_list(strategy_context.content_columns)}",
            f"- 信任设计：{format_prompt_list(strategy_context.trust_design)}",
            f"- 转化路径：{format_prompt_list(strategy_context.conversion_path)}",
            f"- 平台策略：{strategy_context.platform_strategies}",
        ]
        if extras.get("series_positioning"):
            enrich_parts.append(f"- 系列定位：{extras['series_positioning']}")
        if extras.get("persona_layers"):
            pl = extras["persona_layers"]
            enrich_parts.append(
                f"- 人设层次：professional={pl.get('professional','')} / personal={pl.get('personal','')} / daily_life={pl.get('daily_life','')}"
            )
        if extras.get("tone_principles"):
            enrich_parts.append(f"- 语气原则：{format_prompt_list(extras['tone_principles'])}")
        if extras.get("content_structure_template"):
            enrich_parts.append(f"- 内容结构模板：{extras['content_structure_template']}")
        if extras.get("publishing_rhythm"):
            enrich_parts.append(f"- 发布节奏：{extras['publishing_rhythm']}")
        if extras.get("material_pool"):
            mp = extras["material_pool"]
            enrich_parts.append(f"- 素材池：books={mp.get('books',[])} / tv_shows={mp.get('tv_shows',[])} / travel={mp.get('travel',[])} / sports={mp.get('sports',[])}")
        context_text = "\n".join(enrich_parts)
    excluded_titles = "\n".join(f"- {title}" for title in (existing_titles or [])[-100:] if title.strip())
    excluded_text = excluded_titles or "暂无"
    topic_index_text = str(topic_index) if topic_index is not None else "未指定"
    persona_reference_text = "已上传人设本人参考图" if persona_reference_image_uploaded else "未上传人设本人参考图"
    visual_persona_rule = (
        "已上传人设本人参考图：image_prompt、image_edit_prompt、seedance_video_prompt 可以描写人设本人，"
        "但必须以参考图身份一致为前提。"
        if persona_reference_image_uploaded
        else (
            "未上传人设本人参考图：image_prompt、image_edit_prompt、seedance_video_prompt 禁止写人设姓名、昵称、"
            "年龄、长相、正脸、本人出镜、创始人本人或可识别的人设形象；只能写货品、场景、道具、光线，"
            "如需人物只能写“非人设手模/工作人员的手部、背影或局部动作”。"
        )
    )

    samples_part = ""
    if benchmark_samples:
        sample_lines = []
        for idx, s in enumerate(benchmark_samples, 1):
            title = s.get("title", f"样本{idx}")
            platform = s.get("platform", "")
            stats = s.get("stats", "")
            impression = s.get("impression", "")
            impression_reason = s.get("impression_reason", "")
            script = s.get("script", "")
            lines = [f"### 样本 {idx}: {title}"]
            if platform:
                lines.append(f"平台: {platform}")
            if stats:
                lines.append(f"数据: {stats}")
            if impression:
                lines.append(f"表现评级: {impression}")
            if impression_reason:
                lines.append(f"评级理由: {impression_reason}")
            if script:
                lines.append(f"文案/脚本:\n{script}")
            sample_lines.append("\n".join(lines))
        samples_part = (
            "\n【对标样本分析 — cheat-learn-from】\n"
            + "\n\n".join(sample_lines)
            + "\n\n"
            + "你必须基于以上样本进行深度模式提取：\n"
            "1. 高表现样本的共同特征（结构、节奏、情绪、选题角度）必须体现在本次选题中。\n"
            "2. 中低表现样本的问题（硬广、说教、缺乏人味）必须主动避开。\n"
            "3. 每个选题的 hook、shooting_script、shooting_suggestion 必须贴合高表现样本的表达节奏和结构。\n"
            "4. 如果样本中有具体的生活场景（雨天、睡前、便利店等），选题可以直接借用或变体这些场景。\n"
            "5. 行业（产品）只能作为背景素材，不能成为选题主体。\n"
        )

    existing_topic_text = "None"
    if existing_topics:
        existing_topic_text = json.dumps(
            [
                {
                    "title": topic.title,
                    "content_type": topic.content_type,
                    "platform": topic.platform,
                    "goal": topic.goal,
                }
                for topic in existing_topics[:50]
            ],
            ensure_ascii=False,
            indent=2,
        )

    system_prompt = (
        "你是短视频选题策划专家。请基于项目档案、账号策略、平台和内容目标生成短视频选题。"
        "必须输出 JSON，顶层字段为 topics。每个选题必须包含 title、content_type、platform、goal、score。"
        "不同内容形态输出不同字段：video/video_script 输出完整的视频制作字段；video_spoken 只输出 spoken_script；image 只输出 title。"
        "选题必须具体到行业、产品、场景、用户痛点和转化动作，禁止空泛表达。"
        "每个字段都要克制精炼，单个选题的任何文案字段必须严格小于 200 个汉字。"
        "\n\n"
        "【选题质量框架 — 必须应用】\n"
        "每个选题必须通过 HKR 质检，并输出 7 维度评分。\n"
        "\n"
        "HKR 质检（0-5 分，每个选题都评）：\n"
        "- H (Happy / 好奇心): 标题和开头是否让人好奇想点开？是否有悬念、冲突或意外？\n"
        "- K (Knowledge / 信息量): 看完是否能学到新东西？有没有具体知识点或信息增量？\n"
        "- R (Resonance / 情绪共鸣): 能否戳中目标受众的情绪？让人产生'我也是'的认同感？\n"
        "S 级选题三项兼备；及格选题至少占两项；只有一项或零项的选题直接淘汰重写。\n"
        "\n"
        "7 维度内容评分（0-5 分，每个选题都评）：\n"
        "- ER (Engagement / 互动率): 能否引发评论、收藏、互动？是否有开放 loops 或好奇心缺口？\n"
        "- SR (Share / 分享率): 是否具备社交货币？用户会不会转发给朋友说'这就是你'？\n"
        "- HP (Hook Power / 钩子强度): 前 3 秒 / 第一句话的抓力。是否有情绪冲击或认知颠覆？\n"
        "- QL (Quality / 制作质量): 画面、光线、执行的可实现性。是否能在现有条件下高质量完成？\n"
        "- NA (Narrative / 叙事结构): 是否有 setup → tension → release 的结构？不是纯信息罗列。\n"
        "- AB (Authority / 可信度): 是否有具体细节、真实体验、数据支撑？不是泛泛而谈。\n"
        "- SAT (Satisfaction / 完播满足感): 结尾是否兑现了开头的承诺？看完觉得值得？\n"
        "\n"
        "score 计算规则（0-100 整数）：\n"
        "composite = (ER×1.5 + SR×1.5 + HP×1.5 + QL + NA + AB + SAT) / 8.5 × 2.0，映射到 0-100。\n"
        "例：ER=4, SR=3, HP=5, QL=4, NA=3, AB=4, SAT=3 → composite=6.8 → score=68。\n"
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

{samples_part}
生成参数：
- 指定平台：{platform}
- 内容目标：{goal}
- 内容形态：{content_format}
- 选题数量：{count}
- 当前序号：{topic_index_text}
- 人设本人参考图：{persona_reference_text}

已生成选题标题（禁止重复或换壳复述）：
{excluded_text}

内容配比规则（严格执行）：
- 对标账号风格（女性成长vlog/日常日记/情绪独白/强反差人设）：占60%，是主骨架
- 行业内容（产品、客户、行业观察）：占30%，是主人公的日常素材和背景
- 自由发散（书、剧、旅行、运动、生活观察、发散思考）：占10%，避免模板化

生成要求：
1. 必须生成 {count} 个选题。
2. 每个选题都要适配 {platform}，goal 使用 {goal}。
3. 当前序号用于区分选题角度，必须让本次选题和其它序号的选题在切入场景、用户痛点或转化动作上明显不同。
4. 选题要具体体现项目的行业、产品、个人简介、目标客户和信任点，但行业占比不超过30%，不能做成行业科普或纯卖货选题。
5. 如果内容形态是 video 或 video_script：每个选题必须输出 user_pain_point、hook、shooting_suggestion、conversion_method。hook 要能直接作为短视频开头第一句话，语气贴合账号包装的"语气原则"；shooting_suggestion 说明怎么拍；conversion_method 说明评论/私信/咨询承接方式。
6. 如果内容形态是 video_spoken（口播）：每个选题只需要输出 title 和 spoken_script，不需要 user_pain_point、hook、shooting_suggestion、conversion_method 等视频制作字段。
7. 如果内容形态是 image（图片）：每个选题只需要输出 title，不需要其他字段。
8. score 使用 0-100 整数，必须通过 7 维度 rubric 公式计算得出。
9. 每个选题必须额外输出 rubric 对象，包含 er、sr、hp、ql、na、ab、sat 七个整数（0-5）。
10. 每个选题必须额外输出 hkr 对象，包含 h、k、r 三个整数（0-5）。
11. 如果内容形态是 video 或 video_script，每个选题必须额外输出 shooting_script 和 seedance_video_prompt。shooting_script 是可直接拍摄的分镜/口播脚本，必须体现 content_structure_template 的结构；seedance_video_prompt 是给 Seedance 参考图生视频使用的中文提示词。
12. 如果内容形态是 video_spoken（口播/视频号），每个选题必须额外输出 spoken_script。格式要求：
    - title 必须是简洁的话题型标题，如"翡翠是智商税吗？"、"买手镯还是买挂件？"、"打麻将戴什么首饰最旺？"
    - spoken_script 必须是完整的口播文案（300-500字），风格贴近视频号：有深度、讲故事、娓娓道来、真诚分享
    - spoken_script 结构：开场引入话题 → 讲故事/举例子 → 分享观点和经验 → 结尾互动引导
    - spoken_script 要有自然段落，使用换行分隔，语气真诚、有温度，像朋友聊天分享
13. 如果内容形态是 image（图片），每个选题只需要输出 title，不需要其他字段。title 是简洁的图片选题标题。
14. 如果内容形态是 image_to_image，每个选题必须额外输出 image_edit_prompt，作为上传参考图后的图生图改图提示词。
15. 出图人设规则：{visual_persona_rule}
16. 每个选题的 title 必须严格小于 50 个汉字；spoken_script 必须在 300-500 字之间；其他字段必须严格小于 200 个汉字。
17. 字数限制只针对 JSON 输出字段，提示词内容不计入字段字数。
18. 输出只返回 JSON，不要输出 Markdown。
"""
    if existing_topics:
        user_prompt += f"""

Existing fused topic pool:
{existing_topic_text}

Merge and fusion requirements:
1. Treat the existing topic pool above as accumulated generated topics for this project.
2. Generate additional topics that complement the existing pool instead of duplicating it.
3. Reuse strong angles only when you substantially change scene, pain point, hook, or conversion action.
4. Keep titles, hooks, and shooting suggestions distinct enough for the front end to show them as separate ideas.
"""
    return system_prompt, user_prompt.strip()
