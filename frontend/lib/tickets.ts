import { API_BASE_URL } from "@/lib/auth";

export type TicketRecord = {
  id: number;
  ticket_no: string;
  title: string;
  description: string;
  category: string;
  priority: string;
  status: string;
  requester_id: number;
  assignee_id: number | null;
  source_conversation_id: number | null;
  created_at: string;
  updated_at: string;
};

export type TicketDraft = {
  title: string;
  description: string;
  category: string;
  priority: string;
  confidence: number;
  reason: string;
};

export type PendingApproval = {
  id: number;
  status: string;
  tool_name: string;
  requester_id: number;
  approver_id: number | null;
  decision_comment: string | null;
  execution_result: Record<string, unknown>;
  idempotency_key: string;
  created_at: string;
  updated_at: string;
  decided_at: string | null;
};

export type TicketCreatePayload = {
  title: string;
  description: string;
  category: string;
  priority: string;
};

export type TicketCreateResult =
  | { kind: "ticket"; ticket: TicketRecord }
  | { kind: "pending_approval"; approval: PendingApproval };

export type TicketStatusUpdatePayload = {
  status: string;
};

export type TicketCommentRecord = {
  id: number;
  ticket_id: number;
  author_id: number;
  author_name: string;
  author_role: string;
  content: string;
  created_at: string;
};

export type TicketHandlerOption = {
  id: number;
  email: string;
  name: string;
  role: string;
};

async function parseTicketResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const fallback = response.status === 403 ? "当前账号没有工单访问权限" : "工单请求失败，请稍后重试";
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

export async function listTickets(accessToken: string): Promise<TicketRecord[]> {
  const response = await fetch(`${API_BASE_URL}/api/tickets`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });

  return parseTicketResponse<TicketRecord[]>(response);
}

export async function getTicket(accessToken: string, ticketId: number): Promise<TicketRecord> {
  const response = await fetch(`${API_BASE_URL}/api/tickets/${ticketId}`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });

  return parseTicketResponse<TicketRecord>(response);
}

export async function createTicketDraft(accessToken: string, content: string): Promise<TicketDraft> {
  const response = await fetch(`${API_BASE_URL}/api/tickets/draft`, {
    method: "POST",
    headers: jsonHeaders(accessToken),
    body: JSON.stringify({ content }),
  });

  return parseTicketResponse<TicketDraft>(response);
}

export async function createTicket(
  accessToken: string,
  payload: TicketCreatePayload,
): Promise<TicketCreateResult> {
  const response = await fetch(`${API_BASE_URL}/api/tickets`, {
    method: "POST",
    headers: jsonHeaders(accessToken),
    body: JSON.stringify(payload),
  });

  const body = await parseTicketResponse<TicketRecord | { status: "pending_approval"; approval: PendingApproval }>(
    response,
  );

  if ("approval" in body) {
    return { kind: "pending_approval", approval: body.approval };
  }

  return { kind: "ticket", ticket: body as TicketRecord };
}

export async function updateTicketStatus(
  accessToken: string,
  ticketId: number,
  payload: TicketStatusUpdatePayload,
): Promise<TicketRecord> {
  const response = await fetch(`${API_BASE_URL}/api/tickets/${ticketId}/status`, {
    method: "PATCH",
    headers: jsonHeaders(accessToken),
    body: JSON.stringify(payload),
  });

  return parseTicketResponse<TicketRecord>(response);
}

export async function assignTicket(
  accessToken: string,
  ticketId: number,
  assigneeId: number | null,
): Promise<TicketRecord> {
  const response = await fetch(`${API_BASE_URL}/api/tickets/${ticketId}/assignee`, {
    method: "PATCH",
    headers: jsonHeaders(accessToken),
    body: JSON.stringify({ assignee_id: assigneeId }),
  });

  return parseTicketResponse<TicketRecord>(response);
}

export async function listTicketHandlers(accessToken: string): Promise<TicketHandlerOption[]> {
  const response = await fetch(`${API_BASE_URL}/api/auth/handlers`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });

  return parseTicketResponse<TicketHandlerOption[]>(response);
}

export async function listTicketComments(accessToken: string, ticketId: number): Promise<TicketCommentRecord[]> {
  const response = await fetch(`${API_BASE_URL}/api/tickets/${ticketId}/comments`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });

  return parseTicketResponse<TicketCommentRecord[]>(response);
}

export async function createTicketComment(
  accessToken: string,
  ticketId: number,
  content: string,
): Promise<TicketCommentRecord> {
  const response = await fetch(`${API_BASE_URL}/api/tickets/${ticketId}/comments`, {
    method: "POST",
    headers: jsonHeaders(accessToken),
    body: JSON.stringify({ content }),
  });

  return parseTicketResponse<TicketCommentRecord>(response);
}
