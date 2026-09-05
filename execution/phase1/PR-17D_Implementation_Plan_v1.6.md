# PR-17D Phase 1 Implementation Plan v1.6

Status: planning only. Do not execute until final independent approval. No implementation is performed by this document.

## Global constraints

- Preserve v1.0–v1.5 unchanged.
- Touch only the eventual PR-17D implementation surfaces after approval; this design revision touches only these two documents.
- Do not add PR-18, Phase 2 objects, data normalization, or SAFE_MIGRATION transformations.
- The final persistent inventory is derived from the v1.6 invariant/trigger graph: 18 functions, 40 triggers, 0 constraints.

## D1 invariant and manifest-first TDD

Before migration source, test the v1.6 graph as data:

1. Expand all 40 trigger rows from the compact design ranges.
2. Assert every trigger has exactly one function ID and every function ID resolves to one final function row.
3. Assert every DB-required invariant has at least one trigger path.
4. Assert every final function has at least one trigger consumer.
5. Assert the function-to-function edge set is empty.
6. Assert the generated object counts are functions 18, triggers 40, constraints 0.
7. Assert none of the 64 removed v1.5 names occurs in the final manifest or stage lists.

## D2 catalog and ownership TDD

Test literal ownership with the semantic predicate `left(name, 6) = 'pr17d_'` (or the explicitly equivalent escaped `LIKE` form). Include names `pr17d_x`, `pr17dx`, and `apr17d_x`. Test exact expected-vs-observed set equality for functions, triggers, and constraints, including missing and unexpected objects.

Retain tests for function schema/name/signature/return type/language and trigger schema/table/timing/events/ROW level/bound function. A same-name wrong-table, wrong-event, wrong-timing, wrong-level, wrong-schema, or wrong-function trigger must fail.

## D3 migration lifecycle TDD

Test U01–U08 and D01–D07 with the regenerated stages. U04 creates only the 18 final functions; U05 creates only the 40 final triggers; U07 verifies exact catalog projections and sets inside the migration transaction. Test preflight, function-creation, trigger-creation, catalog-verification, and constraint-stage failures for rollback of revision and partial objects.

Preserve tests for fresh install, valid populated upgrade, invalid populated upgrade, zero scientific row transformations, downgrade dependency order, unchanged 0015 objects/data, and upgrade/downgrade/upgrade semantic inventory equality.

## D4 evidence and regression

Regenerate `migration_object_manifest.json` and `migration_catalog_verification.json` from the v1.6 graph while preserving their v1.5 schemas and non-self-referential-v1 protocol. Update only derived object counts/rows. Run the accepted v1.2 Application/HTTP/CLI, query-purity, concurrency, atomicity, and golden-workflow regressions. Preserve D0, configuration, logging, CI, errors, WriteResult, scope, and PR-18 separation.

## D5 final independent gate

The final reviewer must independently confirm:

- 18 final functions, 40 final triggers, and 0 constraints;
- zero orphan functions and zero unresolved generic helpers;
- complete invariant → trigger → function coverage;
- corrected literal ownership detection and exact set equality;
- no stale v1.5 function/stage entries;
- no D0, lifecycle, compatibility, evidence, or scope regression;
- P0/P1/P2 = 0 and `PRIOR_ACCEPTED_DESIGN_REGRESSION = NO`.

`PHASE1_REMAINING_PR18` remains separate and unchanged: index verification, query EXPLAIN baselines, docs/API examples, TODO/FIXME disposition, and the final no-P0/P1 architecture-TODO gate. These do not block PR-17D TDD and block Phase 1 final closure.

PR-17D implementation remains unauthorized until final independent design approval.
