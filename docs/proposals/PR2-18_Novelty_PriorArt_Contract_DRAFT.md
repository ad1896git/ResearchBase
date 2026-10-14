# PR2-18 Novelty / Prior Art Basic Contract — DRAFT

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

**Scope:** documentation proposal only. This document is not an architecture
freeze, ADR, execution pack, migration authorization, scientific finding, owner
approval or PR2-18 acceptance declaration. Proposed refinements require owner
approval and consistency review before separate implementation authorization.

## 1. Purpose, authority and inspected baseline

PR2-18 records what was searched, how exact prior-art sources relate to an exact
ClaimVersion, and how narrowly a novelty judgment can be stated. It must preserve
negative probes, failed retrieval and uncertainty. “No result was returned” never
means “no prior work exists”; a similarity judgment is not scientific support,
priority proof, review completion or permission to release a result.

| Source | Constraint carried into this proposal |
| --- | --- |
| [System Architecture 01](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), §§3, 7–12, 32–34 | One canonical fact owner, immutable exact provenance; preserve search, screening and negative novelty probes; novelty strength cannot exceed coverage. |
| [Correction Addendum 02](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), A2–A4, A10, A12, A18–A23 | LiteratureSearchExecution naming; canonical collections use concrete relations; uppercase enums; R2 precedence, advancing post-lock authorization and bounded Decision semantics. |
| [Global Registry 03](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), Phase 2 rows | Literature owns PriorArtRelation, SearchCoverage and NoveltyAssessment as immutable records/assessments, not new Version identities. |
| [Cross-Phase Contracts 08](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), §§9–18, 24, 30, 38, 40–41, 50 | Stable commands/errors/hashes, concrete frozen refs, additive compatibility, common Application boundary, source lineage and golden regressions. |
| [Phase 2 Specification 05](../architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md), §§25, 35, PR2-18, §49, P2-INV-017 | Three basic objects, explicit quality report and bounded novelty wording; all thirteen §49 architecture tests remain obligations. |
| [Phase 2 Correction 12](../architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md), §§2, 4, 7 | Exact Claim/Source/Coverage references, append-only supersession and own material hashes; no first-ever inference. |
| [Field Contract 13](../architecture/13_Phase2_Schema_Field_Contract_v1.0.md), novelty rows; [Hash R2 15](../architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md), common encoding and literature/search templates | Five already named tables, closed time-range, three novelty outcomes and literal v1 hash payloads. No extra keys or semantic JSON core. |
| [RevisionAction PR2-15 base](PR2-15_RevisionAction_Contract_DRAFT.md); [Basic Approval PR2-16 base](PR2-16_Basic_Approval_Contract_DRAFT.md) | Completed revision trace is separate from Issue disposition; approval/grant is separate from scientific fact and external effect. |
| [Minimal Decision Contract 20](../architecture/20_PR2_15_Minimal_Decision_Command_Contract_v1.0.md) | Existing INTERNAL_SCIENTIFIC_RELEASE/PROCEED neither resolves novelty concerns nor authorizes revision-purpose Decisions. |

For this task, the owner identifies PR2-15/16 as approved on **2026-10-14** and
under implementation; they are the contract base PR2-18 builds on. Their checked-in
headers and verification sections still say DRAFT and 2026-10-13. This proposal
does not edit that metadata or infer completed engineering/gate acceptance from
owner contract approval. Verification below uses the actual checkout baseline.

Inspected code provides:

- [Search execution domain](../../src/researchbase/domain/literature_search_execution.py)
  and [Application service](../../src/researchbase/application/literature_search_execution.py):
  exact plan binding, provider attempts, query/result history and terminal
  SUCCEEDED/FAILED/CANCELLED/UNKNOWN states. Retrieval is not a scientific Run.
- [Metadata observation service](../../src/researchbase/application/metadata_observation.py)
  and [repository](../../src/researchbase/persistence/metadata_observation_repository.py):
  append-only SearchResultResolution, including nullable SourceVersion binding.
  Terminal retrieval does not prevent later resolution records.
- [Literature evidence service](../../src/researchbase/application/literature_evidence.py)
  and [material](../../src/researchbase/domain/literature_evidence.py): immutable
  source-backed quotation material, separately controlled verification and
  LiteratureSupportSnapshot. Source/result identity is not LiteratureEvidence.
- [Internal review](../../src/researchbase/application/internal_review.py) and
  [Decision service](../../src/researchbase/application/decision.py): exact frozen
  Claim/conclusion reviews with initial OPEN Issues and minimal conclusion
  PROCEED. No novelty-target review, screening completion or Issue disposition
  command is inferred. No PR2-18 commands/tables were found in the inspected code.

## 2. Scope, dependency boundaries and non-goals

Propose `record_search_coverage`, `record_prior_art_relation`,
`record_novelty_assessment` and authorized exact-ID read queries. All record
already completed observations; none starts retrieval, imports a source,
extracts/verifies evidence, freezes a Claim or performs a revision.

The proposed initial slice admits immutable coverage, six source-comparison
relations, and **INCONCLUSIVE** NoveltyAssessment. The full registered enum is
retained, but NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE and CLOSE_PRIOR_ART_FOUND remain
unavailable until an exact assessment-basis contract is approved (§3.3). This is
a conservative scope recommendation for owner approval, not a silent reduction
of full PR2-18 acceptance. Every unavailable path denies before writing.

