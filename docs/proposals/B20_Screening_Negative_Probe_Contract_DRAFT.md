# B20 Screening and Negative-probe Assessment Basis Contract — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

## Start here (for the implementer)

B20 proposes an attributable, reproducible basis for
`NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE`. It records every intended query of every
execution in the exact plan's bounded inventory, retains failed and zero-hit
probes, and screens every retained result. A successful search is not screening;
a negative assessment is a judgment within stated coverage, never universal priority.

After owner approval **and separate implementation authorization**:

1. Approve [ADR-0018](ADR-0018_Screening_Negative_Probe_Basis_DRAFT.md), including
   the two child relations and the outcome-specific v2 extension (§5, §12.1).
2. Preserve B18/B01/B19/B21/B22 behavior and exact historical hashes (§1, §11).
3. Build closed values and DTOs, then extend the existing NoveltyService and
   repository; do not introduce a screening service or another persistence owner.
4. Add sealed probe/result children and independent deferred completeness guards;
   follow the first-statement SHARE protocol for writes and lock-free reads (§12.2).
5. Add thin existing-route/CLI support and the tests in §12.4. Record actual
   results and stop. This draft and its baseline checks are not B20 acceptance.

Five review rules:

1. No omitted execution, query, retry, failed branch or result inside the captured
   inventory; intended queries come from saved execution contexts, not hits.
2. No unresolved, unclear, excluded, partial-overlap or close result can justify
   a negative assessment. Zero hits are retained without fabricated evidence.
3. Bind exact v2 coverage and exact comparison/resolution references; preserve
   v1 and existing positive-v2 bytes. Later corrections never redirect history.
4. One Application command/transaction; locks precede reads; fresh database time
   after waits. Exact reads use one read-only REPEATABLE READ snapshot, no locks.
5. Neither assessor authority nor narrative criteria proves scientific truth.
   No novelty-driven approval, support, review or publication side effect.

Read §§1–3 first, use the glossary (§10), and implement only the frozen decisions
in §11 after authorization. §12 gives the build sequence, lock order and tests;
§13 identifies owner decisions. This task changes documentation only.

## 1. Purpose, authority and inspected baseline

Authority, in AGENTS.md order: [Architecture 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md)
§§3, 6–13 (single owner, immutable history, exact frozen provenance);
[Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md)
(architecture review for bounded additions);
[Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md)
(literature owns assessments and relations);
[Compatibility 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md)
(common Application boundary and additive compatibility);
[Phase 2 Specification 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md)
§25/PR2-18; [Harness 09](../harness/09_Harness_Integration_Specification_v1.0.md)
§§2, 15 (tool output is candidate material).
[Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md),
[Field Contract 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md),
[Hash Contract 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md),
[Temporal 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md)
and accepted [ADR-0017](../architecture/adr/ADR-0017-novelty-material-v2.md)
control concrete references, material versions and advancing authorization time.
These authorities require explicit admission of this proposal, not inference
that B20's schema already exists. No B20 execution pack authorizes implementation.

| Current source | Implemented basis / remaining gap |
| --- | --- |
| [domain/novelty.py](../../src/researchbase/domain/novelty.py), [application/novelty.py](../../src/researchbase/application/novelty.py) | INCONCLUSIVE v1, positive assessment v2 with exact comparison basis; negative enum exists but is denied. Coverage quality still says screening_captured=False. |
| [0065 B22](../../migrations/versions/0065_b22_prior_art_correction.py), [0066 B19](../../migrations/versions/0066_b19_close_prior_art_basis.py), [0068 B21](../../migrations/versions/0068_b21_unresolved_capture.py) | Nonforking comparison corrections; sealed positive basis; saved resolution membership and historical unresolved count. No probe/screening children. |
| [0050 B01](../../migrations/versions/0050_b01_resolution_admission.py) | Exact resolution admission/commit closure; all resolution rows matter, not latest-wins. |
| [execution domain](../../src/researchbase/domain/literature_search_execution.py), [0024](../../migrations/versions/0024_literature_search_execution.py) | Saved execution_context includes intended ordered queries and provider/budgets; attempts name query_index. Terminal query/result sets are sealed. These facts can retain zero-hit and interrupted probes. |
| [novelty_repository.py](../../src/researchbase/persistence/novelty_repository.py), [decision_repository.py](../../src/researchbase/persistence/decision_repository.py), [uow.py](../../src/researchbase/persistence/uow.py) | Existing preheld SHARE / READ COMMITTED write protocol, request coordination, formal snapshot reads and SQLSTATE normalization. |
| [0042](../../migrations/versions/0042_pr2_15_minimal_decision.py), 0066, 0068 | Existing same-transaction sealed children and DEFERRABLE INITIALLY DEFERRED constraint-trigger pattern. |
| [B18](B18_Novelty_Coverage_Completion_Contract_DRAFT.md), [B19](B19_Close_Prior_Art_Basis_Contract_DRAFT.md), [B21](B21_Unresolved_Count_Capture_Contract_DRAFT.md), [B22](B22_PriorArt_Correction_Selection_Contract_DRAFT.md), [B01](B01_Search_Result_Resolution_Contract_DRAFT.md) | Dependency contracts; their historical baseline descriptions do not override today's code. |

