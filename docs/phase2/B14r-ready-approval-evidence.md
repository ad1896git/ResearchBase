# B14r READY approval gate — implementation evidence

Owner authorization: 2026-10-18, first slice only. The proposal's status line records that authorization. This evidence does not assert B14 transition/consumption or Phase 2 acceptance.

## Implementation

- Existing `ApprovalService` request/decision dispatch now accepts the exact READY_FOR_SUBMISSION manuscript tuple using the saved B11 READY/PROCEED Decision. It preserves the full saved review set, validates later reviews, B08 Issue histories and finite applicable blockers, current validity, full CAS/closure, exact B14a entry and selected INTERNAL_REVIEW manuscript, and independent current HUMAN APPROVER authority.
- New writes use the unchanged unconditional 46-table B09 SHARE prefix and READ COMMITTED protocol. Rechecks run after affected-grant waits, decision/event FK waits, deferred constraints, and before commit. Only the exact newly inserted REJECT is excluded from its own final rejection fence.
- Reads and completed replay remain one REPEATABLE READ, READ ONLY snapshot with plain nested reads. Historical seal verification ignores navigation and current write admission; current diagnostics remain separate. READY grants retain `usable=false` / `APPROVAL_GATE_FAILED` while the B14 consumer is unavailable.
- `0061_b14r_ready_approval` follows `0060_b14a_publication_entry`. It adds only `b14r_saved_decision` and `b14r_approval_gate` and replaces `pr216_gate` and `pr216_complete`. It preserves all prior migrations, schema objects, grant/receipt guards, hash versions and other purposes. Downgrade restores full predecessor definitions and refuses READY history with P17F1.
- No publication transition, grant consumption, receipt, preparation, consent, package, external effect, adapter, endpoint, dependency, branch, commit or push is added.

## Existing equivalents used

- Guide names `get_approval_request`, `get_approval_decision`, `get_approval_grant` correspond to the branch's existing `get_request`, `get_decision`, `get_grant`; their DTOs and boundary remain unchanged.
- Existing `_prepare_basis` and `_prepare_gate` are shared manuscript helpers with purpose-specific dispatch. READY uses `_readiness_readback` / `_readiness_target`, PREPARE retains its existing verifier and stage.
- Existing `prepare_submission_other_basis` supplies the comprehensive non-manuscript/review child exclusion for READY saved verification. This reuses its plain relational query, not PREPARE policy.
- Existing `PublicationService._entry_readback`, `entry_events`, and `entry_event` supply the B14a historical verifier and plain reads; no new repository read method is needed.
- B16 is absent on this branch. Both ApprovalService writers therefore retain the pre-B16 B09 prefix specified by §12.2. Consumption remains SERIALIZABLE under B13.

## Verification environment and commands

PostgreSQL probe observed **PostgreSQL 18.6 (Homebrew), aarch64-apple-darwin27.0.0**. Integration fixtures use disposable databases and ordinary SQL roles; successful setup uses real freeze, entry, review and B11 Decision commands. No acceptance fixture forces a publication stage or manufactures a grant.

Every command below uses `UV_CACHE_DIR=/private/tmp/b14r-uv-cache`. Pytest additionally uses `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1`. The inherited selectors were:

```sh
DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase_lane19
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres
```

The owner's loop owns the whole-suite run; no whole-suite pytest command was executed here. Final runs below supersede development runs. The broad regression selection is partitioned into four independent disposable-database processes.

| Exact command after the environment prefix above | Observed result |
| --- | --- |
| `uv run --no-sync ruff check .` | All checks passed; exit 0. |
| `uv run --no-sync ruff format --check .` | 653 files already formatted; exit 0. |
| `uv run --no-sync pyright` | 0 errors, 0 warnings, 0 informations; exit 0. |
| `uv run --no-sync alembic heads` | `0061_b14r_ready_approval (head)`; exit 0. |
| `uv run --no-sync pytest tests/unit tests/architecture tests/test_architecture.py --tb=short > /private/tmp/b14r-final-unit.log 2>&1` | 5,254 passed, 42 warnings in 99.81s; exit 0. |
| `uv run --no-sync pytest tests/unit/phase2/test_b14r_ready_approval_contract.py tests/integration/phase2/test_b14r_*.py tests/architecture/test_b14r_ready_approval_boundaries.py --tb=short > /private/tmp/b14r-verified-focused.log 2>&1` | 181 passed, 433 warnings in 259.64s; exit 0. This invocation collected before the additional validity-race case below was added. |
| `uv run --no-sync pytest tests/integration/phase2/test_b14r_ready_approval_races.py -k committed_validity --tb=short > /private/tmp/b14r-validity-race.log 2>&1` | 1 passed, 41 deselected, 4 warnings in 5.39s; exit 0. |

The full focused invocation collected 181 cases. Two additional edge cases were then added: the validity race above, and unsupported READY successor links with an existing rejection fence. The admission rerun below includes the latter case. All 183 B14r cases have executed successfully across these focused commands. The validity case observed an actual impact-assessment writer blocking approval's first inventory lock, then committed invalidity and proved zero partial approval history.

| Additional exact command after the same environment prefix | Observed result |
| --- | --- |
| `uv run --no-sync pytest tests/integration/phase2/test_b14r_ready_approval.py tests/integration/phase2/test_b12_prepare_approval.py --tb=short > /private/tmp/b14r-final-admission.log 2>&1` | 38 passed, 150 warnings in 96.03s. Verifies final READY successor error precedence and preserves PREPARE admission. |
| `uv run --no-sync pytest tests/integration/phase2/test_b04_*.py tests/integration/phase2/test_b05_*.py tests/integration/phase2/test_b08_*.py --tb=short > /private/tmp/b14r-regression-sources.log 2>&1` | 253 passed, 1 skipped, 836 warnings in 585.27s. |
| `uv run --no-sync pytest tests/integration/phase2/test_b09_*.py tests/integration/phase2/test_b11_*.py tests/integration/phase2/test_b12_*.py --tb=short > /private/tmp/b14r-regression-approval.log 2>&1` | 176 passed, 664 warnings in 265.12s. |
| `uv run --no-sync pytest tests/integration/phase2/test_b13_*.py tests/integration/phase2/test_b14a_*.py --tb=short > /private/tmp/b14r-regression-lifecycle.log 2>&1` | 191 passed, 615 warnings in 301.64s. |
| `uv run --no-sync pytest tests/integration/phase2/test_approval.py tests/integration/phase2/test_pr2_15_*.py --tb=short > /private/tmp/b14r-regression-basic.log 2>&1` | 123 passed, 380 warnings in 207.21s. |
| `git diff --check` | Exit 0; no whitespace errors. |

Affected PostgreSQL regressions total **743 passed, 1 skipped**. The existing skip is `test_superseded_manuscript_review`: B04 creates only DRAFT/FROZEN; SUPERSEDED history awaits its later contract. No skipped case is reported as passing.

Successful stdout/stderr logs are retained in [b14r-ready-approval-evidence](b14r-ready-approval-evidence/). Preliminary interrupted runs and development failures are superseded by the successful commands above; no result from an interrupted run is counted as a pass.

## Review

Read-only investigators reviewed authoritative contracts, source/diff and migration definitions. Their two application findings (new-write seal error mapping and complete saved-basis exclusions) were corrected. Final application and SQL reviews reported no remaining concrete P0/P1 implementation defect. Expanded tests cover post-FK/deferred authorization and expiry, immutable history, exact catalog roundtrip, normal-role final graphs, rejection ordering, empty-Issue/upstream phantoms, finite scope, retries and uncertain-commit replay.
