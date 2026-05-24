import assert from 'node:assert/strict'
import test from 'node:test'

import type { GenerationRecord } from '../src/api/generationRecords.ts'
import { groupGenerationRecords } from '../src/utils/generationHistoryGrouping.ts'

function topicRecord(
  id: number,
  topics: string[],
  createdAt: string,
  latencyMs: number,
): GenerationRecord {
  return {
    id,
    user_id: null,
    project_id: 1,
    module_name: 'topics',
    input_data: {
      metadata: {
        count: 2,
        generation_batch_id: 'batch-1',
        generation_target_count: 2,
      },
    },
    output_data: {
      success: true,
      data: {
        topics: topics.map((title) => ({ title })),
      },
    },
    model_provider: 'openai_compatible',
    model_name: 'deepseek-v4-flash',
    prompt_version: 'topics-v1',
    token_usage: {},
    latency_ms: latencyMs,
    created_at: createdAt,
  }
}

test('keeps discarded topics in grouped history but excludes them from count and average time', () => {
  const grouped = groupGenerationRecords([
    topicRecord(1, ['A', 'B'], '2026-05-10T16:00:02.000Z', 2_000),
    topicRecord(2, ['C', 'D'], '2026-05-10T16:00:06.000Z', 2_000),
  ])

  assert.equal(grouped.length, 1)
  const row = grouped[0]
  const outputData = row.output_data.data as {
    topics: Array<{ title: string }>
    discarded_topics: Array<{ title: string }>
  }

  assert.equal(row.topic_count, 2)
  assert.equal(row.avg_topic_latency_ms, 3_000)
  assert.deepEqual(outputData.topics.map((topic) => topic.title), ['A', 'B'])
  assert.deepEqual(outputData.discarded_topics.map((topic) => topic.title), ['C', 'D'])
  assert.deepEqual(row.output_data.record_ids, [1, 2])
  assert.equal(row.child_records?.length, 2)
})
