# PR2-20 Hardening Plan — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

**Scope:** documentation proposal only. This file is not an architecture freeze,
ADR, execution pack, migration authorization, security certification, scientific
approval or Phase 2 exit declaration. Owner approval of this plan must precede a
separate implementation authorization. Only this proposal is changed by this task.

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
| [PR2-15 RevisionAction base](PR2-15_RevisionAction_Contract_DRAFT.md) and [PR2-16 Basic Approval base](PR2-16_Basic_Approval_Contract_DRAFT.md) | Owner approved both on **2026-10-14**, per this task; implementation is in progress. Their completed-action, exact-target, replay, blocking-gate and bounded-slice choices are the base, not gaps for PR2-20 to redesign. |

The base files retain DRAFT headings and unresolved questions. The approval date
above is supplied by the owner/task, not inferred from those headings or this
checkout's verification date. Approval does not prove implementation or whole-PR
acceptance. At execution freeze, attach the approved subject/revision and owner
dispositions; if implemented contracts differ, record the discrepancy and return
it to the owning PR. PR2-20 must not silently settle a base's open policy question.

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

Do not freeze a new command field here. At execution, record exact DTO contract
revision, normalization, accepted/unknown fields, stable error/transport mapping
and fixtures for each exercised boundary. An optimization must produce the same
material result and denial behavior as its pre-change reference.

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
   100 measured calls per case on the declared reference host, fixed concurrency
   profiles 1 and 4, p50/p95/max and full sample references. Host noise/variance
   means rerun or BLOCKED, not an invented pass. Owner must approve fixture size,
   host and tolerance before implementation; no absolute latency claim without
   the data envelope. Keep deterministic plan/correctness checks in ordinary CI;
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
The owner may select the evidence directory in the execution pack; these files
are future deliverables and are not created by this documentation task.

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

## 11. Dependencies and open owner questions

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

| Owner question | Recommended conservative answer |
| --- | --- |
| Which subject constitutes full Phase 2 exit while PR2-15/16 are in progress? | Freeze approved contract subjects and final implemented revisions; require owning acceptance evidence. A bounded slice is not full Phase 2 exit. Produce BLOCKED report if any mandatory path is missing. |
| How should the 2026-10-14 approved bases' DRAFT headings/open questions be reconciled? | Attach the owner's exact approval/dispositions at execution freeze; preserve their precedence and return ambiguities to their owning contracts. Do not edit those base files in this task. |
| May PR2-20 implement missing PaperQA2, Issue disposition or grant/package effects? | No. Assign separately authorized prerequisite work; no PaperQA2 deferral inferred from optional STORM language. No absent-feature vacuous tests. |
| Which performance envelope, reference host and regression tolerance are binding? | Approve seeded representative row counts/skew/fan-out and host before measurement; use the §5.1 protocol and 05 SHOULD targets with explicit miss disposition. Correctness/race gates stay mandatory. |
| Can coarse Decision locks be narrowed for throughput? | Retain the admitted protocol. Alternative protection needs separate contract review and witnessed normal-role SQL phantom/temporal/rollback evidence before implementation. |
| What schema/index changes may PR2-20 make later? | No new canonical schema. Only measured nonredundant additive indexes/query refinements under an approved execution pack; semantic or authority changes go through ADR/owning PR. |
| Should concurrent indexes be the default? | No. Bounded transactional maintenance is simpler for Phase 2. Approve nontransactional concurrent build only with deployment need and failure/recovery tests. |
| Which populated upgrade starting points and legacy policies are supported? | Require frozen 0018 and every material accepted Phase 2 checkpoint with contract-legal populated fixtures; invalid fixtures fail under their owning predicate without repair of history. |
| What repository license, upstream permissions or advisory uncertainty may be treated as cleared? | Owner selects repository license separately. Require authoritative resolved-revision evidence; unknown permission/security evidence remains unresolved and blocks affected activation/distribution. No inferred license grant or blanket “secure” claim. |
| Where should final artifacts live and who signs exit? | Use `docs/phase2/` for the six specified basenames, linked immutable machine evidence by subject; independent reviewer checks spec/diff/results and owner explicitly accepts exit. Reports are engineering evidence, not Approval commands. |
| Can skipped/blocked tests or performance exceptions close exit? | Required correctness/security/migration/architecture skips cannot. Optional deferrals need explicit permitted scope and owner record; target misses need visible disposition, with no open P0/P1. |

Until this plan is approved and separately authorized, it stays DRAFT and grants
no implementation, migration, provider activation or Phase 2/3 gate authority.

## 12. Documentation-task verification — 2026-10-13

Only this proposal is added to the tracked-file change set; no branch, commit or
push was created. These are draft/baseline checks, **not PR2-20 implementation or
Phase 2 exit acceptance**. Logs and PostgreSQL scratch are under ignored
`tmp/pr2-20-verification/`. Test imports use `PYTHONPATH=src` to select this checkout.

Environment setup attempts:

```bash
uv sync --locked --group dev
UV_CACHE_DIR=/private/tmp/researchbase-lane2-uv-cache uv sync --locked --group dev
```

Both exit 2. The first cannot open the default uv cache under sandbox permissions;
the second cannot download locked `iniconfig==2.3.0` because DNS/network access
fails. Locked sync is **BLOCKED**, not PASS. The existing parent repository Python
3.12.15 environment supplies installed pytest 8.4.2 and check tools; it is not
claimed as a newly synchronized environment. To resolve local Pyright's missing
imports during the static-test rerun, installed site-packages were copied read-only
from that environment into this checkout's ignored `.venv`:

