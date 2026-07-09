# Enterprise Support Agent 从 0 搭建指南

> 本文基于 `prd-v1.md` 编写，目标是把两周 MVP 从空目录一步步搭建出来。
> 项目核心闭环：文档上传 -> 文档解析与向量化 -> RAG 问答 -> 工单草稿 -> 用户确认 -> 风险审批 -> 工单执行 -> Agent Trace。

---

## 1. MVP 边界

### 必须完成

- 用户登录与角色识别：`employee`、`handler`、`approver`、`admin`
- 管理员上传 Markdown、TXT、简单 PDF 文档
- 文档解析、chunk 切分、embedding、写入 PostgreSQL + pgvector
- 员工在 Chat 页面进行知识库问答
- AI 回答必须带引用来源；没有可靠来源时拒答
- Agent 识别工单意图并生成工单草稿
- 用户确认后创建工单
- 高风险操作进入人工审批
- 审批通过后执行原工具调用
- 管理员查看 Agent Trace
- Docker Compose 本地启动

### 暂不实现

- 多租户、企业 SSO、复杂权限系统
- Celery、Redis、OpenTelemetry、LangSmith、Ragas
- DOCX、Excel、OCR、复杂表格解析
- 外部工单系统、邮件、飞书、Slack、Jira 集成
- 复杂多 Agent 协作和可视化工作流编排

---

## 2. 推荐技术栈

| 模块 | 技术 | 说明 |
| --- | --- | --- |
| 前端 | Next.js + React + TypeScript | 实现登录、Chat、工单、审批、文档、Trace 页面 |
| UI | Tailwind CSS + shadcn/ui | 快速搭建可演示后台界面 |
| 后端 | Python + FastAPI | 适合 API 与 AI 应用开发 |
| ORM | SQLAlchemy + Alembic | 管理业务表和迁移 |
| 数据库 | PostgreSQL | 存储用户、文档、工单、审批、Trace |
| 向量检索 | pgvector | 存储和检索 chunk embedding |
| RAG | 自定义轻量 RAG Service 或 LlamaIndex | MVP 优先保证链路清晰 |
| Agent | LangGraph 或轻量状态机 | 实现意图识别、工具调用、审批中断 |
| 文件存储 | 本地 `storage/` 目录 | 保存上传原始文件 |
| 异步任务 | FastAPI BackgroundTasks | 文档上传后后台解析 |
| 鉴权 | JWT + 简单 RBAC | MVP 足够 |
| 部署 | Docker Compose | 本地一键启动 |

建议 MVP 先用“自定义轻量 RAG Service + 轻量状态机”，等主链路跑通后再把 LangGraph 接入。这样能降低第一周的集成风险。

---

## 3. 目录结构

从空目录创建以下结构：

```text
enterprise-support-agent/
  backend/
    app/
      main.py
      core/
        config.py
        security.py
        logging.py
      api/
        auth.py
        chat.py
        documents.py
        tickets.py
        approvals.py
        traces.py
      agents/
        graph.py
        nodes.py
        prompts.py
        schemas.py
      services/
        auth_service.py
        document_service.py
        rag_service.py
        ticket_service.py
        approval_service.py
        trace_service.py
      tools/
        rag_tools.py
        ticket_tools.py
        policy.py
      models/
        user.py
        document.py
        chunk.py
        conversation.py
        message.py
        ticket.py
        approval.py
        trace.py
      schemas/
        auth.py
        chat.py
        document.py
        ticket.py
        approval.py
        trace.py
      db/
        session.py
        base.py
        seed.py
      storage/
    alembic/
    tests/
    pyproject.toml
    alembic.ini
    Dockerfile
  frontend/
    app/
      login/
      chat/
      tickets/
      approvals/
      admin/
        documents/
        traces/
    components/
    lib/
    package.json
    Dockerfile
  docker-compose.yml
  .env.example
  README.md
```

---

## 4. 初始化项目

### 4.1 创建根目录

```bash
mkdir enterprise-support-agent
cd enterprise-support-agent
mkdir backend frontend
```

