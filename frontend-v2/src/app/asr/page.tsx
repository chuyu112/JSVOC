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
}

export default function AsrPage() {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [result, setResult] = useState<TranscriptResult | null>(null);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  function handleDrag(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) {
      setFile(e.dataTransfer.files[0]);
      setResult(null);
      setError("");
    }
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files?.[0]) {
      setFile(e.target.files[0]);
      setResult(null);
      setError("");
    }
  }

  async function handleTranscribe() {
    if (!file) return;
    setTranscribing(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("language", "zh");

      const resp = await fetch("/api/asr/transcribe", {
        method: "POST",
        body: formData,
        credentials: "include",
      });
      const json = await resp.json();
      if (!json.success) {
        throw new Error(json.message || "转写失败");
      }
      setResult(json.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "转写失败");
    } finally {
      setTranscribing(false);
    }
  }

  function handleCopy() {
    if (!result) return;
    navigator.clipboard.writeText(result.text).then(() => {
      alert("已复制文案");
    });
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
          <p className="eyebrow">ASR</p>
          <h1 className="text-[28px] md:text-[36px] font-bold leading-[1.15] tracking-[-0.02em] text-[#f5f5f5]">
            视频转文字
          </h1>
        </div>
      </motion.div>

      {/* Upload Area */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className="glass p-6 rounded-[1rem] mb-6"
      >
        <div
          className={`border-2 border-dashed rounded-[0.75rem] p-8 text-center transition-all cursor-pointer ${
            dragActive
              ? "border-[#5a9b82] bg-[rgba(90,155,130,0.08)]"
              : "border-[rgba(255,255,255,0.1)] hover:border-[rgba(255,255,255,0.2)]"
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept="video/*,audio/*"
            onChange={handleChange}
            className="hidden"
          />
          <div className="text-4xl mb-3">📁</div>
          <p className="text-[#f5f5f5] font-medium mb-1">
            {file ? file.name : "点击或拖拽上传视频/音频"}
          </p>
          <p className="text-sm text-[#9ca3af]">
            支持 mp4, mov, wav, mp3 等格式
          </p>
        </div>

        {file && (
          <div className="mt-4 flex gap-3">
            <button
              onClick={handleTranscribe}
              disabled={transcribing}
              className="btn btn-primary flex-1"
            >
              {transcribing ? "转写中..." : "开始转写"}
            </button>
            <button
              onClick={() => {
                setFile(null);
                setResult(null);
              }}
              className="btn btn-outline"
            >
              清除
            </button>
          </div>
        )}

        {error && (
          <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-200 text-sm">
            {error}
          </div>
        )}
      </motion.div>

      {/* Result */}
      {result && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass p-6 rounded-[1rem]"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-[#f5f5f5]">转写结果</h3>
            <div className="flex gap-2">
              <span className="text-xs text-[#9ca3af] bg-[rgba(255,255,255,0.06)] px-2 py-1 rounded">
                {result.language}
              </span>
              <span className="text-xs text-[#9ca3af] bg-[rgba(255,255,255,0.06)] px-2 py-1 rounded">
                {result.duration.toFixed(1)}s
              </span>
              <button onClick={handleCopy} className="btn btn-sm btn-outline">
                复制
              </button>
            </div>
          </div>

          <div className="bg-[rgba(0,0,0,0.2)] rounded-lg p-4 mb-4 max-h-[300px] overflow-y-auto">
            <p className="text-[#f5f5f5] leading-relaxed whitespace-pre-wrap">
              {result.text}
            </p>
          </div>

          <details className="text-sm">
            <summary className="text-[#9ca3af] cursor-pointer hover:text-[#f5f5f5]">
              查看时间戳 ({result.segments.length} 段)
            </summary>
            <div className="mt-2 space-y-1 max-h-[200px] overflow-y-auto">
              {result.segments.map((seg) => (
                <div
                  key={seg.id}
                  className="flex gap-2 text-xs text-[#9ca3af] py-1 border-b border-[rgba(255,255,255,0.04)]"
                >
                  <span className="shrink-0 w-16 text-right">
                    {seg.start.toFixed(1)}s
                  </span>
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
