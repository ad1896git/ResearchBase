# Commands and results

- `uv run pytest` with real PostgreSQL: PASS, exit 0; two pre-existing skips.
- PR-09/10/11/12 + PR-13 targeted regression bundle: PASS, exit 0.
- `uv run ruff check .`: PASS.
- `uv run pyright`: PASS, 0 errors/warnings.
- PR-13-owned `ruff format --check`: PASS (5 owned files after phase-guard update).
- repository-wide `ruff format --check .`: inherited P3; 8 pre-existing files would reformat.
- `git diff --check`: PASS.
- PostgreSQL: `18.6`.
- `uv run alembic current`: `0014_claim_evidence (head)`.

Reality-review correction: the old query implementation produced 13/53/231 SELECTs at increasing
fixture scales; prior wording implying bounded reads is withdrawn. See PR-13R for fresh results.
