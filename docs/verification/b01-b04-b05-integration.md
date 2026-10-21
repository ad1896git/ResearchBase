# B01 / B04 / B05 / B06 integration verification — 2026-10-15

The requested verification command exited **0** after B06 integration:
**6165 passed, 50 skipped, 4175 warnings in 5845.99s (1:37:25)**; no failures or
errors. The final migration round trip also passed. **Acceptance remains blocked
by the Git index restriction described below**; not every P1 is resolved.

The integrated migration chain is now:

```text
0047_pr2_18_novelty_prior_art
→ 0048_b04_manuscript_freeze
→ 0049_b05_manuscript_review
→ 0050_b01_resolution_admission
→ 0051_b06_revision_action
```

B01 was renamed from `0048_b01_resolution_admission.py`; only `revision` and
`down_revision` changed. A byte comparison against the applied index version
verified the entire file equals the original after those two substitutions.
The two B04/B05 migration files are byte-identical to HEAD. The inventory records
the new B01 file hash. Current head expectations in CI, the static baseline,
architecture/unit/integration tests and migration allowlists follow the new chain.
The UoW retains both manuscript error normalization and B01 transaction setup/error
normalization. Slice behavior was not changed.

All regenerated `pr_evidence/pr2-20/` directories were removed; only the original
`3ea9a7ac2f6d2a7f04ad79b907e344b24661a6cfc466be11e02dee1f3725836d/`
remains. Its `pyright-000.txt` ends in a single newline.

## Prior focused verification (before B06 integration)

Commands use `UV_CACHE_DIR=/tmp/researchbase-integration-uv uv run --no-sync`.

| Command after that prefix | Result |
| --- | --- |
| `alembic heads` | One head: `0050_b01_resolution_admission (head)`. |
| `ruff check .` | All checks passed. |
| `ruff format --check .` | 566 files already formatted. |
| `pyright` | 0 errors, 0 warnings, 0 informations. |
| `pytest -o addopts='' -q tests/unit tests/architecture tests/test_architecture.py` | 2357 passed, 41 warnings in 45.54s; 0 failures/errors/skips. |
| `pytest -o addopts='' -q tests/architecture/test_b05_review_boundaries.py` | After preserving the explicit B05 → B04 parent assertion: 4 passed, 1 warning in 0.50s. Focused Ruff lint/format checks also passed. |

A disposable PostgreSQL database was created using
`tests.disposable_postgres.disposable_database("researchbase_pr212_test_")`.
Using an Alembic `Config("alembic.ini")` pointed at that database,
`command.upgrade(config, "head")`, `command.downgrade(config, "base")`, then
`command.upgrade(config, "head")` all succeeded. After each operation, querying
`alembic_version` returned respectively `["0050_b01_resolution_admission"]`,
`[]`, and `["0050_b01_resolution_admission"]`. The database was dropped afterward.
The connected server reports PostgreSQL 18.6 (Homebrew), aarch64-apple-darwin27.0.0.

Focused PostgreSQL command: **365 collected; 364 passed, 1 skipped, 842 warnings
in 627.91s (0:10:27); exit 0; 0 failures/errors**. The pre-existing skip is
`test_b05_manuscript_review.py::test_superseded_manuscript_review`, with reason:
“B04 only creates DRAFT/FROZEN; exact SUPERSEDED history awaits the later
supersession contract”.

```sh
UV_CACHE_DIR=/tmp/researchbase-integration-uv uv run --no-sync pytest -o addopts='' -q \
  tests/integration/phase2/test_b01*.py \
  tests/integration/phase2/test_b04*.py \
  tests/integration/phase2/test_b05*.py \
  tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py \
  tests/integration/phase2/test_pr2_03_review_guards.py \
  tests/integration/phase2/test_pr2_04_execution_migration.py \
  tests/integration/phase2/test_pr2_04_migration_coverage.py \
  tests/integration/phase2/test_pr2_15_decision_schema.py \
  tests/integration/phase2/test_pr2_17_authorship_schema.py \
  tests/integration/phase2/test_pr2_19_search_evidence.py \
  tests/integration/phase2/test_revision_action.py
```

## B06 integration and reviewer remediation

