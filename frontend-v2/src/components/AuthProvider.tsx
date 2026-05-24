"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import {
  getCurrentUser,
  login as loginApi,
  logout as logoutApi,
  register as registerApi,
  type AuthUser,
  type LoginPayload,
  type RegisterPayload,
} from "@/lib/api/auth";

interface AuthContextValue {
  user: AuthUser | null;
  checked: boolean;
  loading: boolean;
  isAuthenticated: boolean;
  displayName: string;
  login: (payload: LoginPayload) => Promise<AuthUser>;
  register: (payload: RegisterPayload) => Promise<AuthUser>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [checked, setChecked] = useState(false);
  const [loading, setLoading] = useState(false);

  const loadCurrentUser = useCallback(async () => {
    if (checked && user) return user;
    setLoading(true);
    try {
      const session = await getCurrentUser();
      setUser(session.user);
      return session.user;
    } catch {
      setUser(null);
      return null;
    } finally {
      setChecked(true);
      setLoading(false);
    }
  }, [checked, user]);

  useEffect(() => {
    loadCurrentUser();
  }, [loadCurrentUser]);

  const login = useCallback(async (payload: LoginPayload) => {
    const session = await loginApi(payload);
    setUser(session.user);
    setChecked(true);
    return session.user;
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    const session = await registerApi(payload);
    setUser(session.user);
    setChecked(true);
    return session.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutApi();
    } finally {
      setUser(null);
      setChecked(true);
    }
  }, []);

  const value: AuthContextValue = {
    user,
    checked,
    loading,
    isAuthenticated: Boolean(user),
    displayName: user?.display_name || user?.username || "未登录",
    login,
    register,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  );
}
