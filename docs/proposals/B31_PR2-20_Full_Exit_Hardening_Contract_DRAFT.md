# PR2-20 Full Exit Hardening (B31) Contract — DRAFT

**Status: APPROVED by owner 2026-10-20 — first slice authorized for implementation**

## Start here (for the implementer)

This draft specifies **B31**, the completion contract for **PR2-20 Full Exit Hardening**
from [PR2-20_Hardening_Plan_DRAFT.md](PR2-20_Hardening_Plan_DRAFT.md) and
[phase2_exit_report.md](../phase2/phase2_exit_report.md). B30 S1 and S2 are implemented;
mandatory owning slices through migration `0068_b21_unresolved_capture` are in the tree.
Owner decisions on **2026-10-19** are binding: **B28** real PaperQA2 is **DEFERRED**
(record as a known gap; `FakeScientificRAGCapability` stays the gate); **B24** = **no
novelty gate** (novelty never gates approval, `READY` transition, or package freeze);
**B29** = **no partial index** (`ix_pr220_issue_open_blocking_review` is rejected; no
migration). **B02**, **B03**, and **H2** (plus **B30-S3** once B02/B03 land) are being
implemented in parallel and are listed as pending inputs in §2.

When separately authorized, implement B31 in four smallest ordered slices (§2.3, §12.3):

1. **B31-S1 — Real Adapter Destination Security & B28 Deferral Disposition**:
   harden `src/researchbase/adapters/literature_http.py::get_json` to reject private,
   loopback, link-local/metadata, multicast, unspecified, and reserved IP literals and
   DNS answers (and pin the resolved IP peer per connection with redirects disabled)
   before socket connect, raising `HttpTransportFailure(DeliveryCertainty.NOT_SENT)`;
   turn `tests/integration/phase2/test_pr2_20_security.py` from a P1 witness into a
   passing regression; record **B28 = DEFERRED** in `tests/contracts/pr2_20_reports.py`.
2. **B31-S2 — Full Migration Chain (`0001`..head) Clean/Upgrade/Hash Parity**:
   extend `tests/integration/phase2/test_pr2_20_migrations.py` and
   `tests/contracts/pr2_20_reports.py` across the complete `0001`..`0068` chain
   (reconciling the `0060`–`0064` table gap in `migration_inventory_phase2.md`) and
   verify populated upgrade, reconnect, and exact `content_hash` parity for revision,
   approval, authorship, novelty, manuscript freeze/review, `READY`, and package freeze
   checkpoints. Keep **B29** closed with zero PR2-20 DDL.
3. **B31-S3 — Extended Governance, Revision/Issue, Approval, Package & Novelty Benchmarks and Races**:
   extend `tests/integration/phase2/pr2_20_scaled.py`,
   `tests/integration/phase2/test_pr2_20_governance_races.py`,
   `tests/integration/phase2/test_pr2_20_novelty.py`, and
   `tests/e2e/test_pr2_20_benchmark.py` (at `concurrency in (1, 4)`) to cover B04
   superseded manuscript history, B06/B07/B08 revision/concern/disposition, B09–B14
   approval/consumption/`READY`, B15–B17 package/consent/withdrawal/freeze, and
   B18/B19/B21/B22 novelty/prior-art chains under **B24 = no novelty gate**.
4. **B31-S4 — Full E2E Inventory & Phase 2 Exit Artifacts**:
   once pending parallel inputs (**B02**, **B03**, **H2**, **B30-S3**) complete, wire
   `scripts/pr2_20_verify.py` and `tests/contracts/pr2_20_reports.py` to attach
   `OWNING_ACCEPTANCE` evidence for 18 exit rows and owner-approved `DEFERRED`
   disposition for Row 6 (`PaperQA2 Adapter`), then regenerate all six deliverables in
   `docs/phase2/`.

Skip on first read: §1 (authority table) and §10 (glossary).

**Five rules that fail review if violated:**

1. **DO NOT ADD SCHEMA.** B31 adds zero Alembic migrations, zero canonical tables, and
   zero indexes (**B29** partial index is rejected).
2. **Snapshots and locks match owner protocols.** Snapshot-consistent writes in
   `decision_repository.py`, `novelty_repository.py`, `revision_action_repository.py`,
   `approval_repository.py`, `publication_repository.py`,
   `prepared_submission_repository.py`, `manuscript_freeze_repository.py`, and
   `search_result_resolution_repository.py` execute `LOCK TABLE <inventory> IN SHARE MODE`
   as the **FIRST** statement in their transaction (§12.2). Read paths and completed
   receipt replays use one `REPEATABLE READ, READ ONLY` transaction and never take
   table, advisory, or row locks.
3. **B24 = no novelty gate.** Novelty assessments (`INCONCLUSIVE` or
   `CLOSE_PRIOR_ART_FOUND`) never block or gate `request_approval`, `decide_approval`,
   `transition_publication_ready`, `prepare_submission`, or `freeze_prepared_submission`.
4. **B28 = DEFERRED known gap.** Never install `paper-qa`/`paperqa` in `uv.lock` or
   enable network/LLM RAG calls; `FakeScientificRAGCapability` remains the deterministic
   gate and `PaperQA2 Adapter` is recorded as an owner-approved `DEFERRED` gap.
5. **Fail-closed exit evidence.** Never convert `BLOCKED`, `SKIPPED`, missing
   `RB_TEST_ADMIN_URL`, or pending parallel slices (**B02**, **B03**, **H2**) into `PASS`.

---

## 1. Purpose, authority and inspected baseline

Read `AGENTS.md` first, then the authoritative architecture documents in order:

| Authority | Binding requirement for B31 |
| --- | --- |
| `docs/architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md` (§§3–9, 13–14) | Canonical scientific invariants, synchronous DB UoW, deterministic facts over authority/review, no ORM leak. |
| `docs/architecture/02_Final_Architecture_Correction_Addendum_v1.0.md` | Immutable version history; corrections by new records/provenance, never destructive mutation. |
| `docs/architecture/03_Global_Schema_and_Contract_Registry_v1.0.md` | Frozen canonical entities; complexity budget (`DO NOT ADD SCHEMA`). |
| `docs/architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md` | Phase 1 contracts preserved; Phase 2 exit requires explicit evidence before Phase 3 GO. |
| `docs/architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md` (§§41–45, PR2-20) | Six exit deliverables, 19 literal exit criteria, 13 mandatory architecture boundary tests, performance/security/migration verification. |
| `docs/architecture/09_TDG1_Phase1_Technology_Decision_Gate_v1.0.md` & `docs/harness/09_Harness_Integration_Specification_v1.0.md` | PostgreSQL 18.x synchronous SQLAlchemy/Alembic; `uv.lock` canonical; `harness.lock.yaml` reference-only entries are not executable pins. |
| `docs/architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md` through `19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md` | `sha256-cjson-v1` payloads, finite governance tuples, atomic grant consumption (`0059`/`0064`/`0067`), post-wait DB-clock checks, lock-free `REPEATABLE READ` reads. |
| `docs/proposals/PR2-20_Hardening_Plan_DRAFT.md` & `docs/phase2/phase2_exit_report.md` | Inspected PR2-20 baseline, evidence schemas (`pr2_20_evidence.py`), and current `BLOCKED` exit report. |

### 1.1 Inspected repository baseline

- **Implemented PR2-20 S1 foundation**: `tests/contracts/pr2_20_evidence.py`,
  `tests/contracts/pr2_20_reports.py`, `scripts/pr2_20_verify.py`,
  `tests/integration/phase2/pr2_20_support.py`,
  `tests/integration/phase2/pr2_20_scaled.py`,
  `tests/integration/phase2/b18_novelty_support.py`,
  `tests/integration/phase2/b29_measurement.py`,
  `tests/unit/phase2/test_pr2_20_evidence.py`, `tests/unit/phase2/test_pr2_20_exit_report.py`, `tests/unit/phase2/test_pr2_20_inventory.py`,
  `tests/architecture/test_pr2_20_boundaries.py`,
  `tests/integration/phase2/test_pr2_20_catalog_plans.py`, `tests/integration/phase2/test_pr2_20_governance_races.py`, `tests/integration/phase2/test_pr2_20_migrations.py`, `tests/integration/phase2/test_pr2_20_novelty.py`, `tests/integration/phase2/test_pr2_20_security.py`,
  and `tests/e2e/test_pr2_20_benchmark.py`.
- **Implemented Phase 2 migration chain**: 70 migration scripts from
  `0001_empty_bootstrap.py` through `0068_b21_unresolved_capture.py` (including `0021a`
  and `0023a`).
- **Owner decisions recorded on 2026-10-19**:
  1. **B28 (`docs/proposals/B28_PaperQA2_Intake_Assessment_DRAFT.md`)**: real PaperQA2
     intake is **DEFERRED** (`REJECT FOR PHASE 2 / DEFER TO PHASE 3+`). Record as a
     known gap in the exit artifacts; `FakeScientificRAGCapability` stays the gate.
  2. **B24**: **no novelty gate**. Novelty outcomes never gate approval, `READY`
     transition, or package freeze.
  3. **B29 (`docs/phase2/B29-measurement-evidence.md`)**: **no partial index**.
     Candidate `ix_pr220_issue_open_blocking_review` failed the p95 improvement gate
     (`39.217 ms` vs `37.026 ms` baseline at 10,000 issues) and is rejected; no
     migration is permitted.

---

## 2. Scope, dependency boundaries and non-goals

### 2.1 Exact delta from `PR2-20_Hardening_Plan_DRAFT.md` and `docs/phase2/phase2_exit_report.md`

| Area in `PR2-20_Hardening_Plan_DRAFT.md` / `phase2_exit_report.md` | Already in tree (PR2-20 S1 + B17/B18/B29 hooks) | Remaining for B31 |
| --- | --- | --- |
| **Adapter security & B28 disposition** (`adapter_compatibility_report.md`, `reference_system_inventory.md`) | `literature_http.py` enforces `_NoRedirect`, 4 MiB body cap, wall-clock timeout, and credential/query redaction. `test_pr2_20_security.py` witnesses missing private-IP denial as an open **P1 MAJOR**. | Close the P1 MAJOR in `src/researchbase/adapters/literature_http.py` by denying non-public IP literals and DNS answers (and pinning the validated IP per connection) before dispatch. Record **B28 = DEFERRED** known gap so `PaperQA2 Adapter` is an approved deferral while `FakeScientificRAGCapability` remains the gate. |
| **Clean/upgrade/hash parity** (`test_pr2_20_migrations.py`, `migration_inventory_phase2.md`) | Tests empty/noop/round-trip (`0041`..head) and populated checkpoints `0018`, `0020`, `0022`, `0028`, `0031`, `0033`→`0037`→`0040`→`0042`→head. `migration_inventory_phase2.md` omits `0060`–`0064` in its narrative table. | Extend populated upgrade, reconnect, and exact `content_hash`/edge parity across post-`0042` checkpoints `0044`–`0068` (RevisionAction, Approval, Authorship, Novelty, B04 manuscript freeze, B05 manuscript review, B01 resolution, B06–B08 concern/disposition, B09–B13 approval/consumption, B14a/B14r/B14 `READY`, B15–B17 package/consent/freeze, B19/B21/B22 novelty). Reconcile `migration_inventory_phase2.md` to list all 70 revisions (`0001`..`0068`). |
| **Benchmarks & multi-worker races** (`test_pr2_20_benchmark.py`, `test_pr2_20_governance_races.py`, `pr2_20_scaled.py`) | Benchmarks source lookup, manuscript trace (`25`/`250`/`2500`), PR2-15 conclusion Decision (`1`/`4` workers), B18 novelty (`1`/`4` workers), B29 clone probe, and 1-worker B17 package freeze. `large_host_blockers` still claims superseded manuscript history is unavailable. | Remove obsolete B04 blocker in `large_host_blockers` and benchmark superseded manuscript trace; add benchmark & `1`/`4`-worker race profiles for B06/B07/B08 revision/issue disposition, B09–B14 approval/grant consumption/`READY`, B15–B17 authorship/package/consent/withdrawal/freeze (including 4-worker freeze/withdrawal/replay races), and B19/B21/B22 novelty (`CLOSE_PRIOR_ART_FOUND`, v2 unresolved capture, `PriorArtRelation` correction chains and `select_prior_art_relation`) with **B24** non-gating assertions. |
| **Full E2E inventory & 6 exit deliverables** (`pr2_20_reports.py`, `scripts/pr2_20_verify.py`, `docs/phase2/*.md`) | `exit_rows()` hardcodes all 19 literal rows to `status="BLOCKED"`. `literature_trace_demo.md` and `publication_trace_demo.md` mark post-PR2-15 stages as unavailable. | Update `pr2_20_reports.py` and `scripts/pr2_20_verify.py` so `exit_rows()` loads verified `OWNING_ACCEPTANCE` evidence for rows 1–5 and 7–19 and owner-approved `DEFERRED` disposition for row 6 (`PaperQA2 Adapter`); update `literature_trace_demo.md` and `publication_trace_demo.md` to walk the complete implemented trace through `READY` and `FROZEN` package; regenerate all 6 reports in `docs/phase2/` once pending parallel inputs land. |

