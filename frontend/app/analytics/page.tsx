"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, BarChart3, Loader2 } from "lucide-react";

import { getDashboardOverview, type DashboardOverview } from "@/lib/dashboard";
import { getStoredSession } from "@/lib/session";

const groupLabels = {
  ticket_status: "工单状态",
  ticket_priority: "优先级分布",
  ticket_category: "工单分类",
};

const valueLabels: Record<string, string> = {
  open: "待处理",
  in_progress: "处理中",
  resolved: "已解决",
  closed: "已关闭",
  low: "低",
  medium: "中",
  high: "高",
  urgent: "紧急",
};

export default function AnalyticsPage() {
  const router = useRouter();
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const session = getStoredSession();
    if (!session) {
      router.replace("/login");
      return;
    }
    getDashboardOverview(session.accessToken)
      .then(setOverview)
      .catch((requestError) => setError(requestError instanceof Error ? requestError.message : "分析数据加载失败"));
  }, [router]);

  return (
    <main className="documents-page">
      <div className="background-image" />
      <div className="background-depth" />
      <section className="documents-shell">
        <header className="documents-header">
          <button className="documents-back" type="button" onClick={() => router.push("/")}>
            <ArrowLeft className="h-4 w-4" />返回
          </button>
          <div><p className="documents-kicker">实时业务洞察</p><h1>数据分析</h1></div>
          <div className="documents-user glass"><BarChart3 className="h-5 w-5" /><strong>实时 API 数据</strong></div>
        </header>

        {error ? <p className="documents-error">{error}</p> : null}
        {!overview ? (
          <div className="documents-empty"><Loader2 className="h-5 w-5 animate-spin" />正在加载分析数据...</div>
        ) : (
          <>
            <section className="analytics-summary">
              {overview.stats.map((stat) => (
                <article className="settings-card glass" key={stat.key}>
                  <span>{stat.label}</span><strong>{stat.key === "average_resolution_hours" ? `${stat.value}h` : stat.value}</strong><small>{stat.detail}</small>
                </article>
              ))}
            </section>
            <section className="analytics-grid">
              {(Object.keys(groupLabels) as Array<keyof typeof groupLabels>).map((groupKey) => {
                const entries = Object.entries(overview.analytics[groupKey]);
                const maxValue = Math.max(...entries.map(([, value]) => value), 1);
                return (
                  <article className="settings-card glass" key={groupKey}>
                    <h2>{groupLabels[groupKey]}</h2>
                    {entries.length ? entries.map(([key, value]) => (
                      <div className="analytics-row" key={key}>
                        <span>{valueLabels[key] ?? key}</span>
                        <div><i style={{ width: `${(value / maxValue) * 100}%` }} /></div>
                        <strong>{value}</strong>
                      </div>
                    )) : <p className="documents-empty">暂无可分析数据</p>}
                  </article>
                );
              })}
            </section>
          </>
        )}
      </section>
    </main>
  );
}
