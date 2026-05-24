<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import {
  editImage,
  generateImage,
  type ImageReferencePayload,
  type ImageReferenceType,
  type ImageGenerateResponse,
  type ImageQuality,
  type ImageSize,
} from '../api/images'
import { getProject, type Project } from '../api/projects'
import { readImagePromptHandoffQuery } from '../utils/imagePromptHandoff'

const route = useRoute()
const router = useRouter()
const project = ref<Project | null>(null)
const loadingProject = ref(false)
const generating = ref(false)
const result = ref<ImageGenerateResponse | null>(null)
const generationStatus = ref('')
const generationError = ref('')
const prompt = ref('')
const size = ref<ImageSize>('1536x1024')
const quality = ref<ImageQuality>('medium')
const mode = ref<'text' | 'image'>('text')

interface LocalReferenceImage extends ImageReferencePayload {
  id: string
  preview: string
}

const referenceImages = ref<LocalReferenceImage[]>([])

let imageGenerationAbortController: AbortController | null = null

const sizeOptions: Array<{ label: string; value: ImageSize; note: string }> = [
  { label: '横图', value: '1536x1024', note: '更适合宽画面构图' },
  { label: '方图', value: '1024x1024', note: '更适合产品主体图' },
  { label: '竖图', value: '1024x1536', note: '更适合竖向海报图' },
  { label: '自动', value: 'auto', note: '由模型判断比例' },
]

const modeOptions = [
  { label: '文生图', value: 'text' },
  { label: '图生图', value: 'image' },
]

const referenceTypeOptions: Array<{
  label: string
  value: ImageReferenceType
  note: string
}> = [
  { label: '人设参考图', value: 'persona', note: '账号本人，例如苹果姐；上传后才允许生成可识别人设' },
  { label: '货品参考图', value: 'product', note: '文案里的产品，例如手镯、吊坠、证书细节' },
  { label: '场景参考图', value: 'location', note: '文案里的公司、档口、柜台、直播间等场景' },
]

const qualityOptions: Array<{ label: string; value: ImageQuality }> = [
  { label: '中等', value: 'medium' },
  { label: '高清', value: 'high' },
  { label: '快速', value: 'low' },
  { label: '自动', value: 'auto' },
]

const referencePromptStart = '【参考图绑定（自动生成）】'
const referencePromptEnd = '【参考图绑定结束】'

const previewSrc = computed(() => {
  const image = result.value?.images?.[0]
  return image?.data_url || image?.url || ''
})
const referenceImageCount = computed(() => referenceImages.value.length)

function projectId() {
  return Number(route.params.id)
}

async function fetchProject() {
  loadingProject.value = true
  try {
    project.value = await getProject(projectId())
    if (!prompt.value) {
      prompt.value = buildDefaultPrompt(project.value)
    }
  } catch (error) {
    ElMessage.error('项目上下文加载失败')
  } finally {
    loadingProject.value = false
  }
}

function applyPromptHandoffFromRoute() {
  const handoff = readImagePromptHandoffQuery(route.query)
  if (!handoff) return

  prompt.value = handoff.prompt
  mode.value = handoff.mode
}

function buildDefaultPrompt(item: Project) {
  return [
    `为“${item.project_name}”生成一张高级清透的翡翠产品图。`,
    `产品：${item.product}。行业：${item.industry} / ${item.sub_industry}。`,
    `画面要求：干净留白、柔和自然光、低饱和翡翠绿和香槟金点缀、真实产品质感。`,
    `不要出现乱码文字，不要出现夸张特效，整体风格高级、可信、清透。`,
  ].join('\n')
}

