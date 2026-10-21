# PR2-10 conditional slice 01 — derived discussion artifacts

**Base:** reviewed PR2-08 conditional evidence
`8a36f48bfdfe1b8be60f299af7534bad03c081fd`.

**Frozen sources:** Phase 2 specification §§14, 26, 41.6, 42.4 and PR2-10;
Global Schema Registry DiscussionSession/DiscussionTurn and ArtifactVersion
roles; Cross-Phase Contracts discussion/decision separation.

**Scope:** Given a trusted, closed DiscussionSession snapshot with immutable,
ordered DiscussionTurn records and concrete ResearchQuestionVersion,
SourceVersion and ClaimVersion input IDs, build deterministic exact-byte
candidates for DiscussionTranscript and
ConceptMap ArtifactVersion roles. ConceptMap contains only mechanical
turn-to-citation edges; it makes no scientific inference. Preserve speaker,
role, timestamp, utterance and exact cited version IDs in the transcript.
Validate session/project identity, contiguous turn order, citation type and
source/claim reference allowlists before rendering. Preserve all three input
reference kinds in the transcript. Return SHA-256 for each
candidate's exact bytes. Both outputs remain unverified derived candidates.

**Exclusions:** No DiscussionSession/Turn table or migration, persistent
Application command, ArtifactVersion/CAS write, ResearchSummary generation,
promotion, decision/approval creation, live provider, retained data write,
human identity simulation or formal PR2-10 admission. Future Application
integration must load authorized canonical records, preserve append-only turn
semantics, create actual ArtifactVersions and implement explicit promotion.

**Acceptance:** Deterministic bytes/hash/order; exact references and
attribution; invalid, cross-session, duplicate or out-of-order turns rejected;
unknown refs rejected; open session rejected; no inferred claims, decisions or
promotion; no mutable aliases or raw bytes logged. Focused tests plus relevant
architecture/M2/M3 regression, Ruff and Pyright.

**STOP:** Any need to authenticate a real person, write retained data, add a
schema outside the frozen contract, or treat discussion as scientific truth.