### 4.2 初始化后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn sqlalchemy alembic psycopg[binary] pgvector pydantic pydantic-settings python-jose[cryptography] passlib[bcrypt] python-multipart openai pypdf loguru pytest httpx
pip freeze > requirements.txt
cd ..
```

后端第一阶段先安装最小依赖。后续如果确定使用 LangGraph 或 LlamaIndex，再补充：

```bash
pip install langgraph llama-index
```

### 4.3 初始化前端

```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir false --import-alias "@/*"
npx shadcn@latest init
cd ..
```

建议安装常用前端依赖：

```bash
cd frontend
npm install axios zustand lucide-react
npx shadcn@latest add button card input textarea badge table dialog tabs select toast
cd ..
```

---

## 5. 环境变量

在根目录创建 `.env.example`：

```env
POSTGRES_DB=enterprise_support_agent
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=db
POSTGRES_PORT=5432

DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/enterprise_support_agent

JWT_SECRET_KEY=replace-with-dev-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

OPENAI_API_KEY=replace-with-your-key
LLM_MODEL=gpt-4.1-mini
EMBEDDING_MODEL=text-embedding-3-small

STORAGE_DIR=app/storage
CHUNK_SIZE=800
CHUNK_OVERLAP=120
RAG_TOP_K=5
RAG_SIMILARITY_THRESHOLD=0.75

NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

本地开发时复制一份：

```bash
cp .env.example .env
```

---

## 6. Docker Compose

