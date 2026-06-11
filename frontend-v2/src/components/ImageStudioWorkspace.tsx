"use client";

import { type ChangeEvent, type ReactNode } from "react";
import {
  ArrowClockwise,
  Copy,
  DownloadSimple,
  ImageSquare,
  MagicWand,
  PaperPlaneTilt,
  Sparkle,
  Trash,
  UploadSimple,
  X,
} from "@phosphor-icons/react";
import AIGeneratedBadge from "@/components/ui/AIGeneratedBadge";
import type {
  DigitalAsset,
  GeneratedImage,
  ImageGenerateResponse,
  ImageQuality,
  ImageReferenceInput,
  ImageSize,
} from "@/lib/api/images";

export type ImageStudioMode = "text" | "image";
export type ImageStudioRefType = "persona" | "product" | "location";

export interface ImageStudioReferenceImage extends ImageReferenceInput {
  id: string;
  preview: string;
  backendId?: number;
  selected: boolean;
}

export interface ImageStudioHistoryItem extends DigitalAsset {
  promptText: string;
}

interface ImageStudioWorkspaceProps {
  title: ReactNode;
  subtitle?: ReactNode;
  headerAction?: ReactNode;
  loading?: boolean;
  mode: ImageStudioMode;
  prompt: string;
  onPromptChange: (value: string) => void;
  referenceImages: Record<ImageStudioRefType, ImageStudioReferenceImage[]>;
  activeReferenceImages: ImageStudioReferenceImage[];
  unknownPromptImageReferences: string[];
  size: ImageSize;
  onSizeChange: (value: ImageSize) => void;
  quality: ImageQuality;
  onQualityChange: (value: ImageQuality) => void;
  count: number;
  onCountChange: (value: number) => void;
  generating: boolean;
  enhancingPrompt: boolean;
  result: ImageGenerateResponse | null;
  error: string;
  onGenerate: () => void;
  onEnhancePrompt: () => void;
  onResetPrompt: () => void;
  onReferenceUpload: (event: ChangeEvent<HTMLInputElement>, type: ImageStudioRefType) => void | Promise<void>;
  onToggleReference: (type: ImageStudioRefType, id: string) => void;
  onRemoveReference: (type: ImageStudioRefType, id: string) => void | Promise<void>;
  onClearReferenceType: (type: ImageStudioRefType) => void | Promise<void>;
  onInsertReferenceMention: (referenceName: string | undefined) => void;
  onCopyImageUrl: (url?: string) => void | Promise<void>;
  onDownloadImage: (url?: string) => void;
  history?: ImageStudioHistoryItem[];
  historyLoading?: boolean;
  onReusePrompt?: (prompt: string) => void;
  onCopyPrompt?: (prompt: string) => void | Promise<void>;
  onRemoveHistoryItem?: (assetId: number) => void | Promise<void>;
}

const refMeta: Record<ImageStudioRefType, { label: string; shortLabel: string }> = {
  product: { label: "货品参考图", shortLabel: "货品" },
  persona: { label: "人设参考图", shortLabel: "人设" },
  location: { label: "场景参考图", shortLabel: "场景" },
};

const refTypeOrder: ImageStudioRefType[] = ["product", "persona", "location"];

const qualityOptions: Array<{ label: string; value: ImageQuality }> = [
  { label: "自动", value: "auto" },
  { label: "高清", value: "high" },
  { label: "标准", value: "medium" },
  { label: "快速", value: "low" },
];

const ratioOptions: Array<{ label: string; value: ImageSize; width: string; height: string }> = [
  { label: "智能", value: "auto", width: "AUTO", height: "AUTO" },
  { label: "1:1", value: "1024x1024", width: "1024", height: "1024" },
  { label: "3:2", value: "1536x1024", width: "1536", height: "1024" },
  { label: "2:3", value: "1024x1536", width: "1024", height: "1536" },
  { label: "16:9", value: "2048x1152", width: "2048", height: "1152" },
  { label: "9:16", value: "1152x2048", width: "1152", height: "2048" },
];

function imageDisplayUrl(image: GeneratedImage | undefined) {
  if (!image) return "";
  return image.url || image.data_url || (image.b64_json ? `data:${image.mime_type || "image/png"};base64,${image.b64_json}` : "");
}

