<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import {
  deleteTopic,
  generateTopics,
  listProjectTopics,
  updateTopicFavorite,
  type Topic,
  type TopicContentFormat,
  type TopicGenerateResponse,
} from '../api/topics'
import { getProject, type Project } from '../api/projects'
import { buildImagePromptHandoffQuery, type ImagePromptHandoffMode } from '../utils/imagePromptHandoff'
import { runTopicGenerationBatch } from '../utils/topicGenerationScheduler'

const route = useRoute()
const router = useRouter()
const loadingProject = ref(false)
const loadingTopics = ref(false)
const generating = ref(false)
const project = ref<Project | null>(null)
const result = ref<TopicGenerateResponse | null>(null)
const savedTopics = ref<Topic[]>([])
const generatedTopics = ref<Topic[]>([])
const platform = ref('抖音')
const goal = ref('获客')
const contentFormat = ref<TopicContentFormat>('video')
const count = ref(10)
const topicConcurrency = ref(3)
const topicRequestCount = ref(1)
const generatedCount = ref(0)
const totalGenerateCount = ref(0)
const managingTopicIds = ref<Set<number>>(new Set())

const platformOptions = ['抖音', '视频号', '快手', '小红书']
const goalOptions = ['获客', '涨粉', '信任建立', '成交转化']
const contentFormatOptions: Array<{ label: string; value: TopicContentFormat }> = [
  { label: '视频：拍摄脚本 + SeedDance 提示词', value: 'video' },
  { label: '图片：生成提示词', value: 'image' },
  { label: '图生图：参考图改图提示词', value: 'image_to_image' },
]
const countOptions = [10, 30, 50]
const topicConcurrencyOptions = [3, 4, 5, 6, 7, 8, 9, 10]
const topicRequestCountOptions = [1, 2, 3, 4, 5]
const maxTopicAttemptMultiplier = 5

const topics = computed(() => (generatedTopics.value.length ? generatedTopics.value : savedTopics.value))
const generationProgressPercent = computed(() => {
  if (totalGenerateCount.value <= 0) return 0
  return Math.min(100, Math.round((generatedCount.value / totalGenerateCount.value) * 100))
})
const generationProgressText = computed(() => {
  if (!generating.value || totalGenerateCount.value <= 0) return ''
  return `生成选题中 ${generationProgressPercent.value}%`
})

function projectId() {
  return Number(route.params.id)
}

function platformTagClass(platformName: string) {
  if (platformName.includes('抖音')) return 'platform-douyin'
  if (platformName.includes('快手')) return 'platform-kuaishou'
  if (platformName.includes('小红书')) return 'platform-xiaohongshu'
  if (platformName.includes('视频号')) return 'platform-video'
  return ''
}

async function fetchProject() {
  loadingProject.value = true
  try {
    project.value = await getProject(projectId())
  } catch (error) {
    ElMessage.error('项目信息加载失败')
  } finally {
    loadingProject.value = false
  }
}

async function fetchSavedTopics() {
  loadingTopics.value = true
  try {
    savedTopics.value = await listProjectTopics(projectId())
  } catch (error) {
    savedTopics.value = []
  } finally {
    loadingTopics.value = false
  }
}

async function handleGenerate() {
  generating.value = true
  result.value = null
  generatedTopics.value = []
  savedTopics.value = []
  generatedCount.value = 0
  totalGenerateCount.value = count.value
  const generationBatchId = createGenerationBatchId()
  try {
    await generateConcurrentTopicBatch(count.value, 0, generationBatchId)
    ElMessage.success('选题已生成')
  } catch (error) {
    ElMessage.error('选题生成失败')
  } finally {
    generating.value = false
    totalGenerateCount.value = 0
  }
}

async function generateConcurrentTopicBatch(
  batchSize: number,
  requestedCount: number,
  generationBatchId: string,
) {
  const maxAttempts = batchSize * maxTopicAttemptMultiplier

  await runTopicGenerationBatch<Topic>({
    targetCount: batchSize,
    requestedOffset: requestedCount,
    concurrency: topicConcurrency.value,
    requestTopicCount: topicRequestCount.value,
    maxAttempts,
    generate: async ({ topicIndex, requestCount }) => {
      const existingTitles = generatedTopics.value.map((topic) => topic.title)

      const batchResult = await generateTopics(
        projectId(),
        platform.value,
        goal.value,
        contentFormat.value,
        requestCount,
        existingTitles,
        topicIndex,
        generationBatchId,
        count.value,
      )
      result.value = batchResult
      return batchResult.topics
    },
    append: appendGeneratedTopics,
  })
}

