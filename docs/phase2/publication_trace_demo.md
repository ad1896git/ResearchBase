Subject `1278a5eecbe5357d9d440a2d0da05541c67ca028`; dirty diff `8be7d685d474c9cb373d627bebe6e204e1a09e9a756145a9ed06b549edb1bb61`.

Recorded evidence: [subject](pr2_20_verification.md#subject). This is engineering evidence. Phase 2 exit is **PASS**; owner acceptance is separate.

The implemented publication trace retains exact frozen Claim/conclusion IDs and hashes, experimental and literature support paths, and exact figure/document ArtifactVersion references. Manuscript freeze seals the placement set. Internal review records issues without rewriting that scientific material. A completed RevisionAction does not dispose an issue: independent re-review and the separate disposition command preserve concern history. M1 manuscript revision and reconsideration owning tests are included in the evidence inventory.

After internal-review entry, the readiness Decision and Approval bind the frozen manuscript and complete review basis. transition_publication_ready consumes the readiness grant exactly once and records READY. Preparation binds the exact manuscript and AuthorshipSnapshot; AuthorConsent records bind the package. A separate PREPARE_SUBMISSION Decision/Approval grant and checked review set authorize freeze_prepared_submission, which validates the manifest and consents and creates the FROZEN PreparedSubmissionVersion atomically. Restart/replay returns the saved receipt through read authority; withdrawal and later invalidity remain new history or derived projections. B24 novelty outcomes never gate Approval, READY or package freeze. No external submission/send is asserted.

Owning lifecycle evidence:

- [ManuscriptVersion scientific placement](pr2_20_verification.md#exit-row-10): PASS; owning assertions verified
- [Internal Review → Issue → Decision → Revision](pr2_20_verification.md#exit-row-12): PASS; owning assertions verified
- [Basic Approval frozen target / blocking gate](pr2_20_verification.md#exit-row-13): PASS; owning assertions verified
- [SubmissionVersion package freeze](pr2_20_verification.md#exit-row-14): PASS; owning assertions verified
- [Retracted-source impact propagation](pr2_20_verification.md#exit-row-15): PASS; owning assertions verified
