from typing import Any

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
        "account_positioning": {"type": "string"},
        "persona": {"type": "string"},
        "target_user_profile": {"type": "object"},
        "account_names": {"type": "array", "items": {"type": "string"}},
        "bios": {"type": "object"},
        "content_columns": {"type": "array", "items": {"type": "string"}},
        "trust_design": {"type": "array", "items": {"type": "string"}},
        "conversion_path": {"type": "array", "items": {"type": "string"}},
        "platform_strategies": {"type": "object"},
    },
}


def build_account_package_prompts(project: Project) -> tuple[str, str]:
    platforms = "、".join(project.platforms)
    system_prompt = (
        "你是短视频账号策略专家。请基于项目档案生成账号包装方案，"
        "必须输出 JSON，字段必须包含 account_positioning、persona、target_user_profile、"
        "account_names、bios、content_columns、trust_design、conversion_path、platform_strategies。"
        "内容必须具体、可执行，避免空泛口号。"
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
3. 输出只返回 JSON，不要输出 Markdown。
"""
    return system_prompt, user_prompt.strip()