根目录创建 `docker-compose.yml`：

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    container_name: esa-db
    environment:
      POSTGRES_DB: enterprise_support_agent
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d enterprise_support_agent"]
      interval: 5s
      timeout: 5s
      retries: 10

  backend:
    build:
      context: ./backend
    container_name: esa-backend
    env_file:
      - .env
    ports:
      - "8000:8000"
    volumes:
      - ./backend/app/storage:/app/app/storage
    depends_on:
      db:
        condition: service_healthy

  frontend:
    build:
      context: ./frontend
    container_name: esa-frontend
    environment:
      NEXT_PUBLIC_API_BASE_URL: http://localhost:8000
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  postgres_data:
```

开发早期可以只启动数据库：

```bash
docker compose up -d db
```

等前后端 Dockerfile 完成后，再启动完整服务：

```bash
docker compose up --build
```

---

## 7. 数据库搭建

### 7.1 初始化 Alembic

```bash
cd backend
alembic init alembic
```

在 Alembic 的首个迁移里启用 pgvector：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 7.2 建表顺序

建议按以下顺序创建模型和迁移：

1. `users`
2. `documents`
3. `document_chunks`
4. `conversations`
5. `messages`
6. `tickets`
7. `ticket_comments`
8. `approvals`
9. `agent_traces`

### 7.3 核心索引

`document_chunks.embedding` 建向量索引：

```sql
CREATE INDEX idx_document_chunks_embedding
ON document_chunks USING hnsw (embedding vector_cosine_ops);
```

常用业务查询索引：

```sql
CREATE INDEX idx_documents_status ON documents (status);
CREATE INDEX idx_tickets_requester_id ON tickets (requester_id);
CREATE INDEX idx_tickets_assignee_id ON tickets (assignee_id);
CREATE INDEX idx_approvals_status ON approvals (status);
CREATE INDEX idx_agent_traces_conversation_id ON agent_traces (conversation_id);
```

### 7.4 种子账号

创建 `backend/app/db/seed.py`，写入 4 个测试账号：

| 角色 | 邮箱 | 密码 |
| --- | --- | --- |
| employee | employee@example.com | 123456 |
| handler | handler@example.com | 123456 |
| approver | approver@example.com | 123456 |
| admin | admin@example.com | 123456 |

验收标准：

- 数据库启动成功
- 迁移执行成功
- 4 个测试账号可以登录

---

## 8. 后端搭建顺序

### 8.1 基础工程

先完成这些底层文件：

- `core/config.py`：读取环境变量
- `db/session.py`：创建数据库连接
- `db/base.py`：汇总 SQLAlchemy models
- `core/security.py`：密码哈希、JWT 生成与校验
- `main.py`：创建 FastAPI app，注册路由，配置 CORS

验收标准：

- `GET /health` 返回 `{ "status": "ok" }`
- 后端能连接数据库

### 8.2 Auth 模块

实现接口：

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| POST | `/api/auth/login` | 邮箱密码登录 |
| GET | `/api/auth/me` | 获取当前用户 |

实现依赖：

- `get_current_user`
- `require_roles(["admin"])`
- `require_roles(["handler", "admin"])`
- `require_roles(["approver"])`

验收标准：

- 4 个种子账号均可登录
- 前端拿到 JWT 后可以请求 `/api/auth/me`

### 8.3 Document 模块

实现接口：

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| POST | `/api/documents/upload` | 上传文档 |
| GET | `/api/documents` | 文档列表 |
| GET | `/api/documents/{id}` | 文档详情 |
| POST | `/api/documents/{id}/reindex` | 重新解析 |
| DELETE | `/api/documents/{id}` | 删除文档 |

上传流程：

1. 校验当前用户是 `admin`
2. 校验文件类型是 `.md`、`.txt`、`.pdf`
3. 保存原始文件到 `storage/documents/`
4. 创建 `documents` 记录，状态为 `pending`
5. 使用 `BackgroundTasks` 触发解析

文档状态：

```text
pending -> processing -> completed
pending -> processing -> failed
```

验收标准：

- 管理员可以上传文档
- 文档列表显示状态和 chunk 数量
- 解析失败时能看到错误原因

### 8.4 文档解析与切分

解析规则：

- Markdown：直接读取文本
- TXT：直接读取文本
- PDF：使用 `pypdf` 提取每页文本

切分规则：

```text
chunk_size = 800
chunk_overlap = 120
```

每个 chunk 保存 metadata：

```json
{
  "document_id": "uuid",
  "filename": "IT_VPN_FAQ.md",
  "chunk_index": 0,
  "page": 1,
  "section": "VPN 使用说明"
}
```

验收标准：

- 上传文档后能生成 chunk
- `documents.chunk_count` 与实际 chunk 数一致

### 8.5 Embedding 与检索

实现 `services/rag_service.py`：

- `embed_text(text: str) -> list[float]`
- `embed_chunks(chunks: list[str])`
- `search(query: str, top_k: int = 5)`
- `format_citations(chunks)`

检索必须返回：

- chunk 内容
- 文档名
- 页码或章节
- 相似度
- metadata

验收标准：

- 给定问题可以检索出 top 5 chunk
- 低于阈值的结果不用于确定回答

### 8.6 Chat 与 RAG 问答

实现接口：

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| POST | `/api/chat/conversations` | 创建对话 |
| GET | `/api/chat/conversations` | 对话列表 |
| GET | `/api/chat/conversations/{id}` | 对话详情 |
| POST | `/api/chat/conversations/{id}/messages` | 发送消息 |

RAG Prompt 约束：

```text
你是企业知识库问答助手。
你只能根据提供的上下文回答。
如果上下文没有答案，必须说明无法从当前知识库确认。
不允许编造制度、金额、日期、流程、联系人。
回答末尾必须列出引用来源。
如果用户的问题更适合人工处理，可以建议创建工单。
```

无可靠来源时固定回复：

```text
我没有在当前知识库中找到可靠依据，暂时不能确认这个问题。你可以换个问法，或创建工单让相关部门处理。
```

验收标准：

- 用户提问后保存 user message
- 系统返回 assistant message
- 有来源时展示引用
- 无来源时拒答

### 8.7 Agent 意图识别

实现一个轻量状态机：

```text
User Message
-> Triage Node
-> knowledge_qa / create_ticket / query_ticket / update_ticket / clarification / out_of_scope
-> 对应服务或工具
-> 写入 Trace
-> 返回结果
```

意图识别输出固定 JSON：

```json
{
  "intent": "knowledge_qa",
  "department": "IT",
  "confidence": 0.87,
  "need_ticket": false,
  "need_approval": false,
  "reason": "用户询问 VPN 操作问题"
}
```

注意事项：

- 不要直接信任 LLM 生成的 `requester_id`
- 所有用户身份都从 JWT 获取
- LLM 输出必须做 JSON schema 校验
- 校验失败时进入 `clarification`

验收标准：

- 普通知识问题进入 RAG
- “帮我创建工单”进入工单草稿
- 信息不足时追问用户补充

### 8.8 工单模块

实现接口：

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| POST | `/api/tickets` | 用户确认后创建工单 |
| GET | `/api/tickets` | 工单列表 |
| GET | `/api/tickets/{id}` | 工单详情 |
| PATCH | `/api/tickets/{id}` | 更新工单 |
| POST | `/api/tickets/{id}/comments` | 添加评论 |

工单字段：

- `ticket_no`
- `title`
- `description`
- `category`
- `priority`
- `status`
- `requester_id`
- `assignee_id`
- `source_conversation_id`

工单编号规则：

```text
TKT-YYYYMMDD-0001
```

验收标准：

- employee 可以创建并查看自己的工单
- handler 可以查看分配给自己的工单
- admin 可以查看全部工单
- handler 可以添加备注和更新状态

### 8.9 审批模块

需要审批的操作：

- 创建 `urgent` 优先级工单
- 将工单状态改为 `closed`
- 分派工单给其他处理人

实现接口：

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/approvals` | 审批列表 |
| GET | `/api/approvals/{id}` | 审批详情 |
| POST | `/api/approvals/{id}/approve` | 审批通过并执行 |
| POST | `/api/approvals/{id}/reject` | 审批拒绝 |

