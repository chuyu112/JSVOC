'use client';

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { getProject, type Project } from "@/lib/api/projects";
import DigitalHumanPlaceholder from "@/components/DigitalHumanPlaceholder";
import ProjectModuleTitle from "@/components/ProjectModuleTitle";

export default function ProjectDigitalHumanPage() {
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
    <section className="page-section digital-human-page">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="section-header"
      >
        <div>
          <p className="eyebrow">Digital Human</p>
          <ProjectModuleTitle projectName={project?.project_name} moduleName="数字人" />
        </div>
        <div className="section-header-actions">
          <Link href={`/projects/${projectId}`} className="project-return-btn">
            返回人设
          </Link>
        </div>
      </motion.div>

      <DigitalHumanPlaceholder />
    </section>
  );
}
