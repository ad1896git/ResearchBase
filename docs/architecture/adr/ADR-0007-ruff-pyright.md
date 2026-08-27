# ADR-0007: Ruff and Pyright

- Status: Accepted
- Context: Bootstrap code needs consistent linting, formatting, and static type checks.
- Decision: Use Ruff for format/lint and Pyright for type checking in local and CI gates.
- Consequences: Checks run from the locked uv environment.
- Rejected alternatives: A parallel formatter/linter stack and untyped acceptance criteria.
- Upstream authority: TDG-1
- Scope: Phase 1

