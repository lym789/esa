"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Loader2, ShieldCheck } from "lucide-react";

import { login } from "@/lib/auth";
import { saveSession } from "@/lib/session";

const seedAccounts = [
  { email: "employee@example.com", role: "员工" },
  { email: "handler@example.com", role: "处理人" },
  { email: "approver@example.com", role: "审批人" },
  { email: "admin@example.com", role: "管理员" },
];

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("123456");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const result = await login(email, password);
      saveSession({
        accessToken: result.access_token,
        currentUser: result.user,
      });
      router.replace("/");
    } catch (loginError) {
      const message = loginError instanceof Error ? loginError.message : "";
      setError(message === "Failed to fetch" ? "无法连接后端服务，请确认后端已启动" : message || "登录失败，请稍后重试");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <div className="background-image" />
      <div className="background-depth" />
      <div className="background-shimmer" />

      <section className="login-shell glass">
        <div className="login-brand">
          <img src="/icons/logo.png" alt="JadeFlow AI 标志" className="login-logo" />
          <div>
            <p className="login-kicker">企业支持智能体</p>
            <h1>JadeFlow AI</h1>
          </div>
        </div>

        <div className="login-copy">
          <h2>登录企业支持工作台</h2>
          <p>使用种子账号进入仪表盘，继续验证知识库、工单、审批与智能体追踪链路。</p>
        </div>

        <form className="login-form" onSubmit={onSubmit}>
          <label>
            <span>邮箱</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
            />
          </label>

          <label>
            <span>密码</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </label>

          {error ? <p className="login-error">{error}</p> : null}

          <button className="login-submit" type="submit" disabled={isSubmitting}>
            {isSubmitting ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <ShieldCheck className="h-5 w-5" />
            )}
            <span>{isSubmitting ? "正在登录" : "登录"}</span>
            <ArrowRight className="ml-auto h-5 w-5" />
          </button>
        </form>

        <div className="seed-list">
          {seedAccounts.map((account) => (
            <button
              key={account.email}
              type="button"
              onClick={() => {
                setEmail(account.email);
                setPassword("123456");
                setError("");
              }}
            >
              <span>{account.role}</span>
              <strong>{account.email}</strong>
            </button>
          ))}
        </div>
      </section>
    </main>
  );
}
