# PR3-05 read-only slice — R4 evidence

Date: 2026-10-24. Scope: owner-approved R4 tests and evidence only. Production
source, frozen draft, migrations, dependency definitions and architecture
exceptions are unchanged. No save/replay, artifact-write lock upgrade, provider,
execution or promotion was implemented. No commit, push or branch creation.

## Environment and method

Every uv invocation used `UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"`.
`RB_TEST_ADMIN_URL` was already explicitly configured. The delivered
`tests/disposable_postgres.py` selector/identity guard created and dropped
random disposable databases; no credentials were guessed and no server was
started. The unchanged `planning`, `normal_engine` and `agents` fixtures
were reused. PostgreSQL **major 18** was verified by the planning fixture's
`SHOW server_version_num` assertion. The actual instrumented readers assert
`rolsuper = false`; setup and migrations use the guarded admin connection.
Shared fixture behavior was not changed. New helpers live in the new modules.

The full repository test suite was **NOT RUN**, as requested. The driver's
check loop owns that evidence. G3 director review/whole-suite acceptance is
pending; this document makes no full PR3-05, PR3-14, live-provider or saving
acceptance claim. D1/D2 remain excluded and G4 remains closed.

## Observed snapshot and SQL evidence

`test_one_readonly_snapshot_survives_committed_writer` instruments the actual
SqlAlchemyUnitOfWork session and normal-role engine. Observed/asserted settings:
`transaction_isolation = repeatable read`, `transaction_read_only = on`,
`autoflush = False`, exactly **one reader UoW/session** and exactly **one**
SQL statement containing `transaction_timestamp()`. SQL is restricted to
SELECT/SHOW/WITH, with no FOR UPDATE, FOR SHARE, PG_ADVISORY or LOCK TABLE.
Connection commit and session flush listeners raise immediately if invoked.

An Event barrier pauses after task/binding reconstruction and before expansion.
A separate legitimate Application writer commits cancellation. The original
reader returns CREATED at revision **2**, all **six** sources and the same
revision/pinned budget policy in safety. A new query sees CANCELLED at revision
**3**. Safety policies are actually bound before the read. The writer is an
independent test connection, not a second reader UoW.

`test_context_reader_completes_under_delivered_writer_exclusion_locks` holds
the accepted writer protocol's locks while the actual normal-role reader
completes in a separate thread with all six sources (3-second completion bound).
This is real PostgreSQL concurrency, not sequential mocks.

`test_consumer_uses_one_readonly_session_without_mutation[memory/promotion]`
independently instruments each remaining public service: the same isolation,
read-only, non-superuser and autoflush assertions; one session and one timestamp
sample; SELECT/SHOW/WITH only; no row/table/advisory locks, flush or commit.
ArtifactStore writes raise. Static Application boundary tests prohibit mutation
and provider/transport/persistence imports; no execution consumer is activated.

## Coverage map (plan §3 R4)

| Required group | Concrete evidence |
| --- | --- |
| 1. Closed formats, bounds, hashes and binding owners | Unit `test_owning_hashes_round_trip_without_rehash` (six families), `test_recursive_malformed_format_rejected`, `test_note_source_and_encoded_bounds`; exact 1,048,576 bytes, 256 sources, 8,192 characters plus over-limit rejection; duplicate sources/JSON keys, unknown nested fields/families, NaN, NFC, UUIDs, order, immutable results. Existing canonical unit tests retain separate task/step binding IDs and reject hash contradictions. |
| 2. Exact scientific context and observations | PostgreSQL `test_each_family_resolves_task_and_step_bindings` (six families), `test_draft_and_live_reference_do_not_enter_context`, `test_current_pointer_change_preserves_exact_historical_artifact`, `test_current_validity_and_safety_are_observations`, `test_required_artifact_bytes_fail_entire_query`, `test_dedup_contradiction_fails_closed_in_postgres_read`; unit STALE/INVALID/UNKNOWN/UNASSESSED and CORRECTED/RETRACTED observations retain values. |
| 3. One lock-free snapshot | The three instrumented reader paths and the two controlled concurrency cases described above, including a committed writer and a fresh read. |
| 4. Scope and trusted admission | PostgreSQL `test_out_of_scope_node_denied_before_any_store_access`, `test_hash_guesses_and_foreign_manifest_sources_fail_closed` (global/foreign × memory/candidate/manifest-source), same bytes/hash across projects, no denied store access or protected error details; `test_revoked_principal_and_wrong_step_disclose_no_context`, `test_wrong_task_step_missing_version_and_denied_credentials`, `test_unlinked_literature_source_and_unbound_agent_are_denied`, `test_enrolled_agent_and_human_use_same_boundary`. Unit tests cover all five read roles, archived history and revoked binding/membership/credentials before expansion. |
| 5. Memory loss, rebuilding and expiry | PostgreSQL `test_optional_loss_explicit_read_failure_and_fresh_reconstruction` (missing/corrupt/malformed/oversize), `test_optional_memory_never_hides_required_context_byte_loss`, `test_expiry_is_projected_without_changing_checkpoint_history`, `test_bytes_actually_returned_are_verified`; fresh canonical construction has no private notes and no storage repair. |
| 6. Promotion and inert memory | PostgreSQL `test_candidate_basis_revision_gates_and_missing_s2` exercises both targets with approved checkpoint fixtures, valid context, wrong revision/hash/basis, cancellation and mandatory S2 limitation; foreign candidate/manifest sources fail closed. `test_exact_memory_is_inert_and_reloaded` retains instruction-like text as data and recomputes saved VALID as current UNASSESSED; `test_manifest_reloads_all_six_sources_and_hash_mismatch_fails` reloads all sources. Unit target-family/request checks reject unsupported targets before a UoW. Consumer SQL/store spies and false capability flags remain asserted. |
| 7. Boundaries and reviewer independence | Extended architecture tests preserve the existing bounded public owning-reader/composition assertions, prohibit SQL/vendor/transport/write calls in read services, verify frozen results and false action flags, and ensure canonical reconstruction has no memory/scratchpad field. Existing import/bootstrap/head/dependency guards run in the required architecture suites. No new schema/dependency or exception is introduced. |

