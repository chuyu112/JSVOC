"use client";

import { useState, useRef } from "react";
import { motion } from "framer-motion";

interface TranscriptSegment {
  id: number;
  start: number;
  end: number;
  text: string;
}

interface TranscriptResult {
  text: string;
  segments: TranscriptSegment[];
  duration: number;
  language: string;
  meta?: { title: string; author: string; cover_url: string };
}

export default function AsrPage() {
  const [mode, setMode] = useState<"url" | "upload">("url");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [result, setResult] = useState<TranscriptResult | null>(null);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // ── Upload handlers ──────────────────────────────────────
  function handleDrag(e: React.DragEvent) {
    e.preventDefault(); e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") setDragActive(true);
    else if (e.type === "dragleave") setDragActive(false);
  }
  function handleDrop(e: React.DragEvent) {
    e.preventDefault(); e.stopPropagation(); setDragActive(false);
    if (e.dataTransfer.files?.[0]) { setFile(e.dataTransfer.files[0]); setResult(null); setError(""); }
  }
  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files?.[0]) { setFile(e.target.files![0]); setResult(null); setError(""); }
  }

  // ── Transcribe ──────────────────────────────────────────
  async function handleTranscribeUrl() {
    if (!url.trim()) return;
    setTranscribing(true); setError("");
    try {
      const resp = await fetch("/api/asr/transcribe-url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim(), language: "zh" }),
        credentials: "include",
      });
      const json = await resp.json();
      if (!json.success) throw new Error(json.message || "转写失败");
      setResult(json.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "转写失败");
    } finally { setTranscribing(false); }
  }

  async function handleTranscribeFile() {
    if (!file) return;
    setTranscribing(true); setError("");
    try {
      const fd = new FormData();
      fd.append("file", file); fd.append("language", "zh");
      const resp = await fetch("/api/asr/transcribe", { method: "POST", body: fd, credentials: "include" });
      const json = await resp.json();
      if (!json.success) throw new Error(json.message || "转写失败");
      setResult(json.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "转写失败");
    } finally { setTranscribing(false); }
  }

  function handleCopy() {
    if (!result) return;
    navigator.clipboard.writeText(result.text).then(() => alert("已复制文案"));
  }

  return (
    <section className="page-section">
      <motion.div
        initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="section-header"
      >
        <div>
          <p className="eyebrow">ASR</p>
          <h1 className="text-[28px] md:text-[36px] font-bold leading-[1.15] tracking-[-0.02em] text-[#f5f5f5]">
            视频转文字
          </h1>
        </div>
      </motion.div>

      {/* Mode Switch */}
      <div className="flex gap-1 mb-4 bg-[rgba(255,255,255,0.04)] rounded-lg p-1 w-fit">
        <button
          onClick={() => setMode("url")}
          className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
            mode === "url" ? "bg-[#5a9b82] text-white" : "text-[#9ca3af] hover:text-[#f5f5f5]"
          }`}
        >
          粘贴链接
        </button>
        <button
          onClick={() => setMode("upload")}
          className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
            mode === "upload" ? "bg-[#5a9b82] text-white" : "text-[#9ca3af] hover:text-[#f5f5f5]"
          }`}
        >
          上传文件
        </button>
      </div>

      {/* URL Mode */}
      {mode === "url" && (
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="glass p-6 rounded-[1rem] mb-6">
          <div className="flex gap-3">
            <input
              type="text"
              value={url}
              onChange={(e) => { setUrl(e.target.value); setResult(null); setError(""); }}
              placeholder="粘贴抖音视频链接..."
              className="flex-1 bg-[rgba(255,255,255,0.06)] border border-[rgba(255,255,255,0.1)] rounded-lg px-4 py-3 text-[#f5f5f5] text-sm outline-none focus:border-[#5a9b82]"
            />
            <button onClick={handleTranscribeUrl} disabled={transcribing || !url.trim()} className="btn btn-primary shrink-0">
              {transcribing ? "转写中..." : "开始转写"}
            </button>
          </div>
          <p className="text-xs text-[#9ca3af] mt-2">支持抖音分享链接，系统自动下载视频并转文字</p>
        </motion.div>
      )}

      {/* Upload Mode */}
      {mode === "upload" && (
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="glass p-6 rounded-[1rem] mb-6">
          <div
            className={`border-2 border-dashed rounded-[0.75rem] p-8 text-center transition-all cursor-pointer ${
              dragActive ? "border-[#5a9b82] bg-[rgba(90,155,130,0.08)]" : "border-[rgba(255,255,255,0.1)] hover:border-[rgba(255,255,255,0.2)]"
            }`}
            onDragEnter={handleDrag} onDragLeave={handleDrag} onDragOver={handleDrag} onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
          >
            <input ref={inputRef} type="file" accept="video/*,audio/*" onChange={handleChange} className="hidden" />
            <div className="text-4xl mb-3">{file ? "📄" : "📁"}</div>
            <p className="text-[#f5f5f5] font-medium mb-1">{file ? file.name : "点击或拖拽上传视频/音频"}</p>
            <p className="text-sm text-[#9ca3af]">支持 mp4, mov, wav, mp3 等格式</p>
          </div>
          {file && (
            <div className="mt-4 flex gap-3">
              <button onClick={handleTranscribeFile} disabled={transcribing} className="btn btn-primary flex-1">{transcribing ? "转写中..." : "开始转写"}</button>
              <button onClick={() => { setFile(null); setResult(null); }} className="btn btn-outline">清除</button>
            </div>
          )}
        </motion.div>
      )}

      {error && (
        <div className="mb-6 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-200 text-sm">{error}</div>
      )}

      {/* Result */}
      {result && (
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="glass p-6 rounded-[1rem]">
          {result.meta && (
            <div className="flex items-center gap-3 mb-4 pb-4 border-b border-[rgba(255,255,255,0.06)]">
              {result.meta.cover_url && <img src={result.meta.cover_url} alt="" className="w-12 h-12 rounded object-cover" />}
              <div>
                <div className="font-bold text-[#f5f5f5]">{result.meta.title?.slice(0, 60)}</div>
                <div className="text-xs text-[#9ca3af]">@{result.meta.author}</div>
              </div>
            </div>
          )}
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-[#f5f5f5]">转写结果</h3>
            <div className="flex gap-2">
              <span className="text-xs text-[#9ca3af] bg-[rgba(255,255,255,0.06)] px-2 py-1 rounded">{result.language}</span>
              <span className="text-xs text-[#9ca3af] bg-[rgba(255,255,255,0.06)] px-2 py-1 rounded">{result.duration.toFixed(1)}s</span>
              <button onClick={handleCopy} className="btn btn-sm btn-outline">复制</button>
            </div>
          </div>
          <div className="bg-[rgba(0,0,0,0.2)] rounded-lg p-4 mb-4 max-h-[300px] overflow-y-auto">
            <p className="text-[#f5f5f5] leading-relaxed whitespace-pre-wrap">{result.text}</p>
          </div>
          <details className="text-sm">
            <summary className="text-[#9ca3af] cursor-pointer hover:text-[#f5f5f5]">查看时间戳 ({result.segments.length} 段)</summary>
            <div className="mt-2 space-y-1 max-h-[200px] overflow-y-auto">
              {result.segments.map((seg) => (
                <div key={seg.id} className="flex gap-2 text-xs text-[#9ca3af] py-1 border-b border-[rgba(255,255,255,0.04)]">
                  <span className="shrink-0 w-16 text-right">{seg.start.toFixed(1)}s</span>
                  <span className="text-[#f5f5f5]">{seg.text}</span>
                </div>
              ))}
            </div>
          </details>
        </motion.div>
      )}
    </section>
  );
}
