# Manuscript Validity and Audit Projection (B25) — DRAFT

**Status: APPROVED by owner 2026-10-17 — first slice authorized for implementation**

## Start here (for the implementer)

B25 adds two exact-manuscript Application queries: current validity with upstream
audit witnesses, and recorded unsupported-assertion concerns. Both read one
PostgreSQL snapshot. Neither records an assessment nor changes scientific history.
An empty concern list means no recorded concern in this scope, not that every
sentence is supported. A VALID result means the accepted closure readers found no
current invalidity; it is not review acceptance or permission to submit.

Build in this order after contract approval **and separate implementation authorization**:

1. Confirm B04 and the accepted validity readers against §1; retain their hashes
   and validity semantics (§3). No migration is needed (§12.1).
2. Add closed query/result DTOs and bounds (§11.3), then the same-UoW collector
   (§12.3). Use exact frozen manuscript IDs, never a current-version selector.
3. Add nonlocking repository selects and compose all verification in one
   REPEATABLE READ, READ ONLY transaction (§12.2).
4. Verify seals, upstream states and review/Issue witnesses; preserve each
   placement occurrence, including repeated use of one target (§3).
5. Run focused contract, architecture and real PostgreSQL tests (§12.4), record
   exact evidence and stop. Adapters and later workflow remain outside (§12.5).

The five review rules:

1. Deterministic facts outrank review, Decision and Approval.
2. Citation and rhetorical strength never create support.
3. Historical hashes and exact dependency IDs remain unchanged after invalidation.
4. Every read uses one snapshot and no explicit table, advisory or row locks.
5. Return a complete bounded result or a named error; never silently omit a broken
   branch, concern or audit witness.

Read §§1–4 first; use the glossary (§10), pinned decisions (§11) and construction
details (§12) as lookup material. This proposal is documentation only, not an
execution pack, architecture amendment or B25 acceptance declaration.

## 1. Purpose, authority and inspected baseline

