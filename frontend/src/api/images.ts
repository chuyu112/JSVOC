import { apiClient, type ApiResponse } from './client'

export type ImageSize = '1024x1024' | '1536x1024' | '1024x1536' | 'auto'
export type ImageQuality = 'high' | 'medium' | 'low' | 'auto'
export type ImageReferenceType = 'persona' | 'product' | 'location'

export interface GeneratedImage {
  b64_json: string | null
  url: string | null
  data_url: string | null
}

export interface ImageGenerateResponse {
  provider: string
  model: string
  images: GeneratedImage[]
  usage: Record<string, unknown>
  latency_ms: number
}

export interface ImageReferencePayload {
  reference_image_type: ImageReferenceType
  source_image_base64: string
  source_image_mime: string
  source_image_filename: string
}

type GenerationTaskStatus = 'queued' | 'running' | 'succeeded' | 'failed'

interface GenerationTaskSubmitResponse {
  task_id: number
  task_type: string
  status: GenerationTaskStatus
}

interface GenerationTask<T> {
  id: number
  task_type: string
  status: GenerationTaskStatus
  project_id: number | null
  result_data: T | null
  error_message: string | null
}

const TASK_POLL_INTERVAL_MS = 2000
const TASK_POLL_TIMEOUT_MS = 10 * 60 * 1000

export async function generateImage(
  projectId: number,
  prompt: string,
  size: ImageSize,
  quality: ImageQuality,
  signal?: AbortSignal,
): Promise<ImageGenerateResponse> {
  const response = await apiClient.post<ApiResponse<GenerationTaskSubmitResponse>>(
    '/api/creation/images/generate/async',
    {
      project_id: projectId,
      prompt,
      size,
      quality,
      n: 1,
    },
    { signal },
  )
  return pollImageGenerationTask(response.data.data.task_id, signal)
}

export async function editImage(
  projectId: number,
  prompt: string,
  referenceImages: ImageReferencePayload[],
  size: ImageSize,
  quality: ImageQuality,
  signal?: AbortSignal,
): Promise<ImageGenerateResponse> {
  const response = await apiClient.post<ApiResponse<GenerationTaskSubmitResponse>>(
    '/api/creation/images/edit/async',
    {
      project_id: projectId,
      prompt,
      reference_images: referenceImages,
      size,
      quality,
      n: 1,
    },
    { signal },
  )
  return pollImageGenerationTask(response.data.data.task_id, signal)
}

async function pollImageGenerationTask(
  taskId: number,
  signal?: AbortSignal,
): Promise<ImageGenerateResponse> {
  const startedAt = Date.now()

  while (Date.now() - startedAt < TASK_POLL_TIMEOUT_MS) {
    if (signal?.aborted) {
      throw new DOMException('图片生成已取消', 'AbortError')
    }
    const response = await apiClient.get<ApiResponse<GenerationTask<ImageGenerateResponse>>>(
      `/api/generation-tasks/${taskId}`,
      { signal },
    )
    const task = response.data.data

    if (task.status === 'succeeded' && task.result_data) {
      return task.result_data
    }
    if (task.status === 'failed') {
      throw new Error(task.error_message || '图片生成失败，请检查渠道配置')
    }

    await sleep(TASK_POLL_INTERVAL_MS, signal)
  }

  throw new Error('图片生成超时，请稍后在生成记录或任务状态中查看结果')
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException('图片生成已取消', 'AbortError'))
      return
    }
    const timer = window.setTimeout(() => {
      signal?.removeEventListener('abort', onAbort)
      resolve()
    }, ms)
    const onAbort = () => {
      window.clearTimeout(timer)
      reject(new DOMException('图片生成已取消', 'AbortError'))
    }
    signal?.addEventListener('abort', onAbort, { once: true })
  })
}
