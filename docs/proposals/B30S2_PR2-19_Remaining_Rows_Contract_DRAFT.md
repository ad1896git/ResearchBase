# Remaining PR2-19 Rows, Second Slice (B30-S2) Contract — DRAFT

**Status: APPROVED by owner 2026-10-19 — first slice authorized for implementation**

**Acceptance: BLOCKED — implementation authorization above is not slice acceptance.**
See [director decisions](B30S2_Architecture_Questions_2026-10-19.md).

Director disposition 2026-10-19: AQ-S2-01 authorizes the separate B13 production
hardening fix in forward migration 0069 (no schema addition), overriding this
slice's test-only restriction solely for that fix. AQ-S2-02 marks scheduled-role
expiry **BLOCKED: no owning Application command**; keep credential/grant expiry
coverage and do not fake scheduled expiry with SQL. Other scope restrictions
remain binding. See the linked decision record and current verification evidence.

## Start here (for the implementer)

This is a test-only continuation of [B30](B30_PR2-19_Remaining_Rows_Contract_DRAFT.md),
not approval to implement it. B30 S1 stays intact. B14a/B14r/B14 now supply real
Publication entry, READY permission and READY consumption; B15/B16 supply local
package preparation and direct author consent; B17 supplies package freeze.
Their presence makes the four bounded suffixes in §2 runnable, not passed.
The full PR2-19 gate remains BLOCKED.

After separate owner authorization:

1. Reconcile subcases in `tests/integration/phase2/test_pr2_19_dependencies.py`;
   preserve its historical inventory and fail-closed gate. Split F1 downstream
   projection from automatic propagation, which remains BLOCKED.
2. Reuse `pr2_19_support.py`, `b30_observations.py`, `b17_fixtures.py` and
   `b25_support.py`. Extend the existing G7 package test; do not build a second
   scenario/report framework or repeat owner suites as the only E2E evidence.
3. Compose the G7 READY → PREPARED → consent → FROZEN path; then F1 downstream
   invalidity, F5 READY blockers and F9 READY/package consumption. Every fixture
   fact comes through its owning Application command, with separate commits.
4. Observe the actual lock protocols in §12.2, exact hashes/CAS bytes, fresh
   readback and command-level deltas. Keep independent reviewers/approvers.
5. Run focused checks and record actual counts/blockers. Stop at these suffixes;
   the loop supplies the full-suite evidence.

Review rules: deterministic facts outrank permission; citation is not support;
PREPARED/FROZEN is local preparation, never venue sending. No SQL-forged READY,
consent or grant. No production code, migration, dependency, fault hook or other
document changes are part of this slice. Reads and completed replay use one
read-only REPEATABLE READ snapshot per invocation, without explicit table,
advisory or row locks. A passing suffix cannot pass its original full row.

## 1. Purpose, authority and inspected baseline

Read `AGENTS.md`, architecture 01 → 02 → 03 → 08 → 05, Harness 09, then the
[PR2-19 catalog](PR2-19_E2E_Failure_Injection_Plan_DRAFT.md) and B30. This draft
uses the Start here / §§1–13 structure of the approved PR2-17 and PR2-18 drafts;
§14 records documentation verification.

| Authority under `docs/architecture/` | Binding requirement |
| --- | --- |
| `01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md`, §§3, 7–9; `02_Final_Architecture_Correction_Addendum_v1.0.md`; `03_Global_Schema_and_Contract_Registry_v1.0.md` | One fact owner, immutable formal history, concrete frozen references and shared Application boundary. |
| `08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md`; `05_Phase2_Development_Specification_v1.1_Harness_Integrated.md`, §§42–43/PR2-19 | Preserve Phase 1 contracts; retain golden/failure obligations. |
| `12_Phase2_Architecture_and_Contract_Correction_v1.0.md`; `15_Phase2_Hash_Payload_Contract_R2_v1.0.md` | Local preparation, literal canonical material and exact closure. |
| `17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md`, §§1–3; `18_Phase2_Design_R3_Targeted_Remediation_v1.0.md`, §5; `19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md`, §§1, 4–5 | Finite purpose/target/command tuples, current direct consent, atomic effect/receipt, post-wait DB-clock checks and historical completed replay. |

Implementation evidence is in `src/researchbase/application/{publication,approval,
prepared_submission}.py`, corresponding persistence repositories, migrations
0060–0064/0067, and the tests in §12.4. Older proposal blockers are historical.
In particular, `test_pr2_19_package_freeze.py` already exercises G7 via
`pr2_19_support.prepared_package_trace`; it needs extension, not replacement.
Owner availability flags in `SUBCASES` are informational and are not acceptance.

## 2. Scope, dependency boundaries and non-goals

