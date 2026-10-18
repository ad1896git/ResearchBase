# B29 measurement evidence — 2026-10-18

Owner approval and implementation authorization cover Start here 1–3 of the [B29 contract](../proposals/B29_Partial_Blocker_Index_Contract_DRAFT.md). **Measurement execution completed; index admission remains BLOCKED/pending owner decision.** No migration, production index, application change, commit, push or branch was created.

The following measurements are local informational evidence, not the dedicated large profile. No threshold admits DDL. The 51,200-Issue profile is NOT RUN: the dedicated Ubuntu x86-64 host, reserved resources and required PostgreSQL settings are unavailable. Concurrent work on the local cluster was observed; the measurements do not establish a production latency or write-cost budget.

## Frozen subject and setup

- Revision: `fa9c43eac6ebdd59fc4684faafb7be5871c2dde5`; authored-input diff SHA-256: `9dc9977cd3ba6aa94068d96b0a5bbb088cdae375160db704236e2f6741bd8326`. This freezes the measured source before this output report was written.
- Observed Alembic head (recheck before any future DDL): `0059_b13_grant_consumption`. No revision was assigned for B29. Historical 0040/0053 and all other migrations are unchanged.
- PostgreSQL: **18.6 (Homebrew)**; host metadata and actual settings are in [the profile](../../pr_evidence/pr2-20/3cbc582587ee098d7227613af27d80dc6e05b5f94ab98ef72415035baf08c40e/samples-b29-profile-0-000.json). RAM/storage reservations are unattested; inherited RAM=0 means unavailable, not measured zero capacity.
- Distribution seed: `2202026`; UUIDs are owning-service-generated and preserved in the seed manifest. One quiescent, legal fixture is physically cloned into two independent disposable databases for each case, worker count and repetition. Each pair starts with identical rows/IDs/hashes/edges. Cloning closes only idle backends and autovacuum workers for the fixture-owned template and refuses active client transactions.
- Each profile uses one warmup and two measured calls per worker, workers **1/4**, and **three repetitions**, reusing the PR2-20 small sampling policy. Every measured write and warmup has a fresh request and distinct target. There are 54 paired cohorts, 108 disposable clones, and 540 retained timed samples (270 before and 270 after), plus warmups and separately captured calls.
- Naming substitution: the guide’s `tests/contracts/pr2_20_scaled.py` is the existing `tests/integration/phase2/pr2_20_scaled.py`. No semantic substitution was made.
- Current Decision service performs a separate REPEATABLE READ historical replay probe before opening a fresh writer. Captures therefore assert the writer transaction’s first SQL is the exact `B09_SHARE_SQL`, rather than treating the preliminary read as a write. Disposition writes retain FIRST-statement `REVISION_SNAPSHOT_TABLES` SHARE. Issue insertion uses the existing owning review service and its ROW EXCLUSIVE reservation. All inventories, advisory/row-lock order, isolation, timeouts and error mappings remain unchanged.
- Observer SELECTs/EXPLAIN and owning history/gate reads use REPEATABLE READ, READ ONLY; captures assert no explicit table/advisory/row locks in the measured read paths. PostgreSQL implicit ACCESS SHARE is expected. No planner settings force index use.

## Measured cardinalities

| Scope | Total | OPEN | BLOCKING | OPEN/BLOCKING |
| --- | ---: | ---: | ---: | ---: |
| Global  | 2318 | 2317 | 783 | 782 |
| Project 0efa2a10-b468-41d9-a3f8-d63ac3cc2fa3 | 2318 | 2317 | 783 | 782 |
| Target class CLAIM | 0 | 0 | 0 | 0 |
| Target class CONCLUSION | 2318 | 2317 | 783 | 782 |

The fixture contains **176 reviews**, including **90 zero-Issue reviews**. Each of the sparse, dense and miss targets has 49 complete favorable reviews; 24 contain 32 Issues each. Sparse has exactly one OPEN/BLOCKING Issue among 768 Issues; dense has 768; miss has zero. One separate stable target has a legal B08 DISMISSED concern, and 13 independent targets supply fresh disposition/write costs. An independent Claim review covers a second target class. All records and terminal events were created through owning Application services; no status UPDATE or disabled guard was used.

Exact per-review/project/target-class counts, ANALYZE observations and fixture identity are retained in the profile/summary. Planner statistics were refreshed with ANALYZE after fixture generation and copied with each template clone.

