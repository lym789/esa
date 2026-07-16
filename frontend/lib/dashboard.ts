import { API_BASE_URL } from "@/lib/auth";

export type DashboardStat = {
  key: string;
  label: string;
  value: number;
  detail: string;
};

export type DashboardNotification = {
  id: string;
  kind: string;
  title: string;
  message: string;
  href: string;
  created_at: string;
};

export type DashboardIntegration = {
  key: string;
  name: string;
  status: string;
  detail: string;
};

export type DashboardOverview = {
  stats: DashboardStat[];
  status: {
    backend: string;
    database: string;
    llm_configured: boolean;
    embedding_configured: boolean;
  };
  notifications: DashboardNotification[];
  analytics: {
    ticket_status: Record<string, number>;
    ticket_priority: Record<string, number>;
    ticket_category: Record<string, number>;
  };
  integrations: DashboardIntegration[];
};

export type DashboardSearchResult = {
  kind: "knowledge" | "document" | "ticket";
  title: string;
  snippet: string;
  href: string;
};

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? "首页数据请求失败");
  }
  return response.json() as Promise<T>;
}

export async function getDashboardOverview(accessToken: string): Promise<DashboardOverview> {
  const response = await fetch(`${API_BASE_URL}/api/dashboard/overview`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return readJson<DashboardOverview>(response);
}

export async function searchDashboard(
  accessToken: string,
  query: string,
): Promise<DashboardSearchResult[]> {
  const response = await fetch(`${API_BASE_URL}/api/dashboard/search?q=${encodeURIComponent(query)}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  const payload = await readJson<{ query: string; results: DashboardSearchResult[] }>(response);
  return payload.results;
}
