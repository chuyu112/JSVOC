"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { createProject } from "@/lib/api/projects";

const platformOptions = [
  "抖音",
  "快手",
  "小红书",
  "视频号",
];

const stageOptions = [
  "冷启动期",
  "成长期",
  "成熟期",
  "衰退期",
];

const FIXED_INDUSTRY = "珠宝";
const FIXED_SUB_INDUSTRY = "翡翠";

export default function ProjectCreatePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    project_name: "",
    industry: FIXED_INDUSTRY,
    sub_industry: FIXED_SUB_INDUSTRY,
    product: "",
    personal_intro: "",
    target_audience: "",
    platforms: [] as string[],
    current_stage: "",
  });

  function togglePlatform(platform: string) {
    setForm((p) => ({
      ...p,
      platforms: p.platforms.includes(platform)
        ? p.platforms.filter((x) => x !== platform)
        : [...p.platforms, platform],
    }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (form.platforms.length === 0) {
      alert("请至少选择一个平台");
      return;
    }
    setLoading(true);
    try {
      await createProject({
        ...form,
        industry: FIXED_INDUSTRY,
        sub_industry: FIXED_SUB_INDUSTRY,
      });
      router.push("/projects");
    } catch {
      alert("创建失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page-section narrow">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="section-header"
      >
        <div>
          <p className="eyebrow">New Project</p>
          <h1 className="text-[28px] md:text-[36px] font-bold leading-[1.15] tracking-[-0.02em] text-[#f5f5f5]">
            新建人设
          </h1>
        </div>
      </motion.div>

      <motion.form
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
        onSubmit={handleSubmit}
        className="glass p-8 rounded-[1rem]"
      >
        <div className="form-grid">
          <div>
            <label className="block text-xs font-medium text-[#9ca3af] mb-1.5">
              人设名称 *
            </label>
            <input
              type="text"
              required
              value={form.project_name}
              onChange={(e) =>
                setForm((p) => ({ ...p, project_name: e.target.value }))
              }
              className="input-glass w-full"
              placeholder="输入人设名称"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-[#9ca3af] mb-1.5">
              行业 *
            </label>
            <input
              type="text"
              required
              value={FIXED_INDUSTRY}
              disabled
              className="input-glass locked-field w-full"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-[#9ca3af] mb-1.5">
              细分行业
            </label>
            <input
              type="text"
              value={FIXED_SUB_INDUSTRY}
              disabled
              className="input-glass locked-field w-full"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-[#9ca3af] mb-1.5">
              产品 *
            </label>
            <input
              type="text"
              required
              value={form.product}
              onChange={(e) =>
                setForm((p) => ({ ...p, product: e.target.value }))
              }
              className="input-glass w-full"
              placeholder="例如：手镯、吊坠"
            />
          </div>
        </div>

        <div className="mt-4">
          <label className="block text-xs font-medium text-[#9ca3af] mb-1.5">
            个人介绍
          </label>
          <textarea
            rows={3}
            value={form.personal_intro}
            onChange={(e) =>
              setForm((p) => ({ ...p, personal_intro: e.target.value }))
            }
            className="input-glass w-full resize-none"
            placeholder="简单介绍你的背景和定位"
          />
        </div>

        <div className="mt-4">
          <label className="block text-xs font-medium text-[#9ca3af] mb-1.5">
            目标受众
          </label>
          <textarea
            rows={3}
            value={form.target_audience}
            onChange={(e) =>
              setForm((p) => ({ ...p, target_audience: e.target.value }))
            }
            className="input-glass w-full resize-none"
            placeholder="描述你的目标用户画像"
          />
        </div>

        <div className="mt-4">
          <label className="block text-xs font-medium text-[#9ca3af] mb-2">
            运营平台 *
          </label>
          <div className="flex flex-wrap gap-2">
            {platformOptions.map((platform) => (
              <button
                key={platform}
                type="button"
                onClick={() => togglePlatform(platform)}
                className={`btn text-[13px] min-h-[36px] px-4 ${
                  form.platforms.includes(platform)
                    ? "btn-primary"
                    : "btn-secondary"
                }`}
              >
                {platform}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-4">
          <label className="block text-xs font-medium text-[#9ca3af] mb-2">
            当前阶段
          </label>
          <div className="flex flex-wrap gap-2">
            {stageOptions.map((stage) => (
              <button
                key={stage}
                type="button"
                onClick={() => setForm((p) => ({ ...p, current_stage: stage }))}
                className={`btn text-[13px] min-h-[36px] px-4 ${
                  form.current_stage === stage ? "btn-primary" : "btn-secondary"
                }`}
              >
                {stage}
              </button>
            ))}
          </div>
        </div>

        <div className="flex justify-between items-center mt-8">
          <button
            type="button"
            onClick={() => router.back()}
            className="btn btn-ghost"
          >
            取消
          </button>
          <button type="submit" disabled={loading} className="btn btn-primary">
            {loading ? "创建中..." : "创建人设"}
          </button>
        </div>
      </motion.form>
    </section>
  );
}
