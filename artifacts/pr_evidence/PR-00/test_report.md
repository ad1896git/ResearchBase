# PR-00 Test Report

## Acceptance results

- Python 3.12 environment via uv: PASS (`3.12.14`, locked sync).
- `uv.lock` committed: PASS (bootstrap commit `565fbc95db53b1c7534bacb41870e941c5d10101`).
- PostgreSQL 18 service starts: PASS (`postgres:18-alpine`, server `18.6`, healthy).
- SQLAlchemy 2.0 + psycopg connection smoke: PASS (integration test).
- Alembic empty upgrade: PASS (`0001_empty` at head).
- FastAPI smoke app: PASS (`/health` returned 200 and `{"status":"ok"}`).
- Typer smoke CLI: PASS (`version` and `status` commands).
- Local ArtifactStore put/open/verify smoke: PASS.
- Ruff format: PASS.
- Ruff lint: PASS.
- Pyright: PASS.
- pytest: PASS (9 passed).
- Architecture skeleton: PASS.
- ADR-0001..ADR-0007: PASS; all seven files present.

## Exact test summaries

```text
pytest with DATABASE_URL: 9 passed in 0.28s
pytest -m integration: 1 passed, 8 deselected in 0.23s
pyright: 0 errors, 0 warnings, 0 informations
ruff check: All checks passed!
```
