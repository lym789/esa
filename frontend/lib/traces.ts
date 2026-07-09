import { API_BASE_URL } from "@/lib/auth";

export type TraceRecord = {
  id: number;
  conversation_id: number | null;
  user_id: number;
  intent: string;
  user_input: string;
  intent_data: Record<string, unknown>;
  retrieved_chunks: Array<Record<string, unknown>>;
  llm_input_summary: string | null;
  llm_output: string | null;
  tool_name: string | null;
  tool_args: Record<string, unknown>;
  approval_status: string;
  final_result: Record<string, unknown>;
  error_message: string | null;
  elapsed_ms: number;
  created_at: string;
};

async function parseTraceResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const fallback = response.status === 403 ? "当前账号没有追踪查看权限" : "追踪数据请求失败，请稍后重试";
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

export async function listTraces(accessToken: string): Promise<TraceRecord[]> {
  const response = await fetch(`${API_BASE_URL}/api/traces`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });

  return parseTraceResponse<TraceRecord[]>(response);
}

export async function getTrace(accessToken: string, traceId: number): Promise<TraceRecord> {
  const response = await fetch(`${API_BASE_URL}/api/traces/${traceId}`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });

  return parseTraceResponse<TraceRecord>(response);
}
