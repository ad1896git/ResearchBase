# B23 Novelty Review and Revision-result Integration Contract — DRAFT

**Status: APPROVED by owner 2026-10-19 — first slice authorized for implementation**

## Start here (for the implementer)

B23 proposes review of one **exact NoveltyAssessment**, including its saved
ClaimVersion, SearchCoverage and selected prior-art basis. Reviewing its Claim
alone does not review that assessment. It also proposes a separately admitted
completed revision shape, `NOVELTY_REASSESSMENT`, referring to a previously
recorded replacement assessment. This is a proposed extension to RevisionAction,
not an eighth result already authorized by PR2-15.

Build only after owner approval, architecture/hash admission and separate
implementation authorization, in this order:

1. Register the exact review target and new result shape (§§5, 9, 11.1).
2. Add versioned material and closed DTOs without changing old hashes (§11).
3. Add one forward migration, typed FKs and deferred guards (§12.1).
4. Extend existing services, ports and repositories, using the prescribed
   transactions and lock order (§§12.2–3).
5. Add thin API/CLI adapters, error parity and the tests in §12.4.
6. Record actual checks, review findings and migration evidence; stop (§9).

Five rules fail review if broken:

1. The target is the assessment ID **and hash**, never a Claim ID, current
   comparison selection, search text or an artifact containing an assessment.
2. A completed reassessment must already exist and directly supersede the exact
   reviewed assessment for the same exact ClaimVersion. No automatic creation.
3. The seven existing action shapes and their v1 bytes remain unchanged. The new
   shape needs explicit admission and v2 material; no generic result locator.
4. Review and re-review correspondence never close an Issue, change a novelty
   finding, authorize release or override deterministic facts.
5. Every new write takes its fixed table SHARE inventory as the FIRST statement
   in a READ COMMITTED UoW. Reads use one REPEATABLE READ snapshot with no table,
   advisory or row locks.

