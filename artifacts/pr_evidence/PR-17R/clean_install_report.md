# Clean Install Report

On PostgreSQL `18.6`, an isolated empty schema `pr17r_clean_20260905` was created and upgraded with:

```bash
DATABASE_URL='postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase?options=-csearch_path=pr17r_clean_20260905' UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run alembic upgrade head
DATABASE_URL='postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase?options=-csearch_path=pr17r_clean_20260905' UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run alembic current
```

The exact result was `0015_governance_audit (head)`. The schema was then removed after verification.

The normal fresh-current-head E2E fixture also upgrades an independent schema and the corrected GSAS/adapter
selection passed. No migration after `0015` was created.