## Authoring failures and disposition

Executed failures were not counted as PASS. A development run of
`uv run pytest -o addopts='' -q -rfE tests/unit/phase3/test_canonical_context.py tests/integration/phase3/test_pr3_05_memory_reads.py`
returned **1 failed, 34 passed, 2 warnings**, exit **1**: the new test expected
AUTHENTICATION_REQUIRED for revoked credentials. Delivered
`research_task.py` `TaskContextAdmission._authorize` (lines 98–120) explicitly
ends with `fail(ErrorCode.FORBIDDEN, "current project entitlement unavailable")`.
The draft §7 permits FORBIDDEN for unavailable credentials/disclosure authority.
The test now checks that exact delivered result and still prohibits expansion.

An expanded three-file PostgreSQL run returned **2 failed, 44 passed,
3 warnings**, exit **1**: a new positive promotion assertion lacked the mandatory
plan-review checkpoint. Delivered `task_safety.py:gates` unions required types
with `{"plan_review"}`. The fixture now approves that checkpoint through the
existing `approve` Application helper before asserting admissibility, then
cancels through the existing task command and asserts GATE_UNMET. No gate
requirement was removed and no production behavior changed.

Intermediate Ruff runs found import order, line length and constant-setattr
style errors. Intermediate Pyright runs reported 19, 2, 10 and 5 errors in new
test construction/narrowing. These were corrected with ordinary formatting,
explicit malformed-value casts, existing union-type assertions and base UoW
factory return annotations; no lint/type exclusion was added. Final current
results follow. No git/uv lock or sandbox error occurred, and no check was skipped.

## Final commands and raw output

Each command below was executed separately. The uv commands used the cache
environment assignment described above. All test counts belong to this lane's
runs, not historical evidence. All final runs have **0 failed, 0 skipped**.
Warnings are the existing Alembic path_separator deprecation and Pyright's
version-update notice; no dependencies/configuration were changed to hide them.


### git diff --check HEAD

Exit code: **0**.

```text
(empty output)
```

### uv run ruff check .

Exit code: **0**.

```text
All checks passed!
```

### uv run ruff format --check .

Exit code: **0**.

```text
931 files already formatted
```

### uv run pyright

Exit code: **0**.

```text
0 errors, 0 warnings, 0 informations
WARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`

