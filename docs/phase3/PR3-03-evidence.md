# PR3-03 evidence

## S1 — A1 retry (2026-10-22)

Baseline: `codex/phase3-wave3-base`, HEAD `93df5bb`. Initial working tree was clean.
Scope: owner-approved A1, literal forward-only 0080 migration, Appendix H mechanical
head maintenance, and this evidence. S2 and later steps are not implemented.

A1 wraps 13 previously unparenthesised CASE expressions in conditions across 17
physical lines in §§4.4–4.5. §4.1 triggers contain no CASE condition requiring a
change. Existing parenthesised expressions, assignments and other statements are
unchanged. Pack §13 lists every changed original line, function, before and after.
The remainder of the original pack is byte-for-byte unchanged. No G stop condition
was observed. SQL literals equal the amended pack statement text; only Python
literal boundaries wrap long lines. All 78 statements retain their SQL whitespace,
including long SQL lines; Python physical lines are at most 100 characters. There
are seven new functions, six replacements, nine new triggers, and no new deferred
trigger. Existing trigger identities remain in place. Ancestor migrations,
pyproject.toml and uv.lock are unchanged.

Environment setup before the first uv command (and inherited or explicitly set
for every subsequent uv command):

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
```

`RB_TEST_ADMIN_URL` was already explicitly selected by the runner. It names the
local PostgreSQL `postgres` admin database with role `researchbase`. The supplied
compile probe created and dropped a random disposable database. The metadata
query below confirms PostgreSQL 18.6 (server_version_num 180006), role researchbase
and UTF8; the compile probe independently asserts UTF8 on its disposable database.
No application database was used.

Console output below is the exact combined stdout/stderr; exit status is recorded
separately. Raw logs and helper scripts remain under ignored `tmp/pr3-03/`.

### uv sync --locked --group dev

```sh
uv sync --locked --group dev
```

Exit: `0`. Output:

```text
Resolved 38 packages in 10ms
Checked 34 packages in 3ms
```

### git diff --check HEAD

```sh
git diff --check HEAD
```

Exit: `0`. Output:

```text
```

### uv run ruff check .

```sh
uv run ruff check .
```

Exit: `0`. Output:

```text
All checks passed!
```

### uv run ruff format --check .

```sh
uv run ruff format --check .
```

Exit: `0`. Output:

```text
889 files already formatted
```

### uv run pyright

```sh
uv run pyright
```

Exit: `0`. Output:

```text
0 errors, 0 warnings, 0 informations
WARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`

```

### uv run alembic heads

```sh
uv run alembic heads
```

Exit: `0`. Output:

```text
0080_capability_gateway (head)
```

### PYTHONPATH=. uv run python /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/pr303_s1_compile_probe.py

```sh
PYTHONPATH=. uv run python /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/pr303_s1_compile_probe.py
```

Exit: `0`. Output:

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
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_0206068fef574b62bf1cebf32a77ce70
SERVER_VERSION_NUM 180006
DATABASE_ROLE researchbase
COMPILED pr303_immutable
COMPILED pr303_policy_insert_guard
COMPILED pr303_permission_insert_guard
COMPILED pr303_invocation_guard
COMPILED pr303_ref_insert_guard
COMPILED pr303_event_insert_guard
COMPILED pr303_validate_gateway
COMPILED pr301_task_guard
COMPILED pr301_receipt_insert_guard
COMPILED pr304_child_guard
COMPILED pr304_validate_safety
COMPILED pr301_graph_final_guard
COMPILED pr301_receipt_complete
0080_capability_gateway (head)
COMPILE_GATE 13/13
DISPOSABLE_DROPPED: researchbase_pr212_test_0206068fef574b62bf1cebf32a77ce70
```

### uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture

```sh
uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture
```

Exit: `0`. Output:

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 351 items

tests/architecture/test_b01_resolution_boundaries.py ...                 [  0%]
tests/architecture/test_b02_strategy_promotion_boundaries.py ....        [  1%]
tests/architecture/test_b03_discussion_hypothesis_boundaries.py ....     [  3%]
tests/architecture/test_b04_boundaries.py ....                           [  4%]
tests/architecture/test_b05_review_boundaries.py ....                    [  5%]
tests/architecture/test_b06_revision_action.py ...                       [  6%]
tests/architecture/test_b07_revision_decisions.py ...                    [  7%]
tests/architecture/test_b08_issue_disposition.py ...                     [  7%]
tests/architecture/test_b10_reconsideration.py ...                       [  8%]
tests/architecture/test_b11_readiness_boundaries.py ...                  [  9%]
tests/architecture/test_b12_prepare_boundaries.py ....                   [ 10%]
tests/architecture/test_b13_grant_boundaries.py ....                     [ 11%]
tests/architecture/test_b14_ready_boundaries.py .....                    [ 13%]
tests/architecture/test_b14a_entry_boundaries.py ..                      [ 13%]
tests/architecture/test_b14r_ready_approval_boundaries.py ...            [ 14%]
tests/architecture/test_b15_package_boundaries.py ....                   [ 15%]
tests/architecture/test_b16_boundaries.py ...                            [ 16%]
tests/architecture/test_b17_boundaries.py ...                            [ 17%]
tests/architecture/test_b19_close_prior_art_boundaries.py ..             [ 18%]
tests/architecture/test_b20_screening_boundaries.py ...                  [ 19%]
tests/architecture/test_b21_capture_boundaries.py ..                     [ 19%]
tests/architecture/test_b22_prior_art_boundaries.py ...                  [ 20%]
tests/architecture/test_b23_novelty_boundaries.py ...                    [ 21%]
tests/architecture/test_b25_boundaries.py ...                            [ 22%]
tests/architecture/test_b26_boundaries.py ...                            [ 23%]
tests/architecture/test_b27_defensive_closure_read.py ...                [ 23%]
tests/architecture/test_b32_boundaries.py ................               [ 28%]
tests/architecture/test_basic_approval.py ...                            [ 29%]
tests/architecture/test_import_boundaries.py .............               [ 33%]
tests/architecture/test_m1_boundaries.py ...                             [ 33%]
tests/architecture/test_no_masked_url_reconnect.py ................      [ 38%]
tests/architecture/test_pr02_boundaries.py ..........                    [ 41%]
tests/architecture/test_pr12_boundaries.py ....                          [ 42%]
tests/architecture/test_pr13_boundaries.py ..                            [ 43%]
tests/architecture/test_pr13r_batched_reads.py ...                       [ 43%]
tests/architecture/test_pr14_boundaries.py ..                            [ 44%]
tests/architecture/test_pr15_http_boundaries.py ...                      [ 45%]
tests/architecture/test_pr16_cli_boundaries.py ....                      [ 46%]
tests/architecture/test_pr17_agent_ready_architecture.py ......          [ 48%]
tests/architecture/test_pr18_boundaries.py .......                       [ 50%]
tests/architecture/test_pr2_00_boundaries.py ...                         [ 50%]
tests/architecture/test_pr2_17_boundaries.py ...                         [ 51%]
tests/architecture/test_pr2_18_boundaries.py .................           [ 56%]
tests/architecture/test_pr2_19_boundaries.py ....................        [ 62%]
tests/architecture/test_pr2_20_boundaries.py .....                       [ 63%]
tests/architecture/test_pr3_00_boundaries.py ........................... [ 71%]
................................                                         [ 80%]
tests/architecture/test_pr3_01_boundaries.py ....                        [ 81%]
tests/architecture/test_pr3_02_s1_boundaries.py ..                       [ 82%]
tests/architecture/test_pr3_04_boundaries.py ..                          [ 82%]
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
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 351 passed, 50 warnings in 20.00s =======================
```

### uv run pytest -o addopts='' -ra tests/unit/test_ci_migration_head.py tests/unit/test_batch_c_migration_history.py tests/unit/test_task12_migration_history.py

```sh
uv run pytest -o addopts='' -ra tests/unit/test_ci_migration_head.py tests/unit/test_batch_c_migration_history.py tests/unit/test_task12_migration_history.py
```

Exit: `0`. Output:

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 3 items

tests/unit/test_ci_migration_head.py .                                   [ 33%]
tests/unit/test_batch_c_migration_history.py .                           [ 66%]
tests/unit/test_task12_migration_history.py .                            [100%]

=============================== warnings summary ===============================
tests/unit/test_ci_migration_head.py::test_ci_migration_head_assertion_matches_repository_head
tests/unit/test_batch_c_migration_history.py::test_batch_c_linear_history_and_frozen_lane_sql
tests/unit/test_task12_migration_history.py::test_task12_preserves_every_historical_migration_byte_and_exact_child
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 3 passed, 3 warnings in 0.10s =========================
```

### uv run pytest -o addopts='' -ra tests/unit/phase2/test_pr2_04_r8a_host_topology.py tests/unit/phase2/test_pr2_20_inventory.py tests/unit/phase2/test_pr2_04_static_acceptance.py

```sh
uv run pytest -o addopts='' -ra tests/unit/phase2/test_pr2_04_r8a_host_topology.py tests/unit/phase2/test_pr2_20_inventory.py tests/unit/phase2/test_pr2_04_static_acceptance.py
```

Exit: `0`. Output:

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 15 items

tests/unit/phase2/test_pr2_04_r8a_host_topology.py ........              [ 53%]
tests/unit/phase2/test_pr2_20_inventory.py ......                        [ 93%]
tests/unit/phase2/test_pr2_04_static_acceptance.py .                     [100%]

=============================== warnings summary ===============================
tests/unit/phase2/test_pr2_04_r8a_host_topology.py::test_r8a_actual_migration_graph_and_frozen_bytes
tests/unit/phase2/test_pr2_04_static_acceptance.py::test_candidate_static_gates_and_inherited_formatter_delta
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 15 passed, 2 warnings in 8.10s ========================
```

### uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_00_bootstrap.py tests/integration/phase3/test_pr3_01_migration.py tests/integration/phase3/test_pr3_04_migration.py tests/integration/phase3/test_pr3_02_s1_migration.py

```sh
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_00_bootstrap.py tests/integration/phase3/test_pr3_01_migration.py tests/integration/phase3/test_pr3_04_migration.py tests/integration/phase3/test_pr3_02_s1_migration.py
```

Exit: `0`. Output:

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 14 items

tests/integration/phase3/test_pr3_00_bootstrap.py ......                 [ 42%]
tests/integration/phase3/test_pr3_01_migration.py ...                    [ 64%]
tests/integration/phase3/test_pr3_04_migration.py ..                     [ 78%]
tests/integration/phase3/test_pr3_02_s1_migration.py ...                 [100%]

=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_00_bootstrap.py: 14 warnings
tests/integration/phase3/test_pr3_01_migration.py: 11 warnings
tests/integration/phase3/test_pr3_04_migration.py: 9 warnings
tests/integration/phase3/test_pr3_02_s1_migration.py: 8 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 14 passed, 42 warnings in 11.03s =======================
```

### uv run pytest -o addopts='' -ra tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_revision_action.py tests/integration/phase2/test_pr2_17_authorship_schema.py

```sh
uv run pytest -o addopts='' -ra tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_revision_action.py tests/integration/phase2/test_pr2_17_authorship_schema.py
```

Exit: `0`. Output:

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 145 items

tests/integration/phase2/test_pr2_03_review_guards.py .................. [ 12%]
...............                                                          [ 22%]
tests/integration/phase2/test_pr2_04_execution_migration.py .....        [ 26%]
tests/integration/phase2/test_pr2_04_migration_coverage.py ...........   [ 33%]
tests/integration/phase2/test_pr2_15_decision_schema.py ...              [ 35%]
tests/integration/phase2/test_revision_action.py ....................... [ 51%]
................................                                         [ 73%]
tests/integration/phase2/test_pr2_17_authorship_schema.py .............. [ 83%]
........................                                                 [100%]

=============================== warnings summary ===============================
tests/integration/phase2/test_pr2_03_review_guards.py: 42 warnings
tests/integration/phase2/test_pr2_04_execution_migration.py: 11 warnings
tests/integration/phase2/test_pr2_04_migration_coverage.py: 24 warnings
tests/integration/phase2/test_pr2_15_decision_schema.py: 13 warnings
tests/integration/phase2/test_revision_action.py: 173 warnings
tests/integration/phase2/test_pr2_17_authorship_schema.py: 51 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================ 145 passed, 314 warnings in 121.47s (0:02:01) =================
```

### PostgreSQL metadata

Exact command:

```sh
uv run python tmp/pr3-03/pg_metadata.py
```

The helper reads `RB_TEST_ADMIN_URL` and executes `SHOW server_version`,
`SELECT current_user` and `SHOW server_encoding` through SQLAlchemy, then disposes
its engine. Exit: `0`. Exact output:

```text
SERVER_VERSION 18.6 (Homebrew)
DATABASE_ROLE researchbase
SERVER_ENCODING UTF8
```

### Pack and SQL literal audit

Exact command:

```sh
.venv/bin/python tmp/pr3-03/audit.py
```

The helper compares original pack lines from `git show HEAD:...` against the
amended original portion, allowing only inserted parentheses at the 17 listed
lines. It extracts every authoritative statement from §§2/2.1/3/4.4/4.5/4.1 and
compares it to the migration's evaluated SQL constants in execution order. It
also checks physical source length and absence of noqa. Exit: `0`. Exact output:

```text
PACK_A1_ONLY 17 changed lines; 13 CASE expressions; original remainder unchanged
SQL_LITERAL_PARITY 78/78 statements exactly equal
MIGRATION_MAX_PHYSICAL_LINE 100
NO_NOQA true; lint configuration unchanged
```

### Formatting correction during preparation

The first ordered gate attempt stopped at `uv run ruff format --check .` with
exit `1`, before Pyright, heads or the probe ran. Exact output:

```text
Would reformat: tests/integration/phase3/test_pr3_01_migration.py
Would reformat: tests/integration/phase3/test_pr3_02_s1_migration.py
2 files would be reformatted, 887 files already formatted
```

The preceding diff and lint commands had exits 0 (empty diff output and
`All checks passed!`). Exact correction command:

```sh
uv run ruff format tests/integration/phase3/test_pr3_01_migration.py tests/integration/phase3/test_pr3_02_s1_migration.py
```

Exit `0`; output `2 files reformatted`. Only the changed head assertions were
collapsed by Ruff. The complete ordered static gate was then rerun with the
passing outputs above. No lint configuration or exclusion was changed.

### Appendix H PostgreSQL setup

Exact wrapper invocation:

```sh
PYTHONPATH=. uv run python tmp/pr3-03/run_h_postgres.py
```

The wrapper uses the existing `disposable_database("researchbase_pr212_test_")`
helper, exports its yielded URL as DATABASE_URL only for the focused pytest
subprocess above, and drops that runtime database afterwards. Each phase2 fixture
creates its own isolated test database using the existing plumbing. RB_TEST_ADMIN_URL
continues to name postgres. The wrapper's complete exact output:

```text
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_a99402429530431fb059f346edfab6e6
$ uv run pytest -o addopts='' -ra tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_revision_action.py tests/integration/phase2/test_pr2_17_authorship_schema.py
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 145 items

tests/integration/phase2/test_pr2_03_review_guards.py .................. [ 12%]
...............                                                          [ 22%]
tests/integration/phase2/test_pr2_04_execution_migration.py .....        [ 26%]
tests/integration/phase2/test_pr2_04_migration_coverage.py ...........   [ 33%]
tests/integration/phase2/test_pr2_15_decision_schema.py ...              [ 35%]
tests/integration/phase2/test_revision_action.py ....................... [ 51%]
................................                                         [ 73%]
tests/integration/phase2/test_pr2_17_authorship_schema.py .............. [ 83%]
........................                                                 [100%]

=============================== warnings summary ===============================
tests/integration/phase2/test_pr2_03_review_guards.py: 42 warnings
tests/integration/phase2/test_pr2_04_execution_migration.py: 11 warnings
tests/integration/phase2/test_pr2_04_migration_coverage.py: 24 warnings
tests/integration/phase2/test_pr2_15_decision_schema.py: 13 warnings
tests/integration/phase2/test_revision_action.py: 173 warnings
tests/integration/phase2/test_pr2_17_authorship_schema.py: 51 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================ 145 passed, 314 warnings in 121.47s (0:02:01) =================

EXIT 0
DISPOSABLE_DROPPED: researchbase_pr212_test_a99402429530431fb059f346edfab6e6
```

### Counts and disposition

- `uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture`: `collected 351 items`; `====================== 351 passed, 50 warnings in 20.00s =======================`; exit `0`.
- `uv run pytest -o addopts='' -ra tests/unit/test_ci_migration_head.py tests/unit/test_batch_c_migration_history.py tests/unit/test_task12_migration_history.py`: `collected 3 items`; `======================== 3 passed, 3 warnings in 0.10s =========================`; exit `0`.
- `uv run pytest -o addopts='' -ra tests/unit/phase2/test_pr2_04_r8a_host_topology.py tests/unit/phase2/test_pr2_20_inventory.py tests/unit/phase2/test_pr2_04_static_acceptance.py`: `collected 15 items`; `======================== 15 passed, 2 warnings in 8.10s ========================`; exit `0`.
- `uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_00_bootstrap.py tests/integration/phase3/test_pr3_01_migration.py tests/integration/phase3/test_pr3_04_migration.py tests/integration/phase3/test_pr3_02_s1_migration.py`: `collected 14 items`; `======================= 14 passed, 42 warnings in 11.03s =======================`; exit `0`.
- `uv run pytest -o addopts='' -ra tests/integration/phase2/test_pr2_03_review_guards.py tests/integration/phase2/test_pr2_04_execution_migration.py tests/integration/phase2/test_pr2_04_migration_coverage.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_revision_action.py tests/integration/phase2/test_pr2_17_authorship_schema.py`: `collected 145 items`; `================ 145 passed, 314 warnings in 121.47s (0:02:01) =================`; exit `0`.

The required S1 gate commands and the additional Appendix H PostgreSQL regressions
are recorded above. There are no failures or skips in the final focused runs.
Existing Alembic deprecation warnings and Pyright's version notice are retained
verbatim. Full suite/six shards: NOT RUN; owned by the external check loop.
Overall PR3-03 acceptance and independent review remain PENDING. No commit, push,
branch creation, later implementation or .git write was performed. Git commands
reported no lock or sandbox error.

### Exact changed paths

```text
 M .github/workflows/ci.yml
 M docs/phase3/PR3-03-contract-freeze.md
 M tests/architecture/test_b02_strategy_promotion_boundaries.py
 M tests/architecture/test_b04_boundaries.py
 M tests/architecture/test_b05_review_boundaries.py
 M tests/architecture/test_b20_screening_boundaries.py
 M tests/architecture/test_basic_approval.py
 M tests/architecture/test_import_boundaries.py
 M tests/architecture/test_pr3_02_s1_boundaries.py
 M tests/fixtures/phase2_static_baseline.json
 M tests/integration/phase2/test_pr2_03_review_guards.py
 M tests/integration/phase2/test_pr2_04_execution_migration.py
 M tests/integration/phase2/test_pr2_04_migration_coverage.py
 M tests/integration/phase2/test_pr2_15_decision_schema.py
 M tests/integration/phase2/test_pr2_17_authorship_schema.py
 M tests/integration/phase2/test_revision_action.py
 M tests/integration/phase3/test_pr3_00_bootstrap.py
 M tests/integration/phase3/test_pr3_01_migration.py
 M tests/integration/phase3/test_pr3_02_s1_migration.py
 M tests/integration/phase3/test_pr3_04_migration.py
 M tests/unit/phase2/test_pr2_04_r8a_host_topology.py
 M tests/unit/phase2/test_pr2_20_inventory.py
 M tests/unit/test_batch_c_migration_history.py
 M tests/unit/test_task12_migration_history.py
?? docs/phase3/PR3-03-evidence.md
?? migrations/versions/0080_capability_gateway.py
```

Final check after evidence generation: `git diff --check HEAD`, exit `0`,
stdout empty, stderr empty.

### S1 independent verification at HEAD 43cae25 (2026-10-22)

Verification only; starting HEAD `43cae2575d665a6512577d93985db01a1c6c38bc`.
Initial `git status --short` exited `0` with no output (clean working tree).
The following cache setting was applied before every uv command:

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
```

Commands below ran in the requested order. Output blocks contain the observed
combined command output; empty output is stated explicitly.

#### `uv sync --locked --group dev`

Exit code: `0`.

```text
Resolved 38 packages in 2ms
Checked 34 packages in 0.70ms
```

#### `git diff --check 93df5bb HEAD`

Exit code: `0`.

Output: empty.

#### `uv run ruff check .`

Exit code: `0`.

```text
All checks passed!
```

#### `uv run ruff format --check .`

Exit code: `0`.

```text
889 files already formatted
```

#### `uv run pyright`

Exit code: `0`.

```text
0 errors, 0 warnings, 0 informations
WARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).
Please install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`

```

#### `uv run alembic heads`

Exit code: `0`.

```text
0080_capability_gateway (head)
```

#### `PYTHONPATH=. uv run python /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/pr303_s1_compile_probe.py`

Exit code: `1`.

```text
Traceback (most recent call last):
  File "/Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/pr303_s1_compile_probe.py", line 11, in <module>
    with disposable_database("researchbase_pr212_test_") as url:
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/fengwang/.local/share/uv/python/cpython-3.12.15-macos-aarch64-none/lib/python3.12/contextlib.py", line 137, in __enter__
    return next(self.gen)
           ^^^^^^^^^^^^^^
  File "/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/tests/disposable_postgres.py", line 57, in disposable_database
    url = admin_url(*aliases)
          ^^^^^^^^^^^^^^^^^^^
  File "/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/tests/disposable_postgres.py", line 34, in admin_url
    pytest.fail("Set RB_TEST_ADMIN_URL explicitly to a disposable local PostgreSQL admin URL")
  File "/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/.venv/lib/python3.12/site-packages/_pytest/outcomes.py", line 177, in fail
    raise Failed(msg=reason, pytrace=pytrace)
Failed: Set RB_TEST_ADMIN_URL explicitly to a disposable local PostgreSQL admin URL
```

