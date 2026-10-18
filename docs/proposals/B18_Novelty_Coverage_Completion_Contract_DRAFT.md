# B18 PR2-18 Coverage / Prior-art / INCONCLUSIVE Completion (S1) — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

## Start here (for the implementer)

**The S1 product is already implemented. No new command, DTO, table, column,
migration or persistence mechanism remains for B18.** The remaining delta is
consumer test/evidence integration: PR2-19 still lists novelty as a G7 blocker;
PR2-20's benchmark has no coverage/prior-art/novelty cases. Existing PR2-18 and
B01 tests already exercise resolution/capture phantoms. Do not rebuild them.

After owner approval and separate execution authorization:

1. Reconfirm the baseline in §1 and preserve the existing contracts in §11.
2. Add only the novelty branch of G7 through existing Application commands;
   keep package/readiness/consent prerequisites separately accounted for (§12.3).
3. Add bounded novelty benchmark cases and reuse the existing phantom tests;
   preserve exact saved hashes/counts and current diagnostics (§12.4).
4. Record executed checks and remaining blockers, then stop. B18 S1 evidence
   cannot establish full G7, full PR2-18 or Phase 2 acceptance.

“Serializable capture” in the backlog means a capture with a legal serialization
order. It does **not** require PostgreSQL SERIALIZABLE isolation: the accepted
implementation uses READ COMMITTED with preheld SHARE locks as its first SQL
statement. Reads use one read-only REPEATABLE READ snapshot and no explicit
table, advisory or row locks. Do not copy the older PR2-18 draft's Claim-before-N
ordering: the current adapter takes N first for **all three** writes (§12.2).

## 1. Purpose, authority and inspected baseline

Read authority in AGENTS.md order: Architecture [01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md)
§§3, 34; Addendum [02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md);
Registry [03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), literature assessments;
Compatibility [08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md)
§§9–18, 24; Phase 2 [05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md)
§25, PR2-18; [Harness §2](../harness/09_Harness_Integration_Specification_v1.0.md).
Correction [12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md),
Field Contract [13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md) rows 68–70,
and literal Hash Contract [15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md)
fix exact references, immutable assessments and material version 1. Temporal
[19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md)
requires advancing DB time after waits. No PR2-18 execution pack was found in
`execution/phase2/`; this draft supplies no execution authorization.

| Inspected source | Already implemented / remaining distinction |
| --- | --- |
| [domain/novelty.py](../../src/researchbase/domain/novelty.py), [application/novelty.py](../../src/researchbase/application/novelty.py) | Literal R2 hashes; three recording commands and three exact-ID reads; accounting, verified comparisons, INCONCLUSIVE guard, immutable replay and same-Claim nonforking supersession. |
| [novelty_repository.py](../../src/researchbase/persistence/novelty_repository.py), [uow.py](../../src/researchbase/persistence/uow.py) | First-statement N SHARE locks, READ COMMITTED writes, three SQLSTATE-qualified attempts, formal lock-free snapshot reads and named error normalization. |
| [0047](../../migrations/versions/0047_pr2_18_novelty_prior_art.py) | Five tables, concrete RESTRICT FKs, sealed child sets, deferred completeness/accounting/verification guards, stronger-outcome CHECK and populated-downgrade refusal. |
| [B01 migration 0050](../../migrations/versions/0050_b01_resolution_admission.py), [B01 contract](B01_Search_Result_Resolution_Contract_DRAFT.md) | Existing resolution admission plus deferred `b01_resolution_closure_at_commit`; reuse it, including all historical resolution rows. |
| [API routes](../../src/researchbase/api/routes.py), [literature CLI](../../src/researchbase/cli/commands/literature.py) | Three POST/GET pairs under `/v1/projects/{project_id}` and six literature CLI commands already exist. |
| [G7 dependency inventory](../../tests/integration/phase2/test_pr2_19_dependencies.py), [scenario support](../../tests/integration/phase2/pr2_19_support.py), [benchmark](../../tests/e2e/test_pr2_20_benchmark.py) | Frozen G7 blocker includes “PR2-18 novelty”; G7 command set is empty; benchmark CASES has eight non-novelty cases. Consumer coverage remains absent. |

