"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { listDigitalAssets, type DigitalAsset, type DigitalAssetType } from "@/lib/api/digitalAssets";
import { useAuth } from "@/components/AuthProvider";

const typeOptions: Array<{ label: string; value: DigitalAssetType | "" }> = [
  { label: "全部资产", value: "" },
  { label: "文案", value: "script" },
  { label: "图片", value: "image" },
  { label: "视频", value: "video" },
];

function formatAssetType(type: string) {
  if (type === "script") return "文案";
  if (type === "image") return "图片";
  if (type === "video") return "视频";
  return type;
}

function projectName(asset: DigitalAsset) {
  const name = (asset.project_snapshot as Record<string, unknown>)?.project_name;
  return typeof name === "string" && name ? name : "账户资产";
}

function ownershipLabel(asset: DigitalAsset, displayName: string) {
  if (asset.source_project_id == null) return displayName;
  return `${displayName}--${projectName(asset)}`;
}

function formatTime(value: string) {
  return new Date(value).toLocaleString();
}

function assetPrompt(asset: DigitalAsset) {
  if (asset.asset_type !== "image" && asset.asset_type !== "video") return "";
  const metadataPrompt = asset.asset_metadata?.prompt;
  return (
    asset.content_text ||
    (typeof metadataPrompt === "string" ? metadataPrompt : "") ||
    asset.preview_text ||
    ""
  ).trim();
}

async function copyPrompt(prompt: string) {
  if (!prompt) return;
  try {
    await navigator.clipboard.writeText(prompt);
    alert("已复制提示词");
  } catch {
    alert("复制失败");
  }
}

export default function AssetsPage() {
  const auth = useAuth();
  const [assetType, setAssetType] = useState<DigitalAssetType | "">("");
  const [assets, setAssets] = useState<DigitalAsset[]>([]);
  const [loading, setLoading] = useState(false);

  async function fetchAssets() {
    setLoading(true);
    try {
      const data = await listDigitalAssets({
        asset_type: assetType || null,
        limit: 80,
        offset: 0,
      });
      setAssets(data);
    } catch {
      setAssets([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchAssets();
  }, [assetType]);

  const assetCount = assets.length;
  const imageCount = assets.filter((a) => a.asset_type === "image").length;
  const scriptCount = assets.filter((a) => a.asset_type === "script").length;
  const videoCount = assets.filter((a) => a.asset_type === "video").length;

  return (
    <section className="page-section assets-page">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="section-header"
      >
        <div>
          <p className="eyebrow">Digital Assets</p>
          <h1 className="text-[28px] md:text-[36px] font-bold leading-[1.15] tracking-[-0.02em] text-[#f5f5f5]">
            数字资产
          </h1>
        </div>
        <div className="flex gap-2">
          <select
            className="input-glass appearance-none cursor-pointer"
            value={assetType}
            onChange={(e) => setAssetType(e.target.value as DigitalAssetType | "")}
          >
            {typeOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <button onClick={fetchAssets} disabled={loading} className="btn btn-primary">
            {loading ? "加载中..." : "刷新"}
          </button>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
        className="asset-summary-panel glass card-hover p-5 md:p-6 mb-6"
      >
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <span className="text-[13px] font-[520] text-[#7a8a82] block">资产数</span>
            <strong className="text-[32px] font-[720] text-[#f5f5f5] block mt-2">{assetCount}</strong>
          </div>
          <div>
            <span className="text-[13px] font-[520] text-[#7a8a82] block">文案</span>
            <strong className="text-[32px] font-[720] text-[#f5f5f5] block mt-2">{scriptCount}</strong>
          </div>
          <div>
            <span className="text-[13px] font-[520] text-[#7a8a82] block">图片</span>
            <strong className="text-[32px] font-[720] text-[#f5f5f5] block mt-2">{imageCount}</strong>
          </div>
          <div>
            <span className="text-[13px] font-[520] text-[#7a8a82] block">视频</span>
            <strong className="text-[32px] font-[720] text-[#f5f5f5] block mt-2">{videoCount}</strong>
          </div>
        </div>
      </motion.div>

      {loading ? (
        <div className="glass p-8 rounded-[1rem]">
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-[rgba(255,255,255,0.06)] rounded w-1/3" />
            <div className="h-4 bg-[rgba(255,255,255,0.06)] rounded w-full" />
          </div>
        </div>
      ) : !assets.length ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
          className="empty-state"
        >
          <h2 className="text-[21px] font-[680] text-[#f5f5f5] mb-2">暂无数字资产</h2>
          <p className="text-[#9ca3af] text-sm">文案、图片和视频生成后会在这里汇总。</p>
        </motion.div>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
        >
          {assets.map((asset) => {
            const promptText = assetPrompt(asset);
            return (
            <div key={asset.id} className="asset-card">
              <div className="flex items-center justify-between mb-3">
                <span className={`tag ${asset.asset_type === "image" ? "tag-success" : asset.asset_type === "video" ? "tag-warning" : "tag-info"}`}>
                  {formatAssetType(asset.asset_type)}
                </span>
                <span className="text-[12px] text-[#6b7280]">{formatTime(asset.created_at)}</span>
              </div>

              {asset.asset_type === "image" && asset.access_url ? (
                <img
                  src={asset.access_url}
                  alt={asset.title}
                  className="asset-media w-full h-[200px] object-cover mb-3"
                  loading="lazy"
                />
              ) : asset.asset_type === "video" && asset.access_url ? (
                <video
                  src={asset.access_url}
                  controls
                  className="asset-media w-full h-[200px] object-cover mb-3"
                />
              ) : (
                <div className="asset-text-preview min-h-[100px] p-3 bg-[rgba(255,255,255,0.04)] mb-3 text-[#b0b0b0] text-sm leading-relaxed">
                  {asset.preview_text || asset.content_text || "暂无预览"}
                </div>
              )}

              <h3 className="text-[14px] font-[680] text-[#f5f5f5] mb-1">{asset.title}</h3>
              {promptText ? (
                <div className="mb-2 rounded-[0.5rem] border border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.03)] p-2">
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <span className="text-[11px] font-[600] text-[#9ccaa8]">提示词</span>
                    <button
                      type="button"
                      onClick={() => copyPrompt(promptText)}
                      className="text-[11px] text-[#9ca3af] transition-colors hover:text-[#f5f5f5]"
                    >
                      复制
                    </button>
                  </div>
                  <p className="line-clamp-3 text-[12px] leading-relaxed text-[#b0b0b0]" title={promptText}>
                    {promptText}
                  </p>
                </div>
              ) : null}
              <p className="text-[12px] text-[#9ccaa8]">归属：{ownershipLabel(asset, auth.displayName)}</p>
            </div>
          );
          })}
        </motion.div>
      )}
    </section>
  );
}
