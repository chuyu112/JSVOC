# Admin LLM Channels Design

## Goal

JSVOC needs administrator-managed LLM channels so production model settings are editable from the admin settings page instead of being limited to static `.env` values. The feature is global: administrator changes affect all users and all LLM-backed generation flows.

## Scope

The first version supports text and image LLM settings:

- `LLM_PROVIDER`
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`

Video generation settings remain separate because JSVOC currently treats video generation as a dedicated Seedance/Ark service via `VIDEO_GENERATION_*`.

## Administrator Access

Only users whose username is listed in `ADMIN_USERNAMES` can view or mutate LLM channel settings. The default server administrator is `chuyu111`. Backend authorization is enforced on every admin channel endpoint, so hiding the UI is not the security boundary.

## Data Model

Add a new `llm_channels` table:

- `id`
- `name`
- `provider`
- `base_url`
- `api_key`
- `model`
- `is_active`
- `created_at`
- `updated_at`

Only one channel can be active at a time. API keys are stored server-side and are never returned to the frontend. Read responses expose `has_api_key` instead.

## Backend Behavior

`LLMGateway` and image generation resolve effective LLM settings at runtime:

1. If an active database channel exists, use that channel's provider, base URL, API key, and model.
2. If no active channel exists, fall back to `.env` settings.

This preserves existing deployment behavior while allowing administrators to switch channels without redeploying.

## API

New admin endpoints:

- `GET /api/admin/llm-channels`
- `POST /api/admin/llm-channels`
- `PATCH /api/admin/llm-channels/{channel_id}`
- `POST /api/admin/llm-channels/{channel_id}/activate`
- `POST /api/admin/llm-channels/{channel_id}/test`
- `DELETE /api/admin/llm-channels/{channel_id}`

Editing a channel with an empty API key preserves the existing key. Sending a non-empty API key replaces it.

## Frontend

The existing `/settings` page gains an admin-only "Model Channels" section when the current user is `chuyu111`. It supports listing, creating, editing, activating, testing, and deleting channels. Non-admin users keep the current settings page only.

## Error Handling

Non-admin requests return `403`. Missing channels return `404`. Invalid provider/base URL/model input returns validation errors. Channel tests return structured success or failure messages without exposing secrets.

## Verification

Backend tests cover:

- Admin-only authorization.
- API key masking and preserve-on-empty update.
- Single active channel behavior.
- `LLMGateway` resolving the active database channel.

Frontend build validates the admin settings UI compiles.
