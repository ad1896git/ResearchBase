Subject `5a78b9f7b96750de2b26a081551bb0bd88bfa91e`; dirty diff `2263d6f0d9ce6f948b975cd4bfe2ceaa2032ee2f2a87411e5c3b33b859c6cbb2`.

Recorded evidence: [subject](pr2_20_verification.md#subject). This is engineering evidence. Phase 2 exit is **PASS**; owner acceptance is separate.

The implemented literature trace starts with a frozen search plan and LiteratureSearchExecution query/result provenance. A persisted hit is resolved through the owning Application command to an exact frozen SourceVersion. Document ArtifactVersion bytes, hash and typed locator are checked before LiteratureEvidence admission; independent human review and sealed support snapshots preserve exact hashes and ordinals. Search hits and RAG candidates supply no scientific support by themselves. FakeScientificRAGCapability is the offline candidate boundary; B28 real PaperQA2 is DEFERRED.

ScientificConclusion freeze closes its typed Claim and literature inputs. A manuscript places exact frozen Claim/conclusion versions, then freezes its placement set. Citation-only placement creates no Claim support. The downstream publication path enters internal review, records readiness Decision and Approval, consumes its grant at READY, prepares the authorship-bound package, records required consents, and consumes a separate preparation grant to create the FROZEN PreparedSubmissionVersion. Retraction/correction and finding/impact projections can make downstream material stale while preserving saved hashes, consumptions and frozen history. Fabricated or unresolved citations fail closed. These are composed owning scenarios; a lookup alone does not prove the full exit.

Owning trace evidence (commands, nodes and counts are in each record):

- [SourceVersion lineage/freeze](pr2_20_verification.md#exit-row-2): PASS; owning assertions verified
- [LiteratureSearchPlan/Run provenance](pr2_20_verification.md#exit-row-3): PASS; owning assertions verified
- [LiteratureEvidence source+locator trace](pr2_20_verification.md#exit-row-4): PASS; owning assertions verified
- [ScientificConclusion support-set freeze](pr2_20_verification.md#exit-row-8): PASS; owning assertions verified
- [ScientificConclusion Frozen Provenance Closure](pr2_20_verification.md#exit-row-9): PASS; owning assertions verified
- [ManuscriptVersion scientific placement](pr2_20_verification.md#exit-row-10): PASS; owning assertions verified
- [Citation ≠ ClaimSupport](pr2_20_verification.md#exit-row-11): PASS; owning assertions verified
- [SubmissionVersion package freeze](pr2_20_verification.md#exit-row-14): PASS; owning assertions verified
- [Retracted-source impact propagation](pr2_20_verification.md#exit-row-15): PASS; owning assertions verified
- [Hallucinated citation rejection](pr2_20_verification.md#exit-row-16): PASS; owning assertions verified
