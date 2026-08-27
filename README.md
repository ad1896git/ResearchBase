# ResearchBase

ResearchBase is a scientific provenance and traceability foundation. This repository is
currently at Phase 1 / PR-00: repository bootstrap only.

## Development

The canonical environment is Python 3.12 managed with `uv`.

```bash
uv sync --group dev
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest
```

For the PostgreSQL integration gate, start the development database with Docker Compose:

```bash
docker compose up -d postgres
uv run alembic upgrade head
DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase uv run pytest -m integration
```

The repository deliberately contains no scientific business-domain implementation in
PR-00. The content-addressed filesystem store is infrastructure-only smoke functionality.

