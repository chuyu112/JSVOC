<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { getProject, type Project } from '../api/projects'

const route = useRoute()
const router = useRouter()
const project = ref<Project | null>(null)
const loading = ref(false)

const workflowMap = {
  image: {
    eyebrow: 'Image Generation',
    title: '图片生成',
    summary: '用于把选题、脚本或产品卖点转成封面图、详情图、场景图。',
    steps: ['选择选题或文案', '生成图片提示词', '输出图片方案'],
  },
  video: {
    eyebrow: 'Video Generation',
    title: '视频生成',
    summary: '用于把文案、镜头建议和素材要求转成短视频生成任务。',
    steps: ['选择文案', '配置视频比例和风格', '生成视频任务'],
  },
  publish: {
    eyebrow: 'Content Publish',
    title: '内容发布',
    summary: '用于整理待发布内容、平台差异文案和发布状态。',
    steps: ['选择内容资产', '配置平台发布信息', '记录发布状态'],
  },
} as const

type WorkflowKey = keyof typeof workflowMap

const workflow = computed(() => {
  const key = String(route.meta.workflow || 'image') as WorkflowKey
  return workflowMap[key] ?? workflowMap.image
})

function projectId() {
  return Number(route.params.id)
}

async function fetchProject() {
  loading.value = true
  try {
    project.value = await getProject(projectId())
  } catch (error) {
    ElMessage.error('项目上下文加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(fetchProject)
</script>

<template>
  <section class="page-section narrow">
    <div class="section-header">
      <div>
        <p class="eyebrow">{{ workflow.eyebrow }}</p>
        <h1>{{ project?.project_name || workflow.title }}</h1>
      </div>
      <div class="header-actions action-ribbon">
        <el-button @click="router.push(`/projects/${projectId()}`)">返回项目</el-button>
        <el-button @click="router.push(`/projects/${projectId()}/topics`)">选题生成</el-button>
      </div>
    </div>

    <el-skeleton v-if="loading" :rows="6" animated />
    <template v-else>
      <div class="workflow-placeholder">
        <p class="eyebrow">{{ workflow.title }}</p>
        <h2>{{ workflow.summary }}</h2>
        <div class="workflow-step-grid">
          <div v-for="(step, index) in workflow.steps" :key="step" class="workflow-step-card">
            <span>{{ index + 1 }}</span>
            <strong>{{ step }}</strong>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>
