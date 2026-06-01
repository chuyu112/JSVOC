"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import { useRouter, useParams, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "@phosphor-icons/react";
import {
  generateImageAsync,
  editImageAsync,
  enhanceImagePrompt,
  listProjectReferenceImages,
  createProjectReferenceImage,
  deleteProjectReferenceImage,
  listProjectDigitalAssets,
  deleteDigitalAsset,
  type GeneratedImage,
  type ImageGenerateResponse,
  type ImageSize,
  type ImageQuality,
  type ImageReferenceType,
  type ImageReferenceInput,
  type ProjectReferenceImage,
  type DigitalAsset,
} from "@/lib/api/images";
import { getProject, type Project } from "@/lib/api/projects";
import { api } from "@/lib/api/client";
import TypingIndicator from "@/components/ui/TypingIndicator";
import AIGeneratedBadge from "@/components/ui/AIGeneratedBadge";
import ProjectModuleTitle from "@/components/ProjectModuleTitle";
import GlassSelect from "@/components/ui/GlassSelect";

type GenMode = "text" | "image";
type RefType = "persona" | "product" | "location";

interface LocalReferenceImage extends ImageReferenceInput {
  id: string;
  preview: string;
  backendId?: number;
  selected: boolean;
}

interface TaskStatus {
  id: number;
  status: "queued" | "running" | "succeeded" | "failed";
  result_data: ImageGenerateResponse | null;
  error_message: string | null;
}

const refMeta: Record<
  RefType,
  { label: string; note: string }
> = {
  persona: {
    label: "人设参考图",
    note: "账号本人，例如苹果姐；上传后才允许生成可识别人设",
  },
  product: {
    label: "货品参考图",
    note: "文案里的产品，例如手镯、吊坠、证书细节",
  },
  location: {
    label: "场景参考图",
    note: "文案里的公司、档口、柜台、直播间等场景",
  },
};

const sizeOptions: ImageSize[] = [
  "1024x1536",
  "1024x1024",
  "1536x1024",
  "2048x1152",
  "1152x2048",
  "auto",
];
const qualityOptions: ImageQuality[] = ["high", "medium", "low", "auto"];
const countOptions = [1, 2, 3, 4];
const sizeLabels: Record<ImageSize, string> = {
  "1024x1536": "竖屏 1024x1536",
  "1024x1024": "方屏 1024x1024",
  "1536x1024": "横屏 1536x1024",
  "2048x1152": "2K 横屏 2048x1152（电影板实验）",
  "1152x2048": "2K 竖屏 1152x2048（短视频实验）",
  auto: "自动",
};
const qualityLabels: Record<ImageQuality, string> = {
  high: "高清（high）",
  medium: "标准（medium）",
  low: "快速（low）",
  auto: "自动（auto）",
};

function buildDefaultTextPrompt(project: Project | null): string {
  if (!project) return "";
  return [
    `画面主体必须是产品：${project.product}。`,
    `项目/账号名「${project.project_name}」只作为业务上下文，不是画面主体；不要把项目名里的词生成成实物、图标或文字。`,
    `行业：${project.industry} / ${project.sub_industry || "未填写"}。`,
    `生成一张高级清透的产品展示图：干净留白、柔和自然光、低饱和色调、真实产品质感。`,
    `突出产品本身、材质纹理和关键细节，背景简洁不抢镜。`,
    `不要出现乱码文字，不要出现夸张特效，整体风格高级、可信、清透。`,
  ].join("\n");
}

