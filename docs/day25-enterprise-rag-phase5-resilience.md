# Day 25：企业级 RAG Phase 5——模型熔断与并发隔离

## 本阶段结果

LLM、Embedding 和可插拔 Reranker 已具备独立故障域。外部供应商持续失败时，系统会快速失败并使用既有安全降级，不再让每个请求都等待供应商超时或重试耗尽。

### 1. Circuit Breaker

每个组件按照“类型 + 供应商 + 模型”或 Reranker 类名建立独立熔断器：

- `closed`：正常放行调用；
- 连续失败达到阈值后进入 `open`；
- `open` 期间直接拒绝，不调用外部供应商；
- 恢复窗口到期进入 `half_open`；
- `half_open` 只允许一个探针调用；
- 探针成功后恢复 `closed`，失败则重新打开。

OpenAI SDK 内部重试仍然保留。熔断器统计的是一次完整客户端调用最终失败，因此不会因为单次可恢复网络抖动过早开路。

### 2. Bulkhead 并发舱壁

LLM、Embedding 和 Reranker 分别拥有独立并发配额：

- 组件达到并发上限后，只等待很短的可配置时间；
- 无法获得配额时快速拒绝；
- 舱壁拒绝不会计为供应商失败，也不会误触发 circuit breaker；
- 一个组件饱和不会占用另一个组件的配额。

这避免慢 LLM 请求耗尽所有工作线程，同时仍允许 Embedding 或本地检索继续工作。

### 3. 现有降级路径保持不变

- LLM 被熔断或舱壁拒绝：意图识别使用保守默认值，RAG 回答退回有引用的抽取式回答。
- Embedding 被熔断或舱壁拒绝：查询和索引流程沿用 `local-hash-v1` 降级。
- 外部 Reranker 被熔断或舱壁拒绝：使用确定性启发式重排。
- 所有降级仍受 ACL、引用校验和 Prompt Injection 防护约束。

### 4. 运行指标

管理员 `GET /api/search/metrics` 响应新增 `resilience`，按组件展示：

- 当前 circuit 状态；
- 连续失败数、打开次数和开路拒绝数；
- 实际调用、成功和失败次数；
- bulkhead 拒绝数；
- 当前及历史最大并发数。

这使“请求最终成功，但外部组件已降级”能够被监控和告警。

## 配置项

- `MODEL_CIRCUIT_FAILURE_THRESHOLD=5`
- `MODEL_CIRCUIT_RECOVERY_SECONDS=30`
- `MODEL_BULKHEAD_TIMEOUT_SECONDS=0.1`
- `LLM_MAX_CONCURRENCY=20`
- `EMBEDDING_MAX_CONCURRENCY=20`
- `RERANKER_MAX_CONCURRENCY=20`

生产值应根据供应商配额、应用 worker 数、平均耗时和请求流量压测确定。

## 验证结果

- 确定性故障注入覆盖：开路、快速拒绝、单探针半开、成功恢复、组件隔离。
- 并发测试覆盖：舱壁满载拒绝、配额释放、无错误开路。
- 集成测试覆盖：Reranker 达阈值后不再调用故障供应商，但每次检索仍有安全结果。
- 后端完整回归：159 passed，1 skipped。
- 根目录 scaffold 回归：53 passed。
- PostgreSQL + pgvector 集成：1 passed。
- Python 编译和 `git diff --check` 通过。

## 后续工作

- 导出 Prometheus/OpenTelemetry 指标并配置告警阈值。
- 增加调用级 deadline budget，使意图、检索、重排和生成共享总时限。
- 对 429、超时、5xx 和不可重试 4xx 使用不同失败分类。
- 接入分布式限流，协调多实例供应商配额。
- 建立故障演练和自动回滚门禁。
