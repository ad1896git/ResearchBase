# ADR-0017 — Novelty material v2 and typed capture membership

Status: ACCEPTED — APPROVED by owner 2026-10-18 (including B19-AQ-01 and B21-AQ-01); slices B19, B21, B22 authorized for implementation.

## Context

[B19](../../proposals/B19_Close_Prior_Art_Basis_Contract_DRAFT.md),
[B21](../../proposals/B21_Unresolved_Count_Capture_Contract_DRAFT.md) and
[B22](../../proposals/B22_PriorArt_Correction_Selection_Contract_DRAFT.md) each amend one PR2-18
material type fixed at version 1 in frozen
[Hash Contract 15](../15_Phase2_Hash_Payload_Contract_R2_v1.0.md).
Respectively, v1 cannot bind a positive assessment's comparison basis, reconstruct
historical unresolved-result membership, or bind a comparison's correction parent.
New fields cannot silently enter v1 bytes. Architecture 12/13 do not register
B21's proposed membership relation; AGENTS.md §4 requires proof that existing
patterns cannot express the missing fact before admitting schema.

Following [ADR-0015](ADR-0015-b07-revision-decisions-concern-carry-forward.md)
and [ADR-0016](ADR-0016-b08-issue-disposition.md), this single
additive ADR requests field/registry and hash-contract admission without editing
frozen numbered architecture. It remains in `docs/proposals/`; only the owner
moves it into architecture on approval. No approval or execution authorization
is inferred from this proposal.

## Decision

### 1. One versioned amendment to Hash Contract 15

Propose the following **entire** v2 payloads. R(T), I(T), NFC, null handling,
UUID encoding and canonical-json-v1/SHA-256 are exactly Contract 15. Tokens are
notation, never strings embedded in actual material; each R/I token expands to
its concrete reference object; each `0` in a JSON integer count field is a typed
placeholder, not a mandated count. No byte-exact literal vector, canonical bytes
or expected digest is provided here: these templates are not hash fixtures.
Persist `hash_scheme = sha256-cjson-v1`; material version does not change it.

**NoveltyAssessment — B19; `novelty_assessments`:**

```json
{"type":"NoveltyAssessment","material_version":2,"claim_version":"<R(ClaimVersion)>","search_coverage":"<R(SearchCoverage)>","assessment":"CLOSE_PRIOR_ART_FOUND","limitations":"<string>","supersedes_assessment":"<R(NoveltyAssessment)|null>","assessed_by":"<I(ActorIdentity)>","scope_statement":"<string>","closeness_criteria":{"statements":["<string>"]},"prior_art_basis":[{"prior_art_relation":"<R(PriorArtRelation)>","search_result_resolution":"<R(SearchResultResolution)>"}]}
```

Only CLOSE_PRIOR_ART_FOUND uses v2; INCONCLUSIVE stays v1 and NO_CLOSE remains
denied. Basis has 1..100 distinct relations sorted by relation UUID, with one
exact resolution witness each; shared witnesses across relations are allowed.
Each relation binds its full sealed evidence set. Criteria retain authored order,
1..100 nonblank NFC statements, total at most 16,384 characters; their storage is
`closeness_criteria TEXT[]`, mapped to exactly the closed `statements` hash value.
Criteria are authored explanatory narrative, not a machine-evaluated rule language:
no statement controls input selection, enum interpretation, admission or validity.
Those semantics come only from the closed outcome/PriorArtKind enums, exact typed
basis/witness FKs and B19 §3's deterministic checks. Criteria never establish
closeness without an admitted IDENTICAL/HIGHLY_SIMILAR basis. The choice of a
bounded narrative column over typed criterion rows is justified in Alternatives.
Add nullable `scope_statement TEXT` and criteria plus `material_version SMALLINT
NOT NULL DEFAULT 1`. B19 §12.1 proposes one literature-owned immutable typed
`novelty_assessment_prior_art_inputs` relation with assessment, relation and
resolution RESTRICT FKs, unique (assessment, relation), actor/time attribution,
same-transaction sealing and deferred completeness. Existing evidence children
already bind evidence; no second evidence owner or criteria table is needed.