审批通过流程：

```text
读取 approvals.tool_name 和 approvals.tool_args
-> 再次做权限与风险校验
-> 执行原工具
-> 保存 execution_result
-> status = executed
```

审批拒绝流程：

```text
保存 decision_comment
-> status = rejected
-> 不执行原工具
```

验收标准：

- urgent 工单不会直接创建
- 审批人通过后才创建工单
- 审批拒绝后不会执行工具

### 8.10 Agent Trace

每次 Chat 请求都写入 `agent_traces`：

- 用户问题
- 意图识别结果
- 检索到的 chunk 摘要
- LLM 输入摘要
- LLM 输出
- 工具调用名称
- 工具调用参数
- 是否触发审批
- 最终结果
- 耗时
- 错误信息

实现接口：

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/traces` | Trace 列表 |
| GET | `/api/traces/{id}` | Trace 详情 |
| GET | `/api/chat/conversations/{id}/traces` | 对话 Trace |

验收标准：

- 管理员可以看到每次 Chat 的执行链路
- LLM 失败、工具失败、审批中断都会记录

---

## 9. 前端搭建顺序

### 9.1 全局基础

先实现：

- API client：统一注入 JWT
- Auth store：保存 token 和当前用户
- 路由守卫：未登录跳转 `/login`
- Layout：顶部导航 + 当前用户信息 + 退出登录
- 角色入口：按角色显示菜单

### 9.2 登录页 `/login`

功能：

- 邮箱输入
- 密码输入
- 登录按钮
- 登录失败提示
- 成功后跳转 `/chat`

验收标准：

- 4 个测试账号都能登录
- 刷新页面后仍能获取当前用户

### 9.3 Chat 页 `/chat`

功能：

- 对话列表
- 消息输入框
- AI 回答展示
- 引用来源展示
- 无依据拒答提示
- 工单草稿确认弹窗
- 创建成功后展示工单编号

验收标准：

- 可以完成一次 RAG 问答
- 可以从自然语言生成工单草稿
- 用户确认后可以创建工单或进入审批

### 9.4 工单页 `/tickets`

功能：

- 工单列表
- 状态筛选
- 工单详情
- 处理备注
- 状态更新

角色规则：

- employee：只看自己的工单
- handler：看分配给自己的工单
- admin：看全部工单

验收标准：

- 不同角色看到的数据范围不同
- handler 可以更新处理状态和添加备注

### 9.5 审批页 `/approvals`

功能：

- 审批列表
- 审批详情
- 工具参数展示
- 风险原因展示
- 通过按钮
- 拒绝按钮
- 审批意见输入

验收标准：

- approver 可以审批 urgent 工单
- 通过后工单被创建或更新
- 拒绝后工具不执行

### 9.6 文档管理页 `/admin/documents`

功能：

- 上传文档
- 文档列表
- 解析状态
- chunk 数量
- 删除文档
- 重新解析

验收标准：

- admin 可以上传文档
- 上传后能看到 `pending / processing / completed / failed`

### 9.7 Trace 页 `/admin/traces`

功能：

- Trace 列表
- Trace 详情
- 意图识别结果
- 检索 chunk
- 工具调用
- 审批状态
- LLM 输出
- 错误信息

验收标准：

- admin 可以复盘一次完整请求
- 面试演示时能讲清 Agent 做了什么

---

## 10. 工具调用安全规则

所有工具执行前必须经过统一检查：

1. 当前用户必须登录
2. 当前用户必须有对应角色权限
3. 参数必须通过 schema 校验
4. `requester_id`、`operator_id` 必须来自当前登录用户
5. 风险策略必须在工具执行前检查
6. 高风险操作只创建审批，不直接执行
7. 工具执行结果必须写入 Trace
8. 审批恢复执行时仍需重新校验权限和参数

工具列表：

| 工具名 | 说明 | 是否审批 |
| --- | --- | --- |
| `search_knowledge_base` | 检索知识库 | 否 |
| `create_ticket` | 创建普通工单 | `urgent` 需要 |
| `query_ticket` | 查询工单 | 否 |
| `update_ticket_status` | 更新工单状态 | `closed` 需要 |
| `assign_ticket` | 分派工单 | 是 |

---

## 11. 本地运行

### 11.1 启动数据库

```bash
docker compose up -d db
```

### 11.2 启动后端

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问：

```text
http://localhost:8000/docs
```

### 11.3 启动前端

```bash
cd frontend
npm run dev
```

访问：

```text
http://localhost:3000
```

---

## 12. 推荐开发里程碑

### 第 1 阶段：基础可启动

交付内容：

- Docker Compose 启动数据库
- FastAPI 启动成功
- Next.js 启动成功
- `/health` 可访问
- 数据库迁移可执行

验收：

```text
前端 http://localhost:3000 能打开
后端 http://localhost:8000/docs 能打开
PostgreSQL 可以连接
```

### 第 2 阶段：登录与角色

交付内容：

- 用户表
- JWT 登录
- 4 个测试账号
- 前端登录页
- 角色菜单

验收：

```text
employee / handler / approver / admin 都能登录
不同角色看到不同入口
```

### 第 3 阶段：文档入库

交付内容：

- 文档上传
- 本地存储
- 文档解析
- chunk 切分
- embedding
- pgvector 写入

验收：

```text
管理员上传 IT_VPN_FAQ.md 后，状态变为 completed，并显示 chunk_count > 0
```

### 第 4 阶段：RAG 问答

交付内容：

- Chat API
- 向量检索
- RAG Prompt
- 引用来源
- 无依据拒答

验收：

```text
员工提问“我电脑连不上 VPN 怎么办？”
系统返回基于文档的回答，并展示引用来源
```

### 第 5 阶段：工单 Agent

交付内容：

- 意图识别
- 工单草稿生成
- 用户确认创建
- 工单列表与详情

验收：

```text
员工输入“帮我创建一个 IT 工单，我的公司邮箱无法登录。”
系统返回工单草稿
用户确认后生成工单编号
```

### 第 6 阶段：审批闭环

交付内容：

- 风险策略
- approvals 表
- 审批页面
- 审批通过后恢复执行
- 审批拒绝后停止执行

验收：

```text
员工创建 urgent 工单
系统创建审批记录而不是直接创建工单
审批人通过后工单才真正创建
```

### 第 7 阶段：Trace 与演示包装

交付内容：

- agent_traces 表
- Trace API
- Trace 页面
- README
- 种子文档
- 演示脚本

验收：

```text
管理员能看到一次请求中的意图识别、检索结果、LLM 输出、工具调用和审批状态
```

---

## 13. 演示数据准备

建议准备 3 个 Markdown 种子文档：

```text
seed_docs/
  IT_VPN_FAQ.md
  HR_Leave_Policy.md
  Finance_Reimbursement.md