| Dependency | Required contract/evidence; no later work imported into this PR |
| --- | --- |
| Phase 1 Claim/closure and PR2-00 | Exact frozen Claim closure; enrolled active project, trusted identity, membership, roles and read access. |
| PR2-01/02 source identity/lineage | Explicit project source access, exact frozen SourceVersion, correction/retraction/merge history; never reparent historical refs. |
| PR2-03/04 search | Exact frozen plan; durable attempts/query/results and terminal guards. Failed and UNKNOWN attempts remain visible. |
| PR2-05/06 evidence and verification capability | Existing source-backed evidence and authorized independent verification; capability evidence governs, not ticket-number assumption. No automatic promotion of snippets. |
| PR2-14 review | Preserve initial OPEN novelty/overclaim Issues. Existing target policy is not expanded to NoveltyAssessment by this draft. |
| Owner-approved PR2-15 RevisionAction base | A completed Claim/source/manuscript correction retains exact old concern and new result. A new novelty assessment is not one of its seven result shapes; do not invent an eighth. |
| Owner-approved PR2-16 Approval base | Novelty cannot satisfy PROCEED/review/approval gates or consume a grant. Later invalidity and blockers remain independently enforced. |
| PR2-11/12/13 and PR2-17 | Downstream conclusion/manuscript/package consumers preserve exact evidence/placement closure; no automatic attachment or novelty-based READY transition. PR2-17 implementation is not a prerequisite for this basic literature slice. |
| PR2-19/20 and later phases | E2E/failure injection and hardening will exercise these contracts. Advanced novelty campaigns, runtime orchestration and automated priority discovery remain later work. |

Non-goals: patent/legal novelty advice, first-ever/world-first proof, comprehensive
or systematic-review certification, global novelty score, embedding thresholds,
automatic similarity classification, new search providers, screening subsystem,
Agent Runtime, queues/vector DBs, new dependencies, mutable novelty status,
Approval consumption, Issue resolution, publication release or ExternalEffect.
This task adds no migration, code, executable test or governing-file edit.

## 3. Invariants and conservative judgments

1. **Exact subject.** PriorArtRelation and NoveltyAssessment bind one exact
   ClaimVersion. A new Claim version requires a new root assessment; no current
   pointer substitution or copied old judgment. Hypothesis != Claim and
   ScientificConclusion != Claim; those are not alternative input types.
2. **Fact precedence and separation.** SearchResult, source title, citation,
   search score, Agent answer, review vote and approval cannot establish novelty
   or scientific support. Recording prior art does not create EvidenceRelation,
   LiteratureSupportSnapshot, manuscript placement, Review, Decision, Approval,
   RevisionAction, IssueEvent or effect. Phase 1 hashes remain unchanged.
3. **Immutable material.** Coverage, relation and assessment material and child
   memberships seal in their creation transaction. No UPDATE/DELETE or Version
   table. Assessment correction appends a superseding assessment; old judgments,
   sources, evidence and coverage remain readable. Supersession is not invalidation
   of an exact historical reference.
4. **Project access.** Scope derives through Claim ownership or the coverage's
   search plan, with agreement across all inputs. Global source identity/merge
   does not confer project access. Evidence belongs to this project and the exact
   stated SourceVersion; title similarity and a shared source parent are insufficient.
5. **Attribution.** `assessed_by` is the trusted authenticated caller; caller
   payload cannot nominate a HUMAN assessor. Proposed writers are effective
   OWNER/RESEARCHER with ACTIVE membership/live verified credential. Human and
   Agent use identical commands. A recorded Agent judgment remains attributable
   judgment, not independent Human review or automatically VERIFIED evidence.
6. **Validity and limits.** First relation/assessment admission verifies frozen
   material, hashes and current validity. A valid frozen SUPERSEDED version remains
   an exact historical input. Retracted/invalid source or DISPUTED/REJECTED evidence
   denies first comparison admission; a later change leaves saved bytes intact
   and yields an explicit derived warning/unusable-for-current-judgment projection.
   Do not silently replace it with a corrected source or delete adverse prior art.
7. **Quality report.** Every novelty read reports exact plan, actual providers,
   query/result counts, time range, resolved source count, unresolved result count,
   attempt outcomes/warnings and nonblank coverage/assessment limitations. Null
   time scope means unspecified, never all time. No read advertises exhaustive
   coverage or priority; even a future NO_CLOSE outcome uses bounded wording.

### 3.1 SearchCoverage accounting — proposed definitions

Use a nonempty duplicate-free set of already terminal executions, all from the
same project and **same exact frozen plan version**. Include failed, cancelled
and UNKNOWN executions in declared scope, with their retained history; do not
turn their lack of returned records into successful negative queries. PLANNED,
RUNNING, outstanding RESERVED attempts or inconsistent terminal history deny.

