<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { MagicStick, Refresh } from '@element-plus/icons-vue'

import { getProject, type Project } from '../api/projects'
import {
  generateVideo,
  type VideoGenerateOptions,
  type VideoGenerateResponse,
  type VideoMode,
  type VideoRatio,
  type VideoResolution,
} from '../api/videos'

interface LocalReferenceFile {
  id: string
  name: string
  type: 'image' | 'video'
  dataUrl: string
  preview: string
  selected: boolean
  referenceName?: string
}

const route = useRoute()
const router = useRouter()
const project = ref<Project | null>(null)
const loadingProject = ref(false)
const generating = ref(false)
const result = ref<VideoGenerateResponse | null>(null)
const generationError = ref('')
const activeMode = ref<VideoMode>('reference')
const prompt = ref('@图片1 跟 @图片2 打架，镜头稳定跟拍，动作激烈但不血腥，电影感光影')
const resolution = ref<VideoResolution>('720p')
const ratio = ref<VideoRatio>('16:9')
const duration = ref(5)
const seed = ref('1234')
const referenceFiles = ref<LocalReferenceFile[]>([])
const generationStatus = ref('')

const videoGenerationPromptStart = '【视频参考图绑定（自动生成）】'
const videoGenerationPromptEnd = '【视频参考图绑定结束】'

const modeOptions: Array<{ label: string; value: VideoMode }> = [
  { label: '图生视频', value: 'image' },
  { label: '文生视频', value: 'text' },
  { label: '参考生视频', value: 'reference' },
]

const resolutionOptions: Array<{ label: string; value: VideoResolution }> = [
  { label: '480P', value: '480p' },
  { label: '720P', value: '720p' },
  { label: '1080P', value: '1080p' },
]
const ratioOptions: VideoRatio[] = ['16:9', '9:16', '1:1', '4:3', '3:4']

const modeTitle = computed(() => {
  return modeOptions.find((item) => item.value === activeMode.value)?.label || '参考生视频'
})

const uploadTitle = computed(() => {
  if (activeMode.value === 'image') return '上传首帧图或主体图'
  if (activeMode.value === 'reference') return '上传参考视频或参考图'
  return '无需上传素材'
})

const uploadHint = computed(() => {
  if (activeMode.value === 'image') return '支持 PNG、JPG、WebP，用作视频首帧或主体参考'
  if (activeMode.value === 'reference') return '支持图片或短视频，用来约束人物、镜头和运动风格'
  return '直接填写提示词即可生成视频'
})

const canUpload = computed(() => activeMode.value !== 'text')

const previewRatioClass = computed(() => `ratio-${ratio.value.replace(':', '-')}`)
const promptReferenceNames = computed(() => extractReferenceImageNames(stripVideoReferencePromptBlock(prompt.value)))
const activeReferenceFiles = computed(() => {
  if (activeMode.value === 'text') return []
  const promptNames = promptReferenceNames.value
  return referenceFiles.value.filter(
    (file) =>
      file.selected ||
      (file.type === 'image' && file.referenceName && promptNames.has(normalizeReferenceImageName(file.referenceName))),
  )
})
const activeReferenceFileCount = computed(() => activeReferenceFiles.value.length)
const activeReferenceImages = computed(() => activeReferenceFiles.value.filter((file) => file.type === 'image'))
const activeReferenceVideos = computed(() => activeReferenceFiles.value.filter((file) => file.type === 'video'))
const imageReferenceFiles = computed(() => referenceFiles.value.filter((file) => file.type === 'image'))
const previewVideoUrl = computed(() => result.value?.video_url || '')

function projectId() {
  return Number(route.params.id)
}

function normalizeReferenceImageName(value: string) {
  return value.trim().replace(/^@/, '')
}

function normalizeReferenceImageIndex(value: string) {
  return value.replace(/[０-９]/g, (char) => String.fromCharCode(char.charCodeAt(0) - 0xfee0))
}

