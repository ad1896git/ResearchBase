# Commands and results

Executed from `/Users/onephone/Documents/Codex/ResearchBase`.

```text
uv run pytest                                      264 passed in 2.01s
uv run ruff check .                                All checks passed!
uv run pyright                                    0 errors, 0 warnings, 0 informations
DATABASE_URL=... uv run pytest PR-07 integration   22 passed in 0.89s
focused contract/architecture/store tests          78 passed in 0.20s
uv run ruff format --check .                       9 inherited baseline files reported
scoped PR-07-owned format check                    7 files already formatted
DATABASE_URL=... uv run alembic upgrade head      0005 -> 0006 successful
DATABASE_URL=... uv run alembic current           0006_artifact_version (head)
disposable migration roundtrip                     upgrade/downgrade/upgrade successful
PostgreSQL server version                          18.6
git diff --check                                   clean
```

The full pytest result included all existing regression tests and real PostgreSQL tests.
The repository-wide format result is not claimed as PASS because the nine inherited files
remain unformatted; all PR-07/PR-07R-owned files pass the scoped check.
