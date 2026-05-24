# Proposal: Enrich Content Generation Pipeline

**Change ID:** `enrich-content-generation-pipeline`
**Created:** 2026-05-18
**Status:** In Progress

---

## Problem Statement

The current content generation pipeline produces generic, industry-dominant content that lacks the depth and specificity of professional content strategy. Specifically:

1. **Account packaging is too thin** — outputs only basic fields (positioning, persona, 4 columns) without series positioning, tone principles, material pool, or dual-persona design. The result feels like a template, not a strategy.

2. **Content lacks quality control** — there is no rubric system to score topics or scripts across dimensions like engagement, shareability, hook power, narrative structure, authority, and satisfaction. Generations are unmeasured.

3. **Scripts read like AI** — no enforced writing style rules. Transitions like "首先...其次...最后", meta-phrases like "说白了", and generic openings like "随着技术的不断进步" slip through constantly.

4. **Benchmark accounts are underutilized** — the platform accepts benchmark accounts in project data but does not inject them into prompts effectively. Generated content remains industry-first instead of benchmark-style-first.

5. **No content ratio discipline** — the platform does not enforce any balance between benchmark-style content, industry content, and free-form creative content. Generated topics are 100% industry-focused even when the strategy calls for 60% personal growth / 30% industry / 10% free-form.

## Proposed Solution

Integrate three external knowledge sources and internal structural improvements into the content generation pipeline:

1. **`cheat-on-content` rubric system** — 7-dimension scoring (ER, SR, HP, QL, NA, AB, SAT) with composite formula and HKR quality check (Happy, Knowledge, Resonance) for topics.

2. **`khazix-skills` writer style** — Rhythm, personal voice, judgment, emotional authenticity, cultural elevation, callback loops, reverse argumentation. Plus absolute prohibitions on AI-telltale phrases and structures.

3. **Benchmark account injection** — Make benchmark account style the PRIMARY content framework (60%), industry context secondary (30%), with 10% free-form creative divergence.

4. **Enriched account packaging** — Add series positioning, daytime/nighttime dual persona, tone principles, material pool (books/tv/travel/sports), and publishing rhythm to the account package output.

## Scope

### In Scope

- Backend prompt updates: `strategy_bundle_prompt.py`, `topic_prompt.py`, `script_prompt.py`.
- Output schema extensions: `ACCOUNT_PACKAGE_OUTPUT_SCHEMA`, `TOPICS_OUTPUT_SCHEMA`, `SCRIPT_OUTPUT_SCHEMA`.
- Rubric and HKR parsing in `topic_service.py` and `script_service.py`.
- Benchmark account injection in `strategy_bundle_prompt.py`.
- 60/30/10 content ratio rules in all three prompts.
- Normalizer updates to handle new optional fields without breaking existing data.
- API route updates to persist and return enriched fields in `context_data`.
- Frontend score display components (`ScoreBar`, `RubricMini`) on topic and script pages.

### Out of Scope

- Full benchmark video analysis and injection (future change).
- Topic/script dual-layer structural change (`白天一幕 + 睡前独白`) — requires data model extension.
- Automated content calibration loop (Score→Predict→Publish→Retro→Evolve) — requires publish data integration.
- Content series grouping (7 thematic groups) — requires new execution plan matrix.
- Frontend account packaging page redesign to show new fields.

## Impact Analysis

| Component | Change Required | Details |
|-----------|-----------------|---------|
| Database | No schema migration | New fields stored in existing JSON/JSONB columns (`topic_data`, `script_data`, `context_data`). |
| API | Yes | `GET /api/strategy/account-package-execution-plan/projects/{id}/latest` now returns `series_positioning`, `dual_persona`, `tone_principles`, `material_pool`, `publishing_rhythm`. |
| Prompts | Yes | Three prompt builders updated with rubric, style rules, benchmark injection, and ratio discipline. |
| AI Layer | Yes | Output schemas expanded; LLM now generates richer structured data with rubric objects. |
| Frontend | Yes | Topic and script cards now display 7-dimension score bars and HKR mini scores. |

## Architecture Considerations

All prompt changes follow the existing pattern: prompt builder constructs system + user prompts, `LLMGateway` executes with output schema validation, normalizer sanitizes malformed responses, service persists to database.

The rubric scores are not stored as separate columns. They are embedded in `topic_data` and `script_data` JSONB fields to avoid schema migrations during rapid iteration.

Benchmark accounts are read from `Project.benchmark_accounts` (already added via migration `20260517_0007_add_benchmark_accounts_to_projects`).

## Success Criteria

- [ ] Account package generation includes `series_positioning`, `dual_persona`, `tone_principles`, `material_pool`, and `publishing_rhythm`.
- [ ] Topic generation outputs include `rubric` (7 dimensions) and `hkr` (3 dimensions) objects.
- [ ] Script generation outputs include `rubric` (7 dimensions) object.
- [ ] Benchmark accounts are injected into strategy bundle prompts and influence output style.
- [ ] 60/30/10 content ratio rules are present in all three main prompts.
- [ ] Frontend displays rubric score bars on topic cards and script cards.
- [ ] khazix-writer style rules and prohibited phrases are enforced in script generation.

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LLM ignores 60/30/10 ratio and defaults to industry content | High | High | Add explicit prohibition rules; consider hard-constraint generation (e.g., generate personal-growth topics first, then assign industry scenes). |
| Rubric scores are inconsistent or inflated | Medium | Medium | Composite formula normalizes to 0-100; future calibration loop will retroactively adjust. |
| New optional fields break normalizer on malformed responses | Low | Medium | Normalizer already defaults missing fields safely; extras extracted separately. |
| Prompt size increase causes token budget overflow | Medium | Low | Monitor latency; if exceeds 120s, split generation into smaller batches. |
