# Day 15 工单分配与评论作者展示

Day 15 在工单详情页基础上补齐管理员分配处理人的能力，并把评论列表中的用户 ID 展示升级为评论作者姓名。

## 已完成内容

- 新增管理员查询可用处理人的接口。
- 新增工单分配 schema。
- 新增工单分配服务函数。
- 新增 `PATCH /api/tickets/{ticket_id}/assignee` 接口。
- 评论列表返回 `author_name` 和 `author_role`。
- 前端工单详情页新增“分配处理人”卡片。
- 管理员可以选择处理人或清空处理人。
- 工单基础信息中的处理人展示姓名。
- 工单评论展示作者姓名和评论时间。

## 后端接口

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/auth/handlers` | 管理员查看可分配的处理人 |
| PATCH | `/api/tickets/{ticket_id}/assignee` | 管理员更新工单处理人 |
| GET | `/api/tickets/{ticket_id}/comments` | 查看带作者姓名的评论列表 |
| POST | `/api/tickets/{ticket_id}/comments` | 新增评论并返回作者姓名 |

分配处理人请求：

```json
{
  "assignee_id": 2
}
```

清空处理人请求：

```json
{
  "assignee_id": null
}
```

评论返回示例：

```json
{
  "id": 1,
  "ticket_id": 3,
  "author_id": 4,
  "author_name": "管理员用户",
  "author_role": "admin",
  "content": "已分配给工单处理人跟进",
  "created_at": "2026-07-07T10:00:00"
}
```

## 权限规则

- `admin`：可以查看全部可用处理人，可以分配或清空任意可访问工单的处理人。
- `handler`：不能分配工单，只能查看和处理已分配给自己的工单。
- `employee`：不能分配工单，只能查看自己提交的工单。
- 分配目标必须是启用状态的 `handler` 用户。

## 前端文件

```text
frontend/lib/tickets.ts
frontend/app/tickets/[ticketId]/page.tsx
frontend/app/globals.css
```

## 页面入口

使用管理员账号登录后进入工单详情：

```text
http://localhost:3000/tickets/{ticketId}
```

右侧“分配处理人”卡片可以选择处理人并保存。员工和处理人账号不会看到该卡片。

## 验证

新增和更新的测试：

```text
backend/tests/test_auth_api.py
backend/tests/test_tickets_api.py
tests/test_day15_frontend_ticket_assignment_scaffold.py
```

运行方式：

```bash
conda run -n esa python -m pytest backend/tests/test_auth_api.py backend/tests/test_tickets_api.py -q
python3 -m unittest tests.test_day15_frontend_ticket_assignment_scaffold -v
cd frontend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run build
```

## 当前限制

- 暂未实现工单列表页直接分配。
- 暂未实现处理人变更通知。
- 暂未实现按处理人筛选、搜索和分页。
- 暂未把重新分配升级为单独审批流程。

这些能力留到后续阶段继续补齐。
