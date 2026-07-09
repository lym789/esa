import { API_BASE_URL } from "@/lib/auth";

export type ChatMessageRecord = {
  id: number;
  conversation_id: number;
  role: "user" | "assistant";
  content: string;
  citations: string[];
  metadata: Record<string, unknown>;
  created_at: string;
};

export type ChatConversationRecord = {
  id: number;
  title: string;
  user_id: number;
  created_at: string;
  updated_at: string;
};

export type ChatConversationDetail = ChatConversationRecord & {
  messages: ChatMessageRecord[];
};

async function parseChatResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const fallback = response.status === 403 ? "当前账号没有对话权限" : "AI 助手请求失败，请稍后重试";
    const body = await response.json().catch(() => null);
    throw new Error(typeof body?.detail === "string" ? body.detail : fallback);
  }

  return response.json() as Promise<T>;
}

function authHeaders(accessToken: string): HeadersInit {
  return {
    Authorization: `Bearer ${accessToken}`,
  };
}

function jsonHeaders(accessToken: string): HeadersInit {
  return {
    ...authHeaders(accessToken),
    "Content-Type": "application/json",
  };
}

export async function listChatConversations(accessToken: string): Promise<ChatConversationRecord[]> {
  const response = await fetch(`${API_BASE_URL}/api/chat/conversations`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });

  return parseChatResponse<ChatConversationRecord[]>(response);
}

export async function createChatConversation(
  accessToken: string,
  title = "新的智能问答",
): Promise<ChatConversationRecord> {
  const response = await fetch(`${API_BASE_URL}/api/chat/conversations`, {
    method: "POST",
    headers: jsonHeaders(accessToken),
    body: JSON.stringify({ title }),
  });

  return parseChatResponse<ChatConversationRecord>(response);
}

export async function getChatConversation(
  accessToken: string,
  conversationId: number,
): Promise<ChatConversationDetail> {
  const response = await fetch(`${API_BASE_URL}/api/chat/conversations/${conversationId}`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });

  return parseChatResponse<ChatConversationDetail>(response);
}

export async function sendChatMessage(
  accessToken: string,
  conversationId: number,
  content: string,
): Promise<ChatMessageRecord> {
  const response = await fetch(`${API_BASE_URL}/api/chat/conversations/${conversationId}/messages`, {
    method: "POST",
    headers: jsonHeaders(accessToken),
    body: JSON.stringify({ content }),
  });

  return parseChatResponse<ChatMessageRecord>(response);
}
