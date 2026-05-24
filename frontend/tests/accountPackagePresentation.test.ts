import assert from 'node:assert/strict'
import test from 'node:test'

import { normalizeContentColumns } from '../src/utils/accountPackagePresentation.ts'

test('normalizes structured content column objects for bento rendering', () => {
  const columns = normalizeContentColumns([
    {
      name: '缅甸砍价实录',
      description: '实拍砍价过程，展示源头优势',
      frequency: '每周2-3条',
      examples: ['老缅开价8万，我砍到2万'],
    },
  ])

  assert.deepEqual(columns, [
    {
      name: '缅甸砍价实录',
      description: '实拍砍价过程，展示源头优势',
      frequency: '每周2-3条',
      examples: ['老缅开价8万，我砍到2万'],
    },
  ])
})

test('parses JSON string content columns from older normalized API output', () => {
  const columns = normalizeContentColumns([
    JSON.stringify({
      name: '手镯鉴赏与鉴别',
      description: '教用户看种水、颜色和瑕疵',
      frequency: '每周1-2条',
      examples: ['糯种vs冰种，价格差10倍，怎么选'],
    }),
  ])

  assert.equal(columns[0].name, '手镯鉴赏与鉴别')
  assert.equal(columns[0].description, '教用户看种水、颜色和瑕疵')
  assert.equal(columns[0].frequency, '每周1-2条')
  assert.deepEqual(columns[0].examples, ['糯种vs冰种，价格差10倍，怎么选'])
})

test('keeps plain string columns readable', () => {
  const columns = normalizeContentColumns(['源头市场见闻'])

  assert.deepEqual(columns, [
    {
      name: '源头市场见闻',
      description: '',
      frequency: '',
      examples: [],
    },
  ])
})
