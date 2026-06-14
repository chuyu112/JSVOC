"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { getProject, updateProject, type Project, type ProjectPayload } from "@/lib/api/projects";
import { getLatestAccountPackage, generateAccountPackage, type AccountPackage } from "@/lib/api/generationRecords";
import { formatBeijingDate } from "@/lib/time";

const workflowNavGroups = [
  {
    title: "策划",
    items: [
      { label: "账号包装", path: "account-package" },
      { label: "执行计划", path: "execution-plan" },
    ],
  },
  {
    title: "生产",
    items: [
      { label: "选题生成", path: "topics" },
    ],
  },
  {
    title: "发布",
    items: [{ label: "内容发布", path: "publish" }],
  },
];

const platformOptions = ["抖音", "视频号", "快手", "小红书"];

const FIXED_INDUSTRY = "珠宝";
const FIXED_SUB_INDUSTRY = "翡翠";

export default function ProjectDetailClient({ projectId }: { projectId: number }) {
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState<Partial<ProjectPayload>>({});
  const [saving, setSaving] = useState(false);
  const [accountPackage, setAccountPackage] = useState<AccountPackage | null>(null);
  const [loadingAccountPackage, setLoadingAccountPackage] = useState(false);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const proj = await getProject(projectId);
        setProject(proj);
        setEditForm({ ...proj, industry: FIXED_INDUSTRY, sub_industry: FIXED_SUB_INDUSTRY });
      } catch {
        router.push("/projects");
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [projectId, router]);

  useEffect(() => {
    async function fetchAccountPackage() {
      setLoadingAccountPackage(true);
      try {
        const data = await getLatestAccountPackage(projectId);
        setAccountPackage(data);
      } catch {
        setAccountPackage(null);
      } finally {
        setLoadingAccountPackage(false);
      }
    }
    fetchAccountPackage();
  }, [projectId]);

  async function handleSave() {
    if (!project) return;
    setSaving(true);
    try {
      const updated = await updateProject(projectId, {
        ...editForm,
        industry: FIXED_INDUSTRY,
        sub_industry: FIXED_SUB_INDUSTRY,
      });
      setProject(updated);
      setEditing(false);
    } catch (err) {
      alert(err instanceof Error ? err.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function handleGenerateAccountPackage() {
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

  function updateEditForm<K extends keyof ProjectPayload>(key: K, value: ProjectPayload[K]) {
    setEditForm((prev) => ({ ...prev, [key]: value }));
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

  if (!project) return null;

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
          <p className="eyebrow">Project</p>
          <h1 className="text-[28px] md:text-[36px] font-bold leading-[1.15] tracking-[-0.02em] text-[#f5f5f5]">
            {project.project_name}
          </h1>
        </div>
        <Link href="/projects" className="btn btn-secondary">
          返回主页
        </Link>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6">
        {/* Left Column - Workflow */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
          className="space-y-4 lg:sticky lg:top-[84px] self-start"
        >
          <div className="glass rounded-[1rem] p-5">
            <h2 className="text-[14px] font-bold text-[#f5f5f5] mb-4">工作流</h2>
            <div className="space-y-4">
              {workflowNavGroups.map((group) => (
                <div key={group.title}>
                  <h3 className="text-[11px] text-[#9ca3af] mb-2 uppercase tracking-wider">{group.title}</h3>
                  <div className="grid grid-cols-1 gap-1.5">
                    {group.items.map((item) => (
                      <Link key={item.path} href={`/projects/${projectId}/${item.path}`} className="workflow-action">
                        {item.label}
                      </Link>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </motion.div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Project Info */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
            className="glass rounded-[1rem] p-5 md:p-6"
          >
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-[15px] font-bold text-[#f5f5f5]">项目信息</h2>
              {editing ? (
                <div className="flex gap-2">
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    className="text-[12px] px-3 py-1.5 rounded-md border transition-all hover:bg-white/[0.08] disabled:opacity-40"
                    style={{ borderColor: "rgba(255,255,255,0.1)", color: "#c0c0c0" }}
                  >
                    {saving ? "保存中..." : "保存"}
                  </button>
                  <button
                    onClick={() => {
                      setEditing(false);
                      setEditForm({ ...project, industry: FIXED_INDUSTRY, sub_industry: FIXED_SUB_INDUSTRY });
                    }}
                    className="text-[12px] px-3 py-1.5 rounded-md border transition-all hover:bg-white/[0.04]"
                    style={{ borderColor: "rgba(255,255,255,0.06)", color: "#7a8a82" }}
                  >
                    取消
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setEditing(true)}
                  className="text-[12px] px-3 py-1.5 rounded-md border transition-all hover:bg-white/[0.08]"
                  style={{ borderColor: "rgba(255,255,255,0.1)", color: "#c0c0c0" }}
                >
                  编辑
                </button>
              )}
            </div>

            {editing ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FieldInput label="人设名称" value={editForm.project_name || ""} onChange={(v) => updateEditForm("project_name", v)} />
                <FieldInput label="行业" value={FIXED_INDUSTRY} locked />
                <FieldInput label="细分行业" value={FIXED_SUB_INDUSTRY} locked />
                <FieldInput label="产品" value={editForm.product || ""} onChange={(v) => updateEditForm("product", v)} />
                <FieldInput label="阶段" value={editForm.current_stage || ""} onChange={(v) => updateEditForm("current_stage", v)} />
                <FieldTextarea label="个人介绍" value={editForm.personal_intro || ""} onChange={(v) => updateEditForm("personal_intro", v)} fullWidth />
                <FieldTextarea label="目标受众" value={editForm.target_audience || ""} onChange={(v) => updateEditForm("target_audience", v)} fullWidth />
                <div className="flex flex-col gap-1.5 md:col-span-2">
                  <label className="text-[12px] text-[#9ca3af]">运营平台</label>
                  <div className="flex flex-wrap gap-3">
                    {platformOptions.map((p) => (
                      <label key={p} className="flex items-center gap-1.5 text-[13px] text-[#b0b0b0] cursor-pointer">
                        <input
                          type="checkbox"
                          checked={(editForm.platforms || []).includes(p)}
                          onChange={(e) => {
                            const current = editForm.platforms || [];
                            if (e.target.checked) {
                              updateEditForm("platforms", [...current, p]);
                            } else {
                              updateEditForm("platforms", current.filter((x) => x !== p));
                            }
                          }}
                          className="rounded border-white/20 bg-white/5"
                        />
                        {p}
                      </label>
                    ))}
                  </div>
                </div>

                {/* Benchmark Accounts — Edit */}
                <div className="flex flex-col gap-1.5 md:col-span-2">
                  <label className="text-[12px] text-[#9ca3af]">对标账号</label>
                  <div className="space-y-2">
                    {(editForm.benchmark_accounts || []).map((item, index) => (
                      <div key={index} className="flex gap-2 items-center">
                        <input
                          className="input-glass w-24"
                          placeholder="平台"
                          value={item.platform}
                          onChange={(e) => {
                            const current = editForm.benchmark_accounts || [];
                            const updated = current.map((it, i) =>
                              i === index ? { ...it, platform: e.target.value } : it
                            );
                            updateEditForm("benchmark_accounts", updated);
                          }}
                        />
                        <input
                          className="input-glass w-32"
                          placeholder="账号名"
                          value={item.account_name}
                          onChange={(e) => {
                            const current = editForm.benchmark_accounts || [];
                            const updated = current.map((it, i) =>
                              i === index ? { ...it, account_name: e.target.value } : it
                            );
                            updateEditForm("benchmark_accounts", updated);
                          }}
                        />
                        <input
                          className="input-glass flex-1"
                          placeholder="备注（可选）"
                          value={item.notes}
                          onChange={(e) => {
                            const current = editForm.benchmark_accounts || [];
                            const updated = current.map((it, i) =>
                              i === index ? { ...it, notes: e.target.value } : it
                            );
                            updateEditForm("benchmark_accounts", updated);
                          }}
                        />
                        <button
                          onClick={() => {
                            const current = editForm.benchmark_accounts || [];
                            updateEditForm("benchmark_accounts", current.filter((_, i) => i !== index));
                          }}
                          className="text-[12px] px-2 py-1.5 rounded-md border transition-all hover:bg-white/[0.04] text-[#7a8a82]"
                          style={{ borderColor: "rgba(255,255,255,0.06)" }}
                        >
                          删除
                        </button>
                      </div>
                    ))}
                    <button
                      onClick={() => {
                        const current = editForm.benchmark_accounts || [];
                        updateEditForm("benchmark_accounts", [
                          ...current,
                          { platform: "", account_name: "", notes: "" },
                        ]);
                      }}
                      className="text-[12px] px-3 py-1.5 rounded-md border transition-all hover:bg-white/[0.08] text-[#9ca3af]"
                      style={{ borderColor: "rgba(255,255,255,0.08)" }}
                    >
                      + 添加对标账号
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <InfoField label="行业" value={FIXED_INDUSTRY} />
                <InfoField label="细分行业" value={FIXED_SUB_INDUSTRY} />
                <InfoField label="产品" value={project.product} />
                <InfoField label="阶段" value={project.current_stage} />
                <InfoField label="个人介绍" value={project.personal_intro || "—"} fullWidth />
                <InfoField label="目标受众" value={project.target_audience || "—"} fullWidth />
                <div className="md:col-span-2">
                  <span className="text-[12px] text-[#9ca3af] block mb-2">运营平台</span>
                  <div className="flex flex-wrap gap-2">
                    {project.platforms.map((p) => (
                      <span key={p} className="tag tag-success">
                        {p}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Benchmark Accounts — View */}
                {project.benchmark_accounts && project.benchmark_accounts.length > 0 && (
                  <div className="md:col-span-2">
                    <span className="text-[12px] text-[#9ca3af] block mb-2">对标账号</span>
                    <div className="space-y-2">
                      {project.benchmark_accounts.map((b, i) => (
                        <div
                          key={i}
                          className="flex items-center gap-2 text-[13px] p-2.5 rounded-md border"
                          style={{
                            borderColor: "rgba(255,255,255,0.06)",
                            background: "rgba(255,255,255,0.02)",
                          }}
                        >
                          <span className="text-[#7a8a82] shrink-0">{b.platform}</span>
                          <span className="text-[#b0b0b0] font-medium">{b.account_name}</span>
                          {b.notes && (
                            <span className="text-[#9ca3af] truncate">{b.notes}</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </motion.div>

          {/* Account Package */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
            className="glass rounded-[1rem] p-5 md:p-6"
          >
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-[15px] font-bold text-[#f5f5f5]">账号包装</h2>
              {accountPackage?.created_at && (
                <span className="text-[11px] text-[#9ca3af]">
                  {formatBeijingDate(accountPackage.created_at)}
                </span>
              )}
            </div>

            {loadingAccountPackage ? (
              <div className="animate-pulse space-y-3">
                <div className="h-4 bg-white/[0.04] rounded w-2/3" />
                <div className="h-4 bg-white/[0.04] rounded w-full" />
              </div>
            ) : accountPackage ? (
              <div className="space-y-4">
                <div>
                  <span className="text-[12px] text-[#9ca3af] block mb-1">账号定位</span>
                  <p className="text-[14px] text-[#f5f5f5] leading-relaxed">{accountPackage.account_positioning}</p>
                </div>
                <div>
                  <span className="text-[12px] text-[#9ca3af] block mb-1">人设</span>
                  <p className="text-[14px] text-[#f5f5f5] leading-relaxed">{accountPackage.persona}</p>
                </div>
                {accountPackage.account_names && accountPackage.account_names.length > 0 && (
                  <div>
                    <span className="text-[12px] text-[#9ca3af] block mb-1.5">推荐账号名</span>
                    <div className="flex flex-wrap gap-2">
                      {accountPackage.account_names.map((name, i) => (
                        <span
                          key={i}
                          className="text-[13px] px-2.5 py-1 rounded-md border"
                          style={{ borderColor: "rgba(255,255,255,0.08)", color: "#b0b0b0", background: "rgba(255,255,255,0.03)" }}
                        >
                          {name}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {accountPackage.bios && Object.keys(accountPackage.bios).length > 0 && (
                  <div>
                    <span className="text-[12px] text-[#9ca3af] block mb-1.5">平台简介</span>
                    <div className="space-y-1.5">
                      {Object.entries(accountPackage.bios).map(([platform, bio]) => (
                        <div key={platform} className="flex gap-2 text-[13px]">
                          <span className="text-[#7a8a82] shrink-0 w-12">{platform}</span>
                          <span className="text-[#b0b0b0]">{bio}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <div className="pt-3 border-t border-white/[0.06]">
                  <Link
                    href={`/projects/${projectId}/account-package`}
                    className="text-[12px] px-3 py-1.5 rounded-md border transition-all hover:bg-white/[0.08]"
                    style={{ borderColor: "rgba(255,255,255,0.1)", color: "#c0c0c0" }}
                  >
                    查看完整账号包装
                  </Link>
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-[13px] text-[#7a8a82] mb-4">暂无账号包装数据</p>
                <button
                  onClick={handleGenerateAccountPackage}
                  disabled={generating}
                  className="text-[13px] px-4 py-2 rounded-md border transition-all hover:bg-white/[0.08] disabled:opacity-40"
                  style={{ borderColor: "rgba(255,255,255,0.1)", color: "#c0c0c0" }}
                >
                  {generating ? "生成中..." : "生成账号包装"}
                </button>
              </div>
            )}
          </motion.div>
        </div>

        {/* Legacy workflow slot hidden after moving workflow to the left. */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.3 }}
          className="hidden"
        >
          <div className="glass rounded-[1rem] p-5">
            <h2 className="text-[14px] font-bold text-[#f5f5f5] mb-4">工作流</h2>
            <div className="space-y-4">
              {workflowNavGroups.map((group) => (
                <div key={group.title}>
                  <h3 className="text-[11px] text-[#9ca3af] mb-2 uppercase tracking-wider">{group.title}</h3>
                  <div className="grid grid-cols-1 gap-1.5">
                    {group.items.map((item) => (
                      <Link
                        key={item.path}
                        href={`/projects/${projectId}/${item.path}`}
                        className="w-full text-left px-3 py-2 rounded-[0.625rem] text-[13px] font-medium transition-all border hover:bg-white/[0.04] hover:border-white/[0.12] hover:text-[#f5f5f5]"
                        style={{
                          background: "rgba(255,255,255,0.02)",
                          borderColor: "rgba(255,255,255,0.06)",
                          color: "#7a8a82",
                        }}
                      >
                        {item.label}
                      </Link>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

function InfoField({ label, value, fullWidth }: { label: string; value: string; fullWidth?: boolean }) {
  return (
    <div className={fullWidth ? "md:col-span-2" : ""}>
      <span className="text-[12px] text-[#9ca3af] block mb-1">{label}</span>
      <p className="text-[14px] text-[#f5f5f5] leading-relaxed">{value}</p>
    </div>
  );
}

function FieldInput({
  label,
  value,
  onChange,
  locked,
}: {
  label: string;
  value: string;
  onChange?: (v: string) => void;
  locked?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-[12px] text-[#9ca3af]">{label}</label>
      <input
        className={"input-glass" + (locked ? " locked-field" : "")}
        value={value}
        disabled={locked}
        onChange={(e) => onChange?.(e.target.value)}
      />
    </div>
  );
}
function FieldTextarea({
  label,
  value,
  onChange,
  fullWidth,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  fullWidth?: boolean;
}) {
  return (
    <div className={`flex flex-col gap-1.5 ${fullWidth ? "md:col-span-2" : ""}`}>
      <label className="text-[12px] text-[#9ca3af]">{label}</label>
      <textarea className="input-glass min-h-[80px] resize-y" value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}
