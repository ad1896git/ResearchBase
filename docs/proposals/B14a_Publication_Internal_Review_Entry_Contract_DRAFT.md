# B14a Publication DRAFTING→INTERNAL_REVIEW Entry Transition Contract — DRAFT

**Status: APPROVED by owner 2026-10-18 — first slice authorized for implementation**

## Start here (for the implementer)

B14a moves one Publication from DRAFTING to INTERNAL_REVIEW against one explicitly
supplied, already frozen ManuscriptVersion. It supplies the real Application
prerequisite required by [B14](B14_Publication_Ready_Transition_Contract_DRAFT.md)
§§2 and 12.1. Entry starts internal review; it does not require a completed review,
readiness Decision or ApprovalGrant. Existing applicable OPEN BLOCKING Issues
still deny entry. Scientific validity comes from exact canonical facts.

Read §§1–4, then §10 for terms, §11 for fixed decisions and §12 for construction.
This is a contract for approval, not implementation authorization. After separate
authorization, build in this order:

1. Reconcile the actual migration head and B14's preservation of this entry branch.
2. Extend existing lifecycle events and Publication guards (§12.1); add no table.
3. Add the closed Application command and exact event query (§§11.3, 12.3).
4. Use SHARE-first READ COMMITTED writes and lock-free snapshot reads (§12.2).
5. Run §12.4 checks with real PostgreSQL 18.x, retain evidence and stop at §12.5.

Five rules whose violation fails review:

1. Explicit exact manuscript ID/hash selects the target; current is navigation only.
2. Frozen closure, retained bytes, current VALID status and applicable blockers
   outrank authority; no review-count or favorable-recommendation gate is added.
3. One status update, one row_version increment and one immutable entry event
   commit together; no state-only success or late event repair.
4. Fresh database time after waits and after deferred checks governs live authority.
5. Completed replay is a lock-free historical read under current read entitlement;
   later READY, invalidity, blockers or write-role loss cannot create a second entry.

## 1. Purpose, authority and inspected baseline

