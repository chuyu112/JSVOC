import json
from typing import Any

from app.schemas.account_strategy_context import AccountPackageResult


def normalize_account_package(data: Any) -> AccountPackageResult:
    if not isinstance(data, dict):
        data = {}

    normalized = {
        "account_positioning": ensure_string(data.get("account_positioning")),
        "persona": ensure_string(data.get("persona")),
        "target_user_profile": ensure_dict_or_summary(data.get("target_user_profile")),
        "account_names": ensure_string_list(data.get("account_names")),
        "bios": ensure_string_dict(data.get("bios")),
        "content_columns": ensure_content_columns(data.get("content_columns")),
        "trust_design": ensure_string_list(data.get("trust_design")),
        "conversion_path": ensure_string_list(data.get("conversion_path")),
        "platform_strategies": ensure_dict(data.get("platform_strategies")),
        "rubric_notes": ensure_dict(data.get("rubric_notes")),
    }
    return AccountPackageResult.model_validate(normalized)


def extract_account_package_extras(data: Any) -> dict[str, Any]:
    """Extract optional new fields that are not in AccountPackageResult schema."""
    if not isinstance(data, dict):
        return {}
    extras: dict[str, Any] = {}
    for key in ["series_positioning", "persona_layers", "tone_principles", "material_pool", "publishing_rhythm", "content_structure_template"]:
        value = data.get(key)
        if value is not None:
            extras[key] = value
    return extras


def ensure_string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def ensure_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            if isinstance(item, list):
                result.extend(ensure_string_list(item))
            else:
                result.append(ensure_string(item))
        return result
    if value is None:
        return []
    return [ensure_string(value)]


def ensure_string_dict(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        return {str(key): ensure_string(item) for key, item in value.items()}
    return {}


def ensure_content_columns(value: Any) -> list[Any]:
    if isinstance(value, list):
        return [ensure_content_column(item) for item in value]
    if value is None:
        return []
    return [ensure_content_column(value)]


def ensure_content_column(value: Any) -> Any:
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return [ensure_content_column(item) for item in value]
    return ensure_string(value)


def ensure_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def ensure_dict_or_summary(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    return {"summary": str(value)}
