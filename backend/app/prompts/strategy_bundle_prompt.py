import json
from typing import Any

from app.models.project import Project
from app.prompts.account_package_prompt import ACCOUNT_PACKAGE_OUTPUT_SCHEMA
from app.prompts.execution_plan_prompt import EXECUTION_PLAN_OUTPUT_SCHEMA


STRATEGY_BUNDLE_MODULE = "strategy_bundle"
STRATEGY_BUNDLE_PROMPT_VERSION = "v1"

STRATEGY_BUNDLE_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["account_package", "execution_plan"],
    "properties": {
        "account_package": ACCOUNT_PACKAGE_OUTPUT_SCHEMA,
        "execution_plan": EXECUTION_PLAN_OUTPUT_SCHEMA,
    },
}


def build_strategy_bundle_prompts(
    project: Project,
    cycle: str,
    daily_time: str,
    benchmark_samples: list[dict[str, Any]] | None = None,
) -> tuple[str, str]:
    platforms = "、".join(project.platforms)
    project_data = {
        "project_name": project.project_name,
        "industry": project.industry,
        "sub_industry": project.sub_industry or "未填写",
        "product_service": project.product,
        "founder_profile": project.personal_intro,
        "target_customer": project.target_audience,
        "platforms": platforms,
        "account_stage": project.current_stage,
        "cycle": cycle,
        "daily_time": daily_time,
    }
    benchmark_part = ""
    if project.benchmark_accounts:
        benchmark_lines = []
        for b in project.benchmark_accounts:
            line = f"- {b.get('platform', '')} @{b.get('account_name', '')}"
            notes = b.get("notes", "")
            if notes:
                line += f"（{notes}）"
            benchmark_lines.append(line)
        benchmark_part = "\n对标账号参考:\n" + "\n".join(benchmark_lines) + "\n\n核心规则：以上对标账号的内容形式、表达节奏、人设逻辑、栏目结构、更新频率是主骨架。行业只是主人公的日常素材和背景，不是内容主体。你必须先深入分析对标账号的风格特征，再把这种风格迁移到本项目上。"

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
            + "你必须基于以上样本进行深度分析（Phase 4 模式提取）：\n"
            "1. 高表现样本（如果有）的共同特征是什么？是结构、节奏、情绪、还是选题角度？\n"
            "2. 中低表现样本（如果有）的问题在哪里？是太硬广、太说教、还是缺乏人味？\n"
            "3. 把这些模式直接映射到 account_package 的每个字段，在 rubric_notes 中记录分析结果：\n"
            "   - persona_layers.daily_life 必须体现高表现样本中的生活真实感\n"
            "   - tone_principles 必须提炼高表现样本的具体写法特征\n"
            "   - content_structure_template 必须总结高表现样本的结构模式\n"
            "   - content_columns 必须对标高表现样本的栏目类型，不是生搬硬套\n"
            "4. 如果样本中有明确的'喜欢/不喜欢'标注，账号包装必须主动避开不喜欢样本的特征。\n"
        )

    system_prompt = "你是短视频账号策略助手。只返回合法 JSON，不要 Markdown，不要解释。所有字段用中文短句。"
    user_prompt = f"""
基于项目资料，一次生成账号包装和{cycle}执行计划。
项目资料: {json.dumps(project_data, ensure_ascii=False)}
{benchmark_part}
{samples_part}
输出必须是一个 JSON 对象，顶层只有 account_package 和 execution_plan。

【质量标准 — 生成后必须自检】
以下是一个优秀账号包装应该达到的水平，你的输出必须对齐这个标准：

1. persona_layers.daily_life 必须是"生活场景"，不是"工作场景"。
   错误示例："档口看货、打包发货、接待客户" —— 这是工作，不是生活。
   正确示例："摘下耳环问自己今天是不是太硬了、睡前泡一杯热茶、陪孩子写作业、跑步时想通一件事、在便利店买晚饭" —— 这是生活。
   要求：daily_life 里的场景，工作相关的内容不能超过 30%。

2. content_columns 的栏目名必须有"人味"，不能是行业术语堆砌。
   错误示例："翡翠知识科普""手镯选购指南""行业避坑大全" —— 这是行业号。
   正确示例："女老板四会日记""今天又被手镯上了一课""我和客户的真实对话""一个人做生意的情绪" —— 这是人号。
   要求：4 个栏目名中，直接出现行业关键词（翡翠/手镯/珠宝等）的不能超过 1 个。

3. tone_principles 必须具体到"怎么写"，不是笼统的形容词。
   错误示例："像朋友聊天""真实自然" —— 太虚。
   正确示例："先讲当天一个具体经历，再落到判断""句子短，像夜里自我复盘""不急着证明专业，用选择证明""敢说不适合，不强行成交" —— 可执行。
   要求：每条原则都能直接指导一条文案的写作。

4. 如果有对标账号，必须体现对标账号的核心结构特征。
   例如对标"飙马野人"（强女日记/人生播客/人生书单），就必须有：
   - 类似"强女日记"的栏目（记录日常+情绪）
   - 类似"人生播客"的栏目（独白+复盘）
   - 内容结构要预留"白天一幕 + 睡前独白"的格式

account_package 字段：
- account_positioning: 1句账号核心定位
- persona: 1句人设
- series_positioning: 系列整体定位。如果有对标账号且对标账号有明确的系列感，就写；如果没有，可以省略或写"无固定系列，以单条内容为主"
- persona_layers: 对象，必须包含 professional（专业身份）、personal（生活身份/真实面）、daily_life（日常真实场景）。核心要求：daily_life 里工作场景不能超过 30%，必须有具体的生活细节（家庭、情绪、爱好、日常琐事）
- target_user_profile: 包含 core_audience、needs、concerns
- account_names: 3个账号名
- bios: 按平台给简介；如果平台为空，给1个通用简介
- content_columns: 4个内容栏目，每个必须是对象，包含 name、description、frequency、examples。要求：栏目名必须有"人味"，行业术语不能超过 1 个；必须贴合对标账号的栏目特征
- trust_design: 4个信任设计
- conversion_path: 4步转化路径
- platform_strategies: 按平台给1句策略
- tone_principles: 5-6条语气原则，每条必须具体到"怎么写"，不能是笼统形容词
- material_pool: 素材池，包含 books（8-10本书）、tv_shows（8-10部剧）、travel（8-10个旅行地）、sports（6-8项运动）。要求：书名/剧名/地名必须具体，不能写"最近看的一本书"这种空洞表达
- publishing_rhythm: 发布节奏
- content_structure_template: 内容结构模板。如果有对标账号的标志性内容结构（如"白天一幕 + 睡前独白"），必须输出；如果没有，写"无固定结构"
- rubric_notes: 对标样本分析笔记。当提供了 benchmark_samples 时必须输出，包含 high_performance_patterns（高表现样本共同特征数组）、low_performance_warnings（避雷点数组）、style_transfer_notes（风格迁移建议数组）、content_ratio_reasoning（60/30/10 配比推理字符串）。不能空泛，必须基于具体样本得出结论。

execution_plan 字段:
- cycle: 使用请求周期
- weekly_plan: 4项，每项包含 week、goal、focus、key_tasks
- daily_plan: 30项，每项包含 day、topic、task、shooting_task、review_metrics

内容配比规则（严格执行）:
- 对标账号风格：占60%，是内容主骨架。必须先分析对标账号风格，再决定这60%具体是什么
- 行业内容（{project.industry}/{project.sub_industry or '相关产品'}）：占30%，是主人公的日常素材和背景
- 自由发散（书、剧、旅行、运动、生活观察、发散思考）：占10%，让内容有真实生活气息，避免模板化

核心原则（优先级最高）:
- 不要假设任何固定内容形式。不是每个账号都要讲故事、不是每个账号都要睡前独白、不是每个账号都要双重人设
- 栏目设计、人设风格、表达节奏、信任建立方式必须完全基于对标账号的风格分析
- 如果有对标账号，人设就是"这个行业里的对标账号风格"，不是固定某种人设类型
- 表达节奏、标题风格、选题方向都必须贴合对标账号，行业只是背景和素材
- 内容要贴合行业、产品、目标客户和平台
- 整体简洁，可直接执行
- daily_plan 每项控制在20字内，review_metrics 每天给2个指标
"""
    return system_prompt, user_prompt.strip()
