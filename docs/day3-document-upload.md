# Day 3 文档上传与存储

Day 3 完成管理员文档上传、本地文件存储和数据库记录，为 Day 4 文档解析与 chunk 切分做准备。

## 已实现能力

- 管理员上传 `.md`、`.txt`、`.pdf` 文档。
- 文件保存到后端本地目录 `backend/app/storage/documents/`。
- 上传成功后写入 `documents` 表。
- 文档初始状态为 `pending`。
- 文档列表和详情接口可供登录用户查看。
- 管理员可以删除文档。
- 管理员可以触发重新解析占位接口，把状态重置为 `pending`。
- 前端新增 `/admin/documents` 文档管理页。
- Dashboard 的“文档”卡片会跳转到文档管理页。

## 后端接口

所有接口都需要登录。

| 方法 | 路径 | 权限 | 用途 |
| --- | --- | --- | --- |
| `POST` | `/api/documents/upload` | admin | 上传文档 |
| `GET` | `/api/documents` | 登录用户 | 文档列表 |
| `GET` | `/api/documents/{id}` | 登录用户 | 文档详情 |
| `POST` | `/api/documents/{id}/reindex` | admin | 重置为等待解析 |
| `DELETE` | `/api/documents/{id}` | admin | 删除文档 |

## 支持的文件类型

- `.md`
- `.txt`
- `.pdf`

空文件和其他扩展名会返回 `400`。

## 状态说明

Day 3 只负责上传和入库，因此新文档状态为：

```text
pending
```

后续 Day 4 会接入：

```text
pending -> processing -> completed
pending -> processing -> failed
```

## 前端页面

文档管理页：

```text
http://localhost:3000/admin/documents
```

如果使用自定义端口，例如 3003：

```text
http://localhost:3003/admin/documents
```

管理员账号可以上传、删除和重新解析。普通账号只能查看列表，并会看到只读提示。

## 手动验证

使用管理员账号登录：

```text
admin@example.com
123456
```

上传一份 Markdown 文件，例如 `IT_VPN_FAQ.md`。

上传后检查：

- 页面列表出现该文件；
- 状态为 `等待解析`；
- Chunk 数量为 `0`；
- 后端目录 `backend/app/storage/documents/` 中出现保存后的文件。

## 自动验证

后端：

```bash
backend/.venv/bin/pytest backend/tests/test_document_service.py backend/tests/test_documents_api.py -q
```

前端：

```bash
python3 -m unittest tests.test_day3_frontend_documents_scaffold -v
cd frontend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8003 npm run build
```

## 下一步

Day 4 将实现文档解析与 chunk 切分，让上传后的文档从 `pending` 进入 `processing / completed / failed` 状态，并写入 chunk 记录。
