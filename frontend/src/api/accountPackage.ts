export interface AccountPackageResult {
  account_positioning: string
  persona: string
  target_user_profile: Record<string, unknown>
  account_names: string[]
  bios: Record<string, string>
  content_columns: unknown[]
  trust_design: string[]
  conversion_path: string[]
  platform_strategies: Record<string, unknown>
}

export interface AccountStrategyContext extends AccountPackageResult {
  id: number
  project_id: number
  generation_record_id: number | null
  content_style: string | null
  trust_points: string[]
  monetization_paths: string[]
  execution_stage: string | null
  context_data: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface AccountPackageGenerateResponse {
  account_package: AccountPackageResult
  context?: AccountStrategyContext | null
  generation_record_id: number
  provider: string
  model: string
  usage: Record<string, unknown>
  latency_ms: number
}
