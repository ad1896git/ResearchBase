# B20 screening and negative-probe basis — implementation evidence

The final continuation verification is recorded at the end of this file. Earlier observations below belong to the interrupted attempt and are retained as history, not substituted for fresh results.

Authorized by the owner on 2026-10-19 through the B20 contract and ACCEPTED ADR-0018. The proposal status line was changed first. This evidence covers the first slice only; it does not declare a Phase 2 or whole-suite gate.

The existing NoveltyService, repository, Application port, HTTP routes and CLI now support typed, sealed screening probes/results and outcome-specific v2 material. Negative admission checks the complete bounded exact-plan execution/query/result inventory, warning-free successful probes, exact provider coverage, captured resolution witnesses and independently HUMAN-VERIFIED UNIQUE terminal RELATED/CONTRASTING comparisons. Historical reads/replays preserve saved membership and hashes while reporting current inventory expansion and scientific usability separately. Old v1 and positive-v2 material retain their literal shapes.

One migration, `0070_b20_screening_basis`, follows actual head `0068_b21_unresolved_capture`. Existing migration files were not edited. It admits both typed child relations, independent deferred parent/child completeness guards, native-xid seals, strict ordinals/narratives, RESTRICT FKs, and populated downgrade refusal. Preflight pins full shared/sibling function definitions, trigger attachments and the original material CHECK. Only the approved B19 parent attachment/CHECK changes; sibling function bodies stay unchanged.

Writes retain the exact existing READ COMMITTED first-statement N SHARE inventory, request coordination and Claim serialization. Exact reads retain one read-only REPEATABLE READ snapshot without explicit table/advisory/row locks. Consumption paths and their isolation settings were not changed.

Naming/location reconciliation: the guide's `<next>` migration placeholder resolves to 0069. The existing B22 attachments are named `b22_prior_art_prelocked` and `b22_complete_correction` without a `trg_` prefix; those actual names are preserved and pinned. Response schemas continue through the existing dataclass-derived `_response_schema(NoveltyReadback)` renderer in `api/routes.py`. No alternate service, ORM owner or dependency was added.

All commands below ran from the repository with `UV_CACHE_DIR=/private/tmp/rb-b20-uv-cache`. PostgreSQL integration used the configured disposable-database fixtures on PostgreSQL 18.6, not SQLite. Plain `uv run` initially could not write the default user cache; the writable cache prefix was then used consistently.

| Exact command (after the cache environment prefix) | Observed result |
| --- | --- |
| `uv run ruff check .` | Exit 0; All checks passed. |
| `uv run ruff format --check .` | Exit 0; 746 files already formatted. |
| `uv run pyright` | Exit 0; 0 errors, 0 warnings, 0 informations. |
| `uv run pytest tests/unit tests/architecture --tb=short` | Exit 0; 5,733 passed, 50 warnings, 87.69s. |
| `uv run pytest tests/unit/phase2/test_b20_*.py tests/architecture/test_b20_*.py tests/integration/phase2/test_b20_*.py --tb=short` | Exit 0; 165 passed, 73 warnings, 80.21s. |
| `uv run pytest tests/integration/phase2/test_b19_close_prior_art_concurrency.py::test_retry_normalization --tb=short` | Exit 0; 4 passed, 5 warnings, 6.61s. |
| `git diff --check` | Exit 0. |

The B20 run includes strict values/transport parity, independent literal material vectors, zero-hit and multi-query negatives, failed/cancelled/unknown/warning branches, provider mismatches, exact verified comparisons, omitted inventory rejection, mixed-shape restart/replay, later roots/resolutions/executions/source/evidence invalidity, direct normal-role SQL gates and array tricks, seals, rollback, downgrade checks, observed execution/resolution insertion and comparison-root/correction races, credential revocation/expiry across waits, same-UUID coordination, qualified retry limits and unknown-commit recovery.

