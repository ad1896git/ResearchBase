# Other Approval Purposes/Effects and External Submission (B32) Contract — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

## Start here (for the implementer)

There are **no unimplemented normal-path approval purposes or local consuming
effects** in architecture 17's finite table in this checkout. The two manuscript
purposes already have request/decision gates and consuming owners. External
submission is still deferred; it is not a fourth approval tuple.

The smallest first slice proposed here is **test-only contract reconciliation**:
verify that purpose, exact target, capability, receipt command and concrete result
remain distinct across the three implemented local effects. Reuse the existing
owners and fixtures. Do not create another approval service or persistence model.
Manuscript rejection reconsideration remains a separate missing workflow.

After owner approval and separate execution authorization:

1. Recheck the inventory in §1 against the then-current code and migration head.
2. Pin the existing tuple/DTO/error contracts in focused tests (§11).
3. Exercise substitution denials and exact completed replay through all three
   owning Application services (§12.3–12.5).
4. Observe the actual write lock protocols and lock-free snapshot reads; do not
   alter isolation to make the scenarios pass (§12.4).
5. Run focused checks, record actual counts and stop. This is neither full
   Phase 2 acceptance nor authorization to send a package.

Five review rules:

- Review, Decision, Approval, Command and ExternalEffect remain separate facts.
- Deterministic validity and frozen provenance outrank every favorable approval.
- A grant authorizes exactly one listed local command against one exact target.
- Each local effect, receipt, consumption and event commits atomically once.
- PREPARED, FROZEN and READY never assert a venue submission or delivery.

This document changes no architecture, schema, runtime behavior or acceptance
status. Its DDL sketch describes existing storage to verify, not SQL to execute.

## 1. Purpose, authority and current baseline

Read `AGENTS.md`, architecture 01 → 02 → 03 → 08 → 05, then Harness 09.
Architecture [17](../architecture/17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md)
§§1–3 supplies the complete tuple policy and rejection fence;
[18](../architecture/18_Phase2_Design_R3_Targeted_Remediation_v1.0.md) §5 fixes
request/receipt material; [19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md)
§§1, 4–5 fixes post-wait DB time and historical completed replay. Addendum 02
A17–A23 and Correction 12 preserve preparation versus sending. Registry 03,
Cross-Phase 08 and Hash R2 15 preserve concrete FKs, immutable history and hashes.
No B32 execution pack is assumed or replaced by this draft.

Inventory first; source presence is not a passing acceptance result:

| Purpose / exact request target | Request/decision gate now | Consuming owner and local effect now | Unimplemented remainder |
| --- | --- | --- | --- |
| `INTERNAL_SCIENTIFIC_RELEASE` / FROZEN valid ScientificConclusionVersion | `application/approval.py:request_approval`, `decide_approval`; B09 | `application/scientific_conclusion.py:record_internal_scientific_release` delegates to B13 ApprovalService; receipt result equals target; no material mutation | No missing normal-path tuple/effect. |
| `READY_FOR_SUBMISSION` / FROZEN valid ManuscriptVersion, Publication INTERNAL_REVIEW | Same ApprovalService, B14r gate and B11 Decision | `application/publication.py:transition_publication_ready`; B14 INTERNAL_REVIEW→READY event plus Publication result receipt | Manuscript-purpose rejection reconsideration is not supplied by B10. |
| `PREPARE_SUBMISSION` / FROZEN valid ManuscriptVersion, Publication READY | Same ApprovalService, B12 Decision/gate | `application/prepared_submission.py:freeze_prepared_submission`; B17 PREPARED→FROZEN with exact manifest, authorship/current consent and package result receipt | Manuscript-purpose rejection reconsideration is not supplied by B10. |
| External submission | No executable tuple in 17–19 | No venue-send owner in these contracts | Actual SubmissionVersion/SubmissionRecord, connector, dispatch, external receipt and Command→ExternalEffect chain remain deferred optional extension. |

Paths above are under `src/researchbase/`. Concrete evidence is
`domain/approval.py:TUPLES`, `RECEIPT_COMMANDS`, result classes and decoder;
`application/approval.py:_consume_in_uow`, `_consume_ready_in_uow`,
`_consume_package_in_uow`; migrations `0055_b09_approval_tuples.py`,
`0059_b13_grant_consumption.py`, `0063_b14r_ready_approval.py`,
`0064_b14_publication_ready.py`, `0067_b17_prepared_package_freeze.py`.
The older PR2-17/18 proposal baseline paragraphs predate these implementations.

