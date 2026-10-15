Subject `1ae0036344c26057b1e70c7bbd3daf4e5d3b2d51`; dirty diff `f01f97fc03bf5cff9f3bfccfce2d46e7d2ef6121b0e820b363c8f6f8d336e47e`.

Machine evidence: [subject](../../pr_evidence/pr2-20/3ea9a7ac2f6d2a7f04ad79b907e344b24661a6cfc466be11e02dee1f3725836d/subject.json). This is engineering evidence. Phase 2 exit is **BLOCKED**; owner acceptance is separate.

**Exit BLOCKED.** First slice authorization: owner user instruction, 2026-10-14 approval. Inherited PR2-15/16 exact approval subjects/dispositions have not been attached. Code presence of later prerequisites is inventoried, not their admission to this slice.

| Literal exit criterion | Status | Reason |
| --- | --- | --- |
| LiteratureSource identity resolution | BLOCKED | Owning acceptance and owner dispositions not attached |
| SourceVersion lineage/freeze | BLOCKED | Owning acceptance and owner dispositions not attached |
| LiteratureSearchPlan/Run provenance | BLOCKED | Owning acceptance and owner dispositions not attached |
| LiteratureEvidence source+locator trace | BLOCKED | Owning acceptance and owner dispositions not attached |
| STORM-like Native ResearchStrategy | BLOCKED | Owning acceptance and owner dispositions not attached |
| PaperQA2 Adapter | BLOCKED | Owning acceptance and owner dispositions not attached |
| Academic Discussion explicit promotion | BLOCKED | Owning acceptance and owner dispositions not attached |
| ScientificConclusion support-set freeze | BLOCKED | Owning acceptance and owner dispositions not attached |
| ScientificConclusion Frozen Provenance Closure | BLOCKED | Owning acceptance and owner dispositions not attached |
| ManuscriptVersion scientific placement | BLOCKED | Owning acceptance and owner dispositions not attached |
| Citation ≠ ClaimSupport | BLOCKED | Owning acceptance and owner dispositions not attached |
| Internal Review → Issue → Decision → Revision | BLOCKED | Owning acceptance and owner dispositions not attached |
| Basic Approval frozen target / blocking gate | BLOCKED | Owning acceptance and owner dispositions not attached |
| SubmissionVersion package freeze | BLOCKED | Owning acceptance and owner dispositions not attached |
| Retracted-source impact propagation | BLOCKED | Owning acceptance and owner dispositions not attached |
| Hallucinated citation rejection | BLOCKED | Owning acceptance and owner dispositions not attached |
| PostgreSQL migrations/integration | BLOCKED | Owning acceptance and owner dispositions not attached |
| No STORM/PaperQA vendor-specific Core schema | BLOCKED | Owning acceptance and owner dispositions not attached |
| Phase 1 Exit tests continue | BLOCKED | Owning acceptance and owner dispositions not attached |

| Architecture requirement | Concrete node | Disposition |
| --- | --- | --- |
| test_literature_source_not_evidence | `tests/architecture/test_pr2_19_boundaries.py::test_literature_source_not_evidence` | See exact run evidence; mapping is not acceptance |
| test_search_result_not_evidence | `tests/architecture/test_pr2_19_boundaries.py::test_search_result_not_evidence` | See exact run evidence; mapping is not acceptance |
| test_citation_not_claim_support | `tests/architecture/test_pr2_19_boundaries.py::test_citation_not_claim_support` | See exact run evidence; mapping is not acceptance |
| test_strategy_does_not_import_persistence | `tests/architecture/test_pr2_19_boundaries.py::test_strategy_does_not_import_persistence` | See exact run evidence; mapping is not acceptance |
| test_adapter_does_not_write_db | `tests/architecture/test_pr2_19_boundaries.py::test_adapter_does_not_write_db` | See exact run evidence; mapping is not acceptance |
| test_no_storm_specific_core_schema | `tests/architecture/test_pr2_19_boundaries.py::test_no_storm_specific_core_schema` | See exact run evidence; mapping is not acceptance |
| test_no_paperqa_specific_core_schema | `tests/architecture/test_pr2_19_boundaries.py::test_no_paperqa_specific_core_schema` | See exact run evidence; mapping is not acceptance |
| test_discussion_not_canonical_science | `tests/architecture/test_pr2_19_boundaries.py::test_discussion_not_canonical_science` | See exact run evidence; mapping is not acceptance |
| test_manuscript_not_scientific_source_of_truth | `tests/architecture/test_pr2_19_boundaries.py::test_manuscript_not_scientific_source_of_truth` | See exact run evidence; mapping is not acceptance |
| test_review_does_not_mutate_target | `tests/architecture/test_pr2_19_boundaries.py::test_review_does_not_mutate_target` | See exact run evidence; mapping is not acceptance |
| test_decision_does_not_mutate_history | `tests/architecture/test_pr2_19_boundaries.py::test_decision_does_not_mutate_history` | See exact run evidence; mapping is not acceptance |
| test_approval_does_not_override_invalid_fact | `tests/architecture/test_pr2_19_boundaries.py::test_approval_does_not_override_invalid_fact` | BLOCKED: runtime Approval admission absent |
| test_external_call_not_inside_long_db_transaction | `tests/architecture/test_pr2_19_boundaries.py::test_external_call_not_inside_long_db_transaction` | See exact run evidence; mapping is not acceptance |

Focused command/count evidence is in [verification](pr2_20_verification.md). Unrun, skipped, failed and blocked results remain distinct. No full suite was run by the implementation agent; loop evidence must be attached separately. Benchmark on the specified dedicated Linux host remains BLOCKED if unavailable; local small timing is informational. Open P1 transport finding, missing real PaperQA2, missing acceptance subjects and owner dispositions prevent gate success. Independent review is recorded in the verification document.

Substitution: the existing disposable PR212 database prefix is reused by the PR220 helper. All named fixtures resolve as written. Approval inventory uses the existing `test_approval.py` name. The 50 pinned error rows are retained; seven existing Approval mappings are appended in source-inventory tests.

**STOP; wait for explicit Phase 3 GO.**
