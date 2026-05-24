import { api } from "./client";

export interface LLMChannel {
  id: number;
  name: string;
  provider: string;
  base_url: string;
  model: string;
  is_active: boolean;
  has_api_key: boolean;
  created_at: string;
  updated_at: string;
}

export interface LLMChannelPayload {
  name: string;
  provider: string;
  base_url: string;
  api_key?: string;
  model: string;
  is_active?: boolean;
}

export interface LLMChannelTestResult {
  success: boolean;
  provider: string;
  model: string;
  message: string;
  latency_ms: number;
  error: string | null;
}

export function listLLMChannels(): Promise<LLMChannel[]> {
  return api.get<LLMChannel[]>("/api/admin/llm-channels");
}

export function createLLMChannel(payload: LLMChannelPayload): Promise<LLMChannel> {
  return api.post<LLMChannel>("/api/admin/llm-channels", payload);
}

export function updateLLMChannel(id: number, payload: Partial<LLMChannelPayload>): Promise<LLMChannel> {
  return api.patch<LLMChannel>(`/api/admin/llm-channels/${id}`, payload);
}

export function activateLLMChannel(id: number): Promise<LLMChannel> {
  return api.post<LLMChannel>(`/api/admin/llm-channels/${id}/activate`);
}

export function testLLMChannel(id: number): Promise<LLMChannelTestResult> {
  return api.post<LLMChannelTestResult>(`/api/admin/llm-channels/${id}/test`);
}

export function deleteLLMChannel(id: number): Promise<{ id: number }> {
  return api.delete<{ id: number }>(`/api/admin/llm-channels/${id}`);
}
