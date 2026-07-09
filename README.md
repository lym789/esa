# 企业支持智能体（Enterprise Support Agent）

Enterprise Support Agent 是一个企业知识库问答、智能工单、人工审批和 Agent Trace 的 AI Agent MVP 项目。

本项目按照 `from-zero-build-guide.md` 逐步推进。Day 1 完成了可运行底座：FastAPI 后端、Next.js 前端、PostgreSQL + pgvector、Docker Compose 和环境变量。Day 2 完成了数据库用户、JWT 登录、RBAC 依赖、种子账号，以及 JadeFlow AI Dashboard 的登录流程。Day 3 完成了管理员文档上传、本地存储、文档记录和最小文档管理页。Day 4 完成了文档解析、chunk 切分、状态流转和重新解析。Day 5 完成了本地 embedding、chunk 向量存储、相似度检索和引用格式化。Day 6 完成了 Chat API、RAG 问答、引用来源和无依据拒答。Day 7 完成了工单草稿生成、普通工单创建和按角色过滤的工单列表/详情接口。Day 8 完成了 urgent 工单审批中断、审批通过后执行和审批拒绝停止执行。Day 9 完成了 Agent Trace 后端记录与管理员查询接口。Day 10 完成了管理员 Trace 前端页面。Day 11 完成了前端工单页面。Day 12 完成了前端审批页面。Day 13 完成了工单详情页和状态流转。Day 14 完成了工单评论。Day 15 完成了工单分配和评论作者展示。Day 16 完成了设置页和退出登录入口。Day 17 完成了 AI 助手前端、首页左侧导航接入和工单手动优先级选择。Day 18 完成了工单筛选分页、审批筛选跳转和本地启动脚本整理。

## 快速启动（推荐：esa Python 环境）

当前本地开发推荐后端和前端分别启动：后端运行在 `esa` conda 环境，数据库使用本机已启动的 PostgreSQL 或 Docker PostgreSQL，前端用 Next.js 开发服务。

### 0. 脚本辅助

如果只是想按当前推荐流程启动，可以在项目根目录执行：

```bash
./scripts/start-local.sh
```

它会尝试启动 Docker PostgreSQL、`esa` conda 环境下的后端，以及 3000 端口前端。日志会写到 `.local-run/logs/`。

检查端口：

```bash
./scripts/check-ports.sh
```

停止本地服务：

```bash
./scripts/stop-local.sh
```

下面的手动步骤适合你想分别打开后端和前端、或需要看实时日志时使用。

### 1. 检查并清理旧端口

先检查端口是否被旧服务占用：

```bash
lsof -nP -iTCP:8000 -sTCP:LISTEN
lsof -nP -iTCP:3000 -sTCP:LISTEN
lsof -nP -iTCP:5173 -sTCP:LISTEN
```

如果发现旧的前端进程来自废纸篓目录，例如 `/Users/liuyiming/.Trash/frontend` 或 `/Users/liuyiming/.Trash/frontend 19.44.37`，可以关闭对应 PID：

```bash
kill <PID>
```

如果普通关闭无效，再使用：

```bash
kill -9 <PID>
```

`Ctrl + C` 只会关闭当前终端前台运行的服务，不会自动关闭其他终端、废纸篓目录、Docker 或残留的子进程。

### 2. 启动后端

打开第一个终端：