These are the **only newly runnable suffixes selected for S2**. Preserve all
original row IDs and S1 evidence. Test artifacts below live under
`tests/integration/phase2/`.

| Original row / bounded suffix | Runnable commands and fixture construction | Required result; remaining boundary |
| --- | --- | --- |
| G7 package/READY | `b17_fixtures.build(b05_env)` uses B14 `issued`, B14a entry, independent manuscript review, B11 READY Decision, B14r approval, `PublicationService.transition_publication_ready`, distinct B12 PREPARE Decision/approval, authorship commands, `prepare_submission`, direct `record_author_consent`; `prepared_package_trace` freezes and reads. | Exact READY event/receipt and package/consent/manifest closure after restart. Existing B17 G7 evidence is retained. Novelty remains a separate branch, not a gate or package attachment. G7 as a whole remains BLOCKED below. |
| F1 READY/package downstream | Before `build`, attach a real literature conclusion using `b25_support.literature_conclusion(env, snapshot=False/True)`. Use separate graphs for each stage: READY grant pending; PREPARED package with unused freeze grant; completed frozen package. Append CORRECTED/RETRACTED source via `source_transition`. | Direct and Claim-snapshot support paths yield manuscript/package current STALE/INVALID and deny new consuming effects. Old READY/package receipts, exact material and CAS bytes survive. Automatic finding/impact propagation remains BLOCKED. |
| F5 READY consumption | B14 `issued(b05_env)` supplies a committed READY request/decision/grant but no READY effect. Add an independent OPEN/BLOCKING manuscript Issue through B05 `create`; invoke `transition_publication_ready`. | `APPROVAL_GATE_FAILED`, Publication remains INTERNAL_REVIEW, no new lifecycle/consumption/grant-event writes and no grant terminalization. Use an unblocked sibling control. No manuscript revision/disposition completion is implied. |
| F9 READY/package consumption | Use B14 `issued` for READY and B17 `build`/`next_package` for package freeze. Exercise both concrete commands, each with its own grant/command key and saved exact target. | One effect/receipt per grant; exact completed replay, wrong tuples, expiry/authority/blocker/consent denial, observed races and rollback. Grant creation or a generic receipt DTO alone is insufficient. |

Keep these requirements **BLOCKED**, with these blockers (not skips/xfails):

| Row/subcase retained from B30 | Blocker |
| --- | --- |
| G2 positive strategy admission | No candidate-binding/authority/replay admission owner. Ordinary DRAFT creation is not promotion. |
| G4 positive discussion admission | `DiscussionService.request_promotion` denies; no successful admission contract. |
| G6 manuscript concern cycle / F6 seventh action type | `RevisionActionService._supported` excludes MANUSCRIPT_CHANGE. Six implemented action types and seven result slots do not supply this command. |
| G7 stronger novelty outcomes | Exact screening/comparison basis absent; existing canonical assessment admission is INCONCLUSIVE only. |
| G7 lock-free novelty completed command replay | B30 §13 owner decision pending; exact GET and replay equality do not prove lock-free command replay. |
| F1 automatic finding/impact propagation | No automatic propagation owner; deterministic read projections and explicitly commanded assessments are available. |
| F5c manuscript-purpose reconsideration | B10 reconsideration is release-only. |
| F9 scheduled role expiry | BLOCKED: no owning Application command to schedule role expiry (AQ-S2-02). Credential/grant expiry coverage remains. |

F5b consent-dependent package checks and F7 effect rollback are now available
owner regressions; S2 uses them only as F9/G7 controls, without adding full-row
acceptance claims. The reserved `test_pr2_19_revision.py` and
`test_pr2_19_grant_consumption.py` remain absent.

One additional historical blocker is obsolete: current `AuthorshipService._get`
calls `authorship_repository.prepare_read` (REPEATABLE READ, READ ONLY), uses
plain reads and checks entitlement again. It no longer locks as B30's old text
and `SUBCASES` claim. Reconcile that availability separately; standalone authorship
acceptance is not an extra S2 deliverable. The novelty replay blocker is unchanged.

## 3. Invariants and conservative judgments

READY consumes only READY_FOR_SUBMISSION permission for the exact frozen
ManuscriptVersion and returns its Publication. Freeze consumes only
PREPARE_SUBMISSION permission for that manuscript and returns its same-publication
package. Both check the sealed review set and current deterministic facts.
Authorship attribution supplies no approval authority. Consent is authenticated
direct HUMAN authorship, with one current GRANTED head per author at freeze.

Source correction/retraction changes current validity, never historical hashes.
SUPERSEDED alone does not mean INVALID. Later withdrawal appends consent history
and derives frozen-package STALE; it does not replace frozen consent items or
reactivate a consumed grant. Independent fixture actors and retained adverse
reviews remain required. No automatic findings are inferred from projections.

