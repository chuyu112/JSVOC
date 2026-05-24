import assert from 'node:assert/strict'
import test from 'node:test'

import { runTopicGenerationBatch } from '../src/utils/topicGenerationScheduler.ts'

test('keeps launching requests after failures until the target topic count is filled', async () => {
  const launchedIndexes: number[] = []
  const appended: number[] = []
  const responses = [
    [],
    [1, 2],
    [3, 4],
    [5],
  ]

  await runTopicGenerationBatch({
    targetCount: 5,
    requestedOffset: 0,
    concurrency: 3,
    requestTopicCount: 2,
    maxAttempts: 10,
    generate: async ({ topicIndex }) => {
      launchedIndexes.push(topicIndex)
      return responses.shift() ?? []
    },
    append: async (topics) => {
      appended.push(...topics)
    },
  })

  assert.equal(appended.length, 5)
  assert.deepEqual(appended, [1, 2, 3, 4, 5])
  assert.ok(launchedIndexes.length > 3)
  assert.ok(launchedIndexes.length <= 10)
})

test('counts in-flight request capacity before launching more requests', async () => {
  let launchedCount = 0
  const appended: number[] = []

  await runTopicGenerationBatch({
    targetCount: 30,
    requestedOffset: 0,
    concurrency: 3,
    requestTopicCount: 3,
    maxAttempts: 30,
    generate: async () => {
      launchedCount += 1
      return [1, 2, 3]
    },
    append: async (topics) => {
      appended.push(...topics)
    },
  })

  assert.equal(appended.length, 30)
  assert.equal(launchedCount, 10)
})

test('discards overflow topics as soon as the target topic count is reached', async () => {
  const appended: number[] = []

  await runTopicGenerationBatch({
    targetCount: 10,
    requestedOffset: 0,
    concurrency: 3,
    requestTopicCount: 4,
    maxAttempts: 10,
    generate: async () => [1, 2, 3, 4],
    append: async (topics) => {
      appended.push(...topics)
    },
  })

  assert.equal(appended.length, 10)
  assert.deepEqual(appended, [1, 2, 3, 4, 1, 2, 3, 4, 1, 2])
})
