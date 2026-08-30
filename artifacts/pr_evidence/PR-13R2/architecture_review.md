# Architecture review

- One UoW/session per trace: preserved.
- Context: typed, request-local, transaction-local, in-memory only.
- SQL-producing calls inside contextual descendant loops: 0.
- Generic graph / persistent cache / global cache: none.
- ORM/Session leakage into DTOs: none.
- Schema/migration drift: none; Alembic `0014_claim_evidence (head)`.
- PR-14 or Phase 2+ implementation: none.
