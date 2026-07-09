# Day 4 文档解析与 Chunk 切分

Day 4 在 Day 3 的文档上传基础上，完成文档解析、chunk 切分和状态流转。

## 已实现能力

- Markdown 和 TXT 文档按 UTF-8 直接读取。
- PDF 文档使用 `pypdf` 按页提取文本。
- 使用 `CHUNK_SIZE` 和 `CHUNK_OVERLAP` 切分文本。
- 新增 `document_chunks` 表保存分块内容。
- 上传文档后自动解析并生成 chunk。
- `documents.chunk_count` 与实际 chunk 数保持一致。
- 重新解析会删除旧 chunk，再重新生成。
- 解析失败时文档状态变为 `failed`，并保存 `error_message`。

## 状态流转

```text
pending -> processing -> completed
pending -> processing -> failed
```

重新解析：

```text
completed/failed -> processing -> completed/failed
```

## Chunk 内容

每条 chunk 保存：

- 文档 ID
- chunk 序号
- chunk 内容
- 内容长度
- 页码
- section
- metadata JSON

metadata 示例：

```json
{
  "document_id": 1,
  "filename": "IT_VPN_FAQ.md",
  "chunk_index": 0,
  "page": 1,
  "section": "VPN 使用说明"
}
```

## 配置项

来自 `.env` 或默认配置：

```text
CHUNK_SIZE=800
CHUNK_OVERLAP=120
```

## 手动验证

1. 使用管理员账号登录。
2. 打开文档管理页：

```text
http://localhost:3003/admin/documents
```

3. 上传 `.md`、`.txt` 或 `.pdf`。
4. 查看文档状态是否变为 `已完成`。
5. 查看分块数是否大于 `0`。

## 自动验证

```bash
backend/.venv/bin/pytest backend/tests/test_document_processing_service.py backend/tests/test_documents_api.py -q
```

完整后端聚焦测试：

```bash
backend/.venv/bin/pytest backend/tests/test_auth_service.py backend/tests/test_auth_api.py backend/tests/test_document_service.py backend/tests/test_document_processing_service.py backend/tests/test_documents_api.py -q
```

## 下一步

Day 5 将实现 embedding 与检索：为 chunk 生成向量，写入 pgvector，并支持按问题检索相关 chunk。