```

### uv run alembic heads

Exit code: **0**.

```text
0080_capability_gateway (head)
```

### uv run pytest -o addopts='' -q -rfE tests/unit/phase3 tests/architecture tests/unit/architecture

Exit code: **0**.

```text
........................................................................ [  5%]
........................................................................ [ 10%]
........................................................................ [ 15%]
........................................................................ [ 20%]
........................................................................ [ 25%]
........................................................................ [ 30%]
........................................................................ [ 36%]
........................................................................ [ 41%]
........................................................................ [ 46%]
........................................................................ [ 51%]
........................................................................ [ 56%]
........................................................................ [ 61%]
........................................................................ [ 66%]
........................................................................ [ 72%]
........................................................................ [ 77%]
........................................................................ [ 82%]
........................................................................ [ 87%]
........................................................................ [ 92%]
........................................................................ [ 97%]
..............................                                           [100%]
=============================== warnings summary ===============================
tests/architecture/test_b02_strategy_promotion_boundaries.py: 1 warning
tests/architecture/test_b04_boundaries.py: 1 warning
tests/architecture/test_b05_review_boundaries.py: 1 warning
tests/architecture/test_b15_package_boundaries.py: 1 warning
tests/architecture/test_b20_screening_boundaries.py: 1 warning
tests/architecture/test_basic_approval.py: 1 warning
tests/architecture/test_pr2_19_boundaries.py: 43 warnings
tests/architecture/test_pr3_02_s1_boundaries.py: 1 warning
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane144/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1398 passed, 50 warnings in 32.72s
```

### uv run pytest -o addopts='' -ra tests/unit/phase3/test_context_contracts.py tests/unit/phase3/test_canonical_context.py tests/unit/phase3/test_task_memory.py tests/unit/phase3/test_promotion_context.py tests/unit/phase3/test_research_task_contracts.py tests/unit/phase3/test_task_safety_contracts.py

Exit code: **0**.

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane144
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 132 items

tests/unit/phase3/test_context_contracts.py ...............              [ 11%]
tests/unit/phase3/test_canonical_context.py .......................      [ 28%]
tests/unit/phase3/test_task_memory.py ..                                 [ 30%]
tests/unit/phase3/test_promotion_context.py ..                           [ 31%]
tests/unit/phase3/test_research_task_contracts.py ...................... [ 48%]
....................................................                     [ 87%]
tests/unit/phase3/test_task_safety_contracts.py ................         [100%]

============================= 132 passed in 0.29s ==============================
```

### uv run pytest -o addopts='' -ra tests/architecture/test_pr3_05_readonly_boundaries.py tests/architecture/test_pr3_01_boundaries.py tests/architecture/test_pr3_04_boundaries.py tests/architecture/test_pr3_02_s1_boundaries.py tests/architecture/test_import_boundaries.py

Exit code: **0**.

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane144
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 26 items

tests/architecture/test_pr3_05_readonly_boundaries.py .....              [ 19%]
tests/architecture/test_pr3_01_boundaries.py ....                        [ 34%]
tests/architecture/test_pr3_04_boundaries.py ..                          [ 42%]
tests/architecture/test_pr3_02_s1_boundaries.py ..                       [ 50%]
tests/architecture/test_import_boundaries.py .............               [100%]

=============================== warnings summary ===============================
tests/architecture/test_pr3_02_s1_boundaries.py::test_authorized_head_and_s1_only
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane144/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 26 passed, 1 warning in 0.69s =========================
```

### uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_05_context_reads.py tests/integration/phase3/test_pr3_05_memory_reads.py tests/integration/phase3/test_pr3_05_promotion_validation.py

Exit code: **0**.

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane144
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 46 items

tests/integration/phase3/test_pr3_05_context_reads.py .................. [ 39%]
.........                                                                [ 58%]
tests/integration/phase3/test_pr3_05_memory_reads.py .................   [ 95%]
tests/integration/phase3/test_pr3_05_promotion_validation.py ..          [100%]

=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_05_context_reads.py::test_each_family_resolves_task_and_step_bindings[RESEARCH_QUESTION_VERSION]
tests/integration/phase3/test_pr3_05_context_reads.py::test_each_family_resolves_task_and_step_bindings[RESEARCH_QUESTION_VERSION]
tests/integration/phase3/test_pr3_05_context_reads.py::test_enrolled_agent_and_human_use_same_boundary
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane144/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 46 passed, 3 warnings in 5.48s ========================
```

### uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_01_application.py tests/integration/phase3/test_pr3_01_concurrency.py tests/integration/phase3/test_pr3_01_replay.py tests/integration/phase3/test_pr3_04_queries.py tests/integration/phase3/test_pr3_04_replay.py tests/integration/phase3/test_pr3_02_s1_application.py tests/integration/phase3/test_pr3_02_s1_replay.py

Exit code: **0**.

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane144
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 68 items

tests/integration/phase3/test_pr3_01_application.py .......              [ 10%]
tests/integration/phase3/test_pr3_01_concurrency.py ................     [ 33%]
tests/integration/phase3/test_pr3_01_replay.py ...............           [ 55%]
tests/integration/phase3/test_pr3_04_queries.py ..                       [ 58%]
tests/integration/phase3/test_pr3_04_replay.py ....                      [ 64%]
tests/integration/phase3/test_pr3_02_s1_application.py ..............    [ 85%]
tests/integration/phase3/test_pr3_02_s1_replay.py ..........             [100%]

=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_01_application.py: 2 warnings
tests/integration/phase3/test_pr3_02_s1_application.py: 14 warnings
tests/integration/phase3/test_pr3_02_s1_replay.py: 10 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane144/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 68 passed, 26 warnings in 24.79s =======================
```
