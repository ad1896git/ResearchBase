# PR2-02 — SourceVersion lifecycle and source merge execution pack v1.0

**Status:** frozen design subject for independent review; implementation is not authorized until the pack review returns P0=0, P1=0 and `READY_FOR_PR2_02_IMPLEMENTATION=YES`.
**Purpose:** implement immutable literature source versions and execute only globally approved, basis-current source merges.
**Starting accepted lineage:** PR2-00; PR2-01; source merge governance bridge (design `89bbad27f1e636182fcd5d9804a33612a755502f`, final remediation implementation `1f275548d3c52e9a66043fd7ab95fdd7b9e88317`, evidence `f586af0afbd34e89cd5ecfe9edeb04c55e182c86`, independent passing review recorded in `de067f5489c9fb4016d65b1f7aa1d072377bd33e`).
**Migration parent:** `0021a_source_merge_gov_guards`.
**Migration revision:** `0022_source_version_and_merge_lineage`.
**Phase 1 baseline:** `d2400fbeca835c89bd802a4e9d647bda01cfd115`, tag object `63f6a1d28afa79ce8620fc9233793ab9c40a515d`.

## 1. Authority and precedence

Apply this precedence for this PR:

1. Frozen Phase 1 semantics and the System Architecture.
2. Explicit later corrections/addenda A18–A22 and their admitted R2/R3/R4 contracts.
3. Global Schema and Contract Registry.
4. The accepted source-merge governance bridge design and migration contract, including the V4/V5 human decisions recorded in ADR-0010, its accepted pack, and the later normative correction `PR2-02-GOV_Idempotency_Contract_Correction_v1.0.md`.
5. Phase 2 field contract 13, hash contract 15, identity/source contract 16, governance contract 17, targeted R3/R4 amendments 18/19, and Phase 2 development specification 05 for uncorrected detail.
6. This execution pack for the bounded PR implementation details.

This pack does not revise a higher-level hash payload or existing schema contract. It uses the exact SourceVersion and SourceMergeRecord payloads in contract 15, the version and merge fields in contract 13, and the typed proposal/approval lifecycle in ADR-0010 and the accepted governance pack. The explicit global merge approval policy remains: every project with an effective link to either source at the frozen basis must approve through an effective Human Owner; approval of a different direction or basis does not carry forward.

## 2. Purpose and dependencies

PR2-02 adds versioned bibliographic/content state to the already-existing global `LiteratureSource` identities, and a non-destructive operation for merging duplicate global source identities. It consumes the accepted `SourceMergeProposal` and `SourceMergeApproval` records. The proposal bridge owns proposal identity, frozen basis, affected project set, approvals, rejection and proposal lifecycle. PR2-02 owns the actual source merge effect and SourceVersion lifecycle.

Dependencies:

- PR2-00 membership, OWNER, verified principal and credential rules are accepted and unchanged.
- PR2-01 global source identity, immutable source identifier identity, normalization, identifier verification/rejection history, project links, durable receipts and lock discipline are accepted and unchanged.
- Governance bridge migrations `0021` and `0021a` are accepted. Migration `0022` must extend its frozen source-version basis and stale-event guard to real SourceVersion references before accepting new submissions.
- Frozen ArtifactVersion identity/hash/storage is used for full text and correction/retraction evidence; bytes remain in ArtifactStore.

## 3. In-scope and out-of-scope

### In scope

- `SourceVersion` draft creation, draft edits, freeze, abandonment, immutable frozen content, version numbering and source `current_version_id`.
- Exact content hash verification using the already-frozen `SourceVersion` hash contract.
- Optional full-text and required correction/retraction references to exact frozen `ArtifactVersion` rows.
- Corrected/retracted version lineage without rewriting the predecessor.
- Migration 0022 adding SourceVersion and SourceMergeRecord schema, `current_version_id`, MERGED source state and same-source alias pointer; updating bridge version-basis references/guards; constraints, indexes and triggers.
- Actual merge of two eligible sources only by consuming a complete, current, globally approved typed proposal.
- Durable SourceMergeRecord, canonical alias/root resolution, history preservation and deterministic replay.
- Identifier treatment limited to non-mutating canonical resolution and mechanically safe carry-forward as defined in §9.
- Minimal Application, Persistence, HTTP and CLI surfaces for SourceVersion and merge commands.

### Out of scope

- Search plans, provider/API retrieval, query/result provenance, LiteratureEvidence extraction, claim support, prior-art assessment, citation/manuscript/publication workflows, generic governance, Agent Runtime, and provider adapters.
- A generic identifier resolver, identifier conflict adjudication, automatic scientific equivalence inference, or any mutation/rebinding/reparenting of SourceIdentifier rows.
- Changes to PR2-00 or PR2-01 behavior or accepted migrations 0019, 0020, 0021, 0021a.
- New SourceVersion lifecycle values, hash payloads, ArtifactVersion behavior, or generic workflow/schema frameworks.

PR2-01’s shared-source identifier rejection remains fail-closed. No cross-project identifier rejection/rebinding command is added here. Rejected identifiers remain immutable history. A conflict that cannot be represented by the existing unique/effective identifier state is preserved as unresolved and is not resolved by this PR.

## 4. Migration 0022

Revision is `0022_source_version_and_merge_lineage`; parent is exactly `0021a_source_merge_gov_guards`. It must be the unique Alembic head. It may not rewrite or amend revisions 0019, 0020, 0021 or 0021a.

### 4.1 `source_versions`

