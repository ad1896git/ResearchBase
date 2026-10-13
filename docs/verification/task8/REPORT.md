# Task 8 — configurable machine paths and retained-host expectations

The Runner and HG1 share environment-backed host configuration. Original defaults
are unchanged; deployment URL/root matching, native peer credentials, UID checks,
private storage checks, root-controlled policy loading, exact server identity and
revision, loopback listeners, and peer/reject HBA checks remain active. README.md
lists every variable and its default. The three historical host shell scripts
accept checkout/branch, Python environment/tools, PostgreSQL binaries, and temporary
root overrides while preserving their existing acceptance and cleanup gates.

Read `docs/verification/task5/REPORT.md` and `task5b/REPORT.md`. Task 5's only
host-path-dependent NOT_RUN was the four-installation Runner test. Its existing
read-only live mode is preserved; `HG1_RUN_LOCAL=1` now runs the same assertions
using four owned disposable databases, real CLI onboarding, and native socket
credentials on the local macOS/PostgreSQL 18.6 host. No retained deployment or
root policy is fabricated. The databases are dropped in fixture cleanup.

No migrations, architecture documents, dependencies, branches, commits, or pushes
were changed or created.

## Final verification commands

All commands ran from the repository root with:

```sh
export UV_CACHE_DIR="$PWD/.uv-cache"
export DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase
export RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres
```

```sh
uv run pytest tests/unit tests/architecture tests/test_architecture.py -o addopts='' -q -rfE -p no:cacheprovider > docs/verification/task8/unit-architecture-final.log 2>&1

HG1_RUN_LOCAL=1 uv run pytest tests/integration/phase2/test_hg1_runner_live.py tests/integration/phase2/test_hg1_enrollment_integration.py tests/integration/phase2/test_hg1_review_integration.py tests/integration/phase2/test_hg1_bound_subject.py tests/integration/phase2/test_m1_local_onboarding.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_m3_real_cli.py tests/integration/phase2/test_m3_p1r1.py tests/integration/phase2/test_m3_p1r2.py -o addopts='' -q -rfE -p no:cacheprovider > docs/verification/task8/integration-final.log 2>&1

uv run ruff check . > docs/verification/task8/ruff-check.log 2>&1
uv run ruff format --check . > docs/verification/task8/ruff-format.log 2>&1
uv run pyright > docs/verification/task8/pyright.log 2>&1
for script in scripts/*.sh; do bash -n "$script" || exit; done
git diff --check
```

| Check | Exact final result |
| --- | --- |
| Unit + architecture | 1837 passed, 0 failed, 0 errors, 0 skipped; 2 warnings; exit 0 |
| Affected PostgreSQL integration | 36 passed, 0 failed, 0 errors, 0 skipped; 51 warnings; exit 0 |
| Ruff | All checks passed; exit 0 |
| Ruff format | 456 files already formatted; exit 0 |
| Pyright | 0 errors, 0 warnings, 0 informations; exit 0 |
| Shell syntax (all `scripts/*.sh`) | PASS; exit 0 |
| `git diff --check` | PASS; exit 0 |

Pyright also prints an informational newer-version notice; no dependency was
updated. The final PostgreSQL run includes the formerly skipped Runner case.
This is affected-suite verification, not a rerun of Task 5's entire scientific
suite or a change to its known schema-failure disposition.

## Corrections during verification

The first local Runner attempt failed because Alembic's environment URL took
precedence over the fixture's Config URL. The fixture now sets `DATABASE_URL`
explicitly before each migration. An initial combined PostgreSQL run had
35 passed / 1 failed: the enrollment test patched the removed `DURABLE_ROOT`
constant. That fixture now uses `RB_HOST_DURABLE_ROOT`; the focused rerun had
2 passed / 0 failed. Final combined results above supersede those intermediate
failures. No production guard was weakened to address them.

Cleanup verification (exit 0; result `0` test databases remaining):

```sh
/opt/homebrew/opt/postgresql@18/bin/psql postgresql://researchbase:researchbase@localhost:5432/postgres -Atc "SELECT count(*) FROM pg_database WHERE datname LIKE 'researchbase_t8_%'"
```
