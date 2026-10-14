# PR2-17 SubmissionVersion + Minimal Authorship Contract — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

**Scope:** documentation proposal only: package manifest, AuthorshipSnapshot and
basic AuthorConsent, with no ExternalEffect. This is not an architecture freeze,
ADR, execution pack, migration authorization or PR2-17 acceptance declaration.
Owner approval of a contract and separate implementation authorization are distinct.

## 1. Purpose, authority and current baseline

Shorthand is defined in §10. Draft decisions are fixed in §11; buildable scope is §12.1.

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

The full design covers contributions, immutable authorship snapshots, exact
PREPARED packages, direct-author consent chains, exact history and validity.
Freeze and withdrawal require additional contracted Application commands.
Freeze is **unavailable until its separately approved dependencies exist** (§9).
The first buildable slice is preparation foundation S1: only `record_contribution`,
`create_authorship_snapshot`, `get_contribution` and `get_authorship_snapshot`.
Package preparation S2 additionally needs the manuscript-freeze contract; consent
withdrawal also needs atomic grant lifecycle support. These are not S1 commands.
Neither slice can claim full PR2-17 acceptance. See §12.1 for every missing contract.

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
4. **Immutable consent context.** The package-preparation slice fixes manuscript, snapshot
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
    WITHDRAWN. No reverse transitions. One FROZEN package per Publication
    is enforced under parent coordination; no current-package pointer is added.
    Never-frozen withdrawal retains null hashes/frozen_at; frozen withdrawal and
    supersession preserve them. Supersession alone is navigation history, not
    deterministic invalidity; historical exact dependencies still resolve.

### 3.1 Manifest projection and hash ordering

Use the six R2 categories and one concrete nonnull target per row:

| Category | Exact target | Draft completeness/ordinal rule |
| --- | --- | --- |
| FIGURE / TABLE | ArtifactVersion | Exact figure/table placement occurrences, separately per category. |
| CITATION | SourceVersion | Exact citation placement occurrences; citation alone adds no scientific support. |
| CLAIM | ClaimVersion | Exact direct Claim placement occurrences. |
| CONCLUSION | ScientificConclusionVersion | Exact direct conclusion placement occurrences; transitive inputs are verified through closure, not duplicated as direct placements. |
| AUTHOR_CONSENT | AuthorConsent | Exactly one current GRANTED head for each snapshot author; no extra author, package or scope. Order follows authored author order, with zero-based manifest ordinals. |

Non-consent occurrences are projected from the sealed manuscript, sorted within
category by `(section_id, placement ordinal)` under its accepted placement
ordering, then assigned contiguous 0..N-1 category ordinals. Preserve repeated
placements of the same target; do not silently deduplicate or append extra
unplaced scientific facts. Manuscript and package sets must agree in multiplicity
and exact target IDs/hashes. Artifact role OTHER fails closed with SUBMISSION_PACKAGE_INVALID; no catch-all
category is invented. FIGURE maps to FIGURE and TABLE maps to TABLE. Document artifact is
already reached through ManuscriptVersion, not a duplicate manifest item.

The occurrence mapping is a **proposed refinement**, not an existing frozen
contract. Snapshot/manifest hashes use exactly R2 15 (§5), not this prose as a new
payload schema. Full transitive scientific provenance, including separate Phase 2
literature support, remains verified without altering Phase 1 hash material.

## 4. Proposed commands, closed DTOs and readback

All DTOs are immutable and closed. Reject extra keys, wrong UUID types, duplicate
set members, unsupported enum literals, blank/invalid Unicode and caller-supplied
status, authenticated-actor, timestamp or effective-role assertions. Only the
explicit attributed actor and expected manifest hash fields are accepted. Text uses R2 NFC normalization
with meaningful whitespace preserved. Draft limits: required statements and
reasons 1..10,000 characters after NFC, at most 100 authors and 10,000 manifest
occurrences. The closed role vocabulary and remaining bounds are fixed in §11.2. Actors, effective times, hashes and version numbers are derived.

| Command | Caller inputs | Atomic result / required role |
| --- | --- | --- |
| `RecordContributionCommand` / `record_contribution` | `id`, `project_id`, `publication_id`, `actor_id` (attributed contributor), `contribution_role`, `contribution_statement` | Immutable ContributionRecord/hash; authenticated active RESEARCHER or OWNER is recorded_by. Attribution is not consent. |
| `CreateAuthorshipSnapshotCommand` / `create_authorship_snapshot` | `id`, project/publication IDs, ordered `author_ids`, set `corresponding_author_ids`, set of equal-author groups, ordered `contribution_record_ids` | One immutable snapshot/hash plus sealed typed relations; RESEARCHER or OWNER, all §3 authorship checks. |
| `PrepareSubmissionCommand` / `prepare_submission` | `id` (package UUID), project/publication IDs, exact manuscript/snapshot IDs | One PREPARED row/version number and creation event with server-projected non-consent items; RESEARCHER or OWNER. Require already FROZEN valid manuscript/snapshot; no grant consumed. |
| `RecordAuthorConsentCommand` / `record_author_consent` | `id`, `project_id`, `prepared_submission_version_id`, `consent_state`, `consent_scope=PREPARED_PACKAGE`, `evidence_artifact_version_id`, `prior_consent_id|null` | One immutable chain append/hash; actor comes only from verified HUMAN context matching a snapshot author. Root/regrant only PREPARED; withdrawal also available after freeze/supersession/package withdrawal. |
| `FreezePreparedSubmissionCommand` / `freeze_prepared_submission` | `command_key`, `project_id`, `grant_id`, `prepared_submission_version_id`, `expected_package_manifest_hash`, nonempty duplicate-free `checked_review_ids` | RESEARCHER or OWNER, dependency-gated; §3 atomic freeze and R3 receipt whose concrete package result equals input ID. No free-form effect argument. |
| `WithdrawPreparedSubmissionCommand` / `withdraw_prepared_submission` | package/project IDs, nonblank `reason` | OWNER, allowed §3 lifecycle states; append event and revoke current eligibility without erasing material; repeat same withdrawal with identical reason/actor returns saved terminal event, differing retry conflicts. This is the draft replay decision (§11). |
| Exact-ID history / `preview_prepared_submission` queries | `project_id`, exact record/package ID | Authorized typed readback; preview recomputes candidate manifest with current consent heads, identifies missing consent/dependencies and returns noncanonical candidate digest. No writes or grant issuance. |

Consent access requires live bound principal and ACTIVE project membership
with any effective read role (OWNER/RESEARCHER/REVIEWER/VIEWER/APPROVER), in addition
to exact HUMAN author identity. It does not require a writer role merely to
withdraw one's consent. An author with no current project entitlement cannot
use this path; a separately contracted withdrawal/offboarding procedure is required before production use (§12.1).
No public or on-behalf-of withdrawal endpoint is implied.

Read DTOs expose exact IDs, parent/project, authored ordering and contribution
refs/hashes; package state, nullable draft hashes, frozen manifest refs/hashes;
consent chain history and current heads; immutable actors/DB times and lifecycle
events; grant/consumption references when present. Report frozen historical facts
separately from derived `current_validity` and bounded reason codes. The
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
indexed FK paths, RESTRICT and normal-role SQL enforcement follow 13; the DDL sketch in §12.2 remains design-only. Additional semantic fields require
separate design/ADR review; implementing this sketch requires owner authorization.

| Table family | Proposed material and database enforcement |
| --- | --- |
| `contribution_records` | UUID PK; Publication/actor/recorded_by concrete FKs, bounded role/statement and immutable content_hash/hash_scheme. No version row; frozen snapshots select exact contribution records. |
| `authorship_snapshots` and four `authorship_snapshot_*` relation tables | Snapshot Publication FK and own hash, unique `(publication_id,id)`; author, corresponding, equal-group and contribution rows are sole canonical collections. Enforce author ordinal/actor uniqueness, contiguous author/contribution order, subset/nonoverlap and same-author contribution coverage through sealed-set/deferred typed guards. No JSON ID arrays. |
| `prepared_submission_versions` | Publication parent/version_number, exact manuscript and snapshot, lifecycle, nullable package_manifest_hash/content_hash/frozen_at. Unique publication+number and publication+id; composite same-Publication manuscript/snapshot FKs. Partial unique FROZEN per Publication; no current pointer. Hash-null/frozen-state checks distinguish never-frozen and formerly frozen WITHDRAWN. |
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
conflicts or foreign history. Use the single mapping table in §11.3. Existing
mappings are copied from the API and CLI adapters, including provenance CLI exit 5
and conflict-of-interest HTTP 403. New mappings are draft decisions, not claims
that enum members already exist. Diagnostics are bounded and sanitized.

