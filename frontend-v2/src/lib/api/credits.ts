import { api } from "./client";

export interface CreditAccount {
  user_id: number;
  balance: number;
  total_granted: number;
  total_spent: number;
  created_at: string;
  updated_at: string;
}

export interface CreditPackage {
  credits: number;
  price_yuan: number;
  title: string;
}

export async function getCreditBalance(): Promise<CreditAccount> {
  return api.get<CreditAccount>("/api/credits/balance");
}

export async function getCreditPackages(): Promise<CreditPackage[]> {
  return api.get<CreditPackage[]>("/api/credits/packages");
}
