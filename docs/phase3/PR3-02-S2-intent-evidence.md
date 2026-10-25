# PR3-02-S2 intent implementation evidence

Baseline: `75d559a` (2026-10-25). Intent-only implementation; this is focused verification evidence, not owner acceptance or a full-suite gate claim.

## Exact file allocation before implementation

- Q3: `migrations/versions/0081_agent_execution_intents.py`
- Q4: `src/researchbase/agent_runtime/domain/agent_execution.py`
- Q4/Q5: `src/researchbase/agent_runtime/application/execution_contracts.py`
- Q2–Q5 ports: `src/researchbase/agent_runtime/ports/execution_repository.py`
- Q2–Q5 persistence: `src/researchbase/persistence/agent_execution_repository.py`
- Q1/Q2/Q4/Q5: `src/researchbase/agent_runtime/application/agent_executions.py`
- Q5 receipt result: `src/researchbase/agent_runtime/application/agent_contracts.py`
- Q2/Q3.5 UoW: `src/researchbase/persistence/uow.py`
- U1–U3: `tests/unit/phase3/test_agent_execution_contracts.py`
- L1–L3: `tests/unit/phase3/test_agent_execution_repository.py`
- A1: `tests/architecture/test_pr3_02_s2_boundaries.py`
- Intent fixtures: `tests/integration/phase3/intent_fixtures.py`
- M1–M3: `tests/integration/phase3/test_pr3_02_s2_intent_migration.py`
- G1–G3: `tests/integration/phase3/test_pr3_02_s2_intent_guards.py`
- E1–E3: `tests/integration/phase3/test_pr3_02_s2_intent_execution.py`
- R1–R2: `tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py`
- R3–R5: `tests/integration/phase3/test_pr3_02_s2_intent_replay.py`

Appendix H mechanical head updates:

- `.github/workflows/ci.yml`
- `tests/fixtures/phase2_static_baseline.json`
- `tests/architecture/test_basic_approval.py`
- `tests/architecture/test_b04_boundaries.py`
- `tests/architecture/test_b20_screening_boundaries.py`
- `tests/architecture/test_b02_strategy_promotion_boundaries.py`
- `tests/architecture/test_b05_review_boundaries.py`
- `tests/architecture/test_pr3_02_s1_boundaries.py`
- `tests/architecture/test_import_boundaries.py`
- `tests/unit/test_task12_migration_history.py`
- `tests/unit/test_batch_c_migration_history.py`
- `tests/unit/phase2/test_pr2_04_r8a_host_topology.py`
- `tests/unit/phase2/test_pr2_20_inventory.py`
- `tests/integration/phase2/test_pr2_04_execution_migration.py`
- `tests/integration/phase2/test_pr2_04_migration_coverage.py`
- `tests/integration/phase2/test_pr2_17_authorship_schema.py`
- `tests/integration/phase2/test_pr2_03_review_guards.py`
- `tests/integration/phase2/test_pr2_15_decision_schema.py`
- `tests/integration/phase2/test_revision_action.py`
- `tests/integration/phase3/test_pr3_00_bootstrap.py`
- `tests/integration/phase3/test_pr3_01_migration.py`
- `tests/integration/phase3/test_pr3_02_s1_migration.py`
- `tests/integration/phase3/test_pr3_03_migration.py`
- `tests/integration/phase3/test_pr3_04_migration.py`
- `tests/integration/phase2/pr2_20_support.py`: Appendix H exact catalog allowance.
- `docs/phase3/PR3-02-S2-intent-evidence.md`: this evidence.


File-allocation refinements discovered during focused verification (within Q3/Appendix H):
- `src/researchbase/persistence/models.py`: inert two-table mappings and two receipt result FKs.
- `tests/architecture/test_pr17_agent_ready_architecture.py`: exact five intent classes and two inert model classes admitted; other runtime exclusions retained.
- `tests/architecture/test_pr3_00_boundaries.py`: exact four authorized intent modules admitted.
- `tests/fixtures/phase3/build_intent_vectors.py` and `tests/fixtures/phase3/intent_vectors.json`: Q4 independent standard-library source and literal vectors.


## Delivered boundary and run attribution

The owner-authorized scope is frozen Q1 and Q3's two intent tables, with Q2/Q4/Q5
support needed for create, exact replay and historical reads. The numeric option-A,
privilege-guard and source-link-revocation refreezes govern. No frozen document,
accepted migration, dependency definition or governing Harness file was edited.
No commit, push or branch creation was performed.

New sole head: `0081_agent_execution_intents`; parent: `0080_capability_gateway`.

Every PostgreSQL assertion below is attributed to a run:

- **PG-I**: required 68-test intent command, raw output below. Disposable PostgreSQL
  18 databases, owning Application connection plus the existing non-superuser S1
  role for direct privilege checks. No required test was skipped.
- **PG-T**: the two separately repeated temporal nodes, with uncaptured raw output
  below: PostgreSQL 18.6 (Homebrew), owning role `researchbase`, port 5432,
  explicitly selected local cluster; random database names and DB timestamps are
  printed. `xact_start` is transaction start; `observed_at` records an actual lock
  wait; `lock_acquired_at` is recorded after the blocked statement returns;
  `authorization_checked_at` is a subsequent advancing DB time. Times with
  America/New_York offsets and UTC denote comparable aware instants. Both the
  first SHARE wait and the distinct later advisory wait cross credential expiry.
  Intent/event totals remain zero; the two S1 receipts are unchanged baseline
  rows, not new intent receipts.
- **PG-R**: selected historical migration/catalog nodes, S1 Application/replay
  suites and the unchanged PR3-05 producer-preview denial, raw command below.
- **PG-N**: disposable catalog probe, raw output below. It confirms PostgreSQL
  18's generated NOT NULL constraint names for the exact Appendix-H allowance.
- **U-A**: required unit/architecture command. It makes no PostgreSQL correctness
  claim; **H-U** is the supplemental historical/static unit command.
- **AUDIT**: source/byte audit only; not a PostgreSQL run.

