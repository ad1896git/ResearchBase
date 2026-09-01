# Application Equivalence Report

Fake-handler tests prove exact command and `ExecutionContext` forwarding. Real PostgreSQL tests compare direct `ProvenanceQueryService.get_run_provenance` with HTTP output for canonical run ID and closure semantics. Error-code equivalence is exercised through the same injected Application boundary.
