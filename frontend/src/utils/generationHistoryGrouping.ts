import type { GenerationRecord } from '../api/generationRecords'

export type GenerationHistoryRow = GenerationRecord & {
  child_records?: GenerationRecord[]
  is_grouped?: boolean
  topic_count?: number
  avg_topic_latency_ms?: number | null
}

export function groupGenerationRecords(source: GenerationRecord[]): GenerationHistoryRow[] {
  const sorted = [...source].sort((a, b) => recordTime(b) - recordTime(a))
  const consumed = new Set<number>()
  const rows: GenerationHistoryRow[] = []

  for (const record of sorted) {
    if (consumed.has(record.id)) continue

    const batchId = topicBatchId(record)
    let group: GenerationRecord[] = []
    if (batchId) {
      group = sorted.filter((item) => !consumed.has(item.id) && topicBatchId(item) === batchId)
    } else if (isSingleTopicRecord(record)) {
      group = collectNearbyTopicRecords(record, sorted, consumed)
    }

    if (group.length > 1) {
      group.forEach((item) => consumed.add(item.id))
      rows.push(createGroupedTopicRecord(group))
    } else {
      consumed.add(record.id)
      rows.push(record)
    }
  }

  return rows.sort((a, b) => recordTime(b) - recordTime(a))
}

function collectNearbyTopicRecords(
  anchor: GenerationRecord,
  sorted: GenerationRecord[],
  consumed: Set<number>,
) {
  const group = [anchor]
  const seenIndexes = new Set<number>()
  const anchorIndex = sorted.findIndex((item) => item.id === anchor.id)
  const anchorTopicIndex = topicIndex(anchor)
  if (anchorTopicIndex !== null) seenIndexes.add(anchorTopicIndex)

  let previousTime = recordTime(anchor)
  for (let index = anchorIndex + 1; index < sorted.length; index += 1) {
    const candidate = sorted[index]
    if (consumed.has(candidate.id) || !isSameSingleTopicRun(anchor, candidate)) continue

    const currentTime = recordTime(candidate)
    if (previousTime - currentTime > 15_000) break

    const currentTopicIndex = topicIndex(candidate)
    if (currentTopicIndex !== null && seenIndexes.has(currentTopicIndex)) break
    if (currentTopicIndex !== null) seenIndexes.add(currentTopicIndex)

    group.push(candidate)
    previousTime = currentTime
  }
  return group
}

function createGroupedTopicRecord(group: GenerationRecord[]): GenerationHistoryRow {
  const sorted = [...group].sort((a, b) => recordTime(a) - recordTime(b))
  const newest = sorted[sorted.length - 1]
  const recordIds = sorted.map((record) => record.id)
  const targetTopicCount = groupedTargetTopicCount(sorted)
  const rawTopics = sorted.flatMap((record) => extractTopics(record.output_data))
  const topics = targetTopicCount ? rawTopics.slice(0, targetTopicCount) : rawTopics
  const discardedTopics = targetTopicCount ? rawTopics.slice(targetTopicCount) : []
  const earliestStart = Math.min(
    ...sorted.map((record) => recordTime(record) - (record.latency_ms ?? 0)),
  )
  const latestEnd = Math.max(...sorted.map(recordTime))
  const latencyMs = Math.max(0, Math.round(latestEnd - earliestStart))

  return {
    ...newest,
    id: Math.max(...recordIds),
    input_data: mergeGroupedInput(newest, sorted, recordIds),
    output_data: {
      success: sorted.every((record) => Boolean(asRecord(record.output_data).success)),
      data: {
        topics,
        discarded_topics: discardedTopics,
      },
      record_ids: recordIds,
    },
    token_usage: sumTokenUsage(sorted),
    latency_ms: latencyMs,
    created_at: new Date(latestEnd).toISOString(),
    child_records: sorted,
    is_grouped: true,
    topic_count: targetTopicCount || topics.length || sorted.length,
    avg_topic_latency_ms: averageTopicLatency(latencyMs, targetTopicCount || topics.length),
  }
}

function mergeGroupedInput(
  newest: GenerationRecord,
  group: GenerationRecord[],
  recordIds: number[],
): Record<string, unknown> {
  const inputData = asRecord(newest.input_data)
  const metadata = asRecord(inputData.metadata)
  const targetTopicCount = groupedTargetTopicCount(group)
  return {
    ...inputData,
    metadata: {
      ...metadata,
      count: targetTopicCount || group.length,
      generation_record_ids: recordIds,
      grouped_records: group.length,
    },
  }
}

function groupedTargetTopicCount(group: GenerationRecord[]) {
  for (const record of group) {
    const value = recordMetadata(record).generation_target_count
    if (typeof value === 'number' && Number.isFinite(value) && value > 0) {
      return value
    }
  }
  return null
}

function isSameSingleTopicRun(anchor: GenerationRecord, candidate: GenerationRecord) {
  return (
    isSingleTopicRecord(candidate) &&
    !topicBatchId(candidate) &&
    anchor.project_id === candidate.project_id &&
    anchor.model_provider === candidate.model_provider &&
    anchor.model_name === candidate.model_name
  )
}

function isSingleTopicRecord(record: GenerationRecord) {
  const metadata = recordMetadata(record)
  return (
    record.module_name === 'topics' &&
    Number(metadata.count) === 1 &&
    typeof metadata.topic_index === 'number'
  )
}

function topicBatchId(record: GenerationRecord) {
  const value = recordMetadata(record).generation_batch_id
  return typeof value === 'string' && value ? value : ''
}

function topicIndex(record: GenerationRecord) {
  const value = recordMetadata(record).topic_index
  return typeof value === 'number' ? value : null
}

function recordMetadata(record: GenerationRecord) {
  return asRecord(asRecord(record.input_data).metadata)
}

function extractTopics(outputData: Record<string, unknown>) {
  const data = asRecord(outputData.data)
  const topics = data.topics
  return Array.isArray(topics) ? topics : []
}

function sumTokenUsage(group: GenerationRecord[]) {
  const totals: Record<string, number> = {}
  for (const record of group) {
    for (const [key, value] of Object.entries(record.token_usage)) {
      if (typeof value === 'number') {
        totals[key] = (totals[key] ?? 0) + value
      }
    }
  }
  return totals
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}

function averageTopicLatency(latencyMs: number, topicCount: number) {
  return topicCount > 0 ? Math.round(latencyMs / topicCount) : null
}

function recordTime(record: GenerationRecord) {
  return new Date(record.created_at).getTime()
}
