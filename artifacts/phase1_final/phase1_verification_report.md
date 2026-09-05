# Phase 1 fresh verification

Verified accepted HEAD: `5fe5dd90310d68d6df1683307f0d24dd2233c3dd`. Tracked worktree matched that commit throughout verification; original untracked files are enumerated in raw/starting_status.txt. Date: 2026-09-05 (Asia/Shanghai). Final independent review acceptance is a supplied fact; this run is consolidation verification only.

| Check | Fresh result | Exit |
|---|---|---|
| `uv run pytest` | 644 collected; 642 passed; 2 skipped; 0 failed; 0 warnings emitted; 53.13s | 0 |
| `uv run pytest --collect-only` | 644 tests collected in 0.50s | 0 |
| `uv run ruff check .` | All checks passed | 0 |
| `uv run pyright` | 0 errors, 0 warnings, 0 informations | 0 |
| `uv run ruff format --check .` | Exactly 8 inherited P3 files; 158 files already formatted | 1 (accepted P3 exception) |
| `git diff --check` | No output | 0 |
| `uv run alembic current` | `0015_governance_audit (head)`, before and after full pytest | 0 |

Consolidation verification = PASS WITH ACCEPTED P3. This does not relabel the formatter exit code as success.

## Reproduction

Use a checkout of accepted HEAD with `uv` and the committed `pyproject.toml`/`uv.lock`, and a PostgreSQL 18 service with this checkout's migrations already applied through `0015_governance_audit`. The checked-in compose.yaml defines the local development database. The fresh run used:

```bash
export DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase
export UV_CACHE_DIR=/tmp/researchbase-uv-cache
uv run pytest
uv run ruff check .
uv run pyright
uv run ruff format --check .
git diff --check
uv run alembic current
```

Static checks used the project environment; the captured subprocess static checks used uv's default cache. Collection is read-only and does not need DB access. Python and exact package versions are in raw/versions.txt; exact static commands, return codes and timestamps are in raw/checks.json. raw/pytest.txt preserves the captured pytest output; trailing graph padding and a terminal blank line were removed from text logs for whitespace hygiene. Pytest's default `-q` comes from pyproject.toml; no warning suppression was added.

The two skipped cases are `tests/integration/test_pr11r2_migration.py`: its module skip condition requires `PR11R2_MIGRATION_DB_URL`, a separate disposable migration database. It was unset, matching accepted default-suite results. These cases were not newly executed by this consolidation. Historical clean-install/migration evidence is retained; this run does not claim a fresh schema replay.

The first sandboxed Alembic attempt could not connect to localhost (Operation not permitted). The authorized external-sandbox rerun passed; pytest likewise ran with local PostgreSQL access. No verification code issue was found or fixed.

## Architecture and scope

Domain, Application, PostgreSQL infrastructure, HTTP/CLI adapters, provenance, governance, Golden Acceptance, architecture guards and exit evidence are all present and tracked. See capability inventory and raw/architecture_surface.json. Source/migration text and class scans returned no forbidden later-phase implementation. Full-suite collection includes architecture and Golden Acceptance tests.

Consolidation changes only artifacts/phase1_final and a local annotated tag. Production source, schema, migrations and test semantics have zero changes. The separate manifest commit is not the accepted implementation SHA and must never replace the tag target. Its SHA is resolved from Git, not embedded in itself.
