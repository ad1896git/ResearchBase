# B14a + B14r + B14 integration over B15/B16

Scope: the owner-approved lane applied over `0061_b16_consent_withdrawal`.
No commit, push, branch creation or whole-suite invocation. No new
`pr_evidence/pr2-20/<hash>/` directory.

## Changes and review

- Resolved every working-file conflict, retaining B15/B16 and B14 lane additions
  in manuscript seal verification, UoW flags/error normalization, and inventories.
- Renumbered the lane to 0062/0063/0064, with 0062 following B16. Updated executable
  references, head expectations and migration links. Archived historical command
  output/diffs retain their original revision names.
- Compared the three original lane migrations from the index with the renamed
  files after normalizing revision identifiers/references: all three are otherwise
  byte-identical, including DDL, upgrade and downgrade function bodies.
- Audited all lane `CREATE OR REPLACE FUNCTION` definitions against B15/B16's
  created/replaced functions. No function names overlap. In particular, B16's
  `b09_preheld`, `b13_validate_event`, `b13_complete`, `b15_consent_guard` and all
  `b16_*` functions remain installed. Added a live catalog preservation assertion.
  Exact catalog roundtrips verify predecessor restoration, including `search_path`.
- Retained ApprovalService's unconditional B16 decision prefix, before purpose
  lookup: B09 inventory excluding publications in SHARE, then publications in
  SHARE ROW EXCLUSIVE. Updated READY ordering/retry test adapters and wait
  witnesses to the integrated protocol.
- Added READY decision versus publication INSERT races in both commit orders,
  asserting actual publication relation waits and the first SQL statements.
- Replaced B16's former disposable READY bypass with real B14a/B14r/B14 commands.
  PREPARE-scope assertions exclude the real READY prerequisite's consumed grant.
- Added SERIALIZABLE READY consumption versus same-manuscript consent withdrawal
  in both commit orders. Both commit and READY remains unaffected. Since PREPARE
  issuance requires READY, real PREPARE grants are then issued and a later
  withdrawal is held open while exact READY consumption replay succeeds. That
  withdrawal stales both PREPARE grants; the READY grant/receipt remain CONSUMED
  with exactly one receipt.

Git could not mark index entries resolved: `git add ...` failed creating
`.git/index.lock` with `Operation not permitted`. Working files have zero conflict
markers; Git's unmerged index flags remain. No Git metadata workaround was used.

## Environment and commands

All uv commands below used `UV_CACHE_DIR="$PWD/.uv-cache"` from the repository
root, with the existing `DATABASE_URL` and `RB_TEST_ADMIN_URL`. Dependencies were
installed locally with `uv sync --frozen`; dependency manifests were unchanged.
Server: PostgreSQL 18.6 (Homebrew), aarch64, 64-bit. Tests use disposable databases.

Static verification:

```sh
uv run --no-sync alembic heads
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync pyright
git diff HEAD --check
git diff --check
```

Observed: exactly `0064_b14_publication_ready (head)`; Ruff lint clean;
699 files already formatted; Pyright 0 errors, 0 warnings, 0 informations;
both diff whitespace checks exit 0. A source/test/CI marker scan found none.
Pyright also printed an informational newer-version notice.

Unit and architecture:

```sh
uv run --no-sync pytest tests/unit tests/architecture -o addopts='' -q --tb=short
```

Observed: **5,447 passed, 49 warnings in 63.28s**.

Independent migration roundtrip checks:

```sh
uv run --no-sync pytest \
  tests/integration/phase2/test_b14a_entry_schema.py::test_fresh_upgrade_catalog_and_empty_downgrade \
  tests/integration/phase2/test_b14r_ready_approval_schema.py::test_clean_upgrade_changes_only_four_functions_and_exact_empty_downgrade \
  tests/integration/phase2/test_b16_schema.py::test_roundtrip_restores_exact_0060_function_catalog \
  -o addopts='' -q --tb=short
```

Observed: **5 passed, 24 warnings in 4.47s**. Includes upgrade from empty,
downgrade to B16 and back, B14r's exact predecessor catalog restoration, and
B16's independent 0060 forward reference. The later combined lane run also runs
these files, including the subsequently added B15/B16 preservation assertion.

Formerly conflicted test files (unit/architecture conflicts are covered above):

