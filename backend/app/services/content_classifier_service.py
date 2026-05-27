import re

DRAMA_INDICATORS = [
    r'[""""].+?[""""]',
    r"[''].+?['']",
    r"（.+?扮演.+?）",
    r"\(.+?扮演.+?\)",
    r"场景[一二三四五六七八九十\d]+",
    r"切到",
    r"画面一转",
    r"镜头切换到",
    r"特写",
    r"远景",
    r"近景",
    r"中景",
    r"推拉",
    r"摇镜头",
    r"淡入",
    r"淡出",
    r"黑屏",
    r"字幕",
    r"旁白",
    r"内心OS",
    r"闪回",
    r"回忆",
    r"\n.+?：.+?\n",
    r"\n.+?:.+?\n",
]

DRAMA_SCORE_THRESHOLD = 3
TALKING_HEAD_SCORE_THRESHOLD = 1


def classify_script(script: str) -> dict[str, str | float]:
    if not script or not script.strip():
        return {"structure_type": "mixed", "confidence": 0.0, "method": "fallback"}

    script = script.strip()
    drama_score = 0
    matched_patterns: list[str] = []

    for pattern in DRAMA_INDICATORS:
        matches = re.findall(pattern, script, re.MULTILINE)
        if matches:
            drama_score += len(matches)
            matched_patterns.append(pattern)

    lines = [line.strip() for line in script.splitlines() if line.strip()]
    total_lines = len(lines)
    if total_lines == 0:
        return {"structure_type": "mixed", "confidence": 0.0, "method": "fallback"}

    quote_chars = {'"', "'", "“", "”", "‘", "’", "（", "("}
    end_quote_chars = {'"', "'", "“", "”", "‘", "’", "）", ")"}
    dialogue_lines = sum(
        1
        for line in lines
        if (line[0] in quote_chars and line[-1] in end_quote_chars)
        or re.search(r"^.+?[：:].+?$", line)
    )
    dialogue_ratio = dialogue_lines / total_lines

    if dialogue_ratio > 0.3:
        drama_score += int(dialogue_ratio * 10)

    if drama_score >= DRAMA_SCORE_THRESHOLD:
        confidence = min(0.5 + (drama_score - DRAMA_SCORE_THRESHOLD) * 0.05, 0.95)
        return {"structure_type": "drama", "confidence": confidence, "method": "rule"}

    info_density = sum(
        1
        for line in lines
        if any(
            kw in line
            for kw in ["因为", "所以", "但是", "其实", "真相", "方法", "步骤", "第一", "第二", "第三", "注意", "千万", "不要", "一定要"]
        )
    )
    info_ratio = info_density / total_lines

    if info_ratio > 0.2 and dialogue_ratio < 0.1:
        confidence = min(0.6 + info_ratio * 0.3, 0.9)
        return {"structure_type": "talking_head", "confidence": confidence, "method": "rule"}

    return {"structure_type": "mixed", "confidence": 0.5, "method": "rule"}
