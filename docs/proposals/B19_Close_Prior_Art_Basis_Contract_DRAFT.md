# B19 Close Prior Art Assessment Basis Contract — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

## Start here (for the implementer)

B19 proposes the missing immutable basis for `CLOSE_PRIOR_ART_FOUND`. It adds
one typed assessment-input relation, explicit scope and closeness criteria, and
NoveltyAssessment material version 2. Existing INCONCLUSIVE records and all v1
hashes retain their exact meaning. Negative novelty findings remain unavailable.
This is a documentation proposal, not an ADR, architecture freeze or execution pack.

After owner approval, the architecture/compatibility decision in §9 and separate
implementation authorization, build in this order:

1. Reconcile the migration head and approve the bounded schema/hash change (§1,
   §5, §12.1). Do not edit accepted migrations.
2. Add typed basis values, versioned hash dispatch and independent vectors (§11.3,
   §12.3); keep the v1 oracle unchanged.
3. Extend the existing assessment command and exact read, repository and UoW;
   preserve the first-statement lock protocol (§4, §7, §12.2).
4. Add thin existing API/CLI fields and parity tests (§11.2–3, §12.4).
5. Verify normal-role SQL guards, restart/replay, races and historical v1 reads
   on PostgreSQL 18, record exact results and stop (§9, §12.4–5).

Five rules fail review if broken:

1. Membership is the saved typed input set, never all current relations or a
   timestamp cutoff. Evidence membership is reached through each sealed relation.
2. A close finding needs at least one exact, currently usable, independently
   verified IDENTICAL or HIGHLY_SIMILAR comparison within selected coverage.
3. Scope and criteria describe a bounded attributed judgment, never first-ever
   priority, exhaustive screening or an authority override of deterministic facts.
4. Preserve v1 bytes; version 2 explicitly hashes every new material field.
5. Writes take the specified SHARE locks first; reads use one read-only
   REPEATABLE READ snapshot without table, advisory or row locks.

