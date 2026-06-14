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
import { formatBeijingTime } from "@/lib/time";

export default function AccountPackagePage() {
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
    if (!confirm("重新生成会覆盖现有账号包装，确定继续吗？")) return;
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

  if (!accountPackage) {
    return (
      <section className="page-section">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="section-header"
        >
          <div>
            <p className="eyebrow">Account Package</p>
            <ProjectModuleTitle projectName={project?.project_name} moduleName="账号包装" />
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
          <p className="text-[#7a8a82] text-sm mb-6">暂无账号包装数据</p>
          <button
            onClick={handleRegenerate}
            disabled={generating}
            className="text-[13px] px-5 py-2.5 rounded-md border transition-all hover:bg-white/[0.08] disabled:opacity-40"
            style={{ borderColor: "rgba(255,255,255,0.1)", color: "#c0c0c0" }}
          >
            {generating ? "生成中..." : "生成账号包装"}
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
          <p className="eyebrow">Account Package</p>
          <ProjectModuleTitle projectName={project?.project_name} moduleName="账号包装" />
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Account Identity */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
          className="glass rounded-[1rem] p-5 md:p-6"
        >
          <h2 className="text-[15px] font-bold text-[#f5f5f5] mb-5">账号定位</h2>
          <div className="space-y-4">
            <Block label="定位概述" value={accountPackage.account_positioning} />
            <Block label="人设" value={accountPackage.persona} />
            {accountPackage.content_style && (
              <Block label="内容风格" value={accountPackage.content_style} />
            )}
            {accountPackage.execution_stage && (
              <Block label="当前阶段" value={accountPackage.execution_stage} />
            )}
          </div>
        </motion.div>

        {/* Account Names */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.15 }}
          className="glass rounded-[1rem] p-5 md:p-6"
        >
          <h2 className="text-[15px] font-bold text-[#f5f5f5] mb-5">推荐账号名</h2>
          {accountPackage.account_names && accountPackage.account_names.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {accountPackage.account_names.map((name, i) => (
                <span
                  key={i}
                  className="text-[13px] px-3 py-1.5 rounded-md border"
                  style={{
                    borderColor: "rgba(255,255,255,0.08)",
                    color: "#b0b0b0",
                    background: "rgba(255,255,255,0.03)",
                  }}
                >
                  {name}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-[13px] text-[#7a8a82]">暂无推荐账号名</p>
          )}

          {accountPackage.bios && Object.keys(accountPackage.bios).length > 0 && (
            <div className="mt-6 pt-5 border-t border-white/[0.06]">
              <h3 className="text-[13px] font-medium text-[#9ca3af] mb-3">平台简介</h3>
              <div className="space-y-2">
                {Object.entries(accountPackage.bios).map(([platform, bio]) => (
                  <div key={platform} className="flex gap-3 text-[13px]">
                    <span className="text-[#7a8a82] shrink-0 w-14">{platform}</span>
                    <span className="text-[#b0b0b0] leading-relaxed">{bio}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>

        {/* Target User Profile */}
        {accountPackage.target_user_profile &&
          Object.keys(accountPackage.target_user_profile).length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
              className="glass rounded-[1rem] p-5 md:p-6"
            >
              <h2 className="text-[15px] font-bold text-[#f5f5f5] mb-5">目标受众</h2>
              <div className="space-y-3">
                {Object.entries(accountPackage.target_user_profile).map(([key, value]) => (
                  <div key={key} className="text-[13px]">
                    <span className="text-[#9ca3af] block mb-0.5">{key}</span>
                    <span className="text-[#b0b0b0] leading-relaxed">
                      {typeof value === "string" ? value : JSON.stringify(value)}
                    </span>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

        {/* Platform Strategies */}
        {accountPackage.platform_strategies &&
          Object.keys(accountPackage.platform_strategies).length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.25 }}
              className="glass rounded-[1rem] p-5 md:p-6"
            >
              <h2 className="text-[15px] font-bold text-[#f5f5f5] mb-5">平台策略</h2>
              <div className="space-y-4">
                {Object.entries(accountPackage.platform_strategies).map(([platform, strategy]) => (
                  <div key={platform} className="text-[13px]">
                    <span className="text-[#9ca3af] font-medium block mb-1">{platform}</span>
                    {typeof strategy === "string" ? (
                      <p className="text-[#b0b0b0] leading-relaxed">{strategy}</p>
                    ) : (
                      <pre className="text-[#b0b0b0] leading-relaxed whitespace-pre-wrap font-sans">
                        {JSON.stringify(strategy, null, 2)}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            </motion.div>
          )}

        {/* Content Columns */}
        {accountPackage.content_columns && accountPackage.content_columns.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.3 }}
            className="glass rounded-[1rem] p-5 md:p-6"
          >
            <h2 className="text-[15px] font-bold text-[#f5f5f5] mb-5">内容栏目</h2>
            <div className="space-y-3">
              {accountPackage.content_columns.map((col, i) => (
                <div
                  key={i}
                  className="text-[13px] p-3 rounded-md border"
                  style={{ borderColor: "rgba(255,255,255,0.06)", background: "rgba(255,255,255,0.02)" }}
                >
                  {typeof col === "string" ? (
                    <span className="text-[#b0b0b0]">{col}</span>
                  ) : (
                    <pre className="text-[#b0b0b0] whitespace-pre-wrap font-sans">
                      {JSON.stringify(col, null, 2)}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Trust Design */}
        {(accountPackage.trust_design?.length || accountPackage.trust_points?.length) ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.35 }}
            className="glass rounded-[1rem] p-5 md:p-6"
          >
            <h2 className="text-[15px] font-bold text-[#f5f5f5] mb-5">信任设计</h2>
            <div className="space-y-4">
              {accountPackage.trust_design && accountPackage.trust_design.length > 0 && (
                <div>
                  <span className="text-[12px] text-[#9ca3af] block mb-2">信任策略</span>
                  <List items={accountPackage.trust_design} />
                </div>
              )}
              {accountPackage.trust_points && accountPackage.trust_points.length > 0 && (
                <div>
                  <span className="text-[12px] text-[#9ca3af] block mb-2">信任锚点</span>
                  <List items={accountPackage.trust_points} />
                </div>
              )}
            </div>
          </motion.div>
        ) : null}

        {/* Conversion & Monetization */}
        {(accountPackage.conversion_path?.length || accountPackage.monetization_paths?.length) ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.4 }}
            className="glass rounded-[1rem] p-5 md:p-6"
          >
            <h2 className="text-[15px] font-bold text-[#f5f5f5] mb-5">转化与变现</h2>
            <div className="space-y-4">
              {accountPackage.conversion_path && accountPackage.conversion_path.length > 0 && (
                <div>
                  <span className="text-[12px] text-[#9ca3af] block mb-2">转化路径</span>
                  <List items={accountPackage.conversion_path} />
                </div>
              )}
              {accountPackage.monetization_paths && accountPackage.monetization_paths.length > 0 && (
                <div>
                  <span className="text-[12px] text-[#9ca3af] block mb-2">变现方式</span>
                  <List items={accountPackage.monetization_paths} />
                </div>
              )}
            </div>
          </motion.div>
        ) : null}
      </div>

      {/* Footer meta */}
      {accountPackage.created_at && (
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-[11px] text-[#9ca3af] mt-6 text-right"
        >
          生成于 {formatBeijingTime(accountPackage.created_at)}
        </motion.p>
      )}
    </section>
  );
}

function Block({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-[12px] text-[#9ca3af] block mb-1">{label}</span>
      <p className="text-[14px] text-[#f5f5f5] leading-relaxed">{value}</p>
    </div>
  );
}

function List({ items }: { items: string[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item, i) => (
        <span
          key={i}
          className="text-[12px] px-2.5 py-1 rounded-md border"
          style={{
            borderColor: "rgba(255,255,255,0.06)",
            color: "#b0b0b0",
            background: "rgba(255,255,255,0.02)",
          }}
        >
          {item}
        </span>
      ))}
    </div>
  );
}
