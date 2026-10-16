# B08 Issue Disposition and Re-review Contract — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

## Start here (for the implementer)

B08 proposes an authorized, one-time OPEN→ADDRESSED or OPEN→DISMISSED transition
for one exact ReviewIssue. It retains the original concern, completed response,
exact independent re-review and Decision basis in immutable IssueEvent history.
Disposition is a judgment about that concern, never scientific validity or release
permission. B06 is implemented; B07 is a draft dependency, not an available gate.

Build only after owner approval, architecture admission of the event-field
refinement, accepted B07 implementation and separate execution authorization:

1. Freeze the finite policies, DTOs and errors in §11.
2. Add one forward migration with §12.1's event/projection guards; preserve old history.
3. Extend the existing review Application/port/repository paths in §12.3.
4. Apply §12.2's exact write order and lock-free snapshot reads throughout helpers.
5. Add §12.4's tests, report executed checks and stop; §12.5 stays excluded.

Use §1 for authority and baseline, §10 for terms, and §13 for owner overrides.
These are draft decisions for approval, not implementation choices left open.

Five rules whose violation fails review:

1. Never infer resolution from a completed action, favorable recommendation or B07 link.
2. ADDRESSED requires a changed result and its exact independent re-review;
   NO_CHANGE is eligible only for DISMISSED with an ACCEPT_NO_CHANGE Decision.
3. A BLOCKING transition always binds a matching Decision and verified closure;
   an OWNER cannot override invalid scientific facts.
4. Commit one immutable event and its status projection together; no reopening,
   historical edits, late basis attachment or replacement disposition.
5. First transactional SQL for writes is SHARE(B); reads use one REPEATABLE READ,
   READ ONLY snapshot with no explicit table, advisory or row locks.

## 1. Purpose, authority and inspected baseline

