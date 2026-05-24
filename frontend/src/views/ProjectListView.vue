<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { deleteProject, listProjects, type Project } from '../api/projects'

const router = useRouter()
const loading = ref(false)
const projects = ref<Project[]>([])

async function fetchProjects() {
  loading.value = true
  try {
    projects.value = await listProjects()
  } catch (error) {
    ElMessage.error('项目列表加载失败')
  } finally {
    loading.value = false
  }
}

async function handleDelete(project: Project) {
  try {
    await ElMessageBox.confirm(`确认删除项目「${project.project_name}」？`, '删除项目', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteProject(project.id)
    ElMessage.success('项目已删除')
    await fetchProjects()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(fetchProjects)
</script>

<template>
  <section class="page-section">
    <div class="section-header">
      <div>
        <p class="eyebrow">Projects</p>
        <h1>项目档案</h1>
      </div>
      <el-button type="primary" @click="router.push('/projects/new')">新建项目</el-button>
    </div>

    <el-table v-loading="loading" :data="projects" empty-text="暂无项目，先创建一个项目档案">
      <el-table-column prop="project_name" label="项目名称" min-width="160" />
      <el-table-column prop="industry" label="行业" width="120" />
      <el-table-column prop="product" label="产品" min-width="140" />
      <el-table-column prop="current_stage" label="阶段" width="120" />
      <el-table-column label="平台" min-width="180">
        <template #default="{ row }">
          <el-tag v-for="platform in row.platforms" :key="platform" class="tag-item" size="small">
            {{ platform }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="190" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="router.push(`/projects/${row.id}`)">
            查看
          </el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </section>
</template>