The structure follows the approved [PR2-17](PR2-17_Submission_Authorship_Contract_DRAFT.md)
and [PR2-18](PR2-18_Novelty_PriorArt_Contract_DRAFT.md) contracts. All B20 behavior
below is proposed; source presence and baseline test results are not acceptance.

## 2. Scope, dependency boundaries and non-goals

Extend `record_novelty_assessment` and `read_novelty_assessment` only. Negative
outcomes require the complete B20 basis; INCONCLUSIVE may optionally retain an
incomplete screening basis. Existing INCONCLUSIVE without screening and B19
positive commands remain unchanged. No new endpoint, command family, dependency,
provider execution mechanism, top-level entity or separate criteria engine.

This inventory is retrospective and explicitly bounded: **all executions of the
exact plan version visible when the assessment acquires its first SHARE locks**,
with every query declared in those executions. It does not certify that the
researcher planned every scientifically desirable search in advance. Scope and
limitations must disclose that distinction. A prospective preregistration protocol
or proof of external search exhaustiveness needs a separate contract.

## 3. Invariants and conservative judgments

1. Claim, plan, coverage, executions, results, resolutions and comparisons resolve
   within one authorized project. Claim and source versions are exact frozen
   versions, admitting historical SUPERSEDED frozen versions as existing code does.
   Verify saved hashes, artifact bytes and current usability with existing owners.
2. New screening uses B21 material_version=2 coverage only. Its execution set must
   equal **all** exact-plan executions visible under N, not a caller-selected subset.
   An active execution blocks admission; retain terminal FAILED/CANCELLED/UNKNOWN
   executions. New later executions do not alter the saved inventory; readback
   reports that the plan inventory has expanded and current negative basis is unusable.
3. Probe keys are `(execution_id, query_index)` for every index of each saved
   execution_context.queries. Include never-invoked queries. Derive attempts and
   query/results through existing concrete execution/attempt/query FKs. No timestamp
   cutoff, result deduplication, latest resolution or guessed query text matching.
4. Probe dispositions are NO_HITS, SCREENED or INCOMPLETE. Derive NO_HITS only
   from a successful, warning-free completed query with zero retained results;
   SCREENED from such a query with results; otherwise INCOMPLETE. Any non-SUCCEEDED
   execution or any non-successful/warning-bearing attempt makes its probes
   INCOMPLETE for this conservative first slice, including recovered retries.
   Retain all attempts; a later successful execution does not erase a failed one.
5. Exactly one screening disposition per retained result, including duplicates
   and failed-attempt hits. NOT_CLOSE requires an exact B21-captured resolution
   witness and one exact same-Claim/SourceVersion PriorArtRelation with full
   independently HUMAN-VERIFIED evidence. All captured resolutions must agree on
   that exact source/version. Current conflicting resolutions block new negatives.
6. A NOT_CLOSE comparison is RELATED or CONTRASTING only. IDENTICAL/HIGHLY_SIMILAR
   requires CLOSE; PARTIAL_OVERLAP/UNCLEAR requires UNCLEAR. EXCLUDED and UNRESOLVED
   retain rationale but cannot establish absence. No arbitrary exclusion can hide
   a close or unresolved hit. Narrative criteria explain the assessment; they are
   neither executable predicates nor authority to redefine these enum rules.
7. For each resolved result inspect the complete B22 same-Claim/exact-source-version
   graph. Negative admission requires UNIQUE selection, the referenced terminal,
   and currently usable evidence/source. EMPTY/AMBIGUOUS, a successor, or conflicting
   independent roots blocks admission. No latest-wins or automatic substitution.
8. Negative outcome requires nonempty probe inventory, all probes complete,
   a nonempty frozen plan planned_providers set equal to the actually invoked
   provider set (no uninvoked or undeclared provider), captured unresolved count
   zero, every result NOT_CLOSE, and nonempty scope,
   criteria and limitations. Zero total results is allowed only with at least one
   completed NO_HITS probe. No query invocation is never a negative search.
9. Existing assessment predecessor chains remain same-exact-Claim and nonforking.
   Correction creates new records/assessment; no child mutation. Later comparison
   corrections, new roots, resolutions, executions or deterministic invalidity
   affect timestamped current usability, never saved membership or hashes.
10. Reads verify historical structure separately from current judgment: later
    failures do not make an exact historical record disappear. Raw nested evidence
    still needs its owning read entitlement. Coverage remains selected_scope=True
    and screening_captured=False: screening belongs to this assessment, not coverage.

## 4. Proposed commands, DTOs and historical readback

