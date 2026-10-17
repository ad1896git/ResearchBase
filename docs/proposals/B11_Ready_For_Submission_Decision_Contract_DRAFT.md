# B11 READY_FOR_SUBMISSION Decision Purpose Contract — DRAFT

**Status: APPROVED by owner 2026-10-16 — first slice authorized for implementation**

## Start here (for the implementer)

B11 records one attributable readiness judgment about one exact frozen manuscript,
with its complete manuscript-review basis. It does not make a Publication READY.
Review evaluates, Decision chooses, Approval authorizes, and a later command
consumes a grant and performs the transition. Invalid scientific facts and OPEN
BLOCKING concerns cannot be overridden by a favorable judgment.

Build only after owner approval, architecture approval of the existing registered relation’s
bounded implementation and purpose refinement below, and separate execution authorization:

1. Freeze §11's purpose/value, DTOs, errors, independence and complete-basis policy.
2. Add §12.1's forward migration and deferred completeness guards, preserving 0042.
3. Extend existing Decision domain/Application/port/repository paths in §12.3.
4. Use §12.2's SHARE-first writes and lock-free snapshot reads, including helpers.
5. Add §12.4's tests, run focused checks, record results and stop at §12.5.

Read §1 for authority/baseline, §10 for terms and §13 for owner overrides. Policies
identified as proposed are decisions for approval, not claims of implemented behavior.

Five rules whose violation fails review:

1. Target the exact sealed ManuscriptVersion ID/hash; never a Publication pointer,
   another version, a conclusion-release Decision or a prepared package.
2. Bind every committed review of that exact manuscript, including unfavorable
   reviews; reject missing, corrupt or nonindependent basis instead of dropping it.
3. Require independent current OWNER/APPROVER decider and independent HUMAN reviews;
   role accumulation cannot override scientific invalidity or OPEN blockers.
4. Preserve immutable Decision/hash history and non-replacement; no late basis,
   Issue disposition, approval/grant write or publication lifecycle transition.
5. The first transactional SQL for writes is SHARE(B); exact reads use a single
   REPEATABLE READ, READ ONLY snapshot and no explicit exclusion locks.

## 1. Purpose, authority and inspected baseline