B06 was located in the nested lane clone `.pipeline/work/lane9`, commit
`6291c22` (`Implement B06 remaining RevisionAction result shapes`). The earlier
search covered the main repository history and missed the nested clone.

Applied the lane's implementation/tests and merged the shared UoW, database
configuration, Application ports and architecture allowlists. The iterative
`LiteratureEvidenceService._snapshot`, including cycle detection, is byte-identical
to lane9. B04/B05 changes to the shared files remain present.

Renamed `0048_b06_revision_action.py` to `0051_b06_revision_action.py` and re-parented
it on `0050_b01_resolution_admission`. Comparing with lane9 verified that only
`revision` and `down_revision` differ; executable DDL is byte-identical.
B06 migration SHA-256:
`004a272db75d945c10e9e6e318c106f47b2cb37c1421ff75f99240312490ca46`.
Updated all current head assertions to 0051, both lineage allowlists, and the
migration inventory. B06's guard-only downgrade tests now target its immediate
predecessor 0050. Historical migration references remain as lineage/evidence.

The reviewer supplied a pre-B06 full-suite result of **6106 passed, 50 skipped**.
That result is historical and does not validate B06. The new post-B06 run used:

```sh
export UV_CACHE_DIR=$PWD/.uv-cache
export DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase
export RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres
! git grep -nE '^(<<<<<<<|>>>>>>>) ' -- . ':!.pipeline' && test $(uv run alembic heads | wc -l) -eq 1 && uv run pyright && uv run ruff format --check . && uv run ruff check . && uv run pytest -o addopts='' -q -rfE -p no:cacheprovider
```

Full-suite result: **6165 passed, 50 skipped, 4175 warnings in 5845.99s
(1:37:25); exit 0; 0 failures/errors**. The complete requested command exited 0.
Raw pytest output is available locally in
[`tmp/b-integration-full-check.txt`](../../tmp/b-integration-full-check.txt).
Static checks: Pyright reported 0 errors, 0 warnings,
0 informations; Ruff reported 570 files already formatted and all lint checks
passed. The conflict-marker and one-head checks also passed.

Final-chain round trip: **PASS**, using the same disposable-database protocol
above. `alembic_version` returned `["0051_b06_revision_action"]`, `[]`, then
`["0051_b06_revision_action"]` after empty → head → base → head.

`git grep -n 0049_b05_manuscript_review -- docs .github tests` found only B05's
historical implementation evidence/proposal, migration inventory rows, the chain
in this note, B01's parent record, explicit B05 migration-parent/DDL checks, and
migration allowlists. No current-head assertion or CI head check remains at 0049.

## Post-run evidence cleanup

The full run regenerated three directories under `pr_evidence/pr2-20/`; all
three were removed after pytest exited. Both the filesystem directory listing and
this exact command now show only the original directory:

```sh
git ls-files pr_evidence/pr2-20 | cut -d/ -f3 | sort -u
# 3ea9a7ac2f6d2a7f04ad79b907e344b24661a6cfc466be11e02dee1f3725836d
```

`git diff HEAD -- pr_evidence/pr2-20/3ea9*/pyright-000.txt` produced no output.
A byte check verified that this file matches the whitespace-fixed version already
in HEAD, ends in one newline and has no blank EOF line. The whitespace fix survives.

## Git index restriction


`git add .github/workflows/ci.yml docs/phase2/migration_inventory_phase2.md`
was retried during reviewer remediation, and staging all 16 affected paths was
retried again after the full run. Both attempts failed with:
`fatal: Unable to create .git/index.lock: Operation not permitted`.
The sandbox explicitly makes the main `.git` read-only. File conflict markers are
resolved; staged deletion/addition state still needs reconciliation by the host.
No commit, push or branch was created. This unresolved index restriction prevents
claiming every P1 is fixed, regardless of the test result.

The requested status audit,
`git status --short | grep -E '^(DA|AD|UU|AA|DU|UD)'`, still returns 16 `DA`
paths. The runtime/source conflicts are resolved, but this is an open P1. A host
process with write access to the main `.git` must stage the integration changes;
the agent did not bypass the read-only policy or claim that index reconciliation
passed.
