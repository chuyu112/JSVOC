import { api } from "./client";

export interface DigitalHumanAvatar {
  id: number;
  name: string;
  avatar_type: string;
  thumbnail_url: string | null;
  video_url: string | null;
  gender: string | null;
  is_active: boolean;
}

export interface DigitalHumanVoice {
  id: number;
  name: string;
  voice_type: string;
  sample_url: string | null;
  gender: string | null;
  is_active: boolean;
}

export interface DigitalHumanVideo {
  id: number;
  title: string;
  video_url: string | null;
  audio_url: string | null;
  duration: number | null;
  status: string;
  error_message: string | null;
  created_at: string;
}

export interface GenerateVideoPayload {
  project_id: number;
  script_id: number;
  voice_id: number;
  avatar_id: number;
  with_subtitle?: boolean;
  with_bgm?: boolean;
  resolution?: string;
}

export async function listAvatars(): Promise<DigitalHumanAvatar[]> {
  return api.get<DigitalHumanAvatar[]>("/api/digital-human/avatars");
}

export async function listVoices(): Promise<DigitalHumanVoice[]> {
  return api.get<DigitalHumanVoice[]>("/api/digital-human/voices");
}

export async function cloneVoice(formData: FormData): Promise<DigitalHumanVoice> {
  const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || ""}/api/digital-human/voices/clone`, {
    method: "POST",
    body: formData,
    credentials: "include",
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "声音克隆失败");
  }
  const json = await response.json();
  if (!json.success) {
    throw new Error(json.message || "声音克隆失败");
  }
  return json.data;
}

export async function listVideos(projectId?: number): Promise<DigitalHumanVideo[]> {
  const params = projectId ? `?project_id=${projectId}` : "";
  return api.get<DigitalHumanVideo[]>(`/api/digital-human/videos${params}`);
}

export async function generateVideo(payload: GenerateVideoPayload): Promise<{ task_id: number; video_id: number; status: string; message: string }> {
  return api.post("/api/digital-human/videos/generate", payload);
}
