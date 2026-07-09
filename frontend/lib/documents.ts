import { API_BASE_URL } from "@/lib/auth";

export type DocumentRecord = {
  id: number;
  original_filename: string;
  stored_filename: string;
  content_type: string;
  file_extension: string;
  file_size: number;
  storage_path: string;
  status: string;
  chunk_count: number;
  error_message: string | null;
  uploaded_by_id: number;
  created_at: string;
  updated_at: string;
};

async function parseDocumentResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const fallback = response.status === 403 ? "当前账号没有文档管理权限" : "文档请求失败，请稍后重试";
    const body = await response.json().catch(() => null);
    throw new Error(typeof body?.detail === "string" ? body.detail : fallback);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

function authHeaders(accessToken: string): HeadersInit {
  return {
    Authorization: `Bearer ${accessToken}`,
  };
}

export async function listDocuments(accessToken: string): Promise<DocumentRecord[]> {
  const response = await fetch(`${API_BASE_URL}/api/documents`, {
    headers: authHeaders(accessToken),
    cache: "no-store",
  });

  return parseDocumentResponse<DocumentRecord[]>(response);
}

export async function uploadDocument(accessToken: string, file: File): Promise<DocumentRecord> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/documents/upload`, {
    method: "POST",
    headers: authHeaders(accessToken),
    body: formData,
  });

  return parseDocumentResponse<DocumentRecord>(response);
}

export async function deleteDocument(accessToken: string, documentId: number): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/documents/${documentId}`, {
    method: "DELETE",
    headers: authHeaders(accessToken),
  });

  return parseDocumentResponse<void>(response);
}

export async function reindexDocument(accessToken: string, documentId: number): Promise<DocumentRecord> {
  const response = await fetch(`${API_BASE_URL}/api/documents/${documentId}/reindex`, {
    method: "POST",
    headers: authHeaders(accessToken),
  });

  return parseDocumentResponse<DocumentRecord>(response);
}