Use the [glossary](#10-glossary), [pinned decisions](#11-decisions-taken-in-this-draft)
and [implementation guide](#12-implementation-guide--after-separate-authorization)
as construction references. This document changes no executable contract and
does not declare B23, PR2-15 or Phase 2 accepted.

## 1. Purpose, authority and inspected baseline

Read authority in AGENTS.md order. The table separates existing rules from the
proposed additions; reference drafts' historical baseline paragraphs are not a
description of today's implementation.

| Source | Rule or observed boundary |
| --- | --- |
| [AGENTS.md](../../AGENTS.md), §§2–11; Architecture [01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 6.7–6.9, 7–12 | One owner, immutable exact provenance, common Application boundary; Review != Decision != Approval. Reuse existing assessment/relation patterns. |
| Addendum [02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A3–A4, A10, A18–A23; Registry [03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md) | Concrete references, literature-owned assessments and separately governed review/revision history. No generic target/result JSON. |
| Compatibility [08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md); Phase 2 [05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §25, PR2-14/15/18, P2-INV-017 | Preserve historical contracts and Phase 1; novelty strength cannot exceed coverage. |
| [Harness 09](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 15, 18–19 | Candidate output enters through Application commands; tool/reviewer output is not scientific truth. |
| Corrections [12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), §§4, 7; [13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md), governance/novelty rows; [17](../architecture/17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md), §4 | Exact immutable assessment; finite seven RevisionAction shapes. Neither novelty review target nor novelty result is admitted there. |
| Hash [15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md), common encoding and governance templates; [18](../architecture/18_Phase2_Design_R3_Targeted_Remediation_v1.0.md); Temporal [19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md), TEMP-AUTH-01 | Preserve literal payloads; incompatible material requires ADR and a new version. Fresh trusted authorization time follows all blocking locks. |
| [PR2-17](PR2-17_Submission_Authorship_Contract_DRAFT.md); [PR2-18](PR2-18_Novelty_PriorArt_Contract_DRAFT.md), §§2, 12.5 | Structural models for this draft; PR2-18 explicitly prohibits inferring an eighth PR2-15 shape. No submission work imported. |
| [B18](B18_Novelty_Coverage_Completion_Contract_DRAFT.md), [B19](B19_Close_Prior_Art_Basis_Contract_DRAFT.md), [B21](B21_Unresolved_Count_Capture_Contract_DRAFT.md), [B22](B22_PriorArt_Correction_Selection_Contract_DRAFT.md); [novelty domain](../../src/researchbase/domain/novelty.py), [service](../../src/researchbase/application/novelty.py) | Implemented dependencies: selected coverage, positive close-art basis, historical resolution capture, comparison correction chains. Current material dispatch admits INCONCLUSIVE/v1 and CLOSE_PRIOR_ART_FOUND/v2; negative outcome remains denied. |
| [review domain](../../src/researchbase/domain/internal_review.py), [service](../../src/researchbase/application/internal_review.py), [repository](../../src/researchbase/persistence/internal_review_repository.py) | Material supports Claim, conclusion, manuscript and artifact targets; public create supports the first three. No NoveltyAssessment target. Initial Issues and separate disposition already exist. |
| [revision domain](../../src/researchbase/domain/revision_action.py), [service](../../src/researchbase/application/revision_action.py); [Decision service](../../src/researchbase/application/decision.py) | B06 completed results and B07 REVISION_RESPONSE Decisions/correspondence operate on Claim/conclusion concerns. `ACTION_SHAPES` has seven entries, seven concrete result columns, no novelty result. |
| [decision repository](../../src/researchbase/persistence/decision_repository.py), [novelty repository](../../src/researchbase/persistence/novelty_repository.py); migrations [0042](../../migrations/versions/0042_pr2_15_minimal_decision.py), [0052](../../migrations/versions/0052_b07_revision_decisions.py), [0068](../../migrations/versions/0068_b21_unresolved_capture.py) | Reuse SHARE-first snapshot writes, deferred completeness, existing re-review relation and native-xid sealing. No new persistence mechanism. |

The inspected migration sequence ends at `0068_b21_unresolved_capture.py`.
Choose the next revision from the actual single head at implementation time;
this draft reserves no number and is not a target execution pack.

## 2. Scope, dependency boundaries and non-goals

Propose three writes: create an exact novelty review, record an issue-only
completed novelty reassessment action, and link an independent exact re-review
to that action. Provide exact-ID historical review/action reads and exact
action/re-review link readback. Reuse InternalReviewRecord, ReviewIssue,
RevisionAction and `revision_action_re_reviews`; add columns, not a parallel
NoveltyReview or NoveltyRevision entity.

B18/B19/B21/B22 own assessment creation, closure, warnings and corrections.
B06/B07 own completed-action history and concern correspondence; their existing
Claim/conclusion behavior remains intact. B23 does not extend their Decision
basis or infer that their current validators accept a novelty concern.

The proposed first slice deliberately requires an explicit ReviewIssue basis
and no Decision on the new action. Novelty-specific REVISION_RESPONSE Decisions,
NO_CHANGE, Issue disposition and blocking-issue resolution require a subsequent
contract. They deny before writing here. A nonblocking or blocking Issue may
record a completed reassessment and re-review link, but remains OPEN.

## 3. Invariants and conservative judgments

1. A novelty review stores one exact `novelty_assessment_id` FK and its own
   `target_content_hash`. The Claim is reached through that assessment, not a
   second review target FK. Project ownership comes from Claim ownership.
2. Recompute the assessment, coverage, selected comparisons, evidence and
   resolution hashes through `NoveltyService._view` in the caller's UoW.
   Refactor a typed in-UoW entrypoint if needed; never call a public read that
   opens another transaction. Preserve B21's captured counts, including legacy
   NULL, and B22's saved comparison refs. Never substitute current terminals.
3. An intact superseded or currently unusable assessment remains reviewable and
   readable as history. Current usability/warnings are separate observations,
   not changed outcome/hash. Broken closure fails closed. A result admitted for
   a new action must be usable and have no assessment successor at admission.
4. Reviewer is a currently authenticated HUMAN OWNER or REVIEWER, distinct from
   the assessment's `assessed_by`, `created_by` and underlying ClaimVersion's
   `created_by`. These finite independence checks are proposed B23 policy;
   they do not claim scientific agreement or exhaustive conflict detection.
5. New reassessment result R must have `R.supersedes_assessment_id = A.id`, where
   A is the assessment targeted by the Issue's original review. Same Project
   and same **ClaimVersion**, not merely same Claim identity. R must already be
   committed before recording the action. R's admitted outcome may equal A's;
   its new record is an attributable reassessment, not proof the concern was
   fixed. IDs/times alone do not establish a scientific improvement.
6. Action correction chains retain exactly the same Issue basis and null
   Decision. Corrections still satisfy rule 5; they cannot relabel a descendant
   assessment as a direct replacement. A later reassessment is reviewed in a
   new concern rather than rewriting this one. Existing unique predecessor
   constraints prevent action forks; assessment uniqueness prevents two direct
   successors. No time-based winner or mutable current pointer is added.
7. Re-review must target R exactly, with R's saved hash, and be a different
   record from the original review. Its HUMAN reviewer also differs from the
   action creator. A link records correspondence even for REJECT/UNCERTAIN;
   it asserts neither acceptance nor disposition. Linked review Issues remain
   visible. Later result/comparison invalidity never deletes the link.
8. Review creation, action recording and link recording are separate commands
   and transactions. None creates a replacement assessment, changes evidence,
   marks an Issue ADDRESSED/DISMISSED, or invokes approval/publication commands.

### 3.1 Coverage and correction boundaries

Review preserves selected coverage and its failures/uncertainty. The current
`NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE` enum remains unavailable; ACCEPT is a review
recommendation, not a stronger novelty outcome. Prior-art corrections preserve
old assessment inputs and may make their current judgment unusable. A reviewed
assessment never follows a corrected comparison automatically. New result
admission uses existing B19/B22 checks; it does not resolve independent roots or
require B22 UNIQUE when B19 permits explicit selection.

### 3.2 Prior-art comparison is not the review target

A PriorArtRelation, SearchCoverage or ClaimVersion can be cited in the saved
assessment's closure, but none substitutes for that assessment. Direct reviews
of these other novelty objects and batch/list/latest review APIs are excluded.

### 3.3 Completed result admission

`NOVELTY_REASSESSMENT` is the proposed new shape, with exactly one new concrete
result FK and all seven legacy result columns NULL. It is unavailable until
§9's admission. It cannot be encoded as SOURCE_CHANGE, CLAIM_CHANGE,
MANUSCRIPT_CHANGE, NO_CHANGE, a result artifact or a generic JSON field.

## 4. Proposed commands, DTOs and historical readback

Extend `InternalReviewService.create` with `target_kind=NOVELTY_ASSESSMENT` and
the normal project, exact target, review content, Issues and request UUID.
Extend its exact `read` dispatch; use the existing actor/project/deployment/
request-derived UUID5 identity (`pr214:...`), comparing **ordered normalized
Issue contents as well as review material** on replay.

Add `RecordNoveltyRevisionCommand` to `application/revision_action.py`, handled
by the existing RevisionActionService through a separately typed method
`record_novelty_revision`. Do not weaken RecordRevisionActionCommand's seven
shapes. Extend `read_revision_action` to dispatch to a distinct novelty readback.
Reuse `record_concern_re_review` and `RecordConcernReReviewCommand` with a B23
dispatch; retain their exact action/review pair identity. Add a bounded
`read_novelty_re_review(principal, project_id, revision_action_id,
internal_review_record_id)` query. The existing aggregate
`get_concern_carry_forward` is not an exact-pair read and is not silently extended.

| Operation | Proposed adapter surface (all new, not current routes/groups) |
| --- | --- |
| Review write/read | `POST /projects/{project_id}/novelty-reviews`, `GET /projects/{project_id}/novelty-reviews/{id}`; `researchbase novelty-review record` / `show`. |
| Completed reassessment write/read | `POST /projects/{project_id}/novelty-revision-actions`, `GET /projects/{project_id}/novelty-revision-actions/{id}`; `researchbase novelty-revision record` / `show`. |
| Correspondence write/read | `POST` / `GET /projects/{project_id}/novelty-revision-actions/{id}/re-reviews/{review_id}`; `researchbase novelty-revision link` / `show-link`. No new link store. |

No InternalReviewService/RevisionActionService adapters were found in current
`api/routes.py` or `cli/commands/`; add the proposed thin surfaces in §12.3.
POST returns 201, GET 200. Review/action POST bodies contain §11.3 command fields
except path project; review target_kind is fixed by this route. Link POST has
no body: both exact IDs are in the path. CLI uses `--project-id` and the DTO's
kebab-case field flags; ordered Issues use a closed JSON input, not text IDs.
All use trusted principal injection; callers cannot supply reviewer/creator IDs,
hashes, timestamps or material versions. Exact reads share the existing project
entitlement checks; denied nested dependencies deny the entire response.

Replay requires current live authentication and project read entitlement, same
actor/project/request material, and verified saved closure. Changed material is
IDEMPOTENCY_CONFLICT; another actor/project gets FORBIDDEN without disclosure.
Completed replay does not require current writer authority, independent-review
eligibility, OPEN status, terminal result or current usability again. Return
saved material with freshly observed diagnostics; never rerun effects.

## 5. Schema and literal hash proposal — one forward migration; no new table

The proposed forward migration adds nullable `internal_review_records.novelty_assessment_id`
and `revision_actions.result_novelty_assessment_id` RESTRICT FKs and indexes,
adds `material_version SMALLINT NOT NULL DEFAULT 1` to both tables, replaces
their target/action CHECKs with version-aware CHECKs admitting novelty-only v2,
and extends review/revision/re-review and Issue/event guards as specified in §12.1.
[ADR-0019](../architecture/adr/ADR-0019-novelty-review-target.md) proposes the required
amendments to frozen contracts 13/15/17. No new
canonical table, JSON collection, receipt, queue, cache or event-sourcing layer.

For new novelty reviews only, use the exact `review_material` object from
`domain/internal_review.py`, with `material_version=2` and target
`R(NoveltyAssessment)`. Every other key remains exactly as in v1. Existing review
targets continue v1; no historical digest is recomputed with v2.

New action material is the following **entire** payload. R(T) is the exact
`{type,id,content_hash}` reference; I(T) is `{type,id}`. No other keys enter it.

```text
{
  "type": "RevisionAction", "material_version": 2,
  "review_issue": I(ReviewIssue), "decision": null,
  "action_type": "NOVELTY_REASSESSMENT",
  "results": {
    "result_experiment_spec_version": null, "result_run": null,
    "result_statistical_result": null, "result_claim_version": null,
    "result_scientific_conclusion_version": null,
    "result_manuscript_version": null, "result_source_version": null,
    "result_novelty_assessment": R(NoveltyAssessment)
  },
  "supersedes_revision_action": R(RevisionAction) | null,
  "created_by": I(ActorIdentity)
}
```

Use existing canonical JSON/NFC and `sha256-cjson-v1`. Exclude own row ID,
project (derived via Issue), timestamps and current diagnostics, matching the
existing action material convention. New target/result membership is typed and
SQL-guarded. Existing action v1 retains exactly seven result keys, including
NO_CHANGE's nulls; a new nullable DB column never enters old material.
Unknown versions fail PROVENANCE_CLOSURE_VIOLATION. The existing re-review
relation has attribution/time and FKs, not an invented content hash.

## 6. Error contract — proposed use of existing categories

Use §11.2's literal mappings from the current adapters. No new ErrorCode or
HASH_MISMATCH alias. Distinguish absent inputs, denied scope, unsupported paths,
and corrupt saved closure. No raw SQL, constraint message, credential detail or
hidden foreign identifier may appear in error envelopes.

## 7. Transactions, concurrency and failure recovery

One command equals one synchronous PostgreSQL transaction. Fixed mutable-fact
SHARE locks precede operational SETs, authentication queries, advisory locks and
row locks (§12.2). Reserve owning-table ROW EXCLUSIVE modes before target/FK
locks; never put a table written by any B23 command into the shared inventory.
Use explicit target-before-review/Issue ordering and reread after waits.

After all blocking locks, obtain `clock_timestamp()` and check live credentials,
HUMAN/roles, active project/membership and half-open effective intervals. Repeat
after a later wait and immediately before the effect/commit. Transaction-start
`now()` and caller time cannot make the final authorization decision.

Force deferred constraints before response and commit; no partial review,
Issue/OPEN event, action or link may survive failure. Retry fresh UoWs at most
three total attempts for SQLSTATE 40001/40P01 only. A predecessor unique race
maps to CONCURRENT_MODIFICATION without retrying a different predecessor.
55P03/57014, connection errors and uncertain commit are not automatic retries.
Use exact identity replay after uncertain commit; never invent a new request ID.

Reads, including history/provenance/link reads, use a single read-only
REPEATABLE READ UoW. No calls to write preparation, target lock helpers, table
locks, advisory locks or SELECT FOR UPDATE/SHARE. Recompute historical material
and current diagnostics in that snapshot, checking current entitlement before
disclosure. Historical author/role eligibility is checked at creation time;
later role loss never rewrites a saved review.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

Test exact target binding, literal material versions, DTO closure, immutable
history, direct SQL guards, independent review, replay and races (§12.4).
No B23 behavior is implemented or tested by this documentation task. Existing
dependency regressions provide baseline evidence only.

## 9. Acceptance criteria and evidence boundary

Two explicit admissions are required before implementation: (1) NoveltyAssessment
as an InternalReviewRecord target with review material v2; (2) the new completed
`NOVELTY_REASSESSMENT` action shape/result FK and action material v2. Record them
in an approved ADR and amendments to the registered 13/15/17 contracts, with
compatibility vectors and owner sign-off. Neither this draft nor B19/B21/B22's
material admission supplies those decisions. If the owner approves only review,
the revision part remains unavailable; do not implement a partial result facade.

Then obtain a target execution pack/implementation authorization. Acceptance
requires all §12.4 cases and required architecture/static checks on PostgreSQL
18.x, clean upgrade, guarded downgrade, restart/replay and controlled lock
evidence, plus review with no open P0/P1. Record exact commands/counts and all
skips/failures. Scope stops at the three bounded writes/reads; no Phase gate or
whole-suite PASS can be inferred from this document.

## 10. Glossary

| Term | Meaning here |
| --- | --- |
| Exact novelty target | Immutable NoveltyAssessment ID and saved content hash; its Claim/coverage/basis are dependencies, not interchangeable targets. |
| Assessment / comparison / coverage | Literature-owned NoveltyAssessment / PriorArtRelation / SearchCoverage, verified by the current novelty service. |
| Completed reassessment | A previously committed replacement assessment directly superseding the reviewed assessment; no plan or reviewer suggestion. |
| Shape admission | Explicit architecture/owner approval of the concrete new result tuple and literal hash payload; different from approving this prose or implementing it. |
| Concern / correspondence | Original ReviewIssue / immutable link proving an exact re-review targets the action's completed result. Neither implies Issue disposition. |
| R(T) / I(T) | Hashed frozen reference / identity-only reference under Hash Contract 15. |
| v1 / v2 | Literal material encodings; not scientific confidence or lifecycle states. |
| Current usability | Existing NoveltyReadback diagnostic, observed now in the read snapshot; saved findings/hashes stay unchanged. |
| SHARE-first / UoW | Fixed PostgreSQL table-lock statement before any other transaction statement / one Application command transaction. |
| Deferred completeness | DEFERRABLE INITIALLY DEFERRED constraint trigger verifies the full inserted relation set, also forced before commit; pattern in migration 0042. |
| NFC / UTC / DTO | Unicode normalization / timezone-aware instant / closed typed transport/application value. |
| P0 / P1 / P2 / P3 | BLOCKER / MAJOR / MINOR / SUGGESTION findings under AGENTS.md. |

## 11. Decisions taken in this draft

These are pinned **proposals**, awaiting owner approval, not assertions that
current code or architecture already admits B23.

### 11.1 Scope and policy decisions

1. Review target spelling is `NOVELTY_ASSESSMENT` in adapters/readback and
   `NoveltyAssessment` in hashed references. It is an immutable record, with no
   fabricated FROZEN status or NoveltyAssessmentVersion.
2. Novelty reviews use the existing six review types and five recommendations;
   Issues use the existing ten types and four severities (§11.3). All initial
   statuses are OPEN. This does not introduce a NOVELTY review_type.
3. The new result is issue-only: explicit Issue, null Decision, exactly one
   concrete novelty result. Existing seven action shapes stay under v1 dispatch.
   Wrong/no-change/decision-only novelty paths deny before persistence.
4. Fresh review/result/link admission and historical readback use separate
   validators. Old assessment usability may be false; new result usability must
   be true. Completed history does not become unreadable because it is stale.
5. Link attribution follows B07: the authenticated HUMAN OWNER/REVIEWER recording
   the link must be the new review's reviewer and satisfy its independence checks.
   Link recording alone never requires ACCEPT or closes any Issue.
6. No new runtime dependency or top-level canonical schema is needed. [ADR-0019](../architecture/adr/ADR-0019-novelty-review-target.md)
   must admit the bounded column/hash extensions; existing generality is not
   permission to bypass the finite result contract.

### 11.2 Pinned error mappings

These match [api/errors.py](../../src/researchbase/api/errors.py) and
[cli/errors.py](../../src/researchbase/cli/errors.py). Their existing review
mapping comments remain provisional; B23 does not resolve that architecture
question by changing mappings.

| Code | HTTP | CLI exit | B23 trigger |
| --- | --- | --- | --- |
| AUTHENTICATION_REQUIRED | 401 | 3 | Missing/invalid trusted principal. |
| FORBIDDEN | 403 | 3 | Current scope/role/credential denied; foreign actor/project replay. |
| CONFLICT_OF_INTEREST | 403 | 3 | Reviewer overlaps the prohibited authors/action creator. |
| VALIDATION_ERROR | 422 | 2 | Unknown field, bad UUID/enum/type, text/Issue limit or malformed result tuple. |
| NOT_FOUND | 404 | 3 | Entitled exact input absent. |
| REVIEW_TARGET_NOT_FROZEN | 409 | 4 | Required underlying ClaimVersion has no frozen material at review admission. An assessment itself has no freeze transition. |
| FROZEN_REFERENCE_REQUIRED | 409 | 5 | Required result dependency lacks frozen material. |
| INVALID_STATE_TRANSITION | 409 | 4 | Unavailable novelty Decision/disposition/no-change path, nonterminal/unusable result, non-OPEN new action concern, used predecessor. |
| DECISION_BASIS_INVALID | 409 | 4 | A supplied existing Decision does not concern the exact novelty Issue; novelty Decision integration remains deferred. |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Hash/version corruption, wrong exact Claim/project/direct successor, altered sealed history, mismatched re-review result. |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Same entitled actor/request identity with changed normalized content, including Issue order. |
| IMMUTABLE_RECORD | 409 | 4 | UPDATE/DELETE of scientific history or late Issue/event insertion. |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Sanitized concrete FK violation. |
| CONCURRENT_MODIFICATION | 409 | 4 | Exhausted 40001/40P01 attempts or unique predecessor race. |
| INTERNAL_ERROR (fallback, not ErrorCode) | 500 | 1 | Unexpected/timeout/connection/unknown-commit failure, sanitized using existing adapter fallbacks. |

Malformed command shapes fail VALIDATION_ERROR first. A well-typed but deferred
command fails INVALID_STATE_TRANSITION; an unrelated supplied Decision fails
DECISION_BASIS_INVALID. Corrupt saved material always fails closed, not as a
client validation error. Authorization precedes any absent/foreign disclosure.

### 11.3 DTO fields, Python types, limits and enums

Use frozen slotted dataclasses and strict transport models (`extra='forbid'`).
UUIDs are exact `uuid.UUID` values; wire text must round-trip to lowercase
hyphenated form. Hashes are 64 lowercase hex `str`; timestamps aware UTC
`datetime.datetime`; version values strict `int` (never bool).

| DTO | Exhaustive fields (existing named types are reused) |
| --- | --- |
| NoveltyReviewCommand (typed facade for create) | `project_id: UUID`, `target_kind: Literal['NOVELTY_ASSESSMENT']`, `target_id: UUID`, `review_type: ReviewType`, `recommendation: Recommendation`, `summary: str`, `issues: tuple[ReviewIssueRequest, ...]`, `request: UUID`. |
| ReviewIssueRequest | `severity: Severity`, `issue_type: IssueType`, `description: str`. |
| RecordNoveltyRevisionCommand | `id: UUID`, `project_id: UUID`, `review_issue_id: UUID`, `result_novelty_assessment_id: UUID`, `supersedes_revision_action_id: UUID \| None = None`. Fixed action_type NOVELTY_REASSESSMENT; Decision and all legacy result fields absent from this DTO. |
| RecordConcernReReviewCommand / exact-pair read arguments | `project_id: UUID`, `revision_action_id: UUID`, `internal_review_record_id: UUID`; no caller actor/time/hash. |
| ExactReadQuery | `project_id: UUID`, `id: UUID` (review ID or action ID, separate methods). |
| NoveltyReviewReadback | All existing InternalReviewReadback fields (`id`, `project_id`, `target_id`, `reviewer_actor_id`: UUID; `target_content_hash`, `review_type`, `recommendation`, `summary`, `content_hash`, `target_kind`: str; `issues: tuple[ReviewIssueReadback, ...]`), plus `material_version: Literal[2]`, `target: NoveltyReadback`. Fixed target_kind NOVELTY_ASSESSMENT. |
| ReviewIssueReadback | Existing `id: UUID`, `severity: str`, `issue_type: str`, `description: str`, `status: str`, with the closed values below. |
| NoveltyRevisionReadback | `id: UUID`, `project_id: UUID`, `review_issue_id: UUID`, `result_novelty_assessment_id: UUID`, `supersedes_revision_action_id: UUID \| None`, `created_by: UUID`, `created_at: datetime`, `action_type: Literal['NOVELTY_REASSESSMENT']`, `material_version: Literal[2]`, `content_hash: str`, `hash_scheme: Literal['sha256-cjson-v1']`, `original_review: NoveltyReviewReadback`, `result: NoveltyReadback`, `predecessor: NoveltyActionRef \| None`, `has_superseding_action: bool`. |
| NoveltyActionRef | `type: Literal['RevisionAction']`, `id: UUID`, `content_hash: str`. |
| NoveltyReReviewReadback | `project_id: UUID`, `revision_action_id: UUID`, `internal_review_record_id: UUID`, `recorded_by: UUID`, `recorded_at: datetime`, `action: NoveltyRevisionReadback`, `review: NoveltyReviewReadback`. |

Use distinct readback types for new variants so existing positional constructors
and old DTO contracts need not change. `NoveltyReadback` and all nested types are
the **current** closed classes in `application/novelty.py`, including
`material_version`, B19 basis/scope/criteria, B21 captured counts and current
quality/validity. No duplicate B23 novelty DTO or untyped dict core.

Summary and Issue descriptions follow `domain/internal_review._text`: NFC,
nonblank, 1–16,000 characters, strict UTF-8; additionally reject NUL at the
boundary (PostgreSQL TEXT cannot store it). Preserve meaningful whitespace.
Issues: ordered tuple of 0–100, contiguous ordinals 0..N-1; no truncation.
New admission validates at most 10,000 distinct dependency records, counting
each `(type,id)` once; excess is VALIDATION_ERROR before writes. Historical
verification must not truncate or apply that new admission cap retroactively.

Closed literals (reuse existing domain sets, define type aliases if useful):

- ReviewType: SCIENTIFIC, STATISTICAL, LITERATURE, REPRODUCIBILITY, EDITORIAL,
  COMPREHENSIVE.
- Recommendation: ACCEPT, MINOR_REVISION, MAJOR_REVISION, REJECT, UNCERTAIN.
- Severity: INFO, MINOR, MAJOR, BLOCKING.
- IssueType: UNSUPPORTED_CLAIM, CITATION, STATISTICAL, METHODOLOGICAL,
  REPRODUCIBILITY, OVERCLAIM, CONTRADICTION, NOVELTY, WRITING, OTHER.
- Issue status: OPEN, ADDRESSED, DISMISSED as existing history values; B23 creates
  OPEN only and does not admit either disposition for novelty-target Issues.
- NoveltyOutcome: INCONCLUSIVE, CLOSE_PRIOR_ART_FOUND,
  NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE; the last stays unavailable.
- Legacy action types: NEW_EXPERIMENT, ANALYSIS_CHANGE, CLAIM_CHANGE,
  CONCLUSION_CHANGE, MANUSCRIPT_CHANGE, SOURCE_CHANGE, NO_CHANGE. Preserve their
  current admission restrictions; B23 does not activate deferred manuscript work.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

One additive migration after the actual head; never edit accepted migrations.
Types and new constraint names are pinned below. Existing row IDs, attribution,
timestamps, hashes and RESTRICT FKs stay in place.

```sql
ALTER TABLE internal_review_records
  ADD COLUMN novelty_assessment_id UUID
    CONSTRAINT fk_b23_review_novelty REFERENCES novelty_assessments(id) ON DELETE RESTRICT,
  ADD COLUMN material_version SMALLINT NOT NULL DEFAULT 1;
ALTER TABLE internal_review_records DROP CONSTRAINT ck_pr214_one_target;
ALTER TABLE internal_review_records ADD CONSTRAINT ck_b23_review_target CHECK (
  num_nonnulls(manuscript_version_id,claim_version_id,
    scientific_conclusion_version_id,artifact_version_id,novelty_assessment_id)=1),
  ADD CONSTRAINT ck_b23_review_version CHECK (
    (material_version=1 AND novelty_assessment_id IS NULL) OR
    (material_version=2 AND novelty_assessment_id IS NOT NULL));
CREATE INDEX ix_b23_review_novelty ON internal_review_records(novelty_assessment_id);

ALTER TABLE revision_actions
  ADD COLUMN result_novelty_assessment_id UUID
    CONSTRAINT fk_b23_result_novelty REFERENCES novelty_assessments(id) ON DELETE RESTRICT,
  ADD COLUMN material_version SMALLINT NOT NULL DEFAULT 1;
ALTER TABLE revision_actions DROP CONSTRAINT revision_action_shape;
ALTER TABLE revision_actions ADD CONSTRAINT ck_b23_revision_shape CHECK (
  (material_version=1 AND result_novelty_assessment_id IS NULL
   AND num_nonnulls(result_experiment_spec_version_id,result_run_id,
     result_statistical_result_id,result_claim_version_id,
     result_scientific_conclusion_version_id,result_manuscript_version_id,
     result_source_version_id) = CASE action_type
       WHEN 'NEW_EXPERIMENT' THEN 2 WHEN 'NO_CHANGE' THEN 0 ELSE 1 END
   AND (
     (action_type='NEW_EXPERIMENT' AND result_experiment_spec_version_id IS NOT NULL
       AND result_run_id IS NOT NULL) OR
     (action_type='ANALYSIS_CHANGE' AND result_statistical_result_id IS NOT NULL) OR
     (action_type='CLAIM_CHANGE' AND result_claim_version_id IS NOT NULL) OR
     (action_type='CONCLUSION_CHANGE' AND result_scientific_conclusion_version_id IS NOT NULL) OR
     (action_type='MANUSCRIPT_CHANGE' AND result_manuscript_version_id IS NOT NULL) OR
     (action_type='SOURCE_CHANGE' AND result_source_version_id IS NOT NULL) OR
     action_type='NO_CHANGE')) OR
  (material_version=2 AND action_type='NOVELTY_REASSESSMENT'
   AND result_novelty_assessment_id IS NOT NULL
   AND review_issue_id IS NOT NULL AND decision_record_id IS NULL
   AND num_nonnulls(result_experiment_spec_version_id,result_run_id,
     result_statistical_result_id,result_claim_version_id,
     result_scientific_conclusion_version_id,result_manuscript_version_id,
     result_source_version_id)=0));
CREATE INDEX ix_b23_result_novelty ON revision_actions(result_novelty_assessment_id);
```

The v1 branch is equivalent to the seven-branch predicate in
[0044](../../migrations/versions/0044_pr2_15_revision_action.py): required concrete
columns plus the exact nonnull count prohibit every extra result column.
Include a cross-product equivalence test; this is no expansion of v1 admission.

`action_type VARCHAR(32)` already fits. Retain
`uq_revision_action_predecessor` and `uq_pr218_novelty_predecessor` unchanged.
No action-result uniqueness is invented: multiple independent concerns may cite
the same exact completed reassessment.

Guard construction, in dependency order:

| Function / trigger name | Required behavior |
| --- | --- |
| `b23_prelocked()` | Reuse the `pr218_capture_prelocked()` pattern: require READ COMMITTED and the complete N SHARE inventory for new write guards. Do not add advisory locks to reads or use transaction-local flags as proof of locks. |
| `b23_review_guard` / `trg_b23_review_guard` BEFORE INSERT | For v2 verify exact assessment/hash/project, frozen Claim closure, historical authorship eligibility, target XOR and text/enum bounds. Extend existing review guard dispatch so legacy functions do not reject or reinterpret a novelty target. Existing immutable-review guard remains. |
| `b23_complete_review` / `b23_complete_review_record`, `b23_complete_review_issue`, `b23_complete_review_event` | DEFERRABLE INITIALLY DEFERRED AFTER INSERT on parent/Issue/event respectively; require 0–100 sealed Issues, contiguous ordinals, exactly one initial OPEN event per Issue with matching actor/time. Existing normal late-insert guards must dispatch to novelty, not only the deferred checker. Use native `xmin = pg_current_xact_id()::xid` for same-transaction children, as 0068; no bigint xid workaround. |
| `b23_validate_revision` / `trg_b23_revision_guard` BEFORE INSERT | Verify new shape, exact Issue/review/assessment binding, same exact Claim/project, directly superseding result committed in a prior transaction (`result.xmin IS DISTINCT FROM pg_current_xact_id()::xid`), intact result closure/current usability and no successor, OPEN concern, same-basis predecessor chain/no fork; verify v2 hash. Retain existing UPDATE/DELETE rejection. Dispatch B06/B07 validators for legacy v1, not for the new shape. |
| `b23_complete_revision` / `b23_complete_revision_action` AFTER INSERT | DEFERRABLE INITIALLY DEFERRED; repeat exact result/basis and v2 hash completeness checks at commit. Extend `b06_revision_complete` dispatch so it does not also apply Claim/conclusion assumptions to v2. |
| `b23_validate_re_review` / existing `b07_re_review_guard`, `b07_complete_re_review` dispatch | Verify exact result-target/hash, original concern, different review and independent HUMAN reviewer, action/link actor/time, immutable relation and project closure. Keep existing B07 behavior for legacy actions. No new link table. |

The B08 Issue/event guard dispatch must explicitly deny ADDRESSED/DISMISSED
for novelty-target Issues, including normal-role SQL attempts; Application
rejection alone is insufficient. Legacy Issue disposition remains unchanged.

Use 0042's deferred constraint-trigger mechanism, including forced checks. Every
INSERT path, including normal-role SQL, enforces relational closure, result
shape, immutable material and hash/version dispatch. SQL does not pretend to
verify a live external credential or artifact bytes; those remain Application
checks. Reuse existing SQL canonical hash helpers and owning novelty verifiers,
with independent Python/SQL golden vectors. No SECURITY DEFINER bypass.

Forward migration preflight verifies the expected current guard definitions;
inventory every replaced function and dependent trigger. Legacy function bodies
must be restored exactly on downgrade. Downgrade takes ACCESS EXCLUSIVE on the
changed owners/link tables first and refuses if **any** v2 review/action or link
to one exists; it never deletes history to make schema rollback succeed.

### 12.2 Exact lock order and transactions

Define `B23_SNAPSHOT_TABLES` as exactly the fixed tuple `N` in
`src/researchbase/persistence/novelty_repository.py`, listed lexically there;
pin equality in a test, with no runtime catalog discovery. N protects
author/authority, mutable validity, resolution and evidence observations.
Immutable assessment/coverage/comparison material needs no extra table SHARE.
Assessment/comparison **successor admission** is serialized by the same exact
ClaimVersion FOR UPDATE taken by `novelty_repository.prepare` for non-coverage
writes. B23 takes that lock before checking terminals or result usability.
Do not add `novelty_assessments` or `prior_art_relations` to N: an existing
novelty writer can already hold the Claim row before its INSERT obtains ROW
EXCLUSIVE; adding SHARE here would invert that order and deadlock.

The inventory also deliberately excludes `internal_review_records`, `review_issues`,
`review_issue_events`, `revision_actions`, `revision_action_re_reviews`: these
are B23 owning write tables. Immutable referenced material needs no table lock;
mutable Issue projection is reread under the specific row lock below.

For **each new write**, set SQLAlchemy connection isolation before statements;
the literal FIRST SQL transaction statement is:

```sql
LOCK TABLE <B23_SNAPSHOT_TABLES in lexical order> IN SHARE MODE;
```

Next take the command's owning-table reservation listed below, then
`SET LOCAL lock_timeout='10s'`, `SET LOCAL statement_timeout='30s'`, then request
advisory lock using `pg_advisory_xact_lock(hashtextextended(:key,0))`. These are
the existing PostgreSQL mechanisms, not a SERIALIZABLE substitute. `BEGIN` and
connection isolation setup do not permit a preliminary SELECT or SET LOCAL
before the SHARE statement.

| Command | Exact subsequent order (each arrow is a separate step) |
| --- | --- |
| Create novelty review | ROW EXCLUSIVE reservation on `internal_review_records,review_issue_events,review_issues` (lexical order) → SETs → `pr214:review:{derived_review_id}` advisory → read entitlement/replay check → underlying exact ClaimVersion FOR UPDATE → target assessment FOR SHARE → reread assessment/Claim/closure → fresh HUMAN reviewer/independence authorization → insert review, ordered Issues and OPEN events → force constraints → readback/final authorization → commit. |
| Record novelty revision | ROW EXCLUSIVE reservation on `revision_actions` → SETs → `pr215:revision:{command.id}` advisory → read entitlement/replay check → underlying ClaimVersion FOR UPDATE → original/result assessment rows FOR SHARE in UUID order → original review FOR SHARE → concern Issue FOR SHARE → predecessor action FOR UPDATE if supplied → reread Issue status, predecessor/successor facts and full closure → fresh OWNER/RESEARCHER authorization → insert action → force constraints → readback/final authorization → commit. |
| Link novelty re-review | ROW EXCLUSIVE reservation on `revision_action_re_reviews` → SETs → `b23:re-review:{action_id}:{review_id}` advisory → read entitlement/replay check → underlying ClaimVersion FOR UPDATE → original/result assessments FOR SHARE in UUID order → original/new reviews FOR SHARE in UUID order → original Issue FOR SHARE → action FOR SHARE → reread exact correspondence/action successor state → fresh HUMAN OWNER/REVIEWER authorization with caller equal to new reviewer → insert link → force constraints → readback/final authorization → commit. |

On first-time action/link admission require the action predecessor/action to be
non-superseded as applicable; replay is historical (§4). Before obtaining row
locks resolve IDs through plain reads, without disclosing foreign objects.
The SHARE inventory stabilizes ownership/authority; the Claim row lock
stabilizes assessment/comparison successor checks. Do not
lock parent Claim, Project or authority rows after these target locks; they are
table-protected. SQL trigger lock paths use the same ordering and introduce no
late parent locks. Own-table reservations occur before all FK/target row locks
to avoid the existing writer-order inversion documented in the repositories.

Do not change legacy review/Decision/revision protocols silently. Exercise
their concurrent interactions with these commands. If an owning legacy trigger
would take a later lock in reverse order, reconcile its explicitly scoped
dispatch and tests in the authorized pack before implementation proceeds.
Every read and exact history replay implemented as a read uses only the
snapshot protocol in §7; a write-endpoint replay retains the write preamble
but performs no mutation and requires only current read entitlement.

### 12.3 Ordered build steps and module paths

1. Obtain §9 admissions and an execution pack; verify head with
   `uv run alembic heads`. Amend registered contracts/ADR in that later PR.
2. Extend `src/researchbase/domain/internal_review.py` with versioned target
   material and `domain/revision_action.py` with a separate v2 material builder,
   exact references and correspondence policy. Keep v1 functions/vectors intact.
3. Extend `src/researchbase/application/internal_review.py`,
   `application/revision_action.py`, `application/novelty.py` and
   `application/ports.py`: closed DTOs, version dispatch, shared in-UoW novelty
   verification, historical/current split, direct-successor relevance and
   re-review checks. Reject unsupported Decision/disposition before writes.
   Do not make Domain depend on ORM, adapters or Skills.
4. Add the next forward file under `migrations/versions/`; extend
   `src/researchbase/persistence/internal_review_repository.py`,
   `persistence/revision_action_repository.py`, `persistence/novelty_repository.py`
   and `persistence/uow.py`. Separate read methods from lock helpers; wire
   constraint-specific error normalization and bounded retries.
5. Wire `src/researchbase/api/routes.py`, `api/app.py`,
   `cli/commands/governance.py`, `cli/composition.py`, `cli/transport.py` and
   `cli/main.py`. Add the narrowly scoped groups/routes in §4 following existing
   Typer registration, service composition and sanitized error patterns. Human/Agent
   callers use the same service; no direct adapter persistence access.
6. Add §12.4 tests, update the migration inventory and API/CLI contract docs in
   that implementation PR; run focused checks and required accepted regressions,
   record evidence, review and stop. No dependencies or infrastructure added.

### 12.4 Test artifacts and required cases

New test filenames below are planned; existing files are regression references.

| Test file(s) | Required cases |
| --- | --- |
| `tests/unit/phase2/test_b23_novelty_review_contract.py` | All DTO fields/enums; strict UUID/int/bool; NFC/NUL/UTF-8; 16,000/16,001 text; 0/100/101 Issues; wrong target; separate seven-shape/new-shape dispatch; admission cap and untruncated legacy history. |
| `tests/unit/phase2/test_b23_hash_vectors.py` | Literal review v2 and action v2 independently expected bytes/digests; all nullable keys; exact result/predecessor refs; no own ID/time/diagnostics; all existing v1 review/action vectors unchanged; unknown versions denied. |
| `tests/architecture/test_b23_novelty_boundaries.py` | Domain isolation, common Application boundary, no generic ref/new entity, no extra action via old command, no locks on any read path; first SHARE and fixed inventory/own-table exclusion for every new write. |
| `tests/integration/phase2/test_b23_novelty_review.py` | INCONCLUSIVE and CLOSE_PRIOR_ART_FOUND exact targets; old v1/v2 coverage, B21 captured count NULL vs zero; selected B19 basis and B22 corrections; stale/superseded assessment remains reviewable; independent HUMAN and foreign scope denials; zero/ordered Issues and atomic OPEN events. |
| `tests/integration/phase2/test_b23_novelty_revision.py` | Precommitted direct same-ClaimVersion result; unrelated Claim/version/project, root result, self-result, indirect descendant, same-transaction result and unusable/superseded result denied; all seven legacy result columns NULL; action correction same-basis/no fork; Decision-only/NO_CHANGE/disposition deny; Issue remains OPEN. |
| `tests/integration/phase2/test_b23_re_review.py` | Exact result-target/hash link; different review; independent reviewer including action creator check; wrong branch/Claim/assessment denied; ACCEPT/MINOR_REVISION/REJECT/UNCERTAIN correspondence, visible new Issues, no automatic closure/approval; original review untouched. |
| `tests/integration/phase2/test_b23_schema.py` | Catalog names/types/FKs/RESTRICT/indexes, XOR and version cross-product; normal-role direct SQL bypass attempts; deferred incomplete parent/child/events/result/link; post-commit child INSERT and UPDATE/DELETE denial; Python/SQL hashes; data-preserving upgrade, empty downgrade/round trip and history-present refusal. |
| `tests/integration/phase2/test_b23_replay.py` | Restart all three readbacks; actor/project entitlement; changed normalized summary/Issue order/result/predecessor; concurrent same-key exact replay; completed replay after writer role loss/result supersession; no second effect; unavailable nested source denies whole response; injected corrupt hashes/edges fail closed. |
| `tests/integration/phase2/test_b23_concurrency.py` | First-statement trace for each writer; held required locks with observed PostgreSQL wait PIDs; correction/retraction/evidence revocation and role expiry races; two action predecessors, action correction vs link; B07 Decision/B08 disposition and old review/novelty writers vs B23; FK reservation order and bounded retry/rollback. Cross-expiry evidence captures transaction-start and post-lock clock_timestamp; reads finish under held conflicting locks and emit no explicit locks. |

Run static checks and unit/architecture tests. Relevant existing PostgreSQL
regressions include `test_pr2_14_internal_review.py`,
`test_pr2_14_conclusion_review.py`, `test_pr2_15_decision.py`,
`test_pr2_15_coordination.py`, `test_revision_action.py`,
`test_b06_revision_action.py`, `test_b06_revision_concurrency.py`,
`test_b07_revision_decisions.py`, `test_b07_concern_carry_forward.py`,
`test_b07_concurrency.py`, the `test_pr2_18_*.py`,
`test_b19_close_prior_art_*.py`, `test_b21_capture*.py` and
`test_b22_prior_art_*.py` suites under `tests/integration/phase2/`.
These are a future verification plan, not a report that they passed here.

### 12.5 Not in this slice

- Novelty-target Decision bases, NO_CHANGE, automatic issue disposition or
  permission to dismiss/resolve blocking concerns.
- Direct PriorArtRelation/SearchCoverage review targets, new negative novelty
  outcomes, exhaustive screening, priority proof or latest-wins selection.
- New assessment creation inside review/revision commands; Claim/source/
  manuscript changes represented as novelty results.
- Approval/grant changes, release/READY transitions, submissions/external sends,
  generic workflow/agent runtime, new persistence service or dependency.
- Rewriting accepted migrations, v1 hashes or old scientific/review history.

## 13. Open questions for the owner — override register

The draft pins a bounded answer for each item, so no implementer chooses policy
implicitly. Owner overrides require an updated draft/admission before code.

| Decision requiring approval | Proposed answer |
| --- | --- |
| Exact review target | NoveltyAssessment only; permit intact stale/superseded history, expose current diagnostics separately. |
| New result admission | Separately admit NOVELTY_REASSESSMENT/v2, issue-only, precommitted direct same-ClaimVersion replacement. Keep the seven legacy shapes unchanged. |
| Decision/disposition reach | Defer novelty Decision/NO_CHANGE/disposition; completed result and correspondence leave all novelty Issues OPEN. |
| Independence | HUMAN OWNER/REVIEWER, independent of assessment authors and Claim author; re-review also independent of action creator. |
| Approval scope | Approve this contract and [ADR-0019](../architecture/adr/ADR-0019-novelty-review-target.md)'s amendments to frozen contracts 13/15/17 explicitly, then separately authorize an execution pack; approval does not declare acceptance. |

## 14. Historical proposal-only verification note

The following records the earlier proposal-only task, before implementation authorization.
Current implementation evidence, review findings and recorded substitutions are in
[the B23 implementation evidence](../verification/b23/implementation-evidence.md).

That earlier task added only this proposal. No migration, production code, tests,
governing contract or dependency file is changed. Verification commands and
observed counts follow (2026-10-19); unavailable PostgreSQL execution is not a
PASS. The loop owns the subsequent whole-suite run; it was not run here.

The checkout has no `.venv`; commands used the existing parent-repository
environment without changing repository configuration. Exact static commands:

```sh
/Users/fengwang/Documents/ResearchBaseProject/.venv/bin/ruff format --check . && /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/ruff check . && /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/pyright
/Users/fengwang/Documents/ResearchBaseProject/.venv/bin/pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject
/Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python -m alembic heads
```

Formatting: **736 files already formatted**; Ruff: **All checks passed**.
Initial Pyright: **1,332 errors, 2 warnings**, unresolved environment imports.
Explicit-environment Pyright: **0 errors, 0 warnings, 0 informations**.
Alembic: **0068_b21_unresolved_capture (head)**, one head.

```sh
PYTHONPATH=src /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python -m pytest tests/unit tests/architecture tests/test_architecture.py -ra
```

**5,630 passed, 5 failed, 14 errors, 9 warnings**. Four runner failures are
socket-bind PermissionError; static-acceptance failure invokes Pyright without
the explicit environment path. Architecture database fixtures require an
explicit disposable admin URL. A diagnostic rerun confirmed these conditions:

```sh
PYTHONPATH=src /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python -m pytest tests/unit/phase2/test_pr2_04_static_acceptance.py::test_candidate_static_gates_and_inherited_formatter_delta tests/unit/test_hg1_runner.py::test_v2_denial_keeps_versioned_fail_closed_response tests/unit/test_hg1_runner.py::test_socket_lifecycle_one_request_and_cleanup tests/unit/test_hg1_runner.py::test_foreign_peer_policy_denies_before_frame_without_using_request_slot tests/unit/test_hg1_runner.py::test_incomplete_owner_frame_cannot_extend_runner_past_deadline tests/architecture/test_pr2_19_boundaries.py::test_literature_source_not_evidence --tb=short -ra
```

Diagnostic result: **5 failed, 1 error, 1 warning**. No fixes to unrelated code or
environment files were made. Focused dependency contract/boundary checks:

```sh
PYTHONPATH=src /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python -m pytest tests/unit/phase2/test_pr2_18_novelty_contract.py tests/unit/phase2/test_pr2_18_hash_vectors.py tests/unit/phase2/test_b19_close_prior_art_contract.py tests/unit/phase2/test_b19_close_prior_art_hash_vectors.py tests/unit/phase2/test_b21_capture_contract.py tests/unit/phase2/test_b21_capture_hash_vectors.py tests/unit/phase2/test_b22_prior_art_contract.py tests/unit/phase2/test_b22_prior_art_hash_vectors.py tests/unit/phase2/test_revision_action.py tests/unit/phase2/test_b07_revision_decisions.py tests/architecture/test_pr2_18_boundaries.py tests/architecture/test_b19_close_prior_art_boundaries.py tests/architecture/test_b21_capture_boundaries.py tests/architecture/test_b22_prior_art_boundaries.py tests/architecture/test_b06_revision_action.py tests/architecture/test_b07_revision_decisions.py -ra
```

**208 passed**. PostgreSQL-focused attempt:

```sh
PYTHONPATH=src DATABASE_URL='postgresql+psycopg:///postgres?host=/private/tmp' /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python -m pytest tests/integration/phase2/test_pr2_18_novelty.py tests/integration/phase2/test_b19_close_prior_art_basis.py tests/integration/phase2/test_b21_capture.py tests/integration/phase2/test_b22_prior_art_correction.py tests/integration/phase2/test_pr2_14_internal_review.py tests/integration/phase2/test_b06_revision_action.py tests/integration/phase2/test_b07_revision_decisions.py -ra --maxfail=1
```

**1 setup error, 1 warning, no passing cases**; stopped immediately because the
sandbox denied connection to `/private/tmp/.s.PGSQL.5432` (Operation not
permitted). The remaining selected PostgreSQL cases were not executed.
Direct `psql -h /private/tmp -p 5432 -d postgres -Atc 'SHOW server_version'`
likewise failed; no running-server version is claimed.

A read-only Python inspection resolved **35 local Markdown links**, verified
all **14 numbered sections**, and compared all **14 ErrorCode HTTP/CLI rows**
with the imported adapter dictionaries. `git diff --check` reported no errors;
the new file is also checked directly against `/dev/null` before handoff.