| Material | Proposed deterministic definition at capture |
| --- | --- |
| `query_count` | Count persisted SearchQueryRecord rows in the selected executions, including invoked failed attempts that have such a row. Retries with distinct records count separately. Not planned query count or unique query text count. |
| `result_count` | Count persisted SearchResultRecord rows under those queries. Provider duplicates/repeated hits remain separate returned observations, not unique publications. |
| `resolved_source_count` | Count distinct exact LiteratureSource IDs among unambiguously resolved results in scope. Require a nonnull accessible frozen SourceVersion and verified resolution material; source-only or conflicting resolution bindings do not qualify. Never deduplicate through a later MERGED/current pointer. |
| `providers` | Sorted NFC provider identifiers with actually invoked persisted query records. Planned-but-uninvoked providers are reported separately as limitations; no padding with the plan's list. Provider versions remain in attempt/query provenance. |
| `time_scope` | Server-derived exact plan `time_range`, null if absent. This is intended publication-date scope, not proof providers honored filters and not execution elapsed time. Filter compliance gaps remain explicit. |
| `coverage_limitations` | Required nonblank NFC narrative. Include failed/unknown attempts, truncation/partial coverage, missing providers, language/date/index limits, unresolved/ambiguous hits and absent screening. No comprehensive/systematic/first-ever assertion. |

Readback also exposes **captured unresolved-result count**, derived at creation
as result rows minus unambiguously resolved result rows. It is not
`result_count - resolved_source_count`: multiple hits may resolve to one source.
It is not a new hashed column in this proposal. Because that captured count is
not in the registered payload, the initial slice cannot promise its exact
historical reconstruction without a saved basis (§3.3/§10). Return it as a
creation-time diagnostic only; on later reads return the current derived count
with explicit observation time and `captured_unresolved_result_count=unknown`.
Never fabricate zero or label current resolution state as frozen coverage.

Counts in SearchCoverage are immutable captured aggregates, computed in one
protected consistent observation, not caller estimates. Later resolution/merge
cannot change those saved integers. Current resolution diagnostics are separate
and may differ. Coverage does **not** freeze a selected source/evidence/screening
set: the registered table/hash does not contain those bindings. Count checks
protect capture honesty but cannot supply missing screening provenance.

### 3.2 PriorArtRelation — finite attributable comparison

Persist only IDENTICAL, HIGHLY_SIMILAR, PARTIAL_OVERLAP, RELATED, CONTRASTING,
UNCLEAR (uppercase forms of 05 §25.1). Every relation requires nonblank rationale
and a nonempty duplicate-free evidence set. Proposed first slice requires each
input independently VERIFIED under existing evidence policy, hash-valid,
same-project and bound to the exact stated frozen SourceVersion. A verified
quotation does not verify the assessor's similarity conclusion.

IDENTICAL/HIGHLY_SIMILAR are proposed close-prior-art candidates; PARTIAL_OVERLAP,
RELATED and CONTRASTING never mechanically establish absence of close prior art.
UNCLEAR explicitly preserves uncertainty. No numeric similarity score, ranked
provider hit or bare DOI substitutes for the inspected source/locator/evidence
and rationale. Different relation records for the same Claim/source may coexist;
contradictory judgments remain visible and cannot be resolved by “latest wins.”
The registered relation has no supersedes FK: corrections append a new relation
and retain ambiguity unless a separately approved correction mechanism exists.

### 3.3 NoveltyAssessment — material-basis gap and proposed first slice

| Registered outcome | Meaning and proposed availability |
| --- | --- |
| INCONCLUSIVE | Coverage/interpretation does not justify a bounded novelty finding. Available with exact valid Claim and coverage and nonblank limitations; no implication that close art was absent or found. |
| CLOSE_PRIOR_ART_FOUND | A specific inspected exact source/evidence comparison establishes close art within an explicitly recorded scope. Deferred until saved assessment basis is contracted. |
| NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE | No close art found within the exact plan and fully accounted, resolved and screened execution scope, subject to stated limitations. Deferred until completeness and saved negative-probe/screening basis are contracted. Never “first work ever.” |

The R2 v1 payload has only Claim, coverage, outcome, limitations, predecessor and
assessor. It has **no PriorArtRelation/evidence input set** and no immutable
screening disposition set. Reading all current relations, taking a favorable
subset or using `created_at <= assessed_at` cannot freeze membership under
concurrent commits or later additions. Free text listing IDs is not a strong FK.
SearchCoverage's counts alone cannot prove every hit was assessed.

Recommend **DO NOT ADD SCHEMA** for the initial slice: admit INCONCLUSIVE and
retain stronger outcomes as unavailable. Before full-scope acceptance, owner
must either approve an existing-pattern deterministic basis solution or a bounded
ADR for concrete assessment-input/screening relations and an explicit new hash
material version. Do not add rows absent from v1 hash material, silently extend
v1, or reinterpret an enum. Positive and negative assertions both need exact
basis. This unresolved gap is a contract-freeze blocker for the full three-outcome
scope, not authority to implement a new screening system here.

## 4. Proposed commands, DTOs and historical readback

Closed immutable DTOs use canonical UUIDs, finite string enums and valid NFC
text with meaningful whitespace preserved under Hash R2. Reject unknown fields,
duplicate IDs, blank narratives, invalid Unicode and malformed typed values.
Principal/actor, UTC time, hashes, derived project and accounting are server-owned.

