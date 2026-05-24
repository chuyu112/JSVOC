'use client';

import { motion } from "framer-motion";
import DigitalHumanPlaceholder from "@/components/DigitalHumanPlaceholder";

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

      <DigitalHumanPlaceholder />
    </section>
  );
}
