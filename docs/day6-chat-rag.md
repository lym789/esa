# Day 6 Chat 与 RAG 问答

Day 6 在 Day 5 检索能力基础上，实现最小可用 Chat API。用户可以创建对话、发送问题，系统保存用户消息，并返回基于知识库检索结果的助手消息。

## 已实现能力

- 新增 `conversations` 表保存对话。
- 新增 `messages` 表保存用户消息和助手消息。
- 新增 `services/chat_service.py`。
- 新增 `/api/chat` 接口：
  - 创建对话
  - 对话列表
  - 对话详情
  - 发送消息
- 发送消息后会：
  - 保存 user message；
  - 调用 Day 5 检索服务；
  - 有来源时生成 assistant message；
  - 无来源时返回固定拒答；
  - 保存 assistant message。

## 接口

### 创建对话

```text
POST /api/chat/conversations
```

请求：

```json
{
  "title": "VPN 问答"
}
```

### 对话列表

```text
GET /api/chat/conversations
```

### 对话详情

```text
GET /api/chat/conversations/{id}
```

### 发送消息

```text
POST /api/chat/conversations/{id}/messages
```

请求：

```json
{
  "content": "VPN 登录不了怎么办"
}
```

## 回答策略

当前不调用真实 LLM，使用保守的 extractive RAG：

- 检索相关 chunk；
- 取相似度最高的内容组织回答；
- 末尾附引用来源；
- 没有可靠来源时固定拒答。

固定拒答：

```text
我没有在当前知识库中找到可靠依据，暂时不能确认这个问题。你可以换个问法，或创建工单让相关部门处理。
```

## 权限

- 所有 Chat 接口都需要登录。
- 用户只能访问自己的对话。
- 其他用户访问不属于自己的对话会返回 `404`。

## 自动验证

```bash
backend/.venv/bin/pytest backend/tests/test_chat_service.py backend/tests/test_chat_api.py -q
```

完整后端聚焦测试：

```bash
backend/.venv/bin/pytest backend/tests/test_auth_service.py backend/tests/test_auth_api.py backend/tests/test_document_service.py backend/tests/test_document_processing_service.py backend/tests/test_documents_api.py backend/tests/test_rag_service.py backend/tests/test_search_api.py backend/tests/test_chat_service.py backend/tests/test_chat_api.py -q
```

## 下一步

Chat 前端页面已在 Day 17 补齐。后续可以继续把“建议创建工单”做成一键跳转到工单草稿。
