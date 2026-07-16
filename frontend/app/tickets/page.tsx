"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, CheckCircle2, Loader2, RefreshCw, Send, Ticket, Wand2 } from "lucide-react";

import { getStoredSession, type StoredSession } from "@/lib/session";
import {
  createTicket,
  createTicketDraft,
  listTickets,
  type TicketDraft,
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

const ticketPriorityOptions = [
  { value: "low", label: "低" },
  { value: "medium", label: "中" },
  { value: "high", label: "高" },
  { value: "urgent", label: "紧急，需要审批" },
];

const statusLabels: Record<string, string> = {
  open: "待处理",
  in_progress: "处理中",
  resolved: "已解决",
  closed: "已关闭",
};

const ticketStatusOptions = [
  { value: "all", label: "全部状态" },
  { value: "open", label: "待处理" },
  { value: "in_progress", label: "处理中" },
  { value: "resolved", label: "已解决" },
  { value: "closed", label: "已关闭" },
];

const ticketPriorityFilterOptions = [
  { value: "all", label: "全部优先级" },
  { value: "low", label: "低" },
  { value: "medium", label: "中" },
  { value: "high", label: "高" },
  { value: "urgent", label: "紧急" },
];

const ticketsPageSize = 8;

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export default function TicketsPage() {
  const router = useRouter();
  const [session, setSession] = useState<StoredSession | null>(null);
  const [tickets, setTickets] = useState<TicketRecord[]>([]);
  const [ticketSearchText, setTicketSearchText] = useState("");
  const [ticketStatusFilter, setTicketStatusFilter] = useState("all");
  const [ticketPriorityFilter, setTicketPriorityFilter] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [requestText, setRequestText] = useState("帮我创建一个 IT 工单，我的公司邮箱无法登录");
  const [draft, setDraft] = useState<TicketDraft | null>(null);
  const [editableDraft, setEditableDraft] = useState<TicketDraft | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDrafting, setIsDrafting] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const currentUser = session?.currentUser;
  const displayName = currentUser ? userNameLabels[currentUser.email] ?? currentUser.name : "正在检查登录状态";

  const summary = useMemo(() => {
    const urgent = tickets.filter((ticket) => ticket.priority === "urgent").length;
    const open = tickets.filter((ticket) => ticket.status === "open").length;
    return { total: tickets.length, open, urgent };
  }, [tickets]);

  const filteredTickets = useMemo(() => {
    const searchText = ticketSearchText.trim().toLowerCase();

    return tickets.filter((ticket) => {
      const matchesStatus = ticketStatusFilter === "all" || ticket.status === ticketStatusFilter;
      const matchesPriority = ticketPriorityFilter === "all" || ticket.priority === ticketPriorityFilter;
      const searchableText = [
        ticket.ticket_no,
        ticket.title,
        ticket.description,
        ticket.category,
        statusLabels[ticket.status] ?? ticket.status,
        priorityLabels[ticket.priority] ?? ticket.priority,
      ]
        .join(" ")
        .toLowerCase();

      return matchesStatus && matchesPriority && (!searchText || searchableText.includes(searchText));
    });
  }, [ticketPriorityFilter, ticketSearchText, ticketStatusFilter, tickets]);

  const totalPages = Math.max(1, Math.ceil(filteredTickets.length / ticketsPageSize));
  const safeCurrentPage = Math.min(currentPage, totalPages);

  const paginatedTickets = useMemo(() => {
    const startIndex = (safeCurrentPage - 1) * ticketsPageSize;
    return filteredTickets.slice(startIndex, startIndex + ticketsPageSize);
  }, [filteredTickets, safeCurrentPage]);

  async function refreshTickets(accessToken: string) {
    const records = await listTickets(accessToken);
    setTickets(records);
  }

  useEffect(() => {
    setCurrentPage(1);
  }, [ticketPriorityFilter, ticketSearchText, ticketStatusFilter]);

  useEffect(() => {
    setCurrentPage((page) => Math.min(page, totalPages));
  }, [totalPages]);

  useEffect(() => {
    const storedSession = getStoredSession();
    if (!storedSession) {
      router.replace("/login");
      return;
    }

    setSession(storedSession);
    refreshTickets(storedSession.accessToken)
      .catch((requestError) => {
        setError(requestError instanceof Error ? requestError.message : "工单列表加载失败");
      })
      .finally(() => setIsLoading(false));
  }, [router]);

  async function onCreateDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session) {
      return;
    }

    setError("");
    setMessage("");
    setIsDrafting(true);
    try {
      const nextDraft = await createTicketDraft(session.accessToken, requestText);
      setDraft(nextDraft);
      setEditableDraft(nextDraft);
      setMessage("工单草稿已生成，可以调整优先级后创建");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "工单草稿生成失败");
    } finally {
      setIsDrafting(false);
    }
  }

  async function onConfirmCreate() {
    if (!session || !editableDraft) {
      return;
    }

    setError("");
    setMessage("");
    if (!editableDraft.title.trim() || !editableDraft.description.trim() || !editableDraft.category.trim()) {
      setError("请补全标题、分类和问题描述后再创建工单");
      return;
    }

    setIsCreating(true);
    try {
      const result = await createTicket(session.accessToken, {
        title: editableDraft.title,
        description: editableDraft.description,
        category: editableDraft.category,
        priority: editableDraft.priority,
      });
      if (result.kind === "pending_approval") {
        setMessage(`紧急工单已进入审批，审批编号 #${result.approval.id}`);
      } else {
        setMessage(`工单已创建：${result.ticket.ticket_no}`);
      }
      setDraft(null);
      setEditableDraft(null);
      await refreshTickets(session.accessToken);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "工单创建失败");
    } finally {
      setIsCreating(false);
    }
  }

  async function onRefresh() {
    if (!session) {
      return;
    }

    setError("");
    setIsLoading(true);
    try {
      await refreshTickets(session.accessToken);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "工单列表刷新失败");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="documents-page tickets-page">
      <div className="background-image" />
      <div className="background-depth" />
      <div className="background-shimmer" />

      <section className="documents-shell tickets-shell">
        <header className="documents-header">
          <button className="documents-back" type="button" onClick={() => router.push("/")}>
            <ArrowLeft className="h-4 w-4" />
            返回
          </button>
          <div>
            <p className="documents-kicker">企业服务台</p>
            <h1>工单中心</h1>
          </div>
          <div className="documents-user glass">
            <span>{displayName}</span>
            <strong>{currentUser?.role === "handler" ? "处理人视图" : "我的工单"}</strong>
          </div>
        </header>

        <section className="tickets-stats">
          <article className="traces-stat glass">
            <Ticket className="h-5 w-5" />
            <span>可见工单</span>
            <strong>{summary.total}</strong>
          </article>
          <article className="traces-stat glass">
            <CheckCircle2 className="h-5 w-5" />
            <span>待处理</span>
            <strong>{summary.open}</strong>
          </article>
          <article className="traces-stat glass">
            <Send className="h-5 w-5" />
            <span>紧急</span>
            <strong>{summary.urgent}</strong>
          </article>
          <button className="traces-refresh glass" type="button" onClick={onRefresh} disabled={isLoading}>
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            刷新
          </button>
        </section>

        <section className="tickets-grid">
          <section className="tickets-draft glass">
            <div className="documents-card-heading">
              <Wand2 className="h-5 w-5" />
              <h2>从描述生成工单</h2>
            </div>

            <form className="ticket-draft-form" onSubmit={onCreateDraft}>
              <label>
                <span>问题描述</span>
                <textarea
                  value={requestText}
                  onChange={(event) => setRequestText(event.target.value)}
                  rows={5}
                  placeholder="例如：帮我创建一个 IT 工单，我的公司邮箱无法登录"
                />
              </label>
              <button className="documents-primary" type="submit" disabled={isDrafting}>
                {isDrafting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Wand2 className="h-4 w-4" />}
                {isDrafting ? "正在生成" : "生成草稿"}
              </button>
            </form>

            {editableDraft ? (
              <form
                className="ticket-draft-preview ticket-draft-editor"
                onSubmit={(event) => {
                  event.preventDefault();
                  onConfirmCreate();
                }}
              >
                <label>
                  <span>标题</span>
                  <input
                    value={editableDraft.title}
                    onChange={(event) =>
                      setEditableDraft((currentDraft) =>
                        currentDraft ? { ...currentDraft, title: event.target.value } : currentDraft,
                      )
                    }
                  />
                </label>
                <label>
                  <span>分类</span>
                  <input
                    value={editableDraft.category}
                    onChange={(event) =>
                      setEditableDraft((currentDraft) =>
                        currentDraft ? { ...currentDraft, category: event.target.value } : currentDraft,
                      )
                    }
                  />
                </label>
                <label>
                  <span>优先级</span>
                  <select
                    value={editableDraft.priority}
                    onChange={(event) =>
                      setEditableDraft((currentDraft) =>
                        currentDraft ? { ...currentDraft, priority: event.target.value } : currentDraft,
                      )
                    }
                  >
                    {ticketPriorityOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>问题描述</span>
                  <textarea
                    value={editableDraft.description}
                    rows={4}
                    onChange={(event) =>
                      setEditableDraft((currentDraft) =>
                        currentDraft ? { ...currentDraft, description: event.target.value } : currentDraft,
                      )
                    }
                  />
                </label>
                <p>{draft?.reason ?? "确认信息后创建工单"}</p>
                <div className="ticket-draft-actions">
                  <button className="documents-primary" type="submit" disabled={isCreating}>
                    {isCreating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                    {editableDraft.priority === "urgent" ? "提交审批" : "创建工单"}
                  </button>
                </div>
              </form>
            ) : null}

            {message ? <p className="documents-message">{message}</p> : null}
            {error ? <p className="documents-error">{error}</p> : null}
          </section>

          <section className="tickets-list glass">
            <div className="documents-card-heading">
              <Ticket className="h-5 w-5" />
              <h2>工单列表</h2>
            </div>

            {isLoading ? (
              <div className="documents-empty">正在加载工单...</div>
            ) : tickets.length === 0 ? (
              <div className="documents-empty">暂无可见工单，可以先从左侧描述生成一个工单草稿。</div>
            ) : (
              <>
                <div className="tickets-filters">
                  <label className="tickets-filter-input">
                    <span>搜索工单</span>
                    <input
                      value={ticketSearchText}
                      onChange={(event) => setTicketSearchText(event.target.value)}
                      placeholder="搜索编号、标题、描述或分类"
                    />
                  </label>
                  <label>
                    <span>状态</span>
                    <select value={ticketStatusFilter} onChange={(event) => setTicketStatusFilter(event.target.value)}>
                      {ticketStatusOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>优先级</span>
                    <select
                      value={ticketPriorityFilter}
                      onChange={(event) => setTicketPriorityFilter(event.target.value)}
                    >
                      {ticketPriorityFilterOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>

                {filteredTickets.length === 0 ? (
                  <div className="documents-empty">没有符合筛选条件的工单。</div>
                ) : (
                  <>
                    <div className="tickets-table">
                      <div className="tickets-row tickets-row-head">
                        <span>编号</span>
                        <span>标题</span>
                        <span>分类</span>
                        <span>优先级</span>
                        <span>状态</span>
                        <span>创建时间</span>
                        <span>操作</span>
                      </div>
                      {paginatedTickets.map((ticket) => (
                        <div className="tickets-row" key={ticket.id}>
                          <span>{ticket.ticket_no}</span>
                          <span title={ticket.description}>{ticket.title}</span>
                          <span>{ticket.category}</span>
                          <span>{priorityLabels[ticket.priority] ?? ticket.priority}</span>
                          <span>{statusLabels[ticket.status] ?? ticket.status}</span>
                          <span>{formatDate(ticket.created_at)}</span>
                          <button
                            className="ticket-detail-link"
                            type="button"
                            onClick={() => router.push(`/tickets/${ticket.id}`)}
                          >
                            查看详情
                          </button>
                        </div>
                      ))}
                    </div>
                    <div className="tickets-pagination">
                      <button
                        type="button"
                        onClick={() => setCurrentPage((page) => Math.max(1, page - 1))}
                        disabled={safeCurrentPage === 1}
                      >
                        上一页
                      </button>
                      <span>
                        第 {safeCurrentPage} / {totalPages} 页 · 共 {filteredTickets.length} 条
                      </span>
                      <button
                        type="button"
                        onClick={() => setCurrentPage((page) => Math.min(totalPages, page + 1))}
                        disabled={safeCurrentPage === totalPages}
                      >
                        下一页
                      </button>
                    </div>
                  </>
                )}
              </>
            )}
          </section>
        </section>
      </section>
    </main>
  );
}
