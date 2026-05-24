import { apiClient, type ApiResponse } from './client'

export type DigitalAssetType = 'script' | 'image' | 'video'

export interface DigitalAsset {
  id: number
  user_id: number
  asset_type: DigitalAssetType | string
  source_project_id: number | null
  project_snapshot: Record<string, unknown>
  title: string
  preview_text: string | null
  content_text: string | null
  generation_record_id: number | null
  oss_object_key: string | null
  mime_type: string | null
  file_size: number | null
  asset_metadata: Record<string, unknown>
  access_url: string | null
  access_url_expires_at: number | null
  created_at: string
}

export interface DigitalAssetQuery {
  asset_type?: DigitalAssetType | null
  project_id?: number | null
  limit?: number
  offset?: number
}

export async function listDigitalAssets(query: DigitalAssetQuery = {}): Promise<DigitalAsset[]> {
  const response = await apiClient.get<ApiResponse<DigitalAsset[]>>('/api/digital-assets', {
    params: {
      asset_type: query.asset_type ?? undefined,
      project_id: query.project_id ?? undefined,
      limit: query.limit ?? 50,
      offset: query.offset ?? 0,
    },
  })
  return response.data.data
}
