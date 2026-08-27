# PR-01R Commands and Results

All commands were run from `/Users/onephone/Documents/Codex/ResearchBase`.

## Baseline and scope

| Command/check | Result |
|---|---|
| `git rev-parse a517b31` | PASS; `a517b3174f14ac2f1fb9dd3ead1852404585aa75` |
| `git rev-parse 647facf` | PASS; `647facf1fc4e6973f131a3e3ff64b49c3f81e349` |
| `git log --oneline --decorate -6` | PASS; `c3e7497` is directly on top of `647facf` |
| `git diff --name-status 647facf..c3e7497` | PASS; only the seven listed source/test files changed |
| `git diff --check` | PASS |
| scope audit | PASS; no business tables, migrations, domains, repositories/UoW, state machine, PR-02+, or Phase 2+ files |

## TDD / remediation checks

| Command/check | Result |
|---|---|
| pre-remediation Foundation/architecture suite | PASS; 31 passed |
| RED architecture/scheme tests before implementation | EXPECTED RED; missing `_find_forbidden_imports` and scheme identifiers |
| targeted remediation suite | PASS; 44 passed |
| full code suite without database URL | PASS; 65 passed, 1 skipped because `DATABASE_URL` was unset |
| `uv run ruff check .` | PASS; all checks passed |
| `uv run pyright` | PASS; 0 errors, 0 warnings, 0 informations |
| `uv run pytest tests/architecture tests/unit/foundation` | PASS; 57 passed |
| `uv run --locked ruff format --check .` | PASS; 32 files already formatted |
| `uv lock --check` | PASS; 38 packages resolved |
| `uv sync --locked --python /opt/homebrew/bin/python3.12 --group dev` | PASS; 34 packages checked |

## Real PostgreSQL / Alembic

Colima was restored for verification. `docker-compose ps` reported healthy
`postgres:18-alpine` on `localhost:5432`.

| Command/check | Result |
|---|---|
| `DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase uv run pytest` | PASS; 66 passed |
| same command with `pytest -m integration` | PASS; 1 passed, 65 deselected |
| same `DATABASE_URL` with `uv run alembic current` | PASS; `0001_empty (head)` |
| same `DATABASE_URL` with `uv run alembic upgrade head` | PASS; exit 0 |

SQLite was not used.
