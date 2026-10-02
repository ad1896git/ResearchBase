# P1-FCR4 clean-subject final evidence

Protocol: `non-self-referential-v1`

Reviewed implementation subject: `0b2fdc9611fd9e88a0c92dfad8b4c690335d39dc`

Parent: `3ebedad1f204bbb2e974572e6a1a00c89fd00503`

The reviewed subject was checked from a new clean checkout. No future
evidence commit identity is embedded in this artifact.

## Environment and lineage

- Python: 3.12.14; pytest 8.4.2
- PostgreSQL: 18.6
- Database Alembic: `0018_current_pointer_same_parent_integrity`
- Subject lineage: direct child of v3; commit count from v3: 1
- `phase1-final`: `5fe5dd90310d68d6df1683307f0d24dd2233c3dd`
- `phase1-final-v2`: `7012d3c95aea8b2da195abb1a54489ca717deaba`
- `phase1-final-v3`: `3ebedad1f204bbb2e974572e6a1a00c89fd00503`

## Package results

### Package A — constructor/hash contract

- Result: PASS
- Ten structured owners covered; lifecycle states and H/I vectors covered.
- `TRUE_HASH_MISMATCH_ACCEPTED=0`
- `INVALID_HASH_SCHEME_ACCEPTED=0`
- `INVALID_LIFECYCLE_HASH_STATE_ACCEPTED=0`
- `INVALID_CANONICAL_JSON_ACCEPTED=0`
- `LIFECYCLE_HASH_CONTRACT_GAPS=0`

### Package B — runtime ownership

- Result: PASS
- Durable matrix: 405 passed; clean focused closure matrix: 570 passed.
- `DTO_CHANGED_FROM_CALLER_MUTATION=0`
- `DOMAIN_CHANGED_FROM_DTO_MUTATION=0`
- `MATERIAL_PAYLOAD_ALIAS_COUNT=0`
- `DOMAIN_CHANGED_FROM_ORM_MUTATION=0`
- `DOMAIN_CHANGED_FROM_ORM_SOURCE_MUTATION=0`
- `ORM_TO_DOMAIN_LIVE_ALIAS_COUNT=0`
- `READ_DTO_ALIAS_COUNT=0`
- `AUTOFLUSH_ALIAS_PERSISTENCE=0`
- `UNRELATED_COMMIT_ALIAS_PERSISTENCE=0`
- `POST_FIX_LIVE_ALIAS_COUNT=0`
- `UNEXPLAINED_UNCOVERED_BOUNDARY_CELLS=0`
- `UNTESTED_PERSISTENCE_FAMILY=0`
- `UNTESTED_ORM_TO_DOMAIN_PERSISTENCE_FAMILY=0`

### Package C — persisted corruption

- Result: PASS.
- Ten structured owners: C1 and C2 fail closed; persisted C3 is N/A because
  schema has no persisted `hash_scheme` column and reconstruction supplies the
  frozen scheme.
- Binding, support-set, manifest-identity, Governance, downstream, query, and
  closure surfaces passed with no unexplained cells.
- `PERSISTED_CORRUPT_CANONICAL_OBJECT_RETURNED=0`
- `PERSISTED_CORRUPT_ROW_SILENTLY_SKIPPED=0`
- `RAW_EXCEPTION_LEAKED=0`
- `GOVERNANCE_CORRUPT_OBJECT_RETURNED=0`
- `UNVERIFIED_STRUCTURED_HASH_PROJECTION=0`
- `UNVERIFIED_GOVERNANCE_BINDING_PROJECTION=0`
- `UNVERIFIED_PROVENANCE_QUERY_PATHS=0`
- `CANONICAL_CORRUPTION_ACCEPTED_INTO_CLOSURE=0`
- `UNEXPLAINED_UNTESTED_CORRUPTION_CELL=0`

### Package D — HTTP/CLI boundaries

- Result: PASS.
- D1 versioned, D2 scientific result, D3 Claim/provenance, and D4 Governance
  corruption boundaries passed.
