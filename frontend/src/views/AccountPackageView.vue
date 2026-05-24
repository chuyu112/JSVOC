<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import {
  generateAccountPackage,
  type AccountPackageGenerateResponse,
  type AccountPackageResult,
} from '../api/accountPackage'
import { getProject, type Project } from '../api/projects'

const route = useRoute()
const router = useRouter()
const loadingProject = ref(false)
const generating = ref(false)
const project = ref<Project | null>(null)
const result = ref<AccountPackageGenerateResponse | null>(null)

const accountPackage = computed<AccountPackageResult | null>(
  () => result.value?.account_package ?? null,
)

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

async function handleGenerate() {
  generating.value = true
  try {
    result.value = await generateAccountPackage(projectId())
    ElMessage.success('账号包装方案已生成')
  } catch (error) {
    ElMessage.error('账号包装生成失败')
  } finally {
    generating.value = false
  }
}

async function copyResult() {
  if (!result.value) return

  const text = JSON.stringify(result.value.account_package, null, 2)
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制账号包装结果')
  } catch (error) {
    ElMessage.error('复制失败，请手动复制页面内容')
  }
}

function formatValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.join('、')
  }
  if (value && typeof value === 'object') {
    return Object.entries(value as Record<string, unknown>)
      .map(([key, item]) => `${key}：${formatValue(item)}`)
      .join('\n')
  }
  return String(value ?? '')
}

onMounted(fetchProject)
</script>

<template>
  <section class="page-section">
    <div class="section-header">
      <div>
        <p class="eyebrow">Account Package</p>
        <h1>{{ project?.project_name || '账号包装方案' }}</h1>
      </div>
      <div class="header-actions">
        <el-button @click="router.push(`/projects/${projectId()}`)">返回项目详情</el-button>
        <el-button type="primary" :loading="generating" @click="handleGenerate">
          生成账号包装
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

      <div v-if="!accountPackage" class="empty-state">
        <h2>尚未生成账号包装方案</h2>
        <p>点击右上方按钮，会基于当前项目档案生成账号定位、人设、栏目和平台策略。</p>
      </div>

      <template v-else>
        <div class="result-toolbar">
          <div class="meta-text">
            Provider：{{ result?.provider }} / Model：{{ result?.model }} / 记录 ID：{{
              result?.generation_record_id
            }}
          </div>
          <el-button @click="copyResult">复制结果</el-button>
        </div>

        <div class="result-grid">
          <article class="result-card wide">
            <h2>账号核心定位</h2>
            <p>{{ accountPackage.account_positioning }}</p>
          </article>
          <article class="result-card wide">
            <h2>人设包装</h2>
            <p>{{ accountPackage.persona }}</p>
          </article>
          <article class="result-card">
            <h2>目标用户画像</h2>
            <pre>{{ formatValue(accountPackage.target_user_profile) }}</pre>
          </article>
          <article class="result-card">
            <h2>账号名称建议</h2>
            <el-tag
              v-for="name in accountPackage.account_names"
              :key="name"
              class="tag-item"
              type="success"
            >
              {{ name }}
            </el-tag>
          </article>
          <article class="result-card">
            <h2>各平台简介</h2>
            <pre>{{ formatValue(accountPackage.bios) }}</pre>
          </article>
          <article class="result-card">
            <h2>内容栏目</h2>
            <ul>
              <li v-for="item in accountPackage.content_columns" :key="item">{{ item }}</li>
            </ul>
          </article>
          <article class="result-card">
            <h2>信任设计</h2>
            <ul>
              <li v-for="item in accountPackage.trust_design" :key="item">{{ item }}</li>
            </ul>
          </article>
          <article class="result-card">
            <h2>转化路径</h2>
            <ul>
              <li v-for="item in accountPackage.conversion_path" :key="item">{{ item }}</li>
            </ul>
          </article>
          <article class="result-card wide">
            <h2>平台策略</h2>
            <pre>{{ formatValue(accountPackage.platform_strategies) }}</pre>
          </article>
        </div>
      </template>
    </template>
  </section>
</template>
