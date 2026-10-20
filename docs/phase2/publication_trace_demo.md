Subject `0a553154faa981221242ce62d743f4fe37f24d92`; dirty diff `a0b97f8848e5fa80b7b37a4cd0bcead45a2a63d3fa12b1d6bd115c44ac7b343b`.

Machine evidence: [subject](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/subject.json). This is engineering evidence. Phase 2 exit is **BLOCKED**; owner acceptance is separate.

The implemented publication trace retains exact frozen Claim/conclusion IDs and hashes, experimental and literature support paths, and exact figure/document ArtifactVersion references. Manuscript freeze seals the placement set. Internal review records issues without rewriting that scientific material. A completed RevisionAction does not dispose an issue: independent re-review and the separate disposition command preserve concern history. M1 manuscript revision and reconsideration owning tests are included in the evidence inventory.

After internal-review entry, the readiness Decision and Approval bind the frozen manuscript and complete review basis. transition_publication_ready consumes the readiness grant exactly once and records READY. Preparation binds the exact manuscript and AuthorshipSnapshot; AuthorConsent records bind the package. A separate PREPARE_SUBMISSION Decision/Approval grant and checked review set authorize freeze_prepared_submission, which validates the manifest and consents and creates the FROZEN PreparedSubmissionVersion atomically. Restart/replay returns the saved receipt through read authority; withdrawal and later invalidity remain new history or derived projections. B24 novelty outcomes never gate Approval, READY or package freeze. No external submission/send is asserted.

Owning lifecycle evidence:

- [ManuscriptVersion scientific placement](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-09.json): PASS; owning assertions verified
- [Internal Review → Issue → Decision → Revision](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-11.json): PASS; owning assertions verified
- [Basic Approval frozen target / blocking gate](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-12.json): PASS; owning assertions verified
- [SubmissionVersion package freeze](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-13.json): PASS; owning assertions verified
- [Retracted-source impact propagation](../../pr_evidence/pr2-20/c408be640b3408ff0b989dd672c5d6d6c225081b6a9a601b57a4c54b5cf17e2c/exit-14.json): PASS; owning assertions verified
