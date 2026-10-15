# PR2-18 first slice — implementation and verification

This document records historical slice verification. Current integration and
restart evidence is in
[`docs/verification/pr2_17_18/integration_2026-10-14.md`](../../docs/verification/pr2_17_18/integration_2026-10-14.md).
The current instruction reserves the full suite for the loop's check.

Owner authorization: 2026-10-14. The first slice is implemented; this is not
full PR2-18, Phase 2 exit, Human Gate, merge, or deployment acceptance.
The initial handoff used focused verification, as then instructed. The loop's
full-suite review subsequently found three missed migration-head expectations
(3 failed, 5,320 passed, 1 skipped). The owner's follow-up authorizes and requires
a full-suite rerun; see the review remediation below.

## Scope and decisions

- Preserved the exact approved status line. Updated §4 for director-approved
  exact-ID readback and nullable chain navigation, with independent-root listing
  deferred. Updated §7, §11.1, §12.1, §12.2 and the test inventory for director
  decision 3: ordinary READ COMMITTED coverage, first-statement SHARE locks over
  authority/validity **and capture-input tables**, and a direct-SQL guard checking
  actual granted locks and isolation. All director decisions cite 2026-10-14.
- Added domain values and literal R2 hashes, three recording commands and three
  exact-ID reads, a typed repository port, synchronous persistence/UoW wiring,
  six HTTP routes and six literature CLI commands. Only INCONCLUSIVE is admitted;
  both stronger registered outcomes fail before writing and are blocked by DDL.
- Added exactly one migration, now `0047_pr2_18_novelty_prior_art`, after
  `0046_pr2_17_authorship`. Integration renumbered the original PR2-18 revision
  and changed its parent; its DDL remains byte-identical. It owns only the
  prescribed five new tables. All earlier migration files are unchanged. No other PR's implementation/table was
  modified, and no dependency, branch, commit, or push was created.
- Parent/child sets seal atomically. Deferred guards recheck comparison evidence;
  SQL functions pin their search path to prevent temporary-table spoofing.
  Downgrade locks all five tables before checking emptiness, then refuses populated
  history. PostgreSQL tests witness writer/downgrade exclusion and preservation.
- Saved hashes/counts remain separate from timestamped current diagnostics.
  Captured unresolved count is always unknown (`None`); current resolution,
  retraction and validity warnings never rewrite saved material. Reads emit UTC
  datetimes. No support/review/decision/approval/revision/release effect is created.

## Existing equivalents and compatibility updates

The HTTP principal is `api/routes.py::_verified_principal`; the CLI equivalent is
`cli/commands/literature.py::_principal` (director decision 2). Shared CLI invocation
uses the existing `cli/common.py::invoke`. Its new optional fallback parameter
selects exit 1 for novelty, as explicitly required by contract §11.2, while
preserving the inherited exit 70 for existing commands. API paths retain the
existing `/v1` router prefix.

The existing protected source/evidence adapters are enabled with
`enable_revision_action_snapshot_reads`; the command uses ordinary UoWs, not
`begin_serializable`. Retry eligibility is separately tagged only for SQLSTATE
40001/40P01, with three fresh UoW attempts. Unique-predecessor loss, timeouts and
unknown commit outcomes are not retried. Unknown commit tests recover all three
commands by the same UUID.

Shared exhaustive route/migration inventories were extended with precisely the
six routes and one new migration. Every old route assertion, historical migration
hash, and exact-inventory check remains. Head/parent-of-head expectations and CI
were updated to the new revision. These are additive compatibility assertions,
not changes to another lane's implementation.

## Verification environment

Both `DATABASE_URL` and `RB_TEST_ADMIN_URL` reported PostgreSQL **18.6 (Homebrew)**.
Tests use disposable databases. Normal-role guard tests provision a temporary
NOSUPERUSER role using `RB_TEST_ADMIN_URL` and remove it afterward. Race fixtures
use independent engines/backend PIDs, `pg_blocking_pids`, and database clocks.
Expiry tests prove transaction/wait start before expiry, release after expiry,
a fresh post-wait authorization clock, and zero protected records.

The default external uv cache was inaccessible in the earlier attempt. All commands
below used the repository-local cache, without changing dependencies:

```sh
export UV_CACHE_DIR="$PWD/.data/uv-cache"
```

## Initial focused commands and results

These results precede PR2-17/PR2-18 integration. The historical `0046_pr2_18`
revision shown below is now `0047_pr2_18_novelty_prior_art`, parented on
`0046_pr2_17_authorship`. Current combined verification is recorded in
[`docs/verification/pr2_17_18/integration_2026-10-14.md`](../../docs/verification/pr2_17_18/integration_2026-10-14.md).

