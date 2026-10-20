# B31-S2 implementation evidence — 2026-10-20

Scope: owner-authorized B31-S2 only. PR2-20 adds zero DDL. No existing migration,
production code, S1 files, draft status, or S3–S4 implementation was changed.

The eleven required populated checkpoints (`0044`, `0045`, `0046`, `0047`,
`0048`, `0049`, `0050`, `0053`, `0059`, `0064`, `0067`) now upgrade through
`0068_b21_unresolved_capture` to the discovered current head. Tests compare every
checkpoint table's original columns, complete row manifests, stored hashes, and
concrete FK/child edges before and after upgrade and `engine.dispose()` reconnect.
Formal readers at current head recompute canonical material and compare readbacks;
only current `observed_at` / `evaluated_at` projections are excluded from DTO equality.
Persisted timestamps remain part of exact row manifests. Actual formal reader
connections are checked for one REPEATABLE READ, READ ONLY transaction and no
explicit table/advisory/row locks.

Historical fixture preparation uses accepted compatible downgrades of disposable
owning graphs. B09 refuses populated approval downgrade, so approval history is
created after reaching `0045`. Historical v1 coverage and INCONCLUSIVE material
use the existing B19/B21 fixture pattern at `0047`; the current coverage command
always emits v2. The novelty case also preserves a verified prior-art evidence edge.

Catalog tests independently inspect constraints, indexes, triggers, functions, and
selected column types at `0068`; historical decision constraint replacements are
checked at `0052`, `0054`, and `0056`. The rejected B29 index is absent at `0068`
and current head. Inventory rendering uses the complete discovered linear chain,
with a unit assertion for the 70-revision prefix through `0068`. The documentation
inventory appends a complete current table, preserving historical entries. The
`migration_inventory_phase2.md` hashes for `0069`–`0073` are a snapshot pinned at
that time (lines 185–189), not a live computation.

## Existing-equivalent substitutions and guide corrections

- `0001_empty_bootstrap.py` contains revision `0001_empty`.
- `0046_pr2_17_authorship_preparation.py` contains revision `0046_pr2_17_authorship`.
- This checkout already contains parallel migrations through `0073_b02_strategy_admission`.
  Tests preserve the explicit `0068` boundary and additionally verify actual head.
  No parallel migration or table is authored by S2.
- Later migrations replace `ck_pr214_one_target`, `revision_action_shape`, and
  `ck_b19_novelty_material`; their guide assertions therefore run at explicit `0068`.
  Current readers require later additive columns, so formal readback runs after
  upgrading to current head, with exact checkpoint manifests also checked at `0068`.
- Guide §12.1 labels `novelty_assessments.closeness_criteria` JSONB. Existing migration
  `0066_b19_close_prior_art_basis.py:118` declares `TEXT[]`; the test asserts `text[]`,
  preserving the existing schema and domain criteria collection. No DDL change is made.

Read-only sub-agent investigation and diff review were used; the primary agent was
the only writer. Final re-review reported no remaining P0/P1 findings.

## Verification

Commands use `UV_CACHE_DIR=/private/tmp/rb-lane68-uv` because plain `uv run` could
not initialize the default cache under the filesystem sandbox. PostgreSQL tests
use the existing opt-in `RB_TEST_ADMIN_URL` and disposable local PostgreSQL 18
fixture databases. No full-suite run was performed.

Final focused results (all exit 0):

| Command (each `uv` command prefixed with `UV_CACHE_DIR=/private/tmp/rb-lane68-uv`) | Observed result |
| --- | --- |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 783 files already formatted |
| `uv run pyright` | 0 errors, 0 warnings, 0 informations |
| `uv run pytest tests/unit tests/architecture --tb=short --show-capture=no` | 6184 passed, 55 warnings in 179.25s |
| `uv run pytest tests/integration/phase2/test_pr2_20_migrations.py tests/integration/phase2/test_pr2_20_catalog_plans.py --tb=short --show-capture=no` | 37 passed, 141 warnings in 165.43s |
| `git diff --check` | Exit 0 |

Warnings are the existing Alembic `path_separator` deprecation and SQLAlchemy
connection `execution_options` warning. The new formal read instrumentation
independently checks the actual database isolation and read-only settings.

Intermediate failures were test authoring issues, corrected before these final runs:
current readers attempted against pre-0071 schemas; current evaluation timestamp
comparison; an inventory substring assertion counting predecessor cells; two
fixtures observing a different engine; and the guide's JSONB/Text-array discrepancy.
The pre-fix complete unit/architecture run reported 1 failed / 6183 passed; its
corrected inventory file then passed all 5 tests. The pre-fix complete PostgreSQL
run reported 2 failed / 35 passed; both observer engine issues are fixed in the
final 37-pass run above. No failed check is reported as PASS.
