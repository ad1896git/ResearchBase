# B12 implementation evidence — director ruling applied

Date: 2026-10-17. Scope: the authorized B12 first slice and director's §12.2
remediation. This record supersedes the interrupted attempt's pending-ruling
status; the director explicitly resolved its inventory question.

## Changes and ruling

- PREPARE_SUBMISSION Approval writers use full inventory B, exactly the existing
  B09 inventory. Both request and decision paths call `lock_snapshot()` first;
  the separate narrow inventory, adapter method, port method and unused migration
  inventory were removed. No predecessor migration was modified.
- Existing installed `b09_preheld()` already requires B. It remains unchanged;
  focused SQL tests accept B and reject a missing review/Issue table with P16G1.
- Removed the purpose-routing read UoW from `ApprovalService._execute` entirely.
  Every purpose uses the same B inventory, so routing no longer needs a separate
  read transaction. Existing replay keeps its lock-free snapshot protocol.
- §12.2, glossary, command tables and test requirements now record B and the
  director ruling. No narrower N remains an approved B12 protocol.
- Retained the original upstream zero-Issue Claim review/normal-role Issue race
  as a regression, with both commit orders and observed PostgreSQL relation waits.
  Approval-first excludes the Issue insert throughout the protected gate;
  Issue-first makes the later gate wait and observe the committed blocker.
  No READY state, trigger bypass or successful approval is fabricated.
- Deleted `docs/phase2/B12-review-complete.patch`; the working-tree diff is the
  review artifact.

The retained first-slice implementation adds PREPARE Decision DTOs, canonical
hash reconstruction, read/replay/write paths, exact B09 preparation basis gates,
and forward migration 0058. It adds no table, column, lifecycle effect, consent,
package freeze or submission operation. Frozen predecessor function preservation
and downgrade restoration remain covered by the catalog roundtrip test.

## Dependency and evidence boundary

Publication READY remains a separate lifecycle dependency. The accepted current
Publication paths allow DRAFTING only; B12 preserves that denial. Positive PREPARE
creation/replay, actual preparation grants and populated PREPARE downgrade cannot
be established through an accepted READY transition in this slice. Focused checks
verify conservative admission, locking, hashes, unchanged predecessor behavior
and migration integrity; they do not claim the deferred lifecycle or full Phase 2
acceptance.

The prior run's predicate-lock exhaustion was an environment limit. The director
reports that the pipeline's sharded full suite passed. No whole-suite run or server
configuration change was made in this remediation; the loop owns the next full
sharded check. No commit, push or branch was created.

## Verification in this remediation

Every uv command below uses `UV_CACHE_DIR=/tmp/researchbase-b12-uv-cache` and the
repository's installed `.venv`, without syncing dependencies. PostgreSQL tests use
PostgreSQL **18.6 (Homebrew)** and disposable databases, with no SQLite replacement.

| Exact command (prepend the environment assignment above to uv commands) | Observed result |
| --- | --- |
| `uv run --no-sync ruff check .` | All checks passed. |
| `uv run --no-sync ruff format --check .` | 618 files already formatted. |
| `uv run --no-sync pyright` | 0 errors, 0 warnings, 0 informations. |
| `git diff --check` | Exit 0; no output. |
| `uv run --no-sync pytest tests/unit tests/architecture` | 4,952 passed, 42 warnings in 61.52s. |
| `uv run --no-sync pytest tests/integration/phase2/test_b12_prepare_races.py` | 13 passed, 39 warnings in 8.63s. |

Focused PostgreSQL commands and completed results:

```sh
UV_CACHE_DIR=/tmp/researchbase-b12-uv-cache uv run --no-sync pytest tests/integration/phase2/test_b12_* tests/integration/phase2/test_b09_* tests/integration/phase2/test_b11_* tests/integration/phase2/test_approval.py tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_15_decision_schema.py
```

Observed result: **285 passed, 997 warnings in 243.46s (0:04:03)**.
This includes the 13 B12 race cases already reported separately; counts overlap.


```sh
UV_CACHE_DIR=/tmp/researchbase-b12-uv-cache uv run --no-sync pytest tests/integration/phase2/test_b04_* tests/integration/phase2/test_b05_* tests/integration/phase2/test_b07_* tests/integration/phase2/test_b08_* tests/integration/phase2/test_b10_*
```

Observed result: **435 passed, 1 skipped, 1,388 warnings in 558.01s (0:09:18)**.
The pre-existing skip is `test_superseded_manuscript_review`: B04 creates only
DRAFT/FROZEN; exact SUPERSEDED history awaits the later supersession contract.


```sh
UV_CACHE_DIR=/tmp/researchbase-b12-uv-cache uv run --no-sync pytest tests/integration/phase2/test_pr2_17_authorship_schema.py tests/integration/phase2/test_pr2_03_literature_search_plan_migration.py tests/integration/phase2/test_revision_action.py tests/integration/phase2/test_batch_c_migration.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_xid_wraparound_guards.py tests/test_architecture.py
```

Observed result: **161 passed, 310 warnings in 88.59s (0:01:28)**.

Final diff checks: `git diff --check` exited 0 without output;
`git diff HEAD --name-only -- migrations` lists only
`migrations/versions/0058_b12_prepare_submission.py`;
`test ! -e docs/phase2/B12-review-complete.patch` exited 0.

The §12.2 inventory mismatch and upstream exclusion findings are resolved by
using the established full B protocol and retaining the stronger installed SQL
guard. All checks started in this remediation finished; no failures were observed.
The one documented predecessor skip remains a skip. The separate READY lifecycle
and whole-suite acceptance boundaries stated above remain in force.