Use the exhaustive contract 13 columns, plus shared contract columns:

- `id UUID PRIMARY KEY`
- `literature_source_id UUID NOT NULL` FK `literature_sources(id)` RESTRICT
- `version_number INTEGER NOT NULL CHECK > 0`
- `version_kind VARCHAR(32) NOT NULL` CHECK in `SUBMITTED, PREPRINT, REVISED_PREPRINT, ACCEPTED, PUBLISHED, CORRECTED, RETRACTED, WEB_SNAPSHOT, OTHER`
- `predecessor_source_version_id UUID NULL`
- `correction_basis_artifact_version_id UUID NULL`
- `title TEXT NOT NULL` and nonblank after NFC normalization
- `abstract TEXT NULL`
- `authors JSONB NOT NULL`, closed schema list in published order; each row has exactly `name` (NFC nonblank string) and `orcid` (NFC string or null)
- `publication_date DATE NULL`, `venue TEXT NULL`, `external_version_label TEXT NULL`
- `fulltext_artifact_version_id UUID NULL` concrete FK to `artifact_versions(id)` RESTRICT
- `metadata JSONB NULL`, exactly the six contract keys `journal_identifier`, `volume`, `issue`, `pages`, `license_label`, `public_repository_label`, each string-or-null
- `status VARCHAR(16) NOT NULL` CHECK `DRAFT, FROZEN, SUPERSEDED, ABANDONED`
- `content_hash CHAR(64) NULL`, `hash_scheme VARCHAR(32) NOT NULL` and fixed to `sha256-cjson-v1`, `frozen_at TIMESTAMPTZ NULL`
- shared `created_by` Actor FK RESTRICT and `created_at TIMESTAMPTZ NOT NULL`

Constraints: unique `(literature_source_id,version_number)` and `(literature_source_id,id)`; composite predecessor same-source FK; FKs indexed; all deletes RESTRICT. Hashes are lowercase 64-hex. DRAFT/ABANDONED require null content hash and null `frozen_at`; FROZEN/SUPERSEDED require both nonnull. CORRECTED and RETRACTED require both predecessor and correction basis. A predecessor must be a previously frozen version on the same source; for CORRECTED/RETRACTED it must equal the source’s current version at freeze. The correction basis must be an independently hash-verified FROZEN ArtifactVersion. A version cannot be its own predecessor; predecessor graph is acyclic. A non-correction kind may include a predecessor only when the external source explicitly identifies it; the Application never infers one.

`literature_sources` gains nullable `current_version_id` and `merged_into_source_id`, plus lifecycle value `MERGED`. `current_version_id` is a composite same-parent FK to `(source_versions.literature_source_id,id)` and a DB guard permits only a FROZEN target belonging to that source. A source with no frozen version has a null pointer. `merged_into_source_id` is null unless status is MERGED; MERGED requires a distinct source ID, and an acyclic root guard prohibits cycles and targets outside the same merge root. ACTIVE/RETIRED rows have no `merged_into_source_id`. The existing source identity fields remain immutable.

### 4.2 `source_merge_records`

Add the registry-defined immutable record with:

- `id UUID PRIMARY KEY`
- `losing_source_id UUID NOT NULL` and `winning_source_id UUID NOT NULL`, both concrete RESTRICT FKs to `literature_sources`, distinct, with one merge record maximum per losing source
- `identity_basis_artifact_version_id UUID NOT NULL` concrete RESTRICT FK to a FROZEN ArtifactVersion and one of the approved proposal’s frozen evidence artifacts
- `reason TEXT NOT NULL` nonblank NFC, equal to the submitted proposal rationale
- `merged_by UUID NOT NULL` Actor FK; `merged_at TIMESTAMPTZ NOT NULL`
- `content_hash CHAR(64) NOT NULL`, `hash_scheme='sha256-cjson-v1'`

Record is append-only and immutable; no source/version/id is deleted, rewritten or reparented. Do not add a proposal FK to this registry-defined record: its material contract remains exactly the existing field contract/hash contract. Instead, a deferred constraint trigger enforces a one-to-one typed bridge through the existing `PROPOSAL_CONSUMED` event: resolve its concrete proposal FK, derive loser/winner from that proposal’s source pair and explicit survivor, and require exact equality with the SourceMergeRecord’s concrete losing/winning FKs. It also verifies actor, rationale, evidence ArtifactVersion membership, complete approval state and request/basis hashes. A unique unordered source-pair guard and unique losing source ensure no second proposal can be consumed for the same identity pair. The bridge event remains the authoritative typed proposal/approval lineage; no generic correlation key is introduced.

Migration adds the SourceVersion columns to each proposal source-basis row as defined by the accepted governance pack, replaces the 0021 empty-version check with nullable ID/hash pair semantics and concrete same-source FK, extends stale-basis validation to current SourceVersion ID/hash/kind/status, and preserves count/seal invariants. Existing proposals whose frozen source basis remains current stay usable; any material mismatch must be terminalized only by the guarded canonical stale path before further approval/merge. A basis mismatch cannot be hidden by resubmission in place. Upgrade from fresh schema and 0021a must be deterministic. Downgrade is allowed only when all 0022-owned SourceVersion/MergeRecord rows are empty and no source pointer/merge/bridge version refs depend on the new schema; otherwise refuse before DDL with a data-preservation error.

