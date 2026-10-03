# Phase 1 regression and non-drift

Implementation subject: `5b65f6983dd627757ac7ab7b1fb6befe0a832573`.

The `phase1-final-v4` annotated tag object is `63f6a1d28afa79ce8620fc9233793ab9c40a515d`; its peeled commit is `d2400fbeca835c89bd802a4e9d647bda01cfd115`, matching the frozen semantic baseline. No Phase 1 production source or historical migration was changed. Migration `0019_phase2_bootstrap_membership` adds the eight Phase 2 tables and its guards; the migration integration test compares Phase 1 schema, constraints, indexes and row digests before and after 0019 and passes without a difference.

The Phase 1 test-harness adaptations are limited to pinning historical Phase 1 regression setup/upgrade targets to `0018_current_pointer_same_parent_integrity`. This keeps those checks at the frozen Phase 1 endpoint while the Phase 2 migration tests independently exercise `0018 → 0019`. The error-mapping fixture adds explicit entries for the newly introduced stable Phase 2 error codes; it retains the existing Phase 1 mappings and set-completeness assertions. These changes do not redefine Phase 1 scientific behavior.

Command: `uv run pytest -o addopts='' -ra` against PostgreSQL 18.6.

Result: **1,806 passed, 2 skipped, 0 failed**. Both skips are the existing PR11R2 migration matrix tests, which require `PR11R2_MIGRATION_DB_URL`.