| Command/query | Caller input | Atomic result |
| --- | --- | --- |
| `RecordSearchCoverageCommand` / `record_search_coverage` | `id`, `project_id`, `search_plan_version_id`, `search_execution_ids: tuple[UUID,...]`, `coverage_limitations` | One immutable coverage with computed providers/counts/time_scope and concrete execution children. No retrieval/resolution work. |
| `RecordPriorArtRelationCommand` / `record_prior_art_relation` | `id`, `project_id`, `claim_version_id`, `source_version_id`, `relation`, `rationale`, `literature_evidence_ids: tuple[UUID,...]` | One immutable comparison and concrete evidence children. No evidence verification/support promotion. |
| `RecordNoveltyAssessmentCommand` / `record_novelty_assessment` | `id`, `project_id`, `claim_version_id`, `search_coverage_id`, `assessment`, `limitations`, `supersedes_assessment_id: UUID|null` | One immutable assessment; initial slice only INCONCLUSIVE; optional predecessor is retained unchanged. |
| `read_search_coverage`, `read_prior_art_relation`, `read_novelty_assessment` | `project_id`, exact object `id` | Authorized typed history DTO and explicitly separate current diagnostics; no write or refreshed authority. |

No input `assessed_by`, created time, content hash, caller counts/providers/time
range, `is_first`, approval flag, “ignore failures,” evidence-status override,
generic target pair, provider response or results JSON. Proposed bounded inputs:
1–100 execution/evidence IDs and 1–16,384 Unicode characters for each narrative;
these new transport limits require owner confirmation, not serializer changes.

CoverageReadback returns ID, derived project, plan ID/hash, sorted execution IDs,
captured material fields, created attribution/time, hash/scheme and a separately
labelled current attempt/resolution quality report. PriorArtReadback returns exact
Claim/Source/evidence IDs and verified hashes, enum/rationale/assessor/time and
own hash/scheme. NoveltyReadback returns exact Claim/Coverage IDs/hashes, outcome,
limitations, predecessor ID/hash, assessor/time and own hash/scheme. Current
validity, superseded-by navigation and “not an independently reviewed finding”
are derived fields; no current latest source or mutable material status is added.
DTOs contain no ORM entity. Related-object details require their own read rights;
reference disclosure cannot widen existing review/evidence authorization.

Proposed read roles mirror existing Decision history readers: effective
OWNER/RESEARCHER/REVIEWER/APPROVER/VIEWER, ACTIVE membership and live verified
credential. UUID is canonical command identity. Exact same-actor replay compares
project, command and normalized caller material, verifies saved hashes/closure,
and returns saved immutable material with current diagnostics. It does not
recompute saved coverage from newer resolution rows or refresh the basis.
Write-role loss/later invalidity permits historical replay only with current
read entitlement. Another actor cannot impersonate original command submission.
Changed normalized input conflicts; unknown/incomplete history uses first-write
gates. No extra receipt/digest schema is proposed; derived counters are compared
to persisted values for integrity, not to changed current resolution state.

Propose nonforking assessment supersession: predecessor same project and **same
exact ClaimVersion**, new UUID, no existing successor, hash-valid, no self/cycle.
New coverage may differ but must remain same project; a valid new assessment may
document correction of a now-stale predecessor. Unique predecessor prevents two
successors. Independent roots are allowed and returned together; no canonical
“latest assessment” is selected. Different ClaimVersion starts a new root, never
retargets a chain. Replay does not allocate another successor.

## 5. Schema and literal hash proposal — no migration

Use only the five already named tables from 13; no NoveltyVersion, new Claim
owner, universal assessment schema or generic polymorphic primary edge. Shared
physical columns follow 13: UUID PK, trusted UTC created_at/created_by where
applicable, fixed hash scheme and lowercase 64-hex own hash on hashed parents.

| Proposed table | Fields and constraints |
| --- | --- |
| `search_coverage` | `search_plan_version_id` concrete FK; `providers` JSONB of strings only; integer `query_count`, `result_count`, `resolved_source_count` each >=0; nullable `time_scope` closed `{from,through}` date bounds; nonblank `coverage_limitations`; `content_hash`, `hash_scheme`; creation metadata. No source-ID JSON or new project owner column. |
| `search_coverage_executions` | Concrete coverage/execution FKs; UNIQUE pair, nonempty sealed parent set, same exact plan/project and terminal-history guards. No child own hash. |
| `prior_art_relations` | Concrete `claim_version_id`, `source_version_id`; six-value `relation`, nonblank `rationale`, `assessed_by` Actor FK, own hash/scheme and creation metadata. No mutable confidence/status or supersession column. |
| `prior_art_evidence_inputs` | Concrete prior-art/evidence FKs, UNIQUE pair, nonempty sealed parent set; exact source-version and same-project enforcement. No child own hash. |
| `novelty_assessments` | Concrete `claim_version_id`, `search_coverage_id`, three-value `assessment`, nonblank `limitations`, `assessed_by` Actor FK, nullable `supersedes_assessment_id` self-FK, own hash/scheme and creation metadata. Proposed partial UNIQUE nonnull predecessor, no self-reference, same-Claim/project chain guards. Initial-slice normal-role guard denies stronger enums even though full design lists them. |

All canonical FKs use RESTRICT, with indexes unless already covered by PK/UNIQUE.
Index Claim/source/coverage/predecessor lookups and reverse execution/evidence
lookups. Project agreement derives through existing ownership/access FKs, checked
by concrete composite constraints or typed guards; no type/id locator. JSON here
is bounded scalar provider metadata or a closed date value, never semantic core.
Normal-role SQL must reject parent/child UPDATE/DELETE, late child insert,
unsupported enum/shape, unfrozen/mismatched inputs and structural bypass. Parent
and children publish atomically; no observable half-sealed record. Admission
validity checks do not prohibit later legitimate invalidity/retraction events.

Hash **exactly** R2 15, `sha256-cjson-v1`, `material_version=1`:

