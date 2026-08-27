# PR-03R Commands and Results

All commands were run from `/Users/onephone/Documents/Codex/ResearchBase`.

## Baseline and TDD

| Command/check | Result |
|---|---|
| `git rev-parse 4ab6af7` | PASS; `4ab6af705aab50af0a13d9289543eb9a21ea2053` |
| TDD remediation test run before production normalization | EXPECTED RED; 2 raw canonical `TypeError`/`ValueError` failures |
| PR-03R targeted tests | PASS; 27 passed |
| `git diff --check` | PASS |
| migration inventory | PASS; only `0001_empty_bootstrap.py` and `0002_actor_project_workspace.py` |

## Final verification

| Command/check | Result |
|---|---|
| `DATABASE_URL=... uv run pytest` | PASS; 124 passed |
| `DATABASE_URL=... uv run pytest -m integration` | PASS; 16 passed, 108 deselected |
| `uv run pytest tests/architecture` | PASS; 23 passed |
| `uv run ruff check .` | PASS; all checks passed |
| `uv run pyright` | PASS; 0 errors, 0 warnings, 0 informations |
| `uv run --locked ruff format --check .` | PASS; 52 files already formatted |
| `uv lock --check` | PASS; 38 packages resolved |
| `docker-compose ps` | PASS; `researchbase-postgres-1` healthy |
| PostgreSQL server version query | PASS; 18.6 |
| `uv run alembic current` | PASS; `0002_actor_project_workspace (head)` |
| `git merge-base --is-ancestor 4ab6af7 HEAD` | PASS; baseline preserved |
| migration diff from `4ab6af7..HEAD` | PASS; none |

SQLite was not used. No migration or database schema change was made.
