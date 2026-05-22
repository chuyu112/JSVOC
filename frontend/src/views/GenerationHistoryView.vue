<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import {
  formatModuleName,
  getGenerationRecord,
  listGenerationRecords,
  type GenerationRecord,
} from '../api/generationRecords'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const detailLoadingId = ref<number | null>(null)
const records = ref<GenerationRecord[]>([])
const detailById = ref<Record<number, GenerationRecord>>({})
const moduleName = ref('')
const projectIdInput = ref(route.params.id ? String(route.params.id) : '')

const moduleOptions = [
  { label: '全部模块', value: '' },
  { label: '账号包装', value: 'account_package' },
  { label: '执行计划', value: 'execution_plan' },
  { label: '选题生成', value: 'topics' },
  { label: '文案生成', value: 'script' },
  { label: '聊天', value: 'chat' },
  { label: '生图', value: 'image_generation' },
]

const pageTitle = computed(() =>
  route.params.id ? `项目 ${route.params.id} 生成历史` : '生成历史',
)

function projectId() {
  const value = Number(projectIdInput.value)
  return Number.isInteger(value) && value > 0 ? value : null
}

async function fetchRecords() {
  loading.value = true
  try {
    records.value = await listGenerationRecords({
      project_id: projectId(),
      module_name: moduleName.value || null,
      limit: 50,
      offset: 0,
    })
  } catch (error) {
    ElMessage.error('生成历史加载失败')
  } finally {
    loading.value = false
  }
}

async function loadDetail(row: GenerationRecord) {
  if (detailById.value[row.id]) return

  detailLoadingId.value = row.id
  try {
    detailById.value[row.id] = await getGenerationRecord(row.id)
  } catch (error) {
    ElMessage.error('生成记录详情加载失败')
  } finally {
    detailLoadingId.value = null
  }
}

function formatJson(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2)
}

function formatTime(value: string) {
  return new Date(value).toLocaleString()
}

async function copyText(text: string, message: string) {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success(message)
  } catch (error) {
    ElMessage.error('复制失败，请手动复制页面内容')
  }
}

function copyInput(record: GenerationRecord) {
  copyText(formatJson(record.input_data), '已复制 input_data')
}

function copyOutput(record: GenerationRecord) {
  copyText(formatJson(record.output_data), '已复制 output_data')
}

function copyRecord(record: GenerationRecord) {
  copyText(formatJson(record), '已复制完整 JSON')
}

function backToProject() {
  const id = projectId()
  if (id) {
    router.push(`/projects/${id}`)
  } else {
    router.push('/projects')
  }
}

onMounted(fetchRecords)
</script>

<template>
  <section class="page-section">
    <div class="section-header">
      <div>
        <p class="eyebrow">Generation History</p>
        <h1>{{ pageTitle }}</h1>
      </div>
      <div class="header-actions">
        <el-button @click="backToProject">返回项目详情</el-button>
        <el-button type="primary" :loading="loading" @click="fetchRecords">刷新</el-button>
      </div>
    </div>

    <div class="plan-controls">
      <el-form label-position="top" class="plan-control-form">
        <div class="history-control-grid">
          <el-form-item label="项目 ID">
            <el-input v-model="projectIdInput" clearable placeholder="全部项目" />
          </el-form-item>
          <el-form-item label="模块类型">
            <el-select v-model="moduleName" class="full-width">
              <el-option
                v-for="item in moduleOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </div>
      </el-form>
    </div>

    <el-table
      v-loading="loading"
      :data="records"
      border
      class="plan-table"
      row-key="id"
      @expand-change="loadDetail"
    >
      <el-table-column type="expand">
        <template #default="{ row }">
          <div class="history-detail">
            <div class="result-toolbar">
              <div class="meta-text">
                记录 ID：{{ row.id }} / Prompt：{{ row.prompt_version || '无' }} / 耗时：{{
                  row.latency_ms ?? 0
                }} ms
              </div>
              <div class="header-actions">
                <el-button size="small" @click="copyInput(detailById[row.id] || row)">
                  复制 input_data
                </el-button>
                <el-button size="small" @click="copyOutput(detailById[row.id] || row)">
                  复制 output_data
                </el-button>
                <el-button size="small" @click="copyRecord(detailById[row.id] || row)">
                  复制完整 JSON
                </el-button>
              </div>
            </div>
            <el-skeleton v-if="detailLoadingId === row.id" :rows="4" animated />
            <div v-else class="history-detail-grid">
              <article class="result-card">
                <h2>input_data</h2>
                <pre>{{ formatJson((detailById[row.id] || row).input_data) }}</pre>
              </article>
              <article class="result-card">
                <h2>output_data</h2>
                <pre>{{ formatJson((detailById[row.id] || row).output_data) }}</pre>
              </article>
              <article class="result-card">
                <h2>token_usage</h2>
                <pre>{{ formatJson((detailById[row.id] || row).token_usage) }}</pre>
              </article>
              <article class="result-card">
                <h2>latency_ms</h2>
                <p>{{ (detailById[row.id] || row).latency_ms ?? 0 }}</p>
              </article>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column label="模块" min-width="140">
        <template #default="{ row }">{{ formatModuleName(row.module_name) }}</template>
      </el-table-column>
      <el-table-column prop="project_id" label="项目 ID" width="100" />
      <el-table-column prop="model_provider" label="模型供应商" min-width="140" />
      <el-table-column prop="model_name" label="模型名称" min-width="160" />
      <el-table-column label="耗时" width="100">
        <template #default="{ row }">{{ row.latency_ms ?? 0 }} ms</template>
      </el-table-column>
      <el-table-column label="创建时间" min-width="190">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
    </el-table>
  </section>
</template>
