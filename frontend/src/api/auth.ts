import { apiClient, type ApiResponse } from './client'

export interface AuthUser {
  id: number
  display_name: string
  username: string | null
  email: string | null
  is_active: boolean
  created_at: string
}

export interface AuthSession {
  user: AuthUser
}

export interface LoginPayload {
  login: string
  password: string
}

export interface RegisterPayload {
  display_name: string
  username: string
  email: string
  password: string
}

export async function getCurrentUser(): Promise<AuthSession> {
  const response = await apiClient.get<ApiResponse<AuthSession>>('/api/auth/me')
  return response.data.data
}

export async function login(payload: LoginPayload): Promise<AuthSession> {
  const response = await apiClient.post<ApiResponse<AuthSession>>('/api/auth/login', payload)
  return response.data.data
}

export async function register(payload: RegisterPayload): Promise<AuthSession> {
  const response = await apiClient.post<ApiResponse<AuthSession>>('/api/auth/register', payload)
  return response.data.data
}

export async function logout(): Promise<void> {
  await apiClient.post<ApiResponse<{ logged_out: boolean }>>('/api/auth/logout')
}
