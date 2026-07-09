# Day 14 工单评论

Day 14 在 Day 13 工单详情页基础上，补齐了工单评论能力。能访问某张工单的用户可以查看评论，并添加处理备注、排查进展或补充信息。

## 已完成内容

- 新增 `ticket_comments` 数据模型。
- 新增评论创建和评论列表 schema。
- 新增评论创建和列表服务函数。
- 新增工单评论接口。
- 前端工单详情页新增“工单评论”卡片。
- 支持查看评论列表。
- 支持新增评论。
- 评论列表区域支持滚动。

## 后端接口

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/tickets/{ticket_id}/comments` | 查看工单评论列表 |
| POST | `/api/tickets/{ticket_id}/comments` | 新增工单评论 |

新增评论请求：

```json
{
  "content": "收到，正在检查账号锁定状态"
}
```

## 权限规则

评论权限沿用工单访问权限：

- `employee`：可以查看并评论自己提交的工单。
- `handler`：可以查看并评论分配给自己的工单。
- `admin`：可以查看并评论全部工单。
- 无权访问工单的用户不能查看或新增评论。

## 前端文件

```text
frontend/lib/tickets.ts
frontend/app/tickets/[ticketId]/page.tsx
frontend/app/globals.css
```

## 页面入口

登录后进入工单详情：

```text
http://localhost:3000/tickets/{ticketId}
```

右侧“工单评论”卡片中可以查看已有评论，也可以填写“新增评论”并发送。

## 验证

新增和更新的测试：

```text
backend/tests/test_ticket_service.py
backend/tests/test_tickets_api.py
tests/test_day14_frontend_ticket_comments_scaffold.py
```

运行方式：

```bash
conda run -n esa python -m pytest backend/tests/test_ticket_service.py backend/tests/test_tickets_api.py -q
python3 -m unittest tests.test_day14_frontend_ticket_comments_scaffold -v
cd frontend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run build
```

## 当前限制

- 评论作者姓名已在 Day 15 补齐。
- 暂未实现评论编辑和删除。
- 工单分配已在 Day 15 补齐。
- 暂未实现评论通知。

这些能力留到后续阶段继续补齐。
