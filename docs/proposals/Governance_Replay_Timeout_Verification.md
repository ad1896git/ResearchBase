# Governance failed-wait receipt recovery verification

Date: 2026-10-21. Baseline: `f0bff71`. Fix: uncommitted worktree, per the
instruction not to commit, push or create branches. No global gate claim.

## Behavior and scope

The four requested writers consume the internal `55P03` receipt-recovery marker
only after the failed UoW has rolled back. Each makes one entitled exact-key
read-only lookup, verifies historical closure, actor and material, and either
returns the saved receipt, rejects changed material/entitlement, or returns a
sanitized timeout. The generic Decision error code remains compatible for other
writers. Existing serialization/deadlock retries, lock order, schema and runtime
dependencies are unchanged. Legacy correspondence has no non-key payload; its
material is the exact action/review pair. Changing that pair is a new key, not
changed material at the same key.

## Original-code regression evidence

The original `decision.py`, `revision_action.py` and `persistence/uow.py` were
loaded from `git show HEAD:<path>` in a temporary source copy. Module origin was
verified as `/tmp/rb-governance-original/researchbase/application/decision.py`.
The repository implementation was not reverted to obtain this evidence.

```sh
PYTHONPATH=/tmp/rb-governance-original UV_CACHE_DIR=/tmp/rb-uv-cache uv run pytest tests/integration/phase2/test_governance_failed_wait_recovery.py
```

Observed: **19 failed**, 57 warnings, 117.43s. Every test passed the real
PostgreSQL advisory-wait witness and driver `55P03` barrier, then failed because
the original implementation returned `INVALID_STATE_TRANSITION` instead of
recovering the receipt or checking changed material/current entitlement. Rolled
back and still-uncommitted winners also produced the original error rather than
the scoped sanitized concurrent-modification timeout. This is the original-code
failure evidence for all four named tests, not an assumed failure.

[Per-case original failure summary](evidence/governance-replay-timeout-original.txt).

## Fixed-code verification

All commands used the existing PostgreSQL test environment. Database fixtures
create disposable real PostgreSQL databases; no SQLite, skips or xfails were
introduced. The whole test suite was not run.

| Exact command | Observed result |
| --- | --- |
| `UV_CACHE_DIR=/tmp/rb-uv-cache uv run ruff check .` | All checks passed |
| `UV_CACHE_DIR=/tmp/rb-uv-cache uv run ruff format --check .` | 802 files already formatted |
| `UV_CACHE_DIR=/tmp/rb-uv-cache uv run pyright` | 0 errors, 0 warnings, 0 informations |
| `UV_CACHE_DIR=/tmp/rb-uv-cache uv run pytest tests/unit tests/architecture` | 6376 passed, 54 warnings, 96.50s |
| `UV_CACHE_DIR=/tmp/rb-uv-cache uv run pytest tests/integration/phase2/test_governance_failed_wait_recovery.py` | 19 passed, 57 warnings, 118.99s |
| `UV_CACHE_DIR=/tmp/rb-uv-cache uv run pytest tests/integration/phase2/test_governance_failed_wait_recovery.py -k readiness` | 5 passed, 14 deselected, 15 warnings, 30.74s |
| `UV_CACHE_DIR=/tmp/rb-uv-cache uv run pytest tests/unit/phase2/test_pr2_15_uow_errors.py tests/unit/phase2/test_b11_readiness_contract.py tests/unit/phase2/test_b11_readiness_hash_vectors.py tests/architecture/test_b11_readiness_boundaries.py` | 115 passed, 0.10s |
| `UV_CACHE_DIR=/tmp/rb-uv-cache uv run pytest tests/integration/phase2/test_pr2_15_*.py tests/integration/phase2/test_revision_action.py tests/integration/phase2/test_b06_*.py tests/integration/phase2/test_b07_*.py tests/integration/phase2/test_b08_*.py tests/integration/phase2/test_b11_*.py tests/integration/phase2/test_b12_*.py tests/integration/phase2/test_b23_*.py` | Initial run: 621 passed, 1 previous-contract assertion failed, 1737 warnings, 956.26s; corrected file rerun: 41 passed (below) |
| `UV_CACHE_DIR=/tmp/rb-uv-cache uv run pytest tests/integration/phase2/test_b11_readiness_races.py` | 41 passed, 125 warnings, 40.55s |
| `git diff --check` | Passed |

The 19 regression cases comprise five each for revision Decision, readiness
Decision and RevisionAction, and four for legacy correspondence. They cover
committed replay, changed payload where representable, revoked current
credentials, winner rollback and a winner still holding its lock. Each requires
exactly one read-only recovery transaction and forbids lock/mutation SQL.
Still-uncommitted-winner cases finish before releasing the winner; no mutation
retry or eventual-commit polling is permitted.

Readiness returns fresh `evaluated_at` validity information. Its assertions
check timestamp ordering/timezone plus equality of every other receipt field.
The additional readiness run verified reuse of its existing collision reader
with explicit absent-receipt handling. The 115-test run verified the final
normalizer metadata contract and readiness return-type refinement.

Intermediate verification found a unit assertion requiring absent timeout
metadata (updated to require the exact scoped marker), three new test failures
from comparing readiness evaluation timestamps as immutable fields (now checked
explicitly as above), and a Pyright optional-return inference error (resolved by
requiring a non-null receipt on the existing PK-collision path). These were
corrected before the passing results above. No existing assertion was loosened.

The owning run exposed the existing
`test_only_sqlstate_retry_and_three_fresh_uows[55P03-1]` expectation of
`INVALID_STATE_TRANSITION`. Its one-mutation-attempt assertion remains unchanged;
it now expects the authorized scoped timeout code and additionally requires
exactly one separate read-only recovery session for `55P03`, zero recovery reads
for the other driver codes, and sanitized public details. The full readiness
race file then passed all 41 tests. This is a contract assertion update with
additional checks, not a relaxation of retry limits.

The completed owning run's only failure was the previous-contract readiness
assertion identified above. Its full owning file passed after the assertion was
updated and strengthened. No failure remains unresolved; the 622-case owning
run was not repeated wholesale after this test-only correction. Pyright and both
Ruff checks were rerun after the final test edit and passed. The collect-only
command used to identify the failing node reported 622 tests; it was not counted
as a passing test run.