The remaining rejection gap is concrete: `application/decision.py`'s
`_reconsideration_view` fixes purpose to INTERNAL_SCIENTIFIC_RELEASE, and
`application/approval.py:_successor_gate` consumes its conclusion-specific
readback. A manuscript-purpose rejection therefore does not authorize a silent
resubmission. Do not generalize this workflow within a tuple parity test slice.

## 2. Proposed scope and non-goals

S1 adds only focused tests of the existing three-row policy and its local
postconditions. Positive fixtures must use owning services; no SQL-fabricated
FROZEN state, READY transition, author consent, grant or completed receipt.
Preserve the existing owner suites instead of duplicating their full admission
matrices. No production change is proposed. If a test reveals a defect, record
its location and violated contract; obtain a bounded repair contract separately.

External-send work requires a later owner-approved purpose/target/command/effect
contract, including dispatch identity, external outcome ambiguity, authorization,
consent scope, retries and reconciliation. This draft chooses none of those
policies and creates no provisional `SEND_SUBMISSION` enum or soft reference.

## 3. Invariants and local-effect closure

1. An ApprovalRequest binds one concrete target FK, exact verified hash, project,
   affirmative purpose-matching Decision and exact independent review set.
2. Request/decision does not execute a consuming effect. An independent active
   HUMAN APPROVER is distinct from requester, deciding actor, material contributors
   and required reviewers. OWNER, Agent role and on-behalf-of do not substitute.
3. Each consuming caller is an active RESEARCHER or OWNER. Recheck frozen closure,
   current deterministic validity, blocking issues, exact basis, grant and issuer
   authority, trusted credential and finite expiry independently at consumption.
4. READY grant cannot freeze a package. PREPARE grant cannot make a Publication
   READY. Internal release cannot change manuscript or publication lifecycle.
5. Package freeze consumes a distinct PREPARE grant for the exact manuscript,
   checks mandatory current author consent, and preserves exact consent FKs.
   Withdrawal after freeze changes derived validity, never frozen history.
6. One grant has at most one immutable consumption and one terminal transition;
   receipt result shape must match purpose and same-parent constraints.

### 3.1 Receipt projection and hash ordering

Reuse `domain/approval.py:consumption_request_material` literally: R3 type
ApprovalGrantConsumptionRequest, material_version=1, uppercase command, project,
actor, grant, exact typed target/hash, result_id, expected_package_manifest_hash,
and UUID-text-sorted checked_review_ids. Command key is the lookup identity,
not another material key. No new digest, payload version or material field.
Existing `result_dto` JSONB is a closed versioned receipt projection backed by
concrete result FKs; it is not a new semantic owner or generic execution record.

## 4. Proposed commands, closed DTOs and readback

No new command or query. Exercise `RequestApprovalCommand`,
`DecideApprovalCommand`, `RecordInternalScientificReleaseCommand`,
`TransitionPublicationReadyCommand`, `FreezePreparedSubmissionCommand` and
their owning methods. Read exact requests/decisions/grants and
`ApprovalService.get_grant_consumption(project_id, command_key)`; use owning
Publication/package readback to verify the effect. See §11.2 for exact fields.
Use VerifiedPrincipal from the trusted boundary; never accept caller assertions
of actor, effective role, status, hash, time, consent or external outcome.

## 5. Persistence/schema proposal — no migration

No added table, column, index, trigger, dependency or migration. Retain the
concrete request target XOR, grant tuple, receipt result XOR, unique grant/key,
same-parent and deferred graph guards described in §12.2. No scientific cascade.

## 6. Proposed error contract

Reuse existing ErrorCode values and transport mappings (§11.3). A structurally
malformed DTO fails VALIDATION_ERROR; a well-formed unlisted purpose/target or
cross-capability substitution fails APPROVAL_PURPOSE_TARGET_COMMAND_INVALID.
Check substitutions with otherwise admissible fixtures so an earlier expiry or
authorization denial does not mask the tuple gate. Do not remap every denial to
one generic approval error.

## 7. Concurrency, transactions and replay

One command uses one synchronous UoW transaction. Approval snapshot writes use
READ COMMITTED with the first-SHARE protocol; consuming effects retain the
existing SERIALIZABLE protocol required by R3 and their SQL guards. These are
different operations, not interchangeable transaction defaults.

