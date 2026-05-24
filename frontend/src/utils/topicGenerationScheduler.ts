export interface TopicGenerationRequest {
  topicIndex: number
  requestCount: number
  attempt: number
}

export interface TopicGenerationBatchOptions<Topic> {
  targetCount: number
  requestedOffset: number
  concurrency: number
  requestTopicCount: number
  maxAttempts: number
  generate: (request: TopicGenerationRequest) => Promise<Topic[]>
  append: (topics: Topic[]) => Promise<void> | void
}

export async function runTopicGenerationBatch<Topic>(
  options: TopicGenerationBatchOptions<Topic>,
) {
  if (options.targetCount <= 0) return

  const concurrency = Math.max(1, options.concurrency)
  const requestTopicCount = Math.max(1, options.requestTopicCount)
  const maxAttempts = Math.max(1, options.maxAttempts)
  let activeRequests = 0
  let collectedTopics = 0
  let attemptedRequests = 0
  let topicSequence = 0
  let settled = false

  await new Promise<void>((resolve, reject) => {
    const finish = () => {
      if (settled) return
      settled = true
      resolve()
    }

    const fail = () => {
      if (settled) return
      settled = true
      reject(new Error('topic generation attempts exhausted'))
    }

    const launchMore = () => {
      if (settled) return
      if (collectedTopics >= options.targetCount) {
        finish()
        return
      }
      if (attemptedRequests >= maxAttempts && activeRequests === 0) {
        fail()
        return
      }

      while (
        !settled &&
        activeRequests < concurrency &&
        collectedTopics + activeRequests * requestTopicCount < options.targetCount &&
        attemptedRequests < maxAttempts
      ) {
        const topicIndex = options.requestedOffset + topicSequence + 1
        const attempt = attemptedRequests + 1
        topicSequence += requestTopicCount
        attemptedRequests += 1
        activeRequests += 1

        options
          .generate({ topicIndex, requestCount: requestTopicCount, attempt })
          .then(async (topics) => {
            if (settled || collectedTopics >= options.targetCount) return

            const remainingTopics = options.targetCount - collectedTopics
            const topicsToAppend = topics.slice(0, remainingTopics)
            if (!topicsToAppend.length) return

            collectedTopics += topicsToAppend.length
            await options.append(topicsToAppend)
          })
          .catch(() => {
            // Failed requests are discarded. The scheduler fills the freed slot.
          })
          .finally(() => {
            activeRequests -= 1
            launchMore()
          })
      }
    }

    launchMore()
  })
}