**SearchCoverage — B21; `search_coverage`:**

```json
{"type":"SearchCoverage","material_version":2,"search_plan_version":"<R(LiteratureSearchPlanVersion)>","search_execution":["<I(LiteratureSearchExecution)>"],"providers":["<string>"],"query_count":0,"result_count":0,"resolved_source_count":0,"time_scope":"<time-range|null>","coverage_limitations":"<string>","captured_unresolved_result_count":0,"captured_results":[{"search_result_record":"<I(SearchResultRecord)>","resolutions":["<R(SearchResultResolution)>"]}]}
```

Execution IDs sort by UUID, provider strings lexically. Captured results sort by
result UUID; resolutions within each result sort by resolution UUID. Reject
duplicate members. Empty result membership is `[]`; a result with no resolution
has `resolutions: []`. I(SearchResultRecord) uses its immutable ID without a new
content hash. R(SearchResultResolution) uses the unchanged M2/B01 digest; verify
its exact source/version tuple with the existing verifier. A result is resolved
iff its captured resolutions are nonempty, all name a nonnull exact version and
all agree on one (source, version) pair. Count unresolved results, not sources;
zero results means zero unresolved. Time scope retains Contract 15's closed form.
The two added keys are mandatory for v2. Add `material_version SMALLINT` and
nullable `captured_unresolved_result_count INT`; upgrade old rows as v1/null,
then set default version 2 and require v2 for new captures. Decision 2 governs
membership storage separately; result membership reuses the existing terminal
execution seals, while one new relation saves resolution membership.

**PriorArtRelation — B22; `prior_art_relations`:**

```json
{"type":"PriorArtRelation","material_version":2,"claim_version":"<R(ClaimVersion)>","source_version":"<R(SourceVersion)>","relation":"<PriorArtKind>","rationale":"<NFC string>","literature_evidence":["<R(LiteratureEvidence)>"],"assessed_by":"<I(ActorIdentity)>","supersedes_prior_art_relation":"<R(PriorArtRelation)>"}
```

Only corrections use v2; roots remain v1. Evidence refs sort by UUID with no
duplicates. Add `material_version SMALLINT NOT NULL DEFAULT 1` and nullable
`supersedes_prior_art_relation_id UUID`; same-Claim/Source composite RESTRICT FK,
unique predecessor and acyclic committed ancestry enforce one successor. Verify
predecessors using their saved material version before embedding the exact hash.
The six PriorArtKind values and attributed, independently verified admission
remain as B18; correction is not adjudication of independent roots.

**Compatibility and exclusions:** existing rows' scientific material and hashes
stay byte-identical. Label them v1 without rewriting/recomputing digests or
backfilling membership from current rows/timestamps. Readers accept both 1 and 2
for all three types, dispatching on each referenced row's saved version, including
mixed-version coverage/basis/predecessor chains. Unknown versions fail closed.
Replay uses the stored version and never upgrades the same UUID. V1 payloads
retain exactly their original keys, including original nulls; no new null fields
are appended. V1 coverage reports historical unresolved count as unknown/null.

Roll out each migration and its dual readers before enabling its v2 writers;
old readers are unsupported for v2. New hashes bind saved input membership only,
never current validity, supersession navigation, observation times, child IDs,
row IDs, scheme or extra metadata. Claim/support, evidence and resolution hashes
remain unchanged. Legitimate later invalidity changes only current projections.
Each downgrade refuses its populated v2/new-child history; never delete or rehash
scientific records to permit rollback.

### 2. Architecture Question B21-AQ-01 — admit one capture relation?