- `HTTP_CORRUPTION_RAW_EXCEPTION_COUNT=0`
- `HTTP_INTERNAL_DETAIL_LEAK_COUNT=0`
- `HTTP_VALID_CONTROL_FAILURES=0`
- `HTTP_ERROR_CLASS_COLLAPSE=0`
- `HTTP_DEEP_FROZENJSON_SERIALIZATION_FAILURES=0`
- `HTTP_SERIALIZATION_MUTATED_SOURCE=0`
- `HTTP_SERIALIZER_MATRIX_FAILURES=0`
- `CLI_CORRUPTION_RAW_EXCEPTION_COUNT=0`
- `CLI_INTERNAL_DETAIL_LEAK_COUNT=0`
- `CLI_VALID_SERIALIZATION_FAILURES=0`
- `CLI_ERROR_CLASS_COLLAPSE=0`
- `BOUNDARY_AUTO_REPAIR_OPERATIONS=0`
- `PUBLIC_HTTP_SCHEMA_CHANGE=NO`

### Package E — digest/canonicalization invariance

- Result: PASS; structured owner count: 10.
- Unit corpus: 20 tests; PostgreSQL corpus: 1 test; all passed.
- Independent canonical JSON oracle, raw-byte SHA, support-set, Governance,
  manifest, FrozenJSON, DTO, and ORM roundtrip checks were unchanged.
- `VALID_DIGEST_CORPUS_CHANGED=0`
- `VALID_STRUCTURED_DIGEST_CHANGED=0`
- `VALID_CANONICAL_PAYLOAD_CHANGED=0`
- `CANONICAL_JSON_V1_CHANGED=NO`
- `SHA256_CJSON_V1_CHANGED=NO`
- `UNICODE_CANONICALIZATION_DRIFT=0`
- `RAW_BYTE_DIGEST_CHANGED=0`
- `ARTIFACT_METADATA_AFFECTS_RAW_HASH=NO`
- `SUPPORT_SET_DIGEST_CHANGED=0`
- `GOVERNANCE_OWN_HASH_CHANGED=0`
- `GOVERNANCE_TARGET_BINDING_SEMANTICS_CHANGED=NO`
- `MANIFEST_HASH_SEMANTICS_CHANGED=NO`
- `FROZENJSON_HASH_REPRESENTATION_DRIFT=0`
- `FREEZE_THAW_DIGEST_DRIFT=0`
- `DTO_DOMAIN_DIGEST_DRIFT=0`
- `ORM_ROUNDTRIP_DIGEST_DRIFT=0`
- `VALID_PERSISTED_DIGEST_MISMATCH=0`

### Package F — mutation testing

- Result: PASS.
- M1 through M9 were each effectively applied, caught by focused tests, and
  restored to the committed file SHA.
- `M1=M2=M3=M4=M5=M6=M7=M8=M9=KILLED`
- `SURVIVING_CRITICAL_MUTATIONS=0`
- `MUTATION_RESTORATION_FAILURES=0`
- `TEMPORARY_MUTATION_RESIDUE=0`

## Fresh representative scan

New disposable PostgreSQL 18.6 database, populated through normal workflows,
using the independent digest oracle:

- Physical rows: 17
- Verification units: 11
- Valid: 11
- N/A: 0
- Mismatch: 0
- Unreadable: 0

## Final test and regression evidence

- Durable P1-FCR4 focused matrix: 570 passed, 0 failed.
- Named S03/S04, P1-FCR3, PR17D, and PR18 regression set: 136 passed,
  0 failed.
- Full suite: 1,747 collected; 1,745 passed; 2 accepted PR11R2 skips;
  0 failed; 0 errors; return code 0.
- PostgreSQL integration: 911 collected; 909 passed; 2 accepted PR11R2
  skips; 0 failed; 0 errors; return code 0.
- S03: PASS
- S04: PASS
- PR17D: PASS
- RB-P1-001: remains closed
- Run: PASS
- Measurement: PASS
- StatisticalResult: PASS
- Claim/provenance: PASS
- Governance: PASS
- ArtifactStore: PASS
- PR18: PASS; false-positive risk LOW

## Static, schema, and phase boundary checks

- Ruff lint: PASS
- Ruff format: 203 files already formatted; 9 inherited S13 files would be
  reformatted; 0 P1-FCR4 changed-file failures; no files modified by formatter.
- Pyright: PASS, 0 errors
- `git diff --check`: PASS
- Migrations changed: 0; new migration: NONE
- Historical canonical rows rewritten: 0
- Hashes rewritten: 0; automatic rehash: 0
- Subject dependency files unchanged; tags unchanged
- Phase 2 source leakage: 0
- Agent framework/runtime additions: 0

All evidence above is bound to the reviewed implementation subject SHA and is
intentionally silent about the future evidence commit identity.
