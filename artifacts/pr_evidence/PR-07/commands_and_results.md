# Commands and results

Executed from `/Users/onephone/Documents/Codex/ResearchBase`.

```text
uv run pytest                                      262 passed in 1.99s
uv run ruff check .                                All checks passed!
uv run pyright                                    0 errors, 0 warnings, 0 informations
DATABASE_URL=... uv run pytest PR-07 integration   21 passed in 0.90s
DATABASE_URL=... uv run alembic upgrade head      0005 -> 0006 successful
DATABASE_URL=... uv run alembic current           0006_artifact_version (head)
disposable migration roundtrip                     upgrade/downgrade/upgrade successful
PostgreSQL server version                          18.6
git diff --check                                   clean
```

The full pytest result included all existing regression tests and real PostgreSQL tests.
