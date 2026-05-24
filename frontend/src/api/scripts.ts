import { apiClient, type ApiResponse } from './client'

export interface ScriptData {
  hook: string
  subtitle_points: string[]
  comment_guidance: string
  private_message_guidance: string
  duration: string
  goal: string
}

export interface Script {
  id: number
  project_id: number
  topic_id: number
  title: string
  script_type: string
  platform: string
  script_content: string
  shot_suggestions: string[]
  conversion_script: string
  script_data: ScriptData
  created_at: string
}

export interface ScriptGenerateResponse {
  script: Script
  generation_record_id: number | null
  provider: string
  model: string
  usage: Record<string, unknown>
  latency_ms: number
}

export async function generateScript(
  projectId: number,
  topicId: number,
  platform: string | null,
  scriptType = '聊观点',
  duration = '60秒',
  goal = '私信获客',
): Promise<ScriptGenerateResponse> {
  const response = await apiClient.post<ApiResponse<ScriptGenerateResponse>>(
    '/api/creation/scripts/generate',
    {
      project_id: projectId,
      topic_id: topicId,
      platform,
      script_type: scriptType,
      duration,
      goal,
    },
  )
  return response.data.data
}

export async function listTopicScripts(topicId: number): Promise<Script[]> {
  const response = await apiClient.get<ApiResponse<Script[]>>(`/api/topics/${topicId}/scripts`)
  return response.data.data
}

export async function listProjectScripts(projectId: number): Promise<Script[]> {
  const response = await apiClient.get<ApiResponse<Script[]>>(
    `/api/projects/${projectId}/scripts`,
  )
  return response.data.data
}