```bash
cp -R /Users/fengwang/Documents/ResearchBaseProject/.venv/lib/python3.12/site-packages/. .venv/lib/python3.12/site-packages/
```

Baseline checks, exact commands:

```bash
PYTHONPATH=src /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python -m pytest -o addopts='' -ra --tb=short tests/unit tests/architecture > tmp/pr2-20-verification/unit-architecture.log 2>&1
/Users/fengwang/Documents/ResearchBaseProject/.venv/bin/ruff check .
/Users/fengwang/Documents/ResearchBaseProject/.venv/bin/ruff format --check .
/Users/fengwang/Documents/ResearchBaseProject/.venv/bin/pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject > tmp/pr2-20-verification/pyright.log 2>&1
PYTHONPATH=src /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python -m pytest -o addopts='' -ra --tb=short tests/unit/phase2/test_pr2_04_static_acceptance.py > tmp/pr2-20-verification/static-rerun.log 2>&1
/Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python -m alembic heads
git diff --check
git diff --exit-code -- src migrations tests docs/architecture pyproject.toml uv.lock README.md .github harness.lock.yaml
```

| Check | Exact result |
| --- | --- |
| Unit + architecture selection | Exit 1: **1820 passed, 5 failed, 0 skipped**, 2 warnings, 31.53s. Four `test_hg1_runner.py` failures occur on sandbox-denied Unix socket bind. Static acceptance initially fails because the incomplete local `.venv` prevents Pyright import resolution. |
| Static acceptance rerun after environment correction | Exit 1: **0 passed, 1 failed, 0 skipped**, 4.60s. Now reaches the inherited-baseline whitespace assertion: `docs/verification/task9/pyright.txt:4: new blank line at EOF` against baseline `b8179f17720ca47c3b25ad9d36f6a8e8d4aa79ff`. That committed file is unchanged by this task; no out-of-scope repair was made. |
| Ruff lint / format | Both exit 0: **All checks passed**; **456 files already formatted**. |
| Pyright with existing environment selector | Exit 0: **0 errors, 0 warnings, 0 informations**. |
| Alembic graph inspection | Exit 0: exactly **0042_pr2_15_minimal_decision (head)**. This is static graph evidence, not clean-install success. |
| Current diff whitespace and protected paths | Both exit 0; no tracked changes outside this proposal. Explicit document checks below also cover the untracked new file. |

PostgreSQL initialization and selected baseline migration/trace/governance suites:

```bash
mkdir -p tmp/pr2-20-verification/pgsocket
/opt/homebrew/opt/postgresql@18/bin/initdb -D tmp/pr2-20-verification/pgdata -U pr220_admin -A trust --no-locale
PYTHONPATH=src RB_TEST_ADMIN_URL=postgresql+psycopg://pr220_admin@127.0.0.1:55479/postgres DATABASE_URL=postgresql+psycopg://pr220_admin@127.0.0.1:55479/researchbase /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python -m pytest -o addopts='' -ra --tb=short tests/integration/phase2/test_pr2_12_migration.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_14_internal_review.py tests/integration/phase2/test_pr2_14_conclusion_review.py tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_15_decision_schema.py > tmp/pr2-20-verification/integration.log 2>&1
```

initdb exits 1: `could not create shared memory segment: Operation not permitted`
at `shmget`; it removes the incomplete cluster. No server starts. Pytest exits 1:
**0 passed, 2 failed, 60 setup errors, 0 skipped**, 6.05s. Both migration failures
and all setup errors are connection failures (`Operation not permitted`) before
database assertions. **PostgreSQL verification is BLOCKED, not PASS**; no clean
install, upgrade, constraint, trace or governance acceptance is claimed. No retained
or production DB was modified. The same selected suites need a permitted disposable
PostgreSQL 18.x environment. Broader scientific integration suites were not run:
this non-authoritative Markdown proposal changes no executable/schema/contract
behavior. All future acceptance in §§8–10 remains planned and NOT RUN.

Exact document/content/scope check, rerun after this evidence section:

```bash
PYTHONPATH=src /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python - <<'PY'
from pathlib import Path
import re
import subprocess

p = Path('docs/proposals/PR2-20_Hardening_Plan_DRAFT.md')
s = p.read_text()
links = re.findall(r'\]\(([^)]+)\)', s)
assert all((p.parent / target).is_file() for target in links)
assert '**Status: DRAFT — awaiting owner approval; not authorized for implementation**' in s
assert all(line == line.rstrip() for line in s.splitlines())
changes = subprocess.check_output(['git', 'status', '--short'], text=True).splitlines()
assert changes == [f'?? {p.as_posix()}'], changes
spec = Path('docs/architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md').read_text()
architecture = spec.split('# 49. Architecture Tests')[1].split('# 50.')[0]
names = re.findall(r'^test_\w+', architecture, re.MULTILINE)
assert len(names) == 13 and all(f'`{name}`' in s for name in names)
exit_block = spec.split('# 52. Phase 2 Exit Criteria')[1].split('Phase 2 exit artifacts')[0]
criteria = re.findall(r'^\[ \] (.+) PASS$', exit_block, re.MULTILINE)
assert len(criteria) == 19 and all(f'| {criterion} |' in s for criterion in criteria)
print(f'6 checks passed; {len(links)} links; {len(names)} architecture tests; {len(criteria)} exit criteria')
PY
```

Result: **6 documentation checks passed**; **24 local links** resolve, exact DRAFT
status and sole-file scope match, no trailing whitespace, **13/13 architecture
requirements** and **19/19 literal exit criteria** are covered. These checks do
not constitute independent architecture review or owner approval of this plan.
