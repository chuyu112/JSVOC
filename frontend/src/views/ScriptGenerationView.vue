<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { getProject, type Project } from '../api/projects'
import { generateScript, listTopicScripts, type ScriptGenerateResponse } from '../api/scripts'
import { listProjectTopics, type Topic } from '../api/topics'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const generating = ref(false)
const project = ref<Project | null>(null)
const topic = ref<Topic | null>(null)
const result = ref<ScriptGenerateResponse | null>(null)
const platform = ref('')
const scriptType = ref('聊观点')
const duration = ref('60秒')
const goal = ref('私信获客')

const scriptTypeOptions = [
  '聊观点',
  '讲故事',
  '列清单',
  '做对比',
  '拆案例',
  '讲误区',
  '提问题',
  '反常识',
  '场景代入',
  '客户问答',
]
const platformOptions = ['抖音', '视频号', '快手', '小红书']
const durationOptions = ['30秒', '60秒', '90秒', '3分钟']
const goalOptions = ['私信获客', '评论互动', '信任建立', '成交转化']

const script = computed(() => result.value?.script ?? null)

function projectId() {
  return Number(route.params.projectId)
}

function topicId() {
  return Number(route.params.topicId)
}

function platformTagClass(platformName: string) {
  if (platformName.includes('抖音')) return 'platform-douyin'
  if (platformName.includes('快手')) return 'platform-kuaishou'
  if (platformName.includes('小红书')) return 'platform-xiaohongshu'
  if (platformName.includes('视频号')) return 'platform-video'
  return ''
}

async function fetchContext() {
  loading.value = true
  try {
    const [projectData, topics, scripts] = await Promise.all([
      getProject(projectId()),
      listProjectTopics(projectId()),
      listTopicScripts(topicId()),
    ])
    project.value = projectData
    topic.value = topics.find((item) => item.id === topicId()) ?? null
    if (!topic.value) {
      ElMessage.error('选题不存在')
      return
    }
    platform.value = topic.value.platform
    if (scripts.length) {
      result.value = {
        script: scripts[0],
        generation_record_id: null,
        provider: 'saved',
        model: 'saved',
        usage: {},
        latency_ms: 0,
      }
    }
  } catch (error) {
    ElMessage.error('文案生成上下文加载失败')
  } finally {
    loading.value = false
  }
}

async function handleGenerate() {
  generating.value = true
  try {
    result.value = await generateScript(
      projectId(),
      topicId(),
      platform.value || null,
      scriptType.value,
      duration.value,
      goal.value,
    )
    ElMessage.success('文案已生成')
  } catch (error) {
    ElMessage.error(apiErrorMessage(error, '文案生成失败'))
  } finally {
    generating.value = false
  }
}

function apiErrorMessage(error: unknown, fallback: string) {
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detail === 'string' && detail.trim() ? detail : fallback
}

function scriptText() {
  if (!script.value) return ''
  return [
    `标题：${script.value.title}`,
    `开头钩子：${script.value.script_data.hook}`,
    `正文口播：${script.value.script_content}`,
    `镜头建议：${script.value.shot_suggestions.join('；')}`,
    `字幕重点：${script.value.script_data.subtitle_points.join('；')}`,
    `结尾转化：${script.value.conversion_script}`,
    `评论区引导：${script.value.script_data.comment_guidance}`,
    `私信引导：${script.value.script_data.private_message_guidance}`,
  ].join('\n\n')
}

async function copyScript() {
  if (!script.value) return
  try {
    await navigator.clipboard.writeText(scriptText())
    ElMessage.success('已复制文案')
  } catch (error) {
    ElMessage.error('复制失败，请手动复制页面内容')
  }
}

async function copyJson() {
  if (!script.value) return
  try {
    await navigator.clipboard.writeText(JSON.stringify(script.value, null, 2))
    ElMessage.success('已复制完整 JSON')
  } catch (error) {
    ElMessage.error('复制失败，请手动复制页面内容')
  }
}

onMounted(fetchContext)
</script>

<template>
  <section class="page-section">
    <div class="section-header">
      <div>
        <p class="eyebrow">Script Generation</p>
        <h1>{{ project?.project_name || '文案生成' }}</h1>
      </div>
      <div class="header-actions">
        <el-button @click="router.push(`/projects/${projectId()}/topics`)">返回选题页面</el-button>
        <el-button @click="router.push(`/projects/${projectId()}`)">返回项目详情</el-button>
        <el-button type="primary" :loading="generating" :disabled="!topic" @click="handleGenerate">
          生成文案
        </el-button>
      </div>
    </div>

    <el-skeleton v-if="loading" :rows="8" animated />
    <template v-else>
      <article v-if="topic" class="result-card wide topic-summary-card">
        <div class="topic-card-header">
          <div>
            <el-tag :class="['platform-tag', platformTagClass(topic.platform)]">
              {{ topic.platform }}
            </el-tag>
            <el-tag class="tag-item">{{ topic.content_type }}</el-tag>
            <el-tag class="tag-item" type="warning">{{ topic.goal }}</el-tag>
          </div>
          <span class="score-badge">{{ topic.score }}</span>
        </div>
        <h2>{{ topic.title }}</h2>
        <p>{{ topic.topic_data.user_pain_point }}</p>
        <p>{{ topic.topic_data.hook }}</p>
      </article>

      <div class="plan-controls">
        <el-form label-position="top" class="plan-control-form">
          <div class="script-control-grid">
            <el-form-item label="写法">
              <el-select v-model="scriptType" class="full-width">
                <el-option
                  v-for="item in scriptTypeOptions"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </el-select>
            </el-form-item>
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
            <el-form-item label="视频时长">
              <el-select v-model="duration" class="full-width">
                <el-option
                  v-for="item in durationOptions"
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
          </div>
        </el-form>
      </div>

      <div v-if="!script" class="empty-state">
        <h2>尚未生成文案</h2>
        <p>文案会基于当前已保存选题生成，不支持手动输入选题。</p>
      </div>

      <template v-else>
        <div class="result-toolbar">
          <div class="meta-text">
            Provider：{{ result?.provider }} / Model：{{ result?.model }} / 记录 ID：{{
              result?.generation_record_id || '已保存'
            }}
          </div>
          <div class="header-actions">
            <el-button @click="copyScript">复制文案</el-button>
            <el-button @click="copyJson">复制完整 JSON</el-button>
          </div>
        </div>

        <div class="script-result-grid">
          <article class="result-card wide">
            <h2>标题</h2>
            <p>{{ script.title }}</p>
          </article>
          <article class="result-card wide">
            <h2>开头钩子</h2>
            <p>{{ script.script_data.hook }}</p>
          </article>
          <article class="result-card wide">
            <h2>正文口播</h2>
            <pre>{{ script.script_content }}</pre>
          </article>
          <article class="result-card">
            <h2>镜头建议</h2>
            <ul>
              <li v-for="item in script.shot_suggestions" :key="item">{{ item }}</li>
            </ul>
          </article>
          <article class="result-card">
            <h2>字幕重点</h2>
            <ul>
              <li v-for="item in script.script_data.subtitle_points" :key="item">{{ item }}</li>
            </ul>
          </article>
          <article class="result-card wide">
            <h2>结尾转化</h2>
            <p>{{ script.conversion_script }}</p>
          </article>
          <article class="result-card">
            <h2>评论区引导</h2>
            <p>{{ script.script_data.comment_guidance }}</p>
          </article>
          <article class="result-card">
            <h2>私信引导</h2>
            <p>{{ script.script_data.private_message_guidance }}</p>
          </article>
        </div>
      </template>
    </template>
  </section>
</template>
