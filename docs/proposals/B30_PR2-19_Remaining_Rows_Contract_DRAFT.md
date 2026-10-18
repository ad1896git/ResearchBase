# Remaining PR2-19 Golden/Failure Rows (B30) Contract — DRAFT

**Status: APPROVED by owner 2026-10-18 — first slice authorized for implementation**

## Start here (for the implementer)

B30 proposes a second, test-only PR2-19 slice. Reassess the old blocker inventory
against this checkout; preserve every existing runnable test. A runnable contract
means tests can be written now, not that the row has passed or its owner is accepted.
The full gate remains BLOCKED. No production code or other document changes are
authorized by this draft.

Build in this order after separate authorization:

1. Use the row → owner → fixture matrix in §2; retain the original row IDs and
   distinguish complete rows from runnable prefixes.
2. Extend the existing report allowlists and dependency inventory (§11). Replace
   the historical frozen inventory with subcase-level prerequisites; never merely
   delete a blocker because a module exists.
3. Finish G1/G5/F2b evidence, then conclusion governance, rollback and release
   consumption cases; separately exercise the available G7 novelty branch (§12.4).
4. Run each scenario through owning Application services with independent actors,
   separate command commits and fresh service/readback instances.
5. Observe exact transaction/lock order (§12.2), verify retained bytes and hashes,
   and record actual counts and blockers. Stop at this bounded slice.

Five review rules:

- Deterministic facts outrank Review, Decision and Approval. Citation is not support.
- No SQL-fabricated FROZEN/READY state, consent, grant, result or successful promotion.
- No new canonical schema, dependency, generic execution DSL or public fault hook.
- Reads use one REPEATABLE READ snapshot, with no explicit table, advisory or row
  exclusion locks. Ordinary PostgreSQL AccessShareLock is not an exclusion lock.
- A green prefix, skipped prerequisite or grant creation cannot pass its whole row.

The older [PR2-19 plan](PR2-19_E2E_Failure_Injection_Plan_DRAFT.md) remains the row
catalog. Its §14 matrix and `test_pr2_19_dependencies.py` explicitly describe the
original slice. This draft proposes their later reconciliation; it does not edit
or silently reinterpret that historical evidence.

## 1. Purpose, authority and inspected baseline

Read `AGENTS.md` and architecture 01 → 02 → 03 → 08 → 05 → Harness 09 before the
PR2-19 plan and tests. Applicable authorities:

| Authority under `docs/architecture/` | Binding rule |
| --- | --- |
| `01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md`, §§3, 7–9 | One fact owner, frozen closure, immutable history, shared Application boundary. |
| `02_Final_Architecture_Correction_Addendum_v1.0.md`, A2–A5, A18–A23; `03_Global_Schema_and_Contract_Registry_v1.0.md` | Concrete formal FKs; no test evidence scientific entity or early AgentPromotionRecord. |
| `08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md`, §§9–18, 24, 41 | Preserve Phase 1 material/hashes and owning error semantics. |
| `05_Phase2_Development_Specification_v1.1_Harness_Integrated.md`, §§42–43, PR2-19 | Golden paths and failure families remain required. |
| `12_Phase2_Architecture_and_Contract_Correction_v1.0.md`, §§1, 5–7; `15_Phase2_Hash_Payload_Contract_R2_v1.0.md` | Prepared means no send; exact closure and literal material. |
| `17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md`, §§1–4; `18_Phase2_Design_R3_Targeted_Remediation_v1.0.md`, §5; `19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md`, §§1, 4–5 | Finite tuples, completed revision, current consent, atomic consumption and post-wait authorization; completed replay is historical read. |

Current evidence is the code, migrations through `0059_b13_grant_consumption.py`,
and named tests below. Proposal banners and older baseline paragraphs are not
proof of current implementation. The [PR2-17](PR2-17_Submission_Authorship_Contract_DRAFT.md)
and [PR2-18](PR2-18_Novelty_PriorArt_Contract_DRAFT.md) structure is followed here;
B30 adopts no deferred production behavior from either proposal.

## 2. Scope, dependency boundaries and non-goals

S1 means first implementable test slice after approval. BLOCKED suffixes remain
required for their original full row. Paths below are relative to this repository;
Application owners are under `src/researchbase/application/` and fixture/test
modules under `tests/integration/phase2/`.

