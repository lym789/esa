"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, FileText, Loader2, RefreshCw, Trash2, UploadCloud } from "lucide-react";

import { getStoredSession, type StoredSession } from "@/lib/session";
import {
  deleteDocument,
  listDocuments,
  reindexDocument,
  uploadDocument,
  type DocumentRecord,
} from "@/lib/documents";

function formatFileSize(size: number): string {
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: "等待解析",
    processing: "解析中",
    completed: "已完成",
    failed: "失败",
  };
  return labels[status] ?? status;
}

const userNameLabels: Record<string, string> = {
  "employee@example.com": "员工用户",
  "handler@example.com": "工单处理人",
  "approver@example.com": "审批负责人",
  "admin@example.com": "管理员用户",
};

export default function AdminDocumentsPage() {
  const router = useRouter();
  const [session, setSession] = useState<StoredSession | null>(null);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const currentUser = session?.currentUser;
  const isAdmin = currentUser ? currentUser.role === "admin" : false;
  const displayName = currentUser ? userNameLabels[currentUser.email] ?? currentUser.name : "正在检查登录状态";

  const supportedText = useMemo(() => ".md / .txt / .pdf", []);

  async function refreshDocuments(accessToken: string) {
    const records = await listDocuments(accessToken);
    setDocuments(records);
  }

  useEffect(() => {
    const storedSession = getStoredSession();
    if (!storedSession) {
      router.replace("/login");
      return;
    }

    setSession(storedSession);
    refreshDocuments(storedSession.accessToken)
      .catch((requestError) => {
        setError(requestError instanceof Error ? requestError.message : "文档列表加载失败");
      })
      .finally(() => setIsLoading(false));
  }, [router]);

  async function onUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session || !selectedFile) {
      setError("请选择要上传的文档");
      return;
    }

    setError("");
    setMessage("");
    setIsUploading(true);

    try {
      await uploadDocument(session.accessToken, selectedFile);
      setSelectedFile(null);
      setMessage("文档已上传，等待后续解析任务处理");
      await refreshDocuments(session.accessToken);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "文档上传失败");
    } finally {
      setIsUploading(false);
    }
  }

  async function onReindex(documentId: number) {
    if (!session) {
      return;
    }

    setError("");
    setMessage("");
    try {
      await reindexDocument(session.accessToken, documentId);
      setMessage("文档已重新进入等待解析状态");
      await refreshDocuments(session.accessToken);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "重新解析失败");
    }
  }

  async function onDelete(documentId: number) {
    if (!session) {
      return;
    }

    setError("");
    setMessage("");
    try {
      await deleteDocument(session.accessToken, documentId);
      setMessage("文档已删除");
      await refreshDocuments(session.accessToken);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "删除文档失败");
    }
  }

  return (
    <main className="documents-page">
      <div className="background-image" />
      <div className="background-depth" />
      <div className="background-shimmer" />

      <section className="documents-shell">
        <header className="documents-header">
          <button className="documents-back" type="button" onClick={() => router.push("/")}>
            <ArrowLeft className="h-4 w-4" />
            返回
          </button>
          <div>
            <p className="documents-kicker">企业知识库</p>
            <h1>文档管理</h1>
          </div>
          <div className="documents-user glass">
            <span>{displayName}</span>
            <strong>{currentUser?.role === "admin" ? "管理员" : "只读访问"}</strong>
          </div>
        </header>

        <section className="documents-grid">
          <form className="documents-upload glass" onSubmit={onUpload}>
            <div className="documents-card-heading">
              <UploadCloud className="h-5 w-5" />
              <h2>上传文档</h2>
            </div>
            <p>支持 {supportedText}，上传后会自动解析文本并生成知识分块，后续将用于向量检索和问答引用。</p>

            {isAdmin ? (
              <>
                <label className="documents-file-input">
                  <input
                    type="file"
                    accept=".md,.txt,.pdf"
                    onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                  />
                  <span>{selectedFile ? selectedFile.name : "选择文档文件"}</span>
                </label>
                <button className="documents-primary" type="submit" disabled={isUploading}>
                  {isUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
                  {isUploading ? "正在上传" : "上传文档"}
                </button>
              </>
            ) : (
              <div className="documents-readonly">当前账号可以查看文档列表，上传和删除需要管理员权限。</div>
            )}

            {message ? <p className="documents-message">{message}</p> : null}
            {error ? <p className="documents-error">{error}</p> : null}
          </form>

          <section className="documents-list glass">
            <div className="documents-card-heading">
              <FileText className="h-5 w-5" />
              <h2>文档列表</h2>
            </div>

            {isLoading ? (
              <div className="documents-empty">正在加载文档...</div>
            ) : documents.length === 0 ? (
              <div className="documents-empty">暂无文档，先上传一份 Markdown、TXT 或 PDF。</div>
            ) : (
              <div className="documents-table">
                <div className="documents-row documents-row-head">
                  <span>文件名</span>
                  <span>类型</span>
                  <span>大小</span>
                  <span>状态</span>
                  <span>分块数</span>
                  <span>操作</span>
                </div>
                {documents.map((document) => (
                  <div className="documents-row" key={document.id}>
                    <span title={document.original_filename}>{document.original_filename}</span>
                    <span>{document.file_extension}</span>
                    <span>{formatFileSize(document.file_size)}</span>
                    <span>{statusLabel(document.status)}</span>
                    <span>{document.chunk_count}</span>
                    <span className="documents-actions">
                      <button type="button" disabled={!isAdmin} onClick={() => onReindex(document.id)} aria-label="重新解析">
                        <RefreshCw className="h-4 w-4" />
                      </button>
                      <button type="button" disabled={!isAdmin} onClick={() => onDelete(document.id)} aria-label="删除文档">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>
        </section>
      </section>
    </main>
  );
}