All tooling commands below used this environment. Test fixtures temporarily
replace DATABASE_URL with their explicitly created random disposable databases;
they do not use an ambient database or SQLite:

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
export DATABASE_URL='postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase_lane331'
export RB_TEST_ADMIN_URL='postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres'
export PGOPTIONS='-c jit=off'
```

## Frozen-item implementation and exact test allocation

Node IDs below are repository-relative. Parameterized base nodes identify every
parameter unless an exact parameter is given.

| Frozen item | Implemented surface | Evidence / exact node IDs |
| --- | --- | --- |
| Q1 CREATED-only, revision 1, sealed PLANNING/current task revision, optional same-task PENDING step | Closed CreateAgentExecution/ExecutionCommand; AgentExecutionService | PG-I: `tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_created_intent_through_common_application_boundary`, `tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_denials_preserve_closed_execution_gate`, `tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_selected_step_and_typed_inputs_preserve_both_owners` |
| Q1 three effects only; unchanged task/step revision/state, closed gate, no policy required | receipt → intent → initial event; no task/gateway/scientific writes | PG-I: `tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_researcher_and_exact_agent_use_common_boundary`, `tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_failure_rolls_back_all_three_effects`; AUDIT |
| Q2 exact ordered 23-table SHARE, project/command/actor/task/version/execution keys; actor/task/step/version/availability/intent row locks | SqlAlchemyExecutionRepository.lock_write; explicit SELECT FOR UPDATE, including immutable AgentVersion | U-A: `tests/unit/phase3/test_agent_execution_repository.py::test_ordered_intent_prefix_and_keys`; PG-I/PG-T: `tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_observed_wait_rechecks_intent_authority` |
| Q2 fresh authority/time after each wait and before commit; live credential/member/availability denial | Post-wait READ callbacks; final write authorization | PG-I: `tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_membership_revocation_during_first_share_wait`, `tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_availability_change_at_existing_s1_writer_wait`; PG-T first_share and second_key temporal nodes |
| Q2 READ COMMITTED, autoflush off, startup lock/statement timeouts | Existing startup-timeout factory reused by agent_execution_uow_factory | PG-I real command/guard runs; U-A ordered lock node; `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards` |
| Q2 atomic receipt-first ownership; force constraints then fresh final credentials | One UoW; receipt/event IDs allocated only for a new write, stable across retries | PG-I: `tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_failure_rolls_back_all_three_effects`; U-A: `tests/unit/phase3/test_agent_execution_repository.py::test_bounded_whole_transaction_retry_and_no_timeout_retry` |
| Q2 at most three 40001/40P01 retries; no automatic timeout retry; uncertain-commit reconciliation | Existing Agent UoW normalization extended before generic fallbacks | U-A: `tests/unit/phase3/test_agent_execution_repository.py::test_bounded_whole_transaction_retry_and_no_timeout_retry`; PG-I: `tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_intent_after_loss_and_uncertain_commit` |
| Q2 actual coexistence with accepted writers, no changed gateway/task/B02 wrapper | Independent accepted S1, task, gateway-policy and Phase 2 source commands | PG-I: `tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_same_command_revision_and_existing_writer_races`, `tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_availability_change_at_existing_s1_writer_wait`, `tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_unchanged_task_writer_coexistence`, `tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_unchanged_gateway_writer_coexistence`, `tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_unchanged_phase2_writer_coexistence`; no deadlock-freedom claim |
| Q3.1 exact columns, nullability, no defaults, finite instants, explicit schemes | Migration 0081 and inert internal models; typed DTOs | PG-I: `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_exact_intent_schema_and_scoped_foreign_keys`, `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_literal_checks_indexes_and_receipt_deferral`; U-A: `tests/architecture/test_pr3_02_s2_boundaries.py::test_inert_persistence_metadata_matches_intent_values` |
| Q3.2 all 15 named keys/FKs, same-project/task/step/version/Agent scope, two deferred receipt FKs and eight additional indexes | Exact frozen intent DDL | PG-I: same two schema nodes; PG-R: `tests/integration/phase2/test_pr2_20_migrations.py::test_populated_source_evidence_conclusion_placement_review_decision_head_noop`; PG-N catalog |
| Q3.3 all 12 listed CHECKs and exact receipt shape; actual baseline CHECK names/definitions checked before replacement | BASELINE_CHECKS drift refusal; only two old receipt CHECKs replaced | PG-I: `tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_empty_upgrade_and_single_head`, `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_literal_checks_indexes_and_receipt_deferral`, `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards` |
| Q3.4 cjson/value_digest helpers, Python-only numeric rejection, SQL NULL diagnostic | Pure normalized JSONB serializer; no SQL numeric spelling rejection | U-A: `tests/unit/phase3/test_agent_execution_contracts.py::test_closed_intent_command_and_literal_vectors`; PG-I: `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_python_postgresql_intent_material_parity` |
| Q3.4 input_material exact typed sealed pins; no fabricated empty success for missing intent | Exact task/selected-step typed readers; frozen scope/hash validation | PG-I: `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_unresolved_input_material_diagnostic`, `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards`; `tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_selected_step_and_typed_inputs_preserve_both_owners` |
| Q3.4 preheld and insertion guards; initial event literal/caller/time and three-row closure | Seven S2 helpers/guards; two forward S1 function replacements; four new triggers | PG-I: `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_named_insertion_and_receipt_guards`, `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_historical_receipt_cannot_attach_new_history`; `tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_created_intent_through_common_application_boundary` |
| Q3.4 privilege refreeze: normal role has no direct INSERT/UPDATE/DELETE/TRUNCATE | No grants on intent tables; revoke PUBLIC and any explicit/default non-owner grants found at upgrade | PG-I: `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables` (eight SQLSTATE 42501 cases). No xmax/holder-view lock-mode verification |
| Q3.4 immutable UPDATE/DELETE, including no-op; no late history | pr302s2_immutable and freshness guards | PG-I: `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_owning_role_immutable_including_noop`, `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_historical_receipt_cannot_attach_new_history` |
| Q3.4 preserve S1 HUMAN OWNER insertion/final behavior; staged S2 HUMAN RESEARCHER/exact Agent | Early operation dispatch before either S1 OWNER predicate | PG-I: `tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_populated_upgrade_preserves_history` exercises all three S1 operations at 0081; `tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_researcher_and_exact_agent_use_common_boundary`; PG-R S1 suites |
| Q3.5 exact SQLSTATE/tag translation; no new public ErrorCode or foreign-service trigger | Intent normalization precedes generic Agent fallback | U-A: `tests/unit/phase3/test_agent_execution_repository.py::test_intent_diagnostics_are_translated_by_exact_state_and_tag`; PG-I direct named-guard diagnostics and Application denial nodes; AUDIT |
| Q3 forward-only clean/populated upgrade; one head; no fabricated history; downgrade refuses before changes, even empty | One child migration; catalog/name drift check before DDL | PG-I: `tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_empty_upgrade_and_single_head`, `tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_populated_upgrade_preserves_history`, `tests/integration/phase3/test_pr3_02_s2_intent_migration.py::test_downgrade_refuses_before_change`; PG-R historical head/catalog nodes |
| Q4 eight-key envelope/six-key arguments, explicit nulls, strict scalar/UUID/revision types, duplicate/unknown JSON key rejection | Separate closed intent contracts and parser; list-of-pairs is not an arguments object | U-A: `tests/unit/phase3/test_agent_execution_contracts.py::test_create_parser_closed_fields_and_envelope`, `tests/unit/phase3/test_agent_execution_contracts.py::test_strict_revision`, `tests/unit/phase3/test_agent_execution_contracts.py::test_closed_intent_command_and_literal_vectors` |
| Q4 V01/V07/V08/V09/V13/V14/V18 independent fixtures, input sorting/duplicates, NULL hash versus DB admission, byte/value distinction | Standard-library vector builder and literal JSON; source identity checked; S1 serializer/fixtures unchanged | U-A: `tests/unit/phase3/test_agent_execution_contracts.py::test_independent_vector_source_identity`, `tests/unit/phase3/test_agent_execution_contracts.py::test_intent_binding_and_harness_pins`, `tests/unit/phase3/test_agent_execution_contracts.py::test_harness_byte_value_hashes_and_ordinal_pins`, existing S1/B02/scientific unit fixtures; PG-I material parity and selected-step input node |
| Q4 actual retained harness/config bytes verified before write locks; frozen project/config/input pins rechecked inside; executable pin intake fails closed when unconfigured | _preflight, immutable binding tuple, local configured pin resolver, DenyAgentVerifier default | PG-I: `tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_denials_preserve_closed_execution_gate[pins-FROZEN_REFERENCE_REQUIRED]`, `tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_selected_step_and_typed_inputs_preserve_both_owners`; U-A harness node. Test resolver intake is not a claim of production Agent/provider verifier deployment |
| Q5 Human OWNER/RESEARCHER and exact enrolled Agent common Application boundary; other/revoked/untrusted caller denied before disclosure | VerifiedPrincipal plus durable current READ and S2 intent caller | PG-I: `tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_researcher_and_exact_agent_use_common_boundary`, `tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_intent_denials_preserve_closed_execution_gate`; `tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_current_entitlement_precedes_intent_disclosure`, `tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_other_caller_cannot_replay_receipt` |
| Q5 original receipt/IDs/time/history on exact replay after retire/archive/cancel/revision advance; changed material conflicts; no new IDs | Saved receipt check before new-write admission/byte failure; no UUID allocation on replay | PG-I: `tests/integration/phase3/test_pr3_02_s2_intent_execution.py::test_created_intent_through_common_application_boundary` installs a UUID-allocation failure sentinel for replay; `tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_current_entitlement_precedes_intent_disclosure`, `tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_saved_intent_after_loss_and_uncertain_commit` |
| Q5 bounded ordered get/list/reconciliation in one REPEATABLE READ READ ONLY snapshot, immutable saved task revision | begin_formal_read; cursor/limit 1..100/default 50; no write/advisory/SHARE lock path | U-A: `tests/unit/phase3/test_agent_execution_contracts.py::test_intent_query_and_receipt_shapes`; PG-I: `tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_queries_are_coherent_bounded_snapshots`, `tests/integration/phase3/test_pr3_02_s2_intent_replay.py::test_other_caller_cannot_replay_receipt` |
| Q6/Q7 intent is not producer provenance; existing preview denial retained | No producer linkage or preview change | AUDIT; PG-R: `tests/integration/phase3/test_pr3_05_promotion_validation.py` |
| §4 A1 Application/Domain boundaries and exact inert metadata; Appendix H mechanical head/catalog maintenance | No new transport, framework, runtime dependency or generic provenance reference | U-A: `tests/architecture/test_pr3_02_s2_boundaries.py::test_intent_only_application_boundary`, `tests/architecture/test_pr3_02_s2_boundaries.py::test_inert_persistence_metadata_matches_intent_values`; H-U and PG-R; AUDIT |


## Deferred inventory: every §2 row remains absent

Confirmed by AUDIT plus the intent-only architecture nodes; this is absence of
new implementation, not a claim that deferred positive behavior was tested.

| Frozen deferred row | Confirmed disposition |
| --- | --- |
| Q1 lifecycle/activation | No transition command, RUNNING/start/resume/waits/outcomes/failure/cancel/recovery/controller takeover; no admitted edge, including CREATED→CANCELLED |
| Q1 linked gateway | No S2 spend, invocation/reservation/settlement link, AGENT_EXECUTION_FAKE mode, capability_invocations.agent_execution_id or S2ConsumerContext |
| Q1 gates | No PR3-01 gate/execution_enabled change or s2_admission switch |
| Q2 composition | No gateway/safety/B02 composition key, linked capture lock protocol, cross-command effect ownership or promotion write upgrade |
| Q3 promotion tables/results | No agent_promotion_records, agent_promotion_outputs, result_promotion_id or output result link |
| Q3 invocation/capture/lifecycle columns | No gateway/capture adjunct or trigger replacement; no result/trace/memory/output/summary/error/start/finish/controller or future-only composite execution key |
| Q4 transition/promotion material | No transition/promotion/candidate/B02/output/new-mode material or AgentPromotionPolicySnapshot; deferred vector IDs V02–V06, V10–V12 and V15–V17 are not computed or counted as passing |
| Q5 running/promotion authority | No controller/dispatch/outcome/settlement/in-flight recovery/promotion authority or AGENT_POLICY; no policy snapshot created |
| Q6 producer/capture attribution | No producing_execution_id, S2CaptureContext, invocation/output/capture link, producer assertion, B02 owning-command link or atomic promotion |
| Q6 promotion→capture project FK question | Remains deferred; no weak/generic substitute or new FK installed |
| Q7 PR3-05 read/preview/save | No producer-read/preview extension, saving, D1 or D2-C work; S2_PRODUCER_PROVENANCE_UNVERIFIED stays in accepted code |
| Q1/Q6 later positive acceptance | RUNNING→SUCCEEDED→promotion, output XOR, capture/finish/cancel races, promotion rollback and scientific producer attribution are NOT RUN / NOT IMPLEMENTED, never credited to intent denial tests |
| R1 source-link revocation | Not implemented or tested as an allowed mutation; all accepted migration bytes, including P17D1, remain unchanged. Independent Phase 2 *source creation* in coexistence testing is not revocation |

The independent gateway coexistence test registers an already-supported gateway
policy on its own task; it makes no invocation and spends nothing. Other writer
coexistence tests exercise their unchanged Application commands, not S2 linkage.

## Iteration record (not final passes)

Development found and corrected PL/pgSQL record/query-alias collisions in the new
intent guard and the forward S1 receipt function, missing advisory preparation in
a negative test, a normal-role inspection of an ungranted new table, and a test
fixture diagnostic that shadowed the registered-version object. Earlier focused
runs reported 50 passed/3 failed, then 57 passed/1 failed; the diagnostic fixture
attempt of the required PostgreSQL command reported 2 passed/59 setup errors.
Those attempts are failures, not acceptance evidence. The successful PG-I command
below is a fresh complete rerun.

The supplemental runs initially reported 17 passed/1 failed (a stale head-parent
assertion) and 44 passed/1 failed (the exact catalog allowance omitted PostgreSQL
18's generated NOT NULL constraint rows). PG-N confirmed the actual names; only
the test head expectation and exact catalog allowance changed. A focused repair
run passed 9 tests; the complete supplemental commands were then repeated below.
No migration or guard was weakened. The initial source whitespace audit found two
whitespace-only lines inside new SQL literals; they were removed, and AUDIT was
rerun. Production pin/verifier intake remains fail-closed, as the frozen pack
requires; tests do not assert provider execution or production verifier rollout.

## Prior implementation runs: raw verification commands and outputs

Each command is a separate invocation. Outputs below are copied from captured
stdout/stderr, including version notices and warnings, with the command's actual
exit code. The baseline development output is not substituted for these runs.

### LINT

```sh
uv run ruff check .
```

Raw stdout/stderr:

```text
All checks passed!
Exit code: 0
```

### FORMAT

```sh
uv run ruff format --check .
```

Raw stdout/stderr:

```text
947 files already formatted
Exit code: 0
```

### TYPE

```sh
uv run pyright
```

Raw stdout/stderr:

```text
0 errors, 0 warnings, 0 informations
WARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`

Exit code: 0
```

