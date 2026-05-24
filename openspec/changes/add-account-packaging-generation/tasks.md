# Implementation Tasks: Add Account Packaging Generation

**Change ID:** `add-account-packaging-generation`

---

## Phase 1: Foundation (Data Layer)

- [x] 1.1 Verify `AccountStrategyContext` model fields cover positioning, persona, target user profile, account names, bios, columns, trust design, conversion path, platform strategies, and downstream context data.
- [x] 1.2 Verify `GenerationRecord` persistence captures module name, input data, output data, provider, model, prompt version, token usage, latency, and project id.
- [x] 1.3 Verify account strategy context service creates records linked to project and generation record.

**Quality Gate:**
- [x] Backend imports without errors
- [x] Database tables initialize in local development

---

## Phase 2: Business Logic (Prompt and Gateway)

- [x] 2.1 Define account packaging module name, prompt version, output schema, and prompt builder.
- [x] 2.2 Implement account packaging generation through `LLMGateway.generate`.
- [x] 2.3 Normalize generated account packaging data before persistence and response.
- [x] 2.4 Handle missing project and LLM failure paths with appropriate HTTP errors.

**Quality Gate:**
- [x] `LLM_PROVIDER=mock` returns a valid account packaging payload
- [x] Failed provider calls do not create incomplete account strategy contexts

---

## Phase 3: API and User Interface

- [x] 3.1 Expose `POST /api/strategy/account-package/generate`.
- [x] 3.2 Add or verify frontend typed API wrapper for account packaging generation.
- [x] 3.3 Add or verify account packaging page reachable from project detail.
- [x] 3.4 Display generated strategy sections and provider/model/latency metadata.
- [x] 3.5 Provide user feedback for loading, success, empty, and error states.

**Quality Gate:**
- [x] Frontend build passes
- [x] Account packaging route renders without runtime errors

---

## Phase 4: Integration & Verification

- [x] 4.1 Exercise the full project-to-account-package flow with mock provider.
- [x] 4.2 Verify the response includes all acceptance-required sections.
- [x] 4.3 Verify generated account strategy context and generation record are persisted.
- [x] 4.4 Update related documentation if implementation behavior differs from existing docs.

**Quality Gate:**
- [x] Backend route verified manually or by test
- [x] Frontend flow verified manually
- [x] Documentation remains consistent with implementation

---

## Completion Checklist

- [x] All phases complete
- [x] All quality gates passed
- [x] Documentation synced
- [x] Ready for `/openspec-archive add-account-packaging-generation`