```

`IT_VPN_FAQ.md` 至少包含：

- VPN 登录失败排查
- VPN 客户端版本要求
- 账号锁定处理流程
- 何时需要提交 IT 工单

`HR_Leave_Policy.md` 至少包含：

- 年假规则
- 病假规则
- 请假审批流程

`Finance_Reimbursement.md` 至少包含：

- 发票抬头错误处理
- 报销提交时间
- 报销材料要求

---

## 14. 最终演示脚本

1. 管理员登录
2. 上传 `IT_VPN_FAQ.md`
3. 等待文档状态变为 `completed`
4. 查看 chunk 数量
5. 员工登录
6. 在 Chat 页面提问：“我电脑连不上 VPN 怎么办？”
7. 系统返回带引用来源的回答
8. 员工输入：“帮我创建一个 IT 工单”
9. Agent 返回工单草稿
10. 用户确认创建
11. 系统返回普通工单编号
12. 员工输入：“帮我创建一个紧急工单，我邮箱完全无法登录”
13. Agent 判断为 `urgent`，创建审批记录
14. 审批人登录
15. 查看审批详情并点击通过
16. 系统执行原工具调用，创建工单
17. 管理员登录
18. 打开 Trace 页面，查看检索、LLM、工具调用、审批状态

---

## 15. 测试清单

### 后端测试

- 登录成功和失败
- JWT 过期或缺失
- 不同角色访问权限
- 文档上传格式校验
- 文档解析失败处理
- chunk 切分数量
- embedding 写入
- 向量检索 top_k
- 无依据拒答
- 工单创建
- urgent 工单进入审批
- 审批通过后执行
- 审批拒绝后不执行
- Trace 写入

### 前端测试

- 登录页错误提示
- 刷新后用户状态恢复
- Chat 加载状态
- 引用来源展示
- 工单草稿确认弹窗
- 工单列表筛选
- 审批通过和拒绝
- 文档上传进度与状态
- Trace 详情展示

### 端到端验收

必须完整跑通：

```text
上传文档
-> RAG 问答
-> 创建普通工单
-> 创建 urgent 工单
-> 审批通过
-> 查看 Agent Trace
```

---

## 16. 常见风险与处理

### RAG 回答编造

处理方式：

- 设置相似度阈值
- 无 chunk 时固定拒答
- Prompt 明确禁止编造
- 响应必须包含 citations

### LLM 输出 JSON 不稳定

处理方式：

- 使用结构化输出或 JSON schema 校验
- 校验失败时重试 1 次
- 再失败则进入 clarification

### 审批恢复执行重复创建

处理方式：

- approvals 表保存 `idempotency_key`
- 审批执行前检查是否已经 `executed`
- 工具执行保持幂等

### 用户伪造工具参数

处理方式：

- 后端不要相信前端或 LLM 提供的用户 ID
- `requester_id` 从 JWT 当前用户获取
- 角色权限在后端统一检查

### PDF 解析效果不稳定

处理方式：

- MVP 只支持简单文本 PDF
- 解析失败记录 `error_message`
- README 明确说明暂不支持扫描件 OCR

---

## 17. README 展示重点

README 建议突出 5 个亮点：

1. RAG 问答可靠性：回答必须带引用，无依据拒答
2. Agent 工具调用：从自然语言生成工单草稿
3. Human-in-the-loop：高风险操作需要人工审批
4. Agent Trace：记录检索、LLM、工具调用、审批全过程
5. 工程化部署：FastAPI + PostgreSQL/pgvector + Docker Compose 一键启动

推荐标题：

```md
# Enterprise Support Agent