Add optional `screening_basis: ScreeningBasisInput | None = None` to
`RecordNoveltyAssessmentCommand`. Existing fields remain unchanged. Negative
requires it; INCONCLUSIVE permits it; CLOSE_PRIOR_ART_FOUND forbids it and keeps
B19's prior_art_basis. Screening INCONCLUSIVE also requires scope/criteria and
empty prior_art_basis. Old INCONCLUSIVE retains null scope/criteria and empty basis.

POST/GET remain `/v1/projects/{project_id}/novelty-assessments[/{id}]`;
CLI remains `literature record-novelty-assessment` / `read-novelty-assessment`.
POST first write/exact replay and GET return 200. Use the existing JSON input and
output envelopes. Authenticated principal is trusted input, never a caller actor
assertion. Writers are current OWNER/RESEARCHER; readers retain the existing
OWNER/RESEARCHER/REVIEWER/VIEWER/APPROVER policy.

Readback adds nullable typed screening_basis and timestamped screening validity
with `inventory_expanded: bool`, `complete: bool`, `usable_for_current_judgment: bool`.
These projections are not material. Same-actor exact replay compares normalized
saved fields/version, requires current read entitlement and returns saved history;
it does not require the old basis to remain eligible for a new negative judgment.
Changed normalized input is IDEMPOTENCY_CONFLICT. Unknown commit recovery reuses
the exact UUID. No automatic same-ID upgrade or alternative UUID retry.

## 5. Schema and literal hash proposal — one forward migration; two new tables

One forward migration adds `novelty_assessments.screening_captured BOOLEAN NOT NULL
DEFAULT FALSE` and two new tables, `novelty_assessment_probes` and
`novelty_assessment_screening_results`, with the constraints and guards in §12.1.

ADR-0018 requests **outcome/shape-specific v2 dispatch**, preserving all existing
payloads exactly. INCONCLUSIVE without screening stays v1; positive v2 stays
ADR-0017's exact shape. New screening INCONCLUSIVE and negative use this entire
v2 template. R/I notation expands to Contract 15 reference objects, not strings;
this is a payload specification, not a literal digest test vector.

```text
{
  "type": "NoveltyAssessment", "material_version": 2,
  "claim_version": R(ClaimVersion), "search_coverage": R(SearchCoverage),
  "assessment": <INCONCLUSIVE|NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE>,
  "limitations": <text>, "supersedes_assessment": R(NoveltyAssessment)|null,
  "assessed_by": I(ActorIdentity), "scope_statement": <text>,
  "closeness_criteria": {"statements": [<text>, ...]},
  "prior_art_basis": [],
  "screening_basis": {
    "probes": [{"search_execution": I(LiteratureSearchExecution),
                "query_index": <int>, "disposition": <ProbeDisposition>,
                "rationale": <text>}],
    "results": [{"search_result_record": I(SearchResultRecord),
                 "disposition": <ScreeningDisposition>,
                 "criteria_ordinals": [<int>, ...], "rationale": <text>,
                 "prior_art_relation": R(PriorArtRelation)|null,
                 "search_result_resolution": R(SearchResultResolution)|null}]
  }
}
```

Probes sort by execution UUID then zero-based query_index; results by result UUID;
criterion ordinals are a sorted distinct nonempty subset of the parent's authored
zero-based criteria positions. Criteria statements preserve authored order.
No new hash for executions/results: reuse existing terminal seals and B21 coverage
membership exactly as ADR-0017 does. Query contexts, attempts and result sets
remain reconstructible through these immutable owners. No JSON reference store.

Scheme remains sha256-cjson-v1. Do not add screening_basis:null to old payloads.
Verify each referenced coverage/comparison/predecessor using its own saved version;
unknown versions/shapes fail closed. Roll out dual-shape readers before writers.
Old binaries cannot read new shapes; never advertise forward-reader compatibility.
No backfill from current sets, historical digest rewrite or Phase 1 hash change.

## 6. Error contract — existing categories

Use the pinned mappings in §11.2. Invalid DTO shape/bounds is validation; a valid
but incomplete negative basis is invalid state; wrong exact membership or corrupt
hash/closure is provenance violation. Database guards must match Application
admission. No new business error code or HASH_MISMATCH literal.

## 7. Transactions, concurrency and failure recovery

One synchronous command is one READ COMMITTED transaction. Use §12.2, not the
older PR2-18 Claim-before-N draft order. SQLSTATE 40001/40P01 alone permits at
most three fresh-UoW attempts, no delay/external call. Unique predecessor loss is
CONCURRENT_MODIFICATION without retry; timeouts and uncertain commits are sanitized
INTERNAL_ERROR. Reads create no records. No current projection enters a digest.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

§12.4 defines future B20 tests. Existing baseline suites can establish dependency
regressions only. Independent canonical JSON/digest fixtures must cover both new
shapes and unchanged old bytes; using the production builder as oracle is insufficient.
Two independent PostgreSQL backends must demonstrate the admission/insert orderings,
including initially empty ranges. A simulated repository lock assertion is insufficient.

