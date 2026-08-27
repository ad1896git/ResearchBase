# PR-01 Commands and Results

All commands were run from `/Users/onephone/Documents/Codex/ResearchBase`.

| Command/check | Result |
|---|---|
| `git status --short --branch` before implementation | PASS; PR-00 HEAD clean except user/input `PR-01_Execution_Pack_v1.0.md` and `.DS_Store` files |
| PR-00 baseline Ruff format | PASS; 18 files already formatted |
| PR-00 baseline Ruff lint | PASS; all checks passed |
| PR-00 baseline Pyright | PASS; 0 errors, 0 warnings, 0 informations |
| PR-00 baseline pytest with PostgreSQL | PASS; 9 passed |
| `pytest tests/unit/foundation` before implementation | EXPECTED RED; six Foundation modules did not yet exist |
| `pytest tests/unit/foundation tests/architecture` after implementation | PASS; 31 passed |
| `uv run --locked ruff format --check .` | PASS; 32 files already formatted |
| `uv run --locked ruff check .` | PASS; all checks passed |
| `uv run --locked pyright` | PASS; 0 errors, 0 warnings, 0 informations |
| `DATABASE_URL=... uv run --locked pytest` | PASS; 40 passed |
| `uv lock --check` | PASS; 38 packages resolved and lock is current |
| `uv sync --locked --python /opt/homebrew/bin/python3.12 --group dev` | PASS; 34 packages checked |
| `uv run --locked alembic upgrade head` | PASS; PostgreSQL migration head remains valid |
| `docker-compose ps` | PASS; PostgreSQL 18.6 container healthy |
| `git diff --cached --check` for PR-01 code | PASS |

## Environment

PR-00's Docker CLI + Compose + Colima environment was reused. PostgreSQL 18.6 remained healthy;
SQLite was not used.
