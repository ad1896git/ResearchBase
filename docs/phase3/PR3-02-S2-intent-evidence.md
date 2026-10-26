# PR3-02-S2 intent review B4 fix4 evidence — lane352

Review: `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/reviews/s2_intent_review_B4_fix3.md`, read in full. Date: 2026-10-26.
Branch: `s2-intent-fix4`. HEAD: `dff29d3792c96c183a3ffbb5569ed72ac41c179c` (the supplied fix3 base).

`GIT-HEAD` and `GIT-STATUS-CLEAN` below were recorded **before editing**, with empty status. No new commit is authorized or created, so there is no new fix4 commit and the final worktree is intentionally dirty. Current test evidence belongs to this HEAD **plus the two uncommitted test changes**, not to a fictitious clean committed fix4 tree. `TREE-BEFORE`/`TREE-AFTER` pin every tracked file except this evidence document and require identical SHA-256 manifests before/after the runs. Final tested-tree digest: `a8af916a2f0563a22a56d1c7927a97642eb97ec34cbaca19add34f33926d7811`. The evidence file is assembled after the runs and `git diff --check HEAD` is repeated afterward.

Only `test_pr3_02_s2_intent_guards.py`, `test_pr3_02_s2_intent_migration.py` and this evidence document change. Frozen packs, every migration (including 0081), runtime source, `pyproject.toml` and `uv.lock` remain unchanged. The mutation harness edits only disposable repository copies under this repository's ignored `tmp/`; original files are checked unchanged and copies restored/removed.

## Historical runs — PREDATE FIX4, no current coverage credit

The prior lane351/B3 evidence at `dff29d3792c96c183a3ffbb5569ed72ac41c179c:docs/phase3/PR3-02-S2-intent-evidence.md` describes `33e2a65` plus a then-uncommitted diff. **Every run in that historical version predates this fix**. Its INTENT, S7, mutation, H-U, PG-R, PG-N and audit outputs are not carried forward as current results. This file replaces that narrative with lane352 reruns; the historical version remains inspectable in Git.

Initial lane352 development probes (S1-OWNER, M1, lint/format, UNIT-ARCH, INTENT and the first two mutation pairs) also **predate the final fix4 type annotation/fingerprint** and receive no current coverage credit. Initial Pyright failed with six type-inference errors in the new receipt dictionary; the explicit `dict[str, object]` annotation fixed them. The failed raw result is retained below as `PRE-ANNOTATION-TYPE`, not PASS. Final-source checks and all twelve mutation pairs are rerun below. Counts overlap between runs and must not be summed as distinct tests.

## B4 findings and actual evidence

- **P1 / G2:** six real PostgreSQL cases at explicit head 0081, using `SqlAlchemyAgentRepository.lock_write`/`insert` through the table-owning database role. Each S1 operation is tested with an Application-provisioned HUMAN RESEARCHER, expecting `23514` / `pr302_scope` / `effective HUMAN OWNER required` from `pr302_receipt_guard`. Each also inserts as HUMAN OWNER, closes its OWNER role interval after insertion in the same transaction, and forces only `pr302_receipt_complete_commit`, expecting `23514` / `pr302_scope` / `OWNER unavailable` from `pr302_receipt_complete`. The exact PL/pgSQL raising-function context is asserted. Receipts are valid in shape but intentionally incomplete; forcing this one root isolates its OWNER predicate from deferred result FKs and the role's CLOSED-event requirement. Every case rolls back, verifies no receipt persisted, and final-check cases verify OWNER restoration by rollback. These are receipt-guard probes, not claims that incomplete S1 writes can commit; the existing populated-upgrade test separately executes all three valid S1 operations at head.
- **P1 mutation:** `M-S1-INSERT` removes only migration 0081's S1 insertion OWNER block. All three researcher nodes must fail with DID NOT RAISE; restored controls pass. `M-S1-FINAL` removes only its S1 final OWNER block. All three nodes must fail on `pr302_provenance` versus expected `pr302_scope`; restored controls pass. Both exact removed blocks, commands, raw output, copied cwd and exit codes are below. Other surviving guards cannot receive credit for the removed OWNER predicate.
- **P2 revision attribution:** the clean starting HEAD/status, final-source fingerprints, rerun INTENT/S7 and all prior ten mutations plus the two new mutations appear below. Final dirty status is reported honestly because committing is prohibited.
- **P2 database identity:** `PG-IDENTITY` executes literal `SELECT version(), current_user` using the requested lane database. Raw server output and exit code are below. Test fixtures create/drop fresh random disposable databases on this same explicitly selected cluster; identity/Agent verifier adapters remain test-only.
- **P3 / M1:** `test_empty_upgrade_and_single_head` now compares the exact `(table, name)` additions/removals for the complete constraint/index catalog, using independent frozen-name lists: 28 explicitly named constraints plus 22 PostgreSQL 18 named NOT NULL constraints added, exactly two old receipt CHECKs removed, and exactly 12 indexes added with none removed. Definitions for all retained constraints/indexes must also be unchanged. It no longer accepts a merely larger constraint count.

New parameterized node IDs, executed by INTENT and S7-SCHEMA (exit codes in the ledger below):

- `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[insertion_researcher-provision_project_agent]`
- `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[insertion_researcher-register_agent_version]`
- `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[insertion_researcher-change_agent_availability]`
- `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[final_owner_removed-provision_project_agent]`
- `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[final_owner_removed-register_agent_version]`
- `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[final_owner_removed-change_agent_availability]`

M1 node: `tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_empty_upgrade_and_single_head` (INTENT / S7-SCHEMA).

## Frozen-ID to actual-node mapping

The frozen `test_pr3_02_s2_schema.py` nodes live in `test_pr3_02_s2_intent_guards.py`; all other S2 integration filenames retain their existing `_intent_` infix. No aliases, duplicate tests or frozen-pack edits were added. Schema/guards/migration therefore run as two actual files in S7-SCHEMA; execution and races/replay use the corresponding actual filenames. All three existing regression commands retain the exact frozen glob/file lists.

| Frozen ID | Actual nodes (integration/repository parameters in COLLECT-NODES) | Run (exit 0) |
| --- | --- | --- |
| U1 | `tests/unit/phase3/test_agent_execution_contracts.py::test_closed_intent_command_and_literal_vectors`; `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_python_postgresql_intent_material_parity` | UNIT-ARCH / INTENT |
| U2 | `tests/unit/phase3/test_agent_execution_contracts.py::test_intent_binding_and_harness_pins` | UNIT-ARCH |
| U3 | `tests/unit/phase3/test_agent_execution_contracts.py::test_intent_query_and_receipt_shapes` | UNIT-ARCH |
| L1 | `tests/unit/phase3/test_agent_execution_repository.py::test_ordered_intent_prefix_and_keys` | UNIT-ARCH |
| L2 | `tests/unit/phase3/test_agent_execution_repository.py::test_fresh_checks_after_each_wait` | UNIT-ARCH |
| L3 | `tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot` | UNIT-ARCH |
| M1 | `tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_empty_upgrade_and_single_head`; `tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift` | INTENT |
| M2 | `tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_populated_upgrade_preserves_history` | INTENT |
| M3 | `tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_downgrade_refuses_before_change` | INTENT |
| G1 | `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_exact_intent_schema_and_scoped_foreign_keys`; `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_literal_checks_indexes_and_receipt_deferral` | INTENT |
| G2 | `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables`; `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards`; `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_owning_role_immutable_including_noop`; `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_historical_receipt_cannot_attach_new_history`; `tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_researcher_and_exact_agent_use_common_boundary`; `tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_populated_upgrade_preserves_history`; `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head` | INTENT / S7-REG3 |
| G3 | `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_python_postgresql_intent_material_parity` | INTENT |
| E1 | `tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_created_intent_through_common_application_boundary` | INTENT |
| E2 | `tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_denials_preserve_closed_execution_gate` | INTENT |
| E3 | `tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_failure_rolls_back_all_three_effects` | INTENT |
| R1 | `tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_observed_wait_rechecks_intent_authority`; `tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_membership_revocation_during_first_share_wait`; `tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_availability_change_at_existing_s1_writer_wait` | INTENT |
| R2 | `tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_same_command_revision_and_existing_writer_races`; `tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_unchanged_task_writer_coexistence`; `tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_unchanged_gateway_writer_coexistence`; `tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_unchanged_phase2_writer_coexistence` | INTENT |
| R3 | `tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_intent_after_loss_and_uncertain_commit`; `tests/unit/phase3/test_agent_execution_repository.py::test_bounded_whole_transaction_retry_and_no_timeout_retry`; `tests/integration/phase3/test_pr3_02_s2_intent_database_errors.py::test_real_postgresql_failure_normalizes_intent_retryability` | UNIT-ARCH / INTENT |
| R4 | `tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_current_entitlement_precedes_intent_disclosure`; `tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_other_caller_cannot_replay_receipt` | INTENT |
| R5 | `tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_queries_are_coherent_bounded_snapshots`; `tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot` | UNIT-ARCH / INTENT |
| A1 | `tests/architecture/test_pr3_02_s2_boundaries.py::test_intent_only_application_boundary` | UNIT-ARCH |

This mapping identifies test allocation, not a claim that every theoretical branch is reachable. Under the option-A numeric refreeze, SQL numeric rejection is not required. The SQL NULL 22023 diagnostic is exercised by G3; the serializer's unsupported-type ELSE is unreachable for valid PostgreSQL jsonb, whose possible types are all handled. That branch is not credited as tested. Source-link revocation and all running/promotion/provider work remain deferred by the frozen pack. The existing PR3-05 preview denial is covered by S7-PREVIEW, not promoted to producer verification.

L2/L3 execute the real service/UoW/repository with deterministic SQL/port doubles; their observations prove call ordering and forbidden I/O/session operations, not PostgreSQL isolation by themselves. INTENT and S7-RACES supply the real PG18.6 wait/snapshot observations. The `-s` output includes all four wait sites (first_share, second_key, task_row, version_row), expiry/acquisition/authorization times and persisted counts. No deadlock-freedom claim is made.

## Environment

Every recorded command/subprocess inherited these exact exports. Mutation copies use the lane interpreter and an explicit PYTHONPATH pointing only to copied source/tests; the UV cache stays in lane352.

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
export DATABASE_URL="postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase_lane352"
export RB_TEST_ADMIN_URL="postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres"
export PGOPTIONS="-c jit=off"
```

Default cwd: `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352`. Mutation cwd and PYTHONPATH overrides are recorded per pair. No whole-suite run is made. Raw stdout/stderr is merged at capture and otherwise reproduced without editing. For mutation runs, pytest's `--show-capture=no` suppresses captured setup logs at emission; this is not postprocessing. Collection establishes node existence only; passing executions supply coverage.

## Current run ledger

| Run | Observed output/result | Exit code |
| --- | --- | --- |
| GIT-HEAD | dff29d3792c96c183a3ffbb5569ed72ac41c179c | 0 |
| GIT-STATUS-CLEAN | (no stdout/stderr) | 0 |
| TREE-BEFORE | HEAD dff29d3792c96c183a3ffbb5569ed72ac41c179c | 0 |
| PG-IDENTITY | version  /  current_user | 0 |
| DIFF | (no stdout/stderr) | 0 |
| LINT | All checks passed! | 0 |
| FORMAT | 948 files already formatted | 0 |
| TYPE | 0 errors, 0 warnings, 0 informations | 0 |
| HEAD | 0081_agent_execution_intents (head) | 0 |
| UNIT-ARCH | 1423 passed, 50 warnings in 26.43s | 0 |
| INTENT | 97 passed, 163 warnings in 86.45s (0:01:26) | 0 |
| S7-U | 1050 passed in 7.27s | 0 |
| S7-A | 373 passed, 50 warnings in 20.95s | 0 |
| S7-SCHEMA | 51 passed, 78 warnings in 37.89s | 0 |
| S7-EXEC | 19 passed, 38 warnings in 20.09s | 0 |
| S7-RACES | 23 passed, 47 warnings in 27.88s | 0 |
| S7-REG3 | 561 passed, 548 warnings in 483.09s (0:08:03) | 0 |
| S7-REG2 | 155 passed, 360 warnings in 157.97s (0:02:37) | 0 |
| S7-PREVIEW | 2 passed, 2 warnings in 1.25s | 0 |
| COLLECT-NODES | 107 tests collected in 0.04s | 0 |
| TREE-AFTER | HEAD dff29d3792c96c183a3ffbb5569ed72ac41c179c | 0 |

## Mutation ledger

| Removed block | Removed result | Exit | Restored result | Exit |
| --- | --- | --- | --- | --- |
| M-L2 | 1 failed in 0.60s | 1 | 1 passed in 0.60s | 0 |
| M-L3 | 3 failed in 0.71s | 1 | 3 passed in 0.65s | 0 |
| M-DRIFT | 2 failed, 4 warnings in 1.61s | 1 | 2 passed, 4 warnings in 1.77s | 0 |
| M-REVOKE-PUBLIC | 8 failed, 8 deselected, 2 warnings in 1.01s | 1 | 8 passed, 8 deselected, 2 warnings in 0.95s | 0 |
| M-REVOKE-ROLE | 8 failed, 8 deselected, 2 warnings in 0.97s | 1 | 8 passed, 8 deselected, 2 warnings in 0.99s | 0 |
| M-SHARE | 1 failed, 2 warnings in 0.98s | 1 | 1 passed, 2 warnings in 1.06s | 0 |
| M-CAS | 1 failed, 2 warnings in 0.99s | 1 | 1 passed, 2 warnings in 1.04s | 0 |
| M-ISOLATION | 1 failed, 2 warnings in 1.09s | 1 | 1 passed, 2 warnings in 1.08s | 0 |
| M-REPLAY-PREFLIGHT | 2 failed, 4 warnings in 1.94s | 1 | 2 passed, 4 warnings in 2.17s | 0 |
| M-REPLAY-WRITE | 1 failed, 2 warnings in 1.06s | 1 | 1 passed, 2 warnings in 1.03s | 0 |
| M-S1-INSERT | 3 failed, 3 deselected, 6 warnings in 2.55s | 1 | 3 passed, 3 deselected, 6 warnings in 2.55s | 0 |
| M-S1-FINAL | 3 failed, 3 deselected, 6 warnings in 2.65s | 1 | 3 passed, 3 deselected, 6 warnings in 2.62s | 0 |

## Raw command output

### GIT-HEAD

```sh
git rev-parse HEAD
```

```text
dff29d3792c96c183a3ffbb5569ed72ac41c179c
```

Exit code: **0**.

### GIT-STATUS-CLEAN

```sh
git status --short
```

```text
```

Exit code: **0**.

### TREE-BEFORE

```sh
python3 tmp/b4_fingerprint.py
```

```text
HEAD dff29d3792c96c183a3ffbb5569ed72ac41c179c
tracked tree SHA-256 (excluding evidence): a8af916a2f0563a22a56d1c7927a97642eb97ec34cbaca19add34f33926d7811
905c4726fe48c2ba9cf17f4fdcb65c07044a59793d7f7dc2f9dc35cca22f6c3d tests/integration/phase3/test_pr3_02_s2_intent_guards.py
9b3103b6ba1fc32a4d8311dd6a2e556a7f41a12fdccf79113de23dc98a990c0c tests/integration/phase3/test_pr3_02_s2_intent_migration.py
142c7a9061785a971d7043667041cf5368be24e38069c59900640d13c2259e52 migrations/versions/0081_agent_execution_intents.py
ce8f06d923256872c6438e1f40308bb647d5c167e070eb875bd980a841692ca9 docs/phase3/PR3-02-S2-contract-freeze.md
9f08950b95fa7fefb3c233cccb97a56ba2baceb1c0bc8e1aea87d25726b235a0 pyproject.toml
e7155e4cbfe7f43157cba3f1c6fc0e7961f466d58810b09024f34487078b3ba6 uv.lock
Protected files unchanged from HEAD
git status --short:
 M tests/integration/phase3/test_pr3_02_s2_intent_guards.py
 M tests/integration/phase3/test_pr3_02_s2_intent_migration.py
```

Exit code: **0**.

### PG-IDENTITY

```sh
uv run python tmp/b4_identity.py
```

```text
version | current_user
PostgreSQL 18.6 (Homebrew) on aarch64-apple-darwin27.0.0, compiled by Apple clang version 21.0.0 (clang-2100.3.34.2), 64-bit | researchbase
```

Exit code: **0**.

### DIFF

```sh
git diff --check HEAD
```

```text
```

Exit code: **0**.

### LINT

```sh
uv run ruff check .
```

```text
All checks passed!
```

Exit code: **0**.

### FORMAT

```sh
uv run ruff format --check .
```

```text
948 files already formatted
```

Exit code: **0**.

### TYPE

```sh
uv run pyright
```

```text
0 errors, 0 warnings, 0 informations
WARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`

```

Exit code: **0**.

### HEAD

```sh
uv run alembic heads
```

```text
0081_agent_execution_intents (head)
```

Exit code: **0**.

### UNIT-ARCH

```sh
uv run pytest -o addopts='' -q -rfE tests/unit/phase3 tests/architecture tests/unit/architecture
```

```text
........................................................................ [  5%]
........................................................................ [ 10%]
........................................................................ [ 15%]
........................................................................ [ 20%]
........................................................................ [ 25%]
........................................................................ [ 30%]
........................................................................ [ 35%]
........................................................................ [ 40%]
........................................................................ [ 45%]
........................................................................ [ 50%]
........................................................................ [ 55%]
........................................................................ [ 60%]
........................................................................ [ 65%]
........................................................................ [ 70%]
........................................................................ [ 75%]
........................................................................ [ 80%]
........................................................................ [ 86%]
........................................................................ [ 91%]
........................................................................ [ 96%]
.......................................................                  [100%]
=============================== warnings summary ===============================
tests/architecture/test_b02_strategy_promotion_boundaries.py: 1 warning
tests/architecture/test_b04_boundaries.py: 1 warning
tests/architecture/test_b05_review_boundaries.py: 1 warning
tests/architecture/test_b15_package_boundaries.py: 1 warning
tests/architecture/test_b20_screening_boundaries.py: 1 warning
tests/architecture/test_basic_approval.py: 1 warning
tests/architecture/test_pr2_19_boundaries.py: 43 warnings
tests/architecture/test_pr3_02_s1_boundaries.py: 1 warning
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1423 passed, 50 warnings in 26.43s
```

Exit code: **0**.

### INTENT

```sh
uv run pytest -o addopts='' -q -rfE tests/integration/phase3/test_pr3_02_s2_intent_*.py
```

```text
........................................................................ [ 74%]
.........................                                                [100%]
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py: 23 warnings
tests/integration/phase3/test_pr3_02_s2_intent_execution.py: 38 warnings
tests/integration/phase3/test_pr3_02_s2_intent_guards.py: 62 warnings
tests/integration/phase3/test_pr3_02_s2_intent_migration.py: 16 warnings
tests/integration/phase3/test_pr3_02_s2_intent_replay.py: 24 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
97 passed, 163 warnings in 86.45s (0:01:26)
```

Exit code: **0**.

### S7-U

```sh
uv run pytest -o addopts='' -ra tests/unit/phase3
```

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 1050 items

tests/unit/phase3/test_agent_execution_contracts.py .............        [  1%]
tests/unit/phase3/test_agent_execution_repository.py ..........          [  2%]
tests/unit/phase3/test_agent_identity_contracts.py .                     [  2%]
tests/unit/phase3/test_agent_tool_policy.py ............................ [  4%]
........................................                                 [  8%]
tests/unit/phase3/test_agent_version_contracts.py ...................... [ 10%]
........................................................................ [ 17%]
....                                                                     [ 18%]
tests/unit/phase3/test_agent_version_transports.py ..................    [ 19%]
tests/unit/phase3/test_canonical_context.py .......................      [ 22%]
tests/unit/phase3/test_capability_gateway.py ........................... [ 24%]
........................................................................ [ 31%]
........................................................................ [ 38%]
...................................................................      [ 44%]
tests/unit/phase3/test_capability_gateway_contracts.py ................. [ 46%]
........................................................                 [ 51%]
tests/unit/phase3/test_capability_gateway_repository.py ................ [ 53%]
.................................................                        [ 57%]
tests/unit/phase3/test_capability_routing.py ........................... [ 60%]
........................................................                 [ 65%]
tests/unit/phase3/test_context_contracts.py ...............              [ 67%]
tests/unit/phase3/test_gateway_input_validation.py ..................... [ 69%]
.........                                                                [ 70%]
tests/unit/phase3/test_harness_manifest.py ...............               [ 71%]
tests/unit/phase3/test_promotion_context.py ..                           [ 71%]
tests/unit/phase3/test_research_task_contracts.py ...................... [ 73%]
....................................................                     [ 78%]
tests/unit/phase3/test_research_task_graph.py .......................... [ 81%]
........................................................................ [ 88%]
.                                                                        [ 88%]
tests/unit/phase3/test_research_task_transports.py ....................  [ 90%]
tests/unit/phase3/test_task_budget_accounting.py .............           [ 91%]
tests/unit/phase3/test_task_checkpoints.py ................              [ 92%]
tests/unit/phase3/test_task_memory.py ..                                 [ 92%]
tests/unit/phase3/test_task_safety_contracts.py ................         [ 94%]
tests/unit/phase3/test_task_safety_policies.py ......................... [ 96%]
.......................                                                  [ 99%]
tests/unit/phase3/test_task_safety_transports.py ..........              [100%]