- SearchCoverage: `type`, `material_version`, `search_plan_version` R-ref,
  `search_execution` sorted UUID I-refs, sorted `providers`, the three counts,
  closed `time_scope` or explicit null, `coverage_limitations`.
- PriorArtRelation: `type`, `material_version`, Claim and Source R-refs,
  `relation`, `rationale`, UUID-sorted `literature_evidence` R-refs,
  `assessed_by` Actor I-ref.
- NoveltyAssessment: `type`, `material_version`, Claim and coverage R-refs,
  `assessment`, `limitations`, `supersedes_assessment` R-ref or explicit null,
  `assessed_by` Actor I-ref.

R-ref is exactly `{type,id,content_hash}`; I-ref is `{type,id}`. SearchExecution
has no invented own scientific hash. Times, row IDs, derived project/validity,
unresolved count, screening state and unlisted actor fields do not enter v1.
Set duplicates deny before sorting; stored normalized material is verified on
read/restart with an independent literal oracle. Frozen Claim support/content
hash and LiteratureSupportSnapshot material are never extended with novelty.

Future realization requires separate authorization, additive forward migration,
one Alembic head, legacy preflight and data-preserving downgrade/refusal. Do not
assign a revision number while PR2-15/16 are being implemented, edit accepted
migrations, or claim schema admission for the missing §3.3 basis. Any new material
contract needs ADR/compatibility review and historical digest preservation.

## 6. Error contract — proposed use of existing categories

Authenticate and establish project entitlement before protected existence,
conflict or target diagnostics. Foreign scope denies without disclosing history.
Bounded sanitized details contain no SQL/driver/credential exception chains.
Transport proposals: 401 authentication, 403 forbidden, 404 authorized absence,
422 malformed input and 409 state/provenance/conflict; stable meanings prevail.

| Code | Proposed trigger and retry rule |
| --- | --- |
| AUTHENTICATION_REQUIRED / FORBIDDEN | Missing trusted principal/live credential/current entitlement; foreign scope or different-actor replay. No blind retry. |
| VALIDATION_ERROR | Unknown fields, malformed/duplicate IDs, blank limitations, unsupported enum/value/shape or bounds. Correct input. |
| NOT_FOUND | Authorized exact input/object absent. Correct reference. |
| FROZEN_REFERENCE_REQUIRED | DRAFT/unfrozen plan, Claim or SourceVersion. Complete owning freeze first. |
| INVALID_STATE_TRANSITION | Nonterminal/unsealed execution, unverified comparison evidence, unavailable stronger assessment, predecessor already superseded. Resolve state or obtain separate contract authorization. |
| PROVENANCE_CLOSURE_VIOLATION | Hash/closure corruption, wrong exact source evidence, invalid first-write inputs, inconsistent accounting or assessment chain. Investigate; never drop adverse inputs. |
| IDEMPOTENCY_CONFLICT | Same entitled actor reuses UUID with changed normalized command material. Recover original request; do not shop IDs to rewrite history. |
| IMMUTABLE_RECORD / REFERENTIAL_INTEGRITY_ERROR | Forbidden material mutation or sanitized FK/constraint failure. Append permitted history/correct refs. |
| CONCURRENT_MODIFICATION | Exhausted serialization/deadlock retries or competing supersession. Only operational deadlock/serialization permits bounded full-transaction retry. |

No new ErrorCode is installed by this draft. “coverage insufficient” is normally
an INCONCLUSIVE result with limitations, not success for a stronger requested
enum. HASH_MISMATCH in design prose maps to the existing provenance category;
timeout/connection/uncertain commit follows the sanitized UoW contract and never
becomes PASS. Pin exact API/CLI and timeout mappings before implementation.

## 7. Transactions, concurrency and failure recovery

One Application command = one synchronous PostgreSQL 18.x UoW transaction:
Caller → Application → Repository Port/UoW → Persistence Adapter → PostgreSQL.
No network retrieval/LLM/provider call inside it. Domain imports no Session,
FastAPI, Typer, Codex or external Skill. Each result already exists durably;
recording cannot retroactively make retrieval and coverage one transaction.

Proposed coordination begins with namespaced request UUID → derived project and
exact Claim/plan target (stable table/UUID order) → compatible closure/authority
snapshot locks → selected execution/result/evidence/coverage rows in stable
order → predecessor → parent/children/audit writes. Before implementation,
inventory every execution finalizer, query/result writer, resolution appender,
evidence verification, source correction/merge/access, governance impact,
membership/role and supersession writer. Freeze a common lock matrix with the
existing Decision target-before-sorted-SHARE-table protocol; do not introduce
inversion or lock upgrade. This ordering is a proposal, not proof today's
resolution writers already coordinate with coverage.

Coverage capture requires phantom protection for resolution INSERTs and a
consistent query/result/attempt observation: participating parent locks or an
approved snapshot/table-lock strategy, not selected-row locks alone. Resolution
committing first contributes to capture; coverage capturing first keeps its
saved counts while later resolution appears only in current diagnostics.
No graph walk silently adds a new execution or refreshes selected resolution
membership on replay. Direct normal-role SQL participates in structural guards.

After every blocking wait, reread durable state; recompute exact hashes/closure
and obtain fresh trusted `clock_timestamp()` immediately before protected write
to recheck credential, ACTIVE membership/effective role and relevant validity.
Never use caller clock, now()/transaction-start time or cached pre-lock gates.
Any further wait repeats checks. Retry at most three whole attempts for
deadlock/serialization, each in a new transaction with fresh reads. Operational
timeouts must be pinned in the future execution pack.

