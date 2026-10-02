# ResearchBase — P1-FCR4R1 clean-subject final evidence

protocol: non-self-referential-v1
reviewed_subject_sha: 7393cacb4684b232c8a314d80be0da628cc18815
reviewed_subject_parent: 545eb5cd141d833e2ca97e2f96e840fe1861ae20

## Lineage and subject integrity

- Clean detached checkout began at `7393cacb4684b232c8a314d80be0da628cc18815`.
- `HEAD^` was `545eb5cd141d833e2ca97e2f96e840fe1861ae20`.
- `HEAD^^` was `0b2fdc9611fd9e88a0c92dfad8b4c690335d39dc`.
- `HEAD^^^` was `3ebedad1f204bbb2e974572e6a1a00c89fd00503`.
- The subject worktree was clean before execution and returned clean after all temporary mutations.
- Historical tags remained exact: `phase1-final`=`5fe5dd90310d68d6df1683307f0d24dd2233c3dd`, `phase1-final-v2`=`7012d3c95aea8b2da195abb1a54489ca717deaba`, `phase1-final-v3`=`3ebedad1f204bbb2e974572e6a1a00c89fd00503`.
- The R1 subject delta was exactly `src/researchbase/foundation/frozen_json.py` and `tests/unit/test_p1_fcr4r1_frozen_json_backing.py`; migration, dependency, CI, and Phase 2 deltas were zero.

## Original independent exploit

The exact prior attack was attempted against the committed representation:

```python
value = freeze_json({"nested": {"x": 1}})
value._values["nested"]._values["x"] = 2
```

The attack was blocked by `AttributeError`; the original path did not reproduce, material drift was `0`, and hash drift was `0`.

## FrozenJSON backing and attacks

- `FrozenJSONObject` authoritative backing: `tuple[tuple[str, FrozenJSON], ...]` in `_items`.
- `FrozenJSONArray` authoritative backing: `tuple[FrozenJSON, ...]` in `_values`.
- Recursive structural inspection found `MUTABLE_AUTHORITATIVE_CONTAINER_COUNT=0`.
- Object assignment, deletion, clear, pop, update, setdefault, slot rebinding, and slot deletion attacks were exercised.
- Nested object attacks were exercised through multiple levels.
- Array append, extend, clear, item assignment, and item deletion attacks were exercised.
- `DIRECT_FROZENJSON_BACKING_ALIAS_COUNT=0`.
- Caller dict/list mutations after construction did not change frozen material.

## Structured-owner hash integrity

All ten structured owners were exercised: ResearchQuestionVersion, HypothesisVersion, ExperimentSpecVersion, DatasetSnapshot, MetricDefinitionVersion, Measurement, StatisticalResult, ClaimVersion, ImpactAssessment, and CorrectionRecord.

- Direct backing attack failures: `0`.
- Material drift after attack: `0`.
- Digest drift after attack: `0`.
- `POST_CONSTRUCTION_HASH_DRIFT_AFTER_DIRECT_ATTACK=0`.

## Package B — ownership

Committed ownership tests passed, including caller→DTO, DTO→Domain, Domain→material payload, Domain→ORM, ORM→Domain, read DTO, same-object ORM attacks, direct Domain→ORM attacks, and direct FrozenJSON backing attacks.

- `POST_FIX_LIVE_ALIAS_COUNT=0`.
- `ORM_TO_DOMAIN_LIVE_ALIAS_COUNT=0`.
- `DIRECT_FROZENJSON_BACKING_ALIAS_COUNT=0`.
- `UNTESTED_PERSISTENCE_FAMILY=0`.
- `UNTESTED_ORM_TO_DOMAIN_PERSISTENCE_FAMILY=0`.
- Package B: PASS.

## Package C — persisted corruption

Wrong valid-shape hashes, changed material with stale hashes, Claim support-set bindings, Governance target bindings, DatasetSnapshot manifest identity, provenance queries/closure, and downstream impact were exercised. Persisted corruption was normalized to `REFERENTIAL_INTEGRITY_ERROR` and was not returned or silently skipped.

- Persisted corrupt canonical object returned: `0`.
- Persisted corrupt row silently skipped: `0`.
- Raw exception leaked: `0`.
- Unverified structured hash projection: `0`.
- Unverified Governance binding projection: `0`.
- Unverified provenance query path: `0`.
- Canonical corruption accepted into closure: `0`.
- Package C: PASS.

## Package D — public boundaries

Valid deep FrozenJSON serialization and persisted corruption were exercised through HTTP and CLI.

