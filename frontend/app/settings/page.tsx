"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, LogOut, Settings, ShieldCheck, UserCircle } from "lucide-react";

import { getMe, type CurrentUser } from "@/lib/auth";
import { clearSession, getStoredSession, saveSession, type StoredSession } from "@/lib/session";

const roleLabels: Record<string, string> = {
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

export default function SettingsPage() {
  const router = useRouter();
  const [session, setSession] = useState<StoredSession | null>(null);
  const [verifiedUser, setVerifiedUser] = useState<CurrentUser | null>(null);
  const [isChecking, setIsChecking] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const storedSession = getStoredSession();
    if (!storedSession) {
      router.replace("/login");
      return;
    }

    setSession(storedSession);
    getMe(storedSession.accessToken)
      .then((user) => {
        setVerifiedUser(user);
        saveSession({ ...storedSession, currentUser: user });
      })
      .catch((requestError) => setError(requestError instanceof Error ? requestError.message : "账号信息验证失败"))
      .finally(() => setIsChecking(false));
  }, [router]);

  function onLogout() {
    clearSession();
    router.replace("/login");
  }

  const currentUser = verifiedUser ?? session?.currentUser;
  const displayName = currentUser ? userNameLabels[currentUser.email] ?? currentUser.name : "正在检查登录状态";

  return (
    <main className="documents-page settings-page">
      <div className="background-image" />
      <div className="background-depth" />
      <div className="background-shimmer" />

      <section className="documents-shell settings-shell">
        <header className="documents-header">
          <button className="documents-back" type="button" onClick={() => router.push("/")}>
            <ArrowLeft className="h-4 w-4" />
            返回
          </button>
          <div>
            <p className="documents-kicker">系统设置</p>
            <h1>设置</h1>
          </div>
          <div className="documents-user glass">
            <span>{displayName}</span>
            <strong>{currentUser ? roleLabels[currentUser.role] ?? currentUser.role : "登录检查"}</strong>
          </div>
        </header>

        <section className="settings-grid">
          <article className="settings-card glass">
            <div className="documents-card-heading">
              <UserCircle className="h-5 w-5" />
              <h2>当前账号</h2>
            </div>

            {isChecking || !currentUser ? (
              <div className="documents-empty">正在读取当前登录账号...</div>
            ) : (
              <div className="settings-account-list">
                <div>
                  <span>姓名</span>
                  <strong>{displayName}</strong>
                </div>
                <div>
                  <span>邮箱</span>
                  <strong>{currentUser.email}</strong>
                </div>
                <div>
                  <span>角色</span>
                  <strong>{roleLabels[currentUser.role] ?? currentUser.role}</strong>
                </div>
                <div>
                  <span>数据来源</span>
                  <strong>已通过账户 API 实时验证</strong>
                </div>
              </div>
            )}
            {error ? <p className="documents-error">{error}</p> : null}
          </article>

          <article className="settings-card glass">
            <div className="documents-card-heading">
              <ShieldCheck className="h-5 w-5" />
              <h2>登录安全</h2>
            </div>

            <div className="settings-security-copy">
              <Settings className="h-5 w-5" />
              <p>退出后会清除本机保存的登录状态，再次访问工作台需要重新登录。</p>
            </div>

            <button className="settings-logout-button" type="button" onClick={onLogout}>
              <LogOut className="h-5 w-5" />
              退出登录
            </button>
          </article>
        </section>
      </section>
    </main>
  );
}
