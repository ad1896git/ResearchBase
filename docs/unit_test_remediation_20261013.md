# Task 2 unit-test remediation

Starting commit: `b8179f17720ca47c3b25ad9d36f6a8e8d4aa79ff` (authorized state through PR2-15, including Task 1 architecture repairs).

Classes: **(a)** code defect; **(b)** obsolete expectation/fixture; **(c)** machine dependency. No tests were deleted, skipped, or marked xfail. Migrations and `docs/architecture/` were not edited. PR2-04 concurrency, serialization, deadlock, and provider cancellation production semantics were not changed.

## Each reported failure

| Failure | Class | Evidence and change |
| --- | --- | --- |
| `foundation/test_errors.py::test_normative_error_codes_are_stable` | b | `ErrorCode` now includes accepted `REVIEW_TARGET_NOT_FROZEN` and `CONFLICT_OF_INTEREST`, used by internal review/Decision. Added both to the literal ordered inventory; retained exact equality. |
| `phase2/test_literature_search_execution_service.py::test_confirmed_provider_cancellation_seals_cancelled_attempt` | b | The accepted provider port says exceptions are not bound confirmation. Old fixture raised `ProviderError(CANCELLED)` and correctly produced UNKNOWN. Fixture now returns `SearchResponse(PROVIDER_CANCELLED)` echoing execution/attempt/request key; still checks CANCELLED attempt and execution with no results. |
| `phase2/test_literature_search_execution_service.py::test_provider_cancellation_without_durable_cancel_intent_fails_closed` | b | Invocation-bound provider confirmation no longer requires C1 (accepted commit `eac3153`). This fixture supplies only an exception, which proves uncertainty, not malformed permanent failure. Renamed to `test_provider_cancellation_exception_without_confirmation_fails_closed`; checks exact UNKNOWN / `PROVIDER_OUTCOME_UNKNOWN` and absence of durable cancel intent. |
| `phase2/test_pr2_04_failed_phase_observations.py::test_failure_before_semantic_facts_records_only_failed_phase_and_never_pass` | a, tooling | Recorder previously omitted traces when failure preceded semantic facts. Fixed `scripts/pr2_04_pytest_evidence.py` to append a failed-phase observation containing only function source location. Unchanged test proves exact trace, no secret canary, and final requirement FAIL. This defect belongs to evidence tooling, not `src/`. |
| `phase2/test_pr2_04_provider_coverage.py::test_attempt_outcome_seals_once_and_internal_reapplication_is_exact[cancelled]` | b | Uncorrelated response is now rejected as malformed. Fixture echoes all required identifiers and supplies the same invocation to internal reapplication. Retains one seal, exact reapplication, unchanged provenance, and rejection of different late material. |
| `phase2/test_pr2_04_r8a_host_topology.py::test_r8a_actual_migration_graph_and_frozen_bytes` | b | Actual single head is `0042_pr2_15_minimal_decision`, parent `0041_pr2_15_review_coordination`; old expectation was 0028. Checks current exact head/parent and byte equality of every migration version through accepted `eac3153` (0028). Historical unauthorized topology mutation cases remain unchanged. |
| `phase2/test_pr2_04_static_acceptance.py::test_candidate_static_gates_and_inherited_formatter_delta` | b | Old gate applies PR2-04 zero-debt assumptions and its whitespace/formatter comparison to later authorized work. Starting tree has 392 Ruff diagnostics, 95 Pyright diagnostics, 114 formatter failures. New pinned registry was generated from a clean Git archive of the starting commit, never the edited tree. Gate runs actual tools, caps exact file/rule/message diagnostic multisets and formatter file set, checks baseline ancestry, retains recovery lineage, and requires all changed Python files to pass Ruff and formatting plus current-range whitespace checks. Existing debt is explicitly inherited, not claimed PASS. |
| `phase2/test_pr2_04_transport_completion.py::test_every_frozen_application_error_maps_through_actual_http_and_cli[VALIDATION_ERROR-create]` | b | Shared CLI fixture incorrectly adds `--execution-id` to create; parser returns `invalid CLI input` before injected Application error. Helper now adds it only for non-create actions. Exact HTTP 422 / CLI 2 and safe message equality remain. |
| Same test `[AUTHENTICATION_REQUIRED-create]` | b | Same fixture defect; preserves HTTP 401 / CLI 3 and exact envelope. |
| Same test `[FORBIDDEN-create]` | b | Same fixture defect; preserves HTTP 403 / CLI 3 and exact envelope. |
| Same test `[NOT_FOUND-create]` | b | Same fixture defect; preserves HTTP 404 / CLI 3 and exact envelope. |
| Same test `[INVALID_STATE_TRANSITION-create]` | b | Same fixture defect; preserves HTTP 409 / CLI 4 and exact envelope. |
| Same test `[IMMUTABLE_RECORD-create]` | b | Same fixture defect; preserves HTTP 409 / CLI 4 and exact envelope. |
| Same test `[CONCURRENT_MODIFICATION-create]` | b | Same fixture defect; preserves HTTP 409 / CLI 4 and exact envelope. |
| Same test `[IDEMPOTENCY_CONFLICT-create]` | b | Same fixture defect; preserves HTTP 409 / CLI 4 and exact envelope. |
| Same test `[PROVENANCE_CLOSURE_VIOLATION-create]` | b | Same fixture defect; preserves HTTP 409 / CLI 5 and exact envelope. |
| Same test `[SEARCH_PLAN_NOT_FROZEN-create]` | b | Same fixture defect; preserves HTTP 409 / CLI 4 and exact envelope. |
| Same test `[ADAPTER_UNAVAILABLE-create]` | b | Same fixture defect; preserves HTTP 503 / CLI 5 and exact envelope. |
| Same test `[ADAPTER_VERSION_MISMATCH-create]` | b | Same fixture defect; preserves HTTP 409 / CLI 4 and exact envelope. All 12 cases retain zero Application/provider effects. |
| `test_ci_migration_head.py::test_ci_migration_head_assertion_matches_repository_head` | b | CI still asserts 0028 despite authorized 0042. Updated CI's literal head; kept the dynamic repository-to-workflow equality test unchanged. |
| `test_m3_runner_binding.py::test_m3_storage_rejects_symlinked_cas` | c | Production validation first lstats `/Users/onephone/ResearchBaseData`, absent here; test never reached its symlink. Injected a private temporary durable root only in this test. First validates real private installation/CAS directories, then proves the symlink is rejected. Deployment bindings remain unchanged. |
| `test_pr15_http.py::test_all_researchbase_error_codes_have_frozen_status_mapping` | a + b | Test inventory omits the two new review codes; production `_STATUS` also omits them and would raise KeyError. Added explicit mappings and literal expectations: review target 409, COI 403. Test exercises every code through actual HTTP error handling. |
| `test_pr16_cli_errors.py::test_all_stable_error_codes_have_cli_exit_mapping` | a + b | Same inventory/production omission in `CLI_EXIT_CODES`. Added review target exit 4, COI exit 3; retains exact full inventory and real CLI envelope/exit/redaction checks. |
| `test_pr18_docs_examples.py::test_phase1_cli_examples_are_registered` | b | Deployment CLI now rejects unauthenticated legacy command groups before nested help. Injected inert services to test registration through the real command tree. No deployment authentication was bypassed in production; executable docs examples already use injected services. |

