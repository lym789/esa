# Day 5 Embedding 与检索设计

## 目标

Day 5 在 Day 4 已生成 `document_chunks` 的基础上，为 chunk 生成 embedding，并实现按问题检索相关 chunk 的能力。

本阶段只做“向量生成、向量存储、相似度检索和引用格式化”，不生成最终自然语言回答。

## 范围

- `document_chunks` 增加 embedding 存储字段。
- 文档解析完成后为每个 chunk 写入 embedding。
- 新增 `services/rag_service.py`：
  - `embed_text(text: str) -> list[float]`
  - `embed_chunks(chunks: list[str]) -> list[list[float]]`
  - `search(db, query: str, top_k: int = 5, similarity_threshold: float | None = None)`
  - `format_citations(chunks)`
- 新增检索 API：`POST /api/search`。
- 检索结果返回 chunk 内容、文档名、页码、章节、相似度和 metadata。

## 本地 embedding 策略

MVP 阶段优先保证本地开发和测试不依赖外部网络或真实 OpenAI Key。`embed_text()` 先使用确定性的轻量 hash embedding：

- 分词包含英文单词、数字、中文字符和中文 bigram。
- 使用固定维度向量。
- 对 token 做 hash 后累加权重。
- 最终做 L2 归一化。

这样可以在无网络环境下完成检索链路验证。后续接入真实 OpenAI embedding 时，只需要替换 `embed_text()` 内部实现，外部接口不变。

## 数据模型

`document_chunks` 新增：

- `embedding_json`: JSON 字符串形式保存 embedding。
- `embedding_model`: 当前使用的 embedding 模型名，MVP 默认 `local-hash-v1`。

暂时不直接使用 pgvector 列，避免 SQLite 测试环境和 PostgreSQL pgvector 类型不兼容。Day 5 先把检索链路打通，后续再迁移到 pgvector。

## API 设计

### `POST /api/search`

权限：登录用户。

请求：

```json
{
  "query": "VPN 怎么登录？",
  "top_k": 5
}
```

响应：

```json
{
  "query": "VPN 怎么登录？",
  "results": [
    {
      "chunk_id": 1,
      "document_id": 1,
      "document_name": "IT_VPN_FAQ.md",
      "content": "……",
      "page": 1,
      "section": "VPN 使用说明",
      "similarity": 0.91,
      "metadata": {}
    }
  ],
  "citations": [
    "[1] IT_VPN_FAQ.md，第 1 页，VPN 使用说明"
  ]
}
```

## 验收标准

- 文档上传并解析完成后，chunk 记录包含 embedding。
- 给定问题可以检索出 top 5 以内的相关 chunk。
- 低于阈值的结果不会返回。
- 检索结果包含 chunk 内容、文档名、页码或章节、相似度和 metadata。
- 无相关内容时返回空结果和空引用。

## 非目标

- 不实现 Chat API。
- 不实现 RAG Prompt。
- 不调用 LLM 生成回答。
- 不强制依赖真实 OpenAI embedding。
- 不迁移 pgvector 索引。