| Remaining row | Owning contract and implemented now? | Required fixture and runnable S1 | Remaining blocker |
| --- | --- | --- | --- |
| G1 | B01 resolution (`search_result_resolution.py`), PR2-04 search, M3 evidence and PR2-11 conclusion: yes | `b01_support.py:b01_env`; fixed persisted hit → `record` exact frozen source → quotation → independent VERIFIED review → conclusion freeze/read. Extend `test_pr2_19_search_evidence.py`'s existing positive bridge case with fresh readback and exact resolution replay. | None for this path; its old resolution blocker is obsolete. |
| G2 | PR2-07 native strategy: yes (`native_research_strategy.py`); successful candidate admission owner: absent | `pr2_19_support.py:pr219_candidate_env`; preserve native output/revision and zero scientific delta in `test_pr2_19_candidates.py`. | Positive ResearchBrief → question/hypothesis DRAFT admission: no owning candidate-binding/authority/replay contract or service. Ordinary create alone is not promotion proof. |
| G4 | PR2-10 discussion/artifacts: yes (`discussion.py`, `discussion_artifacts.py`); positive promotion: absent | `pr219_discussion_env`; preserve close/bind/restart and F4 FORBIDDEN cases in `test_pr2_19_discussion.py`. | Explicit discussion candidate → HypothesisVersion DRAFT admission, exact provenance and replay; `request_promotion` always denies. |
| G5 | PR2-12/13 placements/trace and B04 freeze: yes (`manuscript_freeze.py`) | `test_b04_manuscript_freeze.py:b04_env`; preserve existing G5 freeze case in `test_pr2_19_citation_trace.py`; add artifact placement, CAS verification, fresh exact FROZEN read/trace and expected hashes. | None for initial freeze. Later manuscript revision is a different contract. |
| G6 | PR2-14 review, B06 revision, B07 revision Decision/carry-forward, B08 disposition, PR2-16/B09 approval: implemented for Claim/conclusion; B05 manuscript review exists | `test_revision_action.py:revision_env`, `b08_support.py`, `test_approval.py:approval_env`; compose conclusion correction/re-review/disposition, new-target PROCEED → request → decision → grant, retaining old history. | Manuscript RevisionAction result remains explicitly denied by `RevisionActionService._supported`; do not claim the manuscript cycle. RevisionAction alone leaves Issue OPEN. |
| G7 | PR2-18 coverage/six prior-art kinds/INCONCLUSIVE and PR2-17 contribution/authorship: implemented (`novelty.py`, `authorship.py`); B11/B12 Decisions and B09 approval tuples exist | `pr2_18_fixtures.py:novelty_env`; available Claim → coverage/comparison/INCONCLUSIVE branch in new `test_pr2_19_novelty.py`. Contribution/snapshot owner tests remain regression evidence. | Full READY → prepared package/current consent: B14 transition and package/consent/freeze commands absent. No `transition_publication_ready` or `freeze_prepared_submission` implementation. Strong novelty outcomes lack frozen exact screening/comparison basis. Authorship exact reads still lock in `_get`; exclude them from B30 lock-free read scenarios pending owner remediation. |
| F1 | Source lineage, PR2-11 current conclusion validity, B25 manuscript validity/audit, B09 approval: implemented, bounded | `pr219_evidence_env`, `test_b05_manuscript_review.py:b05_env`, `b25_support.py`; direct-literature and Claim-snapshot corrections/retractions, exact old history, current projection and new conclusion admission/approval denial in `test_pr2_19_lineage.py`. | READY/prepared-package downstream suffix awaits B14/package owner. Automatic finding/impact propagation is not supplied by B25; use authorized assessment commands only where required, and never claim automation. |
| F2b | B27 saved-dependency normalization (`saved_provenance.py`) plus existing CAS/hash guards: yes | `pr219_decision_env`, `b27_fixtures.py`; preserve existing missing saved-review replay case in `test_pr2_19_integrity.py`; add fresh formal reads after isolated committed corrupt FK and unchanged row/event counts. | None for contracted B27 roots; no claim of a universal defensive reader for all tables. |
| F5 | B09 approval gates/B05 review: yes; READY consuming transition: absent | `approval_env`; OPEN/BLOCKING at request and after committed request, zero partial decision/grant/events, prior request preserved in `test_pr2_19_governance.py`. | Lifecycle READY bypass/consumption suffix requires B14; available manuscript tuple denial is not a successful READY transition. |
| F5b | B09 current facts, complete basis, finite tuple and independence: yes | `approval_env`, B09/B12 manuscript approval fixtures; stale/retracted support, wrong tuple/project, all forbidden actor equalities, Agent/OWNER/on-behalf-of and temporal role/credential loss. | No blocker for bounded approval denial. Consent-dependent package checks await package/consent owner. |
| F5c | B09 rejection fence and B10 reconsideration: yes, B10 release scope | `test_b10_reconsideration.py:reconsideration_env`; same-purpose rejection then changed request/version/approver; pre-created request denial; exact approved successor links and historical replay controls. | Reconsideration of manuscript-purpose tuples remains outside B10's release-only scope; keep it BLOCKED rather than generalizing the code. |
| F6 | B06/B07 completed results and revision decisions: six action types implemented, seven typed result slots | `revision_env`; reuse completed Spec+Run, analysis, Claim, conclusion and source builders from `test_b06_revision_action.py`, plus B07 ACCEPT_NO_CHANGE Decision fixture. Deny DRAFT/planned/unrelated/wrong project/pair/fork; accepted action makes no Issue disposition. | Seventh action type MANUSCRIPT_CHANGE explicitly deferred. Seven result columns are not seven accepted action types. NO_CHANGE needs explicit revision Decision, never minimal PROCEED. |
| F7 | PR2-16/B09 atomic request/decision/grant/events; B13 receipt/terminalization: yes | `approval_env`; new `test_pr2_19_approval_atomicity.py`; inject after each protected insert/check and before commit, read through new service. Existing `test_pr2_19_atomicity.py` stays intact. | No blocker for these commands; READY/package effect atomicity waits for its owners. |
| F9 | B13 lifecycle/consumption and `ScientificConclusionService.record_internal_scientific_release`: yes for internal release | `approval_env`, builders in `test_b13_grant_consumption.py:issued`; new `test_pr2_19_grant_consumption_release.py`; invalid/expired/stale/consumed grants, concurrent use, role loss/blocker, entitled completed replay. | READY and prepared-package consumption remain BLOCKED by B14/package owners. Generic receipt DTO/tuple presence does not implement an effect. |

