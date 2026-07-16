"use client";

import { useRouter } from "next/navigation";
import { ArrowLeft, BookOpen, HelpCircle, Search, Sparkles, Ticket } from "lucide-react";

const helpItems = [
  { icon: Search, title: "全局搜索", text: "在首页顶部输入关键词，可检索知识片段、文档名称和你有权限查看的工单。" },
  { icon: Sparkles, title: "AI 助手", text: "AI 助手基于已上传并完成解析的知识文档回答，同时展示引用来源。" },
  { icon: Ticket, title: "工单与审批", text: "普通工单会直接创建；紧急工单会进入人工审批流程。" },
  { icon: BookOpen, title: "知识库", text: "管理员上传文档后，系统解析内容并建立检索索引，供所有已登录用户查询。" },
];

export default function HelpPage() {
  const router = useRouter();
  return (
    <main className="documents-page">
      <div className="background-image" />
      <div className="background-depth" />
      <section className="documents-shell">
        <header className="documents-header">
          <button className="documents-back" type="button" onClick={() => router.push("/")}>
            <ArrowLeft className="h-4 w-4" />返回
          </button>
          <div><p className="documents-kicker">使用说明</p><h1>帮助中心</h1></div>
          <div className="documents-user glass"><HelpCircle className="h-5 w-5" /><strong>Midori</strong></div>
        </header>
        <section className="help-grid">
          {helpItems.map((item) => {
            const Icon = item.icon;
            return <article className="settings-card glass" key={item.title}><Icon className="h-6 w-6" /><h2>{item.title}</h2><p>{item.text}</p></article>;
          })}
        </section>
      </section>
    </main>
  );
}
