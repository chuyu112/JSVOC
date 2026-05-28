"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useParams } from "next/navigation";
import { motion } from "framer-motion";
import {
  getLatestAccountPackage,
  generateAccountPackage,
  type AccountPackage,
} from "@/lib/api/generationRecords";
import { getProject, type Project } from "@/lib/api/projects";
import ProjectModuleTitle from "@/components/ProjectModuleTitle";

export default function ExecutionPlanPage() {
  const router = useRouter();
  const params = useParams();
  const projectId = Number(params.id);

  const [project, setProject] = useState<Project | null>(null);
  const [accountPackage, setAccountPackage] = useState<AccountPackage | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const [projectData, packageData] = await Promise.all([
          getProject(projectId),
          getLatestAccountPackage(projectId).catch(() => null),
        ]);
        setProject(projectData);
        setAccountPackage(packageData);
      } catch {
        router.push("/projects");
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [projectId, router]);

  async function handleRegenerate() {
    if (!confirm("重新生成会覆盖现有执行计划，确定继续吗？")) return;
    setGenerating(true);
    try {
      await generateAccountPackage(projectId);
      const data = await getLatestAccountPackage(projectId);
      setAccountPackage(data);
    } catch (err) {
      alert(err instanceof Error ? err.message : "生成失败");
    } finally {
      setGenerating(false);
    }
  }

  if (loading) {
    return (
      <section className="page-section">
        <div className="flex items-center justify-center py-20">
          <div className="text-[#9ca3af] text-sm">加载中...</div>
        </div>
      </section>
    );
  }

  const executionPlan = accountPackage?.execution_plan;

  if (!executionPlan || !executionPlan.weekly_plan?.length) {
    return (
      <section className="page-section">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="section-header"
        >
          <div>
            <p className="eyebrow">Execution Plan</p>
            <ProjectModuleTitle projectName={project?.project_name} moduleName="执行计划" />
          </div>
          <div className="section-header-actions">
            <Link href={`/projects/${projectId}`} className="project-return-btn">
              返回人设
            </Link>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
          className="glass rounded-[1rem] p-10 text-center"
        >
          <p className="text-[#7a8a82] text-sm mb-6">暂无执行计划数据</p>
          <button
            onClick={handleRegenerate}
            disabled={generating}
            className="text-[13px] px-5 py-2.5 rounded-md border transition-all hover:bg-white/[0.08] disabled:opacity-40"
            style={{ borderColor: "rgba(255,255,255,0.1)", color: "#c0c0c0" }}
          >
            {generating ? "生成中..." : "生成执行计划"}
          </button>
        </motion.div>
      </section>
    );
  }

  return (
    <section className="page-section">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="section-header"
      >
        <div>
          <p className="eyebrow">Execution Plan</p>
          <ProjectModuleTitle projectName={project?.project_name} moduleName="执行计划" />
        </div>
        <div className="section-header-actions">
          <button
            onClick={handleRegenerate}
            disabled={generating}
            className="project-return-btn disabled:opacity-40"
          >
            {generating ? "生成中..." : "重新生成"}
          </button>
          <Link href={`/projects/${projectId}`} className="project-return-btn">
            返回人设
          </Link>
        </div>
      </motion.div>

      {/* Overview */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
        className="glass rounded-[1rem] p-5 md:p-6 mb-5"
      >
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Metric label="执行周期" value={executionPlan.cycle} />
          <Metric label="周计划数" value={`${executionPlan.weekly_plan.length} 周`} />
          <Metric label="日计划数" value={`${executionPlan.daily_plan.length} 天`} />
          {executionPlan.notes && executionPlan.notes.length > 0 && (
            <div className="col-span-2 md:col-span-1">
              <span className="text-[12px] text-[#9ca3af] block mb-1">备注</span>
              <div className="flex flex-wrap gap-1.5">
                {executionPlan.notes.map((note, i) => (
                  <span
                    key={i}
                    className="text-[11px] text-[#7a8a82] px-2 py-0.5 rounded border"
                    style={{ borderColor: "rgba(255,255,255,0.06)" }}
                  >
                    {note}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </motion.div>

      {/* Weekly Plan */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-5">
        {executionPlan.weekly_plan.map((week, index) => (
          <motion.div
            key={week.week}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.15 + index * 0.05 }}
            className="glass rounded-[1rem] p-5 md:p-6"
          >
            <div className="flex items-center gap-3 mb-4">
              <span
                className="text-[11px] font-medium px-2 py-0.5 rounded border"
                style={{ borderColor: "rgba(255,255,255,0.08)", color: "#9ca3af" }}
              >
                第 {week.week} 周
              </span>
            </div>
            <div className="space-y-3">
              <div>
                <span className="text-[12px] text-[#9ca3af] block mb-0.5">阶段目标</span>
                <p className="text-[14px] text-[#f5f5f5] leading-relaxed">{week.goal}</p>
              </div>
              <div>
                <span className="text-[12px] text-[#9ca3af] block mb-0.5">核心重点</span>
                <p className="text-[14px] text-[#f5f5f5] leading-relaxed">{week.focus}</p>
              </div>
              {week.key_tasks && week.key_tasks.length > 0 && (
                <div>
                  <span className="text-[12px] text-[#9ca3af] block mb-2">关键任务</span>
                  <div className="flex flex-wrap gap-2">
                    {week.key_tasks.map((task, i) => (
                      <span
                        key={i}
                        className="text-[12px] px-2.5 py-1 rounded-md border"
                        style={{
                          borderColor: "rgba(255,255,255,0.06)",
                          color: "#b0b0b0",
                          background: "rgba(255,255,255,0.02)",
                        }}
                      >
                        {task}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Daily Plan */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.3 }}
        className="glass rounded-[1rem] p-5 md:p-6"
      >
        <h2 className="text-[15px] font-bold text-[#f5f5f5] mb-5">每日执行计划</h2>
        <div className="overflow-x-auto">
          <div className="min-w-[640px]">
            {/* Table Header */}
            <div className="grid grid-cols-[60px_1fr_1fr_1fr_1fr] gap-3 pb-3 border-b border-white/[0.06]">
              <span className="text-[11px] text-[#9ca3af] uppercase tracking-wider">Day</span>
              <span className="text-[11px] text-[#9ca3af] uppercase tracking-wider">任务</span>
              <span className="text-[11px] text-[#9ca3af] uppercase tracking-wider">选题</span>
              <span className="text-[11px] text-[#9ca3af] uppercase tracking-wider">拍摄任务</span>
              <span className="text-[11px] text-[#9ca3af] uppercase tracking-wider">复盘指标</span>
            </div>
            {/* Table Body */}
            <div className="divide-y divide-white/[0.04]">
              {executionPlan.daily_plan.map((day) => (
                <div key={day.day} className="grid grid-cols-[60px_1fr_1fr_1fr_1fr] gap-3 py-3">
                  <span className="text-[13px] text-[#f5f5f5] font-medium self-center">
                    D{day.day}
                  </span>
                  <span className="text-[13px] text-[#f5f5f5] leading-relaxed self-center">
                    {day.task}
                  </span>
                  <span className="text-[13px] text-[#f5f5f5] leading-relaxed self-center">
                    {day.topic}
                  </span>
                  <span className="text-[13px] text-[#f5f5f5] leading-relaxed self-center">
                    {day.shooting_task}
                  </span>
                  <div className="flex flex-wrap gap-1 self-center">
                    {day.review_metrics.map((metric, i) => (
                      <span
                        key={i}
                        className="text-[11px] text-[#7a8a82] px-1.5 py-0.5 rounded border"
                        style={{ borderColor: "rgba(255,255,255,0.06)" }}
                      >
                        {metric}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </motion.div>

      {/* Footer meta */}
      {accountPackage?.created_at && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-[11px] text-[#9ca3af] mt-6 text-right"
        >
          生成于 {new Date(accountPackage.created_at).toLocaleString("zh-CN")}
        </motion.p>
      )}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-[12px] text-[#9ca3af] block mb-1">{label}</span>
      <p className="text-[15px] font-medium text-[#f5f5f5]">{value}</p>
    </div>
  );
}
