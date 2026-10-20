Subject `0a553154faa981221242ce62d743f4fe37f24d92`; dirty diff `a0b97f8848e5fa80b7b37a4cd0bcead45a2a63d3fa12b1d6bd115c44ac7b343b`.

Machine evidence: [subject](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/subject.json). This is engineering evidence. Phase 2 exit is **BLOCKED**; owner acceptance is separate.

**Exit BLOCKED.** Computed by validate_exit; this is not owner acceptance of Phase 2. The 19 literal criteria retain their frozen order. The Scientific RAG boundary is tested with the fake in the candidate/rejection records; it does not replace Row 6.

| Literal exit criterion | Status | Reason | Evidence |
| --- | --- | --- | --- |
| LiteratureSource identity resolution | PASS | Owning assertions verified | [record](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-00.json) |
| SourceVersion lineage/freeze | PASS | Owning assertions verified | [record](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-01.json) |
| LiteratureSearchPlan/Run provenance | PASS | Owning assertions verified | [record](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-02.json) |
| LiteratureEvidence source+locator trace | PASS | Owning assertions verified | [record](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-03.json) |
| STORM-like Native ResearchStrategy | BLOCKED | AQ-S3-08: positive G2 AGENT admission pending; no Application path creates a bound AGENT (docs/proposals/B30S3_Architecture_Questions_2026-10-20.md; owner 2026-10-20 known gap) | [record](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-04.json) |
| PaperQA2 Adapter | DEFERRED | Owner-approved B28 deferral: docs/proposals/B28_PaperQA2_Intake_Assessment_DRAFT.md | [record](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-05.json) |
| Academic Discussion explicit promotion | PASS | Owning assertions verified | [record](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-06.json) |
| ScientificConclusion support-set freeze | PASS | Owning assertions verified | [record](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-07.json) |
| ScientificConclusion Frozen Provenance Closure | PASS | Owning assertions verified | [record](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-08.json) |
| ManuscriptVersion scientific placement | PASS | Owning assertions verified | [record](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-09.json) |
| Citation ≠ ClaimSupport | PASS | Owning assertions verified | [record](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-10.json) |
| Internal Review → Issue → Decision → Revision | PASS | Owning assertions verified | [record](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-11.json) |
| Basic Approval frozen target / blocking gate | PASS | Owning assertions verified | [record](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-12.json) |
| SubmissionVersion package freeze | PASS | Owning assertions verified | [record](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-13.json) |
| Retracted-source impact propagation | PASS | Owning assertions verified | [record](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-14.json) |
| Hallucinated citation rejection | PASS | Owning assertions verified | [record](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-15.json) |
| PostgreSQL migrations/integration | BLOCKED | Dedicated Linux benchmark host, reserved CPU/RAM/storage/no-competing-job attestation and declared PostgreSQL settings unavailable; local macOS results only, owner disposition pending | [record](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-16.json) |
| No STORM/PaperQA vendor-specific Core schema | PASS | Owning assertions verified | [record](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-17.json) |
| Phase 1 Exit tests continue | PASS | Owning assertions verified | [record](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-18.json) |

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

- B28 real PaperQA2 DEFERRED, owner 2026-10-19: docs/proposals/B28_PaperQA2_Intake_Assessment_DRAFT.md.
- AQ-S3-08, owner 2026-10-20: positive G2 AGENT admission test pending; no Application path creates a bound AGENT. Never forge the binding: docs/proposals/B30S3_Architecture_Questions_2026-10-20.md.
- D-B31-03: B20 NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE (NO_CLOSE_PRIOR_ART), B23 novelty review/revision, and MANUSCRIPT_CHANGE remain Phase 2 exit non-goals: docs/proposals/B31_PR2-20_Full_Exit_Hardening_Contract_DRAFT.md.

Focused commands, exact counts and actual host details are in [verification](pr2_20_verification.md). Unrun, skipped, failed and blocked results stay distinct. Dedicated Linux host timing/attestation remains BLOCKED pending owner disposition; local macOS results are informational. Reference/provider revision, license/notice/terms and dated advisory review remain unresolved in the adapter inventory. No independent review or loop full-suite acceptance is inferred from these focused runs.

**STOP; wait for explicit Phase 3 GO.**

Owner decisions needed

- STORM-like Native ResearchStrategy: AQ-S3-08: positive G2 AGENT admission pending; no Application path creates a bound AGENT (docs/proposals/B30S3_Architecture_Questions_2026-10-20.md; owner 2026-10-20 known gap)
- PostgreSQL migrations/integration: Dedicated Linux benchmark host, reserved CPU/RAM/storage/no-competing-job attestation and declared PostgreSQL settings unavailable; local macOS results only, owner disposition pending
- Reference/provider intake: resolve revision, license/notice/terms and dated advisory review before enabling providers (adapter inventory).
- Attach independent review and loop full-suite evidence before owner exit decision.