### 2.2 Pending parallel inputs (do not re-implement in B31)

`B02`, `B03`, and `H2` (followed by `B30-S3`) are being implemented in parallel. B31
lists their affected exit rows and subcases as **pending inputs** and consumes their
owning tests/evidence once merged:

| Parallel item | Owning scope | Affected PR2-20 exit rows / PR2-19 inventory items | Status in B31 until parallel item lands |
| --- | --- | --- | --- |
| **B02** ([B02_Strategy_Candidate_Promotion_Contract_DRAFT.md](B02_Strategy_Candidate_Promotion_Contract_DRAFT.md)) | Strategy candidate promotion (pending B02; no existing promotion command is asserted) | Exit row 7 (`Native Research Strategy`); PR2-19 row `G2`. | Pending input; remains `BLOCKED` in exit roll-up until B02 acceptance evidence is attached. |
| **B03** ([B03_Discussion_Candidate_Promotion_Contract_DRAFT.md](B03_Discussion_Candidate_Promotion_Contract_DRAFT.md)) | `DiscussionService.request_promotion` (question, hypothesis, and literature search plan candidates) | Exit row 10 (`Scientific Discussion Layer`); PR2-19 row `G4`. | Pending input; remains `BLOCKED` in exit roll-up until B03 acceptance evidence is attached. |
| **H2** ([H2_Phase2_Hardening_Followups_Contract_DRAFT.md](H2_Phase2_Hardening_Followups_Contract_DRAFT.md)) | Lock-free novelty command replay (`NoveltyService._once`), B24 non-gating regression (`test_b24_novelty_non_gating.py` (new, proposed)), B25/B27 audit & corruption closure | Exit rows 18 (`Submission & Authorship`) and 19 (`Novelty & Prior-Art` / `PR2-19` `G7` lock-free novelty replay subcase). | Pending input; B31 benchmarks `read_*` (already lock-free) and `record_*` replay, and consumes H2's lock-free command replay and the proposed B24 non-gating regression once H2 lands. |
| **B30-S3** (post-B02/B03 PR2-19 slice) | PR2-19 E2E integration of B02 (`G2`), B03 (`G4`), and remaining PR2-19 subcases | Exit row 19 (`PR2-19` full golden/failure gate in `test_pr2_19_dependencies.py`). | Pending input; `require_full_gate` stays fail-closed until all mandatory PR2-19 subcases pass or carry explicit owner dispositions. |

### 2.3 Smallest ordered implementation slices

1. **Slice B31-S1 (Transport Destination Security & B28 Disposition)**:
   self-contained in `src/researchbase/adapters/literature_http.py`,
   `tests/contracts/pr2_20_evidence.py`, `tests/contracts/pr2_20_reports.py`,
   `tests/unit/phase2/test_pr2_20_evidence.py`, `tests/unit/phase2/test_pr2_20_exit_report.py`, `tests/unit/phase2/test_pr2_20_inventory.py`, and
   `tests/integration/phase2/test_pr2_20_security.py`. Independent of B02/B03/H2.
2. **Slice B31-S2 (Full Migration Chain `0001`..`0068` Clean/Upgrade/Hash Parity)**:
   self-contained in `tests/integration/phase2/test_pr2_20_migrations.py`,
   `tests/integration/phase2/test_pr2_20_catalog_plans.py`, and
   `tests/contracts/pr2_20_reports.py` (`migration_inventory_phase2.md`). Independent
   of B02/B03/H2 (which are DDL-free).
3. **Slice B31-S3 (Revision/Issue/Approval/Package/Novelty Benchmarks & Multi-Worker Races)**:
   self-contained in `tests/integration/phase2/pr2_20_scaled.py`,
   `tests/integration/phase2/test_pr2_20_governance_races.py`,
   `tests/integration/phase2/test_pr2_20_novelty.py`, and
   `tests/e2e/test_pr2_20_benchmark.py`. Uses existing B04–B19/B21/B22 services; hooks
   into H2's lock-free novelty command replay once H2 merges.
4. **Slice B31-S4 (Full E2E Inventory & Phase 2 Exit Artifacts)**:
   runs after B31-S1..S3 and parallel inputs (B02, B03, H2, B30-S3) complete; updates
   `scripts/pr2_20_verify.py`, `tests/contracts/pr2_20_reports.py`, and regenerates all
   six `docs/phase2/*.md` exit artifacts plus `docs/phase2/pr2_20_verification.md`.

### 2.4 Non-goals

- No new canonical schema, table, column, trigger, or index (`DO NOT ADD SCHEMA`;
  **B29** partial index is rejected).
- No real `paper-qa`/`paperqa` dependency or external LLM runtime (**B28 = DEFERRED**).
- No novelty gate on approval, `READY` transition, or package freeze (**B24 = no novelty gate**).
- No live external HTTP calls in automated tests; no external venue submission,
  `SubmissionVersion`, or `ExternalEffect`; no Phase 3 runtime.

---

## 3. Invariants and conservative judgments

1. **Deterministic facts outrank permission and review**: `ApprovalGrant` issuance or
   consumption never repairs a `RETRACTED` or `CORRECTED` upstream source, an
   `OPEN`/`BLOCKING` `ReviewIssue`, or a missing/withdrawn `AuthorConsent`.
2. **B24 non-gating novelty invariant**: `NoveltyAssessment` (`INCONCLUSIVE` or
   `CLOSE_PRIOR_ART_FOUND`), `PriorArtRelation`, and `SearchCoverage` are epistemic
   assessments on a `ClaimVersion`, never governance prerequisites for
   `INTERNAL_SCIENTIFIC_RELEASE`, `READY_FOR_SUBMISSION`, or `PREPARE_SUBMISSION`.
3. **B28 PaperQA2 deferral invariant**: `FakeScientificRAGCapability` is the sole
   active `ScientificRAGCapability` implementation in Phase 2. `paperqa2` is recorded
   with `mode="DEFERRED"` and `status="DEFERRED"` under explicit owner disposition
   `docs/proposals/B28_PaperQA2_Intake_Assessment_DRAFT.md`, never laundered as an
   enabled provider `PASS`.
4. **B29 zero-index invariant**: `review_issues` retains only its accepted constraints
   and `ix_pr214_issue_review_severity`; `ix_pr220_issue_open_blocking_review` must not
   exist in any migration or fixture database outside `b29_measurement.py`'s disposable
   clone test.
5. **Outbound transport SSRF/rebinding invariant**: `literature_http.get_json` must
   parse the URL, allow only `http` and `https` schemes with a non-empty hostname and no
   embedded credentials, resolve all A/AAAA records, reject any literal or resolved IP
   address that is not globally routable (or is loopback, private, link-local, multicast,
   unspecified, or reserved), and connect directly to the validated IP peer (preserving
   `Host` header and TLS SNI for `https`) with redirects disabled.
   Any rejected destination fails closed with
   `HttpTransportFailure(DeliveryCertainty.NOT_SENT)` before any connection to the destination.
6. **Lock-free reads**: every formal read query and completed grant-consumption replay
   executes inside one `REPEATABLE READ, READ ONLY` transaction and takes zero
   `LOCK TABLE`, `pg_advisory_xact_lock`, `FOR UPDATE`, or `FOR SHARE` locks.

---

## 4. Proposed commands, DTOs and historical readback

B31 introduces **no new public Application command, route, or CLI command**.

- Benchmarks, race tests, migration checkpoints, and trace demos invoke the existing
  closed Application services and DTOs listed in §11.3 (`RevisionActionService`,
  `InternalReviewService`, `DecisionService`, `ApprovalService`,
  `ManuscriptFreezeService`, `PublicationService`, `AuthorshipService`,
  `PreparedSubmissionService`, `NoveltyService`, `ManuscriptScientificTraceService`,
  `ManuscriptValidityService`, `SourceIdentityService`, `SearchResultResolutionService`).
- Outbound HTTP adapter hardening in `src/researchbase/adapters/literature_http.py`
  retains the exact signature
  `get_json(url: str, headers: dict[str, str], timeout: float) -> HttpObservation` and
  existing exception hierarchy (`HttpTransportFailure`, `HttpTimeoutFailure`).
- Engineering evidence schemas in `tests/contracts/pr2_20_evidence.py`
  (`QueryPlanEvidence`, `AdapterInventoryEntry`, `MigrationEvidence`,
  `ExitCriterionEvidence`, `BenchmarkProfile`) retain their existing shared `Result`
  status type and gain only the narrow B28 validation/report behavior (§11.3):
  - `AdapterInventoryEntry.status` (inherited `Result`),
    where `status == "DEFERRED"` is valid only when `mode == "DEFERRED"`, `reason` is
    non-empty, and `unresolved_items` is non-empty.
  - `ExitCriterionEvidence.status` (inherited `Result`),
    where `status == "DEFERRED"` is valid only for `criterion == "PaperQA2 Adapter"`
    with a non-empty `reason` and at least one `disposition_refs` entry pointing to the
    owner deferral record (`docs/proposals/B28_PaperQA2_Intake_Assessment_DRAFT.md`).

---

## 5. Persistence/schema proposal — no migration

**DO NOT ADD SCHEMA.**

- **Migrations added**: `0`. Current head remains `0068_b21_unresolved_capture` (70
  revision files in `migrations/versions/`).
- **Tables / columns / triggers / indexes added**: `0`.
- **B29 decision**: `docs/phase2/B29-measurement-evidence.md` proved that the candidate
  partial index `ix_pr220_issue_open_blocking_review` on `review_issues (review_record_id)
  WHERE severity = 'BLOCKING' AND status = 'OPEN'` did not meet the required `>= 20%`
  and `>= 5 ms` p95 improvement threshold (`+5.9%` / `+2.191 ms` slower at 10,000
  issues). The index is rejected and closed.
- **Canonical hash schemes**: unchanged (`sha256-cjson-v1` across Phase 2 domain
  hashes; `pr2-20-evidence-v1` for non-domain engineering evidence files under
  `pr_evidence/pr2-20/<subject_digest>/`).

---

## 6. Error contract — existing categories only

B31 adds **zero** `ErrorCode` enum members and **zero** HTTP status or CLI exit-code
changes.

