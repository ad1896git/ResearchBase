Subject `5a78b9f7b96750de2b26a081551bb0bd88bfa91e`; dirty diff `2263d6f0d9ce6f948b975cd4bfe2ceaa2032ee2f2a87411e5c3b33b859c6cbb2`.

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

Owner-accepted known gaps and scope dispositions:

- Dedicated Linux benchmark host not tested for now, owner 2026-10-20: Row 17 benchmark-host part only DEFERRED; revisit before Phase 3 performance claims. Local macOS timings are informational, not a substitute: docs/proposals/Owner_Decision_Linux_Benchmark_Host_2026-10-20.md.
- B28 real PaperQA2 DEFERRED, owner 2026-10-19: docs/proposals/B28_PaperQA2_Intake_Assessment_DRAFT.md.
- AQ-S3-08, owner 2026-10-20: positive G2 AGENT admission test pending; no Application path creates a bound AGENT. Never forge the binding: docs/proposals/B30S3_Architecture_Questions_2026-10-20.md.
- D-B31-03: B20 NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE (NO_CLOSE_PRIOR_ART), B23 novelty review/revision, and MANUSCRIPT_CHANGE remain Phase 2 exit non-goals: docs/proposals/B31_PR2-20_Full_Exit_Hardening_Contract_DRAFT.md.

Focused commands, exact counts and actual host details are in [verification](pr2_20_verification.md). Unrun, skipped, failed and blocked results stay distinct. Dedicated Linux host timing/attestation is owner-accepted DEFERRED for the benchmark-host part of Row 17 only; local macOS results remain informational and are not a substitute. Reference/provider revision, license/notice/terms and dated advisory review remain unresolved in the adapter inventory. No independent review or loop full-suite acceptance is inferred from these focused runs.

**STOP; wait for explicit Phase 3 GO.**

Owner decisions needed

- Reference/provider intake: resolve revision, license/notice/terms and dated advisory review before enabling providers (adapter inventory).
- Attach independent review and loop full-suite evidence before owner exit decision.
