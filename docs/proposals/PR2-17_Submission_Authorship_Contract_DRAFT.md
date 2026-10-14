# PR2-17 SubmissionVersion + Minimal Authorship Contract — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

**Scope:** documentation proposal only: package manifest, AuthorshipSnapshot and
basic AuthorConsent, with no ExternalEffect. This is not an architecture freeze,
ADR, execution pack, migration authorization or PR2-17 acceptance declaration.
Owner approval of a contract and separate implementation authorization are distinct.

## 1. Purpose, authority and current baseline

PR2-17 records exactly what was prepared for possible submission, who is attributed
as an author, and which author's own consent supported preparation. It never
asserts that anything was sent. Under Addendum A17 and Correction 12, the older
PR title's `SubmissionVersion` means **PreparedSubmissionVersion** here. Actual
SubmissionVersion, SubmissionRecord and external-send history remain deferred.

The owner reports the [PR2-15 RevisionAction draft](PR2-15_RevisionAction_Contract_DRAFT.md)
and [PR2-16 Basic Approval draft](PR2-16_Basic_Approval_Contract_DRAFT.md) approved
on **2026-10-14**, with implementation underway. Treat their contract choices as
the base for this proposal. Their retained DRAFT headings and older verification
sections are historical file content; this task does not edit them or infer that
ongoing implementation has passed acceptance. The owner-reported approval date is
recorded as supplied, not independently established by repository timestamps.

