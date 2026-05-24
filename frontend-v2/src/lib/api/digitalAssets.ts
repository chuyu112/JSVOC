import { api } from "./client";

export type DigitalAssetType = "script" | "image" | "video";

export interface DigitalAsset {
  id: number;
  user_id: number;
  asset_type: DigitalAssetType | string;
  source_project_id: number | null;
  project_snapshot: Record<string, unknown>;
  title: string;
  preview_text: string | null;
  content_text: string | null;
  generation_record_id: number | null;
  oss_object_key: string | null;
  mime_type: string | null;
  file_size: number | null;
  asset_metadata: Record<string, unknown>;
  access_url: string | null;
  access_url_expires_at: number | null;
  created_at: string;
}

export interface DigitalAssetQuery {
  asset_type?: DigitalAssetType | null;
  project_id?: number | null;
  limit?: number;
  offset?: number;
}

export async function listDigitalAssets(query: DigitalAssetQuery = {}): Promise<DigitalAsset[]> {
  const params = new URLSearchParams();
  if (query.asset_type) params.set("asset_type", query.asset_type);
  if (query.project_id != null) params.set("project_id", String(query.project_id));
  params.set("limit", String(query.limit ?? 50));
  params.set("offset", String(query.offset ?? 0));
  return api.get<DigitalAsset[]>(`/api/digital-assets?${params.toString()}`);
}
