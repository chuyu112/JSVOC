# Channel Purpose Routing Design

## Goal

Split admin provider configuration into three independent runtime channels: chat, image generation, and video generation.

## Design

Each LLM channel gets a `purpose` value:

- `chat`: text chat, planning/content generation, prompt enhancement, and all calls through `LLMGateway`.
- `image`: image generation and image editing endpoints.
- `video`: Seedance/Ark video generation endpoints.

Only one channel can be active per purpose. Existing channels default to `chat` so current production configuration keeps working.

## Runtime Routing

`llm_channel_service` owns purpose selection. Chat keeps using `get_effective_llm_settings(..., purpose="chat")`. Image generation reads the active `image` channel and maps its provider/base URL/key/model into the existing image generation request flow. Video generation reads the active `video` channel and maps base URL/key/model into the existing video settings fields.

## Admin Testing

The existing `/api/admin/llm-channels/{id}/test` endpoint dispatches based on purpose:

- Chat channels run the existing lightweight chat completions test.
- Image channels call the image generation endpoint with a minimal test prompt. This is a real provider call and may consume a small amount of channel quota.
- Video channels perform a non-generating configuration check for base URL, API key, and resolved model endpoint. Real video generation remains tested from the video workflow because submitting a video task is expensive.

## UI

The settings page adds a purpose selector and shows purpose badges on channel cards. The test button remains per-channel and displays the purpose-specific result.

