# ResearchBase PR-00 Execution Pack v1.0

> Target: PR-00 — Repository Bootstrap
> Authorization: Phase 1 GO, PR-00 ONLY
> Stop boundary: completion of PR-00 evidence and review
> Explicit prohibition: NO BUSINESS DOMAIN IMPLEMENTATION

## 1. Objective

Create a minimal, reproducible, architecture-compliant repository skeleton that proves the Phase 1 technology baseline works before any business-domain code is written.

PR-00 is a **bootstrap gate**, not the first domain feature.

## 2. Required inputs

The implementer must have access to:

1. System Architecture v1.3 Harness Integrated
2. Final Architecture Correction Addendum v1.0
3. Global Schema and Contract Registry v1.0
4. Cross-Phase Contracts v1.1 Harness Integrated
5. Phase 1 Development Specification v1.2 Harness Integrated
6. TDG-1 v1.0
7. Harness Integration Specification v1.0
8. `AGENTS.md`
9. `harness.lock.yaml`
10. this PR-00 Execution Pack

If one of the authoritative architecture documents is missing, do not reconstruct it from memory.

## 3. Allowed deliverables

PR-00 may create/configure:

```text
pyproject.toml
uv.lock
README.md
.env.example
compose.yaml
Dockerfile
alembic.ini
migrations/
src/researchbase/
tests/
.github/workflows/ci.yml
docs/architecture/adr/
AGENTS.md
harness.lock.yaml
```

It may create minimal smoke-only modules needed to prove:

- package import;
- FastAPI adapter startup;
- Typer CLI startup;
- synchronous SQLAlchemy + psycopg connectivity;
- Alembic empty migration bootstrap;
- ArtifactStore port and content-addressed local smoke behavior.

## 4. Forbidden deliverables

Do NOT implement any Phase 1 business domain.

Specifically forbidden:

```text
ResearchQuestion domain behavior
Hypothesis domain behavior
ExperimentSpec domain behavior
Run domain behavior
Dataset canonical domain behavior
Artifact canonical scientific-domain behavior
MetricDefinition
Measurement
StatisticalResult
EvidenceRelation
Claim
AuditFinding / ImpactAssessment business behavior
Phase 2 literature workflow
Phase 3 Agent Runtime
STORM/EvoScientist integration
```

A low-level `ArtifactStore` infrastructure port/smoke implementation is allowed; canonical scientific `Artifact`/`ArtifactVersion` business logic is not.

## 5. Required technology profile

```text
Python              3.12.x
uv                  required
PostgreSQL          18.x
SQLAlchemy          2.0.x
psycopg             3.x
Alembic             1.x compatible
Pydantic            2.x
FastAPI             0.141.x
Typer               0.27.x
Ruff                configured
Pyright             configured
pytest              configured
DB I/O              synchronous
```

Use compatible ranges in `pyproject.toml`; commit the actual resolver output in `uv.lock`.

Do not copy example patch versions blindly if the resolver shows incompatibility. Stay inside TDG-1 compatibility windows.

## 6. PostgreSQL development/test decision

Implement ADR-0004 using the TDG-1 preferred profile unless a concrete local blocker exists:

```text
local Docker Compose PostgreSQL
+
CI PostgreSQL service container
```

Integration tests must exercise real PostgreSQL.

SQLite is not an acceptable substitute for the PR-00 PostgreSQL connectivity gate.

## 7. ArtifactStore bootstrap contract

Create the smallest useful `ArtifactStore` Port and local content-addressed implementation needed for smoke testing.

Required behavior:

```text
put(bytes) -> content identity / locator
open(identity) -> exact bytes
verify(identity) -> verifies stored bytes against identity
```

Minimum invariant:

- same bytes produce same content identity;
- different bytes must not overwrite content under an existing hash;
- mutable arbitrary path semantics must not become the Core contract.

Do not implement scientific Artifact/ArtifactVersion domain entities in PR-00.

## 8. Repository skeleton expectations

Create only enough package boundaries to preserve future architecture.

Recommended shape:

```text
src/researchbase/
├── foundation/
├── persistence/
├── application/
├── api/
└── cli/
```

Business-domain directories MAY exist as empty/placeholder package directories only if needed by architecture tests, but SHOULD be deferred to their owning PR to reduce accidental implementation.

No domain behavior belongs in PR-00.

## 9. ADR requirements

Create simplified ADRs:

