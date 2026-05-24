import { apiClient, type ApiResponse } from './client'

export interface TopicData {
  user_pain_point: string
  hook: string
  shooting_suggestion: string
  conversion_method: string
}

export interface Topic {
  id: number
  project_id: number
  title: string
  content_type: string
  platform: string
  goal: string
  selling_point: string | null
  score: number
  topic_data: TopicData
  created_at: string
}

export interface TopicGenerateResponse {
  topics: Topic[]
  generation_record_id: number | null
  provider: string
  model: string
  usage: Record<string, unknown>
  latency_ms: number
}

export async function generateTopics(
  projectId: number,
  platform = '抖音',
  goal = '获客',
  count = 20,
): Promise<TopicGenerateResponse> {
  const response = await apiClient.post<ApiResponse<TopicGenerateResponse>>(
    '/api/creation/topics/generate',
    {
      project_id: projectId,
      platform,
      goal,
      count,
    },
  )
  return response.data.data
}

export async function listProjectTopics(projectId: number): Promise<Topic[]> {
  const response = await apiClient.get<ApiResponse<Topic[]>>(`/api/projects/${projectId}/topics`)
  return response.data.data
}