## 4. Proposed commands, DTOs and historical readback

No new product command, DTO, route or CLI command. Call current closed Application
dataclasses (§11.3). Fresh instances of PublicationService,
PreparedSubmissionService and ApprovalService must read committed results after
success, denial and injected rollback; count queries supplement formal readers.
Compare immutable fields separately from current diagnostics and later events.
Preserve exact result UUIDs, target hashes and typed consent references.

## 5. Schema and literal hash proposal — no migration

**DO NOT ADD SCHEMA.** DDL delta is empty. §12.1 describes existing constraints
to observe, not executable migration work. Reuse `sha256-cjson-v1` and current
manifest/package/consent and grant-consumption material. Expected canonical JSON,
digests and retained CAS bytes must be independently constructed, not calculated
by the production builder used by the result under test. No new semantic JSON
owner, event type or canonical test receipt.

## 6. Error contract — existing categories only

Use exact owner branches and §11.2. No new error code or transport change.
These commands are Application-only; mappings describe existing common adapter
behavior, not new HTTP/CLI exposure. Constraint probes assert SQLSTATE/named
constraint separately from Application errors. Missing requested roots and broken
dependencies of resolved saved roots are different cases. Authorize before
protected disclosure; sanitize unexpected errors.

## 7. Transactions, concurrency and failure recovery

One command, one transaction; never wrap the scenario in a shared UoW. Snapshot
writes use their existing first-SHARE READ COMMITTED protocol. READY and freeze
use their separately implemented SERIALIZABLE consuming protocols (§12.2), not
a newly invented READ COMMITTED substitute. Reads take no exclusion locks.

Use independent connections/PIDs, barriers and `pg_locks`/`pg_blocking_pids`.
Observe blocking and release; elapsed sleep is not evidence. Check advancing
`clock_timestamp()` after blocking/deferred checks, including credential and
grant expiry. Scheduled role expiry remains BLOCKED under AQ-S2-02. Existing
retry classification alone permits up to three
total fresh-UoW attempts for retryable serialization/deadlock conflicts. Business
denial, timeout and uncertain commit do not become generic retries. Recover a
lost response with the same exact key and current read entitlement.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

§12.4 specifies the files/cases. Use disposable real PostgreSQL 18.x at current
migration head, existing deterministic fixtures and CAS. Never fabricate frozen
state with SQL. Test-only repository wrappers may perform the real operation then
raise; no production fault hook. Prove rollback by fresh reads, row versions,
events, receipts and counts, retaining committed predecessors.

## 9. Acceptance criteria and evidence boundary

Acceptance is bounded to §2's four suffixes after authorization and execution of
their tests, with old runnable evidence preserved and no open P0/P1. Full PR2-19
and Phase 2 remain BLOCKED. Preserve `HISTORICAL_BLOCKED_ROWS`; reconcile current
`SUBCASES` by splitting F1's runnable projection from missing automation and
removing obsolete B14 absence from F5. Keep `availability_is_acceptance=False`
and `require_full_gate` fail closed. Never promote a missing fixture, setup error
or skipped case to PASS. The loop runs the full suite.

## 10. Glossary

| Term | Meaning |
| --- | --- |
| Suffix / runnable | Remaining steps of an original G/F row / owning commands and fixture construction exist, without a PASS claim. |
| READY | Publication lifecycle effect, distinct from frozen manuscript or approval issuance. |
| PREPARED / FROZEN | Local package draft / sealed exact manuscript, authorship, manifest and consent closure. Neither sends externally. |
| Current validity | Derived diagnostic separate from immutable saved material and lifecycle status. |
| Consumption / completed replay | Atomic protected effect plus receipt and grant terminalization / entitled historical read of that effect. |
| Observation | Existing bounded operational test record, never scientific persistence. |

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

Adopt only §2. Extend existing observations/fixtures, not production mechanisms.
G7 package success does not establish stronger novelty or standalone authorship
acceptance. Test completed replay and exact GET independently. If a selected
owner behavior fails, record the failure and return it to that owner; do not fix
production code or relax the oracle in a test-only slice.

### 11.2 Pinned error mappings

Values match `src/researchbase/api/errors.py:_STATUS` and
`src/researchbase/cli/errors.py:CLI_EXIT_CODES`.

