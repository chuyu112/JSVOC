import { apiClient, type ApiResponse } from './client'

export interface GeneratedImage {
  url?: string | null
  b64_json?: string | null
  revised_prompt?: string | null
}

export interface ImageGenerateResponse {
  images: GeneratedImage[]
  generation_record_id: number | null
  provider: string
  model: string
  usage: Record<string, unknown>
  latency_ms: number
}

export async function generateImage(
  prompt: string,
  projectId: number | null = null,
  size = '1024x1024',
  n = 1,
): Promise<ImageGenerateResponse> {
  const response = await apiClient.post<ApiResponse<ImageGenerateResponse>>(
    '/api/images/generate',
    {
      project_id: projectId,
      prompt,
      size,
      n,
    },
  )
  return response.data.data
}
