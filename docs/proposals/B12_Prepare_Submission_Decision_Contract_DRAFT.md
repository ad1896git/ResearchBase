# B12 PREPARE_SUBMISSION Decision and Approval Tuple Contract — DRAFT

**Status: APPROVED by owner 2026-10-17 — first slice authorized for implementation**

## Start here (for the implementer)

B12 records a distinct affirmative judgment to prepare one exact frozen manuscript
and connects it to B09's separate command authorization. A readiness Decision or
grant cannot substitute for it. Review evaluates; Decision chooses; Approval
authorizes; a later command consumes permission and freezes a prepared package.
Nothing here sends a manuscript or makes a scientific fact valid by authority.

Build only after this contract is approved and implementation separately authorized:

1. Reconcile the actual migration head and accepted B09/B11 implementations (§1).
2. Freeze the finite purpose/value, DTOs, errors and dependency boundaries (§11).
3. Extend B11's existing typed manuscript basis and deferred guards (§12.1).
4. Extend Decision and Approval through the real paths in §12.3, using exactly
   §12.2's SHARE-first writes and lock-free snapshot reads, including helpers.
5. Add §12.4's tests, execute focused checks, retain evidence and stop at §12.5.

Read §§1–4 first; use §10 as a glossary, §11 for pinned decisions and §12 for
construction. §13 records owner overrides. Proposed B12 policies below are for
approval; they are not descriptions of behavior already shipped.

Five rules whose violation fails review:

1. Use PREPARE_SUBMISSION/PROCEED about the exact FROZEN manuscript ID/hash;
   READY_FOR_SUBMISSION, release and reconsideration Decisions are different facts.
2. Bind all exact-manuscript reviews, including adverse reviews; independently
   verify frozen closure, attribution, validity and applicable OPEN blockers.
3. Require a distinct independent HUMAN approval for the exact finite tuple;
   no Decision creates a grant, changes Publication state or freezes a package.
4. Preserve immutable history and historical replay; no replacement, late basis,
   review truncation, rejection bypass or terminal-grant reactivation.
5. Writes start with SHARE locks in READ COMMITTED; reads and completed replay
   take one REPEATABLE READ, READ ONLY snapshot with no explicit exclusion locks.

## 1. Purpose, authority and inspected baseline