async function handleGenerate() {
  if (mode.value === 'image') {
    syncReferencePromptBlock()
  }
  const cleanPrompt = prompt.value.trim()
  if (!cleanPrompt) {
    ElMessage.warning('请先填写图片提示词')
    return
  }
  if (mode.value === 'image' && referenceImageCount.value < 1) {
    ElMessage.warning('图生图至少要上传一张参考图')
    return
  }

  generating.value = true
  result.value = null
  generationError.value = ''
  generationStatus.value = '图片生成已提交，通常需要 2-3 分钟；请保持页面打开，不要重复点击。'
  imageGenerationAbortController?.abort()
  imageGenerationAbortController = new AbortController()
  const signal = imageGenerationAbortController.signal
  try {
    const startedAt = Date.now()
    result.value =
      mode.value === 'image'
        ? await editImage(
            projectId(),
            cleanPrompt,
            referenceImages.value.map(toReferencePayload),
            size.value,
            quality.value,
            signal,
          )
        : await generateImage(projectId(), cleanPrompt, size.value, quality.value, signal)
    generationStatus.value = `图片已生成，用时 ${Math.round((Date.now() - startedAt) / 1000)} 秒。`
    ElMessage.success('图片已生成')
  } catch (error) {
    if ((error as DOMException | { name?: string })?.name === 'AbortError') {
      generationStatus.value = '图片生成已取消。'
      return
    }
    const message = apiErrorMessage(error, '图片生成失败，请检查模型渠道或稍后重试')
    generationError.value = message
    generationStatus.value = '图片生成失败，未返回可用图片。'
    ElMessage.error(message)
  } finally {
    generating.value = false
  }
}