function createGenerationBatchId() {
  return `topics-${projectId()}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

async function appendGeneratedTopics(newTopics: Topic[]) {
  generatedTopics.value = [...generatedTopics.value, ...newTopics]
  savedTopics.value = generatedTopics.value
  generatedCount.value = Math.min(generatedTopics.value.length, totalGenerateCount.value)
  await nextTick()
}

function topicText(topic: Topic) {
  return [
    `标题：${topic.title}`,
    `类型：${topic.content_type}`,
    `平台：${topic.platform}`,
    `目标：${topic.goal}`,
    `用户痛点：${topic.topic_data.user_pain_point}`,
    `开头钩子：${topic.topic_data.hook}`,
    `拍摄建议：${topic.topic_data.shooting_suggestion}`,
    `转化方式：${topic.topic_data.conversion_method}`,
    topic.topic_data.shooting_script ? `拍摄脚本：${topic.topic_data.shooting_script}` : '',
    topic.topic_data.seeddance_video_prompt
      ? `SeedDance 参考生视频提示词：${topic.topic_data.seeddance_video_prompt}`
      : '',
    topic.topic_data.image_prompt ? `图片生成提示词：${topic.topic_data.image_prompt}` : '',
    topic.topic_data.image_edit_prompt
      ? `图生图改图提示词：${topic.topic_data.image_edit_prompt}`
      : '',
    `评分：${topic.score}`,
  ]
    .filter(Boolean)
    .join('\n')
}

function topicContentFormatLabel(topic: Topic) {
  const format = topic.topic_data.content_format || contentFormat.value
  if (format === 'image') return '图片'
  if (format === 'image_to_image') return '图生图'
  return '视频'
}

async function copyTopic(topic: Topic) {
  try {
    await navigator.clipboard.writeText(topicText(topic))
    ElMessage.success('已复制选题')
  } catch (error) {
    ElMessage.error('复制失败，请手动复制页面内容')
  }
}

async function copyAllTopics() {
  if (!topics.value.length) return

  try {
    await navigator.clipboard.writeText(topics.value.map(topicText).join('\n\n---\n\n'))
    ElMessage.success('已复制全部选题')
  } catch (error) {
    ElMessage.error('复制失败，请手动复制页面内容')
  }
}

function openScriptPage(topic: Topic) {
  router.push(`/projects/${projectId()}/topics/${topic.id}/script`)
}

function openImageGenerationPage(promptText: string | undefined, mode: ImagePromptHandoffMode) {
  const cleanPrompt = (promptText || '').trim()
  if (!cleanPrompt) {
    ElMessage.warning('图片提示词为空')
    return
  }

  router.push({
    name: 'image-generation',
    params: { id: projectId() },
    query: buildImagePromptHandoffQuery(cleanPrompt, mode),
  })
}

function openVideoGenerationPage(promptText: string | undefined) {
  const cleanPrompt = (promptText || '').trim()
  if (!cleanPrompt) {
    ElMessage.warning('视频提示词为空')
    return
  }

  router.push({
    name: 'video-generation',
    params: { id: projectId() },
    query: { mode: 'reference', prompt: cleanPrompt },
  })
}

function setTopicManaging(topicId: number, isManaging: boolean) {
  const next = new Set(managingTopicIds.value)
  if (isManaging) {
    next.add(topicId)
  } else {
    next.delete(topicId)
  }
  managingTopicIds.value = next
}

function isTopicManaging(topicId: number) {
  return managingTopicIds.value.has(topicId)
}

function replaceTopic(updatedTopic: Topic) {
  generatedTopics.value = generatedTopics.value.map((topic) =>
    topic.id === updatedTopic.id ? updatedTopic : topic,
  )
  savedTopics.value = savedTopics.value.map((topic) =>
    topic.id === updatedTopic.id ? updatedTopic : topic,
  )
}

function removeTopic(topicId: number) {
  generatedTopics.value = generatedTopics.value.filter((topic) => topic.id !== topicId)
  savedTopics.value = savedTopics.value.filter((topic) => topic.id !== topicId)
}

async function toggleTopicFavorite(topic: Topic) {
  setTopicManaging(topic.id, true)
  try {
    const updatedTopic = await updateTopicFavorite(topic.id, !topic.is_favorite)
    replaceTopic(updatedTopic)
    ElMessage.success(updatedTopic.is_favorite ? '已收藏选题' : '已取消收藏')
  } catch (error) {
    ElMessage.error('选题收藏状态更新失败')
  } finally {
    setTopicManaging(topic.id, false)
  }
}

async function removeGeneratedTopic(topic: Topic) {
  setTopicManaging(topic.id, true)
  try {
    await deleteTopic(topic.id)
    removeTopic(topic.id)
    ElMessage.success('选题已删除')
  } catch (error) {
    ElMessage.error('选题删除失败')
  } finally {
    setTopicManaging(topic.id, false)
  }
}

onMounted(async () => {
  await fetchProject()
  await fetchSavedTopics()
})
</script>

<template>
  <section class="page-section">
    <div class="section-header">
      <div>
        <p class="eyebrow">Topic Generation</p>
        <h1>{{ project?.project_name || '选题生成' }}</h1>
      </div>
      <div class="header-actions">
        <el-button @click="router.push(`/projects/${projectId()}`)">返回项目详情</el-button>
        <el-button type="primary" :loading="generating" @click="handleGenerate">
          生成选题
        </el-button>
      </div>
    </div>

    <el-skeleton v-if="loadingProject" :rows="6" animated />
    <template v-else>
      <el-alert
        v-if="project"
        class="project-summary"
        type="info"
        :closable="false"
        show-icon
      >
        <template #title>
          {{ project.industry }} / {{ project.product }} / {{ project.platforms.join('、') }}
        </template>
        {{ project.personal_intro }}；目标客户：{{ project.target_audience }}
      </el-alert>

      <div class="plan-controls">
        <el-form label-position="top" class="plan-control-form">
          <div class="topic-control-grid">
            <el-form-item label="平台">
              <el-select v-model="platform" class="full-width platform-select" popper-class="platform-select-popper">
                <el-option
                  v-for="item in platformOptions"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="内容目标">
              <el-select v-model="goal" class="full-width">
                <el-option v-for="item in goalOptions" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
            <el-form-item label="内容形态">
              <el-select v-model="contentFormat" class="full-width">
                <el-option
                  v-for="item in contentFormatOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="选题数量">
              <el-select v-model="count" class="full-width">
                <el-option
                  v-for="item in countOptions"
                  :key="item"
                  :label="`${item} 个`"
                  :value="item"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="并发数">
              <el-select v-model="topicConcurrency" class="full-width">
                <el-option
                  v-for="item in topicConcurrencyOptions"
                  :key="item"
                  :label="`${item} 个并发`"
                  :value="item"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="每个请求选题数">
              <el-select v-model="topicRequestCount" class="full-width">
                <el-option
                  v-for="item in topicRequestCountOptions"
                  :key="item"
                  :label="`${item} 个/请求`"
                  :value="item"
                />
              </el-select>
            </el-form-item>
          </div>
        </el-form>
      </div>

      <el-skeleton v-if="generating && !topics.length" :rows="8" animated />

      <div v-else-if="!topics.length && !loadingTopics" class="empty-state">
        <h2>尚未生成选题</h2>
        <p>选择平台、目标、内容形态和数量后生成可直接使用的选题方案。</p>
      </div>

      <template v-else>
        <div class="result-toolbar">
          <div class="meta-text">
            <template v-if="result">
              <span v-if="generationProgressText">{{ generationProgressText }} / </span>
              Provider：{{ result.provider }} / Model：{{ result.model }} / 记录 ID：{{
                result.generation_record_id
              }}
            </template>
            <template v-else>已保存选题：{{ topics.length }} 个</template>
          </div>
          <el-button :disabled="!topics.length" @click="copyAllTopics">复制全部选题</el-button>
        </div>

        <el-skeleton v-if="loadingTopics" :rows="8" animated />
        <div v-else class="topic-card-grid">
          <article v-for="topic in topics" :key="topic.id" class="topic-card">
            <div class="topic-card-header">
              <div>
                <el-tag :class="['platform-tag', platformTagClass(topic.platform)]">
                  {{ topic.platform }}
                </el-tag>
                <el-tag class="tag-item">{{ topic.content_type }}</el-tag>
                <el-tag class="tag-item" type="warning">{{ topic.goal }}</el-tag>
                <el-tag class="tag-item" type="success">{{ topicContentFormatLabel(topic) }}</el-tag>
                <el-tag v-if="topic.is_favorite" class="tag-item" type="danger">已收藏</el-tag>
              </div>
              <span class="score-badge">{{ topic.score }}</span>
            </div>
            <h2>{{ topic.title }}</h2>
            <dl class="topic-fields">
              <dt>用户痛点</dt>
              <dd>{{ topic.topic_data.user_pain_point }}</dd>
              <dt>开头钩子</dt>
              <dd>{{ topic.topic_data.hook }}</dd>
              <dt>拍摄建议</dt>
              <dd>{{ topic.topic_data.shooting_suggestion }}</dd>
              <dt>转化方式</dt>
              <dd>{{ topic.topic_data.conversion_method }}</dd>
              <template v-if="topic.topic_data.shooting_script">
                <dt>拍摄脚本</dt>
                <dd>{{ topic.topic_data.shooting_script }}</dd>
              </template>
              <template v-if="topic.topic_data.seeddance_video_prompt">
                <dt>SeedDance 参考生视频提示词</dt>
                <dd>{{ topic.topic_data.seeddance_video_prompt }}</dd>
              </template>
              <template v-if="topic.topic_data.image_prompt">
                <dt>图片生成提示词</dt>
                <dd>
                  <div class="prompt-action-row">
                    <span>{{ topic.topic_data.image_prompt }}</span>
                    <el-button
                      size="small"
                      type="warning"
                      class="prompt-generate-button"
                      @click="openImageGenerationPage(topic.topic_data.image_prompt, 'text')"
                    >
                      去出图
                    </el-button>
                  </div>
                </dd>
              </template>
              <template v-if="topic.topic_data.image_edit_prompt">
                <dt>图生图改图提示词</dt>
                <dd>
                  <div class="prompt-action-row">
                    <span>{{ topic.topic_data.image_edit_prompt }}</span>
                    <el-button
                      size="small"
                      type="success"
                      class="prompt-generate-button"
                      @click="openImageGenerationPage(topic.topic_data.image_edit_prompt, 'image')"
                    >
                      去图生图
                    </el-button>
                  </div>
                </dd>
              </template>
            </dl>
            <div class="topic-actions">
              <el-button size="small" @click="copyTopic(topic)">复制选题</el-button>
              <el-button
                size="small"
                :loading="isTopicManaging(topic.id)"
                @click="toggleTopicFavorite(topic)"
              >
                {{ topic.is_favorite ? '取消收藏' : '收藏' }}
              </el-button>
              <el-button
                size="small"
                type="danger"
                plain
                :loading="isTopicManaging(topic.id)"
                @click="removeGeneratedTopic(topic)"
              >
                删除
              </el-button>
              <el-button size="small" type="primary" plain @click="openScriptPage(topic)">
                生成文案
              </el-button>
              <el-button
                v-if="topic.topic_data.seeddance_video_prompt"
                size="small"
                type="primary"
                @click="openVideoGenerationPage(topic.topic_data.seeddance_video_prompt)"
              >
                去生视频
              </el-button>
            </div>
          </article>
        </div>
      </template>
    </template>

    <div v-if="generating" class="generation-overlay" aria-live="polite">
      <div class="generation-progress-panel">
        <div class="generation-progress-title">生成选题中 {{ generationProgressPercent }}%</div>
        <el-progress
          :percentage="generationProgressPercent"
          :stroke-width="12"
          :show-text="false"
          :indeterminate="generationProgressPercent === 0"
        />
        <p>
          已生成 {{ Math.min(generatedTopics.length, totalGenerateCount) }} /
          {{ totalGenerateCount }} 个选题
        </p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.generation-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.42);
}

.generation-progress-panel {
  width: min(420px, 100%);
  padding: 28px;
  border-radius: 32px;
  border: 1px solid var(--studio-border);
  background:
    radial-gradient(circle at 88% 0%, rgba(124, 58, 237, 0.12), transparent 32%),
    rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(20px) saturate(1.2);
  box-shadow: 0 24px 64px rgba(15, 23, 42, 0.18);
}

.generation-progress-title {
  margin-bottom: 14px;
  color: #0f172a;
  font-size: 18px;
  font-weight: 700;
  text-align: center;
}

.generation-progress-panel p {
  margin: 12px 0 0;
  color: #64748b;
  font-size: 14px;
  text-align: center;
}

.prompt-action-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: start;
}

.prompt-generate-button {
  min-width: 104px;
  font-weight: 700;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
}

@media (max-width: 640px) {
  .prompt-action-row {
    grid-template-columns: 1fr;
  }
}
</style>