Verification stopped at the compile probe's first failure, as required. The probe
failed before opening a disposable database. PostgreSQL version, role and encoding
were not observed. No `COMPILED` lines or `COMPILE_GATE 13/13` were produced.
This run does not establish PostgreSQL compilation success.

The following requested commands were NOT RUN after that failure:

- `uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture`

- `uv run pytest -o addopts='' -ra tests/unit/test_ci_migration_head.py tests/unit/test_batch_c_migration_history.py tests/unit/test_task12_migration_history.py`

- `uv run pytest -o addopts='' -ra tests/unit/phase2/test_pr2_04_r8a_host_topology.py tests/unit/phase2/test_pr2_20_inventory.py tests/unit/phase2/test_pr2_04_static_acceptance.py`

- `uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_00_bootstrap.py tests/integration/phase3/test_pr3_01_migration.py tests/integration/phase3/test_pr3_04_migration.py tests/integration/phase3/test_pr3_02_s1_migration.py`

Test counts: no pytest command ran; passed/failed/skipped counts are unavailable.
AST literal-equivalence script and comparison: NOT RUN because verification stopped
at the compile-probe failure. The reported regex mismatches remain unverified;
no MATCH/MISMATCH result is claimed. No six-shard or whole-suite run was performed.
No product, migration, pack or test file was changed. No commit, push or branch
creation was performed. This verification is incomplete; S1 gate success is not claimed.

Changed path for this verification: `docs/phase3/PR3-03-evidence.md` only.


### S1 independent verification follow-up after reviewer findings (2026-10-22)

This follow-up supplies the results missing from the preceding stopped attempt.
That attempt's failure remains recorded above; its NOT RUN statements describe
that attempt only. HEAD remains `43cae2575d665a6512577d93985db01a1c6c38bc`.
Only this S1 evidence section is edited. No product, migration, pack or test
file was changed. The helper script is under ignored `tmp/`.

README.md lines 113–126 and compose.yaml identify the local disposable PostgreSQL
admin selector. The following settings were applied before every uv command:

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
export RB_TEST_ADMIN_URL="postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres"
```

The supplied compile probe exited 0, compiled all thirteen bodies and printed
`COMPILE_GATE 13/13`. It observed server_version_num `180006` and role
`researchbase`, and its UTF8 assertion passed. Because the supplied probe does
not print encoding, the separate disposable-database metadata query below
records the explicit `SERVER_ENCODING UTF8` output on the same server identity.

The phase2 group's first run below failed (14 passed, 1 failed, 0 skipped) because
this evidence addition had an extra blank line at EOF. That evidence-only defect
was removed, and the exact group was rerun successfully. Both outputs are retained.

Final pytest results for the four requested groups:

| Group | Passed | Failed | Skipped | Exit code |
| --- | ---: | ---: | ---: | ---: |
| Architecture and unit architecture | 351 | 0 | 0 | 0 |
| Migration history | 3 | 0 | 0 | 0 |
| Phase2 (rerun after evidence whitespace correction) | 15 | 0 | 0 | 0 |
| Phase3 PostgreSQL integration | 14 | 0 | 0 | 0 |

The AST script `tmp/pr303_s1_ast_equivalence.py` parses module-level SQL constants
with `ast.parse` and evaluates string literals with `ast.literal_eval`; tuple
references resolve only to those evaluated constants. It never executes/imports
the migration. It extracts every CREATE [OR REPLACE] FUNCTION from SQL fences in
the contract and splits SQL statements outside quoted strings and dollar bodies.
Normalization removes SQL comments and whitespace only: no case folding,
punctuation replacement or semantic rewriting. SQL comments use a quote-aware
scanner with nested block-comment support. It checks all thirteen function names
and all other DDL/index/extension/trigger statements as a multiset, including
duplicate cardinality, against the frozen §§2–4.5 inventory. The later attachment
audit and amendment before/after excerpts are not additional migration statements.

Observed equivalence: 13/13 function bodies MATCH; all 78/78 SQL statements MATCH;
zero MISMATCH results. The director's reported 8-of-8 regex mismatches are not real
literal differences under the requested normalization. No correction was made to
SQL or the pack. There is no differing position to report.

Exact combined stdout/stderr and exit codes follow, in execution order.

#### Follow-up command 1

```sh
PYTHONPATH=. uv run python /Users/fengwang/Documents/ResearchBaseProject/.pipeline/bin/pr303_s1_compile_probe.py
```

Exit code: `0`.

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
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_e74e6aff41d8429e90a8dfbedd886d00
SERVER_VERSION_NUM 180006
DATABASE_ROLE researchbase
COMPILED pr303_immutable
COMPILED pr303_policy_insert_guard
COMPILED pr303_permission_insert_guard
COMPILED pr303_invocation_guard
COMPILED pr303_ref_insert_guard
COMPILED pr303_event_insert_guard
COMPILED pr303_validate_gateway
COMPILED pr301_task_guard
COMPILED pr301_receipt_insert_guard
COMPILED pr304_child_guard
COMPILED pr304_validate_safety
COMPILED pr301_graph_final_guard
COMPILED pr301_receipt_complete
0080_capability_gateway (head)
COMPILE_GATE 13/13
DISPOSABLE_DROPPED: researchbase_pr212_test_e74e6aff41d8429e90a8dfbedd886d00
```

#### Follow-up command 2

```sh
uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture
```

Exit code: `0`.

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 351 items

tests/architecture/test_b01_resolution_boundaries.py ...                 [  0%]
tests/architecture/test_b02_strategy_promotion_boundaries.py ....        [  1%]
tests/architecture/test_b03_discussion_hypothesis_boundaries.py ....     [  3%]
tests/architecture/test_b04_boundaries.py ....                           [  4%]
tests/architecture/test_b05_review_boundaries.py ....                    [  5%]
tests/architecture/test_b06_revision_action.py ...                       [  6%]
tests/architecture/test_b07_revision_decisions.py ...                    [  7%]
tests/architecture/test_b08_issue_disposition.py ...                     [  7%]
tests/architecture/test_b10_reconsideration.py ...                       [  8%]
tests/architecture/test_b11_readiness_boundaries.py ...                  [  9%]
tests/architecture/test_b12_prepare_boundaries.py ....                   [ 10%]
tests/architecture/test_b13_grant_boundaries.py ....                     [ 11%]
tests/architecture/test_b14_ready_boundaries.py .....                    [ 13%]
tests/architecture/test_b14a_entry_boundaries.py ..                      [ 13%]
tests/architecture/test_b14r_ready_approval_boundaries.py ...            [ 14%]
tests/architecture/test_b15_package_boundaries.py ....                   [ 15%]
tests/architecture/test_b16_boundaries.py ...                            [ 16%]
tests/architecture/test_b17_boundaries.py ...                            [ 17%]
tests/architecture/test_b19_close_prior_art_boundaries.py ..             [ 18%]
tests/architecture/test_b20_screening_boundaries.py ...                  [ 19%]
tests/architecture/test_b21_capture_boundaries.py ..                     [ 19%]
tests/architecture/test_b22_prior_art_boundaries.py ...                  [ 20%]
tests/architecture/test_b23_novelty_boundaries.py ...                    [ 21%]
tests/architecture/test_b25_boundaries.py ...                            [ 22%]
tests/architecture/test_b26_boundaries.py ...                            [ 23%]
tests/architecture/test_b27_defensive_closure_read.py ...                [ 23%]
tests/architecture/test_b32_boundaries.py ................               [ 28%]
tests/architecture/test_basic_approval.py ...                            [ 29%]
tests/architecture/test_import_boundaries.py .............               [ 33%]
tests/architecture/test_m1_boundaries.py ...                             [ 33%]
tests/architecture/test_no_masked_url_reconnect.py ................      [ 38%]
tests/architecture/test_pr02_boundaries.py ..........                    [ 41%]
tests/architecture/test_pr12_boundaries.py ....                          [ 42%]
tests/architecture/test_pr13_boundaries.py ..                            [ 43%]
tests/architecture/test_pr13r_batched_reads.py ...                       [ 43%]
tests/architecture/test_pr14_boundaries.py ..                            [ 44%]
tests/architecture/test_pr15_http_boundaries.py ...                      [ 45%]
tests/architecture/test_pr16_cli_boundaries.py ....                      [ 46%]
tests/architecture/test_pr17_agent_ready_architecture.py ......          [ 48%]
tests/architecture/test_pr18_boundaries.py .......                       [ 50%]
tests/architecture/test_pr2_00_boundaries.py ...                         [ 50%]
tests/architecture/test_pr2_17_boundaries.py ...                         [ 51%]
tests/architecture/test_pr2_18_boundaries.py .................           [ 56%]
tests/architecture/test_pr2_19_boundaries.py ....................        [ 62%]
tests/architecture/test_pr2_20_boundaries.py .....                       [ 63%]
tests/architecture/test_pr3_00_boundaries.py ........................... [ 71%]
................................                                         [ 80%]
tests/architecture/test_pr3_01_boundaries.py ....                        [ 81%]
tests/architecture/test_pr3_02_s1_boundaries.py ..                       [ 82%]
tests/architecture/test_pr3_04_boundaries.py ..                          [ 82%]
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
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
====================== 351 passed, 50 warnings in 18.10s =======================
```

#### Follow-up command 3

```sh
uv run pytest -o addopts='' -ra tests/unit/test_ci_migration_head.py tests/unit/test_batch_c_migration_history.py tests/unit/test_task12_migration_history.py
```

Exit code: `0`.

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 3 items

tests/unit/test_ci_migration_head.py .                                   [ 33%]
tests/unit/test_batch_c_migration_history.py .                           [ 66%]
tests/unit/test_task12_migration_history.py .                            [100%]

=============================== warnings summary ===============================
tests/unit/test_ci_migration_head.py::test_ci_migration_head_assertion_matches_repository_head
tests/unit/test_batch_c_migration_history.py::test_batch_c_linear_history_and_frozen_lane_sql
tests/unit/test_task12_migration_history.py::test_task12_preserves_every_historical_migration_byte_and_exact_child
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 3 passed, 3 warnings in 0.10s =========================
```

#### Follow-up command 4

```sh
uv run pytest -o addopts='' -ra tests/unit/phase2/test_pr2_04_r8a_host_topology.py tests/unit/phase2/test_pr2_20_inventory.py tests/unit/phase2/test_pr2_04_static_acceptance.py
```

Exit code: `1`.

The failing run's output is encoded as a JSON string so traceback whitespace
is preserved exactly without introducing trailing whitespace into this file.

```json
"============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 15 items\n\ntests/unit/phase2/test_pr2_04_r8a_host_topology.py ........              [ 53%]\ntests/unit/phase2/test_pr2_20_inventory.py ......                        [ 93%]\ntests/unit/phase2/test_pr2_04_static_acceptance.py F                     [100%]\n\n=================================== FAILURES ===================================\n__________ test_candidate_static_gates_and_inherited_formatter_delta ___________\n\npr204_trace = <scripts.pr2_04_pytest_evidence.FactRecorder object at 0x10ba225d0>\n\n    @pytest.mark.pr204_requirements(\"PR204-REG-03\")\n    def test_candidate_static_gates_and_inherited_formatter_delta(pr204_trace: FactRecorder) -> None:\n        def execute(arguments: list[str]) -> subprocess.CompletedProcess[str]:\n            result = subprocess.run(arguments, cwd=ROOT, capture_output=True, text=True, check=False)\n            pr204_trace.record(\n                command=arguments,\n                exit_code=result.returncode,\n                stdout=result.stdout,\n                stderr=result.stderr,\n            )\n            return result\n    \n        baseline = json.loads(BASELINE.read_text())\n        assert ScriptDirectory.from_config(Config(str(ROOT / \"alembic.ini\"))).get_heads() == [\n            baseline[\"migration_head\"]\n        ]\n        assert baseline[\"baseline_commit\"] == \"b8179f17720ca47c3b25ad9d36f6a8e8d4aa79ff\"\n        assert (\n            execute(\n                [\"git\", \"merge-base\", \"--is-ancestor\", baseline[\"baseline_commit\"], \"HEAD\"]\n            ).returncode\n            == 0\n        )\n        scopes = [\"src\", \"migrations\", \"tests\", \"scripts\"]\n        lint = execute([sys.executable, \"-m\", \"ruff\", \"check\", *scopes, \"--output-format\", \"json\"])\n        assert lint.returncode in {0, 1}\n        lint_diagnostics = [\n            (str(Path(row[\"filename\"]).relative_to(ROOT)), row[\"code\"], row[\"message\"])\n            for row in json.loads(lint.stdout)\n        ]\n        types = execute([sys.executable, \"-m\", \"pyright\", \"--outputjson\"])\n        assert types.returncode in {0, 1}\n        type_diagnostics = [\n            (str(Path(row[\"file\"]).relative_to(ROOT)), row[\"severity\"], row.get(\"rule\"), row[\"message\"])\n            for row in json.loads(types.stdout)[\"generalDiagnostics\"]\n        ]\n        # Exact file/rule/message multisets cap inherited debt; new or duplicated errors fail.\n        assert not (Counter(lint_diagnostics) - Counter(map(tuple, baseline.get(\"ruff\", []))))\n        assert not (Counter(type_diagnostics) - Counter(map(tuple, baseline[\"pyright\"])))\n        lineage = execute([sys.executable, RECOVERY_GATES, \"lineage\"])\n        assert lineage.returncode == 0\n        assert json.loads(lineage.stdout)[\"recovery_lineage\"][\"status\"] == \"PASS\"\n        # Whitespace/format deltas start at the current authorized baseline below.\n        raw = execute([sys.executable, \"-m\", \"ruff\", \"format\", \"--check\", *scopes])\n        assert raw.returncode in {0, 1}\n        current = set(re.findall(r\"^Would reformat: (.+)$\", raw.stdout + raw.stderr, re.MULTILINE))\n        assert current <= set(baseline.get(\"formatter\", []))\n        assert (raw.returncode == 0 and not current) or (raw.returncode == 1 and bool(current))\n        changed = execute(\n            [\n                \"git\",\n                \"diff\",\n                \"--name-only\",\n                \"--diff-filter=ACMR\",\n                baseline[\"baseline_commit\"],\n                \"--\",\n                \"*.py\",\n                \"*.pyi\",\n            ]\n        )\n        assert changed.returncode == 0\n>       assert execute([\"git\", \"diff\", \"--check\", baseline[\"baseline_commit\"]]).returncode == 0\nE       AssertionError: assert 2 == 0\nE        +  where 2 = CompletedProcess(args=['git', 'diff', '--check', 'b8179f17720ca47c3b25ad9d36f6a8e8d4aa79ff'], returncode=2, stdout='docs/phase3/PR3-03-evidence.md:723: new blank line at EOF.\\n', stderr='').returncode\nE        +    where CompletedProcess(args=['git', 'diff', '--check', 'b8179f17720ca47c3b25ad9d36f6a8e8d4aa79ff'], returncode=2, stdout='docs/phase3/PR3-03-evidence.md:723: new blank line at EOF.\\n', stderr='') = <function test_candidate_static_gates_and_inherited_formatter_delta.<locals>.execute at 0x10ba4fba0>(['git', 'diff', '--check', 'b8179f17720ca47c3b25ad9d36f6a8e8d4aa79ff'])\n\ntests/unit/phase2/test_pr2_04_static_acceptance.py:81: AssertionError\n=============================== warnings summary ===============================\ntests/unit/phase2/test_pr2_04_r8a_host_topology.py::test_r8a_actual_migration_graph_and_frozen_bytes\ntests/unit/phase2/test_pr2_04_static_acceptance.py::test_candidate_static_gates_and_inherited_formatter_delta\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.\n    util.warn_deprecated(\n\n-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html\n=========================== short test summary info ============================\nFAILED tests/unit/phase2/test_pr2_04_static_acceptance.py::test_candidate_static_gates_and_inherited_formatter_delta\n=================== 1 failed, 14 passed, 2 warnings in 7.62s ===================\n"
```

#### Follow-up command 5

```sh
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_00_bootstrap.py tests/integration/phase3/test_pr3_01_migration.py tests/integration/phase3/test_pr3_04_migration.py tests/integration/phase3/test_pr3_02_s1_migration.py
```

Exit code: `0`.

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 14 items

tests/integration/phase3/test_pr3_00_bootstrap.py ......                 [ 42%]
tests/integration/phase3/test_pr3_01_migration.py ...                    [ 64%]
tests/integration/phase3/test_pr3_04_migration.py ..                     [ 78%]
tests/integration/phase3/test_pr3_02_s1_migration.py ...                 [100%]

=============================== warnings summary ===============================
tests/integration/phase3/test_pr3_00_bootstrap.py: 14 warnings
tests/integration/phase3/test_pr3_01_migration.py: 11 warnings
tests/integration/phase3/test_pr3_04_migration.py: 9 warnings
tests/integration/phase3/test_pr3_02_s1_migration.py: 8 warnings
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================= 14 passed, 42 warnings in 10.83s =======================
```

#### Follow-up command 6

```sh
uv run python tmp/pr303_s1_ast_equivalence.py
```

Exit code: `0`.

```text
MATCH pr303_immutable
MATCH pr303_policy_insert_guard
MATCH pr303_permission_insert_guard
MATCH pr303_invocation_guard
MATCH pr303_ref_insert_guard
MATCH pr303_event_insert_guard
MATCH pr303_validate_gateway
MATCH pr301_task_guard
MATCH pr301_receipt_insert_guard
MATCH pr304_child_guard
MATCH pr304_validate_safety
MATCH pr301_graph_final_guard
MATCH pr301_receipt_complete
FUNCTION_BODIES 13 MISMATCHES 0
MATCH DDL_01_SQL
MATCH DDL_02_SQL
MATCH DDL_03_SQL
MATCH DDL_04_SQL
MATCH DDL_05_SQL
MATCH DDL_06_SQL
MATCH DDL_07_SQL
MATCH DDL_08_SQL
MATCH INDEX_01_SQL
MATCH INDEX_02_SQL
MATCH INDEX_03_SQL
MATCH INDEX_04_SQL
MATCH INDEX_05_SQL
MATCH INDEX_06_SQL
MATCH INDEX_07_SQL
MATCH INDEX_08_SQL
MATCH INDEX_09_SQL
MATCH INDEX_10_SQL
MATCH INDEX_11_SQL
MATCH INDEX_12_SQL
MATCH INDEX_13_SQL
MATCH INDEX_14_SQL
MATCH INDEX_15_SQL
MATCH INDEX_16_SQL
MATCH INDEX_17_SQL
MATCH INDEX_18_SQL
MATCH INDEX_19_SQL
MATCH INDEX_20_SQL
MATCH INDEX_21_SQL
MATCH INDEX_22_SQL
MATCH INDEX_23_SQL
MATCH INDEX_24_SQL
MATCH INDEX_25_SQL
MATCH INDEX_26_SQL
MATCH INDEX_27_SQL
MATCH INDEX_28_SQL
MATCH INDEX_29_SQL
MATCH INDEX_30_SQL
MATCH INDEX_31_SQL
MATCH INDEX_32_SQL
MATCH INDEX_33_SQL
MATCH INDEX_34_SQL
MATCH INDEX_35_SQL
MATCH INDEX_36_SQL
MATCH INDEX_37_SQL
MATCH EXTENSION_01_SQL
MATCH EXTENSION_02_SQL
MATCH EXTENSION_03_SQL
MATCH EXTENSION_04_SQL
MATCH EXTENSION_05_SQL
MATCH EXTENSION_06_SQL
MATCH EXTENSION_07_SQL
MATCH EXTENSION_08_SQL
MATCH EXTENSION_09_SQL
MATCH EXTENSION_10_SQL
MATCH EXTENSION_11_SQL
MATCH TRIGGER_01_SQL
MATCH TRIGGER_02_SQL
MATCH TRIGGER_03_SQL
MATCH TRIGGER_04_SQL
MATCH TRIGGER_05_SQL
MATCH TRIGGER_06_SQL
MATCH TRIGGER_07_SQL
MATCH TRIGGER_08_SQL
MATCH TRIGGER_09_SQL
SQL_STATEMENTS 78 MIGRATION_LITERAL_CONSTANTS 78
EQUIVALENCE_MISMATCHES 0
```

#### Follow-up command 7

```sh
uv run python - <<'PY'
import os
from sqlalchemy import create_engine, text
from tests.disposable_postgres import disposable_database
with disposable_database('researchbase_pr212_test_') as url:
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            for label, query in [('SERVER_VERSION', 'SHOW server_version'), ('SERVER_VERSION_NUM', 'SHOW server_version_num'), ('DATABASE_ROLE', 'SELECT current_user'), ('SERVER_ENCODING', 'SHOW server_encoding')]:
                print(label, connection.execute(text(query)).scalar_one())
    finally:
        engine.dispose()
PY
```

Exit code: `0`.

```text
DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948
DISPOSABLE_CREATED: researchbase_pr212_test_5517cdf713094ca092ded65a3f90ea04
SERVER_VERSION 18.6 (Homebrew)
SERVER_VERSION_NUM 180006
DATABASE_ROLE researchbase
SERVER_ENCODING UTF8
DISPOSABLE_DROPPED: researchbase_pr212_test_5517cdf713094ca092ded65a3f90ea04
```

#### Follow-up command 8

```sh
uv run pytest -o addopts='' -ra tests/unit/phase2/test_pr2_04_r8a_host_topology.py tests/unit/phase2/test_pr2_20_inventory.py tests/unit/phase2/test_pr2_04_static_acceptance.py
```

Exit code: `0`.

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0
rootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113
configfile: pyproject.toml
plugins: anyio-4.14.2
collected 15 items

tests/unit/phase2/test_pr2_04_r8a_host_topology.py ........              [ 53%]
tests/unit/phase2/test_pr2_20_inventory.py ......                        [ 93%]
tests/unit/phase2/test_pr2_04_static_acceptance.py .                     [100%]

=============================== warnings summary ===============================
tests/unit/phase2/test_pr2_04_r8a_host_topology.py::test_r8a_actual_migration_graph_and_frozen_bytes
tests/unit/phase2/test_pr2_04_static_acceptance.py::test_candidate_static_gates_and_inherited_formatter_delta
  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane113/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
======================== 15 passed, 2 warnings in 7.91s ========================
```

#### Follow-up command 9