HASH_MISMATCH is explanatory terminology only: return
PROVENANCE_CLOSURE_VIOLATION for recomputed hash mismatch. Do not add speculative
AUTHOR_CONSENT_* families. Wrong-project IDs return FORBIDDEN without target
details. Missing IDs within the authorized project return NOT_FOUND.

## 7. Concurrency, transactions and replay

Caller → Application Command/Service → Repository Port/UoW → Persistence Adapter
→ PostgreSQL 18.x. Synchronous I/O, one command equals one transaction; freeze
uses R3 SERIALIZABLE isolation. Domain imports no Session/FastAPI/Typer/Harness;
Human and Agent reach the same boundary, with HUMAN-only consent policy enforced
there. No external call or artifact upload is inside a lock-critical DB command;
evidence bytes must already be durably available, then verified for this effect.

The exact S1 command lock sequences are in §12.4. They retain the existing
request → target → sorted SHARE-table coordination pattern. Package, consent,
withdrawal and freeze are outside S1; their future lock contracts must include
all writers listed in §12.1. No engineer may assemble a production freeze order
from a generic list in this document. Those paths stay unavailable until their
missing contracts specify a compatible per-command order.

After every required wait, reread protected manuscript/placements, closure,
snapshot/contributions, all matching reviews/Issues, immutable Decision basis,
request/grant and current consent heads. Immediately before effect obtain fresh
PostgreSQL `clock_timestamp()` and recheck live principal/credential, effective
membership/roles, original approver authority and grant expiry. `now()`, transaction
start, caller clocks and cached lists are not final authority. A further wait
requires another reread/time check. At most three whole transaction attempts for
serialization/deadlock failure, each with fresh reads. Set transaction-local
`lock_timeout = '10s'` and `statement_timeout = '30s'`.
Only SQLSTATE 40001/40P01 retry, for at most three total attempts. SQLSTATE
55P03/57014 abort without retry and map to CONCURRENT_MODIFICATION (409/4).
The persistence boundary retains a private retryable flag for 40001/40P01;
Application must not retry merely because the public code is CONCURRENT_MODIFICATION.
No SQLSTATE or driver exception is disclosed. Other database failures use the
existing sanitized UoW path. No failed freeze
commits a stale event. A separate lifecycle-evaluation contract owns persistent
STALE/EXPIRED events (§12.1); effective denial never waits for that evaluator.

If withdrawal commits first, freeze waits, observes WITHDRAWN and denies. If
freeze commits first, withdrawal waits and then preserves the frozen manifest,
appends withdrawal and stales current validity/unconsumed related grants atomically.
Concurrent consent successors yield one head; concurrent same-grant freezes
produce at most one package effect/receipt; different grants cannot freeze the
same package twice. Different package freezes serialize on Publication, preserving
all history and one current FROZEN projection.

Creation/immutable-record command identity is its canonical UUID; compare complete
normalized caller fields, project and authenticated recorder against saved durable
material. Exact same-actor replay requires a live principal and current read
entitlement, returns saved history after loss of original write role or later
staleness, and writes nothing. Changing author order, contribution order, evidence,
prior consent or package context conflicts; corresponding/equal-group set order
alone does not change semantic identity. No new receipt schema is proposed for
these immutable creations. Package creation replay returns original projected
items, not a projection from a newer manuscript. Withdrawal's terminal-event
replay uses exact package, authenticated actor and NFC-normalized reason; an
identical terminal request returns its saved event, while a changed reason or
actor conflicts (after the nondisclosure authorization check).

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
proposal changed, no authoritative/executable/schema/test edits, no commit/branch/
push, inherited rules distinguished from proposed choices and owner questions.
Verification reports commands/counts and blocked checks without turning setup
failure into PASS. This is not acceptance evidence for unimplemented commands.

Before contract freeze: obtain owner ratification of §11, reconcile the approved
base implementations and review 01/02/03/05/08/12 and focused corrections for
consistency. Require independent review with no open P0 BLOCKER or P1 MAJOR.
The choices below are settled within this draft; owner approval and a separate
execution pack remain necessary. No automatic implementation authorization follows.

Before full future PR2-17 acceptance: every in-scope §8 unit/architecture/real-PG
constraint/migration/command/closure/race/failure/replay check passes; dependent
manuscript review/Decision/approval/READY paths and atomic consumption are accepted;
exact complete package freeze and consent withdrawal trace is demonstrated;
Phase 1 golden regressions pass. If only preparation/authorship is authorized,
label it a bounded slice with freeze BLOCKED, not full PR2-17/M4 gate success.
After this documentation task, STOP; no dependency implementation is authorized.

## 10. Glossary

Document numbers below refer to the linked authority table in §1. This glossary
also defines the shorthand used in the implementation guide.

