# B07 Revision-purpose Decisions and Concern Carry-forward — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

## Start here (for the implementer)

B07 proposes an attributable Decision about one exact old ReviewIssue, admits
that Decision as completed RevisionAction basis, and links the old concern and
exact result to an independently authored, exact-target re-review. It never
resolves the Issue or makes a release decision. B06 (migration 0051) and the
accepted minimal Decision command are prerequisites, not authority to build B07.

Build only after owner approval, architecture admission of the two new relations
in §12.1, and separate execution authorization:

1. Implement the finite policies and closed DTOs in §3 and §11.
2. Add the forward migration, typed basis and immutable relation guards (§12.1).
3. Extend the existing Decision/RevisionAction Application and persistence paths
   in the order in §12.3. Preserve existing release semantics and hashes.
4. Apply the per-command write and lock-free read protocols in §12.2.
5. Add the tests in §12.4, report actual checks, and stop. §12.5 stays excluded.

Use §10 for terms, §1 for authority and the inspected baseline, and §13 for the
owner's approval choices. These are proposed decisions, not unresolved choices
for an implementer to make.

Five rules whose violation fails review:

1. Minimal INTERNAL_SCIENTIFIC_RELEASE/PROCEED is never revision or NO_CHANGE basis.
2. Every association resolves exact concrete FKs; same project, shared parent,
   similar text and “latest” never establish concern/result correspondence.
3. NO_CHANGE requires an explicit ACCEPT_NO_CHANGE Decision and nonblank rationale;
   it creates no scientific result and leaves even BLOCKING Issues OPEN.
4. Re-review correspondence is an attributable relation, not a claim of resolution,
   approval, favorable review, or newly VERIFIED evidence.
5. Writes begin with the prescribed SHARE table inventory; reads use one
   REPEATABLE READ snapshot with no table, advisory or row locks.

## 1. Purpose, authority and inspected baseline

The backlog asks for eligible revision/NO_CHANGE basis and old-concern → exact
result/re-review mapping. The following sources constrain this proposal; new
policy is identified as proposed rather than attributed to existing code.

