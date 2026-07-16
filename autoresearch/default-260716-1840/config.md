# Autoresearch configuration

- Goal: enforce a shared request deadline and classify model failures for correct retry, circuit and alert behavior
- Iteration budget: 10
- Primary metric: downstream timeouts never exceed remaining request budget
- Safety metrics: local deadline exhaustion and invalid requests do not open provider circuits; provider timeout/rate-limit/5xx failures do; regression failures 0
- Observability metrics: error categories and reliability state available in JSON and Prometheus formats
- Keep rule: retain only iterations passing deterministic clock, failure classification, API, full backend, root, and PostgreSQL tests
- Scope: ContextVar deadline, error taxonomy, circuit accounting, outbound timeout clamping, Prometheus export

