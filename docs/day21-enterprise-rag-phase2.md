# Day 21 企业级 RAG Phase 2

本阶段完成企业知识接入链路的结构化、批量化、版本化和异步化基础。

## 已完成

### 结构感知解析与切块

- Markdown 按一级到六级标题拆分逻辑区段。
- chunk 元数据保存完整标题路径，例如 `IT 制度 > VPN > 故障排查`。
- 优先按段落边界组合 chunk，只有超长段落才退回固定窗口切分。
- 保留原固定窗口函数，兼容 TXT、PDF 长段和既有测试。

### 批量 Embedding

- 文档的所有待索引 chunk 一次调用 `embed_texts`。
- 批量响应数量必须与输入数量一致。
- 模型调用失败或客户端不支持批量接口时，安全退回本地 embedding。
- 每个版本记录实际使用的 embedding 模型。

### 文档版本与原子发布

- 新增 `document_versions`，记录版本号、解析器、切块器、embedding 模型、chunk 数和错误。
- chunk 绑定具体 `document_version_id`。
- 新版本完整索引成功后，才切换 `documents.current_version_id`。
- 上一版本切换为 `retired`，历史 chunk 继续保留以供审计。
- 重新索引失败时，失败版本记录错误，当前线上版本继续提供检索服务。
- 在线检索和 Dashboard 只查询当前发布版本。

版本历史接口：

```text
GET /api/documents/{document_id}/versions
```

### 持久化异步任务

- 新增 `document_processing_jobs` 数据表。
- 状态包含 `queued / processing / completed / failed`。
- 重复提交同一文档时复用仍在运行的任务。
- PostgreSQL worker 使用 `FOR UPDATE SKIP LOCKED` 安全领取任务，可横向增加 worker。
- 任务、尝试次数、错误和时间信息在服务重启后仍保留。

异步接口：

```text
POST /api/documents/upload-async
POST /api/documents/{document_id}/reindex-async
GET  /api/documents/jobs/{job_id}
```

兼容期内保留原同步接口。业务前端切换到异步接口并完成轮询后，可以再下线同步处理路径。

## Worker 启动

持续处理任务：

```bash
cd backend
python -m app.workers.document_worker
```

只处理一个任务后退出：

```bash
python -m app.workers.document_worker --once
```

Docker Compose 已新增 `document-worker` 服务，正常启动 Compose 时会自动运行。

## 数据库迁移

新增迁移版本：

```text
0002_document_versioning
0003_document_processing_jobs
```

迁移会把已有 chunk 关联到自动生成的 legacy 版本，不影响历史知识继续检索。

## 验证结果

- 后端完整测试：119 passed，1 skipped。
- 根目录前端 scaffold 测试：53 passed。
- PostgreSQL/pgvector 事务集成测试：1 passed。
- Docker Compose 配置验证通过。
- `git diff --check` 通过。

## 下一阶段

Phase 3 将提升在线检索质量：

1. 查询规范化与多轮独立问题改写。
2. lexical 召回与 dense 召回并行执行。
3. RRF 融合和候选去重。
4. 可插拔 reranker。
5. MMR、邻接块和父块上下文装配。
6. 使用真实黄金集调整 Top-K、阈值和融合权重。
