<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import {
  generateTopics,
  listProjectTopics,
  type Topic,
  type TopicGenerateResponse,
} from '../api/topics'
import { getProject, type Project } from '../api/projects'

const route = useRoute()
const router = useRouter()
const loadingProject = ref(false)
const loadingTopics = ref(false)
const generating = ref(false)
const project = ref<Project | null>(null)
const result = ref<TopicGenerateResponse | null>(null)
const savedTopics = ref<Topic[]>([])
const platform = ref('抖音')
const goal = ref('获客')
const count = ref(20)

const platformOptions = ['抖音', '视频号', '快手', '小红书']
const goalOptions = ['获客', '涨粉', '信任建立', '成交转化']
const countOptions = [10, 20, 30, 50]

const topics = computed(() => result.value?.topics ?? savedTopics.value)

function projectId() {
  return Number(route.params.id)
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
  try {
    result.value = await generateTopics(projectId(), platform.value, goal.value, count.value)
    savedTopics.value = result.value.topics
    ElMessage.success('选题已生成')
  } catch (error) {
    ElMessage.error('选题生成失败')
  } finally {
    generating.value = false
  }
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
    `评分：${topic.score}`,
  ].join('\n')
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
              <el-select v-model="platform" class="full-width">
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
          </div>
        </el-form>
      </div>

      <div v-if="!topics.length && !loadingTopics" class="empty-state">
        <h2>尚未生成选题</h2>
        <p>选择平台、目标和数量后生成可直接拍摄的短视频选题。</p>
      </div>

      <template v-else>
        <div class="result-toolbar">
          <div class="meta-text">
            <template v-if="result">
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
                <el-tag type="success">{{ topic.platform }}</el-tag>
                <el-tag class="tag-item">{{ topic.content_type }}</el-tag>
                <el-tag class="tag-item" type="warning">{{ topic.goal }}</el-tag>
              </div>
              <strong>{{ topic.score }}</strong>
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
            </dl>
            <div class="topic-actions">
              <el-button size="small" @click="copyTopic(topic)">复制选题</el-button>
              <el-button size="small" type="primary" plain @click="openScriptPage(topic)">
                生成文案
              </el-button>
            </div>
          </article>
        </div>
      </template>
    </template>
  </section>
</template>