Same UUID concurrent requests produce one parent/child/event set. Competing
successors produce one winner, with loser rollback/conflict; separate roots do
not get conflated. Mid-parent/child/audit failure rolls back all new writes and
never erases completed retrieval/evidence. Unknown commit outcome is recovered
by exact UUID read/replay, not a new ID. Later correction/retraction/verification
loss remains appendable, preserves hash history and is exposed to downstream
current gates; this draft promises no new automatic ImpactAssessment engine.

## 8. Tests to add after authorization — planned, NOT IMPLEMENTED

05 §49's named obligations map to PR2-18 as follows; existing tests may be
extended without renaming their stable purpose.

| Required architecture test | PR2-18 assertion |
| --- | --- |
| `test_literature_source_not_evidence` | DOI/title/source resolution alone cannot create comparison evidence or novelty proof. |
| `test_search_result_not_evidence` | Snippet/score/zero-result answer stays retrieval provenance; source-backed verification is required. |
| `test_citation_not_claim_support` | Prior art/novelty creates no Claim support or literature snapshot. |
| `test_strategy_does_not_import_persistence` | Strategy calls typed Application commands only. |
| `test_adapter_does_not_write_db` | Search/LLM/Harness output cannot insert canonical novelty rows directly. |
| `test_no_storm_specific_core_schema` | No strategy-specific novelty or screening entity admitted implicitly. |
| `test_no_paperqa_specific_core_schema` | No vendor index/confidence payload as canonical basis. |
| `test_discussion_not_canonical_science` | Discussion/Agent consensus cannot supply novelty admission or reviewer identity. |
| `test_manuscript_not_scientific_source_of_truth` | Novelty wording/citations never establish absence of prior work. |
| `test_review_does_not_mutate_target` | New assessment/comparison leaves Claim/source/review/Issue material unchanged. |
| `test_decision_does_not_mutate_history` | PROCEED/RevisionAction does not replace or upgrade novelty history. |
| `test_approval_does_not_override_invalid_fact` | Grant/APPROVE cannot bypass bad hashes, retraction, insufficient coverage or OPEN/BLOCKING concern. |
| `test_external_call_not_inside_long_db_transaction` | Commands make no provider/LLM call; no effect/grant consumption. |

| Additional test group | Required evidence in future separately authorized implementation |
| --- | --- |
| Closed DTO/accounting | Duplicate/foreign/mixed-plan executions, empty scope, PLANNED/RUNNING/RESERVED deny; retries, failed/UNKNOWN, duplicate hits, zero invoked queries, truncation, source-only and ambiguous resolutions count/report exactly; null/closed date range and provider semantics. |
| Negative probes/limits | Failed query cannot become negative evidence; zero results with SUCCEEDED still INCONCLUSIVE initially; stronger enums deny atomically; no first-ever rendering, exhaustive claim or hidden unresolved hit. Future full slice proves complete exact screening basis. |
| Prior art | All six literals, nonblank rationale/nonempty evidence; wrong source version/project, DRAFT/retracted source, UNREVIEWED/DISPUTED/REJECTED evidence, corruption and score-only admission deny. Contradictory relations stay visible. |
| Hash/history | Independent R2 literal vectors, sorting/NFC/nulls, child set sealing, restart reads, Phase 1 hash compatibility; later resolution/correction does not change captured material; invalidity warnings differ from historical outcome. |
| Supersession/replay | Same-Claim predecessor, cycle/fork/self/foreign-Claim denial; independent roots; one concurrent successor; exact UUID replay after validity/write-role loss with current read right, changed payload conflict, nondisclosure and no duplicate events. |
| PostgreSQL guards/migration | Real 18.x catalog/FK/CHECK/trigger evidence, parent/child direct-SQL append/update/delete bypass attempts; one-head clean install/upgrade, populated legacy preservation and refused destructive downgrade. Never SQLite. |
| Races/faults | Resolution phantom INSERT versus capture in both commit orders; execution finalization, source invalidity, evidence dispute, role/credential expiry/revocation; actual lock witnesses and fresh protected reads; mid-child failure, retry and uncertain-commit recovery. |
| Cross-phase compatibility | Relevant source/search/resolution/evidence suites; Claim closure and Phase 1 golden path; conclusion/manuscript trace, PR2-14 review and PR2-15 Decision suites; PR2-15 RevisionAction/PR2-16 Approval regressions when available. No issue/approval/package/effect side effects. |

Race evidence uses separate backend PIDs, `pg_stat_activity`, `pg_blocking_pids()`
or `pg_locks`, actual blocking/commit order and persisted row/event counts.
Cross-expiry evidence follows Addendum A22: transaction and wait begin before
expiry; lock acquisition and final DB-time check occur after expiry; protected
effect count is zero. Include a second required wait where present. Sleep alone
is not proof. Fault tests use a disposable database and never production data.

## 9. Acceptance criteria and evidence boundary

**Draft acceptance:** this is the sole changed file, exact required DRAFT status
is present, all local links resolve and inherited invariants/proposed choices/
owner blockers are distinguishable. This document records actual baseline checks,
not a PR2-18 implementation test result or independent review.

