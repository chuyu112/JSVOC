import { api } from "./client";

export interface AuthUser {
  id: number;
  display_name: string;
  username: string | null;
  email: string | null;
  is_active: boolean;
  created_at: string;
  credit_balance: number;
}

export interface AuthSession {
  user: AuthUser;
}

export interface LoginPayload {
  login: string;
  password: string;
}

export interface RegisterPayload {
  display_name: string;
  username: string;
  email: string;
  password: string;
}

export async function getCurrentUser(): Promise<AuthSession> {
  return api.get<AuthSession>("/api/auth/me", {
    timeoutMs: 5000,
    redirectOnUnauthorized: false,
  });
}

export async function login(payload: LoginPayload): Promise<AuthSession> {
  return api.post<AuthSession>("/api/auth/login", payload, { timeoutMs: 15000 });
}

export async function register(payload: RegisterPayload): Promise<AuthSession> {
  return api.post<AuthSession>("/api/auth/register", payload, { timeoutMs: 15000 });
}

export async function logout(): Promise<void> {
  await api.post("/api/auth/logout", undefined, { timeoutMs: 10000 });
}
