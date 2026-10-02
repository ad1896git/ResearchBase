# ResearchBase — P1-FCR4R2 clean-subject final evidence

protocol: non-self-referential-v1
reviewed_subject_sha: f133a2bde3046450b50cb814e0932f02a82a492e
reviewed_subject_parent: 23bf03ae749c8dc17dbbda24fafdb41c8a52c888

## Lineage and subject integrity

- The clean detached evidence checkout began at `f133a2bde3046450b50cb814e0932f02a82a492e`.
- Its direct parent was rejected P1-FCR4R1 evidence `23bf03ae749c8dc17dbbda24fafdb41c8a52c888`.
- Earlier immutable audit history remains `3ebedad1f204bbb2e974572e6a1a00c89fd00503` → `0b2fdc9611fd9e88a0c92dfad8b4c690335d39dc` → `545eb5cd141d833e2ca97e2f96e840fe1861ae20` → `7393cacb4684b232c8a314d80be0da628cc18815` → `23bf03ae749c8dc17dbbda24fafdb41c8a52c888` → reviewed subject.
- `phase1-final-v3` still peels to `3ebedad1f204bbb2e974572e6a1a00c89fd00503`.
- The reviewed implementation delta is exactly six files: `src/researchbase/foundation/frozen_json.py`, `src/researchbase/api/routes.py`, `tests/e2e/support.py`, `tests/integration/test_pr15_api.py`, `tests/unit/test_p1_fcr4r1_frozen_json_backing.py`, and `tests/unit/test_p1_fcr4r2_intrinsic_immutability.py`.
- Migration, dependency, CI, Phase 2, and Agent/runtime deltas are zero.

## Original defects and intrinsic representation

- Original P1-FCR4 mutable authoritative dict exploit succeeded on the rejected implementation and is blocked on the reviewed subject.
- Original P1-FCR4R1 `object.__setattr__` authoritative tuple-slot rebinding succeeded on the rejected R1 implementation and is blocked on the reviewed subject for both object and array wrappers.
- `FrozenJSONObject` is a tuple subclass whose tuple payload is its sole authoritative state.
- `FrozenJSONArray` is a tuple subclass whose tuple payload is its sole authoritative state.
- Both types declare `__slots__ = ()`, expose no `__dict__`, and have no writable or rebindable authoritative attribute.
- Fresh post-restoration attacks using `object.__setattr__`, `object.__delattr__`, arbitrary attribute injection/deletion, direct tuple mutation, nested object attacks, and nested array attacks produced `REFLECTIVE_CANONICAL_MUTATION_SUCCESS_COUNT=0`, material drift `0`, and digest drift `0`.
- The direct backing/reflection set passed `31/31` tests after restoration.

## Structured-owner hash integrity

All ten structured owners were attacked and rechecked: ResearchQuestionVersion, HypothesisVersion, ExperimentSpecVersion, DatasetSnapshot, MetricDefinitionVersion, Measurement, StatisticalResult, ClaimVersion, ImpactAssessment, and CorrectionRecord.

- Reflective attack material drift: `0`.
- Reflective attack digest drift: `0`.
- Post-construction hash drift: `0`.
- Recursive mutable authoritative node count: `0`.

## Package B — ownership

Caller→DTO, DTO→Domain, Domain→material payload, Domain→ORM, ORM→Domain, read DTO, same-object ORM attacks, direct Domain→ORM attacks, direct FrozenJSON backing attacks, and reflective attacks passed.

- `POST_FIX_LIVE_ALIAS_COUNT=0`.
- `ORM_TO_DOMAIN_LIVE_ALIAS_COUNT=0`.
- `DIRECT_FROZENJSON_BACKING_ALIAS_COUNT=0`.
- `REFLECTIVE_CANONICAL_MUTATION_SUCCESS_COUNT=0`.
- Package B: PASS.

## Package C — persisted corruption

Wrong valid-shape hashes, stale hashes after material changes, Claim support-set bindings, Governance target bindings, DatasetSnapshot manifest identity, provenance/closure paths, and downstream structured verification fail closed.

