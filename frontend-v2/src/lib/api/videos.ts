import { api } from "./client";

export interface VideoGenerateRequest {
  project_id: number | null;
  prompt: string;
  options?: Record<string, unknown>;
}

export interface VideoTaskResponse {
  task_id: number;
  task_type: string;
  status: string;
  project_id: number | null;
  input_data: Record<string, unknown>;
  result_data: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface VideoModelConfig {
  key: string;
  label: string;
  value: string;
  kind: string;
  resolutions: string[];
  pricing_yuan_per_second: Record<string, number>;
  available: boolean;
  disabled_reason?: string | null;
}

export async function listVideoModels(): Promise<VideoModelConfig[]> {
  return api.get<VideoModelConfig[]>("/api/creation/videos/models");
}

export async function generateVideoAsync(
  projectId: number | null,
  prompt: string,
  options: Record<string, unknown> = {},
): Promise<VideoTaskResponse> {
  const requestOptions = { ...options };
  const payload: Record<string, unknown> = {
    project_id: projectId,
    prompt,
    options: requestOptions,
  };
  for (const key of [
    "first_frame",
    "last_frame",
    "reference_media",
    "reference_medias",
    "reference_images",
    "reference_videos",
    "reference_audios",
  ]) {
    if (requestOptions[key]) {
      payload[key] = requestOptions[key];
      delete requestOptions[key];
    }
  }
  return api.post<VideoTaskResponse>("/api/creation/videos/generate/async", payload);
}

export interface EnhancePromptRequest {
  prompt: string;
  material_hint?: string;
}

export interface EnhancePromptResponse {
  enhanced_prompt: string;
}

export async function enhancePrompt(payload: EnhancePromptRequest): Promise<EnhancePromptResponse> {
  return api.post<EnhancePromptResponse>("/api/creation/videos/enhance-prompt", payload);
}
