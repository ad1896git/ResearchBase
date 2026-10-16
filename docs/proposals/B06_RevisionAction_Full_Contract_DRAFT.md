# B06 Completed RevisionAction, remaining result shapes — DRAFT

**Status: APPROVED by owner 2026-10-15 — first slice authorized for implementation**

## Start here (for the implementer)

This proposes completion of RevisionAction's remaining result contracts after
[approved PR2-15](PR2-15_RevisionAction_Contract_DRAFT.md) and its shipped
[migration 0044](../../migrations/versions/0044_pr2_15_revision_action.py).
It records completed responses; it does not perform a revision or resolve an Issue.
Owner contract approval and separate implementation authorization are required.

Build in this order after authorization:

1. Freeze the finite relevance rules and dependency exclusions (§§3, 11).
2. Add a forward guard migration; preserve 0044 and its existing records (§12.1).
3. Extend the existing domain, Application and repository modules (§12.3).
4. Use the shared-lock protocol for writes/replay and lock-free snapshot reads (§12.2).
5. Add the named tests, run focused checks, record results and stop (§12.4).

Read §1 for authority and shipped scope, §3 for old-to-new relevance, §11 for
closed DTOs/errors and §12 for construction details. Use §10 as a glossary.
No source, migration, test or governing architecture change accompanies this draft.

Five review rules:

1. Preserve immutable history and exact typed references; use the existing R2 hash.
2. Prove relevance through the saved basis graph, never text or project alone.
3. Separate historical replay from first admission and current read entitlement.
4. Protect mutable facts for writes; use one read-only snapshot for reads and
   recheck authority with fresh DB time.
5. Keep Decision/NO_CHANGE, manuscript freeze and Issue disposition dependencies
   closed until their own contracts and implementations exist.

## 1. Purpose, authority and inspected baseline

