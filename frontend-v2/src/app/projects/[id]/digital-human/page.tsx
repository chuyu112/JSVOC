"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { getProject, type Project } from "@/lib/api/projects";
import { listProjectTopics, type Topic } from "@/lib/api/topics";
import {
  listAvatars,
  listVoices,
  cloneVoice,
  generateVideo,
  type DigitalHumanAvatar,
  type DigitalHumanVoice,
} from "@/lib/api/digitalHuman";
import ProjectModuleTitle from "@/components/ProjectModuleTitle";

type Step = 1 | 2 | 3 | 4;

export default function ProjectDigitalHumanPage() {
  const router = useRouter();
  const params = useParams();
  const projectId = Number(params.id);

  const [project, setProject] = useState<Project | null>(null);
  const [step, setStep] = useState<Step>(1);

  // Step 1: Scripts
  const [topics, setTopics] = useState<Topic[]>([]);
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null);

  // Step 2: Voices
  const [voices, setVoices] = useState<DigitalHumanVoice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState<DigitalHumanVoice | null>(null);
  const [cloning, setCloning] = useState(false);

  // Step 3: Avatars
  const [avatars, setAvatars] = useState<DigitalHumanAvatar[]>([]);
  const [selectedAvatar, setSelectedAvatar] = useState<DigitalHumanAvatar | null>(null);

  // Step 4: Config
  const [withSubtitle, setWithSubtitle] = useState(true);
  const [withBgm, setWithBgm] = useState(false);
  const [resolution, setResolution] = useState("1080p");
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<{ task_id: number; video_id: number } | null>(null);

  useEffect(() => {
    getProject(projectId)
      .then(setProject)
      .catch(() => router.push("/projects"));
  }, [projectId, router]);

  useEffect(() => {
    listProjectTopics(projectId).then(setTopics).catch(() => setTopics([]));
    listVoices().then(setVoices).catch(() => setVoices([]));
    listAvatars().then(setAvatars).catch(() => setAvatars([]));
  }, [projectId]);

  function canProceed() {
    if (step === 1) return selectedTopic !== null;
    if (step === 2) return selectedVoice !== null;
    if (step === 3) return selectedAvatar !== null;
    return true;
  }

  async function handleCloneVoice() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "audio/*";
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;
      const name = prompt("给这个克隆声音起个名字：");
      if (!name) return;
      setCloning(true);
      try {
        const formData = new FormData();
        formData.append("audio", file);
        formData.append("name", name);
        const voice = await cloneVoice(formData);
        setVoices((prev) => [...prev, voice]);
        setSelectedVoice(voice);
      } catch (err) {
        alert(err instanceof Error ? err.message : "克隆失败");
      } finally {
        setCloning(false);
      }
    };
    input.click();
  }

  async function handleGenerate() {
    if (!selectedTopic || !selectedVoice || !selectedAvatar) return;
    setGenerating(true);
    try {
      const resp = await generateVideo({
        project_id: projectId,
        script_id: selectedTopic.id,
        voice_id: selectedVoice.id,
        avatar_id: selectedAvatar.id,
        with_subtitle: withSubtitle,
        with_bgm: withBgm,
        resolution,
      });
      setResult({ task_id: resp.task_id, video_id: resp.video_id });
      setStep(4);
    } catch (err) {
      alert(err instanceof Error ? err.message : "生成失败");
    } finally {
      setGenerating(false);
    }
  }

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
          <ProjectModuleTitle projectName={project?.project_name} moduleName="数字人视频生成" />
        </div>
        <div className="section-header-actions">
          <Link href={`/projects/${projectId}`} className="project-return-btn">
            返回人设
          </Link>
        </div>
      </motion.div>

      {/* Stepper */}
      <div className="flex items-center gap-2 mb-8">
        {[1, 2, 3, 4].map((s) => (
          <div key={s} className="flex items-center gap-2">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                s <= step
                  ? "bg-[#5a9b82] text-white"
                  : "bg-[rgba(255,255,255,0.08)] text-[#7a8a82]"
              }`}
            >
              {s}
            </div>
            <span className={`text-sm ${s <= step ? "text-[#f5f5f5]" : "text-[#7a8a82]"}`}>
              {s === 1 && "选择文案"}
              {s === 2 && "选择声音"}
              {s === 3 && "选择形象"}
              {s === 4 && "生成视频"}
            </span>
            {s < 4 && <div className="w-8 h-px bg-[rgba(255,255,255,0.1)]" />}
          </div>
        ))}
      </div>

      {/* Step 1: Select Script */}
      {step === 1 && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass p-6 rounded-[1rem]"
        >
          <h3 className="text-lg font-bold text-[#f5f5f5] mb-4">选择文案</h3>
          <p className="text-sm text-[#9ca3af] mb-4">从项目选题中选择一个用于数字人口播</p>
          <div className="grid gap-3">
            {topics.length === 0 && (
              <div className="text-[#9ca3af] text-sm text-center py-8">
                暂无文案，请先
                <Link href={`/projects/${projectId}/topics`} className="text-[#5a9b82] mx-1">
                  生成选题
                </Link>
              </div>
            )}
            {topics.map((topic) => (
              <button
                key={topic.id}
                onClick={() => setSelectedTopic(topic)}
                className={`text-left p-4 rounded-[0.75rem] border transition-all ${
                  selectedTopic?.id === topic.id
                    ? "border-[#5a9b82] bg-[rgba(90,155,130,0.1)]"
                    : "border-[rgba(255,255,255,0.06)] hover:border-[rgba(255,255,255,0.12)]"
                }`}
              >
                <div className="font-medium text-[#f5f5f5]">{topic.title}</div>
                {topic.topic_data?.hook && (
                  <div className="text-sm text-[#9ca3af] mt-1 line-clamp-2">{topic.topic_data.hook}</div>
                )}
              </button>
            ))}
          </div>
        </motion.div>
      )}

      {/* Step 2: Select Voice */}
      {step === 2 && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass p-6 rounded-[1rem]"
        >
          <h3 className="text-lg font-bold text-[#f5f5f5] mb-4">选择声音</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            {voices.map((voice) => (
              <button
                key={voice.id}
                onClick={() => setSelectedVoice(voice)}
                className={`p-4 rounded-[0.75rem] border text-center transition-all ${
                  selectedVoice?.id === voice.id
                    ? "border-[#5a9b82] bg-[rgba(90,155,130,0.1)]"
                    : "border-[rgba(255,255,255,0.06)] hover:border-[rgba(255,255,255,0.12)]"
                }`}
              >
                <div className="text-2xl mb-2">{voice.gender === "female" ? "👩" : "👨"}</div>
                <div className="text-sm font-medium text-[#f5f5f5]">{voice.name}</div>
                <div className="text-xs text-[#9ca3af]">{voice.voice_type === "preset" ? "预设" : "克隆"}</div>
              </button>
            ))}
          </div>
          <button
            onClick={handleCloneVoice}
            disabled={cloning}
            className="btn btn-outline w-full"
          >
            {cloning ? "克隆中..." : "+ 上传3秒样本克隆新声音（CozyVoice）"}
          </button>
        </motion.div>
      )}

      {/* Step 3: Select Avatar */}
      {step === 3 && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass p-6 rounded-[1rem]"
        >
          <h3 className="text-lg font-bold text-[#f5f5f5] mb-4">选择数字人形象</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {avatars.map((avatar) => (
              <button
                key={avatar.id}
                onClick={() => setSelectedAvatar(avatar)}
                className={`p-4 rounded-[0.75rem] border text-center transition-all ${
                  selectedAvatar?.id === avatar.id
                    ? "border-[#5a9b82] bg-[rgba(90,155,130,0.1)]"
                    : "border-[rgba(255,255,255,0.06)] hover:border-[rgba(255,255,255,0.12)]"
                }`}
              >
                {avatar.thumbnail_url ? (
                  <img
                    src={avatar.thumbnail_url}
                    alt={avatar.name}
                    className="w-16 h-16 rounded-full mx-auto mb-2 object-cover"
                  />
                ) : (
                  <div className="w-16 h-16 rounded-full mx-auto mb-2 bg-[rgba(255,255,255,0.06)] flex items-center justify-center text-2xl">
                    {avatar.gender === "female" ? "👩" : "👨"}
                  </div>
                )}
                <div className="text-sm font-medium text-[#f5f5f5]">{avatar.name}</div>
              </button>
            ))}
          </div>
          {avatars.length === 0 && (
            <div className="text-[#9ca3af] text-sm text-center py-8">
              暂无预设形象，请联系管理员添加
            </div>
          )}
        </motion.div>
      )}

      {/* Step 4: Generate */}
      {step === 4 && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass p-6 rounded-[1rem]"
        >
          <h3 className="text-lg font-bold text-[#f5f5f5] mb-4">生成配置</h3>

          <div className="space-y-4 mb-6">
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={withSubtitle}
                onChange={(e) => setWithSubtitle(e.target.checked)}
                className="w-4 h-4 accent-[#5a9b82]"
              />
              <span className="text-sm text-[#f5f5f5]">添加字幕（FFmpeg 合成）</span>
            </div>
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={withBgm}
                onChange={(e) => setWithBgm(e.target.checked)}
                className="w-4 h-4 accent-[#5a9b82]"
              />
              <span className="text-sm text-[#f5f5f5]">添加 BGM</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm text-[#f5f5f5]">分辨率：</span>
              <select
                value={resolution}
                onChange={(e) => setResolution(e.target.value)}
                className="bg-[rgba(255,255,255,0.06)] border border-[rgba(255,255,255,0.1)] rounded-lg px-3 py-1.5 text-sm text-[#f5f5f5]"
              >
                <option value="720p">720p</option>
                <option value="1080p">1080p</option>
              </select>
            </div>
          </div>

          <div className="border-t border-[rgba(255,255,255,0.06)] pt-4 mb-4">
            <h4 className="text-sm font-bold text-[#f5f5f5] mb-2">生成概览</h4>
            <div className="text-sm text-[#9ca3af] space-y-1">
              <div>文案：{selectedTopic?.title}</div>
              <div>声音：{selectedVoice?.name}</div>
              <div>形象：{selectedAvatar?.name}</div>
              <div className="text-[#5a9b82]">预估消耗：35 积分</div>
            </div>
          </div>

          {result ? (
            <div className="text-center py-4 space-y-3">
              <div className="text-[#5a9b82] font-bold">✅ 任务已提交</div>
              <div className="text-sm text-[#9ca3af]">
                任务 ID: {result.task_id} | 视频 ID: {result.video_id}
              </div>
              <div className="flex gap-3 justify-center">
                <Link
                  href={`/projects/${projectId}/publish?videoId=${result.video_id}`}
                  className="btn btn-primary"
                >
                  🚀 一键分发到多平台
                </Link>
                <Link href="/history" className="btn btn-outline">
                  查看生成记录
                </Link>
              </div>
              <p className="text-xs text-[#7a8a82]">
                支持：抖音、视频号、B站、小红书、快手
              </p>
            </div>
          ) : (
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="btn btn-primary w-full"
            >
              {generating ? "生成中..." : "开始生成数字人视频"}
            </button>
          )}
        </motion.div>
      )}

      {/* Navigation */}
      <div className="flex justify-between mt-6">
        <button
          onClick={() => setStep((s) => Math.max(1, s - 1) as Step)}
          disabled={step === 1}
          className="btn btn-outline disabled:opacity-30"
        >
          上一步
        </button>
        <button
          onClick={() => setStep((s) => Math.min(4, s + 1) as Step)}
          disabled={!canProceed() || step >= 4}
          className="btn btn-primary disabled:opacity-30"
        >
          {step === 3 ? "下一步：生成配置" : "下一步"}
        </button>
      </div>
    </section>
  );
}
