import type { AccountPackageGenerateResponse, AccountPackageResult } from './accountPackage'
import { apiClient, type ApiResponse } from './client'
import type { ExecutionPlanGenerateResponse, ExecutionPlanResult } from './executionPlan'

export interface StrategyBundleGenerateResponse {
  account_package: AccountPackageResult
  execution_plan: ExecutionPlanResult
  context?: AccountPackageGenerateResponse['context']
  generation_record_id: number
  provider: string
  model: string
  usage: Record<string, unknown>
  latency_ms: number
}

export async function generateStrategyBundle(
  projectId: number,
  cycle = '30天',
  dailyTime = '2小时',
): Promise<StrategyBundleGenerateResponse> {
  const response = await apiClient.post<ApiResponse<StrategyBundleGenerateResponse>>(
    '/api/strategy/account-package-execution-plan/generate',
    {
      project_id: projectId,
      cycle,
      daily_time: dailyTime,
      temperature: 0.2,
    },
  )
  return response.data.data
}

export function accountPackageResponseFromStrategyBundle(
  bundle: StrategyBundleGenerateResponse,
): AccountPackageGenerateResponse {
  return {
    account_package: bundle.account_package,
    context: bundle.context,
    generation_record_id: bundle.generation_record_id,
    provider: bundle.provider,
    model: bundle.model,
    usage: bundle.usage,
    latency_ms: bundle.latency_ms,
  }
}

export function executionPlanResponseFromStrategyBundle(
  bundle: StrategyBundleGenerateResponse,
): ExecutionPlanGenerateResponse {
  return {
    execution_plan: bundle.execution_plan,
    generation_record_id: bundle.generation_record_id,
    provider: bundle.provider,
    model: bundle.model,
    usage: bundle.usage,
    latency_ms: bundle.latency_ms,
  }
}
