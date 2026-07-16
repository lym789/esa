"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Bot, Loader2, MessageCircle, Plus, RefreshCw, Send, UserRound } from "lucide-react";

import {
  createChatConversation,
  getChatConversation,
  listChatConversations,
  sendChatMessage,
  type ChatConversationRecord,
  type ChatMessageRecord,
} from "@/lib/chat";
import { getStoredSession, type StoredSession } from "@/lib/session";

const userNameLabels: Record<string, string> = {
  "employee@example.com": "员工用户",
  "handler@example.com": "工单处理人",
  "approver@example.com": "审批负责人",
  "admin@example.com": "管理员用户",
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export default function ChatPage() {
  const router = useRouter();
  const [session, setSession] = useState<StoredSession | null>(null);
  const [conversations, setConversations] = useState<ChatConversationRecord[]>([]);
  const [selectedConversationId, setSelectedConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessageRecord[]>([]);
  const [inputText, setInputText] = useState("公司邮箱无法登录应该怎么处理？");
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const currentUser = session?.currentUser;
  const displayName = currentUser ? userNameLabels[currentUser.email] ?? currentUser.name : "正在检查登录状态";
  const selectedConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === selectedConversationId) ?? null,
    [conversations, selectedConversationId],
  );

  async function loadConversation(accessToken: string, conversationId: number) {
    const detail = await getChatConversation(accessToken, conversationId);
    setSelectedConversationId(detail.id);
    setMessages(detail.messages);
  }

  async function refreshConversations(accessToken: string) {
    const records = await listChatConversations(accessToken);
    setConversations(records);
    if (records.length > 0) {
      await loadConversation(accessToken, records[0].id);
      return;
    }

    const created = await createChatConversation(accessToken, "新的智能问答");
    setConversations([created]);
    setSelectedConversationId(created.id);
    setMessages([]);
  }

  useEffect(() => {
    const storedSession = getStoredSession();
    if (!storedSession) {
      router.replace("/login");
      return;
    }

    setSession(storedSession);
    refreshConversations(storedSession.accessToken)
      .catch((requestError) => {
        setError(requestError instanceof Error ? requestError.message : "AI 助手加载失败");
      })
      .finally(() => setIsLoading(false));
  }, [router]);

  async function onCreateConversation() {
    if (!session) {
      return;
    }

    setError("");
    setMessage("");
    setIsLoading(true);
    try {
      const created = await createChatConversation(session.accessToken, "新的智能问答");
      setConversations((currentConversations) => [created, ...currentConversations]);
      setSelectedConversationId(created.id);
      setMessages([]);
      setMessage("新对话已创建");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "新建对话失败");
    } finally {
      setIsLoading(false);
    }
  }

  async function onRefresh() {
    if (!session) {
      return;
    }

    setError("");
    setIsLoading(true);
    try {
      await refreshConversations(session.accessToken);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "AI 助手刷新失败");
    } finally {
      setIsLoading(false);
    }
  }

  async function onSendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session || !selectedConversationId || !inputText.trim()) {
      return;
    }

    const content = inputText.trim();
    const optimisticMessage: ChatMessageRecord = {
      id: Date.now() * -1,
      conversation_id: selectedConversationId,
      role: "user",
      content,
      citations: [],
      metadata: {},
      created_at: new Date().toISOString(),
    };

    setError("");
    setMessage("");
    setInputText("");
    setMessages((currentMessages) => [...currentMessages, optimisticMessage]);
    setIsSending(true);
    try {
      const assistantMessage = await sendChatMessage(session.accessToken, selectedConversationId, content);
      setMessages((currentMessages) => [...currentMessages, assistantMessage]);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "消息发送失败");
    } finally {
      setIsSending(false);
    }
  }

  return (
    <main className="documents-page chat-page">
      <div className="background-image" />
      <div className="background-depth" />
      <div className="background-shimmer" />

      <section className="documents-shell chat-shell">
        <header className="documents-header">
          <button className="documents-back" type="button" onClick={() => router.push("/")}>
            <ArrowLeft className="h-4 w-4" />
            返回
          </button>
          <div>
            <p className="documents-kicker">知识库问答</p>
            <h1>智能助手</h1>
          </div>
          <div className="documents-user glass">
            <span>{displayName}</span>
            <strong>AI 问答</strong>
          </div>
        </header>

        <section className="chat-grid">
          <aside className="chat-conversations glass">
            <div className="documents-card-heading">
              <MessageCircle className="h-5 w-5" />
              <h2>对话列表</h2>
            </div>
            <div className="chat-side-actions">
              <button type="button" onClick={onCreateConversation} disabled={isLoading}>
                <Plus className="h-4 w-4" />
                新建对话
              </button>
              <button type="button" onClick={onRefresh} disabled={isLoading}>
                {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                刷新
              </button>
            </div>

            {conversations.length === 0 ? (
              <div className="documents-empty">暂无对话，可以新建一个知识库问答。</div>
            ) : (
              <div className="chat-conversation-list">
                {conversations.map((conversation) => (
                  <button
                    className={conversation.id === selectedConversationId ? "active" : ""}
                    key={conversation.id}
                    type="button"
                    onClick={() => {
                      if (!session) {
                        return;
                      }
                      setError("");
                      loadConversation(session.accessToken, conversation.id).catch((requestError) => {
                        setError(requestError instanceof Error ? requestError.message : "对话加载失败");
                      });
                    }}
                  >
                    <span>{conversation.title}</span>
                    <small>{formatDate(conversation.updated_at)}</small>
                  </button>
                ))}
              </div>
            )}
          </aside>

          <section className="chat-panel glass">
            <div className="documents-card-heading">
              <Bot className="h-5 w-5" />
              <h2>{selectedConversation?.title ?? "知识库问答"}</h2>
            </div>

            <div className="chat-message-list">
              {isLoading ? (
                <div className="documents-empty">正在加载 AI 助手...</div>
              ) : messages.length === 0 ? (
                <div className="documents-empty">输入问题后，AI 助手会基于知识库回答，并展示引用来源。</div>
              ) : (
                messages.map((chatMessage) => (
                  <article className={`chat-message ${chatMessage.role}`} key={chatMessage.id}>
                    <div className="chat-message-icon">
                      {chatMessage.role === "user" ? <UserRound className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                    </div>
                    <div className="chat-message-body">
                      <span>{chatMessage.role === "user" ? "我" : "AI 助手"}</span>
                      <p>{chatMessage.content}</p>
                      {chatMessage.role === "assistant" ? (
                        <div className="chat-citations">
                          <strong>引用来源</strong>
                          {chatMessage.citations.length === 0 ? (
                            <small>暂无引用来源</small>
                          ) : (
                            <ul>
                              {chatMessage.citations.map((citation) => (
                                <li key={citation}>{citation}</li>
                              ))}
                            </ul>
                          )}
                        </div>
                      ) : null}
                    </div>
                  </article>
                ))
              )}
            </div>

            <form className="chat-form" onSubmit={onSendMessage}>
              <label>
                <span>提问内容</span>
                <textarea
                  value={inputText}
                  onChange={(event) => setInputText(event.target.value)}
                  rows={3}
                  placeholder="例如：公司邮箱无法登录应该怎么处理？"
                />
              </label>
              <button className="documents-primary" type="submit" disabled={isSending || !selectedConversationId}>
                {isSending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                发送
              </button>
            </form>

            {message ? <p className="documents-message">{message}</p> : null}
            {error ? <p className="documents-error">{error}</p> : null}
          </section>
        </section>
      </section>
    </main>
  );
}
