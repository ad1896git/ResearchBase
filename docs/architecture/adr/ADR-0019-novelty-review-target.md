# ADR-0019 — Novelty review target and reassessment result

Status: ACCEPTED — APPROVED by owner 2026-10-19; first slice authorized for implementation.

## Context

[B23](../../proposals/B23_Novelty_Review_Revision_Contract_DRAFT.md) needs review of one exact
NoveltyAssessment and a completed revision referring to its exact replacement.
Reviewing a ClaimVersion does not bind its assessment, coverage or saved prior-art
basis. Frozen [Field Contract 13](../13_Phase2_Schema_Field_Contract_v1.0.md)
does not admit this review target/result; [Hash Contract 15](../15_Phase2_Hash_Payload_Contract_R2_v1.0.md)
fixes both governance payloads at v1; [Governance Contract 17 §4](../17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md#4-completed-revisionaction-results-p1-10)
admits exactly seven action shapes. Existing generality cannot authorize an eighth.

Following [ADR-0017](ADR-0017-novelty-material-v2.md), this
proposal requests explicit bounded amendments without editing frozen numbered
contracts. It remains a draft in `docs/proposals/`; owner approval and separate
implementation authorization are required. No Phase 2 gate result is implied.

## Decision

### 1. Admit an exact NoveltyAssessment review target

Propose amending Contract 13's InternalReviewRecord target XOR with nullable
`internal_review_records.novelty_assessment_id UUID`, a concrete RESTRICT FK to
`novelty_assessments(id)`. Adapter target kind is `NOVELTY_ASSESSMENT`; hashed
reference type is `NoveltyAssessment`. Store and verify its exact saved hash,
with project derived through its exact ClaimVersion. No second Claim target,
NoveltyAssessmentVersion, fabricated freeze status or new review entity.
Intact stale/superseded history remains reviewable; current diagnostics stay
separate. B23's independent HUMAN review policy and saved closure checks apply.

### 2. Admit one completed RevisionAction shape

Propose amending Contracts 13 and 17 §4 with `NOVELTY_REASSESSMENT` and nullable
`revision_actions.result_novelty_assessment_id UUID`, a concrete RESTRICT FK to
`novelty_assessments(id)`. Require an explicit ReviewIssue and null Decision;
all seven legacy result columns are NULL. The result must already be committed,
usable and non-superseded at admission, and directly supersede the assessment
targeted by the Issue's original review for the same exact ClaimVersion/project.
Action corrections retain that same Issue/null Decision and direct replacement
rule. No automatic assessment creation or claim of scientific improvement.

Reuse `revision_action_re_reviews` for a different independent review targeting
the exact result ID/hash. Correspondence records no acceptance, Issue disposition,
novelty outcome change, approval or release. Novelty Decision bases, NO_CHANGE
and ADDRESSED/DISMISSED remain deferred. The seven legacy shapes are unchanged.

### 3. Amend Contract 15 with two exact v2 payloads

These are the **entire** material objects. R(T) expands to
`{"type":"T","id":"<uuid>","content_hash":"<digest>"}` and I(T) to
`{"type":"T","id":"<uuid>"}`. Angle-bracket tokens below are typed
placeholders, not literal strings in material. Preserve Contract 15's UUID,
NFC, null and canonical JSON encoding and `hash_scheme=sha256-cjson-v1`.
Templates are not byte/digest fixtures; independent literal vectors are required
by B23 §12.4 after implementation authorization.

**InternalReviewRecord — novelty targets only:**

```json
{"type":"InternalReviewRecord","material_version":2,"project_id":"<uuid>","target":"<R(NoveltyAssessment)>","reviewer_actor_id":"<uuid>","review_type":"<ReviewType>","recommendation":"<Recommendation>","summary":"<NFC string>"}
```

All keys except material version and the newly admitted target type match v1.
`target_content_hash` equals `target.content_hash`. Review types/recommendations
remain B23 §11.3's existing closed enums. Own row ID, timestamps, Issues and
current diagnostics do not enter this payload; ordered Issues retain their
separate immutable storage and replay checks.

**RevisionAction — NOVELTY_REASSESSMENT only:**

```json
{"type":"RevisionAction","material_version":2,"review_issue":"<I(ReviewIssue)>","decision":null,"action_type":"NOVELTY_REASSESSMENT","results":{"result_experiment_spec_version":null,"result_run":null,"result_statistical_result":null,"result_claim_version":null,"result_scientific_conclusion_version":null,"result_manuscript_version":null,"result_source_version":null,"result_novelty_assessment":"<R(NoveltyAssessment)>"},"supersedes_revision_action":"<R(RevisionAction)|null>","created_by":"<I(ActorIdentity)>"}
```

Keep every shown null key. Exclude own row ID, project (derived through Issue),
timestamps and current diagnostics. Verify each referenced object's saved
material version/hash before embedding its reference. Re-review relations keep
their existing attribution/time and FKs; no link content hash is introduced.

**V1 compatibility:** existing rows and stored hashes remain byte-identical in
their scientific material; label them v1 without rewriting facts or recomputing
digests. Legacy review targets and all seven legacy action shapes continue to
write v1. V1 action material retains exactly seven result keys: never append
`result_novelty_assessment: null`. New nullable columns do not enter v1 material.
Readers and replay dispatch on each saved version, including nested novelty
v1/v2 and predecessor refs; never upgrade the same UUID on replay. Unknown
versions fail PROVENANCE_CLOSURE_VIOLATION. Deploy dual readers before v2 writers;
old readers are unsupported for v2. Later invalidity affects current projections,
not saved bytes, hashes or correspondence.

### 4. One forward migration; no new table

After separate authorization, use the actual single Alembic head and B23 §12.1's
DDL/guard inventory. Add the two concrete indexed FKs above and
`material_version SMALLINT NOT NULL DEFAULT 1` to each owning table. Replace
`ck_pr214_one_target` with `ck_b23_review_target` plus `ck_b23_review_version`,
and `revision_action_shape` with `ck_b23_revision_shape`. Admit only novelty v2;
prove the v1 seven-shape predicate equivalent. Retain RESTRICT, immutable history,
predecessor uniqueness and existing Issue/re-review tables. Extend legacy guard
dispatch and add B23 deferred closure/hash guards without weakening v1 behavior.
No canonical table, generic locator or persistence infrastructure is added.

Preflight verifies expected guard definitions. Downgrade first locks changed
owners/link tables ACCESS EXCLUSIVE and refuses any v2 review/action or link to
one; otherwise restore replaced legacy functions/CHECKs exactly and remove only
owned additions. Never delete or rehash history to permit rollback.

## Consequences

Literature remains the assessment owner; governance stores exact review and
completed-change provenance through the common Application boundary. Deterministic
facts still outrank review. B23 §12.4 requires independent v1/v2 vectors,
mixed-version reads/replay, real PostgreSQL constraints/deferred guards,
history-preserving upgrade/downgrade refusal, authorization and concurrency
tests. These are future requirements, not results of this documentation change.
This ADR proposes Phase 2 contract amendments only; no runtime dependency,
external effect or approval authority is added.

## Alternatives

- Review only the ClaimVersion: loses the exact assessment and its saved basis.
- Encode reassessment as CLAIM_CHANGE, SOURCE_CHANGE, NO_CHANGE or an artifact:
  misstates the completed result and bypasses the finite action contract.
- Add keys to v1 or rehash old records: breaks frozen references and history.
- Add NoveltyReview/NoveltyRevision tables or generic result JSON/soft locators:
  duplicates existing governance patterns or weakens concrete FK provenance.
- Follow current/latest assessment or auto-close Issues after re-review: changes
  historical meaning and confuses correspondence with disposition/authority.