Preserve G0/G3/F1b/F2/F3/F4/F8 and every runnable prefix in the original matrix.
Do not repurpose reserved `test_pr2_19_revision.py` or
`test_pr2_19_grant_consumption.py` while the historical dependency test requires
those files to be absent. Use the new bounded file names in §12.4.

## 3. Invariants and conservative judgments

Scientific content and exact references never change to satisfy an approval.
A correction/retraction appends lineage; current invalidity does not rewrite
historical bytes or hashes. SUPERSEDED navigation alone is not invalidity.
LiteratureSupportSnapshot remains separate from frozen Phase 1 Claim support.
Keep direct literature, Claim snapshot, experiment and citation-only paths distinct.

Human and Agent use verified owning boundaries; independent HUMAN reviewers and
approvers remain required where the command specifies them. Establish read
entitlement before protected existence or corruption diagnostics. Each command
is a separate transaction; a later rollback retains committed predecessor facts.

## 4. Proposed commands, DTOs and historical readback

No new product command/query/DTO. Call existing closed dataclasses and service
methods, never ORM entities as domain results. Reuse `ScenarioSpec`,
`ScenarioObservation`, `StateDelta`, `VerifiedHash`, `LockEvent` in
`tests/integration/phase2/pr2_19_support.py`; pin their fields in §11.3.
Expected IDs, bytes, relation membership and digest vectors must be independent
of the result under test. Fresh reads must use the actual formal reader, not
merely a test SELECT count. SQL count/catalog observers are additional evidence.

## 5. Schema and literal hash proposal — no migration

**DO NOT ADD SCHEMA.** B30 has an empty DDL change set, no new hash material,
canonical test receipt, Alembic revision or runtime dependency. All production
objects remain owned by their existing migrations. §12.1 lists constraints that
future tests observe, not DDL to execute outside migrations.

## 6. Error contract — existing categories only

Use §11.2, `src/researchbase/foundation/errors.py`, `api/errors.py` and
`cli/errors.py`. Candidate warnings are not ErrorCode members. Normal-role SQL
constraint probes assert owning SQLSTATE/constraint; privileged corruption is
only isolated setup for defensive readers. Neither is an Application error code.

## 7. Transactions, concurrency and failure recovery

Do not introduce persistence or retry mechanisms. Use the owning first-SHARE
READ COMMITTED write protocols and B13's separately contracted SERIALIZABLE
consuming transaction. Exact reads and completed replay are read-only snapshot
paths, without exclusion locks. §12.2 specifies orders to observe.

Use two independent connections/backend PIDs and barriers plus `pg_locks` /
`pg_blocking_pids`; sleeping does not prove contention. Record wait, acquisition,
fresh DB-clock authorization, final check and commit/rollback. Recheck after
blocking deferred checks. Faults classified as 40001/40P01 retry only under the
owner's bounded three-total-attempt policy; permanent business denial, timeout
and uncertain commit do not become generic retries. After lost response, use
same-key exact entitled replay; changed material conflicts.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

§12.4 names artifacts and cases. Reuse deterministic corpus/provider doubles,
real disposable PostgreSQL 18.x and current migrations. No live provider is a
semantic gate. Count parent/child/event/receipt deltas, verify exact closure and
CAS bytes, and assert no unrequested scientific/governance/external effect.
No production fault hooks: wrap repository calls in tests, execute the real
operation, then raise. A caught exception alone is insufficient evidence.

## 9. Acceptance criteria and evidence boundary

S1 acceptance requires its named subcases to pass, old runnable rows preserved,
static/unit/architecture and touched PostgreSQL checks recorded with exact counts,
and no open P0/P1 findings. Full PR2-19 and Phase 2 exit remain BLOCKED by §2.
Report unavailable prerequisites as BLOCKED, actual failures as failures and
setup errors as errors; do not use xfail/skip to turn them into acceptance.
The loop runs the full suite; the implementer runs only focused suites.

## 10. Glossary

| Term | Meaning |
| --- | --- |
| Row / suffix | Original G/F scenario / its remaining dependent steps; neither gets a new scientific identity. |
| Owner | Existing contract and Application service that validates and persists a fact. |
| Runnable | Required commands and fixture construction exist; execution evidence is still required. |
| S1 | First implementable test-only B30 slice, subject to separate approval. |
| Frozen closure | Exact IDs/hashes and typed transitive dependencies, without latest/current fallback. |
| Current validity | Timestamped derived state, separate from immutable saved material. |
| Consumption | One scoped command result and grant terminalization/receipt in the same transaction. |
| Completed replay | Read of an already committed exact command result under current read entitlement. |
| Privileged corruption | Disposable fixture mutation bypassing guards solely to test fail-closed readers. |

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

Adopt §2's S1 and explicit suffix blockers. A future implementation updates
`test_pr2_19_dependencies.py` to retain the historical inventory separately and
report current subcase prerequisites. Keep its fail-closed full-gate assertion.
The `test_approval_does_not_override_invalid_fact` architecture obligation must
receive real B09/B13 evidence before removal from the blocked list.

