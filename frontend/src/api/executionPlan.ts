import { apiClient, type ApiResponse } from './client'

export interface WeeklyPlanItem {
  week: number
  goal: string
  focus: string
  key_tasks: string[]
}

export interface DailyPlanItem {
  day: number
  task: string
  topic: string
  shooting_task: string
  review_metrics: string[]
}

export interface ExecutionPlanResult {
  cycle: string
  weekly_plan: WeeklyPlanItem[]
  daily_plan: DailyPlanItem[]
  notes: string[]
}

export interface ExecutionPlanGenerateResponse {
  execution_plan: ExecutionPlanResult
  generation_record_id: number | null
  provider: string
  model: string
  usage: Record<string, unknown>
  latency_ms: number
}

export async function generateExecutionPlan(
  projectId: number,
  cycle = '30天',
  dailyTime = '2小时',
): Promise<ExecutionPlanGenerateResponse> {
  const response = await apiClient.post<ApiResponse<ExecutionPlanGenerateResponse>>(
    '/api/strategy/execution-plan/generate',
    {
      project_id: projectId,
      cycle,
      daily_time: dailyTime,
    },
  )
  return response.data.data
}