```text
ADR-0001 Python 3.12 / uv
ADR-0002 PostgreSQL 18
ADR-0003 SQLAlchemy 2.0 + sync psycopg
ADR-0004 DEV_LOCAL / Docker Compose PostgreSQL
ADR-0005 Content-addressed ArtifactStore
ADR-0006 FastAPI + Typer adapters
ADR-0007 Ruff + Pyright
```

Each ADR should include:

- Status
- Context
- Decision
- Consequences
- Rejected alternatives
- Upstream authority (`TDG-1`)
- Scope: Phase 1

Do not reopen TDG-1 choices inside these ADRs.

## 10. Required smoke tests/checks

The final PR-00 gate is:

```text
[ ] Python 3.12 environment via uv
[ ] uv.lock committed
[ ] PostgreSQL 18 service starts
[ ] SQLAlchemy 2.0 + psycopg connection smoke
[ ] Alembic empty upgrade head pass
[ ] FastAPI smoke app
[ ] Typer smoke CLI
[ ] local ArtifactStore put/open/verify smoke
[ ] Ruff pass
[ ] Pyright pass
[ ] pytest pass
[ ] architecture skeleton pass
[ ] ADR-0001..0007 created
```

## 11. Architecture skeleton tests

At minimum, add checks that catch obvious bootstrap drift, for example:

- Domain package does not import FastAPI/Typer/SQLAlchemy Session;
- no agent framework dependency exists;
- no Redis/queue/vector DB dependency exists;
- no forbidden parallel dependency manifest exists;
- no business schema migration exists in PR-00.

Keep architecture tests simple and robust. Do not build an elaborate meta-framework.

## 12. CI minimum

CI should verify, in a reproducible order:

```text
checkout
→ Python 3.12
→ uv install/sync from lock
→ PostgreSQL 18 service health
→ Ruff
→ Pyright
→ pytest
→ alembic upgrade head
```

Avoid adding deployment/release automation in PR-00.

## 13. Required implementation procedure

### Step A — Inspect

Before changing files:

- inspect current repository tree;
- inspect existing config;
- inspect git status;
- identify whether repository is empty/partial;
- do not delete pre-existing user work.

### Step B — Plan

Write a short PR-00 implementation plan mapped to the acceptance checklist.

### Step C — Bootstrap

Implement only the minimum files required by the plan.

### Step D — Verify incrementally

Run checks as pieces are added; do not wait until the end to discover environment failures.

### Step E — Diff audit

Inspect the final diff specifically for accidental business-domain implementation and unapproved dependencies.

### Step F — Independent review

Review against:

- PR-00 scope;
- TDG-1;
- `AGENTS.md`;
- Harness policy.

P0/P1 must be resolved before gate success.

### Step G — Evidence

Generate:

```text
artifacts/pr_evidence/PR-00/
├── implementation_summary.md
├── changed_files.txt
├── commands_and_results.md
├── test_report.md
├── architecture_review.md
├── code_review.md
├── unresolved_findings.md
└── harness_fingerprint.json
```

## 14. Harness fingerprint for PR-00

Record only facts actually available.

Example:

```json
{
  "researchbase_git_commit": null,
  "agents_md_sha256": "...",
  "harness_lock_sha256": "...",
  "target_pr_pack_sha256": "...",
  "codex_runtime_version": "unknown",
  "model_identifier": "unknown",
  "external_harness_used": []
}
```

Never invent unavailable runtime/model identifiers.

## 15. Failure behavior

If Docker/PostgreSQL is unavailable:

- do not silently replace PostgreSQL with SQLite;
- complete non-DB bootstrap work if safe;
- report DB gate as BLOCKED;
- do not declare PR-00 accepted.

If a package inside the frozen compatibility window cannot resolve:

- capture resolver evidence;
- choose another compatible patch/minor within the TDG-1 window where permitted;
- update lock;
- report the exact resolution.

If a frozen major/minor baseline must change:

- stop;
- raise ADR/Technology Gate issue.

## 16. Completion report

Final response/evidence must contain:

```text
PR-00 STATUS: PASS | BLOCKED | FAIL

Acceptance checklist:
...
P0 findings:
...
P1 findings:
...
P2 findings:
...

Business-domain implementation detected: NO
PR-01 or later implementation detected: NO
Phase 2+ implementation detected: NO

STOP.
```

No PR-01 work is authorized by this pack.