## Timings and write costs

Nearest-rank percentiles are calculated from raw samples. The table shows the median of the three repetition p95 values in milliseconds; raw per-repetition p50/p95/max values and every sample remain in the referenced cohort files. PASS/FAIL/BLOCKED below are PR2-20 regression/noise classifications only: ratio ≤1.10 and relative spread ≤0.15; none is owner admission.

| Case | Workers | Before p95 ms | After p95 ms | Ratio | Policy | Captured queries before/after |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| sparse | 1 | 0.604 | 0.558 | 0.924 | BLOCKED | 2/2 |
| sparse | 4 | 1.703 | 1.819 | 1.068 | BLOCKED | 2/2 |
| dense | 1 | 1.022 | 0.906 | 0.886 | BLOCKED | 2/2 |
| dense | 4 | 1.425 | 1.329 | 0.932 | BLOCKED | 2/2 |
| miss | 1 | 1.397 | 1.012 | 0.725 | BLOCKED | 2/2 |
| miss | 4 | 1.944 | 1.485 | 0.764 | BLOCKED | 2/2 |
| terminal | 1 | 11.193 | 11.314 | 1.011 | BLOCKED | 3/3 |
| terminal | 4 | 22.324 | 26.969 | 1.208 | BLOCKED | 3/3 |
| service-hit | 1 | 656.719 | 510.962 | 0.778 | BLOCKED | 2453/2453 |
| service-hit | 4 | 1911.660 | 2525.380 | 1.321 | BLOCKED | 2453/2453 |
| service-replay | 1 | 459.169 | 442.043 | 0.963 | BLOCKED | 2504/2504 |
| service-replay | 4 | 1702.568 | 1841.455 | 1.082 | BLOCKED | 2504/2504 |
| history | 1 | 788.276 | 1020.547 | 1.295 | BLOCKED | 6234/6234 |
| history | 4 | 2685.705 | 4416.655 | 1.645 | BLOCKED | 6234/6234 |
| issue-insert | 1 | 8.001 | 7.830 | 0.979 | PASS | 47/47 |
| issue-insert | 4 | 43.689 | 45.121 | 1.033 | BLOCKED | 47/47 |
| disposition | 1 | 1089.216 | 926.468 | 0.851 | PASS | 8255/8255 |
| disposition | 4 | 4086.283 | 3682.723 | 0.901 | PASS | 8255/8255 |

`sparse/dense/miss/terminal` execute the owning repository gate in a single lock-free snapshot, including terminal-history ID scanning and validation calls. `service-hit` measures the complete Decision denial with all matching reviews; `service-replay` compares the exact saved Decision DTO and complete basis; `history` compares exact B08 historical DTOs. `issue-insert` includes its owning Review command and deferred/root-history checks, so it is command overhead rather than an isolated physical INSERT microbenchmark. `disposition` is a fresh legal terminal write, never replay.

## Plans, buffers, storage and build cost

Candidate DDL, executed only by the guarded measurement installer in fixture-owned clones:

```sql
CREATE INDEX ix_pr220_issue_open_blocking_review
  ON review_issues USING btree (review_record_id)
  WHERE status = 'OPEN' AND severity = 'BLOCKING';
```

Preflight refuses the candidate name or an equivalent predicate/key under another name. Catalog assertions require a valid/ready, nonunique single-key B-tree with no INCLUDE columns. The existing composite index remains. Constraints, trigger definitions/enabled/deferred flags and trigger-function hashes are compared unchanged, including B08 and the PR2-15 deferred checks.

- Candidate index bytes: **16,384 (16 KiB)**.
- Issue storage before: `{'heap_bytes': 303104, 'index_bytes': 393216, 'total_bytes': 737280}`; immediately after index installation: `{'heap_bytes': 303104, 'index_bytes': 409600, 'total_bytes': 753664}`.
- Index builds (54 clones): min **0.848 ms**, median **1.299 ms**, max **3.030 ms**. Post-write heap/index/total bytes are retained per side as well.

Every plan is actual `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` for captured read SQL. No mutating statement is EXPLAIN ANALYZEd. Diagnostic parameter expressions are redacted by the existing PR2-20 observer; SQL digests, captured gate SQL, parameter types, nodes, buffer counters and timings remain. Function-only `b08_check_history` calls contribute service/query counts; the existing safe EXPLAIN observer omits function-only SELECTs, so their internal buffer traffic is not separately attributed.

