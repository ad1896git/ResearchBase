# PR-18R Hardening Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Close only the independent PR-18 hardening findings while preserving accepted Phase 1 behavior, adding one minimal structured-log redaction fix, and producing executable non-self-referential evidence.

**Architecture:** PR-18R strengthens verification around the existing Application/Core, PostgreSQL catalog, API/CLI, and evidence boundaries. The real provenance/query-service operations remain the source of EXPLAIN SQL; expected catalog definitions come from frozen migrations/contracts; the evidence runner executes and parses the authoritative command registry. No migration, Phase 2 runtime, new endpoint, agent framework, or unrelated production change is permitted.

**Tech Stack:** Python 3.12, pytest, SQLAlchemy/psycopg, PostgreSQL 18, FastAPI/OpenAPI, Typer, Alembic, JUnit XML, JSON/Markdown evidence, Ruff, Pyright.

## Global Constraints

- Start from `cc29016837bb9aca866ae55c0264c90b9267724e` on branch `codex/pr18r`.
- Preserve `phase1-final` at the historical `5fe5dd90310d68d6df1683307f0d24dd2233c3dd` commit.
- Do not add migrations unless a complete frozen manifest proves a required index is absent; the known workspace index omission is a manifest defect because the index exists live.
- Change production code only for the minimal structured-log redaction defect proven by a failing test.
- Keep expected catalog definitions independent from live PostgreSQL observations.
- Use actual production provenance/query-service operations for EXPLAIN evidence; sparse sequential scans are acceptable when structurally justified.
- Evidence must be generated after the implementation subject is frozen and committed separately as evidence-only content.
- All pytest evidence records `total_discovered`, `selected`, `deselected`, `passed`, `failed`, `skipped`, `xfailed`, `xpassed`, `errors`, and `return_code`.
- PostgreSQL-unavailable or unreconciled required checks are `NOT_VERIFIED` and block readiness.
- Stop after evidence generation with `PR18R_SELF_APPROVED: NO` and `PHASE_2_AUTHORIZED: NO`.

---

### Task 1: Freeze the PR-18R worktree and add the red tests

**Files:**
- Modify: `tests/integration/test_pr18_hardening.py`
- Modify: `tests/unit/test_pr18_error_log_hardening.py`
- Modify: `tests/unit/test_pr18_docs_examples.py`
- Modify: `tests/unit/test_pr18_evidence.py`
- Modify: `tests/architecture/test_pr18_boundaries.py`
- Create: `tests/unit/test_pr18_todo_audit.py`

**Interfaces:**
- Tests define the required behavior for later catalog, EXPLAIN, redaction, docs, architecture, TODO, and evidence implementations.
- Existing accepted PR-17 tests remain authoritative where they already prove a boundary.

- [ ] Verify the branch starts at `cc290168`, the worktree is clean, and the historical tag is unchanged.
- [ ] Add failing redaction tests for API keys, mixed-case authorization headers, bearer tokens, DSNs, and exception strings while asserting safe context remains.
- [ ] Add failing catalog tests for the workspace unique index, full expected/observed set reconciliation, and relevant index metadata.
- [ ] Add failing EXPLAIN tests that invoke the real provenance/query-service operations over deterministic PostgreSQL fixtures and inspect normalized plan structure.
- [ ] Add failing API tests that parse documented curl examples and validate them against OpenAPI request/response/status contracts, including a failure envelope.
- [ ] Add failing CLI tests that execute documented commands against isolated application fixtures and check output/error/exit semantics.
- [ ] Add failing evidence tests for complete count fields, command registry execution, JUnit reconciliation, subject/evidence chronology, stale-result rejection, and fail-closed missing PostgreSQL.
- [ ] Add failing TODO tests for repository-relevant marker categories, independent expected scope, disposition vocabulary, and architecture-critical zero counts.
- [ ] Strengthen PR-18 architecture tests to inspect actual imports/interfaces while reusing PR-17 architecture coverage instead of duplicating it with word scans.
- [ ] Run only the new/modified tests and confirm each fails for the intended missing behavior.

### Task 2: Implement minimal structured-log redaction

**Files:**
- Modify: `src/researchbase/foundation/structured_logging.py`
- Test: `tests/unit/test_pr18_error_log_hardening.py`

**Interfaces:**
- Preserve `emit_event`, `emit_application_event`, `emit_uow_rollback`, event ordering, and transaction ownership.
- Extend only the existing redaction behavior to cover sensitive keys and message patterns justified by the failing tests.

- [ ] Extend sensitive-key matching for `api_key`, `apikey`, `authorization`, `access_token`, and related existing credential keys.
- [ ] Extend sensitive-text matching for `Bearer <token>`, DSN passwords, and credential-bearing exception text without redacting ordinary identifiers.
- [ ] Run the redaction tests and existing PR-17D logging/UoW tests until green.
- [ ] Inspect the diff to confirm no transaction, Application error, or event-semantic changes.

### Task 3: Build the complete frozen catalog manifest and real EXPLAIN harness

**Files:**
- Modify: `tests/integration/test_pr18_hardening.py`
- Modify: `artifacts/pr_evidence/PR-18/catalog_verification.json` only after subject freeze
- Modify: `artifacts/pr_evidence/PR-18/query_explain_baselines.json` only after subject freeze

**Interfaces:**
- Define frozen expected index metadata in test/contracts code from migrations and accepted schema contracts, including `uq_workspaces_project_name`.
- Expose deterministic helpers that execute actual Application query-service operations and capture their emitted SQL or compiled query shape for EXPLAIN.

