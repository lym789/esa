# Day 5 Embedding 与检索 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 document chunks 生成 embedding，并实现登录用户可调用的相似度检索接口。

**Architecture:** `document_chunks` 保存 `embedding_json` 和 `embedding_model`。`rag_service.py` 提供本地确定性 embedding、余弦相似度、搜索和引用格式化。Day 4 的文档处理流程在创建 chunk 时同步写入 embedding。

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic v2, deterministic local hash embedding, cosine similarity.

## Global Constraints

- 不依赖真实 OpenAI Key。
- 不做 Chat API 和 RAG 回答。
- 不引入 pgvector 列，先用 JSON 存储 embedding。
- 检索结果必须包含 chunk 内容、文档名、页码或章节、相似度和 metadata。
- 页面可见文案继续使用中文。
- 当前项目不是 Git 仓库，跳过 commit。

---

### Task 1: RAG Service

**Files:**
- Create: `backend/app/services/rag_service.py`
- Create: `backend/tests/test_rag_service.py`

**Interfaces:**
- Produces: `embed_text(text: str) -> list[float]`
- Produces: `embed_chunks(chunks: list[str]) -> list[list[float]]`
- Produces: `cosine_similarity(left: list[float], right: list[float]) -> float`
- Produces: `search(db: Session, query: str, top_k: int = 5, similarity_threshold: float | None = None) -> list[SearchResult]`
- Produces: `format_citations(results: list[SearchResult]) -> list[str]`

- [ ] Write failing tests for deterministic embedding, search ranking and threshold filtering.
- [ ] Run tests and confirm missing module failure.
- [ ] Implement service.
- [ ] Run tests and confirm pass.

### Task 2: Chunk Embedding Persistence

**Files:**
- Modify: `backend/app/models/document_chunk.py`
- Modify: `backend/app/services/document_processing_service.py`
- Modify: `backend/tests/test_document_processing_service.py`

**Interfaces:**
- Consumes: `embed_text()`
- Produces chunk rows with `embedding_json` and `embedding_model`

- [ ] Update processing tests to assert embedding is saved.
- [ ] Run tests and confirm failure.
- [ ] Add model fields and write embeddings during chunk creation.
- [ ] Run processing tests and confirm pass.

### Task 3: Search API

**Files:**
- Create: `backend/app/schemas/search.py`
- Create: `backend/app/api/search.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_search_api.py`

**Interfaces:**
- Consumes: `rag_service.search()` and `format_citations()`
- Produces: `POST /api/search`

- [ ] Write failing API tests for authenticated search and missing token rejection.
- [ ] Run tests and confirm route missing failure.
- [ ] Implement schema and router.
- [ ] Register router in `main.py`.
- [ ] Run API tests and confirm pass.

### Task 4: Docs and Verification

**Files:**
- Create: `docs/day5-embedding-search.md`
- Modify: `README.md`

- [ ] Add Chinese Day 5 documentation.
- [ ] Update README current scope and next phase.
- [ ] Run backend, scaffold and frontend build verification.

## Final Verification

```bash
backend/.venv/bin/pytest backend/tests/test_auth_service.py backend/tests/test_auth_api.py backend/tests/test_document_service.py backend/tests/test_document_processing_service.py backend/tests/test_documents_api.py backend/tests/test_rag_service.py backend/tests/test_search_api.py -q
python3 -m unittest tests.test_day1_scaffold tests.test_day2_frontend_auth_scaffold tests.test_day3_frontend_documents_scaffold -v
cd frontend && NEXT_PUBLIC_API_BASE_URL=http://localhost:8003 npm run build
```

## Self-Review

- Spec coverage: embedding, chunk persistence, search, citations, API and docs are covered.
- Placeholder scan: no unresolved placeholder remains.
- Scope check: Chat/RAG answer generation and pgvector migration are excluded.