| Authority | Constraint carried forward |
| --- | --- |
| [System 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 7–12; [Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A18–A23; [Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md) | Facts before authority; one owner; frozen immutable provenance; reuse Publication and its lifecycle event. |
| [Cross-Phase 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§9–18, 24, 28; [Phase 2 specification 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), publication/governance sections | Common Application boundary, concrete references, retained history and separate internal/package/external gates. |
| [Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), §6; [Field contract 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md), publication rows; [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md), manuscript payload | DRAFTING→INTERNAL_REVIEW on frozen manuscript; every transition checks project, closure and blocking issues and appends event. Existing manuscript hashes remain unchanged. |
| [Governance R2 17](../architecture/17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md), §1; [R3 18](../architecture/18_Phase2_Design_R3_Targeted_Remediation_v1.0.md), §5; [Temporal R4 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md), §§1, 4–5 | Readiness permission belongs to INTERNAL_REVIEW→READY, not entry; fresh-time authorization, immutable history and entitled replay. No new approval tuple. |
| [B04](B04_Manuscript_Freeze_Contract_DRAFT.md), [B05](B05_Manuscript_Internal_Review_Contract_DRAFT.md), [B11](B11_Ready_For_Submission_Decision_Contract_DRAFT.md), [B12](B12_Prepare_Submission_Decision_Contract_DRAFT.md), [B13](B13_Grant_Consumption_Contract_DRAFT.md), [B14](B14_Publication_Ready_Transition_Contract_DRAFT.md), §§2, 12 | Reuse implemented seal/review mechanisms, B11's finite blocker traversal and B13/B14 lock order. B11–B14 are approved dependencies per this task; retained draft labels do not authorize B14a code. |
| [Harness 09](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 18–21 | Evidence before acceptance; documentation approval and implementation authorization are distinct. |

Inspected 2026-10-17: [0035](../../migrations/versions/0035_pr2_12_publication_draft.py)
has DRAFTING-only lifecycle checks and UNIQUE(publication_id) on events.
[0048](../../migrations/versions/0048_b04_manuscript_freeze.py) extends
pr212_publication_guard for B04's current-pointer update and seal completeness.
[0049](../../migrations/versions/0049_b05_manuscript_review.py) supplies exact
manuscript reviews. The current migration inventory reaches
[0059](../../migrations/versions/0059_b13_grant_consumption.py); B14's older
0051 baseline is historical. No entry command exists in
[PublicationService](../../src/researchbase/application/publication.py).

[ManuscriptFreezeService.verify_in_uow](../../src/researchbase/application/manuscript_freeze.py)
checks literal seals, closure, bytes and validity.
[DecisionService](../../src/researchbase/application/decision.py) supplies
_readiness_authorize and _readiness_blockers; the
[Decision repository](../../src/researchbase/persistence/decision_repository.py)
uses b11_applicable_reviews from [0054](../../migrations/versions/0054_b11_ready_for_submission.py).
[InternalReviewService](../../src/researchbase/application/internal_review.py)
verifies reviews and Issue/disposition histories. These are reusable in-UoW
mechanisms, not permission to call public services in nested transactions.
[Novelty repository](../../src/researchbase/persistence/novelty_repository.py)
and Decision writes demonstrate FIRST-SQL SHARE.
[0042](../../migrations/versions/0042_pr2_15_minimal_decision.py) demonstrates
deferred final-graph checks; use its current-transaction pattern with the
wraparound-safe xid comparison from [0057](../../migrations/versions/0057_xid_wraparound_guards.py).
Source presence is not dependency acceptance evidence. No B14a execution pack exists.

## 2. Scope, dependency boundaries and non-goals

Add only `transition_publication_internal_review(principal, command)` and
`get_publication_internal_review_entry(principal, query)` to PublicationService.
Reuse PublicationLifecycleEvent as the command's result and replay owner. Add no
receipt table, event journal, canonical entity, semantic JSON or infrastructure.
B04/B05 and the existing B11 blocker/history readers must be real prerequisites.
B12/B13/B14 contracts constrain compatibility; entry creates no Decision, request,
grant, consumption, review, Issue, manuscript or artifact.

B14's migration must preserve this entry tuple, its exact-target column, indexes
and guards when adding READY. B14 §12.1 says its READY branch needs no extra event
column; the nullable concrete entry reference below is owned by B14a. It is a
bounded relation on the registered event, not another scientific fact owner.
Jointly reconcile that additive detail before separate execution authorization;
this task does not edit B14 or silently widen READY implementation.

## 3. Invariants and conservative judgments

### 3.1 Exact target and entry gate

Require trusted VerifiedPrincipal, live credential/binding, active membership,
ACTIVE Project and effective RESEARCHER or OWNER role. Human and Agent callers
use the same method and role policy, following B11's snapshot authorization,
which does not impose HUMAN-only approval semantics on commands. The existing
PublicationService._authorize and B04.authorize cannot be copied unchanged:
the former locks the Project and both contain a HUMAN restriction inappropriate
for this command's shared caller policy. No independent approver is needed.

Target must belong to the supplied Publication and Project, be FROZEN with
frozen_at, placement_set_hash, content_hash and sha256-cjson-v1, and match
expected_content_hash. Verify B04's whole closure with admission=True, including
retained document/artifact bytes and current VALID projection. Preserve the B04
same-parent current-pointer invariant; do not use it to select or replace input.
Publication must be DRAFTING. Entry leaves the manuscript, hashes and pointer intact.

Use B11's existing b11_closure/b11_applicable_reviews traversal: exact manuscript,
reachable ClaimVersion, ScientificConclusionVersion and ArtifactVersion review
targets, including the document. Verify matching saved review hashes/attribution
and full Issue/event/disposition history before deriving blockers. Use existing
review-type verification and B08 terminal-history verification; do not trust only
the Issue.status column. Any applicable OPEN BLOCKING Issue denies; unrelated
reviews do not. No reviews is allowed. Unfavorable recommendations, OPEN MINOR
or MAJOR Issues alone do not deny entry. Manuscript Issue disposition remains
outside this slice; neither entry nor RevisionAction closes an Issue.

### 3.2 Atomic retained effect

Update only lifecycle_status to INTERNAL_REVIEW and row_version=OLD+1.
Append exactly one DRAFTING→INTERNAL_REVIEW event with supplied command id,
actual actor, fresh DB time, exact manuscript FK and both basis UUIDs NULL.
The immutable FK resolves its checked hash from the immutable B04 seal.
No copy of manuscript content/hash or grant consumption is created.
Historical success survives later facts; a broken saved seal/graph fails closed.

## 4. Proposed commands, DTOs and historical readback

§11.3 is the exhaustive closed field contract. Command.id is the event ID and
idempotency identity, as caller IDs own immutable Decision results today.
An entitled original actor replaying the same id and normalized material receives
the original EntryReadback. Changed publication, manuscript or expected hash is
IDEMPOTENCY_CONFLICT; another actor/project is FORBIDDEN without material disclosure.
A different id after successful entry is INVALID_STATE_TRANSITION, not replay.

An exact audit query permits any current reader role. It verifies the saved
event/target/initial-history graph in one snapshot. Replay additionally compares
actor and command material. It does not require DRAFTING, a still-live write role,
currently VALID science, absence of later blockers or a still-ACTIVE project.
Read entitlement and actual credential are checked at fresh DB time before
existence disclosure and again before return. Return saved transition facts only;
current lifecycle/validity diagnostics remain existing queries, not saved-result
fields. Missing bytes or invalidity after success are not a second admission gate;
immutable seal/hash corruption remains a provenance error.

## 5. Schema and literal hash proposal — no migration

§12.1 adds only nullable manuscript_version_id UUID to existing events, with a
same-parent concrete FK. It is populated exactly for entry. No new event hash,
request hash, material_version or JSON result is needed: compare the closed
request against immutable event + exact sealed manuscript. Existing manuscript
placement/content hashes and their sha256-cjson-v1 payloads are unchanged.
Do not backfill invented manuscript references onto old creation events.

## 6. Error contract — proposed use of existing categories

§11.2 pins all codes and transport mappings. Authorize before existence disclosure;
validate closed input before DB access; test exact target/state before first-use
hash/closure/blocker checks. Completed event comparison precedes first-use gates.
Corruption is never treated as an ordinary blocker or successful replay.

## 7. Transactions, concurrency and failure recovery

One command is one synchronous write UoW. Use READ COMMITTED with pre-snapshot
exclusion, not SERIALIZABLE grant consumption. Completed replay and exact reads
use one REPEATABLE READ, READ ONLY snapshot with no explicit exclusion locks,
including inside authorization, hydration, Issue histories or closure helpers.
Ordinary PostgreSQL AccessShareLock on SELECT is expected.

Use §12.2's N→W→A before any transactional query. This excludes mutable-input
UPDATEs and zero-row review/Issue INSERT phantoms before the snapshot, avoids a
Publication SHARE→write upgrade, and agrees with B13/B14. Row order is manuscript
then Publication. Failed gate, deferred check or final credential check rolls
back event and status. No status maintenance occurs on reads.

Retry the whole fresh UoW only for SQLSTATE 40001/40P01, at most three total
attempts, rechecking clock/credentials/gates each time. Never retry business
errors or 55P03/57014 timeouts automatically. Named event-PK collision exits the
failed writer and compares in lock-free replay; uniqueness alone proves nothing.
Unknown commit outcome requires same-id read/replay before another effect attempt.
Writer-discovered completed results also exit to a new read UoW before returning.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

§12.4 pins files/cases. Use real PostgreSQL 18.x, Application fixtures and normal
SQL roles. No guard disabling, direct status seeding, SQLite or mocked dependency
acceptance. B14 must construct INTERNAL_REVIEW with this command in its fixtures.

## 9. Acceptance criteria and evidence boundary

After implementation: real create→draft→B04 freeze→entry succeeds without reviews;
applicable blocker denies; exact event/row_version atomicity and entitled replay
are proven. B11→approval→B14 READY uses the real entry prerequisite once READY is
implemented; absence of B14 code blocks that downstream acceptance, not entry's
own bounded tests. All named schema guards, race directions, lock-free reads and
focused regressions must pass with no open P0/P1. This documentation task claims
none of that implementation evidence. Stop after this draft and §14 verification.

## 10. Glossary

| Term | Meaning here |
| --- | --- |
| Publication | Long-lived publication identity and current lifecycle projection. |
| ManuscriptVersion / seal | Exact frozen document/placement/closure identity and B04 hashes. |
| Entry | Single DRAFTING→INTERNAL_REVIEW transition; starts a stage, asserts no completed review. |
| Lifecycle event | Append-only transition fact; also this command's replay result. |
| Applicable blocker | Verified OPEN BLOCKING Issue on B11's finite exact closure. |
| Readiness | B11 judgment and B14 grant-consuming INTERNAL_REVIEW→READY effect, separate from entry. |
| Replay / audit read | Original actor's same command readback / any entitled reader's exact event query. |
| N / W / A | Protected nonwritten scientific/authority inputs / writable Publication / approval compatibility tables. |
| Fresh time | Advancing PostgreSQL clock_timestamp(), not transaction start or caller time. |

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

Adopt §§2–7 as choices awaiting approval: one entry per Publication; exact target;
zero completed reviews allowed; existing finite applicable blockers deny; no
Decision/approval tuple; shared Human/Agent boundary; event-owned idempotency;
read-entitled historical replay; bounded retries; existing SQL lock/trigger
mechanisms. No reset/re-entry or configurable bypass. The additive event FK and
its preservation by B14 require joint freeze before implementation.

### 11.2 Pinned error mappings

Match [HTTP _STATUS](../../src/researchbase/api/errors.py) and
[CLI_EXIT_CODES](../../src/researchbase/cli/errors.py); add no ErrorCode.

| Error code | HTTP status | CLI exit | Trigger |
| --- | --- | --- | --- |
| VALIDATION_ERROR | 422 | 2 | Missing/extra/wrong-type DTO field, malformed UUID/hash. |
| AUTHENTICATION_REQUIRED | 401 | 3 | Missing trusted VerifiedPrincipal. |
| FORBIDDEN | 403 | 3 | Credential/entitlement loss, foreign scope or other-actor replay. |
| NOT_FOUND | 404 | 3 | Authorized exact event/publication/manuscript absent. |
| FROZEN_REFERENCE_REQUIRED | 409 | 5 | First-use manuscript not sealed FROZEN. |
| INVALID_STATE_TRANSITION | 409 | 4 | Publication not DRAFTING, different-id repeated entry. |
| APPROVAL_GATE_FAILED | 409 | 4 | Applicable verified OPEN BLOCKING Issue; existing gate category, no approval implied. |
| CONCURRENT_MODIFICATION | 409 | 4 | First-use expected hash mismatch, optimistic update loss or exhausted retryable SQLSTATE. |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Entitled original actor's same id with changed material. |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Bad saved seal/graph/Issue history, missing admission bytes or inadmissible validity. |
| IMMUTABLE_RECORD | 409 | 4 | Event UPDATE/DELETE or attempted late append. |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Sanitized concrete FK violation. |

Unexpected failures retain HTTP INTERNAL_ERROR/500 and existing CLI fallback
INTERNAL_ERROR_EXIT_CODE=1; INTERNAL_ERROR is not an ErrorCode dictionary entry.
Named new guard constraints map to the categories above in uow.py; no raw SQL or
credential data escapes. Do not collapse provenance errors into gate failure.

### 11.3 DTO fields, Python types and limits

Separate frozen, slotted dataclasses; strict UUID objects in Python, canonical
lowercase hyphenated UUID text at future transport boundaries. Reject unknown
fields/coercion. Hashes are exactly 64 lowercase hexadecimal characters, scheme
exactly sha256-cjson-v1. Times are finite aware UTC datetime; no caller timestamp,
actor, lifecycle enum, review list, grant, narrative or optional material input.
All declared fields are required; no collection or free-text limit is needed.

| DTO | Exhaustive fields and types |
| --- | --- |
| TransitionPublicationInternalReviewCommand | `id: UUID`, `project_id: UUID`, `publication_id: UUID`, `manuscript_version_id: UUID`, `expected_content_hash: str`. |
| GetPublicationInternalReviewEntryQuery | `project_id: UUID`, `id: UUID` (entry event ID). |
| PublicationInternalReviewEntryReadback | `id: UUID`, `project_id: UUID`, `publication_id: UUID`, `manuscript_version_id: UUID`, `manuscript_content_hash: str`, `hash_scheme: Literal['sha256-cjson-v1']`, `prior_status: Literal['DRAFTING']`, `new_status: Literal['INTERNAL_REVIEW']`, `actor_id: UUID`, `occurred_at: datetime`. |

The readback has no current pointer/status or captured validity claim. Server
row_version remains PostgreSQL INT, positive and incremented exactly once; fail
closed on overflow. This slice admits only DRAFTING and INTERNAL_REVIEW lifecycle
states; later READY is B14-owned. Reserved external states remain unavailable.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

One forward revision under migrations/versions/ after the actual head; reserve no
number. Under DDL locks preflight existing creation events, pointers and seals;
abort corrupt legacy history without rewriting it. Preserve B04 freeze/pointer
branches. Replace generated 0035 CHECK/unique constraints by their catalog-verified
names (publications_lifecycle_status_check,
publication_lifecycle_events_new_status_check,
publication_lifecycle_events_check,
publication_lifecycle_events_publication_id_key on this baseline).

```sql
ALTER TABLE publications ADD CONSTRAINT ck_b14a_publication_status
 CHECK (lifecycle_status IN ('DRAFTING','INTERNAL_REVIEW'));
ALTER TABLE publication_lifecycle_events
 ADD COLUMN manuscript_version_id UUID,
 ADD CONSTRAINT fk_b14a_entry_same_parent
 FOREIGN KEY (publication_id,manuscript_version_id)
 REFERENCES manuscript_versions(publication_id,id) ON DELETE RESTRICT,
 ADD CONSTRAINT ck_b14a_event_tuple CHECK (
  (prior_status IS NULL AND new_status='DRAFTING'
   AND manuscript_version_id IS NULL
   AND basis_decision_id IS NULL AND basis_grant_consumption_id IS NULL) OR
  (prior_status IS NOT DISTINCT FROM 'DRAFTING' AND new_status='INTERNAL_REVIEW'
   AND manuscript_version_id IS NOT NULL
   AND basis_decision_id IS NULL AND basis_grant_consumption_id IS NULL)),
 ADD CONSTRAINT ck_b14a_event_time CHECK (isfinite(occurred_at));
CREATE UNIQUE INDEX uq_b14a_initial_event
 ON publication_lifecycle_events(publication_id) WHERE prior_status IS NULL;
CREATE UNIQUE INDEX uq_b14a_review_entry
 ON publication_lifecycle_events(publication_id) WHERE new_status='INTERNAL_REVIEW';
CREATE INDEX ix_b14a_entry_manuscript
 ON publication_lifecycle_events(manuscript_version_id)
 WHERE manuscript_version_id IS NOT NULL;
```

Existing columns retain types: id/publication_id/actor_id UUID NOT NULL;
prior_status VARCHAR(24) NULL, new_status VARCHAR(24) NOT NULL,
occurred_at TIMESTAMPTZ NOT NULL, both basis fields UUID NULL.
Publication.lifecycle_status VARCHAR(24) NOT NULL, row_version INT NOT NULL >0.
Retain event PK and publication/actor RESTRICT FKs, same-parent current pointer,
and pr212_events_immutable. No scientific CASCADE or soft target discriminator.

| Named guard / trigger | Required behavior |
| --- | --- |
| pr212_publication_guard (extend) | Preserve initial INSERT and exact B04 pointer-only update. New entry UPDATE requires READ COMMITTED, preheld §12.2 inventory, OLD=DRAFTING, NEW=INTERNAL_REVIEW, row_version=OLD+1, same nonnull frozen current manuscript and every other column unchanged. Check structural closure/blockers and active effective DB authority. Deny DELETE/unlisted branches. |
| b14a_entry_event_guard, BEFORE INSERT on events | Preserve valid creation insert. Entry requires the Publication UPDATE in this transaction, exact FROZEN same-parent current manuscript, actor/time consistent with effective DB authority and no prior entry. occurred_at must be at least the initial event time and manuscript frozen_at, and no later than clock_timestamp(). Deny late event insertion and mismatched target. |
| b14a_complete_publication, AFTER INSERT OR UPDATE on publications | DEFERRABLE INITIALLY DEFERRED: exactly one valid initial event. Entry UPDATE requires exactly one matching entry event, with both new Publication tuple and event xmin=pg_current_xact_id()::xid, correct chronology/target and final INTERNAL_REVIEW state. B04 pointer-only update does not require entry. |
| b14a_complete_entry_event, AFTER INSERT on events | DEFERRABLE INITIALLY DEFERRED: invoke same final-graph verifier; reject event-only insertion even without Publication UPDATE. Creation requires its new parent and one initial event; entry requires same-transaction effect, no orphan or extra entry. |

Use a shared `b14a_verify_entry(publication_id UUID)` function with
SET search_path = pg_catalog, public, pg_temp. Structural checks reuse B04 seal
verification and B11 finite closure/verified Issue history. Never call admission
checks for an unchanged historical entry simply because today's facts differ.
No trigger-issued late LOCK TABLE substitutes for the FIRST-SQL writer protocol;
verify preheld granted pg_locks and isolation as in b11_require_snapshot.
Database guards cannot authenticate external credentials or read CAS bytes;
Application checks remain required. Use the 0057 xid comparison, not the older
0042 text-bigint form. No session flag bypass.

B14 later widens state/tuple checks, preserves these indexes or explicitly
replaces them with equivalent uniqueness, and preserves the entry reference and
its guards without demanding new receipt fields on entry. READY's manuscript
continues to derive from its receipt; entry's immutable target never derives from
a later live pointer. Downgrade refuses any entry history or dependent later
history; empty-extension downgrade restores validated predecessor guards and
indexes without dropping existing Publication/manuscript/creation history.

### 12.2 Exact lock order and transactions

N below is a frozen literal inventory, equal to current B13_SNAPSHOT_TABLES
in [approval_repository.py](../../src/researchbase/persistence/approval_repository.py)
and B11_SNAPSHOT_TABLES minus publications. Copy the reviewed literal into the
new preparation helper/migration/tests; no runtime catalog discovery or automatic
inheritance of future inventories. All N tables are nonwritten here.

```text
actor_subject_bindings actors artifact_versions artifacts audit_findings
claim_versions claims correction_records dataset_snapshots datasets evidence_relations
experiment_spec_versions experiment_specs impact_assessments impact_targets
internal_review_records literature_evidence literature_evidence_relations
literature_evidence_review_events literature_source_project_links literature_sources
literature_support_snapshots manuscript_artifact_placements manuscript_citation_placements
manuscript_claim_placements manuscript_versions measurements metric_definition_versions
metric_definitions project_membership_events project_memberships project_role_assignments
projects review_issue_events review_issues run_artifact_inputs run_dataset_inputs runs
scientific_conclusion_claim_inputs scientific_conclusion_literature_inputs
scientific_conclusion_versions scientific_conclusions source_versions
statistical_result_inputs statistical_results
```

Freeze N in exactly this order (the existing B13 order). W=`publications`;
A=`approval_decisions,approval_request_reviews,approval_requests` in that order.
A is retained solely to meet B14 §12.2's shared N→W→A protocol, not as an entry
gate. Accepted immutable Decision/basis/disposition histories rely on owning
sealing guards. publication_lifecycle_events is written only after W excludes
participating lifecycle writers; append-only/unique/deferred guards cover SQL
bypasses. No SHARE lock is upgraded on a written table.

Configure connection isolation, autoflush=False and 10s lock/30s statement bounds
before transactional SQL, following uow.configure_revision_transaction and
persistence/database.py. FIRST transactional application SQL is
`LOCK TABLE <N literal> IN SHARE MODE`; next
`LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE`; next
`LOCK TABLE approval_decisions,approval_request_reviews,approval_requests IN SHARE MODE`.
All precede SELECT, advisory calls, SET LOCAL and snapshot creation. Then apply
SET LOCAL timeouts; initial waits rely on the preconfigured bounds.

| Command/path | Exact sequence after configuration |
| --- | --- |
| New transition_publication_internal_review | READ COMMITTED; N→W→A; local timeouts; advisory `b14a:entry:{command.id}`; manuscript FOR UPDATE; supplied Publication FOR UPDATE; enable snapshot-only dependency readers; authorize reader before disclosure, inspect same-id event and exit writer to replay if found; authorize RESEARCHER/OWNER and ACTIVE project at fresh clock; verify target/state/hash/closure/all applicable histories/blockers; take fresh clock and reauthorize; guarded Publication UPDATE and entry INSERT with that actor/time; SET CONSTRAINTS ALL IMMEDIATE; fresh final authority/credential check; commit. |
| get_publication_internal_review_entry / completed replay | One REPEATABLE READ, READ ONLY UoW; snapshot-only dependency readers; plain authority lookup + fresh clock; plain event/Publication/exact manuscript and initial-history reads; verify saved graph/seal (no admission gate); replay additionally compares original actor and material; final fresh read entitlement check; return. No table/advisory/row locks, FOR SHARE/UPDATE, maintenance or writes. |

Advisory SQL is parameter-bound
pg_advisory_xact_lock(hashtextextended(:key,0)); UUID text is canonical. No grant,
request, purpose-scope, consent or package row lock is taken. The command advisory
never precedes table protection. The target row always precedes Publication.

B11/B12 and B09/B10 writers already protect Publication with SHARE; W conflicts
before target/scope waits. B13/B14 use the same N→W→A and manuscript→Publication
order. B04/B05 and upstream review/Issue/validity/authority writers are excluded
by N before entry's first snapshot; retain their owning coordination. Old
parent-first paths can still deadlock: test both orders and bounded whole-UoW
40P01 recovery. Never solve a write race by adding read locks. After any wait
reread affected facts then use clock_timestamp(); final deferred waits require
another check. Locks do not prevent credential/role wall-clock expiry.

### 12.3 Ordered build steps and module paths

1. Freeze B14a/B14 compatibility and actual head. Add one forward file under
   `migrations/versions/` for §12.1; preserve 0035/0048/0049 and 0057 history.
2. Extend `src/researchbase/application/publication.py` with §11.3 DTOs and two
   methods. Use in-UoW B04 verification and refactored existing B11 authority,
   applicable-review and Issue-history helpers from
   `src/researchbase/application/decision.py` and
   `src/researchbase/application/internal_review.py`. Do not create a Decision or
   require B11's nonempty review basis/independence of the entry caller.
3. Extend typed `src/researchbase/application/ports.py` and
   `src/researchbase/persistence/publication_repository.py` for preparation,
   exact event lookup, guarded status/event write and plain history reads.
   Use existing `src/researchbase/persistence/decision_repository.py`,
   `src/researchbase/persistence/internal_review_repository.py` and
   `src/researchbase/persistence/manuscript_freeze_repository.py` read mechanisms.
4. Wire existing transaction/snapshot toggles and named constraint normalization
   in `src/researchbase/persistence/uow.py`; use existing
   `src/researchbase/persistence/database.py` connection bounds. Separate new
   lock-free authorization from PublicationService._authorize; no nested UoW,
   ORM DTOs, Domain framework import or new runtime dependency. Split pure saved-seal
   verification from admission byte/current-validity checks where needed:
   verify_in_uow currently opens artifact bytes even on reads, so it cannot be
   copied unchanged into stable event replay.
5. Add §12.4 tests, record exact focused checks, stop. Future API/CLI adapters
   use §11.2 mappings; routes and CLI commands are not authorized here.

### 12.4 Test artifacts and required cases

Planned files, not present implementation evidence:

| File to add | Required cases |
| --- | --- |
| tests/unit/phase2/test_b14a_entry_contract.py | Closed immutable DTOs, strict UUID/hash, missing/extra/type errors, literal output enums, finite UTC times, exact HTTP/CLI pairs; unchanged B04 hash vectors. |
| tests/integration/phase2/test_b14a_publication_entry.py | Real create/draft/freeze/entry, zero reviews, all recommendations, MINOR/MAJOR allowed; direct/reachable OPEN BLOCKING denial and unrelated Issue ignored; verified terminal upstream history vs corrupt history, manuscript OPEN blocker; wrong project/parent/hash/state, unsealed target, bad closure/bytes/validity; author may enter; Human/Agent same boundary and role/credential bounds; exactly +1 row_version, unchanged pointer/hash, one event, NULL basis fields, rollback at every write/check. |
| tests/integration/phase2/test_b14a_entry_schema.py | Fresh/populated forward upgrade, catalog types/named FK/CHECK/index/trigger, existing B04 pointer freeze and old creation events preserved; normal-role state-only/event-only, wrong target/actor/time, late append, old event reuse, duplicate initial/entry, event edits/deletes, pointer/material mutation and unlisted lifecycle denied; deferred complete graph succeeds only in same transaction; wraparound-safe xid and downgrade retention. |
| tests/integration/phase2/test_b14a_entry_replay.py | Same actor/id/material stable; changed target/parent/hash conflicts; other actor/project nondisclosure; different id after entry denied; replay after write-role/project-active loss with live reader, invalidity/new blocker/byte loss returns saved facts; read/credential loss denies; corrupt saved seal/graph fails closed; uncertain commit/restart, simultaneous duplicate collision readback; later READY replay through real B14 once available. |
| tests/integration/phase2/test_b14a_entry_concurrency.py | Separate PIDs/barriers and pg_locks/pg_blocking_pids prove FIRST-SQL N→W→A, READ COMMITTED, manuscript→Publication; same id one effect, changed material conflict, competing ids one winner; zero-review INSERT phantom and Issue/validity/authority/B04/B05/B11/B13 writer races both orders; waits spanning credential/role expiry including deferred checks deny atomically; ≤3 SQLSTATE retries, no timeout retry; exact reads/replay have no explicit exclusion locks even during concurrent writes. |
| tests/architecture/test_b14a_entry_boundaries.py | Shared Application path, no nested transactions/ORM leak/semantic JSON/new receipt store, exact FK history, no read-side locks or writes including helpers, no new approval tuple or external effect. |

Run new tests plus existing publication draft/migration, B04 freeze/migration/races,
B05 review/basis/migration/races, B11 Decision/schema/replay/races and affected
B09/B10/B12/B13 lock/approval regressions. Run Ruff check/format, Pyright,
unit/architecture and git diff --check; retain exact results. Missing downstream
B14 acceptance stays explicitly unrun; the owner's loop owns whole-suite evidence.

### 12.5 Not in this slice

| Deferred behavior | Owning boundary |
| --- | --- |
| INTERNAL_REVIEW→READY, grant consumption and readiness reevaluation | B14/B13; no automatic promotion. |
| New/revised manuscript, reset, re-entry, withdrawal, archive or supersession | Later lifecycle contract must amend one-entry uniqueness and continuity. |
| Review/Issue creation or disposition, Decision/approval/rejection implementation | Existing owning commands/contracts; no implicit favorable judgment or concern closure. |
| Prepared package/authorship/consent, submission/venue send or ExternalEffect | Separate package/external contracts. |
| API/CLI routes, generic status setter, list/bulk operation, background job/outbox | Separate authorization; no infrastructure/dependency addition. |

## 13. Open questions for the owner — override register

| Owner decision before implementation | Adopted draft answer |
| --- | --- |
| Entry requires completed reviews or readiness permission? | No; frozen-valid closure and absence of applicable blockers suffice. Review/Decision/Approval remain distinct. |
| Exact entry target retention and B14 compatibility? | Add nullable same-parent manuscript FK to the existing event; jointly preserve it and the entry guards when B14 widens lifecycle checks. |
| Repeated entry cycles? | One entry per Publication; reset/re-entry requires a separate amendment. |

These choices await approval; none authorizes implementation or changes governing architecture.

## 14. Documentation verification note

Only this proposal is authored. B14a code, migrations and planned tests above are
not implemented. Documentation-task commands and observed results follow.

Verification on 2026-10-17 used the installed shared environment without sync.
Each uv command below used this common environment prefix:

```sh
UV_CACHE_DIR=/tmp/researchbase-b14a-uv-cache UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv
```

| Exact command after common prefix | Observed result |
| --- | --- |
| `uv run --no-sync ruff check .` | All checks passed. |
| `uv run --no-sync ruff format --check .` | 626 files already formatted. |
| `uv run --no-sync pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject` | 0 errors, 0 warnings, 0 informations. |
| `PYTHONPATH=src RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run --no-sync pytest tests/unit tests/architecture --tb=short` | 4,984 passed, 4 failed, 12 errors, 8 warnings in 60.54s; not PASS. |
| `PYTHONPATH=src uv run --no-sync pytest tests/unit/phase2/test_b04_manuscript_contract.py tests/unit/phase2/test_b04_manuscript_hash_vectors.py tests/unit/phase2/test_b05_review_contract.py tests/unit/phase2/test_b05_review_hash_vectors.py tests/unit/phase2/test_b11_readiness_contract.py tests/unit/phase2/test_b11_readiness_hash_vectors.py tests/architecture/test_b04_boundaries.py tests/architecture/test_b05_review_boundaries.py tests/architecture/test_b11_readiness_boundaries.py tests/architecture/test_b13_grant_boundaries.py --tb=short` | 219 passed, 2 warnings in 1.08s. |
| `PYTHONPATH=src DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run --no-sync pytest tests/integration/phase2/test_pr2_12_publication_draft.py tests/integration/phase2/test_pr2_12_migration.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b04_manuscript_races.py tests/integration/phase2/test_b05_manuscript_review.py tests/integration/phase2/test_b05_review_basis.py tests/integration/phase2/test_b05_review_races.py tests/integration/phase2/test_b11_readiness_decision.py tests/integration/phase2/test_b11_readiness_schema.py tests/integration/phase2/test_b11_readiness_races.py -x --tb=short` | 1 setup error in 0.63s; stopped, remaining cases not run. |

The four failures in tests/unit/test_hg1_runner.py are sandbox-denied Unix socket
binds (Operation not permitted). The twelve architecture errors are
PR2-19 PostgreSQL fixtures denied localhost connections. The focused PostgreSQL
run stopped on that same denial before database assertions; server version and
PostgreSQL acceptance were not verified. Warnings are existing Alembic
path_separator deprecations. No whole-suite run was made; the owner's loop owns
that evidence.

`git diff --check` and
`git diff --no-index --check /dev/null docs/proposals/B14a_Publication_Internal_Review_Entry_Contract_DRAFT.md`
reported no whitespace errors. A local `python3` pathlib/regex/AST check resolved
35 relative links, matched all 12 HTTP/CLI pairs against the source dictionaries,
and verified the required status and 14 numbered sections. The literal N inventory
was compared with current B13_SNAPSHOT_TABLES. `git status --short` showed only
this new proposal. No code, migration, test, dependency or governing file changed;
no commit, push, branch or implementation acceptance is claimed.
