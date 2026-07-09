"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  Clock3,
  Loader2,
  MessageSquare,
  RefreshCw,
  Send,
  Ticket,
  UserCheck,
  Wrench,
} from "lucide-react";

import { getStoredSession, type StoredSession } from "@/lib/session";
import {
  assignTicket,
  createTicketComment,
  getTicket,
  listTicketHandlers,
  listTicketComments,
  updateTicketStatus,
  type TicketCommentRecord,
  type TicketHandlerOption,
  type TicketRecord,
} from "@/lib/tickets";

const userNameLabels: Record<string, string> = {
  "employee@example.com": "员工用户",
  "handler@example.com": "工单处理人",
  "approver@example.com": "审批负责人",
  "admin@example.com": "管理员用户",
};

const priorityLabels: Record<string, string> = {
  low: "低",
  medium: "中",
  high: "高",
  urgent: "紧急",
};

const statusLabels: Record<string, string> = {
  open: "待处理",
  in_progress: "处理中",
  resolved: "已解决",
  closed: "已关闭",
};

const statusOptions = [
  { value: "open", label: "待处理" },
  { value: "in_progress", label: "处理中" },
  { value: "resolved", label: "已解决" },
  { value: "closed", label: "已关闭" },
];

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

type TicketDetailPageProps = {
  params: {
    ticketId: string;
  };
};

