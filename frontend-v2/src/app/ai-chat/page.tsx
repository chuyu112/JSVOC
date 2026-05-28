"use client";

import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { ChatCircleText, GlobeHemisphereEast, PaperPlaneTilt, PlusCircle } from "@phosphor-icons/react";
import {
  listAIChatConversationHistory,
  listAIChatConversations,
  sendAIChat,
  type AIChatConversationSummary,
  type AIChatHistoryTurn,
  type AIChatMessage,
} from "@/lib/api/aiChat";

interface LocalMessage extends AIChatMessage {
  id: string;
  pending?: boolean;
  error?: boolean;
  meta?: string;
  sources?: Array<{ title?: string; url: string }>;
}

const welcomeMessage: LocalMessage = {
  id: "welcome",
  role: "assistant",
  content: "可以直接问短视频运营，账号策略、选题、文案、提示词、生图和生视频问题。也可以问你想问的各种问题",
};

function newMessage(role: AIChatMessage["role"], content: string, extra: Partial<LocalMessage> = {}): LocalMessage {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    role,
    content,
    ...extra,
  };
}

function formatHistoryMeta(turn: AIChatHistoryTurn) {
  const created = new Date(turn.created_at);
  const timeText = Number.isNaN(created.getTime())
    ? ""
    : `${created.getMonth() + 1}/${created.getDate()} ${String(created.getHours()).padStart(2, "0")}:${String(created.getMinutes()).padStart(2, "0")}`;
  const latencyText = typeof turn.latency_ms === "number" ? ` / ${turn.latency_ms}ms` : "";
  return `${turn.web_search ? "联网搜索 / " : ""}${turn.provider} / ${turn.model}${latencyText}${timeText ? ` / ${timeText}` : ""}`;
}

function messagesFromHistory(turns: AIChatHistoryTurn[]): LocalMessage[] {
  return turns.flatMap((turn) => [
    {
      id: `history-${turn.generation_record_id}-user`,
      role: "user" as const,
      content: turn.user_message,
    },
    {
      id: `history-${turn.generation_record_id}-assistant`,
      role: "assistant" as const,
      content: turn.assistant_message,
      meta: formatHistoryMeta(turn),
    },
  ]);
}

function createConversationId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `chat-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function formatConversationTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${month}/${day} ${hours}:${minutes}`;
}

