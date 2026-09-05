# PR-17DR2 Contract, Test, and Evidence Closure Design

## Goal

Close the remaining PR-17DR review findings without changing frozen PR-17D v1.6 database semantics, public HTTP/CLI response shapes, `phase1-final`, PR-18 scope, or Phase 2 scope.

## Constraints

- The PR-17D v1.6 design remains frozen and approved.
- The existing immutable five-field `WriteResult` is authoritative: `id`, `version_id`, `content_hash`, `row_version`, and `server_timestamp`.
- ApplicationService write commands return `WriteResult`; no hidden payload or additional public field is added.
- HTTP and CLI continue returning their accepted legacy response shapes.
- Adapter compatibility uses deterministic read-after-write queries through ApplicationService, keyed by the command result's stable identifier or explicit command outcome.
- Adapters contain orchestration and serialization only; domain/business decisions remain in ApplicationService.
- PR-17D's 18-function, 40-trigger, 0-constraint catalog is unchanged.
- All semantic production, test, and migration changes finish before the PR-17DR2 subject is frozen.
- Evidence is generated afterward under `non-self-referential-v1` and no semantic changes follow evidence generation.

## Architecture

ApplicationService write methods will convert their committed typed result to the existing immutable `WriteResult` at the Application boundary. A central write-method registry will identify writes explicitly so query methods remain typed read operations. The conversion uses the Application clock for the UTC-aware server timestamp and preserves the existing stable identifier/hash semantics.

HTTP and CLI routes will receive `WriteResult`, then invoke an explicit Application query using the exact resource identifier from that result. A small transport compatibility helper will serialize the queried legacy read model. Version and relation queries missing from ApplicationService will be added as deterministic ID lookups; no query will search for a latest row or infer business state. Mutable resources are documented and tested as post-commit compatibility reads rather than atomic snapshots.

## Test and migration hardening

Historical closure fixtures will replace broad trigger suppression with exact trigger names or valid fixture construction. The concurrent Run finish fixture will use legal terminal metadata. A standalone `test_pr17dr2_concurrency.py` will coordinate two real PostgreSQL connections with barriers and inspect final persisted state.

Direct SQL tests will parameterize all applicable ClaimVersion supersession protected fields and all Run terminal metadata, including timestamps and seal fields, with post-state assertions. Migration preflight rollback will snapshot every Phase 1 scientific table in deterministic primary-key order using normalized database values, then compare the complete snapshot, revision, and owned-object catalog after the induced failure.

## Evidence

The existing evidence generator will be changed so expected values come from the static frozen manifest and observed values come from PostgreSQL catalog queries or executed command results. Every check records expected, observed, verdict, and source/query or test identifier; unexecuted checks are `NOT_VERIFIED`. Pytest results are captured with repository-relative commands and machine-readable JUnit output, then summarized with collected/passed/failed/skipped/deselected counts and database identity where applicable.

PR-17DR2 evidence will contain a separate `implementation_verification.json` alongside the object manifest, live catalog verification, and invariant-to-test projection. Authoritative command strings contain repository-relative paths only. Credentials are never persisted.

## Verification boundary

The implementation subject will be frozen after all semantic changes and before evidence generation. PostgreSQL 18 verification will run with zero current-remediation skips; only the two inherited PR11R2 opt-in tests may remain skipped. The branch will be stopped for an independent PR-17DR2 review and will not authorize PR-18 or Phase 2.