The unit/architecture run initially found two bookkeeping failures (the CI head literal and formatting of updated head assertions); both were corrected before the passing 5,733-test run. Inherited B19/B22 timeout tests had expected CONCURRENT_MODIFICATION for 55P03/57014. Their assertions now follow approved B20 §11.2's sanitized INTERNAL_ERROR fallback, retaining the original serialization/deadlock retry assertions. B21's downgrade table inventory was appended with the two new child tables.

The suites with head-only inventory updates were also run using this exact command:

```sh
uv run pytest tests/test_architecture.py tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b05_review_migration.py tests/integration/phase2/test_b08_schema.py tests/integration/phase2/test_b14a_entry_schema.py tests/integration/phase2/test_batch_c_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_17_authorship_schema.py tests/integration/phase2/test_revision_action.py --tb=short
```

Observed: exit 0; **250 passed, 626 warnings in 332.61s**. Warnings include inherited Alembic configuration and SQLAlchemy transaction/isolation warnings; they were not converted into failures or suppressed.

Compatibility assertion corrections were verified together with:

```sh
uv run pytest tests/integration/phase2/test_b19_close_prior_art_concurrency.py::test_retry_normalization tests/integration/phase2/test_b22_prior_art_concurrency.py::test_retry_inventory tests/integration/phase2/test_b21_capture_schema.py --tb=short
```

Observed: exit 0; **29 passed, 41 warnings in 59.93s**. This includes all four inherited timeout expectations and B21's expanded downgrade inventory.

The complete inherited novelty/dependency selection was run with:

```sh
uv run pytest tests/integration/phase2/test_b01_*.py tests/integration/phase2/test_b19_*.py tests/integration/phase2/test_b21_*.py tests/integration/phase2/test_b22_*.py tests/integration/phase2/test_pr2_18_*.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_20_novelty.py --tb=short
```

Observed: exit 1; **322 passed, 7 failed, 363 warnings in 1086.48s**. The seven failures were exactly:

- B19 `test_retry_normalization`: 55P03 and 57014 expectations.
- B22 `test_retry_inventory`: 55P03 and 57014 expectations.
- B21 `test_catalog_and_owned_downgrade`: removed-table inventory omitted the two B20 children.
- PR2-18 `test_normal_role_stronger_outcomes_denied`: both outcome cases still named `ck_b19_novelty_material`; the approved replacement is `ck_b20_novelty_material`.

All seven outdated assertions were corrected without changing sibling guard bodies or historical material. The 29-test compatibility rerun above covers the first five. The remaining two were verified with:

```sh
uv run pytest tests/integration/phase2/test_pr2_18_schema.py::test_normal_role_stronger_outcomes_denied --tb=short
```

Observed: exit 0; **2 passed, 2 warnings in 4.14s**. Thus every failure from the inherited selection has an observed passing focused rerun; the original failed run is not relabeled PASS. The whole inherited selection was not repeated after these assertion-only fixes.

Read-only sub-agent review identified and verified corrections for shared/sibling baseline preflight, captured-resolution agreement, current Claim usability, and conservative INCONCLUSIVE handling. The final B20 run includes the corrected guards and projections.

No whole-suite run was executed. The loop owns that check and its acceptance evidence. No commit, push or branch creation was performed. Stop at this B20 first slice.


## Continuation verification — 2026-10-19

Reviewed the existing diff rather than restarting. Three sub-agents performed read-only specification/code/test investigation; the root agent remained the only writer. No confirmed P0/P1 remained in those reviews. The continuation corrected the shared test builder to derive each probe from its own query's attempts/results, and added mixed-hit/empty query, actual reversed replay, nested-result validation parity, strict result types, pinned digest/reference/order checks, catalog inventories, old-shape populated upgrade, tampered-preflight rejection, predecessor serialization and foreign inventory SQL cases. SQL forgery tests now pin SQLSTATE rather than accepting arbitrary database errors.

