# B21 Historical Unresolved-count Capture Contract — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

## Start here (for the implementer)

B21 preserves which search results and resolution records were inspected when
SearchCoverage was created. New captures can then report an exact historical
unresolved-result count after restart. Existing captures retain an unknown count.
Current diagnostics remain a separate, timestamped projection.

After owner approval of the material amendment and separate execution authorization:

1. Confirm the actual migration head and approve the bounded amendment to Field
   Contract 13 and Hash Contract 15 (§§1, 5). This proposal does not override them.
2. Add two typed membership relations and version/count columns on the existing
   assessment, with sealed children and deferred completeness guards (§12.1).
3. Add version-dispatched material verification, capture and readback in the
   existing novelty modules; keep commands and caller inputs unchanged (§12.3).
4. Follow the existing first-statement SHARE protocol for writes; use one read-only
   REPEATABLE READ snapshot without explicit locks for reads (§12.2).
5. Prove legacy hashes, saved membership, replay, restart and both resolution-race
   orders; record exact focused checks and stop (§§9, 12.4).

The five review rules:

1. Never infer the historical count from current rows, timestamps or source counts.
2. Capture every result and every then-visible resolution, including empty histories.
3. Preserve version-1 bytes and all existing downstream references.
4. Capture and seal membership in the same transaction as the coverage parent.
5. Keep unknown legacy history explicit; capture is neither screening nor novelty proof.

**Scope:** documentation proposal only. No execution pack, migration, canonical
architecture amendment or acceptance gate is authorized by this draft. B18 and
B01 are implemented dependencies; B21 does not reopen their product scope.

## 1. Purpose, authority and inspected baseline

Read in AGENTS.md order: Architecture [01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md)
§3 (one owner, immutable history); Addendum [02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md);
Registry [03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md)
(SearchCoverage is an immutable literature assessment); Compatibility
[08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md)
(exact references and additive compatibility); Phase 2
[05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), PR2-18;
[Harness §2](../harness/09_Harness_Integration_Specification_v1.0.md).
Correction [12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md)
§§2–3, Field Contract [13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md)
row 69 and Hash Contract [15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md)
§2 currently specify version 1 without historical resolution membership.
Temporal [19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md)
requires advancing authorization time after waits.

| Current source | Evidence carried into this proposal |
| --- | --- |
| [domain/novelty.py](../../src/researchbase/domain/novelty.py), `coverage_material` | Version 1 hashes plan, execution IDs, providers, three counts, time scope and limitations; no historical unresolved count. |
| [application/novelty.py](../../src/researchbase/application/novelty.py), `_capture`, `_view_saved` | All resolution rows contribute to ambiguity; historical count is `None`; current count is recomputed on reads. |
| [novelty_repository.py](../../src/researchbase/persistence/novelty_repository.py), `prepare`, `repeatable_read` | All three writes take N SHARE first in READ COMMITTED; exact reads use snapshot isolation. |
| [0047](../../migrations/versions/0047_pr2_18_novelty_prior_art.py), [0057](../../migrations/versions/0057_xid_wraparound_guards.py) | Existing immutable parent, sealed execution children, deferred aggregate guards and corrected native-xid insertion checks. |
| [B01](B01_Search_Result_Resolution_Contract_DRAFT.md), [0050](../../migrations/versions/0050_b01_resolution_admission.py), [resolution_hash](../../src/researchbase/domain/search_result_resolution.py) | Typed immutable resolution records, preserved M2 hash material, closure at commit and serialization against capture. |
| [B18](B18_Novelty_Coverage_Completion_Contract_DRAFT.md), [G7 tests](../../tests/integration/phase2/test_pr2_19_novelty.py), [benchmark tests](../../tests/integration/phase2/test_pr2_20_novelty.py) | Consumer evidence exists; historical unknown remains deliberate until a material amendment. |

