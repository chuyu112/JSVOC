"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter, useParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  generateTopics,
  generateTopicsBatch,
  listProjectTopics,
  updateTopicFavorite,
  deleteTopic,
  type Topic,
  type TopicContentFormat,
} from "@/lib/api/topics";
import { getProject, type Project } from "@/lib/api/projects";
import TypingIndicator from "@/components/ui/TypingIndicator";
import AIGeneratedBadge from "@/components/ui/AIGeneratedBadge";
import ProjectModuleTitle from "@/components/ProjectModuleTitle";
import GlassSelect from "@/components/ui/GlassSelect";

const platformOptions = ["抖音", "视频号", "快手", "小红书"];
const goalOptions = ["获客", "涨粉", "信任建立", "成交转化"];
const contentFormatOptions: Array<{ label: string; value: TopicContentFormat }> = [
  { label: "视频：口播", value: "video_spoken" },
  { label: "视频：脚本", value: "video_script" },
  { label: "图片", value: "image" },
];
const countOptions = [10, 20, 30];

function platformTagClass(platformName: string) {
  if (platformName.includes("抖音")) return "platform-douyin";
  if (platformName.includes("快手")) return "platform-kuaishou";
  if (platformName.includes("小红书")) return "platform-xiaohongshu";
  if (platformName.includes("视频号")) return "platform-video";
  return "";
}

function topicContentFormatLabel(topic: Topic, fallback: string) {
  const format = topic.topic_data?.content_format || fallback;
  if (format === "image") return "图片";
  if (format === "video_spoken") return "视频：口播";
  if (format === "video_script") return "视频：脚本";
  return "视频";
}

function ScoreBar({ label, score }: { label: string; score: number }) {
  const opacity = 0.15 + (score / 5) * 0.6;
  return (
    <div className="flex items-center gap-1">
      <span className="text-[10px] text-[#9ca3af] w-5 shrink-0">{label}</span>
      <div className="flex gap-[2px]">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="w-1 h-2.5 rounded-[1px]"
            style={{
              background: i < score ? "rgba(208,221,214,0.7)" : "rgba(255,255,255,0.08)",
            }}
          />
        ))}
      </div>
    </div>
  );
}

function RubricMini({ rubric, hkr }: { rubric?: { er?: number; sr?: number; hp?: number; ql?: number; na?: number; ab?: number; sat?: number }; hkr?: { h?: number; k?: number; r?: number } }) {
  if (!rubric && !hkr) return null;
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-2 pt-2 border-t border-[rgba(255,255,255,0.04)]">
      {rubric && (
        <>
          <ScoreBar label="ER" score={rubric.er ?? 0} />
          <ScoreBar label="SR" score={rubric.sr ?? 0} />
          <ScoreBar label="HP" score={rubric.hp ?? 0} />
          <ScoreBar label="QL" score={rubric.ql ?? 0} />
          <ScoreBar label="NA" score={rubric.na ?? 0} />
          <ScoreBar label="AB" score={rubric.ab ?? 0} />
          <ScoreBar label="SAT" score={rubric.sat ?? 0} />
        </>
      )}
      {hkr && (
        <>
          <ScoreBar label="H" score={hkr.h ?? 0} />
          <ScoreBar label="K" score={hkr.k ?? 0} />
          <ScoreBar label="R" score={hkr.r ?? 0} />
        </>
      )}
    </div>
  );
}

function topicText(topic: Topic) {
  const td = topic.topic_data || {};
  const lines = [
    `标题：${topic.title}`,
    `类型：${topic.content_type}`,
    `平台：${topic.platform}`,
    `目标：${topic.goal}`,
    `用户痛点：${td.user_pain_point || ""}`,
    `开头钩子：${td.hook || ""}`,
    `拍摄建议：${td.shooting_suggestion || ""}`,
    `转化方式：${td.conversion_method || ""}`,
    td.shooting_script ? `拍摄脚本：${td.shooting_script}` : "",
    td.spoken_script ? `口播文案：${td.spoken_script}` : "",
    td.seedance_video_prompt ? `Seedance 参考生视频提示词：${td.seedance_video_prompt}` : "",
    td.image_prompt ? `图片生成提示词：${td.image_prompt}` : "",
    td.image_edit_prompt ? `图生图改图提示词：${td.image_edit_prompt}` : "",
    `评分：${topic.score}`,
  ];
  if (td.rubric) {
    lines.push(
      `内容评分 ER=${td.rubric.er} SR=${td.rubric.sr} HP=${td.rubric.hp} QL=${td.rubric.ql} NA=${td.rubric.na} AB=${td.rubric.ab} SAT=${td.rubric.sat}`
    );
  }
  if (td.hkr) {
    lines.push(`HKR 质检 H=${td.hkr.h} K=${td.hkr.k} R=${td.hkr.r}`);
  }
  return lines.filter(Boolean).join("\n");
}