**Contract freeze:** owner resolves §10, names initial versus full scope, validates
accounting and assessment-basis sufficiency against 01/02/03/05/08/12/13/15 and
approved PR2-15/16 base, and obtains review with no open P0 BLOCKER/P1 MAJOR.
New schema/material needs ADR before implementation. Contract approval alone
does not grant IMPLEMENTATION_GO.

**Future initial-slice engineering acceptance:** all applicable §8 checks pass,
including real PostgreSQL 18.x guards/migration/races, independent hash vectors,
restart/replay/failure/temporal evidence and zero unintended scientific/governance
effects. Quality reports expose failed/UNKNOWN/unresolved/truncated scope.
Only INCONCLUSIVE is enabled; full PR2-18 is not declared accepted unless owner
explicitly accepts that bounded scope.

**Full PR2-18 acceptance:** in addition, exact positive comparison and complete
negative screening/probe basis are frozen and reconstructable for both stronger
enums; later adverse records cannot disappear through filtering/latest selection.
Coverage limitations survive every DTO/render/consumer. Required checks report
exact commands, server version, pass/fail/error/skip counts and review findings.
No Human Gate, PR2-15/16 acceptance, deployment or Phase 2 exit is advanced here.

## 10. Open questions for the owner — each needs an explicit disposition

| Question | Recommended conservative answer |
| --- | --- |
| Initial scope or full three-outcome PR? | Approve coverage + six comparisons + INCONCLUSIVE first, explicitly label bounded acceptance; defer stronger enums until exact basis is frozen. Do not equate this with full PR2-18 by default. |
| How is an assessment's exact prior-art/screening basis bound? | Reuse existing relation/snapshot patterns only if deterministic membership can be proved. Otherwise require a bounded ADR, concrete FKs and new material version before either stronger outcome. No current-set/time-cutoff/free-text substitute. |
| How is captured unresolved count reported after restart? | Initial scope returns unknown historical count and timestamped current diagnostics. If exact historical quality reporting is required, freeze a minimal deterministic capture-basis/material amendment before implementation; never derive it by subtracting unique sources. |
| Does coverage include all executions of the plan? | Caller declares an exact set; always disclose this is selected scope. For any future negative finding require deterministic complete intended search/probe inventory and no omitted failed/adverse branches; selection alone cannot certify it. |
| Query/source counts and providers? | Use §3.1 record-based accounting, exact source IDs and actually invoked providers; include retry failures and ambiguous/source-only resolutions honestly. Pin these definitions and zero-invocation reporting before freeze. |
| What proves screening and a negative novelty probe? | No new subsystem in initial slice; explicitly report absent screening. Full scope needs exact dispositions/criteria and retained negative probes through approved existing patterns or bounded ADR. SUCCEEDED retrieval is insufficient. |
| Are IDENTICAL/HIGHLY_SIMILAR the only close categories? | Treat them as candidates needing inspected evidence, never automatic truth. PARTIAL_OVERLAP/UNCLEAR cannot justify a negative finding. Freeze scope-specific comparison criteria before stronger outcomes. |
| Must all comparison evidence be VERIFIED? | Yes for initial canonical comparison admission; unreviewed Agent outputs remain candidates. Existing independent Human evidence-verification policy remains unchanged. Assessor need not be an independent HUMAN reviewer. |
| Correction, contradiction and supersession policy? | Nonforking same-exact-Claim assessment chains, independent roots visible; no “latest wins.” PriorArtRelation has no approved supersession field, so preserve conflicting records and defer authoritative correction selection. |
| Who may record/read, and are new DTO bounds acceptable? | Effective OWNER/RESEARCHER writers; authenticated current project readers under §4; Human/Agent same boundary. Confirm 100-ID/16,384-character limits and nested disclosure; owner authority cannot prove novelty. |
| Must novelty be a new approval gate or review target? | No automatic gate, no new RevisionAction result shape, no new Decision purpose. Contract exact typed integration separately; preserve existing OPEN/BLOCKING and invalid-fact rules. |
| How are retraction/dispute and historical captures coordinated? | Preserve immutable bytes, derive current unusability/warnings through existing validity/impact paths, and freeze complete lock/phantom-protection matrix. Do not promise a new propagation engine or silently update saved counts. |

Until these choices are approved and incorporated through the governing review
process, PR2-18 remains DRAFT and not authorized for implementation.

## 11. Documentation-task verification — 2026-10-13

Only this proposal is added to the tracked-file change set. Scratch/cache/logs
are under ignored `tmp/pr218-verification/` inside this repository. No branch,
commit, push, governing-file edit, migration or retained database write occurred.
Checks concern the documentation change and unchanged baseline, not PR2-18
engineering acceptance or independent architecture review.

The worktree initially had no installed environment. Initial `uv --no-sync`
pytest/Ruff/Pyright attempts exited **2 before tool execution** (missing tools);
uv created an empty local `.venv`. Subsequent commands read the existing project
environment without synchronization and use `PYTHONPATH=src` to select this
worktree's source. No external environment was changed. The task-created empty
local `.venv` was removed after verification.

Exact executed baseline commands (output redirection only saves evidence):