| Term | Meaning and governing document |
| --- | --- |
| ResearchBase / canonical fact | The repository's scientific system and its single authoritative persisted fact; System Architecture 01 §§3, 9–13. |
| PR / PR2-nn | Pull request / Phase 2 work package number, not an authorization; Phase 2 Specification 05 §48. |
| Phase 1 / Phase 2 / Phase 3 / Phase 4 | Architecture delivery stages, not interchangeable feature permissions; Cross-Phase Contracts 08. |
| S1 / S2 | This draft's preparation foundation / prerequisite-gated package preparation slices; §§2, 12.1 here. |
| R1 / R2 | First design correction / second correction round; Addendum 02 A17/A18 and focused companions 12–17. |
| R3 / R4 | Targeted third correction / temporal fourth correction; Addendum 02 A19/A20 and companions 18/19. |
| A-numbers | Numbered amendments in Correction Addendum 02, not issue or command IDs. |
| A13 | Requires technology decision gates before their dependent implementation; Addendum 02 A13. |
| A14 | Distinguishes operational tool effects from governed ExternalEffect; Addendum 02 A14. |
| A17 | Incorporates Phase 2 corrections, including prepared-versus-sent naming; Addendum 02 A17. |
| A18 | Admits bounded R2 schema and sets focused-companion precedence; Addendum 02 A18. |
| A19 | Admits the named R3 corrections, including consumption receipts; Addendum 02 A19. |
| A20 | Applies R4 advancing-time authorization without adding schema; Addendum 02 A20. |
| A21 | Requires current read entitlement for completed receipt replay; Addendum 02 A21. |
| A22 | Defines legacy-state and observable cross-expiry evidence requirements; Addendum 02 A22. |
| A23 | Bounds the initial INTERNAL_SCIENTIFIC_RELEASE/PROCEED Decision command; Addendum 02 A23 and companion 20. |
| TEMP-AUTH-01 | Final authorization uses advancing DB time after all required waits; Temporal R4 19 §1. |
| I-ref / I(T) / idref | Typed identity reference `{type,id}` with no hash; Hash R2 15 common rules. |
| R-ref / R(T) / ref | Typed exact immutable reference `{type,id,content_hash}`; Hash R2 15 common rules. |
| Sealed set | Typed child rows committed with their immutable parent; no later insert, update or delete may change the set; Field Contract 13 and Governance R2 17 §3. |
| Closure | All exact transitive frozen scientific dependencies and their verified bindings; Cross-Phase Contracts 08 §9 and Phase 2 Specification 05 §34. |
| Manifest / occurrence | Typed package items / one direct placement, including repeated targets; Hash R2 15 and §3.1 here. |
| PREPARED / FROZEN / SUPERSEDED / WITHDRAWN | Package lifecycle values; Field Contract 13; SUPERSEDED records navigation, not automatic invalidity. |
| GRANTED / WITHDRAWN | Consent chain values; Governance R2 17 §3; consent WITHDRAWN is distinct from package WITHDRAWN. |
| VALID / INVALID / STALE / NOT_FROZEN | Derived validity values; Cross-Phase Contracts 08 and §11.2 here; never saved as a second scientific fact. |
| HUMAN / Agent | Actor kinds with distinct direct-consent eligibility; System Architecture 01 and Governance R2 17 §3. |
| OWNER / RESEARCHER / REVIEWER / VIEWER / APPROVER | Effective project role literals, not authorship or substitute consent; Identity R2 16 and Governance R2 17 §1. |
| READY / INTERNAL_REVIEW | Publication lifecycle states; Field Contract 13 and Governance R2 17 §1. |
| PREPARED_PACKAGE | The sole consent scope, acknowledging exact preparation only; Governance R2 17 §3. |
| PREPARE_SUBMISSION / READY_FOR_SUBMISSION | Separate Decision/approval purposes for freezing a package / transitioning Publication to READY; Governance R2 17 §1. |
| INTERNAL_SCIENTIFIC_RELEASE / PROCEED | Initial scientific Decision purpose/value; companion 20; neither authorizes manuscript or package transitions. |
| FREEZE_PREPARED_SUBMISSION | The only consuming command for a PREPARE_SUBMISSION grant; Governance R2 17 §1. |
| Grant / receipt / replay | Single-use authority / immutable completed consumption result / returning that saved result; Governance R2 17, R3 18 §5 and A21. |
| ExternalEffect | Governed action outside ResearchBase, including actual sending; Addendum 02 A14/A17; absent here. |
| DTO | Immutable data transfer object crossing the Application boundary, never an ORM row; Cross-Phase Contracts 08. |
| UoW | Unit of Work owning one command transaction; System Architecture 01 and Cross-Phase Contracts 08. |
| DB / SQL / DDL | Database / Structured Query Language / data-definition statements; Field Contract 13 and §12.2 here. |
| PK / FK / XOR | Primary key / foreign key / exactly one allowed concrete target; Field Contract 13. |
| NULL / NOT NULL | SQL absence / mandatory value; Field Contract 13. |
| SHARE / UPDATE | PostgreSQL lock modes, distinct from scientific mutation permission; PR2-15 matrix and §12.4 here. |
| B-tree | PostgreSQL ordered index structure required for FK access paths; Field Contract 13. |
| BASE / HASH | Exact shared-column DDL expansion notation, not database objects; §12.2 here. |
| CHAR / VARCHAR / TEXT / INTEGER / TIMESTAMPTZ | Fixed text / bounded text / text / integer / timestamp with time zone SQL types; Field Contract 13. |
| SERIALIZABLE / SQLSTATE | PostgreSQL serializable isolation / database error identifier; R3 18 §5 and §7 here. |
| UUID / ID | Universally unique identifier / record identity; Field Contract 13 and existing foundation IDs. |
| NUL | Zero code point, forbidden in command text and PostgreSQL text values; §11.2 here. |
| NFC / Unicode / UTF-8 | Canonical Unicode composition / character standard / byte encoding; Hash R2 15 common rules. |
| JSON / JSONB / canonical-json-v1 | JSON text / PostgreSQL binary JSON / frozen deterministic serialization scheme; Hash R2 15. |
| SHA-256 / sha256-cjson-v1 | Digest algorithm / hash of canonical-json-v1 UTF-8 bytes; Hash R2 15. |
| API / HTTP / CLI | Application programming interface / Hypertext Transfer Protocol / command-line interface; Cross-Phase Contracts 08 and adapter mappings in §11.3. |
| ORM / Session | Object-relational mapping / SQLAlchemy transaction object, confined to persistence; System Architecture 01. |
| ADR / TDG-2 | Architecture Decision Record / Phase 2 technology decision gate; Addendum 02 A13/A18. |
| CRediT / ORCID / PKI | Contributor Roles Taxonomy / researcher identifier / public-key infrastructure; System Architecture 01 authorship and §2 exclusions here. |
| P0 / P1 / P2 / P3 | BLOCKER / MAJOR / MINOR / SUGGESTION review severity; repository AGENTS.md §10. |
| M4 / E2E / PG | Phase 2 milestone 4 / end-to-end test / PostgreSQL; Phase 2 Specification 05 and §8 here. |
| PID / pg_locks / pg_blocking_pids | Backend process identifier / lock catalog / blocker lookup used as race witnesses; Temporal R4 19 §5 and §8 here. |
| Golden vector / preimage | Independent expected digest / exact serialized bytes before hashing; Hash R2 15 appendix. |
| HASH_MISMATCH | Design description mapped to PROVENANCE_CLOSURE_VIOLATION, not a new code; §11.3 here. |

## 11. Decisions taken in this draft

These choices adopt all former recommended answers. They govern this draft's
body and guide. The owner may overrule them through a revised contract; an
engineer must not choose alternatives during implementation. None authorizes code.

### 11.1 Scope, lifecycle and replay decisions

| Former open question | Draft decision |
| --- | --- |
| Full freeze or preparation only? | Preparation only. S1 records contributions/snapshots and reads them. S2 needs manuscript freeze. Six separate freeze prerequisites are listed in §12.1. No internal grant or PROCEED substitution. |
| Edit PREPARED material? | Never in this design. Manuscript, snapshot and non-consent occurrences are fixed at creation. Changed context requires a new package and fresh consent. |
| Manifest set or occurrences; other roles? | Preserve direct placement multiplicity. Sort by section ID using NFC Unicode code-point order, then placement ordinal, separately within category. FIGURE→FIGURE, TABLE→TABLE; OTHER denies. Transitive inputs stay in closure. |
| Corresponding authors and equal groups? | Require 1..100 HUMAN corresponding authors, all in the 1..100 author list. Equal groups contain at least two distinct authors; groups do not overlap. R2 set hashing remains unchanged. |
| Onboarding/offboarding? | Direct verified HUMAN with current project read entitlement, no writer role required. A withdrawal/offboarding contract is mandatory before production consent use. No representative or public bypass. |
| Role enum and bounds? | Adopt the closed values and all bounds in §11.2. This is a local contribution vocabulary, not a taxonomy service. |
| Is this AuthorshipDecision? | No adjudication, appeal or AuthorshipDecision schema. If later required, a separate contract must authorize it. |
| Current package and withdrawal replay? | One FROZEN package per Publication; newer freeze atomically supersedes the older one. No pointer. OWNER withdrawal replay is exact package + actor + normalized reason against its terminal event; differing material conflicts. |
| Related-grant scope? | All unused PREPARE_SUBMISSION grants for the package's exact manuscript and project; use the concrete join below. This is deferred with consent withdrawal, not approximated in S1. |
| Persist stale/expired events on failed consumption? | Separate lifecycle-evaluation command, with its own approved contract. A denied freeze rolls back every write. Read-derived STALE and effective expiry deny immediately without waiting for stored events. |
| Blocker/rejection recovery? | Separate Issue disposition and rejection reconsideration contracts, with fresh exact review/Decision/approval trace. RevisionAction alone does not clear a blocker or rewrite history. |
| Error/replay/schema admission? | Use §11.3; same-actor immutable-creation replay requires current read entitlement, not the original write role. Completed consumption replay follows A21. Admit only the existing registered tables and typed keys in §12.2, subject to owner review and migration authorization. |

The future related-grant resolver is exact and contains no package locator JSON:

```sql
SELECT g.id
FROM prepared_submission_versions p
JOIN publications pub ON pub.id = p.publication_id
JOIN approval_requests r
  ON r.manuscript_version_id = p.manuscript_version_id
 AND r.project_id = pub.project_id
 AND r.approval_purpose = 'PREPARE_SUBMISSION'
JOIN approval_decisions d ON d.approval_request_id = r.id
JOIN approval_grants g ON g.approval_decision_id = d.id
WHERE p.id = :package_id AND pub.project_id = :project_id
  AND g.project_id = pub.project_id AND g.purpose = 'PREPARE_SUBMISSION'
  AND g.status = 'ACTIVE'
  AND NOT EXISTS (SELECT 1 FROM approval_grant_consumptions c WHERE c.grant_id = g.id)
ORDER BY g.id;
```

Expiry does not permit consumption even if status still says ACTIVE. Withdrawal
must include those ACTIVE rows in atomic staling, without rewriting CONSUMED or
other terminal grants. The missing lifecycle contract must coordinate request,
new-grant and withdrawal writers against insertion phantoms and lock these IDs
in order. This resolver defines scope; it does not enable withdrawal in S1.