## Verification

Commands used `UV_CACHE_DIR=/tmp/researchbase-uv-cache` because the sandbox denies access to uv's default cache.

- The 24 reported parameter cases, with the renamed cancellation test substituted: **24 passed**, 2 existing Alembic deprecation warnings.
- `uv run pytest -o addopts='' -q -p no:cacheprovider tests/architecture`: **57 passed**.
- `uv run pytest -o addopts='' -q -p no:cacheprovider tests/unit`: **1733 passed, 4 failed**, 2 existing Alembic deprecation warnings. All 24 reported failures are fixed. The four additional failures below are sandbox restrictions, not reported as PASS.
- `uv run ruff check` on all 13 touched Python files: **PASS**.
- `uv run ruff format --check` on the same files: **13 already formatted**.
- `git diff --check`: **PASS**.
- `git diff --name-only -- migrations docs/architecture`: **empty**.

The full run's four remaining failures are in `test_hg1_runner.py`: `test_v2_denial_keeps_versioned_fail_closed_response`, `test_socket_lifecycle_one_request_and_cleanup`, `test_foreign_peer_policy_denies_before_frame_without_using_request_slot`, and `test_incomplete_owner_frame_cannot_extend_runner_past_deadline`. All fail at native Unix socket bind with `PermissionError: [Errno 1] Operation not permitted`. They also failed in the unmodified starting tree in this sandbox. These tests were left intact and require a host that permits native socket binding for a full-suite green result.

Full-tree Ruff/Pyright/format debt remains; the unit static gate proves no new debt rather than claiming full-tree cleanliness. No integration database or live providers were needed or exercised for these unit repairs. No commits, pushes, or branches were created.