export default function TicketDetailPage({ params }: TicketDetailPageProps) {
  const router = useRouter();
  const ticketId = Number(params.ticketId);
  const [session, setSession] = useState<StoredSession | null>(null);
  const [ticket, setTicket] = useState<TicketRecord | null>(null);
  const [comments, setComments] = useState<TicketCommentRecord[]>([]);
  const [handlerOptions, setHandlerOptions] = useState<TicketHandlerOption[]>([]);
  const [selectedAssigneeId, setSelectedAssigneeId] = useState("");
  const [commentText, setCommentText] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const [isAssigning, setIsAssigning] = useState(false);
  const [isCommenting, setIsCommenting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const currentUser = session?.currentUser;
  const displayName = currentUser ? userNameLabels[currentUser.email] ?? currentUser.name : "正在检查登录状态";
  const canUpdateStatus = currentUser?.role === "handler" || currentUser?.role === "admin";
  const canAssignTicket = currentUser?.role === "admin";
  const assigneeLabel = ticket?.assignee_id
    ? handlerOptions.find((handler) => handler.id === ticket.assignee_id)?.name ?? `用户 #${ticket.assignee_id}`
    : "未分配";

  async function refreshTicket(accessToken: string, shouldLoadHandlers = canAssignTicket) {
    const [nextTicket, nextComments, nextHandlers] = await Promise.all([
      getTicket(accessToken, ticketId),
      listTicketComments(accessToken, ticketId),
      shouldLoadHandlers ? listTicketHandlers(accessToken) : Promise.resolve([]),
    ]);
    setTicket(nextTicket);
    setComments(nextComments);
    setHandlerOptions(nextHandlers);
    setSelectedAssigneeId(nextTicket.assignee_id ? String(nextTicket.assignee_id) : "");
  }

  useEffect(() => {
    const storedSession = getStoredSession();
    if (!storedSession) {
      router.replace("/login");
      return;
    }

    setSession(storedSession);
    refreshTicket(storedSession.accessToken, storedSession.currentUser.role === "admin")
      .catch((requestError) => {
        setError(requestError instanceof Error ? requestError.message : "工单详情加载失败");
      })
      .finally(() => setIsLoading(false));
  }, [router, ticketId]);

  async function onRefresh() {
    if (!session) {
      return;
    }

    setError("");
    setIsLoading(true);
    try {
      await refreshTicket(session.accessToken);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "工单详情刷新失败");
    } finally {
      setIsLoading(false);
    }
  }

  async function onUpdateStatus(status: string) {
    if (!session || !ticket) {
      return;
    }

    setError("");
    setMessage("");
    setIsUpdating(true);
    try {
      const updated = await updateTicketStatus(session.accessToken, ticket.id, { status });
      setTicket(updated);
      setMessage(`处理状态已更新为：${statusLabels[updated.status] ?? updated.status}`);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "工单状态更新失败");
    } finally {
      setIsUpdating(false);
    }
  }

  async function onAssignTicket(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session || !ticket) {
      return;
    }

    setError("");
    setMessage("");
    setIsAssigning(true);
    try {
      const assigneeId = selectedAssigneeId ? Number(selectedAssigneeId) : null;
      const updated = await assignTicket(session.accessToken, ticket.id, assigneeId);
      setTicket(updated);
      setMessage(assigneeId ? "处理人已更新" : "处理人已清空");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "工单分配失败");
    } finally {
      setIsAssigning(false);
    }
  }

  async function onCreateComment(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session || !ticket) {
      return;
    }

    setError("");
    setMessage("");
    setIsCommenting(true);
    try {
      const comment = await createTicketComment(session.accessToken, ticket.id, commentText);
      setComments((currentComments) => [...currentComments, comment]);
      setCommentText("");
      setMessage("评论已添加");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "评论添加失败");
    } finally {
      setIsCommenting(false);
    }
  }

  return (
    <main className="documents-page ticket-detail-page">
      <div className="background-image" />
      <div className="background-depth" />
      <div className="background-shimmer" />

      <section className="documents-shell ticket-detail-shell">
        <header className="documents-header">
          <button className="documents-back" type="button" onClick={() => router.push("/tickets")}>
            <ArrowLeft className="h-4 w-4" />
            返回工单
          </button>
          <div>
            <p className="documents-kicker">企业服务台</p>
            <h1>工单详情</h1>
          </div>
          <div className="documents-user glass">
            <span>{displayName}</span>
            <strong>{canUpdateStatus ? "处理视图" : "查看视图"}</strong>
          </div>
        </header>

        <section className="tickets-stats">
          <article className="traces-stat glass">
            <Ticket className="h-5 w-5" />
            <span>工单编号</span>
            <strong>{ticket?.ticket_no ?? "-"}</strong>
          </article>
          <article className="traces-stat glass">
            <Clock3 className="h-5 w-5" />
            <span>处理状态</span>
            <strong>{ticket ? statusLabels[ticket.status] ?? ticket.status : "-"}</strong>
          </article>
          <article className="traces-stat glass">
            <CheckCircle2 className="h-5 w-5" />
            <span>优先级</span>
            <strong>{ticket ? priorityLabels[ticket.priority] ?? ticket.priority : "-"}</strong>
          </article>
          <button className="traces-refresh glass" type="button" onClick={onRefresh} disabled={isLoading}>
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            刷新
          </button>
        </section>

        <section className="ticket-detail-grid">
          <section className="ticket-detail-card glass">
            <div className="documents-card-heading">
              <Ticket className="h-5 w-5" />
              <h2>基础信息</h2>
            </div>

            {isLoading ? (
              <div className="documents-empty">正在加载工单详情...</div>
            ) : !ticket ? (
              <div className="documents-empty">未找到可访问的工单。</div>
            ) : (
              <div className="ticket-detail-content">
                <div className="ticket-detail-title">
                  <span>{ticket.ticket_no}</span>
                  <h2>{ticket.title}</h2>
                </div>

                <div className="ticket-detail-fields">
                  <div>
                    <span>分类</span>
                    <strong>{ticket.category}</strong>
                  </div>
                  <div>
                    <span>优先级</span>
                    <strong>{priorityLabels[ticket.priority] ?? ticket.priority}</strong>
                  </div>
                  <div>
                    <span>处理状态</span>
                    <strong>{statusLabels[ticket.status] ?? ticket.status}</strong>
                  </div>
                  <div>
                    <span>创建时间</span>
                    <strong>{formatDate(ticket.created_at)}</strong>
                  </div>
                  <div>
                    <span>更新时间</span>
                    <strong>{formatDate(ticket.updated_at)}</strong>
                  </div>
                  <div>
                    <span>处理人</span>
                    <strong>{assigneeLabel}</strong>
                  </div>
                </div>

                <div className="ticket-detail-description">
                  <span>问题描述</span>
                  <p>{ticket.description}</p>
                </div>
              </div>
            )}
          </section>

          <aside className="ticket-side-panel">
            <section className="ticket-status-card glass">
              <div className="documents-card-heading">
                <Wrench className="h-5 w-5" />
                <h2>状态流转</h2>
              </div>

              <div className="ticket-status-actions">
                {statusOptions.map((option) => (
                  <button
                    key={option.value}
                    className={ticket?.status === option.value ? "active" : ""}
                    type="button"
                    onClick={() => onUpdateStatus(option.value)}
                    disabled={!canUpdateStatus || !ticket || ticket.status === option.value || isUpdating}
                  >
                    {isUpdating && ticket?.status !== option.value ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <CheckCircle2 className="h-4 w-4" />
                    )}
                    {option.label}
                  </button>
                ))}
              </div>

              {!canUpdateStatus ? <p className="documents-empty">当前账号只能查看工单，处理人或管理员可以更新状态。</p> : null}
              {message ? <p className="documents-message">{message}</p> : null}
              {error ? <p className="documents-error">{error}</p> : null}
            </section>

            {canAssignTicket ? (
              <section className="ticket-assignee-card glass">
                <div className="documents-card-heading">
                  <UserCheck className="h-5 w-5" />
                  <h2>分配处理人</h2>
                </div>

                <form className="ticket-assignee-form" onSubmit={onAssignTicket}>
                  <label>
                    <span>处理人</span>
                    <select
                      value={selectedAssigneeId}
                      onChange={(event) => setSelectedAssigneeId(event.target.value)}
                      disabled={!ticket || isAssigning}
                    >
                      <option value="">未分配</option>
                      {handlerOptions.map((handler) => (
                        <option key={handler.id} value={handler.id}>
                          {handler.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button className="documents-primary" type="submit" disabled={!ticket || isAssigning}>
                    {isAssigning ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserCheck className="h-4 w-4" />}
                    保存分配
                  </button>
                </form>
              </section>
            ) : null}

            <section className="ticket-comments-card glass">
              <div className="documents-card-heading">
                <MessageSquare className="h-5 w-5" />
                <h2>工单评论</h2>
              </div>

              {comments.length === 0 ? (
                <div className="documents-empty">暂无评论，可以添加处理备注或补充信息。</div>
              ) : (
                <div className="ticket-comments-list">
                  {comments.map((comment) => (
                    <article className="ticket-comment-item" key={comment.id}>
                      <span>{comment.author_name} · {formatDate(comment.created_at)}</span>
                      <p>{comment.content}</p>
                    </article>
                  ))}
                </div>
              )}

              <form className="ticket-comment-form" onSubmit={onCreateComment}>
                <label>
                  <span>新增评论</span>
                  <textarea
                    value={commentText}
                    onChange={(event) => setCommentText(event.target.value)}
                    rows={3}
                    placeholder="补充处理进展、排查结果或用户反馈"
                  />
                </label>
                <button className="documents-primary" type="submit" disabled={!ticket || isCommenting}>
                  {isCommenting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  发送评论
                </button>
              </form>
            </section>
          </aside>
        </section>
      </section>
    </main>
  );
}