function extractReferenceImageNames(value: string) {
  const names = new Set<string>()
  const matcher = /@?图片\s*([0-9０-９]+)/g
  let match = matcher.exec(value)
  while (match) {
    names.add(`图片${normalizeReferenceImageIndex(match[1])}`)
    match = matcher.exec(value)
  }
  return names
}

function unknownPromptReferenceNames() {
  const knownNames = new Set(
    referenceFiles.value
      .filter((file) => file.type === 'image' && file.referenceName)
      .map((file) => normalizeReferenceImageName(file.referenceName || '')),
  )
  return [...promptReferenceNames.value].filter((name) => !knownNames.has(name))
}

function isReferenceFileMentioned(file: LocalReferenceFile) {
  return file.type === 'image' && Boolean(file.referenceName) && promptReferenceNames.value.has(normalizeReferenceImageName(file.referenceName || ''))
}

function isReferenceFileActive(file: LocalReferenceFile) {
  return activeReferenceFiles.value.some((item) => item.id === file.id)
}

function nextReferenceImageName() {
  const usedIndexes = referenceFiles.value
    .map((file) => normalizeReferenceImageName(file.referenceName || '').match(/^图片(\d+)$/)?.[1])
    .filter((value): value is string => Boolean(value))
    .map((value) => Number(value))
  const nextIndex = usedIndexes.length ? Math.max(...usedIndexes) + 1 : 1
  return `@图片${nextIndex}`
}

async function fetchProject() {
  loadingProject.value = true
  try {
    project.value = await getProject(projectId())
  } catch (error) {
    ElMessage.error('项目上下文加载失败')
  } finally {
    loadingProject.value = false
  }
}

function applyPromptFromRoute() {
  const queryPrompt =
    route.query.prompt || route.query.video_prompt || route.query.seedance_prompt || route.query.seeddance_prompt
  if (typeof queryPrompt === 'string' && queryPrompt.trim()) {
    prompt.value = queryPrompt.trim()
  }

  if (route.query.mode === 'text' || route.query.mode === 'image' || route.query.mode === 'reference') {
    activeMode.value = route.query.mode
  }
}

function setVideoMode(value: VideoMode) {
  activeMode.value = value
  syncVideoReferencePromptBlock()
}

async function handleReferenceChange(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  if (!files.length) return

  const availableSlots = 5 - referenceFiles.value.length
  if (availableSlots <= 0) {
    ElMessage.warning('最多上传 5 个参考素材')
    input.value = ''
    return
  }

  try {
    for (const file of files.slice(0, availableSlots)) {
      if (!isSupportedReference(file)) {
        ElMessage.warning('仅支持 PNG、JPG、WebP、MP4、MOV、WebM')
        continue
      }

      const type = file.type.startsWith('video/') ? 'video' : 'image'
      const dataUrl = await readFileAsDataUrl(file)
      referenceFiles.value.push({
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        name: file.name,
        type,
        dataUrl,
        preview: URL.createObjectURL(file),
        selected: true,
        referenceName: type === 'image' ? nextReferenceImageName() : undefined,
      })
    }
    syncVideoReferencePromptBlock()
  } catch (error) {
    ElMessage.error('参考素材读取失败')
  } finally {
    input.value = ''
  }
}

function isSupportedReference(file: File) {
  return [
    'image/png',
    'image/jpeg',
    'image/jpg',
    'image/webp',
    'video/mp4',
    'video/quicktime',
    'video/webm',
  ].includes(file.type.toLowerCase())
}

function removeReference(fileId: string) {
  const target = referenceFiles.value.find((item) => item.id === fileId)
  if (target) URL.revokeObjectURL(target.preview)
  referenceFiles.value = referenceFiles.value.filter((item) => item.id !== fileId)
  syncVideoReferencePromptBlock()
}

function setReferenceSelection(fileId: string, selected: boolean) {
  const target = referenceFiles.value.find((item) => item.id === fileId)
  if (!target) return
  target.selected = selected
  syncVideoReferencePromptBlock()
}