After every blocking wait, reread affected durable state and use fresh
`clock_timestamp()` immediately before the protected effect. Equality with
expiry denies; transaction-start time and cached credentials cannot authorize.
Force deferred checks before final checks/commit as the owning service does.
All partial effect/receipt/event writes roll back on failure.

Completed matching replay authenticates the original actor/project and current
read entitlement, checks normalized saved scope/hash and returns saved result.
It performs no new effect and does not require the original grant to become
usable again. Changed same-key arguments conflict; a different key cannot reuse
a consumed grant. Read-only exact reads/replay use one REPEATABLE READ snapshot
without explicit table, advisory or row locks and without terminalizing grants.
Inherent PostgreSQL AccessShareLock on SELECT is not an explicit exclusion lock.

Retain existing retry classification: at most three fresh attempts for the
owning command's normalized retryable SQLSTATE conflicts; uncertain commit is
resolved with the same key, never a second external attempt. No retry engine.

## 8. Architecture and adversarial tests to add later — NOT IMPLEMENTED

S1 must demonstrate distinct purpose/target/effect across all three rows, zero
partial writes on cross-tuple substitution, immutable completed replay after
expiry, and absence of network effects. Preserve post-wait expiry, source
invalidity, new blocker, consent withdrawal and direct-SQL guard tests in their
existing owner suites. §12.5 names the proposed additional artifacts.

## 9. Dependencies, acceptance criteria and stop boundary

Dependencies B09, B13, B14r and B17 exist, with B11/B12 Decisions and B14 lifecycle
owner. Reuse their executed evidence only after rerunning the named regressions.
Acceptance for S1 requires the new separation tests, current static/unit/
architecture checks and relevant PostgreSQL 18.x suites with exact counts;
no open P0/P1. A skipped/blocked check is not PASS. The surrounding loop owns the
full-suite run; do not run it here. Stop after bounded evidence. This cannot
declare external submission or the full Phase 2 gate complete.

## 10. Glossary

| Term | Meaning |
| --- | --- |
| Purpose | Why authorization is requested; one of the three finite policy values. |
| Target | Exact FROZEN scientific conclusion or manuscript and verified hash. |
| Capability | Lowercase `allowed_command` naming the sole permitted Application effect. |
| Consuming effect | Atomic local release fact, READY transition or package freeze. |
| Receipt command | Uppercase literal in R3 material and the saved typed result. |
| Prepared package | Exact retained preparation context; FROZEN still does not mean sent. |
| ExternalEffect | What actually changed externally; no such effect in S1. |
| Reconsideration | Separate immutable Decision addressing every prior same-project/purpose rejection; manuscript support remains deferred here. |

## 11. Decisions taken in this draft

### 11.1 Scope, lifecycle and replay decisions

Adopt test-only S1 because all three normal-path tuples and local owners exist.
No fourth purpose, no new endpoint and no migration. Keep rejection equivalence
at `(project_id, purpose)`; do not clear manuscript rejection fences to obtain a
successful fixture. Preserve grant ACTIVE→CONSUMED|EXPIRED|REVOKED|STALE only,
max_uses=1 and no reactivation. Contract approval is not execution authorization.

### 11.2 DTO fields, types, limits and enums

Existing frozen dataclasses are authoritative; this slice tests them unchanged.
`UUID` below means strict Python UUID (canonical lowercase hyphenated wire text),
not bool/int/string coercion. Optional means exactly the stated type or None.

