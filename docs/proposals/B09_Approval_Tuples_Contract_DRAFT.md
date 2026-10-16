# B09 Basic Approval Tuples and Rejection Fence Contract — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

## Start here (for the implementer)

B09 extends the accepted PR2-16 request/decision/grant foundation to the three
finite Phase 2 approval tuples. It preserves the project/purpose rejection fence.
Approval records authorization; it does not release science, make a Publication
READY, freeze a package, or send anything. This document changes no executable
code, schema, architecture baseline or gate status.

Read §§1–4 first. Use §10 for terms, §11 for pinned choices and §12 for the build
plan. The owner can override proposed refinements through §13 before freeze.
Contract approval and implementation authorization are separate decisions.

Build only after both approvals, in this order:

1. Reconcile the actual Alembic head and manuscript Decision dependency (§1).
2. Add a forward migration preserving 0045 history and its existing hashes
   (§12.1); never edit accepted migrations.
3. Extend closed DTOs and pure finite-tuple validation (§11.3), then the existing
   Approval service, ports and SQL adapter (§12.3).
4. Apply the exact writer protocol and lock-free read protocol (§12.2), including
   normal-role SQL guards and the existing authority-loss writers.
5. Add the cases in §§8 and 12.4; execute focused checks, retain exact evidence
   and stop. Do not build a missing dependency to make approval tests pass.

Five review rules:

1. Accept only the three purpose/target/command rows in §3; no wildcard policy.
2. Bind exact frozen hashes, independent reviews and a distinct matching Decision;
   authority never overrides deterministic invalidity or OPEN/BLOCKING issues.
3. Only an independent HUMAN with effective APPROVER authority may decide.
4. Rejection fences every target in the same project/purpose, including requests
   created before the rejection; cloning and changing approver cannot bypass it.
5. One write command, one transaction; SHARE inputs first at READ COMMITTED,
   fresh post-wait DB authorization, atomic history, and read-only historical replay.

## 1. Purpose, authority and inspected baseline