The templates are the approved [PR2-17](PR2-17_Submission_Authorship_Contract_DRAFT.md)
and [PR2-18](PR2-18_Novelty_PriorArt_Contract_DRAFT.md) drafts. Their earlier baseline
inventories are historical. The inspected migration directory ends at 0064;
choose the successor from the actual head at implementation time.

## 2. Scope, dependency boundaries and non-goals

Extend existing SearchCoverage, not a new canonical entity or capture service.
Reuse concrete relation tables, immutable rows, canonical JSON hashing and the
existing Application/repository/UoW boundary. No new persistence mechanism,
runtime dependency, JSON membership store or external call is needed.

Keep the three recording methods and three exact reads. Only coverage capture,
versioned verification and its nested output change. PriorArtRelation and
NoveltyAssessment retain their current material and admission policy.

## 3. Invariants and conservative judgments

For each selected terminal execution, include all its SearchResultRecord rows,
reached through its SearchQueryRecord rows. For each result, include **all**
SearchResultResolution rows visible under the held capture locks, not a selected
winner. Validate each resolution digest and exact source/version closure using
the existing B01/novelty rules before admission.

A result is resolved iff its captured resolution set is nonempty, every row has
a nonnull source_version_id, and the distinct `(source_id, source_version_id)`
set has exactly one member. Otherwise it is unresolved. Duplicate rows with the
same tuple do not create ambiguity; retain their distinct IDs and hashes anyway.
A source-only row followed by an exact row remains ambiguous. Conflicting exact
versions remain ambiguous. No latest-wins, merge deduplication or screening inference.

Historical unresolved count is the number of unresolved **results**. Existing
resolved_source_count counts distinct source IDs among resolved results. Two
resolved hits for one source yield result_count=2, resolved_source_count=1,
unresolved=0; subtraction is invalid. Zero results yields zero unresolved and
empty result/resolution membership, while the execution set remains nonempty.

Later resolution append, source correction/retraction or lost write authority
cannot alter captured membership, count or hash. Existing current validity and
disclosure checks still apply; retained hashes do not confer current usability.

## 4. Proposed commands, DTOs and historical readback

No new command, query, route or CLI command. `RecordSearchCoverageCommand` and
`ExactReadQuery` retain their fields (§11.3). Callers cannot choose material
version, membership, count, actor, hash or capture time.

Add `material_version` to SearchCoverageReadback. Change
CoverageQuality.captured_unresolved_result_count to `int | None`. Nested novelty
readback uses the same versioned coverage verifier. Current count, observed_at,
warnings, attempts and validity remain projections from the current read snapshot.
Do not expose membership lists in public responses in this slice; internal typed
rows suffice for verification. Routes/CLI outputs must accept legacy null and v2
integer without inventing a new endpoint or assuming all stored rows are v2.

## 5. Schema and literal hash proposal — no migration

This is a **proposed architecture/material amendment**, requiring recorded owner
and architecture disposition before implementation. Version 1 remains exactly
Hash Contract 15 and `coverage_material` today. Version 2 has exactly those keys,
with material_version=2, plus these two keys:

```json
{
  "captured_unresolved_result_count": 1,
  "captured_results": [
    {
      "search_result_record": {"type": "SearchResultRecord", "id": "<uuid>"},
      "resolutions": [
        {"type": "SearchResultResolution", "id": "<uuid>", "content_hash": "<digest>"}
      ]
    }
  ]
}
```

This fragment extends, rather than replaces, the full v1 payload. Sort result
entries by canonical UUID text and each resolution set by canonical UUID text;
reject duplicates. An unresolved result with no resolution has `resolutions: []`.
Result identity uses I(T), since no new result-content hash is introduced.
Resolution R(T) binds the existing unchanged M2/B01 digest, not a newly invented
resolution payload. Reconstruct its tuple from the referenced immutable record.
No generated child IDs, creation times, current diagnostics or extra keys enter.
Use existing canonical-json-v1 and sha256-cjson-v1; changing material_version
does not change hash_scheme. Do not extend novelty.HashRef's public literal union
just to serialize these internal concrete references.

