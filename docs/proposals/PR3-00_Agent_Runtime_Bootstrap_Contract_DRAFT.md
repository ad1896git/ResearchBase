# PR3-00 Agent Runtime Bootstrap Contract — DRAFT

> **Revision 2026-10-20:** Rebased entry on Phase 2 director GO and head 0075; corrected Application/UoW references, first-SHARE writes, snapshot reads and forward-only migrations; retained empty bootstrap and owner TDG-3 gates. This aligns the parked draft with actual exit evidence; implementation remains unauthorized. Director review: cited the committed Phase 2 acceptance record and final verification counts.

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

**Scope:** documentation only. This proposal is neither a Phase 3 GO, an ADR,
a frozen execution pack nor authorization to add code, migrations or dependencies.
Phase 2 director GO is recorded in the [Phase 2 acceptance record](../phase2/phase2_acceptance_2026-10-20.md)
(2026-10-20) with explicit deferrals. Separate
owner authorization is required after contract approval and TDG-3; Phase 3
implementation remains unauthorized.

## Start here

PR3-00 prepares empty runtime packages and migration plumbing with tests that
keep agents behind the existing Application boundary. It creates **no product
runtime, task tables, worker, scientific agent or scientific object**. PR3-01
owns task/step persistence; PR3-02 owns agent execution/promotion provenance;
PR3-03/04 own tool policy and budget/checkpoints. Do not pull those into bootstrap.

Read §1 for authority, §2 for scope, §4 for proposed decisions and §5 for the
implementation guide. The guide describes future authorized work, not work
performed by this documentation task. Tests in §6 are future acceptance obligations.

