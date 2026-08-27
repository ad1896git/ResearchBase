# PR-04 Concurrency Report

Identity pointer updates use conditional SQL updates of the form `WHERE id = :id AND row_version = :expected`, incrementing `row_version` on success. A zero row count is translated to `CONCURRENT_MODIFICATION`.

The same pattern is used for actual DRAFT material update paths. Version allocation is parent-local and performed while the identity is locked; PostgreSQL uniqueness additionally protects `(parent_id, version_number)`.

Real PostgreSQL tests passed for:

- stale ResearchQuestion identity pointer updates from two independent UoWs;
- stale Hypothesis identity pointer updates from two independent UoWs;
- stale ResearchQuestion DRAFT material updates;
- parent-local version numbering and retained history.