Migration also adds the typed append-only `source_version_command_receipts` table for create/update/freeze/abandon idempotency; it does not widen or rewrite PR2-01 `literature_command_receipts`. Columns: `id`, `deployment_id`, `project_id`, `actor_id`, `command_name`, `request_id`, `request_hash`, `hash_scheme`, `result_source_version_id`, `result_dto_version`, `result_dto`, `completed_at`. FKs are concrete and RESTRICT; scope key `(deployment_id,project_id,actor_id,command_name,request_id)` is unique; hash scheme is `sha256-cjson-v1`; each supported command has exactly one SourceVersion result. Result JSON is a versioned public response projection only. INSERT must be complete; UPDATE/DELETE denied. Empty-only downgrade includes this table.

## 5. SourceVersion lifecycle and commands

Persisted lifecycle is exactly `DRAFT → FROZEN → SUPERSEDED` or `DRAFT → ABANDONED`; `SUPERSEDED` and `ABANDONED` are terminal. DRAFT is editable and has SQL NULL content hash/frozen time. Freeze computes the exact R2 material hash, sets FROZEN and `frozen_at`, and updates the source current pointer in the same transaction. If the source had a current version, its status becomes SUPERSEDED atomically with pointer replacement. A FROZEN row’s material columns never change; its one permitted status transition to SUPERSEDED does not rewrite material/hash. Abandoning a draft preserves the row and it cannot be reused. Version numbers are allocated under source lock and never reused.

Version kinds are the exact contract values listed in §4.1. CORRECTED and RETRACTED create new versions with exact predecessor and frozen correction basis; they do not change or delete the predecessor bytes. A RETRACTED current version marks source validity as retracted for downstream quality/validity projections, but does not delete the source, change source identity, or rewrite old provenance. This PR does not implement LiteratureEvidence or impact propagation; later consumers must treat a current RETRACTED version as non-valid input, following Phase 2 contracts.

Application commands, each one synchronous transaction:

- `create_source_version(principal, project_id, source_id, version_kind, fields, predecessor_id?, correction_basis_artifact_version_id?, request_id)` creates a DRAFT under an ACTIVE source linked to the project. It allocates the next unused version number while holding the source lock. OWNER/RESEARCHER only; human/agent caller uses the same Application surface.
- `update_source_version(principal, project_id, source_version_id, fields, request_id)` may change material fields only while DRAFT. It cannot change parent, version number, status, hash, frozen time or original creator attribution.
- `freeze_source_version(principal, project_id, source_version_id, request_id)` verifies full closed material schema and all references, computes hash, supersedes the prior current version if present, and switches the same-source current pointer atomically.
- `abandon_source_version(principal, project_id, source_version_id, request_id)` transitions only DRAFT to ABANDONED; terminal/frozen versions cannot be abandoned. Its immutable command receipt records actor, request hash, time and result status; no unregistered SourceVersionEvent table is added.
- `get_source_version` and `list_source_versions` are project scoped and return exact identities/status/hash, never peer project links; they require an active project membership and direct source link under PR2-01’s read-role rules. `resolve_literature_source` returns the ACTIVE canonical root through `merged_into_source_id`, with the requested historical source ID retained in the response.
- `merge_literature_sources(principal, project_id, proposal_id, identity_basis_artifact_version_id, request_id)` executes a complete approved proposal exactly once. The executor must have an authenticated HUMAN or AGENT principal, active membership and effective OWNER/RESEARCHER role in the supplied project, plus a direct project link to at least one proposal source; all affected-project Human Owner approvals are revalidated separately.

Version command receipts use the accepted PR2-01 scope and exact-replay semantics: authenticate and check current project write entitlement (active membership, direct source link, and effective OWNER/RESEARCHER role) before disclosing a saved result; same scope and same request hash returns the stored version ID/DTO without repeating the transition; same scope with a different hash returns `IDEMPOTENCY_CONFLICT`; rolled-back commands leave no receipt. Closed canonical request payloads are:

```json
{"type":"CREATE_SOURCE_VERSION","material_version":1,"project_id":"<uuid>","source_id":"<uuid>","version_kind":"<enum>","predecessor_source_version_id":"<uuid|null>","correction_basis_artifact_version_id":"<uuid|null>","title":"<string>","abstract":"<string|null>","authors":[{"name":"<string>","orcid":"<string|null>"}],"publication_date":"<date|null>","venue":"<string|null>","external_version_label":"<string|null>","fulltext_artifact_version_id":"<uuid|null>","metadata":"<source-metadata|null>"}
{"type":"UPDATE_SOURCE_VERSION_DRAFT","material_version":1,"project_id":"<uuid>","source_version_id":"<uuid>","version_kind":"<enum>","predecessor_source_version_id":"<uuid|null>","correction_basis_artifact_version_id":"<uuid|null>","title":"<string>","abstract":"<string|null>","authors":[{"name":"<string>","orcid":"<string|null>"}],"publication_date":"<date|null>","venue":"<string|null>","external_version_label":"<string|null>","fulltext_artifact_version_id":"<uuid|null>","metadata":"<source-metadata|null>"}
{"type":"FREEZE_SOURCE_VERSION","material_version":1,"project_id":"<uuid>","source_version_id":"<uuid>"}
{"type":"ABANDON_SOURCE_VERSION","material_version":1,"project_id":"<uuid>","source_version_id":"<uuid>"}
```

Request IDs and transport fields are excluded from payload hashes. Authored text is NFC before hashing, nullable fields are present as explicit nulls, and named structures use their exact closed R2 forms. Command events/replay rows are immutable.

