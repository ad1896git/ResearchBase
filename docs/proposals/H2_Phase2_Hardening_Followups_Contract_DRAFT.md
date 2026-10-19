# Phase 2 Hardening Follow-ups and B24 Disposition (H2) — DRAFT

**Status: APPROVED by owner 2026-10-19 — first slice authorized for implementation**

## Start here (for the implementer)

H2 collects the remaining hardening work without adding tables or scientific
workflow. This task writes only this contract. Contract approval and implementation
authorization are separate. B24's proposed owner disposition is **no novelty
publication/governance gate**; this draft does not claim that approval has happened.

Build after separate authorization, in this order:

1. Inventory retained evidence and its consumers; specify recoverable summaries
   before removing any large file (§§3, 11.3, 12.3).
2. Measure the unchanged approval/Decision inventories under the PR2-20 profile.
   Keep every existing lock unless a separately reviewed candidate proves equivalent
   protection and measurable benefit (§§7, 12.2).
3. Verify the installed revision guard and historical upgrade path. The 0044
   mismatch is already superseded at current head; add regression evidence before
   deciding whether any forward fix is necessary (§12.1).
4. Audit B04 writer composition and test connection bounds plus local bounds;
   `SET LOCAL` cannot bound an earlier first-statement lock (§11.1).
5. Add one parametrized PostgreSQL test proving novelty outcomes never determine
   approval, READY or package freeze. Keep every independent scientific, review,
   authority and consent gate (§12.4).
6. Record focused results, attach the loop's full-suite evidence separately,
   obtain review and stop. This is not Phase 2 exit or Phase 3 GO (§9).

Read §1 for authority, §10 for terminology, §11 for fixed draft decisions and
§12 for the build guide. The five review failures are: losing required evidence;
narrowing locks without proof; rewriting accepted migrations; introducing novelty
as permission; and calling unrun/blocked checks PASS. Reads use one REPEATABLE
READ, READ ONLY snapshot with no explicit table, advisory or row locks.

## 1. Purpose, authority and inspected baseline

