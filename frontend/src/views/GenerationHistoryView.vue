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
import {
  groupGenerationRecords,
  type GenerationHistoryRow,
} from '../utils/generationHistoryGrouping'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const detailLoadingId = ref<number | null>(null)
const records = ref<GenerationRecord[]>([])
const detailById = ref<Record<number, GenerationRecord>>({})
const moduleName = ref('')
const projectIdInput = ref(route.params.id ? String(route.params.id) : '')
const displayRecords = computed(() => groupGenerationRecords(records.value))
const groupedRecordCount = computed(
  () => displayRecords.value.filter((record) => record.is_grouped).length,
)
const moduleTypeCount = computed(
  () => new Set(displayRecords.value.map((record) => record.module_name)).size,
)

const moduleOptions = [
  { label: '全部模块', value: '' },
  { label: '账号包装', value: 'account_package' },
  { label: '执行计划', value: 'execution_plan' },
  { label: '选题生成', value: 'topics' },
  { label: '文案生成', value: 'script' },
]

const pageTitle = computed(() =>
  route.params.id ? `人设 ${route.params.id} 生成记录` : '生成记录',
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
    ElMessage.error('生成记录加载失败')
  } finally {
    loading.value = false
  }
}

async function loadDetail(row: GenerationHistoryRow) {
  if (row.is_grouped) return
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

function moduleTagClass(module: string) {
  if (module === 'account_package') return 'module-purple'
  if (module === 'execution_plan') return 'module-mint'
  if (module === 'topics') return 'module-orange'
  if (module === 'script') return 'module-blue'
  return 'module-gray'
}

function formatTime(value: string) {
  return new Date(value).toLocaleString()
}

function formatCompactTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  const month = date.getMonth() + 1
  const day = date.getDate()
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${month}/${day} ${hours}:${minutes}`
}

function formatLatencySeconds(value: number | null | undefined) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '-'
  const seconds = value / 1000
  const formatted = seconds >= 10 ? seconds.toFixed(0) : seconds.toFixed(1)
  return `${formatted} 秒`
}

function compactText(value: string | number | null | undefined, maxLength = 14) {
  const text = value == null || value === '' ? '-' : String(value)
  return text.length > maxLength ? `${text.slice(0, maxLength - 1)}…` : text
}

function formatProvider(value: string | null | undefined) {
  if (value === 'openai_compatible') return 'OpenAI'
  if (value === 'dataeye') return 'DataEye'
  if (value === 'moyu') return 'Moyu'
  return compactText(value, 12)
}

function formatModel(value: string | null | undefined) {
  return compactText(value, 14)
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

function formatAverageTopicTime(row: GenerationHistoryRow) {
  return formatLatencySeconds(row.avg_topic_latency_ms)
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
        <el-button @click="backToProject">返回人设详情</el-button>
        <el-button type="primary" :loading="loading" @click="fetchRecords">刷新</el-button>
      </div>
    </div>

    <div class="overview-strip">
      <div class="overview-item tone-mint">
        <span>记录数</span>
        <strong>{{ displayRecords.length }}</strong>
      </div>
      <div class="overview-item tone-purple">
        <span>模块数</span>
        <strong>{{ moduleTypeCount }}</strong>
      </div>
      <div class="overview-item tone-orange">
        <span>批量记录</span>
        <strong>{{ groupedRecordCount }}</strong>
      </div>
    </div>

    <div class="plan-controls">
      <el-form label-position="top" class="plan-control-form">
        <div class="history-control-grid">
          <el-form-item label="人设 ID">
            <el-input v-model="projectIdInput" clearable placeholder="全部人设" />
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

    <div class="table-panel">
      <el-table
        v-loading="loading"
        :data="displayRecords"
        border
        class="plan-table history-table"
        size="small"
        row-key="id"
        @expand-change="loadDetail"
      >
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="history-detail">
              <div class="result-toolbar">
                <div class="meta-text">
                  记录 ID：{{ row.id }} / Prompt：{{ row.prompt_version || '无' }} / 耗时：{{
                    formatLatencySeconds(row.latency_ms)
                  }}
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
                  <h2>耗时</h2>
                  <p>{{ formatLatencySeconds((detailById[row.id] || row).latency_ms) }}</p>
                </article>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="id" label="ID" width="58" />
        <el-table-column label="模块" width="104">
          <template #default="{ row }">
            <el-tag :class="['module-tag', moduleTagClass(row.module_name)]">
              {{ formatModuleName(row.module_name) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="数量" width="58">
          <template #default="{ row }">
            <span class="count-pill">{{ row.topic_count || 1 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="project_id" label="人设" width="58" />
        <el-table-column label="供应商" width="96" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="history-cell-text" :title="row.model_provider">
              {{ formatProvider(row.model_provider) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="模型" width="116" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="history-cell-text" :title="row.model_name">
              {{ formatModel(row.model_name) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="耗时" width="82">
          <template #default="{ row }">{{ compactText(formatLatencySeconds(row.latency_ms), 10) }}</template>
        </el-table-column>
        <el-table-column label="均耗时" width="82">
          <template #default="{ row }">{{ formatAverageTopicTime(row) }}</template>
        </el-table-column>
        <el-table-column label="时间" width="112">
          <template #default="{ row }">
            <span class="history-cell-text" :title="formatTime(row.created_at)">
              {{ formatCompactTime(row.created_at) }}
            </span>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </section>
</template>