- `PERSISTED_CORRUPT_CANONICAL_OBJECT_RETURNED=0`.
- `PERSISTED_CORRUPT_ROW_SILENTLY_SKIPPED=0`.
- `RAW_EXCEPTION_LEAKED=0`.
- `UNVERIFIED_STRUCTURED_HASH_PROJECTION=0`.
- `UNVERIFIED_GOVERNANCE_BINDING_PROJECTION=0`.
- `UNVERIFIED_PROVENANCE_QUERY_PATHS=0`.
- `CANONICAL_CORRUPTION_ACCEPTED_INTO_CLOSURE=0`.
- Package C: PASS.

## Package D — HTTP and CLI boundaries

- HTTP valid control failures: `0`.
- HTTP corruption raw exception count: `0`.
- HTTP internal detail leak count: `0`.
- CLI valid serialization failures: `0`.
- CLI corruption raw exception count: `0`.
- CLI internal detail leak count: `0`.
- Public HTTP schema change: NO.
- HTTP error contract change: NO.
- Package D: PASS.

The `api/routes.py` compatibility traversal is required because generic Pydantic `model_dump()` would otherwise consume a tuple-subclass `FrozenJSONObject` as a list of pairs before FrozenJSON-specific thawing. It preserves the frozen HTTP shape without adding scientific semantics. Test support avoids the equivalent `dataclasses.asdict()` tuple-subclass reconstruction problem.

## Tuple/Mapping and raw JSON compatibility

- Key iteration, membership, length, string lookup, `items`, `keys`, `values`, dict semantic equality, array sequence behavior, and list semantic equality passed.
- Pydantic, FastAPI, CLI, DTO, persistence, thaw, and canonical hash paths passed.
- Tuple/Mapping compatibility regressions: `0`.
- Direct stdlib `json.dumps(FrozenJSON_wrapper)` is not an existing public contract.
- Supported public paths explicitly thaw or convert wrappers before serialization.

## Package E — semantic invariance

The committed Phase 1 v3 corpus and reviewed R2 subject were compared with the independent stdlib `json.dumps` plus `hashlib.sha256` oracle.

- Valid digest corpus changed: `0`.
- Valid canonical payload changed: `0`.
- `CANONICAL_JSON_V1_CHANGED=NO`.
- `SHA256_CJSON_V1_CHANGED=NO`.
- Raw-byte digest changed: `0`.
- Support-set digest changed: `0`.
- Governance target-binding semantics changed: NO.
- Package E: PASS.

## Fresh clean-subject mutation suite

Every mutation was applied independently to the committed R2 subject, proven behaviorally effective, caught by a durable test, and restored to the committed file SHA before the next mutation.

- M1 shallow wrapper ownership: `KILLED`; direct source mutation changed wrapper material and `test_wrapper_constructors_own_direct_container_inputs` failed.
- M2 shallow recursive ownership: `KILLED`; nested caller material changed frozen values and the ownership matrix produced `80 failed, 112 passed, 309 deselected` for the selected catcher set.
- M3 hash-equality bypass: `KILLED`; wrong valid-shape hashes were accepted and the corruption catcher produced `5 failed, 5 passed, 31 deselected`.
- M4 live `material_payload()`: `KILLED`; repeated payload exposure retained mutation and the selected fresh-payload test failed.
- M5 exact ORM→Domain alias: `KILLED`; ORM nested mutation changed Domain material and the strengthened exact-object test failed.
- M6 Domain→ORM thaw/copy bypass: `KILLED`; the ORM received a FrozenJSONObject instead of a fresh dict and the fresh-tree test failed.
- M7 Governance target-binding bypass: `KILLED`; a mismatched target binding was accepted and the audit-finding corruption test failed.
- M8 downstream structured verification bypass: `KILLED`; a corrupt Measurement reached downstream impact and the corruption test failed.
- M9 persisted-corruption normalization bypass: `KILLED`; raw `ValueError` escaped the D1 HTTP/CLI boundary test.
- M10 mutable authoritative dict backing: `KILLED`; `_values.clear()` changed material from the valid object to `{}` and the direct-backing test failed.
- M11 rebindable authoritative tuple slots: `KILLED`; `object.__setattr__` changed object material to `{}` and array material to `[]`; the R2 reflective suite produced `13 failed, 1 passed`.

