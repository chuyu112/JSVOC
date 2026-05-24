"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "@phosphor-icons/react";
import { api } from "@/lib/api/client";
import { enhancePrompt, generateVideoAsync, listVideoModels, type VideoModelConfig } from "@/lib/api/videos";
import { formatVideoCreditEstimate } from "@/lib/videoCost";
import TypingIndicator from "@/components/ui/TypingIndicator";

interface TaskStatus {
  id: number;
  status: "queued" | "running" | "succeeded" | "failed";
  result_data: Record<string, unknown> | null;
  error_message: string | null;
}

function formatVideoTaskError(message: string | null | undefined) {
  const text = message || '视频生成失败，请稍后重试。';
  const lowerText = text.toLowerCase();
  if (
    text.includes('InputImageSensitiveContentDetected.PrivacyInformation') ||
    lowerText.includes('input image may contain real person') ||
    text.includes('输入参考图疑似包含真实人物或隐私信息')
  ) {
    return '参考图未通过火山审核：输入参考图疑似包含真实人物或隐私信息。任务已停止，积分已自动退回。请更换无真实人物、无隐私信息的参考图，或先用生图生成非真人分镜图后再生视频。';
  }
  if (lowerText.includes('copyright restrictions') || text.includes('版权限制')) {
    return '输出视频未通过火山审核：可能涉及版权限制。任务已停止，积分已自动退回。请换用更通用的描述，避免品牌、明星或受版权保护的画面。';
  }
  return text;
}

interface ReferenceMedia {
  id: string;
  name: string;
  dataUrl: string;
  type: "图片" | "视频" | "音频";
}

interface VideoOptions {
  model: string;
  ratio: string;
  resolution: string;
  duration_mode: "seconds" | "smart";
  duration_seconds: number;
  count: number;
  with_sound: boolean;
  seed: number;
  web_search: boolean;
  timeout_hours: number;
}

const SEEDANCE_STANDARD_MODEL = "doubao-seedance-2-0-260128";
const SEEDANCE_FAST_MODEL = "doubao-seedance-2-0-fast-260128";
const FALLBACK_VIDEO_MODELS: VideoModelConfig[] = [
  {
    key: "seedance-2.0",
    label: "Seedance 2.0",
    value: SEEDANCE_STANDARD_MODEL,
    kind: "standard",
    resolutions: ["480p", "720p", "1080p"],
    pricing_yuan_per_second: { "480p": 7 / 15, "720p": 1, "1080p": 37 / 15 },
    available: true,
  },
  {
    key: "seedance-2.0-fast",
    label: "Seedance 2.0 Fast",
    value: SEEDANCE_FAST_MODEL,
    kind: "fast",
    resolutions: ["480p", "720p"],
    pricing_yuan_per_second: { "480p": 5.6 / 15, "720p": 12 / 15 },
    available: true,
  },
];

const defaultOptions: VideoOptions = {
  model: SEEDANCE_STANDARD_MODEL,
  ratio: "9:16",
  resolution: "480p",
  duration_mode: "seconds",
  duration_seconds: 10,
  count: 1,
  with_sound: false,
  seed: -1,
  web_search: false,
  timeout_hours: 24,
};

const RATIOS = ["21:9", "16:9", "4:3", "1:1", "3:4", "9:16"];
const RESOLUTION_LABELS: Record<string, string> = {
  "480p": "480p",
  "720p": "720p",
  "1080p": "1080p",
};

function estimateCost(options: VideoOptions, models: VideoModelConfig[]): string {
  const modelPrices =
    models.find((model) => model.value === options.model)?.pricing_yuan_per_second ||
    FALLBACK_VIDEO_MODELS[0].pricing_yuan_per_second;
  const duration = options.duration_mode === "smart" ? 5 : options.duration_seconds;
  return formatVideoCreditEstimate(modelPrices[options.resolution] || 1, duration, options.count);
}

