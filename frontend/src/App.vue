<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { useAuthStore } from './stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const globalNavItems = [
  { label: '项目', to: '/projects' },
  { label: '数字资产', to: '/assets' },
  { label: '生成历史', to: '/history' },
]

const currentNavLabel = computed(
  () => globalNavItems.find((item) => route.path.startsWith(item.to))?.label || '项目',
)

async function handleLogout() {
  try {
    await auth.logout()
    await router.push('/login')
  } catch (error) {
    ElMessage.error('退出登录失败')
  }
}
</script>

<template>
  <el-container class="app-shell">
    <el-header class="app-header">
      <div class="app-header-main">
        <router-link class="brand" to="/projects">
          <span class="brand-mark">SS</span>
          <span>
            <strong>短视频运营</strong>
            <small>Strategy Studio</small>
          </span>
        </router-link>

        <nav class="nav-links desktop-nav" aria-label="全局导航">
          <router-link
            v-for="item in globalNavItems"
            :key="item.to"
            :to="item.to"
          >
            {{ item.label }}
          </router-link>
        </nav>

        <div v-if="auth.isAuthenticated" class="console-user">
          <span class="console-user-name">{{ auth.displayName }}</span>
          <el-button size="small" plain @click="handleLogout">退出登录</el-button>
        </div>
      </div>

      <details v-if="auth.isAuthenticated" class="mobile-console-menu">
        <summary>{{ currentNavLabel }}</summary>
        <nav class="mobile-nav-links" aria-label="移动端全局导航">
          <router-link
            v-for="item in globalNavItems"
            :key="item.to"
            :to="item.to"
          >
            {{ item.label }}
          </router-link>
        </nav>
      </details>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>
