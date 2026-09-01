# Architecture Decisions

- The accepted `ApplicationService`, `ProvenanceQueryService`, `GovernanceService`, and `GovernanceQueryService` remain the only business entry points.
- Route modules receive a service bundle and never receive repositories, ORM models, Sessions, or transaction controls.
- HTTP request schemas are strict adapter-local Pydantic models. Response schemas are finite adapter models derived deterministically from accepted dataclass DTO fields.
- Request identity is generated once per request with the accepted UUIDv7 factory and stored only on request state.
- The existing `/health` smoke endpoint is preserved; no additional non-frozen business route exists.