| Source | Constraint carried forward |
| --- | --- |
| [System 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 7–13; [Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A17–A23 | Facts precede authority; immutable exact-version history; Review ≠ Decision ≠ Approval ≠ Command ≠ ExternalEffect; focused R2/R3/R4 precedence. |
| [Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md); [Cross-Phase 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§9–18, 24, 28 | Reuse registered governance records and concrete relations; shared Application boundary; additive compatibility and stable errors. |
| [Phase 2 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), governance and PR2-16; [Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), §§4–7; [Fields 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md), approval contracts | Exact typed targets, immutable decisions, scoped grants and events; prepared is not sent. |
| [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md), “Review, decision, approval, and revision”; [Governance R2 17](../architecture/17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md), §§1–2 | Literal ApprovalDecision hash; complete finite tuple policy, independence, 30-day limit, project/purpose rejection equivalence and separate reconsideration. |
| [R3 18](../architecture/18_Phase2_Design_R3_Targeted_Remediation_v1.0.md), §5; [Temporal R4 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md), §§1, 3–4 | Consumption has its own canonical receipt and SERIALIZABLE effect transaction; advancing post-lock time and historical replay. No receipt is added here. |
| [Minimal Decision 20](../architecture/20_PR2_15_Minimal_Decision_Command_Contract_v1.0.md); [accepted PR2-16 contract](PR2-16_Basic_Approval_Contract.md) | Existing PROCEED is conclusion release only, with complete saved review basis and no replacement; first approval slice excludes consumption and reconsideration. |
| [Harness specification](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 16, 18–19 | Application writes only; evidence before completion. No B09 execution pack is supplied by this proposal. |

Inspected implementation, rather than the older inventories in the reference drafts:

- [0045](../../migrations/versions/0045_pr2_16_basic_approval.py) owns six approval
  tables. Both target FKs exist, but CHECKs permit only conclusion release;
  rejection/reconsideration FKs must be NULL. Grants derive target through the
  immutable decision/request chain; `max_uses=1` is a projection, not a column.
- [ApprovalService](../../src/researchbase/application/approval.py),
  [domain material](../../src/researchbase/domain/approval.py) and
  [SQL repository](../../src/researchbase/persistence/approval_repository.py)
  implement two writes and three exact-ID reads, a project-wide rejection query
  safe only while one purpose exists, finite expiry, authority-loss staleness,
  and no consumption. Existing reads call a locking preparation path: B09 must
  replace that path, not describe it as already lock-free.
  There are no Basic Approval API routes or CLI commands yet; the error mappings
  exist, but transport exposure below is proposed work.
- [DecisionService](../../src/researchbase/application/decision.py) and
  [0042](../../migrations/versions/0042_pr2_15_minimal_decision.py) support only
  `INTERNAL_SCIENTIFIC_RELEASE/PROCEED` with conclusion/review basis. A release
  Decision cannot supply either manuscript purpose. A separately approved
  manuscript Decision command/schema contract is a prerequisite to admitting
  either new tuple; B09 does not broaden Minimal Decision 20 by implication.
- [B04 freeze adapter](../../src/researchbase/persistence/manuscript_freeze_repository.py)
  and [B05 review adapter](../../src/researchbase/persistence/internal_review_repository.py),
  migrations 0048/0049, now supply exact manuscript seals and reviews. Reuse their
  verification and complete-basis paths, not the obsolete assumption that they
  are absent. Authorship 0046 is attribution foundation, not consent/package freeze.
  The inspected migration chain reaches `0051_b06_revision_action`; resolve the
  actual head again before any later migration. Source presence is not acceptance.

## 2. Scope, dependency boundaries and non-goals

Proposed slice: extend `request_approval`, `decide_approval`, `get_request`,
`get_decision`, `get_grant` for all §3 tuples; preserve existing conclusion DTO
calls; enforce purpose-specific rejection, independence, bounds, replay and
writer coordination. No new top-level canonical object or dependency is needed.

The manuscript branches remain unavailable until their exact Decision basis and
required Publication lifecycle states have separately authorized implementations.
Report `DECISION_BASIS_INVALID` for missing/mismatched basis and
`APPROVAL_GATE_FAILED` for an unavailable required lifecycle state; never create
a stand-in Decision, force a lifecycle state, or claim a working end-to-end tuple.
This dependency gate is a limitation, not full B09/Phase 2 acceptance.

Consumption, release receipts, READY transition, prepared-package construction,
consent capture/withdrawal, grant revocation/expiry commands, rejection
reconsideration and Issue disposition are separate contracts (§12.5).

## 3. Invariants and finite approval policy

The following copies Governance R2 §1. Persist `allowed_command` as the lowercase
Application name already used by 0045. R3's uppercase receipt command enum belongs
to later consumption; it is not a second executable grant vocabulary.

| Purpose | Exact target and required state | Matching affirmative Decision and review basis | Sole allowed command, deferred effect |
| --- | --- | --- | --- |
| INTERNAL_SCIENTIFIC_RELEASE | FROZEN, currently VALID ScientificConclusionVersion in active Project | INTERNAL_SCIENTIFIC_RELEASE/PROCEED; exact conclusion/hash and required independent conclusion reviews | `record_internal_scientific_release`; consumption itself records release, no material edit |
| READY_FOR_SUBMISSION | FROZEN, currently VALID ManuscriptVersion; owning Publication INTERNAL_REVIEW | READY_FOR_SUBMISSION, affirmative; exact manuscript/hash and independent manuscript reviews | `transition_publication_ready`; owning Publication INTERNAL_REVIEW→READY |
| PREPARE_SUBMISSION | FROZEN, currently VALID ManuscriptVersion; owning Publication READY | Distinct PREPARE_SUBMISSION, affirmative; same exact manuscript review gate | `freeze_prepared_submission`; same-Publication prepared package freezes |

Every other combination fails `APPROVAL_PURPOSE_TARGET_COMMAND_INVALID`, even if
caller holds OWNER or APPROVER. The command is derived from purpose, never caller
policy. At request and decision verify same-project exact target/hash/scheme,
full frozen scientific closure, current deterministic validity, active project,
required lifecycle state, committed prior Decision and reviews, their own
hashes and creation authority, and all applicable exact-target OPEN/BLOCKING issues.
Use B04's full seal/CAS and transitive scientific checks for manuscripts; a
hash-shaped string, citation trace or favorable review cannot replace them.

The required request review set equals the complete saved review basis of its
Decision, including unfavorable recommendations. Later reviews remain visible
and are checked for corruption and applicable blockers; they do not mutate a
saved Decision or request basis. Required reviewers differ from requester and
all material authors. Basis decider differs from material authors. Approver is
HUMAN, effective same-project APPROVER, distinct from requester, basis decider,
every required reviewer and every material author/contributor. Use the existing
transitive author inventory, extended through manuscript document and placements;
membership, corresponding authorship, acting_on_behalf_of and accumulated roles
cannot satisfy actor independence. OWNER alone and Agent APPROVER cannot decide.

Request is PENDING→DECIDED once. APPROVE/APPROVE_WITH_CONDITIONS creates exactly
one ACTIVE grant in that same transaction; REJECT creates none. No withdrawal
command is added. Preserve terminal history. A new selection of another exact
target for the same project/purpose stales unused older grants, as 0045 already
does for release; merely navigating to a SUPERSEDED frozen version does not.

### 3.1 Rejection fence

`EXISTS REJECT in (project_id, approval_purpose)` fences **all** targets in that
scope, across lineages/Publications, hashes, versions, wording and UUIDs. Correct
the current `rejected(project)` lookup to include purpose everywhere, including
SQL guards and grant usability. Another purpose/project is not fenced.

After a rejection commits, deny new requests and any first decision on an older
PENDING request with `REJECTION_RECONSIDERATION_REQUIRED`. Recheck under the same
scope lock so a concurrent rejection cannot be missed. Existing unused grants
are unusable under that fence; this draft proposes marking them STALE with grant
events in the rejecting transaction, without rewriting previously consumed history.
Exact historical replay is still a read (§7). No elapsed time, changed actor,
RevisionAction, PROCEED, favorable review or owner override flag clears the fence.
Governance R2 §2's all-rejections reconsideration chain remains a separate dependency.

## 4. Proposed commands, DTOs and historical readback

Keep the five existing method names. Request accepts exactly one concrete target
FK, purpose, exact basis Decision and its review IDs. Decide accepts request ID,
outcome and typed conditions only. There is no standalone create-grant method.
Requester is current RESEARCHER/OWNER; decider is independent HUMAN APPROVER.
Reads require live verified principal and current project reader entitlement
(OWNER/RESEARCHER/REVIEWER/APPROVER/VIEWER), including object access to referenced
globally owned sources when their details are disclosed. Never expose ORM objects.

Readbacks retain all existing actor/time/hash/status/event fields, add the nullable
manuscript target to request/grant, and make the conclusion target nullable.
Grant target/hash/command/max_uses derive from its decision/request chain. Decision
readback embeds its optional grant. Historical material and timestamped current
`usable`, `unusable_code` are distinct: reading an expired or stale grant does
not change its stored status. Final read-entitlement checks use fresh DB time.

## 5. Schema and literal hash proposal — no migration

Extend 0045 concrete columns and CHECKs; no target locator JSON, policy table,
new grant target copy, second fingerprint or request hash is admitted. Preserve
`sha256-cjson-v1` and the literal ApprovalDecision payload in Hash R2 15, including
the exact target type, `valid_until` (including null), consent bool and decided_by.
Purpose/allowed command are verified through immutable typed scope, not new hash
keys. ApprovalRequest and ApprovalGrant have no new own content hash.

Use existing immutable request/decision/event records for audit. The decision,
request DECIDED event, optional grant and ACTIVE event, plus affected stale-grant
events commit together. Deferred completeness checks follow 0042/0045 and run
on the final graph; children are sealed against later append/update/delete.

## 6. Error contract — existing categories only

Use §11.2 verbatim at both adapters. Authenticate and authorize before revealing
protected existence or payload conflicts. Do not map a stale target to a missing
record or a serialization failure to a scientific denial. Expected denials have
no successful event or partial record. Unexpected failures use the existing
sanitized HTTP/CLI fallback; never expose SQL, credentials or CAS paths.

## 7. Transactions, concurrency and failure recovery

New writes use READ COMMITTED with protected inputs locked before the first
snapshot query (§12.2). This is not the SERIALIZABLE consumption transaction of
R3. Existing request UUID coordinates replay; no receipt or new persisted key.

Same UUID, actor, project and normalized caller fields returns the saved complete
record after current read authorization, without reevaluating first-write gates.
Verify saved immutable hashes/relations and return current usability separately.
Changed material conflicts; wrong actor/project is nondisclosing FORBIDDEN.
Write-role loss, later invalidity, rejection or expiry does not prevent an
otherwise entitled historical replay. Unknown/incomplete history is never success.
Review order is nonsemantic after duplicate rejection and UUID sorting.

An existing completed write is replayed through the lock-free read path. A racing
new write that discovers a committed duplicate under writer locks closes that
UoW and reopens one REPEATABLE READ, READ ONLY UoW for historical replay; it does
not return a read DTO from a locking writer path. Reads themselves never lock.
If absent, first creation repeats every gate under writer coordination. This
preflight is advisory navigation only and grants no first-write authorization.

Retry only SQLSTATE 40001/40P01, at most three total fresh-UoW attempts, no delay
or external call, preserving existing normalization in persistence/uow.py. Do not
retry business CONCURRENT_MODIFICATION, uniqueness loss, timeout or uncertain
commit. Uncertain commit is recovered by the original UUID, never a new one.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

Required groups: finite tuple cross product; full frozen closure/CAS; complete
saved review basis and later blockers; HUMAN independence and authority expiry;
project/purpose rejection including pending bypass; immutable atomic history;
same-ID replay/disclosure; current grant usability versus saved history; SQL
guard parity and deferred sealing; real wait/race/rollback evidence; additive
migration and transport compatibility. Concrete files/cases are in §12.4.

## 9. Acceptance criteria and evidence boundary

Owner approval and separate execution authorization precede implementation.
Verify manuscript Decision/lifecycle prerequisites before claiming those branches
usable. No B09, G6, PR2-19 or Phase exit gate passes merely because a grant exists.
Execute static, unit, architecture and affected PostgreSQL tests on 18.x; retain
exact commands, counts, server version, migration evidence and findings. No open
P0/P1 may pass. The full suite belongs to the owner's loop for this documentation
task; this author must not run it. Planned tests below are not current evidence.

## 10. Glossary

| Term | Meaning |
| --- | --- |
| Tuple | Purpose × concrete exact target × sole allowed Application command in §3 |
| Request | Immutable target/basis submission with PENDING/DECIDED lifecycle |
| ApprovalDecision | Immutable HUMAN authorization judgment, distinct from its basis DecisionRecord |
| Grant | One-use, finite authorization derived through one approving decision/request |
| Fence | Any prior rejection in the same project/purpose prevents fresh approval work |
| Required reviews | Exact complete saved Decision review basis, sealed into request relations |
| Replay | Currently authorized historical read of an already completed matching command |
| N | Fixed SHARE-locked input table inventory in §12.2; not a persistence entity |

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

Adopt all three R2 tuples, two write/five total methods, no effects. Preserve
release defaults and existing hashes. Manuscript Decision/lifecycle prerequisites
are explicit blockers, not hidden work. Keep the conservative rejection fence;
stale other unused same-scope grants atomically on REJECT. Reconsideration stays
unavailable. No additional generic policy, schema owner or dependency is proposed.

### 11.2 Pinned error mappings

Mappings match [api/errors.py](../../src/researchbase/api/errors.py) and
[cli/errors.py](../../src/researchbase/cli/errors.py); no new ErrorCode is needed.

| Code | HTTP | CLI exit | Use |
| --- | --- | --- | --- |
| VALIDATION_ERROR | 422 | 2 | Closed DTO/type/enum/limit/condition violation |
| AUTHENTICATION_REQUIRED | 401 | 3 | Missing/unverifiable trusted principal |
| FORBIDDEN | 403 | 3 | Current authority/read entitlement or replay actor mismatch |
| CONFLICT_OF_INTEREST | 403 | 3 | Canonical actor independence fails |
| NOT_FOUND | 404 | 3 | Authorized exact target/request/history absent |
| APPROVAL_PURPOSE_TARGET_COMMAND_INVALID | 409 | 4 | Unlisted purpose/target/command tuple |
| DECISION_BASIS_INVALID | 409 | 4 | Missing, incomplete, wrong-purpose/target or uncommitted Decision/review basis |
| APPROVAL_GATE_FAILED | 409 | 4 | Inactive Project, lifecycle prerequisite or applicable blocker |
| APPROVAL_TARGET_STALE | 409 | 4 | New-write target unfrozen/invalid or newer target selected |
| REJECTION_RECONSIDERATION_REQUIRED | 409 | 4 | Same-project/purpose rejection fence |
| GRANT_INVALID | 409 | 4 | Current projection: finite grant expiry reached |
| GRANT_STALE | 409 | 4 | Current projection: terminal status or issuing authority lost |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Changed entitled replay, duplicate pending or already-decided request |
| CONCURRENT_MODIFICATION | 409 | 4 | Exhausted retryable transaction conflict or existing timeout normalization |
| IMMUTABLE_RECORD | 409 | 4 | Forbidden history mutation/late basis append |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Concrete FK/integrity violation |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Saved hash/typed graph corruption |
| INTERNAL_ERROR (fallback string) | 500 | 1 | Existing sanitized unexpected-error fallback |

For multiple failed grant predicates retain current `_grant_view` precedence:
terminal status, expiry, approver authority, then gate order; current projections
may expose the gate's exact error code. This table does not add a consuming API.

### 11.3 DTO fields, Python types and limits

All command dataclasses are frozen/slots/closed, exact UUID objects internally;
wire UUIDs use canonical lowercase hyphenated text. Reject unknown fields, bool
as int, naive/nonfinite times, NUL/surrogates, duplicate IDs and blank text. Use
existing `_text` NFC normalization, preserving meaningful whitespace; add an
explicit NUL check because `_text` alone does not reject it. Size bounds are
proposed first-write refinements: enforce them after the historical replay lookup,
so existing longer saved material remains readable/replayable.

| DTO/field | Python type and pinned rule |
| --- | --- |
| Request: `id`, `project_id`, `basis_decision_id` | `uuid.UUID`, required |
| Request: `scientific_conclusion_version_id` | `UUID | None`; preserve existing positional slot; nonnull only for release |
| Request: `review_ids` | `tuple[UUID, ...]`, 1..100, distinct, sorted by UUID text; entire saved Decision review set required; never truncate |
| Request: `approval_purpose` | strict `str`; finite literals INTERNAL_SCIENTIFIC_RELEASE / READY_FOR_SUBMISSION / PREPARE_SUBMISSION; default release retained; unsupported strings reach tuple validation (409), not transport Literal validation (422) |
| Request: `manuscript_version_id` | New keyword-only `UUID | None = None`; exactly one target nonnull |
| Decide: `id`, `project_id`, `approval_request_id` | `UUID`, required |
| Decide: `decision` | `Literal['APPROVE','APPROVE_WITH_CONDITIONS','REJECT']` |
| Decide: `rationale` | `str`, nonblank NFC, 1..16,384 Unicode code points after normalization |
| Decide: `valid_until` | aware `datetime.datetime | None`; normalize UTC; null for APPROVE/REJECT; required for APPROVE_WITH_CONDITIONS |
| Decide: `requires_current_author_consent` | strict `bool = False`; false for release/ready; conditional true allowed only for PREPARE_SUBMISSION; REJECT must be false |
| Exact reads | `project_id: UUID` and one `request_id`, `decision_id` or `grant_id: UUID`; no filters/pagination/list methods |
| Request readback target fields | Both `UUID | None` under same XOR; other existing fields unchanged |
| Grant readback | Both target fields under XOR; `max_uses: Literal[1]`, `usable: bool`, `unusable_code: str | None`; existing derived scope/time/events retained; add `evaluated_at: datetime` (aware UTC) |

For APPROVE_WITH_CONDITIONS require fresh `decided_at < valid_until <= decided_at
+ timedelta(hours=720)`. For APPROVE, grant expiry is exactly decided_at + 720
hours; it is always finite/non-null. Equality at expiry denies. Free text never
executes a condition. PREPARE_SUBMISSION consumption must require current author
consent even if its APPROVE decision stored false: that baseline gate cannot be
disabled by a condition. No consent is captured or consumed here. Persisted
request statuses remain PENDING/DECIDED/WITHDRAWN; grant statuses remain
ACTIVE/CONSUMED/EXPIRED/REVOKED/STALE, but B09 exposes only existing ACTIVE→STALE
mutation. Stored scope and event enums do not authorize other transitions.
Wrong primitive types, malformed target XOR and unsupported outcome literals
are VALIDATION_ERROR; a well-formed but unlisted purpose/target pairing is
APPROVAL_PURPOSE_TARGET_COMMAND_INVALID.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

Use a single forward revision after the then-current head. Preflight under DDL
locks, retaining legitimate stale history; do not re-run present-day validity as
a migration predicate. Replace only the affected 0045 guards/CHECKs. Existing
unnamed CHECKs must be resolved by table/column and `pg_get_constraintdef`, with
exact expected-definition assertions; do not guess PostgreSQL-generated names
or drop every CHECK. The replacement names and types are pinned below.

```sql
-- Existing UUID FKs, CHAR(64) hashes, TEXT enums and TIMESTAMPTZ stay unchanged.
ALTER TABLE approval_requests ADD CONSTRAINT ck_b09_request_tuple CHECK (
 (approval_purpose='INTERNAL_SCIENTIFIC_RELEASE'
  AND scientific_conclusion_version_id IS NOT NULL AND manuscript_version_id IS NULL)
 OR (approval_purpose IN ('READY_FOR_SUBMISSION','PREPARE_SUBMISSION')
  AND manuscript_version_id IS NOT NULL AND scientific_conclusion_version_id IS NULL));
-- Replace uq_pr216_pending with these two partial unique indexes.
CREATE UNIQUE INDEX uq_b09_pending_conclusion ON approval_requests
 (project_id,approval_purpose,scientific_conclusion_version_id)
 WHERE status='PENDING' AND scientific_conclusion_version_id IS NOT NULL;
CREATE UNIQUE INDEX uq_b09_pending_manuscript ON approval_requests
 (project_id,approval_purpose,manuscript_version_id)
 WHERE status='PENDING' AND manuscript_version_id IS NOT NULL;
ALTER TABLE approval_grants ADD CONSTRAINT ck_b09_grant_tuple CHECK (
 (purpose='INTERNAL_SCIENTIFIC_RELEASE' AND allowed_command='record_internal_scientific_release')
 OR (purpose='READY_FOR_SUBMISSION' AND allowed_command='transition_publication_ready')
 OR (purpose='PREPARE_SUBMISSION' AND allowed_command='freeze_prepared_submission'));
ALTER TABLE approval_decisions ADD CONSTRAINT ck_b09_consent_condition CHECK (
 NOT requires_current_author_consent OR decision='APPROVE_WITH_CONDITIONS');
CREATE INDEX ix_b09_rejection_scope ON approval_requests(project_id,approval_purpose,id);
-- Retain unique approval_decisions.approval_request_id and
-- approval_grants.approval_decision_id, concrete RESTRICT FKs and existing XOR.
-- prior_rejected_request_id/reconsideration_decision_id still CHECK IS NULL.
```

Remove old release-only purpose/target/command and unconditional false-consent
CHECKs before installing these replacements; retain valid-until/outcome/hash
checks. Consent applicability is cross-row and belongs to the guard below, not
a subquery in CHECK. No new tables/columns are required for this slice.

| Guard/constraint name | Required behavior |
| --- | --- |
| Replace functions under existing `pr216_request_guard`, `pr216_decision_guard`, `pr216_grant_guard` triggers | Explicit target dispatch; same-project/state/hash/finite tuple; matching prior immutable Decision/reviews; bounded conditions/new-row rationale and review-count limits; HUMAN independence; purpose-specific fence and exact scope-derived grant expiry. Extend the STALE cause guard for an exact same-transaction, same-project/purpose REJECT decision, not trigger depth alone; preserve authority-loss/new-target causes. No arbitrary JSON authority. |
| `pr216_relation_guard` | Complete request review membership, committed historical basis, no late append; retain immutable relation guards. |
| `pr216_complete_request`, `pr216_complete_reviews`, `pr216_complete_decision` | Retain DEFERRABLE INITIALLY DEFERRED constraint triggers, extend final-graph completeness for both target branches; one decision iff DECIDED, one grant iff approval; request review set equals basis. Attach `pr216_complete_grant` to grant INSERT as another deferred completeness trigger. |
| Existing `pr216_*events` and immutable event guards | Automatic atomic request/grant lifecycle events only; rejection stales other ACTIVE same-scope grants with events; no forged event insertion or history edits. |
| Existing `pr216_role_loss`, `pr216_membership_loss`, `pr216_actor_loss`, `pr216_binding_loss` | Preserve authority-loss staleness across every purpose in the same authority transaction, without resurrecting terminal grants. Scheduled expiry only changes read usability until a separately authorized writer observes/persists it. |

Deferred enforcement follows [0042](../../migrations/versions/0042_pr2_15_minimal_decision.py):
check final sealed sets after all inserts, not an empty intermediate parent.
Normal-role SQL must acquire the same snapshot/scope/target exclusion before
evaluating guards; test the preheld N-lock/isolation precondition as B04/B05 do.
Function search paths remain `pg_catalog, public, pg_temp`. Keep same-project
concrete FK verification and RESTRICT; no CASCADE. Populated downgrade refuses
any loss of history or removal of guarantees required by new-purpose rows;
an empty-slice downgrade may restore old guards and CHECKs.

### 12.2 Exact lock order and transactions

N is the lexically sorted union of the **literal** `B04_SNAPSHOT_TABLES` inventory
in manuscript_freeze_repository.py with `manuscript_versions` and `publications`.
Freeze this inventory in the B09 adapter/migration and test equality against this
baseline; do not dynamically query the catalog or inherit later additions silently.
It covers authority, scientific inputs/relations, validity, manuscript placements
and owning Publication state. B09 writes none of N. Review/Issue insertion phantoms
are protected by the exact target row and existing 0041/0049 writer triggers.
Approval/Decision relations are sealed immutable inputs; new rejection/target
selection phantoms use the common project/purpose scope advisory lock.

For every new write, configure READ COMMITTED and disable autoflush without SQL.
The **FIRST SQL statement** is one `LOCK TABLE <N, sorted> IN SHARE MODE`; no
navigation SELECT, SET LOCAL, advisory or target lock precedes it. Then install
`SET LOCAL lock_timeout='10s'` and `SET LOCAL statement_timeout='30s'`. The initial
SHARE wait needs a connection/server bound set before transaction entry; do not
claim the later SET LOCAL bounds an earlier wait. Use final lock modes directly.

| Command | Exact operations after N SHARE/timeouts |
| --- | --- |
| request_approval | Advisory `pr216:uuid:{command.id}`; advisory `pr216:scope:{project_id}:{purpose}`; exact conclusion or manuscript FOR UPDATE; for manuscript, owning Publication FOR SHARE; authorize reader then writer at fresh DB clock; recheck absence/pending/fence and target; read saved Decision, required reviews UUID-sorted and all exact-target Issues; verify full closure/basis/independence; prelock older ACTIVE same-scope grants for other targets in UUID order; final time authorization; insert request and UUID-sorted review relations; automatic event/staleness updates; deferred/final checks below. |
| decide_approval | Advisory `pr216:uuid:{command.id}`; lookup request only now for routing; advisory same request project/purpose scope; exact target FOR UPDATE; Publication FOR SHARE if manuscript; request FOR UPDATE and reread; authorize reader then HUMAN APPROVER; reread any existing decision/fence/current gates and condition expiry; for REJECT, prelock all affected ACTIVE same-scope grants in UUID order; final time authorization; insert immutable decision, derived grant if approving, automatic request/grant events and rejection staleness updates; deferred/final checks below. |
| get_request / get_decision / get_grant and completed replay | One REPEATABLE READ, READ ONLY UoW; authorize current reader; plain parent and UUID-sorted child reads and saved-hash verification; current diagnostics at fresh clock; final read-entitlement check. **No explicit table, advisory or row locks**, `FOR SHARE`, `FOR UPDATE`, writes or status maintenance. |

Canonical UUID text and parameter binding form keys; no caller-supplied key text.
The namespace stays `pr216` so existing release writers share exclusion; replace
the SQL guard's hardcoded purpose with the actual verified purpose. No target,
project or approval-grant lock precedes N on a B09 writer. No grant is consumed.
Before a mutation that will stale older grants, prelock that complete set in UUID
order; any trigger-discovered additional wait forces renewed final authorization.

Writer inventory and participation:

| Writer | Coordination required |
| --- | --- |
| Approval request/decision/REJECT, new-target selection and normal-role SQL | N first, UUID advisory, same project/purpose scope, target, Publication, request, UUID-sorted affected grants; trigger path must enforce preheld N. This replaces the old target-before-snapshot approval protocol. |
| Conclusion/manuscript review INSERT, including zero Issues, and every applicable Issue writer | Existing exact target FOR UPDATE before review/Issue predicate changes; preserve B05 N-first manuscript path and 0041/0049 SQL guards. Future Issue transitions must participate; this grants no transition authority. |
| Source/evidence dispute, correction/impact, manuscript freeze/placement, target/parent lifecycle, ownership and scientific input writers | Normal PostgreSQL ROW EXCLUSIVE conflicts with N SHARE, including INSERT phantoms. Retain owning-service guards; no new advisory convention replaces these real table conflicts. |
| Membership/role/actor/binding changes | Existing authority-loss triggers stale affected grants atomically; B09 obtains N before grant locks so it cannot hold a grant while waiting on the authority writer's table lock. Never require these writers to acquire a B09 scope after locking grants. |
| Decision creation | Immutable prior basis only; preserve 0042 conclusion nonreplacement/target coordination. Manuscript Decision writers require their separate compatible contract; missing participation blocks that branch. |

Do not reuse locking `target()` or `reviews()` helpers on reads. Use plain SELECT
variants. After any blocking wait reread affected durable state and evaluate live
credential verifier, actor, membership, role, grant and conditions with fresh
`clock_timestamp()`; never `now()` or transaction_timestamp(). Force
`SET CONSTRAINTS ALL IMMEDIATE` before the last clock/authorization check. Repeat
the check if any later required wait occurs; otherwise commit. Any failed gate,
deferred check or final expiry rolls back every row/event. Prove interoperation
with old writers and direct SQL using observable lock evidence; N alone is not
proof of the separate rejection scope or target-based review predicate.

### 12.3 Ordered build steps and module paths

1. Obtain approval/authorization; verify prerequisites and current head. Add only
   §12.1 forward DDL under `migrations/versions/`, preserving 0045/Phase 1 hashes.
2. Extend `src/researchbase/domain/approval.py` finite purpose/command lookup and
   target dispatch; retain literal material builder and golden hashes.
3. Extend DTOs and orchestration in `src/researchbase/application/approval.py`;
   add typed members in `src/researchbase/application/ports.py`. Dispatch to B04
   manuscript verification and B05 saved review verification in the same UoW;
   do not call another service that starts an independent write transaction.
4. Extend `src/researchbase/persistence/approval_repository.py` for §12.2, purpose
   lookups, plain read variants, stable grant ordering and deferred checks. Wire
   read/write preparation in `src/researchbase/persistence/uow.py`; preserve
   SQLSTATE retry classification and existing named normalization, adding only
   new constraint-name mappings to §11.2. No raw driver-error message matching.
5. If transport exposure is included in the later authorization, add closed
   request/response models/routes in `src/researchbase/api/routes.py` and commands
   in existing `src/researchbase/cli/commands/governance.py`, following trusted
   principal injection there. Wire ApprovalService in `src/researchbase/api/app.py`
   and `src/researchbase/cli/composition.py`; keep error tables unchanged. Proposed
   POST/GET pairs are `/projects/{project_id}/approval-requests[/{id}]` and
   `/projects/{project_id}/approval-decisions[/{id}]`, with GET-only
   `/projects/{project_id}/approval-grants/{id}`. POST uses the collection path;
   first/replay and GET return 200. CLI names under governance are
   `request-approval`, `decide-approval`, `read-approval-request`,
   `read-approval-decision`, `read-approval-grant`. No list/consume route.
6. Add §12.4 tests, run focused checks and dependency regressions; record actual
   counts and remaining prerequisites. Stop without implementing §12.5.

### 12.4 Test artifacts and required cases

Use existing disposable PostgreSQL 18.x `approval_env`, conclusion and manuscript
fixture patterns; explicit reusable builders, no fabricated acceptance/history.
Use two independent connections/backend PIDs, barriers and `pg_blocking_pids()`
for races; a sleep alone is not lock evidence.

| File | Required cases |
| --- | --- |
| Extend `tests/unit/test_approval.py` | Three purposes/commands; target XOR; all outcome/condition combinations; UUID/tuple/bool strictness, 100/101 reviews, 16,384/16,385 text, NFC, null/naive/infinite time, exact 720-hour/DST edges; old release constructor compatibility; independent literal hash vectors for both target types and unchanged 0045 vectors. |
| New `tests/unit/phase2/test_b09_approval_transports.py` | If adapters authorized: exact §11.2 HTTP/CLI mapping, five new route/CLI pairs, closed targets, no caller actor/hash/time/status/max_uses/allowed_command; first/replay 200; sanitized fallback; inherited adapters unchanged. |
| Extend `tests/integration/phase2/test_approval.py` | Existing release regressions; new tuples only with real accepted dependencies; missing manuscript Decision fails with no writes; wrong-purpose Decision/grant substitution; same-project exact hash/closure/CAS, all required reviews, later blocker; every pairwise independence conflict, Agent/OWNER-only denial; approval grant iff affirmative; historical replay after rejection/staleness/write-role loss and current read denial. |
| New `tests/integration/phase2/test_b09_approval_schema.py` | Clean install/populated forward upgrade, exact names/types/indexes/FKs, preserved old hashes, empty downgrade/populated refusal; normal-role SQL cross-product/conditions/forged actor/hash/missing grant/reviews deny; deferred completeness at commit and SET CONSTRAINTS; late child/event append/update/delete deny; rollback after each staged insert/event. |
| New `tests/integration/phase2/test_b09_approval_concurrency.py` | FIRST-SQL inventory and READ COMMITTED evidence; lock-free RR reads/replay; same UUID single winner/changed payload; same request two deciders; cross-target REJECT versus request/pending decision in both commit orders; other purpose/project unaffected; later review with zero Issues and blocker insertion; new target selection versus old grant/decision; normal SQL writer parity; authority mutation/stale events and scheduled credential/role expiry across N/scope/target/grant/deferred waits; 40001/40P01 ≤3 fresh attempts, no timeout/business retry; uncertain commit original UUID. |
| Extend `tests/architecture/test_basic_approval.py` | Common Application boundary and no ORM leakage; only five methods; no consumption/reconsideration/effect/READY/consent side effects; concrete refs and unchanged scientific payloads; replace historical single-migration assertions narrowly for the authorized forward revision. |

Run the new tests plus `tests/integration/phase2/test_pr2_15_decision.py`,
`test_pr2_15_decision_schema.py`, `test_b04_manuscript_freeze.py`,
`test_b05_manuscript_review.py` and existing approval/authority-loss regressions.
Execute `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`,
`git diff --check`, and `uv run pytest tests/unit tests/architecture`.
Missing future fixtures/contracts are not skips that count as tuple acceptance.

### 12.5 Not in this slice

| Deferred behavior | Owning dependency |
| --- | --- |
| Manuscript READY/PREPARE affirmative Decision commands and typed Decision basis | Separate Decision extension; preserve Minimal Decision 20 as shipped |
| Internal release, READY transition, package freeze, consumption/receipts | Owning effect contracts; R2/R3/R4 transaction, result-FK and receipt requirements |
| Reconsideration after rejection | Governance R2 §2 all-rejections typed Decision/RevisionAction basis and cycle checks; no B09 bypass |
| Issue disposition/carry-forward across target versions | Separate Issue lifecycle/concern policy; RevisionAction does not close Issues |
| Consent, withdrawals, prepared-package manifest and freeze | Publication/consent contract beyond PR2-17 attribution foundation |
| Grant revoke/expire/withdraw commands, scheduled evaluators | Separate lifecycle contract; no read-side writes or background subsystem |
| External send, SubmissionVersion, ExternalEffect, generalized policy engine | Later authorized slice; never implied by approval |

## 13. Open questions for the owner — override register

| Owner may override | Decision adopted in this draft |
| --- | --- |
| Build manuscript Decision here? | No; dependency gate explicit. Approve a separate compatible Decision extension before admitting those branches. |
| Rejection scope/recovery? | R2 project/purpose equivalence; no recovery here. Pending requests cannot bypass; stale other unused same-scope grants atomically. |
| Conditions/bounds? | Retain finite-expiry conditional model, 100 review IDs and 16,384-character rationale for new submissions; exact prior longer history remains readable. Consent condition only strengthens PREPARE. |
| Lock/read protocol? | N SHARE as first READ COMMITTED statement; existing project/purpose scope and target coordination; all reads/replay lock-free RR; no new persistence mechanism. |

These proposed refinements need owner disposition before freeze. No unanswered
question authorizes relaxing a scientific invariant or implementing later work.

## 14. Documentation verification note

Only this proposal is authored. Future B09 tests in §12.4 do not yet exist.
Documentation-task evidence, 2026-10-15, uses the already installed environment
because the sandbox denies the default uv cache. Equivalent common prefix used
on every successful tool launch below:

```sh
export UV_CACHE_DIR=/tmp/researchbase-b09-uv-cache
export UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv
export PYTHONPATH=src
```

| Exact command after that prefix | Observed result |
| --- | --- |
| `uv run --no-sync ruff check .` | PASS, “All checks passed!” |
| `uv run --no-sync ruff format --check .` | PASS, 570 files already formatted |
| `uv run --no-sync pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject` | PASS, 0 errors, 0 warnings, 0 informations |
| `git diff --check` | PASS, no output |
| `uv run --no-sync pytest tests/unit tests/architecture` | 2,342 passed, 5 failed, 12 errors, 7 warnings in 45.47s; not PASS |
| `uv run --no-sync pytest tests/unit/test_approval.py tests/unit/phase2/test_pr2_15_decision.py tests/architecture/test_basic_approval.py` | 55 passed, 1 warning in 0.59s |
| `uv run --no-sync pytest tests/unit/phase2/test_pr2_04_static_acceptance.py --tb=short` | Failure reproduced: 1 failed, 1 warning in 4.06s; its nested Pyright uses the unpopulated local .venv and reports missing imports |
| `DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run --no-sync pytest tests/integration/phase2/test_approval.py tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_b05_manuscript_review.py -x` | 1 setup error in 0.36s, stopped before test execution: localhost socket connections denied with “Operation not permitted”; remaining cases not run |

Four broad-run failures are HG1 runner socket-bind permission errors; the fifth
is the nested static-check environment lookup reproduced above. The 12 architecture
setup errors require RB_TEST_ADMIN_URL; setting it explicitly in the focused
PostgreSQL attempt then demonstrates the socket restriction. A disposable 18.x
`initdb` attempt also failed on sandbox-denied `shmget`; no server-version query
or PostgreSQL assertion completed. Initial ordinary `uv run` attempts failed
before checks started (cache permission, then uncached offline dependencies).
An initial Pyright launch without `--venvpath` reported 1,010 errors/2 warnings
from unresolved local-environment imports; the corrected launch above passed.

A local Python/AST check resolved all 25 relative links, matched all 17 listed
ErrorCode HTTP/CLI pairs to the current source maps, and verified the required
status and 14 numbered sections. Environment failures are not PASS. The owner's
loop owns the full suite; it was not run here. No implementation, acceptance or
Phase-exit claim follows from this draft.