| Code | HTTP | CLI | Selected oracle |
| --- | ---: | ---: | --- |
| VALIDATION_ERROR | 422 | 2 | Closed DTO types, malformed hash/review IDs. |
| AUTHENTICATION_REQUIRED | 401 | 3 | Missing authenticated boundary. |
| FORBIDDEN / CONFLICT_OF_INTEREST / SUBJECT_BINDING_UNPROVEN | 403 | 3 | Exact applicable credential/role, independence or subject branch. |
| NOT_FOUND | 404 | 3 | Entitled absent requested grant/root. |
| SOURCE_VERSION_NOT_FOUND | 404 | 3 | Source owner absent requested version. |
| APPROVAL_GATE_FAILED | 409 | 4 | New OPEN/BLOCKING Issue; missing current direct consent; missing saved READY receipt. |
| APPROVAL_TARGET_STALE | 409 | 4 | First-use stale/invalid scientific target. |
| APPROVAL_PURPOSE_TARGET_COMMAND_INVALID | 409 | 4 | Wrong finite purpose/command/result tuple. |
| DECISION_BASIS_INVALID | 409 | 4 | Incomplete checked review set on first use. |
| GRANT_INVALID | 409 | 4 | Expired/revoked/consumed first-use grant, except explicit STALE branch. |
| GRANT_STALE | 409 | 4 | STALE grant or unavailable issuing credential/authority. |
| INVALID_STATE_TRANSITION / VERSION_NOT_FROZEN / IMMUTABLE_RECORD | 409 | 4 | Exact owner lifecycle/freeze/immutability branch. |
| CONCURRENT_MODIFICATION | 409 | 4 | Candidate manifest mismatch, obsolete consent head or exhausted classified conflict. |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Same key, changed completed command material. |
| FROZEN_REFERENCE_REQUIRED / PROVENANCE_CLOSURE_VIOLATION / REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Exact admission/closure/FK branch; altered retained bytes use PROVENANCE_CLOSURE_VIOLATION. |
| INTERNAL_ERROR (fallback, not ErrorCode) | 500 | 1 | Sanitized unexpected exception. |

Do not accept any code from a grouped cell: each test pins one branch. For F1,
first-use READY and package freeze reject current scientific invalidity with
APPROVAL_TARGET_STALE; a previously persisted STALE grant instead takes
GRANT_STALE. Completed exact replay remains historical. Pre-freeze missing
consent uses APPROVAL_GATE_FAILED; withdrawal may already have terminalized the
unused grant, in which case GRANT_STALE takes precedence. Test both separately.

### 11.3 DTO fields, Python types, limits and enums

All identities below are strict `uuid.UUID`, not strings; optional fields use
`| None`. Dataclasses remain frozen/closed. Principals are verified separately;
callers never supply actor identity or timestamps in these commands.

| Existing DTO in `application/` | Exact fields |
| --- | --- |
| `publication.TransitionPublicationReadyCommand` | `command_key, project_id, grant_id, result_id: UUID`; `checked_review_ids: tuple[UUID, ...]`. `result_id` is Publication. |
| `publication.GetPublicationReadyTransitionQuery` | `project_id, consumption_id: UUID`. |
| `prepared_submission.PrepareSubmissionCommand` | `id, project_id, publication_id, manuscript_version_id, authorship_snapshot_id: UUID`. |
| `prepared_submission.RecordAuthorConsentCommand` | `id, project_id, prepared_submission_version_id, evidence_artifact_version_id: UUID`; `consent_state: Literal['GRANTED','WITHDRAWN']`; `consent_scope: Literal['PREPARED_PACKAGE']`; `prior_consent_id: UUID | None`. |
| `prepared_submission.FreezePreparedSubmissionCommand` | `command_key, project_id, grant_id, result_id: UUID`; `expected_package_manifest_hash: str`; `checked_review_ids: tuple[UUID, ...]`. `result_id` is PreparedSubmissionVersion. |
| `prepared_submission.GetPreparedSubmissionQuery` | `project_id, prepared_submission_version_id: UUID`. |

Review sets contain 1–100 distinct UUIDs, sorted by UUID text. Expected digest is
exactly 64 lowercase hex characters. Manifest categories are FIGURE, TABLE,
CITATION, CLAIM, CONCLUSION, AUTHOR_CONSENT; ordinals are strict int 0–9999,
gap-free within category. At most 10,000 occurrences including the reserved
1–100 author consent slots; occurrences are not deduplicated. Package version
numbers are positive int, bounded by 2,147,483,647 in preparation.

Readback types remain `PreparedSubmissionReadback`, `ReadyTransitionReadback`
and `ConsumptionReadback` in the named Application files: UUID identities;
timezone-aware UTC `datetime` timestamps; hash strings (package hashes and
`frozen_at` nullable until sealed); tuple children; integer row/version numbers.
Package status enum is PREPARED/FROZEN/SUPERSEDED/WITHDRAWN; current validity is
NOT_FROZEN/VALID/STALE/INVALID. Reasons are NOT_FROZEN, CONSENT_MISSING,
CONSENT_WITHDRAWN, UPSTREAM_INVALID, UPSTREAM_STALE, PACKAGE_WITHDRAWN,
DEPENDENCY_UNAVAILABLE. Receipt command literals are TRANSITION_PUBLICATION_READY
and FREEZE_PREPARED_SUBMISSION for this slice; DTO version remains 1. Compare
typed result and concrete result FK, not just the generic receipt ID.

