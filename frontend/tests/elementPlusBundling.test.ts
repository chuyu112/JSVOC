import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const mainSource = readFileSync(resolve('src/main.ts'), 'utf8')

test('main entry avoids full Element Plus registration and global stylesheet import', () => {
  assert.doesNotMatch(mainSource, /import\s+ElementPlus\s+from\s+['"]element-plus['"]/)
  assert.doesNotMatch(mainSource, /element-plus\/dist\/index\.css/)
  assert.doesNotMatch(mainSource, /\.use\(ElementPlus\)/)
  assert.match(mainSource, /installElementPlus/)
})
