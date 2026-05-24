"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import GlassSelect from "@/components/ui/GlassSelect";
import {
  searchHotVideos,
  type HotVideoItem,
  type HotVideoSearchResponse,
} from "@/lib/api/hotVideos";

const platformOptions = ["抖音", "小红书", "视频号", "快手", "全网"];
const focusOptions = ["同赛道热门视频", "竞品账号拆解", "近期爆点", "可洗稿结构", "获客视频"];
const countOptions = [4, 6, 8, 10, 12];

function formatMetrics(metrics: Record<string, unknown>) {
  const entries = Object.entries(metrics || {}).filter(([, value]) => value !== undefined && value !== null && value !== "");
  if (!entries.length) return "无公开数据";
  return entries.map(([key, value]) => `${key}: ${String(value)}`).join(" / ");
}

function formatHotVideo(item: HotVideoItem) {
  const structure = item.structure || [];
  const riskNotes = item.risk_notes || [];
  const tags = item.tags || [];

  return [
    `标题：${item.title}`,
    `平台：${item.platform || "未知"}`,
    item.creator ? `作者：${item.creator}` : "",
    item.source_url ? `来源：${item.source_url}` : "",
    `公开指标：${formatMetrics(item.metrics)}`,
    `爆点判断：${item.why_trending}`,
    `开头钩子：${item.hook}`,
    structure.length ? `内容结构：\n${structure.map((step, index) => `${index + 1}. ${step}`).join("\n")}` : "",
    `二创角度：${item.remake_angle}`,
    `洗稿简报：${item.rewrite_brief}`,
    riskNotes.length ? `风险提醒：${riskNotes.join("；")}` : "",
    tags.length ? `标签：${tags.join("、")}` : "",
  ].filter(Boolean).join("\n");
}

