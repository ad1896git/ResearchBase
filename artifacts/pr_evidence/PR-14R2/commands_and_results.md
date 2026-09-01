# Commands and results

- `git rev-parse HEAD`: `16695506f285fe015eb15948bb5b07f95f5944aa` before PR-14R2 evidence.
- PR-14R2 evidence payload commit: `3a9cb09ca0c7a84a43c6c12e752c5e41892c3449`.
- PR-14R2 current HEAD after payload commit: `3a9cb09ca0c7a84a43c6c12e752c5e41892c3449`; no later finalization commit.
- `git diff -- src tests migrations`: EMPTY before PR-14R2 edits.
- PostgreSQL: healthy, version 18.6.
- `alembic current`: `0015_governance_audit (head)`.
- repository-wide Ruff format: FAIL on exactly eight unchanged historical files.
- PR-14/PR-14R-owned scoped format: PASS.
- Ruff check: PASS.
- Pyright: PASS.
- `git diff --check`: PASS.
- direct Git changed-file inventories: 17 files (`e57cc7f..b979525`), 29 files (`b979525..16695506`), and 13 evidence files (`16695506..3a9cb09`); set equality PASS.

The SQL counts, TargetResolver counts, concurrency result, and FK/RESTRICT matrix are recorded from the independent PR-14R review evidence in the dedicated reports.