### 11.2 DTO fields, types, limits and enums

Use frozen dataclasses with slots in Application, as in `application/decision.py`.
Constructors enforce exact UUID values, tuple structure, closed fields and enum
membership. Transport adapters parse canonical UUID strings before construction.
`principal: VerifiedPrincipal` is a separate service argument, never caller JSON.
`project_id` is required even where Publication supplies the canonical Project.
Every field below is required unless an explicit default is shown.

```python
ContributionRole = Literal[
    "CONCEPTUALIZATION", "INVESTIGATION", "ANALYSIS", "SOFTWARE", "WRITING", "REVIEW"
]
ConsentState = Literal["GRANTED", "WITHDRAWN"]
ConsentScope = Literal["PREPARED_PACKAGE"]
PackageStatus = Literal["PREPARED", "FROZEN", "SUPERSEDED", "WITHDRAWN"]
Category = Literal["FIGURE", "TABLE", "CITATION", "CLAIM", "CONCLUSION", "AUTHOR_CONSENT"]
Validity = Literal["NOT_FROZEN", "VALID", "INVALID", "STALE"]
ValidityReason = Literal[
    "NOT_FROZEN", "DEPENDENCY_UNAVAILABLE", "CONSENT_MISSING", "CONSENT_WITHDRAWN",
    "UPSTREAM_INVALID", "UPSTREAM_STALE", "PACKAGE_WITHDRAWN", "HASH_MISMATCH"
]
# UUID: uuid.UUID; datetime: timezone-aware datetime.datetime; Literal: typing.Literal.
# These are field declarations for separate frozen command dataclasses, not one DTO.
RecordContributionCommand:
    id: UUID
    project_id: UUID
    publication_id: UUID
    actor_id: UUID
    contribution_role: ContributionRole
    contribution_statement: str
CreateAuthorshipSnapshotCommand:
    id: UUID
    project_id: UUID
    publication_id: UUID
    author_ids: tuple[UUID, ...]
    corresponding_author_ids: tuple[UUID, ...]
    equal_contribution_groups: tuple[tuple[UUID, ...], ...]
    contribution_record_ids: tuple[UUID, ...]
PrepareSubmissionCommand:
    id: UUID
    project_id: UUID
    publication_id: UUID
    manuscript_version_id: UUID
    authorship_snapshot_id: UUID
RecordAuthorConsentCommand:
    id: UUID
    project_id: UUID
    prepared_submission_version_id: UUID
    consent_state: ConsentState
    evidence_artifact_version_id: UUID
    prior_consent_id: UUID | None = None
    consent_scope: ConsentScope = "PREPARED_PACKAGE"
FreezePreparedSubmissionCommand:
    command_key: UUID
    project_id: UUID
    grant_id: UUID
    prepared_submission_version_id: UUID
    expected_package_manifest_hash: str
    checked_review_ids: tuple[UUID, ...]
WithdrawPreparedSubmissionCommand:
    project_id: UUID
    prepared_submission_version_id: UUID
    reason: str
GetContributionQuery / GetAuthorshipSnapshotQuery:
    project_id: UUID
    id: UUID
GetPreparedSubmissionQuery / PreviewPreparedSubmissionQuery:
    project_id: UUID
    prepared_submission_version_id: UUID
```

Tuple order is meaningful for authors and contributions. Corresponding authors,
equal groups and checked reviews use duplicate-rejecting set normalization as
specified by R2/R3. No automatic deduplication. Required text has 1..10,000 Unicode
code points after NFC and must contain a non-whitespace character. Preserve
meaningful whitespace. Reject surrogate code points and NUL. Do not truncate.
Authors: 1..100; corresponding authors: 1..100; equal groups: 0..50, each 2..100,
with no overlaps. Contributions per snapshot: 1..1,000, no duplicate record IDs.
Manifest occurrences: 0..10,000 non-consent rows at prepare; total including
consents: at most 10,000 at freeze. Checked reviews: 1..1,000. Digests: exactly
64 lowercase hexadecimal characters. No caller-supplied timestamps or hashes
except freeze's expected manifest digest. Transport arrays obey these same limits.

Readback dataclasses have these exact fields. Tuple members are typed objects,
not dictionaries. No additional display/affiliation/ORCID field is stored here.

| DTO | Fields and Python types |
| --- | --- |
| `ExactReference` | `type: Literal['ContributionRecord','AuthorshipSnapshot','ArtifactVersion','SourceVersion','ClaimVersion','ScientificConclusionVersion','AuthorConsent','ManuscriptVersion']`, `id: UUID`, `content_hash: str` |
| `AuthorshipAuthor` | `actor_id: UUID`, `ordinal: int` (1-based) |
| `OrderedContribution` | `contribution_record: ExactReference`, `ordinal: int` (0-based) |
| `ContributionReadback` | `id: UUID`, `project_id: UUID`, `publication_id: UUID`, `actor_id: UUID`, `contribution_role: ContributionRole`, `contribution_statement: str`, `recorded_by: UUID`, `created_at: datetime`, `content_hash: str`, `hash_scheme: Literal['sha256-cjson-v1']` |
| `AuthorshipSnapshotReadback` | `id: UUID`, `project_id: UUID`, `publication_id: UUID`, `authors: tuple[AuthorshipAuthor,...]`, `corresponding_author_ids: tuple[UUID,...]`, `equal_contribution_groups: tuple[tuple[UUID,...],...]`, `contributions: tuple[OrderedContribution,...]`, `created_by: UUID`, `created_at: datetime`, `content_hash: str`, `hash_scheme: Literal['sha256-cjson-v1']` |
| `AuthorConsentReadback` | `id: UUID`, `project_id: UUID`, `prepared_submission_version_id: UUID`, `actor_id: UUID`, `consent_state: ConsentState`, `consent_scope: ConsentScope`, `evidence_artifact: ExactReference`, `prior_consent: ExactReference \| None`, `captured_at: datetime`, `content_hash: str`, `hash_scheme: Literal['sha256-cjson-v1']` |
| `ManifestItemReadback` | `id: UUID`, `category: Category`, `ordinal: int`, `target: ExactReference` |
| `PreparedSubmissionEventReadback` | `id: UUID`, `prepared_submission_version_id: UUID`, `prior_status: PackageStatus \| None`, `new_status: PackageStatus`, `actor_id: UUID`, `occurred_at: datetime`, `reason: str \| None` |
| `PreparedSubmissionReadback` | `id: UUID`, `project_id: UUID`, `publication_id: UUID`, `version_number: int`, `manuscript_version_id: UUID`, `authorship_snapshot_id: UUID`, `status: PackageStatus`, `package_manifest_hash: str \| None`, `content_hash: str \| None`, `hash_scheme: Literal['sha256-cjson-v1']`, `frozen_at: datetime \| None`, `created_by: UUID`, `created_at: datetime`, `items: tuple[ManifestItemReadback,...]`, `consents: tuple[AuthorConsentReadback,...]`, `events: tuple[PreparedSubmissionEventReadback,...]`, `grant_id: UUID \| None`, `consumption_id: UUID \| None`, `current_validity: Validity`, `validity_reasons: tuple[ValidityReason,...]` |
| `PreparedSubmissionPreview` | `prepared_submission_version_id: UUID`, `items: tuple[ManifestItemReadback,...]`, `candidate_manifest_hash: str \| None`, `missing_author_ids: tuple[UUID,...]`, `current_validity: Validity`, `validity_reasons: tuple[ValidityReason,...]` |

Before freeze, `items` contains stored non-consent rows only. Preview consent
items use the selected consent UUID as transient item ID; persisted item IDs are
not hash inputs. Candidate hash is null unless exact frozen closure and every
consent are verifiable. PREPARED remains NOT_FROZEN even with a candidate digest.
Frozen historical readback preserves the bound consent rows; current heads are
returned by `consents`. Missing or corrupt formal closure raises the provenance
error, not a silently repaired result. Validity reasons are sorted, duplicate-free
and have at most eight members. Lifecycle WITHDRAWN prevents current use;
SUPERSEDED alone does not. Freeze receipt v1 saves the exact historical result
DTO; separately authorized current readback supplies present validity (§7).

### 11.3 Error-code transport mappings

