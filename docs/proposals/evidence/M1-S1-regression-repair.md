# M1-S1 regression repair — 2026-10-20

Scope: continue the existing uncommitted M1-S1 implementation. No branches,
commits, new migrations beyond 0074, or changes to migrations 0001–0073.
The complete suite is reserved for the director's loop.

## Reproduction and causes

The first reproduction selected the supplied nodes plus the fifth PR2-12 test:
**18 failed, 1 passed, 55 warnings in 51.53s**. The additional passing node was
`test_invalid_document_and_direct_sql_pointer_rejected`. The first repaired exact-18
selection initially deselected that passing node; the final rerun names the four
PR2-12 nodes explicitly and has no deselection. No test is weakened or skipped in source.

All integration paths below are under `tests/integration/phase2/`.

| Test | One-line cause |
|---|---|
| `test_pr2_12_publication_draft.py::test_create_draft_readback_and_no_implicit_freeze` | INITIAL creation at 0035 acquired M1 edit locks on placement tables absent at that revision, raising UndefinedTable. |
| `test_pr2_12_publication_draft.py::test_idempotency_authority_and_missing_bytes_fail_closed` | The initial draft setup at 0035 hit the same premature M1 placement-table lock before replay/byte checks. |
| `test_pr2_12_publication_draft.py::test_concurrent_replay_and_direct_sql_history_guards` | Both initial writers at 0035 requested the premature M1 placement-table inventory. |
| `test_pr2_12_publication_draft.py::test_create_draft_response_is_atomic_with_command` | The 0035 draft command failed on missing M1 lock tables before it could exercise atomic response materialization. |
| `test_pr2_19_revision_cycle.py::test_completed_result_does_not_dispose_until_independent_command[NEW_EXPERIMENT]` | The exported revision/disposition inventory included the two issue tables, while disposition SQL correctly excluded them under M1 §12.2. |
| `test_pr2_19_revision_cycle.py::test_completed_result_does_not_dispose_until_independent_command[ANALYSIS_CHANGE]` | The exported revision/disposition inventory included the two issue tables, while disposition SQL correctly excluded them under M1 §12.2. |
| `test_pr2_19_revision_cycle.py::test_completed_result_does_not_dispose_until_independent_command[CLAIM_CHANGE]` | The exported revision/disposition inventory included the two issue tables, while disposition SQL correctly excluded them under M1 §12.2. |
| `test_pr2_19_revision_cycle.py::test_completed_result_does_not_dispose_until_independent_command[CONCLUSION_CHANGE]` | The exported revision/disposition inventory included the two issue tables, while disposition SQL correctly excluded them under M1 §12.2. |
| `test_pr2_19_revision_cycle.py::test_completed_result_does_not_dispose_until_independent_command[SOURCE_CHANGE]` | The exported revision/disposition inventory included the two issue tables, while disposition SQL correctly excluded them under M1 §12.2. |
| `test_pr2_19_revision_cycle.py::test_completed_result_does_not_dispose_until_independent_command[NO_CHANGE]` | The exported revision/disposition inventory included the two issue tables, while disposition SQL correctly excluded them under M1 §12.2. |
| `test_b11_readiness_races.py::test_snapshot_read_final_expiry_denies` | Replacing the existing applicable-review query bypassed its expiry-injection hook, so the test never expired credentials before final authorization. |
| `test_b14a_entry_concurrency.py::test_real_b04_seal_writer_both_commit_orders[True]` | Initial B04 freeze requested M1 EXCLUSIVE table locks instead of reaching the original entry-held row/transaction lock wait. |
| `test_b14r_ready_approval_schema.py::test_populated_predecessor_preserved_and_ready_history_refuses_downgrade` | Readiness called the 0074-only m1_admission_reviews function after the test pinned the schema to 0063. |
| `test_b14_ready_replay.py::test_restart_later_blocker_and_missing_bytes_do_not_readmit_history` | The newly added manuscript-review verification readmitted document bytes while deriving retained READY-history blockers. |
| `test_b05_review_races.py::test_mixed_existing_protocols_with_protected_verifier[b04]` | The new early frozen replay return bypassed B04's existing project advisory coordination during the protected verifier. |
| `test_pr2_20_migrations.py::test_populated_conclusion_placement_review_and_0042_checkpoints` | Draft creation at 0037 acquired the later M1 placement inventory; the initial placement path also assumed later B04 tables. |
| `test_pr2_19_citation_trace.py::test_g5_application_freeze_retains_exact_scientific_paths` | Initial freeze emitted M1's first SHARE inventory instead of the pre-existing literal B04 inventory. |
| `tests/test_architecture.py::test_phase1_has_no_unauthorized_later_business_schema_migration` | The explicit authorized migration inventory omitted 0074. |