| Gate (repeat 0, one worker) | Before nodes/indexes | After nodes/indexes | Root buffer hits before/after | Root buffer reads before/after |
| --- | --- | --- | ---: | ---: |
| sparse | Index Scan, Memoize, Nested Loop, Result, Seq Scan, Sort; internal_review_records_pkey | Index Only Scan, Index Scan, Nested Loop, Result, Seq Scan, Sort; internal_review_records_pkey, ix_pr220_issue_open_blocking_review | 43/69 | 0/0 |
| dense | Index Scan, Memoize, Nested Loop, Result, Seq Scan, Sort; internal_review_records_pkey | Index Only Scan, Index Scan, Nested Loop, Result, Seq Scan, Sort; internal_review_records_pkey, ix_pr220_issue_open_blocking_review | 56/70 | 0/0 |
| miss | Index Scan, Memoize, Nested Loop, Result, Seq Scan, Sort; internal_review_records_pkey | Index Only Scan, Index Scan, Nested Loop, Result, Seq Scan, Sort; internal_review_records_pkey, ix_pr220_issue_open_blocking_review | 152/96 | 0/0 |
| terminal | Bitmap Heap Scan, Bitmap Index Scan, Nested Loop, Result, Seq Scan, Sort; ix_pr214_issue_review_severity, ix_pr214_review_conclusion | Bitmap Heap Scan, Bitmap Index Scan, Index Only Scan, Nested Loop, Result, Seq Scan, Sort; ix_pr214_review_conclusion, ix_pr220_issue_open_blocking_review | 52/49 | 0/0 |

The candidate was selected in the captured gate plans, but all 14 read/service worker
profiles are BLOCKED by the 15% noise policy. Three write profiles satisfy the small-profile
regression/noise classification; four-worker insertion is noisy. These local results do not
establish a reliable service benefit or authorize the extra index. Separate lock-wait
attribution is unavailable; elapsed times include waits and no zero wait is assumed.

## Correctness and evidence files

Before/after index installation, complete row-byte digests and ID/hash/edge inventories agree exactly, and only the measured candidate’s physical catalog entry differs. Reads remain nonmutating. Read DTOs, complete saved basis, denial codes and query counts (including the whole concurrent warmup/sample window) agree for every measured pair.

Independent fresh writes necessarily receive independent trusted database timestamps; 0040 also generates a random OPEN-root event UUID for each new Issue. Full per-side post-write row digests bind the actual clock values, while the ID/edge inventories retain actual root UUIDs. Cross-database write comparison excludes only new rows’ `created_at`/`occurred_at`, and matches only newly generated OPEN roots by their unique concrete Issue FK. Existing identities/timestamps and every other row field remain compared. Fresh disposition DTOs compare every field except `occurred_at`, whose actual values are retained. This is an explicit comparison limitation, not a mutation of scientific history or a claim that independently generated row bytes are equal.

- [Machine summary](../../pr_evidence/pr2-20/3cbc582587ee098d7227613af27d80dc6e05b5f94ab98ef72415035baf08c40e/samples-b29-summary-0-000.json) (frozen subject, head, migration hashes, catalog, distributions, all 54 cohort summaries).
- [Guard inventory](../../pr_evidence/pr2-20/3cbc582587ee098d7227613af27d80dc6e05b5f94ab98ef72415035baf08c40e/samples-b29-guards-0-000.json) (exact trigger definitions and function SHA-256).
- Cohort files are `samples-b29-<case>-<workers>-<repeat>-0-000.json` in the same directory. They reference bounded `plans-b29-*` files and complete seed/post-write manifest chunks. Raw outputs live in the prescribed PR2-20 layout; this checkout’s existing local Git exclude ignores generated evidence directories. No ignore rule was changed.

Final artifact audit passed: **3,200 JSON files**, maximum **1,048,539 bytes**
(below 1 MiB), bounded arrays/text, **3,143 resolved file references**, all **54 cohorts**
and **540 samples**, and exact captured/sample-window query-count parity. The current
authored-source diff, excluding this output report, matches the frozen diff SHA-256.
Independent read-only review checked every timing-table row against raw cohorts and
the summary, cardinalities and build statistics; no P0/P1 was found.

## Focused verification

