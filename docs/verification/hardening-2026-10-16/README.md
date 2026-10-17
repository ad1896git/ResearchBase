# Hardening lane integration — 2026-10-17

Scope: integrate the existing credential, temporary evidence, and XID hardening
fixes above Batch C. No new commands, canonical schemas, dependencies, or locks.
The full suite was not run; the surrounding loop owns that check and its evidence.

## Changes

The migration is now `0057_xid_wraparound_guards`, parented to
`0056_b10_reconsideration`. The original ten SQL definitions are unchanged byte
for byte. Nineteen corrective definitions are appended, including the current
Batch C versions of three guards already present in the original migration.
The resulting inventory is **26 functions and 43 identity predicates**.
All **58 historical migration files** match `HEAD` byte for byte.

The initial Batch C grep inventory command was:

```sh
rg -n 'xmin::text::bigint|pg_current_xact_id|CREATE.*FUNCTION' migrations/versions/005{2_b*,3*,4*,5*,6*}.py
```

The inventory was then checked against every installed public function at 0056.
This includes trigger helper functions, not just functions returning `trigger`.
The regression compares every installed function before and after 0057, allowing
only `xmin`/current-transaction conversions and corresponding local variable
changes to `xid`. Function bodies, attributes, errors, and lock order otherwise
match exactly. It also checks no-op upgrade, reconnect, and safe-guard retention
when downgrading to 0056. Separate PostgreSQL row tests simulate xid8 epochs
0, 1, and 7; they do not advance the server through a real wraparound.

| Function | Identity predicates |
| --- | ---: |
| allow_impact_target_only_with_new_parent | 1 |
| b07_revision_basis_guard | 1 |
| b07_validate_decision | 1 |
| b07_validate_re_review | 2 |
| b07_validate_revision | 1 |
| b08_check_history | 1 |
| b08_complete_history | 1 |
| b08_event_guard | 3 |
| b08_validate_mapping | 2 |
| b10_child_check | 1 |
| b10_revision_verify | 1 |
| b10_successor_check | 3 |
| b10_validate | 4 |
| b11_check_basis | 1 |
| m3_support_guard | 1 |
| pr210_reference_guard | 2 |
| pr214_issue_guard | 1 |
| pr215_basis_guard | 2 |
| pr216_complete | 3 |
| pr216_event_insert | 2 |
| pr216_grant_guard | 3 |
| pr216_relation_guard | 1 |
| pr216_request_guard | 2 |
| pr217_snapshot_sealed | 1 |
| pr218_child_guard | 1 |
| reject_statistical_result_input_mutation | 1 |

API composition shares the CLI-compatible `LocalIdentityAdapter` across its
credential-dependent services, including the retained Batch C DecisionService
and nested evidence services. Regression coverage checks shared verifier wiring,
HTTP denial, and no commit on denied credentials.

PR2-20 runtime observations, query plans, migration records, manifests, and
benchmark profiles use a separate evidence root. An autouse pytest fixture
redirects it to each test's `tmp_path`; source/subject hashing still uses the
repository. Explicit report generation retains its existing output behavior.
The directory inventory before and after these focused runs contains the same
**nine pre-existing subject directories**, with **zero new directories**.

CI, migration inventories, and current-head expectations now use 0057. The
historical B09/B10 schema comparison explicitly ends at 0056, preserving its
original scope; the new migration's intentional safe-guard retention is verified
separately. The empty round-trip test still upgrades to the actual head,
downgrades to base, and upgrades again.

## Exact focused verification

All commands ran from the repository root. Existing protected environment
variables selected real PostgreSQL 18; no credentials are recorded here.

```sh
UV_CACHE_DIR=.uv-cache uv run ruff check .
UV_CACHE_DIR=.uv-cache uv run ruff format --check .
UV_CACHE_DIR=.uv-cache uv run pyright
UV_CACHE_DIR=.uv-cache uv run alembic heads
```

All exited 0: Ruff checks passed; **609 files already formatted**; Pyright
**0 errors, 0 warnings, 0 informations**; Alembic reports exactly
`0057_xid_wraparound_guards (head)`. An initial Ruff line-length finding in API
composition was corrected with Ruff formatting before the successful run.

```sh
UV_CACHE_DIR=.uv-cache uv run pytest tests/unit tests/architecture tests/test_architecture.py
```

**4879 passed, 42 warnings in 57.00s**; no failures, errors, or skips.

```sh
UV_CACHE_DIR=.uv-cache uv run pytest tests/integration/phase2/test_xid_wraparound_guards.py tests/integration/phase2/test_batch_c_migration.py
```

**6 passed, 12 warnings in 2.86s**; no failures, errors, or skips. Includes the
empty upgrade/base-downgrade/re-upgrade and exact historical B11 schema comparison.

```sh
UV_CACHE_DIR=.uv-cache uv run pytest tests/integration/phase2/test_b07_*.py tests/integration/phase2/test_b08_*.py tests/integration/phase2/test_b09_*.py tests/integration/phase2/test_b10_*.py tests/integration/phase2/test_b11_*.py tests/integration/phase2/test_pr2_18_api.py tests/integration/phase2/test_pr2_20_*.py tests/e2e/test_pr2_20_benchmark.py
```

**475 passed, 48 skipped, 1550 warnings in 609.42s**; no failures or errors.
The 48 skips are the opt-in large benchmark, not passing benchmark evidence.

```sh
UV_CACHE_DIR=.uv-cache uv run pytest tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_pr2_10_discussion_persistence.py tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_approval.py tests/integration/phase2/test_pr2_17_authorship.py tests/integration/phase2/test_pr2_17_authorship_schema.py tests/integration/phase2/test_pr2_18_prior_art.py tests/integration/phase2/test_pr2_18_search_coverage.py tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b05_review_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_revision_action.py
```

**360 passed, 889 warnings in 266.45s**; no failures, errors, or skips.
Warnings in these runs are Alembic configuration deprecations and SQLAlchemy
connection-isolation warnings, reported separately from test outcomes.

The Phase 1 cases also ran against a fresh disposable database at the new head:

```sh
UV_CACHE_DIR=.uv-cache uv run python - <<'PY'
import os
import subprocess
import sys
from tests.disposable_postgres import disposable_database
from tests.integration.phase2.pr2_20_support import upgrade
with disposable_database('researchbase_pr212_test_') as url:
    upgrade(url)
    result = subprocess.run([
        sys.executable, '-m', 'pytest',
        'tests/integration/test_pr11_application.py',
        'tests/integration/test_pr11_schema.py',
        'tests/integration/test_pr14_governance_integration.py',
    ], env={**os.environ, 'DATABASE_URL': url}, check=False)
    if result.returncode:
        raise SystemExit(result.returncode)
PY
```

**43 passed in 1.46s**; no failures, errors, or skips. The disposable database was
dropped after the run.

Final `git diff --check` and the working-file conflict-marker scan exited 0.

## Git index limitation

Conflict markers are resolved in the working files. Recording that resolution
with `git add` failed because the managed filesystem refuses creation of
`.git/index.lock` (`Operation not permitted`). The index therefore still contains
unmerged entries and the new migration remains untracked. No commit, push, or
branch was made. No full-suite or final integration-gate success is claimed.