[PR2-18 verification](../../pr_evidence/PR2-18/VERIFICATION.md) is historical evidence,
not a fresh pass. The approved [PR2-17](PR2-17_Submission_Authorship_Contract_DRAFT.md)
and [PR2-18](PR2-18_Novelty_PriorArt_Contract_DRAFT.md) drafts supply this document's
structure; their old inspected-baseline paragraphs are not today's inventory.

## 2. Scope, dependency boundaries and non-goals

Proposed delta: test/evidence wiring only for accepted S1 behavior. Dependencies
B01 and PR2-18 S1 exist in code and migrations. Full G7 also depends on publication
work; presence of that code does not make its acceptance part of B18. Preserve
the existing owning services and evidence formats. This task changes this file only.

## 3. Invariants and conservative judgments

Coverage is the caller's exact selected terminal-execution set, not exhaustive
search. Count retained query and result records, including retry/failure history;
providers are actually invoked providers. A result resolves only when all its
resolution rows agree on one nonnull exact source/version; count distinct source
IDs, without merge deduplication. A source-only row plus a later B01 exact row
remains ambiguous. Zero invocation stays explicit. Captured counts never change;
captured unresolved count remains unknown, separate from timestamped current quality.

Prior art binds one exact frozen ClaimVersion and SourceVersion plus independently
HUMAN-VERIFIED, same-project evidence for that exact source, with verified hashes
and current usable inputs at admission. Contradictory comparisons remain history.
INCONCLUSIVE is the only admitted assessment. Authority, similarity or retrieval
success cannot establish universal priority or override deterministic invalidity.

## 4. Commands, DTOs and historical readback

Retain exactly `record_search_coverage`, `record_prior_art_relation`,
`record_novelty_assessment` and their `read_*` counterparts in `NoveltyService`:
`read_search_coverage`, `read_prior_art_relation`, `read_novelty_assessment`.
No list, edit, screening or conclusive-outcome command is added. POST first write
and replay return 200, GET returns 200; CLI uses existing envelopes.
Current readers are OWNER/RESEARCHER/REVIEWER/VIEWER/APPROVER; new writes require
OWNER/RESEARCHER. Same-actor exact replay requires current read entitlement;
changed normalized request material conflicts. Nested reads retain their own checks.

## 5. Schema and literal hash contract

No schema delta. Preserve `sha256-cjson-v1`, material version 1 and the three
literal payloads in Architecture 15. Quality, observation time and current
validity are projections, never new material keys. No capture-basis JSON owner,
historical unresolved-count backfill or new assessment-to-comparison relation.

## 6. Error contract

No new ErrorCode. Use §11.2's existing transport mappings and UoW normalization.
An unknown commit is recovered by the same exact UUID after checking entitlement;
never issue a new UUID to hide uncertainty.

## 7. Transactions, concurrency and failure recovery

One command is one synchronous PostgreSQL transaction through Application →
repository/UoW → adapter. Keep §12.2's locks and advancing authorization time.
Retry only SQLSTATE 40001/40P01, at most three fresh UoWs, no delay or external call.
Unique-predecessor loss, business conflicts, timeouts and uncertain commits are
not automatic retries. Reads create no record and take no explicit locks.

## 8. Tests after authorization — remaining consumer evidence

Retain the existing PR2-18/B01 suites (§12.4). A new G7 novelty test must use real
owning commands and retain exact IDs/hashes across restart, denials and later
resolution changes. A dependency-presence assertion is not execution evidence.
Benchmark timing must invoke the same Application methods and compare complete
DTOs and zero unintended scientific/governance effects, not merely fast SQL.

## 9. Acceptance criteria and evidence boundary

