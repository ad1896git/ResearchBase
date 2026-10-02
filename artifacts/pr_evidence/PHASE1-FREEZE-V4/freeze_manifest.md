# ResearchBase — Phase 1 corrected frozen baseline v4

Protocol: `non-self-referential-v1`

## Formal freeze identity

- Formal freeze name: `phase1-final-v4`
- Semantic implementation subject: `f133a2bde3046450b50cb814e0932f02a82a492e`
- Pre-freeze evidence head: `ef3ba46722e226db09c88a8fde0021e4d26fd7c9`
- Previous formal freeze: `phase1-final-v3` at `3ebedad1f204bbb2e974572e6a1a00c89fd00503`

The tag and freeze commit identify this declaration. This artifact intentionally does not
self-reference the future freeze commit object.

## Corrective audit lineage

The complete immutable lineage from Phase 1 v3 is:

```text
3ebedad1f204bbb2e974572e6a1a00c89fd00503  phase1-final-v3
  ↓
0b2fdc9611fd9e88a0c92dfad8b4c690335d39dc  rejected P1-FCR4 implementation
  ↓
545eb5cd141d833e2ca97e2f96e840fe1861ae20  rejected P1-FCR4 evidence
  ↓
7393cacb4684b232c8a314d80be0da628cc18815  rejected P1-FCR4R1 implementation
  ↓
23bf03ae749c8dc17dbbda24fafdb41c8a52c888  rejected P1-FCR4R1 evidence
  ↓
f133a2bde3046450b50cb814e0932f02a82a492e  accepted P1-FCR4R2 implementation
  ↓
ef3ba46722e226db09c88a8fde0021e4d26fd7c9  accepted P1-FCR4R2 evidence
```

Closure history:

- `RB-V3-P1-001`: independently CLOSED.
- `RB-V3-P1-002`: independently CLOSED.
- P1-FCR4: REJECTED.
- P1-FCR4R1: REJECTED.
- P1-FCR4R2: ACCEPTED.
- `FINAL_DELTA_CONFORMANCE`: PASS.
- `CORRECTION_RESTORES_EXISTING_CONTRACT`: YES.
- `CORRECTION_INTRODUCES_NEW_CONTRACT`: NO.

## Accepted verification state

- Focused defense matrix: 601 collected, 601 passed, 0 failed, 0 skipped, 0 xfailed.
- Authoritative integration: 911 collected, 909 passed, 2 accepted PR11R2 skips,
  0 failed, 0 errors.
- Full suite: 1778 collected, 1776 passed, 2 accepted PR11R2 skips, 0 failed,
  0 errors.
- PostgreSQL: 18.6.
- Alembic head: `0018_current_pointer_same_parent_integrity`.
- Representative persisted verification: 11/11 valid, mismatch 0, unreadable 0.

The only accepted skips are:

```text
tests.integration.test_pr11r2_migration::
test_clean_previous_head_upgrade_and_roundtrip_reaches_fail_closed_head

tests.integration.test_pr11r2_migration::
test_invalid_legacy_upgrade_fails_closed_and_manual_remediation_retries
```

No other skip or xfail is accepted by this freeze.

## Semantic conformance

- `canonical-json-v1` changed: NO.
- `sha256-cjson-v1` changed: NO.
- Valid canonical payload drift: 0.
- Structured digest drift: 0.
- Raw-byte digest drift: 0.
- Migration delta: 0.
- Database schema delta: 0.
- Dependency delta: 0.
- Phase 2 leakage: 0.
- Agent/runtime expansion: 0.

## FrozenJSON contract

- `FrozenJSONObject`: intrinsic tuple payload.
- `FrozenJSONArray`: intrinsic tuple payload.
- Instance `__dict__`: absent.
- Writable slots: none.
- Mutable authoritative containers: 0.
- Rebindable authoritative references: 0.
- Ordinary Python-level reflective canonical mutation: blocked.

The covered threat boundary is ordinary Python-level operation, including
`object.__setattr__` and `object.__delattr__`. `ctypes`, C-extension, debugger, and
process-memory rewriting are outside scope.

## Hash-owner roles

The structured own-content hash owners remain exactly:

- `ResearchQuestionVersion`
- `HypothesisVersion`
- `ExperimentSpecVersion`
- `DatasetSnapshot`
- `MetricDefinitionVersion`
- `Measurement`
- `StatisticalResult`
- `ClaimVersion`
- `ImpactAssessment`
- `CorrectionRecord`

`ArtifactVersion` remains the raw-byte hash owner. `Run` remains hashless.

The following bindings remain distinct from own-content hashes:

- `ClaimVersion.support_set_hash`
- `AuditFinding.target_content_hash`
- `ImpactTarget.target_content_hash`
- `CorrectionRecord.target_content_hash`
- `DatasetSnapshot.manifest_hash`

## Accepted P3 set

`P3_COUNT = 3`; no item was added, removed, redefined, or repaired by this freeze:

1. S13 formatter debt — exactly nine inherited files.
2. S16 Golden fixture coverage.
3. MetricDefinition ORM metadata drift — `current_version_id` ORM FK metadata is
   absent while the live database FK exists.

## Phase boundary

Phase 2 is **not** authorized by this freeze. The excluded Phase 2 objects remain:

- `ScientificConclusionVersion`
- `Publication`
- `ManuscriptVersion`
- `InternalReviewRecord`
- `DecisionRecord`
- `ApprovalRequest`
- `ApprovalDecision`
- `ApprovalGrant`
- `SubmissionVersion`

`PHASE_2_AUTHORIZED = NO`.

The next gate is an independent Phase 1 Freeze v4 review.