Extend existing finite command/row allowlists only for scenarios actually built;
never accept arbitrary service names. Do not change production enums or transport
mappings. Defects go back to the owning PR; B30 cannot fix them opportunistically.
In particular, locking authorship reads are an owner discrepancy, not a pattern
for new B30 reads and not a reason to weaken the no-lock assertion.

### 11.2 Pinned error mappings

These are current HTTP status / CLI exit values, not proposed mappings:

| ErrorCode | HTTP | CLI | Oracle |
| --- | ---: | ---: | --- |
| VALIDATION_ERROR | 422 | 2 | Closed DTO/unknown bypass fields. |
| AUTHENTICATION_REQUIRED | 401 | 3 | Missing authenticated boundary. |
| FORBIDDEN | 403 | 3 | Entitlement/role/credential denial; discussion promotion. |
| CONFLICT_OF_INTEREST | 403 | 3 | Owning independence check. |
| SUBJECT_BINDING_UNPROVEN | 403 | 3 | Unproven subject binding. |
| NOT_FOUND / SOURCE_VERSION_NOT_FOUND | 404 | 3 | Entitled absent requested root, according to owner. |
| REVIEW_TARGET_NOT_FROZEN | 409 | 4 | Review admission; existing provisional mapping retained. |
| VERSION_NOT_FROZEN / INVALID_STATE_TRANSITION | 409 | 4 | Owner lifecycle denial; manuscript revision stays unavailable. |
| INVALID_SOURCE_VERSION_LINEAGE / SOURCE_VERSION_NOT_FREEZABLE / SOURCE_VERSION_IMMUTABLE | 409 | 4 | Source owner lineage/freeze/history checks. |
| FROZEN_REFERENCE_REQUIRED / PROVENANCE_CLOSURE_VIOLATION / REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Formal admission or integrity failure. B27 resolved-root broken dependency uses PROVENANCE_CLOSURE_VIOLATION. |
| IMMUTABLE_RECORD | 409 | 4 | Owning immutable-write denial. |
| IDEMPOTENCY_CONFLICT / CONCURRENT_MODIFICATION | 409 | 4 | Changed replay / bounded retry exhaustion. |
| APPROVAL_PURPOSE_TARGET_COMMAND_INVALID | 409 | 4 | Finite tuple/result mismatch. |
| DECISION_BASIS_INVALID | 409 | 4 | Invalid/incomplete exact basis. |
| APPROVAL_GATE_FAILED | 409 | 4 | Current applicable blocker. |
| APPROVAL_TARGET_STALE | 409 | 4 | Approval target invalidity/staleness. |
| REJECTION_RECONSIDERATION_REQUIRED | 409 | 4 | Uncovered project/purpose rejection. |
| GRANT_INVALID / GRANT_STALE | 409 | 4 | B13 unusable grant / invalid current target. |
| INTERNAL_ERROR (transport fallback, not ErrorCode) | 500 | 1 | Sanitized unexpected exception. |

Select the exact owner branch for each case rather than accepting any code in a
group. Do not invent HASH_MISMATCH, promotion success or consent error categories.
A missing requested root differs from a resolved saved root with missing formal
dependencies. Verify no secret, SQL text or raw provider exception in diagnostics.

### 11.3 DTO fields, Python types, limits and enums

Report records remain frozen dataclasses with slots, keyword rejection and strict
runtime types; bool is not int. Preserve the existing fields:

| Record | Exact fields/types |
| --- | --- |
| ScenarioSpec | `scenario_id: str`, `authority_clause: str`, `prerequisite_contracts: tuple[str, ...]`, `actor_ids: tuple[UUID, ...]`, `fixture_case: str`, `command_steps: tuple[str, ...]`, `fault_point: str`, `expected_outcome: str`, `expected_error_code: str | None` |
| ScenarioObservation | `scenario_id: str`, `step_index: int`, `command_identity: str`, `result_ids: tuple[UUID, ...]`, `error_code: str | None`, `state_deltas: tuple[StateDelta, ...]`, `verified_hashes: tuple[VerifiedHash, ...]`, `backend_pids: tuple[int, ...]`, `lock_events: tuple[LockEvent, ...]`, `evidence_paths: tuple[Path, ...]` |
| StateDelta | `table_name: str`, `before_count: int`, `after_count: int` |
| VerifiedHash | `record_id: UUID`, `hash_field: str`, `expected: str`, `actual: str` |
| LockEvent | `backend_pid: int`, `event: str`, `at: datetime`, `blocker_pids: tuple[int, ...]` |

Existing bounds: nonblank strings, authority clause ≤512 characters, error text
≤1000, other strings ≤128; prerequisites ≤32 items, each nonblank ≤512; actors
≤16, steps ≤32, other tuples ≤128. Counts/index nonnegative; PIDs positive;
digests exactly 64 lowercase hex; timestamps aware UTC. Evidence paths resolve
under `tests/artifacts/pr_evidence/PR2-19`. Keep observation sets small enough for
these bounds; never truncate closure to fit. Non-report product bounds stay
owned by product DTOs, not by these report ceilings.

