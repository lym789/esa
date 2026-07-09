# Day 8 审批闭环

Day 8 在 Day 7 工单能力上补齐了最小审批闭环：高风险 `urgent` 工单不直接创建，而是进入审批；审批通过后才执行原始工单创建动作，审批拒绝则不创建工单。

本阶段仍不实现 Agent Trace、评论、工单状态更新和分派审批，这些留到后续阶段。

## 已完成内容

- 新增 `approvals` 数据模型。
- 新增审批列表、详情、通过和拒绝接口。
- `priority=urgent` 的工单创建请求改为创建审批记录。
- 审批通过后读取保存的 `tool_args` 并创建工单。
- 审批拒绝后只保存意见，不执行工单创建。
- 审批通过具备幂等保护：已经执行过的审批不会重复创建工单。
- 新增审批服务测试和 API 测试。

## 后端接口

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/approvals` | 获取当前用户可见的审批列表 |
| GET | `/api/approvals/{id}` | 获取审批详情 |
| POST | `/api/approvals/{id}/approve` | 审批通过并执行原工具 |
| POST | `/api/approvals/{id}/reject` | 审批拒绝并停止执行 |

## urgent 工单流程

普通工单仍然直接创建：

```text
POST /api/tickets
priority != urgent
-> 创建 tickets 记录
-> 返回工单对象
```

紧急工单进入审批：

```text
POST /api/tickets
priority = urgent
-> 不创建 tickets 记录
-> 创建 approvals 记录
-> 返回 202 pending_approval
```

审批通过：

```text
POST /api/approvals/{id}/approve
-> 读取 approvals.tool_name 和 approvals.tool_args
-> 重新执行 create_ticket
-> 保存 execution_result
-> status = executed
```

审批拒绝：

```text
POST /api/approvals/{id}/reject
-> 保存 decision_comment
-> status = rejected
-> 不创建 tickets 记录
```

## 审批字段

```text
status
tool_name
tool_args_json
requester_id
approver_id
decision_comment
execution_result_json
idempotency_key
created_at
updated_at
decided_at
```

## 权限规则

- `employee`：可以发起 urgent 工单审批，可以查看自己发起的审批。
- `approver`：可以查看审批列表，可以通过或拒绝审批。
- `admin`：可以查看、通过或拒绝全部审批。
- 未登录用户不能访问审批接口。

## 示例请求

提交 urgent 工单：

```bash
curl -X POST http://localhost:8000/api/tickets \
  -H "Authorization: Bearer <employee_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "邮箱完全无法登录",
    "description": "公司邮箱完全无法登录，影响工作",
    "category": "IT",
    "priority": "urgent"
  }'
```

返回结果示例：

```json
{
  "status": "pending_approval",
  "approval": {
    "id": 1,
    "status": "pending",
    "tool_name": "create_ticket"
  }
}
```

审批通过：

```bash
curl -X POST http://localhost:8000/api/approvals/1/approve \
  -H "Authorization: Bearer <approver_token>" \
  -H "Content-Type: application/json" \
  -d '{"decision_comment":"同意处理"}'
```

审批拒绝：

```bash
curl -X POST http://localhost:8000/api/approvals/1/reject \
  -H "Authorization: Bearer <approver_token>" \
  -H "Content-Type: application/json" \
  -d '{"decision_comment":"信息不足"}'
```

## 测试

新增测试文件：

- `backend/tests/test_approval_service.py`
- `backend/tests/test_approvals_api.py`

运行方式：

```bash
conda run -n esa python -m pytest backend/tests/test_approval_service.py backend/tests/test_approvals_api.py -q
```

## 下一阶段

下一阶段将推进 Agent Trace：

- 记录工单草稿、审批中断、审批执行结果。
- 管理员可以查看一次请求的执行链路。
- 为后续演示提供可解释的 Agent 行为记录。
