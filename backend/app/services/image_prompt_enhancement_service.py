import json
import re
from typing import Any

from sqlalchemy.orm import Session

from app.llm.llm_gateway import LLMGateway, LLMGatewayRequest
from app.models.project import Project
from app.schemas.image_generation import ImagePromptEnhanceRequest, ImagePromptEnhanceResponse


IMAGE_PROMPT_ENHANCE_MODULE = "image_prompt_enhance"
IMAGE_PROMPT_ENHANCE_PROMPT_VERSION = "image-prompt-enhance-v1"

JEWELRY_MATERIAL_HINTS = {
    "翡翠": "translucent jade texture, smooth polish, natural internal texture, elegant green depth",
    "玉": "translucent jade texture, smooth polish, natural internal texture",
    "钻石": "crisp facets, brilliant fire, clean sparkle, precise reflections",
    "黄金": "warm gold luster, polished metal reflection, premium craftsmanship",
    "珍珠": "soft pearl luster, subtle iridescence, smooth nacre surface",
}

PROJECT_NAME_FILLERS = [
    "翡翠",
    "珠宝",
    "玉石",
    "玉",
    "钻石",
    "黄金",
    "珍珠",
    "首饰",
    "饰品",
    "高货",
    "甄选",
    "严选",
    "工作室",
    "珠宝店",
]


def enhance_image_prompt(
    db: Session,
    *,
    payload: ImagePromptEnhanceRequest,
    project: Project | None,
    user_id: int,
) -> ImagePromptEnhanceResponse:
    interference_terms = extract_interference_terms(payload.prompt, project)
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(payload, project, interference_terms)

    result = LLMGateway().generate(
        db=db,
        project_id=project.id if project is not None else None,
        user_id=user_id,
        prompt_version=IMAGE_PROMPT_ENHANCE_PROMPT_VERSION,
        request=LLMGatewayRequest(
            module_name=IMAGE_PROMPT_ENHANCE_MODULE,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.35,
            max_tokens=1200,
            metadata={
                "project_id": project.id if project is not None else None,
                "mode": payload.mode,
                "size": payload.size,
                "quality": payload.quality,
                "interference_terms": interference_terms,
            },
        ),
    )
    if not result.success:
        raise RuntimeError(result.error or "image prompt enhancement failed")

    data = parse_enhancement_data(result.data, result.content)
    product = project.product.strip() if project is not None else ""
    llm_subject = str(data.get("subject") or "").strip()
    subject = product if product and should_force_project_product(llm_subject, product) else (llm_subject or product or "产品主体")
    enhanced_prompt = str(data.get("enhanced_prompt") or "").strip()
    if not enhanced_prompt:
        enhanced_prompt = fallback_enhanced_prompt(payload.prompt, project, payload.mode)

    enhanced_prompt = sanitize_visual_prompt(enhanced_prompt, interference_terms, product)
    if product and product not in enhanced_prompt:
        enhanced_prompt = f"画面主体必须是{product}。{enhanced_prompt}"
    removed_terms = [term for term in interference_terms if term and term not in product]
    notes = data.get("notes") if isinstance(data.get("notes"), list) else []

    return ImagePromptEnhanceResponse(
        enhanced_prompt=enhanced_prompt,
        subject=subject,
        removed_terms=removed_terms,
        notes=[str(item) for item in notes][:6],
    )


def build_system_prompt() -> str:
    return """你是 JPASP 的生图提示词优化总导演。你的任务不是简单润色，而是分析、增删、纠偏和重写图片生成提示词。

硬规则：
1. 输出必须是 JSON，不要 Markdown，不要解释。
2. enhanced_prompt 只能写可执行的画面生成指令。
3. 项目名、账号名、人名、昵称、老板称呼、IP 名称都属于干扰因素，不能作为画面主体，不能出现在 enhanced_prompt。
4. 如果项目名中含有物体词，例如苹果、玫瑰、龙、佛、小鹿、月亮，且产品字段不是该物体，必须过滤，不能生成该物体。
5. 画面主体必须优先绑定到产品字段，其次是用户原始提示词中的明确产品，不得被项目名污染。
6. 如果原始提示词含人名但未提供人设参考图，只能改写为手部、背影、工作人员局部动作，不能生成可识别人物或正脸。
7. 优化后必须包含：主体、材质/质感、构图、光线、背景、约束。
8. 珠宝类必须强化真实材质，避免塑料感、假绿、乱码文字、夸张特效。

返回 JSON 字段：
{
  "enhanced_prompt": "优化后的中文提示词，120-220 字",
  "subject": "最终画面主体",
  "removed_terms": ["被过滤的干扰词"],
  "notes": ["简短说明"]
}"""


