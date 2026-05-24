# Channel Purpose Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route chat, image generation, and video generation through separate admin-configured channels.

**Architecture:** Extend `llm_channels` with a `purpose` field and keep one active channel per purpose. Centralize purpose-specific settings selection in `llm_channel_service`, then update chat/image/video services and admin testing to call the right provider path.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, unittest, Next/React settings page.

---

### Task 1: Backend Schema And Routing

**Files:**
- Modify: `backend/app/models/llm_channel.py`
- Modify: `backend/app/schemas/llm_channel.py`
- Modify: `backend/app/services/llm_channel_service.py`
- Create: `backend/alembic/versions/20260524_0012_add_llm_channel_purpose.py`
- Test: `backend/tests/test_llm_channels_api.py`

- [ ] Add failing tests proving `purpose` is returned and active channels are isolated per purpose.
- [ ] Add `purpose` column with default `chat`.
- [ ] Deactivate only channels with the same purpose.
- [ ] Add settings helpers for chat, image, and video purpose routing.

### Task 2: Admin Test Dispatch

**Files:**
- Modify: `backend/app/api/llm_channels.py`
- Modify: `backend/app/services/image_generation_service.py`
- Modify: `backend/app/services/video_generation_service.py`
- Test: `backend/tests/test_llm_channels_api.py`

- [ ] Add failing tests for image channel testing through `/images/generations`.
- [ ] Keep chat test behavior unchanged.
- [ ] Add image test using a minimal image request.
- [ ] Add video test as a non-generating config check.

### Task 3: Runtime Services

**Files:**
- Modify: `backend/app/llm/llm_gateway.py`
- Modify: `backend/app/services/image_generation_service.py`
- Modify: `backend/app/services/video_generation_service.py`
- Test: `backend/tests/test_image_generation_api.py`
- Test: `backend/tests/test_generation_tasks_api.py`

- [ ] Ensure text generation uses `purpose=chat`.
- [ ] Ensure image generation uses `purpose=image`.
- [ ] Ensure video generation uses `purpose=video`.

### Task 4: Admin UI

**Files:**
- Modify: `frontend-v2/src/lib/api/llmChannels.ts`
- Modify: `frontend-v2/src/app/settings/page.tsx`

- [ ] Add `purpose` to API types and form payload.
- [ ] Add purpose selector in the channel form.
- [ ] Show purpose on channel cards.
- [ ] Keep test messages purpose-aware without exposing secrets.

### Task 5: Verification And Deploy

**Files:**
- Update docs if behavior changes.

- [ ] Run targeted backend tests.
- [ ] Run frontend build or lint if available.
- [ ] Commit and push.
- [ ] Deploy to `8.152.2.222`.
- [ ] Run Alembic migration and verify the production channel list still works.