## 9. Acceptance criteria and evidence boundary

Acceptance requires owner-approved ADR/contract, separate execution authorization,
all §12.4 tests and focused dependency regressions with exact commands/counts,
normal-role SQL denial, restart/replay and observed PostgreSQL race evidence.
No open P0/P1; full-suite evidence comes from the loop. Documentation completion
or baseline regression success cannot enable negative admission or declare Phase 2 done.

## 10. Glossary

| Term | Meaning |
| --- | --- |
| Probe | One intended query position in a saved execution context, including never-invoked positions. |
| Inventory | All executions of one exact plan version visible under the admission locks, and all their intended probes. |
| Retained negative | A sealed NO_HITS probe or NOT_CLOSE result with its rationale and exact basis; never deletion. |
| Screening | Per-result disposition plus criterion positions and exact comparison/resolution where applicable. |
| N | The exact ordered 35-table tuple exported by novelty_repository.py, expanded in §12.2. |
| Captured / current | Immutable historical basis / timestamped later diagnostics. |
| UNIQUE | B22's one root/terminal comparison chain for the exact Claim/SourceVersion pair; not universal authority. |

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

Adopt §§2–5's bounded retrospective inventory and conservative admission. No
prospective completeness claim, programmable criteria, exclusion shortcut or
failed-probe replacement. Reuse the existing assessment and Relation patterns;
request two child relations and an explicit B19 guard-attachment amendment through
ADR-0018. Preserve existing behavior for callers that omit screening_basis.

### 11.2 Pinned error mappings

These match [api/errors.py](../../src/researchbase/api/errors.py) and
[cli/errors.py](../../src/researchbase/cli/errors.py); INTERNAL_ERROR is a fallback,
not an ErrorCode. Novelty CLI uses the shared unexpected-error exit 1 boundary.

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

Reuse P17D1→IMMUTABLE_RECORD, P17D2→INVALID_STATE_TRANSITION,
P17D3→PROVENANCE_CLOSURE_VIOLATION in uow.py. Named predecessor uniqueness races
retain current normalization; 23503 is referential integrity. 55P03/57014 and
connection/unknown-commit failures remain sanitized INTERNAL_ERROR.

### 11.3 DTO fields, Python types and limits

Frozen dataclasses, strict UUIDs/ints (bool is not int); transports forbid extra
keys and require canonical UUID text. NFC narratives retain meaningful whitespace,
are nonblank, NUL-free, valid UTF-8, 1..16,384 Unicode characters. Bound errors
never truncate records or select an arbitrary prefix.

