# B21 historical unresolved-count first slice

Follow-up: the owner’s full check subsequently found five failures outside the original focused selections. See [review fixes and current verification](review-fixes.md); the original focused-only scope below is historical.

Authority: owner authorization 2026-10-18, the approved B21 first slice, and accepted ADR-0017 Decisions 1–3 including B21-AQ-01. The draft status was changed before implementation. Frozen numbered architecture and existing migrations are unchanged.

Implementation adds only revision `0065_b21_unresolved_capture` after the inspected `0064_b14_publication_ready` head. It adds the two coverage columns, the one typed resolution-membership relation, native-xid/attribution/sealing guards, deferred complete-membership/count checks and populated-v2 downgrade refusal. It validates the frozen shared guard bodies and execution attributes before upgrade; it never replaces shared or sibling guards.

New coverage uses the ADR v2 payload. Legacy v1 material builder and bytes remain unchanged, with explicit unknown historical counts. Saved results come from the existing terminal execution seals; saved resolution references are independently verified with B01's unchanged `resolution_hash`. Current diagnostic counts remain observations of the current read snapshot. Replay preserves the stored material version and saved membership.

Writes retain the existing first-statement N SHARE / READ COMMITTED protocol and request namespace. Exact coverage, comparison and nested assessment reads retain one read-only REPEATABLE READ snapshot and no explicit locks. No consumption transaction or stronger novelty admission changes were made.

## Existing equivalents and bounded test fixtures

- API response schemas already derive from the Application readback dataclasses through `routes._response_schema`; CLI already serializes dataclasses through shared `emit_success`. Updating those readbacks therefore updates existing transports without new route/serializer implementations. Tests verify legacy null and v2 integer output, including nested HTTP and CLI JSON.
- Existing `NoveltyRepository.insert_child` is extended with a concrete membership destination; no separate repository or UoW is introduced.
- Existing `b18_novelty_support.b18_env`, `b01_support`, and `b30_observations` provide owning-service fixtures and SQL/isolation observations. PR2-18 helpers provide native PostgreSQL blocked-lock witnesses.
- The inherited M2 unique constraint prevents normally appending duplicate exact resolution tuples. The all-row verifier case drops that constraint only inside its disposable test database, retaining two independently hashed rows to exercise the required conservative duplicate accounting. Production uniqueness remains unchanged.
- Existing migration-head assertions and inventories were changed only by expected-value updates or appended entries.

## Verification

All commands use the repository's uv environment. `UV_CACHE_DIR=/tmp/researchbase-lane39-uv` keeps the uv cache within writable sandbox storage. PostgreSQL commands use `RB_TEST_ADMIN_URL="${DATABASE_URL%/*}/postgres"` for the explicitly local maintenance database; fixture databases are disposable. The inherited regression run below used `RB_TEST_ADMIN_URL="$DATABASE_URL"` for its normal-role fixture, which does not invoke the stricter maintenance selector. The final capture and migration-head runs use the maintenance URL shown in their commands.

Final commands and observed counts are recorded below. No whole-suite command, commit, push or branch creation is performed.

```sh
UV_CACHE_DIR=/tmp/researchbase-lane39-uv uv run ruff check .
UV_CACHE_DIR=/tmp/researchbase-lane39-uv uv run ruff format --check .
UV_CACHE_DIR=/tmp/researchbase-lane39-uv uv run pyright
UV_CACHE_DIR=/tmp/researchbase-lane39-uv uv run alembic heads
git diff --check
```

Observed: Ruff passed; 706 files already formatted; Pyright 0 errors / 0 warnings / 0 informations; exactly one Alembic head, `0065_b21_unresolved_capture`; whitespace check exited 0. PostgreSQL reported `18.6 (Homebrew)`.

```sh
UV_CACHE_DIR=/tmp/researchbase-lane39-uv uv run pytest -o addopts='' tests/unit tests/architecture tests/test_architecture.py -q
```

