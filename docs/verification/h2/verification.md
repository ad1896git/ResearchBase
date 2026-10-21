# H2 first-slice implementation evidence — 2026-10-19

Owner authorization: H2 first slice and B24 no publication/governance novelty gate.
The contract status now records that authorization. This is focused engineering
verification, not Phase 2 exit, reference-host acceptance, or Phase 3 GO.

## Implementation and dispositions

- **H2-a:** [inventory](retained-originals-000.json) records 136 original files,
  17,005,236 bytes, SHA-256 values and literal Markdown/parser/report consumers.
  Every original remains present. Dynamic consumer review and retained-history
  approval remain **BLOCKED**; no evidence was removed, recomputed, or relabeled.
  Closed compaction metadata validates bounds, paths, text, secrets and hashes.
  Recovery tests verify exact bytes, gzip, missing/corrupt locators and fresh Git
  clones; summary success cannot promote an underlying failed or unavailable run.
- **H2-b:** [baseline](baseline.json) expands actual source inventories, first-lock
  SQL and all 70 migration digests. Retain every inventory. B09 request has 46
  tables; the deciding prefix excludes Publication and takes it separately in
  SHARE ROW EXCLUSIVE. B04 has 41; RevisionAction 26; novelty N 35. Passive
  observers use REPEATABLE READ, READ ONLY and driver PID metadata, with no
  extra writer queries. Added bounded approval first-write/replay/denial and
  independent-project cases, plus witnessed same-target writer contention.
  Project/purpose selection requires separate projects for independent targets.
  Full samples and lock observations use bounded evidence chunks under tmp_path.
  Declared approval-envelope/reference-host measurements remain **BLOCKED**;
  the large approval case explicitly refuses to label its bounded fixture as
  the declared scientific/source envelope. No narrowing or improvement is claimed.
- **H2-c:** installed guard/catalog attributes and clean head tested, together
  with populated 0044→0051→0052→head upgrades and reconnect at each checkpoint.
  Revision, review, Issue and scientific manifests remain identical. Existing
  normal-role SQL, both writer orders and predecessor-only UPDATE tests remain.
  No migration, DDL, startup repair, or historical migration edit was needed.
- **H2-d:** API/CLI production bundles have no freeze writer; their shared
  engines keep ordinary settings. Tests pin that composition and opt-in 10s/30s
  connection bounds, local bounds after FIRST SHARE, rollback/pool behavior,
  credential denial and scheduled role expiry during a witnessed first wait.
  No transport or production factory wiring was added.
- **B24:** one parametrized test covers genuine absence, INCONCLUSIVE and
  CLOSE_PRIOR_ART_FOUND on the same exact Claim placed in the manuscript.
  Actual commands issue approval, consume READY, issue preparation approval,
  and freeze the package. Independent BLOCKING NOVELTY Issues, invalid facts
  and missing consent still deny with unchanged effects/receipts and active
  unconsumed grants. Normalized permission/lifecycle/receipt results are checked;
  scientific/novelty rows and hashes remain unchanged, and novelty material never
  enters permission records. No product gate, error, DTO, enum or dependency added.

## Explicit B24 deviation for owner confirmation

H2 §12.4 requests all three successful outcome fixtures, but §11.3 prohibits
synthesizing unsupported material. `NoveltyService` unconditionally rejects
NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE. Following the user's reviewer-directed
fallback, the fourth parameter asserts that existing INVALID_STATE_TRANSITION
rejection and zero novelty effects, then checks permissions under absence. It
**does not** represent a successful third-outcome fixture. Owner confirmation of
this §12.4 clarification remains open; the stronger outcome was not enabled.
This item does not block the independent H2 work.

## Execution environment and exact focused results

Repository subject: `672f2501e37af8143a2322ffdb769eacbf6e835e` plus the authored
working diff. Baseline subject/diff hashes describe the implementation snapshot
before generating evidence, not owner acceptance of the final diff. No commits,
branches, pushes, or migration changes were made.

Observed PostgreSQL: **18.6 (Homebrew)**, `max_locks_per_transaction=256`;
observer isolation `repeatable read`, `transaction_read_only=on`. Host Darwin
arm64 does not match the declared Ubuntu reference host. No server setting changed.

Commands below used `UV_CACHE_DIR=/private/tmp/h2-uv-cache`, `PYTHONPATH=src`,
and the handoff's explicit local disposable `RB_TEST_ADMIN_URL` (credentials
omitted). `uv run --no-sync` used the existing locked environment. All database
suites created/dropped random disposable databases. Tests write observations to
`tmp_path`; no new repository PR2-20 subject directory was created.

| Exact command after environment prefix | Observed result |
| --- | --- |
| `uv run --no-sync pytest -o addopts='' -q --tb=short tests/unit tests/architecture tests/test_architecture.py` | **5675 passed**, 49 warnings, 113.40s; exit 0. |
| `uv run --no-sync pytest -o addopts='' -q --tb=short tests/integration/phase2/test_pr2_20_governance_races.py tests/integration/phase2/test_b09_approval_concurrency.py tests/integration/phase2/test_b14r_ready_approval_races.py tests/integration/phase2/test_b06_revision_concurrency.py tests/integration/phase2/test_b17_package_freeze.py tests/integration/phase2/test_b13_grant_consumption.py` | **106 passed**, 374 warnings, 294.65s; exit 0. |
| `uv run --no-sync pytest -o addopts='' -q --tb=short tests/integration/phase2/test_revision_action.py tests/integration/phase2/test_b04_manuscript_races.py tests/integration/phase2/test_pr2_20_novelty.py tests/integration/phase2/test_pr2_20_governance_races.py::test_h2_decision_passive_inventory_and_first_statement` | **109 passed**, 357 warnings, 360.37s; exit 0. Subsequent focused refinements are separately verified below. |

