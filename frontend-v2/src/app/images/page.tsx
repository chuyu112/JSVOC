"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api/client";
import {
  editImageAsync,
  enhanceImagePrompt,
  generateImageAsync,
  type ImageGenerateResponse,
  type ImageQuality,
  type ImageSize,
} from "@/lib/api/images";
import ImageStudioWorkspace, {
  type ImageStudioMode,
  type ImageStudioReferenceImage,
  type ImageStudioRefType,
} from "@/components/ImageStudioWorkspace";

interface TaskStatus {
  id: number;
  status: "queued" | "running" | "succeeded" | "failed";
  result_data: ImageGenerateResponse | null;
  error_message: string | null;
}

const IMAGE_REFERENCE_PATTERN = /@图片(\d+)/g;
const EMPTY_REFERENCE_IMAGES: Record<ImageStudioRefType, ImageStudioReferenceImage[]> = {
  persona: [],
  product: [],
  location: [],
};

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

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

export default function ImagesEntryPage() {
  const [prompt, setPrompt] = useState("");
  const [referenceImages, setReferenceImages] =
    useState<Record<ImageStudioRefType, ImageStudioReferenceImage[]>>(EMPTY_REFERENCE_IMAGES);
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

  const flatReferenceImages = Object.values(referenceImages).flat();
  const promptImageReferenceNames = extractImageReferenceNames(prompt);
  const activeReferenceImages = flatReferenceImages.filter(
    (img) =>
      img.selected ||
      (Boolean(img.reference_image_name) &&
        promptImageReferenceNames.has(normalizeImageReferenceName(img.reference_image_name))),
  );
  const unknownPromptImageReferences = Array.from(promptImageReferenceNames).filter(
    (name) => !flatReferenceImages.some((img) => normalizeImageReferenceName(img.reference_image_name) === name),
  );
  const mode: ImageStudioMode = activeReferenceImages.length > 0 ? "image" : "text";

  function refsByType(type: ImageStudioRefType) {
    return referenceImages[type];
  }

  function nextReferenceImageName(existing: ImageStudioReferenceImage[]) {
    const maxNumber = existing.reduce((max, img) => {
      const match = normalizeImageReferenceName(img.reference_image_name).match(/^@图片(\d+)$/);
      return match ? Math.max(max, Number(match[1])) : max;
    }, 0);
    return `@图片${maxNumber + 1}`;
  }

  async function handleReferenceImageChange(event: React.ChangeEvent<HTMLInputElement>, type: ImageStudioRefType) {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;

    const availableSlots = 3 - refsByType(type).length;
    if (availableSlots <= 0) {
      alert("每类参考图最多上传 3 张");
      event.target.value = "";
      return;
    }

    const supported = ["image/png", "image/jpeg", "image/jpg", "image/webp"];
    const newImages: ImageStudioReferenceImage[] = [];

    for (const file of files.slice(0, availableSlots)) {
      if (!supported.includes(file.type.toLowerCase())) {
        alert("参考图仅支持 PNG、JPEG、WebP");
        continue;
      }

      const dataUrl = await readFileAsDataUrl(file);
      const base64 = dataUrl.split(",", 2)[1] || "";
      const imageId = `${type}-${referenceImageIdRef.current}-${file.name}`;
      referenceImageIdRef.current += 1;
      const referenceName = nextReferenceImageName([...Object.values(referenceImages).flat(), ...newImages]);
      newImages.push({
        id: imageId,
        reference_image_type: type,
        source_image_base64: base64,
        source_image_mime: file.type || "image/png",
        source_image_filename: file.name || "source.png",
        reference_image_name: referenceName,
        preview: dataUrl,
        selected: true,
      });
    }

    if (newImages.length) {
      setReferenceImages((prev) => ({ ...prev, [type]: [...prev[type], ...newImages] }));
    }
    event.target.value = "";
  }

  function toggleReferenceImage(type: ImageStudioRefType, id: string) {
    setReferenceImages((prev) => ({
      ...prev,
      [type]: prev[type].map((img) => (img.id === id ? { ...img, selected: !img.selected } : img)),
    }));
  }

  function removeReferenceImage(type: ImageStudioRefType, id: string) {
    setReferenceImages((prev) => ({ ...prev, [type]: prev[type].filter((img) => img.id !== id) }));
  }

  function clearReferenceImages(type: ImageStudioRefType) {
    setReferenceImages((prev) => ({ ...prev, [type]: [] }));
  }

  function appendReferenceMention(referenceName: string | undefined) {
    const normalized = normalizeImageReferenceName(referenceName);
    if (!normalized) return;
    setPrompt((prev) => `${prev}${prev.trim() ? " " : ""}${normalized}`);
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
    const cleanPrompt = prompt.trim();
    if (!cleanPrompt) {
      alert("请输入图片生成提示词");
      return;
    }
    if (unknownPromptImageReferences.length > 0) {
      alert(`这些图片引用不存在：${unknownPromptImageReferences.join("、")}`);
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
              activeReferenceImages.map(({ id, preview, backendId, selected, ...rest }) => rest),
              n,
              size,
              quality,
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
    const cleanPrompt = prompt.trim();
    if (!cleanPrompt) {
      alert("请输入需要优化的提示词");
      return;
    }

    setEnhancingPrompt(true);
    setError("");
    try {
      const response = await enhanceImagePrompt(null, cleanPrompt, mode, size, quality);
      setPrompt(response.enhanced_prompt);
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
    <ImageStudioWorkspace
      title={<h1>AI图片生成</h1>}
      subtitle="载入参考图自动进入图生图；不载入参考图就是文生图。"
      mode={mode}
      prompt={prompt}
      onPromptChange={setPrompt}
      referenceImages={referenceImages}
      activeReferenceImages={activeReferenceImages}
      unknownPromptImageReferences={unknownPromptImageReferences}
      size={size}
      onSizeChange={setSize}
      quality={quality}
      onQualityChange={setQuality}
      count={n}
      onCountChange={setN}
      generating={generating}
      enhancingPrompt={enhancingPrompt}
      result={result}
      error={error}
      onGenerate={handleGenerate}
      onEnhancePrompt={handleEnhancePrompt}
      onResetPrompt={() => setPrompt("")}
      onReferenceUpload={handleReferenceImageChange}
      onToggleReference={toggleReferenceImage}
      onRemoveReference={removeReferenceImage}
      onClearReferenceType={clearReferenceImages}
      onInsertReferenceMention={appendReferenceMention}
      onCopyImageUrl={copyImageUrl}
      onDownloadImage={downloadImage}
    />
  );
}