Existing values come from [API errors](../../src/researchbase/api/errors.py) and
[CLI errors](../../src/researchbase/cli/errors.py). Proposed values apply only when
an authorized future contract adds the absent enum member and both handlers.
This table covers every returned code named in this draft.

| ErrorCode | HTTP status | CLI exit | Standing / use |
| --- | --- | --- | --- |
| AUTHENTICATION_REQUIRED | 401 | 3 | Existing; missing/invalid authenticated principal. |
| FORBIDDEN | 403 | 3 | Existing; wrong actor/project or absent current entitlement. |
| VALIDATION_ERROR | 422 | 2 | Existing; malformed closed DTO, bounds or unsupported literal. |
| NOT_FOUND | 404 | 3 | Existing; authorized missing exact ID. |
| VERSION_NOT_FROZEN | 409 | 4 | Existing; draft exact dependency. |
| INVALID_STATE_TRANSITION | 409 | 4 | Existing; unavailable lifecycle transition. |
| IMMUTABLE_RECORD | 409 | 4 | Existing; attempted sealed-material mutation. |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Existing; concrete FK/same-parent constraint failure. |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Existing; broken closure or HASH_MISMATCH. |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Existing; changed UUID/key material. |
| CONCURRENT_MODIFICATION | 409 | 4 | Existing; obsolete chain head, exhausted retry or lock/statement timeout. |
| CONFLICT_OF_INTEREST | 403 | 3 | Existing provisional review mapping retained; independence failure. |
| SUBMISSION_PACKAGE_INVALID | 409 | 4 | Proposed; missing authorship/consent, occurrence mismatch or OTHER role. |
| APPROVAL_PURPOSE_TARGET_COMMAND_INVALID | 409 | 4 | Proposed dependency code; unavailable or unlisted approval tuple. |
| APPROVAL_GATE_FAILED | 409 | 4 | Proposed dependency code; blocker or invalid Decision/review basis. |
| REJECTION_RECONSIDERATION_REQUIRED | 409 | 4 | Proposed dependency code; unresolved project/purpose rejection. |
| GRANT_INVALID | 409 | 4 | Proposed dependency code; wrong scope, terminal use or expiry. |
| GRANT_STALE | 409 | 4 | Proposed dependency code; loss of current eligibility/authority/consent. |

GRANT_INVALID covers an expiry of the grant itself. GRANT_STALE covers an expired
required approver role or other lost eligibility. Caller credential/role loss
uses AUTHENTICATION_REQUIRED/FORBIDDEN. S1 adds none of the proposed codes.

## 12. Implementation guide — future authorization required

This guide specifies build artifacts, not permission to create them. S1 is the
only immediately buildable write slice in the inspected baseline. A migration
must not install deferred package/consent/governance tables as incidental S1 work.

### 12.1 Not in this slice

| Future contract | Missing behavior and blocked commands |
| --- | --- |
| Manuscript Freeze and Sealed Placement Contract | Exact manuscript/document/placement closure, FROZEN transition and hash verifier. Blocks `prepare_submission` and all package/consent commands. Existing draft/trace is insufficient. |
| Publication READY Transition Contract | Contract `INTERNAL_REVIEW→READY` and its lifecycle event/consumption binding. Blocks `freeze_prepared_submission`. |
| Manuscript Internal Review Contract | Independent exact-manuscript review, complete review discovery, Issue phantom protection and blocker checks. Blocks freeze. |
| READY_FOR_SUBMISSION Decision Purpose Contract | Exact manuscript/review Decision basis and independence. Blocks readiness and hence freeze. |
| PREPARE_SUBMISSION Decision Purpose Contract | Distinct affirmative exact-manuscript Decision and approval tuple. Blocks freeze. |
| Approval Grant Consumption and Lifecycle Contract | Atomic local effect, R3 receipt, terminal grant events, lifecycle evaluator and compatible per-command lock order across PR2-14/15/16 writers. Blocks freeze and atomic consent withdrawal. |
| Consent Withdrawal, Grant Resolution and Offboarding Contract | Implements §11.1 resolver, grant-creation phantom protection, withdrawal/grant event atomicity and timely direct-author withdrawal after role removal. Blocks `record_author_consent(WITHDRAWN)`, regrant and production consent use. |
| Package Preparation S2 Contract/Execution Pack | After manuscript freeze: authorize `prepare_submission`, exact package/history/preview reads, and direct root GRANTED consent with immutable context. No freeze or grant consumption. Package OWNER withdrawal also awaits this lifecycle contract. |
| Issue Disposition and Rejection Reconsideration Contracts | Safe recovery from blockers/rejections; no silent Issue mutation or replacement Decision. Those recovery paths stay unavailable. |

The six freeze prerequisites are the first six rows, each a separate future
contract. The additional rows do not weaken them. S1 ships exactly
`record_contribution`, `create_authorship_snapshot`, `get_contribution` and
`get_authorship_snapshot`. It exposes no package or consent endpoint. Unit tests
may exercise pure package hash helpers without claiming a package workflow.

S2 cannot accept a DRAFT manuscript to make a demonstration pass. Its preparation
commands are specified here for review but are not runnable on the current
baseline. Do not create fake FROZEN rows in normal-role integration fixtures.

### 12.2 Exact DDL sketch

The following compact DDL notation makes shared columns and names explicit.
Expand it mechanically when writing a separately authorized migration. It is not
an executable migration and introduces no new semantic fields.

For each table `t` below, first expand `BASE(t)` into these columns/constraints:

```sql
id UUID NOT NULL CONSTRAINT pk_t PRIMARY KEY,
created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
created_by UUID NOT NULL CONSTRAINT fk_t_created_by REFERENCES actors(id) ON DELETE RESTRICT
```

Replace the literal suffix `t` with the full table name. `HASH(t, nullable)` adds
`content_hash CHAR(64) NULL` if nullable, otherwise `NOT NULL`, and
`hash_scheme VARCHAR(32) NOT NULL`; name checks `ck_t_digest` for
`content_hash IS NULL OR content_hash ~ '^[0-9a-f]{64}$'` and `ck_t_scheme` for
`hash_scheme = 'sha256-cjson-v1'`. No hash default. All subsequent columns below
are NOT NULL unless explicitly marked NULL. SQL types are literal PostgreSQL types.

Name each FK `fk_<table>_<column>` (composite FK names are given explicitly).
Every FK uses ON DELETE RESTRICT. Name each listed unique key `uq_<table>_<label>`
and each listed check `ck_<table>_<label>`. PK names follow BASE. These templates
are exact naming rules, not names for an engineer to choose.

| S1 table | Columns after BASE / HASH | Unique keys and CHECK constraints |
| --- | --- | --- |
| `contribution_records` | `HASH(t,false)`; `publication_id UUID FK publications(id)`; `actor_id UUID FK actors(id)`; `recorded_by UUID FK actors(id)`; `contribution_role VARCHAR(24)`; `contribution_statement TEXT` | `parent_id(publication_id,id)`; `role`: role IN the six §11.2 literals; `statement`: length(contribution_statement) BETWEEN 1 AND 10000 AND contribution_statement ~ '[^[:space:]]'; `recorder`: recorded_by = created_by. |
| `authorship_snapshots` | `HASH(t,false)`; `publication_id UUID FK publications(id)` | `parent_id(publication_id,id)`. No status or row version: immutable snapshot from insertion. |
| `authorship_snapshot_authors` | `authorship_snapshot_id UUID FK authorship_snapshots(id)`; `actor_id UUID FK actors(id)`; `ordinal INTEGER` | `actor(authorship_snapshot_id,actor_id)`; `ordinal(authorship_snapshot_id,ordinal)`; `ordinal`: ordinal BETWEEN 1 AND 100. |
| `authorship_snapshot_corresponding_authors` | `authorship_snapshot_id UUID`; `actor_id UUID`; `ordinal INTEGER` | `actor(authorship_snapshot_id,actor_id)`; `ordinal(authorship_snapshot_id,ordinal)`; `ordinal`: ordinal BETWEEN 0 AND 99; composite `fk_corresponding_author(snapshot_id,actor_id)` described below. |
| `authorship_snapshot_equal_groups` | `authorship_snapshot_id UUID`; `actor_id UUID`; `group_ordinal INTEGER`; `ordinal INTEGER` | `actor(authorship_snapshot_id,actor_id)` prevents overlaps; `position(authorship_snapshot_id,group_ordinal,ordinal)`; `group_ordinal`: group_ordinal BETWEEN 0 AND 49; `ordinal`: ordinal BETWEEN 0 AND 99; composite `fk_equal_group_author` below. |
| `authorship_snapshot_contributions` | `authorship_snapshot_id UUID FK authorship_snapshots(id)`; `contribution_record_id UUID FK contribution_records(id)`; `ordinal INTEGER` | `record(authorship_snapshot_id,contribution_record_id)`; `ordinal(authorship_snapshot_id,ordinal)`; `ordinal`: ordinal BETWEEN 0 AND 999. |