Closed enums: scenario IDs `G0`–`G7`, `F1`, `F1b`, `F2`, `F2b`, `F3`, `F4`,
`F5`, `F5b`, `F5c`, `F6`, `F7`, `F8`, `F9`; outcomes
`PASS|DENIED|BLOCKED|ERROR`; faults
`NONE|AFTER_PARENT_INSERT|AFTER_RELATION_INSERT|AFTER_EVENT_INSERT|BEFORE_COMMIT|AFTER_COMMIT_RESPONSE|SERIALIZATION|DEADLOCK`;
lock events `TX_STARTED|WAIT_OBSERVED|LOCK_ACQUIRED|AUTH_CHECKED|COMMITTED|ROLLED_BACK`.
Multiple fault stages may use separate cases with one existing fault label.

Keep existing COMMANDS/SCENARIO_COMMANDS entries. Proposed additions are exact
implemented methods only: `SearchResultResolutionService.record_search_result_resolution/get_search_result_resolution`,
`ScientificConclusionService.create/freeze/read/record_internal_scientific_release`,
`ManuscriptFreezeService.freeze_manuscript_version/get_manuscript_version`,
`ManuscriptValidityService.get_manuscript_validity/get_manuscript_audit`,
`RevisionActionService.record_revision_action/read_revision_action/record_concern_re_review/get_concern_carry_forward`,
`InternalReviewService.record_issue_disposition/get_issue_history`,
`DecisionService.record_revision_decision/get_revision_decision`,
`ApprovalService.request_approval/decide_approval/get_request/get_decision/get_grant/get_grant_consumption/evaluate_approval_grant/revoke_approval_grant`,
`NoveltyService.record_search_coverage/record_prior_art_relation/record_novelty_assessment/read_search_coverage/read_prior_art_relation/read_novelty_assessment`.
Slash-separated method lists here expand to individual labels, not callable DSL.
Assign each only to its §2 scenarios; G7 remains novelty-only in S1.

Product inputs use exact UUID dataclasses. `FreezeManuscriptCommand` has three
UUID fields (`project_id`, `publication_id`, `manuscript_version_id`) and two
64-hex expected hashes. `RequestApprovalCommand` has UUID id/project/basis,
exact target UUID XOR, nonempty unique sorted review UUID tuple (≤100 at service),
finite purpose and paired optional rejected-request/reconsideration UUIDs.
`DecideApprovalCommand` carries UUID id/project/request, outcome
`APPROVE|APPROVE_WITH_CONDITIONS|REJECT`, rationale str, aware optional expiry
and strict bool consent condition. Conditional approval requires expiry.
`RecordInternalScientificReleaseCommand` carries UUID command_key/project/grant/result,
1–100 unique sorted checked-review UUIDs and `expected_package_manifest_hash: None`.
Do not use it for manuscript results. Prior-art kinds are
`IDENTICAL|HIGHLY_SIMILAR|PARTIAL_OVERLAP|RELATED|CONTRASTING|UNCLEAR`;
S1 novelty admits only INCONCLUSIVE. Reuse product validators and their limits.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

```sql
-- B30 upgrade/downgrade: empty. No CREATE/ALTER/DROP statement.
```

Existing catalog observations (types/constraint names are owned by migrations):

| Owner | Types and named constraints/guards to retain |
| --- | --- |
| `0042_pr2_15_minimal_decision.py` | UUID concrete Decision/basis references; `pr215_complete_decision`, `pr215_complete_conclusion`, `pr215_complete_review` constraint triggers are DEFERRABLE INITIALLY DEFERRED. Exercise missing child/rollback, never weaken them. |
| `0047_pr2_18_novelty_prior_art.py` | UUID parents/children, nonnegative integer counts, text hashes; `fk_pr218_coverage_search_plan_version_id`, `uq_pr218_coverage_execution_pair`, `uq_pr218_prior_art_input_pair`, `ck_pr218_novelty_initial_slice`. Stronger outcomes remain denied. |
| `0059_b13_grant_consumption.py` | `id/grant_id/command_key/project_id/actor_id` UUID; command VARCHAR(40), request_hash CHAR(64), hash_scheme VARCHAR(32), consumed_at TIMESTAMPTZ, result_dto_version SMALLINT and result_dto JSONB closed receipt projection. `uq_b13_consumption_grant`, `uq_b13_command_key`, `fk_b13_consumption_grant`, `fk_b13_result_conclusion`, `ck_b13_result_tuple`, `ck_b13_hash`, `ck_b13_dto`; `b13_complete_consumption` deferred constraint trigger. No generic scientific JSON owner. |

Keep concrete FK RESTRICT, existing immutable guards and sealed child sets from
0044–0056. Do not edit frozen migrations. At fault points force existing deferred
constraints and prove complete rollback through fresh connections. Privileged
corruption helpers in `b27_fixtures.py` must remain isolated from normal-role
constraint tests and restore session/trigger settings as their helper contracts require.

### 12.2 Exact lock order and transactions

The following source constants designate exact ordered table inventories, not
sets to reorder: `R` in `search_result_resolution_repository.py`,
`B04_SNAPSHOT_TABLES` in `manuscript_freeze_repository.py`,
`N` in `novelty_repository.py`, `REVISION_SNAPSHOT_TABLES` in
`revision_action_repository.py`, and `B09_SNAPSHOT_TABLES`,
`B13_SNAPSHOT_TABLES`, `B13_APPROVAL_TABLES` in `approval_repository.py`.
Expand them verbatim in SQL observation assertions. All these paths are under
`src/researchbase/persistence/`. No new lock inventory or persistence helper.

