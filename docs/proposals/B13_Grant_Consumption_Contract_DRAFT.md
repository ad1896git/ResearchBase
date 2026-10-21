# B13 Approval Grant Consumption and Lifecycle Contract — DRAFT

**Status: APPROVED by owner 2026-10-17 — first slice authorized for implementation**

## Start here (for the implementer)

B13 defines one-use grant consumption, immutable receipts, terminal events and an
explicit lifecycle evaluator. Approval authorizes; an owning Application command
performs its local effect. The effect, receipt, consumption and grant event either
all commit or all roll back. Prepared does not mean sent.

Read §§1–4 first; use §10 for terms, §11 for fixed draft choices and §12 for the
construction plan. Contract approval and implementation authorization are separate.
The owner reports B07–B11 approved, with code being implemented in parallel. Build
on those contracts even where this branch has only their prerequisites. B12 is a
draft dependency. B14 must bind the concrete effects; this document does not
implement or authorize any of them.

Build after separate authorization, in this order:

1. Reconcile accepted B09/B12 dependencies and the actual migration head (§1).
2. Add the registered receipt and lifecycle guards without editing old migrations
   (§12.1). Enable a result branch only with its concrete B14 binding.
3. Add pure request normalization and the shared grant evaluator (§11.3), then
   Application orchestration and repository ports at the paths in §12.3.
4. Implement the exact command sequences and participating-writer matrix (§12.2).
5. Add §12.4 tests; execute focused checks, retain exact evidence and stop (§12.5).

Five review rules:

1. Only the three finite B09 tuples consume permission; max_uses remains one.
2. Recheck exact frozen closure, independent basis, blockers, consent and live
   authority at fresh post-wait database time. Authority cannot validate bad facts.
3. Commit exactly one concrete result, receipt and ACTIVE→CONSUMED event together.
4. Never reactivate a terminal grant. Expiry and authority loss deny immediately,
   without depending on a scheduler or a read-side write.
5. Completed replay is an entitled historical read in one REPEATABLE READ snapshot,
   without table, advisory or row locks and without rerunning first-use gates.

## 1. Purpose, authority and inspected baseline

