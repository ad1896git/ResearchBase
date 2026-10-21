# B14 Publication READY Transition Contract — DRAFT

**Status: APPROVED by owner 2026-10-18 — first slice authorized for implementation**

Implementation evidence and reconciled names: [B14 READY first slice](../phase2/B14-ready-evidence.md).

## Start here (for the implementer)

B14 makes one Publication move INTERNAL_REVIEW→READY using one exact manuscript's
READY_FOR_SUBMISSION grant. The lifecycle event, B13 receipt, consumed grant and
grant event commit together. READY records an internal gate; scientific validity
still derives from canonical facts. It grants no package-preparation or sending
permission.

Read §§1–4 first, use §10 for terms, §11 for fixed draft decisions and §12 for the
build plan. The owner reports Batch C (B07–B11) contracts approved and their code
under parallel implementation. Use those contracts where code is absent. B13 is
draft; **jointly freeze B13's READY branch and this contract** before separate
implementation authorization. Approval of this draft alone authorizes no code.

Build in this order after authorization:

1. Reconcile B11/B09/B10/B08 implementations, B13 receipt ownership and the missing
   INTERNAL_REVIEW entry prerequisite (§§2, 12.1); check the actual migration head.
2. Extend existing publication events and guards; add concrete deferred receipt
   binding and bidirectional completeness, preserving existing history (§12.1).
3. Add the closed command and stable B13 result projection (§11.3) through the
   existing Application/port/repository paths (§12.3).
4. Use B13's exact pre-snapshot protection and lock order (§12.2). First use is
   SERIALIZABLE; reads/replay use one lock-free REPEATABLE READ snapshot.
5. Execute §12.4 tests and focused regressions, retain exact evidence and stop at
   §12.5. Missing dependencies are blockers, never mocked acceptance.

Five rules whose violation fails review:

1. Only the exact frozen manuscript, its Publication and the finite readiness
   Decision/request/grant tuple may produce READY.
2. Recheck full closure, independent basis, later reviews, applicable blockers,
   rejection fence and live authority; earlier approval cannot override facts.
3. One transition equals one event and one exact consumption in the same UoW;
   neither an event nor a receipt may be appended later to repair partial success.
4. Expiry is decided using fresh database time after required waits and before
   the effect, with final checks after deferred constraints.
5. Completed replay is entitled historical readback, with no exclusion locks,
   new consumption, lifecycle change or first-use gate reevaluation.

## 1. Purpose, authority and inspected baseline

