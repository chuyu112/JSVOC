import type {
  AccountPackageGenerateResponse,
  AccountPackageResult,
} from '../api/accountPackage.ts'
import type { GenerationRecord } from '../api/generationRecords.ts'

export function accountPackageResponseFromGenerationRecord(
  record: GenerationRecord,
): AccountPackageGenerateResponse | null {
  if (record.module_name !== 'account_package' && record.module_name !== 'strategy_bundle') {
    return null
  }

  const data = record.output_data.data
  const accountPackage =
    record.module_name === 'strategy_bundle' && isPlainObject(data)
      ? data.account_package
      : data
  if (!isAccountPackageResult(accountPackage)) {
    return null
  }

  return {
    account_package: accountPackage,
    context: null,
    generation_record_id: record.id,
    provider: record.model_provider,
    model: record.model_name,
    usage: record.token_usage,
    latency_ms: record.latency_ms ?? 0,
  }
}

function isAccountPackageResult(value: unknown): value is AccountPackageResult {
  if (!value || typeof value !== 'object') {
    return false
  }

  const data = value as AccountPackageResult
  return (
    typeof data.account_positioning === 'string' &&
    typeof data.persona === 'string' &&
    isPlainObject(data.target_user_profile) &&
    Array.isArray(data.account_names) &&
    Array.isArray(data.content_columns) &&
    Array.isArray(data.trust_design) &&
    Array.isArray(data.conversion_path) &&
    isPlainObject(data.bios) &&
    isPlainObject(data.platform_strategies)
  )
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}
