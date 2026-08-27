# Test report

The final full suite passed: **222 passed** against real PostgreSQL with `DATABASE_URL` set. The PR-06-specific integration and schema tests passed: **15 passed**. Static checks passed: Ruff and Pyright. Architecture plus PR-06 unit tests passed: **41 passed**.

Coverage includes Dataset create/get and nullable project ownership, FK preconditions, manifest validation, exact snapshot hashing, canonical ordering, material/excluded-field differentials, idempotent retry, cross-dataset behavior, deterministic concurrent creation, database immutability, late-failure rollback, exact schema, RESTRICT FKs, and uniqueness.
