# Task 5 — PostgreSQL test-suite verification

Status: final verification complete, **suite FAIL**. The director accepts the nine
schema failures as known, pending the owner's decision on the forward migration
proposed in [SCHEMA-BLOCKERS.md](SCHEMA-BLOCKERS.md). They remain executed failures;
no gate acceptance or schema repair is claimed.

## Environment and scope

PostgreSQL 18.6 (Homebrew), Python 3.12, repository uv environment. No dependencies
were added. Task 5 made the permitted source/test corrections without changing
migrations, architecture documents or accepted transaction semantics.

**No pristine pre-task baseline exists.** The original run was interrupted, and
subsequent runs already included inherited partial changes. No before/after
comparison against an untouched pre-task tree is supported.

## Final full run

Exact command, run from the repository root:

```sh
export UV_CACHE_DIR="$PWD/.uv-cache"
export DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase
export RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres
uv run pytest -o addopts='' -q -rfE -p no:cacheprovider > docs/verification/task5/full-verified.log 2>&1
```

**4938 passed, 9 failed, 0 errors, 1 skipped**, 2541 warnings, 4770.74 seconds
(1:19:30), exit 1, 4948 cases. This run includes every permitted Task 5 correction.

Evidence: [full output](full-verified.log), [recorded counts](final-counts.json),
[collected cases](nodes-verified.txt), [exact failed cases](remaining-schema-failures.txt),
[reviewed Task 5 diff](final.diff), and [command record](commands.txt).

All nine failures match the recorded failed-case list: eight physical schema
inventory/index cases in `test_pr2_04_schema_coverage.py` and one concrete scoped-FK
case in `test_pr2_04_structural_guard_repair.py`. Protective expectations remain
enabled. [SCHEMA-BLOCKERS.md](SCHEMA-BLOCKERS.md) identifies the frozen contracts,
actual gaps and proposed additive repair; [schema-live-catalog.json](schema-live-catalog.json)
records the read-only PostgreSQL catalog at revision `0042_pr2_15_minimal_decision`.

## Final supporting checks

These commands used the environment above. Exact outputs are linked below.

| Command | Result | Evidence |
|---|---|---|
| `uv run pytest tests/unit tests/architecture tests/test_architecture.py -o addopts='' -q -rfE -p no:cacheprovider` | 1821 passed, 0 failed, 0 errors; 35.58s | [output](unit-architecture-completed-fixes.log) |
| `uv run ruff check .` | PASS | [output](ruff-check-completed-fixes.log) |
| `uv run ruff format --check .` | PASS; 438 files already formatted | [output](ruff-format-completed-fixes.log) |
| `uv run pyright` | 0 errors, 0 warnings | [output](pyright-completed-fixes.log) |
| `git diff --check` | PASS | [command record](commands.txt) |

The architecture scan permits only the exact authorized migration/table pairs
and prohibits `run_versions` across all migrations. The two historical PR11R2
migration cases execute against owned disposable PostgreSQL databases; they are
included in the final full run.

## NOT_RUN

`tests/integration/phase2/test_hg1_runner_live.py::test_four_durable_deployments_authenticate_and_clean_up`
is the single skipped case. It requires four authorized durable M2 installations
on another host, evidence at `/Users/onephone/ResearchBaseData`, and that host's
PostgreSQL Unix socket on port 55440. Those installations and databases were
unavailable. The existing opt-in skip remains; no deployment state was fabricated.

## Cleanup and schema decision

[database-cleanup.log](database-cleanup.log) records the post-run inventory and
removal of three verified orphans from the interrupted run. Zero test databases
remained; the main `researchbase` database was preserved.

The director ruling accepts the **nine schema failures as known**, pending the
owner's decision on the forward migration proposed in
[SCHEMA-BLOCKERS.md](SCHEMA-BLOCKERS.md). This does not authorize that migration or
convert FAIL to PASS. The no-migrations rule remains in force; no branch, commit
or push was created by Task 5.
