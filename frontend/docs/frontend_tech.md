# JadeFlow AI 前端技术文档

## 1. 项目概述

**项目名称：** JadeFlow AI — Enterprise Support Agent

JadeFlow AI 是一个面向企业知识库与智能工单处理场景的 AI Agent 前端页面。当前版本主要是一个可展示的企业级 Dashboard 首页，用于呈现知识库、文档、工单、审批、Agent Trace、数据分析、系统集成和配置等功能入口。

页面整体采用青绿色山水背景、液态玻璃面板、自定义圆形图标和水波纹点击动效，适合作为 AI 应用工程师简历项目中的前端展示部分。

---

## 2. 技术选型

| 技术 | 用途 | 选择原因 |
|---|---|---|
| Next.js 14 | 前端框架 | 支持 App Router，适合后续扩展多页面和接入后端接口 |
| React 18 | UI 组件开发 | 组件化清晰，适合拆分 Dashboard、卡片、导航等模块 |
| TypeScript | 类型约束 | 提高代码可维护性，减少数据结构错误 |
| Tailwind CSS | 快速样式开发 | 适合快速构建布局和局部样式 |
| 自定义 CSS | 复杂视觉效果 | 用于液态玻璃、水波纹、背景高光和响应式细节 |
| Lucide React | 线性图标 | 用于导航、搜索、通知、设置等基础图标 |
| PNG 图标资源 | 视觉图标 | 用于统计卡片和功能卡片，增强页面风格统一性 |

---

## 3. 项目目录结构

```text
jadeflow-ai-icon-dashboard-v3-icons-fixed/
  app/
    layout.tsx
    page.tsx
    globals.css

  components/
    Dashboard.tsx

  lib/
    dashboard-data.ts

  public/
    jade-river-bg.png
    layout-reference.png
    icons/
      logo.png
      knowledge-articles.png
      open-tickets-stat.png
      resolved-tickets-stat.png
      avg-resolution-time.png
      knowledge-base.png
      documents.png
      tickets.png
      approvals.png
      agent-trace.png
      analytics.png
      integrations.png
      settings.png

  standalone/
    index.html
    jade-river-bg.png
    icons/

  package.json
  tsconfig.json
  tailwind.config.ts
  postcss.config.js
  next.config.mjs
  README.md
```

Next.js 的静态资源访问规则是：只有 `public/` 目录会被作为站点根路径暴露。当前项目中的资源路径对应关系如下：

```text
public/jade-river-bg.png   -> /jade-river-bg.png
public/icons/logo.png      -> /icons/logo.png
public/icons/*.png         -> /icons/*.png
```

`standalone/` 目录是无依赖预览版，里面的 `index.html` 使用相对路径加载同级资源。如果单独移动 `index.html`，会导致背景图或图标找不到。

---

## 4. 核心文件说明

### 4.1 `app/page.tsx`

页面入口文件，只负责加载 Dashboard 主组件。

```tsx
import { Dashboard } from "@/components/Dashboard";

export default function HomePage() {
  return <Dashboard />;
}
```

### 4.2 `components/Dashboard.tsx`

主页面组件，负责组织完整页面结构，包括：

- 背景图层
- 背景高光层
- 点击水波纹层
- 左侧导航栏
- 顶部搜索栏
- Hero 标题区
- 统计卡片区
- 功能卡片区
- 底部安全提示条

### 4.3 `lib/dashboard-data.ts`

页面数据配置文件，用来集中管理：

- 左侧导航菜单
- 统计卡片数据
- 功能卡片数据
- 图标资源路径
- 侧边栏底部按钮

这样可以避免把大量静态数据直接写死在 JSX 结构里，后续接入接口时也更方便。

### 4.4 `app/globals.css`

全局样式文件，主要负责：

- 全屏背景图
- 玻璃拟态效果
- 页面布局
- 卡片 Grid 布局
- 水波纹动画
- 背景高光动画
- 小屏高度适配
- 滚动区域修复

---

## 5. 页面布局设计

当前页面整体分为两大区域：

```text
左侧 Sidebar + 右侧 Main Area
```

### 5.1 左侧导航栏

左侧区域包含：

- Logo
- 产品名 JadeFlow AI
- Enterprise 标签
- 导航菜单
- 用户信息
- 底部快捷按钮

导航项包括：

```text
Overview
Knowledge Base
Documents
Tickets
Approvals
Agent Trace
Analytics
Integrations
Settings
```

### 5.2 右侧主内容区

右侧区域包含：

1. 顶部搜索栏
2. AI Agent Online 状态
3. 帮助按钮
4. 通知按钮
5. Hero 标题区
6. Ask AI Assistant 按钮
7. 四个统计卡片
8. 八个功能卡片
9. 底部安全提示条

