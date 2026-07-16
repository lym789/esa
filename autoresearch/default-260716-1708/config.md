# Autoresearch configuration

- Goal: complete the next Enterprise RAG Phase 2 foundation slice
- Iteration budget: 10
- Primary metric: backend and root scaffold regression tests pass
- Quality invariants: preserve semantic boundaries, batch embedding calls, keep the last published document version on reindex failure
- Safety invariant: version changes must not bypass publication, expiry, knowledge-base, or role ACL filters
- Keep rule: retain only changes that pass targeted tests and the full backend suite
- Scope: update obsolete scaffold assertions, then RAG ingestion/versioning backend