Warnings are the existing Alembic path-separator deprecation and SQLAlchemy
connection-isolation warnings; they are separate from passing assertions.
Final checks after the refinements:

| Exact command after environment prefix | Observed result |
| --- | --- |
| `uv run --no-sync pytest -o addopts='' -q --tb=short tests/e2e/test_pr2_20_benchmark.py` | **20 passed, 65 skipped**, 56 warnings, 272.68s; exit 0. Skips are opt-in profiles, not measured improvements. |
| `uv run --no-sync pytest -o addopts='' -q --tb=short tests/e2e/test_pr2_20_benchmark.py -k h2` | **16 passed, 14 skipped, 57 deselected**, 48 warnings, 192.79s; exit 0. Final instrumentation, inventory chunking, SQLSTATE collection and both actual writer-contention cases included. |
| `uv run --no-sync pytest -o addopts='' -q --tb=short tests/integration/phase2/test_pr2_20_novelty.py tests/integration/phase2/test_revision_action.py::test_h2_installed_revision_guard_at_clean_head tests/integration/phase2/test_revision_action.py::test_h2_populated_0044_0051_0052_head_upgrade_reconnect tests/integration/phase2/test_pr2_20_governance_races.py::test_h2_decision_passive_inventory_and_first_statement` | **30 passed**, 115 warnings, 211.67s; exit 0. Final normalized permission assertions, strengthened guard checks and passive observer without writer queries included. |
| `uv run pyright` | Exit 0: **0 errors, 0 warnings, 0 informations**. The tool additionally reports an available version update; no update was installed. |
| `uv run ruff format --check .` | Exit 0: **736 files already formatted**. |
| `uv run ruff check .` | Exit 0: **All checks passed**. |
| `git diff --check HEAD` | Exit 0. |
| `uv run --no-sync alembic heads` | Exit 0: exactly **0068_b21_unresolved_capture (head)**. |

The focused B04 expiry/contention refinement command also passed **5 tests**,
179 deselected, 15 warnings, 33.94s; its exact command is retained in the
[attempt index](attempts/index.json). It includes the post-lock scheduled role
expiry check with authority still valid at the witnessed wait. Counts above
are overlapping focused runs, **not an aggregate test count**.

[Final run records](runs.json) retain exact commands, counts, complete sanitized
compressed stdout, byte lengths and SHA-256 values. [Source fingerprint](source_manifest.json)
records the tested tracked source files; the subject snapshot precedes writing
its own evidence record. [Earlier attempt records](attempts/index.json) retain
all diagnostic failures and later reruns. Compressed stdout is engineering
evidence, not canonical persistence or scientific ArtifactStore content.

## Earlier attempts and review

Earlier attempts are not passes: the initial B24 fixture constructed CLOSE
before supplying its required basis (six failed parameters); this was corrected
by supplying the admitted material atomically. A benchmark assertion initially
classified preliminary credential reads as writer transactions; grouping by
actual transactions fixed it. Independent targets initially shared a project,
which correctly produced stale-target denials; fixtures now use independent
project/purpose scopes. A subsequent fixture used actors from different
onboarding deployments; using its correctly bound requester as project owner
fixed that denial. The first B04 scheduled-expiry test attempted final readback
through the expired caller; readback now uses an unaffected entitled caller.

One unit/architecture attempt had **1 failed, 5673 passed**, 49 warnings, 101.53s:
`test_h2_compaction_success_does_not_close_source_or_exit[BLOCKED]` observed
changing dirty subjects while authoring continued. Its subject is now frozen
within the test; the subsequent complete unit/architecture run above passed.
The earlier combined new-test run had **5 failed, 39 passed, 14 skipped,
135 deselected**, 160 warnings, 220.54s: B04 role readback and four stale-target
benchmark parameters. Focused follow-ups preserved failures before successful
reruns. Compact attempt records and recoverable sanitized output are linked below.

Read-only sub-agents investigated/reviewed the evidence, guard/timeout and B24
changes; root alone wrote files. Review caught a driver isolation getter adding
hidden writer SQL; it was removed. Review also caught the distinction between
same-target read replay and actual writer contention, and the incomplete large
approval envelope; explicit wait regressions and BLOCKED profile status address
those findings. No inventory was narrowed to satisfy a test.

Filename substitutions: migration 0042 is the existing
`0042_pr2_15_minimal_decision.py`; the novelty inventory constant is `N`.
Existing B14/B17 fixture modules and the approved disposable PR212 prefix are
reused. No semantic substitution beyond the recorded B24 fallback was made.

## Separate loop evidence and outstanding boundaries

The reviewer reports pyright/Ruff and **10975 passed** from the earlier loop
check. That check covered only the previous status-line diff. It verifies none
of this implementation. Its output is loop-owned evidence, not an author-run
full suite. The new full-suite result must be attached by the loop separately.
The author did **not** run `full_suite_sharded.sh` or the whole suite.

Reference-host load/envelope acceptance, retained-host approval, real PaperQA2
intake and owning acceptance subjects remain unavailable here. Inspection still
finds no destination/private-network denial in `literature_http.py`; its existing
transport finding remains outside this slice. These items prevent Phase 2 exit;
H2 does not waive or implement them. STOP after this authorized first slice.
