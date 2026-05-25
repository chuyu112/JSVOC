import { api } from "./client";

export type GenerationModuleName =
  | "account_package"
  | "execution_plan"
  | "strategy_bundle"
  | "topics"
  | "script"
  | "hot_copy_analysis"
  | "hot_copy_rewrite"
  | "image_generate"
  | "image_edit"
  | "video_generate"
  | "ai_chat";

export interface GenerationRecord {
  id: number;
  user_id: number | null;
  project_id: number | null;
  module_name: string;
  input_data: Record<string, unknown>;
  output_data: Record<string, unknown>;
  model_provider: string;
  model_name: string;
  prompt_version: string | null;
  token_usage: Record<string, unknown>;
  latency_ms: number | null;
  created_at: string;
}

export interface GenerationRecordQuery {
  project_id?: number | null;
  module_name?: string | null;
  limit?: number;
  offset?: number;
}

export const moduleNameText: Record<GenerationModuleName, string> = {
  account_package: "账号包装",
  execution_plan: "执行计划",
  strategy_bundle: "账号包装+执行计划",
  topics: "选题生成",
  script: "文案生成",
  hot_copy_analysis: "爆点拆解",
  hot_copy_rewrite: "爆款仿写",
  image_generate: "生图",
  image_edit: "图生图",
  video_generate: "生视频",
  ai_chat: "AI聊天",
};

export function formatModuleName(moduleName: string) {
  return moduleNameText[moduleName as GenerationModuleName] ?? moduleName;
}

export async function listGenerationRecords(
  query: GenerationRecordQuery = {},
): Promise<GenerationRecord[]> {
  const params = new URLSearchParams();
  if (query.project_id != null) params.set("project_id", String(query.project_id));
  if (query.module_name) params.set("module_name", query.module_name);
  params.set("limit", String(query.limit ?? 50));
  params.set("offset", String(query.offset ?? 0));
  return api.get<GenerationRecord[]>(`/api/generation-records?${params.toString()}`);
}

export async function getGenerationRecord(recordId: number): Promise<GenerationRecord> {
  return api.get<GenerationRecord>(`/api/generation-records/${recordId}`);
}

export interface WeeklyPlanItem {
  week: number;
  goal: string;
  focus: string;
  key_tasks: string[];
}

export interface DailyPlanItem {
  day: number;
  task: string;
  topic: string;
  shooting_task: string;
  review_metrics: string[];
}

export interface ExecutionPlan {
  cycle: string;
  weekly_plan: WeeklyPlanItem[];
  daily_plan: DailyPlanItem[];
  notes: string[];
}

export interface AccountPackage {
  id: number;
  account_positioning: string;
  persona: string;
  target_user_profile: Record<string, unknown>;
  account_names: string[];
  bios: Record<string, string>;
  content_columns: unknown[];
  trust_design: string[];
  conversion_path: string[];
  platform_strategies: Record<string, unknown>;
  content_style: string | null;
  trust_points: string[];
  monetization_paths: string[];
  execution_stage: string | null;
  created_at: string | null;
  execution_plan?: ExecutionPlan | null;
}

export async function getLatestAccountPackage(projectId: number): Promise<AccountPackage | null> {
  const res = await api.get<AccountPackage>(`/api/strategy/account-package-execution-plan/projects/${projectId}/latest`);
  if (!res || !res.id) return null;
  return res;
}

export async function generateAccountPackage(
  projectId: number,
  cycle: string = "30天",
  dailyTime: string = "2小时",
): Promise<unknown> {
  return api.post<unknown>("/api/strategy/account-package-execution-plan/generate", {
    project_id: projectId,
    cycle,
    daily_time: dailyTime,
  });
}
