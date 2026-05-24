import { apiClient, type ApiResponse } from './client'

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
}

export interface ChatResponse {
  content: string
  data: unknown
  generation_record_id: number | null
  provider: string
  model: string
  usage: Record<string, unknown>
  latency_ms: number
}

export async function sendChatMessage(
  messages: ChatMessage[],
  projectId: number | null = null,
  temperature = 0.7,
): Promise<ChatResponse> {
  const response = await apiClient.post<ApiResponse<ChatResponse>>('/api/chat', {
    project_id: projectId,
    messages,
    temperature,
  })
  return response.data.data
}
