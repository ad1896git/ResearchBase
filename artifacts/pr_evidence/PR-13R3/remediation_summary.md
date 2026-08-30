# PR-13R3 remediation summary

PR-13R3 closes the requested+missing ExperimentSpecVersion implementation exception by
deterministically initializing the contextual state flag before branch evaluation. The scientific
closure rules, DTOs, schema, and migrations are unchanged. Adversarial PostgreSQL tests cover
MISSING, NEVER_REQUESTED, repository-backed non-contextual validation, repeated determinism,
direct fallback call counts, and stage-bounded SQL.

