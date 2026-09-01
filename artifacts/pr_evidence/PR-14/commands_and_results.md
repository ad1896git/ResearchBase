# Commands and results

- PostgreSQL: healthy, accepting connections, 18.6.
- `alembic current`: `0015_governance_audit (head)`.
- Base/empty install, `0015→0014`, and `0014→0015`: PASS; post-downgrade PR-14 catalog counts were 0/0/0.
- Full pytest: 527 passed, 2 skipped in 21.41s.
- Architecture: 34 passed.
- PR-14 targeted PostgreSQL: 13 passed.
- PR-13 trace/query regression: 15 passed.
- PR-12 Claim/closure regression: 71 passed.
- PR-11 StatisticalResult regression: 50 passed.
- PR-10 Measurement regression: 39 passed.
- PR-09 Run regression: 32 passed.
- Ruff check: PASS.
- Pyright: PASS (0 errors, 0 warnings, 0 informations).
- PR-14-owned format: PASS.
- Repository-wide format: FAIL on eight inherited predecessor files.
- `git diff --check`: PASS.