```bash
PYTHONPATH=src UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv uv --cache-dir tmp/pr218-verification/uv-cache run --offline --no-sync pytest -o addopts='' -ra --tb=short tests/unit tests/architecture > tmp/pr218-verification/unit-architecture.log 2>&1
PYTHONPATH=src UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv uv --cache-dir tmp/pr218-verification/uv-cache run --offline --no-sync ruff check .
PYTHONPATH=src UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv uv --cache-dir tmp/pr218-verification/uv-cache run --offline --no-sync ruff format --check .
PYTHONPATH=src UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv uv --cache-dir tmp/pr218-verification/uv-cache run --offline --no-sync pyright --venvpath /Users/fengwang/Documents/ResearchBaseProject
```

| Check | Actual result |
| --- | --- |
| Unit/architecture selection | Exit 1: **1820 passed, 5 failed, 0 skipped, 2 warnings**, 35.05s. |
| Ruff lint | Exit 0: **All checks passed!** |
| Ruff format | Exit 0: **456 files already formatted**. |
| Standalone Pyright with explicit environment | Exit 0: **0 errors, 0 warnings, 0 informations**. |

Four unit failures are the versioned-denial, socket-lifecycle, foreign-peer and
incomplete-frame tests in `tests/unit/test_hg1_runner.py`, all at socket bind
with `PermissionError: [Errno 1] Operation not permitted`. The fifth is
`tests/unit/phase2/test_pr2_04_static_acceptance.py::test_candidate_static_gates_and_inherited_formatter_delta`:
its nested Pyright invocation uses the configured empty worktree `.venv`, causing
missing imports/type diagnostics. The separately executed explicit-environment
Pyright command above passes. These are reported as actual failed tests, not
waived or converted to PASS; no test/configuration was modified to suppress them.

PostgreSQL availability and initialization commands:

```bash
pg_isready -h 127.0.0.1 -p 5432
pg_isready -h 127.0.0.1 -p 55440
/opt/homebrew/opt/postgresql@18/bin/initdb -D tmp/pr218-verification/pgdata -U pr218_admin -A trust --no-locale
```

Both readiness probes exit 2, **no response**. initdb exits 1 at `shmget` with
`could not create shared memory segment: Operation not permitted`, and removes
its incomplete cluster. No server was initialized/started; no connected server
version can be reported. Escalation is unavailable in this session.

Relevant PostgreSQL baseline selection was nevertheless invoked explicitly:

```bash
PYTHONPATH=src UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv DATABASE_URL=postgresql+psycopg://pr218_admin@127.0.0.1:55479/postgres RB_TEST_ADMIN_URL=postgresql+psycopg://pr218_admin@127.0.0.1:55479/postgres uv --cache-dir tmp/pr218-verification/uv-cache run --offline --no-sync pytest -o addopts='' -ra --tb=short tests/integration/phase2/test_pr2_02_source_version_migration.py tests/integration/phase2/test_pr2_03_literature_search_plan_application.py tests/integration/phase2/test_pr2_04_execution_provenance.py tests/integration/phase2/test_m2_metadata.py tests/integration/phase2/test_m3_evidence.py tests/integration/phase2/test_pr2_11_r2_persistence.py tests/integration/phase2/test_pr2_13_scientific_trace.py tests/integration/phase2/test_pr2_14_internal_review.py tests/integration/phase2/test_pr2_14_conclusion_review.py tests/integration/phase2/test_pr2_15_decision.py tests/integration/phase2/test_pr2_15_decision_schema.py tests/integration/phase2/test_pr2_15_coordination.py tests/integration/test_pr12_closure.py tests/e2e/test_phase1_golden_scientific_workflow.py > tmp/pr218-verification/integration.log 2>&1
```

Exit 1: **0 passed, 7 failed, 146 setup errors, 0 skipped**, 19.81s. The failures
and errors are connection restrictions (`OperationalError`, `Operation not
permitted`), including tests that create connections inside the test body.
**BLOCKED, not PASS:** no PostgreSQL integration assertion/migration acceptance
completed. Rerun this exact selection on a permitted disposable PostgreSQL 18.x
host. Other DB suites and future §8 novelty tests are NOT RUN: no executable,
schema or authoritative contract behavior changes in this task; future
implementation requires the broader applicable regression/acceptance matrix.

Exact documentation checks, rerun after adding this evidence:

```bash
PYTHONPATH=src UV_PROJECT_ENVIRONMENT=/Users/fengwang/Documents/ResearchBaseProject/.venv uv --cache-dir tmp/pr218-verification/uv-cache run --offline --no-sync python - <<'PY'
from pathlib import Path
import re, subprocess
p = Path('docs/proposals/PR2-18_Novelty_PriorArt_Contract_DRAFT.md')
s = p.read_text()
links = re.findall(r'\]\(([^)]+)\)', s)
assert all((p.parent / t).is_file() for t in links)
assert '**Status: DRAFT — awaiting owner approval; not authorized for implementation**' in s
assert subprocess.check_output(['git', 'status', '--porcelain'], text=True).splitlines() == [f'?? {p.as_posix()}']
assert all(line == line.rstrip() for line in s.splitlines())
assert sum(line.startswith('```') for line in s.splitlines()) % 2 == 0
print(f'5 documentation checks passed; {len(links)} local links resolve')
PY
git diff --check
git diff --exit-code -- docs/architecture src migrations tests pyproject.toml uv.lock AGENTS.md
```

Result: **5 documentation checks passed; 19 local links resolve**; both git
checks exit 0. Explicit content checks cover the untracked draft that ordinary
`git diff` omits. Documentation verification is complete; baseline test and
database limitations above remain visible and grant no engineering gate success.
