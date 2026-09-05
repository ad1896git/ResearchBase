# Baseline Regression Report

Exact reproducible command for the accepted PR-09 through PR-16 baseline:

```bash
DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase UV_CACHE_DIR=/tmp/researchbase-uv-cache uv run pytest -o addopts='' -q \
tests/integration/test_pr09_schema.py \
tests/integration/test_pr09_application.py \
tests/integration/test_pr09r2_proof.py \
tests/integration/test_pr10_schema.py \
tests/integration/test_pr10_application.py \
tests/integration/test_pr11_schema.py \
tests/integration/test_pr11_application.py \
tests/integration/test_pr11r2_migration.py \
tests/integration/test_pr12_schema.py \
tests/integration/test_pr12_application.py \
tests/integration/test_pr12_fk.py \
tests/integration/test_pr12_closure.py \
tests/integration/test_pr12_atomicity.py \
tests/integration/test_pr12_concurrency.py \
tests/integration/test_pr13_queries.py \
tests/integration/test_pr14_schema.py \
tests/integration/test_pr14_governance_integration.py \
tests/integration/test_pr15_api.py \
tests/integration/test_pr16_cli.py
```

Exact result: `156 collected, 154 passed, 2 skipped, 0 failed in 19.35s`.

The two skips are the opt-in PR11R2 migration-matrix cases because `PR11R2_MIGRATION_DB_URL` was not set. The
baseline replay is evidence for accepted PR-09..16 capabilities, not PR-17-specific E2E proof.
