# Commands and results

- `git rev-parse HEAD`: `16695506f285fe015eb15948bb5b07f95f5944aa` before PR-14R2 evidence.
- `git diff -- src tests migrations`: EMPTY before PR-14R2 edits.
- PostgreSQL: healthy, version 18.6.
- `alembic current`: `0015_governance_audit (head)`.
- repository-wide Ruff format: FAIL on exactly eight unchanged historical files.
- PR-14/PR-14R-owned scoped format: PASS.
- Ruff check: PASS.
- Pyright: PASS.
- `git diff --check`: PASS.
- direct Git changed-file inventories: set equality PASS.

The SQL counts, TargetResolver counts, concurrency result, and FK/RESTRICT matrix are recorded from the independent PR-14R review evidence in the dedicated reports.