============================= 1050 passed in 7.27s =============================
```

Exit code: **0**.

### S7-A

```sh
uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture
```

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 373 items

tests/architecture/test_b01_resolution_boundaries.py ...                 [  0%]
tests/architecture/test_b02_strategy_promotion_boundaries.py ....        [  1%]
tests/architecture/test_b03_discussion_hypothesis_boundaries.py ....     [  2%]
tests/architecture/test_b04_boundaries.py ....                           [  4%]
tests/architecture/test_b05_review_boundaries.py ....                    [  5%]
tests/architecture/test_b06_revision_action.py ...                       [  5%]
tests/architecture/test_b07_revision_decisions.py ...                    [  6%]
tests/architecture/test_b08_issue_disposition.py ...                     [  7%]
tests/architecture/test_b10_reconsideration.py ...                       [  8%]
tests/architecture/test_b11_readiness_boundaries.py ...                  [  9%]
tests/architecture/test_b12_prepare_boundaries.py ....                   [ 10%]
tests/architecture/test_b13_grant_boundaries.py ....                     [ 11%]
tests/architecture/test_b14_ready_boundaries.py .....                    [ 12%]
tests/architecture/test_b14a_entry_boundaries.py ..                      [ 13%]
tests/architecture/test_b14r_ready_approval_boundaries.py ...            [ 13%]
tests/architecture/test_b15_package_boundaries.py ....                   [ 15%]
tests/architecture/test_b16_boundaries.py ...                            [ 15%]
tests/architecture/test_b17_boundaries.py ...                            [ 16%]
tests/architecture/test_b19_close_prior_art_boundaries.py ..             [ 17%]
tests/architecture/test_b20_screening_boundaries.py ...                  [ 17%]
tests/architecture/test_b21_capture_boundaries.py ..                     [ 18%]
tests/architecture/test_b22_prior_art_boundaries.py ...                  [ 19%]
tests/architecture/test_b23_novelty_boundaries.py ...                    [ 20%]
tests/architecture/test_b25_boundaries.py ...                            [ 20%]
tests/architecture/test_b26_boundaries.py ...                            [ 21%]
tests/architecture/test_b27_defensive_closure_read.py ...                [ 22%]
tests/architecture/test_b32_boundaries.py ................               [ 26%]
tests/architecture/test_basic_approval.py ...                            [ 27%]
tests/architecture/test_import_boundaries.py .............               [ 31%]
tests/architecture/test_m1_boundaries.py ...                             [ 31%]
tests/architecture/test_no_masked_url_reconnect.py ................      [ 36%]
tests/architecture/test_pr02_boundaries.py ..........                    [ 38%]
tests/architecture/test_pr12_boundaries.py ....                          [ 39%]
tests/architecture/test_pr13_boundaries.py ..                            [ 40%]
tests/architecture/test_pr13r_batched_reads.py ...                       [ 41%]
tests/architecture/test_pr14_boundaries.py ..                            [ 41%]
tests/architecture/test_pr15_http_boundaries.py ...                      [ 42%]
tests/architecture/test_pr16_cli_boundaries.py ....                      [ 43%]
tests/architecture/test_pr17_agent_ready_architecture.py .......         [ 45%]
tests/architecture/test_pr18_boundaries.py .......                       [ 47%]
tests/architecture/test_pr2_00_boundaries.py ...                         [ 48%]
tests/architecture/test_pr2_17_boundaries.py ...                         [ 49%]
tests/architecture/test_pr2_18_boundaries.py .................           [ 53%]
tests/architecture/test_pr2_19_boundaries.py ....................        [ 58%]
tests/architecture/test_pr2_20_boundaries.py .....                       [ 60%]
tests/architecture/test_pr3_00_boundaries.py ........................... [ 67%]
................................                                         [ 76%]
tests/architecture/test_pr3_01_boundaries.py ....                        [ 77%]
tests/architecture/test_pr3_02_s1_boundaries.py ..                       [ 77%]
tests/architecture/test_pr3_02_s2_boundaries.py ..                       [ 78%]
tests/architecture/test_pr3_03_boundaries.py ..............              [ 82%]
tests/architecture/test_pr3_04_boundaries.py ..                          [ 82%]
tests/architecture/test_pr3_05_readonly_boundaries.py .....              [ 83%]
tests/unit/architecture/test_pr12_guard.py ..........................    [ 90%]
tests/unit/architecture/test_pr14_guard.py ............................. [ 98%]
.....                                                                    [100%]

=============================== warnings summary ===============================
tests/architecture/test_b02_strategy_promotion_boundaries.py: 1 warning
tests/architecture/test_b04_boundaries.py: 1 warning
tests/architecture/test_b05_review_boundaries.py: 1 warning
tests/architecture/test_b15_package_boundaries.py: 1 warning
tests/architecture/test_b20_screening_boundaries.py: 1 warning
tests/architecture/test_basic_approval.py: 1 warning
tests/architecture/test_pr2_19_boundaries.py: 43 warnings
tests/architecture/test_pr3_02_s1_boundaries.py: 1 warning
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 373 passed, 50 warnings in 20.95s =======================
```

Exit code: **0**.

### S7-SCHEMA

```sh
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_02_s2_intent_guards.py tests/integration/phase3/test_pr3_02_s2_intent_migration.py
```

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 51 items

tests/integration/phase3/test_pr3_02_s2_intent_guards.py ............... [ 29%]
..............................                                           [ 88%]
tests/integration/phase3/test_pr3_02_s2_intent_migration.py ......       [100%]

=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py: 62 warnings
tests/integration/phase3/test_pr3_02_s2_intent_migration.py: 16 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 51 passed, 78 warnings in 37.89s =======================
```

Exit code: **0**.

### S7-EXEC

```sh
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_02_s2_intent_execution.py
```

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 19 items

tests/integration/phase3/test_pr3_02_s2_intent_execution.py ............ [ 63%]
.......                                                                  [100%]

=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_execution.py: 38 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 19 passed, 38 warnings in 20.09s =======================
```

Exit code: **0**.

### S7-RACES

```sh
uv run pytest -o addopts='' -ra -s tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py tests/integration/phase3/test_pr3_02_s2_intent_replay.py
```

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 23 items

tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "e63e2137-fefe-486e-bad1-e3409df336cb", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 32.915, "error_code": null, "level": "INFO", "project_id": "25e5a65e-5f78-4e98-a30a-564b1b11be30", "request_id": "5b1b0f91-da46-419b-aaf3-53a73616ab44", "result": "success", "rollback": false, "target_id": "25e5a65e-5f78-4e98-a30a-564b1b11be30", "timestamp": "2026-10-26T06:31:21.343475+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:21.345026+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 1.437, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:21.345094+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.495, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:21.345132+00:00"}
INFO  [researchbase.commands] {"actor_id": "e63e2137-fefe-486e-bad1-e3409df336cb", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 9.932, "error_code": null, "level": "INFO", "project_id": null, "request_id": "5b1b0f91-da46-419b-aaf3-53a73616ab44", "result": "success", "rollback": false, "target_id": "01a176e8-0bfd-723d-81bd-488b86e42707", "timestamp": "2026-10-26T06:31:21.355143+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:21.355930+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.751, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:21.355965+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.781, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-0c05-7469-9c3d-978ebb68838b", "timestamp": "2026-10-26T06:31:21.355986+00:00"}
INFO  [researchbase.commands] {"actor_id": "e63e2137-fefe-486e-bad1-e3409df336cb", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.426, "error_code": null, "level": "INFO", "project_id": null, "request_id": "5b1b0f91-da46-419b-aaf3-53a73616ab44", "result": "success", "rollback": false, "target_id": "01a176e8-0c05-7469-9c3d-978ebb68838b", "timestamp": "2026-10-26T06:31:21.359442+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:21.359957+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.498, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:21.359984+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.522, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-0c05-7469-9c3d-978ebb68838b", "timestamp": "2026-10-26T06:31:21.360003+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "e63e2137-fefe-486e-bad1-e3409df336cb", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 3.118, "error_code": null, "level": "INFO", "project_id": "25e5a65e-5f78-4e98-a30a-564b1b11be30", "request_id": "df5185fb-6f82-4f2f-92ab-549f3b50dfe9", "result": "success", "rollback": false, "target_id": "25e5a65e-5f78-4e98-a30a-564b1b11be30", "timestamp": "2026-10-26T06:31:21.515265+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:21.516649+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 1.266, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:21.516724+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.33, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:21.516770+00:00"}
INFO  [researchbase.commands] {"actor_id": "e63e2137-fefe-486e-bad1-e3409df336cb", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 9.462, "error_code": null, "level": "INFO", "project_id": null, "request_id": "df5185fb-6f82-4f2f-92ab-549f3b50dfe9", "result": "success", "rollback": false, "target_id": "01a176e8-0caa-79e3-89c8-12415e716c30", "timestamp": "2026-10-26T06:31:21.526302+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:21.527150+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.799, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:21.527212+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.853, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-0cb1-71fa-895a-9323b91907c0", "timestamp": "2026-10-26T06:31:21.527253+00:00"}
INFO  [researchbase.commands] {"actor_id": "e63e2137-fefe-486e-bad1-e3409df336cb", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 4.745, "error_code": null, "level": "INFO", "project_id": null, "request_id": "df5185fb-6f82-4f2f-92ab-549f3b50dfe9", "result": "success", "rollback": false, "target_id": "01a176e8-0cb1-71fa-895a-9323b91907c0", "timestamp": "2026-10-26T06:31:21.532059+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:21.532852+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.751, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:21.532908+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.802, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-0cb1-71fa-895a-9323b91907c0", "timestamp": "2026-10-26T06:31:21.532947+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:21.548466+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:22.255622+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_94f385df0a134197bf915a952b37657d
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_94f385df0a134197bf915a952b37657d
wait evidence first_share {'xact_start': datetime.datetime(2026, 10, 26, 2, 31, 21, 549489, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'query_start': datetime.datetime(2026, 10, 26, 2, 31, 21, 549590, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'observed_at': datetime.datetime(2026, 10, 26, 2, 31, 21, 555585, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'query': 'LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_membership_events, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions, strategy_candidate_captures, strategy_candidate_sources, strategy_hypothesis_admissions, strategy_question_admissions IN SHARE MODE', 'expiry_at': datetime.datetime(2026, 10, 26, 2, 31, 22, 236930, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'lock_wait_started_at': datetime.datetime(2026, 10, 26, 2, 31, 21, 555585, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'lock_acquired_at': datetime.datetime(2026, 10, 26, 2, 31, 22, 249927, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'authorization_checked_at': datetime.datetime(2026, 10, 26, 6, 31, 22, 255190, tzinfo=datetime.timezone.utc)} effects {'agent_execution_instances': 0, 'agent_execution_events': 0, 'agent_command_receipts': 2, 'research_tasks': 1, 'research_task_steps': 2, 'research_task_events': 3, 'research_task_command_receipts': 3, 'budget_reservations': 0, 'budget_usage_records': 0, 'capability_invocations': 0, 'strategy_candidate_captures': 0, 'artifacts': 2, 'artifact_versions': 2}
.DISPOSABLE_DROPPED: researchbase_pr212_test_94f385df0a134197bf915a952b37657d
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "09a8f8a4-7485-4540-b3ab-01e5cd6ba503", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.51, "error_code": null, "level": "INFO", "project_id": "72a6ae83-a9a1-4731-8d8e-6e59214af629", "request_id": "16e07b12-c791-4bca-8e06-f72a45a635b4", "result": "success", "rollback": false, "target_id": "72a6ae83-a9a1-4731-8d8e-6e59214af629", "timestamp": "2026-10-26T06:31:23.247861+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:23.248680+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.758, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:23.248717+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.788, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:23.248738+00:00"}
INFO  [researchbase.commands] {"actor_id": "09a8f8a4-7485-4540-b3ab-01e5cd6ba503", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.541, "error_code": null, "level": "INFO", "project_id": null, "request_id": "16e07b12-c791-4bca-8e06-f72a45a635b4", "result": "success", "rollback": false, "target_id": "01a176e8-136e-7712-a196-3c506abd0cc4", "timestamp": "2026-10-26T06:31:23.254311+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:23.254837+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.512, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:23.254868+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.536, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-1373-7197-a17c-f6a4d2984f69", "timestamp": "2026-10-26T06:31:23.254885+00:00"}
INFO  [researchbase.commands] {"actor_id": "09a8f8a4-7485-4540-b3ab-01e5cd6ba503", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.811, "error_code": null, "level": "INFO", "project_id": null, "request_id": "16e07b12-c791-4bca-8e06-f72a45a635b4", "result": "success", "rollback": false, "target_id": "01a176e8-1373-7197-a17c-f6a4d2984f69", "timestamp": "2026-10-26T06:31:23.257726+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:23.258186+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.449, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:23.258212+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.47, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-1373-7197-a17c-f6a4d2984f69", "timestamp": "2026-10-26T06:31:23.258229+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "09a8f8a4-7485-4540-b3ab-01e5cd6ba503", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 3.055, "error_code": null, "level": "INFO", "project_id": "72a6ae83-a9a1-4731-8d8e-6e59214af629", "request_id": "51708518-486c-4f66-96dc-8e30b95fe2f7", "result": "success", "rollback": false, "target_id": "72a6ae83-a9a1-4731-8d8e-6e59214af629", "timestamp": "2026-10-26T06:31:23.400184+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:23.403563+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 3.284, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:23.403635+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 3.338, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:23.403674+00:00"}
INFO  [researchbase.commands] {"actor_id": "09a8f8a4-7485-4540-b3ab-01e5cd6ba503", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 8.324, "error_code": null, "level": "INFO", "project_id": null, "request_id": "51708518-486c-4f66-96dc-8e30b95fe2f7", "result": "success", "rollback": false, "target_id": "01a176e8-1407-7d34-9ce0-5e17b9cf9fa1", "timestamp": "2026-10-26T06:31:23.412055+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:23.412787+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.659, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:23.412834+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.704, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-1410-73ba-abc7-3482b2fde7c5", "timestamp": "2026-10-26T06:31:23.412867+00:00"}
INFO  [researchbase.commands] {"actor_id": "09a8f8a4-7485-4540-b3ab-01e5cd6ba503", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.668, "error_code": null, "level": "INFO", "project_id": null, "request_id": "51708518-486c-4f66-96dc-8e30b95fe2f7", "result": "success", "rollback": false, "target_id": "01a176e8-1410-73ba-abc7-3482b2fde7c5", "timestamp": "2026-10-26T06:31:23.416581+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:23.417207+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.6, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:23.417251+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.639, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-1410-73ba-abc7-3482b2fde7c5", "timestamp": "2026-10-26T06:31:23.417281+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:23.430176+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:24.132071+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_a434271f9a204f95a028e3728e424e0a
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_a434271f9a204f95a028e3728e424e0a
wait evidence second_key {'xact_start': datetime.datetime(2026, 10, 26, 2, 31, 23, 430809, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'query_start': datetime.datetime(2026, 10, 26, 2, 31, 23, 436592, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'observed_at': datetime.datetime(2026, 10, 26, 2, 31, 23, 439558, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'query': 'SELECT pg_advisory_xact_lock(hashtextextended($1,0))', 'expiry_at': datetime.datetime(2026, 10, 26, 2, 31, 24, 120433, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'lock_wait_started_at': datetime.datetime(2026, 10, 26, 2, 31, 23, 439558, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'lock_acquired_at': datetime.datetime(2026, 10, 26, 2, 31, 24, 128401, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'authorization_checked_at': datetime.datetime(2026, 10, 26, 6, 31, 24, 131198, tzinfo=datetime.timezone.utc)} effects {'agent_execution_instances': 0, 'agent_execution_events': 0, 'agent_command_receipts': 2, 'research_tasks': 1, 'research_task_steps': 2, 'research_task_events': 3, 'research_task_command_receipts': 3, 'budget_reservations': 0, 'budget_usage_records': 0, 'capability_invocations': 0, 'strategy_candidate_captures': 0, 'artifacts': 2, 'artifact_versions': 2}
.DISPOSABLE_DROPPED: researchbase_pr212_test_a434271f9a204f95a028e3728e424e0a
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "6c63faf9-70cc-422e-bce0-043f14816279", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 7.531, "error_code": null, "level": "INFO", "project_id": "fb92d675-6743-4480-b1fd-9422db26c26d", "request_id": "e95f23c8-8107-48cf-9183-a7922015f6f8", "result": "success", "rollback": false, "target_id": "fb92d675-6743-4480-b1fd-9422db26c26d", "timestamp": "2026-10-26T06:31:24.950403+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:24.953076+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 2.503, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:24.953253+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 2.639, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:24.953353+00:00"}
INFO  [researchbase.commands] {"actor_id": "6c63faf9-70cc-422e-bce0-043f14816279", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 15.135, "error_code": null, "level": "INFO", "project_id": null, "request_id": "e95f23c8-8107-48cf-9183-a7922015f6f8", "result": "success", "rollback": false, "target_id": "01a176e8-1a14-7c2b-9115-1c4378d2f0fb", "timestamp": "2026-10-26T06:31:24.968634+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:24.969918+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.214, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:24.969999+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.289, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-1a23-7298-9c16-48dbdaf646c0", "timestamp": "2026-10-26T06:31:24.970056+00:00"}
INFO  [researchbase.commands] {"actor_id": "6c63faf9-70cc-422e-bce0-043f14816279", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 6.078, "error_code": null, "level": "INFO", "project_id": null, "request_id": "e95f23c8-8107-48cf-9183-a7922015f6f8", "result": "success", "rollback": false, "target_id": "01a176e8-1a23-7298-9c16-48dbdaf646c0", "timestamp": "2026-10-26T06:31:24.976214+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:24.977356+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.085, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:24.977433+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.154, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-1a23-7298-9c16-48dbdaf646c0", "timestamp": "2026-10-26T06:31:24.977486+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "6c63faf9-70cc-422e-bce0-043f14816279", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 4.204, "error_code": null, "level": "INFO", "project_id": "fb92d675-6743-4480-b1fd-9422db26c26d", "request_id": "d6ae1cd8-bcbe-4353-8d93-0caf00a14e86", "result": "success", "rollback": false, "target_id": "fb92d675-6743-4480-b1fd-9422db26c26d", "timestamp": "2026-10-26T06:31:25.159490+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:25.161147+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 1.509, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:25.161233+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.588, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:25.161289+00:00"}
INFO  [researchbase.commands] {"actor_id": "6c63faf9-70cc-422e-bce0-043f14816279", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 11.034, "error_code": null, "level": "INFO", "project_id": null, "request_id": "d6ae1cd8-bcbe-4353-8d93-0caf00a14e86", "result": "success", "rollback": false, "target_id": "01a176e8-1ae5-78b5-8325-d824051088c0", "timestamp": "2026-10-26T06:31:25.172406+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:25.173549+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.083, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:25.173650+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.165, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-1aef-7c3d-9089-7a56671f2537", "timestamp": "2026-10-26T06:31:25.173714+00:00"}
INFO  [researchbase.commands] {"actor_id": "6c63faf9-70cc-422e-bce0-043f14816279", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 5.708, "error_code": null, "level": "INFO", "project_id": null, "request_id": "d6ae1cd8-bcbe-4353-8d93-0caf00a14e86", "result": "success", "rollback": false, "target_id": "01a176e8-1aef-7c3d-9089-7a56671f2537", "timestamp": "2026-10-26T06:31:25.179511+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:25.180426+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.871, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:25.180503+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.938, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-1aef-7c3d-9089-7a56671f2537", "timestamp": "2026-10-26T06:31:25.180556+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:25.198938+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:25.892408+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_324684104e674f7eb0fe110412e35c21
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_324684104e674f7eb0fe110412e35c21
wait evidence task_row {'xact_start': datetime.datetime(2026, 10, 26, 2, 31, 25, 199951, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'query_start': datetime.datetime(2026, 10, 26, 2, 31, 25, 211809, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'observed_at': datetime.datetime(2026, 10, 26, 2, 31, 25, 220039, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'query': 'SELECT id FROM research_tasks WHERE id=$1 FOR UPDATE', 'expiry_at': datetime.datetime(2026, 10, 26, 2, 31, 25, 885532, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'lock_wait_started_at': datetime.datetime(2026, 10, 26, 2, 31, 25, 220039, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'lock_acquired_at': datetime.datetime(2026, 10, 26, 2, 31, 25, 890048, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'authorization_checked_at': datetime.datetime(2026, 10, 26, 6, 31, 25, 891825, tzinfo=datetime.timezone.utc)} effects {'agent_execution_instances': 0, 'agent_execution_events': 0, 'agent_command_receipts': 2, 'research_tasks': 1, 'research_task_steps': 2, 'research_task_events': 3, 'research_task_command_receipts': 3, 'budget_reservations': 0, 'budget_usage_records': 0, 'capability_invocations': 0, 'strategy_candidate_captures': 0, 'artifacts': 2, 'artifact_versions': 2}
.DISPOSABLE_DROPPED: researchbase_pr212_test_324684104e674f7eb0fe110412e35c21
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "d437c059-13b0-475d-87ec-2c6e3a01204d", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 7.908, "error_code": null, "level": "INFO", "project_id": "42e0075c-009b-4562-b5fd-f7742305c5d3", "request_id": "2a6c179a-5c00-425c-8637-7bab1b16918c", "result": "success", "rollback": false, "target_id": "42e0075c-009b-4562-b5fd-f7742305c5d3", "timestamp": "2026-10-26T06:31:26.879812+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:26.882686+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 2.646, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:26.882848+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 2.788, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:26.882951+00:00"}
INFO  [researchbase.commands] {"actor_id": "d437c059-13b0-475d-87ec-2c6e3a01204d", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 12.329, "error_code": null, "level": "INFO", "project_id": null, "request_id": "2a6c179a-5c00-425c-8637-7bab1b16918c", "result": "success", "rollback": false, "target_id": "01a176e8-219d-7f23-820c-5afa74b0c363", "timestamp": "2026-10-26T06:31:26.895431+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:26.896698+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.189, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:26.896782+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.26, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-21a9-7e76-b918-57fc639dd84c", "timestamp": "2026-10-26T06:31:26.896834+00:00"}
INFO  [researchbase.commands] {"actor_id": "d437c059-13b0-475d-87ec-2c6e3a01204d", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 5.659, "error_code": null, "level": "INFO", "project_id": null, "request_id": "2a6c179a-5c00-425c-8637-7bab1b16918c", "result": "success", "rollback": false, "target_id": "01a176e8-21a9-7e76-b918-57fc639dd84c", "timestamp": "2026-10-26T06:31:26.902574+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:26.903498+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.878, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:26.903567+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.943, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-21a9-7e76-b918-57fc639dd84c", "timestamp": "2026-10-26T06:31:26.903618+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "d437c059-13b0-475d-87ec-2c6e3a01204d", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.337, "error_code": null, "level": "INFO", "project_id": "42e0075c-009b-4562-b5fd-f7742305c5d3", "request_id": "1a723c86-0480-4008-9629-513440e4f571", "result": "success", "rollback": false, "target_id": "42e0075c-009b-4562-b5fd-f7742305c5d3", "timestamp": "2026-10-26T06:31:27.158772+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:27.159766+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.939, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:27.159810+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.972, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:27.159834+00:00"}
INFO  [researchbase.commands] {"actor_id": "d437c059-13b0-475d-87ec-2c6e3a01204d", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 6.194, "error_code": null, "level": "INFO", "project_id": null, "request_id": "1a723c86-0480-4008-9629-513440e4f571", "result": "success", "rollback": false, "target_id": "01a176e8-22b5-7c3b-a6d6-ec1a26ef6eda", "timestamp": "2026-10-26T06:31:27.166061+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:27.166730+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.646, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:27.166768+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.676, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-22ba-7b23-a8b8-a37888e377c3", "timestamp": "2026-10-26T06:31:27.166791+00:00"}
INFO  [researchbase.commands] {"actor_id": "d437c059-13b0-475d-87ec-2c6e3a01204d", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.171, "error_code": null, "level": "INFO", "project_id": null, "request_id": "1a723c86-0480-4008-9629-513440e4f571", "result": "success", "rollback": false, "target_id": "01a176e8-22ba-7b23-a8b8-a37888e377c3", "timestamp": "2026-10-26T06:31:27.169992+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:27.170529+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.519, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:27.170560+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.546, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-22ba-7b23-a8b8-a37888e377c3", "timestamp": "2026-10-26T06:31:27.170580+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:27.187209+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:27.888610+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_d21a44d057444857a0f92b46f1122b9a
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_d21a44d057444857a0f92b46f1122b9a
wait evidence version_row {'xact_start': datetime.datetime(2026, 10, 26, 2, 31, 27, 187705, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'query_start': datetime.datetime(2026, 10, 26, 2, 31, 27, 199681, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'observed_at': datetime.datetime(2026, 10, 26, 2, 31, 27, 206137, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'query': 'SELECT id FROM agent_versions WHERE id=$1 FOR UPDATE', 'expiry_at': datetime.datetime(2026, 10, 26, 2, 31, 27, 874439, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'lock_wait_started_at': datetime.datetime(2026, 10, 26, 2, 31, 27, 206137, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'lock_acquired_at': datetime.datetime(2026, 10, 26, 2, 31, 27, 885906, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'authorization_checked_at': datetime.datetime(2026, 10, 26, 6, 31, 27, 887763, tzinfo=datetime.timezone.utc)} effects {'agent_execution_instances': 0, 'agent_execution_events': 0, 'agent_command_receipts': 2, 'research_tasks': 1, 'research_task_steps': 2, 'research_task_events': 3, 'research_task_command_receipts': 3, 'budget_reservations': 0, 'budget_usage_records': 0, 'capability_invocations': 0, 'strategy_candidate_captures': 0, 'artifacts': 2, 'artifact_versions': 2}
.DISPOSABLE_DROPPED: researchbase_pr212_test_d21a44d057444857a0f92b46f1122b9a
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "8d4ab078-ee06-49c7-aabe-2e31522ec127", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 9.524, "error_code": null, "level": "INFO", "project_id": "a95bad66-ed19-462c-9a38-43daf34185af", "request_id": "7cc18200-b7e3-48c2-b7d6-856444821462", "result": "success", "rollback": false, "target_id": "a95bad66-ed19-462c-9a38-43daf34185af", "timestamp": "2026-10-26T06:31:28.761981+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:28.764194+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 1.99, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:28.764312+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 2.1, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:28.764388+00:00"}
INFO  [researchbase.commands] {"actor_id": "8d4ab078-ee06-49c7-aabe-2e31522ec127", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 12.728, "error_code": null, "level": "INFO", "project_id": null, "request_id": "7cc18200-b7e3-48c2-b7d6-856444821462", "result": "success", "rollback": false, "target_id": "01a176e8-28f7-7add-82ca-1cfcd4cffcd0", "timestamp": "2026-10-26T06:31:28.777233+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:28.778444+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.117, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:28.778525+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.188, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-2903-7922-a0c9-d0c0d586e14d", "timestamp": "2026-10-26T06:31:28.778576+00:00"}
INFO  [researchbase.commands] {"actor_id": "8d4ab078-ee06-49c7-aabe-2e31522ec127", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 5.591, "error_code": null, "level": "INFO", "project_id": null, "request_id": "7cc18200-b7e3-48c2-b7d6-856444821462", "result": "success", "rollback": false, "target_id": "01a176e8-2903-7922-a0c9-d0c0d586e14d", "timestamp": "2026-10-26T06:31:28.784244+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:28.784968+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.689, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:28.785024+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.738, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-2903-7922-a0c9-d0c0d586e14d", "timestamp": "2026-10-26T06:31:28.785063+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "8d4ab078-ee06-49c7-aabe-2e31522ec127", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 6.48, "error_code": null, "level": "INFO", "project_id": "a95bad66-ed19-462c-9a38-43daf34185af", "request_id": "d3213b5d-0bf7-4b95-8530-9fd4fb76f3d6", "result": "success", "rollback": false, "target_id": "a95bad66-ed19-462c-9a38-43daf34185af", "timestamp": "2026-10-26T06:31:29.001300+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:29.003954+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 2.403, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:29.004106+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 2.534, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:29.004201+00:00"}
INFO  [researchbase.commands] {"actor_id": "8d4ab078-ee06-49c7-aabe-2e31522ec127", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 13.434, "error_code": null, "level": "INFO", "project_id": null, "request_id": "d3213b5d-0bf7-4b95-8530-9fd4fb76f3d6", "result": "success", "rollback": false, "target_id": "01a176e8-29e7-7fa3-8950-28ed18a673e2", "timestamp": "2026-10-26T06:31:29.017775+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:29.018890+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.045, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:29.018980+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.123, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-29f4-7771-987e-aa3e6eb241e8", "timestamp": "2026-10-26T06:31:29.019040+00:00"}
INFO  [researchbase.commands] {"actor_id": "8d4ab078-ee06-49c7-aabe-2e31522ec127", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 5.814, "error_code": null, "level": "INFO", "project_id": null, "request_id": "d3213b5d-0bf7-4b95-8530-9fd4fb76f3d6", "result": "success", "rollback": false, "target_id": "01a176e8-29f4-7771-987e-aa3e6eb241e8", "timestamp": "2026-10-26T06:31:29.024937+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:29.025723+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.747, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:29.025786+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.804, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-29f4-7771-987e-aa3e6eb241e8", "timestamp": "2026-10-26T06:31:29.025832+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:29.035801+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:29.042956+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:29.107676+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_007bd8e14a7946cc9079b0b5aed2d762
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_007bd8e14a7946cc9079b0b5aed2d762
.DISPOSABLE_DROPPED: researchbase_pr212_test_007bd8e14a7946cc9079b0b5aed2d762
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "8fb20805-01fe-4ad6-bcab-3c07a2b4b80f", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 7.242, "error_code": null, "level": "INFO", "project_id": "be10dcb0-788d-4df2-97eb-e934aefa82ac", "request_id": "665f93a5-1b4b-4869-a36f-dc21d6439878", "result": "success", "rollback": false, "target_id": "be10dcb0-788d-4df2-97eb-e934aefa82ac", "timestamp": "2026-10-26T06:31:29.922717+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:29.925063+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 2.142, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:29.925182+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 2.254, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:29.925261+00:00"}
INFO  [researchbase.commands] {"actor_id": "8fb20805-01fe-4ad6-bcab-3c07a2b4b80f", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 15.091, "error_code": null, "level": "INFO", "project_id": null, "request_id": "665f93a5-1b4b-4869-a36f-dc21d6439878", "result": "success", "rollback": false, "target_id": "01a176e8-2d80-7ec7-842b-9868b92ad961", "timestamp": "2026-10-26T06:31:29.940469+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:29.942013+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.423, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:29.942105+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.504, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-2d8c-7664-a124-4f82122eb430", "timestamp": "2026-10-26T06:31:29.942156+00:00"}
INFO  [researchbase.commands] {"actor_id": "8fb20805-01fe-4ad6-bcab-3c07a2b4b80f", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 6.538, "error_code": null, "level": "INFO", "project_id": null, "request_id": "665f93a5-1b4b-4869-a36f-dc21d6439878", "result": "success", "rollback": false, "target_id": "01a176e8-2d8c-7664-a124-4f82122eb430", "timestamp": "2026-10-26T06:31:29.948770+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:29.949724+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.901, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:29.949803+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.964, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-2d8c-7664-a124-4f82122eb430", "timestamp": "2026-10-26T06:31:29.949852+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "8fb20805-01fe-4ad6-bcab-3c07a2b4b80f", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 4.394, "error_code": null, "level": "INFO", "project_id": "be10dcb0-788d-4df2-97eb-e934aefa82ac", "request_id": "9e1ff736-7d7c-4cac-b745-97b8d8056238", "result": "success", "rollback": false, "target_id": "be10dcb0-788d-4df2-97eb-e934aefa82ac", "timestamp": "2026-10-26T06:31:30.138479+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:30.140456+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 1.804, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:30.140572+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.896, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:30.140633+00:00"}
INFO  [researchbase.commands] {"actor_id": "8fb20805-01fe-4ad6-bcab-3c07a2b4b80f", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 9.668, "error_code": null, "level": "INFO", "project_id": null, "request_id": "9e1ff736-7d7c-4cac-b745-97b8d8056238", "result": "success", "rollback": false, "target_id": "01a176e8-2e58-7a89-8798-3cb3a8fd6b30", "timestamp": "2026-10-26T06:31:30.150389+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:30.151460+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.017, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:30.151530+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.076, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-2e61-75bb-9d27-ce1bea4f3e86", "timestamp": "2026-10-26T06:31:30.151575+00:00"}
INFO  [researchbase.commands] {"actor_id": "8fb20805-01fe-4ad6-bcab-3c07a2b4b80f", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 5.084, "error_code": null, "level": "INFO", "project_id": null, "request_id": "9e1ff736-7d7c-4cac-b745-97b8d8056238", "result": "success", "rollback": false, "target_id": "01a176e8-2e61-75bb-9d27-ce1bea4f3e86", "timestamp": "2026-10-26T06:31:30.156722+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:30.157706+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.941, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:30.157767+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.997, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-2e61-75bb-9d27-ce1bea4f3e86", "timestamp": "2026-10-26T06:31:30.157808+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:30.181758+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:30.196783+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_7f3842f4c022459b948163656ab7fd95
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_7f3842f4c022459b948163656ab7fd95
.DISPOSABLE_DROPPED: researchbase_pr212_test_7f3842f4c022459b948163656ab7fd95
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "1bf6ba8b-8937-4358-898a-bb12784709af", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 3.47, "error_code": null, "level": "INFO", "project_id": "ba8318f4-4ec9-43cc-aa2d-7bb01dbaf957", "request_id": "0d672f08-df5a-4db5-916b-2eac264e2241", "result": "success", "rollback": false, "target_id": "ba8318f4-4ec9-43cc-aa2d-7bb01dbaf957", "timestamp": "2026-10-26T06:31:31.025587+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:31.026657+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.974, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:31.026708+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.018, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:31.026738+00:00"}
INFO  [researchbase.commands] {"actor_id": "1bf6ba8b-8937-4358-898a-bb12784709af", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 6.524, "error_code": null, "level": "INFO", "project_id": null, "request_id": "0d672f08-df5a-4db5-916b-2eac264e2241", "result": "success", "rollback": false, "target_id": "01a176e8-31d0-7b93-bd03-41cfeba16ad9", "timestamp": "2026-10-26T06:31:31.033308+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:31.033927+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.582, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:31.033969+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.62, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-31d5-7e0c-a3e6-de67c5c41cd4", "timestamp": "2026-10-26T06:31:31.033997+00:00"}
INFO  [researchbase.commands] {"actor_id": "1bf6ba8b-8937-4358-898a-bb12784709af", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.53, "error_code": null, "level": "INFO", "project_id": null, "request_id": "0d672f08-df5a-4db5-916b-2eac264e2241", "result": "success", "rollback": false, "target_id": "01a176e8-31d5-7e0c-a3e6-de67c5c41cd4", "timestamp": "2026-10-26T06:31:31.037570+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:31.038191+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.602, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:31.038243+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.638, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-31d5-7e0c-a3e6-de67c5c41cd4", "timestamp": "2026-10-26T06:31:31.038270+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "1bf6ba8b-8937-4358-898a-bb12784709af", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 5.999, "error_code": null, "level": "INFO", "project_id": "ba8318f4-4ec9-43cc-aa2d-7bb01dbaf957", "request_id": "7ad462e0-62f8-4456-9194-146063b0b5c2", "result": "success", "rollback": false, "target_id": "ba8318f4-4ec9-43cc-aa2d-7bb01dbaf957", "timestamp": "2026-10-26T06:31:31.266440+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:31.268965+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 2.293, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:31.269086+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 2.401, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:31.269164+00:00"}
INFO  [researchbase.commands] {"actor_id": "1bf6ba8b-8937-4358-898a-bb12784709af", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 14.924, "error_code": null, "level": "INFO", "project_id": null, "request_id": "7ad462e0-62f8-4456-9194-146063b0b5c2", "result": "success", "rollback": false, "target_id": "01a176e8-32c0-7db6-8f85-1fbf9b896d4f", "timestamp": "2026-10-26T06:31:31.284204+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:31.285478+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.175, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:31.285556+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.25, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-32cc-769c-bbea-72aedd773c33", "timestamp": "2026-10-26T06:31:31.285608+00:00"}
INFO  [researchbase.commands] {"actor_id": "1bf6ba8b-8937-4358-898a-bb12784709af", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 5.916, "error_code": null, "level": "INFO", "project_id": null, "request_id": "7ad462e0-62f8-4456-9194-146063b0b5c2", "result": "success", "rollback": false, "target_id": "01a176e8-32cc-769c-bbea-72aedd773c33", "timestamp": "2026-10-26T06:31:31.291603+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:31.292576+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.917, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:31.292650+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.984, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-32cc-769c-bbea-72aedd773c33", "timestamp": "2026-10-26T06:31:31.292703+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:31.325606+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:31.338817+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_c2d7787e1d9249c9a92842158ab25153
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_c2d7787e1d9249c9a92842158ab25153
.DISPOSABLE_DROPPED: researchbase_pr212_test_c2d7787e1d9249c9a92842158ab25153
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "d1e4c7d7-4384-4727-acc4-4cffba2d63b4", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.316, "error_code": null, "level": "INFO", "project_id": "bbcce60b-f031-43b7-ae6a-682fd58d8759", "request_id": "84b72937-eb97-48ca-86aa-cac9c359a54f", "result": "success", "rollback": false, "target_id": "bbcce60b-f031-43b7-ae6a-682fd58d8759", "timestamp": "2026-10-26T06:31:32.283026+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:32.283797+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.719, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:32.283834+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.747, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:32.283854+00:00"}
INFO  [researchbase.commands] {"actor_id": "d1e4c7d7-4384-4727-acc4-4cffba2d63b4", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.114, "error_code": null, "level": "INFO", "project_id": null, "request_id": "84b72937-eb97-48ca-86aa-cac9c359a54f", "result": "success", "rollback": false, "target_id": "01a176e8-36ba-7867-a63b-804b370af7c1", "timestamp": "2026-10-26T06:31:32.288994+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:32.289551+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.535, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:32.289584+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.56, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-36be-7efb-b002-f03313cc6f69", "timestamp": "2026-10-26T06:31:32.289603+00:00"}
INFO  [researchbase.commands] {"actor_id": "d1e4c7d7-4384-4727-acc4-4cffba2d63b4", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.037, "error_code": null, "level": "INFO", "project_id": null, "request_id": "84b72937-eb97-48ca-86aa-cac9c359a54f", "result": "success", "rollback": false, "target_id": "01a176e8-36be-7efb-b002-f03313cc6f69", "timestamp": "2026-10-26T06:31:32.292668+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:32.293165+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.485, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:32.293194+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.507, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-36be-7efb-b002-f03313cc6f69", "timestamp": "2026-10-26T06:31:32.293211+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "d1e4c7d7-4384-4727-acc4-4cffba2d63b4", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.148, "error_code": null, "level": "INFO", "project_id": "bbcce60b-f031-43b7-ae6a-682fd58d8759", "request_id": "0030bd3d-9f93-4c51-ae8f-2842d1671cd0", "result": "success", "rollback": false, "target_id": "bbcce60b-f031-43b7-ae6a-682fd58d8759", "timestamp": "2026-10-26T06:31:32.453392+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:32.454234+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.784, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:32.454270+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.814, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:32.454292+00:00"}
INFO  [researchbase.commands] {"actor_id": "d1e4c7d7-4384-4727-acc4-4cffba2d63b4", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.319, "error_code": null, "level": "INFO", "project_id": null, "request_id": "0030bd3d-9f93-4c51-ae8f-2842d1671cd0", "result": "success", "rollback": false, "target_id": "01a176e8-3764-7fcf-aba0-167d85c6cbae", "timestamp": "2026-10-26T06:31:32.459641+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:32.460148+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.487, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:32.460178+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.512, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-3768-7820-ba1b-537d84c478cc", "timestamp": "2026-10-26T06:31:32.460197+00:00"}
INFO  [researchbase.commands] {"actor_id": "d1e4c7d7-4384-4727-acc4-4cffba2d63b4", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.264, "error_code": null, "level": "INFO", "project_id": null, "request_id": "0030bd3d-9f93-4c51-ae8f-2842d1671cd0", "result": "success", "rollback": false, "target_id": "01a176e8-3768-7820-ba1b-537d84c478cc", "timestamp": "2026-10-26T06:31:32.463496+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:32.463962+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.453, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:32.463990+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.476, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-3768-7820-ba1b-537d84c478cc", "timestamp": "2026-10-26T06:31:32.464008+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:32.481431+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "INVALID_STATE_TRANSITION", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:32.506202+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_69c64c50642247568ead7d536ccfd739
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_69c64c50642247568ead7d536ccfd739
.DISPOSABLE_DROPPED: researchbase_pr212_test_69c64c50642247568ead7d536ccfd739
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "a32260c1-fc98-4f46-ad43-631ae074b552", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 3.929, "error_code": null, "level": "INFO", "project_id": "b075f215-9061-42be-a825-68a3bc895d26", "request_id": "dcc8ebdb-cb68-4b46-b7e1-975c6a85b4b1", "result": "success", "rollback": false, "target_id": "b075f215-9061-42be-a825-68a3bc895d26", "timestamp": "2026-10-26T06:31:33.152702+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:33.155652+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 2.886, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:33.155728+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 2.937, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:33.155766+00:00"}
INFO  [researchbase.commands] {"actor_id": "a32260c1-fc98-4f46-ad43-631ae074b552", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 6.881, "error_code": null, "level": "INFO", "project_id": null, "request_id": "dcc8ebdb-cb68-4b46-b7e1-975c6a85b4b1", "result": "success", "rollback": false, "target_id": "01a176e8-3a1f-7ded-bff8-980b82f66314", "timestamp": "2026-10-26T06:31:33.162702+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:33.163323+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.581, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:33.163367+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.621, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-3a27-744a-92fa-7d21c7ecf17d", "timestamp": "2026-10-26T06:31:33.163397+00:00"}
INFO  [researchbase.commands] {"actor_id": "a32260c1-fc98-4f46-ad43-631ae074b552", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.35, "error_code": null, "level": "INFO", "project_id": null, "request_id": "dcc8ebdb-cb68-4b46-b7e1-975c6a85b4b1", "result": "success", "rollback": false, "target_id": "01a176e8-3a27-744a-92fa-7d21c7ecf17d", "timestamp": "2026-10-26T06:31:33.166788+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:33.167407+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.594, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:33.167448+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.63, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-3a27-744a-92fa-7d21c7ecf17d", "timestamp": "2026-10-26T06:31:33.167477+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "a32260c1-fc98-4f46-ad43-631ae074b552", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 4.314, "error_code": null, "level": "INFO", "project_id": "b075f215-9061-42be-a825-68a3bc895d26", "request_id": "bd3b5962-bd2d-4217-90fb-d2d727ef1b00", "result": "success", "rollback": false, "target_id": "b075f215-9061-42be-a825-68a3bc895d26", "timestamp": "2026-10-26T06:31:33.350566+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:33.352252+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 1.541, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:33.352340+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.623, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:33.352397+00:00"}
INFO  [researchbase.commands] {"actor_id": "a32260c1-fc98-4f46-ad43-631ae074b552", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 9.98, "error_code": null, "level": "INFO", "project_id": null, "request_id": "bd3b5962-bd2d-4217-90fb-d2d727ef1b00", "result": "success", "rollback": false, "target_id": "01a176e8-3ae4-757b-aa9e-2613960c6035", "timestamp": "2026-10-26T06:31:33.362456+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:33.363317+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.811, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:33.363381+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.866, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-3aee-72ae-bef0-12164c608721", "timestamp": "2026-10-26T06:31:33.363423+00:00"}
INFO  [researchbase.commands] {"actor_id": "a32260c1-fc98-4f46-ad43-631ae074b552", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 4.368, "error_code": null, "level": "INFO", "project_id": null, "request_id": "bd3b5962-bd2d-4217-90fb-d2d727ef1b00", "result": "success", "rollback": false, "target_id": "01a176e8-3aee-72ae-bef0-12164c608721", "timestamp": "2026-10-26T06:31:33.367852+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:33.368512+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.632, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:33.368566+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.678, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-3aee-72ae-bef0-12164c608721", "timestamp": "2026-10-26T06:31:33.368602+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:33.393319+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "INVALID_STATE_TRANSITION", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:33.418714+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_b8d3a86aebca469795d9a7001aec9880
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_b8d3a86aebca469795d9a7001aec9880
.DISPOSABLE_DROPPED: researchbase_pr212_test_b8d3a86aebca469795d9a7001aec9880
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "4805439e-4fd4-44b7-bb49-0bd9f4fd0b9b", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 3.653, "error_code": null, "level": "INFO", "project_id": "59a48f19-4a83-4da7-85ec-e7c5e7329dd3", "request_id": "23fc9b4d-b244-46a9-a7fc-a0c87eae1e1a", "result": "success", "rollback": false, "target_id": "59a48f19-4a83-4da7-85ec-e7c5e7329dd3", "timestamp": "2026-10-26T06:31:34.230503+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:34.231484+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.898, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:34.231536+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.941, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:34.231567+00:00"}
INFO  [researchbase.commands] {"actor_id": "4805439e-4fd4-44b7-bb49-0bd9f4fd0b9b", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 6.801, "error_code": null, "level": "INFO", "project_id": null, "request_id": "23fc9b4d-b244-46a9-a7fc-a0c87eae1e1a", "result": "success", "rollback": false, "target_id": "01a176e8-3e55-7670-96d6-47a730937754", "timestamp": "2026-10-26T06:31:34.238412+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:34.239389+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.92, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:34.239442+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.964, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-3e5a-711d-b047-9e02fae7e1ef", "timestamp": "2026-10-26T06:31:34.239473+00:00"}
INFO  [researchbase.commands] {"actor_id": "4805439e-4fd4-44b7-bb49-0bd9f4fd0b9b", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 4.753, "error_code": null, "level": "INFO", "project_id": null, "request_id": "23fc9b4d-b244-46a9-a7fc-a0c87eae1e1a", "result": "success", "rollback": false, "target_id": "01a176e8-3e5a-711d-b047-9e02fae7e1ef", "timestamp": "2026-10-26T06:31:34.244274+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:34.245213+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.885, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:34.245271+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.938, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-3e5a-711d-b047-9e02fae7e1ef", "timestamp": "2026-10-26T06:31:34.245311+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "4805439e-4fd4-44b7-bb49-0bd9f4fd0b9b", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 4.562, "error_code": null, "level": "INFO", "project_id": "59a48f19-4a83-4da7-85ec-e7c5e7329dd3", "request_id": "cc8aae85-59d2-4a0e-ba03-683bee36b99e", "result": "success", "rollback": false, "target_id": "59a48f19-4a83-4da7-85ec-e7c5e7329dd3", "timestamp": "2026-10-26T06:31:34.421853+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:34.423757+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 1.75, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:34.423844+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.829, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:34.423902+00:00"}
INFO  [researchbase.commands] {"actor_id": "4805439e-4fd4-44b7-bb49-0bd9f4fd0b9b", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 9.526, "error_code": null, "level": "INFO", "project_id": null, "request_id": "cc8aae85-59d2-4a0e-ba03-683bee36b99e", "result": "success", "rollback": false, "target_id": "01a176e8-3f14-7ecd-965e-b34ff0f21aaa", "timestamp": "2026-10-26T06:31:34.433509+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:34.434317+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.761, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:34.434378+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.815, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-3f1d-75e3-9f97-e55b59a99605", "timestamp": "2026-10-26T06:31:34.434419+00:00"}
INFO  [researchbase.commands] {"actor_id": "4805439e-4fd4-44b7-bb49-0bd9f4fd0b9b", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 4.605, "error_code": null, "level": "INFO", "project_id": null, "request_id": "cc8aae85-59d2-4a0e-ba03-683bee36b99e", "result": "success", "rollback": false, "target_id": "01a176e8-3f1d-75e3-9f97-e55b59a99605", "timestamp": "2026-10-26T06:31:34.439088+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:34.439963+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.811, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:34.440022+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.864, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-3f1d-75e3-9f97-e55b59a99605", "timestamp": "2026-10-26T06:31:34.440061+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:34.455786+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_9b44ccc2176f4c50a77b2d535da21ebe
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_9b44ccc2176f4c50a77b2d535da21ebe
.DISPOSABLE_DROPPED: researchbase_pr212_test_9b44ccc2176f4c50a77b2d535da21ebe
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "8d628f51-a5a0-48d7-9ea4-0760124b9b3d", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 3.255, "error_code": null, "level": "INFO", "project_id": "bf0df167-0f43-4d4d-b99f-cfa46c79b78b", "request_id": "b6abbb78-3303-4cc3-82a2-3c492566f299", "result": "success", "rollback": false, "target_id": "bf0df167-0f43-4d4d-b99f-cfa46c79b78b", "timestamp": "2026-10-26T06:31:35.295765+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:35.296783+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.932, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.296830+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.974, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.296860+00:00"}
INFO  [researchbase.commands] {"actor_id": "8d628f51-a5a0-48d7-9ea4-0760124b9b3d", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 6.539, "error_code": null, "level": "INFO", "project_id": null, "request_id": "b6abbb78-3303-4cc3-82a2-3c492566f299", "result": "success", "rollback": false, "target_id": "01a176e8-427e-7ec2-a1e4-a12fd1457bc0", "timestamp": "2026-10-26T06:31:35.303442+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:35.304832+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.468, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.305003+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.58, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-4284-7b74-bac2-f02c858e520c", "timestamp": "2026-10-26T06:31:35.305105+00:00"}
INFO  [researchbase.commands] {"actor_id": "8d628f51-a5a0-48d7-9ea4-0760124b9b3d", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 9.106, "error_code": null, "level": "INFO", "project_id": null, "request_id": "b6abbb78-3303-4cc3-82a2-3c492566f299", "result": "success", "rollback": false, "target_id": "01a176e8-4284-7b74-bac2-f02c858e520c", "timestamp": "2026-10-26T06:31:35.314352+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:35.315671+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.236, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.315780+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.331, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-4284-7b74-bac2-f02c858e520c", "timestamp": "2026-10-26T06:31:35.315852+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [researchbase.commands] {"actor_id": "8d628f51-a5a0-48d7-9ea4-0760124b9b3d", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.225, "error_code": null, "level": "INFO", "project_id": "bf0df167-0f43-4d4d-b99f-cfa46c79b78b", "request_id": "a3b64b9e-8fe4-410b-b08e-62c626ca82e7", "result": "success", "rollback": false, "target_id": "bf0df167-0f43-4d4d-b99f-cfa46c79b78b", "timestamp": "2026-10-26T06:31:35.511331+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:35.511927+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.545, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.511957+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.57, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.511974+00:00"}
INFO  [researchbase.commands] {"actor_id": "8d628f51-a5a0-48d7-9ea4-0760124b9b3d", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 3.706, "error_code": null, "level": "INFO", "project_id": null, "request_id": "a3b64b9e-8fe4-410b-b08e-62c626ca82e7", "result": "success", "rollback": false, "target_id": "01a176e8-4356-761a-afe5-8140cc200460", "timestamp": "2026-10-26T06:31:35.515705+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:35.516139+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.421, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.516162+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.441, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-4359-773c-b125-d0582bba4c4a", "timestamp": "2026-10-26T06:31:35.516177+00:00"}
INFO  [researchbase.commands] {"actor_id": "8d628f51-a5a0-48d7-9ea4-0760124b9b3d", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.026, "error_code": null, "level": "INFO", "project_id": null, "request_id": "a3b64b9e-8fe4-410b-b08e-62c626ca82e7", "result": "success", "rollback": false, "target_id": "01a176e8-4359-773c-b125-d0582bba4c4a", "timestamp": "2026-10-26T06:31:35.518226+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:35.518633+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.397, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.518657+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.416, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-4359-773c-b125-d0582bba4c4a", "timestamp": "2026-10-26T06:31:35.518671+00:00"}
INFO  [researchbase.commands] {"actor_id": "8d628f51-a5a0-48d7-9ea4-0760124b9b3d", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.721, "error_code": null, "level": "INFO", "project_id": "bf0df167-0f43-4d4d-b99f-cfa46c79b78b", "request_id": "d8fbbfc2-489e-4419-8ff7-862fc058b07a", "result": "success", "rollback": false, "target_id": "bf0df167-0f43-4d4d-b99f-cfa46c79b78b", "timestamp": "2026-10-26T06:31:35.520567+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:35.520939+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.355, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.520959+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.373, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.520973+00:00"}
INFO  [researchbase.commands] {"actor_id": "8d628f51-a5a0-48d7-9ea4-0760124b9b3d", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 2.732, "error_code": null, "level": "INFO", "project_id": null, "request_id": "d8fbbfc2-489e-4419-8ff7-862fc058b07a", "result": "success", "rollback": false, "target_id": "01a176e8-4360-7e2d-91f5-034cbcf0fb7b", "timestamp": "2026-10-26T06:31:35.523725+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:35.524122+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.391, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.524147+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.408, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-4362-7445-bdd9-1ef235c38eb5", "timestamp": "2026-10-26T06:31:35.524159+00:00"}
INFO  [researchbase.commands] {"actor_id": "8d628f51-a5a0-48d7-9ea4-0760124b9b3d", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 1.756, "error_code": null, "level": "INFO", "project_id": null, "request_id": "d8fbbfc2-489e-4419-8ff7-862fc058b07a", "result": "success", "rollback": false, "target_id": "01a176e8-4362-7445-bdd9-1ef235c38eb5", "timestamp": "2026-10-26T06:31:35.525935+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:35.526340+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.399, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.526363+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.416, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-4362-7445-bdd9-1ef235c38eb5", "timestamp": "2026-10-26T06:31:35.526376+00:00"}
INFO  [researchbase.commands] {"actor_id": "8d628f51-a5a0-48d7-9ea4-0760124b9b3d", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 0.786, "error_code": null, "level": "INFO", "project_id": "bf0df167-0f43-4d4d-b99f-cfa46c79b78b", "request_id": "dad1064f-2c60-4b19-a857-df1934757c59", "result": "success", "rollback": false, "target_id": "bf0df167-0f43-4d4d-b99f-cfa46c79b78b", "timestamp": "2026-10-26T06:31:35.527336+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:35.527729+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.379, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.527753+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.397, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.527767+00:00"}
INFO  [researchbase.commands] {"actor_id": "8d628f51-a5a0-48d7-9ea4-0760124b9b3d", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 2.348, "error_code": null, "level": "INFO", "project_id": null, "request_id": "dad1064f-2c60-4b19-a857-df1934757c59", "result": "success", "rollback": false, "target_id": "01a176e8-4366-7b16-803c-b007fd57f85d", "timestamp": "2026-10-26T06:31:35.530134+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:35.530636+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.488, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.530668+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.513, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-4369-7179-bd5c-eaad2e650d3d", "timestamp": "2026-10-26T06:31:35.530688+00:00"}
INFO  [researchbase.commands] {"actor_id": "8d628f51-a5a0-48d7-9ea4-0760124b9b3d", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.051, "error_code": null, "level": "INFO", "project_id": null, "request_id": "dad1064f-2c60-4b19-a857-df1934757c59", "result": "success", "rollback": false, "target_id": "01a176e8-4369-7179-bd5c-eaad2e650d3d", "timestamp": "2026-10-26T06:31:35.532762+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:35.533188+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.414, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.533213+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.434, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-4369-7179-bd5c-eaad2e650d3d", "timestamp": "2026-10-26T06:31:35.533229+00:00"}
INFO  [researchbase.commands] {"actor_id": "8d628f51-a5a0-48d7-9ea4-0760124b9b3d", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 0.845, "error_code": null, "level": "INFO", "project_id": "bf0df167-0f43-4d4d-b99f-cfa46c79b78b", "request_id": "636e8793-7f02-405c-ba74-804958fa897e", "result": "success", "rollback": false, "target_id": "bf0df167-0f43-4d4d-b99f-cfa46c79b78b", "timestamp": "2026-10-26T06:31:35.541579+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:35.542021+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.423, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.542043+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.442, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.542057+00:00"}
INFO  [researchbase.commands] {"actor_id": "8d628f51-a5a0-48d7-9ea4-0760124b9b3d", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 2.464, "error_code": null, "level": "INFO", "project_id": null, "request_id": "636e8793-7f02-405c-ba74-804958fa897e", "result": "success", "rollback": false, "target_id": "01a176e8-4375-774c-bd19-c1bd4e01e695", "timestamp": "2026-10-26T06:31:35.544544+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:35.544964+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.412, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.544988+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.43, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-4377-733b-8503-3826c8c04d63", "timestamp": "2026-10-26T06:31:35.545002+00:00"}
INFO  [researchbase.commands] {"actor_id": "8d628f51-a5a0-48d7-9ea4-0760124b9b3d", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 1.781, "error_code": null, "level": "INFO", "project_id": null, "request_id": "636e8793-7f02-405c-ba74-804958fa897e", "result": "success", "rollback": false, "target_id": "01a176e8-4377-733b-8503-3826c8c04d63", "timestamp": "2026-10-26T06:31:35.546804+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:35.547210+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.397, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.547234+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.414, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-4377-733b-8503-3826c8c04d63", "timestamp": "2026-10-26T06:31:35.547247+00:00"}
INFO  [researchbase.commands] {"actor_id": "8d628f51-a5a0-48d7-9ea4-0760124b9b3d", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 0.78, "error_code": null, "level": "INFO", "project_id": "bf0df167-0f43-4d4d-b99f-cfa46c79b78b", "request_id": "eec7b4cf-29b7-45fa-a825-3e9a6ece05fd", "result": "success", "rollback": false, "target_id": "bf0df167-0f43-4d4d-b99f-cfa46c79b78b", "timestamp": "2026-10-26T06:31:35.548062+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:35.548452+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.376, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.548475+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.392, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.548488+00:00"}
INFO  [researchbase.commands] {"actor_id": "8d628f51-a5a0-48d7-9ea4-0760124b9b3d", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 2.332, "error_code": null, "level": "INFO", "project_id": null, "request_id": "eec7b4cf-29b7-45fa-a825-3e9a6ece05fd", "result": "success", "rollback": false, "target_id": "01a176e8-437b-7b39-a29f-1ff9bcea01be", "timestamp": "2026-10-26T06:31:35.550839+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:35.551231+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.38, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.551252+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.398, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-437d-7b86-ae16-57ceebe4cfdf", "timestamp": "2026-10-26T06:31:35.551265+00:00"}
INFO  [researchbase.commands] {"actor_id": "8d628f51-a5a0-48d7-9ea4-0760124b9b3d", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 1.627, "error_code": null, "level": "INFO", "project_id": null, "request_id": "eec7b4cf-29b7-45fa-a825-3e9a6ece05fd", "result": "success", "rollback": false, "target_id": "01a176e8-437d-7b86-ae16-57ceebe4cfdf", "timestamp": "2026-10-26T06:31:35.552912+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:35.553308+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.388, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.553331+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.407, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-437d-7b86-ae16-57ceebe4cfdf", "timestamp": "2026-10-26T06:31:35.553347+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:35.554839+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "8d628f51-a5a0-48d7-9ea4-0760124b9b3d", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.551, "error_code": null, "level": "INFO", "project_id": "bf0df167-0f43-4d4d-b99f-cfa46c79b78b", "request_id": "e8c191f7-797c-4508-bf46-18612196269e", "result": "success", "rollback": false, "target_id": "bf0df167-0f43-4d4d-b99f-cfa46c79b78b", "timestamp": "2026-10-26T06:31:35.630118+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:35.630751+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.596, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.630777+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.617, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.630792+00:00"}
INFO  [researchbase.commands] {"actor_id": "8d628f51-a5a0-48d7-9ea4-0760124b9b3d", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 3.793, "error_code": null, "level": "INFO", "project_id": null, "request_id": "e8c191f7-797c-4508-bf46-18612196269e", "result": "success", "rollback": false, "target_id": "01a176e8-43cd-748d-8dda-262090606418", "timestamp": "2026-10-26T06:31:35.634606+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:35.635021+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.399, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.635040+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.416, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-43d0-76e3-a4ec-ee16369d045e", "timestamp": "2026-10-26T06:31:35.635052+00:00"}
INFO  [researchbase.commands] {"actor_id": "8d628f51-a5a0-48d7-9ea4-0760124b9b3d", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.062, "error_code": null, "level": "INFO", "project_id": null, "request_id": "e8c191f7-797c-4508-bf46-18612196269e", "result": "success", "rollback": false, "target_id": "01a176e8-43d0-76e3-a4ec-ee16369d045e", "timestamp": "2026-10-26T06:31:35.637133+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:35.637517+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.376, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:35.637536+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.391, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-43d0-76e3-a4ec-ee16369d045e", "timestamp": "2026-10-26T06:31:35.637548+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:35.639820+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:35.673531+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_9f0f37d7ddca406dad1dd5d0a57a5416
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_9f0f37d7ddca406dad1dd5d0a57a5416
.DISPOSABLE_DROPPED: researchbase_pr212_test_9f0f37d7ddca406dad1dd5d0a57a5416

tests/integration/phase3/test_pr3_02_s2_intent_replay.py INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "d1414b09-5544-4ea6-a26f-737e542aabac", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.571, "error_code": null, "level": "INFO", "project_id": "0470ef84-049a-4582-8d44-0d236cb466af", "request_id": "aae00b19-0cfb-4513-8dd8-ba69a293956b", "result": "success", "rollback": false, "target_id": "0470ef84-049a-4582-8d44-0d236cb466af", "timestamp": "2026-10-26T06:31:36.542088+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:36.542911+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.772, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:36.542949+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.802, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:36.542971+00:00"}
INFO  [researchbase.commands] {"actor_id": "d1414b09-5544-4ea6-a26f-737e542aabac", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.54, "error_code": null, "level": "INFO", "project_id": null, "request_id": "aae00b19-0cfb-4513-8dd8-ba69a293956b", "result": "success", "rollback": false, "target_id": "01a176e8-475d-7834-b91f-ed5a1ae47bff", "timestamp": "2026-10-26T06:31:36.548541+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:36.549094+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.535, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:36.549126+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.561, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-4761-74ef-98c2-20df86919545", "timestamp": "2026-10-26T06:31:36.549145+00:00"}
INFO  [researchbase.commands] {"actor_id": "d1414b09-5544-4ea6-a26f-737e542aabac", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.984, "error_code": null, "level": "INFO", "project_id": null, "request_id": "aae00b19-0cfb-4513-8dd8-ba69a293956b", "result": "success", "rollback": false, "target_id": "01a176e8-4761-74ef-98c2-20df86919545", "timestamp": "2026-10-26T06:31:36.552156+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:36.552665+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.493, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:36.552694+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.517, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-4761-74ef-98c2-20df86919545", "timestamp": "2026-10-26T06:31:36.552713+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "d1414b09-5544-4ea6-a26f-737e542aabac", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.754, "error_code": null, "level": "INFO", "project_id": "0470ef84-049a-4582-8d44-0d236cb466af", "request_id": "1acc635b-7c33-4904-84dd-516470e28856", "result": "success", "rollback": false, "target_id": "0470ef84-049a-4582-8d44-0d236cb466af", "timestamp": "2026-10-26T06:31:36.690885+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:36.691574+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.648, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:36.691603+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.671, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:36.691620+00:00"}
INFO  [researchbase.commands] {"actor_id": "d1414b09-5544-4ea6-a26f-737e542aabac", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.087, "error_code": null, "level": "INFO", "project_id": null, "request_id": "1acc635b-7c33-4904-84dd-516470e28856", "result": "success", "rollback": false, "target_id": "01a176e8-47f2-7aa1-b8ef-9fca778c6c45", "timestamp": "2026-10-26T06:31:36.696730+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:36.697182+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.44, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:36.697204+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.458, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-47f6-7f85-9dfb-30f5232969f1", "timestamp": "2026-10-26T06:31:36.697217+00:00"}
INFO  [researchbase.commands] {"actor_id": "d1414b09-5544-4ea6-a26f-737e542aabac", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.456, "error_code": null, "level": "INFO", "project_id": null, "request_id": "1acc635b-7c33-4904-84dd-516470e28856", "result": "success", "rollback": false, "target_id": "01a176e8-47f6-7f85-9dfb-30f5232969f1", "timestamp": "2026-10-26T06:31:36.699697+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:36.700122+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.41, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:36.700143+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.428, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-47f6-7f85-9dfb-30f5232969f1", "timestamp": "2026-10-26T06:31:36.700157+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:36.704997+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:36.733211+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:36.741356+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:36.742155+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:36.744781+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FROZEN_REFERENCE_REQUIRED", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:36.751972+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_97798bae5f874d35a4abc8bbb474f739
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_97798bae5f874d35a4abc8bbb474f739
.DISPOSABLE_DROPPED: researchbase_pr212_test_97798bae5f874d35a4abc8bbb474f739
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "aba65710-d64c-429f-871a-8a9a90d8aac1", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 3.131, "error_code": null, "level": "INFO", "project_id": "96d3e8a1-74e2-4c20-a83c-ede84e743477", "request_id": "f560e29a-a4e7-4b16-b919-c4da7be45260", "result": "success", "rollback": false, "target_id": "96d3e8a1-74e2-4c20-a83c-ede84e743477", "timestamp": "2026-10-26T06:31:37.416555+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:37.417579+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.945, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:37.417632+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.988, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:37.417663+00:00"}
INFO  [researchbase.commands] {"actor_id": "aba65710-d64c-429f-871a-8a9a90d8aac1", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 6.4, "error_code": null, "level": "INFO", "project_id": null, "request_id": "f560e29a-a4e7-4b16-b919-c4da7be45260", "result": "success", "rollback": false, "target_id": "01a176e8-4ac7-7b4b-9dcb-d342db2af771", "timestamp": "2026-10-26T06:31:37.424107+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:37.424739+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.591, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:37.424781+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.628, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-4acc-71c0-bacb-a31eaea464c9", "timestamp": "2026-10-26T06:31:37.424810+00:00"}
INFO  [researchbase.commands] {"actor_id": "aba65710-d64c-429f-871a-8a9a90d8aac1", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.441, "error_code": null, "level": "INFO", "project_id": null, "request_id": "f560e29a-a4e7-4b16-b919-c4da7be45260", "result": "success", "rollback": false, "target_id": "01a176e8-4acc-71c0-bacb-a31eaea464c9", "timestamp": "2026-10-26T06:31:37.428292+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:37.428829+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.503, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:37.428868+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.538, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-4acc-71c0-bacb-a31eaea464c9", "timestamp": "2026-10-26T06:31:37.428896+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "aba65710-d64c-429f-871a-8a9a90d8aac1", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 4.171, "error_code": null, "level": "INFO", "project_id": "96d3e8a1-74e2-4c20-a83c-ede84e743477", "request_id": "edcb50e1-5691-4db6-ace7-967ae3a9227a", "result": "success", "rollback": false, "target_id": "96d3e8a1-74e2-4c20-a83c-ede84e743477", "timestamp": "2026-10-26T06:31:37.619167+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:37.621061+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 1.761, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:37.621167+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.854, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:37.621238+00:00"}
INFO  [researchbase.commands] {"actor_id": "aba65710-d64c-429f-871a-8a9a90d8aac1", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 9.945, "error_code": null, "level": "INFO", "project_id": null, "request_id": "edcb50e1-5691-4db6-ace7-967ae3a9227a", "result": "success", "rollback": false, "target_id": "01a176e8-4b91-7418-bf73-b77308bca5e0", "timestamp": "2026-10-26T06:31:37.631271+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:37.634105+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 2.795, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:37.634177+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 2.855, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-4b9a-7933-bdae-824dc44f957e", "timestamp": "2026-10-26T06:31:37.634223+00:00"}
INFO  [researchbase.commands] {"actor_id": "aba65710-d64c-429f-871a-8a9a90d8aac1", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 4.126, "error_code": null, "level": "INFO", "project_id": null, "request_id": "edcb50e1-5691-4db6-ace7-967ae3a9227a", "result": "success", "rollback": false, "target_id": "01a176e8-4b9a-7933-bdae-824dc44f957e", "timestamp": "2026-10-26T06:31:37.638414+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:37.639309+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.843, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:37.639360+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.899, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-4b9a-7933-bdae-824dc44f957e", "timestamp": "2026-10-26T06:31:37.639395+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:37.645908+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:37.682178+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:37.693258+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:37.694305+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:37.697638+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "PROVENANCE_CLOSURE_VIOLATION", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:37.705182+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_281a493430c44cad80105cbc412e9e41
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_281a493430c44cad80105cbc412e9e41
.DISPOSABLE_DROPPED: researchbase_pr212_test_281a493430c44cad80105cbc412e9e41
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "fe7e0120-b7ed-4b9f-8fae-8b1b994c0766", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 9.049, "error_code": null, "level": "INFO", "project_id": "dd7e6cb0-3248-4f75-bf80-78324a1f4c0e", "request_id": "87b7bc3e-2ded-447c-8e9b-5cf8009b6826", "result": "success", "rollback": false, "target_id": "dd7e6cb0-3248-4f75-bf80-78324a1f4c0e", "timestamp": "2026-10-26T06:31:38.505117+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:38.579472+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 74.081, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:38.579546+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 74.139, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:38.579571+00:00"}
INFO  [researchbase.commands] {"actor_id": "fe7e0120-b7ed-4b9f-8fae-8b1b994c0766", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.793, "error_code": null, "level": "INFO", "project_id": null, "request_id": "87b7bc3e-2ded-447c-8e9b-5cf8009b6826", "result": "success", "rollback": false, "target_id": "01a176e8-4f06-714b-a7e8-5fa9f7bb4822", "timestamp": "2026-10-26T06:31:38.585399+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:38.585911+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.482, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:38.585942+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.507, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-4f56-75eb-b8de-c122ccb15d79", "timestamp": "2026-10-26T06:31:38.585959+00:00"}
INFO  [researchbase.commands] {"actor_id": "fe7e0120-b7ed-4b9f-8fae-8b1b994c0766", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.661, "error_code": null, "level": "INFO", "project_id": null, "request_id": "87b7bc3e-2ded-447c-8e9b-5cf8009b6826", "result": "success", "rollback": false, "target_id": "01a176e8-4f56-75eb-b8de-c122ccb15d79", "timestamp": "2026-10-26T06:31:38.588644+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:38.589093+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.437, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:38.589119+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.457, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-4f56-75eb-b8de-c122ccb15d79", "timestamp": "2026-10-26T06:31:38.589134+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "fe7e0120-b7ed-4b9f-8fae-8b1b994c0766", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.757, "error_code": null, "level": "INFO", "project_id": "dd7e6cb0-3248-4f75-bf80-78324a1f4c0e", "request_id": "7b5d739c-f41b-448b-8ea5-582328e0fbef", "result": "success", "rollback": false, "target_id": "dd7e6cb0-3248-4f75-bf80-78324a1f4c0e", "timestamp": "2026-10-26T06:31:38.730266+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:38.731000+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.695, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:38.731032+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.72, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:38.731050+00:00"}
INFO  [researchbase.commands] {"actor_id": "fe7e0120-b7ed-4b9f-8fae-8b1b994c0766", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 4.627, "error_code": null, "level": "INFO", "project_id": null, "request_id": "7b5d739c-f41b-448b-8ea5-582328e0fbef", "result": "success", "rollback": false, "target_id": "01a176e8-4fe9-7607-96c1-c3a38a28449c", "timestamp": "2026-10-26T06:31:38.735706+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:38.736173+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.453, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:38.736199+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.474, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-4fed-7f65-9c6d-25d6998c1de3", "timestamp": "2026-10-26T06:31:38.736214+00:00"}
INFO  [researchbase.commands] {"actor_id": "fe7e0120-b7ed-4b9f-8fae-8b1b994c0766", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.419, "error_code": null, "level": "INFO", "project_id": null, "request_id": "7b5d739c-f41b-448b-8ea5-582328e0fbef", "result": "success", "rollback": false, "target_id": "01a176e8-4fed-7f65-9c6d-25d6998c1de3", "timestamp": "2026-10-26T06:31:38.738657+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:38.739083+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.413, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:38.739106+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.433, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-4fed-7f65-9c6d-25d6998c1de3", "timestamp": "2026-10-26T06:31:38.739121+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:38.747020+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:38.750728+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:38.782014+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_a8152c6dbb714f1d85f6b2daba9610f8
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_a8152c6dbb714f1d85f6b2daba9610f8
.DISPOSABLE_DROPPED: researchbase_pr212_test_a8152c6dbb714f1d85f6b2daba9610f8
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "ede1785b-3d34-43f3-904b-f0ae2521e1e6", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 7.547, "error_code": null, "level": "INFO", "project_id": "a452f33f-ccaa-4aaa-915e-452923cc059e", "request_id": "de5116bb-b4b6-45be-8fda-238b8742d4f2", "result": "success", "rollback": false, "target_id": "a452f33f-ccaa-4aaa-915e-452923cc059e", "timestamp": "2026-10-26T06:31:39.457043+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:39.459851+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 2.598, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:39.460011+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 2.739, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:39.460115+00:00"}
INFO  [researchbase.commands] {"actor_id": "ede1785b-3d34-43f3-904b-f0ae2521e1e6", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 18.598, "error_code": null, "level": "INFO", "project_id": null, "request_id": "de5116bb-b4b6-45be-8fda-238b8742d4f2", "result": "success", "rollback": false, "target_id": "01a176e8-52be-7784-92df-98fca7a328a7", "timestamp": "2026-10-26T06:31:39.478865+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:39.480781+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.77, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:39.480899+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.872, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-52cc-7f80-9e95-2595eac2eca4", "timestamp": "2026-10-26T06:31:39.480972+00:00"}
INFO  [researchbase.commands] {"actor_id": "ede1785b-3d34-43f3-904b-f0ae2521e1e6", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 6.704, "error_code": null, "level": "INFO", "project_id": null, "request_id": "de5116bb-b4b6-45be-8fda-238b8742d4f2", "result": "success", "rollback": false, "target_id": "01a176e8-52cc-7f80-9e95-2595eac2eca4", "timestamp": "2026-10-26T06:31:39.487779+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:39.488754+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.951, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:39.488847+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.024, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-52cc-7f80-9e95-2595eac2eca4", "timestamp": "2026-10-26T06:31:39.488906+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "ede1785b-3d34-43f3-904b-f0ae2521e1e6", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 3.083, "error_code": null, "level": "INFO", "project_id": "a452f33f-ccaa-4aaa-915e-452923cc059e", "request_id": "70817a35-1f81-4f39-8977-8b06f3acb920", "result": "success", "rollback": false, "target_id": "a452f33f-ccaa-4aaa-915e-452923cc059e", "timestamp": "2026-10-26T06:31:39.683320+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:39.684378+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.957, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:39.684427+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.999, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:39.684456+00:00"}
INFO  [researchbase.commands] {"actor_id": "ede1785b-3d34-43f3-904b-f0ae2521e1e6", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 7.173, "error_code": null, "level": "INFO", "project_id": null, "request_id": "70817a35-1f81-4f39-8977-8b06f3acb920", "result": "success", "rollback": false, "target_id": "01a176e8-53a2-7eaa-a69d-316499304b33", "timestamp": "2026-10-26T06:31:39.691679+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:39.692327+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.603, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:39.692368+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.644, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-53a7-78c9-ad3b-3eae069898fa", "timestamp": "2026-10-26T06:31:39.692400+00:00"}
INFO  [researchbase.commands] {"actor_id": "ede1785b-3d34-43f3-904b-f0ae2521e1e6", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.679, "error_code": null, "level": "INFO", "project_id": null, "request_id": "70817a35-1f81-4f39-8977-8b06f3acb920", "result": "success", "rollback": false, "target_id": "01a176e8-53a7-78c9-ad3b-3eae069898fa", "timestamp": "2026-10-26T06:31:39.696121+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:39.696738+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.582, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:39.696778+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.619, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-53a7-78c9-ad3b-3eae069898fa", "timestamp": "2026-10-26T06:31:39.696806+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:39.703060+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:39.733657+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:39.734840+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:39.738635+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_7720f547bd604cb4b144920ab67841ed
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_7720f547bd604cb4b144920ab67841ed
.DISPOSABLE_DROPPED: researchbase_pr212_test_7720f547bd604cb4b144920ab67841ed
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "d3b98c18-b254-4e5b-a612-60881d980517", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 7.45, "error_code": null, "level": "INFO", "project_id": "4eaf70ef-2e86-44f4-be6e-bcd663e1b018", "request_id": "356f3465-c39f-4482-82e8-89e76055ccb9", "result": "success", "rollback": false, "target_id": "4eaf70ef-2e86-44f4-be6e-bcd663e1b018", "timestamp": "2026-10-26T06:31:40.474390+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:40.477013+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 2.436, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:40.477147+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 2.548, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:40.477226+00:00"}
INFO  [researchbase.commands] {"actor_id": "d3b98c18-b254-4e5b-a612-60881d980517", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 12.212, "error_code": null, "level": "INFO", "project_id": null, "request_id": "356f3465-c39f-4482-82e8-89e76055ccb9", "result": "success", "rollback": false, "target_id": "01a176e8-56b8-7175-8bda-804c5d01da22", "timestamp": "2026-10-26T06:31:40.489547+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:40.490586+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.969, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:40.490662+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.036, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-56c3-794e-84bf-f3424ce84b48", "timestamp": "2026-10-26T06:31:40.490713+00:00"}
INFO  [researchbase.commands] {"actor_id": "d3b98c18-b254-4e5b-a612-60881d980517", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 5.685, "error_code": null, "level": "INFO", "project_id": null, "request_id": "356f3465-c39f-4482-82e8-89e76055ccb9", "result": "success", "rollback": false, "target_id": "01a176e8-56c3-794e-84bf-f3424ce84b48", "timestamp": "2026-10-26T06:31:40.496472+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:40.497396+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.884, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:40.497464+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.945, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-56c3-794e-84bf-f3424ce84b48", "timestamp": "2026-10-26T06:31:40.497511+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "d3b98c18-b254-4e5b-a612-60881d980517", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.244, "error_code": null, "level": "INFO", "project_id": "4eaf70ef-2e86-44f4-be6e-bcd663e1b018", "request_id": "6ccba20b-cdd6-4956-be1a-24d7b1f28305", "result": "success", "rollback": false, "target_id": "4eaf70ef-2e86-44f4-be6e-bcd663e1b018", "timestamp": "2026-10-26T06:31:40.759685+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:40.760567+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.825, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:40.760609+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.861, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:40.760636+00:00"}
INFO  [researchbase.commands] {"actor_id": "d3b98c18-b254-4e5b-a612-60881d980517", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 6.118, "error_code": null, "level": "INFO", "project_id": null, "request_id": "6ccba20b-cdd6-4956-be1a-24d7b1f28305", "result": "success", "rollback": false, "target_id": "01a176e8-57d6-7fe6-b8e5-3c860f0f9cc3", "timestamp": "2026-10-26T06:31:40.766786+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:40.767358+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.549, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:40.767394+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.578, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-57db-7469-bbae-2abba3b2e2ba", "timestamp": "2026-10-26T06:31:40.767416+00:00"}
INFO  [researchbase.commands] {"actor_id": "d3b98c18-b254-4e5b-a612-60881d980517", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.014, "error_code": null, "level": "INFO", "project_id": null, "request_id": "6ccba20b-cdd6-4956-be1a-24d7b1f28305", "result": "success", "rollback": false, "target_id": "01a176e8-57db-7469-bbae-2abba3b2e2ba", "timestamp": "2026-10-26T06:31:40.770461+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:40.770959+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.482, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:40.770989+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.507, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-57db-7469-bbae-2abba3b2e2ba", "timestamp": "2026-10-26T06:31:40.771008+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:40.777366+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:40.827710+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:40.837109+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:40.837924+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:40.838744+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "IDEMPOTENCY_CONFLICT", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:40.846468+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:40.848585+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "IDEMPOTENCY_CONFLICT", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:40.849353+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:40.851246+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:40.851777+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:40.852389+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:40.852955+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_51c7aef3be194ec8be09f5caf4b81662
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_51c7aef3be194ec8be09f5caf4b81662
.DISPOSABLE_DROPPED: researchbase_pr212_test_51c7aef3be194ec8be09f5caf4b81662
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "11f80286-2302-422f-aecd-306043cde666", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 7.533, "error_code": null, "level": "INFO", "project_id": "1f815cdc-192e-4623-82a0-78a192cc8a1b", "request_id": "7fc735c2-26ad-46fa-930a-c608fbfb1d43", "result": "success", "rollback": false, "target_id": "1f815cdc-192e-4623-82a0-78a192cc8a1b", "timestamp": "2026-10-26T06:31:41.573172+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:41.576345+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 2.913, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:41.576520+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 3.056, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:41.576623+00:00"}
INFO  [researchbase.commands] {"actor_id": "11f80286-2302-422f-aecd-306043cde666", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 12.524, "error_code": null, "level": "INFO", "project_id": null, "request_id": "7fc735c2-26ad-46fa-930a-c608fbfb1d43", "result": "success", "rollback": false, "target_id": "01a176e8-5b02-7933-a98f-b441cf4470d1", "timestamp": "2026-10-26T06:31:41.589296+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:41.590664+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.286, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:41.590744+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.358, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-5b0f-71e1-88fe-46ef0bd77d4f", "timestamp": "2026-10-26T06:31:41.590798+00:00"}
INFO  [researchbase.commands] {"actor_id": "11f80286-2302-422f-aecd-306043cde666", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 5.779, "error_code": null, "level": "INFO", "project_id": null, "request_id": "7fc735c2-26ad-46fa-930a-c608fbfb1d43", "result": "success", "rollback": false, "target_id": "01a176e8-5b0f-71e1-88fe-46ef0bd77d4f", "timestamp": "2026-10-26T06:31:41.596656+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:41.597561+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.86, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:41.597628+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.922, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-5b0f-71e1-88fe-46ef0bd77d4f", "timestamp": "2026-10-26T06:31:41.597677+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "11f80286-2302-422f-aecd-306043cde666", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 4.393, "error_code": null, "level": "INFO", "project_id": "1f815cdc-192e-4623-82a0-78a192cc8a1b", "request_id": "2c787830-610f-4c79-a4b1-0e14b59c2204", "result": "success", "rollback": false, "target_id": "1f815cdc-192e-4623-82a0-78a192cc8a1b", "timestamp": "2026-10-26T06:31:41.795888+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:41.797597+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 1.541, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:41.797687+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.623, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:41.797744+00:00"}
INFO  [researchbase.commands] {"actor_id": "11f80286-2302-422f-aecd-306043cde666", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 12.364, "error_code": null, "level": "INFO", "project_id": null, "request_id": "2c787830-610f-4c79-a4b1-0e14b59c2204", "result": "success", "rollback": false, "target_id": "01a176e8-5be2-783e-a7b9-9a8e14382a1b", "timestamp": "2026-10-26T06:31:41.810188+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:41.811227+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.952, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:41.811298+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.012, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-5bed-7579-b205-58b5734ed8b0", "timestamp": "2026-10-26T06:31:41.811339+00:00"}
INFO  [researchbase.commands] {"actor_id": "11f80286-2302-422f-aecd-306043cde666", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 4.864, "error_code": null, "level": "INFO", "project_id": null, "request_id": "2c787830-610f-4c79-a4b1-0e14b59c2204", "result": "success", "rollback": false, "target_id": "01a176e8-5bed-7579-b205-58b5734ed8b0", "timestamp": "2026-10-26T06:31:41.816263+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:41.816997+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.699, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:41.817054+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.748, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-5bed-7579-b205-58b5734ed8b0", "timestamp": "2026-10-26T06:31:41.817093+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:41.824772+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:41.894239+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:41.910044+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:41.911801+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:41.913841+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "IDEMPOTENCY_CONFLICT", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:41.927754+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:41.931198+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "IDEMPOTENCY_CONFLICT", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:41.932621+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:41.936170+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:41.937369+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:41.938613+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:41.939699+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_72e412da7fc7498c9ef5dd9426f60f5f
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_72e412da7fc7498c9ef5dd9426f60f5f
.DISPOSABLE_DROPPED: researchbase_pr212_test_72e412da7fc7498c9ef5dd9426f60f5f
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "bcbd6710-4b70-469e-9589-d8c18b692430", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 7.662, "error_code": null, "level": "INFO", "project_id": "aceae519-82ed-4df8-b886-e4a70c5b5cbb", "request_id": "01e38907-ea00-4c20-beef-e3e015e737c5", "result": "success", "rollback": false, "target_id": "aceae519-82ed-4df8-b886-e4a70c5b5cbb", "timestamp": "2026-10-26T06:31:42.776472+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:42.779403+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 2.707, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:42.779561+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 2.841, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:42.779658+00:00"}
INFO  [researchbase.commands] {"actor_id": "bcbd6710-4b70-469e-9589-d8c18b692430", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 14.695, "error_code": null, "level": "INFO", "project_id": null, "request_id": "01e38907-ea00-4c20-beef-e3e015e737c5", "result": "success", "rollback": false, "target_id": "01a176e8-5fb6-7b4b-ad38-b027e1939ab2", "timestamp": "2026-10-26T06:31:42.794496+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:42.796090+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.507, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:42.796199+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.607, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-5fc3-7fe7-9ce3-6937d26bce24", "timestamp": "2026-10-26T06:31:42.796276+00:00"}
INFO  [researchbase.commands] {"actor_id": "bcbd6710-4b70-469e-9589-d8c18b692430", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 7.563, "error_code": null, "level": "INFO", "project_id": null, "request_id": "01e38907-ea00-4c20-beef-e3e015e737c5", "result": "success", "rollback": false, "target_id": "01a176e8-5fc3-7fe7-9ce3-6937d26bce24", "timestamp": "2026-10-26T06:31:42.803948+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:42.805270+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.25, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:42.805373+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.354, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-5fc3-7fe7-9ce3-6937d26bce24", "timestamp": "2026-10-26T06:31:42.805456+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "bcbd6710-4b70-469e-9589-d8c18b692430", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.135, "error_code": null, "level": "INFO", "project_id": "aceae519-82ed-4df8-b886-e4a70c5b5cbb", "request_id": "8a1a140c-8b91-4546-8522-eee13f0ea897", "result": "success", "rollback": false, "target_id": "aceae519-82ed-4df8-b886-e4a70c5b5cbb", "timestamp": "2026-10-26T06:31:43.053984+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:43.054868+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.835, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:43.054904+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.865, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:43.054926+00:00"}
INFO  [researchbase.commands] {"actor_id": "bcbd6710-4b70-469e-9589-d8c18b692430", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.742, "error_code": null, "level": "INFO", "project_id": null, "request_id": "8a1a140c-8b91-4546-8522-eee13f0ea897", "result": "success", "rollback": false, "target_id": "01a176e8-60cd-70e0-989b-e51263464820", "timestamp": "2026-10-26T06:31:43.060697+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:43.061388+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.669, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:43.061428+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.699, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-60d1-7ba0-9ef6-842fa021b7f6", "timestamp": "2026-10-26T06:31:43.061450+00:00"}
INFO  [researchbase.commands] {"actor_id": "bcbd6710-4b70-469e-9589-d8c18b692430", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.09, "error_code": null, "level": "INFO", "project_id": null, "request_id": "8a1a140c-8b91-4546-8522-eee13f0ea897", "result": "success", "rollback": false, "target_id": "01a176e8-60d1-7ba0-9ef6-842fa021b7f6", "timestamp": "2026-10-26T06:31:43.064571+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:43.065091+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.505, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:43.065123+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.528, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-60d1-7ba0-9ef6-842fa021b7f6", "timestamp": "2026-10-26T06:31:43.065141+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:43.071134+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:43.123338+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:43.133021+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:43.133853+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:43.134707+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "IDEMPOTENCY_CONFLICT", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:43.142142+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:43.144468+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "IDEMPOTENCY_CONFLICT", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:43.145223+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:43.147240+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:43.147783+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:43.148461+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:43.148993+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_4c6ef8b8a77d409b90787cef9c7c71ea
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_4c6ef8b8a77d409b90787cef9c7c71ea
.DISPOSABLE_DROPPED: researchbase_pr212_test_4c6ef8b8a77d409b90787cef9c7c71ea
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "5d304f40-a254-4aec-98be-e5c7a2c095b2", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 3.545, "error_code": null, "level": "INFO", "project_id": "8a341b4e-03a7-408a-b69f-6a525862908b", "request_id": "e709418e-07a8-4b4f-aec9-23251469c5f8", "result": "success", "rollback": false, "target_id": "8a341b4e-03a7-408a-b69f-6a525862908b", "timestamp": "2026-10-26T06:31:43.802584+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:43.803455+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.784, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:43.803505+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.827, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:43.803537+00:00"}
INFO  [researchbase.commands] {"actor_id": "5d304f40-a254-4aec-98be-e5c7a2c095b2", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 7.524, "error_code": null, "level": "INFO", "project_id": null, "request_id": "e709418e-07a8-4b4f-aec9-23251469c5f8", "result": "success", "rollback": false, "target_id": "01a176e8-63b9-7882-abbb-7d1dac01e42e", "timestamp": "2026-10-26T06:31:43.811105+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:43.811852+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.674, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:43.811901+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.721, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-63bf-7e23-a994-f8f7ac1b7361", "timestamp": "2026-10-26T06:31:43.811930+00:00"}
INFO  [researchbase.commands] {"actor_id": "5d304f40-a254-4aec-98be-e5c7a2c095b2", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.74, "error_code": null, "level": "INFO", "project_id": null, "request_id": "e709418e-07a8-4b4f-aec9-23251469c5f8", "result": "success", "rollback": false, "target_id": "01a176e8-63bf-7e23-a994-f8f7ac1b7361", "timestamp": "2026-10-26T06:31:43.815714+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:43.817191+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.52, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:43.817325+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.622, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-63bf-7e23-a994-f8f7ac1b7361", "timestamp": "2026-10-26T06:31:43.817416+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "5d304f40-a254-4aec-98be-e5c7a2c095b2", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 6.412, "error_code": null, "level": "INFO", "project_id": "8a341b4e-03a7-408a-b69f-6a525862908b", "request_id": "b1a5fab8-58b7-488c-b73a-d32c450917ba", "result": "success", "rollback": false, "target_id": "8a341b4e-03a7-408a-b69f-6a525862908b", "timestamp": "2026-10-26T06:31:44.047739+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:44.050227+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 2.275, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:44.050357+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 2.386, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:44.050435+00:00"}
INFO  [researchbase.commands] {"actor_id": "5d304f40-a254-4aec-98be-e5c7a2c095b2", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 14.356, "error_code": null, "level": "INFO", "project_id": null, "request_id": "b1a5fab8-58b7-488c-b73a-d32c450917ba", "result": "success", "rollback": false, "target_id": "01a176e8-64ad-7645-a76c-2a3a53b12f81", "timestamp": "2026-10-26T06:31:44.064909+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:44.066194+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.217, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:44.066273+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.286, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-64b8-74cb-9677-62e2b58720f2", "timestamp": "2026-10-26T06:31:44.066327+00:00"}
INFO  [researchbase.commands] {"actor_id": "5d304f40-a254-4aec-98be-e5c7a2c095b2", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 5.971, "error_code": null, "level": "INFO", "project_id": null, "request_id": "b1a5fab8-58b7-488c-b73a-d32c450917ba", "result": "success", "rollback": false, "target_id": "01a176e8-64b8-74cb-9677-62e2b58720f2", "timestamp": "2026-10-26T06:31:44.072375+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:44.073542+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.063, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:44.073628+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.14, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-64b8-74cb-9677-62e2b58720f2", "timestamp": "2026-10-26T06:31:44.073686+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:44.083296+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:44.160282+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:44.174059+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:44.175315+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:44.176559+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "IDEMPOTENCY_CONFLICT", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:44.187200+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:44.190022+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "IDEMPOTENCY_CONFLICT", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:44.190988+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:44.193810+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:44.194617+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:44.195601+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:44.196350+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_24eae0d11add469998b6f3625018663b
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_24eae0d11add469998b6f3625018663b
.DISPOSABLE_DROPPED: researchbase_pr212_test_24eae0d11add469998b6f3625018663b
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "36f896a7-506e-41b1-9722-afa89c6dfa38", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 7.548, "error_code": null, "level": "INFO", "project_id": "a2ae2441-3f28-47da-9323-19f68ba77c7b", "request_id": "d3eadf7d-c618-4396-8016-1ac2c4ad9c89", "result": "success", "rollback": false, "target_id": "a2ae2441-3f28-47da-9323-19f68ba77c7b", "timestamp": "2026-10-26T06:31:44.981893+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:44.984681+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 2.566, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:44.984843+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 2.707, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:44.984946+00:00"}
INFO  [researchbase.commands] {"actor_id": "36f896a7-506e-41b1-9722-afa89c6dfa38", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 12.371, "error_code": null, "level": "INFO", "project_id": null, "request_id": "d3eadf7d-c618-4396-8016-1ac2c4ad9c89", "result": "success", "rollback": false, "target_id": "01a176e8-6853-7b56-bcf8-4d693a2724f4", "timestamp": "2026-10-26T06:31:44.997460+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:44.998484+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.952, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:44.998564+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.025, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-685f-7153-ba98-fc25e26a84a6", "timestamp": "2026-10-26T06:31:44.998620+00:00"}
INFO  [researchbase.commands] {"actor_id": "36f896a7-506e-41b1-9722-afa89c6dfa38", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 5.59, "error_code": null, "level": "INFO", "project_id": null, "request_id": "d3eadf7d-c618-4396-8016-1ac2c4ad9c89", "result": "success", "rollback": false, "target_id": "01a176e8-685f-7153-ba98-fc25e26a84a6", "timestamp": "2026-10-26T06:31:45.004284+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:45.005399+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.052, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:45.005490+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.159, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-685f-7153-ba98-fc25e26a84a6", "timestamp": "2026-10-26T06:31:45.005581+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "36f896a7-506e-41b1-9722-afa89c6dfa38", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 6.504, "error_code": null, "level": "INFO", "project_id": "a2ae2441-3f28-47da-9323-19f68ba77c7b", "request_id": "749b9b27-dc83-4b5d-888f-cc40ac5a6201", "result": "success", "rollback": false, "target_id": "a2ae2441-3f28-47da-9323-19f68ba77c7b", "timestamp": "2026-10-26T06:31:45.244661+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:45.247114+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 2.24, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:45.247235+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 2.35, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:45.247314+00:00"}
INFO  [researchbase.commands] {"actor_id": "36f896a7-506e-41b1-9722-afa89c6dfa38", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 14.156, "error_code": null, "level": "INFO", "project_id": null, "request_id": "749b9b27-dc83-4b5d-888f-cc40ac5a6201", "result": "success", "rollback": false, "target_id": "01a176e8-695a-7421-9fb0-88f6dc8790c1", "timestamp": "2026-10-26T06:31:45.261587+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:45.334240+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 72.587, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:45.334326+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 72.629, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-6966-7ab1-83c3-af1d2dace366", "timestamp": "2026-10-26T06:31:45.334352+00:00"}
INFO  [researchbase.commands] {"actor_id": "36f896a7-506e-41b1-9722-afa89c6dfa38", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 5.252, "error_code": null, "level": "INFO", "project_id": null, "request_id": "749b9b27-dc83-4b5d-888f-cc40ac5a6201", "result": "success", "rollback": false, "target_id": "01a176e8-6966-7ab1-83c3-af1d2dace366", "timestamp": "2026-10-26T06:31:45.339638+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:45.340345+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.681, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:45.340385+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.71, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-6966-7ab1-83c3-af1d2dace366", "timestamp": "2026-10-26T06:31:45.340406+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:45.353293+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:45.420828+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:45.432946+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:45.434025+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:45.435163+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "IDEMPOTENCY_CONFLICT", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:45.444691+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:45.447131+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "IDEMPOTENCY_CONFLICT", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:45.447974+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:45.450229+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:45.450872+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:45.451662+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:45.452290+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_2b72823402da40018e0993404ab0bca8
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_2b72823402da40018e0993404ab0bca8
.DISPOSABLE_DROPPED: researchbase_pr212_test_2b72823402da40018e0993404ab0bca8
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "1d9b4c14-0110-46da-80ca-c475995b901d", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 7.925, "error_code": null, "level": "INFO", "project_id": "13845815-3c59-4a28-9bb5-818635c72c5d", "request_id": "01b61170-84dc-43f6-8809-076ceaef3fcc", "result": "success", "rollback": false, "target_id": "13845815-3c59-4a28-9bb5-818635c72c5d", "timestamp": "2026-10-26T06:31:46.125601+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:46.127895+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 2.098, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:46.128018+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 2.208, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:46.128095+00:00"}
INFO  [researchbase.commands] {"actor_id": "1d9b4c14-0110-46da-80ca-c475995b901d", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 11.996, "error_code": null, "level": "INFO", "project_id": null, "request_id": "01b61170-84dc-43f6-8809-076ceaef3fcc", "result": "success", "rollback": false, "target_id": "01a176e8-6ccb-75b0-9fd3-366ff311c76f", "timestamp": "2026-10-26T06:31:46.140206+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:46.141390+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.075, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:46.141471+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.151, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-6cd6-78e4-b2bd-e65a6f2b2138", "timestamp": "2026-10-26T06:31:46.141526+00:00"}
INFO  [researchbase.commands] {"actor_id": "1d9b4c14-0110-46da-80ca-c475995b901d", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 5.703, "error_code": null, "level": "INFO", "project_id": null, "request_id": "01b61170-84dc-43f6-8809-076ceaef3fcc", "result": "success", "rollback": false, "target_id": "01a176e8-6cd6-78e4-b2bd-e65a6f2b2138", "timestamp": "2026-10-26T06:31:46.147308+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:46.148244+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.882, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:46.148314+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.948, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-6cd6-78e4-b2bd-e65a6f2b2138", "timestamp": "2026-10-26T06:31:46.148366+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "1d9b4c14-0110-46da-80ca-c475995b901d", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 2.868, "error_code": null, "level": "INFO", "project_id": "13845815-3c59-4a28-9bb5-818635c72c5d", "request_id": "acaa4a64-0aef-4d55-867a-d87c6dd3d8e4", "result": "success", "rollback": false, "target_id": "13845815-3c59-4a28-9bb5-818635c72c5d", "timestamp": "2026-10-26T06:31:46.288462+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:46.289462+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.911, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:46.289516+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.958, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:46.289551+00:00"}
INFO  [researchbase.commands] {"actor_id": "1d9b4c14-0110-46da-80ca-c475995b901d", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 8.578, "error_code": null, "level": "INFO", "project_id": null, "request_id": "acaa4a64-0aef-4d55-867a-d87c6dd3d8e4", "result": "success", "rollback": false, "target_id": "01a176e8-6d6f-7a6f-8d42-b9681529bc40", "timestamp": "2026-10-26T06:31:46.298177+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:46.298790+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.576, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:46.298833+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.613, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-6d75-7c2f-b85c-ae1c73dc01a1", "timestamp": "2026-10-26T06:31:46.298861+00:00"}
INFO  [researchbase.commands] {"actor_id": "1d9b4c14-0110-46da-80ca-c475995b901d", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 3.275, "error_code": null, "level": "INFO", "project_id": null, "request_id": "acaa4a64-0aef-4d55-867a-d87c6dd3d8e4", "result": "success", "rollback": false, "target_id": "01a176e8-6d75-7c2f-b85c-ae1c73dc01a1", "timestamp": "2026-10-26T06:31:46.302178+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:46.302796+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.584, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:46.302843+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.625, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-6d75-7c2f-b85c-ae1c73dc01a1", "timestamp": "2026-10-26T06:31:46.302876+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:46.308542+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:46.352187+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:46.362026+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:46.363210+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:46.364299+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "IDEMPOTENCY_CONFLICT", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:46.371057+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:46.373249+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "IDEMPOTENCY_CONFLICT", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:46.374031+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:46.376056+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:46.376638+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:46.377284+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:46.377861+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_84c67568eec64a9f86b059a42b5706f3
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_84c67568eec64a9f86b059a42b5706f3
.DISPOSABLE_DROPPED: researchbase_pr212_test_84c67568eec64a9f86b059a42b5706f3
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "b5f1be36-a88f-4176-b6c5-63d1d642c92d", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 7.146, "error_code": null, "level": "INFO", "project_id": "0aef1abe-d799-4c62-b7ed-c924de6ac95d", "request_id": "8e62df4d-c8ca-46cd-8f38-b9d5e5f0c19e", "result": "success", "rollback": false, "target_id": "0aef1abe-d799-4c62-b7ed-c924de6ac95d", "timestamp": "2026-10-26T06:31:47.139400+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:47.141899+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 2.282, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:47.142022+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 2.393, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:47.142100+00:00"}
INFO  [researchbase.commands] {"actor_id": "b5f1be36-a88f-4176-b6c5-63d1d642c92d", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 11.775, "error_code": null, "level": "INFO", "project_id": null, "request_id": "8e62df4d-c8ca-46cd-8f38-b9d5e5f0c19e", "result": "success", "rollback": false, "target_id": "01a176e8-70c1-701a-8a6f-e73619601f2a", "timestamp": "2026-10-26T06:31:47.153992+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:47.155233+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.192, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:47.155341+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.286, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-70cc-7674-98f1-36bbc4da8be4", "timestamp": "2026-10-26T06:31:47.155417+00:00"}
INFO  [researchbase.commands] {"actor_id": "b5f1be36-a88f-4176-b6c5-63d1d642c92d", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 6.354, "error_code": null, "level": "INFO", "project_id": null, "request_id": "8e62df4d-c8ca-46cd-8f38-b9d5e5f0c19e", "result": "success", "rollback": false, "target_id": "01a176e8-70cc-7674-98f1-36bbc4da8be4", "timestamp": "2026-10-26T06:31:47.161882+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:47.162843+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.906, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:47.162916+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.976, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-70cc-7674-98f1-36bbc4da8be4", "timestamp": "2026-10-26T06:31:47.162973+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "b5f1be36-a88f-4176-b6c5-63d1d642c92d", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 4.333, "error_code": null, "level": "INFO", "project_id": "0aef1abe-d799-4c62-b7ed-c924de6ac95d", "request_id": "de742a16-a83c-4ed4-8819-53cd286b6e9f", "result": "success", "rollback": false, "target_id": "0aef1abe-d799-4c62-b7ed-c924de6ac95d", "timestamp": "2026-10-26T06:31:47.358770+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:47.360670+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 1.731, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:47.360761+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.813, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:47.360818+00:00"}
INFO  [researchbase.commands] {"actor_id": "b5f1be36-a88f-4176-b6c5-63d1d642c92d", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 13.082, "error_code": null, "level": "INFO", "project_id": null, "request_id": "de742a16-a83c-4ed4-8819-53cd286b6e9f", "result": "success", "rollback": false, "target_id": "01a176e8-719d-779e-9ef2-a82899567495", "timestamp": "2026-10-26T06:31:47.373986+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:47.375340+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.255, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:47.375424+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.331, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-71a6-7452-8bee-ad98d1f1baad", "timestamp": "2026-10-26T06:31:47.375478+00:00"}
INFO  [researchbase.commands] {"actor_id": "b5f1be36-a88f-4176-b6c5-63d1d642c92d", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 5.704, "error_code": null, "level": "INFO", "project_id": null, "request_id": "de742a16-a83c-4ed4-8819-53cd286b6e9f", "result": "success", "rollback": false, "target_id": "01a176e8-71a6-7452-8bee-ad98d1f1baad", "timestamp": "2026-10-26T06:31:47.381263+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:47.382300+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.977, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:47.382371+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.042, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-71a6-7452-8bee-ad98d1f1baad", "timestamp": "2026-10-26T06:31:47.382422+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:47.390870+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:47.448483+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:47.450947+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_84e353e410254583b8e56eff2e18963c
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_84e353e410254583b8e56eff2e18963c
.DISPOSABLE_DROPPED: researchbase_pr212_test_84e353e410254583b8e56eff2e18963c
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.
INFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.
INFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.
INFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.
INFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.
INFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.
INFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.
INFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.
INFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.
INFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.
INFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.
INFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.
INFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.
INFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.
INFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.
INFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.
INFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.
INFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.
INFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.
INFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.
INFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.
INFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.
INFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.
INFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.
INFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.
INFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.
INFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.
INFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.
INFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.
INFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.
INFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.
INFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.
INFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.
INFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.
INFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.
INFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.
INFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.
INFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.
INFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.
INFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.
INFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.
INFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.
INFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.
INFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.
INFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.
INFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.
INFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.
INFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.
INFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.
INFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.
INFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.
INFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.
INFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.
INFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.
INFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.
INFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.
INFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.
INFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.
INFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.
INFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.
INFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.
INFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.
INFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.
INFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.
INFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.
INFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.
INFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.
INFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.
INFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.
INFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.
INFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.
INFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).
INFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.
INFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.
INFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.
INFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.
INFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.
INFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.
INFO  [researchbase.commands] {"actor_id": "93ee9969-be06-4e7b-bc0f-3767f5040f64", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 6.146, "error_code": null, "level": "INFO", "project_id": "a77f6ce1-4894-4be3-acac-79c6c701d631", "request_id": "8199c158-17b6-4d1a-835a-e21ebf6ddb5f", "result": "success", "rollback": false, "target_id": "a77f6ce1-4894-4be3-acac-79c6c701d631", "timestamp": "2026-10-26T06:31:48.113970+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:48.115686+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 1.573, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:48.115776+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.656, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:48.115836+00:00"}
INFO  [researchbase.commands] {"actor_id": "93ee9969-be06-4e7b-bc0f-3767f5040f64", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 11.817, "error_code": null, "level": "INFO", "project_id": null, "request_id": "8199c158-17b6-4d1a-835a-e21ebf6ddb5f", "result": "success", "rollback": false, "target_id": "01a176e8-7490-79cb-b1e8-21f947970a61", "timestamp": "2026-10-26T06:31:48.127737+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:48.128895+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 1.07, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:48.128977+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.149, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-7499-78e8-81da-913c4b70e52a", "timestamp": "2026-10-26T06:31:48.129038+00:00"}
INFO  [researchbase.commands] {"actor_id": "93ee9969-be06-4e7b-bc0f-3767f5040f64", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 6.051, "error_code": null, "level": "INFO", "project_id": null, "request_id": "8199c158-17b6-4d1a-835a-e21ebf6ddb5f", "result": "success", "rollback": false, "target_id": "01a176e8-7499-78e8-81da-913c4b70e52a", "timestamp": "2026-10-26T06:31:48.135174+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:48.136257+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.993, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:48.136342+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.068, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-7499-78e8-81da-913c4b70e52a", "timestamp": "2026-10-26T06:31:48.136398+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "93ee9969-be06-4e7b-bc0f-3767f5040f64", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 4.267, "error_code": null, "level": "INFO", "project_id": "a77f6ce1-4894-4be3-acac-79c6c701d631", "request_id": "09a07c6e-2699-400e-8991-473777f32671", "result": "success", "rollback": false, "target_id": "a77f6ce1-4894-4be3-acac-79c6c701d631", "timestamp": "2026-10-26T06:31:48.316733+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:48.318506+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 1.61, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:48.318584+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 1.684, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:48.318632+00:00"}
INFO  [researchbase.commands] {"actor_id": "93ee9969-be06-4e7b-bc0f-3767f5040f64", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 8.475, "error_code": null, "level": "INFO", "project_id": null, "request_id": "09a07c6e-2699-400e-8991-473777f32671", "result": "success", "rollback": false, "target_id": "01a176e8-755b-7797-8230-a272442a293b", "timestamp": "2026-10-26T06:31:48.327177+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:48.328133+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.914, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:48.328207+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.974, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-7563-77a3-b7a2-ca937ec567a8", "timestamp": "2026-10-26T06:31:48.328254+00:00"}
INFO  [researchbase.commands] {"actor_id": "93ee9969-be06-4e7b-bc0f-3767f5040f64", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 5.91, "error_code": null, "level": "INFO", "project_id": null, "request_id": "09a07c6e-2699-400e-8991-473777f32671", "result": "success", "rollback": false, "target_id": "01a176e8-7563-77a3-b7a2-ca937ec567a8", "timestamp": "2026-10-26T06:31:48.334229+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:48.335013+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.719, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-26T06:31:48.335068+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.772, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a176e8-7563-77a3-b7a2-ca937ec567a8", "timestamp": "2026-10-26T06:31:48.335108+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:48.342094+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:48.386694+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:48.421035+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-26T06:31:48.423530+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_8fba8de350294d18bb1b17e6411e5bf4
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_8fba8de350294d18bb1b17e6411e5bf4
.DISPOSABLE_DROPPED: researchbase_pr212_test_8fba8de350294d18bb1b17e6411e5bf4


=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py: 23 warnings
tests/integration/phase3/test_pr3_02_s2_intent_replay.py: 24 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 23 passed, 47 warnings in 27.88s =======================
```

Exit code: **0**.

### S7-REG3

```sh
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_01_*.py tests/integration/phase3/test_pr3_02_s1_*.py tests/integration/phase3/test_pr3_03_*.py tests/integration/phase3/test_pr3_04_*.py
```

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 561 items

tests/integration/phase3/test_pr3_01_application.py .......              [  1%]
tests/integration/phase3/test_pr3_01_concurrency.py ................     [  4%]
tests/integration/phase3/test_pr3_01_migration.py ...                    [  4%]
tests/integration/phase3/test_pr3_01_replay.py ...............           [  7%]
tests/integration/phase3/test_pr3_01_schema.py ......................... [ 11%]
........................................................................ [ 24%]
..................................                                       [ 30%]
tests/integration/phase3/test_pr3_02_s1_application.py ..............    [ 33%]
tests/integration/phase3/test_pr3_02_s1_b02_agent.py .                   [ 33%]
tests/integration/phase3/test_pr3_02_s1_concurrency.py .......           [ 34%]
tests/integration/phase3/test_pr3_02_s1_identity.py ...................  [ 37%]
tests/integration/phase3/test_pr3_02_s1_migration.py ...                 [ 38%]
tests/integration/phase3/test_pr3_02_s1_replay.py ..........             [ 40%]
tests/integration/phase3/test_pr3_02_s1_schema.py .....................  [ 44%]
tests/integration/phase3/test_pr3_03_application.py .................... [ 47%]
...........................................                              [ 55%]
tests/integration/phase3/test_pr3_03_concurrency.py .................... [ 58%]
...                                                                      [ 59%]
tests/integration/phase3/test_pr3_03_guards.py ......................... [ 63%]
.....................                                                    [ 67%]
tests/integration/phase3/test_pr3_03_input_versions.py ....              [ 68%]
tests/integration/phase3/test_pr3_03_migration.py ...                    [ 68%]
tests/integration/phase3/test_pr3_03_replay.py ......................... [ 73%]
................................................                         [ 81%]
tests/integration/phase3/test_pr3_03_schema.py ......................... [ 86%]
.....                                                                    [ 87%]
tests/integration/phase3/test_pr3_04_accounting.py ...........           [ 89%]
tests/integration/phase3/test_pr3_04_application.py .................... [ 92%]
..                                                                       [ 93%]
tests/integration/phase3/test_pr3_04_concurrency.py .......              [ 94%]
tests/integration/phase3/test_pr3_04_fake_consumer.py ..                 [ 94%]
tests/integration/phase3/test_pr3_04_guards.py ..................        [ 97%]
tests/integration/phase3/test_pr3_04_migration.py ..                     [ 98%]
tests/integration/phase3/test_pr3_04_queries.py ..                       [ 98%]
tests/integration/phase3/test_pr3_04_replay.py ....                      [ 99%]
tests/integration/phase3/test_pr3_04_schema.py ....                      [100%]

=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_01_application.py: 2 warnings
tests/integration/phase3/test_pr3_01_migration.py: 11 warnings
tests/integration/phase3/test_pr3_02_s1_application.py: 14 warnings
tests/integration/phase3/test_pr3_02_s1_b02_agent.py: 1 warning
tests/integration/phase3/test_pr3_02_s1_concurrency.py: 7 warnings
tests/integration/phase3/test_pr3_02_s1_identity.py: 19 warnings
tests/integration/phase3/test_pr3_02_s1_migration.py: 8 warnings
tests/integration/phase3/test_pr3_02_s1_replay.py: 10 warnings
tests/integration/phase3/test_pr3_02_s1_schema.py: 21 warnings
tests/integration/phase3/test_pr3_03_application.py: 126 warnings
tests/integration/phase3/test_pr3_03_concurrency.py: 46 warnings
tests/integration/phase3/test_pr3_03_guards.py: 92 warnings
tests/integration/phase3/test_pr3_03_migration.py: 8 warnings
tests/integration/phase3/test_pr3_03_replay.py: 146 warnings
tests/integration/phase3/test_pr3_03_schema.py: 28 warnings
tests/integration/phase3/test_pr3_04_migration.py: 9 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================ 561 passed, 548 warnings in 483.09s (0:08:03) =================
```

Exit code: **0**.

### S7-REG2

```sh
uv run pytest -o addopts='' -ra tests/integration/phase2/test_b02_*.py tests/integration/phase2/test_b03_*.py
```

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 155 items

tests/integration/phase2/test_b02_identity_boundary.py ........          [  5%]
tests/integration/phase2/test_b02_strategy_admission.py .............    [ 13%]
tests/integration/phase2/test_b02_strategy_capture.py .........          [ 19%]
tests/integration/phase2/test_b02_strategy_concurrency.py .............. [ 28%]
.................                                                        [ 39%]
tests/integration/phase2/test_b02_strategy_replay.py ................    [ 49%]
tests/integration/phase2/test_b02_strategy_schema.py ................... [ 61%]
......                                                                   [ 65%]
tests/integration/phase2/test_b03_discussion_hypothesis.py ............. [ 74%]
...................                                                      [ 86%]
tests/integration/phase2/test_b03_discussion_hypothesis_guards.py ...... [ 90%]
...............                                                          [100%]

=============================== warnings summary ===============================
tests/integration/phase2/test_b02_identity_boundary.py: 8 warnings
tests/integration/phase2/test_b02_strategy_admission.py: 26 warnings
tests/integration/phase2/test_b02_strategy_capture.py: 18 warnings
tests/integration/phase2/test_b02_strategy_concurrency.py: 62 warnings
tests/integration/phase2/test_b02_strategy_replay.py: 31 warnings
tests/integration/phase2/test_b02_strategy_schema.py: 53 warnings
tests/integration/phase2/test_b03_discussion_hypothesis.py: 98 warnings
tests/integration/phase2/test_b03_discussion_hypothesis_guards.py: 64 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================ 155 passed, 360 warnings in 157.97s (0:02:37) =================
```

Exit code: **0**.

### S7-PREVIEW

```sh
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_05_promotion_validation.py
```

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 2 items

tests/integration/phase3/test_pr3_05_promotion_validation.py ..          [100%]

=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_05_promotion_validation.py::test_candidate_basis_revision_gates_and_missing_s2[RESEARCH_QUESTION_VERSION]
tests/integration/phase3/test_pr3_05_promotion_validation.py::test_candidate_basis_revision_gates_and_missing_s2[RESEARCH_QUESTION_VERSION]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 2 passed, 2 warnings in 1.25s =========================
```

Exit code: **0**.

### COLLECT-NODES

```sh
uv run pytest -o addopts='' --collect-only -q tests/integration/phase3/test_pr3_02_s2_intent_*.py tests/unit/phase3/test_agent_execution_repository.py
```

```text
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_observed_wait_rechecks_intent_authority[first_share]
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_observed_wait_rechecks_intent_authority[second_key]
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_observed_wait_rechecks_intent_authority[task_row]
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_observed_wait_rechecks_intent_authority[version_row]
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_same_command_revision_and_existing_writer_races
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_membership_revocation_during_first_share_wait[membership]
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_membership_revocation_during_first_share_wait[credential]
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_availability_change_at_existing_s1_writer_wait
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_unchanged_task_writer_coexistence
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_unchanged_phase2_writer_coexistence
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_unchanged_gateway_writer_coexistence
tests/integration/phase3/test_pr3_02_s2_intent_database_errors.py::test_real_postgresql_failure_normalizes_intent_retryability[40001]
tests/integration/phase3/test_pr3_02_s2_intent_database_errors.py::test_real_postgresql_failure_normalizes_intent_retryability[40P01]
tests/integration/phase3/test_pr3_02_s2_intent_database_errors.py::test_real_postgresql_failure_normalizes_intent_retryability[55P03]
tests/integration/phase3/test_pr3_02_s2_intent_database_errors.py::test_real_postgresql_failure_normalizes_intent_retryability[57014]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_created_intent_through_common_application_boundary
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_researcher_and_exact_agent_use_common_boundary[human_researcher]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_researcher_and_exact_agent_use_common_boundary[agent]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_denials_preserve_closed_execution_gate[stale-CONCURRENT_MODIFICATION]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_denials_preserve_closed_execution_gate[unsealed-INVALID_STATE_TRANSITION]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_denials_preserve_closed_execution_gate[unavailable-INVALID_STATE_TRANSITION]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_denials_preserve_closed_execution_gate[viewer-FORBIDDEN]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_denials_preserve_closed_execution_gate[other_agent-FORBIDDEN]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_denials_preserve_closed_execution_gate[untrusted-AUTHENTICATION_REQUIRED]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_denials_preserve_closed_execution_gate[pins-FROZEN_REFERENCE_REQUIRED]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_denials_preserve_closed_execution_gate[bytes-PROVENANCE_CLOSURE_VIOLATION]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_denials_preserve_closed_execution_gate[scope-FORBIDDEN]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_denials_preserve_closed_execution_gate[unfrozen-VERSION_NOT_FROZEN]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_failure_rolls_back_all_three_effects[agent_command_receipts]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_failure_rolls_back_all_three_effects[agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_failure_rolls_back_all_three_effects[agent_execution_events]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_failure_rolls_back_all_three_effects[constraints]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_failure_rolls_back_all_three_effects[credentials]
tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_selected_step_and_typed_inputs_preserve_both_owners
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[insertion_researcher-provision_project_agent]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[insertion_researcher-register_agent_version]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[insertion_researcher-change_agent_availability]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[final_owner_removed-provision_project_agent]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[final_owner_removed-register_agent_version]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[final_owner_removed-change_agent_availability]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-INSERT-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-INSERT-agent_execution_events]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-UPDATE-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-UPDATE-agent_execution_events]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-DELETE-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-DELETE-agent_execution_events]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-TRUNCATE-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-TRUNCATE-agent_execution_events]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-INSERT-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-INSERT-agent_execution_events]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-UPDATE-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-UPDATE-agent_execution_events]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-DELETE-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-DELETE-agent_execution_events]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-TRUNCATE-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-TRUNCATE-agent_execution_events]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[prefix-pr302s2_preheld]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[isolation-pr302s2_preheld]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[advisory-pr302s2_preheld]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[missing_receipt-pr302s2_completeness]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[actor-pr302s2_scope]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[state-pr302s2_state]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[cas-pr302s2_cas]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[binding-pr302s2_binding]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[not_frozen-pr302s2_not_frozen]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[hash-pr302s2_provenance]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[event-pr302s2_completeness]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[partial-pr302s2_completeness]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[request_hash-pr302s2_provenance]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_owning_role_immutable_including_noop[UPDATE-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_owning_role_immutable_including_noop[UPDATE-agent_execution_events]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_owning_role_immutable_including_noop[DELETE-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_owning_role_immutable_including_noop[DELETE-agent_execution_events]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_python_postgresql_intent_material_parity
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_historical_receipt_cannot_attach_new_history[agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_historical_receipt_cannot_attach_new_history[agent_execution_events]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_unresolved_input_material_diagnostic
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_exact_intent_schema_and_scoped_foreign_keys
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_literal_checks_indexes_and_receipt_deferral
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_operation_check]
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_check]
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_empty_upgrade_and_single_head
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_populated_upgrade_preserves_history
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_downgrade_refuses_before_change[False]
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_downgrade_refuses_before_change[True]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[unavailable]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[mismatch]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_receipt_committed_during_failed_byte_preflight_is_replayed
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_intent_after_loss_and_uncertain_commit
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_current_entitlement_precedes_intent_disclosure[expected_task_revision]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_current_entitlement_precedes_intent_disclosure[harness_artifact_version_id]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_current_entitlement_precedes_intent_disclosure[agent_version_id]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_current_entitlement_precedes_intent_disclosure[research_task_step_id]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_current_entitlement_precedes_intent_disclosure[execution_id]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_current_entitlement_precedes_intent_disclosure[research_task_id]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_other_caller_cannot_replay_receipt
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_queries_are_coherent_bounded_snapshots
tests/unit/phase3/test_agent_execution_repository.py::test_fresh_checks_after_each_wait
tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot[replay]
tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot[get]
tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot[list]
tests/unit/phase3/test_agent_execution_repository.py::test_ordered_intent_prefix_and_keys
tests/unit/phase3/test_agent_execution_repository.py::test_intent_diagnostics_are_translated_by_exact_state_and_tag
tests/unit/phase3/test_agent_execution_repository.py::test_bounded_whole_transaction_retry_and_no_timeout_retry[40001-3]
tests/unit/phase3/test_agent_execution_repository.py::test_bounded_whole_transaction_retry_and_no_timeout_retry[40P01-3]
tests/unit/phase3/test_agent_execution_repository.py::test_bounded_whole_transaction_retry_and_no_timeout_retry[55P03-1]
tests/unit/phase3/test_agent_execution_repository.py::test_bounded_whole_transaction_retry_and_no_timeout_retry[57014-1]

107 tests collected in 0.04s
```

Exit code: **0**.

### TREE-AFTER

```sh
python3 tmp/b4_fingerprint.py
```

```text
HEAD dff29d3792c96c183a3ffbb5569ed72ac41c179c
tracked tree SHA-256 (excluding evidence): a8af916a2f0563a22a56d1c7927a97642eb97ec34cbaca19add34f33926d7811
905c4726fe48c2ba9cf17f4fdcb65c07044a59793d7f7dc2f9dc35cca22f6c3d tests/integration/phase3/test_pr3_02_s2_intent_guards.py
9b3103b6ba1fc32a4d8311dd6a2e556a7f41a12fdccf79113de23dc98a990c0c tests/integration/phase3/test_pr3_02_s2_intent_migration.py
142c7a9061785a971d7043667041cf5368be24e38069c59900640d13c2259e52 migrations/versions/0081_agent_execution_intents.py
ce8f06d923256872c6438e1f40308bb647d5c167e070eb875bd980a841692ca9 docs/phase3/PR3-02-S2-contract-freeze.md
9f08950b95fa7fefb3c233cccb97a56ba2baceb1c0bc8e1aea87d25726b235a0 pyproject.toml
e7155e4cbfe7f43157cba3f1c6fc0e7961f466d58810b09024f34487078b3ba6 uv.lock
Protected files unchanged from HEAD
git status --short:
 M docs/phase3/PR3-02-S2-intent-evidence.md
 M tests/integration/phase3/test_pr3_02_s2_intent_guards.py
 M tests/integration/phase3/test_pr3_02_s2_intent_migration.py
```

Exit code: **0**.

### PRE-ANNOTATION-TYPE

```sh
uv run pyright
```

```text
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tests/integration/phase3/test_pr3_02_s2_intent_guards.py
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:68:12 - error: Argument of type "UUID" cannot be assigned to parameter "id" of type "None" in function "update"
    "UUID" is not assignable to "None" (reportArgumentType)
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:70:25 - error: Argument of type "UUID | Unknown" cannot be assigned to parameter "caller_actor_id" of type "None" in function "update"
    Type "UUID | Unknown" is not assignable to type "None"
      "UUID" is not assignable to "None" (reportArgumentType)
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:72:19 - error: Argument of type "Unknown | Literal['provision_project_agent', 'change_agent_availability']" cannot be assigned to parameter "operation" of type "None" in function "update"
    Type "Unknown | Literal['provision_project_agent', 'change_agent_availability']" is not assignable to type "None"
      "Literal['change_agent_availability']" is not assignable to "None" (reportArgumentType)
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:74:21 - error: Argument of type "Literal['sha256-cjson-v1']" cannot be assigned to parameter "hash_scheme" of type "None" in function "update"
    "Literal['sha256-cjson-v1']" is not assignable to "None" (reportArgumentType)
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:75:28 - error: Argument of type "Literal[2, 1]" cannot be assigned to parameter "resulting_revision" of type "None" in function "update"
    Type "Literal[2, 1]" is not assignable to type "None"
      "Literal[1]" is not assignable to "None" (reportArgumentType)
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:76:11 - error: Argument of type "UUID" cannot be assigned to parameter "kwargs" of type "None" in function "update"
    "UUID" is not assignable to "None" (reportArgumentType)
6 errors, 0 warnings, 0 informations
WARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`

```

Exit code: **1**.

## Removed/restored mutation output

### M-L2

Copy-only target: `src/researchbase/persistence/agent_execution_repository.py`. Replace the first matching block below (L3 is scoped to `begin_formal_read`), then restore the original bytes.

```text
        self._session.execute(text(INTENT_SHARE_SQL))
        after_wait()
```

Replacement:

```text
        self._session.execute(text(INTENT_SHARE_SQL))
```

**removed** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-hxu5xekz`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-hxu5xekz/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-hxu5xekz`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=line --show-capture=no tests/unit/phase3/test_agent_execution_repository.py::test_fresh_checks_after_each_wait
```

```text
F                                                                        [100%]
=================================== FAILURES ===================================
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-hxu5xekz/tests/unit/phase3/test_agent_execution_repository.py:235: AssertionError: [('wait', 'LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis...egy_hypothesis_admissions, strategy_question_admissions IN SHARE MODE'), ('sql', 'SELECT rb_phase2_lock_project(:id)')]
=========================== short test summary info ============================
FAILED tests/unit/phase3/test_agent_execution_repository.py::test_fresh_checks_after_each_wait
1 failed in 0.60s
```

Exit code: **1**.

**restored** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-hxu5xekz`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-hxu5xekz/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-hxu5xekz`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=line --show-capture=no tests/unit/phase3/test_agent_execution_repository.py::test_fresh_checks_after_each_wait
```

```text
.                                                                        [100%]
1 passed in 0.60s
```

Exit code: **0**.

### M-L3

Copy-only target: `src/researchbase/persistence/uow.py`. Replace the first matching block below (L3 is scoped to `begin_formal_read`), then restore the original bytes.

```text
"postgresql_readonly": True,
```

Replacement:

```text
"postgresql_readonly": False,
```

**removed** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-j_hi5nml`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-j_hi5nml/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-j_hi5nml`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=short --show-capture=no tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot
```

```text
FFF                                                                      [100%]
=================================== FAILURES ===================================
______________ test_formal_read_has_one_readonly_snapshot[replay] ______________
tests/unit/phase3/test_agent_execution_repository.py:285: in test_formal_read_has_one_readonly_snapshot
    session.connection.assert_called_once_with(
/Users/fengwang/.local/share/uv/python/cpython-3.12.15-macos-aarch64-none/lib/python3.12/unittest/mock.py:961: in assert_called_once_with
    return self.assert_called_with(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/Users/fengwang/.local/share/uv/python/cpython-3.12.15-macos-aarch64-none/lib/python3.12/unittest/mock.py:949: in assert_called_with
    raise AssertionError(_error_message()) from cause
E   AssertionError: expected call not found.
E   Expected: connection(execution_options={'isolation_level': 'REPEATABLE READ', 'postgresql_readonly': True})
E     Actual: connection(execution_options={'isolation_level': 'REPEATABLE READ', 'postgresql_readonly': False})
_______________ test_formal_read_has_one_readonly_snapshot[get] ________________
tests/unit/phase3/test_agent_execution_repository.py:285: in test_formal_read_has_one_readonly_snapshot
    session.connection.assert_called_once_with(
/Users/fengwang/.local/share/uv/python/cpython-3.12.15-macos-aarch64-none/lib/python3.12/unittest/mock.py:961: in assert_called_once_with
    return self.assert_called_with(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/Users/fengwang/.local/share/uv/python/cpython-3.12.15-macos-aarch64-none/lib/python3.12/unittest/mock.py:949: in assert_called_with
    raise AssertionError(_error_message()) from cause
E   AssertionError: expected call not found.
E   Expected: connection(execution_options={'isolation_level': 'REPEATABLE READ', 'postgresql_readonly': True})
E     Actual: connection(execution_options={'isolation_level': 'REPEATABLE READ', 'postgresql_readonly': False})
_______________ test_formal_read_has_one_readonly_snapshot[list] _______________
tests/unit/phase3/test_agent_execution_repository.py:285: in test_formal_read_has_one_readonly_snapshot
    session.connection.assert_called_once_with(
/Users/fengwang/.local/share/uv/python/cpython-3.12.15-macos-aarch64-none/lib/python3.12/unittest/mock.py:961: in assert_called_once_with
    return self.assert_called_with(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/Users/fengwang/.local/share/uv/python/cpython-3.12.15-macos-aarch64-none/lib/python3.12/unittest/mock.py:949: in assert_called_with
    raise AssertionError(_error_message()) from cause
E   AssertionError: expected call not found.
E   Expected: connection(execution_options={'isolation_level': 'REPEATABLE READ', 'postgresql_readonly': True})
E     Actual: connection(execution_options={'isolation_level': 'REPEATABLE READ', 'postgresql_readonly': False})
=========================== short test summary info ============================
FAILED tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot[replay]
FAILED tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot[get]
FAILED tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot[list]
3 failed in 0.71s
```

Exit code: **1**.

**restored** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-j_hi5nml`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-j_hi5nml/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-j_hi5nml`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=short --show-capture=no tests/unit/phase3/test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot
```

```text
...                                                                      [100%]
3 passed in 0.65s
```

Exit code: **0**.

### M-DRIFT

Copy-only target: `migrations/versions/0081_agent_execution_intents.py`. Replace the first matching block below (L3 is scoped to `begin_formal_read`), then restore the original bytes.

```text
    if actual != BASELINE_CHECKS:
        raise RuntimeError("S2 receipt CHECK catalog drift; forward migration refused")
```

Replacement:

```text
    # Mutation: no baseline CHECK comparison.
```

**removed** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-9klxrvwf`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-9klxrvwf/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-9klxrvwf`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=short --show-capture=no tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift
```

```text
FF                                                                       [100%]
=================================== FAILURES ===================================
_ test_upgrade_refuses_receipt_check_drift[agent_command_receipts_operation_check] _
tests/integration/phase3/test_pr3_02_s2_intent_migration.py:120: in test_upgrade_refuses_receipt_check_drift
    with pytest.raises(
E   Failed: DID NOT RAISE <class 'RuntimeError'>
____ test_upgrade_refuses_receipt_check_drift[agent_command_receipts_check] ____
tests/integration/phase3/test_pr3_02_s2_intent_migration.py:120: in test_upgrade_refuses_receipt_check_drift
    with pytest.raises(
E   Failed: DID NOT RAISE <class 'RuntimeError'>
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_operation_check]
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_operation_check]
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_check]
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_check]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_operation_check]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_check]
2 failed, 4 warnings in 1.61s
```

Exit code: **1**.

**restored** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-9klxrvwf`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-9klxrvwf/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-9klxrvwf`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=short --show-capture=no tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift
```

```text
..                                                                       [100%]
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_operation_check]
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_operation_check]
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_check]
tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift[agent_command_receipts_check]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2 passed, 4 warnings in 1.77s
```

Exit code: **0**.

### M-REVOKE-PUBLIC

Copy-only target: `migrations/versions/0081_agent_execution_intents.py`. Replace the first matching block below (L3 is scoped to `begin_formal_read`), then restore the original bytes.

```text
REVOKE INSERT,UPDATE,DELETE,TRUNCATE ON agent_execution_instances,agent_execution_events FROM PUBLIC;
```

Replacement:

```text
-- Mutation: PUBLIC revoke removed.
```

**removed** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-qmfc0qbn`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-qmfc0qbn/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-qmfc0qbn`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=line --show-capture=no tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables -k PUBLIC
```

```text
FFFFFFFF                                                                 [100%]
=================================== FAILURES ===================================
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-qmfc0qbn/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:228: AssertionError: assert '23514' == '42501'
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-qmfc0qbn/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:228: AssertionError: assert '23514' == '42501'
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-qmfc0qbn/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:221: Failed: DID NOT RAISE <class 'sqlalchemy.exc.DBAPIError'>
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-qmfc0qbn/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:221: Failed: DID NOT RAISE <class 'sqlalchemy.exc.DBAPIError'>
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-qmfc0qbn/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:221: Failed: DID NOT RAISE <class 'sqlalchemy.exc.DBAPIError'>
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-qmfc0qbn/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:221: Failed: DID NOT RAISE <class 'sqlalchemy.exc.DBAPIError'>
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-qmfc0qbn/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:228: AssertionError: assert '0A000' == '42501'
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-qmfc0qbn/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:228: AssertionError: assert '0A000' == '42501'
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-INSERT-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-INSERT-agent_execution_instances]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-INSERT-agent_execution_instances]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-INSERT-agent_execution_events]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-UPDATE-agent_execution_instances]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-UPDATE-agent_execution_events]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-DELETE-agent_execution_instances]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-DELETE-agent_execution_events]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-TRUNCATE-agent_execution_instances]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-TRUNCATE-agent_execution_events]
8 failed, 8 deselected, 2 warnings in 1.01s
```

Exit code: **1**.

**restored** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-qmfc0qbn`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-qmfc0qbn/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-qmfc0qbn`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=line --show-capture=no tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables -k PUBLIC
```

```text
........                                                                 [100%]
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-INSERT-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[PUBLIC-INSERT-agent_execution_instances]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
8 passed, 8 deselected, 2 warnings in 0.95s
```

Exit code: **0**.

### M-REVOKE-ROLE

Copy-only target: `migrations/versions/0081_agent_execution_intents.py`. Replace the first matching block below (L3 is scoped to `begin_formal_read`), then restore the original bytes.

```text
        op.execute(
            f"REVOKE INSERT,UPDATE,DELETE,TRUNCATE ON agent_execution_instances,agent_execution_events FROM {quoted}"
        )
```

Replacement:

```text
        pass  # Mutation: explicit-role revoke removed.
```

**removed** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-5ms_z3vl`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-5ms_z3vl/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-5ms_z3vl`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=line --show-capture=no tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables -k normal_role-
```

```text
FFFFFFFF                                                                 [100%]
=================================== FAILURES ===================================
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-5ms_z3vl/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:228: AssertionError: assert '23514' == '42501'
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-5ms_z3vl/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:228: AssertionError: assert '23514' == '42501'
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-5ms_z3vl/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:221: Failed: DID NOT RAISE <class 'sqlalchemy.exc.DBAPIError'>
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-5ms_z3vl/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:221: Failed: DID NOT RAISE <class 'sqlalchemy.exc.DBAPIError'>
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-5ms_z3vl/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:221: Failed: DID NOT RAISE <class 'sqlalchemy.exc.DBAPIError'>
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-5ms_z3vl/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:221: Failed: DID NOT RAISE <class 'sqlalchemy.exc.DBAPIError'>
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-5ms_z3vl/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:228: AssertionError: assert '0A000' == '42501'
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-5ms_z3vl/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:228: AssertionError: assert '0A000' == '42501'
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-INSERT-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-INSERT-agent_execution_instances]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-INSERT-agent_execution_instances]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-INSERT-agent_execution_events]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-UPDATE-agent_execution_instances]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-UPDATE-agent_execution_events]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-DELETE-agent_execution_instances]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-DELETE-agent_execution_events]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-TRUNCATE-agent_execution_instances]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-TRUNCATE-agent_execution_events]
8 failed, 8 deselected, 2 warnings in 0.97s
```

Exit code: **1**.

**restored** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-5ms_z3vl`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-5ms_z3vl/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-5ms_z3vl`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=line --show-capture=no tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables -k normal_role-
```

```text
........                                                                 [100%]
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-INSERT-agent_execution_instances]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[normal_role-INSERT-agent_execution_instances]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
8 passed, 8 deselected, 2 warnings in 0.99s
```

Exit code: **0**.

### M-SHARE

Copy-only target: `migrations/versions/0081_agent_execution_intents.py`. Replace the first matching block below (L3 is scoped to `begin_formal_read`), then restore the original bytes.

```text
 IF NOT EXISTS(SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() AND locktype='relation' AND granted
 AND relation=to_regclass('public.'||relation_name) AND mode IN ('ShareLock','ShareRowExclusiveLock','ExclusiveLock','AccessExclusiveLock')) THEN
 RAISE EXCEPTION 'intent SHARE protection absent' USING ERRCODE='23514',CONSTRAINT='pr302s2_preheld'; END IF;
```

Replacement:

```text
 PERFORM 1; -- Mutation: SHARE guard removed.
```

**removed** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-08v3xvgv`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-08v3xvgv/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-08v3xvgv`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=line --show-capture=no 'tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[prefix-pr302s2_preheld]'
```

```text
F                                                                        [100%]
=================================== FAILURES ===================================
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-08v3xvgv/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:348: AssertionError: assert 'intent comma...ection absent' == 'intent SHARE...ection absent'
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[prefix-pr302s2_preheld]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[prefix-pr302s2_preheld]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[prefix-pr302s2_preheld]
1 failed, 2 warnings in 0.98s
```

Exit code: **1**.

**restored** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-08v3xvgv`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-08v3xvgv/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-08v3xvgv`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=line --show-capture=no 'tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[prefix-pr302s2_preheld]'
```

```text
.                                                                        [100%]
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[prefix-pr302s2_preheld]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[prefix-pr302s2_preheld]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1 passed, 2 warnings in 1.06s
```

Exit code: **0**.

### M-CAS

Copy-only target: `migrations/versions/0081_agent_execution_intents.py`. Replace the first matching block below (L3 is scoped to `begin_formal_read`), then restore the original bytes.

```text
 IF task.row_version<>x.task_revision_at_creation THEN RAISE EXCEPTION 'task revision' USING ERRCODE='23514',CONSTRAINT='pr302s2_cas'; END IF;
```

Replacement:

```text
 -- Mutation: insertion CAS guard removed.
```

**removed** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-way39nd3`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-way39nd3/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-way39nd3`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=short --show-capture=no 'tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[cas-pr302s2_cas]'
```

```text
F                                                                        [100%]
=================================== FAILURES ===================================
___________ test_named_insertion_and_receipt_guards[cas-pr302s2_cas] ___________
tests/integration/phase3/test_pr3_02_s2_intent_guards.py:349: in test_named_insertion_and_receipt_guards
    assert re.search(
E   AssertionError: PL/pgSQL function pr302_receipt_complete() line 52 at RAISE
E   assert None
E    +  where None = <function search at 0x10658eca0>('^PL/pgSQL function pr302s2_execution_guard\\(\\) line \\d+ at RAISE$', ('PL/pgSQL function pr302_receipt_complete() line 52 at RAISE'), re.MULTILINE)
E    +    where <function search at 0x10658eca0> = re.search
E    +    and   'PL/pgSQL function pr302_receipt_complete() line 52 at RAISE' = <psycopg.errors.Diagnostic object at 0x10b99db20>.context
E    +    and   re.MULTILINE = re.MULTILINE
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[cas-pr302s2_cas]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[cas-pr302s2_cas]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[cas-pr302s2_cas]
1 failed, 2 warnings in 0.99s
```

Exit code: **1**.

**restored** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-way39nd3`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-way39nd3/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-way39nd3`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=short --show-capture=no 'tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[cas-pr302s2_cas]'
```

```text
.                                                                        [100%]
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[cas-pr302s2_cas]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[cas-pr302s2_cas]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1 passed, 2 warnings in 1.04s
```

Exit code: **0**.

### M-ISOLATION

Copy-only target: `migrations/versions/0081_agent_execution_intents.py`. Replace the first matching block below (L3 is scoped to `begin_formal_read`), then restore the original bytes.

```text
 IF current_setting('transaction_isolation')<>'read committed' THEN
 RAISE EXCEPTION 'intent isolation' USING ERRCODE='23514',CONSTRAINT='pr302s2_preheld'; END IF;
```

Replacement:

```text
 -- Mutation: isolation guard removed.
```

**removed** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-onbewsq5`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-onbewsq5/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-onbewsq5`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=short --show-capture=no 'tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[isolation-pr302s2_preheld]'
```

```text
F                                                                        [100%]
=================================== FAILURES ===================================
______ test_named_insertion_and_receipt_guards[isolation-pr302s2_preheld] ______
tests/integration/phase3/test_pr3_02_s2_intent_guards.py:294: in test_named_insertion_and_receipt_guards
    with pytest.raises(DBAPIError) as exc, Session(env.owning_engine) as session, session.begin():
         ^^^^^^^^^^^^^^^^^^^^^^^^^
E   Failed: DID NOT RAISE <class 'sqlalchemy.exc.DBAPIError'>
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[isolation-pr302s2_preheld]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[isolation-pr302s2_preheld]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[isolation-pr302s2_preheld]
1 failed, 2 warnings in 1.09s
```

Exit code: **1**.

**restored** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-onbewsq5`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-onbewsq5/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-onbewsq5`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=short --show-capture=no 'tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[isolation-pr302s2_preheld]'
```

```text
.                                                                        [100%]
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[isolation-pr302s2_preheld]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards[isolation-pr302s2_preheld]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1 passed, 2 warnings in 1.08s
```

Exit code: **0**.

### M-REPLAY-PREFLIGHT

Copy-only target: `src/researchbase/agent_runtime/application/agent_executions.py`. Replace the first matching block below (L3 is scoped to `begin_formal_read`), then restore the original bytes.

```text
            saved = repo.receipt(command)
            if saved:
                return None
```

Replacement:

```text
            # Mutation: do not short-circuit saved receipt before bytes.
```

**removed** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-7wpfe8at`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-7wpfe8at/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-7wpfe8at`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=short --show-capture=no tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure
```

```text
FF                                                                       [100%]
=================================== FAILURES ===================================
________ test_saved_replay_precedes_retained_byte_failure[unavailable] _________
tests/integration/phase3/test_pr3_02_s2_intent_replay.py:33: in test_saved_replay_precedes_retained_byte_failure
    broken_open.assert_not_called()
/Users/fengwang/.local/share/uv/python/cpython-3.12.15-macos-aarch64-none/lib/python3.12/unittest/mock.py:910: in assert_not_called
    raise AssertionError(msg)
E   AssertionError: Expected 'mock' to not have been called. Called 1 times.
E   Calls: [call('sha256:28bf151822a35cc3d78e0c14d45fbba5c5f87017e5e9f92ded57821b7544f363')].
__________ test_saved_replay_precedes_retained_byte_failure[mismatch] __________
tests/integration/phase3/test_pr3_02_s2_intent_replay.py:33: in test_saved_replay_precedes_retained_byte_failure
    broken_open.assert_not_called()
/Users/fengwang/.local/share/uv/python/cpython-3.12.15-macos-aarch64-none/lib/python3.12/unittest/mock.py:910: in assert_not_called
    raise AssertionError(msg)
E   AssertionError: Expected 'mock' to not have been called. Called 1 times.
E   Calls: [call('sha256:28bf151822a35cc3d78e0c14d45fbba5c5f87017e5e9f92ded57821b7544f363')].
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[unavailable]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[unavailable]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[mismatch]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[mismatch]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[unavailable]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[mismatch]
2 failed, 4 warnings in 1.94s
```

Exit code: **1**.

**restored** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-7wpfe8at`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-7wpfe8at/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-7wpfe8at`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=short --show-capture=no tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure
```

```text
..                                                                       [100%]
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[unavailable]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[unavailable]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[mismatch]
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_replay_precedes_retained_byte_failure[mismatch]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2 passed, 4 warnings in 2.17s
```

Exit code: **0**.

### M-REPLAY-WRITE

Copy-only target: `src/researchbase/agent_runtime/application/agent_executions.py`. Replace the first matching block below (L3 is scoped to `begin_formal_read`), then restore the original bytes.

```text
            saved = self._saved(repo, command)
            if saved is not None:
                return saved
            if preflight_error is not None:
                raise preflight_error
```

Replacement:

```text
            if preflight_error is not None:
                raise preflight_error
            saved = self._saved(repo, command)
            if saved is not None:
                return saved
```

**removed** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-v90_9ti_`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-v90_9ti_/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-v90_9ti_`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=short --show-capture=no tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_receipt_committed_during_failed_byte_preflight_is_replayed
```

```text
F                                                                        [100%]
=================================== FAILURES ===================================
_______ test_receipt_committed_during_failed_byte_preflight_is_replayed ________
tests/integration/phase3/test_pr3_02_s2_intent_replay.py:66: in test_receipt_committed_during_failed_byte_preflight_is_replayed
    result = env.intents.execute(env.intent)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src/researchbase/agent_runtime/application/agent_executions.py:197: in execute
    return self._once(command, ids, preflight, preflight_error)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src/researchbase/agent_runtime/application/agent_executions.py:218: in _once
    raise preflight_error
src/researchbase/agent_runtime/application/agent_executions.py:191: in execute
    preflight = self._preflight(command)
                ^^^^^^^^^^^^^^^^^^^^^^^^
src/researchbase/agent_runtime/application/agent_executions.py:129: in _preflight
    fail(ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "retained bytes mismatch")
src/researchbase/agent_runtime/application/agent_versions.py:26: in fail
    raise ResearchBaseError(code, message)
E   researchbase.foundation.errors.ResearchBaseError: retained bytes mismatch
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_receipt_committed_during_failed_byte_preflight_is_replayed
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_receipt_committed_during_failed_byte_preflight_is_replayed
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_receipt_committed_during_failed_byte_preflight_is_replayed
1 failed, 2 warnings in 1.06s
```

Exit code: **1**.

**restored** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-v90_9ti_`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-v90_9ti_/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-v90_9ti_`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=short --show-capture=no tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_receipt_committed_during_failed_byte_preflight_is_replayed
```

```text
.                                                                        [100%]
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_receipt_committed_during_failed_byte_preflight_is_replayed
tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_receipt_committed_during_failed_byte_preflight_is_replayed
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1 passed, 2 warnings in 1.03s
```

Exit code: **0**.

### M-S1-INSERT

Copy-only target: `migrations/versions/0081_agent_execution_intents.py`. Replace the first matching block below (L3 is scoped to `begin_formal_read`), then restore the original bytes.

```text
 IF NOT EXISTS (
  SELECT 1 FROM projects p JOIN project_memberships m ON m.project_id=p.id
  JOIN project_role_assignments ro ON ro.membership_id=m.id
  JOIN actors a ON a.id=m.actor_id
  JOIN actor_subject_bindings b ON b.actor_id=a.id
  WHERE p.id=NEW.project_id AND p.lifecycle_status='ACTIVE'
   AND a.id=NEW.caller_actor_id AND a.actor_type='HUMAN' AND a.retired_at IS NULL
   AND m.status='ACTIVE' AND m.started_at<=t AND ro.role='OWNER'
   AND ro.effective_from<=t AND (ro.effective_until IS NULL OR ro.effective_until>t)
   AND b.status='ACTIVE' AND b.bound_at<=t AND (b.revoked_at IS NULL OR b.revoked_at>t)
 ) THEN
  RAISE EXCEPTION 'effective HUMAN OWNER required' USING ERRCODE='23514', CONSTRAINT='pr302_scope';
 END IF;
```

Replacement:

```text
 -- Mutation: S1 OWNER block removed.
```

**removed** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-a_3pyody`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-a_3pyody/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-a_3pyody`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=line --show-capture=no tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head -k insertion_researcher
```

```text
FFF                                                                      [100%]
=================================== FAILURES ===================================
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-a_3pyody/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:107: Failed: DID NOT RAISE <class 'sqlalchemy.exc.DBAPIError'>
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-a_3pyody/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:107: Failed: DID NOT RAISE <class 'sqlalchemy.exc.DBAPIError'>
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-a_3pyody/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:107: Failed: DID NOT RAISE <class 'sqlalchemy.exc.DBAPIError'>
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[insertion_researcher-provision_project_agent]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[insertion_researcher-provision_project_agent]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[insertion_researcher-register_agent_version]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[insertion_researcher-register_agent_version]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[insertion_researcher-change_agent_availability]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[insertion_researcher-change_agent_availability]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[insertion_researcher-provision_project_agent]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[insertion_researcher-register_agent_version]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[insertion_researcher-change_agent_availability]
3 failed, 3 deselected, 6 warnings in 2.55s
```

Exit code: **1**.

**restored** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-a_3pyody`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-a_3pyody/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-a_3pyody`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=line --show-capture=no tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head -k insertion_researcher
```

```text
...                                                                      [100%]
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[insertion_researcher-provision_project_agent]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[insertion_researcher-provision_project_agent]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[insertion_researcher-register_agent_version]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[insertion_researcher-register_agent_version]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[insertion_researcher-change_agent_availability]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[insertion_researcher-change_agent_availability]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
3 passed, 3 deselected, 6 warnings in 2.55s
```

Exit code: **0**.

### M-S1-FINAL

Copy-only target: `migrations/versions/0081_agent_execution_intents.py`. Replace the first matching block below (L3 is scoped to `begin_formal_read`), then restore the original bytes.

```text
 IF NOT EXISTS (
  SELECT 1 FROM projects p JOIN project_memberships m ON m.project_id=p.id
   JOIN project_role_assignments ro ON ro.membership_id=m.id JOIN actors a ON a.id=m.actor_id
   JOIN actor_subject_bindings b ON b.actor_id=a.id
  WHERE p.id=r.project_id AND p.lifecycle_status='ACTIVE' AND a.id=r.caller_actor_id
   AND a.actor_type='HUMAN' AND a.retired_at IS NULL AND m.status='ACTIVE' AND m.started_at<=t
   AND ro.role='OWNER' AND ro.effective_from<=t AND (ro.effective_until IS NULL OR ro.effective_until>t)
   AND b.status='ACTIVE' AND b.bound_at<=t AND (b.revoked_at IS NULL OR b.revoked_at>t)
 ) THEN RAISE EXCEPTION 'OWNER unavailable' USING ERRCODE='23514', CONSTRAINT='pr302_scope'; END IF;
```

Replacement:

```text
 -- Mutation: S1 OWNER block removed.
```

**removed** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-xum8m0dm`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-xum8m0dm/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-xum8m0dm`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=line --show-capture=no tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head -k final_owner_removed
```

```text
FFF                                                                      [100%]
=================================== FAILURES ===================================
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-xum8m0dm/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:129: AssertionError: assert 'pr302_provenance' == 'pr302_scope'
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-xum8m0dm/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:129: AssertionError: assert 'pr302_provenance' == 'pr302_scope'
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-xum8m0dm/tests/integration/phase3/test_pr3_02_s2_intent_guards.py:129: AssertionError: assert 'pr302_provenance' == 'pr302_scope'
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[final_owner_removed-provision_project_agent]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[final_owner_removed-provision_project_agent]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[final_owner_removed-register_agent_version]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[final_owner_removed-register_agent_version]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[final_owner_removed-change_agent_availability]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[final_owner_removed-change_agent_availability]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[final_owner_removed-provision_project_agent]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[final_owner_removed-register_agent_version]
FAILED tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[final_owner_removed-change_agent_availability]
3 failed, 3 deselected, 6 warnings in 2.65s
```

Exit code: **1**.

**restored** — cwd `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-xum8m0dm`; PYTHONPATH `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-xum8m0dm/src:/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/tmp/b4-mutation-xum8m0dm`.

```sh
/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/bin/python -m pytest -o addopts= -q -rfE --tb=line --show-capture=no tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head -k final_owner_removed
```

```text
...                                                                      [100%]
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[final_owner_removed-provision_project_agent]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[final_owner_removed-provision_project_agent]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[final_owner_removed-register_agent_version]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[final_owner_removed-register_agent_version]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[final_owner_removed-change_agent_availability]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_s1_receipts_require_human_owner_at_head[final_owner_removed-change_agent_availability]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane352/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
3 passed, 3 deselected, 6 warnings in 2.62s
```

Exit code: **0**.

## Reproduction helpers

These ignored helpers are reproduced so rerunning does not depend on retaining temporary files. Run them under the environment above. `b4_mutations.py` asserts every removed/restored pair is `[1, 0]`. `b4_fingerprint.py` computes the sorted JSON SHA-256 file manifest and verifies protected files and HEAD.

### tmp/b4_identity.py

```python
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ['DATABASE_URL'])
try:
    with engine.connect() as conn:
        row = conn.execute(text('SELECT version(), current_user')).one()
        print('version | current_user')
        print(f'{row[0]} | {row[1]}')
finally:
    engine.dispose()
```

### tmp/b4_fingerprint.py

```python
import hashlib
import json
from pathlib import Path
import subprocess

root = Path.cwd()
evidence = 'docs/phase3/PR3-02-S2-intent-evidence.md'
head = subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip()
assert head == 'dff29d3792c96c183a3ffbb5569ed72ac41c179c'
paths = subprocess.check_output(['git','ls-files','-z'], text=True).split('\0')
manifest = {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in sorted(paths) if p and p != evidence}
encoded = json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()
fingerprint = hashlib.sha256(encoded).hexdigest()
old = root/'tmp/b4-evidence/source-manifest.json'
if old.exists():
    assert json.loads(old.read_text()) == manifest, 'tested tree changed'
else:
    old.write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
print('HEAD', head)
print('tracked tree SHA-256 (excluding evidence):', fingerprint)
for p in ['tests/integration/phase3/test_pr3_02_s2_intent_guards.py','tests/integration/phase3/test_pr3_02_s2_intent_migration.py','migrations/versions/0081_agent_execution_intents.py','docs/phase3/PR3-02-S2-contract-freeze.md','pyproject.toml','uv.lock']:
    print(manifest[p], p)
protected = [p for p in paths if p and (p.startswith('migrations/') or 'contract-freeze' in p or p in {'pyproject.toml','uv.lock'})]
assert subprocess.check_output(['git','diff','HEAD','--',*protected]) == b''
print('Protected files unchanged from HEAD')
print('git status --short:')
print(subprocess.check_output(['git','status','--short'], text=True),end='')
```

### tmp/b4_mutations.py

```python
"""Review B4 mutation witnesses; only disposable copies under this lane are edited."""
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import tempfile

root = Path.cwd()
logs = root / 'tmp/b4-evidence'
migration = 'migrations/versions/0081_agent_execution_intents.py'
repository = 'src/researchbase/persistence/agent_execution_repository.py'
service = 'src/researchbase/agent_runtime/application/agent_executions.py'
uow = 'src/researchbase/persistence/uow.py'
unit = 'tests/unit/phase3/test_agent_execution_repository.py::'
guards = 'tests/integration/phase3/test_pr3_02_s2_intent_guards.py::'
replay = 'tests/integration/phase3/test_pr3_02_s2_intent_replay.py::'
share_check = """ IF NOT EXISTS(SELECT 1 FROM pg_locks WHERE pid=pg_backend_pid() AND locktype='relation' AND granted
 AND relation=to_regclass('public.'||relation_name) AND mode IN ('ShareLock','ShareRowExclusiveLock','ExclusiveLock','AccessExclusiveLock')) THEN
 RAISE EXCEPTION 'intent SHARE protection absent' USING ERRCODE='23514',CONSTRAINT='pr302s2_preheld'; END IF;"""
cas_check = " IF task.row_version<>x.task_revision_at_creation THEN RAISE EXCEPTION 'task revision' USING ERRCODE='23514',CONSTRAINT='pr302s2_cas'; END IF;"
saved_before_error = """            saved = self._saved(repo, command)
            if saved is not None:
                return saved
            if preflight_error is not None:
                raise preflight_error"""
cases = {
    'L2': (repository,
           '        self._session.execute(text(INTENT_SHARE_SQL))\n        after_wait()',
           '        self._session.execute(text(INTENT_SHARE_SQL))',
           [unit + 'test_fresh_checks_after_each_wait']),
    'L3': (uow, '"postgresql_readonly": True,', '"postgresql_readonly": False,',
           [unit + 'test_formal_read_has_one_readonly_snapshot']),
    'DRIFT': (migration,
              '    if actual != BASELINE_CHECKS:\n        raise RuntimeError("S2 receipt CHECK catalog drift; forward migration refused")',
              '    # Mutation: no baseline CHECK comparison.',
              ['tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_upgrade_refuses_receipt_check_drift']),
    'REVOKE-PUBLIC': (migration,
                      'REVOKE INSERT,UPDATE,DELETE,TRUNCATE ON agent_execution_instances,agent_execution_events FROM PUBLIC;',
                      '-- Mutation: PUBLIC revoke removed.',
                      [guards + 'test_normal_role_cannot_write_intent_tables', '-k', 'PUBLIC']),
    'REVOKE-ROLE': (migration,
                    '        op.execute(\n            f"REVOKE INSERT,UPDATE,DELETE,TRUNCATE ON agent_execution_instances,agent_execution_events FROM {quoted}"\n        )',
                    '        pass  # Mutation: explicit-role revoke removed.',
                    [guards + 'test_normal_role_cannot_write_intent_tables', '-k', 'normal_role-']),
    'SHARE': (migration, share_check, ' PERFORM 1; -- Mutation: SHARE guard removed.',
              [guards + 'test_named_insertion_and_receipt_guards[prefix-pr302s2_preheld]']),
    # Only the first CAS check is removed; the receipt-root CAS remains installed.
    'CAS': (migration, cas_check, ' -- Mutation: insertion CAS guard removed.',
            [guards + 'test_named_insertion_and_receipt_guards[cas-pr302s2_cas]']),
    'ISOLATION': (migration,
                  " IF current_setting('transaction_isolation')<>'read committed' THEN\n RAISE EXCEPTION 'intent isolation' USING ERRCODE='23514',CONSTRAINT='pr302s2_preheld'; END IF;",
                  ' -- Mutation: isolation guard removed.',
                  [guards + 'test_named_insertion_and_receipt_guards[isolation-pr302s2_preheld]']),
    'REPLAY-PREFLIGHT': (service,
                        '            saved = repo.receipt(command)\n            if saved:\n                return None',
                        '            # Mutation: do not short-circuit saved receipt before bytes.',
                        [replay + 'test_saved_replay_precedes_retained_byte_failure']),
    'REPLAY-WRITE': (service, saved_before_error,
                    '            if preflight_error is not None:\n                raise preflight_error\n'
                    '            saved = self._saved(repo, command)\n'
                    '            if saved is not None:\n                return saved',
                    [replay + 'test_receipt_committed_during_failed_byte_preflight_is_replayed']),
}

source = (root / migration).read_text()
for label, message, stage in (
    ('S1-INSERT', 'effective HUMAN OWNER required', 'insertion_researcher'),
    ('S1-FINAL', 'OWNER unavailable', 'final_owner_removed'),
):
    position = source.index(message)
    start = source.rfind('\n IF NOT EXISTS (', 0, position) + 1
    end = source.index(' END IF;', position) + len(' END IF;')
    block = source[start:end]
    assert block.startswith(' IF NOT EXISTS (') and message in block
    cases[label] = (migration, block, ' -- Mutation: S1 OWNER block removed.',
                    [guards + 'test_s1_receipts_require_human_owner_at_head', '-k', stage])

selected = sys.argv[1:] or list(cases)
for name in selected:
    path, old, new, nodes = cases[name]
    with tempfile.TemporaryDirectory(prefix='b4-mutation-', dir=root / 'tmp') as directory:
        copy = Path(directory)
        for folder in ('src', 'tests', 'migrations', 'scripts', 'execution', 'docs'):
            shutil.copytree(root / folder, copy / folder,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        for filename in ('alembic.ini', 'pyproject.toml', 'uv.lock', 'README.md'):
            shutil.copyfile(root / filename, copy / filename)
        original = (copy / path).read_text()
        assert old in original, name
        # L3 is scoped to begin_formal_read, not another UoW method.
        if name == 'L3':
            prefix, body = original.split('    def begin_formal_read(self)', 1)
            mutated = prefix + '    def begin_formal_read(self)' + body.replace(old, new, 1)
        else:
            mutated = original.replace(old, new, 1)
        env = os.environ | {
            'PYTHONPATH': str(copy / 'src') + os.pathsep + str(copy),
            'PYTHONPYCACHEPREFIX': str(copy / 'bytecode'),
        }
        argv = [str(root / '.venv/bin/python'), '-m', 'pytest', '-o', 'addopts=',
                '-q', '-rfE', '--tb=line' if name in {'L2', 'SHARE', 'REVOKE-PUBLIC', 'REVOKE-ROLE', 'S1-INSERT', 'S1-FINAL'} else '--tb=short', '--show-capture=no', *nodes]
        exits = []
        try:
            for state, content in [('removed', mutated), ('restored', original)]:
                (copy / path).write_text(content)
                shutil.rmtree(copy / 'bytecode', ignore_errors=True)
                label = f'M-{name}-{state}'
                with (logs / f'{label}.out').open('w') as output:
                    result = subprocess.run(argv, cwd=copy, env=env, stdout=output,
                                            stderr=subprocess.STDOUT)
                exits.append(result.returncode)
                (logs / f'{label}.json').write_text(json.dumps({
                    'command': shlex.join(argv), 'cwd': str(copy), 'exit_code': result.returncode,
                    'path': path, 'old': old, 'new': new,
                }))
                print(label, 'exit', result.returncode, flush=True)
        finally:
            (copy / path).write_text(original)
        assert (root / path).read_text() == original, 'original checkout changed'
        assert exits == [1, 0], (name, exits)
```

## Completion boundary

Current-source commands have the raw exit codes shown above; deliberately removed guards are expected failures, never normal-suite PASS. Unrun historical H-U/PG-R/PG-N/audit commands receive no current credit. Full suite: **NOT RUN by this agent**; the external loop owns that evidence. No external-loop result, independent B4 re-review, owner acceptance or gate success is asserted. No commit, push, branch creation, protected-file edit or runtime implementation is performed.
