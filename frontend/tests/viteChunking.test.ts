import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const routerSource = readFileSync(resolve('src/router/index.ts'), 'utf8')
const viteConfigSource = readFileSync(resolve('vite.config.ts'), 'utf8')

test('router uses lazy-loaded view imports for route components', () => {
  assert.doesNotMatch(routerSource, /import\s+\w+View\s+from\s+['"].*views\/.*\.vue['"]/)
  assert.match(routerSource, /const\s+ProjectListView\s*=\s*\(\)\s*=>\s*import\(/)
  assert.match(routerSource, /const\s+TopicGenerationView\s*=\s*\(\)\s*=>\s*import\(/)
})

test('vite config defines manual chunks for framework and ui vendors', () => {
  assert.match(viteConfigSource, /manualChunks/)
  assert.match(viteConfigSource, /['"]vue-vendor['"]/)
  assert.match(viteConfigSource, /['"]ui-vendor['"]/)
})
