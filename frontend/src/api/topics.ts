import { apiClient, type ApiResponse } from './client'

export interface TopicData {
  content_format?: TopicContentFormat
  user_pain_point: string
  hook: string
  shooting_suggestion: string
  conversion_method: string
  shooting_script?: string
  seedance_video_prompt?: string
  image_prompt?: string
  image_edit_prompt?: string
}

export type TopicContentFormat = 'video' | 'image' | 'image_to_image'

export interface Topic {
  id: number
  project_id: number
  title: string
  content_type: string
  platform: string
  goal: string
  selling_point: string | null
  score: number
  is_favorite: boolean
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
  contentFormat: TopicContentFormat = 'video',
  count = 10,
  existingTitles: string[] = [],
  topicIndex?: number,
  generationBatchId?: string,
  generationTargetCount?: number,
  personaReferenceImageUploaded = false,
): Promise<TopicGenerateResponse> {
  const response = await apiClient.post<ApiResponse<TopicGenerateResponse>>(
    '/api/creation/topics/generate',
    {
      project_id: projectId,
      platform,
      goal,
      content_format: contentFormat,
      count,
      existing_titles: existingTitles,
      topic_index: topicIndex,
      generation_batch_id: generationBatchId,
      generation_target_count: generationTargetCount,
      persona_reference_image_uploaded: personaReferenceImageUploaded,
    },
  )
  return response.data.data
}

export async function listProjectTopics(projectId: number): Promise<Topic[]> {
  const response = await apiClient.get<ApiResponse<Topic[]>>(`/api/projects/${projectId}/topics`)
  return response.data.data
}

export async function updateTopicFavorite(topicId: number, isFavorite: boolean): Promise<Topic> {
  const response = await apiClient.patch<ApiResponse<Topic>>(`/api/topics/${topicId}/favorite`, {
    is_favorite: isFavorite,
  })
  return response.data.data
}

export async function deleteTopic(topicId: number): Promise<void> {
  await apiClient.delete<ApiResponse<{ id: number }>>(`/api/topics/${topicId}`)
}