In the two composite FKs above, `snapshot_id` is explanatory abbreviation for the
actual column `authorship_snapshot_id`. The exact definitions are:

```sql
CONSTRAINT fk_corresponding_author
  FOREIGN KEY (authorship_snapshot_id, actor_id)
  REFERENCES authorship_snapshot_authors(authorship_snapshot_id, actor_id) ON DELETE RESTRICT
CONSTRAINT fk_equal_group_author
  FOREIGN KEY (authorship_snapshot_id, actor_id)
  REFERENCES authorship_snapshot_authors(authorship_snapshot_id, actor_id) ON DELETE RESTRICT
```

The four remaining tables below are deferred S2/full-design DDL. Do not install
these tables or grant-result FKs in S1. Each uses the same BASE and naming rules.

| Deferred table | Columns after BASE / HASH | Unique keys and CHECK constraints |
| --- | --- | --- |
| `prepared_submission_versions` | `HASH(t,true)`; `publication_id UUID FK publications(id)`; `version_number INTEGER`; `manuscript_version_id UUID`; `authorship_snapshot_id UUID`; `status VARCHAR(16)`; `package_manifest_hash CHAR(64) NULL`; `frozen_at TIMESTAMPTZ NULL`; `row_version INTEGER` | `parent_id(publication_id,id)`; `number(publication_id,version_number)`; `number`: version_number > 0; `row_version`: row_version > 0; `status`: status IN ('PREPARED','FROZEN','SUPERSEDED','WITHDRAWN'); `hash_state` below; `manifest_digest`: package_manifest_hash IS NULL OR package_manifest_hash ~ '^[0-9a-f]{64}$'. |
| `author_consents` | `HASH(t,false)`; `prepared_submission_version_id UUID FK prepared_submission_versions(id)`; `actor_id UUID FK actors(id)`; `consent_state VARCHAR(16)`; `consent_scope VARCHAR(24)`; `evidence_artifact_version_id UUID FK artifact_versions(id)`; `prior_consent_id UUID NULL FK author_consents(id)`; `captured_at TIMESTAMPTZ` | `package_id(prepared_submission_version_id,id)`; `state`: consent_state IN ('GRANTED','WITHDRAWN'); `scope`: consent_scope = 'PREPARED_PACKAGE'; `not_self`: prior_consent_id IS NULL OR prior_consent_id <> id; `capturer`: created_by = actor_id. Evidence is NOT NULL, overriding old Field Contract 13 allowance per R2 17. |
| `prepared_submission_manifest_items` | `prepared_submission_version_id UUID FK prepared_submission_versions(id)`; `category VARCHAR(24)`; `ordinal INTEGER`; `artifact_version_id UUID NULL FK artifact_versions(id)`; `source_version_id UUID NULL FK source_versions(id)`; `claim_version_id UUID NULL FK claim_versions(id)`; `scientific_conclusion_version_id UUID NULL FK scientific_conclusion_versions(id)`; `author_consent_id UUID NULL` | `position(prepared_submission_version_id,category,ordinal)`; `ordinal`: ordinal BETWEEN 0 AND 9999; `target` below; composite consent FK below. Repeated target occurrences remain legal. |
| `prepared_submission_events` | `prepared_submission_version_id UUID FK prepared_submission_versions(id)`; `prior_status VARCHAR(16) NULL`; `new_status VARCHAR(16)`; `actor_id UUID FK actors(id)`; `occurred_at TIMESTAMPTZ`; `reason TEXT NULL` | `transition` below; `reason`: reason IS NULL OR (length(reason) BETWEEN 1 AND 10000 AND reason ~ '[^[:space:]]'); `actor`: actor_id = created_by. |

Exact deferred composite FKs and nontrivial checks:

```sql
-- prepared_submission_versions
CONSTRAINT fk_prepared_manuscript_same_publication
  FOREIGN KEY (publication_id, manuscript_version_id)
  REFERENCES manuscript_versions(publication_id, id) ON DELETE RESTRICT
CONSTRAINT fk_prepared_snapshot_same_publication
  FOREIGN KEY (publication_id, authorship_snapshot_id)
  REFERENCES authorship_snapshots(publication_id, id) ON DELETE RESTRICT
CONSTRAINT ck_prepared_submission_versions_hash_state CHECK (
  (status = 'PREPARED' AND content_hash IS NULL
    AND package_manifest_hash IS NULL AND frozen_at IS NULL)
  OR (status IN ('FROZEN','SUPERSEDED','WITHDRAWN') AND content_hash IS NOT NULL
    AND package_manifest_hash IS NOT NULL AND frozen_at IS NOT NULL)
  OR (status = 'WITHDRAWN' AND content_hash IS NULL
    AND package_manifest_hash IS NULL AND frozen_at IS NULL)
)
-- prepared_submission_manifest_items
CONSTRAINT fk_manifest_consent_same_package
  FOREIGN KEY (prepared_submission_version_id, author_consent_id)
  REFERENCES author_consents(prepared_submission_version_id, id) ON DELETE RESTRICT
CONSTRAINT ck_prepared_submission_manifest_items_target CHECK (
  num_nonnulls(artifact_version_id, source_version_id, claim_version_id,
    scientific_conclusion_version_id, author_consent_id) = 1
  AND ((category IN ('FIGURE','TABLE') AND artifact_version_id IS NOT NULL)
    OR (category = 'CITATION' AND source_version_id IS NOT NULL)
    OR (category = 'CLAIM' AND claim_version_id IS NOT NULL)
    OR (category = 'CONCLUSION' AND scientific_conclusion_version_id IS NOT NULL)
    OR (category = 'AUTHOR_CONSENT' AND author_consent_id IS NOT NULL))
)
-- prepared_submission_events
CONSTRAINT ck_prepared_submission_events_transition CHECK (
  (prior_status IS NULL AND new_status = 'PREPARED' AND reason IS NULL)
  OR (prior_status = 'PREPARED' AND new_status = 'FROZEN' AND reason IS NULL)
  OR (prior_status = 'FROZEN' AND new_status = 'SUPERSEDED' AND reason IS NULL)
  OR (prior_status IN ('PREPARED','FROZEN') AND new_status = 'WITHDRAWN'
    AND reason IS NOT NULL)
)
CREATE UNIQUE INDEX uq_prepared_submission_versions_frozen_publication
  ON prepared_submission_versions(publication_id) WHERE status = 'FROZEN';
CREATE UNIQUE INDEX uq_author_consents_root
  ON author_consents(prepared_submission_version_id, actor_id, consent_scope)
  WHERE prior_consent_id IS NULL;
CREATE UNIQUE INDEX uq_author_consents_successor
  ON author_consents(prior_consent_id) WHERE prior_consent_id IS NOT NULL;
```

For every FK column not already the leading column of a PK/unique index, create
`ix_<table>_<column>` as a B-tree on exactly that column. This includes BASE's
created_by, relation actor IDs, contribution_record_id, all manifest target IDs,
prepared manuscript/snapshot IDs, consent evidence and event actor IDs. A
composite FK's first column may use an existing leading unique index; also index
its target-ID column if not already covered. Add these two history indexes:
`ix_author_consents_history(prepared_submission_version_id,actor_id,captured_at,id)`
and `ix_prepared_submission_events_history(prepared_submission_version_id,occurred_at,id)`.
Index names follow the literal templates. All generated names must fit
PostgreSQL's 63-byte limit; for an overlength name replace only the table token
using `authorship_snapshot_corresponding_authors→as_corresponding`,
`authorship_snapshot_contributions→as_contributions`,
`authorship_snapshot_equal_groups→as_equal_groups`,
`authorship_snapshot_authors→as_authors`,
`prepared_submission_manifest_items→ps_manifest`,
`prepared_submission_versions→ps_versions`,
`prepared_submission_events→ps_events`. Apply this substitution consistently to
all constraint/index templates, before creating objects; do not rely on truncation.

