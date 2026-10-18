# B22 PriorArtRelation Correction Selection Contract — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

## Start here (for the implementer)

B22 adds explicit corrections to B18's immutable prior-art comparisons and a
read-only selector for one exact ClaimVersion/SourceVersion pair. A correction
creates a new comparison referring to its predecessor; it never edits history.
The selector returns the terminal comparison of each independent chain. It
selects one record only when there is exactly one chain, and reports ambiguity
otherwise. Time, actor seniority and enum strength never select a winner.
Selection describes recorded comparison history, not scientific truth.

Build in this order after separate authorization:

1. Approve the bounded field/hash amendment and compatibility ADR (§§5, 9).
2. Add only the additive migration and guards (§12.1).
3. Extend pure material validation, the Application command and typed ports
   (§§11.3, 12.3); preserve ordinary B18 root recording and exact reads.
4. Implement the write protocol and snapshot-only selection (§12.2).
5. Add thin API/CLI adapters and the pinned errors (§§4, 11.2).
6. Run the specified tests, record actual evidence, and stop (§§9, 12.4).

Five review rules:

1. Exact same ClaimVersion **and** SourceVersion throughout each chain.
2. One predecessor and at most one successor; independent roots remain visible.
3. Old v1 digests stay identical; correction edges enter explicit v2 material.
4. Writes take the existing N SHARE lock as their first transaction statement;
   reads use one REPEATABLE READ snapshot without explicit locks.
5. An unusable terminal record never causes fallback to an older/other record.

Use §10 for terms, §11 for fixed draft choices and §12 for implementation details.
This file is a proposal, not an execution pack, architecture amendment, migration
permission or acceptance declaration. No B22 behavior is implemented by this task.

## 1. Purpose, authority and inspected baseline

