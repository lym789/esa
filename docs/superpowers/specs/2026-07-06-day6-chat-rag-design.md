# Day 6 Chat 与 RAG 问答设计

## 目标

Day 6 在 Day 5 检索能力基础上，提供最小可用 Chat API：用户可以创建对话、查看对话、发送问题，系统保存用户消息并返回带引用的助手消息。

本阶段不调用真实 LLM，使用保守的 extractive RAG：只根据检索到的 chunk 内容组织回答。没有可靠来源时返回固定拒答，避免编造。

## 范围

- 新增 `conversations` 表。
- 新增 `messages` 表。
- 新增 `services/chat_service.py`。
- 新增 `/api/chat` 路由：
  - `POST /api/chat/conversations`
  - `GET /api/chat/conversations`
  - `GET /api/chat/conversations/{id}`
  - `POST /api/chat/conversations/{id}/messages`
- 发送消息时：
  - 保存 user message；
  - 调用 Day 5 `search()` 检索 chunk；
  - 有来源时生成 assistant message，并附引用；
  - 无来源时生成固定拒答；
  - 保存 assistant message。

## 非目标

- 不调用 OpenAI Chat Completion。
- 不做意图识别。
- 不创建工单。
- 不写 Agent Trace。
- 不实现前端 Chat 页面。

## RAG 回答策略

使用固定约束：

```text
你是企业知识库问答助手。
你只能根据提供的上下文回答。
如果上下文没有答案，必须说明无法从当前知识库确认。
不允许编造制度、金额、日期、流程、联系人。
回答末尾必须列出引用来源。
如果用户的问题更适合人工处理，可以建议创建工单。
```

MVP 本地实现不调用 LLM，而是：

- 使用 `search()` 获取相关 chunk；
- 取相似度最高的 chunk；
- 以“根据当前知识库……”开头；
- 引用 chunk 内容摘要；
- 末尾列出引用来源。

无可靠来源时固定回复：

```text
我没有在当前知识库中找到可靠依据，暂时不能确认这个问题。你可以换个问法，或创建工单让相关部门处理。
```

## 数据模型

### `conversations`

- `id`
- `title`
- `user_id`
- `created_at`
- `updated_at`

### `messages`

- `id`
- `conversation_id`
- `role`: `user` 或 `assistant`
- `content`
- `citations_json`
- `metadata_json`
- `created_at`

## 权限

- 登录用户只能查看和操作自己的对话。
- 发送消息必须在自己的对话中。

## 验收标准

- 用户可以创建对话。
- 用户可以查看自己的对话列表和详情。
- 用户提问后保存 user message。
- 系统返回并保存 assistant message。
- 有来源时 assistant message 包含引用。
- 无来源时 assistant message 使用固定拒答。
- 其他用户不能访问不属于自己的对话。
