"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import { motion } from "framer-motion";
import { api } from "@/lib/api/client";
import { getProject, type Project } from '@/lib/api/projects';
import TypingIndicator from "@/components/ui/TypingIndicator";
import AIGeneratedBadge from "@/components/ui/AIGeneratedBadge";
import ProjectModuleTitle from '@/components/ProjectModuleTitle';

interface ScriptRubric {
  er: number;
  sr: number;
  hp: number;
  ql: number;
  na: number;
  ab: number;
  sat: number;
}

interface Script {
  id: number;
  project_id: number;
  topic_id: number;
  title: string;
  script_type: string;
  platform: string;
  script_content: string;
  shot_suggestions: string[];
  conversion_script: string;
  script_data: Record<string, unknown> & { rubric?: ScriptRubric };
  created_at: string;
}

interface ScriptGenerateResponse {
  script: Script;
  generation_record_id: number | null;
  provider: string;
  model: string;
  usage: Record<string, unknown>;
  latency_ms: number;
}

function ScoreBar({ label, score }: { label: string; score: number }) {
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

function RubricMini({ rubric }: { rubric?: ScriptRubric }) {
  if (!rubric) return null;
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-2 pt-2 border-t border-[rgba(255,255,255,0.04)]">
      <ScoreBar label="ER" score={rubric.er ?? 0} />
      <ScoreBar label="SR" score={rubric.sr ?? 0} />
      <ScoreBar label="HP" score={rubric.hp ?? 0} />
      <ScoreBar label="QL" score={rubric.ql ?? 0} />
      <ScoreBar label="NA" score={rubric.na ?? 0} />
      <ScoreBar label="AB" score={rubric.ab ?? 0} />
      <ScoreBar label="SAT" score={rubric.sat ?? 0} />
    </div>
  );
}

const scriptTypeOptions = ["聊观点", "讲故事", "晒过程", "教知识", "辩认知", "纯带货"];
const durationOptions = ["15秒", "30秒", "60秒", "90秒", "120秒", "180秒", "300秒"];
const goalOptions = ["私信获客", "涨粉", "信任建立", "成交转化", "品牌曝光"];

