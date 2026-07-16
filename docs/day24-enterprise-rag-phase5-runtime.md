# Day 24：企业级 RAG Phase 5——缓存、运行指标与容量基准

## 本阶段结果

Phase 5 第一批运行时基础已经落地：在不降低 ACL 安全边界的前提下减少重复检索，并让延迟、缓存命中和降级路径可直接观测。

### 1. 两级有界 TTL 缓存

新增两类进程内 LRU + TTL 缓存：

- 查询向量缓存：键包含规范化查询和 embedding 模型，可安全跨用户复用。
- 检索结果缓存：键包含数据库实例、知识 revision、用户 ID、角色、部门、知识库、查询、阈值和全部排序参数。

检索结果采用防御性深拷贝，调用方修改结果不会污染缓存；缓存支持最大条目数、TTL、LRU 淘汰、命中/未命中/淘汰/失效计数，并使用线程锁保护并发访问。

检索缓存故意包含用户 ID。它牺牲了一部分同权限用户之间的命中率，但为未来可能加入的用户级 ACL 保留了安全边界。

### 2. 跨进程安全失效

新增持久化 `rag_index_state.revision`：

- 文档新版本发布；
- 文档治理或 ACL 更新；
- 文档删除；

都会在同一数据库事务内递增 revision，并清空本进程检索缓存。每次检索缓存键都会读取当前 revision，因此其他应用实例即使尚未收到本地失效通知，也不会命中旧 revision 的结果。

当前缓存值保存在各应用进程内。后续可接入 Redis 共享缓存以提升多实例命中率，但安全失效不依赖 Redis pub/sub。

### 3. 分阶段诊断与运行指标

每次检索会生成：

- 是否命中检索缓存；
- Dense / Lexical 候选数量；
- 最终上下文数量；
- 被 Prompt Injection 规则过滤的 chunk 数；
- 降级组件列表；
- Dense、Lexical、排序装配和总耗时。

搜索 API 返回本次请求诊断；Chat 的消息 metadata 和 Agent Trace 同步保存诊断。管理员可通过 `GET /api/search/metrics` 查看：

- 总检索量、缓存命中率和已选择 chunk 数；
- 注入过滤和组件降级计数；
- 各阶段 P50/P95/P99/最大耗时；
- 两级缓存当前统计。

指标样本使用有界内存窗口，避免长期运行无限增长。普通用户不能访问聚合指标端点。

### 4. Reranker 降级可见性

可插拔 reranker 失败时继续使用确定性启发式重排，不中断问答；同时在本次诊断和聚合指标中记录 `degraded_reranker`，使“请求成功但质量组件发生降级”不再是静默事件。

### 5. 可重复容量基准

新增本地容量基准命令：

```bash
cd backend
python -m app.evaluation.rag_capacity_benchmark \
  --documents 500 \
  --queries 100 \
  --unique-queries 10
```

本轮环境中的首个样例结果：

| 文档 | 查询 | 热点问题 | 命中率 | 冷查询 P95 | 热查询 P95 | 吞吐量 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 200 | 40 | 8 | 80% | 22.311 ms | 0.137 ms | 313.42 QPS |

该结果来自单进程内存 SQLite 合成数据，只用于改动前后相对比较，不能替代 PostgreSQL 生产容量测试。

## 配置项

- `RAG_CACHE_ENABLED=true`
- `RAG_CACHE_TTL_SECONDS=60`
- `RAG_CACHE_MAX_ENTRIES=512`
- `RAG_METRICS_MAX_SAMPLES=1000`

## 数据库变更

幂等迁移 `0006_rag_cache_revision` 创建 `rag_index_state` 并初始化 revision。迁移已应用到本地 PostgreSQL 验证库。

## 验证结果

- Phase 5 定向测试：缓存隔离、revision 失效、TTL/LRU、防御性复制、并发访问、指标权限、reranker 降级和容量基准均通过。
- 后端完整回归：153 passed，1 skipped。
- 根目录 scaffold 回归：53 passed。
- PostgreSQL + pgvector 集成：1 passed。

## 后续工作

- Redis 共享缓存与实例级缓存命中分析。
- embedding、reranker、LLM 各自的熔断器、限流和超时预算。
- Prometheus/OpenTelemetry 导出，不只保存在进程内指标窗口。
- PostgreSQL 百万级 chunk、并发权限分布和 HNSW 参数压测。
- 灰度、A/B、shadow traffic、线上反馈与自动回滚门禁。