All four SourceVersion write commands acquire locks in this order: preliminary reads only to discover the project/source/version keys; project row; command receipt scope; source row; target SourceVersion row when it exists. Create serializes version-number allocation on the source row. Freeze and abandon lock the target version then reread source pointer and version state. After all required locks and durable rereads, fetch fresh PostgreSQL `clock_timestamp()` and validate the caller’s authenticated verified principal, actor-not-retired state, active membership, effective OWNER/RESEARCHER interval and live credential validity at that instant; only then perform the write and insert its receipt atomically. If a further blocking lock is needed after that authorization, repeat the fresh time and authorization checks. `CURRENT_TIMESTAMP`, `now()` and `transaction_timestamp()` cannot be final authority. Read-only queries do not use a write-authority decision.

Merge consumption uses this exact closed request payload:

```json
{"type":"CONSUME_SOURCE_MERGE_PROPOSAL","material_version":1,"project_id":"<uuid>","proposal_id":"<uuid>","proposal_basis_hash":"<digest>","identity_basis_artifact":{"type":"ArtifactVersion","id":"<uuid>","content_hash":"<digest>"}}
```

Its `request_hash` is SHA-256 of `canonical-json-v1(payload).UTF8`, lowercase hex, scheme `sha256-cjson-v1`; request ID and transport headers are excluded. The canonical project, proposal ID, basis hash and exact identity-basis ArtifactVersion ID/content hash are required payload keys. Its canonical command key is `(deployment_id, actor_id, project_id, command_name='CONSUME_SOURCE_MERGE_PROPOSAL', request_id)`, consistent with the governance idempotency correction. The `source_merge_governance_events.id` UUID remains the event identity; the event row also serves as the durable command receipt for this event-backed command. For `PROPOSAL_CONSUMED`, `basis_hash` equals `proposal_basis_hash`, and its `request_hash`, project, actor, deployment, command name and request ID are copied from this validated request. Exact completed replay authenticates the same actor, verifies current project read entitlement, compares the full command key and hash, and returns the SourceMergeRecord reached through the consumed event without repeating a mutation or requiring current write-role validity. Same key with another hash is `IDEMPOTENCY_CONFLICT`; a different request key against an already consumed proposal is `SOURCE_MERGE_PROPOSAL_ALREADY_CONSUMED`. No incomplete event is a receipt.

Request-hash golden vectors (synthetic values, exact compact canonical JSON UTF-8 preimage, no terminal newline):

```text
CONSUME_SOURCE_MERGE_PROPOSAL
{"identity_basis_artifact":{"content_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","id":"00000000-0000-0000-0000-000000000003","type":"ArtifactVersion"},"material_version":1,"project_id":"00000000-0000-0000-0000-000000000001","proposal_basis_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","proposal_id":"00000000-0000-0000-0000-000000000002","type":"CONSUME_SOURCE_MERGE_PROPOSAL"}
sha256-cjson-v1 = 62716578f10846c0b02c8519e5d9c360cb872ba9ca792be121f8dec5b95aa016

CREATE_SOURCE_VERSION
{"abstract":null,"authors":[{"name":"Ana Lee","orcid":null}],"correction_basis_artifact_version_id":null,"external_version_label":null,"fulltext_artifact_version_id":null,"material_version":1,"metadata":null,"predecessor_source_version_id":null,"project_id":"00000000-0000-0000-0000-000000000001","publication_date":"2024-01-02","source_id":"00000000-0000-0000-0000-000000000002","title":"Café study","type":"CREATE_SOURCE_VERSION","venue":null,"version_kind":"PUBLISHED"}
sha256-cjson-v1 = 1026b626d9d47961cb5d8ac64ca8b96646d2c7c258aa763a5ac8572b41d56853
```

The other SourceVersion command payloads use the exact literals in §5 and the same canonical encoding; tests assert these vectors, explicit-null behavior, NFC normalization, request-ID exclusion and changed request material producing a different digest.

Exact API/CLI DTO shapes follow adjacent PR2-01 and bridge conventions. HTTP routes and CLI commands call the same Application operations and error mapping; actor headers or CLI actor IDs never establish authority.

## 6. SourceVersion hash and artifact contract

Use exactly `SourceVersion.content_hash` in `15_Phase2_Hash_Payload_Contract_R2_v1.0.md`, material version 1. Hash is SHA-256 of `canonical-json-v1(payload).UTF8`, stored lowercase hex with scheme `sha256-cjson-v1`. Exact payload fields and all explicit nulls remain the existing contract; do not hash status, row ID/version number, timestamps, actor, provider responses or unlisted columns. NFC-normalize authored strings before persistence/hash. Author order is meaningful and preserved. Metadata has the closed six-field shape; no provider-specific response objects or secret/config data.

Golden vector required unchanged:

- SourceVersion content hash: `dc89646783c513cbe656a285836705bc8986e871715a837597309024eda2b8ca` for the exact canonical preimage printed in contract 15 §Literature and search.
- Negative tests: changing a material title/author/order/date/fulltext reference or predecessor/correction basis changes the digest; changing excluded status/time/creator does not change it; missing-vs-null, extra metadata keys, malformed hashes, duplicate/invalid reference shape fail before persistence.

The SourceMergeRecord payload is already frozen in contract 15. Add this implementation-level golden vector (all values synthetic):

