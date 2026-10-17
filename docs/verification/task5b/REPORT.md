# Task 5b — evidence and architecture exception cleanup

Changes are implemented. Verification is **partially blocked by the execution
sandbox**; no all-green or PostgreSQL acceptance claim is made.

## Changes

- Every migration exception in `tests/test_architecture.py` now names its
  authorizing PR and matches an exact repository-relative file path and table.
  Basename reuse in another directory receives no exemption. The global
  `run_versions` prohibition remains intact.
- [Task 5 report](../task5/REPORT.md) retains the final full run only:
  **4938 passed, 9 failed, 1 skipped**. It states that no pristine pre-task baseline
  exists and records the director's acceptance of the nine known schema failures
  pending the owner's forward-migration decision in
  [SCHEMA-BLOCKERS.md](../task5/SCHEMA-BLOCKERS.md). Historical failures remain FAIL.
- Normalized 81 whitespace-only context lines in
  [Task 5 diff evidence](../task5/final.diff). This fixes the pinned-baseline
  whitespace gate. `git apply --numstat -` produces identical output before and
  after normalization; no recorded additions/deletions changed.
- All 16 report links resolve. Repository search found no old evidence-path
  references. No `src/` or `migrations/` files changed. HEAD remains
  `eb86f6d20444b82ed9dd5f5d61ac4d62e8bd1713`; no commit, push or branch was created.

## Verification

Run from the repository root with:

```sh
export UV_CACHE_DIR="$PWD/.uv-cache"
export DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase
export RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres
```

| Exact command | Result |
|---|---|
| `uv run ruff check .` | PASS; all checks passed; exit 0 |
| `uv run ruff format --check .` | PASS; 438 files formatted; exit 0 |
| `uv run pyright` | PASS; 0 errors, 0 warnings; exit 0 |
| `uv run pytest tests/architecture tests/test_architecture.py -o addopts='' -q -rfE -p no:cacheprovider` | 69 passed, 0 failed, 0 errors; exit 0; [output](architecture-final.log) |
| `uv run pytest tests/unit tests/architecture tests/test_architecture.py -o addopts='' -q -rfE -p no:cacheprovider` | 1817 passed, 4 failed, 0 errors; exit 1; [output](unit-architecture-final.log) |
| `uv run pytest tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_pr2_10*.py tests/integration/phase2/test_pr2_11*.py tests/integration/phase2/test_pr2_13*.py tests/integration/phase2/test_pr2_14*.py tests/integration/phase2/test_pr2_15*.py tests/integration/test_pr11r2_migration.py -o addopts='' -q -rfE -p no:cacheprovider` | 0 passed, 0 failed, 133 setup errors; exit 1; [output](postgresql-references.log) |
| `git diff --check` | PASS; exit 0 |
| `git diff --check b8179f17720ca47c3b25ad9d36f6a8e8d4aa79ff` | PASS after evidence normalization; exit 0 |
| `git diff --exit-code -- src migrations` | PASS; empty diff; exit 0 |

An in-memory probe of the actual architecture test passed all **45 cases**:
nine authorized file/table pairs accepted; 36 wrong-path, wrong-table, future-file
and `run_versions` cases rejected. No migration files were created for these probes.

The first combined unit/architecture run had 1816 passes and five failures. One
was the evidence whitespace defect fixed above; the final run passes that static
gate. The remaining four failures are in `tests/unit/test_hg1_runner.py`:
`test_v2_denial_keeps_versioned_fail_closed_response`,
`test_socket_lifecycle_one_request_and_cleanup`,
`test_foreign_peer_policy_denies_before_frame_without_using_request_slot`, and
`test_incomplete_owner_frame_cannot_extend_runner_past_deadline`. Each fails at
Unix socket binding with `PermissionError: [Errno 1] Operation not permitted`.

All 133 integration cases fail during setup because PostgreSQL connections to
localhost:5432 are denied with `Operation not permitted`. The sandbox disallows
permission escalation. No tests were weakened, skipped or replaced to conceal
these restrictions. A full suite was not rerun: it would encounter the same
socket restrictions. Task 5's recorded full-run result is historical evidence,
not a fresh Task 5b run.
