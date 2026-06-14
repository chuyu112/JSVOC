"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import {
  activateLLMChannel,
  createLLMChannel,
  deleteLLMChannel,
  listLLMChannels,
  testLLMChannel,
  updateLLMChannel,
  type LLMChannel,
  type LLMChannelPayload,
} from "@/lib/api/llmChannels";

const themes = [
  { key: "yang", label: "阳绿", dot: "#5a9b82", desc: "鲜亮明快，生机勃勃" },
  { key: "imperial", label: "帝王绿", dot: "#3a6b5a", desc: "深沉华贵，顶级翡翠" },
  { key: "apple", label: "苹果绿", dot: "#6aaa92", desc: "清新自然，水润透亮" },
  { key: "lavender", label: "紫罗兰", dot: "#8a7ab0", desc: "浪漫神秘，春色翡翠" },
  { key: "yellow", label: "黄翡", dot: "#b8985a", desc: "温暖富贵，金玉满堂" },
  { key: "red", label: "红翡", dot: "#b86868", desc: "热烈奔放，鸿运当头" },
  { key: "black", label: "墨翠", dot: "#b8a060", desc: "黑金相映，低调奢华" },
];

type ProviderOption = {
  value: string;
  label: string;
  purposes: string[];
  defaultBaseUrl?: string;
  defaultModel?: string;
  defaultModelByPurpose?: Record<string, string>;
  modelOptionsByPurpose?: Record<string, string[]>;
};

const kakayiduoChatModels = ["gpt-5.5", "gpt-5.4-mini"];
const kakayiduoBaseUrl = "http://43.173.105.8:8080/v1";

const providerOptions: ProviderOption[] = [
  {
    value: "kakayiduo",
    label: "kakayiduo",
    purposes: ["chat", "image"],
    defaultBaseUrl: kakayiduoBaseUrl,
    defaultModelByPurpose: { chat: "gpt-5.5", image: "gpt-image-2" },
    modelOptionsByPurpose: { chat: kakayiduoChatModels },
  },
  { value: "moyu_image", label: "moyu-image", purposes: ["image"], defaultModel: "gpt-image-2" },
  { value: "seedance_video", label: "seedance-video", purposes: ["video"], defaultModel: "seedance-2.0" },
  { value: "dianli", label: "点力视频 (Dianli)", purposes: ["video"], defaultModel: "ant-2-text-2-video", defaultBaseUrl: "https://www.dianliciyuan.com" },
  { value: "mock", label: "Mock", purposes: ["chat"] },
  { value: "openai_compatible", label: "OpenAI Compatible", purposes: ["chat", "image"] },
  { value: "dataeye", label: "DataEye", purposes: ["chat"] },
  { value: "moyu", label: "Moyu Chat", purposes: ["chat"] },
  { value: "anthropic_compatible", label: "Anthropic Compatible", purposes: ["chat"] },
  { value: "seedance", label: "Seedance Legacy", purposes: ["video"], defaultModel: "seedance-2.0" },
];

const channelPurposes = [
  { value: "chat", label: "聊天" },
  { value: "image", label: "生图" },
  { value: "video", label: "生视频" },
];

const emptyChannelForm: LLMChannelPayload = {
  name: "",
  purpose: "chat",
  provider: "kakayiduo",
  base_url: kakayiduoBaseUrl,
  api_key: "",
  model: "gpt-5.5",
  is_active: false,
};

