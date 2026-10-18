# B14r READY_FOR_SUBMISSION Approval Gate Contract — DRAFT

**Status: APPROVED by owner 2026-10-18 — first slice authorized for implementation**

## Start here (for the implementer)

B14r enables requests and independent HUMAN approval for one exact frozen
manuscript's READY_FOR_SUBMISSION permission. It is the READY analogue of B12's
PREPARE_SUBMISSION gate. The basis is B11's READY_FOR_SUBMISSION/PROCEED Decision;
the owning Publication must be INTERNAL_REVIEW. Approval creates permission only.
B14 owns consumption and the INTERNAL_REVIEW→READY effect.

Read §§1–4 first; use §10 for terms, §11 for fixed draft decisions and §12 for
construction. These are proposed policies awaiting approval, not shipped behavior.
Contract approval and separate execution authorization are distinct.

Build in this order after authorization:

1. Reconcile the migration head and B11/B09/B12/B14a prerequisites (§1).
2. Extend the existing ApprovalService purpose dispatch and saved-basis verifier;
   keep the exact request, decision and grant DTOs (§§4, 11.3).
3. Add a forward guard amendment, preserving existing tables and purposes (§12.1).
4. Use the branch's shared ApprovalService lock prefixes for writes and lock-free
   snapshot reads/replay, including nested helpers (§12.2).
5. Run the planned tests and focused regressions, record exact evidence and stop
   at the exclusions in §12.5. This document authorizes no implementation.

Five rules whose violation fails review:

1. Bind READY_FOR_SUBMISSION to the exact FROZEN, VALID manuscript ID/hash,
   B11 Decision and INTERNAL_REVIEW Publication; never substitute PREPARE.
2. Preserve the Decision's entire saved review set, including adverse reviews;
   revalidate later reviews, exact closure, applicable blockers and independence.
3. Only an independent current HUMAN APPROVER may decide; OWNER-only and Agent
   approval cannot substitute. A Decision is not an ApprovalDecision.
4. Keep history immutable, rejection fences purpose-specific and grant scope
   finite. Force deferred constraints before final advancing-clock authorization.
5. No publication mutation, receipt, consumption, package or external effect;
   exact reads/replay take one REPEATABLE READ, READ ONLY snapshot without
   explicit table, advisory or row locks.

## 1. Purpose, authority and inspected baseline

