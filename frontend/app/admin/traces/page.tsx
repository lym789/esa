"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Braces, Clock3, FileSearch, Loader2, RefreshCw, ShieldAlert } from "lucide-react";

import { getStoredSession, type StoredSession } from "@/lib/session";
import { getTrace, listTraces, type TraceRecord } from "@/lib/traces";

const userNameLabels: Record<string, string> = {
  "employee@example.com": "员工用户",
  "handler@example.com": "工单处理人",
  "approver@example.com": "审批负责人",
  "admin@example.com": "管理员用户",
};

const intentLabels: Record<string, string> = {
  knowledge_qa: "知识问答",
  create_ticket: "创建工单",
  approval_decision: "审批决策",
};

const approvalLabels: Record<string, string> = {
  not_required: "无需审批",
  pending: "等待审批",
  executed: "已执行",
  rejected: "已拒绝",
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

export default function AdminTracesPage() {
  const router = useRouter();
  const [session, setSession] = useState<StoredSession | null>(null);
  const [traces, setTraces] = useState<TraceRecord[]>([]);
  const [selectedTrace, setSelectedTrace] = useState<TraceRecord | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [error, setError] = useState("");

  const currentUser = session?.currentUser;
  const isAdmin = currentUser ? currentUser.role === "admin" : false;
  const displayName = currentUser ? userNameLabels[currentUser.email] ?? currentUser.name : "正在检查登录状态";

  const summary = useMemo(() => {
    const pending = traces.filter((trace) => trace.approval_status === "pending").length;
    const failed = traces.filter((trace) => trace.error_message).length;
    return {
      total: traces.length,
      pending,
      failed,
    };
  }, [traces]);

  async function refreshTraces(accessToken: string) {
    const records = await listTraces(accessToken);
    setTraces(records);
    setSelectedTrace((current) => current ?? records[0] ?? null);
  }

  useEffect(() => {
    const storedSession = getStoredSession();
    if (!storedSession) {
      router.replace("/login");
      return;
    }

    setSession(storedSession);
    if (storedSession.currentUser.role !== "admin") {
      setIsLoading(false);
      return;
    }

    refreshTraces(storedSession.accessToken)
      .catch((requestError) => {
        setError(requestError instanceof Error ? requestError.message : "追踪列表加载失败");
      })
      .finally(() => setIsLoading(false));
  }, [router]);

  async function onSelectTrace(traceId: number) {
    if (!session) {
      return;
    }

    setError("");
    setIsDetailLoading(true);
    try {
      const detail = await getTrace(session.accessToken, traceId);
      setSelectedTrace(detail);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "追踪详情加载失败");
    } finally {
      setIsDetailLoading(false);
    }
  }

  async function onRefresh() {
    if (!session || !isAdmin) {
      return;
    }

    setError("");
    setIsLoading(true);
    try {
      await refreshTraces(session.accessToken);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "追踪列表刷新失败");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="documents-page traces-page">
      <div className="background-image" />
      <div className="background-depth" />
      <div className="background-shimmer" />

      <section className="documents-shell traces-shell">
        <header className="documents-header">
          <button className="documents-back" type="button" onClick={() => router.push("/")}>
            <ArrowLeft className="h-4 w-4" />
            返回仪表盘
          </button>
          <div>
            <p className="documents-kicker">执行链路审计</p>
            <h1>智能体追踪</h1>
          </div>
          <div className="documents-user glass">
            <span>{displayName}</span>
            <strong>{currentUser?.role === "admin" ? "管理员" : "无追踪权限"}</strong>
          </div>
        </header>

        <section className="traces-stats">
          <article className="traces-stat glass">
            <FileSearch className="h-5 w-5" />
            <span>追踪总数</span>
            <strong>{summary.total}</strong>
          </article>
          <article className="traces-stat glass">
            <ShieldAlert className="h-5 w-5" />
            <span>等待审批</span>
            <strong>{summary.pending}</strong>
          </article>
          <article className="traces-stat glass">
            <Clock3 className="h-5 w-5" />
            <span>异常记录</span>
            <strong>{summary.failed}</strong>
          </article>
          <button className="traces-refresh glass" type="button" onClick={onRefresh} disabled={!isAdmin || isLoading}>
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            刷新
          </button>
        </section>

        {!isAdmin ? (
          <section className="traces-permission glass">
            <ShieldAlert className="h-6 w-6" />
            <div>
              <h2>当前账号不能查看追踪记录</h2>
              <p>请使用管理员账号登录后查看智能体执行链路、工具调用和审批状态。</p>
            </div>
          </section>
        ) : (
          <section className="traces-grid">
            <section className="traces-list glass">
              <div className="documents-card-heading">
                <FileSearch className="h-5 w-5" />
                <h2>追踪列表</h2>
              </div>

              {error ? <p className="documents-error">{error}</p> : null}

              {isLoading ? (
                <div className="documents-empty">正在加载追踪记录...</div>
              ) : traces.length === 0 ? (
                <div className="documents-empty">暂无追踪记录，先完成一次问答、工单或审批操作。</div>
              ) : (
                <div className="trace-list-items">
                  {traces.map((trace) => (
                    <button
                      key={trace.id}
                      className={`trace-list-item ${selectedTrace?.id === trace.id ? "active" : ""}`}
                      type="button"
                      onClick={() => onSelectTrace(trace.id)}
                    >
                      <span>{intentLabels[trace.intent] ?? trace.intent}</span>
                      <strong>{trace.tool_name ?? "未调用工具"}</strong>
                      <small>
                        {approvalLabels[trace.approval_status] ?? trace.approval_status} · {formatDate(trace.created_at)}
                      </small>
                    </button>
                  ))}
                </div>
              )}
            </section>

            <section className="traces-detail glass">
              <div className="documents-card-heading">
                <Braces className="h-5 w-5" />
                <h2>追踪详情</h2>
              </div>

              {isDetailLoading ? (
                <div className="documents-empty">正在加载详情...</div>
              ) : selectedTrace ? (
                <div className="trace-detail-content">
                  <div className="trace-detail-head">
                    <div>
                      <p>意图</p>
                      <strong>{intentLabels[selectedTrace.intent] ?? selectedTrace.intent}</strong>
                    </div>
                    <div>
                      <p>工具调用</p>
                      <strong>{selectedTrace.tool_name ?? "未调用工具"}</strong>
                    </div>
                    <div>
                      <p>审批状态</p>
                      <strong>{approvalLabels[selectedTrace.approval_status] ?? selectedTrace.approval_status}</strong>
                    </div>
                    <div>
                      <p>耗时</p>
                      <strong>{selectedTrace.elapsed_ms} ms</strong>
                    </div>
                  </div>

                  <div className="trace-field">
                    <span>用户输入</span>
                    <p>{selectedTrace.user_input}</p>
                  </div>

                  {selectedTrace.llm_output ? (
                    <div className="trace-field">
                      <span>智能体输出</span>
                      <p>{selectedTrace.llm_output}</p>
                    </div>
                  ) : null}

                  <div className="trace-json-grid">
                    <div>
                      <span>意图识别</span>
                      <pre>{formatJson(selectedTrace.intent_data)}</pre>
                    </div>
                    <div>
                      <span>工具参数</span>
                      <pre>{formatJson(selectedTrace.tool_args)}</pre>
                    </div>
                    <div>
                      <span>检索摘要</span>
                      <pre>{formatJson(selectedTrace.retrieved_chunks)}</pre>
                    </div>
                    <div>
                      <span>最终结果</span>
                      <pre>{formatJson(selectedTrace.final_result)}</pre>
                    </div>
                  </div>

                  {selectedTrace.error_message ? (
                    <p className="documents-error">{selectedTrace.error_message}</p>
                  ) : null}
                </div>
              ) : (
                <div className="documents-empty">请选择一条追踪记录查看详情。</div>
              )}
            </section>
          </section>
        )}
      </section>
    </main>
  );
}