- All 57 existing `ErrorCode` members in `src/researchbase/foundation/errors.py`,
  `src/researchbase/api/errors.py:_STATUS`, and
  `src/researchbase/cli/errors.py:CLI_EXIT_CODES` (plus the `INTERNAL_ERROR` `500`/`1`
  fallback) are pinned in §11.2.
- `tests/unit/phase2/test_pr2_20_evidence.py::test_all_pinned_error_mappings_and_source_additions`
  must assert that §11.2 of this contract (57 `ErrorCode` rows) matches
  `set(ErrorCode)`, `_STATUS`, and `CLI_EXIT_CODES` 1-for-1, while preserving the 50+7
  split check against `PR2-20_Hardening_Plan_DRAFT.md`.
- In `src/researchbase/adapters/literature_http.py`, pre-dispatch destination denial
  (disallowed scheme, userinfo in URL, unresolvable host, or any non-global/private/
  loopback/link-local/metadata/multicast/unspecified/reserved IP in literal host or DNS
  resolution) raises `HttpTransportFailure(DeliveryCertainty.NOT_SENT)` without leaking
  the raw URL, query string, or headers in exception messages.

---

## 7. Transactions, concurrency and failure recovery

1. **One command = one database transaction**: every benchmark sample, race worker, and
   migration checkpoint step invokes Application services with its own `UnitOfWork`
   factory; tests never wrap multiple commands in an outer shared transaction.
2. **Snapshot-consistent writes (`READ COMMITTED`)**: commands in
   `decision_repository.py`, `novelty_repository.py`, `revision_action_repository.py`,
   `approval_repository.py`, `publication_repository.py`,
   `prepared_submission_repository.py`, `manuscript_freeze_repository.py`, and
   `search_result_resolution_repository.py` execute `LOCK TABLE <inventory> IN SHARE MODE`
   as the **first transactional statement** before `SET LOCAL lock_timeout = '10s'`,
   `SET LOCAL statement_timeout = '30s'`, advisory locks, or `FOR UPDATE`/`FOR SHARE`
   row locks (§12.2).
3. **Grant-consuming writes (`SERIALIZABLE`)**: `record_internal_scientific_release`,
   `transition_publication_ready`, and `freeze_prepared_submission` run in
   `SERIALIZABLE` isolation (`configure_grant_transaction(consuming=True)` /
   `prepare_freeze_write()`), acquire their `LOCK TABLE ... IN SHARE MODE` and
   `SHARE ROW EXCLUSIVE` table locks first, coordinate on
   `b13:consume:<command_key>` and `pr216:scope:<project>:<purpose>`, lock target and
   grant rows in deterministic order, force `SET CONSTRAINTS ALL IMMEDIATE`, and
   re-verify authority and grant `valid_until` against advancing `clock_timestamp()`
   immediately before commit.
4. **Bounded SQLSTATE retry**: only SQLSTATE `40001` and `40P01` normalized by the owning UoW retry up to 3 total
   fresh-UoW attempts; business denials, lock timeouts (`55P03`), statement timeouts
   (`57014`), and constraint violations never retry.
5. **Lock-free reads (`REPEATABLE READ, READ ONLY`)**: all read queries and completed
   consumption replays execute in a single read-only `REPEATABLE READ` snapshot with
   zero table, advisory, or row locks.

---

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

All test additions and extensions are specified in §12.4 and are **not implemented in
this documentation-only turn**:

- **B31-S1**: unit and integration security tests in
  `tests/unit/phase2/test_pr2_20_evidence.py`,
  `tests/unit/phase2/test_pr2_20_exit_report.py`,
  `tests/unit/phase2/test_pr2_20_inventory.py`, and
  `tests/integration/phase2/test_pr2_20_security.py` covering literal and DNS-resolved
  IPv4/IPv6 loopback (`127.0.0.1`, `::1`), RFC 1918 (`10.0.0.1`, `172.16.0.1`,
  `192.168.1.1`), CGNAT (`100.64.0.1`), link-local/cloud metadata (`169.254.169.254`,
  `fe80::1`), unique-local (`fc00::1`, `fd00::1`), IPv4-mapped IPv6
  (`::ffff:127.0.0.1`, `::ffff:169.254.169.254`), multicast/unspecified (`0.0.0.0`,
  `::`), mixed public+private DNS answers, DNS rebinding (pinned IP peer verification),
  and B28 `DEFERRED` report validation.
- **B31-S2**: migration checkpoint tests in
  `tests/integration/phase2/test_pr2_20_migrations.py` covering populated upgrades from
  `0044`, `0045`, `0046`, `0047`, `0048`, `0049`, `0050`, `0053`, `0059`, `0064`, and
  `0067` to `0068_b21_unresolved_capture`, verifying byte-identical manifests,
  reconnect readback, and `content_hash` parity.
- **B31-S3**: extended multi-worker races in
  `tests/integration/phase2/test_pr2_20_governance_races.py`, extended novelty parity
  in `tests/integration/phase2/test_pr2_20_novelty.py`, and `1`/`4`-worker benchmark
  profiles in `tests/e2e/test_pr2_20_benchmark.py` (revision/disposition, approval/
  consumption/`READY`, package/consent/withdrawal/freeze, superseded manuscript trace,
  and B19/B21/B22 novelty with B24 non-gating assertions).
- **B31-S4**: exit report and verifier tests in
  `tests/unit/phase2/test_pr2_20_exit_report.py` and
  `tests/architecture/test_pr2_20_boundaries.py`.

---

## 9. Acceptance criteria and evidence boundary

1. **Documentation turn boundary**: this turn authors only
   `docs/proposals/B31_PR2-20_Full_Exit_Hardening_Contract_DRAFT.md`. No code, test, or
   report in `docs/phase2/` is modified until the owner approves this contract.
2. **Slice acceptance (`B31-S1`..`B31-S3`)**: each slice is verified by static checks
   (`ruff check`, `ruff format --check`, `pyright`), `tests/unit` +
   `tests/architecture`, and the slice's focused PostgreSQL 18 integration/benchmark
   files with `0` failed, `0` errors, and `0` skipped.
3. **Full Phase 2 Exit (`B31-S4`)**: `validate_exit(rows, findings)` returns `"PASS"`
   only when:
   - `findings == ()` (including closure of the `literature_http.py` P1 MAJOR in
     `B31-S1`);
   - all 13 mandatory architecture tests in `ARCHITECTURE_NODES` pass (`0` skipped);
   - Row 6 (`PaperQA2 Adapter`) has `status == "DEFERRED"` backed by owner disposition
     `docs/proposals/B28_PaperQA2_Intake_Assessment_DRAFT.md` and `paper-qa`/`paperqa`
     remains absent from `uv.lock`;
   - all other 18 literal rows in `EXIT_CRITERIA` (including pending parallel inputs
     **B02** on Row 7, **B03** on Row 10, **H2** on Rows 18–19, and **B30-S3** on Row 19)
     have `status == "PASS"` with `verified_acceptance(row, ROOT) is True` (`passed > 0`,
     `failed == 0`, `errors == 0`, `skipped == 0`, matching `subject_revision` and
     `dirty_diff_sha256`);
   - all six deliverables under `docs/phase2/` and `docs/phase2/pr2_20_verification.md`
     are regenerated and verified by `scripts/pr2_20_verify.py`.
   - Even after `validate_exit == "PASS"`, the final recommendation in
     `docs/phase2/phase2_exit_report.md` remains: **STOP; wait for explicit Phase 3 GO**.

---

## 10. Glossary

| Term | Definition in B31 |
| --- | --- |
| **B24 (No novelty gate)** | Owner decision (2026-10-19) that novelty outcomes (`INCONCLUSIVE`, `CLOSE_PRIOR_ART_FOUND`) never gate approval requests, approval decisions, `READY` transitions, or package freeze. |
| **B28 (PaperQA2 deferred)** | Owner decision (2026-10-19) deferring real PaperQA2 intake to Phase 3+; recorded as an explicit `DEFERRED` known gap while `FakeScientificRAGCapability` stays the gate. |
| **B29 (No partial index)** | Owner decision (2026-10-19) rejecting `ix_pr220_issue_open_blocking_review` after `docs/phase2/B29-measurement-evidence.md`; zero PR2-20 DDL. |
| **Pending parallel inputs** | `B02` (strategy candidate promotion), `B03` (discussion candidate promotion), `H2` (novelty lock-free command replay, B24 non-gating test, B25/B27 closure), and `B30-S3` (remaining PR2-19 rows). |
| **Pinned IP peer** | Connecting the HTTP/HTTPS socket directly to the pre-validated IP address returned by DNS resolution so DNS rebinding between check and `connect()` cannot reach a private destination. |
| **Subject digest** | `sha256-cjson-v1` digest of `{"dirty_diff_sha256": ..., "schema_version": 1, "subject_revision": ...}` scoping all machine evidence under `pr_evidence/pr2-20/<subject_digest>/`. |

---

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

1. **Four ordered slices (`B31-S1`..`B31-S4`)**: B31 is partitioned so `B31-S1`
   (transport security + B28 deferral), `B31-S2` (full migration chain `0001`..`0068`),
   and `B31-S3` (benchmarks and multi-worker races for implemented slices) can execute
   immediately without waiting for `B02`/`B03`/`H2`, while `B31-S4` attaches the final
   acceptance evidence after `B02`/`B03`/`H2`/`B30-S3` merge.
2. **Owner decision B28 (`PaperQA2 Adapter`)**: `validate_exit` and
   `verified_acceptance` in `tests/contracts/pr2_20_reports.py` permit
   `status="DEFERRED"` exclusively for `criterion == "PaperQA2 Adapter"` when
   `disposition_refs` includes `docs/proposals/B28_PaperQA2_Intake_Assessment_DRAFT.md`
   and `adapter_inventory()` confirms `paperqa2` has `mode == "DEFERRED"`,
   `package_version is None`, and `paper-qa`/`paperqa` absent from `uv.lock`. Every
   other exit row still requires `status == "PASS"`.
3. **Owner decision B24 (`No novelty gate`)**: `B31-S3` benchmarks and race suites
   verify that recording `INCONCLUSIVE` or `CLOSE_PRIOR_ART_FOUND` on a placed
   `ClaimVersion` does not alter `ApprovalGrant` eligibility, `READY` transition, or
   `freeze_prepared_submission`.
4. **Owner decision B29 (`No partial index`)**: `B31-S2` and `B31-S3` retain
   `b29_measurement.py` as an isolated clone-only regression check and assert
   `ix_pr220_issue_open_blocking_review` is absent from the canonical catalog.
5. **Transport destination validation in `literature_http.py`**: `get_json` validates
   the target URL and every resolved IP address before opening a socket, rejects
   non-global, loopback, private, link-local, multicast, unspecified, and reserved
   addresses (also checking IPv4-mapped IPv6), and connects to a validated IP using
   connection code (new, proposed) that preserves the original `Host` header and TLS
   SNI with `_NoRedirect`.

### 11.2 Pinned error mappings

Every `ErrorCode` member in `src/researchbase/foundation/errors.py` (57 members) is
pinned below with its exact HTTP status (`src/researchbase/api/errors.py:_STATUS`) and
CLI exit code (`src/researchbase/cli/errors.py:CLI_EXIT_CODES`), plus the unhandled
`INTERNAL_ERROR` fallback:

| `ErrorCode` | HTTP | CLI | Category / Oracle |
| --- | ---: | ---: | --- |
| `VALIDATION_ERROR` | 422 | 2 | Closed DTO/field/hash/limit validation failure |
| `IDENTIFIER_INVALID` | 422 | 2 | Malformed external literature source identifier |
| `SEARCH_PLAN_QUESTION_REQUIRED` | 422 | 2 | Search plan missing research question reference |
| `SEARCH_PLAN_LANGUAGE_SCOPE_REQUIRED` | 422 | 2 | Search plan missing language scope |
| `SEARCH_PLAN_QUESTION_INVALID` | 422 | 2 | Search plan research question reference invalid |
| `AUTHENTICATION_REQUIRED` | 401 | 3 | Missing, unverified, revoked, or expired principal credential |
| `FORBIDDEN` | 403 | 3 | Authenticated principal lacks required project role or project scope |
| `CONFLICT_OF_INTEREST` | 403 | 3 | Reviewer/approver independence violation |
| `SUBJECT_BINDING_UNPROVEN` | 403 | 3 | Principal subject binding missing or unproven for deployment |
| `SOURCE_MERGE_APPROVAL_FORBIDDEN` | 403 | 3 | Caller not authorized to approve source merge proposal |
| `SEARCH_PLAN_QUESTION_SCOPE_MISMATCH` | 403 | 3 | Search plan question belongs to another project |
| `NOT_FOUND` | 404 | 3 | Entitled lookup for absent target record |
| `SOURCE_NOT_FOUND` | 404 | 3 | Absent literature source |
| `SOURCE_MERGE_PROPOSAL_NOT_FOUND` | 404 | 3 | Absent source merge proposal |
| `SOURCE_VERSION_NOT_FOUND` | 404 | 3 | Absent literature source version |
| `REVIEW_TARGET_NOT_FROZEN` | 409 | 4 | Review target exists in non-frozen state |
| `INVALID_STATE_TRANSITION` | 409 | 4 | Illegal lifecycle/outcome/supersession/disposition transition |
| `VERSION_NOT_FROZEN` | 409 | 4 | Target version exists in `DRAFT` when `FROZEN` is required |
| `IMMUTABLE_RECORD` | 409 | 4 | Attempted mutation/deletion of frozen/immutable row |
| `CONCURRENT_MODIFICATION` | 409 | 4 | Exhausted serialization/deadlock retry, lock timeout, or manifest race |
| `DUPLICATE_CONTENT` | 409 | 4 | Duplicate content-addressed or unique domain payload |
| `SUBJECT_ALREADY_BOUND` | 409 | 4 | External subject already bound in deployment |
| `OWNER_COVERAGE_GAP` | 409 | 4 | Project owner membership/role coverage would become empty |
| `OWNER_CREDENTIAL_UNAVAILABLE` | 409 | 4 | Owner lacks active verified credential for operation |
| `ENROLLMENT_CHALLENGE_EXPIRED` | 409 | 4 | Subject binding enrollment challenge expired |
| `BOOTSTRAP_CLOSED` | 409 | 4 | Phase 2 bootstrap window already closed |
| `IDEMPOTENCY_CONFLICT` | 409 | 4 | Reused command UUID/key with different normalized payload |
| `LEGACY_STATE_INVALID` | 409 | 4 | Legacy preflight state violates Phase 2 invariant |
| `SOURCE_IDENTITY_CONFLICT` | 409 | 4 | Conflicting literature source identity binding |
| `IDENTIFIER_ALREADY_BOUND` | 409 | 4 | Literature identifier already bound to another source |
| `IDENTIFIER_BASIS_NOT_FROZEN` | 409 | 4 | Identifier binding basis is not frozen |
| `SHARED_SOURCE_REJECTION_REQUIRES_REVIEW` | 409 | 4 | Shared source rejection requires governance review |
| `SOURCE_MERGE_PROPOSAL_STALE` | 409 | 4 | Source merge proposal basis is stale |
| `SOURCE_MERGE_APPROVAL_MISSING` | 409 | 4 | Source merge execution lacks required approval |
| `SOURCE_MERGE_REJECTED` | 409 | 4 | Source merge proposal was rejected |
| `SOURCE_MERGE_PROPOSAL_ALREADY_CONSUMED` | 409 | 4 | Source merge proposal already consumed |
| `SOURCE_MERGE_BASIS_CONFLICT` | 409 | 4 | Source merge basis changed concurrently |
| `SOURCE_NOT_MERGEABLE` | 409 | 4 | Source state does not permit merge |
| `SOURCE_MERGE_IDENTIFIER_CONFLICT` | 409 | 4 | Source merge produces conflicting identifier binding |
| `SOURCE_VERSION_NOT_FREEZABLE` | 409 | 4 | Source version cannot transition to `FROZEN` |
| `SOURCE_VERSION_ALREADY_FROZEN` | 409 | 4 | Source version is already `FROZEN` |
| `SOURCE_VERSION_IMMUTABLE` | 409 | 4 | Frozen source version cannot be mutated |
| `INVALID_SOURCE_VERSION_LINEAGE` | 409 | 4 | Invalid predecessor/merge source version lineage |
| `SEARCH_PLAN_VERSION_IMMUTABLE` | 409 | 4 | Frozen search plan version cannot be mutated |
| `SEARCH_PLAN_NOT_FROZEN` | 409 | 4 | Search plan version is not `FROZEN` |
| `ADAPTER_VERSION_MISMATCH` | 409 | 4 | Provider adapter version/profile mismatch |
| `APPROVAL_PURPOSE_TARGET_COMMAND_INVALID` | 409 | 4 | Finite approval purpose/target/allowed_command tuple mismatch |
| `APPROVAL_GATE_FAILED` | 409 | 4 | Open blocking issue, missing/withdrawn consent, or missing `READY` receipt |
| `DECISION_BASIS_INVALID` | 409 | 4 | Incomplete/invalid review basis or checked review set |
| `APPROVAL_TARGET_STALE` | 409 | 4 | Target scientifically stale/invalid or superseded at gate/first use |
| `REJECTION_RECONSIDERATION_REQUIRED` | 409 | 4 | Prior rejected request requires valid reconsideration Decision |
| `GRANT_INVALID` | 409 | 4 | Grant expired, revoked, or already consumed on a different command key |
| `GRANT_STALE` | 409 | 4 | Grant terminalized `STALE` or issuing authority unavailable |
| `FROZEN_REFERENCE_REQUIRED` | 409 | 5 | Formal provenance reference targets non-frozen state |
| `PROVENANCE_CLOSURE_VIOLATION` | 409 | 5 | Saved/input provenance graph incomplete, corrupt, or cross-scope |
| `REFERENTIAL_INTEGRITY_ERROR` | 409 | 5 | Concrete foreign-key or referential integrity violation |
| `ADAPTER_UNAVAILABLE` | 503 | 5 | External/provider adapter unavailable |

Unhandled non-`ResearchBaseError` exceptions map to HTTP `500` with body code
`"INTERNAL_ERROR"` and CLI exit code `1` (literal fallback in the CLI error adapter).

### 11.3 Verified DTO fields, Python types and evidence records

The following declarations are copied from the owning Application modules. These are
DTO fields, not database columns; validation remains defined by each class and its
owning domain validators. No new Application DTO is proposed by B31.

#### 11.3.1 Exercised Application DTOs (`src/researchbase/application/`)

| Module & DTO class | Existing field declarations (including defaults) |
| --- | --- |
| `manuscript_freeze.FreezeManuscriptCommand` | `project_id: UUID`; `publication_id: UUID`; `manuscript_version_id: UUID`; `expected_placement_set_hash: str`; `expected_content_hash: str`. |
| `revision_action.RecordRevisionActionCommand` | `id: UUID`; `project_id: UUID`; `action_type: str`; `review_issue_id: UUID \| None = None`; `decision_record_id: UUID \| None = None`; `result_experiment_spec_version_id: UUID \| None = None`; `result_run_id: UUID \| None = None`; `result_statistical_result_id: UUID \| None = None`; `result_claim_version_id: UUID \| None = None`; `result_scientific_conclusion_version_id: UUID \| None = None`; `result_manuscript_version_id: UUID \| None = None`; `result_source_version_id: UUID \| None = None`; `supersedes_revision_action_id: UUID \| None = None`. |
| `revision_action.RecordConcernReReviewCommand` | `project_id: UUID`; `revision_action_id: UUID`; `internal_review_record_id: UUID`. |
| `internal_review.RecordIssueDispositionCommand` | `id: UUID`; `project_id: UUID`; `review_issue_id: UUID`; `disposition: Disposition`; `revision_action_id: UUID`; `re_review_record_id: UUID`; `rationale: str`; `decision_id: UUID \| None = None`. |
| `decision.RecordRevisionDecisionCommand` | `id: UUID`; `project_id: UUID`; `review_issue_id: UUID`; `question: str`; `rationale: str`; `decision: RevisionChoice`; `decision_type: RevisionPurpose = 'REVISION_RESPONSE'`. |
| `decision.RecordReadyForSubmissionDecisionCommand` | `id: UUID`; `project_id: UUID`; `manuscript_version_id: UUID`; `question: str`; `rationale: str`; `decision_type: Literal['READY_FOR_SUBMISSION'] = 'READY_FOR_SUBMISSION'`; `decision: Literal['PROCEED'] = 'PROCEED'`. |
| `decision.RecordPrepareSubmissionDecisionCommand` | `id: UUID`; `project_id: UUID`; `manuscript_version_id: UUID`; `question: str`; `rationale: str`; `decision_type: Literal['PREPARE_SUBMISSION'] = 'PREPARE_SUBMISSION'`; `decision: Literal['PROCEED'] = 'PROCEED'`. |
| `approval.RequestApprovalCommand` | `id: UUID`; `project_id: UUID`; `scientific_conclusion_version_id: UUID \| None`; `basis_decision_id: UUID`; `review_ids: tuple[UUID, ...]`; `approval_purpose: str = PURPOSE`; `manuscript_version_id: UUID \| None = field(default=None, kw_only=True)`; `prior_rejected_request_id: UUID \| None = field(default=None, kw_only=True)`; `reconsideration_decision_id: UUID \| None = field(default=None, kw_only=True)`. |
| `approval.DecideApprovalCommand` | `id: UUID`; `project_id: UUID`; `approval_request_id: UUID`; `decision: str`; `rationale: str`; `valid_until: datetime \| None = None`; `requires_current_author_consent: bool = False`. |
| `approval.EvaluateApprovalGrantCommand` | `project_id: UUID`; `grant_id: UUID`. |
| `approval.RevokeApprovalGrantCommand` | `project_id: UUID`; `grant_id: UUID`; `reason: str`. |
| `approval.RecordInternalScientificReleaseCommand` | `command_key: UUID`; `project_id: UUID`; `grant_id: UUID`; `result_id: UUID`; `checked_review_ids: tuple[UUID, ...]`; `expected_package_manifest_hash: None = None`. |
| `publication.TransitionPublicationReadyCommand` | `command_key: UUID`; `project_id: UUID`; `grant_id: UUID`; `result_id: UUID`; `checked_review_ids: tuple[UUID, ...]`. |
| `authorship.RecordContributionCommand` | `id: UUID`; `project_id: UUID`; `publication_id: UUID`; `actor_id: UUID`; `contribution_role: ContributionRole`; `contribution_statement: str`. |
| `authorship.CreateAuthorshipSnapshotCommand` | `id: UUID`; `project_id: UUID`; `publication_id: UUID`; `author_ids: tuple[UUID, ...]`; `corresponding_author_ids: tuple[UUID, ...]`; `equal_contribution_groups: tuple[tuple[UUID, ...], ...]`; `contribution_record_ids: tuple[UUID, ...]`. |
| `prepared_submission.PrepareSubmissionCommand` | `id: UUID`; `project_id: UUID`; `publication_id: UUID`; `manuscript_version_id: UUID`; `authorship_snapshot_id: UUID`. |
| `prepared_submission.RecordAuthorConsentCommand` | `id: UUID`; `project_id: UUID`; `prepared_submission_version_id: UUID`; `consent_state: ConsentState`; `consent_scope: ConsentScope`; `evidence_artifact_version_id: UUID`; `prior_consent_id: UUID \| None`. |
| `prepared_submission.WithdrawPreparedSubmissionCommand` | `project_id: UUID`; `prepared_submission_version_id: UUID`; `reason: str`. |
| `prepared_submission.FreezePreparedSubmissionCommand` | `command_key: UUID`; `project_id: UUID`; `grant_id: UUID`; `result_id: UUID`; `expected_package_manifest_hash: str`; `checked_review_ids: tuple[UUID, ...]`. |
| `novelty.RecordSearchCoverageCommand` | `id: UUID`; `project_id: UUID`; `search_plan_version_id: UUID`; `search_execution_ids: tuple[UUID, ...]`; `coverage_limitations: str`. |
| `novelty.RecordPriorArtRelationCommand` | `id: UUID`; `project_id: UUID`; `claim_version_id: UUID`; `source_version_id: UUID`; `relation: PriorArtKind`; `rationale: str`; `literature_evidence_ids: tuple[UUID, ...]`; `supersedes_prior_art_relation_id: UUID \| None = None`. |
| `novelty.RecordNoveltyAssessmentCommand` | `id: UUID`; `project_id: UUID`; `claim_version_id: UUID`; `search_coverage_id: UUID`; `assessment: NoveltyOutcome`; `limitations: str`; `supersedes_assessment_id: UUID \| None = None`; `prior_art_basis: tuple[PriorArtBasisInput, ...] = ()`; `scope_statement: str \| None = None`; `closeness_criteria: ClosenessCriteria \| None = None`. |
| `novelty.ExactReadQuery` | `project_id: UUID`; `id: UUID`. |
| `novelty.PriorArtSelectionQuery` | `project_id: UUID`; `claim_version_id: UUID`; `source_version_id: UUID`. |

