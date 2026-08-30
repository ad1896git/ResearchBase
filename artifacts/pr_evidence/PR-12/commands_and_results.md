# Commands and results

All commands below were executed from the repository root.

- `DATABASE_URL=... uv run pytest -rA --tb=no` with `PR11R2_MIGRATION_DB_URL=...`: `481 passed in 19.18s`.
- PR-12 integration command covering schema/application/closure/atomicity/concurrency/FK: `35 passed in 1.83s`.
- `uv run ruff check .`: `All checks passed!`
- `uv run pyright`: `0 errors, 0 warnings, 0 informations`.
- Scoped `uv run ruff format --check` over 22 PR-12-owned files: `22 files already formatted`.
- Repository-wide `uv run ruff format --check .`: exit 1 because 8 inherited non-PR-12 files would be reformatted; 104 files were already formatted. No inherited files were modified.
- `uv run alembic current` on the development PostgreSQL database: `0014_claim_evidence (head)`.
- PostgreSQL health query: `PostgreSQL 18.6 on aarch64-unknown-linux-musl, compiled by gcc (Alpine 15.2.0) 15.2.0, 64-bit`.
- Empty disposable PostgreSQL upgrade: base through `0014_claim_evidence`, success; current: `0014_claim_evidence (head)`.
- `0014 -> 0013 -> 0014` Alembic roundtrip: success; current: `0014_claim_evidence (head)`.
- `git diff --check`: pass.
- `git diff --name-only 18fb413...019148e` compared set-equal to `changed_files.txt`.

The full suite and migration tests use real PostgreSQL; SQLite was not used.

## PR-12R reconciliation

The original `481 passed` observation did not prove isolation when migration tests were directed at the shared database. PR-12R used a dedicated disposable migration database, restored it to the dynamically discovered repository head, immediately ran PR-12 targeted tests, and ran the full suite twice. Results were 66 targeted tests, then 483 passed for Run A and 483 passed for Run C. Shared and disposable databases both reported `0014_claim_evidence (head)` after the sequence; no manual Alembic repair occurred between stages.
