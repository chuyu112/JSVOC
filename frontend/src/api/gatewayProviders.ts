import { apiClient, type ApiResponse } from './client'

export type GatewayCapability = 'chat' | 'image' | 'video'

export interface GatewayProvider {
  id: number
  capability: GatewayCapability
  name: string
  provider: string
  base_url: string | null
  model: string
  is_enabled: boolean
  is_default: boolean
  config: Record<string, unknown>
  has_api_key: boolean
  api_key_mask: string | null
  created_at: string
  updated_at: string
}

export interface GatewayProviderPayload {
  capability: GatewayCapability
  name: string
  provider: string
  base_url?: string | null
  api_key?: string | null
  model: string
  is_enabled: boolean
  is_default: boolean
  config: Record<string, unknown>
}

export interface GatewayProviderDefault {
  capability: GatewayCapability
  source: 'database' | 'environment' | 'none'
  provider_config: GatewayProvider | null
  fallback: Record<string, unknown> | null
}

function adminConfig(adminToken: string) {
  return {
    headers: {
      'X-Admin-Token': adminToken,
    },
  }
}

export async function listGatewayProviders(
  adminToken: string,
  capability?: GatewayCapability,
): Promise<GatewayProvider[]> {
  const response = await apiClient.get<ApiResponse<GatewayProvider[]>>(
    '/api/admin/gateway-providers',
    {
      ...adminConfig(adminToken),
      params: {
        capability,
      },
    },
  )
  return response.data.data
}

export async function listGatewayProviderDefaults(
  adminToken: string,
): Promise<GatewayProviderDefault[]> {
  const response = await apiClient.get<ApiResponse<GatewayProviderDefault[]>>(
    '/api/admin/gateway-providers/defaults',
    adminConfig(adminToken),
  )
  return response.data.data
}

export async function createGatewayProvider(
  adminToken: string,
  payload: GatewayProviderPayload,
): Promise<GatewayProvider> {
  const response = await apiClient.post<ApiResponse<GatewayProvider>>(
    '/api/admin/gateway-providers',
    payload,
    adminConfig(adminToken),
  )
  return response.data.data
}

export async function updateGatewayProvider(
  adminToken: string,
  providerId: number,
  payload: Partial<GatewayProviderPayload>,
): Promise<GatewayProvider> {
  const response = await apiClient.put<ApiResponse<GatewayProvider>>(
    `/api/admin/gateway-providers/${providerId}`,
    payload,
    adminConfig(adminToken),
  )
  return response.data.data
}

export async function deleteGatewayProvider(
  adminToken: string,
  providerId: number,
): Promise<void> {
  await apiClient.delete<ApiResponse<null>>(
    `/api/admin/gateway-providers/${providerId}`,
    adminConfig(adminToken),
  )
}

export async function setDefaultGatewayProvider(
  adminToken: string,
  providerId: number,
): Promise<GatewayProvider> {
  const response = await apiClient.post<ApiResponse<GatewayProvider>>(
    `/api/admin/gateway-providers/${providerId}/set-default`,
    null,
    adminConfig(adminToken),
  )
  return response.data.data
}
