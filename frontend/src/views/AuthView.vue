<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import gsap from 'gsap'

import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const mode = ref<'login' | 'register'>('login')
const loading = ref(false)
const panelRef = ref<HTMLElement | null>(null)

const loginForm = reactive({
  login: '',
  password: '',
})

const registerForm = reactive({
  display_name: '',
  username: '',
  email: '',
  password: '',
})

function redirectTarget() {
  const redirect = route.query.redirect
  if (typeof redirect !== 'string') return '/projects'
  if (!redirect.startsWith('/') || redirect.startsWith('//')) return '/projects'
  return redirect
}

async function handleLogin() {
  loading.value = true
  try {
    await auth.login(loginForm)
    await router.push(redirectTarget())
  } catch (error) {
    ElMessage.error('账号或密码不正确')
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  loading.value = true
  try {
    await auth.register(registerForm)
    await router.push(redirectTarget())
  } catch (error) {
    ElMessage.error('注册失败，请检查用户名或邮箱是否已存在')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (panelRef.value) {
    gsap.from(panelRef.value, {
      opacity: 0,
      x: 40,
      duration: 0.7,
      ease: 'power3.out',
      delay: 0.15,
    })
  }
})
</script>

<template>
  <section class="auth-page">
    <!-- Left Panel: Branding -->
    <div class="auth-brand hidden md:flex">
      <div class="auth-brand-content">
        <div class="auth-brand-mark">SS</div>
        <h2 class="auth-brand-title">Strategy Studio</h2>
        <p class="auth-brand-desc">
          短视频运营策略工作台。从项目策划到内容生产，一站式驱动增长。
        </p>
      </div>
    </div>

    <!-- Right Panel: Form -->
    <div ref="panelRef" class="auth-panel">
      <div class="auth-heading">
        <p class="eyebrow">Account</p>
        <h1 class="text-2xl font-bold tracking-tight">{{ mode === 'login' ? '登录' : '注册' }}</h1>
      </div>

      <el-segmented
        v-model="mode"
        class="auth-mode"
        :options="[
          { label: '登录', value: 'login' },
          { label: '注册', value: 'register' },
        ]"
      />

      <el-form
        v-if="mode === 'login'"
        label-position="top"
        class="auth-form"
        @submit.prevent="handleLogin"
      >
        <el-form-item label="用户名或邮箱" required>
          <el-input v-model="loginForm.login" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码" required>
          <el-input v-model="loginForm.password" type="password" autocomplete="current-password" />
        </el-form-item>
        <el-button type="primary" size="large" native-type="submit" :loading="loading">
          登录
        </el-button>
      </el-form>

      <el-form
        v-else
        label-position="top"
        class="auth-form"
        @submit.prevent="handleRegister"
      >
        <el-form-item label="昵称" required>
          <el-input v-model="registerForm.display_name" autocomplete="name" />
        </el-form-item>
        <el-form-item label="用户名" required>
          <el-input v-model="registerForm.username" autocomplete="username" />
        </el-form-item>
        <el-form-item label="邮箱" required>
          <el-input v-model="registerForm.email" autocomplete="email" />
        </el-form-item>
        <el-form-item label="密码" required>
          <el-input v-model="registerForm.password" type="password" autocomplete="new-password" />
        </el-form-item>
        <el-button type="primary" size="large" native-type="submit" :loading="loading">
          注册并登录
        </el-button>
      </el-form>
    </div>
  </section>
</template>

<style scoped>
.auth-page {
  display: grid;
  grid-template-columns: 1fr;
  min-height: calc(100dvh - 60px);
  background: linear-gradient(135deg, #0a0a0c 0%, #030303 50%, #0a0a0c 100%);
}

@media (min-width: 768px) {
  .auth-page {
    grid-template-columns: 1fr 1fr;
  }
}

.auth-brand {
  position: relative;
  align-items: center;
  justify-content: center;
  padding: 48px;
  background:
    radial-gradient(circle at 20% 30%, rgba(16, 185, 129, 0.12), transparent 40%),
    linear-gradient(135deg, rgba(5, 46, 22, 0.25) 0%, rgba(0, 0, 0, 0.55) 100%);
}

.auth-brand::before {
  position: absolute;
  inset: 0;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  content: '';
}

.auth-brand-content {
  max-width: 360px;
}

.auth-brand-mark {
  display: inline-grid;
  width: 48px;
  height: 48px;
  place-items: center;
  border-radius: 14px;
  background: var(--studio-primary);
  color: #000000;
  font-size: 16px;
  font-weight: 720;
  letter-spacing: -0.02em;
  margin-bottom: 24px;
  box-shadow: 0 0 20px -6px rgba(66, 255, 156, 0.55);
}

.auth-brand-title {
  margin: 0 0 12px;
  color: var(--studio-ink);
  font-size: 32px;
  font-weight: 720;
  letter-spacing: -0.03em;
  line-height: 1.15;
}

.auth-brand-desc {
  margin: 0;
  color: var(--studio-muted);
  font-size: 15px;
  line-height: 1.6;
  max-width: 320px;
}

.auth-panel {
  display: flex;
  flex-direction: column;
  justify-content: center;
  width: 100%;
  max-width: 440px;
  margin: 0 auto;
  padding: 32px 24px;
}

@media (min-width: 768px) {
  .auth-panel {
    padding: 48px;
  }
}

.auth-heading {
  margin-bottom: 24px;
}

.auth-mode {
  width: 100%;
  margin-bottom: 24px;
}

.auth-form .el-button {
  width: 100%;
  margin-top: 8px;
}

.auth-form :deep(.el-form-item__label) {
  font-weight: 580;
  padding-bottom: 4px;
}
</style>
