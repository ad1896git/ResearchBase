# Cross-Adapter Equivalence Report

`tests/e2e/test_phase1_cross_adapter_equivalence.py` passed all three tests:

- Application projection equals FastAPI projection;
- Application projection equals Typer projection;
- adapter order independence holds across independent fresh fixtures in CLI, Application, HTTP order.

The CLI workflow uses the accepted CLI command surface and supplies only the parent IDs required by that
surface. HTTP payloads remain the accepted HTTP payloads. Neither adapter calls the other.

The comparison retains scientific statuses, hashes, exact references, evidence relation type/qualification/
ordinal, closure, trace topology, deduplicated Runs, and governance outcome.

PR-17R corrected the projection helper to consume observed Application DTOs, HTTP JSON, CLI JSON, and fresh
accepted reads. The independent order replay uses two fresh fixtures and both adapter orders; it also asserts
Application == HTTP == CLI after real observation rather than comparing a no-op normalized structure.
