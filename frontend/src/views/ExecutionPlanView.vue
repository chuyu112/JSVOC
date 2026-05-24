<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import {
  type ExecutionPlanGenerateResponse,
  type ExecutionPlanResult,
} from '../api/executionPlan'
import { getProject, type Project } from '../api/projects'
import {
  executionPlanResponseFromStrategyBundle,
  generateStrategyBundle,
} from '../api/strategyBundle'

const route = useRoute()
const router = useRouter()
const loadingProject = ref(false)
const generating = ref(false)
const project = ref<Project | null>(null)
const result = ref<ExecutionPlanGenerateResponse | null>(null)
const cycle = ref('30天')
const dailyTime = ref('2小时')

const cycleOptions = ['30天']
const dailyTimeOptions = ['1小时', '2小时', '3小时', '半天']

const executionPlan = computed<ExecutionPlanResult | null>(
  () => result.value?.execution_plan ?? null,
)
const weeklyPlanCount = computed(() => executionPlan.value?.weekly_plan.length ?? 0)
const dailyPlanCount = computed(() => executionPlan.value?.daily_plan.length ?? 0)
const reviewMetricCount = computed(
  () =>
    executionPlan.value?.daily_plan.reduce(
      (total, day) => total + day.review_metrics.length,
      0,
    ) ?? 0,
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
    const bundle = await generateStrategyBundle(projectId(), cycle.value, dailyTime.value)
    result.value = executionPlanResponseFromStrategyBundle(bundle)
    ElMessage.success('账号包装和执行计划已生成')
  } catch (error) {
    ElMessage.error('执行计划生成失败')
  } finally {
    generating.value = false
  }
}

async function copyResult() {
  if (!result.value) return

  const text = JSON.stringify(result.value.execution_plan, null, 2)
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('已复制执行计划')
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
        <p class="eyebrow">Execution Plan</p>
        <h1>{{ project?.project_name || '执行计划生成' }}</h1>
      </div>
      <div class="header-actions">
        <el-button @click="router.push(`/projects/${projectId()}`)">返回项目详情</el-button>
        <el-button type="primary" :loading="generating" @click="handleGenerate">
          生成执行计划
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
          <div class="form-grid">
            <el-form-item label="执行周期">
              <el-select v-model="cycle" class="full-width">
                <el-option v-for="item in cycleOptions" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
            <el-form-item label="每天可投入时间">
              <el-select v-model="dailyTime" class="full-width">
                <el-option
                  v-for="item in dailyTimeOptions"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </el-select>
            </el-form-item>
          </div>
        </el-form>
      </div>

      <div v-if="!executionPlan" class="empty-state">
        <h2>尚未生成执行计划</h2>
        <p>选择周期和每天可投入时间后生成 30 天执行节奏、每日选题方向和拍摄任务。</p>
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

        <div class="overview-strip result-metrics">
          <div class="overview-item tone-mint">
            <span>周期</span>
            <strong>{{ executionPlan.cycle }}</strong>
          </div>
          <div class="overview-item tone-purple">
            <span>周计划</span>
            <strong>{{ weeklyPlanCount }}</strong>
          </div>
          <div class="overview-item tone-blue">
            <span>日任务</span>
            <strong>{{ dailyPlanCount }}</strong>
          </div>
          <div class="overview-item tone-orange">
            <span>复盘指标</span>
            <strong>{{ reviewMetricCount }}</strong>
          </div>
        </div>

        <div class="result-grid">
          <article class="result-card wide">
            <h2>每周计划</h2>
            <el-table :data="executionPlan.weekly_plan" border class="plan-table">
              <el-table-column prop="week" label="周" width="72" />
              <el-table-column prop="goal" label="每周目标" min-width="220" />
              <el-table-column prop="focus" label="重点方向" min-width="220" />
              <el-table-column label="关键任务" min-width="260">
                <template #default="{ row }">
                  <ul class="compact-list">
                    <li v-for="item in row.key_tasks" :key="item">{{ item }}</li>
                  </ul>
                </template>
              </el-table-column>
            </el-table>
          </article>

          <article class="result-card wide">
            <h2>每日计划</h2>
            <el-table :data="executionPlan.daily_plan" border class="plan-table">
              <el-table-column prop="day" label="天" width="72" />
              <el-table-column prop="task" label="每日任务" min-width="240" />
              <el-table-column prop="topic" label="每日选题方向" min-width="240" />
              <el-table-column prop="shooting_task" label="拍摄任务" min-width="280" />
              <el-table-column label="复盘指标" min-width="220">
                <template #default="{ row }">
                  <el-tag
                    v-for="item in row.review_metrics"
                    :key="item"
                    class="tag-item"
                    type="success"
                  >
                    {{ item }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </article>
        </div>
      </template>
    </template>
  </section>
</template>