The [glossary](#10-glossary), [pinned decisions](#11-decisions-taken-in-this-draft)
and [implementation guide](#12-implementation-guide--after-separate-authorization)
are the construction references. No implementation is authorized by this document.

## 1. Purpose, authority and inspected baseline

Read in AGENTS.md order: Architecture [01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md)
§§3, 7–13 (exact frozen provenance, one owner, immutable history); Addendum
[02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md);
Registry [03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md)
(literature owns PriorArtRelation and NoveltyAssessment); Compatibility
[08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md)
(additive evolution and historical verification); Phase 2
[05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md)
§25/PR2-18 (bounded novelty); [Harness §2](../harness/09_Harness_Integration_Specification_v1.0.md)
(Application boundary). Correction [12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md)
§2 and Field Contract [13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md)
rows 68–70 specify existing typed immutable assessments. Hash Contract
[15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md), common encoding
and literature payloads, requires an ADR and new material version for incompatible
material changes. Temporal [19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md)
requires advancing authorization time after waits.

| Inspected source | Current behavior; B19 distinction |
| --- | --- |
| [PR2-18 draft](PR2-18_Novelty_PriorArt_Contract_DRAFT.md), §3.3; [B18](B18_Novelty_Coverage_Completion_Contract_DRAFT.md), including its implementation record; [B18 evidence](../../pr_evidence/B18/VERIFICATION.md) | B18 S1 is implemented. The missing assessment-to-comparison basis is explicitly deferred; B18's consumer tests do not admit either stronger outcome. Historical evidence is not a fresh pass here. |
| [domain/novelty.py](../../src/researchbase/domain/novelty.py), [application/novelty.py](../../src/researchbase/application/novelty.py) | Three recording commands and three exact reads; six comparison kinds; assessment command and material contain no comparison inputs. `_once` admits only INCONCLUSIVE. `_comparison` validates exact source/evidence and independent HUMAN verification. |
| [novelty_repository.py](../../src/researchbase/persistence/novelty_repository.py), [uow.py](../../src/researchbase/persistence/uow.py) | READ COMMITTED with N SHARE locks first, request advisory then Claim row lock; read-only formal snapshots; normalized SQLSTATE-qualified retries. |
| [0047](../../migrations/versions/0047_pr2_18_novelty_prior_art.py), [0050](../../migrations/versions/0050_b01_resolution_admission.py), [0057](../../migrations/versions/0057_xid_wraparound_guards.py) | Five novelty tables, INCONCLUSIVE CHECK, sealed evidence children, deferred completeness; B01 deferred resolution closure; epoch-safe same-transaction child seals. |
| [metadata_observation.py](../../src/researchbase/application/metadata_observation.py), [B01 contract](B01_Search_Result_Resolution_Contract_DRAFT.md) | Existing hashed immutable result resolutions; all rows must agree on one nonnull exact source/version to resolve a result. A source-only row followed by an exact row remains ambiguous. Reuse the existing resolution hash verifier, not an invented R2 resolution payload. |
| [decision_repository.py](../../src/researchbase/persistence/decision_repository.py), [0042](../../migrations/versions/0042_pr2_15_minimal_decision.py) | Existing first-SHARE write protocol and deferred typed-basis completeness pattern. These are mechanisms to reuse, not new Decision targets. |

The inspected migration files run through `0064_b14_publication_ready.py`.
Reconcile the actual single Alembic head before implementation; no revision number
is reserved here. The reference drafts' older baseline inventories are historical.
No B19 execution pack exists in the inspected execution tree; this draft cannot
replace execution authorization.

## 2. Scope, dependency boundaries and non-goals

**Order:** B22 must land before B19 (CLOSE_PRIOR_ART_FOUND selects only
non-superseded B22 relations). B19 does not depend on B21. The new basis relation is
AQ B19-AQ-01 in ADR-0017.

Proposed delta: extend the existing assessment command/read for a positive close-art
finding. Reuse existing Claim, coverage, relation, evidence and resolution owners.
Add a typed child relation rather than a new canonical entity, snapshot service,
receipt, JSON reference list or persistence mechanism. B18 S1 and B01 resolution
admission are prerequisites. The extra storage and v2 payload require explicit
architecture admission (§9); they are proposals, not current frozen architecture.

Cross-draft order and guard ownership are defined once in
[ADR-0017 Decision 3](../architecture/adr/ADR-0017-novelty-material-v2.md#3-cross-draft-order-and-migration-composition).
That decision is the dependency contract for this draft's single forward migration.

New CLOSE_PRIOR_ART_FOUND basis relations must be non-superseded B22 chain
terminals. Explicit basis selection across independent roots is allowed; it does
not assert B22 UNIQUE selection or adjudicate competing roots.

A positive existential finding does not require every result to be resolved or
screened, successful execution of every planned provider, or proof of no omitted
art. Preserve coverage warnings and limitations. No new review, Decision,
Approval, publication or external-effect workflow is introduced.

## 3. Invariants and conservative judgments

1. Bind one exact frozen ClaimVersion and immutable SearchCoverage in the same
   Project. A basis relation must bind that exact Claim, not another version.
   It must have no B22 successor at admission.
   Its exact SourceVersion must be project-accessible and currently usable.
2. Each selected relation contributes **all** its sealed
   `prior_art_evidence_inputs`; no second assessment-owned evidence selection.
   Verify relation, Claim, SourceVersion, LiteratureEvidence and retained artifact
   closure with existing readers. Admission requires current VERIFIED evidence
   and latest independent HUMAN verification distinct from the evidence creator,
   exactly as `_comparison`/`independent_verification` enforce today.
3. Each basis row selects one existing SearchResultResolution witness for that
   relation. Its result → query → execution must be in the assessment coverage's
   sealed execution set. Resolution project, source identity and exact version
   must agree with the relation; all current resolution rows for that result
   must agree on that one nonnull pair. Check the witness's existing own hash.
   The witness may postdate coverage capture: it proves selected-execution scope
   at assessment creation, not a historical resolution count at coverage capture.
4. Select 1..100 distinct relations, with one witness per relation. At least one
   selected relation must be IDENTICAL or HIGHLY_SIMILAR. Other registered kinds
   may be retained as qualification/contradiction; none alone establishes close
   art. Validate every selected input, not just the favorable one. Scope statement,
   closeness criteria and limitations explain the judgment; no computed similarity
   threshold or automated language/time-filter compliance is asserted. Criteria
   admission validates presence, ordered text shape and bounds only; it never
   parses narrative as formal rules. Closed outcome/comparison enums and the
   typed basis/evidence checks establish admission, as justified in
   [ADR-0017 Alternatives](../architecture/adr/ADR-0017-novelty-material-v2.md#alternatives).
5. This is an explicit selected basis, not a complete inventory of all comparisons.
   Unselected and later contradictory relations remain independently readable;
   no implicit favorable-subset discovery, “latest wins”, deletion or adjudication.
   The result asserts a specific close comparison within the stated scope only.
6. Parent, basis and own hash publish atomically. After commit neither membership,
   scope, criteria, witness nor material changes. Corrections create a new record
   using the existing same-Claim, single-successor supersession chain. No cycles,
   forks or current-assessment pointer; supersession alone is not invalidity.
7. Later B22 succession, source correction/retraction, evidence dispute or new ambiguous resolution
   makes a saved v2 finding unusable for current judgment when its bound closure
   fails current validity. Preserve the saved material/hash and show timestamped
   diagnostics. Hash/identity corruption fails closed; legitimate later invalidity
   is a projection, not a read error or historical rewrite. A later B22 successor
   sets current usability false without redirecting the saved basis; the historical
   finding and its hash remain valid history. Replay remains a
   historical read with current entitlement, not re-admission of the finding.

## 4. Proposed commands, DTOs and historical readback

Extend `RecordNoveltyAssessmentCommand` and `NoveltyReadback`, not the service's
method inventory. B19 adds no coverage/prior-art command fields or public
operations; retain B22's predecessor fields and additional pair selector.
The command UUID is canonical assessment identity and replay key; no new receipt.

| Outcome | Proposed command admission and read material |
| --- | --- |
| INCONCLUSIVE | Existing v1 command; empty basis, null scope and criteria. Persist material_version=1, same literal hash. |
| CLOSE_PRIOR_ART_FOUND | Nonempty explicit basis and nonblank scope/criteria, all §3 checks. Persist material_version=2. |
| NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE | Reject INVALID_STATE_TRANSITION, even if positive basis fields are supplied. |

OWNER/RESEARCHER may create in an active Project. OWNER/RESEARCHER/REVIEWER/VIEWER/
APPROVER may read under existing authenticated project policy. Principal, effective
time and assessor are derived. Replay requires the original actor and project,
equal normalized input including basis pairing, and current reader entitlement;
changed material raises IDEMPOTENCY_CONFLICT with no writes. Do not require current
writer role or new-write validity for an already saved matching record.

Readback returns only the saved relation/witness pairs and transitive exact
relation/evidence material, plus current diagnostics. No current-table expansion
may change membership. V1 rows project version 1, empty basis and null scope/criteria
without adding these fields to their hashed payload. Unknown material versions
fail PROVENANCE_CLOSURE_VIOLATION. Old callers omitting new optional command fields
retain v1 behavior; updated transports expose the additive read fields explicitly.

## 5. Schema and literal hash proposal — one forward migration; one new table

The migration adds `material_version`, `scope_statement` and typed
`closeness_criteria TEXT[]` columns to `novelty_assessments`, the
`novelty_assessment_prior_art_inputs` table and §12.1 constraints/guards.
No direct assessment/evidence table:
relation membership plus immutable `prior_art_evidence_inputs` already fixes it.
Retain `sha256-cjson-v1`, canonical JSON and all existing v1 literal payloads.
`material_version` identifies NoveltyAssessment material, not a new hash algorithm.

The complete NoveltyAssessment v2 payload and shared v1 compatibility decision
are specified once in [ADR-0017](../architecture/adr/ADR-0017-novelty-material-v2.md),
Decision 1. This draft requests that amendment to frozen Hash Contract 15; it cannot approve it.

`closeness_criteria` serializes the typed SQL array as the closed
`{"statements":[...]}` value specified by ADR-0017: authored
statement order is material. Basis entries sort by prior-art relation UUID;
duplicate relation IDs reject before sorting, even with different witnesses.
Shared witness IDs across distinct relations are allowed. Embedded relation hashes
bind their full exact evidence sets; resolution hashes use the existing M2/B01
verifier unchanged. Predecessor may be v1 or v2; verify it by its saved version
before embedding its existing hash. No recomputation of a v1 predecessor as v2.

Exclude row/child IDs, timestamps, derived project/validity, verification status,
current warnings and hash scheme, as with existing novelty material. B19 changes
only assessment material; B21/B22 separately version coverage/prior-art material
under the same ADR. Claim/support, evidence and resolution hashes stay unchanged.
The transitive evidence closure is verified on read/restart, not duplicated in v2.

## 6. Error contract

Use existing categories and §11.2 mappings; introduce no ErrorCode. Validate DTO
shape before opening a transaction. After authenticated access checks, missing
selected records are NOT_FOUND; wrong project is FORBIDDEN. Nonfrozen exact inputs
are FROZEN_REFERENCE_REQUIRED. Missing close-kind basis or currently unverified
evidence is INVALID_STATE_TRANSITION. Same-Claim/source/coverage/witness mismatch,
ambiguous witness result, unusable scientific inputs or digest corruption is
PROVENANCE_CLOSURE_VIOLATION. DTO field/outcome-shape inconsistencies are
VALIDATION_ERROR; the unavailable negative outcome is INVALID_STATE_TRANSITION.
A selected basis relation or assessment predecessor already superseded is
INVALID_STATE_TRANSITION; concurrent unique
predecessor loss is CONCURRENT_MODIFICATION.

Keep existing UoW normalization: immutable guard P17D1 → IMMUTABLE_RECORD;
P17D2 → INVALID_STATE_TRANSITION; P17D3 → PROVENANCE_CLOSURE_VIOLATION;
FK violations → REFERENTIAL_INTEGRITY_ERROR; ordinary CHECK violations →
VALIDATION_ERROR. Extend named new constraints accordingly. CHECK `ck_b19_novelty_material` maps to INVALID_STATE_TRANSITION for
unsupported persisted outcome/version combinations; transport shape failures
remain VALIDATION_ERROR. Sanitized messages reveal no SQL, credentials or paths.

## 7. Transactions, concurrency and failure recovery

One synchronous Application command equals one PostgreSQL transaction. §12.2
specifies every explicit lock. Immutable basis tables need no new table locks:
selected dependencies are sealed, and assessment membership is explicit. Mutable
validity and resolution ranges are already in N. Do not SHARE-lock tables that
this transaction inserts into, or introduce lock upgrades.

First prehold N, then request/Claim locks, then authorization and input reads.
Recheck live credentials, role intervals and Project lifecycle using fresh
`clock_timestamp()` after waits and before commit. Force all deferred constraints,
verify saved readback and recheck authority before committing. Database parent and
child guards require the preheld protocol, rather than acquiring it after reads.
A direct SQL writer without it fails; database constraints still enforce structural
closure under normal-role bypass. Do not trust caller flags for protocol admission.

Retry only SQLSTATE 40001/40P01, at most three fresh UoWs, using existing retry flag
normalization; no external calls, sleeps or new retry mechanism. Exhaustion gives
CONCURRENT_MODIFICATION. Unique business conflicts, 55P03/57014, connection loss
and unknown commit are not automatic retries. Recover an unknown commit by exact
same UUID and current reader entitlement, not a new assessment ID. Rollback leaves
no parent, basis or success effect. Reads never invoke write preparation helpers.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

Use independent literal v1/v2 payload oracles and real PostgreSQL 18 normal-role
SQL. Exercise selected-basis sealing, exact resolution scope, later invalidity,
restart and actual two-backend waits. Required files/cases are pinned in §12.4.
Do not replace executed concurrency evidence with source-string or timing checks.

## 9. Acceptance criteria and evidence boundary

Before implementation, approve [ADR-0017](../architecture/adr/ADR-0017-novelty-material-v2.md) admitting the one typed
relation, new columns and v2 payload, and reconcile Architecture 13/15 and the
PR2-18 stronger-outcome guard explicitly. This draft alone cannot amend them.
Contract approval, architecture admission and execution authorization are distinct.
ADR-0017 is a proposal in `docs/proposals/`; no frozen architecture file changes.

After authorization, completion requires focused static/unit/architecture and
PostgreSQL results, migration preservation/refusal tests, transport parity and
zero open P0/P1 findings. Record exact commands/counts and retained identities/hash
vectors. Run the whole suite only through the owning loop as requested. B19's
positive finding is not negative-novelty completeness, full PR2-18 or Phase 2 gate
acceptance. Stop after the authorized positive-basis slice.

## 10. Glossary

| Term | Meaning |
| --- | --- |
| Basis | Saved relation/witness pairs; each relation transitively binds all its evidence. |
| Witness | Existing exact SearchResultResolution connecting a selected execution result to the comparison's source/version. Retrieval provenance, not scientific evidence. |
| N | Ordered SHARE-lock inventory exported by novelty_repository.py, expanded in §12.2. |
| Close kind | IDENTICAL or HIGHLY_SIMILAR; attributed comparison, not an automatic similarity metric. |
| Scope / criteria | Explicit scope statement plus ordered closeness statements; no claim of exhaustive provider/filter compliance. |
| Material version / hash scheme | Payload shape selector 1 or 2 / unchanged sha256-cjson-v1 algorithm and serialization. |
| Historical / current | Saved immutable material / timestamped usability diagnostics from the read snapshot. |

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

Propose a selected positive basis only. Include one exact selected-execution
resolution witness per comparison to make scope testable; free-text scope alone
cannot establish execution membership. Reuse sealed evidence sets rather than
creating a competing assessment/evidence owner. Preserve contradictory records,
coverage limitations and current quality warnings. Do not require exhaustive
screening for an existential finding. INCONCLUSIVE stays v1; CLOSE uses v2;
NO_CLOSE stays denied in Application and PostgreSQL. No runtime dependency added.
All these are proposed contract choices awaiting approval, not existing behavior.

### 11.2 Pinned error mappings

From [api/errors.py](../../src/researchbase/api/errors.py) and
[cli/errors.py](../../src/researchbase/cli/errors.py). Novelty uses the shared
invocation option for unexpected-error exit 1. INTERNAL_ERROR is fallback text,
not an ErrorCode; HASH_MISMATCH is not an implemented novelty error.

| Code | HTTP | CLI |
| --- | ---: | ---: |
| AUTHENTICATION_REQUIRED | 401 | 3 |
| FORBIDDEN | 403 | 3 |
| VALIDATION_ERROR | 422 | 2 |
| NOT_FOUND | 404 | 3 |
| FROZEN_REFERENCE_REQUIRED | 409 | 5 |
| INVALID_STATE_TRANSITION | 409 | 4 |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 |
| IDEMPOTENCY_CONFLICT | 409 | 4 |
| IMMUTABLE_RECORD | 409 | 4 |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 |
| CONCURRENT_MODIFICATION | 409 | 4 |
| INTERNAL_ERROR | 500 | 1 |

### 11.3 DTO fields, Python types and limits

Extend existing frozen, slotted dataclasses; transports remain closed to extra
keys. Strict UUID means Python `type(value) is UUID`; wire UUIDs parse through
existing adapters. Reject bool-as-int and caller-supplied material version, hashes,
assessor, time, principal, role or validity. Hashes below are derived lowercase
64-hex `str`; time is UTC `datetime`. Text is NFC, valid UTF-8, NUL-free, nonblank,
1..16,384 Unicode characters; preserve meaningful whitespace.

| DTO | Exact fields / proposed additions |
| --- | --- |
| RecordNoveltyAssessmentCommand | Existing `id: UUID`, `project_id: UUID`, `claim_version_id: UUID`, `search_coverage_id: UUID`, `assessment: NoveltyOutcome`, `limitations: str`, `supersedes_assessment_id: UUID \| None = None`; append `prior_art_basis: tuple[PriorArtBasisInput, ...] = ()`, `scope_statement: str \| None = None`, `closeness_criteria: ClosenessCriteria \| None = None`. |
| PriorArtBasisInput | Exactly `prior_art_relation_id: UUID`, `search_result_resolution_id: UUID`. Frozen typed value, no own entity identity/hash. |
| ClosenessCriteria | Exactly `statements: tuple[str, ...]`, 1..100 statements, each narrative-bounded; total ≤16,384 Unicode characters. Authored order retained. Wire/hash form is exactly `{"statements":[...]}`; storage is one ordered `TEXT[]` column, never JSONB. |
| ExactReadQuery | Unchanged: `project_id: UUID`, `id: UUID`. |
| NoveltyReadback | Existing fields retained (§4); append `material_version: Literal[1, 2]`, `scope_statement: str \| None`, `closeness_criteria: ClosenessCriteria \| None`, `prior_art_basis: tuple[PriorArtBasisReadback, ...]`. |
| PriorArtBasisReadback | Exactly `prior_art_relation: PriorArtReadback`, `search_result_resolution: HashRef`. Extend HashRef's closed type literals with SearchResultResolution and PriorArtRelation for witness and v2 hash building. Relation readback includes its sealed evidence HashRefs and current validity. |

Basis: zero for INCONCLUSIVE; 1..100 for CLOSE, distinct relation IDs, sorted
by UUID after rejection of duplicates. Shared witness IDs are allowed. Scope and
criteria both null for INCONCLUSIVE, both required for CLOSE. Criteria statements
are explanatory narrative, never parsed as executable rules or used to replace
closed PriorArtKind/outcome and typed basis/evidence admission. ADR-0017
Alternatives explicitly compares this bounded narrative column with a closed enum
and typed criterion child rows; its justification requires owner approval.
No caller can set version 2 on an empty or inconclusive basis. Narrative remains independently
bounded for limitations and scope. Existing input evidence sets remain 1..100;
therefore one assessment reaches at most 10,000 evidence occurrences before
cross-relation deduplication. No truncation of a saved set on read.

Enums unchanged: PriorArtKind = IDENTICAL/HIGHLY_SIMILAR/PARTIAL_OVERLAP/RELATED/
CONTRASTING/UNCLEAR; NoveltyOutcome = INCONCLUSIVE/CLOSE_PRIOR_ART_FOUND/
NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE. Keep existing QualityWarning and
CoverageQuality/CurrentValidity types from `application/novelty.py`; v2 folds all
bound comparisons' usability and witness ambiguity into CurrentValidity, emitting
INPUT_CURRENTLY_UNUSABLE when false. Coverage quality remains separately visible.
Existing coverage/prior-art command fields, quality enums and limits stay as pinned
in B18 §11.3; no new confidence, screening or source-scope enum is introduced.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

**No DDL is executed by this task.** Proposed additive forward migration, after
head reconciliation; constraint names below are fixed by this draft. Keep existing
RESTRICT FKs, immutable triggers and `uq_pr218_novelty_predecessor`.

```sql
ALTER TABLE novelty_assessments
  ADD COLUMN material_version SMALLINT NOT NULL DEFAULT 1,
  ADD COLUMN scope_statement TEXT NULL,
  ADD COLUMN closeness_criteria TEXT[] NULL;
ALTER TABLE novelty_assessments DROP CONSTRAINT ck_pr218_novelty_initial_slice;
ALTER TABLE novelty_assessments ADD CONSTRAINT ck_b19_novelty_material CHECK (
  (material_version=1 AND assessment='INCONCLUSIVE'
    AND scope_statement IS NULL AND closeness_criteria IS NULL)
  OR (material_version=2 AND assessment='CLOSE_PRIOR_ART_FOUND'
    AND scope_statement IS NOT NULL AND closeness_criteria IS NOT NULL));
ALTER TABLE novelty_assessments ADD CONSTRAINT ck_b19_scope CHECK (
  scope_statement IS NULL OR
  (length(btrim(scope_statement))>0 AND char_length(scope_statement)<=16384));
ALTER TABLE novelty_assessments ADD CONSTRAINT ck_b19_criteria CHECK (
  closeness_criteria IS NULL OR b19_valid_criteria(closeness_criteria));
CREATE TABLE novelty_assessment_prior_art_inputs (
  id UUID NOT NULL CONSTRAINT pk_b19_basis PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL,
  created_by UUID NOT NULL CONSTRAINT fk_b19_basis_actor
    REFERENCES actors(id) ON DELETE RESTRICT,
  novelty_assessment_id UUID NOT NULL CONSTRAINT fk_b19_basis_assessment
    REFERENCES novelty_assessments(id) ON DELETE RESTRICT,
  prior_art_relation_id UUID NOT NULL CONSTRAINT fk_b19_basis_relation
    REFERENCES prior_art_relations(id) ON DELETE RESTRICT,
  search_result_resolution_id UUID NOT NULL CONSTRAINT fk_b19_basis_resolution
    REFERENCES search_result_resolutions(id) ON DELETE RESTRICT,
  CONSTRAINT uq_b19_basis_relation UNIQUE(novelty_assessment_id,prior_art_relation_id)
);
CREATE INDEX ix_b19_basis_actor ON novelty_assessment_prior_art_inputs(created_by);
CREATE INDEX ix_b19_basis_relation ON novelty_assessment_prior_art_inputs(prior_art_relation_id);
CREATE INDEX ix_b19_basis_resolution ON novelty_assessment_prior_art_inputs(search_result_resolution_id);
```

`b19_valid_criteria(TEXT[]) RETURNS BOOLEAN` validates a typed ordered column:
one dimension with lower bound 1, 1..100 nonnull text elements, each nonblank NFC,
valid UTF-8 and at most 16,384 characters, total at most 16,384 characters. It is
immutable and rejects empty/multidimensional arrays, NULL elements and nonstandard
bounds; SQL NULL is allowed only for v1 by `ck_b19_novelty_material`. The
Application maps the ordered tuple to this column and reconstructs exactly
`{"statements":[...]}` for wire/hash material. No free-form JSON semantic storage
or new criteria entity/table is introduced. Existing own hashes remain CHAR(64),
`ck_pr218_novelty_hash`; scheme remains VARCHAR(32), `ck_pr218_novelty_scheme`.

Proposed guards, all with fixed `search_path = pg_catalog, public, pg_temp`:

- `trg_b19_basis_immutable`: BEFORE UPDATE OR DELETE, existing P17D1 policy.
- `trg_b19_basis_insert`: BEFORE INSERT, requires `pr218_capture_prelocked()`,
  parent `xmin = pg_current_xact_id()::xid` as corrected by 0057, same created_by,
  material version 2 and §3's exact typed joins. Late inserts raise P17D1;
  scope/closure failures P17D3. Parent/child timestamps use trusted creation time.
- `trg_b19_novelty_complete` on parent and `trg_b19_basis_complete` on child:
  AFTER INSERT constraint triggers, DEFERRABLE INITIALLY DEFERRED, invoking
  `b19_complete_basis()`. At transaction end require zero children for v1;
  1..100 for v2, at least one close kind, exact Claim/project/source/evidence
  and witness execution/resolution agreement, non-superseded B22 terminals and
  usable current inputs. No parent without basis can commit, including normal-role SQL. Missing/oversized basis or
  absence of a close kind or a superseded basis raises P17D2; typed closure failures raise P17D3. Use existing verification
  predicates and 0050's resolution closure; never mutate existing evidence rows.
- Add BEFORE INSERT `trg_b19_novelty_prelocked` on novelty_assessments,
  calling `b19_require_prelocked() RETURNS trigger`: require
  `pr218_capture_prelocked()`, else P17D3, then return NEW without acquiring locks.
  Its fixed name sorts before both `trg_pr218_novelty_chain` and
  `trg_pr218_novelty_assessments_parent_guard`, so the baseline guard cannot
  acquire Claim/N locks first for a bypass writer. Leave `pr218_parent_guard()`
  and every sibling function unchanged; attach the additional check as specified
  in ADR-0017 Decision 3. `trg_b19_basis_insert` calls `b19_basis_insert_guard()`;
  immutable children reuse `pr218_immutable()`. Child/deferred guards acquire no
  new locks.

Database guards enforce structural admission and independent verification;
Application recomputes scientific hashes/retained bytes, as today. No claim that
PostgreSQL CHECKs alone recompute canonical scientific material. Direct SQL with
fabricated hashes must fail closed at formal read.

Preflight rejects any existing non-INCONCLUSIVE assessment, unresolved ownership
or broken immutable closure rather than guessing repairs. Existing rows receive
version 1 only; own hashes and material remain untouched. Migration tests compare
pre/post exact v1 digests. Downgrade takes ACCESS EXCLUSIVE on the assessment and
new input table, refuses any v2 or input rows, and otherwise restores the original
INCONCLUSIVE guard and drops only B19 objects/columns, preserving B21/B22 guards.
Never erase history to make downgrade succeed; refuse inside the migration transaction.

### 12.2 Exact lock order and transactions

N is unchanged, copied literally from the current adapter. For **all three write
commands**, configure READ COMMITTED through connection execution options (no SQL),
then execute this as the **FIRST statement**, before SET LOCAL, SELECT or auth:

```sql
LOCK TABLE actor_subject_bindings,actors,artifact_versions,artifacts,audit_findings,
claim_versions,claims,correction_records,datasets,experiment_spec_versions,
experiment_specs,impact_assessments,impact_targets,literature_evidence,
literature_evidence_review_events,literature_search_execution_events,
literature_search_executions,literature_search_plan_versions,literature_search_plans,
literature_search_provider_attempts,literature_source_project_links,literature_sources,
metadata_observations,metric_definition_versions,metric_definitions,
project_membership_events,project_memberships,project_role_assignments,projects,runs,
scientific_conclusions,search_query_records,search_result_records,
search_result_resolutions,source_versions IN SHARE MODE;
```

Then SET LOCAL lock_timeout='10s', SET LOCAL statement_timeout='30s'; request
`pg_advisory_xact_lock(hashtextextended(:key,0))` with existing canonical key
`pr218:{kind}:{id}`. No explicit table lock is added for novelty_assessments,
prior_art_relations or either immutable input table.

| Command | Exact remaining order after N/timeouts |
| --- | --- |
| record_search_coverage | kind=coverage advisory; reader auth; replay check; writer auth if new; plan and sorted execution/history capture; writer recheck; parent then sorted execution children (plus B21 capture children when installed). No target row lock. |
| record_prior_art_relation | kind=prior_art advisory; exact ClaimVersion FOR UPDATE; reader auth/replay; writer auth if new; exact Claim/source and sorted evidence validation; writer recheck; parent then sorted evidence children, retaining B22 predecessor admission/locking for corrections. |
| record_novelty_assessment, v1 or v2 | kind=novelty advisory; exact ClaimVersion FOR UPDATE; reader auth/replay including version/basis; writer auth if new; Claim/coverage verification; v2 selected relation/witness validation in relation-UUID order using plain reads, rejecting any B22 successor after the Claim lock; optional predecessor FOR UPDATE, same-Claim/single-successor validation and versioned read; writer recheck; parent then basis children in relation-UUID order. B22 corrections use this same Claim lock, so terminal checks stay stable through commit. No other explicit row locks. |

New writes force SET CONSTRAINTS ALL IMMEDIATE, verify versioned saved readback,
recheck writer at fresh DB time, commit. Matching replay verifies saved hashes and
current reader entitlement and returns without inserts. A retry repeats everything.
Implicit FK locks are ordinary PostgreSQL behavior, not extra explicit read locks.

All three exact-read commands call `begin_formal_read()`, authorize, read exact
parent/children and transitive saved closure, compute current projections and
recheck reader entitlement at advancing DB time inside **one read-only REPEATABLE
READ snapshot**. No prepare, FOR UPDATE/SHARE, table/advisory lock, side UoW or
canonical write anywhere in their dependency traversal. Reuse the existing plain
`_hash`/resolution readers, not MetadataObservationService's locking write auth.

### 12.3 Ordered build steps and module paths

1. Obtain the approved ADR/architecture updates and execution authorization;
   reconcile actual head and add one forward file under `migrations/versions/`
   with suffix `_b19_close_prior_art_basis.py`. Do not reserve a number or alter
   0047/0050/0057. Extend migration evidence, including safe downgrade refusal.
2. Extend `src/researchbase/domain/novelty.py` with pure basis/criteria values,
   strict bounds, new HashRef literals and a separate v2 material builder. Retain
   `novelty_material` v1 unchanged and add strict version dispatch.
3. Extend `src/researchbase/application/novelty.py` DTOs, `_once` admission,
   `_view_saved` version dispatch, selected-basis verification, replay comparison
   and current validity. Reuse `_comparison`, existing saved-dependency context,
   evidence/source readers and metadata resolution hash verification. Do not
   re-admit saved historical v2 rows using new-write validity rules.
4. Extend `src/researchbase/persistence/novelty_repository.py` with plain ordered
   basis/resolution reads and child inserts. Keep prepare and N lock order exact.
   Extend named error normalization in `src/researchbase/persistence/uow.py`;
   follow its existing repository exposure (no speculative new port framework).
   Application → UoW/repository → adapter stays the only canonical write path.
5. Extend existing models/routes in `src/researchbase/api/routes.py` and nested
   `--material-json` parsing in `src/researchbase/cli/commands/literature.py`; reuse existing
   service composition in `src/researchbase/api/app.py`. Keep POST/GET
   `/v1/projects/{project_id}/novelty-assessments` (GET adds `/{id}`) and existing
   CLI `--project-id`, `--material-json`, `--json` options. Additive optional inputs,
   no new endpoint or authority model. Existing error mapping files need no codes.
6. Add §12.4 tests through existing fixture builders; update the approved contract
   and evidence together if a discovered implementation constraint changes it.
   Run focused checks, report exact results and stop at the positive-basis boundary.

### 12.4 Test artifacts and required cases

Names marked new are proposed files; existing paths are regression anchors.

| File / suite | Required cases after authorization |
| --- | --- |
| New `tests/unit/phase2/test_b19_close_prior_art_contract.py` | Strict UUID/tuple/closed nested types; duplicate relation/different witness rejection; shared witness allowed; 0/1/100/101 limits; text/NFC/Unicode/criteria total limits; outcome-field XOR; version derived, never caller chosen; error mappings. |
| New `tests/unit/phase2/test_b19_close_prior_art_hash_vectors.py`; existing `test_pr2_18_hash_vectors.py` | Independent literal v2 vector; reorder basis invariant, criteria order material; changed relation/evidence/witness/scope affects digest; all excluded fields invariant; unchanged v1 bytes; mixed-version predecessor; unknown version rejected. |
| New `tests/architecture/test_b19_close_prior_art_boundaries.py`; existing `test_pr2_18_boundaries.py` | No new canonical owner, domain adapter dependency or direct evidence owner; no B19 method additions; retain B22 selector; first-N writes and read traversal without explicit locks; no negative-outcome admission. |
| New `tests/integration/phase2/test_b19_close_prior_art_schema.py` | Clean upgrade; populated v1 migration/read/hash preservation; typed array shape/NULL/NFC/bounds; normal-role SQL superseded relation, wrong Claim/project/source/execution, ambiguous/source-only resolution, nonverified evidence, parent without children, 101 children and non-close-only basis denied; parent/child UPDATE/DELETE and late insertion denied; same-transaction seal epoch-safe; rollback; populated-v2 downgrade refusal, v1-only downgrade preservation. Force constraints and test commit-time rejection separately. |
| New `tests/integration/phase2/test_b19_close_prior_art_basis.py` | Real owning commands → coverage → verified close relation → v2 assessment → restart exact read. Full evidence membership retained; selected witness may postdate coverage, saved counts unchanged; qualified close plus contradictory selected input retained; missing witness/unresolved result/cross-version/wrong coverage rejected; no negative admission or unrelated support/governance effects. |
| New `tests/integration/phase2/test_b19_close_prior_art_replay.py` | Equal normalized replay/restart; changed pairing/scope/criteria conflict; original actor/project checks; role downgrade to reader; expired/revoked access denied; later B22 succession/dispute/retraction/correction/ambiguous resolution alters only current usability; new unrelated comparison leaves saved basis unchanged; v1↔v2 predecessor chains with one successor. |
| New `tests/integration/phase2/test_b19_close_prior_art_concurrency.py` | Observe B19 versus B22 correction in both Claim-lock orders (correction first rejects predecessor; assessment first retains history with later unusability); backend wait/blocker for both commit orders: source/evidence validity change and initially empty additional-resolution range versus capture; one legal basis or denial, never hybrid. Concurrent same UUID yields one record; same Claim/predecessor distinct UUID yields one successor; post-lock credential expiry rolls back; injected retry/commit uncertainty follows §7. Read paths observed without explicit lock helpers under concurrent writes, one snapshot and zero writes. |
| Existing `tests/unit/phase2/test_pr2_18_transports.py`; new `tests/integration/phase2/test_b19_close_prior_art_api.py` | Existing v1 API/CLI parity; v2 nested input, readback, JSON closure, forbidden server fields and exact §11.2 status/exit codes; injected unexpected failure HTTP 500/CLI 1. |
| Existing `tests/integration/phase2/test_pr2_18_*.py`, `test_b01_resolution_*.py`, `test_pr2_19_novelty.py`, `test_pr2_20_novelty.py` | Unchanged coverage accounting, six comparisons, v1 replay, sealed/deferred guards, B01 phantoms and bounded B18 consumers. Update only tests whose intentional “CLOSE always denied” premise becomes superseded; keep unbacked CLOSE and all NO_CLOSE denial assertions. |

Focused future commands: static Ruff/Pyright; `pytest tests/unit tests/architecture
tests/test_architecture.py`; PostgreSQL `pytest tests/integration/phase2/test_b19_*.py
tests/integration/phase2/test_pr2_18_*.py tests/integration/phase2/test_b01_resolution_*.py
tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_20_novelty.py`.
Use the repository's PostgreSQL admin/test selectors and record actual counts.
No full-suite run or large benchmark is required of this documentation author.

### 12.5 Not in this slice

NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE; intended-probe inventory, negative probes,
exhaustive screening dispositions, automatic search completeness/filter compliance,
new captured unresolved counts; correction/adjudication of conflicting prior-art
relations; new novelty review/Decision/Approval targets; impact-propagation engine;
Claim literature-support changes; manuscript/package workflows; provider calls,
queues, agent frameworks or runtime dependencies. No implementation, tests,
migrations or canonical architecture documents change in this task. ADR-0017 is
the shared proposed decision only.

## 13. Open questions for the owner — override register

Approve or replace [ADR-0017](../architecture/adr/ADR-0017-novelty-material-v2.md), Decisions 1–3, and the proposed selected
positive basis, exact-resolution witness,
explicit criteria bounds and v1/v2 split. Architecture admission must explicitly
approve the typed child table and scope/criteria/version columns; until then the
implemented INCONCLUSIVE-only guard remains binding until B19 authorization.
There is no deferred choice for the implementer to invent. Contract approval does not authorize implementation.

## 14. Documentation verification note

### Reviewer-remediation verification — 2026-10-18

Only B19, B21, B22 and proposed ADR-0017 changed; the three status lines are
unchanged. These are current-code regression checks, not implementation evidence
for the proposed contracts. No whole-suite run, commit, push or branch creation.
Commands below used this shared environment without dependency synchronization:

```sh
export PYTHONPATH="$PWD/src:$PWD"
export VIRTUAL_ENV=/Users/fengwang/Documents/ResearchBaseProject/.venv
export UV_CACHE_DIR=/private/tmp/rb-novelty-review-uv-cache
export DATABASE_URL=postgresql+psycopg://fengwang@localhost/postgres
export RB_TEST_ADMIN_URL=postgresql+psycopg://fengwang@localhost/postgres
```

| Exact command after exports | Observed result |
| --- | --- |
| `uv run --active --offline --no-sync ruff check .` | Exit 0; all checks passed. |
| `uv run --active --offline --no-sync ruff format --check .` | Exit 0; 699 files already formatted. |
| `uv run --active --offline --no-sync pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject` | Exit 0; 0 errors, 0 warnings, 0 informations. |
| `uv run --active --offline --no-sync pytest tests/unit/phase2/test_pr2_18_*.py tests/unit/phase2/test_b01_*.py tests/architecture/test_pr2_18_boundaries.py tests/architecture/test_b01_resolution_boundaries.py` | Exit 0; 126 passed in 2.82s. |
| `uv run --active --offline --no-sync pytest -x tests/integration/phase2/test_pr2_18_*.py` | Exit 1; 1 setup error in 0.43s; zero PostgreSQL cases passed, remaining cases not run after fail-fast. |
| `git diff --check` | Exit 0; no whitespace errors. |
| `test -z "$(git status --porcelain -- . ':!docs/proposals' ':!.pipeline')"` | Exit 0; no changes outside the permitted paths. |

**Verdict: documentation checks passed; PostgreSQL verification BLOCKED.** The
requested PR2-18 rerun failed before its first case because the sandbox denied
connections to localhost:5432 (`Operation not permitted`). PostgreSQL 18.x and
proposed guard behavior remain unverified. The prior broader run's four runner
socket failures and 14 PostgreSQL setup errors were environment failures, not
passes; that broader run was not repeated for this documentation-only remediation.
Stale per-draft authoring tables have been removed; this is the sole current
verification record. No implementation acceptance, migration-order test result or
Phase exit is claimed. The full-suite check remains with the owning loop.