Commands below ran inside this repository with the prefix `UV_CACHE_DIR=/private/tmp/rb-b20-uv-cache`. PostgreSQL used the environment's existing `DATABASE_URL` and `RB_TEST_ADMIN_URL` selectors and disposable fixture databases. No production database or existing migration file was changed.

| Exact command (after the cache prefix) | Observed final result |
| --- | --- |
| `uv run ruff check .` | Exit 0; All checks passed. |
| `uv run ruff format --check .` | Exit 0; 746 files already formatted. |
| `uv run pyright` | Exit 0; 0 errors, 0 warnings, 0 informations. |
| `uv run pytest tests/unit tests/architecture --tb=short` | Exit 0; **5,763 passed**, 50 warnings in 113.54s. |
| `uv run pytest tests/unit/phase2/test_b20_*.py tests/architecture/test_b20_*.py tests/integration/phase2/test_b20_*.py --tb=short` | Exit 0; **205 passed**, 88 warnings in 124.39s. |
| `uv run pytest tests/integration/phase2/test_b20_screening_schema.py::test_normal_role_cannot_forge_complete_negative --tb=short` | Exit 0; **10 passed**, 10 warnings in 18.20s; verifies the final SQLSTATE assertion refinement. |

Intermediate continuation observations are not relabeled: the initial unchanged implementation passed 5,733 unit/architecture and 69 B20 PostgreSQL tests. While new tests were being added, one unit/architecture run had 5,759 passed / 1 failed because its embedded static check observed test typing errors; a three-test PostgreSQL run had 2 passed / 1 failed because the new race test lacked an error import. Both test-code issues were corrected before the final passing runs above. A subsequent B20 PostgreSQL selection passed 72 tests before the final additions; the final combined run covers all additions.

The head/migration inventory regression command was rerun in the continuation:

```sh
UV_CACHE_DIR=/private/tmp/rb-b20-uv-cache uv run pytest tests/test_architecture.py tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b05_review_migration.py tests/integration/phase2/test_b08_schema.py tests/integration/phase2/test_b14a_entry_schema.py tests/integration/phase2/test_batch_c_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_17_authorship_schema.py tests/integration/phase2/test_revision_action.py --tb=short
```

Observed: exit 0; **250 passed**, 626 warnings in 303.73s. The inherited Alembic and SQLAlchemy warnings remain visible.

A final error-contract review found and corrected two B20-specific classifications: `ck_b20_novelty_material` now maps to INVALID_STATE_TRANSITION before the generic B20 constraint handler, and the new migration separates a false deterministic probe disposition (P17D3 / provenance violation) from a correctly retained INCOMPLETE probe used for a negative (P17D2 / invalid state). Three normalization unit cases and two direct normal-role SQL cases cover the distinction. The final 5,763/205 runs in the table above followed these corrections; the preceding continuation checkpoints were 5,760/200 passing tests. Static checks were also rerun successfully after these corrections. Existing migration files and sibling guard bodies remain unchanged.

The 250-test head/inventory selection finished before this narrow error-mapping correction. Its migration/catalog behaviors are additionally covered by the final B20 run. The inherited dependency selection began before that correction; its existing sibling behavior does not use the new B20 error branches.

The complete inherited dependency selection also completed in the continuation:

```sh
UV_CACHE_DIR=/private/tmp/rb-b20-uv-cache uv run pytest tests/integration/phase2/test_b01_*.py tests/integration/phase2/test_b19_*.py tests/integration/phase2/test_b21_*.py tests/integration/phase2/test_b22_*.py tests/integration/phase2/test_pr2_18_*.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_20_novelty.py --tb=short
```

Observed: exit 0; **329 passed**, 365 warnings in 955.83s. This fresh selection supersedes the interrupted attempt's failed 322/7 checkpoint as dependency evidence; that historical failure remains recorded above.

