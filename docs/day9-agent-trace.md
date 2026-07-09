# Day 9 Agent Trace

Day 9 补齐了后端 Agent Trace 能力，用于记录 Chat/RAG、工单创建、urgent 审批中断、审批通过和审批拒绝等关键执行链路。

本阶段实现后端模型、服务、接口和自动写入，不实现前端 Trace 页面。前端页面留到后续阶段。

## 已完成内容

- 新增 `agent_traces` 数据模型。
- 新增 Trace 写入服务。
- 新增管理员 Trace 查询接口。
- Chat/RAG 问答会自动写入 Trace。
- 普通工单创建会自动写入 Trace。
- urgent 工单创建审批时会自动写入 Trace。
- 审批通过和审批拒绝会自动写入 Trace。
- 新增 Trace 服务测试和 API 测试。

## 后端接口

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/traces` | 管理员查看 Trace 列表 |
| GET | `/api/traces/{id}` | 管理员查看 Trace 详情 |
| GET | `/api/chat/conversations/{id}/traces` | 管理员查看指定对话的 Trace |

## Trace 字段

```text
conversation_id
user_id
intent
user_input
intent_json
retrieved_chunks_json
llm_input_summary
llm_output
tool_name
tool_args_json
approval_status
final_result_json
error_message
elapsed_ms
created_at
```

## 已记录的链路

### Chat/RAG

用户发送 Chat 消息后，系统记录：

- `intent = knowledge_qa`
- `tool_name = rag_search`
- `retrieved_chunks_json`：命中的 chunk 摘要
- `llm_input_summary`：本地 RAG 输入摘要
- `llm_output`：返回给用户的回答
- `approval_status = not_required`

### 普通工单

普通工单直接创建后，系统记录：

- `intent = create_ticket`
- `tool_name = create_ticket`
- `approval_status = not_required`
- `final_result_json`：工单 ID 和工单编号

### urgent 工单

urgent 工单不会直接创建，而是创建审批记录。系统记录：

- `intent = create_ticket`
- `tool_name = create_approval`
- `approval_status = pending`
- `final_result_json`：审批 ID 和审批状态

### 审批通过

审批人通过审批后，系统执行原始工单创建动作，并记录：

- `intent = approval_decision`
- `tool_name = approve_approval`
- `approval_status = executed`
- `final_result_json`：创建出的工单 ID 和工单编号

### 审批拒绝

审批人拒绝审批后，系统不创建工单，并记录：

- `intent = approval_decision`
- `tool_name = reject_approval`
- `approval_status = rejected`
- `final_result_json`：审批 ID 和最终状态

## 权限规则

- 只有 `admin` 可以访问 `/api/traces` 和 `/api/traces/{id}`。
- 只有 `admin` 可以访问 `/api/chat/conversations/{id}/traces`。
- 其他角色访问 Trace 接口会返回 `403`。

## 示例请求

查看 Trace 列表：

```bash
curl http://localhost:8000/api/traces \
  -H "Authorization: Bearer <admin_token>"
```

查看 Trace 详情：

```bash
curl http://localhost:8000/api/traces/1 \
  -H "Authorization: Bearer <admin_token>"
```

查看某个对话的 Trace：

```bash
curl http://localhost:8000/api/chat/conversations/1/traces \
  -H "Authorization: Bearer <admin_token>"
```

## 测试

新增测试文件：

- `backend/tests/test_trace_service.py`
- `backend/tests/test_traces_api.py`

运行方式：

```bash
conda run -n esa python -m pytest backend/tests/test_trace_service.py backend/tests/test_traces_api.py -q
```

## 下一阶段

下一阶段建议补前端页面：

- `/admin/traces`：Trace 列表。
- Trace 详情抽屉或详情页。
- 展示意图识别、工具调用、审批状态和最终结果。
- 从 Dashboard 增加 Trace 管理入口。