Product delta: **none**. Remaining consumer evidence is complete only when actual
G7 novelty operations, bounded benchmark samples and observed phantom orderings
are recorded with exact commands/counts. Preserve other G7 blockers. A small
local correctness run is not a large-profile benchmark PASS. Full-suite execution
belongs to the loop; neither this proposal nor historical evidence declares a gate.

## 10. Glossary

| Term | Meaning |
| --- | --- |
| S1 | Coverage + six verified comparison kinds + INCONCLUSIVE only. |
| N | Ordered SHARE-lock table tuple exported by novelty_repository.py; expanded in §12.2. |
| Phantom | Concurrent INSERT into a captured range, including an initially empty resolution history. |
| G7 | PR2-19 combined package/authorship/consent and novelty scenario; B18 covers only its novelty branch. |
| Captured / current | Immutable saved material / timestamped diagnostics from a later read snapshot. |

## 11. Decisions taken in this draft

### 11.1 Scope and policy decisions

Accept the existing product contract without expansion; propose only consumer
evidence integration. Retain both stronger registered enum literals for validation
compatibility while denying their admission in Application and PostgreSQL.
The stale consumer “SERIALIZABLE retry” wording does not override the accepted
READ COMMITTED/preheld-lock capture protocol. No new dependency is required.

### 11.2 Pinned error mappings

Mappings are from [api/errors.py](../../src/researchbase/api/errors.py) and
[cli/errors.py](../../src/researchbase/cli/errors.py); INTERNAL_ERROR is a fallback,
not an ErrorCode. Novelty selects CLI exit 1 through the shared invocation option.

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

Stronger outcomes and unverified evidence emit INVALID_STATE_TRANSITION; corrupted
hashes/exact closure emit PROVENANCE_CLOSURE_VIOLATION. Never invent HASH_MISMATCH.
Exhausted retryable SQLSTATEs or unique-predecessor races emit CONCURRENT_MODIFICATION;
55P03/57014 and connection/unknown-commit failures use sanitized INTERNAL_ERROR.

### 11.3 DTO fields, Python types and limits

All existing commands are frozen dataclasses; transports forbid extra fields.
Every `id`/`*_id` below is strict `UUID`; authenticated actor/time are derived.

| DTO | Caller fields beyond `id: UUID, project_id: UUID` |
| --- | --- |
| RecordSearchCoverageCommand | `search_plan_version_id: UUID`, `search_execution_ids: tuple[UUID, ...]`, `coverage_limitations: str` |
| RecordPriorArtRelationCommand | `claim_version_id: UUID`, `source_version_id: UUID`, `relation: PriorArtKind`, `rationale: str`, `literature_evidence_ids: tuple[UUID, ...]` |
| RecordNoveltyAssessmentCommand | `claim_version_id: UUID`, `search_coverage_id: UUID`, `assessment: NoveltyOutcome`, `limitations: str`, `supersedes_assessment_id: UUID | None = None` |
| ExactReadQuery | No additional fields. |

UUID sets contain 1..100 distinct values, sorted canonically. Narrative is NFC,
nonblank, valid UTF-8, NUL-free, 1..16,384 Unicode characters; whitespace is retained.
Derived counts are strict `int` in 0..2,147,483,647, resolved ≤ results; provider
strings are NFC nonblank ≤128 characters. Derived `TimeScope | None` has exactly
`from_date: date | None`, `through_date: date | None`, at least one bound, ordered;
wire/material keys are `from`/`through` ISO dates. Caller cannot supply accounting.