Required contribution statements and reasons also have named `ck_<table>_nfc`
checks using `column = normalize(column, NFC)` with the same name-shortening
rules. For nullable reason, allow SQL NULL. PostgreSQL text rejects NUL bytes.
SQL CHECKs cannot enforce child aggregates or historical transitions alone.
Create these named functions/triggers, with identical function and trigger names
unless a suffix is shown. They are required build artifacts, not optional checks:

| Guard | Exact enforcement |
| --- | --- |
| `pr217_immutable` | BEFORE UPDATE OR DELETE on contribution, snapshot, all four snapshot relation, consent and package event tables. Always reject. For each table use trigger name `pr217_immutable_<table alias>` with the aliases above. |
| `pr217_snapshot_sealed` | BEFORE INSERT on each snapshot relation. Require parent inserted by the same transaction; acquire parent row lock and forbid additions to any previously committed snapshot, including one with no child rows. No mutable seal flag. Mirror the accepted Decision basis creation-transaction guard pattern in migration 0042. |
| `pr217_snapshot_complete` | DEFERRABLE INITIALLY DEFERRED constraint triggers AFTER INSERT on snapshot and each relation. At commit require 1..100 distinct HUMAN authors, contiguous 1-based author order; 1..100 corresponding subset with contiguous 0-based storage order; groups 2+ with contiguous 0-based group/member coordinates, disjoint subset; 1..1000 contributions, contiguous 0-based order, same Publication and per-author actor match. Recompute the snapshot R2 material in Application; SQL independently enforces membership and seals the rows. |
| `pr217_contribution_guard` | BEFORE INSERT on contributions: exact Publication, valid attributed Actor, nonblank normalized bounded role/statement; recorded_by = created_by. Authority checked in Application at final DB time. |
| `pr217_consent_chain` (deferred scope) | BEFORE INSERT: lock exact package and prior head, verify direct HUMAN snapshot author, evidence frozen/same-project, chain scope/actor/package equality and current terminal head. Root GRANTED only; successors alternate. Grants only PREPARED; withdrawal allowed after freeze. SQL evidence bytes cannot replace Application byte/hash verification. |
| `pr217_package_guard` (deferred scope) | BEFORE INSERT/UPDATE/DELETE: INSERT requires PREPARED, row_version = 1, exact FROZEN currently valid manuscript and sealed snapshot; immutable material from creation; no DELETE; only §3 lifecycle transitions and row_version + 1; frozen hashes/timestamp immutable. Freeze requires complete exact consent items and concrete grant consumption in the same transaction, checked by a deferred constraint trigger `pr217_package_consumption`. |
| `pr217_manifest_guard` (deferred scope) | BEFORE INSERT/UPDATE/DELETE: insert non-consent items only with new package; add consent items only in freeze transaction, with exact current heads. No UPDATE/DELETE. Deferred `pr217_manifest_complete` verifies ordinal contiguity, occurrence equality, total bound and one distinct consent per snapshot author. |
| `pr217_package_events` (deferred scope) | Deferred constraint trigger: exactly one initial event, then one event per allowed row transition; actor/time and freeze receipt agree; OWNER withdrawal reason required; no fabricated prior state. |

For S1 triggers, propose private SQLSTATE P17A1 for immutable/sealed-set
mutation, P17A2 for invalid snapshot aggregate/HUMAN/coverage, and P17A3 for
invalid contribution material. In the opt-in authorship UoW normalizer, map these
to IMMUTABLE_RECORD, PROVENANCE_CLOSURE_VIOLATION and VALIDATION_ERROR respectively.
Map 23503 to REFERENTIAL_INTEGRITY_ERROR and 23514/23502 to VALIDATION_ERROR.
UUID-coordinated changed replay maps to IDEMPOTENCY_CONFLICT; an unexpected
23505 after those guards maps to CONCURRENT_MODIFICATION without automatic retry.
Only the private retryable flag described in §7 permits another attempt. Unknown
failures use sanitized INVALID_STATE_TRANSITION, never success. Deferred-scope
guards must get their own mapping in the missing command contracts.

Use constraint-trigger names `<guard>_<table alias>` when installed on multiple
tables; use the full table name when no alias is listed. Reject direct SQL
attempts under the normal application role. Grant table ownership/trigger-disable
rights are not given to that role. Shared timestamps are set from DB time;
service-generated UUIDs are the canonical record/event IDs.

S1 does not change existing manuscript checks/triggers. In future S2, create
packages then consents then add the composite manifest FK after both tables exist.
The future consumption contract owns the concrete result FK from
`approval_grant_consumptions.result_prepared_submission_version_id` to this table;
no S1 stub or alternate receipt schema is allowed. Downgrade refuses to discard
any retained new-table rows; an empty-schema downgrade removes guards/indexes/FKs
in reverse dependency order. Never modify accepted migrations.

### 12.3 Ordered build steps and file paths

1. Obtain S1 contract approval and separate execution authorization. Check the
   real Alembic head. Add one forward migration named
   `migrations/versions/<next_revision>_pr2_17_authorship_preparation.py`, with
   down_revision equal to that head. The placeholder is intentional: concurrent
   PR2-15/16 implementation owns the intervening revision numbers. Do not assume
   0043, edit an earlier migration or create a second head.
2. Add pure role/text/ordering checks and literal R2 hash material builders in
   `src/researchbase/domain/authorship.py`. Follow
   `src/researchbase/domain/decision.py`. Reuse foundation canonical serialization;
   independently check the R2 authorship golden vector. Do not import persistence.
3. Add `RecordContributionCommand`, `CreateAuthorshipSnapshotCommand`, their
   readbacks and `AuthorshipService` in
   `src/researchbase/application/authorship.py`. Constructor:
   `AuthorshipService(factory: Callable[[], UnitOfWork], credentials: CredentialVerifier)`.
   Import the existing `CredentialVerifier` protocol from
   `src/researchbase/domain/phase2_identity.py`. The four S1 methods take
   `principal: VerifiedPrincipal` plus the corresponding command/query and return
   the typed readback in §11.2. Follow the authorization/replay structure in
   `application/decision.py` and `application/internal_review.py`.
4. Add `AuthorshipRepository` protocol and `UnitOfWork.authorship` in
   `src/researchbase/application/ports.py`. Required operations:
   `lock_request(id)`, `lock_publication(publication_id, project_id)`,
   `lock_snapshot()`, `lock_project(project_id)`, `contribution(id)`,
   `snapshot(id)`, `snapshot_relations(id)`, `insert_contribution(row)`,
   `insert_snapshot(row)`, `insert_snapshot_relations(rows)` and
   `lock_contributions(ids)` (UUID sorted). Use typed domain/Application values
   at the public service boundary; repository mappings stay internal.
5. Implement those operations in
   `src/researchbase/persistence/authorship_repository.py`, following
   `persistence/decision_repository.py`. Wire the repository and sanitized error
   normalization in `src/researchbase/persistence/uow.py`. Use the S1 table DDL,
   guards and lock sequence below. No runtime dependency is added.
6. Add only thin S1 transport wiring in `src/researchbase/api/routes.py` and
   `src/researchbase/cli/commands/authorship.py`; register CLI composition in
   `src/researchbase/cli/app.py` and `src/researchbase/cli/composition.py` using
   the existing verified-context boundary. HTTP: POST
   `/projects/{project_id}/publications/{publication_id}/contributions` and
   `/authorship-snapshots` under the same publication prefix; GET each with
   `/{id}`. Path IDs must equal body scope IDs. CLI: `authorship contribution
   record|get` and `authorship snapshot create|get`. CLI uses the existing API
   transport; neither adapter writes the DB. If transports are not authorized
   by the execution pack, ship the Application slice only and say so explicitly.
7. Create the §12.5 tests, run S1 and dependent real-PostgreSQL suites, record
   exact results, then stop. Do not advertise full PR2-17 or M4 acceptance.