function dimensionsForSize(size: ImageSize) {
  return ratioOptions.find((item) => item.value === size) || ratioOptions[0];
}

function totalReferenceCount(referenceImages: Record<ImageStudioRefType, ImageStudioReferenceImage[]>) {
  return Object.values(referenceImages).reduce((sum, items) => sum + items.length, 0);
}

export default function ImageStudioWorkspace({
  title,
  subtitle,
  headerAction,
  loading = false,
  mode,
  prompt,
  onPromptChange,
  referenceImages,
  activeReferenceImages,
  unknownPromptImageReferences,
  size,
  onSizeChange,
  quality,
  onQualityChange,
  count,
  onCountChange,
  generating,
  enhancingPrompt,
  result,
  error,
  onGenerate,
  onEnhancePrompt,
  onResetPrompt,
  onReferenceUpload,
  onToggleReference,
  onRemoveReference,
  onClearReferenceType,
  onInsertReferenceMention,
  onCopyImageUrl,
  onDownloadImage,
  history = [],
  historyLoading = false,
  onReusePrompt,
  onCopyPrompt,
  onRemoveHistoryItem,
}: ImageStudioWorkspaceProps) {
  const refCount = totalReferenceCount(referenceImages);
  const dimensions = dimensionsForSize(size);
  const primaryActionLabel = mode === "image" ? "按图生成" : "生成图片";
  const modeLabel = mode === "image" ? "图生图" : "文生图";
  const disabled = generating || !prompt.trim();

  return (
    <section className="image-studio-page">
      <header className="image-studio-header">
        <div className="min-w-0">
          <p className="image-studio-eyebrow">Image Generation</p>
          <div className="image-studio-title">{title}</div>
          {subtitle ? <div className="image-studio-subtitle">{subtitle}</div> : null}
        </div>
        {headerAction ? <div className="image-studio-header-action">{headerAction}</div> : null}
      </header>

      {loading ? (
        <div className="image-studio-loading">
          <div />
          <div />
        </div>
      ) : null}

      <div className="image-studio-shell">
        <main className="image-studio-main">
          <div className="image-studio-model-row">
            <span className="image-studio-model-dot" />
            <strong>AI Image Studio</strong>
            <span>{modeLabel}</span>
          </div>

          <div className="image-studio-canvas">
            {!result && !generating ? (
              <div className="image-studio-empty">
                <Sparkle size={28} weight="duotone" />
                <h1>体验图片生成，让创意摇动</h1>
              </div>
            ) : null}

            {generating ? (
              <div className="image-studio-generating">
                <span className="btn-spinner" />
                <strong>{mode === "image" ? "正在按参考图生成" : "正在生成图片"}</strong>
              </div>
            ) : null}

            {result ? (
              <ImageResultGallery
                result={result}
                onCopyImageUrl={onCopyImageUrl}
                onDownloadImage={onDownloadImage}
              />
            ) : null}
          </div>

          {error ? <div className="image-studio-error">{error}</div> : null}
          {unknownPromptImageReferences.length > 0 ? (
            <div className="image-studio-warning">未找到引用：{unknownPromptImageReferences.join("、")}</div>
          ) : null}

          <div className="image-studio-composer">
            <label className="image-studio-upload-main">
              <ImageSquare size={18} weight="duotone" />
              <span>图片</span>
              <input
                type="file"
                accept="image/*"
                multiple
                onChange={(event) => void onReferenceUpload(event, "product")}
              />
            </label>
            <textarea
              value={prompt}
              onChange={(event) => onPromptChange(event.target.value)}
              placeholder={mode === "image" ? "@图片1 作为参考，生成新的商品展示图" : "输入创意描述"}
              className="image-studio-prompt"
            />
            <button
              type="button"
              onClick={onGenerate}
              disabled={disabled}
              className="image-studio-send"
              aria-label={primaryActionLabel}
              title={primaryActionLabel}
            >
              {generating ? <span className="btn-spinner" /> : <PaperPlaneTilt size={18} weight="fill" />}
            </button>
          </div>

          <ReferenceTray
            referenceImages={referenceImages}
            activeReferenceImages={activeReferenceImages}
            onReferenceUpload={onReferenceUpload}
            onToggleReference={onToggleReference}
            onRemoveReference={onRemoveReference}
            onClearReferenceType={onClearReferenceType}
            onInsertReferenceMention={onInsertReferenceMention}
          />
        </main>

        <aside className="image-studio-params">
          <div className="image-studio-param-title">
            <strong>模型参数</strong>
            <button type="button" onClick={onResetPrompt} title="重置提示词" aria-label="重置提示词">
              <ArrowClockwise size={16} />
            </button>
          </div>

          <ParamBlock label="生成类型">
            <div className="image-studio-mode-pill">
              <span className={mode === "image" ? "is-image" : ""} />
              {modeLabel}
            </div>
          </ParamBlock>

          <ParamBlock label="提示词">
            <button
              type="button"
              onClick={onEnhancePrompt}
              disabled={enhancingPrompt || generating || !prompt.trim()}
              className="image-studio-secondary-action"
            >
              {enhancingPrompt ? <span className="btn-spinner" /> : <MagicWand size={15} weight="duotone" />}
              优化提示词
            </button>
          </ParamBlock>

          <ParamBlock label="清晰度">
            <SegmentedControl
              value={quality}
              options={qualityOptions}
              onChange={(value) => onQualityChange(value as ImageQuality)}
            />
          </ParamBlock>

          <ParamBlock label="图片比例">
            <SegmentedControl
              value={size}
              options={ratioOptions.map((item) => ({ label: item.label, value: item.value }))}
              onChange={(value) => onSizeChange(value as ImageSize)}
              columns={3}
            />
          </ParamBlock>

          <ParamBlock label="图片尺寸">
            <div className="image-studio-size-fields">
              <span>W</span>
              <strong>{dimensions.width}</strong>
              <i />
              <span>H</span>
              <strong>{dimensions.height}</strong>
            </div>
          </ParamBlock>

          <ParamBlock label="最大生成张数">
            <div className="image-studio-slider-row">
              <input
                type="range"
                min={1}
                max={4}
                value={count}
                onChange={(event) => onCountChange(Number(event.target.value))}
              />
              <strong>{count}</strong>
            </div>
          </ParamBlock>

          <ParamBlock label="参考图">
            <div className="image-studio-ref-summary">
              <strong>{activeReferenceImages.length}</strong>
              <span>/ {refCount}</span>
            </div>
          </ParamBlock>
        </aside>
      </div>

      {history.length > 0 || historyLoading ? (
        <HistoryGallery
          history={history}
          historyLoading={historyLoading}
          onReusePrompt={onReusePrompt}
          onCopyPrompt={onCopyPrompt}
          onRemoveHistoryItem={onRemoveHistoryItem}
        />
      ) : null}
    </section>
  );
}

