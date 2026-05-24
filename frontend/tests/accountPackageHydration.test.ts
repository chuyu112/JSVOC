import assert from 'node:assert/strict'
import test from 'node:test'

import type { GenerationRecord } from '../src/api/generationRecords.ts'
import { accountPackageResponseFromGenerationRecord } from '../src/utils/accountPackageHydration.ts'

function accountPackageRecord(): GenerationRecord {
  return {
    id: 18,
    user_id: null,
    project_id: 2,
    module_name: 'account_package',
    input_data: {},
    output_data: {
      success: true,
      data: {
        account_positioning: '四会翡翠源头专业买手',
        persona: '真实、专业、审美在线的翡翠选品人',
        target_user_profile: {
          core_audience: '想买翡翠但怕踩坑的人',
        },
        account_names: ['四会翡翠选品人'],
        bios: {
          抖音: '源头翡翠避坑和选品建议',
        },
        content_columns: ['源头市场见闻'],
        trust_design: ['展示自然光实拍'],
        conversion_path: ['评论咨询', '私信预算', '微信私域'],
        platform_strategies: {
          抖音: '强钩子切入避坑',
        },
      },
    },
    model_provider: 'mock',
    model_name: 'mock-model',
    prompt_version: 'v1',
    token_usage: {
      total_tokens: 0,
    },
    latency_ms: 12,
    created_at: '2026-05-11T03:00:00.000Z',
  }
}

test('hydrates account package page response from latest generation record', () => {
  const hydrated = accountPackageResponseFromGenerationRecord(accountPackageRecord())

  assert.ok(hydrated)
  assert.equal(hydrated.generation_record_id, 18)
  assert.equal(hydrated.provider, 'mock')
  assert.equal(hydrated.model, 'mock-model')
  assert.equal(hydrated.latency_ms, 12)
  assert.deepEqual(hydrated.account_package.account_names, ['四会翡翠选品人'])
  assert.equal(hydrated.account_package.bios['抖音'], '源头翡翠避坑和选品建议')
})

test('ignores malformed generation records', () => {
  const record = accountPackageRecord()
  record.output_data = {
    success: true,
    data: {
      account_positioning: 'missing required arrays',
    },
  }

  assert.equal(accountPackageResponseFromGenerationRecord(record), null)
})
