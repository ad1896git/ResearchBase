# PR2-02-GOV implementation verification

## Subjects and lineage

- Accepted starting evidence subject: `5e2dee35bc146211cd2294f943f9235978eb916c`.
- Accepted design pack subject: `89bbad27f1e636182fcd5d9804a33612a755502f`.
- Implementation subject: `c00efe323a48da063885377f073e2b14c691b330`.
- Parent migration: `0020_literature_source_identity`.
- Migration owned by this bridge: `0021_source_merge_governance_bridge`.
- Frozen Phase 1 annotated tag object: `63f6a1d28afa79ce8620fc9233793ab9c40a515d`.
- `phase1-final-v4^{commit}` and frozen Phase 1 baseline both resolve to `d2400fbeca835c89bd802a4e9d647bda01cfd115`.
- PostgreSQL version: `18.6`, image `postgres:18-alpine`, temporary container `researchbase-pr2-review-postgres`, host port `55439`.
- Test DB setup: integration fixture creates an isolated disposable database per test from `DATABASE_URL`; example pattern `postgresql+psycopg://researchbase_test:<container-password>@127.0.0.1:55439/researchbase_pr2_test`. Password is read from the local container environment at runtime and is not recorded here. The fixture drops its per-test database after each test. Container cleanup: `docker stop researchbase-pr2-review-postgres` after reviewer checks.

## Implementation summary

Migration 0021 adds the typed proposal, frozen project/link basis, identifier and source basis snapshots, frozen evidence references, per-project approvals, append-only events, request receipts, integrity guards, and empty-only downgrade behavior. Domain/application/persistence provide directed canonical basis hashing and governance proposal, approval/rejection, revocation, supersession, stale detection, replay, scoped reads, and fail-closed authorization. Minimal HTTP and CLI entry points use the same application service. A command discriminator in receipt uniqueness preserves the design review's request-key scope across approve and reject commands.

The temporal authorization ordering now locks the authority rows first and samples `clock_timestamp()` only after those row locks are acquired. Exact approval/rejection replay checks the saved receipt after current authorization and before comparing a changed live basis; new decisions against a stale basis still fail.

## Verification

Commands and results on the implementation tree:

| Check | Command | Result |
|---|---|---|
| Full regression, final run | `DATABASE_URL=postgresql+psycopg://researchbase_test:<container-password>@127.0.0.1:55439/researchbase_pr2_test uv run pytest -o addopts=''` | **PASS** — 1,869 passed, 2 skipped, 0 failed, 1,871 collected, 80.17 s |
| Governance Application + PostgreSQL migration | `uv run pytest -q tests/integration/phase2/test_pr2_02_gov_application.py tests/integration/phase2/test_pr2_02_gov_migration.py` with the same PostgreSQL URL pattern | **PASS in final full run** — all 4 cases passed; an earlier focused attempt exposed a lock-observation assertion issue in the new test, corrected to poll `pg_locks` ungranted rows |
| Temporal lock wait | `uv run pytest -q tests/integration/phase2/test_pr2_02_gov_application.py::test_owner_credential_expiry_during_authority_lock_wait_denies_approval` with the same PostgreSQL URL pattern | **PASS** — confirmed ungranted PostgreSQL lock, waited beyond a 750 ms credential deadline, denied approval, persisted zero approval rows |
| Basis golden vectors and lock-before-clock order | `uv run pytest -q tests/unit/phase2/test_source_merge_basis.py` | **PASS** — 4 passed |
| Lint | `uv run ruff check .` | **PASS** — all checks passed |
| Types | `uv run pyright` | **PASS** — 0 errors, 0 warnings, 0 informations |
| Raw repository formatter | `uv run ruff format --check .` | **FAIL as raw command** — nine files would be reformatted; these are exactly the accepted frozen baseline set listed below |
| Formatter baseline-delta gate | Set difference `current formatter failures - baseline formatter failures` | **PASS_VIA_BASELINE_DELTA** — no new failures; every changed Python file passes the scoped check |
| Changed Python format | `uv run ruff format --check <all changed Python files>` | **PASS** — 25 files already formatted |
| Migration graph | `.venv/bin/alembic heads`; `.venv/bin/alembic history -r '0020:0021'` | **PASS** — one head, 0021 has parent 0020 |
| Diff whitespace | `git diff --cached --check` before commit; `git diff HEAD^ --check` after commit | **PASS** |
| Phase 1 semantic drift | frozen production/domain/migration files compared and full regression Phase 1 contracts run | **NO DRIFT** — no Phase 1 semantic source or frozen migration was changed; Phase 1 regression checks passed in the final full run |

The accepted nine-file formatter baseline is:

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

The raw formatter command remains unchanged and its nonzero result is not reported as PASS.

## Preserved full-suite first failures

Two earlier full-suite attempts each recorded one failure in existing PR2-01 concurrency coverage. Neither result is removed from this record:

1. `tests/integration/phase2/test_pr2_01_source_identity.py::test_concurrent_rejection_and_corrected_rebinding_preserve_one_live_identity` failed once in the prior full run and passed on an isolated rerun.
2. `tests/integration/phase2/test_pr2_01_source_identity.py::test_concurrent_same_key_add_verify_and_reject_replay_one_result` failed once in a subsequent full run (the observed failure was `CONCURRENT_MODIFICATION` during the competing command attempts) and passed on an isolated PostgreSQL rerun. It also passed in the final full run.

The final full run is green, but these first failures concern concurrent identity/idempotency behavior and are explicitly provided for independent severity classification. No post-expiry successful actor challenge consumption was observed; `PR2-00-TEMP-HISTORICAL-TRACE-01` was not reopened.

## Design review carry-forward

The fresh design reviewer returned P0=0, P1=0, P2=1 and readiness YES. The P2 concerned approval receipt uniqueness lacking the command discriminator in the design-level table description. The implementation's receipt key and regression coverage include command scope, so a request UUID shared by approve and reject commands does not alias the two commands. The design review record is `artifacts/pr_evidence/PR2-02-GOV/design_review.md`.

## Changed files

The implementation subject contains the migration, Application/domain/persistence code, HTTP/CLI adapters, architecture/error/CI contract updates, and unit/integration tests. The authoritative file list is the committed file list of implementation subject `c00efe323a48da063885377f073e2b14c691b330`.

Implementation verification status is presented for independent review. This document does not certify its own Git subject.
