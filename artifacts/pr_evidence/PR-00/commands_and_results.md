# PR-00 Commands and Results

All commands were run from `/Users/onephone/Documents/Codex/ResearchBase`.

| Command/check | Result |
|---|---|
| `git init` | PASS; independent repository created in ResearchBase |
| `sha256sum -c MANIFEST_SHA256.txt` | PASS; all packaged manifest entries verified |
| `/opt/homebrew/bin/python3.12 --version` | PASS; Python 3.12.14 |
| `uv lock --python /opt/homebrew/bin/python3.12` | PASS; 38 packages resolved |
| `uv sync --locked --python /opt/homebrew/bin/python3.12 --group dev` | PASS; `.venv` created and dependencies installed |
| `uv run --locked ruff format --check .` | PASS; 18 files already formatted |
| `uv run --locked ruff check .` | PASS; all checks passed |
| `uv run --locked pyright` | PASS; 0 errors, 0 warnings, 0 informations |
| `DATABASE_URL=... uv run --locked pytest` | PASS; 9 passed |
| `uv run --locked researchbase version` | PASS; output `0.1.0` |
| `uv run --locked researchbase status` | PASS; output `ok` |
| `docker-compose config` | PASS; PostgreSQL 18 Compose profile rendered |
| `docker-compose ps` | PASS; `postgres:18-alpine` healthy |
| Docker container `show server_version` | PASS; PostgreSQL 18.6 |
| `uv run --locked alembic upgrade head` | PASS; revision `0001_empty` applied |
| `DATABASE_URL=... uv run --locked pytest -m integration` | PASS; 1 passed, 8 deselected |
| `uv run --locked alembic current` | PASS; `0001_empty (head)` |
| `git diff --check` | PASS |

## Environment notes

Docker Desktop installation was attempted but the installer required an unavailable sudo
password. Homebrew Docker CLI, Compose, and Colima were installed instead. Colima was started
successfully, its temporary VM DNS was repaired, and the required real PostgreSQL 18.6 service
was verified through Docker Compose.

