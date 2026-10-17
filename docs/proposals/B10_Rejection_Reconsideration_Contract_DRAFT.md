# B10 Rejection Reconsideration Contract — DRAFT

**Status: APPROVED by owner 2026-10-16 — first slice authorized for implementation**

Execution note (2026-10-16): the owner's task authorizes the first conclusion slice
and §12.2's READ COMMITTED protocol. Historical documentation-only/open-approval
wording below is superseded for that slice. Implementation substitutions and
executed results are recorded in [the first-slice evidence](../phase2/B10-first-slice-evidence-2026-10-16.md).

## Start here (for the implementer)

B10 proposes an explicit, evidenced route to one new approval request after a
project/purpose rejection. It preserves every rejection and does not approve,
release or execute anything. This task changes documentation only.

Build in this order **after contract approval and separate execution authorization**:

1. Resolve the dependency and isolation questions in §§1, 9 and 13. B09 is a draft;
   no B08 contract was found. Do not implement either dependency here.
2. Add the bounded typed relations and forward guards in §12.1, after checking
   the actual migration head. Never edit migrations 0042 or 0045.
3. Add the closed reconsideration command, literal R2 basis construction and
   exact-ID read; extend B09 request/decision validation (§§4–5, 11, 12.3).
4. Apply §12.2 to every participating writer. Writes take snapshot table locks
   first; reads and completed replay use one lock-free REPEATABLE READ snapshot.
5. Add §12.4 tests, execute focused checks, record exact evidence and stop.

Read §1 for authority, §3 for evidence policy, §11 for pinned choices and §12 for
construction. Use §10 as a glossary. Five rules fail review if violated:

1. Cite **all** earlier REJECT decisions in the same project/purpose, not only
   the last rejection or the old target's lineage.
2. Require fresh independent review plus a completed relevant change or an
   explicit correction of an earlier review error; favorable opinion alone fails.
3. Bind exact frozen IDs/hashes through admitted concrete FKs. Keep Review,
   Decision, Approval and completed RevisionAction distinct.
4. Bind a reconsideration to only one successor request. Recheck the complete
   rejection set at request creation and approval decision, including old PENDING
   requests. Never clear a global rejection flag or reactivate old grants.
5. Preserve historical reads/replay with current disclosure authority; do not
   report planned tests or inaccessible PostgreSQL checks as passing.

This is a proposed contract, not an architecture amendment, execution pack,
migration authorization, backlog acceptance or Phase 2 completion declaration.

## 1. Purpose, authority and inspected baseline

