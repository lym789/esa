# Day 2：数据库模型与登录

Day 2 实现项目的第一个真实应用闭环：种子账号可以登录、获取 JWT、调用 `/api/auth/me`，并进入 JadeFlow AI Dashboard。Dashboard 侧边栏会显示当前登录用户的姓名和角色。

## 后端

新增接口：

```text
POST /api/auth/login
GET  /api/auth/me
```

`POST /api/auth/login` 请求体：

```json
{
  "email": "admin@example.com",
  "password": "123456"
}
```

响应示例：

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "admin@example.com",
    "name": "Admin User",
    "role": "admin"
  }
}
```

`GET /api/auth/me` 需要携带：

```text
Authorization: Bearer <jwt>
```

## 种子账号

所有种子账号的密码都是 `123456`。

| 角色 | 邮箱 |
| --- | --- |
| 普通员工 | `employee@example.com` |
| 工单处理人 | `handler@example.com` |
| 审批人 | `approver@example.com` |
| 管理员 | `admin@example.com` |

## 前端

现有 JadeFlow AI Dashboard 已加入客户端登录保护：

- 未登录用户会跳转到 `/login`
- 登录成功后将 `accessToken` 和 `currentUser` 保存到 `localStorage`
- Dashboard 侧边栏显示当前登录用户的姓名和角色
- 退出登录入口已在 Day 16 移到 `/settings` 设置页

## 后端本地验证

```bash
cd backend
source .venv/bin/activate
pytest tests/test_auth_service.py tests/test_auth_api.py -q
```

## 前端本地验证

```bash
cd frontend
npm run build
```

## 说明

如果本机没有安装 Python 3.12，本地虚拟环境可能会使用 macOS 系统自带 Python。Docker 后端镜像仍使用 `python:3.12-slim`，这是本项目推荐运行时。
