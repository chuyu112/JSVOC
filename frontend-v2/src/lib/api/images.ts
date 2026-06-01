import { api } from "./client";

export type ImageSize =
  | "1024x1024"
  | "1536x1024"
  | "1024x1536"
  | "2048x1152"
  | "1152x2048"
  | "auto";
export type ImageQuality = "high" | "medium" | "low" | "auto";
export type ImageReferenceType = "persona" | "product" | "location";

export interface GeneratedImage {
  b64_json?: string;
  url?: string;
  data_url?: string;
  asset_id?: number;
  oss_object_key?: string;
  mime_type?: string;
  signed_url_expires_at?: number;
}

export interface ImageGenerateResponse {
  provider: string;
  model: string;
  images: GeneratedImage[];
  usage: Record<string, unknown>;
  latency_ms: number;
}

export interface ImagePromptEnhanceResponse {
  enhanced_prompt: string;
  subject: string;
  removed_terms: string[];
  notes: string[];
}

export interface ImageReferenceInput {
  reference_image_type: ImageReferenceType;
  source_image_base64: string;
  source_image_mime: string;
  source_image_filename: string;
  reference_image_name?: string;
}

export async function generateImage(
  projectId: number | null,
  prompt: string,
  n: number = 1,
  size: ImageSize = "1536x1024",
  quality: ImageQuality = "medium",
): Promise<ImageGenerateResponse> {
  return api.post<ImageGenerateResponse>("/api/creation/images/generate", {
    project_id: projectId,
    prompt,
    n,
    size,
    quality,
  });
}

export async function generateImageAsync(
  projectId: number | null,
  prompt: string,
  n: number = 1,
  size: ImageSize = "1024x1536",
  quality: ImageQuality = "medium",
): Promise<{ task_id: number; task_type: string; status: string }> {
  return api.post("/api/creation/images/generate/async", {
    project_id: projectId,
    prompt,
    n,
    size,
    quality,
  });
}

export async function enhanceImagePrompt(
  projectId: number | null,
  prompt: string,
  mode: "text" | "image" = "text",
  size: ImageSize = "1024x1536",
  quality: ImageQuality = "medium",
): Promise<ImagePromptEnhanceResponse> {
  return api.post<ImagePromptEnhanceResponse>("/api/creation/images/enhance-prompt", {
    project_id: projectId,
    prompt,
    mode,
    size,
    quality,
  });
}

export async function editImageAsync(
  projectId: number | null,
  prompt: string,
  referenceImages: ImageReferenceInput[],
  n: number = 1,
  size: ImageSize = "1024x1536",
  quality: ImageQuality = "medium",
): Promise<{ task_id: number; task_type: string; status: string }> {
  return api.post("/api/creation/images/edit/async", {
    project_id: projectId,
    prompt,
    n,
    size,
    quality,
    reference_images: referenceImages,
    reference_image_types: referenceImages.map((img) => img.reference_image_type),
  });
}

export async function editImage(
  projectId: number | null,
  prompt: string,
  referenceImages: ImageReferenceInput[],
  n: number = 1,
  size: ImageSize = "1536x1024",
  quality: ImageQuality = "medium",
): Promise<ImageGenerateResponse> {
  return api.post<ImageGenerateResponse>("/api/creation/images/edit", {
    project_id: projectId,
    prompt,
    n,
    size,
    quality,
    reference_images: referenceImages,
    reference_image_types: referenceImages.map((img) => img.reference_image_type),
  });
}

export interface ProjectReferenceImage {
  id: number;
  project_id: number;
  reference_image_type: ImageReferenceType;
  source_image_base64: string;
  source_image_mime: string;
  source_image_filename: string;
  created_at: string;
}

export async function listProjectReferenceImages(projectId: number): Promise<ProjectReferenceImage[]> {
  return api.get<ProjectReferenceImage[]>(`/api/projects/${projectId}/reference-images`);
}

export async function createProjectReferenceImage(
  projectId: number,
  payload: ImageReferenceInput,
): Promise<ProjectReferenceImage> {
  return api.post<ProjectReferenceImage>(`/api/projects/${projectId}/reference-images`, payload);
}

export async function deleteProjectReferenceImage(projectId: number, imageId: number): Promise<void> {
  await api.delete(`/api/projects/${projectId}/reference-images/${imageId}`);
}

export interface DigitalAsset {
  id: number;
  asset_type: string;
  source_project_id: number | null;
  title: string;
  preview_text: string | null;
  content_text: string | null;
  access_url: string | null;
  asset_metadata: Record<string, unknown>;
  created_at: string;
}

export async function listProjectDigitalAssets(_projectId: number, assetType: string = "image"): Promise<DigitalAsset[]> {
  return api.get<DigitalAsset[]>(
    `/api/digital-assets?asset_type=${assetType}&limit=100`
  );
}

export async function deleteDigitalAsset(assetId: number): Promise<void> {
  await api.delete(`/api/digital-assets/${assetId}`);
}