export default function ScriptPage() {
  const router = useRouter();
  const params = useParams();
  const projectId = Number(params.id);
  const topicId = Number(params.topicId);

  const [project, setProject] = useState<Project | null>(null);
  const [scripts, setScripts] = useState<Script[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [scriptType, setScriptType] = useState("聊观点");
  const [duration, setDuration] = useState("60秒");
  const [goal, setGoal] = useState("私信获客");

  const fetchScripts = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.get<Script[]>(`/api/topics/${topicId}/scripts`);
      setScripts(data);
    } catch {
      setScripts([]);
    } finally {
      setLoading(false);
    }
  }, [topicId]);

  useEffect(() => {
    fetchScripts();
  }, [fetchScripts]);

  useEffect(() => {
    getProject(projectId)
      .then(setProject)
      .catch(() => router.push('/projects'));
  }, [projectId, router]);

  async function handleGenerate() {
    setGenerating(true);
    try {
      const res = await api.post<ScriptGenerateResponse>("/api/creation/scripts/generate", {
        project_id: projectId,
        topic_id: topicId,
        platform: null,
        script_type: scriptType,
        duration,
        goal,
      });
      setScripts((prev) => [res.script, ...prev]);
    } catch (err) {
      alert(err instanceof Error ? err.message : "文案生成失败");
    } finally {
      setGenerating(false);
    }
  }

  async function copyScript(script: Script) {
    const lines = [
      `标题：${script.title}`,
      `类型：${script.script_type}`,
      `平台：${script.platform}`,
      `文案内容：\n${script.script_content}`,
      script.shot_suggestions?.length ? `拍摄建议：\n${script.shot_suggestions.join("\n")}` : "",
      `转化文案：\n${script.conversion_script}`,
    ];
    const rubric = script.script_data?.rubric;
    if (rubric) {
      lines.push(
        `内容评分 ER=${rubric.er} SR=${rubric.sr} HP=${rubric.hp} QL=${rubric.ql} NA=${rubric.na} AB=${rubric.ab} SAT=${rubric.sat}`
      );
    }
    try {
      await navigator.clipboard.writeText(lines.filter(Boolean).join("\n\n"));
      alert("已复制文案");
    } catch {
      alert("复制失败");
    }
  }

  const Select = ({
    label,
    value,
    onChange,
    options,
  }: {
    label: string;
    value: string;
    onChange: (v: string) => void;
    options: string[];
  }) => (
    <div className="flex flex-col gap-1.5">
      <label className="text-[12px] font-[540] text-[#9ca3af]">{label}</label>
      <select
        className="input-glass w-full appearance-none cursor-pointer"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    </div>
  );

  return (
    <section className="page-section script-page">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="section-header"
      >
        <div>
          <p className="eyebrow">Script Generation</p>
          <ProjectModuleTitle projectName={project?.project_name} moduleName='文案生成' />
        </div>
        <button onClick={() => router.push(`/projects/${projectId}/topics`)} className="btn btn-secondary">
          返回选题
        </button>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
        className="script-workspace-plate"
      >
        <div className="metal-block script-control-panel p-5 mb-6">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-4">
          <Select label="文案类型" value={scriptType} onChange={setScriptType} options={scriptTypeOptions} />
          <Select label="时长" value={duration} onChange={setDuration} options={durationOptions} />
          <Select label="目标" value={goal} onChange={setGoal} options={goalOptions} />
        </div>
        <div className="flex justify-end">
          <button onClick={handleGenerate} disabled={generating} className="btn btn-primary">
            {generating ? (
              <span className="flex items-center gap-2">
                <span className="btn-spinner" />
                生成中
              </span>
            ) : (
              "生成文案"
            )}
          </button>
        </div>
        </div>

        {loading ? (
        <div className="script-results-plate overflow-hidden">
          <TypingIndicator text="AI 正在撰写文案..." />
          <div className="px-4 pb-4 space-y-3">
            <div className="h-3 bg-[rgba(99,102,241,0.08)] rounded w-3/4 animate-pulse" />
            <div className="h-3 bg-[rgba(99,102,241,0.06)] rounded w-full animate-pulse" />
            <div className="h-3 bg-[rgba(99,102,241,0.06)] rounded w-2/3 animate-pulse" />
          </div>
        </div>
      ) : !scripts.length ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
          className="script-results-plate empty-state"
        >
          <h2 className="text-[21px] font-[680] text-[#f5f5f5] mb-2">尚未生成文案</h2>
          <p className="text-[#9ca3af] text-sm">选择文案类型、时长和目标后生成文案。</p>
        </motion.div>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
          className="script-results-plate script-list"
        >
          {scripts.map((script) => (
            <div key={script.id} className="script-card ai-context-card">
              <div className="flex items-start justify-between mb-3">
                <div className="flex flex-wrap gap-1.5 items-center">
                  <AIGeneratedBadge />
                  <span className="tag tag-info">{script.script_type}</span>
                  <span className="tag tag-success">{script.platform || "—"}</span>
                </div>
                <button
                  onClick={() => copyScript(script)}
                  className="btn btn-ghost text-xs"
                  style={{ minHeight: 28, padding: "0 10px" }}
                >
                  复制文案
                </button>
              </div>
              <h3 className="text-[16px] font-[680] text-[#f5f5f5] mb-2">{script.title}</h3>
              <RubricMini rubric={script.script_data?.rubric} />
              <div className="space-y-3 text-sm mt-3">
                <div>
                  <span className="text-[12px] text-[#9ca3af] block mb-1">文案内容</span>
                  <p className="text-[#b0b0b0] leading-relaxed whitespace-pre-wrap">{script.script_content}</p>
                </div>
                {script.shot_suggestions?.length > 0 && (
                  <div>
                    <span className="text-[12px] text-[#9ca3af] block mb-1">拍摄建议</span>
                    <ul className="list-disc list-inside text-[#b0b0b0] leading-relaxed">
                      {script.shot_suggestions.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <div>
                  <span className="text-[12px] text-[#9ca3af] block mb-1">转化文案</span>
                  <p className="text-[#b0b0b0] leading-relaxed whitespace-pre-wrap">{script.conversion_script}</p>
                </div>
              </div>
            </div>
          ))}
        </motion.div>
      )}
      </motion.div>
    </section>
  );
}
