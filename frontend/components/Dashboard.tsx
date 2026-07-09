"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { Bell, ChevronDown, HelpCircle, Search, ShieldCheck, Sparkles } from "lucide-react";
import { features, navItems, sidebarActions, stats } from "@/lib/dashboard-data";
import type { CurrentUser } from "@/lib/auth";

type Ripple = {
  id: number;
  x: number;
  y: number;
};

type DashboardProps = {
  currentUser: CurrentUser;
};

const roleLabels: Record<CurrentUser["role"], string> = {
  employee: "员工",
  handler: "处理人",
  approver: "审批人",
  admin: "管理员",
};

const userNameLabels: Record<string, string> = {
  "employee@example.com": "员工用户",
  "handler@example.com": "工单处理人",
  "approver@example.com": "审批负责人",
  "admin@example.com": "管理员用户",
};

function getInitials(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function Dashboard({ currentUser }: DashboardProps) {
  const router = useRouter();
  const [ripples, setRipples] = useState<Ripple[]>([]);
  const displayName = userNameLabels[currentUser.email] ?? currentUser.name;
  const initials = getInitials(displayName) || currentUser.email.slice(0, 2).toUpperCase();

  const onPageClick = useCallback((event: React.MouseEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const id = Date.now() + Math.floor(Math.random() * 1000);

    setRipples((prev) => [...prev, { id, x, y }]);

    window.setTimeout(() => {
      setRipples((prev) => prev.filter((item) => item.id !== id));
    }, 2300);
  }, []);

  return (
    <main className="dashboard-page" onClick={onPageClick}>
      <div className="background-image" />
      <div className="background-depth" />
      <div className="background-shimmer" />

      <div className="ripple-layer" aria-hidden="true">
        {ripples.map((item) => (
          <span
            key={item.id}
            className="ripple"
            style={{ left: item.x, top: item.y }}
          />
        ))}
      </div>

      <section className="content-layer">
        <aside className="sidebar glass">
          <div className="logo-row">
            <img src="/icons/logo.png" alt="JadeFlow AI 标志" className="logo-img" />
            <h1 className="brand-text">JadeFlow AI</h1>
          </div>
          <div className="enterprise-pill">企业版</div>

          <nav className="nav">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.label}
                  className={`nav-button ${item.active ? "active" : ""}`}
                  onClick={(event) => {
                    if (item.href) {
                      event.stopPropagation();
                      router.push(item.href);
                    }
                  }}
                >
                  <Icon className="nav-icon" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          <div className="user-area">
            <div className="avatar">{initials}</div>
            <div>
              <p className="m-0 text-sm font-semibold">{displayName}</p>
              <p className="m-0 text-xs text-[#cce4d7]">{roleLabels[currentUser.role]}</p>
            </div>
            <ChevronDown className="ml-auto h-4 w-4" />
          </div>

          <div className="sidebar-actions">
            {sidebarActions.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.label}
                  className="sidebar-action"
                  aria-label={item.ariaLabel}
                >
                  <Icon className="mx-auto h-5 w-5" />
                </button>
              );
            })}
          </div>
        </aside>

        <section className="main-area">
          <header className="topbar">
            <div className="search-box glass">
              <Search className="h-5 w-5" />
              <span>搜索知识、工单、文档...</span>
              <span className="ml-auto rounded-md bg-black/10 px-2 py-1 text-sm opacity-80">⌘ K</span>
            </div>

            <div className="top-spacer" />

            <div className="top-chip glass">
              <span className="h-2.5 w-2.5 rounded-full bg-[#45ef75]" />
              AI 助手在线
            </div>

            <button className="top-chip notification-button glass" aria-label="帮助">
              <HelpCircle className="h-5 w-5" />
            </button>

            <button className="top-chip notification-button glass relative" aria-label="通知">
              <Bell className="h-5 w-5" />
              <span className="absolute right-1.5 top-1.5 grid h-5 w-5 place-items-center rounded-full bg-[#7df2bd] text-[10px] font-bold text-[#07533f]">
                3
              </span>
            </button>
          </header>

          <section className="hero">
            <h2 className="hero-title">企业支持智能体</h2>
            <h3 className="hero-subtitle">企业知识库与智能工单处理 AI 助手</h3>
            <p className="hero-desc">
              融合企业知识与业务流程的智能助手，助力高效服务与决策。
            </p>
            <button
              className="ask-button"
              onClick={(event) => {
                event.stopPropagation();
                router.push("/chat");
              }}
            >
              <span className="flex items-center gap-3">
                <Sparkles className="h-5 w-5 text-[#f5e6b8]" />
                询问 AI 助手
              </span>
              <span>→</span>
            </button>
          </section>

          <section className="stats-grid">
            {stats.map((item) => (
              <article key={item.title} className="stat-card glass">
                <div className="stat-inner">
                  <img src={item.icon} alt="" className="stat-icon" />
                  <div>
                    <p className="stat-title">{item.title}</p>
                    <p className="stat-value">{item.value}</p>
                    <p className="stat-delta">{item.delta}</p>
                  </div>
                </div>
              </article>
            ))}
          </section>

          <section className="feature-grid">
            {features.map((item) => (
              <button
                key={item.title}
                className="feature-card glass text-left"
                onClick={(event) => {
                  if (item.href) {
                    event.stopPropagation();
                    router.push(item.href);
                  }
                }}
              >
                <div className="feature-inner">
                  <img src={item.icon} alt="" className="feature-icon" />
                  <div>
                    <h3 className="feature-title">{item.title}</h3>
                    <p className="feature-desc">{item.desc}</p>
                  </div>
                  <span className="feature-arrow">›</span>
                </div>
              </button>
            ))}
          </section>

          <div className="bottom-notice glass">
            <ShieldCheck className="h-4 w-4" />
            <span>企业级安全防护 · 数据加密存储 · 权限精细控制 · 审计日志完整</span>
            <span className="ml-auto">›</span>
          </div>
        </section>
      </section>
    </main>
  );
}
