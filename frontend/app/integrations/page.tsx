"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Link2, Loader2 } from "lucide-react";

import { getDashboardOverview, type DashboardOverview } from "@/lib/dashboard";
import { getStoredSession } from "@/lib/session";

const statusLabels: Record<string, string> = {
  connected: "已连接",
  configured: "已配置",
  active: "运行中",
  disabled: "未启用",
};

export default function IntegrationsPage() {
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
      .catch((requestError) => setError(requestError instanceof Error ? requestError.message : "集成状态加载失败"));
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
          <div><p className="documents-kicker">服务连接状态</p><h1>系统集成</h1></div>
          <div className="documents-user glass"><Link2 className="h-5 w-5" /><strong>运行状态</strong></div>
        </header>
        {error ? <p className="documents-error">{error}</p> : null}
        {!overview ? (
          <div className="documents-empty"><Loader2 className="h-5 w-5 animate-spin" />正在检查集成状态...</div>
        ) : (
          <section className="integration-grid">
            {overview.integrations.map((integration) => (
              <article className="settings-card glass" key={integration.key}>
                <div className="integration-heading">
                  <h2>{integration.name}</h2>
                  <span className={integration.status === "disabled" ? "disabled" : "active"}>
                    {statusLabels[integration.status] ?? integration.status}
                  </span>
                </div>
                <p>{integration.detail}</p>
              </article>
            ))}
          </section>
        )}
      </section>
    </main>
  );
}
