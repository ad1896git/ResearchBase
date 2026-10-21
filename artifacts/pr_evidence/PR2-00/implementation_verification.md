# PR2-00 implementation verification

## Subjects and scope

- Original authorized implementation start: `e756b1392ee25c2753e0837bda8eb905df7de013`.
- Formatter contract subject: `8c45e393c6ba68ab3989acaa4a319bc63c3bea89`.
- Implementation subject: `5b65f6983dd627757ac7ab7b1fb6befe0a832573`.
- Phase 1 frozen semantic baseline: `d2400fbeca835c89bd802a4e9d647bda01cfd115`.
- Migration: `0019_phase2_bootstrap_membership`, parent `0018_current_pointer_same_parent_integrity`.
- PostgreSQL: **18.6**.
- Table inventory: `project_memberships`, `project_role_assignments`, `project_membership_events`, `project_role_events`, `actor_subject_bindings`, `actor_subject_binding_events`, `bootstrap_records`, `actor_enrollment_challenges`.

## Verification results

| Area | Command or tests | Result |
|---|---|---|
| Phase 2 unit | `uv run pytest -o addopts='' tests/unit/phase2 -ra` | 1 passed |
| Architecture | `uv run pytest -o addopts='' tests/architecture/test_pr2_00_boundaries.py -ra` | 3 passed |
| Migration | `uv run pytest -o addopts='' tests/integration/phase2/test_pr2_00_migration.py -ra` | 4 passed |
| Challenges | `uv run pytest -o addopts='' tests/integration/phase2/test_pr2_00_challenges.py -ra` | 1 passed |
| Temporal authorization | `uv run pytest -o addopts='' tests/integration/phase2/test_pr2_00_temporal_auth.py -ra` | 1 passed |
| Concurrency | `uv run pytest -o addopts='' tests/integration/phase2/test_pr2_00_concurrency.py -ra` | 4 passed |
| Identity and ownership | `uv run pytest -o addopts='' tests/integration/phase2/test_pr2_00_identity.py tests/integration/phase2/test_pr2_00_ownership.py -ra` | 4 passed |
| Order-sensitive logging plus contaminating predecessor | `uv run pytest -o addopts='' tests/integration/phase2/test_pr2_00_bootstrap.py::test_first_owner_bootstrap_is_atomic_and_permanently_closes tests/unit/test_pr17dr_logging_config.py::test_application_logging_has_required_context_and_no_credentials tests/unit/test_pr17dr_logging_config.py::test_legacy_event_logging_redacts_credential_bearing_fields tests/unit/test_pr18_error_log_hardening.py::test_structured_logging_redacts_nested_credentials_and_connection_strings_checked tests/unit/test_pr18_error_log_hardening.py::test_structured_logging_redacts_api_keys_authorization_bearer_and_exception_secrets -ra` | 5 passed |
| Full regression | `uv run pytest -o addopts='' -ra` | 1,806 passed, 2 skipped, 0 failed (1,808 collected) |
| Ruff lint | `uv run ruff check .` | PASS: all checks passed |
| Pyright | `uv run pyright` | PASS: 0 errors, 0 warnings, 0 informations |
| Changed-file formatting | Git-derived implementation `.py`/`.pyi` files against the contract subject | 29/29 formatted |
| Diff whitespace | `git diff --check e756b1392ee25c2753e0837bda8eb905df7de013..HEAD` | PASS |

The two full-suite skips are the existing PR11R2 migration tests requiring `PR11R2_MIGRATION_DB_URL`. The suite emitted 31 Alembic `path_separator` deprecation warnings.

## Logging isolation

The four previously order-sensitive logging/redaction tests pass individually and pass after `tests/integration/phase2/test_pr2_00_bootstrap.py::test_first_owner_bootstrap_is_atomic_and_permanently_closes`. The root cause was Alembic `fileConfig()` applying its default `disable_existing_loggers=True` during in-process migration. `migrations/env.py` now calls `fileConfig(..., disable_existing_loggers=False)`. A focused migration regression confirms that the existing `researchbase.commands` logger remains enabled and retains its level, handlers and propagation setting; the logging/redaction assertions were not weakened.

## Migration and Phase 1

A fresh disposable PostgreSQL 18.6 database upgraded with `uv run alembic upgrade 0019_phase2_bootstrap_membership`; `uv run alembic current` reported `0019_phase2_bootstrap_membership (head)`. The frozen-0018 migration test passed, as did empty downgrade and populated-downgrade refusal/data-preservation tests. The Phase 1 schema/constraint/index/row snapshot was identical around the 0019 migration. Test-harness adjustments pin Phase 1-only setup and regression checks to revision 0018; Phase 2 migration tests separately verify 0018→0019. No Phase 1 production source or historical migration changed.

## Formatter baseline delta

The exact repository-wide command remains `uv run ruff format --check .`. Ruff 0.12.12 exits 1 on the original clean archive and the current implementation subject, reporting the same nine inherited frozen Phase 1 files. The set difference `current - baseline` is empty. All 29 Git-derived changed Python files are formatted. The formatter command and configuration were not weakened, and none of the inherited failing files was modified for formatting. See `formatter_baseline.json` for exact sets and exit codes.