function toggleReferenceSelection(fileId: string) {
  const target = referenceFiles.value.find((item) => item.id === fileId)
  if (!target) return
  setReferenceSelection(fileId, !target.selected)
}

function handleReferenceSelectionChange(event: Event, fileId: string) {
  setReferenceSelection(fileId, (event.target as HTMLInputElement).checked)
}

function appendReferenceMention(file: LocalReferenceFile) {
  if (file.type !== 'image' || !file.referenceName) return
  const basePrompt = stripVideoReferencePromptBlock(prompt.value).trimEnd()
  const spacer = basePrompt && !/[\s，。；,.!?！？]$/.test(basePrompt) ? ' ' : ''
  prompt.value = `${basePrompt}${spacer}${file.referenceName}`.trimStart()
  activeMode.value = activeMode.value === 'text' ? 'reference' : activeMode.value
  syncVideoReferencePromptBlock()
}

function randomizeSeed() {
  seed.value = String(Math.floor(1000 + Math.random() * 9000))
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(file)
  })
}

function stripVideoReferencePromptBlock(value: string) {
  const startIndex = value.indexOf(videoGenerationPromptStart)
  const endIndex = value.indexOf(videoGenerationPromptEnd)
  if (startIndex === -1 || endIndex === -1 || endIndex < startIndex) return value

  return `${value.slice(0, startIndex)}${value.slice(endIndex + videoGenerationPromptEnd.length)}`.trim()
}

function syncVideoReferencePromptBlock() {
  const basePrompt = stripVideoReferencePromptBlock(prompt.value).trim()
  if (activeMode.value === 'text' || !activeReferenceFiles.value.length) {
    prompt.value = basePrompt
    return
  }

  prompt.value = [basePrompt, buildVideoReferencePromptBlock()].filter(Boolean).join('\n\n')
}

function buildVideoReferencePromptBlock() {
  const lines = [
    videoGenerationPromptStart,
    '本次选中或在提示词中 @ 引用的图片/视频会发送给视频模型；未选中且未 @ 引用的素材不会参与生成。',
    '如果提示词写 @图片1、@图片2，必须分别绑定到下方同名参考图，不要把两个主体合并。',
    '例：@图片1 跟 @图片2 打架 = 图片1主体和图片2主体发生打架动作，动作激烈但不血腥，镜头保持稳定。',
  ]

  for (const file of activeReferenceImages.value) {
    lines.push(`${file.referenceName}：参考图片，文件名 ${file.name}。`)
  }
  activeReferenceVideos.value.forEach((file, index) => {
    lines.push(`参考视频${index + 1}：参考运动、镜头或风格，文件名 ${file.name}。`)
  })

  lines.push(videoGenerationPromptEnd)
  return lines.join('\n')
}

function apiErrorMessage(error: unknown, fallback: string) {
  const detail = (error as { response?: { data?: { detail?: unknown } }; message?: string })?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  const message = (error as { message?: string })?.message
  return typeof message === 'string' && message.trim() ? message : fallback
}

function buildVideoOptions(): VideoGenerateOptions {
  const parsedSeed = Number(seed.value)
  return {
    mode: activeMode.value,
    ratio: ratio.value,
    resolution: resolution.value,
    duration_mode: 'seconds',
    duration_seconds: duration.value,
    seed: Number.isFinite(parsedSeed) ? parsedSeed : undefined,
    count: 1,
  }
}

function buildVideoReferences() {
  const activeImages = activeReferenceImages.value
  return {
    firstFrame: null,
    referenceImages: activeImages.map((file) => file.dataUrl),
    referenceImageNames: activeImages.map((file) => file.referenceName || ''),
    referenceVideos: activeReferenceVideos.value.map((file) => file.dataUrl),
  }
}

let videoGenerationAbortController: AbortController | null = null

