"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  analyzeHotCopyMaterial,
  createAutoHotCopyMaterial,
  createManualHotCopyMaterial,
  generateScenesFromRewrite,
  generateVideoFromRewrite,
  listHotCopyMaterials,
  rewriteHotCopyMaterial,
  searchRedianbaoHotCopy,
  uploadHotCopyMaterial,
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
  const [loading, setLoading] = useState<"" | "save" | "analyze" | "rewrite" | "redianbao" | "parseLink" | "uploadVideo" | "generateVideo" | "generateScenes">("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [linkUrl, setLinkUrl] = useState("");
  const [inputMode, setInputMode] = useState<"link" | "upload" | "manual">("link");

  const structureType = getString(analysis?.structure_type);
  const structureTypeLabel = useMemo(() => {
    switch (structureType) {
      case "talking_head": return "口播类";
      case "drama": return "剧情类";
      case "mixed": return "混剪类";
      default: return "";
    }
  }, [structureType]);

  const structureTypeHint = useMemo(() => {
    switch (structureType) {
      case "talking_head": return "可直接数字人复刻";
      case "drama": return "需自行拍摄演绎";
      case "mixed": return "需混剪素材拼接";
      default: return "";
    }
  }, [structureType]);

  const analysisPoints = useMemo(() => {
    if (!analysis) return [];
    return [
      { label: "开头钩子", value: getString(analysis.hook) },
      { label: "内容结构", value: getStringList(analysis.structure).join(" / ") },
      { label: "爆点情绪", value: getStringList(analysis.emotion_triggers).join(" / ") || getString(analysis.why_trending) },
      { label: "信任支撑", value: getStringList(analysis.trust_builders).join(" / ") },
      { label: "转化设计", value: getStringList(analysis.conversion_points).join(" / ") || getString(analysis.conversion_design) },
      { label: "风险提醒", value: getStringList(analysis.risk_notes).join(" / ") },
      { label: "可仿写简报", value: getString(analysis.rewrite_brief) || getString(analysis.rewrite_angle) || getString(analysis.remake_angle) },
    ].filter((item) => item.value);
  }, [analysis]);

  const sceneBreakdown = useMemo(() => {
    const raw = rewriteOutput?.scene_breakdown;
    if (!Array.isArray(raw)) return [];
    return raw.filter((s) => s && typeof s === "object");
  }, [rewriteOutput]);

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
      setRewriteOutput({ ...response.output, rewrite_id: response.rewrite.id });
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
    } catch {
      setNotice("热点宝数据源暂未接入，请先使用手动输入。");
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

  async function parseLink() {
    const cleanUrl = linkUrl.trim();
    if (!cleanUrl) {
      setError("请粘贴视频链接后再解析。");
      return;
    }
    setLoading("parseLink");
    setError("");
    setNotice("");
    try {
      const material = await createAutoHotCopyMaterial({
        project_id: projectId.trim() ? Number(projectId) : null,
        source_url: cleanUrl,
      });
      setMaterials((prev) => [material, ...prev.filter((item) => item.id !== material.id)]);
      selectMaterial(material);
      setLinkUrl("");
      setNotice("链接解析完成，已保存为素材。");
    } catch (err) {
      setError(err instanceof Error ? err.message : "链接解析失败");
    } finally {
      setLoading("");
    }
  }

  async function handleFileUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setLoading("uploadVideo");
    setError("");
    setNotice("");
    try {
      const material = await uploadHotCopyMaterial(
        file,
        projectId.trim() ? Number(projectId) : null,
        "douyin",
      );
      setMaterials((prev) => [material, ...prev.filter((item) => item.id !== material.id)]);
      selectMaterial(material);
      setNotice("视频上传并提取完成，已保存为素材。");
    } catch (err) {
      setError(err instanceof Error ? err.message : "视频上传提取失败");
    } finally {
      setLoading("");
    }
    event.target.value = "";
  }

  async function handleGenerateVideo() {
    const rewriteId = rewriteOutput ? (rewriteOutput as Record<string, unknown>).rewrite_id : null;
    if (!rewriteId || typeof rewriteId !== "number") {
      setError("无法获取仿写记录 ID，请重新仿写后再试。");
      return;
    }
    setLoading("generateVideo");
    setError("");
    setNotice("");
    try {
      const result = await generateVideoFromRewrite(rewriteId);
      setNotice(`视频生成任务已提交（任务 ID: ${result.task_id}），请前往"生成历史"查看进度。`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "视频生成任务提交失败");
    } finally {
      setLoading("");
    }
  }

  async function handleGenerateScenes() {
    const rewriteId = rewriteOutput ? (rewriteOutput as Record<string, unknown>).rewrite_id : null;
    if (!rewriteId || typeof rewriteId !== "number") {
      setError("无法获取仿写记录 ID，请重新仿写后再试。");
      return;
    }
    setLoading("generateScenes");
    setError("");
    setNotice("");
    try {
      const result = await generateScenesFromRewrite(rewriteId);
      setNotice(`已提交 ${result.total} 个分镜素材生成任务，请前往"生成历史"查看进度。`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "分镜素材生成任务提交失败");
    } finally {
      setLoading("");
    }
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
          <p className="section-subtitle">粘贴链接或上传视频自动提取文案，拆解爆点后结合精准人设生成仿写脚本。</p>
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
                <p className="text-sm text-[#9ca3af]">粘贴链接、上传视频或手动输入文案。</p>
              </div>
              <span className="metal-tag">抖音</span>
            </div>

            <div className="mb-3 grid grid-cols-3 gap-2">
              <button
                className={`metal-btn text-xs ${inputMode === "link" ? "metal-btn-primary" : ""}`}
                type="button"
                onClick={() => setInputMode("link")}
              >
                粘贴链接
              </button>
              <button
                className={`metal-btn text-xs ${inputMode === "upload" ? "metal-btn-primary" : ""}`}
                type="button"
                onClick={() => setInputMode("upload")}
              >
                上传视频
              </button>
              <button
                className={`metal-btn text-xs ${inputMode === "manual" ? "metal-btn-primary" : ""}`}
                type="button"
                onClick={() => setInputMode("manual")}
              >
                手动输入
              </button>
            </div>

            {inputMode === "link" ? (
              <div className="grid gap-3">
                <input
                  className="metal-input"
                  value={linkUrl}
                  onChange={(event) => setLinkUrl(event.target.value)}
                  placeholder="粘贴抖音/小红书/视频号链接"
                />
                <input className="metal-input" value={projectId} onChange={(event) => setProjectId(event.target.value)} placeholder="项目 ID（可选）" />
                <button className="metal-btn metal-btn-primary" type="button" onClick={parseLink} disabled={loading === "parseLink"}>
                  {loading === "parseLink" ? (
                    <span className="inline-flex items-center gap-2">
                      <span className="btn-spinner" />
                      解析中
                    </span>
                  ) : (
                    "解析并保存"
                  )}
                </button>
              </div>
            ) : null}

            {inputMode === "upload" ? (
              <div className="grid gap-3">
                <label className="metal-input flex cursor-pointer items-center justify-center gap-2 py-3">
                  <input
                    type="file"
                    accept="video/*"
                    className="sr-only"
                    onChange={handleFileUpload}
                    disabled={loading === "uploadVideo"}
                  />
                  {loading === "uploadVideo" ? (
                    <span className="inline-flex items-center gap-2">
                      <span className="btn-spinner" />
                      上传提取中
                    </span>
                  ) : (
                    "选择视频文件上传"
                  )}
                </label>
                <input className="metal-input" value={projectId} onChange={(event) => setProjectId(event.target.value)} placeholder="项目 ID（可选）" />
              </div>
            ) : null}

            {inputMode === "manual" ? (
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
            ) : null}

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
                      {material.source_type === "auto" ? (
                        <span className="ml-2 shrink-0 text-[10px] text-[#9ca3af]">自动</span>
                      ) : null}
                    </button>
                  ))}
                </div>
              ) : (
                <div className="topic-empty-state">
                  <h3 className="mb-2 text-[18px] font-[680] text-[#f5f5f5]">暂无素材</h3>
                  <p className="text-sm text-[#9ca3af]">先保存一条素材，再进入拆解和仿写。</p>
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
                  <span className="metal-tag">{selectedMaterial.source_type === "auto" ? "自动提取" : "手动输入"}</span>
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

            {structureTypeLabel ? (
              <div className="mb-3 flex items-center gap-2">
                <span className={`metal-tag ${structureType === "drama" ? "bg-[rgba(180,80,60,0.3)] text-[#e8a090]" : "bg-[rgba(60,140,100,0.3)] text-[#90d8b0]"}`}>
                  {structureTypeLabel}
                </span>
                <span className="text-xs text-[#9ca3af]">{structureTypeHint}</span>
              </div>
            ) : null}

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
                  <div className="flex gap-2">
                    {structureType === "talking_head" || structureType === "mixed" ? (
                      <button
                        className="metal-btn metal-btn-primary text-xs"
                        type="button"
                        onClick={handleGenerateVideo}
                        disabled={loading === "generateVideo"}
                      >
                        {loading === "generateVideo" ? (
                          <span className="inline-flex items-center gap-2">
                            <span className="btn-spinner" />
                            提交中
                          </span>
                        ) : (
                          "一键生成视频"
                        )}
                      </button>
                    ) : null}
                    {structureType === "drama" ? (
                      <button
                        className="metal-btn metal-btn-primary text-xs"
                        type="button"
                        onClick={handleGenerateScenes}
                        disabled={loading === "generateScenes"}
                      >
                        {loading === "generateScenes" ? (
                          <span className="inline-flex items-center gap-2">
                            <span className="btn-spinner" />
                            提交中
                          </span>
                        ) : (
                          "生成分镜参考图"
                        )}
                      </button>
                    ) : null}
                    <Link className="metal-btn text-xs" href={videoHref}>
                      去视频工具
                    </Link>
                  </div>
                </div>
                {getString(rewriteOutput.hook) ? (
                  <p className="mb-3 text-sm leading-relaxed text-[#d8c58a]">{getString(rewriteOutput.hook)}</p>
                ) : null}
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-[#d0ddd6]">
                  {rewriteScript || JSON.stringify(rewriteOutput, null, 2)}
                </p>

                {structureType === "drama" && sceneBreakdown.length ? (
                  <div className="mt-4 border-t border-[rgba(255,255,255,0.06)] pt-4">
                    <h4 className="mb-3 text-[14px] font-[680] text-[#f5f5f5]">场景分镜表</h4>
                    <div className="grid gap-3">
                      {sceneBreakdown.map((scene: Record<string, unknown>, idx: number) => (
                        <div key={idx} className="rounded-md bg-[rgba(255,255,255,0.04)] p-3">
                          <div className="mb-1 flex items-center gap-2">
                            <span className="text-xs font-bold text-[#b8a060]">场景 {getString(scene.scene_no) || idx + 1}</span>
                            <span className="text-xs text-[#9ca3af]">{getString(scene.shot_type) || ""}</span>
                          </div>
                          <p className="mb-1 text-sm text-[#d0ddd6]">
                            <span className="text-[#9ca3af]">地点：</span>{getString(scene.setting) || "未指定"}
                          </p>
                          <p className="mb-1 text-sm text-[#d0ddd6]">
                            <span className="text-[#9ca3af]">人物：</span>{getString(scene.characters) || ""}
                          </p>
                          <p className="mb-1 text-sm text-[#d0ddd6]">
                            <span className="text-[#9ca3af]">动作：</span>{getString(scene.action) || ""}
                          </p>
                          <p className="mb-1 text-sm italic text-[#e8c898]">
                            {getString(scene.dialogue) || ""}
                          </p>
                          {getString(scene.image_prompt) ? (
                            <p className="mt-2 text-xs text-[#7a9a8a]">
                              生图提示：{getString(scene.image_prompt)}
                            </p>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
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
