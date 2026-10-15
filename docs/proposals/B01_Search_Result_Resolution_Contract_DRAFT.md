# B01 Search-result Resolution Admission Contract — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

## Start here (for the implementer)

B01 gives an authenticated caller one command to append an exact search-result
→ frozen SourceVersion binding, and one exact-record read. It fills the bounded
admission gap identified by PR2-19 G1. It does not retrieve, create a source,
choose its current version, or create/verify LiteratureEvidence.

M2 already implements `search_result_resolutions`. Reuse that relation and its
literal hash; do not introduce a second resolution store. The proposed first
slice admits DOI-bearing hits with an independently VERIFIED source identifier
and compatible exact-version title. Other identifier families and ambiguous
matches remain outside this slice. These are draft policy choices, not claims
about an already accepted B01 implementation.

Build in this order after owner approval **and separate execution authorization**:

1. Reconcile the actual migration head and M2 baseline; add only the deferred
   closure guard in [§12.1](#121-ddl-sketch-and-guard-inventory).
2. Build the closed command/read DTOs and pure validation ([§11.3](#113-dto-fields-python-types-and-limits)).
3. Add the Application service and repository port, then its PostgreSQL adapter
   ([§12.3](#123-ordered-build-steps-and-module-paths)).
4. Implement the FIRST-statement SHARE protocol and exact replay
   ([§12.2](#122-exact-lock-order-and-transactions)).
5. Add the focused adversarial tests and run dependent suites
   ([§12.4](#124-test-artifacts-and-required-cases)); attach evidence and stop.

The five review rules:

1. Caller supplies an exact version; never substitute `current/latest` or a merge survivor.
2. Keep retrieved hits and existing resolutions immutable; retain conflicting history.
3. DOI/title compatibility and bibliographic verification do not establish scientific support.
4. One command is one transaction through Application → port/UoW → PostgreSQL.
5. Approval of this draft neither authorizes implementation nor declares G1/Phase 2 accepted.

Read §1 for authority, §10 for terminology, §11 for fixed draft choices and §12
for the build instructions. This task changes only this proposal.

## 1. Purpose, authority and inspected baseline

| Authority / current code | Constraint carried into this proposal |
| --- | --- |
| [Architecture 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 6.7, 9–13; [Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A3–A4, A18–A20 | Deterministic facts, exact concrete references, immutable history, scoped identity and fresh post-wait authorization. |
| [Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), §3; [Cross-Phase 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§9–18, 24, 30, 38 | SearchResultResolution is an existing literature-owned immutable relation; preserve hashes/errors and historical SourceVersion lineage. No new canonical entity. |
| [Phase 2 Specification 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §§4–7, 42; [Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md); [Field Contract 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md), literature table and M2 amendment | SearchResult is retrieval provenance; appended resolutions replace old resolved-source columns on hits. Source-only resolutions remain legal historical records. |
| [Source R2 16](../architecture/16_Phase2_Identity_Ownership_and_Source_Contract_R2_v1.0.md), source normalization/access/verification; [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md); [Temporal R4 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md) | Reuse DOI normalization, verified identity basis, project links, SourceVersion material hashes and advancing database time. |
| [Harness Specification](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 15, 19; [PR2-04 pack](../../execution/phase2/PR2-04_Literature_Search_Execution_Execution_Pack_v1.0.md), §§3, 15 | External output is candidate material; PR2-04 deliberately excludes source resolution. No provider call inside B01. |
| [ADR-0013](../architecture/adr/ADR-0013-durable-metadata-observations.md), [migration 0029](../../migrations/versions/0029_metadata_observations.py), [M2 service](../../src/researchbase/application/metadata_observation.py) | M2 persists observations and resolutions; MATCH observations can retain null source references. Its resolver uses identity/version commands and may choose an existing current version. B01 requires an explicit version and does not replace that orchestration. |
| [Resolution repository](../../src/researchbase/persistence/metadata_observation_repository.py), [novelty service](../../src/researchbase/application/novelty.py), [novelty repository](../../src/researchbase/persistence/novelty_repository.py) | Existing exact-tuple lookup, append and history; coverage validates every resolution and treats distinct/source-only bindings conservatively. Coverage takes SHARE locks first. |
| [PR2-19 plan](PR2-19_E2E_Failure_Injection_Plan_DRAFT.md), “Not in this slice” dependency table; [G1 test](../../tests/integration/phase2/test_pr2_19_search_evidence.py) | Current G1 exercises a search prefix and proves retrieval is not evidence; a full bridge-dependent chain is not supplied there. Source presence is not acceptance evidence. |

No B01 execution pack is supplied by this proposal. The approved PR2-17/18
drafts provide its document structure, not authorization for B01. Reconcile
owner acceptance evidence for PR2-01..04 and M2 before implementation; do not
repair their unrelated work under B01.

## 2. Scope, dependency boundaries and non-goals

First slice: `record_search_result_resolution` and `get_search_result_resolution`.
The record command takes the exact result, source and version IDs plus a bounded
human-readable basis. It verifies identity compatibility using existing canonical
identifier state; the basis text itself is not proof. Human and Agent callers
use the same authenticated service and roles.

M2 observation capture, CAS retention, source registration, identifier verification
and SourceVersion freezing remain separate commands. A caller may use those
existing commands before B01. B01 neither invokes them nor promises atomicity
across them. No new runtime dependency, receipt table, JSON reference object,
dispatch journal, resolution status machine or mutable winner pointer is added.

## 3. Invariants and conservative judgments

1. Resolve the exact result → query → execution → frozen/superseded plan →
   project chain and verify its existing hashes/provenance using the owning
   search reader. Admit only terminal execution history: SUCCEEDED, FAILED,
   CANCELLED or UNKNOWN. Partial durable hits may resolve; that does not turn a
   partial execution into SUCCEEDED. PLANNED/RUNNING fail closed.
2. Require the explicitly named source's project link and ACTIVE identity.
   Require the named version to belong to that source, be FROZEN or SUPERSEDED,
   and pass the existing SourceVersion digest/typed-reference checks. SUPERSEDED
   is frozen history, not permission to follow the current pointer.
3. For this slice, take the DOI from the hit's `url` only when it starts with
   the exact `https://doi.org/` wrapper, as M2 `observe` already does, then use
   `normalize_source_identifier(IdentifierType.DOI, ...)`. The provider's opaque
   `external_identifier` is not a DOI assertion. No snippet/title scraping,
   URL fetching or provider-ID guessing. Missing/invalid DOI URL denies admission.
   Exactly one currently VERIFIED DOI binding must name the supplied source;
   reject UNVERIFIED/REJECTED, different-source or absent bindings. Verify its
   retained verification event and exact frozen basis ArtifactVersion, including
   CAS bytes/hash under existing ArtifactStore semantics and project access.
4. `normalize_source_title(result.title)` must equal
   `normalize_source_title(exact_version.title)`. Do not compare only to the
   registration display title or tolerate fuzzy similarity. A mismatch requires
   separate identity/metadata handling. This conservative DOI/title policy is a
   **proposed B01 restriction**, narrower than the architecture's resolver priority.
5. Bibliographic admission preserves the requested version even if another
   version is current. RETRACTED material, or a current RETRACTED/CORRECTED version
   making this older version unusable under the existing novelty predicate,
   denies a **new** admission. MERGED/RETIRED sources deny new admission. Exact
   historical reads/replays still return the original binding after these changes.
6. Never rewrite a result, null-version resolution, observation, source or version.
   A different exact version may append a new resolution UUID. Every prior row
   stays visible. No later resolution silently invalidates or selects among older
   bindings. PR2-18 still marks multiple distinct tuples, including a source-only
   tuple plus a versioned tuple, unresolved; B01 changes none of its saved counts.
7. Resolution does not create LiteratureEvidence, its VERIFIED state, support,
   a locator, novelty proof, a review, Decision or Approval. G1 must independently
   extract/verify evidence through its owning commands.

### 3.1 SearchCoverage accounting — compatibility

Use the current `NoveltyService` rule: validate every stored resolution hash and
exact source/version; count a result as resolved only when its binding set is one
nonnull tuple. No new “B01 winner” projection overrides this rule. Later appended
rows may change current diagnostics, never a previously captured SearchCoverage.

### 3.2 Resolution — finite attributable binding

One row records one result/source/version assertion by `resolved_by` at
`resolved_at`. The immutable ID is the replay key, following PR2-18's record-ID
pattern. The tuple uniqueness from M2 remains the established-link uniqueness.
Duplicate provider hits remain separate results and require separate bindings.

### 3.3 Admission versus historical usability

New admission checks current deterministic usability. Historical read/replay
checks stored integrity and present read entitlement, without replaying the
original write gate or replacing its exact version. Consumers obtain current
scientific validity through existing owning-domain queries; a successful exact
read does not certify present usability or full-text availability.

## 4. Proposed commands, DTOs and historical readback

`SearchResultResolutionService.record_search_result_resolution(principal, command)`
returns `SearchResultResolutionReadback`. A successful first call appends one row;
a matching same-ID retry returns that row without another write.
`get_search_result_resolution(principal, query)` reads one exact ID. No list,
latest-resolution or batch command is added; M2's authorized result history stays
available. Exhaustive fields/types are pinned in §11.3.

Authenticated principal, credentials, time and roles come from the trusted
Application context, never command fields. Writes require OWNER/RESEARCHER and
an active project; reads/replays permit OWNER/RESEARCHER/REVIEWER/VIEWER/APPROVER
with active membership and a valid binding/credential. An archived project may
be read under existing policy. Check entitlement before disclosing ID collisions.

## 5. Schema and literal hash proposal — no migration

Reuse all nine immutable columns of `search_result_resolutions` from 0029.
`source_version_id` stays nullable in storage for M2 compatibility; it is required
by B01's command. Do not add project/observation IDs or duplicate actor/time columns.
Project is derived from the result chain. M2 observations are supporting history,
not mandatory input or an implied scientific-verification decision.

The literal hash payload is exactly the existing M2 row excluding `content_hash`:
`id`, `search_result_record_id`, `source_id`, `source_version_id`, `resolved_by`,
`resolved_at`, `basis`, `hash_scheme`. UUIDs are strings, time is aware UTC
`datetime.isoformat()`, null remains JSON null, scheme is `sha256-cjson-v1`.
Use `sha256_canonical_json` and independent vectors matching M2 `_hash`.
Project, current version/status and readback hashes are not new payload fields.
No Phase 1, search, SourceVersion, observation or old resolution digest changes.

## 6. Error contract — proposed use of existing categories

Use only the existing error enum and transport maps, pinned in §11.2. Do not add
`RESOLUTION_INVALID`, `HASH_MISMATCH` or another catch-all domain code. Sanitize
database diagnostics; never expose unlinked source metadata or filesystem paths.

## 7. Transactions, concurrency and failure recovery

One write command uses one fresh READ COMMITTED UoW. SHARE locks protect every
mutable fact consulted and resolution insertion phantoms. Follow §12.2 exactly;
do not call SERIALIZABLE M2 orchestration or take late `FOR UPDATE` locks under
this protocol. Existing M2 writers contend through ordinary PostgreSQL table
locks; no second persistence/coordination mechanism is needed.

Read entitlement first, then find the supplied ID in project scope. Matching
normalized `(result, source, version, basis)` and original `resolved_by` means
replay. Changed material is IDEMPOTENCY_CONFLICT; another actor cannot take over
the request ID (FORBIDDEN). An ID already belonging to another project returns
the same NOT_FOUND as an inaccessible ID; disclose none of its material.
A pre-existing same tuple under another UUID is DUPLICATE_CONTENT,
including an M2-created row; return no synthetic new success. The caller can
read the established row through existing authorized history. No B01 marker is
required for an already valid M2 bridge to be used by G1.

Retry only SQLSTATE 40001/40P01, at most three total fresh UoWs, with the same
command ID/material. Same-ID unique races reread in a fresh authorized UoW;
tuple conflicts never mint a replacement ID. Lock/statement timeouts and I/O
failures are not automatic retries. Unknown commit outcome is recovered by
exact-ID read/replay, never assumed rolled back. A failed known transaction
leaves no resolution. Read commands use one REPEATABLE READ, read-only UoW;
authorize at fresh DB time before returning, verify resolution and exact upstream
hashes, and preserve original times/actor/basis.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

The concrete file/case plan is §12.4. Test admission, raw-SQL constraints,
identity/authorization waits, rollback, replay/restart, unchanged M2 rows/hashes,
and the complete G1 path separately. Offline provider fixtures prove deterministic
behavior, not live-provider acceptance. No future test is claimed PASS here.

## 9. Acceptance criteria and evidence boundary

B01 requires the two methods, exact durable readback after restart, current
authorization, immutable nullable-history compatibility, verified same-source
closure, honest ambiguity, and the focused checks in §12.4. A future G1 test must
show one persisted result ID linked through this relation to **the same** frozen
SourceVersion used by independently verified LiteratureEvidence and downstream
conclusion provenance. Merely creating unrelated search and evidence prefixes
does not satisfy G1. G1 still requires its other dependencies and owner acceptance.

Stop after the authorized slice's evidence. This documentation task authorizes
no code, migration, test, architecture amendment, commit, branch or acceptance gate.

## 10. Glossary

| Term | Meaning |
| --- | --- |
| B01 | Phase 2 completion-backlog item: explicit search-result resolution admission. |
| Result / hit | Immutable SearchResultRecord returned by one recorded provider query; retrieval provenance. |
| Source / version | Global LiteratureSource identity / exact immutable bibliographic SourceVersion. |
| Resolution | Append-only result/source/optional-version relation already supplied by M2. |
| Admission | New Application validation and append of an explicitly versioned resolution. |
| M2 / MATCH | Durable metadata observation work / compatible bibliographic observation outcome; neither means verified scientific evidence. |
| Frozen | FROZEN or SUPERSEDED material with retained verified hash; never a current pointer. |
| G1 | PR2-19 Search → SourceVersion → LiteratureEvidence → downstream literature provenance golden path. |
| UoW / CAS | Unit of Work transaction / existing content-addressed ArtifactStore. |
| Replay | Authorized exact read of already committed matching material, without repeating write admission. |

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

Use the existing relation, its row ID and hash format; two Application methods;
DOI-only exact-title admission; mandatory explicit frozen version; OWNER/RESEARCHER
writes; all existing project reader roles for read/replay. Preserve M2's nullable
storage, resolver and observation behavior. No new canonical concept or persistence
mechanism. Add only a deferred closure guard using the existing M2 function;
it does not enforce DOI policy on M2 or require a version on legacy/source-only rows.
These choices are fixed for owner review; an override requires body edits before freeze.

### 11.2 Pinned error mappings

The numbers below match [API errors](../../src/researchbase/api/errors.py) and
[CLI errors](../../src/researchbase/cli/errors.py). They are compatibility targets
for any later authorized adapter; this slice adds no transport activation.

| Code | HTTP | CLI exit | B01 use |
| --- | --- | --- | --- |
| VALIDATION_ERROR | 422 | 2 | Wrong/extra fields, UUID type, invalid basis or bounds. |
| IDENTIFIER_INVALID | 422 | 2 | Hit has no admissible DOI or DOI normalization rejects it. |
| AUTHENTICATION_REQUIRED | 401 | 3 | No trusted authenticated principal. |
| FORBIDDEN | 403 | 3 | Current role/binding/credential denied, writer project inactive, or related basis inaccessible. |
| NOT_FOUND | 404 | 3 | Result/resolution absent or outside requested project. |
| SOURCE_NOT_FOUND | 404 | 3 | Source absent or unlinked; identical shape for both. |
| SOURCE_VERSION_NOT_FOUND | 404 | 3 | Exact version absent after source access check. |
| SOURCE_IDENTITY_CONFLICT | 409 | 4 | DOI absent from VERIFIED bindings, wrong source, incompatible title, MERGED/RETIRED source. |
| FROZEN_REFERENCE_REQUIRED | 409 | 5 | Supplied version or identifier basis is not exact frozen material. |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Digest/bytes/closure corruption, wrong-source version or deterministically unusable new basis. |
| INVALID_STATE_TRANSITION | 409 | 4 | New admission against PLANNED/RUNNING execution. |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Entitled original actor reuses ID with changed normalized material. |
| DUPLICATE_CONTENT | 409 | 4 | Same result/source/version already exists under another ID. |
| IMMUTABLE_RECORD | 409 | 4 | Attempted material UPDATE/DELETE. |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Sanitized concrete FK violation. |
| CONCURRENT_MODIFICATION | 409 | 4 | Exhausted 40001/40P01 attempts. |
| INTERNAL_ERROR | 500 | 1 | Existing HTTP/CLI fallback for unexpected failures; not an ErrorCode enum member. |

Use existing UoW normalization: M2 SQLSTATE P17D1 → IMMUTABLE_RECORD and
P17D3 → PROVENANCE_CLOSURE_VIOLATION. Add only B01-specific unique-constraint
handling where needed. Timeouts/connection
failures remain sanitized unexpected failures, not business conflict retries.

### 11.3 DTO fields, Python types and limits

All command/read DTOs are frozen, slotted dataclasses. Reject unknown transport
keys if adapters are later authorized. UUID values must be Python `UUID`; wire
strings must round-trip to lowercase hyphenated UUID form. No bool/string coercion.

| DTO | Exhaustive fields |
| --- | --- |
| RecordSearchResultResolutionCommand | `id: UUID`, `project_id: UUID`, `search_result_record_id: UUID`, `source_id: UUID`, `source_version_id: UUID`, `basis: str`. |
| ExactResolutionQuery | `project_id: UUID`, `id: UUID`. |
| SearchResultResolutionReadback | `id: UUID`, `project_id: UUID`, `search_result_record_id: UUID`, `source_id: UUID`, `source_version_id: UUID \| None`, `resolved_by: UUID`, `resolved_at: datetime`, `basis: str`, `content_hash: str`, `hash_scheme: Literal['sha256-cjson-v1']`. |

Readback permits null version only to read existing M2 source-only history;
B01 record success always has a nonnull version. No new enum. Reuse existing
IdentifierType.DOI and source/version/execution states listed in §3. Times are
aware UTC. Hashes are exactly 64 lowercase hexadecimal characters. Basis is NFC,
outer-trimmed, control/surrogate-free, nonblank, 1–4096 Unicode code points after
normalization; meaningful interior whitespace is preserved. This is compatible
with 0029's SQL bound and `normalize_reason`. DOI normalization has its existing
2048-code-point limit. There are no collections, pagination or batch limits.
Historic readback never normalizes saved basis text or changes old digests.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

Do **not** create this existing table again. This is its 0029 physical contract;
unmarked columns are NOT NULL. Existing implicit PostgreSQL FK/unique names must
be read from the migrated catalog, not guessed or renamed in accepted migrations.
Use constraint definitions plus the exact names read from that catalog for
unique-error classification. Explicit existing guard/index names are pinned below.

```sql
-- Existing search_result_resolutions (0029), reference sketch only:
-- id UUID PRIMARY KEY
-- search_result_record_id UUID REFERENCES search_result_records(id) ON DELETE RESTRICT
-- source_id UUID REFERENCES literature_sources(id) ON DELETE RESTRICT
-- source_version_id UUID NULL
-- resolved_by UUID REFERENCES actors(id) ON DELETE RESTRICT
-- resolved_at TIMESTAMPTZ
-- basis TEXT CHECK (length(btrim(basis)) BETWEEN 1 AND 4096)
-- content_hash CHAR(64) CHECK (content_hash ~ '^[0-9a-f]{64}$')
-- hash_scheme TEXT CHECK (hash_scheme = 'sha256-cjson-v1')
-- FOREIGN KEY (source_id, source_version_id)
--   REFERENCES source_versions(literature_source_id, id) ON DELETE RESTRICT
-- UNIQUE NULLS NOT DISTINCT (search_result_record_id, source_id, source_version_id)

-- Sole proposed forward DDL, in a new migration after the actual current head:
CREATE CONSTRAINT TRIGGER b01_resolution_closure_at_commit
AFTER INSERT ON search_result_resolutions
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION m2_check_closure();
```

Keep `m2_resolution_immutable` (BEFORE UPDATE/DELETE, `m2_immutable`, P17D1) and
`m2_resolution_closure` (BEFORE INSERT, `m2_check_closure`, P17D3). The new named
constraint trigger repeats structural result/project/link/frozen-version closure
at commit, covering invalidation later in the same transaction. Like
[0042's deferred guards](../../migrations/versions/0042_pr2_15_minimal_decision.py),
it is forced by `SET CONSTRAINTS ALL IMMEDIATE` before success. It does not prove
filesystem bytes, bibliographic identity or authorization; Application owns those.
No new parent/child set needs a sealing schema. Preserve nullable M2 rows and all
existing hashes. Test this function's use as an AFTER constraint trigger, not
only its existing BEFORE-trigger path.

Preserve `ix_srr_source_version`, `ix_srr_version`, `ix_srr_actor` and the unique
index's leading result lookup. No new index is justified. Forward migration
filename: `migrations/versions/<next_revision>_b01_resolution_admission.py`, with
actual head allocated at authorization. Downgrade drops only
`b01_resolution_closure_at_commit`; it deletes no rows/columns and does not touch
0029 or 0042. No DDL is executed by this draft.

### 12.2 Exact lock order and transactions

Define the fixed table set **R**, in this exact lexical order:

```text
actor_subject_bindings, actors, artifact_versions, artifacts,
literature_search_execution_command_receipts, literature_search_execution_events,
literature_search_executions,
literature_search_plan_versions, literature_search_plans,
literature_search_provider_attempts, literature_source_project_links,
literature_sources, project_membership_events, project_memberships,
project_role_assignments, projects, research_question_versions, research_questions,
search_query_records, search_result_records,
search_result_resolutions, source_identifier_verification_events,
source_identifiers, source_versions
```

| Method | Exact order |
| --- | --- |
| record_search_result_resolution | Fresh ordinary READ COMMITTED UoW; **FIRST SQL statement** `LOCK TABLE <R> IN SHARE MODE`; then `SET LOCAL lock_timeout='10s'`, `SET LOCAL statement_timeout='30s'`; request advisory `SELECT pg_advisory_xact_lock(hashtextextended(:key,0))`, key `b01:resolution:<canonical id>`; read authority at `clock_timestamp()` and check credentials/read entitlement; scoped exact-ID replay lookup; for new material check writer entitlement; read result/query/execution/plan and attempts/events in existing ordinal order; read supplied source/project link, exact version and referenced version/artifact closure by UUID; read matching DOI identifier and verification events by UUID; verify existing basis CAS bytes/hash; inspect exact-tuple duplicate; compute immutable row hash; refresh clock and all time-dependent authorization checks; INSERT one row; `SET CONSTRAINTS ALL IMMEDIATE`; refresh clock/authorization once more; commit. |
| get_search_result_resolution | Fresh REPEATABLE READ read-only transaction configured before its first query; no advisory/table/row locks; clock/authenticate project reader; scoped exact ID; verify row and exact upstream hashes/closure without present write-usability gate; final fresh clock/credential/role check; return exact readback. |

No autoflush, SELECT, authorization query, request lookup or SET LOCAL may precede
the write's table lock. Connection-level operational bounds must cover its initial
wait; SET LOCAL after it cannot bound that earlier wait. The SHARE-first rule is
the accepted coverage pattern in `novelty_repository.py`; `decision_repository.py`
also supplies protected SHARE snapshots but has its own earlier request/target
locks. Do not copy Decision's different command sequence into B01.

Use protected read repository methods after SHARE acquisition, following UoW
`enable_revision_action_snapshot_reads`; do not invoke M2 `_authorize`, whose
project/authority `FOR UPDATE` sequence would invert this order. R covers only
facts read here: B01's usability predicate is §3.5's source lineage predicate,
not a new general governance-validity traversal. If implementation needs another
mutable table, amend this inventory and its race tests before freeze.

SHARE on resolutions conflicts with INSERT's ROW EXCLUSIVE lock, including
other B01 and M2 writers. Concurrent SHARE holders upgrading to write may deadlock;
use the bounded fresh-UoW retry, not a different lock protocol. Test both commit
orders against PR2-18 capture, including an initially empty result history.

### 12.3 Ordered build steps and module paths

1. Read the governing sources in §1 and actual Alembic head. Add the forward
   migration from §12.1; leave accepted revisions unchanged.
2. Add `src/researchbase/domain/search_result_resolution.py`: pure closed values,
   basis/UUID validation and literal hash material. Reuse
   `domain/source_identity.py` normalization and `foundation/canonical_json.py`
   / `foundation/hashing.py`; no ORM, transport, filesystem or provider imports.
3. Add `src/researchbase/application/search_result_resolution.py`: the two DTOs,
   readback and service. Reuse owning search provenance, source material/basis
   verification and principal/credential policy; keep existing hashes unchanged.
4. Extend `src/researchbase/application/ports.py` with a typed narrow resolution
   repository/UoW contract; add `src/researchbase/persistence/search_result_resolution_repository.py`
   for protected queries, R locks and existing-table writes. Existing M2
   `metadata_observation_repository.py` remains its working adapter; no hidden
   requirement to refactor M2. Wire through `src/researchbase/persistence/uow.py`;
   add only needed unique-error/retry normalization using stable driver metadata.
5. Wire service construction through `src/researchbase/cli/composition.py` where
   needed by the authorized test harness. HTTP routes/CLI commands are deferred;
   do not silently activate a new public surface. Future adapters must use §11.2.
6. Add §12.4 tests. Once separately authorized, extend the existing G1 test to
   exercise the bridge and independent evidence commands. Attach exact results
   and stop; B01 implementation is not authorization for other completion items.

### 12.4 Test artifacts and required cases

New files below are planned; existing named suites are regression targets.

| File | Required cases |
| --- | --- |
| `tests/unit/phase2/test_b01_resolution_contract.py` (new) | Closed immutable DTOs; UUID/bool/extra-field rejection; basis NFC/4096 boundary/controls; DOI wrapper normalization; exact title policy; independent M2-compatible row hash vectors including UTC/null; no new enums/transport-code drift. |
| `tests/architecture/test_b01_resolution_boundaries.py` (new) | Domain import boundaries; shared Application service; only existing relation writes; no provider/identity/version orchestration, scientific-evidence writes, new semantic JSON or parallel store. |
| `tests/integration/phase2/test_b01_resolution_admission.py` (new) | Real PG18 migrated fixture using `setup_m2` patterns; explicit version succeeds/read after restart; frozen SUPERSEDED target stays exact; DOI/title mismatch, unverified/rejected identity, wrong source/project/version, active execution, retraction/correction and inaccessible/corrupt basis deny; failed terminal execution's real partial hit may resolve; retrieval/observation/evidence row counts unchanged. |
| `tests/integration/phase2/test_b01_resolution_schema.py` (new) | Actual catalog names/types/FKs/NULLS NOT DISTINCT and named guards; direct SQL UPDATE/DELETE/FK denial; nullable M2 insert preserved; exercise deferred guard through explicit forcing and commit, assert invalid closure denies (an owning guard may reject an attempted same-transaction invalidation earlier); unchanged legacy hashes across upgrade/downgrade/re-upgrade; downgrade retains rows. |
| `tests/integration/phase2/test_b01_resolution_replay.py` (new) | Same ID/material returns original hash/time/actor; changed basis/version conflicts; other actor takeover denied; same tuple/other ID and M2 tuple duplicate; uncertain commit exact-ID recovery; credential/read-entitlement loss denies; later merge/retraction does not retarget authorized historical read. |
| `tests/integration/phase2/test_b01_resolution_concurrency.py` (new) | FIRST SQL evidence; no late FOR UPDATE; both resolution/coverage commit orders and empty-range phantom; concurrent same ID/tuple; deadlock retry ≤3 total attempts; no timeout retry; rollback before insert/after insert/deferred failure; revocation, project archive, identifier rejection, source merge, version correction and scheduled credential/role expiry across waits, using observable blocked-lock evidence and final DB clock. |
| Existing `tests/integration/phase2/test_m2_metadata.py`, `test_pr2_02_source_version_migration.py`, `test_pr2_18_search_coverage.py` | Existing observation/resolution replay, source lineage, all-row ambiguity accounting and unchanged captured coverage. Include the B01 append after a source-only row: current coverage remains unresolved. |
| Existing `tests/integration/phase2/test_pr2_19_search_evidence.py` | Keep retrieval-is-not-evidence check; add explicit persisted resolution → identical frozen SourceVersion → independently VERIFIED LiteratureEvidence → downstream conclusion path when other dependencies are available. Retain source/result IDs and row hashes as assertions; no fabricated in-memory bridge. |

Run static checks, `tests/unit tests/architecture`, these new PostgreSQL suites
and the existing regression targets. Report exact commands/counts, failures and
environment blocks. The owner's loop runs the whole suite; do not substitute a
full-suite claim for focused evidence.

### 12.5 Not in this slice

Non-DOI/fuzzy resolution, provider retrieval or raw-response retention, source
creation/freezing/merge/rebinding, M2 resolver redesign, ambiguous-result
adjudication/supersession, latest winner queries, backfills/deletes, bulk
resolution, evidence extraction/verification/support, novelty outcome changes,
public API/CLI activation, governance changes, new infrastructure or runtime
dependencies, other backlog items, full G1 or Phase 2 acceptance.

## 13. Open questions for the owner — override register

No implementation choice is intentionally left open. Approve or override the
DOI-only/title-exact policy, current-usability restriction, same-ID replay and
duplicate-tuple behavior, deferred closure guard and two-method Application-only
scope. Broader identifier families or conflict adjudication require a revised
contract; they are not implicit implementer discretion. Pending owner approval
is not a reason to implement a subset now.

## 14. Documentation verification note

This is a documentation-only draft. The following final checks were executed on
2026-10-15 against current code, not the proposed B01 methods/migration/tests.
The shared repository environment was used through a temporary local environment
wrapper, removed after checking. Initial environment-discovery runs were
superseded; no application code or test was repaired.

All commands in this table used the exact prefix
`UV_CACHE_DIR=/private/tmp/rb-b01-uv-cache uv run --offline --no-sync`:

| Command suffix | Observed result |
| --- | --- |
| `ruff format --check .` | Exit 0; 536 files already formatted. |
| `ruff check .` | Exit 0; All checks passed. |
| `pyright` | Exit 0; 0 errors, 0 warnings, 0 informations. |
| `pytest tests/unit tests/architecture -o addopts='' -q -p no:cacheprovider` | Exit 1; 2139 passed, 5 failed, 12 errors, 5 warnings in 45.03s. |

The five failures were the inherited baseline-diff whitespace assertion against
`b8179f17720ca47c3b25ad9d36f6a8e8d4aa79ff` (the committed PR2-20
`pyright-000.txt` has a new blank line at EOF) and four runner tests denied Unix
socket binding by this environment. Twelve PR2-19 architecture cases require
PostgreSQL fixtures and errored because `RB_TEST_ADMIN_URL` was unset in that
unit/architecture invocation. They are not passes.

Focused PostgreSQL command (executed; no successful database test):

```bash
DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres UV_CACHE_DIR=/private/tmp/rb-b01-uv-cache uv run --offline --no-sync pytest tests/integration/phase2/test_m2_metadata.py tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_18_search_coverage.py tests/integration/phase2/test_pr2_19_search_evidence.py -o addopts='' -q -p no:cacheprovider --maxfail=1
```

Result: exit 1; **1 setup error in 0.61s**, stopped at the first M2 case because
localhost:5432 refused connection. PostgreSQL 18 `initdb` attempts, including
explicit mmap settings, were blocked by shared-memory permissions. No PostgreSQL
suite is claimed PASS. `git diff --check` passed for the working change; all
23 local document links resolved. Only this draft remains changed.

The full suite is reserved for the owner's loop. No acceptance or implementation
authorization is inferred from successful static checks.