Observed: **5490 passed, 49 warnings in 75.15s**. The warnings are the existing Alembic configuration deprecation. This final rerun includes the coverage-only error-normalization cleanup and the completed review fixes.

```sh
RB_TEST_ADMIN_URL="${DATABASE_URL%/*}/postgres" UV_CACHE_DIR=/tmp/researchbase-lane39-uv uv run pytest -o addopts='' tests/integration/phase2/test_b21_capture.py tests/integration/phase2/test_b21_capture_schema.py tests/integration/phase2/test_b21_capture_concurrency.py tests/integration/phase2/test_pr2_18_search_coverage.py -q
```

Observed: **51 passed, 63 warnings in 76.11s**. Coverage includes complete/empty historical membership, all-row ambiguity, duplicate tuple verification, independent current projections, fresh-engine restart, mixed v1/v2 nested read/replay, unchanged v1 digests/references, normal-role guard denials, rollback, downgrade refusal, baseline preflight, both observed resolution/capture lock orders, one read snapshot, no explicit read locks, FIRST SQL N, retry qualification and uncertain-commit replay.

```sh
RB_TEST_ADMIN_URL="${DATABASE_URL%/*}/postgres" UV_CACHE_DIR=/tmp/researchbase-lane39-uv uv run pytest -o addopts='' tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b05_review_migration.py tests/integration/phase2/test_b08_schema.py tests/integration/phase2/test_b14a_entry_schema.py tests/integration/phase2/test_batch_c_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_17_authorship_schema.py tests/integration/phase2/test_revision_action.py -q
```

Observed: **238 passed, 626 warnings in 302.09s**. These are the touched migration/head-expectation suites; their changes are expected head values only. Existing Alembic deprecation and SQLAlchemy connection-options warnings are retained.

```sh
RB_TEST_ADMIN_URL="$DATABASE_URL" UV_CACHE_DIR=/tmp/researchbase-lane39-uv uv run pytest -o addopts='' tests/integration/phase2/test_pr2_18_api.py tests/integration/phase2/test_pr2_18_concurrency.py tests/integration/phase2/test_pr2_18_replay.py tests/integration/phase2/test_pr2_18_schema.py tests/integration/phase2/test_b01_resolution_admission.py tests/integration/phase2/test_b01_resolution_replay.py tests/integration/phase2/test_b01_resolution_schema.py tests/integration/phase2/test_b01_resolution_concurrency.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_20_novelty.py -q
```

Observed: **134 passed, 141 warnings in 675.80s**. This includes inherited schema/replay/authorization/concurrency/error regressions, credential and role expiry after observed waits, the B01 empty-history phantom orders, and bounded G7/benchmark consumers. Warnings are the existing Alembic deprecation and a pytest helper-import rewrite warning.

Final PostgreSQL total across the three explicitly listed, disjoint file selections: **423 passed, 830 warnings**, with zero failed, zero skipped and zero setup errors. Raw successful run output is retained alongside this note in `capture-postgresql.txt`, `migration-head-postgresql.txt`, `inherited-postgresql.txt`, `unit-architecture.txt` and `pyright.txt`.

## Review and evidence boundary

Read-only sub-agent reviews reported no P0/P1 findings. Their P2 findings about strict current counts, preflight execution attributes, overflow normalization and additional transport/legacy replay assertions were addressed and checked in focused runs. All edits were made by the primary agent.

An exploratory migration run used the application database in `RB_TEST_ADMIN_URL`, which the stricter disposable-database selector rejected: 6 failed / 54 passed / 178 setup errors. Its diagnostic rerun stopped after 1 failed test. The corrected maintenance-URL run above passed all 238 tests. An exploratory inherited-regression command used the nonexistent `test_b01_resolution.py` filename and collected zero tests; the actual equivalents are `test_b01_resolution_admission.py` and `test_b01_resolution_replay.py`.

No whole-suite, full G7/benchmark acceptance, Phase-2 exit or cross-order B19/B22 migration-composition result is claimed. B19/B22 implementations are not installed in this checkout. Their guard definitions and product semantics were not changed.
