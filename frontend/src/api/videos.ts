import { apiClient, type ApiResponse } from './client'

export type VideoMode = 'image' | 'text' | 'reference'
export type VideoResolution = '480p' | '720p' | '1080p'
export type VideoRatio = '16:9' | '9:16' | '1:1' | '4:3' | '3:4'

export interface VideoGenerateOptions {
  mode: VideoMode
  ratio: VideoRatio
  resolution: VideoResolution
  duration_mode: 'seconds'
  duration_seconds: number
  seed?: number
  count: number
}

export interface VideoGenerateResponse {
  provider: string
  model: string
  video_url: string | null
  task_id: string | null
  status: string
  latency_ms: number
  asset_id?: number | null
  oss_object_key?: string | null
  signed_url_expires_at?: number | null
  storage_status?: string | null
}

type GenerationTaskStatus = 'queued' | 'running' | 'succeeded' | 'failed'

interface GenerationTaskSubmitResponse {
  task_id: number
  task_type: string
  status: GenerationTaskStatus
  credit_cost?: number | null
}

interface GenerationTask<T> {
  id: number
  task_type: string
  status: GenerationTaskStatus
  project_id: number | null
  result_data: T | null
  error_message: string | null
}

const TASK_POLL_INTERVAL_MS = 5000
const TASK_POLL_TIMEOUT_MS = 30 * 60 * 1000

export async function generateVideo(
  projectId: number,
  prompt: string,
  options: VideoGenerateOptions,
  references: {
    firstFrame?: string | null
    referenceImages: string[]
    referenceImageNames: string[]
    referenceVideos: string[]
  },
  signal?: AbortSignal,
): Promise<VideoGenerateResponse> {
  const response = await apiClient.post<ApiResponse<GenerationTaskSubmitResponse>>(
    '/api/creation/videos/generate/async',
    {
      project_id: projectId,
      prompt,
      options,
      first_frame: references.firstFrame || null,
      reference_images: references.referenceImages,
      reference_image_names: references.referenceImageNames,
      reference_videos: references.referenceVideos,
    },
    { signal },
  )
  return pollVideoGenerationTask(response.data.data.task_id, signal)
}

async function pollVideoGenerationTask(
  taskId: number,
  signal?: AbortSignal,
): Promise<VideoGenerateResponse> {
  const startedAt = Date.now()

  while (Date.now() - startedAt < TASK_POLL_TIMEOUT_MS) {
    if (signal?.aborted) {
      throw new DOMException('视频生成已取消', 'AbortError')
    }
    const response = await apiClient.get<ApiResponse<GenerationTask<VideoGenerateResponse>>>(
      `/api/generation-tasks/${taskId}`,
      { signal },
    )
    const task = response.data.data

    if (task.status === 'succeeded' && task.result_data) {
      return task.result_data
    }
    if (task.status === 'failed') {
      throw new Error(task.error_message || '视频生成失败，请检查渠道配置')
    }

    await sleep(TASK_POLL_INTERVAL_MS, signal)
  }

  throw new Error('视频生成超时，请稍后在生成记录或任务状态中查看结果')
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException('视频生成已取消', 'AbortError'))
      return
    }
    const timer = window.setTimeout(() => {
      signal?.removeEventListener('abort', onAbort)
      resolve()
    }, ms)
    const onAbort = () => {
      window.clearTimeout(timer)
      reject(new DOMException('视频生成已取消', 'AbortError'))
    }
    signal?.addEventListener('abort', onAbort, { once: true })
  })
}
