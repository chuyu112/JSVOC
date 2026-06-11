"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api/client";
import {
  createProjectReferenceImage,
  deleteDigitalAsset,
  deleteProjectReferenceImage,
  editImageAsync,
  enhanceImagePrompt,
  generateImageAsync,
  listProjectDigitalAssets,
  listProjectReferenceImages,
  type DigitalAsset,
  type ImageGenerateResponse,
  type ImageQuality,
  type ImageSize,
} from "@/lib/api/images";
import { getProject, type Project } from "@/lib/api/projects";
import ImageStudioWorkspace, {
  type ImageStudioHistoryItem,
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

function buildDefaultTextPrompt(project: Project | null): string {
  if (!project) return "";
  return [
    `画面主体必须是产品：${project.product}。`,
    `项目/账号名「${project.project_name}」只作为业务上下文，不是画面主体；不要把项目名里的词生成成实物、图标或文字。`,
    `行业：${project.industry} / ${project.sub_industry || "未填写"}。`,
    "生成一张高级清透的产品展示图：干净留白、柔和自然光、低饱和色调、真实产品质感。",
    "突出产品本身、材质纹理和关键细节，背景简洁不抢镜。",
    "不要出现乱码文字，不要出现夸张特效，整体风格高级、可信、清透。",
  ].join("\n");
}

function buildDefaultEditPrompt(project: Project | null): string {
  if (!project) return "";
  return [
    `画面主体必须是产品：${project.product}。`,
    `项目/账号名「${project.project_name}」只作为业务上下文，不是画面主体；不要把项目名里的词生成成实物、图标或文字。`,
    `行业：${project.industry} / ${project.sub_industry || "未填写"}。`,
    "画面要求：自然光、真实质感、风格与参考图一致。",
    "不要出现乱码文字，不要出现夸张特效，整体风格高级、可信、清透。",
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
  const [refImageCount, setRefImageCount] = useState(0);
  const [history, setHistory] = useState<DigitalAsset[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchProject = useCallback(async () => {
    setLoadingProject(true);
    try {
      const data = await getProject(projectId);
      setProject(data);
      setPrompt(buildDefaultTextPrompt(data));
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
    const promptParam = searchParams.get("prompt");
    if (promptParam) {
      setPrompt(promptParam);
    }
  }, [searchParams]);

  useEffect(() => {
    if (!projectId) return;
    listProjectReferenceImages(projectId)
      .then((images) => {
        const byType: Record<ImageStudioRefType, ImageStudioReferenceImage[]> = {
          persona: [],
          product: [],
          location: [],
        };
        let referenceIndex = 1;
        for (const image of images) {
          const type = image.reference_image_type as ImageStudioRefType;
          if (!byType[type]) continue;
          const prefix = image.source_image_base64.startsWith("data:")
            ? ""
            : `data:${image.source_image_mime};base64,`;
          byType[type].push({
            id: `backend-${image.id}`,
            backendId: image.id,
            reference_image_type: type,
            source_image_base64: image.source_image_base64,
            source_image_mime: image.source_image_mime,
            source_image_filename: image.source_image_filename,
            reference_image_name: `@图片${referenceIndex}`,
            preview: prefix + image.source_image_base64,
            selected: true,
          });
          referenceIndex += 1;
        }
        setReferenceImages(byType);
        setRefImageCount(images.length);
      })
      .catch(() => {
        setRefImageCount(0);
      });
  }, [projectId]);

  useEffect(() => {
    if (!project || refImageCount < 1 || searchParams.get("prompt")) return;
    const textDefault = buildDefaultTextPrompt(project);
    setPrompt((prev) => (!prev.trim() || prev === textDefault ? buildDefaultEditPrompt(project) : prev));
  }, [project, refImageCount, searchParams]);

  async function loadHistory() {
    if (!projectId) return;
    setHistoryLoading(true);
    try {
      const assets = await listProjectDigitalAssets(projectId, "image");
      setHistory(assets);
    } catch {
      // Keep the current history through transient API failures.
    } finally {
      setHistoryLoading(false);
    }
  }

  useEffect(() => {
    void loadHistory();
  }, [projectId]);

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
      try {
        const dataUrl = await readFileAsDataUrl(file);
        const base64 = dataUrl.split(",", 2)[1] || "";
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
      setReferenceImages((prev) => ({ ...prev, [type]: [...prev[type], ...newImages] }));
      setRefImageCount((prev) => prev + newImages.length);
    }
    event.target.value = "";
  }

  function toggleReferenceImage(type: ImageStudioRefType, id: string) {
    setReferenceImages((prev) => ({
      ...prev,
      [type]: prev[type].map((img) => (img.id === id ? { ...img, selected: !img.selected } : img)),
    }));
  }

  function appendReferenceMention(referenceName: string | undefined) {
    const normalized = normalizeImageReferenceName(referenceName);
    if (!normalized) return;
    setPrompt((prev) => `${prev}${prev.trim() ? " " : ""}${normalized}`);
  }

  async function removeReferenceImage(type: ImageStudioRefType, id: string) {
    const image = referenceImages[type].find((item) => item.id === id);
    if (image?.backendId) {
      try {
        await deleteProjectReferenceImage(projectId, image.backendId);
      } catch {
        alert("删除参考图失败");
        return;
      }
    }
    setReferenceImages((prev) => ({ ...prev, [type]: prev[type].filter((item) => item.id !== id) }));
    setRefImageCount((prev) => Math.max(0, prev - 1));
  }

  async function clearReferenceImages(type: ImageStudioRefType) {
    const toDelete = referenceImages[type];
    for (const image of toDelete) {
      if (image.backendId) {
        try {
          await deleteProjectReferenceImage(projectId, image.backendId);
        } catch {
          // Continue deleting the remaining local references.
        }
      }
    }
    setReferenceImages((prev) => ({ ...prev, [type]: [] }));
    setRefImageCount((prev) => Math.max(0, prev - toDelete.length));
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
              projectId,
              cleanPrompt,
              activeReferenceImages.map(({ id, preview, backendId, selected, ...rest }) => rest),
              n,
              size,
              quality,
            )
          : await generateImageAsync(projectId, cleanPrompt, n, size, quality);
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
      const response = await enhanceImagePrompt(projectId || null, cleanPrompt, mode, size, quality);
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

  async function removeHistoryItem(assetId: number) {
    try {
      await deleteDigitalAsset(assetId);
      setHistory((prev) => prev.filter((item) => item.id !== assetId));
    } catch {
      alert("删除失败");
    }
  }

  const historyItems: ImageStudioHistoryItem[] = history.map((item) => ({
    ...item,
    promptText: digitalAssetPrompt(item),
  }));

  return (
    <ImageStudioWorkspace
      title={
        <>
          <h1>{project?.project_name || "图片生成"}</h1>
          <span>图片生成</span>
        </>
      }
      subtitle={project ? `${project.product} / ${project.industry}` : "载入参考图自动进入图生图；不载入参考图就是文生图。"}
      headerAction={
        <Link href={`/projects/${projectId}`} className="image-studio-back">
          返回人设
        </Link>
      }
      loading={loadingProject}
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
      onResetPrompt={() => setPrompt(mode === "image" ? buildDefaultEditPrompt(project) : buildDefaultTextPrompt(project))}
      onReferenceUpload={handleReferenceImageChange}
      onToggleReference={toggleReferenceImage}
      onRemoveReference={removeReferenceImage}
      onClearReferenceType={clearReferenceImages}
      onInsertReferenceMention={appendReferenceMention}
      onCopyImageUrl={copyImageUrl}
      onDownloadImage={downloadImage}
      history={historyItems}
      historyLoading={historyLoading}
      onReusePrompt={setPrompt}
      onCopyPrompt={copyPromptText}
      onRemoveHistoryItem={removeHistoryItem}
    />
  );
}
