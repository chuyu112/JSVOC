import { api } from "./client";

export interface BenchmarkAccount {
  platform: string;
  account_name: string;
  notes: string;
}

export interface ProjectPayload {
  project_name: string;
  industry: string;
  sub_industry: string | null;
  product: string;
  personal_intro: string;
  target_audience: string;
  platforms: string[];
  benchmark_accounts?: BenchmarkAccount[];
  current_stage: string;
}

export interface Project extends ProjectPayload {
  id: number;
  user_id: number | null;
  created_at: string;
  updated_at: string;
}

export async function listProjects(): Promise<Project[]> {
  return api.get<Project[]>("/api/projects");
}

export async function getProject(projectId: number): Promise<Project> {
  return api.get<Project>(`/api/projects/${projectId}`);
}

export async function createProject(payload: ProjectPayload): Promise<Project> {
  return api.post<Project>("/api/projects", payload);
}

export async function updateProject(
  projectId: number,
  payload: Partial<ProjectPayload>,
): Promise<Project> {
  return api.put<Project>(`/api/projects/${projectId}`, payload);
}

export async function deleteProject(projectId: number): Promise<void> {
  await api.delete(`/api/projects/${projectId}`);
}
