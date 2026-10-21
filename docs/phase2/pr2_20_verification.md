# PR2-20 focused verification

Subject `1278a5eecbe5357d9d440a2d0da05541c67ca028`; authored dirty diff `8be7d685d474c9cb373d627bebe6e204e1a09e9a756145a9ed06b549edb1bb61`. Generated reports/evidence are excluded from their own digest.

[Recorded commands, host and counts](#focused-commands). Counts below are exact command totals. Each OWNING_ACCEPTANCE record partitions those cases by the row's owning files and retains every parametrized outcome. ENABLED describes the required acceptance check, not a live provider. The verifier never runs the whole suite. Static checks have no pytest counts. Test observations remain in tmp_path; sanitized raw JSON/logs remain local under `pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05`. Report links target tracked Markdown because the sandbox prohibits writing Git's index. No evidence directory was staged.

## Subject

```json
{
  "dirty_diff_sha256": "8be7d685d474c9cb373d627bebe6e204e1a09e9a756145a9ed06b549edb1bb61",
  "subject_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028"
}
```

Actual local host: `{"architecture": "arm64", "benchmark_disposition": "DEFERRED: owner 2026-10-20; dedicated Linux host not tested for now", "cpu": "arm", "dedicated_linux_attested": false, "kernel": "27.0.0", "logical_cpus": 12, "os": "macOS-27.0-arm64-arm-64bit", "python": "3.12.15"}`. Actual PostgreSQL: `{"settings": {"jit": "on", "max_connections": "100", "shared_buffers": "16384", "track_io_timing": "off", "work_mem": "4096"}, "version": "18.6 (Homebrew)"}`. Local timing is informational; it cannot satisfy the dedicated Linux host requirement.

## Focused commands

| Command | Exit | Passed | Failed | Errors | Skipped | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `uv sync --locked --group dev` | 0 | — | — | — | — | PASS |
| `uv run ruff check .` | 0 | — | — | — | — | PASS |
| `uv run ruff format --check .` | 0 | — | — | — | — | PASS |
| `uv run pyright` | 0 | — | — | — | — | PASS |
| `uv run alembic heads` | 0 | — | — | — | — | PASS |
| `uv run pytest tests/unit/phase2/test_pr2_20_evidence.py tests/unit/phase2/test_pr2_20_exit_report.py tests/unit/phase2/test_pr2_20_inventory.py tests/architecture/test_pr2_20_boundaries.py --tb=short --junitxml /var/folders/h5/hx7bbybn4j9422jrdzpkgln00000gp/T/b31-s4-5tqufo_e/unit-architecture.xml` | 0 | 158 | 0 | 0 | 0 | PASS |
| `uv run pytest tests/integration/phase2/test_pr2_20_security.py tests/integration/phase2/test_pr2_20_catalog_plans.py tests/integration/phase2/test_pr2_20_migrations.py tests/integration/phase2/test_pr2_20_governance_races.py tests/integration/phase2/test_pr2_20_novelty.py tests/e2e/test_pr2_20_benchmark.py --tb=short --junitxml /var/folders/h5/hx7bbybn4j9422jrdzpkgln00000gp/T/b31-s4-5tqufo_e/changed-postgres.xml` | 0 | 302 | 0 | 0 | 65 | BLOCKED |
| `uv run pytest tests/architecture/test_pr2_19_boundaries.py tests/e2e/test_phase1_concurrency_acceptance.py tests/e2e/test_phase1_cross_adapter_equivalence.py tests/e2e/test_phase1_failure_recovery.py tests/e2e/test_phase1_golden_scientific_workflow.py tests/e2e/test_phase1_historical_exactness.py tests/e2e/test_phase1_performance_shape.py tests/integration/phase2/test_approval.py tests/integration/phase2/test_b02_strategy_admission.py tests/integration/phase2/test_b02_strategy_capture.py tests/integration/phase2/test_b03_discussion_hypothesis.py tests/integration/phase2/test_b03_discussion_hypothesis_guards.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b07_revision_decisions.py tests/integration/phase2/test_b08_issue_disposition.py tests/integration/phase2/test_b17_package_freeze.py tests/integration/phase2/test_b26_finding_impact.py tests/integration/phase2/test_b27_defensive_closure_read.py tests/integration/phase2/test_m1_manuscript_reconsideration.py tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_pr2_01_source_identity.py tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_application.py tests/integration/phase2/test_pr2_04_execution_provenance.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_19_approval_atomicity.py tests/integration/phase2/test_pr2_19_atomicity.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_citation_trace.py tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_discussion.py tests/integration/phase2/test_pr2_19_governance.py tests/integration/phase2/test_pr2_19_grant_consumption_publication.py tests/integration/phase2/test_pr2_19_grant_consumption_release.py tests/integration/phase2/test_pr2_19_integrity.py tests/integration/phase2/test_pr2_19_lineage.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_19_package_freeze.py tests/integration/phase2/test_pr2_19_races.py tests/integration/phase2/test_pr2_19_rag_evidence.py tests/integration/phase2/test_pr2_19_rejection.py tests/integration/phase2/test_pr2_19_replay.py tests/integration/phase2/test_pr2_19_revision_cycle.py tests/integration/phase2/test_pr2_19_search_evidence.py tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/unit/phase2/test_pr2_08_native_strategy.py --tb=short --junitxml /var/folders/h5/hx7bbybn4j9422jrdzpkgln00000gp/T/b31-s4-5tqufo_e/owning-acceptance.xml` | 0 | 782 | 0 | 0 | 0 | PASS |
| `RB_PR220_BENCHMARK=1 uv run pytest tests/e2e/test_pr2_20_benchmark.py --tb=short --junitxml /var/folders/h5/hx7bbybn4j9422jrdzpkgln00000gp/T/b31-s4-5tqufo_e/large-benchmark.xml` | 0 | 102 | 0 | 0 | 63 | BLOCKED |

Computed validate_exit verdict: **PASS**. Owner acceptance is separate. B28 real PaperQA2 is DEFERRED under the owner 2026-10-19 disposition. AQ-S3-08 defers only positive G2 AGENT admission (docs/proposals/B30S3_Architecture_Questions_2026-10-20.md); dedicated Linux benchmark host defers only the Row 17 host requirement (docs/proposals/Owner_Decision_Linux_Benchmark_Host_2026-10-20.md). Both are owner-accepted 2026-10-20; every other owning assertion must pass. Owner-approved 2026-10-19 first slices delivered: B20 `NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE` with a typed `ScreeningBasis`, sealed probe/result children and exact historical readback ([B20 contract](../proposals/B20_Screening_Negative_Probe_Contract_DRAFT.md), migration `0070_b20_screening_basis`); B23 exact NoveltyAssessment reviews, issue-only `NOVELTY_REASSESSMENT` actions referencing precommitted direct replacements, and independent re-review links that leave Issues OPEN ([B23 contract](../proposals/B23_Novelty_Review_Revision_Contract_DRAFT.md), migration `0071_b23_novelty_review`). Implementation: `src/researchbase/domain/novelty.py`, `src/researchbase/application/internal_review.py`, `src/researchbase/application/revision_action.py`; migrations are under `migrations/versions/`. B20/B23 remaining scope exclusions (contracts §2 and §12.5): prospective preregistration/external search exhaustiveness, automatic query planning/provider execution, programmable criteria, failed/adverse-branch replacement, universal priority claims, source-merge deduplication, automatic selection across independent comparison roots and automatic impact propagation; novelty-target Decisions, NO_CHANGE, Issue disposition/blocking-concern resolution, direct PriorArtRelation/SearchCoverage review targets, and assessment creation inside review/revision commands. MANUSCRIPT_CHANGE RevisionAction as a novelty result remains a non-goal; M1 already supports MANUSCRIPT_CHANGE for manuscript concerns. No novelty-driven approval, READY/package gate or generic Agent runtime. [Independent director review and integration full check](phase2_exit_review_2026-10-20.md): lane72 head `64b5f1e`, 2026-10-20, **12,523 passed, 66 skipped, 0 failed (exit 0)**; pyright 0 errors, ruff clean, git diff --check clean, one Alembic head 0075. These are the director's recorded integration results, separate from the focused runs below. The review identifies R1–R3 for correction; owner exit acceptance and Phase 3 GO remain separate. See phase2_exit_report.md for every remaining owner decision. STOP; wait for explicit Phase 3 GO.

## Row evidence

### Exit row 1

Recorded after verification of the owning assertions and local log digests. Raw evidence paths below identify local artifacts; they are not file links.

```json
{
  "acceptance_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "commands": [
    "uv run pytest tests/architecture/test_pr2_19_boundaries.py tests/e2e/test_phase1_concurrency_acceptance.py tests/e2e/test_phase1_cross_adapter_equivalence.py tests/e2e/test_phase1_failure_recovery.py tests/e2e/test_phase1_golden_scientific_workflow.py tests/e2e/test_phase1_historical_exactness.py tests/e2e/test_phase1_performance_shape.py tests/integration/phase2/test_approval.py tests/integration/phase2/test_b02_strategy_admission.py tests/integration/phase2/test_b02_strategy_capture.py tests/integration/phase2/test_b03_discussion_hypothesis.py tests/integration/phase2/test_b03_discussion_hypothesis_guards.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b07_revision_decisions.py tests/integration/phase2/test_b08_issue_disposition.py tests/integration/phase2/test_b17_package_freeze.py tests/integration/phase2/test_b26_finding_impact.py tests/integration/phase2/test_b27_defensive_closure_read.py tests/integration/phase2/test_m1_manuscript_reconsideration.py tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_pr2_01_source_identity.py tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_application.py tests/integration/phase2/test_pr2_04_execution_provenance.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_19_approval_atomicity.py tests/integration/phase2/test_pr2_19_atomicity.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_citation_trace.py tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_discussion.py tests/integration/phase2/test_pr2_19_governance.py tests/integration/phase2/test_pr2_19_grant_consumption_publication.py tests/integration/phase2/test_pr2_19_grant_consumption_release.py tests/integration/phase2/test_pr2_19_integrity.py tests/integration/phase2/test_pr2_19_lineage.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_19_package_freeze.py tests/integration/phase2/test_pr2_19_races.py tests/integration/phase2/test_pr2_19_rag_evidence.py tests/integration/phase2/test_pr2_19_rejection.py tests/integration/phase2/test_pr2_19_replay.py tests/integration/phase2/test_pr2_19_revision_cycle.py tests/integration/phase2/test_pr2_19_search_evidence.py tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/unit/phase2/test_pr2_08_native_strategy.py --tb=short --junitxml /var/folders/h5/hx7bbybn4j9422jrdzpkgln00000gp/T/b31-s4-5tqufo_e/owning-acceptance.xml"
  ],
  "contract_refs": [
    "docs/proposals/B31_PR2-20_Full_Exit_Hardening_Contract_DRAFT.md",
    "docs/proposals/PR2-20_Hardening_Plan_DRAFT.md"
  ],
  "corrected_term": null,
  "criterion": "LiteratureSource identity resolution",
  "dirty_diff_sha256": "8be7d685d474c9cb373d627bebe6e204e1a09e9a756145a9ed06b549edb1bb61",
  "disposition_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/scope-dispositions.json"
  ],
  "errors": 0,
  "evidence_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-01.json",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-000.txt",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-junit.xml"
  ],
  "exit_codes": [
    0
  ],
  "failed": 0,
  "finding_refs": [],
  "owning_prs": [
    "PR2-01"
  ],
  "passed": 11,
  "reason": null,
  "schema_version": 1,
  "skipped": 0,
  "status": "PASS",
  "subject_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "test_nodes": [
    "tests/integration/phase2/test_pr2_01_source_identity.py::test_register_verify_reject_rebind_and_replay_are_durable",
    "tests/integration/phase2/test_pr2_01_source_identity.py::test_register_without_identifier_replay_and_changed_input_conflict",
    "tests/integration/phase2/test_pr2_01_source_identity.py::test_concurrent_same_key_add_verify_and_reject_replay_one_result",
    "tests/integration/phase2/test_pr2_01_source_identity.py::test_unlinked_source_is_not_disclosed_and_shared_source_cannot_be_rejected",
    "tests/integration/phase2/test_pr2_01_source_identity.py::test_concurrent_same_key_registration_replays_one_committed_result",
    "tests/integration/phase2/test_pr2_01_source_identity.py::test_receipt_failure_rolls_back_each_command_and_allows_same_key_retry",
    "tests/integration/phase2/test_pr2_01_source_identity.py::test_distinct_key_identifier_collision_has_typed_conflict",
    "tests/integration/phase2/test_pr2_01_source_identity.py::test_http_cli_share_authenticated_application_and_idempotent_result",
    "tests/integration/phase2/test_pr2_01_source_identity.py::test_credential_expiry_during_project_lock_wait_denies_registration",
    "tests/integration/phase2/test_pr2_01_source_identity.py::test_concurrent_rejection_and_corrected_rebinding_preserve_one_live_identity"
  ]
}
```

### Exit row 2

Recorded after verification of the owning assertions and local log digests. Raw evidence paths below identify local artifacts; they are not file links.

```json
{
  "acceptance_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "commands": [
    "uv run pytest tests/architecture/test_pr2_19_boundaries.py tests/e2e/test_phase1_concurrency_acceptance.py tests/e2e/test_phase1_cross_adapter_equivalence.py tests/e2e/test_phase1_failure_recovery.py tests/e2e/test_phase1_golden_scientific_workflow.py tests/e2e/test_phase1_historical_exactness.py tests/e2e/test_phase1_performance_shape.py tests/integration/phase2/test_approval.py tests/integration/phase2/test_b02_strategy_admission.py tests/integration/phase2/test_b02_strategy_capture.py tests/integration/phase2/test_b03_discussion_hypothesis.py tests/integration/phase2/test_b03_discussion_hypothesis_guards.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b07_revision_decisions.py tests/integration/phase2/test_b08_issue_disposition.py tests/integration/phase2/test_b17_package_freeze.py tests/integration/phase2/test_b26_finding_impact.py tests/integration/phase2/test_b27_defensive_closure_read.py tests/integration/phase2/test_m1_manuscript_reconsideration.py tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_pr2_01_source_identity.py tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_application.py tests/integration/phase2/test_pr2_04_execution_provenance.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_19_approval_atomicity.py tests/integration/phase2/test_pr2_19_atomicity.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_citation_trace.py tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_discussion.py tests/integration/phase2/test_pr2_19_governance.py tests/integration/phase2/test_pr2_19_grant_consumption_publication.py tests/integration/phase2/test_pr2_19_grant_consumption_release.py tests/integration/phase2/test_pr2_19_integrity.py tests/integration/phase2/test_pr2_19_lineage.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_19_package_freeze.py tests/integration/phase2/test_pr2_19_races.py tests/integration/phase2/test_pr2_19_rag_evidence.py tests/integration/phase2/test_pr2_19_rejection.py tests/integration/phase2/test_pr2_19_replay.py tests/integration/phase2/test_pr2_19_revision_cycle.py tests/integration/phase2/test_pr2_19_search_evidence.py tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/unit/phase2/test_pr2_08_native_strategy.py --tb=short --junitxml /var/folders/h5/hx7bbybn4j9422jrdzpkgln00000gp/T/b31-s4-5tqufo_e/owning-acceptance.xml"
  ],
  "contract_refs": [
    "docs/proposals/B31_PR2-20_Full_Exit_Hardening_Contract_DRAFT.md",
    "docs/proposals/PR2-20_Hardening_Plan_DRAFT.md"
  ],
  "corrected_term": null,
  "criterion": "SourceVersion lineage/freeze",
  "dirty_diff_sha256": "8be7d685d474c9cb373d627bebe6e204e1a09e9a756145a9ed06b549edb1bb61",
  "disposition_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/scope-dispositions.json"
  ],
  "errors": 0,
  "evidence_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-02.json",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-000.txt",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-junit.xml"
  ],
  "exit_codes": [
    0
  ],
  "failed": 0,
  "finding_refs": [],
  "owning_prs": [
    "PR2-02"
  ],
  "passed": 39,
  "reason": null,
  "schema_version": 1,
  "skipped": 0,
  "status": "PASS",
  "subject_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "test_nodes": [
    "tests/integration/phase2/test_pr2_02_source_version_migration.py::test_source_version_authority_rechecks_after_confirmed_lock_wait",
    "tests/integration/phase2/test_pr2_02_source_version_migration.py::test_pr2_02_fresh_migration_adds_version_merge_and_command_receipt_schema",
    "tests/integration/phase2/test_pr2_02_source_version_migration.py::test_pr2_02_empty_downgrade_restores_0021a_schema",
    "tests/integration/phase2/test_pr2_02_source_version_migration.py::test_pr2_02_populated_downgrade_refuses_without_losing_version_history",
    "tests/integration/phase2/test_pr2_02_source_version_migration.py::test_source_version_lifecycle_and_scoped_command_replay",
    "tests/integration/phase2/test_pr2_02_source_version_migration.py::test_approved_source_merge_is_atomic_and_exactly_once",
    "tests/integration/phase2/test_pr2_02_source_version_migration.py::test_revoked_merge_approval_returns_canonical_denial_without_effects",
    "tests/integration/phase2/test_pr2_02_source_version_migration.py::test_merge_and_approval_revocation_serialize",
    "tests/integration/phase2/test_pr2_19_lineage.py::test_lineage_rejection_has_zero_delta",
    "tests/integration/phase2/test_pr2_19_lineage.py::test_lineage_preserves_exact_bytes_and_blocks_new_support",
    "tests/integration/phase2/test_pr2_19_lineage.py::test_concurrent_corrections_cannot_fork_current_lineage",
    "tests/integration/phase2/test_pr2_19_lineage.py::test_current_manuscript_projection_audit_retains_frozen_material",
    "tests/integration/phase2/test_pr2_19_lineage.py::test_f1_current_downstream_facts_preserve_saved_consumptions",
    "tests/integration/phase2/test_pr2_19_lineage.py::test_f1_unrelated_source_control_does_not_block_ready_or_package"
  ]
}
```

### Exit row 3

Recorded after verification of the owning assertions and local log digests. Raw evidence paths below identify local artifacts; they are not file links.

```json
{
  "acceptance_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "commands": [
    "uv run pytest tests/architecture/test_pr2_19_boundaries.py tests/e2e/test_phase1_concurrency_acceptance.py tests/e2e/test_phase1_cross_adapter_equivalence.py tests/e2e/test_phase1_failure_recovery.py tests/e2e/test_phase1_golden_scientific_workflow.py tests/e2e/test_phase1_historical_exactness.py tests/e2e/test_phase1_performance_shape.py tests/integration/phase2/test_approval.py tests/integration/phase2/test_b02_strategy_admission.py tests/integration/phase2/test_b02_strategy_capture.py tests/integration/phase2/test_b03_discussion_hypothesis.py tests/integration/phase2/test_b03_discussion_hypothesis_guards.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b07_revision_decisions.py tests/integration/phase2/test_b08_issue_disposition.py tests/integration/phase2/test_b17_package_freeze.py tests/integration/phase2/test_b26_finding_impact.py tests/integration/phase2/test_b27_defensive_closure_read.py tests/integration/phase2/test_m1_manuscript_reconsideration.py tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_pr2_01_source_identity.py tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_application.py tests/integration/phase2/test_pr2_04_execution_provenance.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_19_approval_atomicity.py tests/integration/phase2/test_pr2_19_atomicity.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_citation_trace.py tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_discussion.py tests/integration/phase2/test_pr2_19_governance.py tests/integration/phase2/test_pr2_19_grant_consumption_publication.py tests/integration/phase2/test_pr2_19_grant_consumption_release.py tests/integration/phase2/test_pr2_19_integrity.py tests/integration/phase2/test_pr2_19_lineage.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_19_package_freeze.py tests/integration/phase2/test_pr2_19_races.py tests/integration/phase2/test_pr2_19_rag_evidence.py tests/integration/phase2/test_pr2_19_rejection.py tests/integration/phase2/test_pr2_19_replay.py tests/integration/phase2/test_pr2_19_revision_cycle.py tests/integration/phase2/test_pr2_19_search_evidence.py tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/unit/phase2/test_pr2_08_native_strategy.py --tb=short --junitxml /var/folders/h5/hx7bbybn4j9422jrdzpkgln00000gp/T/b31-s4-5tqufo_e/owning-acceptance.xml"
  ],
  "contract_refs": [
    "docs/proposals/B31_PR2-20_Full_Exit_Hardening_Contract_DRAFT.md",
    "docs/proposals/PR2-20_Hardening_Plan_DRAFT.md"
  ],
  "corrected_term": "LiteratureSearchExecution",
  "criterion": "LiteratureSearchPlan/Run provenance",
  "dirty_diff_sha256": "8be7d685d474c9cb373d627bebe6e204e1a09e9a756145a9ed06b549edb1bb61",
  "disposition_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/scope-dispositions.json"
  ],
  "errors": 0,
  "evidence_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-03.json",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-000.txt",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-junit.xml"
  ],
  "exit_codes": [
    0
  ],
  "failed": 0,
  "finding_refs": [],
  "owning_prs": [
    "PR2-03",
    "PR2-04"
  ],
  "passed": 10,
  "reason": null,
  "schema_version": 1,
  "skipped": 0,
  "status": "PASS",
  "subject_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "test_nodes": [
    "tests/integration/phase2/test_pr2_03_literature_search_plan_application.py::test_plan_draft_cardinality_language_freeze_and_immutability",
    "tests/integration/phase2/test_pr2_04_execution_provenance.py::test_pr2_04_draft_plan_version_cannot_be_bound_to_execution",
    "tests/integration/phase2/test_pr2_04_execution_provenance.py::test_pr2_04_execution_persists_reconstructable_plan_attempt_query_result_chain",
    "tests/integration/phase2/test_pr2_04_execution_provenance.py::test_pr2_04_provider_retry_persists_distinct_attempt_and_query_observations",
    "tests/integration/phase2/test_pr2_04_execution_provenance.py::test_pr2_04_interrupted_c1_recovers_cancelled_without_provider_dispatch",
    "tests/integration/phase2/test_pr2_04_execution_provenance.py::test_pr2_04_authority_loss_during_provider_call_denies_tx_b",
    "tests/integration/phase2/test_pr2_04_execution_provenance.py::test_pr2_04_create_receipt_replay_and_same_key_payload_conflict_are_durable",
    "tests/integration/phase2/test_pr2_04_execution_provenance.py::test_pr2_04_unknown_is_terminal_and_replay_or_recovery_never_redispatches",
    "tests/integration/phase2/test_pr2_04_execution_provenance.py::test_pr2_04_known_provider_failure_is_terminal_without_retry_or_partial_results"
  ]
}
```

### Exit row 4

Recorded after verification of the owning assertions and local log digests. Raw evidence paths below identify local artifacts; they are not file links.

```json
{
  "acceptance_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "commands": [
    "uv run pytest tests/architecture/test_pr2_19_boundaries.py tests/e2e/test_phase1_concurrency_acceptance.py tests/e2e/test_phase1_cross_adapter_equivalence.py tests/e2e/test_phase1_failure_recovery.py tests/e2e/test_phase1_golden_scientific_workflow.py tests/e2e/test_phase1_historical_exactness.py tests/e2e/test_phase1_performance_shape.py tests/integration/phase2/test_approval.py tests/integration/phase2/test_b02_strategy_admission.py tests/integration/phase2/test_b02_strategy_capture.py tests/integration/phase2/test_b03_discussion_hypothesis.py tests/integration/phase2/test_b03_discussion_hypothesis_guards.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b07_revision_decisions.py tests/integration/phase2/test_b08_issue_disposition.py tests/integration/phase2/test_b17_package_freeze.py tests/integration/phase2/test_b26_finding_impact.py tests/integration/phase2/test_b27_defensive_closure_read.py tests/integration/phase2/test_m1_manuscript_reconsideration.py tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_pr2_01_source_identity.py tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_application.py tests/integration/phase2/test_pr2_04_execution_provenance.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_19_approval_atomicity.py tests/integration/phase2/test_pr2_19_atomicity.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_citation_trace.py tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_discussion.py tests/integration/phase2/test_pr2_19_governance.py tests/integration/phase2/test_pr2_19_grant_consumption_publication.py tests/integration/phase2/test_pr2_19_grant_consumption_release.py tests/integration/phase2/test_pr2_19_integrity.py tests/integration/phase2/test_pr2_19_lineage.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_19_package_freeze.py tests/integration/phase2/test_pr2_19_races.py tests/integration/phase2/test_pr2_19_rag_evidence.py tests/integration/phase2/test_pr2_19_rejection.py tests/integration/phase2/test_pr2_19_replay.py tests/integration/phase2/test_pr2_19_revision_cycle.py tests/integration/phase2/test_pr2_19_search_evidence.py tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/unit/phase2/test_pr2_08_native_strategy.py --tb=short --junitxml /var/folders/h5/hx7bbybn4j9422jrdzpkgln00000gp/T/b31-s4-5tqufo_e/owning-acceptance.xml"
  ],
  "contract_refs": [
    "docs/proposals/B31_PR2-20_Full_Exit_Hardening_Contract_DRAFT.md",
    "docs/proposals/PR2-20_Hardening_Plan_DRAFT.md"
  ],
  "corrected_term": null,
  "criterion": "LiteratureEvidence source+locator trace",
  "dirty_diff_sha256": "8be7d685d474c9cb373d627bebe6e204e1a09e9a756145a9ed06b549edb1bb61",
  "disposition_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/scope-dispositions.json"
  ],
  "errors": 0,
  "evidence_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-04.json",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-000.txt",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-junit.xml"
  ],
  "exit_codes": [
    0
  ],
  "failed": 0,
  "finding_refs": [],
  "owning_prs": [
    "PR2-05"
  ],
  "passed": 16,
  "reason": null,
  "schema_version": 1,
  "skipped": 0,
  "status": "PASS",
  "subject_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "test_nodes": [
    "tests/integration/phase2/test_m3_evidence.py::test_pg_manual_evidence_replay_and_restart",
    "tests/integration/phase2/test_m3_evidence.py::test_pg_missing_content_version_mismatch_and_wrong_location",
    "tests/integration/phase2/test_m3_evidence.py::test_pg_independence_missing_approval_related_and_conflicts",
    "tests/integration/phase2/test_m3_evidence.py::test_pg_authority_replay_integrity_and_derived_staleness",
    "tests/integration/phase2/test_m3_evidence.py::test_pg_review_rejection_is_terminal_and_history_append_only",
    "tests/integration/phase2/test_m3_evidence.py::test_pg_document_import_replay_and_missing_fulltext",
    "tests/integration/phase2/test_m3_evidence.py::test_pg_snapshot_sequence_empty_correction_and_sealed_rows",
    "tests/integration/phase2/test_m3_evidence.py::test_pg_credential_expiry_and_non_reviewer_cannot_verify",
    "tests/integration/phase2/test_m3_evidence.py::test_pg_claim_link_uses_unchanged_phase1_closure",
    "tests/integration/phase2/test_m3_evidence.py::test_pg_upstream_retraction_stales_historical_support",
    "tests/integration/phase2/test_m3_evidence.py::test_pg_m3_migration_from_phase1_and_empty_roundtrip",
    "tests/integration/phase2/test_m3_evidence.py::test_pg_m3_alembic_env_preserves_percent_escaped_url",
    "tests/integration/phase2/test_m3_evidence.py::test_pg_authority_expiring_during_document_storage_rolls_back",
    "tests/integration/phase2/test_pr2_19_search_evidence.py::test_persisted_search_result_is_not_verified_evidence",
    "tests/integration/phase2/test_pr2_19_search_evidence.py::test_persisted_resolution_exact_source_verified_evidence_conclusion_path",
    "tests/integration/phase2/test_pr2_19_rag_evidence.py::test_retrieval_then_owning_admission_independent_human_review_restart"
  ]
}
```

### Exit row 5

Recorded after verification of the owning assertions and local log digests. Raw evidence paths below identify local artifacts; they are not file links.

```json
{
  "acceptance_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "commands": [
    "uv run pytest tests/architecture/test_pr2_19_boundaries.py tests/e2e/test_phase1_concurrency_acceptance.py tests/e2e/test_phase1_cross_adapter_equivalence.py tests/e2e/test_phase1_failure_recovery.py tests/e2e/test_phase1_golden_scientific_workflow.py tests/e2e/test_phase1_historical_exactness.py tests/e2e/test_phase1_performance_shape.py tests/integration/phase2/test_approval.py tests/integration/phase2/test_b02_strategy_admission.py tests/integration/phase2/test_b02_strategy_capture.py tests/integration/phase2/test_b03_discussion_hypothesis.py tests/integration/phase2/test_b03_discussion_hypothesis_guards.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b07_revision_decisions.py tests/integration/phase2/test_b08_issue_disposition.py tests/integration/phase2/test_b17_package_freeze.py tests/integration/phase2/test_b26_finding_impact.py tests/integration/phase2/test_b27_defensive_closure_read.py tests/integration/phase2/test_m1_manuscript_reconsideration.py tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_pr2_01_source_identity.py tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_application.py tests/integration/phase2/test_pr2_04_execution_provenance.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_19_approval_atomicity.py tests/integration/phase2/test_pr2_19_atomicity.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_citation_trace.py tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_discussion.py tests/integration/phase2/test_pr2_19_governance.py tests/integration/phase2/test_pr2_19_grant_consumption_publication.py tests/integration/phase2/test_pr2_19_grant_consumption_release.py tests/integration/phase2/test_pr2_19_integrity.py tests/integration/phase2/test_pr2_19_lineage.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_19_package_freeze.py tests/integration/phase2/test_pr2_19_races.py tests/integration/phase2/test_pr2_19_rag_evidence.py tests/integration/phase2/test_pr2_19_rejection.py tests/integration/phase2/test_pr2_19_replay.py tests/integration/phase2/test_pr2_19_revision_cycle.py tests/integration/phase2/test_pr2_19_search_evidence.py tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/unit/phase2/test_pr2_08_native_strategy.py --tb=short --junitxml /var/folders/h5/hx7bbybn4j9422jrdzpkgln00000gp/T/b31-s4-5tqufo_e/owning-acceptance.xml"
  ],
  "contract_refs": [
    "docs/proposals/B31_PR2-20_Full_Exit_Hardening_Contract_DRAFT.md",
    "docs/proposals/PR2-20_Hardening_Plan_DRAFT.md"
  ],
  "corrected_term": null,
  "criterion": "STORM-like Native ResearchStrategy",
  "dirty_diff_sha256": "8be7d685d474c9cb373d627bebe6e204e1a09e9a756145a9ed06b549edb1bb61",
  "disposition_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/scope-dispositions.json",
    "docs/proposals/B30S3_Architecture_Questions_2026-10-20.md"
  ],
  "errors": 0,
  "evidence_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-05.json",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-000.txt",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-junit.xml"
  ],
  "exit_codes": [
    0
  ],
  "failed": 0,
  "finding_refs": [],
  "owning_prs": [
    "PR2-08"
  ],
  "passed": 63,
  "reason": "AQ-S3-08: positive G2 AGENT admission pending; owner-accepted known gap 2026-10-20; all other owning assertions verified",
  "schema_version": 1,
  "skipped": 0,
  "status": "DEFERRED",
  "subject_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "test_nodes": [
    "tests/integration/phase2/test_b02_strategy_capture.py::test_capture_exact_bytes_after_restart_no_scientific_delta",
    "tests/integration/phase2/test_b02_strategy_capture.py::test_external_execution_is_outside_database_transaction",
    "tests/integration/phase2/test_b02_strategy_capture.py::test_handled_retrieval_failure_is_saved",
    "tests/integration/phase2/test_b02_strategy_capture.py::test_capture_failure_no_canonical_delta",
    "tests/integration/phase2/test_b02_strategy_capture.py::test_substituted_capture_bytes_fail_closed",
    "tests/integration/phase2/test_b02_strategy_admission.py::test_saved_question_and_researcher_adaptation_drafts",
    "tests/integration/phase2/test_b02_strategy_admission.py::test_bad_admission_has_no_scientific_delta",
    "tests/integration/phase2/test_b02_strategy_admission.py::test_reader_roles_and_writer_policy",
    "tests/integration/phase2/test_b02_strategy_admission.py::test_unbound_principal_denied_with_existing_error",
    "tests/integration/phase2/test_b02_strategy_admission.py::test_missing_principal_and_cross_project_are_fail_closed",
    "tests/integration/phase2/test_b02_strategy_admission.py::test_same_reader_cannot_resolve_cross_project_ids_or_parent",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_native_strategy_is_candidate_only",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_candidate_exact_corpus_and_zero_scientific_delta",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_saved_native_brief_question_and_researcher_adaptation_after_restart",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_exact_replay_and_changed_payload_zero_delta",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_invalid_selector_or_unanswered_section_zero_delta",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_cas_corruption_denies_admission_and_exact_read",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_fault_after_admission_insert_rolls_back_root_and_version",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_creation_guard_maps_failure_and_rolls_back",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_admission_history_is_immutable",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_credentials_revoked_during_observed_share_wait",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_historical_replay_after_application_closes_writer_roles",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_duplicate_loser_with_backend_wait",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_inaccessible_source_precedes_frozen_reference_gate",
    "tests/unit/phase2/test_pr2_08_native_strategy.py::test_plan_has_deterministic_multiple_perspectives_and_queries",
    "tests/unit/phase2/test_pr2_08_native_strategy.py::test_execute_preserves_exact_source_spans_and_candidate_provenance",
    "tests/unit/phase2/test_pr2_08_native_strategy.py::test_missing_evidence_makes_open_question_without_fabricated_answer",
    "tests/unit/phase2/test_pr2_08_native_strategy.py::test_provider_failure_is_isolated_and_raw_error_is_not_returned",
    "tests/unit/phase2/test_pr2_08_native_strategy.py::test_foreign_source_candidate_fails_closed",
    "tests/unit/phase2/test_pr2_08_native_strategy.py::test_cancellation_between_perspectives_aborts_without_partial_result",
    "tests/unit/phase2/test_pr2_08_native_strategy.py::test_provider_cancellation_propagates_instead_of_becoming_availability_warning",
    "tests/unit/phase2/test_pr2_08_native_strategy.py::test_tampered_plan_cannot_dispatch_a_different_query",
    "tests/unit/phase2/test_pr2_08_native_strategy.py::test_tampered_plan_cannot_dispatch_a_different_source_set_or_topic",
    "tests/unit/phase2/test_pr2_08_native_strategy.py::test_provider_qualifications_cannot_be_silently_dropped"
  ]
}
```

### Exit row 6

Recorded after verification of the owning assertions and local log digests. Raw evidence paths below identify local artifacts; they are not file links.

```json
{
  "acceptance_revision": null,
  "commands": [],
  "contract_refs": [
    "docs/proposals/B31_PR2-20_Full_Exit_Hardening_Contract_DRAFT.md",
    "docs/proposals/PR2-20_Hardening_Plan_DRAFT.md"
  ],
  "corrected_term": null,
  "criterion": "PaperQA2 Adapter",
  "dirty_diff_sha256": "8be7d685d474c9cb373d627bebe6e204e1a09e9a756145a9ed06b549edb1bb61",
  "disposition_refs": [
    "docs/proposals/B28_PaperQA2_Intake_Assessment_DRAFT.md"
  ],
  "errors": 0,
  "evidence_refs": [],
  "exit_codes": [],
  "failed": 0,
  "finding_refs": [],
  "owning_prs": [
    "PR2-07"
  ],
  "passed": 0,
  "reason": "Owner-approved B28 deferral: docs/proposals/B28_PaperQA2_Intake_Assessment_DRAFT.md",
  "schema_version": 1,
  "skipped": 0,
  "status": "DEFERRED",
  "subject_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "test_nodes": []
}
```

### Exit row 7

Recorded after verification of the owning assertions and local log digests. Raw evidence paths below identify local artifacts; they are not file links.

```json
{
  "acceptance_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "commands": [
    "uv run pytest tests/architecture/test_pr2_19_boundaries.py tests/e2e/test_phase1_concurrency_acceptance.py tests/e2e/test_phase1_cross_adapter_equivalence.py tests/e2e/test_phase1_failure_recovery.py tests/e2e/test_phase1_golden_scientific_workflow.py tests/e2e/test_phase1_historical_exactness.py tests/e2e/test_phase1_performance_shape.py tests/integration/phase2/test_approval.py tests/integration/phase2/test_b02_strategy_admission.py tests/integration/phase2/test_b02_strategy_capture.py tests/integration/phase2/test_b03_discussion_hypothesis.py tests/integration/phase2/test_b03_discussion_hypothesis_guards.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b07_revision_decisions.py tests/integration/phase2/test_b08_issue_disposition.py tests/integration/phase2/test_b17_package_freeze.py tests/integration/phase2/test_b26_finding_impact.py tests/integration/phase2/test_b27_defensive_closure_read.py tests/integration/phase2/test_m1_manuscript_reconsideration.py tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_pr2_01_source_identity.py tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_application.py tests/integration/phase2/test_pr2_04_execution_provenance.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_19_approval_atomicity.py tests/integration/phase2/test_pr2_19_atomicity.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_citation_trace.py tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_discussion.py tests/integration/phase2/test_pr2_19_governance.py tests/integration/phase2/test_pr2_19_grant_consumption_publication.py tests/integration/phase2/test_pr2_19_grant_consumption_release.py tests/integration/phase2/test_pr2_19_integrity.py tests/integration/phase2/test_pr2_19_lineage.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_19_package_freeze.py tests/integration/phase2/test_pr2_19_races.py tests/integration/phase2/test_pr2_19_rag_evidence.py tests/integration/phase2/test_pr2_19_rejection.py tests/integration/phase2/test_pr2_19_replay.py tests/integration/phase2/test_pr2_19_revision_cycle.py tests/integration/phase2/test_pr2_19_search_evidence.py tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/unit/phase2/test_pr2_08_native_strategy.py --tb=short --junitxml /var/folders/h5/hx7bbybn4j9422jrdzpkgln00000gp/T/b31-s4-5tqufo_e/owning-acceptance.xml"
  ],
  "contract_refs": [
    "docs/proposals/B31_PR2-20_Full_Exit_Hardening_Contract_DRAFT.md",
    "docs/proposals/PR2-20_Hardening_Plan_DRAFT.md"
  ],
  "corrected_term": null,
  "criterion": "Academic Discussion explicit promotion",
  "dirty_diff_sha256": "8be7d685d474c9cb373d627bebe6e204e1a09e9a756145a9ed06b549edb1bb61",
  "disposition_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/scope-dispositions.json"
  ],
  "errors": 0,
  "evidence_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-07.json",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-000.txt",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-junit.xml"
  ],
  "exit_codes": [
    0
  ],
  "failed": 0,
  "finding_refs": [],
  "owning_prs": [
    "PR2-10"
  ],
  "passed": 79,
  "reason": null,
  "schema_version": 1,
  "skipped": 0,
  "status": "PASS",
  "subject_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "test_nodes": [
    "tests/integration/phase2/test_b03_discussion_hypothesis.py::test_draft_restart_initial_material_and_lock_free_read",
    "tests/integration/phase2/test_b03_discussion_hypothesis.py::test_request_conflict_duplicate_and_missing_store",
    "tests/integration/phase2/test_b03_discussion_hypothesis.py::test_concurrent_requests",
    "tests/integration/phase2/test_b03_discussion_hypothesis.py::test_failure_at_every_insert_or_constraint_rolls_back",
    "tests/integration/phase2/test_b03_discussion_hypothesis.py::test_invalid_context_zero_delta",
    "tests/integration/phase2/test_b03_discussion_hypothesis.py::test_expired_credentials_and_unverified_denied",
    "tests/integration/phase2/test_b03_discussion_hypothesis.py::test_prior_head_upgrade_keeps_receipts_and_empty_downgrade",
    "tests/integration/phase2/test_b03_discussion_hypothesis.py::test_nonwriter_denied_but_human_replay_uses_read_entitlement",
    "tests/integration/phase2/test_b03_discussion_hypothesis.py::test_open_or_unbound_session_rejected",
    "tests/integration/phase2/test_b03_discussion_hypothesis.py::test_expiry_after_candidate_wait_and_receipt_failure",
    "tests/integration/phase2/test_b03_discussion_hypothesis.py::test_failure_after_receipt_insert",
    "tests/integration/phase2/test_b03_discussion_hypothesis.py::test_corrupt_retained_closure_fails_read_and_replay",
    "tests/integration/phase2/test_b03_discussion_hypothesis.py::test_empty_upgrade_to_head",
    "tests/integration/phase2/test_b03_discussion_hypothesis.py::test_cross_actor_same_request_is_duplicate_not_replay",
    "tests/integration/phase2/test_b03_discussion_hypothesis.py::test_frozen_output_and_archived_project_remain_readable",
    "tests/integration/phase2/test_b03_discussion_hypothesis_guards.py::test_deferred_creation_failure_rolls_back_every_row",
    "tests/integration/phase2/test_b03_discussion_hypothesis_guards.py::test_admission_and_receipt_are_immutable",
    "tests/integration/phase2/test_b03_discussion_hypothesis_guards.py::test_populated_downgrade_refused",
    "tests/integration/phase2/test_b03_discussion_hypothesis_guards.py::test_existing_output_graft_rejected",
    "tests/integration/phase2/test_b03_discussion_hypothesis_guards.py::test_exact_foreign_keys_reject_mismatched_context",
    "tests/integration/phase2/test_pr2_19_discussion.py::test_transcript_binding_restart_and_forbidden_promotion",
    "tests/integration/phase2/test_pr2_19_discussion.py::test_g4_explicit_manual_admission_suffix",
    "tests/integration/phase2/test_pr2_19_discussion.py::test_g4_missing_root_zero_delta",
    "tests/integration/phase2/test_pr2_19_discussion.py::test_g4_open_or_unbound_zero_delta",
    "tests/integration/phase2/test_pr2_19_discussion.py::test_g4_corrupt_or_missing_cas_denies_read_replay_and_admission",
    "tests/integration/phase2/test_pr2_19_discussion.py::test_g4_mid_uow_fault_rolls_back_all_command_rows",
    "tests/integration/phase2/test_pr2_19_discussion.py::test_g4_creation_guard_maps_missing_admission_and_rolls_back",
    "tests/integration/phase2/test_pr2_19_discussion.py::test_g4_saved_admission_is_immutable",
    "tests/integration/phase2/test_pr2_19_discussion.py::test_g4_same_request_two_connection_barrier_returns_one_admission",
    "tests/integration/phase2/test_pr2_19_discussion.py::test_g4_credentials_revoked_during_observed_share_wait",
    "tests/integration/phase2/test_pr2_19_discussion.py::test_g4_saved_replay_after_application_closes_writer_role",
    "tests/integration/phase2/test_pr2_19_discussion.py::test_g4_transcript_mismatch_precedes_artifact_lookup"
  ]
}
```

### Exit row 8

Recorded after verification of the owning assertions and local log digests. Raw evidence paths below identify local artifacts; they are not file links.

```json
{
  "acceptance_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "commands": [
    "uv run pytest tests/architecture/test_pr2_19_boundaries.py tests/e2e/test_phase1_concurrency_acceptance.py tests/e2e/test_phase1_cross_adapter_equivalence.py tests/e2e/test_phase1_failure_recovery.py tests/e2e/test_phase1_golden_scientific_workflow.py tests/e2e/test_phase1_historical_exactness.py tests/e2e/test_phase1_performance_shape.py tests/integration/phase2/test_approval.py tests/integration/phase2/test_b02_strategy_admission.py tests/integration/phase2/test_b02_strategy_capture.py tests/integration/phase2/test_b03_discussion_hypothesis.py tests/integration/phase2/test_b03_discussion_hypothesis_guards.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b07_revision_decisions.py tests/integration/phase2/test_b08_issue_disposition.py tests/integration/phase2/test_b17_package_freeze.py tests/integration/phase2/test_b26_finding_impact.py tests/integration/phase2/test_b27_defensive_closure_read.py tests/integration/phase2/test_m1_manuscript_reconsideration.py tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_pr2_01_source_identity.py tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_application.py tests/integration/phase2/test_pr2_04_execution_provenance.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_19_approval_atomicity.py tests/integration/phase2/test_pr2_19_atomicity.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_citation_trace.py tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_discussion.py tests/integration/phase2/test_pr2_19_governance.py tests/integration/phase2/test_pr2_19_grant_consumption_publication.py tests/integration/phase2/test_pr2_19_grant_consumption_release.py tests/integration/phase2/test_pr2_19_integrity.py tests/integration/phase2/test_pr2_19_lineage.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_19_package_freeze.py tests/integration/phase2/test_pr2_19_races.py tests/integration/phase2/test_pr2_19_rag_evidence.py tests/integration/phase2/test_pr2_19_rejection.py tests/integration/phase2/test_pr2_19_replay.py tests/integration/phase2/test_pr2_19_revision_cycle.py tests/integration/phase2/test_pr2_19_search_evidence.py tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/unit/phase2/test_pr2_08_native_strategy.py --tb=short --junitxml /var/folders/h5/hx7bbybn4j9422jrdzpkgln00000gp/T/b31-s4-5tqufo_e/owning-acceptance.xml"
  ],
  "contract_refs": [
    "docs/proposals/B31_PR2-20_Full_Exit_Hardening_Contract_DRAFT.md",
    "docs/proposals/PR2-20_Hardening_Plan_DRAFT.md"
  ],
  "corrected_term": null,
  "criterion": "ScientificConclusion support-set freeze",
  "dirty_diff_sha256": "8be7d685d474c9cb373d627bebe6e204e1a09e9a756145a9ed06b549edb1bb61",
  "disposition_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/scope-dispositions.json"
  ],
  "errors": 0,
  "evidence_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-08.json",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-000.txt",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-junit.xml"
  ],
  "exit_codes": [
    0
  ],
  "failed": 0,
  "finding_refs": [],
  "owning_prs": [
    "PR2-11"
  ],
  "passed": 16,
  "reason": null,
  "schema_version": 1,
  "skipped": 0,
  "status": "PASS",
  "subject_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "test_nodes": [
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_claim_only_freeze_exact_hash_restart_and_supersession",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_snapshot_exact_claim_and_project_binding",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_empty_freeze_and_unreviewed_positive_support_fail_closed",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_duplicate_request_concurrent_and_unauthorized",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_literature_only_freeze_and_hash_readback",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_positive_review_must_be_independent_of_conclusion_author",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_direct_evidence_dispute_blocks_freeze_without_partial_write",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_dispute_projects_stale_without_rewriting_frozen_history",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_revision_preserves_prior_hashes_and_moves_same_parent_pointer",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_frozen_science_rejects_direct_mutation",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_current_pointer_cannot_reference_superseded_at_commit",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_draft_inputs_change_only_through_authorized_application_command",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_empty_0033_downgrade_and_nonempty_history_protection",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_empty_0033_downgrade_succeeds"
  ]
}
```

### Exit row 9

Recorded after verification of the owning assertions and local log digests. Raw evidence paths below identify local artifacts; they are not file links.

```json
{
  "acceptance_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "commands": [
    "uv run pytest tests/architecture/test_pr2_19_boundaries.py tests/e2e/test_phase1_concurrency_acceptance.py tests/e2e/test_phase1_cross_adapter_equivalence.py tests/e2e/test_phase1_failure_recovery.py tests/e2e/test_phase1_golden_scientific_workflow.py tests/e2e/test_phase1_historical_exactness.py tests/e2e/test_phase1_performance_shape.py tests/integration/phase2/test_approval.py tests/integration/phase2/test_b02_strategy_admission.py tests/integration/phase2/test_b02_strategy_capture.py tests/integration/phase2/test_b03_discussion_hypothesis.py tests/integration/phase2/test_b03_discussion_hypothesis_guards.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b07_revision_decisions.py tests/integration/phase2/test_b08_issue_disposition.py tests/integration/phase2/test_b17_package_freeze.py tests/integration/phase2/test_b26_finding_impact.py tests/integration/phase2/test_b27_defensive_closure_read.py tests/integration/phase2/test_m1_manuscript_reconsideration.py tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_pr2_01_source_identity.py tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_application.py tests/integration/phase2/test_pr2_04_execution_provenance.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_19_approval_atomicity.py tests/integration/phase2/test_pr2_19_atomicity.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_citation_trace.py tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_discussion.py tests/integration/phase2/test_pr2_19_governance.py tests/integration/phase2/test_pr2_19_grant_consumption_publication.py tests/integration/phase2/test_pr2_19_grant_consumption_release.py tests/integration/phase2/test_pr2_19_integrity.py tests/integration/phase2/test_pr2_19_lineage.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_19_package_freeze.py tests/integration/phase2/test_pr2_19_races.py tests/integration/phase2/test_pr2_19_rag_evidence.py tests/integration/phase2/test_pr2_19_rejection.py tests/integration/phase2/test_pr2_19_replay.py tests/integration/phase2/test_pr2_19_revision_cycle.py tests/integration/phase2/test_pr2_19_search_evidence.py tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/unit/phase2/test_pr2_08_native_strategy.py --tb=short --junitxml /var/folders/h5/hx7bbybn4j9422jrdzpkgln00000gp/T/b31-s4-5tqufo_e/owning-acceptance.xml"
  ],
  "contract_refs": [
    "docs/proposals/B31_PR2-20_Full_Exit_Hardening_Contract_DRAFT.md",
    "docs/proposals/PR2-20_Hardening_Plan_DRAFT.md"
  ],
  "corrected_term": null,
  "criterion": "ScientificConclusion Frozen Provenance Closure",
  "dirty_diff_sha256": "8be7d685d474c9cb373d627bebe6e204e1a09e9a756145a9ed06b549edb1bb61",
  "disposition_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/scope-dispositions.json"
  ],
  "errors": 0,
  "evidence_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-09.json",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-000.txt",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-junit.xml"
  ],
  "exit_codes": [
    0
  ],
  "failed": 0,
  "finding_refs": [],
  "owning_prs": [
    "PR2-11"
  ],
  "passed": 20,
  "reason": null,
  "schema_version": 1,
  "skipped": 0,
  "status": "PASS",
  "subject_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "test_nodes": [
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_claim_only_freeze_exact_hash_restart_and_supersession",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_snapshot_exact_claim_and_project_binding",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_empty_freeze_and_unreviewed_positive_support_fail_closed",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_duplicate_request_concurrent_and_unauthorized",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_literature_only_freeze_and_hash_readback",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_positive_review_must_be_independent_of_conclusion_author",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_direct_evidence_dispute_blocks_freeze_without_partial_write",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_dispute_projects_stale_without_rewriting_frozen_history",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_revision_preserves_prior_hashes_and_moves_same_parent_pointer",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_frozen_science_rejects_direct_mutation",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_current_pointer_cannot_reference_superseded_at_commit",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_draft_inputs_change_only_through_authorized_application_command",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_empty_0033_downgrade_and_nonempty_history_protection",
    "tests/integration/phase2/test_pr2_11_r2_persistence.py::test_pg_empty_0033_downgrade_succeeds",
    "tests/integration/phase2/test_pr2_13_scientific_trace.py::test_unified_trace_exact_placements_and_experiment_path",
    "tests/integration/phase2/test_pr2_13_scientific_trace.py::test_unreviewed_contradiction_is_not_promoted_or_inferred_from_citation",
    "tests/integration/phase2/test_pr2_13_scientific_trace.py::test_empty_duplicate_and_unauthorized_trace",
    "tests/integration/phase2/test_pr2_13_scientific_trace.py::test_conclusion_trace_uses_only_its_pinned_claim_snapshot"
  ]
}
```

### Exit row 10

Recorded after verification of the owning assertions and local log digests. Raw evidence paths below identify local artifacts; they are not file links.

```json
{
  "acceptance_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "commands": [
    "uv run pytest tests/architecture/test_pr2_19_boundaries.py tests/e2e/test_phase1_concurrency_acceptance.py tests/e2e/test_phase1_cross_adapter_equivalence.py tests/e2e/test_phase1_failure_recovery.py tests/e2e/test_phase1_golden_scientific_workflow.py tests/e2e/test_phase1_historical_exactness.py tests/e2e/test_phase1_performance_shape.py tests/integration/phase2/test_approval.py tests/integration/phase2/test_b02_strategy_admission.py tests/integration/phase2/test_b02_strategy_capture.py tests/integration/phase2/test_b03_discussion_hypothesis.py tests/integration/phase2/test_b03_discussion_hypothesis_guards.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b07_revision_decisions.py tests/integration/phase2/test_b08_issue_disposition.py tests/integration/phase2/test_b17_package_freeze.py tests/integration/phase2/test_b26_finding_impact.py tests/integration/phase2/test_b27_defensive_closure_read.py tests/integration/phase2/test_m1_manuscript_reconsideration.py tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_pr2_01_source_identity.py tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_application.py tests/integration/phase2/test_pr2_04_execution_provenance.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_19_approval_atomicity.py tests/integration/phase2/test_pr2_19_atomicity.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_citation_trace.py tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_discussion.py tests/integration/phase2/test_pr2_19_governance.py tests/integration/phase2/test_pr2_19_grant_consumption_publication.py tests/integration/phase2/test_pr2_19_grant_consumption_release.py tests/integration/phase2/test_pr2_19_integrity.py tests/integration/phase2/test_pr2_19_lineage.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_19_package_freeze.py tests/integration/phase2/test_pr2_19_races.py tests/integration/phase2/test_pr2_19_rag_evidence.py tests/integration/phase2/test_pr2_19_rejection.py tests/integration/phase2/test_pr2_19_replay.py tests/integration/phase2/test_pr2_19_revision_cycle.py tests/integration/phase2/test_pr2_19_search_evidence.py tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/unit/phase2/test_pr2_08_native_strategy.py --tb=short --junitxml /var/folders/h5/hx7bbybn4j9422jrdzpkgln00000gp/T/b31-s4-5tqufo_e/owning-acceptance.xml"
  ],
  "contract_refs": [
    "docs/proposals/B31_PR2-20_Full_Exit_Hardening_Contract_DRAFT.md",
    "docs/proposals/PR2-20_Hardening_Plan_DRAFT.md"
  ],
  "corrected_term": null,
  "criterion": "ManuscriptVersion scientific placement",
  "dirty_diff_sha256": "8be7d685d474c9cb373d627bebe6e204e1a09e9a756145a9ed06b549edb1bb61",
  "disposition_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/scope-dispositions.json"
  ],
  "errors": 0,
  "evidence_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-10.json",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-000.txt",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-junit.xml"
  ],
  "exit_codes": [
    0
  ],
  "failed": 0,
  "finding_refs": [],
  "owning_prs": [
    "PR2-12",
    "PR2-13"
  ],
  "passed": 30,
  "reason": null,
  "schema_version": 1,
  "skipped": 0,
  "status": "PASS",
  "subject_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "test_nodes": [
    "tests/integration/phase2/test_b04_manuscript_freeze.py::test_empty_seal_restart_and_replay",
    "tests/integration/phase2/test_b04_manuscript_freeze.py::test_all_placements_and_frozen_readback",
    "tests/integration/phase2/test_b04_manuscript_freeze.py::test_changed_expectations_and_expired_credentials",
    "tests/integration/phase2/test_b04_manuscript_freeze.py::test_document_cas_failures",
    "tests/integration/phase2/test_b04_manuscript_freeze.py::test_rollback_seal_and_pointer",
    "tests/integration/phase2/test_b04_manuscript_freeze.py::test_positive_support_denies_new_seal_and_preserves_history",
    "tests/integration/phase2/test_b04_manuscript_freeze.py::test_broken_phase1_hashes_deny_formal_provenance",
    "tests/integration/phase2/test_b04_manuscript_freeze.py::test_literature_only_closure_verifies_source_artifacts_and_predecessor",
    "tests/integration/phase2/test_b04_manuscript_freeze.py::test_retry_aborted_transactions_from_fresh_share_snapshot",
    "tests/integration/phase2/test_pr2_13_scientific_trace.py::test_unified_trace_exact_placements_and_experiment_path",
    "tests/integration/phase2/test_pr2_13_scientific_trace.py::test_unreviewed_contradiction_is_not_promoted_or_inferred_from_citation",
    "tests/integration/phase2/test_pr2_13_scientific_trace.py::test_empty_duplicate_and_unauthorized_trace",
    "tests/integration/phase2/test_pr2_13_scientific_trace.py::test_conclusion_trace_uses_only_its_pinned_claim_snapshot",
    "tests/integration/phase2/test_pr2_19_citation_trace.py::test_citation_only_preserves_claim_hashes_and_numeric_facts",
    "tests/integration/phase2/test_pr2_19_citation_trace.py::test_experiment_and_literature_trace_paths_remain_separate",
    "tests/integration/phase2/test_pr2_19_citation_trace.py::test_g5_application_freeze_retains_exact_scientific_paths"
  ]
}
```

### Exit row 11

Recorded after verification of the owning assertions and local log digests. Raw evidence paths below identify local artifacts; they are not file links.

```json
{
  "acceptance_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "commands": [
    "uv run pytest tests/architecture/test_pr2_19_boundaries.py tests/e2e/test_phase1_concurrency_acceptance.py tests/e2e/test_phase1_cross_adapter_equivalence.py tests/e2e/test_phase1_failure_recovery.py tests/e2e/test_phase1_golden_scientific_workflow.py tests/e2e/test_phase1_historical_exactness.py tests/e2e/test_phase1_performance_shape.py tests/integration/phase2/test_approval.py tests/integration/phase2/test_b02_strategy_admission.py tests/integration/phase2/test_b02_strategy_capture.py tests/integration/phase2/test_b03_discussion_hypothesis.py tests/integration/phase2/test_b03_discussion_hypothesis_guards.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b07_revision_decisions.py tests/integration/phase2/test_b08_issue_disposition.py tests/integration/phase2/test_b17_package_freeze.py tests/integration/phase2/test_b26_finding_impact.py tests/integration/phase2/test_b27_defensive_closure_read.py tests/integration/phase2/test_m1_manuscript_reconsideration.py tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_pr2_01_source_identity.py tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_application.py tests/integration/phase2/test_pr2_04_execution_provenance.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_19_approval_atomicity.py tests/integration/phase2/test_pr2_19_atomicity.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_citation_trace.py tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_discussion.py tests/integration/phase2/test_pr2_19_governance.py tests/integration/phase2/test_pr2_19_grant_consumption_publication.py tests/integration/phase2/test_pr2_19_grant_consumption_release.py tests/integration/phase2/test_pr2_19_integrity.py tests/integration/phase2/test_pr2_19_lineage.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_19_package_freeze.py tests/integration/phase2/test_pr2_19_races.py tests/integration/phase2/test_pr2_19_rag_evidence.py tests/integration/phase2/test_pr2_19_rejection.py tests/integration/phase2/test_pr2_19_replay.py tests/integration/phase2/test_pr2_19_revision_cycle.py tests/integration/phase2/test_pr2_19_search_evidence.py tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/unit/phase2/test_pr2_08_native_strategy.py --tb=short --junitxml /var/folders/h5/hx7bbybn4j9422jrdzpkgln00000gp/T/b31-s4-5tqufo_e/owning-acceptance.xml"
  ],
  "contract_refs": [
    "docs/proposals/B31_PR2-20_Full_Exit_Hardening_Contract_DRAFT.md",
    "docs/proposals/PR2-20_Hardening_Plan_DRAFT.md"
  ],
  "corrected_term": null,
  "criterion": "Citation \u2260 ClaimSupport",
  "dirty_diff_sha256": "8be7d685d474c9cb373d627bebe6e204e1a09e9a756145a9ed06b549edb1bb61",
  "disposition_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/scope-dispositions.json"
  ],
  "errors": 0,
  "evidence_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-11.json",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-000.txt",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-junit.xml"
  ],
  "exit_codes": [
    0
  ],
  "failed": 0,
  "finding_refs": [],
  "owning_prs": [
    "PR2-13",
    "PR2-19"
  ],
  "passed": 3,
  "reason": null,
  "schema_version": 1,
  "skipped": 0,
  "status": "PASS",
  "subject_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "test_nodes": [
    "tests/integration/phase2/test_pr2_19_citation_trace.py::test_citation_only_preserves_claim_hashes_and_numeric_facts",
    "tests/integration/phase2/test_pr2_19_citation_trace.py::test_experiment_and_literature_trace_paths_remain_separate",
    "tests/integration/phase2/test_pr2_19_citation_trace.py::test_g5_application_freeze_retains_exact_scientific_paths"
  ]
}
```

### Exit row 12

Recorded after verification of the owning assertions and local log digests. Raw evidence paths below identify local artifacts; they are not file links.

```json
{
  "acceptance_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "commands": [
    "uv run pytest tests/architecture/test_pr2_19_boundaries.py tests/e2e/test_phase1_concurrency_acceptance.py tests/e2e/test_phase1_cross_adapter_equivalence.py tests/e2e/test_phase1_failure_recovery.py tests/e2e/test_phase1_golden_scientific_workflow.py tests/e2e/test_phase1_historical_exactness.py tests/e2e/test_phase1_performance_shape.py tests/integration/phase2/test_approval.py tests/integration/phase2/test_b02_strategy_admission.py tests/integration/phase2/test_b02_strategy_capture.py tests/integration/phase2/test_b03_discussion_hypothesis.py tests/integration/phase2/test_b03_discussion_hypothesis_guards.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b07_revision_decisions.py tests/integration/phase2/test_b08_issue_disposition.py tests/integration/phase2/test_b17_package_freeze.py tests/integration/phase2/test_b26_finding_impact.py tests/integration/phase2/test_b27_defensive_closure_read.py tests/integration/phase2/test_m1_manuscript_reconsideration.py tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_pr2_01_source_identity.py tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_application.py tests/integration/phase2/test_pr2_04_execution_provenance.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_19_approval_atomicity.py tests/integration/phase2/test_pr2_19_atomicity.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_citation_trace.py tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_discussion.py tests/integration/phase2/test_pr2_19_governance.py tests/integration/phase2/test_pr2_19_grant_consumption_publication.py tests/integration/phase2/test_pr2_19_grant_consumption_release.py tests/integration/phase2/test_pr2_19_integrity.py tests/integration/phase2/test_pr2_19_lineage.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_19_package_freeze.py tests/integration/phase2/test_pr2_19_races.py tests/integration/phase2/test_pr2_19_rag_evidence.py tests/integration/phase2/test_pr2_19_rejection.py tests/integration/phase2/test_pr2_19_replay.py tests/integration/phase2/test_pr2_19_revision_cycle.py tests/integration/phase2/test_pr2_19_search_evidence.py tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/unit/phase2/test_pr2_08_native_strategy.py --tb=short --junitxml /var/folders/h5/hx7bbybn4j9422jrdzpkgln00000gp/T/b31-s4-5tqufo_e/owning-acceptance.xml"
  ],
  "contract_refs": [
    "docs/proposals/B31_PR2-20_Full_Exit_Hardening_Contract_DRAFT.md",
    "docs/proposals/PR2-20_Hardening_Plan_DRAFT.md"
  ],
  "corrected_term": null,
  "criterion": "Internal Review \u2192 Issue \u2192 Decision \u2192 Revision",
  "dirty_diff_sha256": "8be7d685d474c9cb373d627bebe6e204e1a09e9a756145a9ed06b549edb1bb61",
  "disposition_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/scope-dispositions.json"
  ],
  "errors": 0,
  "evidence_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-12.json",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-000.txt",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-junit.xml"
  ],
  "exit_codes": [
    0
  ],
  "failed": 0,
  "finding_refs": [],
  "owning_prs": [
    "PR2-14",
    "PR2-15"
  ],
  "passed": 116,
  "reason": null,
  "schema_version": 1,
  "skipped": 0,
  "status": "PASS",
  "subject_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "test_nodes": [
    "tests/integration/phase2/test_pr2_19_revision_cycle.py::test_completed_result_does_not_dispose_until_independent_command",
    "tests/integration/phase2/test_pr2_19_revision_cycle.py::test_wrong_result_cannot_resolve_original_concern",
    "tests/integration/phase2/test_pr2_19_revision_cycle.py::test_completed_experiment_requires_exact_spec_run_pair",
    "tests/integration/phase2/test_pr2_19_revision_cycle.py::test_conclusion_cycle_new_target_proceed_request_decision_grant",
    "tests/integration/phase2/test_pr2_19_revision_cycle.py::test_draft_or_unrelated_conclusion_does_not_resolve_issue",
    "tests/integration/phase2/test_pr2_19_revision_cycle.py::test_revision_successor_cannot_fork_saved_history",
    "tests/integration/phase2/test_b07_revision_decisions.py::test_revision_decision_complete_adverse_snapshot_and_exact_concern",
    "tests/integration/phase2/test_b07_revision_decisions.py::test_changed_action_three_exact_basis_forms",
    "tests/integration/phase2/test_b07_revision_decisions.py::test_no_change_has_no_result_or_disposition",
    "tests/integration/phase2/test_b07_revision_decisions.py::test_ineligible_revision_basis_denies",
    "tests/integration/phase2/test_b07_revision_decisions.py::test_release_proceed_is_never_no_change_basis",
    "tests/integration/phase2/test_b07_revision_decisions.py::test_revision_response_is_never_approval_basis",
    "tests/integration/phase2/test_b07_revision_decisions.py::test_action_decision_reference_preserves_scope_and_absence_errors",
    "tests/integration/phase2/test_b07_revision_decisions.py::test_exact_read_graph_including_re_reviews_acquires_no_row_locks",
    "tests/integration/phase2/test_b08_issue_disposition.py::test_exact_terminal_transition_and_event_only_projection",
    "tests/integration/phase2/test_b08_issue_disposition.py::test_unfavorable_exact_link_is_history_not_permission",
    "tests/integration/phase2/test_b08_issue_disposition.py::test_selected_review_open_concern_denies",
    "tests/integration/phase2/test_b08_issue_disposition.py::test_wrong_actor_changed_payload_and_terminal_new_uuid",
    "tests/integration/phase2/test_b08_issue_disposition.py::test_mismatched_basis_denies_atomically",
    "tests/integration/phase2/test_b08_issue_disposition.py::test_all_five_changed_shapes_bind_exact_independent_re_review",
    "tests/integration/phase2/test_b08_issue_disposition.py::test_transition_at_each_severity_retains_explicit_decision",
    "tests/integration/phase2/test_b08_issue_disposition.py::test_disposer_authority_and_independence",
    "tests/integration/phase2/test_b08_issue_disposition.py::test_blocking_issue_only_changed_action_is_insufficient",
    "tests/integration/phase2/test_b08_issue_disposition.py::test_disposition_preserves_other_blockers_and_creates_no_other_governance_records",
    "tests/integration/phase2/test_b08_issue_disposition.py::test_same_result_link_for_another_action_is_not_correspondence",
    "tests/integration/phase2/test_b08_issue_disposition.py::test_new_changed_disposition_denies_invalid_result_in_application_and_sql",
    "tests/integration/phase2/test_b08_issue_disposition.py::test_exact_reads_authenticate_before_absence_and_foreign_scope_disclosure",
    "tests/integration/phase2/test_m1_manuscript_revision.py::test_manuscript_revision_decision_action_re_review_disposition",
    "tests/integration/phase2/test_m1_manuscript_revision.py::test_successor_conflicts_and_invalid_change_class",
    "tests/integration/phase2/test_m1_manuscript_revision.py::test_historical_placement_trace_and_replay_after_successor_are_lock_free",
    "tests/integration/phase2/test_m1_manuscript_reconsideration.py::test_correction_successor_separate_approve_and_lock_free_replay",
    "tests/integration/phase2/test_m1_manuscript_reconsideration.py::test_invalid_evidence_and_conflicts_rollback",
    "tests/integration/phase2/test_m1_manuscript_reconsideration.py::test_s2_upgrade_downgrade_restores_exact_0074_catalog",
    "tests/integration/phase2/test_m1_manuscript_reconsideration.py::test_direct_sql_bypass_denied_atomically",
    "tests/integration/phase2/test_m1_manuscript_reconsideration.py::test_exact_replay_after_write_role_loss_and_changed_scope_denials",
    "tests/integration/phase2/test_m1_manuscript_reconsideration.py::test_successor_reuse_and_actor_independence",
    "tests/integration/phase2/test_m1_manuscript_reconsideration.py::test_saved_s2_basis_rederives_ordinals_without_admission",
    "tests/integration/phase2/test_m1_manuscript_reconsideration.py::test_current_target_invalid_denies_but_old_corrected_target_may_be_stale"
  ]
}
```

### Exit row 13

Recorded after verification of the owning assertions and local log digests. Raw evidence paths below identify local artifacts; they are not file links.

```json
{
  "acceptance_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "commands": [
    "uv run pytest tests/architecture/test_pr2_19_boundaries.py tests/e2e/test_phase1_concurrency_acceptance.py tests/e2e/test_phase1_cross_adapter_equivalence.py tests/e2e/test_phase1_failure_recovery.py tests/e2e/test_phase1_golden_scientific_workflow.py tests/e2e/test_phase1_historical_exactness.py tests/e2e/test_phase1_performance_shape.py tests/integration/phase2/test_approval.py tests/integration/phase2/test_b02_strategy_admission.py tests/integration/phase2/test_b02_strategy_capture.py tests/integration/phase2/test_b03_discussion_hypothesis.py tests/integration/phase2/test_b03_discussion_hypothesis_guards.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b07_revision_decisions.py tests/integration/phase2/test_b08_issue_disposition.py tests/integration/phase2/test_b17_package_freeze.py tests/integration/phase2/test_b26_finding_impact.py tests/integration/phase2/test_b27_defensive_closure_read.py tests/integration/phase2/test_m1_manuscript_reconsideration.py tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_pr2_01_source_identity.py tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_application.py tests/integration/phase2/test_pr2_04_execution_provenance.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_19_approval_atomicity.py tests/integration/phase2/test_pr2_19_atomicity.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_citation_trace.py tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_discussion.py tests/integration/phase2/test_pr2_19_governance.py tests/integration/phase2/test_pr2_19_grant_consumption_publication.py tests/integration/phase2/test_pr2_19_grant_consumption_release.py tests/integration/phase2/test_pr2_19_integrity.py tests/integration/phase2/test_pr2_19_lineage.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_19_package_freeze.py tests/integration/phase2/test_pr2_19_races.py tests/integration/phase2/test_pr2_19_rag_evidence.py tests/integration/phase2/test_pr2_19_rejection.py tests/integration/phase2/test_pr2_19_replay.py tests/integration/phase2/test_pr2_19_revision_cycle.py tests/integration/phase2/test_pr2_19_search_evidence.py tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/unit/phase2/test_pr2_08_native_strategy.py --tb=short --junitxml /var/folders/h5/hx7bbybn4j9422jrdzpkgln00000gp/T/b31-s4-5tqufo_e/owning-acceptance.xml"
  ],
  "contract_refs": [
    "docs/proposals/B31_PR2-20_Full_Exit_Hardening_Contract_DRAFT.md",
    "docs/proposals/PR2-20_Hardening_Plan_DRAFT.md"
  ],
  "corrected_term": null,
  "criterion": "Basic Approval frozen target / blocking gate",
  "dirty_diff_sha256": "8be7d685d474c9cb373d627bebe6e204e1a09e9a756145a9ed06b549edb1bb61",
  "disposition_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/scope-dispositions.json"
  ],
  "errors": 0,
  "evidence_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-13.json",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-000.txt",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-junit.xml"
  ],
  "exit_codes": [
    0
  ],
  "failed": 0,
  "finding_refs": [],
  "owning_prs": [
    "PR2-16"
  ],
  "passed": 113,
  "reason": null,
  "schema_version": 1,
  "skipped": 0,
  "status": "PASS",
  "subject_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "test_nodes": [
    "tests/integration/phase2/test_approval.py::test_approval_atomic_history_and_replay",
    "tests/integration/phase2/test_approval.py::test_rejection_scope_and_pending_bypass",
    "tests/integration/phase2/test_approval.py::test_conflicts_and_independence",
    "tests/integration/phase2/test_approval.py::test_current_stale_gate_and_historical_replay",
    "tests/integration/phase2/test_approval.py::test_later_blocking_review_denies_pending_decision",
    "tests/integration/phase2/test_approval.py::test_all_outcomes_and_changed_replay",
    "tests/integration/phase2/test_approval.py::test_finite_expiry_gate",
    "tests/integration/phase2/test_approval.py::test_saved_basis_and_later_unfavorable_review",
    "tests/integration/phase2/test_approval.py::test_live_authority_loss_stales_grant_atomically",
    "tests/integration/phase2/test_approval.py::test_normal_role_history_guards",
    "tests/integration/phase2/test_approval.py::test_failure_rolls_back_all_success_events",
    "tests/integration/phase2/test_approval.py::test_concurrent_outcomes_one_decision_and_grant",
    "tests/integration/phase2/test_approval.py::test_downgrade_preserves_history",
    "tests/integration/phase2/test_approval.py::test_actual_target_wait_crosses_expiry",
    "tests/integration/phase2/test_approval.py::test_review_insert_commit_orders_are_observed",
    "tests/integration/phase2/test_approval.py::test_empty_downgrade_upgrade_and_catalog",
    "tests/integration/phase2/test_approval.py::test_normal_sql_cannot_bypass_approval_gate",
    "tests/integration/phase2/test_approval.py::test_pending_other_target_cannot_bypass_rejection",
    "tests/integration/phase2/test_approval.py::test_sql_float_spelling_preserves_python_canonical_hash",
    "tests/integration/phase2/test_approval.py::test_normal_sql_rejects_forged_frozen_leaf_hashes",
    "tests/integration/phase2/test_approval.py::test_literature_closure_has_same_application_and_sql_gate",
    "tests/integration/phase2/test_approval.py::test_navigation_supersession_preserves_grant_until_new_approval_target_selected",
    "tests/integration/phase2/test_approval.py::test_archived_project_preserves_history_but_grant_is_unusable",
    "tests/integration/phase2/test_approval.py::test_normal_sql_cannot_shadow_authority_or_invoke_uncontracted_lifecycle",
    "tests/integration/phase2/test_approval.py::test_grant_utc_thirty_days_is_independent_of_session_dst",
    "tests/integration/phase2/test_approval.py::test_normal_sql_denies_noncanonical_or_blank_rationale",
    "tests/integration/phase2/test_approval.py::test_normal_sql_request_denies_future_credential_binding",
    "tests/integration/phase2/test_approval.py::test_new_target_selection_denies_late_approval_of_old_pending_request",
    "tests/integration/phase2/test_approval.py::test_b09_rejection_fences_other_target_older_pending_request",
    "tests/integration/phase2/test_pr2_19_governance.py::test_complete_unfavorable_basis_does_not_change_target_or_effects",
    "tests/integration/phase2/test_pr2_19_governance.py::test_exact_open_blocking_predicate",
    "tests/integration/phase2/test_pr2_19_governance.py::test_unrelated_issue_control",
    "tests/integration/phase2/test_pr2_19_governance.py::test_authority_and_closed_boundary_zero_delta",
    "tests/integration/phase2/test_pr2_19_governance.py::test_approval_current_fact_denial_retains_committed_request",
    "tests/integration/phase2/test_pr2_19_governance.py::test_approval_independence_and_authority_matrix",
    "tests/integration/phase2/test_pr2_19_governance.py::test_snapshot_observer_uses_server_settings_across_pooled_reuse",
    "tests/integration/phase2/test_pr2_19_governance.py::test_closed_approval_command_rejects_bypass_fields",
    "tests/integration/phase2/test_pr2_19_governance.py::test_wrong_purpose_target_tuple_never_creates_approval",
    "tests/integration/phase2/test_pr2_19_governance.py::test_approval_expiry_denial_retains_committed_request",
    "tests/integration/phase2/test_pr2_19_governance.py::test_complete_adverse_review_basis_cannot_be_substituted",
    "tests/integration/phase2/test_pr2_19_governance.py::test_agent_with_existing_role_and_verified_binding_cannot_approve",
    "tests/integration/phase2/test_pr2_19_governance.py::test_f5_ready_consumption_uses_current_issue_not_recommendation",
    "tests/integration/phase2/test_pr2_19_approval_atomicity.py::test_protected_command_rolls_back_but_committed_predecessors_survive"
  ]
}
```

### Exit row 14

Recorded after verification of the owning assertions and local log digests. Raw evidence paths below identify local artifacts; they are not file links.

```json
{
  "acceptance_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "commands": [
    "uv run pytest tests/architecture/test_pr2_19_boundaries.py tests/e2e/test_phase1_concurrency_acceptance.py tests/e2e/test_phase1_cross_adapter_equivalence.py tests/e2e/test_phase1_failure_recovery.py tests/e2e/test_phase1_golden_scientific_workflow.py tests/e2e/test_phase1_historical_exactness.py tests/e2e/test_phase1_performance_shape.py tests/integration/phase2/test_approval.py tests/integration/phase2/test_b02_strategy_admission.py tests/integration/phase2/test_b02_strategy_capture.py tests/integration/phase2/test_b03_discussion_hypothesis.py tests/integration/phase2/test_b03_discussion_hypothesis_guards.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b07_revision_decisions.py tests/integration/phase2/test_b08_issue_disposition.py tests/integration/phase2/test_b17_package_freeze.py tests/integration/phase2/test_b26_finding_impact.py tests/integration/phase2/test_b27_defensive_closure_read.py tests/integration/phase2/test_m1_manuscript_reconsideration.py tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_pr2_01_source_identity.py tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_application.py tests/integration/phase2/test_pr2_04_execution_provenance.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_19_approval_atomicity.py tests/integration/phase2/test_pr2_19_atomicity.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_citation_trace.py tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_discussion.py tests/integration/phase2/test_pr2_19_governance.py tests/integration/phase2/test_pr2_19_grant_consumption_publication.py tests/integration/phase2/test_pr2_19_grant_consumption_release.py tests/integration/phase2/test_pr2_19_integrity.py tests/integration/phase2/test_pr2_19_lineage.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_19_package_freeze.py tests/integration/phase2/test_pr2_19_races.py tests/integration/phase2/test_pr2_19_rag_evidence.py tests/integration/phase2/test_pr2_19_rejection.py tests/integration/phase2/test_pr2_19_replay.py tests/integration/phase2/test_pr2_19_revision_cycle.py tests/integration/phase2/test_pr2_19_search_evidence.py tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/unit/phase2/test_pr2_08_native_strategy.py --tb=short --junitxml /var/folders/h5/hx7bbybn4j9422jrdzpkgln00000gp/T/b31-s4-5tqufo_e/owning-acceptance.xml"
  ],
  "contract_refs": [
    "docs/proposals/B31_PR2-20_Full_Exit_Hardening_Contract_DRAFT.md",
    "docs/proposals/PR2-20_Hardening_Plan_DRAFT.md"
  ],
  "corrected_term": "PreparedSubmissionVersion",
  "criterion": "SubmissionVersion package freeze",
  "dirty_diff_sha256": "8be7d685d474c9cb373d627bebe6e204e1a09e9a756145a9ed06b549edb1bb61",
  "disposition_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/scope-dispositions.json"
  ],
  "errors": 0,
  "evidence_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-14.json",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-000.txt",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-junit.xml"
  ],
  "exit_codes": [
    0
  ],
  "failed": 0,
  "finding_refs": [],
  "owning_prs": [
    "PR2-17"
  ],
  "passed": 87,
  "reason": null,
  "schema_version": 1,
  "skipped": 0,
  "status": "PASS",
  "subject_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "test_nodes": [
    "tests/integration/phase2/test_pr2_19_package_freeze.py::test_g7_ready_preparation_consent_freeze_then_withdrawal_is_derived_stale",
    "tests/integration/phase2/test_pr2_19_package_freeze.py::test_g7_denied_freeze_has_no_partial_suffix",
    "tests/integration/phase2/test_pr2_19_package_freeze.py::test_g7_full_committed_trace_literal_hashes_and_snapshot_readers",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_first_use_denials_preserve_exact_predecessors",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_restart_replay_conflict_and_single_use",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_lost_commit_response_recovers_without_second_write",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_observed_competitors_have_one_concrete_effect",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_each_effect_write_and_deferred_check_rolls_back",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_freeze_withdrawal_observed_serial_orders",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_terminal_grants_cannot_create_effect",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_package_specific_current_closure",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_observed_required_wait_crosses_credential_or_grant_expiry",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_replay_needs_read_authority_after_writer_offboarding",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_role_closure_commits_across_observed_required_wait",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_ready_cannot_consume_real_prepare_permission",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_package_sealed_review_completeness_and_completed_manifest_conflict",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_real_other_manuscript_grant_cannot_authorize_saved_target",
    "tests/integration/phase2/test_b17_package_freeze.py::test_complete_freeze_and_concrete_receipt",
    "tests/integration/phase2/test_b17_package_freeze.py::test_substitution_has_no_partial_effect",
    "tests/integration/phase2/test_b17_package_freeze.py::test_consent_is_mandatory",
    "tests/integration/phase2/test_b17_package_freeze.py::test_exact_retained_bytes_required_and_zero_partial_effect",
    "tests/integration/phase2/test_b17_package_freeze.py::test_consumed_grant_cannot_freeze_a_fresh_package",
    "tests/integration/phase2/test_b17_package_freeze.py::test_complete_sealed_multi_review_set_cannot_be_changed",
    "tests/integration/phase2/test_b17_package_freeze.py::test_later_real_blocking_issue_denies_without_staling_maintenance",
    "tests/integration/phase2/test_b17_package_freeze.py::test_current_scientific_invalidation_precedes_package_authority",
    "tests/integration/phase2/test_b17_package_freeze.py::test_missing_immutable_consent_condition_is_unusable_and_sql_lifecycle_agrees",
    "tests/integration/phase2/test_b17_package_freeze.py::test_every_current_author_is_captured_at_zero_based_authored_position",
    "tests/integration/phase2/test_b17_package_freeze.py::test_prepare_blocker_maintenance_persists_stale_and_event",
    "tests/integration/phase2/test_b17_package_freeze.py::test_b32_freeze_preserves_ready_history_and_local_receipt",
    "tests/integration/phase2/test_b17_package_freeze.py::test_b32_exact_reads_and_completed_freeze_are_readonly_snapshots"
  ]
}
```

### Exit row 15

Recorded after verification of the owning assertions and local log digests. Raw evidence paths below identify local artifacts; they are not file links.

```json
{
  "acceptance_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "commands": [
    "uv run pytest tests/architecture/test_pr2_19_boundaries.py tests/e2e/test_phase1_concurrency_acceptance.py tests/e2e/test_phase1_cross_adapter_equivalence.py tests/e2e/test_phase1_failure_recovery.py tests/e2e/test_phase1_golden_scientific_workflow.py tests/e2e/test_phase1_historical_exactness.py tests/e2e/test_phase1_performance_shape.py tests/integration/phase2/test_approval.py tests/integration/phase2/test_b02_strategy_admission.py tests/integration/phase2/test_b02_strategy_capture.py tests/integration/phase2/test_b03_discussion_hypothesis.py tests/integration/phase2/test_b03_discussion_hypothesis_guards.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b07_revision_decisions.py tests/integration/phase2/test_b08_issue_disposition.py tests/integration/phase2/test_b17_package_freeze.py tests/integration/phase2/test_b26_finding_impact.py tests/integration/phase2/test_b27_defensive_closure_read.py tests/integration/phase2/test_m1_manuscript_reconsideration.py tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_pr2_01_source_identity.py tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_application.py tests/integration/phase2/test_pr2_04_execution_provenance.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_19_approval_atomicity.py tests/integration/phase2/test_pr2_19_atomicity.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_citation_trace.py tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_discussion.py tests/integration/phase2/test_pr2_19_governance.py tests/integration/phase2/test_pr2_19_grant_consumption_publication.py tests/integration/phase2/test_pr2_19_grant_consumption_release.py tests/integration/phase2/test_pr2_19_integrity.py tests/integration/phase2/test_pr2_19_lineage.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_19_package_freeze.py tests/integration/phase2/test_pr2_19_races.py tests/integration/phase2/test_pr2_19_rag_evidence.py tests/integration/phase2/test_pr2_19_rejection.py tests/integration/phase2/test_pr2_19_replay.py tests/integration/phase2/test_pr2_19_revision_cycle.py tests/integration/phase2/test_pr2_19_search_evidence.py tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/unit/phase2/test_pr2_08_native_strategy.py --tb=short --junitxml /var/folders/h5/hx7bbybn4j9422jrdzpkgln00000gp/T/b31-s4-5tqufo_e/owning-acceptance.xml"
  ],
  "contract_refs": [
    "docs/proposals/B31_PR2-20_Full_Exit_Hardening_Contract_DRAFT.md",
    "docs/proposals/PR2-20_Hardening_Plan_DRAFT.md"
  ],
  "corrected_term": null,
  "criterion": "Retracted-source impact propagation",
  "dirty_diff_sha256": "8be7d685d474c9cb373d627bebe6e204e1a09e9a756145a9ed06b549edb1bb61",
  "disposition_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/scope-dispositions.json"
  ],
  "errors": 0,
  "evidence_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-15.json",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-000.txt",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-junit.xml"
  ],
  "exit_codes": [
    0
  ],
  "failed": 0,
  "finding_refs": [],
  "owning_prs": [
    "PR2-19"
  ],
  "passed": 105,
  "reason": null,
  "schema_version": 1,
  "skipped": 0,
  "status": "PASS",
  "subject_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "test_nodes": [
    "tests/integration/phase2/test_pr2_19_lineage.py::test_lineage_rejection_has_zero_delta",
    "tests/integration/phase2/test_pr2_19_lineage.py::test_lineage_preserves_exact_bytes_and_blocks_new_support",
    "tests/integration/phase2/test_pr2_19_lineage.py::test_concurrent_corrections_cannot_fork_current_lineage",
    "tests/integration/phase2/test_pr2_19_lineage.py::test_current_manuscript_projection_audit_retains_frozen_material",
    "tests/integration/phase2/test_pr2_19_lineage.py::test_f1_current_downstream_facts_preserve_saved_consumptions",
    "tests/integration/phase2/test_pr2_19_lineage.py::test_f1_unrelated_source_control_does_not_block_ready_or_package",
    "tests/integration/phase2/test_b26_finding_impact.py::test_historical_status_conclusion_and_exact_occurrences",
    "tests/integration/phase2/test_b26_finding_impact.py::test_conflicting_assessments_correction_and_unlinked_state",
    "tests/integration/phase2/test_b26_finding_impact.py::test_unassessed_zero_match_is_complete_success",
    "tests/integration/phase2/test_b26_finding_impact.py::test_literature_bound_claim_validity_without_fabricated_records",
    "tests/integration/phase2/test_b26_finding_impact.py::test_root_policy_and_cas_failures",
    "tests/integration/phase2/test_b26_finding_impact.py::test_saved_corruption_fails_closed",
    "tests/integration/phase2/test_b26_finding_impact.py::test_citation_artifact_and_retained_predecessor_navigation",
    "tests/integration/phase2/test_b26_finding_impact.py::test_database_inventory_ceiling_before_hydration",
    "tests/integration/phase2/test_b26_finding_impact.py::test_unreachable_linked_target_is_still_verified",
    "tests/integration/phase2/test_b26_finding_impact.py::test_combined_response_budget_on_prepared_database_snapshot",
    "tests/integration/phase2/test_b26_finding_impact.py::test_selected_history_does_not_claim_other_invalidity",
    "tests/integration/phase2/test_b27_defensive_closure_read.py::test_conclusion_saved_direct_and_transitive_absence",
    "tests/integration/phase2/test_b27_defensive_closure_read.py::test_saved_decision_missing_basis_cannot_replay",
    "tests/integration/phase2/test_b27_defensive_closure_read.py::test_internal_review_transitive_missing_measurement",
    "tests/integration/phase2/test_b27_defensive_closure_read.py::test_trace_keeps_missing_selected_snapshot_branch",
    "tests/integration/phase2/test_b27_defensive_closure_read.py::test_each_novelty_reader_preserves_unresolved_ownership",
    "tests/integration/phase2/test_b27_defensive_closure_read.py::test_conclusion_snapshot_is_readonly_lock_free_and_final_expiry_denies",
    "tests/integration/phase2/test_b27_defensive_closure_read.py::test_diagnostic_missing_measurement_retains_report",
    "tests/integration/phase2/test_b27_defensive_closure_read.py::test_one_snapshot_survives_concurrent_committed_corruption",
    "tests/integration/phase2/test_b27_defensive_closure_read.py::test_normal_role_guards_remain_enforced",
    "tests/integration/phase2/test_b27_defensive_closure_read.py::test_removed_snapshot_membership_cannot_shorten_trace",
    "tests/integration/phase2/test_b27_defensive_closure_read.py::test_trace_and_diagnostics_reject_missing_transitive_identity",
    "tests/integration/phase2/test_b27_defensive_closure_read.py::test_statistical_result_and_each_selected_input_resolve",
    "tests/integration/phase2/test_b27_defensive_closure_read.py::test_saved_source_owning_identity_and_permission_nondisclosure",
    "tests/integration/phase2/test_b27_defensive_closure_read.py::test_saved_other_project_claim_is_closure_not_disclosing_not_found",
    "tests/integration/phase2/test_b27_defensive_closure_read.py::test_source_predecessor_must_resolve_in_every_trace_branch"
  ]
}
```

### Exit row 16

Recorded after verification of the owning assertions and local log digests. Raw evidence paths below identify local artifacts; they are not file links.

```json
{
  "acceptance_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "commands": [
    "uv run pytest tests/architecture/test_pr2_19_boundaries.py tests/e2e/test_phase1_concurrency_acceptance.py tests/e2e/test_phase1_cross_adapter_equivalence.py tests/e2e/test_phase1_failure_recovery.py tests/e2e/test_phase1_golden_scientific_workflow.py tests/e2e/test_phase1_historical_exactness.py tests/e2e/test_phase1_performance_shape.py tests/integration/phase2/test_approval.py tests/integration/phase2/test_b02_strategy_admission.py tests/integration/phase2/test_b02_strategy_capture.py tests/integration/phase2/test_b03_discussion_hypothesis.py tests/integration/phase2/test_b03_discussion_hypothesis_guards.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b07_revision_decisions.py tests/integration/phase2/test_b08_issue_disposition.py tests/integration/phase2/test_b17_package_freeze.py tests/integration/phase2/test_b26_finding_impact.py tests/integration/phase2/test_b27_defensive_closure_read.py tests/integration/phase2/test_m1_manuscript_reconsideration.py tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_pr2_01_source_identity.py tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_application.py tests/integration/phase2/test_pr2_04_execution_provenance.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_19_approval_atomicity.py tests/integration/phase2/test_pr2_19_atomicity.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_citation_trace.py tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_discussion.py tests/integration/phase2/test_pr2_19_governance.py tests/integration/phase2/test_pr2_19_grant_consumption_publication.py tests/integration/phase2/test_pr2_19_grant_consumption_release.py tests/integration/phase2/test_pr2_19_integrity.py tests/integration/phase2/test_pr2_19_lineage.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_19_package_freeze.py tests/integration/phase2/test_pr2_19_races.py tests/integration/phase2/test_pr2_19_rag_evidence.py tests/integration/phase2/test_pr2_19_rejection.py tests/integration/phase2/test_pr2_19_replay.py tests/integration/phase2/test_pr2_19_revision_cycle.py tests/integration/phase2/test_pr2_19_search_evidence.py tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/unit/phase2/test_pr2_08_native_strategy.py --tb=short --junitxml /var/folders/h5/hx7bbybn4j9422jrdzpkgln00000gp/T/b31-s4-5tqufo_e/owning-acceptance.xml"
  ],
  "contract_refs": [
    "docs/proposals/B31_PR2-20_Full_Exit_Hardening_Contract_DRAFT.md",
    "docs/proposals/PR2-20_Hardening_Plan_DRAFT.md"
  ],
  "corrected_term": null,
  "criterion": "Hallucinated citation rejection",
  "dirty_diff_sha256": "8be7d685d474c9cb373d627bebe6e204e1a09e9a756145a9ed06b549edb1bb61",
  "disposition_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/scope-dispositions.json"
  ],
  "errors": 0,
  "evidence_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-16.json",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-000.txt",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-junit.xml"
  ],
  "exit_codes": [
    0
  ],
  "failed": 0,
  "finding_refs": [],
  "owning_prs": [
    "PR2-19"
  ],
  "passed": 59,
  "reason": null,
  "schema_version": 1,
  "skipped": 0,
  "status": "PASS",
  "subject_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "test_nodes": [
    "tests/integration/phase2/test_pr2_19_candidates.py::test_native_strategy_is_candidate_only",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_candidate_exact_corpus_and_zero_scientific_delta",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_saved_native_brief_question_and_researcher_adaptation_after_restart",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_exact_replay_and_changed_payload_zero_delta",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_invalid_selector_or_unanswered_section_zero_delta",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_cas_corruption_denies_admission_and_exact_read",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_fault_after_admission_insert_rolls_back_root_and_version",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_creation_guard_maps_failure_and_rolls_back",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_admission_history_is_immutable",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_credentials_revoked_during_observed_share_wait",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_historical_replay_after_application_closes_writer_roles",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_duplicate_loser_with_backend_wait",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_inaccessible_source_precedes_frozen_reference_gate",
    "tests/integration/phase2/test_pr2_19_integrity.py::test_cas_integrity_failure_has_zero_canonical_delta",
    "tests/integration/phase2/test_pr2_19_integrity.py::test_normal_role_immutability_and_fk_denial",
    "tests/integration/phase2/test_pr2_19_integrity.py::test_saved_hash_corruption_fails_closed",
    "tests/integration/phase2/test_pr2_19_integrity.py::test_normal_role_missing_author_fk_rejects_new_evidence",
    "tests/integration/phase2/test_pr2_19_integrity.py::test_corrupt_committed_decision_hash_denies_fresh_exact_replay",
    "tests/integration/phase2/test_pr2_19_integrity.py::test_f2b_unresolved_saved_review_denies_owning_replay",
    "tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py::test_offline_candidate_preserves_source_locator_and_provenance",
    "tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py::test_request_requires_a_nonempty_unique_source_set",
    "tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py::test_foreign_source_version_is_rejected_without_partial_candidate",
    "tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py::test_unverifiable_or_unbounded_locator_is_rejected",
    "tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py::test_internal_index_identifier_cannot_be_used_as_source_locator",
    "tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py::test_locator_label_cannot_hide_an_opaque_reference",
    "tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py::test_structured_char_span_is_bounded_and_source_addressed",
    "tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py::test_duplicate_source_locator_and_candidate_budget_are_rejected",
    "tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py::test_answer_and_excerpt_are_bounded_and_answer_requires_evidence",
    "tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py::test_cancellation_prevents_fake_answer_without_claiming_provider_result",
    "tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py::test_query_and_adapter_provenance_cannot_be_substituted"
  ]
}
```

### Exit row 17

Recorded after verification of the owning assertions and local log digests. Raw evidence paths below identify local artifacts; they are not file links.

```json
{
  "acceptance_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "commands": [
    "uv run pytest tests/integration/phase2/test_pr2_20_security.py tests/integration/phase2/test_pr2_20_catalog_plans.py tests/integration/phase2/test_pr2_20_migrations.py tests/integration/phase2/test_pr2_20_governance_races.py tests/integration/phase2/test_pr2_20_novelty.py tests/e2e/test_pr2_20_benchmark.py --tb=short --junitxml /var/folders/h5/hx7bbybn4j9422jrdzpkgln00000gp/T/b31-s4-5tqufo_e/changed-postgres.xml",
    "uv run pytest tests/architecture/test_pr2_19_boundaries.py tests/e2e/test_phase1_concurrency_acceptance.py tests/e2e/test_phase1_cross_adapter_equivalence.py tests/e2e/test_phase1_failure_recovery.py tests/e2e/test_phase1_golden_scientific_workflow.py tests/e2e/test_phase1_historical_exactness.py tests/e2e/test_phase1_performance_shape.py tests/integration/phase2/test_approval.py tests/integration/phase2/test_b02_strategy_admission.py tests/integration/phase2/test_b02_strategy_capture.py tests/integration/phase2/test_b03_discussion_hypothesis.py tests/integration/phase2/test_b03_discussion_hypothesis_guards.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b07_revision_decisions.py tests/integration/phase2/test_b08_issue_disposition.py tests/integration/phase2/test_b17_package_freeze.py tests/integration/phase2/test_b26_finding_impact.py tests/integration/phase2/test_b27_defensive_closure_read.py tests/integration/phase2/test_m1_manuscript_reconsideration.py tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_pr2_01_source_identity.py tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_application.py tests/integration/phase2/test_pr2_04_execution_provenance.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_19_approval_atomicity.py tests/integration/phase2/test_pr2_19_atomicity.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_citation_trace.py tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_discussion.py tests/integration/phase2/test_pr2_19_governance.py tests/integration/phase2/test_pr2_19_grant_consumption_publication.py tests/integration/phase2/test_pr2_19_grant_consumption_release.py tests/integration/phase2/test_pr2_19_integrity.py tests/integration/phase2/test_pr2_19_lineage.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_19_package_freeze.py tests/integration/phase2/test_pr2_19_races.py tests/integration/phase2/test_pr2_19_rag_evidence.py tests/integration/phase2/test_pr2_19_rejection.py tests/integration/phase2/test_pr2_19_replay.py tests/integration/phase2/test_pr2_19_revision_cycle.py tests/integration/phase2/test_pr2_19_search_evidence.py tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/unit/phase2/test_pr2_08_native_strategy.py --tb=short --junitxml /var/folders/h5/hx7bbybn4j9422jrdzpkgln00000gp/T/b31-s4-5tqufo_e/owning-acceptance.xml"
  ],
  "contract_refs": [
    "docs/proposals/B31_PR2-20_Full_Exit_Hardening_Contract_DRAFT.md",
    "docs/proposals/PR2-20_Hardening_Plan_DRAFT.md"
  ],
  "corrected_term": null,
  "criterion": "PostgreSQL migrations/integration",
  "dirty_diff_sha256": "8be7d685d474c9cb373d627bebe6e204e1a09e9a756145a9ed06b549edb1bb61",
  "disposition_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/scope-dispositions.json",
    "docs/proposals/Owner_Decision_Linux_Benchmark_Host_2026-10-20.md"
  ],
  "errors": 0,
  "evidence_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-17.json",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/changed-postgres-000.txt",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/changed-postgres-junit.xml",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-000.txt",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-junit.xml"
  ],
  "exit_codes": [
    0,
    0
  ],
  "failed": 0,
  "finding_refs": [],
  "owning_prs": [
    "PR2-20"
  ],
  "passed": 485,
  "reason": "Dedicated Linux benchmark host not tested for now; owner-accepted deferral 2026-10-20 for benchmark-host part only; local macOS timings informational, not a substitute; all other owning assertions verified",
  "schema_version": 1,
  "skipped": 0,
  "status": "DEFERRED",
  "subject_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "test_nodes": [
    "tests/integration/phase2/test_pr2_19_approval_atomicity.py::test_protected_command_rolls_back_but_committed_predecessors_survive",
    "tests/integration/phase2/test_pr2_19_atomicity.py::test_discussion_parent_relation_receipt_rollback",
    "tests/integration/phase2/test_pr2_19_atomicity.py::test_decision_rollback_keeps_predecessor_review",
    "tests/integration/phase2/test_pr2_19_atomicity.py::test_review_event_abort_preserves_unreviewed_evidence",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_native_strategy_is_candidate_only",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_candidate_exact_corpus_and_zero_scientific_delta",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_saved_native_brief_question_and_researcher_adaptation_after_restart",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_exact_replay_and_changed_payload_zero_delta",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_invalid_selector_or_unanswered_section_zero_delta",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_cas_corruption_denies_admission_and_exact_read",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_fault_after_admission_insert_rolls_back_root_and_version",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_creation_guard_maps_failure_and_rolls_back",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_admission_history_is_immutable",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_credentials_revoked_during_observed_share_wait",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_historical_replay_after_application_closes_writer_roles",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_duplicate_loser_with_backend_wait",
    "tests/integration/phase2/test_pr2_19_candidates.py::test_g2_inaccessible_source_precedes_frozen_reference_gate",
    "tests/integration/phase2/test_pr2_19_citation_trace.py::test_citation_only_preserves_claim_hashes_and_numeric_facts",
    "tests/integration/phase2/test_pr2_19_citation_trace.py::test_experiment_and_literature_trace_paths_remain_separate",
    "tests/integration/phase2/test_pr2_19_citation_trace.py::test_g5_application_freeze_retains_exact_scientific_paths",
    "tests/integration/phase2/test_pr2_19_dependencies.py::test_all_blocked_matrix_rows_and_contracts_are_inventoried",
    "tests/integration/phase2/test_pr2_19_dependencies.py::test_current_subcases_reconcile_b30_without_claiming_full_rows_passed",
    "tests/integration/phase2/test_pr2_19_dependencies.py::test_omitting_blockers_cannot_promote_informational_inventory_to_acceptance",
    "tests/integration/phase2/test_pr2_19_discussion.py::test_transcript_binding_restart_and_forbidden_promotion",
    "tests/integration/phase2/test_pr2_19_discussion.py::test_g4_explicit_manual_admission_suffix",
    "tests/integration/phase2/test_pr2_19_discussion.py::test_g4_missing_root_zero_delta",
    "tests/integration/phase2/test_pr2_19_discussion.py::test_g4_open_or_unbound_zero_delta",
    "tests/integration/phase2/test_pr2_19_discussion.py::test_g4_corrupt_or_missing_cas_denies_read_replay_and_admission",
    "tests/integration/phase2/test_pr2_19_discussion.py::test_g4_mid_uow_fault_rolls_back_all_command_rows",
    "tests/integration/phase2/test_pr2_19_discussion.py::test_g4_creation_guard_maps_missing_admission_and_rolls_back",
    "tests/integration/phase2/test_pr2_19_discussion.py::test_g4_saved_admission_is_immutable",
    "tests/integration/phase2/test_pr2_19_discussion.py::test_g4_same_request_two_connection_barrier_returns_one_admission",
    "tests/integration/phase2/test_pr2_19_discussion.py::test_g4_credentials_revoked_during_observed_share_wait",
    "tests/integration/phase2/test_pr2_19_discussion.py::test_g4_saved_replay_after_application_closes_writer_role",
    "tests/integration/phase2/test_pr2_19_discussion.py::test_g4_transcript_mismatch_precedes_artifact_lookup",
    "tests/integration/phase2/test_pr2_19_governance.py::test_complete_unfavorable_basis_does_not_change_target_or_effects",
    "tests/integration/phase2/test_pr2_19_governance.py::test_exact_open_blocking_predicate",
    "tests/integration/phase2/test_pr2_19_governance.py::test_unrelated_issue_control",
    "tests/integration/phase2/test_pr2_19_governance.py::test_authority_and_closed_boundary_zero_delta",
    "tests/integration/phase2/test_pr2_19_governance.py::test_approval_current_fact_denial_retains_committed_request",
    "tests/integration/phase2/test_pr2_19_governance.py::test_approval_independence_and_authority_matrix",
    "tests/integration/phase2/test_pr2_19_governance.py::test_snapshot_observer_uses_server_settings_across_pooled_reuse",
    "tests/integration/phase2/test_pr2_19_governance.py::test_closed_approval_command_rejects_bypass_fields",
    "tests/integration/phase2/test_pr2_19_governance.py::test_wrong_purpose_target_tuple_never_creates_approval",
    "tests/integration/phase2/test_pr2_19_governance.py::test_approval_expiry_denial_retains_committed_request",
    "tests/integration/phase2/test_pr2_19_governance.py::test_complete_adverse_review_basis_cannot_be_substituted",
    "tests/integration/phase2/test_pr2_19_governance.py::test_agent_with_existing_role_and_verified_binding_cannot_approve",
    "tests/integration/phase2/test_pr2_19_governance.py::test_f5_ready_consumption_uses_current_issue_not_recommendation",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_first_use_denials_preserve_exact_predecessors",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_restart_replay_conflict_and_single_use",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_lost_commit_response_recovers_without_second_write",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_observed_competitors_have_one_concrete_effect",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_each_effect_write_and_deferred_check_rolls_back",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_freeze_withdrawal_observed_serial_orders",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_terminal_grants_cannot_create_effect",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_package_specific_current_closure",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_observed_required_wait_crosses_credential_or_grant_expiry",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_replay_needs_read_authority_after_writer_offboarding",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_role_closure_commits_across_observed_required_wait",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_ready_cannot_consume_real_prepare_permission",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_package_sealed_review_completeness_and_completed_manifest_conflict",
    "tests/integration/phase2/test_pr2_19_grant_consumption_publication.py::test_f9_real_other_manuscript_grant_cannot_authorize_saved_target",
    "tests/integration/phase2/test_pr2_19_grant_consumption_release.py::test_exact_receipt_replay_is_snapshot_only_after_write_authority_loss",
    "tests/integration/phase2/test_pr2_19_grant_consumption_release.py::test_unusable_grant_has_no_partial_receipt_or_terminalization",
    "tests/integration/phase2/test_pr2_19_grant_consumption_release.py::test_receipt_and_terminal_event_rollback_then_fresh_recovery",
    "tests/integration/phase2/test_pr2_19_grant_consumption_release.py::test_two_backends_wait_then_single_grant_winner",
    "tests/integration/phase2/test_pr2_19_grant_consumption_release.py::test_observed_inventory_wait_crosses_credential_expiry",
    "tests/integration/phase2/test_pr2_19_grant_consumption_release.py::test_expired_grant_denies_without_implicit_terminalization",
    "tests/integration/phase2/test_pr2_19_grant_consumption_release.py::test_observed_wait_crosses_grant_or_role_expiry_without_partial_effect",
    "tests/integration/phase2/test_pr2_19_integrity.py::test_cas_integrity_failure_has_zero_canonical_delta",
    "tests/integration/phase2/test_pr2_19_integrity.py::test_normal_role_immutability_and_fk_denial",
    "tests/integration/phase2/test_pr2_19_integrity.py::test_saved_hash_corruption_fails_closed",
    "tests/integration/phase2/test_pr2_19_integrity.py::test_normal_role_missing_author_fk_rejects_new_evidence",
    "tests/integration/phase2/test_pr2_19_integrity.py::test_corrupt_committed_decision_hash_denies_fresh_exact_replay",
    "tests/integration/phase2/test_pr2_19_integrity.py::test_f2b_unresolved_saved_review_denies_owning_replay",
    "tests/integration/phase2/test_pr2_19_lineage.py::test_lineage_rejection_has_zero_delta",
    "tests/integration/phase2/test_pr2_19_lineage.py::test_lineage_preserves_exact_bytes_and_blocks_new_support",
    "tests/integration/phase2/test_pr2_19_lineage.py::test_concurrent_corrections_cannot_fork_current_lineage",
    "tests/integration/phase2/test_pr2_19_lineage.py::test_current_manuscript_projection_audit_retains_frozen_material",
    "tests/integration/phase2/test_pr2_19_lineage.py::test_f1_current_downstream_facts_preserve_saved_consumptions",
    "tests/integration/phase2/test_pr2_19_lineage.py::test_f1_unrelated_source_control_does_not_block_ready_or_package",
    "tests/integration/phase2/test_pr2_19_novelty.py::test_g7_novelty_restart_denials_and_later_resolution",
    "tests/integration/phase2/test_pr2_19_novelty.py::test_g7_six_comparisons_have_exact_history_without_issue_or_gate_effect",
    "tests/integration/phase2/test_pr2_19_novelty.py::test_g7_selected_failed_and_zero_scope_is_disclosed",
    "tests/integration/phase2/test_pr2_19_package_freeze.py::test_g7_ready_preparation_consent_freeze_then_withdrawal_is_derived_stale",
    "tests/integration/phase2/test_pr2_19_package_freeze.py::test_g7_denied_freeze_has_no_partial_suffix",
    "tests/integration/phase2/test_pr2_19_package_freeze.py::test_g7_full_committed_trace_literal_hashes_and_snapshot_readers",
    "tests/integration/phase2/test_pr2_19_races.py::test_zero_issue_review_first",
    "tests/integration/phase2/test_pr2_19_races.py::test_blocking_issue_first",
    "tests/integration/phase2/test_pr2_19_races.py::test_decision_first_review_or_issue_writer",
    "tests/integration/phase2/test_pr2_19_races.py::test_upstream_impact_both_orders",
    "tests/integration/phase2/test_pr2_19_races.py::test_authority_writer_first",
    "tests/integration/phase2/test_pr2_19_races.py::test_decision_first_authority_writer",
    "tests/integration/phase2/test_pr2_19_races.py::test_cross_expiry_five_database_timestamps",
    "tests/integration/phase2/test_pr2_19_races.py::test_discussion_second_wait_rechecks_expiry",
    "tests/integration/phase2/test_pr2_19_rag_evidence.py::test_retrieval_then_owning_admission_independent_human_review_restart",
    "tests/integration/phase2/test_pr2_19_rejection.py::test_rejection_fences_new_and_precreated_requests",
    "tests/integration/phase2/test_pr2_19_rejection.py::test_reconsideration_exact_successor_retains_rejected_history",
    "tests/integration/phase2/test_pr2_19_rejection.py::test_later_rejection_requires_complete_new_coverage_but_retains_saved_history",
    "tests/integration/phase2/test_pr2_19_replay.py::test_decision_same_uuid_concurrent_changed_material_restart",
    "tests/integration/phase2/test_pr2_19_replay.py::test_decision_lost_response",
    "tests/integration/phase2/test_pr2_19_replay.py::test_historical_replay_after_staleness",
    "tests/integration/phase2/test_pr2_19_replay.py::test_three_whole_attempts_then_exact_recovery",
    "tests/integration/phase2/test_pr2_19_replay.py::test_permanent_denial_is_not_retried",
    "tests/integration/phase2/test_pr2_19_replay.py::test_discussion_concurrent_exact_uuid_and_changed_material",
    "tests/integration/phase2/test_pr2_19_replay.py::test_discussion_committed_lost_response_replays_without_extra_turn",
    "tests/integration/phase2/test_pr2_19_replay.py::test_discussion_three_fresh_attempts_exhaust_then_replay",
    "tests/integration/phase2/test_pr2_19_revision_cycle.py::test_completed_result_does_not_dispose_until_independent_command",
    "tests/integration/phase2/test_pr2_19_revision_cycle.py::test_wrong_result_cannot_resolve_original_concern",
    "tests/integration/phase2/test_pr2_19_revision_cycle.py::test_completed_experiment_requires_exact_spec_run_pair",
    "tests/integration/phase2/test_pr2_19_revision_cycle.py::test_conclusion_cycle_new_target_proceed_request_decision_grant",
    "tests/integration/phase2/test_pr2_19_revision_cycle.py::test_draft_or_unrelated_conclusion_does_not_resolve_issue",
    "tests/integration/phase2/test_pr2_19_revision_cycle.py::test_revision_successor_cannot_fork_saved_history",
    "tests/integration/phase2/test_pr2_19_search_evidence.py::test_persisted_search_result_is_not_verified_evidence",
    "tests/integration/phase2/test_pr2_19_search_evidence.py::test_persisted_resolution_exact_source_verified_evidence_conclusion_path",
    "tests/integration/phase2/test_pr2_20_catalog_plans.py::test_catalog_matches_accepted_review_constraints_and_indexes",
    "tests/integration/phase2/test_pr2_20_catalog_plans.py::test_trace_25_250_count_scaling_exact_parity_and_denials",
    "tests/integration/phase2/test_pr2_20_catalog_plans.py::test_source_lookup_hit_miss_denied_instrumentation_parity",
    "tests/integration/phase2/test_pr2_20_catalog_plans.py::test_one_blocker_among_many_favorable_reviews_is_never_filtered",
    "tests/integration/phase2/test_pr2_20_catalog_plans.py::test_b29_candidate_only_in_owned_clone_with_exact_catalog_and_snapshot",
    "tests/integration/phase2/test_pr2_20_catalog_plans.py::test_full_chain_0068_catalog_contract",
    "tests/integration/phase2/test_pr2_20_catalog_plans.py::test_historical_decision_constraints_at_owning_checkpoint",
    "tests/integration/phase2/test_pr2_20_governance_races.py::test_owning_witnessed_race_basis_rollback_and_authorized_replay",
    "tests/integration/phase2/test_pr2_20_governance_races.py::test_decision_first_review_and_issue_wait_preserves_saved_basis",
    "tests/integration/phase2/test_pr2_20_governance_races.py::test_normal_role_issue_first_wait_refreshes_all_blockers",
    "tests/integration/phase2/test_pr2_20_governance_races.py::test_post_lock_source_impact_both_commit_orders",
    "tests/integration/phase2/test_pr2_20_governance_races.py::test_h2_decision_passive_inventory_and_first_statement",
    "tests/integration/phase2/test_pr2_20_governance_races.py::test_s3_owning_both_commit_orders",
    "tests/integration/phase2/test_pr2_20_governance_races.py::test_s3_post_wait_denial_is_atomic",
    "tests/integration/phase2/test_pr2_20_governance_races.py::test_s3_package_freeze_workers_wait_and_single_effect",
    "tests/integration/phase2/test_pr2_20_governance_races.py::test_s3_superseded_manuscript_freeze_trace_race",
    "tests/integration/phase2/test_pr2_20_governance_races.py::test_s3_superseded_manuscript_post_wait_denial_is_atomic",
    "tests/integration/phase2/test_pr2_20_governance_races.py::test_s3_superseded_manuscript_mid_seal_failure_is_atomic",
    "tests/integration/phase2/test_pr2_20_governance_races.py::test_s3_freeze_consent_withdrawal_and_replay_workers",
    "tests/integration/phase2/test_pr2_20_governance_races.py::test_s3_disposition_workers_wait_and_one_terminal_event",
    "tests/integration/phase2/test_pr2_20_governance_races.py::test_s3_revision_midwrite_failure_rolls_back_complete_graph",
    "tests/integration/phase2/test_pr2_20_governance_races.py::test_s3_revision_workers_observed_wait_and_exact_replay",
    "tests/integration/phase2/test_pr2_20_governance_races.py::test_s3_approval_and_consumption_workers_single_effect",
    "tests/integration/phase2/test_pr2_20_migrations.py::test_empty_install_noop_reconnect_and_permitted_empty_round_trip",
    "tests/integration/phase2/test_pr2_20_migrations.py::test_legal_populated_0018_upgrade_preserves_identity_and_scientific_history",
    "tests/integration/phase2/test_pr2_20_migrations.py::test_populated_source_evidence_conclusion_placement_review_decision_head_noop",
    "tests/integration/phase2/test_pr2_20_migrations.py::test_interrupted_accepted_upgrade_transaction_rolls_back_without_repair",
    "tests/integration/phase2/test_pr2_20_migrations.py::test_owning_illegal_legacy_preflight_atomic_and_deterministic",
    "tests/integration/phase2/test_pr2_20_migrations.py::test_owning_populated_downgrade_refusal_without_history_loss",
    "tests/integration/phase2/test_pr2_20_migrations.py::test_accepted_populated_source_checkpoints_preserve_exact_rows",
    "tests/integration/phase2/test_pr2_20_migrations.py::test_accepted_populated_search_checkpoint_preserves_plan_execution_results",
    "tests/integration/phase2/test_pr2_20_migrations.py::test_accepted_populated_evidence_checkpoint_preserves_hash_locator_and_edges",
    "tests/integration/phase2/test_pr2_20_migrations.py::test_populated_conclusion_placement_review_and_0042_checkpoints",
    "tests/integration/phase2/test_pr2_20_migrations.py::test_populated_revision_checkpoint_hash_parity",
    "tests/integration/phase2/test_pr2_20_migrations.py::test_populated_approval_checkpoint_hash_parity",
    "tests/integration/phase2/test_pr2_20_migrations.py::test_populated_authorship_checkpoint_hash_parity",
    "tests/integration/phase2/test_pr2_20_migrations.py::test_populated_novelty_checkpoint_hash_parity",
    "tests/integration/phase2/test_pr2_20_migrations.py::test_populated_manuscript_checkpoints_hash_parity",
    "tests/integration/phase2/test_pr2_20_migrations.py::test_populated_resolution_checkpoint_hash_parity",
    "tests/integration/phase2/test_pr2_20_migrations.py::test_populated_disposition_checkpoint_hash_parity",
    "tests/integration/phase2/test_pr2_20_migrations.py::test_populated_consumption_checkpoint_hash_parity",
    "tests/integration/phase2/test_pr2_20_migrations.py::test_populated_ready_checkpoint_hash_parity",
    "tests/integration/phase2/test_pr2_20_migrations.py::test_populated_package_freeze_checkpoint_hash_parity",
    "tests/integration/phase2/test_pr2_20_novelty.py::test_bounded_first_write_replay_read_and_later_resolution",
    "tests/integration/phase2/test_pr2_20_novelty.py::test_novelty_outcomes_never_gate_approval_ready_or_package_freeze",
    "tests/integration/phase2/test_pr2_20_novelty.py::test_s3_novelty_both_commit_orders",
    "tests/integration/phase2/test_pr2_20_novelty.py::test_s3_prior_art_selection_empty_unique_ambiguous",
    "tests/integration/phase2/test_pr2_20_novelty.py::test_s3_prior_art_correction_atomic_rollback",
    "tests/integration/phase2/test_pr2_20_novelty.py::test_s3_prior_art_correction_workers_observed_wait_and_saved_history",
    "tests/integration/phase2/test_pr2_20_novelty.py::test_s3_novelty_non_gating_workers",
    "tests/integration/phase2/test_pr2_20_security.py::test_offline_candidate_corpus_and_canonical_bytes_unchanged",
    "tests/integration/phase2/test_pr2_20_security.py::test_shared_global_identity_and_cross_project_denied_disclosure",
    "tests/integration/phase2/test_pr2_20_security.py::test_credential_and_query_redaction_preserves_safe_provider_failures",
    "tests/integration/phase2/test_pr2_20_security.py::test_private_loopback_link_local_metadata_and_rebinding_destinations_denied",
    "tests/integration/phase2/test_pr2_20_security.py::test_mixed_dns_answers_are_denied_before_any_connect",
    "tests/integration/phase2/test_pr2_20_security.py::test_dns_failure_is_sanitized_not_sent",
    "tests/integration/phase2/test_pr2_20_security.py::test_rebinding_pins_socket_preserves_host_tls_and_disables_proxy_redirects",
    "tests/integration/phase2/test_pr2_20_security.py::test_untrusted_tool_text_is_not_scientific_promotion"
  ]
}
```

### Exit row 18

Recorded after verification of the owning assertions and local log digests. Raw evidence paths below identify local artifacts; they are not file links.

```json
{
  "acceptance_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "commands": [
    "uv run pytest tests/architecture/test_pr2_19_boundaries.py tests/e2e/test_phase1_concurrency_acceptance.py tests/e2e/test_phase1_cross_adapter_equivalence.py tests/e2e/test_phase1_failure_recovery.py tests/e2e/test_phase1_golden_scientific_workflow.py tests/e2e/test_phase1_historical_exactness.py tests/e2e/test_phase1_performance_shape.py tests/integration/phase2/test_approval.py tests/integration/phase2/test_b02_strategy_admission.py tests/integration/phase2/test_b02_strategy_capture.py tests/integration/phase2/test_b03_discussion_hypothesis.py tests/integration/phase2/test_b03_discussion_hypothesis_guards.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b07_revision_decisions.py tests/integration/phase2/test_b08_issue_disposition.py tests/integration/phase2/test_b17_package_freeze.py tests/integration/phase2/test_b26_finding_impact.py tests/integration/phase2/test_b27_defensive_closure_read.py tests/integration/phase2/test_m1_manuscript_reconsideration.py tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_pr2_01_source_identity.py tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_application.py tests/integration/phase2/test_pr2_04_execution_provenance.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_19_approval_atomicity.py tests/integration/phase2/test_pr2_19_atomicity.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_citation_trace.py tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_discussion.py tests/integration/phase2/test_pr2_19_governance.py tests/integration/phase2/test_pr2_19_grant_consumption_publication.py tests/integration/phase2/test_pr2_19_grant_consumption_release.py tests/integration/phase2/test_pr2_19_integrity.py tests/integration/phase2/test_pr2_19_lineage.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_19_package_freeze.py tests/integration/phase2/test_pr2_19_races.py tests/integration/phase2/test_pr2_19_rag_evidence.py tests/integration/phase2/test_pr2_19_rejection.py tests/integration/phase2/test_pr2_19_replay.py tests/integration/phase2/test_pr2_19_revision_cycle.py tests/integration/phase2/test_pr2_19_search_evidence.py tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/unit/phase2/test_pr2_08_native_strategy.py --tb=short --junitxml /var/folders/h5/hx7bbybn4j9422jrdzpkgln00000gp/T/b31-s4-5tqufo_e/owning-acceptance.xml"
  ],
  "contract_refs": [
    "docs/proposals/B31_PR2-20_Full_Exit_Hardening_Contract_DRAFT.md",
    "docs/proposals/PR2-20_Hardening_Plan_DRAFT.md"
  ],
  "corrected_term": null,
  "criterion": "No STORM/PaperQA vendor-specific Core schema",
  "dirty_diff_sha256": "8be7d685d474c9cb373d627bebe6e204e1a09e9a756145a9ed06b549edb1bb61",
  "disposition_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/scope-dispositions.json"
  ],
  "errors": 0,
  "evidence_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-18.json",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-000.txt",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-junit.xml"
  ],
  "exit_codes": [
    0
  ],
  "failed": 0,
  "finding_refs": [],
  "owning_prs": [
    "PR2-20"
  ],
  "passed": 20,
  "reason": null,
  "schema_version": 1,
  "skipped": 0,
  "status": "PASS",
  "subject_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "test_nodes": [
    "tests/architecture/test_pr2_19_boundaries.py::test_literature_source_not_evidence",
    "tests/architecture/test_pr2_19_boundaries.py::test_search_result_not_evidence",
    "tests/architecture/test_pr2_19_boundaries.py::test_citation_not_claim_support",
    "tests/architecture/test_pr2_19_boundaries.py::test_strategy_does_not_import_persistence",
    "tests/architecture/test_pr2_19_boundaries.py::test_adapter_does_not_write_db",
    "tests/architecture/test_pr2_19_boundaries.py::test_no_storm_specific_core_schema",
    "tests/architecture/test_pr2_19_boundaries.py::test_no_paperqa_specific_core_schema",
    "tests/architecture/test_pr2_19_boundaries.py::test_discussion_not_canonical_science",
    "tests/architecture/test_pr2_19_boundaries.py::test_manuscript_not_scientific_source_of_truth",
    "tests/architecture/test_pr2_19_boundaries.py::test_review_does_not_mutate_target",
    "tests/architecture/test_pr2_19_boundaries.py::test_decision_does_not_mutate_history",
    "tests/architecture/test_pr2_19_boundaries.py::test_approval_does_not_override_invalid_fact",
    "tests/architecture/test_pr2_19_boundaries.py::test_external_call_not_inside_long_db_transaction",
    "tests/architecture/test_pr2_19_boundaries.py::test_b30_has_no_production_fault_hook_or_generic_scenario_executor",
    "tests/architecture/test_pr2_19_boundaries.py::test_s2_keeps_suffix_availability_distinct_from_full_gate",
    "tests/architecture/test_pr2_19_boundaries.py::test_s2_saved_publication_and_package_readers_use_one_snapshot",
    "tests/architecture/test_pr2_19_boundaries.py::test_s3_candidate_admission_retains_single_application_boundary",
    "tests/architecture/test_pr2_19_boundaries.py::test_s3_write_inventories_match_independent_e2e_protocol_expectations"
  ]
}
```

### Exit row 19

Recorded after verification of the owning assertions and local log digests. Raw evidence paths below identify local artifacts; they are not file links.

```json
{
  "acceptance_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "commands": [
    "uv run pytest tests/architecture/test_pr2_19_boundaries.py tests/e2e/test_phase1_concurrency_acceptance.py tests/e2e/test_phase1_cross_adapter_equivalence.py tests/e2e/test_phase1_failure_recovery.py tests/e2e/test_phase1_golden_scientific_workflow.py tests/e2e/test_phase1_historical_exactness.py tests/e2e/test_phase1_performance_shape.py tests/integration/phase2/test_approval.py tests/integration/phase2/test_b02_strategy_admission.py tests/integration/phase2/test_b02_strategy_capture.py tests/integration/phase2/test_b03_discussion_hypothesis.py tests/integration/phase2/test_b03_discussion_hypothesis_guards.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b07_revision_decisions.py tests/integration/phase2/test_b08_issue_disposition.py tests/integration/phase2/test_b17_package_freeze.py tests/integration/phase2/test_b26_finding_impact.py tests/integration/phase2/test_b27_defensive_closure_read.py tests/integration/phase2/test_m1_manuscript_reconsideration.py tests/integration/phase2/test_m1_manuscript_revision.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_pr2_01_source_identity.py tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_application.py tests/integration/phase2/test_pr2_04_execution_provenance.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_19_approval_atomicity.py tests/integration/phase2/test_pr2_19_atomicity.py tests/integration/phase2/test_pr2_19_candidates.py tests/integration/phase2/test_pr2_19_citation_trace.py tests/integration/phase2/test_pr2_19_dependencies.py tests/integration/phase2/test_pr2_19_discussion.py tests/integration/phase2/test_pr2_19_governance.py tests/integration/phase2/test_pr2_19_grant_consumption_publication.py tests/integration/phase2/test_pr2_19_grant_consumption_release.py tests/integration/phase2/test_pr2_19_integrity.py tests/integration/phase2/test_pr2_19_lineage.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_19_package_freeze.py tests/integration/phase2/test_pr2_19_races.py tests/integration/phase2/test_pr2_19_rag_evidence.py tests/integration/phase2/test_pr2_19_rejection.py tests/integration/phase2/test_pr2_19_replay.py tests/integration/phase2/test_pr2_19_revision_cycle.py tests/integration/phase2/test_pr2_19_search_evidence.py tests/unit/phase2/test_pr2_07_scientific_rag_boundary.py tests/unit/phase2/test_pr2_08_native_strategy.py --tb=short --junitxml /var/folders/h5/hx7bbybn4j9422jrdzpkgln00000gp/T/b31-s4-5tqufo_e/owning-acceptance.xml"
  ],
  "contract_refs": [
    "docs/proposals/B31_PR2-20_Full_Exit_Hardening_Contract_DRAFT.md",
    "docs/proposals/PR2-20_Hardening_Plan_DRAFT.md"
  ],
  "corrected_term": null,
  "criterion": "Phase 1 Exit tests continue",
  "dirty_diff_sha256": "8be7d685d474c9cb373d627bebe6e204e1a09e9a756145a9ed06b549edb1bb61",
  "disposition_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/scope-dispositions.json"
  ],
  "errors": 0,
  "evidence_refs": [
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-19.json",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-000.txt",
    "pr_evidence/pr2-20/10ea37ab50af126f0ce02dcf7f48b957f5035f0bde88869f9cbb73c94deccc05/owning-acceptance-junit.xml"
  ],
  "exit_codes": [
    0
  ],
  "failed": 0,
  "finding_refs": [],
  "owning_prs": [
    "Phase 1 frozen baseline"
  ],
  "passed": 20,
  "reason": null,
  "schema_version": 1,
  "skipped": 0,
  "status": "PASS",
  "subject_revision": "1278a5eecbe5357d9d440a2d0da05541c67ca028",
  "test_nodes": [
    "tests/e2e/test_phase1_concurrency_acceptance.py::test_representative_commands_rollback_and_retry_without_partial_rows",
    "tests/e2e/test_phase1_concurrency_acceptance.py::test_concurrent_version_revise_has_one_winner_and_no_partial_history",
    "tests/e2e/test_phase1_concurrency_acceptance.py::test_concurrent_freeze_and_audit_transition_have_stable_winner_loser",
    "tests/e2e/test_phase1_concurrency_acceptance.py::test_concurrent_run_transition_has_one_winner_and_no_partial_overwrite",
    "tests/e2e/test_phase1_concurrency_acceptance.py::test_claim_evidence_link_and_freeze_conflict_has_valid_final_state",
    "tests/e2e/test_phase1_cross_adapter_equivalence.py::test_adapter_gsas_01_projection_matches_direct_application",
    "tests/e2e/test_phase1_cross_adapter_equivalence.py::test_adapter_order_independence_uses_independent_fresh_fixtures",
    "tests/e2e/test_phase1_cross_adapter_equivalence.py::test_projection_integrity_preserves_observed_semantic_differences",
    "tests/e2e/test_phase1_failure_recovery.py::test_http_recovery_sequence_has_no_poisoned_context_or_partial_write",
    "tests/e2e/test_phase1_failure_recovery.py::test_cli_recovery_sequence_has_no_stale_request_id_or_context",
    "tests/e2e/test_phase1_failure_recovery.py::test_every_stable_researchbase_error_has_explicit_http_and_cli_mapping",
    "tests/e2e/test_phase1_golden_scientific_workflow.py::test_gsas_01_direct_application_is_complete_and_non_trivial",
    "tests/e2e/test_phase1_golden_scientific_workflow.py::test_gsas_01_repeated_independent_fresh_postgresql_fixtures_match",
    "tests/e2e/test_phase1_historical_exactness.py::test_historical_advancement_preserves_original_exact_ids_hashes_and_closure",
    "tests/e2e/test_phase1_historical_exactness.py::test_closure_negative_cases_are_deterministic_and_positive_closure_has_no_violations",
    "tests/e2e/test_phase1_historical_exactness.py::test_claim_closure_reports_a_real_broken_descendant_deterministically",
    "tests/e2e/test_phase1_historical_exactness.py::test_governance_validity_precedence_dismissal_and_correction_are_non_mutating",
    "tests/e2e/test_phase1_performance_shape.py::test_application_http_cli_queries_are_read_only_and_formatting_adds_no_selects",
    "tests/e2e/test_phase1_performance_shape.py::test_scaled_queries_are_stage_bounded_and_preserve_trace_paths"
  ]
}
```