export default function SettingsPage() {
  const router = useRouter();
  const auth = useAuth();
  const [saved, setSaved] = useState("yang");
  const [current, setCurrent] = useState("yang");
  const [savedFlag, setSavedFlag] = useState(false);
  const [channels, setChannels] = useState<LLMChannel[]>([]);
  const [channelForm, setChannelForm] = useState<LLMChannelPayload>(emptyChannelForm);
  const [editingChannelId, setEditingChannelId] = useState<number | null>(null);
  const [channelsLoading, setChannelsLoading] = useState(false);
  const [channelSaving, setChannelSaving] = useState(false);
  const [channelError, setChannelError] = useState("");
  const [testMessages, setTestMessages] = useState<Record<number, string>>({});
  const [testingChannelId, setTestingChannelId] = useState<number | null>(null);
  const isAdmin = Boolean(auth.user?.is_admin);

  useEffect(() => {
    const stored = localStorage.getItem("jade-theme");
    const initial = stored && themes.some((t) => t.key === stored) ? stored : "yang";
    const frame = requestAnimationFrame(() => {
      setSaved(initial);
      setCurrent(initial);
    });
    return () => cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    if (!isAdmin) return;
    void loadChannels();
  }, [isAdmin]);

  async function loadChannels() {
    setChannelsLoading(true);
    setChannelError("");
    try {
      const data = await listLLMChannels();
      setChannels(data);
    } catch (error) {
      setChannelError(error instanceof Error ? error.message : "模型渠道加载失败");
    } finally {
      setChannelsLoading(false);
    }
  }

  function select(key: string) {
    setCurrent(key);
  }

  function handleSave() {
    localStorage.setItem("jade-theme", current);
    document.documentElement.dataset.theme = current === "yang" ? "" : current;
    setSaved(current);
    setSavedFlag(true);

    const params = new URLSearchParams(window.location.search);
    const returnTo = params.get("returnTo");
    if (returnTo && returnTo.startsWith("/") && !returnTo.startsWith("//") && returnTo !== "/settings") {
      router.push(returnTo);
      return;
    }

    if (window.history.length > 1) {
      router.back();
      return;
    }

    router.push("/projects");
  }

  async function handleLogout() {
    await auth.logout();
    router.push("/login");
  }

  function resetChannelForm() {
    setEditingChannelId(null);
    setChannelForm(emptyChannelForm);
    setChannelError("");
  }

  function editChannel(channel: LLMChannel) {
    setEditingChannelId(channel.id);
    setChannelForm({
      name: channel.name,
      purpose: channel.purpose,
      provider: normalizeProviderValue(channel.provider),
      base_url: channel.base_url,
      api_key: "",
      model: normalizeChannelModel(channel.provider, channel.purpose, channel.model),
      is_active: channel.is_active,
    });
    setChannelError("");
  }

  function changeChannelPurpose(purpose: string) {
    const next = defaultProviderForPurpose(purpose);
    setChannelForm({
      ...channelForm,
      purpose,
      provider: next.value,
      base_url: next.defaultBaseUrl || "",
      model: defaultModelForOption(next, purpose),
    });
  }

  function purposeLabel(value: string) {
    return channelPurposes.find((item) => item.value === value)?.label || value;
  }

  function normalizeProviderValue(value: string) {
    const normalized = value.trim().toLowerCase().replaceAll("-", "_");
    if (
      [
        "kakayiduo_chat",
        "kakayiduo_image",
        "kakayioduo",
        "kakayioduo_image",
        "kakayuiduo",
        "kakayuiduo_image",
      ].includes(normalized)
    ) {
      return "kakayiduo";
    }
    return normalized;
  }

  function normalizeChannelModel(provider: string, purpose: string, model: string) {
    const normalizedProvider = normalizeProviderValue(provider);
    if (normalizedProvider === "kakayiduo" && purpose === "chat") {
      if (model === "gpt5.5") return "gpt-5.5";
      if (model === "gpt5.4-mini") return "gpt-5.4-mini";
    }
    return model;
  }

  function providerOptionsForPurpose(purpose: string) {
    return providerOptions.filter((item) => item.purposes.includes(purpose));
  }

  function defaultProviderForPurpose(purpose: string) {
    return providerOptionsForPurpose(purpose)[0] || providerOptions[0];
  }

  function providerLabel(value: string) {
    const normalized = normalizeProviderValue(value);
    return providerOptions.find((item) => item.value === normalized)?.label || value;
  }

  function defaultModelForOption(option: ProviderOption, purpose: string) {
    return option.defaultModelByPurpose?.[purpose] || option.defaultModel || "";
  }

  function modelOptionsForChannel() {
    const option = providerOptions.find((item) => item.value === normalizeProviderValue(channelForm.provider));
    return option?.modelOptionsByPurpose?.[channelForm.purpose] || [];
  }

  function changeChannelProvider(provider: string) {
    const normalized = normalizeProviderValue(provider);
    const option = providerOptions.find((item) => item.value === normalized);
    setChannelForm({
      ...channelForm,
      provider: normalized,
      base_url: option?.defaultBaseUrl || channelForm.base_url,
      model: option ? defaultModelForOption(option, channelForm.purpose) : channelForm.model,
    });
  }

  async function saveChannel() {
    setChannelSaving(true);
    setChannelError("");
    try {
      if (editingChannelId) {
        await updateLLMChannel(editingChannelId, channelForm);
      } else {
        await createLLMChannel(channelForm);
      }
      resetChannelForm();
      await loadChannels();
    } catch (error) {
      setChannelError(error instanceof Error ? error.message : "模型渠道保存失败");
    } finally {
      setChannelSaving(false);
    }
  }

  async function activateChannel(id: number) {
    setChannelError("");
    try {
      await activateLLMChannel(id);
      await loadChannels();
    } catch (error) {
      setChannelError(error instanceof Error ? error.message : "模型渠道启用失败");
    }
  }

  async function selectActiveChannel(purpose: string, channelId: string) {
    const id = Number(channelId);
    if (!id) return;

    setChannelError("");
    try {
      await activateLLMChannel(id);
      await loadChannels();
    } catch (error) {
      setChannelError(error instanceof Error ? error.message : `${purposeLabel(purpose)}渠道选择失败`);
    }
  }

  async function runChannelTest(id: number) {
    setTestingChannelId(id);
    setChannelError("");
    try {
      const result = await testLLMChannel(id);
      setTestMessages((currentMessages) => ({
        ...currentMessages,
        [id]: result.success
          ? `测试成功：${result.provider} / ${result.model}`
          : `测试失败：${result.error || result.message}`,
      }));
    } catch (error) {
      setTestMessages((currentMessages) => ({
        ...currentMessages,
        [id]: error instanceof Error ? `测试失败：${error.message}` : "测试失败",
      }));
    } finally {
      setTestingChannelId(null);
    }
  }

  async function removeChannel(id: number) {
    if (!window.confirm("确定删除这个模型渠道吗？")) return;
    setChannelError("");
    try {
      await deleteLLMChannel(id);
      if (editingChannelId === id) resetChannelForm();
      await loadChannels();
    } catch (error) {
      setChannelError(error instanceof Error ? error.message : "模型渠道删除失败");
    }
  }

  return (
    <section className="page-section">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="section-header"
      >
        <div>
          <p className="eyebrow">Preferences</p>
          <h1 className="text-[28px] md:text-[36px] font-bold leading-[1.15] tracking-[-0.02em] text-[#f5f5f5]">
            用户设置
          </h1>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
        className="glass rounded-[1rem] p-6 md:p-8 max-w-[720px]"
      >
        <h2 className="text-[18px] font-[680] text-[#f5f5f5] mb-6">外观主题</h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {themes.map((t) => (
            <button
              key={t.key}
              onClick={() => select(t.key)}
              className={`flex items-center gap-3 w-full p-3 rounded-[0.75rem] border text-left transition-all duration-200 ${
                current === t.key
                  ? "border-[var(--jade-primary)] bg-[rgba(90,155,130,0.1)]"
                  : "border-[rgba(255,255,255,0.06)] bg-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.06)]"
              }`}
            >
              <span
                className="shrink-0 block w-8 h-8 rounded-full border-2"
                style={{
                  background: t.dot,
                  borderColor: current === t.key ? "#ffffff" : "rgba(255,255,255,0.15)",
                  boxShadow: current === t.key ? `0 0 12px ${t.dot}` : "none",
                }}
              />
              <div className="min-w-0">
                <div className="text-[14px] font-[620] text-[#f5f5f5]">{t.label}</div>
                <div className="text-[12px] text-[#6b7280] mt-0.5">{t.desc}</div>
              </div>
              {current === t.key && (
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="ml-auto shrink-0"
                  style={{ color: "var(--jade-primary)" }}
                >
                  <path d="M20 6L9 17l-5-5" />
                </svg>
              )}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-3 mt-6">
          <button
            onClick={handleSave}
            disabled={current === saved}
            className="metal-btn metal-btn-primary text-sm disabled:opacity-40 disabled:cursor-not-allowed"
          >
            保存主题
          </button>
          {savedFlag && (
            <span className="text-[13px] text-[#7fdc92]">已保存</span>
          )}
        </div>

        <div className="mt-8 border-t border-[rgba(255,255,255,0.06)] pt-6">
          <h2 className="text-[18px] font-[680] text-[#f5f5f5] mb-3">账号操作</h2>
          <button
            type="button"
            onClick={handleLogout}
            className="metal-btn text-sm"
          >
            退出登录
          </button>
        </div>
      </motion.div>

      {isAdmin && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.16 }}
          className="glass rounded-[1rem] p-6 md:p-8 max-w-[980px] mt-6"
        >
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-6">
            <div>
              <p className="eyebrow">Admin</p>
              <h2 className="text-[20px] font-[720] text-[#f5f5f5]">模型渠道</h2>
            </div>
            <button
              type="button"
              onClick={loadChannels}
              className="metal-btn text-sm w-fit"
              disabled={channelsLoading}
            >
              {channelsLoading ? "刷新中" : "刷新"}
            </button>
          </div>

          {channelError && (
            <div className="mb-4 rounded-[0.5rem] border border-red-400/25 bg-red-500/10 px-3 py-2 text-[13px] text-red-200">
              {channelError}
            </div>
          )}

          <div className="mb-5 grid grid-cols-1 md:grid-cols-3 gap-3">
            {channelPurposes.map((purpose) => {
              const purposeChannels = channels.filter((channel) => channel.purpose === purpose.value);
              const activeChannel = purposeChannels.find((channel) => channel.is_active);

              return (
                <label
                  key={purpose.value}
                  className="block rounded-[0.75rem] border border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.03)] p-3"
                >
                  <span className="block text-[12px] text-[#9ca3af] mb-1">
                    当前{purpose.label}渠道
                  </span>
                  <select
                    value={activeChannel?.id ?? ""}
                    onChange={(event) => selectActiveChannel(purpose.value, event.target.value)}
                    disabled={purposeChannels.length === 0 || channelsLoading}
                    className="w-full rounded-[0.5rem] border border-[rgba(255,255,255,0.08)] bg-[#101613] px-3 py-2 text-sm text-[#f5f5f5] outline-none focus:border-[var(--jade-primary)] disabled:opacity-50"
                  >
                    <option value="" disabled>
                      {purposeChannels.length > 0 ? "请选择渠道" : "暂无渠道"}
                    </option>
                    {purposeChannels.map((channel) => (
                      <option key={channel.id} value={channel.id}>
                        {channel.name} / {providerLabel(channel.provider)} / {channel.model}
                      </option>
                    ))}
                  </select>
                  <span className="mt-2 block truncate text-[11px] text-[#7a8a82]">
                    {activeChannel
                      ? `${providerLabel(activeChannel.provider)} / ${activeChannel.model}`
                      : "未启用时使用环境变量配置"}
                  </span>
                </label>
              );
            })}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.2fr] gap-5">
            <div className="rounded-[0.75rem] border border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.03)] p-4">
              <h3 className="text-[15px] font-[680] text-[#f5f5f5] mb-4">
                {editingChannelId ? "编辑渠道" : "新增渠道"}
              </h3>
              <div className="space-y-3">
                <label className="block">
                  <span className="block text-[12px] text-[#9ca3af] mb-1">名称</span>
                  <input
                    value={channelForm.name}
                    onChange={(event) => setChannelForm({ ...channelForm, name: event.target.value })}
                    className="w-full rounded-[0.5rem] border border-[rgba(255,255,255,0.08)] bg-[rgba(0,0,0,0.22)] px-3 py-2 text-sm text-[#f5f5f5] outline-none focus:border-[var(--jade-primary)]"
                    placeholder="例如：DeepSeek 主渠道"
                  />
                </label>

                <label className="block">
                  <span className="block text-[12px] text-[#9ca3af] mb-1">用途</span>
                  <select
                    value={channelForm.purpose}
                    onChange={(event) => changeChannelPurpose(event.target.value)}
                    className="w-full rounded-[0.5rem] border border-[rgba(255,255,255,0.08)] bg-[#101613] px-3 py-2 text-sm text-[#f5f5f5] outline-none focus:border-[var(--jade-primary)]"
                  >
                    {channelPurposes.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block">
                  <span className="block text-[12px] text-[#9ca3af] mb-1">Provider</span>
                  <select
                    value={channelForm.provider}
                    onChange={(event) => changeChannelProvider(event.target.value)}
                    className="w-full rounded-[0.5rem] border border-[rgba(255,255,255,0.08)] bg-[#101613] px-3 py-2 text-sm text-[#f5f5f5] outline-none focus:border-[var(--jade-primary)]"
                  >
                    {providerOptionsForPurpose(channelForm.purpose).map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                    {!providerOptionsForPurpose(channelForm.purpose).some(
                      (item) => item.value === normalizeProviderValue(channelForm.provider),
                    ) && (
                      <option value={normalizeProviderValue(channelForm.provider)}>
                        {providerLabel(channelForm.provider)}
                      </option>
                    )}
                  </select>
                </label>

                <label className="block">
                  <span className="block text-[12px] text-[#9ca3af] mb-1">Base URL</span>
                  <input
                    value={channelForm.base_url}
                    onChange={(event) => setChannelForm({ ...channelForm, base_url: event.target.value })}
                    className="w-full rounded-[0.5rem] border border-[rgba(255,255,255,0.08)] bg-[rgba(0,0,0,0.22)] px-3 py-2 text-sm text-[#f5f5f5] outline-none focus:border-[var(--jade-primary)]"
                    placeholder="https://example.com/v1"
                  />
                </label>

                <label className="block">
                  <span className="block text-[12px] text-[#9ca3af] mb-1">API Key</span>
                  <input
                    value={channelForm.api_key || ""}
                    onChange={(event) => setChannelForm({ ...channelForm, api_key: event.target.value })}
                    className="w-full rounded-[0.5rem] border border-[rgba(255,255,255,0.08)] bg-[rgba(0,0,0,0.22)] px-3 py-2 text-sm text-[#f5f5f5] outline-none focus:border-[var(--jade-primary)]"
                    placeholder={editingChannelId ? "留空则保留原密钥" : "可留空"}
                    type="password"
                    autoComplete="new-password"
                  />
                </label>

                <label className="block">
                  <span className="block text-[12px] text-[#9ca3af] mb-1">模型名</span>
                  {modelOptionsForChannel().length > 0 ? (
                    <select
                      value={channelForm.model}
                      onChange={(event) => setChannelForm({ ...channelForm, model: event.target.value })}
                      className="w-full rounded-[0.5rem] border border-[rgba(255,255,255,0.08)] bg-[#101613] px-3 py-2 text-sm text-[#f5f5f5] outline-none focus:border-[var(--jade-primary)]"
                    >
                      {modelOptionsForChannel().map((model) => (
                        <option key={model} value={model}>
                          {model}
                        </option>
                      ))}
                      {!modelOptionsForChannel().includes(channelForm.model) && channelForm.model && (
                        <option value={channelForm.model}>{channelForm.model}</option>
                      )}
                    </select>
                  ) : (
                    <input
                      value={channelForm.model}
                      onChange={(event) => setChannelForm({ ...channelForm, model: event.target.value })}
                      className="w-full rounded-[0.5rem] border border-[rgba(255,255,255,0.08)] bg-[rgba(0,0,0,0.22)] px-3 py-2 text-sm text-[#f5f5f5] outline-none focus:border-[var(--jade-primary)]"
                      placeholder="deepseek-v4-flash"
                    />
                  )}
                </label>

                <label className="flex items-center gap-2 text-[13px] text-[#d0ddd6]">
                  <input
                    type="checkbox"
                    checked={Boolean(channelForm.is_active)}
                    onChange={(event) => setChannelForm({ ...channelForm, is_active: event.target.checked })}
                  />
                  保存后立即启用
                </label>

                <div className="flex gap-2 pt-2">
                  <button
                    type="button"
                    onClick={saveChannel}
                    disabled={channelSaving || !channelForm.name.trim() || !channelForm.model.trim()}
                    className="metal-btn metal-btn-primary text-sm disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {channelSaving ? "保存中" : "保存渠道"}
                  </button>
                  {editingChannelId && (
                    <button type="button" onClick={resetChannelForm} className="metal-btn text-sm">
                      取消
                    </button>
                  )}
                </div>
              </div>
            </div>

            <div className="space-y-3">
              {channels.length === 0 && (
                <div className="rounded-[0.75rem] border border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.03)] p-4 text-[13px] text-[#9ca3af]">
                  暂无模型渠道。
                </div>
              )}

              {channels.map((channel) => (
                <div
                  key={channel.id}
                  className="rounded-[0.75rem] border border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.03)] p-4"
                >
                  <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-[15px] font-[680] text-[#f5f5f5]">{channel.name}</h3>
                        <span className="rounded-full bg-[rgba(255,255,255,0.08)] px-2 py-0.5 text-[11px] text-[#d0ddd6]">
                          {purposeLabel(channel.purpose)}
                        </span>
                        {channel.is_active && (
                          <span className="rounded-full bg-[rgba(127,220,146,0.14)] px-2 py-0.5 text-[11px] text-[#7fdc92]">
                            当前启用
                          </span>
                        )}
                        {channel.has_api_key && (
                          <span className="rounded-full bg-[rgba(255,255,255,0.08)] px-2 py-0.5 text-[11px] text-[#d0ddd6]">
                            Key 已保存
                          </span>
                        )}
                      </div>
                      <div className="mt-2 space-y-1 text-[12px] text-[#9ca3af]">
                        <div>用途：{purposeLabel(channel.purpose)}</div>
                        <div>Provider：{providerLabel(channel.provider)}</div>
                        <div className="break-all">Base URL：{channel.base_url || "-"}</div>
                        <div>模型：{channel.model}</div>
                      </div>
                      {testMessages[channel.id] && (
                        <div className="mt-2 text-[12px] text-[#d0ddd6]">{testMessages[channel.id]}</div>
                      )}
                    </div>

                    <div className="flex flex-wrap gap-2">
                      {!channel.is_active && (
                        <button type="button" onClick={() => activateChannel(channel.id)} className="metal-btn text-xs">
                          设为当前
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => runChannelTest(channel.id)}
                        className="metal-btn text-xs"
                        disabled={testingChannelId === channel.id}
                      >
                        {testingChannelId === channel.id ? "测试中" : "测试"}
                      </button>
                      <button type="button" onClick={() => editChannel(channel)} className="metal-btn text-xs">
                        编辑
                      </button>
                      <button type="button" onClick={() => removeChannel(channel.id)} className="metal-btn text-xs">
                        删除
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      )}
    </section>
  );
}