Reuse unchanged report records in `pr2_19_support.py`: `ScenarioSpec` has string
scenario/authority/fixture/fault/outcome fields, tuple[str, ...] prerequisite and
command fields, tuple[UUID, ...] actor IDs and optional string error code.
`ScenarioObservation` has `scenario_id, command_identity: str`, `step_index: int`,
`result_ids: tuple[UUID, ...]`, `error_code: str | None`, and tuple fields
`state_deltas`, `verified_hashes`, `backend_pids: tuple[int, ...]`, `lock_events`,
`evidence_paths: tuple[Path, ...]`. Elements remain `StateDelta(table_name: str,
before_count: int, after_count: int)`, `VerifiedHash(record_id: UUID,
hash_field: str, expected: str, actual: str)` and `LockEvent(backend_pid: int,
event: str, at: datetime, blocker_pids: tuple[int, ...])`.
Keep current finite scenario/fault/command allowlists; outcomes remain
PASS/DENIED/BLOCKED/ERROR and events TX_STARTED/WAIT_OBSERVED/LOCK_ACQUIRED/
AUTH_CHECKED/COMMITTED/ROLLED_BACK. Add only the concrete labels needed by §12.4.

Report limits stay unchanged: 16 actor IDs; 32 prerequisite/command entries;
128 entries in other tuples; 512 characters for authority/prerequisite text,
128 for other text except 1,000 for error codes. Counts/step indices are
nonnegative strict int, PIDs positive, hashes lowercase SHA-256, lock timestamps
aware UTC, and evidence paths confined to `REPORT_ROOT`.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

Empty DDL change set. Observe these existing types/constraints; do not execute
this inventory as SQL or modify frozen migrations. All paths are under
`migrations/versions/`.

| Owner migration / existing shape | Named guards to observe |
| --- | --- |
| `0060_b15_package_preparation.py`: package UUID parent/manuscript/authorship FKs, INTEGER version/row_version, VARCHAR(16) status, nullable CHAR(64) hashes/TIMESTAMPTZ frozen_at, VARCHAR(32) hash_scheme | `uq_b15_package_parent`, `uq_b15_package_number`, `fk_b15_manuscript_parent`, `fk_b15_snapshot_parent`, `ck_b15_package_status`, `ck_b15_package_hash_state`, `ck_b15_package_row_version` (last three extended by 0067). |
| 0060/`0061_b16_consent_withdrawal.py`: consent UUID package/actor/evidence/prior FKs, VARCHAR(16) state, VARCHAR(24) scope, CHAR(64) hash, TIMESTAMPTZ captured_at | `uq_b15_consent_package`, `ck_b15_consent_actor`, `ck_b15_consent_hash`; existing B16 single-root/successor chain guards remain authoritative. |
| `0064_b14_publication_ready.py`: lifecycle UUID basis_decision_id/basis_grant_consumption_id; consumption UUID result_publication_id | `fk_b14_ready_decision`, deferred `fk_b14_ready_consumption`, `ck_b14a_event_tuple`, `ck_b13_result_tuple`; deferred `b14_complete_publication`, `b14_complete_ready_event`, `b14_complete_ready_consumption`. |
| `0067_b17_prepared_package_freeze.py`: consumption UUID result_prepared_submission_version_id; manifest UUID author_consent_id; sealed CHAR(64) hashes and TIMESTAMPTZ frozen_at | Deferred `fk_b17_result_package`, extended `ck_b13_result_tuple`, `ck_b15_event_transition`; deferred `b17_complete_package`, `b17_complete_item`, `b17_complete_event`, `b17_complete_consumption`. |

Concrete FKs remain RESTRICT; no scientific cascade or polymorphic soft reference.
Deferred graph guards follow the existing 0042 Decision pattern. Force
`SET CONSTRAINTS ALL IMMEDIATE` before final time-sensitive authorization; test
failure there rolls back effect, receipt and grant event together. No new trigger.

### 12.2 Exact lock order and transactions

Source constants mean their **exact ordered SQL inventories**, not sets to
reorder. Expand them verbatim in test assertions. Paths below are under
`src/researchbase/persistence/`. For READ COMMITTED snapshot writes,
`LOCK TABLE <inventory> IN SHARE MODE` is the FIRST transactional statement,
before SET LOCAL, authorization, advisory or row locks, as in
`decision_repository.py` and `novelty_repository.py`. Connection configuration
in driver autocommit is outside that transaction. Timeouts below are
`lock_timeout='10s'`, then `statement_timeout='30s'`.

