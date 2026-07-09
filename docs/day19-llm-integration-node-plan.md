# Day 19：大模型接入功能节点推进方案

## 1. 目标

本文档用于拆解 Enterprise Support Agent 的大模型接入工作，把 `docs/day19-llm-integration.md` 中的设计方案落成可推进、可验收的功能节点。

本次接入目标不是把业务逻辑完全交给模型，而是在保留后端权限、状态流转、审批和审计规则的前提下，让模型承担以下能力：

- 自然语言理解。
- 知识库答案生成。
- 语义检索向量生成。
- 工单草稿结构化提取。
- 意图识别和风险解释。
- Agent Trace 可解释性增强。

## 2. 推进原则

- 默认不破坏现有功能：未配置 API Key 或未启用模型时，系统继续使用本地规则和本地检索。
- 业务服务不直接依赖第三方 SDK：统一通过内部 `LLMClient` 和 `EmbeddingClient` 调用模型。
- 模型只做理解、生成和判断：权限、审批、数据库写入和状态变更仍由后端代码控制。
- 单元测试不调用真实模型：测试使用 fake client，真实模型调用只用于手动验收或单独集成测试。
- 所有关键模型链路必须可追踪：输入摘要、检索结果、模型输出、耗时、错误和审批状态写入 Agent Trace。
- API Key 只放在后端环境变量，不能进入前端代码或日志明文。

## 3. 总体节点

| 节点 | 名称 | 主要目标 | 依赖 | 建议优先级 |
| --- | --- | --- | --- | --- |
| 节点 1 | 模型基础设施 | 建立 LLM 和 Embedding 访问层 | 无 | P0 |
| 节点 2 | 真实 Embedding 接入 | 替换本地 hash 向量，提高检索质量 | 节点 1 | P0 |
| 节点 3 | RAG 大模型回答 | 基于知识库 chunk 生成带引用回答 | 节点 1、节点 2 | P0 |
| 节点 4 | 工单草稿大模型提取 | 用模型生成结构化工单草稿 | 节点 1 | P1 |
| 节点 5 | 意图识别与风险增强 | 支持 Agent 路由和审批风险解释 | 节点 1、节点 3、节点 4 | P2 |

推荐顺序：

```text
节点 1 -> 节点 2 -> 节点 3 -> 节点 4 -> 节点 5
```

最小可交付版本：

```text
节点 1 + 节点 2 + 节点 3 + 节点 4
```

完成最小可交付版本后，系统就具备真实 AI Agent 的核心能力：真实 embedding、知识库大模型回答、工单草稿提取和 Trace 记录。

## 4. 节点 1：模型基础设施

### 4.1 目标

先把模型调用封装成统一内部能力，不直接改动业务主流程。

### 4.2 涉及模块

- `backend/app/core/config.py`
- `backend/app/services/llm_client.py`
- `backend/app/services/embedding_client.py`
- `backend/app/services/prompt_templates.py`
- `backend/tests/`

### 4.3 功能内容