async function handleGenerate() {
  if (activeMode.value !== 'text') {
    syncVideoReferencePromptBlock()
  }
  const cleanPrompt = prompt.value.trim()
  if (!cleanPrompt) {
    ElMessage.warning('请先填写提示词')
    return
  }

  if (activeMode.value !== 'text') {
    const unknownNames = unknownPromptReferenceNames()
    if (unknownNames.length) {
      ElMessage.warning(`提示词引用了 ${unknownNames.map((name) => `@${name}`).join('、')}，请先上传对应图片`)
      return
    }
  }

  if (activeMode.value !== 'text' && activeReferenceFileCount.value < 1) {
    ElMessage.warning(activeMode.value === 'image' ? '图生视频至少选中或 @ 引用 1 张图' : '参考生视频至少选中或 @ 引用 1 个素材')
    return
  }

  generating.value = true
  result.value = null
  generationError.value = ''
  generationStatus.value = '视频生成任务已提交，通常需要几分钟；请保持页面打开，不要重复点击。'
  videoGenerationAbortController?.abort()
  videoGenerationAbortController = new AbortController()
  const signal = videoGenerationAbortController.signal

  try {
    const startedAt = Date.now()
    result.value = await generateVideo(projectId(), cleanPrompt, buildVideoOptions(), buildVideoReferences(), signal)
    generationStatus.value = `视频已生成，用时 ${Math.round((Date.now() - startedAt) / 1000)} 秒。`
    ElMessage.success('视频已生成')
  } catch (error) {
    if ((error as DOMException | { name?: string })?.name === 'AbortError') {
      generationStatus.value = '视频生成已取消。'
      return
    }
    const message = apiErrorMessage(error, '视频生成失败，请检查模型渠道或稍后重试')
    generationError.value = message
    generationStatus.value = '视频生成失败。'
    ElMessage.error(message)
  } finally {
    generating.value = false
  }
}

onMounted(async () => {
  applyPromptFromRoute()
  await fetchProject()
})

onBeforeUnmount(() => {
  videoGenerationAbortController?.abort()
  videoGenerationAbortController = null
  for (const file of referenceFiles.value) {
    URL.revokeObjectURL(file.preview)
  }
  referenceFiles.value = []
})
</script>