| Authority | Constraint applied here |
| --- | --- |
| [System 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 7–9, 23 | Facts precede authority; history is immutable; governance concepts stay distinct. |
| [Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A17–A23; [Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md) | RevisionAction is already admitted; focused R2/R3/R4 corrections take precedence. |
| [Compatibility 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§9, 12–18, 24, 38 | Additive changes, exact FKs, stable commands/errors and no historical hash rewrite. |
| [Phase 2 spec 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §§19–22, PR2-15; [Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md) | Completed revision trace is separate from planning and Issue disposition. |
| [Fields 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md); [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md), RevisionAction payload; [Governance R2 17](../architecture/17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md), §4 | Seven concrete result columns, exact finite shapes, Run identity reference and immutable correction history. R2 replaces older action/result examples. |
| [R3 18](../architecture/18_Phase2_Design_R3_Targeted_Remediation_v1.0.md); [Temporal R4 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md) | Fresh database time after waits; saved historical result does not bypass current disclosure authority. |
| [Decision 20](../architecture/20_PR2_15_Minimal_Decision_Command_Contract_v1.0.md); [Harness specification](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 18–19 | PROCEED is not revision disposition; Application boundary and executed evidence govern completion. |

The [domain](../../src/researchbase/domain/revision_action.py) and
[closed command](../../src/researchbase/application/revision_action.py) already
represent all seven shapes. The service's `_supported` and 0044's
`pr215_revision_guard` admit only issue-only CLAIM_CHANGE/CONCLUSION_CHANGE,
strictly later frozen versions of the matching owning identity. Correction,
UUID replay, historical verification and locked snapshot reads already exist;
B06 replaces the read path with the lock-free snapshot protocol in §12.2.
This is the baseline, not a claim that all PR2-15 acceptance gates passed.

[Internal review](../../src/researchbase/application/internal_review.py) admits
Claim/conclusion targets; [Decision](../../src/researchbase/application/decision.py)
admits INTERNAL_SCIENTIFIC_RELEASE/PROCEED only. Neither supplies revision-purpose
Decision semantics. [Publication](../../src/researchbase/application/publication.py)
provides manuscript drafts, not manuscript freeze. These remain dependencies.

The [revision repository](../../src/researchbase/persistence/revision_action_repository.py)
currently takes request advisory → old target UPDATE → snapshot SHARE locks.
[Decision](../../src/researchbase/persistence/decision_repository.py) supplies the
mutable-table inventory; [novelty](../../src/researchbase/persistence/novelty_repository.py)
uses a first-statement table lock for coverage, but target-first locking for other
writes. B06's write-only table-first/no-target-row-lock protocol below is a **proposed
refinement**, not a description of every existing command. It requires replacing
0044's locking guard in a new migration, not simply moving one Application call.

## 2. Scope, dependency boundaries and non-goals

Propose issue-based NEW_EXPERIMENT, ANALYSIS_CHANGE and SOURCE_CHANGE, plus
explicit cross-target Claim/conclusion rules. Keep the two existing same-identity
paths unchanged. Define MANUSCRIPT_CHANGE's relevance now, but do not enable it
until an independently approved frozen-manuscript contract and verifier ship.
All Decision-bearing actions and NO_CHANGE remain unavailable. No eligible
revision-purpose Decision enum/value can be inferred from PROCEED.

This is the full remaining-shapes proposal, with an implementable issue-based
slice and explicit unavailable combinations. It does not claim that dependency
exclusions complete the full Phase 2 backlog item. No new persistence mechanism,
canonical entity, receipt, JSON reference or runtime dependency is proposed.

## 3. Invariants and conservative judgments

Completed results exist before recording. Hashed versions must have nonnull
frozen_at/hash and status FROZEN or SUPERSEDED; immutable StatisticalResult is a
record, not a Version. Terminal Run means SUCCEEDED/FAILED/CANCELLED with sealed
inputs and its exact ExperimentSpecVersion. FAILED/CANCELLED is completion
history, never positive support. First admission requires current deterministic
VALID closure of the result dependencies; an invalid old target may be corrected.

Verify the saved ReviewRecord hash, target binding and historical creation
authority using the existing review/Decision verifiers. Derive project through
Issue → ReviewRecord. Traverse only exact typed edges and verify their hashes.
Do not require an obsolete target to become valid before recording its correction.

### 3.1 Finite relevance matrix — proposed admission policy

Define C as the exact reviewed ClaimVersion, or the exact ClaimVersion inputs of
the reviewed conclusion via `scientific_conclusion_claim_inputs`. Define M as
Measurements reached from C via `evidence_relations`, directly or through
`statistical_result_inputs`. These paths are verified frozen scientific closure;
a shared project, metric, phrase or hypothesis label alone is insufficient.

| action_type | Exactly nonnull result suffixes (each prefixed `result_`) | Required relevance and completion |
| --- | --- | --- |
| NEW_EXPERIMENT | experiment_spec_version_id, run_id | The new Run uses that exact frozen Spec and is terminal/sealed. From M follow `measurements.run_id → runs.experiment_spec_version_id → experiment_spec_versions.experiment_spec_id`. Result Spec has the same experiment_spec_id as at least one reached Spec and version_number >= that Spec's. Result Run differs from every reached Run. No hypothesis-only shortcut. |
| ANALYSIS_CHANGE | statistical_result_id | New immutable result is absent from C's old statistical evidence and has at least one exact Measurement input in M; verify all its inputs, not just the overlap. New datasets with no shared Measurement need a later relevance contract. |
| CLAIM_CHANGE | claim_version_id | Strictly higher version_number under the same claim_id as one member of C. This retains the shipped Claim-target rule and adds the conclusion-input case. |
| CONCLUSION_CHANGE | scientific_conclusion_version_id | Conclusion target: strictly higher version_number under the same scientific_conclusion_id. Claim target: new conclusion has an exact claim input equal to the reviewed Claim or a higher frozen version under its claim_id. No same-project-only match. |
| MANUSCRIPT_CHANGE | manuscript_version_id | Future frozen manuscript has a direct exact claim/conclusion placement equal to the reviewed target or its higher same-identity successor. Citation alone is insufficient. Manuscript-target reviews remain excluded. **Unavailable in this slice.** |
| SOURCE_CHANGE | source_version_id | Result is CORRECTED or RETRACTED and its exact predecessor_source_version_id chain reaches an old SourceVersion in the target's saved literature closure, under the same literature_source_id. Verify correction-basis artifact and current project source access. Unrelated/new sources and ordinary PUBLISHED versions do not qualify. |
| NO_CHANGE | none | Requires an independently contracted revision-purpose Decision with nonblank rationale. **Unavailable**, including issue-only and PROCEED. |

For SOURCE_CHANGE, old literature closure is exact conclusion literature inputs
and claim support snapshots (including the snapshots saved on conclusion claim
inputs), through `literature_evidence_relations → literature_evidence → source_versions`.
Direct conclusion literature inputs go straight to `literature_evidence`.
A source correction does not rebind old evidence. A structurally valid retraction
may be recorded even though its downstream scientific dependents become stale;
validate the correction's own closure, not a fictitious positive-support status.
This is the explicit exception to the first-write VALID gate: a verified RETRACTED
SourceVersion is admissible as correction history; readback still exposes its
owner-derived current validity and does not label it usable evidence.

For a Claim-target SOURCE_CHANGE, the relevance predicate is existential over
exact immutable support snapshots bound to the reviewed ClaimVersion. Verify a
matching snapshot and its complete typed closure. Do not invent a requirement
that the snapshot predate or be pinned by the Review; no such temporal cutoff is
part of this matrix. A concurrently appended snapshot may establish a new valid
witness, but cannot invalidate an existing immutable witness. Unrelated sidecars
are not action dependencies, and other Claim-target shapes do not enumerate them.
The literal write inventory in §12.2 is unchanged.

All unlisted result fields are null. Relevance proves a connection, not adequacy.
Recording adds no IssueEvent, changes no OPEN Issue and creates no re-review,
Decision, Approval, scientific evidence, release or external effect.

## 4. Proposed commands, DTOs and historical readback

Retain `record_revision_action(principal, RecordRevisionActionCommand)` and
`read_revision_action(principal, project_id, identity)`. No bulk/list/mutation API.
Use the existing frozen dataclasses; exact fields/types are pinned in §11.3.
Caller-supplied actor, time, hash, rationale, status or transition is rejected.

Readback keeps exact basis, seven result slots, predecessor, recorder/time,
content_hash/hash_scheme and verified typed provenance. Extend provenance in
fixed order: review, old target, nonnull results in RESULT_KEYS order, predecessor.
ReviewIssue and Run are identity refs; no fabricated hash. Return references, not
nested review text. `target_validity`, `result_validity` and
`has_superseding_action` are derived, never persisted action lifecycle fields.

## 5. Schema and literal hash proposal — no migration

Keep 0044's existing columns, FKs, `revision_action_shape`, indexes and immutable
history. Use exactly `revision_action_material` and Hash R2 15: type,
material_version=1, review_issue I-ref/null, decision R-ref/null, action_type,
all seven RESULT_KEYS with explicit nulls, supersedes_revision_action R-ref/null,
and created_by I-ref. All results except Run are hashed refs. Use existing
sha256-cjson-v1 and canonical JSON; no row ID, project scope, time or derived
validity in the payload. Never rehash old rows into a new format.

DDL changes only refine guards in a forward migration (§12.1). No result is
created or frozen by this command; no extra provenance relation is persisted.

## 6. Error contract — proposed use of existing categories

Use the existing ErrorCode members and transport mappings in §11.2. Access
checks precede existence/material disclosure. UUID collisions in another project
or another recorder return nondisclosing FORBIDDEN. An authorized missing exact
object returns NOT_FOUND. Do not introduce HASH_MISMATCH or B06-specific codes.

## 7. Transactions, concurrency and failure recovery

Writes, including `record_revision_action` replay: one synchronous READ COMMITTED
UoW per attempt, at most one committed action. Take the snapshot SHARE lock as
the first SQL statement, before SET LOCAL, advisory locks, lookups or credential
queries (§12.2). Every mutable closure/authority fact read by a write command is
protected; existing immutable SQL guards protect frozen material and inputs.

Exact-ID `read_revision_action`: one fresh REPEATABLE READ, read-only transaction,
configured before the first query. Authenticate and verify saved hashes/closure
within that snapshot, without explicit table, row or advisory locks (§12.2).

First write: active project OWNER/RESEARCHER and live verified principal.
Reads: existing Decision reader roles OWNER/RESEARCHER/REVIEWER/VIEWER/APPROVER.
Use advancing `clock_timestamp()` after waits and immediately before commit/
return, rechecking credential validity, binding, role interval and membership.
Do not weaken existing HUMAN subject-binding constraints to admit Agents.

Replay: authenticate and establish current read entitlement; require same UUID,
project, original actor and every command field (including all nulls). Different
material yields IDEMPOTENCY_CONFLICT. Verify saved hash and historical closure;
return saved record after write-role loss or later invalidity, with current
validity projected. Do not demand current-valid first-write gates on replay.
Read entitlement loss denies even a previously successful recorder. Recover
uncertain commit by exact UUID, never a second request identity.

Corrections retain exactly the same Issue/Decision IDs and derived project.
Predecessor exists, has valid material, differs from new ID, and has no successor.
Lock it before testing successor existence; the partial unique index prevents
forks, including normal SQL races. Verify chains iteratively with a visited set;
reject cycles. New result/action type may differ if its own admission rules pass.
Multiple independent roots per Issue remain allowed. No predecessor mutation.

Retry only deadlock/serialization failures in a fresh UoW, at most three attempts,
as the shipped service does. Roll back all writes on any failure; timeout is not
success. Do not change other commands' isolation or locking by this draft.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

Test every admitted shape and wrong/null/extra result slot; exact relevance and
all unrelated same-project counterexamples; nonterminal/unsealed/wrong-Spec Run;
FAILED/CANCELLED history; corrupt/stale result versus stale old target; source
lineage, retraction and access. Keep excluded shapes/Decision bases denied.

Independently compute R2 hashes for all seven representable shapes, including
explicit nulls and Run I-ref, without treating hash representability as admission.
Prove no Issue/governance/publication side effects and no historical mutation.
Concrete files and PostgreSQL race obligations are in §12.4.

## 9. Acceptance criteria and evidence boundary

Draft completion means this single document is reviewable, source links resolve
and focused checks are reported exactly. Existing tests exercise baseline
behavior; they cannot prove these unimplemented rules or owner approval.

Future acceptance requires authorized scope, forward migration/catalog evidence,
normal-role bypass tests, result-owner regressions, observed lock races, restart/
replay/rollback evidence and no open P0/P1 findings. MANUSCRIPT_CHANGE, revision
Decisions, NO_CHANGE and Issue disposition need separate authorization and tests
before anyone claims full B06/PR2-15/Phase 2 completion. Stop after the approved slice.

## 10. Glossary

| Term | Meaning |
| --- | --- |
| Completed RevisionAction | Immutable attribution of an already completed response. |
| Basis | Exact Issue and/or eligible Decision; an Issue resolves to its saved review target. |
| Relevance | Deterministic typed old-to-new connection, not a judgment of resolution. |
| Closure | Exact frozen/terminal dependencies and their independently verified material. |
| Supersession | New same-basis correction preserving predecessor history. |
| Replay | Same actor/material/UUID historical return with current read entitlement. |
| I-ref / R-ref | Typed identity reference / typed exact ID plus existing content hash. |
| Snapshot locks | Write-only SHARE table locks protecting mutable facts across READ COMMITTED statements. |

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

These are proposed choices awaiting approval, not new architecture authority.
Admit only the issue-based combinations in §3.1 whose prerequisites exist.
Do not broaden review targets. Freeze the relevance predicates exactly as written;
new data-only analysis and hypothesis-only experiment relevance stay excluded.
Retain existing replay, roles, same-basis nonforking corrections and R2 hashes.
Adopt table-first protection for B06 write commands only, including the SQL guard
changes; exact-ID reads use a lock-free read-only REPEATABLE READ snapshot.

### 11.2 Pinned error mappings

Exact mappings from [api/errors.py](../../src/researchbase/api/errors.py) and
[cli/errors.py](../../src/researchbase/cli/errors.py):

| ErrorCode | HTTP | CLI exit | B06 condition |
| --- | --- | --- | --- |
| VALIDATION_ERROR | 422 | 2 | Wrong DTO/type/enum, absent basis, bad result shape, unknown field. |
| AUTHENTICATION_REQUIRED | 401 | 3 | No verified principal. |
| FORBIDDEN | 403 | 3 | No live entitlement, foreign/inaccessible scope or another recorder's UUID. |
| NOT_FOUND | 404 | 3 | Authorized exact basis/result/read ID missing. |
| INVALID_STATE_TRANSITION | 409 | 4 | Unavailable shape/basis path, nonterminal Run, predecessor already superseded, normalized lock/statement timeout. |
| FROZEN_REFERENCE_REQUIRED | 409 | 5 | Required version not frozen or Run inputs not sealed. |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Hash, lineage, relevance, Spec/Run, same-basis or current closure failure. |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Entitled original actor reuses ID with changed material. |
| IMMUTABLE_RECORD | 409 | 4 | Attempted UPDATE/DELETE of an action. |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Concrete FK/structural DB reference failure. |
| CONCURRENT_MODIFICATION | 409 | 4 | Deadlock/serialization conflict after bounded transaction retries. |

Preserve SQLSTATE normalization P17R1 → INVALID_STATE_TRANSITION,
P17F1 → IMMUTABLE_RECORD, P17F2 → PROVENANCE_CLOSURE_VIOLATION,
P17F3 → IDEMPOTENCY_CONFLICT in [uow.py](../../src/researchbase/persistence/uow.py).
Normalize a predecessor unique race to INVALID_STATE_TRANSITION after rollback,
without exposing driver text; this constraint-specific addition needs tests.

### 11.3 DTO fields, Python types and limits

| DTO field(s) | Exact Python type / limit |
| --- | --- |
| Command id, project_id | UUID, exact UUID instances; required. |
| review_issue_id, decision_record_id, supersedes_revision_action_id | UUID \| None, default None; at least one basis syntactically, but this slice requires Issue and null Decision. |
| result_experiment_spec_version_id, result_run_id, result_statistical_result_id, result_claim_version_id, result_scientific_conclusion_version_id, result_manuscript_version_id, result_source_version_id | UUID \| None, default None; exact §3.1 shape. |
| action_type | str restricted to NEW_EXPERIMENT, ANALYSIS_CHANGE, CLAIM_CHANGE, CONCLUSION_CHANGE, MANUSCRIPT_CHANGE, SOURCE_CHANGE, NO_CHANGE. No aliases. |
| Read arguments project_id, identity | UUID, exact UUID instances. |
| Readback id, project_id, review_issue_id, created_by | UUID (Issue always present in this slice). |
| Readback optional IDs, action_type | Same field names/types as command. |
| created_at | datetime, aware UTC, trusted DB recording time. |
| content_hash, hash_scheme | str: exactly 64 lowercase hex characters; literal sha256-cjson-v1. |
| provenance | tuple[RevisionReference, ...]; type/id/content_hash as existing domain class; no nested free text. |
| target_validity, result_validity | str restricted to VALID, STALE, INVALID. NO_CHANGE has no readback in this slice. |
| has_superseding_action | bool, derived. |

No text/list payloads or pagination limits are added. Exactly seven result slots,
one basis Issue and at most one predecessor per action. Chain traversal is
iterative, without an arbitrary historical depth cutoff; existing 30s statement
and, for writes, 10s lock limits bound operations (§12.2). Never truncate
verification and report success. Unknown constructor fields are rejected; future
transport adapters must use extra=forbid and UUID parsing before this boundary.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

Keep the existing physical types (all columns already exist in 0044):

```text
id UUID PRIMARY KEY
created_by UUID NOT NULL; created_at TIMESTAMPTZ NOT NULL
action_type VARCHAR(32) NOT NULL
review_issue_id UUID NULL; decision_record_id UUID NULL
result_experiment_spec_version_id UUID NULL; result_run_id UUID NULL
result_statistical_result_id UUID NULL; result_claim_version_id UUID NULL
result_scientific_conclusion_version_id UUID NULL; result_manuscript_version_id UUID NULL
result_source_version_id UUID NULL; supersedes_revision_action_id UUID NULL
content_hash CHAR(64) NOT NULL; hash_scheme VARCHAR(32) NOT NULL
```

Preserve all concrete ON DELETE RESTRICT FKs, `revision_action_shape`,
`uq_revision_action_predecessor` (unique where predecessor nonnull), and
`ix_revision_action_<column>` indexes from 0044. Keep its basis-required,
no-self-reference, hash-format and fixed-scheme CHECKs; inspect actual catalog
names rather than guessing names of those unnamed CHECKs.

Proposed forward SQL outline (function bodies implement §3.1, not generic JSON):

```sql
-- Replace only the function body; existing trigger name remains installed.
CREATE OR REPLACE FUNCTION pr215_revision_guard() RETURNS trigger
  LANGUAGE plpgsql AS $$ /* immutable UPDATE/DELETE: P17F1;
    INSERT: supported issue-only shape, exact basis, scope, frozen/terminal
    result, relevance, same-basis predecessor and no-cycle checks;
    remove old target FOR UPDATE; use the §12.2 protocol */ $$;
CREATE FUNCTION b06_complete_revision() RETURNS trigger
  LANGUAGE plpgsql AS $$ /* repeat structural closure/relevance checks
    against final transaction state; no new late scientific row locks */ $$;
CREATE CONSTRAINT TRIGGER b06_revision_complete
  AFTER INSERT ON revision_actions DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION b06_complete_revision();
```

This is a sketch, not executable migration text. Follow
[0042's deferred completeness triggers](../../migrations/versions/0042_pr2_15_minimal_decision.py).
Use `SET CONSTRAINTS b06_revision_complete IMMEDIATE` before final readback/commit.
DB guards enforce scope, exact frozen/terminal shape, relevance and correction
structure for normal-role direct SQL; Application recomputes hashes, complete
scientific validity and authority. A deferred trigger alone is not concurrency
protection: keep predecessor locking and its unique index. An INSERT trigger's
implicit ROW EXCLUSIVE lock on revision_actions is why that table must not enter
the shared snapshot inventory. The guard acquires that inventory before basis
queries for direct SQL; supported Application writes acquire it earlier still.

Do not edit accepted migrations. Allocate the next actual Alembic revision after
checking `alembic heads`; no reserved migration number here. Preflight preserved
rows without rewriting them. Downgrade refuses when it would strand a newly
admitted shape under 0044's narrower guard or discard retained history.

### 12.2 Exact write lock order and read transactions

For write commands only, define B as the literal sorted table set
`_SNAPSHOT_TABLES` in decision_repository.py **minus claim_versions**, exactly as
the shipped revision repository does.
It covers actors/bindings/memberships/roles/projects, audit/impact/correction,
literature evidence/review events, sources/project links, scientific owning
identities, artifact/dataset/metric/spec material and runs. Pin that set in the
implementation test; changes require an inventory review. Do not add
revision_actions, immutable review/Issue tables or scientific_conclusion_versions
to B. Frozen Claim/conclusion/input material uses existing immutability guards;
FROZEN→SUPERSEDED does not change acceptable historical material. No manuscript
path is enabled, so no manuscript table inventory is silently assumed.

`record_revision_action`, including UUID replay, in a fresh READ COMMITTED UoW:

1. **First SQL statement:** `LOCK TABLE <B in lexical order> IN SHARE MODE`.
   No preflight SELECT, SET LOCAL or advisory lock precedes it. Use engine/connection
   lock_timeout=10s and statement_timeout=30s configured before transaction start
   so this initial lock is bounded; this uses existing PostgreSQL timeout settings,
   not new lock infrastructure. Reapply SET LOCAL bounds after this statement.
2. Transaction advisory `pg_advisory_xact_lock(hashtextextended(:key,0))`, key
   `pr215:revision:<canonical UUID>`, preserving the shipped request namespace.
3. Enable existing protected closure readers; read live read entitlement, saved
   action and exact Issue/review. No project/parent/target/result FOR UPDATE locks.
   For a saved action, compare original actor/material and verify historical closure.
4. For a new action, recheck writer entitlement; lock exact review then Issue
   FOR SHARE (immutable rows); lock the optional predecessor FOR UPDATE, then
   check its terminal head and same basis. Ancestors are immutable reads only.
5. Verify complete old/result closure and relevance through protected readers;
   check fresh authority/time, insert the single action, force deferred guards,
   verify readback, recheck authority with fresh DB time, commit.

`read_revision_action` uses a separate exact-ID read protocol, as in B01
`get_search_result_resolution` and the PR2-18 exact-ID read fix:

1. Open one fresh UoW/transaction and set REPEATABLE READ and READ ONLY before
   the first query (including authentication or existence lookups). Retain the
   30s statement timeout configured before transaction start.
2. Authenticate the reader and establish current read entitlement before
   disclosing existence/material. Read the exact saved action and all typed
   dependencies in that single snapshot; verify saved hashes and historical
   closure, including the predecessor chain. Project validity and successor
   presence from the same snapshot, without requiring current-valid admission.
3. Recheck read entitlement with fresh `clock_timestamp()` immediately before
   return, preserving credential, binding, role-interval and membership checks.
   End the read-only transaction without canonical changes.

Do not acquire table SHARE locks, advisory locks (including the request key),
row locks or the write protocol's inventory B on this read path, including inside
closure/authentication adapters. Snapshot consistency replaces write protection
for reads: concurrent unrelated inserts must commit while the read remains open
and remain outside its established snapshot. `record_revision_action` replay
continues to use the write protocol above; it does not define the read protocol.

For write commands, SHARE conflicts with normal writers' ROW EXCLUSIVE and
prevents mutable-fact phantoms. Existing Decision/Review/novelty target-first commands may keep their
protocol: B06 takes no scientific row lock while holding B, so it does not wait
back on their prelocked targets. Immutable review rows cannot be updated by
normal writers; action insertion writes outside B. Verify this reasoning with
actual owning-writer races before accepting the protocol. Do not retain hidden
row locks in closure adapters or the replaced 0044 guard. A new mutable dependency
requires an explicit inventory/protocol update before admitting its path.

### 12.3 Ordered build steps and module paths

1. Approve §11 and dependency exclusions; inspect head and add a single forward
   file under `migrations/versions/` implementing §12.1, with downgrade safeguards.
2. Extend `src/researchbase/domain/revision_action.py` with pure finite relevance
   validation and iterative predecessor material verification; preserve literal
   payload helpers and Phase 1 hashes.
3. Extend `src/researchbase/application/revision_action.py` with per-shape closure
   checks and replay/read projections; reuse result-owner verification from
   `application/literature_evidence.py`, `scientific_conclusion.py`,
   `source_version.py`, `application/closure.py` and Phase 1 services in
   `application/commands.py`.
   Extract reusable pure/read verification where necessary; never call a separate
   committing service transaction during action admission.
4. Update `src/researchbase/application/ports.py`,
   `src/researchbase/persistence/revision_action_repository.py` and
   `src/researchbase/persistence/uow.py` for protected typed traversals, table-first
   acquisition for writes, lock-free read-only REPEATABLE READ setup before the
   first read query, and named-constraint error normalization; configure a dedicated
   connection timeout profile via `src/researchbase/persistence/database.py`
   before opening this UoW, without altering owning writers.
   Follow owning FK paths in `persistence/models.py`, migrations 0030/0033 and
   `application/manuscript_scientific_trace.py`; the trace query is not a substitute
   for a full result hash/validity verifier. Keep owning writers unchanged.
5. Add §12.4 tests and evidence. No new API/CLI endpoint is required; if adapters
   are separately authorized, keep them thin and use §11.2 mappings. Stop.

### 12.4 Test artifacts and required cases

| File (existing unless marked new) | Cases/evidence |
| --- | --- |
| `tests/unit/phase2/test_revision_action.py` | Closed DTO and independent literal hashes for seven shapes; Run identity ref; pure relevance, iterative cycle rejection and unchanged shipped payloads. |
| `tests/unit/phase2/test_pr2_15_uow_errors.py` | SQLSTATE compatibility, sanitized predecessor unique race, timeout and bounded retries. |
| `tests/architecture/test_b06_revision_action.py` (new) | Layering; concrete FK-only results, no JSON/receipt/status/entity expansion, unchanged Phase 1 material and no Issue disposition/effect. |
| `tests/integration/phase2/test_revision_action.py` | Preserve same-identity paths, replay after stale/write loss, read loss, multiple roots, nonforking correction and no IssueEvent change. |
| `tests/integration/phase2/test_b06_revision_action.py` (new) | Every new admitted combination, wrong project/identity/measurement/source, DRAFT/unsealed/nonterminal/wrong-Spec, bad lineage/artifact/hash, invalid result versus stale target; denied Decision/NO_CHANGE/manuscript; SQL constraint/catalog/forward upgrade and refused downgrade evidence. |
| `tests/integration/phase2/test_b06_revision_concurrency.py` (new) | Assert first SQL statement and exact inventory for writes/replay only; assert read-only REPEATABLE READ setup before the first read query and no explicit table/row/advisory locks on reads; pause an exact-ID read and prove a concurrent unrelated insert commits before the read ends and stays outside its snapshot (following PR2-18's `test_exact_read_does_not_block_unrelated_insert`); preserve read authentication/hash/closure checks; two-session witnesses with pg_blocking_pids/pg_stat_activity; both commit orders for source/evidence/validity/role writers; scheduled expiry during first table-lock wait; same UUID, predecessor fork race, direct SQL, review/Decision/claim-freeze/novelty overlaps; rollback, restart and lost commit acknowledgment. No sleep-only proof. |

Run static checks, unit/architecture tests and focused PostgreSQL suites for
RevisionAction, PR2-14 reviews, PR2-15 Decision/schema/coordination, PR2-18 concurrency,
PR2-11 conclusion closure, source lineage and Phase 1 Run/StatisticalResult owners.
Choose the exact owner test files from the authorized diff; do not run the whole
suite in this documentation task. Report commands, PG version and exact pass/
fail/error/skip counts. Baseline tests do not count as unimplemented B06 tests.

### 12.5 Not in this slice

Revision-purpose Decision enums/authority/basis, Decision-only or combined basis,
NO_CHANGE, manuscript freeze or manuscript-target review, Issue ADDRESSED/
DISMISSED/VERIFIED, automatic re-review, result creation/execution, release/
approval/package/consent, ExternalEffect, Agent authentication/runtime, arbitrary
cross-domain causality, new infrastructure and any Phase 2 acceptance declaration.

## 13. Open questions for the owner — override register

Approval must explicitly accept or replace the §3.1 relevance predicates,
§11 policies and §12.2 write-only table-first / lock-free snapshot read protocols.
In particular, same-experiment lineage and shared-Measurement analysis are conservative proposed boundaries;
they do not claim every scientifically relevant response is representable.
Missing Decision and manuscript contracts remain blocking dependencies for their
paths. Approval of this document alone does not authorize implementation.

## 14. Documentation verification note

Executed on 2026-10-15. These are baseline/documentation checks, not B06
implementation acceptance. Only this proposal was added; no branch, commit or
push was created. The whole test suite was not run.

All uv invocations used the existing locked environment with this prefix:

```bash
UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv \
uv --cache-dir /tmp/b06-uv-cache run --offline --no-sync
```

| Command after that prefix (extra environment shown below) | Observed result |
| --- | --- |
| `ruff check .` | Exit 0; All checks passed. |
| `ruff format --check .` | Exit 0; 536 files already formatted. |
| `pyright --pythonpath /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python` | Exit 0; 0 errors, 0 warnings, 0 informations; preamble noted absent checkout-local .venv. |
| `pytest -o addopts='' -ra tests/unit tests/architecture` | With PYTHONPATH=src: 2156 collected; 2139 passed, 5 failed, 12 errors, 5 warnings. |
| `pytest -o addopts='' -ra --tb=short tests/unit/phase2/test_pr2_04_static_acceptance.py tests/architecture/test_pr2_19_boundaries.py::test_literature_source_not_evidence` | Diagnostic rerun: 2 collected; 1 failed, 1 error, 1 warning. |

Four unit failures are sandbox-denied AF_UNIX socket binds in
`test_hg1_runner.py`. The static-acceptance failure checks the diff from pinned
commit b8179f17720ca47c3b25ad9d36f6a8e8d4aa79ff and finds existing evidence-file
whitespace, including a pyright-000.txt blank EOF line; ordinary working-tree
`git diff --check` passed. Twelve PR2-19 architecture fixture errors require an
explicit RB_TEST_ADMIN_URL; they are not passing architecture tests.

Attempted focused PostgreSQL command (same uv prefix, with PYTHONPATH=src and
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase@127.0.0.1:56366/postgres):

```bash
pytest -o addopts='' -ra --maxfail=1 \
  tests/integration/phase2/test_revision_action.py \
  tests/integration/phase2/test_pr2_15_decision.py \
  tests/integration/phase2/test_pr2_15_decision_schema.py \
  tests/integration/phase2/test_pr2_15_coordination.py \
  tests/integration/phase2/test_pr2_18_concurrency.py
```

129 collected; 1 setup error, 128 unexecuted because of --maxfail=1; no passed,
failed test bodies or skips. PostgreSQL 18 initdb failed before startup with
`could not create shared memory segment: Operation not permitted`; the test
connection also failed with Operation not permitted. No connected server version
or PostgreSQL acceptance result is available. The external loop must provide
that evidence; this document does not turn the blocked run into PASS.

A repository-local inline Python check resolved all 27 relative Markdown links,
compared all 11 error rows directly with api.errors._STATUS and
cli.errors.CLI_EXIT_CODES, and compared all 15 top-level headings with PR2-18's
section order: all passed. `git diff --check` passed. These checks do not validate
the proposed unimplemented database protocol.
