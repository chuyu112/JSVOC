"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  analyzeHotCopyMaterial,
  createManualHotCopyMaterial,
  listHotCopyMaterials,
  rewriteHotCopyMaterial,
  searchRedianbaoHotCopy,
  type HotCopyMaterial,
} from "@/lib/api/hotCopy";

function getStringList(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map((item) => String(item || "").trim()).filter(Boolean);
  }
  if (typeof value === "string") {
    return value.split(/\n|,|，|、/).map((item) => item.trim()).filter(Boolean);
  }
  return [];
}

function getString(value: unknown): string {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "";
}

export default function HotCopyPage() {
  const [materials, setMaterials] = useState<HotCopyMaterial[]>([]);
  const [selectedMaterial, setSelectedMaterial] = useState<HotCopyMaterial | null>(null);
  const [title, setTitle] = useState("");
  const [originalScript, setOriginalScript] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [accountName, setAccountName] = useState("");
  const [accountHomeUrl, setAccountHomeUrl] = useState("");
  const [coverUrl, setCoverUrl] = useState("");
  const [projectId, setProjectId] = useState("");
  const [rewriteMode, setRewriteMode] = useState<"light" | "medium" | "strong">("medium");
  const [duration, setDuration] = useState<"30s" | "60s" | "90s">("60s");
  const [conversionGoal, setConversionGoal] = useState("私信获客");
  const [product, setProduct] = useState("");
  const [targetCustomer, setTargetCustomer] = useState("");
  const [accountPersona, setAccountPersona] = useState("");
  const [analysis, setAnalysis] = useState<Record<string, unknown> | null>(null);
  const [rewriteOutput, setRewriteOutput] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState<"" | "save" | "analyze" | "rewrite" | "redianbao">("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const analysisPoints = useMemo(() => {
    if (!analysis) return [];
    return [
      { label: "开头钩子", value: getString(analysis.hook) },
      { label: "爆点判断", value: getString(analysis.why_trending) },
      { label: "内容结构", value: getStringList(analysis.structure).join(" / ") },
      { label: "转化设计", value: getString(analysis.conversion_design) },
      { label: "可仿写角度", value: getString(analysis.rewrite_angle) },
    ].filter((item) => item.value);
  }, [analysis]);

  const rewriteScript = getString(rewriteOutput?.script);
  const videoHref = rewriteScript ? `/videos?prompt=${encodeURIComponent(rewriteScript)}` : "/videos";

  useEffect(() => {
    refreshMaterials();
    // The initial material load should only run once when the workbench mounts.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function refreshMaterials() {
    setError("");
    try {
      const data = await listHotCopyMaterials();
      setMaterials(data);
      if (!selectedMaterial && data.length) {
        selectMaterial(data[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "爆款素材加载失败");
    }
  }

  async function saveMaterial() {
    const cleanTitle = title.trim();
    const cleanScript = originalScript.trim();
    if (!cleanTitle || !cleanScript) {
      setError("请填写标题和原始口播文案后再保存素材。");
      return;
    }

    setLoading("save");
    setError("");
    setNotice("");
    try {
      const material = await createManualHotCopyMaterial({
        project_id: projectId.trim() ? Number(projectId) : null,
        platform: "douyin",
        source_url: sourceUrl.trim() || null,
        account_name: accountName.trim() || null,
        account_home_url: accountHomeUrl.trim() || null,
        cover_url: coverUrl.trim() || null,
        title: cleanTitle,
        original_script: cleanScript,
        metrics_json: {},
      });
      setMaterials((prev) => [material, ...prev.filter((item) => item.id !== material.id)]);
      selectMaterial(material);
      setTitle("");
      setOriginalScript("");
      setSourceUrl("");
      setAccountName("");
      setAccountHomeUrl("");
      setCoverUrl("");
      setNotice("素材已保存，可以继续拆解爆点。");
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存素材失败");
    } finally {
      setLoading("");
    }
  }

  async function analyzeSelected() {
    if (!selectedMaterial) {
      setError("请先选择一个爆款素材。");
      return;
    }

    setLoading("analyze");
    setError("");
    setNotice("");
    try {
      const response = await analyzeHotCopyMaterial(selectedMaterial.id);
      setAnalysis(response.analysis);
      setSelectedMaterial(response.material);
      setMaterials((prev) => prev.map((item) => (item.id === response.material.id ? response.material : item)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "拆解爆点失败");
    } finally {
      setLoading("");
    }
  }

  async function rewriteSelected() {
    if (!selectedMaterial) {
      setError("请先选择一个爆款素材。");
      return;
    }

    setLoading("rewrite");
    setError("");
    setNotice("");
    try {
      const response = await rewriteHotCopyMaterial(selectedMaterial.id, {
        project_id: projectId.trim() ? Number(projectId) : null,
        rewrite_mode: rewriteMode,
        duration,
        conversion_goal: conversionGoal.trim() || "私信获客",
        product: product.trim() || null,
        target_customer: targetCustomer.trim() || null,
        account_persona: accountPersona.trim() || null,
      });
      setRewriteOutput(response.output);
    } catch (err) {
      setError(err instanceof Error ? err.message : "仿写文案失败");
    } finally {
      setLoading("");
    }
  }

  async function openRedianbaoReserved() {
    setLoading("redianbao");
    setError("");
    setNotice("");
    try {
      await searchRedianbaoHotCopy("抖音口播爆款", 30);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "热点宝数据源暂未接入，请先使用手动输入。");
    } finally {
      setLoading("");
    }
  }

  function selectMaterial(material: HotCopyMaterial) {
    setSelectedMaterial(material);
    setAnalysis(material.analysis_json);
    setRewriteOutput(null);
    setNotice("");
    setError("");
  }

  return (
    <section className="page-section hot-copy-page">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="section-header"
      >
        <div>
          <p className="eyebrow">Hot Copy Workbench</p>
          <h1 className="section-title">爆款仿写工作台</h1>
          <p className="section-subtitle">先手动输入抖音爆款素材，拆解爆点后生成可直接拍摄的仿写文案。</p>
        </div>
        <div className="section-header-actions">
          <button className="metal-btn" type="button" onClick={openRedianbaoReserved} disabled={loading === "redianbao"}>
            {loading === "redianbao" ? (
              <span className="inline-flex items-center gap-2">
                <span className="btn-spinner" />
                热点宝搜索中
              </span>
            ) : (
              "热点宝每日热门搜索"
            )}
          </button>
        </div>
      </motion.div>

      {error ? <div className="mb-4 border-l-4 border-l-red-500 bg-[rgba(120,30,30,0.2)] p-4 text-sm text-red-200">{error}</div> : null}
      {notice ? <div className="mb-4 border-l-4 border-l-[#b8a060] bg-[rgba(184,160,96,0.12)] p-4 text-sm text-[#d8c58a]">{notice}</div> : null}

      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
        className="topic-workspace-plate"
      >
        <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1fr_1fr_1fr]">
          <div className="topic-control-panel">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-[18px] font-[720] text-[#f5f5f5]">爆款素材</h2>
                <p className="text-sm text-[#9ca3af]">手动输入抖音口播、标题和来源信息。</p>
              </div>
              <span className="metal-tag">抖音</span>
            </div>

            <div className="grid gap-3">
              <input className="metal-input" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="爆款标题" />
              <textarea className="metal-input" value={originalScript} onChange={(event) => setOriginalScript(event.target.value)} placeholder="粘贴原始口播文案" />
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <input className="metal-input" value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} placeholder="视频链接" />
                <input className="metal-input" value={accountName} onChange={(event) => setAccountName(event.target.value)} placeholder="账号名称" />
                <input className="metal-input" value={accountHomeUrl} onChange={(event) => setAccountHomeUrl(event.target.value)} placeholder="账号主页链接" />
                <input className="metal-input" value={coverUrl} onChange={(event) => setCoverUrl(event.target.value)} placeholder="封面链接" />
                <input className="metal-input" value={projectId} onChange={(event) => setProjectId(event.target.value)} placeholder="项目 ID（可选）" />
              </div>
              <button className="metal-btn metal-btn-primary" type="button" onClick={saveMaterial} disabled={loading === "save"}>
                {loading === "save" ? (
                  <span className="inline-flex items-center gap-2">
                    <span className="btn-spinner" />
                    保存中
                  </span>
                ) : (
                  "保存素材"
                )}
              </button>
            </div>

            <div className="mt-5 border-t border-[rgba(255,255,255,0.06)] pt-4">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-[14px] font-[680] text-[#d0ddd6]">已保存素材</h3>
                <button className="metal-btn text-xs" type="button" onClick={refreshMaterials}>
                  刷新
                </button>
              </div>
              {materials.length ? (
                <div className="grid gap-2">
                  {materials.map((material) => (
                    <button
                      key={material.id}
                      className={`metal-btn justify-start text-left ${selectedMaterial?.id === material.id ? "metal-btn-primary" : ""}`}
                      type="button"
                      onClick={() => selectMaterial(material)}
                    >
                      <span className="block min-w-0 truncate">{material.title}</span>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="topic-empty-state">
                  <h3 className="mb-2 text-[18px] font-[680] text-[#f5f5f5]">暂无素材</h3>
                  <p className="text-sm text-[#9ca3af]">先保存一条手动输入素材，再进入拆解和仿写。</p>
                </div>
              )}
            </div>
          </div>

          <div className="topic-control-panel">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-[18px] font-[720] text-[#f5f5f5]">爆点拆解</h2>
                <p className="text-sm text-[#9ca3af]">提取钩子、结构、转化和二创角度。</p>
              </div>
              <button className="metal-btn metal-btn-primary" type="button" onClick={analyzeSelected} disabled={loading === "analyze" || !selectedMaterial}>
                {loading === "analyze" ? (
                  <span className="inline-flex items-center gap-2">
                    <span className="btn-spinner" />
                    拆解中
                  </span>
                ) : (
                  "拆解爆点"
                )}
              </button>
            </div>

            {selectedMaterial ? (
              <article className="metal-block mb-4 p-4">
                <div className="mb-2 flex flex-wrap gap-2">
                  <span className="metal-tag">手动输入</span>
                  <span className="metal-tag">{selectedMaterial.platform || "抖音"}</span>
                  {selectedMaterial.account_name ? <span className="metal-tag">{selectedMaterial.account_name}</span> : null}
                </div>
                <h3 className="mb-2 text-[16px] font-[680] text-[#f5f5f5]">{selectedMaterial.title}</h3>
                <p className="max-h-[240px] overflow-auto whitespace-pre-wrap text-sm leading-relaxed text-[#b0b0b0]">
                  {selectedMaterial.original_script}
                </p>
              </article>
            ) : (
              <div className="topic-empty-state">
                <h3 className="mb-2 text-[18px] font-[680] text-[#f5f5f5]">未选择素材</h3>
                <p className="text-sm text-[#9ca3af]">从左侧列表选择素材后开始拆解。</p>
              </div>
            )}

            {analysisPoints.length ? (
              <div className="grid gap-3">
                {analysisPoints.map((item) => (
                  <article key={item.label} className="metal-block p-4">
                    <span className="metal-tag mb-2">{item.label}</span>
                    <p className="text-sm leading-relaxed text-[#d0ddd6]">{item.value}</p>
                  </article>
                ))}
              </div>
            ) : null}
          </div>

          <div className="topic-control-panel">
            <div className="mb-4">
              <h2 className="text-[18px] font-[720] text-[#f5f5f5]">仿写文案</h2>
              <p className="text-sm text-[#9ca3af]">输入产品、人群和人设，生成新账号可用脚本。</p>
            </div>

            <div className="grid gap-3">
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <select className="metal-input" value={rewriteMode} onChange={(event) => setRewriteMode(event.target.value as "light" | "medium" | "strong")}>
                  <option value="light">轻度仿写</option>
                  <option value="medium">中度仿写</option>
                  <option value="strong">强转化仿写</option>
                </select>
                <select className="metal-input" value={duration} onChange={(event) => setDuration(event.target.value as "30s" | "60s" | "90s")}>
                  <option value="30s">30s</option>
                  <option value="60s">60s</option>
                  <option value="90s">90s</option>
                </select>
              </div>
              <input className="metal-input" value={conversionGoal} onChange={(event) => setConversionGoal(event.target.value)} placeholder="转化目标" />
              <input className="metal-input" value={product} onChange={(event) => setProduct(event.target.value)} placeholder="产品/服务" />
              <input className="metal-input" value={targetCustomer} onChange={(event) => setTargetCustomer(event.target.value)} placeholder="目标客户" />
              <input className="metal-input" value={accountPersona} onChange={(event) => setAccountPersona(event.target.value)} placeholder="账号人设" />
              <button className="metal-btn metal-btn-primary" type="button" onClick={rewriteSelected} disabled={loading === "rewrite" || !selectedMaterial}>
                {loading === "rewrite" ? (
                  <span className="inline-flex items-center gap-2">
                    <span className="btn-spinner" />
                    仿写中
                  </span>
                ) : (
                  "仿写文案"
                )}
              </button>
            </div>

            {rewriteOutput ? (
              <article className="metal-block mt-5 p-4">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <span className="metal-tag">{getString(rewriteOutput.title) || "仿写结果"}</span>
                  <Link className="metal-btn metal-btn-primary text-xs" href={videoHref}>
                    去生成视频
                  </Link>
                </div>
                {getString(rewriteOutput.hook) ? (
                  <p className="mb-3 text-sm leading-relaxed text-[#d8c58a]">{getString(rewriteOutput.hook)}</p>
                ) : null}
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-[#d0ddd6]">
                  {rewriteScript || JSON.stringify(rewriteOutput, null, 2)}
                </p>
              </article>
            ) : (
              <div className="topic-empty-state mt-5">
                <h3 className="mb-2 text-[18px] font-[680] text-[#f5f5f5]">等待仿写</h3>
                <p className="text-sm text-[#9ca3af]">拆解后补充业务信息，生成可跳转视频工具的文案。</p>
              </div>
            )}
          </div>
        </div>
      </motion.div>
    </section>
  );
}