export default function TopicsPage() {
  const router = useRouter();
  const params = useParams();
  const projectId = Number(params.id);

  const [project, setProject] = useState<Project | null>(null);
  const [loadingProject, setLoadingProject] = useState(true);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [loadingTopics, setLoadingTopics] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [resultMeta, setResultMeta] = useState<{ provider: string; model: string; generation_record_id: number | null } | null>(null);

  const [platform, setPlatform] = useState("抖音");
  const [goal, setGoal] = useState("获客");
  const [contentFormat, setContentFormat] = useState<TopicContentFormat>("video_script");
  const [count, setCount] = useState(10);
  const [managingIds, setManagingIds] = useState<Set<number>>(new Set());
  const [batchProgress, setBatchProgress] = useState<{ generated: number; target: number } | null>(null);
  const [activeTab, setActiveTab] = useState<"all" | TopicContentFormat>("all");

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

  const fetchSavedTopics = useCallback(async () => {
    setLoadingTopics(true);
    try {
      const data = await listProjectTopics(projectId);
      setTopics(data);
    } catch {
      setTopics([]);
    } finally {
      setLoadingTopics(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchProject();
    fetchSavedTopics();
  }, [fetchProject, fetchSavedTopics]);

  async function handleGenerate() {
    setGenerating(true);
    setResultMeta(null);
    setBatchProgress(null);
    try {
      const existingTitles = topics.map((t) => t.title);
      if (count <= 10) {
        const res = await generateTopics(
          projectId,
          platform,
          goal,
          contentFormat,
          count,
          existingTitles,
        );
        setResultMeta({
          provider: res.provider,
          model: res.model,
          generation_record_id: res.generation_record_id,
        });
        setTopics((prev) => [...res.topics, ...prev]);
      } else {
        setBatchProgress({ generated: 0, target: count });
        const res = await generateTopicsBatch(
          projectId,
          platform,
          goal,
          contentFormat,
          count,
        );
        setBatchProgress({ generated: res.generated_count, target: res.target_count });
        setResultMeta({
          provider: res.provider,
          model: res.model,
          generation_record_id: null,
        });
        setTopics((prev) => [...res.topics, ...prev]);
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "选题生成失败");
    } finally {
      setGenerating(false);
      setBatchProgress(null);
    }
  }

  function setManaging(topicId: number, managing: boolean) {
    setManagingIds((prev) => {
      const next = new Set(prev);
      if (managing) next.add(topicId);
      else next.delete(topicId);
      return next;
    });
  }

  async function toggleFavorite(topic: Topic) {
    setManaging(topic.id, true);
    try {
      const updated = await updateTopicFavorite(topic.id, !topic.is_favorite);
      setTopics((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
    } catch (err) {
      alert(err instanceof Error ? err.message : "更新失败");
    } finally {
      setManaging(topic.id, false);
    }
  }

  async function removeTopic(topic: Topic) {
    if (!confirm("确定删除该选题？")) return;
    setManaging(topic.id, true);
    try {
      await deleteTopic(topic.id);
      setTopics((prev) => prev.filter((t) => t.id !== topic.id));
    } catch (err) {
      alert(err instanceof Error ? err.message : "删除失败");
    } finally {
      setManaging(topic.id, false);
    }
  }

  function getTopicFormat(topic: Topic): TopicContentFormat {
    const format = topic.topic_data?.content_format;
    if (format === "image") return "image";
    if (format === "video_spoken") return "video_spoken";
    return "video_script";
  }

  const filteredTopics = activeTab === "all"
    ? topics
    : topics.filter((t) => getTopicFormat(t) === activeTab);

  const topicCounts = {
    all: topics.length,
    video_spoken: topics.filter((t) => getTopicFormat(t) === "video_spoken").length,
    video_script: topics.filter((t) => getTopicFormat(t) === "video_script").length,
    image: topics.filter((t) => getTopicFormat(t) === "image").length,
  };

  async function copyTopic(topic: Topic) {
    try {
      await navigator.clipboard.writeText(topicText(topic));
      alert("已复制选题");
    } catch {
      alert("复制失败，请手动复制");
    }
  }

  async function copyAllTopics() {
    if (!topics.length) return;
    try {
      await navigator.clipboard.writeText(topics.map(topicText).join("\n\n---\n\n"));
      alert("已复制全部选题");
    } catch {
      alert("复制失败，请手动复制");
    }
  }

  function openScriptPage(topic: Topic) {
    router.push(`/projects/${projectId}/topics/${topic.id}/script`);
  }

  function openImageGenerationPage(promptText: string | undefined, mode: "text" | "image") {
    const cleanPrompt = (promptText || "").trim();
    if (!cleanPrompt) {
      alert("图片提示词为空");
      return;
    }
    const query = mode === "text" ? `?prompt=${encodeURIComponent(cleanPrompt)}` : `?mode=reference&prompt=${encodeURIComponent(cleanPrompt)}`;
    router.push(`/projects/${projectId}/images${query}`);
  }

  function openVideoGenerationPage(promptText: string | undefined) {
    const cleanPrompt = (promptText || "").trim();
    if (!cleanPrompt) {
      alert("视频提示词为空");
      return;
    }
    router.push(`/projects/${projectId}/videos?prompt=${encodeURIComponent(cleanPrompt)}`);
  }

  return (
    <section className="page-section topics-page">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="section-header"
      >
        <div>
          <p className="eyebrow">Topic Generation</p>
          <ProjectModuleTitle projectName={project?.project_name} moduleName="选题生成" />
        </div>
        <div className="section-header-actions">
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="metal-btn metal-btn-primary"
          >
            {generating ? (
              <span className="flex items-center gap-2">
                <span className="btn-spinner" />
                {batchProgress ? "批量生成中" : "生成中"}
              </span>
            ) : count > 10 ? (
              `批量生成 ${count} 条`
            ) : (
              "生成选题"
            )}
          </button>
          <Link href={`/projects/${projectId}`} className="project-return-btn">
            返回人设
          </Link>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.15 }}
        className="topic-workspace-plate"
      >
        {loadingProject ? (
          <div className="topic-context-strip">
            <div className="animate-pulse space-y-4">
              <div className="h-4 bg-[rgba(255,255,255,0.06)] w-1/3" />
              <div className="h-4 bg-[rgba(255,255,255,0.06)] w-2/3" />
              <div className="h-4 bg-[rgba(255,255,255,0.06)] w-1/2" />
            </div>
          </div>
        ) : project ? (
          <div className="topic-context-strip">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[#9ca3af] text-[13px]">
                {project.industry} / {project.product} / {project.platforms.join("、")}
              </span>
            </div>
            <p className="text-[#b0b0b0] text-sm leading-relaxed">
              {project.personal_intro}；目标客户：{project.target_audience}
            </p>
          </div>
        ) : null}

        <div className="topic-control-panel">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <GlassSelect label="平台" value={platform} onChange={setPlatform} options={platformOptions} />
            <GlassSelect label="内容目标" value={goal} onChange={setGoal} options={goalOptions} />
            <GlassSelect
              label="内容形态"
              value={contentFormat}
              onChange={(v) => setContentFormat(v as TopicContentFormat)}
              options={contentFormatOptions.map((o) => o.value)}
              renderLabel={(v) => contentFormatOptions.find((o) => o.value === v)?.label || String(v)}
            />
            <GlassSelect
              label="选题数量"
              value={count}
              onChange={(v) => setCount(Number(v))}
              options={countOptions}
              renderLabel={(v) => `${v} 个`}
            />
          </div>
        </div>

        {generating ? (
          <div className="topic-generate-state">
            <div className="flex items-center gap-3 mb-3">
              <span className="btn-spinner" />
              <span className="text-[13px] text-[#f5f5f5]">
                {batchProgress
                  ? `批量生成中 ${batchProgress.generated}/${batchProgress.target} 条...`
                  : "AI 正在构思选题..."}
              </span>
            </div>
            {batchProgress && batchProgress.target > 0 ? (
              <div className="w-full h-1.5 bg-[rgba(255,255,255,0.06)] rounded-full overflow-hidden">
                <div
                  className="h-full bg-[rgba(208,221,214,0.5)] rounded-full transition-all duration-500"
                  style={{
                    width: `${Math.min(100, (batchProgress.generated / batchProgress.target) * 100)}%`,
                  }}
                />
              </div>
            ) : (
              <div className="space-y-2">
                <div className="h-2 bg-[rgba(99,102,241,0.08)] rounded w-3/4 animate-pulse" />
                <div className="h-2 bg-[rgba(99,102,241,0.06)] rounded w-full animate-pulse" />
              </div>
            )}
          </div>
        ) : null}

        {!topics.length && !loadingTopics && !generating ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
            className="topic-empty-state"
          >
            <h2 className="text-[21px] font-[680] text-[#f5f5f5] mb-2">尚未生成选题</h2>
            <p className="text-[#9ca3af] text-sm">
              选择平台、目标、内容形态和数量后生成可直接使用的选题方案。
            </p>
          </motion.div>
        ) : null}

        {topics.length > 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
            className="topic-results-plate"
          >
          <div className="flex items-center justify-between mb-4">
            <div className="text-[13px] text-[#9ca3af]">
              {resultMeta ? (
                <span>
                  Provider：{resultMeta.provider} / Model：{resultMeta.model} / 记录 ID：{resultMeta.generation_record_id}
                </span>
              ) : (
                <span>已保存选题：{topics.length} 个</span>
              )}
            </div>
            <button onClick={copyAllTopics} className="metal-btn" disabled={!topics.length}>
              复制全部选题
            </button>
          </div>

          {/* 分类 Tab */}
          <div className="topic-tab-row">
            {[
              { key: "all", label: "全部", count: topicCounts.all },
              { key: "video_spoken", label: "视频：口播", count: topicCounts.video_spoken },
              { key: "video_script", label: "视频：脚本", count: topicCounts.video_script },
              { key: "image", label: "图片", count: topicCounts.image },
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as "all" | TopicContentFormat)}
                className={`metal-btn ${activeTab === tab.key ? "metal-btn-primary" : ""}`}
              >
                {tab.label}
                <span className="ml-1.5 text-[11px] opacity-60">{tab.count}</span>
              </button>
            ))}
          </div>

          {loadingTopics ? (
            <div className="metal-block p-8">
              <div className="animate-pulse space-y-4">
                <div className="h-4 bg-[rgba(255,255,255,0.06)] rounded w-1/3" />
                <div className="h-4 bg-[rgba(255,255,255,0.06)] rounded w-full" />
                <div className="h-4 bg-[rgba(255,255,255,0.06)] rounded w-2/3" />
              </div>
            </div>
          ) : (
            <div className="topic-card-grid">
              <AnimatePresence>
                {filteredTopics.map((topic) => {
                  const td = topic.topic_data || {};
                  const managing = managingIds.has(topic.id);
                  return (
                    <motion.article
                      key={topic.id}
                      layout
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
                      className="topic-card ai-context-card"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex flex-wrap gap-1.5 items-center">
                          <AIGeneratedBadge />
                          <span className={`tag ${platformTagClass(topic.platform)}`}>
                            {topic.platform}
                          </span>
                          <span className="tag tag-info">{topic.content_type}</span>
                          <span className="tag tag-warning">{topic.goal}</span>
                          <span className="tag tag-success">
                            {topicContentFormatLabel(topic, contentFormat)}
                          </span>
                          {topic.is_favorite && <span className="tag tag-danger">已收藏</span>}
                        </div>
                        <span className="text-[#f5f5f5] text-sm font-bold">{topic.score}</span>
                      </div>

                      <h2 className="text-[16px] font-[680] text-[#f5f5f5] mb-3 leading-snug">
                        {topic.title}
                      </h2>

                      <RubricMini rubric={td.rubric} hkr={td.hkr} />

                      <dl className="space-y-2 text-sm mb-4 flex-1 mt-2">
                        {td.spoken_script ? (
                          <div>
                            <dt className="text-[12px] text-[#9ca3af] mb-0.5">口播文案</dt>
                            <dd className="text-[#b0b0b0] leading-relaxed whitespace-pre-wrap">{td.spoken_script}</dd>
                          </div>
                        ) : getTopicFormat(topic) === "image" ? (
                          <div className="text-[#9ca3af] text-sm">图片选题，只需标题即可。</div>
                        ) : (
                          <>
                            <div>
                              <dt className="text-[12px] text-[#9ca3af] mb-0.5">用户痛点</dt>
                              <dd className="text-[#b0b0b0] leading-relaxed">{td.user_pain_point || "—"}</dd>
                            </div>
                            <div>
                              <dt className="text-[12px] text-[#9ca3af] mb-0.5">开头钩子</dt>
                              <dd className="text-[#b0b0b0] leading-relaxed">{td.hook || "—"}</dd>
                            </div>
                            <div>
                              <dt className="text-[12px] text-[#9ca3af] mb-0.5">拍摄建议</dt>
                              <dd className="text-[#b0b0b0] leading-relaxed">{td.shooting_suggestion || "—"}</dd>
                            </div>
                            <div>
                              <dt className="text-[12px] text-[#9ca3af] mb-0.5">转化方式</dt>
                              <dd className="text-[#b0b0b0] leading-relaxed">{td.conversion_method || "—"}</dd>
                            </div>
                            {td.shooting_script ? (
                              <div>
                                <dt className="text-[12px] text-[#9ca3af] mb-0.5">拍摄脚本</dt>
                                <dd className="text-[#b0b0b0] leading-relaxed">{td.shooting_script}</dd>
                              </div>
                            ) : null}
                          </>
                        )}
                        {td.seedance_video_prompt ? (
                          <div>
                            <dt className="text-[12px] text-[#9ca3af] mb-0.5">Seedance 参考生视频提示词</dt>
                            <dd className="text-[#b0b0b0] leading-relaxed">{td.seedance_video_prompt}</dd>
                          </div>
                        ) : null}
                        {td.image_prompt ? (
                          <div>
                            <dt className="text-[12px] text-[#9ca3af] mb-0.5">图片生成提示词</dt>
                            <dd>
                              <div className="flex items-start gap-2">
                                <span className="text-[#b0b0b0] leading-relaxed flex-1">{td.image_prompt}</span>
                                <button
                                  onClick={() => openImageGenerationPage(td.image_prompt, "text")}
                                  className="metal-btn text-xs shrink-0"
                                  style={{ minHeight: 28, padding: "0 10px" }}
                                >
                                  去出图
                                </button>
                              </div>
                            </dd>
                          </div>
                        ) : null}
                        {td.image_edit_prompt ? (
                          <div>
                            <dt className="text-[12px] text-[#9ca3af] mb-0.5">图生图改图提示词</dt>
                            <dd>
                              <div className="flex items-start gap-2">
                                <span className="text-[#b0b0b0] leading-relaxed flex-1">{td.image_edit_prompt}</span>
                                <button
                                  onClick={() => openImageGenerationPage(td.image_edit_prompt, "image")}
                                  className="metal-btn text-xs shrink-0"
                                  style={{ minHeight: 28, padding: "0 10px" }}
                                >
                                  去图生图
                                </button>
                              </div>
                            </dd>
                          </div>
                        ) : null}
                      </dl>

                      {/* Generation entry points */}
                      <div className="flex gap-2 mb-3">
                        {td.seedance_video_prompt ? (
                          <button
                            onClick={() => openVideoGenerationPage(td.seedance_video_prompt)}
                            className="flex-1 py-2 rounded-[0.625rem] text-[13px] font-medium border transition-all hover:bg-white/[0.08] hover:border-white/[0.15]"
                            style={{
                              background: "rgba(255,255,255,0.04)",
                              borderColor: "rgba(255,255,255,0.1)",
                              color: "#c0c0c0",
                            }}
                          >
                            直接生视频
                          </button>
                        ) : null}
                        {td.image_prompt ? (
                          <button
                            onClick={() => openImageGenerationPage(td.image_prompt, "text")}
                            className="flex-1 py-2 rounded-[0.625rem] text-[13px] font-medium border transition-all hover:bg-white/[0.04] hover:border-white/[0.12] hover:text-[#f5f5f5]"
                            style={{
                              background: "transparent",
                              borderColor: "rgba(255,255,255,0.06)",
                              color: "#7a8a82",
                            }}
                          >
                            先生图
                          </button>
                        ) : null}
                      </div>

                      <div className="flex flex-wrap gap-2 mt-auto pt-3 border-t border-[rgba(255,255,255,0.06)]">
                        <button
                          onClick={() => copyTopic(topic)}
                          className="metal-btn text-xs"
                          style={{ minHeight: 28, padding: "0 10px" }}
                        >
                          复制选题
                        </button>
                        <button
                          onClick={() => toggleFavorite(topic)}
                          disabled={managing}
                          className="metal-btn text-xs"
                          style={{ minHeight: 28, padding: "0 10px" }}
                        >
                          {topic.is_favorite ? "取消收藏" : "收藏"}
                        </button>
                        <button
                          onClick={() => removeTopic(topic)}
                          disabled={managing}
                          className="metal-btn text-xs text-[#a05858] hover:text-[#b86868]"
                          style={{ minHeight: 28, padding: "0 10px" }}
                        >
                          删除
                        </button>
                        <button
                          onClick={() => openScriptPage(topic)}
                          className="metal-btn text-xs"
                          style={{ minHeight: 28, padding: "0 10px" }}
                        >
                          生成文案
                        </button>
                      </div>
                    </motion.article>
                  );
                })}
              </AnimatePresence>
            </div>
          )}
          </motion.div>
        ) : null}
      </motion.div>
    </section>
  );
}
