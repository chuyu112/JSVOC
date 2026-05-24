import { api } from "./client";

export interface HotVideoItem {
  title: string;
  platform: string;
  creator: string;
  source_url: string;
  source_title: string;
  publish_time: string;
  metrics: Record<string, unknown>;
  why_trending: string;
  hook: string;
  structure: string[];
  remake_angle: string;
  rewrite_brief: string;
  risk_notes: string[];
  tags: string[];
}

export interface HotVideoSearchResponse {
  items: HotVideoItem[];
  provider: string;
  model: string;
  usage: Record<string, unknown>;
  sources: Array<{ title?: string; url: string }>;
  latency_ms: number;
  generation_record_id: number | null;
}

export interface HotVideoSearchPayload {
  project_id?: number;
  platform: string;
  keyword: string;
  search_focus: string;
  count: number;
  web_search_context_size?: "low" | "medium" | "high";
}

export async function searchHotVideos(payload: HotVideoSearchPayload): Promise<HotVideoSearchResponse> {
  return api.post<HotVideoSearchResponse>("/api/creation/hot-videos/search", payload);
}
