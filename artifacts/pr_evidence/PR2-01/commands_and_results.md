# PR2-01 Acceptance Evidence

## Subjects and scope

- PR: `PR2-01`
- Starting branch: `phase2/entry-gate`
- Starting subject: `fcc3b132f648789d948943493289d1fbc4f55dbc`
- Frozen Phase 1 tag object: `63f6a1d28afa79ce8620fc9233793ab9c40a515d`
- Frozen Phase 1 peeled commit: `d2400fbeca835c89bd802a4e9d647bda01cfd115`
- Phase 1 semantic drift: `NO`
- Implementation commits: `68febb50e9d5ca309907673061448165823e4c42` (feature) → `414e59e6deb08904269de8b4b5e9351af2d4d85a` (final race coverage)
- Final implementation subject: `414e59e6deb08904269de8b4b5e9351af2d4d85a`
- Migration: `0020_literature_source_identity`, parent `0019_phase2_bootstrap_membership`
- PostgreSQL: `PostgreSQL 18.6`
- Production scope: five source-identity tables, typed identifier normalization, command/query Application service, PostgreSQL repository, HTTP/CLI adapters, stable errors, CI migration-head assertion.
- Excluded scope: SourceVersion/current pointer, merge/alias, providers/search, evidence/citation/manuscript, governance, Agent Runtime, and edits to migration 0019.

Changed production and configuration files:

```text
.github/workflows/ci.yml
migrations/versions/0020_literature_source_identity.py
pyproject.toml
src/researchbase/api/app.py
src/researchbase/api/errors.py
src/researchbase/api/routes.py
src/researchbase/application/ports.py
src/researchbase/application/source_identity.py
src/researchbase/cli/app.py
src/researchbase/cli/commands/literature.py
src/researchbase/cli/composition.py
src/researchbase/cli/context.py
src/researchbase/cli/errors.py
src/researchbase/domain/source_identity.py
src/researchbase/foundation/errors.py
src/researchbase/persistence/source_identity_repository.py
src/researchbase/persistence/uow.py
uv.lock
```

Changed and added tests:

```text
tests/architecture/test_import_boundaries.py
tests/e2e/test_phase1_failure_recovery.py
tests/integration/phase2/test_pr2_01_migration.py
tests/integration/phase2/test_pr2_01_source_identity.py
tests/unit/foundation/test_errors.py
tests/unit/phase2/test_source_identifier_normalization.py
tests/unit/test_pr15_http.py
tests/unit/test_pr15r_route_contract.py
tests/unit/test_pr16_cli_errors.py
```

## Environment and reproducibility

The PostgreSQL 18.6 service was already reachable through the local SSH forward at `localhost:5432`; no container was started. Use an explicitly supplied URL with this shape (credentials are placeholders):

```text
DATABASE_URL=postgresql+psycopg://<test-user>:<test-password>@localhost:5432/<maintenance-database>
```

The Phase 2 PostgreSQL fixture creates a uniquely named `researchbase_pr2_test_<uuid>` database for each test, points `DATABASE_URL` at it, terminates remaining sessions, and drops it in fixture cleanup. Commands below used the local environment’s test credentials without recording them here. The broad regression command also received `DATABASE_URL` inline.

## Verification

Focused PR2-01 command:

```bash
DATABASE_URL='postgresql+psycopg://<test-user>:<test-password>@localhost:5432/<maintenance-database>' \
  uv run pytest -o addopts='' \
  tests/integration/phase2/test_pr2_01_migration.py \
  tests/integration/phase2/test_pr2_01_source_identity.py \
  tests/unit/phase2/test_source_identifier_normalization.py -q
```

Result: **44 passed**, 17 Alembic `path_separator` deprecation warnings, 0 failed.

Full regression command:

```bash
DATABASE_URL='postgresql+psycopg://<test-user>:<test-password>@localhost:5432/<maintenance-database>' \
  uv run pytest -o addopts=''
```

Result: **1,861 passed, 2 skipped, 71 warnings, 0 failed** (78.45 seconds). This includes the PR2-00 challenge and temporal regression tests, Phase 1 frozen acceptance tests, architecture tests, and the complete repository suite.

Other checks:

| Check | Result |
|---|---|
| `uv run ruff check .` / `.venv/bin/ruff check .` | PASS |
| `uv run pyright` / `.venv/bin/pyright` | PASS, 0 errors, 0 warnings, 0 informations |
| `UV_CACHE_DIR=/private/tmp/researchbase-phase2-uv-cache uv lock --check --offline` | PASS, resolved 38 packages |
| `git diff --check` | PASS |
| `uv run alembic heads` | PASS, unique head `0020_literature_source_identity` |
| `uv run alembic history -r 0018_current_pointer_same_parent_integrity:head` | PASS, 0018 → 0019 → 0020 linear ancestry |
| Phase 1 catalog comparison in `test_pr2_01_schema_has_five_owned_tables_and_no_phase1_alters` | PASS, prior Phase 1 catalog unchanged |
| PostgreSQL migration/constraint tests | PASS: fresh install, 0018→0019→0020, five-table inventory, catalog preservation, populated downgrade refusal, live identifier uniqueness, immutable source trigger |
| Architecture import boundary | PASS |

### Formatter baseline accounting

Raw repository-wide command:

```bash
.venv/bin/ruff format --check .
```

Raw result: **FAIL**, 9 files reported. They are the accepted frozen baseline set:

```text
migrations/versions/0004_experiment_spec.py
scripts/pr17dr_evidence.py
tests/integration/test_pr04_application.py
tests/integration/test_pr04_schema.py
tests/integration/test_pr05_application.py
tests/integration/test_pr05_schema.py
tests/integration/test_pr06_application.py
tests/unit/domain/test_pr05_experiment.py
tests/unit/test_pr17dr2_evidence.py
```

Every PR2-01-added or modified Python file passed the targeted `ruff format --check` command. Current failures minus the authorized nine-file starting baseline is the empty set. Formatter gate: **PASS** (`FORMAT-BASELINE-01`). The repository-wide raw command is reported as nonzero, not PASS.

## Concurrency and temporal evidence

- Same-key register, add, verify, and reject races return one durable DTO/result; rollback-injection cases verify receipt and protected state commit atomically. Registration races cover with and without initial identifier flows.
- Distinct-key identifier collision returns `IDENTIFIER_ALREADY_BOUND`; concurrent rejection/rebinding leaves one rejected historical row and one live corrected row.
- The lock-wait test holds the real project advisory lock, observes an ungranted advisory lock in `pg_locks`, waits until PostgreSQL time passes the credential validity deadline, releases the lock, and asserts the retried command’s authorization timestamp is after the deadline, the command returns `AUTHENTICATION_REQUIRED`, and no source was written.
- No test produced successful post-expiry challenge consumption or contradictory challenge timing evidence. The accepted residual issue remains `PR2-00-TEMP-HISTORICAL-TRACE-01`, `ACCEPTED_NONBLOCKING`, `UNPROVEN_HISTORICAL_EVENT`; reopened: **NO**.

## Review state

This evidence subject is committed before the independent review. Independent reviewer verdict and finding counts are pending and will be recorded in a separate review evidence update after the review completes.

## Independent review

- Reviewer: one fresh, review-only independent context; it made no repository changes.
- Verdict: **PASS**.
- Findings: `NEW_P0_GAPS=0`, `NEW_P1_GAPS=0`, `NEW_P2_GAPS=0`.
- Independently rerun focused PR2-01 PostgreSQL migration/source identity/temporal suite: **44 passed, 0 failed**.
- Independently rerun full regression suite: **1,861 passed, 2 skipped, 71 warnings, 0 failed** (77.53 seconds).
- Independent Ruff, Pyright, changed-file formatter, ancestry, Phase 1 tag, and clean-worktree checks passed. Repository-wide formatter output matched the same nine-file frozen baseline; no new failures were found.
- The reviewer's initial run lacked `DATABASE_URL` and was blocked by loopback sandbox restrictions. After the local PostgreSQL connection was permitted and the explicit test URL was supplied, the focused and full reruns above completed successfully. The initial attempt was an environment setup error, not a test failure.

## Acceptance checkpoint

- PR2-01 accepted: **YES**.
- Implementation subject: `414e59e6deb08904269de8b4b5e9351af2d4d85a`.
- Evidence subject reviewed: `defcfdd1020470ca008e2773f9bb4c055e84d653`.
- PR2-00 residual `PR2-00-TEMP-HISTORICAL-TRACE-01`: remains `ACCEPTED_NONBLOCKING / UNPROVEN_HISTORICAL_EVENT`; no reopen condition occurred.
- Next PR: **NONE AUTHORIZED**. The PR2-01 execution pack explicitly says “no implicit PR2-02” and grants no implementation permission; the repository contains no PR2-02 execution pack. Stop pending a separately authorized PR and execution pack.