### HEAD

```sh
uv run alembic heads
```

Raw stdout/stderr:

```text
0081_agent_execution_intents (head)
Exit code: 0
```

### U-A

```sh
uv run pytest -o addopts='' -q -rfE tests/unit/phase3 tests/architecture tests/unit/architecture
```

Raw stdout/stderr:

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
........................................................................ [ 61%]
........................................................................ [ 66%]
........................................................................ [ 71%]
........................................................................ [ 76%]
........................................................................ [ 81%]
........................................................................ [ 86%]
........................................................................ [ 91%]
........................................................................ [ 96%]
................................................                         [100%]
=============================== warnings summary ===============================
tests/architecture/test_b02_strategy_promotion_boundaries.py: 1 warning
tests/architecture/test_b04_boundaries.py: 1 warning
tests/architecture/test_b05_review_boundaries.py: 1 warning
tests/architecture/test_b15_package_boundaries.py: 1 warning
tests/architecture/test_b20_screening_boundaries.py: 1 warning
tests/architecture/test_basic_approval.py: 1 warning
tests/architecture/test_pr2_19_boundaries.py: 43 warnings
tests/architecture/test_pr3_02_s1_boundaries.py: 1 warning
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane331/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1416 passed, 50 warnings in 26.48s
Exit code: 0
```

### PG-I

```sh
uv run pytest -o addopts='' -q -rfE tests/integration/phase3/test_pr3_02_s2_intent_*.py
```

Raw stdout/stderr:

```text
....................................................................     [100%]
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py: 23 warnings
tests/integration/phase3/test_pr3_02_s2_intent_execution.py: 38 warnings
tests/integration/phase3/test_pr3_02_s2_intent_guards.py: 60 warnings
tests/integration/phase3/test_pr3_02_s2_intent_migration.py: 12 warnings
tests/integration/phase3/test_pr3_02_s2_intent_replay.py: 8 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane331/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
68 passed, 141 warnings in 64.91s (0:01:04)
Exit code: 0
```

### H-U

```sh
uv run pytest -o addopts='' -q -rfE tests/unit/test_task12_migration_history.py tests/unit/test_batch_c_migration_history.py tests/unit/test_ci_migration_head.py tests/unit/phase2/test_pr2_04_static_acceptance.py tests/unit/phase2/test_pr2_04_r8a_host_topology.py tests/unit/phase2/test_pr2_20_inventory.py
```

Raw stdout/stderr:

```text
..................                                                       [100%]
=============================== warnings summary ===============================
tests/unit/test_task12_migration_history.py::test_task12_preserves_every_historical_migration_byte_and_exact_child
tests/unit/test_batch_c_migration_history.py::test_batch_c_linear_history_and_frozen_lane_sql
tests/unit/test_ci_migration_head.py::test_ci_migration_head_assertion_matches_repository_head
tests/unit/phase2/test_pr2_04_static_acceptance.py::test_candidate_static_gates_and_inherited_formatter_delta
tests/unit/phase2/test_pr2_04_r8a_host_topology.py::test_r8a_actual_migration_graph_and_frozen_bytes
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane331/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
18 passed, 5 warnings in 9.56s
Exit code: 0
```

### PG-R

```sh
uv run pytest -o addopts='' -q -rfE tests/integration/phase2/test_pr2_03_review_guards.py::test_remediation_child_upgrade_empty_downgrade_and_unique_head tests/integration/phase2/test_pr2_04_execution_migration.py::test_pr2_04_upgrade_adds_exact_tables_and_unique_head tests/integration/phase2/test_pr2_04_migration_coverage.py::test_upgrade_paths_preserve_complete_existing_rows_and_exact_table_delta tests/integration/phase2/test_pr2_04_migration_coverage.py::test_historical_migration_bytes_match_frozen_accepted_tree tests/integration/phase2/test_pr2_15_decision_schema.py::test_0042_exact_minimal_schema_fks_indexes_and_no_extra_tables tests/integration/phase2/test_pr2_17_authorship_schema.py::test_install_upgrade_exact_catalog_and_one_head tests/integration/phase2/test_revision_action.py::test_empty_additive_upgrade_downgrade_preserves_predecessor_catalog tests/integration/phase3/test_pr3_00_bootstrap.py::test_single_head_and_exact_parent tests/integration/phase3/test_pr3_01_migration.py::test_clean_and_populated_upgrade_and_downgrade_refusal tests/integration/phase3/test_pr3_02_s1_migration.py::test_empty_upgrade_and_refusal tests/integration/phase3/test_pr3_03_migration.py::test_empty_base_upgrade_and_downgrade_refusal tests/integration/phase3/test_pr3_04_migration.py::test_forward_upgrade_and_refusal tests/integration/phase2/test_pr2_20_migrations.py::test_populated_source_evidence_conclusion_placement_review_decision_head_noop tests/integration/phase3/test_pr3_02_s1_application.py tests/integration/phase3/test_pr3_02_s1_replay.py tests/integration/phase3/test_pr3_05_promotion_validation.py
```

Raw stdout/stderr:

```text
.............................................                            [100%]
=============================== warnings summary ===============================
tests/integration/phase2/test_pr2_03_review_guards.py: 5 warnings
tests/integration/phase2/test_pr2_04_execution_migration.py: 3 warnings
tests/integration/phase2/test_pr2_04_migration_coverage.py: 9 warnings
tests/integration/phase2/test_pr2_15_decision_schema.py: 4 warnings
tests/integration/phase2/test_pr2_17_authorship_schema.py: 12 warnings
tests/integration/phase2/test_revision_action.py: 6 warnings
tests/integration/phase3/test_pr3_00_bootstrap.py: 1 warning
tests/integration/phase3/test_pr3_01_migration.py: 10 warnings
tests/integration/phase3/test_pr3_02_s1_migration.py: 4 warnings
tests/integration/phase3/test_pr3_03_migration.py: 3 warnings
tests/integration/phase3/test_pr3_04_migration.py: 9 warnings
tests/integration/phase2/test_pr2_20_migrations.py: 6 warnings
tests/integration/phase3/test_pr3_02_s1_application.py: 14 warnings
tests/integration/phase3/test_pr3_02_s1_replay.py: 10 warnings
tests/integration/phase3/test_pr3_05_promotion_validation.py: 2 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane331/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
45 passed, 98 warnings in 33.43s
Exit code: 0
```

### PG-T

```sh
uv run pytest -o addopts='' -q -rfE -s 'tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_observed_wait_rechecks_intent_authority[first_share]' 'tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_observed_wait_rechecks_intent_authority[second_key]'
```

Raw stdout/stderr:

```text
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
INFO  [researchbase.commands] {"actor_id": "f634e4a4-6781-4686-b38e-923f7a61fb18", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 11.06, "error_code": null, "level": "INFO", "project_id": "046d0b40-5aba-4d50-880a-66a45dee753d", "request_id": "73f74d5a-800f-43fc-aa38-55bf57639467", "result": "success", "rollback": false, "target_id": "046d0b40-5aba-4d50-880a-66a45dee753d", "timestamp": "2026-10-25T16:55:24.393573+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-25T16:55:24.394370+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.75, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-25T16:55:24.394404+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.777, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-25T16:55:24.394423+00:00"}
INFO  [researchbase.commands] {"actor_id": "f634e4a4-6781-4686-b38e-923f7a61fb18", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 5.474, "error_code": null, "level": "INFO", "project_id": null, "request_id": "73f74d5a-800f-43fc-aa38-55bf57639467", "result": "success", "rollback": false, "target_id": "01a173fd-05e8-7810-84e4-526d2f98d824", "timestamp": "2026-10-25T16:55:24.399923+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-25T16:55:24.400414+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.465, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-25T16:55:24.400441+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.489, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a173fd-05ec-7b37-b304-259999421b43", "timestamp": "2026-10-25T16:55:24.400458+00:00"}
INFO  [researchbase.commands] {"actor_id": "f634e4a4-6781-4686-b38e-923f7a61fb18", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.376, "error_code": null, "level": "INFO", "project_id": null, "request_id": "73f74d5a-800f-43fc-aa38-55bf57639467", "result": "success", "rollback": false, "target_id": "01a173fd-05ec-7b37-b304-259999421b43", "timestamp": "2026-10-25T16:55:24.402857+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-25T16:55:24.403215+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.343, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-25T16:55:24.403236+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.362, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a173fd-05ec-7b37-b304-259999421b43", "timestamp": "2026-10-25T16:55:24.403249+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "f634e4a4-6781-4686-b38e-923f7a61fb18", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.574, "error_code": null, "level": "INFO", "project_id": "046d0b40-5aba-4d50-880a-66a45dee753d", "request_id": "bee83797-d252-4e26-8f95-3b1e35b50ac5", "result": "success", "rollback": false, "target_id": "046d0b40-5aba-4d50-880a-66a45dee753d", "timestamp": "2026-10-25T16:55:24.516165+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-25T16:55:24.516787+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.589, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-25T16:55:24.516819+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.613, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-25T16:55:24.516837+00:00"}
INFO  [researchbase.commands] {"actor_id": "f634e4a4-6781-4686-b38e-923f7a61fb18", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 3.994, "error_code": null, "level": "INFO", "project_id": null, "request_id": "bee83797-d252-4e26-8f95-3b1e35b50ac5", "result": "success", "rollback": false, "target_id": "01a173fd-0663-70b2-924c-22f0fd1e2ad6", "timestamp": "2026-10-25T16:55:24.520856+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-25T16:55:24.521282+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.409, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-25T16:55:24.521309+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.431, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a173fd-0666-70ff-8a2a-aff5d1ea8b22", "timestamp": "2026-10-25T16:55:24.521326+00:00"}
INFO  [researchbase.commands] {"actor_id": "f634e4a4-6781-4686-b38e-923f7a61fb18", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.322, "error_code": null, "level": "INFO", "project_id": null, "request_id": "bee83797-d252-4e26-8f95-3b1e35b50ac5", "result": "success", "rollback": false, "target_id": "01a173fd-0666-70ff-8a2a-aff5d1ea8b22", "timestamp": "2026-10-25T16:55:24.523672+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-25T16:55:24.524048+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.361, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-25T16:55:24.524071+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.381, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a173fd-0666-70ff-8a2a-aff5d1ea8b22", "timestamp": "2026-10-25T16:55:24.524087+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-25T16:55:24.535372+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-25T16:55:25.237718+00:00"}
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_e75d5e60b8d7400ab282d2280294978a
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_e75d5e60b8d7400ab282d2280294978a
wait evidence first_share {'xact_start': datetime.datetime(2026, 10, 25, 12, 55, 24, 535710, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'query_start': datetime.datetime(2026, 10, 25, 12, 55, 24, 535769, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'observed_at': datetime.datetime(2026, 10, 25, 12, 55, 24, 545936, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'query': 'LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_membership_events, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions, strategy_candidate_captures, strategy_candidate_sources, strategy_hypothesis_admissions, strategy_question_admissions IN SHARE MODE', 'expiry_at': datetime.datetime(2026, 10, 25, 12, 55, 25, 226751, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'lock_wait_started_at': datetime.datetime(2026, 10, 25, 12, 55, 24, 545936, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'lock_acquired_at': datetime.datetime(2026, 10, 25, 12, 55, 25, 235734, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'authorization_checked_at': datetime.datetime(2026, 10, 25, 16, 55, 25, 237496, tzinfo=datetime.timezone.utc)} effects {'agent_execution_instances': 0, 'agent_execution_events': 0, 'agent_command_receipts': 2, 'research_tasks': 1, 'research_task_steps': 2, 'research_task_events': 3, 'research_task_command_receipts': 3, 'budget_reservations': 0, 'budget_usage_records': 0, 'capability_invocations': 0, 'strategy_candidate_captures': 0, 'artifacts': 2, 'artifact_versions': 2}
.INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
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
INFO  [researchbase.commands] {"actor_id": "a371ecd6-3d14-4b8e-892c-bc17c7b58628", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 31.03, "error_code": null, "level": "INFO", "project_id": "84352ad9-c483-4972-b65e-99510eb442ba", "request_id": "99c6a8f5-1845-40d5-a0d9-0a979c62a3f8", "result": "success", "rollback": false, "target_id": "84352ad9-c483-4972-b65e-99510eb442ba", "timestamp": "2026-10-25T16:55:25.931211+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-25T16:55:25.931812+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.559, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-25T16:55:25.931839+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.581, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-25T16:55:25.931854+00:00"}
INFO  [researchbase.commands] {"actor_id": "a371ecd6-3d14-4b8e-892c-bc17c7b58628", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 4.314, "error_code": null, "level": "INFO", "project_id": null, "request_id": "99c6a8f5-1845-40d5-a0d9-0a979c62a3f8", "result": "success", "rollback": false, "target_id": "01a173fd-0bea-741d-b7bd-1dcf46ca90ed", "timestamp": "2026-10-25T16:55:25.936191+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-25T16:55:25.936659+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.448, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-25T16:55:25.936684+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.469, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a173fd-0bed-76e0-a6cc-85d4e0fa9d38", "timestamp": "2026-10-25T16:55:25.936700+00:00"}
INFO  [researchbase.commands] {"actor_id": "a371ecd6-3d14-4b8e-892c-bc17c7b58628", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.468, "error_code": null, "level": "INFO", "project_id": null, "request_id": "99c6a8f5-1845-40d5-a0d9-0a979c62a3f8", "result": "success", "rollback": false, "target_id": "01a173fd-0bed-76e0-a6cc-85d4e0fa9d38", "timestamp": "2026-10-25T16:55:25.939189+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-25T16:55:25.939693+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.491, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-25T16:55:25.939718+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.51, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a173fd-0bed-76e0-a6cc-85d4e0fa9d38", "timestamp": "2026-10-25T16:55:25.939733+00:00"}
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
INFO  [researchbase.commands] {"actor_id": "a371ecd6-3d14-4b8e-892c-bc17c7b58628", "application_env": "development", "command_name": "create_artifact", "correlation_id": null, "duration_ms": 1.703, "error_code": null, "level": "INFO", "project_id": "84352ad9-c483-4972-b65e-99510eb442ba", "request_id": "daf929c9-9648-48b5-a218-e4e6e813e639", "result": "success", "rollback": false, "target_id": "84352ad9-c483-4972-b65e-99510eb442ba", "timestamp": "2026-10-25T16:55:26.052760+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-25T16:55:26.053447+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact", "correlation_id": null, "duration_ms": 0.651, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-25T16:55:26.053477+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.674, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-25T16:55:26.053494+00:00"}
INFO  [researchbase.commands] {"actor_id": "a371ecd6-3d14-4b8e-892c-bc17c7b58628", "application_env": "development", "command_name": "create_artifact_version", "correlation_id": null, "duration_ms": 4.191, "error_code": null, "level": "INFO", "project_id": null, "request_id": "daf929c9-9648-48b5-a218-e4e6e813e639", "result": "success", "rollback": false, "target_id": "01a173fd-0c64-70c5-8be2-7a4c4c02fb4b", "timestamp": "2026-10-25T16:55:26.057708+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-25T16:55:26.058184+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.459, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-25T16:55:26.058212+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.481, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a173fd-0c67-7653-ad89-2afd7988bdf9", "timestamp": "2026-10-25T16:55:26.058228+00:00"}
INFO  [researchbase.commands] {"actor_id": "a371ecd6-3d14-4b8e-892c-bc17c7b58628", "application_env": "development", "command_name": "freeze_artifact_version", "correlation_id": null, "duration_ms": 2.318, "error_code": null, "level": "INFO", "project_id": null, "request_id": "daf929c9-9648-48b5-a218-e4e6e813e639", "result": "success", "rollback": false, "target_id": "01a173fd-0c67-7653-ad89-2afd7988bdf9", "timestamp": "2026-10-25T16:55:26.060569+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-25T16:55:26.060974+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "get_artifact_version", "correlation_id": null, "duration_ms": 0.394, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": null, "timestamp": "2026-10-25T16:55:26.060994+00:00"}
INFO  [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "project_write_result", "correlation_id": null, "duration_ms": 0.411, "error_code": null, "level": "INFO", "project_id": null, "request_id": null, "result": "success", "rollback": false, "target_id": "01a173fd-0c67-7653-ad89-2afd7988bdf9", "timestamp": "2026-10-25T16:55:26.061007+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": null, "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-25T16:55:26.073375+00:00"}
ERROR [researchbase.commands] {"actor_id": null, "application_env": "development", "command_name": "unknown", "correlation_id": null, "duration_ms": 0, "error_code": "FORBIDDEN", "level": "ERROR", "project_id": null, "request_id": null, "result": "failure", "rollback": true, "target_id": null, "timestamp": "2026-10-25T16:55:26.771429+00:00"}
DISPOSABLE_DROPPED: researchbase_pr212_test_e75d5e60b8d7400ab282d2280294978a
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_4eddd3bccdf14706aa2e114eb18861b2
INTENT_PG_IDENTITY 18.6 (Homebrew) researchbase researchbase_pr212_test_4eddd3bccdf14706aa2e114eb18861b2
wait evidence second_key {'xact_start': datetime.datetime(2026, 10, 25, 12, 55, 26, 73705, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'query_start': datetime.datetime(2026, 10, 25, 12, 55, 26, 79003, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'observed_at': datetime.datetime(2026, 10, 25, 12, 55, 26, 83689, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'query': 'SELECT pg_advisory_xact_lock(hashtextextended($1,0))', 'expiry_at': datetime.datetime(2026, 10, 25, 12, 55, 26, 764323, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'lock_wait_started_at': datetime.datetime(2026, 10, 25, 12, 55, 26, 83689, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'lock_acquired_at': datetime.datetime(2026, 10, 25, 12, 55, 26, 768223, tzinfo=zoneinfo.ZoneInfo(key='America/New_York')), 'authorization_checked_at': datetime.datetime(2026, 10, 25, 16, 55, 26, 770851, tzinfo=datetime.timezone.utc)} effects {'agent_execution_instances': 0, 'agent_execution_events': 0, 'agent_command_receipts': 2, 'research_tasks': 1, 'research_task_steps': 2, 'research_task_events': 3, 'research_task_command_receipts': 3, 'budget_reservations': 0, 'budget_usage_records': 0, 'capability_invocations': 0, 'strategy_candidate_captures': 0, 'artifacts': 2, 'artifact_versions': 2}
.DISPOSABLE_DROPPED: researchbase_pr212_test_4eddd3bccdf14706aa2e114eb18861b2

=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_observed_wait_rechecks_intent_authority[first_share]
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_observed_wait_rechecks_intent_authority[first_share]
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_observed_wait_rechecks_intent_authority[second_key]
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_observed_wait_rechecks_intent_authority[second_key]
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane331/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
2 passed, 4 warnings in 3.09s
Exit code: 0
```

### PG-N

```sh
uv run python - <<'PY'
from tests.disposable_postgres import disposable_database
from tests.integration.phase2.pr2_20_support import upgrade
from sqlalchemy import create_engine,text
with disposable_database("researchbase_pr212_test_") as url:
    upgrade(url)
    engine=create_engine(url)
    with engine.connect() as conn:
        for row in conn.execute(text("SELECT c.relname,k.conname,k.contype FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid WHERE c.relname IN ('agent_execution_instances','agent_execution_events') ORDER BY 1,2")):
            print(tuple(row))
    engine.dispose()
PY
```

Raw stdout/stderr:

```text
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
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Running upgrade 0080_capability_gateway -> 0081_agent_execution_intents, PR3-02-S2 frozen intent-only delta; accepted migration bytes remain unchanged.
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_c09afe2b2bdd4af4ab8339cb0270d60e
('agent_execution_events', 'agent_execution_events_actor_id_not_null', 'n')
('agent_execution_events', 'agent_execution_events_execution_id_not_null', 'n')
('agent_execution_events', 'agent_execution_events_id_not_null', 'n')
('agent_execution_events', 'agent_execution_events_new_status_not_null', 'n')
('agent_execution_events', 'agent_execution_events_occurred_at_not_null', 'n')
('agent_execution_events', 'agent_execution_events_reason_not_null', 'n')
('agent_execution_events', 'agent_execution_events_receipt_id_not_null', 'n')
('agent_execution_events', 'agent_execution_events_sequence_not_null', 'n')
('agent_execution_events', 'pr302s2_event_actor_fk', 'f')
('agent_execution_events', 'pr302s2_event_execution_fk', 'f')
('agent_execution_events', 'pr302s2_event_execution_uq', 'u')
('agent_execution_events', 'pr302s2_event_id_ck', 'c')
('agent_execution_events', 'pr302s2_event_initial_ck', 'c')
('agent_execution_events', 'pr302s2_event_pk', 'p')
('agent_execution_events', 'pr302s2_event_reason_ck', 'c')
('agent_execution_events', 'pr302s2_event_receipt_fk', 'f')
('agent_execution_events', 'pr302s2_event_receipt_uq', 'u')
('agent_execution_events', 'pr302s2_event_time_ck', 'c')
('agent_execution_instances', 'agent_execution_instances_actor_id_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_agent_version_id_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_created_at_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_harness_artifact_version_id_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_harness_content_hash_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_harness_hash_scheme_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_id_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_input_ref_hash_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_input_ref_hash_scheme_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_project_id_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_research_task_id_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_revision_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_status_not_null', 'n')
('agent_execution_instances', 'agent_execution_instances_task_revision_at_creation_not_null', 'n')
('agent_execution_instances', 'pr302s2_exec_actor_fk', 'f')
('agent_execution_instances', 'pr302s2_exec_harness_fk', 'f')
('agent_execution_instances', 'pr302s2_exec_hashes_ck', 'c')
('agent_execution_instances', 'pr302s2_exec_id_ck', 'c')
('agent_execution_instances', 'pr302s2_exec_pk', 'p')
('agent_execution_instances', 'pr302s2_exec_project_fk', 'f')
('agent_execution_instances', 'pr302s2_exec_revision_ck', 'c')
('agent_execution_instances', 'pr302s2_exec_schemes_ck', 'c')
('agent_execution_instances', 'pr302s2_exec_status_ck', 'c')
('agent_execution_instances', 'pr302s2_exec_step_fk', 'f')
('agent_execution_instances', 'pr302s2_exec_task_fk', 'f')
('agent_execution_instances', 'pr302s2_exec_task_revision_ck', 'c')
('agent_execution_instances', 'pr302s2_exec_time_ck', 'c')
('agent_execution_instances', 'pr302s2_exec_version_fk', 'f')
DISPOSABLE_DROPPED: researchbase_pr212_test_c09afe2b2bdd4af4ab8339cb0270d60e
Exit code: 0
```

### AUDIT

```sh
uv run python tmp/s2_scope_audit.py
```

Raw stdout/stderr:

```text
Protected bytes unchanged: 82 accepted migrations; dependencies, freeze, public errors, closed task gate, gateway, safety and producer-preview paths.
Exact intent delta: 2 tables; 2 nullable receipt links; 9 allowed functions; no deferred identifiers.
Untracked deliverables checked for trailing whitespace and final newline: 17 files.
Migration SHA-256: 142c7a9061785a971d7043667041cf5368be24e38069c59900640d13c2259e52
Exit code: 0
```

### AUDIT command source

The audit script used above is reproduced for review/reproduction:

```python
import ast
import hashlib
import re
import subprocess
from pathlib import Path

accepted = subprocess.check_output(['git', 'ls-files', 'migrations/versions/*.py'], text=True).splitlines()
protected = accepted + [
    'pyproject.toml', 'uv.lock', 'docs/phase3/PR3-02-S2-contract-freeze.md',
    'src/researchbase/foundation/errors.py',
    'src/researchbase/agent_runtime/domain/research_task.py',
    'src/researchbase/agent_runtime/application/research_task.py',
    'src/researchbase/agent_runtime/application/capability_gateway.py',
    'src/researchbase/persistence/capability_gateway_repository.py',
    'src/researchbase/agent_runtime/application/task_safety.py',
    'src/researchbase/persistence/task_safety_repository.py',
    'src/researchbase/agent_runtime/application/promotion_context.py',
]
for name in protected:
    original = subprocess.check_output(['git', 'show', f'HEAD:{name}'])
    assert Path(name).read_bytes() == original, name
path = Path('migrations/versions/0081_agent_execution_intents.py')
module = ast.parse(path.read_text())
constants = {n.targets[0].id: ast.literal_eval(n.value) for n in module.body if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)}
ddl = constants['DDL']
assert re.findall(r'CREATE TABLE (\w+)', ddl) == ['agent_execution_instances', 'agent_execution_events']
assert re.findall(r'ADD COLUMN (\w+)', ddl) == ['result_execution_id', 'result_execution_event_id']
functions = set(re.findall(r'CREATE(?: OR REPLACE)? FUNCTION (\w+)', constants['FUNCTIONS']))
assert functions == {'pr302s2_cjson', 'pr302s2_value_digest', 'pr302s2_input_material', 'pr302s2_preheld', 'pr302s2_execution_guard', 'pr302s2_event_guard', 'pr302s2_immutable', 'pr302_receipt_guard', 'pr302_receipt_complete'}
for forbidden in ('agent_promotion_records', 'agent_promotion_outputs', 'producing_execution_id', 'result_promotion_id', 'AGENT_EXECUTION_FAKE', 'S2ConsumerContext', 'S2CaptureContext', 's2_admission', 'AGENT_POLICY'):
    assert forbidden not in ddl + constants['FUNCTIONS'], forbidden
new_files = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], text=True).splitlines()
for name in new_files:
    data = Path(name).read_text()
    assert data.endswith('\n') and all(line == line.rstrip() for line in data.splitlines()), name
print(f'Protected bytes unchanged: {len(accepted)} accepted migrations; dependencies, freeze, public errors, closed task gate, gateway, safety and producer-preview paths.')
print('Exact intent delta: 2 tables; 2 nullable receipt links; 9 allowed functions; no deferred identifiers.')
print(f'Untracked deliverables checked for trailing whitespace and final newline: {len(new_files)} files.')
print('Migration SHA-256:', hashlib.sha256(path.read_bytes()).hexdigest())
```

## Independent active vector identities

Builder source SHA-256: `d43ef1059440d2fdf2f71a5d2296d6d21b4a44ac69dd28a44cbf2aa98802e93d`. The builder uses only Python standard-library JSON and hashlib, without proposed serializers, SQL helpers or stored output. Literal values, canonical UTF-8 strings and expected digests are in `tests/fixtures/phase3/intent_vectors.json`. Rejection vectors are literal cases in the linked unit nodes; the SQL NULL case belongs to PG-I.

| Fixture | Canonical value SHA-256 | Retained byte SHA-256, when distinct material is supplied |
| --- | --- | --- |
| V01 | `aca0d9bdc9cea1de0b42ff15657629f6e3a6a1127e140a78f2f9a7d8eeceb3ed` | — |
| V08_V09 | `0f51e4d55f3f50a07f555cf3507109d95ecec09ee739f925993c6f185ca2921d` | — |
| V09_empty | `13ac2a6d9fe780ebd19fced4f2e275505a2772443d78ac2ea6de2ce297f85ba6` | — |
| V13_unicode | `9c8e7df4716d7dd0c1bbb6020cd7d86c9044262c3ef8229e1d79dbd52a32153b` | — |
| V13_harness_compact | `86f2771b79fb7957aed5184ed42504e9bb82565959897624293b41c77de58887` | `86f2771b79fb7957aed5184ed42504e9bb82565959897624293b41c77de58887` |
| V13_harness_spaced | `86f2771b79fb7957aed5184ed42504e9bb82565959897624293b41c77de58887` | `f6aa6637c7c2b116cfc0f6c7df2dde18b7f920d0117ac4587a336d904114b287` |
| V14_changed_pin | `bc182bac58afe0e109be9df476ee192563b372ac55e7205b4b8093d3ac7d59ce` | `bc182bac58afe0e109be9df476ee192563b372ac55e7205b4b8093d3ac7d59ce` |


## Completion boundary

All seven requested focused commands have observed results, including the final
diff check appended below. Required unit/architecture: 1,416 passed; intent
PostgreSQL PG-I: 68 passed; no failures or skips in either command. Supplemental
H-U: 18 passed; PG-R: 45 passed; PG-T: 2 passed. Counts overlap deliberately and
are not summed into a unique-test or full-suite count. Warnings are the existing
Alembic path_separator deprecation; Pyright's separate newer-version notice did
not upgrade any dependency.

Full suite / external check-loop output: **NOT RUN by this implementing agent**,
not available here and not relabeled as passing. Independent implementation
review, external CI and owner acceptance remain outside this evidence. No later
execution/promotion/provider work is implemented or credited by intent tests.

### DIFF — final documentation included

```sh
git diff --check HEAD
```

Raw stdout/stderr: empty (zero bytes). Actual exit code: **0**.

`git diff --check HEAD` does not inspect untracked files. AUDIT separately checked
all 17 untracked deliverables for trailing whitespace and a final newline. This
final diff check was repeated after recording this paragraph, with the same empty
output and exit code 0.


## Reviewer remediation and fresh verification (2026-10-25)

This section supersedes the prior implementation run for the reviewed working
copy. Each RR command below is run separately, with its own complete captured
stdout/stderr and exit code. No chained command status or truncated output is
used. The original runs above remain historical evidence; their counts are not
added to these repeated runs.

Changes made for review:

- Q5 authorization: `agent_versions.py` exposes the public Application helper
  `authorize_agent_project`; both services use the same predicate. S1's private
  wrapper delegates without changing its HUMAN OWNER write restriction.
  `AgentExecutionService` no longer constructs another service or calls its
  private `_authorize`. The intent architecture test enforces that boundary.
- L1 explicit locks: `test_ordered_intent_prefix_and_keys` now asserts the entire
  ordered FOR UPDATE statement list, including both actor rows, task, steps,
  Agent version, availability and existing intent. This is an Application SQL
  contract test, not a PostgreSQL lock-mode probe.
- Q2 deliberately broad SHARE prefix: the frozen pack §Q2 opening paragraph
  states, "The 23-table SHARE prefix remains the deliberately broad approved S2
  inventory" and "Do not silently shrink or reorder it." Q2 item 2 provides the
  exact SQL, including projects, actors and artifact_versions. The concurrency
  cost is prescribed by the frozen contract, so no ADR or unapproved lock change
  is introduced. This is a specification citation, not a PostgreSQL observation.
- Q3.4 duplication: `pr302s2_input_material(p_execution uuid)` is frozen as a
  persisted-intent read helper. Its first lookup requires the intent to exist.
  `pr302s2_execution_guard` is BEFORE INSERT and validates NEW before that row
  exists, so calling the persisted helper there would reject every insertion.
  The receipt root already calls the helper on the now-present intent. Q3.4
  freezes exhaustive helper signatures and the BEFORE INSERT trigger; adding
  an overload/shared SQL helper or moving the guard requires a revised delta.
  Therefore the typed input resolution is intentionally retained in both
  contexts. The input parity, named guard, selected-step and receipt-completeness
  tests exercise them; the implementation does not waive either validation.
- Q3.4 staged caller/Agent predicates: its paragraph after the function table
  expressly requires receipt-first durable caller validation, exact Agent/version
  matching against NEW, and complete predicate revalidation at the receipt root.
  The repeated predicates have different available rows and validation times;
  they cannot be replaced with a single earlier authorization result. The frozen
  exhaustive function inventory also precludes an extra SQL authorization helper.
- The requested pg_locks row-lock-mode test is superseded by the binding Q3.4
  refreeze (2026-10-25, t313). Q3.4 says "Database-side verification of the lock
  mode is NOT provided" and specifies SQLSTATE 42501 protection instead. There
  is no such test or claimed passing node. No xmax/holder-view inference is used.
  `test_observed_wait_rechecks_intent_authority` observes real PostgreSQL waits
  through pg_stat_activity and the advancing authorization time, not row lock
  mode. `pr302s2_preheld` uses pg_locks only for the separately frozen TABLE
  SHARE protection. Application SQL below shows the explicit parent FOR UPDATE.

Explicit parent-row locking (production source:
`src/researchbase/persistence/agent_execution_repository.py::lock_write`):

```python
for identity in sorted({command.caller.actor_id, actor} - {None}, key=str):
    self.many("SELECT id FROM actors WHERE id=:id FOR UPDATE", id=identity)
    after_wait()
self.many("SELECT id FROM research_tasks WHERE id=:id FOR UPDATE", id=args.research_task_id)
after_wait()
for step in sorted(self.steps(args.research_task_id), key=lambda s: str(s["id"])):
    self.many("SELECT id FROM research_task_steps WHERE id=:id FOR UPDATE", id=step["id"])
    after_wait()
self.many("SELECT id FROM agent_versions WHERE id=:id FOR UPDATE", id=args.agent_version_id)
after_wait()
self.many(
    "SELECT agent_version_id FROM agent_availability WHERE agent_version_id=:id FOR UPDATE",
    id=args.agent_version_id,
)
after_wait()
self.many(
    "SELECT id FROM agent_execution_instances WHERE id=:id FOR UPDATE", id=args.execution_id
)
after_wait()
```

Fresh-run PostgreSQL attribution (only observed runs below support these claims):

- **RR-07**: required intent PostgreSQL suite, covering clean/populated forward
  upgrade, one head, downgrade refusal, named guards, normal-role SQLSTATE 42501,
  Application create/replay/read/denial/atomicity and real authority-change waits.
- **RR-08**: verbose repeated node output identifying all eight normal-role
  SQLSTATE 42501 cases and four observed-wait cases. The unit SQL-order node in
  the same command asserts explicit FOR UPDATE syntax, not DB lock mode.
- **RR-09**: focused accepted S1 Application/replay regression after extracting
  the shared public helper; S1 authorization behavior must remain unchanged.

Exact evidence nodes:

- `tests/unit/phase3/test_agent_execution_repository.py::test_ordered_intent_prefix_and_keys`
- `tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables`
  (INSERT, UPDATE, DELETE, TRUNCATE × both intent tables; assert SQLSTATE 42501).
- `tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_observed_wait_rechecks_intent_authority`
  (`first_share`, `second_key`, `task_row`, `version_row`; no lock-mode claim).

All commands in this section use exactly:

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
export DATABASE_URL='postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase_lane331'
export RB_TEST_ADMIN_URL='postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres'
export PGOPTIONS='-c jit=off'
```

PostgreSQL fixtures in RR-07/RR-08/RR-09 create disposable lane test databases
using the admin URL; those runs use actual PostgreSQL, not SQLite. No full-suite run, owner acceptance, or
external loop output is claimed.

### RR-01

```sh
git diff --check HEAD
```

Raw stdout/stderr (empty; zero bytes):

```text
Exit code: 0
```

### RR-02

```sh
uv run ruff check .
```

Raw stdout/stderr:

```text
All checks passed!
Exit code: 0
```

### RR-03

```sh
uv run ruff format --check .
```

Raw stdout/stderr:

```text
947 files already formatted
Exit code: 0
```

### RR-04

```sh
uv run pyright
```

Raw stdout/stderr:

```text
0 errors, 0 warnings, 0 informations
WARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`

Exit code: 0
```

### RR-05

```sh
uv run alembic heads
```

Raw stdout/stderr:

```text
0081_agent_execution_intents (head)
Exit code: 0
```

### RR-06

```sh
uv run pytest -o addopts='' -q -rfE tests/unit/phase3 tests/architecture tests/unit/architecture
```

Raw stdout/stderr:

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
........................................................................ [ 61%]
........................................................................ [ 66%]
........................................................................ [ 71%]
........................................................................ [ 76%]
........................................................................ [ 81%]
........................................................................ [ 86%]
........................................................................ [ 91%]
........................................................................ [ 96%]
................................................                         [100%]
=============================== warnings summary ===============================
tests/architecture/test_b02_strategy_promotion_boundaries.py: 1 warning
tests/architecture/test_b04_boundaries.py: 1 warning
tests/architecture/test_b05_review_boundaries.py: 1 warning
tests/architecture/test_b15_package_boundaries.py: 1 warning
tests/architecture/test_b20_screening_boundaries.py: 1 warning
tests/architecture/test_basic_approval.py: 1 warning
tests/architecture/test_pr2_19_boundaries.py: 43 warnings
tests/architecture/test_pr3_02_s1_boundaries.py: 1 warning
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane331/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
1416 passed, 50 warnings in 26.66s
Exit code: 0
```

### RR-07

```sh
uv run pytest -o addopts='' -q -rfE tests/integration/phase3/test_pr3_02_s2_intent_*.py
```

Raw stdout/stderr:

```text
....................................................................     [100%]
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py: 23 warnings
tests/integration/phase3/test_pr3_02_s2_intent_execution.py: 38 warnings
tests/integration/phase3/test_pr3_02_s2_intent_guards.py: 60 warnings
tests/integration/phase3/test_pr3_02_s2_intent_migration.py: 12 warnings
tests/integration/phase3/test_pr3_02_s2_intent_replay.py: 8 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane331/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
68 passed, 141 warnings in 72.19s (0:01:12)
Exit code: 0
```

### RR-08

```sh
uv run pytest -o addopts='' -vv -rfE tests/unit/phase3/test_agent_execution_repository.py::test_ordered_intent_prefix_and_keys tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_observed_wait_rechecks_intent_authority tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables
```

Raw stdout/stderr:

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0 -- /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane331/.venv/bin/python
cachedir: .pytest_cache
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane331
configfile: pyproject.toml
plugins: anyio-4.14.2
collecting ... collected 13 items

tests/unit/phase3/test_agent_execution_repository.py::test_ordered_intent_prefix_and_keys PASSED [  7%]
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_observed_wait_rechecks_intent_authority[first_share] PASSED [ 15%]
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_observed_wait_rechecks_intent_authority[second_key] PASSED [ 23%]
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_observed_wait_rechecks_intent_authority[task_row] PASSED [ 30%]
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py::test_observed_wait_rechecks_intent_authority[version_row] PASSED [ 38%]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[INSERT-agent_execution_instances] PASSED [ 46%]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[INSERT-agent_execution_events] PASSED [ 53%]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[UPDATE-agent_execution_instances] PASSED [ 61%]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[UPDATE-agent_execution_events] PASSED [ 69%]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[DELETE-agent_execution_instances] PASSED [ 76%]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[DELETE-agent_execution_events] PASSED [ 84%]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[TRUNCATE-agent_execution_instances] PASSED [ 92%]
tests/integration/phase3/test_pr3_02_s2_intent_guards.py::test_normal_role_cannot_write_intent_tables[TRUNCATE-agent_execution_events] PASSED [100%]

=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s2_intent_concurrency.py: 8 warnings
tests/integration/phase3/test_pr3_02_s2_intent_guards.py: 16 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane331/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 13 passed, 24 warnings in 15.02s =======================
Exit code: 0
```

### RR-09

```sh
uv run pytest -o addopts='' -q -rfE tests/integration/phase3/test_pr3_02_s1_application.py tests/integration/phase3/test_pr3_02_s1_replay.py
```

Raw stdout/stderr:

```text
........................                                                 [100%]
=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_02_s1_application.py: 14 warnings
tests/integration/phase3/test_pr3_02_s1_replay.py: 10 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane331/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
24 passed, 24 warnings in 19.56s
Exit code: 0
```

Fresh verification result: RR-01 through RR-09 each exited 0. Required
unit/architecture RR-06: 1,416 passed; required intent PostgreSQL RR-07: 68 passed;
verbose evidence RR-08: 13 passed (one unit SQL contract node plus twelve
PostgreSQL cases); accepted S1 PostgreSQL regression RR-09: 24 passed. The
repeated cases overlap; these counts are not summed. RR-10 below repeats the
diff check after incorporating all raw results in this document.

### RR-10 — final evidence-inclusive whitespace check

```sh
git diff --check HEAD
```

Raw stdout/stderr: empty (zero bytes).

```text
Exit code: 0
```

This command is repeated after recording its result, so the final working copy
including this evidence text is checked. No implementation changed after RR-02
through RR-09.