<template>
  <section class="page-section video-generation-page">
    <div class="section-header video-header">
      <div>
        <p class="eyebrow">Video Generation</p>
        <h1>{{ project?.project_name || '生视频' }}</h1>
      </div>
      <div class="header-actions action-ribbon">
        <el-button @click="router.push(`/projects/${projectId()}`)">返回项目</el-button>
        <el-button @click="router.push(`/projects/${projectId()}/topics`)">选题生成</el-button>
      </div>
    </div>

    <el-skeleton v-if="loadingProject" :rows="8" animated />

    <template v-else>
      <div class="video-workspace">
        <article class="video-form-panel">
          <h2>视觉模型</h2>

          <div class="video-mode-tabs" role="tablist" aria-label="视频生成模式">
            <button
              v-for="item in modeOptions"
              :key="item.value"
              type="button"
              :class="['video-mode-tab', { 'is-active': activeMode === item.value }]"
              @click="setVideoMode(item.value)"
            >
              {{ item.label }}
            </button>
            <button type="button" class="video-mode-tool" aria-label="打开模型设置">⌘</button>
          </div>

          <div class="video-reference-shell">
            <div class="reference-strip">
              <span>示例</span>
              <div class="reference-example-row">
                <div v-for="index in 5" :key="index" class="reference-example-thumb">
                  <span>{{ index === 2 ? 4 : 3 }}</span>
                </div>
              </div>
            </div>

            <label v-if="canUpload" class="video-upload-zone">
              <input type="file" accept="image/*,video/mp4,video/quicktime,video/webm" multiple @change="handleReferenceChange" />
              <strong>{{ uploadTitle }}</strong>
              <small>{{ uploadHint }}</small>
            </label>
            <div v-else class="video-upload-zone is-disabled">
              <strong>{{ uploadTitle }}</strong>
              <small>{{ uploadHint }}</small>
            </div>

            <div v-if="referenceFiles.length" class="reference-file-grid">
              <div
                v-for="file in referenceFiles"
                :key="file.id"
                :class="[
                  'reference-file',
                  {
                    'is-active': isReferenceFileActive(file),
                    'is-mentioned': isReferenceFileMentioned(file),
                  },
                ]"
                @click="toggleReferenceSelection(file.id)"
              >
                <img v-if="file.type === 'image'" :src="file.preview" :alt="file.name" />
                <video v-else :src="file.preview" muted />
                <button
                  v-if="file.type === 'image' && file.referenceName"
                  type="button"
                  class="reference-name-button"
                  @click.stop="appendReferenceMention(file)"
                >
                  {{ file.referenceName }}
                </button>
                <span v-else class="reference-video-badge">视频</span>
                <label class="reference-select-check" @click.stop>
                  <input
                    type="checkbox"
                    :checked="file.selected"
                    @change="handleReferenceSelectionChange($event, file.id)"
                  />
                  <span>选中</span>
                </label>
                <button type="button" class="reference-remove-button" @click.stop="removeReference(file.id)">移除</button>
              </div>
            </div>
            <div v-if="referenceFiles.length" class="video-reference-summary">
              <strong>本次使用 {{ activeReferenceFileCount }} / {{ referenceFiles.length }} 个素材</strong>
              <span>选中素材会参与生成；提示词里的 @图片 会自动纳入对应图片。</span>
              <div class="video-reference-chips">
                <button
                  v-for="file in imageReferenceFiles"
                  :key="file.id"
                  type="button"
                  :class="['video-reference-chip', { 'is-active': isReferenceFileActive(file) }]"
                  @click="appendReferenceMention(file)"
                >
                  {{ file.referenceName }}
                </button>
              </div>
            </div>
          </div>

          <el-form label-position="top" class="video-form">
            <el-form-item label="提示词 *">
              <el-input
                v-model="prompt"
                type="textarea"
                :rows="5"
                maxlength="2500"
                show-word-limit
                placeholder="例如：@图片1 跟 @图片2 打架，镜头稳定跟拍，动作激烈但不血腥。也可以描述场景、镜头运动、光线、情绪和风格"
              />
            </el-form-item>

            <el-form-item label="清晰度">
              <div class="video-choice-grid two">
                <button
                  v-for="item in resolutionOptions"
                  :key="item.value"
                  type="button"
                  :class="['video-choice', { 'is-selected': resolution === item.value }]"
                  @click="resolution = item.value"
                >
                  {{ item.label }}
                </button>
              </div>
            </el-form-item>

            <el-form-item label="宽高比">
              <div class="video-choice-grid ratio">
                <button
                  v-for="item in ratioOptions"
                  :key="item"
                  type="button"
                  :class="['video-choice', { 'is-selected': ratio === item }]"
                  @click="ratio = item"
                >
                  {{ item }}
                </button>
              </div>
            </el-form-item>

            <el-form-item label="视频时长(秒)">
              <div class="duration-row">
                <el-slider v-model="duration" :min="3" :max="15" :step="1" />
                <el-input-number v-model="duration" :min="3" :max="15" controls-position="right" />
              </div>
            </el-form-item>

            <el-form-item label="随机种子">
              <div class="seed-row">
                <el-input v-model="seed" maxlength="8" />
                <button type="button" class="seed-random-button" aria-label="随机种子" @click="randomizeSeed">
                  <Refresh class="w-4 h-4" />
                </button>
              </div>
            </el-form-item>
          </el-form>

          <button type="button" class="video-submit-button" :disabled="generating" @click="handleGenerate">
            <MagicStick class="w-5 h-5" />
            <strong>{{ generating ? '生成中...' : '开始生成' }}</strong>
            <small>生成1个视频，约扣费4.5元</small>
          </button>

          <p class="video-disclaimer">所有内容均由人工智能模型生成，准确性和完整性无法保证。</p>
        </article>

        <aside class="video-preview-panel">
          <div class="video-preview-head">
            <div>
              <p class="eyebrow">{{ modeTitle }}</p>
              <h2>生成预览</h2>
            </div>
            <el-tag class="module-purple">{{ resolution.toUpperCase() }}</el-tag>
          </div>

          <el-alert
            v-if="generationError"
            class="video-status-alert"
            type="error"
            show-icon
            :closable="false"
            :title="generationStatus"
            :description="generationError"
          />

          <div :class="['video-preview-frame', previewRatioClass]">
            <video v-if="previewVideoUrl" class="video-result-player" :src="previewVideoUrl" controls playsinline />
            <div v-else class="video-preview-inner">
              <span>VIDEO</span>
              <strong>{{ ratio }} / {{ duration }}s</strong>
              <p>{{ generationStatus || '点击开始生成后，这里展示任务状态和视频结果。' }}</p>
            </div>
          </div>

          <dl class="video-meta-list">
            <div>
              <dt>模式</dt>
              <dd>{{ modeTitle }}</dd>
            </div>
            <div>
              <dt>参考素材</dt>
              <dd>{{ activeReferenceFileCount }} / {{ referenceFiles.length }} 个</dd>
            </div>
            <div>
              <dt>随机种子</dt>
              <dd>{{ seed || '随机' }}</dd>
            </div>
          </dl>
        </aside>
      </div>
    </template>
  </section>
