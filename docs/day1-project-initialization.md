# Day 1：项目初始化

本文记录 `from-zero-build-guide.md` 中 Day 1 的落地结果。

## 目标

Day 1 只做可运行底座，不实现登录、文档上传、RAG、工单、审批或执行链路追踪等业务逻辑。

交付范围：

- FastAPI 后端项目骨架
- Next.js 前端项目骨架
- PostgreSQL + pgvector 数据库服务
- Docker Compose 编排
- `.env.example` 环境变量模板
- README 启动说明

## 文件结构

```text
backend/
  app/
    main.py
    core/config.py
    db/session.py
    storage/
  Dockerfile
  pyproject.toml
  requirements.txt
frontend/
  app/
    layout.tsx
    page.tsx
    globals.css
  Dockerfile
  package.json
docker-compose.yml
.env.example
README.md
```

## 后端

Day 1 后端提供两个基础检查接口：

- `GET /health`：确认 FastAPI 服务已启动
- `GET /db/health`：通过 SQLAlchemy 执行 `SELECT 1`，确认数据库可连接

数据库连接串来自 `DATABASE_URL`。Docker Compose 中默认使用：

```text
postgresql+psycopg://postgres:postgres@db:5432/enterprise_support_agent
```

本机直接运行后端时，需要把数据库主机改为 `localhost`，或通过环境变量覆盖。

## 前端

Day 1 前端用于确认 Next.js 应用可以启动，并能接入后端。后续 Day 2 已将前端升级为 JadeFlow AI Dashboard，并加入登录保护。

## Docker Compose 编排

Compose 中包含三个服务：

- `db`：`pgvector/pgvector:pg16`
- `backend`：FastAPI + Uvicorn，暴露 `8000`
- `frontend`：Next.js，暴露 `3000`

`backend` 等待数据库健康检查通过后启动。

## 验收方式

```bash
cp .env.example .env
docker compose up --build
```

启动后检查：

```bash
curl http://localhost:8000/health
curl http://localhost:8000/db/health
open http://localhost:3000
```

如果本机端口已被占用，可以临时覆盖宿主机端口：

```bash
POSTGRES_PORT=5433 BACKEND_PORT=8001 FRONTEND_PORT=3001 FRONTEND_ORIGIN=http://localhost:3001 NEXT_PUBLIC_API_BASE_URL=http://localhost:8001 docker compose up --build
```

预期：

- `/health` 返回 `{"status":"ok","service":"backend"}`
- `/db/health` 返回 `{"status":"ok","service":"database"}`
- 前端页面可以正常打开

## 下一步

Day 2 开始实现：

- `users` 表
- JWT 登录
- RBAC 依赖
- 4 个测试账号种子数据
- 登录页
