import { apiClient, type ApiResponse } from './client'

export type GenerationModuleName = 'account_package' | 'execution_plan' | 'topics' | 'script'

export interface GenerationRecord {
  id: number
  user_id: number | null
  project_id: number | null
  module_name: string
  input_data: Record<string, unknown>
  output_data: Record<string, unknown>
  model_provider: string
  model_name: string
  prompt_version: string | null
  token_usage: Record<string, unknown>
  latency_ms: number | null
  created_at: string
}

export interface GenerationRecordQuery {
  project_id?: number | null
  module_name?: string | null
  limit?: number
  offset?: number
}

export const moduleNameText: Record<GenerationModuleName, string> = {
  account_package: '账号包装',
  execution_plan: '执行计划',
  topics: '选题生成',
  script: '文案生成',
}

export function formatModuleName(moduleName: string) {
  return moduleNameText[moduleName as GenerationModuleName] ?? moduleName
}

export async function listGenerationRecords(
  query: GenerationRecordQuery = {},
): Promise<GenerationRecord[]> {
  const response = await apiClient.get<ApiResponse<GenerationRecord[]>>(
    '/api/generation-records',
    {
      params: {
        project_id: query.project_id || undefined,
        module_name: query.module_name || undefined,
        limit: query.limit ?? 50,
        offset: query.offset ?? 0,
      },
    },
  )
  return response.data.data
}

export async function getGenerationRecord(recordId: number): Promise<GenerationRecord> {
  const response = await apiClient.get<ApiResponse<GenerationRecord>>(
    `/api/generation-records/${recordId}`,
  )
  return response.data.data
}