On upgrade label existing coverage rows version 1 with null historical count and
no new membership. Never backfill from resolved_at, created_at or current rows.
All new captures are v2; replay selects the stored version and never upgrades an
existing UUID. A new UUID captures a new observation. Version-1 digests and saved
NoveltyAssessment refs remain identical. New NoveltyAssessments may bind either
verified version through the existing SearchCoverage R(T); their own payload
stays version 1. Unknown versions, mismatched count/membership or digest fail
closed. Roll out migration and dual-version readers before enabling v2 writers;
old binaries cannot safely read v2. Downgrade refuses any v2 parent or new child.

## 6. Error contract — existing categories

Use §11.2, including its distinct CLI integrity exits. There is no new
HASH_MISMATCH or CAPTURE_UNKNOWN ErrorCode. Legacy unknown is successful null
readback, not an error. Authorize before revealing missing/corrupt nested inputs.

## 7. Transactions, concurrency and failure recovery

One synchronous Application command, one transaction. Extend the existing capture
transaction, not a later fill-in transaction. SHARE locks exclude resolution
INSERT phantoms, including empty histories; a waiting capture reads after the
writer commits under READ COMMITTED. A resolution writer waiting behind capture
can affect only subsequent current diagnostics. Exact reads take no explicit locks.

Retry only 40001/40P01, at most three total fresh UoWs, without delay or external
calls. Preserve existing normalization and do not retry every business
CONCURRENT_MODIFICATION, unique failure, timeout or uncertain commit. Recover an
uncertain commit through the same exact UUID/request. Failed parent, membership,
hash or deferred validation leaves no partial history.

## 8. Tests after authorization — planned, NOT IMPLEMENTED

Use §12.4 with independent expected payloads, real PostgreSQL 18.x, two backend
PIDs and observable blocked-lock evidence. Restart means new service/UoW/engine
objects reading committed rows, not returning a cached DTO. Existing tests in
this checkout prove the baseline only; they cannot prove the proposed amendment.

## 9. Acceptance criteria and evidence boundary

Approval must resolve §13 and freeze the exact material/schema amendment.
Implementation acceptance requires legacy digest preservation, complete sealed
membership, exact saved counts after restart, independent current diagnostics,
both race orders, denial atomicity and focused inherited regressions. No stronger
novelty outcome, full G7 or Phase 2 exit follows from B21. Full-suite execution
belongs to the owner's loop. Stop after this bounded evidence.

## 10. Glossary

| Term | Meaning |
| --- | --- |
| Capture | Membership observed atomically when the existing coverage assessment is created. |
| Historical / current | Saved membership-based count / timestamped diagnostic over the read snapshot. |
| I(T) / R(T) | Exact typed ID / exact typed ID plus existing content hash. |
| Legacy | Stored material version 1; historical unresolved count is unknown. |
| N | Exact ordered table tuple in novelty_repository.py, expanded in §12.2. |
| Seal | Children may be inserted only with their newly inserted parent in the same transaction. |

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

Adopt v2 only for new coverage, two concrete child relations, complete all-row
membership, no retrospective reconstruction, dual-version reads and unchanged
resolution/novelty hashes. Reject a count-only column: it cannot establish what
was inspected. These are proposed decisions, not current architecture authority.

### 11.2 Pinned error mappings

From [api/errors.py](../../src/researchbase/api/errors.py),
[cli/errors.py](../../src/researchbase/cli/errors.py) and novelty normalization in
[uow.py](../../src/researchbase/persistence/uow.py):

