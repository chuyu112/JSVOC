import json
from typing import Any

from app.models.account_strategy_context import AccountStrategyContext
from app.models.project import Project
from app.prompts.formatting import format_prompt_list


EXECUTION_PLAN_MODULE = "execution_plan"
EXECUTION_PLAN_PROMPT_VERSION = "v1"

EXECUTION_PLAN_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["cycle", "weekly_plan", "daily_plan"],
    "properties": {
        "cycle": {"type": "string"},
        "weekly_plan": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["week", "goal", "focus", "key_tasks"],
                "properties": {
                    "week": {"type": "integer"},
                    "goal": {"type": "string"},
                    "focus": {"type": "string"},
                    "key_tasks": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "daily_plan": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["day", "task", "topic", "shooting_task", "review_metrics"],
                "properties": {
                    "day": {"type": "integer"},
                    "task": {"type": "string"},
                    "topic": {"type": "string"},
                    "shooting_task": {"type": "string"},
                    "review_metrics": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "notes": {"type": "array", "items": {"type": "string"}},
    },
}


def build_execution_plan_prompts(
    project: Project,
    strategy_context: AccountStrategyContext | None,
    cycle: str,
    daily_time: str,
    previous_plan: dict[str, Any] | None = None,
) -> tuple[str, str]:
    platforms = "、".join(project.platforms)
    context_text = "暂无账号包装上下文，请仅基于项目档案生成。"
    if strategy_context is not None:
        context_text = f"""
- 账号定位：{strategy_context.account_positioning}
- 人设：{strategy_context.persona}
- 内容栏目：{format_prompt_list(strategy_context.content_columns)}
- 信任设计：{format_prompt_list(strategy_context.trust_design)}
- 转化路径：{format_prompt_list(strategy_context.conversion_path)}
- 平台策略：{strategy_context.platform_strategies}
""".strip()

    system_prompt = (
        "你是短视频账号执行教练。请基于项目档案和账号策略上下文，生成可直接执行的执行计划。"
        "必须输出 JSON，字段必须包含 cycle、weekly_plan、daily_plan。"
        "weekly_plan 每项必须包含 week、goal、focus、key_tasks。"
        "daily_plan 每天必须包含 day、task、topic、shooting_task、review_metrics。"
        "内容必须具体到行业、产品、场景、拍摄动作和复盘指标，禁止使用“多发优质内容、保持账号活跃”等空话。"
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

执行计划参数：
- 周期：{cycle}
- 每天可投入时间：{daily_time}

生成要求：
1. 默认按 30 天生成，daily_plan 必须覆盖第 1 天到第 30 天。
2. 至少输出 4 周 weekly_plan，每周必须有明确目标、重点和关键任务。
3. 每天的 task、topic、shooting_task、review_metrics 都必须具体。
4. topic 要体现每日选题方向，shooting_task 要能指导当天怎么拍。
5. review_metrics 至少包含 3 个可复盘指标。
6. 输出只返回 JSON，不要输出 Markdown。
"""
    if previous_plan is not None:
        previous_plan_json = json.dumps(previous_plan, ensure_ascii=False, indent=2)
        user_prompt += f"""

Existing fused execution plan:
{previous_plan_json}

Merge and fusion requirements:
1. Treat the existing execution plan above as the accumulated plan from prior generations.
2. Merge its strong weekly goals, daily topics, shooting tasks, and review metrics into the new plan.
3. Deduplicate repeated daily topics and avoid cosmetic rewrites of the same task.
4. Keep one coherent {cycle} execution plan, not multiple versions.
5. If the new idea conflicts with the existing plan, keep the version that better fits the project file, account strategy, cycle, and daily available time.
"""
    return system_prompt, user_prompt.strip()