- HTTP valid control failures: `0`.
- HTTP corruption raw exception count: `0`.
- HTTP internal detail leak count: `0`.
- HTTP error-class collapse: `0`.
- CLI valid serialization failures: `0`.
- CLI corruption raw exception count: `0`.
- CLI internal detail leak count: `0`.
- CLI error-class collapse: `0`.
- Public HTTP schema change: NO.
- Package D: PASS.

## Package E — semantic invariance

The committed v3 corpus was compared with the R1 subject using an independent stdlib `json.dumps`/`hashlib.sha256` oracle. Structured digest drift was `0`; canonical payload drift was `0`; production and oracle canonical/digest outputs matched; raw ArtifactVersion bytes, support-set hashes, hashless Run semantics, and Governance target semantics remained unchanged.

- Valid digest corpus changed: `0`.
- Valid structured digest changed: `0`.
- Valid canonical payload changed: `0`.
- `CANONICAL_JSON_V1_CHANGED=NO`.
- `SHA256_CJSON_V1_CHANGED=NO`.
- Raw-byte digest changed: `0`.
- Support-set digest changed: `0`.
- Governance own-hash changed: `0`.
- Governance target-binding semantics changed: NO.
- Manifest-hash semantics changed: NO.
- Package E: PASS.

## Package F/R1 mutation suite

M1 through M10 were effectively applied as temporary source mutations, each caused its intended focused failure, and each was restored before proceeding:

`M1=KILLED` (shallow wrapper construction), `M2=KILLED` (shallow recursive ownership), `M3=KILLED` (hash equality bypass), `M4=KILLED` (live material payload), `M5=KILLED` (ORM→Domain alias), `M6=KILLED` (Domain→ORM no thaw/copy), `M7=KILLED` (Governance target-binding bypass), `M8=KILLED` (provenance content-hash bypass), `M9=KILLED` (persisted-corruption normalization bypass), and `M10=KILLED` (mutable FrozenJSONObject backing resurrection).

- Surviving critical mutations: `0`.
- Mutation restoration failures: `0`.
- Temporary mutation residue: `0`.
- Worktree returned exactly to the R1 subject before evidence generation.

## Fresh representative PostgreSQL scan

- PostgreSQL: `18.6`.
- Repository and database Alembic head: `0018_current_pointer_same_parent_integrity`.
- A new isolated database was clean-installed and populated through normal workflows.
- Physical rows scanned across the 11 canonical/raw owner tables: `12`.
- Verification units: `11`.
- Valid: `11`.
- N/A: `0`.
- Mismatch: `0`.
- Unreadable: `0`.

## Regression and static evidence

- Full suite: `1764 collected, 1762 passed, 0 failed, 0 errors, 2 accepted historical PR11R2 skips, 0 xfails`.
- PostgreSQL integration suite: `911 collected, 909 passed, 0 failed, 0 errors, 2 accepted historical PR11R2 skips`.
- S03, S04, PR17D, RB-P1-001, Run, Measurement, StatisticalResult, Claim/provenance, Governance, ArtifactStore, and PR18: PASS.
- PR18 false-positive risk: LOW; its hardening, boundary, evidence, and route-contract tests passed without new skips or xfails.
- Ruff lint: PASS.
- Ruff format check: only the inherited 9 S13 files would reformat; 0 R1 changed-file failures; no formatting changes made.
- Pyright: PASS, 0 errors.
- `git diff --check`: PASS.
- Migration delta: `0`; new migration: NONE.
- Historical rows rewritten: `0`; hashes rewritten: `0`; automatic rehash: `0`.
- Phase 2 source leakage: `0`; Agent/runtime expansion: `0`.
- P3 scope unchanged: S13 formatter debt, S16 Golden fixture coverage, and MetricDefinition ORM metadata drift.

## Closure state

- `RB_V3_P1_001_SELF_VERIFIED_CLOSED=YES`.
- `RB_V3_P1_002_SELF_VERIFIED_CLOSED=YES`.
- `P1_FCR4R1_SELF_APPROVED=NO`.
- `READY_FOR_INDEPENDENT_P1_FCR4R1_REVIEW=YES`.
- `READY_FOR_FINAL_DELTA_CONFORMANCE=NO`.
- `READY_FOR_PHASE1_FREEZE_V4=NO`.
- `PHASE1_FINAL_V3_MUTATED=NO`.
- `PHASE_2_AUTHORIZED=NO`.

This artifact intentionally contains no future evidence-commit SHA.
