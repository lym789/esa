# Day 3 文档上传 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现管理员文档上传、本地存储、数据库记录和最小前端文档管理页。

**Architecture:** 后端新增 `documents` 模型、schema、service 和 API router，沿用当前 FastAPI + SQLAlchemy + `Base.metadata.create_all()` 初始化方式。前端新增文档 API 封装和 `/admin/documents` 页面，Dashboard 的“文档”卡片跳转到该页面。

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic v2, python-multipart, Next.js 14 App Router, React 18, TypeScript.

## Global Constraints

- 仅支持 `.md`、`.txt`、`.pdf` 上传。
- 文件保存到 `backend/app/storage/documents/`。
- Day 3 不做解析、chunk、embedding、RAG。
- 上传、删除、重新解析接口仅允许 `admin`。
- 列表和详情接口允许任意登录用户访问。
- 页面可见文案使用中文；品牌名 `JadeFlow AI` 可保留。
- 当前项目不是 Git 仓库，跳过 commit 步骤。

---

## File Structure

- Create: `backend/app/models/document.py`：`Document` SQLAlchemy 模型。
- Modify: `backend/app/models/__init__.py`：导入新模型。
- Modify: `backend/app/db/init_db.py`：确保 `documents` 表参与 `create_all()`。
- Create: `backend/app/schemas/document.py`：API 响应模型。
- Create: `backend/app/services/document_service.py`：文件校验、保存、查询、删除、重置状态。
- Create: `backend/app/api/documents.py`：文档 API router。
- Modify: `backend/app/main.py`：注册文档 router。
- Create: `backend/tests/test_document_service.py`：服务层测试。
- Create: `backend/tests/test_documents_api.py`：接口测试。
- Create: `frontend/lib/documents.ts`：文档接口封装。
- Create: `frontend/app/admin/documents/page.tsx`：文档管理页。
- Modify: `frontend/components/Dashboard.tsx`：支持功能卡片跳转。
- Modify: `frontend/lib/dashboard-data.ts`：给“文档”卡片添加 `href`。
- Modify: `tests/test_day2_frontend_auth_scaffold.py` 或新增 `tests/test_day3_frontend_documents_scaffold.py`：前端脚手架检查。
- Create: `docs/day3-document-upload.md`：Day 3 中文说明。
- Modify: `README.md`：当前范围和下一阶段更新。

---

### Task 1: 后端 Document 模型与服务层

**Files:**
- Create: `backend/app/models/document.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/db/init_db.py`
- Create: `backend/app/services/document_service.py`
- Create: `backend/tests/test_document_service.py`

**Interfaces:**
- Produces: `Document` model.
- Produces: `create_document_from_upload(db, file, uploaded_by, storage_dir) -> Document`.
- Produces: `list_documents(db) -> list[Document]`.
- Produces: `get_document(db, document_id) -> Document | None`.
- Produces: `reset_document_for_reindex(db, document) -> Document`.
- Produces: `delete_document(db, document, storage_dir) -> None`.

- [ ] **Step 1: Write failing service tests**

Create tests for:

```python
def test_create_document_from_upload_saves_file_and_record():
    ...

def test_create_document_rejects_unsupported_extension():
    ...

def test_create_document_rejects_empty_file():
    ...

def test_delete_document_removes_record_and_file():
    ...
```

- [ ] **Step 2: Run service tests and verify failure**

Run: `backend/.venv/bin/pytest backend/tests/test_document_service.py -q`

Expected: fails because `app.models.document` and `app.services.document_service` do not exist.

- [ ] **Step 3: Implement `Document` model**

Model fields:

```python
id, original_filename, stored_filename, content_type, file_extension,
file_size, storage_path, status, chunk_count, error_message,
uploaded_by_id, created_at, updated_at
```

- [ ] **Step 4: Implement service functions**

Rules:

- allowed extensions: `{".md", ".txt", ".pdf"}`
- empty files raise `HTTPException(400, "Uploaded file is empty")`
- unsupported files raise `HTTPException(400, "Unsupported file type")`
- stored filename format: `<uuid4><extension>`
- storage path persisted relative to `settings.storage_dir`, e.g. `documents/<uuid>.md`

- [ ] **Step 5: Run service tests**

Run: `backend/.venv/bin/pytest backend/tests/test_document_service.py -q`

Expected: all service tests pass.

---

### Task 2: 后端 Documents API

**Files:**
- Create: `backend/app/schemas/document.py`
- Create: `backend/app/api/documents.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_documents_api.py`

**Interfaces:**
- Consumes: `Document` model and service functions from Task 1.
- Produces routes:
  - `POST /api/documents/upload`
  - `GET /api/documents`
  - `GET /api/documents/{document_id}`
  - `POST /api/documents/{document_id}/reindex`
  - `DELETE /api/documents/{document_id}`

