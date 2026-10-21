# Batch E integration verification — 2026-10-18

Continued the existing applied lanes and partial working tree. Resolved the benchmark
content conflict by retaining both B18 bounded novelty sampling and the B29 opt-in
measurement runner, using one shared profile implementation. No lane behavior was
changed. Corrected B30 approval test expectations to use the existing decision
SHARE inventory and require its publication lock. No migration was added or edited. The existing linear 0059 → 0060 (B15) →
0061 (B16) history and test/CI head expectations already agreed.

Git index resolution remains blocked: `git add tests/e2e/test_pr2_20_benchmark.py`
failed because the sandbox denies writes to `.git/index.lock`. The working file has
no conflict markers; Git still reports its unmerged index entry. No commit, push,
or branch creation was attempted. This is not an integration gate acceptance claim.

All successful commands below used:

```sh
export UV_CACHE_DIR=/tmp/researchbase-lane30-uv-cache
export DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase_lane30
export RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres
```

The default uv cache was initially inaccessible; rerunning with the explicit
writable cache succeeded. PostgreSQL reported 18.6 (Homebrew), aarch64 macOS.
Only focused selections were run; the whole suite was not run.

## Formatting

```sh
uv run ruff format --check .
```

Exit 0: 678 files already formatted.

## Lint

```sh
uv run ruff check .
```

Exit 0: All checks passed.

## Types

```sh
uv run pyright
```

Exit 0: 0 errors, 0 warnings, 0 informations. An available-version notice was printed. Formatting, lint, and Pyright were rerun after the test correction with the same results.

## Migration head

```sh
uv run alembic heads
```

Exit 0: 0061_b16_consent_withdrawal (head), exactly one head.

## Unit and architecture

```sh
uv run pytest tests/unit tests/architecture tests/test_architecture.py -ra
```

5284 passed, 49 warnings in 77.47s (0:01:17)

## Migration round trips and B15/B16 guards

```sh
uv run pytest tests/integration/phase2/test_batch_c_migration.py tests/integration/phase2/test_b15_package_schema.py tests/integration/phase2/test_b16_schema.py -ra
```

34 passed, 85 warnings in 34.79s

## Changed PostgreSQL and benchmark files

```sh
uv run pytest tests/e2e/test_pr2_20_benchmark.py tests/integration/phase2/test_b01_resolution_concurrency.py tests/integration/phase2/test_b26_finding_impact.py tests/integration/phase2/test_b26_finding_impact_races.py tests/integration/phase2/test_pr2_19_approval_atomicity.py tests/integration/phase2/test_pr2_19_citation_trace.py tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_governance.py tests/integration/phase2/test_pr2_19_grant_consumption_release.py tests/integration/phase2/test_pr2_19_integrity.py tests/integration/phase2/test_pr2_19_lineage.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_19_rejection.py tests/integration/phase2/test_pr2_19_revision_cycle.py tests/integration/phase2/test_pr2_19_search_evidence.py tests/integration/phase2/test_pr2_20_catalog_plans.py tests/integration/phase2/test_pr2_20_novelty.py -ra
```

2 failed, 203 passed, 51 skipped, 532 warnings in 485.81s (0:08:05)

This initial run found two stale B30 test expectations: both decision-stage
current-fact denial cases expected B09_SHARE_SQL instead of the already-existing
B09_DECIDE_SHARE_SQL plus the publication SHARE ROW EXCLUSIVE lock. The test was
corrected to assert both existing decision locks. No production protocol changed.
The full affected file was rerun after correction:

```sh
uv run pytest tests/integration/phase2/test_pr2_19_governance.py -ra
```

31 passed, 93 warnings in 35.59s

The other changed-file cases passed in the initial run. Across that run and the
corrected-file rerun, all 205 non-opt-in changed-file cases have passing evidence;
51 opt-in cases remain NOT RUN (48 large service benchmarks, two large novelty
profiles, one B29 measurement). The whole changed-file selection was not repeated.

The diagnostic command before correction was:

```sh
uv run pytest tests/integration/phase2/test_pr2_19_governance.py -k approval_current_fact_denial -x -ra
```

1 failed, 1 passed, 27 deselected, 6 warnings in 2.21s

## Shared helper regressions

```sh
uv run pytest tests/integration/phase2/test_b25_manuscript_validity.py tests/integration/phase2/test_b25_manuscript_audit.py tests/integration/phase2/test_b25_manuscript_read_races.py tests/integration/phase2/test_pr2_20_migrations.py tests/integration/phase2/test_pr2_20_governance_races.py tests/integration/phase2/test_pr2_20_security.py -ra
```

133 passed, 412 warnings in 170.27s (0:02:50)

## Final hygiene and scope

`git diff --check`, `git diff --cached --check`, and `git diff HEAD --check`
returned exit 0 with no diagnostics. There are no untracked subject directories
under `pr_evidence/pr2-20/`; test observations used pytest temporary directories.

The opt-in large benchmark and full B29 timing measurement were not executed.
B29 clone isolation, index catalog, duplicate-index rejection, and read-only
snapshot behavior are covered by the changed catalog-plan and contract tests.
No candidate index or B29 migration was admitted to application persistence.
