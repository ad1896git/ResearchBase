# AGENTS.md — ResearchBase

## Purpose

This repository implements ResearchBase, a scientific provenance and traceability foundation.

The repository is architecture-controlled. Correctness means conformance to the frozen design, not maximizing code generation.

## 1. Read order

Before implementation, read the applicable authoritative documents in this order:

1. `docs/architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md`
2. `docs/architecture/02_Final_Architecture_Correction_Addendum_v1.0.md`
3. `docs/architecture/03_Global_Schema_and_Contract_Registry_v1.0.md`
4. `docs/architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md`
5. current phase specification
6. `docs/architecture/09_TDG1_Phase1_Technology_Decision_Gate_v1.0.md` for Phase 1
7. `docs/harness/09_Harness_Integration_Specification_v1.0.md`
8. target PR execution pack

Do not infer architecture from tickets alone.

## 2. Phase discipline

Only implement the explicitly authorized PR.

Never implement a later PR "because it is easy" or "because the current code needs it".

If the current target is PR-00, there must be no business-domain implementation.

## 3. Canonical scientific invariants

Never violate:

- deterministic canonical facts take precedence over authority/review;
- one canonical source of truth per fact;
- frozen formal provenance must resolve to deterministic frozen versions;
- immutable scientific history is corrected by new records/provenance, not ordinary mutation;
- Hypothesis != Claim;
- ExperimentSpec != Run;
- Review != Decision != Approval != Command != ExternalEffect;
- Human and Agent callers use the same Application boundary;
- Agent/Skill output is not scientific truth by itself;
- third-party agent frameworks do not own canonical scientific state.

## 4. Architecture complexity budget

Default answer to a proposed new top-level canonical schema is:

```text
DO NOT ADD SCHEMA
```

unless the concept cannot be represented clearly by existing Entity + Relation + Assessment + Snapshot + Event patterns and the change is approved through ADR/architecture review.

Do not use generic polymorphic JSON objects as the semantic core.

## 5. Layering

Required write path:

```text
Caller
→ Application Command/Service
→ Repository Port / UoW
→ Persistence Adapter
→ PostgreSQL
```

Domain must not depend on:

- SQLAlchemy Session;
- FastAPI;
- Typer;
- Codex;
- external Skills/Plugins.

Do not expose ORM entities as API/domain objects.

## 6. Database and transactions

Phase 1:

- PostgreSQL 18.x is the integration DB;
- DB I/O is synchronous;
- one Application command equals one database transaction unless an approved specification says otherwise;
- no scientific `ON DELETE CASCADE`;
- no primary-chain `target_type + target_id` soft references;
- integration/constraint/migration tests use real PostgreSQL, not SQLite.

## 7. Dependency rules

Canonical environment management:

```text
uv + pyproject.toml + uv.lock
```

Do not add:

- `requirements.txt` as a parallel canonical source;
- Poetry;
- Pipenv;
- Conda environment as canonical dependency definition.

New runtime dependencies require justification.

Do not introduce Redis, queues, microservices, vector DBs, agent frameworks, or other infrastructure unless the authorized phase/PR explicitly requires them.

## 8. Harness rules

ResearchBase architecture and safety rules override external Skills/Plugins.

External Harness:

- may guide planning, testing, debugging, review, and verification;
- must not write ResearchBase canonical persistence directly;
- must not silently change scope;
- must not self-modify governing Harness files to pass a task.

Production material Harness dependencies must be pinned when actually enabled.

Do not pretend a reference-only Skill library is an executable locked dependency.

## 9. Verification

Evidence precedes completion claims.

Before saying a task is complete, run the target PR's required checks and report exact results.

Never turn:

```text
not run
could not run
assumed
looks correct
```

into PASS.

## 10. Review

Findings:

```text
P0 BLOCKER
P1 MAJOR
P2 MINOR
P3 SUGGESTION
```

Do not merge/declare gate success with open P0 or P1.

Reviews should identify concrete target/location, evidence, violated rule, impact, and action.

Where practical, review should be performed from authoritative specs + diff + test evidence rather than inheriting the authoring agent's full working context.

## 11. Documentation and ADR

Do not let implementation silently become architecture.

Material deviations require ADR/Architecture Question before implementation.

Documentation and tests must be updated in the same PR when the contract changes.

## 12. PR-00 special rule

PR-00 is repository/bootstrap only.

Allowed:

- Python/uv bootstrap;
- `pyproject.toml`, `uv.lock`;
- source/test directory skeleton;
- PostgreSQL development/test plumbing;
- Alembic empty bootstrap;
- FastAPI smoke adapter;
- Typer smoke CLI;
- local content-addressed ArtifactStore port + smoke implementation;
- Ruff/Pyright/pytest configuration;
- CI;
- architecture skeleton tests;
- ADR-0001..ADR-0007;
- README development commands;
- Harness config files.

Forbidden in PR-00:

- ResearchQuestion/Hypothesis implementation;
- ExperimentSpec/Run implementation;
- Dataset/Artifact canonical domain implementation;
- Measurement/StatisticalResult/Claim implementation;
- governance business implementation;
- Phase 2+ functionality.

After PR-00 acceptance evidence is generated: STOP.
