# Day 20 企业级 RAG Phase 0/1

本阶段按照《Enterprise Support Agent 企业级 RAG 优化方案》完成评测与检索基础改造。

## 已完成

- 新增 RAG 离线评测框架，支持 Recall@K、MRR 和 nDCG@K。
- 新增 JSONL 黄金问题集格式及 5 条示例数据。
- `document_chunks` 新增 pgvector 原生向量字段，保留 JSON 字段作为迁移期兼容数据。
- PostgreSQL 使用数据库侧 cosine Top-K，不再加载全部 chunk 到 Python 计算。
- 本地 SQLite 测试继续使用确定性内存检索，保证单元测试不依赖外部服务。
- 新增幂等 schema migration runner 和迁移记录表。
- 自动回填已有 JSON 向量，并为 256 维本地向量、1536 维 OpenAI 向量创建独立 HNSW 索引。
- 文档新增发布状态、知识库范围、可见性、内容指纹、生效和失效时间。
- 新增角色级文档 ACL，并在数据库检索条件内执行权限过滤。
- Chat、Search API 和 Dashboard 知识搜索均传入当前用户权限。
- 新增管理员文档治理接口，可设置发布状态、知识库、可见性、角色和有效期。
- 文档 chunk 新增稳定 UID、内容指纹和估算 token 数。

## 数据库迁移

应用启动时只在 PostgreSQL 执行：

1. 确保 `vector` extension 存在。
2. `Base.metadata.create_all` 创建新表。
3. 按 `schema_migrations` 中的版本执行尚未应用的幂等迁移。

当前迁移版本：

```text
0001_enterprise_rag_phase1
```

## 文档治理接口

```text
PATCH /api/documents/{document_id}/governance
```

示例请求：

```json
{
  "publication_status": "published",
  "knowledge_base_id": "finance",
  "visibility": "restricted",
  "allowed_roles": ["approver", "admin"],
  "effective_at": null,
  "expires_at": null
}
```

只有管理员可以修改治理信息。`restricted` 文档必须至少配置一个允许角色。

## 离线评测

先把样例集复制为真实业务数据集，上传对应知识文档，然后执行：

```bash
cd backend
python -m app.evaluation.rag_evaluator evals/rag_golden.sample.jsonl --k 10 --output rag-eval-report.json
```

评测结果包含逐问题与聚合的 Recall@K、MRR 和 nDCG@K。

## 验证结果

- 后端完整测试：111 passed，1 skipped。
- PostgreSQL/pgvector 事务集成测试：1 passed。
- 本地数据库迁移成功，迁移版本已记录。
- 256/1536 维 HNSW 索引均已创建。
- PostgreSQL 集成测试数据在事务结束后回滚，不污染业务数据。

显式运行 PostgreSQL 集成测试：

```bash
cd backend
RUN_POSTGRES_TESTS=1 \
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/enterprise_support_agent \
python -m pytest tests/test_rag_postgres_integration.py -q
```

## 当前限制与下一步

- 样例黄金集只有 5 条，尚不能代表真实质量基线。
- 当前仍使用固定字符切块，下一阶段改为标题/段落/列表感知切块。
- 文档处理仍在请求内同步执行，下一阶段改为任务队列、批量 embedding 和可恢复状态机。
- 当前只有 dense 向量召回，后续增加 lexical 召回、RRF 融合和 reranker。
- ACL 当前覆盖角色维度，后续扩展部门、用户组和密级。