</template>

<style scoped>
.video-generation-page {
  width: min(1180px, 100%);
}

.video-header {
  min-height: 108px;
}

.video-workspace {
  display: grid;
  grid-template-columns: minmax(360px, 456px) minmax(0, 1fr);
  gap: 22px;
  align-items: start;
}

.video-form-panel,
.video-preview-panel {
  border: 1px solid var(--studio-border);
  border-radius: var(--studio-radius-card);
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(20px) saturate(1.2);
  box-shadow: var(--studio-shadow);
}

.video-form-panel {
  padding: 18px 16px 20px;
}

.video-form-panel h2,
.video-preview-head h2 {
  margin: 0;
  color: #111a3d;
  font-size: 18px;
  font-weight: 700;
}

.video-mode-tabs {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr)) 36px;
  align-items: end;
  gap: 14px;
  min-height: 70px;
  border-top: 1px solid #e6e8f0;
  margin: 24px -16px 20px;
  padding: 18px 16px 0;
}

.video-mode-tab,
.video-mode-tool {
  border: 0;
  background: transparent;
  color: #121a42;
  cursor: pointer;
  font: inherit;
}

.video-mode-tab {
  position: relative;
  min-height: 34px;
  padding: 0 0 14px;
  font-size: 15px;
  text-align: center;
}

.video-mode-tab.is-active {
  color: #4f46ff;
  font-weight: 650;
}

.video-mode-tab.is-active::after {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 3px;
  border-radius: 999px;
  background: #635bff;
  content: '';
}

.video-mode-tool {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  color: #6b7280;
}

.video-mode-tool:hover,
.seed-random-button:hover {
  background: rgba(255, 255, 255, 0.06);
}

.video-reference-shell {
  overflow: hidden;
  border: 1px solid #e3e6ef;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.06);
}

.reference-strip {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 70px;
  padding: 10px 14px;
  border-top: 12px solid #f0f2f8;
}

.reference-strip > span {
  color: #8c94ad;
  font-size: 14px;
}

.reference-example-row {
  display: flex;
  gap: 10px;
}