#### 11.3.2 Closed Engineering Evidence Records (`tests/contracts/pr2_20_evidence.py`)

Existing engineering records inherit `schema_version`, `subject_revision`,
`dirty_diff_sha256`, `status`, `reason`, and `evidence_refs` from `EvidenceRecord`.
The shared `Result` type already includes `"DEFERRED"` and `"NOT RUN"`; B31 proposes
narrow validation and report changes for B28, not new status fields. Bounds are
`MAX_BYTES = 1024 * 1024` and `MAX_ARRAY = 10_000` in the owning module.

| Dataclass | Verified existing fields used by B31 & proposed behavior |
| --- | --- |
| `QueryPlanEvidence` | `case_id`, `service_method`, `repository_method`, `parameter_class`, `sql_sha256`, `profile_ref`, `sample_ref`, `plan_refs`, `index_definitions`, `calls`, `warmups`, `concurrency`, `p50_ms`, `p95_ms`, `max_ms`, `lock_wait_ms`, `buffer_hits`, `buffer_reads`, `query_count`, `correctness_equal`. |
| `AdapterInventoryEntry` | `mode`, `package_version`, `unresolved_items` plus inherited `status` and `reason`. Proposed B28 validation: `status == "DEFERRED"` requires `mode == "DEFERRED"`, `package_version is None`, non-empty `reason` and `unresolved_items`. |
| `MigrationEvidence` | `start_revision`, `target_revision`, `fixture_class` (`"EMPTY"`, `"LEGAL_POPULATED"`, `"INVALID_LEGACY"`, `"INTERRUPTED"`), `commands`, `exit_codes`, `catalog_before_ref`, `catalog_after_ref`, `manifest_before_ref`, `manifest_after_ref`, `rollback_equal`, `history_equal`, `downgrade_result`, `restored_read_result`. |
| `ExitCriterionEvidence` | `criterion`, `test_nodes`, `commands`, `exit_codes`, `passed`, `failed`, `errors`, `skipped`, `disposition_refs` plus inherited `status` and `reason`. Proposed B28 validation: accept `status == "DEFERRED"` only for `criterion == "PaperQA2 Adapter"` with a non-empty `reason` and the owner deferral record in `disposition_refs`; all other rows require verified `"PASS"`. |
| `BenchmarkProfile` | Dataset/host configuration includes `seed`, `projects`, `sources`, `claims`, `manuscripts`, `warmups`, `calls_per_worker`, `repetitions`, `concurrency_profiles`. Per-operation timing and correctness observations belong to `QueryPlanEvidence`; do not invent timing or failure-count fields on `BenchmarkProfile`. |

---

## 12. Implementation guide

### 12.1 DDL sketch and catalog assertions

```sql
-- B31 upgrade / downgrade DDL: EMPTY.
-- DO NOT ADD SCHEMA. Candidate partial index ix_pr220_issue_open_blocking_review is rejected (B29).
```

`tests/integration/phase2/test_pr2_20_catalog_plans.py` and
`tests/integration/phase2/test_pr2_20_migrations.py` must assert the following live
PostgreSQL 18 catalog invariants at head (`0068_b21_unresolved_capture`):

The columns below are selected assertions, not full table definitions. SQL types
are copied from the migrations. Constraint names, trigger names, function names,
and index names are separate catalog objects: check `pg_constraint`, `pg_trigger`,
`pg_proc`, and `pg_indexes` respectively. Generated object names must be obtained
from the migration's explicit construction or the live catalog, never inferred.

| Migration source (`migrations/versions/`) | Existing tables and selected columns | Existing objects and head/checkpoint distinction |
| --- | --- | --- |
| `0040_pr2_14_initial_internal_review.py`, `0041_pr2_15_review_coordination.py`, `0053_b08_issue_disposition.py` | `internal_review_records`; `review_issues`: `id UUID`, `review_record_id UUID`, `severity VARCHAR(16)`, `status VARCHAR(16)`, `ordinal INT`; `review_issue_events`: `id UUID`, `issue_id UUID`, `revision_action_id UUID`, `decision_id UUID`, `re_review_record_id UUID`. | Constraints `ck_pr214_one_target`, `ck_b08_issue_status`, `ck_b08_event_shape`, `fk_b08_event_action`, `fk_b08_event_re_review`, `fk_b08_event_decision`, `fk_b08_event_mapping`; deferred triggers `b08_complete_issue`, `b08_complete_event`; index `ix_pr214_issue_review_severity`. The rejected clone-only index `ix_pr220_issue_open_blocking_review` must be absent at canonical head. |
| `0042_pr2_15_minimal_decision.py`, `0052_b07_revision_decisions.py`, `0054_b11_ready_for_submission.py`, `0056_b10_reconsideration.py`, `0058_b12_prepare_submission.py` | `decision_records`: `id UUID`, `project_id UUID`, `decision_type VARCHAR(40)`, `decision VARCHAR(16)`, `question TEXT`, `rationale TEXT`, `decided_by UUID`, `decided_at TIMESTAMPTZ`, `supersedes_decision_id UUID`, `basis_set_hash CHAR(64)`, `content_hash CHAR(64)`, `hash_scheme VARCHAR(32)`; `decision_basis_conclusions`, `decision_basis_reviews`, `decision_basis_claims`, `decision_basis_manuscripts`, `decision_basis_approval_decisions`, `decision_basis_revision_actions`; `decision_revision_concerns`: `decision_id UUID`, `review_issue_id UUID`. | At head: constraints `ck_b07_claim_ordinal`, `ck_b11_manuscript_ordinal`, `ck_b11_text_bounds`, `ck_b10_text_bounds`, `ck_b10_finite_time`, `ck_b12_decision_policy`, `ck_b12_text_bounds`; immutable trigger `b07_decision_concern_immutable`; deferred triggers `pr215_complete_decision`, `pr215_complete_conclusion`, `pr215_complete_review`, `b07_complete_decision`, `b11_complete_manuscript`, `b10_complete_decision`. Function `b11_complete` is not a trigger. Historical constraints `ck_b07_decision_tuple` (0052), `ck_b11_decision_policy` (0054), and `ck_b10_decision_pair` (0056) are successively dropped/replaced; assert them at their owning checkpoints, not at head. |
| `0044_pr2_15_revision_action.py`, `0051_b06_revision_action.py`, `0052_b07_revision_decisions.py` | `revision_actions`: `id UUID`, `review_issue_id UUID`, `decision_record_id UUID`, `action_type VARCHAR(32)`, `supersedes_revision_action_id UUID`, `content_hash CHAR(64)`; `revision_action_re_reviews`: `revision_action_id UUID`, `internal_review_record_id UUID`, `recorded_by UUID`, `recorded_at TIMESTAMPTZ`. | Constraint `revision_action_shape`; unique index `uq_revision_action_predecessor`; primary key `pk_b07_action_re_review`; deferred triggers `b06_revision_complete`, `b07_complete_re_review`. The table has no project column; the command's project scope is resolved through its basis. |
| `0045_pr2_16_basic_approval.py`, `0055_b09_approval_tuples.py`, `0059_b13_grant_consumption.py` | `approval_requests`, `approval_request_reviews`, `approval_request_events`, `approval_decisions`, `approval_grants`, `approval_grant_events`; `approval_grant_consumptions`: `id UUID`, `grant_id UUID`, `command_key UUID`, `project_id UUID`, `actor_id UUID`, `command VARCHAR(40)`, `request_hash CHAR(64)`, `result_dto JSONB`. | Constraints `ck_b09_request_tuple`, `ck_b09_grant_tuple`, `ck_b09_consent_condition`, `uq_b13_consumption_grant`, `uq_b13_command_key`, `ck_b13_result_tuple`, `ck_b13_hash`, `ck_b13_dto`; deferred triggers `pr216_complete_request`, `pr216_complete_reviews`, `pr216_complete_decision`, `pr216_complete_grant`, `b13_complete_consumption`. Later migrations extend the definition of `ck_b13_result_tuple` without changing its name. |
| `0046_pr2_17_authorship_preparation.py`, `0060_b15_package_preparation.py`, `0061_b16_consent_withdrawal.py`, `0067_b17_prepared_package_freeze.py` | `contribution_records`, `authorship_snapshots`, `authorship_snapshot_authors`, `authorship_snapshot_corresponding_authors`, `authorship_snapshot_equal_groups`, `authorship_snapshot_contributions`, `prepared_submission_versions`, `prepared_submission_manifest_items`, `prepared_submission_events`, `author_consents`. | Constraints `uq_b15_package_parent`, `uq_b15_package_number`, `ck_b15_package_status`, `ck_b15_package_hash_state`, `uq_b15_consent_package`, `ck_b15_consent_hash`, `ck_b16_consent_state`, `ck_b16_consent_scope`; deferred FK `fk_b17_result_package`; deferred triggers `b17_complete_package`, `b17_complete_item`, `b17_complete_event`, `b17_complete_consumption`. |
| `0047_pr2_18_novelty_prior_art.py`, `0065_b22_prior_art_correction.py`, `0066_b19_close_prior_art_basis.py`, `0068_b21_unresolved_capture.py` | `search_coverage`: `material_version SMALLINT`, `captured_unresolved_result_count INT`; `search_coverage_executions`; `search_coverage_resolutions`: `search_coverage_id UUID`, `search_result_resolution_id UUID`, `resolution_content_hash CHAR(64)`; `prior_art_relations`: `supersedes_prior_art_relation_id UUID`; `prior_art_evidence_inputs`; `novelty_assessments`: `scope_statement TEXT`, `closeness_criteria JSONB`; `novelty_assessment_prior_art_inputs`. | Constraints `uq_pr218_coverage_execution_pair`, `uq_b21_resolutions_pair`, `ck_b21_capture_version`, `ck_b21_capture_count`, `ck_b21_resolution_hash`, `uq_b22_prior_art_pair`, `fk_b22_prior_art_predecessor`, `ck_b19_novelty_material`; unique index `uq_b22_prior_art_predecessor`; deferred triggers `trg_b19_novelty_complete`, `trg_b19_basis_complete`, `b22_complete_correction`. Function `b19_complete_basis` is not a trigger. |
| `0035_pr2_12_publication_draft.py`, `0048_b04_manuscript_freeze.py`, `0049_b05_manuscript_review.py`, `0062_b14a_publication_entry.py`, `0063_b14r_ready_approval.py`, `0064_b14_publication_ready.py` | `publications`: `lifecycle_status VARCHAR(24)`, `current_manuscript_version_id UUID`; `publication_lifecycle_events`; `manuscript_versions`: `status VARCHAR(16)`, `content_hash CHAR(64)`, `placement_set_hash CHAR(64)`. | Constraints `ck_b04_manuscript_seal`, `ck_b04_manuscript_status`, `fk_b14_ready_decision`, `ck_b14a_event_tuple`; deferred FK `fk_b14_ready_consumption`; deferred triggers `b04_complete_manuscript`, `b05_complete_review`, `b14_complete_publication`, `b14_complete_ready_event`, `b14_complete_ready_consumption`. |

