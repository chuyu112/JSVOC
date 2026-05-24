# Implementation Tasks: Enrich Content Generation Pipeline

**Change ID:** `enrich-content-generation-pipeline`

---

## Phase 1: Content Quality Rubric & HKR

- [x] 1.1 Add 7-dimension rubric schema (ER, SR, HP, QL, NA, AB, SAT) to `TOPICS_OUTPUT_SCHEMA` and `SCRIPT_OUTPUT_SCHEMA`.
- [x] 1.2 Add HKR schema (H, K, R) to `TOPICS_OUTPUT_SCHEMA`.
- [x] 1.3 Update `topic_prompt.py` system prompt with HKR质检 rules and 7-dimension scoring instructions.
- [x] 1.4 Update `script_prompt.py` system prompt with 7-dimension scoring instructions.
- [x] 1.5 Add rubric/HKR parsing in `topic_service.py` — store in `topic_data` JSONB.
- [x] 1.6 Add rubric parsing in `script_service.py` — store in `script_data` JSONB.
- [x] 1.7 Add composite score formula documentation in prompts.

**Quality Gate:**
- [x] Backend imports without errors
- [x] Topic generation returns rubric and hkr objects in response
- [x] Script generation returns rubric object in response

---

## Phase 2: khazix-Writer Style Integration

- [x] 2.1 Add khazix-writer style rules to `script_prompt.py` system prompt (rhythm, personal voice, judgment, emotional authenticity, cultural elevation, callback, reverse argumentation).
- [x] 2.2 Add absolute prohibitions list (banned transitions, meta-phrases, openings, punctuation habits, structural traps).
- [x] 2.3 Add structure template (Opening→Background→Core→Elevation→Closing) to script prompt.
- [x] 2.4 Verify script generation output no longer contains prohibited phrases.

**Quality Gate:**
- [x] Script generation produces text without "首先...其次...最后" or "在当今AI快速发展的时代"
- [x] Scripts feel conversational, not report-like

---

## Phase 3: Benchmark Account Injection

- [x] 3.1 Verify `Project.benchmark_accounts` column exists (migration `20260517_0007`).
- [x] 3.2 Update `strategy_bundle_prompt.py` to read `project.benchmark_accounts` and inject into user prompt.
- [x] 3.3 Add benchmark emphasis rule: "对标账号的内容形式、表达节奏、人设逻辑是主骨架。行业只是主人公的日常素材和背景。"
- [x] 3.4 Test generation with benchmark account "飙马野人" and verify output style shifts from industry-dominant to female-growth-vlog style.

**Quality Gate:**
- [x] Account package `content_columns` reference female growth/diary themes, not just jade industry
- [x] `account_positioning` centers on "女老板真实成长日记" rather than "翡翠行业号"

---

## Phase 4: 60/30/10 Content Ratio

- [x] 4.1 Add 60/30/10 ratio rule to `strategy_bundle_prompt.py`.
- [x] 4.2 Add 60/30/10 ratio rule to `topic_prompt.py`.
- [x] 4.3 Add 60/30/10 ratio rule to `script_prompt.py`.
- [ ] 4.4 Verify topic generation actually follows ratio (currently still industry-heavy — needs structural fix).
- [ ] 4.5 Implement hard constraint: title/hook must not contain industry keywords more than 30% of the time.

**Quality Gate:**
- [ ] 5 generated topics have ≤2 industry-dominant titles (pending structural fix)
- [x] Ratio rules are present in all three prompts

---

## Phase 5: Enriched Account Packaging

- [x] 5.1 Extend `ACCOUNT_PACKAGE_OUTPUT_SCHEMA` with optional fields: `series_positioning`, `dual_persona`, `tone_principles`, `material_pool`, `publishing_rhythm`.
- [x] 5.2 Update `strategy_bundle_prompt.py` user prompt to require all new fields.
- [x] 5.3 Update `normalize_account_package` to safely handle new fields.
- [x] 5.4 Add `extract_account_package_extras` helper for optional fields.
- [x] 5.5 Update `strategy_bundle.py` API route to store extras in `context_data.account_package_extras`.
- [x] 5.6 Update `get_latest_account_package` endpoint to return new fields.
- [x] 5.7 Test enriched generation and verify all new fields are populated.

**Quality Gate:**
- [x] Backend starts without errors
- [x] Generated account package includes `series_positioning`, `dual_persona`, `tone_principles`, `material_pool`, `publishing_rhythm`
- [x] `material_pool` contains specific books, shows, travel destinations, and sports
- [x] `content_columns` are objects with name/description/frequency/examples

---

## Phase 6: Frontend Score Display

- [x] 6.1 Add `ScoreBar` component to topic page (`projects/[id]/topics/page.tsx`).
- [x] 6.2 Add `RubricMini` component to topic page for 7-dimension + HKR display.
- [x] 6.3 Add `ScoreBar` and `RubricMini` components to script page (`projects/[id]/topics/[topicId]/script/page.tsx`).
- [x] 6.4 Update `topicText()` copy function to include rubric/hkr in clipboard output.

**Quality Gate:**
- [x] Topic cards display score bars for ER, SR, HP, QL, NA, AB, SAT
- [x] Script cards display score bars
- [x] Copy-to-clipboard includes rubric scores

---

## Phase 7: Integration & Verification

- [ ] 7.1 Full end-to-end test: project creation → account package generation → topic generation → script generation.
- [ ] 7.2 Verify all generation records are persisted with correct module names.
- [ ] 7.3 Verify enriched account package is returned by `GET /api/strategy/account-package-execution-plan/projects/{id}/latest`.
- [ ] 7.4 Frontend build passes (`npm run build` in `frontend-v2`).
- [ ] 7.5 Update OpenSpec change status to Complete.

**Quality Gate:**
- [ ] Full flow verified manually
- [ ] Frontend build passes
- [ ] OpenSpec documentation synced

---

## Completion Checklist

- [ ] All phases complete
- [ ] All quality gates passed
- [ ] Documentation synced
- [ ] Ready for `/openspec-archive enrich-content-generation-pipeline`