After separate S2 authorization, use `domain/prepared_submission.py`,
`application/prepared_submission.py`, `persistence/prepared_submission_repository.py`
and `cli/commands/prepared_submission.py`, with port/UoW/API registration in the
same existing files. Consent helpers belong to `domain/authorship.py`; the
package service owns its transaction and chain resolver. Do not put grant
consumption into the contribution service. The consumption/withdrawal contracts
must supply their executable lock matrices before these paths are enabled.

### 12.4 Exact S1 lock order per command

Use READ COMMITTED as in PR2-14/15. Never call an existing service that opens a
second UoW from inside the command. Queries below use separate statements after
waits. First repository operation sets the §7 transaction-local timeouts.
The request advisory key is `hashtextextended('pr217:authorship:' || id::text,0)`
passed to `pg_advisory_xact_lock`. Its purpose is UUID replay coordination only.

`lock_snapshot()` takes one SHARE table lock on this exact lexically sorted list:
`actor_subject_bindings`, `actors`, `project_membership_events`,
`project_memberships`, `project_role_assignments`, `projects`.
These are read-only tables for S1; do not SHARE-lock a table S1 then INSERTs into.
The list protects authority/actor INSERT phantoms as well as existing row changes.
Existing immutable contribution/author rows need no table lock.

| Command | Exact acquisition order; all locks transaction-scoped |
| --- | --- |
| `record_contribution` | (1) request advisory for command.id; (2) exact Publication FOR UPDATE, scoped by project_id; (3) the sorted SHARE list above; (4) Project FOR UPDATE via existing identity repository; (5) attributed Actor and recording Actor FOR SHARE in ascending UUID, with duplicates removed; (6) reread existing UUID and authorization at clock_timestamp; (7) insert contribution. |
| `create_authorship_snapshot` | (1) request advisory for command.id; (2) exact Publication FOR UPDATE; (3) sorted SHARE list; (4) Project FOR UPDATE; (5) all author/contributor/recorder Actors FOR SHARE in ascending UUID; (6) selected contribution_records FOR SHARE in ascending UUID; (7) reread existing snapshot UUID and all selected material; final clock_timestamp authorization; (8) insert snapshot then author, corresponding, equal-group and contribution rows, in that order, each in its defined storage order. |
| `get_contribution` | (1) exact Publication FOR SHARE, resolved through requested contribution without disclosing it; (2) sorted SHARE list; (3) Project FOR UPDATE using the existing identity authorization path; (4) read contribution, verify saved hash and fresh read entitlement; no writes. |
| `get_authorship_snapshot` | (1) exact Publication FOR SHARE resolved through requested snapshot; (2) sorted SHARE list; (3) Project FOR UPDATE; (4) read snapshot and all immutable relations; verify hashes/membership and fresh read entitlement; no writes. |

Authenticate before target lookup; do not disclose missing/foreign target results
until project read entitlement is established. If the target is absent, omit its
row lock, acquire the same SHARE list and requested Project lock, then distinguish
NOT_FOUND from FORBIDDEN. UUID lookups across another project remain nondisclosing.

Creation replay follows the creation command's same order, returns only the
saved rows, checks same recorder/project/material and current read entitlement,
and skips original writer-role/current actor eligibility gates. A new snapshot
must still select currently eligible HUMAN authors. Both create commands use
RESEARCHER/OWNER only on first execution. A second blocking wait after the final
check repeats affected reads and clock_timestamp authorization before writes.
Normal-role SQL child guards take their parent snapshot lock; Application inserts
its new snapshot before its child rows, so they cannot invert these row locks.
Direct invalid SQL is rejected, not treated as an alternate authorized writer.

There is deliberately no executable freeze/consent/withdrawal lock sequence in S1:
those commands are absent, per §12.1. Their future contract must preserve the
accepted request→exact manuscript target→sorted SHARE coordination, then order
project/purpose, Publication, all affected packages, request/grant and sorted
Actor-ID consent chains consistently across every participating writer. It must
include new-review/zero-Issue INSERT, role revocation, new-grant INSERT and atomic
supersession. A generic proposal is insufficient to enable any of those commands.

### 12.5 Test files and required cases

All paths below are files to create during authorized implementation, not links
to files asserted to exist now. Use `tests/disposable_postgres.py` and existing
PR2-14/15 fixture patterns. Identities are disposable TEST ONLY actors.

| New test file | Mandatory cases |
| --- | --- |
| `tests/unit/phase2/test_pr2_17_authorship.py` | Exact commands/UUID/tuple/extra-field rejection; all enum/bound edges; NFC and nonblank/NUL/surrogate handling; author/contribution order sensitivity; corresponding/equal set order invariance; R2 independent snapshot vector; contribution literal preimage; no HUMAN authorship for Agent; duplicate/overlap/subset/coverage rejection. |
| `tests/integration/phase2/test_pr2_17_authorship_schema.py` | PostgreSQL 18 clean install and upgrade from 0018/accepted head; one Alembic head; catalog exact columns/nullability/types/constraint/index names; normal-role wrong-parent/HUMAN/ordinal/coverage constraints; later child INSERT and all immutable UPDATE/DELETE rejected; transaction rollback; nonempty downgrade refusal and empty downgrade round trip. |
| `tests/integration/phase2/test_pr2_17_authorship.py` | Publication and HUMAN/Agent contributor fixtures; both create commands and exact reads; per-author contribution match; cross-project denial; verified principal/role/credential gates; saved hash corruption fails closed; new UUID is new fact; same UUID exact replay after restart and writer-role loss with read retained; changed material conflicts; lost read/credential denies; no manuscript/grant/scientific mutations. |
| `tests/integration/phase2/test_pr2_17_authorship_concurrency.py` | Same UUID identical/conflicting creates, overlapping snapshot authors/contributions, concurrent direct late child INSERT; at most one durable fact; held Publication/Project lock with credential/role expiry during wait, including second wait; three-attempt serialization/deadlock bound and no timeout retry; final authorization timestamps and zero effects on denial. Capture backend PIDs and actual blocking evidence. |
| `tests/architecture/test_pr2_17_boundaries.py` | Domain imports, port/UoW write path, no ORM DTOs, no ExternalEffect, no new top-level schema or support/authority inference; S1 exposes exactly four methods and no package/consent/freeze transport. |
| `tests/test_pr2_17_adapters.py` | Authorized S1 HTTP/CLI parity, path/body mismatch rejection, existing error mappings, bounded diagnostics and no raw driver/credential errors. Required only when transport step 6 is authorized. |

Future S2 files, blocked by the contracts in §12.1:
`tests/integration/phase2/test_pr2_17_preparation.py` (exact frozen manuscript,
occurrence projection including repeated targets and OTHER denial, immutable
PREPARED/null hashes, version allocation, preview, direct root consent/evidence);
`test_pr2_17_consent_withdrawal.py` in the same directory (fork/root/alternation,
package→grant resolver, newly inserted grants, atomic staling, offboarding);
`test_pr2_17_freeze.py` (all gates, exact receipt/replay, supersession and rollback);
and `test_pr2_17_freeze_concurrency.py` (every §8 race and expiry order). These are
not runnable S1 acceptance tests. Build independent golden preimages rather than
calling the implementation to generate expected digests.

For authorized S1, run `uv run pytest -o addopts='' -ra` over the new unit,
architecture and applicable adapter files, then the three new integration files
against disposable PostgreSQL 18.x. Also run the existing
`tests/integration/phase2/test_pr2_12_publication_draft.py`,
`test_pr2_14_internal_review.py`, `test_pr2_15_decision.py` and
`test_pr2_15_decision_schema.py` under that directory, plus `tests/e2e` with its
required DATABASE_URL. Run `uv run ruff check .`, `uv run ruff format --check .`
and `uv run pyright`. Use actual dependency-suite names from the approved PR2-16
base once integrated; do not invent a passing PR2-16 suite. Report executed,
passed, failed, skipped and blocked counts separately.

## 13. Open questions for the owner

No implementation choice remains delegated to the engineer for S1. The owner may
overrule any §11 decision before ratification. Missing future contracts are listed
in §12.1; they are explicit unavailable commands, not alternative S1 behaviors.
Approval of this document still requires a separate execution pack and explicit
implementation authorization. This draft retains its DRAFT status.

This is a documentation change verified by local-link and format checks only.
These checks do not establish implementation, PostgreSQL integration or gate acceptance.