| Source | Requirement carried forward |
| --- | --- |
| [Architecture 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 6, 12; [Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A18–A23 | Fact precedes authority; immutable exact provenance; separate Review, Decision, Approval and effect; bounded schema admission. |
| [Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), governance rows; [Cross-Phase 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§9–18, 24 | Existing DecisionRecord, ReviewIssue and RevisionAction owners, concrete relations and additive compatibility. |
| [Phase 2 specification 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §22, PR2-14/15; [Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), §§4, 6 | Preserve old version → review/concern → completed revision → targeted re-review; OWNER/APPROVER independent decision; disposition is a separate command. |
| [Field contract 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md), governance tables; [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md), review/decision/revision; [R3 18](../architecture/18_Phase2_Design_R3_Targeted_Remediation_v1.0.md), §1 | Typed basis tables, literal material_version=1 payloads; derive basis ordering from verified refs, never caller/persisted ordering. ReviewIssue material is separate from Review hash. |
| [Governance R2 17](../architecture/17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md), §§1, 4; [Temporal R4 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md), TEMP-AUTH-01 | Completed finite results; explicit NO_CHANGE Decision rationale; no automatic Issue disposition; fresh post-wait authorization. |
| [Minimal Decision 20](../architecture/20_PR2_15_Minimal_Decision_Command_Contract_v1.0.md), §§2–7 | Preserve complete release-review snapshot, blocker denial, no replacement and historical replay. Revision-purpose policy is separately required. |
| [Harness 09](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 18–21 | Application boundary; evidence before completion; this is documentation only. |

Inspected baseline (2026-10-15):

- [DecisionService](../../src/researchbase/application/decision.py) and
  [migration 0042](../../migrations/versions/0042_pr2_15_minimal_decision.py)
  admit only INTERNAL_SCIENTIFIC_RELEASE/PROCEED, conclusion and review basis.
  0042 supplies immutable membership and deferred completeness triggers.
- [RevisionActionService](../../src/researchbase/application/revision_action.py),
  [pure material/relevance](../../src/researchbase/domain/revision_action.py) and
  [migration 0051](../../migrations/versions/0051_b06_revision_action.py)
  admit Issue-only NEW_EXPERIMENT, ANALYSIS_CHANGE, CLAIM_CHANGE,
  CONCLUSION_CHANGE and SOURCE_CHANGE. Decision-bearing actions, NO_CHANGE and
  MANUSCRIPT_CHANGE still deny despite their representable DTO/hash shapes.
- [Revision repository](../../src/researchbase/persistence/revision_action_repository.py)
  takes the mutable-fact SHARE inventory first; its reads use the UoW's
  read-only snapshot adapters. [Decision repository](../../src/researchbase/persistence/decision_repository.py)
  and [novelty repository](../../src/researchbase/persistence/novelty_repository.py)
  demonstrate SHARE protection, but existing Decision and non-coverage novelty
  writes take target locks first. B07 uses B06's table-first variant, not a claim
  that every existing writer already does so.
- [B05 migration 0049](../../migrations/versions/0049_b05_manuscript_review.py)
  supplies manuscript review guards. Its presence does not enable manuscript
  RevisionAction relevance, which B06 still rejects. B07 keeps that path deferred.

No B07 execution pack exists in the inspected `execution/phase2/` inventory.
This proposal cannot substitute for authorization or declare dependency acceptance.

## 2. Scope, dependency boundaries and non-goals

Propose `record_revision_decision`, `get_revision_decision`, extension of existing
`record_revision_action` / `read_revision_action`, `record_concern_re_review`, and
`get_concern_carry_forward`. All use the same Application boundary for Human and
Agent callers. Re-review is created through existing InternalReviewService before
it is associated here; B07 creates neither results nor reviews.

Targets are ClaimVersion and ScientificConclusionVersion only. Keep the five
B06 changed-result shapes and add NO_CHANGE. Admit Issue-only changed actions,
Decision-only actions and combined Issue+Decision actions under §3.1. Every
Decision-bearing action ultimately identifies one exact Issue through its Decision.
Manuscript, Artifact/research-brief and arbitrary cross-domain review targets deny.

Two proposed concrete association tables (§12.1) are needed because current typed
Decision basis cannot name a ReviewIssue and current Review/RevisionAction has no
re-review correspondence FK. Existing domain objects remain the owners. These are
new relations, not new top-level entities, snapshots, JSON references, receipt
stores or a propagation engine. They require explicit architecture admission;
A23's minimal-release-only no-new-field approval does not admit them by implication.

## 3. Invariants and conservative judgments

### 3.1 Finite Decision and action policy

Propose `decision_type=REVISION_RESPONSE` with exactly two values:

| Decision | Meaning and eligible action |
| --- | --- |
| REQUIRE_CHANGE | Choose a material response to this exact concern. Only the five completed B06 changed shapes may cite it; the Decision itself is not a completed change. |
| ACCEPT_NO_CHANGE | Explicitly accept this exact concern without material change, with nonblank rationale. Only NO_CHANGE may cite it; all seven result FKs must be NULL. |

A revision Decision binds exactly one Issue through `decision_revision_concerns`,
its exact old target through one typed Claim/conclusion basis row, and **all**
eligible committed reviews of that exact project/target/hash at the protected
snapshot (including the Issue's own review). Use the accepted Decision eligibility
checks: immutable hash/closure, historical creation authority, independent reviewer,
all recommendations including REJECT/UNCERTAIN, and no silent omission of corrupt
matching records. At least one review is required. New reviews arriving later do
not change saved basis. Do not apply release's no-blocker gate here: choosing a
response to an OPEN/BLOCKING concern must be reachable. This grants no dismissal.

New Decisions require current OWNER/APPROVER, ACTIVE project and live verified
principal, independent of all affected old-target material authors. Preserve the
base's absence of a HUMAN-only decider rule. One revision Decision per exact Issue,
across both values, enforced in SQL; supersedes_decision_id remains NULL. Changing
that choice later requires a separate correction contract, not a second UUID.

Both Issue and Decision supplied: Issue must equal the Decision's single bound
Issue, with the same project and exact old target/hash. Decision-only: derive
that Issue from the immutable relation. Issue-only: preserve B06 changed paths;
NO_CHANGE denies. Release PROCEED, foreign purpose, incompatible value, unbound
or corrupt Decision denies. Existing B06 predecessor rules remain: same **stored**
Issue/Decision pair, nonforking terminal head, iterative acyclic history. Switching
an Issue-only chain to combined basis requires a new root, never a rewritten pair.

### 3.2 Exact carry-forward and re-review

The old Issue remains attached to its original immutable review and exact target.
Each action identifies an exact result using the existing seven typed columns and
hash payload. Reuse every B06 admission/relevance check, including sealed terminal
Run + exact Spec, shared Measurement analysis and exact source-correction lineage.
Old material may be STALE/INVALID provided its historical closure verifies; new
results must pass B06's current result checks, including its RETRACTED-source
exception. NO_CHANGE supplies no result; its result_validity is NULL, not VALID.
ACCEPT_NO_CHANGE never overrides deterministic invalidity in the old target.

A re-review association joins one exact action to one existing independent review.
It derives the old Issue through the action's basis, never through free text.
New first associations require an action with no successor at the protected
point, and a review created at or after that action, whose complete own hash,
project, target closure and creation authority verify. Current writer must be
that review's HUMAN reviewer, have effective REVIEWER or OWNER authority, and be
independent of old/new material authors and the action creator. No favorable
recommendation is required; REJECT/UNCERTAIN and new OPEN Issues remain visible.
The writer attests correspondence by recording the relation; review text is never
parsed as structured linkage and the link is never a favorable disposition.

| Action | Only admissible re-review target and exact-result witness |
| --- | --- |
| CLAIM_CHANGE | Exactly result_claim_version_id and its hash. |
| CONCLUSION_CHANGE | Exactly result_scientific_conclusion_version_id and its hash. |
| NEW_EXPERIMENT | Frozen Claim/conclusion whose Phase 1 evidence closure contains a Measurement from **result_run_id**, with that Run's exact paired result Spec. |
| ANALYSIS_CHANGE | Frozen Claim/conclusion whose EvidenceRelation closure contains **result_statistical_result_id**, not just the same Measurement. |
| SOURCE_CHANGE | Frozen Claim/conclusion whose exact LiteratureSupportSnapshot/direct conclusion literature inputs bind **result_source_version_id** through LiteratureEvidence. A citation/title/current source pointer is insufficient. |
| NO_CHANGE | Exactly the unchanged old target/hash. No invented replacement ref. |

For the three indirect rows, also require the same old Claim identity at an equal
or higher version number, or the same old conclusion identity at an equal or
higher number; a conclusion re-review of an old Claim must include that Claim's
same/equal-or-later identity lineage. Verify all traversed frozen material and
current target validity on first association; a retracted source cannot become
positive support merely to obtain a mapping. Unrepresentable indirect results
remain explicitly unmapped, with no fabricated review of Run/StatisticalResult/
SourceVersion. Subsequent associations may add other exact reviews; none replaces
an earlier link. Superseded actions and their links stay in historical readback.

`get_concern_carry_forward` returns **all** actions for the exact concern, including
decision-only actions, their successors and exact mapped reviews. Empty mappings
mean PENDING_RE_REVIEW, never “no concern remains”. Late Issues on the same old
version are separate concerns; no identity-wide transfer, automatic cloning, or
“latest wins”. Another review with the same target is not mapped unless linked.

## 4. Proposed commands, DTOs and historical readback

Closed frozen dataclasses and service methods are pinned in §11.3. Trusted
principal is separate; actor/time/hash/role/ordinal/validity are never input.

- `record_revision_decision(principal, command)` selects and freezes its complete
  review basis server-side and inserts Decision + basis + concern relation in one
  transaction. Return RevisionDecisionReadback, not an ORM entity.
- Existing `record_revision_action` accepts the newly eligible bases and NO_CHANGE;
  all existing B06 behavior and request UUIDs stay compatible. Readback may now
  have review_issue_id=NULL; `effective_review_issue_id` is derived, never stored.
- `record_concern_re_review(principal, command)` inserts one immutable relation
  between completed action and already committed re-review, after §3.2 checks.
  Its composite `(revision_action_id, internal_review_record_id)` is its request
  identity; it creates no new canonical record UUID or request receipt.
- `get_revision_decision(principal, project_id, id)` and
  `get_concern_carry_forward(principal, project_id, review_issue_id)` disclose only
  after current project read entitlement. Read the complete saved graph in one
  snapshot; verify historical material and project current validity separately.

Readers are effective OWNER, RESEARCHER, REVIEWER, VIEWER or APPROVER with ACTIVE
membership, live credential and canonical binding, as in DecisionService._READERS.
No old role confers perpetual read access. Foreign scope yields nondisclosing
FORBIDDEN; an authorized absent exact ID yields NOT_FOUND.

## 5. Schema and literal hash proposal — no migration

Retain the R2/R3 Decision and RevisionAction payloads verbatim. Decision basis is
the exact target and complete saved review set. Derive sorted contiguous ordinals
from `(type, canonical UUID, verified hash)` on write/read; persisted ordering is
checked as storage integrity, not used to choose hash order (R3 §1). Recompute
basis_set_hash and content_hash independently. RevisionAction binds both its
optional Issue ID and exact Decision ID/hash, seven result keys including NULLs,
predecessor ID/hash and trusted actor. Run remains an identity ref with no hash.

The two new association relations have no own content hash. Like separate
ReviewIssue facts under Correction 12 §4, their immutable FK membership is enforced
by database guards. **Neither an Issue selection nor a re-review association is
cryptographically covered by the existing Review/Decision hash.** Do not claim it
is or silently add payload keys/material versions. Verify relation membership,
immutability and exact closure as well as hashes; if cryptographic binding of
these relations is required, owner must amend the hash contract before coding.
No Phase 1 or accepted minimal-release payload changes are proposed.

## 6. Error contract — proposed use of existing categories

Use §11.2 exactly, with sanitized messages and no raw driver/credential detail.
DECISION_BASIS_INVALID is available in both transports for ineligible revision
Decision selection. Persisted corruption stays PROVENANCE_CLOSURE_VIOLATION;
malformed caller material stays VALIDATION_ERROR. Do not introduce error names
from prose that lack an existing ErrorCode/transport mapping.

## 7. Transactions, concurrency and failure recovery

One command is one READ COMMITTED UoW; the FIRST transactional SQL statement is
`LOCK TABLE <B> IN SHARE MODE` (§12.2). Configure existing connection timeouts
before BEGIN. No preflight query, SET LOCAL, advisory or row lock comes first.
Explicit complete-set queries run after that wait. Table SHARE protects the
mutable closure/authority inventory against ordinary ROW EXCLUSIVE writers.
B includes internal_review_records to exclude review-insertion phantoms through
commit. All writers, including normal-role SQL, take ROW EXCLUSIVE on review
insertion and therefore participate without new writer hooks. Do not infer Issue membership from the review hash or scan a mutable
“all concerns” set: select the one exact immutable Issue relation instead.

Only deadlock/serialization failures retry, at most three fresh UoWs, repeating
locks, reads, validation and fresh `clock_timestamp()` authority checks. Timeout
or other failure rolls back without a success record. Force deferred constraints
before readback and recheck live authority immediately before commit/return.
No driver error chain leaves Application.

UUID replay of Decision/action requires original actor, identical normalized
command, and current read entitlement; verify saved basis without selecting later
reviews or requiring current write authority/result validity. Changed payload
conflicts, unauthorized scope does not disclose existence. Composite relation
replay returns the saved relation for its original recording actor with current
read entitlement, even after writer-role loss, invalidity or action supersession;
another authorized reader uses the read query. No duplicate effect/event.
Lost commit acknowledgment is recovered by the same UUID/composite key. New IDs
never replace the Decision for an already decided Issue. Historical reads use
§12.2's distinct lock-free protocol, never the write/replay protocol.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

Require independent literal hash vectors, DTO/caller boundaries, exact concern
and result scope, complete unfavorable review inclusion, SQL immutability and
completeness, both race commit orders, historical replay/read entitlement and
rollback/restart evidence. Test every allowed action/basis combination and every
rejected result shape. Concrete artifacts/cases are in §12.4. Passing current
baseline tests is not evidence that these unimplemented B07 behaviors work.

## 9. Acceptance criteria and evidence boundary

Approval must accept §11 policy, the two concrete relations and §12 guards/locks;
implementation additionally needs an authorized execution pack and architecture
registry admission. Preserve minimal-release blocker/nonreplacement and Basic
Approval gates; a revision Decision must fail every approval-basis substitution.

Later acceptance requires disposable PostgreSQL 18.x fresh/forward migration,
normal-role constraints, exact snapshot/read/write witnesses and focused dependent
regressions, with commands/counts/version recorded. No open P0/P1 finding, partial
transaction or undocumented architecture deviation may be called accepted. This
task writes only this file, creates no branch/commit/push and makes no gate claim.

## 10. Glossary

| Term | Meaning here |
| --- | --- |
| Concern | One existing ReviewIssue UUID, owned by its original exact review/target. |
| Revision-purpose Decision | Proposed REVISION_RESPONSE choice about one exact concern; no Approval. |
| Completed action | Existing immutable RevisionAction; result already exists, or eligible NO_CHANGE. |
| Effective Issue | Stored action Issue, or Issue derived from its eligible Decision relation; both must agree. |
| Carry-forward | Explicit immutable old concern → action/results → re-review correspondence. No Issue movement or resolution. |
| Re-review | Separate InternalReviewRecord of an exact supported target; not a mutable review status. |
| B | The exact B06 mutable-fact table inventory in §12.2, used only on writes. |
| Historical closure | Saved refs/hashes/relationships verify even when current validity has changed. |
| Current validity | Derived VALID/STALE/INVALID projection, distinct from immutable history. |
| Deferred trigger | DEFERRABLE INITIALLY DEFERRED database constraint, forced before command readback. |

## 11. Decisions taken in this draft

These are fixed proposed answers, awaiting owner approval. No permission to
implement, choose alternatives silently, or expand accepted Decision semantics.

### 11.1 Scope and policy decisions

| Question | Draft decision |
| --- | --- |
| Purpose/value vocabulary | Only REVISION_RESPONSE × REQUIRE_CHANGE or ACCEPT_NO_CHANGE, paired by SQL CHECK. Existing INTERNAL_SCIENTIFIC_RELEASE × PROCEED remains unchanged. |
| Concern granularity | One exact Issue per Decision, complete exact-target review set as basis; no selective favorable reviews, inferred Issue selection or reusable blanket acceptance. |
| Actor | Decision OWNER/APPROVER independent of old material authors; action OWNER/RESEARCHER; relation authored by its HUMAN re-reviewer with REVIEWER/OWNER, independent of authors and action creator. No invented HUMAN attribution. |
| Replacement | No second Decision for an Issue and no Decision supersession in this slice. B06 action correction is same stored basis, nonforking and append-only. Multiple action roots and re-reviews stay visible. |
| NO_CHANGE | Only ACCEPT_NO_CHANGE, no result fields, rationale in Decision, effective Issue mandatory; no ADDRESSED/DISMISSED or validity override. |
| Missing re-review | Explicit PENDING_RE_REVIEW; original OPEN/BLOCKING concern remains. Mapping is evidence of correspondence, never resolution. |
| Schema | Add registered decision_basis_claims and two narrowly justified concrete relations, only after architecture admission. No generic target JSON, new canonical entity, hash or receipt. |
| Limits | One Issue and one target per Decision; one action/review pair per link; text at most 16,000 NFC Unicode characters. No caller basis array or batch API. Complete server-selected reviews/actions/links are not truncated or capped to obtain success. |
| Compatibility | Preserve B06 relevance and hashes, release-only Decision/Approval rules and source retraction exception. Manuscript path remains denied. |

### 11.2 Pinned error mappings

These rows match [api/errors.py](../../src/researchbase/api/errors.py) and
[cli/errors.py](../../src/researchbase/cli/errors.py); no new ErrorCode.

| Error code | HTTP status | CLI exit | Trigger |
| --- | --- | --- | --- |
| AUTHENTICATION_REQUIRED | 401 | 3 | No trusted principal. |
| FORBIDDEN | 403 | 3 | No live entitlement, foreign scope, different-actor replay/link. |
| VALIDATION_ERROR | 422 | 2 | Unknown field, malformed UUID/enum, text limit, invalid result shape. |
| NOT_FOUND | 404 | 3 | Entitled exact object absent. |
| CONFLICT_OF_INTEREST | 403 | 3 | Decider/re-reviewer independence fails. |
| FROZEN_REFERENCE_REQUIRED | 409 | 5 | Required material not frozen or inputs not sealed. |
| DECISION_BASIS_INVALID | 409 | 4 | Wrong Decision purpose/value, different concern/target or missing eligible basis. |
| INVALID_STATE_TRANSITION | 409 | 4 | Nonterminal Run, deferred manuscript path, used predecessor, superseded action for a new link. |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Same request/different material or second Decision for an Issue. |
| IMMUTABLE_RECORD | 409 | 4 | Attempt to update/delete sealed history or append basis after creation. |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Missing concrete FK under SQL enforcement. |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Corrupt saved graph/hash, unrelated result/re-review, invalid required current result. |
| CONCURRENT_MODIFICATION | 409 | 4 | SQLSTATE 40001/40P01 after bounded retries. |

Reuse UoW mapping P17R1→INVALID_STATE_TRANSITION, P17F1→IMMUTABLE_RECORD,
P17F2→PROVENANCE_CLOSURE_VIOLATION, P17F3→IDEMPOTENCY_CONFLICT.
23505 on `uq_b07_decision_concern` maps IDEMPOTENCY_CONFLICT; same-key link races
must roll back/reload/compare before success, not swallow a failed statement.
Keep `uq_revision_action_predecessor` normalization. Timeout/unknown transaction
errors follow the existing sanitized INVALID_STATE_TRANSITION fallback and do not
retry blindly. Only 40001/40P01 qualify for the three-attempt policy.

### 11.3 DTO fields, Python types and limits

`UUID` means exact `uuid.UUID`; `datetime` is timezone-aware UTC; all DTOs are
frozen dataclasses with slots and reject unknown fields. Normalize NFC text and
strict UTF-8 without stripping material; require nonblank and ≤16,000 Unicode
characters for the **new** command's question/rationale. Do not retroactively
reject longer accepted historical release records. Hashes are lowercase 64-hex.
Enums are case-sensitive literals; no aliases or caller-provided result digest.

```python
# typing.Literal; UUID and datetime imported from their standard-library modules.
RevisionChoice = Literal["REQUIRE_CHANGE", "ACCEPT_NO_CHANGE"]
RevisionPurpose = Literal["REVISION_RESPONSE"]
Validity = Literal["VALID", "STALE", "INVALID"]
MappingState = Literal["PENDING_RE_REVIEW", "RE_REVIEW_LINKED"]

# RecordRevisionDecisionCommand: all fields required except fixed purpose default.
id: UUID
project_id: UUID
review_issue_id: UUID
question: str
rationale: str
decision: RevisionChoice
decision_type: RevisionPurpose = "REVISION_RESPONSE"

# RecordConcernReReviewCommand: exactly these three fields; no separate id.
project_id: UUID
revision_action_id: UUID
internal_review_record_id: UUID
```

`RecordRevisionActionCommand` retains every field/type/default currently declared
in `application/revision_action.py`: id/project_id UUID; action_type str restricted
to its seven registered shapes; review_issue_id, decision_record_id, seven
result_*_id and supersedes_revision_action_id all UUID|None default None. At
least one basis is required; MANUSCRIPT_CHANGE still denies in Application/SQL.
Its first five changed shapes and NO_CHANGE admission are exactly §3.1.

| Readback | Exact field contract |
| --- | --- |
| RevisionDecisionReadback | id, project_id, review_issue_id, decided_by: UUID; decision_type: RevisionPurpose; decision: RevisionChoice; question, rationale: str; decided_at: datetime; claim_version_id, scientific_conclusion_version_id: UUID\|None (exactly one nonnull); target_content_hash, basis_set_hash, content_hash: str (64-hex); hash_scheme: Literal["sha256-cjson-v1"]; basis: tuple[DecisionBasisReference, ...]; target_validity: Validity. |
| Extended RevisionActionReadback | Retain existing fields; review_issue_id becomes UUID\|None, effective_review_issue_id: UUID is derived; result_validity: Validity\|None is NULL only for NO_CHANGE; target_validity: Validity; existing provenance tuple additionally returns exact Decision ref when used. |
| ConcernReReviewReadback | revision_action_id, internal_review_record_id, effective_review_issue_id, recorded_by: UUID; recorded_at: datetime; action_content_hash, review_content_hash, target_content_hash: str (64-hex); claim_version_id, scientific_conclusion_version_id: UUID\|None XOR; target_validity: Validity; has_superseding_action: bool. IDs/hashes of every result come from the verified action readback. |
| ConcernCarryForwardReadback | project_id, review_issue_id, original_review_id: UUID; original target UUID XOR and target_content_hash as above; target_validity: Validity; actions: tuple[ConcernActionReadback, ...]. |
| ConcernActionReadback | action: RevisionActionReadback; mapping_state: MappingState; re_reviews: tuple[ConcernReReviewReadback, ...]. Empty tuple is PENDING_RE_REVIEW, otherwise RE_REVIEW_LINKED; neither is an Issue status. |

Read query arguments are `(principal: VerifiedPrincipal, project_id: UUID, id:
UUID)` for Decision and `(principal, project_id, review_issue_id: UUID)` for concern.
Return actions ordered by `(created_at,id)` and links by review UUID; include all
roots/successors. Readback contains no caller credentials, role assertions or ORM.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

No DDL is executed by this task. Inspect the actual head before allocating the
next forward file; current head is `0051_b06_revision_action`. Never edit 0042,
0044 or 0051. All new FKs below are concrete and ON DELETE RESTRICT.

Replace 0042's generated `decision_records_decision_type_check` and
`decision_records_decision_check` with one paired CHECK; preserve all other
existing fields/types, hash checks, self-FK and NULL supersession rule:

```sql
ALTER TABLE decision_records
  ADD CONSTRAINT ck_b07_decision_tuple CHECK (
    (decision_type='INTERNAL_SCIENTIFIC_RELEASE' AND decision='PROCEED') OR
    (decision_type='REVISION_RESPONSE' AND
      decision IN ('REQUIRE_CHANGE','ACCEPT_NO_CHANGE')));

CREATE TABLE decision_basis_claims (
  decision_id UUID NOT NULL REFERENCES decision_records(id) ON DELETE RESTRICT,
  claim_version_id UUID NOT NULL REFERENCES claim_versions(id) ON DELETE RESTRICT,
  ordinal INT NOT NULL CONSTRAINT ck_b07_claim_ordinal CHECK (ordinal>=0),
  CONSTRAINT pk_b07_basis_claim PRIMARY KEY (decision_id,claim_version_id),
  CONSTRAINT uq_b07_claim_target UNIQUE (decision_id),
  CONSTRAINT uq_b07_claim_ordinal UNIQUE (decision_id,ordinal)
);
CREATE INDEX ix_b07_claim_basis_target ON decision_basis_claims(claim_version_id);

-- New association, not a Decision hash input or a new Issue lifecycle record.
CREATE TABLE decision_revision_concerns (
  decision_id UUID CONSTRAINT pk_b07_decision_concern PRIMARY KEY
    REFERENCES decision_records(id) ON DELETE RESTRICT,
  review_issue_id UUID NOT NULL REFERENCES review_issues(id) ON DELETE RESTRICT,
  CONSTRAINT uq_b07_decision_concern UNIQUE (review_issue_id)
);

-- Result and old concern are derived through the immutable action, not copied.
CREATE TABLE revision_action_re_reviews (
  revision_action_id UUID NOT NULL REFERENCES revision_actions(id) ON DELETE RESTRICT,
  internal_review_record_id UUID NOT NULL
    REFERENCES internal_review_records(id) ON DELETE RESTRICT,
  recorded_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  recorded_at TIMESTAMPTZ NOT NULL,
  CONSTRAINT pk_b07_action_re_review
    PRIMARY KEY (revision_action_id,internal_review_record_id)
);
CREATE INDEX ix_b07_re_review_target ON revision_action_re_reviews(internal_review_record_id);
```

The existing Decision VARCHAR(40)/VARCHAR(16) fit every proposed literal. Registered
`decision_basis_claims` is activated here; the other two tables need architecture
admission under §2. No new semantic JSON, generic reference columns, stored
mapping status, content hash or request receipt is admitted.

Required guard inventory (names pin future migration/tests):

| Guard | Required behavior |
| --- | --- |
| `b07_claim_basis_immutable`, `b07_decision_concern_immutable`, `b07_re_review_immutable` | BEFORE UPDATE/DELETE reject P17F1. Existing Decision/conclusion/review basis immutability remains. |
| `b07_revision_basis_guard` | Revision branch only: basis/concern rows belong to Decision inserted in this transaction, as 0042's xmin check; no later append, including post-commit same-UUID retry. Exact project/frozen target, scope and typed refs; no scientific/parent FOR UPDATE locks. |
| `b07_complete_decision`, `b07_complete_claim`, `b07_complete_concern` | AFTER INSERT constraint triggers DEFERRABLE INITIALLY DEFERRED. Also dispatch existing `pr215_complete_conclusion` and `pr215_complete_review` by purpose. Revision Decision requires one concern, XOR one Claim/conclusion target, complete eligible matching reviews, old Issue's review included, no other basis type, derived contiguous ordinals, exact hashes and §3.1. No release blocker test in revision branch. |
| `pr215_basis_guard`, `pr215_complete_basis` | Forward replacement dispatches by saved purpose; preserve original release no-replacement/complete-review/blocker behavior and target-first coordination on that branch. Revision branch must not execute release target/parent locks. A release row cannot gain concern/Claim basis. |
| `pr215_revision_guard`, `b06_revision_complete` | Forward replacement validates all admitted Issue/Decision combinations; reuse B06 result/relevance through a factored validator after resolving effective Issue; do not call the unchanged 0051 validator, which rejects every Decision basis. Validate eligible Decision and exact concern/project/hash; NO_CHANGE all-null and ACCEPT_NO_CHANGE only; retain existing immutability/predecessor unique guard. Decision must be committed before action creation, preventing same-transaction construction of incomplete bases. |
| `b07_re_review_guard`, `b07_complete_re_review` | BEFORE INSERT and deferred AFTER INSERT verify §3.2 exact path, project, committed dependencies, actor independence/creation authority, order and no-successor on first association; immutable repeat read does not reapply admission. Derive effective Issue, never trust a copied old ID or current pointer. |

Implement deferred guards as in 0042 (`CREATE CONSTRAINT TRIGGER ... AFTER INSERT
... DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION ...`). Attach
completeness to parent **and every child** insertion, so a parent with missing
children and an extra late child both fail. Force the applicable named constraints
IMMEDIATE before readback. SQL validates structural/hash/path invariants; trusted
live credentials remain Application checks, not invented SQL authentication.

Revision-Decision guards lock the exact immutable old Issue FOR UPDATE before
scope checking; all new revision branches use that order. Relation guards lock
the action FOR UPDATE before checking successor presence. Existing B06 corrections
already lock their predecessor; the same action row serializes link-versus-
supersession. SQL guards must also enforce these exclusions for normal-role direct
SQL; FK/UNIQUE alone cannot check complete basis/relevance. No new durable lock row.

Preflight all retained rows without rewriting them. Fresh DB and 0051→new-head
upgrades must preserve accepted release/action hashes and history. Downgrade locks
the affected tables in stable order and refuses P17F2 if revision Decisions,
Claim basis, concern relations or re-review links would be lost or stranded.
Only an empty new slice may restore the previous guards/checks and drop new tables.
No scientific CASCADE, history deletion, or rewriting migration checksums.

### 12.2 Exact lock order and transactions

For every B07 write and UUID/composite replay, B is the shipped
`REVISION_SNAPSHOT_TABLES` (`decision_repository._SNAPSHOT_TABLES` minus
`claim_versions`) **plus internal_review_records**, sorted lexically. The added
immutable table protects complete review-set selection against INSERT phantoms;
B07 never inserts reviews. Pin this explicit addition in implementation tests:

```text
actor_subject_bindings, actors, artifact_versions, artifacts, audit_findings,
claims, correction_records, datasets, experiment_spec_versions, experiment_specs,
impact_assessments, impact_targets, internal_review_records, literature_evidence,
literature_evidence_review_events, literature_source_project_links,
literature_sources, metric_definition_versions, metric_definitions,
project_membership_events, project_memberships, project_role_assignments,
projects, runs, scientific_conclusions, source_versions
```

No manuscript path is enabled. Frozen target/input and immutable Issue/Decision/
action/link tables are outside B; immutable review rows are the stated exception. No command mutates any B table;
SHARE→ROW EXCLUSIVE upgrade inside B07 is forbidden. Preserve protected adapters
from `enable_revision_action_snapshot_reads()` for closure/auth reads, with **no
hidden scientific target, parent, project or source row lock**.

Configure the existing `configure_revision_transaction()` connection profile
before transactional SQL: READ COMMITTED, lock_timeout=10s, statement_timeout=30s,
restored on pool checkin. Its pre-BEGIN driver configuration is not a query in the
command transaction. Then use the following exact sequences:

| Command | Ordered transaction statements/steps |
| --- | --- |
| `record_revision_decision` | **1.** `LOCK TABLE <B> IN SHARE MODE` FIRST. **2.** Existing SET LOCAL bounds, then request advisory `pg_advisory_xact_lock(hashtextextended(:key,0))`, key `pr215:decision:<canonical id>`. **3.** Protected readers; read entitlement, saved UUID and original actor/material comparison. Saved replay verifies saved graph, then fresh read entitlement and returns. **4.** New request: current write entitlement; exact Issue `FOR UPDATE` (no scientific row lock); inspect existing concern scope after wait. **5.** Reviews `FOR SHARE` in UUID order, then nonlocking closure/complete-review selection and all checks. **6.** Fresh time/authority, insert parent/basis/concern; force deferred guards, verify readback, fresh authority, commit. |
| `record_revision_action` including NO_CHANGE | **1.** First SHARE(B). **2.** SET LOCAL, request advisory `pr215:revision:<id>`. **3.** Read entitlement and saved replay checks first. **4.** New action: write entitlement, derive effective Issue from committed Decision if needed; exact old review `FOR SHARE`, then Issue `FOR SHARE`; predecessor `FOR UPDATE` if supplied, then reread successor. **5.** Nonlocking complete old/Decision/result/predecessor verification. **6.** Fresh authority, insert action, force guards, readback, fresh authority, commit. No target/result/parent row lock. |
| `record_concern_re_review` | **1.** First SHARE(B). **2.** SET LOCAL; request advisory key `b07:re-review:<action UUID>:<review UUID>`. **3.** Read entitlement and existing composite replay check before write eligibility. **4.** New link: action `FOR UPDATE`; reread successor; collect old and new immutable review IDs, lock `FOR SHARE` in UUID order, then effective Issue `FOR SHARE`. **5.** Verify complete saved basis/result and §3.2 correspondence; no re-review creation call. **6.** Fresh authorizing time, insert relation, force guards, verify readback, fresh authority, commit. |

All request keys are derived from canonical UUIDs; none is caller-defined policy.
A saved replay does not take new-creation scope/action/predecessor locks. Direct
SQL obtains ROW EXCLUSIVE on its destination before triggers; new relation/basis/
action destinations are outside B. Triggers take SHARE(B) before the listed row
locks and use the same exclusions. Already-held request/Issue/action/review locks
are reentrant; do not invert them by calling ordinary locking closure services.

Compatibility reasoning: B06 and B07 hold B without scientific row locks, so they
do not wait back on targets prelocked by Decision/Review/novelty. They write outside
B. Review INSERTs wait on B; Issue rows are immutable and exact Issue identity
is selected rather than enumerated. B07 does not take scientific row locks that
could invert a waiting review writer. Revision Decision serializes on the old Issue, so it sees a competing revision
Decision's committed concern after waiting; the UNIQUE is the final race guard.
Mapping and predecessor correction serialize on the exact action row. A correction
that commits first denies a fresh mapping; a mapping committed first remains
historical after correction. Treat this as reasoning to test, not a race PASS.
Inventory a newly introduced dependency before widening supported paths.

Every exact read (`get_revision_decision`, `read_revision_action`,
`get_concern_carry_forward`, including nested dependency/authentication readers):

1. Before the first query, configure **one REPEATABLE READ, READ ONLY transaction**
   and the pre-BEGIN statement timeout via existing UoW/connection pattern.
2. Establish current read entitlement, then read and verify saved refs/hashes,
   concern membership, results, links and successors in that same snapshot.
   Use nonlocking authorization and protected closure adapters throughout.
3. Recheck credential/binding/membership/role intervals with fresh
   `clock_timestamp()` immediately before return; end the read-only transaction.

Reads acquire **no explicit table, advisory or row locks**, including no request
advisory or FOR SHARE/UPDATE inside helpers. Ordinary PostgreSQL MVCC SELECT locks
are not an application exclusion protocol. Concurrent unrelated INSERTs must
commit while a read is paused and remain outside its established snapshot. A
fresh read observes later revocation; scheduled expiry is checked at fresh time
within the snapshot. Do not promise observation of commits after that snapshot.

### 12.3 Ordered build steps and module paths

1. Obtain owner/architecture approval of §11–§12, register the two relations and
   purpose policy, inspect Alembic head and add one forward file in
   `migrations/versions/` implementing §12.1. No accepted migration edits.
2. Extend `src/researchbase/domain/decision.py` and `domain/revision_action.py`
   with pure finite policy/typed correspondence validation. Preserve literal
   hash functions; add no persistence/framework imports to Domain.
3. Extend `src/researchbase/application/decision.py` with the separate closed
   revision command/readback and complete-basis historical verifier. Extend
   `application/revision_action.py` for effective Issue derivation, Decision
   checks, NO_CHANGE and the two concern correspondence methods/readbacks.
   Reuse nonlocking verification from `application/internal_review.py`,
   `scientific_conclusion.py`, `literature_evidence.py`, `source_version.py` and
   `closure.py`; pass the existing UoW, never invoke a separately committing
   service inside a command. Keep release-only RecordDecisionCommand unchanged. NO_CHANGE skips changed-result
   lookup/relevance entirely: verify its exact Decision, return seven NULL refs
   and result_validity=None; never fall through the existing SOURCE_CHANGE branch.
4. Extend `src/researchbase/application/ports.py`,
   `persistence/decision_repository.py`, `persistence/revision_action_repository.py`
   and `persistence/uow.py` for typed Claim/concern/link traversal, exact request
   sequences, snapshot reads and named error normalization. Reuse
   `persistence/database.py`'s B06 timeout setup/restore. Decision-only action
   lookup must join its Decision concern rather than drop rows through the
   current Issue-only INNER JOIN. Read query must include both basis forms
   without duplicate actions. Use existing SQL repository style, no new ORM core.
5. Add tests in §12.4, verify preserved release/Approval behavior and B06 hashes,
   record exact commands/counts/version and stop. API/CLI endpoints are excluded;
   if later authorized, they only parse closed DTOs and use §11.2 mappings.

### 12.4 Test artifacts and required cases

All B07-specific files below are **new, planned**, not present implementation.

| File | Required cases |
| --- | --- |
| `tests/unit/phase2/test_b07_revision_decisions.py` | Closed fields, exact UUIDs, text boundaries/Unicode, finite purpose/value and action matrix; trusted actor; R2/R3 literal vectors independent of helpers; persisted basis order not hash authority. |
| `tests/unit/phase2/test_b07_concern_carry_forward.py` | Effective-Issue agreement for three basis forms; all six action mapping predicates; exact Run/Spec, statistic and source witnesses; NULL NO_CHANGE validity; pending/linked and multiple-root/superseded read ordering. |
| `tests/unit/phase2/test_pr2_15_uow_errors.py` (existing) | Named unique/FK/immutability errors, timeout fallback, 40001/40P01 three-attempt boundary, sanitized diagnostics and link collision reload. |
| `tests/architecture/test_b07_revision_decisions.py` | Application boundary; concrete FK-only relations; no new top-level entity/JSON core/receipt/hash or IssueEvent/Approval/effect mutation; preserve Phase 1 and release hash contract. |
| `tests/integration/phase2/test_b07_revision_decisions.py` | Both values, Claim/conclusion targets; complete favorable/adverse review snapshot; exact concern, missing/foreign/corrupt basis; owner/approver author conflicts; blocker reachable for revision choice but still blocks PROCEED; every Issue-only/Decision-only/combined action tuple; NO_CHANGE denies PROCEED/REQUIRE_CHANGE/Issue-only/results; no Issue status/event effects. |
| `tests/integration/phase2/test_b07_concern_carry_forward.py` | Every §3.2 target/witness, unrelated same-project and equal-text IDs rejected, failed Run preserved, retracted-source mapping denied as positive support, HUMAN reviewer identity/independence, REJECT/UNCERTAIN/new Issues retained, no implicit correspondence by same target; composite replay after role loss/supersession, authorized missing read, no foreign disclosure. |
| `tests/integration/phase2/test_b07_schema.py` | Fresh/0051 upgrade, retained hashes, refused downgrade with each new history kind; catalog constraint/trigger names, all parent/child deferred guards, normal-role SQL empty/extra/late basis, concern substitution, result/re-review mismatch, UPDATE/DELETE/append denial and exact FK RESTRICT. Approval cannot accept revision Decision. |
| `tests/integration/phase2/test_b07_concurrency.py` | First transaction SQL is SHARE(B) for each write/replay and exact inventory; no hidden scientific row locks; pg_blocking_pids/pg_stat_activity/backend IDs prove both orders against role/source/evidence/validity owning writers and existing Decision/Review/novelty; scheduled expiry during first wait; competing UUID/same concern, same UUID/payload conflict, composite link race, link-versus-predecessor correction and no partial commit. |

Concurrency tests also pause each exact read after snapshot establishment and
prove an unrelated INSERT commits before read completion and is absent from that
snapshot. Assert REPEATABLE READ/READ ONLY precede the first query and capture
SQL to reject table/advisory/row locks in every nested reader. Exercise fresh-time
expiry, read loss, hash corruption, restart/lost acknowledgment and rollback.
Sleep-only observations are insufficient concurrency evidence.

Preserve focused regressions in existing `tests/integration/phase2/` files:
`test_revision_action.py`, `test_b06_revision_action.py`,
`test_b06_revision_concurrency.py`, `test_pr2_15_decision.py`,
`test_pr2_15_decision_schema.py`, `test_pr2_15_coordination.py`,
`test_pr2_14_internal_review.py`, `test_pr2_14_conclusion_review.py`,
`test_pr2_18_concurrency.py`, plus `tests/integration/phase2/test_approval.py`
for preserved Approval-basis policy.
The documentation run's concrete selected files/results are in §14; future B07
implementation must additionally run its new suites and actual Approval tests.
Do not run the whole suite in this documentation task; the external loop owns it.

### 12.5 Not in this slice

Issue ADDRESSED/DISMISSED/reopening or event lifecycle; rejection reconsideration;
Decision correction/supersession; manuscript RevisionAction/relevance; review of
Run/StatisticalResult/SourceVersion as new target types; automatic re-review or
result creation; scientific evidence promotion, approval/grant/release/readiness;
package/submission/ExternalEffect; new infrastructure/runtime dependencies;
Agent runtime/authentication expansion; crypto signing or new hash payloads;
API/CLI endpoints; Phase 2 completion/gate declarations.

## 13. Open questions for the owner — override register

Approval must accept or replace the pinned choices: one concern per revision
Decision, REVISION_RESPONSE × two values, no replacement, complete exact-target
review basis, no blocker gate on response choice, the §3.2 finite mapping matrix,
and the §12.2 write-only table-first/read-only snapshot protocols. In particular,
explicitly approve architecture admission of the two association relations and
the stated absence of cryptographic binding of those relations in existing hashes.
These are proposed narrow Entity+Relation patterns, not already-admitted schema.

There is no implicit permission to infer resolution from re-review or to admit
manuscript actions. Any owner override must update the body, DTO/DDL/guard/test
contracts and governing registry before an implementation pack is authorized.
Approval of this draft alone is not implementation authorization.

## 14. Documentation verification note

Executed 2026-10-15. These are documentation/current-baseline checks, not B07
implementation or acceptance. Only this file was added. No branch, commit or push
was created; the whole suite was not run. The external loop owns that evidence.

Every uv command below used this exact environment/prefix:

```bash
export UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv
export PYTHONPATH=src
uv --cache-dir /tmp/b07-uv-cache run --offline --no-sync <command>
```

| Command after that prefix | Observed result |
| --- | --- |
| `ruff check .` | All checks passed; exit 0. |
| `ruff format --check .` | 570 files already formatted; exit 0. |
| `pyright --pythonpath /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python` | 0 errors, 0 warnings, 0 informations; exit 0. Preamble notes absent checkout-local .venv. |
| `pytest -o addopts='' -ra tests/unit tests/architecture` | 2,359 collected; 2,343 passed, 4 failed, 12 errors, 7 warnings; no skips. |

Four failures in `tests/unit/test_hg1_runner.py` are AF_UNIX socket binds denied
by the sandbox (`PermissionError: Operation not permitted`). Twelve setup errors
in `tests/architecture/test_pr2_19_boundaries.py` require an explicit
RB_TEST_ADMIN_URL. Those are failures/errors, not passes. Logs were inspected at
`/tmp/b07-unit-architecture.log`. The shell log-tail wrapper subsequently attempted
to assign zsh's read-only `status` variable; that wrapper error did not rerun or
alter the recorded pytest results.

Focused PostgreSQL baseline attempt (same uv prefix):

```bash
pytest -o addopts='' -ra --maxfail=1 \
  tests/integration/phase2/test_revision_action.py \
  tests/integration/phase2/test_b06_revision_action.py \
  tests/integration/phase2/test_b06_revision_concurrency.py \
  tests/integration/phase2/test_pr2_15_decision.py \
  tests/integration/phase2/test_pr2_15_decision_schema.py \
  tests/integration/phase2/test_pr2_15_coordination.py \
  tests/integration/phase2/test_pr2_14_internal_review.py \
  tests/integration/phase2/test_pr2_14_conclusion_review.py \
  tests/integration/phase2/test_pr2_18_concurrency.py
```

191 collected; 1 setup error, 190 unexecuted after --maxfail=1; zero passed,
failed test bodies or skips. Setup failed because RB_TEST_ADMIN_URL (or its
suite-specific alias) was unset, before any database connection. No connected
PostgreSQL version or PostgreSQL PASS is available. Log:
`/tmp/b07-postgres.log`; its log-tail wrapper had the same post-run shell-variable
error described above. This does not provide SQL/concurrency acceptance evidence.

A repository-local inline Python check resolved all 24 relative Markdown links,
compared all 13 error rows directly to api.errors._STATUS and
cli.errors.CLI_EXIT_CODES, matched all 15 top-level sections to PR2-18, and checked
the 26-table write inventory against B06 plus internal_review_records: all passed.
The exact DRAFT status was checked. `git diff --check` passed. These static
checks do not execute the proposed DDL, policies or transaction protocol.