| DTO | Fields and bounds |
| --- | --- |
| RequestApprovalCommand | `id, project_id, basis_decision_id: UUID`; `scientific_conclusion_version_id: UUID | None`; keyword `manuscript_version_id: UUID | None`, exactly one target; `approval_purpose: str` from the three §1 literals; `review_ids: tuple[UUID, ...]`, distinct, nonempty, max 100 enforced by service, normalized UUID-text order; keyword `prior_rejected_request_id, reconsideration_decision_id: UUID | None`, both or neither. Default purpose INTERNAL_SCIENTIFIC_RELEASE. |
| DecideApprovalCommand | `id, project_id, approval_request_id: UUID`; `decision: str` exactly APPROVE, APPROVE_WITH_CONDITIONS or REJECT; `rationale: str`, nonblank NFC, NUL forbidden; `valid_until: datetime | None`, timezone-aware normalized UTC; `requires_current_author_consent: bool` strict, default false. Only conditional outcome accepts nonnull expiry and consent=true; conditional outcome requires expiry. Rationale is limited to 1..16,384 characters by normalization plus the service gate; the DTO itself does not enforce the maximum. Consent=true is accepted only for PREPARE_SUBMISSION by the service. |
| All three effect commands | `command_key, project_id, grant_id, result_id: UUID`; `checked_review_ids: tuple[UUID, ...]`, 1..100 distinct, sorted by canonical text. Release has `expected_package_manifest_hash: None = None`; READY has no such input field; freeze requires `expected_package_manifest_hash: str`, exactly 64 lowercase hex characters. Result ID is conclusion target, owning Publication, or exact package respectively. |
| Saved result | ScientificReleaseResult, PublicationReadyResult or PreparedSubmissionFreezeResult: `consumption_id: UUID` and exactly one named result UUID; constant uppercase command from §1 capability. `result_dto_version: int` strictly 1, not bool. Decoder rejects extra keys and noncanonical UUID strings. |
| ConsumptionReadback | `id, project_id, grant_id, command_key, actor_id: UUID`; `consumed_at: datetime` UTC; `command, request_hash, hash_scheme: str` (three receipt commands, lowercase hex64, sha256-cjson-v1); exact checked review tuple; three nullable concrete result UUID fields, exactly one nonnull; strict v1 and corresponding typed result. |

Grant expiry is finite, later than decision time and at most 30 days after it;
plain APPROVE derives that 30-day expiry. PREPARE consumption independently
requires consent=true and current direct HUMAN author consent; APPROVE alone
cannot satisfy it. No free-text executable conditions or caller-selected enum.

### 11.3 Error-code transport mappings

These are the actual mappings in `src/researchbase/api/errors.py:_STATUS` and
`src/researchbase/cli/errors.py:CLI_EXIT_CODES`; reuse their shared envelopes.

| Codes / condition | HTTP | CLI exit |
| --- | --- | --- |
| VALIDATION_ERROR | 422 | 2 |
| NOT_FOUND | 404 | 3 |
| AUTHENTICATION_REQUIRED | 401 | 3 |
| FORBIDDEN, CONFLICT_OF_INTEREST | 403 | 3 |
| APPROVAL_PURPOSE_TARGET_COMMAND_INVALID, APPROVAL_GATE_FAILED, DECISION_BASIS_INVALID, APPROVAL_TARGET_STALE, REJECTION_RECONSIDERATION_REQUIRED | 409 | 4 |
| GRANT_INVALID, GRANT_STALE, IDEMPOTENCY_CONFLICT, CONCURRENT_MODIFICATION, INVALID_STATE_TRANSITION, VERSION_NOT_FROZEN, IMMUTABLE_RECORD | 409 | 4 |
| FROZEN_REFERENCE_REQUIRED, PROVENANCE_CLOSURE_VIOLATION, REFERENTIAL_INTEGRITY_ERROR | 409 | 5 |
| Unexpected exception: INTERNAL_ERROR, sanitized existing fallback | 500 | 1 |

Wrong expected package manifest yields CONCURRENT_MODIFICATION; wrong complete
review set yields DECISION_BASIS_INVALID, following B17 substitution tests.
No new B32 error values or HTTP/CLI routes are proposed.

## 12. Implementation guide — future authorization required

### 12.1 Not in this slice

External send/connector/outbox/queue, SubmissionVersion/SubmissionRecord,
ExternalEffect storage, new send-purpose consent, publisher outcomes,
manuscript rejection reconsideration and MANUSCRIPT_CHANGE RevisionAction,
new grant conditions, broader IAM, automatic impact propagation and new
production schemas are excluded. No new production mechanism is needed for S1.

### 12.2 Exact DDL sketch

**Existing schema projection only; no CREATE/ALTER is proposed.** Verify actual
catalog definitions at head, not older release-only forms of the same checks.

