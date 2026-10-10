# M3 implementation plan

Single executor; reuse feature/m3-literature-evidence at accepted M2 SHA. No authentication-profile change. Real independent-human acceptance is deferred by explicit user direction.

- [x] Localized document adapter: bounded UTF-8 text and JATS XML; exact paragraph/codepoint spans; reject ambiguous or mismatched selections. Test malformed XML, unsafe entities, invalid ranges and repeated matches before implementation.
- [x] Existing approved canonical LiteratureEvidence/review events/support snapshots: additive migration 0030, repository port/UoW and literal R2/R3 hashes; append-only history and database project/frozen-state guards. No Phase 1 hash or object changes.
- [x] Application commands: import immutable document ArtifactVersion with explicit lawful-retention basis; inspect; create source-backed bounded quotation; explicit attributable review; create/read immutable Claim/Hypothesis/Question support snapshots. Idempotent commands reauthorize and verify content before replay. SUPPORTS requires independent HUMAN VERIFIED event; non-support remains typed.
- [x] Authenticated local CLI: expose commands through production composition; reuse source-version create/freeze and existing local research commands. Technical test actors only inside tests, never a production bypass.
- [x] Focused real PostgreSQL tests: exact source/document closure, explicit review transitions, independent support, cross-project/forged identity/expired authority, conflicting edges, replay, artifact corruption and new-process recovery. Real accessible scientific document via approved source registration, actual non-root CLI identity, inspectable passage and Hypothesis; human review NOT RUN.
- [x] Modified-file Ruff/format/Pyright, relevant M0-M2 regressions, primary-executor contract/diff review, completion report, commit and verified replacement milestone bundle; M3_PARTIAL without actual independent reviewer. No push/merge/M4.

Real independent-human verification remains NOT RUN by explicit user direction; technical completion does not satisfy that acceptance item. Final delivery SHA and bundle verification are recorded in the completion report and delivery response.