async function handleReferenceImageChange(event: Event, referenceType: ImageReferenceType) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  if (!files.length) return

  const availableSlots = 3 - referenceImagesByType(referenceType).length
  if (availableSlots <= 0) {
    ElMessage.warning('每类参考图最多上传 3 张')
    input.value = ''
    return
  }
  if (files.length > availableSlots) {
    ElMessage.warning(`当前类别还能上传 ${availableSlots} 张，已自动截取`)
  }

  try {
    for (const file of files.slice(0, availableSlots)) {
      if (!isSupportedReferenceImage(file)) {
        ElMessage.warning('参考图仅支持 PNG、JPEG、WebP')
        continue
      }
      const dataUrl = await readFileAsDataUrl(file)
      referenceImages.value.push({
        id: `${referenceType}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        reference_image_type: referenceType,
        source_image_base64: dataUrl.split(',', 2)[1] || '',
        source_image_mime: file.type || 'image/png',
        source_image_filename: file.name || 'source.png',
        preview: dataUrl,
      })
    }
    mode.value = 'image'
    syncReferencePromptBlock()
  } catch (error) {
    ElMessage.error('参考图读取失败')
  } finally {
    input.value = ''
  }
}

function isSupportedReferenceImage(file: File) {
  return ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'].includes(file.type.toLowerCase())
}

function apiErrorMessage(error: unknown, fallback: string) {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detail === 'string' && detail.trim() ? detail : fallback
}

function referenceImagesByType(referenceType: ImageReferenceType) {
  return referenceImages.value.filter((image) => image.reference_image_type === referenceType)
}

function removeReferenceImage(imageId: string) {
  referenceImages.value = referenceImages.value.filter((image) => image.id !== imageId)
  syncReferencePromptBlock()
}

function clearReferenceImages(referenceType: ImageReferenceType) {
  referenceImages.value = referenceImages.value.filter((image) => image.reference_image_type !== referenceType)
  syncReferencePromptBlock()
}

function toReferencePayload(image: LocalReferenceImage): ImageReferencePayload {
  return {
    reference_image_type: image.reference_image_type,
    source_image_base64: image.source_image_base64,
    source_image_mime: image.source_image_mime,
    source_image_filename: image.source_image_filename,
  }
}

function syncReferencePromptBlock() {
  const basePrompt = stripReferencePromptBlock(prompt.value).trim()
  if (!referenceImages.value.length) {
    prompt.value = basePrompt
    return
  }

  prompt.value = [basePrompt, buildReferencePromptBlock()].filter(Boolean).join('\n\n')
}

function stripReferencePromptBlock(value: string) {
  const startIndex = value.indexOf(referencePromptStart)
  const endIndex = value.indexOf(referencePromptEnd)
  if (startIndex === -1 || endIndex === -1 || endIndex < startIndex) return value

  return `${value.slice(0, startIndex)}${value.slice(endIndex + referencePromptEnd.length)}`.trim()
}

function buildReferencePromptBlock() {
  const lines = [
    referencePromptStart,
    '术语定义：人设图只定义账号人物/出镜人物，包括脸、年龄感、发型、体型、气质和穿搭风格。',
    '术语定义：货品图只定义商品，包括形状、颜色、材质、纹理、比例、证书或关键细节。',
    '术语定义：场景图只定义拍摄环境，包括档口、公司、桌面、柜台、灯光、陈列方式和空间氛围。',
    '必须按下面顺序绑定参考图用途，不要把人设图、货品图、场景图混用。',
    '同一类型有多张图时，第 1 张为主参考，其余只作为补充；不要把多张图混合成新的人脸、新货品或新场景。',
    ...referencePromptImageLines(),
  ]

  if (referenceImagesByType('persona').length) {
    lines.push(
      `人设参考图：画面人物必须参考已上传的人设图；如果文案写“${project.value?.project_name || '账号人设'}”，不要凭名字另造人物。`,
    )
  } else {
    lines.push('未上传人设参考图：不要生成账号本人/昵称对应人物/正脸；如需人物，只允许非人设手部、背影或工作人员局部。')
  }

  if (referenceImagesByType('product').length) {
    lines.push(`货品参考图：货品按上传图理解，重点保留 ${project.value?.product || '货品'} 的形状、颜色、材质、比例和关键细节。`)
  }
  if (referenceImagesByType('location').length) {
    lines.push('场景参考图：环境按上传图理解，重点保留空间、桌面/档口/公司陈列关系和光线氛围。')
  }

  lines.push('生成目标：在上述参考图约束下，生成一张新的完整图片。')
  lines.push(referencePromptEnd)
  return lines.join('\n')
}

function referenceTypeLabel(referenceType: ImageReferenceType) {
  if (referenceType === 'persona') return '人设参考图'
  if (referenceType === 'product') return '货品参考图'
  return '场景参考图'
}

function referencePromptImageLines() {
  const counts: Record<ImageReferenceType, number> = {
    persona: 0,
    product: 0,
    location: 0,
  }

  return referenceImages.value.map((image) => {
    counts[image.reference_image_type] += 1
    return `${referencePromptImageName(image.reference_image_type, counts[image.reference_image_type])}：${referenceTypeLabel(image.reference_image_type)}，文件名 ${image.source_image_filename}。`
  })
}

function referencePromptImageName(referenceType: ImageReferenceType, index: number) {
  if (referenceType === 'persona') return `人设图${index}`
  if (referenceType === 'product') return `货品图${index}`
  return `场景图${index}`
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(file)
  })
}

async function copyPrompt() {
  try {
    await navigator.clipboard.writeText(prompt.value)
    ElMessage.success('提示词已复制')
  } catch (error) {
    ElMessage.error('复制失败，请手动复制')
  }
}

function downloadImage() {
  if (!previewSrc.value) return
  const link = document.createElement('a')
  link.href = previewSrc.value
  link.download = `jsvoc-image-${projectId()}-${Date.now()}.png`
  link.click()
}

onMounted(async () => {
  applyPromptHandoffFromRoute()
  await fetchProject()
})

onBeforeUnmount(() => {
  imageGenerationAbortController?.abort()
  imageGenerationAbortController = null
})
</script>

<template>
  <section class="page-section image-generation-page">
    <div class="section-header">
      <div>
        <p class="eyebrow">Image Generation</p>
        <h1>{{ project?.project_name || '图片生成' }}</h1>
      </div>
      <div class="header-actions action-ribbon">
        <el-button @click="router.push(`/projects/${projectId()}`)">返回项目</el-button>
        <el-button @click="router.push(`/projects/${projectId()}/topics`)">选题生成</el-button>
        <el-button type="primary" :loading="generating" @click="handleGenerate">生成图片</el-button>
      </div>
    </div>

    <el-skeleton v-if="loadingProject" :rows="7" animated />

    <template v-else>
      <div class="image-generator-grid">
        <article class="image-prompt-card">
          <div class="image-card-title">
            <div>
              <p class="eyebrow">Prompt</p>
              <h2>生图程序</h2>
            </div>
            <el-tag class="module-mint">gpt-image-2</el-tag>
          </div>

          <el-form label-position="top" class="image-form">
            <el-form-item label="生成方式">
              <div class="image-mode-grid">
                <button
                  v-for="item in modeOptions"
                  :key="item.value"
                  type="button"
                  :class="['image-mode-card', { 'is-selected': mode === item.value }]"
                  @click="mode = item.value as 'text' | 'image'"
                >
                  <strong>{{ item.label }}</strong>
                  <span>
                    {{
                      item.value === 'image'
                        ? '上传参考图，再按提示词改图'
                        : '只输入提示词直接生成图片'
                    }}
                  </span>
                </button>
              </div>
            </el-form-item>

            <el-form-item v-if="mode === 'image'" label="参考图">
              <div class="reference-type-grid">
                <article
                  v-for="item in referenceTypeOptions"
                  :key="item.value"
                  class="reference-type-card"
                >
                  <div class="reference-type-head">
                    <div>
                      <strong>{{ item.label }}</strong>
                      <small>{{ item.note }}</small>
                    </div>
                    <el-tag size="small">{{ referenceImagesByType(item.value).length }}/3</el-tag>
                  </div>

                  <div
                    v-if="referenceImagesByType(item.value).length"
                    class="reference-preview-grid"
                  >
                    <div
                      v-for="image in referenceImagesByType(item.value)"
                      :key="image.id"
                      class="reference-preview-item"
                    >
                      <img :src="image.preview" :alt="image.source_image_filename" />
                      <button type="button" @click="removeReferenceImage(image.id)">移除</button>
                    </div>
                  </div>

                  <label class="source-upload-card compact">
                    <input
                      type="file"
                      accept="image/*"
                      multiple
                      @change="handleReferenceImageChange($event, item.value)"
                    />
                    <strong>上传{{ item.label }}</strong>
                    <small>最少 0 张，最多 3 张</small>
                  </label>

                  <div v-if="referenceImagesByType(item.value).length" class="source-upload-actions">
                    <el-button size="small" @click="clearReferenceImages(item.value)">清空本类</el-button>
                  </div>
                </article>
              </div>
              <p class="reference-rule-note">
                图生图至少上传 1 张；没有人设参考图时，只生成货品和场景，不生成可识别人设本人。
              </p>
            </el-form-item>

            <el-form-item label="图片提示词">
              <el-input
                v-model="prompt"
                type="textarea"
                :rows="11"
                maxlength="2000"
                show-word-limit
                placeholder="写清楚产品、场景、光线、质感、风格和不要出现的元素"
              />
            </el-form-item>

            <div class="image-option-grid">
              <el-form-item label="尺寸">
                <div class="image-size-grid">
                  <button
                    v-for="item in sizeOptions"
                    :key="item.value"
                    type="button"
                    :class="['image-size-option', { 'is-selected': size === item.value }]"
                    @click="size = item.value"
                  >
                    <strong>{{ item.label }}</strong>
                    <span>{{ item.value }}</span>
                    <small>{{ item.note }}</small>
                  </button>
                </div>
              </el-form-item>

              <el-form-item label="质量">
                <el-segmented
                  v-model="quality"
                  :options="qualityOptions"
                  block
                />
              </el-form-item>
            </div>
          </el-form>

          <div class="image-actions">
            <el-button @click="copyPrompt">复制提示词</el-button>
            <el-button type="primary" :loading="generating" @click="handleGenerate">
              {{ mode === 'image' ? '按图生成' : '生成图片' }}
            </el-button>
          </div>
        </article>

        <article class="image-preview-card">
          <div class="image-card-title">
            <div>
              <p class="eyebrow">Preview</p>
              <h2>生成结果</h2>
            </div>
            <el-tag v-if="result" class="module-blue">{{ result.latency_ms }} ms</el-tag>
          </div>

          <el-alert
            v-if="generationError"
            class="image-status-alert"
            type="error"
            show-icon
            :closable="false"
            :title="generationStatus"
            :description="generationError"
          />

          <el-alert
            v-else-if="generationStatus"
            class="image-status-alert"
            :type="result ? 'success' : 'info'"
            show-icon
            :closable="false"
            :title="generationStatus"
          />

          <div v-if="generating" class="image-loading-panel">
            <el-skeleton :rows="8" animated />
            <p>图片生成通常需要 2-3 分钟；如果上游 502/503/504，系统会自动重试一次。</p>
          </div>

          <div v-else-if="previewSrc" class="image-preview-frame">
            <img :src="previewSrc" alt="生成图片预览" />
          </div>

          <div v-else class="image-empty-preview">
            <span>IMG</span>
            <h3>等待生成</h3>
            <p>{{ mode === 'image' ? '上传参考图并输入提示词后会在这里预览新图。' : '输入提示词后会在这里预览图片。' }}</p>
          </div>

          <div class="image-result-meta">
            <template v-if="result">
              <span>Provider: {{ result.provider }}</span>
              <span>Model: {{ result.model }}</span>
              <span>数量: {{ result.images.length }}</span>
            </template>
            <template v-else>
              <span>{{ mode === 'image' ? '图生图' : '文生图' }}</span>
              <span>尺寸: {{ size }}</span>
              <span>质量: {{ quality }}</span>
            </template>
          </div>

          <div class="image-actions">
            <el-button :disabled="!previewSrc" @click="downloadImage">下载图片</el-button>
            <el-button type="primary" plain :loading="generating" :disabled="!previewSrc" @click="handleGenerate">
              再生成
            </el-button>
          </div>
        </article>
      </div>
    </template>
  </section>
</template>

<style scoped>
.image-generation-page {
  width: min(1180px, 100%);
}

.image-generator-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.02fr) minmax(360px, 0.98fr);
  gap: 20px;
}

.image-prompt-card,
.image-preview-card {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  min-height: 640px;
  border: 1px solid var(--studio-border);
  border-radius: var(--studio-radius-card);
  padding: 28px;
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(20px) saturate(1.2);
  box-shadow: var(--studio-shadow);
  transition:
    transform 0.28s cubic-bezier(0.34, 1.56, 0.64, 1),
    box-shadow 0.25s ease,
    border-color 0.25s ease;
}

.image-prompt-card:hover,
.image-preview-card:hover {
  transform: translateY(-4px);
  border-color: rgba(5, 150, 105, 0.12);
  box-shadow: var(--studio-glow);
}

.image-prompt-card::before,
.image-prompt-card::after,
.image-preview-card::before,
.image-preview-card::after {
  position: absolute;
  z-index: 0;
  width: 128px;
  height: 128px;
  border-radius: 9999px;
  content: '';
  opacity: 0;
  pointer-events: none;
  transition:
    opacity 0.34s ease,
    transform 0.42s cubic-bezier(0.2, 0.95, 0.28, 1.1);
}

.image-prompt-card::before,
.image-preview-card::before {
  top: -38px;
  left: -46px;
  background: radial-gradient(circle, rgba(5, 150, 105, 0.2), rgba(5, 150, 105, 0) 68%);
  transform: translate(-34px, -12px) scale(0.55);
}

.image-prompt-card::after,
.image-preview-card::after {
  right: -50px;
  bottom: -44px;
  background: radial-gradient(circle, rgba(246, 213, 138, 0.25), rgba(246, 213, 138, 0) 68%);
  transform: translate(34px, 16px) scale(0.55);
}

.image-prompt-card:hover::before,
.image-preview-card:hover::before {
  opacity: 1;
  transform: translate(58px, 34px) scale(1.18);
}

.image-prompt-card:hover::after,
.image-preview-card:hover::after {
  opacity: 1;
  transform: translate(-62px, -34px) scale(1.1);
}

.image-prompt-card > *,
.image-preview-card > * {
  position: relative;
  z-index: 1;
}

.image-card-title,
.image-actions,
.image-result-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.image-card-title {
  margin-bottom: 22px;
}

.image-card-title h2 {
  margin: 0;
  color: var(--studio-ink);
  font-size: 22px;
  font-weight: 660;
}

.image-form .el-form-item {
  margin-bottom: 18px;
}

.image-mode-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  width: 100%;
}

.image-mode-card {
  min-height: 86px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 18px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--studio-soft-ink);
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition:
    transform 0.22s ease,
    border-color 0.22s ease,
    box-shadow 0.22s ease,
    background 0.22s ease;
}

.image-mode-card:hover,
.image-mode-card.is-selected {
  transform: translateY(-2px);
  border-color: rgba(5, 150, 105, 0.18);
  background: rgba(16, 185, 129, 0.12);
  box-shadow: 0 14px 32px rgba(15, 23, 42, 0.055);
}

.image-mode-card strong,
.image-mode-card span {
  display: block;
}

.image-mode-card strong {
  color: var(--studio-ink);
  font-size: 15px;
  font-weight: 660;
}

.image-mode-card span {
  margin-top: 8px;
  color: var(--studio-muted);
  font-size: 13px;
  line-height: 1.35;
}

.source-upload-card {
  display: grid;
  width: 100%;
  min-height: 168px;
  place-items: center;
  overflow: hidden;
  border: 1px dashed rgba(5, 150, 105, 0.2);
  border-radius: 24px;
  padding: 16px;
  background:
    radial-gradient(circle at 82% 0%, rgba(246, 213, 138, 0.18), transparent 30%),
    rgba(0, 0, 0, 0.55);
  color: var(--studio-soft-ink);
  cursor: pointer;
  text-align: center;
  transition:
    transform 0.22s ease,
    border-color 0.22s ease,
    box-shadow 0.22s ease;
}

.reference-type-grid {
  display: grid;
  width: 100%;
  gap: 12px;
}

.reference-type-card {
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 24px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.06);
}

.reference-type-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.reference-type-head strong,
.reference-type-head small {
  display: block;
}

.reference-type-head strong {
  color: var(--studio-ink);
  font-size: 15px;
  font-weight: 660;
}

.reference-type-head small {
  margin-top: 5px;
  color: var(--studio-muted);
  font-size: 12px;
  line-height: 1.35;
}

.reference-preview-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 10px;
}

.reference-preview-item {
  position: relative;
  overflow: hidden;
  border-radius: 14px;
  background: rgba(0, 0, 0, 0.55);
  border: 1px solid var(--studio-border);
}

.reference-preview-item img {
  display: block;
  width: 100%;
  height: 86px;
  object-fit: cover;
}

.reference-preview-item button {
  position: absolute;
  right: 6px;
  bottom: 6px;
  border: 0;
  border-radius: 999px;
  padding: 3px 8px;
  background: rgba(15, 23, 42, 0.72);
  color: #ffffff;
  font: inherit;
  font-size: 12px;
  cursor: pointer;
}

.source-upload-card.compact {
  min-height: 88px;
  border-radius: 18px;
}

.reference-rule-note {
  margin: 10px 0 0;
  color: var(--studio-muted);
  font-size: 13px;
  line-height: 1.5;
}

.source-upload-card:hover {
  transform: translateY(-2px);
  border-color: rgba(5, 150, 105, 0.32);
  box-shadow: 0 14px 32px rgba(15, 23, 42, 0.055);
}

.source-upload-card input {
  display: none;
}

.source-upload-card img {
  width: 100%;
  max-height: 220px;
  border-radius: 18px;
  object-fit: contain;
}

.source-upload-card strong,
.source-upload-card span,
.source-upload-card small {
  display: block;
}

.source-upload-card strong {
  color: var(--studio-ink);
  font-size: 16px;
  font-weight: 640;
}

.source-upload-card span {
  max-width: 100%;
  margin-top: 10px;
  overflow: hidden;
  color: var(--studio-muted);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-upload-card small {
  margin-top: 8px;
  color: var(--studio-muted);
  font-size: 13px;
}

.source-upload-actions {
  display: flex;
  justify-content: flex-end;
  width: 100%;
  margin-top: 10px;
}

.image-option-grid {
  display: grid;
  gap: 18px;
}

.image-size-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  width: 100%;
}

.image-size-option {
  min-height: 96px;
  border: 1px solid rgba(15, 23, 42, 0.05);
  border-radius: 22px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.06);
  color: var(--studio-soft-ink);
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition:
    transform 0.22s ease,
    border-color 0.22s ease,
    box-shadow 0.22s ease,
    background 0.22s ease;
}

.image-size-option:hover,
.image-size-option.is-selected {
  transform: translateY(-2px);
  border-color: rgba(5, 150, 105, 0.16);
  background: rgba(16, 185, 129, 0.12);
  box-shadow: 0 14px 32px rgba(15, 23, 42, 0.055);
}

.image-size-option strong,
.image-size-option span,
.image-size-option small {
  display: block;
}

.image-size-option strong {
  color: var(--studio-ink);
  font-size: 14px;
  font-weight: 620;
}

.image-size-option span {
  margin-top: 7px;
  color: var(--studio-primary-dark);
  font-size: 13px;
  font-weight: 560;
}

.image-size-option small {
  margin-top: 8px;
  color: var(--studio-muted);
  font-size: 12px;
  line-height: 1.35;
}

.image-actions {
  flex-wrap: wrap;
  justify-content: flex-end;
  margin-top: 20px;
}

.image-preview-card {
  display: flex;
  flex-direction: column;
}

.image-preview-frame,
.image-empty-preview,
.image-loading-panel {
  display: grid;
  flex: 1;
  min-height: 420px;
  place-items: center;
  border: 1px solid var(--studio-border);
  border-radius: 28px;
  background:
    radial-gradient(circle at 82% 8%, rgba(246, 213, 138, 0.15), transparent 30%),
    rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(20px) saturate(1.2);
}

.image-preview-frame {
  overflow: hidden;
}

.image-preview-frame img {
  width: 100%;
  height: 100%;
  max-height: 540px;
  object-fit: contain;
}

.image-empty-preview {
  align-content: center;
  padding: 30px;
  text-align: center;
}

.image-empty-preview span {
  display: inline-grid;
  width: 74px;
  height: 74px;
  place-items: center;
  margin: 0 auto 18px;
  border-radius: 26px;
  background: var(--studio-soft-gradient);
  color: var(--studio-primary-dark);
  font-size: 15px;
  font-weight: 680;
  box-shadow: inset 0 0 0 1px rgba(5, 150, 105, 0.08);
}

.image-empty-preview h3 {
  margin: 0 0 8px;
  color: var(--studio-ink);
  font-size: 20px;
  font-weight: 620;
}

.image-empty-preview p,
.image-loading-panel p {
  margin: 0;
  color: var(--studio-muted);
  font-size: 14px;
}

.image-loading-panel {
  align-content: center;
  gap: 16px;
  padding: 28px;
}

.image-status-alert {
  margin-bottom: 16px;
  border-radius: 16px;
}

.image-result-meta {
  flex-wrap: wrap;
  justify-content: flex-start;
  min-height: 38px;
  margin-top: 16px;
  color: var(--studio-muted);
  font-size: 13px;
}

.image-result-meta span {
  display: inline-flex;
  min-height: 28px;
  align-items: center;
  border-radius: var(--studio-radius-pill);
  padding: 0 10px;
  background: rgba(255, 255, 255, 0.06);
}

@media (max-width: 900px) {
  .image-generator-grid {
    grid-template-columns: 1fr;
  }

  .image-prompt-card,
  .image-preview-card {
    min-height: auto;
    padding: 20px;
  }
}

@media (max-width: 520px) {
  .image-mode-grid,
  .image-size-grid {
    grid-template-columns: 1fr;
  }
}
</style>