For the snapshot-consistent writes listed below use fresh READ COMMITTED UoW; acquire the designated
`LOCK TABLE <inventory in source order> IN SHARE MODE` as FIRST transactional
statement, before SET LOCAL, authorization or advisory/row locks. Initial shape
validation is in memory. The B13 consuming command's approved SERIALIZABLE
transaction is the explicit exception to READ COMMITTED, not to first SHARE.

| Exercised command | Exact subsequent order after first SHARE |
| --- | --- |
| Resolution `record` | R SHARE; SET LOCAL lock_timeout 10s and statement_timeout 30s; advisory `b01:resolution:<id>` as specified by `prepare_write`; authorize/read exact replay or validate exact result/source closure; insert; force constraints; final authority; commit. No row lock added by B30. |
| Manuscript `freeze` | B04 SHARE; same timeouts; `literature_search_plan.lock_project(project)`; Publication FOR UPDATE; ManuscriptVersion FOR UPDATE; authorization/replay/closure/expected digests; seal; deferred checks/final authority; commit. Exact GET uses separate reader, never this writer for read testing. |
| Approval request / decision | B09 SHARE; timeouts; advisory `pr216:uuid:<id>`; resolve purpose; advisory `pr216:scope:<project>:<purpose>`; exact conclusion/manuscript version FOR UPDATE; manuscript's Publication FOR SHARE if applicable; saved request FOR UPDATE for decision; authorization and saved replay detection; affected grants by UUID FOR UPDATE before protected writes; insert/check/final authorization/commit. Replay leaves writer then reopens historical reader. |
| Minimal conclusion PROCEED | B09 SHARE through the current `_record_once` protocol; timeouts; `pr215:decision:<id>` advisory; `pr216:scope:<project>:INTERNAL_SCIENTIFIC_RELEASE` advisory; exact conclusion version FOR UPDATE; project authority lock via `_authorize`; complete review/blocker/closure checks; parent and basis writes; deferred checks/final authority; commit. Do not copy its older target-first draft sequence. |
| RevisionAction record | REVISION inventory SHARE; timeouts; `pr215:revision:<id>` advisory; authority/replay; basis InternalReviewRecord FOR SHARE then ReviewIssue FOR SHARE; predecessor RevisionAction FOR UPDATE if supplied; reread successor; verify completed result/relevance/current validity; insert/force checks/final authority/commit. |
| Novelty coverage / prior-art / assessment | N SHARE; timeouts; advisory `pr218:coverage:<id>`, `pr218:prior_art:<id>` or `pr218:novelty:<id>` respectively; prior-art/novelty exact ClaimVersion FOR UPDATE; authority/replay/closure reads; novelty predecessor FOR UPDATE if nonnull then successor reread; parent/UUID-sorted children; deferred checks/final authority/commit. Coverage takes no Claim row lock. |
| Internal release first use | SERIALIZABLE; B13 snapshot SHARE first; `publications` SHARE ROW EXCLUSIVE; B13 approval inventory SHARE; timeouts; `b13:consume:<command_key>` advisory; read entitlement/receipt check; `pr216:scope:<project>:<purpose>` advisory; target version FOR UPDATE; ScientificConclusion parent FOR SHARE; ApprovalRequest FOR SHARE; ApprovalGrant FOR UPDATE; reread chain/current eligibility; receipt + CONSUMED event/terminalization; deferred checks/final clock/commit. |
| Grant evaluate/revoke maintenance | READ COMMITTED; same B13 inventories/modes/timeouts; `b13:lifecycle:<grant_id>` advisory; same scope/target/parent/request/grant order; recheck chain; only contracted terminal event/status mutation; force checks/final authority/commit. |

Additional concern-cycle commands use these existing orders, without an outer
scenario transaction:

| Command | Exact order |
| --- | --- |
| B07 revision Decision | READ COMMITTED; REVISION SHARE first; `pr215:decision:<id>` advisory; authority/replay reads; applicable InternalReviewRecord rows by UUID FOR SHARE; exact ReviewIssue FOR UPDATE; full basis/result checks; parent/basis/concern writes; force checks/final authority/commit. |
| B07 concern re-review correspondence | READ COMMITTED; REVISION SHARE first; timeouts; `b07:re-review:<action>:<review>` advisory; authority/replay; old/new review IDs sorted FOR SHARE; basis review FOR SHARE then Issue FOR SHARE; RevisionAction FOR UPDATE; reread successor; validate independent exact result review; insert link/force checks/final authority/commit. |
| B08 Issue disposition | READ COMMITTED; REVISION SHARE first; timeouts; `b08:disposition:<id>` advisory; authority/replay/Issue reads; old/re-review IDs sorted FOR SHARE; primary plus selected re-review Issue IDs sorted, primary FOR UPDATE and others FOR SHARE; validate independent disposition/result/history; event insert and Issue transition; force checks/final authority/commit. |
| B10 release reconsideration | READ COMMITTED; B09 SHARE first; timeouts; `pr215:decision:<id>` advisory from `lock_reconsideration`; project/purpose scope advisory; exact conclusion version FOR UPDATE; conclusion parent FOR SHARE; authority/replay/full rejection and evidence checks; Decision and basis inserts; force checks/final authority/commit. |