export default function HotVideosPage() {
  const [platform, setPlatform] = useState("抖音");
  const [keyword, setKeyword] = useState("");
  const [searchFocus, setSearchFocus] = useState("同赛道热门视频");
  const [count, setCount] = useState(8);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<HotVideoSearchResponse | null>(null);

  async function handleSearch() {
    const cleanKeyword = keyword.trim();
    if (!cleanKeyword) {
      alert("请输入搜索关键词");
      return;
    }

    setSearching(true);
    setError("");
    setResult(null);
    try {
      const response = await searchHotVideos({
        platform,
        keyword: cleanKeyword,
        search_focus: searchFocus,
        count,
        web_search_context_size: "medium",
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "爆款视频拆解失败");
    } finally {
      setSearching(false);
    }
  }

  async function copyText(text: string, successMessage: string) {
    try {
      await navigator.clipboard.writeText(text);
      alert(successMessage);
    } catch {
      alert("复制失败，请手动复制");
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
          <p className="eyebrow">Hot Video Research</p>
          <h1 className="section-title">AI爆款拆解</h1>
          <p className="section-subtitle">
            输入赛道、产品或账号关键词，联网搜索公开视频素材，输出爆点判断、结构拆解和洗稿简报。
          </p>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
        className="topic-workspace-plate"
      >
        <div className="topic-control-panel">
          <div className="grid grid-cols-1 md:grid-cols-[1.2fr_1fr_1fr_0.7fr_auto] gap-4 items-end">
            <label className="flex flex-col gap-1.5">
              <span className="text-[12px] text-[#9ca3af]">关键词</span>
              <input
                className="metal-input min-h-[46px]"
                value={keyword}
                onChange={(event) => setKeyword(event.target.value)}
                placeholder="例如：小红书珠宝种草、同城获客、健身私教转化"
              />
            </label>
            <GlassSelect label="平台" value={platform} onChange={setPlatform} options={platformOptions} />
            <GlassSelect label="研究重点" value={searchFocus} onChange={setSearchFocus} options={focusOptions} />
            <GlassSelect
              label="数量"
              value={count}
              onChange={(value) => setCount(Number(value))}
              options={countOptions}
              renderLabel={(value) => `${value} 条`}
            />
            <button
              onClick={handleSearch}
              disabled={searching}
              className="metal-btn metal-btn-primary min-h-[46px] px-6"
            >
              {searching ? (
                <span className="inline-flex items-center gap-2">
                  <span className="btn-spinner" />
                  搜索中
                </span>
              ) : (
                "搜索拆解"
              )}
            </button>
          </div>
        </div>

        {error ? (
          <div className="mt-5 border-l-4 border-l-red-500 bg-[rgba(120,30,30,0.2)] p-4 text-sm text-red-200">
            {error}
          </div>
        ) : null}

        {searching ? (
          <div className="topic-generate-state mt-5">
            <div className="flex items-center gap-3">
              <span className="btn-spinner" />
              <span className="text-[13px] text-[#f5f5f5]">正在联网搜索并拆解热门视频...</span>
            </div>
          </div>
        ) : null}

        {result ? (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            className="topic-results-plate mt-5"
          >
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div className="text-[13px] text-[#9ca3af]">
                Provider：{result.provider} / Model：{result.model} / {result.latency_ms}ms
              </div>
              {result.sources.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {result.sources.slice(0, 4).map((source) => (
                    <a
                      key={source.url}
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="metal-tag max-w-[220px] truncate"
                    >
                      {source.title || source.url}
                    </a>
                  ))}
                </div>
              ) : null}
            </div>

            {result.items.length ? (
              <div className="topic-card-grid">
                {result.items.map((item, index) => {
                  const structure = item.structure || [];
                  const riskNotes = item.risk_notes || [];
                  const tags = item.tags || [];

                  return (
                    <article key={`${item.source_url || item.title}-${index}`} className="topic-card ai-context-card">
                      <div className="mb-3 flex items-start justify-between gap-3">
                        <div className="flex flex-wrap gap-1.5">
                          <span className="metal-tag">{item.platform || platform}</span>
                          {item.creator ? <span className="metal-tag">{item.creator}</span> : null}
                          {tags.slice(0, 3).map((tag) => (
                            <span key={tag} className="metal-tag">{tag}</span>
                          ))}
                        </div>
                        <span className="text-[12px] text-[#7a8a82]">{item.publish_time || "公开来源"}</span>
                      </div>

                      <h2 className="mb-3 text-[16px] font-[700] leading-snug text-[#f5f5f5]">
                        {item.title || item.source_title || "未命名素材"}
                      </h2>

                      <div className="space-y-3 text-sm leading-relaxed text-[#b0b0b0]">
                        <p>
                          <span className="text-[#9ca3af]">公开指标：</span>
                          {formatMetrics(item.metrics)}
                        </p>
                        <p>
                          <span className="text-[#9ca3af]">爆点判断：</span>
                          {item.why_trending || "暂无"}
                        </p>
                        <p>
                          <span className="text-[#9ca3af]">开头钩子：</span>
                          {item.hook || "暂无"}
                        </p>
                        {structure.length ? (
                          <div>
                            <span className="text-[#9ca3af]">结构：</span>
                            <ol className="mt-1 list-decimal space-y-1 pl-5">
                              {structure.map((step, stepIndex) => (
                                <li key={`${step}-${stepIndex}`}>{step}</li>
                              ))}
                            </ol>
                          </div>
                        ) : null}
                        <p>
                          <span className="text-[#9ca3af]">二创角度：</span>
                          {item.remake_angle || "暂无"}
                        </p>
                        <p>
                          <span className="text-[#9ca3af]">洗稿简报：</span>
                          {item.rewrite_brief || "暂无"}
                        </p>
                        {riskNotes.length ? (
                          <p className="text-[#b8985a]">
                            风险提醒：{riskNotes.join("；")}
                          </p>
                        ) : null}
                      </div>

                      <div className="mt-4 flex flex-wrap gap-2 border-t border-[rgba(255,255,255,0.06)] pt-3">
                        {item.source_url ? (
                          <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="metal-btn text-xs">
                            打开来源
                          </a>
                        ) : null}
                        <button onClick={() => copyText(formatHotVideo(item), "已复制拆解内容")} className="metal-btn text-xs">
                          复制拆解
                        </button>
                        <button
                          onClick={() => copyText(item.rewrite_brief || formatHotVideo(item), "已复制洗稿简报")}
                          className="metal-btn metal-btn-primary text-xs"
                        >
                          复制洗稿简报
                        </button>
                      </div>
                    </article>
                  );
                })}
              </div>
            ) : (
              <div className="topic-empty-state">
                <h2 className="mb-2 text-[21px] font-[680] text-[#f5f5f5]">没有拿到可用结果</h2>
                <p className="text-sm text-[#9ca3af]">换一个更具体的关键词，或把平台改成全网再试。</p>
              </div>
            )}
          </motion.div>
        ) : null}
      </motion.div>
    </section>
  );
}