```text
preimage = {"identity_basis_artifact":{"content_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","id":"00000000-0000-0000-0000-000000000030","type":"ArtifactVersion"},"losing_source":{"id":"00000000-0000-0000-0000-000000000010","type":"LiteratureSource"},"material_version":1,"merged_by":{"id":"00000000-0000-0000-0000-000000000040","type":"ActorIdentity"},"reason":"Duplicate DOI record","type":"SourceMergeRecord","winning_source":{"id":"00000000-0000-0000-0000-000000000020","type":"LiteratureSource"}}
sha256-cjson-v1 = c00555621d772e43f204c3b46689c458823949f590992e9d97a3bf321dd667ca
```

Tests also swap the losing/winning IDs and require a different digest; proposal-survivor validation independently rejects a record whose direction does not match the consumed proposal event.

`fulltext_artifact_version_id` and `correction_basis_artifact_version_id` reference exact ArtifactVersion identities. Before freeze, Application recomputes/validates referenced content hashes and requires FROZEN status. SourceVersion stores no bytes. A referenced ArtifactVersion remains immutable and retrievable through the accepted ArtifactStore path. Full text may be null; correction basis is mandatory for CORRECTED/RETRACTED.

## 7. Global merge authorization and atomic effect

### 7.1 Frozen proposal basis and all-project approvals

The exact accepted SourceMergeProposal basis controls the operation: unordered source pair normalized/sorted by canonical UUID; explicit canonical survivor separately bound; frozen effective project/link set; identifier-state snapshot including rejected history; current SourceVersion ID/hash/kind/status for both sources; rationale and sorted frozen evidence references; proposal basis contract/hash. A→B differs from B→A. The accepted bridge’s canonical basis/hash contract is consumed unchanged.

At merge, recompute and compare exact source rows, all effective extant `literature_source_project_links` to either source, exact link IDs, identifier-state rows, source version/current pointer state and evidence references. Effective links follow the 0020/bridge contract: all extant immutable project/source links, deduplicated by project and sorted; membership, role, source ACTIVE/RETIRED and project lifecycle do not erase a link from the approval set. A project linked to both sources approves once. A newly added link or any material basis change makes the proposal stale and denies merge.

For every frozen affected project require exactly one APPROVE and no REJECT/revocation. At the final authorization time, each approving actor must still be a HUMAN, have a live verified principal/credential and active membership plus effective OWNER assignment for that exact project. Approval must bind to this proposal ID and exact proposal basis hash. Missing, stale, revoked, rejected, wrong-direction, no-longer-authorized, or cross-basis approvals deny. Agents may propose and execute after authorization, but cannot approve.

### 7.2 Deterministic lock order and TEMP-AUTH-01

Use the accepted bridge/PR2-01 lock ordering; acquire no lower-order lock after a later-order row lock:

1. Preliminary reads only to discover lock keys.
2. Lock affected Project rows in ascending canonical UUID order.
3. Lock command/idempotency key.
4. Lock all relevant identifier advisory keys sorted by `(identifier_type, normalized_value)`.
5. Lock both LiteratureSource rows/advisory keys in ascending canonical UUID order.
6. Reread and lock effective project links, identifier rows, current SourceVersion rows and all version basis rows in deterministic primary-key order.
7. Lock the proposal row, then its approvals and governance events in deterministic ID order.
8. Reread durable state and recompute the complete basis and affected-project set. If discovered project scopes differ from locked scopes, abort/retry the entire SERIALIZABLE transaction from a fresh read; never acquire a newly discovered earlier-sorting project lock late.
9. Obtain a fresh PostgreSQL `clock_timestamp()` after every required blocking lock and final reread. Validate caller role, each Human Owner/credential, proposal basis, approvals and mergeability at that instant. If any further blocking wait occurs, repeat the final authorization and basis checks.
10. Insert SourceMergeRecord; update canonical source state/alias; add permitted identifier resolution projection if any; append `PROPOSAL_CONSUMED` event; persist receipt; commit once.

`CURRENT_TIMESTAMP`, `now()` and `transaction_timestamp()` are never final authority for expiry-sensitive checks. Source merge is protected by TEMP-AUTH-01 because project roles, membership, principal verification and credentials can expire or be revoked.

TEMP-AUTH-01 also applies to every create/update/freeze/abandon command in §5, including a replay that the accepted PR2-01 rule subjects to current write entitlement. Each performs the final owner/researcher authorization only after its required locks and durable reread, immediately before a protected write or saved-result disclosure. A second blocking wait causes another fresh check. A completed merge-consumption replay follows the distinct accepted governance-bridge rule in §5: authenticate, match exact event scope and current project read entitlement, then return the historical result without re-executing the merge or revalidating write-role/approval authority.

### 7.3 Merge eligibility, direction, concurrency and replay

Both source rows must exist and be `ACTIVE`, distinct, and not already merged; the survivor must be exactly one of the two source IDs selected in the approved proposal. A retired, already merged, cyclic or otherwise conflicting identity is not mergeable. The losing source becomes `MERGED` with `merged_into_source_id` pointing to the approved survivor; the survivor remains ACTIVE. Source current versions, identifiers, project links and all historical foreign keys stay attached to their original identity. No version or historical scientific reference is reparented. Repeated alias resolution follows the acyclic chain to the active root and never rewrites the requested historical ID. A project-scoped query still requires a direct extant link to the requested source ID; resolving an alias may return the canonical public identity, but version and identifier history are disclosed only when the project has a direct link to the owning source row. Merge does not create, delete, or widen project grants.