| Code | HTTP | CLI | Trigger |
| --- | --- | --- | --- |
| AUTHENTICATION_REQUIRED | 401 | 3 | Trusted principal absent. |
| FORBIDDEN | 403 | 3 | Current read/write entitlement absent, foreign scope or different-actor replay. |
| VALIDATION_ERROR | 422 | 2 | Closed DTO, type, duplicate or bound violation. |
| NOT_FOUND | 404 | 3 | Authorized exact input/record absent. |
| FROZEN_REFERENCE_REQUIRED | 409 | 5 | Required exact plan/source is not frozen. |
| INVALID_STATE_TRANSITION | 409 | 4 | Nonterminal execution/attempt or existing unsupported novelty admission. |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Unsupported stored version, corrupt digest, incomplete or foreign membership, false accounting. |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Same entitled actor/UUID with changed normalized request. |
| IMMUTABLE_RECORD | 409 | 4 | Parent/child mutation or late child insertion. |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Concrete FK violation. |
| CONCURRENT_MODIFICATION | 409 | 4 | Existing normalized concurrency/uniqueness conflict; retry only SQLSTATE-qualified cases. |
| INTERNAL_ERROR (fallback, not ErrorCode) | 500 | 1 | Unexpected infrastructure/programming failure, including novelty's nonretryable timeout/unknown commit failure. |

Reuse SQLSTATE P17D1 for sealing/immutability, P17D3 for capture closure and 23503
for FKs. Name B21 CHECK/unique constraints explicitly in UoW normalization:
stored capture shape/accounting failures map to PROVENANCE_CLOSURE_VIOLATION;
duplicate membership is not permission to drop a row. Do not broadly remap other
commands' errors. Sanitize database details and keep existing error envelopes.

### 11.3 DTO fields, Python types, limits and enums

| DTO/field | Pinned type and rule |
| --- | --- |
| RecordSearchCoverageCommand | `id: UUID`, `project_id: UUID`, `search_plan_version_id: UUID`, `search_execution_ids: tuple[UUID, ...]`, `coverage_limitations: str`; unchanged. |
| ExactReadQuery | `project_id: UUID`, `id: UUID`; unchanged. |
| SearchCoverageReadback.material_version | `Literal[1, 2]`, server-derived. |
| CoverageQuality.captured_unresolved_result_count | `int | None`; exactly None for v1; strict non-bool integer 0..result_count for v2. |
| Internal captured result | `search_result_record_id: UUID`; sorted tuple of concrete resolution refs (`id: UUID`, `content_hash: str`). No ORM object or arbitrary JSON. |
| Existing count/hash/time fields | Counts strict int 0..2,147,483,647; digest lowercase 64-hex; hash_scheme literal sha256-cjson-v1; UTC-aware datetime; TimeScope date bounds unchanged. |
| Current quality | `current_unresolved_result_count: int`, `observed_at: datetime`, selected_scope literal True, screening_captured literal False; unchanged attempt and warning tuples. |

Commands remain frozen/closed. UUID fields require exact UUID objects internally;
transport UUID strings retain existing canonical validation. Execution IDs are
distinct, sorted, 1..100; limitations are NFC, valid UTF-8, nonblank, no NUL,
1..16,384 characters without trimming. Provider text retains 128-character bound.
No new arbitrary result/resolution cap: capture the complete set or fail atomically;
never truncate. INT accounting overflow is a closure failure before INSERT.

No new status enum. Preserve all QualityWarning literals: NO_INVOKED_QUERIES,
FAILED_ATTEMPT, CANCELLED_ATTEMPT, UNKNOWN_ATTEMPT, UNINVOKED_PROVIDER,
PARTIAL_RESULTS, UNRESOLVED_RESULTS, FILTER_COMPLIANCE_UNPROVEN,
SCREENING_NOT_CAPTURED, INPUT_CURRENTLY_UNUSABLE. UNRESOLVED_RESULTS continues to
describe the current projection. NoveltyOutcome remains INCONCLUSIVE,
CLOSE_PRIOR_ART_FOUND, NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE, with only INCONCLUSIVE
admitted. PriorArtKind and attempt-status enums remain unchanged.
PriorArtKind is exactly IDENTICAL, HIGHLY_SIMILAR, PARTIAL_OVERLAP, RELATED,
CONTRASTING, UNCLEAR. Attempt status is exactly RESERVED, SUCCEEDED,
RETRYABLE_FAILURE, PERMANENT_FAILURE, CANCELLED, UNKNOWN; RESERVED prevents
capture. Selected execution status is SUCCEEDED, FAILED, CANCELLED or UNKNOWN.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

