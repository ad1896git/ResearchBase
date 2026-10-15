# B04 Manuscript Freeze and Sealed Placement Contract — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

## Start here (for the implementer)

This slice seals one existing manuscript draft: document, exact placement targets,
placement-set hash and manuscript hash. It supplies the missing freeze suffix of
[PR2-19 G5](PR2-19_E2E_Failure_Injection_Plan_DRAFT.md), not publication readiness
or package preparation. Freeze preserves scientific facts; it cannot establish
support by citing a source or placing a claim in prose.

Build in this order after owner approval **and separate execution authorization**:

1. Reconcile migration head and accepted PR2-12/13 and verified-support dependencies
   (§1); replace draft-only guards without rewriting existing material (§12.1).
2. Build pure literal hash material and closure verification (§§3, 11.3, 12.3).
3. Add one freeze command and one exact-version read through Application ports
   (§4); use the precise transaction/lock protocol (§12.2).
4. Extend frozen placement/trace readback, retaining existing draft behavior (§12.3).
5. Execute the named unit, architecture, migration, race and G5 tests (§12.4),
   record actual results, then stop. No migration or runtime change is authorized here.

On first read use §§1–4, then §11 for pinned decisions and §12 for construction.
The glossary (§10) is a lookup. The owner override register (§13) records approval
choices, not permission to improvise missing behavior.

Five review rules:

1. Verify document bytes, both manuscript digests and complete exact scientific
   closure; a digest-shaped string or trace result is insufficient.
2. Seal all three placement tables, including empty sets and INSERT phantoms;
   block both old- and new-parent moves after freeze.
3. Keep citation, presentation, scientific support, review and authority distinct.
4. Use one synchronous PostgreSQL transaction and fresh authorization after waits.
5. Preserve history and Phase 1 hashes. No READY, grant consumption, authorship,
   package freeze, sending or new canonical entity in this slice (§12.5).

## 1. Purpose, authority and inspected baseline

This is a documentation proposal, not an architecture amendment, execution pack,
acceptance declaration or implementation authorization. Proposed refinements below
need owner approval; normative architecture wins on conflict.