| Source | Constraint carried into this proposal |
| --- | --- |
| [System Architecture 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 9–13, 27–31 | Deterministic facts precede authority; immutable exact-version closure; membership is not authorship, corresponding authorship is not approval authority, Agent contribution is not HUMAN authorship. |
| [Correction Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A17–A23 | Prepared versus sent distinction; focused R2/R3/R4 precedence, bounded schema admission, advancing DB time and completed-receipt read entitlement; minimal Decision purpose stays bounded. |
| [Global Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), Phase 2 registry | Publication owns PreparedSubmissionVersion, AuthorshipSnapshot, ContributionRecord, AuthorConsent and PreparedSubmissionEvent; no new top-level canonical concept is needed. |
| [Cross-Phase Contracts 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§9, 12–18, 24, 28, 38, 41 | Common Application boundary, additive compatibility, strong exact FKs, immutable history, stable errors and golden regressions. |
| [Phase 2 Specification 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §§23–24, 34, 37–39, PR2-17, §§49–52 | Prepared package manifest and minimal authorship; frozen closure, internal gate, architecture tests and no ExternalEffect. |
| [Phase 2 Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), §§1–2, 4–7 | AuthorConsent is append-only; separate PREPARE_SUBMISSION grant consumed by package freeze; package lifecycle never implies sending. |
| [Field Contract 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md), §§66–72; [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md), authorship/package payloads | Typed relation storage, literal hash payloads and null draft hashes; R2 author/set ordering overrides conflicting older ordering. |
| [Governance R2 17](../architecture/17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md), §§1–3 | Finite approval tuple, same-Publication closure, evidence-required direct HUMAN consent chains, freeze/withdrawal serialization and no post-freeze reactivation. |
| [R3 18](../architecture/18_Phase2_Design_R3_Targeted_Remediation_v1.0.md), §5; [Temporal R4 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md), TEMP-AUTH-01 | Exact normalized consumption request/receipt, SERIALIZABLE effect transaction, fresh post-wait authorization and historical completed replay. |
| [Minimal Decision Contract 20](../architecture/20_PR2_15_Minimal_Decision_Command_Contract_v1.0.md) and approved PR2-15/16 bases above | PROCEED is not revision disposition, manuscript readiness or package preparation authority; PR2-16's bounded internal approval slice does not enable deferred manuscript tuples. |

The inspected code supplies narrower prerequisites:

- [PublicationService](../../src/researchbase/application/publication.py) creates
  publication identity and manuscript drafts bound to document ArtifactVersion;
  it does not expose manuscript freeze or READY transition.
- [Placement services](../../src/researchbase/application/manuscript_placement.py)
  and [scientific trace](../../src/researchbase/application/manuscript_scientific_trace.py)
  supply exact claim/conclusion, citation and artifact paths. A read-only trace
  and structurally valid stored hash are not a complete package freeze verifier.
- [InternalReviewService](../../src/researchbase/application/internal_review.py)
  covers ClaimVersion and ScientificConclusionVersion reviews with initial OPEN
  issues, not manuscript review or Issue disposition.
- [DecisionService](../../src/researchbase/application/decision.py) implements
  INTERNAL_SCIENTIFIC_RELEASE/PROCEED only. Existing migrations through
  [0042](../../migrations/versions/0042_pr2_15_minimal_decision.py) do not supply
  prepared packages, authorship/consent or Basic Approval persistence.

Source presence is not milestone acceptance. Reconcile this inventory with the
PR2-15/16 implementations at contract freeze; do not silently implement their
missing work inside PR2-17. No target PR2-17 execution pack was found; this proposal
cannot serve as an authorized replacement pack.

## 2. Proposed scope and non-goals

Propose recording contributions, creating an immutable authorship snapshot,
creating one exact PREPARED package, appending direct-author grant/withdrawal/
regrant consent, querying exact package history and validity, and eventually
freezing/withdrawing prepared packages through contracted Application commands.
Freeze is **unavailable until its separately approved dependencies exist** (§9).
A preparation-only slice is useful but cannot claim full PR2-17 acceptance.

Minimal authorship includes contribution evidence because R2 requires at least
one same-author contribution per author. Do not add AuthorshipDecision or a
CRediT taxonomy service to this slice; attribution is not adjudication. The
System Architecture's broader authorship chain is retained for later extensions,
not converted into a new required workflow engine here.

Excluded: actual SubmissionVersion/SubmissionRecord, venue API, dispatch,
ExternalEffect, submission receipt, publisher response, publication release,
PublishedVersion, representative consent, signatures/PKI service, authorship
appeals/disputes, full governance engine, runtime Agent orchestration, queues and
new runtime dependencies. No schema, migration, executable code, tests or
canonical architecture files are changed by this task.

## 3. Invariants and prepared-package closure

1. **One owner per fact.** Package packaging belongs to publication; scientific
   support belongs to its existing owners. A manifest copies no scientific
   assertion and creates no EvidenceRelation or LiteratureSupportSnapshot.
   Citation is presentation, never Claim support. Review, RevisionAction,
   Decision, Approval, consent and a package are not interchangeable facts.
2. **Same Publication and exact identity.** Manuscript, snapshot, contributions
   and package agree on Publication; Publication determines Project. Use concrete
   typed FKs and same-parent composite keys. No `latest/current`, generic
   `target_type + target_id`, arbitrary reference JSON or ORM entities in DTOs.
   Project-access checks still apply to globally owned literature sources.
3. **Authorship is frozen attribution.** Nonempty HUMAN author list has distinct
   Actor IDs, authored ordinals 1..N and at least one same-Publication contribution
   whose actor equals each author. Contribution role/statement are nonblank.
   Agent contributions may be included as evidence, never silently in the HUMAN
   author list. Corresponding authors are a duplicate-free subset; equal groups
   contain at least two distinct authors, with no duplicate or overlapping groups.
   Roles, affiliation, display name, ORCID and corresponding-author status neither
   establish author identity nor grant scientific/governance authority.
4. **Immutable consent context.** Proposed first slice fixes manuscript, snapshot
   and non-consent manifest at PREPARED creation. No retarget/edit command follows
   consent capture; corrections require a new package and new author consent.
   This deliberately narrows draft editing to prevent an ID-only package consent
   from approving changed material. A preview digest is noncanonical and is not
   persisted as a premature package hash (§5).
5. **Direct consent only.** Scope is exactly PREPARED_PACKAGE, acknowledging
   preparation of this exact context, never venue sending. Verified HUMAN author
   identity equals the consent actor; no OWNER/APPROVER/corresponding author or
   Agent acting_on_behalf_of substitute. Both GRANTED and WITHDRAWN require an
   exact frozen accessible evidence ArtifactVersion with verified bytes/hash.
   A file proves retained evidence, not identity authentication by itself.
6. **One immutable chain.** Root is GRANTED with no prior consent. WITHDRAWN
   refers to the current GRANTED head; regrant refers to the current WITHDRAWN
   head. Every link retains package, author and scope; one root, one successor,
   no cycles/forks. Current consent is the unique terminal head. Regrant on a
   PREPARED package is permitted; new consent is not transported across packages.
7. **Freeze binds complete material.** Verify exact frozen manuscript/document,
   placement bindings, AuthorshipSnapshot, contribution hashes, source/claim/
   conclusion/artifact closure and current deterministic VALID status. Required
   reviews and Decision basis, no applicable OPEN/BLOCKING Issue and all author
   consent gates must pass independently of earlier approval. Hash equality or
   authority cannot override invalid scientific facts.
8. **Mandatory distinct preparation grant.** Publication is READY, target is the
   exact FROZEN ManuscriptVersion, purpose PREPARE_SUBMISSION, allowed command
   FREEZE_PREPARED_SUBMISSION, max_uses=1. Require its distinct affirmative
   PREPARE_SUBMISSION Decision and exact manuscript reviews, not the readiness
   grant or conclusion PROCEED. Recheck independent HUMAN approver, current
   authority, finite expiry, rejection guard and all typed conditions;
   requires_current_author_consent is mandatory true at consumption.
9. **Freeze is one atomic local effect.** Hashes/frozen_at, PREPARED→FROZEN event,
   any older frozen package supersession, one exact-result consumption receipt,
   grant ACTIVE→CONSUMED and grant event commit together. No network send occurs.
   No failed gate may leave a receipt, frozen row, supersession or success event.
10. **History versus current validity.** Withdrawal before freeze denies freeze
    until valid regrant. Withdrawal after freeze appends history and immediately
    makes that package's derived current validity STALE; material, frozen consent
    FK, hashes and consumed grant remain untouched. It atomically stales related
    unconsumed PREPARE_SUBMISSION grants with events. Regrant cannot restore a
    frozen package binding to withdrawn consent or reactivate terminal grants:
    create a new package, fresh consents and new approval.
11. **Lifecycle is separate from bytes.** PREPARED→FROZEN or OWNER WITHDRAWN;
    FROZEN→SUPERSEDED when a newer same-Publication package freezes, or OWNER
    WITHDRAWN. No reverse transitions. Proposed one FROZEN package per Publication
    is enforced under parent coordination; no current-package pointer is added.
    Never-frozen withdrawal retains null hashes/frozen_at; frozen withdrawal and
    supersession preserve them. Supersession alone is navigation history, not
    deterministic invalidity; historical exact dependencies still resolve.

### 3.1 Manifest projection and hash ordering

Use the six R2 categories and one concrete nonnull target per row:

| Category | Exact target | Proposed completeness/ordinal rule |
| --- | --- | --- |
| FIGURE / TABLE | ArtifactVersion | Exact figure/table placement occurrences, separately per category. |
| CITATION | SourceVersion | Exact citation placement occurrences; citation alone adds no scientific support. |
| CLAIM | ClaimVersion | Exact direct Claim placement occurrences. |
| CONCLUSION | ScientificConclusionVersion | Exact direct conclusion placement occurrences; transitive inputs are verified through closure, not duplicated as direct placements. |
| AUTHOR_CONSENT | AuthorConsent | Exactly one current GRANTED head for each snapshot author; no extra author, package or scope. Proposed order follows authored author order, with zero-based manifest ordinals. |

Non-consent occurrences are projected from the sealed manuscript, sorted within
category by `(section_id, placement ordinal)` under its accepted placement
ordering, then assigned contiguous 0..N-1 category ordinals. Preserve repeated
placements of the same target; do not silently deduplicate or append extra
unplaced scientific facts. Manuscript and package sets must agree in multiplicity
and exact target IDs/hashes. Mixed artifact categories not FIGURE/TABLE require
owner resolution (§10); no catch-all category is invented. Document artifact is
already reached through ManuscriptVersion, not a duplicate manifest item.

The occurrence mapping is a **proposed refinement**, not an existing frozen
contract. Snapshot/manifest hashes use exactly R2 15 (§5), not this prose as a new
payload schema. Full transitive scientific provenance, including separate Phase 2
literature support, remains verified without altering Phase 1 hash material.

## 4. Proposed commands, closed DTOs and readback

All DTOs are immutable and closed. Reject extra keys, wrong UUID types, duplicate
set members, unsupported enum literals, blank/invalid Unicode and caller-supplied
status, actor, timestamp, hash or role assertions. Text uses R2 NFC normalization
with meaningful whitespace preserved. Proposed limits: required statements and
reasons 1..10,000 characters after NFC, at most 100 authors and 10,000 manifest
occurrences; pin these conservative limits and the contribution-role enum before
freeze (§10). Actors, effective times, hashes and version numbers are derived.

| Command | Caller inputs | Atomic result / role proposal |
| --- | --- | --- |
| `RecordContributionCommand` / `record_contribution` | `id`, `project_id`, `publication_id`, `actor_id` (attributed contributor), `contribution_role`, `contribution_statement` | Immutable ContributionRecord/hash; authenticated active RESEARCHER or OWNER is recorded_by. Attribution is not consent. |
| `CreateAuthorshipSnapshotCommand` / `create_authorship_snapshot` | `id`, project/publication IDs, ordered `author_ids`, set `corresponding_author_ids`, set of equal-author groups, ordered `contribution_record_ids` | One immutable snapshot/hash plus sealed typed relations; RESEARCHER or OWNER, all §3 authorship checks. |
| `PrepareSubmissionCommand` / `prepare_submission` | `id` (package UUID), project/publication IDs, exact manuscript/snapshot IDs | One PREPARED row/version number and creation event with server-projected non-consent items; RESEARCHER or OWNER. Proposed require already FROZEN valid manuscript/snapshot; no grant consumed. |
| `RecordAuthorConsentCommand` / `record_author_consent` | `id`, `project_id`, `prepared_submission_version_id`, `consent_state`, `consent_scope=PREPARED_PACKAGE`, `evidence_artifact_version_id`, `prior_consent_id|null` | One immutable chain append/hash; actor comes only from verified HUMAN context matching a snapshot author. Root/regrant only PREPARED; withdrawal also available after freeze/supersession/package withdrawal. |
| `FreezePreparedSubmissionCommand` / `freeze_prepared_submission` | `command_key`, `project_id`, `grant_id`, `prepared_submission_version_id`, `expected_package_manifest_hash`, nonempty duplicate-free `checked_review_ids` | RESEARCHER or OWNER, dependency-gated; §3 atomic freeze and R3 receipt whose concrete package result equals input ID. No free-form effect argument. |
| `WithdrawPreparedSubmissionCommand` / `withdraw_prepared_submission` | package/project IDs, nonblank `reason` | OWNER, allowed §3 lifecycle states; append event and revoke current eligibility without erasing material; repeat same withdrawal with identical reason/actor returns saved terminal event, differing retry conflicts. Replay policy needs owner freeze (§10). |
| Exact-ID history / `preview_prepared_submission` queries | `project_id`, exact record/package ID | Authorized typed readback; preview recomputes candidate manifest with current consent heads, identifies missing consent/dependencies and returns noncanonical candidate digest. No writes or grant issuance. |

Proposed consent access requires live bound principal and ACTIVE project membership
with any effective read role (OWNER/RESEARCHER/REVIEWER/VIEWER/APPROVER), in addition
to exact HUMAN author identity. It does not require a writer role merely to
withdraw one's consent. An author with no current project entitlement cannot
use this path; owner must resolve offboarding safety before implementation (§10).
No public or on-behalf-of withdrawal endpoint is implied.

Read DTOs expose exact IDs, parent/project, authored ordering and contribution
refs/hashes; package state, nullable draft hashes, frozen manifest refs/hashes;
consent chain history and current heads; immutable actors/DB times and lifecycle
events; grant/consumption references when present. Report frozen historical facts
separately from derived `current_validity` and bounded reason codes. Proposed
PREPARED result is NOT_FROZEN, never VALID merely from a preview. A validity
projection is not a new canonical row or mutable scientific assertion.

Freeze's normalized R3 request has exactly `type=ApprovalGrantConsumptionRequest`,
`material_version=1`, `command=FREEZE_PREPARED_SUBMISSION`, project, authenticated
actor, grant, request's exact manuscript `target={type,id,content_hash}`,
`result_id=prepared_submission_version_id`, expected manifest hash and sorted
checked review IDs. Target and result scope derive from the durable package and
grant request; callers cannot retarget them. Persisted receipt DTO is replay
projection only. The expected digest is compared with a fresh fully validated
manifest inside freeze, not trusted as caller proof.

## 5. Persistence/schema proposal — no migration

Use registered Entity/Version + Relation + Snapshot + Event objects. No generic
Package, ConsentVersion, ManifestDocument, AuthorshipDecision, custom policy JSON
or new request-receipt table is admitted. Standard actor/time/hash-scheme fields,
indexed FK paths, RESTRICT and normal-role SQL enforcement follow 13; actual DDL
and any extra field require separately authorized design/ADR review.

| Table family | Proposed material and database enforcement |
| --- | --- |
| `contribution_records` | UUID PK; Publication/actor/recorded_by concrete FKs, bounded role/statement and immutable content_hash/hash_scheme. No version row; frozen snapshots select exact contribution records. |
| `authorship_snapshots` and four `authorship_snapshot_*` relation tables | Snapshot Publication FK and own hash, unique `(publication_id,id)`; author, corresponding, equal-group and contribution rows are sole canonical collections. Enforce author ordinal/actor uniqueness, contiguous author/contribution order, subset/nonoverlap and same-author contribution coverage through sealed-set/deferred typed guards. No JSON ID arrays. |
| `prepared_submission_versions` | Publication parent/version_number, exact manuscript and snapshot, lifecycle, nullable package_manifest_hash/content_hash/frozen_at. Unique publication+number and publication+id; composite same-Publication manuscript/snapshot FKs. Proposed partial unique FROZEN per Publication; no current pointer. Hash-null/frozen-state checks distinguish never-frozen and formerly frozen WITHDRAWN. |
| `prepared_submission_manifest_items` | Concrete package FK, category, ordinal, XOR artifact/source/claim/conclusion/consent FK. Enforce category/type, unique package+category+ordinal, contiguous category ordinals, same-project access and sealed material. Consent uses composite `(package_id,author_consent_id)` FK via consent unique key plus same-author/current-head freeze guard. No duplicated manuscript/snapshot items. |
| `prepared_submission_events` | Package/actor FKs, prior/new status, DB occurred_at, reason; append-only. Creation convention must follow approved field contract; no fabricated prior state. Freeze event reaches decision/grant via concrete consumption path. |
| `author_consents` | Package/actor/prior-consent/evidence-artifact FKs, state, PREPARED_PACKAGE scope, captured_at, own hash. R2 overrides older nullable evidence allowance: evidence required for both states. Unique root per package+actor+scope, unique nonnull prior FK, unique package+id for manifest FK; same-chain/current-head/alternating-state guards reject branches/cycles. Immutable UPDATE/DELETE. |
| Existing governance grant/event/consumption relations | Freeze references the approved PREPARE_SUBMISSION scope and R3 receipt with globally unique command_key and unique grant; concrete result FK is this package only. No duplicate release/send record; no change to scientific version bytes. |

Package points to snapshot, not a reciprocal snapshot→package FK: R2/13's
same-Publication shape governs over Registry 03's abbreviated linkage wording.
Contribution belongs to Publication; snapshot relation selects it for a package.
No package-hash cycle or second owner is introduced.

All five hashes use literal R2 type/material_version=1, canonical-json-v1 and
sha256-cjson-v1. Own and binding material is exactly:

- ContributionRecord: Publication idref, actor idref, contribution_role,
  contribution_statement and recorded_by idref.
- AuthorshipSnapshot: publication_id; authored author rows with 1..N ordinals;
  corresponding Actor idrefs sorted by UUID; equal-group members sorted by UUID
  and groups lexicographically by member tuples; contribution refs with authored
  contiguous 0..N-1 ordinals. Storage group/set ordinals are not hash order.
- AuthorConsent: package idref, actor idref, state, scope, exact evidence artifact
  ref and prior consent ref or null. Capture time excluded. Package is ID-only
  because capture precedes freeze, avoiding a package/consent digest cycle.
- PreparedSubmissionVersionManifest: manuscript and snapshot exact refs plus
  items `{category,ordinal,target}` sorted lexically by category enum text then
  ordinal. Generated item IDs are excluded.
- PreparedSubmissionVersion: publication_id, manuscript/snapshot exact refs and
  package_manifest_hash; no status, timestamp, actor or version number addition.

Immutable records/snapshot receive hashes at insertion. PREPARED own/manifest
hashes stay SQL NULL until successful freeze; transient preview is not a saved
hash. Every formal read recomputes hashes and full exact closure, failing closed
on mismatch. Later validity/lifecycle changes preserve frozen bytes. Future
migration must use one forward Alembic head, invalid-legacy-state preflight,
clean install/upgrade, normal-role guards and data-preserving downgrade/refusal;
never edit accepted migrations or frozen Phase 1 payloads.

## 6. Proposed error contract

Authenticate and establish live project entitlement before revealing existence,
conflicts or foreign history. Proposed HTTP classes: 401 unauthenticated, 403
forbidden, 404 authorized missing ID, 422 malformed DTO, 409 state/gate/provenance/
concurrency conflict. Pin API/CLI mappings before implementation; diagnostics
are bounded and sanitized, with no SQL/driver/credential chains.

| Code | Trigger / standing |
| --- | --- |
| AUTHENTICATION_REQUIRED / FORBIDDEN | Existing categories; invalid principal/live entitlement, wrong HUMAN consent actor or insufficient effective role. |
| VALIDATION_ERROR / NOT_FOUND | Existing; malformed closed DTO/unlisted category, authorized missing exact record. |
| VERSION_NOT_FROZEN / INVALID_STATE_TRANSITION / IMMUTABLE_RECORD | Existing; draft target, terminal package command or mutation of sealed material. |
| REFERENTIAL_INTEGRITY_ERROR / PROVENANCE_CLOSURE_VIOLATION | Existing; same-parent/type mismatch, broken exact closure or recomputed hash mismatch. HASH_MISMATCH is design terminology, not currently an ErrorCode enum member; use provenance error until mapping is approved. |
| IDEMPOTENCY_CONFLICT / CONCURRENT_MODIFICATION | Existing; changed UUID/key/normalized material, obsolete consent head or exhausted bounded serialization/deadlock retry. |
| CONFLICT_OF_INTEREST | Existing; independent manuscript review/Decision/approval checks fail. |
| SUBMISSION_PACKAGE_INVALID | Correction 12 design code, absent enum; missing author contribution/current consent, manifest mismatch, wrong Publication or invalid gate. Proposed package-specific mapped category. |
| APPROVAL_PURPOSE_TARGET_COMMAND_INVALID / APPROVAL_GATE_FAILED / REJECTION_RECONSIDERATION_REQUIRED | Design/dependency categories; missing or unavailable manuscript approval tuple, blocker/basis failure or rejection shopping. Never substitute conclusion PROCEED. |
| GRANT_INVALID / GRANT_STALE | Design/dependency categories; wrong command/target/project, already used/expired/revoked grant or current eligibility/authority/consent loss. Expiry boundary uses fresh DB time. |

Do not add speculative AUTHOR_CONSENT_* error families or silently widen existing
handlers. Final absent-enum adoption belongs to authorized dependent implementation.
Wrong-project IDs deny without protected target details; exact transport policy
must align with the existing phase-specific adapters.

## 7. Concurrency, transactions and replay

Caller → Application Command/Service → Repository Port/UoW → Persistence Adapter
→ PostgreSQL 18.x. Synchronous I/O, one command equals one transaction; freeze
uses R3 SERIALIZABLE isolation. Domain imports no Session/FastAPI/Typer/Harness;
Human and Agent reach the same boundary, with HUMAN-only consent policy enforced
there. No external call or artifact upload is inside a lock-critical DB command;
evidence bytes must already be durably available, then verified for this effect.

Proposed common order: command-key/UUID coordination → project/purpose rejection
scope where needed → Publication parent → exact manuscript → package → sorted
authority/closure locks → grant/request rows → sorted Actor-ID consent chains →
manifest, receipt and event writes. Consent append and freeze both lock the same
package; automatic supersession locks the Publication and affected package rows
in stable order. These are proposed protocol requirements, not a ready-to-copy
lock implementation. Inventory all PR2-14/15/16, manuscript/Issue, role-revocation,
grant and consent writers, including normal-role SQL triggers, before freezing a
lock matrix. Preserve existing request→target→sorted SHARE-table coordination;
if a shared order cannot be established without inversion, correct the contract
before implementation, not through unbounded retries.

After every required wait, reread protected manuscript/placements, closure,
snapshot/contributions, all matching reviews/Issues, immutable Decision basis,
request/grant and current consent heads. Immediately before effect obtain fresh
PostgreSQL `clock_timestamp()` and recheck live principal/credential, effective
membership/roles, original approver authority and grant expiry. `now()`, transaction
start, caller clocks and cached lists are not final authority. A further wait
requires another reread/time check. At most three whole transaction attempts for
serialization/deadlock failure, each with fresh reads; lock timeout/error mapping
must be pinned before implementation. No failed freeze secretly commits a stale
event: resolve R2's first-observer persistence/rollback issue explicitly (§10).

If withdrawal commits first, freeze waits, observes WITHDRAWN and denies. If
freeze commits first, withdrawal waits and then preserves the frozen manifest,
appends withdrawal and stales current validity/unconsumed related grants atomically.
Concurrent consent successors yield one head; concurrent same-grant freezes
produce at most one package effect/receipt; different grants cannot freeze the
same package twice. Different package freezes serialize on Publication, preserving
all history and one proposed current FROZEN projection.

Creation/immutable-record command identity is its canonical UUID; compare complete
normalized caller fields, project and authenticated recorder against saved durable
material. Exact same-actor replay requires a live principal and current read
entitlement, returns saved history after loss of original write role or later
staleness, and writes nothing. Changing author order, contribution order, evidence,
prior consent or package context conflicts; corresponding/equal-group set order
alone does not change semantic identity. No new receipt schema is proposed for
these immutable creations. Package creation replay returns original projected
items, not a projection from a newer manuscript. Withdrawal's terminal-event
replay remains an explicit owner choice.

Completed freeze replay follows R3/R4/A21: same globally unique command_key,
authenticated actor/project, exact normalized scope/request hash and current
read entitlement return saved result DTO without rechecking present grant/effect
eligibility, recomputing a new expected manifest or executing freeze. Changed
hash conflicts; different key is a first-time command and cannot reuse a consumed
grant. Terminal grant without complete matching durable receipt is not success.
Rollback creates no effect/receipt; uncertain commit recovery uses the original
key, never a replacement approval. Historical receipt return does not assert
present package validity; expose that separately through authorized readback.

## 8. Architecture and adversarial tests to add later — NOT IMPLEMENTED

| Test group | Required evidence in separately authorized implementation |
| --- | --- |
| 05 §49 architecture obligations | Retain/test literature_source_not_evidence, search_result_not_evidence, citation_not_claim_support, strategy_does_not_import_persistence, adapter_does_not_write_db, no_storm_specific_core_schema, no_paperqa_specific_core_schema, discussion_not_canonical_science, manuscript_not_scientific_source_of_truth, review_does_not_mutate_target, decision_does_not_mutate_history, approval_does_not_override_invalid_fact, external_call_not_inside_long_db_transaction. Package paths must not circumvent them. |
| Package-specific boundaries | No actual SubmissionVersion/SubmissionRecord/ExternalEffect or venue send; Domain imports no adapters; no ORM DTOs; Agent output, manifest citation or author status cannot create support/authority. |
| Authorship/hash | Nonempty distinct HUMAN authors, exact one-based order; Agent contribution without HUMAN authorship; matching same-author contribution coverage; corresponding subset, no equal-group overlaps; set-order stability and author/contribution-order sensitivity; R2 independent golden preimages/digests. |
| Consent/immutability | Direct HUMAN identity only; evidence mandatory and frozen; one root/head, alternating withdrawal/regrant, no cycles/forks/wrong-package scope, immutable normal-role SQL UPDATE/DELETE; grants or role labels cannot consent. |
| Manifest/closure | Exact placement multiplicity/category/type, contiguous ordinals, no missing/extra items, exactly one current consent per author; wrong Publication/project/access, corrupted child/material/hash, DRAFT or INVALID/STALE closure deny; no Phase 1 hash changes. |
| Approval finite tuple | READY Publication, exact FROZEN manuscript, distinct PREPARE_SUBMISSION Decision/reviews/grant, mandatory current consent, HUMAN independence, blocker/rejection guard, bounded expiry; readiness/internal grant substitution fails. Missing dependencies fail closed. |
| PostgreSQL races | Actual lock waits for consent withdrawal versus freeze in both commit orders, two consent successors, same/different command keys/grants/packages, supersession and new review/zero-Issue INSERT/blocking Issue/upstream invalidation; no success through stale protected reads. |
| Temporal authorization | Credential/membership/role/approver/grant expiry while waiting, including second required wait; observe A22 timestamp inequalities and zero protected effects after denial. |
| Replay/failure | Restart/exact saved IDs and DTO, lost write authority with retained read role, withdrawn consent/expired grant historical replay, revoked credential/read role deny, changed scope/order/hash conflict; failures between hashes/event/receipt/consumption/supersession roll back all. |
| Lifecycle/validity | Never-frozen WITHDRAWN null hashes; frozen SUPERSEDED/WITHDRAWN preserved bytes; withdrawal immediately STALE and unconsumed grant events atomic; regrant never revives frozen binding/terminal grant; new package requires fresh consent/approval. |
| Migration/regression | Real PostgreSQL clean install/upgrade/catalog/normal-role constraints and downgrade preservation/refusal, one Alembic head; PR2-11–16 dependent suites and Phase 1 golden scientific workflow/historical/concurrency/failure regressions. No SQLite substitution. |

Race evidence records separate backend PIDs, pg_stat_activity/pg_blocking_pids/
pg_locks wait witnesses, actual commit order, final protected rereads and persisted
package/manifest/consent/event/receipt counts. Sleeps alone are not race proof.
Formal package history remains exactly reproducible after source correction,
role revocation, restart and newer manuscript/package creation.

## 9. Dependencies, acceptance criteria and stop boundary

| Dependency | Required readiness / effect on PR2-17 |
| --- | --- |
| PR2-00 identity and effective authority | Live trusted principal, project membership/read entitlement, direct HUMAN identity and advancing DB-time checks; no bare actor header. |
| PR2-11 conclusion and Phase 1 provenance | Exact currently valid scientific closure, including independent Phase 2 literature support; existing golden semantics untouched. |
| PR2-12/13 publication and placements | Exact document/placement trace plus a separately contracted manuscript freeze and sealed placement hash; draft creation/trace alone is insufficient. |
| PR2-14 review and PR2-15 Decision/RevisionAction | Manuscript review and distinct READY_FOR_SUBMISSION/PREPARE_SUBMISSION Decisions need separate contracts; current minimal PROCEED and approved RevisionAction recording do not supply them or resolve blocking Issues. |
| Approved PR2-16 base | Its initial internal request/decision/grant slice supplies no manuscript tuple, READY transition or grant consumption. Those paths and grant lifecycle/lock participation must be separately approved and verified before freeze. |
| PR2-17 internal ordering | Contribution → immutable snapshot → exact PREPARED package → direct consent/evidence → preview → valid preparation grant consumption/freeze. Contribution/snapshot exist before package, consent before package hash; no circular scientific hash. |
| Later work | PR2-18 novelty is not inferred as a new freeze prerequisite; PR2-19/20 extend E2E/hardening evidence. Venue connectors and actual send remain optional later extensions. |

Draft acceptance: exact requested DRAFT status, local links resolve, only this
proposal added, no authoritative/executable/schema/test edits, no commit/branch/
push, inherited rules distinguished from proposed choices and owner questions.
Verification reports commands/counts and blocked checks without turning setup
failure into PASS. This is not acceptance evidence for unimplemented commands.

Before contract freeze: resolve §10, reconcile approved base implementations,
review 01/02/03/05/08/12 and focused corrections for consistency, pin DTO/errors/
manifest/authority/lock matrix and bounded schema choices, and obtain independent
review with no open P0 BLOCKER or P1 MAJOR. No automatic IMPLEMENTATION_GO follows.

Before full future PR2-17 acceptance: every in-scope §8 unit/architecture/real-PG
constraint/migration/command/closure/race/failure/replay check passes; dependent
manuscript review/Decision/approval/READY paths and atomic consumption are accepted;
exact complete package freeze and consent withdrawal trace is demonstrated;
Phase 1 golden regressions pass. If only preparation/authorship is authorized,
label it a bounded slice with freeze BLOCKED, not full PR2-17/M4 gate success.
After this documentation task, STOP; no dependency implementation is authorized.

## 10. Open questions for the owner — conservative recommended answers

| Question | Recommended answer and consequence |
| --- | --- |
| Full freeze in PR2-17 or preparation-only slice pending manuscript governance? | Approve this contract's full design but authorize a preparation-only slice until manuscript freeze/review, both manuscript Decision purposes, READY transition and preparation consumption are separately accepted. Never bypass with PROCEED/internal grant or implement other PRs here. |
| Can PREPARED material be edited after consent? | Fix manuscript/snapshot/non-consent manifest at creation in the first slice; new context means new package and fresh consent. A later editing contract must explicitly invalidate prior consent and prove capture-context binding; ID-only consent is insufficient for silent mutation. |
| Is manifest a set or placement-occurrence projection; what about other artifact roles? | Preserve exact direct occurrence multiplicity and deterministically derive per-category ordinals as §3.1; verify transitive inputs through closure. Fail closed on uncontracted artifact roles; freeze explicit category mapping before implementation, no generic catch-all. |
| Must there be corresponding authors and how are equal groups handled? | Require at least one HUMAN corresponding author for a submission-intended package; retain R2 subset/nonoverlap/set ordering. This minimum is a proposed gate, not an inherited hash requirement. |
| How are consent authors onboarded/offboarded? | Require verified HUMAN identity and current project read entitlement; do not require RESEARCHER to consent/withdraw. Provide a separately contracted timely withdrawal/offboarding procedure before production use so role removal cannot trap consent; no implicit public/representative bypass. |
| Which contribution role enum and DTO bounds are approved? | Pin a small closed vocabulary against existing artifact-role/contracts before implementation, with no taxonomy service; approve conservative bounds in §4. No new enum literal is inferred from free text. |
| Are contribution/snapshot choices an AuthorshipDecision? | No. Record attributable preparation and direct consent only, no adjudication/appeal or new schema. If a formal AuthorshipDecision is required, separately contract it and keep this path unavailable until then. |
| What is the current-package policy and withdrawal replay identity? | One FROZEN package per Publication, serialized automatic supersession with no current pointer. For minimal OWNER withdrawal reuse exact package/terminal event with same actor/reason replay; if multiple lifecycle requests need distinct keys, approve typed existing-event fields/receipt needs through architecture review first. |
| How broad is a consent withdrawal's related-grant scope? | Conservatively stale all unconsumed PREPARE_SUBMISSION grants for the exact manuscript/project affected by that package, under coordinated locks; preserve consumed history. Freeze a concrete request/package resolver, since grant itself is manuscript-scoped and has no generic package locator. |
| How are stale/expired events committed when consumption fails? | Use a separately contracted lifecycle evaluation command or explicitly approved transaction exception; never silently commit partial events after raising a failed-freeze error. Effective denial and read-derived STALE must work immediately without a sweeper. |
| What if existing blockers or historical rejection need recovery? | Depend on separately approved disposition/reconsideration contracts and new exact review/Decision/approval trace; RevisionAction documents completion only. Do not alter old Issues/reviews or clone around project/purpose rejection guards. |
| Are error/replay policy and schema refinements admitted? | Approve closed mappings and same-actor/current-read replay explicitly; retain R2/R3 literal material and A21 historical consumption semantics. Review composite/partial unique/normal-role guards and any extra fields before migration authorization. |

## 11. Documentation-task verification

Verification results below describe this draft change and current baseline checks,
not PR2-17 implementation tests. Future §8 tests remain NOT IMPLEMENTED/NOT RUN.
All retained scratch/cache paths are ignored repository-local `tmp/` or `.venv/`.

Executed on **2026-10-13**. Environment setup attempts:

```bash
uv --cache-dir tmp/pr2-17-verification/uv-cache sync --frozen --offline
uv --cache-dir tmp/pr2-17-verification/uv-cache sync --frozen
```

Offline sync exits 1: locked Ruff 0.12.12 is absent from the repository-local cache.
Online sync exits 2: locked MarkupSafe 3.0.3 download fails after three retries
because files.pythonhosted.org DNS resolution is unavailable. Neither dependency
source nor lockfile was changed. `uv run --no-sync` created the ignored local
`.venv`; the required executables remain unavailable.

Exact baseline check commands:

```bash
uv --cache-dir tmp/pr2-17-verification/uv-cache run --offline --no-sync pytest -o addopts='' -ra tests/unit tests/architecture
uv --cache-dir tmp/pr2-17-verification/uv-cache run --offline --no-sync ruff check .
uv --cache-dir tmp/pr2-17-verification/uv-cache run --offline --no-sync ruff format --check .
uv --cache-dir tmp/pr2-17-verification/uv-cache run --offline --no-sync pyright
```

Each exits 2, failed to spawn its absent executable. **BLOCKED:** pytest collected
no tests: **0 passed, 0 failed assertions, 0 skipped, 0 setup errors**; there is
one command startup failure, not a successful empty suite. Ruff lint/format and
Pyright processed **0 files** and produced no checking result. No historical
PR2-15/16 counts are reused as this task's evidence. An earlier redirected unit
invocation failed before uv execution because its scratch parent did not yet
exist; the explicit invocation above was retried after setup.

PostgreSQL readiness and local disposable-cluster initialization attempts:

```bash
pg_isready -h 127.0.0.1 -p 5432
pg_isready -h 127.0.0.1 -p 55440
/opt/homebrew/opt/postgresql@18/bin/initdb -D tmp/pr2-17-verification/pgdata -U pr217_admin -A trust --no-locale
```

Both readiness commands exit 2, **no response**. initdb exits 1 at `shmget` with
`could not create shared memory segment: Operation not permitted`; it removes its
incomplete cluster. No PostgreSQL server was started or persistent scientific
data changed. Approval escalation is unavailable in this session.

The dependent scientific/publication/review/Decision integration and Phase 1
E2E regression invocation was nevertheless attempted explicitly:

```bash
RB_TEST_ADMIN_URL=postgresql+psycopg://pr217_admin@127.0.0.1:55479/postgres uv --cache-dir tmp/pr2-17-verification/uv-cache run --offline --no-sync pytest -o addopts='' -ra --tb=short tests/integration/phase2/test_pr2_1[1-5]*.py tests/e2e
```

Exit 2, absent pytest executable: **0 passed, 0 failed assertions, 0 skipped,
0 setup errors; 1 command startup failure**. **BLOCKED, not PASS:** no integration,
constraint, migration or golden assertion executed. A preceding invocation naming
thirteen dependency test files individually plus tests/e2e had the same exit 2
startup failure; the broader glob above includes those files. No PR2-16 approval
suite exists in this inspected baseline. On a permitted disposable PostgreSQL
18.x host with locked tools installed, rerun these suites using their documented
DB selectors (including DATABASE_URL for Phase 1 E2E); this draft does not claim
baseline integration success or unimplemented PR2-17 test coverage.

Exact documentation verification command:

```bash
.venv/bin/python - <<'PY'
from pathlib import Path
import re
import subprocess
p = Path('docs/proposals/PR2-17_Submission_Authorship_Contract_DRAFT.md')
s = p.read_text()
links = re.findall(r'\]\(([^)]+)\)', s)
assert all((p.parent / target).is_file() for target in links)
assert '**Status: DRAFT — awaiting owner approval; not authorized for implementation**' in s
assert subprocess.check_output(['git', 'status', '--short'], text=True).splitlines() == [f'?? {p.as_posix()}']
assert all(line == line.rstrip() for line in s.splitlines())
assert len(re.findall(r'^## [0-9]+\.', s, re.M)) == 11
assert len(re.findall(r'^```', s, re.M)) % 2 == 0
print(f'6 checks passed: {len(links)} local links resolve; exact status; sole draft change; no trailing whitespace; 11 sections; balanced fences')
PY
git diff --check
```

Exit 0: **6 documentation checks passed, 0 failed; 20 local links resolve**.
`git diff --check` exits 0. The explicit content check covers this untracked
proposal, which ordinary git diff does not include. Source/spec consistency was
reviewed manually; these six mechanical checks do not establish owner approval
or independent architecture review. Only the requested proposal is in the
tracked/untracked nonignored change set; no commit, push or branch was created.
