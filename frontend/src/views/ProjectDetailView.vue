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

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const project = ref<Project | null>(null)

const platformOptions = ['抖音', '视频号', '快手', '小红书']
const stageOptions = ['起步期', '冷启动', '稳定更新', '转化优化']

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
    project.value = await updateProject(projectId(), form)
    ElMessage.success('项目已更新')
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
        <el-button
          type="primary"
          :disabled="!project"
          @click="router.push(`/projects/${projectId()}/account-package`)"
        >
          账号包装
        </el-button>
        <el-button
          type="success"
          :disabled="!project"
          @click="router.push(`/projects/${projectId()}/execution-plan`)"
        >
          执行计划
        </el-button>
        <el-button
          type="warning"
          :disabled="!project"
          @click="router.push(`/projects/${projectId()}/topics`)"
        >
          选题生成
        </el-button>
        <el-button
          :disabled="!project"
          @click="router.push(`/projects/${projectId()}/history`)"
        >
          生成历史
        </el-button>
      </div>
    </div>

    <el-skeleton v-if="loading" :rows="8" animated />
    <el-form v-else label-position="top" class="project-form" @submit.prevent="handleSave">
      <el-form-item label="项目名称" required>
        <el-input v-model="form.project_name" />
      </el-form-item>
      <div class="form-grid">
        <el-form-item label="行业" required>
          <el-input v-model="form.industry" />
        </el-form-item>
        <el-form-item label="细分行业">
          <el-input v-model="form.sub_industry" />
        </el-form-item>
      </div>
      <el-form-item label="产品" required>
        <el-input v-model="form.product" />
      </el-form-item>
      <el-form-item label="个人简介" required>
        <el-input v-model="form.personal_intro" type="textarea" :rows="4" />
      </el-form-item>
      <el-form-item label="目标客户" required>
        <el-input v-model="form.target_audience" type="textarea" :rows="3" />
      </el-form-item>
      <el-form-item label="平台" required>
        <el-checkbox-group v-model="form.platforms">
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
          <el-button type="primary" native-type="submit" :loading="saving">保存修改</el-button>
        </div>
      </div>
    </el-form>
  </section>
</template>
