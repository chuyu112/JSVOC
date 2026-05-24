"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { listGenerationRecords, formatModuleName, type GenerationRecord } from "@/lib/api/generationRecords";

const moduleOptions = [
  { label: "全部模块", value: "" },
  { label: "账号包装", value: "account_package" },
  { label: "执行计划", value: "execution_plan" },
  { label: "选题生成", value: "topics" },
  { label: "文案生成", value: "script" },
  { label: "AI聊天", value: "ai_chat" },
];

function formatTime(value: string) {
  return new Date(value).toLocaleString();
}

function formatCompactTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${month}/${day} ${hours}:${minutes}`;
}

function formatLatencySeconds(value: number | null | undefined) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "-";
  const seconds = value / 1000;
  const formatted = seconds >= 10 ? seconds.toFixed(0) : seconds.toFixed(1);
  return `${formatted} 秒`;
}

function formatProvider(value: string | null | undefined) {
  if (value === "openai_compatible") return "OpenAI";
  return (value || "").slice(0, 12);
}

function formatModel(value: string | null | undefined) {
  return (value || "").slice(0, 14);
}

function moduleTagClass(module: string) {
  if (module === "account_package") return "bg-[rgba(124,58,237,0.15)] text-[#8b5cf6]";
  if (module === "execution_plan") return "bg-[rgba(90,155,130,0.15)] text-[#4a856e]";
  if (module === "topics") return "bg-[rgba(249,115,22,0.15)] text-[#ea580c]";
  if (module === "script") return "bg-[rgba(14,165,233,0.15)] text-[#0284c7]";
  if (module === "ai_chat") return "bg-[rgba(255,255,255,0.08)] text-[#f5f5f5]";
  return "bg-[rgba(255,255,255,0.06)] text-[#b0b0b0]";
}

function formatJson(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2);
}

export default function HistoryClient({ projectId }: { projectId?: number }) {
  const [records, setRecords] = useState<GenerationRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [moduleName, setModuleName] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [detailById, setDetailById] = useState<Record<number, GenerationRecord>>({});
  const [detailLoadingId, setDetailLoadingId] = useState<number | null>(null);

  async function fetchRecords() {
    setLoading(true);
    try {
      const data = await listGenerationRecords({
        project_id: projectId ?? null,
        module_name: moduleName || null,
        limit: 50,
        offset: 0,
      });
      setRecords(data);
    } catch {
      setRecords([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchRecords();
  }, [moduleName, projectId]);

  async function loadDetail(record: GenerationRecord) {
    if (expandedId === record.id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(record.id);
    if (detailById[record.id]) return;
    setDetailLoadingId(record.id);
    try {
      // Reuse the list data as detail for now; individual GET endpoint exists if needed
      setDetailById((prev) => ({ ...prev, [record.id]: record }));
    } finally {
      setDetailLoadingId(null);
    }
  }

  async function copyText(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      alert("已复制");
    } catch {
      alert("复制失败");
    }
  }

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
        className="overview-strip mb-6"
      >
        <div className="overview-item">
          <span>记录数</span>
          <strong>{records.length}</strong>
        </div>
        <div className="overview-item">
          <span>模块数</span>
          <strong>{new Set(records.map((r) => r.module_name)).size}</strong>
        </div>
        <div className="overview-item">
          <span>最近</span>
          <strong>{records[0] ? formatCompactTime(records[0].created_at) : "-"}</strong>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.15 }}
        className="history-filter-panel glass p-4 mb-6"
      >
        <div className="flex flex-wrap gap-4 items-end">
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-[540] text-[#9ca3af]">模块类型</label>
            <select
              className="input-glass appearance-none cursor-pointer"
              value={moduleName}
              onChange={(e) => setModuleName(e.target.value)}
            >
              {moduleOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <button onClick={fetchRecords} disabled={loading} className="btn btn-primary">
            {loading ? "加载中..." : "刷新"}
          </button>
        </div>
      </motion.div>

      {loading ? (
        <div className="history-loading-panel glass p-8">
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-[rgba(255,255,255,0.06)] rounded w-1/3" />
            <div className="h-4 bg-[rgba(255,255,255,0.06)] rounded w-full" />
          </div>
        </div>
      ) : !records.length ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
          className="empty-state"
        >
          <h2 className="text-[21px] font-[680] text-[#f5f5f5] mb-2">暂无生成记录</h2>
          <p className="text-[#9ca3af] text-sm">使用各项目的生成功能后，记录将在此展示。</p>
        </motion.div>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
          className="table-panel"
        >
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[rgba(255,255,255,0.06)] text-[#9ca3af] text-left">
                  <th className="px-4 py-3 w-12">ID</th>
                  <th className="px-4 py-3 w-24">模块</th>
                  <th className="px-4 py-3 w-12">项目</th>
                  <th className="px-4 py-3 w-24">供应商</th>
                  <th className="px-4 py-3 w-28">模型</th>
                  <th className="px-4 py-3 w-20">耗时</th>
                  <th className="px-4 py-3 w-24">时间</th>
                  <th className="px-4 py-3 w-16">详情</th>
                </tr>
              </thead>
              <tbody>
                {records.map((record) => (
                  <>
                    <tr
                      key={record.id}
                      className="border-b border-[rgba(255,255,255,0.04)] hover:bg-[rgba(255,255,255,0.02)] transition-colors cursor-pointer"
                      onClick={() => loadDetail(record)}
                    >
                      <td className="px-4 py-3 text-[#b0b0b0]">{record.id}</td>
                      <td className="px-4 py-3">
                        <span className={`tag text-xs ${moduleTagClass(record.module_name)}`}>
                          {formatModuleName(record.module_name)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-[#b0b0b0]">{record.project_id ?? "-"}</td>
                      <td className="px-4 py-3 text-[#b0b0b0]">{formatProvider(record.model_provider)}</td>
                      <td className="px-4 py-3 text-[#b0b0b0]">{formatModel(record.model_name)}</td>
                      <td className="px-4 py-3 text-[#b0b0b0]">{formatLatencySeconds(record.latency_ms)}</td>
                      <td className="px-4 py-3 text-[#b0b0b0]">{formatCompactTime(record.created_at)}</td>
                      <td className="px-4 py-3">
                        <span className="text-[#5a9b82] text-xs">
                          {expandedId === record.id ? "收起" : "展开"}
                        </span>
                      </td>
                    </tr>
                    {expandedId === record.id && (
                      <tr>
                        <td colSpan={8} className="px-4 py-4">
                          {detailLoadingId === record.id ? (
                            <div className="animate-pulse space-y-2">
                              <div className="h-4 bg-[rgba(255,255,255,0.06)] rounded w-1/3" />
                              <div className="h-4 bg-[rgba(255,255,255,0.06)] rounded w-full" />
                            </div>
                          ) : (
                            <div className="space-y-3">
                              <div className="flex gap-2">
                                <button
                                  onClick={() => copyText(formatJson((detailById[record.id] || record).input_data))}
                                  className="btn btn-ghost text-xs"
                                  style={{ minHeight: 28, padding: "0 10px" }}
                                >
                                  复制 input_data
                                </button>
                                <button
                                  onClick={() => copyText(formatJson((detailById[record.id] || record).output_data))}
                                  className="btn btn-ghost text-xs"
                                  style={{ minHeight: 28, padding: "0 10px" }}
                                >
                                  复制 output_data
                                </button>
                                <button
                                  onClick={() => copyText(formatJson(detailById[record.id] || record))}
                                  className="btn btn-ghost text-xs"
                                  style={{ minHeight: 28, padding: "0 10px" }}
                                >
                                  复制完整 JSON
                                </button>
                              </div>
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="history-detail-panel glass p-4">
                                  <h4 className="text-[12px] text-[#9ca3af] mb-2">input_data</h4>
                                  <pre className="text-[12px] text-[#b0b0b0] whitespace-pre-wrap overflow-auto max-h-[300px]">
                                    {formatJson((detailById[record.id] || record).input_data)}
                                  </pre>
                                </div>
                                <div className="history-detail-panel glass p-4">
                                  <h4 className="text-[12px] text-[#9ca3af] mb-2">output_data</h4>
                                  <pre className="text-[12px] text-[#b0b0b0] whitespace-pre-wrap overflow-auto max-h-[300px]">
                                    {formatJson((detailById[record.id] || record).output_data)}
                                  </pre>
                                </div>
                                <div className="history-detail-panel glass p-4">
                                  <h4 className="text-[12px] text-[#9ca3af] mb-2">token_usage</h4>
                                  <pre className="text-[12px] text-[#b0b0b0] whitespace-pre-wrap overflow-auto max-h-[300px]">
                                    {formatJson((detailById[record.id] || record).token_usage)}
                                  </pre>
                                </div>
                                <div className="history-detail-panel glass p-4">
                                  <h4 className="text-[12px] text-[#9ca3af] mb-2">耗时</h4>
                                  <p className="text-[#b0b0b0]">{formatLatencySeconds((detailById[record.id] || record).latency_ms)}</p>
                                </div>
                              </div>
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      )}
    </>
  );
}