function buildDefaultEditPrompt(project: Project | null): string {
  if (!project) return "";
  return [
    `画面主体必须是产品：${project.product}。`,
    `项目/账号名「${project.project_name}」只作为业务上下文，不是画面主体；不要把项目名里的词生成成实物、图标或文字。`,
    `行业：${project.industry} / ${project.sub_industry || "未填写"}。`,
    `画面要求：自然光、真实质感、风格与参考图一致。`,
    `不要出现乱码文字，不要出现夸张特效，整体风格高级、可信、清透。`,
  ].join("\n");
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
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

function imageDisplayUrl(image: GeneratedImage | undefined) {
  if (!image) return "";
  return image.url || image.data_url || (image.b64_json ? `data:${image.mime_type || "image/png"};base64,${image.b64_json}` : "");
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

export default function ImagesPage() {
  const router = useRouter();
  const params = useParams();
  const searchParams = useSearchParams();
  const projectId = Number(params.id);

  const [project, setProject] = useState<Project | null>(null);
  const [loadingProject, setLoadingProject] = useState(true);
  const [mode, setMode] = useState<GenMode>("text");

  const [textPrompt, setTextPrompt] = useState("");
  const [editPrompt, setEditPrompt] = useState("");

  const [referenceImages, setReferenceImages] = useState<Record<RefType, LocalReferenceImage[]>>({
    persona: [],
    product: [],
    location: [],
  });

  const [size, setSize] = useState<ImageSize>("1024x1536");
  const [quality, setQuality] = useState<ImageQuality>("medium");
  const [n, setN] = useState(1);

  const [generating, setGenerating] = useState(false);
  const [enhancingPrompt, setEnhancingPrompt] = useState(false);
  const [, setTask] = useState<TaskStatus | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [result, setResult] = useState<ImageGenerateResponse | null>(null);
  const [error, setError] = useState("");
  const [refImagesLoading, setRefImagesLoading] = useState(false);
  const [history, setHistory] = useState<DigitalAsset[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const fetchProject = useCallback(async () => {
    setLoadingProject(true);
    try {
      const data = await getProject(projectId);
      setProject(data);
      setTextPrompt(buildDefaultTextPrompt(data));
      setEditPrompt(buildDefaultEditPrompt(data));
    } catch {
      router.push("/projects");
    } finally {
      setLoadingProject(false);
    }
  }, [projectId, router]);

  useEffect(() => {
    fetchProject();
  }, [fetchProject]);

  // 加载已持久化的参考图
  useEffect(() => {
    if (!projectId) return;
    setRefImagesLoading(true);
    listProjectReferenceImages(projectId)
      .then((images) => {
        const byType: Record<RefType, LocalReferenceImage[]> = {
          persona: [],
          product: [],
          location: [],
        };
        let referenceIndex = 1;
        for (const img of images) {
          const type = img.reference_image_type as RefType;
          if (!byType[type]) continue;
          const prefix = img.source_image_base64.startsWith("data:")
            ? ""
            : `data:${img.source_image_mime};base64,`;
          byType[type].push({
            id: `backend-${img.id}`,
            backendId: img.id,
            reference_image_type: type,
            source_image_base64: img.source_image_base64,
            source_image_mime: img.source_image_mime,
            source_image_filename: img.source_image_filename,
            reference_image_name: `@图片${referenceIndex}`,
            preview: prefix + img.source_image_base64,
            selected: true,
          });
          referenceIndex += 1;
        }
        setReferenceImages(byType);
      })
      .catch(() => {
        // 静默失败，保持本地空状态
      })
      .finally(() => setRefImagesLoading(false));
  }, [projectId]);

  // 处理从选题页面跳转过来的参数
  useEffect(() => {
    const promptParam = searchParams.get("prompt");
    if (!promptParam) return;
    const modeParam = searchParams.get("mode");
    if (modeParam === "reference") {
      setMode("image");
      setEditPrompt(promptParam);
    } else {
      setMode("text");
      setTextPrompt(promptParam);
    }
  }, [searchParams]);

  const currentPrompt = mode === "text" ? textPrompt : editPrompt;
  const flatReferenceImages = Object.values(referenceImages).flat();
  const promptImageReferenceNames = extractImageReferenceNames(editPrompt);
  const activeReferenceImages = flatReferenceImages.filter(
    (img) =>
      img.selected ||
      (Boolean(img.reference_image_name) &&
        promptImageReferenceNames.has(normalizeImageReferenceName(img.reference_image_name))),
  );
  const unknownPromptImageReferences = Array.from(promptImageReferenceNames).filter(
    (name) => !flatReferenceImages.some((img) => normalizeImageReferenceName(img.reference_image_name) === name),
  );
  function updatePrompt(value: string) {
    if (mode === "text") setTextPrompt(value);
    else setEditPrompt(value);
  }

  function refsByType(type: RefType) {
    return referenceImages[type];
  }

  const totalRefCount = Object.values(referenceImages).reduce((sum, arr) => sum + arr.length, 0);

  function nextReferenceImageName(existing: LocalReferenceImage[]) {
    const maxNumber = existing.reduce((max, img) => {
      const match = normalizeImageReferenceName(img.reference_image_name).match(/^@图片(\d+)$/);
      return match ? Math.max(max, Number(match[1])) : max;
    }, 0);
    return `@图片${maxNumber + 1}`;
  }

  function toggleReferenceImage(type: RefType, id: string) {
    setReferenceImages((prev) => ({
      ...prev,
      [type]: prev[type].map((img) => (img.id === id ? { ...img, selected: !img.selected } : img)),
    }));
  }

  function appendReferenceMention(referenceName: string | undefined) {
    const normalized = normalizeImageReferenceName(referenceName);
    if (!normalized) return;
    setEditPrompt((prev) => `${prev}${prev.trim() ? " " : ""}${normalized}`);
  }

  async function handleReferenceImageChange(event: React.ChangeEvent<HTMLInputElement>, type: RefType) {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;

    const availableSlots = 3 - refsByType(type).length;
    if (availableSlots <= 0) {
      alert("每类参考图最多上传 3 张");
      event.target.value = "";
      return;
    }

    const supported = ["image/png", "image/jpeg", "image/jpg", "image/webp"];
    const newImages: LocalReferenceImage[] = [];

    for (const file of files.slice(0, availableSlots)) {
      if (!supported.includes(file.type.toLowerCase())) {
        alert("参考图仅支持 PNG、JPEG、WebP");
        continue;
      }
      try {
        const dataUrl = await readFileAsDataUrl(file);
        const base64 = dataUrl.split(",", 2)[1] || "";
        // 上传到后端持久化
        const persisted = await createProjectReferenceImage(projectId, {
          reference_image_type: type,
          source_image_base64: base64,
          source_image_mime: file.type || "image/png",
          source_image_filename: file.name || "source.png",
        });
        const referenceName = nextReferenceImageName([...Object.values(referenceImages).flat(), ...newImages]);
        newImages.push({
          id: `backend-${persisted.id}`,
          backendId: persisted.id,
          reference_image_type: type,
          source_image_base64: persisted.source_image_base64,
          source_image_mime: persisted.source_image_mime,
          source_image_filename: persisted.source_image_filename,
          reference_image_name: referenceName,
          preview: dataUrl,
          selected: true,
        });
      } catch {
        alert("参考图上传失败");
      }
    }

    if (newImages.length) {
      setReferenceImages((prev) => ({
        ...prev,
        [type]: [...prev[type], ...newImages],
      }));
    }
    event.target.value = "";
  }

  async function removeReferenceImage(type: RefType, id: string) {
    const img = referenceImages[type].find((i) => i.id === id);
    if (img?.backendId) {
      try {
        await deleteProjectReferenceImage(projectId, img.backendId);
      } catch {
        alert("删除参考图失败");
        return;
      }
    }
    setReferenceImages((prev) => ({
      ...prev,
      [type]: prev[type].filter((i) => i.id !== id),
    }));
  }

  async function clearReferenceImages(type: RefType) {
    const toDelete = referenceImages[type];
    for (const img of toDelete) {
      if (img.backendId) {
        try {
          await deleteProjectReferenceImage(projectId, img.backendId);
        } catch {
          // 继续删除其他
        }
      }
    }
    setReferenceImages((prev) => ({ ...prev, [type]: [] }));
  }

  async function loadHistory() {
    if (!projectId) return;
    setHistoryLoading(true);
    try {
      const assets = await listProjectDigitalAssets(projectId, "image");
      setHistory(assets);
    } catch {
      // 静默失败
    } finally {
      setHistoryLoading(false);
    }
  }

  useEffect(() => {
    loadHistory();
  }, [projectId]);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback((taskId: number) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const res = await api.get<TaskStatus>(`/api/generation-tasks/${taskId}`);
        setTask(res);
        if (res.status === "succeeded" || res.status === "failed") {
          stopPolling();
          setGenerating(false);
          if (res.status === "succeeded" && res.result_data) {
            setResult(res.result_data);
            await loadHistory();
          } else if (res.status === "failed") {
            setError(res.error_message || "图片生成失败");
          }
        }
      } catch {
        // Keep polling through transient network/proxy errors.
      }
    }, 3000);
  }, [stopPolling]);

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  async function handleGenerate() {
    const cleanPrompt = currentPrompt.trim();
    if (!cleanPrompt) {
      alert("请输入图片生成提示词");
      return;
    }
    if (mode === "image" && totalRefCount < 1) {
      alert("图片生成至少要上传一张参考图");
      return;
    }
    if (mode === "image" && unknownPromptImageReferences.length > 0) {
      alert(`这些图片引用不存在：${unknownPromptImageReferences.join("、")}`);
      return;
    }
    if (mode === "image" && activeReferenceImages.length < 1) {
      alert("请至少选中一张参考图，或在提示词中引用 @图片N");
      return;
    }

    setGenerating(true);
    setTask(null);
    setResult(null);
    setError("");
    stopPolling();

    try {
      const res =
        mode === "image"
          ? await editImageAsync(
              projectId,
              cleanPrompt,
              activeReferenceImages.map(({ id, preview, backendId, selected, ...rest }) => rest),
              n,
              size,
              quality
            )
          : await generateImageAsync(projectId, cleanPrompt, n, size, quality);
      setTask({ id: res.task_id, status: res.status as TaskStatus["status"], result_data: null, error_message: null });
      startPolling(res.task_id);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "图片生成失败";
      setError(msg);
      setGenerating(false);
    }
  }

  async function handleEnhancePrompt() {
    const cleanPrompt = currentPrompt.trim();
    if (!cleanPrompt) {
      alert("请输入需要优化的提示词");
      return;
    }
    setEnhancingPrompt(true);
    setError("");
    try {
      const response = await enhanceImagePrompt(projectId || null, cleanPrompt, mode, size, quality);
      updatePrompt(response.enhanced_prompt);
    } catch (err) {
      setError(err instanceof Error ? err.message : "提示词优化失败");
    } finally {
      setEnhancingPrompt(false);
    }
  }

  async function copyImageUrl(url: string | undefined) {
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      alert("已复制图片链接");
    } catch {
      alert("复制失败");
    }
  }

  async function copyPromptText(promptText: string) {
    if (!promptText) return;
    try {
      await navigator.clipboard.writeText(promptText);
      alert("已复制提示词");
    } catch {
      alert("复制失败");
    }
  }

  function downloadImage(url: string | undefined) {
    if (!url) return;
    const link = document.createElement("a");
    link.href = url;
    link.download = `jsvoc-${mode}-${projectId}-${Date.now()}.png`;
    link.click();
  }

  function reusePrompt(prompt: string | null) {
    if (!prompt) return;
    if (mode === "text") {
      setTextPrompt(prompt);
    } else {
      setEditPrompt(prompt);
    }
  }

  async function removeHistoryItem(assetId: number) {
    try {
      await deleteDigitalAsset(assetId);
      setHistory((prev) => prev.filter((item) => item.id !== assetId));
    } catch {
      alert("删除失败");
    }
  }

  const firstImageUrl = imageDisplayUrl(result?.images?.[0]);

  return (
    <section className="page-section">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="section-header"
      >
        <div>
          <p className="eyebrow">Image Generation</p>
          <ProjectModuleTitle projectName={project?.project_name} moduleName="图片生成" />
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

      {/* Mode Tabs */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
        className="image-mode-tabs flex items-center gap-2 mb-5"
      >
        <button
          onClick={() => setMode("text")}
          className={`metal-btn ${mode === "text" ? "metal-btn-primary" : ""}`}
        >
          <span className="text-sm">图片</span>
          <span className="text-xs opacity-70 ml-1">输入提示词直接生成</span>
        </button>
        <button
          onClick={() => setMode("image")}
          className={`metal-btn ${mode === "image" ? "metal-btn-primary" : ""}`}
        >
          <span className="text-sm">图片</span>
          <span className="text-xs opacity-70 ml-1">上传参考图再改图</span>
        </button>
      </motion.div>

      <AnimatePresence mode="wait">
        {mode === "text" ? (
          <motion.div
            key="text"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 10 }}
            transition={{ duration: 0.25 }}
          >
            {/* 图片：简洁布局 */}
            <div className="glass card-hover p-5 mb-6">
              <div className="flex flex-col gap-4">
                <div>
                  <label className="text-[12px] font-[540] text-[#9ca3af] mb-1.5 block">提示词</label>
                  <textarea
                    className="input-glass w-full min-h-[120px] resize-y"
                    placeholder="描述你想生成的图片内容..."
                    value={textPrompt}
                    onChange={(e) => setTextPrompt(e.target.value)}
                  />
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <GlassSelect
                    label="尺寸"
                    value={size}
                    onChange={(v) => setSize(v as ImageSize)}
                    options={sizeOptions}
                    renderLabel={(v) => sizeLabels[v as ImageSize] || String(v)}
                  />
                  <GlassSelect
                    label="质量"
                    value={quality}
                    onChange={(v) => setQuality(v as ImageQuality)}
                    options={qualityOptions}
                    renderLabel={(v) => qualityLabels[v as ImageQuality] || String(v)}
                  />
                  <GlassSelect label="数量" value={n} onChange={(v) => setN(Number(v))} options={countOptions} />
                </div>
                <div className="image-action-row flex justify-end gap-2">
                  <button
                    onClick={() => setTextPrompt(buildDefaultTextPrompt(project))}
                    className="image-action-btn metal-btn text-sm"
                  >
                    重置提示词
                  </button>
                  <button
                    onClick={handleEnhancePrompt}
                    disabled={enhancingPrompt || generating}
                    className="image-action-btn metal-btn text-sm"
                  >
                    {enhancingPrompt ? (
                      <span className="flex items-center gap-2">
                        <span className="btn-spinner" />
                        优化中
                      </span>
                    ) : (
                      "提示词优化"
                    )}
                  </button>
                  <button onClick={handleGenerate} disabled={generating} className="image-action-btn metal-btn metal-btn-primary">
                    {generating ? (
                      <span className="flex items-center gap-2">
                        <span className="btn-spinner" />
                        生成中
                      </span>
                    ) : (
                      "生成图片"
                    )}
                  </button>
                </div>
              </div>
            </div>

            {generating ? (
              <div className="glass p-0 overflow-hidden">
                <TypingIndicator text="AI 正在绘制图片..." />
                <div className="px-4 pb-4 space-y-3">
                  <div className="h-3 bg-[rgba(99,102,241,0.08)] rounded w-3/4 animate-pulse" />
                  <div className="h-3 bg-[rgba(99,102,241,0.06)] rounded w-full animate-pulse" />
                </div>
              </div>
            ) : null}

            {error && !result ? (
              <div className="glass p-5 mb-6 border-l-4 border-l-red-500">
                <p className="text-sm text-red-400">{error}</p>
              </div>
            ) : null}

            {result ? <ResultGallery result={result} onCopy={copyImageUrl} onDownload={downloadImage} /> : null}
          </motion.div>
        ) : (
          <motion.div
            key="image"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 10 }}
            transition={{ duration: 0.25 }}
            className="grid grid-cols-1 lg:grid-cols-[400px_1fr] gap-5"
          >
            {/* 左侧：参考图 + 提示词 + 参数 */}
            <div className="flex flex-col gap-3">
              {/* 参考图卡片 */}
              {(["persona", "product", "location"] as RefType[]).map((type) => (
                <div
                  key={type}
                  className="glass card-hover p-3 flex flex-col gap-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[13px] font-medium text-[#f5f5f5]">{refMeta[type].label}</span>
                    <span className="text-xs text-[#6b7280] bg-[rgba(255,255,255,0.04)] px-2 py-0.5 rounded-full">
                      {refsByType(type).length}/3
                    </span>
                  </div>
                  <p className="text-[10px] leading-4 text-[#6b7280]">{refMeta[type].note}</p>

                  {refsByType(type).length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {refsByType(type).map((img) => {
                        const isActive =
                          img.selected ||
                          promptImageReferenceNames.has(normalizeImageReferenceName(img.reference_image_name));
                        return (
                        <div
                          key={img.id}
                          onClick={() => toggleReferenceImage(type, img.id)}
                          className="flat-delete-target w-[68px] h-[68px] cursor-pointer rounded-[0.45rem] overflow-hidden border transition-colors"
                          style={{
                            borderColor: isActive ? "rgba(127,220,146,0.5)" : "rgba(255,255,255,0.06)",
                            background: isActive ? "rgba(127,220,146,0.08)" : "rgba(255,255,255,0.03)",
                          }}
                        >
                          <img src={img.preview} alt={img.source_image_filename} className="w-full h-full object-cover" />
                          {img.reference_image_name ? (
                            <button
                              type="button"
                              onClick={(event) => {
                                event.stopPropagation();
                                appendReferenceMention(img.reference_image_name);
                              }}
                              className="absolute left-1 bottom-1 rounded bg-[rgba(0,0,0,0.62)] px-1.5 py-0.5 text-[10px] font-semibold leading-none text-white"
                              title={`插入 ${img.reference_image_name}`}
                            >
                              {img.reference_image_name}
                            </button>
                          ) : null}
                          <button
                            onClick={(event) => {
                              event.stopPropagation();
                              removeReferenceImage(type, img.id);
                            }}
                            className="flat-delete-action"
                            title="删除"
                            aria-label="删除参考图"
                          >
                            <X size={13} weight="bold" />
                          </button>
                        </div>
                        );
                      })}
                    </div>
                  )}

                  <label className="flex flex-col items-center justify-center gap-0.5 min-h-[52px] rounded-[0.65rem] border border-dashed border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.02)] cursor-pointer hover:bg-[rgba(255,255,255,0.04)] transition-colors">
                    <input
                      type="file"
                      accept="image/*"
                      multiple
                      className="hidden"
                      onChange={(e) => handleReferenceImageChange(e, type)}
                    />
                    <span className="text-[12px] text-[#9ca3af]">上传{refMeta[type].label}</span>
                    <span className="text-xs text-[#6b7280]">最少 0 张，最多 3 张</span>
                  </label>

                  {refsByType(type).length > 0 && (
                    <button
                      onClick={() => clearReferenceImages(type)}
                      className="text-[11px] text-[#6b7280] hover:text-[#f5f5f5] self-end transition-colors"
                    >
                      清空本类
                    </button>
                  )}
                </div>
              ))}

              <p className="text-[11px] text-[#6b7280]">
                图片至少上传 1 张参考图；没有人设参考图时，只生成货品和场景，不生成可识别人设本人。
              </p>

              {/* 提示词 */}
              <div className="glass card-hover p-4">
                <label className="text-[12px] font-[540] text-[#9ca3af] mb-1.5 block">图片提示词</label>
                <textarea
                  className="input-glass w-full min-h-[340px] resize-y leading-7"
                  placeholder="@图片1 和 @图片2 一起去 @图片3 吃饭，保持各自外观特征和场景关系"
                  value={editPrompt}
                  onChange={(e) => setEditPrompt(e.target.value)}
                />
                {totalRefCount > 0 && (
                  <p className="mt-2 text-[12px] text-[#6b7280]">
                    本次使用 {activeReferenceImages.length} / {totalRefCount} 张参考图。点击图片可选中/取消，点击 @图片N 可插入提示词。
                  </p>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3">
                  <GlassSelect
                    label="尺寸"
                    value={size}
                    onChange={(v) => setSize(v as ImageSize)}
                    options={sizeOptions}
                    renderLabel={(v) => sizeLabels[v as ImageSize] || String(v)}
                  />
                  <GlassSelect
                    label="质量"
                    value={quality}
                    onChange={(v) => setQuality(v as ImageQuality)}
                    options={qualityOptions}
                    renderLabel={(v) => qualityLabels[v as ImageQuality] || String(v)}
                  />
                  <GlassSelect label="数量" value={n} onChange={(v) => setN(Number(v))} options={countOptions} />
                </div>
                <div className="image-action-row flex justify-end gap-2 mt-3">
                  <button
                    onClick={() => setEditPrompt(buildDefaultEditPrompt(project))}
                    className="image-action-btn metal-btn text-sm"
                  >
                    重置提示词
                  </button>
                  <button
                    onClick={handleEnhancePrompt}
                    disabled={enhancingPrompt || generating}
                    className="image-action-btn metal-btn text-sm"
                  >
                    {enhancingPrompt ? (
                      <span className="flex items-center gap-2">
                        <span className="btn-spinner" />
                        优化中
                      </span>
                    ) : (
                      "提示词优化"
                    )}
                  </button>
                  <button onClick={handleGenerate} disabled={generating} className="image-action-btn metal-btn metal-btn-primary">
                    {generating ? (
                      <span className="flex items-center gap-2">
                        <span className="btn-spinner" />
                        图片生成中
                      </span>
                    ) : (
                      "按图生成"
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* 右侧：结果预览 */}
            <div className="flex flex-col gap-4">
              {generating ? (
                <div className="glass p-0 overflow-hidden">
                  <TypingIndicator text="AI 正在按参考图改图..." />
                  <div className="px-4 pb-4 space-y-3">
                    <div className="h-3 bg-[rgba(99,102,241,0.08)] rounded w-3/4 animate-pulse" />
                    <div className="h-3 bg-[rgba(99,102,241,0.06)] rounded w-full animate-pulse" />
                  </div>
                </div>
              ) : null}

              {error && !result ? (
                <div className="glass p-5 border-l-4 border-l-red-500">
                  <p className="text-sm text-red-400">{error}</p>
                </div>
              ) : null}

              {result ? (
                <div className="glass card-hover p-5">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <AIGeneratedBadge />
                      <span className="text-[13px] text-[#9ca3af]">
                        Provider：{result.provider} / Model：{result.model} / {result.latency_ms}ms
                      </span>
                    </div>
                  </div>

                  {firstImageUrl ? (
                    <img
                      src={firstImageUrl}
                      alt="生成图片"
                      className="w-full rounded-[0.75rem] object-cover"
                    />
                  ) : (
                    <div className="w-full h-[300px] flex items-center justify-center text-[#6b7280] text-sm">
                      图片数据不可用
                    </div>
                  )}

                  <div className="flex gap-2 mt-4">
                    {result.images[0]?.url && (
                      <button
                        onClick={() => copyImageUrl(result.images[0].url)}
                        className="btn btn-ghost text-xs"
                        style={{ minHeight: 28, padding: "0 10px" }}
                      >
                        复制链接
                      </button>
                    )}
                    {result.images[0]?.url && (
                      <a
                        href={result.images[0].url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-ghost text-xs"
                        style={{ minHeight: 28, padding: "0 10px" }}
                      >
                        查看原图
                      </a>
                    )}
                    {firstImageUrl && (
                      <button
                        onClick={() => downloadImage(firstImageUrl)}
                        className="btn btn-ghost text-xs"
                        style={{ minHeight: 28, padding: "0 10px" }}
                      >
                        下载
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                <div className="glass card-hover p-8 flex flex-col items-center justify-center min-h-[400px] text-[#6b7280]">
                  <span className="text-2xl mb-2">IMG</span>
                  <p className="text-sm">上传参考图并输入提示词后，生成结果将显示在这里</p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 生成记录 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
        className="mt-8"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-[#f5f5f5]">生成记录</h2>
          {historyLoading && <span className="text-xs text-[#6b7280]">加载中...</span>}
        </div>

        {history.length === 0 && !historyLoading ? (
          <div className="glass p-6 text-center text-[#6b7280] text-sm">
            暂无生成记录
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {history.map((item) => {
              const promptText = digitalAssetPrompt(item);
              return (
              <div key={item.id} className="glass card-hover flat-delete-target p-3 flex flex-col gap-2">
                <button
                  onClick={() => removeHistoryItem(item.id)}
                  className="flat-delete-action"
                  title="删除"
                  aria-label="删除生成记录"
                >
                  <X size={13} weight="bold" />
                </button>
                <div className="relative aspect-square rounded-[0.5rem] overflow-hidden bg-[rgba(255,255,255,0.03)]">
                  {item.access_url ? (
                    <img
                      src={item.access_url}
                      alt={item.title}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-[#6b7280] text-xs">
                      图片不可用
                    </div>
                  )}
                </div>
                <p className="text-xs text-[#9ca3af] line-clamp-3" title={promptText}>
                  {promptText}
                </p>
                <div className="flex items-center justify-between gap-1">
                  <span className="text-[10px] text-[#6b7280]">
                    {new Date(item.created_at).toLocaleDateString()}
                  </span>
                  <div className="flex gap-1">
                    <button
                      onClick={() => reusePrompt(promptText)}
                      className="text-[10px] text-[#5a9b82] hover:text-[#7bc4a8] transition-colors"
                    >
                      复用提示词
                    </button>
                    <button
                      onClick={() => copyPromptText(promptText)}
                      className="text-[10px] text-[#9ca3af] hover:text-[#f5f5f5] transition-colors"
                    >
                      复制
                    </button>
                  </div>
                </div>
              </div>
            );
            })}
          </div>
        )}
      </motion.div>
    </section>
  );
}

function ResultGallery({
  result,
  onCopy,
  onDownload,
}: {
  result: ImageGenerateResponse;
  onCopy: (url?: string) => void;
  onDownload: (url?: string) => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <AIGeneratedBadge />
          <span className="text-[13px] text-[#9ca3af]">
            Provider：{result.provider} / Model：{result.model} / {result.latency_ms}ms
          </span>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {result.images.map((img, idx) => {
          const imageUrl = imageDisplayUrl(img);
          return (
          <div key={idx} className="glass card-hover p-4 ai-context-card">
            {imageUrl ? (
              <img
                src={imageUrl}
                alt={`生成图片 ${idx + 1}`}
                className="w-full rounded-[0.75rem] object-cover"
                loading="lazy"
              />
            ) : (
              <div className="w-full h-[200px] flex items-center justify-center text-[#6b7280] text-sm">
                图片数据不可用
              </div>
            )}
            <div className="flex gap-2 mt-3">
              {img.url && (
                <button
                  onClick={() => onCopy(img.url)}
                  className="btn btn-ghost text-xs"
                  style={{ minHeight: 28, padding: "0 10px" }}
                >
                  复制链接
                </button>
              )}
              {img.url && (
                <a
                  href={img.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-ghost text-xs"
                  style={{ minHeight: 28, padding: "0 10px" }}
                >
                  查看原图
                </a>
              )}
              {imageUrl && (
                <button
                  onClick={() => onDownload(imageUrl)}
                  className="btn btn-ghost text-xs"
                  style={{ minHeight: 28, padding: "0 10px" }}
                >
                  下载
                </button>
              )}
            </div>
          </div>
          );
        })}
      </div>
    </motion.div>
  );
}
