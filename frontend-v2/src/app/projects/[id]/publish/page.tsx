"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useParams } from "next/navigation";
import { motion } from "framer-motion";
import { getProject, type Project } from "@/lib/api/projects";
import ProjectModuleTitle from "@/components/ProjectModuleTitle";


export default function PublishPage() {
  const router = useRouter();
  const params = useParams();
  const projectId = Number(params.id);
  const [project, setProject] = useState<Project | null>(null);

  useEffect(() => {
    getProject(projectId)
      .then(setProject)
      .catch(() => router.push("/projects"));
  }, [projectId, router]);

  return (
    <section className="page-section">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="section-header"
      >
        <div>
          <p className="eyebrow">Content Publish</p>
          <ProjectModuleTitle projectName={project?.project_name} moduleName="内容发布" />
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
        className="glass p-8 rounded-[1rem] text-center"
      >
        <h2 className="text-[21px] font-[680] text-[#f5f5f5] mb-2">
          内容发布功能开发中
        </h2>
        <p className="text-[#9ca3af] text-sm">
          该功能将在后续版本上线，敬请期待。
        </p>
      </motion.div>
    </section>
  );
}