- `SURVIVING_CRITICAL_MUTATIONS=0`.
- `MUTATION_RESTORATION_FAILURES=0`.
- `TEMPORARY_MUTATION_RESIDUE=0`.
- Restored committed SHA-256 values included `frozen_json.py=c2347c47a6274939c07446d1ac5df8f7a5e91dc0f19b5cb4a6745fafec9a001c`, `versioning.py=6a90afff1943d3e846ddc75953a93b53583fb3ae0393a06b861ba8e0e8ba48e8`, `research.py=01a4dad7cbc05d7ae10a408ecadc536453b33c3eb8f377886de183f106e76ec6`, `repositories.py=5583fce0eb6fe47397291564453edebaf60ae22a4d961babeaa41d5e448bc51f`, and `governance_repository.py=69382d18e21e6511c383cb8a624c3f571e5fc9c04d56b9d9e179159333e3c6ae`.
- The post-restoration focused defense matrix passed `601 collected, 601 passed, 0 failed, 0 skipped, 0 xfailed`.

## Fresh representative PostgreSQL scan

- A new isolated PostgreSQL database was migrated and populated through the repository-owned application workflow.
- PostgreSQL: `18.6`.
- Database Alembic head: `0018_current_pointer_same_parent_integrity`.
- The persisted reconstruction scan used the independent stdlib JSON/SHA-256 oracle.
- Physical rows across the 11 canonical/raw owner tables: `12`.
- Verification units: `11`.
- Valid: `11`.
- N/A: `0`.
- Mismatch: `0`.
- Unreadable: `0`.
- No persisted hash was repaired or rewritten; the disposable database was removed automatically.

## Clean-subject regression and static evidence

- Focused R2 defense matrix: `601 collected, 601 passed, 0 failed, 0 skipped, 0 xfailed`.
- Authoritative PostgreSQL integration directory: `911 collected, 909 passed, 0 failed, 0 errors, 2 accepted historical PR11R2 skips, 0 xfailed, 0 deselected`.
- Full suite: `1778 collected, 1776 passed, 0 failed, 0 errors, 2 accepted historical PR11R2 skips, 0 xfailed`.
- Ruff lint: PASS.
- Pyright: PASS, `0 errors`.
- `git diff --check`: PASS.
- Ruff formatting: all six R2 changed files formatted; only the inherited nine S13 files remain.

## History, schema, Phase, and P3 boundaries

- Migration delta: `0`; new migration: NONE.
- Repository/database Alembic head: `0018_current_pointer_same_parent_integrity`.
- Historical rows rewritten: `0`; hashes rewritten: `0`; automatic rehash: NO.
- Historical commits modified: NO; historical tags moved: NO.
- Phase 2 leakage: `0`; Agent/runtime expansion: `0`.
- P3 scope unchanged: S13 formatter debt, S16 Golden fixture coverage, and MetricDefinition ORM metadata drift.

## Executor closure state

- `RB_V3_P1_001_SELF_VERIFIED_CLOSED=YES`.
- `RB_V3_P1_002_SELF_VERIFIED_CLOSED=YES`.
- `P1_FCR4R2_SELF_APPROVED=NO`.
- `READY_FOR_INDEPENDENT_P1_FCR4R2_REVIEW=YES`.
- `READY_FOR_FINAL_DELTA_CONFORMANCE=NO`.
- `READY_FOR_PHASE1_FREEZE_V4=NO`.
- `PHASE1_FINAL_V3_MUTATED=NO`.
- `PHASE_2_AUTHORIZED=NO`.

This artifact intentionally contains no future evidence-commit SHA.
