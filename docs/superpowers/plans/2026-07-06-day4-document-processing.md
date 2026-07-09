# Day 4 文档解析与 Chunk 切分 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 上传文档后自动解析文件内容、生成 chunk 记录，并更新文档状态和 chunk 数量。

**Architecture:** 新增 `DocumentChunk` 模型和 `document_processing_service`。上传接口保存文件后同步调用解析流程，重新解析接口复用同一流程。解析失败不抛出到用户请求之外，而是把文档状态保存为 `failed` 并记录错误。

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic v2, pypdf, SQLite-compatible tests, PostgreSQL-compatible SQLAlchemy models.

## Global Constraints

- Day 4 不做 embedding、pgvector 和 RAG。
- Markdown/TXT 直接按 UTF-8 读取。
- PDF 使用 `pypdf.PdfReader` 提取文本。
- 切分使用 `settings.chunk_size=800` 和 `settings.chunk_overlap=120`。
- 页面可见文案继续使用中文。
- 当前项目不是 Git 仓库，跳过 commit 步骤。

---

### Task 1: Chunk 模型与处理服务

**Files:**
- Create: `backend/app/models/document_chunk.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/db/init_db.py`
- Create: `backend/app/services/document_processing_service.py`
- Create: `backend/tests/test_document_processing_service.py`

**Interfaces:**
- Produces: `DocumentChunk`
- Produces: `split_text_into_chunks(text: str, chunk_size: int, chunk_overlap: int) -> list[str]`
- Produces: `process_document(db: Session, document: Document, storage_dir: str, chunk_size: int, chunk_overlap: int) -> Document`

- [ ] Write failing service tests.
- [ ] Run service tests and confirm missing module failure.
- [ ] Add `DocumentChunk` model.
- [ ] Implement text/PDF parsing and chunk splitting.
- [ ] Implement `process_document()` status flow.
- [ ] Run service tests and confirm pass.

### Task 2: API 联动解析

**Files:**
- Modify: `backend/app/api/documents.py`
- Modify: `backend/app/services/document_service.py`
- Modify: `backend/tests/test_documents_api.py`

**Interfaces:**
- Consumes: `process_document()`
- Produces: upload and reindex responses with updated `status` and `chunk_count`

- [ ] Update API tests to expect `completed` after upload.
- [ ] Run API tests and confirm failure.
- [ ] Call `process_document()` after upload and reindex.
- [ ] Ensure delete removes chunks before document row.
- [ ] Run API tests and confirm pass.

### Task 3: 前端与文档更新

**Files:**
- Modify: `frontend/app/admin/documents/page.tsx`
- Create: `docs/day4-document-processing.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: `status=completed/failed`, `chunk_count`
- Produces: Chinese Day 4 documentation.

- [ ] Adjust frontend status copy if needed.
- [ ] Add Day 4 docs.
- [ ] Update README current range and next phase.
- [ ] Run frontend build.

### Task 4: Final Verification

Run:

```bash
backend/.venv/bin/pytest backend/tests/test_auth_service.py backend/tests/test_auth_api.py backend/tests/test_document_service.py backend/tests/test_document_processing_service.py backend/tests/test_documents_api.py -q
python3 -m unittest tests.test_day1_scaffold tests.test_day2_frontend_auth_scaffold tests.test_day3_frontend_documents_scaffold -v
cd frontend && NEXT_PUBLIC_API_BASE_URL=http://localhost:8003 npm run build
```

Expected:

- Backend tests pass.
- Frontend scaffold tests pass.
- Next.js build passes.

## Self-Review

- Spec coverage: model, parser, chunker, upload/reindex integration, docs and tests are covered.
- Placeholder scan: no unresolved placeholder remains.
- Scope check: embedding and RAG are explicitly excluded.
