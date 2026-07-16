# Day 26：企业级 RAG Phase 5——统一 Deadline、错误分类与指标导出

## 本阶段结果

在线请求现在拥有统一的总时间预算。检索、LLM 和 Embedding 不再各自完整使用一份超时，而是共享请求剩余时间；模型异常也会按照根因分类，避免把本地预算耗尽或客户端无效请求错误计入供应商熔断。

### 1. 统一请求 Deadline

API 中间件为每个请求建立 ContextVar Deadline：

- 默认总预算 30 秒，可通过 `REQUEST_DEADLINE_SECONDS` 调整；
- Deadline 上下文可传递到同步服务与外部客户端；
- 嵌套阶段只能缩短预算，不能延长上层总时限；
- Dense、Lexical、Rerank/Context 阶段开始前检查剩余时间；
- LLM 和 Embedding 外呼 timeout 取“客户端默认超时”和“请求剩余预算”的较小值；
- 预算耗尽返回 HTTP 504；
- 正常响应包含 `X-Request-Deadline-Ms`，便于网关与调用方核对配置。

该机制是协作式 Deadline：外部网络调用能够使用缩短后的 timeout，内部阶段在边界主动检查。Python 同步代码无法被安全强制终止，因此 CPU 密集阶段仍应保持细粒度检查或迁移到可取消任务。

### 2. 模型错误分类

新增统一分类：

- `deadline_exceeded`；
- `timeout`；
- `rate_limit`；
- `authentication`；
- `invalid_request`；
- `provider_5xx`；
- `network`；
- `invalid_response`；
- `unknown`。

每类错误同时描述是否可重试、是否应推动 Circuit Breaker：

- 超时、429、网络、5xx、无效模型响应会计入供应商连续失败；
- 本地 Deadline、401/403 和客户端无效请求不会误开供应商熔断；
- 分类器沿 `__cause__ / __context__` 追溯包装异常，保留 OpenAI 客户端包装前的 HTTP 根因。

当前重试仍由供应商 SDK 执行；分类中的 `retryable` 为后续统一重试策略和告警提供依据。

### 3. Prometheus 指标导出

管理员可访问：

```text
GET /api/search/metrics/prometheus
```

响应采用 Prometheus text exposition format，包含：

- RAG 请求和降级累计计数；
- 检索缓存命中率；
- 各阶段 P50/P95/P99；
- 查询向量与检索缓存状态；
- 组件 Circuit 状态；
- 调用、失败、开路拒绝与 Bulkhead 拒绝；
- 按错误类别统计的组件错误数。

JSON 指标接口 `GET /api/search/metrics` 继续保留。两个端点均仅限管理员。

OpenTelemetry SDK 尚未直接引入：当前项目没有确定 Collector、采样规则和导出协议。先提供无额外依赖的 Prometheus 格式，后续确认观测基础设施后再接 OTLP，避免引入未使用依赖。

## 配置项

- `REQUEST_DEADLINE_SECONDS=30`
- 原有 `LLM_TIMEOUT_SECONDS` 仍作为单次模型调用上限，但不能超过请求剩余预算。

## 验证结果

- Deadline 确定性时钟测试覆盖：剩余时间、嵌套不可延长、预算耗尽和上下文恢复。
- API 测试覆盖：正常 Deadline Header 与耗尽后的 HTTP 504。
- 外呼测试覆盖：LLM timeout 被请求剩余预算夹紧。
- 错误分类覆盖：Deadline、timeout、429、401、400、503、network、invalid response 和包装异常根因。
- 熔断测试覆盖：无效请求可观测但不打开 Circuit。
- Prometheus 测试覆盖：指标格式、组件状态和管理员权限。
- 后端完整回归：167 passed，1 skipped。
- 根目录 scaffold 回归：53 passed。
- PostgreSQL + pgvector 集成：1 passed。

## 后续工作

- OTLP/OpenTelemetry tracing、跨服务 trace ID 和采样策略。
- 基于错误分类的统一退避策略，避免 SDK 与应用层重复重试。
- Redis/网关分布式限流与供应商配额协调。
- 为异步 worker 增加任务 Deadline、取消和死信原因分类。
- 按知识库、部门、模型统计 Token 与成本。