Commands ran from this repository using its existing `.venv` (Python 3.12). All DB suites use the explicitly configured local admin selector and fixture-owned PostgreSQL 18 databases. The full test suite was not run; the external loop owns that check.

| Exact command | Observed result |
| --- | --- |
| `.venv/bin/ruff check .` | Exit 0; All checks passed. |
| `.venv/bin/ruff format --check .` | Exit 0; 641 files already formatted. |
| `.venv/bin/pyright` | Exit 0; 0 errors, 0 warnings, 0 informations. |
| `.venv/bin/pytest -o addopts='' -q tests/unit tests/architecture` | Exit 0; 5,125 passed, 0 failed/errors/skipped; 42 warnings, 119.12s. |
| PostgreSQL selection A below | Exit 0; 112 collected: 63 passed, 48 skipped, 1 deselected; 0 failed/errors; 191 warnings, 324.31s. The 48 large-profile cases are NOT RUN. |
| `.venv/bin/pytest -o addopts='' -q tests/integration/phase2/test_b08_concurrency.py` | Exit 0; 46 passed, 0 failed/errors/skipped; 138 warnings, 400.47s. |
| `.venv/bin/pytest -o addopts='' -q tests/integration/phase2/test_pr2_20_migrations.py` | Exit 0; 17 passed, 0 failed/errors/skipped; 56 warnings, 34.81s. |
| `RB_B29_MEASUREMENT=1 .venv/bin/pytest -o addopts='' -xq tests/e2e/test_pr2_20_benchmark.py::test_b29_measurement` | Exit 0; 1 passed, 0 failed/errors/skipped; 3 warnings, 574.95s. Execution PASS; admission BLOCKED. |
| Observer selection B below, after the clone-maintenance correction | Exit 0; 41 passed, 0 failed/errors/skipped; 3 warnings, 2.38s. |
| `git diff --check` | Exit 0. |
| `git diff --exit-code HEAD -- migrations` | Exit 0; no migration changes. |
| `.venv/bin/alembic heads` | Exit 0; `0059_b13_grant_consumption (head)`. |

PostgreSQL selection A:

```sh
.venv/bin/pytest -o addopts='' -q \
  tests/integration/phase2/test_pr2_20_catalog_plans.py \
  tests/integration/phase2/test_b08_schema.py \
  tests/integration/phase2/test_b08_issue_disposition.py \
  tests/integration/phase2/test_b08_issue_history.py \
  tests/e2e/test_pr2_20_benchmark.py -k 'not b29_measurement'
```

Observer selection B:

```sh
.venv/bin/pytest -o addopts='' -q \
  tests/integration/phase2/test_pr2_20_catalog_plans.py::test_b29_candidate_only_in_owned_clone_with_exact_catalog_and_snapshot \
  tests/unit/phase2/test_pr2_20_evidence.py \
  tests/architecture/test_pr2_20_boundaries.py
```

The final nonoverlapping PostgreSQL selections (A, B08 concurrency, migrations and the
opt-in measurement) total **127 passed, 48 skipped, 1 deselected**, with no failures or
errors. Selection B is additional targeted verification and overlaps A/unit/architecture.
Earlier successful development runs included 5,124 unit/architecture passes, 40 targeted
unit/architecture passes, and one isolated repaired clone pass; they are not added again.
The first PostgreSQL A attempt reported 1 failed, 62 passed, 48 skipped, 1 deselected;
the clean rerun above supersedes it. Earlier Pyright runs briefly reported 3 and then
7 errors in the evolving test helpers; the final result is zero.

Development attempts are not acceptance: one earlier measurement and the first focused run failed clone setup due to retained idle fixture connections; the isolated repaired clone test subsequently passed. One long run stopped after 39 cohorts when the template-quiescence check treated a non-idle backend as an active application client; the check now distinguishes client transactions from maintenance workers, while refusing active/idle-in-transaction clients. A later measurement failed an overly broad first-SQL assertion because the current Decision service has a separate lock-free replay probe. Captures now identify the writer’s first statement by transaction. Intermediate runs interrupted while extending measurement/serialization are NOT PASS. The final commands above supersede those attempts.

Read-only sub-agents investigated and reviewed the spec/diff; only the primary agent wrote files. No outstanding P0/P1 was identified in the reviewed measurement code. Admission and any deployment window/rollback remain a separate owner decision. Stop at B29 measurement; this is not B08 acceptance or Phase 2 exit.
