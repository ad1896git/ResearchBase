# Batch D integration evidence — 2026-10-17

## Integrated scope

Continued the supplied interrupted three-way application of B25/B27 over B12/B13.
B14 remains deferred. Kept one copy of each approved B12/B13/B25/B27 proposal,
including B12's director ruling and B13's implementation reconciliation.

Removed the empty `0052_b27_defensive_closure_read` revision and changed its
architecture assertion to require no B27 migration. The retained history is
0057 → 0058 B12 → 0059 B13. No re-parenting was necessary after removal: every
retained migration file is byte-identical to HEAD, including revision IDs,
parents, filenames and DDL. A direct history/byte audit observed **61 linear
revisions, exactly one head**. CI and conflicting test/baseline expectations use
`0059_b13_grant_consumption`. Updated the live migration inventory and digests;
annotated the original B27 evidence to distinguish its withdrawn empty revision.

Application conflict resolution preserves the accepted approval SHARE-first
release-write protocol and existing Issue-disposition history verification.
Ports retain both lanes' methods. B25's OPEN-history audit verifier and B27's
saved-dependency wrappers remain additive. No behavior was added to resolve
conflicts, and no governing Harness files or dependencies were changed.

## Verification commands

All commands ran from this repository using its frozen uv environment. The
integration database reported **PostgreSQL 18.6 (Homebrew)**. The existing test
fixtures create disposable PostgreSQL databases; SQLite was not used.

```sh
UV_CACHE_DIR=.uv-cache uv run --frozen alembic heads
```

Result: exit 0; `0059_b13_grant_consumption (head)` — exactly one head.

```sh
UV_CACHE_DIR=.uv-cache uv run --frozen pyright
UV_CACHE_DIR=.uv-cache uv run --frozen ruff format --check .
UV_CACHE_DIR=.uv-cache uv run --frozen ruff check .
```

Results: each exit 0. Pyright: **0 errors, 0 warnings, 0 informations**.
Ruff format: **639 files already formatted**. Ruff lint: **All checks passed!**

```sh
UV_CACHE_DIR=.uv-cache uv run --frozen pytest tests/unit tests/architecture -o addopts='' -q -rfE -p no:cacheprovider --tb=short --show-capture=no
```

Result: exit 0; **5121 passed, 42 warnings in 70.01s (0:01:10)**.

```sh
UV_CACHE_DIR=.uv-cache uv run --frozen pytest tests/integration/phase2/test_batch_c_migration.py tests/integration/phase2/test_b12_*.py tests/integration/phase2/test_b13_*.py tests/integration/phase2/test_b25_*.py tests/integration/phase2/test_b27_*.py -o addopts='' -q -rfE -p no:cacheprovider --tb=short --show-capture=no
```

Result: exit 0; **235 passed, 736 warnings in 231.71s (0:03:51)**.
This includes the empty-database head upgrade → base downgrade → head re-upgrade,
full-schema B11 roundtrip comparison, B12/B13 schema/receipt/lifecycle/replay/race
coverage, and B25/B27 validity/audit/defensive-read/corruption/race coverage.

```sh
UV_CACHE_DIR=.uv-cache uv run --frozen pytest tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_17_authorship_schema.py tests/integration/phase2/test_revision_action.py -o addopts='' -q -rfE -p no:cacheprovider --tb=short --show-capture=no
```

Result: exit 0; **143 passed, 298 warnings in 107.58s (0:01:47)**.

```sh
UV_CACHE_DIR=.uv-cache uv run --frozen pytest tests/integration/test_pr12_closure.py tests/integration/test_pr13_queries.py tests/integration/test_pr18_hardening.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_14_internal_review.py tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_18_*.py tests/integration/phase2/test_pr2_19_integrity.py tests/integration/phase2/test_b04_*.py tests/integration/phase2/test_b05_*.py tests/integration/phase2/test_b08_*.py -o addopts='' -q -rfE -p no:cacheprovider --tb=short --show-capture=no
```

Result: exit 0; **438 passed, 1 skipped, 1154 warnings in 520.77s (0:08:40)**.
The skip is the existing `test_superseded_manuscript_review`: B04 creates only
DRAFT/FROZEN; exact SUPERSEDED history awaits its later supersession contract.
It is not counted as passing. This selection covers affected Phase 1 closure,
query-plan, scientific trace, Conclusion/review/Decision/novelty/integrity,
manuscript freeze/review and existing B08 disposition behavior.

```sh
git diff HEAD --check
git status --short --untracked-files=all pr_evidence/pr2-20
git ls-files --others --exclude-standard pr_evidence/pr2-20
```

Results: exit 0 with no output. No new `pr_evidence/pr2-20/<hash>/`
directories or evidence updates remain. Test observations use disposable fixtures.
Warnings include existing Alembic configuration deprecations and already-open
connection execution-option notices. The full suite was **not run**; the outer
loop owns the full sharded check and its evidence.

## Index limitation

Working-tree conflict markers are resolved, but `git add -u` failed with exit 128:
`Unable to create .../.git/index.lock: Operation not permitted`. The sandbox
allows reads of `.git` but prevents updating its index. Consequently 26 paths
remain marked unmerged in the index, and the staged B27 addition still needs its
working-tree deletion staged. A writable-index environment must run `git add -u`
to record these resolutions. No commit, push or branch creation was performed.
No merge or Phase 2 gate acceptance is claimed.