### 12.2 Exact lock order per command

All write commands below set `lock_timeout = '10s'` and `statement_timeout = '30s'`.
Source tuple names refer to the existing ordered table tuples in
`src/researchbase/persistence/`. Angle brackets below are explanatory interpolation
placeholders, not SQL identifiers; SQL constants already contain complete statements:

| Command (`Service.method`) | Isolation & exact lock order |
| --- | --- |
| `SearchResultResolutionService.record_search_result_resolution` | `READ COMMITTED`; **1st stmt**: `LOCK TABLE <search_result_resolution_repository.R> IN SHARE MODE`; timeouts; `pg_advisory_xact_lock('b01:resolution:<id>')`; authority/replay/closure reads; insert; `SET CONSTRAINTS ALL IMMEDIATE`; final authority; commit. |
| `ManuscriptFreezeService.freeze_manuscript_version` | `READ COMMITTED`; **1st stmt**: `LOCK TABLE <manuscript_freeze_repository.B04_SNAPSHOT_TABLES> IN SHARE MODE`; timeouts; `lock_project(project_id)`; `publications` `FOR UPDATE`; `manuscript_versions` `FOR UPDATE`; authority/replay/placement closure/hash check; supersession + freeze update; `SET CONSTRAINTS ALL IMMEDIATE`; final authority; commit. |
| `InternalReviewService.create` (Claim / Conclusion / Manuscript) | `READ COMMITTED`; owner reservation protocol: `LOCK TABLE internal_review_records IN ROW EXCLUSIVE MODE` first; for manuscript review then `LOCK TABLE <B05_SNAPSHOT_TABLES> IN SHARE MODE`, timeouts, `pr214:review:<id>` advisory, `manuscript_versions` `FOR UPDATE`, `lock_project`, `publications` `FOR SHARE`; for conclusion/claim review `pr214:review:<id>` advisory, target `FOR UPDATE`, parent `FOR UPDATE`, `lock_project`; insert review + issues + events; commit. |
| `RevisionActionService.record_revision_action` | `READ COMMITTED`; **1st stmt**: `LOCK TABLE <revision_action_repository.REVISION_SNAPSHOT_TABLES> IN SHARE MODE`; timeouts; `pg_advisory_xact_lock('pr215:revision:<id>')`; authority/replay; basis `internal_review_records` `FOR SHARE`; basis `review_issues` `FOR SHARE`; predecessor `revision_actions` row `FOR UPDATE` (when `supersedes_revision_action_id` is non-null) + successor recheck; verify result closure; insert; `SET CONSTRAINTS ALL IMMEDIATE`; final authority; commit. |
| `RevisionActionService.record_concern_re_review` | `READ COMMITTED`; **1st stmt**: `LOCK TABLE <REVISION_SNAPSHOT_TABLES> IN SHARE MODE`; timeouts; `pg_advisory_xact_lock('b07:re-review:<action>:<review>')`; authority/replay; sorted original and re-review record IDs `FOR SHARE`; basis `review_issues` `FOR SHARE`; `revision_actions` `FOR UPDATE`; insert link; `SET CONSTRAINTS ALL IMMEDIATE`; final authority; commit. |
| `InternalReviewService.record_issue_disposition` | `READ COMMITTED`; **1st stmt**: `LOCK TABLE <REVISION_SNAPSHOT_TABLES> IN SHARE MODE`; timeouts; `pg_advisory_xact_lock('b08:disposition:<id>')`; authority/replay; sorted original and re-review record IDs `FOR SHARE`; sorted issue IDs (the selected `review_issues.id` `FOR UPDATE`, re-review issues `FOR SHARE`); verify basis/correspondence; insert `review_issue_events` + update `review_issues.status`; `SET CONSTRAINTS ALL IMMEDIATE`; final authority; commit. |
| `DecisionService.record_decision` (minimal conclusion `PROCEED`) | `READ COMMITTED`; **1st stmt**: `LOCK TABLE <approval_repository.B09_SNAPSHOT_TABLES> IN SHARE MODE`; timeouts; `pg_advisory_xact_lock('pr215:decision:<id>')`; `pg_advisory_xact_lock('pr216:scope:<project>:INTERNAL_SCIENTIFIC_RELEASE')`; `scientific_conclusion_versions` `FOR UPDATE`; `lock_project(project_id)`; basis/blocker verification; insert decision + basis; `SET CONSTRAINTS ALL IMMEDIATE`; final authority; commit. |
| `DecisionService.record_revision_decision` | `READ COMMITTED`; **1st stmt**: `LOCK TABLE <REVISION_SNAPSHOT_TABLES> IN SHARE MODE`; timeouts; `pg_advisory_xact_lock('pr215:decision:<id>')`; authority/replay; sorted review IDs `FOR SHARE`; `review_issue_id` `FOR UPDATE`; target/action verification; insert decision + basis + concern link; `SET CONSTRAINTS ALL IMMEDIATE`; final authority; commit. |
| `DecisionService.record_ready_for_submission_decision` / `record_prepare_submission_decision` | `READ COMMITTED`; **1st stmt**: execute `decision_repository.B11_SHARE_SQL`; timeouts; `pg_advisory_xact_lock('b11:decision:<id>')` / `'b12:decision:<id>'`; `manuscript_versions` `FOR UPDATE`; `projects` `FOR SHARE`; `publications` `FOR SHARE`; authority/replay/review closure; insert decision + manuscript/review basis; `SET CONSTRAINTS ALL IMMEDIATE`; final authority; commit. |
| `ApprovalService.request_approval` / `decide_approval` | `READ COMMITTED`; **1st stmt**: `approval_repository.B09_SHARE_SQL` for requests; `approval_repository.B09_DECIDE_SHARE_SQL` followed by `LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE` for decisions; timeouts; `pg_advisory_xact_lock('pr216:uuid:<id>')`; resolve purpose; `pg_advisory_xact_lock('pr216:scope:<project>:<purpose>')`; target (`scientific_conclusion_version_id` or `manuscript_version_id`) `FOR UPDATE`; `publications` `FOR SHARE` (when manuscript target); `approval_requests` `FOR UPDATE` (on `decide_approval`); authority/replay/gate checks; affected `approval_grants` UUID-sorted `FOR UPDATE`; insert rows/events; `SET CONSTRAINTS ALL IMMEDIATE`; final authority; commit. |
| `ApprovalService.evaluate_approval_grant` / `revoke_approval_grant` | `READ COMMITTED`; **1st stmt**: `LOCK TABLE <B13_SNAPSHOT_TABLES> IN SHARE MODE`; `LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE`; `LOCK TABLE <B13_APPROVAL_TABLES> IN SHARE MODE`; timeouts; `pg_advisory_xact_lock('b13:lifecycle:<grant_id>')`; `pr216:scope:<project>:<purpose>` advisory; target `FOR UPDATE`; parent `FOR SHARE`; `approval_requests` `FOR SHARE`; `approval_grants` `FOR UPDATE`; terminalize + insert event; `SET CONSTRAINTS ALL IMMEDIATE`; final authority; commit. |
| `ScientificConclusionService.record_internal_scientific_release` | `SERIALIZABLE`; **1st stmt**: `LOCK TABLE <B13_SNAPSHOT_TABLES> IN SHARE MODE`; `LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE`; `LOCK TABLE <B13_APPROVAL_TABLES> IN SHARE MODE`; timeouts; `pg_advisory_xact_lock('b13:consume:<command_key>')`; `pg_advisory_xact_lock('pr216:scope:<project>:INTERNAL_SCIENTIFIC_RELEASE')`; `scientific_conclusion_versions` `FOR UPDATE`; `scientific_conclusions` `FOR SHARE`; `approval_requests` `FOR SHARE`; `approval_grants` `FOR UPDATE`; gate/fresh-clock checks; insert receipt + `CONSUMED` event/status; `SET CONSTRAINTS ALL IMMEDIATE`; final authority/expiry checks; commit. |
| `PublicationService.transition_publication_internal_review` | `READ COMMITTED`; **1st stmt**: execute `publication_repository.B14A_SHARE_SQL`; `LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE`; `LOCK TABLE approval_decisions,approval_request_reviews,approval_requests IN SHARE MODE`; timeouts; `pg_advisory_xact_lock('b14a:entry:<publication_id>')`; `manuscript_versions` `FOR UPDATE`; `publications` `FOR UPDATE`; update status + insert lifecycle event; `SET CONSTRAINTS ALL IMMEDIATE`; final authority; commit. |
| `PublicationService.transition_publication_ready` | `SERIALIZABLE`; **1st stmt**: execute `B13_SHARE_SQL`; `LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE`; execute `B13_APPROVAL_SQL`; timeouts; `pg_advisory_xact_lock('b13:consume:<command_key>')`; `pg_advisory_xact_lock('pr216:scope:<project>:READY_FOR_SUBMISSION')`; `manuscript_versions` `FOR UPDATE`; `publications` `FOR UPDATE`; `approval_requests` `FOR SHARE`; `approval_grants` `FOR UPDATE`; gate/fresh-clock checks; update publication `READY` + lifecycle event + receipt + `CONSUMED` grant event/status; `SET CONSTRAINTS ALL IMMEDIATE`; final checks; commit. |
| `AuthorshipService.record_contribution` / `create_authorship_snapshot` | `READ COMMITTED`; owner PR2-17 order: timeouts; `pg_advisory_xact_lock('pr217:authorship:<id>')`; `publications` `FOR UPDATE`; `LOCK TABLE <authorship_repository._SNAPSHOT_TABLES> IN SHARE MODE`; `lock_project(project_id)`; `actors` UUID-sorted `FOR SHARE`; `contribution_records` UUID-sorted `FOR SHARE` (when snapshot); replay/coverage checks; insert parent + child rows; final authority; commit. |
| `PreparedSubmissionService.prepare_submission` / `withdraw_prepared_submission` | `READ COMMITTED`; **1st stmt**: execute `prepared_submission_repository.B15_SHARE_SQL`; timeouts; `pg_advisory_xact_lock('b15:prepare:<id>')` or `'b15:withdraw:<package_id>'`; `manuscript_versions` `FOR UPDATE`; `publications` `FOR UPDATE`; `prepared_submission_versions` `FOR UPDATE` (on `withdraw`); authority/replay/projection; insert/update package + items/event; `SET CONSTRAINTS ALL IMMEDIATE`; final authority; commit. |
| `PreparedSubmissionService.record_author_consent` | `READ COMMITTED`; **1st stmt**: execute `B16_SHARE_SQL`; `LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE`; `LOCK TABLE approval_decisions,approval_request_reviews,approval_requests IN SHARE MODE`; timeouts; `pg_advisory_xact_lock('b15:consent:<id>')`; `pg_advisory_xact_lock('pr216:scope:<project>:PREPARE_SUBMISSION')`; `manuscript_versions` `FOR UPDATE`; `publications` `FOR UPDATE`; `prepared_submission_versions` `FOR UPDATE`; caller's `author_consents` chain `ORDER BY id FOR UPDATE`; on `WITHDRAWN`, related `ACTIVE` `approval_grants` UUID-sorted `FOR UPDATE` and terminalized `STALE`; insert consent; `SET CONSTRAINTS ALL IMMEDIATE`; final authority; commit. |
| `PreparedSubmissionService.freeze_prepared_submission` | `SERIALIZABLE`; **1st stmt**: execute `B17_SHARE_SQL`; `LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE`; `LOCK TABLE prepared_submission_versions IN SHARE ROW EXCLUSIVE MODE`; `LOCK TABLE approval_decisions,approval_request_reviews,approval_requests IN SHARE MODE`; timeouts; `pg_advisory_xact_lock('b13:consume:<command_key>')`; `pg_advisory_xact_lock('pr216:scope:<project>:PREPARE_SUBMISSION')`; `manuscript_versions` `FOR UPDATE`; `publications` `FOR UPDATE`; `prepared_submission_versions` `FOR UPDATE`; older `FROZEN` packages `ORDER BY id FOR UPDATE`; each author's `author_consents` chain `FOR UPDATE` in sorted `actor_id` order; `approval_requests` `FOR SHARE`; `approval_grants` `FOR UPDATE`; insert `AUTHOR_CONSENT` items + supersede older packages/events + seal package/event + receipt + `CONSUMED` grant event/status; `SET CONSTRAINTS ALL IMMEDIATE`; final checks; commit. |
| `NoveltyService.record_search_coverage` / `record_prior_art_relation` / `record_novelty_assessment` | `READ COMMITTED`; **1st stmt**: `LOCK TABLE <novelty_repository.N> IN SHARE MODE`; timeouts; `pg_advisory_xact_lock('pr218:<kind>:<id>')`; `claim_versions` `FOR UPDATE` (for `prior_art` and `novelty`; `coverage` takes no Claim row lock); predecessor `prior_art_relations` or `novelty_assessments` `FOR UPDATE` (when a predecessor ID is non-null) + successor recheck; insert parent + UUID-sorted child rows (`search_coverage_executions`, `search_coverage_resolutions`, `prior_art_evidence_inputs`, `novelty_assessment_prior_art_inputs`); `SET CONSTRAINTS ALL IMMEDIATE`; final authority; commit. (When H2 lands, completed exact command replay returns via the lock-free `REPEATABLE READ` reader before opening the writer.) |
| **All formal read queries & completed consumption replays** | Single `REPEATABLE READ, READ ONLY` UoW; initial + final DB-clock read entitlement; **zero** `LOCK TABLE`, **zero** `pg_advisory_xact_lock`, **zero** `FOR UPDATE` / `FOR SHARE`, and **zero** writes. |