PriorArtKind is IDENTICAL/HIGHLY_SIMILAR/PARTIAL_OVERLAP/RELATED/CONTRASTING/UNCLEAR.
NoveltyOutcome is INCONCLUSIVE/CLOSE_PRIOR_ART_FOUND/NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE;
only the first may persist. QualityWarning is NO_INVOKED_QUERIES/FAILED_ATTEMPT/
CANCELLED_ATTEMPT/UNKNOWN_ATTEMPT/UNINVOKED_PROVIDER/PARTIAL_RESULTS/
UNRESOLVED_RESULTS/FILTER_COMPLIANCE_UNPROVEN/SCREENING_NOT_CAPTURED/
INPUT_CURRENTLY_UNUSABLE. AttemptQuality status is RESERVED/SUCCEEDED/
RETRYABLE_FAILURE/PERMANENT_FAILURE/CANCELLED/UNKNOWN.
Readback uses UUIDs, typed HashRef tuples with lowercase 64-hex `content_hash: str`,
UTC `datetime` timestamps, `hash_scheme: Literal['sha256-cjson-v1']`, integer counts,
and existing typed nested quality/validity. In CoverageQuality,
`captured_unresolved_result_count: None`, `current_unresolved_result_count: int`,
`selected_scope: Literal[True]`, `screening_captured: Literal[False]` stay explicit.
Novelty predecessor/successor navigation IDs remain `UUID | None`; no “latest wins.”

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

**DDL to execute: none.** Existing 0047 uses UUID PK/FKs with ON DELETE RESTRICT,
TIMESTAMPTZ attribution, TEXT narratives, CHAR(64) hashes and VARCHAR(32) schemes.
The following is an inventory, not a replacement migration:

| Existing table | Material types and named guards |
| --- | --- |
| search_coverage | Plan UUID; providers JSONB; three INT counts; nullable time_scope JSONB; coverage_limitations TEXT. `ck_pr218_coverage_counts`, `ck_pr218_coverage_providers`, `ck_pr218_coverage_time_scope`, `ck_pr218_coverage_text`. |
| search_coverage_executions | Coverage/execution UUIDs; `uq_pr218_coverage_execution_pair`. |
| prior_art_relations | Claim/source/assessor UUIDs; relation VARCHAR(32); rationale TEXT; `ck_pr218_prior_art_relation`, `ck_pr218_prior_art_assessor`, `ck_pr218_prior_art_text`. |
| prior_art_evidence_inputs | Relation/evidence UUIDs; `uq_pr218_prior_art_input_pair`. |
| novelty_assessments | Claim/coverage/assessor UUIDs; assessment VARCHAR(40); limitations TEXT; nullable predecessor UUID; `ck_pr218_novelty_outcome`, `ck_pr218_novelty_initial_slice`, `ck_pr218_novelty_not_self`, `ck_pr218_novelty_assessor`, `ck_pr218_novelty_text`; partial unique index `uq_pr218_novelty_predecessor`. |

Keep existing `trg_pr218_<table>_immutable`, parent/child guards and
`trg_pr218_novelty_chain`. Completeness triggers
`trg_pr218_search_coverage_complete_coverage`,
`trg_pr218_search_coverage_executions_complete_coverage`,
`trg_pr218_prior_art_relations_complete_prior_art` and
`trg_pr218_prior_art_evidence_inputs_complete_prior_art` are constraint triggers,
DEFERRABLE INITIALLY DEFERRED, following the repository pattern in
[0042](../../migrations/versions/0042_pr2_15_minimal_decision.py).
Preserve `pr218_capture_prelocked()` isolation/granted-lock check and 0050's B01
closure trigger. No disabling, historical rewrites or outcome-guard removal.

### 12.2 Exact lock order and transactions

For all three writes, existing `SqlAlchemyNoveltyRepository.prepare` first selects
READ COMMITTED via connection options (no query), then executes one statement:

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

No SELECT, SET LOCAL, authorization or advisory lock precedes it. Then set local
lock_timeout=10s and statement_timeout=30s; acquire request advisory lock via
`pg_advisory_xact_lock(hashtextextended(:key,0))`, where key is
`pr218:{kind}:{canonical UUID}`. There is no lock upgrade.

