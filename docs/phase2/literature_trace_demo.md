Subject `0a553154faa981221242ce62d743f4fe37f24d92`; dirty diff `a0b97f8848e5fa80b7b37a4cd0bcead45a2a63d3fa12b1d6bd115c44ac7b343b`.

Machine evidence: [subject](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/subject.json). This is engineering evidence. Phase 2 exit is **BLOCKED**; owner acceptance is separate.

The implemented literature trace starts with a frozen search plan and LiteratureSearchExecution query/result provenance. A persisted hit is resolved through the owning Application command to an exact frozen SourceVersion. Document ArtifactVersion bytes, hash and typed locator are checked before LiteratureEvidence admission; independent human review and sealed support snapshots preserve exact hashes and ordinals. Search hits and RAG candidates supply no scientific support by themselves. FakeScientificRAGCapability is the offline candidate boundary; B28 real PaperQA2 is DEFERRED.

ScientificConclusion freeze closes its typed Claim and literature inputs. A manuscript places exact frozen Claim/conclusion versions, then freezes its placement set. Citation-only placement creates no Claim support. The downstream publication path enters internal review, records readiness Decision and Approval, consumes its grant at READY, prepares the authorship-bound package, records required consents, and consumes a separate preparation grant to create the FROZEN PreparedSubmissionVersion. Retraction/correction and finding/impact projections can make downstream material stale while preserving saved hashes, consumptions and frozen history. Fabricated or unresolved citations fail closed. These are composed owning scenarios; a lookup alone does not prove the full exit.

Owning trace evidence (commands, nodes and counts are in each record):

- [SourceVersion lineage/freeze](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-01.json): PASS; owning assertions verified
- [LiteratureSearchPlan/Run provenance](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-02.json): PASS; owning assertions verified
- [LiteratureEvidence source+locator trace](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-03.json): PASS; owning assertions verified
- [ScientificConclusion support-set freeze](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-07.json): PASS; owning assertions verified
- [ScientificConclusion Frozen Provenance Closure](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-08.json): PASS; owning assertions verified
- [ManuscriptVersion scientific placement](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-09.json): PASS; owning assertions verified
- [Citation ≠ ClaimSupport](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-10.json): PASS; owning assertions verified
- [SubmissionVersion package freeze](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-13.json): PASS; owning assertions verified
- [Retracted-source impact propagation](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-14.json): PASS; owning assertions verified
- [Hallucinated citation rejection](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-15.json): PASS; owning assertions verified
