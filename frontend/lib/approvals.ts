import { API_BASE_URL } from "@/lib/auth";

export type ApprovalToolArgs = Record<string, unknown> & {
  requester_id?: number;
  title?: string;
  description?: string;
  category?: string;
  priority?: string;
  assignee_id?: number | null;
  source_conversation_id?: number | null;
};

export type ApprovalRecord = {
  id: number;
  status: string;
  tool_name: string;
  tool_args: ApprovalToolArgs;
  requester_id: number;
  approver_id: number | null;
  decision_comment: string | null;
  execution_result: Record<string, unknown>;
  idempotency_key: string;
  created_at: string;
  updated_at: string;
  decided_at: string | null;
};

async function parseApprovalResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const fallback = response.status === 403 ? "当前账号没有审批权限" : "审批请求失败，请稍后重试";
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

export async function listApprovals(accessToken: string): Promise<ApprovalRecord[]> {
  const response = await fetch(`${API_BASE_URL}/api/approvals`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });

  return parseApprovalResponse<ApprovalRecord[]>(response);
}

export async function getApproval(accessToken: string, approvalId: number): Promise<ApprovalRecord> {
  const response = await fetch(`${API_BASE_URL}/api/approvals/${approvalId}`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });

  return parseApprovalResponse<ApprovalRecord>(response);
}

export async function approveApproval(
  accessToken: string,
  approvalId: number,
  decisionComment: string,
): Promise<ApprovalRecord> {
  const response = await fetch(`${API_BASE_URL}/api/approvals/${approvalId}/approve`, {
    method: "POST",
    headers: jsonHeaders(accessToken),
    body: JSON.stringify({ decision_comment: decisionComment }),
  });

  return parseApprovalResponse<ApprovalRecord>(response);
}

export async function rejectApproval(
  accessToken: string,
  approvalId: number,
  decisionComment: string,
): Promise<ApprovalRecord> {
  const response = await fetch(`${API_BASE_URL}/api/approvals/${approvalId}/reject`, {
    method: "POST",
    headers: jsonHeaders(accessToken),
    body: JSON.stringify({ decision_comment: decisionComment }),
  });

  return parseApprovalResponse<ApprovalRecord>(response);
}
