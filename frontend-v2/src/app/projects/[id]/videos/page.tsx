"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import { useRouter, useParams, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "@phosphor-icons/react";
import { generateVideoAsync, enhancePrompt, listVideoModels, type VideoModelConfig } from "@/lib/api/videos";
import { formatVideoCreditEstimate } from "@/lib/videoCost";
import { getProject, type Project } from "@/lib/api/projects";
import { listProjectTopics, type Topic } from "@/lib/api/topics";
import { listDigitalAssets, type DigitalAsset } from "@/lib/api/digitalAssets";
import { api } from "@/lib/api/client";
import ProjectModuleTitle from "@/components/ProjectModuleTitle";
import { formatBeijingTime } from "@/lib/time";

interface TaskStatus {
  id: number;
  status: "queued" | "running" | "succeeded" | "failed";
  result_data: Record<string, unknown> | null;
  error_message: string | null;
}

function formatVideoTaskError(message: string | null | undefined) {
  const text = message || "视频生成失败，请稍后重试。";
  const lowerText = text.toLowerCase();
  if (
    text.includes("InputImageSensitiveContentDetected.PrivacyInformation") ||
    lowerText.includes("input image may contain real person") ||
    text.includes("输入参考图疑似包含真实人物或隐私信息")
  ) {
    return "参考图未通过火山审核：输入参考图疑似包含真实人物或隐私信息。任务已停止，积分已自动退回。请更换无真实人物、无隐私信息的参考图，或先用生图生成非真人分镜图后再生视频。";
  }
  if (lowerText.includes("copyright restrictions") || text.includes("版权限制")) {
    return "输出视频未通过火山审核：可能涉及版权限制。任务已停止，积分已自动退回。请换用更通用的描述，避免品牌、明星或受版权保护的画面。";
  }
  return text;
}

function digitalAssetPrompt(asset: DigitalAsset) {
  const metadataPrompt = asset.asset_metadata?.prompt;
  return (
    asset.content_text ||
    (typeof metadataPrompt === "string" ? metadataPrompt : "") ||
    asset.preview_text ||
    asset.title ||
    ""
  ).trim();
}

interface VideoOptions {
  model: string;
  mode: "reference" | "keyframe";
  ratio: string;
  resolution: string;
  duration_mode: "seconds" | "smart";
  duration_seconds: number;
  count: number;
  with_sound: boolean;
  seed: number;
  advanced_open: boolean;
  web_search: boolean;
  timeout_hours: number;
}

const RATIOS = [
  { label: "21:9", value: "21:9" },
  { label: "16:9", value: "16:9" },
  { label: "4:3", value: "4:3" },
  { label: "1:1", value: "1:1" },
  { label: "3:4", value: "3:4" },
  { label: "9:16", value: "9:16" },
];

const RESOLUTIONS = [
  { label: "480p", value: "480p" },
  { label: "720p", value: "720p" },
  { label: "1080p", value: "1080p" },
];

function Toggle({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className="relative inline-flex h-[22px] w-10 items-center rounded-full transition-colors"
      style={{
        background: checked ? "#6366f1" : "rgba(255,255,255,0.1)",
      }}
    >
      <span
        className="inline-block h-[18px] w-[18px] rounded-full bg-white transition-transform"
        style={{ transform: checked ? "translateX(19px)" : "translateX(2px)" }}
      />
    </button>
  );
}

function SegmentedControl({
  options,
  value,
  onChange,
}: {
  options: { label: string; value: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div
      className="inline-flex rounded-[0.625rem] p-[3px] gap-[3px]"
      style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.06)" }}
    >
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className="px-4 py-1.5 rounded-[0.5rem] text-[13px] font-medium transition-all"
          style={{
            background: value === opt.value ? "rgba(255,255,255,0.9)" : "transparent",
            color: value === opt.value ? "#111" : "var(--jade-text-sub)",
          }}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

function RatioGrid({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="space-y-2">
      <div className="grid grid-cols-3 gap-2">
        {RATIOS.map((r) => (
          <button
            key={r.value}
            onClick={() => onChange(r.value)}
            className="py-2 rounded-[0.625rem] text-[13px] font-medium transition-all border"
            style={{
              background: value === r.value ? "rgba(255,255,255,0.9)" : "rgba(255,255,255,0.03)",
              borderColor: value === r.value ? "rgba(255,255,255,0.2)" : "rgba(255,255,255,0.06)",
              color: value === r.value ? "#111" : "var(--jade-text-sub)",
            }}
          >
            {r.label}
          </button>
        ))}
      </div>
      <button
        onClick={() => onChange("auto")}
        className="py-2 px-4 rounded-[0.625rem] text-[13px] font-medium transition-all border"
        style={{
          background: value === "auto" ? "rgba(255,255,255,0.9)" : "rgba(255,255,255,0.03)",
          borderColor: value === "auto" ? "rgba(255,255,255,0.2)" : "rgba(255,255,255,0.06)",
          color: value === "auto" ? "#111" : "var(--jade-text-sub)",
        }}
      >
        智能比例
      </button>
    </div>
  );
}

function ResolutionRow({
  value,
  onChange,
  resolutions,
}: {
  value: string;
  onChange: (v: string) => void;
  resolutions: string[];
}) {
  const available = RESOLUTIONS.filter((r) => resolutions.includes(r.value));
  return (
    <div className="flex gap-2">
      {available.map((r) => (
        <button
          key={r.value}
          onClick={() => onChange(r.value)}
          className="flex-1 py-2 rounded-[0.625rem] text-[13px] font-medium transition-all border"
          style={{
            background: value === r.value ? "rgba(255,255,255,0.9)" : "rgba(255,255,255,0.03)",
            borderColor: value === r.value ? "rgba(255,255,255,0.2)" : "rgba(255,255,255,0.06)",
            color: value === r.value ? "#111" : "var(--jade-text-sub)",
          }}
        >
          {r.label}
        </button>
      ))}
    </div>
  );
}

function SliderField({
  value,
  min,
  max,
  step,
  suffix,
  onChange,
}: {
  value: number;
  min: number;
  max: number;
  step: number;
  suffix: string;
  onChange: (v: number) => void;
}) {
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <div className="video-slider-field">
      <div className="video-slider-shell">
        <div className="video-slider-track" />
        <div className="video-slider-progress" style={{ width: `${pct}%` }} />
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="video-slider-range"
        />
      </div>
      <span
        className="video-slider-value"
        style={{ color: "var(--jade-text-main)" }}
      >
        {value}
        <span className="ml-1" style={{ color: "var(--jade-text-sub)" }}>{suffix}</span>
      </span>
    </div>
  );
}

const IMAGE_REFERENCE_PATTERN = /@图片(\d+)/g;

function normalizeImageReferenceName(value: string | undefined) {
  if (!value) return "";
  const match = value.trim().match(/^@?图片(\d+)$/);
  return match ? `@图片${Number(match[1])}` : "";
}

function extractImageReferenceNames(text: string) {
  const names = new Set<string>();
  for (const match of text.matchAll(IMAGE_REFERENCE_PATTERN)) {
    names.add(`@图片${Number(match[1])}`);
  }
  return names;
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
    pricing_yuan_per_second: { "480p": 7 / 15, "720p": 1.0, "1080p": 37 / 15 },
    available: true,
  },
  {
    key: "seedance-2.0-fast",
    label: "Seedance 2.0 Fast",
    value: SEEDANCE_FAST_MODEL,
    kind: "fast",
    resolutions: ["480p", "720p"],
    pricing_yuan_per_second: { "480p": 5.6 / 15, "720p": 0.8 },
    available: true,
  },
];

