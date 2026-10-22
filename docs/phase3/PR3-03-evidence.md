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