Proposed successor migration `migrations/versions/<next>_b21_unresolved_capture.py`;
resolve `<next>` from the actual head. Use existing relation/audit conventions:

```sql
ALTER TABLE search_coverage
  ADD COLUMN material_version SMALLINT NOT NULL DEFAULT 1,
  ADD COLUMN captured_unresolved_result_count INT,
  ADD CONSTRAINT ck_b21_capture_version CHECK (material_version IN (1,2)),
  ADD CONSTRAINT ck_b21_capture_count CHECK (
    (material_version=1 AND captured_unresolved_result_count IS NULL) OR
    (material_version=2 AND captured_unresolved_result_count IS NOT NULL
      AND captured_unresolved_result_count BETWEEN 0 AND result_count));
ALTER TABLE search_coverage ALTER COLUMN material_version SET DEFAULT 2;

CREATE TABLE search_coverage_results (
  id UUID CONSTRAINT pk_b21_results PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL,
  created_by UUID NOT NULL CONSTRAINT fk_b21_results_actor
    REFERENCES actors(id) ON DELETE RESTRICT,
  search_coverage_id UUID NOT NULL CONSTRAINT fk_b21_results_coverage
    REFERENCES search_coverage(id) ON DELETE RESTRICT,
  search_result_record_id UUID NOT NULL CONSTRAINT fk_b21_results_result
    REFERENCES search_result_records(id) ON DELETE RESTRICT,
  CONSTRAINT uq_b21_results_pair UNIQUE(search_coverage_id,search_result_record_id)
);
CREATE TABLE search_coverage_resolutions (
  id UUID CONSTRAINT pk_b21_resolutions PRIMARY KEY,
  created_at TIMESTAMPTZ NOT NULL,
  created_by UUID NOT NULL CONSTRAINT fk_b21_resolutions_actor
    REFERENCES actors(id) ON DELETE RESTRICT,
  search_coverage_id UUID NOT NULL,
  search_result_record_id UUID NOT NULL,
  search_result_resolution_id UUID NOT NULL CONSTRAINT fk_b21_resolutions_resolution
    REFERENCES search_result_resolutions(id) ON DELETE RESTRICT,
  resolution_content_hash CHAR(64) NOT NULL,
  CONSTRAINT ck_b21_resolution_hash CHECK (resolution_content_hash ~ '^[0-9a-f]{64}$'),
  CONSTRAINT fk_b21_resolutions_result FOREIGN KEY
    (search_coverage_id,search_result_record_id) REFERENCES search_coverage_results
    (search_coverage_id,search_result_record_id) ON DELETE RESTRICT,
  CONSTRAINT uq_b21_resolutions_pair UNIQUE(search_coverage_id,search_result_resolution_id)
);
CREATE INDEX ix_b21_results_target ON search_coverage_results(search_result_record_id);
CREATE INDEX ix_b21_resolutions_target ON search_coverage_resolutions(search_result_resolution_id);
```

Preserve existing parent/execution immutability. Add BEFORE UPDATE OR DELETE
`trg_b21_results_immutable`, `trg_b21_resolutions_immutable`, calling
pr218_immutable(). BEFORE INSERT `trg_b21_results_guard` and
`trg_b21_resolutions_guard` require v2, pr218_capture_prelocked(), parent inserted
in this transaction and equal created_by/created_at. Use native
`parent.xmin = pg_current_xact_id()::xid` as corrected by 0057, never bigint
comparison, a saved xmin or a durable transaction ID. Check result belongs to a
selected execution; resolution belongs to that exact result and saved digest
matches its row. New-parent guard `trg_b21_capture_version_guard` requires v2
on INSERT, including explicit caller-supplied v1; legacy rows are untouched.