After a source becomes MERGED, Application and database guards reject new source-version creation, identifier mutation, and project/source link insertion against that losing ID. Existing immutable link, identifier, version and event rows remain queryable under their original IDs subject to project authorization.

A merge is one serializable transaction. All validation precedes the first protected write. Failure rolls back all merge/consumption/event/receipt writes. Source locks serialize opposite and same-direction requests; the unique losing-source record and proposal consumption guard are database backstops. For same request key and canonical payload, return the saved completed result without repeating mutation. Same key with changed proposal, survivor, basis artifact or payload returns `IDEMPOTENCY_CONFLICT` 409. A second command against a consumed proposal returns `SOURCE_MERGE_PROPOSAL_ALREADY_CONSUMED` 409 unless it is an exact completed receipt replay. A pair already merged by another proposal returns deterministic `SOURCE_NOT_MERGEABLE` 409 with canonical root only if caller is entitled to both through supplied project; otherwise `SOURCE_NOT_FOUND` 404.

### 7.4 SourceMergeRecord hash and lineage

Hash exactly the existing R2 contract 15 `SourceMergeRecord.content_hash` payload, scheme `sha256-cjson-v1`; do not add fields to or change that payload. It binds losing source, winning source, reason, exact frozen identity-basis ArtifactVersion ref and merging actor. The accepted bridge proposal’s immutable basis and per-project approvals are reached through its typed `PROPOSAL_CONSUMED` event. A consumed event and SourceMergeRecord commit in the same transaction. Deferred constraints enforce both directions: every SourceMergeRecord has exactly one matching consumed event, and every consumed event has exactly one SourceMergeRecord. The pair agrees on proposal-derived source direction, actor, rationale, evidence, identity-basis hash and command request hash. Golden tests use contract 15’s existing vectors where supplied and add deterministic source-merge lineage linkage cases; no duplicate generic approval model.

### 7.5 Identifier policy

`SourceIdentifier` identity and verification/history rows are immutable; PR2-02 never changes `literature_source_id`, normalized/raw values, verification state, or rejected predecessor. A resolver may project an identifier’s historical source through the alias chain to the canonical root only when the existing 0020 global uniqueness constraint proves there is at most one effective UNVERIFIED/VERIFIED binding for its normalized `(identifier_type, normalized_value)`. The source merge does not manufacture or duplicate an identifier row. Rejected identifiers remain history and do not occupy the active unique slot.

If any identifier state is contradictory, already corrected/rebound in a way that makes ownership ambiguous, or otherwise cannot satisfy the existing uniqueness/verification contract, do not transfer or resolve it automatically. Preserve every row and refuse the merge as `SOURCE_MERGE_IDENTIFIER_CONFLICT` 409, with no merge effect, until a separately authorized identifier decision path exists. Never infer equivalence from title or metadata. This rule is compatible with the existing bridge basis snapshot: the proposal binds the exact identifier state and becomes stale if it changes.

## 8. Failure contract

Use canonical existing error names where present; these semantic outcomes are required:

| Condition | Error | Transaction and retry |
|---|---|---|
| Missing/unlinked source in supplied project | `SOURCE_NOT_FOUND` 404 | No disclosure or writes; retry only after caller receives link/access. |
| Missing/invalid request fields, closed JSON shape, invalid hash/UUID | `VALIDATION_ERROR` 422 | No writes; caller may correct payload with a new request ID. |
| Missing/expired principal, membership, role or credential | `AUTHENTICATION_REQUIRED` 401 or `FORBIDDEN` 403 per existing mapping | Roll back; fresh authenticated retry only. |
| Missing/hidden proposal | `SOURCE_MERGE_PROPOSAL_NOT_FOUND` or `SOURCE_NOT_FOUND` 404 according to bridge disclosure rule | No writes or peer-project disclosure. |
| Proposal basis, source/link/version/identifier state changed | `SOURCE_MERGE_PROPOSAL_STALE` 409 | Canonical stale event may commit atomically only after the guarded stale precondition is proven; no approval/merge effect. New basis requires a new/superseding proposal. |
| Missing any project approval | `SOURCE_MERGE_APPROVAL_MISSING` 409 | No merge writes; proposal remains pending. |
| Rejection exists | `SOURCE_MERGE_REJECTED` 409 | Rejection remains immutable; no merge; new proposal required. |
| Approval actor is non-human, not current project OWNER, credential invalid, or wrong basis | `SOURCE_MERGE_APPROVAL_FORBIDDEN` 403 or stale 409 per bridge rule | No merge writes. |
| Proposal already consumed | `SOURCE_MERGE_PROPOSAL_ALREADY_CONSUMED` 409 | No writes except exact completed replay. |
| Pair/status/direction invalid or previously merged | `SOURCE_NOT_MERGEABLE` 409 | Roll back; no alternative survivor selection. |
| Identifier ambiguity | `SOURCE_MERGE_IDENTIFIER_CONFLICT` 409 | Roll back; identifiers remain untouched. |
| SourceVersion missing/not draft/not freezable | `SOURCE_VERSION_NOT_FOUND` 404 or `SOURCE_VERSION_NOT_FREEZABLE` 409 | Roll back; no pointer/status/hash change. |
| Version edit after freeze / freeze twice | `SOURCE_VERSION_IMMUTABLE` or `SOURCE_VERSION_ALREADY_FROZEN` 409 | No writes. |
| Invalid predecessor/correction/retraction graph | `INVALID_SOURCE_VERSION_LINEAGE` 409 | Roll back. |
| Exact idempotency key, changed canonical payload | `IDEMPOTENCY_CONFLICT` 409 | Roll back; no result reassignment. |
| Serialization/deadlock retry budget exhausted | `CONCURRENT_MODIFICATION` 409 | Whole transaction rolls back; only a fresh retry may run. |
| Any validation/constraint error during atomic merge | mapped deterministic conflict | Entire transaction rolls back; no partial SourceMergeRecord, alias, consumption event or receipt. |

