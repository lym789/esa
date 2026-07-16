# Autoresearch configuration

- Goal: deliver Enterprise RAG Phase 0/1 foundations
- Iteration budget: 8
- Primary metric: backend RAG regression tests pass
- Quality metrics: Recall@K and nDCG@K evaluator correctness
- Safety metric: restricted documents are never returned to an unauthorized role
- Performance invariant: PostgreSQL retrieval must use database-side Top-K rather than loading all chunks
- Keep rule: retain an iteration only when targeted tests pass and no existing backend tests regress
- Scope: RAG/document/database backend only; preserve unrelated workspace changes

