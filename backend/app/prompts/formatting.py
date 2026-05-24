import json
from typing import Any


def format_prompt_list(value: Any) -> str:
    if isinstance(value, list):
        return " / ".join(format_prompt_value(item) for item in value)
    return format_prompt_value(value)


def format_prompt_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        name = value.get("name") or value.get("title")
        description = value.get("description") or value.get("summary")
        if name and description:
            return f"{name}: {description}"
        if name:
            return str(name)
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return format_prompt_list(value)
    return str(value)