```sh
uv run --no-sync pytest tests/test_architecture.py \
  tests/integration/phase2/test_b04_manuscript_migration.py \
  tests/integration/phase2/test_b05_review_migration.py \
  tests/integration/phase2/test_b08_schema.py \
  tests/integration/phase2/test_batch_c_migration.py \
  tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py \
  tests/integration/phase2/test_pr2_03_review_guards.py \
  tests/integration/phase2/test_pr2_04_execution_migration.py \
  tests/integration/phase2/test_pr2_04_migration_coverage.py \
  tests/integration/phase2/test_pr2_15_decision_schema.py \
  tests/integration/phase2/test_pr2_17_authorship_schema.py \
  tests/integration/phase2/test_revision_action.py \
  -o addopts='' -q --tb=short
```

Observed: **232 passed, 563 warnings in 214.75s**.

Shared approval/consumption regression:

```sh
uv run --no-sync pytest \
  tests/integration/phase2/test_b09_approval_schema.py \
  tests/integration/phase2/test_b09_approval_concurrency.py \
  tests/integration/phase2/test_b12_prepare_approval.py \
  tests/integration/phase2/test_b12_prepare_schema.py \
  tests/integration/phase2/test_b13_grant_lifecycle.py \
  tests/integration/phase2/test_b13_grant_schema.py \
  tests/integration/phase2/test_b13_grant_concurrency.py \
  -o addopts='' -q --tb=short
```

Observed: **97 passed, 307 warnings in 141.38s**.

Lane verification:

```sh
uv run --no-sync pytest tests/integration/phase2/test_b14*.py \
  tests/integration/phase2/test_b15_package_*.py \
  tests/integration/phase2/test_b16_*.py -o addopts='' -q --tb=short
uv run --no-sync pytest tests/integration/phase2/test_b16_*.py \
  -o addopts='' -q --tb=short
```

Combined run: **458 passed, 1 failed, 1,507 warnings in 547.77s**. The sole
failure was `test_ready_decision_prefix_excludes_publication_insert_phantoms[True]`:
this long-running process collected the earlier Application-creator variant
before its project-row/INSERT witness correction. All **395 B14a/B14r/B14/B15
cases passed** (the exact B14/B15 collection command with `--collect-only`
reported 395). The collection command was:

```sh
uv run --no-sync pytest tests/integration/phase2/test_b14*.py \
  tests/integration/phase2/test_b15_package_*.py --collect-only -o addopts='' -q
```

No combined-run PASS is claimed.

Final B16 rerun against the corrected file: **64 passed, 153 warnings in 85.16s**,
zero skips. This covers every B16 case, superseding that earlier phantom failure,
and includes both enhanced READY/withdrawal overlap cases. Thus all 459 distinct
lane cases have passing focused evidence, across these overlapping runs.

## Diagnostic runs and targeted corrections

An initial B16-consent/B14r-race run returned 45 passed and 4 failed: the four
race witnesses expected advisory waits, but B16 now excludes competitors earlier
at publication relation locks. A six-case correction run (both B14r race pairs
and the new B16 publication phantom pair) passed: **6 passed, 22 warnings in 9.50s**.

An initial B16 concurrency run returned 28 passed and 1 failed. The publication
Application creator waited first at its project row, hiding the intended INSERT
relation witness. The new phantom test uses complete guarded publication/event
SQL, without disabling any guard, to observe that specific relation wait.
Final targeted publication-phantom command:

```sh
uv run --no-sync pytest \
  tests/integration/phase2/test_b16_concurrency.py::test_ready_decision_prefix_excludes_publication_insert_phantoms \
  -o addopts='' -q --tb=short
```

Observed: **2 passed, 6 warnings in 4.29s**, including the explicit publications
relation assertion. Repeating that exact command after the combined process
finished returned **2 passed, 6 warnings in 2.75s**, exit 0.
Final targeted READY/withdrawal command:

```sh
uv run --no-sync pytest \
  tests/integration/phase2/test_b16_concurrency.py::test_ready_consumption_and_same_manuscript_consent_withdrawal \
  -o addopts='' -q --tb=short
```

Observed: **2 passed, 6 warnings in 4.17s**, including concurrent replay during
nonempty PREPARE staling. Counts from overlapping commands must not be added.
Warnings are Alembic's existing path_separator deprecation and existing
SQLAlchemy execution-options warnings; no skipped test is represented as PASS.
