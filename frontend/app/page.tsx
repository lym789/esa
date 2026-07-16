"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Dashboard } from "@/components/Dashboard";
import { getStoredSession, type StoredSession } from "@/lib/session";

export default function HomePage() {
  const router = useRouter();
  const [session, setSession] = useState<StoredSession | null>(null);
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    const storedSession = getStoredSession();
    if (!storedSession) {
      router.replace("/login");
      return;
    }

    setSession(storedSession);
    setIsChecking(false);
  }, [router]);

  if (isChecking || !session) {
    return (
      <main className="login-page">
        <div className="background-image" />
        <div className="background-depth" />
        <div className="login-loading glass">正在检查登录状态...</div>
      </main>
    );
  }

  return <Dashboard currentUser={session.currentUser} accessToken={session.accessToken} />;
}