| Authority | Rule carried into B25 |
| --- | --- |
| [System Architecture 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), deterministic facts, frozen provenance and §73 | Validity is derived from retained facts; invalidation does not rewrite scientific values. |
| [Correction Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md) and [Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), Phase2-Core | Existing Entity/Relation/Assessment patterns suffice; manuscript placements hold concrete frozen references, citations confer no support. |
| [Cross-Phase Contracts 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), invariants and G3 | Manuscript is not scientific truth; stale history remains traceable; Application boundaries and existing contracts remain compatible. |
| [Phase 2 Specification 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §§36–38 | Read retraction, stale/invalid Claims, unsupported placements and unresolved issues independently of authority. |
| [Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), §§4–7; [Field Contract 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md); [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md) | Recompute literal hashes and exact closure; distinguish retained material integrity from current validity. |
| [Gap Closure R2 14](../architecture/14_Phase2_Design_Gap_Closure_R2_v1.0.md), §§2–3 | Retraction, dispute, correction and invalid Claim dependencies propagate through support snapshots and Conclusions to manuscripts without changing old bytes. |
| [Harness Specification](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 15, 19 | Skill output is candidate material; no direct canonical persistence; executed evidence precedes completion. |

Inspected prerequisites, not inferred milestone acceptance:

- [B04 Application](../../src/researchbase/application/manuscript_freeze.py),
  [repository](../../src/researchbase/persistence/manuscript_freeze_repository.py)
  and [0048](../../migrations/versions/0048_b04_manuscript_freeze.py) implement
  initial sealing, exact reads, CAS verification and current validity. Manuscript
  status is currently only DRAFT/FROZEN; freeze supersession is not implemented.
- [Scientific trace](../../src/researchbase/application/manuscript_scientific_trace.py)
  exposes exact placement, Conclusion→Claim, experimental and literature paths.
  It labels citation `CITATION_ONLY` and other placement `PLACEMENT_ONLY`.
- [Governance queries](../../src/researchbase/application/governance_queries.py)
  supply `validity_projection_in_uow`, including finding, assessment and correction
  IDs. [GovernanceTargetType](../../src/researchbase/domain/governance.py) has eight
  Phase 1 kinds, **no ManuscriptVersion, Conclusion or SourceVersion target**.
- [Literature readers](../../src/researchbase/application/literature_evidence.py)
  and [Conclusion reader](../../src/researchbase/application/scientific_conclusion.py)
  verify retained hashes and derive literature/support validity. B25 must retain
  their state distinctions rather than treating every non-VALID state as INVALID.
- [Internal reviews](../../src/researchbase/application/internal_review.py),
  [repository](../../src/researchbase/persistence/internal_review_repository.py)
  and [0049](../../migrations/versions/0049_b05_manuscript_review.py) provide
  manuscript reviews and OPEN Issue history. `manuscript_reviews()` currently
  uses FOR SHARE and is **not suitable for B25 reads**. Issue disposition is not
  implemented by these readers; B25 does not implement the B08 draft.

The [PR2-17](PR2-17_Submission_Authorship_Contract_DRAFT.md) and
[PR2-18](PR2-18_Novelty_PriorArt_Contract_DRAFT.md) proposals provide this document's
structure, not authority to extend their workflows. There is no B25 execution pack
in this checkout. Proposed choices below require owner approval.

## 2. Scope, dependency boundaries and non-goals

First slice: `get_manuscript_validity` and `get_manuscript_audit`, both scoped by
Project, Publication and exact FROZEN ManuscriptVersion. B04 and accepted validity
readers are required. The audit query additionally reuses the shipped PR2-14/B05
review verifier. If those prerequisites change before authorization, reconcile
this contract first. Do not implement missing dependencies here.

No new persistence, canonical target kinds, write commands, global downstream
search, prose parser, model evaluation or automatic unsupported-claim detector.
This reads downstream impact **at a specified manuscript** through its existing
upstream graph; it does not extend PR-14's downstream-impact API to publication.

## 3. Invariants and conservative judgments

### 3.1 Exact closure and current validity

Verify B04's document bytes/size/hash, placement-set hash, content hash, typed
same-project closure and frozen references in the caller's UoW with
`admission=False`. Use the existing protected, nonlocking adapters. Never invoke
a public service method that opens another UoW. Preserve Phase 1 hashes and R2
support bindings exactly; current pointers are not dependency selectors.

Aggregate all verified dependency states using B04's order-independent rule:
INVALID or RETRACTED → INVALID; otherwise any non-VALID → STALE; otherwise VALID.
For governance projections: `invalid` → INVALID; `not_assessed` or `unaffected`
with no correction IDs → VALID; all other states or corrections → STALE.
Retain the original governance state and IDs alongside the aggregate. In
particular NOT_ASSESSED is not an assertion that a reviewer validated the work.

Collect states over the whole B04 graph, not only direct placements: Claim
evidence, StatisticalResult inputs, Measurement/metric, Run and sealed inputs;
bound support snapshots, Conclusion inputs, literature verification and source
lineage/artifacts. Follow B04's distinction between retained predecessor history
and material validity: verifying a predecessor does not make it the current
source's validity owner. Do not bind a newer support snapshot or corrected source
by navigation. Repeated uses produce separate witnesses, not extra scientific
facts. Merge every branch before aggregation so input iteration order cannot
hide INVALID behind STALE.

Integrity failure (missing concrete edge, wrong project, malformed seal, hash/CAS
mismatch or cyclic lineage) is an error, not a successful INVALID projection.
After the initial scoped lookup, normalize nested NOT_FOUND or saved-review
target-state failures to PROVENANCE_CLOSURE_VIOLATION; they describe broken saved
closure, not an absent user-selected manuscript.
Genuine later staleness/invalidity with intact historical closure is returned as
data. No invalidity projection updates lifecycle, hashes, content or pointers.

### 3.2 Unsupported-assertion and audit reads

Audit scope is all exact reviews of this manuscript and every ClaimVersion or
ScientificConclusionVersion reachable through its scientific placements and
Conclusion Claim inputs. Scope is version identity, not parent identity or shared
source coincidence. Select review rows through their concrete target columns;
never guess scope from Issue description, locator text or related-ID hints.

Verify each review's literal hash, target hash and historical reviewer binding
through existing verification helpers. Read **all** its Issues and initial events
before filtering. Require the shipped OPEN-only structure: contiguous per-review
ordinals, valid enums/NFC text, exactly one root OPEN event per Issue, null prior
status, matching reviewer actor and Issue creation time. Apply these structural
checks to Claim/Conclusion issues too; B05's `_issues` currently adds them only
for manuscript reviews. Do not claim the review content hash seals Issue text;
the current review hash payload excludes the Issue set.

Return `UNSUPPORTED_CLAIM` Issues as recorded concerns, regardless of severity.
Return all OPEN/BLOCKING Issue IDs separately, regardless of issue type. Concern
presence neither changes deterministic validity nor becomes canonical proof of
unsupportedness. `OVERCLAIM`, contradiction, unverified/disputed evidence and
stale dependencies remain distinct facts in the trace/validity output; do not
relabel them as `UNSUPPORTED_CLAIM`. Citation-only or empty-placement manuscripts
can have an empty concern set; they do not thereby acquire positive support.

One upstream concern may have several occurrence paths; retain every path. For a
manuscript-level Issue return no invented sentence/placement attribution. The
present Application creates null Issue locators, so B25 returns the recorded
description and review target rather than constructing a prose location.

## 4. Proposed commands, DTOs and historical readback

There are no commands. Both queries accept the same closed UUID triple (§11.3)
and an out-of-band `VerifiedPrincipal`. Return immutable typed DTOs, never ORM
rows. The audit result embeds the validity result and the existing scientific
trace DTO from the **same** snapshot; it adds concerns and blocking Issue IDs.

Authorize with B04's nonlocking authority helper and publication `_READERS`:
active HUMAN with OWNER/RESEARCHER/REVIEWER/VIEWER/APPROVER role, live membership,
subject binding and credential. This preserves current publication policy; it
does not add Agent read authority. Authenticate before target lookup; return
NOT_FOUND for missing or incorrectly scoped Publication/manuscript. Recheck fresh
DB time and credential validity before return. Archived-project reads follow
B04's existing reader policy. No writer/reviewer role is required just to read.

DRAFT yields VERSION_NOT_FROZEN. A persisted manuscript status outside the shipped
DRAFT/FROZEN vocabulary is a closure failure; future SUPERSEDED support requires
its own approved lifecycle contract. Exact FROZEN dependencies may themselves be
SUPERSEDED where the owning verifier already accepts retained material.

Repeated queries recompute current facts; there is no idempotency receipt or
stored projection. `evaluated_at` is the final fresh UTC database time, not a
durable snapshot identity or a promise about commits after snapshot acquisition.

## 5. Schema and literal hash proposal — no migration

No new tables, columns, materialized views, triggers, projection cache, events or
hash scheme. Derived DTOs are not canonical records and have no content hash.
Existing manuscript/review hashes and Issue/event IDs are returned unchanged.
The DDL inventory in §12.1 is explanatory, not executable migration authorization.

## 6. Error contract — proposed use of existing categories

Use only §11.2 codes and existing transport mappings. STALE, INVALID, recorded
unsupported concerns and an empty concern list are successful query results.
Never return partial success on integrity or completeness failure.

## 7. Transactions, concurrency and failure recovery

Each query owns one fresh REPEATABLE READ, READ ONLY UoW configured before its
first data query, including authorization (§12.2). No explicit table, advisory or
row locks, temporary writes, receipts, event appends or commits with side effects.
PostgreSQL's ordinary SELECT ACCESS SHARE locks are not explicit table locking.

A concurrent correction, retraction, Issue INSERT or placement writer can commit
while the reader is open. The query sees one complete snapshot-visible graph;
the next query may differ. Credential checks use advancing time but database
membership/binding rows remain snapshot-visible. Do not claim linearizable
revocation visibility beyond this accepted read protocol. Missing/corrupt CAS
bytes fail verification; PostgreSQL isolation does not snapshot external files.

Retain UoW sanitized error normalization. An aborted transaction returns no DTO;
do not catch a failed branch and continue or turn connection loss into VALID.
The caller can issue a fresh query; no new retry or persistence mechanism is added.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

Test complete old/new snapshots with barriers on separate PostgreSQL connections,
not timing-only sleeps. Assert nonblocking reads, preserved bytes and exact audit
paths, as well as ordinary success/error behavior. File plan and cases: §12.4.
The present documentation change adds no executable tests or product behavior.

## 9. Acceptance criteria and evidence boundary

Implementation acceptance requires both closed queries, complete bounded witnesses,
unchanged hash semantics, explicit lock-free snapshot evidence and all §12.4
checks on PostgreSQL 18.x. No open P0/P1 review finding; source presence and draft
approval alone are not acceptance. Stop after the authorized slice's evidence.
This document's verification is recorded in §14 and does not accept B25 runtime.

## 10. Glossary

| Term | Meaning here |
| --- | --- |
| Seal / integrity | Exact frozen material, retained bytes and literal hashes resolve and verify. |
| Current validity | Derived VALID/STALE/INVALID over the accepted dependency readers. |
| Audit witness | Existing finding/assessment/correction IDs or source/evidence state reached by exact provenance. |
| Unsupported concern | Recorded OPEN `UNSUPPORTED_CLAIM` ReviewIssue; an attributed assessment. |
| Occurrence path | One direct placement plus its exact typed intermediate references to the affected node. |
| Complete result | All scoped rows and paths in one snapshot, within §11.3 limits; never a truncated sample. |

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

Pin two Application-only FROZEN-manuscript queries; no write, migration, runtime
dependency or new GovernanceTargetType. Keep deterministic validity separate from
recorded concerns and readiness. Reuse B04's graph and accepted owner verifiers,
with a same-UoW witness collector rather than a second scientific rules engine.
The collector must not change existing public DTOs or legacy query behavior.

### 11.2 Pinned error mappings

These match [HTTP errors](../../src/researchbase/api/errors.py) and
[CLI errors](../../src/researchbase/cli/errors.py). Adapters are deferred; the
mappings still pin the Application contract.

| Code | HTTP | CLI exit | Trigger |
| --- | --- | --- | --- |
| VALIDATION_ERROR | 422 | 2 | Wrong query type, extra fields, non-UUID inputs or caller-selected bounds/status/actor. |
| AUTHENTICATION_REQUIRED | 401 | 3 | No verified principal. |
| FORBIDDEN | 403 | 3 | Current reader entitlement or credential check fails. |
| NOT_FOUND | 404 | 3 | Exact scoped Publication/manuscript unavailable after authorization. |
| VERSION_NOT_FROZEN | 409 | 4 | DRAFT manuscript queried. |
| FROZEN_REFERENCE_REQUIRED | 409 | 5 | Referenced material is not frozen where an owner verifier requires it. |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Integrity failure, malformed saved review/Issue history, unsupported persisted shape, or complete-result ceiling exceeded. |
| CONCURRENT_MODIFICATION | 409 | 4 | Existing UoW-normalized concurrency/timeout failure; no partial result. |

Map nested saved-review REVIEW_TARGET_NOT_FROZEN to
PROVENANCE_CLOSURE_VIOLATION, following the existing manuscript review verifier.
Do not invent HASH_MISMATCH, MANUSCRIPT_INVALID or UNSUPPORTED_ASSERTION codes.
Unexpected failures retain existing INTERNAL_ERROR HTTP 500 / CLI 1 sanitation.

### 11.3 DTO fields, Python types and limits

All new DTOs are frozen/closed. UUID fields require `type(value) is UUID`, not
UUID-looking strings; transports may parse canonical UUIDs if later authorized.
No caller-supplied timestamps, limits, actors, hashes or status. Reject bools as
integers. Output hashes are lowercase `[0-9a-f]{64}`; times are aware UTC.

| DTO | Exact fields |
| --- | --- |
| `GetManuscriptValidityQuery`, `GetManuscriptAuditQuery` | `project_id: UUID`, `publication_id: UUID`, `manuscript_version_id: UUID`. |
| `AuditNodeRef` | `kind: Literal['ManuscriptVersion','ArtifactVersion','ClaimVersion','ScientificConclusionVersion','LiteratureSupportSnapshot','LiteratureEvidence','SourceVersion','EvidenceRelation','StatisticalResult','Measurement','Run','MetricDefinitionVersion','DatasetSnapshot','ExperimentSpecVersion']`; `id: UUID`. A transient closed discriminated reference, never stored as a soft FK. |
| `AuditOccurrence` | `placement_kind: Literal['CLAIM','CONCLUSION','CITATION','ARTIFACT'] | None`, `placement_id: UUID | None`, `nodes: tuple[AuditNodeRef, ...]`. Both placement fields null only for manuscript/document-root paths; nodes are ordered root→affected node, with exact manuscript first. |
| `ManuscriptValidityWitness` | `node: AuditNodeRef`, `state: Literal['VALID','STALE','INVALID']`, `governance: ValidityProjection | None` (existing DTO, existing lowercase enum), `source_kind: SourceVersionKind | None` (existing enum: SUBMITTED/PREPRINT/REVISED_PREPRINT/ACCEPTED/PUBLISHED/CORRECTED/RETRACTED), `evidence_review_status: Literal['UNREVIEWED','VERIFIED','DISPUTED','REJECTED'] | None`, `occurrences: tuple[AuditOccurrence, ...]`. Source/evidence fields apply only to their corresponding node kinds; no free-form reason JSON. |
| `ManuscriptValidityReadback` | `project_id`, `publication_id`, `manuscript_version_id`: UUID; `status: Literal['FROZEN']`; `content_hash`, `placement_set_hash`: str; `current_validity: Literal['VALID','STALE','INVALID']`; `witnesses: tuple[ManuscriptValidityWitness, ...]`; `evaluated_at: datetime`. |
| `UnsupportedAssertionConcern` | `issue_id`, `review_record_id`: UUID; `review_target: AuditNodeRef` (manuscript/Claim/Conclusion only); `review_content_hash`, `target_content_hash`: str; `issue_type: Literal['UNSUPPORTED_CLAIM']`; `severity: Literal['INFO','MINOR','MAJOR','BLOCKING']`; `status: Literal['OPEN']`; `description: str`; `issue_ordinal: int`; `event_id`, `event_actor_id`: UUID; `occurred_at: datetime`; `occurrences: tuple[AuditOccurrence, ...]` (empty for manuscript-level concern). |
| `ManuscriptAuditReadback` | `validity: ManuscriptValidityReadback`, `trace: ManuscriptScientificTrace` (existing DTO), `unsupported_concerns: tuple[UnsupportedAssertionConcern, ...]`, `blocking_issue_ids: tuple[UUID, ...]`. |

Return witnesses for all visited validity-owning nodes, including VALID ones;
zero governance records stays explicit. Reference-only relation nodes can occur
in paths without claiming a validity assessment. Do not manufacture content hashes
for relation rows which have none. Evidence/source states preserve owner-reader
meaning; source retraction has INVALID precedence in B04's aggregate.

Limits proposed here, not assertions about current code: at most 10,000 placements
(B04's existing cap), 10,000 distinct visited nodes, 10,000 reviews, 10,000 Issues,
and 10,000 total occurrence paths across each response, each path at most 256
nodes. Check before unbounded allocation; fetch ceiling+1 for new row scans.
Issue descriptions retain existing NFC, strict UTF-8, nonblank 1..16,000 character
bound; ordinals are nonnegative. Oversize stored graphs fail closure, never return
truncated success. No pagination or client-adjustable ceilings in this slice.

Order witnesses by `(kind, UUID string)`, concerns by `(review UUID string,
issue_ordinal, issue UUID string)`, blocking IDs by UUID string. Deduplicate identical
paths only; order paths by placement kind (null first), placement UUID (null first),
then the tuple of node kind/UUID strings. Preserve distinct placement occurrences.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

**B25 DDL is empty.** Do not allocate a migration number or execute the following
inventory as DDL. Existing typed storage already represents every fact needed:

| Existing shape / type | Existing named constraint or guard retained |
| --- | --- |
| `manuscript_versions.id UUID`, `publication_id UUID`, `document_artifact_version_id UUID`; `status VARCHAR(16)`; hashes `CHAR(64)`; `frozen_at TIMESTAMPTZ` | `ck_b04_manuscript_status`, `ck_b04_manuscript_seal`; concrete RESTRICT FKs and `fk_pr212_current_same_parent`. |
| Three placement tables: exact manuscript/target UUID FKs, section/locator and integer ordinal | B04's `b04_complete_claim_placement`, `b04_complete_citation_placement`, `b04_complete_artifact_placement` deferred constraint triggers; sealed relation guards remain intact. |
| `internal_review_records`: project and four nullable concrete target UUIDs, target/content `CHAR(64)`, `hash_scheme VARCHAR(32)` | `ck_pr214_one_target`; B05's `b05_complete_review` deferred constraint trigger. |
| `review_issues`: `id UUID`, `review_record_id UUID`, `severity VARCHAR(16)`, `issue_type VARCHAR(32)`, `description TEXT`, `status VARCHAR(16)`, `ordinal INT` | Existing OPEN/type/severity checks, unique `(review_record_id,ordinal)` and `b05_complete_issue`. |
| `review_issue_events`: issue/actor UUIDs, prior/new `VARCHAR(16)`, `occurred_at TIMESTAMPTZ` | Existing unique issue/root OPEN checks and `b05_complete_issue_event`. |

See [0035](../../migrations/versions/0035_pr2_12_publication_draft.py),
[0040](../../migrations/versions/0040_pr2_14_initial_internal_review.py), 0048 and
0049. Their commit-time guards follow the existing DEFERRABLE INITIALLY DEFERRED
pattern, also used by `pr215_complete_decision`, `pr215_complete_conclusion` and
`pr215_complete_review` in [0042](../../migrations/versions/0042_pr2_15_minimal_decision.py).
B25 neither replaces those guards nor adds SQL hashing, a persisted validity
column, or a new canonical assertion table. Database guards do not replace
Application literal-hash/CAS verification on formal reads.

### 12.2 Exact lock order and transactions

| Operation | Exact ordered protocol |
| --- | --- |
| `get_manuscript_validity` | Validate closed input/principal → fresh UoW → B04 error normalization → `prepare_read()` executes `SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY` before any SELECT → `enable_revision_action_snapshot_reads()` → nonlocking authority plus fresh clock/credential check → scoped Publication and exact manuscript SELECTs → require FROZEN → same-UoW B04 integrity/validity traversal and witness collection → final nonlocking authority/fresh clock/credential check → construct DTO → close read UoW. |
| `get_manuscript_audit` | Same preparation/authentication/lookup → same-UoW validity collector → existing scientific trace builders on nonlocking exact rows → nonlocking SELECT of all scoped reviews ordered UUID → verify each review and all Issues/events in ordinal/UUID order → project concerns and blocking IDs with occurrence paths → enforce complete-result limits → final authority/time/credential check → return embedded DTOs → close read UoW. |

The lock sequence for both operations is **empty**: no `LOCK TABLE`,
`pg_advisory_xact_lock`, FOR UPDATE, FOR SHARE or project-lock helper. In
particular do not call public `trace()`, `get_manuscript_version()`, review `read()`
or `collect_manuscript_review_basis()` from inside these queries. Reuse their
same-UoW verification/building parts, not their transaction or write orchestration.
Add a nonlocking review selector rather than using existing `manuscript_reviews()`.

There is no B25 write lock order because there is no B25 write command. Do not
copy the Decision command's older ordering into readers. Any separately approved
future snapshot-consistent write must follow the existing B04/Novelty pattern:
READ COMMITTED, lexically sorted fixed inventory `LOCK TABLE ... IN SHARE MODE`
as the **FIRST SQL statement**, before limits, advisory/row locks or authority
queries; then its separately specified exact command lock order. This document
does not authorize such a command or invent a write inventory for it.

### 12.3 Ordered build steps and module paths

1. Reconcile this draft with shipped B04/readers and migration head. No migration
   or modification under `docs/architecture/` is expected.
2. **New** `src/researchbase/application/manuscript_validity.py`: §11 DTOs,
   `ManuscriptValidityService`, two public queries and a private same-UoW collector.
   Domain imports remain free of SQLAlchemy, FastAPI and Typer.
3. Refactor only as needed in existing
   `src/researchbase/application/manuscript_freeze.py` and
   `src/researchbase/application/manuscript_scientific_trace.py` to expose reusable
   same-UoW traversal/builders. Collect states/witnesses at existing verification
   sites; preserve old public results and hash payloads. Reuse
   `governance_queries.py:validity_projection_in_uow`, literature `_snapshot`/`_read`
   and Conclusion `_view(require_current=False)`; do not rely solely on a
   Conclusion's returned scalar where branch-order aggregation could mask INVALID.
4. Extend `src/researchbase/application/ports.py`'s `InternalReviewRepository`
   with a nonlocking exact-target review selector; implement in
   `src/researchbase/persistence/internal_review_repository.py`. Reuse concrete
   manuscript/Claim/Conclusion target columns, same-project joins and existing
   review/Issue/event indexes. No row locks or temporary target table. Share
   review verification from `application/internal_review.py`; add common pure
   OPEN-history checking without enabling disposition commands.
5. Reuse `src/researchbase/persistence/uow.py` and existing B04 read preparation,
   normalization and protected adapters. No new persistence mechanism or UoW
   factory inside the collector. Instantiate the new service via the existing
   factory, credential verifier and ArtifactStore ports; adapters are deferred.
6. Add §12.4 tests, run focused checks, record exact results, review for P0/P1 and
   stop. Changes to prerequisites that require new semantics return to contract
   review rather than expanding B25 silently.

### 12.4 Test artifacts and required cases

All **new** files below are future work after authorization:

| File | Required cases |
| --- | --- |
| `tests/unit/phase2/test_b25_manuscript_validity_contract.py` | Exact types/closed DTOs; enums, mappings, text/path/row boundaries and ceiling+1; deterministic sorting; INVALID dominates STALE in both branch orders; no-assessment/correction mapping; concern never changes scientific validity. |
| `tests/architecture/test_b25_boundaries.py` | Common Application boundary; no Domain infrastructure imports, new canonical schemas or migrations; one UoW; no explicit locks/writer helper/public nested queries; existing API/CLI mappings unchanged. |
| `tests/integration/phase2/test_b25_manuscript_validity.py` | B04-frozen empty/all-placement manuscripts; direct Claim and Conclusion paths; experimental upstream invalidation; metric/Run/input audit witnesses; source correction/retraction, disputed/rejected/unreviewed positive evidence and bound snapshot propagation; both mixed INVALID/STALE orders; corrected predecessors retain lineage semantics; unchanged hashes/bytes/pointers after query. DRAFT, wrong project/parent, missing target, broken FK graph, hash/size/CAS corruption and malformed seals fail by pinned codes. |
| `tests/integration/phase2/test_b25_manuscript_audit.py` | Manuscript/direct Claim/transitive Claim/Conclusion unsupported Issues with every severity; exact review/event IDs, hashes and attribution; repeated placements retain occurrences; unrelated project/version reviews excluded; all-type blocking IDs; no concern for citation-only/no-review input; citation and SUPPORTED/STRONG rhetoric never imply support. Tampered review hash, reviewer binding, Issue enum/text/ordinal/root history fail; empty result has no support-completeness claim. |
| `tests/integration/phase2/test_b25_manuscript_read_races.py` | Hold query after first SELECT; concurrent unrelated INSERT and relevant audit/verification/retraction/Issue INSERT commit before releasing reader; assert complete old snapshot and fresh next-query result. Observe REPEATABLE READ/READ ONLY and absence of explicit locks via SQL capture and pg_locks (ordinary ACCESS SHARE allowed). Credential expiry during read denies return; concurrent placement freeze cannot produce mixed material. |

Use disposable PostgreSQL 18.x via `tests/disposable_postgres.py` and exported
B04 fixtures; never SQLite. Run new files plus existing B04 contract/hash,
B05 review contract/hash, architecture tests, B04 migration/freeze/races,
`tests/integration/phase2/test_pr2_13_scientific_trace.py`,
`tests/integration/phase2/test_b05_manuscript_review.py` and
`tests/integration/test_pr14_governance_integration.py`. Run affected literature/
Conclusion suites if their helpers change. Static commands: `uv run --frozen ruff
format --check .`, `uv run --frozen ruff check .`, `uv run --frozen pyright`.
Report commands/counts, skips and failures exactly. The outer loop owns the whole
suite; this task does not run it or claim its results.

### 12.5 Not in this slice

Manuscript supersession/revision, DRAFT preview audits, automatic prose-to-Claim
binding or semantic support scoring, Issue creation/disposition, new audit
findings, Decision/Approval/READY transitions, consent, prepared packages,
submission/external effects, reverse global impact enumeration, bulk pagination,
HTTP/CLI exposure, queues, caches, materialized projections and new dependencies.

## 13. Open questions for the owner — override register

Approval is requested for the pinned first slice: exact FROZEN reads, existing
publication reader policy, attributed OPEN unsupported concerns over exact
manuscript/Claim/Conclusion reviews, fixed completeness ceilings and zero DDL.
These choices leave no implementation-time policy selection. Owner changes
require revising this contract before execution; approval alone does not authorize
implementation or accept later backlog items.

## 14. Documentation verification note

Only this proposal is changed. No B25 runtime or test implementation exists from
this task. Verification used
`UV_CACHE_DIR=/private/tmp/researchbase-lane14-uv-cache` for each `uv` command.
The initial online attempts failed downloading dependencies because DNS was
unavailable; the local cache then allowed these offline runs:

```sh
uv run --frozen --offline ruff format --check .
uv run --frozen --offline ruff check .
uv run --frozen --offline pyright
uv run --frozen --offline pytest tests/unit tests/architecture -o addopts='' -ra
uv run --frozen --offline pytest tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b04_manuscript_races.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_b05_manuscript_review.py tests/integration/test_pr14_governance_integration.py -o addopts='' -ra --tb=short
```

Static results: 570 files already formatted; Ruff passed; Pyright reported
0 errors, 0 warnings, 0 informations. PostgreSQL selection: 116 collected,
2 failed, 102 setup errors, 12 skipped, no passes. No admin URL was configured;
localhost ports 5432/55440 had no server. Local PostgreSQL 18 `initdb` attempts
failed with `shmget: Operation not permitted` in the sandbox, including the
mmap configuration attempt. This is **not PostgreSQL acceptance evidence**.
Unit/architecture selection: 2,359 collected; 2,343 passed, 4 failed, 12 setup
errors, 7 warnings in 45.41s. The four failures in `test_hg1_runner.py` were
`PermissionError: Operation not permitted` at Unix socket bind; all 12 errors in
`test_pr2_19_boundaries.py` required the missing disposable PostgreSQL admin URL.
The seven warnings were the existing Alembic `path_separator` deprecation.

A focused document check verified the exact status, all 14 numbered sections and
28 local links. `git diff --check` returned clean. No whole-suite result is claimed.
No commit, push or branch creation is authorized or performed.
