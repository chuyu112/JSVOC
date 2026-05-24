# Delta Spec: Content Generation Pipeline Enrichment

**Change ID:** `enrich-content-generation-pipeline`
**Applies to:** `backend/app/prompts/`, `backend/app/services/`, `backend/app/api/`, `frontend-v2/`

---

## Schema Changes

### ACCOUNT_PACKAGE_OUTPUT_SCHEMA

Added optional properties (no breaking changes to required fields):

```json
{
  "series_positioning": "string — series overall positioning with daytime/nighttime contrast",
  "dual_persona": {
    "daytime": "string — persona during business hours",
    "nighttime": "string — persona during private reflection time"
  },
  "tone_principles": ["string array — e.g., '低说教', '有人味', '强反差'"],
  "material_pool": {
    "books": ["string array"],
    "tv_shows": ["string array"],
    "movies": ["string array"],
    "travel": ["string array"],
    "sports": ["string array"]
  },
  "publishing_rhythm": "string — e.g., '每周5-6条主内容 + 1-2条生活碎片'"
}
```

Existing `content_columns` item schema already supports objects with `name`, `description`, `frequency`, `examples`. Prompt now requires object form instead of plain strings.

### TOPICS_OUTPUT_SCHEMA

Added per-topic scoring objects:

```json
{
  "rubric": {
    "er": "integer 0-5 — Engagement Rate",
    "sr": "integer 0-5 — Share Rate",
    "hp": "integer 0-5 — Hook Power",
    "ql": "integer 0-5 — Quality",
    "na": "integer 0-5 — Narrative",
    "ab": "integer 0-5 — Authority",
    "sat": "integer 0-5 — Satisfaction"
  },
  "hkr": {
    "h": "integer 0-5 — Happy/好奇心",
    "k": "integer 0-5 — Knowledge/信息量",
    "r": "integer 0-5 — Resonance/情绪共鸣"
  }
}
```

`score` field (0-100 integer) is computed from rubric via formula:
`composite = (ER×1.5 + SR×1.5 + HP×1.5 + QL + NA + AB + SAT) / 8.5 × 2.0`

### SCRIPT_OUTPUT_SCHEMA

Added per-script rubric object (same 7 dimensions as topics, no HKR).

---

## Prompt Changes

### strategy_bundle_prompt.py

- **Benchmark injection**: Reads `project.benchmark_accounts` and formats into `benchmark_part` string. Includes emphasis rule that benchmark style is the PRIMARY framework (60%).
- **60/30/10 ratio**: Added explicit content ratio section.
- **Enriched fields**: Prompt now requires `series_positioning`, `dual_persona`, `tone_principles`, `material_pool`, `publishing_rhythm` in addition to existing fields.
- **Content form requirements**: "女老板日常/日记/成长" as main theme, jade as background material only.

### topic_prompt.py

- **HKR质检**: System prompt now requires Happy/Knowledge/Resonance evaluation per topic.
- **7-dimension rubric**: System prompt requires ER/SR/HP/QL/NA/AB/SAT scoring per topic.
- **60/30/10 ratio**: Added to user prompt generation requirements.
- **Score computation**: Formula documented in system prompt.

### script_prompt.py

- **khazix-writer style**: 7 style rules added (rhythm, personal voice, judgment, emotional authenticity, cultural elevation, callback, reverse argumentation).
- **Absolute prohibitions**: Banned transitions, meta-phrases, generic openings, punctuation habits, structural traps.
- **Structure template**: Opening→Background→Core→Elevation→Closing.
- **7-dimension rubric**: Each script scored on same 7 dimensions.
- **60/30/10 ratio**: Added to system prompt.

---

## Service Changes

### account_package_normalizer.py

- Added `extract_account_package_extras(data)` helper that pulls optional new fields (`series_positioning`, `dual_persona`, `tone_principles`, `material_pool`, `publishing_rhythm`) from raw LLM output.
- Returns empty dict if fields missing — backward compatible.

### topic_service.py

- Added rubric parsing: extracts `rubric` object from LLM response and stores in `topic_data`.
- Added HKR parsing: extracts `hkr` object from LLM response and stores in `topic_data`.
- Added `_ensure_int_score()` helper for 0-5 range validation.

### script_service.py

- Added rubric parsing: extracts `rubric` object from LLM response and stores in `script_data`.

---

## API Route Changes

### strategy_bundle.py

- `generate_account_package_and_execution_plan`:
  - Calls `extract_account_package_extras(account_package_data)` after normalization.
  - Stores extras in `context_data["account_package_extras"]`.
- `get_latest_account_package`:
  - Reads extras from `context_data["account_package_extras"]`.
  - Returns `series_positioning`, `dual_persona`, `tone_principles`, `material_pool`, `publishing_rhythm` in response.

---

## Frontend Changes

### Topic Page (`projects/[id]/topics/page.tsx`)

- Added `ScoreBar` component: 5-bar visual score indicator.
- Added `RubricMini` component: displays 7 dimension score bars + HKR bars on each topic card.
- Updated `topicText()` copy function to include rubric/hkr scores in clipboard output.

### Script Page (`projects/[id]/topics/[topicId]/script/page.tsx`)

- Added `ScoreBar` and `RubricMini` components for script cards.

---

## Data Migration Notes

No database schema migrations required. All new fields use existing JSON/JSONB columns:

- `account_strategy_contexts.context_data` — stores `account_package_extras`
- `topics.topic_data` — stores `rubric` and `hkr`
- `scripts.script_data` — stores `rubric`

Existing records without these fields will simply return `null` for the new API response fields.
