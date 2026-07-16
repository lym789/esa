# Autoresearch configuration

- Goal: implement Enterprise RAG Phase 3 hybrid retrieval
- Iteration budget: 10
- Primary metric: Recall@10 and nDCG@10 must not regress on deterministic fixtures
- Safety invariant: every retrieval branch applies current-version, publication, expiry, knowledge-base, and ACL filters
- Performance invariant: PostgreSQL dense and lexical branches each use database-side bounded candidate queries
- Keep rule: retain only iterations passing targeted, full backend, root, and PostgreSQL integration tests
- Scope: query understanding, hybrid retrieval, fusion, reranking, and context selection