```sh
git diff --check 93df5bb HEAD && uv run ruff check .
```

Exit code: `0`.

```text
All checks passed!
```

All requested focused groups now have successful observed runs. The requested
`git diff --check 93df5bb HEAD && uv run ruff check .` exited 0, with output
`All checks passed!`. An additional `git diff --check` of the working tree exited
0 with empty output before this evidence append. The first attempt's successful
sync, diff, Ruff format, Pyright and Alembic-head outputs remain recorded above.
No six-shard or full-suite run, commit, push or branch creation was performed.

Changed tracked path: `docs/phase3/PR3-03-evidence.md` only.
Ignored verification helper: `tmp/pr303_s1_ast_equivalence.py`.

## S2 — Repository ports, composed locks and stored-row reads

Date: 2026-10-22. Baseline HEAD: `52d984ab8c5c1cd424656e6da3a1000fae06b70b`
(S1 evidence baseline supplied by the owner). **S2 focused checks passed.**
S3 has not started. Overall PR3-03 acceptance, independent review and the external
six-shard check remain **PENDING**; no full suite or shard was launched here.
No commit, branch creation or push was performed. Work remains uncommitted.

The gateway adapter composes the delivered safety prefix and task-row phase.
Its first statement is the literal eighteen-parent SHARE; project, pr301 command,
pr301 task, target pr302 actor and target pr302 version keys precede row locking.
Version-to-actor resolution is unlocked after the prefix, and version is reread
under both target keys after availability locking. Registration omits both target
keys, availability locking and version reads. Eleven blocking acquisitions each
have an immediately following callback; registration has eight. A callback may
terminate the recipe before any subsequent SQL. Existing safety `lock_write`
retains its combined recipe and callbacks. No gateway command admission,
accounting, dispatch, S3 DTOs, execution identity or write operation is added.

Closed TypedDict stored rows cover all five new tables and every stored receipt
and task-event column. SQL adapters return detached dictionaries/lists with UTC
normalization; no Session, ORM entity or result cursor crosses the port.
Permissions use canonical tuple order; refs use direction/family/version UUID;
events use sequence; receipt lookup uses project/authenticated actor/command.
The UoW and adapters construct without SQL, including entering an unbound Session
UoW. Metadata includes new columns, relationships, unique keys, indexes and CHECKs;
accepted migrations and the frozen pack were not edited.

### Changed paths and Deviations

Every changed or new nonignored path:

- `src/researchbase/agent_runtime/ports/gateway_repository.py` (new)
- `src/researchbase/agent_runtime/ports/task_safety_repository.py`
- `src/researchbase/persistence/capability_gateway_repository.py` (new)
- `src/researchbase/persistence/task_safety_repository.py`
- `src/researchbase/persistence/models.py`
- `src/researchbase/persistence/uow.py`
- `tests/unit/phase3/test_capability_gateway_repository.py` (new)
- `src/researchbase/persistence/research_task_repository.py` (Deviation S2-D1)
- `docs/phase3/PR3-03-evidence.md` (Deviation S2-D2)

**Deviation S2-D1 — resolved compatibility defect, extra read-adapter file.**
Scope: `research_task_repository.py`, explicit existing task-event column projection.
Evidence: frozen pack §3 adds nullable `result_tool_policy_id`,
`result_capability_invocation_id`, `result_capability_event_id` to task events;
S2 completion requires “existing ports/callers remain type-compatible.” Delivered
`research_task_repository.py:99–103` selected `SELECT * FROM {table}` while
`agent_runtime/application/research_task.py:450` constructs
`TaskEventRead(**r)`. The first extra PostgreSQL behavior run collected 33:
19 passed, 14 failed, 0 skipped, all failures reporting
`TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'`.
Action: current `research_task_repository.py:50/105` explicitly selects the existing
17-column planning event shape; the gateway's separate stored read includes all
20 columns. The command API/DTO and write behavior remain unchanged. The added
unit regression compares the projection against TaskEventRead's actual fields.
Disposition: fixed; the same PostgreSQL command now passes all 33, and the additional
planning Application/safety-query command passes 9. No architecture gap or waiver
is claimed. No S3 vocabulary was introduced to fix this.

**Deviation S2-D2 — owner-required evidence and ignored verification files.**
The task explicitly requires an S2 section in this evidence file, although the
plan lists that file under S8. Its change records only S2 work and does not start
S8 implementation. All supporting scripts, raw command output, diff and traces
are under ignored `tmp/pr3-03/`; uv's ignored cache is
`tmp/pr3-03-uv-cache/`. These are local verification artifacts, not runtime files.
The helper scripts are enumerated below. Disposition: recorded within the owner's
explicit evidence authorization; no contract/dependency/configuration changes.

### Observed checks and counts

Before every uv command, `UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"` was set
(the capture helper sets the equivalent absolute path in its subprocess environment).
Setup `uv sync --locked --group dev` exited 0, stdout exactly:

```text
Resolved 38 packages in 3ms
Checked 34 packages in 4ms
```

Setup stderr was empty. `pyproject.toml` and `uv.lock` are unchanged.
`command -v pg_dump` returned `/opt/homebrew/bin/pg_dump`; `pg_dump --version`
returned `pg_dump (PostgreSQL) 18.6 (Homebrew)`. PostgreSQL runs used the already
explicitly selected `RB_TEST_ADMIN_URL` for the local disposable admin database.
No application database or SQLite was used.

| Final distinct check group | Collected | Passed | Failed | Skipped | Exit |
| --- | ---: | ---: | ---: | ---: | ---: |
| S2 repository unit tests | 29 | 29 | 0 | 0 | 0 |
| Required safety transport + PR3-04/S1 architecture | 14 | 14 | 0 | 0 | 0 |
| PostgreSQL bootstrap + PR3-01/04/S1 migrations | 14 | 14 | 0 | 0 | 0 |
| PostgreSQL safety Application + concurrency + replay | 33 | 33 | 0 | 0 | 0 |
| PostgreSQL planning Application + safety queries | 9 | 9 | 0 | 0 | 0 |
| **Total distinct final tests** | **99** | **99** | **0** | **0** | **0** |

The final required commands ran in the owner's prescribed order. Static checks
all exited 0: whitespace, Ruff, format (892 files), Pyright (0 errors), sole
Alembic head `0080_capability_gateway (head)`. Counts for non-pytest probes are
not pytest counts. The disposable metadata probe verifies 5/5 new tables and
7/7 nullable extensions and all six receipt/event extension indexes on PostgreSQL 18.6, role `researchbase`, UTF8: exact column
names/types/nullability, FK tuples/delete rules, unique tuples, index names/columns/
uniqueness and CHECK counts. It does not claim exhaustive trigger or lock behavior.

Earlier failures are retained below, not relabeled PASS: preliminary Pyright had
33 metadata typing errors, then 12 test-double typing errors; preliminary Ruff had
2 errors; preliminary unit runs had 25 passed/1 failed (26 collected, 0 skipped).
Metadata declaration/type fixes and the test-double casts resolved these. The
unit failure tried to resolve the existing raw-SQL-owned `source_versions` table
through incomplete historical ORM metadata; the corrected assertion checks the
actual FK target specifications, and real catalog parity independently verifies
all concrete targets. The first helper launch lacked the repository on PYTHONPATH
and exited 1 before DB access; the explicit `PYTHONPATH=.` rerun passed. The
19-pass/14-fail PostgreSQL run is S2-D1 above. A self-review added the six
receipt/event extension indexes to metadata. The expanded catalog probe initially
counted a PostgreSQL supporting UNIQUE constraint as an explicit index and failed
its helper assertion; filtering SQLAlchemy inspector `duplicates_constraint`
entries fixed that probe, whose subsequent exit-0 output is retained below. Later successful repeated gates
had 28 then 29 repository tests; those repeated counts are not added to 99.

### Exact command output archive

Each JSON record below preserves the exact command, exit code, stdout and stderr
(including trailing newlines/traceback whitespace). Empty strings mean no output.
This encoding avoids adding traceback trailing whitespace to this Markdown file.
No unrun command is marked PASS.

Initial metadata Pyright run, command `uv run pyright`, exit 1:

```json
"/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3234:35 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"append_constraint\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3240:35 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"append_constraint\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3244:44 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"append_constraint\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3248:69 - error: Cannot access attribute \"constraints\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"constraints\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3250:52 - error: Cannot access attribute \"constraints\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"constraints\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3252:44 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"append_constraint\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3264:44 - error: Cannot access attribute \"append_column\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"append_column\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3268:44 - error: Cannot access attribute \"append_column\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"append_column\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3272:44 - error: Cannot access attribute \"append_column\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"append_column\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3276:44 - error: Cannot access attribute \"append_column\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"append_column\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3280:44 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"append_constraint\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3291:44 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"append_constraint\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3306:44 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"append_constraint\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3321:44 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"append_constraint\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3340:60 - error: Cannot access attribute \"constraints\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"constraints\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3342:43 - error: Cannot access attribute \"constraints\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"constraints\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3344:60 - error: Cannot access attribute \"constraints\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"constraints\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3346:43 - error: Cannot access attribute \"constraints\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"constraints\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3348:60 - error: Cannot access attribute \"constraints\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"constraints\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3350:43 - error: Cannot access attribute \"constraints\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"constraints\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3352:60 - error: Cannot access attribute \"constraints\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"constraints\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3354:43 - error: Cannot access attribute \"constraints\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"constraints\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3356:35 - error: Cannot access attribute \"append_column\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"append_column\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3360:35 - error: Cannot access attribute \"append_column\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"append_column\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3364:35 - error: Cannot access attribute \"append_column\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"append_column\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3368:35 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"append_constraint\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3377:35 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"append_constraint\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3386:35 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"append_constraint\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3395:35 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"append_constraint\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3407:35 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"append_constraint\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3425:35 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"append_constraint\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3437:35 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"append_constraint\" is unknown (reportAttributeAccessIssue)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/src/researchbase/persistence/models.py:3447:35 - error: Cannot access attribute \"append_constraint\" for class \"FromClause\"\n  \u00a0\u00a0Attribute \"append_constraint\" is unknown (reportAttributeAccessIssue)\n33 errors, 0 warnings, 0 informations\nWARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).\nPlease install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`\n\n"
```

Capture `tmp/pr3-03/s2-preliminary.json`:

```json
[
  {
    "command": "uv run ruff check .",
    "exit_code": 1,
    "stdout": "I001 [*] Import block is un-sorted or un-formatted\n   --> src/researchbase/persistence/uow.py:3:1\n    |\n  1 |   \"\"\"Synchronous SQLAlchemy UnitOfWork for one application transaction.\"\"\"\n  2 |\n  3 | / from __future__ import annotations\n  4 | |\n  5 | | from collections.abc import Callable\n  6 | | from types import TracebackType\n  7 | |\n  8 | | from sqlalchemy import create_engine\n  9 | | from sqlalchemy.exc import DBAPIError\n 10 | | from sqlalchemy.orm import Session, sessionmaker\n 11 | |\n 12 | | from researchbase.agent_runtime.ports.agent_repository import UncertainAgentCommit\n 13 | | from researchbase.agent_runtime.ports.task_repository import UncertainTaskCommit\n 14 | | from researchbase.application.ports import (\n 15 | |     ActorRepository,\n 16 | |     ArtifactRepository,\n 17 | |     ArtifactVersionRepository,\n 18 | |     AuthorshipRepository,\n 19 | |     ClaimRepository,\n 20 | |     DatasetRepository,\n 21 | |     DatasetSnapshotRepository,\n 22 | |     DiscussionHypothesisRepository,\n 23 | |     ExperimentSpecRepository,\n 24 | |     GovernanceRepository,\n 25 | |     HypothesisRepository,\n 26 | |     MeasurementRepository,\n 27 | |     MetricDefinitionRepository,\n 28 | |     MetricDefinitionVersionRepository,\n 29 | |     Phase2IdentityRepository,\n 30 | |     PreparedSubmissionRepository,\n 31 | |     ProjectRepository,\n 32 | |     ResearchQuestionRepository,\n 33 | |     RunRepository,\n 34 | |     SearchResultResolutionRepository,\n 35 | |     StatisticalResultRepository,\n 36 | |     StrategyCandidatePromotionRepository,\n 37 | |     WorkspaceRepository,\n 38 | | )\n 39 | | from researchbase.foundation.errors import ErrorCode, ResearchBaseError\n 40 | | from researchbase.foundation.structured_logging import emit_uow_rollback\n 41 | | from researchbase.persistence.agent_version_repository import SqlAlchemyAgentRepository\n 42 | | from researchbase.persistence.capability_gateway_repository import SqlAlchemyGatewayRepository\n 43 | | from researchbase.persistence.approval_repository import SqlAlchemyApprovalRepository\n 44 | | from researchbase.persistence.authorship_repository import SqlAlchemyAuthorshipRepository\n 45 | | from researchbase.persistence.decision_repository import SqlAlchemyDecisionRepository\n 46 | | from researchbase.persistence.discussion_hypothesis_repository import (\n 47 | |     SqlAlchemyDiscussionHypothesisRepository,\n 48 | | )\n 49 | | from researchbase.persistence.discussion_repository import SqlAlchemyDiscussionRepository\n 50 | | from researchbase.persistence.governance_repository import SqlAlchemyGovernanceRepository\n 51 | | from researchbase.persistence.internal_review_repository import SqlAlchemyInternalReviewRepository\n 52 | | from researchbase.persistence.literature_evidence_repository import (\n 53 | |     SqlAlchemyLiteratureEvidenceRepository,\n 54 | | )\n 55 | | from researchbase.persistence.literature_search_execution_repository import (\n 56 | |     SqlAlchemyLiteratureSearchExecutionRepository,\n 57 | | )\n 58 | | from researchbase.persistence.literature_search_plan_repository import (\n 59 | |     SqlAlchemyLiteratureSearchPlanRepository,\n 60 | | )\n 61 | | from researchbase.persistence.manuscript_freeze_repository import (\n 62 | |     SqlAlchemyManuscriptFreezeRepository,\n 63 | | )\n 64 | | from researchbase.persistence.metadata_observation_repository import (\n 65 | |     SqlAlchemyMetadataObservationRepository,\n 66 | | )\n 67 | | from researchbase.persistence.novelty_repository import SqlAlchemyNoveltyRepository\n 68 | | from researchbase.persistence.phase2_identity_repository import SqlAlchemyPhase2IdentityRepository\n 69 | | from researchbase.persistence.prepared_submission_repository import (\n 70 | |     SqlAlchemyPreparedSubmissionRepository,\n 71 | | )\n 72 | | from researchbase.persistence.publication_repository import SqlAlchemyPublicationRepository\n 73 | | from researchbase.persistence.repositories import (\n 74 | |     SqlAlchemyActorRepository,\n 75 | |     SqlAlchemyArtifactRepository,\n 76 | |     SqlAlchemyArtifactVersionRepository,\n 77 | |     SqlAlchemyClaimRepository,\n 78 | |     SqlAlchemyDatasetRepository,\n 79 | |     SqlAlchemyDatasetSnapshotRepository,\n 80 | |     SqlAlchemyExperimentSpecRepository,\n 81 | |     SqlAlchemyHypothesisRepository,\n 82 | |     SqlAlchemyMeasurementRepository,\n 83 | |     SqlAlchemyMetricDefinitionRepository,\n 84 | |     SqlAlchemyMetricDefinitionVersionRepository,\n 85 | |     SqlAlchemyProjectRepository,\n 86 | |     SqlAlchemyResearchQuestionRepository,\n 87 | |     SqlAlchemyRunRepository,\n 88 | |     SqlAlchemyStatisticalResultRepository,\n 89 | |     SqlAlchemyWorkspaceRepository,\n 90 | | )\n 91 | | from researchbase.persistence.research_task_repository import SqlAlchemyResearchTaskRepository\n 92 | | from researchbase.persistence.revision_action_repository import SqlAlchemyRevisionActionRepository\n 93 | | from researchbase.persistence.scientific_conclusion_repository import (\n 94 | |     SqlAlchemyScientificConclusionRepository,\n 95 | | )\n 96 | | from researchbase.persistence.search_result_resolution_repository import (\n 97 | |     SqlAlchemySearchResultResolutionRepository,\n 98 | | )\n 99 | | from researchbase.persistence.source_identity_repository import SqlAlchemySourceIdentityRepository\n100 | | from researchbase.persistence.source_merge_repository import SqlAlchemySourceMergeRepository\n101 | | from researchbase.persistence.source_version_repository import SqlAlchemySourceVersionRepository\n102 | | from researchbase.persistence.strategy_candidate_promotion_repository import (\n103 | |     SqlAlchemyStrategyCandidatePromotionRepository,\n104 | | )\n105 | | from researchbase.persistence.task_safety_repository import SqlAlchemyTaskSafetyRepository\n    | |__________________________________________________________________________________________^\n    |\nhelp: Organize imports\n\nE501 Line too long (106 > 100)\n   --> tests/unit/phase3/test_capability_gateway_repository.py:276:101\n    |\n274 |             ],\n275 |             [\n276 |                 \"SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project AND policy_id=:id \"\n    |                                                                                                     ^^^^^^\n277 |                 \"ORDER BY capability_id,capability_version,operation,adapter_id,adapter_version, \"\n278 |                 \"parameter_schema_hash,effect\",\n    |\n\nFound 2 errors.\n[*] 1 fixable with the `--fix` option.\n",
    "stderr": ""
  },
  {
    "command": "uv run pyright",
    "exit_code": 1,
    "stdout": "/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py:183:33 - error: Argument of type \"RecordingSession\" cannot be assigned to parameter \"session\" of type \"Session\" in function \"__init__\"\n    \"RecordingSession\" is not assignable to \"Session\" (reportArgumentType)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py:190:33 - error: Argument of type \"RecordingSession\" cannot be assigned to parameter \"session\" of type \"Session\" in function \"__init__\"\n    \"RecordingSession\" is not assignable to \"Session\" (reportArgumentType)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py:196:33 - error: Argument of type \"RecordingSession\" cannot be assigned to parameter \"session\" of type \"Session\" in function \"__init__\"\n    \"RecordingSession\" is not assignable to \"Session\" (reportArgumentType)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py:203:33 - error: Argument of type \"RecordingSession\" cannot be assigned to parameter \"session\" of type \"Session\" in function \"__init__\"\n    \"RecordingSession\" is not assignable to \"Session\" (reportArgumentType)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py:215:36 - error: Argument of type \"RecordingSession\" cannot be assigned to parameter \"session\" of type \"Session\" in function \"__init__\"\n    \"RecordingSession\" is not assignable to \"Session\" (reportArgumentType)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py:218:38 - error: Argument of type \"RecordingSession\" cannot be assigned to parameter \"session\" of type \"Session\" in function \"__init__\"\n    \"RecordingSession\" is not assignable to \"Session\" (reportArgumentType)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py:235:37 - error: Argument of type \"RecordingSession\" cannot be assigned to parameter \"session\" of type \"Session\" in function \"__init__\"\n    \"RecordingSession\" is not assignable to \"Session\" (reportArgumentType)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py:245:46 - error: Argument of type \"RecordingSession\" cannot be assigned to parameter \"session\" of type \"Session\" in function \"__init__\"\n    \"RecordingSession\" is not assignable to \"Session\" (reportArgumentType)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py:323:26 - error: Argument of type \"() -> RecordingSession\" cannot be assigned to parameter \"session_factory\" of type \"(() -> Session) | sessionmaker[Session]\" in function \"__init__\"\n    Type \"() -> RecordingSession\" is not assignable to type \"(() -> Session) | sessionmaker[Session]\"\n      Type \"() -> RecordingSession\" is not assignable to type \"() -> Session\"\n        Function return type \"RecordingSession\" is incompatible with type \"Session\"\n          \"RecordingSession\" is not assignable to \"Session\"\n      \"FunctionType\" is not assignable to \"sessionmaker[Session]\" (reportArgumentType)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py:325:33 - error: Argument of type \"RecordingSession\" cannot be assigned to parameter \"session\" of type \"Session\" in function \"__init__\"\n    \"RecordingSession\" is not assignable to \"Session\" (reportArgumentType)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py:326:36 - error: Argument of type \"RecordingSession\" cannot be assigned to parameter \"session\" of type \"Session\" in function \"__init__\"\n    \"RecordingSession\" is not assignable to \"Session\" (reportArgumentType)\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tests/unit/phase3/test_capability_gateway_repository.py:375:32 - error: Cannot access attribute \"startswith\" for class \"_NoneName\"\n    Attribute \"startswith\" is unknown (reportAttributeAccessIssue)\n12 errors, 0 warnings, 0 informations\nWARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).\nPlease install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`\n\n",
    "stderr": ""
  },
  {
    "command": "uv run pytest -o addopts='' -ra tests/unit/phase3/test_capability_gateway_repository.py",
    "exit_code": 1,
    "stdout": "============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 26 items\n\ntests/unit/phase3/test_capability_gateway_repository.py ................ [ 61%]\n.....F....                                                               [100%]\n\n=================================== FAILURES ===================================\n_ test_closed_stored_columns_match_inert_metadata[capability_invocation_refs-StoredInvocationRef] _\n\ntable = 'capability_invocation_refs'\nstored = <class 'researchbase.agent_runtime.ports.gateway_repository.StoredInvocationRef'>\n\n    @pytest.mark.parametrize(\n        \"table,stored\",\n        [\n            (\"agent_tool_policies\", port.StoredToolPolicy),\n            (\"agent_tool_policy_permissions\", port.StoredPermission),\n            (\"capability_invocations\", port.StoredInvocation),\n            (\"capability_invocation_refs\", port.StoredInvocationRef),\n            (\"capability_invocation_events\", port.StoredInvocationEvent),\n            (\"research_task_command_receipts\", port.StoredGatewayReceipt),\n            (\"research_task_events\", port.StoredTaskEvent),\n        ],\n    )\n    def test_closed_stored_columns_match_inert_metadata(table, stored):\n        mapped = Base.metadata.tables[table]\n        assert set(get_type_hints(stored)) == set(mapped.columns.keys())\n        assert stored.__required_keys__ == frozenset(mapped.columns.keys())\n        for fk in mapped.foreign_key_constraints:\n            assert fk.ondelete == \"RESTRICT\"\n>           assert fk.referred_table is not None\n                   ^^^^^^^^^^^^^^^^^\n\ntests/unit/phase3/test_capability_gateway_repository.py:349: \n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \n.venv/lib/python3.12/site-packages/sqlalchemy/sql/schema.py:4797: in referred_table\n    return self.elements[0].column.table\n           ^^^^^^^^^^^^^^^^^^^^^^^\n.venv/lib/python3.12/site-packages/sqlalchemy/util/langhelpers.py:1122: in __get__\n    obj.__dict__[self.__name__] = result = self.fget(obj)\n                                           ^^^^^^^^^^^^^^\n.venv/lib/python3.12/site-packages/sqlalchemy/sql/schema.py:3202: in column\n    return self._resolve_column()\n           ^^^^^^^^^^^^^^^^^^^^^^\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \n\nself = ForeignKey('source_versions.id')\n\n    def _resolve_column(\n        self, *, raiseerr: bool = True\n    ) -> Optional[Column[Any]]:\n        _column: Column[Any]\n    \n        if isinstance(self._colspec, str):\n            parenttable, tablekey, colname = self._resolve_col_tokens()\n    \n            if self._unresolvable or tablekey not in parenttable.metadata:\n                if not raiseerr:\n                    return None\n>               raise exc.NoReferencedTableError(\n                    f\"Foreign key associated with column \"\n                    f\"'{self.parent}' could not find \"\n                    f\"table '{tablekey}' with which to generate a \"\n                    f\"foreign key to target column '{colname}'\",\n                    tablekey,\nE                   sqlalchemy.exc.NoReferencedTableError: Foreign key associated with column 'capability_invocation_refs.source_version_id' could not find table 'source_versions' with which to generate a foreign key to target column 'id'\n\n.venv/lib/python3.12/site-packages/sqlalchemy/sql/schema.py:3225: NoReferencedTableError\n=========================== short test summary info ============================\nFAILED tests/unit/phase3/test_capability_gateway_repository.py::test_closed_stored_columns_match_inert_metadata[capability_invocation_refs-StoredInvocationRef]\n========================= 1 failed, 25 passed in 0.19s =========================\n",
    "stderr": ""
  }
]
```

Capture `tmp/pr3-03/s2-required.json`:

```json
[
  {
    "command": "git diff --check HEAD",
    "exit_code": 0,
    "stdout": "",
    "stderr": ""
  },
  {
    "command": "uv run ruff check .",
    "exit_code": 0,
    "stdout": "All checks passed!\n",
    "stderr": ""
  },
  {
    "command": "uv run ruff format --check .",
    "exit_code": 0,
    "stdout": "892 files already formatted\n",
    "stderr": ""
  },
  {
    "command": "uv run pyright",
    "exit_code": 0,
    "stdout": "0 errors, 0 warnings, 0 informations\nWARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).\nPlease install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`\n\n",
    "stderr": ""
  },
  {
    "command": "uv run alembic heads",
    "exit_code": 0,
    "stdout": "0080_capability_gateway (head)\n",
    "stderr": ""
  },
  {
    "command": "uv run pytest -o addopts='' -ra tests/unit/phase3/test_capability_gateway_repository.py",
    "exit_code": 0,
    "stdout": "============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 28 items\n\ntests/unit/phase3/test_capability_gateway_repository.py ................ [ 57%]\n............                                                             [100%]\n\n============================== 28 passed in 0.18s ==============================\n",
    "stderr": ""
  },
  {
    "command": "uv run pytest -o addopts='' -ra tests/unit/phase3/test_task_safety_transports.py tests/architecture/test_pr3_04_boundaries.py tests/architecture/test_pr3_02_s1_boundaries.py",
    "exit_code": 0,
    "stdout": "============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 14 items\n\ntests/unit/phase3/test_task_safety_transports.py ..........              [ 71%]\ntests/architecture/test_pr3_04_boundaries.py ..                          [ 85%]\ntests/architecture/test_pr3_02_s1_boundaries.py ..                       [100%]\n\n=============================== warnings summary ===============================\ntests/architecture/test_pr3_02_s1_boundaries.py::test_authorized_head_and_s1_only\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.\n    util.warn_deprecated(\n\n-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html\n======================== 14 passed, 1 warning in 1.60s =========================\n",
    "stderr": ""
  }
]
```

Capture `tmp/pr3-03/s2-required-final.json`:

```json
[
  {
    "command": "git diff --check HEAD",
    "exit_code": 0,
    "stdout": "",
    "stderr": ""
  },
  {
    "command": "uv run ruff check .",
    "exit_code": 0,
    "stdout": "All checks passed!\n",
    "stderr": ""
  },
  {
    "command": "uv run ruff format --check .",
    "exit_code": 0,
    "stdout": "892 files already formatted\n",
    "stderr": ""
  },
  {
    "command": "uv run pyright",
    "exit_code": 0,
    "stdout": "0 errors, 0 warnings, 0 informations\nWARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).\nPlease install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`\n\n",
    "stderr": ""
  },
  {
    "command": "uv run alembic heads",
    "exit_code": 0,
    "stdout": "0080_capability_gateway (head)\n",
    "stderr": ""
  },
  {
    "command": "uv run pytest -o addopts='' -ra tests/unit/phase3/test_capability_gateway_repository.py",
    "exit_code": 0,
    "stdout": "============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 29 items\n\ntests/unit/phase3/test_capability_gateway_repository.py ................ [ 55%]\n.............                                                            [100%]\n\n============================== 29 passed in 0.17s ==============================\n",
    "stderr": ""
  },
  {
    "command": "uv run pytest -o addopts='' -ra tests/unit/phase3/test_task_safety_transports.py tests/architecture/test_pr3_04_boundaries.py tests/architecture/test_pr3_02_s1_boundaries.py",
    "exit_code": 0,
    "stdout": "============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 14 items\n\ntests/unit/phase3/test_task_safety_transports.py ..........              [ 71%]\ntests/architecture/test_pr3_04_boundaries.py ..                          [ 85%]\ntests/architecture/test_pr3_02_s1_boundaries.py ..                       [100%]\n\n=============================== warnings summary ===============================\ntests/architecture/test_pr3_02_s1_boundaries.py::test_authorized_head_and_s1_only\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.\n    util.warn_deprecated(\n\n-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html\n======================== 14 passed, 1 warning in 1.20s =========================\n",
    "stderr": ""
  }
]
```

Capture `tmp/pr3-03/s2-postgres.json`:

```json
[
  {
    "command": "uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_00_bootstrap.py tests/integration/phase3/test_pr3_01_migration.py tests/integration/phase3/test_pr3_04_migration.py tests/integration/phase3/test_pr3_02_s1_migration.py",
    "exit_code": 0,
    "stdout": "============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 14 items\n\ntests/integration/phase3/test_pr3_00_bootstrap.py ......                 [ 42%]\ntests/integration/phase3/test_pr3_01_migration.py ...                    [ 64%]\ntests/integration/phase3/test_pr3_04_migration.py ..                     [ 78%]\ntests/integration/phase3/test_pr3_02_s1_migration.py ...                 [100%]\n\n=============================== warnings summary ===============================\ntests/integration/phase3/test_pr3_00_bootstrap.py: 14 warnings\ntests/integration/phase3/test_pr3_01_migration.py: 11 warnings\ntests/integration/phase3/test_pr3_04_migration.py: 9 warnings\ntests/integration/phase3/test_pr3_02_s1_migration.py: 8 warnings\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.\n    util.warn_deprecated(\n\n-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html\n======================= 14 passed, 42 warnings in 12.44s =======================\n",
    "stderr": ""
  },
  {
    "command": "uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_04_application.py tests/integration/phase3/test_pr3_04_concurrency.py tests/integration/phase3/test_pr3_04_replay.py",
    "exit_code": 1,
    "stdout": "============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 33 items\n\ntests/integration/phase3/test_pr3_04_application.py .FFF..FFFFF......... [ 60%]\n..                                                                       [ 66%]\ntests/integration/phase3/test_pr3_04_concurrency.py .FFFFFF              [ 87%]\ntests/integration/phase3/test_pr3_04_replay.py ....                      [100%]\n\n=================================== FAILURES ===================================\n__________ test_binding_preserves_plan_and_cancel_bookkeeping[False] ___________\n\nplanning = PlanningFixture(engine=Engine(postgresql+psycopg://researchbase:***@localhost:5432/researchbase_pr212_test_52fdd45ad0e...3d00d26', store=<researchbase.foundation.artifact_store.ContentAddressedFilesystemArtifactStore object at 0x10d638680>)\nsealed = False\n\n    @pytest.mark.parametrize(\"sealed\", (False, True))\n    def test_binding_preserves_plan_and_cancel_bookkeeping(planning, sealed):\n        p = planning\n        task, _ = p.plan()\n        revision = 2\n        if sealed:\n            p.service.execute(p.principal, p.command(\"seal_task_plan\", task, revision))\n            revision += 1\n>       before = p.service.get_task_graph(p.principal, p.project, task)\n                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n\ntests/integration/phase3/test_pr3_04_application.py:175: \n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \nsrc/researchbase/agent_runtime/application/research_task.py:459: in get_task_graph\n    return self._graph(uow, project_id, task_id)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nsrc/researchbase/agent_runtime/application/research_task.py:450: in _graph\n    tuple(TaskEventRead(**r) for r in repo.events(task)),\n    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \n\n.0 = <list_iterator object at 0x10d704ee0>\n\n>       tuple(TaskEventRead(**r) for r in repo.events(task)),\n              ^^^^^^^^^^^^^^^^^^\n        tuple(StepEventRead(**r) for r in repo.events(task, step=True)),\n    )\nE   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'\n\nsrc/researchbase/agent_runtime/application/research_task.py:450: TypeError\n----------------------------- Captured stderr call -----------------------------\nERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.695282+00:00\"}\n------------------------------ Captured log call -------------------------------\nERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.695282+00:00\"}\n___________ test_binding_preserves_plan_and_cancel_bookkeeping[True] ___________\n\nplanning = PlanningFixture(engine=Engine(postgresql+psycopg://researchbase:***@localhost:5432/researchbase_pr212_test_52fdd45ad0e...3d00d26', store=<researchbase.foundation.artifact_store.ContentAddressedFilesystemArtifactStore object at 0x10d638680>)\nsealed = True\n\n    @pytest.mark.parametrize(\"sealed\", (False, True))\n    def test_binding_preserves_plan_and_cancel_bookkeeping(planning, sealed):\n        p = planning\n        task, _ = p.plan()\n        revision = 2\n        if sealed:\n            p.service.execute(p.principal, p.command(\"seal_task_plan\", task, revision))\n            revision += 1\n>       before = p.service.get_task_graph(p.principal, p.project, task)\n                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n\ntests/integration/phase3/test_pr3_04_application.py:175: \n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \nsrc/researchbase/agent_runtime/application/research_task.py:459: in get_task_graph\n    return self._graph(uow, project_id, task_id)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nsrc/researchbase/agent_runtime/application/research_task.py:450: in _graph\n    tuple(TaskEventRead(**r) for r in repo.events(task)),\n    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \n\n.0 = <list_iterator object at 0x10d73bc70>\n\n>       tuple(TaskEventRead(**r) for r in repo.events(task)),\n              ^^^^^^^^^^^^^^^^^^\n        tuple(StepEventRead(**r) for r in repo.events(task, step=True)),\n    )\nE   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'\n\nsrc/researchbase/agent_runtime/application/research_task.py:450: TypeError\n----------------------------- Captured stderr call -----------------------------\nERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.745280+00:00\"}\n------------------------------ Captured log call -------------------------------\nERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.745280+00:00\"}\n__________________ test_public_reserve_denies_without_effects __________________\n\nplanning = PlanningFixture(engine=Engine(postgresql+psycopg://researchbase:***@localhost:5432/researchbase_pr212_test_52fdd45ad0e...3d00d26', store=<researchbase.foundation.artifact_store.ContentAddressedFilesystemArtifactStore object at 0x10d638680>)\n\n    def test_public_reserve_denies_without_effects(planning):\n        task = planning.create()\n        c = reserve(planning, task, 1)\n        with pytest.raises(ResearchBaseError) as exc:\n            service(planning).execute(planning.principal, c)\n        assert exc.value.code == ErrorCode.FORBIDDEN\n        assert (\n>           planning.service.get_research_task(planning.principal, planning.project, task).row_version\n            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n            == 1\n        )\n\ntests/integration/phase3/test_pr3_04_application.py:202: \n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \nsrc/researchbase/agent_runtime/application/research_task.py:462: in get_research_task\n    return self.get_task_graph(principal, project_id, task_id).task\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nsrc/researchbase/agent_runtime/application/research_task.py:459: in get_task_graph\n    return self._graph(uow, project_id, task_id)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nsrc/researchbase/agent_runtime/application/research_task.py:450: in _graph\n    tuple(TaskEventRead(**r) for r in repo.events(task)),\n    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \n\n.0 = <list_iterator object at 0x10d7dbf70>\n\n>       tuple(TaskEventRead(**r) for r in repo.events(task)),\n              ^^^^^^^^^^^^^^^^^^\n        tuple(StepEventRead(**r) for r in repo.events(task, step=True)),\n    )\nE   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'\n\nsrc/researchbase/agent_runtime/application/research_task.py:450: TypeError\n----------------------------- Captured stderr call -----------------------------\nERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"FORBIDDEN\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.760264+00:00\"}\nERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.761571+00:00\"}\n------------------------------ Captured log call -------------------------------\nERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"FORBIDDEN\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.760264+00:00\"}\nERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.761571+00:00\"}\n___ test_injected_failure_rolls_back_task_and_all_results[execution_budgets] ___\n\nplanning = PlanningFixture(engine=Engine(postgresql+psycopg://researchbase:***@localhost:5432/researchbase_pr212_test_52fdd45ad0e...3d00d26', store=<researchbase.foundation.artifact_store.ContentAddressedFilesystemArtifactStore object at 0x10d638680>)\nmonkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x10d7d1340>\npoint = 'execution_budgets'\n\n    @pytest.mark.parametrize(\n        \"point\",\n        (\n            \"execution_budgets\",\n            \"checkpoint_policies\",\n            \"human_checkpoints\",\n            \"research_task_events\",\n            \"research_task_receipt_events\",\n        ),\n    )\n    def test_injected_failure_rolls_back_task_and_all_results(planning, monkeypatch, point):\n        from researchbase.persistence.task_safety_repository import SqlAlchemyTaskSafetyRepository\n    \n        p = planning\n        task = p.create()\n        if point == \"human_checkpoints\":\n            bind(p, task)\n        revision = 2 if point == \"human_checkpoints\" else 1\n>       before = p.service.get_task_graph(p.principal, p.project, task)\n                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n\ntests/integration/phase3/test_pr3_04_application.py:274: \n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \nsrc/researchbase/agent_runtime/application/research_task.py:459: in get_task_graph\n    return self._graph(uow, project_id, task_id)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nsrc/researchbase/agent_runtime/application/research_task.py:450: in _graph\n    tuple(TaskEventRead(**r) for r in repo.events(task)),\n    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \n\n.0 = <list_iterator object at 0x10d7d2e30>\n\n>       tuple(TaskEventRead(**r) for r in repo.events(task)),\n              ^^^^^^^^^^^^^^^^^^\n        tuple(StepEventRead(**r) for r in repo.events(task, step=True)),\n    )\nE   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'\n\nsrc/researchbase/agent_runtime/application/research_task.py:450: TypeError\n----------------------------- Captured stderr call -----------------------------\nERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.820753+00:00\"}\n------------------------------ Captured log call -------------------------------\nERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.820753+00:00\"}\n__ test_injected_failure_rolls_back_task_and_all_results[checkpoint_policies] __\n\nplanning = PlanningFixture(engine=Engine(postgresql+psycopg://researchbase:***@localhost:5432/researchbase_pr212_test_52fdd45ad0e...3d00d26', store=<researchbase.foundation.artifact_store.ContentAddressedFilesystemArtifactStore object at 0x10d638680>)\nmonkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x10d7d04a0>\npoint = 'checkpoint_policies'\n\n    @pytest.mark.parametrize(\n        \"point\",\n        (\n            \"execution_budgets\",\n            \"checkpoint_policies\",\n            \"human_checkpoints\",\n            \"research_task_events\",\n            \"research_task_receipt_events\",\n        ),\n    )\n    def test_injected_failure_rolls_back_task_and_all_results(planning, monkeypatch, point):\n        from researchbase.persistence.task_safety_repository import SqlAlchemyTaskSafetyRepository\n    \n        p = planning\n        task = p.create()\n        if point == \"human_checkpoints\":\n            bind(p, task)\n        revision = 2 if point == \"human_checkpoints\" else 1\n>       before = p.service.get_task_graph(p.principal, p.project, task)\n                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n\ntests/integration/phase3/test_pr3_04_application.py:274: \n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \nsrc/researchbase/agent_runtime/application/research_task.py:459: in get_task_graph\n    return self._graph(uow, project_id, task_id)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nsrc/researchbase/agent_runtime/application/research_task.py:450: in _graph\n    tuple(TaskEventRead(**r) for r in repo.events(task)),\n    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \n\n.0 = <list_iterator object at 0x10d7d9660>\n\n>       tuple(TaskEventRead(**r) for r in repo.events(task)),\n              ^^^^^^^^^^^^^^^^^^\n        tuple(StepEventRead(**r) for r in repo.events(task, step=True)),\n    )\nE   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'\n\nsrc/researchbase/agent_runtime/application/research_task.py:450: TypeError\n----------------------------- Captured stderr call -----------------------------\nERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.831403+00:00\"}\n------------------------------ Captured log call -------------------------------\nERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.831403+00:00\"}\n___ test_injected_failure_rolls_back_task_and_all_results[human_checkpoints] ___\n\nplanning = PlanningFixture(engine=Engine(postgresql+psycopg://researchbase:***@localhost:5432/researchbase_pr212_test_52fdd45ad0e...3d00d26', store=<researchbase.foundation.artifact_store.ContentAddressedFilesystemArtifactStore object at 0x10d638680>)\nmonkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x10d7dbfb0>\npoint = 'human_checkpoints'\n\n    @pytest.mark.parametrize(\n        \"point\",\n        (\n            \"execution_budgets\",\n            \"checkpoint_policies\",\n            \"human_checkpoints\",\n            \"research_task_events\",\n            \"research_task_receipt_events\",\n        ),\n    )\n    def test_injected_failure_rolls_back_task_and_all_results(planning, monkeypatch, point):\n        from researchbase.persistence.task_safety_repository import SqlAlchemyTaskSafetyRepository\n    \n        p = planning\n        task = p.create()\n        if point == \"human_checkpoints\":\n            bind(p, task)\n        revision = 2 if point == \"human_checkpoints\" else 1\n>       before = p.service.get_task_graph(p.principal, p.project, task)\n                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n\ntests/integration/phase3/test_pr3_04_application.py:274: \n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \nsrc/researchbase/agent_runtime/application/research_task.py:459: in get_task_graph\n    return self._graph(uow, project_id, task_id)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nsrc/researchbase/agent_runtime/application/research_task.py:450: in _graph\n    tuple(TaskEventRead(**r) for r in repo.events(task)),\n    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \n\n.0 = <list_iterator object at 0x10d6e3370>\n\n>       tuple(TaskEventRead(**r) for r in repo.events(task)),\n              ^^^^^^^^^^^^^^^^^^\n        tuple(StepEventRead(**r) for r in repo.events(task, step=True)),\n    )\nE   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'\n\nsrc/researchbase/agent_runtime/application/research_task.py:450: TypeError\n----------------------------- Captured stderr call -----------------------------\nERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.852410+00:00\"}\n------------------------------ Captured log call -------------------------------\nERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.852410+00:00\"}\n_ test_injected_failure_rolls_back_task_and_all_results[research_task_events] __\n\nplanning = PlanningFixture(engine=Engine(postgresql+psycopg://researchbase:***@localhost:5432/researchbase_pr212_test_52fdd45ad0e...3d00d26', store=<researchbase.foundation.artifact_store.ContentAddressedFilesystemArtifactStore object at 0x10d638680>)\nmonkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x10d73b500>\npoint = 'research_task_events'\n\n    @pytest.mark.parametrize(\n        \"point\",\n        (\n            \"execution_budgets\",\n            \"checkpoint_policies\",\n            \"human_checkpoints\",\n            \"research_task_events\",\n            \"research_task_receipt_events\",\n        ),\n    )\n    def test_injected_failure_rolls_back_task_and_all_results(planning, monkeypatch, point):\n        from researchbase.persistence.task_safety_repository import SqlAlchemyTaskSafetyRepository\n    \n        p = planning\n        task = p.create()\n        if point == \"human_checkpoints\":\n            bind(p, task)\n        revision = 2 if point == \"human_checkpoints\" else 1\n>       before = p.service.get_task_graph(p.principal, p.project, task)\n                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n\ntests/integration/phase3/test_pr3_04_application.py:274: \n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \nsrc/researchbase/agent_runtime/application/research_task.py:459: in get_task_graph\n    return self._graph(uow, project_id, task_id)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nsrc/researchbase/agent_runtime/application/research_task.py:450: in _graph\n    tuple(TaskEventRead(**r) for r in repo.events(task)),\n    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \n\n.0 = <list_iterator object at 0x10d7c1cf0>\n\n>       tuple(TaskEventRead(**r) for r in repo.events(task)),\n              ^^^^^^^^^^^^^^^^^^\n        tuple(StepEventRead(**r) for r in repo.events(task, step=True)),\n    )\nE   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'\n\nsrc/researchbase/agent_runtime/application/research_task.py:450: TypeError\n----------------------------- Captured stderr call -----------------------------\nERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.862360+00:00\"}\n------------------------------ Captured log call -------------------------------\nERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.862360+00:00\"}\n_ test_injected_failure_rolls_back_task_and_all_results[research_task_receipt_events] _\n\nplanning = PlanningFixture(engine=Engine(postgresql+psycopg://researchbase:***@localhost:5432/researchbase_pr212_test_52fdd45ad0e...3d00d26', store=<researchbase.foundation.artifact_store.ContentAddressedFilesystemArtifactStore object at 0x10d638680>)\nmonkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x10d7c2ea0>\npoint = 'research_task_receipt_events'\n\n    @pytest.mark.parametrize(\n        \"point\",\n        (\n            \"execution_budgets\",\n            \"checkpoint_policies\",\n            \"human_checkpoints\",\n            \"research_task_events\",\n            \"research_task_receipt_events\",\n        ),\n    )\n    def test_injected_failure_rolls_back_task_and_all_results(planning, monkeypatch, point):\n        from researchbase.persistence.task_safety_repository import SqlAlchemyTaskSafetyRepository\n    \n        p = planning\n        task = p.create()\n        if point == \"human_checkpoints\":\n            bind(p, task)\n        revision = 2 if point == \"human_checkpoints\" else 1\n>       before = p.service.get_task_graph(p.principal, p.project, task)\n                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n\ntests/integration/phase3/test_pr3_04_application.py:274: \n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \nsrc/researchbase/agent_runtime/application/research_task.py:459: in get_task_graph\n    return self._graph(uow, project_id, task_id)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nsrc/researchbase/agent_runtime/application/research_task.py:450: in _graph\n    tuple(TaskEventRead(**r) for r in repo.events(task)),\n    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \n\n.0 = <list_iterator object at 0x10d7c3e80>\n\n>       tuple(TaskEventRead(**r) for r in repo.events(task)),\n              ^^^^^^^^^^^^^^^^^^\n        tuple(StepEventRead(**r) for r in repo.events(task, step=True)),\n    )\nE   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'\n\nsrc/researchbase/agent_runtime/application/research_task.py:450: TypeError\n----------------------------- Captured stderr call -----------------------------\nERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.872731+00:00\"}\n------------------------------ Captured log call -------------------------------\nERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:06.872731+00:00\"}\n________ test_response_waits_through_expiry_and_denies_without_effects _________\n\nplanning = PlanningFixture(engine=Engine(postgresql+psycopg://researchbase:***@localhost:5432/researchbase_pr212_test_52fdd45ad0e...3d00d26', store=<researchbase.foundation.artifact_store.ContentAddressedFilesystemArtifactStore object at 0x10d638680>)\nmonkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x10d7a1220>\n\n    def test_response_waits_through_expiry_and_denies_without_effects(planning, monkeypatch):\n        p = planning\n        task = p.create()\n        bind(p, task, checkpoint={\"timeout_seconds\": 2})\n        checkpoint_id = new_uuid7()\n        service(p).execute(\n            p.principal,\n            command(\n                p,\n                task,\n                2,\n                \"request_human_checkpoint\",\n                {\n                    \"checkpoint_id\": str(checkpoint_id),\n                    \"step_id\": None,\n                    \"checkpoint_type\": \"plan_review\",\n                    \"reason\": \"Expiry wait test.\",\n                },\n            ),\n        )\n        times = []\n        original = SqlAlchemyTaskSafetyRepository.at\n    \n        def at(repo):\n            stamp = original(repo)\n            times.append(stamp)\n            return stamp\n    \n        monkeypatch.setattr(SqlAlchemyTaskSafetyRepository, \"at\", at)\n        response = command(\n            p,\n            task,\n            3,\n            \"respond_human_checkpoint\",\n            {\n                \"checkpoint_id\": str(checkpoint_id),\n                \"expected_checkpoint_row_version\": 1,\n                \"response\": \"APPROVED\",\n                \"reason\": \"Late response denied.\",\n            },\n        )\n        with p.engine.connect() as blocker, ThreadPoolExecutor(max_workers=1) as pool:\n            expiry = blocker.execute(\n                text(\"SELECT expires_at FROM human_checkpoints WHERE id=:id\"), {\"id\": checkpoint_id}\n            ).scalar_one()\n            blocker.execute(\n                text(\"SELECT pg_advisory_xact_lock(hashtextextended(:key,0))\"),\n                {\"key\": f\"pr301:task:{task}\"},\n            )\n            future = pool.submit(service(p).execute, p.principal, response)\n            waiting = waiters(p.engine)[0]\n            assert waiting.xact_start < expiry and waiting.waitstart < expiry\n            blocker.execute(\n                text(\"SELECT pg_sleep(greatest(0,extract(epoch FROM (:expiry-clock_timestamp()))))\"),\n                {\"expiry\": expiry},\n            )\n            released = blocker.execute(text(\"SELECT clock_timestamp()\")).scalar_one()\n            blocker.commit()\n            with pytest.raises(ResearchBaseError) as exc:\n                future.result(timeout=5)\n        assert exc.value.code == ErrorCode.INVALID_STATE_TRANSITION\n        assert times[0] < expiry\n        assert released >= expiry and times and times[-1] >= released\n        assert (\n            service(p).get_task_checkpoint_history(p.principal, p.project, task).checkpoints[0].status\n            == \"PENDING\"\n        )\n>       assert p.service.get_research_task(p.principal, p.project, task).row_version == 3\n               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n\ntests/integration/phase3/test_pr3_04_concurrency.py:125: \n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \nsrc/researchbase/agent_runtime/application/research_task.py:462: in get_research_task\n    return self.get_task_graph(principal, project_id, task_id).task\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nsrc/researchbase/agent_runtime/application/research_task.py:459: in get_task_graph\n    return self._graph(uow, project_id, task_id)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nsrc/researchbase/agent_runtime/application/research_task.py:450: in _graph\n    tuple(TaskEventRead(**r) for r in repo.events(task)),\n    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \n\n.0 = <list_iterator object at 0x10d775f00>\n\n>       tuple(TaskEventRead(**r) for r in repo.events(task)),\n              ^^^^^^^^^^^^^^^^^^\n        tuple(StepEventRead(**r) for r in repo.events(task, step=True)),\n    )\nE   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'\n\nsrc/researchbase/agent_runtime/application/research_task.py:450: TypeError\n----------------------------- Captured stderr call -----------------------------\nERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"INVALID_STATE_TRANSITION\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.305315+00:00\"}\nERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.313620+00:00\"}\nERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.317688+00:00\"}\n------------------------------ Captured log call -------------------------------\nERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"INVALID_STATE_TRANSITION\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.305315+00:00\"}\nERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.313620+00:00\"}\nERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.317688+00:00\"}\n_________ test_shared_old_new_command_keys_converge[response_response] _________\n\nplanning = PlanningFixture(engine=Engine(postgresql+psycopg://researchbase:***@localhost:5432/researchbase_pr212_test_52fdd45ad0e...3d00d26', store=<researchbase.foundation.artifact_store.ContentAddressedFilesystemArtifactStore object at 0x10d638680>)\nrace = 'response_response'\n\n    @pytest.mark.parametrize(\n        \"race\", (\"response_response\", \"stop_admission\", \"settlement_stop\", \"bind_seal\", \"bind_cancel\")\n    )\n    def test_shared_old_new_command_keys_converge(planning, race):\n        from tests.integration.phase3.test_pr3_04_application import settle\n    \n        p = planning\n        if race in (\"bind_seal\", \"bind_cancel\"):\n            task, _ = p.plan()\n            c, _ = bind(p, p.create())\n            from dataclasses import replace\n    \n            c = replace(\n                c,\n                task_id=task,\n                expected_row_version=2,\n                command_id=new_uuid7(),\n                arguments=replace(\n                    c.arguments,\n                    budget_id=new_uuid7(),\n                    termination_policy_id=new_uuid7(),\n                    checkpoint_policy_id=new_uuid7(),\n                ),\n            )\n            old = p.command(\n                \"seal_task_plan\" if race == \"bind_seal\" else \"cancel_research_task\",\n                task,\n                2,\n                {} if race == \"bind_seal\" else {\"reason\": \"Concurrent cancel.\"},\n            )\n            calls = [\n                lambda: service(p).execute(p.principal, c),\n                lambda: p.service.execute(p.principal, old),\n            ]\n            expected = 3\n        else:\n            task, fake = setup(p)\n            expected = 5\n            if race == \"response_response\":\n                c = command(\n                    p,\n                    task,\n                    4,\n                    \"request_human_checkpoint\",\n                    {\n                        \"checkpoint_id\": str(new_uuid7()),\n                        \"step_id\": None,\n                        \"checkpoint_type\": \"exception\",\n                        \"reason\": \"Concurrent response.\",\n                    },\n                )\n                service(p).execute(p.principal, c)\n                from researchbase.agent_runtime.application.safety_contracts import (\n                    RequestCheckpointArguments,\n                )\n    \n                assert isinstance(c.arguments, RequestCheckpointArguments)\n                checkpoint_id = c.arguments.checkpoint_id\n                responses = [\n                    command(\n                        p,\n                        task,\n                        5,\n                        \"respond_human_checkpoint\",\n                        {\n                            \"checkpoint_id\": str(checkpoint_id),\n                            \"expected_checkpoint_row_version\": 1,\n                            \"response\": status,\n                            \"reason\": \"Competing response.\",\n                        },\n                    )\n                    for status in (\"APPROVED\", \"REJECTED\")\n                ]\n                calls = [lambda c=c: service(p).execute(p.principal, c) for c in responses]\n                expected = 6\n            elif race == \"stop_admission\":\n                c = command(\n                    p,\n                    task,\n                    4,\n                    \"evaluate_task_termination\",\n                    {\"human_stop\": True, \"reason\": \"Stop before spend.\"},\n                )\n                admission = reserve(p, task, 4)\n                calls = [\n                    lambda: service(p).execute(p.principal, c),\n                    lambda: fake.execute(p.principal, admission),\n                ]\n            else:\n                reservation = fake.execute(p.principal, reserve(p, task, 4)).reservation_ids[0]\n                c = command(\n                    p,\n                    task,\n                    5,\n                    \"evaluate_task_termination\",\n                    {\"human_stop\": True, \"reason\": \"Stop while settling.\"},\n                )\n                measurement = settle(p, task, 5, reservation)\n                calls = [\n                    lambda: service(p).execute(p.principal, c),\n                    lambda: fake.execute(p.principal, measurement),\n                ]\n                expected = 6\n        with p.engine.connect() as blocker, ThreadPoolExecutor(max_workers=2) as pool:\n            blocker.execute(\n                text(\"SELECT pg_advisory_xact_lock(hashtextextended(:key,0))\"),\n                {\"key\": f\"pr301:task:{task}\"},\n            )\n            futures = [pool.submit(call) for call in calls]\n            waiters(p.engine)\n            blocker.commit()\n            successes = 0\n            for future in futures:\n                try:\n                    future.result(timeout=5)\n                    successes += 1\n                except ResearchBaseError as exc:\n                    assert exc.code == ErrorCode.CONCURRENT_MODIFICATION\n        assert successes == 1\n>       assert p.service.get_research_task(p.principal, p.project, task).row_version == expected\n               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n\ntests/integration/phase3/test_pr3_04_concurrency.py:250: \n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \nsrc/researchbase/agent_runtime/application/research_task.py:462: in get_research_task\n    return self.get_task_graph(principal, project_id, task_id).task\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nsrc/researchbase/agent_runtime/application/research_task.py:459: in get_task_graph\n    return self._graph(uow, project_id, task_id)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nsrc/researchbase/agent_runtime/application/research_task.py:450: in _graph\n    tuple(TaskEventRead(**r) for r in repo.events(task)),\n    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \n\n.0 = <list_iterator object at 0x10d7e6680>\n\n>       tuple(TaskEventRead(**r) for r in repo.events(task)),\n              ^^^^^^^^^^^^^^^^^^\n        tuple(StepEventRead(**r) for r in repo.events(task, step=True)),\n    )\nE   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'\n\nsrc/researchbase/agent_runtime/application/research_task.py:450: TypeError\n----------------------------- Captured stderr call -----------------------------\nERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"CONCURRENT_MODIFICATION\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.478224+00:00\"}\nERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.480613+00:00\"}\n------------------------------ Captured log call -------------------------------\nERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"CONCURRENT_MODIFICATION\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.478224+00:00\"}\nERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.480613+00:00\"}\n__________ test_shared_old_new_command_keys_converge[stop_admission] ___________\n\nplanning = PlanningFixture(engine=Engine(postgresql+psycopg://researchbase:***@localhost:5432/researchbase_pr212_test_52fdd45ad0e...3d00d26', store=<researchbase.foundation.artifact_store.ContentAddressedFilesystemArtifactStore object at 0x10d638680>)\nrace = 'stop_admission'\n\n    @pytest.mark.parametrize(\n        \"race\", (\"response_response\", \"stop_admission\", \"settlement_stop\", \"bind_seal\", \"bind_cancel\")\n    )\n    def test_shared_old_new_command_keys_converge(planning, race):\n        from tests.integration.phase3.test_pr3_04_application import settle\n    \n        p = planning\n        if race in (\"bind_seal\", \"bind_cancel\"):\n            task, _ = p.plan()\n            c, _ = bind(p, p.create())\n            from dataclasses import replace\n    \n            c = replace(\n                c,\n                task_id=task,\n                expected_row_version=2,\n                command_id=new_uuid7(),\n                arguments=replace(\n                    c.arguments,\n                    budget_id=new_uuid7(),\n                    termination_policy_id=new_uuid7(),\n                    checkpoint_policy_id=new_uuid7(),\n                ),\n            )\n            old = p.command(\n                \"seal_task_plan\" if race == \"bind_seal\" else \"cancel_research_task\",\n                task,\n                2,\n                {} if race == \"bind_seal\" else {\"reason\": \"Concurrent cancel.\"},\n            )\n            calls = [\n                lambda: service(p).execute(p.principal, c),\n                lambda: p.service.execute(p.principal, old),\n            ]\n            expected = 3\n        else:\n            task, fake = setup(p)\n            expected = 5\n            if race == \"response_response\":\n                c = command(\n                    p,\n                    task,\n                    4,\n                    \"request_human_checkpoint\",\n                    {\n                        \"checkpoint_id\": str(new_uuid7()),\n                        \"step_id\": None,\n                        \"checkpoint_type\": \"exception\",\n                        \"reason\": \"Concurrent response.\",\n                    },\n                )\n                service(p).execute(p.principal, c)\n                from researchbase.agent_runtime.application.safety_contracts import (\n                    RequestCheckpointArguments,\n                )\n    \n                assert isinstance(c.arguments, RequestCheckpointArguments)\n                checkpoint_id = c.arguments.checkpoint_id\n                responses = [\n                    command(\n                        p,\n                        task,\n                        5,\n                        \"respond_human_checkpoint\",\n                        {\n                            \"checkpoint_id\": str(checkpoint_id),\n                            \"expected_checkpoint_row_version\": 1,\n                            \"response\": status,\n                            \"reason\": \"Competing response.\",\n                        },\n                    )\n                    for status in (\"APPROVED\", \"REJECTED\")\n                ]\n                calls = [lambda c=c: service(p).execute(p.principal, c) for c in responses]\n                expected = 6\n            elif race == \"stop_admission\":\n                c = command(\n                    p,\n                    task,\n                    4,\n                    \"evaluate_task_termination\",\n                    {\"human_stop\": True, \"reason\": \"Stop before spend.\"},\n                )\n                admission = reserve(p, task, 4)\n                calls = [\n                    lambda: service(p).execute(p.principal, c),\n                    lambda: fake.execute(p.principal, admission),\n                ]\n            else:\n                reservation = fake.execute(p.principal, reserve(p, task, 4)).reservation_ids[0]\n                c = command(\n                    p,\n                    task,\n                    5,\n                    \"evaluate_task_termination\",\n                    {\"human_stop\": True, \"reason\": \"Stop while settling.\"},\n                )\n                measurement = settle(p, task, 5, reservation)\n                calls = [\n                    lambda: service(p).execute(p.principal, c),\n                    lambda: fake.execute(p.principal, measurement),\n                ]\n                expected = 6\n        with p.engine.connect() as blocker, ThreadPoolExecutor(max_workers=2) as pool:\n            blocker.execute(\n                text(\"SELECT pg_advisory_xact_lock(hashtextextended(:key,0))\"),\n                {\"key\": f\"pr301:task:{task}\"},\n            )\n            futures = [pool.submit(call) for call in calls]\n            waiters(p.engine)\n            blocker.commit()\n            successes = 0\n            for future in futures:\n                try:\n                    future.result(timeout=5)\n                    successes += 1\n                except ResearchBaseError as exc:\n                    assert exc.code == ErrorCode.CONCURRENT_MODIFICATION\n        assert successes == 1\n>       assert p.service.get_research_task(p.principal, p.project, task).row_version == expected\n               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n\ntests/integration/phase3/test_pr3_04_concurrency.py:250: \n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \nsrc/researchbase/agent_runtime/application/research_task.py:462: in get_research_task\n    return self.get_task_graph(principal, project_id, task_id).task\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nsrc/researchbase/agent_runtime/application/research_task.py:459: in get_task_graph\n    return self._graph(uow, project_id, task_id)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nsrc/researchbase/agent_runtime/application/research_task.py:450: in _graph\n    tuple(TaskEventRead(**r) for r in repo.events(task)),\n    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \n\n.0 = <list_iterator object at 0x10d7bab00>\n\n>       tuple(TaskEventRead(**r) for r in repo.events(task)),\n              ^^^^^^^^^^^^^^^^^^\n        tuple(StepEventRead(**r) for r in repo.events(task, step=True)),\n    )\nE   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'\n\nsrc/researchbase/agent_runtime/application/research_task.py:450: TypeError\n----------------------------- Captured stderr call -----------------------------\nERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"CONCURRENT_MODIFICATION\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.571392+00:00\"}\nERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.572812+00:00\"}\n------------------------------ Captured log call -------------------------------\nERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"CONCURRENT_MODIFICATION\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.571392+00:00\"}\nERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.572812+00:00\"}\n__________ test_shared_old_new_command_keys_converge[settlement_stop] __________\n\nplanning = PlanningFixture(engine=Engine(postgresql+psycopg://researchbase:***@localhost:5432/researchbase_pr212_test_52fdd45ad0e...3d00d26', store=<researchbase.foundation.artifact_store.ContentAddressedFilesystemArtifactStore object at 0x10d638680>)\nrace = 'settlement_stop'\n\n    @pytest.mark.parametrize(\n        \"race\", (\"response_response\", \"stop_admission\", \"settlement_stop\", \"bind_seal\", \"bind_cancel\")\n    )\n    def test_shared_old_new_command_keys_converge(planning, race):\n        from tests.integration.phase3.test_pr3_04_application import settle\n    \n        p = planning\n        if race in (\"bind_seal\", \"bind_cancel\"):\n            task, _ = p.plan()\n            c, _ = bind(p, p.create())\n            from dataclasses import replace\n    \n            c = replace(\n                c,\n                task_id=task,\n                expected_row_version=2,\n                command_id=new_uuid7(),\n                arguments=replace(\n                    c.arguments,\n                    budget_id=new_uuid7(),\n                    termination_policy_id=new_uuid7(),\n                    checkpoint_policy_id=new_uuid7(),\n                ),\n            )\n            old = p.command(\n                \"seal_task_plan\" if race == \"bind_seal\" else \"cancel_research_task\",\n                task,\n                2,\n                {} if race == \"bind_seal\" else {\"reason\": \"Concurrent cancel.\"},\n            )\n            calls = [\n                lambda: service(p).execute(p.principal, c),\n                lambda: p.service.execute(p.principal, old),\n            ]\n            expected = 3\n        else:\n            task, fake = setup(p)\n            expected = 5\n            if race == \"response_response\":\n                c = command(\n                    p,\n                    task,\n                    4,\n                    \"request_human_checkpoint\",\n                    {\n                        \"checkpoint_id\": str(new_uuid7()),\n                        \"step_id\": None,\n                        \"checkpoint_type\": \"exception\",\n                        \"reason\": \"Concurrent response.\",\n                    },\n                )\n                service(p).execute(p.principal, c)\n                from researchbase.agent_runtime.application.safety_contracts import (\n                    RequestCheckpointArguments,\n                )\n    \n                assert isinstance(c.arguments, RequestCheckpointArguments)\n                checkpoint_id = c.arguments.checkpoint_id\n                responses = [\n                    command(\n                        p,\n                        task,\n                        5,\n                        \"respond_human_checkpoint\",\n                        {\n                            \"checkpoint_id\": str(checkpoint_id),\n                            \"expected_checkpoint_row_version\": 1,\n                            \"response\": status,\n                            \"reason\": \"Competing response.\",\n                        },\n                    )\n                    for status in (\"APPROVED\", \"REJECTED\")\n                ]\n                calls = [lambda c=c: service(p).execute(p.principal, c) for c in responses]\n                expected = 6\n            elif race == \"stop_admission\":\n                c = command(\n                    p,\n                    task,\n                    4,\n                    \"evaluate_task_termination\",\n                    {\"human_stop\": True, \"reason\": \"Stop before spend.\"},\n                )\n                admission = reserve(p, task, 4)\n                calls = [\n                    lambda: service(p).execute(p.principal, c),\n                    lambda: fake.execute(p.principal, admission),\n                ]\n            else:\n                reservation = fake.execute(p.principal, reserve(p, task, 4)).reservation_ids[0]\n                c = command(\n                    p,\n                    task,\n                    5,\n                    \"evaluate_task_termination\",\n                    {\"human_stop\": True, \"reason\": \"Stop while settling.\"},\n                )\n                measurement = settle(p, task, 5, reservation)\n                calls = [\n                    lambda: service(p).execute(p.principal, c),\n                    lambda: fake.execute(p.principal, measurement),\n                ]\n                expected = 6\n        with p.engine.connect() as blocker, ThreadPoolExecutor(max_workers=2) as pool:\n            blocker.execute(\n                text(\"SELECT pg_advisory_xact_lock(hashtextextended(:key,0))\"),\n                {\"key\": f\"pr301:task:{task}\"},\n            )\n            futures = [pool.submit(call) for call in calls]\n            waiters(p.engine)\n            blocker.commit()\n            successes = 0\n            for future in futures:\n                try:\n                    future.result(timeout=5)\n                    successes += 1\n                except ResearchBaseError as exc:\n                    assert exc.code == ErrorCode.CONCURRENT_MODIFICATION\n        assert successes == 1\n>       assert p.service.get_research_task(p.principal, p.project, task).row_version == expected\n               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n\ntests/integration/phase3/test_pr3_04_concurrency.py:250: \n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \nsrc/researchbase/agent_runtime/application/research_task.py:462: in get_research_task\n    return self.get_task_graph(principal, project_id, task_id).task\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nsrc/researchbase/agent_runtime/application/research_task.py:459: in get_task_graph\n    return self._graph(uow, project_id, task_id)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nsrc/researchbase/agent_runtime/application/research_task.py:450: in _graph\n    tuple(TaskEventRead(**r) for r in repo.events(task)),\n    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \n\n.0 = <list_iterator object at 0x10d7bb700>\n\n>       tuple(TaskEventRead(**r) for r in repo.events(task)),\n              ^^^^^^^^^^^^^^^^^^\n        tuple(StepEventRead(**r) for r in repo.events(task, step=True)),\n    )\nE   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'\n\nsrc/researchbase/agent_runtime/application/research_task.py:450: TypeError\n----------------------------- Captured stderr call -----------------------------\nERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"CONCURRENT_MODIFICATION\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.648700+00:00\"}\nERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.650314+00:00\"}\n------------------------------ Captured log call -------------------------------\nERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"CONCURRENT_MODIFICATION\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.648700+00:00\"}\nERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.650314+00:00\"}\n_____________ test_shared_old_new_command_keys_converge[bind_seal] _____________\n\nplanning = PlanningFixture(engine=Engine(postgresql+psycopg://researchbase:***@localhost:5432/researchbase_pr212_test_52fdd45ad0e...3d00d26', store=<researchbase.foundation.artifact_store.ContentAddressedFilesystemArtifactStore object at 0x10d638680>)\nrace = 'bind_seal'\n\n    @pytest.mark.parametrize(\n        \"race\", (\"response_response\", \"stop_admission\", \"settlement_stop\", \"bind_seal\", \"bind_cancel\")\n    )\n    def test_shared_old_new_command_keys_converge(planning, race):\n        from tests.integration.phase3.test_pr3_04_application import settle\n    \n        p = planning\n        if race in (\"bind_seal\", \"bind_cancel\"):\n            task, _ = p.plan()\n            c, _ = bind(p, p.create())\n            from dataclasses import replace\n    \n            c = replace(\n                c,\n                task_id=task,\n                expected_row_version=2,\n                command_id=new_uuid7(),\n                arguments=replace(\n                    c.arguments,\n                    budget_id=new_uuid7(),\n                    termination_policy_id=new_uuid7(),\n                    checkpoint_policy_id=new_uuid7(),\n                ),\n            )\n            old = p.command(\n                \"seal_task_plan\" if race == \"bind_seal\" else \"cancel_research_task\",\n                task,\n                2,\n                {} if race == \"bind_seal\" else {\"reason\": \"Concurrent cancel.\"},\n            )\n            calls = [\n                lambda: service(p).execute(p.principal, c),\n                lambda: p.service.execute(p.principal, old),\n            ]\n            expected = 3\n        else:\n            task, fake = setup(p)\n            expected = 5\n            if race == \"response_response\":\n                c = command(\n                    p,\n                    task,\n                    4,\n                    \"request_human_checkpoint\",\n                    {\n                        \"checkpoint_id\": str(new_uuid7()),\n                        \"step_id\": None,\n                        \"checkpoint_type\": \"exception\",\n                        \"reason\": \"Concurrent response.\",\n                    },\n                )\n                service(p).execute(p.principal, c)\n                from researchbase.agent_runtime.application.safety_contracts import (\n                    RequestCheckpointArguments,\n                )\n    \n                assert isinstance(c.arguments, RequestCheckpointArguments)\n                checkpoint_id = c.arguments.checkpoint_id\n                responses = [\n                    command(\n                        p,\n                        task,\n                        5,\n                        \"respond_human_checkpoint\",\n                        {\n                            \"checkpoint_id\": str(checkpoint_id),\n                            \"expected_checkpoint_row_version\": 1,\n                            \"response\": status,\n                            \"reason\": \"Competing response.\",\n                        },\n                    )\n                    for status in (\"APPROVED\", \"REJECTED\")\n                ]\n                calls = [lambda c=c: service(p).execute(p.principal, c) for c in responses]\n                expected = 6\n            elif race == \"stop_admission\":\n                c = command(\n                    p,\n                    task,\n                    4,\n                    \"evaluate_task_termination\",\n                    {\"human_stop\": True, \"reason\": \"Stop before spend.\"},\n                )\n                admission = reserve(p, task, 4)\n                calls = [\n                    lambda: service(p).execute(p.principal, c),\n                    lambda: fake.execute(p.principal, admission),\n                ]\n            else:\n                reservation = fake.execute(p.principal, reserve(p, task, 4)).reservation_ids[0]\n                c = command(\n                    p,\n                    task,\n                    5,\n                    \"evaluate_task_termination\",\n                    {\"human_stop\": True, \"reason\": \"Stop while settling.\"},\n                )\n                measurement = settle(p, task, 5, reservation)\n                calls = [\n                    lambda: service(p).execute(p.principal, c),\n                    lambda: fake.execute(p.principal, measurement),\n                ]\n                expected = 6\n        with p.engine.connect() as blocker, ThreadPoolExecutor(max_workers=2) as pool:\n            blocker.execute(\n                text(\"SELECT pg_advisory_xact_lock(hashtextextended(:key,0))\"),\n                {\"key\": f\"pr301:task:{task}\"},\n            )\n            futures = [pool.submit(call) for call in calls]\n            waiters(p.engine)\n            blocker.commit()\n            successes = 0\n            for future in futures:\n                try:\n                    future.result(timeout=5)\n                    successes += 1\n                except ResearchBaseError as exc:\n                    assert exc.code == ErrorCode.CONCURRENT_MODIFICATION\n        assert successes == 1\n>       assert p.service.get_research_task(p.principal, p.project, task).row_version == expected\n               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n\ntests/integration/phase3/test_pr3_04_concurrency.py:250: \n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \nsrc/researchbase/agent_runtime/application/research_task.py:462: in get_research_task\n    return self.get_task_graph(principal, project_id, task_id).task\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nsrc/researchbase/agent_runtime/application/research_task.py:459: in get_task_graph\n    return self._graph(uow, project_id, task_id)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nsrc/researchbase/agent_runtime/application/research_task.py:450: in _graph\n    tuple(TaskEventRead(**r) for r in repo.events(task)),\n    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \n\n.0 = <list_iterator object at 0x10d7e6530>\n\n>       tuple(TaskEventRead(**r) for r in repo.events(task)),\n              ^^^^^^^^^^^^^^^^^^\n        tuple(StepEventRead(**r) for r in repo.events(task, step=True)),\n    )\nE   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'\n\nsrc/researchbase/agent_runtime/application/research_task.py:450: TypeError\n----------------------------- Captured stderr call -----------------------------\nERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"CONCURRENT_MODIFICATION\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.707031+00:00\"}\nERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.708336+00:00\"}\n------------------------------ Captured log call -------------------------------\nERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"CONCURRENT_MODIFICATION\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.707031+00:00\"}\nERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.708336+00:00\"}\n____________ test_shared_old_new_command_keys_converge[bind_cancel] ____________\n\nplanning = PlanningFixture(engine=Engine(postgresql+psycopg://researchbase:***@localhost:5432/researchbase_pr212_test_52fdd45ad0e...3d00d26', store=<researchbase.foundation.artifact_store.ContentAddressedFilesystemArtifactStore object at 0x10d638680>)\nrace = 'bind_cancel'\n\n    @pytest.mark.parametrize(\n        \"race\", (\"response_response\", \"stop_admission\", \"settlement_stop\", \"bind_seal\", \"bind_cancel\")\n    )\n    def test_shared_old_new_command_keys_converge(planning, race):\n        from tests.integration.phase3.test_pr3_04_application import settle\n    \n        p = planning\n        if race in (\"bind_seal\", \"bind_cancel\"):\n            task, _ = p.plan()\n            c, _ = bind(p, p.create())\n            from dataclasses import replace\n    \n            c = replace(\n                c,\n                task_id=task,\n                expected_row_version=2,\n                command_id=new_uuid7(),\n                arguments=replace(\n                    c.arguments,\n                    budget_id=new_uuid7(),\n                    termination_policy_id=new_uuid7(),\n                    checkpoint_policy_id=new_uuid7(),\n                ),\n            )\n            old = p.command(\n                \"seal_task_plan\" if race == \"bind_seal\" else \"cancel_research_task\",\n                task,\n                2,\n                {} if race == \"bind_seal\" else {\"reason\": \"Concurrent cancel.\"},\n            )\n            calls = [\n                lambda: service(p).execute(p.principal, c),\n                lambda: p.service.execute(p.principal, old),\n            ]\n            expected = 3\n        else:\n            task, fake = setup(p)\n            expected = 5\n            if race == \"response_response\":\n                c = command(\n                    p,\n                    task,\n                    4,\n                    \"request_human_checkpoint\",\n                    {\n                        \"checkpoint_id\": str(new_uuid7()),\n                        \"step_id\": None,\n                        \"checkpoint_type\": \"exception\",\n                        \"reason\": \"Concurrent response.\",\n                    },\n                )\n                service(p).execute(p.principal, c)\n                from researchbase.agent_runtime.application.safety_contracts import (\n                    RequestCheckpointArguments,\n                )\n    \n                assert isinstance(c.arguments, RequestCheckpointArguments)\n                checkpoint_id = c.arguments.checkpoint_id\n                responses = [\n                    command(\n                        p,\n                        task,\n                        5,\n                        \"respond_human_checkpoint\",\n                        {\n                            \"checkpoint_id\": str(checkpoint_id),\n                            \"expected_checkpoint_row_version\": 1,\n                            \"response\": status,\n                            \"reason\": \"Competing response.\",\n                        },\n                    )\n                    for status in (\"APPROVED\", \"REJECTED\")\n                ]\n                calls = [lambda c=c: service(p).execute(p.principal, c) for c in responses]\n                expected = 6\n            elif race == \"stop_admission\":\n                c = command(\n                    p,\n                    task,\n                    4,\n                    \"evaluate_task_termination\",\n                    {\"human_stop\": True, \"reason\": \"Stop before spend.\"},\n                )\n                admission = reserve(p, task, 4)\n                calls = [\n                    lambda: service(p).execute(p.principal, c),\n                    lambda: fake.execute(p.principal, admission),\n                ]\n            else:\n                reservation = fake.execute(p.principal, reserve(p, task, 4)).reservation_ids[0]\n                c = command(\n                    p,\n                    task,\n                    5,\n                    \"evaluate_task_termination\",\n                    {\"human_stop\": True, \"reason\": \"Stop while settling.\"},\n                )\n                measurement = settle(p, task, 5, reservation)\n                calls = [\n                    lambda: service(p).execute(p.principal, c),\n                    lambda: fake.execute(p.principal, measurement),\n                ]\n                expected = 6\n        with p.engine.connect() as blocker, ThreadPoolExecutor(max_workers=2) as pool:\n            blocker.execute(\n                text(\"SELECT pg_advisory_xact_lock(hashtextextended(:key,0))\"),\n                {\"key\": f\"pr301:task:{task}\"},\n            )\n            futures = [pool.submit(call) for call in calls]\n            waiters(p.engine)\n            blocker.commit()\n            successes = 0\n            for future in futures:\n                try:\n                    future.result(timeout=5)\n                    successes += 1\n                except ResearchBaseError as exc:\n                    assert exc.code == ErrorCode.CONCURRENT_MODIFICATION\n        assert successes == 1\n>       assert p.service.get_research_task(p.principal, p.project, task).row_version == expected\n               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n\ntests/integration/phase3/test_pr3_04_concurrency.py:250: \n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \nsrc/researchbase/agent_runtime/application/research_task.py:462: in get_research_task\n    return self.get_task_graph(principal, project_id, task_id).task\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nsrc/researchbase/agent_runtime/application/research_task.py:459: in get_task_graph\n    return self._graph(uow, project_id, task_id)\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nsrc/researchbase/agent_runtime/application/research_task.py:450: in _graph\n    tuple(TaskEventRead(**r) for r in repo.events(task)),\n    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ \n\n.0 = <list_iterator object at 0x10d7baa10>\n\n>       tuple(TaskEventRead(**r) for r in repo.events(task)),\n              ^^^^^^^^^^^^^^^^^^\n        tuple(StepEventRead(**r) for r in repo.events(task, step=True)),\n    )\nE   TypeError: TaskEventRead.__init__() got an unexpected keyword argument 'result_tool_policy_id'\n\nsrc/researchbase/agent_runtime/application/research_task.py:450: TypeError\n----------------------------- Captured stderr call -----------------------------\nERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"CONCURRENT_MODIFICATION\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.762439+00:00\"}\nERROR [researchbase.commands] {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.763694+00:00\"}\n------------------------------ Captured log call -------------------------------\nERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": \"CONCURRENT_MODIFICATION\", \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.762439+00:00\"}\nERROR    researchbase.commands:structured_logging.py:118 {\"actor_id\": null, \"application_env\": \"development\", \"command_name\": \"unknown\", \"correlation_id\": null, \"duration_ms\": 0, \"error_code\": null, \"level\": \"ERROR\", \"project_id\": null, \"request_id\": null, \"result\": \"failure\", \"rollback\": true, \"target_id\": null, \"timestamp\": \"2026-10-22T16:13:09.763694+00:00\"}\n=============================== warnings summary ===============================\ntests/integration/phase3/test_pr3_04_application.py::test_bind_checkpoint_reserve_settle_and_read\ntests/integration/phase3/test_pr3_04_application.py::test_bind_checkpoint_reserve_settle_and_read\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.\n    util.warn_deprecated(\n\n-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html\n=========================== short test summary info ============================\nFAILED tests/integration/phase3/test_pr3_04_application.py::test_binding_preserves_plan_and_cancel_bookkeeping[False]\nFAILED tests/integration/phase3/test_pr3_04_application.py::test_binding_preserves_plan_and_cancel_bookkeeping[True]\nFAILED tests/integration/phase3/test_pr3_04_application.py::test_public_reserve_denies_without_effects\nFAILED tests/integration/phase3/test_pr3_04_application.py::test_injected_failure_rolls_back_task_and_all_results[execution_budgets]\nFAILED tests/integration/phase3/test_pr3_04_application.py::test_injected_failure_rolls_back_task_and_all_results[checkpoint_policies]\nFAILED tests/integration/phase3/test_pr3_04_application.py::test_injected_failure_rolls_back_task_and_all_results[human_checkpoints]\nFAILED tests/integration/phase3/test_pr3_04_application.py::test_injected_failure_rolls_back_task_and_all_results[research_task_events]\nFAILED tests/integration/phase3/test_pr3_04_application.py::test_injected_failure_rolls_back_task_and_all_results[research_task_receipt_events]\nFAILED tests/integration/phase3/test_pr3_04_concurrency.py::test_response_waits_through_expiry_and_denies_without_effects\nFAILED tests/integration/phase3/test_pr3_04_concurrency.py::test_shared_old_new_command_keys_converge[response_response]\nFAILED tests/integration/phase3/test_pr3_04_concurrency.py::test_shared_old_new_command_keys_converge[stop_admission]\nFAILED tests/integration/phase3/test_pr3_04_concurrency.py::test_shared_old_new_command_keys_converge[settlement_stop]\nFAILED tests/integration/phase3/test_pr3_04_concurrency.py::test_shared_old_new_command_keys_converge[bind_seal]\nFAILED tests/integration/phase3/test_pr3_04_concurrency.py::test_shared_old_new_command_keys_converge[bind_cancel]\n================== 14 failed, 19 passed, 2 warnings in 4.00s ===================\n",
    "stderr": ""
  }
]
```

Capture `tmp/pr3-03/s2-postgres-final.json`:

```json
[
  {
    "command": "uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_04_application.py tests/integration/phase3/test_pr3_04_concurrency.py tests/integration/phase3/test_pr3_04_replay.py",
    "exit_code": 0,
    "stdout": "============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 33 items\n\ntests/integration/phase3/test_pr3_04_application.py .................... [ 60%]\n..                                                                       [ 66%]\ntests/integration/phase3/test_pr3_04_concurrency.py .......              [ 87%]\ntests/integration/phase3/test_pr3_04_replay.py ....                      [100%]\n\n=============================== warnings summary ===============================\ntests/integration/phase3/test_pr3_04_application.py::test_bind_checkpoint_reserve_settle_and_read\ntests/integration/phase3/test_pr3_04_application.py::test_bind_checkpoint_reserve_settle_and_read\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.\n    util.warn_deprecated(\n\n-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html\n======================== 33 passed, 2 warnings in 4.40s ========================\n",
    "stderr": ""
  },
  {
    "command": "uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_01_application.py tests/integration/phase3/test_pr3_04_queries.py",
    "exit_code": 0,
    "stdout": "============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 9 items\n\ntests/integration/phase3/test_pr3_01_application.py .......              [ 77%]\ntests/integration/phase3/test_pr3_04_queries.py ..                       [100%]\n\n=============================== warnings summary ===============================\ntests/integration/phase3/test_pr3_01_application.py::test_task_plan_seal_cancel_and_snapshot\ntests/integration/phase3/test_pr3_01_application.py::test_task_plan_seal_cancel_and_snapshot\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.\n    util.warn_deprecated(\n\n-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html\n======================== 9 passed, 2 warnings in 2.47s =========================\n",
    "stderr": ""
  }
]
```

Capture `tmp/pr3-03/s2-metadata.json`:

```json
[
  {
    "command": "uv run python tmp/pr3-03/s2_metadata_probe.py",
    "exit_code": 1,
    "stdout": "",
    "stderr": "Traceback (most recent call last):\n  File \"/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tmp/pr3-03/s2_metadata_probe.py\", line 7, in <module>\n    from tests.disposable_postgres import disposable_database\nModuleNotFoundError: No module named 'tests'\n"
  }
]
```

Capture `tmp/pr3-03/s2-metadata-retry.json`:

```json
[
  {
    "command": "PYTHONPATH=. uv run python tmp/pr3-03/s2_metadata_probe.py",
    "exit_code": 0,
    "stdout": "DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948\nDISPOSABLE_CREATED: researchbase_pr212_test_18ef7a885c3c49e689365f54ac3bb3b9\nSERVER_VERSION_NUM 180006\nDATABASE_ROLE researchbase\nSERVER_ENCODING UTF8\nMETADATA_MATCH agent_tool_policies columns 18 foreign_keys 5 unique 2 indexes 4 checks 11\nMETADATA_MATCH agent_tool_policy_permissions columns 10 foreign_keys 1 unique 1 indexes 2 checks 7\nMETADATA_MATCH capability_invocations columns 41 foreign_keys 14 unique 8 indexes 12 checks 26\nMETADATA_MATCH capability_invocation_refs columns 14 foreign_keys 8 unique 0 indexes 15 checks 5\nMETADATA_MATCH capability_invocation_events columns 16 foreign_keys 5 unique 4 indexes 4 checks 9\nNULLABLE_EXTENSIONS_MATCH research_task_command_receipts 4\nNULLABLE_EXTENSIONS_MATCH research_task_events 3\nMETADATA_GATE 5/5 tables 7/7 nullable extensions\nDISPOSABLE_DROPPED: researchbase_pr212_test_18ef7a885c3c49e689365f54ac3bb3b9\n",
    "stderr": "INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.\nINFO  [alembic.runtime.migration] Will assume transactional DDL.\nINFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.\nINFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.\nINFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.\nINFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.\nINFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.\nINFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.\nINFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.\nINFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.\nINFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.\nINFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.\nINFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.\nINFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.\nINFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.\nINFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.\nINFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.\nINFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.\nINFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.\nINFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.\nINFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.\nINFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.\nINFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.\nINFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.\nINFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.\nINFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.\nINFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.\nINFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.\nINFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.\nINFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.\nINFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.\nINFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.\nINFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.\nINFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.\nINFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.\nINFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.\nINFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.\nINFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.\nINFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.\nINFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.\nINFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.\nINFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.\nINFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.\nINFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.\nINFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.\nINFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.\nINFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.\nINFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.\nINFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.\nINFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.\nINFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.\nINFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.\nINFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.\nINFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.\nINFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.\nINFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.\nINFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.\nINFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.\nINFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.\nINFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.\nINFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.\nINFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.\nINFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.\nINFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.\nINFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.\nINFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.\nINFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.\nINFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.\nINFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.\nINFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.\nINFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.\nINFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.\nINFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.\nINFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.\nINFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.\nINFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.\nINFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).\nINFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.\nINFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.\nINFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.\nINFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.\nINFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.\nINFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.\nINFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.\n"
  }
]
```

Capture `tmp/pr3-03/s2-before-index-review.json`:

```json
[
  {
    "command": "git diff --check HEAD",
    "exit_code": 0,
    "stdout": "",
    "stderr": ""
  },
  {
    "command": "uv run ruff check .",
    "exit_code": 0,
    "stdout": "All checks passed!\n",
    "stderr": ""
  },
  {
    "command": "uv run ruff format --check .",
    "exit_code": 0,
    "stdout": "892 files already formatted\n",
    "stderr": ""
  },
  {
    "command": "uv run pyright",
    "exit_code": 0,
    "stdout": "0 errors, 0 warnings, 0 informations\nWARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).\nPlease install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`\n\n",
    "stderr": ""
  },
  {
    "command": "uv run alembic heads",
    "exit_code": 0,
    "stdout": "0080_capability_gateway (head)\n",
    "stderr": ""
  },
  {
    "command": "uv run pytest -o addopts='' -ra tests/unit/phase3/test_capability_gateway_repository.py",
    "exit_code": 0,
    "stdout": "============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 29 items\n\ntests/unit/phase3/test_capability_gateway_repository.py ................ [ 55%]\n.............                                                            [100%]\n\n============================== 29 passed in 0.17s ==============================\n",
    "stderr": ""
  },
  {
    "command": "uv run pytest -o addopts='' -ra tests/unit/phase3/test_task_safety_transports.py tests/architecture/test_pr3_04_boundaries.py tests/architecture/test_pr3_02_s1_boundaries.py",
    "exit_code": 0,
    "stdout": "============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 14 items\n\ntests/unit/phase3/test_task_safety_transports.py ..........              [ 71%]\ntests/architecture/test_pr3_04_boundaries.py ..                          [ 85%]\ntests/architecture/test_pr3_02_s1_boundaries.py ..                       [100%]\n\n=============================== warnings summary ===============================\ntests/architecture/test_pr3_02_s1_boundaries.py::test_authorized_head_and_s1_only\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.\n    util.warn_deprecated(\n\n-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html\n======================== 14 passed, 1 warning in 1.20s =========================\n",
    "stderr": ""
  },
  {
    "command": "PYTHONPATH=. uv run python tmp/pr3-03/s2_metadata_probe.py",
    "exit_code": 0,
    "stdout": "DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948\nDISPOSABLE_CREATED: researchbase_pr212_test_2494e012137a4822bcdcde1b0fe39405\nSERVER_VERSION_NUM 180006\nDATABASE_ROLE researchbase\nSERVER_ENCODING UTF8\nMETADATA_MATCH agent_tool_policies columns 18 foreign_keys 5 unique 2 indexes 4 checks 11\nMETADATA_MATCH agent_tool_policy_permissions columns 10 foreign_keys 1 unique 1 indexes 2 checks 7\nMETADATA_MATCH capability_invocations columns 41 foreign_keys 14 unique 8 indexes 12 checks 26\nMETADATA_MATCH capability_invocation_refs columns 14 foreign_keys 8 unique 0 indexes 15 checks 5\nMETADATA_MATCH capability_invocation_events columns 16 foreign_keys 5 unique 4 indexes 4 checks 9\nNULLABLE_EXTENSIONS_MATCH research_task_command_receipts 4\nNULLABLE_EXTENSIONS_MATCH research_task_events 3\nMETADATA_GATE 5/5 tables 7/7 nullable extensions\nDISPOSABLE_DROPPED: researchbase_pr212_test_2494e012137a4822bcdcde1b0fe39405\n",
    "stderr": "INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.\nINFO  [alembic.runtime.migration] Will assume transactional DDL.\nINFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.\nINFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.\nINFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.\nINFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.\nINFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.\nINFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.\nINFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.\nINFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.\nINFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.\nINFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.\nINFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.\nINFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.\nINFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.\nINFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.\nINFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.\nINFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.\nINFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.\nINFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.\nINFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.\nINFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.\nINFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.\nINFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.\nINFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.\nINFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.\nINFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.\nINFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.\nINFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.\nINFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.\nINFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.\nINFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.\nINFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.\nINFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.\nINFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.\nINFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.\nINFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.\nINFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.\nINFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.\nINFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.\nINFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.\nINFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.\nINFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.\nINFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.\nINFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.\nINFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.\nINFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.\nINFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.\nINFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.\nINFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.\nINFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.\nINFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.\nINFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.\nINFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.\nINFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.\nINFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.\nINFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.\nINFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.\nINFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.\nINFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.\nINFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.\nINFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.\nINFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.\nINFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.\nINFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.\nINFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.\nINFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.\nINFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.\nINFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.\nINFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.\nINFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.\nINFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.\nINFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.\nINFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.\nINFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.\nINFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.\nINFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).\nINFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.\nINFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.\nINFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.\nINFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.\nINFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.\nINFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.\nINFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.\n"
  }
]
```

Capture `tmp/pr3-03/s2-final.json`:

```json
[
  {
    "command": "git diff --check HEAD",
    "exit_code": 0,
    "stdout": "",
    "stderr": ""
  },
  {
    "command": "uv run ruff check .",
    "exit_code": 0,
    "stdout": "All checks passed!\n",
    "stderr": ""
  },
  {
    "command": "uv run ruff format --check .",
    "exit_code": 0,
    "stdout": "892 files already formatted\n",
    "stderr": ""
  },
  {
    "command": "uv run pyright",
    "exit_code": 0,
    "stdout": "0 errors, 0 warnings, 0 informations\nWARNING: there is a new pyright version available (v1.1.411 -> v1.1.414).\nPlease install the new version or set PYRIGHT_PYTHON_FORCE_VERSION to `latest`\n\n",
    "stderr": ""
  },
  {
    "command": "uv run alembic heads",
    "exit_code": 0,
    "stdout": "0080_capability_gateway (head)\n",
    "stderr": ""
  },
  {
    "command": "uv run pytest -o addopts='' -ra tests/unit/phase3/test_capability_gateway_repository.py",
    "exit_code": 0,
    "stdout": "============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 29 items\n\ntests/unit/phase3/test_capability_gateway_repository.py ................ [ 55%]\n.............                                                            [100%]\n\n============================== 29 passed in 0.18s ==============================\n",
    "stderr": ""
  },
  {
    "command": "uv run pytest -o addopts='' -ra tests/unit/phase3/test_task_safety_transports.py tests/architecture/test_pr3_04_boundaries.py tests/architecture/test_pr3_02_s1_boundaries.py",
    "exit_code": 0,
    "stdout": "============================= test session starts ==============================\nplatform darwin -- Python 3.12.15, pytest-8.4.2, pluggy-1.6.0\nrootdir: /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114\nconfigfile: pyproject.toml\nplugins: anyio-4.14.2\ncollected 14 items\n\ntests/unit/phase3/test_task_safety_transports.py ..........              [ 71%]\ntests/architecture/test_pr3_04_boundaries.py ..                          [ 85%]\ntests/architecture/test_pr3_02_s1_boundaries.py ..                       [100%]\n\n=============================== warnings summary ===============================\ntests/architecture/test_pr3_02_s1_boundaries.py::test_authorized_head_and_s1_only\n  /Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/.venv/lib/python3.12/site-packages/alembic/config.py:604: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.\n    util.warn_deprecated(\n\n-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html\n======================== 14 passed, 1 warning in 1.21s =========================\n",
    "stderr": ""
  },
  {
    "command": "PYTHONPATH=. uv run python tmp/pr3-03/s2_metadata_probe.py",
    "exit_code": 1,
    "stdout": "DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948\nDISPOSABLE_CREATED: researchbase_pr212_test_2a19c0f1affd4310b69c7dfeac125775\nSERVER_VERSION_NUM 180006\nDATABASE_ROLE researchbase\nSERVER_ENCODING UTF8\nMETADATA_MATCH agent_tool_policies columns 18 foreign_keys 5 unique 2 indexes 4 checks 11\nMETADATA_MATCH agent_tool_policy_permissions columns 10 foreign_keys 1 unique 1 indexes 2 checks 7\nMETADATA_MATCH capability_invocations columns 41 foreign_keys 14 unique 8 indexes 12 checks 26\nMETADATA_MATCH capability_invocation_refs columns 14 foreign_keys 8 unique 0 indexes 15 checks 5\nMETADATA_MATCH capability_invocation_events columns 16 foreign_keys 5 unique 4 indexes 4 checks 9\nDISPOSABLE_DROPPED: researchbase_pr212_test_2a19c0f1affd4310b69c7dfeac125775\n",
    "stderr": "INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.\nINFO  [alembic.runtime.migration] Will assume transactional DDL.\nINFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.\nINFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.\nINFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.\nINFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.\nINFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.\nINFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.\nINFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.\nINFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.\nINFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.\nINFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.\nINFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.\nINFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.\nINFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.\nINFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.\nINFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.\nINFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.\nINFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.\nINFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.\nINFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.\nINFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.\nINFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.\nINFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.\nINFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.\nINFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.\nINFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.\nINFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.\nINFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.\nINFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.\nINFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.\nINFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.\nINFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.\nINFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.\nINFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.\nINFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.\nINFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.\nINFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.\nINFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.\nINFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.\nINFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.\nINFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.\nINFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.\nINFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.\nINFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.\nINFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.\nINFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.\nINFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.\nINFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.\nINFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.\nINFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.\nINFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.\nINFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.\nINFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.\nINFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.\nINFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.\nINFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.\nINFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.\nINFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.\nINFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.\nINFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.\nINFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.\nINFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.\nINFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.\nINFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.\nINFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.\nINFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.\nINFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.\nINFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.\nINFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.\nINFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.\nINFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.\nINFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.\nINFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.\nINFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.\nINFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.\nINFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).\nINFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.\nINFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.\nINFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.\nINFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.\nINFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.\nINFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.\nINFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.\nTraceback (most recent call last):\n  File \"/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane114/tmp/pr3-03/s2_metadata_probe.py\", line 94, in <module>\n    assert actual_indexes == mapped_indexes\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\nAssertionError\n"
  }
]
```

Capture `tmp/pr3-03/s2-extension-index-probe.json`:

```json
[
  {
    "command": "PYTHONPATH=. uv run python tmp/pr3-03/s2_metadata_probe.py",
    "exit_code": 0,
    "stdout": "DISPOSABLE_PG_PREFLIGHT: port=5432 system_id=7696072587520791948\nDISPOSABLE_CREATED: researchbase_pr212_test_354f15b55ad24b52a89ac73eb56d7274\nSERVER_VERSION_NUM 180006\nDATABASE_ROLE researchbase\nSERVER_ENCODING UTF8\nMETADATA_MATCH agent_tool_policies columns 18 foreign_keys 5 unique 2 indexes 4 checks 11\nMETADATA_MATCH agent_tool_policy_permissions columns 10 foreign_keys 1 unique 1 indexes 2 checks 7\nMETADATA_MATCH capability_invocations columns 41 foreign_keys 14 unique 8 indexes 12 checks 26\nMETADATA_MATCH capability_invocation_refs columns 14 foreign_keys 8 unique 0 indexes 15 checks 5\nMETADATA_MATCH capability_invocation_events columns 16 foreign_keys 5 unique 4 indexes 4 checks 9\nEXTENSION_INDEXES_MATCH research_task_command_receipts 3\nNULLABLE_EXTENSIONS_MATCH research_task_command_receipts 4\nEXTENSION_INDEXES_MATCH research_task_events 3\nNULLABLE_EXTENSIONS_MATCH research_task_events 3\nMETADATA_GATE 5/5 tables 7/7 nullable extensions\nDISPOSABLE_DROPPED: researchbase_pr212_test_354f15b55ad24b52a89ac73eb56d7274\n",
    "stderr": "INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.\nINFO  [alembic.runtime.migration] Will assume transactional DDL.\nINFO  [alembic.runtime.migration] Running upgrade  -> 0001_empty, Empty PR-00 migration proving Alembic connectivity.\nINFO  [alembic.runtime.migration] Running upgrade 0001_empty -> 0002_actor_project_workspace, Create PR-02 actor, project, and workspace tables.\nINFO  [alembic.runtime.migration] Running upgrade 0002_actor_project_workspace -> 0003_research_question_hypothesis, Create PR-04 ResearchQuestion and Hypothesis identity/version tables.\nINFO  [alembic.runtime.migration] Running upgrade 0003_research_question_hypothesis -> 0004_experiment_spec, Create PR-05 ExperimentSpec identity/version tables.\nINFO  [alembic.runtime.migration] Running upgrade 0004_experiment_spec -> 0005_dataset_snapshot, Create PR-06 Dataset and immutable DatasetSnapshot tables.\nINFO  [alembic.runtime.migration] Running upgrade 0005_dataset_snapshot -> 0006_artifact_version, Create PR-07 Artifact and ArtifactVersion tables.\nINFO  [alembic.runtime.migration] Running upgrade 0006_artifact_version -> 0007_metric_definition, Create PR-08 MetricDefinition and MetricDefinitionVersion tables.\nINFO  [alembic.runtime.migration] Running upgrade 0007_metric_definition -> 0008_run_core, Create PR-09 Run Core tables.\nINFO  [alembic.runtime.migration] Running upgrade 0008_run_core -> 0009_run_input_seal_fix, Harden PR-09 sealed Run input mutation protection.\nINFO  [alembic.runtime.migration] Running upgrade 0009_run_input_seal_fix -> 0010_measurement, Create PR-10 immutable Measurement records.\nINFO  [alembic.runtime.migration] Running upgrade 0010_measurement -> 0011_statistical_result, Create PR-11 immutable StatisticalResult records and Measurement inputs.\nINFO  [alembic.runtime.migration] Running upgrade 0011_statistical_result -> 0012_statistical_result_input_guard, Enforce at least one input for every StatisticalResult at commit time.\nINFO  [alembic.runtime.migration] Running upgrade 0012_statistical_result_input_guard -> 0013_statistical_result_legacy_input_precheck, Reject legacy zero-input StatisticalResults before accepting the guarded head.\nINFO  [alembic.runtime.migration] Running upgrade 0013_statistical_result_legacy_input_precheck -> 0014_claim_evidence, Create PR-12 Claim, ClaimVersion, and EvidenceRelation tables.\nINFO  [alembic.runtime.migration] Running upgrade 0014_claim_evidence -> 0015_governance_audit, Create PR-14 governance audit, impact, and correction tables.\nINFO  [alembic.runtime.migration] Running upgrade 0015_governance_audit -> 0016_pr17d_history_protection, Install the PR-17D PostgreSQL history-protection policy.\nINFO  [alembic.runtime.migration] Running upgrade 0016_pr17d_history_protection -> 0017_persisted_canonical_enum_normalization, Normalize Phase 1 persisted canonical enum lexemes.\nINFO  [alembic.runtime.migration] Running upgrade 0017_persisted_canonical_enum_normalization -> 0018_current_pointer_same_parent_integrity, Enforce same-parent ownership for all Phase 1 current-version pointers.\nINFO  [alembic.runtime.migration] Running upgrade 0018_current_pointer_same_parent_integrity -> 0019_phase2_bootstrap_membership, Add Phase 2 identity, membership, and owner-coverage foundations.\nINFO  [alembic.runtime.migration] Running upgrade 0019_phase2_bootstrap_membership -> 0020_literature_source_identity, Add public literature source identity, identifiers, and project access links.\nINFO  [alembic.runtime.migration] Running upgrade 0020_literature_source_identity -> 0021_source_merge_governance_bridge, Persist typed, basis-bound source merge governance proposals and decisions.\nINFO  [alembic.runtime.migration] Running upgrade 0021_source_merge_governance_bridge -> 0021a_source_merge_gov_guards, Serialize proposal basis sealing and verify stale transitions.\nINFO  [alembic.runtime.migration] Running upgrade 0021a_source_merge_gov_guards -> 0022_source_version_and_merge_lineage, Add immutable source versions and non-destructive merge lineage.\nINFO  [alembic.runtime.migration] Running upgrade 0022_source_version_and_merge_lineage -> 0023_literature_search_plan, Add versioned, project-scoped literature search plans.\nINFO  [alembic.runtime.migration] Running upgrade 0023_literature_search_plan -> 0023a_search_plan_review_guards, PR2-03 independent-review backstops; preserve 0023 and scientific history.\nINFO  [alembic.runtime.migration] Running upgrade 0023a_search_plan_review_guards -> 0024_literature_search_execution, Add bounded literature-search execution provenance.\nINFO  [alembic.runtime.migration] Running upgrade 0024_literature_search_execution -> 0025_pr2_04_reservation_guards, Enforce frozen PR2-04 reservation time and cancellation invariants.\nINFO  [alembic.runtime.migration] Running upgrade 0025_pr2_04_reservation_guards -> 0026_pr2_04_p1_contract_guards, Restore attribution and one-to-one execution provenance contracts.\nINFO  [alembic.runtime.migration] Running upgrade 0026_pr2_04_p1_contract_guards -> 0027_pr2_04_hash_scheme_guards, Enforce the frozen query/result hash scheme without rewriting provenance.\nINFO  [alembic.runtime.migration] Running upgrade 0027_pr2_04_hash_scheme_guards -> 0028_provider_cancellation, M0-CANCEL-001..004: independently confirmed provider cancellation.\nINFO  [alembic.runtime.migration] Running upgrade 0028_provider_cancellation -> 0029_metadata_observations, M2-AQ-001: dependent bibliographic observations and established resolutions.\nINFO  [alembic.runtime.migration] Running upgrade 0029_metadata_observations -> 0030_literature_evidence, Approved M3 literature evidence, review history and independent support snapshots.\nINFO  [alembic.runtime.migration] Running upgrade 0030_literature_evidence -> 0031_m3_snapshot_relation_cardinality, Seal M3 snapshot relation ordinals at commit without duplicating canonical hashing.\nINFO  [alembic.runtime.migration] Running upgrade 0031_m3_snapshot_relation_cardinality -> 0032_pr2_10_discussion, PR2-10 typed discussion sessions, immutable turns and exact references.\nINFO  [alembic.runtime.migration] Running upgrade 0032_pr2_10_discussion -> 0033_pr2_11_r2_scientific_conclusion, R2 typed ScientificConclusion versions and sealed scientific inputs.\nINFO  [alembic.runtime.migration] Running upgrade 0033_pr2_11_r2_scientific_conclusion -> 0034_pr2_10_exact_transcript_binding, Enforce the contracted exact transcript ArtifactVersion FK without a seal column.\nINFO  [alembic.runtime.migration] Running upgrade 0034_pr2_10_exact_transcript_binding -> 0035_pr2_12_publication_draft, PR2-12 project publication identity and nonformal manuscript draft.\nINFO  [alembic.runtime.migration] Running upgrade 0035_pr2_12_publication_draft -> 0036_pr2_13_citation_placement, PR2-13 citation-only placement on a draft manuscript version.\nINFO  [alembic.runtime.migration] Running upgrade 0036_pr2_13_citation_placement -> 0037_pr2_13_claim_placement, PR2-13 exact ClaimVersion or ScientificConclusionVersion placement.\nINFO  [alembic.runtime.migration] Running upgrade 0037_pr2_13_claim_placement -> 0038_pr2_13_artifact_placement, PR2-13 exact frozen ArtifactVersion placement.\nINFO  [alembic.runtime.migration] Running upgrade 0038_pr2_13_artifact_placement -> 0039_pr2_13_citation_rebinding_guard, Prevent direct SQL rebinding of a Citation placement to another manuscript.\nINFO  [alembic.runtime.migration] Running upgrade 0039_pr2_13_citation_rebinding_guard -> 0040_pr2_14_initial_internal_review, PR2-14 immutable frozen-target review and initial OPEN issues.\nINFO  [alembic.runtime.migration] Running upgrade 0040_pr2_14_initial_internal_review -> 0041_pr2_15_review_coordination, Forward exact-conclusion review/Issue coordination, preserving immutable history.\nINFO  [alembic.runtime.migration] Running upgrade 0041_pr2_15_review_coordination -> 0042_pr2_15_minimal_decision, PR2-15 immutable minimal DecisionRecord and typed conclusion/review basis.\nINFO  [alembic.runtime.migration] Running upgrade 0042_pr2_15_minimal_decision -> 0043_pr2_04_schema_contract, Owner-approved Task 12: repair existing PR2-04 schema contracts without row changes.\nINFO  [alembic.runtime.migration] Running upgrade 0043_pr2_04_schema_contract -> 0044_pr2_15_revision_action, Approved conservative completed RevisionAction slice; retained history is immutable.\nINFO  [alembic.runtime.migration] Running upgrade 0044_pr2_15_revision_action -> 0045_pr2_16_basic_approval, Owner-approved bounded Basic Approval; no consumption or scientific effects.\nINFO  [alembic.runtime.migration] Running upgrade 0045_pr2_16_basic_approval -> 0046_pr2_17_authorship, PR2-17 S1 immutable contribution and authorship foundation only.\nINFO  [alembic.runtime.migration] Running upgrade 0046_pr2_17_authorship -> 0047_pr2_18_novelty_prior_art, Immutable first-slice coverage, prior art and inconclusive assessments.\nINFO  [alembic.runtime.migration] Running upgrade 0047_pr2_18_novelty_prior_art -> 0048_b04_manuscript_freeze, B04 initial manuscript seal; retain scientific history and draft placement checks.\nINFO  [alembic.runtime.migration] Running upgrade 0048_b04_manuscript_freeze -> 0049_b05_manuscript_review, B05 manuscript review coordination and deferred immutable OPEN history guards.\nINFO  [alembic.runtime.migration] Running upgrade 0049_b05_manuscript_review -> 0050_b01_resolution_admission, Repeat the existing M2 structural resolution closure at transaction end.\nINFO  [alembic.runtime.migration] Running upgrade 0050_b01_resolution_admission -> 0051_b06_revision_action, Owner-approved B06 issue-only completed results; no result or Issue mutation.\nINFO  [alembic.runtime.migration] Running upgrade 0051_b06_revision_action -> 0052_b07_revision_decisions, B07 approved revision choices and immutable concern/re-review relations.\nINFO  [alembic.runtime.migration] Running upgrade 0052_b07_revision_decisions -> 0053_b08_issue_disposition, B08 immutable terminal Issue events and guarded status projection.\nINFO  [alembic.runtime.migration] Running upgrade 0053_b08_issue_disposition -> 0054_b11_ready_for_submission, B11 exact immutable manuscript readiness judgment; no publication effect.\nINFO  [alembic.runtime.migration] Running upgrade 0054_b11_ready_for_submission -> 0055_b09_approval_tuples, B09 finite approval tuples, lock protocol and project/purpose rejection fence.\nINFO  [alembic.runtime.migration] Running upgrade 0055_b09_approval_tuples -> 0056_b10_reconsideration, B10 owner-approved first conclusion rejection reconsideration slice.\nINFO  [alembic.runtime.migration] Running upgrade 0056_b10_reconsideration -> 0057_xid_wraparound_guards, Keep transaction-identity guards correct across PostgreSQL XID epochs.\nINFO  [alembic.runtime.migration] Running upgrade 0057_xid_wraparound_guards -> 0058_b12_prepare_submission, B12 PREPARE judgment and exact approval tuple, without lifecycle effects.\nINFO  [alembic.runtime.migration] Running upgrade 0058_b12_prepare_submission -> 0059_b13_grant_consumption, B13 one-use release receipts and explicit terminal grant maintenance.\nINFO  [alembic.runtime.migration] Running upgrade 0059_b13_grant_consumption -> 0060_b15_package_preparation, B15 immutable local PREPARED packages and direct HUMAN consent roots.\nINFO  [alembic.runtime.migration] Running upgrade 0060_b15_package_preparation -> 0061_b16_consent_withdrawal, B16 immutable alternating consent and atomic exact-manuscript grant staling.\nINFO  [alembic.runtime.migration] Running upgrade 0061_b16_consent_withdrawal -> 0062_b14a_publication_entry, B14a exact frozen manuscript entry, with retained atomic lifecycle history.\nINFO  [alembic.runtime.migration] Running upgrade 0062_b14a_publication_entry -> 0063_b14r_ready_approval, B14r exact READY approval permission; no publication or consumption effects.\nINFO  [alembic.runtime.migration] Running upgrade 0063_b14r_ready_approval -> 0064_b14_publication_ready, B14 one atomic INTERNAL_REVIEW to READY effect and concrete B13 receipt.\nINFO  [alembic.runtime.migration] Running upgrade 0064_b14_publication_ready -> 0065_b22_prior_art_correction, B22 immutable same-pair prior-art corrections; no new semantic table.\nINFO  [alembic.runtime.migration] Running upgrade 0065_b22_prior_art_correction -> 0066_b19_close_prior_art_basis, B19 sealed selected prior-art basis and versioned positive novelty material.\nINFO  [alembic.runtime.migration] Running upgrade 0066_b19_close_prior_art_basis -> 0067_b17_prepared_package_freeze, B17 exact prepared-package freeze and concrete single-use consumption.\nINFO  [alembic.runtime.migration] Running upgrade 0067_b17_prepared_package_freeze -> 0068_b21_unresolved_capture, B21 sealed historical resolution membership; preserve all v1 material.\nINFO  [alembic.runtime.migration] Running upgrade 0068_b21_unresolved_capture -> 0069_b13_stale_gate_denials, B13 hardening: recognize current READY/PREPARE fact denials as STALE.\nINFO  [alembic.runtime.migration] Running upgrade 0069_b13_stale_gate_denials -> 0070_b20_screening_basis, B20 sealed screening and negative-probe assessment basis.\nINFO  [alembic.runtime.migration] Running upgrade 0070_b20_screening_basis -> 0071_b23_novelty_review, B23 exact novelty reviews and precommitted reassessment correspondence.\nINFO  [alembic.runtime.migration] Running upgrade 0071_b23_novelty_review -> 0072_b03_discussion_hypothesis, B03 immutable explicit discussion to DRAFT hypothesis admission.\nINFO  [alembic.runtime.migration] Running upgrade 0072_b03_discussion_hypothesis -> 0073_b02_strategy_admission, B02 immutable typed strategy candidate admission relations (ADR-0020).\nINFO  [alembic.runtime.migration] Running upgrade 0073_b02_strategy_admission -> 0074_m1_manuscript_revision, M1-S1 manuscript successors, exact revision evidence and carried blockers.\nINFO  [alembic.runtime.migration] Running upgrade 0074_m1_manuscript_revision -> 0075_m1_reconsideration, M1-S2 corrected manuscript review reconsideration, with exact 0074 restoration.\nINFO  [alembic.runtime.migration] Running upgrade 0075_m1_reconsideration -> 0076_agent_runtime_bootstrap, PR3-00 empty, forward-only Agent Runtime bootstrap.\nINFO  [alembic.runtime.migration] Running upgrade 0076_agent_runtime_bootstrap -> 0077_research_task_graph, PR3-01 planning graph, exact frozen DDL and forward-only history guards.\nINFO  [alembic.runtime.migration] Running upgrade 0077_research_task_graph -> 0078_task_safety_policies, PR3-04 immutable safety policies and accounting; forward only.\nINFO  [alembic.runtime.migration] Running upgrade 0078_task_safety_policies -> 0079_agent_identity_versions, Owner-authorized ADR-0023 S1 identity and immutable versions.\nINFO  [alembic.runtime.migration] Running upgrade 0079_agent_identity_versions -> 0080_capability_gateway, Frozen PR3-03 capability gateway; forward-only migration.\n"
  }
]
```

### Recording-session evidence: expected versus actual

These are recordings, **not live gateway lock evidence**. Full SQL and callback
sequences with bound UUIDs are retained below and in their raw JSON files. UUIDs
1–6 respectively identify project, authenticated actor, command, task, target
version and target actor. Tests compare the full traces, not only SQL substrings.

| Required behavior | Test node suffix | Raw expected/actual trace |
| --- | --- | --- |
| Literal first 18-table SHARE | `test_first_statement_is_literal_eighteen_parent_share` | `s2-trace-first-statement.json` |
| Registration omits target keys/version/availability | `test_registration_omits_target_actor_version_and_availability` | `s2-trace-registration.json` |
| Exact complete key/row/table order | `test_exact_advisory_row_and_table_order` | `s2-trace-complete-order.json` |
| Callback after every blocking acquisition | `test_callback_after_every_blocking_acquisition[False/True]` | `s2-trace-callbacks-False.json`, `s2-trace-callbacks-True.json` |
| Original safety combined recipe | `test_existing_safety_combined_recipe_unchanged` | `s2-trace-safety-compatibility.json` |
| Receipt/scoped reads and ordering, detached rows | `test_receipt_and_scoped_reads_have_deterministic_order_and_detached_rows` | `s2-trace-scoped-reads.json` |
| No SQL at construction | `test_no_sql_at_uow_or_adapter_construction` | `s2-trace-construction.json` |
| No SQL when UoW enters and installs adapters | `test_entering_uow_constructs_gateway_without_sql` | `s2-trace-uow-entry.json` |

All node IDs are in `tests/unit/phase3/test_capability_gateway_repository.py`.
Eleven additional parameter cases raise at each callback position and assert
execution stops before the next SQL. Seven metadata cases match closed stored
field sets, and the nullable-extension test checks mapped attributes and deferred
receipt relationships. The extra legacy-projection case covers S2-D1.

The existing safety PostgreSQL concurrency suite passed seven cases. That evidence
belongs to existing safety compatibility; it does not establish gateway contention,
expiry/revocation races or availability-writer ordering. Gateway live concurrency,
command semantics and later S3–S8 acceptance remain unrun here by scope.

`tmp/pr3-03/s2-trace-callback-stop-1.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}]]}
```

`tmp/pr3-03/s2-trace-callback-stop-10.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM termination_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_availability WHERE agent_version_id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM termination_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_availability WHERE agent_version_id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}]]}
```

`tmp/pr3-03/s2-trace-callback-stop-11.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM termination_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_availability WHERE agent_version_id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM agent_tool_policies WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocations WHERE project_id=:project AND research_task_id=:task ORDER BY id FOR UPDATE",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM termination_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_availability WHERE agent_version_id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM agent_tool_policies WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocations WHERE project_id=:project AND research_task_id=:task ORDER BY id FOR UPDATE",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}]]}
```

`tmp/pr3-03/s2-trace-callback-stop-2.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}]]}
```

`tmp/pr3-03/s2-trace-callback-stop-3.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}]]}
```

`tmp/pr3-03/s2-trace-callback-stop-4.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}]]}
```

`tmp/pr3-03/s2-trace-callback-stop-5.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}]]}
```

`tmp/pr3-03/s2-trace-callback-stop-6.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}]]}
```

`tmp/pr3-03/s2-trace-callback-stop-7.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}]]}
```

`tmp/pr3-03/s2-trace-callback-stop-8.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}]]}
```

`tmp/pr3-03/s2-trace-callback-stop-9.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}]]}
```

`tmp/pr3-03/s2-trace-callbacks-False.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM termination_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_availability WHERE agent_version_id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM agent_tool_policies WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocations WHERE project_id=:project AND research_task_id=:task ORDER BY id FOR UPDATE",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM capability_invocation_refs WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocation_events WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM termination_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_availability WHERE agent_version_id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000005"}],["CALLBACK",{}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM agent_tool_policies WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocations WHERE project_id=:project AND research_task_id=:task ORDER BY id FOR UPDATE",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM capability_invocation_refs WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocation_events WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}]]}
```

`tmp/pr3-03/s2-trace-callbacks-True.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM termination_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policies WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocations WHERE project_id=:project AND research_task_id=:task ORDER BY id FOR UPDATE",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM capability_invocation_refs WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocation_events WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM termination_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policies WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocations WHERE project_id=:project AND research_task_id=:task ORDER BY id FOR UPDATE",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT * FROM capability_invocation_refs WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocation_events WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}]]}
```

`tmp/pr3-03/s2-trace-complete-order.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM termination_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_availability WHERE agent_version_id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM agent_tool_policies WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocations WHERE project_id=:project AND research_task_id=:task ORDER BY id FOR UPDATE",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocation_refs WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocation_events WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:actor:00000000-0000-0000-0000-000000000006"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr302:version:00000000-0000-0000-0000-000000000005"}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM termination_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_availability WHERE agent_version_id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM agent_versions WHERE id=:id",{"id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM agent_tool_policies WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocations WHERE project_id=:project AND research_task_id=:task ORDER BY id FOR UPDATE",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocation_refs WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocation_events WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}]]}
```

`tmp/pr3-03/s2-trace-construction.json`:

```json
{"expected":[],"actual":[]}
```

`tmp/pr3-03/s2-trace-first-statement.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}]]}
```

`tmp/pr3-03/s2-trace-registration.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM termination_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policies WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocations WHERE project_id=:project AND research_task_id=:task ORDER BY id FOR UPDATE",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocation_refs WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocation_events WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_reservations WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM budget_usage_records WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_dataset_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM checkpoint_policy_metric_scopes WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM execution_budgets WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM human_checkpoints WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM termination_policies WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policies WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocations WHERE project_id=:project AND research_task_id=:task ORDER BY id FOR UPDATE",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocation_refs WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM capability_invocation_events WHERE project_id=:project AND research_task_id=:task ORDER BY id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004"}]]}
```

`tmp/pr3-03/s2-trace-safety-compatibility.json`:

```json
{"expected":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}]],"actual":[["LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions, claims, hypothesis_versions, hypotheses, literature_source_project_links, literature_sources, manuscript_versions, project_memberships, project_role_assignments, projects, publications, research_question_versions, research_questions, source_versions IN SHARE MODE",{}],["CALLBACK",{}],["SELECT rb_phase2_lock_project(:id)",{"id":"00000000-0000-0000-0000-000000000001"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:command:00000000-0000-0000-0000-000000000001:00000000-0000-0000-0000-000000000002:00000000-0000-0000-0000-000000000003"}],["CALLBACK",{}],["SELECT pg_advisory_xact_lock(hashtextextended(:key,0))",{"key":"pr301:task:00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_tasks WHERE id=:id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT id FROM research_task_steps WHERE research_task_id=:id ORDER BY id FOR UPDATE",{"id":"00000000-0000-0000-0000-000000000004"}],["CALLBACK",{}],["SELECT predecessor_id,dependent_id FROM research_task_step_dependencies WHERE research_task_id=:id ORDER BY predecessor_id,dependent_id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}],["SELECT * FROM research_task_step_inputs WHERE research_task_id=:id ORDER BY id",{"id":"00000000-0000-0000-0000-000000000004"}]]}
```

`tmp/pr3-03/s2-trace-scoped-reads.json`:

```json
{"expected":[["SELECT * FROM research_task_command_receipts WHERE project_id=:project AND actor_id=:actor AND command_id=:command",{"project":"00000000-0000-0000-0000-000000000001","actor":"00000000-0000-0000-0000-000000000002","command":"00000000-0000-0000-0000-000000000003"}],["SELECT * FROM agent_tool_policies WHERE project_id=:project AND id=:id",{"project":"00000000-0000-0000-0000-000000000001","id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project AND policy_id=:id ORDER BY capability_id,capability_version,operation,adapter_id,adapter_version, parameter_schema_hash,effect",{"project":"00000000-0000-0000-0000-000000000001","id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM capability_invocations WHERE project_id=:project AND research_task_id=:task AND id=:id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004","id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM capability_invocation_refs WHERE project_id=:project AND research_task_id=:task AND invocation_id=:id ORDER BY direction, CASE WHEN research_question_version_id IS NOT NULL THEN 'RESEARCH_QUESTION_VERSION' WHEN hypothesis_version_id IS NOT NULL THEN 'HYPOTHESIS_VERSION' WHEN claim_version_id IS NOT NULL THEN 'CLAIM_VERSION' WHEN source_version_id IS NOT NULL THEN 'SOURCE_VERSION' WHEN artifact_version_id IS NOT NULL THEN 'ARTIFACT_VERSION' WHEN manuscript_version_id IS NOT NULL THEN 'MANUSCRIPT_VERSION' END, coalesce(research_question_version_id,hypothesis_version_id,claim_version_id, source_version_id,artifact_version_id,manuscript_version_id)",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004","id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM capability_invocation_events WHERE project_id=:project AND research_task_id=:task AND invocation_id=:id ORDER BY sequence",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004","id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM research_task_events WHERE research_task_id=:task ORDER BY sequence",{"task":"00000000-0000-0000-0000-000000000004"}]],"actual":[["SELECT * FROM research_task_command_receipts WHERE project_id=:project AND actor_id=:actor AND command_id=:command",{"project":"00000000-0000-0000-0000-000000000001","actor":"00000000-0000-0000-0000-000000000002","command":"00000000-0000-0000-0000-000000000003"}],["SELECT * FROM agent_tool_policies WHERE project_id=:project AND id=:id",{"project":"00000000-0000-0000-0000-000000000001","id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM agent_tool_policy_permissions WHERE project_id=:project AND policy_id=:id ORDER BY capability_id,capability_version,operation,adapter_id,adapter_version, parameter_schema_hash,effect",{"project":"00000000-0000-0000-0000-000000000001","id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM capability_invocations WHERE project_id=:project AND research_task_id=:task AND id=:id",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004","id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM capability_invocation_refs WHERE project_id=:project AND research_task_id=:task AND invocation_id=:id ORDER BY direction, CASE WHEN research_question_version_id IS NOT NULL THEN 'RESEARCH_QUESTION_VERSION' WHEN hypothesis_version_id IS NOT NULL THEN 'HYPOTHESIS_VERSION' WHEN claim_version_id IS NOT NULL THEN 'CLAIM_VERSION' WHEN source_version_id IS NOT NULL THEN 'SOURCE_VERSION' WHEN artifact_version_id IS NOT NULL THEN 'ARTIFACT_VERSION' WHEN manuscript_version_id IS NOT NULL THEN 'MANUSCRIPT_VERSION' END, coalesce(research_question_version_id,hypothesis_version_id,claim_version_id, source_version_id,artifact_version_id,manuscript_version_id)",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004","id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM capability_invocation_events WHERE project_id=:project AND research_task_id=:task AND invocation_id=:id ORDER BY sequence",{"project":"00000000-0000-0000-0000-000000000001","task":"00000000-0000-0000-0000-000000000004","id":"00000000-0000-0000-0000-000000000005"}],["SELECT * FROM research_task_events WHERE research_task_id=:task ORDER BY sequence",{"task":"00000000-0000-0000-0000-000000000004"}]]}
```

`tmp/pr3-03/s2-trace-uow-entry.json`:

```json
{"expected":[],"actual":[]}
```

### Ignored helpers and reproducibility

- `tmp/pr3-03/add_extension_indexes.py` — SHA-256 `06bbb763e46249a6b9cb73ea5ea82998825541f14d77880de950621c7fe494bf`
- `tmp/pr3-03/edit_safety.py` — SHA-256 `291061f7d5889dec73a25f4116646763e8a940ad8ca762cbd8b8f672d5e7aec7`
- `tmp/pr3-03/fix_event_projection.py` — SHA-256 `07493dbfb7d689d89ecd73303aaf6ee748bdff7f7af4f37fedf26788dfcdeacb`
- `tmp/pr3-03/fix_tests.py` — SHA-256 `619f433d34179d0c56fa8299bb20ce7c8b6bcf8ed782943db0807fdb04f3f977`
- `tmp/pr3-03/generate_metadata.py` — SHA-256 `a87a957f4dcbeb693b2e65b4ea4a0bb02a3f319f3eae153acd3b7f3fb3308a65`
- `tmp/pr3-03/integrate_metadata.py` — SHA-256 `1f89589dd720b3d8d985c2e000234a5d887bde93b2db1efd89dd7b9e9ecab23d`
- `tmp/pr3-03/readable_checks.py` — SHA-256 `a46d9568d6f10a0888f0f0ae6848f9d1b98b7de9d71d9447d05f519133e0009c`
- `tmp/pr3-03/run_checks.py` — SHA-256 `ad86dbf011374dc53438d58f2067200a5530b828377256433b559682b424904a`
- `tmp/pr3-03/s2_metadata_probe.py` — SHA-256 `1cd73bd03cd81a43cc7e2a9f60a1caa7c24c68779c8d12ccbb99b454088d7278`
- `tmp/pr3-03/stored_fields.py` — SHA-256 `5d28d179977602a8ab6ad8f24408c48a14de032f1f2f9fe042bacf1687701b31`
- `tmp/pr3-03/wrap_model_literals.py` — SHA-256 `194432a1a9395ebfa320577299d52c34e2dd0e54d6d7620c9e215d3d135b1f73`
- `tmp/pr3-03/write_s2_evidence.py` — SHA-256 `890e734609f79dd95df132cb6bd32c5b11bbfff711eede5c06c70dd9b6dc2cd9`

Disposable catalog probe source used by the exact commands above:

```python
"""Read-only catalog parity of inert mappings after a disposable 0080 upgrade."""
import os

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from tests.disposable_postgres import disposable_database

from researchbase.persistence import models

TABLES = (
    'agent_tool_policies',
    'agent_tool_policy_permissions',
    'capability_invocations',
    'capability_invocation_refs',
    'capability_invocation_events',
)
with disposable_database('researchbase_pr212_test_') as url:
    config = Config('alembic.ini')
    config.set_main_option('sqlalchemy.url', url.replace('%', '%%'))
    os.environ['DATABASE_URL'] = url
    command.upgrade(config, '0080_capability_gateway')
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            version = int(connection.execute(text('SHOW server_version_num')).scalar_one())
            assert version // 10000 == 18
            print('SERVER_VERSION_NUM', version)
            print('DATABASE_ROLE', connection.execute(text('SELECT current_user')).scalar_one())
            encoding = connection.execute(text('SHOW server_encoding')).scalar_one()
            assert encoding == 'UTF8'
            print('SERVER_ENCODING', encoding)
            catalog = inspect(connection)
            for name in TABLES:
                mapped = models.Base.metadata.tables[name]
                columns = catalog.get_columns(name)
                assert set(mapped.columns.keys()) == {c['name'] for c in columns}
                for column in columns:
                    candidate = mapped.c[column['name']]
                    assert candidate.nullable == column['nullable'], (name, column['name'])
                    assert str(candidate.type.compile(engine.dialect)) == str(
                        column['type'].compile(engine.dialect)
                    ), (name, column['name'])
                    assert column['default'] is None
                actual_fks = {
                    (tuple(fk['constrained_columns']), fk['referred_table'],
                     tuple(fk['referred_columns']), fk['options'].get('ondelete'))
                    for fk in catalog.get_foreign_keys(name)
                }
                expected_fks = {
                    (tuple(fk.column_keys), next(iter(fk.elements)).target_fullname.split('.')[0],
                     tuple(e.target_fullname.split('.')[1] for e in fk.elements), fk.ondelete)
                    for fk in mapped.foreign_key_constraints
                }
                assert actual_fks == expected_fks, name
                actual_unique = {tuple(u['column_names']) for u in catalog.get_unique_constraints(name)}
                expected_unique = {
                    tuple(c.name for c in u.columns)
                    for u in mapped.constraints if u.__class__.__name__ == 'UniqueConstraint'
                }
                assert actual_unique == expected_unique, name
                indexes = {
                    (i['name'], tuple(i['column_names']), bool(i['unique']))
                    for i in catalog.get_indexes(name)
                    if i['name'].startswith('pr303_') and not i.get('duplicates_constraint')
                }
                expected_indexes = {
                    (i.name, tuple(c.name for c in i.columns), bool(i.unique))
                    for i in mapped.indexes
                }
                assert indexes == expected_indexes, name
                checks = catalog.get_check_constraints(name)
                expected_checks = [c for c in mapped.constraints
                                   if c.__class__.__name__ == 'CheckConstraint']
                assert len(checks) == len(expected_checks), name
                print('METADATA_MATCH', name, 'columns', len(columns), 'foreign_keys', len(actual_fks),
                      'unique', len(actual_unique), 'indexes', len(indexes), 'checks', len(checks))
            for name in ('research_task_command_receipts', 'research_task_events'):
                columns = {c['name']: c for c in catalog.get_columns(name)}
                pointers = ['result_tool_policy_id', 'result_capability_invocation_id',
                            'result_capability_event_id']
                if name.endswith('receipts'):
                    pointers.append('resulting_invocation_revision')
                mapped = models.Base.metadata.tables[name]
                for pointer in pointers:
                    assert columns[pointer]['nullable'] and mapped.c[pointer].nullable
                actual_indexes = {
                    (i['name'], tuple(i['column_names']), bool(i['unique']))
                    for i in catalog.get_indexes(name)
                    if i['name'].startswith('pr303_') and not i.get('duplicates_constraint')
                }
                mapped_indexes = {
                    (i.name, tuple(c.name for c in i.columns), bool(i.unique))
                    for i in mapped.indexes if i.name.startswith('pr303_')
                }
                assert actual_indexes == mapped_indexes
                assert len(actual_indexes) == 3
                print('EXTENSION_INDEXES_MATCH', name, len(actual_indexes))
                print('NULLABLE_EXTENSIONS_MATCH', name, len(pointers))
            print('METADATA_GATE 5/5 tables 7/7 nullable extensions')
    finally:
        engine.dispose()
```

### Handoff and stop

All required S2 checks and touched PostgreSQL compatibility checks have passing
observed final results. S2-D1 is fixed and verified; S2-D2 documents the evidence
scope. No unresolved S2 P0/P1 finding is identified by these checks; independent
review remains pending. The next authorized plan step would be S3, but it was not
started. Overall PR3-03 gate success is not declared. STOP at S2.

Post-evidence verification: `git diff --check HEAD` exited 0 with empty stdout
and stderr. The working tree has exactly the nine nonignored paths listed above.
The complete tracked/new-file diff is retained at `tmp/pr3-03/s2-working-tree.diff`.
