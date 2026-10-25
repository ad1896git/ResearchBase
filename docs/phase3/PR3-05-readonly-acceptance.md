# PR3-05 read-only slice acceptance and D1/D2 deferral record

Date: 2026-10-25. Documentation only; baseline `d744074` (PR #12 merge).
Accepted delivery: PR #10, merge `8dc9bd2accc55cfe8e14d1d5ab0d72f511f65d28`.
This records the owner's acceptance below; it grants no further implementation scope.

## Owner decisions (verbatim)

- D1 = D1-C: durable save/replay is deferred; the read-only boundary is kept.
- D2 = D2-C: the save lock protocol is deferred.
- The PR3-05 read-only slice (R1 to R4, merged as PR #10, merge commit 8dc9bd2) is accepted as its own deliverable.
- Full PR3-05 (with save) remains deferred; this record does not accept it.

Authority for these decisions is the owner's instruction for this record, not inferred test success.

## Sources and evidence labels

**Read from source:** references below are repository-relative `file:line` at `d744074`;
the merged inventory was read using `git diff 8dc9bd2^1 8dc9bd2` and the individual
R1–R4 commits listed below. No inferred CI outcome is labeled measured.
The plan is `docs/phase3/PR3-05-readonly-slice-plan.md:1`; the R1-added contract is
`docs/phase3/PR3-05-readonly-slice-contract.md:1`. Their historical review/authorization
labels are superseded only for this slice by the owner's decisions above.
`docs/phase3/PR3-05-D1-D2-decision-brief.md` is absent from the baseline tree and
reachable Git history; no planning-lane copy was found inside this repository.
**Neither brief copy was used.** This is an explicit source limitation, not a claim
to have reviewed it. D1/D2 background was read from the existing draft at
`docs/proposals/PR3-05_Context_Memory_Contract_DRAFT.md:285`; the decisions come from the owner.

**Measured:** local run IDs `L181-1` through `L181-8` below identify this record's
focused verification on the baseline plus this document. They are local labels, not CI IDs.
Historical R4 results are **read from source**, including 1398 unit/architecture passes
(`docs/phase3/PR3-05-readonly-slice-evidence.md:144`) and 46 PostgreSQL passes
(`docs/phase3/PR3-05-readonly-slice-evidence.md:235`); they are not new measurements.

## Accepted scope and delivered files

Paths below use these literal prefixes: `AR = src/researchbase/agent_runtime/`,
`SRC = src/researchbase/`, `U = tests/unit/phase3/`, `I = tests/integration/phase3/`,
`A = tests/architecture/`, `D = docs/phase3/`. Expand prefix + suffix to get each file.
Inventory is **read from the merged diff**; repeated files indicate later refinement.

| Delivery / source commit | Accepted behavior | Files delivered or changed |
| --- | --- | --- |
| R1 / `13e4076` | Closed immutable requests/results, six source variants, bounded canonical memory format and read-only ports | `AR/application/context_contracts.py`; `AR/domain/task_memory.py`; `AR/ports/context_repository.py`; `D/PR3-05-readonly-slice-contract.md`; `A/test_pr3_00_boundaries.py` |
| R2 / `5a8c3e3` | Scoped exact canonical reconstruction in one read snapshot, owning checks, verified required bytes and configured API/CLI composition | `AR/application/canonical_context.py`; `AR/application/research_task.py`; `AR/ports/context_repository.py`; `SRC/persistence/context_repository.py`; `SRC/persistence/context_queries.py`; `SRC/persistence/uow.py`; `SRC/application/manuscript_freeze.py`; `SRC/application/provenance_queries.py`; `SRC/application/source_version.py`; `SRC/api/app.py`; `SRC/cli/composition.py`; `A/test_pr3_00_boundaries.py`; `A/test_pr3_05_readonly_boundaries.py`; `U/test_canonical_context.py`; `I/test_pr3_05_context_reads.py`; `D/PR3-05-readonly-slice-contract.md` |
| R3 / `4976e8f` | Exact memory reads, optional unusable-memory diagnostics and non-authorizing promotion-context validation | `AR/application/task_memory.py`; `AR/application/promotion_context.py`; `A/test_pr3_00_boundaries.py`; `D/PR3-05-readonly-slice-contract.md` |
| R4 / `0285ae2` | Adversarial unit, architecture, real PostgreSQL snapshot/concurrency and consumer evidence | `U/test_context_contracts.py`; `U/test_canonical_context.py`; `U/test_task_memory.py`; `U/test_promotion_context.py`; `A/test_pr3_05_readonly_boundaries.py`; `I/test_pr3_05_context_reads.py`; `I/test_pr3_05_memory_reads.py`; `I/test_pr3_05_promotion_validation.py`; `D/PR3-05-readonly-slice-evidence.md` |
| Included follow-up / `16392b7` | API test factory accepts the configured context ArtifactStore argument | `tests/unit/test_api_credential_wiring.py`; `D/PR3-05-readonly-slice-evidence.md` (trailing blank-line cleanup) |

These are all 27 distinct files in the merged diff, including bootstrap admissions
and the follow-up. R2 delivered some tests originally allocated to R4 by the plan.
Behavioral source anchors: `AR/application/canonical_context.py:34`,
`AR/application/task_memory.py:44`, `AR/application/promotion_context.py:26`.

The accepted reads preserve task/step binding owners and exact FROZEN or historically
frozen SUPERSEDED versions. They check project entitlement before protected expansion,
use one REPEATABLE READ READ ONLY snapshot, preserve validity warnings, and verify
required bytes. Memory is derived operational data, read separately and revalidated.
Bounds are 1,048,576 encoded bytes, 256 manifest sources and 8,192 characters per note.
Source: `D/PR3-05-readonly-slice-contract.md:17`, `:51`, `:120`, `:177`, `:208`.

## What this acceptance does not do

No durable memory save, receipt/replay, ArtifactStore write/repair, save lock protocol,
schema/migration/dependency change, new transport route, scientific promotion or freeze,
execution activation, provider call/disclosure grant, long-term/vector memory, or
cross-project grant is accepted. Source: `D/PR3-05-readonly-slice-plan.md:155`.
Canonical reconstruction excludes author memory/scratchpad; it does not implement
PR3-14 reviewer execution (`D/PR3-05-readonly-slice-contract.md:116`).
An admissible validation still reports `S2_PRODUCER_PROVENANCE_UNVERIFIED` and grants
no promotion, execution or provider action (`AR/application/promotion_context.py:99`).

## Tests supporting the accepted boundary

**Read from merged test source:** each entry is a pytest node ID plus its `file:line`
anchor, using the prefixes above. Listed parameter instances are actual merged cases;
the focused runs exercised every case in their selected files, not just this selection.

| Evidence | Node ID(s) and source line |
| --- | --- |
| Closed/immutable formats, owning hashes and all three bounds | `U/test_context_contracts.py::test_owning_hashes_round_trip_without_rehash[RESEARCH_QUESTION_VERSION]` (`:40`); `U/test_context_contracts.py::test_recursive_malformed_format_rejected[nested]` (`:59`); `U/test_context_contracts.py::test_note_source_and_encoded_bounds` (`:89`) |
| Binding owners, observations and admission | `U/test_canonical_context.py::test_single_snapshot_preserves_binding_owners_and_non_authorizing_safety` (`:143`); `U/test_canonical_context.py::test_observations_preserve_facts_and_do_not_invent_validity[INVALID]` (`:225`); `U/test_canonical_context.py::test_revoked_credentials_precede_protected_sql` (`:257`) |
| Exact source families and frozen history | `I/test_pr3_05_context_reads.py::test_each_family_resolves_task_and_step_bindings[CLAIM_VERSION]` (`:83`); `I/test_pr3_05_context_reads.py::test_draft_and_live_reference_do_not_enter_context[ARTIFACT_VERSION]` (`:485`); `I/test_pr3_05_context_reads.py::test_current_pointer_change_preserves_exact_historical_artifact` (`:540`) |
| Real single snapshot under concurrent writers; no explicit exclusion locks | `I/test_pr3_05_context_reads.py::test_one_readonly_snapshot_survives_committed_writer` (`:124`); `I/test_pr3_05_context_reads.py::test_context_reader_completes_under_delivered_writer_exclusion_locks` (`:466`); `I/test_pr3_05_memory_reads.py::test_consumer_uses_one_readonly_session_without_mutation[memory]` (`:193`); same node `[promotion]` |
| Deny foreign/global bytes and share Human/Agent boundary | `I/test_pr3_05_context_reads.py::test_out_of_scope_node_denied_before_any_store_access[global]` (`:230`); `I/test_pr3_05_memory_reads.py::test_hash_guesses_and_foreign_manifest_sources_fail_closed[manifest_source-foreign]` (`:124`); `I/test_pr3_05_context_reads.py::test_enrolled_agent_and_human_use_same_boundary` (`:503`) |
| Required corruption fails; optional loss permits independent reconstruction | `I/test_pr3_05_context_reads.py::test_required_artifact_bytes_fail_entire_query[corrupt]` (`:279`); `I/test_pr3_05_memory_reads.py::test_optional_loss_explicit_read_failure_and_fresh_reconstruction[missing]` (`:69`); `I/test_pr3_05_memory_reads.py::test_optional_memory_never_hides_required_context_byte_loss` (`:287`) |
| Inert, reloaded memory and verified returned bytes; expiry stays a projection | `I/test_pr3_05_memory_reads.py::test_exact_memory_is_inert_and_reloaded` (`:56`); `I/test_pr3_05_memory_reads.py::test_bytes_actually_returned_are_verified` (`:313`); `I/test_pr3_05_context_reads.py::test_expiry_is_projected_without_changing_checkpoint_history` (`:386`) |
| Validation never promotes, including both admitted targets | `I/test_pr3_05_promotion_validation.py::test_candidate_basis_revision_gates_and_missing_s2[RESEARCH_QUESTION_VERSION]` (`:21`); same node `[HYPOTHESIS_VERSION]` |
| No write/transport/vendor capability; independent reviewer reconstruction | `A/test_pr3_05_readonly_boundaries.py::test_read_services_have_no_transport_vendor_sql_or_write_calls` (`:79`); `A/test_pr3_05_readonly_boundaries.py::test_reviewer_reconstruction_has_no_memory_and_results_grant_no_actions` (`:111`) |

## Measured verification for this record

All uv commands used `UV_CACHE_DIR="$PWD/tmp/pr3-05-readonly-uv-cache"`.
Commands below expand the same prefixes above; `pytest` means `uv run pytest -o addopts='' -q`.

| Local run ID | Exact command after prefix expansion | Observed result / exit |
| --- | --- | --- |
| L181-1 | `uv run ruff check .` | `All checks passed!` / 0 |
| L181-2 | `uv run ruff format --check .` | `931 files already formatted` / 0 |
| L181-3 | `uv run pyright` | `0 errors, 0 warnings, 0 informations`; tool-update notice / 0 |
| L181-4 | `pytest U/test_context_contracts.py U/test_canonical_context.py U/test_task_memory.py U/test_promotion_context.py tests/unit/test_api_credential_wiring.py` | 50 passed in 2.41s / 0 |
| L181-5 | `pytest A/test_pr3_05_readonly_boundaries.py A/test_pr3_00_boundaries.py` | 64 passed in 0.45s / 0 |
| L181-6 | `pytest I/test_pr3_05_context_reads.py I/test_pr3_05_memory_reads.py I/test_pr3_05_promotion_validation.py` | 46 passed, 3 warnings in 4.58s / 0 |
| L181-7 | `git diff --check HEAD` | empty output / 0 |
| L181-8 | `test -s docs/phase3/PR3-05-readonly-acceptance.md && echo record-present` | `record-present` / 0 |

No failed or skipped tests in these runs. PostgreSQL used the existing explicit
`RB_TEST_ADMIN_URL` disposable fixture; its major-18 assertion is at
`tests/integration/phase3/conftest.py:112`. The three warnings are Alembic's existing
`path_separator` deprecation. No whole suite was run; the loop owns that evidence.

## Remaining open and prerequisite status

- D1 and D2 are **deferred**, not technically resolved. Saving needs a separately reviewed,
  frozen and authorized write pack; full PR3-05 remains **not accepted**.
  Source: `D/PR3-05-readonly-slice-plan.md:444`, narrowed by the owner decisions above.
- PR3-02-S2 is **not started; needs its own authorization**, and is not accepted here.
  Source: `D/PR3-04-acceptance.md:36`; S1 excludes execution/promotion at
  `D/PR3-02-S1-contract-freeze.md:36`. Producer provenance and atomic promotion remain future work.
- PR3-04 has an **owner acceptance record dated 2026-10-24**, conditional on green full-suite
  CI on that PR's head. Source: `D/PR3-04-acceptance.md:3` and `:24` records runs
  `40111940781` / `40111943031` on `2914208`; `:31` records the owner's two-review waiver.
  This is read from source, not a new measurement of those CI runs or a new PR3-04 decision.
  PR3-04's acceptance does not authorize S2, resolve D1/D2 or accept full PR3-05.
