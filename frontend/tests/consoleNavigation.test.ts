import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import test from 'node:test'

const appSource = readFileSync(resolve('src/App.vue'), 'utf8')
const routerSource = readFileSync(resolve('src/router/index.ts'), 'utf8')
const projectDetailSource = readFileSync(resolve('src/views/ProjectDetailView.vue'), 'utf8')

test('global console header exposes project assets and history entries', () => {
  assert.match(appSource, /项目/)
  assert.match(appSource, /数字资产/)
  assert.match(appSource, /生成历史/)
  assert.match(appSource, /console-user/)
  assert.match(appSource, /退出登录/)
  assert.doesNotMatch(appSource, /项目档案/)
})

test('router exposes digital assets as a top level route', () => {
  assert.match(routerSource, /const\s+DigitalAssetsView\s*=\s*\(\)\s*=>\s*import\(/)
  assert.match(routerSource, /path:\s*['"]\/assets['"]/)
  assert.match(routerSource, /name:\s*['"]digital-assets['"]/)
})

test('project detail uses grouped workflow navigation instead of colored action ribbon', () => {
  assert.match(projectDetailSource, /project-workflow-nav/)
  assert.match(projectDetailSource, /策略/)
  assert.match(projectDetailSource, /创作/)
  assert.match(projectDetailSource, /媒体/)
  assert.match(projectDetailSource, /其他/)
  assert.doesNotMatch(projectDetailSource, /class="header-actions action-ribbon"/)
  assert.doesNotMatch(projectDetailSource, /\/history`\)/)
})

test('project edit saves in place without save-as wording', () => {
  assert.match(projectDetailSource, /项目已保存/)
  assert.match(projectDetailSource, />保存项目</)
  assert.doesNotMatch(projectDetailSource, /另存/)
})
