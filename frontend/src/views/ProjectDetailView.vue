<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import {
  deleteProject,
  getProject,
  updateProject,
  type Project,
  type ProjectPayload,
} from '../api/projects'
import FieldChips from '../components/FieldChips.vue'
import ProductMultiSelect from '../components/ProductMultiSelect.vue'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const project = ref<Project | null>(null)

const platformOptions = ['抖音', '视频号', '快手', '小红书']
const stageOptions = ['起步期', '冷启动', '稳定更新', '转化优化']
const workflowGroups = [
  {
    label: '策略',
    items: [
      { label: '账号包装', path: 'account-package' },
      { label: '执行计划', path: 'execution-plan' },
    ],
  },
  {
    label: '创作',
    items: [
      { label: '选题生成', path: 'topics' },
      { label: '文案生成', path: 'topics' },
    ],
  },
  {
    label: '媒体',
    items: [
      { label: '图片生成', path: 'images' },
      { label: '视频生成', path: 'videos' },
    ],
  },
  {
    label: '其他',
    items: [
      { label: '内容发布', path: 'publish' },
    ],
  },
]

const form = reactive<ProjectPayload>({
  project_name: '',
  industry: '',
  sub_industry: '',
  product: '',
  personal_intro: '',
  target_audience: '',
  platforms: [],
  current_stage: '起步期',
})

function projectId() {
  return Number(route.params.id)
}

function workflowPath(path: string) {
  return `/projects/${projectId()}/${path}`
}

function platformTagClass(platform: string) {
  if (platform.includes('抖音')) return 'platform-douyin'
  if (platform.includes('快手')) return 'platform-kuaishou'
  if (platform.includes('小红书')) return 'platform-xiaohongshu'
  if (platform.includes('视频号')) return 'platform-video'
  return ''
}

async function fetchProject() {
  loading.value = true
  try {
    project.value = await getProject(projectId())
    Object.assign(form, {
      project_name: project.value.project_name,
      industry: project.value.industry,
      sub_industry: project.value.sub_industry,
      product: project.value.product,
      personal_intro: project.value.personal_intro,
      target_audience: project.value.target_audience,
      platforms: [...project.value.platforms],
      current_stage: project.value.current_stage,
    })
  } catch (error) {
    ElMessage.error('项目详情加载失败')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    const savedProject = await updateProject(projectId(), form)
    project.value = savedProject
    ElMessage.success('项目已保存')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete() {
  if (!project.value) return

  try {
    await ElMessageBox.confirm(`确认删除项目「${project.value.project_name}」？`, '删除项目', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteProject(project.value.id)
    ElMessage.success('项目已删除')
    await router.push('/projects')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(fetchProject)
</script>

<template>
  <section class="page-section narrow">
    <div class="section-header">
      <div>
        <p class="eyebrow">Project Detail</p>
        <h1>{{ project?.project_name || '项目详情' }}</h1>
      </div>
      <div class="header-actions">
        <el-button @click="router.push('/projects')">返回列表</el-button>
      </div>
    </div>

    <nav class="project-workflow-nav" aria-label="项目工作流导航">
      <section v-for="group in workflowGroups" :key="group.label" class="workflow-nav-group">
        <h2>{{ group.label }}</h2>
        <div class="workflow-nav-items">
          <button
            v-for="item in group.items"
            :key="`${group.label}-${item.label}`"
            class="workflow-nav-button"
            type="button"
            :disabled="!project"
            @click="router.push(workflowPath(item.path))"
          >
            {{ item.label }}
          </button>
        </div>
      </section>
    </nav>

    <el-skeleton v-if="loading" :rows="8" animated />
    <template v-else>
      <div v-if="project" class="project-brief field-summary-grid">
        <FieldChips label="行业" :value="project.industry" tone="industry" />
        <FieldChips label="细分行业" :value="project.sub_industry" tone="subIndustry" />
        <FieldChips label="产品" :value="project.product" tone="product" />
        <FieldChips label="目标客户" :value="project.target_audience" tone="customer" />
        <FieldChips label="阶段" :items="[project.current_stage]" tone="stage" />
        <div class="tone-blue project-platform-panel">
          <span>平台</span>
          <div class="platform-pill-row">
            <el-tag
              v-for="platform in project.platforms"
              :key="platform"
              :class="['platform-tag', platformTagClass(platform)]"
            >
              {{ platform }}
            </el-tag>
            <strong v-if="!project.platforms.length">未选择</strong>
          </div>
        </div>
      </div>
      <el-form label-position="top" class="project-form" @submit.prevent="handleSave">
        <div class="form-kicker">
          <span>档案编辑</span>
          <span>策略上下文</span>
          <span>当前项目</span>
        </div>
        <el-form-item label="项目名称" required>
          <el-input v-model="form.project_name" />
        </el-form-item>
      <div class="form-grid">
        <el-form-item label="行业" class="field-form-item field-form-industry" required>
          <el-input v-model="form.industry" />
        </el-form-item>
        <el-form-item label="细分行业" class="field-form-item field-form-sub-industry">
          <el-input v-model="form.sub_industry" />
        </el-form-item>
      </div>
      <el-form-item label="产品" class="field-form-item field-form-product" required>
        <ProductMultiSelect v-model="form.product" />
      </el-form-item>
      <el-form-item label="个人简介" class="field-form-item field-form-profile" required>
        <el-input v-model="form.personal_intro" type="textarea" :rows="4" />
      </el-form-item>
      <el-form-item label="目标客户" class="field-form-item field-form-customer" required>
        <el-input v-model="form.target_audience" type="textarea" :rows="3" />
        <div class="field-template-row">
          <span class="field-template-chip field-template-gender">男女</span>
          <span class="field-template-chip field-template-customer">客户类型</span>
          <span class="field-template-chip field-template-city">一线/二线</span>
          <span class="field-template-chip field-template-interest">兴趣</span>
        </div>
      </el-form-item>
      <el-form-item label="平台" required>
        <el-checkbox-group v-model="form.platforms" class="creative-checks">
          <el-checkbox v-for="platform in platformOptions" :key="platform" :label="platform" />
        </el-checkbox-group>
      </el-form-item>
      <el-form-item label="当前阶段" required>
        <el-select v-model="form.current_stage" class="full-width">
          <el-option v-for="stage in stageOptions" :key="stage" :label="stage" :value="stage" />
        </el-select>
      </el-form-item>
      <div class="form-actions between">
        <el-button type="danger" plain @click="handleDelete">删除项目</el-button>
        <div>
          <el-button @click="fetchProject">重置</el-button>
          <el-button type="primary" native-type="submit" :loading="saving">保存项目</el-button>
        </div>
      </div>
      </el-form>
    </template>
  </section>
</template>
