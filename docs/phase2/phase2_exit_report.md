Subject `1278a5eecbe5357d9d440a2d0da05541c67ca028`; dirty diff `8be7d685d474c9cb373d627bebe6e204e1a09e9a756145a9ed06b549edb1bb61`.

Recorded evidence: [subject](pr2_20_verification.md#subject). This is engineering evidence. Phase 2 exit is **PASS**; owner acceptance is separate.

**Exit PASS.** Computed by validate_exit; this is not owner acceptance of Phase 2. The 19 literal criteria retain their frozen order. The Scientific RAG boundary is tested with the fake in the candidate/rejection records; it does not replace Row 6.

| Literal exit criterion | Status | Reason | Evidence |
| --- | --- | --- | --- |
| LiteratureSource identity resolution | PASS | Owning assertions verified | [record](pr2_20_verification.md#exit-row-1) |
| SourceVersion lineage/freeze | PASS | Owning assertions verified | [record](pr2_20_verification.md#exit-row-2) |
| LiteratureSearchPlan/Run provenance | PASS | Owning assertions verified | [record](pr2_20_verification.md#exit-row-3) |
| LiteratureEvidence source+locator trace | PASS | Owning assertions verified | [record](pr2_20_verification.md#exit-row-4) |
| STORM-like Native ResearchStrategy | DEFERRED | AQ-S3-08: positive G2 AGENT admission pending; owner-accepted known gap 2026-10-20; all other owning assertions verified | [record](pr2_20_verification.md#exit-row-5) |
| PaperQA2 Adapter | DEFERRED | Owner-approved B28 deferral: docs/proposals/B28_PaperQA2_Intake_Assessment_DRAFT.md | [record](pr2_20_verification.md#exit-row-6) |
| Academic Discussion explicit promotion | PASS | Owning assertions verified | [record](pr2_20_verification.md#exit-row-7) |
| ScientificConclusion support-set freeze | PASS | Owning assertions verified | [record](pr2_20_verification.md#exit-row-8) |
| ScientificConclusion Frozen Provenance Closure | PASS | Owning assertions verified | [record](pr2_20_verification.md#exit-row-9) |
| ManuscriptVersion scientific placement | PASS | Owning assertions verified | [record](pr2_20_verification.md#exit-row-10) |
| Citation ≠ ClaimSupport | PASS | Owning assertions verified | [record](pr2_20_verification.md#exit-row-11) |
| Internal Review → Issue → Decision → Revision | PASS | Owning assertions verified | [record](pr2_20_verification.md#exit-row-12) |
| Basic Approval frozen target / blocking gate | PASS | Owning assertions verified | [record](pr2_20_verification.md#exit-row-13) |
| SubmissionVersion package freeze | PASS | Owning assertions verified | [record](pr2_20_verification.md#exit-row-14) |
| Retracted-source impact propagation | PASS | Owning assertions verified | [record](pr2_20_verification.md#exit-row-15) |
| Hallucinated citation rejection | PASS | Owning assertions verified | [record](pr2_20_verification.md#exit-row-16) |
| PostgreSQL migrations/integration | DEFERRED | Dedicated Linux benchmark host not tested for now; owner-accepted deferral 2026-10-20 for benchmark-host part only; local macOS timings informational, not a substitute; all other owning assertions verified | [record](pr2_20_verification.md#exit-row-17) |
| No STORM/PaperQA vendor-specific Core schema | PASS | Owning assertions verified | [record](pr2_20_verification.md#exit-row-18) |
| Phase 1 Exit tests continue | PASS | Owning assertions verified | [record](pr2_20_verification.md#exit-row-19) |

| Architecture requirement | Concrete node | Disposition |
| --- | --- | --- |
| test_literature_source_not_evidence | `tests/architecture/test_pr2_19_boundaries.py::test_literature_source_not_evidence` | See owning Row 18 evidence |
| test_search_result_not_evidence | `tests/architecture/test_pr2_19_boundaries.py::test_search_result_not_evidence` | See owning Row 18 evidence |
| test_citation_not_claim_support | `tests/architecture/test_pr2_19_boundaries.py::test_citation_not_claim_support` | See owning Row 18 evidence |
| test_strategy_does_not_import_persistence | `tests/architecture/test_pr2_19_boundaries.py::test_strategy_does_not_import_persistence` | See owning Row 18 evidence |
| test_adapter_does_not_write_db | `tests/architecture/test_pr2_19_boundaries.py::test_adapter_does_not_write_db` | See owning Row 18 evidence |
| test_no_storm_specific_core_schema | `tests/architecture/test_pr2_19_boundaries.py::test_no_storm_specific_core_schema` | See owning Row 18 evidence |
| test_no_paperqa_specific_core_schema | `tests/architecture/test_pr2_19_boundaries.py::test_no_paperqa_specific_core_schema` | See owning Row 18 evidence |
| test_discussion_not_canonical_science | `tests/architecture/test_pr2_19_boundaries.py::test_discussion_not_canonical_science` | See owning Row 18 evidence |
| test_manuscript_not_scientific_source_of_truth | `tests/architecture/test_pr2_19_boundaries.py::test_manuscript_not_scientific_source_of_truth` | See owning Row 18 evidence |
| test_review_does_not_mutate_target | `tests/architecture/test_pr2_19_boundaries.py::test_review_does_not_mutate_target` | See owning Row 18 evidence |
| test_decision_does_not_mutate_history | `tests/architecture/test_pr2_19_boundaries.py::test_decision_does_not_mutate_history` | See owning Row 18 evidence |
| test_approval_does_not_override_invalid_fact | `tests/architecture/test_pr2_19_boundaries.py::test_approval_does_not_override_invalid_fact` | See owning Row 18 evidence |
| test_external_call_not_inside_long_db_transaction | `tests/architecture/test_pr2_19_boundaries.py::test_external_call_not_inside_long_db_transaction` | See owning Row 18 evidence |

Delivered B20/B23 first slices:

Owner-approved 2026-10-19 first slices delivered: B20 `NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE` with a typed `ScreeningBasis`, sealed probe/result children and exact historical readback ([B20 contract](../proposals/B20_Screening_Negative_Probe_Contract_DRAFT.md), migration `0070_b20_screening_basis`); B23 exact NoveltyAssessment reviews, issue-only `NOVELTY_REASSESSMENT` actions referencing precommitted direct replacements, and independent re-review links that leave Issues OPEN ([B23 contract](../proposals/B23_Novelty_Review_Revision_Contract_DRAFT.md), migration `0071_b23_novelty_review`). Implementation: `src/researchbase/domain/novelty.py`, `src/researchbase/application/internal_review.py`, `src/researchbase/application/revision_action.py`; migrations are under `migrations/versions/`.

Owner-accepted known gaps and scope dispositions:

- Dedicated Linux benchmark host not tested for now, owner 2026-10-20: Row 17 benchmark-host part only DEFERRED; revisit before Phase 3 performance claims. Local macOS timings are informational, not a substitute: docs/proposals/Owner_Decision_Linux_Benchmark_Host_2026-10-20.md.
- B28 real PaperQA2 DEFERRED, owner 2026-10-19: docs/proposals/B28_PaperQA2_Intake_Assessment_DRAFT.md.
- AQ-S3-08, owner 2026-10-20: positive G2 AGENT admission test pending; no Application path creates a bound AGENT. Never forge the binding: docs/proposals/B30S3_Architecture_Questions_2026-10-20.md.
- B20/B23 remaining scope exclusions (contracts §2 and §12.5): prospective preregistration/external search exhaustiveness, automatic query planning/provider execution, programmable criteria, failed/adverse-branch replacement, universal priority claims, source-merge deduplication, automatic selection across independent comparison roots and automatic impact propagation; novelty-target Decisions, NO_CHANGE, Issue disposition/blocking-concern resolution, direct PriorArtRelation/SearchCoverage review targets, and assessment creation inside review/revision commands. MANUSCRIPT_CHANGE RevisionAction as a novelty result remains a non-goal; M1 already supports MANUSCRIPT_CHANGE for manuscript concerns. No novelty-driven approval, READY/package gate or generic Agent runtime.

Focused commands, exact counts and actual host details are in [verification](pr2_20_verification.md). Unrun, skipped, failed and blocked results stay distinct. Dedicated Linux host timing/attestation is owner-accepted DEFERRED for the benchmark-host part of Row 17 only; local macOS results remain informational and are not a substitute. Reference/provider revision, license/notice/terms and dated advisory review remain unresolved in the adapter inventory.

[Independent director review and integration full check](phase2_exit_review_2026-10-20.md): lane72 head `64b5f1e`, 2026-10-20, **12,523 passed, 66 skipped, 0 failed (exit 0)**; pyright 0 errors, ruff clean, git diff --check clean, one Alembic head 0075. These are the director's recorded integration results, separate from the focused runs below. The review identifies R1–R3 for correction; owner exit acceptance and Phase 3 GO remain separate.

**STOP; wait for explicit Phase 3 GO.**

Owner decisions needed

- Reference/provider intake: resolve revision, license/notice/terms and dated advisory review before enabling providers (adapter inventory).
