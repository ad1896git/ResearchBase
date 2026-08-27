# PR-02 Commands and Results

All commands were run from `/Users/onephone/Documents/Codex/ResearchBase`.

## Baseline and scope

| Command/check | Result |
|---|---|
| `git rev-parse 99e0888` | PASS; `99e088812e8ce86ddaceec7f731bc9ae913c33e0` |
| `git rev-parse dd69bbf` | PASS; `dd69bbff27971b9ce4065d06a321f3c278e728a1` |
| baseline `uv run pytest` before PR-02 | PASS; 65 passed, 1 skipped |
| baseline `uv run ruff check .` | PASS; all checks passed |
| baseline `uv run pyright` | PASS; 0 errors, 0 warnings, 0 informations |
| TDD RED PR-02 tests | EXPECTED RED; missing `researchbase.domain` and application command modules |
| `git diff --check` | PASS |
| scope audit | PASS; only Actor/Project/Workspace, ports, adapters, UoW, application commands, migration, and their tests |

## Code and architecture verification

| Command/check | Result |
|---|---|
| domain unit tests | PASS; 5 passed |
| architecture tests | PASS; 22 passed |
| `uv run ruff check .` | PASS; all checks passed |
| `uv run pyright` | PASS; 0 errors, 0 warnings, 0 informations |
| `uv run --locked ruff format --check .` | PASS; 47 files already formatted |
| `uv lock --check` | PASS; 38 packages resolved |
| full PostgreSQL pytest | PASS; 92 passed |
| integration pytest | PASS; 16 passed, 76 deselected |

## PostgreSQL / migration verification

The local service reported healthy `postgres:18-alpine` on `localhost:5432`; direct server
version query reported PostgreSQL 18.6 on aarch64 Alpine.

| Command/check | Result |
|---|---|
| `uv run alembic upgrade head` from `0001_empty` | PASS; created `0002_actor_project_workspace` |
| `uv run alembic downgrade 0001_empty` | PASS; PR-02 tables removed |
| `uv run alembic upgrade head` | PASS; PR-02 tables recreated |
| `uv run alembic current` | PASS; `0002_actor_project_workspace (head)` |
| transaction commit test | PASS |
| explicit rollback test | PASS |
| exception rollback test | PASS |
| atomic multi-repository rollback test | PASS |
| PostgreSQL FK/CHECK/unique constraint tests | PASS |

SQLite was not used. No PR-03 or later implementation was started.
