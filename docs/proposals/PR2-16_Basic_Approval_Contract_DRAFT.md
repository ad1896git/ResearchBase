# PR2-16 Basic Approval Command Contract — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

**Scope:** documentation proposal only. This is not an architecture freeze, ADR,
execution pack, migration authorization, scientific approval or PR2-16 acceptance.
Proposed choices require owner approval and contract consistency review, followed
by separate engineering authorization. Existing authoritative contracts prevail.

## 1. Purpose, hierarchy and inspected baseline

Basic Approval records a request to authorize an exact frozen scientific target,
one attributable approval decision, and a narrowly scoped grant for a later
Application command. It answers “who authorized which future action, on which
exact material and evidence?” Grant creation does not perform that action.

| Authority | Constraint carried into this proposal |
| --- | --- |
| [System Architecture 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 7–9, 22–26, 37 | Deterministic facts precede authority; immutable history; frozen provenance; Review != Decision != Approval != Command != ExternalEffect. |
| [Correction Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A3–A5, A10, A12, A18–A23 | Concrete formal FKs; R2 precedence; fresh post-lock authorization; historical replay read entitlement; bounded minimal Decision purpose. |
| [Global Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), §§3, 7–12 | Governance owns request/decision/grant and their history; canonical collections use relations; no new canonical identity or generic JSON core. |
| [Cross-Phase Contracts 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§9, 12–18, 27–28 | Stable boundaries/errors, additive compatibility, historical approvals survive later authority-engine expansion; prepared package != external send. |
| [Phase 2 Specification 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §§19–22, 38, 41.9, 43, PR2-14/15/16 | Request/decision/grant, frozen target and blocking review gate; review/revision trace and invalid-fact denial. |
| [Phase 2 Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), §§1–2, 6–7 | HUMAN approver, independence, exact target and basis, one transaction per command; approval cannot create external effects. |
| [Field Contract 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md), approval rows; [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md), “Review, decision, approval, and revision”; [Governance R2 17](../architecture/17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md), §§1–2, 4 | Finite purpose/target/command policy, typed conditions, 30-day expiry, rejection reconsideration and completed revision semantics supersede older generic examples. |
| [R3 18](../architecture/18_Phase2_Design_R3_Targeted_Remediation_v1.0.md), grant receipts; [Temporal R4 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md), TEMP-AUTH-01 | Completed consumption receipt replay is historical read, not renewed execution; final expiry checks use advancing DB time after waits. |
| [Minimal Decision Contract 20](../architecture/20_PR2_15_Minimal_Decision_Command_Contract_v1.0.md), §§1–7 | Only INTERNAL_SCIENTIFIC_RELEASE/PROCEED; complete saved review basis, no replacement, independent later approval gates; Issue-disposition cycle remains open. |

The inspected [InternalReviewService](../../src/researchbase/application/internal_review.py)
creates immutable ClaimVersion/conclusion reviews and initial OPEN issues; it
does not resolve issues or review manuscripts. [DecisionService](../../src/researchbase/application/decision.py),
[decision material](../../src/researchbase/domain/decision.py) and
[Decision repository](../../src/researchbase/persistence/decision_repository.py)
implement the minimal exact-conclusion PROCEED command, complete review basis,
UUID replay and no replacement. Its coordination uses request advisory locks,
exact conclusion FOR UPDATE and a sorted SHARE-table snapshot inventory.
[0040](../../migrations/versions/0040_pr2_14_initial_internal_review.py),
[0041](../../migrations/versions/0041_pr2_15_review_coordination.py) and
[0042](../../migrations/versions/0042_pr2_15_minimal_decision.py) are existing
baseline evidence, not files to edit. No Basic Approval command/schema is supplied
by these components. Source presence is not formal milestone acceptance.

## 2. Proposed scope and non-goals

Propose a first slice with `request_approval`, `decide_approval` and authorized
exact-ID read queries, restricted to INTERNAL_SCIENTIFIC_RELEASE. The full R2
design remains the compatibility ceiling:

| Purpose | Exact target and required state | Sole future consuming command | First-slice availability |
| --- | --- | --- | --- |
| INTERNAL_SCIENTIFIC_RELEASE | Same-project FROZEN, currently VALID ScientificConclusionVersion | `record_internal_scientific_release` | Request/decision/grant proposed here; effect command separately contracted. |
| READY_FOR_SUBMISSION | Same-project FROZEN, currently VALID ManuscriptVersion; Publication INTERNAL_REVIEW | `transition_publication_ready` | Deferred: manuscript reviews and this Decision purpose are not implemented/contracted by minimal PR2-15. |
| PREPARE_SUBMISSION | Same-project FROZEN, currently VALID ManuscriptVersion; Publication READY | `freeze_prepared_submission` | Deferred: distinct Decision purpose, package/authorship/consent contracts required. |

All unlisted tuples fail closed. Deferred tuples remain unavailable rather than
being mapped to PROCEED, another target or another grant. This proposed narrower
slice is not a claim that all PR2-16 or Phase 2 acceptance is satisfied.

Excluded from this slice: grant consumption/release, publication transitions,
prepared packages, venue submission, ExternalEffect, RevisionAction creation,
Issue ADDRESSED/DISMISSED, reconsideration Decisions, other Decision purposes,
full Authority/Delegation/COI/Appeal engine, Agent Runtime, queues or new runtime
dependencies. Request withdrawal and explicit grant revocation require separate
lifecycle command definitions before implementation; their states are retained
in the compatibility proposal below. No migration, code, tests or authoritative
architecture changes are authorized by this draft.

## 3. Domain invariants, blocking gate and revision trace

1. **Immutable material.** Request target, hash, purpose, requester, basis and
   request time never change. Request status is a lifecycle projection with
   append-only events. ApprovalDecision is an immutable record, not a Version.
   Grant scope cannot broaden or retarget; only monotonic lifecycle transitions
   are permitted. Correction preserves original records and explicit provenance.
2. **Semantic separation.** Review evaluates; Decision chooses; Approval
   authorizes. PROCEED, ACCEPT, OWNER, manuscript wording or a HUMAN click cannot
   make INVALID/STALE evidence valid, mark an Issue resolved, or release a result.
   Human and Agent callers use the same Application boundary; no ORM DTOs or
   direct adapter/Harness writes are exposed.
3. **Exact target.** No latest/current substitution. Verify same Project,
   frozen state, target hash/scheme and deterministic dependency closure at
   request and decision. Historical navigation supersession alone cannot rewrite
   an exact frozen binding; selecting a different target for the same approval
   purpose requires new request/basis and can stale an unused grant under R2.
4. **Affirmative basis.** Require the exact immutable PROCEED DecisionRecord,
   same project/purpose/target hash, with verified own hash, basis-set hash and
   concrete target/review basis. The Decision and required reviews must already
   be committed before request creation. No inferred intent or synthesized HUMAN
   attribution; current approval authority is independently checked.
5. **Required review set.** Proposed first-slice `review_ids` is the complete
   saved PR2-15 review basis, duplicate-free and order-independent, not a favorable
   subset. Each is completed/immutable, exact-target/hash bound and creation-
   authorized. No new completion flag. Include REJECT and UNCERTAIN recommendations
   permitted by PR2-14; recommendation alone is not the OPEN/BLOCKING predicate.
   Approval adds requester/approver independence checks. A saved review failing
   these cannot simply be dropped. All currently committed matching reviews are
   also inspected for corrupt material, eligibility changes and applicable
   concerns; a corrupt exact-target record fails closed. Later reviews never
   alter the old Decision basis. The distinction between required saved reviews
   and later gate evidence needs owner resolution in §10 before freezing.
6. **Blocking predicate.** Inspect all Issues through authoritative ReviewRecord
   relations independently of caller review IDs or display filters. An applicable
   blocker is exactly same-project, exact target version,
   `status=OPEN AND severity=BLOCKING`. Shared Claim/source, similar text, another
   version or merely the same Project is insufficient. No bypass flag, severity
   override, favorable vote or old PROCEED permits a request or decision through
   this gate. Denial leaves no partial request/decision/grant or success event.
7. **Independent actors.** Requester: authenticated ACTIVE membership, effective
   RESEARCHER or OWNER in active Project. Approver: authenticated HUMAN with
   effective APPROVER, distinct from requester, Decision decider, every required
   reviewer and every material author/contributor in exact closure. Required
   reviewers differ from requester and material authors. Use canonical Actor IDs
   and historical review-creation evidence, not role names alone. OWNER alone,
   Agent APPROVER or acting_on_behalf_of cannot substitute. Existing decider
   policy gains no HUMAN-only requirement from this draft.
8. **Grant scope and time.** Exactly one grant for APPROVE or
   APPROVE_WITH_CONDITIONS; none for REJECT. Scope is project, purpose, exact
   request target/hash, sole allowed command, max_uses=1 and finite expiry. Null
   decision `valid_until` yields `decided_at + 30 days`; otherwise require
   `decided_at < valid_until <= decided_at + 30 days`. UTC and fresh post-lock
   DB time apply; equality at expiry denies. Conditions never execute free text.
9. **Rejection cannot be shopped.** R2's conservative equivalence scope is every
   target in the same `(project_id, approval_purpose)`, irrespective of UUID,
   lineage, hash or wording. After any REJECT, new requests fail
   REJECTION_RECONSIDERATION_REQUIRED until a separately contracted
   RECONSIDER_REJECTION path exists. Retrying another approver or cloning a
   conclusion is not recovery. Existing matching historical replay still reads
   its saved result; deciding an earlier pending request after a rejection must
   also fail closed to prevent pre-created requests bypassing the guard.
10. **Revision trace is preserved, not invented.** Future trace is
    `old Review → Issue → completed RevisionAction → exact new frozen target →
    new independent Review → separately authorized Decision → new ApprovalRequest`.
    Retain old target/reviews/rejection and typed supersession/reconsideration
    edges. This draft creates none of those missing revision/disposition commands.
    OPEN blockers cannot be “fixed” by ordinary mutation or by using PROCEED as
    a dismissal Decision. Carry-forward/closure of old-target concerns needs its
    own contracted policy; exact-target blocking is not permission to clone away
    an unresolved concern. The broader blocking-Issue cycle remains OPEN.

## 4. Proposed commands and DTOs

Commands are closed, typed immutable DTOs with canonical UUID/NFC text
normalization under R2. Unknown fields, duplicate IDs, blank/invalid text, naive
timestamps and unsupported literals fail. Principal comes from verified trusted
context; actors, times, hashes, scope, status and grant ID are server-derived.

| Command | Caller inputs | Result and atomic effect |
| --- | --- | --- |
| `RequestApprovalCommand` / `request_approval` | `id` UUID (canonical request identity), `project_id`, `scientific_conclusion_version_id`, `approval_purpose=INTERNAL_SCIENTIFIC_RELEASE`, `basis_decision_id`, `review_ids: tuple[UUID,...]` | After all gates: one PENDING request, concrete review relation rows and request creation event; no Decision/grant/effect. |
| `DecideApprovalCommand` / `decide_approval` | `id` UUID (canonical ApprovalDecision identity), `project_id`, `approval_request_id`, `decision: APPROVE|APPROVE_WITH_CONDITIONS|REJECT`, nonblank `rationale`, `valid_until: UTC instant|null`, `requires_current_author_consent: bool` | Revalidate pending request and all gates; one immutable decision, request PENDING→DECIDED and event; approving outcome adds one ACTIVE grant and grant event in the same transaction. |
| Exact-ID read queries | Project and exact request/decision/grant UUID | Currently authorized history DTO; no canonical writes, effect or authority refresh. |

APPROVE and REJECT use null `valid_until` and false consent condition in the
proposed first slice; nondefault conditions require APPROVE_WITH_CONDITIONS.
Conditional approval permits only the two R2 typed fields. A true consent
condition for a conclusion has no contracted author-consent resolver in the
current baseline: propose denying it rather than treating it as satisfied.
PREPARE_SUBMISSION's mandatory true consent condition remains deferred, not
removed. Owner must resolve this narrowing before contract freeze.

Request readback: canonical ID/project, exact target/hash/scheme, purpose,
requester/time, immutable basis Decision ID/hash, exact saved review refs/hashes,
current request status and event IDs. ApprovalDecision readback: ID, request ID,
outcome, typed conditions, rationale, actor/time, content hash and nullable grant
readback. Grant readback: ID/decision ID, typed projected scope, expiry, lifecycle
status and events. Historical outcome and current usability are separate DTO
fields; an old APPROVE is not a present authorization assertion. No mutable
reverse arrays become canonical facts.

## 5. Persistence/schema proposal — no migration

Use the already registered governance objects and relation/event patterns. Do
not add a universal ApprovalTarget, DecisionVersion, request receipt entity,
generic policy JSON, review snapshot entity or second scientific hash. All
canonical FKs use RESTRICT, indexed lookups and same-project enforcement. Persisted
enum values are UPPER_SNAKE_CASE. The proposal follows 13/17; it is not DDL.

| Proposed table | Material and enforcement |
| --- | --- |
| `approval_requests` | UUID PK; project FK; concrete conclusion/manuscript target FKs with XOR (first slice conclusion only); frozen target hash and scheme; purpose, actor/time, status. Non-null `basis_decision_id` FK; immutable material; same-project/type/target/basis checks via composite FKs or deferred typed guards. R2 `prior_rejected_request_id` self-FK and `reconsideration_decision_id` FK remain reserved for separately contracted recovery, not writable first-slice inputs. |
| `approval_request_reviews` | Concrete request/review FKs, unique pair; enforce exact target/hash, same project and required saved Decision basis membership; sealed relation set after creation. No canonical ID arrays in JSON. |
| `approval_request_events` | Request FK, prior/new status, actor FK, occurred_at, reason; append-only. Creation status/event convention must match the approved field contract; no fabricated predecessor state. |
| `approval_decisions` | UUID PK; unique request FK; outcome, typed valid_until/consent, rationale, actor/time, content_hash. Immutable UPDATE/DELETE guards. Enforce HUMAN/independence/authority and one decision/request through Application plus database guards against normal-role SQL bypass. |
| `approval_grants` | UUID PK; unique approving decision FK; project, purpose, allowed_command, status, finite valid_until. Exact target reached only through Decision→Request concrete FKs. No target locator or scope JSON. Cross-row guards enforce outcome, sole command and expiry bound. |
| `approval_grant_events` | Concrete grant/actor FKs, prior/new status, time, reason; append-only and atomic with lifecycle change. |
| `approval_grant_consumptions` | Deferred effect boundary: unique grant and command key, concrete XOR result FKs, R3 actor/project/target/command scope, normalized request hash/result receipt fields. No rows are created by request or approval decision. |

Request lifecycle: PENDING→DECIDED or WITHDRAWN; no reuse of terminal request.
Decision: insert once. Grant: ACTIVE→CONSUMED/EXPIRED/REVOKED/STALE; never reactivate.
No unused grant remains usable after new blocker, upstream invalidity, relevant
target selection change or issuing approver authority loss. Immediate role loss
must coordinate and append STALE history atomically under R2. Scheduled expiry
denies at fresh DB time even before projection catches up. Approved lifecycle
implementation must reconcile “persist terminal stale/expired event” with a
failed consumption's rollback; this draft does not silently commit after raising
an error (§10). No sweeper is required to make expiry effective.

Hashes use literal R2 `sha256-cjson-v1`: ApprovalRequest has no own content hash;
it binds the frozen target and immutable decision/review hashes through FKs.
ApprovalDecision material is exactly request UUID, typed exact target ref,
outcome, valid_until, consent boolean, rationale and decided_by, with R2 type and
material_version. Do not add status, event times or review-ID arrays to that
payload. Grant scope is validated typed state, not a new content-hash payload.
R3 consumption request hashes are operational idempotency material, never a
substitute for scientific content hashes.

Future schema admission requires owner review of existing registry fields,
constraints and any genuinely new fields; complexity-budget/ADR review precedes
material deviations. Use a forward migration, one Alembic head, legacy preflight,
immutable normal-role SQL guards and data-preserving downgrade/refusal. Never
edit accepted 0040–0042 or frozen Phase 1 hashes to fit this proposal.

## 6. Proposed error contract

Authenticate and establish current project entitlement before returning existence,
conflict or protected target details. Wrong-project IDs must not disclose foreign
history. Transport mappings are proposals: 401 authentication, 403 forbidden,
404 authorized missing record, 422 malformed command, 409 gate/state/conflict.
Use bounded sanitized diagnostics; no SQL, driver or credential exception chains.

| Code | Trigger | Standing |
| --- | --- | --- |
| AUTHENTICATION_REQUIRED / FORBIDDEN | Missing trusted principal; missing live credential/effective role or read entitlement; wrong actor scope | Existing categories. |
| VALIDATION_ERROR / NOT_FOUND | Malformed closed DTO; authorized exact ID absent | Existing categories. |
| CONFLICT_OF_INTEREST | Requester/reviewer/decider/author/approver independence failure | Existing category. |
| IDEMPOTENCY_CONFLICT | Same UUID changed canonical material; second decision/new UUID for terminal request | Existing category. |
| CONCURRENT_MODIFICATION | Exhausted bounded serialization/deadlock retry; no partial commit | Existing category; operational timeout mapping must be pinned before implementation. |
| PROVENANCE_CLOSURE_VIOLATION / REFERENTIAL_INTEGRITY_ERROR / IMMUTABLE_RECORD | Corrupt hash/basis, broken strong FK or forbidden mutation | Existing categories. |
| APPROVAL_PURPOSE_TARGET_COMMAND_INVALID | Unlisted or unavailable purpose/target/command tuple | R2 design code, not yet an implemented ErrorCode here. |
| APPROVAL_GATE_FAILED / DECISION_BASIS_INVALID | Missing required review/affirmative basis; OPEN/BLOCKING Issue; request target not eligible | 12 design codes; proposed approval mapping. |
| APPROVAL_TARGET_STALE | Request's target/hash/current validity no longer passes decision gate | 12 design code; no scientific mutation. |
| REJECTION_RECONSIDERATION_REQUIRED | Any prior same-project/purpose rejection without contracted complete reconsideration | R2 design code; first slice always denies new recovery. |
| GRANT_INVALID / GRANT_STALE | Deferred consumption has wrong scope/terminal/expired grant or current eligibility loss | 12/17 design codes; no consumption implementation in this task. |

Adding any absent enum or API/CLI mapping belongs to separately authorized
implementation. A free-text error must not quietly authorize a deferred path.

## 7. Concurrency, transactions and replay

One Application command = one synchronous PostgreSQL 18.x UoW transaction:
Caller → Application → Repository Port/UoW → Persistence Adapter → PostgreSQL.
Domain imports no Session/FastAPI/Typer/Harness. No external network call is
part of approval persistence or the lock-critical scientific gate.

Proposed coordination order is request/decision UUID advisory coordination →
project/purpose approval-rejection scope → exact conclusion FOR UPDATE → sorted
closure/authority snapshot locks → request/decision/grant rows in stable order →
review rows in UUID order → Issue/basis/event writes. The rejection scope must
serialize all first requests and deciding REJECT operations across different
target IDs, not just one target row. No caller-defined arbitrary scope is
authority. A fixed namespaced project/purpose advisory lock is an operational
mechanism, not a new canonical identity. Direct normal-role SQL needs equivalent
database participation; Application-only locks cannot enforce the invariant.

The existing PR2-15 request→target→sorted SHARE-table protocol and PR2-14/0041
review/Issue writer target coordination must remain compatible. Before a future
implementation, inventory every review, Issue, closure, target-selection,
membership/role, rejection and grant writer; document a common lock matrix/order
including deferred consumption/revocation. If a path cannot participate without
inversion, stop for a contract correction. Target exclusion alone does not
protect unrelated upstream state, role changes or cross-target rejection races.

After every required wait, reread durable target, complete matching reviews,
all applicable Issues, immutable Decision basis and rejection history using
fresh protected reads. Validate hashes/closure and independence. Obtain fresh
`clock_timestamp()` immediately before effect and recheck live credential,
membership/effective roles and expiry. Never use now()/transaction_timestamp(),
cached lists or a caller clock as final authority. Any further wait repeats the
check. Retry at most three whole attempts for deadlock/serialization failure,
with a new transaction and fresh reads each time; pin timeout policy separately.

If review/Issue commits first, request/decision waits then observes it and
includes gate evidence or denies. If approval commits first, later legitimate
concerns remain appendable and immediately prevent future grant use; they never
rewrite approval history. Prove both orders, including zero-Issue review INSERT.
Concurrent APPROVE/REJECT on one request yield one decision and at most one grant;
different pending requests in one project/purpose cannot bypass a committed
rejection. Proposed duplicate pending exact-target/purpose requests are denied
under scope coordination (owner to freeze uniqueness/lifecycle policy in §10).

Canonical request identity is `ApprovalRequest.id`; decision command identity is
`ApprovalDecision.id`. Compare normalized caller fields, project, command and
trusted actor against saved immutable material; no new request-digest field or
receipt table is proposed for these commands. Review UUID set normalization is
deterministic; caller order does not change semantic identity. At most one saved
result/event set per UUID. Entitled same-actor exact replay returns saved history,
including after target STALE or original write-role loss, with current read
entitlement and live credential. Replay never rescans a new basis or refreshes
grant scope/expiry. Current lifecycle usability is returned separately. Changed
payload conflicts; another actor cannot impersonate the original submission.
Uncertain commit recovery uses exact UUID, not replacement approval. Unknown or
incomplete history is not completed replay. This proposed request/decision replay
policy extends the minimal Decision pattern; it does not change PR2-14 replay.

Future consumption uses R3/R4/A21 completed receipt scope and current read
entitlement: exact durable replay returns saved result without rechecking effect
authority or executing again. First consumption still needs all current gates,
one unique receipt and atomic effect. Those obligations are not fulfilled by an
ACTIVE grant from this proposed slice.

## 8. Architecture and adversarial tests to add later — NOT IMPLEMENTED

| Test group | Required assertions in a separately authorized PR |
| --- | --- |
| Layer/boundary | Domain has no persistence/web/CLI/Harness imports; Human/Agent callers use identical Application commands; DTOs contain no ORM entities. |
| Semantic separation | Approval/replay never creates release, publication transition, prepared package, ExternalEffect, Issue disposition, RevisionAction, VERIFIED or changed scientific material. PROCEED/approval cannot override invalid facts. |
| Finite policy | Exhaustive purpose × concrete target × state × allowed-command matrix; only contracted slice available; no role/condition/free-text widening. |
| Frozen closure | DRAFT/missing/wrong-project/hash mismatch/INVALID/STALE deny; exact history survives newer versions, restart and source correction without altered hashes. |
| Basis and blocking | Complete saved favorable/unfavorable basis; new zero-Issue review, corrupt matching review, zero required reviews, requester conflict; OPEN/BLOCKING exact target denies, unrelated version/project does not. |
| Actor/temporal policy | HUMAN effective APPROVER required; every independence pair; Agent role/OWNER/on-behalf-of bypass fails; scheduled/immediate revocation and lock wait across credential/role/grant expiry deny with DB-derived timestamps. |
| Schema/history | Concrete target XOR and same-project FKs, unique decision/request and grant/decision, sealed relations, finite expiry checks, append-only events, immutable UPDATE/DELETE and direct-SQL bypass attempts. Real PostgreSQL, never SQLite. |
| Rejection/revision | Scope-wide clone/UUID/hash/approver shopping denies; pending request versus other-target REJECT race; no PROCEED dismissal/reconsideration substitution; preserved old Issue/review/rejection/new-result trace once separately contracted. |
| Replay/failure | Same UUID once, reordered identical review set, changed fields conflict, nondisclosure, write-role loss with read role, STALE historical read; fault between decision/grant/event rolls back everything; uncertain commit and bounded retry do not duplicate. |
| Lifecycle/effect dependency | Unused grant becomes unusable after new blocker/authority loss; no terminal reactivation; separate future consumption tests one receipt/effect under concurrency, exact scope/results, R3/R4 completed replay. |
| Migration/regression | Disposable PostgreSQL upgrade/catalog/legacy preflight/downgrade preservation and one head; PR2-14/15 suites and Phase 1 golden compatibility. No migration added for this draft. |

Race evidence must identify separate backend PIDs, actual lock wait via
pg_stat_activity/pg_blocking_pids()/pg_locks, commit order, protected reads and
persisted effect/event counts. Cross-expiry tests meet Addendum A22 inequalities,
including a second required wait when present. Sleeps alone do not prove safety.

## 9. Acceptance criteria and evidence boundary

Draft acceptance requires resolved local source links, exact DRAFT status, only
this proposal added, no authoritative/code/schema/test edits, and clear separation
of inherited invariants, proposed choices and unresolved owner decisions.
Verification must report exact commands and actual counts, including unavailable
PostgreSQL evidence; source inspection is not execution PASS.

Before any contract freeze: resolve §10, verify consistency against 01/02/03/05/
08/12 and R2/R3/R4/20, explicitly approve the bounded slice and its dependency
limits, and record independent review with no open P0 BLOCKER or P1 MAJOR. Owner
approval of this document alone does not grant IMPLEMENTATION_GO.

Before future implementation acceptance: all in-slice §8 requirements pass on
PostgreSQL 18.x, required lint/type/unit/architecture/golden checks pass, forward
migration and normal-role SQL evidence pass, restart/replay/race/failure evidence
is recorded, and a concrete grant-usability policy exists. Full PR2-16 acceptance
cannot be claimed from only the internal request/decision/grant slice if owner
requires the remaining finite-policy/lifecycle/effect paths. No Human Gate, TDG2,
PR2-14/15/16 or M4 gate status changes are inferred from this draft.

## 10. Open questions for the owner — resolve before freeze

| Question | Proposed disposition and consequence |
| --- | --- |
| Is PR2-16 initially internal request/decision/grant only, or all three R2 purposes and grant consumption? | Approve the bounded slice explicitly; manuscript review, new Decision purposes, effects and lifecycle commands otherwise require separate contracts. Do not claim full PR acceptance prematurely. |
| Must later matching reviews join the request's required Decision-backed set, or only the current gate evidence? | Propose required IDs equal immutable PROCEED basis, with all later concerns inspected. Requiring a refreshed complete Decision basis conflicts with minimal Decision no-replacement; do not silently supersede it. Resolve requester-independence failures and unfavorable recommendations explicitly. |
| What is the exact duplicate-request policy after withdrawal, expiry or stale grant? | Propose no duplicate pending exact-target/purpose requests. Freeze uniqueness, successor links and resubmission rules; every historical rejection retains project/purpose equivalence guard. |
| How are concern carry-forward, ADDRESSED/DISMISSED and rejection recovery authorized? | Separate Issue/RevisionAction/revision-purpose/RECONSIDER_REJECTION contracts; current BLOCKING cycle remains open. The existing RevisionAction draft is not authority. |
| Which typed conditions are executable for conclusion approval? | Permit finite valid_until only in first-slice conditional approval; deny true author-consent condition until its target-specific resolver is contracted. Never add generic condition JSON. |
| Must REJECT still require all frozen/review/validity gates? | R2 requires request and decision rechecks; propose symmetric denial if stale/blocked rather than recording rejection on invalid pending material. A withdrawal/administrative termination path needs separate definition. |
| Which lifecycle commands and writer coordination must accompany grant creation? | Freeze withdrawal/revocation authority, duplicate scope, stale events and lock matrix before implementation. No unsafe usable grant can rely solely on eventual projection. |
| How does first-observer stale/expiry persistence coexist with failed-command atomic rollback? | Choose a separately committed lifecycle-evaluation command or explicit approved transaction exception; current first-slice reads report unusability without pretending an error committed events. |
| Are proposed request/decision replay and transport/error mappings approved? | Pin closed DTO normalization, current read roles, same-actor replay, conditional-field bounds, timeout mapping and unavailable-purpose errors before implementation. Preserve R3/R4/A21 consumption receipt semantics. |

## 11. Documentation-task verification — 2026-10-13

These are current repository checks, not tests of a Basic Approval implementation.
Only this draft is added to the tracked-file change set. Verification scratch/cache
paths are under ignored repository `tmp/task11-verification/`. No commit, branch,
push, accepted migration edit or retained database write was performed.

Exact executed commands and results:

```bash
uv --cache-dir tmp/task11-verification/uv-cache run --offline --no-sync pytest -o addopts='' -ra tests/unit tests/architecture
```

Exit 1: **1821 passed, 4 failed, 0 skipped, 2 warnings** in 30.16s. All four
failures are in `tests/unit/test_hg1_runner.py`: versioned denial, socket lifecycle,
foreign-peer policy and incomplete-frame deadline. They fail at `RunnerServer.start`
with `PermissionError: [Errno 1] Operation not permitted` on Unix socket bind.
The repository was not modified to suppress these environment failures.

```bash
uv --cache-dir tmp/task11-verification/uv-cache run --offline --no-sync ruff check .
uv --cache-dir tmp/task11-verification/uv-cache run --offline --no-sync ruff format --check .
uv --cache-dir tmp/task11-verification/uv-cache run --offline --no-sync pyright
```

All three exit 0: Ruff lint **All checks passed**; formatter **456 files already
formatted**; Pyright **0 errors, 0 warnings, 0 informations**. These tools do not
validate Markdown policy semantics.

```bash
pg_isready -h 127.0.0.1 -p 5432
pg_isready -h 127.0.0.1 -p 55440
mkdir -p tmp/task11-verification/pgsocket
/opt/homebrew/opt/postgresql@18/bin/initdb -D tmp/task11-verification/pgdata -U task11_admin -A trust --no-locale
RB_TEST_ADMIN_URL=postgresql+psycopg://task11_admin@127.0.0.1:55479/postgres uv --cache-dir tmp/task11-verification/uv-cache run --offline --no-sync pytest -o addopts='' -ra --tb=short tests/integration/phase2/test_pr2_14_internal_review.py tests/integration/phase2/test_pr2_14_conclusion_review.py tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_15_decision_schema.py
```

Both readiness checks exit 2, **no response**. initdb exits 1 at `shmget` with
`could not create shared memory segment: Operation not permitted` and removes its
incomplete cluster. No server could be started. The integration invocation exits
1: **0 passed, 0 failed assertions, 56 setup errors, 0 skipped** in 4.47s;
connection attempts are denied by the environment. **BLOCKED, not PASS:** no
PostgreSQL integration assertion or migration acceptance completed. Approval
escalation is unavailable in this session. Rerun those four suites on a permitted
disposable PostgreSQL 18.x host before claiming baseline integration success.

Other scientific integration suites were not run: this file is a non-authoritative
proposal and changes no executable/schema/frozen contract. The future §8
acceptance matrix remains planned, NOT RUN; it requires broader real-database
verification when implementation is separately authorized.

Documentation checks use the following exact command:

```bash
uv --cache-dir tmp/task11-verification/uv-cache run --offline --no-sync python - <<'PY'
from pathlib import Path
import re
import subprocess

p = Path('docs/proposals/PR2-16_Basic_Approval_Contract_DRAFT.md')
s = p.read_text()
links = re.findall(r'\]\(([^)]+)\)', s)
assert all((p.parent / target).is_file() for target in links)
assert '**Status: DRAFT — awaiting owner approval; not authorized for implementation**' in s
changes = subprocess.check_output(['git', 'status', '--short'], text=True).splitlines()
assert changes == [f'?? {p.as_posix()}'], changes
assert all(line == line.rstrip() for line in s.splitlines())
print(f'4 checks passed: {len(links)} links resolve; exact status; sole draft change; no trailing whitespace')
PY
git diff --check
```

Result: **4 documentation checks passed**, **19 local links resolve**; exact DRAFT
status, sole draft change and no trailing whitespace verified. `git diff --check`
exits 0. The explicit content check covers this untracked proposal, which ordinary
git diff does not include. This is draft verification, not independent architecture
review or owner approval.