The [Phase 2 exit report](../phase2/phase2_exit_report.md) records validate_exit
PASS (16 PASS + 3 DEFERRED); director GO is recorded in the
[Phase 2 acceptance record](../phase2/phase2_acceptance_2026-10-20.md) on 2026-10-20 after the independent review
and R1–R3 corrections. Its final baseline is `286cd9a`: **12,524 passed,
66 skipped, 0 failed** (historical evidence, not checks rerun for this draft).
B20 screening and B23 novelty review/revision first slices are delivered, alongside
prepared-package freeze, manuscript revision and reconsideration. The
[roadmap carry-over inventory](PHASE3_Roadmap_DRAFT.md#phase-2-completion-backlog)
maps B28, AQ-S3-08, Linux host evidence, B20/B23 exclusions and R4–R7 to Phase 3
consequences. None authorizes Phase 3 implementation.

## 1. Authoritative basis and entry gate

Read these in repository AGENTS.md order; proposals never override them.

| Source | Binding requirement |
| --- | --- |
| [AGENTS.md](../../AGENTS.md) | Named PR only; one Application boundary; no direct agent DB writes; evidence before completion. |
| [System Architecture 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 55–57, 82–90, 97–106, Appendix H | One scientific owner; frameworks are replaceable; candidate promotion; harness is outside scientific truth. |
| [Correction Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A1, A4, A10–A14, A18–A22 | Concrete canonical FKs; immutable promotion record later; TDG-3 before implementation; fresh post-lock authorization where applicable. |
| [Global Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), §§4, 6–12 | Task is workflow, execution is separate from Run, fingerprint/memory reuse values/artifacts. |
| [Cross-Phase Contracts 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§12–24, 33, 46, 50, 52 | Additive migrations; retain history; no vendor-owned canonical state; Phase 2 STOP/review precedes Phase 3. |
| [Phase 3 Specification 06](../architecture/06_Phase3_Development_Specification_v1.1_Harness_Integrated.md), §§69–71, 77, 79, 81, final Harness Runtime Integration Addendum | PR3-00 = modules, migrations, architecture tests; phase-wide runtime features are apportioned across later PRs. |
| [TDG-2 11](../architecture/11_TDG2_Phase2_Technology_Decision_Gate_v1.0.md) | Accepted literature roles; activation still needs intake; B28 remains deferred. TDG-3 remains an owner decision. |
| [Harness Specification](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 5, 13–19, 21, 23–29 | Pin actually enabled material; HC-0 documentation; no same-execution harness weakening; fingerprint is a manifest/value. |

[Phase 3 roadmap](PHASE3_Roadmap_DRAFT.md) is planning context only. Its empty
bootstrap allocation agrees with this proposed scope; its technology suggestions
are not TDG-3 decisions. No separate PR3-00 execution pack exists in this checkout.
This contract must be approved and converted into a bounded pack before coding.

Before implementation: record the accepted Phase 2 baseline revision,
exit report and contract revisions; resolve any new P0/P1; record Phase 3 owner GO and TDG-3
ADR decisions for runtime framework, queue/worker, sandbox, compute and coding
provider. An ADR can defer activation to its owning PR but cannot leave the
phase's technology gate falsely marked complete. No required Phase 2 behavior
moves into PR3-00. Optional venue submission/full authority/IRB/resource extensions
are not invented as entry requirements.

Inspected baseline: one migration lineage ending at
`0075_m1_reconsideration`; see [0075](../../migrations/versions/0075_m1_reconsideration.py).
Any later authorized bootstrap revision is **new in PR3-00**, parented to the
then-accepted head, never an assumed 0043 or reused Phase 2 revision.

Existing implementation patterns are
[Application ports / UnitOfWork](../../src/researchbase/application/ports.py),
[DecisionService](../../src/researchbase/application/decision.py),
[SqlAlchemyUnitOfWork](../../src/researchbase/persistence/uow.py), and
[Decision repository](../../src/researchbase/persistence/decision_repository.py).
Services take a UoW factory, use typed commands/readbacks and repositories inside
one UoW, commit once on success and roll back failures; persistence owns SQL and
normalizes database errors. Bootstrap adds no command or repository method.

## 2. Authorized scope proposed for owner approval

| Include only in a later authorized PR3-00 | Exclude / owning PR |
| --- | --- |
| Importable empty package namespaces for runtime domain/application/ports/services, scientific strategies, capabilities and replaceable adapters | Task/step model, graph, commands and queries: PR3-01. |
| One empty forward Alembic revision attached to the then-accepted Phase 2 head | AgentVersion, availability, execution, promotion and fingerprint binding: PR3-02. |
| Architecture tests covering nested/relative imports and forbidden framework/DB access | Gateway/routing/production policy: PR3-03; budgets/checkpoints: PR3-04. |
| Development commands, evidence inventory and scope assertions | Context/memory, sandbox, compute, coding, scientific agents, search, background recovery: PR3-05..19. |
| Explicit separation of product runtime and development harness | Evaluation/security/E2E/hardening: PR3-20..23; self-evolution: Phase 4. |

No new runtime dependencies, infrastructure, top-level canonical schema, API
route or CLI business command. No modifications to governing AGENTS.md, production
Skills, routing/capability policy or harness lock to make tests pass. Reference-only
libraries remain reference-only. No placeholder scientific success or synthetic
AgentExecution is generated by an import/smoke test.

## 3. Boundary and invariants

```text
Human or Agent caller
→ Application Command/Query
→ Repository Port / UoW
→ Persistence Adapter
→ PostgreSQL 18.x
```

The future runtime is a caller of Application services. It receives typed DTOs,
never Sessions, repositories, ORM entities or database credentials. Application
orchestration may use ports; persistence implements ports. Domain imports only
pure foundation/types and approved domain interfaces, never SQLAlchemy, FastAPI,
Typer, provider SDKs, Codex/OpenHands, external Skills or frameworks. Foundation
must not import agent_runtime. Test recursive packages and relative/dynamic
imports, not only an empty top-level `__init__.py`.

ResearchBase owns task state in PostgreSQL once PR3-01 is separately accepted.
LangGraph/EvoScientist/vendor checkpoints are operational artifacts, never the
sole task state or scientific state. Agent output remains a candidate until owning
Application validation/promotion. Agent confidence, review and approval cannot
establish a scientific fact. Human and Agent use the same commands and authority
checks; role/Skill/autonomy is not permission. No agent self-approval.

Do not add a canonical Skill, HarnessFingerprint, WorkingMemory, WorkflowRun or
universal JSON reference table. Fingerprint binding and immutable
AgentPromotionRecord with concrete output FKs belong to later approved contracts;
promotion and scientific create/revise must eventually share one transaction.
PR3-00 must not claim those guarantees are operational.

## Glossary

| Term | Plain meaning |
| --- | --- |
| Bootstrap | Empty package/migration plumbing and boundary checks. |
| Canonical / candidate | Owning-domain accepted state / proposed output awaiting validation and explicit promotion. |
| ResearchTask / Run | Workflow identity / formal scientific execution; permanently distinct. |
| Application / port / UoW | Common use-case boundary / typed dependency interface / one-command transaction owner. |
| TDG-3 / ADR / GO | Phase 3 technology gate / architecture decision record / explicit owner authorization to start. |
| Fingerprint | Immutable effective harness manifest/value, later bound to execution provenance. |
| FK / RESTRICT / DAG | Foreign key / deny deletion of referenced history / dependency graph without cycles. |
| HC-0 | Documentation-only harness change, no executable behavior change. |
| P0 / P1 / P2 / P3 | BLOCKER / MAJOR / MINOR / SUGGESTION review severity. |

## 4. Proposed decisions for the owner

These are proposed choices awaiting owner approval, not accepted architecture.

| Decision | Choice and reason |
| --- | --- |
| Meaning of bootstrap migrations | Exactly one empty additive revision; no task or policy tables. Makes the boundary independently reviewable. |
| Runtime dependency | None. Native namespace skeleton; no framework selected or installed by this PR. TDG-3 owns selections. |
| Module layout | Follow 06 §69 with repository-standard shared persistence and transport adapters. Empty markers are sufficient. |
| Scientific schema | DO NOT ADD SCHEMA. This PR has no domain business implementation. |
| Migration numbering | Resolve `<phase3_bootstrap_revision>` and `<accepted_phase2_head>` in the authorized pack; current baseline is 0075; assign the new ID only in the authorized pack. |
| Future task staging | Review the [PR3-01 proposal](PR3-01_ResearchTask_Step_Graph_Contract_DRAFT.md) before dependent PRs; missing policy/execution/worker contracts keep execution disabled. |
| Gate evidence | Empty schema inventory delta plus real PostgreSQL clean/upgrade and forward-only refusal tests; no vacuous claim that future runtime features pass. |

Blockers to implementation: Phase 3 GO/TDG-3, owner contract
approval, exact migration parent/revision, and a reviewed execution pack. No
technology selection or architecture deviation is approved by this draft.

## 5. Implementation guide — future work only

### 5.1 File paths and build steps

The runtime, strategies and capabilities namespaces below are new and follow
06 §69; their `__init__.py` markers are new too. The adapters parent exists; its
coding/compute/runtime children are new. Phase3 docs/test directories and the
migration are new; README, ADR directory, migration directory, PostgreSQL helper
and import-boundary test already exist. Future paths are plain text, not links.

1. Freeze the scope/entry evidence in `docs/phase3/PR3-00-contract-freeze.md` and
   record selected TDG-3 ADRs under `docs/architecture/adr/`. Do not edit authoritative specs
   implicitly; any actual deviation first returns to architecture review.
2. Add empty `__init__.py` markers in `src/researchbase/agent_runtime/` and its
   `domain/`, `application/`, `ports/`, `services/`; `src/researchbase/strategies/scientific/`;
   `src/researchbase/capabilities/{coding,compute,sandbox,analysis,model}/`;
   `src/researchbase/adapters/{coding,compute,runtime}/`. Create missing parent markers; reuse existing parent packages. Do not add placeholder ResearchTask or executable Gateway.
3. Add `migrations/versions/<phase3_bootstrap_revision>_agent_runtime_bootstrap.py`
   with the exact then-accepted Phase 2 `down_revision`. No metadata registration
   that creates future tables as an import side effect.
4. Add `tests/architecture/test_pr3_00_boundaries.py` and
   `tests/integration/phase3/test_pr3_00_bootstrap.py`; extend the accepted migration
   allowlist in `tests/architecture/test_import_boundaries.py` by precisely the
   approved empty revision, retaining every earlier entry. Add malicious nested
   scanner fixtures proving the test rejects forbidden imports.
5. Update `README.md` with scope, commands and STOP rule; put exact test results,
   accepted parent/head, schema inventory and preserved history evidence in
   `docs/phase3/PR3-00-evidence.md`. Stop; PR3-01 needs its own authorization.

### 5.2 DDL sketch / migration behavior

```python
# Conceptual Alembic migration; placeholders require pack approval.
revision = "<phase3_bootstrap_revision>"
down_revision = "<accepted_phase2_head>"
branch_labels = None
depends_on = None

def upgrade() -> None:
    pass  # no CREATE/ALTER/DROP of business schema

def downgrade() -> None:
    raise RuntimeError("forward-only migration; use a reviewed forward repair")
```

No SQL DDL is authorized. No scientific `ON DELETE CASCADE` is permitted in any
later approved migration. Catalog table/column/FK/check/index/trigger inventory
must be identical before and after, excluding the Alembic revision value. Do not
stamp over a missing parent. Clean apply = the accepted full lineage plus the
empty revision. Migrations are forward-only, including this empty revision: downgrade refuses
without moving the revision pointer. Recovery uses a separately reviewed forward
repair; never edit accepted revisions or rewind scientific history.

### 5.3 Transaction and lock boundary

Product commands: **none** in PR3-00. The migrator runs alone through the existing
Alembic runner: exclusive deployment migration ownership → inspect accepted head
→ apply empty revision → verify head/catalog → release ownership. Do not invent
a second migrator, queue or runtime advisory lock. Disposable PostgreSQL helpers
are in `tests/disposable_postgres.py`; no retained database is migrated for tests.

Later commands must follow the actual Phase 2 pattern: select READ COMMITTED
before SQL, then issue `LOCK TABLE ... IN SHARE MODE` as the **first application
SQL statement**, before advisory locks, row locks, reads or validation. Configure
bounded first-lock waits before connection checkout without a preceding SET SQL;
transaction-local timeouts can follow the first SHARE statement. After all waits,
reread durable authority and evaluate credentials/expiry at fresh DB time before
writes. One Application command = one synchronous UoW transaction; no external I/O
under locks. See PR3-01 §6 for its proposed exact inventory.

Reads use `UnitOfWork.begin_formal_read()` / `SqlAlchemyUnitOfWork.begin_formal_read()`
before any SQL: one REPEATABLE READ READ ONLY snapshot, autoflush disabled, shared
by nested authorization and provenance verification. No table, advisory or row
locks (`FOR SHARE`/`FOR UPDATE`), writes, or independent nested snapshots.
Bootstrap must not claim later runtime guarantees are already operational.

### 5.4 Error-code mappings

PR3-00 adds no product errors or mappings. Existing values below are copied from
[HTTP errors](../../src/researchbase/api/errors.py) and
[CLI errors](../../src/researchbase/cli/errors.py); preserve them if smoke checks
exercise the existing adapters. Migration/bootstrap tool failures exit nonzero
with sanitized evidence; they are not invented Application ErrorCodes.

| Existing code | HTTP | CLI exit | Meaning |
| --- | --- | --- | --- |
| VALIDATION_ERROR | 422 | 2 | Malformed existing transport input. |
| NOT_FOUND | 404 | 3 | Authorized exact-ID query misses. |
| AUTHENTICATION_REQUIRED | 401 | 3 | No verified principal. |
| FORBIDDEN | 403 | 3 | No current entitlement. |
| CONCURRENT_MODIFICATION | 409 | 4 | Existing concurrency failure. |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Existing strong-reference contradiction. |
| ADAPTER_UNAVAILABLE | 503 | 5 | Existing selected adapter unavailable. |

06 §73 Phase 3 error names are design requirements, absent from the current enum
and transport maps; no `TASK_*` code is emitted by bootstrap. Register each later
code with explicit HTTP/CLI mapping in its separately authorized owner PR.

## 6. Required future tests and acceptance

| Proposed file / test group | Required proof |
| --- | --- |
| `tests/architecture/test_pr3_00_boundaries.py` | Recursive import scanner rejects direct SQL/ORM, vendor frameworks/SDKs and lower-layer harness dependencies; foundation reverse import prohibited; Application DTO boundary preserved. |
| Same architecture suite | Empty namespaces import without network, DB, worker, Skill routing or provider activation; no new dependency/production harness change; no vendor-specific scientific schema. |
| `tests/integration/phase3/test_pr3_00_bootstrap.py` | Real PostgreSQL 18: clean upgrade, accepted Phase 2→bootstrap upgrade, sole head, empty inventory delta, data/hash/trace preservation, forward-only downgrade refusal with unchanged revision/catalog. |
| Existing Phase 1/2 regression | All required accepted phase-exit suites continue to pass, including migration/history/constraints and Human/Agent boundary guards. |
| Scope audit | Only approved skeleton/empty migration/tests/docs; no task business implementation or future PR behavior. |

Future commands: `uv sync --locked`, `uv run ruff check .`,
`uv run ruff format --check .`, `uv run pyright`,
`uv run alembic heads`, and
`uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture tests/integration/phase3/test_pr3_00_bootstrap.py`.
Run the accepted Phase 1/2 regression/exit commands from their packs against
disposable PostgreSQL as well; do not replace those with bootstrap-only tests.
Record exact commands, versions, counts, failures/skips, inventory comparisons
and review findings. Open P0/P1 prevents acceptance. No later PR begins after
PR3-00 evidence without separate authorization.

Documentation-only revision. Future acceptance commands above are not current
execution evidence and do not establish Phase 3 GO.