Review fixture commands keep the existing explicit write-table reservation:
`InternalReviewRepository.prepare_insert` takes `internal_review_records` ROW
EXCLUSIVE first. This owner protocol is not a snapshot SHARE capture and must
not be rewritten in B30. Initial conclusion review then reserves that table mode
again, takes `pr214:review:<derived-id>` advisory, exact target FOR UPDATE, parent
FOR UPDATE, project authority lock, validates and inserts review/Issues/events.
Claim review authorizes before that advisory and locks its exact Claim through
`literature_evidence.target`; manuscript review reserves ROW EXCLUSIVE, then
B05 SHARE, timeouts, request advisory, manuscript FOR UPDATE, project then
Publication locks. Assert these owner-specific orders in fixture observations;
do not impose a contradictory SHARE-first order on review reservations.

Every exact read/current validity/audit/receipt read and completed receipt replay uses
one read-only REPEATABLE READ UoW, entitlement checks and final advancing-clock
read authorization. Assert absence of LOCK TABLE, advisory, FOR UPDATE/FOR SHARE,
project-lock function and INSERT/UPDATE/DELETE. No “snapshot consistency” lock
on reads. Authorship `_get` currently violates this expectation and remains an
explicit owner blocker, not a B30 production fix.

### 12.3 Ordered build steps and real module paths

1. Extend `tests/integration/phase2/pr2_19_support.py`: named wrappers for the §2
   owning fixtures, finite per-row command labels, additional count inventories
   for B08/approval/grant/novelty tables, bounded typed observations. Use separate
   engines/PIDs for races. No owner production module changes.
2. Update `tests/integration/phase2/test_pr2_19_dependencies.py`: keep historical
   evidence separate; current matrix tracks every §2 subcase with exact owner,
   implemented status and blocker. Full gate still rejects missing required
   suffixes. Update its brittle plan-parsing assertions to the new contract
   deliberately; do not edit the old plan to satisfy a test.
3. Extend search/trace/integrity tests, then lineage/governance. Add the bounded
   modules in §12.4. Expose fixture builders rather than treating another test's
   PASS as the scenario oracle. Observe fresh readback after every failed command.
4. Extend `tests/unit/phase2/test_pr2_19_report_contract.py` and
   `tests/architecture/test_pr2_19_boundaries.py` for allowlists, blocker semantics,
   lock-free reads and no new state owner/production hooks. Keep all thirteen
   Phase 2 architecture obligations visible.
5. Run §12.4 focused checks; record exact commands/counts/PG version and known
   blockers, with evidence under the existing report root. Stop; full-suite
   execution belongs to the loop.

### 12.4 Test files and required cases

All paths in this table are under `tests/integration/phase2/`.

| File (existing unless marked new) | Required cases |
| --- | --- |
| `test_pr2_19_search_evidence.py` | G1 committed exact resolution bridge, independent quotation review, frozen conclusion; search alone zero evidence; fresh service read and resolution replay. |
| `test_pr2_19_citation_trace.py` | G5 all placement kinds including CAS artifact; frozen exact closure/independent expected hashes; no citation-as-support; fresh trace after freeze/restart. |
| `test_pr2_19_integrity.py` | F2b B27 missing formal dependency versus absent requested root; normal-role FK/immutable rejection separate from privileged corrupt committed state; fail-closed formal read/replay, zero mutation, nondisclosure and no locks. |
| `test_pr2_19_lineage.py` | F1 direct and snapshot support paths, CORRECTED/RETRACTED successor, B25 current manuscript projection/audit, unaffected control and retained old bytes/hashes; new admission/approval denial; no automatic finding assertion. |
| `test_pr2_19_governance.py` | F5/F5b current blocker at request and decision, complete adverse basis, stale facts, tuple/authority/independence/expiry matrix. Use committed request as predecessor. |
| `test_pr2_19_revision_cycle.py` (new) | G6 Claim/conclusion cycle, all available F6 shapes and wrong-result pairs/lineage; explicit NO_CHANGE Decision; independent re-review and B08 disposition as separate command; immutable old Issue history; manuscript suffix BLOCKED. |
| `test_pr2_19_rejection.py` (new) | F5c rejection across UUID/hash/target/approver changes and pre-created request; release-only B10 reconsideration control, full rejection coverage, lost entitlement and changed replay. |
| `test_pr2_19_approval_atomicity.py` (new) | F7 after request/child/event and decision/grant/event inserts; before commit/deferred checks; all-or-none command deltas, prior committed reviews/requests persist. |
| `test_pr2_19_grant_consumption_release.py` (new) | F9 exact internal release result/receipt, each unusable grant condition, two-command single-grant winner, same-key replay, role/credential expiry across observed wait, new blocker, failed receipt/terminalization rollback, completed replay after write authority loss with retained read role; lost read entitlement denies with zero new effect. |
| `test_pr2_19_novelty.py` (new) | G7 selected terminal execution scope, failed/zero-result coverage disclosure, six comparisons, INCONCLUSIVE exact history/replay; stronger outcomes denied, no gate/package/Issue side effect. |

Keep original PR2-19 races/replay/candidate/RAG/discussion tests runnable. Future
focused verification commands after implementation:

```sh
UV_CACHE_DIR=.uv-cache uv run ruff check .
UV_CACHE_DIR=.uv-cache uv run ruff format --check .
UV_CACHE_DIR=.uv-cache uv run pyright
UV_CACHE_DIR=.uv-cache uv run pytest tests/unit tests/architecture
# RB_TEST_ADMIN_URL must already select a disposable local PostgreSQL 18 admin.
UV_CACHE_DIR=.uv-cache uv run pytest tests/integration/phase2/test_pr2_19_*.py
```

