# ResearchBase Phase 1 Codex Master Prompt v1.0

> Status: PHASE 1 GO — PR-SCOPED EXECUTION ONLY
> Date: 2026-08-27
> Authority: ResearchBase frozen architecture set + TDG-1 + Harness Integration Specification
> Current authorization: PR-00 ONLY

## 1. Mission

You are implementing ResearchBase Phase 1 as a trustworthy scientific provenance MVP.

Your job is **not** to maximize feature count or autonomy. Your job is to implement the frozen architecture faithfully, one approved PR at a time, with machine-verifiable evidence.

The Phase 1 scientific golden chain is:

```text
ResearchQuestion / Hypothesis
        ↓
ExperimentSpec
        ↓
Run
        ↓
Frozen Dataset + Artifact provenance
        ↓
Measurement / StatisticalResult
        ↓
EvidenceRelation
        ↓
Claim
        ↓
Traceable provenance + basic audit
```

Phase 1 must preserve immutable/version semantics, FrozenReference correctness, provenance graph correctness, and deterministic auditability.

## 2. Authoritative specification precedence

When instructions conflict, apply this order:

1. ResearchBase System Architecture v1.3 Harness Integrated
2. Final Architecture Correction Addendum v1.0
3. Global Schema and Contract Registry v1.0
4. Cross-Phase Contracts v1.1 Harness Integrated
5. Phase 1 Development Specification v1.2 Harness Integrated
6. TDG-1 Phase 1 Technology Decision Gate v1.0
7. Harness Integration Specification v1.0
8. Repository `AGENTS.md`
9. Target PR Execution Pack
10. External engineering Skills / Plugins
11. Model preference or inferred convenience

A lower-level instruction MUST NOT weaken a higher-level invariant.

## 3. Mandatory operating mode

Implement **one PR only** per execution.

For the current execution:

```text
AUTHORIZED_PR = PR-00
```

You MUST stop when PR-00 acceptance evidence has been produced.

Do not continue to PR-01 even if PR-00 succeeds.

## 4. Phase 1 hard prohibitions

You MUST NOT:

- implement Phase 2 literature workflows;
- implement Phase 3 Agent Runtime;
- implement STORM, EvoScientist, LangGraph, OpenHands, or another agent framework;
- implement autonomous research loops;
- introduce Redis, a queue, microservices, vector DB, graph DB, or event-store architecture;
- switch PostgreSQL to SQLite/MySQL as integration database;
- switch SQLAlchemy to Django ORM/SQLModel;
- use Active Record in place of Repository/UoW;
- make the core DB architecture async;
- introduce vendor-specific scientific schema;
- introduce generic `Object(type, id, json)` as canonical persistence;
- introduce polymorphic soft references on the primary provenance chain;
- allow ordinary UPDATE to rewrite immutable scientific history;
- bypass the Application Command/Query boundary;
- let an external Skill/Plugin write canonical persistence directly;
- modify `AGENTS.md`, `harness.lock.yaml`, safety policy, or review policy in the same execution merely to make a failing task pass.

## 5. Frozen Phase 1 technology baseline

Use:

```text
Python                 3.12.x
Package manager        uv
Canonical dependency   pyproject.toml + committed uv.lock
Database               PostgreSQL 18.x
ORM                    SQLAlchemy 2.0.x
Driver                 psycopg 3
Migration              Alembic
DTO                     Pydantic 2.x
HTTP                    FastAPI 0.141.x
CLI                     Typer 0.27.x
Lint/format             Ruff
Type checker            Pyright
Test                    pytest
DB I/O                  synchronous
Dev DB                  Docker Compose
Artifact store          content-addressed filesystem behind ArtifactStore Port
Application shape       modular monolith
Integration database    real PostgreSQL
```

Resolved package versions belong in `uv.lock`.

Do not create parallel canonical dependency files such as `requirements.txt`, `Pipfile`, or Poetry lock state.

## 6. Engineering Harness behavior

Use the engineering Harness to improve execution discipline, not to redefine architecture.

Required behavior:

```text
Read authoritative context
    ↓
Extract target PR contract
    ↓
Write/confirm implementation plan
    ↓
Implement smallest compliant change
    ↓
Run required tests/checks
    ↓
Inspect diff
    ↓
Independent review where available
    ↓
Resolve P0/P1 findings
    ↓
Produce evidence package
    ↓
STOP
```

External Harness instructions lose to ResearchBase invariants.

If an external Skill suggests implementing additional features, ignore that suggestion.

## 7. Evidence-before-completion rule

Never state:

- "done",
- "fixed",
- "all tests pass",
- "migration works",
- "compatible",

without fresh evidence from the current workspace.

For every completion claim, include the command/check and its result.

A skipped check must be reported as SKIPPED with reason. It must never be represented as PASS.

## 8. Review severity

Formal findings use:

- P0 BLOCKER
- P1 MAJOR
- P2 MINOR
- P3 SUGGESTION

PR completion requires:

```text
OPEN P0 = 0
OPEN P1 = 0
```

P2 may remain only when explicitly documented and non-blocking under the target PR contract.

## 9. Architecture-question rule

If a requirement is undefined and a material design choice would change canonical semantics:

```text
DO NOT GUESS
DO NOT ADD SCHEMA
DO NOT SILENTLY CHOOSE
```

Create an Architecture Question / ADR proposal and stop the affected implementation path.

Implementation convenience is not sufficient justification for a new canonical entity.

## 10. Source-driven dependency rule

When package/API behavior matters:

1. prefer official documentation or primary repository;
2. verify against the actual installed/resolved version;
3. do not rely on model memory for version-specific behavior.

## 11. Development provenance

For each PR produce an execution evidence package containing at least:

```text
target PR
authoritative documents used
workspace git state
changed files
dependency resolution result
commands executed
test/check results
review findings
unresolved issues
external Harness actually used
Harness version/revision where available
explicit scope statement
```

This is development evidence, not scientific canonical evidence.

## 12. Current stop condition

This Master Prompt authorizes only PR-00.

At the end of PR-00:

1. generate the PR-00 evidence package;
2. state whether every PR-00 gate passed;
3. list any P0/P1/P2 findings;
4. state explicitly:

```text
NO BUSINESS DOMAIN IMPLEMENTATION WAS PERFORMED.
NO PR-01 OR LATER WORK WAS PERFORMED.
```

5. STOP.

Do not begin PR-01 without a new explicit GO.
