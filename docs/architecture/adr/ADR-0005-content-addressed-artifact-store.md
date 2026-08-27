# ADR-0005: Content-addressed ArtifactStore

- Status: Accepted
- Context: Artifact bytes need immutable, verifiable infrastructure storage before scientific Artifact domain behavior exists.
- Decision: Define an ArtifactStore port and use a local SHA-256 content-addressed filesystem implementation.
- Consequences: Identical bytes are idempotent; objects are never overwritten under an existing hash.
- Rejected alternatives: Mutable arbitrary paths, direct object-store coupling, and scientific Artifact entities in PR-00.
- Upstream authority: TDG-1
- Scope: Phase 1

