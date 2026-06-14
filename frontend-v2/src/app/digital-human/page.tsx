'use client';

import { motion } from "framer-motion";

export default function DigitalHumanPage() {
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
          <h1 className="text-[28px] md:text-[36px] font-bold leading-[1.15] tracking-[-0.02em] text-[#f5f5f5]">
            数字人
          </h1>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className="glass p-8 rounded-[1rem] text-center"
      >
        <h2 className="text-[21px] font-[680] text-[#f5f5f5] mb-2">
          请在项目内使用数字人功能
        </h2>
        <p className="text-[#9ca3af] text-sm mb-4">
          数字人视频生成需要关联项目文案，请进入具体项目后使用。
        </p>
        <a href="/projects" className="btn btn-primary inline-block">
          前往项目列表
        </a>
      </motion.div>
    </section>
  );
}