Final `git diff --check`: exit 0. PostgreSQL was directly checked with `SHOW server_version`: **18.6 (Homebrew)**. Read-only review of the final error corrections reported no findings. No confirmed P0/P1 remains. No whole-suite execution, commit, push or branch creation was performed. Work stops at the authorized B20 first slice; the loop owns whole-suite evidence.

## Reviewer remediation — 2026-10-19

The reviewer identified two additional head round-trip suites omitted from the earlier 250-test selection. Reproduction with `uv run pytest tests/integration/phase2/test_b07_schema.py tests/integration/phase2/test_b15_package_schema.py -x` stopped at B07: 1 failed, 3 warnings in 1.89s. An independent B15 reproduction also failed. Both assertions reported exactly the two B20 child tables as unexpected extra inventory entries. These failures came from this diff, not flakiness. Only the missing `novelty_assessment_probes` and `novelty_assessment_screening_results` entries were appended to both expected table sets; no migration or sibling guard was changed for this correction.

The timeout behavior is explicitly required by approved B20 §11.2 (proposal lines 287–290): “55P03/57014 and connection/unknown-commit failures remain sanitized INTERNAL_ERROR.” Section 7 also requires timeouts to be sanitized INTERNAL_ERROR and limits retries to 40001/40P01. The RuntimeError fallback is therefore retained. `test_database_timeouts_use_sanitized_internal_fallback` now directly pins both driver SQLSTATEs to the exact sanitized RuntimeError, while the existing PostgreSQL retry tests verify they get one attempt. HTTP/CLI fallback mappings remain covered by the B20 transport suite.

The B20 concurrency observer now records actual psycopg transaction modes without issuing observer SQL before the first statement. It pins the full literal 35-table N inventory, verifies READ COMMITTED writes and timeout/advisory/Claim lock order, and verifies read-only REPEATABLE READ exact reads with no explicit table/advisory locks or any row-lock mode. The driver can represent the default write read-only setting as None; the test verifies the write is not read-only, and exact reads explicitly require True.

Fresh focused results, all with `UV_CACHE_DIR=/private/tmp/rb-b20-uv-cache`:

| Exact command | Observed result |
| --- | --- |
| `uv run pytest tests/integration/phase2/test_b07_schema.py tests/integration/phase2/test_b15_package_schema.py -x` | Exit 0; **36 passed**, 99 warnings in 44.53s. |
| `uv run pytest tests/integration/phase2/test_b20_screening_concurrency.py --tb=short` | Exit 0; **24 passed**, 24 warnings in 33.60s. Includes both first-statement/replay/read cases, observed backend waits/phantoms, comparison Claim serialization, successor/request races, final-clock authorization and rollback/retry cases. |
| `uv run pytest tests/integration/phase2/test_b13_grant_concurrency.py::test_first_statement_inventory_isolation_and_lock_free_history tests/integration/phase2/test_b14_ready_concurrency.py::test_first_sql_and_read_locks_are_exact tests/integration/phase2/test_b17_freeze_concurrency.py::test_literal_first_sql_and_lock_order tests/unit/phase2/test_b20_screening_contract.py::test_database_timeouts_use_sanitized_internal_fallback --tb=short` | Exit 0; **5 passed**, 11 warnings in 7.39s: three PostgreSQL SERIALIZABLE consumption/lock checks plus the two timeout classifications. |
| `uv run pytest tests/unit/phase2/test_b20_screening_contract.py tests/integration/phase2/test_b13_grant_concurrency.py::test_first_statement_inventory_isolation_and_lock_free_history tests/integration/phase2/test_b14_ready_concurrency.py::test_first_sql_and_read_locks_are_exact tests/integration/phase2/test_b17_freeze_concurrency.py::test_literal_first_sql_and_lock_order --tb=short` | Exit 0; **63 passed**, 11 warnings in 8.41s. |

The proposal status value is exactly: **APPROVED by owner 2026-10-19 — first slice authorized for implementation**.

