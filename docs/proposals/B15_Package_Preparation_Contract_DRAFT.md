# PR2-17 Package Preparation (S2) (B15) Contract — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

## Start here (for the implementer)

B15 records an exact PREPARED package, its manuscript occurrences and immutable
already-sealed authorship context. Each HUMAN author may record one direct root
GRANTED consent with retained evidence. Authorized readers can inspect history
and preview a candidate manifest; an OWNER can withdraw the package. Nothing is
frozen, sent or approved by these commands. A complete preview is still PREPARED.

Read §§1–4 first; use §10 for terms, §11 for pinned choices and §12 for construction.
This draft refines the S2 boundary in the approved [authorship contract](PR2-17_Submission_Authorship_Contract_DRAFT.md),
§12.1. Contract approval and implementation authorization remain separate.

Build only after separate authorization, in this order:

1. Reconcile accepted B04/S1 and the migration head (§1); add only §12.1's four
   registered package/consent tables and guards in a new forward migration.
2. Add pure occurrence projection and literal R2 consent/manifest hash builders
   (§§5, 11), then closed Application commands and ports at §12.3's paths.
3. Implement SHARE-first READ COMMITTED writes and plain REPEATABLE READ reads,
   including every nested verifier (§12.2). Do not call S1 public read services
   inside a write UoW (they open their own transaction); reuse their material
   verification with plain repository reads in the same UoW.
4. Add preparation, root consent, history/preview and OWNER withdrawal (§4).
   Preserve material from creation; corrections require another package UUID.
5. Run §12.4's focused checks, retain actual results and stop at §12.5.

Five rules whose violation fails review:

1. Require a valid exact FROZEN manuscript and same-Publication sealed snapshot;
   authority cannot override deterministic invalidity or repair missing provenance.
2. Preserve every direct placement occurrence, including repeated targets. No
   arbitrary input manifest, deduplication, JSON reference list or new fact owner.
3. Package hashes and frozen_at stay SQL NULL, including after OWNER withdrawal.
   Preview is read-only; consent items are transient until a future freeze slice.
4. Consent is direct HUMAN authorship acknowledgment, never OWNER/approver consent
   for someone else. This slice accepts only GRANTED roots with verified evidence.
5. One command is one transaction. Reads/replay take no explicit table, advisory
   or row locks. No grant consumption, consent withdrawal/regrant or external send.

## 1. Purpose, authority and inspected baseline

