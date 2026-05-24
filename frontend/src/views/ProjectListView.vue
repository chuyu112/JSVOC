<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import gsap from 'gsap'

import { deleteProject, listProjects, type Project } from '../api/projects'
import FieldChips from '../components/FieldChips.vue'

const router = useRouter()
const loading = ref(false)
const projects = ref<Project[]>([])
const listRef = ref<HTMLElement | null>(null)
const overviewRef = ref<HTMLElement | null>(null)

const projectCount = computed(() => projects.value.length)
const platformCount = computed(
  () => new Set(projects.value.flatMap((project) => project.platforms)).size,
)
const activeStageCount = computed(
  () => new Set(projects.value.map((project) => project.current_stage)).size,
)

function platformTagClass(platform: string) {
  if (platform.includes('抖音')) return 'platform-douyin'
  if (platform.includes('快手')) return 'platform-kuaishou'
  if (platform.includes('小红书')) return 'platform-xiaohongshu'
  if (platform.includes('视频号')) return 'platform-video'
  return ''
}

async function fetchProjects() {
  loading.value = true
  try {
    projects.value = await listProjects()
    await nextTickAnimate()
  } catch (error) {
    ElMessage.error('项目列表加载失败')
  } finally {
    loading.value = false
  }
}

async function nextTickAnimate() {
  await new Promise((r) => setTimeout(r, 50))
  if (overviewRef.value) {
    gsap.from(overviewRef.value.children, {
      opacity: 0,
      y: 24,
      duration: 0.6,
      stagger: 0.1,
      ease: 'power3.out',
    })
  }
  if (listRef.value) {
    gsap.from(listRef.value.children, {
      opacity: 0,
      y: 28,
      duration: 0.55,
      stagger: 0.08,
      ease: 'power3.out',
      delay: 0.2,
    })
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
    <!-- Asymmetric Hero Header -->
    <div class="section-header mb-7">
      <div>
        <p class="eyebrow">Projects</p>
        <h1>项目档案</h1>
      </div>
      <el-button type="primary" size="large" @click="router.push('/projects/new')">
        新建项目
      </el-button>
    </div>

    <!-- Bento Overview Strip -->
    <div v-if="!loading" ref="overviewRef" class="overview-strip">
      <div class="overview-item">
        <span>项目数</span>
        <strong>{{ projectCount }}</strong>
      </div>
      <div class="overview-item">
        <span>覆盖平台</span>
        <strong>{{ platformCount }}</strong>
      </div>
      <div class="overview-item">
        <span>运营阶段</span>
        <strong>{{ activeStageCount }}</strong>
      </div>
    </div>

    <!-- Skeleton Loading -->
    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-7">
      <div
        v-for="i in 3"
        :key="i"
        class="h-28 rounded-[var(--studio-radius-card)] bg-zinc-800 animate-pulse"
      />
      <div
        v-for="i in 4"
        :key="`c-${i}`"
        class="h-64 rounded-[var(--studio-radius-card)] bg-zinc-800 animate-pulse md:col-span-2"
      />
    </div>

    <!-- Empty State -->
    <div v-else-if="!projects.length" class="empty-state">
      <h2>暂无项目</h2>
      <p class="mt-2 text-zinc-400">先创建一个项目档案，后续生成内容会围绕它展开。</p>
      <el-button type="primary" class="mt-6" @click="router.push('/projects/new')">
        创建第一个项目
      </el-button>
    </div>

    <!-- Project Cards -->
    <div v-else ref="listRef" class="project-card-grid">
      <article
        v-for="project in projects"
        :key="project.id"
        class="project-card"
        :class="{ 'md:col-span-2': project.id === projects[0]?.id }"
      >
        <div class="project-card-header">
          <button
            class="project-card-title"
            type="button"
            @click="router.push(`/projects/${project.id}`)"
          >
            {{ project.project_name }}
          </button>
          <el-tag type="success" size="small">{{ project.current_stage || '未填写' }}</el-tag>
        </div>

        <div class="project-field-matrix">
          <FieldChips label="行业" :value="project.industry" tone="industry" compact />
          <FieldChips label="细分行业" :value="project.sub_industry" tone="subIndustry" compact />
          <FieldChips label="产品" :value="project.product" tone="product" compact />
          <FieldChips label="目标客户" :value="project.target_audience" tone="customer" compact />
        </div>

        <div class="project-card-platforms project-platform-panel">
          <span>平台</span>
          <div class="platform-pill-row">
            <el-tag
              v-for="platform in project.platforms"
              :key="platform"
              :class="['tag-item', 'platform-tag', platformTagClass(platform)]"
              size="small"
            >
              {{ platform }}
            </el-tag>
            <strong v-if="!project.platforms.length" class="text-sm text-zinc-400">未选择</strong>
          </div>
        </div>

        <div class="project-card-actions">
          <el-button type="primary" plain @click="router.push(`/projects/${project.id}`)">
            查看
          </el-button>
          <el-button type="danger" plain @click="handleDelete(project)">删除</el-button>
        </div>
      </article>
    </div>
  </section>
</template>