| Source | Constraint used here |
| --- | --- |
| [System Architecture 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 6.7 | Immutable history, exact frozen provenance, literature ownership; deterministic facts precede authority. |
| [Correction Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A18–A20; [Cross-Phase 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md) | Preserve Phase 1 contracts; compatible additions, common Application boundary and fresh-time authorization. |
| [Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), Phase 2; [Phase 2 Spec 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §25 | PriorArtRelation is a literature-owned immutable comparison of exact Claim/Source versions, not a first-ever claim. |
| [Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), §§4, 7; [Field Contract 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md), novelty rows | Concrete comparison/evidence FKs and immutable records; no PriorArtRelation predecessor is currently defined. |
| [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md), common encoding and PriorArtRelation template | v1 has no correction edge. Incompatible material needs an ADR and new material version; historical digests remain verifiable. |
| [Temporal R4 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md), TEMP-AUTH-01; [Harness specification](../harness/09_Harness_Integration_Specification_v1.0.md), §§2, 18–19 | Fresh trusted clock after waits; Application-only writes; evidence before completion. |
| [Approved B18 draft](PR2-18_Novelty_PriorArt_Contract_DRAFT.md), §§12.5, 13 | Explicitly defers authoritative PriorArtRelation correction selection and retains contradictions. |

Current [domain](../../src/researchbase/domain/novelty.py),
[Application](../../src/researchbase/application/novelty.py) and
[repository](../../src/researchbase/persistence/novelty_repository.py) implement
six comparison enums, independently VERIFIED evidence admission, immutable replay
and exact-ID readback. NoveltyAssessment has a separate predecessor chain;
PriorArtRelation has none. [Migration 0047](../../migrations/versions/0047_pr2_18_novelty_prior_art.py)
seals comparison/evidence sets. Its predecessor uniqueness pattern applies to
NoveltyAssessment only. The current repository's `prepare` takes N SHARE first
for **every** scoped write; older draft lock sequences must not override it.
[Migration 0042](../../migrations/versions/0042_pr2_15_minimal_decision.py) provides
the deferred constraint-trigger pattern used below. No B22 execution pack is
supplied; B18 is the implemented dependency, not permission to extend it.

## 2. Scope, dependency boundaries and non-goals

**Order:** B22 has no prerequisite among B19/B21 and must land before B19.

Propose an optional typed predecessor on the existing recording command, an
additive correction-aware exact read, and a pair-scoped selector. Reuse the
existing tables, service, repository/UoW, serializer and trusted principals.
No new canonical entity, generic CorrectionRecord locator, JSON relation owner,
current pointer, cache, queue or external dependency is needed.

This draft proposes a bounded amendment to contracts 13/15; it does not claim
that those frozen documents already authorize correction fields. Approval of
this draft alone does not authorize implementation. See §12.5 for exclusions.

Cross-draft order and guard ownership are defined once in
[ADR-0017 Decision 3](ADR-0017_Novelty_Material_v2_DRAFT.md#3-cross-draft-order-and-migration-composition).
That decision is the dependency contract for this draft's single forward migration.

B22 alone retains INCONCLUSIVE-only assessment admission. When B19 later lands,
new CLOSE_PRIOR_ART_FOUND bases must select non-superseded terminals; independent
roots remain explicit choices, never an assertion of UNIQUE pair selection. A
later correction preserves the assessment's saved basis/hash and marks it unusable
for current judgment. B22 never silently redirects a historical assessment.

## 3. Invariants and conservative judgments

1. Every correction names one committed, exact predecessor with the same
   `claim_version_id` and `source_version_id`. Project is derived from Claim
   ownership; source/evidence access remains independently checked.
2. A root has no predecessor. A correction may extend only a terminal record.
   No self-reference, forks, cycles, cross-version correction or root merging.
   A changed Claim or SourceVersion starts a new pair/root.
3. New comparison material must pass B18 admission: frozen exact Claim/Source,
   valid closure and hashes, 1..100 distinct same-source/project evidence IDs,
   independently HUMAN-VERIFIED evidence, and currently usable inputs. Correction
   authority is OWNER/RESEARCHER, not a claim of adjudicated scientific truth.
4. The predecessor may now be unusable; verify historical material/closure without
   requiring current usability or current VERIFIED status for its old evidence.
   Structurally corrupt/unresolvable historical material fails closed. Corrections
   cannot rehabilitate a retracted source: the new inputs still pass rule 3.
5. Old rows, evidence, assessors, timestamps and hashes never change. Supersession
   is derived from the new FK; it does not invalidate historical provenance.
6. Selection includes all roots for the exact pair, even if they agree or share
   an assessor. One root means one terminal candidate; multiple roots are
   AMBIGUOUS. No latest timestamp/UUID, highest role, strongest enum or usable-only
   filter determines authority. Pair selection cannot prove novelty.
7. Current usability is timestamped separately. An unusable selected terminal is
   still selected history, with `usable_for_current_judgment=false`; never restore
   its predecessor. Multiple roots remain ambiguous even if only one is usable.
8. B22 does not change NoveltyAssessment admission; B19 owns the later
   positive-outcome amendment. All Phase 1 scientific hashes/support sets remain
   unchanged. Selection creates no downstream effects.

## 4. Proposed commands, DTOs and historical readback

Keep `NoveltyService.record_prior_art_relation` and its existing route/CLI name;
add optional `supersedes_prior_art_relation_id=None`. Omission/null retains the
existing root operation and v1 hash. A nonnull predecessor creates v2 material.
Exact UUID is the retry identity, separate from transport X-Request-ID.

Keep `read_prior_art_relation(ExactReadQuery)` and add the navigation/version
fields in §11.3, without redirecting an old ID to its successor. Add
`select_prior_art_relation(PriorArtSelectionQuery)` for a pair; it returns all
chain summaries, not a relation inferred from text or a caller-supplied root set.
Current project readers are OWNER, RESEARCHER, REVIEWER, VIEWER and APPROVER;
writers are OWNER/RESEARCHER, using the same verified-principal checks as B18.
Wrong project/source access is FORBIDDEN; nested evidence details require their
existing read entitlement. Do not return partially authorized selection results.

Proposed GET `/v1/projects/{project_id}/prior-art-relations/selection` takes
`claim_version_id` and `source_version_id` UUID query parameters; register this
static path before the existing `/{id}` route. Existing POST and exact GET stay
200, including replay. Selection returns 200 for EMPTY, UNIQUE and AMBIGUOUS;
ambiguity is explicit data, not an error. CLI adds
`literature select-prior-art-relation` with the same three IDs and JSON output.
Existing `record-prior-art-relation` gains the optional predecessor flag.

## 5. Schema and literal hash proposal — one forward migration; no new table

The migration adds `material_version SMALLINT NOT NULL DEFAULT 1`, nullable
`supersedes_prior_art_relation_id UUID`, and §12.1 constraints/indexes/guards on
`prior_art_relations`; it adds no table. Existing v1 rows and new roots serialize
exactly Hash R2 15's v1 template, with no extra null predecessor key.

The complete correction-only PriorArtRelation v2 payload and shared compatibility
amendment to frozen Hash Contract 15 are specified once in [ADR-0017](ADR-0017_Novelty_Material_v2_DRAFT.md),
Decision 1. This draft requests that decision; it does not approve it.

R/I notation, UUID-sorted evidence, NFC normalization and excluded metadata are
exactly R2 15. `sha256-cjson-v1` remains the encoding/hash scheme; material version
is distinct. Recompute predecessor content before embedding its hash; recursively
verify typed ancestry iteratively with a visited-ID set. Extend the closed HashRef
vocabulary with `PriorArtRelation`, not arbitrary type strings. The new row's
rationale explains its correction; no separate unbound correction-reason field.
Readback dispatches by stored material_version and rejects unknown values.
Selection is a derived snapshot projection with no persisted hash or pointer.

## 6. Error contract — existing categories

Use only the existing enum values and mappings pinned in §11.2. Do not invent
PRIOR_ART_AMBIGUOUS or HASH_MISMATCH transport codes. Hash/closure failure uses
PROVENANCE_CLOSURE_VIOLATION. Selection cannot suppress corrupt chains as EMPTY.
All failures roll back the new parent and evidence set together. Sanitized
INTERNAL_ERROR must disclose no SQL, credentials or inaccessible record details.

## 7. Transactions, concurrency and failure recovery

One Application command is one synchronous database transaction. New writes use
READ COMMITTED and the exact first-SHARE sequence in §12.2. Authorization uses
fresh `clock_timestamp()` after each blocking wait and before commit; force
constraints before the final check. No provider/network call occurs inside it.

Replay compares normalized caller material, including the nullable predecessor,
and the original created_by. Same UUID/different material is IDEMPOTENCY_CONFLICT;
different actor or lost read entitlement is FORBIDDEN. Exact saved replay requires
current read entitlement, not writer role or currently usable scientific inputs;
return historical material with current validity and navigation. Never re-execute
or append on replay, including after an uncertain commit. Normalize evidence ID
order before comparison. A later successor does not make exact replay conflict.

Use B18's three total fresh-UoW attempts only for SQLSTATE 40001/40P01, with no
delay. Do not retry predecessor uniqueness loss, business denials, lock/statement
timeouts or uncertain commits. A losing concurrent correction returns
CONCURRENT_MODIFICATION, while a predecessor already superseded when inspected
returns INVALID_STATE_TRANSITION. Unknown commit recovery is exact-ID read/replay.

Reads, including selection and exact-history reads, take one REPEATABLE READ
snapshot, no explicit table/advisory/row locks and no writes. They check current
read entitlement using advancing trusted time at entry and exit, as B18 does;
never claim that a later clock refreshes the database snapshot.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

Require independent golden vectors for unchanged v1 and correction v2; normal-role
SQL constraint tests; committed-parent and sealed-child tests; two-backend races
with observable blocking and database-clock expiry; all selection states and
history after restart. Specifically test a read while an unrelated actor INSERT
commits: neither exact reads nor selection may block that writer. Detailed files
and cases are §12.4. These are future obligations, not evidence of B22 execution.

## 9. Acceptance criteria and evidence boundary

Before implementation: owner disposition of §13, approved bounded ADR/compatibility
review for field/hash changes, matching architecture amendments and a separately
authorized execution pack. Those amendments are future work; do not edit them in
this documentation task. Resolve the actual Alembic head then; do not reuse 0047
or assume the next revision number.

Bounded acceptance needs passing focused checks, PostgreSQL 18.x migration,
constraint/race tests, preserved B18 behavior and no open P0/P1 findings. Record
commands, counts, skips and server version; no whole-phase acceptance follows.
The task's full-suite run belongs to the loop. Stop after this draft and its
focused verification; neither missing tests nor this document authorize code.

## 10. Glossary

| Term | Meaning |
| --- | --- |
| Pair | Exact ClaimVersion UUID plus exact SourceVersion UUID; never long-lived identities or merged aliases. |
| Root | Comparison with null predecessor; independent recorded judgment. |
| Correction | New immutable comparison whose typed FK names the previous terminal record. |
| Chain | One root and its nonforking successors for the same pair. |
| Terminal/head | Record with no successor in the read snapshot. |
| Selection | Deterministic navigation across all chains for one pair. |
| UNIQUE | Exactly one chain; its terminal ID is selected. |
| AMBIGUOUS | Multiple independent chains; no selected ID, even with agreeing judgments. |
| EMPTY | Authorized pair has no comparisons. Missing/inaccessible pair inputs still error. |
| Current usability | Existing B18 timestamped validity projection, distinct from immutable content and chain position. |
| Material version | Hash-payload schema version; distinct from hash scheme and Source/Claim version. |

## 11. Decisions taken in this draft

These are proposed choices awaiting owner approval, not claims of frozen authority.

### 11.1 Scope and policy decisions

Use existing relation/child storage and command; same-pair single-successor chains;
retain independent roots; return ambiguity rather than arbitrate. No author-only
correction restriction: any currently authorized writer may append, with their own
assessor attribution and evidence. A stale predecessor may be corrected using
currently admissible inputs. Use v1 for roots and v2 for corrections, with exact
historical replay preserved. Selection includes unusable heads and never falls
back. No pagination/truncation: §11.3's bounded selector fails explicitly rather
than quietly omit conflicting history.

### 11.2 Pinned error mappings

Mappings below match current [api/errors.py](../../src/researchbase/api/errors.py)
and [cli/errors.py](../../src/researchbase/cli/errors.py); no mapping change needed.

| Code | HTTP | CLI exit | B22 use |
| --- | ---: | ---: | --- |
| VALIDATION_ERROR | 422 | 2 | Closed DTO/type/enum/text/set bounds; selector limit exceeded. |
| AUTHENTICATION_REQUIRED | 401 | 3 | Missing verified principal. |
| FORBIDDEN | 403 | 3 | Credential/role/project/source access, different replay actor. |
| NOT_FOUND | 404 | 3 | Missing exact pair input, relation or predecessor after authorization. |
| FROZEN_REFERENCE_REQUIRED | 409 | 5 | New comparison input is not exact frozen material. |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Hash corruption, wrong predecessor pair, cycle, broken closure/unknown material version, unusable new inputs. |
| INVALID_STATE_TRANSITION | 409 | 4 | Known nonterminal predecessor or evidence not independently VERIFIED. |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Same request UUID, changed normalized inputs. |
| CONCURRENT_MODIFICATION | 409 | 4 | Concurrent successor/ID conflict, exhausted retry or normalized timeout. |
| IMMUTABLE_RECORD | 409 | 4 | Ordinary SQL attempts to mutate history/sealed evidence. |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Concrete FK failure. |
| INTERNAL_ERROR (fallback string) | 500 | 1 | Sanitized unexpected failure; novelty uses `invoke`'s exit-1 fallback. |

Named new checks/guards map as §12.1 specifies. Preserve inherited errors from
existing closure validators and their existing mappings; never remap them by text.

### 11.3 DTO fields, Python types and limits

Frozen, slotted, closed dataclasses; API forbids extras. Python UUID fields require
`type(x) is UUID`; transport accepts canonical lowercase hyphenated UUID text.
No caller actor, timestamp, hash, material_version or validity fields.

| DTO | Complete fields / bounds |
| --- | --- |
| RecordPriorArtRelationCommand | Existing `id`, `project_id`, `claim_version_id`, `source_version_id`: UUID; `relation: PriorArtKind`; `rationale: str`; `literature_evidence_ids: tuple[UUID, ...]`; add `supersedes_prior_art_relation_id: UUID \| None = None`. |
| ExactReadQuery | Existing `project_id: UUID`, `id: UUID`. |
| PriorArtSelectionQuery | `project_id: UUID`, `claim_version_id: UUID`, `source_version_id: UUID`. No caller root IDs or ordering. |
| PriorArtReadback additions | Preserve every existing field/type; add `material_version: Literal[1,2]`, `supersedes_prior_art_relation: HashRef \| None`, `superseded_by_prior_art_relation_id: UUID \| None`. No nested recursive DTO. |
| PriorArtChainHead | `root_id: UUID`, `terminal: HashRef` (literal type PriorArtRelation), `current_validity: CurrentValidity`. |
| PriorArtSelectionReadback | `project_id: UUID`, `claim_version_id: UUID`, `source_version_id: UUID`, `observed_at: datetime`, `state: PriorArtSelectionState`, `chains: tuple[PriorArtChainHead, ...]`, `selected_prior_art_relation_id: UUID \| None`. |

`PriorArtKind` remains exactly IDENTICAL, HIGHLY_SIMILAR, PARTIAL_OVERLAP, RELATED,
CONTRASTING, UNCLEAR. New `PriorArtSelectionState` is EMPTY, UNIQUE, AMBIGUOUS.
Rationale uses existing `narrative`: NFC, 1..16,384 characters, nonblank, valid UTF-8,
no NUL, meaningful whitespace preserved. Evidence uses `uuid_set`: 1..100 unique
UUIDs, UUID-sorted; reject duplicates rather than deduplicate. HashRef is type/id/
64-lowercase-hex content_hash, with the PriorArtRelation literal specified in §5 and ADR-0017. Existing
CurrentValidity fields/types/warnings stay unchanged; all datetimes are aware UTC.

Selector inspects at most 10,000 pair records (fetch 10,001 to detect overflow),
validates every chain and sorts summaries by root UUID. Overflow returns
VALIDATION_ERROR with a sanitized limit message and **no partial selection**;
exact-ID reads/correction writes remain available. This is a proposed read bound,
not a new persisted cap or a license to stop chain verification. EMPTY has zero
chains/null selected ID; UNIQUE has one chain and its terminal ID; AMBIGUOUS has
at least two chains/null selected ID. `observed_at` is trusted DB time for this
snapshot's projections, not a durable as-of token or commit timestamp.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

This migration owns only prior-art additions and retains any installed B21
coverage guards; it never replaces the shared parent guard. B19 must follow it.
Only additive columns/constraints/index on the existing table; sketch to implement
in a new migration after the then-current head, never edit 0047:

```sql
ALTER TABLE prior_art_relations
  ADD COLUMN material_version SMALLINT NOT NULL DEFAULT 1,
  ADD COLUMN supersedes_prior_art_relation_id UUID NULL,
  ADD CONSTRAINT uq_b22_prior_art_pair UNIQUE
    (id, claim_version_id, source_version_id),
  ADD CONSTRAINT ck_b22_prior_art_material CHECK (
    (material_version = 1 AND supersedes_prior_art_relation_id IS NULL) OR
    (material_version = 2 AND supersedes_prior_art_relation_id IS NOT NULL)),
  ADD CONSTRAINT ck_b22_prior_art_not_self CHECK (
    supersedes_prior_art_relation_id IS NULL OR
    supersedes_prior_art_relation_id <> id),
  ADD CONSTRAINT fk_b22_prior_art_predecessor FOREIGN KEY
    (supersedes_prior_art_relation_id, claim_version_id, source_version_id)
    REFERENCES prior_art_relations (id, claim_version_id, source_version_id)
    ON DELETE RESTRICT;
CREATE UNIQUE INDEX uq_b22_prior_art_predecessor
  ON prior_art_relations (supersedes_prior_art_relation_id)
  WHERE supersedes_prior_art_relation_id IS NOT NULL;
CREATE INDEX ix_b22_prior_art_pair
  ON prior_art_relations (claim_version_id, source_version_id, id);

CREATE CONSTRAINT TRIGGER b22_complete_correction
  AFTER INSERT ON prior_art_relations
  DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
  EXECUTE FUNCTION b22_validate_correction();
```

`b22_validate_correction() RETURNS trigger`, PL/pgSQL, pinned
`search_path = pg_catalog, public, pg_temp`, validates the same pair and acyclic
ancestry; every nonnull predecessor must have been committed before this
transaction. Use 0047's existing `xmin::text::bigint` versus
`pg_current_xact_id()::text::bigint` pattern to reject same-transaction parents;
reject unresolved ancestors and visited IDs. This plus immutable parents prevents
cycles and multiple links created in one transaction. No FK deferral permitting
future predecessors. Retain all 0047 immutable/sealed-child/nonempty-set guards.

Add BEFORE INSERT trigger `b22_prior_art_prelocked` using function
`b22_require_prelocked() RETURNS trigger` with the same pinned search_path. Require
0047's actual N SHARE-lock/isolation predicate `pr218_capture_prelocked()` for
**prior-art INSERTs**, before the existing parent guard runs. Both triggers remain
safe in either alphabetical order: this new guard never acquires locks itself.
Application ordering, separately tested, ensures the lock was the first statement;
pg_locks alone cannot prove statement history. Other B18 tables are unchanged.

New trigger denials use existing SQLSTATE P17D3 (closure violation); immutable
history keeps P17D1. Map `ck_b22_prior_art_material`, `ck_b22_prior_art_not_self`
and `fk_b22_prior_art_predecessor` to PROVENANCE_CLOSURE_VIOLATION;
`uq_b22_prior_art_predecessor` to nonretryable CONCURRENT_MODIFICATION.
Normalize SQLSTATE 55P03/57014 to nonretryable CONCURRENT_MODIFICATION in the
scoped novelty handler. Other FK errors retain REFERENTIAL_INTEGRITY_ERROR.
Application missing-predecessor
checks return NOT_FOUND before insertion. Existing parent PK/replay race handling
remains B18's. Do not normalize every 23505 as a correction race.

Upgrade preserves populated v1 rows and digests without UPDATE. Downgrade takes
ACCESS EXCLUSIVE on prior_art_relations and prior_art_evidence_inputs in that
order, refuses any v2/non-null predecessor row, then drops only B22 objects;
old v1 history may remain. Test both populated paths; no scientific CASCADE.

### 12.2 Exact lock order and transactions

**N** is exactly the literal ordered tuple `N` in
`src/researchbase/persistence/novelty_repository.py`: from actor_subject_bindings
through source_versions, including authority, validity and capture-input tables.
Reuse that inventory unchanged; do not add prior_art_relations or its child table
to N (SHARE plus INSERT upgrades there would deadlock). Current N and
`pr218_capture_prelocked()` must continue to agree.

| Operation | Exact ordered steps |
| --- | --- |
| record_prior_art_relation, root or correction, including replay | Validate principal/DTO shape in memory. Open fresh synchronous READ COMMITTED UoW via connection isolation option. FIRST transaction SQL: single `LOCK TABLE <N in existing tuple order> IN SHARE MODE`. No SELECT, SET LOCAL, advisory or row lock first. Then SET LOCAL lock_timeout='10s'; SET LOCAL statement_timeout='30s'. Acquire `pg_advisory_xact_lock(hashtextextended(:key,0))`, key `pr218:prior_art:<canonical command id>`. Lock exact ClaimVersion FOR UPDATE. Fresh-clock current read authorization; read existing request for replay before writer/new-input admission. For a new correction, authorize writer, lock predecessor `prior_art_relations WHERE id=:id FOR UPDATE`; reread its successor after that wait. Check same pair, committed ancestry and historical hashes. Read new source/evidence in UUID order with no extra FOR UPDATE, under N; verify new material/closure/current usability. Fresh-clock writer authorization; INSERT parent then UUID-sorted child rows. `SET CONSTRAINTS ALL IMMEDIATE`; build/verify exact readback; final fresh-clock authorization; commit. Repeat final authorization if any subsequent blocking wait occurs. |
| read_prior_art_relation | Fresh `begin_formal_read()` REPEATABLE READ UoW; authorize current reader, read exact parent/UUID-sorted evidence, typed ancestry/hashes and successor navigation; derive current validity; final clock/read authorization; return. No lock helpers. |
| select_prior_art_relation | Same read UoW/authorization; verify pair existence/ownership and source access, plain SELECT pair records ORDER BY id LIMIT 10001; enforce bound, read exact evidence and ancestry in this snapshot; verify hashes/graph and derive every root/head. Return state and terminal projections after final clock/read authorization. No table, advisory or row locks, writes, constraint forcing or retry that creates records. |

One request advisory namespace only. Claim coordination precedes predecessor row
coordination. No project/source row lock or separate pair advisory lock is added.
Independent roots created by B18 serialize on the same Claim lock but remain
independent. Unique predecessor enforcement is the final normal-SQL race backstop.
N's SHARE locks stabilize mutable authorization/validity; READ COMMITTED rereads
after waits. The first SHARE wait precedes transaction-local timeouts, exactly as
in current B18; do not promise these later SET statements bound that initial wait.

### 12.3 Ordered build steps and module paths

1. Approve ADR and field/hash amendments; inspect `uv run alembic heads`. Add the
   additive migration under `migrations/versions/` with the actual new revision
   and parent. No table or architecture source change is authorized now.
2. Extend `src/researchbase/domain/novelty.py`: closed selection enum, one new
   HashRef literal, pure version-dispatched material builders and graph validation.
   Keep existing v1 builder output identical and add independent v2 vectors.
3. Extend `src/researchbase/application/novelty.py` DTOs/service and the typed
   NoveltyRepository port in `src/researchbase/application/ports.py`. Implement
   correction/replay admission and snapshot selection; use existing saved-provenance
   error handling. Do not require current usability to verify saved predecessors.
4. Extend `src/researchbase/persistence/novelty_repository.py` with typed predecessor,
   successor and bounded pair queries. Reuse `prepare('prior_art', ...)` unchanged
   before adding predecessor locks; do not make read methods call prepare.
   Extend named normalizations in `src/researchbase/persistence/uow.py`; keep
   existing wiring and SQLSTATE-only retry eligibility.
5. Extend closed requests/responses/routes in `src/researchbase/api/routes.py` and
   commands in `src/researchbase/cli/commands/literature.py`; reuse current service
   composition (`api/app.py`, `cli/composition.py`), verified principals, shared
   envelopes and novelty's CLI exit-1 fallback. Preserve existing paths/flags.
6. Add §12.4 tests and update additive inventories only as required. Run focused
   tests and applicable inherited PostgreSQL regressions; record exact results,
   obtain review, stop. No downstream novelty behavior follows automatically.

### 12.4 Test artifacts and required cases

Reuse `tests/integration/phase2/pr2_18_fixtures.py` and the existing disposable
`phase2_database_url`; real PostgreSQL 18.x, normal-role SQL, two independent
backend PIDs for races. Proposed new files are explicitly future artifacts.

| File | Required cases |
| --- | --- |
| `tests/unit/phase2/test_b22_prior_art_contract.py` (new) | Closed fields, UUID/enum strictness, null default, text/evidence boundaries, duplicates, normalized replay, state/count/null invariants, cross-pair graph and cycles, 10,000/10,001 bound. |
| `tests/unit/phase2/test_b22_prior_art_hash_vectors.py` (new) | Independent literal v1/v2 JSON/digests; v1 byte equality, evidence permutation, changed predecessor/hash/actor/rationale inequality, unknown version fail-closed. |
| `tests/integration/phase2/test_b22_prior_art_correction.py` (new) | Root→correction→correction, own assessor, stale predecessor with admissible new inputs, old exact reads/replay after succession/restart, changed predecessor replay conflict, no role/current-invalidity requirement for saved replay, lost read entitlement, atomic parent/child failure, unusable new inputs deny. |
| `tests/integration/phase2/test_b22_prior_art_selection.py` (new) | EMPTY/UNIQUE/AMBIGUOUS; agreeing independent roots, timestamp/UUID/role changes do not arbitrate, invalid terminal no fallback, wrong Claim/Source versions, inaccessible source/project and corrupt history fail closed, pair bound with no truncation, one snapshot across concurrent root/correction commits. |
| `tests/integration/phase2/test_b22_prior_art_schema.py` (new) | Exact types/names/indexes/triggers; populated v1 upgrade preserves hashes, v2 downgrade refusal/v1 downgrade preservation; normal-role no-prelock INSERT, same-transaction predecessor, cross-pair/self/fork/cycle, mutation/late evidence, empty evidence, FK RESTRICT and forced-deferred rollback. |
| `tests/integration/phase2/test_b22_prior_art_concurrency.py` (new) | First SQL and lock order evidence; two corrections one winner; same UUID one parent/child set; revocation and scheduled expiry across request/Claim/predecessor/deferred waits; 40001/40P01 three attempts, no business/timeout retry, uncertain commit exact recovery; exact/selection reads do not block unrelated writes. |
| `tests/unit/phase2/test_b22_prior_art_transports.py` (new) | Every §11.2 mapping, extras/UUIDs, static route precedence, 200 replay/selection states, nullable fields, CLI optional predecessor, sanitized fallback, trusted principal and no partial disclosure. |
| `tests/architecture/test_b22_prior_art_boundaries.py` (new) | No extra semantic table/persistence mechanism, no explicit locks in read paths, Application-only writes, unchanged Phase 1/B18 v1 hash contracts and INCONCLUSIVE guard, no governance/publication/support effects. |

Future focused commands: `uv run pytest tests/unit/phase2/test_b22_*.py
 tests/architecture/test_b22_*.py` and `uv run pytest
 tests/integration/phase2/test_b22_*.py` (join each wrapped command on one line).
Preserve and run `uv run pytest tests/integration/phase2/test_pr2_18_*.py` and
`uv run pytest tests/integration/phase2/test_pr2_19_novelty.py
 tests/integration/phase2/test_pr2_20_novelty.py`, plus
`uv run pytest tests/unit tests/architecture tests/test_architecture.py`,
`uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright` and
`git diff --check`. The whole-suite check is reserved for the loop.

### 12.5 Not in this slice

No cross-root adjudication/merge, cross-source alias selection, bulk replacement,
mutable selected/current pointer, whole-Claim novelty aggregation, stronger
NoveltyAssessment outcomes, assessment-to-comparison basis, automatic impact
propagation, Review/Decision/Approval/RevisionAction target/result expansion,
Claim support changes, publication/package attachment, first-ever priority,
external effects or Agent runtime. Each requires its own approved contract.

## 13. Open questions for the owner — override register

| Owner disposition required | Proposed answer fixed in this draft |
| --- | --- |
| How should conflicting independent roots resolve? | Report AMBIGUOUS; no automatic arbitration. Cross-root resolution is separate scope. |
| Who may correct whose comparison? | Any active OWNER/RESEARCHER with B18 admission; retain distinct attribution, never imply adjudication. |
| Approve [ADR-0017](ADR-0017_Novelty_Material_v2_DRAFT.md) field/hash compatibility amendment? | Add same-pair typed predecessor and explicit v2 material; preserve v1 roots and all historical digests. Require ADR-0017 Decisions 1–3 before implementation. |
| Accept bounded selector? | 10,000 pair records; explicit failure above bound, never partial authority. |

Any override requires body/schema/hash/test-plan updates before approval. No owner
approval or implementation authorization is inferred from the backlog entry.

## 14. Documentation verification note

Current coordinated verification and its environment limitations are recorded once
in [B19 §14](B19_Close_Prior_Art_Basis_Contract_DRAFT.md#14-documentation-verification-note).
No proposed migration or PostgreSQL guard behavior is verified by documentation
checks. No implementation, acceptance gate or Phase exit is claimed.