### 12.3 Ordered build steps with real file paths

#### Slice B31-S1 — Real Adapter Destination Security & B28 Deferral Disposition

1. Edit `src/researchbase/adapters/literature_http.py`:
   - Add pre-dispatch URL and destination IP validation helper `_resolve_public_peer(url: str, timeout: float) -> tuple[str, str, int, str, str]` (new, proposed); its implementation will parse URLs, resolve addresses, and classify IPs before connecting.
   - Reject disallowed schemes, URL userinfo, empty hostnames, invalid ports, and any literal or DNS-resolved address that is non-global, loopback, private, link-local, multicast, unspecified, or reserved. Inspect IPv4-mapped IPv6 as well, raising `HttpTransportFailure(DeliveryCertainty.NOT_SENT)` before a destination connection.
   - Add connection code (new, proposed) that connects directly to the validated IP and port while sending the original `Host` header and verifying the HTTPS certificate and TLS SNI against the original hostname. This removes the DNS-rebinding window between resolution and connection. Keep `_NoRedirect`.
2. Edit `tests/contracts/pr2_20_evidence.py` and `tests/contracts/pr2_20_reports.py`:
   - Retain the existing shared `Result` allowance for `"DEFERRED"`; enforce the B28 predicates in §11.3.2 for `AdapterInventoryEntry` and `ExitCriterionEvidence`.
   - Update `adapter_inventory()` in `tests/contracts/pr2_20_reports.py` so `paperqa2` carries `status="DEFERRED"` (referencing `docs/proposals/B28_PaperQA2_Intake_Assessment_DRAFT.md`), and update `validate_exit` / `verified_acceptance` so Row 6 (`PaperQA2 Adapter`) validates as `"DEFERRED"` when backed by that disposition ref.
3. Update `tests/integration/phase2/test_pr2_20_security.py`,
   `tests/unit/phase2/test_pr2_20_evidence.py`,
   `tests/unit/phase2/test_pr2_20_exit_report.py`, and
   `tests/unit/phase2/test_pr2_20_inventory.py` to verify destination denial and B28 deferral.

#### Slice B31-S2 — Full Migration Chain (`0001`..`0068`) Clean/Upgrade/Hash Parity

4. Extend `tests/integration/phase2/test_pr2_20_migrations.py` and
   `tests/integration/phase2/test_pr2_20_catalog_plans.py`:
   - Add populated checkpoint upgrades across `0044_pr2_15_revision_action`,
     `0045_pr2_16_basic_approval`, `0046_pr2_17_authorship_preparation`,
     `0047_pr2_18_novelty_prior_art`, `0048_b04_manuscript_freeze`,
     `0049_b05_manuscript_review`, `0050_b01_resolution_admission`,
     `0053_b08_issue_disposition`, `0059_b13_grant_consumption`,
     `0064_b14_publication_ready`, and `0067_b17_prepared_package_freeze` to
     `0068_b21_unresolved_capture`, asserting manifest equality, reconnect readback, and
     exact `content_hash` parity.
   - Assert the §12.1 catalog constraints and absence of `ix_pr220_issue_open_blocking_review` (B29).
5. Update `tests/contracts/pr2_20_reports.py` so `migration_inventory_phase2.md` lists
   every revision from `0001_empty_bootstrap` through `0068_b21_unresolved_capture` (70
   revisions, closing the `0060`–`0064` table omission).

#### Slice B31-S3 — Extended Benchmarks & Multi-Worker Races

6. Extend `tests/integration/phase2/pr2_20_scaled.py`,
   `tests/integration/phase2/test_pr2_20_governance_races.py`,
   `tests/integration/phase2/test_pr2_20_novelty.py`, and
   `tests/e2e/test_pr2_20_benchmark.py`:
   - Remove `"Superseded manuscript history BLOCKED: owning lifecycle unavailable"` from
     `large_host_blockers` in `test_pr2_20_benchmark.py` and benchmark superseded B04
     manuscript trace (`ManuscriptFreezeService.freeze_manuscript_version` + `trace`).
   - Add benchmark cases and `1`/`4`-worker race profiles for RevisionAction & Issue
     disposition (`B06`–`B08`), Approval request/decision & grant consumption (`B09`–`B14`
     including `transition_publication_ready`), Authorship & PreparedSubmission (`B15`–`B17`
     at `concurrency in (1, 4)` including concurrent freeze vs consent withdrawal), and
     Novelty (`B18`/`B19` `CLOSE_PRIOR_ART_FOUND`/`B21` v2 unresolved capture/`B22`
     correction chains & `select_prior_art_relation`), asserting **B24** non-gating
     behavior.

#### Slice B31-S4 — Full E2E Inventory & Phase 2 Exit Artifacts

7. Once parallel inputs (`B02`, `B03`, `H2`, `B30-S3`) merge, update
   `scripts/pr2_20_verify.py` and `tests/contracts/pr2_20_reports.py` to execute and
   collect `OWNING_ACCEPTANCE` JSON records for the 18 active rows + `DEFERRED` for
   Row 6 (`PaperQA2 Adapter`), update the rendered `literature_trace_demo.md` and
   `publication_trace_demo.md` narratives through `READY` and `FROZEN` package, and
   regenerate all six `docs/phase2/*.md` deliverables and `docs/phase2/pr2_20_verification.md`.

### 12.4 Test files and required cases

| Test file | Slice | Required test cases |
| --- | --- | --- |
| `tests/unit/phase2/test_pr2_20_evidence.py` | S1 | All 57 `ErrorCode` mappings match `_STATUS` and `CLI_EXIT_CODES`; `AdapterInventoryEntry` and `ExitCriterionEvidence` accept `status="DEFERRED"` only under §11.3.2 predicates and reject invalid `DEFERRED` combinations. |
| `tests/unit/phase2/test_pr2_20_inventory.py` | S1 / S2 | `paperqa2` inventory entry has `mode="DEFERRED"`, `status="DEFERRED"`, `package_version=None`, and `paper-qa`/`paperqa` absent from `uv.lock`; `migration_inventory()` has all 70 revisions through `0068_b21_unresolved_capture`. |
| `tests/integration/phase2/test_pr2_20_security.py` | S1 | Replace `test_private_destination_protection_is_an_unresolved_finding` with `test_private_loopback_link_local_metadata_and_rebinding_destinations_denied` (new, proposed): test `127.0.0.1`, `::1`, `10.0.0.1`, `172.16.0.1`, `192.168.1.1`, `100.64.0.1`, `169.254.169.254`, `fe80::1`, `fc00::1`, `::ffff:127.0.0.1`, `0.0.0.0`, `ftp://`, URL userinfo, mixed public+private DNS answers, and DNS-rebinding (verifying socket connects to the resolved public IP and never dispatches to a private IP), recording `"status": "PASS"` in `security-findings`. |
| `tests/integration/phase2/test_pr2_20_catalog_plans.py` | S2 | Assert §12.1 constraints and deferred triggers across `0042`–`0068`; assert `ix_pr220_issue_open_blocking_review` is absent in canonical DB (B29). |
| `tests/integration/phase2/test_pr2_20_migrations.py` | S2 | Populated upgrade checkpoints from `0044`, `0045`, `0046`, `0047`, `0048`, `0049`, `0050`, `0053`, `0059`, `0064`, and `0067` to `0068_b21_unresolved_capture` preserve row manifests, foreign-key edges, and recomputed `content_hash` after `engine.dispose()` reconnect. |
| `tests/integration/phase2/test_pr2_20_governance_races.py` | S3 | Witnessed multi-connection race and rollback tests for `RevisionAction` (`record_revision_action`, `record_concern_re_review`), `record_issue_disposition`, `ApprovalService` (`request_approval`, `decide_approval`), and `SERIALIZABLE` single-grant consumption (`record_internal_scientific_release`, `transition_publication_ready`, `freeze_prepared_submission` vs `record_author_consent(WITHDRAWN)`). |
| `tests/integration/phase2/test_pr2_20_novelty.py` | S3 | Extend B18 parity with B19 `CLOSE_PRIOR_ART_FOUND` basis, B21 v2 `captured_unresolved_result_count` + `search_coverage_resolutions`, B22 `PriorArtRelation` correction chain + `select_prior_art_relation` (`EMPTY`, `UNIQUE`, `AMBIGUOUS`), and B24 non-gating verification across approval, `READY`, and package freeze. |
| `tests/e2e/test_pr2_20_benchmark.py` | S3 | `1`- and `4`-worker `BenchmarkProfile` generation for revision/disposition, approval/consumption/`READY`, authorship/package/consent/freeze, superseded manuscript trace, and B19/B21/B22 novelty; assert zero unexpected operation failures and lock-free `REPEATABLE READ` on all read cases. |
| `tests/unit/phase2/test_pr2_20_exit_report.py` & `tests/architecture/test_pr2_20_boundaries.py` | S1 / S4 | Verify 6 generated reports, 19 literal rows (Row 6 `DEFERRED` with B28 disposition ref, Rows 1–5 & 7–19 `PASS` when `OWNING_ACCEPTANCE` is attached, fail-closed `BLOCKED` when any row or P0/P1 is unresolved), and 13 mandatory architecture boundary tests. |

