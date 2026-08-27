# ResearchBase Phase 1 GO Package Static Review v1.0

## Verdict

```text
P0 OPEN: 0
P1 OPEN: 0
P2 OPEN: 3
GO: PR-00 ONLY
```

## Consistency checks

### PASS — Scope

The package preserves the frozen rule that Phase 1 GO authorizes PR-00 only, not all of Phase 1.

### PASS — PR-00 deliverables

The execution pack includes the TDG-1 bootstrap requirements:

- uv/Python environment;
- lockfile;
- PostgreSQL 18;
- SQLAlchemy + psycopg smoke;
- Alembic bootstrap;
- FastAPI/Typer smoke;
- local content-addressed ArtifactStore smoke;
- Ruff/Pyright/pytest;
- architecture skeleton;
- ADR-0001..0007.

### PASS — No business-domain implementation

The pack explicitly separates low-level `ArtifactStore` infrastructure from canonical scientific `Artifact`/`ArtifactVersion` business behavior and forbids Phase 1 domain implementation in PR-00.

### PASS — Agent Runtime boundary

Engineering Harness may assist development, but Phase 1 does not implement a ResearchBase Agent Runtime.

### PASS — Canonical schema boundary

`HarnessFingerprint` is development evidence / execution metadata, not a new top-level scientific canonical entity.

### PASS — PostgreSQL rule

Real PostgreSQL remains mandatory for integration acceptance. SQLite fallback is explicitly forbidden for the gate.

### PASS — External Harness precedence

ResearchBase architecture and phase rules override external Skills/Plugins.

## P2-01 — External Harness availability

Superpowers and Codex Security are optional for PR-00, so local installation/runtime differences cannot block the architectural bootstrap. This is intentional but means PR-00 review quality may vary by environment.

Mitigation: native verification/review requirements remain mandatory.

## P2-02 — plugin-eval is not fully pinned

`plugin-eval` is recorded with `revision: null` and therefore cannot be treated as a reproducible executable dependency.

Mitigation: it is not required for PR-00 and the lock explicitly forbids governed executable use until an exact reviewed revision is recorded.

## P2-03 — agent-skills is reference-only

`addyosmani/agent-skills` is deliberately not executable/pinned in PR-00.

Mitigation: when a specific skill is admitted later, pin exact commit/revision through a dedicated Harness change and regression review.

## Final decision

No P0/P1 inconsistency was found between the Phase 1 GO package and the frozen Phase 1/TDG-1/Harness architecture.

The package is suitable for handing to Codex for **PR-00 only**.
