# B02 first-slice implementation — 2026-10-19

> Review follow-up: the deterministic B07 schema-inventory regression is fixed,
> with 19 affected PostgreSQL tests and 50 new normalization tests passing.
> The requested full-check attempt passed its static gates and 491-case pre-check,
> then was blocked by sandbox permissions on the runner's external mutex path.
> See [review remediation and exact evidence](review-remediation.md); no full-suite
> PASS is claimed.

Implemented under ADR-0020 and the director ruling recorded in
[implementation-blocker.md](implementation-blocker.md). That identity blocker is
**RESOLVED by director ruling**; its original PostgreSQL evidence is retained.
The contract approval status is restored and §§12.4–12.5 explicitly defer Agent
writers until an owning Phase 3 identity/provisioning contract exists.

## Delivered behavior

- Application-only native strategy capture, question admission, researcher-adapted
  hypothesis admission, and three exact historical reads. Composition accepts a
  configured ScientificRAGCapability; absent configuration returns
  ADAPTER_UNAVAILABLE for new captures. No HTTP/CLI command was activated.
- Closed, bounded canonical capture bytes in an existing frozen ResearchBrief
  ArtifactVersion; exact source membership and independent relation hashes.
  Native candidate-v1 still emits no hypotheses. Original prose, warnings,
  contradictions, missing evidence and coverage limitations remain retained.
- Each admission creates one identity, version 1 DRAFT, current pointer and
  immutable typed receipt in one transaction. Initial text/rationale survives
  ordinary draft editing, freezing, supersession and abandonment. Scientific
  hashes/freeze times remain absent on initial DRAFTs.
- Lock-free REPEATABLE READ reads; exact SHARE-first write inventory, request
  advisory lock, fresh DB-time authorization, deferred closure forcing and final
  source/authority checks. Only 40001/40P01 retry, at most three fresh attempts.
  Exhaustion returns CONCURRENT_MODIFICATION; tests also exercise caller recovery
  with the same command ID after a concurrent winner commits.
- Migration `0069_b02_strategy_admission`, directly after
  `0068_b21_unresolved_capture`, adds only the four approved relations and their
  constraints/indexes/guards. Populated downgrade refuses history deletion.
  Existing migrations and scientific hashes are unchanged. Current-head assertions,
  CI's head assertion and additive-schema inventories include this authorized child;
  historical byte pins and static-debt limits remain intact.
- Policy has no actor-type branch. Verified HUMAN roles are tested; unbound HUMAN
  and AGENT principals receive existing FORBIDDEN. The HUMAN-only identity binding
  guard and provisioning interfaces are unchanged.

## Verification

Commands below ran from the repository root. Every PostgreSQL run used the
explicit local disposable-database opt-in:

```sh
export UV_CACHE_DIR="$PWD/tmp/uv-cache"
export RB_TEST_ADMIN_URL='postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres'
```

Static commands (all exit 0):

```sh
UV_CACHE_DIR="$PWD/tmp/uv-cache" uv run ruff check .
UV_CACHE_DIR="$PWD/tmp/uv-cache" uv run ruff format --check .
UV_CACHE_DIR="$PWD/tmp/uv-cache" uv run pyright
git diff --check HEAD
```

Results: Ruff lint **All checks passed!**; Ruff format **750 files already
formatted**; Pyright **0 errors, 0 warnings, 0 informations**. Logs:
[lint](implementation-ruff-check.txt), [format](implementation-ruff-format.txt),
[types](implementation-pyright.txt).

Final unit/architecture command (exit 0):

```sh
RB_TEST_ADMIN_URL='postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres' UV_CACHE_DIR="$PWD/tmp/uv-cache" uv run pytest tests/unit tests/architecture -o addopts='' -q -p no:cacheprovider > /private/tmp/b02-unit-final-clean.txt 2>&1
```

**5690 passed, 50 warnings in 71.14s**.
[Retained output](implementation-unit-architecture.txt).

Final B02 PostgreSQL command (exit 0):

```sh
RB_TEST_ADMIN_URL='postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres' UV_CACHE_DIR="$PWD/tmp/uv-cache" uv run pytest tests/integration/phase2/test_b02_*.py -q -o addopts='' --tb=short > /private/tmp/b02-final-clean.txt 2>&1
```

**98 passed, 195 warnings in 102.17s**.
[Retained output](implementation-postgres-b02.txt). Coverage includes real native
capture/CAS/restart, separate admitting actor, roles and credential loss, source
correction/retraction and owning merge commands, exact replay/unknown commit,
immutable guards and deferred closure, catalog/upgrades/downgrades, observed
backend waits and temporal expiry, bounded retries, and rollback at every write
step. The deterministic constraint-wait test uses test-only coordination; it adds
no production advisory key or lock.

Additional affected additive-schema command (exit 0):

```sh
RB_TEST_ADMIN_URL='postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres' UV_CACHE_DIR="$PWD/tmp/uv-cache" uv run pytest tests/integration/phase2/test_b15_package_schema.py tests/integration/phase2/test_b21_capture_schema.py -q -o addopts='' --tb=short > docs/verification/b02/implementation-postgres-additive.txt 2>&1
```

**38 passed, 69 warnings in 30.48s**.
[Output](implementation-postgres-additive.txt).

Affected PostgreSQL regressions (exit 0):

```sh
RB_TEST_ADMIN_URL='postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres' UV_CACHE_DIR="$PWD/tmp/uv-cache" uv run pytest tests/integration/test_pr04_application.py tests/integration/test_pr04_schema.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_b01_resolution_admission.py tests/integration/phase2/test_b01_resolution_replay.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_18_search_coverage.py tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b05_review_migration.py tests/integration/phase2/test_b08_schema.py tests/integration/phase2/test_b14a_entry_schema.py tests/integration/phase2/test_batch_c_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_17_authorship_schema.py tests/integration/phase2/test_revision_action.py -q -o addopts='' --tb=short > docs/verification/b02/implementation-postgres-regression.txt 2>&1
```

The output file was moved to `/private/tmp/b02-regression-running.txt` during the
run so its changing bytes would not interfere with the unit suite's repository
subject-digest checks; the exact completed output is copied back for retention.

**304 passed, 693 warnings in 497.40s**.
[Retained output](implementation-postgres-regression.txt). This includes the
persisted G2 suffix and every changed historical migration-head assertion.
Warnings include existing Alembic deprecations, fixture rewrite warnings and
an existing SQLAlchemy connection-options warning; no warning is presented as
zero warnings or suppressed to claim a pass.

Temporal evidence retention command (exit 0):

```sh
RB_TEST_ADMIN_URL='postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres' UV_CACHE_DIR="$PWD/tmp/uv-cache" uv run pytest tests/integration/phase2/test_b02_strategy_concurrency.py -k 'initial_wait or fresh_credential_check_after_observed_constraint_wait' -q -s -o addopts='' --tb=short > docs/verification/b02/implementation-temporal.txt 2>&1
```

**4 passed, 27 deselected, 9 warnings in 5.89s**.
[Observed backend waits and DB timestamp evidence](implementation-temporal.txt).

The positive G2 suffix is independently read back from a fresh service in
`test_g2_saved_native_brief_question_and_researcher_adaptation_after_restart`.
Candidate-only zero-scientific-delta tests remain separate. These results do not
claim native hypothesis generation, scientific verification, full G2/Phase 2 gate
success, or a successful provisioned Agent writer.

The full suite was **not run in this turn**; the owner's loop owns that check.
Historical interrupted full-suite-runner evidence in this directory predates this
implementation and is not claimed as current verification. No commit, push or
branch creation occurred.