| Command | Operations after N and timeouts |
| --- | --- |
| record_search_coverage | `kind=coverage` advisory; reader authorization at DB clock; replay check; writer authorization if new; exact plan and sorted execution/attempt/query/result/resolution capture; writer recheck; parent then sorted execution children INSERT. No target FOR UPDATE. |
| record_prior_art_relation | `kind=prior_art` advisory; exact ClaimVersion FOR UPDATE; reader authorization/replay; writer authorization; exact Claim/source and sorted evidence validation; writer recheck; parent then sorted evidence children INSERT. |
| record_novelty_assessment | `kind=novelty` advisory; exact ClaimVersion FOR UPDATE; reader authorization/replay; writer authorization; INCONCLUSIVE guard, exact Claim/coverage validation; optional predecessor FOR UPDATE, same-Claim/successor recheck; writer recheck; parent INSERT. |

New writes then force `SET CONSTRAINTS ALL IMMEDIATE`, read back/verify, recheck
writer entitlement at fresh `clock_timestamp()`, commit. Replays verify saved
material, recheck current reader entitlement and return without inserts. Every
retry repeats the full sequence. No external call occurs in the transaction.
All exact reads use `begin_formal_read()` (read-only REPEATABLE READ), authorize,
read parent/children/dependencies and current projections within that snapshot,
then recheck current read entitlement with advancing time. They never call prepare,
take explicit table/advisory/row locks, or perform canonical writes.

### 12.3 Ordered build steps and real file paths

1. Reconcile code, 0047/0050 and existing tests; record that production delta is
   empty. Do not edit domain/application/persistence or create a migration.
2. Add `tests/integration/phase2/test_pr2_19_novelty.py`, reusing exported builders
   in `pr2_18_fixtures.py` and B01's `b01_support.py`. Construct through existing
   services, including real retained artifact bytes and independent verification.
3. Extend `tests/integration/phase2/pr2_19_support.py` command allowlists for the
   three NoveltyService recording methods and exact reads. Update
   `test_pr2_19_dependencies.py` and the corresponding PR2-19 proposal matrix
   together: remove only the proven novelty blocker, retaining other prerequisites.
   A novelty subscenario PASS must not mark combined G7 PASS.
4. Add `tests/integration/phase2/test_pr2_20_novelty.py` for small correctness,
   parity and phantom references. Extend `tests/e2e/test_pr2_20_benchmark.py`
   through existing `pr2_20_support.py` evidence/profile helpers. Update the
   PR2-20 draft's stale novelty/SERIALIZABLE dependency wording in that later PR.
5. Run focused suites and record immutable IDs/hashes, counts, DB version, actual
   waits and any unavailable measurements. Stop at the S1 evidence boundary.

### 12.4 Test files and required cases

| File / suite | Required evidence |
| --- | --- |
| Existing `tests/unit/phase2/test_pr2_18_*.py`, `tests/architecture/test_pr2_18_boundaries.py` | Closed DTO bounds/enums, independent hash vectors, transport mappings and architecture invariants remain passing. |
| Existing `tests/integration/phase2/test_pr2_18_*.py` | Capture accounting/restart; six verified comparisons and contradiction retention; stronger Application/normal-role SQL denial with no row; sealed/deferred guards; replay, expiry, rollback and exact lock-free reads. |
| Existing `test_b01_resolution_concurrency.py` | `test_both_coverage_commit_orders_and_empty_history_phantom` and `test_b01_append_after_source_only_stays_ambiguous`: actual resolution admission, both commit orders, empty range and honest ambiguity. |
| New `test_pr2_19_novelty.py` | Coverage → exact verified comparison → INCONCLUSIVE → restart exact reads; all three hashes and attribution retained; changed-input conflict, wrong-project/unverified/stronger-outcome denial; later B01 resolution alters only current diagnostics. No package/send/support/review/grant side effect. |
| New `test_pr2_20_novelty.py`, extended benchmark | First-write/replay/read parity for all three methods; saved counts/hash equality across later resolution; refer to observed two-backend phantom regressions, never infer exclusion from elapsed time alone. |

