import {
  BarChart3,
  Bell,
  BookOpen,
  CheckSquare,
  FileText,
  Gauge,
  Home,
  Link2,
  Search,
  Settings,
  ShieldQuestion,
  Sparkles,
  Ticket,
} from "lucide-react";

type FeatureItem = {
  title: string;
  desc: string;
  icon: string;
  href?: string;
};

export const navItems = [
  { label: "总览", icon: Home, active: true },
  { label: "知识库", icon: BookOpen, href: "/chat" },
  { label: "文档", icon: FileText, href: "/admin/documents" },
  { label: "工单", icon: Ticket, href: "/tickets" },
  { label: "审批", icon: CheckSquare, href: "/approvals" },
  { label: "智能体追踪", icon: Gauge, href: "/admin/traces" },
  { label: "数据分析", icon: BarChart3, href: "/analytics" },
  { label: "系统集成", icon: Link2, href: "/integrations" },
  { label: "设置", icon: Settings, href: "/settings" },
];

export const stats = [
  {
    key: "knowledge_articles",
    title: "知识文章",
    icon: "/icons/knowledge-articles.png",
  },
  {
    key: "open_tickets",
    title: "待处理工单",
    icon: "/icons/open-tickets-stat.png",
  },
  {
    key: "resolved_tickets",
    title: "已解决工单",
    icon: "/icons/resolved-tickets-stat.png",
  },
  {
    key: "average_resolution_hours",
    title: "平均解决时长",
    icon: "/icons/avg-resolution-time.png",
  },
];

export const features: FeatureItem[] = [
  {
    title: "知识库",
    desc: "构建与管理企业知识库，支持 AI 精准问答与检索。",
    icon: "/icons/knowledge-base.png",
    href: "/chat",
  },
  {
    title: "文档",
    desc: "集中管理文档与资源，支持版本、权限与协作。",
    icon: "/icons/documents.png",
    href: "/admin/documents",
  },
  {
    title: "工单",
    desc: "智能工单管理与自动分派，提升响应与处理效率。",
    icon: "/icons/tickets.png",
    href: "/tickets",
  },
  {
    title: "审批",
    desc: "流程审批与合规管理，确保业务规范与可追溯。",
    icon: "/icons/approvals.png",
    href: "/approvals",
  },
  {
    title: "智能体追踪",
    desc: "追踪 AI 决策过程与执行轨迹，提升透明与可解释性。",
    icon: "/icons/agent-trace.png",
    href: "/admin/traces",
  },
  {
    title: "数据分析",
    desc: "多维数据分析与洞察，驱动服务与业务持续优化。",
    icon: "/icons/analytics.png",
    href: "/analytics",
  },
  {
    title: "系统集成",
    desc: "连接企业系统与第三方应用，打通数据与流程。",
    icon: "/icons/integrations.png",
    href: "/integrations",
  },
  {
    title: "设置",
    desc: "查看当前账号与服务配置，管理登录状态。",
    icon: "/icons/settings.png",
    href: "/settings",
  },
];

export const topIcons = {
  Search,
  Bell,
  ShieldQuestion,
  Sparkles,
};
