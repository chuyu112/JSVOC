import { api } from "./client";

export type GenerationTaskStatus = "queued" | "running" | "succeeded" | "failed";

export interface GenerationTask {
  id: number;
  task_type: string;
  status: GenerationTaskStatus;
  user_id: number | null;
  project_id: number | null;
  input_data: Record<string, unknown>;
  result_data: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
  credit_cost: number | null;
  credit_transaction_id: number | null;
}

export function listGenerationTasks(limit: number = 10): Promise<GenerationTask[]> {
  return api.get<GenerationTask[]>(`/api/generation-tasks?limit=${limit}`);
}