Also run the owning B01/B04/B06–B13/B25/B27/PR2-17/PR2-18 files used by a new
fixture or assertion, explicitly listed in that implementation's evidence;
never report an unexecuted owner suite as PASS. No whole-suite command here.

### 12.5 Not in this slice

Positive strategy/discussion promotion; MANUSCRIPT_CHANGE RevisionAction and
manuscript concern-cycle completion; B14 READY transition; prepared-package,
author consent and freeze/consumption; manuscript-purpose reconsideration;
strong novelty outcomes and screening basis; automatic impact propagation;
authorship reader remediation; provider activation, venue send/ExternalEffect,
Phase 3 runtime and any production schema/code fix. Missing fixture state must
remain missing rather than being inserted with SQL to make a golden row green.

## 13. Open questions for the owner — override register

Review follow-up (2026-10-18): the reviewer permits the novelty test to cover
lock-free exact GET and command-replay equality separately while the owner decides
whether to authorize a production lock-free replay path or defer that requirement.
The §7 completed-replay requirement is unchanged; its command-replay lock assertion
is pending owner resolution and remains an explicit G7 subcase blocker. No production
fix or contract relaxation is inferred. Owner-availability flags in the dependency
inventory are informational, never proof that a subcase ran or passed. “Start here”
step 2 and §§11.1/12.3 authorize reconciliation of that inventory; acceptance still
requires actual test evidence.


The adopted proposal is S1 with all §2 blockers retained. Owner approval may
change test ordering/scope, but requires corresponding body/matrix edits before
implementation authorization. This draft requests no architecture exception,
new schema or change to frozen material. No approval is inferred from code presence.

## 14. Documentation verification note

Documentation-only verification results are recorded below after focused runs.
No full-suite, PR2-19 gate or Phase 2 exit success is implied.

Focused runs on 2026-10-18, before implementation:

| Exact command | Observed result |
| --- | --- |
| `UV_CACHE_DIR=.uv-cache uv run ruff check .` | Exit 2 before check: uncached dependency download/DNS failure. |
| `UV_CACHE_DIR=.uv-cache uv run ruff format --check .` | Exit 2 before check: uncached dependency download/DNS failure. |
| `UV_CACHE_DIR=.uv-cache uv run pyright` | Exit 2 before check: uncached dependency download/DNS failure. |
| `UV_CACHE_DIR=.uv-cache uv run pytest tests/unit tests/architecture` | Exit 2 during environment setup; no test counts. |
| `DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase UV_CACHE_DIR=.uv-cache uv run pytest tests/integration/phase2/test_pr2_19_search_evidence.py tests/integration/phase2/test_pr2_19_citation_trace.py tests/integration/phase2/test_pr2_19_integrity.py tests/integration/phase2/test_pr2_19_dependencies.py` | Exit 2 during Hatchling dependency resolution/DNS; no test counts. |
| `/Users/fengwang/Documents/ResearchBaseProject/.venv/bin/ruff check .` | PASS, all checks passed. Existing repository environment used read-only. |
| `/Users/fengwang/Documents/ResearchBaseProject/.venv/bin/ruff format --check .` | PASS, 639 files already formatted. |
| `/Users/fengwang/Documents/ResearchBaseProject/.venv/bin/pyright --pythonpath /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python` | Exit 1, 1,145 errors and 2 warnings with lane `.venv` dependency discovery; not PASS. |
| `/Users/fengwang/Documents/ResearchBaseProject/.venv/bin/pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject` | PASS, 0 errors, 0 warnings, 0 informations with existing installed environment. |
| `PYTHONPATH=src /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python -m pytest tests/unit tests/architecture` | 5,104 passed, 5 failed, 12 errors, 8 warnings. Four failures are Runner Unix-socket bind PermissionError; static acceptance also fails. Twelve PR2-19 architecture setup errors require unset RB_TEST_ADMIN_URL. This run is not PASS. |
| `DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase PYTHONPATH=src /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python -m pytest tests/integration/phase2/test_pr2_19_search_evidence.py tests/integration/phase2/test_pr2_19_citation_trace.py tests/integration/phase2/test_pr2_19_integrity.py tests/integration/phase2/test_pr2_19_dependencies.py --tb=short` | 1 passed, 16 setup errors: explicitly selected disposable RB_TEST_ADMIN_URL is missing; DATABASE_URL does not satisfy that policy. PostgreSQL assertions did not execute. |
| `PYTHONPATH=src /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python -m pytest tests/unit/phase2/test_pr2_19_report_contract.py tests/integration/phase2/test_pr2_19_dependencies.py` | PASS, 49 passed. |
| `git diff --check` | Exit 0. New draft also checked separately for whitespace. |

The `psql -d postgres -Atc 'SELECT version()'` probe exited 2: local socket access
was denied (Operation not permitted); no PostgreSQL version was observed. Do not
claim a PostgreSQL 18 result. No other owning PostgreSQL suites or full suite were
run; the loop supplies subsequent evidence. A read-only Python 3.12 AST check
verified all 32 proposed command labels against current Application classes and
sections 1–14/status. Only this draft is an authored change.
