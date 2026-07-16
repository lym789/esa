# Autoresearch configuration

- Goal: isolate external model failures with independent circuit breakers and concurrency bulkheads
- Iteration budget: 10
- Primary metric: repeated provider failures fast-fail after threshold and recover through one half-open probe
- Safety metrics: LLM, embedding and reranker failure domains remain isolated; fallback behavior unchanged; regression failures 0
- Reliability metrics: circuit-open rejections and bulkhead rejections observable per component
- Keep rule: retain only iterations passing deterministic fault injection, concurrency, full backend, root, and PostgreSQL tests
- Scope: circuit breaker, bulkhead, wrappers, runtime metrics, failure injection tests, documentation