- [ ] Create the expected manifest independently from live discovery, recording schema, table, name, uniqueness, ordered columns, predicate, operator class when material, constraint-backed status, and source migration/contract.
- [ ] Query all relevant public indexes and constraints from PostgreSQL catalogs, compare the complete required set, and separately classify optional/system/automatic indexes.
- [ ] Add representative-cardinality fixtures for at least one provenance/query-service path where an index is planner-usable; use planner controls only as secondary diagnostics.
- [ ] Capture normalized structural EXPLAIN plans for real run-provenance, claim-trace, and governance/impact query-service paths, asserting required relations, joins, predicates, no Cartesian product, and no writes/locks.
- [ ] Run the catalog and EXPLAIN tests against PostgreSQL 18 and verify no migration is needed.

### Task 4: Implement executable documentation contracts

**Files:**
- Modify: `docs/phase1_api_cli_examples.md`
- Modify: `tests/unit/test_pr18_docs_examples.py`
- Test: existing API and CLI contract suites

**Interfaces:**
- Documentation remains limited to existing Phase 1 routes and Typer commands.
- Tests consume OpenAPI, FastAPI TestClient, Typer CliRunner, and Application-backed isolated fixtures.

- [ ] Make API examples explicit about method, path, request/query fields, success status/shape, identifier semantics, and failure envelope/status.
- [ ] Validate each documented API example against current OpenAPI and execute representative success/failure calls through the test client without adding endpoints.
- [ ] Execute documented CLI examples against isolated fixtures and validate output shape, error output, and exit codes.
- [ ] Confirm no production golden workflow command or Phase 2 capability is introduced.

### Task 5: Implement the authoritative evidence runner and count schema

**Files:**
- Modify: `scripts/pr18_evidence.py`
- Modify: `tests/unit/test_pr18_evidence.py`
- Create: focused parser/runner tests if the module boundary requires them

**Interfaces:**
- `AUTHORITATIVE_COMMANDS` is the single ordered registry of required command token arrays.
- `run_authoritative_commands(...)` executes only normalized repository-relative commands and returns machine-readable results.
- `parse_pytest_junit(...)` returns all required count fields plus return code.
- `build_evidence_artifact(...)` requires the actual implementation subject, evidence parent/HEAD, current registry, parsed results, catalog/EXPLAIN/TODO projections, and explicit audit outcomes.
- `validate_evidence_artifact(...)` rejects stale, incomplete, chronologically invalid, credential-bearing, absolute-path, failed, skipped, or inconsistent evidence.

- [ ] Add red tests for command drift, missing targets, credential/absolute path tokens, count arithmetic, PostgreSQL-unavailable, unexpected skips, stale result reuse, wrong subject, and evidence self-reference.
- [ ] Implement command execution and JUnit/machine-readable parsing with fail-closed return codes and complete count fields.
- [ ] Bind command fingerprints and parsed results to the canonical registry; do not accept hand-supplied observed counts.
- [ ] Add Git checks for subject ancestry, evidence-only post-subject changes, separate evidence HEAD, and `non-self-referential-v1` protocol metadata.
- [ ] Add live catalog, EXPLAIN, repository marker, and credential/path audits to the generated artifact.
- [ ] Run the evidence tool tests and reproduce a small command fixture before running the full registry.

### Task 6: Implement repository-wide TODO/FIXME classification

**Files:**
- Modify: `tests/unit/test_pr18_todo_audit.py`
- Create: deterministic TODO audit helper or extend `scripts/pr18_evidence.py`
- Modify: `artifacts/pr_evidence/PR-18/todo_fixme_disposition.md` only after subject freeze

**Interfaces:**
- Marker projection records `path`, `line`, `marker`, `category`, `disposition`, and `rationale`.
- Expected live scope is independent of observed matches and includes production, migrations, tests, docs, evidence/tooling, historical, and generated/vendor categories where present.
- Live dispositions are `CLOSED`, `INTENTIONAL_NONBLOCKING`, `OUT_OF_PHASE`, or `PR18_BLOCKER`.

- [ ] Add failing tests covering `TODO`, `FIXME`, `XXX`, `HACK`, and `TBD` across authorized repository scope.
- [ ] Implement deterministic category/disposition projection with architecture-sensitive review and zero undisposed live markers.
- [ ] Verify P0/P1 architecture marker counts are zero and historical evidence is classified without becoming a live blocker.

### Task 7: Verify, freeze, generate evidence, and stop

**Files:**
- Modify: evidence files under `artifacts/pr_evidence/PR-18/` only after the implementation subject is frozen

- [ ] Run focused red/green suites, then the complete PostgreSQL 18 verification matrix, Ruff, Pyright, and `git diff --check` in a disposable checkout.
- [ ] Reconcile exact full, integration, focused, regression, catalog, EXPLAIN, redaction, docs, architecture, Agent-ready, TODO, and evidence counts.
- [ ] Confirm exactly two inherited PR11R2 opt-in migration skips and zero PR-18-specific/environment skips.
- [ ] Review the implementation diff for production changes; confirm the only production file changed is the minimal redaction module.
- [ ] Commit all semantic code/test/docs/tooling remediation as the PR-18R implementation subject.
- [ ] Run the executable evidence generator against the frozen subject and PostgreSQL 18.
- [ ] Commit generated evidence separately with evidence-only changes.
- [ ] Verify chronology, fingerprints, command equality, no credential/absolute path leakage, and fresh reproduction from a disposable clone.
- [ ] Report `PR18R_SELF_APPROVED: NO`, `READY_FOR_INDEPENDENT_PR18R_REVIEW: YES` only if every P1/P2 gate passes, and stop.
