# Day 13 工单详情与状态流转

Day 13 在 Day 11 工单前端和 Day 7 工单后端基础上，补齐了工单详情页和最小状态流转。处理人或管理员可以进入工单详情页，将工单状态更新为待处理、处理中、已解决或已关闭。

## 已完成内容

- 新增工单状态更新后端 schema。
- 新增工单状态更新服务函数。
- 新增 `PATCH /api/tickets/{ticket_id}/status` 接口。
- 工单列表新增“查看详情”操作。
- 新增 `/tickets/[ticketId]` 工单详情页。
- 工单详情页展示编号、标题、描述、分类、优先级、状态、创建时间和更新时间。
- 工单详情页支持处理人或管理员更新处理状态。
- 员工可以查看自己工单详情，但不能更新状态。

## 后端接口

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/tickets/{ticket_id}` | 查看工单详情 |
| PATCH | `/api/tickets/{ticket_id}/status` | 更新工单状态 |

状态更新请求：

```json
{
  "status": "in_progress"
}
```

支持状态：

```text
open
in_progress
resolved
closed
```

## 权限规则

- `employee`：可以查看自己提交的工单详情，不能更新状态。
- `handler`：可以查看并更新分配给自己的工单。
- `admin`：可以查看并更新全部工单。
- 未登录用户不能访问工单接口。

## 前端文件

```text
frontend/lib/tickets.ts
frontend/app/tickets/page.tsx
frontend/app/tickets/[ticketId]/page.tsx
frontend/app/globals.css
```

## 页面入口

登录后访问工单列表：

```text
http://localhost:3000/tickets
```

点击列表里的“查看详情”进入：

```text
http://localhost:3000/tickets/{ticketId}
```

## 验证

新增和更新的测试：

```text
backend/tests/test_ticket_service.py
backend/tests/test_tickets_api.py
tests/test_day13_frontend_ticket_detail_scaffold.py
```

运行方式：

```bash
conda run -n esa python -m pytest backend/tests/test_ticket_service.py backend/tests/test_tickets_api.py -q
python3 -m unittest tests.test_day13_frontend_ticket_detail_scaffold -v
cd frontend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run build
```

## 当前限制

- 工单评论已在 Day 14 补齐。
- 工单分配已在 Day 15 补齐。
- 暂未把“关闭工单”升级为单独审批流程。
- 暂未实现按状态筛选、搜索和分页。

这些能力留到后续阶段继续补齐。
