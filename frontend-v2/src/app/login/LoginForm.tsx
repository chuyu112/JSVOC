"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { useAuth } from "@/components/AuthProvider";

export default function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const auth = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [loginForm, setLoginForm] = useState({
    login: "",
    password: "",
  });

  const [registerForm, setRegisterForm] = useState({
    display_name: "",
    username: "",
    email: "",
    password: "",
  });

  function parseApiError(err: unknown): string {
    const msg = err instanceof Error ? err.message : String(err);
    try {
      const parsed = JSON.parse(msg);
      const detail = parsed.detail;
      if (typeof detail === "string") return detail;
      if (Array.isArray(detail)) {
        const messages = detail
          .map((item: unknown) => {
            if (typeof item === "string") return item;
            if (item && typeof item === "object" && "msg" in item) {
              return String((item as { msg: unknown }).msg);
            }
            return String(item);
          })
          .filter(Boolean);
        return messages.join("；") || msg;
      }
      return parsed.message || msg;
    } catch {
      return msg;
    }
  }

  function redirectTarget() {
    const redirect = searchParams.get("redirect");
    if (!redirect || !redirect.startsWith("/") || redirect.startsWith("//"))
      return "/projects";
    return redirect;
  }

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await auth.login(loginForm);
      router.push(redirectTarget());
    } catch (err) {
      setError(parseApiError(err) || "账号或密码不正确");
    } finally {
      setLoading(false);
    }
  }

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await auth.register(registerForm);
      router.push(redirectTarget());
    } catch (err) {
      setError(parseApiError(err) || "注册失败，请检查用户名或邮箱是否已存在");
    } finally {
      setLoading(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: 40 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1], delay: 0.15 }}
      className="auth-panel"
    >
      <div className="mb-[18px]">
        <p className="eyebrow">Account</p>
        <h1 className="text-2xl font-bold tracking-tight text-[#f5f5f5]">
          {mode === "login" ? "登录" : "注册"}
        </h1>
      </div>

      <div className="w-full mb-[18px] flex rounded-[0.75rem] bg-[rgba(255,255,255,0.04)] p-1">
        <button
          type="button"
          onClick={() => setMode("login")}
          className={`flex-1 py-2 text-sm font-medium rounded-[0.5rem] transition-all ${
            mode === "login"
              ? "bg-[#5a9b82] text-white"
              : "text-[#7a8a82] hover:text-[#f5f5f5]"
          }`}
        >
          登录
        </button>
        <button
          type="button"
          onClick={() => setMode("register")}
          className={`flex-1 py-2 text-sm font-medium rounded-[0.5rem] transition-all ${
            mode === "register"
              ? "bg-[#5a9b82] text-white"
              : "text-[#7a8a82] hover:text-[#f5f5f5]"
          }`}
        >
          注册
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-[0.75rem] bg-[rgba(160,88,88,0.15)] border border-[rgba(160,88,88,0.2)] text-[#c09090] text-sm">
          {error}
        </div>
      )}

      {mode === "login" ? (
        <form onSubmit={handleLogin} className="flex flex-col gap-4">
          <div>
            <label className="block text-xs font-medium text-[#7a8a82] mb-1.5">
              用户名 / 邮箱
            </label>
            <input
              type="text"
              required
              value={loginForm.login}
              onChange={(e) =>
                setLoginForm((p) => ({ ...p, login: e.target.value }))
              }
              className="input-glass w-full"
              placeholder="请输入用户名或邮箱"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-[#7a8a82] mb-1.5">
              密码
            </label>
            <input
              type="password"
              required
              value={loginForm.password}
              onChange={(e) =>
                setLoginForm((p) => ({ ...p, password: e.target.value }))
              }
              className="input-glass w-full"
              placeholder="请输入密码"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary w-full mt-2"
          >
            {loading ? "登录中..." : "登录"}
          </button>
        </form>
      ) : (
        <form onSubmit={handleRegister} className="flex flex-col gap-4">
          <div>
            <label className="block text-xs font-medium text-[#7a8a82] mb-1.5">
              显示名称
            </label>
            <input
              type="text"
              required
              value={registerForm.display_name}
              onChange={(e) =>
                setRegisterForm((p) => ({
                  ...p,
                  display_name: e.target.value,
                }))
              }
              className="input-glass w-full"
              placeholder="请输入显示名称"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-[#7a8a82] mb-1.5">
              用户名
            </label>
            <input
              type="text"
              required
              value={registerForm.username}
              onChange={(e) =>
                setRegisterForm((p) => ({
                  ...p,
                  username: e.target.value,
                }))
              }
              className="input-glass w-full"
              placeholder="请输入用户名"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-[#7a8a82] mb-1.5">
              邮箱
            </label>
            <input
              type="email"
              required
              value={registerForm.email}
              onChange={(e) =>
                setRegisterForm((p) => ({
                  ...p,
                  email: e.target.value,
                }))
              }
              className="input-glass w-full"
              placeholder="请输入邮箱"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-[#7a8a82] mb-1.5">
              密码
            </label>
            <input
              type="password"
              required
              minLength={8}
              value={registerForm.password}
              onChange={(e) =>
                setRegisterForm((p) => ({
                  ...p,
                  password: e.target.value,
                }))
              }
              className="input-glass w-full"
              placeholder="请输入密码"
            />
            <p className="text-[11px] text-[#6b7280] mt-1">
              密码至少 8 位，需同时包含英文字母和数字
            </p>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary w-full mt-2"
          >
            {loading ? "注册中..." : "注册"}
          </button>
        </form>
      )}
    </motion.div>
  );
}