```sql
-- approval_grant_consumptions (0059, amended by 0064 and 0067)
id UUID                         -- pk_b13_consumptions
grant_id UUID NOT NULL          -- uq_b13_consumption_grant; fk_b13_consumption_grant
command_key UUID NOT NULL       -- uq_b13_command_key
project_id UUID NOT NULL        -- fk_b13_consumption_project
actor_id UUID NOT NULL          -- fk_b13_consumption_actor
consumed_at TIMESTAMPTZ NOT NULL -- ck_b13_time: isfinite
command VARCHAR(40) NOT NULL
request_hash CHAR(64) NOT NULL  -- ck_b13_hash: lowercase hex64
hash_scheme VARCHAR(32) NOT NULL -- ck_b13_hash: sha256-cjson-v1
result_dto_version SMALLINT NOT NULL -- ck_b13_dto: =1
result_dto JSONB NOT NULL       -- ck_b13_dto: object; closed decoder/receipt guards
result_publication_id UUID     -- fk_b13_result_publication
result_scientific_conclusion_version_id UUID -- fk_b13_result_conclusion
result_prepared_submission_version_id UUID  -- fk_b17_result_package
-- ck_b13_result_tuple: exactly the matching nonnull result FK:
-- RECORD_INTERNAL_SCIENTIFIC_RELEASE -> conclusion
-- TRANSITION_PUBLICATION_READY -> publication
-- FREEZE_PREPARED_SUBMISSION -> prepared package
```

All listed FKs use ON DELETE RESTRICT. `fk_b17_result_package` is DEFERRABLE
INITIALLY DEFERRED. `uq_b17_package_consumption` prevents another consumption of
the same package; `uq_b17_frozen_publication` is the partial unique FROZEN-package
index. Request/grant tuples use `ck_b09_request_tuple` and `ck_b09_grant_tuple`;
`ck_b09_consent_condition` restricts the conditional approval shape.

Preserve deferred graph validation, following 0042's
`pr215_complete_decision/conclusion/review` constraint triggers:
0064 supplies `b14_complete_publication`, `b14_complete_ready_event`,
`b14_complete_ready_consumption`; 0067 supplies `b17_complete_package`,
`b17_complete_item`, `b17_complete_event`, `b17_complete_consumption`.
These AFTER ROW constraint triggers are DEFERRABLE INITIALLY DEFERRED, enforcing
complete linked effects rather than accepting an isolated receipt or status.
S1 does not replace them with Application-only checks or modify old migrations.

### 12.3 Ordered build steps and file paths

1. Inspect the §1 owners and `migrations/versions/0063_b14r_ready_approval.py`,
   `0064_b14_publication_ready.py`, `0067_b17_prepared_package_freeze.py` at the
   actual head. Reconcile inventory without changing authoritative documents.
2. Create `tests/unit/phase2/test_b32_approval_separation.py` for literal tuple,
   receipt material, decoder and error mapping cases. Expected values must be
   independently written, not derived from production TUPLES as the oracle.
3. Extend `tests/integration/phase2/test_b13_grant_consumption.py`,
   `test_b14_publication_ready.py` and `test_b17_package_freeze.py` with the
   missing separation cases in §12.5. Reuse existing fixture builders from
   `test_approval.py`, B14 and `b17_fixtures.py`; do not add a generic executor.
4. Create `tests/architecture/test_b32_boundaries.py` for the bounded absence of
   external calls in these effect owners and lock-free formal read paths.
   Observe SQL through existing test instrumentation, not a production hook.
5. Run only the new tests plus owner regressions named in §12.5, static checks,
   unit and architecture tests. Record exact commands/counts/server version,
   findings and limitations, then stop. Production repairs require separate scope.

### 12.4 Exact S1 lock order per command

No new commands acquire locks. Tests must observe these current protocols;
named inventories mean the literal ordered tuples in the cited repository,
not dynamically discovered sets. Initial DTO/principal shape checks are in memory.
Connection setup is outside the protected transaction; no SELECT, SET LOCAL or
advisory lock precedes its first SHARE statement.

