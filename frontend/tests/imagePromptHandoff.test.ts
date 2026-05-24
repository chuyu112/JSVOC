import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildImagePromptHandoffQuery,
  readImagePromptHandoffQuery,
} from '../src/utils/imagePromptHandoff.ts'

test('builds query for text-to-image prompt handoff', () => {
  const query = buildImagePromptHandoffQuery('natural light jade bracelet', 'text')

  assert.deepEqual(query, {
    mode: 'text',
    prompt: 'natural light jade bracelet',
  })
})

test('builds query for image-to-image prompt handoff', () => {
  const query = buildImagePromptHandoffQuery('keep the bracelet and soften light', 'image')

  assert.deepEqual(query, {
    mode: 'image',
    prompt: 'keep the bracelet and soften light',
  })
})

test('reads prompt handoff query and ignores empty prompt values', () => {
  assert.deepEqual(
    readImagePromptHandoffQuery({
      mode: 'image',
      prompt: 'keep the bracelet',
    }),
    {
      mode: 'image',
      prompt: 'keep the bracelet',
    },
  )

  assert.equal(readImagePromptHandoffQuery({ mode: 'image', prompt: '   ' }), null)
})
