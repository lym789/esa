# Day 2 登录设计

## 范围

实现 `from-zero-build-guide.md` 中 Day 2 的里程碑：数据库用户、JWT 登录、基础 RBAC 依赖、4 个种子账号，以及登录后进入现有 JadeFlow AI Dashboard 的前端流程。

## 后端设计

后端保留现有 FastAPI 结构，并新增以下职责清晰的模块：

- `models/user.py`：定义 SQLAlchemy `User` 模型，包含 `id`、`email`、`name`、`role`、`hashed_password` 和时间戳字段。
- `core/security.py`：负责密码哈希、密码校验、JWT 生成和 JWT 解析。
- `services/auth_service.py`：负责用户查询、凭证校验和幂等创建种子账号。
- `api/auth.py`：暴露 `POST /api/auth/login` 和 `GET /api/auth/me`。
- `api/deps.py`：暴露 `get_db`、`get_current_user` 和 `require_roles`。
- `db/base.py`：汇总数据库元数据；`db/init_db.py` 在启动时创建 Day 2 所需表并写入种子账号。

MVP 当前阶段直接用 SQLAlchemy metadata 在启动时创建 `users` 表，不引入 Alembic 迁移文件。Day 3 之后表结构增多，再引入 Alembic 会更有价值。

## 前端设计

现有 Dashboard 视觉设计保留，作为登录后的应用主界面。

新增前端部分：

- `app/login/page.tsx`：使用同一套青绿色玻璃视觉语言渲染登录页。
- `lib/auth.ts`：封装 `/api/auth/login` 和 `/api/auth/me`。
- `lib/session.ts`：把 JWT 和用户信息保存到 `localStorage`。
- `app/page.tsx`：变成轻量客户端登录门卫；未登录用户跳转到 `/login`，已登录用户看到 `Dashboard`。
- `components/Dashboard.tsx`：从 props 读取登录用户，显示真实姓名和角色，不再写死管理员信息。

## 种子账号

所有账号密码都是 `123456`：

- `employee@example.com` / `employee`
- `handler@example.com` / `handler`
- `approver@example.com` / `approver`
- `admin@example.com` / `admin`

## 验收标准

- `POST /api/auth/login` 能为 4 个种子账号返回访问令牌和用户信息。
- 错误邮箱或密码返回 HTTP 401。
- 携带有效 Bearer token 调用 `GET /api/auth/me` 时返回当前用户。
- 缺少 token 或 token 无效时返回 HTTP 401。
- `require_roles(["admin"])` 允许管理员访问，拒绝非管理员用户。
- 前端登录成功后保存 token 和用户信息，并打开 Dashboard。
- Dashboard 显示当前登录用户的姓名和角色。