| Authority | Constraint carried forward |
| --- | --- |
| [System 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 6, 12; [Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A17–A23 | Deterministic facts precede authority; frozen provenance and immutable history; Review, Decision, Approval, Command and ExternalEffect remain separate. |
| [Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md); [Cross-Phase 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§9–18, 24 | Existing typed governance records, concrete RESTRICT FKs, common Application boundary and additive compatibility. |
| [Phase 2 specification 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), governance/publication, PR2-15/16/17; [Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), §§4–7 | Frozen manuscript, internal review, distinct readiness authorization; preparation is separate from readiness and sending. |
| [Field contract 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md), approval/Decision rows; [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md); [R3 18](../architecture/18_Phase2_Design_R3_Targeted_Remediation_v1.0.md), §§1, 5 | Exact typed basis; unchanged literal material_version=1 hashes; derived canonical basis order; consumption has its own receipt. |
| [Governance R2 17](../architecture/17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md), §§1–2; [Temporal R4 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md), TEMP-AUTH-01 | Finite READY tuple, independent HUMAN approval, project/purpose rejection fence, one use, at most 30 days and fresh post-wait DB time. |
| [B09](B09_Approval_Tuples_Contract_DRAFT.md), [B11](B11_Ready_For_Submission_Decision_Contract_DRAFT.md), [B12](B12_Prepare_Submission_Decision_Contract_DRAFT.md) | Exact request/Decision/review binding; B11 judgment supplies READY basis; B12 supplies the approval-gate pattern and full B lock protocol. |
| [B14a](B14a_Publication_Internal_Review_Entry_Contract_DRAFT.md), [B14](B14_Publication_Ready_Transition_Contract_DRAFT.md), [B13](B13_Grant_Consumption_Contract_DRAFT.md); [Harness 09](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 18–21 | Entry, grant issuance and consumption are separate slices; no direct Harness persistence; acceptance requires executed evidence. |

Inspected branch baseline:

- [ApprovalService](../../src/researchbase/application/approval.py)
  `_manuscript_gate` accepts only PREPARE_SUBMISSION. `_prepare_basis` and
  `_prepare_gate` verify its saved Decision and READY Publication. READY fails
  DECISION_BASIS_INVALID before a request can be issued.
- [0058](../../migrations/versions/0058_b12_prepare_submission.py)
  `pr216_gate` dispatches manuscript PREPARE to `b12_approval_gate`, then raises
  P16B1 for READY. The request/decision guards call this gate, so the atomic approval/grant
  issuance flow is denied. [0059](../../migrations/versions/0059_b13_grant_consumption.py)
  retains grant INSERT scope/authority/expiry checks; it does not enable READY basis.
- [B11/0054](../../migrations/versions/0054_b11_ready_for_submission.py) and
  [DecisionService](../../src/researchbase/application/decision.py)
  `_readiness_readback` already supply immutable READY_FOR_SUBMISSION/PROCEED
  with `decision_basis_manuscripts` and `decision_basis_reviews`.
- [B09/0055](../../migrations/versions/0055_b09_approval_tuples.py) and
  [domain approval tuples](../../src/researchbase/domain/approval.py) already
  register READY → ManuscriptVersion → `transition_publication_ready`.
  No new purpose, command, table or column is needed.
- [0062](../../migrations/versions/0062_b14a_publication_entry.py) is the current
  head. It implements real INTERNAL_REVIEW entry and exact manuscript lifecycle
  history; its Publication CHECK still admits only DRAFTING/INTERNAL_REVIEW.
  The owner identifies B14 as approved; its consumption behavior is a dependency,
  not implemented or authorized by this proposal. Older inventories in linked
  drafts are historical and do not describe this branch.

No B14r execution pack exists in `execution/phase2/`. This draft is no replacement
execution authorization. Source presence and previous evidence do not establish
new gate acceptance.

## 2. Scope, dependency boundaries and non-goals

Enable the READY branch of the existing `request_approval` and `decide_approval`,
and their existing exact `get_approval_request`, `get_approval_decision` and
`get_approval_grant` reads. An approving decision issues one ACTIVE grant in its
own transaction; there is no standalone issue-grant command.

Reuse B04 seal verification, B05 manuscript reviews, B08 Issue-history validation,
B11 saved readiness basis, B09 finite approval policy, B12 transaction patterns
and B14a's actual entry command. B10's reconsideration implementation remains
conclusion-release only; READY reconsideration stays unavailable. B13 owns grant
lifecycle and B14 owns READY consumption. Neither is reimplemented here.

## 3. Invariants and conservative judgments

At both request creation and approval decision require ACTIVE Project; exact
same-project FROZEN manuscript with `frozen_at`, `placement_set_hash`, content hash
and sha256-cjson-v1 seal; owning Publication INTERNAL_REVIEW and its selected
`current_manuscript_version_id` equal to that exact target. The pointer checks
eligibility; it never selects or replaces the caller's exact reference. Verify
B14a entry history for that manuscript, using its history verifier without write
admission or locks on read paths. Do not promote DRAFTING implicitly.

Verify full B04 document CAS bytes/hash, placements, transitive scientific and
literature/input closure and deterministic current VALID status in the same UoW.
Use `ManuscriptFreezeService.verify_in_uow(..., admission=True)` for new gates;
use historical verification for reads. No authority or matching digest can waive
invalid facts. A missing seal/current invalidity is APPROVAL_TARGET_STALE; corrupt
saved provenance is PROVENANCE_CLOSURE_VIOLATION.

The basis must be a prior committed B11 READY_FOR_SUBMISSION/PROCEED Decision in
that Project, with exactly this manuscript/hash and no other target shape or
supersession. Reconstruct its unchanged basis/content hashes and historical
attribution. The request's review IDs equal its entire saved manuscript-review
basis, not a caller-selected subset. B11 creation already collects all matching
reviews; approvals do not rewrite that saved set when later reviews arrive.

Validate every currently committed exact-manuscript review, including later and
adverse reviews: matching target/hash, saved hash, historical HUMAN REVIEWER/OWNER
and independence from `material_authors(target, manuscript=True)`. ACCEPT,
MINOR_REVISION, MAJOR_REVISION, REJECT and UNCERTAIN remain evidence, not votes.
Do not require equality between today's review set and the historical Decision
set, silently refresh basis, filter unfavorable reviews or truncate to a limit.

Use B11 `_readiness_blockers` / SQL `b11_applicable_reviews` for exact manuscript
and reachable ClaimVersion, ScientificConclusionVersion and ArtifactVersion
(including document) Issue scope. Verify B08 event/disposition history; any OPEN
BLOCKING Issue denies. Nonblocking OPEN Issues remain visible. Another version,
identity-wide navigation or related-source text does not enlarge this finite
scope. No implicit manuscript Issue disposition is introduced.

Requester has current OWNER/RESEARCHER and differs from every required saved
reviewer. Basis decider has B11's historical OWNER/APPROVER authority and is
independent of every traversed material author; reviewer/decider overlap remains
permitted by B11; its decider may be HUMAN or AGENT. Requesters use the same
Application boundary for either actor kind. Approver has current HUMAN APPROVER authority and differs from
requester, basis decider, every required reviewer and every material contributor.
OWNER alone, accumulated roles and `acting_on_behalf_of` cannot satisfy this.
Later reviewers retain B12's validation policy; they are not silently appended to
the required reviewer set or the Decision hash.

Preserve the B09/B10 rejection fence across the whole `(project_id, purpose)`,
including older PENDING requests and other manuscript/Publication identities.
Any READY rejection blocks further new READY requests/decisions until a separately
contracted reconsideration path exists. Both successor-link fields must be null
here. A PREPARE/release rejection belongs to a different fence. Newer target
selection and issuer authority loss retain existing atomic staleness/events;
terminal grants never reactivate.

## 4. Proposed commands, DTOs and historical readback

Use the existing immutable closed dataclasses in application/approval.py; §11.3
pins READY inputs. Trusted VerifiedPrincipal is separate. Actors, timestamps,
target hashes, statuses, grant IDs and allowed command are server-derived.

| Method | READY behavior |
| --- | --- |
| `request_approval` | Create PENDING request, exact saved review relations and initial request event; no grant. |
| `decide_approval` | Require still-PENDING and revalidate §3 for every outcome; insert one immutable ApprovalDecision and PENDING→DECIDED event. APPROVE/APPROVE_WITH_CONDITIONS atomically create one ACTIVE grant/event; REJECT creates none and stales affected unused READY grants. |
| Three exact-ID reads | Return existing typed request/decision/grant readbacks under current project read entitlement, verifying immutable history; no lifecycle mutation. |

Readers have current verified OWNER/RESEARCHER/REVIEWER/VIEWER/APPROVER entitlement;
check it before existence/conflict disclosure and separately before nested source
information. Exact same-UUID replay additionally requires original actor and
normalized caller material. Changed material is IDEMPOTENCY_CONFLICT; different
actor/project is nondisclosing FORBIDDEN. Saved history remains readable after
write-role loss, later reviews/blockers, expiry or stage changes. Do not rerun
new-write admission to return history. Corrupt saved hashes/bindings still deny.

Retain current grant evaluation separately from immutable history. The present
`_evaluate_in_uow` treats all manuscript dependencies as unavailable. This slice
must not globally enable manuscript usability or infer consumption support from
issuance. Preserve `usable=false` / APPROVAL_GATE_FAILED while the owning B14
consumer is unavailable; document that reason. B14 separately enables its READY
consumption/evaluation integration. No PREPARE evaluator or generic consume path
is enabled by B14r. Reads/replay never persist proposed terminal status.

## 5. Schema and literal hash proposal — no new table; one forward guard migration

The forward guard migration adds `b14r_saved_decision` and `b14r_approval_gate`
and replaces `pr216_gate` and `pr216_complete` to enable READY approval dispatch
and transactional final-gate rechecks (§12.1).

Reuse `approval_requests`, `approval_request_reviews`, `approval_decisions`,
`approval_grants`, `approval_request_events`, `approval_grant_events`,
`decision_records`, `decision_basis_manuscripts` and `decision_basis_reviews`.
Grant target/hash/max_uses are projections through immutable Decision→Request,
not new grant columns or JSON scope. Existing `approval_decisions_approval_request_id_key` and
`approval_grants_approval_decision_id_key` enforce one decision per request and
one grant per approving decision.

ApprovalDecision uses unchanged `approval_decision_material`, material_version=1,
sha256-cjson-v1 and target type ManuscriptVersion. B11 Decision hashes and
canonical `(type, UUID text, digest)` basis order stay unchanged. No stage, clock,
evaluation, purpose or command key is added to a hash. Issue events are verified
history, not a new signed Issue-state snapshot.

## 6. Error contract — proposed use of existing categories

§11.2 pins existing codes and transport mappings; add no ErrorCode. Normalize
PostgreSQL named constraints/SQLSTATE through the existing UoW boundary. SQL can
verify structural provenance/roles/hashes; Application additionally verifies
credential validity, artifact bytes and deterministic closure. Never leak SQL,
credentials, artifact paths or protected foreign-project existence.

## 7. Transactions, concurrency and failure recovery

One new request or approval decision equals one synchronous READ COMMITTED UoW;
no nested command transaction or network effect. §12.2 defines the exact order.
The §12.2 table locks stabilize mutable validity, authority and INSERT phantoms;
scope advisory locking serializes rejection and newer-target selection. Acquire
final lock modes directly. The shared ApprovalService prefix in §12.2 is mandatory;
never narrow it to direct manuscript inputs.

Use `clock_timestamp()` after each wait, reread relevant rows in a new READ
COMMITTED statement, force `SET CONSTRAINTS ALL IMMEDIATE`, then final credential,
role, gate and expiry checks before commit. Any later wait requires another
check. When rechecking a newly inserted REJECT, exclude only that exact
current-transaction decision from the prior-rejection query; otherwise the
command would block its own rejection. Every other rejection, including another
one in the same transaction, remains a fence. Mirror the existing b10_successor_check own-request/current-transaction
exclusion in Application final checks; retain its xid-safe installed SQL form.
Scheduled credential/role expiry still denies while SHARE locks block
revocation writes. Connection configuration bounds the first lock wait before
BEGIN; a transactional SELECT/SET must not precede the first SHARE statement.

Completed replay uses the lock-free snapshot read path. A racing duplicate found
inside a locking writer closes that UoW and reopens a fresh historical snapshot;
it never returns history from the write gate. Retry only SQLSTATE 40001/40P01,
exactly three total fresh-UoW attempts with no delay; redo all checks. Do not retry
business conflicts, uniqueness loss, timeouts or uncertain commit blindly.
Recover uncertain commit by the same UUID. Any failed gate/deferred check rolls
back all request/decision/grant/review/event writes. Older target-first writers
can deadlock with SHARE-first writers; bounded recovery does not prove otherwise.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

§12.4 fixes files/cases: successful real entry→B11 basis→request→approval,
substitutions and independence, direct SQL/final-graph enforcement, historical
reads/replay and two-backend wait/expiry/rollback races. No test may force
INTERNAL_REVIEW/READY, disable guards or fabricate a grant to claim acceptance.

## 9. Acceptance criteria and evidence boundary

Require owner approval of §11 and separate implementation authorization. Run
static, unit, architecture and affected real PostgreSQL 18.x checks, report exact
commands/counts/version and resolve all P0/P1 findings. The owner's loop owns the
whole-suite run. Request/decision/grant issuance acceptance does not imply B14
consumption, preparation, consent, external submission or Phase 2 completion.

## 10. Glossary

| Term | Meaning here |
| --- | --- |
| B11 Decision | Immutable READY_FOR_SUBMISSION/PROCEED judgment and exact saved manuscript/review basis. |
| ApprovalDecision | Separate independent HUMAN authorization or rejection of a PENDING request. |
| READY tuple | Project + READY purpose + exact manuscript FK/hash + `transition_publication_ready` + finite expiry + max_uses=1. |
| B | Full fixed B09/B12 snapshot table inventory in §12.2. |
| Required reviews | Complete saved B11 review basis copied into request relations; later reviews are revalidation inputs. |
| Material authors | Existing B11 transitive authors/contributors traversal, not a new authorship snapshot. |
| Fresh clock | Advancing PostgreSQL clock_timestamp(), including checks after blocking waits. |
| History / usability | Immutable records versus timestamped present permission evaluation; neither changes scientific truth. |

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

| Decision | Adopted proposal |
| --- | --- |
| Smallest slice | Existing request + approval decision + atomic grant issuance and exact reads; no new command family. |
| Sole tuple | READY_FOR_SUBMISSION → FROZEN, VALID ManuscriptVersion in INTERNAL_REVIEW → `transition_publication_ready`; B11 READY/PROCEED required. |
| Required basis | Entire saved B11 review set, 1..100 for approval; B11 allows up to 10,000. Over 100 fails without truncation or replacing the Decision. |
| Conditions | APPROVE defaults to exactly decided_at + 720 hours; conditional expiry is finite, strictly future and at most 720 hours. READY consent flag is always false. |
| Independence/blockers | §3, exactly B09/B12 policy applied to READY; all matching reviews verified, exact upstream blockers checked. |
| Reconsideration | Null successor links only; existing READY rejection blocks new gate actions. No B10 manuscript extension. |
| Persistence and concurrency | No table/column/index/hash change; forward function amendment, existing deferred final-graph guards and B-first READ COMMITTED writes. |
| Adapters | No new API/CLI routes; mappings below pin existing compatibility. |

### 11.2 Pinned error mappings

Matches [HTTP errors](../../src/researchbase/api/errors.py) `_STATUS` and
[CLI errors](../../src/researchbase/cli/errors.py) `CLI_EXIT_CODES`.

| ErrorCode | Use | HTTP | CLI exit |
| --- | --- | ---: | ---: |
| VALIDATION_ERROR | Closed DTO/type/bounds/READY consent or malformed successor inputs | 422 | 2 |
| AUTHENTICATION_REQUIRED | No VerifiedPrincipal | 401 | 3 |
| FORBIDDEN | No current entitlement, HUMAN APPROVER absent, foreign scope/actor | 403 | 3 |
| NOT_FOUND | Authorized exact record absent | 404 | 3 |
| CONFLICT_OF_INTEREST | Requester/reviewer, approver/decider/author overlap | 403 | 3 |
| APPROVAL_PURPOSE_TARGET_COMMAND_INVALID | Unlisted or substituted finite tuple | 409 | 4 |
| DECISION_BASIS_INVALID | Missing, wrong-purpose, wrong-target or uncommitted basis/review set | 409 | 4 |
| APPROVAL_GATE_FAILED | Stage/project/blocker or unavailable consumer dependency | 409 | 4 |
| APPROVAL_TARGET_STALE | Unsealed, invalid, replaced or newer selected target | 409 | 4 |
| REJECTION_RECONSIDERATION_REQUIRED | Project/READY rejection fence | 409 | 4 |
| IDEMPOTENCY_CONFLICT | Changed UUID replay, terminal request, duplicate PENDING scope | 409 | 4 |
| IMMUTABLE_RECORD | History mutation or late child insertion | 409 | 4 |
| CONCURRENT_MODIFICATION | Exhausted 40001/40P01; lock/statement timeout | 409 | 4 |
| FROZEN_REFERENCE_REQUIRED | Propagated exact frozen dependency failure | 409 | 5 |
| PROVENANCE_CLOSURE_VIOLATION | Corrupt saved hashes, attribution, closure or event history | 409 | 5 |
| REFERENTIAL_INTEGRITY_ERROR | Concrete FK violation | 409 | 5 |
| GRANT_INVALID | Expired/terminal grant diagnostic | 409 | 4 |
| GRANT_STALE | Current issuer authority/staleness diagnostic | 409 | 4 |

Retain P16P1→tuple, P16B1→basis, P16G1→gate, P16T1→target,
P16R1→reconsideration, P16C1→COI, P16A1→FORBIDDEN, P17F1→immutable,
P17F2→provenance and P17F3→idempotency mappings. Do not collapse business denials
into retries. Unexpected transport fallback remains HTTP 500 / CLI 1,
INTERNAL_ERROR, sanitized. No new transport surface is introduced.

### 11.3 DTO fields, Python types and limits

No subclass or alternate JSON DTO. Reuse the named frozen dataclasses (§4).
Reject extra fields; UUIDs require `type(x) is UUID`. UUID lock/hash text uses
canonical lowercase hyphenated form. No caller actor/time/hash/status assertions.

| DTO / fields | READY contract |
| --- | --- |
| RequestApprovalCommand: `id`, `project_id`, `basis_decision_id` | Required UUID; id is replay identity. |
| `scientific_conclusion_version_id`, `manuscript_version_id` | Respectively None and required UUID (keyword-only manuscript); exactly one concrete target. |
| `approval_purpose` | str exactly READY_FOR_SUBMISSION; generic DTO's release default is not inferred to mean READY. |
| `review_ids` | tuple[UUID, ...], distinct, nonempty, 1..100 at Application admission; normalized UUID-text order. Must equal saved B11 basis. |
| `prior_rejected_request_id`, `reconsideration_decision_id` | Existing UUID \| None fields; READY accepts None only. Malformed pair/types are validation errors; a valid-looking unsupported manuscript successor is DECISION_BASIS_INVALID, never a fence bypass. |
| DecideApprovalCommand: `id`, `project_id`, `approval_request_id` | Required UUIDs; exact existing request. |
| `decision` | str enum APPROVE, APPROVE_WITH_CONDITIONS, REJECT. |
| `rationale` | str, NFC, valid UTF-8, nonblank, no NUL, 1..16,384 characters after normalization; meaningful whitespace retained. |
| `valid_until` | datetime \| None; timezone-aware, normalize UTC. Required finite future time only for APPROVE_WITH_CONDITIONS; otherwise None. At decision DB time: now < expiry ≤ now + 720 hours. Recheck expiry after waits. |
| `requires_current_author_consent` | strict bool, default false; READY requires false even for conditional approval. No readiness consent subsystem. |
| Three exact reads | Required project UUID and request/decision/grant UUID, separate trusted principal. |

Return existing ApprovalRequestReadback, ApprovalDecisionReadback and
ApprovalGrantReadback field types (§4 and application/approval.py): UUID identities,
nullable conclusion/manuscript UUID XOR, str digests/scheme/purpose, UTC datetime
accounting, tuple[DecisionBasisReference, ...] reviews, tuple[UUID, ...] event IDs;
Decision has nullable datetime expiry, bool consent and optional grant. Grant
has Literal[1] max_uses, nonnull datetime expiry, bool usable, str | None
unusable_code and datetime evaluated_at. Request status vocabulary remains
PENDING/DECIDED/WITHDRAWN (no withdrawal command here); grants remain
ACTIVE/CONSUMED/EXPIRED/REVOKED/STALE, with no terminal→ACTIVE transition.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

No CREATE TABLE, ADD COLUMN or new index. Choose a forward migration after the
actual accepted head; never edit 0054/0055/0058/0059/0060. Retain existing column
types: request IDs/targets/basis UUID, target_content_hash CHAR(64), scheme/purpose/
status TEXT, requested_at TIMESTAMPTZ; approval decision valid_until TIMESTAMPTZ,
consent BOOLEAN, content_hash CHAR(64); grant scope TEXT, valid_until TIMESTAMPTZ.
All existing concrete FKs stay ON DELETE RESTRICT.

DDL shape (function bodies implement §§3, 7; this is not executable migration SQL):

```sql
CREATE FUNCTION b14r_saved_decision(did UUID, tid UUID, pid UUID) RETURNS void
  LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$ ... $$;
CREATE FUNCTION b14r_approval_gate(r approval_requests, approver UUID) RETURNS void
  LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$ ... $$;
CREATE OR REPLACE FUNCTION pr216_gate(r approval_requests, approver UUID)
  RETURNS void LANGUAGE plpgsql
  SET search_path=pg_catalog,public,pg_temp AS $$ ... $$;
CREATE OR REPLACE FUNCTION pr216_complete() RETURNS trigger
  LANGUAGE plpgsql SET search_path=pg_catalog,public,pg_temp AS $$ ... $$;
```

| Object | Exact amendment / preserved obligation |
| --- | --- |
| `b14r_saved_decision(UUID,UUID,UUID)` | B12 saved verifier analogue with READY_FOR_SUBMISSION/PROCEED, exactly one manuscript and nonempty saved reviews, no other basis/supersession; project/target/hash equality, historical independent decider/reviewers, review times ≤ Decision time, literal canonical basis/content hashes. Does not require today's complete review set or stage. Never call creation-only b11_complete on old Decisions. |
| `b14r_approval_gate(approval_requests,UUID)` | B12 gate analogue, INTERNAL_REVIEW instead of READY; selected frozen target/seal/project, prior committed B11 Decision, B14a history, all later review verification, b11_applicable_reviews + b08_check_history blockers, requester/approver independence, fresh authority, newer-target and project/purpose rejection checks. Reuse b04_verify_structure; Application still verifies bytes/current validity. Reject nonnull READY successor links. |
| `pr216_gate` | Keep b09_preheld, exact tuple validation, scope advisory and manuscript/Publication lock sequence. Dispatch READY to b14r_approval_gate; PREPARE still b12_approval_gate; release branch unchanged. |
| `ck_b09_request_tuple`, `ck_b09_grant_tuple`, `ck_b09_consent_condition` | Already admit READY/manuscript/transition command and typed conditional policy. Retain definitions; READY consent=false also enforced in existing decision guard. |
| `uq_b09_pending_manuscript`, `uq_b09_pending_conclusion` and existing request/decision/grant unique keys | Preserve one PENDING exact target/purpose and one decision/request, one grant/decision. These replaced uq_pr216_pending in 0055. |
| `pr216_request_guard`, `pr216_decision_guard`, `pr216_grant_guard` | Retain triggers, committed-basis checks, exact tuple projection, finite expiry, automatic events, immutable scope and current-transaction sealing. Newly enabled READY must pass dispatch at request/decision INSERT; grant INSERT must resolve that same-transaction approving decision with exact scope/expiry. Deferred completeness must deny partial issuance, including normal-role SQL. Preserve 0057's xid-safe comparisons and 0059 lifecycle branches. |
| `pr216_complete` and `pr216_complete_request`, `pr216_complete_reviews`, `pr216_complete_decision`, `pr216_complete_grant` | Retain DEFERRABLE INITIALLY DEFERRED final-graph checks: bidirectional saved-review equality, status/decision coherence, approving outcome iff one grant, exact events, final role/expiry checks. Add READY gate recheck only for creation/decision rows belonging to this transaction, after waits; never re-admit historical rows on later lifecycle operations. Use the 0042 deferred-final-graph pattern. |

Preserve B13 `b13_complete_grant`, consumption and terminal-history guards.
Do not add a second completeness/event store. Lock affected approval tables in
lexical order ACCESS EXCLUSIVE during migration function replacement. Upgrade
preserves all history. Downgrade takes the same exclusion, refuses if any READY
approval request/decision/grant history exists (P17F1), otherwise restores exact
predecessor functions and drops only the two new functions. No history deletion.
Tests must compare full predecessor catalog definitions, not just object counts.

### 12.2 Exact lock order and transactions

B is **exactly** the 46-entry literal `B09_SNAPSHOT_TABLES` in
`src/researchbase/persistence/approval_repository.py`, identical to
`B12_SNAPSHOT_TABLES` in migration 0058. It is already lexical, includes
publications and mutable authority/validity/review/Issue/placement/input tables,
and excludes approval output tables. Freeze that inspected list in the forward
migration/tests; no runtime-discovered inventory or narrowed N. B14a entry uses
its own write protocol; B14r never writes publications.

For both writers: configure a new READ COMMITTED UoW/connection before BEGIN,
autoflush disabled. `request_approval` keeps the B09 prefix: FIRST transactional
SQL is `LOCK TABLE <B in literal lexical order> IN SHARE MODE`, as B16 permits.

`decide_approval` uses the single unconditional prefix ApprovalService uses on the
branch at implementation time, for ALL purposes: the B09 prefix today; once B16
lands, FIRST SQL is `LOCK TABLE <B without publications in literal lexical order>
IN SHARE MODE`, followed by `LOCK TABLE publications IN SHARE ROW EXCLUSIVE MODE`.
Choose this prefix unconditionally before any purpose lookup. B14r must not
introduce a READY-specific prefix or upgrade publications from SHARE to SRE.
This follows the owner-approved 2026-10-18 B16 contract (§§12.2, 13).

No SELECT, SET LOCAL, authorization or advisory lock may precede the applicable
prefix. Then SET LOCAL lock_timeout='10s' and statement_timeout='30s'.
`b09_preheld()` must recognize the applicable shared prefix and READ COMMITTED
isolation: B in SHARE for requests and pre-B16 decisions; after B16, B without
publications in SHARE plus publications in SHARE ROW EXCLUSIVE for decisions.
Whichever of B14r/B16 lands second adds a READY `decide_approval` case to B16's
phantom/ordering tests, proving the unconditional prefix and publication INSERT
phantom exclusion.

| Command | Subsequent exact order after the applicable prefix and timeouts |
| --- | --- |
| request_approval (READY) | Request advisory `pg_advisory_xact_lock(hashtextextended(:key,0))`, key `pr216:uuid:<request UUID>`; scope advisory `pr216:scope:<project UUID>:READY_FOR_SUBMISSION`; exact manuscript FOR UPDATE; owning Publication FOR SHARE; current read authorization with plain SELECT/fresh clock; duplicate branches reopen snapshot replay; new writer OWNER/RESEARCHER authorization; plain reads of saved Decision/basis/reviews, target/entry/history/closure and all applicable Issues in UUID order; check pending/fence/independence; ACTIVE other-target same-project/READY grants FOR UPDATE by grant UUID via lock_affected_grants(reject=False); reread/recheck gates and fresh authority; insert request then UUID-sorted review links (trigger appends initial event and stales affected grants/events); force constraints; final fresh gate/credential/role check; commit. |
| decide_approval (READY) | Request advisory `pr216:uuid:<approval decision UUID>`; plain routing read of exact request; scope advisory `pr216:scope:<project UUID>:READY_FOR_SUBMISSION`; manuscript FOR UPDATE; Publication FOR SHARE; saved request FOR UPDATE; reread request after wait; current read authorization; duplicate branch reopens snapshot replay; HUMAN APPROVER/new-write authorization; plain basis/closure/review/Issue reads and all gates; affected ACTIVE grants FOR UPDATE by UUID (all same-project/READY for REJECT, other targets for approve, existing lock_affected_grants); reread/recheck and fresh clock; insert immutable ApprovalDecision; triggers update request/event; Application inserts one grant for approving outcomes and its trigger appends the grant event; REJECT stales affected grants/events; force constraints; final fresh authorization/gate and conditional expiry check; commit. |
| get_approval_request / get_approval_decision / get_approval_grant; completed UUID replay | Configure REPEATABLE READ, READ ONLY before first query; current read entitlement; exact parent, saved typed relations, target/reviews/history and separate current diagnostics with plain SELECT in one snapshot; verify hashes and normalized replay/actor; final advancing-clock read entitlement; return without writes. No explicit table, advisory or row locks anywhere, including nested helpers. |

Authorization uses `revision_action.authorize` and the existing protected-read
adapters; it does not add project FOR SHARE. Decision, basis, review and Issue
rows are plain reads protected by B/immutability; no hidden collector row locks.
Trigger reacquisition of already held scope/target locks changes no order. Actor
FK/key-share or deferred-trigger waits are still waits: §7 final checks apply.
Lock-free snapshots promise entitlement in that snapshot plus advancing-clock
expiry, not exclusion of revocations committed after snapshot start.

### 12.3 Ordered build steps and module paths

1. Reconcile head and dependencies; add only the authorized forward migration
   under `migrations/versions/` with §12.1 functions/guards and exact downgrade.
2. Extend `src/researchbase/application/approval.py` `_manuscript_gate` to dispatch
   READY to DecisionService._readiness_readback and PREPARE to its current verifier.
   Make manuscript basis/gate dispatch purpose-specific: reuse B12 logic with
   READY's stage and B11 target verifier. Keep saved verification separate from
   admission; do not change B11 creation or PREPARE policy.
3. Reuse `src/researchbase/domain/approval.py` tuples/material builder and existing
   DTOs. Extend typed ports only where necessary in
   `src/researchbase/application/ports.py`; implement plain history/entry reads in
   `src/researchbase/persistence/approval_repository.py` and existing
   `src/researchbase/persistence/publication_repository.py`. Use §12.2's shared
   lock_snapshot prefix; keep subsequent lock_request/scope/target/saved_request/
   affected_grants order unchanged.
4. Reuse protected reads/normalization in `src/researchbase/persistence/uow.py`;
   any shared helper changes in `src/researchbase/application/decision.py`,
   `src/researchbase/application/internal_review.py` and their repositories must
   be additive and tested against B11/B12. Retain generic manuscript dependency
   unavailability until B14 supplies the owning consumer. No adapter/dependency
   or composition change is required for the existing ApprovalService.
5. Add §12.4 tests, inspect specs + diff + executed evidence for P0/P1, run focused
   regressions and stop. Never implement B14 to make an issuance test pass.

### 12.4 Test artifacts and required cases

Use disposable PostgreSQL 18.x `phase2_database_url`, normal-role SQL and existing
exported B04/B05/B11/B14a fixture builders. Successful setup uses actual freeze,
entry, review and Decision Application commands; no disabled triggers or forced
lifecycle state. Race tests need separate backend PIDs and observed
pg_blocking_pids/pg_locks witnesses, not sleep-only assertions.

| File to add | Required cases |
| --- | --- |
| `tests/unit/phase2/test_b14r_ready_approval_contract.py` | Existing DTO types/defaults/closed inputs, UUID and tuple strictness, duplicate/sorted sets, 100/101 boundary without truncation, 16,384 text boundary/NFC/invalid UTF-8/NUL, aware finite expiry and 720-hour bound, READY consent=false/successor denial, enums and every §11.2 mapping. |
| `tests/integration/phase2/test_b14r_ready_approval.py` | Real B14a entry + B11 basis + request; APPROVE and conditional finite APPROVE issue one ACTIVE exact READY grant; REJECT issues none; all event/scope/hash fields; DRAFTING denial then real-entry success with same prior B11 basis; wrong project/manuscript/hash/purpose/PROCEED, PREPARE/release substitution, missing/extra/uncommitted reviews/Decision; saved 101-review basis denied. Full CAS/closure/validity corruption, later adverse review validation, exact direct/upstream blockers and B08 history; all actor-role/author/reviewer/decider overlaps. No publication, receipt, consent or package writes. |
| `tests/integration/phase2/test_b14r_ready_approval_replay.py` | Exact request/decision replay/restart, changed material/different actor/project denial, pending/terminal collisions; history after authority/write-role loss, new blockers/reviews, expiry and grant terminal states; corrupt saved provenance denial. Query trace/backend lock inspection proves no exclusion locks in exact reads/replay or nested helpers; reads append no stale events. Consumer-unavailable grant diagnostic remains explicit. |
| `tests/integration/phase2/test_b14r_ready_approval_schema.py` | Clean install/populated upgrade, catalog types/names/constraints/triggers unchanged except approved functions; empty downgrade exact catalog roundtrip; populated READY downgrade refusal unchanged history. Direct SQL without B or wrong isolation; wrong tuple/basis/conditions/hash, mixed/late/missing review children, parent-only/decision-without-grant/REJECT-with-grant/event forgery; deferred force failures atomically roll back. Preserve xid-wraparound comparisons. |
| `tests/integration/phase2/test_b14r_ready_approval_races.py` | Same UUID and two decisions/request single winners; successful REJECT final recheck does not self-fence, while all other rejections still fence; both orderings of rejection vs request/old pending decision, other-project/purpose isolation, newer target vs grant; review INSERT and zero-Issue/upstream BLOCKING INSERT phantoms; credential/binding/membership/validity changes; actual first-SQL and target/request/grant/FK/deferred waits crossing credential/role/conditional expiry. Final checks deny zero partial history; 40001/40P01 exactly three fresh attempts, no retry on business/unique/timeout; mid-write failure and uncertain-commit same-UUID recovery. Include B14a/B11/B12/B13 writer coordination; no B14 effect test here. |
| `tests/architecture/test_b14r_ready_approval_boundaries.py` | Shared Application boundary, pure Domain, B SHARE first, no hidden read locks, no new schema/JSON owner/hash version, no lifecycle/consumption/ExternalEffect writes, distinct B11 Decision and ApprovalDecision. |

Update existing `test_b12_prepare_approval.py` READY expectations: a valid B11
basis on DRAFTING now fails APPROVAL_GATE_FAILED for stage, not the removed
unavailable-basis branch. Keep PREPARE basis substitution denial. Update migration
head/catalog inventories only in the later authorized implementation.

Future focused command after implementation:
`uv run pytest tests/unit/phase2/test_b14r_*.py tests/integration/phase2/test_b14r_*.py tests/architecture/test_b14r_ready_approval_boundaries.py`.
Then static/unit/architecture plus B09/B11/B12/B14a/Basic Approval, B04/B05/B08,
PR2-15 Decision and B13 regressions for shared guards/helpers. Tests above do not
exist yet; §14 reports this documentation task's actual baseline checks.

### 12.5 Not in this slice

B14 READY transition, consumption/receipt/evaluator integration; B13 lifecycle
commands or new terminalization mechanisms; B11/B12 Decision creation changes;
PREPARE gate expansion, authorship/consent/package preparation/freezing; manuscript
reconsideration/Issue disposition; automatic propagation, new schema or hashes;
API/CLI endpoints; venue submission, ExternalEffect, Agent runtime, queues,
new dependencies or architecture freeze/Phase-exit acceptance.

## 13. Open questions for the owner — override register

| Owner may override | Adopted proposal |
| --- | --- |
| Stage and basis | INTERNAL_REVIEW only, B11 READY/PROCEED only, exact frozen selected manuscript. |
| Slice and limits | Request + decide + grant only; existing 100-review approval ceiling and 16,384-character rationale, no truncation. |
| Conditions/reconsideration | Finite expiry only, READY consent=false; no manuscript reconsideration. |
| B16 lock compatibility | Shared unconditional ApprovalService decision prefix for all purposes (§12.2); request keeps B09. Whichever lands second adds READY decide_approval to B16 phantom/ordering tests. |
| Consumption dependency | Issuance can be accepted independently; existing read diagnostic reports consumer unavailable until B14 integration. |

These choices are fixed in this draft. An override needs a recorded disposition
and matching body/guard/test edits before approval. No implementation is authorized.

## 14. Documentation verification note

Only this proposal is changed. Checks below exercise the current baseline, not
proposed B14r commands or guards. The whole-suite run belongs to the owner's loop.

Executed 2026-10-18. All uv commands used this exact environment prefix to reuse
installed dependencies without changing dependency sources or creating a local
environment (the repository has no `.venv`):

```sh
UV_CACHE_DIR=/private/tmp/b14r-uv-cache UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv
```

| Exact command after that prefix | Observed result |
| --- | --- |
| `uv run --no-sync ruff check .` | All checks passed; exit 0. |
| `uv run --no-sync ruff format --check .` | 646 files already formatted; exit 0. |
| `uv run --no-sync pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject` | 0 errors, 0 warnings, 0 informations; exit 0. |
| `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 uv run --no-sync pytest tests/unit tests/architecture tests/test_architecture.py --tb=short > /private/tmp/b14r-unit-architecture.log 2>&1` | 5,180 cases: 5,164 passed, 4 failed, 12 errors, 8 warnings in 66.32s; exit 1. |
| `PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run --no-sync pytest tests/integration/phase2/test_b09_*.py tests/integration/phase2/test_b11_*.py tests/integration/phase2/test_b12_*.py tests/integration/phase2/test_b14a_*.py tests/integration/phase2/test_approval.py --tb=short > /private/tmp/b14r-postgresql.log 2>&1` | 360 cases: 1 passed, 2 failed, 357 errors in 42.89s; exit 1. |

The four unit failures are Runner AF_UNIX `bind` PermissionError in
`tests/unit/test_hg1_runner.py`. Twelve architecture fixture errors require an
explicit RB_TEST_ADMIN_URL absent from that run. The focused PostgreSQL run used
the README's explicit local development selectors; localhost IPv4/IPv6 port 5432
connections fail with “Operation not permitted.” Its two B14a catalog roundtrip
failures and 357 setup errors could not exercise PostgreSQL behavior. No server
version, database PASS or successful B14r gate is claimed. No guards, assertions,
server settings or dependency definitions were changed to bypass these limits.

Additional documentation checks:

| Exact command | Observed result |
| --- | --- |
| `python3 /private/tmp/b14r-check-doc.py` | PASS: 28 local links, 14 numbered sections, 18 HTTP/CLI mappings checked against source AST, required status and whitespace. |
| `git diff --check` | Exit 0; no output. The document script separately checks new-file whitespace. |
| `git status --short` | Only `?? docs/proposals/B14r_Ready_Approval_Gate_Contract_DRAFT.md`. |

No whole-suite run, implementation, commit, push or branch creation was performed.
