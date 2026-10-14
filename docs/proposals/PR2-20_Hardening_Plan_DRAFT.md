# PR2-20 Hardening Plan — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

## Start here (for the implementer)

After owner approval and separate implementation authorization, the first slice
builds file-based report helpers, disposable database fixtures and tests of existing
commands. It measures source lookup, manuscript scientific trace and review and
decision behavior without changing their contracts, queries or database schema.
It collects migration, adapter, license and security evidence and produces six
reports, marking missing prerequisites as blocked. These reports support a later
owner decision; completing this slice does not establish full Phase 2 exit.

**Build in this order** (exact paths and commands are in [the build guide](#132-ordered-build-steps-and-ownership-paths)):

1. Define the file-only evidence records and unit tests using [types and limits](#123-file-only-dtos-limits-and-enums).
2. Add the disposable PostgreSQL support helper and reuse the fixtures named in [build step 2](#132-ordered-build-steps-and-ownership-paths).
3. Build small correctness fixtures, then scaled fixtures using [benchmark defaults](#122-benchmark-defaults--owner-adjustable) and [build step 3](#132-ordered-build-steps-and-ownership-paths).
4. Add [the PostgreSQL test cases](#134-exact-test-files-and-required-cases), retaining [the existing lock sequences](#133-exact-lock-order-per-exercised-commandquery).
5. Add the opt-in benchmark using [the measurement protocol](#51-measurement-protocol) and [build step 5](#132-ordered-build-steps-and-ownership-paths).
6. Collect migration and adapter inventories and license/security sources using [build step 6](#132-ordered-build-steps-and-ownership-paths) and [the required inventory cases](#134-exact-test-files-and-required-cases).
7. Generate [all six documentation artifacts and the exit report](#10-documentation-deliverables-and-phase-2-exit-report), retaining every required row.
8. Run the checks and separate benchmark command in [build step 8](#132-ordered-build-steps-and-ownership-paths); record exact results.
9. Review specifications, diff and evidence independently, resolve blocking findings, attach owner dispositions and stop before Phase 3 ([acceptance criteria](#92-proposed-acceptance-criteria-for-the-future-pr)).

**Background to skip on first read:** [authority and baseline observations](#1-purpose-authority-and-inspected-baseline),
[the glossary](#11-glossary) and [dependency and owner-override rationale](#14-dependencies-and-owner-override-points).
Consult them when needed; [the draft decisions](#12-decisions-taken-in-this-draft) and [deferred work](#135-not-in-this-slice) still govern the build.

**Five rules that would fail review if broken:**

1. Build only the authorized slice: no missing prerequisite features, new public commands, schema changes, query changes or indexes ([scope decisions](#121-scope-subject-and-exit-decisions), [first-slice database boundary](#131-exact-ddl-sketch-and-catalog-assertions)).
2. Preserve exact frozen versions, hashes and immutable history; never substitute latest versions or repair historical facts ([invariants](#3-invariants-and-evidence-boundaries)).
3. Use existing application boundaries and fresh authorization; retain complete blockers, review basis, closure, replay and lock protection ([invariants](#3-invariants-and-evidence-boundaries), [lock sequences](#133-exact-lock-order-per-exercised-commandquery)).
4. Use disposable PostgreSQL fixtures and record reproducible, sanitized evidence; never expose secrets or treat fake adapter tests as real acceptance ([required cases](#134-exact-test-files-and-required-cases), [evidence limits](#123-file-only-dtos-limits-and-enums)).
5. Keep failed, blocked, unrun and skipped results distinct from passes; missing mandatory paths or open blocker/major findings prevent exit success ([exit decisions](#121-scope-subject-and-exit-decisions)).

**Scope:** documentation proposal only. This file is not an architecture freeze,
ADR, execution pack, migration authorization, security certification, scientific
approval or Phase 2 exit declaration. Owner approval of this plan must precede a
separate implementation authorization. Only this proposal is changed by this task.
Shorthand and authority numbers are defined in §11; read that glossary first.

## 1. Purpose, authority and inspected baseline

PR2-20 assembles reproducible evidence that the admitted Phase 2 capabilities are
operable, bounded, compatible with frozen Phase 1, and ready for an owner exit
decision. It covers indexes/query plans, adapter/version inventory, migration
clean install/upgrade, license/security notes, documentation and the Phase 2 exit
report. Performance and favorable review cannot substitute for scientific
correctness, missing prerequisite commands or unrun acceptance tests.

| Authority/base | Constraint carried into this proposal |
| --- | --- |
| [System Architecture 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), scientific principles, reference/version rules, implementation constraints and Appendix H | One scientific truth owner, exact frozen closure, immutable history, bounded modular monolith and replaceable Harness. |
| [Correction Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A18–A23 | R2/R3/R4 precedence, frozen Phase 1 preservation, bounded schema admissions, fresh temporal authorization and scoped minimal Decision. |
| [Global Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), Phase 2 registry and §12 | Existing named entities/relations own semantics; hardening reports are engineering evidence, not new canonical scientific objects. |
| [Cross-Phase Contracts 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§9–18, 24, 38, 41, 49, 52 | Stable commands/errors/queries, additive migration, immutable historical reads, deny-by-default project access, golden regression and documentation synchronization. |
| [Phase 2 Specification 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §§44–46, PR2-20, §§49–56 | Six hardening deliverables, performance SHOULD baselines, mandatory architecture tests, full exit checklist and STOP before Phase 3. |
| [Phase 2 Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), §§1–2, 6–7 | PreparedSubmissionVersion means a prepared package, not external send; typed provenance, governance separation, migration preservation and PostgreSQL 18.x. |
| [Harness Integration 09](../harness/09_Harness_Integration_Specification_v1.0.md), §§17–24, 29 | Material strategy revisions identifiable, execution pins distinguished from references, supply-chain review and no direct Harness persistence writes. |
| [PR2-15 RevisionAction base](PR2-15_RevisionAction_Contract_DRAFT.md) and [PR2-16 Basic Approval base](PR2-16_Basic_Approval_Contract_DRAFT.md) | Owner approved both on **2026-10-14**, as an inherited proposal dependency; implementation is in progress. Their completed-action, exact-target, replay, blocking-gate and bounded-slice choices are the base, not gaps for PR2-20 to redesign. |

The base files retain DRAFT headings and unresolved questions. The approval date
above is an inherited proposal assertion, not approval evidence supplied by this
documentation task or inferred from headings or this checkout's verification date.
Approval does not prove implementation or whole-PR acceptance. At execution freeze, attach the approved subject/revision and owner
dispositions; if implemented contracts differ, record the discrepancy and return
it to the owning PR. The decisions in §12 settle this hardening draft only; they
do not settle another PR's open policy question.

Addendum A18–A20 supersedes conflicting older 05/12/registry examples. For hash,
schema and governance details use the incorporated
[Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md),
[Governance R2 17](../architecture/17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md),
[R3 18](../architecture/18_Phase2_Design_R3_Targeted_Remediation_v1.0.md) and
[Temporal R4 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md)
where applicable; no new hash scheme or generic receipt is proposed here.

### 1.1 Current code observations, not acceptance assertions

- [CI](../../.github/workflows/ci.yml) uses PostgreSQL 18, uv locked sync,
  Ruff, Pyright, upgrade-to-head and pytest. It currently asserts
  `0042_pr2_15_minimal_decision` as head. Future hardening must inspect the
  authorized head rather than carry this snapshot value forward blindly.
- [0042](../../migrations/versions/0042_pr2_15_minimal_decision.py) supplies
  the minimal Decision and typed conclusion/review basis. RevisionAction and
  Basic Approval implementation are not present in this inspected baseline.
  [DecisionRepository](../../src/researchbase/persistence/decision_repository.py)
  coordinates request advisory lock → exact conclusion row → sorted SHARE-table
  inventory → closure/authority/reviews; lock and statement bounds are 10s/30s.
- [ManuscriptScientificTraceService](../../src/researchbase/application/manuscript_scientific_trace.py)
  uses authorized explicit repository reads and typed trace DTOs. It distinguishes
  citation/placement from support. Structural trace readback must not be advertised
  as full revalidation of every historical hash unless that verification ran.
- [OpenAlexSearchCapability](../../src/researchbase/adapters/openalex.py)
  identifies its native mapping as `works-v1`; [CrossrefVerifier](../../src/researchbase/adapters/crossref.py)
  uses `doi-v1` and provider `REST-unversioned`. A mapping label is not an upstream
  release pin. [NativeResearchStrategy](../../src/researchbase/application/native_research_strategy.py)
  identifies `native-storm-like` / `candidate-v1`.
- [ScientificRAGCapability](../../src/researchbase/application/scientific_rag_provider.py)
  has typed requests/candidates and a fake test adapter. Source inspection finds
  no PaperQA2 or official STORM adapter implementation; the dependency manifest
  contains neither package. Fake response tests cannot close PaperQA2 acceptance.
- [README](../../README.md) has an early “Phase 2 is not implemented or authorized”
  statement alongside later onboarding instructions and implemented Phase 2 code.
  Future documentation must reconcile status against owner gate evidence without
  treating code presence as acceptance. It also reports no repository license file.
- [harness.lock.yaml](../../harness.lock.yaml) distinguishes executable, conditional
  and reference-only dependencies, including an unresolved plugin-eval revision.
  Its presence alone proves neither activation nor reproducible executable intake.

Refresh this inventory from the execution subject. No baseline observation is a
license opinion, current vendor advisory assessment or performance measurement.

## 2. Proposed scope and non-goals

Propose six workstreams under a separately authorized PR2-20 execution pack:

1. Measure canonical DB hot paths, audit FK/index coverage, propose only justified
   additive indexes and safe query refinements, and repeat correctness/race tests.
2. Reconstruct adapter/strategy/provider/dependency versions and replacement
   compatibility, including material artifact/execution provenance.
3. Verify empty PostgreSQL install and populated upgrades, preflight failure,
   history preservation and downgrade refusal on disposable databases.
4. Produce source-backed license, copyright, privacy and security intake notes.
5. Synchronize supported commands, limitations, operational guidance and trace demos.
6. Assemble the exact Phase 2 exit checklist with evidence, unresolved findings,
   owner decisions and a STOP statement.

Non-goals: implementing missing PR2-00–19 features; widening Decision purposes,
RevisionAction relevance or Approval grant consumption; resolving Issues through
an optimization; external venue submission/ExternalEffect; Phase 3 Agent Runtime,
SkillRouter, generic capability gateway or orchestration; full IAM/compliance;
new vector DB, queue, Redis, service or runtime dependency; historical rehash,
rewrite, pruning or migration squash. No source, migration, test, config, lock or
authoritative document is changed in this documentation task.

Hardening may expose defects. Return semantic/feature defects to an explicitly
authorized owning PR; architecture deviations require ADR/Architecture Question
before implementation. PR2-20 cannot absorb later functionality to make exit green.

## 3. Invariants and evidence boundaries

1. **Deterministic fact precedes authority.** A fast query, APPROVE, PROCEED,
   completed RevisionAction, passing report or confident adapter output cannot
   override INVALID/STALE provenance or an applicable OPEN/BLOCKING Issue.
2. **Exact frozen history.** Every formal path retains concrete version IDs,
   existing hash schemes and owning relations. No latest/current substitution,
   soft `target_type + target_id`, JSON semantic core, scientific DELETE CASCADE
   or change to frozen Phase 1 facts/hashes/lifecycle rules.
3. **Semantic separation.** Hypothesis != Claim; ExperimentSpec != Run;
   Review != Decision != Approval != Command != ExternalEffect. RevisionAction
   records completion, not resolution; Basic Approval grant creation is not
   consumption or release. Prepared package freeze is not venue delivery.
4. **Literature/collaboration distinctions.** Source != LiteratureEvidence;
   SearchResult != Evidence; citation != support; DiscussionTurn and ResearchBrief
   remain candidates unless existing owning Application commands promote them.
5. **Same boundary and access.** Human and Agent use authenticated Application
   services → repository/UoW → persistence → PostgreSQL. Domain imports no ORM,
   FastAPI/Typer/vendor/Harness implementation. DTOs expose no ORM entities.
   Optimization retains project links, membership, independence and fresh temporal
   checks; a global source identity does not confer cross-project read access.
6. **No correctness traded for speed.** Preserve complete eligible review basis,
   all applicable blockers, closure inputs, stable ordering, replay normalization
   and lock coverage. No favorable review subset, truncated closure, hidden
   pagination, cache-only validity gate or removal of anti-phantom protection.
7. **Engineering reports are derived evidence.** Inventory/report files have
   no approval authority or scientific lifecycle. Include subject revision and
   dirty diff identity; changed subjects invalidate earlier acceptance attribution.
8. **Truthful results.** PASS requires completed assertions for the named subject.
   FAIL, BLOCKED, NOT RUN and approved optional deferral remain distinct. Skips
   never count as passes. Open P0/P1 prohibits exit success.

## 4. Commands, queries and DTOs — preserve existing contracts

Propose **no new public Application command, endpoint, CLI group, domain DTO or
error enum**. PR2-20 exercises the owning PRs' approved DTOs unchanged. First-write,
historical read/replay and future grant consumption remain separate paths with
their existing authorization and transaction semantics.

| Boundary | Hardening exercise and compatibility obligation |
| --- | --- |
| Source identifier lookup and search ingestion | Authorized exact normalized identifier lookup, project linkage, batch result persistence and idempotent retries; do not alter verified identity or delivery certainty semantics. |
| Exact manuscript scientific trace | Existing `trace(principal, project, publication, manuscript)` and `ManuscriptScientificTrace`; compare exact IDs, edges, hashes, warnings and citation/support labels before/after optimization. Preserve historical version and authorization behavior. |
| PR2-15 Decision | Minimal `RecordDecisionCommand` with complete eligible saved review basis, exact conclusion, immutable replay and no replacement. Do not invent revision-purpose support through PROCEED. |
| Approved RevisionAction base | Exercise `record_revision_action` / `read_revision_action` once implemented, seven finite result shapes, immutable correction/replay and completion != Issue resolution. Unavailable dependent paths deny. |
| Approved Basic Approval base | Exercise `request_approval`, `decide_approval`, exact readback and request/decision/grant replay once implemented. Respect approved purpose/target/command tuple and HUMAN approver independence; deferred tuples remain unavailable. |
| PR2-17/18 and PR2-19 boundaries | Use their separately approved prepared-package/authorship/consent, conservative novelty, golden and failure-injection contracts. No helper bypasses authority to produce exit evidence. |

Public command fields remain owned by their admitted contracts. Section 12 pins
the file-only evidence types, benchmark inputs and existing error mappings. The
first slice exercises only the exact boundaries listed in §13.3; future boundaries
remain blocked until their owning contract and implementation are accepted.
An optimization must produce the same material result and denial behavior as its
pre-change reference.

### 4.1 Proposed engineering evidence records, file-only

These are closed report layouts, not generic scientific persistence or runtime APIs:

| Record | Required fields/content |
| --- | --- |
| `QueryPlanEvidence` | Case ID; service/repository method; subject/SQL digest; sanitized parameter class; fixture seed/counts/skew/fan-out; PG/Python/driver versions; settings/stats; index definitions; repetitions/warm-up; raw plan/log references; timing, buffers, query counts and lock waits; correctness comparison; result/limitation. |
| `AdapterInventoryEntry` | Capability/adapter ID, local mapping version and source digest/revision; upstream repository/package and immutable resolution or explicitly unversioned API; model/provider/API profile; enabled/test/reference/deferred mode; dependency/lock provenance; corpus/index format; material provenance location; source/license/security evidence/date; compatibility tests; owner and unresolved items. |
| `MigrationEvidence` | Start/target revisions and script digests; PG server identity/version; fixture classification; exact commands, exit codes/logs; Alembic/catalog inventory; before/after canonical hashes/IDs/edges; invalid-state predicate/error/rollback; empty downgrade/nonempty refusal results; restored-read evidence. |
| `ExitCriterionEvidence` | Literal 05 §52 criterion; corrected terminology; required owning PR/approved contract; implementation/acceptance subject; test node/command/result counts; migration/demo links; review findings and dispositions; status and reason. |

Use UTF-8 Markdown tables plus bounded structured evidence files only where useful.
Evidence may carry schema-format version and file SHA-256 for reproducibility;
neither becomes a new scientific hash scheme, canonical entity or AgentExecution.
No secrets, raw proprietary prompts, restricted fulltext or database passwords in
reports, EXPLAIN parameters, command logs or artifacts.

## 5. Index/schema proposal and query-plan work — no migration

**Default: DO NOT ADD SCHEMA.** No table, semantic column, enum, report entity,
materialized scientific source of truth, stored performance status or hash payload
is proposed. Existing unique/partial/composite indexes may already cover a need;
catalog evidence and measured plans precede any DDL recommendation.

| Query family | Proposed candidate physical access path, subject to measurement |
| --- | --- |
| Normalized source identity + access | Existing identifier uniqueness/lookup and project-link keys first; consider an uncovered project/source or identifier predicate B-tree only where actual lookup plans require it. Never replace the conditional verified/binding contract with unconditional uniqueness. |
| Exact trace fan-out and upstream impact | Check parent+ordinal and target-FK coverage across manuscript placements, conclusion claim/literature inputs, support snapshot relations, evidence relations and SourceVersion lineage. 0037 already indexes claim/conclusion placement targets. |
| Review/blocking gate | 0040 already indexes concrete review targets and `(review_record_id,severity)`. Evaluate an additional partial `(review_record_id)` index for `status='OPEN' AND severity='BLOCKING'` only after Issue disposition exists and measured cardinality justifies it; current all-OPEN data may gain nothing. |
| Decision basis and historical reads | 0042 already supplies project/actor/predecessor and reverse basis-target indexes; UNIQUE basis-owner keys can cover leading decision lookups. Do not add duplicate indexes by different names. |
| RevisionAction/Approval/consumption | Inspect their accepted migrations first. Check concrete result/basis FK coverage, approved correction uniqueness, request target/status and grant expiry/consumption lookup coverage. No guessed DDL for tables absent from the execution subject. |
| Membership/temporal entitlement | Check existing project+actor/role and active-membership access. Index only predicates supported by the accepted temporal policy; an index cannot make cached roles or statement-start time authoritative after waits. |

For each candidate, specify exact table/columns/order/predicate/name, existing
coverage, real SQL, measured benefit, storage/write cost, planner statistics,
required lock and bounded deployment time, reversibility and test evidence in
the future execution pack. No blanket “index every column” or unconditional
uniqueness change. RESTRICT FKs and immutable-history guards stay intact.

If authorized later, use a new additive forward Alembic migration with one head;
never edit accepted migration bytes or guess the next revision while prerequisite
PRs are being implemented. Prefer ordinary transactional index creation in a
maintenance window for bounded Phase 2 datasets. `CREATE INDEX CONCURRENTLY`
needs an explicit nontransactional migration protocol, invalid-index recovery,
retry and clean/upgrade evidence before use; it is not an Application transaction
exception. Do not drop existing required indexes without a separately reviewed
replacement/compatibility argument. Index-only downgrade must preserve history;
canonical-table downgrade refusals from owning PRs remain mandatory.

### 5.1 Measurement protocol

1. Freeze execution revision/diff, locked environment, PostgreSQL **18.x exact
   patch**, fixture generator seed, row counts/fan-out/skew, settings and query set.
   Use synthetic disposable same-project and cross-project data; never benchmark
   against production or retained history.
2. Measure identifier hit/miss/denied lookup; typical/high-fan-out historical
   manuscript trace; source-retraction downstream lookup; complete review/blocker
   gate; Decision/RevisionAction/Approval first-write and replay where available.
   Include empty sets, many favorable reviews plus one blocker, superseded exact
   versions, shared global source and invalid closure. Distinguish DB execution,
   authorization/hash work, lock wait, DTO serialization and external latency.
3. Capture `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` on actual read SQL, with
   statistics refreshed, sanitized parameters and warm/cold-cache disclosure.
   ANALYZE executes SQL: never apply it to mutating commands outside disposable
   fixtures. Use application SQL capture/query counts and contention tests for
   writes; no benchmark helper rewrites canonical facts.
4. Proposed repeatable warm-run protocol: five unreported warm-ups followed by
   100 measured calls per worker per case on the declared reference host, fixed concurrency
   profiles 1 and 4, p50/p95/max and full sample references. Host noise/variance
   means rerun or BLOCKED, not an invented pass. Use the owner-adjustable fixture,
   host and tolerance defaults in §12.2. No absolute latency claim without the
   recorded data envelope. Keep deterministic plan/correctness checks in ordinary CI;
   wall-clock thresholds belong to the declared benchmark job.
5. 05 §45 SHOULD targets are identifier lookup p95 **<100ms** and typical
   manuscript scientific trace **<2s**. Propose measuring both through the
   authorized service boundary, excluding external calls and reporting included
   auth/serialization costs. Record misses/denials and high-fan-out cases separately.
   A target miss requires explicit owner disposition; it cannot silently become
   PASS or override correctness. No performance waiver closes a P0/P1.
6. Compare before/after results and plans, row estimates/actuals, loops, buffers,
   sorts/spills, query count, index size and ingestion cost. No fragile assertion
   on exact planner node text or prohibition of every sequential scan; small-table
   scans can be appropriate. Reject N+1 growth, unrelated-project scans or unbounded
   closure work; optimization preserves the complete response/denial contract.

## 6. Adapter/version, license and security hardening

Inventory all enabled, test-only, method-reference and deferred paths separately:
OpenAlex/Crossref and document retrieval, SearchCapability, ScientificRAG/PaperQA2,
native baseline/STORM-like strategies, optional official STORM adapter, model/LLM
providers, index/parser dependencies and material external Harness tooling. Resolve
from actual source plus `pyproject.toml`/`uv.lock`/reviewed intake; a URL, `latest`,
`main`, mapping label or reference-library entry is not an executable pin.

For hosted unversioned APIs record API profile, observation date, sanitized contract
fixtures and local adapter revision, with provider reproducibility limitations.
Do not fabricate a vendor commit. For package adapters record exact locked package,
hashes and authoritative immutable upstream tag/commit mapping. Material
strategy/adapter/model/prompt revisions must reconstruct execution/artifact
provenance through existing admitted mechanisms; do not add generic Agent runtime.

Replacement tests run against the same typed candidate/request contract and exact
source set: normal/empty/contradictory output, unsupported/malformed source/locator,
version mismatch, cancellation, timeout/rate limit, uncertain delivery, retry,
project/corpus separation and byte-for-byte canonical-state nonmutation. Offline
fixtures are deterministic; live-provider probes are separately configured,
budgeted and optional unless the owning PR requires them. Fake-adapter evidence is
labelled fake. A supported adapter upgrade needs intake and relevant regression,
not an automatic lock update in hardening.

License/security notes must identify authoritative source, exact assessed revision,
review date, reviewer, license text/digest, notices/redistribution obligations,
dependency scope and unresolved evidence. Assess software license, provider terms,
source/fulltext copyright and cache/index redistribution separately. No repository
license is selected by this proposal; no permission is inferred from public access.
Future advisory review records tool/database version, scan date, affected resolved
versions, severity, exploitability, remediation and approved dispositions. This
draft asserts no current CVE or legal conclusion and copies no stale package/license
claims from 05 §55. Offline/unavailable advisory checks remain BLOCKED/NOT RUN.

Required bounded security cases for existing supported surfaces:

- Secrets absent from errors, headers/URLs, EXPLAIN evidence, logs, prompts,
  artifacts and candidate output; redact keys and restricted query text.
- Retrieval HTML/PDF/tool content is untrusted; no scripts/prompt instructions
  execute or grant authority. URL/redirect/private-network, size/time/decompression
  and parser failure protections are tested where document retrieval is enabled.
- No loading of untrusted serialized PaperQA/index state (including unsafe
  deserialization); local indexes/caches are derived and project/corpus isolated.
  Regeneration/replacement must not require canonical migration.
- Proprietary discussions/queries/fulltext are sent only within configured provider
  scope; no public cache export by default. Test denied project access and corpus
  confusion, including shared globally identified sources.
- Direct adapter/strategy/Harness SQL/ORM mutation, self-weakened Harness, stale
  credential replay and Agent approval escalation deny. The trusted-account local
  deployment limitation remains explicit; hardening does not claim Agent sandbox
  or multi-user isolation that the repository has not implemented.

If a required protection is missing, record a concrete finding and separately
authorize its bounded remediation. Do not enable an unsafe optional adapter or
invent broad security infrastructure to complete an inventory row.

## 7. Errors, concurrency and transaction rules

No `HARDENING_FAILED` Application error or migration-status canonical record is
proposed. Existing [ErrorCode](../../src/researchbase/foundation/errors.py) meanings
and owning PR mappings remain stable; older design names absent from that enum
must not be advertised as implemented transport codes.

| Existing category | Hardening regression obligation |
| --- | --- |
| `VALIDATION_ERROR` | Closed DTOs and malformed identifiers/unsupported shapes still deny without partial writes. |
| `AUTHENTICATION_REQUIRED`, `FORBIDDEN` | Missing principal, expired/revoked credential, cross-project access and disclosure denial remain nondisclosing. |
| `NOT_FOUND` and owning source-not-found codes | Exact authorized absence stays distinct from integrity failure; no latest fallback or existence leak. |
| `PROVENANCE_CLOSURE_VIOLATION`, `FROZEN_REFERENCE_REQUIRED`, `VERSION_NOT_FROZEN`, `IMMUTABLE_RECORD` | Corrupt/unresolved/unfrozen history fails under its existing command mapping; no optimization treats structural presence as valid closure. |
| `IDEMPOTENCY_CONFLICT`, `CONCURRENT_MODIFICATION` | Changed-material replay, races and bounded fresh-transaction retries preserve existing result and rollback semantics. Do not rename every timeout to a retryable conflict. |
| `ADAPTER_UNAVAILABLE`, `ADAPTER_VERSION_MISMATCH` | Unsupported/unresolved adapter resolution denies under the existing adapter boundary; provider failure/delivery certainty taxonomy remains separate. |
| `LEGACY_STATE_INVALID` | Preserve the already contracted legacy predicate where applicable. Other migration preflight errors retain their owning migration's exact SQLSTATE/message; no new legacy rejection policy here. |

Engineering checks return nonzero on failure and record command, exit code, counts
and sanitized diagnostic. Missing environment produces BLOCKED evidence, not an
Application success DTO. Any new error mapping needs owning-contract approval.

Synchronous DB I/O and one Application command per UoW transaction remain required.
External retrieval/search/RAG/model calls execute outside long DB transactions,
using the existing reservation/dispatch/completion boundaries; retry must retain
delivery certainty and command identity. Benchmarking is not permission to move
network calls inside a DB lock.

Preserve each admitted command's lock order and snapshot/phantom protection. In
particular, no removal or narrowing of Decision's SHARE inventory, exact-target
locks or review coordination is authorized merely because contention is costly.
Any alternative protocol requires a separately approved correctness argument and
observable normal-role SQL race evidence. Test blocker insertion, authority or
credential expiry/revocation, impact/retraction, correction forks, approval
decisions and consumption races where those contracts are admitted. Fresh trusted
DB time after relevant waits governs first-time authorization/expiry; statement-
start/application-cached time cannot extend authority.

Historical replay authenticates and checks current read entitlement, validates
saved material and returns only the original result. It neither re-executes nor
reapplies current first-write gates as replacement history. Failed gates leave no
partial business state or committed success event. Preserve the base contracts'
explicit distinction between derived stale/expiry readback and separately
authorized lifecycle writes; hardening adds no hidden commit-on-error exception.

## 8. Migration clean install, upgrade and preservation plan

Use disposable **real PostgreSQL 18.x**, never SQLite. Freeze the complete Alembic
chain and accepted file digests before executing:

| Path/case | Required evidence |
| --- | --- |
| Empty DB → authorized head | Exact `alembic upgrade head`, `heads`, `current`; one head; expected tables, columns, indexes, constraints, triggers and supported command/read smoke. Second upgrade is a no-op. |
| Frozen `0018_current_pointer_same_parent_integrity` → head | Populate accepted Phase 1 scientific chain and contract-permitted identity/project state before upgrade. Apply the exact legacy preflight policy; legal data succeeds with original hashes/IDs/edges preserved. Invalid state fails without rewriting attribution/history. Do not assume every populated 0018 state is upgradeable. |
| Accepted populated Phase 2 checkpoints → head | At minimum source/search/evidence/snapshot, conclusion/manuscript/placements, review/minimal Decision, and final accepted RevisionAction/Approval/package/novelty predecessors. Inventory exact revisions after those PRs merge; present 0042 is a checkpoint, not the promised final head. |
| Invalid legacy/constraint state and interrupted upgrade | Owning-contract fixtures, deterministic preflight/SQLSTATE, bounded locks, complete rollback/no partial head advance; recovery follows the accepted protocol with no trigger bypass or historical repair UPDATE. |
| Empty downgrade/round trip | Only downgrade paths permitted by owning migrations; predecessor catalog intact and re-upgrade works. |
| Populated canonical downgrade | Required refusal occurs before data loss; history/hash/edges remain readable. Do not call unsupported destructive downgrade “tested rollback.” |
| Index migration/removal if admitted | Same clean/populated upgrade checks plus catalog equivalence and no history alteration; remove only added indexes on reversal. Nontransactional failure recovery requires explicit tests if approved. |

Capture schema catalogs and canonical fixture manifests before/after. Reconstruct
hash payloads through accepted validators, check scientific and literature closure,
same-parent pointers, RESTRICT FKs, immutable UPDATE/DELETE guards, append-only
events, enum/check/unique constraints and exact historical read/replay after restart.
Never “fix” illegal fixtures by dropping triggers or mutating frozen rows to pass
upgrade. Preserve prior migration digest pins and frozen Phase 1 golden evidence.

Operational docs include backup-before-upgrade, disposable restore rehearsal,
required privileges, bounded maintenance/lock timing, expected preflight failures,
roll-forward recovery and refusal of history-destroying downgrade. Production or
retained database upgrade is outside this plan's test authorization.

## 9. Tests to add and acceptance evidence

Future test names below are **planned**, not implemented or run by this draft.
Map each requirement to existing tests where sufficient; add focused assertions
for uncovered behavior rather than duplicating implementation mechanically.

| Test family | Proposed additions/evidence |
| --- | --- |
| Index/query plans | Catalog coverage without duplicate indexes; seeded representative plans/buffers; bounded query count/fan-out; before/after DTO and denial parity; source/trace benchmark profile; ingestion and contention cost. |
| Adapter inventory/compatibility | Enabled resolution matches lock/source/provenance; references cannot execute as pins; required candidate metadata/version; native/selected adapter replacement; unsupported source and version denial; no canonical DB writes. |
| Migration | Parametrized empty/0018/accepted populated checkpoints → head; no-op second upgrade; preflight atomic failure; historical hash/edge equality; guards remain enforced; empty round trip and populated refusal; recovery for admitted DDL. |
| Governance races | Full review/blocker lookup unaffected by filters/indexes; late blocker/retraction/expiry after witnessed wait; same and changed replay; correction fork and concurrent approval decision; approved consumption race only when separately implemented. Use DB blocker witnesses, not sleeps alone. |
| Security/privacy | Secret redaction, untrusted retrieval/index rejection, project/corpus isolation, denied disclosure, bounded provider data scope, injection cannot promote candidates or elevate authority. |
| Documentation/exit | Local links and executable command examples; current supported vs deferred status; criterion-to-node/log mapping; exact subject and counts; no optional/fake/skip evidence masquerading as required PASS. |
| Frozen regression | Full Phase 1 golden/immutability/closure/cross-adapter tests; Phase 2 unit, PostgreSQL, adapter, migration, contract, E2E and PR2-19 failure injection; Ruff/Pyright and uv lock checks. |

### 9.1 Mandatory 05 §49 architecture tests

Every named requirement needs a collected CI test with equivalent assertions and
an explicit mapping. Missing implementation is a blocked criterion, not a test
which vacuously passes because the forbidden feature is absent.

| Required test | Required proof |
| --- | --- |
| `test_literature_source_not_evidence` | Source identity alone never supplies Claim support. |
| `test_search_result_not_evidence` | Retrieval provenance requires separate resolved/validated promotion. |
| `test_citation_not_claim_support` | Citation placement alone is citation-only in trace and cannot satisfy support. |
| `test_strategy_does_not_import_persistence` | Strategy import/dependency graph excludes persistence/ORM mutation. |
| `test_adapter_does_not_write_db` | Adapter has no direct canonical write path; observed calls produce candidates. |
| `test_no_storm_specific_core_schema` | Catalog/domain inventory has no vendor canonical schema or state ownership. |
| `test_no_paperqa_specific_core_schema` | PaperQA state/index is derived/replaceable; no vendor canonical schema. |
| `test_discussion_not_canonical_science` | Transcript/turn cannot bypass explicit promotion. |
| `test_manuscript_not_scientific_source_of_truth` | Exact placements reference owning facts; manuscript wording cannot overwrite them. |
| `test_review_does_not_mutate_target` | Review/Issue writes preserve target bytes/hash/closure. |
| `test_decision_does_not_mutate_history` | Choice/replay/revision trace preserves all prior records and inputs. |
| `test_approval_does_not_override_invalid_fact` | Actual Approval boundary denies invalid/stale closure and applicable blockers. |
| `test_external_call_not_inside_long_db_transaction` | Instrument real orchestration's transaction/session lifetime across provider dispatch, completion, timeout/cancellation and retry. |

Ruff/import guards alone do not prove runtime transaction isolation or approval
denial. Conversely, one passing happy-path integration test does not prove import
or schema boundaries. Run the appropriate complementary evidence.

### 9.2 Proposed acceptance criteria for the future PR

PR2-20 hardening acceptance requires: (a) all six workstreams delivered for the
fixed subject; (b) justified indexes/queries with contract parity, measured plans
and owner-disposed performance targets; (c) complete enabled/reference/deferred
inventory and material revision reconstruction; (d) required real PostgreSQL
paths and historical preservation passing; (e) assessed license/security evidence
with no open P0/P1; (f) every §49 requirement mapped and passing, required Phase 1
regression and Phase 2/PR2-19 suites passing; (g) accurate supported/deferred docs;
(h) independent review from specifications + diff + machine evidence, with concrete
location/evidence/violated rule/impact/action for each P0–P3 finding.

A blocked environment or missing prerequisite can yield a useful incomplete exit
report, but **cannot yield PR2-20 gate success or Phase 2 exit PASS**. Owner-approved
optional deferrals are recorded as deferrals; required failures/skips need actual
remediation or a separate architecture correction, not a renamed result.

## 10. Documentation deliverables and Phase 2 exit report

Propose the six exact artifact basenames required by 05 §52 under `docs/phase2/`,
with machine logs/manifests under the repository's agreed evidence convention.
Use `pr_evidence/pr2-20/<subject_sha256>/` for machine evidence. The subject digest
is SHA-256 of `canonical-json-v1({"subject_revision": revision,
"dirty_diff_sha256": diff_digest})`. It binds the revision and dirty diff digest. These future files are not created
by this documentation task.

| Artifact | Required content |
| --- | --- |
| `reference_system_inventory.md` | Native/reference/selected upstream modes, pins, enabled versions, licenses, security/intake status, provenance reconstruction and deferrals. |
| `adapter_compatibility_report.md` | Capability contract versions, tested matrix, replacement/nonmutation/isolation evidence, fake vs live distinction and unsupported configurations. |
| `migration_inventory_phase2.md` | Every revision/predecessor/digest/owning PR, schema/index purpose, clean/upgrade/rollback/refusal results and operational limitations. |
| `literature_trace_demo.md` | Exact source/version/locator → evidence/promotion/support paths, correction/retraction and hallucination denial, distinguishing search provenance from evidence. |
| `publication_trace_demo.md` | Exact manuscript placement → Claim/conclusion → experimental/literature closure; citation-only contrast; review → Issue → Decision → completed revision and separately gated approval/package history, no external send claim. |
| `phase2_exit_report.md` | Subject/approved contracts, literal criterion matrix below, performance report links, six artifacts, all exact commands/counts, independent review/dispositions, known limits and owner exit decision/STOP. |

Update README/developer/operator docs in a future authorized PR to show actual
supported DTO/CLI/API surfaces, installation and clean/upgrade commands, errors,
replay/authorization limitations, adapter/provider setup without embedded secrets,
copyright/cache policy, restore and troubleshooting, reference/test/deferred modes,
and Phase 3 stable boundaries. Contract changes trigger the 08 §49 ADR/spec/test
sync rule; they cannot arise silently from documentation corrections.

The exit report must retain **all 19** 05 §52 criteria:

| Literal exit criterion | Required dependency/evidence; current proposal disposition |
| --- | --- |
| LiteratureSource identity resolution | PR2-01 normalized identity/access/merge evidence; NOT ASSESSED here. |
| SourceVersion lineage/freeze | PR2-02 exact version/correction/retraction evidence; NOT ASSESSED. |
| LiteratureSearchPlan/Run provenance | PR2-03/04; registry name is LiteratureSearchExecution, distinct from experimental Run; NOT ASSESSED. |
| LiteratureEvidence source+locator trace | PR2-05 resolved version/locator/support promotion; NOT ASSESSED. |
| STORM-like Native ResearchStrategy | PR2-08 candidate/revision/eval/trace evidence; code presence alone insufficient. |
| PaperQA2 Adapter | PR2-07 selected actual adapter/pin/safety/compatibility evidence; missing in this baseline, BLOCKED pending prerequisite. |
| Academic Discussion explicit promotion | PR2-10 noncanonical transcript and explicit commands; NOT ASSESSED. |
| ScientificConclusion support-set freeze | PR2-11 exact sealed typed inputs/hash; NOT ASSESSED. |
| ScientificConclusion Frozen Provenance Closure | PR2-11 full experimental/literature hash/validity reconstruction; NOT ASSESSED. |
| ManuscriptVersion scientific placement | PR2-12/13 exact placements/readback; NOT ASSESSED. |
| Citation ≠ ClaimSupport | PR2-13/19 citation-only denial/trace; NOT ASSESSED. |
| Internal Review → Issue → Decision → Revision | PR2-14/15 approved RevisionAction plus required independently contracted disposition/re-review paths; minimal PROCEED alone does not close this. |
| Basic Approval frozen target / blocking gate | Approved PR2-16 implemented slice + deterministic denial and temporal/race tests; slice limitations remain explicit. |
| SubmissionVersion package freeze | Corrected by 12 to **PreparedSubmissionVersion**, PR2-17 manifest/authorship/consent/grant closure; external SubmissionVersion/send remains deferred. |
| Retracted-source impact propagation | PR2-19 end-to-end exact downstream invalidity/denial; NOT ASSESSED. |
| Hallucinated citation rejection | PR2-19 unresolved/fabricated source denied without canonical insertion; NOT ASSESSED. |
| PostgreSQL migrations/integration | All required PR2-20 paths and owning suites on real PG18; NOT RUN as future acceptance. |
| No STORM/PaperQA vendor-specific Core schema | Catalog + boundary/replacement tests across actual adapters; NOT ASSESSED. |
| Phase 1 Exit tests continue | Frozen golden/regression must continue PASS on final subject; NOT RUN as future acceptance. |

PR2-18 Novelty/Prior Art and PR2-19 remaining failure cases also need their owning
PR acceptance evidence even though not every feature has a separate literal §52
row. Attach them; do not remove them by narrowing the report to the checklist.
05 allows optional official STORM PR2-09 deferral only if native strategy required
tests pass; it does **not** grant the same exception to PaperQA2.

Only after all required evidence and owner dispositions are complete may the
report propose Phase 2 exit. Owner acceptance is separate from report generation
and scientific Approval. Then **STOP; wait for explicit Phase 3 GO**. A partial
report says exit BLOCKED, identifies dependencies and makes no later-phase promise.

## 11. Glossary

These definitions apply throughout this draft. Numbered authorities refer to the
linked governing documents in §1. Section 14 lists owner override points, not
undecided implementation choices.

| Shorthand | Meaning and governing document |
| --- | --- |
| 01 / 02 / 03 / 05 / 08 / 09 / 12–19 | Document numbers in `docs/architecture/`; 09 Harness means `docs/harness/09_Harness_Integration_Specification_v1.0.md`; titles and authority are in §1. |
| 11 / 13 / 14 / 16 / 20 | [TDG2](../architecture/11_TDG2_Phase2_Technology_Decision_Gate_v1.0.md) / [Field Contract](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md) / [Gap Closure R2](../architecture/14_Phase2_Design_Gap_Closure_R2_v1.0.md) / [Identity Contract](../architecture/16_Phase2_Identity_Ownership_and_Source_Contract_R2_v1.0.md) / [Minimal Decision Contract](../architecture/20_PR2_15_Minimal_Decision_Command_Contract_v1.0.md); governing companion documents. |
| R1 | First Phase 2 correction, now historical where superseded; Addendum 02 A17 and Correction 12 / Field Contract 13. |
| R2 | Second Phase 2 design correction; Addendum 02 A18 and companions 14–17. |
| R3 | Targeted remediation of R2 gaps; Addendum 02 A19 and Remediation 18. |
| R4 | Temporal authorization correction; Addendum 02 A20 and Temporal 19. |
| A17 | Initial Phase 2 gap closure; Addendum 02 A17. |
| A18 | R2 precedence and bounded schema admissions; Addendum 02 A18. |
| A19 | R3 targeted supersession; Addendum 02 A19. |
| A20 | R4 expiry-sensitive supersession; Addendum 02 A20. |
| A21 | Completed grant-receipt replay needs current read entitlement; Addendum 02 A21. |
| A22 | Legacy preflight and observable cross-expiry evidence; Addendum 02 A22. |
| A23 | Minimal internal scientific PROCEED Decision only; Addendum 02 A23 and companion 20. |
| TEMP-AUTH-01 | Lock, durable reread, fresh trusted DB time, authorization, then effect; Temporal 19 §1. |
| R-ref | Exact immutable-record or frozen-version reference with type, ID and content hash; Hash Contract 15 reference constructors. |
| I-ref | ID-only reference with type and ID, only where the payload permits it; Hash Contract 15 reference constructors. |
| sealed set / support-set freeze | Complete ordered typed dependency set cannot gain or lose material members after freeze; System 01 frozen closure and Hash Contract 15. |
| frozen closure | Recursively resolved exact immutable/versioned material dependencies; System 01 §12 and Cross-Phase 08. |
| canonical | Owning domain's single scientific source of truth; System 01 §3.2. |
| DTO | Data transfer object crossing a boundary; never an ORM entity; Cross-Phase 08 API contracts. |
| UoW | Unit of Work, one Application-command transaction; System 01 transaction rules and TDG2 11. |
| ORM | Object-relational mapper; persistence implementation only; System 01 layering. |
| DB / PG / PG18 | Database / PostgreSQL / PostgreSQL 18.x; Phase 2 Correction 12 and TDG2 11. |
| SQL / DDL | Structured Query Language / data definition language; PostgreSQL persistence under TDG2 11. |
| FK / RESTRICT | Foreign key / refusal of referenced deletion; System 01 persistence rules. |
| B-tree / partial / composite index | Ordered physical index / predicate-filtered index / multi-column index; Phase 2 05 PR2-20; no semantic authority. |
| SHARE / UPDATE / ROW EXCLUSIVE | PostgreSQL lock modes, including row `FOR SHARE`/`FOR UPDATE`; companion 20 and Decision repository protocol in §13.3. |
| phantom | Newly inserted row omitted by an earlier read; companion 20 concurrency rules. |
| replay / first-write | Return saved normalized result / perform a new effect; Temporal 19 and Addendum 02 A21. |
| SHA-256 / cjson / NFC / UTF-8 | Digest / canonical JSON serialization / Unicode normalization / text encoding; Hash Contract 15. |
| JSON / JSONB | Structured text encoding / PostgreSQL JSON storage; diagnostics and admitted locators only, never a generic semantic core; System 01 and Field Contract 13. |
| UUID / UUIDv7 | Exact identifier / time-ordered UUID; System 01 foundation types. |
| API / HTTP / CLI | Application interface / HTTP transport / command-line interface; Cross-Phase 08. |
| CI / E2E | Continuous integration / end-to-end tests; Phase 2 05 §§49–52. |
| PR / PR2 / S1 | Pull-request work package / Phase 2 package / first bounded slice; Phase 2 05 and companion 20. |
| ADR / TDG-2 | Architecture Decision Record / Phase 2 Technology Decision Gate; Cross-Phase 08 §49 and TDG2 11. |
| IAM / COI | Identity and access management / conflict of interest; System 01 bounded governance scope. |
| STORM / Co-STORM | Reference research/conversation strategies, replaceable outside Core; Harness 09 §10 and Phase 2 05. |
| PaperQA2 / RAG / LLM | Selected scientific question-answering adapter / retrieval-augmented generation / large language model; Phase 2 05 and Harness 09. |
| OpenAlex / Crossref / DOI | Literature providers / digital object identifier; Phase 2 05 and Identity Contract 16. |
| Harness / Skill / Core | External engineering or scientific tooling / bounded responsibility / canonical ResearchBase state; Harness 09 §§2, 9. |
| READY / READY_FOR_SUBMISSION / PREPARE_SUBMISSION | Publication readiness / Decision purpose / preparation command tuple; Governance Contract 17; unavailable prerequisites remain in §13.5. |
| ApprovalGrantConsumption / ExternalEffect | Durable grant-consuming result / actual external change; Governance Contract 17; neither is basic grant creation. |
| p50 / p95 / max / ms | Median / 95th percentile / largest sample / milliseconds; measurement convention fixed by §12.2 under Phase 2 05 §45. |
| fan-out / skew / N+1 | Child count / uneven distribution / query count growing with each child; performance evidence under Phase 2 05 §45. |
| SQLSTATE | PostgreSQL error classification; owning migrations and UoW error normalization. |
| P0 / P1 / P2 / P3 | BLOCKER / MAJOR / MINOR / SUGGESTION finding; AGENTS.md §10 and Harness 09 §16. |
| PASS / FAIL / BLOCKED / NOT RUN / DEFERRED | Asserted success / asserted failure / missing prerequisite / not executed / explicitly permitted optional deferral; Harness 09 §19 and §12.3. |
| SHOULD / STOP / GO | Performance recommendation / halt at gate / explicit next-phase authorization; Phase 2 05 §§45, 52. |
| UTC / ISO 8601 / Z | Coordinated Universal Time / timestamp encoding / UTC suffix; Hash Contract 15 instant encoding. |
| vCPU / GiB / MiB / SSD / MB / GB | Virtual CPU / binary memory units / solid-state drive / DB-setting units; benchmark profile in §12.2, engineering conventions only. |
| OS / x86-64 / REST / PDF / HTML | Operating system / host instruction set / hosted API profile / document formats; TDG2 11 and Phase 2 05 adapter boundaries. |
| ANALYZE / BUFFERS / ACCESS SHARE / SERIALIZABLE / REPEATABLE READ | PostgreSQL statistics/plan diagnostics/lock/isolation modes; existing persistence protocols and §13.3. |
| ID / UUID5 / Literal / enum | Identifier / deterministic namespaced UUID / Python exact-value type / finite accepted values; existing PR2-14 code and §12.3. |
| CVE | Common Vulnerabilities and Exposures advisory identifier; assessed supply-chain evidence under Harness 09 §22. |
| subject / head / checkpoint | Revision plus dirty diff identity / authorized Alembic tip / accepted populated predecessor; Phase 2 05 hardening and §12.1. |
| `phase1-final-v4` / 0018 / 0037 / 0040 / 0042 | Frozen Phase 1 baseline / pointer-integrity migration / placement indexes / review schema / minimal Decision schema; owning migration files and §8. |
| `works-v1` / `doi-v1` / `candidate-v1` / `REST-unversioned` | Local adapter mappings / native candidate format / explicitly unpinned hosted API; inspected source in §1.1 and Harness 09 §17. |

## 12. Decisions taken in this draft

These decisions adopt all recommendations formerly left as open questions. The
owner can overrule them explicitly before execution. They do not authorize work
or amend another PR's contract. An override must update the affected tables and
checks before the separately authorized execution pack is used.

### 12.1 Scope, subject and exit decisions

1. Freeze approved contract revisions and final implemented revisions. Require
   owning acceptance evidence. Missing mandatory paths produce a BLOCKED exit
   report. A bounded slice cannot constitute full Phase 2 exit.
2. Attach exact owner approval and dispositions for the inherited 2026-10-14 base
   assertion. Until attached, report that dependency as unverified. Keep base
   precedence. Return base ambiguities to their owners; do not edit base drafts.
3. Missing PaperQA2, Issue disposition, revision-purpose Decisions and grant/package
   effects are separately authorized prerequisites. Optional STORM language does
   not permit PaperQA2 deferral. Never pass an absent-feature test vacuously.
4. Use §12.2 performance defaults. Keep correctness and race checks mandatory.
5. Retain the admitted Decision lock protocol. Narrowing it requires a separate
   reviewed contract and normal-role SQL race evidence.
6. Add no canonical schema. The first slice has no migration or query change.
   Measured nonredundant indexes or query refinements can be proposed for a later
   approved execution pack. Semantic changes require ADR/owning-PR review.
7. Use transactional maintenance for any later admitted index. Concurrent builds
   require explicit deployment need and nontransactional recovery tests.
8. Test populated frozen 0018 and every material accepted Phase 2 checkpoint.
   Invalid fixtures fail under the owning predicate. Never repair frozen history.
9. Repository license selection stays with the owner. Unknown permissions or
   security evidence remain unresolved and block affected activation/distribution.
10. Write the six §10 basenames under `docs/phase2/`. Write machine evidence under
    `pr_evidence/pr2-20/<subject_sha256>/`. An independent reviewer checks specs,
    diff and results. The owner accepts exit separately from scientific Approval.
11. Required correctness, security, migration or architecture skips cannot close
    exit. Optional deferral needs an explicitly permitted scope and owner record.
    Performance misses require visible disposition. No open P0/P1 permits success.

### 12.2 Benchmark defaults — owner-adjustable

These are engineering defaults, not new scientific limits. Record overrides in
`benchmark_profile.json` before collection. Compare only matching profiles.

| Setting | Concrete default |
| --- | --- |
| Host | Dedicated Linux x86-64 runner, Ubuntu 24.04, 4 reserved vCPUs, 16 GiB RAM, 100 GiB local SSD; DB and service on the same host; no competing job. Record CPU model, kernel and storage model. An unavailable matching host yields BLOCKED benchmark evidence. |
| Environment | Exact PostgreSQL 18 patch, Python and driver from the execution subject; `uv sync --locked --group dev`; record `uv.lock` digest. No guessed package patch pin. |
| DB settings | `shared_buffers=1GB`, `work_mem=16MB`, `max_connections=32`, `jit=off`, `track_io_timing=on`; retain durability defaults. Run `ANALYZE` after fixture generation. |
| Seed and source envelope | Seed `2202026`; 10 projects; 10,000 sources, 20,000 frozen SourceVersions, 20,000 identifiers, 11,000 project/source links. Exactly 1,000 sources are shared with a second project. 8,000 sources belong to the busiest project; distribute the rest across nine projects. |
| Scientific envelope | 1,000 complete valid Claim closures and 100 exact manuscript versions, including superseded history. Typical trace has 25 placements; high-fan-out has 250. Each placed Claim has 4 evidence edges; no truncation of the returned closure. Reuse legal upstream fixtures, not invalid copied history. |
| Governance envelope | 512 exact conclusion targets; 5,120 reviews and 51,200 initial OPEN Issues. Include one BLOCKING Issue amid favorable reviews, an empty basis, corrupt/invalid closure and unauthorized lookups in separate negative fixtures. Negative fixtures never count as successful first writes. |
| Sampling | Five warm-ups, then 100 calls **per worker per case**, at concurrency 1 and 4. Retain every sample. p95 is sorted sample at `ceil(0.95*n)-1`; p50 at `ceil(0.50*n)-1`, where `n` is the sample count. Use monotonic elapsed time. |
| Repeatability | Three independent repetitions using identical fixture profiles; reset an isolated database for each case/concurrency/repetition. Report per-repetition p50/p95/max; compare the median of the three p95 values. Each worker gets distinct first-write targets/IDs; same-ID contention is a separate race case. |
| Tolerance | Before/after p95 ratio must be ≤1.10 for each successful hot path; ingestion median time and index-size growth must be ≤1.10 when proposing an optimization. Correctness and query-count parity have zero tolerance. Relative spread `(largest p95-smallest p95)/median p95` >0.15 yields BLOCKED/noisy evidence and rerun, never PASS. |
| SHOULD targets | Successful identifier lookup p95 <100ms; typical trace p95 <2,000ms through the service boundary, including authorization/serialization and excluding external network. Record target misses independently of relative regression. High-fan-out/denial/race timings are separate rows. |
| Evidence | Save sanitized JSON plans, SQL digests, raw samples, row counts, query counts, buffers, locks and host profile. Warm runs are the gate; cold-cache experiments are informational and explicitly labelled. |

Generate all legal science through existing Application commands. Create TEST ONLY
identities through the existing disposable fixture setup. Measure fresh-first-write
using a new request and exact target for every call. The 512-target pool covers
the largest run: four workers × (5 warm-ups + 100 measured calls) = 420 targets.
Reserve at least 420 valid, independent, unblocked targets; negative cases use
the other targets and separate database resets. Replay uses the saved request
and result. Repeat with the same deterministic distribution; random request UUIDs
are recorded, not assumed reproducible bytes. A setup failure is BLOCKED.

### 12.3 File-only DTOs, limits and enums

Implement these closed, frozen dataclasses in the future
`tests/contracts/pr2_20_evidence.py`. They are test/report helpers, not public DTOs.
Reject unknown fields when parsing JSON. All fields are required unless their
Python type contains `None`; nullable fields must be emitted as JSON null.
Tuples serialize as arrays. UTC datetimes serialize as ISO 8601 with `Z`.

Common aliases: `Digest = str` matching `[0-9a-f]{64}`;
`Result = Literal['PASS','FAIL','BLOCKED','NOT RUN','DEFERRED']`;
`Mode = Literal['ENABLED','TEST_ONLY','METHOD_REFERENCE','DEFERRED']`.
`EvidenceRef = str` is a repository-relative path into the subject evidence directory.
No `..`, absolute path, URL credentials or secret query parameters are allowed.
These aliases are governed by Harness 09 §19 and this file-only draft convention.

Every record has `schema_version: Literal[1]`, `subject_revision: str`,
`dirty_diff_sha256: Digest`, `status: Result`, `reason: str | None`, and
`evidence_refs: tuple[EvidenceRef, ...]`. `reason` is required and nonblank for
FAIL, BLOCKED, NOT RUN and DEFERRED. PASS requires completed assertions.

| Record | Field names | Exact Python type |
| --- | --- | --- |
| `QueryPlanEvidence` | `case_id`, `service_method`, `repository_method`, `parameter_class` | `str` |
| `QueryPlanEvidence` | `sql_sha256` | `Digest` |
| `QueryPlanEvidence` | `profile_ref`, `sample_ref` | `EvidenceRef` |
| `QueryPlanEvidence` | `plan_refs` | `tuple[EvidenceRef, ...]` |
| `QueryPlanEvidence` | `index_definitions` | `tuple[str, ...]` |
| `QueryPlanEvidence` | `calls`, `warmups` | `int` |
| `QueryPlanEvidence` | `concurrency` | `Literal[1,4]` |
| `QueryPlanEvidence` | `p50_ms`, `p95_ms`, `max_ms`, `lock_wait_ms` | `float \| None` |
| `QueryPlanEvidence` | `buffer_hits`, `buffer_reads`, `query_count` | `int \| None` |
| `QueryPlanEvidence` | `correctness_equal` | `bool \| None` |
| `AdapterInventoryEntry` | `capability_id`, `adapter_id`, `mapping_version`, `upstream_source`, `owner` | `str` |
| `AdapterInventoryEntry` | `local_source_sha256` | `Digest` |
| `AdapterInventoryEntry` | `upstream_revision`, `package_version`, `api_profile`, `model_id`, `corpus_format` | `str \| None` |
| `AdapterInventoryEntry` | `index_format`, `material_provenance_path`, `reviewer` | `str \| None` |
| `AdapterInventoryEntry` | `lock_sha256`, `license_sha256` | `Digest \| None` |
| `AdapterInventoryEntry` | `mode` | `Mode` |
| `AdapterInventoryEntry` | `reviewed_at` | `datetime \| None` |
| `AdapterInventoryEntry` | `compatibility_nodes`, `unresolved_items` | `tuple[str, ...]` |
| `MigrationEvidence` | `start_revision`, `sqlstate`, `preflight_predicate` | `str \| None` |
| `MigrationEvidence` | `target_revision`, `postgres_version`, `server_identity` | `str` |
| `MigrationEvidence` | `script_refs` | `tuple[EvidenceRef, ...]` |
| `MigrationEvidence` | `fixture_class` | `Literal['EMPTY','LEGAL_POPULATED','INVALID_LEGACY','INTERRUPTED']` |
| `MigrationEvidence` | `commands` | `tuple[str, ...]` |
| `MigrationEvidence` | `exit_codes` | `tuple[int, ...]` |
| `MigrationEvidence` | `catalog_before_ref`, `catalog_after_ref`, `manifest_before_ref`, `manifest_after_ref` | `EvidenceRef \| None` |
| `MigrationEvidence` | `rollback_equal`, `history_equal` | `bool \| None` |
| `MigrationEvidence` | `downgrade_result`, `restored_read_result` | `Result` |
| `ExitCriterionEvidence` | `criterion` | `str` |
| `ExitCriterionEvidence` | `corrected_term`, `acceptance_revision` | `str \| None` |
| `ExitCriterionEvidence` | `owning_prs`, `contract_refs`, `test_nodes`, `commands` | `tuple[str, ...]` |
| `ExitCriterionEvidence` | `exit_codes` | `tuple[int, ...]` |
| `ExitCriterionEvidence` | `passed`, `failed`, `errors`, `skipped` | `int` |
| `ExitCriterionEvidence` | `finding_refs`, `disposition_refs` | `tuple[EvidenceRef, ...]` |
| `BenchmarkProfile` | `schema_version` | `Literal[1]` |
| `BenchmarkProfile` | `seed`, `vcpus`, `ram_gib`, `disk_gib`, `projects` | `int` |
| `BenchmarkProfile` | `sources`, `source_versions`, `identifiers`, `project_links`, `shared_sources` | `int` |
| `BenchmarkProfile` | `busy_project_sources`, `claims`, `manuscripts`, `typical_placements`, `high_placements` | `int` |
| `BenchmarkProfile` | `evidence_per_claim`, `conclusion_targets`, `reviews`, `issues`, `shared_buffers_mb` | `int` |
| `BenchmarkProfile` | `work_mem_mb`, `max_connections`, `warmups`, `calls_per_worker`, `repetitions` | `int` |
| `BenchmarkProfile` | `host_os`, `cpu_model`, `kernel`, `storage_model`, `postgres_version` | `str` |
| `BenchmarkProfile` | `python_version`, `driver_version` | `str` |
| `BenchmarkProfile` | `lock_sha256` | `Digest` |
| `BenchmarkProfile` | `jit`, `track_io_timing` | `bool` |
| `BenchmarkProfile` | `concurrency_profiles` | `tuple[Literal[1,4], ...]` |
| `BenchmarkProfile` | `regression_ratio`, `noise_spread` | `float` |
| `BenchmarkProfile` | `owner_override_ref` | `EvidenceRef \| None` |

Text fields: strict UTF-8, NFC, at most 16,000 characters; identifiers at most 128;
paths at most 1,024. Arrays: at most 10,000 entries per record. Each structured
file: at most 1 MiB. Split raw samples/plans into numbered files at that bound;
never truncate canonical results. Digests and resolved revisions are exact values,
not `latest`. Nonnegative counts/times; finite floats only. Commands and exit-code
arrays have equal lengths. Exit rows retain skipped counts; skips cannot be PASS.

Existing `RecordDecisionCommand` stays in `src/researchbase/application/decision.py`:
`id: UUID`, `project_id: UUID`, `scientific_conclusion_version_id: UUID`,
`question: str`, `rationale: str`, `decision_type: str='INTERNAL_SCIENTIFIC_RELEASE'`,
`decision: str='PROCEED'`. Both string enums accept only those exact values.
Question/rationale use strict UTF-8 NFC nonblank text; the existing command has
**no maximum length**. Do not impose a new public limit through these report limits.
Use 128-character benchmark text. The authenticated principal is server-supplied,
not a caller actor field. Readback is the unchanged `DecisionReadback` dataclass.

The raced review call uses `InternalReviewService.create` in
`src/researchbase/application/internal_review.py`: `principal: VerifiedPrincipal`,
`project: UUID`, `target_kind: str`, `target_id: UUID`, `review_type: str`,
`recommendation: str`, `summary: str`, `issues: tuple[ReviewIssueRequest, ...]`,
`request: UUID`. `ReviewIssueRequest` has `severity: str`, `issue_type: str`,
`description: str`. Maximum 100 Issues; summary/description are nonblank NFC,
strict UTF-8, maximum 16,000 characters. The first-slice race uses only
`target_kind='SCIENTIFIC_CONCLUSION_VERSION'`; the existing command also accepts
`CLAIM_VERSION`. Do not broaden to manuscript/artifact review.

Review enums are exactly: types SCIENTIFIC, STATISTICAL, LITERATURE,
REPRODUCIBILITY, EDITORIAL, COMPREHENSIVE; recommendations ACCEPT, MINOR_REVISION,
MAJOR_REVISION, REJECT, UNCERTAIN; severities INFO, MINOR, MAJOR, BLOCKING; issue
types UNSUPPORTED_CLAIM, CITATION, STATISTICAL, METHODOLOGICAL, REPRODUCIBILITY,
OVERCLAIM, CONTRADICTION, NOVELTY, WRITING, OTHER. Issue status remains OPEN.
Contribution roles and prepared-package enums are not used in this slice; their
missing accepted DTO/command contracts are listed in §13.5.

### 12.4 Error code → HTTP status / CLI exit

The following table pins **all existing enum mappings**, read from
[src/researchbase/api/errors.py](../../src/researchbase/api/errors.py) and
[src/researchbase/cli/errors.py](../../src/researchbase/cli/errors.py).
Hardening introduces no new Application code, so there is no proposed new-code
mapping in this slice.
The two review mappings remain provisional in their owning architecture question;
this draft preserves their current values and cannot approve that question.

| Existing error code | HTTP status | CLI exit |
| --- | --- | --- |
| `VALIDATION_ERROR` | 422 | 2 |
| `IDENTIFIER_INVALID` | 422 | 2 |
| `SEARCH_PLAN_QUESTION_REQUIRED` | 422 | 2 |
| `SEARCH_PLAN_LANGUAGE_SCOPE_REQUIRED` | 422 | 2 |
| `SEARCH_PLAN_QUESTION_INVALID` | 422 | 2 |
| `NOT_FOUND` | 404 | 3 |
| `SOURCE_NOT_FOUND` | 404 | 3 |
| `SOURCE_MERGE_PROPOSAL_NOT_FOUND` | 404 | 3 |
| `SOURCE_VERSION_NOT_FOUND` | 404 | 3 |
| `AUTHENTICATION_REQUIRED` | 401 | 3 |
| `FORBIDDEN` | 403 | 3 |
| `CONFLICT_OF_INTEREST` | 403 | 3 |
| `SUBJECT_BINDING_UNPROVEN` | 403 | 3 |
| `SOURCE_MERGE_APPROVAL_FORBIDDEN` | 403 | 3 |
| `SEARCH_PLAN_QUESTION_SCOPE_MISMATCH` | 403 | 3 |
| `REVIEW_TARGET_NOT_FROZEN` | 409 | 4 |
| `INVALID_STATE_TRANSITION` | 409 | 4 |
| `VERSION_NOT_FROZEN` | 409 | 4 |
| `IMMUTABLE_RECORD` | 409 | 4 |
| `CONCURRENT_MODIFICATION` | 409 | 4 |
| `DUPLICATE_CONTENT` | 409 | 4 |
| `SUBJECT_ALREADY_BOUND` | 409 | 4 |
| `OWNER_COVERAGE_GAP` | 409 | 4 |
| `OWNER_CREDENTIAL_UNAVAILABLE` | 409 | 4 |
| `ENROLLMENT_CHALLENGE_EXPIRED` | 409 | 4 |
| `BOOTSTRAP_CLOSED` | 409 | 4 |
| `IDEMPOTENCY_CONFLICT` | 409 | 4 |
| `LEGACY_STATE_INVALID` | 409 | 4 |
| `SOURCE_IDENTITY_CONFLICT` | 409 | 4 |
| `IDENTIFIER_ALREADY_BOUND` | 409 | 4 |
| `IDENTIFIER_BASIS_NOT_FROZEN` | 409 | 4 |
| `SHARED_SOURCE_REJECTION_REQUIRES_REVIEW` | 409 | 4 |
| `SOURCE_MERGE_PROPOSAL_STALE` | 409 | 4 |
| `SOURCE_MERGE_APPROVAL_MISSING` | 409 | 4 |
| `SOURCE_MERGE_REJECTED` | 409 | 4 |
| `SOURCE_MERGE_PROPOSAL_ALREADY_CONSUMED` | 409 | 4 |
| `SOURCE_MERGE_BASIS_CONFLICT` | 409 | 4 |
| `SOURCE_NOT_MERGEABLE` | 409 | 4 |
| `SOURCE_MERGE_IDENTIFIER_CONFLICT` | 409 | 4 |
| `SOURCE_VERSION_NOT_FREEZABLE` | 409 | 4 |
| `SOURCE_VERSION_ALREADY_FROZEN` | 409 | 4 |
| `SOURCE_VERSION_IMMUTABLE` | 409 | 4 |
| `INVALID_SOURCE_VERSION_LINEAGE` | 409 | 4 |
| `SEARCH_PLAN_VERSION_IMMUTABLE` | 409 | 4 |
| `SEARCH_PLAN_NOT_FROZEN` | 409 | 4 |
| `ADAPTER_VERSION_MISMATCH` | 409 | 4 |
| `FROZEN_REFERENCE_REQUIRED` | 409 | 5 |
| `REFERENTIAL_INTEGRITY_ERROR` | 409 | 5 |
| `PROVENANCE_CLOSURE_VIOLATION` | 409 | 5 |
| `ADAPTER_UNAVAILABLE` | 503 | 5 |

HTTP-only `INTERNAL_ERROR` is the existing sanitized unexpected-exception response
(500); it is not an ErrorCode or a new CLI code. Report-tool exits are proposed
local conventions: 0 for completed passing checks, 1 for failed assertions, 2 for
invalid report/profile input, 3 for unavailable prerequisite/environment. They
are not Application transport mappings. Preserve owning migration SQLSTATE/messages.

## 13. Implementation guide

This guide becomes executable only after owner approval and a separate execution
pack. The first slice builds report helpers, fixtures and tests against existing
commands. It produces an incomplete exit report when dependencies are missing.
It does not implement those dependencies, change queries or install indexes.

### 13.1 Exact DDL sketch and catalog assertions

**First-slice DDL is empty.** New tables, columns, constraints, indexes and Alembic
revisions: none. NULL/NOT NULL and new enum decisions: not applicable. Do not create
an evidence table; §12.3 records are files. Catalog assertions use the accepted
migrations, not a reconstructed replacement schema.

The only concrete index candidate in this draft is below. It is **not in this
slice**: an accepted Issue-disposition contract and measured benefit are required.
These are the exact existing columns relevant to its predicate, from
`migrations/versions/0040_pr2_14_initial_internal_review.py`:

| Table.column | SQL type | Nullability | Existing constraint/index names |
| --- | --- | --- | --- |
| `review_issues.id` | UUID | NOT NULL | `review_issues_pkey` |
| `review_issues.review_record_id` | UUID | NOT NULL | `review_issues_review_record_id_fkey`, references `internal_review_records(id) ON DELETE RESTRICT`; `review_issues_review_record_id_ordinal_key`; `ix_pr214_issue_review_severity` |
| `review_issues.severity` | VARCHAR(16) | NOT NULL | `review_issues_severity_check`, values INFO/MINOR/MAJOR/BLOCKING; `ix_pr214_issue_review_severity` |
| `review_issues.status` | VARCHAR(16) | NOT NULL | `review_issues_status_check`, currently exactly OPEN |
| `review_issues.ordinal` | INTEGER | NOT NULL | `review_issues_ordinal_check`, `ordinal>=0`; `review_issues_review_record_id_ordinal_key` |

Constraint names above are PostgreSQL's names for the unnamed constraints in
0040. Assert the live catalog matches. The future disposition contract must own
any change to `review_issues_status_check`; PR2-20 must not relax it.

```sql
-- Candidate only, after prerequisite admission and measurement.
-- No table/column/constraint change. B-tree, nonunique, transactional.
CREATE INDEX ix_pr220_issue_open_blocking_review
    ON review_issues USING btree (review_record_id)
    WHERE status = 'OPEN' AND severity = 'BLOCKING';
-- Reversal, only if this candidate was admitted and installed:
DROP INDEX ix_pr220_issue_open_blocking_review;
```

Preserve `ix_pr214_issue_review_severity` on `(review_record_id,severity)` and all
existing FK, trigger and immutable-history rules. The candidate may prove redundant;
record rejection instead of installing it. A future approved migration belongs in
`migrations/versions/<assigned_revision>_pr2_20_measured_indexes.py`, after the then
accepted head. The execution pack must assign the exact revision/predecessor;
this slice deliberately creates no such file. No concurrent build is the default.

### 13.2 Ordered build steps and ownership paths

1. Add `tests/contracts/pr2_20_evidence.py` with §12.3 dataclasses, bounded JSON
   readers/writers and manifest digests. Add the corresponding unit tests first.
2. Add `tests/integration/phase2/pr2_20_support.py`. Reuse
   `phase2_database_url` / `conclusion_env` from
   `tests/integration/phase2/test_pr2_11_r2_persistence.py`, `_draft` from
   `tests/integration/phase2/test_pr2_13_claim_placement.py`, `decision_env` from
   `tests/integration/phase2/test_pr2_15_decision.py`, and `_authorized_service`
   from `tests/integration/phase2/test_pr2_01_source_identity.py`. Refactor shared
   fixture helpers only if required; preserve their identity check and cleanup.
   Use `tests/disposable_postgres.py`; never retained DBs or trigger bypass.
3. Build deterministic small correctness fixtures, then the §12.2 scaled fixtures.
   Save actual counts and canonical hash/ID/edge manifests. Assert counts before
   measuring. Set up corpus/network fakes outside transaction timing. The busiest
   project and shared-source denial cases must both be present.
4. Add the PostgreSQL tests in §13.4. Capture emitted SQL with SQLAlchemy events
   in the test helper. Time authorized services, not raw substitute queries.
   Keep existing production boundaries: Application `internal_review.py`,
   `decision.py`, `manuscript_scientific_trace.py`, `source_identity.py` →
   `application/ports.py` → persistence repositories and `persistence/uow.py`.
   No new domain, API or CLI hardening module is needed.
5. Add `tests/e2e/test_pr2_20_benchmark.py`, using the same support helper. Make
   the large profile opt-in via `RB_PR220_BENCHMARK=1`; ordinary CI runs small
   parity/query-count cases. Skipped large-profile tests are NOT RUN benchmark
   evidence. Use `benchmark_profile.json`, `samples-<case>-<repeat>.json`, and
   `plans-<case>-<repeat>.json` under the subject directory; split at 1 MiB.
6. Collect migration digests/catalogs, adapter versions and license/security
   sources. Use the inventory tests in §13.4; do not update runtime dependencies,
   enable providers or claim live PaperQA2 evidence from a fake.
7. Generate all six §10 Markdown artifacts from the typed evidence. Retain all
   19 exit rows and 13 architecture mappings. Fill missing prerequisites with
   BLOCKED, not empty PASS rows. Check documentation commands and local links.
8. Run the future authorized checks: `uv sync --locked --group dev`,
   `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`,
   `uv run alembic heads`, `uv run pytest tests/unit tests/architecture`, and
   `uv run pytest tests/integration tests/e2e` against fixture-owned PostgreSQL 18.
   Set `RB_TEST_ADMIN_URL` using the permitted disposable host and existing
   fixture policy. Never put credentials in evidence command strings.
   Run the declared benchmark separately with
   `RB_PR220_BENCHMARK=1 uv run pytest tests/e2e/test_pr2_20_benchmark.py`.
9. Review specifications + diff + results independently. Resolve open P0/P1.
   Attach owner dispositions and produce exit evidence. STOP before Phase 3.

No PostgreSQL acceptance is claimed by writing this guide. Future migrations
require `alembic upgrade head` on each fixture database, catalog assertions and
restart readback; a graph-only `heads` command is insufficient.

### 13.3 Exact lock order per exercised command/query

The test helper adds **no locks** around service calls. It observes the existing
protocol, including nested repository calls and trigger locks. The following is
statement order, not a promise about internal tuple order within a joined SQL
statement. Commands not listed here are outside the first-slice benchmark.
Fixture generation invokes their existing owning services unchanged.

Define `AUTH(project)` as this exact sequence from
`persistence/literature_search_plan_repository.py`: call
`rb_phase2_lock_project(project)` → project row `FOR UPDATE` → matching
actors/memberships/role assignments/subject bindings `FOR UPDATE OF a,m,r,b`
with `ORDER BY a.id,m.id,r.id,b.id` → use durably reread authorization material → fresh
`clock_timestamp()` → live credential/effective-role check. Repeating AUTH
reuses transaction locks and refreshes the time/check. Do not cache the check.

| Exercised boundary | Exact sequence to retain |
| --- | --- |
| `SourceIdentityService.find_source_by_identifier` | Begin SERIALIZABLE → project advisory `researchbase-project:<project>` → project row UPDATE → receipt advisory `literature-receipt:<deployment>:<project>:<actor>:READ_SOURCE:<request>` → durable authorization reread and fresh DB time → exact normalized identifier/project-link SELECT → commit. This read has no identifier/source row lock. The current read method has no automatic retry wrapper; the harness records any conflict, never retries a write disguised as a read. |
| `ManuscriptScientificTraceService.trace` | Set REPEATABLE READ before reads → AUTH(project) → exact publication/version reads → placements → conclusion Claim inputs → experimental paths → literature paths. No target UPDATE lock is added. Preserve the stable snapshot and current inherited authorization protocol. Return unchanged typed trace; end UoW without a canonical write. |
| `DecisionService.record_decision`, new and replay | Set local lock timeout 10s and statement timeout 30s → advisory `pr215:decision:<id>` → exact conclusion-version UPDATE → sorted table SHARE inventory below → AUTH(project) → existing-request check. First-write continues AUTH(writer) → closure traversal → material-author read → matching reviews ordered by ID `FOR SHARE` → blocker/scope checks → AUTH(writer) → Decision and typed-basis INSERTs → saved readback verification → AUTH(writer) → commit. Replay instead verifies saved basis/hash/caller material, then AUTH(reader), returns original readback without re-execution. |
| `InternalReviewService.create`, conclusion race | Derive review ID by existing UUID5 deployment/project/actor/request rule → advisory `pr214:review:<derived_id>` → exact conclusion-version UPDATE → conclusion parent UPDATE → AUTH(project) → closure traversal → AUTH(project) → replay check or review INSERT → initial Issue INSERTs in ordinal order → readback → commit. The review INSERT trigger reacquires exact target UPDATE then parent SHARE; each Issue trigger acquires exact target UPDATE then review SHARE before Issue/event writes. Zero-Issue review INSERT still coordinates on exact target. |
| Normal-role SQL Issue INSERT race | Discover immutable review target ID without locking → exact conclusion-version UPDATE → fresh statement rereads review `FOR SHARE` → reference/project checks → Issue INSERT → initial event INSERT. This is a trigger path, not a public command or a test-helper canonical write bypass. Use only disposable race fixtures. |
| Catalog/EXPLAIN/report collection | Independent read-only observer connection; PostgreSQL's implicit ACCESS SHARE for SELECT. No Application locks are acquired in advance. Run EXPLAIN ANALYZE only on actual captured read SQL in disposable fixtures; no mutating SQL is analyzed. |

Closure traversal in Decision and conclusion-review calls is the unchanged
`ScientificConclusionService._view`: exact parent/version reads → Claim inputs
by saved ordinal → each `claim_reference` query `FOR UPDATE OF v,c` in
`scientific_conclusion_repository.py` → exact Claim target query `FOR UPDATE OF p,v`
in `literature_evidence_repository.py` → optional support snapshot checks → direct
literature inputs by saved ordinal. Snapshot verification reacquires its exact
target, recursively verifies predecessor snapshots first, then reads relations by
`ordinal,literature_evidence_id`. Each evidence check takes evidence row UPDATE →
exact SourceVersion UPDATE → owning LiteratureSource UPDATE → artifact/locator and
review-event reads. Repeated readback
reacquires the same locks. Preserve saved ordinals; do not add an independent
sorted-lock prepass or substitute latest versions. Database FK/INSERT locks and
0041/0042 triggers remain active in addition to the explicit list.

Decision's SHARE inventory is exactly the following alphabetical list from
`persistence/decision_repository.py`, acquired in one `LOCK TABLE ... IN SHARE MODE`:

```text
actor_subject_bindings
actors
artifact_versions
artifacts
audit_findings
claim_versions
claims
correction_records
datasets
experiment_spec_versions
experiment_specs
impact_assessments
impact_targets
literature_evidence
literature_evidence_review_events
literature_source_project_links
literature_sources
metric_definition_versions
metric_definitions
project_membership_events
project_memberships
project_role_assignments
projects
runs
scientific_conclusions
source_versions
```

Decision retries CONCURRENT_MODIFICATION at most three total attempts with a fresh
UoW, preserving request identity. Its normalization treats deadlock/serialization
failures as retryable, not every timeout. Review `create` has no automatic three-
attempt wrapper in this baseline. Preserve that difference; report failures.
New hardening helpers cannot silently add a retry policy to an owning command.
Replay rules in §7 apply to accepted future contracts, not a rewrite of the
existing review replay implementation. Missing future lock orders stay blocked.

### 13.4 Exact test files and required cases

These files are future additions. Their tests must assert outcomes and persisted
state, not only exercise a method. Small fixtures run in normal CI; large timings
run on the declared host. PostgreSQL suites never fall back to SQLite.

| Create file | Required cases and fixture source |
| --- | --- |
| `tests/unit/phase2/test_pr2_20_evidence.py` | All five closed layouts round-trip; unknown fields; invalid enums/digests/NFC/UTF-8; 1 MiB/array/path bounds; nonfinite/negative times; missing non-PASS reason; inconsistent counts/exit-code arrays; secret redaction. Verify every ErrorCode mapping in §12.4 against API/CLI source and keep HTTP-only INTERNAL_ERROR separate. |
| `tests/integration/phase2/test_pr2_20_catalog_plans.py` | Reuse `conclusion_env` and `_draft`; assert accepted catalog/index coverage and no duplicate index proposals; exact trace and source lookup IDs/denials before/after read instrumentation; 25/250-placement query-count scaling; one blocker among many favorable reviews; record full buffers/plans without asserting exact planner text. Assert no first-slice DDL. |
| `tests/integration/phase2/test_pr2_20_governance_races.py` | Reuse `decision_env` and `_wait_for_pg_blocker` from `test_pr2_14_internal_review.py`; both commit orders for review/Issue INSERT and Decision; zero-Issue coordination; witnessed post-lock credential/role expiry and source impact; concurrent identical request and changed-material conflict; complete saved basis; full rollback; same historical replay after current validity changes, with current read authority; denied replay disclosure. Reuse original PR2-15 tests where they already prove a case and link their exact nodes. |
| `tests/integration/phase2/test_pr2_20_migrations.py` | Use disposable PG helper plus owning fixtures: empty upgrade/no-op; populated legal 0018; accepted source/search/evidence, conclusion/placement, review and 0042 checkpoints; owning illegal-legacy preflight; interrupted transactional rollback; digest/catalog/hash/edge parity; reconnect reads; permitted empty round trip; populated downgrade refusal. Future checkpoints get BLOCKED report rows until accepted fixtures exist, never skip-to-PASS. |
| `tests/unit/phase2/test_pr2_20_inventory.py` | Resolve actual source/uv lock identities; enabled/test/reference/deferred modes; unversioned hosted API labelled explicitly; reference-only entries never executable pins; fake never real PaperQA2 acceptance; missing license/advisory evidence unresolved; replacement candidate contract and byte-for-byte canonical nonmutation using existing offline adapters. |
| `tests/integration/phase2/test_pr2_20_security.py` | Reuse TEST ONLY projects and adapter fixtures; credential/query secret redaction; untrusted tool text cannot promote or elevate; cross-project/global-source nondisclosure; enabled retrieval private-network/redirect/size/time/parser protections; corpus isolation and unsafe index deserialization denial where enabled. Missing protection is a finding; absent PaperQA2 cases are BLOCKED prerequisites. |
| `tests/architecture/test_pr2_20_boundaries.py` | Map all §9.1 names to concrete collected tests; check strategy/adapter imports, canonical catalog ownership and report-only helpers; no ORM DTO or Harness direct write; no new public command or scientific schema; mandatory missing implementation reported BLOCKED. Runtime Approval denial remains blocked until its owning implementation exists. |
| `tests/e2e/test_pr2_20_benchmark.py` | Exact §12.2 counts/distribution/profile; 1/4 worker sampling and three repetitions; hit/miss/denied lookup, typical/high trace, complete review gate, Decision first-write/replay; nearest-rank percentile; zero-tolerance DTO/query-count parity; 10% regression and 15% noise classification; external latency separate; no favorable-subset/truncated closure. |
| `tests/unit/phase2/test_pr2_20_exit_report.py` | Six basenames; 19 literal criteria and 13 architecture mappings; exact subject/diff; referenced collected node/command/log exists; pass/fail/error/skip counts remain distinct; fake/optional/deferred cannot satisfy mandatory row; open P0/P1 blocks exit; STOP text and local links. |

Also retain and run the existing PR2-01 identity, PR2-13 trace, PR2-14 review,
PR2-15 coordination/Decision/schema suites and full Phase 1 golden regression.
Use `tests/integration/phase2/test_pr2_12_migration.py` as a migration-fixture
pattern, not as proof that every populated 0018 state is legal. Owning accepted
preflight predicates control the fixture matrix.

### 13.5 Not in this slice

| Deferred build artifact/path | Missing prerequisite contract or evidence |
| --- | --- |
| Partial blocker-index migration | Accepted Issue-disposition command/status transitions and populated cardinality evidence; current 0040 enforces all OPEN. Measurement and owner admission must precede the DDL in §13.1. |
| RevisionAction first-write/replay/correction races | Accepted and implemented PR2-15 RevisionAction contract, exact seven result DTO shapes and lock protocol; minimal Decision S1 is insufficient. |
| Issue resolution, dismissal and re-review workflow | Separate Issue-disposition contract binding Decision, completed revision and new review; no mutation authorized by a hardening report. |
| Basic Approval request/decision/grant benchmark | Accepted and implemented PR2-16 purpose/target/command tuple, DTO limits, independence, replay and exact locks. No invented mappings/enums here. |
| Grant consumption and package-to-grant resolver | Separately accepted consumption effect/receipt contract and exact package/grant resolver; creating a grant is not consuming it. |
| Manuscript freeze | Exact frozen ManuscriptVersion material/hash/closure and immutability contract. |
| Manuscript READY transition | Separate deterministic readiness guards and lifecycle command contract. |
| Manuscript review | Exact frozen-target scientific validation and review command admission; current command accepts Claim/conclusion only. |
| READY_FOR_SUBMISSION Decision | Separately admitted Decision purpose, complete basis, blockers and locks. |
| PREPARE_SUBMISSION Decision/command tuple | Separately admitted purpose/target/command authorization tuple and grant-consuming command. |
| Prepared-package/authorship/consent tests and freeze benchmark | Accepted PR2-17 preparation slice with exact fields/roles/limits; package freeze also needs all preceding manuscript/governance prerequisites. Preparation and external submission remain distinct. |
| Prior-art/novelty benchmark and phantoms | Accepted PR2-18 coverage snapshot, INCONCLUSIVE-only guard, DTO/limits and SERIALIZABLE retry contract. No conclusive novelty inference is added here. |
| Full PR2-19 golden/failure matrix | Accepted row-to-contract/test-fixture matrix, including blockers above; hardening reports blocked rows until executable owning cases exist. |
| Real PaperQA2 compatibility/security and full exit row | Selected, pinned, licensed PR2-07 adapter/intake, exact corpus/index/candidate boundary and real acceptance fixtures. Offline fake compatibility is insufficient. |
| Other Approval purposes, consuming effects, external submission | Separately authorized owning contracts; no Phase 3 implementation or ExternalEffect inferred from hardening. |

When a dependency lands, update the execution pack's exact subject, DTO inventory,
lock sequences, mapping table and tests before adding that boundary to this slice.
Do not ask a mid-level implementer to invent the missing contract.

Documentation change only; verification is limited to local link and format checks.
These checks are not implementation, PostgreSQL acceptance or a Phase 2 exit gate.

## 14. Dependencies and owner override points

Dependencies are contract and acceptance subjects, not merely files in Git:
frozen `phase1-final-v4` baseline and accepted Phase 2 entry/migration policy;
PR2-00–06 source/search/evidence/access; PR2-07 real PaperQA2 selection and intake;
PR2-08 native strategy (PR2-09 only under its explicit optional exception);
PR2-10–13 discussion/conclusion/manuscript/trace; PR2-14 review; approved PR2-15
RevisionAction and PR2-16 Basic Approval; PR2-17 prepared package/authorship/consent;
PR2-18 prior-art/novelty; PR2-19 full golden/failure injection. The base drafts'
unavailable Issue disposition, revision-purpose Decisions, other Approval purposes
and consuming effects must be assigned and separately authorized before any exit
criterion needing them can close. Hardening owns measurement and evidence, not
those missing scientific/governance commands.

| Owner override point (already decided in §12) | Draft decision; owner may overrule |
| --- | --- |
| Which subject constitutes full Phase 2 exit while PR2-15/16 are in progress? | Freeze approved contract subjects and final implemented revisions; require owning acceptance evidence. A bounded slice is not full Phase 2 exit. Produce BLOCKED report if any mandatory path is missing. |
| How should the 2026-10-14 approved bases' DRAFT headings/open questions be reconciled? | Attach the owner's exact approval/dispositions at execution freeze; preserve their precedence and return ambiguities to their owning contracts. Do not edit those base files in this task. |
| May PR2-20 implement missing PaperQA2, Issue disposition or grant/package effects? | No. Assign separately authorized prerequisite work; no PaperQA2 deferral inferred from optional STORM language. No absent-feature vacuous tests. |
| Which performance envelope, reference host and regression tolerance are binding? | Use the concrete owner-adjustable defaults in §12.2, the §5.1 protocol and 05 SHOULD targets with explicit miss disposition. Correctness/race gates stay mandatory. |
| Can coarse Decision locks be narrowed for throughput? | Retain the admitted protocol. Alternative protection needs separate contract review and witnessed normal-role SQL phantom/temporal/rollback evidence before implementation. |
| What schema/index changes may PR2-20 make later? | No new canonical schema. Only measured nonredundant additive indexes/query refinements under an approved execution pack; semantic or authority changes go through ADR/owning PR. |
| Should concurrent indexes be the default? | No. Bounded transactional maintenance is simpler for Phase 2. Approve nontransactional concurrent build only with deployment need and failure/recovery tests. |
| Which populated upgrade starting points and legacy policies are supported? | Require frozen 0018 and every material accepted Phase 2 checkpoint with contract-legal populated fixtures; invalid fixtures fail under their owning predicate without repair of history. |
| What repository license, upstream permissions or advisory uncertainty may be treated as cleared? | Owner selects repository license separately. Require authoritative resolved-revision evidence; unknown permission/security evidence remains unresolved and blocks affected activation/distribution. No inferred license grant or blanket “secure” claim. |
| Where should final artifacts live and who signs exit? | Use `docs/phase2/` for the six specified basenames, linked immutable machine evidence by subject; independent reviewer checks spec/diff/results and owner explicitly accepts exit. Reports are engineering evidence, not Approval commands. |
| Can skipped/blocked tests or performance exceptions close exit? | Required correctness/security/migration/architecture skips cannot. Optional deferrals need explicit permitted scope and owner record; target misses need visible disposition, with no open P0/P1. |

Until this plan is approved and separately authorized, it stays DRAFT and grants
no implementation, migration, provider activation or Phase 2/3 gate authority.
