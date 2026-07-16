# Autoresearch configuration

- Goal: implement Enterprise RAG Phase 5 runtime reliability and observability foundations
- Iteration budget: 12
- Primary metric: repeated authorized searches avoid redundant retrieval without any ACL cache leakage
- Safety metrics: cross-user/department cache leakage 0; stale-cache results after document mutation 0; regression failures 0
- Performance metrics: cache-hit retrieval avoids database search stages; stage latency and degradation counters observable
- Keep rule: retain only iterations passing cache isolation, invalidation, backend, root, and PostgreSQL tests
- Scope: bounded TTL caches, invalidation, search diagnostics, runtime metrics, reranker degradation visibility, capacity benchmark