| Source | Constraint carried into this proposal |
| --- | --- |
| [System 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 6, 12; [Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A18–A23 | Facts precede authority; immutable provenance; Review, Decision, Approval and effect remain distinct; bounded schema admission. |
| [Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), governance registry; [Cross-Phase 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§9–18, 24 | ReviewIssue is STATEFUL_OPERATIONAL; ReviewIssueEvent is IMMUTABLE_RECORD; concrete references and additive compatibility. |
| [Phase 2 specification 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §§19, 22, PR2-14/15; [Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), §§4, 6–7 | Exact old review→concern→revision→re-review; original reviewer/independent OWNER authority, independent review for ADDRESSED, independent OWNER and Decision for DISMISSED; terminal issues do not reopen. |
| [Field contract 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md), governance rows; [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md); [R3 18](../architecture/18_Phase2_Design_R3_Targeted_Remediation_v1.0.md), §1 | Concrete Issue/actor/Decision event FKs; original Issue material immutable and separate from Review hash; preserve literal hashes and verified canonical basis order. |
| [Governance R2 17](../architecture/17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md), §4; [Temporal R4 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md) | Completed typed results; explicit NO_CHANGE rationale; separate Issue command checks exact result and independent reviewer, appending history; fresh post-wait authorization. |
| [Minimal Decision 20](../architecture/20_PR2_15_Minimal_Decision_Command_Contract_v1.0.md), §§2–7 | Release PROCEED is not revision/disposition basis; preserve blocker and complete-review gates. |
| [Harness 09](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 18–21 | Application boundary and evidence before acceptance; this task changes documentation only. |

Inspected 2026-10-15: [0040](../../migrations/versions/0040_pr2_14_initial_internal_review.py)
restricts Issue/event status to OPEN, forbids Issue mutation and permits one event
per Issue. [0041](../../migrations/versions/0041_pr2_15_review_coordination.py)
coordinates Issue creation with exact reviews/targets. [0042](../../migrations/versions/0042_pr2_15_minimal_decision.py)
provides immutable typed Decision basis and deferred completeness triggers.
[0051/B06](../../migrations/versions/0051_b06_revision_action.py) and
[RevisionActionService](../../src/researchbase/application/revision_action.py)
supply five Issue-only changed-result paths; Decision-bearing actions and NO_CHANGE
remain denied. [B07](B07_Revision_Decisions_Contract_DRAFT.md) proposes revision
Decisions and exact action/re-review correspondence, without disposition.
[InternalReviewService](../../src/researchbase/application/internal_review.py)
returns Issue status; its manuscript history verifier explicitly requires one OPEN
event. That assumption must change with B08, while the Review hash stays unchanged.
No B08 execution pack exists in `execution/phase2/`; this draft is not one.

## 2. Scope, dependency boundaries and non-goals

Add `record_issue_disposition`, `get_issue_disposition` and `get_issue_history` to
the review Application boundary. Admit ClaimVersion and ScientificConclusionVersion
concerns only, matching B06/B07 relevance. Existing manuscript review/OPEN history
remains readable and creatable; manuscript disposition is deferred.

Require an already committed completed action and already committed B07 exact
re-review relation; this command creates neither action, Decision nor review.
Require all applicable B06/B07 admission, hash and correspondence checks. B07
approval and tested implementation are prerequisites, not inferred from its file.
In particular, B07-AQ-01/02 (§11.4 of the B07 draft) remain unresolved: both new
relations require explicit owner/ADR approval and registry/field-contract admission.
The re-review relation and this draft's dependent FK are conditional on that outcome.
Reuse ReviewIssue + ReviewIssueEvent, with additional concrete event basis fields;
no new canonical entity, receipt table, JSON semantic core or infrastructure.

## 3. Invariants and conservative judgments

### 3.1 Finite transition and authority policy

The following are **proposed conservative B08 policy refinements** of Correction
12, not claims that current code implements them. Every new transition requires
ACTIVE project, live verified credential/binding/membership, HUMAN actor and
independence from old target authors, result/re-review target authors and action
creator. Reuse B07's traversed-material author checks; no asserted actor/role input.

| Transition | Actor and exact basis |
| --- | --- |
| OPEN→ADDRESSED | Original Issue-opening reviewer with current REVIEWER or OWNER, or an independent current OWNER. Require a B06 changed action, exact B07 linked re-review, and the re-review's HUMAN author independent under B07. For BLOCKING also require a matching REVISION_RESPONSE/REQUIRE_CHANGE Decision bound to this Issue and cited by that action. |
| OPEN→DISMISSED | Independent current HUMAN OWNER. Require B07 REVISION_RESPONSE/ACCEPT_NO_CHANGE Decision bound to this Issue, its NO_CHANGE action and exact linked re-review of the unchanged old target/hash. Decision is mandatory at every severity. |

Issue opener is derived from its original review, never a caller assertion.
An opener without OWNER cannot dismiss. A new REVIEWER who did not open the Issue
cannot perform disposition merely by authoring a re-review. Disposition actor may
be the independent re-review author; no additional separation between those two
roles is required. Decider independence is B07's policy; do not invent HUMAN-only
revision Decision authorship or require the decider to equal the disposer.

For nonblocking ADDRESSED, Decision is optional; if supplied it must be matching
REQUIRE_CHANGE and equal the action's decision_record_id. An action citing a
Decision must always include that same Decision in the event. For blocking
ADDRESSED, an Issue-only action is insufficient: record eligible combined/Decision
basis through B07, without rewriting the old action. DISMISSED never uses a changed
action or release PROCEED. NO_CHANGE can never yield ADDRESSED, even for INFO.

### 3.2 Exact new re-review and closure

Select exactly one B07 `(revision_action_id, internal_review_record_id)` relation.
Derive its effective Issue, project, old target/hash and exact result witness;
verify complete saved Decision/action/review hashes and concrete relation membership.
The action must have no successor at the protected transition point. Re-review
must postdate or equal action creation and differ from the Issue's original review.
Same project, parent identity, text, recommendation or unlinked same-target review
is insufficient. B07's six mapping predicates apply verbatim: exact changed Claim/
conclusion; exact Run+Spec Measurement witness; exact StatisticalResult; exact
SourceVersion support witness; unchanged old target for NO_CHANGE. Do not add Run,
SourceVersion or StatisticalResult as direct review targets.

Propose a conservative acceptance gate: selected re-review recommendation is
ACCEPT or MINOR_REVISION, and that exact review has no OPEN MAJOR/BLOCKING Issue.
Its other Issues stay visible and unchanged. REJECT/UNCERTAIN/MAJOR_REVISION links
remain historical B07 facts but cannot support a new B08 transition. Review text
is not machine proof that a concern was fixed; the authorized actor explicitly
attests that correspondence and disposition in the event's nonblank rationale.

Historical old target may be STALE/INVALID if exact frozen historical closure
verifies. ADDRESSED requires B06-valid completed result and currently VALID exact
re-review target/closure. DISMISSED verifies historical old closure and reports its
current validity honestly; ACCEPT_NO_CHANGE never converts STALE/INVALID to VALID
or permits release. For all BLOCKING transitions verify the Decision's exact
concern/old target and full saved basis as well as these result/re-review checks.
New concerns on old or new targets remain separate OPEN Issues; no status transfer,
automatic cloning or “latest wins”. Gate consumers still scan all applicable OPEN
BLOCKING Issues, including those in reviews outside the selected re-review.

## 4. Proposed commands, DTOs and historical readback

`record_issue_disposition(principal, command)` atomically appends the terminal
IssueEvent and updates only Issue.status, returning the saved event/readback.
Its UUID is the event's ID and replay key, not a second command receipt.
`get_issue_disposition(principal, project_id, id)` reads that exact terminal event;
`get_issue_history(principal, project_id, review_issue_id)` returns the original
Issue, OPEN event and optional terminal event with exact basis and current validity.

Readers are current OWNER, RESEARCHER, REVIEWER, VIEWER or APPROVER with live
verified entitlement, following DecisionService._READERS. Foreign scope yields
nondisclosing FORBIDDEN; entitled absent IDs yield NOT_FOUND. Authenticate before
existence disclosure. Reads contain typed DTOs, never ORM or credentials.

## 5. Schema and literal hash proposal — no migration

Extend existing `review_issue_events`, not ReviewIssue material, with rationale
and concrete action/re-review/Decision FKs (§12.1). Issue.status is the sole current
projection and must equal its event history. No extra current-status pointer.
Retain original OPEN event IDs/times/actors and every Issue descriptor, relation,
ordinal and created_at. Retain all accepted Review/Decision/RevisionAction hashes.
Events have no registered content-hash payload: enforce immutable membership and
verify referenced hashes; do not claim the event rationale or basis selection is
cryptographically covered by the Review hash. A new hash scheme requires a separate
approved amendment, not an implementer-added payload field.

## 6. Error contract — proposed use of existing categories

Use §11.2's existing ErrorCode categories, HTTP/CLI mappings and sanitized messages.
Caller shape errors differ from corrupt saved provenance. Named SQL constraint
normalization is required; never expose driver chains or infer success from a
unique violation without rollback and saved-record comparison.

## 7. Transactions, concurrency and failure recovery

One command is one READ COMMITTED UoW with SHARE(B) as its FIRST transactional SQL
statement. Existing pre-BEGIN connection configuration bounds even that first wait.
The inventory, request lock, review locks and Issue row exclusion are fixed in
§12.2. Issue exclusion serializes disposition and the B06/B07 action-insert guards;
action rows are read without locking to avoid inversion with B07 mapping writers.

UUID replay requires original actor, identical normalized command and current read
entitlement; verify saved history/basis without requiring current write role,
current scientific validity or still-terminal action. Changed same-ID material is
IDEMPOTENCY_CONFLICT. Different UUID against a terminal Issue is
INVALID_STATE_TRANSITION, even if desired status matches. Unknown commit outcome
is recovered by the same UUID; do not blindly create another event.

Only SQLSTATE 40001/40P01 retry: three total fresh UoWs, no delay/external call,
redo all locks/reads/authority. Force deferred guards before final fresh-clock
checks. Timeout rolls back with existing sanitized fallback, without blind retry.
Failure between event insertion and status projection, or during constraints,
leaves neither transition nor event. Historical reads follow the distinct protocol.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

§12.4 pins concrete test artifacts. Test each transition/severity/role/action/
Decision/recommendation tuple, exact result correspondence, immutable history,
normal-role SQL bypass attempts, rollback/restart and observable concurrency in both
commit orders. Current baseline checks do not execute any proposed B08 behavior.

## 9. Acceptance criteria and evidence boundary

Owner approval must accept §11 policy and §12's field/guard refinement, followed
by architecture registry/field-contract admission and separate implementation
pack. B07 must be approved, implemented and verified first. No open P0/P1 permits
engineering acceptance. Require real PostgreSQL 18.x catalog/migration/constraint/
race evidence, static/unit/architecture checks and inherited review/Decision/
Approval regressions. The external loop owns the whole-suite run. This document
cannot declare B08 implementation, Phase 2 exit, release or submission acceptance.

## 10. Glossary

| Term | Meaning here |
| --- | --- |
| ReviewIssue / concern | Exact original assessment fact and its operational status; descriptors never edited. |
| Disposition | Authorized judgment that one concern is addressed or dismissed, recorded separately from Review. |
| ADDRESSED | Completed changed response and acceptable independent exact re-review; never NO_CHANGE. |
| DISMISSED | Independent OWNER accepts no material change on explicit Decision basis; not scientific validation. |
| ReviewIssueEvent | Existing immutable OPEN/terminal transition history, including actor, DB time and exact basis. |
| Effective Issue | B07-derived Issue from action Issue/Decision basis; both supplied forms must agree. |
| Re-review link | B07 immutable action→exact review correspondence; alone it grants no disposition. |
| Historical closure / current validity | Verified saved refs/hashes versus today's VALID/STALE/INVALID projection. |
| B / protected snapshot | §12.2's table inventory held SHARE before selecting write inputs. |
| Replay | Same event UUID/actor/normalized inputs, disclosed under current read authority. |

## 11. Decisions taken in this draft

These decisions are proposed for owner approval; none authorizes implementation.

### 11.1 Scope and policy decisions

| Choice | Adopted decision |
| --- | --- |
| Scope | One terminal disposition per Claim/conclusion Issue; exact B07 re-review prerequisite. |
| Authority | §3.1's HUMAN opener REVIEWER/OWNER or independent OWNER for ADDRESSED; independent HUMAN OWNER only for DISMISSED. |
| Changed versus unchanged | Five B06 changed shapes for ADDRESSED; B07 NO_CHANGE + ACCEPT_NO_CHANGE for DISMISSED. |
| BLOCKING | Matching revision Decision mandatory; no release PROCEED or authority override of facts. |
| Review quality | §3.2's ACCEPT/MINOR_REVISION and no selected-review OPEN MAJOR/BLOCKING Issues. |
| History/correction | OPEN→terminal only; new concerns require new Issues through existing review creation, never reopen/delete. Event correction/adjudication is deferred. |
| Persistence | Extend registered event pattern, concrete FKs and deferred projection consistency; no new B08 table/hash/receipt. B07 takes option (b) for both unregistered relations (§11.4); require owner/ADR admission before implementing the dependent `fk_b08_event_mapping`. If redesigned/rejected, revise both drafts before execution. |
| Replay/read | Original actor plus current read entitlement; snapshot reads have no explicit exclusion locks. |
| Adapters | Application contract only; API/CLI endpoints deferred, mappings pinned for compatibility. |

### 11.2 Pinned error mappings

Rows match `src/researchbase/api/errors.py` and `src/researchbase/cli/errors.py`.

| Error code | HTTP status | CLI exit | Trigger |
| --- | --- | --- | --- |
| AUTHENTICATION_REQUIRED | 401 | 3 | Missing trusted principal. |
| FORBIDDEN | 403 | 3 | Lost entitlement, foreign scope, wrong role or different-actor replay. |
| VALIDATION_ERROR | 422 | 2 | Unknown field, wrong UUID/enum, blank/oversize/invalid Unicode rationale. |
| NOT_FOUND | 404 | 3 | Entitled exact object absent. |
| CONFLICT_OF_INTEREST | 403 | 3 | Disposer/re-reviewer/decider independence fails. |
| FROZEN_REFERENCE_REQUIRED | 409 | 5 | Required result/target not frozen or Run inputs unsealed. |
| DECISION_BASIS_INVALID | 409 | 4 | Missing mandatory Decision, wrong purpose/value/Issue/action binding. |
| INVALID_STATE_TRANSITION | 409 | 4 | Terminal Issue, superseded action, deferred target or unacceptable re-review. |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Event UUID reused with different normalized material. |
| IMMUTABLE_RECORD | 409 | 4 | Update/delete history, late basis or Issue descriptor edit. |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Concrete FK violation. |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Saved graph/hash/history mismatch, unrelated link, invalid required changed result. |
| CONCURRENT_MODIFICATION | 409 | 4 | 40001/40P01 after three total attempts. |

Reuse UoW P17R1→INVALID_STATE_TRANSITION, P17F1→IMMUTABLE_RECORD,
P17F2→PROVENANCE_CLOSURE_VIOLATION. Add named unique handling for
`uq_b08_issue_terminal`: rollback/reload under entitlement, compare same event UUID
for replay; another UUID gets INVALID_STATE_TRANSITION. Primary-key collision
also reloads/compares after rollback, never swallows the failed statement.
Timeout/unknown DB errors retain sanitized INVALID_STATE_TRANSITION fallback;
only SQLSTATE determines retry eligibility. Unexpected transport fallback remains
HTTP 500 `INTERNAL_ERROR`, CLI exit 1, with no raw diagnostics.

### 11.3 DTO fields, Python types and limits

Closed frozen dataclasses with slots. UUID means exact `uuid.UUID`, with canonical
lowercase hyphenated transport text if adapters are later authorized. Datetimes
are aware UTC; hashes lowercase 64-hex. Reject extras and actor/time/hash/status
assertions outside the declared fields. Rationale: NFC, strict UTF-8, nonblank,
1..16,000 Unicode characters after normalization; preserve meaningful whitespace.
No bool/int/string coercion into UUID or enum. No caller-generated basis hashes.

```python
Disposition = Literal["ADDRESSED", "DISMISSED"]
IssueStatus = Literal["OPEN", "ADDRESSED", "DISMISSED"]
Validity = Literal["VALID", "STALE", "INVALID"]
IssueType = Literal[
    "UNSUPPORTED_CLAIM", "CITATION", "STATISTICAL", "METHODOLOGICAL",
    "REPRODUCIBILITY", "OVERCLAIM", "CONTRADICTION", "NOVELTY", "WRITING", "OTHER",
]
EligibleAction = Literal[
    "NEW_EXPERIMENT", "ANALYSIS_CHANGE", "CLAIM_CHANGE", "CONCLUSION_CHANGE",
    "SOURCE_CHANGE", "NO_CHANGE",
]

# RecordIssueDispositionCommand; all required except decision_id default.
id: UUID
project_id: UUID
review_issue_id: UUID
disposition: Disposition
revision_action_id: UUID
re_review_record_id: UUID
rationale: str
decision_id: UUID | None = None
```

| Readback | Exact fields/types |
| --- | --- |
| IssueDispositionReadback | id, project_id, review_issue_id, actor_id, revision_action_id, re_review_record_id: UUID; decision_id: UUID\|None; prior_status: Literal["OPEN"]; new_status: Disposition; rationale: str; occurred_at: datetime; action_content_hash, re_review_content_hash: str; decision_content_hash: str\|None; old_target_validity, re_review_target_validity: Validity; has_superseding_action: bool. |
| IssueEventReadback | id, review_issue_id, actor_id: UUID; prior_status: Literal["OPEN"]\|None; new_status: IssueStatus; occurred_at: datetime; revision_action_id, re_review_record_id, decision_id: UUID\|None; rationale: str\|None. OPEN has NULL prior/basis/rationale; terminal follows command shape. |
| IssueHistoryReadback | project_id, review_issue_id, original_review_id: UUID; severity: Literal["INFO","MINOR","MAJOR","BLOCKING"]; issue_type: IssueType; description: str; status: IssueStatus; created_at: datetime; claim_version_id, scientific_conclusion_version_id: UUID\|None XOR for supported disposition targets; target_content_hash: str; target_validity: Validity; events: tuple[IssueEventReadback, ...]; disposition: IssueDispositionReadback\|None. |

History accepts existing manuscript OPEN records too: extend its concrete target
fields with `manuscript_version_id: UUID|None` (three-way XOR), not a generic
locator. Preserve the existing review Issue readback fields; do not change Review
hash material. Events are ordered root then terminal by transition, not arbitrary
UUID/time tie order. A terminal history always has exactly two events. Exact
queries take `(principal: VerifiedPrincipal, project_id: UUID, id: UUID)` or
`review_issue_id: UUID` as specified in §4. No pagination or list command here.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

Conditional sketch only. `revision_action_re_reviews` is an unapproved B07-AQ-02
proposal, not an existing registered relation. Do not implement the dependent
`fk_b08_event_mapping` until owner/ADR approval, registry/field-contract updates
and verified B07 implementation; if it is rejected/redesigned, revise this sketch
and mapping policies/tests first. Check the actual Alembic head after B07; allocate
one forward file
under `migrations/versions/`, never edit shipped 0040/0041/0042/0051. Preflight
retained Issue/root-event consistency; refuse corrupt legacy rows. Inspect catalog
names before replacing 0040's generated checks (`review_issues_status_check`,
`review_issue_events_new_status_check`, `review_issue_events_prior_status_check`)
and `review_issue_events_issue_id_key`; do not drop unrelated constraints.

```sql
ALTER TABLE review_issues DROP CONSTRAINT review_issues_status_check;
ALTER TABLE review_issue_events
  DROP CONSTRAINT review_issue_events_new_status_check,
  DROP CONSTRAINT review_issue_events_prior_status_check,
  DROP CONSTRAINT review_issue_events_issue_id_key;
ALTER TABLE review_issues ADD CONSTRAINT ck_b08_issue_status
  CHECK (status IN ('OPEN','ADDRESSED','DISMISSED'));
ALTER TABLE review_issue_events
  ADD COLUMN revision_action_id UUID,
  ADD COLUMN re_review_record_id UUID,
  ADD COLUMN decision_id UUID,
  ADD COLUMN rationale TEXT,
  ADD CONSTRAINT fk_b08_event_action FOREIGN KEY (revision_action_id)
    REFERENCES revision_actions(id) ON DELETE RESTRICT,
  ADD CONSTRAINT fk_b08_event_re_review FOREIGN KEY (re_review_record_id)
    REFERENCES internal_review_records(id) ON DELETE RESTRICT,
  ADD CONSTRAINT fk_b08_event_decision FOREIGN KEY (decision_id)
    REFERENCES decision_records(id) ON DELETE RESTRICT,
  -- Conditional on B07-AQ-02 owner/ADR admission; not currently available.
  ADD CONSTRAINT fk_b08_event_mapping
    FOREIGN KEY (revision_action_id,re_review_record_id)
    REFERENCES revision_action_re_reviews(revision_action_id,internal_review_record_id)
    ON DELETE RESTRICT,
  ADD CONSTRAINT ck_b08_event_shape CHECK (
    (prior_status IS NULL AND new_status='OPEN'
      AND revision_action_id IS NULL AND re_review_record_id IS NULL
      AND decision_id IS NULL AND rationale IS NULL) OR
    (prior_status IS NOT NULL AND prior_status='OPEN'
      AND new_status IN ('ADDRESSED','DISMISSED')
      AND revision_action_id IS NOT NULL AND re_review_record_id IS NOT NULL
      AND rationale IS NOT NULL AND length(btrim(rationale)) BETWEEN 1 AND 16000
      AND (new_status<>'DISMISSED' OR decision_id IS NOT NULL)));
CREATE UNIQUE INDEX uq_b08_issue_open ON review_issue_events(issue_id)
  WHERE prior_status IS NULL;
CREATE UNIQUE INDEX uq_b08_issue_terminal ON review_issue_events(issue_id)
  WHERE prior_status='OPEN';
CREATE INDEX ix_b08_event_action ON review_issue_events(revision_action_id);
CREATE INDEX ix_b08_event_re_review ON review_issue_events(re_review_record_id);
CREATE INDEX ix_b08_event_decision ON review_issue_events(decision_id);
```

Keep existing event `id UUID PK`, `issue_id UUID NOT NULL`, `actor_id UUID NOT
NULL`, `prior_status VARCHAR(16) NULL`, `new_status VARCHAR(16) NOT NULL`,
`occurred_at TIMESTAMPTZ NOT NULL` and original Issue/actor RESTRICT FKs. New UUID/
TEXT columns are nullable for retained roots. No root backfill or history rewrite.
CHECK explicitly uses IS NOT NULL to avoid PostgreSQL UNKNOWN accepting missing
terminal prior/rationale. The three-way enum is finite, not caller policy.

Implement these named guards/functions in the same migration:

| Guard | Required SQL behavior |
| --- | --- |
| `pr214_issue_guard` replacement | INSERT preserves same-project reference checks and requires status OPEN. Strengthen its final exact review-row lock from FOR SHARE to FOR UPDATE, after the existing target coordination, so late Issue INSERTs conflict with disposition’s review SHARE locks. This is a proposed guard refinement, not existing behavior. DELETE always P17F1. UPDATE permits **only** OPEN→terminal status, every other column `IS NOT DISTINCT FROM` OLD; matching terminal event must already exist, inserted in this transaction (0042 parent-xmin pattern), with the same transition. Otherwise P17F1/P17F2. Remove 0041's scientific row-lock path from the UPDATE branch only; INSERT keeps its existing coordination. |
| `b08_event_guard` BEFORE INSERT | OPEN requires same-transaction newly inserted Issue, exact original reviewer actor/time and no basis. Terminal takes SHARE(B), review SHARE locks then the sorted mixed-mode Issue pass in §12.2 order, rereads status/successor and enforces supported target, effective Issue/project, B07 mapping, action/Decision shape, HUMAN independence, timestamps and re-review gate. Set terminal occurred_at from clock_timestamp(), not caller time. Reject orphan/duplicate/mismatched root or basis with P17F2/P17R1. |
| `b08_project_status` AFTER INSERT | Terminal event updates only corresponding Issue.status; root does not update Issue. Event exists before guarded UPDATE. No second event trigger or recursive success insertion. |
| `b08_complete_issue` constraint trigger AFTER INSERT OR UPDATE on review_issues | DEFERRABLE INITIALLY DEFERRED; call `b08_check_history(issue_id)`. |
| `b08_complete_event` constraint trigger AFTER INSERT on review_issue_events | DEFERRABLE INITIALLY DEFERRED; same final-history function. |
| `b08_check_history` | Exactly one correct OPEN root; OPEN projection has no terminal; terminal projection has exactly one matching terminal and valid complete basis. Verify Issue→review actor/time and terminal time≥root/action/re-review/link/Decision times. Parent/root cannot commit missing its other half. Use immutable structural provenance checks for retained events; do not retroactively require current role/validity or unsuperseded actions on historical events. |
| Existing `pr214_issue_events_immutable` | Retain BEFORE UPDATE OR DELETE rejection. Appending changed/late event basis is impossible because basis is on that immutable event, not a mutable child set. |

SQL structural validation repeats the finite result, concern, Decision and re-review
predicates from §3/B07; no arbitrary JSON locator or session-variable bypass token.
Use existing historical project-role/actor checks for attribution, while live
credential and complete hash/validity checks remain mandatory in Application.
Normal-role SQL cannot forge a structurally unrelated or incomplete disposition;
no claim is made that database superusers cannot bypass triggers. FORCE deferred
checks with `SET CONSTRAINTS ALL IMMEDIATE` before final authority checks.

Migration downgrade takes ACCESS EXCLUSIVE on both existing tables, refuses if
any terminal event/status or nonnull new basis exists, then restores old checks,
one-event uniqueness and guard definitions (including the prior INSERT lock mode). OPEN-only data downgrades without
rewriting it; populated terminal history never disappears. Test fresh install,
B07 populated upgrade and this refusal explicitly.

### 12.2 Exact lock order and transactions

B is B07's inventory: shipped `REVISION_SNAPSHOT_TABLES` plus
`internal_review_records`, lexical order:

```text
actor_subject_bindings, actors, artifact_versions, artifacts, audit_findings,
claims, correction_records, datasets, experiment_spec_versions, experiment_specs,
impact_assessments, impact_targets, internal_review_records, literature_evidence,
literature_evidence_review_events, literature_source_project_links,
literature_sources, metric_definition_versions, metric_definitions,
project_membership_events, project_memberships, project_role_assignments,
projects, runs, scientific_conclusions, source_versions
```

One `LOCK TABLE <B in that order> IN SHARE MODE` statement, acquiring final modes;
no command writes B. Configure `configure_revision_transaction()` before SQL:
READ COMMITTED, lock_timeout=10s, statement_timeout=30s, restored on pool checkin.
Pre-BEGIN driver setup is not a statement in the command transaction. No SET LOCAL,
authentication query, request advisory or row lock precedes SHARE(B).

| Command | Exact ordered operations |
| --- | --- |
| `record_issue_disposition` including UUID replay | 1. First SHARE(B). 2. Existing SET LOCAL timeout bounds, then `SELECT pg_advisory_xact_lock(hashtextextended(:key,0))` with key `b08:disposition:<canonical event UUID>`. 3. Protected nonlocking adapters; current read entitlement, saved UUID/project/actor/material comparison. Replay verifies saved history/basis, rechecks fresh-time read entitlement and returns without new-creation locks/checks. 4. New request: live writer checks; discover exact old/new review IDs without locks, lock those immutable reviews `FOR SHARE` in UUID order, then collect primary Issue plus all selected re-review Issue IDs. Acquire Issue row locks in one UUID-sorted pass: primary `FOR UPDATE`, all others `FOR SHARE`. Reread their statuses and action successor **after** waiting. 5. Read exact action, Decision, B07 mapping and closure without row locks; verify §3. 6. Fresh authority/time; insert terminal event, trigger status projection; force all deferred constraints, verify readback/history, fresh authority immediately before commit. Repeat final checks after any later wait. |
| `get_issue_disposition`, `get_issue_history`, nested review/history readers | Before first query configure one REPEATABLE READ, READ ONLY UoW via existing connection pattern. Authorize current readers; read/verify original Issue, events and exact saved basis in that snapshot; derive current validity separately. Recheck intervals against fresh clock_timestamp() immediately before return. No explicit table/advisory/row locks, writes or creation retries, including inside auth/closure helpers. |

B excludes `review_issues`, events, actions and B07 relations: B08 writes Issue/
event, so including them SHARE would force upgrades. B08 takes **no action or
scientific target/parent/project row lock**. This avoids a cycle with B07 mapping
(action UPDATE→Issue SHARE) and B06/B07 correction (Issue SHARE→predecessor UPDATE).
The already committed exact link is immutable; complete-set link enumeration is
unnecessary. All B06/B07 action INSERT guards must hold effective Issue FOR SHARE
before successor check/insertion (including Decision-only bases), as B06 does.
B08's Issue UPDATE excludes those writers until commit; READ COMMITTED rereads
see a correction that committed first. Mapping additions do not change a selected
saved link. No B07 lock-order rewrite or second advisory namespace is required.

B's internal_review_records SHARE prevents new-review insertion through commit.
The strengthened Issue INSERT guard (§12.1) takes its exact parent review FOR
UPDATE; B08's FOR SHARE on old/new reviews therefore also excludes late Issue
INSERTs into those existing reviews. This refinement is required: the shipped
FOR SHARE guard alone does **not** protect that phantom. Acquire these review
locks before enumerating the selected re-review's Issue IDs. Existing Issue status
changes are excluded by the sorted mixed-mode Issue pass in step 4. All B08
commands use that same UUID order, avoiding mutual primary/secondary Issue cycles.
Reread statuses after waits; acquire no further Issue locks in step 5 or trigger
reentry. The event guard uses the same discovery, review order and sorted pass.

Compatibility with release/Approval: existing no-OPEN-BLOCKING predicates remain
required. Their SHARE review-row coordination, with the strengthened INSERT guard, prevents Issue creation but does
not exclude these monotonic OPEN→terminal writes. A concurrent release may
conservatively observe OPEN and deny; it can succeed only on committed terminal
history plus its independent current-validity checks. No blocker creation is
hidden and no old rejected Decision is replaced. Verify both orders; do not
introduce scientific row locks to make disposition imitate release.

Snapshot reads never promise to see commits after their first snapshot. Paused
reads must allow unrelated inserts and disposition commits; a fresh read observes
later history/revocation. Scheduled expiry is checked with advancing DB time even
within a snapshot. SHARE writes stabilize mutable inputs; REPEATABLE READ alone
is never substituted for the write capture protocol.

### 12.3 Ordered build steps and module paths

1. Obtain approval/admission and B07 acceptance, including explicit owner/ADR
   resolution of B07-AQ-01/02 and registry/field-contract entries for the admitted
   relations. Verify the accepted re-review relation matches this draft's FK;
   otherwise revise both drafts before building. Inspect head; add one forward
   file under `migrations/versions/` with §12.1's exact types, names and guards.
2. Extend `src/researchbase/domain/internal_review.py` with pure enums, rationale
   normalization and finite disposition predicates; preserve review_material.
3. Extend `src/researchbase/application/internal_review.py` with §11.3 commands/
   readbacks and three methods; reuse nonlocking B06/B07 verifiers within the same
   UoW, never call a service that commits a separate transaction. Replace OPEN-only
   manuscript history validation with shared root/terminal history validation;
   preserve unsupported manuscript disposition denial. Existing review reads must
   accept valid terminal histories and still reject corrupt ones.
4. Extend `src/researchbase/application/ports.py`,
   `src/researchbase/persistence/internal_review_repository.py` and
   `src/researchbase/persistence/uow.py` for exact event lookup/insert, sorted Issue
   locks, historical DTOs, protected readers and named error normalization. Reuse
   `src/researchbase/persistence/database.py` timeout setup/restore. Extend existing
   SQL repositories only; no parallel ORM owner or new runtime dependency.
5. Audit current status consumers in `application/decision.py`,
   `application/approval.py`, `persistence/decision_repository.py` and
   `persistence/approval_repository.py`: preserve exact-target no-OPEN-BLOCKING
   predicates and verify terminal event integrity where exposed. Preserve all
   scientific validity, complete Decision basis and independent Approval gates.
6. Add §12.4 tests and run focused checks, report actual counts/version/findings,
   stop. API/CLI remain deferred; future thin adapters must use §11.2 unchanged.

### 12.4 Test artifacts and required cases

All B08 files below are **planned, not present implementation**. Use existing
PostgreSQL 18.x disposable fixture conventions; export shared builders rather
than introducing test-module fixture coupling. Two engines/backend PIDs and
pg_blocking_pids/pg_stat_activity are required for races, not sleep-only evidence.

| File | Required cases |
| --- | --- |
| `tests/unit/phase2/test_b08_issue_disposition.py` | Every DTO field/extra rejection; strict UUID/enum, NFC/UTF-8/nonblank/16,000 boundaries; all transition/severity/role/action/Decision tuples; no caller authority; readback NULL root versus terminal shape. |
| `tests/unit/phase2/test_pr2_15_uow_errors.py` (extend) | Every pinned mapping, named uniqueness reload/compare, sanitized timeout, only 40001/40P01 retry and exactly three attempts; unknown commit recovered with original UUID. |
| `tests/architecture/test_b08_issue_disposition.py` | Owner/ADR and registry/field-contract admission gate for B07-AQ-01/02 and dependent mapping FK; Application-only writes, no new B08 entity/table/JSON core/hash/receipt/ExternalEffect; same Human/Agent boundary but HUMAN disposition policy; unchanged Phase 1/Review/Decision/action literal hash vectors; no explicit locks in every nested read helper. |
| `tests/integration/phase2/test_b08_issue_disposition.py` | Claim/conclusion and all five changed shapes; opener REVIEWER and independent OWNER; changed blocking needs REQUIRE_CHANGE; dismissal all severities needs ACCEPT_NO_CHANGE+NO_CHANGE; exact explicitly attested linked review and favorable gate; same-target unlinked reviews and links belonging to another action with the same result deny; wrong/foreign/unlinked/superseded/invalid result denies atomically; historical invalid old target dismissal never restores validity. |
| `tests/integration/phase2/test_b08_issue_history.py` | Original Issue fields/root event unchanged; exactly two events and correct projection; B07 indirect witnesses, new concerns remain OPEN; old review reads (including manuscript) work; independent authority and no Agent disposer; exact replay after writer-role loss/result invalidity/action supersession, read loss/different actor/changed payload denial; terminal new UUID denied; restart and lost acknowledgment. |
| `tests/integration/phase2/test_b08_schema.py` | Catalog names/types/check NULL behavior/FK RESTRICT; clean install, populated B07 upgrade, OPEN-only downgrade, terminal downgrade refusal; late Issue INSERT versus review SHARE exclusion; normal-role SQL descriptor/status edits, fake/missing root, orphan event, wrong effective Issue/Decision/mapping, duplicate terminal, late basis and UPDATE/DELETE rejection; event-only path produces projection, missing half cannot commit; deferred rollback. |
| `tests/integration/phase2/test_b08_concurrency.py` | First SQL SHARE(B), exact inventory/timeouts; different UUID same Issue and same UUID races; correction/disposition both orders, B07 map/action-lock inversion absent, selected-review Issue disposition both orders and sorted multi-Issue locks; review and late Issue INSERT phantoms blocked; role/credential/source/evidence/validity writers both orders; expiry across every wait; event/projection/constraint failure injection leaves zero partial writes. |

Paused REPEATABLE READ tests must prove unrelated INSERT/disposition commits
before read completion, remains outside that snapshot, then appears on fresh read;
assert no LOCK TABLE/advisory/FOR SHARE/FOR UPDATE anywhere in read SQL. Include
current read entitlement and scheduled expiry. Regression suites: existing
`test_revision_action.py`, `test_b06_revision_action.py`,
`test_b06_revision_concurrency.py`, `test_pr2_14_internal_review.py`,
`test_pr2_14_conclusion_review.py`, `test_pr2_15_decision.py`,
`test_pr2_15_decision_schema.py`, `test_pr2_15_coordination.py`,
`test_pr2_18_concurrency.py` under `tests/integration/phase2/`, plus accepted B07
and Approval suites. Assert unrelated OPEN BLOCKING Issues still deny release/
Approval; disposal does not consume grants or create Decisions, revisions/reviews.

Future focused command: `uv run pytest tests/unit/phase2/test_b08_*.py
 tests/architecture/test_b08_issue_disposition.py
 tests/integration/phase2/test_b08_*.py` (one shell line), then inherited focused
regressions, `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`
and `uv run pytest tests/unit tests/architecture`. Record exact commands/counts,
connected PostgreSQL version and migration evidence. Whole-suite execution belongs
to the external loop; unimplemented tests and unavailable DB runs are never PASS.

### 12.5 Not in this slice

Manuscript/Artifact/novelty-target disposition; direct Run/Source/statistic review;
new Decision purposes; changing B07's one-Decision-per-Issue rule; re-review creation
or new result creation; reopening, disposition supersession, appeal/adjudication
or correction of a wrongly disposed Issue; batch/list commands; API/CLI endpoints;
automatic impact propagation or grant reactivation; rejection reconsideration;
release/READY/package preparation/consent/send; ExternalEffect; Agent runtime;
new infrastructure/dependencies or a new event hash contract. New concern creation
uses the existing immutable review path; it does not correct old event history.

## 13. Open questions for the owner — override register

| Owner may override before freeze | Decision adopted in this draft |
| --- | --- |
| Authority interpretation across Correction 12's two tables? | Apply stricter lifecycle policy: original independent HUMAN reviewer or independent HUMAN OWNER for ADDRESSED; independent HUMAN OWNER only for DISMISSED. |
| Decision for nonblocking dismissal? | Require ACCEPT_NO_CHANGE for every dismissal, with completed NO_CHANGE and exact independent re-review. |
| Review acceptance threshold? | ACCEPT/MINOR_REVISION and no selected-review OPEN MAJOR/BLOCKING Issues; explicit rationale attests resolution. |
| BLOCKING ADDRESSED basis? | REQUIRE_CHANGE cited by selected changed action, plus verified exact closure/re-review; Issue-only actions cannot suffice. |
| Dismiss an invalid old target? | Historical closure may verify while current validity stays STALE/INVALID; no release bypass or restored validity. |
| Late Issue insertion concurrency? | Strengthen the existing Issue INSERT parent-review lock to FOR UPDATE; disposition holds review FOR SHARE before collecting Issue IDs. Admit and test this guard refinement with the event changes. |
| Event schema and cryptographic coverage? | Admit concrete event action/re-review/rationale fields with registered Decision FK; retain existing hashes, no claim event is hash-covered. |
| Correct an erroneous terminal disposition? | Defer an explicit immutable correction/adjudication contract; never mutate/reopen history. |

Overrides require corresponding policy/DTO/DDL/lock/test and architecture contract
updates before execution authorization. This task neither requests nor assumes
that approval; this documentation revision updates B07 and B08 together.

## 14. Documentation verification note

Current joint B07/B08 revision evidence (2026-10-16), including exact commands and
counts, is recorded in [B07 §14.2](B07_Revision_Decisions_Contract_DRAFT.md#142-director-review-revision-checks-2026-10-16).
These checks do not admit either proposed relation.

### 14.1 Original draft checks (2026-10-15; historical)

Executed 2026-10-15 as documentation/current-baseline checks, not implemented B08
behavior or dependency/Phase acceptance. Only this proposal was added. No branch,
commit or push was created; the whole suite was not run. The external loop owns it.

All uv commands used this exact environment and prefix:

```bash
export UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv
export PYTHONPATH=src
uv --cache-dir /tmp/b08-uv-cache run --offline --no-sync <command>
```

| Command after that prefix | Observed result |
| --- | --- |
| `ruff check .` | All checks passed; exit 0. |
| `ruff format --check .` | 570 files already formatted; exit 0. |
| `pyright --pythonpath /Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python` | 0 errors, 0 warnings, 0 informations; exit 0. Preamble notes absent checkout-local .venv. |
| `pytest -o addopts='' -ra tests/unit tests/architecture` | 2,359 collected: 2,343 passed, 4 failed, 12 errors, 7 warnings; no skips; exit 1. |

Four failures in `tests/unit/test_hg1_runner.py` are sandbox AF_UNIX bind denials
(`PermissionError: Operation not permitted`). Twelve setup errors in
`tests/architecture/test_pr2_19_boundaries.py` require explicit RB_TEST_ADMIN_URL.
These are failures/errors, not passes. Log: `/tmp/b08-unit-architecture.log`.

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

191 collected; 1 setup error, 190 unexecuted after --maxfail=1; zero passed test
bodies or skips; exit 1. RB_TEST_ADMIN_URL (or its suite-specific alias) was unset,
before any connection. No connected PostgreSQL version or PostgreSQL PASS is
available. Log: `/tmp/b08-postgres.log`. No database URL was guessed.

A repository-local inline Python check (same uv prefix, `python -`) resolved all
20 relative links, matched all 13 error rows against api.errors._STATUS and
cli.errors.CLI_EXIT_CODES, matched 15 top-level sections/numbering to PR2-18,
compared the 26-table inventory to B06 plus internal_review_records, and checked
the exact DRAFT status: all passed. `git diff --check` passed; the new-file
whitespace check is `git diff --no-index --check /dev/null
 docs/proposals/B08_Issue_Disposition_Contract_DRAFT.md` (one shell line).
These checks do not execute proposed DDL, policies or lock protocols.