An AI Agent MVP for enterprise knowledge base Q&A, ticket automation, human approval, and execution tracing.
```

---

## 18. 两周开发排期

| 天数 | 目标 | 交付 |
| --- | --- | --- |
| Day 1 | 项目初始化 | 前后端、数据库、Docker Compose 可启动 |
| Day 2 | 数据库模型与登录 | 4 个角色账号可登录 |
| Day 3 | 文档上传与存储 | 管理员可上传文档 |
| Day 4 | 文档解析与 chunk | 上传后生成 chunk |
| Day 5 | Embedding 与检索 | 问题可检索相关 chunk |
| Day 6 | RAG 问答 | 返回带引用的回答 |
| Day 7 | 对话与消息 | 支持简单多轮对话 |
| Day 8 | 工单基础功能 | 创建、查看工单 |
| Day 9 | 意图识别与草稿 | 自然语言生成工单草稿 |
| Day 10 | 审批流程 | 高风险操作暂停并等待审批 |
| Day 11 | 工单处理与评论 | handler 可处理工单 |
| Day 12 | Agent Trace | admin 可查看执行链路 |
| Day 13 | 联调与优化 | 演示流程稳定 |
| Day 14 | 包装与演示 | README、种子文档、演示脚本 |

---

## 19. 完成标准

项目完成时应满足：

- `docker compose up --build` 可以启动主要服务
- README 能让别人独立跑起来
- 4 个测试账号可用
- 管理员可以上传文档并完成向量化
- 员工可以获得带引用的知识库回答
- 无可靠来源时系统拒答
- Agent 可以生成工单草稿
- 普通工单可以直接创建
- urgent 工单必须审批
- 审批通过后执行原工具调用
- 管理员可以查看 Agent Trace

达到以上标准后，这个 MVP 就具备可演示、可写简历、可用于面试讲解的完整闭环。
