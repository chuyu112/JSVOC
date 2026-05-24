"use client";

import { useState, useEffect } from "react";

const themes = [
  { key: "yang", label: "阳绿", dot: "#7fdc92" },
  { key: "imperial", label: "帝王绿", dot: "#1f5a3c" },
  { key: "apple", label: "苹果绿", dot: "#8fcca8" },
  { key: "lavender", label: "紫罗兰", dot: "#8a7ab0" },
  { key: "yellow", label: "黄翡", dot: "#b8985a" },
  { key: "red", label: "红翡", dot: "#b86868" },
  { key: "black", label: "墨翠", dot: "#b8a060" },
];

export default function ThemeSwitcher() {
  const [open, setOpen] = useState(false);
  const [current, setCurrent] = useState("yang");

  useEffect(() => {
    const saved = localStorage.getItem("jade-theme");
    const initial = saved && themes.some((t) => t.key === saved) ? saved : "yang";
    setCurrent(initial);
    document.documentElement.dataset.theme = initial === "yang" ? "" : initial;
  }, []);

  function select(key: string) {
    setCurrent(key);
    setOpen(false);
    localStorage.setItem("jade-theme", key);
    document.documentElement.dataset.theme = key === "yang" ? "" : key;
  }

  const active = themes.find((t) => t.key === current) || themes[0];

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1.5 min-h-[32px] px-2.5 rounded-[0.75rem] border text-[12px] font-medium transition-all"
        style={{
          borderColor: "var(--jade-border)",
          background: "var(--jade-bg-card)",
          color: "var(--jade-text-sub)",
        }}
      >
        <span
          className="block w-2.5 h-2.5 rounded-full"
          style={{ background: active.dot }}
        />
        {active.label}
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="opacity-60">
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>

      {open && (
        <div
          className="absolute right-0 top-[calc(100%+6px)] z-50 min-w-[120px] rounded-[0.75rem] overflow-hidden"
          style={{
            background: "var(--jade-bg-card-strong)",
            backdropFilter: "blur(24px)",
            border: "1px solid var(--jade-border)",
            boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
          }}
        >
          {themes.map((t) => (
            <button
              key={t.key}
              onClick={() => select(t.key)}
              className="flex items-center gap-2 w-full px-3 py-2 text-[13px] font-medium transition-colors hover:bg-[rgba(255,255,255,0.04)]"
              style={{
                color: current === t.key ? "var(--jade-text-main)" : "var(--jade-text-sub)",
              }}
            >
              <span
                className="block w-2.5 h-2.5 rounded-full"
                style={{ background: t.dot }}
              />
              {t.label}
              {current === t.key && (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="ml-auto" style={{ color: "var(--jade-primary)" }}>
                  <path d="M20 6L9 17l-5-5" />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}

      {open && (
        <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
      )}
    </div>
  );
}