| Authority | Constraint carried forward |
| --- | --- |
| [System 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 7–13; [Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A17–A23 | Deterministic facts precede authority; immutable exact provenance; Review ≠ Decision ≠ Approval ≠ Command ≠ ExternalEffect; bounded schema admission. |
| [Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md); [Cross-Phase 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§9–18, 24, 28 | Reuse Publication, lifecycle events and ApprovalGrantConsumption; concrete RESTRICT FKs and the common Application boundary. |
| [Phase 2 specification 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), publication/governance and PR2-16/17; [Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), §§4, 6–7 | DRAFTING→INTERNAL_REVIEW requires a frozen manuscript; INTERNAL_REVIEW→READY consumes readiness permission; preparation and external submission remain separate. |
| [Field contract 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md), publication/approval rows; [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md), governance/manuscript payloads | Existing lifecycle columns, append-only events, exact typed dependencies and unchanged scientific hashes. |
| [Governance R2 17](../architecture/17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md), §1; [R3 18](../architecture/18_Phase2_Design_R3_Targeted_Remediation_v1.0.md), §5; [Temporal R4 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md), §§1, 4–5 | Finite readiness tuple, independent HUMAN approver, atomic event/consumption, literal normalized request, SERIALIZABLE effect and post-wait clock; historical replay. |
| [B11](B11_Ready_For_Submission_Decision_Contract_DRAFT.md), §§3–5, 11–12; [B09](B09_Approval_Tuples_Contract_DRAFT.md); [B10](B10_Rejection_Reconsideration_Contract_DRAFT.md); [B08](B08_Issue_Disposition_Contract_DRAFT.md) | Exact readiness judgment and complete basis; finite approval/rejection fence; verified concern history. Owner-reported approval takes precedence over retained DRAFT labels. |
| [B13](B13_Grant_Consumption_Contract_DRAFT.md), §§3–7, 11–12; [Harness 09](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 18–21 | B13 owns receipt/hash/grant lifecycle; B14 binds READY effect/event; joint freeze, common UoW and evidence before acceptance. |

Inspected branch, 2026-10-16: [0035](../../migrations/versions/0035_pr2_12_publication_draft.py)
creates Publication and publication_lifecycle_events with DRAFTING-only checks,
one event per Publication, and unbound nullable basis UUIDs.
[0048/B04](../../migrations/versions/0048_b04_manuscript_freeze.py) adds manuscript
seal/current-pointer guards, but no INTERNAL_REVIEW entry or READY transition.
[0049/B05](../../migrations/versions/0049_b05_manuscript_review.py) supplies manuscript
reviews and OPEN Issue history. [0045](../../migrations/versions/0045_pr2_16_basic_approval.py)
is release-only approval, without consumption. Migration inventory reaches 0051/B06.

[PublicationService](../../src/researchbase/application/publication.py) and
[publication repository](../../src/researchbase/persistence/publication_repository.py)
provide draft commands/reads. Their authorization helper locks project state;
it cannot be reused unchanged for B14's lock-free reads.
[Decision](../../src/researchbase/persistence/decision_repository.py),
[novelty](../../src/researchbase/persistence/novelty_repository.py) and
[B04 repository](../../src/researchbase/persistence/manuscript_freeze_repository.py)
provide existing table-lock mechanisms; B04/novelty coverage demonstrate SHARE as
FIRST SQL. Older target-first paths are not the new sequence.
[0042](../../migrations/versions/0042_pr2_15_minimal_decision.py) demonstrates deferred
final-graph triggers and current-transaction child sealing. No B14 execution pack
was found. Contract approval, source presence and acceptance are distinct.

## 2. Scope, dependency boundaries and non-goals

Add only `transition_publication_ready` and exact `get_publication_ready_transition`
to PublicationService. B13 owns the consumption operation and replay verifier;
there is no second receipt store or public generic consume command. Reuse the
registered PublicationLifecycleEvent; add no canonical schema or infrastructure.

B11 is required for the affirmative readiness Decision; B09/B10 for finite
approval and rejection coordination; B08 for interpreting accepted terminal
upstream Issue history; B04/B05 for seal/reviews. B07 revision judgments do not
replace any of these. Manuscript Issue disposition is still deferred by B08;
original OPEN manuscript blockers deny. Do not implement missing Batch C code here.

**Entry prerequisite:** this branch has no authorized command that establishes
INTERNAL_REVIEW. Correction 12 defines its required frozen-manuscript gate, but
does not supply its DTO/event/replay/lock contract. B14 does not invent that
command or automatically promote DRAFTING. Require a separately approved entry
contract and its real Application fixture before migration/READY acceptance;
joint freeze must name its owning execution slice. Do not bypass guards in tests
to manufacture an accepted INTERNAL_REVIEW state. This is an explicit dependency
gap for owner disposition (§13), not implicit implementation scope.

B13's release and package branches remain separately bound dependencies. This
READY-only contract cannot fulfill B13's requested package/consent binding or
declare all B13 branches accepted. No package schema, consent, freeze, supersession,
withdrawal, reset, archive, venue send or external effect belongs here.

## 3. Invariants and conservative judgments

### 3.1 Exact target and gate

First use requires ACTIVE Project and a trusted live VerifiedPrincipal with
effective RESEARCHER or OWNER authority. Human and Agent callers use the same
Application method and policy; an Agent is not an independent HUMAN approver.
Derive target from the immutable grant→ApprovalDecision→ApprovalRequest chain:
purpose READY_FOR_SUBMISSION, allowed_command `transition_publication_ready`,
max_uses=1, finite unexpired ACTIVE grant, exact manuscript ID/hash/scheme,
result Publication equal to manuscript.publication_id and supplied Project.

Publication must be INTERNAL_REVIEW. Verify the exact FROZEN manuscript's B04
seal, placement/document and transitive scientific/literature closure, retained
artifact bytes and current VALID projection. Preserve B04's current-pointer
invariant; do not use the pointer to choose a target or silently substitute it.
If later accepted lifecycle permits exact sealed SUPERSEDED navigation, follow
B13: navigation alone does not invalidate frozen provenance; actual new-target
selection for this purpose stales unused permission. B14 adds no supersession.

Require the same-Project B11 READY_FOR_SUBMISSION/PROCEED Decision, exact typed
manuscript/review basis and verified literal hashes. Request-bound review set
equals its Decision's complete saved manuscript review basis and the command's
checked_review_ids. Verify all later exact-target reviews without adding them to
the immutable saved basis/receipt. All review recommendations remain visible;
recommendation alone is neither veto nor scientific truth.

Use B11 §3.2's finite applicable-blocker traversal: exact manuscript plus reachable
ClaimVersion, ScientificConclusionVersion and ArtifactVersion review targets from
the verified B04 closure, including the document. Verify Issue/event/disposition
history before excluding a closed concern. Any applicable OPEN BLOCKING Issue
denies. Do not widen reachability by shared identity/text or treat a RevisionAction
or favorable Decision as Issue closure. Corruption fails closed.

Recheck B09/B10's Project/purpose rejection fence and selection staleness. Require
issuing independent HUMAN's effective APPROVER authority and actual trusted
credential at fresh database time; preserve all requester/reviewer/decider/material
author independence rules. OWNER role accumulation cannot replace independent
approval. B09 permits requires_current_author_consent=false only for this tuple;
no consent subsystem or free-text condition is introduced for READY.

### 3.2 Atomic effect and retained history

Update only Publication.lifecycle_status to READY and increment row_version by
one; retain identity, metadata and current manuscript pointer. Append exactly one
INTERNAL_REVIEW→READY event with actual actor/time, basis_decision_id equal to the
request's B11 Decision and basis_grant_consumption_id equal to the new B13 receipt.
Receipt command is TRANSITION_PUBLICATION_READY, result_publication_id is that
Publication, other result FKs null. Event actor/time equals receipt actor/consumed_at
and the consumed grant event actor/time. Preallocate IDs to resolve deferred FKs.

All five changes (Publication, lifecycle event, receipt referencing the sealed
request reviews, grant status, grant event) commit in one UoW. Validate both directions, including
same-transaction creation; existing historical receipts cannot authorize a new
transition. No failed gate leaves a partial event, receipt or terminal maintenance.
Historical READY is retained if later facts become invalid; current diagnostics
report those facts without rewriting state, hashes, consumed grant or saved DTO.

## 4. Proposed commands, DTOs and historical readback

§11.3 pins closed immutable fields. Principal is separate and trusted. A first
command returns B13 ConsumptionReadback with its stable READY result; the exact
read accepts project_id and consumption_id and returns that receipt plus its
unique lifecycle event. B13's command-key audit read remains available through
its own boundary. No list, bulk transition or public generic status setter.

Readers require live project OWNER, RESEARCHER, REVIEWER, VIEWER or APPROVER
entitlement before existence disclosure. Completed replay additionally requires
original actor/project and matching normalized material. Verify saved receipt,
Decision/review membership/hashes and event/grant graph. Current roles needed to
write, expiry, new blockers and current scientific validity are not historical
replay gates. Read current validity/status separately with evaluated_at; never
overwrite the stable saved result. Recheck read entitlement at final fresh time.

## 5. Schema and literal hash proposal — no migration

§12.1 extends existing event FKs/checks and guards. The exact manuscript is reached
through event→consumption→grant→request.manuscript_version_id; Decision is a concrete
FK. No extra target discriminator/hash column, READY snapshot or semantic JSON.
B13's result_dto JSONB is only a versioned projection checked against concrete
FKs, not a second owner of readiness or scientific facts.

Use exactly R3 18 §5's ApprovalGrantConsumptionRequest material_version=1 with
command TRANSITION_PUBLICATION_READY, authenticated actor, project/grant, derived
exact ManuscriptVersion ref, Publication result_id, null
expected_package_manifest_hash and canonical sorted checked_review_ids. The
command key, consumption/event IDs and timestamps are not hash fields. Compare
normalized scope as well as digest on replay. Preserve R2/R3 golden vectors,
Phase 1, manuscript, Decision and ApprovalDecision payloads byte for byte. Add no
Publication or lifecycle-event hash algorithm.

## 6. Error contract — proposed use of existing categories

§11.2 matches source mappings; no new ErrorCode. Use named-constraint/SQLSTATE
normalization through the UoW, never raw driver-message matching. Unexpected
failures remain sanitized HTTP 500/CLI exit 1. No SQL, credentials or CAS paths
in public errors. Denied consumption rolls back; it cannot secretly commit B13
maintenance in another transaction.

## 7. Transactions, concurrency and failure recovery

First use is one synchronous SERIALIZABLE UoW as required by R3/B13. B09/B11's
READ COMMITTED write pattern supplies the same FIRST-SQL SHARE mechanism; it
does not authorize downgrading consumption isolation. §12.2 excludes mutable
inputs and approval/rejection phantoms before the SERIALIZABLE snapshot. No
artifact writes or external calls occur inside this database transaction.

Replay preflight is one REPEATABLE READ, READ ONLY UoW. Same key/material returns
saved result; changed material for the entitled original actor/project conflicts.
Other actor/project is nondisclosing FORBIDDEN. Different key is first use and
cannot reuse CONSUMED permission. Missing receipt enters first use; incomplete or
corrupt saved graph fails closed. If a writer discovers committed duplicate key,
close that UoW and use the lock-free replay path; never return replay from a
locking verifier or call every unique violation success.

Retry only SQLSTATE 40001/40P01, at most three total fresh-UoW attempts, no delay.
Redo all locks, durable reads, closure and time-sensitive checks. No automatic
retry for timeout, business conflict or uncertain commit; recover uncertain commit
with the original key. Force SET CONSTRAINTS ALL IMMEDIATE before final fresh-clock
authorization and commit. Every further required wait repeats affected checks;
SERIALIZABLE changed-row conflicts require abort/retry, not a claimed snapshot
refresh. Equality at expiry denies; now()/transaction_timestamp() never decide
expiry. Any final failure rolls back the entire effect.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

§12.4 fixes files/cases. Use real PostgreSQL 18.x for migrations, direct-SQL
constraints, atomicity and concurrent waits. No SQLite, fake receipt/effect,
disabled trigger fixture or sleep-only concurrency proof constitutes acceptance.

## 9. Acceptance criteria and evidence boundary

Joint owner freeze of B13/B14 READY binding, explicit entry-prerequisite ownership
and separate execution authorization precede implementation. Require complete
concrete FKs/deferred graph guards, real command-path fixtures and successful
focused static/unit/architecture/PostgreSQL evidence with no open P0/P1. Reconcile
the actual head and participating writers rather than assuming parallel code has
landed. No READY-only acceptance implies package/send, full B13 or Phase 2 exit.
The owner's loop owns the whole-suite run; this task must not run it.

## 10. Glossary

| Term | Meaning here |
| --- | --- |
| Readiness Decision | B11's immutable exact-manuscript judgment; it changes no lifecycle. |
| READY grant | B09's one-use authorization for the readiness command only. |
| Consumption / receipt | B13's immutable key/hash/result binding committed with the effect. |
| Lifecycle event | Existing append-only Publication history, citing Decision and consumption. |
| Complete basis / later reviews | Saved Decision/request review membership versus additional current gate inputs. |
| Historical integrity / current validity | Saved provenance integrity versus today's deterministic projection. |
| N / W / A | Fixed input SHARE / Publication write / approval SHARE table inventories in §12.2. |
| Replay | Original actor's matching completed request under current read entitlement. |

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

| Choice | Adopted decision |
| --- | --- |
| Effect | Exactly INTERNAL_REVIEW→READY, no automatic entry or reset. |
| Dependencies | Approved Batch C contracts; B13 READY binding jointly frozen. Missing entry contract/implementation blocks deployment and acceptance. |
| Caller / approver | Live RESEARCHER/OWNER caller; independently issued HUMAN APPROVER permission under B09. |
| Gate | B11 basis/reachability plus B09/B10 fence and B13 first-use checks, including later reviews. |
| Persistence | Existing Publication/event/receipt chain; one transaction, concrete FKs, deferred completeness. Adopt B13 §11.1 option (a): derive checked reviews through grant→approval decision→request→approval_request_reviews, cross-check decision_basis_reviews; no consumption-review table. |
| Consent / packages | No readiness consent condition; package and consent bindings require another authorized slice. |
| Transport | Application methods only; future adapter mappings pinned below, routes/CLI deferred. |

### 11.2 Pinned error mappings

Matches [api/errors.py](../../src/researchbase/api/errors.py) and
[cli/errors.py](../../src/researchbase/cli/errors.py).

| Code | HTTP | CLI exit | Trigger |
| --- | --- | --- | --- |
| AUTHENTICATION_REQUIRED | 401 | 3 | Missing/unverifiable principal. |
| FORBIDDEN | 403 | 3 | Caller authority/read entitlement or replay actor/project mismatch. |
| VALIDATION_ERROR | 422 | 2 | Wrong/extra fields, malformed UUID/hash or duplicate/oversize review set. |
| NOT_FOUND | 404 | 3 | Entitled exact grant/receipt/result absent. |
| CONFLICT_OF_INTEREST | 403 | 3 | Required independence fails. |
| APPROVAL_PURPOSE_TARGET_COMMAND_INVALID | 409 | 4 | Well-formed scope outside readiness tuple. |
| DECISION_BASIS_INVALID | 409 | 4 | Wrong/incomplete affirmative Decision or review basis. |
| APPROVAL_GATE_FAILED | 409 | 4 | Publication not INTERNAL_REVIEW, inactive Project, blocker or missing dependency. |
| APPROVAL_TARGET_STALE | 409 | 4 | First-use target seal/hash/state/current validity mismatch. |
| REJECTION_RECONSIDERATION_REQUIRED | 409 | 4 | Unresolved Project/purpose rejection fence. |
| GRANT_INVALID | 409 | 4 | Expired, CONSUMED or REVOKED first use without matching receipt. |
| GRANT_STALE | 409 | 4 | Stored STALE or effective issuer/material staleness. |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Same key, entitled actor/project, changed normalized material. |
| IMMUTABLE_RECORD | 409 | 4 | Event/receipt edit, late history append or terminal rewrite. |
| CONCURRENT_MODIFICATION | 409 | 4 | Exhausted 40001/40P01 or concurrent update conflict. |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Corrupt saved hash/event/receipt/closure. |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Exact concrete FK/parent inconsistency. |

Use B13 evaluator precedence (expiry before effective staleness); specific first-use
gate codes remain available. A new key when Publication is already READY fails
APPROVAL_GATE_FAILED with unused permission; an already consumed grant fails
GRANT_INVALID. Completed matching replay is checked before these first-use gates.

### 11.3 DTO fields, Python types, limits and enums

Frozen, slots, closed dataclasses; uuid.UUID internally, canonical UUID text at
future transports; strict types, no bool/int coercion. No caller actor/time/status,
row_version, reason or arbitrary effect arguments. All fields below are required,
including explicit null; command and manifest-null constants are derived by the
owning method, not accepted as user-selected policy.

| DTO / fields | Type and rule |
| --- | --- |
| TransitionPublicationReadyCommand: command_key, project_id, grant_id, result_id | UUID each; result_id must equal exact target manuscript's Publication. |
| TransitionPublicationReadyCommand: checked_review_ids | tuple[UUID, ...], 1..100 distinct; required, canonical set order; equals saved request review set. Reject 101, duplicates and missing array, never truncate. |
| Derived R3 command / expected_package_manifest_hash | Literal['TRANSITION_PUBLICATION_READY'] / None; both present in normalized hash material. |
| Derived R3 target | Closed type Literal['ManuscriptVersion'], id UUID, content_hash str of 64 lowercase hex; derived from verified request. |
| GetPublicationReadyTransitionQuery | project_id UUID, consumption_id UUID; no filters. |
| Stable saved result v1 (B13, unchanged) | command Literal['TRANSITION_PUBLICATION_READY'], publication_id UUID, consumption_id UUID. Version strict int=1, persisted SMALLINT. No additional event/status fields in saved v1. |
| ReadyTransitionReadback | B13 ConsumptionReadback plus event_id UUID, publication_id UUID, basis_decision_id UUID, manuscript_version_id UUID, actor_id UUID, occurred_at aware UTC datetime.datetime, prior_status Literal['INTERNAL_REVIEW'], new_status Literal['READY']. All reconstructed from concrete history. |
| Separate current diagnostics | publication_status str from accepted lifecycle enum, target_validity Literal['VALID','STALE','INVALID'], blocking_issue_ids tuple[UUID, ...] sorted by canonical UUID, evaluated_at aware UTC datetime; not saved receipt material. |

New receipt admission limit 100 matches B09/B13. Diagnostics are complete/uncapped;
historical verified sets are not retroactively truncated. Lowercase grant command
and uppercase receipt command are distinct pinned representations. Only DRAFTING,
INTERNAL_REVIEW and READY are admitted lifecycle states for the prerequisite plus
this slice; reserved SUBMITTED/ACCEPTED/PUBLISHED stay unavailable, as do other
uncontracted transitions. Existing grant five-state enum and finite 720-hour
maximum remain B09/B13-owned. No new text limit or timestamp input is introduced.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

Forward revision only after accepted dependencies and an approved implemented
INTERNAL_REVIEW entry slice. Reserve no migration number. Preflight existing
events/pointers/receipt graph under DDL locks; reject corrupt history without
rewriting it. Preserve 0035 creation events and B04 seal/pointer checks. Replace
0035's generated DRAFTING-only status/event CHECKs and UNIQUE(publication_id)
with the final constraints below; inspect their actual catalog names at migration
authoring. The entry tuple below is **preserved prerequisite behavior**, not
authorization to implement its command in B14.

```sql
ALTER TABLE publications ADD CONSTRAINT ck_b14_publication_status
 CHECK (lifecycle_status IN ('DRAFTING','INTERNAL_REVIEW','READY'));
ALTER TABLE publication_lifecycle_events
 ADD CONSTRAINT fk_b14_ready_decision FOREIGN KEY (basis_decision_id)
 REFERENCES decision_records(id) ON DELETE RESTRICT,
 ADD CONSTRAINT fk_b14_ready_consumption FOREIGN KEY (basis_grant_consumption_id)
 REFERENCES approval_grant_consumptions(id) ON DELETE RESTRICT
 DEFERRABLE INITIALLY DEFERRED,
 ADD CONSTRAINT ck_b14_event_tuple CHECK (
  (prior_status IS NULL AND new_status='DRAFTING'
   AND basis_decision_id IS NULL AND basis_grant_consumption_id IS NULL) OR
  (prior_status IS NOT DISTINCT FROM 'DRAFTING' AND new_status='INTERNAL_REVIEW'
   AND basis_decision_id IS NULL AND basis_grant_consumption_id IS NULL) OR
  (prior_status IS NOT DISTINCT FROM 'INTERNAL_REVIEW' AND new_status='READY'
   AND basis_decision_id IS NOT NULL AND basis_grant_consumption_id IS NOT NULL)),
 ADD CONSTRAINT ck_b14_event_time CHECK (isfinite(occurred_at));
CREATE UNIQUE INDEX uq_b14_initial_event ON publication_lifecycle_events(publication_id)
 WHERE prior_status IS NULL;
CREATE UNIQUE INDEX uq_b14_review_entry ON publication_lifecycle_events(publication_id)
 WHERE new_status='INTERNAL_REVIEW';
CREATE UNIQUE INDEX uq_b14_ready_event ON publication_lifecycle_events(publication_id)
 WHERE new_status='READY';
CREATE UNIQUE INDEX uq_b14_ready_consumption
 ON publication_lifecycle_events(basis_grant_consumption_id)
 WHERE basis_grant_consumption_id IS NOT NULL;
CREATE INDEX ix_b14_event_decision ON publication_lifecycle_events(basis_decision_id)
 WHERE basis_decision_id IS NOT NULL;
```

Existing types remain: event id/publication_id/actor_id/basis IDs UUID,
prior_status nullable VARCHAR(24), new_status VARCHAR(24) NOT NULL,
occurred_at TIMESTAMPTZ NOT NULL; Publication lifecycle_status VARCHAR(24) and
row_version INT NOT NULL positive. Existing publication/actor FKs retain RESTRICT.
No new event column is needed. B13 supplies its named receipt constraints and
concrete result_publication_id FK. One-READY uniqueness is bounded to this slice;
future READY→DRAFTING/re-entry needs a separately approved history amendment.

| Named guard / trigger | Required behavior |
| --- | --- |
| pr212_publication_guard (extend current definition) | Preserve creation/B04 pointer/prerequisite entry branches; only new branch is INTERNAL_REVIEW→READY, row_version=OLD+1, all other columns unchanged. Deny DELETE and every unlisted transition. Require §12.2 preheld locks/SERIALIZABLE, complete first-use structural gates and actual ACTIVE grant before effect; no session bypass flag. |
| b14_ready_event_guard | BEFORE INSERT: validate real entry/creation or READY provenance, same Project/Publication/manuscript/Decision, actual transition in this transaction and actor/time. READY event cannot be a later append. Preserve pr212_events_immutable for UPDATE/DELETE. |
| b14_complete_publication | AFTER INSERT OR UPDATE ON publications, DEFERRABLE INITIALLY DEFERRED: one initial event and accepted continuous entry history; READY iff one complete READY event/receipt graph. For the new READY update, require event/receipt/grant terminal event from this transaction. |
| b14_complete_ready_event | AFTER INSERT ON publication_lifecycle_events, DEFERRABLE INITIALLY DEFERRED: reject orphan event even when no Publication UPDATE occurs; validate exact final state and complete graph. |
| b14_complete_ready_consumption | AFTER INSERT ON approval_grant_consumptions, DEFERRABLE INITIALLY DEFERRED: dispatch TRANSITION_PUBLICATION_READY to same graph verifier; exactly one event and Publication effect, not just a matching result UUID. Other commands remain B13-owned. |
| B13 complete grant/receipt/event triggers | CONSUMED iff complete unique receipt and terminal event; sealed request-review/Decision-basis equality via B13 §11.1, literal hash and saved result v1. B14 must be invoked from the READY dispatch, with no missing-effect fallback. |

The graph verifier requires consumption.result_publication_id=event.publication_id
=request manuscript's parent, matching project/purpose/command/hash, event Decision
=request.basis_decision_id, B11 exact basis, matching actor/time, checked reviews
and exactly one ACTIVE→CONSUMED grant event. It checks same-transaction effect,
receipt and events using the existing 0042 xmin/current-transaction pattern; an
old receipt/event or a second status change in the transaction cannot satisfy it.
Retain initial/entry history and verify continuity; do not require today's state
to equal READY forever in future historical read logic. Functions use
SET search_path = pg_catalog, public, pg_temp. Normal-role direct SQL must satisfy
the same preheld locks, isolation and final structural graph; database guards
do not claim to authenticate external credentials or inspect CAS bytes.

Downgrade refuses any entry/READY or consumption-dependent history loss. Only an
empty affected extension may restore predecessor guards/indexes after validation;
never delete/rewrite events or null receipt references to force downgrade.

### 12.2 Exact lock order and transactions

Pin literal inventories in adapter/migration/tests, using existing SQL table locks.
For this READY branch, N is sorted unique B04_SNAPSHOT_TABLES from
manuscript_freeze_repository.py plus `manuscript_versions`,
`internal_review_records`, `review_issues`, `review_issue_events`.
W is `publications`. A, in order, is `approval_decisions`,
`approval_request_reviews`, `approval_requests`. This is exactly B13's READY
inventory. Freeze the expanded N as a literal tuple when implementation is
authorized; no catalog discovery or automatic inheritance of later B04 changes.
N/A are never written here; Publication appears only in W, avoiding lock upgrades.
Accepted immutable Decision/basis/disposition histories use their owning sealed
guards; any later mutable input must undergo joint inventory review before use.

Configure isolation/autoflush and server/connection timeouts before UoW entry,
without snapshot-producing SQL. FIRST application SQL is
`LOCK TABLE <N, sorted> IN SHARE MODE`. Next
`LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE`, then
`LOCK TABLE approval_decisions,approval_request_reviews,approval_requests IN SHARE MODE`.
All table locks precede SELECT, advisory calls, SET LOCAL and snapshot creation.
Then SET LOCAL lock_timeout='10s', statement_timeout='30s'; initial waits need
the preconfigured bounds because later SET LOCAL cannot bound them retroactively.

| Command/path | Exact sequence |
| --- | --- |
| transition_publication_ready, absent completed receipt | begin_serializable before SQL; N→W→A as above; local timeouts; advisory b13:consume:{command_key}; plain grant/request routing lookup; advisory pr216:scope:{project_id}:READY_FOR_SUBMISSION; exact manuscript FOR UPDATE; owning Publication FOR UPDATE; request FOR SHARE; grant FOR UPDATE; reread all protected state; authorize reader then RESEARCHER/OWNER and all first-use gates at fresh clock; preallocate consumption/event IDs; update Publication, insert lifecycle event, receipt after verifying UUID-sorted existing request reviews, validated grant terminal event and CONSUMED update; force deferred checks; final advancing-clock authorization; commit. |
| get_publication_ready_transition / completed replay / B13 exact receipt audit read | One REPEATABLE READ, READ ONLY UoW; plain receipt/scope, UUID-sorted existing request-review joins through the immutable grant/decision/request chain and exact event/result reads; saved graph/hash checks; fresh entitlement/current diagnostics, final entitlement check. No LOCK TABLE, advisory lock, FOR UPDATE/FOR SHARE, status maintenance or locking helper, including authorization. |

Advisories use parameter-bound pg_advisory_xact_lock(hashtextextended(:key,0))
with canonical UUID text. Do not introduce a b14 scope namespace. No package or
consent row/table locks are taken by READY. Preflight replay is the read sequence;
writer duplicate detection exits to that sequence, never returns under locks.

| Participating writer | Required compatibility |
| --- | --- |
| B09/B10 approval/REJECT/new target, B11/B12 Decision | Their initial Publication SHARE conflicts with W before snapshot/scope locks. Retain pr216 purpose scope and UUID-sorted automatic grant updates; replace older target-first helpers before acceptance. |
| B13 revoke/evaluate/other consumption | Same N→W→A then scope/target/parent/request/grant order; no reverse grant→Publication wait. Maintenance stays READ COMMITTED; consumption stays SERIALIZABLE. |
| Review/Issue/validity/source/authority writers | N SHARE excludes ordinary ROW EXCLUSIVE mutations and INSERT phantoms before snapshot; preserve their own parent coordination and atomic authority-loss staleness events. |
| INTERNAL_REVIEW entry / later publication writers | Entry contract must agree on N→W→A before snapshot and manuscript→Publication row order. Later reset/package/consent protocols require separately approved bindings; do not assume compatibility. |

After every required wait, reread affected state then clock_timestamp(); check
caller and issuing approver actual credentials, binding/membership/role bounds,
grant issued/expiry bounds and every gate. Deferred waits force another final
check and rollback on expiry. N protects data but cannot stop wall-clock expiry.
Legacy target-first scientific writers can still deadlock; prove bounded whole-UoW
40P01 recovery and both commit orders. Add no read lock to solve a write race.

### 12.3 Ordered build steps and module paths

1. Reconcile joint B13/B14 READY freeze, entry prerequisite and actual head.
   Preserve B13 §11.1 existing review relations and sealing; add no
   consumption-review table/index/trigger. Add one forward file under
   `migrations/versions/` for §12.1; preserve 0035,
   0042/0045/0048 history and accepted entry semantics. No missing dependency stubs.
2. Reuse `src/researchbase/domain/approval.py` and
   `src/researchbase/foundation/hashing.py` for B13's pure request normalization
   and saved result v1. No new domain schema, event hash or ORM dependency.
3. Extend `src/researchbase/application/publication.py` with §11.3 DTOs and the two
   methods. Call shared in-UoW consumption orchestration from
   `src/researchbase/application/approval.py`; never nest write-service transactions.
   Use B11/B09 gate helpers and the existing B04 closure verifier.
4. Extend typed ports in `src/researchbase/application/ports.py` and
   `src/researchbase/persistence/publication_repository.py` for prepared writes,
   guarded update/event and plain snapshot history reads. Integrate B13
   `src/researchbase/persistence/approval_repository.py`; extend
   `src/researchbase/persistence/uow.py` for wiring/constraint normalization.
   Replace locking authorization helpers only as needed by these new paths.
5. Add §12.4 tests and existing regressions; run static/unit/architecture and
   affected PostgreSQL checks, record exact evidence, stop. API/CLI changes need
   later authorization; existing maps in §11.2 already determine future errors.

### 12.4 Test artifacts and required cases

Planned files below are not present implementation evidence. Use accepted B04/B05,
approval and entry Application fixtures with disposable real PostgreSQL 18.x.
Concurrent tests use separate backend PIDs, barriers and pg_blocking_pids()/pg_locks;
exercise both commit orders, including zero-Issue review INSERT phantoms.

| File to add | Required cases |
| --- | --- |
| tests/unit/phase2/test_b14_ready_contract.py | Closed/frozen DTOs, strict UUIDs, missing/extra fields, explicit null/hash-only constants, 1/100/101 reviews, duplicates/permutation; exact error pairs; B13 saved v1 unchanged and R3 READY vectors. |
| tests/integration/phase2/test_b14_publication_ready.py | Real entry→B11 Decision→approval→READY path; same Publication/exact manuscript/hash/basis; all recommendations, later matching reviews and finite upstream blockers; B08 terminal history and manuscript OPEN blockers; B10 rejection fence; independence, Agent caller/HUMAN approver; wrong tuple/parent/state, bad bytes/closure, stale target; one row_version increment, event/receipt/grant/event atomicity; injection after each write, deferred check and final clock leaves zero partial effect. |
| tests/integration/phase2/test_b14_ready_schema.py | Clean/populated forward upgrade, preserved creation/entry/pointer/hash history, exact named FK/index/CHECK/trigger catalog and downgrade refusal; normal-role SQL state-only, event-only, receipt-only, old receipt reuse, wrong actor/time/Decision/reviews/parent, late request-review INSERT, request-review UPDATE/DELETE or chain substitution, late event append, second transition and event/receipt edit denied; deferred cycles succeed only with complete graph at SET CONSTRAINTS and commit. |
| tests/integration/phase2/test_b14_ready_replay.py | Same key/material returns original result after grant/issuer authority/caller write-role expiry, blockers or validity loss with live current read entitlement; caller credential/read loss denies; other actor/project nondisclosure, changed grant/result/reviews conflicts, review permutation replay, different key consumed grant, uncertain commit/restart and corrupt/incomplete receipt fail closed; audit read distinct from replay; checked reviews reconstruct from the sealed request relation, empty/mismatched basis or broken chain fails closed. |
| tests/integration/phase2/test_b14_ready_concurrency.py | FIRST-SQL literal inventory/isolation and pre-snapshot exclusion; same key one result, changed key material conflict, two keys/one grant and competing grants one READY winner; REJECT/new-target, review/Issue INSERT, authority/validity and maintenance both orders; starts T−1, holds required table/scope/target/grant/deferred lock until T+1, final clock denies with no effect; retry crossing expiry, ≤3 SQLSTATE attempts, no timeout/business retry; pg_locks proves reads/replay have no explicit exclusion locks. |
| tests/architecture/test_b14_ready_boundaries.py | Human/Agent same Application command, no ORM/domain leakage or nested transaction, concrete receipt/event chain, no semantic JSON owner/generic status endpoint, no read-side locks/writes, package/send/outbox scope absent. |

After implementation run these plus existing publication draft/migration,
B04 freeze/migration/races, B05 review/basis/races, approval, Decision/schema and
accepted Batch C/B13/entry regressions. Run ruff check/format, pyright,
git diff --check and unit/architecture tests. Missing future tests/dependencies
are not passing acceptance; the owner's loop runs the full suite.

### 12.5 Not in this slice

| Deferred behavior | Owner / reason |
| --- | --- |
| DRAFTING→INTERNAL_REVIEW command | Separate entry contract/execution slice required before READY deployment. |
| READY→DRAFTING, repeat readiness cycles, withdrawal/archive | Later lifecycle contract must amend uniqueness/continuity and event binding. |
| Internal release or package freeze result bindings | Other B13 owning branches; no acceptance inferred here. |
| Prepared package, authorship consent/withdrawal and manifest/supersession | Separately authorized publication/consent slice, distinct PREPARE_SUBMISSION Decision/grant. |
| Manuscript Issue disposition, revision/reconsideration implementation | Separate approved owning contracts; no implicit blocker closure. |
| Routes/CLI, scheduler, queue/outbox, generic workflow/policy engine | Separate authorization; no new dependency or persistence mechanism. |
| SubmissionVersion/SubmissionRecord, venue send, ExternalEffect | Later external-event extension; READY proves no sending. |

## 13. Open questions for the owner — override register

| Owner disposition needed | Decision adopted pending approval |
| --- | --- |
| Joint freeze with B13? | Freeze READY DTO/hash/result/event graph and shared lock inventory together; release/package bindings remain outside this task. |
| Who owns INTERNAL_REVIEW entry? | Require a separately approved entry contract/implementation; name its execution slice before B14 migration. No automatic DRAFTING promotion or test bypass. |
| Repeated READY cycles? | One READY per Publication in this bounded slice; future reset/re-entry requires an approved amendment. |
| Coarse Publication protection? | Retain B13's pre-snapshot SHARE ROW EXCLUSIVE mechanism; narrower protection needs equivalent demonstrated phantom exclusion. |

These are explicit draft choices/dependency gaps, not permission to extend scope.

## 14. Documentation verification note

Only this proposal is authored. All B14 tests above are planned, not executed
implementation evidence. Exact documentation-task results are recorded below.

Verification on 2026-10-16 used the installed shared environment without sync.
Every uv command below has this common environment prefix:

```sh
UV_CACHE_DIR=/tmp/researchbase-b14-uv-cache UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv
```

| Exact command after common prefix | Observed result |
| --- | --- |
| `uv run --no-sync ruff check .` | PASS: All checks passed! |
| `uv run --no-sync ruff format --check .` | PASS: 570 files already formatted. |
| `uv run --no-sync pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject` | PASS: 0 errors, 0 warnings, 0 informations. |
| `PYTHONPATH=src RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run --no-sync pytest tests/unit tests/architecture --tb=short` | 2,343 passed, 4 failed, 12 errors, 7 warnings in 50.16s; not PASS. |
| `PYTHONPATH=src uv run --no-sync pytest tests/unit/test_approval.py tests/unit/phase2/test_pr2_15_decision.py tests/unit/phase2/test_b04_manuscript_contract.py tests/unit/phase2/test_b04_manuscript_hash_vectors.py tests/unit/phase2/test_b05_review_contract.py tests/unit/phase2/test_b05_review_hash_vectors.py tests/architecture/test_basic_approval.py tests/architecture/test_b04_boundaries.py tests/architecture/test_b05_review_boundaries.py --tb=short` | 196 passed, 3 warnings in 0.83s. |
| `PYTHONPATH=src DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run --no-sync pytest tests/integration/phase2/test_pr2_12_publication_draft.py tests/integration/phase2/test_pr2_12_migration.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b05_manuscript_review.py tests/integration/phase2/test_b05_review_basis.py tests/integration/phase2/test_approval.py tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_15_decision_schema.py -x --tb=short` | 1 setup error in 0.54s; stopped before database assertions, remaining cases not run. |

The four broad-run failures are in tests/unit/test_hg1_runner.py: sandbox-denied
Unix socket binds (Operation not permitted). The twelve errors are PR2-19
architecture fixtures: sandbox-denied localhost PostgreSQL connections. The
focused PostgreSQL run hit the same connection denial. No database assertions
or server-version query completed; PostgreSQL is not reported PASS. Warnings
are Alembic's existing path_separator deprecation. No whole-suite run was made;
the owner's loop owns that evidence.

`git diff --check` produced no whitespace errors. For the untracked draft,
`git diff --no-index --check /dev/null docs/proposals/B14_Publication_Ready_Transition_Contract_DRAFT.md`
also produced no whitespace errors (exit 1 denotes the new-file difference).
A local `python3` pathlib/regex/AST check resolved 29 relative links, matched all
17 HTTP/CLI pairs against the source dictionaries, and verified the required
status and 14 numbered sections. `git status --short` showed only this new file.
No implementation or gate acceptance is claimed.


Director review 1 consistency revision (2026-10-16): B14 adopts B13 §11.1 option
(a), deriving checked reviews from the existing sealed ApprovalRequest relation.
The exact static, unit/architecture and focused PostgreSQL commands/counts for
this documentation revision are recorded in [B13's Director review 1 revision
verification](B13_Grant_Consumption_Contract_DRAFT.md#director-review-1-revision-verification--2026-10-16).
Static checks passed; unit/architecture returned 2,343 passed, 4 failed and
12 errors; focused PostgreSQL stopped at 1 setup error. Sandbox socket/connection
denials prevented those checks from passing. No implementation acceptance or
whole-suite result is claimed.