| Existing command | Ordered transaction operations to retain |
| --- | --- |
| request_approval | READ COMMITTED; first `B09_SHARE_SQL` (B09_SNAPSHOT_TABLES, ordered, SHARE); timeouts 10s/30s; advisory `pr216:uuid:{command.id}`; advisory `pr216:scope:{project}:{purpose}`; exact target FOR UPDATE (manuscript then Publication FOR SHARE where applicable); authorization and replay/admission; affected ACTIVE grants ordered by grant id FOR UPDATE when applicable; inserts, deferred checks and final authorization, commit. |
| decide_approval | READ COMMITTED; first `B09_DECIDE_SHARE_SQL` (same ordered inventory excluding publications); publications SHARE ROW EXCLUSIVE; timeouts; same UUID advisory then project/purpose advisory; exact target FOR UPDATE then manuscript's Publication FOR SHARE; saved request FOR UPDATE; read authorization/replay; independent approver gate; affected ACTIVE grants ordered by grant id FOR UPDATE; atomic decision/grant/events, deferred checks, final authorization, commit. |
| record_internal_scientific_release | SERIALIZABLE; `prepare_write`: first B13_SHARE_SQL, publications SHARE ROW EXCLUSIVE, B13_APPROVAL_SQL (approval_decisions, approval_request_reviews, approval_requests SHARE), then timeouts; advisory `b13:consume:{command_key}`; project/purpose advisory; conclusion version FOR UPDATE; owning scientific_conclusions FOR SHARE; request FOR SHARE; grant FOR UPDATE; reread, current gate/fresh DB clock, local receipt/terminal event, deferred checks/final clock, commit. |
| transition_publication_ready | SERIALIZABLE; same B13 prepare_write table order and consumption-key advisory; project/purpose advisory; manuscript FOR UPDATE; Publication FOR UPDATE; request FOR SHARE; grant FOR UPDATE; reread and READY gate/fresh DB clock; atomic lifecycle/receipt/grant event, deferred checks/final clock, commit. |
| freeze_prepared_submission | SERIALIZABLE; first B17_SHARE_SQL (ordered B17_SNAPSHOT_TABLES in prepared_submission_repository.py); publications SHARE ROW EXCLUSIVE; prepared_submission_versions SHARE ROW EXCLUSIVE; approval_decisions, approval_request_reviews, approval_requests SHARE; timeouts; advisory `b13:consume:{command_key}`; project/PREPARE_SUBMISSION advisory; manuscript FOR UPDATE, Publication FOR UPDATE, exact package FOR UPDATE; older FROZEN packages ordered by id FOR UPDATE; author chains sorted Actor UUID, each consent rows ordered id FOR UPDATE; request FOR SHARE; grant FOR UPDATE; reread context/current consent/manifest, fresh clock and full gates; atomic package/manifest/supersession/receipt/grant events; deferred checks/final clock, commit. |
| Exact reads and completed replay | One REPEATABLE READ snapshot via begin_formal_read/owner read setup; current read authorization, plain exact SELECTs and saved-hash verification, final entitlement check. No explicit table, advisory or row lock and no write. |

Advisories use existing parameterized `pg_advisory_xact_lock(hashtextextended(:key,0))`.
The READ COMMITTED first-SHARE rule follows decision_repository.py and
novelty_repository.py. It must not be used to weaken the separately specified
SERIALIZABLE consuming effects. No table-lock upgrades or altered inventories.

### 12.5 Test files and required cases

| Artifact | Focused cases |
| --- | --- |
| New unit file (§12.3) | All three literal purpose/target/capability/receipt-command/result mappings; every cross-pair denied; purpose/command case sensitivity; strict UUID/bool/tuple/hex and 0/1/100/101 reviews; duplicates; fixed request material and unchanged R3 vectors; decoder rejects wrong command/result/extra key/version; §11.3 mappings checked against both transports. |
| Existing B13 consumption file | Release result equals exact target; manuscript grants cannot release a conclusion; request/approval alone adds no consumption or lifecycle change; changed-key and same-key changed-command/result conflicts; zero partial receipt/event writes. |
| Existing B14 READY file | READY uses exact manuscript's Publication result; PREPARE grant cannot substitute; approval alone leaves INTERNAL_REVIEW; fresh read proves saved lifecycle/event/receipt link; no package freeze. |
| Existing B17 freeze file | Distinct PREPARE grant required; READY grant substitution denied with no delta; manifest/current consent gates retained; fresh read proves package receipt FK and unchanged READY history; frozen package never claims sent. Preserve existing substitution tests; add only missing cases. |
| Existing replay/race/schema suites | Preserve B13, B14r, B14 and B17 replay, concurrency and schema tests: one winner, post-lock expiry and credential loss, consent withdrawal race, final deferred-check rollback, FK/result XOR, complete graphs, immutable completed replay after expiry without mutation. Run these suites; do not copy them wholesale. |
| New architecture file (§12.3) | Same Application boundary for Human/Agent; no new canonical owner, dependency or external call from the three effects; formal reads have no explicit locking/writes; first statement/isolation and lock inventory assertions for representative writes. |