- [ ] **Step 1: Write failing API tests**

Create tests for:

```python
def test_admin_can_upload_document():
    ...

def test_employee_cannot_upload_document():
    ...

def test_list_and_detail_return_uploaded_document():
    ...

def test_reindex_resets_document_status():
    ...

def test_delete_document_removes_document():
    ...
```

- [ ] **Step 2: Run API tests and verify failure**

Run: `backend/.venv/bin/pytest backend/tests/test_documents_api.py -q`

Expected: fails because document API is not registered.

- [ ] **Step 3: Implement schemas**

`DocumentResponse` should expose:

```python
id, original_filename, stored_filename, content_type, file_extension,
file_size, storage_path, status, chunk_count, error_message,
uploaded_by_id, created_at, updated_at
```

- [ ] **Step 4: Implement router**

Use:

```python
current_user: User = Depends(require_roles(["admin"]))
```

for upload, delete, reindex.

Use:

```python
current_user: User = Depends(get_current_user)
```

for list and detail.

- [ ] **Step 5: Register router in `main.py`**

Add:

```python
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
```

- [ ] **Step 6: Run API tests**

Run: `backend/.venv/bin/pytest backend/tests/test_documents_api.py -q`

Expected: all API tests pass.

---

### Task 3: 前端文档管理页

**Files:**
- Create: `frontend/lib/documents.ts`
- Create: `frontend/app/admin/documents/page.tsx`
- Modify: `frontend/components/Dashboard.tsx`
- Modify: `frontend/lib/dashboard-data.ts`
- Create: `tests/test_day3_frontend_documents_scaffold.py`

**Interfaces:**
- Consumes: existing `getStoredSession()` and `CurrentUser`.
- Produces: `listDocuments(accessToken: string)`.
- Produces: `uploadDocument(accessToken: string, file: File)`.
- Produces: `/admin/documents` client page.

- [ ] **Step 1: Write failing frontend scaffold tests**

Check:

```python
assert "app/admin/documents/page.tsx" exists
assert "uploadDocument" in frontend/lib/documents.ts
assert "/admin/documents" in frontend/lib/dashboard-data.ts
```

- [ ] **Step 2: Run scaffold tests and verify failure**

Run: `python3 -m unittest tests.test_day3_frontend_documents_scaffold -v`

Expected: fails before files exist.

- [ ] **Step 3: Implement `frontend/lib/documents.ts`**

Functions:

```ts
export async function listDocuments(accessToken: string): Promise<DocumentRecord[]>
export async function uploadDocument(accessToken: string, file: File): Promise<DocumentRecord>
export async function deleteDocument(accessToken: string, documentId: number): Promise<void>
export async function reindexDocument(accessToken: string, documentId: number): Promise<DocumentRecord>
```

- [ ] **Step 4: Implement `/admin/documents` page**

Behavior:

- Redirect to `/login` when no session.
- Show uploader only when `currentUser.role === "admin"`.
- Upload success refreshes list.
- API errors display Chinese message.

- [ ] **Step 5: Wire Dashboard document card**

Add `href: "/admin/documents"` to the “文档” feature. In `Dashboard.tsx`, use `router.push(item.href)` when present.

- [ ] **Step 6: Run frontend checks**

Run:

```bash
python3 -m unittest tests.test_day3_frontend_documents_scaffold -v
cd frontend && NEXT_PUBLIC_API_BASE_URL=http://localhost:8003 npm run build
```

Expected: scaffold tests and build pass.

---

### Task 4: 文档与端到端验证

**Files:**
- Create: `docs/day3-document-upload.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: implemented Day 3 APIs and frontend route.
- Produces: Chinese documentation for running and validating Day 3.

- [ ] **Step 1: Write Day 3 docs**

Document:

- supported file types
- backend API list
- storage directory
- admin-only operations
- manual validation commands

- [ ] **Step 2: Update README**

Update current range from Day 2 to Day 3 and next phase from Day 3 to Day 4.

- [ ] **Step 3: Run full focused verification**

Run:

```bash
backend/.venv/bin/pytest backend/tests/test_auth_service.py backend/tests/test_auth_api.py backend/tests/test_document_service.py backend/tests/test_documents_api.py -q
python3 -m unittest tests.test_day1_scaffold tests.test_day2_frontend_auth_scaffold tests.test_day3_frontend_documents_scaffold -v
cd frontend && NEXT_PUBLIC_API_BASE_URL=http://localhost:8003 npm run build
```

Expected: all pass.

---

## Self-Review

- Spec coverage: model, upload API, list/detail, reindex, delete, frontend minimal page and docs are covered.
- Placeholder scan: no `TBD` or undefined placeholder steps remain.
- Type consistency: service, schema and frontend function names are consistent across tasks.
- Scope check: parsing, chunk, embedding and RAG are explicitly excluded and left for later days.