| Exercised command | Exact owner order |
| --- | --- |
| B14a `transition_publication_internal_review` | READ COMMITTED; `publication_repository.B14A_SHARE_SQL` first; publications SHARE ROW EXCLUSIVE; approval_decisions,approval_request_reviews,approval_requests SHARE; timeouts; advisory `b14a:entry:<id>`; manuscript FOR UPDATE; Publication FOR UPDATE; authorize/replay/exact frozen target; transition/event; force constraints/final authority; commit. |
| B11 READY / B12 PREPARE Decision | READ COMMITTED; `decision_repository.B11_SHARE_SQL` first; timeouts; advisory `b11:decision:<id>` / `b12:decision:<id>` respectively; manuscript FOR UPDATE; project FOR SHARE; Publication FOR SHARE via `internal_review.lock_publication`; authority/replay, exact review/target closure; Decision/basis inserts; force constraints/final authority; commit. |
| Approval request / decision | READ COMMITTED; `approval_repository.B09_SNAPSHOT_TABLES` SHARE first; timeouts; advisory `pr216:uuid:<id>`; resolve tuple; `pr216:scope:<project>:<purpose>` advisory; exact manuscript FOR UPDATE; Publication FOR SHARE; decision's saved request FOR UPDATE; authorize/replay/gates; affected grants UUID-sorted FOR UPDATE; inserts; force constraints/final authority; commit. |
| `prepare_submission` | READ COMMITTED; `prepared_submission_repository.B15_SHARE_SQL` first; timeouts; advisory `b15:prepare:<id>`; manuscript FOR UPDATE; Publication FOR UPDATE; authorization/replay/context and exact occurrence projection; parent/items/event insert; force constraints/final stage authorization; commit. |
| `record_author_consent` GRANTED or WITHDRAWN | READ COMMITTED; `B16_SHARE_SQL` first; publications SHARE ROW EXCLUSIVE; approval_decisions,approval_request_reviews,approval_requests SHARE; timeouts; advisory `b15:consent:<id>`; permission lookup; `pr216:scope:<project>:PREPARE_SUBMISSION` advisory; manuscript FOR UPDATE; Publication FOR UPDATE; package FOR UPDATE; caller's consent chain ordered id FOR UPDATE; recheck head/permission/evidence; on withdrawal related ACTIVE grants UUID-sorted FOR UPDATE and reread scope; append consent and terminalize applicable unused grants; force constraints/final authority; commit. |
| `transition_publication_ready` first use | SERIALIZABLE via `configure_grant_transaction(consuming=True)`; `approval_repository.B13_SHARE_SQL` first; publications SHARE ROW EXCLUSIVE; `B13_APPROVAL_SQL` SHARE; timeouts; advisory `b13:consume:<command_key>`; receipt/chain lookup; `pr216:scope:<project>:READY_FOR_SUBMISSION` advisory; manuscript FOR UPDATE; Publication FOR UPDATE; ApprovalRequest FOR SHARE; ApprovalGrant FOR UPDATE; reread/gate/fresh clock; Publication transition/lifecycle event + receipt + CONSUMED event/status; force constraints/final authority and issuer/expiry checks; commit. |
| `freeze_prepared_submission` first use | SERIALIZABLE; `prepared_submission_repository.B17_SHARE_SQL` first; publications SHARE ROW EXCLUSIVE; prepared_submission_versions SHARE ROW EXCLUSIVE; approval_decisions,approval_request_reviews,approval_requests SHARE; timeouts; advisory `b13:consume:<command_key>`; entitled receipt/package/grant lookup; `pr216:scope:<project>:PREPARE_SUBMISSION` advisory; manuscript FOR UPDATE; Publication FOR UPDATE; package FOR UPDATE; older FROZEN packages ordered id FOR UPDATE; each author's consent chain FOR UPDATE in sorted Actor-ID order; ApprovalRequest FOR SHARE; ApprovalGrant FOR UPDATE; reread context/heads/READY receipt/hash/gates/fresh clock; consent items + older supersession/events + seal/event + consumption + CONSUMED grant event/status; force constraints/final checks; commit. |
| Exact READY/package/history/preview/consent/receipt reads and completed replay | One read-only REPEATABLE READ UoW per call; current read entitlement, exact saved closure then derived diagnostics, final advancing-clock entitlement; no LOCK TABLE, advisory locks, FOR UPDATE/FOR SHARE, project-lock function or writes. First-use lookup may close a separate snapshot before entering the writer. A concurrent receipt discovered inside a writer exits it before returning through the historical reader. |