function ParamBlock({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="image-studio-param-block">
      <label>{label}</label>
      {children}
    </div>
  );
}

function SegmentedControl({
  value,
  options,
  onChange,
  columns = 2,
}: {
  value: string;
  options: Array<{ label: string; value: string }>;
  onChange: (value: string) => void;
  columns?: 2 | 3;
}) {
  return (
    <div className={`image-studio-segment image-studio-segment-${columns}`}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={value === option.value ? "active" : ""}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function ReferenceTray({
  referenceImages,
  activeReferenceImages,
  onReferenceUpload,
  onToggleReference,
  onRemoveReference,
  onClearReferenceType,
  onInsertReferenceMention,
}: {
  referenceImages: Record<ImageStudioRefType, ImageStudioReferenceImage[]>;
  activeReferenceImages: ImageStudioReferenceImage[];
  onReferenceUpload: (event: ChangeEvent<HTMLInputElement>, type: ImageStudioRefType) => void | Promise<void>;
  onToggleReference: (type: ImageStudioRefType, id: string) => void;
  onRemoveReference: (type: ImageStudioRefType, id: string) => void | Promise<void>;
  onClearReferenceType: (type: ImageStudioRefType) => void | Promise<void>;
  onInsertReferenceMention: (referenceName: string | undefined) => void;
}) {
  const activeIds = new Set(activeReferenceImages.map((item) => item.id));
  return (
    <div className="image-studio-reference-panel">
      <div className="image-studio-reference-actions">
        {refTypeOrder.map((type) => (
          <label key={type} className="image-studio-upload-chip">
            <UploadSimple size={14} />
            {refMeta[type].shortLabel}
            <input
              type="file"
              accept="image/*"
              multiple
              onChange={(event) => void onReferenceUpload(event, type)}
            />
          </label>
        ))}
      </div>

      <div className="image-studio-reference-groups">
        {refTypeOrder.map((type) => {
          const items = referenceImages[type];
          if (items.length === 0) return null;
          return (
            <div key={type} className="image-studio-reference-group">
              <div className="image-studio-reference-group-head">
                <span>{refMeta[type].label}</span>
                <button type="button" onClick={() => void onClearReferenceType(type)}>
                  清空
                </button>
              </div>
              <div className="image-studio-reference-list">
                {items.map((image) => {
                  const active = activeIds.has(image.id);
                  return (
                    <div key={image.id} className={`image-studio-reference-thumb ${active ? "active" : ""}`}>
                      <button
                        type="button"
                        className="image-studio-reference-image"
                        onClick={() => onToggleReference(type, image.id)}
                        title={image.source_image_filename}
                      >
                        <img src={image.preview} alt={image.source_image_filename} />
                      </button>
                      {image.reference_image_name ? (
                        <button
                          type="button"
                          className="image-studio-reference-name"
                          onClick={() => onInsertReferenceMention(image.reference_image_name)}
                        >
                          {image.reference_image_name}
                        </button>
                      ) : null}
                      <button
                        type="button"
                        className="image-studio-reference-remove"
                        onClick={() => void onRemoveReference(type, image.id)}
                        aria-label="删除参考图"
                        title="删除参考图"
                      >
                        <X size={13} weight="bold" />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ImageResultGallery({
  result,
  onCopyImageUrl,
  onDownloadImage,
}: {
  result: ImageGenerateResponse;
  onCopyImageUrl: (url?: string) => void | Promise<void>;
  onDownloadImage: (url?: string) => void;
}) {
  return (
    <div className="image-studio-result">
      <div className="image-studio-result-meta">
        <AIGeneratedBadge />
        <span>
          {result.provider} / {result.model} / {result.latency_ms}ms
        </span>
      </div>
      <div className="image-studio-result-grid">
        {result.images.map((image, index) => {
          const url = imageDisplayUrl(image);
          return (
            <figure key={index} className="image-studio-result-item">
              {url ? <img src={url} alt={`生成图片 ${index + 1}`} loading="lazy" /> : <figcaption>图片数据不可用</figcaption>}
              <div className="image-studio-result-actions">
                {image.url ? (
                  <button type="button" onClick={() => void onCopyImageUrl(image.url)} title="复制链接">
                    <Copy size={15} />
                  </button>
                ) : null}
                {url ? (
                  <button type="button" onClick={() => onDownloadImage(url)} title="下载">
                    <DownloadSimple size={15} />
                  </button>
                ) : null}
              </div>
            </figure>
          );
        })}
      </div>
    </div>
  );
}

function HistoryGallery({
  history,
  historyLoading,
  onReusePrompt,
  onCopyPrompt,
  onRemoveHistoryItem,
}: {
  history: ImageStudioHistoryItem[];
  historyLoading: boolean;
  onReusePrompt?: (prompt: string) => void;
  onCopyPrompt?: (prompt: string) => void | Promise<void>;
  onRemoveHistoryItem?: (assetId: number) => void | Promise<void>;
}) {
  return (
    <section className="image-studio-history">
      <div className="image-studio-history-head">
        <h2>生成记录</h2>
        {historyLoading ? <span>加载中...</span> : null}
      </div>
      <div className="image-studio-history-grid">
        {history.map((item) => (
          <article key={item.id} className="image-studio-history-item">
            {onRemoveHistoryItem ? (
              <button
                type="button"
                className="image-studio-history-delete"
                onClick={() => void onRemoveHistoryItem(item.id)}
                title="删除"
                aria-label="删除生成记录"
              >
                <Trash size={14} />
              </button>
            ) : null}
            <div className="image-studio-history-preview">
              {item.access_url ? <img src={item.access_url} alt={item.title} loading="lazy" /> : <span>图片不可用</span>}
            </div>
            <p title={item.promptText}>{item.promptText}</p>
            <div className="image-studio-history-actions">
              {onReusePrompt ? (
                <button type="button" onClick={() => onReusePrompt(item.promptText)}>
                  复用
                </button>
              ) : null}
              {onCopyPrompt ? (
                <button type="button" onClick={() => void onCopyPrompt(item.promptText)}>
                  复制
                </button>
              ) : null}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
