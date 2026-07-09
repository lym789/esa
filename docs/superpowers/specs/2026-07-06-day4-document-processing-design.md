# Day 4 文档解析与 Chunk 切分设计

## 目标

Day 4 在 Day 3 的上传与存储基础上，完成文档解析和 chunk 切分。管理员上传 `.md`、`.txt`、`.pdf` 后，系统应读取文件内容，生成 `document_chunks` 记录，并把文档状态更新为 `completed` 或 `failed`。

## 范围

- 新增 `document_chunks` 数据表。
- Markdown 和 TXT 使用 UTF-8 文本读取。
- PDF 使用 `pypdf.PdfReader` 按页提取文本。
- 使用 `settings.chunk_size` 和 `settings.chunk_overlap` 切分文本。
- 每个 chunk 保存文档 ID、chunk 序号、内容、页码、section 和 metadata JSON。
- 上传成功后立即解析并切分，MVP 阶段先同步执行，后续文件变大再改为后台任务。
- 重新解析接口会删除旧 chunk，重新解析文件，并更新 `chunk_count`。
- 解析失败时文档状态为 `failed`，`error_message` 保存失败原因。

## 非目标

- 不生成 embedding。
- 不接入 pgvector。
- 不做 RAG 检索。
- 不支持 DOCX、Excel、OCR 或复杂表格解析。

## 状态流转

```text
pending -> processing -> completed
pending -> processing -> failed
```

重新解析：

```text
completed/failed -> processing -> completed/failed
```

## Chunk 字段

`document_chunks` 字段：

- `id`
- `document_id`
- `chunk_index`
- `content`
- `content_length`
- `page`
- `section`
- `metadata_json`
- `created_at`

`metadata_json` 示例：

```json
{
  "document_id": 1,
  "filename": "IT_VPN_FAQ.md",
  "chunk_index": 0,
  "page": 1,
  "section": "VPN 使用说明"
}
```

## 验收标准

- 管理员上传 Markdown 后，响应中的 `status` 为 `completed`。
- `chunk_count` 大于 0。
- 数据库中的 `document_chunks` 数量与 `documents.chunk_count` 一致。
- 重新解析会先删除旧 chunk，再生成新 chunk。
- 解析失败时状态为 `failed`，并能看到错误原因。

## 测试策略

- 服务层测试 chunk 切分、重叠、Markdown section 提取。
- 服务层测试 `process_document()` 能创建 chunk 并更新文档状态。
- API 测试上传后状态为 `completed` 且 `chunk_count > 0`。
- API 测试重新解析后仍保持 chunk 数一致。
- 保留 Day 1、Day 2、Day 3 测试，防止回归。