| Source | Constraint carried into this proposal |
| --- | --- |
| [System 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 6, 12; [Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A18–A23 | Facts precede authority; exact frozen immutable provenance; separate Review/Decision/Approval/Command/effect; bounded schema admission. |
| [Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md); [Cross-Phase 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§9–18, 24 | Reuse DecisionRecord and typed relations, Application boundary, additive compatibility, concrete RESTRICT FKs. |
| [Phase 2 specification 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §§19, 22–24, PR2-14/15/17; [Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), §§4, 6–7 | Independent review, explicit Decision, unresolved blockers and separate internal publication/package gates. |
| [Field contract 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md), governance/publication rows; [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md), DecisionRecord payloads; [R3 18](../architecture/18_Phase2_Design_R3_Targeted_Remediation_v1.0.md), §1 | Concrete manuscript/review basis, unchanged literal material_version=1 hashes; derive canonical ordering from verified refs. |
| [Governance R2 17](../architecture/17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md), §1; [Temporal R4 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md), TEMP-AUTH-01 | READY_FOR_SUBMISSION is a distinct manuscript purpose; OWNER/APPROVER decider independent of material authors; later independent HUMAN approval and fresh post-wait authorization. |
| [Minimal Decision 20](../architecture/20_PR2_15_Minimal_Decision_Command_Contract_v1.0.md), §§2–7 | Existing release purpose remains bounded; complete review snapshot, no replacement, original-actor replay under current read entitlement. |
| [Harness 09](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 18–21 | Common Application boundary; evidence before acceptance; documentation is not implementation authorization. |

Inspected baseline (2026-10-15):

- [0048/B04](../../migrations/versions/0048_b04_manuscript_freeze.py) and
  [ManuscriptFreezeService](../../src/researchbase/application/manuscript_freeze.py)
  supply document/placement seals, exact frozen closure and current validity.
  Publication lifecycle remains DRAFTING-only in these guards.
- [0049/B05](../../migrations/versions/0049_b05_manuscript_review.py) and
  [InternalReviewService](../../src/researchbase/application/internal_review.py)
  supply exact independent HUMAN manuscript review, immutable OPEN Issue history
  and `collect_manuscript_review_basis`. Its `gate_satisfied` means nonempty
  reviews and no direct manuscript OPEN BLOCKING Issues; it is not B11 permission.
- [DecisionService](../../src/researchbase/application/decision.py),
  [Decision repository](../../src/researchbase/persistence/decision_repository.py)
  and [0042](../../migrations/versions/0042_pr2_15_minimal_decision.py) admit only
  INTERNAL_SCIENTIFIC_RELEASE/PROCEED with conclusion/review basis, immutable
  membership, canonical hashes and deferred completeness checks.
- [B08](B08_Issue_Disposition_Contract_DRAFT.md) is a draft, not an implemented
  disposition mechanism. It proposes Claim/conclusion disposition only and defers
  manuscript disposition. B11 cannot presume it closes manuscript Issues.
- [B04 repository](../../src/researchbase/persistence/manuscript_freeze_repository.py)
  and [novelty repository](../../src/researchbase/persistence/novelty_repository.py)
  demonstrate SHARE-first protected writes. Existing Decision and non-coverage
  novelty commands take earlier request/target locks; do not copy that order here.

No B11 execution pack exists in the inspected `execution/phase2/` inventory.
This proposal is not an execution pack or dependency acceptance declaration.

## 2. Scope, dependency boundaries and non-goals

Add `record_ready_for_submission_decision` and `get_ready_for_submission_decision`
to DecisionService. Keep existing release command/DTO behavior intact. Reuse the
registered DecisionRecord + typed basis relations; add no canonical entity,
receipt store, JSON semantic core, snapshot owner or infrastructure.

B04/B05 are implemented prerequisites. B08 approval/implementation is required
before treating any proposed terminal disposition as an eligible closed concern.
Until then, original OPEN history is verified and OPEN blockers deny. Do not build
B08 inside B11. Even an accepted B08 as currently drafted cannot close manuscript
Issues; their disposition requires a separately approved extension. Unblocked
manuscripts need no fabricated disposition record.

Proposed stage policy: Decision creation is allowed while Publication is DRAFTING
or INTERNAL_REVIEW; B11 does not enable the latter state. R2 17 requires
INTERNAL_REVIEW at the later readiness approval/effect gate. Imposing that state
on this earlier judgment would require an unrelated lifecycle implementation.
No READY/SUBMITTED/ACCEPTED/PUBLISHED target admission in this slice.

## 3. Invariants and conservative judgments

### 3.1 Exact target, authority and independence

For a new record require ACTIVE project, trusted VerifiedPrincipal with live
credential, binding, membership and effective OWNER or APPROVER assignment.
The decider may be HUMAN or AGENT, matching the accepted Decision base; HUMAN-only
approval is a different boundary. Derive `decided_by` and advancing DB time.

Require FROZEN manuscript with nonnull frozen_at, placement_set_hash, content_hash
and sha256-cjson-v1 scheme; exact Publication belongs to the supplied Project.
Verify B04's complete document/placement/scientific/literature closure and current
VALID status, including retained artifact bytes. Neither hash shape nor review
recommendation substitutes for closure verification. There is no latest/current
lookup to choose the target. B04's existing pointer/seal consistency is still
verified; supporting a future SUPERSEDED manuscript needs its own lifecycle contract.

Use `material_authors(target, manuscript=True)` in decision_repository.py:
manuscript/Publication and document authors, placement creators, and the complete
existing typed transitive scientific/literature/input author set. The decider
must differ from every actor in that set. Each review author must be HUMAN and
independent of the same set, with valid historical REVIEWER/OWNER attribution and
exact target ID/hash. As in the accepted Decision base, the decider may also be a
required reviewer; B11 adds no reviewer/decider separation. Later R2 approval must
separately exclude requester, decider, reviewers and material contributors.

### 3.2 Complete review basis and applicable blockers

Inside the protected write snapshot, select **all** committed
`internal_review_records` with `(project_id, manuscript_version_id)` equal to the
target; require at least one. Each must have only that concrete target, matching
hash, valid saved review hash/scheme, historical independent attribution and
complete Issue/event structure. An invalid matching review fails the command;
never filter it away, select the latest, or accept caller-selected review IDs.

Include ACCEPT, MINOR_REVISION, MAJOR_REVISION, REJECT and UNCERTAIN records.
No recommendation vote or affirmative-only filter is introduced: consistent with
Decision 20, an authorized decider explains the judgment in rationale. Recommendation
alone is neither a blocker nor proof of readiness. Exact review summaries remain
readable through their own authorization boundary.

Always reject any OPEN BLOCKING Issue on any review of the exact manuscript,
including reviews outside a favorable subset and zero-Issue review insertion races.
Proposed conservative extension: also scan reviews whose exact ClaimVersion,
ScientificConclusionVersion or ArtifactVersion target is reachable from B04's
verified manuscript dependency closure (including the document). Use concrete
placement/input edges already traversed by B04 and material_authors, recursively,
not related text, shared identity, another version or related_source_version_id.
These upstream reviews are blocker inputs, not extra manuscript-review basis rows.
No review requirement is added for every dependency. INFO/MINOR/MAJOR OPEN Issues
remain visible and do not alone veto this bounded Decision.

When B08 becomes available, verify terminal history/basis under its approved
policy before excluding a closed Issue; do not trust a changed status column
alone. Current manuscript Issues remain OPEN-only under B05. No action completion,
NO_CHANGE, disposition, authority or favorable review makes INVALID facts VALID.

## 4. Proposed commands, DTOs and historical readback

Both methods take a trusted principal separately from a closed immutable DTO
(§11.3). Creation returns the saved DecisionReadback specialized for a manuscript;
exact read takes project and Decision ID. No list, preview, batch or target search.

Read roles are current OWNER, RESEARCHER, REVIEWER, VIEWER or APPROVER, with live
verified project entitlement. Unlike review authorship, read access is not HUMAN-
or REVIEWER-only. Authorize before existence disclosure; foreign scope/different
actor replay is FORBIDDEN; entitled absent exact ID is NOT_FOUND.

Historical read/replay verifies saved typed membership, exact frozen target and
review hashes, literal basis/content hashes and attribution. It does not demand
that today's review set equal the saved set, current write role, current VALID
status, current absence of blockers or the original publication stage. Report
current validity and blocker IDs separately, timestamped in the same snapshot.
New reviews cannot be appended to an old Decision's basis. Historical hash integrity
does not certify today's gate; later approval/effect must recheck the complete set.

## 5. Schema and literal hash proposal — no migration

Add only `decision_basis_manuscripts` (§12.1), alongside existing concrete
conclusion/review basis tables. No target-type locator, redundant target hash
column or new Decision event is needed. Parent is attributable immutable history.

Reuse [domain/decision.py](../../src/researchbase/domain/decision.py) builders
unchanged: `DecisionRecordBasisSet` and `DecisionRecord`, material_version=1,
sha256-cjson-v1, supersedes_decision_id=null. Basis consists of exactly one
`ManuscriptVersion` ref and all exact `InternalReviewRecord` refs. Verify hashes,
sort by `(type, canonical UUID text, content_hash)`, assign contiguous 0..N-1
ordinals across tables and derive basis_set_hash. InternalReviewRecord sorts before
ManuscriptVersion. Content includes literal READY_FOR_SUBMISSION/PROCEED,
project/question/rationale/decided_by and basis_set_hash as in R2; request ID,
times, diagnostics, blockers and publication stage are not new hash fields.

Issue descriptors/status/events are not covered by the Review content hash.
This draft introduces no cryptographic Issue-state snapshot and makes no claim
that a Decision digest alone proves the historical blocker gate. Preserve and
validate existing event history; do not invent a new hash payload to fill that gap.

## 6. Error contract — proposed use of existing categories

§11.2 pins existing mappings; add no ErrorCode. Distinguish malformed command,
ineligible new basis and corrupt saved provenance. Normalize named constraints
and SQLSTATE through existing UoW patterns; never return raw driver/credential
chains or treat a swallowed uniqueness error as success.

## 7. Transactions, concurrency and failure recovery

One command is one synchronous READ COMMITTED UoW. §12.2 fixes the exact first
statement, table inventory and subsequent lock order. SHARE locks stabilize mutable
closure/authority inputs and prevent review/Issue INSERT phantoms. Do not write
to any table in B. No external network call or artifact mutation occurs in a UoW.

Same UUID/original actor/normalized material returns saved history under current
read entitlement. Same UUID changed material is IDEMPOTENCY_CONFLICT; another
actor or project cannot inspect/replay it. A different UUID for an already decided
`(project, READY_FOR_SUBMISSION, manuscript)` also conflicts, even with identical
wording. No supersession, replacement or correction command is admitted. A new
manuscript can have a new Decision; it is not automatic supersession of the old.

Retry only SQLSTATE 40001/40P01, exactly three total fresh-UoW attempts, no delay;
redo locks, reads, closure and current-clock authorization. Never retry a business
conflict, timeout or uncertain commit blindly. Recover an uncertain commit with
the same UUID. Deferred checks and any resulting waits precede final fresh-clock
authority checks. Failure rolls back parent and all basis rows together.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

§12.4 pins concrete files/cases. Verify both commit orders with independent real
PostgreSQL backends, actual lock observations and injected failures. Include
normal-role direct SQL bypass attempts, historical read lock inspection, and
inherited release/hash behavior. Documentation review is not execution evidence.

## 9. Acceptance criteria and evidence boundary

Owner approval must accept §11 and the bounded typed relation/guard amendment,
followed by architecture review of conformance to the registered manuscript-basis
relation and approval of the new bounded policies, then a separate execution pack.
Require real PostgreSQL 18.x migrations, catalog/constraints/races and focused
static/unit/architecture evidence with no open P0/P1. B08 behavior stays unavailable
until approved and verified; manuscript disposition remains separately deferred.
The external loop owns the whole-suite run. This draft cannot declare B11
implementation, Phase 2 exit, READY, package freeze or submission acceptance.

## 10. Glossary

| Term | Meaning here |
| --- | --- |
| Readiness Decision | Immutable choice about an exact manuscript; not lifecycle state or permission. |
| Exact manuscript | Concrete ManuscriptVersion UUID and verified frozen content/placement seal. |
| Complete review basis | All committed reviews targeting that exact manuscript at the protected write point. |
| Material authors | Actors reached by the existing typed manuscript/scientific/literature attribution traversal. |
| Applicable blocker | OPEN BLOCKING concern on the manuscript or §3.2's exact reachable review targets. |
| Historical closure / current validity | Saved immutable provenance integrity versus today's VALID/STALE/INVALID projection. |
| B | Fixed SHARE-protected relation inventory in §12.2, acquired before write-side reads. |
| Replay | Original actor and identical normalized UUID request, returned under current read entitlement. |

## 11. Decisions taken in this draft

These proposed choices require owner approval; none authorizes implementation.

### 11.1 Scope and policy decisions

| Choice | Adopted decision |
| --- | --- |
| Purpose/value | READY_FOR_SUBMISSION/PROCEED only; no PREPARE_SUBMISSION or reconsideration. |
| Stage | Earlier judgment permits DRAFTING/INTERNAL_REVIEW; later approval requires INTERNAL_REVIEW under R2 17. |
| Authority | Current OWNER/APPROVER, no HUMAN-only decider refinement; independent of traversed material authors. |
| Reviews | Nonempty complete exact-manuscript set, all recommendations retained; historical independent HUMAN attribution. |
| Blockers | Direct manuscript plus §3.2 exact reachable Claim/conclusion/artifact targets; no source-text or identity-wide expansion. |
| B08 | Draft dependency for terminal status use; no implicit manuscript disposition extension. |
| History | One Decision per purpose/project/exact manuscript; no replacement, supersession or late basis. |
| Persistence/adapters | One typed basis relation; existing parent/hash/UoW patterns. Application only; routes/CLI deferred. |

### 11.2 Pinned error mappings

Matches [api/errors.py](../../src/researchbase/api/errors.py) and
[cli/errors.py](../../src/researchbase/cli/errors.py).

| Error code | HTTP | CLI exit | Trigger |
| --- | --- | --- | --- |
| AUTHENTICATION_REQUIRED | 401 | 3 | No trusted principal. |
| FORBIDDEN | 403 | 3 | Wrong role, lost read entitlement, foreign project or different-actor replay. |
| VALIDATION_ERROR | 422 | 2 | Wrong type/literal, extra key, blank/invalid/oversize text. |
| NOT_FOUND | 404 | 3 | Entitled exact requested record/target absent. |
| CONFLICT_OF_INTEREST | 403 | 3 | New decider is a traversed material author. |
| FROZEN_REFERENCE_REQUIRED | 409 | 5 | New target lacks required frozen manuscript seal. |
| DECISION_BASIS_INVALID | 409 | 4 | New decision has no reviews, invalid requested purpose/value or OPEN applicable blocker. Unsupported DTO literals fail earlier as VALIDATION_ERROR. |
| INVALID_STATE_TRANSITION | 409 | 4 | Ineligible publication stage or unsupported transition. |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Same UUID changed material or different UUID same decided scope. |
| IMMUTABLE_RECORD | 409 | 4 | Historical edit/delete or late basis insertion. |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Concrete FK violation. |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Corrupt saved hashes/basis/history, nonindependent review, wrong target/hash/project, or non-VALID required closure. |
| CONCURRENT_MODIFICATION | 409 | 4 | SQLSTATE 40001/40P01 after three total attempts. |

Preserve existing UoW P17F1→IMMUTABLE_RECORD, P17F2→PROVENANCE_CLOSURE_VIOLATION,
P17F3→IDEMPOTENCY_CONFLICT. B11 completeness/shape failures use P17F2 and scope
loss P17F3; new-command Application checks use the specific categories above
before insertion. Primary-key collisions require rollback and entitled saved
record comparison in a fresh UoW. No SQL constraint failure is an automatic replay.
Timeout/unknown DB errors keep sanitized INVALID_STATE_TRANSITION fallback;
unexpected transport errors remain HTTP 500 INTERNAL_ERROR / CLI exit 1.

### 11.3 DTO fields, Python types, limits and enums

Use closed `@dataclass(frozen=True, slots=True)` types, never ORM objects. All UUID
fields require exact `uuid.UUID`; future transport text is canonical lowercase
hyphenated UUID. Text is strict Unicode UTF-8, NFC, nonblank, with meaningful
whitespace preserved as domain `_text` does. Proposed new-command bounds are
1..16,000 Unicode characters after NFC for question/rationale; do not retroactively
reject older release records using these new bounds.

| DTO | Exact fields |
| --- | --- |
| `RecordReadyForSubmissionDecisionCommand` | `id: UUID`, `project_id: UUID`, `manuscript_version_id: UUID`, `question: str`, `rationale: str`, `decision_type: Literal['READY_FOR_SUBMISSION']='READY_FOR_SUBMISSION'`, `decision: Literal['PROCEED']='PROCEED'`. |
| `GetReadyForSubmissionDecisionQuery` | `project_id: UUID`, `id: UUID`. |
| `ReadyForSubmissionDecisionReadback` | `id`, `project_id`, `publication_id`, `manuscript_version_id`, `decided_by`: UUID; `decision_type`, `decision`: above literals; `question`, `rationale`: str; `decided_at: datetime`; `target_content_hash`, `basis_set_hash`, `content_hash`: str; `hash_scheme: Literal['sha256-cjson-v1']`; `basis: tuple[DecisionBasisReference, ...]`; `current_validity: Literal['VALID','STALE','INVALID']`; `current_blocking_issue_ids: tuple[UUID, ...]`; `evaluated_at: datetime`. |

Times are aware UTC, hashes lowercase 64-hex. Basis refs keep existing
`type: str` restricted here to ManuscriptVersion/InternalReviewRecord, `id: UUID`,
`content_hash: str`, `ordinal: int` (exact int, not bool, ≥0). One manuscript plus
1..10,000 reviews (proposed admission ceiling; no pagination/truncation). Over
10,000 matching reviews denies new creation as DECISION_BASIS_INVALID; historical
read verifies the saved complete set without imposing a new ceiling. Ordinals are
0..review_count; diagnostic Issue IDs are distinct, canonical UUID sorted, complete
and uncapped. Caller supplies no review subset, actor, time, hash, status, basis,
publication pointer, independence assertion, grant, outcome alternative or supersedes ID.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

Choose the next forward migration after the actual accepted head; do not reserve
0052 or rewrite 0042/0048/0049. This is a sketch, not executable authorization.
Preserve existing parent types: UUID id/project/decided_by/supersedes; VARCHAR(40)
decision_type, VARCHAR(16) decision, TEXT question/rationale, TIMESTAMPTZ decided_at,
CHAR(64) basis/content hashes and VARCHAR(32) hash_scheme. Supersedes remains NULL.

```sql
CREATE TABLE decision_basis_manuscripts (
  decision_id UUID NOT NULL,
  manuscript_version_id UUID NOT NULL,
  ordinal INT NOT NULL,
  CONSTRAINT pk_b11_basis_manuscripts PRIMARY KEY (decision_id, manuscript_version_id),
  CONSTRAINT fk_b11_basis_decision FOREIGN KEY (decision_id)
    REFERENCES decision_records(id) ON DELETE RESTRICT,
  CONSTRAINT fk_b11_basis_manuscript FOREIGN KEY (manuscript_version_id)
    REFERENCES manuscript_versions(id) ON DELETE RESTRICT,
  CONSTRAINT uq_b11_one_manuscript UNIQUE (decision_id),
  CONSTRAINT uq_b11_manuscript_ordinal UNIQUE (decision_id, ordinal),
  CONSTRAINT ck_b11_manuscript_ordinal CHECK (ordinal >= 0)
);
CREATE INDEX ix_b11_manuscript_target
  ON decision_basis_manuscripts(manuscript_version_id);
-- Replace 0042's generated purpose/value checks, using their actual catalog names:
ALTER TABLE decision_records DROP CONSTRAINT decision_records_decision_type_check;
ALTER TABLE decision_records DROP CONSTRAINT decision_records_decision_check;
ALTER TABLE decision_records ADD CONSTRAINT ck_b11_decision_policy CHECK (
  (decision_type='INTERNAL_SCIENTIFIC_RELEASE' AND decision='PROCEED') OR
  (decision_type='READY_FOR_SUBMISSION' AND decision='PROCEED'));
ALTER TABLE decision_records ADD CONSTRAINT ck_b11_text_bounds CHECK (
  decision_type<>'READY_FOR_SUBMISSION' OR
  (length(question) BETWEEN 1 AND 16000 AND length(rationale) BETWEEN 1 AND 16000));
```

If another accepted purpose migration precedes B11, retain its exact admitted
policy branches and guards. Never broaden to arbitrary purpose/value cross-products.
Do not add UNIQUE(manuscript_version_id): future distinct purposes must remain
representable. Scope exclusion is purpose-specific under the exact target lock,
as in 0042, with P17F3 on another READY Decision for that target/project.

| Named guard | Required behavior |
| --- | --- |
| `b11_require_snapshot` / `b11_decision_guard` BEFORE INSERT parent | For READY require READ COMMITTED and all B relation locks preheld in SHARE or stronger, then exact target coordination through basis guards. Bound text, purpose/value and NULL supersedes; no session-variable bypass. Cannot prove Application's first-statement order from a hash; separately test that order. |
| `b11_manuscript_basis_guard` BEFORE INSERT | Preheld B; exact manuscript FOR UPDATE, project/publication binding, FROZEN seal; parent xmin equals current transaction as in 0042; READY purpose, no conclusion basis; enforce no other same-purpose/project/target Decision (P17F3). Parent and child immutable IDs cannot retarget scope. |
| `pr215_basis_guard` replacement | Dispatch review basis by parent purpose: legacy path unchanged; READY review must target the one exact manuscript/hash/project after target lock. Same-transaction parent requirement, no late membership. Conclusion basis always rejects READY; never route manuscript review through conclusion-only guard. |
| `pr215_complete_basis` replacement | Dispatch by parent purpose, preserving legacy SQL. READY requires exactly one manuscript, zero conclusion/other target basis, 1..10,000 exact manuscript reviews, and bidirectional equality with ALL committed matching reviews; verified structural reviewer and decider independence/historical role bindings, frozen target and same project, no applicable OPEN BLOCKING Issues under §3.2. Enforce canonical global ordinals: review UUID order 0..N-1, manuscript ordinal N. SQL checks structural provenance; Application still checks bytes, full hashes, credential and deterministic validity. |
| `b11_complete_manuscript` constraint trigger AFTER INSERT on new relation | DEFERRABLE INITIALLY DEFERRED, invoke the dispatched completeness function. Retain `pr215_complete_decision` and `pr215_complete_review` so parent-only, review-only, missing/extra/mixed basis cannot commit. |
| `b11_manuscript_basis_immutable` BEFORE UPDATE OR DELETE | Invoke existing pr215_immutable (P17F1). Retain existing Decision/conclusion/review immutability triggers. Late INSERT fails same-transaction-parent guard. |

Do not install a trigger that reruns historical completeness every time a later
review is created; a later review does not corrupt the saved Decision. The later
consumer must revalidate its current basis. Underlying review INSERT guards keep
the existing manuscript-target coordination. SQL blocker traversal uses the same
finite concrete dependency edges as §3.2; test the query against Application scope.

Downgrade locks Decision parent/all basis tables ACCESS EXCLUSIVE in lexical
order, refuses if any READY Decision or manuscript basis exists, otherwise restores
prior checks/functions and drops only new empty structures. Populated legacy release
history survives both upgrade and permissible downgrade. No history erasure/backfill.

### 12.2 Exact lock order and transactions

B is the shipped B04_SNAPSHOT_TABLES union the five tables below, deduplicated and
sorted by literal table name. This is a fixed inventory, not runtime discovery:

```python
B = tuple(sorted(set(B04_SNAPSHOT_TABLES) | {
    'internal_review_records', 'manuscript_versions', 'publications',
    'review_issue_events', 'review_issues',
}))
```

B04_SNAPSHOT_TABLES means the exact list in
`src/researchbase/persistence/manuscript_freeze_repository.py` inspected above;
freeze that list into the implementation/tests, not a dependency that silently
widens later. It includes mutable validity/authority and typed scientific/input/
placement relations. No command writes to B. Decision parent/basis tables are
excluded because this command inserts there.

| Command | Exact ordered operations |
| --- | --- |
| `record_ready_for_submission_decision` | In-memory principal/DTO shape validation; open fresh READ COMMITTED UoW (connection settings before BEGIN bound the first wait). FIRST transactional SQL is one `LOCK TABLE <B in lexical order> IN SHARE MODE`; no SELECT, SET LOCAL or advisory lock precedes it. Then SET LOCAL lock_timeout='10s', statement_timeout='30s'; request advisory `pg_advisory_xact_lock(hashtextextended(:key,0))`, bound key `b11:decision:<canonical request UUID>`; exact manuscript FOR UPDATE; project FOR SHARE; owning Publication FOR SHARE. Authorize readers at fresh DB time before disclosure; saved UUID replay branch verifies history/actor/normalized command and final read entitlement. If new, authorize writer; verify target/seals/stage/closure/authors; enumerate all target reviews by UUID with plain SELECT (B stabilizes them); read their Issue/event sets and exact upstream blocker sets with plain SELECT, deterministic UUID ordering; verify hashes/independence/history and no blockers; check same-purpose scope; derive canonical refs/hashes; fresh writer check; insert parent then manuscript basis then review basis in UUID order; force SET CONSTRAINTS ALL IMMEDIATE; final fresh-clock credential/role/closure eligibility check; commit atomically. |
| `get_ready_for_submission_decision` | FIRST SQL sets TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY; enable existing snapshot-read adapters; authorize current readers without project row lock; read exact parent then basis/target/reviews/history using plain SELECT; verify saved closure/hashes, derive timestamped current diagnostics; final fresh-clock read-entitlement check; return DTO, no writes. No explicit table, advisory or row locks anywhere in nested helpers. |

The collector currently locks manuscript→project→publication and then reviews;
call it only inside the prepared write UoW, with those first three locks already
held. Add a plain-SELECT review enumeration variant to avoid hidden review-row
locks. Read/replay verifiers must not invoke the write collector. Use existing
`enable_revision_action_snapshot_reads` adapters and lock-free authority helpers;
DecisionService._authorize currently locks project and is unsuitable for exact reads.
Do not call InternalReviewService's HUMAN REVIEWER-only read authorization to
implement Decision read access.

After any blocking wait reread relevant durable state in a new READ COMMITTED
statement and obtain `clock_timestamp()`. Force deferred guards before the last
check; another later wait requires another check. Scheduled credential/role expiry
must deny even while SHARE locks prevent database revocation writes. Protected read
snapshots report entitlement in that snapshot plus advancing-clock expiry; they
promise no lock-based exclusion against a revocation committed after snapshot start.

SHARE-first can deadlock with older target-first writers; do not claim otherwise.
40001/40P01 abort/retry the entire UoW under §7, never upgrade B lock modes or
acquire review/Issue row locks to work around this. Direct-SQL guards require the
same protected inventory and exact target exclusion before completing basis.

### 12.3 Ordered build steps and real module paths

1. Inspect accepted head and policy predecessors. Add only the authorized forward
   file in `migrations/versions/` with §12.1 schema/dispatch/immutability/deferred
   guards; retain all accepted purposes and data.
2. Extend `src/researchbase/domain/decision.py` only for pure typed readiness
   validation needed by §11.3; reuse existing DecisionBasisReference and unchanged
   literal material builders. No ORM, SQLAlchemy Session or transport import.
3. Extend `src/researchbase/application/decision.py` with the two named methods,
   closed DTOs, admission, historical verification, normalized replay and SQLSTATE-
   bounded retry. Inject the existing ArtifactStore port for B04 verification;
   update construction in `src/researchbase/api/app.py` and
   `src/researchbase/cli/composition.py` without exposing new adapter commands. Reuse B04 verify_in_uow and B05 review verification/collector
   in the same UoW; do not open nested transactions or use a read DTO as gate proof.
4. Extend DecisionRepository/UnitOfWork ports in
   `src/researchbase/application/ports.py`; implement typed manuscript basis reads,
   inserts, purpose scope and snapshot protocol in
   `src/researchbase/persistence/decision_repository.py`. Add the lock-free review
   query in `src/researchbase/persistence/internal_review_repository.py` and update
   `src/researchbase/application/internal_review.py` collector use accordingly.
5. Wire normalization/snapshot adapters in `src/researchbase/persistence/uow.py`.
   Preserve release target-first semantics unless a separately authorized fix is
   needed; B11 protocol applies only to B11. Keep shared helper changes additive.
6. Add §12.4 tests, run focused gates and dependent suites, record exact results,
   review against authoritative specs/diff/evidence and stop. No API/CLI wiring or
   runtime dependency additions; pinned mappings are future adapter compatibility.

### 12.4 Test files and required cases

Reuse exported PostgreSQL fixture builders/B04/B05 patterns and disposable
`phase2_database_url` databases, not retained canonical installations. Test real
PostgreSQL 18.x with independent engines/backend PIDs and normal-role connections.
No SQLite substitutes or sleep-only concurrency evidence.

| File to add | Cases |
| --- | --- |
| `tests/unit/phase2/test_b11_readiness_contract.py` | Exact UUID/type/closed fields, unsupported purposes/values, bool ordinal, NFC/invalid UTF-8/nonblank and 16,000 boundaries; reader/writer policy; complete-set ceiling without truncation; all pinned error mappings. |
| `tests/unit/phase2/test_b11_readiness_hash_vectors.py` | Independently authored literal R2 JSON/digests for one/multiple/adverse reviews, canonical UUID/type order, changed manuscript/hash/rationale/review set inequality; no actor/time/diagnostic additions to basis payload; unchanged release/Phase 1 golden vectors. |
| `tests/integration/phase2/test_b11_readiness_decision.py` | FROZEN exact manuscript success; unfrozen/wrong project/version/hash/seal/document bytes/placement corruption; STALE/INVALID denial; stage and all writer/reader roles; transitive author independence including placements/document/literature; HUMAN reviewer historical role/hash/independence; decider-reviewer overlap permitted; complete adverse/zero-Issue reviews; no reviews and 10,001-review denial. Direct/upstream exact blocker scope, another version excluded, nonblocking allowed, no assumption of B08 manuscript disposition; no publication/Issue/approval/grant/receipt side effects. |
| `tests/integration/phase2/test_b11_readiness_replay.py` | Same UUID restart/exact replay; changed material/different actor/project; different UUID same scope cannot replace; lost write role/current invalidity/new adverse review/blocker permit authorized history read/replay only, never new gate success; no late basis; uncertain commit recovery; read-only SQL/pg_locks prove no explicit table/advisory/row locks in nested verifiers. |
| `tests/integration/phase2/test_b11_readiness_schema.py` | Catalog types/names/FKs/indexes; clean install, populated release upgrade and downgrade preservation; populated B11 downgrade refusal; direct normal-role SQL missing/mixed/wrong project/extra/omitted review basis, noncanonical global ordinals, fake scope, late child mutation/INSERT, parent-only commit, preheld snapshot/isolation checks, deferred force failure and atomic rollback. |
| `tests/integration/phase2/test_b11_readiness_races.py` | Actual pg_blocking_pids/pg_stat_activity/lock evidence for both commit orders of zero-Issue review INSERT, BLOCKING Issue INSERT, upstream blocker INSERT/disposition (only once B08 exists), credential/binding/membership/validity mutation and same/different UUID scope races; final clock expiry after each wait; deterministic 40001/40P01 three-attempt exhaustion; timeout/business conflict no retry; mid-parent/child and deferred-check failure rolls back everything. |
| `tests/architecture/test_b11_readiness_boundaries.py` | Application boundary, pure Domain, no JSON locator/new state owner, shared exact read without locks, SHARE first statement, no current-pointer target selection, no new scientific truth/approval/lifecycle/ExternalEffect writes. |

After implementation, run focused B11 files above, B04/B05 and PR2-15 Decision/
coordination/schema suites, B06 and existing Basic Approval regressions for shared
UoW/helper compatibility, plus static/unit/architecture checks. Add accepted B08
regressions only when that implementation exists. Exact commands/counts/server
version belong in implementation evidence. The external loop runs the whole suite;
do not substitute future planned tests for current executed results.

### 12.5 Not in this slice

Publication INTERNAL_REVIEW/READY transitions; READY approval requests/decisions/
grants/consumption; PREPARE_SUBMISSION Decisions; RECONSIDER_REJECTION; manuscript
revision or Issue disposition; B07/B08 implementation; authorship/consent/package
freeze; automatic Issue propagation; Decision supersession/replacement; source
review targets; API/CLI endpoints; venue send/SubmissionRecord/ExternalEffect;
Agent runtime, queues, new dependencies or new hash/material versions.

## 13. Open questions for the owner — override register

| Owner may override | Adopted proposal |
| --- | --- |
| Stage and outcome | DRAFTING/INTERNAL_REVIEW judgment with PROCEED only; INTERNAL_REVIEW prerequisite belongs to later approval/effect. |
| Review quality | Complete adverse-inclusive set, no vote threshold; independent decider explains judgment, blockers/invalid facts always deny. |
| Independence | Accepted OWNER/APPROVER decider policy, including AGENT and reviewer-decider overlap; later HUMAN approval separation stays mandatory. |
| Blocker scope and B08 | Exact manuscript and reachable Claim/conclusion/artifact reviews; terminal history only after accepted disposition implementation; no implied manuscript extension. |
| Correction and limits | One initial Decision per exact scope, no replacement; new-command 16,000-character text and 10,000-review admission bounds. |

Override requires a recorded disposition and matching body/schema/test edits
before contract freeze. Owner approval and execution authorization remain distinct.

## 14. Documentation verification note

This proposal changes documentation only. Current baseline checks are recorded
below after execution; none exercises proposed B11 code, migrations or gates.
The whole-suite run belongs to the external loop.

Executed in this restricted workspace on 2026-10-15/16:

| Exact command | Observed result |
| --- | --- |
| `/Users/fengwang/Documents/ResearchBaseProject/.venv/bin/ruff check .` | PASS, “All checks passed!” |
| `/Users/fengwang/Documents/ResearchBaseProject/.venv/bin/ruff format --check .` | PASS, 570 files already formatted. |
| `/Users/fengwang/Documents/ResearchBaseProject/.venv/bin/pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject` | PASS, 0 errors, 0 warnings, 0 informations. |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python -m pytest tests/unit tests/architecture tests/test_architecture.py -o addopts='' -ra > /private/tmp/b11-unit-architecture-installed.log 2>&1` | 2,371 collected: 2,354 passed, 5 failed, 12 errors, 7 warnings. Four Runner failures: sandbox AF_UNIX bind PermissionError. One static-acceptance failure: its nested Pyright uses the unavailable lane-local environment and reports missing dependency imports. Twelve architecture fixture errors: RB_TEST_ADMIN_URL absent. Not PASS. |
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python -m pytest tests/unit/phase2/test_pr2_04_static_acceptance.py -o addopts='' -ra > /private/tmp/b11-static-unit-recheck.log 2>&1` | 1 collected, 1 failed, 1 warning; nested Pyright still cannot resolve dependencies using its default environment. No implementation failure is inferred from this environment result. |
| `python3 /private/tmp/b11-check-doc.py` | PASS: 26 local links, 14 numbered sections, required status, 13 HTTP/CLI mapping pairs checked against source AST, write/read protocol text and whitespace. |
| `git diff --check` | Exit 0; new-file whitespace also checked by the document script. |

Exact focused PostgreSQL command:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python -m pytest tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_15_coordination.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b04_manuscript_races.py tests/integration/phase2/test_b05_manuscript_review.py tests/integration/phase2/test_b05_review_basis.py tests/integration/phase2/test_b05_review_migration.py tests/integration/phase2/test_b05_review_races.py -o addopts='' -ra > /private/tmp/b11-postgres-installed.log 2>&1
```

206 collected: **4 failed, 1 skipped, 201 errors**, zero passes. Setup/admin URL
failures prevent PostgreSQL behavior verification; RB_TEST_ADMIN_URL was not
supplied. The existing skip is SUPERSEDED manuscript history, deferred by B04.
No server version or PostgreSQL PASS is claimed. No retained deployment was used.

Initial canonical-environment attempts all failed dependency downloads because
network DNS was unavailable (exit 2, no tests collected):

- `UV_CACHE_DIR=/private/tmp/b11-uv-cache uv run ruff check .`
- `UV_CACHE_DIR=/private/tmp/b11-uv-cache uv run ruff format --check .`
- `UV_CACHE_DIR=/private/tmp/b11-uv-cache uv run pyright`
- `UV_CACHE_DIR=/private/tmp/b11-uv-cache uv run pytest tests/unit tests/architecture tests/test_architecture.py -o addopts='' -ra > /private/tmp/b11-unit-architecture.log 2>&1`
- `UV_CACHE_DIR=/private/tmp/b11-uv-cache uv run pytest tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_15_coordination.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b04_manuscript_races.py tests/integration/phase2/test_b05_manuscript_review.py tests/integration/phase2/test_b05_review_basis.py tests/integration/phase2/test_b05_review_migration.py tests/integration/phase2/test_b05_review_races.py -o addopts='' -ra > /private/tmp/b11-postgres.log 2>&1`

An initial fallback
`/Users/fengwang/Documents/ResearchBaseProject/.venv/bin/pyright --pythonpath /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python`
reported 1,010 errors and 2 warnings because project configuration still selected
the incomplete lane-local environment. The explicit `--venvpath` run above
resolved this for the standalone check. The incomplete environment created by uv
was removed; no dependency/configuration source was changed. Installed-environment
checks are fallback evidence, not a successful canonical uv synchronization.

Only this proposal is a source change. No whole-suite run, commit, push, branch,
implementation, migration or acceptance declaration was performed.
