import { api } from "./client";

export interface RubricScores {
  er: number;
  sr: number;
  hp: number;
  ql: number;
  na: number;
  ab: number;
  sat: number;
}

export interface HkrScores {
  h: number;
  k: number;
  r: number;
}

export interface TopicData {
  user_pain_point?: string;
  hook?: string;
  shooting_suggestion?: string;
  conversion_method?: string;
  shooting_script?: string;
  spoken_script?: string;
  seedance_video_prompt?: string;
  image_prompt?: string;
  image_edit_prompt?: string;
  content_format?: string;
  rubric?: RubricScores;
  hkr?: HkrScores;
}

export interface Topic {
  id: number;
  project_id: number;
  title: string;
  content_type: string;
  platform: string;
  goal: string;
  selling_point: string | null;
  score: number;
  is_favorite: boolean;
  topic_data: TopicData;
  created_at: string;
}

export interface TopicGenerateResponse {
  topics: Topic[];
  generation_record_id: number | null;
  provider: string;
  model: string;
  usage: Record<string, unknown>;
  latency_ms: number;
}

export interface TopicBatchGenerateResponse {
  topics: Topic[];
  generated_count: number;
  target_count: number;
  provider: string;
  model: string;
  latency_ms: number;
}

export type TopicContentFormat = "video_spoken" | "video_script" | "image";

export async function generateTopics(
  projectId: number,
  platform: string,
  goal: string,
  contentFormat: string,
  count: number,
  existingTitles: string[] = [],
  topicIndex?: number,
  generationBatchId?: string,
  generationTargetCount?: number,
): Promise<TopicGenerateResponse> {
  return api.post<TopicGenerateResponse>("/api/creation/topics/generate", {
    project_id: projectId,
    platform,
    goal,
    content_format: contentFormat,
    count,
    existing_titles: existingTitles,
    topic_index: topicIndex,
    generation_batch_id: generationBatchId,
    generation_target_count: generationTargetCount,
  });
}

export async function listProjectTopics(projectId: number): Promise<Topic[]> {
  return api.get<Topic[]>(`/api/projects/${projectId}/topics`);
}

export async function updateTopicFavorite(topicId: number, isFavorite: boolean): Promise<Topic> {
  return api.patch<Topic>(`/api/topics/${topicId}/favorite`, { is_favorite: isFavorite });
}

export async function deleteTopic(topicId: number): Promise<void> {
  await api.delete(`/api/topics/${topicId}`);
}

export async function generateTopicsBatch(
  projectId: number,
  platform: string,
  goal: string,
  contentFormat: string,
  targetCount: number,
): Promise<TopicBatchGenerateResponse> {
  return api.post<TopicBatchGenerateResponse>("/api/creation/topics/generate-batch", {
    project_id: projectId,
    platform,
    goal,
    content_format: contentFormat,
    target_count: targetCount,
  });
}