Setup commands retain B30 §12.2's owner protocols: B04 freeze first SHARE then
project/Publication/manuscript locks; B11/B12 Decisions use their actual
`decision_repository.py` orders above; B05 review reserves
`internal_review_records` ROW EXCLUSIVE before its snapshot locks. Do not impose
the snapshot-write order on that reservation. Source lineage setup uses its
existing Application boundary. Observe suffix commands separately from setup.

Use `b30_observations.sql_protocol`, `assert_first_share` (SERIALIZABLE explicitly
for consumers), and `assert_snapshot_read(..., snapshots=1)` on each selected
read/replay. Do not relax the novelty replay requirement; its owner decision
remains BLOCKED in §2. Authorship's historical blocker is reconciled there too.

### 12.3 Ordered build steps and module paths

1. Extend `tests/integration/phase2/pr2_19_support.py` with finite F1/F5/F9
   command labels and count tables for the concrete suffixes. Reuse G7's existing
   `B17_COMMANDS`/`prepared_package_trace`, all existing report dataclasses and
   `tests/integration/phase2/b30_observations.py`. No production edits.
2. Update `tests/integration/phase2/test_pr2_19_dependencies.py` as §9 specifies;
   preserve historical parsing/reserved modules. Extend
   `tests/unit/phase2/test_pr2_19_report_contract.py` for bounded labels and
   `tests/architecture/test_pr2_19_boundaries.py` for behavioral scope/lock-free
   reads. An availability flag never becomes a passing scenario.
3. Compose helpers in the existing support module using exported
   `tests/integration/phase2/b17_fixtures.py:build`, `next_package`,
   `withdraw_consent` and `b25_support.py:literature_conclusion/source_transition`.
   Place literature before manuscript freeze; create a separate fixture graph
   for each pre/post-consumption stage. Preserve current fixtures and actors.
4. Extend G7/lineage/governance tests, then add the bounded F9 file in §12.4.
   Attach SQL observers only around the invocation under test. Reconstruct fresh
   owning services after commits/faults. Do not use another test's PASS as oracle.
5. Run static, unit/architecture, selected PR2-19 and touched owner PostgreSQL
   suites. Record exact commands/counts/server version and blockers using existing
   report conventions under `artifacts/pr_evidence/PR2-19`. Stop; no full suite.

### 12.4 Test artifacts and required cases

Paths in the table are under `tests/integration/phase2/`; these are future
extensions, not claims of executed S2 tests.

| File | Required cases |
| --- | --- |
| `test_pr2_19_package_freeze.py` (extend) | G7: retain current success/denial; observe entire separately committed READY/preparation/consent/freeze trace, distinct purpose grants and typed receipts; independently expected hashes and exact manifest occurrence/consent IDs; fresh READY receipt, package/history/preview and completed replay each lock-free; withdrawal leaves frozen seal/items unchanged and current STALE; zero venue-send/SubmissionVersion/ExternalEffect creation. |
| `test_pr2_19_lineage.py` (extend) | F1: 2 support paths × 2 source successor kinds × 3 stages (unused READY grant, PREPARED with unused freeze grant, completed frozen package). Use existing B25 placement before `build`. Fresh manuscript/audit/READY diagnostics and package read where present; CORRECTED→STALE, RETRACTED→INVALID; new READY/freeze denied with exact owner code, zero new effect; completed receipts replay unchanged. Retain historical source/evidence/snapshot/manuscript/package hashes and CAS bytes; unaffected graph control. No automatic finding/impact creation assertion except zero unsolicited writes. |
| `test_pr2_19_governance.py` (extend) | F5: new OPEN/BLOCKING Issue after READY grant issuance and before first consumption; exact denial and unchanged INTERNAL_REVIEW/ACTIVE grant, saved request/decision/reviews retained; unblocked control succeeds. Repeat blocker across an observed required-lock wait. An adverse recommendation alone is not a blocking Issue. |
| `test_pr2_19_grant_consumption_publication.py` (new) | F9: parameterize READY/freeze concrete consumers. Missing/wrong-purpose/project/target grant; expired, revoked, STALE and already consumed new-key use; missing/changed review set; caller/issuer credential and scheduled role expiry across observed wait; blocker after issuance; package missing/withdrawn consent and changed manifest. Same key exact replay after restart/lost response/write-role loss with read role retained; changed key material conflicts; lost read entitlement denies. Same-key concurrent callers produce one receipt; two keys/one grant produce one winner; freeze/withdrawal both serial orders. Fault after each effect/item/event/receipt/terminalization write and deferred check rolls back this command only; fresh readers prove predecessor facts intact. |

For frozen withdrawal, freeze-first yields saved exact material plus derived
STALE; withdrawal-first denies freeze (or requires a valid regrant/new usable
grant as the owner contracts). Reuse B14/B17 owner race orchestration rather than
adding timing sleeps. Retain S1's internal-release F9 tests.

