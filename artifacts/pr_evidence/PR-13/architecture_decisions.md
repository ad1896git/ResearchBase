# Architecture decisions

- AD-PR13-001: explicit frozen dataclass DTOs containing scalar/typed values only.
- AD-PR13-002: explicit `ClaimEvidencePathDTO`; Run deduplication is independent from path preservation.
- AD-PR13-003: no generic graph abstraction or traversal registry.
- AD-PR13-004: every public query opens exactly one UoW and reuses it for all traversal legs and closure validation.
- Existing repositories and validators are reused; no second source of scientific truth exists.