右侧主区域使用自然流式布局，避免不同屏幕高度下卡片重叠。

核心样式：

```css
.main-area {
  position: absolute;
  left: 324px;
  right: 24px;
  top: 24px;
  bottom: 24px;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}
```

---

## 6. 视觉设计说明

### 6.1 背景图

背景图文件：

```text
public/jade-river-bg.png
```

该图为 16:9 比例，因此页面中直接使用：

```css
.background-image {
  background-image: url("/jade-river-bg.png");
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}
```

说明：

- `cover` 不会拉伸图片；
- 16:9 屏幕下基本不会裁切；
- 非 16:9 屏幕会轻微裁切边缘；
- 不使用 `100% 100%`，避免图片被压缩或拉伸。

### 6.2 液态玻璃效果

页面中大量使用统一的 `.glass` 类，实现半透明、模糊、高光和阴影效果。

```css
.glass {
  border: 1px solid rgba(230, 255, 238, 0.34);
  background:
    linear-gradient(145deg, rgba(237, 255, 243, 0.22), rgba(113, 211, 173, 0.10) 48%, rgba(255,255,255,0.06)),
    radial-gradient(circle at 24% 16%, rgba(255,255,255,0.34), transparent 24%);
  backdrop-filter: blur(20px) saturate(160%);
  box-shadow:
    0 24px 60px rgba(0, 25, 20, 0.26),
    inset 0 1px 0 rgba(255,255,255,0.48),
    inset 0 -18px 32px rgba(36, 168, 124, 0.08);
}
```

该样式用于：

- Sidebar
- 搜索栏
- 顶部状态按钮
- 统计卡片
- 功能卡片
- 底部提示条

---

## 7. 图标资源说明

图标资源存放在：

```text
public/icons/
```

图标对应关系如下：

| 文件名 | 用途 |
|---|---|
| `logo.png` | 左上角产品 Logo |
| `knowledge-articles.png` | Knowledge Articles 统计卡 |
| `open-tickets-stat.png` | Open Tickets 统计卡 |
| `resolved-tickets-stat.png` | Resolved Tickets 统计卡 |
| `avg-resolution-time.png` | Avg. Resolution Time 统计卡 |
| `knowledge-base.png` | Knowledge Base 功能卡 |
| `documents.png` | Documents 功能卡 |
| `tickets.png` | Tickets 功能卡 |
| `approvals.png` | Approvals 功能卡 |
| `agent-trace.png` | Agent Trace 功能卡 |
| `analytics.png` | Analytics 功能卡 |
| `integrations.png` | Integrations 功能卡 |
| `settings.png` | 设置功能卡 |

图标已做透明背景处理，避免显示棋盘格背景。

---

## 8. 数据结构设计

当前页面数据主要写在 `lib/dashboard-data.ts` 中。

### 8.1 导航菜单

```ts
export const navItems = [
  { label: "总览", icon: Home, active: true },
  { label: "知识库", icon: BookOpen },
  { label: "文档", icon: FileText },
  { label: "工单", icon: Ticket },
  { label: "审批", icon: CheckSquare },
  { label: "智能体追踪", icon: Gauge },
  { label: "数据分析", icon: BarChart3 },
  { label: "系统集成", icon: Link2 },
  { label: "设置", icon: Settings, href: "/settings" },
];
```

### 8.2 统计卡片

```ts
export const stats = [
  {
    title: "Knowledge Articles",
    value: "12,842",
    delta: "↗ 12.6% vs last 30 days",
    icon: "/icons/knowledge-articles.png",
  },
  ...
];
```

### 8.3 功能卡片

```ts
export const features = [
  {
    title: "Knowledge Base",
    desc: "构建与管理企业知识库，支持 AI 精准问答与检索。",
    icon: "/icons/knowledge-base.png",
  },
  ...
];
```

这种写法方便后续替换为接口返回数据。

---

## 9. 动效实现

### 9.1 点击水波纹

页面点击时会在点击位置生成水波纹。

核心逻辑位于 `Dashboard.tsx`：

```tsx
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
```

CSS 动画：

```css
@keyframes rippleExpand {
  0% {
    transform: translate(-50%, -50%) scale(0.06);
    opacity: 0.75;
  }
  58% {
    opacity: 0.28;
  }
  100% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 0;
  }
}
```

### 9.2 背景高光流动

通过 `.background-shimmer` 实现轻微高光流动：

```css
.background-shimmer {
  animation: softShimmer 8s ease-in-out infinite alternate;
}
```

作用：