| Source | Constraint carried forward |
| --- | --- |
| [System 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 7–13; [Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A17–A23 | Facts precede authority; exact frozen provenance; immutable history; Review ≠ Decision ≠ Approval ≠ Command ≠ ExternalEffect; current entitlement for completed replay. |
| [Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md); [Cross-Phase 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§9–18, 24, 28 | Reuse registered ApprovalGrantConsumption and events; concrete RESTRICT references, common Application boundary, additive compatibility. |
| [Phase 2 specification 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), governance/publication and PR2-16/17; [Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), §§4–7 | Separate authorization and execution; mandatory preparation consent; local preparation never implies submission. |
| [Field contract 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md), approval and publication rows; [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md), governance payloads | Concrete result XOR, unique grant/key, append-only consumption/events; retain existing scientific and approval hashes. |
| [Governance R2 17](../architecture/17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md), §§1–3 | Three finite tuples, finite one-use scope, atomic effects/events, terminal-only lifecycle and effective-time staleness. |
| [R3 18](../architecture/18_Phase2_Design_R3_Targeted_Remediation_v1.0.md), §5 and grant vectors; [Temporal R4 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md), §§1, 4–5 | Literal normalized request/hash, global command key, versioned DTO projection, SERIALIZABLE effect transaction; fresh post-lock clock and historical completed replay. |
| [Minimal Decision 20](../architecture/20_PR2_15_Minimal_Decision_Command_Contract_v1.0.md); [Harness 09](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 18–21 | Preserve bounded Decision semantics, Application writes only and evidence before acceptance. |
| [B09](B09_Approval_Tuples_Contract_DRAFT.md), §§3, 7, 11–12; [B12](B12_Prepare_Submission_Decision_Contract_DRAFT.md), §§3, 11–12 | Exact grant scope and rejection fence; distinct PREPARE Decision; lowercase grant command versus uppercase receipt enum. |
| [B07](B07_Revision_Decisions_Contract_DRAFT.md), [B08](B08_Issue_Disposition_Contract_DRAFT.md), [B10](B10_Rejection_Reconsideration_Contract_DRAFT.md), [B11](B11_Ready_For_Submission_Decision_Contract_DRAFT.md) | Preserve separate revision/disposition/reconsideration/readiness purposes, finite concern reachability, complete basis and shared purpose-scope coordination. |

Inspected branch, 2026-10-16: [0045](../../migrations/versions/0045_pr2_16_basic_approval.py)
creates six approval tables and release-only policy. Grant status already lists
all five states, but its update guard and event CHECK admit only ACTIVE→STALE.
[ApprovalService](../../src/researchbase/application/approval.py) exposes request,
decide and three exact reads; no consumption or receipt. Its usability projection
checks expiry/approver and its read preparation still locks. B09 contracts the
necessary replacements; do not describe them as shipped here.

[0035](../../migrations/versions/0035_pr2_12_publication_draft.py) permits only
DRAFTING publication events; its basis consumption UUID has no receipt FK yet.
[B04](../../src/researchbase/persistence/manuscript_freeze_repository.py) and
[B05](../../migrations/versions/0049_b05_manuscript_review.py) provide manuscript
seal/review prerequisites; [0046](../../migrations/versions/0046_pr2_17_authorship_preparation.py)
is attribution foundation, not consent or package freeze. The migration inventory
reaches 0051/B06. Reconcile the actual head before implementation; reserve no number.

[UoW](../../src/researchbase/persistence/uow.py) already supplies
`begin_serializable`, SQLSTATE normalization and synchronous transactions.
[Decision](../../src/researchbase/persistence/decision_repository.py),
[novelty](../../src/researchbase/persistence/novelty_repository.py) and B04 supply
existing SQL table-lock mechanisms; coverage/B04 demonstrate FIRST-SQL SHARE
protection. [0042](../../migrations/versions/0042_pr2_15_minimal_decision.py)
supplies deferred final-graph constraint triggers. No B13 execution pack is present.
Source presence and owner-reported contract approval are not acceptance evidence.

## 2. Scope, dependency boundaries and non-goals

Contract the common consumption operation used inside the three owning commands,
`get_grant_consumption`, `revoke_approval_grant`, and one-grant
`evaluate_approval_grant`. Reuse B09 `get_grant` for read-only diagnostics. There
is no public generic consume endpoint, independent mark-consumed command, batch,
sweeper, queue, outbox or new top-level canonical object.

B13 owns grant lifecycle and receipt integrity. B14 owns release/READY/package
postconditions, their concrete FK/event guards and effect DTOs. Package tables,
consent chains/withdrawal and B12's accepted implementation are prerequisites to
freeze. No placeholder result, fake READY state or JSON-only success may bridge a
missing dependency. The complete DDL sketch below is a joint binding requirement,
not permission to create a missing B14 publication model inside B13.

## 3. Invariants and conservative judgments

| Purpose | Grant command → receipt command | Exact target and atomic result |
| --- | --- | --- |
| INTERNAL_SCIENTIFIC_RELEASE | `record_internal_scientific_release` → RECORD_INTERNAL_SCIENTIFIC_RELEASE | FROZEN VALID ScientificConclusionVersion; result conclusion equals target. Consumption itself is the release fact; material is unchanged. |
| READY_FOR_SUBMISSION | `transition_publication_ready` → TRANSITION_PUBLICATION_READY | FROZEN VALID ManuscriptVersion; result is its Publication, INTERNAL_REVIEW→READY with a lifecycle event citing basis Decision and consumption. |
| PREPARE_SUBMISSION | `freeze_prepared_submission` → FREEZE_PREPARED_SUBMISSION | FROZEN VALID ManuscriptVersion in READY Publication; result is the exact precreated same-Publication PREPARED package frozen with complete validated manifest/authorship/current consent. |

First use requires ACTIVE Project, active grant, `t < valid_until`, live verified
RESEARCHER/OWNER caller and issuing independent HUMAN's effective APPROVER
credential/role at fresh DB time. Verify the immutable request/decision/grant
chain, exact target/hash/scheme, matching affirmative Decision and complete saved
review basis; verify all later matching reviews and applicable OPEN BLOCKING
Issues through B08/B11/B12 finite reachability. A valid authorized disposition
history is required before excluding a blocker. Rejection/reconsideration follows
accepted B09/B10 scope rules; a new favorable Decision never clears the fence.

Revalidate full frozen scientific closure, CAS bytes where required, deterministic
current validity, material-author independence and typed conditions. PREPARE
always requires current direct-author consent even if its approval stored false.
A later review is checked but does not silently change the receipt's bound review
set. An exact previously frozen target may now carry SUPERSEDED navigation state:
verify its unchanged seal and current validity; navigation alone cannot deny use.
Actual newer-target selection for this purpose still stales the old grant. Hash equality alone proves neither validity nor consent.

Lifecycle is ACTIVE→CONSUMED / EXPIRED / REVOKED / STALE only. No terminal update,
terminal-to-terminal conversion or reactivation. Exact frozen SUPERSEDED navigation
alone is not staleness; new target selection, invalid upstream facts, blockers,
withdrawn required consent or lost issuing authority can stale unused permission.
Existing authority-loss and B09 rejection/new-target writers retain atomic STALE
events. Already CONSUMED grants remain historical even if today's gates fail.

### 3.1 Evaluator and terminal precedence — proposed refinement

One pure evaluator returns stored status, current usability, one denial code,
complete reason codes and evaluated_at. It never writes. For ACTIVE grants:
expiry first yields EXPIRED/GRANT_INVALID; otherwise lost approver authority,
new-target selection, rejection fence, invalid target/closure, blocker or required
consent loss yields STALE/GRANT_STALE. Corrupt immutable history raises
PROVENANCE_CLOSURE_VIOLATION rather than manufacturing a valid terminal history.
A missing concrete effect/consent dependency yields APPROVAL_GATE_FAILED and no
terminalization; implementation incompleteness is not evidence of consent loss.
Caller write-role loss denies that caller, not the grant for every eligible caller.

The explicit evaluator command persists the chosen terminal status and one event
when ACTIVE is unusable; otherwise returns unchanged status and no event. It
needs current OWNER authority; read entitlement alone cannot mutate history.
Revocation also requires effective OWNER and a reason. It first applies the same
expiry/staleness evaluation: a grant already effectively unusable records that
cause; an otherwise usable ACTIVE grant becomes REVOKED. Terminal input returns
verified existing history without appending an event, after current OWNER checks.
No command promises a new idempotency receipt for lifecycle maintenance: the
locked one-way state transition itself prevents duplicate terminal events.

Scheduled expiry takes effect without a write. The explicit evaluator is the
first observing maintenance command that persists it. A denied first-use command
rolls back all its writes, including attempted terminal maintenance. Run an
independent explicitly invoked evaluator to retain that observation; never hide a
second committed transaction behind a failed consumption. This separation is a
proposed clarification of R2's “first observing command,” requiring owner approval.

## 4. Proposed commands, DTOs and historical readback

Closed immutable DTOs and strict types are pinned in §11.3. The trusted principal
is separate; server derives actor, DB times, target scope and canonical review
set from the exact grant chain. Owning commands accept the R3 request fields only;
no free-form mutable effect arguments. Protected existence and conflict disclosure
follow authentication and project read entitlement.

`get_grant_consumption(project_id, command_key)` returns exact receipt/result
history under current project reader entitlement. Completed command replay also
requires the original actor/project. An OWNER cannot replay another actor's key
as their own command; an authorized audit read is a separate operation. Nested
source details require their existing object entitlement. Never return ORM rows.

The saved result DTO is an immutable versioned projection of the committed local
result, separate from fresh `evaluated_at`, grant usability and current validity.
Do not rewrite saved bytes to represent later supersession/consent loss. Saved
history remains readable after write-role loss, expiry, rejection or new blockers;
lost current credential/read entitlement denies disclosure.

## 5. Schema and literal hash proposal — no migration

Use registered `approval_grant_consumptions`, existing grants and events, exact
result FKs and the existing sealed `approval_request_reviews` relation (§12.1).
No persisted target copy,
new grant hash, generic locator, mutable reservation row or second command ledger.
The only semantic JSON is R3's explicitly allowed versioned replay projection;
concrete FKs and owning records remain authoritative.

The literal request has exactly R3 §5's keys: `type`, `material_version`, `command`,
`project_id`, `actor_id`, `grant_id`, `target:{type,id,content_hash}`, `result_id`,
`expected_package_manifest_hash`, `checked_review_ids`. Type is
ApprovalGrantConsumptionRequest; material_version is integer 1. Review IDs equal
the complete ApprovalRequest set, distinct and UUID-text sorted. Target is derived
from immutable request, not current pointers. Expected manifest hash is required
for freeze and JSON null otherwise. Result is conclusion target, owning Publication
or exact precreated package respectively. A generic target object is a hash value
only; persistence uses the concrete FKs.

Use existing canonical-json-v1/sha256-cjson-v1: compact recursively key-sorted UTF-8,
no BOM/newline, lowercase canonical UUIDs and 64-hex digests. Always include null.
Hash excludes command_key, generated consumption/event IDs, arrival/DB time and
saved DTO. Preserve R3 vectors, including review permutation equality and changed
grant inequality; preserve Phase 1 and ApprovalDecision hashes byte for byte.

## 6. Error contract — proposed use of existing categories

Use §11.2 at both adapters. Normalize named constraints/SQLSTATE through the
existing UoW; never match raw driver messages. Unexpected errors retain sanitized
HTTP 500/CLI exit 1 behavior. No SQL, CAS paths or credentials in errors. A failed
gate cannot be returned as a successful receipt or silently retried as a new key.

## 7. Transactions, concurrency and failure recovery

R3 requires one SERIALIZABLE UoW for a first effect; do not downgrade it to
READ COMMITTED to copy a neighboring service. Maintenance writes use READ
COMMITTED with FIRST-SQL SHARE protection. §12.2 protects mutable inputs before
the first snapshot-producing query, including rejection INSERT phantoms. SSI
alone does not refresh a snapshot after a wait or guarantee coordination with
READ COMMITTED writers. No external calls or artifact writes occur in a DB UoW.

Replay preflight is one lock-free REPEATABLE READ, READ ONLY UoW. Locate key,
authenticate/authorize, verify actor/project, compare canonical hash AND normalized
scope, validate complete saved receipt/result/history and return the saved result.
Changed material for the same entitled actor/project yields IDEMPOTENCY_CONFLICT;
wrong actor/project is nondisclosing FORBIDDEN. Different key means first use and
cannot reuse a consumed grant. Absent receipt takes the protected first-use path;
incomplete/corrupt receipt fails closed, never reconstructs success from a caller.

A racing writer that finds a committed key closes its writer UoW and opens the
same read-only replay path; no replay is returned from a locking verifier. A
unique-key race is resolved by verified receipt lookup, not by calling every
integrity error success. Uncertain commit is recovered with the original key.

Retry only SQLSTATE 40001/40P01, at most three total fresh UoWs, no delay; redo all
locks, reads, hashes and live-clock authorization. No automatic timeout, business
conflict, unrelated uniqueness or uncertain-commit retry. After required waits,
read durable state again; at SERIALIZABLE a concurrently changed locked row must
abort/retry rather than claim a refreshed snapshot. Use clock_timestamp(), never
now()/transaction_timestamp(), with half-open expiry bounds. Force deferred checks
before final fresh-clock authorization; any subsequent required wait forces a
renewed check. Failure, including final expiry, rolls back effect/receipt/events.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

§12.4 fixes files/cases: independent R3 hash vectors; all tuples and substitutions;
atomic result/receipt/event completeness; terminal/evaluator behavior; direct SQL
bypass; entitled historical replay; real wait/expiry, two-key/one-grant and
same-key races; compatibility with all participating writers. Planned tests are
not current implementation evidence.

## 9. Acceptance criteria and evidence boundary

Owner approval and separate authorization precede implementation. Reconcile B09,
B12 and concrete B14 bindings before enabling a consumption branch. No branch is
accepted from mocked effect success or missing-FK stubs. Run static, unit,
architecture and affected PostgreSQL 18.x suites, with exact commands/counts,
server version and no open P0/P1. A bounded foundation may be reviewed separately
but is not full consumption, B14, PR2-17 or Phase 2 acceptance. The owner's loop
runs the whole suite; this documentation task does not.

## 10. Glossary

| Term | Meaning |
| --- | --- |
| Grant | B09's one-use finite authorization derived through decision/request |
| Consumption / receipt | One registered immutable record binding key/hash to exact local result |
| Command key | UUID globally unique across all three consuming commands |
| Effect | Local release fact, READY transition or package freeze; no external send |
| Terminal event | Append-only ACTIVE→CONSUMED/EXPIRED/REVOKED/STALE history |
| Evaluator | Pure current-usability calculation; explicit maintenance command may persist its result |
| Replay | Entitled historical retrieval of a matching completed command |
| N / W / A | Fixed input, mutable-effect and approval-input table inventories in §12.2; not entities |

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

Adopt R2/R3/R4 finite effects, literal request and SERIALIZABLE atomic consumption.
Use one-grant explicit OWNER maintenance, no scheduler or lifecycle receipt ledger.
Adopt expiry-before-staleness-before-explicit-revocation precedence and §3.1's
observation clarification. Keep B09 rejection/reconsideration and all terminal
history intact. B14 supplies concrete effect/DTO bindings. Transport exposure is
deferred; mappings are fixed now. §12.2's coarse publication-table coordination is
a proposed compatible use of existing locks, not a new persistence mechanism.

**Decision (a): reuse registered relations; remove
`approval_grant_consumption_reviews`.** R3 §5 requires `checked_review_ids` to
equal the exact finite ApprovalRequest review set, so consumption adds no
independent review membership fact. Each receipt resolves that set through
`grant_id → approval_grants.approval_decision_id →
approval_decisions.approval_request_id → approval_request_reviews.request_id`;
its review FK resolves to `internal_review_records.id`. The request's
`basis_decision_id → decision_basis_reviews.decision_id` supplies the independent
basis equality check. These are the typed relations admitted by Addendum A18,
Correction 12 and Governance R2 17 §1, and implemented in migration 0045.
`revision_actions`, `review_issues` and their existing basis/event relations retain
their disposition/blocker roles; no receipt-specific copies are needed. Later
reviews remain live first-use gates, never additional members of this sealed set.
No new relation table, FK, index or trigger for consumption-review children is
proposed. This uses one canonical owner per membership fact under AGENTS.md §§4/11
and Registry 03 §§8/12; no architecture schema admission is requested.

### 11.2 Pinned error mappings

These pairs match [api/errors.py](../../src/researchbase/api/errors.py) and
[cli/errors.py](../../src/researchbase/cli/errors.py). No new ErrorCode.

| Code | HTTP | CLI exit | Use |
| --- | --- | --- | --- |
| VALIDATION_ERROR | 422 | 2 | Closed fields/types/bounds, duplicate reviews, malformed hash/key |
| AUTHENTICATION_REQUIRED | 401 | 3 | Missing/unverifiable live principal |
| FORBIDDEN | 403 | 3 | Caller role/read entitlement or replay actor/project mismatch |
| CONFLICT_OF_INTEREST | 403 | 3 | Required actor independence fails |
| NOT_FOUND | 404 | 3 | Authorized exact grant/key/result absent |
| APPROVAL_PURPOSE_TARGET_COMMAND_INVALID | 409 | 4 | Well-formed command outside finite tuple |
| DECISION_BASIS_INVALID | 409 | 4 | Wrong/incomplete affirmative Decision/review basis |
| APPROVAL_GATE_FAILED | 409 | 4 | Lifecycle/blocker/condition gate or missing effect dependency |
| APPROVAL_TARGET_STALE | 409 | 4 | First-use target state/hash/current validity mismatch |
| REJECTION_RECONSIDERATION_REQUIRED | 409 | 4 | Unresolved purpose-scope rejection fence |
| GRANT_INVALID | 409 | 4 | Expired, CONSUMED or REVOKED first-use grant; no matching receipt |
| GRANT_STALE | 409 | 4 | Stored STALE or effective issuing authority/material staleness |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Same key, entitled actor/project, different normalized request |
| CONCURRENT_MODIFICATION | 409 | 4 | Exhausted 40001/40P01 or genuine concurrent conflict |
| IMMUTABLE_RECORD | 409 | 4 | Receipt/event edit, late child or terminal rewrite |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Corrupt saved hash/receipt/closure/history |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Exact concrete FK/result-parent inconsistency |

First-use diagnostics may retain specific gate codes above; evaluator persists
STALE with complete cause codes when there is verified material/authority loss.
Terminal read diagnostics use GRANT_INVALID for CONSUMED/EXPIRED/REVOKED and
GRANT_STALE for STALE. This refines the current service's all-terminal GRANT_STALE
projection; preserve history and test the explicit compatibility change.

### 11.3 DTO fields, Python types, limits and enums

All dataclasses frozen/closed; API objects, if later authorized, forbid extras.
Strict UUID means uuid.UUID in Application, parsed canonical UUID at adapters;
no integers/coercive booleans. Text is NFC, rejects invalid Unicode/blank values.
Times are aware UTC datetime.datetime; caller never supplies effective time/status.

| DTO/field | Python type and rule |
| --- | --- |
| Owning effect input: command_key, project_id, grant_id, result_id | UUID, required; result_id fixed by §3, not a free alternate target |
| Owning effect input: command | strict str derived from owning method; three uppercase receipt literals in §3; unlisted well-formed tuple is 409 |
| Owning effect input: expected_package_manifest_hash | str or None, always represented; lowercase 64-hex for freeze, None otherwise |
| Owning effect input: checked_review_ids | tuple[UUID, ...], required, 1..100 distinct UUIDs, equals B09 saved request set; sort canonically, never truncate |
| Derived hash-only target | Closed value: type Literal['ScientificConclusionVersion','ManuscriptVersion'], id UUID, content_hash str (64 lowercase hex) |
| Derived hash-only fields | type Literal['ApprovalGrantConsumptionRequest'], material_version Literal[1] (strict int), actor_id UUID from principal, project/grant/target/result as above |
| RevokeApprovalGrantCommand | project_id UUID, grant_id UUID, reason str, 1..16,384 NFC code points; no caller actor/time/status/key |
| EvaluateApprovalGrantCommand | project_id UUID, grant_id UUID only; one exact grant, no scan/filter/batch |
| Exact receipt read | project_id UUID, command_key UUID |
| GrantEvaluation | grant_id UUID; stored_status Literal['ACTIVE','CONSUMED','EXPIRED','REVOKED','STALE']; usable bool; proposed_terminal_status Literal['EXPIRED','STALE'] or None; unusable_code str or None; reason_codes tuple[str, ...] (distinct existing ErrorCode values sorted lexically); evaluated_at datetime |
| Lifecycle readback | B09 grant readback plus evaluation and event_ids tuple[UUID, ...] in (occurred_at,id) order; no new lifecycle DTO persistence |
| ConsumptionReadback | id, project_id, grant_id, command_key, actor_id UUID; consumed_at datetime; command same three literals; request_hash str (64 lowercase hex); hash_scheme Literal['sha256-cjson-v1']; checked_review_ids tuple[UUID, ...]; three nullable result UUID fields under §3 XOR; result_dto_version strict int=1; result typed union below |
| Saved result v1 | Closed discriminated union: command literal plus scientific_conclusion_version_id UUID, publication_id UUID, or prepared_submission_version_id UUID respectively, and consumption_id UUID; no mutable current-validity fields |

B14 owning command readbacks may wrap this minimal stable result projection with
fresh diagnostics; changing saved projection needs a new positive SMALLINT DTO
version and explicit decoder, never an in-place rewrite. Hash material has no
extra semantic keys. New admission limit 100 matches B09; historical verified
records are read without retroactive truncation. Source/Issue diagnostic sets are
complete and uncapped. Grant expiry remains B09's finite maximum 720 hours; no
new caller-controlled expiry or max_uses field. All event states are the five
stored grant states; creation NULL→ACTIVE, terminal transitions only from ACTIVE.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

Forward revision after accepted dependencies/current head; never edit 0042/0045.
Types and names below are pinned proposed additions. Package FK is enabled only
when its accepted owning table exists; absent package schema blocks full DDL.
Do not substitute a soft reference. All FKs ON DELETE RESTRICT.

```sql
CREATE TABLE approval_grant_consumptions (
 id UUID CONSTRAINT pk_b13_consumptions PRIMARY KEY,
 grant_id UUID NOT NULL CONSTRAINT uq_b13_consumption_grant UNIQUE
   CONSTRAINT fk_b13_consumption_grant REFERENCES approval_grants(id) ON DELETE RESTRICT,
 command_key UUID NOT NULL CONSTRAINT uq_b13_command_key UNIQUE,
 project_id UUID NOT NULL CONSTRAINT fk_b13_consumption_project REFERENCES projects(id) ON DELETE RESTRICT,
 actor_id UUID NOT NULL CONSTRAINT fk_b13_consumption_actor REFERENCES actors(id) ON DELETE RESTRICT,
 consumed_at TIMESTAMPTZ NOT NULL,
 command VARCHAR(40) NOT NULL,
 request_hash CHAR(64) NOT NULL,
 hash_scheme VARCHAR(32) NOT NULL,
 result_dto_version SMALLINT NOT NULL,
 result_dto JSONB NOT NULL,
 result_publication_id UUID CONSTRAINT fk_b13_result_publication REFERENCES publications(id) ON DELETE RESTRICT,
 result_prepared_submission_version_id UUID CONSTRAINT fk_b13_result_package
   REFERENCES prepared_submission_versions(id) ON DELETE RESTRICT,
 result_scientific_conclusion_version_id UUID CONSTRAINT fk_b13_result_conclusion
   REFERENCES scientific_conclusion_versions(id) ON DELETE RESTRICT,
 CONSTRAINT ck_b13_hash CHECK(request_hash ~ '^[0-9a-f]{64}$' AND hash_scheme='sha256-cjson-v1'),
 CONSTRAINT ck_b13_time CHECK(isfinite(consumed_at)),
 CONSTRAINT ck_b13_dto CHECK(result_dto_version=1 AND jsonb_typeof(result_dto)='object'),
 CONSTRAINT ck_b13_result_tuple CHECK (
  (command='RECORD_INTERNAL_SCIENTIFIC_RELEASE' AND result_scientific_conclusion_version_id IS NOT NULL
   AND result_publication_id IS NULL AND result_prepared_submission_version_id IS NULL) OR
  (command='TRANSITION_PUBLICATION_READY' AND result_publication_id IS NOT NULL
   AND result_scientific_conclusion_version_id IS NULL AND result_prepared_submission_version_id IS NULL) OR
  (command='FREEZE_PREPARED_SUBMISSION' AND result_prepared_submission_version_id IS NOT NULL
   AND result_scientific_conclusion_version_id IS NULL AND result_publication_id IS NULL))
);
CREATE INDEX ix_b13_consumption_project ON approval_grant_consumptions(project_id,consumed_at,id);
CREATE INDEX ix_b13_consumption_actor ON approval_grant_consumptions(actor_id);
-- No consumption-owned review relation. Existing read path (bind :consumption_id):
-- SELECT rr.internal_review_record_id
-- FROM approval_grant_consumptions c
-- JOIN approval_grants g ON g.id=c.grant_id
-- JOIN approval_decisions d ON d.id=g.approval_decision_id
-- JOIN approval_requests r ON r.id=d.approval_request_id
-- JOIN approval_request_reviews rr ON rr.request_id=r.id
-- WHERE c.id=:consumption_id ORDER BY rr.internal_review_record_id::text;
-- Add partial nonnull indexes ix_b13_result_publication / ix_b13_result_package /
-- ix_b13_result_conclusion on their respective result FK columns.
```

Reconstruct `checked_review_ids` by the existing typed FK path in §11.1,
UUID-text sorted, and verify nonempty exact equality with `decision_basis_reviews`
and the normalized command input before consumption. No consumption-review rows
are inserted. The saved request material/hash and readback derive membership
from the same sealed request relation, never from today's eligible review query
or a JSON ID list. Migration 0045's `pr216_review_insert`/`pr216_relation_guard`
permits relation INSERT only in the parent request's creation transaction while
PENDING; `pr216_review_immutable` rejects UPDATE/DELETE and `pr216_complete_reviews`
checks complete Decision basis equality. Preserve these guarantees in accepted
B09 dependencies, plus immutable grant/decision/request linkage and RESTRICT FKs.
First-use and readback must fail closed on a missing/empty/mismatched chain or
request-hash mismatch. No opaque request JSON is a second owner.

B14 adds concrete DEFERRABLE INITIALLY DEFERRED
`fk_b14_ready_consumption` on publication_lifecycle_events.basis_grant_consumption_id
and its corresponding package event FK; it must also replace 0035's DRAFTING-only
checks and UNIQUE(publication_id) under its own lifecycle contract. Do not
silently broaden those restrictions in B13.

| Named guard/constraint | Required behavior |
| --- | --- |
| b13_consumption_guard | SERIALIZABLE, preheld §12.2 locks, actor/project/tuple, exact immutable grant chain and result-parent dispatch; validate current first-use gates and literal request hash. Require grant was ACTIVE before the operation, one-use uniqueness and same-transaction effect. No standalone receipt without effect. |
| b13_consumption_immutable | Reject receipt UPDATE/DELETE; preserve existing request-review sealing and immutable linkage guards; no pruning history. |
| b13_complete_consumption / b13_complete_grant | DEFERRABLE INITIALLY DEFERRED constraint triggers on receipt INSERT and grant INSERT/UPDATE; bidirectional CONSUMED iff one complete receipt, exact nonempty request-review/Decision-basis equality via §11.1, correct result DTO and hash, exactly one matching terminal grant event; terminal nonconsumed grants have no consumption. Validate final graph, not intermediate inserts. |
| b13_grant_transition_guard | Replace pr216_grant_guard update branch narrowly; only ACTIVE→terminal, scope immutable; CONSUMED requires same-transaction receipt/effect, EXPIRED fresh clock evidence, STALE concrete verified cause, REVOKED live OWNER and retained reason. Preserve creation and authority/new-target/rejection guards. Trigger depth/session flags alone never prove cause. |
| ck_b13_grant_event_status / b13_grant_event_guard | Replace old ACTIVE/STALE event CHECK with five states; creation exactly NULL→ACTIVE and terminal events exactly ACTIVE→terminal. Retain automatic creation/authority-loss events; command transitions carry their actual caller/reason through the validated terminal-event protocol below. Deny forged event append/update/delete and duplicate terminal event. |
| uq_b13_one_terminal_event | Partial UNIQUE(grant_id) on approval_grant_events WHERE prior_status='ACTIVE'; retain creation event and every accepted existing STALE event. |
| B14 complete-result guards | Both directions: READY/package transition iff exact matching consumption in same transaction, matching Decision, Publication/manuscript/package, manifest hash and actor/time. Release has no second result table. Cannot enable branch until these guards are accepted. |

For command transitions, insert the terminal event under the held grant lock,
then update grant status in the same UoW. The event guard verifies ACTIVE prior
state, actual command actor/role/cause and DB time; deferred checks require the
matching final grant state. Refactor the existing automatic status-event producer
to reuse only that exact validated event inserted in the current transaction,
otherwise generate its existing authority/new-target/rejection STALE event. Never
skip production based solely on an event's existence or a session flag. Receipt
and event actor agree for consumption; maintenance records the invoking OWNER,
reason and observation time. Creation/authority-trigger attribution is preserved.
Deferred completeness must also be attached to event INSERT so an orphan or a
second terminal event cannot commit; add `b13_complete_terminal_event`.

Functions use `SET search_path = pg_catalog, public, pg_temp`. SQL guards require
preheld real table locks/isolation, not caller-controlled flags; normal-role SQL
must satisfy the same final graph/authority checks. Application verifies actual
trusted live credentials and CAS bytes; database structural guards do not claim
to authenticate external credentials. Preserve immutable material and accepted
old events/hashes. Populated downgrade refuses consumption/terminal-history loss;
empty-slice downgrade can restore predecessor constraints after validating data.

### 12.2 Exact lock order and transactions

Freeze literal inventories in adapter/migration; test equality to these source
lists, no catalog discovery or silent inheritance. N is the sorted literal
B04_SNAPSHOT_TABLES from manuscript_freeze_repository.py plus
`manuscript_versions`, `internal_review_records`, `review_issues`,
`review_issue_events`. W is `publications` for **every** B13 writer, plus
`prepared_submission_versions` for freeze only. A is `approval_decisions`,
`approval_request_reviews`, `approval_requests`, in that order. N/A are never
written by B13. Publication belongs only to W: never SHARE-lock it and upgrade.
The accepted consent binding must add its concrete consent inputs to N before
freeze is enabled; B14 must pin that literal extension and withdrawal protocol.

Configure isolation and disable autoflush without SQL. FIRST SQL is
`LOCK TABLE <N, sorted> IN SHARE MODE`. Next lock `publications IN SHARE ROW
EXCLUSIVE MODE`, then package table in that same mode for freeze, then one
`LOCK TABLE <A, sorted> IN SHARE MODE`. All these table locks precede any SELECT,
advisory call, SET LOCAL or snapshot-producing query. No lock upgrade. This
coarse publication lock deliberately serializes B13 writers; lock-free reads
continue normally. It also excludes B09/B10/B11/B12 writers at their initial
Publication SHARE lock before they reach scope/target/grant locks. A then protects
rejection and approval INSERT phantoms before a SERIALIZABLE snapshot is chosen.
Do not claim a later advisory wait can refresh that snapshot.

Set connection/server timeout bounds before UoW entry for these initial waits;
then SET LOCAL lock_timeout='10s' and statement_timeout='30s'. The latter cannot
bound an earlier wait. For consumption use existing begin_serializable before
SQL; maintenance uses READ COMMITTED. Keys use existing parameter-bound
pg_advisory_xact_lock/hashtextextended convention with canonical UUID text.

| Command | Exact sequence after N → W → A and local timeouts |
| --- | --- |
| record_internal_scientific_release | SERIALIZABLE; advisory `b13:consume:{command_key}`; plain grant/request routing lookup; advisory `pr216:scope:{project_id}:{purpose}`; exact conclusion FOR UPDATE; owning scientific_conclusions FOR SHARE; request FOR SHARE; grant FOR UPDATE; reread; fresh reader then RESEARCHER/OWNER authorization; absence/key/scope and all first-use gates; final clock; verify UUID-sorted existing request reviews and insert consumption, insert terminal event and update grant CONSUMED; deferred/final checks then commit. Receipt itself is effect. |
| transition_publication_ready | SERIALIZABLE; same key advisory/routing/scope; exact manuscript FOR UPDATE; owning Publication FOR UPDATE; request FOR SHARE; grant FOR UPDATE; reread and all gates; final clock; preallocate consumption ID, perform B14 READY transition/event referencing it, insert receipt after verifying existing request reviews and update grant/event; deferred/final checks then commit. |
| freeze_prepared_submission | SERIALIZABLE; same key advisory/routing/scope; exact manuscript FOR UPDATE; Publication FOR UPDATE; exact precreated package FOR UPDATE; any older packages affected by B14 supersession in UUID order; request FOR SHARE; grant FOR UPDATE; exact consent-chain heads in accepted B14 author/UUID order; reread every protected input and gate; final clock; B14 freeze/manifest hashes/events and any supersession, receipt with verified existing request reviews, grant/event; deferred/final checks then commit. Missing consent lock binding blocks this branch. |
| revoke_approval_grant | READ COMMITTED; advisory `b13:lifecycle:{grant_id}`; plain routing lookup; same pr216 scope; target FOR UPDATE; owning conclusion FOR SHARE or Publication FOR UPDATE; request FOR SHARE; grant FOR UPDATE; reread; authorize reader and OWNER at fresh clock; verify saved history, evaluate; terminal returns unchanged, otherwise persist §3.1 cause or REVOKED with reason and one validated terminal event; deferred/final checks then commit. No package/consent row locks; fixed consent N protection required if evaluating that branch. |
| evaluate_approval_grant | READ COMMITTED; same lifecycle advisory/routing/scope/target/parent/request/grant order as revoke; fresh reader/OWNER authorization; verify and evaluate; ACTIVE→EXPIRED/STALE plus event or unchanged; deferred/final checks then commit. |
| get_grant / get_grant_consumption / completed replay | One REPEATABLE READ, READ ONLY UoW; plain parent/UUID-sorted existing request-review/result/event reads and saved-hash verification; current entitlement/diagnostics at fresh clock; final read entitlement check. No explicit table, advisory or row locks, FOR SHARE/FOR UPDATE, writes or status maintenance, including inside helpers. |

Before any mutation, use fresh clock_timestamp() after all waits; verify actual
caller/issuer credential, actor, binding, membership/role, grant expiry, exact
validity and consent. Force SET CONSTRAINTS ALL IMMEDIATE; check advancing time
again and roll back if any authorization expired. Repeat checks after any later
required wait. Grant events retain observed DB time, not a fabricated scheduled
expiry time. Deferred cyclic result references resolve on the complete graph.

| Participating writer | Compatibility requirement |
| --- | --- |
| B09 request/decision/REJECT/new-target and B10 reconsideration | Adopt approved SHARE-first inventory including publications before scope/target/grants. B13 W excludes them before snapshot creation; same pr216 purpose namespace retained. Their automatic grant updates prelock UUID order. Old target-first approval helpers must be replaced before acceptance. |
| B11/B12 manuscript Decision | Their initial Publication SHARE conflicts with W; immutable basis stays sealed. No grant-to-Decision reverse lock. |
| Review/Issue writers, including B08 disposition | Normal ROW EXCLUSIVE conflicts with N SHARE, including INSERT phantoms; retain exact-target row coordination and complete issue-history validation. |
| Scientific/placement/validity/source and authority writers | N SHARE excludes their ordinary mutations before B13 snapshot; authority-loss updates/event remain in the authority transaction. They must not take B13 scope after holding grant locks. |
| Publication lifecycle/package/consent writers | B14 acquires N and final W modes before snapshot, then manuscript→Publication→packages→request→grant→consent rows. Withdrawal must use compatible parent coordination, stale unused grants/events atomically, never rewrite consumed receipts. Missing concrete consent inventory/order is a B14 acceptance blocker. |
| Direct normal-role SQL | Same preheld inventory/isolation, scope and final-graph guards; no standalone terminal update or fabricated receipt. |

Old target-first scientific writers may still deadlock with table protection;
prove bounded whole-UoW 40P01 recovery and no stale success. Never claim the matrix
eliminates every legacy deadlock. Enabling B14 requires observed interoperability
in both commit orders and no unbounded retry. No read lock is added to solve races.

### 12.3 Ordered build steps and module paths

1. Reconcile accepted dependencies/head; add a forward revision under
   `migrations/versions/` for §12.1. Stage concrete result FKs with B14, refusing
   missing owners. Preserve 0045 history, sealed request-review/basis relations and
   existing payloads; add no consumption-review table/index/trigger.
2. Extend `src/researchbase/domain/approval.py` with finite receipt-command mapping,
   literal R3 material builder, closed evaluation/result values and pure terminal
   precedence. Reuse `src/researchbase/foundation/hashing.py`; no ORM/transport imports.
3. Extend `src/researchbase/application/approval.py` with maintenance/read DTOs and
   shared in-UoW consumption orchestration; add typed repository/UoW ports in
   `src/researchbase/application/ports.py`. Reuse B09's exact gate verification
   and B08/B11/B12 concern/basis rules; no nested service write transaction.
4. Extend `src/researchbase/persistence/approval_repository.py` with explicit
   prepare_write/prepare_read paths, literal inventories, receipt SQL, existing
   request-review joins and lifecycle mutations. Extend `src/researchbase/persistence/uow.py` for named
   constraint normalization, plain read helpers and isolated retry classification.
5. B14 binds its authorized owning commands in
   `src/researchbase/application/publication.py` and its SQL adapter
   `src/researchbase/persistence/publication_repository.py`, plus accepted package
   modules. Use the same UoW for effect and receipt; do not build those effects
   merely to exercise B13. Shared consumption returns no success before commit.
6. No routes/CLI exposure in this slice. Later adapters use
   `src/researchbase/api/routes.py`, `api/app.py`,
   `src/researchbase/cli/commands/governance.py` and `cli/composition.py`, trusted
   principal injection and §11.2 maps; no public generic consume endpoint.
7. Add §12.4 tests, run focused checks/dependent regressions, retain evidence and
   report unavailable branches. Stop; no new dependency or background service.

### 12.4 Test artifacts and required cases

Use existing approval/conclusion/manuscript fixture builders and disposable real
PostgreSQL 18.x via phase2_database_url. Two independent connections/backend PIDs,
barriers and pg_blocking_pids() prove waits; a sleep alone is not evidence. Future
B14 branches need accepted Application fixture paths, not disabled guards.

| File to create or extend | Required cases |
| --- | --- |
| tests/unit/test_approval.py | Exact closed fields/UUID/bool/int, 100/101 review IDs, duplicates/missing array, Unicode/reason boundaries, all tuples and null/hash rules; evaluator precedence/equality at expiry, caller loss versus issuer loss, incomplete dependency; independent R3 request vectors, review permutation/key exclusion and changed scope/grant/result/hash. |
| tests/unit/phase2/test_b13_grant_contract.py | Pure lifecycle/result union, frozen DTOs, no caller actor/time/status; version decoding and exact HTTP/CLI pairs; unchanged ApprovalDecision/Phase 1 vectors. |
| tests/integration/phase2/test_b13_grant_consumption.py | Release receipt is result; B14 READY/package concrete postconditions when available; all tuple/result substitutions, full CAS/closure/basis/independence/blocker/consent gates; atomic receipt+effect+grant+events with unchanged request-review rows; injection after each write and deferred/final check leaves zero partial history. |
| tests/integration/phase2/test_b13_grant_lifecycle.py | ACTIVE to each terminal exactly once; repeat evaluation/revoke no extra event, no reactivation/terminal rewrite; observed versus scheduled time; expiry without evaluator denies; authority-loss event atomicity; new target/rejection/upstream invalidity/consent withdrawal; superseded navigation alone harmless; denial creates no maintenance event. |
| tests/integration/phase2/test_b13_grant_replay.py | Same key/material saved result after expiry/write-role loss/new blockers/withdrawal; current credential/read loss and other actor/project nondisclosure; changed grant/command/result/reviews/hash conflicts; permutation replay; different key consumed-grant denial; restart/uncertain commit; empty/mismatched request-review basis, broken grant/decision/request chain or corrupt DTO/hash fails closed; identical UUID-sorted review readback with no copied relation; audit read distinct from original-actor replay. |
| tests/integration/phase2/test_b13_grant_schema.py | Clean/populated upgrade, exact types/constraint names/FK XOR/indexes, preserved old events/hash, populated downgrade refusal; normal-role SQL missing effect/receipt/event, wrong parent/hash/reviews, forged events, late request-review INSERT and request-review UPDATE/DELETE or linkage substitution denied, terminal edits denied; no consumption-review table/index/trigger; deferred final graph checked at commit and SET CONSTRAINTS. |
| tests/integration/phase2/test_b13_grant_concurrency.py | FIRST-SQL inventory/isolation and pre-snapshot W/A protection; same key single result, different payload conflict, two keys/one grant one winner; revoke/evaluate/consume both orders; review/Issue INSERT, REJECT/new target, authority/credential/source/consent writers both orders; starts T−1, held N/scope/target/grant/consent/deferred lock until T+1, fresh clock denies with zero effect; retry crossing expiry; exact ≤3 SQLSTATE attempts and no timeout/business retry; lock inspection proves reads/replay take no explicit locks. |
| tests/architecture/test_b13_grant_boundaries.py | Human/Agent same Application boundary, no ORM/domain leakage, literal R3 hash and concrete FKs; existing grant→decision→request→review FK path, no duplicate review-membership persistence; no standalone consume/status update route, read-side writes, semantic JSON owner, queue/external effect; missing B14 branch cannot report acceptance. |

After implementation, run these files plus existing test_approval.py,
test_pr2_15_decision.py/test_pr2_15_decision_schema.py, B04/B05 review/freeze and
accepted B08–B12/authority-loss regressions. Run ruff check/format, pyright,
git diff --check, and unit/architecture tests. The owner's loop owns the full
suite for this task. Unavailable future tests are not passing/skipped acceptance.

### 12.5 Not in this slice

| Deferred behavior | Owning dependency |
| --- | --- |
| Concrete READY/package lifecycle, result/event FKs and complete DTO integration | B14, with compatible W/consent lock extension and bidirectional final-graph guards |
| Manuscript preparation Decision and approval extension | Accepted B12 implementation on B09/B11 |
| Package creation, direct-author consent/withdrawal, manifest closure | Publication/consent contracts beyond attribution S1; exact consent inventory must precede freeze |
| New Issue disposition/reconsideration semantics or automatic impact propagation | B08/B10 and separately approved extensions; no implied manuscript disposition |
| Scheduler, sweeper, bulk evaluator, notification, generic policy engine | Separate authorization; expiry already denies without them |
| Venue send, SubmissionVersion/SubmissionRecord, ExternalEffect | Later authorized slice; no external submission here |

## 13. Open questions for the owner — override register

| Owner may override | Decision adopted in this draft |
| --- | --- |
| Evaluator and expiry persistence? | Explicit one-grant OWNER maintenance; immediate effective denial, no hidden commit in a failed consuming command (§3.1 R2 clarification). |
| Terminal precedence and projection compatibility? | Expiry then verified staleness then explicit revoke; consumed/revoked/expired diagnostic GRANT_INVALID, stale GRANT_STALE; retain exact old history. |
| Lock granularity? | Existing SHARE mechanism plus coarse Publication SHARE ROW EXCLUSIVE before snapshot; retain SERIALIZABLE effect, READ COMMITTED maintenance, lock-free RR reads. Narrowing requires equivalent demonstrated exclusion. |
| Can B13 enable freeze before consent/B14 binding? | No. Missing concrete FKs, final guards or consent inventory/order block that branch; no stand-ins or later work inside this slice. |

These are adopted draft refinements awaiting disposition. No unanswered question
permits weakening invariants or implementing this document.

## 14. Documentation verification note

Only this proposal is authored. B13 tests above are planned, not present evidence.
Verification on 2026-10-16 used the installed shared environment. Common prefix
for every uv command below (no dependency sync or repository environment changes):

```sh
UV_CACHE_DIR=/tmp/researchbase-b13-uv-cache UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv
```

| Exact command after common prefix | Observed result |
| --- | --- |
| `uv run --no-sync ruff check .` | PASS: All checks passed! |
| `uv run --no-sync ruff format --check .` | PASS: 570 files already formatted |
| `uv run --no-sync pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject` | PASS: 0 errors, 0 warnings, 0 informations |
| `PYTHONPATH=src uv run --no-sync pytest tests/unit tests/architecture` | 2,343 passed, 4 failed, 12 errors, 7 warnings in 54.43s; not PASS |
| `PYTHONPATH=src uv run --no-sync pytest tests/unit/test_approval.py tests/unit/phase2/test_pr2_15_decision.py tests/architecture/test_basic_approval.py` | 55 passed, 1 warning in 0.86s |
| `PYTHONPATH=src DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run --no-sync pytest tests/integration/phase2/test_approval.py tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b05_manuscript_review.py -x --tb=short` | 1 setup error in 0.49s; stopped before PostgreSQL assertions; remaining cases not run |

The four broad-run failures are HG1 runner socket binds denied by the sandbox
(Operation not permitted). Twelve PR2-19 architecture setup errors require an
explicit RB_TEST_ADMIN_URL. The focused PostgreSQL attempt supplied that URL and
then failed on sandbox-denied localhost connections. No PostgreSQL server version
or database assertion completed; none is reported PASS. No whole-suite run was
performed; the owner's loop owns that evidence.

`git diff --check` passed with no output. Because this proposal is untracked,
`git diff --no-index --check /dev/null docs/proposals/B13_Grant_Consumption_Contract_DRAFT.md`
also checks the actual new file. A local Python/AST check resolved all 31 relative
links, matched all 17 HTTP/CLI pairs against the source maps and verified the
required status and 14 numbered sections. Only this document is changed; no
implementation, acceptance or Phase gate claim follows.


### Director review 1 revision verification — 2026-10-16

Documentation only: option (a) removes duplicate review membership persistence;
B14 adopts the same existing-relation read/write/guard/test plan. No implementation,
migration, dependency, branch or commit is created. Earlier evidence above belongs
to the original draft; the exact commands and results for this revision follow.
Commands ran from the repository root using its installed `.venv`, without sync.

| Exact command | Observed result |
| --- | --- |
| `UV_CACHE_DIR=/tmp/researchbase-b13-review-uv-cache uv run --no-sync ruff check .` | PASS: All checks passed! |
| `UV_CACHE_DIR=/tmp/researchbase-b13-review-uv-cache uv run --no-sync ruff format --check .` | PASS: 570 files already formatted. |
| `UV_CACHE_DIR=/tmp/researchbase-b13-review-uv-cache uv run --no-sync pyright` | PASS: 0 errors, 0 warnings, 0 informations. |
| `PYTHONPATH=src RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres UV_CACHE_DIR=/tmp/researchbase-b13-review-uv-cache uv run --no-sync pytest tests/unit tests/architecture --tb=short > /tmp/b13-review-unit-architecture.log 2>&1` | 2,343 passed, 4 failed, 12 errors, 7 warnings in 41.62s; exit 1, not PASS. |
| `PYTHONPATH=src DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres UV_CACHE_DIR=/tmp/researchbase-b13-review-uv-cache uv run --no-sync pytest tests/integration/phase2/test_approval.py tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_12_publication_draft.py tests/integration/phase2/test_pr2_12_migration.py tests/integration/phase2/test_b05_review_basis.py -x --tb=short > /tmp/b13-review-postgres.log 2>&1` | 1 setup error in 0.43s; exit 1, no database assertions completed; remaining cases not run. |
| `git diff --check` | PASS: no whitespace errors. |

The four failures are HG1 runner Unix socket tests denied by the sandbox
(`Operation not permitted`). The twelve PR2-19 architecture setup errors and the
focused PostgreSQL setup error are denied localhost PostgreSQL connections with
the same error. PostgreSQL version and assertions could not be verified here;
these are not passing database evidence. Warnings are the existing Alembic
`path_separator` deprecation. The whole test suite was not run; the owner's loop
owns that evidence. A local `python3` pathlib/regex check verified 60 relative
links across both drafts, explicit option (a), and absence of the removed relation
DDL, trigger and child-write instructions. Planned B13/B14 tests remain planned.


## Implementation substitutions — owner-authorized first slice, 2026-10-17

- Follow the guide's isolation split: SERIALIZABLE for consumption; READ COMMITTED
  for maintenance; lock-free REPEATABLE READ, READ ONLY for reads/replay. The task
  summary's READ COMMITTED wording applies to maintenance, not consumption.
- The reconciled predecessor is `0058_b12_prepare_submission`; B13 adds only
  `0059_b13_grant_consumption`. Existing migrations remain byte-for-byte unchanged.
- Scientific release belongs to the existing `ScientificConclusionService` in
  `application/scientific_conclusion.py`; its command delegates to private shared
  approval orchestration. ApprovalService exposes no generic consume command.
- No accepted package table or B14 lifecycle binding exists. The receipt schema
  therefore admits only the concrete scientific conclusion result. Publication
  references are typed RESTRICT FKs but disabled by the result CHECK; the reserved
  package field is constrained NULL and cannot store a soft reference. Its FK,
  index, READY/package result tuples and result guards await B14. No package,
  consent, publication lifecycle or transport implementation is added here.
- Current-head expectations/inventories advance to 0059. B12's schema roundtrip is
  pinned to its own 0058 revision before its catalog snapshot so a later additive
  table does not alter the meaning of the historical B12 test.

- Existing SQL trigger bindings are retained for their obvious named equivalents:
  the guide's `b13_grant_transition_guard` is the forward replacement of
  `pr216_grant_guard`; its event guard uses the existing `pr216_event_insert`
  entrypoint, dispatching grant events to `b13_validate_event` while preserving
  request-event validation. Receipt/completeness/immutable triggers and the new
  CHECK/UNIQUE/FK/index names use the guide's B13 names. These substitutions retain
  existing authority and approval writers without duplicating lifecycle guards.