Following [0042's deferred constraint-trigger pattern](../../migrations/versions/0042_pr2_15_minimal_decision.py),
add DEFERRABLE INITIALLY DEFERRED AFTER INSERT row triggers named
`trg_b21_parent_complete`, `trg_b21_executions_complete`,
`trg_b21_results_complete`, `trg_b21_resolutions_complete`, all calling
`b21_capture_complete()`. They validate v2 complete result membership by bidirectional
set difference against selected executions and complete resolution membership by
bidirectional set difference against then-visible resolutions. Check exact tuple
bindings, hashes, counts and existing providers/query/time accounting. Empty
sets are legal only when the actual selected executions produced no results.
The parent trigger catches omitted children even when no child event exists.

Keep existing pr218_complete_coverage validation and B01 deferred closure;
coordinate functions without replacing v1 history or allowing late completion.
Completeness runs only on insertion, never against later resolution rows during
historical reads. DB guards enforce structure/accounting; Application recomputes
canonical digests. Do not claim the SQL lock inventory proves first-statement
ordering: test that separately. Refuse populated-v2 downgrade before any DDL;
legacy-only downgrade removes added metadata/guards without changing old bytes.

### 12.2 Exact lock order and transactions

N is the current ordered tuple, unchanged. For **each** recording command select
READ COMMITTED through connection options, then this is the FIRST SQL statement:

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

Then SET LOCAL lock_timeout='10s', statement_timeout='30s'; request advisory
`pg_advisory_xact_lock(hashtextextended(:key,0))` using
`pr218:{kind}:{canonical request UUID}`. No lock upgrade, preceding SELECT/SET,
new namespace or explicit lock on the new membership tables is required.

| Command | Remaining order after N, timeouts and request advisory |
| --- | --- |
| record_search_coverage (`kind=coverage`) | Authorize reader at DB clock; read existing parent for replay. New request: authorize writer, validate exact plan, UUID-sorted executions/attempts/queries/results/resolutions under N, retain membership and compute v2. Recheck writer; INSERT parent, sorted execution children, sorted result children, then resolution children sorted by result/ID. No FOR UPDATE. |
| record_prior_art_relation (`kind=prior_art`) | Exact ClaimVersion FOR UPDATE; authorize reader/replay; if new authorize writer, verify exact Claim/source and sorted evidence; recheck writer; parent and evidence children. No B21 membership writes. |
| record_novelty_assessment (`kind=novelty`) | Exact ClaimVersion FOR UPDATE; authorize reader/replay; if new authorize writer, enforce INCONCLUSIVE, verify Claim and stored-version coverage, optional predecessor FOR UPDATE then reread successor; recheck writer; parent INSERT. |
| Three exact reads | begin_formal_read(): read-only REPEATABLE READ, authorize reader, read parent/children/exact dependencies, verify stored material and compute current projections in that one snapshot, final read-entitlement clock check, return. No explicit table, advisory, FOR SHARE or FOR UPDATE locks; no writes. |

New writes force SET CONSTRAINTS ALL IMMEDIATE, read back and verify, recheck
writer entitlement with fresh clock_timestamp(), commit. Replay verifies saved
membership/version, compares the unchanged normalized caller request, rechecks
current reader entitlement and returns without inserts. Current resolutions may
change diagnostics, never replay's saved capture. After blocking waits reread
authority and use fresh DB time; repeat final checks if a later wait occurs.
Do not retrofit locks into read paths to verify v2. Existing shared row/reference
read helpers must remain configured for protected/snapshot reads.

### 12.3 Ordered build steps and real file paths

1. Freeze the approved amendment in `docs/architecture/13_Phase2_Schema_Field_Contract_v1.0.md`
   and `docs/architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md`, with bounded
   architecture disposition. Add the successor migration from §12.1; preserve
   0047/0050/0057 and all existing hashes. No changes to those files in this task.
2. In `src/researchbase/domain/novelty.py`, retain v1 builder; add typed capture
   values, strict v2 builder and accounting validation. Reuse foundation hashing;
   keep transport/SQL imports out. Use unchanged domain/search_result_resolution.py
   resolution_hash as the digest authority in Application verification.
3. Extend `src/researchbase/application/novelty.py`: collect validated membership
   once under N, compute saved count, dispatch reads/replays by stored version,
   verify membership using retained records separately from current `_capture`.
   Add only §11.3 readback fields; update typed repository port in
   `src/researchbase/application/ports.py`.
4. Extend `src/researchbase/persistence/novelty_repository.py` with plain sorted
   membership reads and inserts. Wire guards/errors through
   `src/researchbase/persistence/uow.py`; retain existing factory and transactions.
   No ORM semantic owner, new UoW or separate repository subsystem.
5. Update coverage/nested response schemas in `src/researchbase/api/routes.py`
   and serialization in `src/researchbase/cli/commands/literature.py` as needed.
   Existing service composition/routes/command names remain. No caller capture fields.
6. Add §12.4 tests, update consumer expectations to distinguish legacy null from
   v2 count, run focused checks, record exact evidence and stop. Do not implement
   deferred novelty or publication behavior to satisfy a test.

### 12.4 Test files and required cases

Files marked new are future artifacts, not part of this documentation change.

| File | Required cases |
| --- | --- |
| `tests/unit/phase2/test_b21_capture_contract.py` (new) | Strict count/version/UUID types, bool rejection, bounds, Unicode, closed caller DTOs; no caller membership/version; exact legacy null/v2 int output. |
| `tests/unit/phase2/test_b21_capture_hash_vectors.py` (new) | Independent literal full v2 canonical bytes/digests; empty results, empty resolution set, sorted/permuted children, changed resolution hash/membership inequality; v1 vectors unchanged; no extra material keys. |
| `tests/integration/phase2/test_b21_capture.py` (new) | Real owning services via pr2_18_fixtures.py/b01_support.py; zero-result, two hits/one source, no resolution, identical tuple duplicates, source-only plus exact, conflicting versions; restart then append resolution changes current only; valid nested novelty read/replay on both versions; lost entitlement, corrupt refs and atomic failures. |
| `tests/integration/phase2/test_b21_capture_schema.py` (new) | Catalog names/types/FKs; clean install and populated-v1 upgrade without digest/novelty-ref changes; explicit v1 insert denial, wrong execution/result/resolution, missing/extra children, false count, invalid digest, late insert/update/delete, missing prelocks/wrong isolation, rollback on deferred failure; downgrade refusal with v2. |
| `tests/integration/phase2/test_b21_capture_concurrency.py` (new) | Capture first vs B01 resolution first, empty-history phantom, two engines/PIDs with blocked-lock witness; first SQL N; reader does not block writer and keeps one snapshot; no explicit read locks; credential/role expiry after waits; exactly three 40001/40P01 attempts, no timeout/business retry, same-ID single saved set and uncertain-commit replay. |
| `tests/architecture/test_b21_capture_boundaries.py` (new) | Domain/Application/adapter separation, no direct scientific writes by transports, no generic JSON membership, existing canonical owner, no external call in transaction, inherited v1 and Phase 1 hashes. |
| Existing PR2-18/B01 unit, schema, replay, coverage and concurrency files | Preserve all-row ambiguity, error mappings, immutable history and replay. Extend `test_pr2_18_api.py`/`test_pr2_18_transports.py` for legacy/v2 coverage and nested output. |
| Existing `tests/integration/phase2/test_pr2_19_novelty.py`, `test_pr2_20_novelty.py` | G7/benchmark compare saved v2 counts/hash across restart and later resolution; legacy fixtures remain explicit. No claim of full G7/benchmark acceptance. |

### 12.5 Not in this slice

Legacy-history reconstruction or rehash; caller-selected resolution winners;
screening dispositions; intended-probe completeness; stronger novelty outcomes;
new comparison supersession; new review/Decision/Approval targets; automatic
impact propagation; package/READY/consent changes; provider execution; pagination
or public membership-detail endpoint; queues, event sourcing or new infrastructure.

## 13. Open questions for the owner — override register

| Approval item | Decision adopted in this draft |
| --- | --- |
| Material compatibility | Approve v2 extension with retained v1 verifier, unchanged scheme and no rehash/backfill. Update architecture contracts before implementation. |
| Concrete membership | Approve two typed existing-assessment relations binding every result and every visible resolution, including empty histories. |
| Public output/limits | Expose version and historical count only; preserve command limits; never truncate complete membership. |
| Release boundary | Dual readers before v2 writers; old binaries unsupported for v2; populated-v2 downgrade refuses. |

Owner override requires body edits and recorded architecture disposition before
freeze. Contract approval alone is not execution authorization.

## 14. Documentation verification note

Only this draft is changed. Executed against current code on 2026-10-18; these
are baseline checks, not evidence that proposed B21 behavior exists. Every command
below used this exact prefix:

```bash
VIRTUAL_ENV=/Users/fengwang/Documents/ResearchBaseProject/.venv UV_CACHE_DIR=/private/tmp/rb-b21-uv-cache uv run --active --offline --no-sync
```

| Command suffix | Observed result |
| --- | --- |
| `ruff check .` | Exit 0; All checks passed. |
| `ruff format --check .` | Exit 0; 699 files already formatted. |
| `pyright` | Exit 0; 0 errors, 0 warnings, 0 informations. Initial diagnostic: local .venv subdirectory absent; shared active environment used. |
| `pytest tests/unit/phase2/test_pr2_18_hash_vectors.py tests/unit/phase2/test_pr2_18_novelty_contract.py tests/unit/phase2/test_pr2_18_transports.py tests/unit/phase2/test_b01_resolution_contract.py tests/architecture/test_pr2_18_boundaries.py tests/architecture/test_b01_resolution_boundaries.py tests/integration/phase2/test_pr2_19_dependencies.py -o addopts='' -q -p no:cacheprovider` | Exit 0; 129 passed in 1.55s. |

Focused PostgreSQL command, with the same prefix between the DB variables and pytest:

```bash
DATABASE_URL=postgresql+psycopg:///postgres RB_TEST_ADMIN_URL=postgresql+psycopg:///postgres VIRTUAL_ENV=/Users/fengwang/Documents/ResearchBaseProject/.venv UV_CACHE_DIR=/private/tmp/rb-b21-uv-cache uv run --active --offline --no-sync pytest tests/integration/phase2/test_pr2_18_search_coverage.py tests/integration/phase2/test_pr2_18_schema.py tests/integration/phase2/test_pr2_18_replay.py tests/integration/phase2/test_pr2_18_concurrency.py tests/integration/phase2/test_b01_resolution_concurrency.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_20_novelty.py -o addopts='' -q -p no:cacheprovider --maxfail=1
```

Exit 1: **1 error, 1 warning in 0.62s; zero database cases passed**. First fixture
`test_capture_and_restart` could not connect to `/tmp/.s.PGSQL.5432`: Operation
not permitted. Remaining PostgreSQL cases were not run after fail-fast. The
warning concerns already imported b01_support assertion rewriting. No database
PASS, implementation acceptance or Phase exit is claimed. Full suite reserved
for the owner's loop.

Documentation checks: `git diff --no-index --check /dev/null
docs/proposals/B21_Unresolved_Count_Capture_Contract_DRAFT.md` exited 0. A local
Python Markdown-link check resolved all 27 relative links, with zero missing.
`git status --short` showed only this new draft; no branch or commit was created.