function getMediaType(file: File): ReferenceMedia["type"] | null {
  if (file.type.startsWith("image/")) return "图片";
  if (file.type.startsWith("video/")) return "视频";
  if (file.type.startsWith("audio/")) return "音频";
  return null;
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

export default function VideosEntryPage() {
  const [prompt, setPrompt] = useState("");
  const [referenceMedias, setReferenceMedias] = useState<ReferenceMedia[]>([]);
  const [task, setTask] = useState<TaskStatus | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [enhancing, setEnhancing] = useState(false);
  const [error, setError] = useState("");
  const [videoModels, setVideoModels] = useState<VideoModelConfig[]>(FALLBACK_VIDEO_MODELS);
  const [options, setOptions] = useState<VideoOptions>(defaultOptions);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const availableVideoModels = videoModels.filter((model) => model.available);
  const selectableVideoModels = availableVideoModels.length > 0 ? availableVideoModels : FALLBACK_VIDEO_MODELS;
  const selectedVideoModel =
    selectableVideoModels.find((model) => model.value === options.model) || selectableVideoModels[0];
  const selectedResolutions = selectedVideoModel.resolutions.length > 0 ? selectedVideoModel.resolutions : ["480p"];
  const isRunning = submitting || task?.status === "queued" || task?.status === "running";
  const videoUrl = task?.result_data?.video_url as string | undefined;

  useEffect(() => {
    let cancelled = false;
    listVideoModels()
      .then((models) => {
        if (cancelled || models.length === 0) return;
        const enabled = models.filter((model) => model.available);
        const nextModels = enabled.length > 0 ? models : FALLBACK_VIDEO_MODELS;
        setVideoModels(nextModels);
        setOptions((prev) => {
          const current = nextModels.find((model) => model.available && model.value === prev.model);
          const firstEnabled = nextModels.find((model) => model.available) || FALLBACK_VIDEO_MODELS[0];
          const model = current || firstEnabled;
          return {
            ...prev,
            model: model.value,
            resolution: model.resolutions.includes(prev.resolution) ? prev.resolution : model.resolutions[0] || "480p",
          };
        });
      })
      .catch(() => setVideoModels(FALLBACK_VIDEO_MODELS));
    return () => {
      cancelled = true;
    };
  }, []);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback((taskId: number) => {
    stopPolling();
    const pollOnce = async () => {
      try {
        const res = await api.get<TaskStatus>('/api/generation-tasks/' + taskId);
        setTask(res);
        if (res.status === 'succeeded' || res.status === 'failed') {
          stopPolling();
          if (res.status === 'failed') {
            alert(formatVideoTaskError(res.error_message));
          }
        }
      } catch {
        // Keep polling through transient network/proxy errors.
      }
    };
    void pollOnce();
    pollRef.current = setInterval(pollOnce, 1500);
  }, [stopPolling]);

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  function updateOption<K extends keyof VideoOptions>(key: K, value: VideoOptions[K]) {
    setOptions((prev) => {
      const next = { ...prev, [key]: value };
      if (key === "model" && typeof value === "string") {
        const model = selectableVideoModels.find((item) => item.value === value);
        if (model && !model.resolutions.includes(prev.resolution)) {
          next.resolution = model.resolutions[0] || "480p";
        }
      }
      return next;
    });
  }

  async function handleReferenceUpload(files: FileList | null) {
    if (!files) return;
    const next: ReferenceMedia[] = [];
    for (const file of Array.from(files)) {
      const type = getMediaType(file);
      if (!type) continue;
      const dataUrl = await readFileAsDataUrl(file);
      next.push({
        id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
        name: `${type}${referenceMedias.filter((item) => item.type === type).length + next.filter((item) => item.type === type).length + 1}`,
        type,
        dataUrl,
      });
    }
    if (next.length) setReferenceMedias((prev) => [...prev, ...next]);
  }

  function removeReferenceMedia(id: string) {
    setReferenceMedias((prev) => prev.filter((item) => item.id !== id));
  }

  async function handleEnhance() {
    if (!prompt.trim() || enhancing) return;
    setEnhancing(true);
    setError("");
    try {
      const res = await enhancePrompt({ prompt: prompt.trim() });
      if (res.enhanced_prompt) setPrompt(res.enhanced_prompt);
    } catch (err) {
      setError(err instanceof Error ? err.message : "提示词优化失败");
    } finally {
      setEnhancing(false);
    }
  }

  function clearComposer() {
    setPrompt("");
    setReferenceMedias([]);
    setTask(null);
    setError("");
    stopPolling();
  }

  async function handleSubmit() {
    if (!prompt.trim()) {
      alert("请输入视频生成提示词");
      return;
    }

    setSubmitting(true);
    setTask(null);
    setError("");
    stopPolling();
    try {
      const apiOptions: Record<string, unknown> = {
        model: options.model,
        mode: "reference",
        ratio: options.ratio,
        resolution: options.resolution,
        duration_mode: options.duration_mode,
        duration_seconds: options.duration_mode === "seconds" ? options.duration_seconds : undefined,
        count: options.count,
        generate_audio: options.with_sound,
        seed: options.seed,
        web_search: options.web_search,
        timeout_hours: options.timeout_hours,
      };
      if (referenceMedias.length > 0) {
        apiOptions.reference_images = referenceMedias.filter((m) => m.type === "图片").map((m) => m.dataUrl);
        apiOptions.reference_videos = referenceMedias.filter((m) => m.type === "视频").map((m) => m.dataUrl);
        apiOptions.reference_audios = referenceMedias.filter((m) => m.type === "音频").map((m) => m.dataUrl);
      }

      const res = await generateVideoAsync(null, prompt.trim(), apiOptions);
      setTask({ id: res.task_id, status: res.status as TaskStatus["status"], result_data: null, error_message: null });
      startPolling(res.task_id);
    } catch (err) {
      setError(formatVideoTaskError(err instanceof Error ? err.message : "提交失败"));
    } finally {
      setSubmitting(false);
    }
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
          <p className="eyebrow">Video Generation</p>
          <h1 className="text-[28px] md:text-[36px] font-bold leading-[1.15] tracking-[-0.02em] text-[#f5f5f5]">
            AI视频生成
          </h1>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-5">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.05 }}
          className="glass card-hover p-5"
        >
          <div className="flex flex-col gap-4">
            <div>
              <label className="text-[12px] font-[540] text-[#9ca3af] mb-1.5 block">提示词</label>
              <textarea
                className="input-glass w-full min-h-[180px] resize-y leading-7"
                placeholder="输入视频生成提示词"
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
              />
            </div>

            <input
              ref={fileInputRef}
              type="file"
              accept="image/*,video/*,audio/*"
              multiple
              className="hidden"
              onChange={(event) => {
                handleReferenceUpload(event.target.files);
                event.target.value = "";
              }}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="min-h-[54px] border border-dashed border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.02)] text-[13px] font-[620] text-[#9ca3af] transition-colors hover:bg-[rgba(255,255,255,0.04)]"
            >
              上传图片 / 视频 / 音频参考
            </button>

            {referenceMedias.length > 0 && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {referenceMedias.map((media) => (
                  <div key={media.id} className="flat-delete-target border border-[rgba(255,255,255,0.06)] bg-[rgba(255,255,255,0.03)] p-2">
                    <button
                      onClick={() => removeReferenceMedia(media.id)}
                      className="flat-delete-action"
                      title="删除"
                      aria-label="删除参考素材"
                    >
                      <X size={13} weight="bold" />
                    </button>
                    {media.type === "图片" ? (
                      <img src={media.dataUrl} alt={media.name} className="h-20 w-full object-cover" />
                    ) : media.type === "视频" ? (
                      <video src={media.dataUrl} className="h-20 w-full object-cover" muted />
                    ) : (
                      <div className="h-20 flex items-center justify-center text-[12px] text-[#9ca3af]">音频</div>
                    )}
                    <div className="mt-1 text-[11px] text-[#9ca3af]">{media.name}</div>
                  </div>
                ))}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1">
              <button
                onClick={clearComposer}
                className="video-action-btn video-action-btn-secondary"
                type="button"
              >
                全部清空
              </button>
              <button
                onClick={handleEnhance}
                disabled={enhancing || isRunning}
                className="video-action-btn video-action-btn-secondary"
                type="button"
              >
                {enhancing ? "优化中" : "提示词优化"}
              </button>
              <button
                onClick={handleSubmit}
                disabled={isRunning}
                className="video-action-btn video-action-btn-send"
                type="button"
              >
                {isRunning ? "生成中" : "发送生成"}
              </button>
            </div>
          </div>

          {error && (
            <div className="mt-4 border-l-4 border-l-red-500 bg-[rgba(160,45,45,0.08)] p-4">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          {(task?.status === "queued" || task?.status === "running") && (
            <div className="mt-4 overflow-hidden glass p-0">
              <TypingIndicator text="AI 正在生成视频..." />
            </div>
          )}

          {task?.status === "failed" && (
            <div className="mt-4 border-l-4 border-l-red-500 bg-[rgba(160,45,45,0.08)] p-4">
              <p className="text-sm text-red-400">{formatVideoTaskError(task.error_message)}</p>
            </div>
          )}

          {task?.status === "succeeded" && videoUrl && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="mt-5 glass overflow-hidden"
            >
              <video src={videoUrl} controls crossOrigin="anonymous" className="w-full" style={{ aspectRatio: "16 / 9", objectFit: "cover" }} />
              <div className="p-3 flex items-center gap-2">
                <a
                  href={videoUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-ghost text-xs"
                  style={{ minHeight: 28, padding: "0 10px" }}
                >
                  查看视频
                </a>
              </div>
            </motion.div>
          )}
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
          className="glass card-hover p-5 h-fit"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-[15px] font-bold text-[#f5f5f5]">模型参数</h2>
            <span className="text-[13px] font-mono text-[#9ca3af]">{estimateCost(options, selectableVideoModels)}</span>
          </div>

          <div className="space-y-5">
            <Field label="模型">
              <select
                className="input-glass w-full appearance-none cursor-pointer"
                value={options.model}
                onChange={(event) => updateOption("model", event.target.value)}
              >
                {selectableVideoModels.map((model) => (
                  <option key={model.value} value={model.value}>
                    {model.label}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="视频比例">
              <div className="grid grid-cols-3 gap-2">
                {RATIOS.map((ratio) => (
                  <button
                    key={ratio}
                    type="button"
                    onClick={() => updateOption("ratio", ratio)}
                    className={`min-h-[36px] border text-[13px] font-[620] transition-colors ${
                      options.ratio === ratio
                        ? "border-[rgba(127,220,146,0.35)] bg-[rgba(127,220,146,0.16)] text-[#f5f5f5]"
                        : "border-[rgba(255,255,255,0.06)] bg-[rgba(255,255,255,0.03)] text-[#9ca3af]"
                    }`}
                  >
                    {ratio}
                  </button>
                ))}
              </div>
            </Field>

            <Field label="分辨率">
              <div className="grid grid-cols-3 gap-2">
                {selectedResolutions.map((resolution) => (
                  <button
                    key={resolution}
                    type="button"
                    onClick={() => updateOption("resolution", resolution)}
                    className={`min-h-[36px] border text-[13px] font-[620] transition-colors ${
                      options.resolution === resolution
                        ? "border-[rgba(127,220,146,0.35)] bg-[rgba(127,220,146,0.16)] text-[#f5f5f5]"
                        : "border-[rgba(255,255,255,0.06)] bg-[rgba(255,255,255,0.03)] text-[#9ca3af]"
                    }`}
                  >
                    {RESOLUTION_LABELS[resolution] || resolution}
                  </button>
                ))}
              </div>
            </Field>

            <Field label="视频时长">
              <div className="grid grid-cols-2 gap-2 mb-3">
                <button
                  type="button"
                  onClick={() => updateOption("duration_mode", "seconds")}
                  className={`min-h-[36px] border text-[13px] font-[620] ${
                    options.duration_mode === "seconds"
                      ? "border-[rgba(127,220,146,0.35)] bg-[rgba(127,220,146,0.16)] text-[#f5f5f5]"
                      : "border-[rgba(255,255,255,0.06)] bg-[rgba(255,255,255,0.03)] text-[#9ca3af]"
                  }`}
                >
                  按秒数
                </button>
                <button
                  type="button"
                  onClick={() => updateOption("duration_mode", "smart")}
                  className={`min-h-[36px] border text-[13px] font-[620] ${
                    options.duration_mode === "smart"
                      ? "border-[rgba(127,220,146,0.35)] bg-[rgba(127,220,146,0.16)] text-[#f5f5f5]"
                      : "border-[rgba(255,255,255,0.06)] bg-[rgba(255,255,255,0.03)] text-[#9ca3af]"
                  }`}
                >
                  智能时长
                </button>
              </div>
              {options.duration_mode === "seconds" && (
                <NumberInput
                  value={options.duration_seconds}
                  min={4}
                  max={15}
                  step={1}
                  suffix="秒"
                  onChange={(value) => updateOption("duration_seconds", value)}
                />
              )}
            </Field>

            <Field label="生成数量">
              <NumberInput
                value={options.count}
                min={1}
                max={4}
                suffix="条"
                onChange={(value) => updateOption("count", value)}
              />
            </Field>

            <div className="flex items-center justify-between">
              <span className="text-[13px] font-medium text-[#f5f5f5]">输出声音</span>
              <Toggle checked={options.with_sound} onChange={(value) => updateOption("with_sound", value)} />
            </div>

            <Field label="种子值">
              <div className="flex gap-2">
                <input
                  type="number"
                  className="input-glass flex-1"
                  value={options.seed}
                  onChange={(event) => updateOption("seed", Number(event.target.value))}
                />
                <button
                  type="button"
                  onClick={() => updateOption("seed", Math.floor(Math.random() * 1000000))}
                  className="metal-btn"
                >
                  随机
                </button>
              </div>
            </Field>

            <div className="flex items-center justify-between">
              <span className="text-[13px] font-medium text-[#f5f5f5]">联网搜索</span>
              <Toggle checked={options.web_search} onChange={(value) => updateOption("web_search", value)} />
            </div>

            <Field label="超时时间">
              <NumberInput
                value={options.timeout_hours}
                min={1}
                max={48}
                suffix="小时"
                onChange={(value) => updateOption("timeout_hours", value)}
              />
            </Field>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-[12px] font-[540] text-[#9ca3af] mb-2 block">{label}</label>
      {children}
    </div>
  );
}

function NumberInput({
  value,
  min,
  max,
  step = 1,
  suffix,
  onChange,
}: {
  value: number;
  min: number;
  max: number;
  step?: number;
  suffix: string;
  onChange: (value: number) => void;
}) {
  return (
    <div className="flex items-center gap-3">
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="flex-1 h-1.5 rounded-full appearance-none cursor-pointer"
      />
      <span className="w-[56px] text-right text-[13px] font-[620] text-[#f5f5f5]">
        {value}
        <span className="ml-1 text-[#9ca3af]">{suffix}</span>
      </span>
    </div>
  );
}

function Toggle({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className="relative inline-flex h-[22px] w-10 items-center rounded-full transition-colors"
      style={{ background: checked ? "var(--jade-primary)" : "rgba(255,255,255,0.1)" }}
    >
      <span
        className="inline-block h-[18px] w-[18px] rounded-full bg-white transition-transform"
        style={{ transform: checked ? "translateX(19px)" : "translateX(2px)" }}
      />
    </button>
  );
}