| Authority | Binding rule |
| --- | --- |
| [System 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 13, 31; [Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A17–A22 | Scientific facts precede authority; membership is not authorship; prepared versus sent; focused R2/R3/R4 corrections take precedence. |
| [Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), §3; [Cross-Phase 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§9–18, 28 | Reuse PreparedSubmissionVersion/Event and AuthorConsent; typed exact FKs, additive compatibility and common Application boundary. |
| [Phase 2 spec 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §§23–24, PR2-17; [Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), §§1–2, 4 | Package preparation is local history, not SubmissionVersion/SubmissionRecord or ExternalEffect. |
| [Field contract 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md), prepared-package rows; [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md), authorship/package and hash lifecycle | Concrete occurrence rows, same-parent FKs, literal R2 material, NULL PREPARED hashes; no hash cycle. |
| [Governance R2 17](../architecture/17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md), §§1, 3; [R3 18](../architecture/18_Phase2_Design_R3_Targeted_Remediation_v1.0.md), §5; [Temporal R4 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md), TEMP-AUTH-01 | Direct HUMAN consent/evidence; immutable context; later freeze needs distinct preparation grant; post-wait advancing DB authorization time. |
| [Harness 09](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 18–21; [authorship S1/S2 contract](PR2-17_Submission_Authorship_Contract_DRAFT.md), §§3–5, 11–12 | No Harness direct persistence; immutable attribution; explicit S2 preparation/root-consent boundary, no incidental freeze. |
| [B04](B04_Manuscript_Freeze_Contract_DRAFT.md), [B12](B12_Prepare_Submission_Decision_Contract_DRAFT.md), [B13](B13_Grant_Consumption_Contract_DRAFT.md) | B04 verifies sealed manuscript closure; B12 judgment and B13 consumption are separate prerequisites to later freeze, not preparation permission. |

Inspected 2026-10-18; source presence does not establish acceptance:

- [0046](../../migrations/versions/0046_pr2_17_authorship_preparation.py),
  [domain/authorship.py](../../src/researchbase/domain/authorship.py) and
  [application/authorship.py](../../src/researchbase/application/authorship.py)
  supply contribution/snapshot hashes, ordered typed relations and exact readers.
  Do not call S1 public read services inside a write UoW (they open their own
  transaction); reuse their material verification with plain repository reads
  in the same UoW.
- [0048/B04](../../migrations/versions/0048_b04_manuscript_freeze.py) and
  [ManuscriptFreezeService.verify_in_uow](../../src/researchbase/application/manuscript_freeze.py)
  provide sealed document/placement/transitive closure verification. Its
  [repository](../../src/researchbase/persistence/manuscript_freeze_repository.py)
  supplies SHARE-first writes and lock-free snapshot reads.
- [0058/B12](../../migrations/versions/0058_b12_prepare_submission.py) adds distinct
  preparation Decision/approval gates. [0059/B13](../../migrations/versions/0059_b13_grant_consumption.py)
  supplies release receipts and grant lifecycle; its result CHECK disables READY
  and package results and constrains the reserved package UUID to NULL. Do not
  change that guard or treat the reserved UUID as an available result FK here.
- The inspected migration head is `0059_b13_grant_consumption`. No package tables
  exist. Reconcile the head at implementation time; reserve no revision number.
  [0042](../../migrations/versions/0042_pr2_15_minimal_decision.py) supplies deferred
  completeness triggers; [0057](../../migrations/versions/0057_xid_wraparound_guards.py)
  supplies the corrected native `xmin = pg_current_xact_id()::xid` sealing pattern.

## 2. Scope, dependency boundaries and non-goals

B04 and accepted authorship S1 are implementation prerequisites. Preparation
requires no READY state, Review/Decision, ApprovalRequest or grant. A Publication
may be DRAFTING, INTERNAL_REVIEW or, when enabled by its owner, READY; its Project
must be ACTIVE. No command creates or changes those Publication states.

B12/B13 remain independent: a favorable preparation Decision does not create a
package; creating a package neither issues nor consumes a grant. Full freeze
still needs the separately accepted READY, review, Decision, approval/consumption
and consent-withdrawal/offboarding bindings. S2 consent must not be used as a
production freeze gate before those bindings exist.

Only PREPARED→WITHDRAWN is enabled here. This is OWNER withdrawal of a package,
not an author's WITHDRAWN consent, not Publication withdrawal and not grant
revocation. Full-model FROZEN/SUPERSEDED states remain disabled. No new runtime
dependency, infrastructure, canonical object, receipt or persistence mechanism.

## 3. Invariants and conservative judgments

1. **Exact context.** Publication determines Project. Manuscript and snapshot use
   same-Publication composite FKs. Snapshot authors, contributions, corresponding
   subset and equal groups retain S1's sealed attribution rules and hashes.
   Package manuscript/snapshot IDs and non-consent occurrences never change,
   even before consent. New context requires a new package and fresh consent.
2. **Occurrences, not sets.** Project the sealed manuscript's direct FIGURE,
   TABLE, CITATION, CLAIM and CONCLUSION placements. Per category sort by
   `(section_id COLLATE "C", placement ordinal)` and assign contiguous 0-based
   manifest ordinals. Claim/conclusion share a placement table but are projected
   separately. Preserve multiplicity; no unique package+target constraint.
   OTHER artifact role fails closed. Document artifact and snapshot occur only
   in top-level context. Transitive inputs are verified through B04, not appended
   as direct occurrences; citations never establish scientific support.
3. **Root consent.** Derive actor from VerifiedPrincipal; require live HUMAN
   identity, effective project read entitlement and exact snapshot author
   membership. No RESEARCHER/OWNER role is required of an author holding VIEWER.
   No Agent, acting_on_behalf_of or corresponding-author substitute. Only
   PREPARED_PACKAGE/GRANTED/prior_consent_id=NULL is admitted. Frozen accessible
   same-project evidence ArtifactVersion is mandatory, with verified bytes/hash.
   Evidence retention does not authenticate the subject by itself.
4. **No premature consent binding.** Consent is an immutable package/author root,
   separate from stored non-consent items. Missing roots are normal during
   preparation. Preview selects one root per author in authored order and adds
   transient AUTHOR_CONSENT items with 0-based author ordinals. No consent item
   is inserted into the canonical manifest in S2.
5. **Terminal withdrawal.** OWNER may withdraw an existing PREPARED package even
   if its upstream material later becomes STALE/INVALID or evidence bytes become
   unavailable. Require entitlement, package structure and event history, not a
   successful scientific admission gate. Preserve all context, occurrences,
   consents and NULL hashes; increment row_version once and append one event.
   Deny all subsequent new consents and material writes. No reactivation.
6. **Grant boundary.** Package withdrawal makes this package ineligible; it does
   not append a consent withdrawal or modify manuscript-scoped grants. B12/B13
   grants target the exact manuscript, potentially used by another package;
   there is no package-specific grant association in this slice. The S1 resolver
   for atomic staling on *author consent withdrawal* remains deferred. Later
   freeze must independently reject WITHDRAWN packages regardless of grant state.
7. **History and diagnostics.** Historical IDs, attribution, events and consent
   hashes remain reproducible. Current upstream invalidity or missing consent
   is a diagnostic, never permission. Superseded navigation alone does not
   invalidate retained frozen material. Structural/hash contradiction raises
   PROVENANCE_CLOSURE_VIOLATION; do not return a repaired or trusted candidate.

## 4. Proposed commands, closed DTOs and readback

All methods belong to `PreparedSubmissionService`; VerifiedPrincipal is a separate
trusted argument. §11 fixes exact field types. Human/Agent callers use the same
boundary; only direct HUMAN authors can consent.

| Method / DTO | Result and policy |
| --- | --- |
| `prepare_submission(PrepareSubmissionCommand)` | RESEARCHER or OWNER; allocate next same-Publication version_number under parent exclusion, insert PREPARED, server-projected non-consent rows and initial event atomically. Valid FROZEN manuscript and verified S1 snapshot required. |
| `record_author_consent(RecordAuthorConsentCommand)` | Direct HUMAN snapshot author with read entitlement; insert one evidence-backed GRANTED root and R2 hash on an existing PREPARED package. Reverify exact fixed context and current validity; no automatic consent on preparation. |
| `withdraw_prepared_submission(WithdrawPreparedSubmissionCommand)` | OWNER first use; PREPARED→WITHDRAWN with NFC reason and terminal event. Returns saved event on exact entitled replay. |
| `get_prepared_submission(GetPreparedSubmissionQuery)` | Exact package, immutable occurrences, ordered root consents, events and current diagnostics. |
| `get_prepared_submission_history(GetPreparedSubmissionQuery)` | Exact package's 1..2 lifecycle events, ordered initial then withdrawal, plus unchanged context IDs. No global listing or latest pointer. |
| `preview_prepared_submission(GetPreparedSubmissionQuery)` | Exact stored context plus candidate consent items and nonpersisted candidate digest, missing author IDs and diagnostics. |
| `get_author_consent(GetAuthorConsentQuery)` | Exact consent, evidence reference and recomputed R2 hash; project-scoped authorized read. |

Preparation and consent use their canonical record UUID for request identity.
Same UUID, actor and normalized inputs return the saved record with current read
entitlement, including after write-role loss, upstream invalidity or package
withdrawal; different material is IDEMPOTENCY_CONFLICT. Preparation compares saved
context/occurrences, never a new manuscript pointer or fresh projection replacing
them. Root consent compares exact package/evidence, actor, state/scope/prior.
Another UUID cannot create a second root for the same package/author/scope.

Resolve current project read entitlement before exposing a replay comparison,
saved result or UUID collision. An ID found outside the supplied project returns
FORBIDDEN without its context; an absent ID in an authorized project is NOT_FOUND.

Withdrawal replay compares exact package, authenticated actor and NFC reason to
its terminal event. An entitled original actor may replay after OWNER loss;
another actor or changed reason conflicts after entitlement is checked. Replay
returns the saved event, with no new transition. Fresh writes always reauthorize.
All completed replay paths use §12.2's read snapshot; a cache miss starts a fresh
write UoW and rechecks for a concurrent committed result under exclusion.

## 5. Schema and literal hash proposal — registered tables, one forward migration

One forward migration adds the four registered tables `prepared_submission_versions`,
`author_consents`, `prepared_submission_manifest_items` and `prepared_submission_events`,
with the keys, CHECKs, indexes and guards specified in §12.1.
Do not add a snapshot of author relations or copied scientific facts. Package
owns its manuscript/snapshot references; do not add reciprocal snapshot→package
FK or mutable current-package pointer.

Reuse [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md)
exactly: canonical-json-v1 UTF-8, sha256-cjson-v1, type and material_version=1,
NFC strings, lowercase canonical UUIDs/digests, explicit null optional fields.
AuthorConsent payload has exactly `prepared_submission` idref, `actor` idref,
`consent_state`, `consent_scope`, `evidence_artifact` exact ref, `prior_consent`
(null here). captured_at and attribution timestamps are excluded. The ID-only
package reference avoids a cycle; no provisional package content hash is invented.

Preview uses `PreparedSubmissionVersionManifest` with exact `manuscript_version`,
`authorship_snapshot` refs and items `{category, ordinal, target}` sorted by
category text lexically then ordinal. Item IDs are excluded. Compute a candidate
only for an unwithdrawn package with verified VALID closure and every root consent
and evidence. Otherwise return NULL plus diagnostics. Do not persist this digest,
package content hash, consent-manifest rows or frozen_at. A future freeze will use
the unchanged R2 PreparedSubmissionVersion payload and consumption receipt.

## 6. Error contract — existing categories only

Use §11.2's existing transport mappings. The older S1 proposal's
SUBMISSION_PACKAGE_INVALID, AUTHOR_CONSENT_* and HASH_MISMATCH labels are not
implemented ErrorCode members; B15 introduces none. Separate malformed input,
missing references, forbidden scope, unsupported transitions and broken provenance.
Never disclose foreign-project material in error details.

## 7. Transactions, concurrency and failure recovery

§12.2 is normative for proposed implementation. Each write uses one synchronous
READ COMMITTED UoW, acquiring a literal SHARE inventory as FIRST SQL, before
SET LOCAL, advisory/row locks, clock or authorization SELECT. No output table is
SHARE-locked then upgraded. Parent/package coordination serializes version
allocation, root consent and withdrawal; uniqueness and deferred triggers guard
the final graph, including direct normal-role SQL.

All required waits precede fresh durable rereads and clock_timestamp() checks.
After `SET CONSTRAINTS ALL IMMEDIATE`, recheck credential, binding, membership,
role bounds and relevant stage using fresh advancing DB time. A further blocking
wait repeats those checks before commit. now()/transaction_timestamp() and caller
time cannot decide authorization. Retry only SQLSTATE 40001/40P01, exactly three
total fresh UoWs, no delay; third conflict is CONCURRENT_MODIFICATION. Do not retry
business denials, 23505, timeout, unknown outcome or lost connection as success.
Uncertain commit requires entitled exact read/replay, not blind reexecution.

Read/preview/history/replay use one REPEATABLE READ, READ ONLY snapshot and no
explicit table, advisory or row locks, including in nested helpers. Snapshot
entitlement plus fresh-clock expiry does not exclude a revocation committed after
the snapshot began. No read performs grant maintenance or writes a preview cache.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

§12.4 pins test artifacts and cases. Tests must exercise accepted Application
fixture paths and real PostgreSQL 18.x. Do not disable manuscript seals, forge
READY, use SQLite, or report planned tests as evidence. Failure injection must
show zero partial package/items/events/consent rows and unchanged grant receipts.

## 9. Acceptance criteria and evidence boundary

B15 acceptance requires exact PREPARED/context/occurrence persistence, direct root
consent evidence and hashes, immutable history, lock-free reads, OWNER withdrawal,
controlled race/expiry evidence, normal-role SQL guards and dependency regressions.
Neither B15 nor a complete preview establishes full PR2-17 acceptance, package
freeze, Human Gate, TDG2 or Phase 2 completion. Retain exact commands/counts and
unavailable checks; stop after the authorized slice. The owner's loop runs the
whole suite; this drafting task does not.

## 10. Glossary

| Term | Meaning |
| --- | --- |
| B15 / S2 | This backlog item / package-preparation slice following attribution S1. |
| PREPARED / WITHDRAWN | Fixed preparation context / OWNER-terminated package eligibility; neither means sent. |
| Occurrence | One direct manuscript placement, including a repeated exact target. |
| AuthorshipSnapshot | S1 immutable ordered HUMAN attribution and contribution evidence; not approval. |
| Root consent | Direct author's first GRANTED PREPARED_PACKAGE record with no predecessor. |
| Preview | Noncanonical candidate manifest assembled in one read snapshot; no frozen package. |
| ExactReference | Typed UUID and verified content hash from domain/authorship.py; persistence uses concrete FKs. |
| UoW / SHARE | One Application transaction / PostgreSQL table mode excluding ordinary mutations and INSERT phantoms. |
| Deferred constraint trigger | Final-graph validation at commit or SET CONSTRAINTS ALL IMMEDIATE, as in 0042. |
| OWNER withdrawal | Package lifecycle event; distinct from author consent withdrawal and grant revocation. |
| PREPARE_SUBMISSION | B12 Decision/approval purpose; only a later FREEZE_PREPARED_SUBMISSION consumes its grant. |

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

| Decision | Adopted proposal |
| --- | --- |
| Stage | Preparation works before READY, only in DRAFTING/INTERNAL_REVIEW/READY on ACTIVE Project; no lifecycle transition added. |
| Admission | Manuscript exactly FROZEN and currently VALID; immutable same-Publication S1 snapshot/hash/contribution coverage. Historical SUPERSEDED dependencies remain resolvable. |
| Context editing | Forbidden from creation, before or after consent. New package ID for corrections. |
| Manifest limit | Non-consent occurrences + snapshot author count ≤10,000 at creation, reserving room for one future consent per author; no truncation. |
| Consent | One direct HUMAN GRANTED root; actor derived, evidence mandatory; all successors and offboarding deferred. |
| Package withdrawal | Only PREPARED→WITHDRAWN; OWNER first use, reason required, exact historical replay; no grant/consent/Publication mutation (§3.6). |
| Surface | Application-only slice; no API routes or CLI commands added. Pin mappings now for consistent later exposure. |

### 11.2 Pinned error mappings

These pairs match [api/errors.py](../../src/researchbase/api/errors.py) `_STATUS`
and [cli/errors.py](../../src/researchbase/cli/errors.py) `CLI_EXIT_CODES`.

| ErrorCode | HTTP | CLI | B15 use |
| --- | --- | --- | --- |
| VALIDATION_ERROR | 422 | 2 | Extra/wrong fields, limits, Unicode, enum or digest syntax. |
| AUTHENTICATION_REQUIRED | 401 | 3 | Missing verified principal. |
| FORBIDDEN | 403 | 3 | Wrong project, missing current entitlement/role, nonauthor/proxy consent. |
| NOT_FOUND | 404 | 3 | Absent exact ID after authorized project resolution. |
| VERSION_NOT_FROZEN | 409 | 4 | Existing manuscript/evidence lacks required frozen material at admission. |
| FROZEN_REFERENCE_REQUIRED | 409 | 5 | Required formal frozen dependency unavailable. |
| INVALID_STATE_TRANSITION | 409 | 4 | New consent on withdrawn package; disabled lifecycle/successor consent; invalid upstream admission. |
| IMMUTABLE_RECORD | 409 | 4 | Retarget, late item insertion, UPDATE/DELETE of sealed history. |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Same UUID/different normalized request or changed withdrawal replay. |
| CONCURRENT_MODIFICATION | 409 | 4 | Another UUID already owns consent root; unexpected unique conflict; exhausted 40001/40P01 retries. |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Concrete FK failure. |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Corrupt hash/history, wrong parent, occurrence mismatch, unsupported OTHER placement or over-limit stored closure. |

Expected missing consent gives preview diagnostics, not an exception. Observed
upstream STALE/INVALID gives history diagnostics and no candidate; corrupted
material raises the provenance error. No catch-all error becomes successful replay.

Package history may retain verified reference metadata when ArtifactStore bytes
are unavailable, with DEPENDENCY_UNAVAILABLE and no candidate. Exact consent read
or fresh consent admission requiring that evidence fails FROZEN_REFERENCE_REQUIRED
if bytes are unavailable; bytes/hash contradiction is a provenance error. Neither
absence nor corruption silently becomes valid evidence.

### 11.3 DTO fields, Python types, limits and enums

Use frozen, slotted dataclasses and closed adapters, matching S1. UUID fields
require `type(value) is UUID`; integers exclude bool. NFC reason is 1..10,000
characters, nonblank, preserves meaningful whitespace; reject NUL/unpaired
surrogates. Digests are exactly 64 lowercase hex characters. Datetimes are aware
UTC DB instants. No caller status, actor, version, hash, clock or raw manifest.

```python
PackageStatus = Literal['PREPARED', 'WITHDRAWN']
ConsentState = Literal['GRANTED']
ConsentScope = Literal['PREPARED_PACKAGE']
Category = Literal['FIGURE', 'TABLE', 'CITATION', 'CLAIM', 'CONCLUSION', 'AUTHOR_CONSENT']
Validity = Literal['NOT_FROZEN', 'STALE', 'INVALID']
ValidityReason = Literal['NOT_FROZEN', 'CONSENT_MISSING', 'UPSTREAM_INVALID',
                         'UPSTREAM_STALE', 'PACKAGE_WITHDRAWN', 'DEPENDENCY_UNAVAILABLE']
# Separate required-field DTOs, no defaults:
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
    consent_scope: ConsentScope
    evidence_artifact_version_id: UUID
    prior_consent_id: None
WithdrawPreparedSubmissionCommand:
    project_id: UUID
    prepared_submission_version_id: UUID
    reason: str
GetPreparedSubmissionQuery:  # also history and preview
    project_id: UUID
    prepared_submission_version_id: UUID
GetAuthorConsentQuery:
    project_id: UUID
    id: UUID
```

Readbacks use existing `ExactReference` with category/type validation (not a
polymorphic persistence locator). Every field below is required, including NULLs.

| DTO | Exact fields |
| --- | --- |
| ManifestItemReadback | `id: UUID`, `category: Category`, `ordinal: int` (0..9999), `target: ExactReference`; persisted S2 items exclude AUTHOR_CONSENT. |
| AuthorConsentReadback | `id: UUID`, `project_id: UUID`, `prepared_submission_version_id: UUID`, `actor_id: UUID`, `consent_state: ConsentState`, `consent_scope: ConsentScope`, `evidence_artifact: ExactReference` (ArtifactVersion), `prior_consent: None`, `captured_at: datetime`, `content_hash: str`, `hash_scheme: Literal['sha256-cjson-v1']`. |
| PreparedSubmissionEventReadback | `id: UUID`, `prepared_submission_version_id: UUID`, `prior_status: Literal['PREPARED'] \| None`, `new_status: PackageStatus`, `actor_id: UUID`, `occurred_at: datetime`, `reason: str \| None`. |
| PreparedSubmissionReadback | `id: UUID`, `project_id: UUID`, `publication_id: UUID`, `version_number: int`, `manuscript_version_id: UUID`, `authorship_snapshot_id: UUID`, `status: PackageStatus`, `row_version: int`, `package_manifest_hash: None`, `content_hash: None`, `hash_scheme: Literal['sha256-cjson-v1']`, `frozen_at: None`, `created_by: UUID`, `created_at: datetime`, `items: tuple[ManifestItemReadback,...]`, `consents: tuple[AuthorConsentReadback,...]`, `events: tuple[PreparedSubmissionEventReadback,...]`, `grant_id: None`, `consumption_id: None`, `current_validity: Validity`, `validity_reasons: tuple[ValidityReason,...]`. |
| PreparedSubmissionHistory | `prepared_submission_version_id: UUID`, `publication_id: UUID`, `manuscript_version_id: UUID`, `authorship_snapshot_id: UUID`, `events: tuple[PreparedSubmissionEventReadback,...]`. |
| PreparedSubmissionPreview | `prepared_submission_version_id: UUID`, `items: tuple[ManifestItemReadback,...]`, `candidate_manifest_hash: str \| None`, `missing_author_ids: tuple[UUID,...]`, `current_validity: Validity`, `validity_reasons: tuple[ValidityReason,...]`. |

Counts: S1 retains 1..100 authors, 1..1000 contributions, 1..100 corresponding
subset and ≤50 disjoint equal groups. Roots ≤100; events 1..2; version_number
1..2,147,483,647 (exhaustion denies, no wrap); row_version 1 or 2. Readback items
sort category text/ordinal; consents and missing IDs follow authored order; reasons
are sorted distinct enum values, ≤6. Preview consent item ID is the consent UUID,
transient only. INVALID dominates STALE; withdrawal is STALE; otherwise package
is NOT_FROZEN, even with a complete digest. NOT_FROZEN always remains a reason;
CONSENT_MISSING alone does not assert scientific invalidity. No VALID package
result is possible in S2. These are proposed bounded projections, not changes to
B04's VALID/STALE/INVALID upstream evaluator.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch with types and constraint names

Create one forward revision under `migrations/versions/` after the reconciled head;
never edit old migrations. The following compact templates are exhaustive for S2.
`T` is the literal table name. BASE(T) = `id UUID CONSTRAINT pk_T PRIMARY KEY`,
`created_at TIMESTAMPTZ NOT NULL`, `created_by UUID NOT NULL CONSTRAINT
fk_T_created_by REFERENCES actors(id) ON DELETE RESTRICT`. Other columns below
are NOT NULL unless `NULL` is shown. Each `fk(column, table)` means a named
`fk_T_column` UUID FK to `table(id) ON DELETE RESTRICT`. All generated names fit
63 bytes; use `ps_manifest` for the manifest table token when a name exceeds 63,
as in S1's naming rule. No silent PostgreSQL name truncation.

| Table after BASE | Columns | Named keys/checks (prefix on this table) |
| --- | --- | --- |
| prepared_submission_versions | `publication_id UUID fk(publications)`, `version_number INTEGER`, `manuscript_version_id UUID`, `authorship_snapshot_id UUID`, `status VARCHAR(16)`, `package_manifest_hash CHAR(64) NULL`, `content_hash CHAR(64) NULL`, `hash_scheme VARCHAR(32)`, `frozen_at TIMESTAMPTZ NULL`, `row_version INTEGER` | `uq_b15_package_parent(publication_id,id)`; `uq_b15_package_number(publication_id,version_number)`; `ck_b15_package_number`: >0; `ck_b15_package_status`: PREPARED/WITHDRAWN only; `ck_b15_package_hash_state`: all three nullable fields IS NULL; `ck_b15_package_scheme`: sha256-cjson-v1; `ck_b15_package_row_version`: (PREPARED,1) or (WITHDRAWN,2). |
| author_consents | `prepared_submission_version_id UUID fk(prepared_submission_versions)`, `actor_id UUID fk(actors)`, `consent_state VARCHAR(16)`, `consent_scope VARCHAR(24)`, `evidence_artifact_version_id UUID fk(artifact_versions)`, `prior_consent_id UUID NULL fk(author_consents)`, `captured_at TIMESTAMPTZ`, `content_hash CHAR(64)`, `hash_scheme VARCHAR(32)` | `uq_b15_consent_package(prepared_submission_version_id,id)`; `ck_b15_consent_root`: state=GRANTED AND scope=PREPARED_PACKAGE AND prior_consent_id IS NULL; `ck_b15_consent_actor`: actor_id=created_by; `ck_b15_consent_hash`: lowercase 64 hex and scheme=sha256-cjson-v1; `ck_b15_consent_time`: captured_at=created_at and finite. |
| prepared_submission_manifest_items | `prepared_submission_version_id UUID fk(prepared_submission_versions)`, `category VARCHAR(24)`, `ordinal INTEGER`, nullable concrete UUID FKs `artifact_version_id`, `source_version_id`, `claim_version_id`, `scientific_conclusion_version_id`, `author_consent_id` | Targets respectively artifact_versions/source_versions/claim_versions/scientific_conclusion_versions/author_consents. `uq_b15_manifest_position(prepared_submission_version_id,category,ordinal)`; `ck_b15_manifest_ordinal`: 0..9999; `ck_b15_manifest_target`: exact category-XOR below; `ck_b15_manifest_s2`: category<>AUTHOR_CONSENT AND author_consent_id IS NULL. |
| prepared_submission_events | `prepared_submission_version_id UUID fk(prepared_submission_versions)`, `prior_status VARCHAR(16) NULL`, `new_status VARCHAR(16)`, `actor_id UUID fk(actors)`, `occurred_at TIMESTAMPTZ`, `reason TEXT NULL` | `uq_b15_package_event(prepared_submission_version_id,new_status)`; `ck_b15_event_actor`: actor_id=created_by; `ck_b15_event_time`: occurred_at=created_at and finite; `ck_b15_event_transition`: initial NULL→PREPARED/reason NULL, or PREPARED→WITHDRAWN/reason required; `ck_b15_event_reason`: NULL or nonblank NFC 1..10000. |

Exact composite FKs and XOR expression:

```sql
-- prepared_submission_versions
CONSTRAINT fk_b15_manuscript_parent FOREIGN KEY (publication_id,manuscript_version_id)
  REFERENCES manuscript_versions(publication_id,id) ON DELETE RESTRICT
CONSTRAINT fk_b15_snapshot_parent FOREIGN KEY (publication_id,authorship_snapshot_id)
  REFERENCES authorship_snapshots(publication_id,id) ON DELETE RESTRICT
-- manifest consent edge: add after both tables exist, despite being disabled in S2
CONSTRAINT fk_b15_manifest_consent FOREIGN KEY (prepared_submission_version_id,author_consent_id)
  REFERENCES author_consents(prepared_submission_version_id,id) ON DELETE RESTRICT
-- ck_b15_manifest_target
num_nonnulls(artifact_version_id,source_version_id,claim_version_id,
  scientific_conclusion_version_id,author_consent_id)=1 AND (
  (category IN ('FIGURE','TABLE') AND artifact_version_id IS NOT NULL) OR
  (category='CITATION' AND source_version_id IS NOT NULL) OR
  (category='CLAIM' AND claim_version_id IS NOT NULL) OR
  (category='CONCLUSION' AND scientific_conclusion_version_id IS NOT NULL) OR
  (category='AUTHOR_CONSENT' AND author_consent_id IS NOT NULL))
CREATE UNIQUE INDEX uq_author_consents_root ON author_consents
  (prepared_submission_version_id,actor_id,consent_scope) WHERE prior_consent_id IS NULL;
CREATE UNIQUE INDEX uq_author_consents_successor ON author_consents(prior_consent_id)
  WHERE prior_consent_id IS NOT NULL; -- successors remain prohibited by S2 CHECK
```

Use individual target FKs except author_consent_id, which uses the composite FK.
Add `ix_T_column` B-tree for every FK whose column is not already a leading
PK/unique index column, including created_by, manuscript/snapshot/target IDs,
consent actor/evidence/prior and event actor. Add
`ix_b15_consent_history(prepared_submission_version_id,actor_id,captured_at,id)`
and `ix_b15_event_history(prepared_submission_version_id,occurred_at,id)`.
No FROZEN partial index or receipt FK is needed while freeze is disabled.

SQL CHECKs alone cannot seal an aggregate. Use existing PostgreSQL trigger patterns:

| Named guard / timing | Required enforcement |
| --- | --- |
| `b15_package_guard`, BEFORE INSERT/UPDATE/DELETE on packages | Insert only PREPARED/row_version=1 with same-parent FROZEN manuscript and verified sealed snapshot structure. No DELETE. UPDATE only previously committed PREPARED→WITHDRAWN/row_version+1; every other column unchanged. No UPDATE to make a committed row appear newly created. |
| `b15_manifest_guard`, BEFORE INSERT/UPDATE/DELETE on items | No UPDATE/DELETE; INSERT only while parent PREPARED, row_version=1 and native xmin equals pg_current_xact_id()::xid; lock parent. created_by/time equal package creation attribution. A committed empty manifest is sealed too. |
| `b15_consent_guard`, BEFORE INSERT on consents | Lock exact package; PREPARED only, direct HUMAN snapshot author, GRANTED root only, evidence exact frozen same-project; actor=created_by. Root uniqueness serializes even normal-role SQL. Application separately verifies trusted subject and ArtifactStore bytes/hash. |
| `b15_immutable_consents`, `b15_immutable_events`, BEFORE UPDATE/DELETE | Reject every mutation/deletion. |
| `b15_manifest_complete`, DEFERRABLE INITIALLY DEFERRED constraint triggers AFTER INSERT on package/items | Complete five-category occurrence projection equals manuscript projection in multiplicity and ordinal, total occurrences+authors ≤10000, exact same-project targets and 0-based gap-free category order; S1 snapshot has valid HUMAN contribution coverage. Zero occurrences legal. Recheck sealed graph, not latest pointers. |
| `b15_package_events`, DEFERRABLE INITIALLY DEFERRED constraint triggers AFTER INSERT/UPDATE on package and AFTER INSERT on events | Exactly one initial event with package creator/time; optional single terminal event iff WITHDRAWN/row_version=2. Transition event must match OLD/NEW and observed actor/time, no orphan/forged success event, immutable initial event cannot be replaced. OWNER authorization is Application policy checked at fresh time. |

Install one constraint trigger per listed table/event with suffix `_package`,
`_items` or `_events`; functions may be shared. Follow 0042's final-graph approach,
using 0057's native XID comparison, not bigint epoch comparisons or new seal flags.
Application recomputes R2 hashes and verifies bytes; SQL guards independently
check references, aggregates, immutable sets and legal transitions. Normal-role SQL
must retain required preheld snapshot protection; no trigger-disable/owner rights.
Map named guard failures: sealed/immutable→IMMUTABLE_RECORD;
aggregate/history/parent→PROVENANCE_CLOSURE_VIOLATION;
closed transition/root-state→INVALID_STATE_TRANSITION. Existing 23503 maps to
REFERENTIAL_INTEGRITY_ERROR; 23514/23502 malformed shape→VALIDATION_ERROR;
23505→CONCURRENT_MODIFICATION after entitled replay comparison. Unknown errors
fail closed via existing sanitized UoW handling. No generic exception retry.
Clean upgrade/downgrade must work; populated downgrade refuses rather than dropping
scientific history, preserving earlier revisions byte-for-byte.

### 12.2 Exact lock order and transactions

Define literal `B15_SNAPSHOT_TABLES` in the new repository. This is the current
B11 closure inventory plus S1 immutable authorship inputs, spelled out for review;
do not dynamically import private inventories or scan/lock the whole schema:

```text
actor_subject_bindings actors artifact_versions artifacts audit_findings
authorship_snapshot_authors authorship_snapshot_contributions
authorship_snapshot_corresponding_authors authorship_snapshot_equal_groups
authorship_snapshots claim_versions claims contribution_records correction_records
dataset_snapshots datasets evidence_relations experiment_spec_versions experiment_specs
impact_assessments impact_targets internal_review_records literature_evidence
literature_evidence_relations literature_evidence_review_events literature_source_project_links
literature_sources literature_support_snapshots manuscript_artifact_placements
manuscript_citation_placements manuscript_claim_placements manuscript_versions
measurements metric_definition_versions metric_definitions project_membership_events
project_memberships project_role_assignments projects publications review_issue_events
review_issues run_artifact_inputs run_dataset_inputs runs scientific_conclusion_claim_inputs
scientific_conclusion_literature_inputs scientific_conclusion_versions scientific_conclusions
source_versions statistical_result_inputs statistical_results
```

Use those names in lexical order in one `LOCK TABLE ... IN SHARE MODE` statement,
FIRST SQL in a new READ COMMITTED UoW. All commands use the same inventory; package,
manifest, consent and package-event output tables are excluded. No table-mode
upgrade. Then SET LOCAL lock_timeout='10s', statement_timeout='30s'. Configuring
isolation/autoflush on the fresh connection must not execute a preceding SELECT.

| Command | Exact subsequent sequence after FIRST SHARE and timeouts |
| --- | --- |
| prepare_submission | Advisory `pg_advisory_xact_lock(hashtextextended(:key,0))`, key=`b15:prepare:{id}`; manuscript row FOR UPDATE by exact ID; Publication FOR UPDATE, verify project; reread saved package by command UUID for race replay. For new result, plain snapshot/contribution/placement/closure reads under inventory; verify current authority/stage/hash/validity; allocate max(version_number)+1 under Publication; fresh clock; insert package, category/ordinal-ordered items and initial event; force constraints; final fresh authorization; commit. |
| record_author_consent | Advisory key=`b15:consent:{id}`; plain project-confined package routing read; exact manuscript FOR UPDATE; Publication FOR UPDATE; exact package FOR UPDATE; reread root/saved UUID and complete fixed context; replay/conflict checks. New root: authorize direct HUMAN author, verify evidence and current closure, check PREPARED and no root, fresh clock; insert consent; force constraints; final fresh authorization/stage; commit. All author chains are single roots here; no predecessor/extra actor row lock. |
| withdraw_prepared_submission | Advisory key=`b15:withdraw:{package_id}`; plain project-confined routing; exact manuscript FOR UPDATE; Publication FOR UPDATE; exact package FOR UPDATE; reread package/events; exact terminal replay comparison before first-use OWNER gate. New withdrawal: verify local structural/event history, fresh OWNER authorization, update only status/row_version, insert event using observed DB time; force constraints; final fresh authorization; commit. No scientific admission or grant locks/mutations. |
| get package / history / preview / consent / completed replay | Fresh REPEATABLE READ, READ ONLY UoW configured before SELECT. No SHARE inventory, advisory, FOR UPDATE or FOR SHARE. Plain authorization/project-scoped parent lookup; package/items by category+ordinal, authors/roots in authored order, events in transition order and referenced exact material in UUID order within one snapshot; recompute stored hashes and diagnostics; final fresh-clock read entitlement. No writes, constraints forcing, read-side repair or grant maintenance. |

Every write rereads protected facts after required waits and uses
clock_timestamp() immediately before its effect and after deferred checks (§7).
Do not call S1 public read services inside a write UoW (they open their own
transaction); reuse their material verification with plain repository reads in
the same UoW. `lock_record_publication`, `lock_project` and locking `_authorize`
paths are not read helpers for B15. Reuse pure S1 hash/coverage logic and plain SQL
methods; B04 verify_in_uow and UoW protected-read adapters provide the pattern.

| Participating writer | Compatibility proof required |
| --- | --- |
| B04/manuscript placement and scientific/source/authority writers | SHARE inventory excludes ordinary mutation/INSERT phantoms before snapshot. Existing target-first writers may deadlock; demonstrate bounded whole-UoW 40P01 recovery, never stale success. |
| S1 attribution | Inventory SHARE excludes S1 relation writes; B15 creates no attribution rows. Do not change S1 workflow or public read semantics as incidental work. |
| B11/B12/B09 Decisions/approvals | Shared manuscript→Publication row order; B15 takes no approval scope or grant locks and never waits on a grant while holding a package. Their Publication SHARE is compatible with B15 inventory. |
| B13 lifecycle/consumption; future B14 READY | Their publications SHARE ROW EXCLUSIVE excludes B15's Publication SHARE before snapshot. B15 touches no grants, receipts or Publication state. Both commit orders require regression tests; READY/package result branches remain disabled here. |
| B15 consent / withdrawal / another preparation | Same parent and package exclusion; fresh rechecks after waits. Distinct preparation UUIDs yield distinct ordered versions; one consent root wins; consent-before-withdraw remains history, withdrawal-before-consent denies. |
| Future consent-chain/freeze writers | Must bind accepted manuscript→Publication→package and sorted-author chain exclusion, concrete receipt and grant order before enabling. This matrix does not claim freeze-race acceptance for absent commands. |

### 12.3 Ordered build steps and real file paths

1. Reconcile head and accepted B04/S1; create the forward migration under
   `migrations/versions/` with §12.1's four tables/indexes/guards. Preserve 0046,
   0048, 0057–0059 and all earlier payloads. No approval-result enabling migration.
2. Create `src/researchbase/domain/prepared_submission.py` for finite enums,
   immutable occurrence projection, root consent validation and literal R2 hash
   material. Reuse `domain/authorship.py`, `foundation/hashing.py` and
   `foundation/canonical_json.py`; domain imports no ORM/transport.
3. Create `src/researchbase/application/prepared_submission.py` with §4/§11 DTOs,
   seven service methods, in-UoW verification, replay and three-attempt SQLSTATE
   retry. Reuse B04 verification. Do not call S1 public read services inside a
   write UoW (they open their own transaction); reuse their material verification
   with plain repository reads in the same UoW.
4. Extend `src/researchbase/application/ports.py` with typed package repository/UoW
   protocols; create `src/researchbase/persistence/prepared_submission_repository.py`
   with literal inventory, separate prepare_write/prepare_read, plain exact reads,
   inserts and guarded withdrawal. Extend `src/researchbase/persistence/uow.py`
   for wiring, protected nested reads and opt-in named-constraint normalization;
   reuse existing synchronous Session/transaction infrastructure.
5. Add §12.4 tests using existing fixture builders. No API/CLI in S2; future thin
   adapters belong in `src/researchbase/api/routes.py`, `api/app.py`,
   `src/researchbase/cli/commands/governance.py` and `cli/composition.py` after
   separate authorization; errors retain §11.2 pairs.
6. Run focused static/unit/architecture/PostgreSQL checks, retain evidence and
   unresolved findings, then stop. No dependency, branch, commit or later slice.

### 12.4 Test artifacts and required cases

Files below are planned, not created by this documentation task. PostgreSQL tests
use `phase2_database_url` and accepted Application fixtures. Concurrency proof
needs two backend PIDs, barriers and pg_blocking_pids()/observed wait state; a sleep
alone proves nothing. Capture R4 tx_started_at, expiry_at, lock_wait_started_at,
lock_acquired_at and final authorization_checked_at and zero failed-effect counts.

| File to create | Required cases |
| --- | --- |
| tests/unit/phase2/test_b15_package_contract.py | Closed/frozen DTOs; strict UUID/int/enum/null; NFC/blank/NUL/surrogate reason and 10000/10001 boundaries; 100/101 authors through S1; count reserve and version exhaustion; exact current HTTP/CLI pairs; withdrawal and consent restrictions. |
| tests/unit/phase2/test_b15_package_hash_vectors.py | Independent literal R2 consent and manifest preimages; package ID-only cycle avoidance, prior NULL, captured_at exclusion; lexical category/order, author-order consent, repeated target preservation; unchanged S1/R2/Phase 1 vectors; never persist candidate hashes. |
| tests/integration/phase2/test_b15_package_preparation.py | Accepted B04 freeze→S1 snapshot→PREPARED in DRAFTING/INTERNAL_REVIEW (READY only when accepted); same-parent/validity/byte gates; all five direct categories, repeated targets, empty manifest, OTHER denial; immutable context and separate package for change; version allocation; prepare/consent replay after write-role loss/withdrawal/restart; changed material conflicts. |
| tests/integration/phase2/test_b15_package_consent.py | Each HUMAN author, VIEWER author allowed, owner cannot consent for another, Agent/proxy/nonauthor/wrong-project denied; mandatory frozen accessible verified evidence; hash recomputation; one root, another UUID conflict; prior/state/scope substitutions rejected; withdrawn package denies new consent; no stored AUTHOR_CONSENT item. |
| tests/integration/phase2/test_b15_package_history.py | Exact package/consent/history; candidate absent until all roots/evidence/VALID closure; transient consent order/IDs, all NULL stored hashes; no grants issued/consumed; upstream STALE/INVALID versus corruption; missing evidence diagnostic; supersession navigation harmless; withdrawal preserves rows/roots and suppresses candidate; current roles/credentials and foreign-project nondisclosure. |
| tests/integration/phase2/test_b15_package_withdrawal.py | OWNER first use, VIEWER/RESEARCHER denied; exact terminal replay after OWNER loss, actor/reason conflict; withdraw with invalid/missing upstream evidence; atomic row_version/event and unchanged consent/grant/receipt rows; fail after each insert/update/deferred/final check leaves zero partial result. |
| tests/integration/phase2/test_b15_package_schema.py | Clean/populated upgrade, constraints/index names, native XID seal, clean downgrade/populated refusal, unchanged predecessors; normal-role SQL retarget/delete, late item INSERT even empty, duplicate/root/successor/wrong-parent/forged-event/ordinal/multiplicity violations; 10000 bound; final graph at commit and SET CONSTRAINTS. |
| tests/integration/phase2/test_b15_package_concurrency.py | FIRST-SQL/isolation inventory; same UUID single result, changed replay conflict; two package versions; two roots; consent/withdrawal both commit orders; concurrent scientific/source/authority/B12/B13 writers; first and later required lock wait across expiry deny at equality and after; exact ≤3 40001/40P01 attempts, no timeout/business retry; reads/preview/history/replay acquire no explicit exclusion locks and all nested reads share one snapshot. |
| tests/architecture/test_b15_package_boundaries.py | Common Application boundary, typed ports/DTOs and RESTRICT FKs; no ORM leaks, copied authorship/semantic JSON core, nested write/read UoWs, premature hashes, read locks/writes, enabled freeze/receipt route or send/ExternalEffect. |

Run those files plus current S1 unit/integration/schema/concurrency files,
B04 freeze/migration/races, B12 decision/approval/schema/replay/races and B13
lifecycle/schema regressions. Run Ruff check/format, Pyright, git diff --check and
unit/architecture tests; exact observed counts belong in evidence. Whole-suite
execution belongs to the owner's loop for this drafting task.

### 12.5 Not in this slice

B17 freeze must widen both `ck_b15_package_status` and
`ck_b15_package_row_version` in its own forward migration to support the registered
PREPARED/FROZEN/SUPERSEDED/WITHDRAWN lifecycle.

| Deferred behavior | Required owning contract |
| --- | --- |
| PREPARED→FROZEN, FROZEN→SUPERSEDED/WITHDRAWN; consent-manifest persistence and package hashes | Full freeze contract with READY, exact reviews/Decision, B12/B13 concrete result/event binding and consent chain coordination. |
| Author consent WITHDRAWN/regrant, related-grant staling and offboarded-author access | Consent withdrawal/grant resolution/offboarding contract; root GRANTED is not production-complete consent lifecycle. |
| Publication READY or withdrawal/archive/reset | B14 and later lifecycle contracts; no force-state fixture. |
| Attribution editing/disputes/representatives | Separate scope; S1 attribution is immutable and direct-author-only. |
| Global search/listing, export bundle, signature/PKI, notification/sweeper | Separate authorization; no new runtime dependency here. |
| Actual SubmissionVersion/SubmissionRecord, venue connector or ExternalEffect | Later external-send extension, never implied by preparation. |

## 13. Open questions for the owner — override register

| Owner may override | Decision adopted pending approval |
| --- | --- |
| Preparation before READY? | Yes; immutable FROZEN manuscript is mandatory, READY belongs to later freeze. |
| Manifest coordinate policy? | S1 occurrence refinement, C-collated section order then placement ordinal, category-local coordinates; repeated targets retained. |
| Reserve consent capacity now? | Yes; occurrences+authors ≤10000 avoids a permanently unfreezable prepared context. |
| OWNER withdrawal affect manuscript grants? | No in S2 (§3.6); package is disabled, author roots remain history. Consent withdrawal with atomic grant staling remains separately contracted. |
| Expose transport now? | No; Application-only, existing error mappings pinned for future adapters. |

These are proposed refinements for approval, not unresolved permission to weaken
architecture or start implementation. Material overrides require contract revision
and architecture review where applicable.

## 14. Documentation verification note

Only this draft is changed. B15 implementation/tests above are planned. Current
repository verification commands and exact observed results are recorded below;
no implementation, PR2-17 acceptance or Phase gate claim follows.

Verification used the installed shared environment without dependency sync. Every
`uv` command had this exact common environment prefix (additional pytest variables
are shown with their commands):

```sh
UV_CACHE_DIR=/tmp/researchbase-b15-uv-cache UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv
```

| Exact command after common prefix | Observed result |
| --- | --- |
| `uv run --no-sync ruff check .` | PASS: All checks passed! |
| `uv run --no-sync ruff format --check .` | PASS: 639 files already formatted. |
| `uv run --no-sync pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject` | PASS: 0 errors, 0 warnings, 0 informations. |
| `PYTHONPATH=src RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run --no-sync pytest tests/unit tests/architecture --tb=short > /tmp/researchbase-b15-unit-architecture.log 2>&1` | Exit 1: 5,105 passed, 4 failed, 12 errors, 8 warnings in 64.19s; not PASS. |

The exact focused PostgreSQL command, also with that common prefix:

```sh
PYTHONPATH=src DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres uv run --no-sync pytest tests/integration/phase2/test_pr2_17_authorship.py tests/integration/phase2/test_pr2_17_authorship_schema.py tests/integration/phase2/test_pr2_17_authorship_concurrency.py tests/integration/phase2/test_b04_manuscript_freeze.py tests/integration/phase2/test_b04_manuscript_migration.py tests/integration/phase2/test_b04_manuscript_races.py tests/integration/phase2/test_b12_prepare_decision.py tests/integration/phase2/test_b12_prepare_approval.py tests/integration/phase2/test_b12_prepare_replay.py tests/integration/phase2/test_b12_prepare_schema.py tests/integration/phase2/test_b12_prepare_races.py tests/integration/phase2/test_b13_grant_lifecycle.py tests/integration/phase2/test_b13_grant_schema.py -x --tb=short > /tmp/researchbase-b15-postgres.log 2>&1
```

Result: exit 1, **1 setup error in 0.68s**; stopped at the first S1 test before
any database assertion. Remaining cases were not run. Localhost PostgreSQL
connections were denied with `Operation not permitted`; server version was not
verified and no PostgreSQL check is reported PASS. The unit/architecture run's
four failures are HG1 Unix socket operations denied by the sandbox; its twelve
PR2-19 architecture setup errors are denied PostgreSQL connections. Warnings are
existing Alembic path_separator deprecations. No whole-suite run was performed.

`git diff --check` and
`git diff --no-index --check /dev/null docs/proposals/B15_Package_Preparation_Contract_DRAFT.md`
passed with no whitespace errors. Only the requested draft is added; no source,
test, migration, dependency, governing document, branch or commit is changed.

A local Python pathlib/regex/AST check also verified all 30 relative links, the
required status, 14 numbered sections and all 12 HTTP/CLI mappings against the
current source dictionaries.
