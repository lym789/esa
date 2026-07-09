"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  ClipboardCheck,
  Loader2,
  RefreshCw,
  ShieldAlert,
  XCircle,
} from "lucide-react";

import { getStoredSession, type StoredSession } from "@/lib/session";
import {
  approveApproval,
  listApprovals,
  rejectApproval,
  type ApprovalRecord,
} from "@/lib/approvals";

const userNameLabels: Record<string, string> = {
  "employee@example.com": "员工用户",
  "handler@example.com": "工单处理人",
  "approver@example.com": "审批负责人",
  "admin@example.com": "管理员用户",
};

const statusLabels: Record<string, string> = {
  pending: "待审批",
  executed: "已通过",
  rejected: "已拒绝",
};

const approvalStatusOptions = [
  { value: "all", label: "全部审批" },
  { value: "pending", label: "只看待审批" },
  { value: "executed", label: "已通过" },
  { value: "rejected", label: "已拒绝" },
];

const toolNameLabels: Record<string, string> = {
  create_ticket: "创建工单",
};

const priorityLabels: Record<string, string> = {
  low: "低",
  medium: "中",
  high: "高",
  urgent: "紧急",
};

function formatDate(value: string | null): string {
  if (!value) {
    return "-";
  }
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function getToolText(approval: ApprovalRecord | null, key: string, fallback = "-"): string {
  const value = approval?.tool_args[key];
  if (typeof value === "string" && value.trim()) {
    return value;
  }
  if (typeof value === "number") {
    return String(value);
  }
  return fallback;
}

export default function ApprovalsPage() {
  const router = useRouter();
  const [session, setSession] = useState<StoredSession | null>(null);
  const [approvals, setApprovals] = useState<ApprovalRecord[]>([]);
  const [selectedApprovalId, setSelectedApprovalId] = useState<number | null>(null);
  const [approvalStatusFilter, setApprovalStatusFilter] = useState("all");
  const [decisionComment, setDecisionComment] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isDeciding, setIsDeciding] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const currentUser = session?.currentUser;
  const displayName = currentUser ? userNameLabels[currentUser.email] ?? currentUser.name : "正在检查登录状态";
  const canDecide = currentUser?.role === "approver" || currentUser?.role === "admin";
  const filteredApprovals = useMemo(
    () =>
      approvalStatusFilter === "all"
        ? approvals
        : approvals.filter((approval) => approval.status === approvalStatusFilter),
    [approvalStatusFilter, approvals],
  );
  const selectedApproval =
    filteredApprovals.find((approval) => approval.id === selectedApprovalId) ?? filteredApprovals[0] ?? null;
  const executionTicketId = selectedApproval?.execution_result.ticket_id;
  const createdTicketId =
    typeof executionTicketId === "number" || typeof executionTicketId === "string" ? executionTicketId : null;

  const summary = useMemo(() => {
    const pending = approvals.filter((approval) => approval.status === "pending").length;
    const executed = approvals.filter((approval) => approval.status === "executed").length;
    const rejected = approvals.filter((approval) => approval.status === "rejected").length;
    return { total: approvals.length, pending, executed, rejected };
  }, [approvals]);

  async function refreshApprovals(accessToken: string, preferredApprovalId?: number) {
    const records = await listApprovals(accessToken);
    setApprovals(records);
    if (preferredApprovalId && records.some((approval) => approval.id === preferredApprovalId)) {
      setSelectedApprovalId(preferredApprovalId);
    } else {
      setSelectedApprovalId(records[0]?.id ?? null);
    }
  }

  useEffect(() => {
    const storedSession = getStoredSession();
    if (!storedSession) {
      router.replace("/login");
      return;
    }

    setSession(storedSession);
    refreshApprovals(storedSession.accessToken)
      .catch((requestError) => {
        setError(requestError instanceof Error ? requestError.message : "审批列表加载失败");
      })
      .finally(() => setIsLoading(false));
  }, [router]);

  async function onRefresh() {
    if (!session) {
      return;
    }

    setError("");
    setIsLoading(true);
    try {
      await refreshApprovals(session.accessToken, selectedApproval?.id);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "审批列表刷新失败");
    } finally {
      setIsLoading(false);
    }
  }

  async function onDecision(decision: "approve" | "reject") {
    if (!session || !selectedApproval) {
      return;
    }

    setError("");
    setMessage("");
    setIsDeciding(true);
    try {
      const updated =
        decision === "approve"
          ? await approveApproval(session.accessToken, selectedApproval.id, decisionComment)
          : await rejectApproval(session.accessToken, selectedApproval.id, decisionComment);
      setDecisionComment("");
      setMessage(
        decision === "approve"
          ? `审批 #${updated.id} 已通过，原操作已执行`
          : `审批 #${updated.id} 已拒绝，原操作未执行`,
      );
      await refreshApprovals(session.accessToken, updated.id);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "审批处理失败");
    } finally {
      setIsDeciding(false);
    }
  }

  return (
    <main className="documents-page approvals-page">
      <div className="background-image" />
      <div className="background-depth" />
      <div className="background-shimmer" />

      <section className="documents-shell approvals-shell">
        <header className="documents-header">
          <button className="documents-back" type="button" onClick={() => router.push("/")}>
            <ArrowLeft className="h-4 w-4" />
            返回仪表盘
          </button>
          <div>
            <p className="documents-kicker">人工审批</p>
            <h1>审批中心</h1>
          </div>
          <div className="documents-user glass">
            <span>{displayName}</span>
            <strong>{canDecide ? "审批视图" : "发起记录"}</strong>
          </div>
        </header>

        <section className="approvals-stats">
          <article className="traces-stat glass">
            <ClipboardCheck className="h-5 w-5" />
            <span>可见审批</span>
            <strong>{summary.total}</strong>
          </article>
          <article className="traces-stat glass">
            <ShieldAlert className="h-5 w-5" />
            <span>待审批</span>
            <strong>{summary.pending}</strong>
          </article>
          <article className="traces-stat glass">
            <CheckCircle2 className="h-5 w-5" />
            <span>已通过</span>
            <strong>{summary.executed}</strong>
          </article>
          <button className="traces-refresh glass" type="button" onClick={onRefresh} disabled={isLoading}>
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            刷新
          </button>
        </section>

        <section className="approvals-grid">
          <section className="approvals-list glass">
            <div className="documents-card-heading">
              <ClipboardCheck className="h-5 w-5" />
              <h2>审批列表</h2>
            </div>

            <div className="approvals-filters">
              {approvalStatusOptions.map((option) => (
                <button
                  className={approvalStatusFilter === option.value ? "active" : ""}
                  key={option.value}
                  type="button"
                  onClick={() => {
                    setApprovalStatusFilter(option.value);
                    setMessage("");
                    setError("");
                  }}
                >
                  {option.label}
                </button>
              ))}
            </div>

            {isLoading ? (
              <div className="documents-empty">正在加载审批...</div>
            ) : approvals.length === 0 ? (
              <div className="documents-empty">暂无可见审批。员工提交紧急工单后，这里会出现待审批记录。</div>
            ) : filteredApprovals.length === 0 ? (
              <div className="documents-empty">当前筛选条件下没有审批记录。</div>
            ) : (
              <div className="approvals-list-items">
                {filteredApprovals.map((approval) => (
                  <button
                    className={`approval-list-item ${selectedApproval?.id === approval.id ? "active" : ""}`}
                    key={approval.id}
                    type="button"
                    onClick={() => {
                      setSelectedApprovalId(approval.id);
                      setMessage("");
                      setError("");
                    }}
                  >
                    <span>审批 #{approval.id}</span>
                    <strong>{getToolText(approval, "title", toolNameLabels[approval.tool_name] ?? approval.tool_name)}</strong>
                    <small>{statusLabels[approval.status] ?? approval.status} · {formatDate(approval.created_at)}</small>
                  </button>
                ))}
              </div>
            )}
          </section>

          <section className="approvals-detail glass">
            <div className="documents-card-heading">
              <ShieldAlert className="h-5 w-5" />
              <h2>审批详情</h2>
            </div>

            {!selectedApproval ? (
              <div className="documents-empty">选择一条审批记录后查看详情。</div>
            ) : (
              <div className="approval-detail-content">
                <div className="approval-detail-head">
                  <div>
                    <p>状态</p>
                    <strong>{statusLabels[selectedApproval.status] ?? selectedApproval.status}</strong>
                  </div>
                  <div>
                    <p>工具</p>
                    <strong>{toolNameLabels[selectedApproval.tool_name] ?? selectedApproval.tool_name}</strong>
                  </div>
                  <div>
                    <p>优先级</p>
                    <strong>{priorityLabels[getToolText(selectedApproval, "priority")] ?? getToolText(selectedApproval, "priority")}</strong>
                  </div>
                  <div>
                    <p>更新时间</p>
                    <strong>{formatDate(selectedApproval.updated_at)}</strong>
                  </div>
                </div>

                <div className="approval-risk">
                  <ShieldAlert className="h-5 w-5" />
                  <div>
                    <strong>风险原因</strong>
                    <p>该操作会创建紧急工单，必须由审批人确认后才能执行原工具调用。</p>
                  </div>
                </div>

                <div className="approval-field">
                  <span>工单标题</span>
                  <p>{getToolText(selectedApproval, "title")}</p>
                </div>

                <div className="approval-field">
                  <span>问题描述</span>
                  <p>{getToolText(selectedApproval, "description")}</p>
                </div>

                <div className="approval-tool-args">
                  <span>工具参数</span>
                  <pre>{JSON.stringify(selectedApproval.tool_args, null, 2)}</pre>
                </div>

                {selectedApproval.decision_comment ? (
                  <div className="approval-field">
                    <span>审批意见</span>
                    <p>{selectedApproval.decision_comment}</p>
                  </div>
                ) : null}

                {Object.keys(selectedApproval.execution_result).length > 0 ? (
                  <div className="approval-tool-args">
                    <span>执行结果</span>
                    <pre>{JSON.stringify(selectedApproval.execution_result, null, 2)}</pre>
                    {createdTicketId ? (
                      <button
                        className="approval-ticket-link"
                        type="button"
                        onClick={() => router.push(`/tickets/${createdTicketId}`)}
                      >
                        查看工单
                      </button>
                    ) : null}
                  </div>
                ) : null}

                <form
                  className="approval-decision-form"
                  onSubmit={(event) => {
                    event.preventDefault();
                    onDecision("approve");
                  }}
                >
                  <label>
                    <span>审批意见</span>
                    <textarea
                      value={decisionComment}
                      onChange={(event) => setDecisionComment(event.target.value)}
                      rows={3}
                      placeholder="例如：同意处理，请工单处理人优先跟进"
                    />
                  </label>

                  <div className="approval-actions">
                    <button
                      className="documents-primary"
                      type="submit"
                      disabled={!canDecide || selectedApproval.status !== "pending" || isDeciding}
                    >
                      {isDeciding ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                      通过审批
                    </button>
                    <button
                      className="documents-primary approval-reject"
                      type="button"
                      onClick={() => onDecision("reject")}
                      disabled={!canDecide || selectedApproval.status !== "pending" || isDeciding}
                    >
                      <XCircle className="h-4 w-4" />
                      拒绝审批
                    </button>
                  </div>
                  {!canDecide ? <p className="documents-empty">当前账号只能查看审批记录，不能执行通过或拒绝。</p> : null}
                </form>

                {message ? <p className="documents-message">{message}</p> : null}
                {error ? <p className="documents-error">{error}</p> : null}
              </div>
            )}
          </section>
        </section>
      </section>
    </main>
  );
}
