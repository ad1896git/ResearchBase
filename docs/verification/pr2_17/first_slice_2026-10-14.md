# PR2-17 S1 implementation verification — 2026-10-14

Status: first-slice implementation and focused verification complete. Full-suite verification is reserved for the loop, as directed; no full PR2-17 or M4 acceptance is claimed.

## Scope and continuation

The proposal's status line already exactly reads `APPROVED by owner 2026-10-14 — first slice authorized for implementation`; no replacement was necessary. The interrupted attempt's implementation was reviewed and retained. The director's clarification permits the migration inventory appends that blocked that attempt; both inventories now append only the new filename.

- One new migration, `0046_pr2_17_authorship_preparation.py`, revision `0046_pr2_17_authorship`, follows accepted head `0045_pr2_16_basic_approval`. Existing migrations are unchanged. `uv run alembic heads` reports exactly `0046_pr2_17_authorship (head)`.
- Exactly six S1 contribution/snapshot tables, concrete RESTRICT FKs, checks/indexes, immutable records, creation-transaction child sealing and deferred HUMAN/order/subset/equal-group/coverage guards. Nonempty downgrade refuses to discard retained history.
- Pure validation and literal R2 hash builders, including an independent authorship golden preimage. Author/contribution order is meaningful; corresponding/equal sets normalize without silently deduplicating.
- Exactly four Application methods: `record_contribution`, `create_authorship_snapshot`, `get_contribution`, `get_authorship_snapshot`. Frozen commands/readbacks, repository port/adapter and UoW wiring preserve the Application write boundary.
- UUID-coordinated replay returns saved material with current credential/read entitlement. Ordered locks, advancing database-time checks after waits, sanitized error mappings and private SQLSTATE retry classification follow the guide. Only 40001/40P01 retry, with three total attempts.
- Head and directly derived head-parent expectation values were updated without changing existing test logic. Migration inventory changes append only. CI and the static baseline point at the new head.
- HTTP/CLI transports are omitted because the guide requires separate authorization. No package, consent, freeze, sending, PR2-18 tables/modules, dependencies, commits, pushes or branches were added.
- Two sub-agents performed read-only investigation and final review; only the primary agent wrote files. Neither final review found a P0/P1 issue. Reviewers did not independently execute tests.

Existing-equivalent substitutions: accepted dependency suites are `test_revision_action.py` and `test_approval.py`, rather than invented PR2-15/16 filenames. No semantic or architectural contradiction was found.

## Coverage added during continuation

The earlier missing cases now cover valid maximum tuples, malformed UUID/tuple and extra-field rejection, corresponding/equal set ordering, exact catalog names/key columns/type widths/defaults/indexes/trigger definitions, direct contribution guard failures, corresponding/equal subset failures and equal-group singleton/overlap/coordinate failures. Application tests positively exercise RESEARCHER creation and snapshot replay/new-write/read/credential denial after role loss. Both commands now exercise credential and role expiry during Publication/Project waits and a second Actor wait, asserting actual blocking backend evidence, fresh check times and zero new effects.

## Final executed checks

All `uv` commands below used `UV_CACHE_DIR=/tmp/researchbase-pr217-uv-cache`. The existing environment's DATABASE_URL and RB_TEST_ADMIN_URL were present and used by the established PostgreSQL fixtures. Disposable tests created and dropped isolated databases; no SQLite substitute or custom database URL was used. The new schema tests assert PostgreSQL major version 18.

| Check | Executed | Passed | Failed | Skipped | Blocked |
| --- | ---: | ---: | ---: | ---: | ---: |
| Pyright | static check | 0 errors, 0 warnings, 0 informations | 0 | — | 0 |
| Ruff check | static check | All checks passed | 0 | — | 0 |
| Ruff format check | 491 files | 491 | 0 | 0 | 0 |
| Unit | 1903 | 1903 | 0 | 0 | 0 |
| Architecture | 63 | 63 | 0 | 0 | 0 |
| New PR2-17 PostgreSQL service | 8 | 8 | 0 | 0 | 0 |
| New PR2-17 PostgreSQL schema | 38 | 38 | 0 | 0 | 0 |
| New PR2-17 PostgreSQL concurrency | 26 | 26 | 0 | 0 | 0 |
| Existing dependency/e2e | 193 | 193 | 0 | 0 | 0 |
| Existing changed-head PostgreSQL regression | 52 | 52 | 0 | 0 | 0 |

Final static commands:

```sh
UV_CACHE_DIR=/tmp/researchbase-pr217-uv-cache uv run pyright
UV_CACHE_DIR=/tmp/researchbase-pr217-uv-cache uv run ruff check .
UV_CACHE_DIR=/tmp/researchbase-pr217-uv-cache uv run ruff format --check .
```

Final unit/architecture command:

```sh
UV_CACHE_DIR=/tmp/researchbase-pr217-uv-cache uv run pytest -o addopts='' -ra --tb=short --junitxml=/tmp/pr217-unit-architecture-final.xml tests/unit tests/architecture
```

Result: **1966 passed, 0 failed, 0 skipped**, 5 Alembic deprecation warnings, in 34.65s. Per-directory counts above were read from this run's JUnit XML. New unit tests contribute 62 passes; new architecture tests contribute 3 passes.

Final PostgreSQL first-slice/dependency/e2e command:

```sh
UV_CACHE_DIR=/tmp/researchbase-pr217-uv-cache uv run pytest -o addopts='' -ra --tb=short --junitxml=/tmp/pr217-postgres-final.xml tests/integration/phase2/test_pr2_17_authorship.py tests/integration/phase2/test_pr2_17_authorship_schema.py tests/integration/phase2/test_pr2_17_authorship_concurrency.py tests/integration/phase2/test_pr2_12_publication_draft.py tests/integration/phase2/test_pr2_14_internal_review.py tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_revision_action.py tests/integration/phase2/test_approval.py tests/e2e
```

Result: **265 passed, 0 failed, 0 skipped**, 617 Alembic deprecation warnings, in 209.12s. Counts from this run's JUnit XML: PR2-17 8/38/26; publication draft 5; internal review 9; decision 36; decision schema 3; RevisionAction 51; Basic Approval 69; e2e 20.

Final changed-head regression command:

```sh
UV_CACHE_DIR=/tmp/researchbase-pr217-uv-cache uv run pytest -o addopts='' -ra --tb=short --junitxml=/tmp/pr217-head-regressions-final.xml tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py
```

Result: **52 passed, 0 failed, 0 skipped**, 109 warnings (Alembic deprecation and existing record_property/xunit2 warnings), in 22.86s. Per-file counts: 3, 33, 5, 11.

`git diff --check` completed with exit 0. Existing migration byte/lineage checks passed in the unit, architecture and PostgreSQL runs.

During continuation, initial static checks found two overlong SQL strings and one optional test-variable access; these test-only issues were corrected before the final passing checks. An earlier focused run passed 137 tests (62 unit, 3 architecture, 72 integration), with 85 warnings in 38.24s; those overlapping results are not added to the final counts above. Failures recorded by the interrupted attempt are historical, superseded by these executed final results.

Full suite: **NOT RUN by this agent**, as instructed. The loop's subsequent full-suite output is the required full-suite evidence and is not yet available in this report. No full-suite PASS or broader gate success is claimed.