.reference-example-thumb,
.reference-file {
  position: relative;
  overflow: hidden;
  width: 44px;
  height: 44px;
  border-radius: 7px;
  background:
    linear-gradient(135deg, rgba(17, 24, 39, 0.05), rgba(17, 24, 39, 0.18)),
    linear-gradient(135deg, #a7c7e7, #d8b4fe 48%, #fed7aa);
}

.reference-file {
  width: 86px;
  height: 86px;
  border: 1px solid rgba(148, 163, 184, 0.25);
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
}

.reference-file:hover,
.reference-file.is-active {
  transform: translateY(-1px);
  border-color: rgba(99, 91, 255, 0.55);
  box-shadow: 0 0 0 2px rgba(99, 91, 255, 0.12);
}

.reference-example-thumb:nth-child(2) {
  background: linear-gradient(135deg, #e6ccb2, #6b7280);
}

.reference-example-thumb:nth-child(3) {
  background: linear-gradient(135deg, #c4b5fd, #334155);
}

.reference-example-thumb:nth-child(4) {
  background: linear-gradient(135deg, #99f6e4, #1e293b);
}

.reference-example-thumb:nth-child(5) {
  background: linear-gradient(135deg, #fde68a, #94a3b8);
}

.reference-example-thumb span {
  position: absolute;
  right: 3px;
  bottom: 3px;
  display: grid;
  min-width: 18px;
  height: 18px;
  place-items: center;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.78);
  color: #ffffff;
  font-size: 11px;
}

.video-upload-zone {
  display: grid;
  gap: 6px;
  min-height: 84px;
  place-items: center;
  padding: 14px;
  border-top: 1px dashed #dde1ec;
  color: #69708a;
  cursor: pointer;
  text-align: center;
}

.video-upload-zone input {
  display: none;
}

.video-upload-zone strong {
  color: #111a3d;
  font-size: 14px;
}

.video-upload-zone small {
  color: #8c94ad;
  font-size: 12px;
}

.video-upload-zone.is-disabled {
  cursor: default;
}

.reference-file-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px 14px 14px;
}

.reference-file img,
.reference-file video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.reference-name-button,
.reference-video-badge,
.reference-select-check,
.reference-remove-button {
  position: absolute;
  border: 0;
  border-radius: 999px;
  color: #ffffff;
  font: inherit;
  font-size: 11px;
  line-height: 1;
}

.reference-name-button,
.reference-video-badge {
  top: 5px;
  left: 5px;
  padding: 5px 7px;
  background: rgba(99, 91, 255, 0.88);
}

.reference-name-button,
.reference-remove-button {
  cursor: pointer;
}

.reference-video-badge {
  background: rgba(15, 23, 42, 0.78);
}

.reference-select-check {
  left: 5px;
  bottom: 5px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-height: 22px;
  padding: 4px 7px;
  background: rgba(15, 23, 42, 0.72);
}

.reference-select-check input {
  width: 12px;
  height: 12px;
  accent-color: #635bff;
}

.reference-remove-button {
  right: 5px;
  bottom: 5px;
  padding: 5px 7px;
  background: rgba(15, 23, 42, 0.74);
}

.video-reference-summary {
  display: grid;
  gap: 8px;
  margin: 0 14px 14px;
  border: 1px solid rgba(99, 91, 255, 0.14);
  border-radius: 8px;
  padding: 10px;
  background: rgba(99, 91, 255, 0.08);
}

.video-reference-summary strong,
.video-reference-summary span {
  display: block;
}

.video-reference-summary strong {
  color: #111a3d;
  font-size: 13px;
  font-weight: 650;
}

.video-reference-summary span {
  color: #8c94ad;
  font-size: 12px;
  line-height: 1.45;
}

.video-reference-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.video-reference-chip {
  border: 1px solid rgba(99, 91, 255, 0.22);
  border-radius: 999px;
  padding: 5px 9px;
  background: rgba(255, 255, 255, 0.06);
  color: #343a56;
  cursor: pointer;
  font: inherit;
  font-size: 12px;
}

.video-reference-chip.is-active {
  border-color: rgba(99, 91, 255, 0.46);
  background: rgba(99, 91, 255, 0.14);
  color: #111a3d;
}

.video-form {
  margin-top: 26px;
}

.video-choice-grid {
  display: grid;
  width: 100%;
  gap: 14px;
}

.video-choice-grid.two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.video-choice-grid.ratio {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.video-choice {
  min-height: 40px;
  border: 1px solid var(--studio-border);
  border-radius: var(--studio-radius-inner);
  background: rgba(0, 0, 0, 0.4);
  color: #b0b0b0;
  cursor: pointer;
  font: inherit;
  font-size: 16px;
}

.video-choice.is-selected {
  border-color: var(--studio-primary);
  background: rgba(16, 185, 129, 0.15);
  color: var(--studio-primary);
}

.duration-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 112px;
  gap: 14px;
  width: 100%;
  align-items: center;
}

.seed-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 40px;
  gap: 10px;
  width: 100%;
}

.seed-random-button {
  border: 0;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  color: #635bff;
  cursor: pointer;
  font-size: 18px;
}

.video-submit-button {
  display: grid;
  grid-template-columns: 34px 1fr;
  column-gap: 8px;
  align-items: center;
  width: 100%;
  min-height: 62px;
  border: 0;
  border-radius: 8px;
  padding: 10px 16px;
  background: #19243a;
  color: #ffffff;
  cursor: pointer;
  font: inherit;
}

.video-submit-button:disabled {
  cursor: wait;
  opacity: 0.72;
}

.video-submit-button span {
  grid-row: 1 / span 2;
  font-size: 22px;
}

.video-submit-button strong {
  font-size: 16px;
  font-weight: 650;
}

.video-submit-button small {
  color: rgba(255, 255, 255, 0.82);
  font-size: 12px;
}

.video-disclaimer {
  margin: 10px 0 0;
  color: #a0a6ba;
  font-size: 12px;
  line-height: 1.5;
  text-align: center;
}

.video-preview-panel {
  padding: 24px;
}

.video-preview-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 18px;
}

.video-preview-frame {
  display: grid;
  width: min(520px, 100%);
  min-height: 420px;
  place-items: center;
  margin: 0 auto;
  border: 1px solid #e3e6ef;
  border-radius: 8px;
  background:
    linear-gradient(rgba(255, 255, 255, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.08) 1px, transparent 1px),
    #111827;
  background-size: 28px 28px;
}

.video-status-alert {
  margin-bottom: 16px;
  border-radius: 8px;
}

.video-preview-frame.ratio-9-16,
.video-preview-frame.ratio-3-4 {
  width: min(320px, 100%);
}

.video-preview-frame.ratio-1-1 {
  width: min(420px, 100%);
  min-height: 420px;
}

.video-preview-frame.ratio-4-3 {
  width: min(480px, 100%);
}

.video-preview-inner {
  display: grid;
  max-width: 280px;
  gap: 10px;
  place-items: center;
  color: #ffffff;
  text-align: center;
}

.video-result-player {
  width: 100%;
  height: 100%;
  max-height: 560px;
  border-radius: 8px;
  object-fit: contain;
}

.video-preview-inner span {
  display: grid;
  width: 76px;
  height: 76px;
  place-items: center;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.12);
  font-size: 13px;
  font-weight: 700;
}

.video-preview-inner strong {
  font-size: 18px;
}

.video-preview-inner p {
  margin: 0;
  color: rgba(255, 255, 255, 0.72);
  font-size: 13px;
  line-height: 1.6;
}

.video-meta-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin: 18px 0 0;
}

.video-meta-list div {
  min-height: 70px;
  border-radius: 8px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.06);
}

.video-meta-list dt {
  color: #8c94ad;
  font-size: 12px;
}

.video-meta-list dd {
  margin: 8px 0 0;
  color: #111a3d;
  font-size: 14px;
  font-weight: 650;
}

@media (max-width: 980px) {
  .video-workspace {
    grid-template-columns: 1fr;
  }

  .video-form-panel {
    max-width: 456px;
  }
}

@media (max-width: 560px) {
  .video-form-panel {
    max-width: none;
  }

  .video-mode-tabs,
  .video-choice-grid.ratio,
  .duration-row,
  .video-meta-list {
    grid-template-columns: 1fr;
  }
}
</style>
