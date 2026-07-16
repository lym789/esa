"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Bell, HelpCircle, Loader2, Search, Sparkles } from "lucide-react";
import { features, navItems, stats } from "@/lib/dashboard-data";
import type { CurrentUser } from "@/lib/auth";
import {
  getDashboardOverview,
  searchDashboard,
  type DashboardOverview,
  type DashboardSearchResult,
} from "@/lib/dashboard";

type Ripple = {
  id: number;
  x: number;
  y: number;
};

type DashboardProps = {
  currentUser: CurrentUser;
  accessToken: string;
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

const searchKindLabels: Record<DashboardSearchResult["kind"], string> = {
  knowledge: "知识",
  document: "文档",
  ticket: "工单",
};

export function Dashboard({ currentUser, accessToken }: DashboardProps) {
  const router = useRouter();
  const [ripples, setRipples] = useState<Ripple[]>([]);
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [overviewError, setOverviewError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<DashboardSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const displayName = userNameLabels[currentUser.email] ?? currentUser.name;
  const initials = getInitials(displayName) || currentUser.email.slice(0, 2).toUpperCase();
  const liveStats = useMemo(
    () => new Map(overview?.stats.map((item) => [item.key, item]) ?? []),
    [overview],
  );
  const isAssistantOnline = Boolean(
    overview?.status.backend === "online" && overview.status.database === "online" && overview.status.llm_configured,
  );

  useEffect(() => {
    getDashboardOverview(accessToken)
      .then(setOverview)
      .catch((error) => setOverviewError(error instanceof Error ? error.message : "首页数据加载失败"));
  }, [accessToken]);

  useEffect(() => {
    function onShortcut(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchInputRef.current?.focus();
        setIsSearchOpen(true);
      }
    }
    window.addEventListener("keydown", onShortcut);
    return () => window.removeEventListener("keydown", onShortcut);
  }, []);

  async function onSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = searchQuery.trim();
    if (!query) {
      setSearchResults([]);
      setIsSearchOpen(true);
      return;
    }
    setIsSearching(true);
    setIsSearchOpen(true);
    try {
      setSearchResults(await searchDashboard(accessToken, query));
    } catch (error) {
      setOverviewError(error instanceof Error ? error.message : "搜索失败");
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  }

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
            <img src="/icons/logo.png" alt="Midori 标志" className="logo-img" />
            <h1 className="brand-text">Midori</h1>
          </div>

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
            <p className="m-0 text-sm font-semibold">{displayName}</p>
          </div>
        </aside>

        <section className="main-area">
          <header className="topbar">
            <div className="search-area">
              <form className="search-box glass" onSubmit={onSearch}>
                {isSearching ? <Loader2 className="h-5 w-5 animate-spin" /> : <Search className="h-5 w-5" />}
                <input
                  ref={searchInputRef}
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  onFocus={() => setIsSearchOpen(true)}
                  placeholder="搜索知识、工单、文档..."
                  aria-label="全局搜索"
                />
                <button type="submit" className="search-shortcut" aria-label="执行搜索">⌘ K</button>
              </form>
              {isSearchOpen ? (
                <div className="search-results glass">
                  {!searchQuery.trim() ? (
                    <p>输入关键词后按回车搜索。</p>
                  ) : isSearching ? (
                    <p>正在搜索...</p>
                  ) : searchResults.length === 0 ? (
                    <p>没有找到匹配的知识、文档或工单。</p>
                  ) : (
                    searchResults.map((result, index) => (
                      <button
                        type="button"
                        key={`${result.kind}-${result.href}-${index}`}
                        onClick={(event) => {
                          event.stopPropagation();
                          router.push(result.href);
                        }}
                      >
                        <span>{searchKindLabels[result.kind]}</span>
                        <strong>{result.title}</strong>
                        <small>{result.snippet}</small>
                      </button>
                    ))
                  )}
                </div>
              ) : null}
            </div>

            <div className="top-spacer" />

            <div className={`top-chip glass ${isAssistantOnline ? "" : "offline"}`} title={overviewError || undefined}>
              <span className={`h-2.5 w-2.5 rounded-full ${isAssistantOnline ? "bg-[#45ef75]" : "bg-[#f0b45d]"}`} />
              {overview ? (isAssistantOnline ? "AI 助手在线" : "AI 服务未就绪") : "正在检测服务"}
            </div>

            <button
              className="top-chip notification-button glass"
              aria-label="帮助"
              onClick={(event) => {
                event.stopPropagation();
                router.push("/help");
              }}
            >
              <HelpCircle className="h-5 w-5" />
            </button>

            <div className="notification-area">
              <button
                className="top-chip notification-button glass relative"
                aria-label="通知"
                onClick={(event) => {
                  event.stopPropagation();
                  setIsNotificationsOpen((current) => !current);
                }}
              >
                <Bell className="h-5 w-5" />
                {overview?.notifications.length ? (
                  <span className="absolute right-1.5 top-1.5 grid h-5 w-5 place-items-center rounded-full bg-[#7df2bd] text-[10px] font-bold text-[#07533f]">
                    {overview.notifications.length}
                  </span>
                ) : null}
              </button>
              {isNotificationsOpen ? (
                <div className="notification-list glass">
                  <strong>通知</strong>
                  {overview?.notifications.length ? overview.notifications.map((item) => (
                    <button
                      type="button"
                      key={item.id}
                      onClick={(event) => {
                        event.stopPropagation();
                        router.push(item.href);
                      }}
                    >
                      <span>{item.title}</span>
                      <small>{item.message}</small>
                    </button>
                  )) : <p>当前没有待处理通知。</p>}
                </div>
              ) : null}
            </div>
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
            {stats.map((item) => {
              const liveStat = liveStats.get(item.key);
              const value = liveStat?.value;
              const displayValue = item.key === "average_resolution_hours" && typeof value === "number"
                ? `${value}h`
                : value?.toLocaleString("zh-CN") ?? "—";
              return (
              <article key={item.title} className="stat-card glass">
                <div className="stat-inner">
                  <img src={item.icon} alt="" className="stat-icon" />
                  <div>
                    <p className="stat-title">{item.title}</p>
                    <p className="stat-value">{displayValue}</p>
                    <p className="stat-delta">{liveStat?.detail ?? "正在加载实时数据"}</p>
                  </div>
                </div>
              </article>
              );
            })}
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

        </section>
      </section>
    </main>
  );
}
