# Admin LLM Channels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build administrator-managed global LLM channel settings for JSVOC.

**Architecture:** Store LLM channels in PostgreSQL through SQLAlchemy/Alembic, protect management endpoints with an admin dependency, and resolve active channel settings in runtime LLM services before falling back to `.env`. Add an admin-only panel to the existing `/settings` page.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, unittest, Next.js/React/TypeScript.

---

### Task 1: Backend Data Model And Admin Authorization

**Files:**
- Create: `backend/app/models/llm_channel.py`
- Create: `backend/app/schemas/llm_channel.py`
- Create: `backend/alembic/versions/20260524_0011_add_llm_channels.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/db/base.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/api/dependencies.py`
- Modify: `.env.example`

- [ ] Write failing tests for admin authorization and channel persistence in `backend/tests/test_llm_channels_api.py`.
- [ ] Add the `LLMChannel` model, Pydantic schemas, Alembic migration, and admin username setting.
- [ ] Register the model in SQLAlchemy metadata.
- [ ] Run `python -m unittest tests.test_llm_channels_api`.

### Task 2: Admin LLM Channel API

**Files:**
- Create: `backend/app/services/llm_channel_service.py`
- Create: `backend/app/api/llm_channels.py`
- Modify: `backend/app/main.py`

- [ ] Write failing API tests for list/create/update/activate/delete and secret masking.
- [ ] Implement service functions that enforce one active channel and preserve API key on empty update.
- [ ] Implement admin-only FastAPI routes.
- [ ] Include the router in `backend/app/main.py`.
- [ ] Run `python -m unittest tests.test_llm_channels_api`.

### Task 3: Runtime Channel Resolution

**Files:**
- Modify: `backend/app/services/llm_channel_service.py`
- Modify: `backend/app/llm/llm_gateway.py`
- Modify: `backend/app/services/image_generation_service.py`
- Modify: `backend/tests/test_llm_channels_api.py`

- [ ] Write failing tests that active channels override `.env` settings for `LLMGateway`.
- [ ] Add `get_effective_llm_settings` to return a settings copy overlaid with the active channel.
- [ ] Update `LLMGateway.generate` and image generation service to resolve active channel settings.
- [ ] Run `python -m unittest tests.test_llm_channels_api tests.test_image_generation_api`.

### Task 4: Frontend Admin Settings Panel

**Files:**
- Create: `frontend-v2/src/lib/api/llmChannels.ts`
- Modify: `frontend-v2/src/app/settings/page.tsx`

- [ ] Add typed API helpers for admin channel endpoints.
- [ ] Extend settings page with admin-only model channel UI for `chuyu111`.
- [ ] Support create, edit, activate, test, and delete states with masked API keys.
- [ ] Run `npm run build` in `frontend-v2`.

### Task 5: Deploy And Verify

**Files:**
- Commit all changed source files.

- [ ] Run backend focused tests.
- [ ] Run frontend production build.
- [ ] Commit and push.
- [ ] Deploy to `8.152.2.222`.
- [ ] Verify `/health`, `/settings`, and admin channel API on production.
