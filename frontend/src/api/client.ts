import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 360000,
  withCredentials: true,
})

export interface ApiResponse<T> {
  success: boolean
  data: T
  message: string
}

const SKIP_401_PATHS = ['/api/auth/login', '/api/auth/register']

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status !== 401) {
      return Promise.reject(error)
    }

    const url: string = error.config?.url ?? ''
    if (SKIP_401_PATHS.some((path) => url.includes(path))) {
      return Promise.reject(error)
    }

    try {
      const { useAuthStore } = await import('../stores/auth')
      useAuthStore().clearSession()
    } catch {
      // pinia not initialized yet
    }

    try {
      const { router } = await import('../router')
      const current = router.currentRoute.value
      if (current.name !== 'login') {
        const redirect = current.fullPath
        await router
          .push({
            path: '/login',
            query: redirect && redirect !== '/' ? { redirect } : undefined,
          })
          .catch(() => undefined)
      }
    } catch {
      // router not available yet
    }

    return Promise.reject(error)
  },
)
