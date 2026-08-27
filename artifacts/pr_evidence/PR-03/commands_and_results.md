# PR-03 Commands and Results

All commands were run from `/Users/onephone/Documents/Codex/ResearchBase`.

## Baseline and implementation

| Command/check | Result |
|---|---|
| `git rev-parse 99e402c` | PASS; `99e402cc01bb189925bcfae0db6ba0016b4ccde9` |
| `git rev-parse HEAD` after implementation | PASS; `9929df67f7b8c296c25ff680faec257048b5a050` |
| TDD RED `uv run pytest tests/unit/foundation/test_versioning.py` | EXPECTED RED; missing `researchbase.foundation.versioning` before implementation |
| targeted PR-03 tests | PASS; 24 passed |
| `git diff --check` | PASS |
| migration inventory | PASS; only `0001_empty_bootstrap.py` and `0002_actor_project_workspace.py` |

## Final verification

| Command/check | Result |
|---|---|
| `DATABASE_URL=... uv run pytest` | PASS; 121 passed |
| `DATABASE_URL=... uv run pytest -m integration` | PASS; 16 passed, 105 deselected |
| `uv run pytest tests/architecture` | PASS; 23 passed |
| `uv run ruff check .` | PASS; all checks passed |
| `uv run pyright` | PASS; 0 errors, 0 warnings, 0 informations |
| `uv run --locked ruff format --check .` | PASS; 52 files already formatted |
| `uv lock --check` | PASS; 38 packages resolved |
| `docker-compose ps` | PASS; `researchbase-postgres-1` healthy |
| PostgreSQL server version query | PASS; 18.6 |
| `uv run alembic current` | PASS; `0002_actor_project_workspace (head)` |

SQLite was not used. No migration or database schema change was made.