新增配置项：

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=replace-with-your-key
OPENAI_BASE_URL=
LLM_MODEL=gpt-4.1-mini
EMBEDDING_MODEL=text-embedding-3-small
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2
LLM_ENABLED=false
```

新增服务：

- `LLMClient`：封装文本生成、结构化 JSON 生成、超时、重试和错误处理。
- `EmbeddingClient`：封装单条文本和批量文本的 embedding 调用。
- `prompt_templates.py`：集中保存 RAG、工单草稿、意图识别和风险判断 prompt。
- `FakeLLMClient` / `FakeEmbeddingClient`：供单元测试使用。

### 4.4 验收标准

- 不配置 API Key 时，系统仍能使用当前本地规则运行。
- `LLM_ENABLED=false` 时，不调用真实模型。
- `LLM_ENABLED=true` 且有 API Key 时，可以调用真实模型。
- 单元测试不依赖外网和真实 API Key。
- 业务服务不直接导入 OpenAI SDK。

### 4.5 需要外部信息

开发阶段不需要 API Key。

真实联调阶段需要：

```text
OPENAI_API_KEY=<实际 key>
LLM_ENABLED=true
```

如果使用 OpenAI 兼容服务，还需要：

```text
OPENAI_BASE_URL=<兼容服务地址>
```

## 5. 节点 2：真实 Embedding 接入

### 5.1 目标

用真实 embedding 模型替换当前 `local-hash-v1`，提升知识库语义检索质量。

### 5.2 涉及模块

- `backend/app/services/document_processing_service.py`
- `backend/app/services/rag_service.py`
- `backend/app/services/embedding_client.py`
- `backend/app/models/document_chunk.py`
- `backend/tests/test_document_processing_service.py`
- `backend/tests/test_rag_service.py`

### 5.3 功能内容

- 文档解析并切 chunk 后，通过 `EmbeddingClient` 生成向量。
- 用户查询知识库时，通过同一 embedding 模型生成 query 向量。
- 保留 `local-hash-v1` 作为 fallback。
- `document_chunks.embedding_model` 记录实际使用的模型名称。
- 检索时避免不同模型生成的向量直接混用。
- 增加重新索引旧文档的内部服务函数，为后续管理入口预留能力。

### 5.4 验收标准

- 新上传文档在模型开启时使用真实 embedding。
- 未开启模型或模型调用失败时，仍可回退本地 hash embedding。
- 查询向量和 chunk 向量使用同一模型时才参与相似度计算。
- 单元测试可以验证 embedding fallback 和模型名称记录。

### 5.5 风险点

- 更换 embedding 模型后，旧文档需要重新索引。
- 真实 embedding 维度可能与当前本地 256 维不同，检索逻辑必须兼容不同维度。
- 模型调用失败不能导致文档永久卡在 processing 状态。

## 6. 节点 3：RAG 大模型回答

### 6.1 目标

让 Chat/RAG 从“拼接最高相似度 chunk”升级为“基于多个知识库片段生成带引用的中文回答”。

### 6.2 涉及模块

- `backend/app/services/chat_service.py`
- `backend/app/services/rag_service.py`
- `backend/app/services/llm_client.py`
- `backend/app/services/prompt_templates.py`
- `backend/app/services/trace_service.py`
- `backend/tests/test_chat_service.py`

### 6.3 功能内容

- Chat 收到用户问题后，先检索知识库 chunk。
- 无命中或相似度低于阈值时，直接返回当前拒答文案。
- 有可靠来源时，调用 LLM 生成回答。
- Prompt 明确限制模型只能基于检索结果回答。
- 模型输出结构化字段：

```json
{
  "answer": "根据知识库生成的中文回答",
  "citations": ["[1]", "[2]"],
  "confidence": 0.86,
  "suggest_ticket": false
}
```

- 模型输出不合法、引用不合法或模型失败时，回退当前本地回答逻辑。
- Agent Trace 记录检索 chunk、模型输入摘要、模型输出、工具参数、耗时和错误。

### 6.4 验收标准

- `/chat` 页面有来源时返回自然中文回答。
- 回答保留引用来源。
- 没有可靠来源时不调用或不采纳模型自由回答。
- 模型失败时用户仍能收到可用回答或拒答。
- 管理员可在 Trace 中看到模型链路。

### 6.5 风险点

- Prompt injection：知识库片段中可能包含“忽略前文规则”等内容，Prompt 必须强调片段只是资料，不是指令。
- 幻觉：模型输出引用必须来自检索结果，不能生成不存在的来源。
- 成本控制：限制 top_k、上下文长度、最大输出长度和重试次数。

## 7. 节点 4：工单草稿大模型提取

### 7.1 目标

让自然语言创建工单更准确，减少关键词规则误判。

### 7.2 涉及模块

- `backend/app/services/ticket_service.py`
- `backend/app/services/llm_client.py`
- `backend/app/services/prompt_templates.py`
- `backend/app/services/trace_service.py`
- `backend/tests/test_ticket_service.py`

### 7.3 功能内容

- `generate_ticket_draft` 在模型开启时优先调用 LLM。
- 模型从用户描述中提取结构化工单草稿。
- 只允许以下分类：

```text
IT, HR, Finance, Admin, Other
```

- 只允许以下优先级：

```text
low, medium, high, urgent
```

- 模型输出格式：

```json
{
  "title": "公司邮箱无法登录",
  "description": "用户反馈公司邮箱无法登录，影响正常办公。",
  "category": "IT",
  "priority": "medium",
  "confidence": 0.88,
  "reason": "描述中出现邮箱、登录等 IT 支持关键词，未体现紧急中断。"
}
```

- 后端严格校验模型输出。
- 模型输出不合法、字段缺失或调用失败时，回退当前关键词规则。
- 前端仍允许用户在提交前手动修改草稿。

### 7.4 验收标准

- 复杂自然语言能生成合理工单草稿。
- 模型输出非法时不会写入非法分类或优先级。
- urgent 工单仍进入现有审批流程。
- 用户确认前不直接创建工单。
- Trace 能记录草稿生成原因和模型输出。

### 7.5 风险点

- 模型可能生成未允许的分类或优先级，必须后端校验。
- 模型不能替代权限判断，不能直接创建或更新工单状态。
- 用户输入可能包含敏感信息，发送给模型前应只保留生成草稿所需内容。

## 8. 节点 5：意图识别与风险增强

### 8.1 目标

从单一问答和建单能力升级为企业支持 Agent：先识别意图，再路由到知识库、工单、审批或查询流程。

### 8.2 涉及模块

- `backend/app/services/chat_service.py`
- `backend/app/services/ticket_service.py`
- `backend/app/services/approval_service.py`
- `backend/app/services/trace_service.py`
- `backend/app/services/llm_client.py`
- `backend/app/services/prompt_templates.py`
- `frontend/app/chat/page.tsx`
- `frontend/lib/chat.ts`

### 8.3 功能内容

新增意图识别结果：

```json
{
  "intent": "knowledge_qa",
  "confidence": 0.91,
  "need_ticket": false,
  "need_approval": false,
  "reason": "用户询问 VPN 配置，适合走知识库问答。"
}
```

支持意图：

- `knowledge_qa`
- `create_ticket`
- `ticket_query`
- `approval_query`
- `unknown`

新增风险判断结果：

```json
{
  "risk_level": "medium",
  "risk_reason": "请求涉及账号访问问题，但未要求绕过审批或修改权限。",
  "requires_approval": false
}
```

风险判断关注：

- 账号和权限。
- 安全事件。
- 财务操作。
- 生产中断。
- 数据访问。
- 绕过流程或审批的请求。

### 8.4 验收标准

- 同一个 Chat 输入可以识别问答或建单意图。
- 高风险动作必须进入人工审批或审批建议流程。
- 模型不能直接查询越权数据。
- 模型不能直接修改数据库状态。
- Trace 能解释为什么选择某条路由、为什么需要审批。

### 8.5 风险点

- 需要谨慎处理权限边界，模型只能给出意图和理由，不能决定用户能看什么。
- 前端交互可能需要调整，避免用户以为模型已经自动执行了高风险动作。
- 意图识别置信度低时，应保守处理，提示用户补充信息或创建普通工单。

## 9. 联调配置清单

本地开发和单元测试不需要真实 API Key。

真实模型联调需要在后端环境变量中配置：

```text
LLM_ENABLED=true
OPENAI_API_KEY=<实际 key>
LLM_MODEL=gpt-4.1-mini
EMBEDDING_MODEL=text-embedding-3-small
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2
```

如果使用 OpenAI 兼容服务，额外配置：

```text
OPENAI_BASE_URL=<兼容服务地址>
```

## 10. 建议里程碑

### 里程碑 A：模型可调用但业务无侵入

包含：

- 节点 1

结果：

- 项目具备可复用模型访问层。
- 现有业务和测试保持稳定。

### 里程碑 B：知识库检索升级

包含：

- 节点 1
- 节点 2

结果：

- 新文档可使用真实 embedding。
- 知识库检索语义质量提升。

### 里程碑 C：真实 Chat/RAG 能力

包含：

- 节点 1
- 节点 2
- 节点 3

结果：

- Chat 基于知识库生成带引用回答。
- 无来源不编造。
- Trace 可复盘模型链路。

### 里程碑 D：最小可交付 AI Agent

包含：

- 节点 1
- 节点 2
- 节点 3
- 节点 4

结果：

- 真实 embedding。
- RAG 大模型回答。
- 工单草稿大模型提取。
- Trace 记录关键模型输入和输出。

### 里程碑 E：企业支持 Agent 增强

包含：

- 节点 5

结果：

- 支持意图识别。
- 支持风险判断。
- 高风险流程保留人工审批。

## 11. 建议下一步

建议先实现节点 1，原因是它是所有后续能力的基础，并且可以在没有 API Key 的情况下完成开发和单元测试。

节点 1 完成后，再推进节点 2 和节点 3，先形成知识库问答的真实大模型闭环。节点 4 可以在 Chat/RAG 稳定后接入，节点 5 放到基础 Agent 能力稳定后再做。
