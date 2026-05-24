"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";

const themes = [
  { key: "yang", label: "阳绿", dot: "#5a9b82", desc: "鲜亮明快，生机勃勃" },
  { key: "imperial", label: "帝王绿", dot: "#3a6b5a", desc: "深沉华贵，顶级翡翠" },
  { key: "apple", label: "苹果绿", dot: "#6aaa92", desc: "清新自然，水润透亮" },
  { key: "lavender", label: "紫罗兰", dot: "#8a7ab0", desc: "浪漫神秘，春色翡翠" },
  { key: "yellow", label: "黄翡", dot: "#b8985a", desc: "温暖富贵，金玉满堂" },
  { key: "red", label: "红翡", dot: "#b86868", desc: "热烈奔放，鸿运当头" },
  { key: "black", label: "墨翠", dot: "#b8a060", desc: "黑金相映，低调奢华" },
];

export default function SettingsPage() {
  const router = useRouter();
  const auth = useAuth();
  const [saved, setSaved] = useState("yang");
  const [current, setCurrent] = useState("yang");
  const [savedFlag, setSavedFlag] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("jade-theme");
    const initial = stored && themes.some((t) => t.key === stored) ? stored : "yang";
    const frame = requestAnimationFrame(() => {
      setSaved(initial);
      setCurrent(initial);
    });
    return () => cancelAnimationFrame(frame);
  }, []);

  function select(key: string) {
    setCurrent(key);
  }

  function handleSave() {
    localStorage.setItem("jade-theme", current);
    document.documentElement.dataset.theme = current === "yang" ? "" : current;
    setSaved(current);
    setSavedFlag(true);

    const params = new URLSearchParams(window.location.search);
    const returnTo = params.get("returnTo");
    if (returnTo && returnTo.startsWith("/") && !returnTo.startsWith("//") && returnTo !== "/settings") {
      router.push(returnTo);
      return;
    }

    if (window.history.length > 1) {
      router.back();
      return;
    }

    router.push("/projects");
  }

  async function handleLogout() {
    await auth.logout();
    router.push("/login");
  }

  return (
    <section className="page-section">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="section-header"
      >
        <div>
          <p className="eyebrow">Preferences</p>
          <h1 className="text-[28px] md:text-[36px] font-bold leading-[1.15] tracking-[-0.02em] text-[#f5f5f5]">
            用户设置
          </h1>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
        className="glass rounded-[1rem] p-6 md:p-8 max-w-[720px]"
      >
        <h2 className="text-[18px] font-[680] text-[#f5f5f5] mb-6">外观主题</h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {themes.map((t) => (
            <button
              key={t.key}
              onClick={() => select(t.key)}
              className={`flex items-center gap-3 w-full p-3 rounded-[0.75rem] border text-left transition-all duration-200 ${
                current === t.key
                  ? "border-[var(--jade-primary)] bg-[rgba(90,155,130,0.1)]"
                  : "border-[rgba(255,255,255,0.06)] bg-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.06)]"
              }`}
            >
              <span
                className="shrink-0 block w-8 h-8 rounded-full border-2"
                style={{
                  background: t.dot,
                  borderColor: current === t.key ? "#ffffff" : "rgba(255,255,255,0.15)",
                  boxShadow: current === t.key ? `0 0 12px ${t.dot}` : "none",
                }}
              />
              <div className="min-w-0">
                <div className="text-[14px] font-[620] text-[#f5f5f5]">{t.label}</div>
                <div className="text-[12px] text-[#6b7280] mt-0.5">{t.desc}</div>
              </div>
              {current === t.key && (
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="ml-auto shrink-0"
                  style={{ color: "var(--jade-primary)" }}
                >
                  <path d="M20 6L9 17l-5-5" />
                </svg>
              )}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3 mt-6">
          <button
            onClick={handleSave}
            disabled={current === saved}
            className="metal-btn metal-btn-primary text-sm disabled:opacity-40 disabled:cursor-not-allowed"
          >
            保存主题
          </button>
          {savedFlag && (
            <span className="text-[13px] text-[#7fdc92]">已保存</span>
          )}
        </div>

        <div className="mt-8 border-t border-[rgba(255,255,255,0.06)] pt-6">
          <h2 className="text-[18px] font-[680] text-[#f5f5f5] mb-3">账号操作</h2>
          <button
            type="button"
            onClick={handleLogout}
            className="metal-btn text-sm"
          >
            退出登录
          </button>
        </div>
      </motion.div>
    </section>
  );
}
