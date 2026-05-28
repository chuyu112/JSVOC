"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import HistoryClient from "@/app/history/HistoryClient";

export default function ProjectHistoryPage() {
  const params = useParams();
  const projectId = Number(params.id);

  return (
    <section className="page-section">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="section-header"
      >
        <div>
          <p className="eyebrow">Generation History</p>
          <h1 className="text-[28px] md:text-[36px] font-bold leading-[1.15] tracking-[-0.02em] text-[#f5f5f5]">
            人设 {projectId} 生成记录
          </h1>
        </div>
        <div className="section-header-actions">
          <Link href={`/projects/${projectId}`} className="project-return-btn">
            返回人设
          </Link>
        </div>
      </motion.div>

      <HistoryClient projectId={projectId} />
    </section>
  );
}
