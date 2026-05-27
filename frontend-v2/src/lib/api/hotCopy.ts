import { api } from "./client";

export interface HotCopyMaterial {
  id: number;
  user_id: number;
  project_id: number | null;
  platform: string;
  source_type: string;
  source_url: string | null;
  account_name: string | null;
  account_home_url: string | null;
  cover_url: string | null;
  title: string;
  original_script: string;
  metrics_json: Record<string, unknown>;
  analysis_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface CreateManualHotCopyPayload {
  project_id?: number | null;
  platform: "douyin" | "xiaohongshu" | "shipinhao";
  source_url?: string | null;
  account_name?: string | null;
  account_home_url?: string | null;
  cover_url?: string | null;
  title: string;
  original_script: string;
  metrics_json?: Record<string, unknown>;
}

export interface CreateAutoHotCopyPayload {
  project_id?: number | null;
  source_url?: string | null;
  platform?: "douyin" | "xiaohongshu" | "shipinhao";
}

export interface HotCopyAnalysisResponse {
  material: HotCopyMaterial;
  analysis: Record<string, unknown>;
  generation_record_id: number | null;
}

export interface HotCopyRewritePayload {
  project_id?: number | null;
  rewrite_mode: "light" | "medium" | "strong";
  duration: "30s" | "60s" | "90s";
  conversion_goal: string;
  product?: string | null;
  target_customer?: string | null;
  account_persona?: string | null;
}

export interface HotCopyRewriteResponse {
  rewrite: {
    id: number;
    material_id: number;
    user_id: number;
    project_id: number | null;
    rewrite_mode: string;
    duration: string;
    conversion_goal: string;
    input_json: Record<string, unknown>;
    output_json: Record<string, unknown>;
    generation_record_id: number | null;
    created_at: string;
  };
  output: Record<string, unknown>;
  generation_record_id: number | null;
}

export async function createManualHotCopyMaterial(payload: CreateManualHotCopyPayload): Promise<HotCopyMaterial> {
  return api.post<HotCopyMaterial>("/api/hot-copy/materials/manual", payload, { timeoutMs: 20000 });
}

export async function createAutoHotCopyMaterial(payload: CreateAutoHotCopyPayload): Promise<HotCopyMaterial> {
  return api.post<HotCopyMaterial>("/api/hot-copy/materials/auto", payload, { timeoutMs: 60000 });
}

export async function uploadHotCopyMaterial(file: File, projectId?: number | null, platform = "douyin"): Promise<HotCopyMaterial> {
  const formData = new FormData();
  formData.append("file", file);
  if (projectId) {
    formData.append("project_id", String(projectId));
  }
  formData.append("platform", platform);
  return api.post<HotCopyMaterial>("/api/hot-copy/materials/auto-upload", formData, { timeoutMs: 120000 });
}

export async function listHotCopyMaterials(): Promise<HotCopyMaterial[]> {
  return api.get<HotCopyMaterial[]>("/api/hot-copy/materials");
}

export async function analyzeHotCopyMaterial(materialId: number): Promise<HotCopyAnalysisResponse> {
  return api.post<HotCopyAnalysisResponse>(`/api/hot-copy/materials/${materialId}/analyze`, {}, { timeoutMs: 90000 });
}

export async function rewriteHotCopyMaterial(
  materialId: number,
  payload: HotCopyRewritePayload,
): Promise<HotCopyRewriteResponse> {
  return api.post<HotCopyRewriteResponse>(`/api/hot-copy/materials/${materialId}/rewrite`, payload, { timeoutMs: 90000 });
}

export async function searchRedianbaoHotCopy(keyword: string, count = 30): Promise<unknown> {
  return api.post<unknown>("/api/hot-copy/redianbao/search", { keyword, platform: "douyin", count }, { timeoutMs: 20000 });
}

export interface GenerationTaskSubmitResponse {
  task_id: number;
  task_type: string;
  status: string;
  credit_cost: number;
}

export async function generateVideoFromRewrite(rewriteId: number): Promise<GenerationTaskSubmitResponse> {
  return api.post<GenerationTaskSubmitResponse>(`/api/hot-copy/rewrites/${rewriteId}/generate-video`, {}, { timeoutMs: 30000 });
}

export interface SceneTaskInfo {
  task_id: number;
  task_type: string;
  status: string;
  scene_no: number;
  credit_cost: number;
}

export async function generateScenesFromRewrite(rewriteId: number): Promise<{ tasks: SceneTaskInfo[]; total: number }> {
  return api.post<{ tasks: SceneTaskInfo[]; total: number }>(`/api/hot-copy/rewrites/${rewriteId}/generate-scenes`, {}, { timeoutMs: 60000 });
}