The application distinguishes stale detection from stale authority. Only the canonical guarded Application transition may append `PROPOSAL_STALE`; it locks proposal and basis rows, proves a previously frozen material basis mismatch using the accepted bridge guard extended to SourceVersion state, and appends event/transition atomically. Direct SQL state flips or stale events without that condition remain denied by database guards. No actor column alone authorizes staleness.

## 9. Architecture and scientific contracts

Write path is Caller → Application Command/Service → Repository Port/UoW → PostgreSQL. Domain has no SQLAlchemy, FastAPI, Typer, or provider imports; ORM models never cross the persistence boundary. HTTP and CLI are thin parity adapters using VerifiedPrincipal and identical typed Application commands/errors. PostgreSQL 18 is required for all persistence, constraint, migration, concurrency and temporal tests; SQLite/mocks do not substitute.

Scientific contracts: Acceptance, Independence, Planted-Truth and Reading contracts do not apply to identity merge or bibliographic version capture. Human-Authority applies to the proposal approvals as frozen by the governance bridge; merge execution revalidates each project’s Human Owner authority. Honest-Failure applies: ambiguous identity/version state is denied without mutation. Deterministic source/version facts take precedence over approval and cannot be rewritten by it. A citation, source version or merge is not a Claim or support relation. Phase 1 facts, hashes, lifecycle and closure remain unchanged.

## 10. Required acceptance matrix

Each row must have inspectable test/evidence output on PostgreSQL 18 where persistence, constraints or races are involved.

| Requirement | Required acceptance cases |
|---|---|
| Migration/fresh install | Fresh DB→0022; frozen 0018→0019→0020→0021→0021a→0022; one head and exact parent; inventory; no prior migration edits; constraints/indexes; empty downgrade succeeds; populated downgrade refusal before DDL. |
| SourceVersion create/edit | First version, monotonic number under concurrent creation, project access, active source only, owner/researcher write, invalid input, duplicate request replay/conflict, rollback, abandon; invalid/nonexistent/unfrozen ArtifactVersion denied. |
| Freeze | Exact hash golden vector; all fields/nulls/NFC; malformed/extra JSON keys denied; current pointer same-parent frozen FK; two simultaneous freeze attempts serialize; pointer/current version atomically updates; previous current becomes SUPERSEDED; no partial changes on failure. |
| Frozen immutability | Direct SQL update/delete of frozen material denied; draft edit succeeds; terminal edit, double freeze and abandon-after-freeze denied; status-only supersession allowed only with a new frozen current pointer and same parent. |
| Hash determinism | Golden SourceVersion vector `dc8964…2b8ca`; material field changes change digest; excluded status/creator/time do not; reference hash mismatch, changed artifact hash, malformed metadata, list ordering errors denied. |
| ArtifactVersion | Optional exact full-text reference and required correction/retraction basis; both must be FROZEN and independently hash-verified; bytes are not copied; same-parent predecessor/source constraints hold. |
| Correction/retraction | Corrected version requires prior current frozen predecessor and frozen basis; retracted version likewise; predecessor remains inspectable and unchanged; correction chain; retraction changes derived current validity only; invalid/cyclic/wrong-source/noncurrent predecessor denied. |
| Cross-phase current pointers | Null before first frozen version; pointer only to frozen same-source version; stale/wrong-source/draft target denied; same-source constraint tested through direct PostgreSQL writes. |
| Proposal source-version basis | Existing 0021 empty basis upgrades safely; 0022 concrete same-source refs; changed current version/kind/hash makes old proposal stale; guard denies false stale event; true stale event commits only through canonical path; basis sealed and immutable. |
| Affected project set | One project linked to both counts once; separate A/B projects both required; exact extant effective links freeze; no peer IDs disclosed; changed/new link after proposal stales. |
| Human approvals | Every unique affected project approves; missing one denies; explicit reject denies; wrong direction/basis, non-human/agent, non-Owner, inactive membership, expired/revoked credential, credential/role expiry during lock wait deny at fresh `clock_timestamp()`. |
| SourceVersion TEMP-AUTH | For create/update/freeze/abandon independently, use PostgreSQL-observed held required lock, start transaction before OWNER/RESEARCHER credential or role expiry, release after expiry, capture transaction start/expiry/lock wait/acquisition/final authorization timestamps, deny after fresh `clock_timestamp()`, and prove zero version/pointer/receipt writes. No sleep-only test. |
| Identifier behavior | No identifiers; only A; only B; mechanically unique effective values resolve to survivor without row mutation; same live normalized value impossible/defensive conflict; rejected/rebound/correction provenance retained; ambiguity fails closed; title similarity never merges. |
| Merge atomicity | Correct survivor/direction; SourceMergeRecord exact fields/hash and deferred typed match to consumed proposal event; losing source becomes MERGED alias; winning ACTIVE; historical source IDs, versions, identifier rows, links and refs remain; event `PROPOSAL_CONSUMED`, record, alias and receipt commit together or none do. |
| Merge concurrency | Lock-order observation; simultaneous same proposal gives one effect; simultaneous opposite survivor proposals cannot both commit; two proposals for same loser serialized by source lock/unique losing source; project-link insertion vs merge serializes; owner/credential expires while waiting and denies; rollback leaves no partial rows. |
| Replay/idempotency | Every command uses `(deployment_id, actor_id, project_id, command_name, request_id)`. Prove the same actor/deployment/request ID in another project and the same actor/deployment/project/request ID under another command are distinct keys. Same key/hash returns the saved result without repeating mutation; same key with changed canonical hash conflicts without mutation or receipt overwrite. Concurrent identical keys yield one execution and one replay/conflict outcome. For merge consumption, event UUID is event identity; the event-backed receipt key and request/basis hashes match; exact replay creates no second SourceMergeRecord, alias, identifier effect, proposal consumption, or protected causal event. A new key after consumed denies; current read entitlement precedes disclosure. |
| Alias/history/access | Alias chain resolves to ACTIVE root; cycles and cross-root target denied; merged source cannot receive new versions, identifiers or project links; historical exact IDs remain queryable only under direct project links; root versions/identifier history are not exposed through a losing-source link; merge does not widen project grants; peers remain undisclosed. |
| Stale authority | Direct stale UPDATE and direct stale event with current basis denied; true stale basis canonical path succeeds atomically; false stale canonical attempt denied; stale vs submit/merge race serializes to one terminal outcome. |
| HTTP/CLI | Create/edit/freeze/abandon/get/list/resolve/merge route and CLI parity; exact errors and replay result parity; no actor-header authority. |
| Architecture | Import boundaries; Domain/persistence separation; no ORM leakage; no provider/network call; no generic polymorphic target/JSON; no Phase 1 file or historical migration change. |
| Regression | All relevant PR2-00 and PR2-01 tests; frozen Phase 1 catalog/hash/closure/migration regression; no post-expiry PR2-00 challenge success. |
| Tool/evidence | Focused and full suite exact collected/passed/failed/skipped/xfail counts; Ruff, Pyright; raw formatter reported honestly and baseline delta empty; every changed Python file formatter-clean; `git diff --check`; reproducible PostgreSQL setup. |

