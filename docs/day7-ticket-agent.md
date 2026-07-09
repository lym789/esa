# Day 7 工单 Agent 与基础工单接口

Day 7 在 Day 6 Chat/RAG 的基础上，补齐了工单闭环的第一步：从自然语言生成工单草稿，并在用户确认后创建普通工单。

本阶段不实现审批、评论、工单状态更新和 Agent Trace，这些留到后续阶段。

## 已完成内容

- 新增 `tickets` 数据模型。
- 新增工单草稿生成服务。
- 新增工单创建、列表和详情接口。
- 按用户角色过滤工单可见范围。
- 新增后端单元测试和 API 测试。

## 后端接口

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| POST | `/api/tickets/draft` | 根据自然语言生成工单草稿 |
| POST | `/api/tickets` | 用户确认后创建工单 |
| GET | `/api/tickets` | 获取当前用户可见的工单列表 |
| GET | `/api/tickets/{id}` | 获取当前用户可见的工单详情 |

## 工单字段

```text
ticket_no
title
description
category
priority
status
requester_id
assignee_id
source_conversation_id
created_at
updated_at
```

## 编号规则

工单编号使用当天递增编号：

```text
TKT-YYYYMMDD-0001
```

例如：

```text
TKT-20260707-0001
```

## 草稿生成规则

当前为了保证本地演示稳定，草稿生成使用确定性关键词规则，不依赖外部 LLM。

分类识别：

- `IT`：邮箱、登录、VPN、网络、系统、账号等关键词。
- `HR`：请假、年假、入职、离职、社保、薪资等关键词。
- `Finance`：报销、发票、付款、预算、财务等关键词。
- `Admin`：门禁、工位、会议室、办公用品、行政等关键词。
- `Other`：无法明确分类时使用。

优先级识别：

- `urgent`：紧急、完全无法、中断、立刻、马上等关键词。
- `high`：严重、无法工作、影响工作等关键词。
- `low`：低优先级、不着急、有空等关键词。
- `medium`：默认优先级。

## 权限规则

- `employee`：可以创建工单，只能查看自己提交的工单。
- `handler`：可以查看分配给自己的工单。
- `admin`：可以查看全部工单。
- 未登录用户不能访问工单接口。

## 示例请求

生成草稿：

```bash
curl -X POST http://localhost:8000/api/tickets/draft \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"content":"帮我创建一个 IT 工单，我的公司邮箱无法登录"}'
```

创建工单：

```bash
curl -X POST http://localhost:8000/api/tickets \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "公司邮箱无法登录",
    "description": "帮我创建一个 IT 工单，我的公司邮箱无法登录",
    "category": "IT",
    "priority": "medium"
  }'
```

## 测试

新增测试文件：

- `backend/tests/test_ticket_service.py`
- `backend/tests/test_tickets_api.py`

运行方式：

```bash
conda run -n esa python -m pytest backend/tests/test_ticket_service.py backend/tests/test_tickets_api.py -q
```

## 下一阶段

下一阶段将推进审批闭环：

- `urgent` 工单不直接创建，改为创建审批记录。
- 审批人可以通过或拒绝审批。
- 审批通过后恢复执行原工单创建动作。
- 审批结果写入后续 Agent Trace。