| Command | Observed result |
| --- | --- |
| `uv run pyright` | 0 errors, 0 warnings, 0 informations; exit 0 |
| `uv run ruff check .` | All checks passed; exit 0 |
| `uv run ruff format --check .` | 498 files already formatted; exit 0 |
| `uv run pytest tests/unit` | 1,902 passed, 4 warnings in 37.15s; exit 0 |
| `uv run pytest tests/architecture tests/test_architecture.py` | 89 passed, 1 warning in 2.69s; exit 0 |
| `uv run pytest tests/integration/phase2/test_pr2_18_*.py` | 77 passed, 81 warnings in 58.55s; exit 0 |
| `git diff --check` | No output; exit 0 |
| `uv run alembic heads` | `0046_pr2_18_novelty_prior_art (head)`; exit 0 |

Every final pytest run above had **0 failures, 0 errors, 0 skips**. The pytest
warnings are inherited Alembic `path_separator` deprecations. Pyright separately
printed an available-version notice; its diagnostic warning count was zero.

PR2-18 PostgreSQL suite counts:

| Suite | Passed |
| --- | ---: |
| `test_pr2_18_search_coverage.py` | 9 |
| `test_pr2_18_prior_art.py` | 13 |
| `test_pr2_18_novelty.py` | 4 |
| `test_pr2_18_replay.py` | 4 |
| `test_pr2_18_schema.py` | 25 |
| `test_pr2_18_concurrency.py` | 22 |
| Total | 77 |

The affected inherited PostgreSQL regression command was:

```sh
uv run pytest \
  tests/integration/phase2/test_pr2_02_source_version_migration.py \
  tests/integration/phase2/test_pr2_03_literature_search_plan_application.py \
  tests/integration/phase2/test_pr2_03_review_guards.py \
  tests/integration/phase2/test_pr2_04_migration_coverage.py \
  tests/integration/phase2/test_m2_metadata.py \
  tests/integration/phase2/test_m3_evidence.py \
  tests/integration/phase2/test_pr2_14_internal_review.py \
  tests/integration/phase2/test_pr2_15_decision.py \
  tests/integration/phase2/test_pr2_15_decision_schema.py \
  tests/integration/phase2/test_revision_action.py \
  tests/integration/phase2/test_approval.py \
  tests/integration/test_pr12_application.py
```

Result: **274 passed, 639 warnings in 337.25s; exit 0; 0 failures/errors/skips**.
Those warnings are the same inherited Alembic deprecation.

Earlier exploratory runs exposed stale route/head inventories and test-fixture
mistakes, which were corrected. One capture-first race test incorrectly held a
second SHARE transaction while launching another capture behind a queued writer;
its disposable backends were terminated and the test was replaced with a barrier
inside the actual capture transaction. Final race runs passed. Failed exploratory
runs are not counted as passing checks.

## Read-only review and boundary

Two read-only sub-agents investigated the contract, existing equivalents and
implementation. The primary agent was the only writer. Review found and led to
fixes for current-validity warnings, frozen-input mappings, deferred verification,
and downgrade exclusion. The primary agent additionally hardened SQL search paths.
The initial read-only reviews reported no open P0/P1 findings within their review
scope. That report did not establish full-suite success; the subsequent loop
found the P1 migration-head regression described above.
All thirteen named §8 architecture obligations are included in the architecture
suite. The earlier `BLOCKED.md` and `snapshot_probe.py` are historical evidence
superseded by director decision 3 and the passing stale-capture regression.

## Review remediation

Updated only the expected head values in the three failing assertions in
`test_pr2_03_literature_search_plan_migration.py` and
`test_pr2_04_execution_migration.py` to `0046_pr2_18_novelty_prior_art`.
The existing table assertions already express their intended inventories and
remain unchanged. No migration or implementation code changed in this revision.

Confirmed populated-downgrade refusal and data preservation are covered by
`test_pr2_18_schema.py::test_catalog_and_empty_downgrade` and the concurrent
`test_populated_upgrade_cannot_be_lost_during_downgrade`. The stale-capture
regression remains `test_stale_serializable_capture_fails_closed`.

The exact requested check, with the repository-local uv cache exported as above:

```sh
uv run pyright && uv run ruff format --check . && uv run ruff check . && uv run pytest -o addopts='' -q -rfE -p no:cacheprovider
```

Result: **PASS, command exit 0**.

| Check | Observed result |
| --- | --- |
| Pyright | 0 errors, 0 warnings, 0 informations |
| Ruff format | 498 files already formatted |
| Ruff check | All checks passed |
| Full pytest suite | **5,323 passed, 1 skipped, 3,021 warnings in 5,059.98s (1:24:19); 0 failures/errors** |

The passing run includes all three corrected migration tests, all 77 PR2-18
PostgreSQL tests, populated-downgrade refusal/preservation, and
`test_stale_serializable_capture_fails_closed`. Warnings comprise the inherited
Alembic `path_separator` deprecations and the existing `TestOwnedInterruption`
collection warning. Pyright also printed an available-version notice separately
from its zero diagnostic warnings. The reviewer-reported P1 full-suite regression
is resolved by this observed passing command; the earlier focused review is not
used as evidence of full-suite success.
