"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "@phosphor-icons/react";
import { api } from "@/lib/api/client";
import {
  editImageAsync,
  enhanceImagePrompt,
  generateImageAsync,
  type GeneratedImage,
  type ImageGenerateResponse,
  type ImageQuality,
  type ImageReferenceInput,
  type ImageSize,
} from "@/lib/api/images";
import TypingIndicator from "@/components/ui/TypingIndicator";
import AIGeneratedBadge from "@/components/ui/AIGeneratedBadge";
import GlassSelect from "@/components/ui/GlassSelect";

type GenMode = "text" | "image";
type RefType = "persona" | "product" | "location";

interface LocalReferenceImage extends ImageReferenceInput {
  id: string;
  preview: string;
}

interface TaskStatus {
  id: number;
  status: "queued" | "running" | "succeeded" | "failed";
  result_data: ImageGenerateResponse | null;
  error_message: string | null;
}

const refMeta: Record<RefType, { label: string; note: string }> = {
  persona: {
    label: "人设参考图",
    note: "人物、模特、账号本人等参考，只在本次生成中使用。",
  },
  product: {
    label: "货品参考图",
    note: "产品、包装、材质、细节等参考，只在本次生成中使用。",
  },
  location: {
    label: "场景参考图",
    note: "店铺、街景、办公室、直播间等参考，只在本次生成中使用。",
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
  "2048x1152": "2K 横屏 2048x1152",
  "1152x2048": "2K 竖屏 1152x2048",
  auto: "自动",
};
const qualityLabels: Record<ImageQuality, string> = {
  high: "高清（high）",
  medium: "标准（medium）",
  low: "快速（low）",
  auto: "自动（auto）",
};

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

function imageDisplayUrl(image: GeneratedImage) {
  return image.url || image.data_url || (image.b64_json ? `data:${image.mime_type || "image/png"};base64,${image.b64_json}` : "");
}

export default function ImagesEntryPage() {
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
  const [result, setResult] = useState<ImageGenerateResponse | null>(null);
  const [error, setError] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const referenceImageIdRef = useRef(0);

  const currentPrompt = mode === "text" ? textPrompt : editPrompt;
  const totalRefCount = Object.values(referenceImages).reduce((sum, arr) => sum + arr.length, 0);

  function updatePrompt(value: string) {
    if (mode === "text") setTextPrompt(value);
    else setEditPrompt(value);
  }

  function refsByType(type: RefType) {
    return referenceImages[type];
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

      const dataUrl = await readFileAsDataUrl(file);
      const base64 = dataUrl.split(",", 2)[1] || "";
      const imageId = `${type}-${referenceImageIdRef.current}-${file.name}`;
      referenceImageIdRef.current += 1;
      newImages.push({
        id: imageId,
        reference_image_type: type,
        source_image_base64: base64,
        source_image_mime: file.type || "image/png",
        source_image_filename: file.name || "source.png",
        preview: dataUrl,
      });
    }

    if (newImages.length) {
      setReferenceImages((prev) => ({ ...prev, [type]: [...prev[type], ...newImages] }));
    }
    event.target.value = "";
  }

  function removeReferenceImage(type: RefType, id: string) {
    setReferenceImages((prev) => ({ ...prev, [type]: prev[type].filter((img) => img.id !== id) }));
  }

  function clearReferenceImages(type: RefType) {
    setReferenceImages((prev) => ({ ...prev, [type]: [] }));
  }

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
          } else {
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
      alert("图生图至少要上传一张参考图");
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
              null,
              cleanPrompt,
              Object.values(referenceImages).flat().map(({ id, preview, ...rest }) => rest),
              n,
              size,
              quality
            )
          : await generateImageAsync(null, cleanPrompt, n, size, quality);
      setTask({ id: res.task_id, status: res.status as TaskStatus["status"], result_data: null, error_message: null });
      startPolling(res.task_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "图片生成失败");
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
      const response = await enhanceImagePrompt(null, cleanPrompt, mode, size, quality);
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

  function downloadImage(url: string | undefined) {
    if (!url) return;
    const link = document.createElement("a");
    link.href = url;
    link.download = `jsvoc-global-${mode}-${Date.now()}.png`;
    link.click();
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
          <p className="eyebrow">Image Generation</p>
          <h1 className="text-[28px] md:text-[36px] font-bold leading-[1.15] tracking-[-0.02em] text-[#f5f5f5]">
            AI图片生成
          </h1>
        </div>
      </motion.div>

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
          <span className="text-sm">文生图</span>
          <span className="text-xs opacity-70 ml-1">输入提示词直接生成</span>
        </button>
        <button
          onClick={() => setMode("image")}
          className={`metal-btn ${mode === "image" ? "metal-btn-primary" : ""}`}
        >
          <span className="text-sm">图生图</span>
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
            <div className="glass card-hover p-5 mb-6">
              <div className="flex flex-col gap-4">
                <div>
                  <label className="text-[12px] font-[540] text-[#9ca3af] mb-1.5 block">提示词</label>
                  <textarea
                    className="input-glass w-full min-h-[150px] resize-y"
                    placeholder="描述你想生成的图片内容。全局入口不会自动带入任何项目、账号或人设。"
                    value={textPrompt}
                    onChange={(e) => setTextPrompt(e.target.value)}
                  />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
                  <button onClick={() => setTextPrompt("")} className="image-action-btn metal-btn text-sm">
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

            {generating ? <ImageLoadingState text="AI 正在绘制图片..." /> : null}
            {error && !result ? <ErrorState error={error} /> : null}
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
            <div className="flex flex-col gap-3">
              {(["persona", "product", "location"] as RefType[]).map((type) => (
                <div key={type} className="glass card-hover p-3 flex flex-col gap-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[13px] font-medium text-[#f5f5f5]">{refMeta[type].label}</span>
                    <span className="text-xs text-[#6b7280] bg-[rgba(255,255,255,0.04)] px-2 py-0.5 rounded-full">
                      {refsByType(type).length}/3
                    </span>
                  </div>
                  <p className="text-[10px] leading-4 text-[#6b7280]">{refMeta[type].note}</p>

                  {refsByType(type).length > 0 && (
                    <div className="flex flex-wrap gap-2">
                      {refsByType(type).map((img) => (
                        <div key={img.id} className="flat-delete-target w-[56px] h-[56px] rounded-[0.45rem] overflow-hidden border border-[rgba(255,255,255,0.06)]">
                          <img src={img.preview} alt={img.source_image_filename} className="w-full h-full object-cover" />
                          <button
                            onClick={() => removeReferenceImage(type, img.id)}
                            className="flat-delete-action"
                            title="删除"
                            aria-label="删除参考图"
                          >
                            <X size={13} weight="bold" />
                          </button>
                        </div>
                      ))}
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
                    <span className="text-xs text-[#6b7280]">最多 3 张</span>
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
            </div>

            <div className="flex flex-col gap-4">
              <div className="glass card-hover p-5">
                <label className="text-[12px] font-[540] text-[#9ca3af] mb-1.5 block">图片提示词</label>
                <textarea
                  className="input-glass w-full min-h-[260px] resize-y leading-7"
                  placeholder="上传参考图后，描述你想保留、调整、替换或增强的画面内容。"
                  value={editPrompt}
                  onChange={(e) => setEditPrompt(e.target.value)}
                />
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
                  <button onClick={() => setEditPrompt("")} className="image-action-btn metal-btn text-sm">
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
                      "按图生成"
                    )}
                  </button>
                </div>
              </div>

              {generating ? <ImageLoadingState text="AI 正在按参考图改图..." /> : null}
              {error && !result ? <ErrorState error={error} /> : null}
              {result ? (
                <ResultGallery result={result} onCopy={copyImageUrl} onDownload={downloadImage} />
              ) : (
                <div className="glass card-hover p-8 flex flex-col items-center justify-center min-h-[320px] text-[#6b7280]">
                  <span className="text-2xl mb-2">IMG</span>
                  <p className="text-sm">上传参考图并输入提示词后，生成结果将显示在这里</p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}

function ImageLoadingState({ text }: { text: string }) {
  return (
    <div className="glass p-0 overflow-hidden mb-6">
      <TypingIndicator text={text} />
      <div className="px-4 pb-4 space-y-3">
        <div className="h-3 bg-[rgba(99,102,241,0.08)] rounded w-3/4 animate-pulse" />
        <div className="h-3 bg-[rgba(99,102,241,0.06)] rounded w-full animate-pulse" />
      </div>
    </div>
  );
}

function ErrorState({ error }: { error: string }) {
  return (
    <div className="glass p-5 mb-6 border-l-4 border-l-red-500">
      <p className="text-sm text-red-400">{error}</p>
    </div>
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
