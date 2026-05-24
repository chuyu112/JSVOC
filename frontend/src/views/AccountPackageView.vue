<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import {
  type AccountPackageGenerateResponse,
} from '../api/accountPackage'
import { listGenerationRecords } from '../api/generationRecords'
import { getProject, type Project } from '../api/projects'
import {
  accountPackageResponseFromStrategyBundle,
  generateStrategyBundle,
} from '../api/strategyBundle'
import AccountPackageBento from '../components/AccountPackageBento.vue'
import { accountPackageResponseFromGenerationRecord } from '../utils/accountPackageHydration'

const route = useRoute()
const router = useRouter()
const loadingProject = ref(false)
const loadingLatest = ref(false)
const generating = ref(false)
const project = ref<Project | null>(null)
const result = ref<AccountPackageGenerateResponse | null>(null)

function projectId() {
  return Number(route.params.id)
}

async function fetchProject() {
  loadingProject.value = true
  try {
    project.value = await getProject(projectId())
    await fetchLatestAccountPackage()
  } catch (error) {
    ElMessage.error('项目信息加载失败')
  } finally {
    loadingProject.value = false
  }
}

async function fetchLatestAccountPackage() {
  loadingLatest.value = true
  try {
    const records = await listGenerationRecords({
      project_id: projectId(),
      limit: 10,
      offset: 0,
    })
    const latestRecord = records.find((record) =>
      ['account_package', 'strategy_bundle'].includes(record.module_name),
    )
    result.value = latestRecord ? accountPackageResponseFromGenerationRecord(latestRecord) : null
  } catch (error) {
    result.value = null
  } finally {
    loadingLatest.value = false
  }
}

async function handleGenerate() {
  generating.value = true
  try {
    const bundle = await generateStrategyBundle(projectId())
    result.value = accountPackageResponseFromStrategyBundle(bundle)
    ElMessage.success('账号包装和执行计划已生成')
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

      <div v-if="!result && !generating && !loadingLatest" class="empty-state premium-empty">
        <h2>尚未生成账号包装方案</h2>
        <p>点击右上方按钮，会基于当前项目档案生成一份 Bento 风格的账号策略报告。</p>
      </div>

      <template v-else-if="result">
        <div class="result-toolbar">
          <div class="meta-text">
            Provider：{{ result?.provider }} / Model：{{ result?.model }} / 记录 ID：{{
              result?.generation_record_id
            }} / 耗时：{{ result?.latency_ms }}ms
          </div>
          <el-button @click="copyResult">复制结果</el-button>
        </div>
        <AccountPackageBento :result="result" />
      </template>

      <AccountPackageBento v-else :result="null" :loading="true" />
    </template>
  </section>
</template>

<style scoped>
.premium-empty {
  border-color: rgba(5, 150, 105, 0.14);
  background:
    radial-gradient(circle at 50% 0%, rgba(16, 185, 129, 0.12), transparent 34%),
    rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(20px) saturate(1.2);
}
</style>
