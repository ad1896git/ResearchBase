# Architecture Decisions

- CLI commands invoke only `ApplicationService`, `ProvenanceQueryService`, `GovernanceService`, and
  `GovernanceQueryService` public interfaces.
- Persistence/UoW construction is isolated in `cli/composition.py`, the composition-root exception allowed
  by AD-PR16-001; command modules do not import persistence or repositories.
- CLI invocation state is immutable and created per invocation. No system actor or process-global request
  context exists.
- JSON string and UTF-8 JSON-file input are the only structured transports. Artifact content in JSON uses
  explicit base64 (`data_base64`); no YAML/TOML transport was introduced.
- Query commands call accepted read services and format returned DTOs without ORM access or output-layer
  database work.