The user now explicitly authorized the full-suite check, superseding the earlier instruction to leave it to the loop. The exact check below was launched after these fixes with the writable UV cache environment prefix; its result is recorded below only after completion:

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && git diff --check HEAD && /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/full_suite_sharded.sh 6
```

The exact command's static stages passed: Pyright 0 errors/0 warnings, Ruff format 746 files, Ruff lint all checks passed, and `git diff --check HEAD` exit 0. Its changed-file pre-check passed **622 tests**, 926 warnings in 541.91s. It then could not acquire its shared coordinator lock: attempts to create/remove `.pipeline/logs/full_suite.lock*` were rejected with `Operation not permitted` by this session's repository/temp-only filesystem sandbox. The runner was interrupted (exit 130) while waiting for that unavailable path; this is **not a PASS of the exact full command**. The shared runner and its lock/duration files were not modified.

Full test verification continues through a temporary-output orchestration at `/private/tmp/b20_review_six_shards.py`, invoked with `UV_CACHE_DIR=/private/tmp/rb-b20-uv-cache uv run python /private/tmp/b20_review_six_shards.py`. It selects all **490** `test_*.py` files, uses the shared runner's greedy duration balancing, creates six fresh PostgreSQL databases, upgrades each to head, and runs the same worker arguments: `uv run pytest -o addopts='' -q -rfE -p no:cacheprovider --junitxml=<temporary-output>/junit-<shard>.xml <shard-files>`. It routes logs/JUnit to temporary files, retains the shared duration data read-only, and drops its fresh databases afterward. It does not alter any test or governing Harness file. Outputs are retained at `/private/tmp/b20-review-shards-1q4zywco`; the final result will be recorded after completion. Write access to the original runner's shared coordination/output paths was requested separately; elapsed time does not grant that access.

Independent read-only comparison of the temporary-output run verified 490 expected files, 490 assigned entries, 490 unique entries, no missing/extra/duplicate files, exact greedy shard assignments (51/86/87/88/89/89 files), identical pytest worker arguments, and all six migration logs reaching 0069. Intentional orchestration differences are output/coordination locations, unique disposable database names and cleanup, retained evidence, omitted shared duration writes, and stopping a shard on migration failure (the original runner proceeds). No tests or selection gates were weakened. The already passing 622-test quick pre-check was not repeated for the temporary-output invocation.

The complete temporary-output six-shard run finished with **exit 0**. Observed per-shard summaries:

| Shard | Observed pytest result |
| --- | --- |
| 0 | 1,241 passed, 680 warnings in 2983.29s |
| 1 | 4,118 passed, 1 skipped, 1,528 warnings in 2988.60s |
| 2 | 1,251 passed, 1,625 warnings in 2935.98s |
| 3 | 1,646 passed, 1 skipped, 1,579 warnings in 2862.67s |
| 4 | 1,700 passed, 2,100 warnings in 3077.76s |
| 5 | 1,226 passed, 51 skipped, 1,543 warnings in 3020.02s |

Aggregate: **11,182 passed, 53 skipped, 0 failed, 0 errors, 9,055 warnings**. JUnit independently reports 11,235 selected cases, 0 failures, 0 errors and 53 skips. Skip reasons are: 48 opt-in large benchmarks; 2 opt-in novelty sampling profiles; 1 opt-in B29 measurement; 1 B04 SUPERSEDED case deferred to its later supersession contract; 1 HG1 live M2 check requiring `HG1_RUN_LIVE=1`. These skipped cases are NOT RUN, not PASS. The six fresh shard databases were dropped after their runs; logs and JUnit remain at the temporary-output path above.

Both reviewer P1 inventory omissions are fixed and the full selected pytest suite has no failing test. The exact shared-runner shell command remains unverified to completion because its outside-workspace coordinator paths are sandbox-denied; no exact-command PASS is claimed. Static checks and the final `git diff --check HEAD` pass. No commit, push, branch creation, shared-runner modification or governing Harness change was performed.