- 增强页面动态感；
- 与水面背景风格一致；
- 不影响主要内容阅读。

---

## 10. 响应式与布局修复

上一版页面中，统计卡片和功能卡片使用固定绝对定位，导致在不同窗口高度或浏览器缩放下出现重叠。

当前版本已修复：

- 右侧内容改为 `.main-area` 自然文档流；
- 统计区和功能区使用 `margin-top` 顺序排列；
- 页面高度不足时右侧区域可以滚动；
- 小屏高度下自动压缩卡片、图标和间距。

小高度适配示例：

```css
@media (max-height: 860px) {
  .hero {
    margin-top: 44px;
  }

  .stats-grid {
    margin-top: 48px;
  }

  .stat-card {
    min-height: 104px;
    padding: 16px;
  }

  .feature-card {
    min-height: 112px;
    padding: 16px;
  }
}
```

---

## 11. 登录流接入

当前版本已接入 Day 2 登录能力：

- `/login`：登录页面，默认填入 `admin@example.com` / `123456`；
- `/`：Dashboard 页面，未登录时会自动跳转到 `/login`；
- `lib/auth.ts`：封装 `/api/auth/login` 与 `/api/auth/me`；
- `lib/session.ts`：用 `localStorage` 保存 `accessToken` 和 `currentUser`；
- `components/Dashboard.tsx`：从登录用户读取姓名、角色和头像缩写。

登录成功后，前端保存：

```ts
{
  accessToken: string;
  currentUser: {
    id: number;
    email: string;
    name: string;
    role: "employee" | "handler" | "approver" | "admin";
  };
}
```

种子账号：

```text
employee@example.com / 123456
handler@example.com / 123456
approver@example.com / 123456
admin@example.com / 123456
```

## 12. 运行方式

### 12.1 安装依赖

```bash
npm install
```

### 12.2 启动开发环境

```bash
npm run dev
```

默认访问：

```text
http://localhost:3000
```

### 12.3 构建生产版本

```bash
npm run build
```

### 12.4 启动生产服务

```bash
npm run start
```

---

## 13. 单文件预览版

项目提供了一个无需安装依赖的 HTML 版本：

```text
standalone/index.html
```

可直接双击打开，用于快速预览页面视觉效果。

---

## 14. 后续扩展建议

### 14.1 接入真实后端接口

建议新增接口：

```text
GET /api/dashboard/stats
GET /api/knowledge/summary
GET /api/tickets/recent
GET /api/agent/traces
```

将当前写死的统计数据替换为接口返回数据。

### 14.2 增加知识库问答页面

建议路由：

```text
/knowledge/ask
```

功能：

- 输入问题；
- 调用 RAG 问答接口；
- 展示答案；
- 展示引用文档；
- 支持多轮追问。

### 14.3 增加工单中心页面

建议路由：

```text
/tickets
```

功能：

- 工单列表；
- 创建工单；
- AI 自动分类；
- AI 推荐优先级；
- 工单状态流转。

### 14.4 增加执行链路追踪页面

建议路由：

```text
/agent-trace
```

功能：

- 展示 Agent 执行步骤；
- 展示工具调用记录；
- 展示知识检索过程；
- 展示审批流转信息；
- 支持审计与回放。

### 14.5 增加数据可视化

可以接入：

- ECharts
- Recharts
- AntV

展示：

- 工单趋势；
- 平均响应时长；
- 知识库命中率；
- Agent 调用成功率；
- 用户满意度。

---

## 15. 简历描述建议

可在简历中这样描述：

> 设计并实现企业级 AI Agent Dashboard 前端页面，基于 Next.js、React、TypeScript 和 Tailwind CSS 构建，采用液态玻璃视觉风格和青绿色山水背景，完成知识库、文档、工单、审批、智能体追踪、数据分析、系统集成、设置等核心功能入口设计。通过配置化数据结构管理导航、统计卡片和功能卡片，并实现点击水波纹、背景高光流动、响应式滚动布局等交互效果，为后续接入 RAG 问答、智能工单分派和 Agent 执行链路追踪提供前端基础。

---

## 16. 当前版本总结

当前版本已经完成：

- 16:9 全屏背景图；
- 左侧玻璃导航栏；
- 顶部搜索和状态栏；
- Hero 产品介绍区；
- 4 个统计卡片；
- 8 个功能卡片；
- 自定义图标接入；
- 液态玻璃风格；
- 点击水波纹动效；
- 背景高光流动；
- 小屏高度下防重叠布局；
- Next.js 版本和 standalone HTML 版本。

该前端页面可以作为 AI 应用工程师简历项目中的前端展示基础，后续可继续扩展真实业务页面和后端 Agent 能力。