## Repairs and contract alignment

- INITIAL creation and initial-version placement/freeze retain the PR2-12/B04
  protocols and work at pinned predecessor schemas. Initial B04 freeze retains
  its existing project coordination, including replay. Successor draft,
  placement and freeze use the dedicated `prepare_revision_write`: M1-A SHARE,
  then disjoint M1-B EXCLUSIVE, followed by the guide's advisory/row locks.
  This follows the director's explicit compatibility instruction; earlier §14
  implementation notes claiming all initial freezes use M1 are superseded.
- M1 §12.2 explicitly requires full B09 (46 tables) for revision decision,
  action and re-review, and B09 minus `review_issues`/`review_issue_events`
  (44 tables) for disposition. `REVISION_SNAPSHOT_TABLES` now denotes that
  disposition subset; the revision writer still emits full B09. The previously
  edited architecture/B06/B07 expectations distinguish those contracts, with
  §12.2 citations. An independent M1 architecture assertion checks set equality.
- Admission composes the existing `applicable_manuscript_reviews` query with the
  earlier same-Publication OPEN/BLOCKING manuscript query, deduplicated and
  sorted by UUID. This preserves predecessor-schema support and final expiry
  injection. It has the same membership as the 0074 SQL helper; exact-target
  affirmative review basis remains unchanged (M1 §3, §12.1).
- Blocker reviews verify retained seals and review attribution under
  `saved_seal`; selected-target admission remains separate. READY history can
  report later blockers after bytes disappear without readmitting that history
  (M1 §3, §7). Hash, creation-authority and issue-history checks remain active.
- The architecture migration inventory adds only the authorized 0074 entry.
  Existing B04 lock expectations and owner wait expectations were restored;
  the replay-aware writer pause helper still waits until actual locks are held.
  Separate query discovery follows M1 §7; each legacy writer still starts with
  the literal B04 inventory in its own transaction.

## b07_validate_revision IF / END IF pairing

The installed function is exported without truncation in
[M1-S1-function-review/b07_validate_revision.sql](M1-S1-function-review/b07_validate_revision.sql).
The 0074 upgrade body now indents the retained scientific arm and labels the
outer close. Its control flow is:

```sql
IF review.manuscript_version_id IS NOT NULL THEN  -- outer target dispatch
  -- exact frozen manuscript concern, allowed action, later same-Publication result
  IF a.action_type = 'MANUSCRIPT_CHANGE' THEN
    -- validate result seal and lineage
  END IF;                                       -- manuscript result arm
ELSE                                            -- scientific concerns
  IF a.action_type = 'MANUSCRIPT_CHANGE' THEN
    RAISE EXCEPTION ...;
  END IF;                                       -- incompatible action
  IF review.claim_version_id IS NOT NULL THEN
    -- claim basis
  ELSE
    -- scientific conclusion basis
  END IF;                                       -- scientific target selection
  -- retained same-project/frozen closure and result-validation branches
  IF a.action_type = 'NO_CHANGE' THEN ...
  ELSIF ... THEN ...
  END IF;                                       -- scientific result validation
  -- retained target/result fact verification
  IF a.action_type = 'CLAIM_CHANGE' THEN ...
  ELSIF ... THEN ...
  END IF;                                       -- scientific fact dispatch
END IF;                                         -- outer target dispatch
-- shared by manuscript AND scientific concerns:
cursor_id := a.supersedes_revision_action_id;
WHILE cursor_id IS NOT NULL LOOP
  -- reject cycles and different-basis correction chains
END LOOP;
```

PostgreSQL tests call the installed validator directly on valid saved actions
for MANUSCRIPT_CHANGE, manuscript NO_CHANGE, and all six scientific action kinds.
Local composite mutations also prove wrong target/action dispatch rejects and
that **both** outer arms reach the shared correction-cycle rejection. No
scientific row or trigger is modified to produce those probes.

## 0074 upgrade and downgrade

`test_m1_upgrade_downgrade_catalog_preserves_predecessor_functions` executes:

```text
0074 -> downgrade 0073 -> capture predecessor catalog
0073 -> upgrade 0074 -> assert unchanged table inventory, M1 checks/index/FK
0074 -> downgrade 0073 -> assert exact equality of all public function definitions
0073 -> upgrade 0074
```