def build_user_prompt(
    payload: ImagePromptEnhanceRequest,
    project: Project | None,
    interference_terms: list[str],
) -> str:
    project_data: dict[str, Any] = {}
    if project is not None:
        project_data = {
            "project_name": project.project_name,
            "industry": project.industry,
            "sub_industry": project.sub_industry,
            "product": project.product,
            "personal_intro": project.personal_intro,
            "target_audience": project.target_audience,
        }

    material_hints = material_hints_for_text(" ".join([payload.prompt, project.product if project else ""]))
    return json.dumps(
        {
            "raw_prompt": payload.prompt,
            "mode": payload.mode,
            "size": payload.size,
            "quality": payload.quality,
            "project_data": project_data,
            "interference_terms_must_filter": interference_terms,
            "material_hints": material_hints,
            "rewrite_goal": "生成一个可直接用于图片模型的高质量提示词。过滤所有会污染主体判断的项目名、人名、账号名和昵称。",
        },
        ensure_ascii=False,
        indent=2,
    )


def parse_enhancement_data(data: Any, content: str) -> dict[str, Any]:
    if isinstance(data, dict) and data:
        return data
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {"enhanced_prompt": text}
    return parsed if isinstance(parsed, dict) else {"enhanced_prompt": text}


def extract_interference_terms(raw_prompt: str, project: Project | None) -> list[str]:
    product = project.product if project is not None else ""
    candidates: list[str] = []
    if project is not None:
        candidates.append(project.project_name)
        candidates.extend(project_name_residual_terms(project.project_name, product))
        candidates.extend(extract_person_like_terms(project.personal_intro))
    candidates.extend(extract_person_like_terms(raw_prompt))

    result: list[str] = []
    for item in candidates:
        term = normalize_term(item)
        if not term or term in result:
            continue
        if product and term in product and term != (project.project_name if project else ""):
            continue
        result.append(term)
    return result


def project_name_residual_terms(project_name: str, product: str) -> list[str]:
    residual = project_name.strip()
    for filler in PROJECT_NAME_FILLERS:
        residual = residual.replace(filler, "")
    terms = [residual.strip()]
    terms.extend(re.findall(r"[\u4e00-\u9fff]{2,4}", residual))
    return [term for term in terms if term and term not in product]


def extract_person_like_terms(text: str | None) -> list[str]:
    if not text:
        return []
    terms = re.findall(r"[\u4e00-\u9fff]{1,6}(?:姐|哥|总|老师|老板娘|老板|先生|女士|小姐)", text)
    quoted = re.findall(r"[「《“\"]([^」》”\"]{2,12})[」》”\"]", text)
    for item in quoted:
        if re.search(r"(姐|哥|总|老师|老板娘|老板|先生|女士|小姐)$", item):
            terms.append(item)
    return terms


def normalize_term(value: str | None) -> str:
    return re.sub(r"\s+", "", str(value or "").strip())


def material_hints_for_text(text: str) -> list[str]:
    hints: list[str] = []
    for keyword, hint in JEWELRY_MATERIAL_HINTS.items():
        if keyword in text and hint not in hints:
            hints.append(hint)
    return hints


def sanitize_visual_prompt(prompt: str, terms: list[str], product: str) -> str:
    cleaned = prompt.strip()
    for term in sorted(terms, key=len, reverse=True):
        if not term or term in product:
            continue
        cleaned = cleaned.replace(term, "")
    cleaned = re.sub(r"[「」《》“”\"]", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"，{2,}", "，", cleaned)
    cleaned = re.sub(r"。{2,}", "。", cleaned)
    return cleaned.strip(" ，。") or prompt.strip()


def should_force_project_product(llm_subject: str, product: str) -> bool:
    if not product:
        return False
    if not llm_subject:
        return True
    if product in llm_subject:
        return False
    generic_markers = ["产品字段", "商品实物", "待展示商品", "产品主体", "单件商品", "主体商品"]
    return any(marker in llm_subject for marker in generic_markers) or len(llm_subject) < 3


def fallback_enhanced_prompt(raw_prompt: str, project: Project | None, mode: str) -> str:
    product = project.product if project is not None else "产品主体"
    material_hints = "，".join(material_hints_for_text(f"{raw_prompt} {product}"))
    reference_rule = "参考已上传图片的货品形制、材质纹理和场景关系，" if mode == "image" else ""
    material_part = f"材质要求：{material_hints}。" if material_hints else "材质要求：真实质感、自然纹理、避免塑料感。"
    return (
        f"画面主体必须是{product}。{reference_rule}"
        f"生成高级清透的产品展示图，主体居中清晰，构图干净留白，柔和自然光，背景简洁不抢镜。"
        f"{material_part}"
        f"突出产品结构、质感、细节和高级感。避免乱码文字、项目名图形化、可识别人脸、夸张特效、过度饱和、假绿和廉价塑料质感。"
    )
