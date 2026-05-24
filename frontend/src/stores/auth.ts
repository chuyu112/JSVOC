import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import {
  getCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
  register as registerRequest,
  type AuthUser,
  type LoginPayload,
  type RegisterPayload,
} from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null)
  const checked = ref(false)
  const loading = ref(false)

  const displayName = computed(() => user.value?.display_name || user.value?.username || '未登录')
  const isAuthenticated = computed(() => Boolean(user.value))

  function clearSession() {
    user.value = null
    checked.value = true
  }

  async function loadCurrentUser() {
    if (checked.value && user.value) return user.value

    loading.value = true
    try {
      const session = await getCurrentUser()
      user.value = session.user
      return session.user
    } finally {
      checked.value = true
      loading.value = false
    }
  }

  async function login(payload: LoginPayload) {
    const session = await loginRequest(payload)
    user.value = session.user
    checked.value = true
    return session.user
  }

  async function register(payload: RegisterPayload) {
    const session = await registerRequest(payload)
    user.value = session.user
    checked.value = true
    return session.user
  }

  async function logout() {
    try {
      await logoutRequest()
    } finally {
      user.value = null
      checked.value = true
    }
  }

  return {
    checked,
    clearSession,
    displayName,
    isAuthenticated,
    loadCurrentUser,
    loading,
    login,
    logout,
    register,
    user,
  }
})