Focused verification commands after implementation of each slice (do not run the whole
test suite manually):

```sh
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest tests/unit/phase2/test_pr2_20_evidence.py tests/unit/phase2/test_pr2_20_exit_report.py tests/unit/phase2/test_pr2_20_inventory.py tests/architecture/test_pr2_20_boundaries.py
# With RB_TEST_ADMIN_URL pointing to a disposable local PostgreSQL 18 admin:
uv run pytest tests/integration/phase2/test_pr2_20_security.py tests/integration/phase2/test_pr2_20_catalog_plans.py tests/integration/phase2/test_pr2_20_migrations.py tests/integration/phase2/test_pr2_20_governance_races.py tests/integration/phase2/test_pr2_20_novelty.py tests/e2e/test_pr2_20_benchmark.py
```

### 12.5 Not in this slice

- Implementing `B02` (strategy candidate promotion), `B03` (discussion candidate
  promotion), `H2` (novelty lock-free command replay production change, B24 standalone
  regression file, B25/B27 closure), or `B30-S3` (their PR2-19 rows); those are parallel
  items listed as pending inputs in §2.2.
- Implementing `B20` (`NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE`), `B23` (novelty review/
  revision), `B32` (extra approval purposes), or `MANUSCRIPT_CHANGE` `RevisionAction`.
- Adding any database migration, table, column, trigger, or index (`ix_pr220_issue_open_blocking_review` is rejected per **B29**).
- Installing `paper-qa`/`paperqa` or making live network/LLM calls (**B28 = DEFERRED**).
- Gating approval, `READY` transition, or package freeze on novelty outcomes (**B24 = no novelty gate**).
- External venue submission, `SubmissionVersion`, `ExternalEffect`, or Phase 3 work.

---

## 13. Open questions for the owner — override register

None blocking slice authorization. All three owner decisions from 2026-10-19 (**B28 =
DEFERRED**, **B24 = no novelty gate**, **B29 = no partial index**) and the parallel
input boundary (**B02**, **B03**, **H2**, **B30-S3**) are incorporated in §§2–12:

| Decision ID | Default pinned in this draft | Owner override required if changed |
| --- | --- | --- |
| **D-B31-01 (Slice order)** | Execute `B31-S1` → `B31-S2` → `B31-S3` immediately upon authorization; execute `B31-S4` final exit artifact regeneration once `B02`, `B03`, `H2`, and `B30-S3` merge. | Owner may authorize `B31-S1`..`B31-S3` together or individually before `B31-S4`. |
| **D-B31-02 (B28 exit row status)** | Row 6 (`PaperQA2 Adapter`) uses `status="DEFERRED"` with `disposition_refs=("docs/proposals/B28_PaperQA2_Intake_Assessment_DRAFT.md",)` while Row 5 (`Scientific RAG Boundary`) requires `status="PASS"` via `FakeScientificRAGCapability`. | Explicit owner amendment if Row 6 should use a different literal status token. |
| **D-B31-03 (Unimplemented backlog exclusions)** | `NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE` (B20), novelty review/revision (B23), and `MANUSCRIPT_CHANGE` remain closed/denied as non-goals for Phase 2 exit. | Explicit owner scope expansion before `B31-S4`. |

---

## 14. Documentation verification note

### Identifier verification

On 2026-10-19, checked inline identifiers against `src/`, `migrations/`, `tests/`,
and `scripts/`, checked file paths against the repository inventory, and read the
owning declarations. The temporary identifier list contains the draft's inline
identifier tokens; each unmatched token was inspected, removed, or explicitly
marked **(new, proposed)**. Also compared DTO fields and qualified class/method
names with Python AST declarations. Grep commands run for this revision:

```sh
rg --files src migrations tests scripts docs
rg -n -w -F -f /private/tmp/b31-identifiers.txt src migrations tests scripts pyproject.toml uv.lock
rg -n 'CREATE (CONSTRAINT )?TRIGGER|CREATE (OR REPLACE )?FUNCTION|CREATE TABLE|ADD CONSTRAINT|DROP CONSTRAINT|CREATE UNIQUE INDEX' migrations/versions
rg -n 'class |def |^[[:space:]]+[a-z_]+:' src/researchbase/application
rg -n 'decision_concern' src migrations tests
rg -n 'lifecycle_status|placement_set_hash|content_hash|status VARCHAR' migrations/versions/0035_pr2_12_publication_draft.py migrations/versions/0048_b04_manuscript_freeze.py
```

For this checkout, the concern table is `decision_revision_concerns` and its
immutability trigger is `b07_decision_concern_immutable` (0052); those names come
from the migration rather than the review's suggested shorthand. Historical
constraint replacements are called out in §12.1. Proposed helper/test names are
marked at their use sites; pending B02/B03 work does not assert nonexistent names.

### Focused checks

Document audit verified 24 DTO declarations against their owning classes, all 57
error mappings against both adapters, and 52 named SQL constraints/indexes against
repository source. The status line matches the baseline. `git diff --check` exited
`0`; `git status --short` showed only this draft modified.

Runs used the existing repository environment read-only with
`V=/Users/fengwang/Documents/ResearchBaseProject/.venv/bin` and `PYTHONPATH=src`
for pytest. The full test suite was not run.

| Exact command (with `V` as above) | Observed result |
| --- | --- |
| `$V/ruff check .` | Exit `0`: `All checks passed!` |
| `$V/ruff format --check .` | Exit `0`: `736 files already formatted` |
| `$V/pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject` | Exit `0`: `0 errors, 0 warnings, 0 informations` |
| `PYTHONPATH=src $V/python -m pytest tests/unit/phase2/test_pr2_20_evidence.py tests/unit/phase2/test_pr2_20_exit_report.py tests/unit/phase2/test_pr2_20_inventory.py tests/architecture/test_pr2_20_boundaries.py tests/unit/phase2/test_pr2_19_report_contract.py tests/integration/phase2/test_pr2_19_dependencies.py` | Exit `0`: `143 passed in 4.57s` |
| `PYTHONPATH=src $V/python -m pytest tests/integration/phase2/test_pr2_20_security.py tests/integration/phase2/test_pr2_20_catalog_plans.py tests/integration/phase2/test_pr2_20_migrations.py tests/integration/phase2/test_pr2_20_governance_races.py tests/integration/phase2/test_pr2_20_novelty.py --tb=short` | Exit `1`: `13 failed, 2 passed, 34 errors in 1.25s`. `RB_TEST_ADMIN_URL` is unset; the two passing cases are offline security tests. No PostgreSQL assertions ran; this is not PostgreSQL acceptance evidence. |

Local PostgreSQL is `18.6`. Attempted `initdb -D /private/tmp/b31-pg.o0DK4m/data -A trust --no-locale`
and retried with `-c shared_memory_type=mmap`; both exited `1` because macOS
`shmget` reported `No space left on device` (shared-memory IDs/limits). No server
started and no existing cluster was changed. PostgreSQL verification remains
blocked by the local environment. Only this draft is changed; its status line is
preserved. No commit, push, or branch was created.

## 15. B31-S1 implementation evidence — 2026-10-20

Only S1 is implemented: destination validation and numeric peer pinning in the real
HTTP adapter, offline security regressions, and the owner-approved B28 deferral in
the typed adapter/exit inventories. HTTPS retains default certificate verification
and the original hostname for SNI; environment proxies and redirects are disabled.
The shared transport phase tests now stub DNS so their opener doubles remain fully
offline. No naming/location substitutions were needed. No migration, schema,
dependency, or transaction/lock protocol changes were made. S2–S4 and regeneration
of the six exit artifacts remain outside this slice.

Read-only sub-agent reviews found no P0/P1 issues. Their minor findings (two
explicit IPv6 cases and stale renderer wording) were corrected before final focused
verification. Real PaperQA2 remains absent; the fake remains the deterministic gate.

The default uv cache was inaccessible under the workspace sandbox. Commands used
the repository-local cache instead. All commands below exited 0:

| Exact command | Observed result |
| --- | --- |
| `UV_CACHE_DIR=.uv-cache uv run ruff check .` | `All checks passed!` |
| `UV_CACHE_DIR=.uv-cache uv run ruff format --check .` | `783 files already formatted` |
| `UV_CACHE_DIR=.uv-cache uv run pyright` | `0 errors, 0 warnings, 0 informations` |
| `UV_CACHE_DIR=.uv-cache uv run pytest tests/unit tests/architecture --tb=short` | `6195 passed, 55 warnings in 112.42s` |
| `UV_CACHE_DIR=.uv-cache uv run pytest tests/unit/phase2/test_pr2_20_evidence.py tests/unit/phase2/test_pr2_20_exit_report.py tests/unit/phase2/test_pr2_20_inventory.py tests/architecture/test_pr2_20_boundaries.py tests/unit/phase2/test_pr2_06_transport_boundary.py tests/unit/test_m2_crossref.py --tb=short` | `116 passed in 10.35s` |
| `UV_CACHE_DIR=.uv-cache uv run pytest tests/integration/phase2/test_pr2_20_security.py --tb=short` | `48 passed, 20 warnings in 12.44s` |

The final focused unit run includes the explicit 57-row B31 error-mapping test added
after the broader run collected its tests. The PostgreSQL/security run used the
inherited `RB_TEST_ADMIN_URL` with local PostgreSQL 18.6 and disposable test databases.
Warnings were Alembic's existing `path_separator` deprecation and, in the broader
run, an existing SQLAlchemy isolation-option warning. No full test suite was run;
no commit, push, or branch was created.

### 15.1 Full-suite findings and director fix

Round 1's sharded full run had one temporal-wait failure and one B08 fixture error;
both node IDs passed when rerun together on this tree, so they are recorded as
load-dependent flakiness, not S1 regressions. Round 2's sharded full run completed
all six shards: 12026 passed, 67 skipped, 16 errors. All 16 errors were
`fixture 'novelty_transports' not found` in
`tests/unit/phase2/test_b22_prior_art_transports.py`. Cause (pre-existing, not S1):
B20 and B22 loaded the fixture through `pytest_plugins` naming the test module
`test_pr2_18_transports.py`; when that module is collected first in the same run,
the later modules lose the fixture. It reproduced with
`pytest tests/unit/phase2/test_pr2_18_transports.py tests/unit/phase2/test_b22_prior_art_transports.py`
(41 passed, 16 errors). Fix: `tests/unit/phase2/conftest.py` re-exports the fixture
and the two `pytest_plugins` lines are removed. Afterwards the three files pass in
both collection orders (129 passed each) and `pytest tests/unit/phase2` reports
4936 passed. Other test modules still use the same `pytest_plugins` pattern; they
are a separate follow-up.

Open P2 review items, accepted for this slice and tracked as follow-ups:
`_resolve_public_peer` pins the first validated DNS answer with no fallback across
the other validated answers, and each timed-out DNS lookup leaves one daemon thread.