Focused implementation verification (not authorization and not present results):

```sh
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest tests/unit tests/architecture
uv run pytest tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_package_freeze.py tests/integration/phase2/test_pr2_19_lineage.py tests/integration/phase2/test_pr2_19_governance.py tests/integration/phase2/test_pr2_19_grant_consumption_release.py tests/integration/phase2/test_pr2_19_grant_consumption_publication.py
```

PostgreSQL runs require explicit `RB_TEST_ADMIN_URL` selecting a disposable local
PostgreSQL 18 admin. Also run the touched B14a/B14r/B14/B15/B16/B17 owner files,
especially READY replay/concurrency, package history/freeze/replay/concurrency,
consent/offboarding, and B25 lineage fixtures; list the actual selected files and
counts in implementation evidence. Do not claim untouched/unrun owners passed.

### 12.5 Not in this slice

All §2 BLOCKED subcases; new promotion/screening/impact mechanisms; production
read remediation; new approval/Decision purposes, RevisionAction shapes or
reconsideration scope; provider activation, external submission/send and Phase 3
runtime. No production code/schema/configuration changes, new dependencies,
edits to frozen architecture or changes to B30/S1 acceptance evidence.

## 13. Open questions for the owner — override register

Adopt the four bounded suffixes and retained blockers in §2. Owner may change
the ordering or selected test scope only by a recorded disposition reflected in
this body before implementation approval. No architecture exception is proposed.
The novelty replay decision remains with its owner; successful package readback
does not settle it or prove standalone authorship acceptance. This document grants
no implementation authorization and no full-gate acceptance.

## 14. Documentation verification note

Documentation-only runs on 2026-10-19 used the existing repository environment
read-only because this lane has no `.venv`. No dependencies were changed. In the
commands below, `V=/Users/fengwang/Documents/ResearchBaseProject/.venv/bin` is
only an abbreviation for that exact executable prefix (not a new environment).

| Exact command (expand `$V` as above) | Observed result |
| --- | --- |
| `$V/ruff check .` | Exit 0: all checks passed. |
| `$V/ruff format --check .` | Exit 0: 736 files already formatted. |
| `$V/pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject` | Exit 0: 0 errors, 0 warnings, 0 informations. |
| `PYTHONPATH=src $V/python -m pytest tests/unit tests/architecture --tb=short` | Exit 1: 5,618 passed, 5 failed, 14 errors, 9 warnings in 69.55s. Four Runner tests fail with Unix-socket PermissionError; static acceptance fails on dependency import diagnostics from its lane-local Pyright discovery. Fourteen PR2-19 architecture setups require unset RB_TEST_ADMIN_URL. Not PASS. |
| `PYTHONPATH=src $V/python -m pytest tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_package_freeze.py tests/integration/phase2/test_pr2_19_lineage.py tests/integration/phase2/test_pr2_19_governance.py tests/integration/phase2/test_pr2_19_grant_consumption_release.py tests/integration/phase2/test_b14_publication_ready.py tests/integration/phase2/test_b17_package_history.py --tb=short` | Exit 1: 3 passed, 96 setup errors in 1.15s. Only dependency inventory tests passed; PostgreSQL cases did not execute because RB_TEST_ADMIN_URL is unset. |
| `PYTHONPATH=src $V/python -m pytest tests/integration/phase2/test_b14a_publication_entry.py tests/integration/phase2/test_b14r_ready_approval.py tests/integration/phase2/test_b15_package_preparation.py tests/integration/phase2/test_b16_consent.py tests/integration/phase2/test_b17_package_freeze.py --tb=short` | Exit 1: 103 setup errors in 1.08s, same missing explicit disposable admin selector. No PostgreSQL assertions executed. |
| `PYTHONPATH=src $V/python -m pytest tests/unit/phase2/test_pr2_19_report_contract.py tests/integration/phase2/test_pr2_19_dependencies.py` | Exit 0: 86 passed in 0.34s. |
| `git diff --check` and `git diff --no-index --check /dev/null docs/proposals/B30S2_PR2-19_Remaining_Rows_Contract_DRAFT.md` | Exit 0, including the untracked draft's whitespace. |

A read-only Python check confirmed the required status, numbered sections 1–14,
no trailing whitespace and five literal full Python paths (four existing, one
explicitly planned test file). Source constants and named constraints were
checked against the owning repositories/migrations while drafting.

The three longer runs redirected stdout/stderr to `/tmp/b30s2-unit-architecture.txt`,
`/tmp/b30s2-postgres.txt` and `/tmp/b30s2-owners.txt`, respectively. No PostgreSQL
server version or database PASS was observed. No full suite was run. Only this
draft is authored; no gate, Phase exit or implementation authorization is claimed.
