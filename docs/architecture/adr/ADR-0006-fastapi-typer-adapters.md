# ADR-0006: FastAPI and Typer adapters

- Status: Accepted
- Context: PR-00 must prove the HTTP and CLI adapter entry points without implementing business behavior.
- Decision: Use FastAPI 0.141.x and Typer 0.27.x as thin smoke adapters.
- Consequences: Adapters remain outside the future domain and application core.
- Rejected alternatives: Framework-owned domain logic and direct adapter-to-persistence writes.
- Upstream authority: TDG-1
- Scope: Phase 1

