# Day 5 Embedding 与检索

Day 5 在 Day 4 的 chunk 基础上，完成 embedding 生成、embedding 存储、相似度检索和引用格式化。

## 已实现能力

- 文档解析生成 chunk 时，同步生成 embedding。
- `document_chunks` 新增：
  - `embedding_json`
  - `embedding_model`
- 新增 `services/rag_service.py`：
  - `embed_text(text)`
  - `embed_chunks(chunks)`
  - `search(db, query, top_k, similarity_threshold)`
  - `format_citations(results)`
- 新增检索接口：
  - `POST /api/search`

## 本地 embedding 策略

当前使用确定性的本地 hash embedding：

- 不需要真实 OpenAI API Key；
- 不需要网络；
- 测试结果稳定；
- 可以跑通 embedding、存储、检索、引用的完整链路。

后续接入真实 OpenAI embedding 时，只需要替换 `embed_text()` 内部实现，外部接口可以保持不变。

## 检索接口

### `POST /api/search`

权限：登录用户。

请求：

```json
{
  "query": "VPN 登录不了怎么办",
  "top_k": 5
}
```

响应：

```json
{
  "query": "VPN 登录不了怎么办",
  "results": [
    {
      "chunk_id": 1,
      "document_id": 1,
      "document_name": "IT_VPN_FAQ.md",
      "content": "VPN 登录失败时，请检查统一身份认证和网络连接。",
      "page": 1,
      "section": "VPN 使用说明",
      "similarity": 0.24,
      "metadata": {
        "document_id": 1,
        "filename": "IT_VPN_FAQ.md",
        "chunk_index": 0,
        "page": 1,
        "section": "VPN 使用说明"
      }
    }
  ],
  "citations": [
    "[1] IT_VPN_FAQ.md，第 1 页，VPN 使用说明"
  ]
}
```

## 阈值

检索会使用配置项过滤低相似度结果：

```text
RAG_SIMILARITY_THRESHOLD=0.75
```

本地 hash embedding 与真实 embedding 的分数分布不同。开发阶段可以按本地检索效果临时调低阈值；后续接入真实 embedding 后再恢复或重新校准。

## 自动验证

```bash
backend/.venv/bin/pytest backend/tests/test_rag_service.py backend/tests/test_search_api.py -q
```

完整后端聚焦测试：

```bash
backend/.venv/bin/pytest backend/tests/test_auth_service.py backend/tests/test_auth_api.py backend/tests/test_document_service.py backend/tests/test_document_processing_service.py backend/tests/test_documents_api.py backend/tests/test_rag_service.py backend/tests/test_search_api.py -q
```

## 下一步

Day 6 将实现 Chat 与 RAG 问答：调用检索服务获取相关 chunk，构造带引用的回答，并在没有依据时拒答。