| Source | Constraint carried into this proposal |
| --- | --- |
| [System 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 7–9 | Deterministic facts precede authority; immutable formal history and exact frozen provenance; common Application boundary. |
| [Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A18–A23; [Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md) | Bounded admission of rejection request FKs and two concrete Decision basis relations; no new canonical entity. |
| [Compatibility 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§9, 12–18, 24, 38 | Preserve command/error semantics and hashes; additive migrations; material deviations require architecture review. |
| [Phase 2 spec 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), governance and PR2-15/16; [Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md); [Fields 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md), governance | Rejection cannot be silently resubmitted; typed immutable governance records. R2 overrides conflicting older fields. |
| [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md), “Review, decision, approval, and revision” | Exact DecisionRecord and basis-set payloads already include ApprovalDecision and RevisionAction reference kinds. |
| [Governance R2 17](../architecture/17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md), §§1–2, 4–5 | Project/purpose equivalence, all-rejections coverage, independent HUMAN reconsiderer, two evidence grounds, unique successor and deferred cycle rejection. |
| [R3 18](../architecture/18_Phase2_Design_R3_Targeted_Remediation_v1.0.md); [Temporal R4 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md) | Fresh database time and live authority after waits; historical replay is separate from current admission. No grant consumption is introduced here. |
| [Minimal Decision 20](../architecture/20_PR2_15_Minimal_Decision_Command_Contract_v1.0.md); [Harness spec](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 18–19 | Existing PROCEED cannot substitute for reconsideration or disposition; external tools do not own persistence or scientific truth. |
| [B09](B09_Approval_Tuples_Contract_DRAFT.md), §§3.1, 12; [PR2-17](PR2-17_Submission_Authorship_Contract_DRAFT.md); [PR2-18](PR2-18_Novelty_PriorArt_Contract_DRAFT.md) | B09 finite tuple/fence dependency; reference draft structure and explicit evidence/dependency boundaries. |

Inspected source is narrower than R2's full design:

- [approval.py](../../src/researchbase/application/approval.py) exposes two writes
  and three exact reads; `_gate` calls the project-only `rejected(project)` fence.
  [0045](../../migrations/versions/0045_pr2_16_basic_approval.py) has both request
  link FKs but CHECKs them NULL. B09 purpose-scoping is not yet shipped here.
- [Decision domain](../../src/researchbase/domain/decision.py) accepts the R2 basis
  kinds, but [DecisionService](../../src/researchbase/application/decision.py) and
  [0042](../../migrations/versions/0042_pr2_15_minimal_decision.py) admit only
  INTERNAL_SCIENTIFIC_RELEASE/PROCEED and conclusion/review basis. Existing
  complete-basis triggers cannot admit reconsideration without explicit dispatch.
- [0051](../../migrations/versions/0051_b06_revision_action.py) extends issue-based
  RevisionAction shapes; Decision-bearing and manuscript-result actions remain
  unavailable. [B04 persistence](../../src/researchbase/persistence/manuscript_freeze_repository.py)
  and [B05 review](../../src/researchbase/application/internal_review.py) exist;
  their presence does not supply manuscript-purpose affirmative Decisions.
- No B08 document or B10 execution pack was found under `docs/`. Do not guess
  B08's scope, enums, evidence verifier or acceptance from its backlog number.

The first-statement SHARE protocol below follows B04 and the coverage path in
[novelty_repository.py](../../src/researchbase/persistence/novelty_repository.py).
[decision_repository.py](../../src/researchbase/persistence/decision_repository.py)
uses the same SHARE mechanism but currently takes advisory/target locks first.
This draft deliberately specifies the requested table-first order; it does not
claim all existing writers already follow it.

## 2. Scope, dependency boundaries and non-goals

Propose `record_rejection_reconsideration`, `get_rejection_reconsideration`, and
additive optional links on B09's `request_approval`. Extend `decide_approval`'s
fence recheck without changing its outcome or grant semantics. The first bounded
branch is INTERNAL_SCIENTIFIC_RELEASE with an exact ScientificConclusionVersion.
Both R2 evidence grounds are specified below. Manuscript branches remain blocked
on B09, their affirmative Decision contracts and B08 wherever its approved
contract supplies missing evidence/relevance rules. Missing dependencies deny;
they are not implemented opportunistically.

No new entity, receipt, rejection-status projection, fingerprint, generic JSON
basis, queue, dependency or persistence mechanism. A reconsideration Decision is
not the ordinary affirmative `basis_decision_id`: a successor needs **both**.

## 3. Invariants and conservative judgments

The equivalence scope is exactly `(project_id, approval_purpose)` under R2 §2.
Include every committed prior REJECT, even a previously reconsidered rejection,
from unrelated target lineages or publications. Rejected requests stay DECIDED;
REJECT is an ApprovalDecision outcome, not a new request status.

A reconsideration is immutable, has `decision_type=RECONSIDER_REJECTION`, and
binds one exact new frozen, currently VALID target. Its actor is a currently
credentialed HUMAN APPROVER, different from **every** cited rejecting approver,
new target material author/contributor and required reviewer. At successor create
and decide, also require that actor differs from the actual requester. OWNER
alone, Agent delegation and `acting_on_behalf_of` cannot substitute. Retain B09's
independent subsequent approver rules, additionally excluding the reconsiderer.

### 3.1 Evidence grounds — proposed bounded policy

Every cited rejection must have a witness under the selected ground. Mixed
grounds within one Decision are deferred; no partial justification is accepted.

| Decision outcome | Required exact prior and fresh evidence |
| --- | --- |
| `REVISED_TARGET` | For each rejection, an already committed immutable RevisionAction whose saved Issue → Review targets that rejection's old conclusion, with `action_type=CONCLUSION_CHANGE` and `result_scientific_conclusion_version_id` equal to the new target. New target is a strictly higher frozen version under the same scientific_conclusion_id. Fresh HUMAN independent review of the new exact version/hash is mandatory. |
| `CORRECTED_REVIEW` | For each rejection, at least one corrected prior InternalReviewRecord from that rejected request's sealed review set and at least one fresh independent HUMAN review of the new exact target/hash. Rationale names each rejection and corrected review UUID and describes the specific factual/assessment error and reasoned correction; reviewers' summaries must support that correction. Mere recommendation change fails. Unchanged target material is allowed. |

Fresh means committed before the reconsideration and created strictly after
**every** cited rejection's decided_at, using DB time, by a reviewer different
from all cited rejecting actors and old corrected reviewers as well as target
authors, requester and reconsiderer. Verify historical reviewer creation authority,
review hash, exact target binding and frozen provenance. Select all eligible
new-target reviews, not a favorable subset; at least one satisfies freshness.
Any matching record with a corrupt hash/binding fails closed; do not omit it as
ineligible. Prior commitment is a database visibility/transaction check, not
merely a caller timestamp comparison.
For the correction ground include the specified old reviews as well. An old
review's target may now be SUPERSEDED or invalid; verify saved history without
requiring the rejected scientific position to become currently valid.

For the first revised-target branch, compare the actual conclusion `statement`,
four-key `scope`, `confidence`, `limitation_summary` and expanded support material
from [scientific_conclusion.py](../../src/researchbase/domain/scientific_conclusion.py).
As a conservative first admission rule, require a change in at least one of the
four non-support fields after NFC and whitespace collapse on text leaves.
Support-only changes remain blocked pending an approved material-comparison
contract (B08 if applicable). A changed own hash, version number, parent UUID,
input UUID, ordinal or whitespace alone is insufficient. Do not persist this
comparison or its digest. Rationale and the fresh review explain why the detected
change addresses **each** rejection; this relevance judgment is attributable
human assessment, not a deterministic scientific truth inferred from text.
Manuscript/document-byte comparison is not inferred from unequal artifact hashes.

### 3.2 Successor and cycle rules

`prior_rejected_request_id` is one anchor, chosen deterministically as the rejection
with greatest `(decided_at, canonical decision UUID)`; it does not replace the
complete typed rejection set. `reconsideration_decision_id` is unique among
successor requests. Both links are NULL before any rejection and both nonnull
when reconsideration is required. The Decision must predate the successor and
match project, purpose and exact target/hash. A saved unused reconsideration is
not a reservation and does not unblock other requests.

At create and first approval decision, recompute the entire same-scope rejection
set under common exclusion. Any new rejection not in the sealed reconsideration
basis denies with REJECTION_RECONSIDERATION_REQUIRED. An older PENDING request
cannot be retrofitted with links; create a new successor. On later rejection,
new reconsideration must cite all historical rejections again. No old grant is
reactivated; terminal and consumed history stays intact.

Reject a cycle through Decision → typed basis RevisionAction/ApprovalDecision/
Review → their concrete Decision/request/Issue dependencies, including supersession
edges, using a visited-node traversal and a deferred typed-graph constraint.
A RevisionAction must already be committed and cannot cite this reconsideration
or any Decision transitively dependent on it. No depth cutoff may silently accept
a cycle; exceeding the traversal bound fails closed (§11.3).

## 4. Proposed commands, DTOs and historical readback

| Method | Contract |
| --- | --- |
| `record_rejection_reconsideration(command, principal)` | One new immutable Decision and sealed typed basis; no request, grant, review, action or Issue mutation. HUMAN APPROVER and §3 checks required. |
| `get_rejection_reconsideration(project_id, decision_id, principal)` | Exact saved material/basis with current reader entitlement; no write or admission gates. |
| B09 `request_approval` | Add the two optional link UUIDs; enforce §3.2 and ordinary affirmative Decision/review/closure gates together. Return existing request readback plus links and exact reconsideration provenance. |
| B09 `decide_approval` | Recheck successor links, complete rejection coverage and current gates; outcome/grant/event behavior remains B09's. No link editing. |

A completed matching UUID replay is a read: compare normalized caller material,
return the original saved IDs/hashes, require current project read entitlement,
and do not demand current write authority, unchanged validity or a still-complete
current rejection set. Changed material is IDEMPOTENCY_CONFLICT. No second
request may reuse a reconsideration under a different UUID. Reads retain old
material and disclose current usability separately; they never rewrite history.

## 5. Schema and literal hash proposal — no migration

Use existing DecisionRecord, concrete conclusion/review basis and A18's admitted
`decision_basis_approval_decisions` / `decision_basis_revision_actions`. For later
manuscript scope use its separately approved concrete manuscript basis relation;
do not add it in this first slice. Keep the existing request self/Decision FKs.

Hash exactly [R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md):
`DecisionRecordBasisSet` refs contain type, UUID, saved content_hash and ordinal;
sort `(type, canonical UUID, hash)`, deduplicate by `(type, UUID)` and assign global
ordinals 0..N-1 across tables. Include all rejected ApprovalDecisions, one new
target, all selected reviews (old corrected and fresh), and ground (a)'s actions.
Do not put old targets in the single-new-target conclusion relation: reach them
through each rejection request and corrected review/action. Verify those exact
bindings and hashes transitively.

DecisionRecord's question is exactly `Reconsider rejection for {approval_purpose}`,
decision is one §11.3 outcome, rationale is normalized supplied text, actor comes
from verified principal, and supersedes_decision_id is NULL. Thus purpose and
ground are bound by existing R2 fields, without a new hash payload or schema
column. Reject mismatched rejection-purpose sets. Preserve existing hashes and
PROCEED's no-replacement rule; dispatch by decision_type rather than weakening it.
Request links are sealed immutable columns verified against this basis; no new
request hash or generic command receipt is introduced.

## 6. Error contract — existing categories only

Use §11.2. Authenticate and authorize disclosure before returning detailed object
errors. Normalize constraint names/SQLSTATE through the existing UoW path;
never parse raw driver messages or expose SQL. A missing reconsideration on a
fenced request is REJECTION_RECONSIDERATION_REQUIRED, not a successful no-op.

## 7. Transactions, concurrency and failure recovery

One synchronous Application command is one PostgreSQL transaction. §12.2 is the
complete proposed protocol. R2 §2 explicitly requires SERIALIZABLE for rejection
enumeration. The requested READ COMMITTED plus first-statement SHARE/common-scope
protocol is a **proposed architecture refinement requiring owner/architecture
approval**, not an assertion that READ COMMITTED is SERIALIZABLE. Until that
conflict is approved and every writer participates, B10 implementation is blocked.
Do not silently substitute isolation or infer approval from B09's draft.

Use existing bounded whole-UoW retry only for 40001/40P01, at most three fresh
attempts with rereads and reauthorization. A committed new rejection causes a
business fence failure, requiring new evidence/Decision; do not auto-rewrite the
saved basis on retry. Do not retry business errors or timeouts as success.
Uncertain commit uses the same UUID and exact replay. Any failed gate, deferred
check or final authority expiry rolls back all inserts and automatic events.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

§12.4 fixes the files and cases. Evidence must show all-rejection enumeration,
two independent evidence grounds, no bypass through older pending requests,
normal-role SQL enforcement, immutable sealed hashes, cycle rejection and
observable blocking/race outcomes. Favorable-only fixtures cannot prove safety.

## 9. Acceptance criteria and evidence boundary

B10 needs approved B09 purpose/scope behavior, reviewed isolation refinement,
registry/ADR confirmation of A18's exact additions and a separate execution pack.
B08 is an unresolved dependency wherever evidence/material comparison or Issue
resolution needs it: no filename, enum or permission is invented for that item.
Neither this Decision nor a RevisionAction resolves an OPEN/BLOCKING Issue.
If the ordinary approval gate still has a blocker, reconsideration cannot bypass
it; a separately authorized disposition path must resolve it first.

First-slice acceptance needs both conclusion grounds, unique successor, races,
normal SQL parity and exact executed checks. It is not full B10 acceptance while
manuscript tuples, support-only comparison or B08 obligations remain blocked.
Stop at the authorized slice; source presence and tests planned here are not
acceptance evidence.

## 10. Glossary

| Term | Meaning |
| --- | --- |
| Fence / equivalence scope | All targets in one project and approval purpose share rejection protection. |
| Rejection | Immutable ApprovalDecision REJECT; its request remains DECIDED. |
| Reconsideration | New DecisionRecord authorizing evidenced reconsideration of one exact target; no approval grant. |
| Successor | New ApprovalRequest linked to an anchor rejection and one exclusive reconsideration. |
| Ground | Completed relevant revision or reasoned independent review correction. |
| Fresh review | Independent exact-target review committed after every cited rejection. |
| N | Fixed table inventory held SHARE for snapshot-consistent writes (§12.2). |
| Historical replay | Saved result read with current disclosure authority; no new admission or mutation. |

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

First scope is conclusion release, two explicit ground outcomes, all historical
rejections and one successor. Manuscript and support-only change admissions are
blocked, not approximated. No global fence clearing, approver substitution,
ordinary PROCEED reuse, optional owner bypass or automatic Issue disposition.
The first-statement write protocol and lock-free reads are mandatory proposed
choices; §7's architecture conflict must be resolved before implementation.

### 11.2 Pinned error mappings

These pairs match [API errors](../../src/researchbase/api/errors.py) and
[CLI errors](../../src/researchbase/cli/errors.py); no new ErrorCode is proposed.

| Code | HTTP | CLI exit | Use |
| --- | --- | --- | --- |
| VALIDATION_ERROR | 422 | 2 | Closed DTO/type/text/size/enum violation |
| AUTHENTICATION_REQUIRED | 401 | 3 | Missing verified authentication |
| SUBJECT_BINDING_UNPROVEN | 403 | 3 | Trusted actor binding unproven |
| FORBIDDEN | 403 | 3 | Current read/write authority unavailable; HUMAN/APPROVER required |
| CONFLICT_OF_INTEREST | 403 | 3 | Any required actor independence fails |
| NOT_FOUND | 404 | 3 | Entitled exact record absent |
| APPROVAL_PURPOSE_TARGET_COMMAND_INVALID | 409 | 4 | Unsupported purpose/target branch |
| DECISION_BASIS_INVALID | 409 | 4 | Incomplete evidence, bad ground, order or cycle |
| REJECTION_RECONSIDERATION_REQUIRED | 409 | 4 | Missing/stale rejection coverage, invalid successor links |
| APPROVAL_GATE_FAILED | 409 | 4 | Inactive project, lifecycle or blocker gate |
| APPROVAL_TARGET_STALE | 409 | 4 | New target not frozen/currently VALID |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Changed replay or reconsideration already bound |
| CONCURRENT_MODIFICATION | 409 | 4 | Exhausted transaction retries / existing timeout normalization |
| IMMUTABLE_RECORD | 409 | 4 | History mutation or late basis append |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Concrete FK violation |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Corrupt saved hash or typed dependency graph |
| INTERNAL_ERROR (fallback string) | 500 | 1 | Existing sanitized unexpected failure |

GRANT_INVALID/GRANT_STALE remain B09 read diagnostics, not new B10 grant actions.
Semantic missing evidence uses DECISION_BASIS_INVALID; saved corrupt evidence
uses PROVENANCE_CLOSURE_VIOLATION. Current fence coverage failure is separate.

### 11.3 DTO fields, Python types and limits

Separate frozen, slotted dataclasses; wire models forbid extra fields. UUID means
strict `uuid.UUID`; wire form is canonical lowercase hyphenated text. Collections
are strict tuples, no coercion from strings/bools or silent duplicate removal.
The following new bounds are proposed admission limits, not historical facts.

| Field / DTO | Exact type and bound |
| --- | --- |
| Record command: `id`, `project_id`, `scientific_conclusion_version_id` | Required UUID; command id is canonical Decision id |
| `approval_purpose` | `Literal['INTERNAL_SCIENTIFIC_RELEASE']` in first slice; later only B09's three finite purpose literals |
| `decision` | `Literal['REVISED_TARGET','CORRECTED_REVIEW']`; decision_type is server-fixed `RECONSIDER_REJECTION` |
| `rejected_approval_decision_ids` | `tuple[UUID, ...]`, 1..100, distinct, UUID-sorted; must equal service-enumerated full scope set |
| `fresh_review_ids` | `tuple[UUID, ...]`, 1..100, distinct, UUID-sorted; must equal all eligible new-target review IDs and contain a fresh witness |
| `corrected_review_ids` | `tuple[UUID, ...] = ()`, 0..100 distinct; empty for REVISED_TARGET, nonempty for CORRECTED_REVIEW; cover every rejection's saved review basis |
| `revision_action_ids` | `tuple[UUID, ...] = ()`, 0..100 distinct; nonempty for REVISED_TARGET, empty for CORRECTED_REVIEW; exact result/relevance for each rejection |
| `rationale` | strict str, NFC UTF-8, 1..16,384 characters after NFC, nonblank; reject NUL and invalid Unicode; meaningful whitespace preserved in stored/hash material |
| B09 request additions | `prior_rejected_request_id: UUID | None = None`, `reconsideration_decision_id: UUID | None = None`; both-or-neither |
| Exact read inputs | `project_id: UUID`, `decision_id: UUID`; trusted principal passed separately |
| Readback | Existing Decision scalar fields: UUID ids, str type/question/decision/rationale/hashes, UTC-aware datetime decided_at, `supersedes_decision_id: UUID | None` (always NULL here); `basis: tuple[DecisionBasisReference, ...]` |
| Readback additions | `approval_purpose: str`, `successor_request_id: UUID | None`, `cited_rejected_request_ids: tuple[UUID, ...]`, `current_coverage_complete: bool`; derive with plain queries, never persist a second truth |
| Readback audit detail | `rejections: tuple[RejectedApprovalReference, ...]`; each closed reference has `request_id: UUID`, `approval_decision_id: UUID`, `content_hash: str`, `decided_by: UUID`, `decided_at: datetime`, `scientific_conclusion_version_id: UUID | None`, `manuscript_version_id: UUID | None` (exactly one), `target_content_hash: str`; no soft target pair |

Readback basis refs have `type: str` from the finite R2 set, `id: UUID`,
`content_hash: str` matching `[0-9a-f]{64}`, `ordinal: int` (not bool, ≥0).
Hash scheme is exactly `sha256-cjson-v1`. At most 401 distinct basis refs and
10,000 visited typed graph nodes per new admission; excess raises
DECISION_BASIS_INVALID without truncation. More than 100 rejections denies new
admission until separately reviewed bounds expand; never keep only the newest.
Old accepted longer history stays readable. Caller actor, times, hashes, status,
role, ground evidence JSON, question and supersession fields are forbidden.
Audit detail also exposes the new target's concrete FK/hash through the saved
Decision basis, exact old/fresh review and action refs, rationale and outcome.
No copied audit target becomes another scientific source of truth.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

Future additive migration under `migrations/versions/`; select number from actual
head at authorization. No historical rewrite/backfill of rejection evidence.

```sql
CREATE TABLE decision_basis_approval_decisions (
 decision_id UUID NOT NULL,
 approval_decision_id UUID NOT NULL,
 ordinal INTEGER NOT NULL,
 CONSTRAINT pk_b10_rejection_basis PRIMARY KEY(decision_id,approval_decision_id),
 CONSTRAINT fk_b10_rejection_decision FOREIGN KEY(decision_id)
  REFERENCES decision_records(id) ON DELETE RESTRICT,
 CONSTRAINT fk_b10_rejection_approval FOREIGN KEY(approval_decision_id)
  REFERENCES approval_decisions(id) ON DELETE RESTRICT,
 CONSTRAINT ck_b10_rejection_ordinal CHECK(ordinal>=0),
 CONSTRAINT uq_b10_rejection_ordinal UNIQUE(decision_id,ordinal)
);
CREATE TABLE decision_basis_revision_actions (
 decision_id UUID NOT NULL,
 revision_action_id UUID NOT NULL,
 ordinal INTEGER NOT NULL,
 CONSTRAINT pk_b10_revision_basis PRIMARY KEY(decision_id,revision_action_id),
 CONSTRAINT fk_b10_revision_decision FOREIGN KEY(decision_id)
  REFERENCES decision_records(id) ON DELETE RESTRICT,
 CONSTRAINT fk_b10_revision_action FOREIGN KEY(revision_action_id)
  REFERENCES revision_actions(id) ON DELETE RESTRICT,
 CONSTRAINT ck_b10_revision_ordinal CHECK(ordinal>=0),
 CONSTRAINT uq_b10_revision_ordinal UNIQUE(decision_id,ordinal)
);
CREATE INDEX ix_b10_rejection_reverse
 ON decision_basis_approval_decisions(approval_decision_id);
CREATE INDEX ix_b10_revision_reverse
 ON decision_basis_revision_actions(revision_action_id);
ALTER TABLE approval_requests ADD CONSTRAINT ck_b10_request_links CHECK
 ((prior_rejected_request_id IS NULL)=(reconsideration_decision_id IS NULL));
CREATE UNIQUE INDEX uq_b10_successor_reconsideration
 ON approval_requests(reconsideration_decision_id)
 WHERE reconsideration_decision_id IS NOT NULL;
ALTER TABLE decision_records ADD CONSTRAINT ck_b10_decision_pair CHECK (
 (decision_type='INTERNAL_SCIENTIFIC_RELEASE' AND decision='PROCEED') OR
 (decision_type='RECONSIDER_REJECTION'
  AND decision IN ('REVISED_TARGET','CORRECTED_REVIEW')));
```

Before the replacement CHECKs, drop only 0042's release-only type/outcome CHECKs
and 0045's two NULL-only link CHECKs using their inspected catalog names. Retain
all concrete FKs, target XOR, hash syntax, NULL supersession, immutable rows and
B09's finite tuples. `decision_type VARCHAR(40)`, `decision VARCHAR(16)`, question/
rationale TEXT, actor/project UUID FKs, decided_at TIMESTAMPTZ, hashes CHAR(64),
hash_scheme VARCHAR(32) remain unchanged. Add `ck_b10_text_bounds` for new
reconsideration question/rationale NFC/nonblank and rationale length, and
`ck_b10_finite_time` for finite decided_at; do not invalidate older PROCEED rows.
B09 supplies scope index `ix_b09_rejection_scope`; no second rejection index.

| Named guard | Required behavior |
| --- | --- |
| `b10_decision_guard`, `b10_basis_guard` | Insert-only, current preheld N/scope protocol, same-transaction unsealed parent, same project/purpose, exact immutable already committed evidence; forbid late child append. Preserve PROCEED dispatch. |
| `b10_basis_immutable` on both new relation tables | Deny UPDATE/DELETE through existing immutable-history convention. |
| `b10_complete_decision`, `b10_complete_rejections`, `b10_complete_revisions`, existing `pr215_complete_decision` / `pr215_complete_conclusion` / `pr215_complete_review` | DEFERRABLE INITIALLY DEFERRED AFTER INSERT constraint triggers on parent and each child; shared type-dispatched final-graph verifier checks full rejection/review coverage, ground, global ordinals, literal hashes, bounds and current authority. Replace the existing function with explicit dispatch; old 0042 checks remain exact for PROCEED only. |
| `b10_no_basis_cycle` | DEFERRABLE INITIALLY DEFERRED constraint trigger on Decision and every participating basis INSERT, plus RevisionAction/approval-request link INSERT; typed transitive graph cycle and prior-commit check, including future Decision-bearing RevisionAction edges. |
| Extend `pr216_request_guard`, `pr216_decision_guard`, `pr216_complete_request` | Verify links and unique successor; request and first decision recompute all-rejection coverage under same scope; historical DECIDED rows remain readable. Reject incomplete new links and legacy-PENDING bypass. |

Constraints use `SET search_path = pg_catalog, public, pg_temp`. Bind exact
normalization to named constraints/SQLSTATE in UoW, not exception text. Deferred
guards inspect the final sealed graph, following 0042, not an incomplete parent
before children are inserted. Application and normal-role SQL must both enforce
evidence, hashes, authority, lock preconditions and all-rejection scope. An SQL
trigger cannot retrospectively make its INSERT the first statement: require and
test preheld N and reject a direct writer without it. Populated downgrade refuses
to discard reconsideration history or its enforcement; empty downgrade restores
the prior guards/CHECKs. No CASCADE or generic reference table.

### 12.2 Exact lock order and transactions

Freeze N as the lexically sorted union of the **literal** B04_SNAPSHOT_TABLES
inventory in `src/researchbase/persistence/manuscript_freeze_repository.py` and
`internal_review_records`, `review_issues`, `review_issue_events`,
`manuscript_versions`, `publications`. Copy that fixed inventory into the future
adapter/migration and test equality; no catalog-generated inventory or silent
inheritance of later additions. B10/B09 write none of N. N protects authority,
scientific/placement/validity inputs and review/Issue INSERT phantoms. Approval
and Decision basis inputs are sealed; scope coordination protects rejection
INSERT phantoms. Do not SHARE-lock approval_requests or decision_records and then
upgrade those tables during inserts.

Configure READ COMMITTED and disable autoflush without SQL. **FIRST SQL statement**
is one `LOCK TABLE <N, sorted> IN SHARE MODE`, before navigation SELECT, advisory,
row lock or SET LOCAL. Then `SET LOCAL lock_timeout='10s'` and
`SET LOCAL statement_timeout='30s'`. Bound the initial SHARE wait through existing
connection/server configuration before UoW entry; later SET LOCAL cannot bound
an earlier wait. This is conditional on §7's architecture approval.

| Command | Exact sequence after N SHARE and timeouts |
| --- | --- |
| record_rejection_reconsideration | Advisory `pr215:decision:{id}` (existing global Decision UUID namespace); advisory `pr216:scope:{project_id}:{approval_purpose}`; new exact conclusion FOR UPDATE; owning scientific_conclusions row FOR SHARE; authorize current reader then HUMAN APPROVER; enumerate all rejected requests/decisions UUID-sorted with plain reads; read committed reviews/actions/basis and exact old targets without row locks; validate evidence, hashes, bounds, independence and gates; final fresh authority; insert Decision then typed children in global ordinal order; force deferred checks, final authority, commit. |
| request_approval | Advisory `pr216:uuid:{id}`; same project/purpose scope advisory; new target FOR UPDATE; owning Publication FOR SHARE only for later manuscript branch; fresh reader then writer authorization; re-enumerate all rejections and verify saved reconsideration/anchor/unused successor, ordinary affirmative Decision/reviews and current gates; prelock B09's affected ACTIVE grants UUID-sorted; final authority; insert request/relations and automatic events/staleness; deferred/final checks, commit. |
| decide_approval | Advisory `pr216:uuid:{id}`; plain request routing lookup; same project/purpose scope advisory; exact target FOR UPDATE; Publication FOR SHARE if applicable; request FOR UPDATE and reread; fresh reader then independent HUMAN APPROVER authorization; re-enumerate rejection set and recheck saved links/evidence/current gates; for REJECT prelock all affected ACTIVE grants UUID-sorted; final authority; B09 decision/grant/events/staleness; deferred/final checks, commit. |
| get_rejection_reconsideration, B09 exact reads, completed matching replay | One REPEATABLE READ, READ ONLY UoW; reader authorization; plain exact parent/children/successor queries, saved-hash verification, derived coverage diagnostics; final reader check at fresh DB time; return. No explicit table, advisory or row locks, FOR SHARE/FOR UPDATE, writes or status maintenance. |

Keys use parameter-bound canonical UUID/purpose text and existing advisory hash
convention. B09 must use the **same** `pr216` scope namespace, including ordinary
REJECT on another target; normal SQL follows it too. The old project-only approval
scope and target-before-snapshot protocol must be replaced through B09 before
B10 admission. Do not reuse locking repository helpers in any read/replay path.

The record write rechecks for an existing UUID after exclusion to handle races;
a committed matching result is returned through a fresh read-only replay UoW,
without mutation. A cheap preflight uses the same lock-free read protocol. All
commands reread after waits and evaluate credentials, binding, actor, membership,
role and finite conditions with fresh `clock_timestamp()`, never `now()`.
`SET CONSTRAINTS ALL IMMEDIATE` precedes the last authority/time check; any later
required wait forces another reread/time check. No external effect occurs.

Writer participation is part of acceptance: approval/rejection/new-target writers
share purpose scope; review/Issue/scientific/authority writers conflict with N via
ordinary ROW EXCLUSIVE locks, including INSERTs; existing exact-target review
coordination remains. Immutable Decision/RevisionAction inserts cannot append to
committed parents. Authority-loss writers retain atomic grant-staleness/events
and must not acquire B10 scope after grant locks. Existing target-first writers
can deadlock with N-first writers; prove bounded whole-transaction recovery and
migrate incompatible participating guards before acceptance. N alone is not proof
of rejection-scope exclusion or a solution to lock-order inversion.

### 12.3 Ordered build steps and module paths

1. Resolve §§7, 9, 13 and obtain separate authorization; inspect actual Alembic
   head, B09 and B08 status. Add §12.1 as one forward migration under
   `migrations/versions/`, preserving old source/hashes.
2. Extend `src/researchbase/domain/decision.py` with finite reconsideration
   validation and evidence comparison using existing R2 builders. Keep policy
   pure; no SQLAlchemy/FastAPI/Typer imports or ORM DTOs.
3. Extend `src/researchbase/application/decision.py` with the two methods/closed
   DTOs in §4; extend `src/researchbase/application/approval.py` with successor
   inputs and fence checks. Add typed operations to
   `src/researchbase/application/ports.py`. Verify saved review/action/closure in
   the same UoW, not by calling services that open separate transactions.
4. Extend `src/researchbase/persistence/decision_repository.py` for typed basis
   reads/inserts, plain historical reads and §12.2; extend
   `src/researchbase/persistence/approval_repository.py` for all-rejection queries
   and successor validation. Wire read/write modes and named error normalization
   in `src/researchbase/persistence/uow.py`. Preserve existing release behavior.
5. If separately authorized for transport exposure, extend
   `src/researchbase/api/routes.py`, `src/researchbase/api/app.py`,
   `src/researchbase/cli/commands/governance.py` and
   `src/researchbase/cli/composition.py`. Proposed POST collection and GET exact
   route: `/projects/{project_id}/rejection-reconsiderations[/{decision_id}]`;
   CLI `record-rejection-reconsideration`, `read-rejection-reconsideration`.
   Return 200 for first/replay/GET; inject trusted principal. Extend B09 request
   models only with the two links; keep existing transport error maps unchanged.
6. Add/run §12.4 tests, record exact results and remaining blockers, then stop.

### 12.4 Test artifacts and required cases

Planned new tests below do not exist yet. Reuse disposable PostgreSQL 18.x approval,
Decision, B05 and B06 fixture patterns; no SQLite or fabricated acceptance rows.

| File | Required cases |
| --- | --- |
| New `tests/unit/phase2/test_b10_reconsideration.py` | Closed DTOs/types/enums, duplicate/empty/100 versus 101 collections, NFC/NUL/Unicode and 16,384/16,385 text, 401 refs / 10,000-node limits; both grounds; UUID/whitespace-only changes denied; correction without material change allowed; fixed question/outcome/hash literals and unchanged PROCEED golden vectors. |
| New `tests/integration/phase2/test_b10_reconsideration.py` | Every same-project/purpose rejection, unrelated lineages, anchor ordering, wrong scope/target/hash/review/result, missing ordinary affirmative Decision; fresh-after-all timestamp and actor rules; each independence pair, Agent/OWNER-only deny; blocker not closed; both grounds; support-only/manuscript unavailable; successor once only; old pending request bypass denied; new rejection invalidates unused saved coverage; no old grant reactivation; historical read/replay after rejection/write-role loss and current read denial. |
| New `tests/integration/phase2/test_b10_reconsideration_schema.py` | Clean install/populated upgrade and empty downgrade/populated refusal; exact types/names/FKs and global cross-table ordinals; normal-role SQL forged hash/actor/partial basis/late append/update/delete/NULL links deny; final completeness and direct/transitive cycles at commit and SET CONSTRAINTS; rollback after each staged insert, unchanged old hashes. |
| New `tests/integration/phase2/test_b10_reconsideration_concurrency.py` | FIRST-SQL/isolation/N evidence; lock-free RR reads/replay; same Decision UUID race/changed replay; two successors competing for one reconsideration; REJECT on unrelated target versus record/request/old pending decision in both commit orders; role/credential expiry across N/scope/target/grant/deferred waits; review/Issue insertion and source invalidation; normal SQL parity; 40001/40P01 fresh attempts ≤3 and no business/timeout retry; uncertain commit same UUID. Use independent backend PIDs, barriers and pg_blocking_pids(), not sleeps as proof. |
| New `tests/architecture/test_b10_reconsideration.py` | Common Application boundary, pure domain/closed DTOs, admitted typed relations only, exact two new methods, no effects/disposition/new entity/JSON core; narrowly update existing single-revision assertions only after authorization. |
| New `tests/unit/phase2/test_b10_reconsideration_transports.py` | If adapters authorized: exact §11.2 HTTP/CLI codes and 200 first/replay, closed fields, authenticated principal, sanitized fallback; existing approval adapters unchanged. |

Run static checks, `uv run pytest tests/unit tests/architecture`, new authorized
B10 files and dependent PostgreSQL suites: `tests/integration/phase2/test_approval.py`,
`test_pr2_15_decision.py`, `test_pr2_15_decision_schema.py`,
`test_b06_revision_action.py`, `test_b06_revision_concurrency.py`,
`test_b04_manuscript_freeze.py`, `test_b05_manuscript_review.py`,
`test_b05_review_basis.py`, `test_b05_review_races.py`, plus B09 tests when shipped.
Record PostgreSQL server version and constraint/lock evidence. Missing contracts
and blocked database setup cannot count as passing cases. The owner's loop owns
the full suite; do not run it as part of this documentation task.

### 12.5 Not in this slice

| Deferred behavior | Boundary |
| --- | --- |
| B09 tuple implementation, B08 missing contract | Separate owner-approved work; no inferred acceptance |
| Manuscript reconsideration and affirmative Decision extensions | Need all exact target/review/material/action dependencies |
| Support-only or arbitrary artifact semantic-change inference | Need approved material comparison; hash inequality is insufficient |
| Mixed grounds per rejection, general appeals/policy/COI engine | Later contract; no new evidence-map JSON or canonical schema |
| Issue ADDRESSED/DISMISSED, NO_CHANGE or Decision-bearing revisions | Separate disposition/revision contracts; no circular self-justification |
| Grant consumption/revoke/expiry commands, READY/package/consent/send | Owning contracts; reconsideration has no effect or grant authority |

## 13. Open questions for the owner — override register

| Owner/architecture disposition required | Proposed decision |
| --- | --- |
| R2 §2 SERIALIZABLE versus requested protocol | Approve an explicit architecture refinement to §12.2 READ COMMITTED + first N SHARE + common purpose scope, with SQL writer parity/race evidence; until then implementation blocked. |
| What does B08 actually authorize? | Supply/review its contract before depending on it; no guessed mechanism, enum or implementation. |
| Scope/bounds/evidence choices | First conclusion branch, two finite outcomes, all rejections, conservative material-change rule and bounded fail-closed admission; broader completion remains open. |
| Can existing Decision serve as ordinary basis and reconsideration? | No. Preserve distinct purposes, immutable R2 hashes and independent actors. |

These are approval questions, not implicit permission to implement missing work.

## 14. Documentation verification note

Only this proposal is authored. Tests named in §12.4 are future work. Executed
checks and exact counts for this documentation task are recorded below; no
implementation, gate or Phase-exit success follows from them.

Observed on 2026-10-15 using the installed shared environment. Every `uv` command
below had these exact inline environment assignments prepended:

```sh
UV_CACHE_DIR=/tmp/researchbase-b10-uv-cache UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv PYTHONPATH=src
```

| Exact command after that prefix | Observed result |
| --- | --- |
| `uv run --no-sync ruff check .` | PASS: All checks passed! |
| `uv run --no-sync ruff format --check .` | PASS: 570 files already formatted |
| `uv run --no-sync pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject` | PASS: 0 errors, 0 warnings, 0 informations |
| `uv run --no-sync pytest tests/unit tests/architecture` | 2,343 passed, 4 failed, 12 errors, 7 warnings in 41.64s; NOT PASS |
| `DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run --no-sync pytest tests/integration/phase2/test_approval.py tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_b06_revision_action.py tests/integration/phase2/test_b05_manuscript_review.py -x` | 1 setup error in 0.53s, stopped before test execution; NOT PASS |

The four unit failures are `tests/unit/test_hg1_runner.py` socket-bind
PermissionErrors (“Operation not permitted”). The twelve architecture setup errors
in `tests/architecture/test_pr2_19_boundaries.py` require explicit
RB_TEST_ADMIN_URL. The separately configured PostgreSQL attempt then failed
because sandbox policy denies localhost connections, on IPv4 and IPv6; remaining
selected cases were not run. No PostgreSQL server version, constraint assertion
or race was verified. These are execution limits, not passing tests.

`git diff --check` passed with no output. A local `python3 -` standard-library
AST/link check resolved all 30 relative links, matched all 17 HTTP/CLI pairs
(including the existing fallback), and verified sections 1–14 and the required
status. Only the requested proposal is changed; the full suite is left to the
owner's loop as instructed.
`git diff --no-index --check /dev/null docs/proposals/B10_Rejection_Reconsideration_Contract_DRAFT.md`
emitted no whitespace diagnostics (exit 1 for the new-file difference). A separate
`python3 -` whitespace check passed: no trailing spaces and final newline present.