Proposed bounded benchmark defaults: reuse existing small fixture infrastructure,
one selected execution, one query, two results, one exact resolved source and one
unresolved result; one independently verified evidence input and one frozen Claim.
Use nine cases (first-write/replay/read × coverage/prior-art/novelty), new UUIDs
for first writes, retained UUIDs for replays. Setup/verification are outside timing.
Reuse the existing profile's warmups, repetitions, 1/4-worker sampling and evidence
format; per-worker fresh writes must not build an unintended supersession chain.
Record these exact cardinalities separately from existing source/trace counts.
This is a bounded extension; no production-scale novelty latency target is invented.
Do not label the existing eight-case benchmark as novelty evidence or a skipped/
unavailable large run as PASS. Existing full G7/publication blockers stay explicit.

### 12.5 Not in this slice

Stronger outcomes, exhaustive intended-probe inventory, screening dispositions,
negative-probe persistence, exact historical unresolved counts, new hash material,
authoritative prior-art correction selection, new review/Decision/Approval targets,
automatic impact propagation and publication workflow implementation remain outside
B18. They require separately approved contracts; none is needed to preserve S1.

## 13. Open questions for the owner — override register

Proposed disposition: close the product portion as already implemented, authorize
only the consumer evidence delta above, and retain all broader acceptance blockers.
The bounded benchmark defaults in §12.4 require owner approval with this draft.
Contract approval and implementation authorization remain distinct.

## 14. Documentation verification note

Observed 2026-10-18, documentation only. Dependency bootstrap could not download
httpcore2 (DNS/network restriction). Checks therefore used the existing environment,
with current-checkout imports, via this common prefix:

```sh
export PYTHONPATH="$PWD/src:$PWD"
export VIRTUAL_ENV=/Users/fengwang/Documents/ResearchBaseProject/.venv
export UV_CACHE_DIR="$PWD/.data/uv-cache"
```

| Exact command after prefix | Observed result |
| --- | --- |
| `uv run --active --no-sync ruff check .` | PASS; all checks passed. |
| `uv run --active --no-sync ruff format --check .` | PASS; 639 files already formatted. |
| `uv run --active --no-sync pyright` | PASS; 0 errors, 0 warnings, 0 informations. |
| `uv run --active --no-sync pytest tests/unit tests/architecture tests/test_architecture.py` | 5,116 passed, 5 failed, 12 errors, 8 warnings in 61.29s; exit 1. Four runner failures involve denied Unix socket operations; twelve PR2-19 architecture setup errors lack the DB admin selector. The static-acceptance failure was environment resolution, subsequently rerun below. |
| `uv run --active --no-sync pytest tests/unit/phase2/test_pr2_04_static_acceptance.py::test_candidate_static_gates_and_inherited_formatter_delta` | 1 passed, 1 warning in 7.41s after environment resolution; exit 0. |
| `uv run --active --no-sync pytest tests/unit/phase2/test_pr2_18_*.py tests/unit/phase2/test_b01_*.py tests/architecture/test_pr2_18_boundaries.py tests/architecture/test_b01_resolution_boundaries.py tests/integration/phase2/test_pr2_19_dependencies.py` | 127 passed in 1.23s; exit 0. |
| `DATABASE_URL=postgresql+psycopg:///postgres RB_TEST_ADMIN_URL=postgresql+psycopg:///postgres uv run --active --no-sync pytest -x tests/integration/phase2/test_pr2_18_*.py tests/integration/phase2/test_b01_resolution_*.py` | 1 setup error, 1 warning in 0.49s; exit 1. Local PostgreSQL socket access denied: Operation not permitted. Stopped before any case passed; remaining DB cases not run. |
| `git diff --check` | PASS; no output. |

Initial Pyright attempt with `--pythonpath` still selected the empty local venv
from repository configuration (1,145 errors, 2 warnings). A temporary local venv
link to the existing environment resolved that configuration; the passing Pyright
and static-acceptance rerun above followed. The temporary link was removed.
No executable/configuration/dependency files were changed. No fresh PostgreSQL
server version or database acceptance is claimed. Historical PR2-18 counts are
not reused as a pass. The loop owns the whole-suite run; it was not run here.