`test_m1_downgrade_refuses_successor_history` seals v1, creates v2, attempts the
0074 downgrade, checks P17F1, and proves both manuscripts and the 0074 revision
remain. Duplicate-draft preflight proves failed upgrade preserves legacy rows.
Only 0074's upgrade body was clarified; its predecessor-restoring downgrade
body and all migrations 0001–0073 remain unchanged.

The catalog export was regenerated successfully with:

```sh
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres UV_CACHE_DIR=/tmp/researchbase-m1-uv-cache uv run python -m scripts.m1_sql_review
```

Observed: 32 actual 0073→0074 function diffs and the installed validator exported;
the isolated database was dropped. Whitespace indentation in the scientific
arm changes the textual diff, not its retained validation statements.

## Verification commands and observed results

All commands ran from the repository root. `DATABASE_URL` was the provided
local PostgreSQL lane database; fixtures create and drop isolated databases.
`UV_CACHE_DIR=/tmp/researchbase-m1-uv-cache` prefixes the uv commands below.

```sh
uv run pytest -o addopts='' tests/integration/phase2/test_pr2_12_publication_draft.py tests/integration/phase2/test_pr2_19_revision_cycle.py::test_completed_result_does_not_dispose_until_independent_command tests/integration/phase2/test_b11_readiness_races.py::test_snapshot_read_final_expiry_denies 'tests/integration/phase2/test_b14a_entry_concurrency.py::test_real_b04_seal_writer_both_commit_orders[True]' tests/integration/phase2/test_b14r_ready_approval_schema.py::test_populated_predecessor_preserved_and_ready_history_refuses_downgrade tests/integration/phase2/test_b14_ready_replay.py::test_restart_later_blocker_and_missing_bytes_do_not_readmit_history 'tests/integration/phase2/test_b05_review_races.py::test_mixed_existing_protocols_with_protected_verifier[b04]' tests/integration/phase2/test_pr2_20_migrations.py::test_populated_conclusion_placement_review_and_0042_checkpoints tests/integration/phase2/test_pr2_19_citation_trace.py::test_g5_application_freeze_retains_exact_scientific_paths tests/test_architecture.py::test_phase1_has_no_unauthorized_later_business_schema_migration --deselect=tests/integration/phase2/test_pr2_12_publication_draft.py::test_invalid_document_and_direct_sql_pointer_rejected --tb=short
uv run pytest -o addopts='' tests/integration/phase2/test_m1_schema.py tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_m1_concurrency.py --tb=short
uv run pytest -o addopts='' tests/integration/phase2/test_m1_concurrency.py::test_successor_placements_and_freeze_keep_disjoint_first_locks --tb=short
uv run pytest -o addopts='' tests/unit tests/architecture tests/test_architecture.py --tb=short
```

| Selection | Observed result |
|---|---|
| Exact 18 regression nodes, first repaired run | 18 passed, 1 deselected, 59 warnings in 69.49s |
| M1 PostgreSQL suites before the additional successor lock capture test | 30 passed, 97 warnings in 88.62s |
| Additional successor placement/freeze lock capture | 1 passed, 3 warnings in 6.24s |

The following records preserve intermediate failures and final verification.
No full-suite result is claimed here.

Final unit/architecture selection: **6216 passed, 54 warnings in 140.66s**.
This includes all **19 M1 unit cases** and **2 M1 architecture cases**.
The first invocation had **6213 passed, 3 failed, 54 warnings in 134.65s**:
the new tests accessed a psycopg-only `diag` attribute without narrowing its
SQLAlchemy exception type, and two `inspect.getsource` checks observed stale
line positions while the imported Publication module was reformatted. The
attribute probes now use `getattr`; a fresh process passed both boundary checks
(**4 passed in 0.56s**) and the complete fresh selection passed as reported above.

The additional successor lock-capture test initially failed (**1 failed,
3 warnings in 2.93s**): its freeze assertion observed the B05 engine while the
fixture's freeze service uses the original B04 engine. Observing the actual
service engine fixed the new test; all four writer inventories are still asserted.

Final static command:

```sh
UV_CACHE_DIR=/tmp/researchbase-m1-uv-cache uv run ruff format --check . && UV_CACHE_DIR=/tmp/researchbase-m1-uv-cache uv run ruff check . && UV_CACHE_DIR=/tmp/researchbase-m1-uv-cache uv run pyright && git diff --check HEAD
```

Observed: **790 files already formatted**; **All checks passed**; **0 errors,
0 warnings, 0 informations**; whitespace check exit **0**. Pyright emitted an
available-version notice. Earlier static failures from the new exception attribute
probes and formatting were corrected, not added to the accepted baseline.

