# Autoresearch configuration

- Goal: implement Enterprise RAG Phase 4 trust and security controls
- Iteration budget: 10
- Primary metric: unsupported claims and unauthorized/suspicious context never reach the final answer
- Safety metrics: prompt-injection block rate 100% on fixtures; trace secrets and PII redacted; department ACL violations 0
- Keep rule: retain only iterations passing security fixtures, full backend, root, and PostgreSQL integration tests
- Scope: claim citations, evidence checks, prompt injection, trace redaction, department ACL and classification