| Value | Closed fields / bounds |
| --- | --- |
| Existing command fields | `id, project_id, claim_version_id, search_coverage_id: UUID`; `assessment: NoveltyOutcome`; `limitations: str`; `supersedes_assessment_id: UUID | None`; `prior_art_basis: tuple[PriorArtBasisInput,...] = ()`; `scope_statement: str | None`; `closeness_criteria: ClosenessCriteria | None`. |
| ScreeningBasisInput | `probes: tuple[ProbeInput,...]` (1..3,200); `results: tuple[ScreeningResultInput,...]` (0..10,000). Duplicate keys rejected; canonical sorting. |
| ProbeInput | `search_execution_id: UUID`, `query_index: int` 0..31, `disposition: ProbeDisposition`, `rationale: str`. Execution set 1..100; index must exist in saved context. |
| ScreeningResultInput | `search_result_record_id: UUID`, `disposition: ScreeningDisposition`, `criteria_ordinals: tuple[int,...]` (1..100 distinct, 0..99 and within parent's criteria), `rationale: str`, `prior_art_relation_id: UUID | None`, `search_result_resolution_id: UUID | None`. Both references present together for NOT_CLOSE/CLOSE; optional together for UNCLEAR/EXCLUDED; both null for UNRESOLVED. |
| ClosenessCriteria | Existing `statements: tuple[str,...]`, 1..100, combined length ≤16,384. All result rationale/criterion links are authored explanations, not a new rule language. |
| Readback screening basis | Same typed rows with exact HashRef instead of nonnull relation/resolution IDs; nullable only on old/positive shapes. Existing UTC datetime attribution, lowercase 64-hex hash, literal scheme, material_version 1 or 2. No ORM entities. |
| Read query | Existing `ExactReadQuery(project_id: UUID, id: UUID)` only. No caller actor/time/hash/count/version. |

ProbeDisposition = NO_HITS / SCREENED / INCOMPLETE.
ScreeningDisposition = NOT_CLOSE / CLOSE / UNCLEAR / EXCLUDED / UNRESOLVED.
NoveltyOutcome and all six PriorArtKind literals stay as domain/novelty.py.
Existing B22 EMPTY/UNIQUE/AMBIGUOUS selection and existing QualityWarning enums
stay unchanged. New screening diagnostics use the closed booleans in §4 rather
than silently altering coverage quality or warning/hash material.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

One forward migration at the actual linear head, named
`migrations/versions/<next>_b20_screening_basis.py`; do not reserve an obsolete
revision number. No migration is created by this documentation task.

Add `novelty_assessments.screening_captured BOOLEAN NOT NULL DEFAULT FALSE` as a
stored shape discriminator, derived from request shape, not caller controlled.
Replace only `ck_b19_novelty_material` with `ck_b20_novelty_material`: preserve the
original v1 INCONCLUSIVE and v2 CLOSE branches (screening_captured=false); add
v2 INCONCLUSIVE/NO_CLOSE with screening_captured=true and nonnull scope/criteria.
Keep ck_b19_scope/criteria and existing outcome/chain/immutable guards.

Two proposed literature-owned sealed children (all columns NOT NULL unless `?`):

| Table / constraint prefix | Typed columns and keys |
| --- | --- |
| `novelty_assessment_probes` / b20_probe | `id UUID` PK; `novelty_assessment_id UUID` assessment FK; `search_execution_id UUID` execution FK; `query_index INT`; `disposition VARCHAR(16)`; `rationale TEXT`; `created_by UUID` actor FK; `created_at TIMESTAMPTZ`. `pk_b20_probe`, `uq_b20_probe_key` UNIQUE(assessment,execution,query_index), `ck_b20_probe_index` 0..31, `ck_b20_probe_disposition`, `ck_b20_probe_text`. |
| `novelty_assessment_screening_results` / b20_screen | `id UUID` PK; `novelty_assessment_id UUID` assessment FK; `search_result_record_id UUID` result FK; `disposition VARCHAR(16)`; `criteria_ordinals INT[]`; `rationale TEXT`; `prior_art_relation_id UUID ?`; `search_result_resolution_id UUID ?`; `created_by UUID` actor FK; `created_at TIMESTAMPTZ`. `pk_b20_screen`, `uq_b20_screen_result` UNIQUE(assessment,result), `ck_b20_screen_disposition`, `ck_b20_screen_refs`, `ck_b20_screen_ordinals`, `ck_b20_screen_text`. |

For each FK use `fk_<prefix>_<assessment|execution|result|relation|resolution|actor>`
for its applicable column, ON DELETE RESTRICT, and `ix_<prefix>_<target>` unless
already covered by the leading unique key. `ck_*_text` enforces §11.3 NFC/length/
nonblank; ordinals must be one-dimensional, lower bound 1, no null elements,
strictly ascending distinct values in 0..99. Cross-parent criterion bounds belong
to the deferred check. No JSONB, cascade, soft reference or copied source fact.

Owned functions: `b20_child_guard()` checks pr218_capture_prelocked(), native
`xmin = pg_current_xact_id()::xid` parent creation, screening_captured=true and
same actor/time; `b20_complete_screening()` enforces both-direction set equality,
limits, all §§3/11 predicates, exact witness membership and scientific eligibility;
`b20_valid_ordinals(INT[])` validates the array. Attach BEFORE INSERT
`trg_b20_probe_insert`/`trg_b20_screen_insert`; UPDATE/DELETE
`trg_b20_probe_immutable`/`trg_b20_screen_immutable` reuse pr218_immutable().

Attach `trg_b20_parent_complete`, `trg_b20_probe_complete`,
`trg_b20_screen_complete` as AFTER INSERT constraint triggers, DEFERRABLE INITIALLY
DEFERRED (0042 pattern), including a parent trigger to catch wholly omitted children.
Check non-screening parents have no B20 children; screening parents have no B19
positive-basis children. No bypass via ordinary-role SQL or caller-supplied flags.

**B19 integration requiring ADR approval:** b19_complete_basis() currently requires
positive close basis for every v2 row. Keep that function byte-identical; recreate
only `trg_b19_novelty_complete` with `WHEN (NOT NEW.screening_captured)`. The B19
child trigger remains unconditional; b20_complete_screening() rejects B19 children
on screening parents. Preserve trg_b19_novelty_prelocked and its early lock check.
Do not replace any pr218_*, b21_* or b22_* function, or widen the shared lock tuple.
Preflight exact baseline definitions and fail on mismatch. Downgrade refuses any
screening parent/child history, then restores the original B19 parent attachment
and material CHECK, dropping only B20 objects. Never delete or rehash to downgrade.

### 12.2 Exact lock order and transactions

All three existing writes continue taking the following **single first SQL
statement** after choosing READ COMMITTED via connection options. B20 adds no
SHARE lock on an insert destination and no lock-mode upgrade.

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

Then SET LOCAL lock_timeout='10s', statement_timeout='30s'; request advisory lock
`SELECT pg_advisory_xact_lock(hashtextextended(:key,0))`, key
`pr218:{kind}:{canonical UUID}`. No SELECT, SET LOCAL, authorization, advisory or
Claim row lock precedes N. PostgreSQL's configured timeout, not these later SETs,
governs waiting for the first lock; do not promise a 10s first-lock bound.

| Command | Exact operations after N, timeouts and request advisory |
| --- | --- |
| record_search_coverage (kind=coverage) | Existing reader authorization/replay, writer authorization, exact plan and sorted execution/attempt/query/result/resolution capture; parent then sorted execution/resolution children. No target FOR UPDATE. B21 behavior unchanged. |
| record_prior_art_relation (kind=prior_art) | Exact ClaimVersion FOR UPDATE; reader authorization/replay, writer authorization, Claim/source/evidence verification; optional prior-art predecessor FOR UPDATE and successor reread after wait; parent then sorted evidence children. B22 behavior unchanged. |
| record_novelty_assessment (kind=novelty), all shapes | Exact ClaimVersion FOR UPDATE; reader authorization and replay before new-admission checks; writer authorization; exact Claim/coverage; optional assessment predecessor FOR UPDATE and successor reread. For screening: enumerate all exact-plan executions sorted UUID, contexts then attempts/query/results sorted UUID; verify inventory equality/B21 saved membership; inspect result resolution histories and UUID-sorted B22 pair graphs/evidence. No comparison/coverage/probe/result row locks. Recheck eligibility and writer clock; INSERT parent, sorted probes then sorted results (positive shape retains sorted B19 basis inserts). |
| All exact reads and B22 selection reads | begin_formal_read(): one read-only REPEATABLE READ snapshot; authorize, read exact parent/children and dependencies, verify saved material, compute timestamped current diagnostics, final advancing read-entitlement check; no prepare, explicit table/advisory/row locks or canonical writes. |

Claim FOR UPDATE serializes all canonical comparison-root/correction and assessment
writers for that Claim; normal-role parent triggers enforce the same coordination.
N blocks execution/query/result/resolution and validity/authority mutations,
including INSERT phantoms. After every blocking wait re-read with READ COMMITTED
and fresh clock_timestamp(); reread successor/selection before admission. Child
seals prevent late INSERT. No new advisory namespace, project row lock or external call.

All new writes force SET CONSTRAINTS ALL IMMEDIATE, verify readback and recheck
current writer entitlement at fresh database time before commit. Repeat final
checks after any subsequent wait. Replays verify saved material and final reader
entitlement without inserts or new eligibility requirements. Retry only §7's
SQLSTATE-qualified failures, from a fresh UoW with the entire lock/read sequence.

### 12.3 Ordered build steps and module paths

1. Reconcile actual head and approved ADR; add the one §12.1 migration with
   preflight, preserved sibling guards and populated downgrade refusal.
2. Extend `src/researchbase/domain/novelty.py` with closed screening values,
   normalization, outcome-specific literal material and old-shape dispatch. Keep
   Domain free of SQLAlchemy, FastAPI, Typer and external tools.
3. Extend `src/researchbase/application/novelty.py` with §11.3 DTOs, admission,
   historical verification/replay and separate current projections. Extend typed
   NoveltyRepository/UoW ports in `src/researchbase/application/ports.py`.
4. Extend `src/researchbase/persistence/novelty_repository.py` with exact-plan
   enumeration, sorted child reads/inserts and graph queries under existing prepare.
   Wire named constraints through `src/researchbase/persistence/uow.py`; no new
   ORM owner, transaction framework, session leakage or dependencies.
5. Extend closed request/response schemas in `src/researchbase/api/routes.py`
   and existing JSON command conversion in `src/researchbase/cli/commands/literature.py`.
   Reuse `api/app.py` and `cli/composition.py` service wiring. Preserve trusted
   principals, same inputs/output, POST/GET status and sanitized error envelopes.
6. Add §12.4 tests, run focused regressions/static checks and record exact results.
   Leave whole-suite execution to the loop. Stop at B20; no later backlog work.

### 12.4 Test artifacts and required cases

Use exported `tests/integration/phase2/pr2_18_fixtures.py`, `b01_support.py` and
`b19_basis_support.py` builders; real PostgreSQL 18.x disposable databases from
phase2_database_url. Create `b20_screening_support.py` for shared construction;
never treat imported test functions as fixtures. Races use independent engines
and backend PIDs with observed waiting locks, not sleep-only assertions.

| Future file | Required cases |
| --- | --- |
| `tests/unit/phase2/test_b20_screening_contract.py` | Every strict type/extra key, enum, NFC, duplicate, nullable pair, index/ordinal and limit boundary; all outcome/shape combinations; no silent prefix truncation. |
| `tests/unit/phase2/test_b20_screening_hash_vectors.py` | Independent complete literal bytes/digests for negative and screening-INCONCLUSIVE; empty results, Unicode, ordering, changed criterion/reference, mixed-version predecessors; old v1/positive-v2 golden bytes unchanged and no extra null keys. |
| `tests/unit/phase2/test_b20_screening_transports.py` | All §11.2 mappings, HTTP/CLI parity, strict nested schemas, principal injection, first/replay/read 200, sanitized fallback and no nested unauthorized disclosure. |
| `tests/integration/phase2/test_b20_screening_basis.py` | Complete query inventory and all result multiplicities; zero hits valid; zero invocation or uninvoked/undeclared planned provider denies; omitted execution/query/retry/result denies; active/failing/cancelled/unknown/warning-bearing branches retained as incomplete; unresolved/ambiguous, EXCLUDED, PARTIAL_OVERLAP/UNCLEAR and close results deny negative; only exact captured witnesses and UNIQUE usable RELATED/CONTRASTING terminals qualify; verified evidence/hash/byte checks. |
| `tests/integration/phase2/test_b20_screening_replay.py` | Restart and old/mixed-shape exact reads; same-actor replay/order normalization; changed material conflict; different actor/lost read entitlement denies; lost write role or later invalidity still permits authorized historical replay; correction/new root/resolution/execution changes current usability without altering bytes; unknown-commit same UUID recovery. |
| `tests/integration/phase2/test_b20_screening_schema.py` | Catalog types/constraint names; clean and populated upgrade preserves old digests/functions; empty downgrade restores exact B19 trigger/CHECK, populated refusal; normal-role SQL every gate, no prelocks/wrong isolation, omitted children, cross-parent/source/project, late INSERT/update/delete, array null/dimension/order tricks, forced deferred rollback. |
| `tests/integration/phase2/test_b20_screening_concurrency.py` | Both orderings of execution/resolution INSERT and capture; first-lock phantoms; comparison root/correction versus negative admission (Claim serialization); predecessor single successor, same UUID single set; credential revocation and scheduled expiry across waits, final clock; failure after parent/child and deferred checks leaves no partial records; exactly three SQLSTATE retries, no timeout/business/unknown-commit retry. |
| `tests/architecture/test_b20_screening_boundaries.py` | Application-only writes; Domain import boundary, lock-free reads, exact first-statement N, no new semantic JSON/persistence owner, no governance/support/publication side effects; B19/B21/B22 guard definitions and hash compatibility. |

Future focused B20 run: `uv run pytest tests/unit/phase2/test_b20_*.py
 tests/architecture/test_b20_*.py tests/integration/phase2/test_b20_*.py`
(on one shell line). Also run existing B01/B19/B21/B22 and PR2-18 novelty,
PR2-19 novelty and PR2-20 novelty suites, `uv run ruff check .`,
`uv run ruff format --check .`, `uv run pyright`, and unit/architecture tests.
These are future obligations, not claims that B20 tests exist today.

### 12.5 Not in this slice

Prospective preregistration or a new search-plan query schema; automatic query
planning/provider execution; programmable or discipline-specific criteria taxonomy;
replacement of failed/adverse branches; universal novelty/first-ever claims;
source merge deduplication; automatic correction selection across independent
roots; review/Issue/RevisionAction/Decision/Approval gates; READY/package integration;
automatic impact propagation; new Skill/Agent runtime, queues or dependencies.

## 13. Open questions for the owner — override register

| Owner decision required | Proposed decision pinned above |
| --- | --- |
| Is retrospective bounded inventory sufficient? | Yes, explicitly disclose all exact-plan executions visible at admission; no prospective/external completeness claim. Otherwise contract a preregistration slice first. |
| Admit `novelty_assessment_probes`? | Yes, subject to [ADR-0018 Decision 1](ADR-0018_Screening_Negative_Probe_Basis_DRAFT.md#1-owner-decision--admit-novelty_assessment_probes)'s separate schema admission; no new top-level entity. |
| Admit `novelty_assessment_screening_results`? | Yes, subject to [ADR-0018 Decision 2](ADR-0018_Screening_Negative_Probe_Basis_DRAFT.md#2-owner-decision--admit-novelty_assessment_screening_results)'s separate schema admission; no new top-level entity. |
| Conservative failures and comparisons? | Any failed/warning-bearing attempt blocks a negative; RELATED/CONTRASTING with UNIQUE verified basis only. Broader policy requires an approved contract change. |
| Compatible v2 extension and B19 attachment amendment? | Subject to [ADR-0018 Decision 3](ADR-0018_Screening_Negative_Probe_Basis_DRAFT.md#3-owner-decision--compatible-outcome-specific-material-v2) and B20-AQ-02: preserve existing payloads/functions; add closed outcome-specific v2 shape and narrow the B19 parent trigger attachment explicitly. |

All answers are proposed, not owner-approved. An override requires corresponding
body/ADR edits before implementation authorization.

## 14. Documentation verification note

This proposal does not change executable code, migrations, tests or frozen
architecture. Baseline verification commands/results are recorded below after
execution; missing PostgreSQL capability is not PASS. The loop owns full-suite
execution. No B20 or Phase 2 gate success is claimed.

Executed 2026-10-19 in lane41. In the commands below, `P` is the existing shared
repository interpreter; every Python invocation also used `PYTHONPATH=src`:

```sh
P=/Users/fengwang/Documents/ResearchBaseProject/.venv/bin/python
export PYTHONPATH=src
```

| Executed command (with the prefix above) | Observed result |
| --- | --- |
| `UV_CACHE_DIR=/private/tmp/researchbase-b20-uv-cache uv run ruff check .` | Exit 2: uv bootstrap could not download mako==1.4.1; DNS/network unavailable. |
| `$P -m ruff check .` | Exit 0; All checks passed. |
| `$P -m ruff format --check .` | Exit 0; 736 files already formatted. |
| `$P -m pyright` | Exit 1; 1,332 errors, 2 warnings, caused by incomplete lane-local .venv dependency resolution. |
| `$P -m pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject` | Exit 0; 0 errors, 0 warnings, 0 informations. |
| `$P -m pytest tests/unit tests/architecture` | Exit 1; 5,618 passed, 5 failed, 14 errors, 9 warnings, 67.44s. |
| `$P -m pytest tests/unit/phase2/test_pr2_04_static_acceptance.py::test_candidate_static_gates_and_inherited_formatter_delta --tb=short` | Exit 1; 1 failed, 1 warning, 5.10s; its embedded unconfigured pyright sees missing imports. |
| `$P -m pytest tests/unit/test_hg1_runner.py -k 'v2_denial or socket_lifecycle or foreign_peer or incomplete_owner' --tb=short` | Exit 1; 4 failed, 18 deselected, 0.07s; each fails at socket.bind with PermissionError. |
| `git diff --check` | Exit 0. Local-link validation of both proposals found zero missing links. |

The broad unit/architecture run's five failures are exactly the static test and
four runner cases above. Its 14 architecture setup errors require the explicit
RB_TEST_ADMIN_URL PostgreSQL selector, which was unset. No code fix is inferred
from these environment failures. The configured standalone typecheck does not
turn the failed embedded static test into PASS.

Focused dependency run (exact arguments):

```sh
$P -m pytest tests/unit/phase2/test_b01_resolution_contract.py tests/unit/phase2/test_b19_close_prior_art_contract.py tests/unit/phase2/test_b19_close_prior_art_hash_vectors.py tests/unit/phase2/test_b21_capture_contract.py tests/unit/phase2/test_b21_capture_hash_vectors.py tests/unit/phase2/test_b22_prior_art_contract.py tests/unit/phase2/test_b22_prior_art_hash_vectors.py tests/unit/phase2/test_b22_prior_art_transports.py tests/unit/phase2/test_pr2_18_novelty_contract.py tests/architecture/test_b01_resolution_boundaries.py tests/architecture/test_b19_close_prior_art_boundaries.py tests/architecture/test_b21_capture_boundaries.py tests/architecture/test_b22_prior_art_boundaries.py --tb=short
```

Observed: **192 passed in 3.16s**, exit 0.

Focused PostgreSQL dependency run (output redirected to
`/private/tmp/b20-postgres.txt`; exact arguments):

```sh
DATABASE_URL=postgresql+psycopg://researchbase:researchbase@localhost:5432/researchbase $P -m pytest tests/integration/phase2/test_b01_resolution_admission.py tests/integration/phase2/test_b19_close_prior_art_basis.py tests/integration/phase2/test_b19_close_prior_art_schema.py tests/integration/phase2/test_b19_close_prior_art_concurrency.py tests/integration/phase2/test_b21_capture.py tests/integration/phase2/test_b21_capture_schema.py tests/integration/phase2/test_b21_capture_concurrency.py tests/integration/phase2/test_b22_prior_art_correction.py tests/integration/phase2/test_b22_prior_art_selection.py tests/integration/phase2/test_b22_prior_art_concurrency.py tests/integration/phase2/test_pr2_19_novelty.py tests/integration/phase2/test_pr2_20_novelty.py --tb=short
```

Observed: **175 setup errors, 3 warnings in 32.27s**, exit 1. Connections to
localhost:5432 fail with Operation not permitted; no PostgreSQL test body passed.
Local recovery attempts also failed (exit 1):

```sh
/opt/homebrew/opt/postgresql@18/bin/initdb -D /private/tmp/rb-b20-pg -A trust --no-locale
/opt/homebrew/opt/postgresql@18/bin/initdb -D /private/tmp/rb-b20-pg -A trust --no-locale --encoding=UTF8 -c shared_memory_type=mmap -c dynamic_shared_memory_type=posix
```

Both reported shared-memory allocation failure (shmget: No space left on device)
and removed the failed temporary cluster. PostgreSQL verification is **blocked**,
not PASS. Full suite was not run; no implementation tests for proposed B20 exist.
