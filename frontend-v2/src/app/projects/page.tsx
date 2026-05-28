"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { X } from "@phosphor-icons/react";
import { listProjects, deleteProject, type Project } from "@/lib/api/projects";

function platformTagClass(platform: string) {
  if (platform.includes("抖音")) return "platform-douyin";
  if (platform.includes("快手")) return "platform-kuaishou";
  if (platform.includes("小红书")) return "platform-xiaohongshu";
  if (platform.includes("视频号")) return "platform-video";
  return "tag-info";
}

export default function ProjectsPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(false);

  async function fetchProjects() {
    setLoading(true);
    try {
      const data = await listProjects();
      setProjects(data);
    } catch {
      // error handled by api client
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchProjects();
  }, []);

  async function handleDelete(project: Project) {
    if (!confirm(`确认删除人设档案「${project.project_name}」？`)) return;
    try {
      await deleteProject(project.id);
      await fetchProjects();
    } catch {
      alert("删除失败");
    }
  }

  const projectCount = projects.length;
  const platformCount = new Set(
    projects.flatMap((p) => p.platforms),
  ).size;
  const activeStageCount = new Set(
    projects.map((p) => p.current_stage),
  ).size;

  return (
    <section className="page-section projects-page">
      {/* Section Header */}
      <div className="section-header">
        <div>
          <p className="eyebrow">Projects</p>
          <h1 className="text-[28px] md:text-[36px] font-bold leading-[1.15] tracking-[-0.02em] text-[#f5f5f5]">
            人设档案
          </h1>
        </div>
        <button
          onClick={() => router.push("/projects/new")}
          className="btn btn-primary"
        >
          新建人设
        </button>
      </div>

      {/* Overview Strip */}
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="overview-strip"
      >
        <div className="overview-item">
          <span>人设总数</span>
          <strong>{projectCount}</strong>
        </div>
        <div className="overview-item">
          <span>覆盖平台</span>
          <strong>{platformCount}</strong>
        </div>
        <div className="overview-item">
          <span>运营阶段</span>
          <strong>{activeStageCount}</strong>
        </div>
      </motion.div>

      {/* Project Cards */}
      {loading && projects.length === 0 ? (
        <div className="flex items-center justify-center py-20">
          <div className="text-[#9ca3af] text-sm">加载中...</div>
        </div>
      ) : projects.length === 0 ? (
        <div className="empty-state">
          <h2>暂无人设档案</h2>
          <p>点击右上角按钮创建你的第一个人设档案</p>
        </div>
      ) : (
        <div className="project-card-grid">
          {projects.map((project, i) => (
            <motion.div
              key={project.id}
              initial={{ opacity: 0, y: 28 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                duration: 0.55,
                ease: [0.16, 1, 0.3, 1],
                delay: 0.2 + i * 0.08,
              }}
              className="project-card flat-delete-target"
            >
              <div className="flex items-center justify-between gap-3 mb-6">
                <button
                  onClick={() => router.push(`/projects/${project.id}`)}
                  className="text-[20px] font-bold leading-[1.25] tracking-[-0.01em] text-[#f5f5f5] text-left transition-colors hover:text-[#4a856e]"
                >
                  {project.project_name}
                </button>
                <button
                  onClick={() => handleDelete(project)}
                  className="flat-delete-action"
                  title="删除"
                  aria-label={`删除人设档案 ${project.project_name}`}
                >
                  <X size={13} weight="bold" />
                </button>
              </div>

              <div className="grid grid-cols-2 gap-3 mb-[18px]">
                <div className="project-card-field min-h-[76px] p-[14px_16px] border border-[rgba(255,255,255,0.04)] bg-[rgba(255,255,255,0.04)]">
                  <span className="block text-[#9ca3af] text-[12px] font-[520]">
                    行业
                  </span>
                  <strong className="block mt-2 text-[14px] font-[620] leading-[1.45] text-[#b0b0b0]">
                    {project.industry}
                  </strong>
                </div>
                <div className="project-card-field min-h-[76px] p-[14px_16px] border border-[rgba(255,255,255,0.04)] bg-[rgba(255,255,255,0.04)]">
                  <span className="block text-[#9ca3af] text-[12px] font-[520]">
                    产品
                  </span>
                  <strong className="block mt-2 text-[14px] font-[620] leading-[1.45] text-[#b0b0b0]">
                    {project.product}
                  </strong>
                </div>
              </div>

              <div className="min-h-[72px] mb-4">
                <div className="flex flex-wrap gap-2">
                  {project.platforms.map((platform) => (
                    <span
                      key={platform}
                      className={`tag ${platformTagClass(platform)}`}
                    >
                      {platform}
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex justify-end gap-2 mt-5">
                <button
                  onClick={() =>
                    router.push(`/projects/${project.id}/account-package`)
                  }
                  className="project-card-action btn btn-secondary text-[13px] min-h-[36px]"
                >
                  账号包装
                </button>
                <button
                  onClick={() =>
                    router.push(`/projects/${project.id}`)
                  }
                  className="project-card-action btn btn-primary text-[13px] min-h-[36px]"
                >
                  详情
                </button>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </section>
  );
}
