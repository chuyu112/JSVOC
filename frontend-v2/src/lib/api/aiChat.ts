import { api } from "./client";

export type AIChatRole = "user" | "assistant";

export interface AIChatMessage {
  role: AIChatRole;
  content: string;
}

export interface AIChatResponse {
  reply: string;
  provider: string;
  model: string;
  usage: Record<string, unknown>;
  sources: Array<{ title?: string; url: string }>;
  latency_ms: number;
  generation_record_id: number | null;
  conversation_id: string;
  conversation_title: string;
}

export interface AIChatHistoryTurn {
  generation_record_id: number;
  conversation_id: string;
  conversation_title: string;
  user_message: string;
  assistant_message: string;
  provider: string;
  model: string;
  web_search: boolean;
  latency_ms: number | null;
  created_at: string;
}

export interface AIChatConversationSummary {
  conversation_id: string;
  title: string;
  last_user_message: string;
  last_assistant_message: string;
  turn_count: number;
  created_at: string;
  updated_at: string;
}

export async function sendAIChat(
  message: string,
  history: AIChatMessage[] = [],
  webSearch: boolean = false,
  conversationId?: string,
  conversationTitle?: string,
): Promise<AIChatResponse> {
  return api.post<AIChatResponse>("/api/ai-chat", {
    message,
    history,
    web_search: webSearch,
    conversation_id: conversationId,
    conversation_title: conversationTitle,
  });
}

export async function listAIChatHistory(limit: number = 20): Promise<AIChatHistoryTurn[]> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  return api.get<AIChatHistoryTurn[]>(`/api/ai-chat/history?${params.toString()}`);
}

export async function listAIChatConversations(limit: number = 50): Promise<AIChatConversationSummary[]> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  return api.get<AIChatConversationSummary[]>(`/api/ai-chat/conversations?${params.toString()}`);
}

export async function listAIChatConversationHistory(
  conversationId: string,
  limit: number = 50,
): Promise<AIChatHistoryTurn[]> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  return api.get<AIChatHistoryTurn[]>(
    `/api/ai-chat/conversations/${encodeURIComponent(conversationId)}/history?${params.toString()}`,
  );
}