## 11. Verification and evidence protocol

Use the repository’s established PostgreSQL 18 setup; record exact version and non-secret `DATABASE_URL` pattern, clean startup/readiness, base DB at frozen revision `0018_current_pointer_same_parent_integrity` for Phase 1 catalog tests, isolated Phase 2 test DB behavior, migration commands and cleanup. No hidden shell variable or existing container may be required by the reviewer.

Run, record exact output and counts:

- SourceVersion unit tests and focused PostgreSQL lifecycle/hash/artifact tests, including one deterministic held-lock expiry case for each create/update/freeze/abandon command.
- Source merge approval, stale basis, identifier, alias, replay, atomicity and deterministic concurrency/lock-wait tests.
- Migration fresh install, 0018-to-head, upgrade/current/head, constraints and downgrade behavior.
- HTTP/CLI parity and architecture/import tests.
- Relevant PR2-00/PR2-01 regression plus full `uv run pytest -o addopts=''`; record collected, passed, failed, skipped and xfailed.
- `uv run ruff check .`, `uv run pyright`, raw `uv run ruff format --check .`, changed-Python formatting and FORMAT-BASELINE-01 delta; no new formatter failure and changed Python files clean.
- `git diff --check`, frozen Phase 1 baseline/tag check and no Phase 1 semantic or migration drift.

Create evidence only after the implementation commit. Evidence must record starting SHA, implementation SHA, migration and changed files, exact commands/results, PostgreSQL startup and cleanup, concurrency timestamps/lock observation, hash vectors, approval cases, formatter baseline/current/new sets, Phase 1 non-drift, PR2-00/01 regression and known residuals. Evidence is an evidence-only child and does not certify its own SHA. Then one new, independent review-only implementation context inspects committed diffs and independently reruns key checks.

## 12. PR2-03 boundary and design gate

PR2-03 is LiteratureSearchPlan/version/freeze and its frozen question/source scope, inclusion/exclusion criteria, time/language scope, strategy, provider set and stopping rule. PR2-02 does not create plans, execute providers, or return search results. After PR2-02 acceptance, PR2-03 may start only from its own repository-authorized execution pack and accepted dependencies.

This pack must be committed by itself with a clean worktree before one fresh design reviewer starts. The reviewer receives this pack SHA, the governance bridge pack/ADR and accepted gate evidence, authoritative architecture/contracts, PR2-00/01 accepted lineage, migration history and Phase 1 baseline. Review exact committed docs and independently attack schema ownership, source-version lifecycle/hash, ArtifactVersion closure, cross-project approvals, lock/race safety, stale-state validation, identifier semantics, failure/replay, migration reversibility, evidence testability, Phase 1 non-drift and PR2-03 boundary. The reviewer is review-only and returns `NEW_P0_GAPS`, `NEW_P1_GAPS`, `NEW_P2_GAPS`, and `READY_FOR_PR2_02_IMPLEMENTATION`.

Pass requires P0=0, P1=0, readiness YES, and no new P2 requiring a human policy choice. One narrow non-policy pack remediation and one new fresh reviewer are allowed. Only after pass is direct main-context implementation authorized. Stop on policy ambiguity, architecture contradiction, Phase 1 drift, bridge/PR2-00/01 regression, P0/P1 after the allowed cycle, verification unavailability, migration conflict, or an unreviewable/dirty subject.
