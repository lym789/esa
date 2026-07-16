# Day 22 企业级 RAG Phase 3

本阶段完成在线检索质量升级的核心链路：查询理解、双路召回、融合、重排和上下文选择。

## 查询规范化与多轮改写

- 使用 Unicode NFKC 统一全角/半角字符。
- 合并多余空白并保留原始问题。
- 对包含“这个、上述、刚才、该流程”等指代的追问补充最近用户问题。
- 短但主题明确的新问题不会错误继承上一话题。
- Trace 同时记录 `query`、`retrieval_query` 和 `query_rewritten`。

示例：

```text
上一轮：差旅报销需要哪些凭证？
本轮：这个需要审批吗？
检索：差旅报销需要哪些凭证？；追问：这个需要审批吗？
```

## Dense + Lexical 双路召回

### Dense

- 继续使用 pgvector 数据库侧 cosine Top-K。
- 按 embedding 模型隔离查询，不混用不同模型向量。
- 保留 similarity threshold。

### Lexical

- PostgreSQL 启用 `pg_trgm`。
- `document_chunks.content` 建立 GIN trigram 索引。
- 精确包含查询获得最高 lexical 分数。
- SQLite 测试使用 ASCII token 和中文 bigram 重叠率。
- 错误码、制度编号和产品名即使没有兼容 dense 向量也可以召回。

两条检索分支都在数据库条件中执行：

- 当前文档版本
- 发布状态
- 生效/失效时间
- 知识库范围
- 用户角色 ACL

## RRF 融合

Dense 和 Lexical 各自返回有序候选，再使用 Reciprocal Rank Fusion：

```text
score(chunk) += 1 / (rrf_k + rank)
```

同时被两条路径召回的 chunk 会自然得到更高融合分数。默认 `rrf_k=60`。

## 可插拔 Reranker

新增 `Reranker` 协议。默认实现使用确定性组合：

- dense score
- lexical score
- fusion score

后续可以接入 cross-encoder 或独立 rerank API，而不改变检索和 Chat 接口。外部 Reranker 报错时自动退回默认排序。

## 上下文装配

- 跨文档相同内容按内容指纹去重。
- 使用 MMR 在相关性和内容多样性之间平衡。
- 限制单份文档最多进入上下文的 chunk 数。
- 按 token 预算停止装配，避免固定 Top-K 超出模型窗口。
- 最终顺序和四类分数写入 Message metadata 与 Agent Trace。

当前结果字段：

```text
similarity
dense_score
lexical_score
fusion_score
rerank_score
```

## 配置

```text
RAG_CANDIDATE_K=30
RAG_RRF_K=60
RAG_LEXICAL_MIN_SCORE=0.05
RAG_MAX_CHUNKS_PER_DOCUMENT=3
RAG_CONTEXT_TOKEN_BUDGET=3000
RAG_MMR_LAMBDA=0.75
```

这些参数应通过真实黄金集调整，不应只依赖人工体验。

## 数据库迁移

```text
0004_hybrid_lexical_retrieval
```

迁移内容：

- 启用 `pg_trgm` extension。
- 创建 `ix_document_chunks_content_trgm` GIN 索引。

## 验证结果

- 后端测试：131 passed，1 skipped。
- 根目录前端 scaffold：53 passed。
- PostgreSQL 混合召回集成测试：1 passed。
- 集成测试覆盖 pgvector、pg_trgm、角色 ACL 和精确错误码召回。
- Docker Compose 配置检查通过。
- `git diff --check` 通过。

## 尚未完成

- 真实业务黄金集仍需从 5 条示例扩充到 100～200 条。
- 当前默认 Reranker 是确定性实现，尚未接入真实 cross-encoder。
- 邻接 chunk 和 parent chunk 扩展尚未接入在线上下文。
- 尚未基于真实集执行融合权重、阈值和 token 预算的系统调参。

这些工作应先补齐真实黄金集，再通过对照实验推进，避免无指标调参。