The neighboring PostgreSQL selection is:

```sh
UV_CACHE_DIR=/tmp/researchbase-m1-uv-cache uv run pytest -o addopts='' tests/integration/phase2/test_m1_concurrency.py::test_successor_placements_and_freeze_keep_disjoint_first_locks tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b04_manuscript_races.py tests/integration/phase2/test_b06_revision_concurrency.py tests/integration/phase2/test_b07_concurrency.py tests/integration/phase2/test_b08_concurrency.py tests/integration/phase2/test_b11_readiness_races.py tests/integration/phase2/test_b14a_entry_concurrency.py::test_real_b04_seal_writer_both_commit_orders tests/integration/phase2/test_b05_review_races.py::test_mixed_existing_protocols_with_protected_verifier tests/integration/phase2/test_b14_ready_replay.py tests/integration/phase2/test_b14r_ready_approval_schema.py --tb=short
```

Observed neighbor result: **275 passed, 1 failed, 842 warnings in 1069.59s
(17:49)**. The only failing node was the new successor lock-capture test's
wrong-engine observer, already corrected and verified separately above. All
275 existing selected neighbor cases passed, including the restored B04
inventories/waits, B06/B07 full B09 writes, B08 disposition races, B11 expiry,
both entry/seal orders, protected verifier protocols and READY replay/schema
checks. The complete final M1 rerun below includes the corrected capture case.

Final exact-18 rerun command (four explicit PR2-12 nodes; no deselection):

```sh
UV_CACHE_DIR=/tmp/researchbase-m1-uv-cache uv run pytest -o addopts='' tests/integration/phase2/test_pr2_12_publication_draft.py::test_create_draft_readback_and_no_implicit_freeze tests/integration/phase2/test_pr2_12_publication_draft.py::test_idempotency_authority_and_missing_bytes_fail_closed tests/integration/phase2/test_pr2_12_publication_draft.py::test_concurrent_replay_and_direct_sql_history_guards tests/integration/phase2/test_pr2_12_publication_draft.py::test_create_draft_response_is_atomic_with_command tests/integration/phase2/test_pr2_19_revision_cycle.py::test_completed_result_does_not_dispose_until_independent_command tests/integration/phase2/test_b11_readiness_races.py::test_snapshot_read_final_expiry_denies 'tests/integration/phase2/test_b14a_entry_concurrency.py::test_real_b04_seal_writer_both_commit_orders[True]' tests/integration/phase2/test_b14r_ready_approval_schema.py::test_populated_predecessor_preserved_and_ready_history_refuses_downgrade tests/integration/phase2/test_b14_ready_replay.py::test_restart_later_blocker_and_missing_bytes_do_not_readmit_history 'tests/integration/phase2/test_b05_review_races.py::test_mixed_existing_protocols_with_protected_verifier[b04]' tests/integration/phase2/test_pr2_20_migrations.py::test_populated_conclusion_placement_review_and_0042_checkpoints tests/integration/phase2/test_pr2_19_citation_trace.py::test_g5_application_freeze_retains_exact_scientific_paths tests/test_architecture.py::test_phase1_has_no_unauthorized_later_business_schema_migration --tb=short
```

Complete final M1 rerun command:

```sh
UV_CACHE_DIR=/tmp/researchbase-m1-uv-cache uv run pytest -o addopts='' tests/integration/phase2/test_m1_schema.py tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_m1_concurrency.py --tb=short
```

Final exact-18 observed result: **18 passed, 59 warnings in 93.60s (1:33)**.
Exactly 18 nodes were collected; no deselection or skip.

Final complete M1 PostgreSQL observed result: **31 passed, 100 warnings in
109.39s (1:49)**: 13 schema, 4 manuscript workflow, and 14 concurrency cases.
This includes the corrected successor lock-capture test. No test was skipped.

The 18 supplied regression tests retain their expectations; the only edit in
those test files is the specifically requested appended 0074 authorization entry.
The other expectation corrections are the guide-cited inventory distinctions
and restoration of the legacy B04 protocol described above.

Final verification: exact regressions **18/18**; complete M1 PostgreSQL **31/31**;
unit/architecture **6216 passed** (including M1's 19 unit and 2 architecture cases);
all **275 existing** selected PostgreSQL neighbors passed; Ruff/Pyright and
`git diff --check HEAD` passed. Alembic deprecations remain visible in the
recorded warning counts. Only migration 0074 is changed relative to HEAD.
No complete-suite run, commit, push, or branch creation was performed.
