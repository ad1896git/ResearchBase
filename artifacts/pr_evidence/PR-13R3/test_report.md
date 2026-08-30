# Test report

Full pytest passed on real PostgreSQL with 506 passed and 2 skipped. The focused PR-13 suite passed
14 tests, including repeated MISSING and NEVER_REQUESTED SpecVersion behavior, direct fallback
instrumentation, non-contextual validation, existing missing descendants, deterministic trace DTOs,
SQL scaling, closure reuse, exact historical provenance, cross-project isolation, and query purity.
Ruff and Pyright passed.

