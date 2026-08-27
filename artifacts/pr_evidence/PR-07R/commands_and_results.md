# PR-07R commands and results

```text
uv run pytest                                      264 passed in 2.01s
PR-07 PostgreSQL application/schema tests          22 passed in 0.89s
focused PR-03/PR-04/PR-05/contracts/architecture   78 passed in 0.20s
uv run ruff check .                                All checks passed!
uv run pyright                                    0 errors, 0 warnings, 0 informations
scoped PR-07/PR-07R-owned format check             8 files already formatted
repository-wide format check                      8 untouched baseline files reported
PostgreSQL server version                          18.6
alembic current                                    0006_artifact_version (head)
empty -> head -> 0005 -> head                      successful; final 0006 head
git diff --check                                   clean before evidence generation
```

All PostgreSQL tests used the real PostgreSQL service; SQLite was not substituted.