**Existing representation first:** Architecture 13 already provides
`search_coverage_executions`, immutable `search_result_records` (query → execution)
and append-only `search_result_resolutions` (result → source/version). Reuse their
facts and existing hashes. They do not record which subset of resolutions was
visible to a particular coverage. For the same result R, C1 sees {}, C2 sees {A}
after resolution A commits, and later B makes the current set {A,B}. A captured
membership hash alone verifies a known set but cannot enumerate C1/C2's saved
IDs. Execution membership is identical; neither timestamps nor current rows
recover transaction visibility, and a hash preimage search is not a reader.

**Ordering-key alternative and evidence:** timestamps are not transaction
visibility. [PostgreSQL 18, Read Committed](https://www.postgresql.org/docs/18/transaction-iso.html#XACT-READ-COMMITTED)
says a SELECT “sees only data committed before the query began”.
[Date/time functions](https://www.postgresql.org/docs/18/functions-datetime.html#FUNCTIONS-DATETIME-CURRENT)
describe transaction timestamps as “the start time of the current transaction”;
clock timestamps measure evaluation time, not commit visibility. In this repository,
[migration 0029](../../../migrations/versions/0029_metadata_observations.py) defines
`search_result_resolutions.resolved_at TIMESTAMPTZ NOT NULL`, with no `created_at`,
commit marker or sequence. The [repository](../../../src/researchbase/persistence/metadata_observation_repository.py)
inserts `:resolved_at` and sorts `ORDER BY resolved_at,id`; sorting is not capture
membership. There is no existing ordering key with the required guarantee.

For example, resolver T obtains time t1 before waiting to INSERT behind capture C's
SHARE lock. C captures an empty resolution history at t2 > t1 and commits. T then
inserts/commits A with t1. A later `resolved_at <= t2` query incorrectly includes A.
Conversely, capture's transaction-start time may precede a resolver that commits
before capture acquires SHARE, so a timestamp cutoff can exclude a visible row.
The locks stabilize the captured set, but do not make these stored times commit
markers. These schedules are deductions from the documented visibility and lock
protocol, not executed race evidence in this documentation task. **Owner to confirm:**
the claim that timestamps cannot recover capture membership is unverified until the
B21 race tests run on PostgreSQL.

A bare new monotonic sequence is also insufficient: allocating n before a wait
and committing after capture's n+1 still produces a false prefix. PostgreSQL's
[isolation documentation](https://www.postgresql.org/docs/18/transaction-iso.html)
notes sequence changes “are immediately visible to all other transactions”,
independently of the row transaction's commit or abort. A *new* durable ordering
protocol could work if every resolution writer allocated its key only inside a
common serialization gate held through commit, and coverage saved a boundary in
that same order. That is not an existing column/pattern: it requires new
writer/normal-SQL guards and a compatibility rule for unmarked rows. Reject that
wider cross-owner protocol in favor of explicit typed captured membership; do
not claim ordering is impossible.

**One typed spanning-row alternative — sufficient with existing seals:**
[migration 0024](../../../migrations/versions/0024_literature_search_execution.py),
`pr204_reject_terminal_child()` / `pr204_reject_terminal_result()` and their query/
result INSERT triggers forbid adding provenance to a terminal execution; existing
query/result UPDATE/DELETE guards retain the rows. Coverage already requires
terminal executions and seals its `search_coverage_executions`. Therefore the
result set is recoverable after restart by coverage → execution → query → result,
including results with no resolution. It does not need a second membership table
or a NULL resolution sentinel. A typed (coverage, result, resolution) row suffices
for each captured resolution; the result ID can be derived from its immutable
resolution FK, so persist only (coverage, resolution, verified resolution hash).
This is one new relation that reuses existing result/resolution rows and seals;
the earlier two-table proposal is rejected as redundant.

An added coverage FK on an existing result/resolution would rewrite immutable
rows and cannot represent one row in many captures. Existing Assessment/Relation
fields target other owners and cannot store coverage → result → resolution.
An ArtifactVersion manifest, Snapshot or generic Event without concrete membership
FKs would move primary-chain references into a JSON/blob/locator store and add
a competing persistence boundary. Reuse the sealed Relation pattern instead.

**Proposed separate decision:** admit one literature-owned immutable child
relation as an additive Registry 03 / Architecture 12 / Field Contract 13 entry,
subject to owner approval of B21 §12.1's exact DDL and guards:

- `search_coverage_resolutions`: UUID primary key; trusted created_at and
  created_by actor RESTRICT FK; `search_coverage_id` coverage RESTRICT FK;
  `search_result_resolution_id` resolution RESTRICT FK; verified
  `resolution_content_hash CHAR(64)`; unique (coverage, resolution). Guard joins
  resolution → result → query → execution to require membership in the coverage's
  exact saved execution set. Coverage is indexed by the unique pair; actor and
  resolution FKs have their own indexes. No source/version facts are duplicated.

Insert children only in their new coverage parent's transaction with identical
actor/time; forbid UPDATE/DELETE/late INSERT. Deferred bidirectional set checks
under existing N SHARE locks require every visible resolution of every result in
the sealed execution set, exact tuples and correct counts. Parent trigger catches
omitted children. After restart reconstruct the immutable result set through
execution seals and group only saved resolution refs by their immutable result
FK. Results with no saved resolution produce an empty array; later resolutions
are excluded even if their timestamps precede capture. Zero results yields an
empty result array. Both cases are distinguished from unknown v1 by version.

No existing relation stores this historical coverage/resolution subset; a hash
alone cannot enumerate it. One new typed relation is sufficient; a second result
relation, result-copying, generic JSON or new persistence infrastructure is not
admitted. This is a requested architecture exception, not an assertion that frozen
12/13 already register the coverage/resolution relation.

### 2b. Architecture Question B19-AQ-01 — admit one assessment basis relation?

B19 needs `novelty_assessment_prior_art_inputs`, the immutable typed membership of a
CLOSE_PRIOR_ART_FOUND assessment in its exact PriorArtRelations. Architecture 13 row 70
registers `novelty_assessments` but no basis relation, and a hash alone cannot enumerate
the members. Like B21-AQ-01, this is one bounded typed relation (concrete RESTRICT FKs,
sealed at creation, no JSON reference list), proposed for explicit owner admission.

### 3. Cross-draft order and migration composition

After approval and separate execution authorization, B22 must land before B19;
B21 is independent and may land before, between or after them. Each owns one
forward revision at the actual linear Alembic head, with B19 descending from B22.
The guard ownership contract is additive; **none of these migrations replaces
`pr218_parent_guard()` or another `pr218_*` function**. Migration 0047 remains
the owner of the shared parent/chain/completeness/prelock functions (with accepted
0057 seal corrections retained). Future implementations must fail preflight on
an unexpected baseline definition rather than overwrite it.

| Migration owner | New functions / trigger attachments it alone owns |
| --- | --- |
| B19 | `b19_require_prelocked()` via BEFORE INSERT `trg_b19_novelty_prelocked` on novelty_assessments; `b19_valid_criteria(TEXT[])`; `b19_basis_insert_guard()` via `trg_b19_basis_insert`; `b19_complete_basis()` via the parent/basis constraint triggers in B19 §12.1. Immutable children reuse `pr218_immutable()` unchanged. |
| B21 | `b21_require_capture_version()` via `trg_b21_capture_version_guard`; `b21_guard_resolution_insert()` via its membership INSERT trigger; `b21_capture_complete()` via its three constraint triggers. Immutable children reuse `pr218_immutable()` unchanged. No assessment or prior-art trigger/function is touched. |
| B22 | `b22_require_prelocked()` via BEFORE INSERT `b22_prior_art_prelocked`; `b22_validate_correction()` via constraint trigger `b22_complete_correction`. No coverage or assessment trigger/function is touched. |

Each BEFORE trigger returns NEW and adds only its own denial checks. In particular,
B19's prelock trigger checks `pr218_capture_prelocked()` and raises P17D3 without
acquiring locks; it runs before both existing `trg_pr218_novelty_chain` and
`trg_pr218_novelty_assessments_parent_guard`. B22's prelock trigger likewise precedes
`trg_pr218_prior_art_relations_parent_guard`. These fixed names use PostgreSQL's
[alphabetical order for same-kind triggers](https://www.postgresql.org/docs/18/sql-createtrigger.html).
Thus normal-role INSERT cannot reach the old parent function's Claim/table-lock
path before proving N is already held. The parent's retained checks and redundant
acquisition of already-held N remain unchanged. B21 adds its own capture-version
check; the baseline coverage parent already requires preheld N. No sibling's
clause is copied into or removed from a shared function.

Later migrations extend admission by attaching their own triggers, never by
replacing a sibling function. Downgrade first refuses owned v2/child history,
then drops only owned triggers/functions/columns/constraints; B19 also restores
only the original INCONCLUSIVE CHECK it removed. Linear Alembic downgrade must
remove B19 before B22 because B19's terminal check depends on B22's column.
B21 has no sibling-column dependency and leaves all B19/B22 definitions intact.

New B19 close-art admission accepts only non-superseded B22 terminals, using the
shared exact ClaimVersion FOR UPDATE serialization and a successor reread after
waiting. Deferred SQL admission enforces the same rule. Independent roots remain
explicit selected basis, not a claim of UNIQUE pair authority. A later correction
never redirects or rehashes the saved assessment; it makes that basis unusable
for current judgment while historical structure/hash remain verifiable. B19 accepts
v1/v2 coverage; B21 does not require stronger novelty admission. Exact reads remain
one lock-free read-only REPEATABLE READ snapshot; no new explicit table lock on
insert destinations is introduced.

## Consequences

All three changes share one explicit material amendment and keep frozen history
verifiable. B19 uses a typed criteria column and one sealed input relation; B21
requires separate schema admission for one sealed membership relation; B22 adds
no table. Migration, normal-role guards, independent literal vectors, mixed-version
reads/replay, array validation, downgrade refusal and B19/B22 race tests are required
by the respective drafts. The following are proposed orders requiring future
PostgreSQL verification, **not verified orders or an independence test result**:
B21 → B22 → B19, B22 → B21 → B19, and B22 → B19 → B21, preserving sibling
guards and saved v1 digests in each. Current baseline test results cannot prove proposed
behavior. Approval of this ADR is neither implementation authorization nor a
Phase 2 gate result.

## Alternatives

- Silently add keys to v1 or rehash old records: breaks frozen references.
- Three independent ADR/version decisions: risks incompatible nested readers and
  duplicate ownership of the same frozen hash amendment.
- JSONB criteria as semantic storage: rejected. The selected TEXT[] is a bounded,
  ordered narrative column, with no keys, discriminator, references or executable
  predicates. It does not claim to implement a closed scientific criteria vocabulary.
  A closed enum would need an approved discipline-specific taxonomy that these
  drafts do not define, and would make an existential attributed comparison depend
  on a newly invented formal rule language. Typed criterion child rows such as
  `(assessment_id, ordinal, statement)` following Assessment/Relation are possible,
  but without such a taxonomy they store the same narrative and add row identities,
  ordering/sealing guards and a second child table without strengthening admission.
  Existing `novelty_assessment_prior_art_inputs` already supplies the typed semantic
  core: exact comparison and resolution references, closed comparison kind and
  deterministic evidence admission. Keep criteria explanatory, validate their
  bounds/order and hash them, and require a separate approved vocabulary/version
  amendment before interpreting narrative as formal criteria. This is the explicit
  requested exception/justification for a narrative column, subject to owner review.
- Count-only or membership-hash-only capture: cannot reconstruct saved inputs or
  validate all-row resolution ambiguity after restart; see B21-AQ-01 above.
- Mutable current pointers, latest-wins selection or automatic predecessor
  substitution: rewrites scientific meaning and hides competing roots.
