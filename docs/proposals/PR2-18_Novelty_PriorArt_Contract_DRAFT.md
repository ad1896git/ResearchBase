# PR2-18 Novelty / Prior Art Basic Contract — DRAFT

**Status: APPROVED by owner 2026-10-14 — first slice authorized for implementation**

## Start here (for the implementer)

After separate authorization, the first slice records the coverage of completed
literature searches, six kinds of evidence-backed comparison between an exact
frozen claim version and an exact frozen source version, and inconclusive novelty
assessments. It provides three recording commands and three reads by exact
identifier, shared by human and agent callers through the application boundary.
Records are immutable; reads preserve saved material and separately report current
limitations and validity warnings. It does not search for literature, establish
that no close prior work exists, prove priority, or advance review or approval.

**Build in this order** (module paths are in [the ordered build guide](#123-ordered-build-steps-and-module-paths)):

1. Define domain records, enums and normalization using [types and limits](#113-dto-fields-python-types-and-limits) and [literal hash material](#5-schema-and-literal-hash-proposal--no-migration).
2. Define application commands, reads and repository ports using [command behavior](#4-proposed-commands-dtos-and-historical-readback), [accounting](#31-searchcoverage-accounting--proposed-definitions) and [scope guards](#111-scope-and-policy-decisions).
3. Add the forward migration and persistence repository using [tables and guards](#121-ddl-sketch-and-guard-inventory) and [exact lock order](#122-exact-lock-order-and-transactions).
4. Wire transactions, constraint errors and bounded retries using [transaction sequences](#122-exact-lock-order-and-transactions) and [error mappings](#112-pinned-error-mappings).
5. Wire the application service and web routes using [the route and composition instructions](#123-ordered-build-steps-and-module-paths), step 5.
6. Add the command-line commands and sanitized errors using [the command-line instructions](#123-ordered-build-steps-and-module-paths), step 6, and [error mappings](#112-pinned-error-mappings).
7. Add and run [the required tests and regressions](#124-test-artifacts-and-required-cases), cover [the architecture obligations](#8-tests-to-add-after-authorization--planned-not-implemented), record evidence and stop at [bounded acceptance](#9-acceptance-criteria-and-evidence-boundary).

**Background to skip on first read:** [authority and inspected baseline](#1-purpose-authority-and-inspected-baseline),
[the glossary](#10-glossary) and [the owner override register](#13-open-questions-for-the-owner--override-register).
Consult these for provenance, unfamiliar terms or an owner override; they do not replace the build contracts.

**Five rules that would fail review if broken:**

1. Admit only inconclusive assessments; deny both stronger outcomes before writing. Add no missing assessment or screening schema ([scope decisions](#111-scope-and-policy-decisions)).
2. Bind exact frozen claim, source and plan versions; require independently verified comparison evidence, matching project access and trusted caller attribution ([invariants](#3-invariants-and-conservative-judgments)).
3. Seal parent and child material atomically, preserve literal registered hashes and append corrections; never rewrite history or select a judgment by “latest wins” ([schema and hashes](#5-schema-and-literal-hash-proposal--no-migration)).
4. Count persisted observations honestly, retain failures and uncertainty, and separate saved counts from current diagnostics; never imply exhaustive coverage or first-ever priority ([accounting](#31-searchcoverage-accounting--proposed-definitions)).
5. Use the shared application boundary and prescribed PostgreSQL transactions, locks and fresh authorization checks; create no scientific-support, review, approval or release effects ([transactions](#7-transactions-concurrency-and-failure-recovery), [separation](#3-invariants-and-conservative-judgments)).

**Scope:** owner-approved first-slice implementation contract, authorized
2026-10-14. This authorization does not accept the implementation, advance a
Phase gate, or authorize the deferred §12.5 behavior. Director decisions dated
2026-10-14 resolve the exact-ID readback and coverage-isolation protocols below.

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
owner contract approval. The inspected code claims below describe the checkout baseline, not implementation acceptance.

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
unavailable until an exact assessment-basis contract is approved (§3.3). This is the shipped behavior of the draft’s first slice. Owner approval may
change the scope; bounded acceptance does not mean full PR2-18 acceptance. Every unavailable path denies before writing.

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
The authorized first slice adds only the implementation and verification specified in §12.3–§12.4.

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
   payload cannot nominate a HUMAN assessor. Writers are effective
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

At capture, compute the unresolved-result diagnostic as result rows minus
unambiguously resolved result rows. It is not `result_count - resolved_source_count`:
multiple hits may resolve to one source. The registered payload does not save this
diagnostic or its membership basis. Therefore `captured_unresolved_result_count`
is always null in the first slice, including the initial response. Return only a
timestamped current derived count. After restart, never label current resolution
state as frozen coverage. Exact historical reconstruction needs the §12.5 amendment.

Counts in SearchCoverage are immutable captured aggregates, computed in one
protected consistent observation, not caller estimates. Later resolution/merge
cannot change those saved integers. Current resolution diagnostics are separate
and may differ. Coverage does **not** freeze a selected source/evidence/screening
set: the registered table/hash does not contain those bindings. Count checks
protect capture honesty but cannot supply missing screening provenance.

### 3.2 PriorArtRelation — finite attributable comparison

Persist only IDENTICAL, HIGHLY_SIMILAR, PARTIAL_OVERLAP, RELATED, CONTRASTING,
UNCLEAR (uppercase forms of 05 §25.1). Every relation requires nonblank rationale
and a nonempty duplicate-free evidence set. The first slice requires each
input independently VERIFIED under existing evidence policy, hash-valid,
same-project and bound to the exact stated frozen SourceVersion. A verified
quotation does not verify the assessor's similarity conclusion.

IDENTICAL/HIGHLY_SIMILAR are close-prior-art candidates; PARTIAL_OVERLAP,
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

The draft decides **DO NOT ADD SCHEMA** for the initial slice: admit INCONCLUSIVE and
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
| `RecordNoveltyAssessmentCommand` / `record_novelty_assessment` | `id`, `project_id`, `claim_version_id`, `search_coverage_id`, `assessment`, `limitations`, `supersedes_assessment_id: UUID\|null` | One immutable assessment; initial slice only INCONCLUSIVE; optional predecessor is retained unchanged. |
| `read_search_coverage`, `read_prior_art_relation`, `read_novelty_assessment` | `project_id`, exact object `id` | Authorized typed history DTO and explicitly separate current diagnostics; no write or refreshed authority. |

No input `assessed_by`, created time, content hash, caller counts/providers/time
range, `is_first`, approval flag, “ignore failures,” evidence-status override,
generic target pair, provider response or results JSON. Proposed bounded inputs:
1–100 execution/evidence IDs and 1–16,384 Unicode characters for each narrative;
these limits are draft decisions, subject to owner override. They do not change hashing.

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

Read roles mirror existing Decision history readers: effective
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

Use nonforking assessment supersession: predecessor same project and **same
exact ClaimVersion**, new UUID, no existing successor, hash-valid, no self/cycle.
New coverage may differ but must remain same project; a valid new assessment may
document correction of a now-stale predecessor. Unique predecessor prevents two
successors. Independent roots are allowed. First-slice reads use exact IDs only:
`read_novelty_assessment` returns one assessment plus nullable, derived chain
navigation fields `supersedes_assessment_id` and `superseded_by_assessment_id`.
“Independent roots returned together” is deferred to a later slice; no list
endpoint or canonical “latest assessment” is introduced (§12.3 stands).
This resolves §4 versus §11.3 by director decision, 2026-10-14.
Different ClaimVersion starts a new root, never
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
Use the exact HTTP and CLI mappings in §11.2; existing meanings prevail.

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
becomes PASS. §11.2 pins mappings and §12.2 pins operational timeouts.

## 7. Transactions, concurrency and failure recovery

One Application command = one synchronous PostgreSQL 18.x UoW transaction:
Caller → Application → Repository Port/UoW → Persistence Adapter → PostgreSQL.
No network retrieval/LLM/provider call inside it. Domain imports no Session,
FastAPI, Typer, Codex or external Skill. Each result already exists durably;
recording cannot retroactively make retrieval and coverage one transaction.

Use the exact command-specific sequences in §12.2. Relation and assessment
commands keep the existing Decision target-before-sorted-SHARE-table protocol.
Coverage uses an ordinary READ COMMITTED UoW. Its FIRST SQL statement is
`LOCK TABLE <N> IN SHARE MODE`, before the request advisory lock or any read.
The inventory includes every capture-input table, so SHARE blocks concurrent
INSERT/UPDATE/DELETE, including resolution phantoms. Subsequent READ COMMITTED
statements see rows committed before lock acquisition. Direct-SQL coverage
insertion rejects unless isolation is READ COMMITTED and the backend already
holds granted SHARE locks on every table in N; triggers do not acquire those
locks on behalf of coverage callers. This replaces SSI capture by director
decision 3, 2026-10-14, after the stale-capture reproduction. Read every resolution
row, including conflicting and source-only bindings; later resolution commits
remain separate current diagnostics.

No graph walk adds executions or refreshes saved resolution membership on replay.
Direct normal-role SQL participates in the structural guards in §12.1.

After every blocking wait, reread durable state; recompute exact hashes/closure
and obtain fresh trusted `clock_timestamp()` immediately before protected write
to recheck credential, ACTIVE membership/effective role and relevant validity.
Never use caller clock, now()/transaction-start time or cached pre-lock gates.
Any further wait repeats checks. For coverage, authority/validity tables are
locked before capture reads, so rereads remain valid while the clock advances.
Retry at most three whole attempts for SQLSTATE 40001/40P01 only, each in a new
transaction with fresh reads. Use the operational limits in §12.2.

Same UUID concurrent requests produce one parent/child set. Competing
successors produce one winner, with loser rollback/conflict; separate roots do
not get conflated. Mid-parent/child failure rolls back all new writes and
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
| Supersession/replay | Same-Claim predecessor, cycle/fork/self/foreign-Claim denial; independent roots; one concurrent successor; exact UUID replay after validity/write-role loss with current read right, changed payload conflict, nondisclosure and no duplicate records. |
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
owner blockers are distinguishable. This document records an inspected baseline,
not a PR2-18 implementation test result or independent review.

**Contract freeze:** owner approves or overrides §11 decisions, validates
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

## 10. Glossary

This reference key also defines the shorthand used earlier. Document numbers
refer to the authoritative files linked in §1. Terms apply to this draft only
where the named governing contract permits them.

| Shorthand | Meaning and governing document |
| --- | --- |
| 01 / 02 / 03 / 05 / 08 / 12 / 13 / 15 / 20 | Numbered architecture documents in §1; their titles and links are the authority key. |
| Phase 1 / Phase 2 / Phase 3+ | Provenance core / literature and governance / later agent runtime; 01, [Phase 1 04](../architecture/04_Phase1_Development_Specification_v1.2_Harness_Integrated.md), 05 and [Phase 3 06](../architecture/06_Phase3_Development_Specification_v1.1_Harness_Integrated.md). |
| PR2-nn | Phase 2 pull-request work package number, not authorization or proof of installed capability; 05 implementation sequence. |
| R1 | Original Phase 2 correction, superseded only where R2 says so; 12 and Addendum A17–A18. |
| R2 | Second Phase 2 correction; Addendum A18 incorporates [Gap Closure 14](../architecture/14_Phase2_Design_Gap_Closure_R2_v1.0.md), Hash 15, [Ownership 16](../architecture/16_Phase2_Identity_Ownership_and_Source_Contract_R2_v1.0.md) and [Governance 17](../architecture/17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md). |
| R3 | Targeted correction to R2; [Design R3 18](../architecture/18_Phase2_Design_R3_Targeted_Remediation_v1.0.md), incorporated by A19. |
| R4 | Temporal authorization correction; [Design R4 19](../architecture/19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md), incorporated by A20. |
| A-number | Numbered normative clause in Correction Addendum 02; ranges include every named clause. |
| A2 | Execution naming; Correction Addendum 02. |
| A3 | Formal target references; Correction Addendum 02. |
| A4 | Reference persistence classes; Correction Addendum 02. |
| A10 | Concrete canonical-ID collection persistence; Correction Addendum 02. |
| A12 | Uppercase enum policy; Correction Addendum 02. |
| A17 | Phase 2 field-contract incorporation; Correction Addendum 02. |
| A18 | Phase 2 R2 incorporation and separate literature support; Correction Addendum 02. |
| A19 | R3 targeted correction incorporation; Correction Addendum 02. |
| A20 | R4 temporal authorization correction incorporation; Correction Addendum 02. |
| A21 | Current read entitlement for completed grant receipt replay; Correction Addendum 02. |
| A22 | Legacy-state preflight and observable cross-expiry evidence; Correction Addendum 02. |
| A23 | Minimal Decision command incorporation; Correction Addendum 02 and Decision Contract 20. |
| TEMP-AUTH-01 | Lock, reread, fresh database clock, authorize, then effect; Design R4 19 §1. |
| TEMP-AUTH-EVIDENCE-01 | Observable database lock and cross-expiry timestamps, not sleep-based evidence; Addendum A22. |
| P2-INV-017 | Novelty strength cannot exceed documented search coverage; 05 invariant register. |
| R-ref / R(T) | Exact hashed reference `{type,id,content_hash}` to material T; Hash R2 15. |
| I-ref / I(T) | Exact identity reference `{type,id}` without an invented content hash; Hash R2 15. |
| FrozenReference / closure | Exact immutable version reference / transitively deterministic material inputs; 01 and 08. |
| Sealed set | Concrete child membership published atomically with its parent, then closed to insert/update/delete; 13 and Hash R2 15. |
| v1 / material_version=1 | Registered first material encoding, not permission to add payload keys; Hash R2 15. |
| sha256-cjson-v1 / SHA-256 | Registered canonical JSON hash scheme / digest algorithm; Hash R2 15 and foundation hashing. |
| UUID / UUIDv7 | Typed globally unique ID / time-ordered UUID generation profile; 01 foundation and 08. |
| UTC / Instant / TIMESTAMPTZ | Universal time / trusted instant / PostgreSQL timezone-aware timestamp; 01 and 13. |
| NFC | Unicode Normalization Form C, applied before material hashing; Hash R2 15. |
| DTO | Closed typed data-transfer object; 08 and this draft §11.3. |
| API / CLI / HTTP | Application programming interface / command-line interface / HTTP transport; 08 and the error adapters linked in §11.2. |
| DB / SQL / DDL / JSONB | Database / SQL statements / schema definition language / PostgreSQL binary JSON; 13 shared physical rules. |
| PK / FK / CHECK / UNIQUE / RESTRICT | Primary key / foreign key / row predicate / uniqueness / deny referenced deletion; 13. |
| B-tree / partial index | PostgreSQL lookup index / index over a predicate-selected subset; 13 and this draft §12.1. |
| UoW / ORM | Unit of Work transaction boundary / object-relational mapper; 01 layering and existing persistence UoW. |
| SSI / phantom / SQLSTATE | Serializable snapshot isolation / newly inserted matching row / PostgreSQL error classification; existing UoW and this draft §12.2. |
| SHARE / FOR SHARE / FOR UPDATE | PostgreSQL table or row lock modes; existing Decision repository and §12.2. |
| PID | PostgreSQL backend process ID used for lock evidence; A22 and §8. |
| ADR / DO NOT ADD SCHEMA | Architecture Decision Record / default prohibition on new canonical schema; [AGENTS.md](../../AGENTS.md) §4 and Addendum 02. |
| IMPLEMENTATION_GO / Gate / PASS | Separate implementation authorization / acceptance boundary / completed passing evidence; AGENTS.md and [Harness 09](../harness/09_Harness_Integration_Specification_v1.0.md). |
| P0 BLOCKER / P1 MAJOR / P2 MINOR / P3 SUGGESTION | Review finding severities; AGENTS.md §10. |
| E2E | End-to-end regression, not a unit-level scope claim; 05 and 08 golden workflows. |
| ACTIVE | Current membership status, required alongside live credential/effective role; identity R2 16 and R4 19. |
| HUMAN / Agent / OWNER / RESEARCHER / REVIEWER / APPROVER / VIEWER | Caller classification and project roles; identity/ownership R2 16 and temporal R4 19. |
| DOI / ID / LLM | Literature identifier / exact object identity / language-model tool; 05 literature and Harness 09. None supplies scientific truth. |
| EvidenceRelation / LiteratureSupportSnapshot | Phase 1 scientific support / separate Phase 2 literature support binding; Addendum A18 and Hash R2 15. |
| Review / Decision / Approval / Command / ExternalEffect | Evaluate / choose / authorize / request execution / external change; 01 separation invariant. |
| OPEN / BLOCKING / PROCEED / READY | Issue status / severity / minimal Decision result / publication lifecycle state; 13 and 20. Novelty changes none of them. |
| DRAFT / FROZEN / SUPERSEDED / ABANDONED | Version lifecycle states; 13. DRAFT in the header instead means proposal status. |
| PLANNED / RUNNING / SUCCEEDED / FAILED / CANCELLED / UNKNOWN / RESERVED | Search execution and provider-attempt states; PR2-04 execution contract and current domain code. |
| UNREVIEWED / VERIFIED / DISPUTED / REJECTED / MERGED | Evidence review statuses / source identity merge status; 13. |
| INCONCLUSIVE / CLOSE_PRIOR_ART_FOUND / NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE | Registered novelty outcomes; 13 and §3.3. Only INCONCLUSIVE ships in this slice. |
| IDENTICAL / HIGHLY_SIMILAR / PARTIAL_OVERLAP / RELATED / CONTRASTING / UNCLEAR | Six attributable comparison categories; 05 §25.1, uppercase under A12. |
| STORM / PaperQA2 / Codex / FastAPI / Typer / Session | Reference research systems / engineering caller / HTTP adapter / CLI adapter / ORM session; Harness 09 and 01 layering. None owns canonical novelty facts. |
| Alembic / PostgreSQL 18.x / pytest / Ruff / Pyright | Migration tool / integration DB / tests / formatter and linter / type checker; [Phase 2 technology gate 11](../architecture/11_TDG2_Phase2_Technology_Decision_Gate_v1.0.md) and AGENTS.md verification. |
| StrEnum / Literal / NULL / NOT NULL / INT / VARCHAR / TEXT / CHAR | Python finite string enum/type literals and SQL column types/nullability; 13 and §11.3/§12.1. |
| ErrorCode / HASH_MISMATCH | Stable Application error enum / prose alias for PROVENANCE_CLOSURE_VIOLATION; existing adapters and §11.2. |

## 11. Decisions taken in this draft

All §13 recommended answers are adopted here. Owner approval on 2026-10-14
authorizes the first slice, subject to the director decisions recorded in §4,
§7 and §12.2. Deferred behavior still requires separate authorization.

### 11.1 Scope and policy decisions

1. Ship exactly three record commands and three exact-ID read queries from §4.
   Coverage, all six comparisons and INCONCLUSIVE are the complete first slice.
   Preserve the three-outcome enum for history/compatibility. Deny either stronger
   outcome with INVALID_STATE_TRANSITION before allocating children or events.
   The Application guard is `if command.assessment is not
   NoveltyOutcome.INCONCLUSIVE: raise INVALID_STATE_TRANSITION`.
   Database `ck_pr218_novelty_initial_slice` independently requires
   `assessment = 'INCONCLUSIVE'` on INSERT. No configuration bypass exists.
2. Add no assessment-basis schema. Stronger outcomes require the separate exact
   assessment-input and screening/negative-probe contracts in §12.5. Neither
   current relations, timestamps nor text IDs are an acceptable substitute.
3. Return `captured_unresolved_result_count=None` on every read, including the
   initial command response. Return the creation-time unresolved diagnostic as
   the timestamped current diagnostic only. Do not promise a saved historical
   unresolved count. An amendment is required before making that promise.
4. Coverage is a caller-selected execution set, never all plan executions by
   implication. Zero invoked queries yields `providers=()`, zero query/result/
   resolved counts and a `NO_INVOKED_QUERIES` warning. Failed/unknown/omitted
   branches remain visible; absent screening always yields `SCREENING_NOT_CAPTURED`.
5. Use §3.1 accounting. For each result, validate every resolution digest and
   its exact source-version/access binding. A result qualifies only when all
   retained bindings agree on one nonnull exact `(source_id,source_version_id)`.
   Any source-only binding or conflicting exact binding makes it unresolved.
   A corrupt resolution fails capture with PROVENANCE_CLOSURE_VIOLATION; it is
   not silently excluded. No merge/current-pointer deduplication applies.
6. IDENTICAL/HIGHLY_SIMILAR are close-art candidates, never an automatic outcome.
   All comparison evidence must be independently VERIFIED at first admission.
   Existing Human verification rules remain intact; the assessor may be an Agent.
7. Assessment supersession is nonforking, same exact Claim, and append-only.
   Independent roots and contradictory comparisons remain visible. No relation
   correction selector, authoritative newest judgment or mutable novelty status.
8. Writers are effective OWNER/RESEARCHER. Readers are the five roles in §4.
   Bounds are 100 IDs and 16,384 Unicode characters. Nested details require
   their own read rights. Same-actor exact replay uses current read entitlement,
   saved normalized material and saved hashes, with no new effect authorization.
   Changed input conflicts. Input UUID sets sort before comparison; duplicates deny.
9. Novelty is no new approval gate, review target, Decision purpose or RevisionAction
   result. Preserve existing blockers and deterministic invalidity precedence.
10. Later retraction/dispute never alters saved bytes or captured counts. Derive
    current warnings using existing validity readers, without a new propagation
    engine. Coverage uses READ COMMITTED with preheld SHARE locks and three attempts as specified in §12.2 (director decision 3, 2026-10-14).

### 11.2 Pinned error mappings

Reuse [HTTP mappings](../../src/researchbase/api/errors.py) and
[CLI mappings](../../src/researchbase/cli/errors.py) exactly. This slice needs no
new ErrorCode. Table entries are not aliases that may change transport meaning.

| Error code | HTTP status | CLI exit | Trigger |
| --- | --- | --- | --- |
| AUTHENTICATION_REQUIRED | 401 | 3 | No valid trusted principal. |
| FORBIDDEN | 403 | 3 | No current entitlement, foreign scope, different-actor replay. |
| VALIDATION_ERROR | 422 | 2 | Closed DTO, enum membership, bounds or shape violation. |
| NOT_FOUND | 404 | 3 | Authorized exact object absent. |
| FROZEN_REFERENCE_REQUIRED | 409 | 5 | Required frozen plan/Claim/source missing its freeze. |
| INVALID_STATE_TRANSITION | 409 | 4 | Nonterminal execution, unverified evidence, stronger outcome, used predecessor. |
| PROVENANCE_CLOSURE_VIOLATION | 409 | 5 | Corruption, invalid input, exact binding/accounting/chain violation. |
| IDEMPOTENCY_CONFLICT | 409 | 4 | Same UUID, entitled actor, changed normalized request. |
| IMMUTABLE_RECORD | 409 | 4 | Material mutation or late child insertion. |
| REFERENTIAL_INTEGRITY_ERROR | 409 | 5 | Sanitized concrete FK violation. |
| CONCURRENT_MODIFICATION | 409 | 4 | Exhausted SQLSTATE 40001/40P01 attempts or unique predecessor race. |
| INTERNAL_ERROR (existing HTTP fallback; proposed CLI fallback) | 500 | 1 (proposed) | Nonretryable timeout, connection failure or unknown commit outcome. |

HASH_MISMATCH is prose only; emit PROVENANCE_CLOSURE_VIOLATION. Do not add it to
the enum. In the separately authorized implementation, normalize unexpected CLI
failures to the proposed sanitized INTERNAL_ERROR/exit 1 fallback, without
pretending it is already in CLI_EXIT_CODES. SQLSTATE 55P03/57014 (lock/statement
timeout) and connection failures are not automatic retries. Roll back if known;
when commit is uncertain, recover with exact UUID replay before any new attempt.
A unique predecessor violation is CONCURRENT_MODIFICATION and is not retried.

### 11.3 DTO fields, Python types and limits

Implement commands as frozen, slotted dataclasses like RecordDecisionCommand.
Transport models reject unknown fields. UUID strings must round-trip to canonical
lowercase hyphenated strings; Python values must be `UUID`, not arbitrary strings.
Counts are strict `int`, never bool, within PostgreSQL INT range 0–2,147,483,647.
All times are aware UTC `datetime`. Required narratives are `str`, NFC-normalized,
nonblank, length 1–16,384 after normalization; preserve meaningful whitespace.

| DTO | Exhaustive fields and Python types |
| --- | --- |
| RecordSearchCoverageCommand | `id: UUID`, `project_id: UUID`, `search_plan_version_id: UUID`, `search_execution_ids: tuple[UUID, ...]`, `coverage_limitations: str`. |
| RecordPriorArtRelationCommand | `id: UUID`, `project_id: UUID`, `claim_version_id: UUID`, `source_version_id: UUID`, `relation: PriorArtKind`, `rationale: str`, `literature_evidence_ids: tuple[UUID, ...]`. |
| RecordNoveltyAssessmentCommand | `id: UUID`, `project_id: UUID`, `claim_version_id: UUID`, `search_coverage_id: UUID`, `assessment: NoveltyOutcome`, `limitations: str`, `supersedes_assessment_id: UUID \| None = None`. |
| ExactReadQuery | `project_id: UUID`, `id: UUID`; separate service method per object. |
| TimeScope | `from_date: date \| None`, `through_date: date \| None`; JSON aliases `from`, `through`. Exactly two keys, at least one bound, inclusive ISO dates, from <= through where both exist. |
| HashRef | `type: Literal['LiteratureSearchPlanVersion','ClaimVersion','SourceVersion','LiteratureEvidence','SearchCoverage','NoveltyAssessment']`, `id: UUID`, `content_hash: str` (64 lowercase hexadecimal characters). |
| SearchCoverageReadback | `id: UUID`, `project_id: UUID`, `search_plan_version: HashRef`, `search_execution_ids: tuple[UUID, ...]`, `providers: tuple[str, ...]`, `query_count: int`, `result_count: int`, `resolved_source_count: int`, `time_scope: TimeScope \| None`, `coverage_limitations: str`, `created_at: datetime`, `created_by: UUID`, `content_hash: str`, `hash_scheme: Literal['sha256-cjson-v1']`, `quality: CoverageQuality`. |
| PriorArtReadback | `id: UUID`, `project_id: UUID`, `claim_version: HashRef`, `source_version: HashRef`, `relation: PriorArtKind`, `rationale: str`, `literature_evidence: tuple[HashRef, ...]`, `assessed_by: UUID`, `created_at: datetime`, `created_by: UUID`, `content_hash: str`, `hash_scheme: Literal['sha256-cjson-v1']`, `current_validity: CurrentValidity`. |
| NoveltyReadback | `id: UUID`, `project_id: UUID`, `claim_version: HashRef`, `search_coverage: SearchCoverageReadback`, `assessment: NoveltyOutcome`, `limitations: str`, `supersedes_assessment: HashRef \| None`, `assessed_by: UUID`, `created_at: datetime`, `created_by: UUID`, `content_hash: str`, `hash_scheme: Literal['sha256-cjson-v1']`, `current_validity: CurrentValidity`, `supersedes_assessment_id: UUID \| None`, `superseded_by_assessment_id: UUID \| None` (derived chain navigation; director, 2026-10-14). |
| CoverageQuality | `observed_at: datetime`, `captured_unresolved_result_count: None`, `current_unresolved_result_count: int`, `selected_scope: Literal[True]`, `screening_captured: Literal[False]`, `attempts: tuple[AttemptQuality, ...]`, `uninvoked_providers: tuple[str, ...]`, `warnings: tuple[QualityWarning, ...]`. |
| AttemptQuality | `execution_id: UUID`, `attempt_id: UUID`, `provider_id: str`, `provider_version: str \| None`, `status: Literal['RESERVED','SUCCEEDED','RETRYABLE_FAILURE','PERMANENT_FAILURE','CANCELLED','UNKNOWN']` (existing PR2-04 enum unchanged), `failure_code: str \| None`. |
| CurrentValidity | `observed_at: datetime`, `usable_for_current_judgment: bool`, `warnings: tuple[QualityWarning, ...]`. No mutation of historical outcome. |

`PriorArtKind` is a StrEnum with exactly the six §3.2 literals. `NoveltyOutcome`
is a StrEnum with exactly the three §3.3 literals; only INCONCLUSIVE is admitted.
`QualityWarning` is a StrEnum with `NO_INVOKED_QUERIES`, `FAILED_ATTEMPT`,
`CANCELLED_ATTEMPT`, `UNKNOWN_ATTEMPT`, `UNINVOKED_PROVIDER`, `PARTIAL_RESULTS`,
`UNRESOLVED_RESULTS`, `FILTER_COMPLIANCE_UNPROVEN`, `SCREENING_NOT_CAPTURED`,
`INPUT_CURRENTLY_UNUSABLE`. Warnings sort lexically and deduplicate. Always include
FILTER_COMPLIANCE_UNPROVEN and SCREENING_NOT_CAPTURED in this slice. Limits and
narratives explain language/date/index gaps; warnings do not certify completeness.

Execution/evidence input tuples contain 1–100 distinct IDs. Output sets sort by
UUID; providers sort lexically after NFC normalization. Provider IDs/versions are NFC strings of 1–128 characters, matching existing
SearchQueryRecord validation; versions may be null where the owning search
contract allows it. Do not truncate provenance. History
output attempts may exceed 100 because they are derived, not caller collections.
Do not apply input limits to an authorized legacy history read. No pagination or
latest-assessment query is introduced. A related-detail authorization failure
denies the whole nested read with FORBIDDEN; never emit partially disclosed history.

## 12. Implementation guide — after separate authorization

### 12.1 DDL sketch and guard inventory

Create one forward migration following the current Alembic head. The filename is
`migrations/versions/<next_revision>_pr2_18_novelty_prior_art.py`; allocate its
prefix only after PR2-15/16 migrations are known. No schema change is made by this
proposal. The following is the exact proposed physical shape. All unspecified
NULL rules are explicitly NOT NULL. Constraint names are stable error targets.

Define two `IMMUTABLE STRICT` Boolean helper functions before these tables:
`pr218_valid_providers(JSONB)` accepts only an array of nonblank NFC strings in
strict lexical order with no duplicates (empty is allowed).
`pr218_valid_time_scope(JSONB)` accepts only the two keys `from` and `through`,
ISO date strings or JSON null, at least one date, valid Gregorian dates and
nondecreasing bounds. Catch invalid date casts and return false. Neither helper
queries another table. These enforce named structured values, not semantic JSON.

```sql
CREATE TABLE search_coverage (
  id UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  created_by UUID NOT NULL,
  search_plan_version_id UUID NOT NULL,
  providers JSONB NOT NULL,
  query_count INT NOT NULL,
  result_count INT NOT NULL,
  resolved_source_count INT NOT NULL,
  time_scope JSONB NULL,
  coverage_limitations TEXT NOT NULL,
  content_hash CHAR(64) NOT NULL,
  hash_scheme VARCHAR(32) NOT NULL,
  CONSTRAINT pk_pr218_coverage PRIMARY KEY (id),
  CONSTRAINT fk_pr218_coverage_created_by FOREIGN KEY (created_by)
    REFERENCES actors(id) ON DELETE RESTRICT,
  CONSTRAINT fk_pr218_coverage_search_plan_version_id FOREIGN KEY (search_plan_version_id)
    REFERENCES literature_search_plan_versions(id) ON DELETE RESTRICT,
  CONSTRAINT ck_pr218_coverage_counts CHECK (query_count >= 0 AND result_count >= 0 AND resolved_source_count BETWEEN 0 AND result_count),
  CONSTRAINT ck_pr218_coverage_providers CHECK (pr218_valid_providers(providers)),
  CONSTRAINT ck_pr218_coverage_time_scope CHECK (time_scope IS NULL OR pr218_valid_time_scope(time_scope)),
  CONSTRAINT ck_pr218_coverage_text CHECK
    (length(btrim(coverage_limitations)) > 0 AND char_length(coverage_limitations) BETWEEN 1 AND 16384),
  CONSTRAINT ck_pr218_coverage_hash CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  CONSTRAINT ck_pr218_coverage_scheme CHECK (hash_scheme = 'sha256-cjson-v1')
);
CREATE INDEX ix_pr218_coverage_created_by ON search_coverage (created_by);
CREATE INDEX ix_pr218_coverage_search_plan_version_id ON search_coverage (search_plan_version_id);
CREATE TABLE search_coverage_executions (
  id UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  created_by UUID NOT NULL,
  search_coverage_id UUID NOT NULL,
  search_execution_id UUID NOT NULL,
  CONSTRAINT pk_pr218_coverage_execution PRIMARY KEY (id),
  CONSTRAINT fk_pr218_coverage_execution_created_by FOREIGN KEY (created_by)
    REFERENCES actors(id) ON DELETE RESTRICT,
  CONSTRAINT fk_pr218_coverage_execution_search_coverage_id FOREIGN KEY (search_coverage_id)
    REFERENCES search_coverage(id) ON DELETE RESTRICT,
  CONSTRAINT fk_pr218_coverage_execution_search_execution_id FOREIGN KEY (search_execution_id)
    REFERENCES literature_search_executions(id) ON DELETE RESTRICT,
  CONSTRAINT uq_pr218_coverage_execution_pair UNIQUE (search_coverage_id, search_execution_id)
);
CREATE INDEX ix_pr218_coverage_execution_created_by ON search_coverage_executions (created_by);
CREATE INDEX ix_pr218_coverage_execution_search_execution_id ON search_coverage_executions (search_execution_id);
CREATE TABLE prior_art_relations (
  id UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  created_by UUID NOT NULL,
  claim_version_id UUID NOT NULL,
  source_version_id UUID NOT NULL,
  relation VARCHAR(32) NOT NULL,
  rationale TEXT NOT NULL,
  assessed_by UUID NOT NULL,
  content_hash CHAR(64) NOT NULL,
  hash_scheme VARCHAR(32) NOT NULL,
  CONSTRAINT pk_pr218_prior_art PRIMARY KEY (id),
  CONSTRAINT fk_pr218_prior_art_created_by FOREIGN KEY (created_by)
    REFERENCES actors(id) ON DELETE RESTRICT,
  CONSTRAINT fk_pr218_prior_art_claim_version_id FOREIGN KEY (claim_version_id)
    REFERENCES claim_versions(id) ON DELETE RESTRICT,
  CONSTRAINT fk_pr218_prior_art_source_version_id FOREIGN KEY (source_version_id)
    REFERENCES source_versions(id) ON DELETE RESTRICT,
  CONSTRAINT fk_pr218_prior_art_assessed_by FOREIGN KEY (assessed_by)
    REFERENCES actors(id) ON DELETE RESTRICT,
  CONSTRAINT ck_pr218_prior_art_relation CHECK (relation IN ('IDENTICAL','HIGHLY_SIMILAR','PARTIAL_OVERLAP','RELATED','CONTRASTING','UNCLEAR')),
  CONSTRAINT ck_pr218_prior_art_assessor CHECK (assessed_by = created_by),
  CONSTRAINT ck_pr218_prior_art_text CHECK
    (length(btrim(rationale)) > 0 AND char_length(rationale) BETWEEN 1 AND 16384),
  CONSTRAINT ck_pr218_prior_art_hash CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  CONSTRAINT ck_pr218_prior_art_scheme CHECK (hash_scheme = 'sha256-cjson-v1')
);
CREATE INDEX ix_pr218_prior_art_created_by ON prior_art_relations (created_by);
CREATE INDEX ix_pr218_prior_art_claim_version_id ON prior_art_relations (claim_version_id);
CREATE INDEX ix_pr218_prior_art_source_version_id ON prior_art_relations (source_version_id);
CREATE INDEX ix_pr218_prior_art_assessed_by ON prior_art_relations (assessed_by);
CREATE TABLE prior_art_evidence_inputs (
  id UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  created_by UUID NOT NULL,
  prior_art_relation_id UUID NOT NULL,
  literature_evidence_id UUID NOT NULL,
  CONSTRAINT pk_pr218_prior_art_input PRIMARY KEY (id),
  CONSTRAINT fk_pr218_prior_art_input_created_by FOREIGN KEY (created_by)
    REFERENCES actors(id) ON DELETE RESTRICT,
  CONSTRAINT fk_pr218_prior_art_input_prior_art_relation_id FOREIGN KEY (prior_art_relation_id)
    REFERENCES prior_art_relations(id) ON DELETE RESTRICT,
  CONSTRAINT fk_pr218_prior_art_input_literature_evidence_id FOREIGN KEY (literature_evidence_id)
    REFERENCES literature_evidence(id) ON DELETE RESTRICT,
  CONSTRAINT uq_pr218_prior_art_input_pair UNIQUE (prior_art_relation_id, literature_evidence_id)
);
CREATE INDEX ix_pr218_prior_art_input_created_by ON prior_art_evidence_inputs (created_by);
CREATE INDEX ix_pr218_prior_art_input_literature_evidence_id ON prior_art_evidence_inputs (literature_evidence_id);
CREATE TABLE novelty_assessments (
  id UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  created_by UUID NOT NULL,
  claim_version_id UUID NOT NULL,
  search_coverage_id UUID NOT NULL,
  assessment VARCHAR(40) NOT NULL,
  limitations TEXT NOT NULL,
  assessed_by UUID NOT NULL,
  supersedes_assessment_id UUID NULL,
  content_hash CHAR(64) NOT NULL,
  hash_scheme VARCHAR(32) NOT NULL,
  CONSTRAINT pk_pr218_novelty PRIMARY KEY (id),
  CONSTRAINT fk_pr218_novelty_created_by FOREIGN KEY (created_by)
    REFERENCES actors(id) ON DELETE RESTRICT,
  CONSTRAINT fk_pr218_novelty_claim_version_id FOREIGN KEY (claim_version_id)
    REFERENCES claim_versions(id) ON DELETE RESTRICT,
  CONSTRAINT fk_pr218_novelty_search_coverage_id FOREIGN KEY (search_coverage_id)
    REFERENCES search_coverage(id) ON DELETE RESTRICT,
  CONSTRAINT fk_pr218_novelty_assessed_by FOREIGN KEY (assessed_by)
    REFERENCES actors(id) ON DELETE RESTRICT,
  CONSTRAINT fk_pr218_novelty_supersedes_assessment_id FOREIGN KEY (supersedes_assessment_id)
    REFERENCES novelty_assessments(id) ON DELETE RESTRICT,
  CONSTRAINT ck_pr218_novelty_outcome CHECK (assessment IN ('NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE','CLOSE_PRIOR_ART_FOUND','INCONCLUSIVE')),
  CONSTRAINT ck_pr218_novelty_initial_slice CHECK (assessment = 'INCONCLUSIVE'),
  CONSTRAINT ck_pr218_novelty_not_self CHECK (supersedes_assessment_id IS NULL OR supersedes_assessment_id <> id),
  CONSTRAINT ck_pr218_novelty_assessor CHECK (assessed_by = created_by),
  CONSTRAINT ck_pr218_novelty_text CHECK
    (length(btrim(limitations)) > 0 AND char_length(limitations) BETWEEN 1 AND 16384),
  CONSTRAINT ck_pr218_novelty_hash CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  CONSTRAINT ck_pr218_novelty_scheme CHECK (hash_scheme = 'sha256-cjson-v1')
);
CREATE INDEX ix_pr218_novelty_created_by ON novelty_assessments (created_by);
CREATE INDEX ix_pr218_novelty_claim_version_id ON novelty_assessments (claim_version_id);
CREATE INDEX ix_pr218_novelty_search_coverage_id ON novelty_assessments (search_coverage_id);
CREATE INDEX ix_pr218_novelty_assessed_by ON novelty_assessments (assessed_by);
CREATE UNIQUE INDEX uq_pr218_novelty_predecessor
  ON novelty_assessments (supersedes_assessment_id)
  WHERE supersedes_assessment_id IS NOT NULL;
```

Install the following functions and triggers in the same migration. The trigger
names below are literal naming patterns expanded once for each listed table.
No request-controlled session flag, superuser requirement or mutable seal column.

| Function / trigger name | Timing, tables and exact behavior |
| --- | --- |
| `pr218_immutable` / `trg_pr218_<table>_immutable` | BEFORE UPDATE OR DELETE on all five tables: raise SQLSTATE P17D1. |
| `pr218_parent_guard` / `trg_pr218_<table>_parent_guard` | BEFORE INSERT on the three hashed parents: exact frozen plan/Claim/source/coverage hash shape and binding; derive project through existing owning parents; verify same-project/access/validity inputs. Coverage rejects unless current transaction isolation is READ COMMITTED and pg_locks shows this backend already holding granted ShareLock on every table in N (director decision 3, 2026-10-14). Relation and novelty take Claim row FOR UPDATE before any closure-table locks, matching §12.2. Use P17D3 for structural violations. |
| `pr218_child_guard` / `trg_pr218_<table>_child_guard` | BEFORE INSERT on both child tables: parent's `xmin::text::bigint = pg_current_xact_id()::text::bigint`; else P17D1. Check same exact plan and terminal execution, or same exact source/project and VERIFIED evidence, respectively. Lock no existing parent material for update; input checks use §12.2 order. Direct-SQL insertion invokes the same table coordination before validation; new child rows cannot upgrade old locks. |
| `pr218_complete_coverage` / `trg_pr218_<table>_complete_coverage` | AFTER INSERT, DEFERRABLE INITIALLY DEFERRED constraint trigger on search_coverage and search_coverage_executions: 1–100 children, exact plan/project, terminal histories with no RESERVED attempt; recompute §3.1 counts/providers/time_scope from the transaction snapshot and require equality. Use P17D3. |
| `pr218_complete_prior_art` / `trg_pr218_<table>_complete_prior_art` | AFTER INSERT, DEFERRABLE INITIALLY DEFERRED on prior_art_relations and prior_art_evidence_inputs: 1–100 children, exact source/project and VERIFIED inputs, no digest-null binding; P17D3. |
| `pr218_novelty_chain` / `trg_pr218_novelty_chain` | BEFORE INSERT on novelty_assessments, after Claim exclusion: same derived project/exact Claim predecessor, no self/cycle; predecessor may be currently stale. Existing successor means P17D2; unique predecessor catches races. |

Only the newly inserted parent transaction may populate child sets; deferred
checks prevent empty or incomplete publication. Shared child `created_by` equals
parent `created_by`, checked in pr218_child_guard. Shared times use one trusted
creation instant per command. SHA recomputation and transitive closure remain
Application responsibilities, following existing adapters; DB checks independently
protect typed structure, state and aggregate honesty. An ordinary SQL role cannot
insert stronger outcomes, coverage without READ COMMITTED and preheld N SHARE locks, late children or false counts.
No trigger disables future valid source/review/impact events. Use the existing
normal-role permissions; do not give callers permission to bypass triggers.

Register the named predecessor uniqueness and new CHECKs in UoW error normalization.
P17D1/P17D2/P17D3 already normalize to immutable/state/provenance errors. Generic
23514 remains VALIDATION_ERROR; map `ck_pr218_novelty_initial_slice` specifically
to INVALID_STATE_TRANSITION. Map `uq_pr218_novelty_predecessor` to
CONCURRENT_MODIFICATION without operational retry. A populated downgrade refuses
with a sanitized explanation; an empty downgrade drops only these five tables,
indexes, triggers and helper functions. Never alter accepted migration history.

### 12.2 Exact lock order and transactions

Define the immutable table inventory `N` in novelty_repository.py as the following
literal, lexically sorted tuple. It matches the existing Decision closure/authority
inventory, adding plan ownership and all capture inputs. Do not dynamically import
private Decision constants or lock an entire schema. The capture-input additions
implement director decision 3, 2026-10-14; SHARE locks protect their phantoms.

```python
N = (
    'actor_subject_bindings', 'actors', 'artifact_versions', 'artifacts',
    'audit_findings', 'claim_versions', 'claims', 'correction_records',
    'datasets', 'experiment_spec_versions', 'experiment_specs',
    'impact_assessments', 'impact_targets', 'literature_evidence',
    'literature_evidence_review_events', 'literature_search_execution_events',
    'literature_search_executions', 'literature_search_plan_versions',
    'literature_search_plans', 'literature_search_provider_attempts',
    'literature_source_project_links',
    'literature_sources', 'metadata_observations', 'metric_definition_versions',
    'metric_definitions',
    'project_membership_events', 'project_memberships',
    'project_role_assignments', 'projects', 'runs', 'scientific_conclusions',
    'search_query_records', 'search_result_records', 'search_result_resolutions',
    'source_versions',
)
```

`LOCK TABLE <N in that order> IN SHARE MODE` is one statement. Acquire the final
lock modes directly; no upgrades. A table SHARE lock blocks normal-role inserts,
updates and deletes into mutable authority/validity inputs. No command writes to
N. The distinction between coverage and the Claim commands below is intentional:
coverage uses READ COMMITTED and its N lock is the FIRST SQL statement; no
SET LOCAL, advisory lock, SELECT or authorization query may precede it. Initial principal shape validation is in memory.

| Command | Exact ordered operations |
| --- | --- |
| record_search_coverage | New ordinary READ COMMITTED UoW; lock N SHARE as the FIRST SQL statement; then `SET LOCAL lock_timeout='10s'; SET LOCAL statement_timeout='30s';`; request advisory lock `SELECT pg_advisory_xact_lock(hashtextextended('pr218:coverage:' \|\| $1::uuid::text, 0))` with the canonical request ID bound as parameter $1; authorize current readers at DB clock; read existing parent/children for replay; if new, authorize writers, read exact plan then UUID-sorted execution/attempt/query/result/resolution rows under the held SHARE locks; no FOR UPDATE on capture rows; compute material; final clock/authorization/validity check; insert parent and UUID-sorted children; force deferred checks, final clock check, commit. |
| record_prior_art_relation | READ COMMITTED UoW; same timeouts; request advisory `SELECT pg_advisory_xact_lock(hashtextextended('pr218:prior_art:' \|\| $1::uuid::text, 0))` with the canonical request ID bound as parameter $1; ClaimVersion FOR UPDATE by exact ID; lock N SHARE; authorize readers; replay check; if new, authorize writers; read Claim owning row, SourceVersion, UUID-sorted evidence under held N; verify exact closure/hashes/validity; final clock check; insert parent and UUID-sorted children; force deferred checks, final clock check, commit. |
| record_novelty_assessment | READ COMMITTED UoW; same timeouts; request advisory `SELECT pg_advisory_xact_lock(hashtextextended('pr218:novelty:' \|\| $1::uuid::text, 0))` with the canonical request ID bound as parameter $1; ClaimVersion FOR UPDATE; lock N SHARE; authorize readers; replay check; if new, authorize writers and INCONCLUSIVE guard; read Claim owning row, immutable coverage and UUID-sorted execution children; lock predecessor FOR UPDATE when nonnull; reread successor existence after any wait; verify chain/closure/hashes/validity; final clock check; insert parent; force deferred checks, final clock check, commit. |
| Three exact-ID reads | REPEATABLE READ UoW with no Application writes; authorize at fresh clock; read parent then UUID-sorted children and exact hash refs within one snapshot, then timestamped current quality/validity; final current read-entitlement clock check; return typed DTO. No explicit table locks, advisory locks, target row locks, writes or retries that create records. Director review correction (2026-10-14): exact-ID snapshot reads do not require N SHARE locks; the coverage write protocol above is unchanged. |

The bound request ID uses the canonical lowercase hyphenated UUID text required
by [§11.3](#113-dto-fields-python-types-and-limits); `$1::uuid::text` preserves
that lock-key format. Copy SQL from the rendered table: raw Markdown escapes
`\|\|` render as PostgreSQL's `||` concatenation operator.

The request namespaces are distinct; no command acquires a second namespace.
No project row lock precedes a Claim row lock. Source/evidence locks are covered
by N and do not acquire FOR UPDATE. Coverage never takes Claim row locks, avoiding
a cycle with Claim commands that take their target before N. Table SHARE locks
stabilize mutable authority/validity and protect capture-input INSERT phantoms.

Force `SET CONSTRAINTS ALL IMMEDIATE` before the last clock check. This makes any
trigger/FK wait happen before the final authorization. Use fresh `clock_timestamp()`
after each blocking wait. Coverage rereads its already protected authority rows;
it never claims SSI can refresh a snapshot. Scheduled expiry is checked against
the advancing clock. READ COMMITTED commands reread after waits. On any wait after
the final check, repeat the check before commit. The immutable parent and sealed
children are the attributable record history.
No separate novelty event table or audit-finding side effect is introduced.
Replay/denial creates no record; use existing operational logging separately.

Retry exactly three total fresh-UoW attempts for 40001/40P01, with no delay and
no external call. Enable the existing SQLSTATE deadlock normalization for
coverage, without begin_serializable. Classify retry eligibility from SQLSTATE, not every business
CONCURRENT_MODIFICATION. The third conflict emits that code. Do not retry
unique-predecessor loss, timeout or uncertain commit. Every retry redoes locks,
reads, hashes and trusted-clock authorization. Race tests must demonstrate legal
serialization outcomes; they must witness blocked resolution writes and rejection of stale capture
without the READ COMMITTED/preheld-lock protocol.

### 12.3 Ordered build steps and module paths

1. Create `src/researchbase/domain/novelty.py`. Define the enums, closed time scope,
   typed records, narrative/set normalization and three literal R2 material builders.
   Reuse foundation.hashing and exact reference helpers. No ORM or transport import.
2. Create `src/researchbase/application/novelty.py`. Put §11.3 command/readback
   dataclasses and NoveltyService here, following application/decision.py. Add
   typed NoveltyRepository/UoW members in `src/researchbase/application/ports.py`.
   Implement accounting and immutable replay, then the three admission paths.
3. Add the §12.1 migration after the current head. Create
   `src/researchbase/persistence/novelty_repository.py` using named SQL statements
   like decision_repository.py/internal_review_repository.py. Implement N locks,
   capture predicates, child reads/inserts and derived project lookup. No ORM
   model is required by this SQL layout; do not add a parallel material owner.
4. Wire `novelty` into `src/researchbase/persistence/uow.py`, transaction factory
   and typed port. Add only the named constraint/error normalizations above.
   Implement isolated retry classification and existing operational logging. The parent supplies attributable history;
   do not invent a canonical event or AuditFinding. No dependency additions.
5. Add NoveltyService to `src/researchbase/api/app.py` ServiceBundle/build_services
   and `src/researchbase/cli/composition.py` service construction. Extend
   `src/researchbase/api/routes.py` with closed request/response models and
   the same trusted principal injection as Decision. Routes are POST/GET pairs:
   `/projects/{project_id}/search-coverage[/{id}]`,
   `/projects/{project_id}/prior-art-relations[/{id}]`,
   `/projects/{project_id}/novelty-assessments[/{id}]`.
   Brackets here mean GET uses /{id}; POST uses the collection path. GET returns
   200; POST returns 200 for both first write and exact replay. No list endpoint.
6. Extend `src/researchbase/cli/commands/literature.py` and composition wiring in
   `src/researchbase/cli/composition.py`. Commands are `record-search-coverage`,
   `read-search-coverage`, `record-prior-art-relation`, `read-prior-art-relation`,
   `record-novelty-assessment`, `read-novelty-assessment` under the existing
   literature group. Use shared transport/output/error envelope; add the proposed
   unexpected-error fallback in cli/errors.py and the shared invocation boundary.
   Accept the same fields as the API; callers never supply assessor or accounting.
7. Create the tests in §12.4; run focused PostgreSQL tests first, then inherited
   regressions and all thirteen §8 architecture obligations. Record exact commands,
   counts, server version and no P0/P1 findings before bounded engineering acceptance.
   Stop. Do not build §12.5 to make a test green.

### 12.4 Test artifacts and required cases

Create `tests/integration/phase2/pr2_18_fixtures.py` with `novelty_env`: a disposable
PostgreSQL 18.x database via existing `phase2_database_url`, migrated to head;
OWNER, RESEARCHER, independent HUMAN REVIEWER and VIEWER with live verified
credentials; a second project; frozen Claim with unchanged Phase 1 closure;
one exact frozen search plan; terminal SUCCEEDED/FAILED/CANCELLED/UNKNOWN
executions; query/results with duplicate hits and zero-result cases; exact
source versions, source project links, VERIFIED quotation evidence and resolution
rows. Reuse the construction patterns of `setup_m2`, `m3`, and `conclusion_env`
in existing metadata/evidence/review suites; do not import test modules as fixtures.
Use exported fixture builders or this explicit new helper. Two independent engines
and backend PIDs are required for race fixtures; expiry is database-derived.

| File to create | Cases required in addition to the detailed §8 obligations |
| --- | --- |
| `tests/unit/phase2/test_pr2_18_novelty_contract.py` | Every DTO field/type, unknown field, strict UUID/int, Unicode/NFC/blank/limit boundaries, duplicates and canonical set order; all six relations and three outcome literals; exact stronger-outcome Application denial; closed date bounds including leap date; quality enums, null historical unresolved count and no first-ever rendering. |
| `tests/unit/phase2/test_pr2_18_hash_vectors.py` | Independently written literal canonical JSON/digest vectors for all three payloads; null predecessor/time, Unicode, sorted refs/providers, child permutation equality, changed material inequality; no extra actor/time/quality keys; Phase 1 hash vectors unchanged. Never use production material builder as expected oracle. |
| `tests/integration/phase2/test_pr2_18_search_coverage.py` | novelty_env; record-based accounting including retries and failed queries, ambiguous/source-only/conflicting resolutions, no merge deduplication, corruption denial, zero invocation, selected scope, wrong plan/project and active execution denial, incomplete terminal history, unchanged capture after later resolution/restart, timestamped current diagnostics. |
| `tests/integration/phase2/test_pr2_18_prior_art.py` | novelty_env; all six relations; wrong exact source/project, unfrozen/retracted source, evidence not VERIFIED, corrupt closure and empty evidence deny atomically; contradictory records retained; no EvidenceRelation/support/Issue/Decision/grant writes. |
| `tests/integration/phase2/test_pr2_18_novelty.py` | novelty_env; INCONCLUSIVE creation/read, each stronger enum denied with zero new records, exact same-Claim chain, foreign/self/cycle/fork denial, stale predecessor correction, independent roots and new Claim root; warnings versus saved judgment; author identity and separate detail authorization. |
| `tests/integration/phase2/test_pr2_18_replay.py` | novelty_env; all commands exact replay/restart, permuted ID set replay, changed material conflict, different actor and lost read entitlement deny, write-role loss/current invalidity historical read, no duplicate parents/children, unknown-commit exact UUID recovery. |
| `tests/integration/phase2/test_pr2_18_schema.py` | Real catalog names/types/nullability/indexes; clean install and populated upgrade preservation; empty downgrade and populated refusal; normal-role SQL stronger outcomes, capture without READ COMMITTED/preheld N SHARE locks, false counts/providers, late child insert/update/delete, empty deferred sets, wrong project/source, FK restrictions and named predecessor uniqueness. |
| `tests/integration/phase2/test_pr2_18_concurrency.py` | Both resolution INSERT/capture orderings and empty-range phantoms; SHARE lock ordering and fail-closed stale-capture reproduction (director decision 3, 2026-10-14); 40001/40P01 exactly three attempts, nonretryable business conflicts/timeouts; same UUID single parent/child set and successor single winner; source dispute/retraction, credential revocation and scheduled role/credential expiry across each wait; observable lock evidence and final clock; failure between parent/child and during deferred checks rolls back all writes. |
| `tests/unit/phase2/test_pr2_18_transports.py` | Every pinned HTTP/CLI mapping, sanitized fallback, strict schemas and same principal boundary, all six route/CLI commands, POST first/replay 200, GET 200, no nested disclosure or ORM entities. |
| `tests/architecture/test_pr2_18_boundaries.py` | All thirteen named §8 obligations, Domain import boundary, no provider call in DB transaction, no new semantic JSON owner, no missing-basis/approval/revision/publication side effects. |

Future regression command (after implementation; not a claim of present tests):
`uv run pytest tests/unit/phase2/test_pr2_18_*.py tests/integration/phase2/test_pr2_18_*.py tests/architecture/test_pr2_18_boundaries.py`.
Then run `uv run pytest tests/unit tests/architecture tests/integration tests/e2e`
on disposable PostgreSQL 18.x, plus `uv run ruff check .`,
`uv run ruff format --check .`, and `uv run pyright`. Preserve inherited source,
search, metadata, evidence, Claim, conclusion, manuscript, review and Decision
suites. Include RevisionAction/Approval regressions only once their separately
approved implementation exists. Missing future contracts are not passing tests.

### 12.5 Not in this slice

| Deferred behavior | Missing contract required before building it |
| --- | --- |
| CLOSE_PRIOR_ART_FOUND | Exact immutable assessment-to-PriorArtRelation/evidence membership contract, scope-specific close-art criteria and compatible new hash material version. |
| NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE | Complete intended probe/execution inventory and immutable per-result screening dispositions/criteria, negative-probe retention and exact assessment basis; bounded ADR if existing patterns cannot represent them. |
| Exact historical unresolved count after restart | Deterministic capture-basis/material amendment with concrete membership and hash/version compatibility. No new column here. |
| Authoritative correction of conflicting PriorArtRelation | Typed correction/supersession selection contract; registered relation has no predecessor field. |
| Novelty-target review or RevisionAction result | Exact review target and result-shape integration contracts; existing seven revision result shapes remain unchanged. |
| Novelty-driven approval/READY/package attachment | Typed publication/governance integration contract, not inferred from PR2-16/17; no grant consumption here. |
| Automatic impact propagation | Separate current-validity/impact propagation contract; this slice only invokes existing read projections. |

## 13. Open questions for the owner — override register

| Owner may override | Decision adopted in this draft |
| --- | --- |
| Initial scope or full three-outcome PR? | Approve coverage + six comparisons + INCONCLUSIVE first, explicitly label bounded acceptance; defer stronger enums until exact basis is frozen. Do not equate this with full PR2-18 by default. |
| How is an assessment's exact prior-art/screening basis bound? | Reuse existing relation/snapshot patterns only if deterministic membership can be proved. Otherwise require a bounded ADR, concrete FKs and new material version before either stronger outcome. No current-set/time-cutoff/free-text substitute. |
| How is captured unresolved count reported after restart? | Initial scope returns unknown historical count and timestamped current diagnostics. If exact historical quality reporting is required, freeze a minimal deterministic capture-basis/material amendment before implementation; never derive it by subtracting unique sources. |
| Does coverage include all executions of the plan? | Caller declares an exact set; always disclose this is selected scope. For any future negative finding require deterministic complete intended search/probe inventory and no omitted failed/adverse branches; selection alone cannot certify it. |
| Query/source counts and providers? | Use §3.1 record-based accounting, exact source IDs and actually invoked providers; include retry failures and ambiguous/source-only resolutions honestly. These definitions are pinned; zero invoked queries means zero counts, empty providers and an explicit warning. |
| What proves screening and a negative novelty probe? | No new subsystem in initial slice; explicitly report absent screening. Full scope needs exact dispositions/criteria and retained negative probes through approved existing patterns or bounded ADR. SUCCEEDED retrieval is insufficient. |
| Are IDENTICAL/HIGHLY_SIMILAR the only close categories? | Treat them as candidates needing inspected evidence, never automatic truth. PARTIAL_OVERLAP/UNCLEAR cannot justify a negative finding. Freeze scope-specific comparison criteria before stronger outcomes. |
| Must all comparison evidence be VERIFIED? | Yes for initial canonical comparison admission; unreviewed Agent outputs remain candidates. Existing independent Human evidence-verification policy remains unchanged. Assessor need not be an independent HUMAN reviewer. |
| Correction, contradiction and supersession policy? | Nonforking same-exact-Claim assessment chains, independent roots visible; no “latest wins.” PriorArtRelation has no approved supersession field, so preserve conflicting records and defer authoritative correction selection. |
| Who may record/read, and are new DTO bounds acceptable? | Effective OWNER/RESEARCHER writers; authenticated current project readers under §4; Human/Agent same boundary. Use 100-ID/16,384-character limits and per-object nested disclosure; owner authority cannot prove novelty. |
| Must novelty be a new approval gate or review target? | No automatic gate, no new RevisionAction result shape, no new Decision purpose. Contract exact typed integration separately; preserve existing OPEN/BLOCKING and invalid-fact rules. |
| How are retraction/dispute and historical captures coordinated? | Preserve immutable bytes, derive current unusability/warnings through existing validity/impact paths, and use §12.2’s exact lock order and READ COMMITTED/preheld-SHARE capture (director decision 3, 2026-10-14). Do not promise a new propagation engine or silently update saved counts. |

Every recommended answer above is adopted in §11. Owner override requires a
recorded disposition and corresponding body edits before freeze. The owner approved first-slice implementation on 2026-10-14; deferred behavior
requires separate approval.


## 14. Documentation verification note

The original proposal was verified as documentation only. Current first-slice
engineering checks and their limits are recorded in
[PR2-18 verification evidence](../../pr_evidence/PR2-18/VERIFICATION.md).
The full suite is reserved for the loop by the owner's latest task instruction;
no full-suite or Phase-exit success is implied by this contract.