export default function AIChatPage() {
  const [messages, setMessages] = useState<LocalMessage[]>([welcomeMessage]);
  const [conversations, setConversations] = useState<AIChatConversationSummary[]>([]);
  const [activeConversationId, setActiveConversationId] = useState(() => createConversationId());
  const [activeConversationTitle, setActiveConversationTitle] = useState("");
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [webSearch, setWebSearch] = useState(false);
  const [loadingConversations, setLoadingConversations] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const streamRef = useRef<HTMLDivElement>(null);

  const canSend = input.trim().length > 0 && !sending;
  const history = useMemo(
    () =>
      messages
        .filter((message) => message.id !== "welcome" && !message.pending && !message.error)
        .slice(-16)
        .map(({ role, content }) => ({ role, content })),
    [messages],
  );

  async function refreshConversations(selectLatest: boolean = false) {
    setLoadingConversations(true);
    try {
      const data = await listAIChatConversations(50);
      setConversations(data);
      if (selectLatest && data.length > 0) {
        await loadConversation(data[0]);
      }
    } catch {
      setConversations([]);
    } finally {
      setLoadingConversations(false);
    }
  }

  async function loadConversation(conversation: AIChatConversationSummary) {
    if (sending) return;
    setActiveConversationId(conversation.conversation_id);
    setActiveConversationTitle(conversation.title);
    setLoadingMessages(true);
    try {
      const turns = await listAIChatConversationHistory(conversation.conversation_id, 50);
      setMessages([welcomeMessage, ...messagesFromHistory(turns)]);
    } catch {
      setMessages([welcomeMessage]);
    } finally {
      setLoadingMessages(false);
    }
  }

  function startNewChat() {
    if (sending) return;
    setActiveConversationId(createConversationId());
    setActiveConversationTitle("");
    setMessages([welcomeMessage]);
    setInput("");
  }

  useEffect(() => {
    void refreshConversations(true);
  }, []);

  useLayoutEffect(() => {
    const stream = streamRef.current;
    if (!stream || loadingMessages) return;
    stream.scrollTop = stream.scrollHeight;
  }, [messages, loadingMessages]);

  async function handleSubmit(event?: React.FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    const cleanInput = input.trim();
    if (!cleanInput || sending) return;

    const userMessage = newMessage("user", cleanInput);
    const pendingMessage = newMessage("assistant", webSearch ? "正在联网搜索..." : "正在思考...", { pending: true });
    setInput("");
    setSending(true);
    setMessages((current) => [...current, userMessage, pendingMessage]);

    try {
      const conversationTitle = activeConversationTitle || cleanInput;
      const response = await sendAIChat(
        cleanInput,
        history,
        webSearch,
        activeConversationId,
        conversationTitle,
      );
      setActiveConversationId(response.conversation_id);
      setActiveConversationTitle(response.conversation_title);
      setMessages((current) =>
        current.map((message) =>
          message.id === pendingMessage.id
            ? {
                ...message,
                content: response.reply,
                pending: false,
                sources: response.sources || [],
                meta: `${webSearch ? "联网搜索 / " : ""}${response.provider} / ${response.model} / ${response.latency_ms}ms`,
              }
            : message,
        ),
      );
      void refreshConversations();
    } catch (err) {
      const message = err instanceof Error ? err.message : "AI聊天失败";
      setMessages((current) =>
        current.map((item) =>
          item.id === pendingMessage.id
            ? { ...item, content: message, pending: false, error: true }
            : item,
        ),
      );
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="page-section ai-chat-page">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="section-header"
      >
        <div>
          <p className="eyebrow">AI Chat</p>
          <h1 className="text-[28px] md:text-[36px] font-bold leading-[1.15] tracking-[-0.02em] text-[#f5f5f5]">
            AI聊天
          </h1>
        </div>
      </motion.div>

      <div className="ai-chat-workspace">
        <aside className="ai-chat-sidebar glass">
          <div className="ai-chat-sidebar-header">
            <div>
              <p>聊天历史</p>
              <span>{conversations.length ? `${conversations.length} 个话题` : "暂无话题"}</span>
            </div>
            <button type="button" onClick={startNewChat} disabled={sending} className="metal-btn ai-chat-new-btn">
              <PlusCircle size={16} weight="bold" />
              新聊天
            </button>
          </div>

          <div className="ai-chat-topic-list">
            {loadingConversations ? (
              <div className="ai-chat-topic-empty">加载中...</div>
            ) : conversations.length === 0 ? (
              <div className="ai-chat-topic-empty">还没有聊天话题</div>
            ) : (
              conversations.map((conversation) => (
                <button
                  key={conversation.conversation_id}
                  type="button"
                  onClick={() => void loadConversation(conversation)}
                  disabled={sending || loadingMessages}
                  className={`ai-chat-topic ${
                    conversation.conversation_id === activeConversationId ? "ai-chat-topic-active" : ""
                  }`}
                >
                  <span className="ai-chat-topic-title">
                    <ChatCircleText size={15} weight="bold" />
                    {conversation.title}
                  </span>
                  <span className="ai-chat-topic-last">{conversation.last_user_message}</span>
                  <span className="ai-chat-topic-meta">
                    {conversation.turn_count} 轮 / {formatConversationTime(conversation.updated_at)}
                  </span>
                </button>
              ))
            )}
          </div>
        </aside>

        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1], delay: 0.08 }}
          className="ai-chat-shell glass overflow-hidden"
        >
        <div ref={streamRef} className="ai-chat-stream">
          {loadingMessages ? (
            <article className="ai-chat-message ai-chat-message-assistant">
              <div className="ai-chat-message-label">AI</div>
              <div className="ai-chat-bubble">
                <p>正在加载聊天记录...</p>
                <span className="ai-chat-pulse" aria-hidden="true" />
              </div>
            </article>
          ) : null}
          {!loadingMessages && messages.map((message) => (
            <article
              key={message.id}
              className={`ai-chat-message ${
                message.role === "user" ? "ai-chat-message-user" : "ai-chat-message-assistant"
              } ${message.error ? "ai-chat-message-error" : ""}`}
            >
              <div className="ai-chat-message-label">
                {message.role === "user" ? "你" : "AI"}
              </div>
              <div className="ai-chat-bubble">
                <p>{message.content}</p>
                {message.pending ? <span className="ai-chat-pulse" aria-hidden="true" /> : null}
              </div>
              {message.sources && message.sources.length > 0 ? (
                <div className="ai-chat-sources">
                  {message.sources.slice(0, 4).map((source) => (
                    <a key={source.url} href={source.url} target="_blank" rel="noopener noreferrer">
                      {source.title || source.url}
                    </a>
                  ))}
                </div>
              ) : null}
              {message.meta ? <div className="ai-chat-meta">{message.meta}</div> : null}
            </article>
          ))}
        </div>

        <form className="ai-chat-composer" onSubmit={handleSubmit}>
          <textarea
            className="input-glass ai-chat-input"
            placeholder="输入你要讨论的问题"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
                void handleSubmit();
              }
            }}
          />
          <div className="ai-chat-actions">
            <button
              type="button"
              onClick={() => setWebSearch((current) => !current)}
              disabled={sending}
              className={`metal-btn ai-chat-action ${webSearch ? "ai-chat-search-active" : ""}`}
            >
              <GlobeHemisphereEast size={16} weight="bold" />
              联网搜索
            </button>
            <button
              type="button"
              onClick={startNewChat}
              disabled={sending}
              className="metal-btn ai-chat-action"
            >
              <PlusCircle size={16} weight="bold" />
              新聊天
            </button>
            <button
              type="submit"
              disabled={!canSend}
              className="metal-btn metal-btn-primary ai-chat-action"
            >
              <PaperPlaneTilt size={16} weight="fill" />
              {sending ? "发送中" : "发送"}
            </button>
          </div>
        </form>
        </motion.div>
      </div>
    </section>
  );
}