| Source | Binding rule carried forward |
| --- | --- |
| [System 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 7–12, 19–20 | Deterministic facts precede authority; frozen exact closure and immutable material; correction creates new history. |
| [Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A3–A6, A17–A23 | Concrete references, shared Application boundary, existing ArtifactStore, focused R2/R3/R4 precedence and current authorization. |
| [Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), Phase 2 | Publication owns ManuscriptVersion and its three sealed placement relations. |
| [Cross-Phase 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§9–14, 24, 28 | Preserve commands, exact read paths, hashes, RESTRICT references and immutable history. |
| [Phase 2 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §§16–18, 40, PR2-12/13 | Document ArtifactVersion, Claim/Conclusion XOR, separate citations/artifacts and full manuscript closure. |
| [Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), §§2, 4; [Fields 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md), manuscript rows | Null draft hashes; verify and seal on freeze; exact frozen references; formal reads recompute. |
| [Closure R2 14](../architecture/14_Phase2_Design_Gap_Closure_R2_v1.0.md), §§1–3; [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md), common rules and manuscript templates | Scientific support stays with existing owners; exact separate literature snapshots; literal hash schemas and ordering. |
| [Ownership R2 16](../architecture/16_Phase2_Identity_Ownership_and_Source_Contract_R2_v1.0.md); [Governance R2 17](../architecture/17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md), §1; [R3 18](../architecture/18_Phase2_Design_R3_Targeted_Remediation_v1.0.md), §7; [Temporal R4 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md) | Project access, exact historical versions, manuscript golden vectors, fresh advancing DB time; manuscript seal is distinct from the three grant-consuming effects. |
| [Harness specification](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 18–19 | All writes use Application; evidence precedes completion. |

Inspected code, rather than reference-draft historical inventories, is the baseline:

- [PublicationService](../../src/researchbase/application/publication.py) creates
  an initial DRAFT with a verified same-project FROZEN `manuscript` document;
  `read_draft` requires null hashes. There is no manuscript freeze command.
- [Migrations 0035](../../migrations/versions/0035_pr2_12_publication_draft.py)
  through [0039](../../migrations/versions/0039_pr2_13_citation_rebinding_guard.py)
  permit only DRAFT manuscripts and DRAFTING publications, reject all manuscript
  UPDATEs and all publication UPDATEs, and provide typed placements with guards.
  Merely adding a freeze service cannot pass these constraints.
- [Placement services](../../src/researchbase/application/manuscript_placement.py)
  add/read draft placements. [Scientific trace](../../src/researchbase/application/manuscript_scientific_trace.py)
  already reports frozen status/hashes if present, but does not recompute manuscript
  digests, verify document bytes or constitute the full freeze verifier.
- [Conclusion service](../../src/researchbase/application/scientific_conclusion.py)
  and [literature evidence service](../../src/researchbase/application/literature_evidence.py)
  supply same-UoW closure/hash/validity helpers; use these rather than opening nested
  transactions or trusting DTOs from earlier reads. Direct Claim placements need
  Phase 1 closure verification too; current trace is not a substitute.
- Migration head in this checkout is `0047_pr2_18_novelty_prior_art`; authorship,
  RevisionAction and Basic Approval code exists. Presence is not acceptance.
  Recheck head before any future migration; do not edit historical migrations.

[PR2-12 matrix](../phase2/PR2-12-draft-contract-matrix.md) and
[PR2-13 matrix](../phase2/PR2-13-remaining-contract-matrix.md) explicitly defer
freeze/closure. Accepted placement/trace and verified support are B04 prerequisites;
this draft does not certify their acceptance. No B04 execution pack was found.

## 2. Scope, dependency boundaries and non-goals

One existing initial DRAFT becomes FROZEN and the same Publication's current
manuscript pointer is set atomically. Publication remains DRAFTING; its initial
lifecycle event remains untouched. No prior current manuscript is replaced in
this initial slice. A later revision/supersession command needs its own contract.

Add exact-version inspection and formal frozen readback; preserve draft APIs and
trace distinctions. A citation-only or empty placement set may seal if document
closure is valid: freeze asserts retained material, not scientific completeness,
review acceptance, readiness or truth of unstructured prose. Full G5 tests must
exercise actual Claim/Conclusion support paths, not this minimal boundary case.

No new table, receipt store, generic snapshot, canonical entity, runtime dependency,
external effect or persistence mechanism is proposed.

## 3. Invariants and manuscript closure

1. Parent Publication belongs to requested Project; manuscript belongs to that
   Publication. Document belongs to the same Project, has artifact type `manuscript`,
   exact FROZEN material, frozen_at, byte_size and verified CAS SHA-256 bytes.
   Freeze rereads/verifies bytes and size; it does not trust draft-time verification.
2. All three placement sets are complete, locked and materialized. Claim and
   Conclusion share one placement kind/array and the existing target XOR. Sources
   require an exact project-access link; scientific and artifact targets require
   same-project ownership. Frozen material may be FROZEN or SUPERSEDED with preserved
   hash/frozen_at; supersession alone does not invalidate history. New admission retains the document
   FROZEN requirement of draft creation; historical frozen reads also accept its
   SUPERSEDED material with unchanged hash/frozen_at.
3. Independently recompute each referenced owner's applicable hashes and closure.
   Claims traverse EvidenceRelation, Measurement/StatisticalResult, Run, sealed
   dataset/artifact inputs, experiment and metric versions. Conclusions traverse
   exact Claim inputs, any explicitly bound LiteratureSupportSnapshot, and direct
   literature inputs. Never select a latest support snapshot for a direct Claim
   placement, or add a new support FK to placements. Verify SourceVersion material
   and all referenced artifact bytes using existing owner rules.
4. New freeze requires current deterministic VALID closure. Positive literature
   SUPPORTS must retain current VERIFIED independent HUMAN review under R2 14;
   extraction actor and support author cannot substitute for that reviewer.
   CONTRADICTS/QUALIFIES paths stay explicit and use existing owner admission rules;
   do not relabel them SUPPORTS or require every citation to become evidence.
   Retraction, dispute or owning validity failure denies new admission. Authority,
   strength annotation and a well-formed hash cannot override these checks.
5. Title, abstract, document FK, semantic class, parent/version, attribution, all
   placement fields and both hashes become immutable. Frozen UPDATE/DELETE or
   placement INSERT/UPDATE/DELETE fails even through normal-role direct SQL.
   Corrections require a later authorized new-version command, never unfreeze.
6. Historical read verifies retained material and reports current derived validity
   separately. Later upstream invalidity never rewrites a sealed hash or FK.
   Broken hashes/bytes/closure fail formal provenance; an ordinary history view
   must not present affected history as newly admissible evidence.

### 3.1 Literal hash material and ordering

Use exactly Hash R2 15's two manuscript payloads. `R(T)` means the closed
`{type,id,content_hash}` reference with canonical lowercase UUID/digest strings.
The entire placement payload is:

```json
{"type":"ManuscriptVersionPlacementSet","material_version":1,"claim_placements":[{"target":"R(ClaimVersion|ScientificConclusionVersion)","section_id":"string","locator":{"kind":"enum","value":"string"},"rhetorical_strength":"enum","ordinal":0}],"citation_placements":[{"source_version":"R(SourceVersion)","section_id":"string","locator":{"kind":"enum","value":"string"},"citation_purpose":"enum","ordinal":0}],"artifact_placements":[{"artifact_version":"R(ArtifactVersion)","section_id":"string","locator":{"kind":"enum","value":"string"},"artifact_role":"enum","ordinal":0}]}
```

The entire own-content payload is:

```json
{"type":"ManuscriptVersion","material_version":1,"publication_id":"uuid","document_artifact":"R(ArtifactVersion)","title":"string","abstract":null,"semantic_change_class":"enum","placement_set_hash":"digest"}
```

These are templates: replace reference placeholders with objects, abstract with
string or JSON null, and lists with all actual occurrences (including empty `[]`).
Each array sorts `(section_id,ordinal)` after NFC; Claim/Conclusion share the
existing claim-placement namespace. Retain repeated targets at distinct locations.
Reject duplicate `(placement kind,section_id,ordinal)`; do not deduplicate targets.
This draft interprets contiguous ordinals within each `(placement table,section_id)`
namespace, matching existing uniqueness (§11.1); owner approval must resolve that
interpretation before implementation. Never silently renumber existing placements.

Hash with existing canonical-json-v1 UTF-8 and SHA-256, persisted scheme
`sha256-cjson-v1`. Exclude placement UUIDs, status, times, row_version, current
pointer and author attribution from these payloads. Keep meaningful whitespace;
reject invalid Unicode and non-NFC persisted Phase 2 material rather than rewriting
it at freeze. Do not change the serializer or Phase 1 material.

## 4. Proposed commands, DTOs and historical readback

Two new Application methods on `ManuscriptFreezeService`; principal is a separately
verified `VerifiedPrincipal`, never request body identity:

| Method | Closed input | Result and authority |
| --- | --- | --- |
| `freeze_manuscript_version` | `FreezeManuscriptCommand` (§11.3) | Exact FROZEN version, hashes and frozen_at; active authenticated HUMAN OWNER or RESEARCHER in active Project. |
| `get_manuscript_version` | `GetManuscriptVersionQuery` (§11.3) | Exact DRAFT/FROZEN material, preview hashes or verified sealed hashes, current validity; existing HUMAN project read roles. Preview is not persisted closure. |

Read the draft to obtain the two computed preview hashes, then freeze with both as
expectations. Freeze recomputes independently; changed placement/document material
denies the attempt. No caller-supplied material, timestamp, actor, status, grant,
review, assertion of verification or hash scheme is accepted as fact.

Existing placement `trace` methods gain an additive frozen path preserving fields,
ordering and draft behavior; their frozen path delegates to the same formal verifier.
The combined scientific trace must also invoke it when serving formal frozen
provenance, choosing the B04 read protocol before its existing snapshot call. Keep `CITATION_ONLY` and `PLACEMENT_ONLY` semantics. No draft response is
silently reclassified as frozen, and `read_draft` keeps its original meaning.

## 5. Schema and literal hash proposal — no migration

Reuse manuscript/publication and placement tables, exact typed FKs and indexes.
Replace the 0035 draft-only checks/functions with the named guards in §12.1;
retain 0036–0039 target/locator/reparent protections and strengthen their sealed
failure paths. No separate placement seal column/hash or new current pointer.
The manuscript FROZEN transition is the seal. No manuscript lifecycle event table
is needed: this is a Version freeze, not a Publication lifecycle transition.

DB enforces structural completeness, seal state, ownership, FK, ordinal and digest
shape rules; Application recomputes canonical hashes, CAS bytes and full scientific
closure. As in [0042](../../migrations/versions/0042_pr2_15_minimal_decision.py),
deferred constraint triggers check the final transaction state; SQL does not
implement a second canonical serializer or claim to hash CAS bytes.

## 6. Error contract — existing categories only

Use the exact HTTP/CLI pairs in §11.2. Validate input shape before opening a UoW;
authenticate/authorize before exposing exact record existence. An inaccessible or
wrong-project record does not disclose another project's data. Once authorized,
missing scoped Publication/manuscript is NOT_FOUND. Unsupported lifecycle is
INVALID_STATE_TRANSITION; changed expected hashes are CONCURRENT_MODIFICATION.
Broken retained material or non-VALID new-admission closure is
PROVENANCE_CLOSURE_VIOLATION. No unmapped `HASH_MISMATCH` or new
`MANUSCRIPT_INPUT_NOT_FROZEN` enum is introduced from architecture examples.

## 7. Transactions, concurrency and failure recovery

One command = one synchronous READ COMMITTED UoW. Protect mutable read facts and
insertable relation sets with first-statement table SHARE locks (§12.2); do not
reuse an earlier request's snapshot, open nested services or switch to SERIALIZABLE
without a reviewed change. Enable existing protected-read adapters so owner closure
helpers do not introduce late row-lock inversions.

Freeze is naturally idempotent on the exact manuscript and its two expected
hashes. No new request key or durable receipt is needed: after a lost response,
matching already-FROZEN material returns the same stable frozen record with current
read entitlement, without changing frozen_at, hashes, row_version or pointer.
Different expectations on an already-FROZEN record raise IDEMPOTENCY_CONFLICT.
Replay verifies retained closure; later current invalidity is reported, not used
to rewrite historical success. A fresh DRAFT freeze still needs current write
entitlement and VALID closure. This is not approval-grant consumption/replay.

After every possible wait, and immediately before writes/commit, use fresh
`clock_timestamp()` and credential validation with half-open authority intervals.
No transaction-start timestamp can authorize an expired caller. A replay needs
current read entitlement; it does not require a still-active write role.

Any validation, CAS, constraint or commit failure rolls back status, hashes and
pointer together. Retry only normalized deadlock/serialization failures, at most
three complete attempts in fresh UoWs as existing services do; never retry a
validation failure or continue an aborted transaction. Timeouts return sanitized
CONCURRENT_MODIFICATION. Table/row cycles with existing placement/owner writers
may abort an attempt; the race tests must prove rollback and safe retry, not promise
zero deadlocks. Do not weaken guards to avoid contention.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

§12.4 pins test files and cases. Use Application-created drafts/placements and
actual verified-support fixtures for successful G5. Normal-role SQL tests are
adversarial guard tests, not a replacement for the freeze command. Establish
concurrency with barriers and separate connections; observe a blocked writer and
verify both possible serial outcomes. A sleep-only test is insufficient.

## 9. Acceptance criteria and evidence boundary

After separate authorization, require literal R3 golden vectors; clean/upgrade and
history-preserving downgrade checks; exact closure/CAS failures; immutable direct
SQL; replay/restart and races; existing placement/trace and Phase 1 regressions;
and a successful Application freeze followed by PR2-19 G5 trace. No P0/P1 findings.
Record exact commands, PostgreSQL version, counts and limitations. B04 completion
only removes G5's manuscript-freeze blocker; it cannot declare PR2-19 or Phase 2
accepted. This task creates only this draft and stops.

## 10. Glossary

| Term | Meaning |
| --- | --- |
| ManuscriptVersion | Publication-owned exact wording/document and placement binding; not a Claim. |
| Document | Same-project manuscript ArtifactVersion whose CAS bytes are verified. |
| Placement | Exact presentation occurrence; Claim/Conclusion XOR, citation or artifact. |
| Sealed set | Complete placement rows, including absence of further rows, fixed by freeze. |
| Frozen material | Immutable hash-verified version; SUPERSEDED preserves historical identity. |
| Closure | Every exact dependency resolves and verifies to owning immutable material. |
| Support snapshot | Explicit Phase 2 literature binding, never implicit latest Claim support. |
| Preview hash | Computed draft expectation; not a stored canonical frozen hash. |
| Current validity | Derived VALID/STALE/INVALID state; separate from frozen material/status. |
| CAS | Existing content-addressed ArtifactStore; locator alone is not identity. |
| UoW | Single Application database transaction. |
| G5 | PR2-19 manuscript/placement/freeze/scientific-trace scenario (§42.5 in its plan). |

## 11. Decisions taken in this draft

These are proposed fixed choices for approval, not claims of existing implementation.
An override changes this contract before code, not silently during construction.

### 11.1 Scope and policy decisions

| Topic | Pinned decision |
| --- | --- |
| Lifecycle | Only initial DRAFT→FROZEN; insert remains DRAFT-only. No abandon, revise, supersede or readiness command. |
| Pointer | Set existing same-parent current pointer from NULL to this FROZEN version; retain DRAFTING lifecycle and initial event. |
| Scope/roles | Preserve current HUMAN publication write/read rules; no new Agent-authority workflow. |
| Empty/citation-only material | Allowed if closure passes; does not establish manuscript scientific sufficiency or G5 acceptance. |
| Ordering | Per-array `(section_id,ordinal)`; contiguous `0..N-1` per table/section; Claim/Conclusion share one namespace. This is an owner-review refinement of R2's common ordinal wording. |
| Bounds | At most 10,000 total placement occurrences at admission; max ordinal 2,147,483,647 from existing INT. No new bound on legacy draft abstract; existing valid drafts stay readable. |
| Replay | Exact ID plus two matching expectations, stored FROZEN record, current read entitlement; no receipt table. |
| Artifact OTHER | Preserve accepted manuscript placement enum; package category restrictions belong to PR2-17. |
| Support | Verify explicit transitive support and current validity; never attach a latest snapshot or infer support from citation/strength. |
| SQL snapshots | Fixed table list, first statement SHARE, READ COMMITTED; protected owner reads within same UoW. |

### 11.2 Pinned error mappings

Verified against [API errors](../../src/researchbase/api/errors.py) `_STATUS` and
[CLI errors](../../src/researchbase/cli/errors.py) `CLI_EXIT_CODES`:

| Code | HTTP | CLI | Use |
| --- | ---: | ---: | --- |
| VALIDATION_ERROR | 422 | 2 | Bad closed DTO, UUID/hash/enum/limit/Unicode/ordinal shape. |
| AUTHENTICATION_REQUIRED | 401 | 3 | Missing/unverified principal. |
| FORBIDDEN | 403 | 3 | No current project entitlement or expired credential. |
| NOT_FOUND | 404 | 3 | Authorized scoped exact record absent. |
| INVALID_STATE_TRANSITION | 409 | 4 | Wrong lifecycle or current pointer already occupied. |
| FROZEN_REFERENCE_REQUIRED | 409 | 5 | Referenced existing target lacks frozen material. |
| IMMUTABLE_RECORD | 409 | 4 | Frozen material/placement mutation or history deletion. |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Missing/inaccessible dependency, wrong ownership, broken hash/bytes, invalid support/validity. |
| CONCURRENT_MODIFICATION | 409 | 4 | Draft expectation changed; exhausted retry or wait timeout. |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Frozen retry expectations differ. |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | SQL FK violation. |

Preserve current error envelope, request-ID and CLI rendering. This document pins
adapter mappings without authorizing a new HTTP route/CLI command. Proposed B04
SQLSTATEs (§12.1) need scoped UoW normalization; do not expose raw SQL exceptions.

### 11.3 DTO fields, Python types, limits and enums

Frozen, slots dataclasses; adapters (when authorized) reject extra keys and bool-as-int.
All UUID fields are `uuid.UUID`, not arbitrary strings. Digest strings match
`[0-9a-f]{64}` exactly; aware times are UTC `datetime.datetime`.

```python
FreezeManuscriptCommand:
    project_id: UUID
    publication_id: UUID
    manuscript_version_id: UUID
    expected_placement_set_hash: str
    expected_content_hash: str
GetManuscriptVersionQuery:
    project_id: UUID
    publication_id: UUID
    manuscript_version_id: UUID
ManuscriptVersionReadback:
    project_id: UUID
    publication_id: UUID
    manuscript_version_id: UUID
    version_number: int
    status: Literal["DRAFT", "FROZEN"]
    document_artifact_version_id: UUID
    title: str
    abstract: str | None
    semantic_change_class: str
    placement_set_hash: str | None
    content_hash: str | None
    frozen_at: datetime | None
    preview_placement_set_hash: str | None
    preview_content_hash: str | None
    current_validity: Literal["VALID", "STALE", "INVALID"]
```

Version number >0. Frozen readback has stored hashes/time and null previews; draft
has null stored hashes/time and computed previews only when closure is admissible;
an unresolved draft fails preview with the same explicit error. Validity is a
read-time projection (INVALID dominates STALE, which dominates VALID), excluded
from the stable freeze result identity. Successful
initial freeze returns FROZEN/VALID. No ORM/session or mutable material JSON DTO.

Existing placement readbacks remain the dataclasses in `manuscript_placement.py`;
combined trace retains the dataclasses in `manuscript_scientific_trace.py`. Preserve
UUID fields, nullable XOR targets, tuple collections and locator `{kind,value}`.
Text is valid UTF-8 NFC; section/locator value nonblank, ≤2000 characters; title
nonblank, ≤2000. Abstract remains existing optional nonblank text without an added
length cap. Expected hashes are checks, never stored caller assertions.

| Field | Closed values |
| --- | --- |
| semantic_change_class | INITIAL, EDITORIAL, SCIENTIFIC_MINOR, SCIENTIFIC_MATERIAL |
| locator.kind | PARAGRAPH, SPAN, CAPTION, ANCHOR |
| rhetorical_strength | DESCRIPTIVE, SUGGESTIVE, SUPPORTED, STRONG |
| citation_purpose | BACKGROUND, METHOD, COMPARISON, EVIDENCE, PRIOR_ART, DATASET, OTHER |
| artifact_role | FIGURE, TABLE, OTHER |
| publication lifecycle in this slice | DRAFTING |
| hash_scheme / material_version | sha256-cjson-v1 / integer 1 |

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

All columns already exist: manuscript IDs/FKs UUID; version_number/row_version INT;
status VARCHAR(16); semantic_change_class VARCHAR(24); title/abstract TEXT;
placement_set_hash/content_hash CHAR(64); hash_scheme VARCHAR(32); frozen_at
TIMESTAMPTZ. Placement locator remains the existing closed JSONB value, not a
polymorphic reference. Keep every FK ON DELETE RESTRICT, existing indexes,
`ck_pr213_claim_target_xor` and `fk_pr212_current_same_parent`.

Proposed migration (not created here) after actual head; current candidate path
`migrations/versions/0048_b04_manuscript_freeze.py`. Inspect generated names on the
0035 baseline before replacing the anonymous status CHECK (expected
`manuscript_versions_status_check`); fail on an unexpected definition.

```sql
ALTER TABLE manuscript_versions
  DROP CONSTRAINT manuscript_versions_status_check,
  DROP CONSTRAINT ck_pr212_unfrozen_draft,
  ADD CONSTRAINT ck_b04_manuscript_status CHECK (status IN ('DRAFT','FROZEN')),
  ADD CONSTRAINT ck_b04_manuscript_seal CHECK (
    (status='DRAFT' AND placement_set_hash IS NULL AND content_hash IS NULL
                    AND frozen_at IS NULL)
    OR
    (status='FROZEN' AND placement_set_hash IS NOT NULL AND content_hash IS NOT NULL
     AND placement_set_hash ~ '^[0-9a-f]{64}$' AND content_hash ~ '^[0-9a-f]{64}$'
     AND frozen_at IS NOT NULL));
CREATE CONSTRAINT TRIGGER b04_complete_manuscript
  AFTER INSERT OR UPDATE ON manuscript_versions
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
  EXECUTE FUNCTION b04_check_manuscript_closure();
CREATE CONSTRAINT TRIGGER b04_current_manuscript
  AFTER INSERT OR UPDATE ON publications
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
  EXECUTE FUNCTION b04_check_current_manuscript();
```

Function bodies must implement this finite guard inventory (DDL sketch, not runnable
SQL authorization):

| Function/trigger | Required behavior |
| --- | --- |
| Replace `pr212_draft_guard()` (retain trigger name) | INSERT only DRAFT/null seal/row_version=1; DELETE always denied. UPDATE only DRAFT→FROZEN with row_version old+1, nonnull seal and all remaining columns identical (`IS DISTINCT FROM` comparison). FROZEN never updates. Recheck same-project frozen manuscript document structurally. |
| Replace `pr212_publication_guard()` | Keep INSERT/DELETE rules. Only UPDATE permitted is DRAFTING, old pointer NULL→same-parent FROZEN manuscript, row_version old+1; all other columns unchanged. No lifecycle event rewrite. |
| `b04_check_manuscript_closure()` | At final state, frozen document/target state and ownership, SourceVersion project link, XOR and complete ≤10,000 occurrence set with per-table/section gap-free ordinals; pointer equals frozen version. Reject malformed draft seal; no automatic hashes or semantic support inference. |
| `b04_check_current_manuscript()` | Nonnull current pointer references exact same-publication FROZEN version with complete seal. NULL cannot replace a sealed pointer. Existing composite FK remains. |
| Strengthen `pr213_citation_guard()`, `pr213_claim_placement_guard()`, `pr213_artifact_placement_guard()` | Lock/check OLD and NEW manuscript parents, sorted UUID, on UPDATE; reject reparent, frozen INSERT/UPDATE/DELETE and ownership changes. Retain draft target/locator checks, including 0039 citation reparent fix. Use IMMUTABLE_RECORD for sealed mutation. |
| Deferred `b04_complete_claim_placement`, `b04_complete_citation_placement`, `b04_complete_artifact_placement` | AFTER INSERT OR UPDATE OR DELETE on corresponding table, DEFERRABLE INITIALLY DEFERRED; dispatch final OLD/NEW manuscript IDs to same structural checker. Draft gaps may exist; complete contiguous set is required at seal. |

Use proposed `P04M1`→IMMUTABLE_RECORD, `P04M2`→INVALID_STATE_TRANSITION,
`P04M3`→PROVENANCE_CLOSURE_VIOLATION in **B04-scoped** UoW normalization.
SQL 23503→REFERENTIAL_INTEGRITY_ERROR, 23514/23502→VALIDATION_ERROR,
23505/40001/40P01/55P03/57014→CONCURRENT_MODIFICATION; only 40001/40P01 retry.
These are proposed trigger codes, not currently implemented mappings. Keep old
P17D mappings working for existing commands. Never weaken a check to enable seal.

Migration preflight under ACCESS EXCLUSIVE locks on affected publication/manuscript/
placement tables rejects incompatible legacy material and reports IDs; it does not
rewrite scientific rows. Existing drafts, hashes and Phase 1 tables are untouched.
Downgrade rejects any frozen manuscript/nonnull pointer before restoring original
guards/checks; never discard history. Exercise empty and populated-draft downgrade
as well as frozen-history refusal on real PostgreSQL 18.x.

### 12.2 Exact lock order and transactions

Define `B04_SNAPSHOT_TABLES` as the following **literal set**, sorted lexically for
one `LOCK TABLE ... IN SHARE MODE` statement (not dynamic catalog discovery):

```text
actor_subject_bindings actors artifact_versions artifacts audit_findings
claim_versions claims correction_records dataset_snapshots datasets
evidence_relations experiment_spec_versions experiment_specs impact_assessments
impact_targets literature_evidence literature_evidence_review_events
literature_evidence_relations literature_source_project_links literature_sources
literature_support_snapshots manuscript_artifact_placements
manuscript_citation_placements manuscript_claim_placements measurements
metric_definition_versions metric_definitions project_membership_events
project_memberships project_role_assignments projects run_artifact_inputs
run_dataset_inputs runs scientific_conclusion_claim_inputs
scientific_conclusion_literature_inputs scientific_conclusion_versions
scientific_conclusions source_versions statistical_result_inputs statistical_results
```

Inventory follows the consulted ownership/validity facts in Decision/Approval and
Novelty repositories plus actual scientific/placement relation tables. Immutable
leaf tables are included to exclude malformed INSERT phantoms. `publications` and
`manuscript_versions` are coordinated by the row locks below, not SHARE-to-write
table-lock upgrades. Any future verifier dependency requires an explicit inventory
review and race test before use; no unlisted mutable query in the command.

| Operation | Exact sequence |
| --- | --- |
| `freeze_manuscript_version` | Begin fresh READ COMMITTED UoW → **first SQL statement** `LOCK TABLE <sorted B04_SNAPSHOT_TABLES> IN SHARE MODE` → `SET LOCAL lock_timeout='10s'`, `SET LOCAL statement_timeout='30s'` → project ownership advisory lock via existing `literature_search_plan.lock_project(project_id)` (advisory `rb_phase2_lock_project`, then Project `FOR UPDATE`) → scoped Publication `FOR UPDATE` → exact manuscript `FOR UPDATE` → read/check current entitlement using a nonlocking B04 authority query with fresh DB time → branch saved FROZEN replay or new DRAFT admission → read complete sets and owner closure through protected adapters (no further row locks) → verify CAS and recompute hashes → fresh credential/role check → atomic manuscript seal and pointer writes → `SET CONSTRAINTS ALL IMMEDIATE` → final fresh entitlement check → commit. |
| `get_manuscript_version` / frozen placement and combined trace reads | Begin fresh READ COMMITTED UoW → first SQL statement the same sorted SHARE inventory → SET LOCAL limits as above → existing project lock helper (advisory, then Project FOR UPDATE) → scoped Publication FOR SHARE → exact manuscript FOR SHARE → nonlocking B04 authority query and fresh credential/time check → protected owner reads → recompute/compare sealed hashes or compute draft preview → fresh read entitlement → return; no writes. |

Missing principal/invalid DTO rejects before SQL. For replay use fresh read-role
checks at both authorization points; never fall through to writes. No receipt
advisory lock is needed: exact manuscript+Publication rows serialize the sole effect.
The B04 authority query uses the exact subject/deployment/credential binding and
actor/membership/role predicates of PublicationService, with no FOR UPDATE: the
first SHARE statement already protects those tables. Do not call its locking
`_authorize` helper after closure reads. Existing draft/placement writers retain
their parent coordination; frozen guards
are rechecked after any wait, including direct SQL UPDATE/DELETE/reparent.

FIRST means before authorization queries, row locks, advisory locks, `SET LOCAL`,
lookup or ORM autoflush. Install an initial 10s lock timeout/30s statement timeout
on the connection before transaction start (engine connection options), so the
first SHARE wait is bounded too; SET LOCAL retains the existing operational pattern.
Use `autoflush=False`. PostgreSQL transaction-control BEGIN is not a data statement.

[Decision repository](../../src/researchbase/persistence/decision_repository.py)
uses SHARE protection but actually takes request/target locks first;
[Novelty repository](../../src/researchbase/persistence/novelty_repository.py)
coverage `prepare` takes SHARE first. B04 deliberately pins the requested first
statement protocol; do not claim all existing commands already use this order or
change their lock protocols inside B04. Race tests must cover mixed protocols.

### 12.3 Ordered build steps and module paths

Paths marked **new** are proposed files, not current code:

1. Reconcile acceptance evidence/head; add only the candidate migration in §12.1.
   Verify table names/check definitions against migrations 0033, 0035–0039, 0042.
2. **New** `src/researchbase/domain/manuscript.py`: pure immutable material values,
   closed enum/locator validation and the two literal payload builders; use
   `src/researchbase/foundation/canonical_json.py` and `hashing.py` unchanged.
3. **New** `src/researchbase/application/manuscript_freeze.py`: DTOs in §11.3,
   freeze/read methods, same-UoW formal verifier and pure hash comparison. Reuse
   owning closure checks from `application/literature_evidence.py`,
   `scientific_conclusion.py`, `closure.py` and `governance_queries.py`; extract shared helpers only as
   needed, preserving existing behavior and hashes. Direct Claim support stays
   its exact accepted Phase 1 graph; no inferred literature attachment.
4. `src/researchbase/application/ports.py`: add typed manuscript-freeze repository
   protocol and UoW property; no domain SQL imports. **New**
   `src/researchbase/persistence/manuscript_freeze_repository.py`: fixed inventory,
   exact scoped selects, guarded seal/pointer updates and constraint forcing.
   Wire in `persistence/uow.py`, scoped normalization and existing
   `enable_revision_action_snapshot_reads()` protected adapters; use connection
   settings in `persistence/database.py` for bounded first lock. Check affected
   row counts; stale state never becomes apparent success.
5. `application/manuscript_placement.py`, `manuscript_scientific_trace.py` and
   `persistence/publication_repository.py`: add verified frozen read path without
   nested UoWs, retaining draft paths and typed trace DTOs. No silent broadening
   of `PublicationService.read_draft` or draft creation/replay.
6. Add §12.4 tests; run static, unit/architecture and focused PostgreSQL regressions.
   A separately authorized adapter slice may wire `api/` and `cli/` with §11.2
   mappings; this contract's first slice is Application plus persistence/readback.

### 12.4 Test artifacts and required cases

| File (new unless described as existing) | Cases |
| --- | --- |
| `tests/unit/phase2/test_b04_manuscript_contract.py` | Closed DTOs, UUID/digest/bool/Unicode bounds, enums, 10,000/10,001 admission, XOR, duplicate/gapped ordinals, repeated targets at distinct locations; no extra hash fields. |
| `tests/unit/phase2/test_b04_manuscript_hash_vectors.py` | R3 18 exact 411-byte placement vector/digest `4dd9c22356a328ec182d0a4f2330f55ffe5b60b6ca65d48eee63ced773bddf95` and 439-byte manuscript vector/digest `2e910c3b0c9242184a0d4daf7fda5bd5f17defb41feb7e53fa46be1ff83830dc`; NFC/null/empty arrays, order invariance, each material field changes hash, status/timestamp/row IDs do not. |
| `tests/architecture/test_b04_boundaries.py` | Domain imports; Application→port→adapter boundary; first emitted SQL is exact SHARE inventory; no nested transactions, caller bypass of Application or new canonical/receipt schema; frozen trace delegates verifier; read and write authority queries use the specified protected protocol. |
| `tests/integration/phase2/test_b04_manuscript_migration.py` | Clean base and actual-head upgrades, retained drafts/placements, catalog types/FK/check/trigger definitions, deferred final-state checks, downgrade safety. Normal-role SQL rejects forged frozen insert, null/malformed seals, material/hash/time/parent/row_version edits, deletion, all placement mutations and old/new-parent moves, wrong-project document/target and pointer. |
| `tests/integration/phase2/test_b04_manuscript_freeze.py` | Command success and restart/replay, changed expectations and permission expiry, concurrent calls, empty/citation-only seal, every placement kind, exact frozen/SUPERSEDED targets, CAS missing/corrupt/wrong-size document/figure, recomputed hash tamper, invalid Phase 1 closure, explicit snapshot mismatch, retracted/disputed/unreviewed positive support, contradiction retained, rollback between seal and pointer/at commit. |
| `tests/integration/phase2/test_b04_manuscript_races.py` | Freeze versus placement INSERT/UPDATE/DELETE/reparent, Source correction/retraction, review VERIFIED→DISPUTED, governance finding/impact INSERT phantom, project/binding/credential expiry; observe blocking and assert complete old/new snapshot or full rollback/retry, no partial seal. Mixed Decision/Novelty/owner writer lock order and first SHARE timeout. |
| Existing `tests/integration/phase2/test_pr2_19_citation_trace.py` | Extend G5 through Application freeze then exact scientific trace; retain F3 citation-only negative, exact IDs/locators/ordinals/CAS/hashes and distinct support paths. Do not freeze a fixture by SQL. |

Also run existing `test_pr2_12_migration.py`, `test_pr2_12_publication_draft.py`,
`test_pr2_13_citation_placement.py`, `test_pr2_13_claim_placement.py`,
`test_pr2_13_artifact_placement.py`, `test_pr2_13_citation_rebinding.py` and
`test_pr2_13_scientific_trace.py` under `tests/integration/phase2/`; support-owner
regressions in `test_m3_evidence.py` and `test_pr2_11_r2_persistence.py` if their
helpers change. Phase 1 golden evidence remains required by the implementation
pack. Do not claim future tests exist or pass today.

### 12.5 Not in this slice

Publication INTERNAL_REVIEW/READY or any other lifecycle transition; manuscript
review workflow, Issue disposition, Decision/Approval purposes, grant consumption,
authorship/consent, package manifests/freeze, external submission, new revision/
supersession command, document editing/rendering/parser or rhetorical truth audit,
Agent runtime, queues, SQLite integration, new dependencies, alternate persistence
or Phase 1 hash changes. Owner approval here does not authorize those features.

## 13. Open questions for the owner — override register

Approval must explicitly accept or replace these proposed refinements: initial-only
freeze with pointer advance but DRAFTING retained; no receipt table/natural exact
ID replay; per-table/section contiguous ordinals; 10,000 admission cap; empty or
citation-only seal permitted; Application-first delivery without new transports.
If ordinal interpretation conflicts with the intended R2 meaning, resolve it in
this draft/architecture review before implementation; do not renumber history.
No other scientific or concurrency decision is delegated to implementation.


## 14. Documentation verification note

Documentation-only run, 2026-10-15; no future B04 tests or G5 freeze acceptance
claimed. Only this proposal is added. No commit, push or branch was created.

The default uv cache was denied; an empty temporary cache then hit unavailable
network downloads. Existing cached dependencies allowed
`UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv sync --offline --frozen`
to succeed (34 packages installed). Subsequent checks used that cache:

| Exact command | Observed result |
| --- | --- |
| `UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline ruff format --check .` | Exit 0; 536 files already formatted. |
| `UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline ruff check .` | Exit 0; All checks passed. |
| `UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline pyright` | Exit 0; 0 errors, 0 warnings, 0 informations. |
| `UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline pytest tests/unit tests/architecture -o addopts='' -ra` | 2,156 collected; 2,139 passed, 5 failed, 12 errors, 5 warnings in 46.24s. |
| `UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline pytest tests/unit/phase2/test_pr2_04_static_acceptance.py -o addopts='' -ra --tb=short` | Diagnostic rerun: 1 failed, 1 warning in 7.05s. Inherited `git diff --check b8179f17720ca47c3b25ad9d36f6a8e8d4aa79ff` reports a new blank line at EOF in `pr_evidence/pr2-20/3ea9a7ac2f6d2a7f04ad79b907e344b24661a6cfc466be11e02dee1f3725836d/pyright-000.txt:4`. This task leaves that file unchanged. |
| `git diff --check` | Exit 0. |
| `git diff --no-index --check /dev/null docs/proposals/B04_Manuscript_Freeze_Contract_DRAFT.md` | Exit 1 (new-file difference); no whitespace diagnostics; includes this untracked new file. |

Four other unit failures are Runner socket-bind `PermissionError: Operation not
permitted` in `tests/unit/test_hg1_runner.py`. All 12 architecture errors are
PostgreSQL-fixture setup errors in `test_pr2_19_boundaries.py`: the run has no
DATABASE_URL/admin selector. A diagnostic run of
`UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline pytest tests/architecture/test_pr2_19_boundaries.py::test_literature_source_not_evidence -o addopts='' -ra --tb=short`
reported 1 error in 1.49s: explicit RB_TEST_ADMIN_URL selector required. They are errors, not passes or skips.

Focused PostgreSQL command:

```bash
RB_TEST_ADMIN_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/postgres UV_CACHE_DIR=/private/tmp/researchbase-uv-cache uv run --offline pytest tests/integration/phase2/test_pr2_12_migration.py tests/integration/phase2/test_pr2_12_publication_draft.py tests/integration/phase2/test_pr2_13_citation_placement.py tests/integration/phase2/test_pr2_13_claim_placement.py tests/integration/phase2/test_pr2_13_artifact_placement.py tests/integration/phase2/test_pr2_13_citation_rebinding.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_19_citation_trace.py -o addopts='' -ra -x
```

Observed: **26 collected, 1 failed in 0.40s**, stopped at first failure; 25 did not
execute. PostgreSQL connection to localhost:5432 is denied with Operation not
permitted. A temporary PostgreSQL initialization attempt also failed at shared
memory creation (`shmget: Operation not permitted`); no PostgreSQL PASS is claimed.
The loop must supply full-suite evidence; this task did not run the whole suite.

A read-only documentation check verified 29 local links, all 11 HTTP/CLI mapping
pairs against actual code, and existence of all 41 named lock tables in migrations.
