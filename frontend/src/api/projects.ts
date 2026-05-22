import { apiClient, type ApiResponse } from './client'

export interface ProjectPayload {
  project_name: string
  industry: string
  sub_industry: string | null
  product: string
  personal_intro: string
  target_audience: string
  platforms: string[]
  current_stage: string
}

export interface Project extends ProjectPayload {
  id: number
  user_id: number | null
  created_at: string
  updated_at: string
}

export async function listProjects(): Promise<Project[]> {
  const response = await apiClient.get<ApiResponse<Project[]>>('/api/projects')
  return response.data.data
}

export async function getProject(projectId: number): Promise<Project> {
  const response = await apiClient.get<ApiResponse<Project>>(`/api/projects/${projectId}`)
  return response.data.data
}

export async function createProject(payload: ProjectPayload): Promise<Project> {
  const response = await apiClient.post<ApiResponse<Project>>('/api/projects', payload)
  return response.data.data
}

export async function updateProject(
  projectId: number,
  payload: Partial<ProjectPayload>,
): Promise<Project> {
  const response = await apiClient.put<ApiResponse<Project>>(`/api/projects/${projectId}`, payload)
  return response.data.data
}

export async function deleteProject(projectId: number): Promise<void> {
  await apiClient.delete<ApiResponse<null>>(`/api/projects/${projectId}`)
}