| Source | Requirement used here |
| --- | --- |
| [System Architecture 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), scientific principles; [Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A18–A23 | Deterministic facts precede authority; frozen exact history; focused later corrections take precedence. |
| [Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md); [Cross-phase 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md) | Existing owners, typed references, additive compatibility and stable transports; no new canonical concept. |
| [Phase 2 Specification 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §§44–46, PR2-20, exit criteria; [Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), novelty registry | Hardening evidence and PostgreSQL acceptance; NoveltyAssessment is bounded, immutable assessment, not proof of universal priority. |
| [Governance R2 17](../architecture/17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md); [R3 18](../architecture/18_Phase2_Design_R3_Targeted_Remediation_v1.0.md); [Temporal R4 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md), TEMP-AUTH-01 | Independent approval/consent and atomic consumption; fresh `clock_timestamp()` authorization after waits, including deferred checks. |
| [Harness Integration 09](../harness/09_Harness_Integration_Specification_v1.0.md), §§18–21 | Evidence before completion; reports do not grant scientific authority. |
| [PR2-17](PR2-17_Submission_Authorship_Contract_DRAFT.md), [PR2-18](PR2-18_Novelty_PriorArt_Contract_DRAFT.md), [PR2-20](PR2-20_Hardening_Plan_DRAFT.md) | Structure and owning contracts; refresh older baseline observations against current code. |

Current evidence is [handoff §§3–4](../handsoff.md), the
[hardening integration notes](../verification/hardening-2026-10-16/README.md),
[B04 remediation](../phase2/B04-review-remediation.md), and
[PR2-20 verification](../phase2/pr2_20_verification.md). Their historical counts,
head numbers and dispositions are not current acceptance assertions.
The [exit report](../phase2/phase2_exit_report.md) remains explicitly BLOCKED.
The user-supplied H2 backlog is the source of the five requested follow-ups and
B24 disposition; no B24 implementation approval is inferred from file presence.

Code inspection establishes these narrower facts:

- [DecisionService._record_once](../../src/researchbase/application/decision.py)
  now uses the approval SHARE prefix before request/scope/target locks. The
  legacy `_SNAPSHOT_TABLES` in
  [decision_repository.py](../../src/researchbase/persistence/decision_repository.py)
  remains imported by RevisionAction; its size is not every Decision's live inventory.
- [approval_repository.py](../../src/researchbase/persistence/approval_repository.py)
  pins B09/B13 inventories and a distinct Publication SHARE ROW EXCLUSIVE branch.
  The backlog's “28–46 tables” is a historical range, not a measured current count.
- [novelty_repository.py](../../src/researchbase/persistence/novelty_repository.py)
  `prepare` locks N first for all three writes; its older target-before-N draft
  sequence is superseded. [B27 evidence](../verification/b27/implementation_2026-10-17.md)
  records the correction.
- [0044](../../migrations/versions/0044_pr2_15_revision_action.py) locks the old
  scientific target FOR UPDATE; [0041](../../migrations/versions/0041_pr2_15_review_coordination.py)
  distinguishes target kinds, including Claim FOR SHARE and conclusion FOR UPDATE.
  [0051](../../migrations/versions/0051_b06_revision_action.py) and
  [0052](../../migrations/versions/0052_b07_revision_decisions.py) replace the revision
  guard with inventory protection, review/Issue SHARE and predecessor UPDATE.
  Historical mismatch alone is not an open current-head defect.
- [database.py](../../src/researchbase/persistence/database.py) exposes
  `b04_write_timeouts: bool = False`; the opted-in connection has 10s/30s bounds.
  [manuscript_freeze_repository.py](../../src/researchbase/persistence/manuscript_freeze_repository.py)
  still takes B04 SHARE first, then SET LOCAL 10s/30s.

## 2. Proposed scope and non-goals

Five work items: evidence compaction, measured lock review, revision-guard
alignment verification, B04 timeout consistency, and B24 non-gating regression.
§11.1 also records adjacent unresolved work without implementing its owning slice.
No public command, database table, new dependency or persistence mechanism.
Measurement and regression coverage can close an item without a production change.

## 3. Invariants and evidence boundaries

Compaction must preserve the subject revision and dirty-diff digest, command and
sanitized environment/profile, exit code, exact counts, failed/error/skipped node
IDs, blockers, timing and required migration/lock witnesses. Preserve both failed
attempts and later successful reruns. A hash proves byte identity, not execution,
availability or acceptance.

Before removing a blob, inventory every Markdown link, parser, test and report
that consumes it. Commit a bounded summary and original byte count/SHA-256;
retain original bytes in an already supported retained evidence destination, or
leave the blob in place marked BLOCKED. For previously committed bytes an exact
Git revision plus repository-relative path is acceptable only after testing
`git show <revision>:<path>` and hash recovery in a fresh checkout with retained
history. Do not rely on an uncommitted tmp directory, a disappearing CI run or
an unreachable Git object. Do not rewrite Git history. Redact before retaining
new evidence; a secret's hash is not a substitute for removing secret exposure.

Use existing file evidence helpers in
[tests/contracts/pr2_20_evidence.py](../../tests/contracts/pr2_20_evidence.py) and
[pr2_20_reports.py](../../tests/contracts/pr2_20_reports.py), not ArtifactStore or
canonical scientific persistence for engineering logs. Required raw SQL plans,
Junit reconciliation, catalog manifests and witnessed lock records stay recoverable.
Scientific records, hashes and frozen manifests are never compacted by H2.

## 4. Proposed commands, DTOs and historical readback

No Application/API/CLI DTO changes. Existing commands and historical replay keep
their own types, limits, hashes and entitlement checks. §11.3 defines a proposed
file-only compaction inventory, not a public endpoint or new report authority.
Report generation uses existing PR2-20 entry points in
[scripts/pr2_20_verify.py](../../scripts/pr2_20_verify.py); do not add a product command.

## 5. Persistence/schema proposal — no migration

No DDL is proposed for the first H2 slice. The current guard supersession must be
proved from the installed catalog and tested upgrades. Any discovered remaining
defect needs a separately authorized forward migration against the actual head;
§12.1 fixes its permitted boundary. No historical migration edits or startup DDL.

## 6. Error contract — existing categories only

No H2 error code. File validation failures stay evidence-tool validation failures;
they must not be presented as successful product operations. Product errors stay
as mapped in §11.2. A novelty outcome never creates APPROVAL_GATE_FAILED or
APPROVAL_TARGET_STALE by itself. An actual independently recorded blocking Issue
or invalid scientific dependency still fails through the existing gate.

## 7. Transactions, concurrency and failure recovery

Retain first-statement inventory locks for snapshot-consistent READ COMMITTED
writes. Pre-BEGIN connection configuration can bound that first wait; no SELECT,
authorization or SET LOCAL may precede the first transactional lock. Keep existing
SERIALIZABLE consumption/freeze exceptions (§12.2); H2 does not lower isolation.
No lock upgrades or helpers that quietly lock during reads.

Measure unchanged inventories first, using
[PR2-20 §12.2](PR2-20_Hardening_Plan_DRAFT.md#122-benchmark-defaults--owner-adjustable):
seed 2202026, the declared source/scientific envelopes, five warm-ups and 100
measured calls per worker, concurrency 1 and 4, three repetitions on the matching
reference host. Add approval request/decision and independent/same-target writers
using existing legal fixtures. Record first-write, replay, denied and contended
cases separately, full latency samples, nearest-rank p50/p95, throughput, lock-wait
duration, table names/modes/counts, backend PIDs, blockers and SQLSTATE counts.
Capture PostgreSQL version, isolation and lock capacity. No matching host means
BLOCKED profile evidence; local small runs are informational.

For each candidate removed table, enumerate every consulted fact, its owner and
all writers, including INSERT/empty-range phantoms, raw normal-role SQL and trigger
paths. Prove replacement exclusion using existing mechanisms, both commit orders,
complete-basis/hash/DTO/error parity, expiry after each wait and zero partial effects.
Retain the inventory if protection or benefit is unproven. Use PR2-20's 10%
regression/15% noise classifications, not an invented latency SLA for approval.
Do not retry benchmark failures into favorable samples. Preserve each command's
retry policy: at most three whole attempts where already supported for 40001/40P01;
no new timeout, business-conflict or uncertain-commit retry.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

§12.4 pins cases and files. Tests must observe real PostgreSQL 18 waits/catalogs,
not merely sleeps or mock SQL ordering. Every evidence helper writes under
`tmp_path`; installed functions and deferred commit guards must be exercised as
well as Python paths. No future test described here ran as part of drafting.

## 9. Acceptance criteria and evidence boundary

Close each item separately: recoverable compact evidence; a measured retain/narrow
decision; installed revision alignment and upgrade coverage; bounded first B04
wait with no timeout leakage; and B24 non-gating test plus owner disposition.
No open P0/P1 permits gate success. The loop owns the full suite; attach its exact
subject and results without claiming this drafting agent ran it. Dedicated-load,
retained-host and owner decisions can remain BLOCKED independently of focused tests.
STOP after the authorized slice; no Phase 2 exit or Phase 3 activation is implied.

## 10. Glossary

| Term | Meaning |
| --- | --- |
| H2 / B24 | This hardening backlog contract / proposed novelty non-gating disposition. |
| Inventory / N | Literal ordered table names in the named repository constant; expand the constant from the execution subject, never reconstruct it from an old count. |
| SHARE / SHARE ROW EXCLUSIVE | Existing PostgreSQL table modes; the latter coordinates writable Publication/package scopes without a later upgrade. |
| FOR SHARE / FOR UPDATE | Explicit row locks, forbidden on read paths. Ordinary SELECT ACCESS SHARE is implicit and permitted. |
| UoW / RR | One Application transaction / REPEATABLE READ snapshot. |
| Guard / deferred check | Installed trigger function / commit-time constraint check, such as 0042's complete-basis triggers. |
| Summary / hash / locator | Human-readable result / SHA-256 of exact retained bytes / reproducible way to retrieve those bytes. None alone proves acceptance. |
| Novelty outcome | Coverage-bounded literature judgment; neither publication permission nor governance authority. |

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

| Item | Smallest action and closure condition |
| --- | --- |
| H2-a evidence bloat | Inventory `docs/verification/task12/*/partition.json`, `docs/verification/task14/` and large `pr_evidence/` text first. Summarize/hash/recover before removing; update consumers and test fresh-checkout recovery. Do not recompute old evidence as if it were the original run. |
| H2-b wide locks | Measure live constants and call paths, including the B09 46-table prefix and its deciding branch. Propose narrowing only with §7 proof; retaining locks is an acceptable disposition. No removal merely because a table is absent from one favorable trace. |
| H2-c 0044/0041 | Already superseded by 0051/0052 at code level. Add installed-function and historical-upgrade tests; preserve target-specific review coordination. Do not replace every UPDATE with SHARE or edit 0044. |
| H2-d B04 timeouts | Keep `b04_write_timeouts=True` on B04 writer engines and SET LOCAL 10s/30s after first SHARE. Audit all actual writer factory wiring; fix only missing opt-ins after authorization. Prove ordinary/read engines retain defaults and pool reuse does not leak task-specific settings. |
| H2-e B24 owner disposition | Propose **no novelty publication/governance gate**. Absence and every admitted outcome leave permission unchanged when independent prerequisites are identical. No novelty-required approval condition, READY check, package manifest item, new error or table. |
| Additional: lock capacity/flaky timing | Handoff §3.1 records lock-table exhaustion and fixed-window flakes. Record actual `max_locks_per_transaction` and concurrency; use observed waits/events in affected tests. Do not change server configuration or weaken assertions under this contract. |
| Additional: temporary evidence | Hardening notes and `tests/conftest.py` already redirect PR2-20 observations. Preserve that fix and test zero new repository evidence directories; this is regression work, not another storage mechanism. |
| Additional: exit/intake/status debt | PR2-20 verification/exit report retain missing owner subjects, real PaperQA2 intake, reference-host evidence and an open P1 transport-destination finding. Revalidate each against the execution subject and link owning evidence; H2 does not waive or implement these items. |
| Additional: provisional mappings | [REVIEW-AQ-001](../../planning/REVIEW_ERROR_MAPPING_ARCHITECTURE_QUESTION.md) remains the owner route for provisional review errors. Preserve current mappings pending explicit architecture disposition. |
| Additional: migration/head hygiene | Handoff records lane-number collisions; hardening notes retain XID-safe function replacements. Inspect the actual single head and installed definitions, preserve historical digests and downgrade guards; do not pin a stale head number from old reports. |

### 11.2 Pinned error mappings

These are current values in [api/errors.py](../../src/researchbase/api/errors.py)
and [cli/errors.py](../../src/researchbase/cli/errors.py), not new H2 mappings.

| Existing code | HTTP | CLI exit | Relevant use |
| --- | ---: | ---: | --- |
| VALIDATION_ERROR | 422 | 2 | Malformed existing command. |
| AUTHENTICATION_REQUIRED | 401 | 3 | Missing authentication. |
| FORBIDDEN | 403 | 3 | Current entitlement absent. |
| NOT_FOUND | 404 | 3 | Authorized exact lookup absent. |
| CONFLICT_OF_INTEREST | 403 | 3 | Existing provisional independence mapping. |
| REVIEW_TARGET_NOT_FROZEN | 409 | 4 | Existing provisional review mapping. |
| APPROVAL_GATE_FAILED, DECISION_BASIS_INVALID, APPROVAL_TARGET_STALE | 409 | 4 | Independent existing gates; never inferred solely from novelty. |
| APPROVAL_PURPOSE_TARGET_COMMAND_INVALID, GRANT_INVALID, GRANT_STALE | 409 | 4 | Existing tuple and grant conditions. |
| CONCURRENT_MODIFICATION, IDEMPOTENCY_CONFLICT | 409 | 4 | Existing scoped concurrency/material conflict handling. |
| INVALID_STATE_TRANSITION, IMMUTABLE_RECORD, VERSION_NOT_FROZEN | 409 | 4 | Existing lifecycle/history checks. |
| FROZEN_REFERENCE_REQUIRED, PROVENANCE_CLOSURE_VIOLATION, REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Existing provenance categories. |
| INTERNAL_ERROR (transport fallback, not ErrorCode) | 500 | 1 | Unexpected error; sanitize details, do not invent a product success. |

This table does not remap SQLSTATEs globally: UoW opt-in normalizers in
[uow.py](../../src/researchbase/persistence/uow.py) determine each command's
category/retryability. B04 tests already distinguish lock/query timeouts from
serialization/deadlock. Preserve those distinctions.

### 11.3 DTO fields, Python types, limits and enums

No new product DTO. Proposed file-only compaction entries use a closed frozen
dataclass in `tests/contracts/pr2_20_evidence.py`, validated with existing helpers:

| Field | Python type / bound |
| --- | --- |
| `schema_version` | `Literal[1]`. |
| `subject_revision`, `dirty_diff_sha256` | `str`: exact Git subject / 64 lowercase hex SHA-256; retain the existing EvidenceRecord validation. |
| `status`, `reason`, `evidence_refs` | Existing `Result`, `str \| None`, `tuple[str, ...]`; PASS/FAIL/BLOCKED/NOT RUN/DEFERRED exactly. Non-PASS requires explanation. |
| `original_path`, `retained_path`, `retained_revision` | `str`: normalized repository-relative paths, max 1,024 characters; exact recoverable revision max 128. Reject absolute paths, traversal and credentials. Original paths may be outside PR2-20; never relax existing EvidenceRef subject-prefix checks. |
| `original_bytes`, `retained_bytes` | Strict `int >= 0`, excluding bool; compressed and original lengths separately. |
| `original_sha256`, `retained_sha256` | `str`, exactly 64 lowercase hex; verify original digest after decompression where applicable. |
| `summary` | Nonblank NFC UTF-8 `str`, max 16,000 characters, sanitized; link exact commands/count records instead of truncating them. |

Retain existing helper ceilings: at most 10,000 array entries, 1 MiB per structured
file. Partition deterministically when needed; never drop failures or samples to
fit a cap. Do not silently change existing report schemas/subject hashing or
reinterpret old partition files. This schema is proposed engineering metadata,
not stored JSON in the semantic core.

B24 tests use the exact [domain NoveltyOutcome](../../src/researchbase/domain/novelty.py)
values `INCONCLUSIVE`, `CLOSE_PRIOR_ART_FOUND`,
`NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE`, plus absence as a test fixture case, not a
fourth enum. No stronger outcome is synthesized for material versions that do
not admit it. Existing command DTO limits remain unchanged.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

```sql
-- First H2 slice: empty DDL. No CREATE TABLE, column, index or constraint change.
-- Inspect pg_get_functiondef('pr215_revision_guard()'::regprocedure) at head.
-- revision_actions.id, review_issue_id, supersedes_revision_action_id are UUID;
-- content_hash is CHAR(64), hash_scheme VARCHAR(32), created_at TIMESTAMPTZ.
-- Preserve existing keys and revision_action_shape CHECK,
-- uq_revision_action_predecessor unique partial index and revision_action_guard.
-- Preserve 0042 constraint triggers: pr215_complete_decision,
-- pr215_complete_conclusion, pr215_complete_review:
-- AFTER INSERT ... DEFERRABLE INITIALLY DEFERRED, FOR EACH ROW.
```

The current guard body is supplied by 0052, not the original 0044 body. Compare
installed SQL and function/trigger attributes after clean install, populated
0044→head upgrade and reconnect; include 0051/0052 checkpoints. If a defect remains,
return for authorization of a forward `CREATE OR REPLACE FUNCTION
pr215_revision_guard() RETURNS trigger LANGUAGE plpgsql` preserving current
validators, hash checks, SQLSTATEs, names and immutable history. No function
replacement is proposed now. Reuse 0042-style deferred constraint triggers only
if an approved fix actually needs a commit-time completeness check; H2 adds none.

### 12.2 Exact lock order and transactions

Expand named constants literally from the execution subject and capture actual
SQL in tests. They specify exact inventories/order; historical table counts do
not. Configuration before driver BEGIN is outside the transactional sequence.
No helper may precede these first locks with a query.

| Command/path | Existing sequence to retain |
| --- | --- |
| `record_decision` (internal release) | READ COMMITTED configured by UoW → B09_SHARE_SQL first → local bounds → `pr215:decision:{id}` advisory → `pr216:scope:{project}:{purpose}` advisory → exact conclusion version FOR UPDATE → protected reads/authorization/basis writes. See `application/decision.py::_record_once`. |
| Approval request | READ COMMITTED → B09_SHARE_SQL first → local bounds → `pr216:uuid:{id}` advisory → routing read → scope advisory → exact target FOR UPDATE → manuscript Publication FOR SHARE if applicable → authorization, sealed basis, writes. |
| Approval decision | READ COMMITTED → B09_DECIDE_SHARE_SQL first (excludes publications) → publications SHARE ROW EXCLUSIVE → local bounds → UUID advisory → routing read → scope advisory → exact target FOR UPDATE → manuscript Publication FOR SHARE if applicable → saved request FOR UPDATE → affected grants UUID-sorted FOR UPDATE before updates/events. See `approval.py::_once` and repository `lock_affected_grants`. |
| Manuscript readiness / preparation Decision | READ COMMITTED → B11_SHARE_SQL first → local bounds → `b11:decision:{id}` / `b12:decision:{id}` advisory respectively → manuscript FOR UPDATE → project FOR SHARE → Publication FOR SHARE → basis reads/writes. Both branches use `decision_repository.py::prepare_readiness_write`. |
| RevisionAction | READ COMMITTED with pre-BEGIN bounds → REVISION_SNAPSHOT_TABLES SHARE first → local bounds/request advisory → protected reads → review then Issue FOR SHARE → predecessor FOR UPDATE if present → insert/deferred validation. Current B06/B07 paths do not take scientific-target FOR UPDATE; preserve this distinction. |
| Novelty coverage / prior-art / assessment | READ COMMITTED → N SHARE first → local bounds → `pr218:{kind}:{id}` advisory → ClaimVersion FOR UPDATE for prior-art/assessment only → protected basis reads → predecessor FOR UPDATE when superseding → writes/deferred checks. Coverage has no Claim row lock. |
| B04 manuscript freeze | READ COMMITTED with opted-in connection bounds → B04_SHARE_SQL first → local bounds → project coordination → Publication FOR UPDATE → exact manuscript FOR UPDATE → closure/readback/writes. |
| B13 release / READY consumption | SERIALIZABLE → B13_SHARE_SQL first → publications SHARE ROW EXCLUSIVE → B13_APPROVAL_SQL SHARE → local bounds → `b13:consume:{command_key}` advisory → routing reads → purpose scope advisory → target FOR UPDATE → owning conclusion FOR SHARE or Publication FOR UPDATE → request FOR SHARE → grant FOR UPDATE → gates/effect/receipt/events atomically. |
| B17 package freeze | SERIALIZABLE with pre-BEGIN bounds → B17_SHARE_SQL first → publications SHARE ROW EXCLUSIVE → prepared_submission_versions SHARE ROW EXCLUSIVE → approval_decisions, approval_request_reviews, approval_requests SHARE → local bounds → consume-key advisory → routing/authorization → PREPARE_SUBMISSION scope advisory → manuscript, Publication, package FOR UPDATE → older frozen packages UUID-sorted FOR UPDATE → author consent-chain advisories in actor-UUID order → request FOR SHARE → grant FOR UPDATE → complete gates/freeze/receipt/events. See `prepared_submission.py::freeze_prepared_submission`. |
| Exact reads / read-only completed replay | One REPEATABLE READ, READ ONLY snapshot before authorization; plain reads and final fresh entitlement check. No explicit table, advisory or row lock, write or status maintenance, including nested verifiers. Approval and internal-release Decision writers detecting saved material close before reopening the read UoW. RevisionAction command replay retains its existing SHARE-first writer sequence above; it is not an exact-read query. |

After every required wait, reread protected state and use fresh DB time, including
commit-time checks. This table describes commands exercised by H2, not permission
to refactor other writers. The file-only compactor takes no database locks.

### 12.3 Ordered build steps and module paths

1. Freeze the authorized subject, actual Alembic head and source constants. Read
   `docs/handsoff.md`, hardening notes and `docs/phase2/pr2_20_verification.md`;
   reconcile existing owner blockers rather than copying old status as current.
2. Extend `tests/contracts/pr2_20_evidence.py` and
   `tests/contracts/pr2_20_reports.py` with closed compaction metadata/recovery
   checks; update `scripts/pr2_20_verify.py` only as needed for explicit report
   generation. Add tests before replacing large artifacts in the three §11.1
   paths. Update every consumer link; keep necessary originals when blocked.
3. Extend `tests/integration/phase2/pr2_20_support.py`,
   `tests/integration/phase2/pr2_20_scaled.py` and
   `tests/e2e/test_pr2_20_benchmark.py` for passive lock observations and approval
   cases. Use existing service boundaries and disposable PostgreSQL helpers.
   Write the retained/narrowing recommendation in PR2-20 evidence, with no query
   or lock change until independently justified and separately authorized.
4. Extend `tests/integration/phase2/test_revision_action.py` and
   `test_b06_revision_concurrency.py` for installed guard/upgrade assertions.
   Inspect `revision_action_repository.py`, `uow.py` and migrations 0041/0044/
   0051/0052. If the current supersession passes, close H2-c with no migration.
5. Audit composition in `src/researchbase/api/app.py`,
   `src/researchbase/cli/composition.py`, `database.py` and `manuscript_freeze_repository.py`.
   These current shared bundles do not instantiate ManuscriptFreezeService;
   do not add an unrequested transport merely to attach its timeout option.
   Preserve opt-in scope; change only proven missing writer wiring, with the
   existing `test_b04_manuscript_contract.py` and real first-wait regressions.
6. Add the B24 case to `tests/integration/phase2/test_pr2_20_novelty.py`, reusing
   `b18_novelty_support.py`, B14 READY fixtures and `b17_fixtures.py`. Exercise
   actual application commands; do not fabricate permission by direct SQL.
7. Run §12.4 focused checks; retain exact command/result evidence compactly.
   Review specs + diff + results, attach the loop's full-suite evidence, obtain
   owner dispositions and stop. No commit/push/branch action is part of drafting.

### 12.4 Test artifacts and required cases

All additions below are future work; existing suites supply baseline evidence only.

| File | Required cases |
| --- | --- |
| `tests/unit/phase2/test_pr2_20_evidence.py` | Summary/hash round trip, exact bytes including compressed recovery, corrupted/missing locator refusal, strict fields/bounds, redaction, deterministic partitioning; retain all failed/error/skipped IDs and counts. Fresh checkout recovery of every removed original; broken consumers deny compaction. Existing tmp_path test proves zero new repository subject directories. |
| `tests/unit/phase2/test_pr2_20_exit_report.py`, `tests/architecture/test_pr2_20_boundaries.py` | Summary status cannot promote BLOCKED/NOT RUN/FAIL to PASS; report generation adds no canonical state/dependencies and preserves required report rows. |
| `tests/e2e/test_pr2_20_benchmark.py` | Exact PR2-20 reference profile/sampling plus approval cases; passive pg_locks observations, per-command inventories, waits/SQLSTATEs, comparable repetitions and noise classification. Opt-in skip remains NOT RUN, not a measured lock improvement. |
| `tests/integration/phase2/test_pr2_20_governance_races.py`, `test_b09_approval_concurrency.py`, `test_b14r_ready_approval_races.py` | Capture FIRST SQL and exact per-command mode/order; both writer commit orders, zero-row phantoms, authority/source/review/Issue changes, fresh expiry checks, same/different targets, rollback and replay. Any narrowed candidate must pass unchanged DTO/hash/error/basis results; no hidden lock on exact reads. |
| `tests/integration/phase2/test_revision_action.py`, `test_b06_revision_concurrency.py` | Catalog body/trigger attributes at actual head, clean and populated 0044→0051→0052→head upgrades/reconnect, unchanged historical records/digests; normal-role direct SQL guards; review/Issue SHARE and predecessor-only UPDATE; raw owning writers and both wait orders. Keep existing first-inventory/no-scientific-row-lock test. |
| `tests/unit/phase2/test_b04_manuscript_contract.py`, `tests/integration/phase2/test_b04_manuscript_races.py` | Existing opt-in-engine test plus all production writer compositions; first SHARE blocks with bounded connection settings, SET LOCAL follows it; timeout/rollback and pool checkout retain expected settings; ordinary/read engine defaults unchanged; credential and scheduled-role expiry after wait denies with zero effects. |
| `tests/integration/phase2/test_pr2_20_novelty.py` | Add **one parametrized test** `test_novelty_outcomes_never_gate_approval_ready_or_package_freeze`: absence plus all three admitted outcomes, with legal material/basis per outcome. For otherwise equivalent valid fixtures, create actual approval/grant, consume READY, then separately approve preparation and freeze package; all succeed for every novelty case. Compare normalized results excluding fresh IDs/timestamps, frozen scientific hashes and receipt counts. Add independent blocker/invalid-fact controls across the same novelty cases: each still denies, with zero transition/freeze/receipt/consumption. Record a real BLOCKING Issue of novelty type only as an independent Issue control; an unfavorable novelty outcome alone must never create one or deny. Assert novelty hashes/rows unchanged and no novelty outcome enters permission material. |
| `tests/integration/phase2/test_b17_package_freeze.py`, `test_b13_grant_consumption.py` | Run existing consent, invalid-science, sealed-basis, exact-tuple and single-use regressions with B24 coverage. Neither favorable novelty nor missing novelty bypasses any required gate. |

Focused implementation commands: `uv run ruff format --check .`,
`uv run ruff check .`, `uv run pyright`,
`uv run pytest tests/unit tests/architecture tests/test_architecture.py`, and
`uv run pytest` with the explicit integration paths above on disposable
PostgreSQL 18. Run the declared benchmark separately with
`RB_PR220_BENCHMARK=1 uv run pytest tests/e2e/test_pr2_20_benchmark.py` on its matching
host. Do not run the whole suite in the authoring lane; the loop supplies it.

### 12.5 Not in this slice

New tables, product DTOs/errors/enums, novelty publication/governance gates,
novelty-driven grant staleness, new approval conditions, scientific history
pruning/rehashing, migration rewrites, unmeasured inventory narrowing, new lock
or persistence frameworks, automatic server tuning, live provider intake fixes,
transport-destination remediation, retained deployment acceptance, external send,
Phase 2 exit declaration and Phase 3 runtime.

## 13. Open questions for the owner — override register

Approve or reject the proposed B24 no-gate disposition and H2's measurement-first
scope. Confirm retained Git history or another already supported evidence
destination before compaction; missing recovery keeps the file. Confirm reference
host availability and attach current owning dispositions for PR2-20 blockers.
No answer is inferred from elapsed time, test success or this draft's existence.

## 14. Documentation verification note

Only this draft is changed (2026-10-19). Commands ran from the repository root,
using the existing locked environment with
`UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv`,
`UV_CACHE_DIR=/private/tmp/h2-uv-cache`, and `uv run --no-sync --offline`.
Pytest additionally used `PYTHONPATH=src` and the explicit local
`RB_TEST_ADMIN_URL` documented in the handoff (credentials omitted here).

| Exact tool command after the common environment prefix | Observed result |
| --- | --- |
| `uv run --no-sync --offline ruff format --check .` | Exit 0; 736 files already formatted. |
| `uv run --no-sync --offline ruff check .` | Exit 0; all checks passed. |
| `uv run --no-sync --offline pyright` | Exit 0; 0 errors, 0 warnings, 0 informations. |
| `uv run --no-sync --offline pytest -o addopts='' -q --tb=short tests/unit tests/architecture tests/test_architecture.py` | Exit 1; **5631 passed, 4 failed, 14 errors**, 9 warnings, 59.33s. Four `test_hg1_runner.py` socket-bind failures are PermissionError; all 14 `test_pr2_19_boundaries.py` setup errors are denied PostgreSQL connections. No skips reported. |
| `uv run --no-sync --offline pytest -o addopts='' -q --tb=short tests/integration/phase2/test_b06_revision_concurrency.py tests/integration/phase2/test_b04_manuscript_races.py tests/integration/phase2/test_pr2_20_novelty.py tests/integration/phase2/test_pr2_20_governance_races.py` | Exit 1; **51 setup errors**, 4.73s; localhost PostgreSQL connections fail with Operation not permitted. No database assertions passed. |
| `git diff --check` | Exit 0. The new untracked draft was also checked directly for trailing whitespace. |

Direct Python checks resolved **38 local links**, **22 full Python paths** and
all 14 numbered sections; AST comparison confirmed **20 ErrorCode HTTP/CLI
pairs** against current adapters. The separate INTERNAL_ERROR fallback was
inspected in source. Preliminary setup attempts failed on the empty offline uv
cache and local environment resolution; a temporary environment-link experiment
also caused evidence-walker failures (11 failed, 5624 passed, 14 errors). Those
results were not passes; correcting the local environment produced the final
results above. No dependency or tracked configuration changed.

The full suite and dedicated reference-host benchmark were **NOT RUN** by this
agent. The loop's later full-suite output is separate evidence. None of these
checks establishes future H2 implementation acceptance, B24 owner approval or
Phase 2 exit.
