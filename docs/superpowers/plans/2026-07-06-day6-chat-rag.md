# Day 6 Chat 与 RAG 问答 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 提供最小可用 Chat API，保存对话消息，并基于检索结果返回带引用的 RAG 回答。

**Architecture:** 新增 conversation/message 模型和 chat_service。Chat service 复用 Day 5 `rag_service.search()`，有来源时生成 extractive answer，无来源时返回固定拒答。API 层负责鉴权和当前用户对话边界。

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic v2, existing local RAG search.

## Global Constraints

- 不调用真实 LLM。
- 不做工单 Agent、意图识别或 Trace。
- 登录用户只能访问自己的对话。
- 无来源时必须固定拒答。
- 当前项目不是 Git 仓库，跳过 commit。

---

### Task 1: Chat 模型与服务

**Files:**
- Create: `backend/app/models/conversation.py`
- Create: `backend/app/models/message.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/db/init_db.py`
- Create: `backend/app/services/chat_service.py`
- Create: `backend/tests/test_chat_service.py`

**Interfaces:**
- Produces: `create_conversation(db, user, title=None)`
- Produces: `list_conversations(db, user)`
- Produces: `get_conversation_for_user(db, conversation_id, user)`
- Produces: `send_message(db, conversation, content, top_k, similarity_threshold)`

- [ ] Write failing service tests.
- [ ] Run tests and confirm missing module failure.
- [ ] Implement models and service.
- [ ] Run service tests and confirm pass.

### Task 2: Chat API

**Files:**
- Create: `backend/app/schemas/chat.py`
- Create: `backend/app/api/chat.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_chat_api.py`

**Interfaces:**
- Produces:
  - `POST /api/chat/conversations`
  - `GET /api/chat/conversations`
  - `GET /api/chat/conversations/{id}`
  - `POST /api/chat/conversations/{id}/messages`

- [ ] Write failing API tests.
- [ ] Run tests and confirm route missing failure.
- [ ] Implement schemas and router.
- [ ] Register router.
- [ ] Run API tests and confirm pass.

### Task 3: Docs and Verification

**Files:**
- Create: `docs/day6-chat-rag.md`
- Modify: `README.md`

- [ ] Add Chinese Day 6 documentation.
- [ ] Update README current scope and next phase.
- [ ] Run full focused verification.

## Final Verification

```bash
backend/.venv/bin/pytest backend/tests/test_auth_service.py backend/tests/test_auth_api.py backend/tests/test_document_service.py backend/tests/test_document_processing_service.py backend/tests/test_documents_api.py backend/tests/test_rag_service.py backend/tests/test_search_api.py backend/tests/test_chat_service.py backend/tests/test_chat_api.py -q
python3 -m unittest tests.test_day1_scaffold tests.test_day2_frontend_auth_scaffold tests.test_day3_frontend_documents_scaffold -v
cd frontend && NEXT_PUBLIC_API_BASE_URL=http://localhost:8003 npm run build
```

## Self-Review

- Spec coverage: conversation CRUD, message send, RAG answer, refusal and ownership checks are covered.
- Placeholder scan: no unresolved placeholder remains.
- Scope check: LLM, ticket Agent and Trace are excluded.
