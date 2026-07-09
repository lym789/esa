# Day 3 文档上传与存储设计

## 目标

Day 3 实现管理员文档上传与本地存储能力，为后续 Day 4 文档解析、chunk 切分、Day 5 embedding 与检索做准备。

本阶段只处理“文件接收、文件校验、文件落盘、数据库记录、列表查询和基础管理”，不实现解析、chunk、embedding、RAG 问答或前端复杂文档工作流。

## 范围

后端新增 `documents` 模块：

- 管理员可以上传 `.md`、`.txt`、`.pdf` 文件。
- 文件保存到 `backend/app/storage/documents/`。
- 上传成功后创建 `documents` 数据库记录。
- 文档初始状态为 `pending`。
- 文档列表显示状态、文件大小、上传人、chunk 数量和错误信息。
- 删除文档时删除数据库记录，并尝试删除本地文件。
- 重新解析接口本阶段只把状态重置为 `pending`，为 Day 4 解析流程预留入口。

前端新增最小文档管理入口：

- 从 Dashboard 的“文档”卡片进入文档管理页。
- 页面允许管理员上传文档。
- 页面显示文档列表和基础状态。
- 非管理员用户访问上传能力时应看到清晰提示，后端仍作为最终权限边界。

## 非目标

- 不解析文件内容。
- 不生成 chunk。
- 不调用 OpenAI embedding。
- 不接入 pgvector。
- 不实现 RAG 问答。
- 不做复杂 PDF 表格、OCR、DOCX、Excel 支持。

## 数据模型

新增 `Document` 模型，表名为 `documents`。

字段：

- `id`: 主键。
- `original_filename`: 用户上传时的原始文件名。
- `stored_filename`: 后端保存到磁盘的安全文件名。
- `content_type`: 上传请求中的文件 MIME 类型。
- `file_extension`: 小写扩展名，允许 `.md`、`.txt`、`.pdf`。
- `file_size`: 文件大小，单位 byte。
- `storage_path`: 相对 `settings.storage_dir` 的存储路径，例如 `documents/uuid.md`。
- `status`: 文档状态，Day 3 只产生 `pending`，并支持重置为 `pending`。
- `chunk_count`: chunk 数量，Day 3 固定为 `0`。
- `error_message`: 错误信息，Day 3 默认为空。
- `uploaded_by_id`: 上传用户 ID，关联 `users.id`。
- `created_at`: 创建时间。
- `updated_at`: 更新时间。

## API 设计

所有接口都需要登录。

### `POST /api/documents/upload`

权限：仅 `admin`。

请求：`multipart/form-data`，字段名 `file`。

校验：

- 必须提供文件。
- 文件名必须包含扩展名。
- 扩展名必须是 `.md`、`.txt`、`.pdf`。
- 文件内容不能为空。

成功返回：文档详情。

错误：

- 非管理员：`403`。
- 不支持的文件类型：`400`。
- 空文件：`400`。

### `GET /api/documents`

权限：任意登录用户。

返回：按创建时间倒序排列的文档列表。

### `GET /api/documents/{document_id}`

权限：任意登录用户。

返回：单个文档详情。

不存在返回 `404`。

### `POST /api/documents/{document_id}/reindex`

权限：仅 `admin`。

行为：把文档状态重置为 `pending`，`chunk_count` 重置为 `0`，`error_message` 清空。

### `DELETE /api/documents/{document_id}`

权限：仅 `admin`。

行为：删除数据库记录，并尽力删除本地文件。如果本地文件已经不存在，接口仍返回成功。

## 后端实现边界

文件保存逻辑放在 `services/document_service.py`，API 层只负责请求参数、权限依赖和响应模型。

服务层负责：

- 扩展名校验。
- 安全文件名生成。
- 目标目录创建。
- 文件保存。
- 数据库记录创建。
- 文档查询、删除、重置状态。

## 前端实现边界

新增 `frontend/lib/documents.ts` 封装文档 API。

新增 `frontend/app/admin/documents/page.tsx` 作为最小可用管理页。

Dashboard 的“文档”功能卡片点击后跳转到 `/admin/documents`。其他卡片暂时不跳转。

## 验收标准

- 管理员使用种子账号登录后可以上传 `.md` 文件。
- 上传后 `backend/app/storage/documents/` 下能看到保存的文件。
- `GET /api/documents` 能返回刚上传的文档。
- 文档状态为 `pending`，`chunk_count` 为 `0`。
- 非管理员调用上传接口返回 `403`。
- 上传 `.exe` 或无扩展名文件返回 `400`。
- 前端文档管理页可以显示上传后的文档。

## 测试策略

后端优先：

- 单元测试服务层文件类型校验、空文件拒绝、保存记录。
- API 测试管理员上传成功、非管理员禁止、列表可查、详情可查、重置状态、删除文档。

前端最小测试：

- 静态脚手架测试确认新增文档 API 封装和管理页面存在。
- `npm run build` 验证 TypeScript 和页面构建通过。

## 兼容性

本项目当前没有 Git 仓库元数据，也没有 Alembic。Day 3 延续 Day 2 的 `Base.metadata.create_all()` 初始化方式。后续表更多时再引入 Alembic。