Future focused command: `uv run pytest tests/unit/phase2/test_b32_approval_separation.py
tests/architecture/test_b32_boundaries.py` plus the B09/B13/B14r/B14/B17 owner
files above (including schema, replay and concurrency variants). Run
`uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, and
`uv run pytest tests/unit tests/architecture`. PostgreSQL tests use disposable
real 18.x databases via `phase2_database_url`. Never substitute SQLite or claim
these future files exist today. The full test suite remains the loop's work.

## 13. Open questions for the owner

Approve the test-only reconciliation slice, or commission a separate manuscript
reconsideration contract first. This draft adopts the former because no normal
tuple or consuming owner is missing. External send remains an optional later
extension in either case. Any owner override must update scope, DTOs, DDL and
tests together before implementation authorization.


## 14. Documentation verification note

Only this proposal was added. No B32 tests or implementation were created.
Checks on 2026-10-19 used the already installed repository environment without
syncing dependencies. Exact environment prefix for the commands below:

```sh
export UV_CACHE_DIR=/private/tmp/rb-b32-uv-cache
export UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv
export PYTHONPATH=src
```

| Exact command | Observed result |
| --- | --- |
| `uv run --no-sync ruff check .` | PASS, All checks passed. |
| `uv run --no-sync ruff format --check .` | PASS, 736 files already formatted. |
| `uv run --no-sync pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject` | PASS, 0 errors, 0 warnings, 0 informations. |
| `uv run --no-sync pytest tests/unit tests/architecture` | 5,618 passed, 5 failed, 14 errors, 9 warnings in 74.27s. NOT PASS. |
| `uv run --no-sync pytest tests/unit/test_approval.py tests/unit/phase2/test_b13_grant_contract.py tests/unit/phase2/test_b14r_ready_approval_contract.py tests/unit/phase2/test_b14_ready_contract.py tests/unit/phase2/test_b17_freeze_contract.py tests/unit/phase2/test_b17_freeze_hash_vectors.py tests/architecture/test_basic_approval.py tests/architecture/test_b13_grant_boundaries.py tests/architecture/test_b14r_ready_approval_boundaries.py tests/architecture/test_b14_ready_boundaries.py tests/architecture/test_b17_boundaries.py` | PASS, 308 passed, 1 warning in 0.95s. |

The broad unit/architecture run's static-acceptance subprocess used the empty
local virtualenv and reported new missing-import diagnostics; the explicit
Pyright environment run above passes. Four runner failures involved socket
operations; a focused `uv run --no-sync pytest tests/unit/test_hg1_runner.py -x`
confirmed `connection.bind` raises PermissionError (1 failed, 16 passed in
0.08s). The 14 PR2-19 architecture setup errors lacked an explicit disposable
PostgreSQL admin URL. No source repair was attempted for these environment limits.
The plain `uv` attempts also could not write the default cache; a new offline
cache could not download Ruff. No dependency or lockfile was changed.

Focused PostgreSQL command, after explicitly setting disposable local URLs:

```sh
RB_TEST_ADMIN_URL='postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres' DATABASE_URL='postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase' uv run --no-sync pytest tests/integration/phase2/test_b09_approval_schema.py tests/integration/phase2/test_b09_approval_concurrency.py tests/integration/phase2/test_b13_grant_*.py tests/integration/phase2/test_b14r_*.py tests/integration/phase2/test_b14_publication_ready.py tests/integration/phase2/test_b14_ready_*.py tests/integration/phase2/test_b17_*.py --maxfail=1
```

Result: **1 setup error in 0.73s; zero tests passed**, stopped at the first test:
localhost TCP connections denied with Operation not permitted. The same file
selection with `--collect-only` instead of `--maxfail=1` collected **403 tests in
0.61s**; collection is not execution. An earlier attempt without the admin URL
stopped with 1 setup error in 0.65s. A disposable PostgreSQL 18 initdb attempt
also failed at bootstrap with shared-memory allocation exhaustion. PostgreSQL
suites remain BLOCKED, not accepted. The full suite was not run; its evidence
belongs to the surrounding loop. No Phase 2 gate success is claimed.
