# Proposal: Add Account Packaging Generation

**Change ID:** `add-account-packaging-generation`
**Created:** 2026-05-09
**Status:** Draft

---

## Problem Statement

The MVP requires users to turn a short video account project profile into a concrete account packaging strategy before they can generate execution plans, topics, and scripts. Without a structured account packaging module, downstream AI generation lacks reusable positioning context and produces generic content.

This affects operators who need specific guidance for account positioning, persona, target audience, platform bios, content columns, trust-building, and conversion paths. The current codebase already contains an initial account packaging route and UI, but the capability should be captured as an OpenSpec change so implementation, verification, and future archiving have a clear source of truth.

## Proposed Solution

Implement and verify an account packaging generation workflow that:

- Reads an existing project profile.
- Builds structured prompts from project data and module methodology.
- Sends all AI generation through `backend/app/llm/llm_gateway.py`.
- Normalizes the generated result into a stable account packaging response shape.
- Persists an `account_strategy_contexts` record for downstream modules.
- Persists a `generation_records` audit record through the LLM Gateway.
- Provides a frontend route where users can trigger generation and review/copy the result.

## Scope

### In Scope

- Backend API endpoint: `POST /api/strategy/account-package/generate`.
- Prompt builder and output schema for account packaging.
- Mock provider compatibility for local development and acceptance checks.
- Account strategy context persistence linked to project and generation record.
- Frontend API wrapper and project-level account packaging page.
- User-facing display of positioning, persona, target profile, names, bios, columns, trust design, conversion path, platform strategies, provider/model metadata, and latency.

### Out of Scope

- Execution plan generation.
- Topic generation.
- Script generation.
- Full generation history page.
- Multi-user authentication and permissions.
- Manual editing/versioning of account strategy contexts.
- Advanced prompt template management in database.

## Impact Analysis

| Component | Change Required | Details |
|-----------|-----------------|---------|
| Database | Yes | Use `account_strategy_contexts` and `generation_records`; keep JSON fields compatible with SQLite and PostgreSQL. |
| API | Yes | Add or verify account packaging generate endpoint and stable response payload. |
| State | No | Page-local frontend state is sufficient for this MVP slice. |
| UI | Yes | Add or verify project detail navigation and account packaging result view. |
| AI Layer | Yes | Route all generation through `LLMGateway`; support mock and OpenAI-compatible providers. |

## Architecture Considerations

This change follows the existing architecture documented in `openspec/project.md`:

`Vue view -> frontend API wrapper -> FastAPI router -> prompt builder -> LLMGateway -> generation_records -> account_strategy_contexts -> response`

The router should handle HTTP validation and response shaping. Prompt content belongs in `backend/app/prompts`. Persistence details belong in services. Provider-specific behavior must stay inside `backend/app/llm/llm_gateway.py`.

The account strategy context becomes the reusable strategy source for later Sprint work, especially execution plan, topic generation, and script generation.

## Success Criteria

- [ ] A user can select an existing project and generate an account packaging strategy.
- [ ] The generated result includes account positioning, persona, target user profile, account name suggestions, platform bios, content columns, trust design, conversion path, and platform strategies.
- [ ] The backend creates a `generation_records` entry for the AI call.
- [ ] The backend creates an `account_strategy_contexts` entry linked to the project and generation record.
- [ ] The flow works with `LLM_PROVIDER=mock`.
- [ ] The frontend displays the generated result and relevant generation metadata.

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| OpenAI-compatible providers return malformed JSON | Medium | Medium | Normalize gateway output before validating response schema and default missing fields safely. |
| Account packaging output becomes too generic | Medium | High | Include project profile, target audience, platforms, and account methodology in prompts; verify against acceptance criteria. |
| Downstream modules cannot reuse the output | Low | High | Persist a structured `account_strategy_contexts` record with stable fields and raw context data. |
| Local development lacks a real LLM provider | High | Low | Keep mock provider as a first-class verification path. |