function estimateCost(options: VideoOptions, models: VideoModelConfig[]): string {
  const modelPrices =
    models.find((model) => model.value === options.model)?.pricing_yuan_per_second ||
    FALLBACK_VIDEO_MODELS[0].pricing_yuan_per_second;
  const duration = options.duration_mode === "smart" ? 5 : options.duration_seconds;
  return formatVideoCreditEstimate(modelPrices[options.resolution] || 1.0, duration, options.count);
}

function PromptInput({
  value,
  onChange,
  referenceMedias,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  referenceMedias: { id: string; name: string; dataUrl: string; type: string }[];
  placeholder: string;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  function syncScroll() {
    if (textareaRef.current && overlayRef.current) {
      overlayRef.current.scrollTop = textareaRef.current.scrollTop;
      overlayRef.current.scrollLeft = textareaRef.current.scrollLeft;
    }
  }

  function renderHighlightedText(text: string) {
    if (referenceMedias.length === 0) {
      return text;
    }
    const names = referenceMedias.map((m) => m.name);
    const pattern = new RegExp(`@(${names.map((n) => n.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`, "g");
    const parts = text.split(pattern);
    return parts.map((part, idx) => {
      const media = referenceMedias.find((m) => m.name === part);
      if (media && idx % 2 === 1) {
        return (
          <span key={idx} style={{ color: "#6366f1", fontWeight: 500 }}>
            {media.type === "图片" ? (
              <img
                src={media.dataUrl}
                alt=""
                className="inline-block rounded-[3px] object-cover align-text-bottom mr-0.5"
                style={{ width: 16, height: 16 }}
              />
            ) : media.type === "视频" ? (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="inline-block align-text-bottom mr-0.5">
                <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18" />
                <polygon points="10 8 16 12 10 16 10 8" />
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="inline-block align-text-bottom mr-0.5">
                <path d="M9 18V5l12-2v13" />
                <circle cx="6" cy="18" r="3" />
                <circle cx="18" cy="16" r="3" />
              </svg>
            )}
            @{part}
          </span>
        );
      }
      return <span key={idx}>{part}</span>;
    });
  }

  return (
    <div className="flex-1 relative min-h-[80px]">
      <div
        ref={overlayRef}
        className="absolute inset-0 pointer-events-none overflow-hidden whitespace-pre-wrap break-words rounded-[var(--radius-inner)]"
        style={{
          fontFamily: "inherit",
          color: "var(--jade-text-main)",
          fontSize: 14,
          lineHeight: "1.5",
          padding: "10px 14px",
          zIndex: 1,
        }}
      >
        {renderHighlightedText(value)}
        {value === "" && (
          <span style={{ color: "rgba(255,255,255,0.25)" }}>{placeholder}</span>
        )}
      </div>
      <textarea
        ref={textareaRef}
        className="input-glass w-full h-full min-h-[80px] resize-y relative"
        style={{
          zIndex: 2,
          color: "transparent",
          caretColor: "white",
          background: "transparent",
        }}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onScroll={syncScroll}
      />
    </div>
  );
}

export default function VideosPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const projectId = Number(params.id);

  const [project, setProject] = useState<Project | null>(null);
  const [loadingProject, setLoadingProject] = useState(true);
  const [prompt, setPrompt] = useState(searchParams.get("prompt") || "");
  const [submitting, setSubmitting] = useState(false);
  const [task, setTask] = useState<TaskStatus | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [firstFrame, setFirstFrame] = useState<string | null>(null);
  const [lastFrame, setLastFrame] = useState<string | null>(null);
  interface ReferenceMedia {
    id: string;
    name: string;
    dataUrl: string;
    type: string;
    selected: boolean;
    referenceName?: string;
  }
  const [referenceMedias, setReferenceMedias] = useState<ReferenceMedia[]>([]);
  const firstFrameRef = useRef<HTMLInputElement>(null);
  const lastFrameRef = useRef<HTMLInputElement>(null);
  const referenceMediaRef = useRef<HTMLInputElement>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [selectedTopicId, setSelectedTopicId] = useState<number | null>(null);
  const [assets, setAssets] = useState<DigitalAsset[]>([]);
  const [loadingAssets, setLoadingAssets] = useState(false);

  interface MaterialPrompt {
    id: string;
    title: string;
    text: string;
    source: string;
  }
  interface MaterialImage {
    id: string;
    url: string;
    name: string;
  }
  const [materialPrompts, setMaterialPrompts] = useState<MaterialPrompt[]>([]);
  const [materialImages, setMaterialImages] = useState<MaterialImage[]>([]);
  const [enhancing, setEnhancing] = useState(false);

  const defaultOptions: VideoOptions = {
    model: SEEDANCE_STANDARD_MODEL,
    mode: "reference",
    ratio: "9:16",
    resolution: "480p",
    duration_mode: "seconds",
    duration_seconds: 10,
    count: 1,
    with_sound: true,
    seed: -1,
    advanced_open: false,
    web_search: false,
    timeout_hours: 48,
  };

  const [options, setOptions] = useState<VideoOptions>({ ...defaultOptions });
  const [videoModels, setVideoModels] = useState<VideoModelConfig[]>(FALLBACK_VIDEO_MODELS);
  const availableVideoModels = videoModels.filter((model) => model.available);
  const selectableVideoModels = availableVideoModels.length > 0 ? availableVideoModels : FALLBACK_VIDEO_MODELS;
  const selectedVideoModel =
    selectableVideoModels.find((model) => model.value === options.model) || selectableVideoModels[0];
  const selectedResolutions = selectedVideoModel.resolutions.length > 0 ? selectedVideoModel.resolutions : ["480p"];
  const promptImageReferenceNames = extractImageReferenceNames(prompt);
  const activeReferenceMedias = referenceMedias.filter(
    (media) =>
      media.selected ||
      (media.type === "图片" &&
        Boolean(media.referenceName) &&
        promptImageReferenceNames.has(normalizeImageReferenceName(media.referenceName))),
  );
  const unknownPromptImageReferences = Array.from(promptImageReferenceNames).filter(
    (name) => !referenceMedias.some((media) => normalizeImageReferenceName(media.referenceName) === name),
  );

  useEffect(() => {
    let cancelled = false;
    listVideoModels()
      .then((models) => {
        if (cancelled || models.length === 0) return;
        const enabled = models.filter((model) => model.available);
        const nextModels = enabled.length > 0 ? models : FALLBACK_VIDEO_MODELS;
        const firstEnabled = enabled[0] || FALLBACK_VIDEO_MODELS[0];
        setVideoModels(nextModels);
        setOptions((prev) => {
          const current = nextModels.find((model) => model.available && model.value === prev.model);
          if (current && current.resolutions.includes(prev.resolution)) return prev;
          const model = current || firstEnabled;
          return {
            ...prev,
            model: model.value,
            resolution: model.resolutions.includes(prev.resolution) ? prev.resolution : model.resolutions[0] || "480p",
          };
        });
      })
      .catch(() => {
        if (!cancelled) setVideoModels(FALLBACK_VIDEO_MODELS);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const fetchProject = useCallback(async () => {
    setLoadingProject(true);
    try {
      const data = await getProject(projectId);
      setProject(data);
    } catch {
      router.push("/projects");
    } finally {
      setLoadingProject(false);
    }
  }, [projectId, router]);

  useEffect(() => {
    fetchProject();
  }, [fetchProject]);

  useEffect(() => {
    async function fetchTopics() {
      try {
        const data = await listProjectTopics(projectId);
        setTopics(data);
      } catch {
        // ignore
      }
    }
    fetchTopics();
  }, [projectId]);

  const fetchAssets = useCallback(async () => {
    setLoadingAssets(true);
    try {
      const data = await listDigitalAssets({ asset_type: "video", limit: 100, offset: 0 });
      setAssets(data);
    } catch {
      setAssets([]);
    } finally {
      setLoadingAssets(false);
    }
  }, [projectId]);

  const fetchImageAssets = useCallback(async () => {
    try {
      const data = await listDigitalAssets({ asset_type: "image", limit: 50, offset: 0 });
      setMaterialImages((prev) => {
        const existingUrls = new Set(prev.map((m) => m.url));
        const newImages = data
          .filter((d) => d.access_url && !existingUrls.has(d.access_url))
          .map((d) => ({
            id: `asset_${d.id}`,
            url: d.access_url!,
            name: d.title || "项目图片",
          }));
        return [...prev, ...newImages];
      });
    } catch {
      // ignore
    }
  }, [projectId]);

  async function copyText(text: string, successMessage: string) {
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      alert(successMessage);
    } catch {
      alert("复制失败");
    }
  }

  useEffect(() => {
    fetchAssets();
    fetchImageAssets();
  }, [fetchAssets, fetchImageAssets]);

  // Parse query params into material sidebar
  useEffect(() => {
    const qPrompt = searchParams.get("prompt");
    const qImage = searchParams.get("image");
    const qFirstFrame = searchParams.get("first_frame");
    if (qPrompt) {
      setMaterialPrompts((prev) => {
        const exists = prev.some((p) => p.text === qPrompt);
        if (exists) return prev;
        return [
          ...prev,
          {
            id: `qp_${Date.now()}`,
            title: qPrompt.slice(0, 20) + (qPrompt.length > 20 ? "..." : ""),
            text: qPrompt,
            source: "选题",
          },
        ];
      });
    }
    const imgUrl = qImage || qFirstFrame;
    if (imgUrl) {
      setMaterialImages((prev) => {
        const exists = prev.some((m) => m.url === imgUrl);
        if (exists) return prev;
        return [
          ...prev,
          {
            id: `qi_${Date.now()}`,
            url: imgUrl,
            name: qFirstFrame ? "首帧图" : "参考图",
          },
        ];
      });
    }
  }, [searchParams]);

  function removeMaterialPrompt(id: string) {
    setMaterialPrompts((prev) => prev.filter((p) => p.id !== id));
  }

  function removeMaterialImage(id: string) {
    setMaterialImages((prev) => prev.filter((m) => m.id !== id));
  }

  function detectMaterialHint(text: string): string | undefined {
    const lower = text.toLowerCase();
    if (/翡翠|玉|jade/.test(lower)) return "jade";
    if (/钻石|diamond/.test(lower)) return "diamond";
    if (/黄金|gold/.test(lower)) return "gold";
    if (/珍珠|pearl/.test(lower)) return "pearl";
    if (/红宝石|ruby/.test(lower)) return "ruby";
    if (/蓝宝石|sapphire/.test(lower)) return "sapphire";
    return undefined;
  }

  async function handleEnhanceVideoPrompt() {
    if (!prompt.trim() || enhancing) return;
    setEnhancing(true);
    try {
      const hint = detectMaterialHint(prompt);
      const res = await enhancePrompt({ prompt: prompt.trim(), material_hint: hint });
      if (res.enhanced_prompt) {
        setPrompt(res.enhanced_prompt);
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "优化失败");
    } finally {
      setEnhancing(false);
    }
  }

  function clearVideoComposer() {
    setPrompt("");
    setFirstFrame(null);
    setLastFrame(null);
    setReferenceMedias([]);
    setTask(null);
    stopPolling();
  }

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
        const res = await api.get<TaskStatus>("/api/generation-tasks/" + taskId);
        setTask(res);
        if (res.status === "succeeded" || res.status === "failed") {
          stopPolling();
          if (res.status === "succeeded") {
            fetchAssets();
          } else {
            alert(formatVideoTaskError(res.error_message));
          }
        }
      } catch {
        // ignore polling errors
      }
    };
    void pollOnce();
    pollRef.current = setInterval(pollOnce, 1500);
  }, [stopPolling, fetchAssets]);

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
      if (key === "mode") {
        // Clear mode-specific uploads when switching
        setFirstFrame(null);
        setLastFrame(null);
        setReferenceMedias([]);
      }
      return next;
    });
  }

  function resetOptions() {
    setOptions({ ...defaultOptions });
  }

  function handleFileUpload(
    file: File,
    setter: (v: string | null) => void,
    acceptedTypes?: string[],
  ) {
    if (acceptedTypes && !acceptedTypes.some((t) => file.type.startsWith(t))) {
      alert(`请上传 ${acceptedTypes.join("/")} 文件`);
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setter(reader.result as string);
    };
    reader.readAsDataURL(file);
  }

  function nextReferenceMediaName(items: ReferenceMedia[], typePrefix: string): string {
    const maxNum = items.reduce((max, item) => {
      if (item.type !== typePrefix) return max;
      const match = item.name.match(new RegExp(`^${typePrefix}(\\d+)$`));
      return match ? Math.max(max, Number(match[1])) : max;
    }, 0);
    return `${typePrefix}${maxNum + 1}`;
  }

  function handleMultipleFileUpload(
    files: FileList | null,
    acceptedTypes: string[],
  ) {
    if (!files) return;
    const validFiles = Array.from(files).filter((file) =>
      acceptedTypes.some((t) => file.type.startsWith(t)),
    );
    if (validFiles.length === 0) {
      alert(`请上传 ${acceptedTypes.join("/")} 文件`);
      return;
    }
    validFiles.forEach((file) => {
      const reader = new FileReader();
      reader.onload = () => {
        const dataUrl = reader.result as string;
        const typePrefix = file.type.startsWith("video/")
          ? "视频"
          : file.type.startsWith("audio/")
            ? "音频"
            : "图片";
        setReferenceMedias((prev) => {
          const name = nextReferenceMediaName(prev, typePrefix);
          return [
            ...prev,
            {
              id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
              name,
              dataUrl,
              type: typePrefix,
              selected: true,
              referenceName: typePrefix === "图片" ? `@${name}` : undefined,
            },
          ];
        });
      };
      reader.readAsDataURL(file);
    });
  }

  function removeReferenceMedia(id: string) {
    setReferenceMedias((prev) => prev.filter((m) => m.id !== id));
  }

  function toggleReferenceMedia(id: string) {
    setReferenceMedias((prev) =>
      prev.map((m) => (m.id === id ? { ...m, selected: !m.selected } : m)),
    );
  }

  function appendReferenceMention(referenceName: string | undefined) {
    const normalized = normalizeImageReferenceName(referenceName);
    if (!normalized) return;
    setPrompt((prev) => `${prev}${prev.trim() ? " " : ""}${normalized}`);
  }

  async function handleSubmit() {
    if (!prompt.trim()) {
      // eslint-disable-next-line no-alert
      alert("请输入视频生成提示词");
      return;
    }
    setSubmitting(true);
    setTask(null);
    stopPolling();
    try {
      const apiOptions: Record<string, unknown> = {
        model: options.model,
        mode: options.mode,
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
      if (options.mode === "keyframe") {
        if (firstFrame) apiOptions.first_frame = firstFrame;
        if (lastFrame) apiOptions.last_frame = lastFrame;
      } else if (options.mode === "reference") {
        if (unknownPromptImageReferences.length > 0) {
          alert(`这些图片引用不存在：${unknownPromptImageReferences.join("、")}`);
          return;
        }
        if (activeReferenceMedias.length > 0) {
          const imageReferences = activeReferenceMedias.filter((m) => m.type === "图片");
          apiOptions.reference_images = imageReferences.map((m) => m.dataUrl);
          apiOptions.reference_image_names = imageReferences.map((m) => normalizeImageReferenceName(m.referenceName));
          apiOptions.reference_videos = activeReferenceMedias.filter((m) => m.type === "视频").map((m) => m.dataUrl);
          apiOptions.reference_audios = activeReferenceMedias.filter((m) => m.type === "音频").map((m) => m.dataUrl);
        }
      }
      const res = await generateVideoAsync(projectId, prompt.trim(), apiOptions);
      setTask({ id: res.task_id, status: res.status as TaskStatus["status"], result_data: null, error_message: null });
      startPolling(res.task_id);
    } catch (err) {
      // eslint-disable-next-line no-alert
      alert(formatVideoTaskError(err instanceof Error ? err.message : "提交失败"));
    } finally {
      setSubmitting(false);
    }
  }

  const videoUrl = task?.result_data?.video_url as string | undefined;

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
          <ProjectModuleTitle projectName={project?.project_name} moduleName="视频生成" />
        </div>
        <div className="section-header-actions">
          <Link href={`/projects/${projectId}`} className="project-return-btn">
            返回人设
          </Link>
        </div>
      </motion.div>

      {loadingProject ? (
        <div className="glass p-8">
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-[rgba(255,255,255,0.06)] rounded w-1/3" />
            <div className="h-4 bg-[rgba(255,255,255,0.06)] rounded w-2/3" />
          </div>
        </div>
      ) : null}

      <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr_380px] gap-6">
        {/* Left: Material Sidebar */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.05 }}
          className="space-y-4"
        >
          <div className="glass card-hover p-4">
            <h3 className="text-[13px] font-bold text-[#f5f5f5] mb-3">素材备选</h3>

            {/* Prompt materials */}
            {materialPrompts.length > 0 && (
              <div className="mb-4">
                <p className="text-[11px] text-[#9ca3af] mb-2 uppercase tracking-wider">Prompt</p>
                <div className="space-y-2">
                  {materialPrompts.map((mp) => (
                    <div
                      key={mp.id}
                      className="flat-delete-target rounded-[0.625rem] p-2.5 border transition-colors hover:bg-[rgba(255,255,255,0.04)]"
                      style={{ borderColor: "rgba(255,255,255,0.06)", background: "rgba(255,255,255,0.02)" }}
                    >
                      <button
                        onClick={() => removeMaterialPrompt(mp.id)}
                        className="flat-delete-action"
                        title="删除"
                        aria-label="删除素材提示词"
                      >
                        <X size={13} weight="bold" />
                      </button>
                      <p className="text-[11px] text-[#9ca3af] mb-1 pr-4">{mp.source}</p>
                      <p className="text-[12px] text-[#f5f5f5] line-clamp-2 leading-relaxed mb-2">{mp.text}</p>
                      <button
                        onClick={() => setPrompt(mp.text)}
                        className="text-[11px] px-2 py-1 rounded-md border transition-colors hover:bg-[rgba(255,255,255,0.08)]"
                        style={{ borderColor: "rgba(255,255,255,0.1)", color: "var(--jade-text-sub)" }}
                      >
                        使用
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Image materials */}
            {materialImages.length > 0 && (
              <div>
                <p className="text-[11px] text-[#9ca3af] mb-2 uppercase tracking-wider">图片</p>
                <div className="space-y-2">
                  {materialImages.map((mi) => (
                    <div
                      key={mi.id}
                      className="flat-delete-target rounded-[0.625rem] overflow-hidden border"
                      style={{ borderColor: "rgba(255,255,255,0.06)" }}
                    >
                      <div className="relative">
                        <img src={mi.url} alt={mi.name} className="w-full aspect-video object-cover" />
                        <button
                          onClick={() => removeMaterialImage(mi.id)}
                          className="flat-delete-action"
                          title="删除"
                          aria-label="删除素材图片"
                        >
                          <X size={13} weight="bold" />
                        </button>
                      </div>
                      <div className="p-2 space-y-1.5">
                        <p className="text-[11px] text-[#9ca3af]">{mi.name}</p>
                        <div className="flex gap-1.5">
                          <button
                            onClick={() => {
                              setFirstFrame(mi.url);
                              if (options.mode !== "keyframe") updateOption("mode", "keyframe");
                            }}
                            className="flex-1 text-[10px] px-1.5 py-1 rounded border transition-colors hover:bg-[rgba(255,255,255,0.08)]"
                            style={{ borderColor: "rgba(255,255,255,0.1)", color: "var(--jade-text-sub)" }}
                          >
                            作为首帧
                          </button>
                          <button
                            onClick={() => {
                              const typePrefix = "图片";
                              setReferenceMedias((prev) => {
                                const name = nextReferenceMediaName(prev, typePrefix);
                                return [
                                  ...prev,
                                  {
                                    id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
                                    name,
                                    dataUrl: mi.url,
                                    type: typePrefix,
                                    selected: true,
                                    referenceName: `@${name}`,
                                  },
                                ];
                              });
                              if (options.mode !== "reference") updateOption("mode", "reference");
                            }}
                            className="flex-1 text-[10px] px-1.5 py-1 rounded border transition-colors hover:bg-[rgba(255,255,255,0.08)]"
                            style={{ borderColor: "rgba(255,255,255,0.1)", color: "var(--jade-text-sub)" }}
                          >
                            作为参考图
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Video materials — project assets */}
            {assets.length > 0 && (
              <div className="mt-4">
                <p className="text-[11px] text-[#9ca3af] mb-2 uppercase tracking-wider">项目视频</p>
                <div className="space-y-2">
                  {assets.slice(0, 5).map((asset) => (
                    <div
                      key={asset.id}
                      className="rounded-[0.625rem] overflow-hidden border relative group"
                      style={{ borderColor: "rgba(255,255,255,0.06)" }}
                    >
                      <div className="relative aspect-video bg-black flex items-center justify-center">
                        {asset.access_url ? (
                          <video
                            src={asset.access_url}
                            className="w-full h-full object-cover"
                            preload="metadata"
                            muted
                          />
                        ) : (
                          <span className="text-[11px] text-[#6b7280]">无预览</span>
                        )}
                      </div>
                      <div className="p-2 space-y-1.5">
                        <p className="text-[11px] text-[#9ca3af] truncate">{asset.title || "生成视频"}</p>
                        <button
                          onClick={() => {
                            const url = asset.access_url;
                            if (!url) return;
                            setReferenceMedias((prev) => {
                              const name = nextReferenceMediaName(prev, "视频");
                              return [
                                ...prev,
                                {
                                  id: `asset_video_${asset.id}`,
                                  name,
                                  dataUrl: url,
                                  type: "视频",
                                  selected: true,
                                },
                              ];
                            });
                            if (options.mode !== "reference") updateOption("mode", "reference");
                          }}
                          disabled={!asset.access_url}
                          className="w-full text-[10px] px-1.5 py-1 rounded border transition-colors hover:bg-[rgba(255,255,255,0.08)] disabled:opacity-40"
                          style={{ borderColor: "rgba(255,255,255,0.1)", color: "var(--jade-text-sub)" }}
                        >
                          作为参考视频
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {materialPrompts.length === 0 && materialImages.length === 0 && assets.length === 0 && (
              <p className="text-[12px] text-[#6b7280] text-center py-6">暂无素材</p>
            )}
          </div>
        </motion.div>

        {/* Center: Prompt */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
        >
          <div className="glass card-hover p-4 md:p-5 mb-6">
            {/* Topic selector */}
            {topics.length > 0 && (
              <div className="flex items-center gap-2 mb-3 pb-3 border-b" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                <span className="text-[12px] text-[#9ca3af] shrink-0">加载选题:</span>
                <select
                  className="flex-1 input-glass text-[13px] py-1.5 cursor-pointer"
                  value={selectedTopicId ?? ""}
                  onChange={(e) => {
                    const id = Number(e.target.value);
                    if (!id) {
                      setSelectedTopicId(null);
                      return;
                    }
                    const topic = topics.find((t) => t.id === id);
                    if (topic) {
                      setSelectedTopicId(id);
                      const text = topic.topic_data?.seedance_video_prompt || topic.title || "";
                      if (text) setPrompt(text);
                    }
                  }}
                >
                  <option value="">选择选题...</option>
                  {topics.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.title}
                    </option>
                  ))}
                </select>
              </div>
            )}
            {/* Toolbar above prompt */}
            <div className="flex items-center justify-between mb-3">
              <span className="text-[12px] text-[#9ca3af]">提示词</span>
            </div>

            {/* Input bar: frames + prompt + submit */}
            <div className="flex flex-wrap gap-3 items-start">
              {options.mode === "reference" ? (
                /* Reference media upload */
                <div className="shrink-0 flex flex-col gap-2">
                  <input
                    ref={referenceMediaRef}
                    type="file"
                    accept="image/*,video/*,audio/*"
                    multiple
                    className="hidden"
                    onChange={(e) => {
                      handleMultipleFileUpload(e.target.files, ["image/", "video/", "audio/"]);
                      e.target.value = "";
                    }}
                  />
                  <button
                    onClick={() => referenceMediaRef.current?.click()}
                    className="w-16 h-16 rounded-[0.625rem] bg-[rgba(255,255,255,0.03)] border border-dashed border-[rgba(255,255,255,0.1)] flex flex-col items-center justify-center gap-1 transition-colors hover:bg-[rgba(255,255,255,0.06)]"
                    title="上传参考媒体"
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[#9ca3af]">
                      <line x1="12" y1="5" x2="12" y2="19" />
                      <line x1="5" y1="12" x2="19" y2="12" />
                    </svg>
                    <span className="text-[10px] text-[#9ca3af] leading-tight text-center">图片/视频/音频</span>
                  </button>
                  {referenceMedias.length > 0 && (
                    <div className="flex flex-col gap-1.5 w-16">
                      {referenceMedias.map((m) => {
                        const isActive =
                          m.selected ||
                          (m.type === "图片" &&
                            Boolean(m.referenceName) &&
                            promptImageReferenceNames.has(normalizeImageReferenceName(m.referenceName)));
                        return (
                        <div
                          key={m.id}
                          onClick={() => toggleReferenceMedia(m.id)}
                          className="flat-delete-target relative w-16 h-16 cursor-pointer rounded-[0.5rem] overflow-hidden border shrink-0 transition-colors"
                          style={{
                            borderColor: isActive ? "rgba(127,220,146,0.5)" : "rgba(255,255,255,0.08)",
                            background: isActive ? "rgba(127,220,146,0.08)" : "rgba(255,255,255,0.03)",
                          }}
                          role="button"
                          tabIndex={0}
                          title={`${isActive ? "取消选择" : "选择"} ${m.name}`}
                        >
                          {m.type === "图片" ? (
                            <>
                              <img src={m.dataUrl} alt={m.name} className="w-full h-full object-cover" />
                              <button
                                type="button"
                                onClick={(event) => {
                                  event.stopPropagation();
                                  appendReferenceMention(m.referenceName);
                                }}
                                className="absolute left-1 bottom-1 max-w-[calc(100%-0.5rem)] rounded-[0.25rem] bg-[rgba(0,0,0,0.62)] px-1.5 py-0.5 text-[10px] leading-none font-medium text-white shadow-sm truncate"
                                title={`插入 ${m.referenceName || `@${m.name}`}`}
                              >
                                {m.referenceName || `@${m.name}`}
                              </button>
                            </>
                          ) : (
                            <div className="w-full h-full flex flex-col items-center justify-center gap-0.5 bg-[rgba(255,255,255,0.04)]">
                              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                                {m.type === "视频" ? (
                                  <>
                                    <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18" />
                                    <polygon points="10 8 16 12 10 16 10 8" />
                                  </>
                                ) : (
                                  <>
                                    <path d="M9 18V5l12-2v13" />
                                    <circle cx="6" cy="18" r="3" />
                                    <circle cx="18" cy="16" r="3" />
                                  </>
                                )}
                              </svg>
                              <span className="text-[9px] text-[#9ca3af] truncate px-1 w-full text-center">{m.name}</span>
                            </div>
                          )}
                          <span
                            className="flat-delete-action"
                            onClick={(event) => {
                              event.stopPropagation();
                              removeReferenceMedia(m.id);
                            }}
                            role="button"
                            tabIndex={0}
                          >
                            <X size={13} weight="bold" />
                          </span>
                        </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              ) : (
                /* Keyframe mode: first + last frame */
                <>
                  <div className="shrink-0 flex flex-col items-center gap-1.5">
                    <input
                      ref={firstFrameRef}
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) handleFileUpload(f, setFirstFrame, ["image/"]);
                        e.target.value = "";
                      }}
                    />
                    {firstFrame ? (
                      <button
                        onClick={() => setFirstFrame(null)}
                        className="flat-delete-target w-12 h-12 rounded-[0.625rem] overflow-hidden border border-[rgba(255,255,255,0.1)]"
                        title="删除首帧"
                      >
                        <img src={firstFrame} alt="首帧" className="w-full h-full object-cover" />
                        <span className="flat-delete-action">
                          <X size={13} weight="bold" />
                        </span>
                      </button>
                    ) : (
                      <button
                        onClick={() => firstFrameRef.current?.click()}
                        className="w-12 h-12 rounded-[0.625rem] border border-dashed border-[rgba(255,255,255,0.12)] flex items-center justify-center transition-colors hover:bg-[rgba(255,255,255,0.04)]"
                        title="上传首帧"
                      >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-[#9ca3af]">
                          <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                          <circle cx="8.5" cy="8.5" r="1.5" />
                          <path d="M21 15l-5-5L5 21" />
                        </svg>
                      </button>
                    )}
                    <span className="text-[10px] text-[#9ca3af]">首帧</span>
                  </div>

                  {/* Swap button */}
                  {firstFrame && lastFrame && (
                    <button
                      onClick={() => {
                        const tmp = firstFrame;
                        setFirstFrame(lastFrame);
                        setLastFrame(tmp);
                      }}
                      className="shrink-0 self-center p-1 rounded-md transition-colors hover:bg-[rgba(255,255,255,0.06)]"
                      title="交换首帧尾帧"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M7 10h14l-4-4" />
                        <path d="M17 14H3l4 4" />
                      </svg>
                    </button>
                  )}

                  <div className="shrink-0 flex flex-col items-center gap-1.5">
                    <input
                      ref={lastFrameRef}
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) handleFileUpload(f, setLastFrame, ["image/"]);
                        e.target.value = "";
                      }}
                    />
                    {lastFrame ? (
                      <button
                        onClick={() => setLastFrame(null)}
                        className="flat-delete-target w-12 h-12 rounded-[0.625rem] overflow-hidden border border-[rgba(255,255,255,0.1)]"
                        title="删除尾帧"
                      >
                        <img src={lastFrame} alt="尾帧" className="w-full h-full object-cover" />
                        <span className="flat-delete-action">
                          <X size={13} weight="bold" />
                        </span>
                      </button>
                    ) : (
                      <button
                        onClick={() => lastFrameRef.current?.click()}
                        className="w-12 h-12 rounded-[0.625rem] border border-dashed border-[rgba(255,255,255,0.12)] flex items-center justify-center transition-colors hover:bg-[rgba(255,255,255,0.04)]"
                        title="上传尾帧"
                      >
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-[#9ca3af]">
                          <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                          <circle cx="8.5" cy="8.5" r="1.5" />
                          <path d="M21 15l-5-5L5 21" />
                        </svg>
                      </button>
                    )}
                    <span className="text-[10px] text-[#9ca3af]">尾帧</span>
                  </div>
                </>
              )}

              {/* Prompt with @ citation highlighting */}
              <PromptInput
                value={prompt}
                onChange={setPrompt}
                referenceMedias={referenceMedias}
                placeholder="@图片1 跟 @图片2 打架，镜头稳定跟拍，动作激烈但不血腥"
              />

              {/* Actions + cost */}
              <div className="video-action-stack shrink-0">
                <button
                  onClick={clearVideoComposer}
                  className="video-action-btn video-action-btn-secondary"
                  title="全部清空"
                >
                  <span>全部清空</span>
                </button>
                <button
                  onClick={handleEnhanceVideoPrompt}
                  disabled={!prompt.trim() || enhancing}
                  className="video-action-btn video-action-btn-secondary"
                >
                  {enhancing ? <span className="btn-spinner" /> : null}
                  <span>{enhancing ? "优化中" : "提示词优化"}</span>
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={submitting || !prompt.trim()}
                  className="video-action-btn video-action-btn-send"
                >
                  {submitting ? <span className="btn-spinner" style={{ borderColor: "rgba(255,255,255,0.3)", borderTopColor: "white" }} /> : null}
                  <span>{submitting ? "生成中" : "发送生成"}</span>
                </button>
              </div>
            </div>
            {/* @ citation hint */}
            {options.mode === "reference" && referenceMedias.length > 0 && (
              <p className="mt-3 text-[12px] text-[#6b7280] leading-relaxed">
                本次使用 {activeReferenceMedias.length} / {referenceMedias.length} 个素材。使用@可快速引用上传的文件，如：参考
                {referenceMedias.map((m, idx) => (
                  <span key={m.id}>
                    {idx > 0 && "和"}{m.referenceName || `@${m.name}`}
                  </span>
                ))}
                中的内容生成视频。
              </p>
            )}
          </div>

          {(submitting || task?.status === "queued" || task?.status === "running") && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              className="glass p-0 overflow-hidden mb-6"
            >
              <div
                className="w-full flex flex-col items-center justify-center gap-4"
                style={{ background: "#000", aspectRatio: "16 / 9", maxHeight: 480 }}
              >
                <div className="w-10 h-10 rounded-full border-2 border-[rgba(255,255,255,0.15)] border-t-[rgba(255,255,255,0.7)] animate-spin" />
                <p className="text-[15px] font-medium text-[rgba(255,255,255,0.7)]">正在生成视频，稍后回来看</p>
              </div>
            </motion.div>
          )}

          {task?.status === "succeeded" && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              className="glass p-6 mb-6"
            >
              <h3 className="text-[16px] font-[680] text-[#f5f5f5] mb-4">生成结果</h3>
              {videoUrl ? (
                <div className="space-y-3">
                  <video
                    src={videoUrl}
                    controls
                    crossOrigin="anonymous"
                    className="w-full rounded-[0.75rem] border border-[rgba(255,255,255,0.06)]"
                    style={{ maxHeight: 480 }}
                  />
                  <div className="flex gap-3">
                    <a
                      href={videoUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="metal-btn metal-btn-primary text-sm"
                    >
                      下载视频
                    </a>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(videoUrl).then(() => {
                          // eslint-disable-next-line no-alert
                          alert("已复制视频链接");
                        }).catch(() => {
                          // eslint-disable-next-line no-alert
                          alert("复制失败");
                        });
                      }}
                      className="metal-btn text-sm"
                    >
                      复制链接
                    </button>
                  </div>
                </div>
              ) : (
                <p className="text-[#9ca3af] text-sm">任务已完成，但未返回视频链接。</p>
              )}
            </motion.div>
          )}

          {task?.status === "failed" && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              className="glass p-6 mb-6"
            >
              <h3 className="text-[16px] font-[680] text-[#f5f5f5] mb-2">任务失败</h3>
              <p className="text-[#a05858] text-sm">{formatVideoTaskError(task.error_message)}</p>
            </motion.div>
          )}
        </motion.div>

        {/* Right: Parameter Panel */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.15 }}
          className="glass card-hover overflow-hidden"
          style={{ alignSelf: "flex-start" }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
            <h2 className="text-[15px] font-bold text-[#f5f5f5]">模型参数</h2>
            <div className="flex items-center gap-2">
              <button
                onClick={resetOptions}
                className="p-1.5 rounded-lg transition-colors hover:bg-[rgba(255,255,255,0.06)]"
                title="重置参数"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[#9ca3af]">
                  <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                  <path d="M3 3v5h5" />
                </svg>
              </button>
            </div>
          </div>

          <div className="px-5 py-4 space-y-5 max-h-[calc(100dvh-220px)] overflow-y-auto">
            {/* Cost estimate */}
            <div className="flex items-center justify-between">
              <span className="text-[13px]" style={{ color: "var(--jade-text-sub)" }}>费用预估</span>
              <span className="text-[13px] font-mono" style={{ color: "var(--jade-text-main)" }}>
                {estimateCost(options, selectableVideoModels)}
              </span>
            </div>

            <div className="h-px" style={{ background: "rgba(255,255,255,0.06)" }} />

            {/* Model */}
            <div>
              <label className="text-[12px] font-[540] text-[#9ca3af] mb-2 block">模型</label>
              <SegmentedControl
                options={[
                  ...selectableVideoModels.map((model) => ({
                    label: model.label,
                    value: model.value,
                  })),
                ]}
                value={options.model}
                onChange={(v) => updateOption("model", v)}
              />
            </div>

            {/* Mode */}
            <div>
              <label className="text-[12px] font-[540] text-[#9ca3af] mb-2 block">选择模式</label>
              <SegmentedControl
                options={[
                  { label: "参考生成", value: "reference" },
                  { label: "首尾帧", value: "keyframe" },
                ]}
                value={options.mode}
                onChange={(v) => updateOption("mode", v as VideoOptions["mode"])}
              />
            </div>

            {/* Ratio */}
            <div>
              <label className="text-[12px] font-[540] text-[#9ca3af] mb-2 block">视频比例</label>
              <RatioGrid value={options.ratio} onChange={(v) => updateOption("ratio", v)} />
            </div>

            {/* Resolution */}
            <div>
              <label className="text-[12px] font-[540] text-[#9ca3af] mb-2 block">分辨率</label>
              <ResolutionRow
                value={options.resolution}
                onChange={(v) => updateOption("resolution", v)}
                resolutions={selectedResolutions}
              />
            </div>

            {/* Duration */}
            <div>
              <label className="text-[12px] font-[540] text-[#9ca3af] mb-2 block">视频时长</label>
              <SegmentedControl
                options={[
                  { label: "按秒数", value: "seconds" },
                  { label: "智能时长", value: "smart" },
                ]}
                value={options.duration_mode}
                onChange={(v) => updateOption("duration_mode", v as VideoOptions["duration_mode"])}
              />
              <AnimatePresence>
                {options.duration_mode === "seconds" && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <div className="pt-3">
                      <SliderField
                        value={options.duration_seconds}
                        min={4}
                        max={15}
                        step={1}
                        suffix="秒"
                        onChange={(v) => updateOption("duration_seconds", v)}
                      />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Count */}
            <div>
              <label className="text-[12px] font-[540] text-[#9ca3af] mb-2 block">选择生成数量</label>
              <SliderField
                value={options.count}
                min={1}
                max={4}
                step={1}
                suffix="条"
                onChange={(v) => updateOption("count", v)}
              />
            </div>

            {/* Sound */}
            <div className="flex items-center justify-between">
              <span className="text-[13px] font-medium" style={{ color: "var(--jade-text-main)" }}>
                输出声音
              </span>
              <Toggle checked={options.with_sound} onChange={(v) => updateOption("with_sound", v)} />
            </div>

            {/* Seed */}
            <div>
              <label className="text-[12px] font-[540] text-[#9ca3af] mb-2 block">种子值</label>
              <div className="flex gap-2">
                <input
                  type="number"
                  className="input-glass flex-1"
                  value={options.seed}
                  onChange={(e) => updateOption("seed", Number(e.target.value))}
                />
                <button
                  onClick={() => updateOption("seed", Math.floor(Math.random() * 1000000))}
                  className="px-3 rounded-[0.625rem] border transition-colors hover:bg-[rgba(255,255,255,0.06)]"
                  style={{ borderColor: "rgba(255,255,255,0.06)" }}
                  title="随机种子"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[#9ca3af]">
                    <rect x="2" y="2" width="20" height="20" rx="5" ry="5" />
                    <path d="M8 8h.01" />
                    <path d="M16 8h.01" />
                    <path d="M8 16h.01" />
                    <path d="M16 16h.01" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Advanced */}
            <div>
              <button
                onClick={() => updateOption("advanced_open", !options.advanced_open)}
                className="flex items-center justify-between w-full py-1"
              >
                <span className="text-[13px] font-medium" style={{ color: "var(--jade-text-main)" }}>
                  高级参数设置
                </span>
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="text-[#9ca3af]"
                  style={{
                    transform: options.advanced_open ? "rotate(180deg)" : "rotate(0deg)",
                    transition: "transform 0.2s ease",
                  }}
                >
                  <path d="M18 15l-6-6-6 6" />
                </svg>
              </button>
              <AnimatePresence>
                {options.advanced_open && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <div className="pt-4 space-y-4">
                      <div className="flex items-center justify-between">
                        <span className="text-[13px] font-medium" style={{ color: "var(--jade-text-main)" }}>
                          联网搜索
                        </span>
                        <Toggle checked={options.web_search} onChange={(v) => updateOption("web_search", v)} />
                      </div>
                      <div>
                        <label className="text-[12px] font-[540] text-[#9ca3af] mb-2 block">生成超时时间</label>
                        <SliderField
                          value={options.timeout_hours}
                          min={1}
                          max={48}
                          step={1}
                          suffix="小时"
                          onChange={(v) => updateOption("timeout_hours", v)}
                        />
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Waterfall video list */}
      {assets.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
          className="mt-8"
        >
          <h2 className="text-[18px] font-bold text-[#f5f5f5] mb-4">已生成视频</h2>
          <div className="flex flex-col gap-4 max-w-2xl mx-auto">
            {assets.map((asset) => {
              const promptText = digitalAssetPrompt(asset);
              return (
              <div
                key={asset.id}
                className="glass card-hover rounded-[1rem] overflow-hidden"
              >
                {asset.access_url ? (
                  <video
                    src={asset.access_url}
                    controls
                    crossOrigin="anonymous"
                    className="w-full"
                    style={{ aspectRatio: "16 / 9", objectFit: "cover" }}
                  />
                ) : (
                  <div
                    className="w-full flex items-center justify-center"
                    style={{ aspectRatio: "16 / 9", background: "#000" }}
                  >
                    <span className="text-[13px] text-[rgba(255,255,255,0.4)]">无预览</span>
                  </div>
                )}
                <div className="p-3 space-y-1">
                  <div className="flex items-center gap-2">
                    <p className="text-[13px] font-medium text-[#f5f5f5] truncate flex-1">{asset.title || "生成视频"}</p>
                    {typeof asset.asset_metadata?.resolution === "string" && (
                      <span
                        className="text-[10px] px-1.5 py-0.5 rounded font-medium shrink-0"
                        style={{ background: "rgba(99,102,241,0.15)", color: "#a5b4fc" }}
                      >
                        {asset.asset_metadata.resolution}
                      </span>
                    )}
                  </div>
                  {promptText ? (
                    <div className="rounded-[0.5rem] border border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.03)] p-2">
                      <div className="mb-1 flex items-center justify-between gap-2">
                        <span className="text-[11px] font-medium text-[#9ccaa8]">提示词</span>
                        <button
                          type="button"
                          onClick={() => copyText(promptText, "已复制提示词")}
                          className="text-[11px] text-[#9ca3af] transition-colors hover:text-[#f5f5f5]"
                        >
                          复制
                        </button>
                      </div>
                      <p className="line-clamp-3 text-[11px] leading-relaxed text-[#b0b0b0]" title={promptText}>
                        {promptText}
                      </p>
                    </div>
                  ) : null}
                  <p className="text-[11px] text-[#9ca3af]">
                    {formatBeijingTime(asset.created_at)}
                  </p>
                  {asset.access_url && (
                    <div className="flex gap-2 pt-1">
                      <a
                        href={asset.access_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[11px] px-2 py-1 rounded-md border transition-colors hover:bg-[rgba(255,255,255,0.06)]"
                        style={{ borderColor: "rgba(255,255,255,0.1)", color: "var(--jade-text-sub)" }}
                      >
                        下载
                      </a>
                      <button
                        onClick={() => copyText(asset.access_url!, "已复制链接")}
                        className="text-[11px] px-2 py-1 rounded-md border transition-colors hover:bg-[rgba(255,255,255,0.06)]"
                        style={{ borderColor: "rgba(255,255,255,0.1)", color: "var(--jade-text-sub)" }}
                      >
                        复制链接
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
            })}
          </div>
        </motion.div>
      )}

      {loadingAssets && (
        <div className="mt-8 flex justify-center">
          <div className="w-6 h-6 rounded-full border-2 border-[rgba(255,255,255,0.15)] border-t-[rgba(255,255,255,0.7)] animate-spin" />
        </div>
      )}
    </section>
  );
}