| Source | Constraint carried forward |
| --- | --- |
| [System 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 6, 12; [Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A17–A23 | Deterministic facts precede authority; immutable frozen provenance; separate Review, Decision, Approval, Command and ExternalEffect; bounded schema admission. |
| [Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md); [Cross-Phase 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§9–18, 24 | Existing DecisionRecord, ApprovalRequest/Decision/Grant and concrete relations; Application boundary, RESTRICT FKs and additive compatibility. |
| [Phase 2 specification 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §§19–24, PR2-15/16/17; [Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), §§4–7 | Review, explicit Decision and distinct preparation authorization; prepared is not sent; no authority override of invalid facts or unresolved blockers. |
| [Field contract 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md), governance/publication rows; [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md), governance payloads; [R3 18](../architecture/18_Phase2_Design_R3_Targeted_Remediation_v1.0.md), §§1, 5 | Exact typed basis, unchanged literal material_version=1 hashes, derived canonical basis order; later consumption has its own exact receipt. |
| [Governance R2 17](../architecture/17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md), §§1–3; [Temporal R4 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md), TEMP-AUTH-01 | PREPARE target is manuscript in READY Publication; distinct affirmative Decision, independent HUMAN approval, finite one-use command scope, mandatory consent at consumption and fresh post-wait DB authorization. |
| [Minimal Decision 20](../architecture/20_PR2_15_Minimal_Decision_Command_Contract_v1.0.md); [Harness 09](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 18–21 | Preserve initial release command, complete basis, nonreplacement and entitled replay; documentation and approval are not execution evidence. |
| [B09 approval tuples](B09_Approval_Tuples_Contract_DRAFT.md), §§3, 7, 11–12; [B11 readiness Decision](B11_Ready_For_Submission_Decision_Contract_DRAFT.md), §§3–5, 11–12 | Reuse manuscript basis, complete review/author/blocker policy, purpose-specific approval fence and exact transaction protocols. |
| [B07](B07_Revision_Decisions_Contract_DRAFT.md), [B08](B08_Issue_Disposition_Contract_DRAFT.md), [B10](B10_Rejection_Reconsideration_Contract_DRAFT.md) | Preserve separate revision, disposition and reconsideration purposes; no implied manuscript disposition or reconsideration extension. |

The owner reports Batch C (B07–B11) contracts approved and their code in parallel
implementation. This report governs dependency planning despite their retained
DRAFT status lines and historical inventories. It does not establish implementation
acceptance. Build on those contracts; do not rewrite them or fill missing code here.

Inspected branch, 2026-10-16:

- [DecisionService](../../src/researchbase/application/decision.py) and
  [0042](../../migrations/versions/0042_pr2_15_minimal_decision.py) admit only
  INTERNAL_SCIENTIFIC_RELEASE/PROCEED and conclusion/review basis. The
  [domain builders](../../src/researchbase/domain/decision.py) already recognize
  ManuscriptVersion references. B11's manuscript basis is a contracted dependency,
  not an existing table on this branch.
- [B04/0048](../../migrations/versions/0048_b04_manuscript_freeze.py) and
  [B05/0049](../../migrations/versions/0049_b05_manuscript_review.py) implement
  manuscript seals, exact review and complete-basis collection. Use
  [freeze verification](../../src/researchbase/application/manuscript_freeze.py)
  and [review verification](../../src/researchbase/application/internal_review.py)
  in the same UoW. Current Publication guards do not enable READY.
- [ApprovalService](../../src/researchbase/application/approval.py),
  [approval repository](../../src/researchbase/persistence/approval_repository.py)
  and [0045](../../migrations/versions/0045_pr2_16_basic_approval.py) implement
  release-only requests/decisions/grants, no consumption. Manuscript columns
  exist but are excluded by policy CHECKs. B09 contracts their extension.
- [Decision repository](../../src/researchbase/persistence/decision_repository.py)
  uses SHARE protection after request/target locks; B04 and the coverage path in
  [novelty repository](../../src/researchbase/persistence/novelty_repository.py)
  demonstrate SHARE as FIRST SQL. Copy the mechanism, using the latter order.
  Existing locking authorization/read helpers need plain-SELECT variants.
- The migration inventory reaches 0051/B06. No B12 execution pack exists in
  `execution/phase2/`. Reconcile the actual accepted head before implementation;
  this document reserves no revision number and authorizes no migration.

## 2. Scope, dependency boundaries and non-goals

Add `record_prepare_submission_decision` and `get_prepare_submission_decision`
to DecisionService, specialized closed DTOs, and purpose dispatch through B11's
manuscript relation. Connect B09's existing five approval methods to this exact
Decision; do not create a second request, grant, receipt or policy subsystem.

B04/B05 are implemented prerequisites; accepted B09/B11 implementations are build
prerequisites. Publication READY is a separate effect/lifecycle dependency.
**Proposed B12 stage policy:** require READY even at first Decision creation,
matching the later preparation approval gate. Until that lifecycle is authorized
and implemented, this branch denies new creation; do not force READY, relax its
guards, or build the transition inside B12. Test builders must use its accepted
Application path once available, not disable guards to claim end-to-end success.

B08 permits only its contracted concern targets; it does not close manuscript
Issues. B10's initial reconsideration branch is conclusion release, not permission
to reconsider preparation rejection. Missing manuscript extensions remain denied.
B12 can record a judgment after a rejection, but it neither clears that fence nor
qualifies as RECONSIDER_REJECTION. Approval remains unavailable in that scope.

No top-level entity, semantic JSON, dependency, queue, scheduler or new persistence
mechanism. Package preparation, consent, freeze, consumption and external send are
outside this slice (§12.5). Existing PR2-17 attribution foundation is not consent.

## 3. Invariants and conservative judgments

### 3.1 Exact manuscript and attributable judgment

A new Decision requires ACTIVE Project; live VerifiedPrincipal, binding,
membership and effective OWNER or APPROVER authority; exact same-project FROZEN
ManuscriptVersion with frozen_at, placement_set_hash, content_hash and
sha256-cjson-v1 seal; owning Publication READY. Derive actor and advancing DB time.
A HUMAN or AGENT may decide under the accepted Decision policy; approval is HUMAN-only.

Use B04 full verification, including document CAS bytes/hash, exact placement and
transitive scientific/literature/input closure, deterministic current VALID status
and existing seal/pointer consistency. No latest/current lookup chooses a target.
Use B11's existing `material_authors(target, manuscript=True)` traversal through
manuscript, Publication, document, placement creators and transitive inputs. The
decider must differ from all those authors. Membership or accumulated roles do
not establish independence. No new authorship owner or attribution copy is added.

### 3.2 Complete reviews and applicable blockers

Apply B11 §§3.1–3.2 without a favorable-review filter: require all committed
reviews of `(project_id, manuscript_version_id)`, nonempty, each with matching
exact target/hash, valid saved review hash/scheme, historical HUMAN REVIEWER/OWNER
attribution, material-author independence and valid Issue/event history. Corrupt
or nonindependent matching review fails; never omit it. ACCEPT, MINOR_REVISION,
MAJOR_REVISION, REJECT and UNCERTAIN all remain basis. The decider may be a reviewer
as in B11; the later approver cannot be either actor.

Reject any applicable OPEN BLOCKING Issue on the manuscript or B11's exact
reachable ClaimVersion, ScientificConclusionVersion and ArtifactVersion review
targets (including document). Traverse the same finite concrete dependency edges;
no identity-wide, related-text, related_source_version_id or other-version scope.
Upstream reviews are blocker inputs, not extra manuscript-review basis rows.
Nonblocking OPEN Issues remain visible. A terminal status excludes a blocker only
when its full B08-authorized disposition history/basis verifies. No implicit
manuscript disposition; no revision/re-review/NO_CHANGE alone closes a concern.

### 3.3 Distinct authorization tuple

| Purpose | Target/state | Required Decision | Allowed command / later result |
| --- | --- | --- | --- |
| PREPARE_SUBMISSION | Exact FROZEN, VALID ManuscriptVersion; same-project Publication READY | PREPARE_SUBMISSION/PROCEED with that manuscript/hash and complete saved manuscript reviews | `freeze_prepared_submission`; later consumption result is a same-Publication PreparedSubmissionVersion |

B09 request `basis_decision_id` must resolve to this prior committed Decision;
required `review_ids` equal its entire saved review set. Never substitute B11's
READY_FOR_SUBMISSION Decision/grant, INTERNAL_SCIENTIFIC_RELEASE/PROCEED,
REVISION_RESPONSE, RECONSIDER_REJECTION or an approval for another manuscript/hash.
Readiness history is verified by its owning lifecycle path; B12 adds no readiness
Decision basis member, grant FK or alternate READY flag.

At request and approval decision, independently recheck exact hashes/full closure,
VALID status, READY stage, all current applicable blockers, later reviews and
saved review/Decision integrity. Later reviews do not mutate saved membership.
Requester is current RESEARCHER/OWNER and differs from every required reviewer.
Approver is a current independent HUMAN APPROVER, distinct from requester,
basis decider, every required reviewer and every traversed material contributor.
OWNER-only, Agent APPROVER and acting_on_behalf_of cannot substitute.

APPROVE or APPROVE_WITH_CONDITIONS creates exactly one ACTIVE grant; REJECT none.
Grant scope is B09's typed projection of project, purpose, exact request manuscript
FK/hash, sole allowed command, finite valid_until and max_uses=1. No package is
selected or frozen by this authorization. Both approving outcomes remain allowed:
PREPARE's mandatory current-author-consent gate applies at consumption even when
APPROVE stores requires_current_author_consent=false. A true typed condition only
strengthens it. A grant alone cannot attest package closure or author consent.
The persisted allowed_command is lowercase `freeze_prepared_submission` as in
B09/0045; R3's uppercase FREEZE_PREPARED_SUBMISSION belongs to the deferred
consumption receipt enum, not an additional grant command.

Preserve B09's project/purpose rejection fence (including older PENDING requests),
new-target and authority-loss staleness/events. Another purpose/project is outside
that fence. B12 does not reactivate terminal grants or implement reconsideration.

## 4. Proposed commands, DTOs and historical readback

Trusted principal is separate from each closed immutable DTO (§11.3). Creation
returns PrepareSubmissionDecisionReadback; exact read takes project and Decision
ID. No list, preview, caller-selected basis, batch or target search.

Reads require current verified OWNER/RESEARCHER/REVIEWER/VIEWER/APPROVER project
entitlement, with separate access checks before disclosing nested source details.
Authorize before protected existence/conflict disclosure. Same UUID replay also
requires the original actor. Verify saved immutable target, basis, attribution and
hashes; do not demand today's READY stage, write role, complete current review
set, VALID status or absence of blockers to read historical material. Return
current validity and blocker IDs separately with evaluated_at. Historical reading
is not gate success. Reuse B09 request/decision/grant readback and current-usability
semantics without claiming that an unimplemented package effect is executable.

## 5. Schema and literal hash proposal — no migration

Reuse B11 `decision_basis_manuscripts`, existing `decision_records` and
`decision_basis_reviews`; **no new table or column**. Extend purpose-specific
CHECK/guard dispatch. One Decision per `(project, purpose, exact manuscript)`;
READY and PREPARE may coexist for the same target. No supersession or replacement.

Reuse unchanged `DecisionRecordBasisSet` and `DecisionRecord` literal builders,
material_version=1, sha256-cjson-v1, supersedes_decision_id=null. Basis is exactly
one ManuscriptVersion ref plus all exact manuscript InternalReviewRecord refs.
Independently verify each frozen digest, reject duplicate `(type,id)`, sort by
`(type, canonical UUID text, content_hash)`, derive 0..N canonical positions, then
hash. Persisted ordinals are storage coordinates, never authority for hash order
(R3 §1); new writes store the derived order. Review refs sort before manuscript.
Reconstruct and derive again on reads. Include literal PREPARE_SUBMISSION/PROCEED
in Decision content, with existing project/question/rationale/decided_by/basis hash.
Request ID, DB time, stage and diagnostics are not new hash fields.

ApprovalDecision retains B09's literal R2 payload and exact manuscript reference,
including valid_until, consent bool and approver. Purpose/command remain enforced
through immutable typed scope, not extra hash keys. Issue descriptions/status/
events are outside Review content hashes; no claim of a cryptographic Issue-state
snapshot, new digest or signed historical gate certificate is made here.

## 6. Error contract — proposed use of existing categories

§11.2 pins mappings to the actual source tables. No new ErrorCode. Distinguish
malformed inputs, unavailable new-write gates and corrupt saved provenance;
normalize named constraints/SQLSTATE through existing UoW patterns. Never turn
unique-constraint loss or partial history into a successful replay, or expose raw
SQL, credential exceptions or artifact paths. Transport exposure is deferred.

## 7. Transactions, concurrency and failure recovery

One new command is one synchronous READ COMMITTED write UoW with §12.2 protection;
no external call or artifact mutation. Decision parent and basis commit together.
Approval uses B09's separate transaction for each request or decision, with its
existing atomic events and optional grant. Decision creation does not call an
approval command or open a nested transaction.

Completed replay is a lock-free REPEATABLE READ, READ ONLY path: same UUID,
original actor/project and normalized caller material returns verified history
under current read entitlement, despite write-role loss or later blockers/staleness.
Changed material conflicts. Different UUID for the same decided purpose/target
also conflicts; a new manuscript can receive a new Decision. Different actor/
project gets nondisclosing FORBIDDEN. An advisory read preflight grants no write
authority; if absent, start the fully protected write path. If a racing write
finds a committed duplicate under locks, close that UoW and reopen the lock-free
snapshot replay path. Never return replay from a locking write verifier.

Retry SQLSTATE 40001/40P01 only, exactly three total fresh-UoW attempts, no delay;
redo all locks/reads/hash/clock checks. Do not retry business conflicts, uniqueness
loss, timeout or uncertain commit blindly. Recover uncertain commit with the same
UUID. Force deferred constraints before final fresh-clock authorization; recheck
after any later wait. Any denial rolls back every new row/event. No consumption
transaction or receipt is added; R3/R4 SERIALIZABLE effect semantics stay deferred.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

§12.4 fixes files and cases. Test pure DTO/hash boundaries, current versus saved
gates, all tuple substitutions and actor independence, deferred final graphs and
normal-role SQL bypass, real two-backend races, rollback and read lock inspection.
Planned tests and this documentation review are not implementation evidence.

## 9. Acceptance criteria and evidence boundary

Require owner approval of §11, conformance review of the bounded forward guard
amendment, and separate execution authorization. Verify accepted B09/B11 and
READY lifecycle dependencies before declaring this tuple usable. An unavailable
dependency must be reported, not simulated as end-to-end acceptance.

Run static/unit/architecture and affected PostgreSQL 18.x suites, retaining exact
commands, counts, server version and no open P0/P1. The owner's loop runs the whole
suite; this author does not. B12 acceptance does not imply consent, package freeze,
PR2-17 full acceptance, G6, Phase 2 exit or external submission acceptance.

## 10. Glossary

| Term | Meaning here |
| --- | --- |
| Preparation Decision | Immutable PREPARE_SUBMISSION/PROCEED choice about an exact manuscript. |
| Readiness Decision | B11 judgment for the distinct READY_FOR_SUBMISSION purpose. |
| Approval tuple | B09's finite purpose/target/hash/command/expiry/single-use scope. |
| Required review basis | Complete saved exact-manuscript review set, including adverse reviews. |
| Applicable blocker | B11's OPEN BLOCKING concern on exact manuscript/reachable review targets. |
| READY | Publication lifecycle state; neither a Decision value nor a grant. |
| Prepared / sent | Local prepared package provenance / deferred external submission history. |
| B | Fixed full SHARE-protected write inputs for both Decision and Approval (§12.2; director ruling 2026-10-17). |
| Historical replay | Original actor's matching saved command under current read entitlement. |

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

| Choice | Adopted decision |
| --- | --- |
| Purpose/value/stage | PREPARE_SUBMISSION/PROCEED only; Publication READY at new Decision, request and approval decision. |
| Authority | OWNER/APPROVER Decision, HUMAN or AGENT; independent HUMAN APPROVER separately authorizes. |
| Basis/blockers | B11 complete manuscript set and exact reachable blocker policy; no affirmative-only subset. |
| Independence | B11 decider/material-author policy; B09 requester/reviewer/approver exclusions, all by exact actor. |
| Capacity | Decision 1..10,000 reviews; B09 approval 1..100. A saved basis above 100 cannot be approved in this slice; no truncation or silent limit increase. |
| History | One Decision per project/purpose/exact manuscript; no correction, supersession or late basis. |
| Persistence | Reuse B11 relation and B09 tuple; no new table/column/hash owner or dependency. |
| Adapters/effects | Application only; no new routes/CLI commands, READY transition, consent or consumption. |
| Rejection/disposition | Preserve approved Batch C boundaries; preparation reconsideration and manuscript disposition remain unavailable without their own extension. |

### 11.2 Pinned error mappings

Matches [api/errors.py](../../src/researchbase/api/errors.py) and
[cli/errors.py](../../src/researchbase/cli/errors.py).

| Code | HTTP | CLI exit | Use |
| --- | --- | --- | --- |
| AUTHENTICATION_REQUIRED | 401 | 3 | Missing trusted principal. |
| FORBIDDEN | 403 | 3 | Current authority/read entitlement, foreign project or replay actor mismatch. |
| VALIDATION_ERROR | 422 | 2 | Closed DTO/type/literal, Unicode, bounds, duplicate IDs or condition shape. |
| NOT_FOUND | 404 | 3 | Entitled exact target or history absent. |
| CONFLICT_OF_INTEREST | 403 | 3 | Decider/material-author or approval independence failure. |
| FROZEN_REFERENCE_REQUIRED | 409 | 5 | New Decision target lacks required FROZEN seal. |
| DECISION_BASIS_INVALID | 409 | 4 | No/too many reviews, applicable new-Decision blocker, missing/mismatched approval basis or unapproved basis subset. |
| INVALID_STATE_TRANSITION | 409 | 4 | New Decision's Publication is not READY. |
| APPROVAL_PURPOSE_TARGET_COMMAND_INVALID | 409 | 4 | Well-typed but unlisted approval purpose/target/command pairing. |
| APPROVAL_GATE_FAILED | 409 | 4 | Approval requires active Project, READY lifecycle or no applicable blocker. |
| APPROVAL_TARGET_STALE | 409 | 4 | Approval's new-write target unfrozen, invalid or replaced by newer selected target. |
| REJECTION_RECONSIDERATION_REQUIRED | 409 | 4 | Preparation project/purpose rejection fence; B12 is no reconsideration. |
| GRANT_INVALID | 409 | 4 | Current grant projection: finite expiry reached. |
| GRANT_STALE | 409 | 4 | Current projection: terminal status or issuing authority lost. |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Changed replay, duplicate decided scope or B09 pending/decided conflict. |
| IMMUTABLE_RECORD | 409 | 4 | Historical edit/delete/late basis append. |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Concrete FK/integrity violation. |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Corrupt saved hash/basis/history, nonindependent review, or Decision required closure not VALID. |
| CONCURRENT_MODIFICATION | 409 | 4 | Exhausted retryable transaction conflict or existing timeout normalization. |
| INTERNAL_ERROR (fallback string) | 500 | 1 | Existing sanitized unexpected-error fallback. |

Decision unsupported literals fail DTO validation before basis admission. Approval
purpose remains B09 strict str dispatch (unsupported string 409, wrong primitive
422). A >100 required-review set fails B09 command bounds as VALIDATION_ERROR;
a smaller caller subset fails equality as DECISION_BASIS_INVALID. Preserve B09
current grant diagnostic precedence: terminal status, expiry, approver authority,
then gate order. Direct-SQL P17F1/F2/F3 retain existing UoW mappings to
IMMUTABLE_RECORD / PROVENANCE_CLOSURE_VIOLATION / IDEMPOTENCY_CONFLICT;
P16T1/R1/B1/G1/C1/A1 retain B09 mappings. SQL structural denials are not a new
Application error vocabulary; map new named CHECKs to the corresponding category.

### 11.3 DTO fields, Python types, limits and enums

Frozen/slots dataclasses, exact UUID objects internally, canonical lowercase
hyphenated UUID text at any future wire boundary. Reject unknown fields, coerced
primitive types, NUL/surrogates and blank text. Normalize text with existing NFC
`_text`, preserving meaningful whitespace, plus explicit NUL validation. All
readback times are aware UTC; hashes lowercase 64-hex. No caller actor, time,
hash, status, publication pointer, independence assertion, supersedes ID or basis.

| DTO | Exact fields |
| --- | --- |
| `RecordPrepareSubmissionDecisionCommand` | `id: UUID`, `project_id: UUID`, `manuscript_version_id: UUID`, `question: str`, `rationale: str`, `decision_type: Literal['PREPARE_SUBMISSION']='PREPARE_SUBMISSION'`, `decision: Literal['PROCEED']='PROCEED'`. Both texts 1..16,000 Unicode code points after NFC. |
| `GetPrepareSubmissionDecisionQuery` | `project_id: UUID`, `id: UUID`. |
| `PrepareSubmissionDecisionReadback` | `id`, `project_id`, `publication_id`, `manuscript_version_id`, `decided_by`: UUID; `decision_type`, `decision`: above literals; `question`, `rationale`: str; `decided_at: datetime`; `target_content_hash`, `basis_set_hash`, `content_hash`: str; `hash_scheme: Literal['sha256-cjson-v1']`; `basis: tuple[DecisionBasisReference, ...]`; `current_validity: Literal['VALID','STALE','INVALID']`; `current_blocking_issue_ids: tuple[UUID, ...]`; `evaluated_at: datetime`. |
| `DecisionBasisReference` | Existing `type: str`, restricted here to ManuscriptVersion/InternalReviewRecord; `id: UUID`, `content_hash: str`, `ordinal: int` (exact int, not bool, ≥0). Readback ordinals are derived canonical positions. |
| B09 `RequestApprovalCommand`, preparation branch | `id`, `project_id`, `basis_decision_id`: UUID; existing positional `scientific_conclusion_version_id: UUID | None` supplied as None; keyword-only `manuscript_version_id: UUID | None = None` supplied nonnull; `review_ids: tuple[UUID, ...]`, 1..100 distinct, UUID-text sorted; `approval_purpose: str` supplied as PREPARE_SUBMISSION (shared DTO default stays INTERNAL_SCIENTIFIC_RELEASE). |
| B09 `DecideApprovalCommand` | `id`, `project_id`, `approval_request_id`: UUID; `decision: Literal['APPROVE','APPROVE_WITH_CONDITIONS','REJECT']`; `rationale: str` NFC/nonblank 1..16,384; `valid_until: datetime | None=None`; `requires_current_author_consent: bool=False` (exact bool). |
| B09 exact read inputs | `project_id: UUID` plus `request_id`, `decision_id` or `grant_id: UUID` for its respective method. |
| B09 request readback | `id`, `project_id`, `requested_by`, `basis_decision_id`: UUID; `scientific_conclusion_version_id: UUID | None` null, `manuscript_version_id: UUID | None` nonnull; `target_content_hash`, `basis_decision_hash`: str; `target_hash_scheme: Literal['sha256-cjson-v1']`; `approval_purpose: Literal['PREPARE_SUBMISSION']`; `requested_at: datetime`; `reviews: tuple[DecisionBasisReference, ...]`; `status: Literal['PENDING','DECIDED','WITHDRAWN']`; `event_ids: tuple[UUID, ...]`. |
| B09 approval decision readback | `id`, `approval_request_id`, `decided_by`: UUID; `decision`: outcome literals above; `valid_until: datetime | None`; `requires_current_author_consent: bool`; `rationale`, `content_hash`: str; `decided_at: datetime`; `grant: ApprovalGrantReadback | None`. |
| B09 grant readback | `id`, `approval_decision_id`, `project_id`: UUID; same nullable target pair as request; `purpose: Literal['PREPARE_SUBMISSION']`; `target_content_hash: str`; `allowed_command: Literal['freeze_prepared_submission']`; `max_uses: Literal[1]`; `valid_until: datetime`; `status: Literal['ACTIVE','CONSUMED','EXPIRED','REVOKED','STALE']`; `event_ids: tuple[UUID, ...]`; `usable: bool`; `unusable_code: str | None` (existing ErrorCode values); `evaluated_at: datetime`. |

Decision ceiling is 10,000 reviews, one manuscript ref; no pagination/truncation.
Diagnostic blocker IDs are complete, distinct, UUID-text sorted and uncapped.
Historical verification imposes no new admission ceiling. New Decision text limits
match B11. B09 first-write bounds must not reject an otherwise matching historical
longer record before its replay lookup.

APPROVE/REJECT require valid_until=null and consent=false. Conditional approval
requires aware finite UTC-normalized valid_until with fresh decided_at < valid_until
<= decided_at + timedelta(hours=720), consent true or false for PREPARE only.
APPROVE derives grant expiry exactly decided_at+720 hours; REJECT creates no grant.
Equality at expiry denies. No free-text executable conditions. Stored lifecycle
enums do not authorize new transitions; B12 adds no revoke/expire/withdraw command.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch with types and constraint names

Use a forward migration after accepted B11/B09 and the actual head, never edit
0042/0045 or reserve a number. No CREATE TABLE or ADD COLUMN in B12. B11 supplies
`decision_basis_manuscripts(decision_id UUID, manuscript_version_id UUID,
ordinal INT)`, all NOT NULL, `pk_b11_basis_manuscripts`, concrete
`fk_b11_basis_decision`/`fk_b11_basis_manuscript` RESTRICT FKs,
`uq_b11_one_manuscript`, `uq_b11_manuscript_ordinal`, `ck_b11_manuscript_ordinal`
and `ix_b11_manuscript_target`. Retain these; never add UNIQUE(manuscript_version_id).

Parent types remain UUID IDs/project/actor/supersedes, VARCHAR(40) purpose,
VARCHAR(16) decision, TEXT question/rationale, TIMESTAMPTZ decided_at,
CHAR(64) basis/content hashes, VARCHAR(32) scheme. Supersedes stays NULL for PREPARE.
B09 retains 0045's request manuscript UUID FK/CHAR(64) hash/TEXT scheme,
TEXT purpose, decision TIMESTAMPTZ condition/BOOLEAN consent, and grant
TEXT command/TIMESTAMPTZ expiry; no persisted max_uses or duplicate target.

Post-Batch-C composed policy sketch (include only already accepted predecessor
branches plus PREPARE; retain their exact guards, never admit a missing purpose):

```sql
-- Drop the accepted predecessor's finite tuple CHECK(s) by actual catalog name,
-- e.g. ck_b11_decision_policy; retaining a narrower CHECK would still deny PREPARE.
ALTER TABLE decision_records ADD CONSTRAINT ck_b12_decision_policy CHECK (
 (decision_type='INTERNAL_SCIENTIFIC_RELEASE' AND decision='PROCEED') OR
 (decision_type='READY_FOR_SUBMISSION' AND decision='PROCEED') OR
 (decision_type='PREPARE_SUBMISSION' AND decision='PROCEED') OR
 (decision_type='REVISION_RESPONSE' AND decision IN ('REQUIRE_CHANGE','ACCEPT_NO_CHANGE')) OR
 (decision_type='RECONSIDER_REJECTION' AND decision IN ('REVISED_TARGET','CORRECTED_REVIEW'))
);
ALTER TABLE decision_records ADD CONSTRAINT ck_b12_text_bounds CHECK (
 decision_type<>'PREPARE_SUBMISSION' OR
 (length(question) BETWEEN 1 AND 16000 AND length(rationale) BETWEEN 1 AND 16000)
);
-- B09's existing ck_b09_request_tuple / ck_b09_grant_tuple already admit
-- PREPARE_SUBMISSION + manuscript + freeze_prepared_submission: retain them.
-- Preserve uq_b09_pending_manuscript, one decision per request and one grant
-- per approving decision. No package/consumption FK is added in this slice.
```

Confirm predecessor names against its accepted migration; do not silently drop
unrelated checks. Existing nonblank/hash/scheme/FK checks remain in force.

| Guard/constraint | Required extension, preserving other purposes |
| --- | --- |
| `b11_require_snapshot` / `b11_decision_guard` | Include PREPARE in READ COMMITTED/preheld full B SHARE validation; PREPARE/PROCEED, NULL supersedes and text bounds only. Test FIRST SQL separately; no session flag bypass. |
| `b11_manuscript_basis_guard` | Admit PREPARE; same-transaction parent xmin, exact manuscript FOR UPDATE, FROZEN seal, same Project/Publication READY, zero conclusion/other basis. Purpose-specific no-replacement scope raises P17F3, allowing READY and PREPARE to coexist. |
| `pr215_basis_guard` | Manuscript review dispatch for both purposes; exact review target/hash/project and no late INSERT. Preserve legacy conclusion/revision/reconsideration dispatch; never route through conclusion-only logic. |
| `pr215_complete_basis`, `b11_complete_manuscript`, `pr215_complete_decision`, `pr215_complete_review` | Preserve DEFERRABLE INITIALLY DEFERRED final-graph checks; PREPARE exactly one manuscript plus 1..10,000 reviews, bidirectional equality to all committed exact-manuscript reviews, independent saved attribution, READY stage and no §3.2 blockers. New storage ordinals match derived positions; hash readers independently derive positions. Application still verifies CAS/full hashes/live credentials/current validity. |
| `b11_manuscript_basis_immutable`, existing `pr215_*immutable` | P17F1 update/delete denial; same-transaction guard denies late basis append. No new Decision event table. |
| B09 `pr216_request_guard`, `pr216_decision_guard`, `pr216_grant_guard`, `pr216_relation_guard` | Explicit PREPARE manuscript dispatch to matching affirmative prior Decision and saved reviews, all independent gates, finite scope/conditions and same-project/purpose fence. No readiness-purpose substitution or naked consent assertion. |
| B09 `pr216_complete_request/reviews/decision/grant` and event/authority-loss guards | Preserve deferred request-review completeness, one immutable decision/optional grant and atomic request/grant events/staleness; no effect or consent write. |

Normal-role SQL must prehold the same B inventory and target/scope coordination;
SQL structural guards cannot replace Application bytes/hash/credential verification.
Functions use `search_path=pg_catalog,public,pg_temp`. Do not rerun historical
complete-set equality whenever a later review is inserted. Downgrade acquires
ACCESS EXCLUSIVE on Decision parent/all installed basis tables in lexical order,
refuses if any PREPARE Decision or approval history exists, otherwise restores
prior finite checks/dispatch. Preserve all predecessor history; no destructive
backfill or scientific CASCADE.

### 12.2 Exact lock order per command

Freeze the literal B04_SNAPSHOT_TABLES inventory from
`src/researchbase/persistence/manuscript_freeze_repository.py` into migration and
adapter tests, not runtime catalog discovery or silent inheritance. Define the
following sorted, deduplicated fixed inventory, shared by B11/B09:

```python
B = tuple(sorted(set(B04_SNAPSHOT_TABLES) | {
    'internal_review_records', 'manuscript_versions', 'publications',
    'review_issue_events', 'review_issues',
}))
```

**Director ruling, 2026-10-17 (§12.2):** PREPARE_SUBMISSION Approval
writers use full inventory B, identical to B09 approval writers, including
`internal_review_records`, `review_issues` and `review_issue_events`. The former
narrow inventory N is withdrawn. Wider SHARE locking is the established
conservative pattern and excludes upstream Issue insertion during the gate.

B04 covers authority, mutable validity and concrete scientific/input/placement
relations. Decision and Approval write none of B. Decision/basis and approval/event
tables are excluded from their write input inventory. Approved extensions must
explicitly reconcile new mutable read dependencies; never silently claim an old
inventory protects a new table.

Configure READ COMMITTED and disable autoflush without SQL. FIRST transactional
SQL on each writer is one `LOCK TABLE <B in lexical order> IN SHARE MODE`.
No SELECT, SET LOCAL, advisory, row lock or navigation precedes it. Then install
`SET LOCAL lock_timeout='10s'`, `SET LOCAL statement_timeout='30s'`. A connection/
server setting made before BEGIN bounds the initial SHARE wait; later SET LOCAL
cannot bound an earlier wait. Acquire final lock modes directly, no upgrades.
All advisory keys below are parameter-bound canonical UUID text via
`pg_advisory_xact_lock(hashtextextended(:key,0))`.

| Command | Exact operations after first SHARE and timeouts |
| --- | --- |
| `record_prepare_submission_decision` | B; advisory `b12:decision:<command.id>`; exact manuscript FOR UPDATE; Project FOR SHARE; owning Publication FOR SHARE; fresh reader authorization and UUID lookup. If new: fresh OWNER/APPROVER authorization, target/stage/full closure/material-author check; plain SELECT all manuscript reviews UUID-sorted, their Issues/events and exact upstream blockers in deterministic UUID order; verify histories/hashes and complete set, absence of blockers and same-purpose scope; derive material; fresh writer check; insert Decision, manuscript basis then UUID-sorted review basis; force deferred/final checks below. Racing existing record exits to lock-free replay (§7). |
| B09 `request_approval`, PREPARE | B; advisory `pr216:uuid:<command.id>`; advisory `pr216:scope:<project_id>:PREPARE_SUBMISSION`; exact manuscript FOR UPDATE; Publication FOR SHARE; fresh reader then writer authorization; replay/fence/pending/target checks; verify committed PREPARE Decision and its UUID-sorted saved review basis, later reviews/all applicable Issues, full closure/stage/independence; prelock older ACTIVE same-scope other-target grants FOR UPDATE in UUID order; fresh writer check; insert request and UUID-sorted review relations, automatic events/staleness; deferred/final checks. |
| B09 `decide_approval`, PREPARE | B; advisory `pr216:uuid:<command.id>`; plain request routing lookup now; advisory verified request project/purpose scope; exact manuscript FOR UPDATE; Publication FOR SHARE; request FOR UPDATE and reread; fresh reader then HUMAN APPROVER checks; reread decision/fence/current gates/condition expiry; REJECT prelocks all affected ACTIVE same-scope grants UUID-sorted; fresh writer check; insert immutable decision and derived grant iff approving, automatic request/grant events and rejection staleness; deferred/final checks. |
| `get_prepare_submission_decision`, B09 `get_request/get_decision/get_grant`, completed replay | One REPEATABLE READ, READ ONLY UoW, set before first data query; plain authorization/parent/basis/target/review/history SELECTs and saved integrity verification; current diagnostics plus final fresh-clock read entitlement. No explicit table, advisory or row locks, FOR SHARE/UPDATE, writes, maintenance or locking nested helper. |

Keep B09's shared `pr216` namespace for all purposes/normal-role SQL; no new
preparation approval namespace. B12 target exclusion coordinates with B11 and
B05 even though request UUID namespaces differ. Decision cannot hold any B table
write lock; B09 obtains B before grant locks to avoid an authority-writer cycle.

Review INSERT (including zero Issues) and every applicable Issue/disposition
writer must retain accepted exact-target FOR UPDATE coordination before predicate
changes. B05 manuscript review/disposition contracts retain SHARE-first order;
upstream table ROW EXCLUSIVE writes conflict with B. Source dispute, impact,
correction, placement, parent state and authority writers conflict with B through
ordinary table writes. Immutable saved Decision membership needs no read lock.
Old target-first writers may deadlock with SHARE-first paths; do not claim this
protocol removes every deadlock. Retry the whole transaction under §7.

Use plain review enumeration under B, not hidden FOR SHARE. Invoke B04/B05
verifiers within the existing UoW; write collector only after target/Project/
Publication locks, never on reads. Existing `DecisionService._authorize` locks
Project: use the accepted snapshot-read authority variant instead. Use existing
snapshot-read UoW adapters throughout nested closure verification, with no HUMAN-
REVIEWER-only read restriction borrowed from review creation.

After each blocking wait, reread affected durable state in READ COMMITTED and
use fresh `clock_timestamp()`, not now()/transaction_timestamp(). Recheck verifier,
binding, membership, roles, stage and relevant gate. Force
`SET CONSTRAINTS ALL IMMEDIATE` before final authorization so FK/deferred waits
precede it; any subsequent wait requires another final check before commit.
Scheduled expiry must deny even while SHARE prevents database authority mutation.
Snapshot reads promise entitlement in their one snapshot plus advancing-clock
expiry, not exclusion against revocation committed after snapshot start.

### 12.3 Ordered build steps and real file paths

1. Confirm accepted B09/B11 and lifecycle implementations, exact head and approval
   scope. Add §12.1 forward guard/check migration under `migrations/versions/`;
   retain Batch C dispatch/DDL names and prior golden material.
2. Extend pure validation in `src/researchbase/domain/decision.py` only as needed;
   reuse literal builders and canonical reconstruction. Keep Domain free of
   ORM/SQLAlchemy Session/FastAPI/Typer imports.
3. Extend `src/researchbase/application/decision.py` with the two methods/DTOs,
   B04 in-UoW verification, B05/B11 complete basis and author/blocker policy,
   historical verification/replay and SQLSTATE-bounded retry. Reuse accepted
   ArtifactStore injection; do not open another service transaction for a gate.
4. Extend DecisionRepository/UnitOfWork in `src/researchbase/application/ports.py`
   and purpose-scoped SQL in `src/researchbase/persistence/decision_repository.py`.
   Reuse B11 manuscript reads/inserts, plain review enumeration in
   `src/researchbase/persistence/internal_review_repository.py`, and existing
   snapshot adapters/normalization in `src/researchbase/persistence/uow.py`.
5. Connect the exact PREPARE Decision verifier in
   `src/researchbase/application/approval.py` and
   `src/researchbase/persistence/approval_repository.py`; reuse
   `src/researchbase/domain/approval.py` finite tuple/material and B09's request,
   decision, grant, event and authority-loss guards. Do not implement B09 again
   or change other purposes' policy. Adjust constructor composition only if
   needed in `src/researchbase/api/app.py` and
   `src/researchbase/cli/composition.py`; add no route or CLI command. Existing
   `api/errors.py` and `cli/errors.py` mappings remain unchanged.
6. Add §12.4 tests; run focused static/unit/architecture and affected PostgreSQL
   regressions, record exact results and dependency limitations, review against
   specs/diff/evidence, then stop. Do not build §12.5 to make a test pass.

### 12.4 Test files and required cases

Use disposable PostgreSQL 18.x `phase2_database_url` and exported B04/B05/Approval
builders, plus accepted B11/lifecycle paths when present. No SQLite, bypassed
triggers or fake READY transition. Race tests need two independent engines/backend
PIDs, barriers and observed pg_blocking_pids/pg_locks, not sleep-only evidence.

| File to add | Required cases |
| --- | --- |
| `tests/unit/phase2/test_b12_prepare_decision_contract.py` | Closed/exact UUID/types, literals, extra fields, NFC/blank/NUL/surrogates/16,000 boundaries, strict ordinals; 10,000/10,001 reviews; B09 100/101 limit mismatch, no truncation; every pinned HTTP/CLI pair and outcome/condition/720-hour/expiry edge. |
| `tests/unit/phase2/test_b12_prepare_decision_hash_vectors.py` | Independent literal JSON/digest oracles for one/many/adverse reviews and PREPARE vs READY content inequality; same basis allowed but distinct Decision purpose hashes; member permutation/persisted-ordinal independence, changed target/hash/rationale/member inequality; no new time/stage/diagnostic keys, unchanged release/B11/Approval/Phase 1 vectors. |
| `tests/integration/phase2/test_b12_prepare_decision.py` | Exact frozen VALID manuscript in READY succeeds; DRAFTING/INTERNAL_REVIEW and unfrozen/wrong version/project/hash/seal/CAS corruption fail atomically; complete adverse/zero-Issue reviews, nonindependent HUMAN history and transitive contributor denial; decider-reviewer overlap allowed; direct/upstream blocker scope and verified B08 history only, no manuscript disposition assumption; coexistence with B11 READY Decision, same-purpose nonreplacement. No approval/lifecycle/Issue/consent/package writes. |
| `tests/integration/phase2/test_b12_prepare_approval.py` | Real B09 request→approve/conditional/reject with exact PREPARE basis and full saved review set; READY/release/reconsideration Decision or grant substitution fails, wrong manuscript/hash/project fails; every pairwise approver exclusion, Agent/OWNER-only denial; later zero-Issue/adverse/blocking review rechecks, >100 review basis cannot authorize; grant iff approving, exact command/expiry/max_uses and atomic events. Scope rejection includes older PENDING and another Publication; other purpose/project unaffected; B12 Decision does not bypass fence or add reconsideration. No consumption/receipt/package effect. |
| `tests/integration/phase2/test_b12_prepare_replay.py` | Same UUID/restart/uncertain-commit recovery; changed payload/different actor/project deny, new UUID same scope conflicts; current invalidity/new review/blocker/stage/write-role loss permit entitled history only; lost read entitlement denies; all exact reads/completed replay observed lock-free RR including nested helpers and current grant diagnostics. |
| `tests/integration/phase2/test_b12_prepare_schema.py` | Real catalog types/names/CHECKs/FKs/indexes, no new tables/columns; clean install/populated Batch C upgrade preserves history/hashes, populated PREPARE downgrade refuses; normal-role SQL wrong/missing/mixed/extra/omitted basis and forged scope/attribution deny; no late append/update/delete, parent-only/deferred force failure, preheld B/isolation enforcement, both purposes coexist but same-purpose target exclusion; rollback at each Decision/approval/child/event stage. |
| `tests/integration/phase2/test_b12_prepare_races.py` | Both commit orders of same/different UUID scope writes, zero-Issue review INSERT, direct/upstream BLOCKING Issue and authorized disposition, validity/READY-state/authority changes and rejection vs request/decision; normal SQL parity and lock observations; credential/role scheduled expiry after B/advisory/target/grant/deferred waits; three fresh attempts only for 40001/40P01, no retry of timeout/business conflict/unknown commit; all staged failures atomic. |
| `tests/architecture/test_b12_prepare_boundaries.py` | Shared Application boundary, pure Domain/closed DTOs/concrete FKs, no JSON semantic core or second owner; SHARE FIRST SQL, no write to B; lock-free one-snapshot reads/replay; no READY/consent/package/receipt/ExternalEffect side effects, inherited release/Batch C boundaries unchanged. |

After implementation run these files, B09/B11 tests, applicable accepted B07/B08/
B10 regressions, existing `tests/unit/test_approval.py`,
`tests/unit/phase2/test_pr2_15_decision.py`,
`tests/integration/phase2/test_approval.py`, `test_pr2_15_decision.py`,
`test_pr2_15_decision_schema.py`, B04 freeze/migration/races and B05 manuscript
review/basis/migration/races suites. Also run `uv run ruff check .`,
`uv run ruff format --check .`, `uv run pyright`, `git diff --check`, and
`uv run pytest tests/unit tests/architecture`. Missing dependency tests do not
count as acceptance; the external loop owns the whole-suite run.

### 12.5 Not in this slice

| Deferred behavior | Owning dependency |
| --- | --- |
| INTERNAL_REVIEW→READY and readiness grant consumption | Separate Publication lifecycle/effect contract; B11 judgment alone never transitions. |
| Prepared package construction/manifest, consent capture/withdrawal, freeze/supersession | Publication package/consent contract beyond PR2-17 attribution foundation. |
| Grant consumption, canonical request/receipt, result FK and atomic effect | R2/R3/R4 consuming-command contract, including SERIALIZABLE transaction and mandatory exact current consent. |
| Preparation rejection reconsideration or manuscript Issue disposition | Separate manuscript extensions to approved B10/B08; no inferred authorization. |
| Revoke/expire/withdraw commands, automatic staleness propagation/evaluator | Separate lifecycle/propagation slice; preserve existing atomic authority-loss/new-target/rejection behavior. |
| New HTTP/CLI endpoints, generic policy engine or larger review limits | Separate explicit adapter/policy authorization. |
| SubmissionVersion/SubmissionRecord, venue send, ExternalEffect, Agent runtime | Later phases/slices; no implication from local preparation authority. |

## 13. Open questions for the owner — override register

| Owner may override | Decision adopted in this draft |
| --- | --- |
| Earlier stage for preparation judgment? | Require READY, matching its approval row; missing lifecycle remains a dependency, never implemented here. |
| Reuse readiness Decision/reviews? | Distinct PREPARE Decision mandatory. Same exact immutable reviews may appear in both Decisions, with a complete fresh gate for each; no reuse of readiness authority. |
| Decision/reviewer/approver separation? | B11 permits reviewer-decider overlap; B09 independent HUMAN approver excludes both, requester and material authors. |
| Review limit mismatch? | Preserve approved 10,000 Decision / 100 Approval ceilings; fail without truncation. A larger authorization limit needs a separate approved refinement. |
| Consent condition required already at approval? | Preserve B09 approving outcomes/typed conditions; mandatory true gate is enforced at later consumption regardless of stored false on APPROVE. No consent subsystem here. |
| Rejection recovery or new effects? | No expansion of B10 manuscript scope, no readiness transition, consumption or package freeze. |

All proposed answers are adopted above. Overrides require corresponding contract
edits before approval; no unanswered question permits weakening a frozen invariant.

## 14. Documentation verification note

Only this proposal is changed. §12.4 describes future tests, not executed B12
implementation. Documentation-task check results follow below; the whole suite
is reserved for the owner's loop. No implementation or Phase-exit claim follows.

Checks executed 2026-10-16 using the installed shared environment, without syncing
or changing dependencies. Every `uv` command below used this exact common prefix:

```sh
UV_CACHE_DIR=/tmp/researchbase-b12-uv-cache UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv PYTHONPATH=src
```

| Command after the prefix | Observed result |
| --- | --- |
| `uv run --no-sync ruff check .` | PASS: All checks passed! |
| `uv run --no-sync ruff format --check .` | PASS: 570 files already formatted. |
| `uv run --no-sync pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject` | PASS: 0 errors, 0 warnings, 0 informations. |
| `uv run --no-sync pytest tests/unit tests/architecture` | 2,343 passed, 4 failed, 12 errors, 7 warnings in 46.83s; not PASS. |
| Focused unit/architecture command below | PASS: 196 passed, 3 warnings in 0.91s. |
| PostgreSQL command below | 1 setup error in 0.59s; stopped before any database test completed. |
| `git diff --check` (no environment prefix needed) | PASS: no output. |

Exact focused unit/architecture command after the common prefix:

```sh
uv run --no-sync pytest tests/unit/test_approval.py tests/unit/phase2/test_pr2_15_decision.py tests/unit/phase2/test_b04_manuscript_contract.py tests/unit/phase2/test_b04_manuscript_hash_vectors.py tests/unit/phase2/test_b05_review_contract.py tests/unit/phase2/test_b05_review_hash_vectors.py tests/architecture/test_basic_approval.py tests/architecture/test_b04_boundaries.py tests/architecture/test_b05_review_boundaries.py
```

Exact PostgreSQL command after the common prefix:

```sh
DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run --no-sync pytest tests/integration/phase2/test_approval.py tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b04_manuscript_races.py tests/integration/phase2/test_b05_manuscript_review.py tests/integration/phase2/test_b05_review_basis.py tests/integration/phase2/test_b05_review_migration.py tests/integration/phase2/test_b05_review_races.py -x
```

The four broad-run failures are HG1 runner AF_UNIX socket-bind PermissionErrors.
The twelve architecture setup errors require RB_TEST_ADMIN_URL. The separate
PostgreSQL attempt supplies it and DATABASE_URL explicitly, but localhost IPv4
and IPv6 connections are sandbox-denied with “Operation not permitted”. Its first
Approval fixture cannot create a disposable database; remaining cases were not
run. No PostgreSQL server version, migration assertion or database PASS was
obtained. These environment failures remain failures/errors, not acceptance.

A local Python/AST audit checked all 32 relative links, the required status,
14 numbered sections and all 19 ErrorCode HTTP/CLI pairs against the current
source dictionaries. The fallback string is separately confirmed as HTTP 500 /
CLI exit 1. Only this new proposal appears in `git status --short`; no code,
architecture baseline, dependency, test or existing proposal is changed. No full
suite was run, and no commit, push or branch was created.