```bash
cd /Users/liuyiming/Desktop/project/ai_agent/backend
conda activate esa

export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/enterprise_support_agent"
export FRONTEND_ORIGIN="http://localhost:3000"
export JWT_SECRET_KEY="replace-with-dev-secret"
export STORAGE_DIR="app/storage"
export RAG_SIMILARITY_THRESHOLD="0.1"

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

如果前端临时改用 `5173` 等其他端口，请把 `FRONTEND_ORIGIN` 改成对应地址后重新启动后端。

后端检查地址：

- http://localhost:8000/health
- http://localhost:8000/db/health

### 3. 启动前端

打开第二个终端。默认使用 `3000`：

```bash
cd /Users/liuyiming/Desktop/project/ai_agent/frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```

访问：

- 登录页：http://localhost:3000/login
- 仪表盘：http://localhost:3000
- AI 助手：http://localhost:3000/chat
- 设置页：http://localhost:3000/settings

如果 `3000` 被旧前端或其他服务占用，可以临时换到 `5173`：

```bash
cd /Users/liuyiming/Desktop/project/ai_agent/frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev -- -p 5173
```

此时访问：

- 登录页：http://localhost:5173/login
- 仪表盘：http://localhost:5173
- AI 助手：http://localhost:5173/chat
- 设置页：http://localhost:5173/settings

使用备用端口时，后端也要把 `FRONTEND_ORIGIN` 改成同一个前端地址。

### 4. 登录账号

所有种子账号的密码都是 `123456`：

- `employee@example.com`
- `handler@example.com`
- `approver@example.com`
- `admin@example.com`

### 5. 停止服务

在后端和前端对应的终端里分别按：

```text
Ctrl + C
```

如果端口仍然被占用，使用 `lsof` 查出 PID 后再 `kill`。

## Docker 启动（可选）

如果需要使用 Docker Compose 一次性启动数据库、后端和前端：

```bash
cp .env.example .env
docker compose up --build
```

Docker Compose 默认服务地址：

- 前端：http://localhost:3000
- 登录页：http://localhost:3000/login
- 后端健康检查：http://localhost:8000/health
- 数据库健康检查：http://localhost:8000/db/health
- PostgreSQL：localhost:5432

如果本机端口已被占用，可以覆盖宿主机端口：

```bash
POSTGRES_PORT=5433 BACKEND_PORT=8001 FRONTEND_PORT=3001 FRONTEND_ORIGIN=http://localhost:3001 NEXT_PUBLIC_API_BASE_URL=http://localhost:8001 docker compose up --build
```

## 前端资源目录

Next.js 前端的静态资源放在 `frontend/public/` 下，页面中会以站点根路径访问：

- `frontend/public/jade-river-bg.png` -> `/jade-river-bg.png`
- `frontend/public/icons/logo.png` -> `/icons/logo.png`
- `frontend/public/icons/*.png` -> `/icons/*.png`

单文件预览版的资源放在 `frontend/standalone/` 下。如果直接打开 `frontend/standalone/index.html`，不要只移动 HTML 文件，需要保留同级的 `jade-river-bg.png` 和 `icons/` 目录。

## 种子账号

所有种子账号的密码都是 `123456`。

- `employee@example.com`
- `handler@example.com`
- `approver@example.com`
- `admin@example.com`

## 当前范围

- `backend/`：FastAPI 后端，包含 `/health` 和 `/db/health`。
- `backend/app/api/auth.py`：登录接口 `/api/auth/login` 和当前用户接口 `/api/auth/me`。
- `backend/app/models/user.py`：Day 2 的 `users` 数据模型。
- `backend/app/api/documents.py`：文档上传、列表、详情、删除和重新解析接口。
- `backend/app/models/document.py`：Day 3 的 `documents` 数据模型。
- `backend/app/models/document_chunk.py`：Day 4 的 `document_chunks` 数据模型。
- `backend/app/services/document_processing_service.py`：Day 4 文档解析与 chunk 切分服务。
- `backend/app/services/rag_service.py`：Day 5 embedding、相似度检索和引用格式化服务。
- `backend/app/api/search.py`：Day 5 检索接口 `/api/search`。
- `backend/app/models/conversation.py`：Day 6 的 `conversations` 数据模型。
- `backend/app/models/message.py`：Day 6 的 `messages` 数据模型。
- `backend/app/services/chat_service.py`：Day 6 Chat 与 RAG 问答服务。
- `backend/app/api/chat.py`：Day 6 Chat 接口 `/api/chat/*`。
- `backend/app/models/ticket.py`：Day 7 的 `tickets` 数据模型。
- `backend/app/models/ticket_comment.py`：Day 14 的 `ticket_comments` 数据模型。
- `backend/app/services/ticket_service.py`：Day 7 工单草稿生成、编号和权限过滤服务，Day 13 增加工单状态更新，Day 15 增加工单分配。
- `backend/app/api/tickets.py`：Day 7 工单接口 `/api/tickets/*`，Day 13 增加状态更新接口，Day 14 增加评论接口，Day 15 增加分配接口。
- `backend/app/models/approval.py`：Day 8 的 `approvals` 数据模型。
- `backend/app/services/approval_service.py`：Day 8 审批创建、通过、拒绝和幂等执行服务。
- `backend/app/api/approvals.py`：Day 8 审批接口 `/api/approvals/*`。
- `backend/app/models/agent_trace.py`：Day 9 的 `agent_traces` 数据模型。
- `backend/app/services/trace_service.py`：Day 9 Trace 写入与查询服务。
- `backend/app/api/traces.py`：Day 9 管理员 Trace 查询接口 `/api/traces/*`。
- `frontend/`：Next.js JadeFlow AI Dashboard，并带登录保护和文档管理页。
- `frontend/app/settings/page.tsx`：Day 16 设置页，展示当前账号并提供退出登录。
- `frontend/components/Dashboard.tsx`：Dashboard 首页和导航入口，Day 16 将“设置”入口连接到 `/settings`，Day 17 将 AI 助手按钮连接到 `/chat`。
- `frontend/lib/chat.ts`：Day 17 Chat 前端 API client。
- `frontend/app/chat/page.tsx`：Day 17 AI 助手页面，支持对话、发送消息和引用来源展示。
- `frontend/app/admin/documents/page.tsx`：管理员文档管理页面。
- `frontend/lib/traces.ts`：Day 10 Trace 前端 API client。
- `frontend/app/admin/traces/page.tsx`：Day 10 管理员智能体追踪页面。
- `frontend/lib/tickets.ts`：Day 11 工单前端 API client，Day 13 增加工单详情和状态更新方法，Day 14 增加评论方法，Day 15 增加处理人列表和分配方法。
- `frontend/app/tickets/page.tsx`：Day 11 工单中心页面，Day 17 支持手动调整草稿优先级并明确显示创建按钮，Day 18 增加搜索、筛选和分页。
- `frontend/app/tickets/[ticketId]/page.tsx`：Day 13 工单详情和状态流转页面，Day 14 增加工单评论，Day 15 增加管理员分配处理人。
- `frontend/lib/approvals.ts`：Day 12 审批前端 API client。
- `frontend/app/approvals/page.tsx`：Day 12 审批中心页面，Day 18 增加审批状态筛选和审批结果跳转工单。
- `scripts/check-ports.sh`：检查本地常用端口占用。
- `scripts/start-local.sh`：按当前推荐流程启动数据库、后端和前端。
- `scripts/stop-local.sh`：停止本地后端、前端和 Docker 数据库。
- `docker-compose.yml`：PostgreSQL/pgvector、后端和前端服务编排。
- `.env.example`：本地开发环境变量模板。
- `docs/day1-project-initialization.md`：Day 1 初始化记录。
- `docs/day2-auth.md`：Day 2 登录和种子账号说明。
- `docs/day3-document-upload.md`：Day 3 文档上传说明。
- `docs/day4-document-processing.md`：Day 4 文档解析与 chunk 切分说明。
- `docs/day5-embedding-search.md`：Day 5 embedding 与检索说明。
- `docs/day6-chat-rag.md`：Day 6 Chat 与 RAG 问答说明。
- `docs/day7-ticket-agent.md`：Day 7 工单 Agent 与基础工单接口说明。
- `docs/day8-approval-workflow.md`：Day 8 审批闭环说明。
- `docs/day9-agent-trace.md`：Day 9 Agent Trace 后端能力说明。
- `docs/day10-frontend-traces.md`：Day 10 前端 Trace 页面说明。
- `docs/day11-frontend-tickets.md`：Day 11 前端工单页面说明。
- `docs/day12-frontend-approvals.md`：Day 12 前端审批页面说明。
- `docs/day13-ticket-detail-status.md`：Day 13 工单详情和状态流转说明。
- `docs/day14-ticket-comments.md`：Day 14 工单评论说明。
- `docs/day15-ticket-assignment.md`：Day 15 工单分配和评论作者展示说明。
- `docs/day16-settings-logout.md`：Day 16 设置页和退出登录说明。
- `docs/day17-frontend-chat-nav-ticket-create.md`：Day 17 AI 助手、左侧导航和工单创建体验说明。
- `docs/day18-ticket-approval-startup.md`：Day 18 工单列表、审批跳转和本地启动整理说明。
- `docs/day19-llm-integration.md`：Day 19 大模型接入设计和功能规划说明。

## 本地开发

本地开发默认沿用上面的推荐方式：后端使用 `esa` conda 环境，前端使用 Next.js 开发服务。不要再额外创建 `.venv`，除非你明确想维护一套独立 Python 虚拟环境。

后端：

```bash
cd /Users/liuyiming/Desktop/project/ai_agent/backend
conda activate esa
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

前端：

```bash
cd /Users/liuyiming/Desktop/project/ai_agent/frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```

如果在 Docker 外直接运行后端，需要把 `DATABASE_URL` 指向可访问的数据库。当前本地默认使用 `localhost:5432`；Docker Compose 内部才使用 `db` 作为数据库主机名。

## 下一阶段

后续阶段将补更完整的演示数据、审批通知和数据分析页面，让工单从创建、审批到处理形成更完整的端到端闭环。
