# PR2-04 — LiteratureSearchExecution + Query/Result Provenance

**Version:** 1.0, design-review candidate, 2026-10-05. **Status:** DESIGN ONLY — proposed freeze subject, not an accepted contract or implementation authorization.

**Accepted baseline:** `cdc50eb8b4c35602501741e9205b7e0f3a43509f`, branch `phase2/entry-gate`, checkout `/private/tmp/ResearchBase-phase2-recovered`. PR2-03 is closed. Current migration head: `0023a_search_plan_review_guards`. Frozen Phase 1 semantic baseline: `d2400fbeca835c89bd802a4e9d647bda01cfd115`.

This pack, the [acceptance matrix](PR2-04_Acceptance_Matrix_v1.0.md), and [proposed ADR-0011](../../docs/architecture/adr/ADR-0011-search-execution-attempt-accounting.md) form one review subject. They require independent design review and explicit approval of the supporting-schema admission before implementation. Authorship does not freeze or approve the proposal. Earlier contracts remain authoritative until that approval.

## 1. Purpose

Execute bounded literature retrieval against an exact frozen plan, preserving provider attempts, query/result provenance, uncertainty and crash boundaries. A search hit is neither a LiteratureSource identity nor LiteratureEvidence. Scientific `Run` remains separate. Produce an implementation-ready contract without enabling a live provider, implementing PR2-05, or reopening PR2-03.

## 2. Authoritative prerequisites and recovered sources

Source paths below are relative to the repository root. Section identifiers, not this pack's interpretation, locate the governing clauses.

| Ref | Source | Governing clauses |
|---|---|---|
| S01 | `docs/architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md` | §§55–57 schema budget/typed provenance; normative §§62, 69–79 layering, strong FKs, short commands, concurrency, hashes, immutable history. |
| S02 | `docs/architecture/02_Final_Architecture_Correction_Addendum_v1.0.md` | A2 Execution rename; A4 reference classes; A5 authority; A13 TDG-2; A17–A20 incorporation of corrected field/hash/temporal contracts; A21 governance replay is not a blanket literature replay exemption. |
| S03 | `docs/architecture/03_Global_Schema_and_Contract_Registry_v1.0.md` | Phase 2 registry: Execution is STATEFUL_OPERATIONAL; Query/Result are IMMUTABLE_RECORD; exact plan/execution/query FKs. |
| S04 | `docs/architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md` | §§9, 13–19, 30, 33, 38–41: additive migrations, no historical mutation, stable hash material, UTC, Application boundary, ADR triggers, compatibility tests. |
| S05 | `docs/architecture/05_Phase2_Development_Specification_v1.1_Harness_Integrated.md` | §§5.2–5.3 execution/query/result; §10 `SearchCapability.search`; §§12, 30–32 commands, split transactions, errors/API; §41.3 acceptance; §48 PR order. Older Run naming and resolved-source columns are superseded. |
| S06 | `docs/architecture/11_TDG2_Phase2_Technology_Decision_Gate_v1.0.md` and `docs/architecture/adr/ADR-0008-phase2-literature-technology-gate.md` | TDG2-01 and 06–10: frozen plan, bounded external calls outside transactions, retry policy, UNKNOWN, neutral candidates, credential/raw-data boundary; live adapter activation is separate. |
| S07 | `docs/architecture/12_Phase2_Architecture_and_Contract_Correction_v1.0.md` | §4 query binding/vendor-neutral material; §7 search schema, provider/request key uniqueness. |
| S08 | `docs/architecture/13_Phase2_Schema_Field_Contract_v1.0.md` | Shared physical rules and “Literature source, search and evidence” table: exhaustive semantic columns, six execution states, immutable terminal/query/result rows, appended resolutions. |
| S09 | `docs/architecture/14_Phase2_Design_Gap_Closure_R2_v1.0.md` and `docs/architecture/15_Phase2_Hash_Payload_Contract_R2_v1.0.md` | R2 precedence; literal SearchQueryRecord hash, normalization, zero-based contiguous ordinals, immutable scientific bindings. |
| S10 | `docs/architecture/16_Phase2_Identity_Ownership_and_Source_Contract_R2_v1.0.md`, `18_Phase2_Design_R3_Targeted_Remediation_v1.0.md`, `19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md` (same directory) | Identity/role/credential validity; contract 19 §1 TEMP-AUTH-01: locks → durable reread → fresh DB time → authorization, repeated on serialization retry. |
| S11 | `execution/phase2/PR2-00_Design_Execution_Pack_R2_v1.0.md` | Commands/TEMP-AUTH-01, PostgreSQL evidence, FORMAT-BASELINE-01. |
| S12 | `execution/phase2/PR2-01_Design_Execution_Pack_R2_v1.1.md` | Typed receipts, scoped request keys, exact replay/current entitlement, no raw persistence errors. |
| S13 | `execution/phase2/PR2-02_Source_Version_and_Merge_Execution_Pack_v1.0.md` | §§4–5 receipt/schema patterns; §§8–11 canonical errors, retry exhaustion, empty-only downgrade, regression proof. |
| S14 | `execution/phase2/PR2-03_Literature_Search_Plan_Execution_Pack_v1.0.md` and `PR2-03_Review_Remediation_Addendum_v1.0.md` (same directory) | §§7–12: literature authority/replay, accepted migrations and exact FROZEN plan consumption; PR2-04 owns execution only. |
| S15 | `docs/architecture/adr/ADR-0002-postgresql-18.md`, `ADR-0003-sqlalchemy-sync-psycopg.md`, `ADR-0005-content-addressed-artifact-store.md`, `ADR-0006-fastapi-typer-adapters.md` (same directory) | PostgreSQL 18, synchronous DB I/O, immutable artifact bytes, thin transport adapters. |
| S16 | `docs/harness/09_Harness_Integration_Specification_v1.0.md` | §§2–3, 16, 19: Harness cannot own canonical truth; independent review and evidence. |
| C01 | `src/researchbase/application/literature_search_plan.py`, `src/researchbase/persistence/literature_search_plan_repository.py`, `src/researchbase/persistence/uow.py`, `src/researchbase/foundation/errors.py`, `migrations/versions/0023a_search_plan_review_guards.py` | Existing conventions, subordinate to contracts: typed commands; three DB attempts for canonical concurrency; project advisory-before-row lock; current ErrorCode inventory and migration parent. Baseline UoW normalizes 40001, not 40P01; the latter is a PR2-04-specific obligation in §9. |

Prerequisites: accepted Phase 1, PR2-00, PR2-01, source-merge governance bridge, PR2-02, PR2-03. No new claim about their runtime acceptance is made by this design exercise.

Recovery inspected current architecture, execution packs, ADRs, production interfaces and all-ref Git history for PR2-04/search-execution subjects and PR2-04 paths. No earlier PR2-04 execution pack or abandoned implementation contract was found in reachable history. This is not proof that every unreachable Git object or external document is absent. The core schema is **not** unspecified: S08 already defines it; the remaining gap is operational attempt/recovery detail.

Precedence: frozen architecture and incorporated corrections → accepted ADRs → accepted Phase 2 contracts → accepted prior packs → unsuperseded Phase 2 specification → implementation conventions → proposed choices here. ADR-0011 proposes only the explicit admission described there; it cannot silently overrule S08.

Remediation incorporates independent-review defects F1–F4, not new higher-order authority: interrupted cancellation is resolved within S06's cancellation/crash model and S08's lifecycle; terminal receipts and complete receipt keys follow S12–S14; concurrency ownership is checked against C01 and S10. The review report is a defect report, not a replacement for those sources.

### 2.1 Design-decision ledger

`E` = explicit upstream; `I` = inherited convention; `D` = newly resolved detail requiring this design's approval.

| ID | Class | Decision and minimal rationale |
|---|---|---|
| D01 | E | Preserve S08's six states and three core tables; exact frozen plan, immutable query/result and terminal execution. |
| D02 | E/I | TX A / external / TX B / TX C; independently retry only each short DB transaction, never the entire external-call orchestration. |
| D03 | D | Add a dependent typed provider-attempt table, lifecycle event table and dedicated receipts (ADR-0011). Existing core rows cannot encode dispatch ownership and crash uncertainty without mutable JSON history or lost provenance. No new top-level aggregate/framework. |
| D04 | D | One selected provider per execution; 1–32 ordered explicit text queries; sequential bounded attempts. Multi-provider research uses separate executions. No strategy/query-generation engine in PR2-04. |
| D05 | D | UNKNOWN is terminal, not resumable or auto-reconciled. Recovery can close an unresolved reservation as UNKNOWN; it cannot invent a provider answer. A deliberate new execution is new retrieval, not reconciliation of the old fact. |
| D06 | E/D | Retry known-safe 429/transient 5xx/not-sent transport failures; uncertain delivery stops UNKNOWN. Application owns the loop; adapter/HTTP client hidden retries are disabled. |
| D07 | I/D | Reauthorize every DB effect and disclosure; no durable future-authority grant at TX A. Lost authority prevents TX B/C by that caller. Another currently entitled caller can recover bookkeeping without inventing results. |
| D08 | D | Public create/execute/cancel/recover return immutable command-admission DTOs; current state/provenance is a separate authorized query. This preserves exact receipt replay across a multi-transaction operation. |
| D09 | E/D | Minimal `SearchCapability.search` port and deterministic fake are prerequisites for execution testing, not PR2-06 live-adapter implementation. HTTP/CLI execution surfaces are required by S05 §32. |
| D10 | D | No raw-provider-payload retention/cache in PR2-04. Canonical neutral fields and allowlisted operational metadata suffice; immutable raw-artifact retention remains a later adapter decision. |
| D11 | D | Add a literal SearchResultRecord own-hash payload to implement S08's own-hash rule where S09 supplies no result template. No existing hash changes. |
| D12 | D | Boundaries, DTO limits, attempt caps, failure reasons, transport paths and recovery deadlines below are concrete proposed details, not claims that upstream prescribed their exact values. |

## 3. Scope

Execution domain types and lifecycle; three core tables plus the three supporting tables admitted by ADR-0011; neutral provider port, deterministic fake and synchronous Application orchestration; query/result/provenance reads; HTTP/CLI parity; real PostgreSQL concurrency/crash/idempotency/authority tests; one additive migration; PR2-04 host mode and requirement-level evidence. No live calls during acceptance.

## 4. Non-goals

LiteratureEvidence, source creation/resolution/merge/dedup, `search_result_resolutions`, evidence verification/support snapshots, PDF fetch/parsing, embeddings/RAG/LLM summaries, ranking models, query generation/perspective discovery, STORM, UI, autonomous agents, generic jobs/queues/workflows, distributed worker leases, provider marketplace, cache or raw-response storage, live adapter activation, reconciliation of a terminal UNKNOWN. PR2-05/06/08 keep their respective responsibilities. No modifications to accepted plan/hash/abandon/retry/identity semantics or Phase 1.

## 5. Domain model

**LiteratureSearchExecution:** UUID operational identity; immutable project and exact plan-version FK; immutable admitted request/context; mutable lifecycle and positive `row_version`, immutable after terminal. `requested_by` is the create actor. `executed_by` initially equals that actor and is set once to the first execution actor when PLANNED→RUNNING; after that it is historical attribution, not current authority. Actual provider-attempt and recovery actors are separately attributed. The plan must be FROZEN at creation and initial execution start. If it becomes SUPERSEDED after start, continue against the same immutable, hash-verified version; never resolve `current_version_id`. Existing frozen closure remains valid historical input.

`idempotency_key` is the public create `request_id`, unique across **the project**, as required by S08. It is not a credential. Execution UUID is the end-to-end correlation ID; each attempt has a separate UUID/provider request key. No reuse of execution ID for a rerun. Counts are projections from attempts/query/results, not second mutable counters.

**SearchQueryRecord:** one immutable record for a provider invocation whose entry is observed by the orchestrator. It records the exact normalized text passed to the port, provider ID/version, optional perspective, execution-scoped ordinal and invocation-entry UTC time. `executed_at` means entry into the bounded search invocation, **not proof of remote processing**; delivery certainty belongs to its attempt. Crash recovery without an observed invocation time creates no fictitious query record. The durable reservation still identifies the intended query from immutable execution context.

One execution can issue multiple queries and repeated attempts. Each observed retry creates a distinct query record even for identical text. Ordinal is assigned at TX B under execution lock, zero-based contiguous over persisted query records, independent of attempt numbers. S09's hash includes ordinal/execution identity, so repeated identical text is not deduplicated. `query_type` is TEXT only in v1 and is part of the admitted context, not an invented core-table enum.

**SearchResultRecord:** UUID immutable provider hit owned by one query. `external_identifier` is an opaque provider result identifier, not a canonical source ID. Title/url/snippet/finite score are neutral candidate metadata. Rank is the zero-based provider response-order position. Repeated provider IDs at different positions remain separate hits; same position cannot repeat. No source FK is invented, no ingestion occurs, no scientific support is asserted. Corrections require a new retrieval; no in-place repair.

**Provider attempt:** dependent operational record, created before possible I/O, fixed reservation facts plus a write-once outcome. The attempt UUID is the locally generated provider request key; optional `provider_request_id` is the provider's returned correlation token. Exactly one unsealed attempt per execution. No claim of provider-side exactly-once processing.

## 6. Lifecycle and transition matrix

Execution states are exactly `PLANNED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCELLED`, `UNKNOWN`. First two are nonterminal; last four terminal. Terminal execution columns never change; no reconciliation command is implemented.

| From | To | Allowed | Trigger/conditions |
|---|---|---|---|
| absent | PLANNED | yes | TX A create, frozen plan and current authority; row_version=1. |
| PLANNED | RUNNING | yes | First committed reservation; recheck FROZEN plan/authority; started_at=fresh DB time. |
| PLANNED | CANCELLED | yes | Durable CANCEL_REQUESTED, no attempt/dispatch; TX C2 (cancellation's TX C), including authorized recovery; started_at remains null. |
| RUNNING | SUCCEEDED | yes | TX C; every input query has a successful sealed attempt; no unresolved attempt/cancel request. Empty successful hit list is valid. |
| RUNNING | FAILED | yes | TX C; permanent/malformed failure, exhausted safe retry, or explicit recovery stopping a known incomplete run; all attempts sealed. Earlier hits retained. |
| RUNNING | CANCELLED | yes | TX C; cancellation won before next reservation, or provider guarantees cancelled/not sent; no unresolved delivery. |
| RUNNING | UNKNOWN | yes | TX C; sealed uncertain outcome (including expired unresolved reservation); never relabel uncertainty as cancellation/failure. |
| PLANNED | SUCCEEDED/FAILED/UNKNOWN | no | No invocation evidence; invalid state transition. |
| RUNNING | PLANNED | no | Never rewind execution. |
| any terminal | any different state | no | Immutable; new execution for new retrieval. |
| state | same state | no lifecycle write | Exact receipt replay/read only; no row-version increment. |

Successful execution writes increment row_version exactly once per mutation transaction, including reservation, outcome, cancellation request and terminal transition. An event records prior/new status and prior/new row_version (same-status events are operational mutations). CAS mismatch is `CONCURRENT_MODIFICATION`; no last-write-wins. No status is inferred solely from the last HTTP response.

Attempt states: `RESERVED` → exactly one of `SUCCEEDED`, `RETRYABLE_FAILURE`, `PERMANENT_FAILURE`, `CANCELLED`, `UNKNOWN`; never reopen. A sealed outcome is immutable. Execution success requires a successful attempt for **each** query index, not merely some results.

## 7. Transaction boundaries

```text
TX A-create: execution PLANNED + create receipt + CREATED event; commit
TX A-reserve: authorize + reserve attempt + RUNNING/ATTEMPT_RESERVED event
              + first execute-admission receipt; commit and release UoW/connection
SearchCapability.search(request, context): NO open DB transaction or DB lock
TX B: authorize + seal attempt + append observed query/results + OUTCOME_RECORDED; commit
  [if safe retry/next query: bounded wait outside DB, then a new TX A-reserve]
TX C: authorize + derive and commit terminal state + FINISHED event; commit
```

These are short Application commands called by one Application orchestrator. The provider/transport never owns a UoW. The split is the explicit S05 §30/TDG2-06 exception to ordinary one-command/one-transaction operation. Every loop iteration has its own committed reservation. Result batches and attempt seal are atomic, never incremental partial success. TX C never calls a provider and cannot run until required outcomes are durable.

Only the process receiving a definite successful reservation commit with `newly_reserved=true` may invoke that attempt, once. Reading an existing reservation or receipt never gives dispatch ownership. A lost reservation-commit acknowledgment is **not** permission to call; observe/recover it as unresolved. No network call or backoff is inside a DB retry closure. Connection/session closure must occur before entering the provider. Evidence must verify this with both UoW instrumentation and PostgreSQL transaction/lock observation.

Cancellation has separate short transactions: **TX C1** admits intent/receipt, commits and releases locks; **TX C2** is the existing TX C finalizer applied to that durable intent after reacquiring locks and authority. C1 and C2 are not one atomic cancellation. Their exact coordinates and interrupted-completion path are specified in §10. Recovery may perform C2 without C1 when intent is already committed; it never invokes the provider.

## 8. Provider boundary

Preserve S05's interface: `SearchCapability.capability_id`, `.version`, `.search(request, context) -> SearchResponse`. Add typed value DTOs, not ORM/provider JSON. This is a minimal dependency for PR2-04; PR2-06 owns production adapters.

`SearchRequest` has exactly: execution UUID, attempt UUID, provider request key UUID (=attempt UUID), exact frozen plan reference (version UUID + verified content hash) and immutable plan material DTO, query index, normalized query text, nullable perspective, query_type=TEXT, provider ID and adapter version, max_results. IDs here are a typed invocation DTO, never a JSON persistence reference list.

`SearchCallContext` has: correlation ID (=execution UUID), UTC deadline, monotonic remaining timeout, cooperative cancellation token. No DB handle, secret, caller-controlled URL, retry callback or authority grant. Adapter configuration is injected outside the DTO. A provider selection is an allowlisted identifier/version pair; it must be in the plan's `planned_providers` and compatible with source_scope. Reject unsupported combinations before creating an execution. The fake's registration declares supported source scopes explicitly; no source-scope inference from a URL.

`SearchResponse` is a closed tagged union. Common fields: provider ID/version, normalized query echo, nullable provider_request_id, delivery certainty (`NOT_SENT`, `RESPONSE_RECEIVED`, `MAY_HAVE_BEEN_SENT`), allowlisted warning codes, nullable bounded Retry-After seconds. Success adds an ordered list of typed hits and retrieved_at. Failure adds the reason in §16 and a safe-retry classification; it never embeds exception text/headers. The orchestrator separately captures invocation-entry and response-return UTC times; these are not taken from untrusted response fields. The Application validates identity/echo, limits and all types before persistence. Success requires RESPONSE_RECEIVED; uncertain delivery requires UNKNOWN regardless of suggested retryability. No partial hit salvage from a malformed response. An unexpected adapter exception without a proven NOT_SENT classification is UNKNOWN; retain only a sanitized reason, not exception text. A malformed response still uses the intended query and orchestrator-observed times for its failed-attempt provenance, never malformed response material.

Each hit has exactly `external_identifier?`, nonblank `title`, `url?`, `snippet?`, finite decimal `provider_score?`. The adapter preserves provider-returned order; optional native numeric ranks/extra vendor fields stay adapter-side. The Application assigns contiguous rank. Provider ID/version and invocation/request/time facts are canonical operational metadata. HTTP fields/internal parsing data are adapter metadata, not new canonical columns. Raw payload retention and caches are disabled in this PR; later retention must use redacted, licensed immutable ArtifactVersion bytes and a separately reviewed concrete linkage, never inline provider JSON.

Limits (D12): query_count 1–32; normalized query 1–4096 characters; perspective ≤256; provider/strategy identifiers and versions 1–128; max_results 1–100 per query; title 1–2048; identifier ≤1024; URL ≤4096 (http/https only, no userinfo/credentials); snippet ≤4096; provider request ID ≤256; warning codes from `RESULTS_TRUNCATED`, `PARTIAL_COVERAGE`, `RATE_LIMITED` only, no free text. Optional empty text normalizes to null; required blank text rejects. No truncation of accepted fields silently. Oversized response is malformed. Provider material is untrusted text, not instructions.

## 9. Retry domains and recovery separation

**DB retries:** follow the existing bounded three-attempt convention for canonical `CONCURRENT_MODIFICATION` (initial attempt plus at most two retries), independently for each short phase, including C1/C2. Existing UoW normalization covers PostgreSQL `40001`. Mapping `40P01` to `CONCURRENT_MODIFICATION` is a **PR2-04-SPECIFIC IMPLEMENTATION OBLIGATION**, not inherited global behavior. Every new transaction repeats locks, durable reads, fresh DB clock and authorization. Attempt counts/PIDs/SQLSTATE remain observable. A CAS conflict or authoritative terminal/fenced outcome cannot be bypassed by blindly replaying writes. Exhaustion returns canonical concurrency error without current-phase partial effects; earlier commits remain. DB attempt number is not provider attempt number.

Own 40P01 handling in a persistence-layer UoW wrapper/factory used only by LiteratureSearchExecutionService: cover transaction-body, commit and context-exit database failures, ensure rollback/closure, then normalize this SQLSTATE while retaining its cause for sanitized evidence. Reuse inherited 40001 handling. Do not import SQLAlchemy into Domain/Application or normalize arbitrary persistence exceptions. Application owns the bounded per-phase retry loop, never a provider-call retry closure. Changing the global UoW normalization policy for earlier services is **not authorized**: if a shared-policy expansion proves necessary, STOP for explicit approval and require historical regression/non-drift proof before such a change. Prior services' current 40P01 behavior must remain unchanged; tests must not retroactively demand the new PR2-04 mapping from them.

TX B retries reuse the same validated in-memory provider outcome, with the same attempt ID, never re-call the provider. If TX B committed but acknowledgment was lost, an exact persisted outcome is recognized and no append is repeated. A different payload for a sealed attempt fails `IMMUTABLE_RECORD`. TX C retries derive terminal state from durable rows. No transaction retry reuses stale authorization.

**Provider retries:** Application orchestrator only. Persist each outcome before reserving its successor. Default and v1 maximum: three provider attempts **per query**, including initial; configuration may lower to 1 or 2, not raise above 3 without contract review. Maximum 96 reservations per execution. Retry only definite 429, declared transient 5xx with no usable response, or transport/timeout explicitly known NOT_SENT. Never retry auth/validation/permanent/malformed errors, cancellation, or uncertain delivery. Known rejection may be retried despite RESPONSE_RECEIVED; MAY_HAVE_BEEN_SENT always terminates UNKNOWN. Provider adapters must not retry internally.

Honor Retry-After when it fits the remaining bounded operation budget; never retry earlier by clamping it downward. Otherwise end FAILED with `PROVIDER_RETRY_EXHAUSTED`. Without Retry-After use jittered exponential delay in [0, min(8, 2^(attempt_number−1))] seconds, bounded by remaining budget. Inject a deterministic clock/sleeper/random source in tests. Per-call timeout 1–30 seconds; execution dispatch budget 1–600 seconds from started_at, fixed in context. Before each reservation verify remaining budget and authority. If budget ends with a known outcome, stop FAILED; if delivery is unresolved, UNKNOWN. Backoff never holds DB resources.

Retry-After survives process loss in the sealed attempt. The next reservation must not precede `completed_at + retry_after_seconds` by fresh DB time; using DB completion instead of provider time is conservatively later. Enforce this under execution lock for **all** drivers/new command keys, not only by an in-memory sleep. Close the UoW before waiting and reenter the full authorization sequence afterward. If the minimum delay cannot fit a subsequent call in the execution budget, finalize exhaustion without a new reservation. Adapter parsing converts a valid Retry-After date/duration to nonnegative ceiling seconds; very long delays cause exhaustion, not early retry. A new command cannot reset attempt counts, start time or budget.

**Caller retry:** same request key is receipt replay only, never provider retry or redispatch. A new execute request key is an explicit request to drive remaining **known-safe** work; it may reserve the next attempt/query only if no unsealed attempt exists and no stop/terminal condition exists. It cannot resume UNKNOWN/FAILED/CANCELLED or erase a failed attempt. After process loss, an existing RESERVED attempt is recovered, not taken over. A new create key creates a deliberate new execution, including after a previous FAILED/UNKNOWN; external duplicate cost/hits remain possible and visible, not described as exactly-once.

**Recovery:** an explicit currently authorized command, separate from all three retry domains. It performs only the state/CAS bookkeeping in §19. It cannot redispatch, reset provider budgets, or turn receipt replay into execution work.

## 10. Timeout, cancellation and UNKNOWN

Known timeout before dispatch: sealed RETRYABLE_FAILURE/NOT_SENT, eligible for bounded retry. Timeout/disconnect after possible dispatch: sealed UNKNOWN/MAY_HAVE_BEEN_SENT; no further query or provider retry. A valid late response cannot change a sealed UNKNOWN execution/attempt. UNKNOWN is a historical observation, not proof that remote work failed.

Cancellation uses the unique `CANCEL_REQUESTED` event as its durable intent; no extra intent column/table is introduced. **TX C1:** acquire canonical project/command/execution locks, durable reread, fresh DB time and current authorization; admit only PLANNED/RUNNING, append CANCEL_REQUESTED and cancel admission receipt atomically, increment execution row_version once, commit. Status and lifecycle timestamps do not change. An existing intent admits only the explicitly permitted no-op receipt (§11), with no new event/version increment. No terminal CANCELLED/FINISHED event is emitted by C1.

**TX C2:** independently reacquire locks, durable reread, fresh DB time and authorization; apply §16's TX C derivation. For PLANNED with committed intent, verify no attempt/dispatch exists, set CANCELLED, finished_at=fresh DB time and failure_code=CANCELLED, keep started_at null, increment row_version once and append FINISHED atomically. Normal cancel drives this finalizer after C1; after interruption a new authorized recovery command does so. For an otherwise untouched execution the coordinates are CREATED sequence0/version1; C1 CANCEL_REQUESTED sequence1, PLANNED v1→v2; C2 FINISHED sequence2, PLANNED→CANCELLED v2→v3. Admission accepted_row_version remains 2. With intervening RUNNING effects use actual locked version/next sequence, never these illustrative constants.

**Convergence invariant:** PLANNED + durable cancellation intent + no dispatch MUST converge to CANCELLED through C2 or explicit authorized recovery without any provider invocation. PLANNED without intent remains PLANNED on recovery. Exact receipt replay remains read-only, so convergence after a crash requires a currently entitled recovery caller, not background scheduling or stale authority.

At RUNNING, no new reservation may follow committed intent. An already committed reservation may have dispatched: pass a cooperative token where available; cross-process immediate remote cancellation is not promised. A bounded provider timeout remains mandatory. C2 cannot finalize while a RESERVED attempt remains: the normal driver records its observed outcome, or authorized recovery waits until recovery_after and seals UNKNOWN. A provider guarantee of cancellation/not-sent permits CANCELLED; uncertainty takes precedence over cancellation. A valid response is persisted with fresh authority even if intent committed during that call, then CANCELLED wins if intent committed before TX C. If TX C committed first, a new cancellation is INVALID_STATE_TRANSITION. Cancellation before reservation forbids dispatch; after reservation it cannot claim dispatch was prevented. Never discard committed earlier hits.

The invocation deadline is `min(reserved_at + timeout_seconds, started_at + execution_budget_seconds)`, in DB time; no new reservation is allowed with less than one second remaining. The timeout passed to the adapter is further reduced by elapsed time since reservation, never reset to a full timeout on entry. Recovery deadline is `deadline_at + 30 seconds` (bounded processing/persistence grace). Recovery before that instant is denied with `CONCURRENT_MODIFICATION`; at/after it, a currently authorized recovery command seals it UNKNOWN and fences late TX B. This is a DB-write fence, **not proof that a remote request stopped**. The adapter must not deliberately start dispatch after its deadline; scheduling pauses and lost responses can still yield uncertain remote work. No replacement invocation is created for that reservation.

Terminal UNKNOWN reconciliation is not implemented. A future explicit appended reconciliation record requires its own contract; old terminal rows must not be reopened. This is at-most-one local invocation per durable reservation with uncertain delivery, and potentially repeated known-safe attempts/new executions; it is not an exactly-once external-effect guarantee.

## 11. Idempotency

Each public write has the complete receipt key `(deployment_id, actor_id, project_id, command_name, request_id)` as in PR2-03 §7. Command names: `CREATE_LITERATURE_SEARCH_EXECUTION`, `EXECUTE_LITERATURE_SEARCH_EXECUTION`, `CANCEL_LITERATURE_SEARCH_EXECUTION`, `RECOVER_LITERATURE_SEARCH_EXECUTION`. Hash the closed normalized payload with unchanged sha256-cjson-v1:

- create: `{project_id, search_plan_version_id, provider_id, provider_version, queries, max_results, max_provider_attempts, timeout_seconds, execution_budget_seconds}`; queries is ordered `[{query_type:"TEXT",query_text,perspective}]`, all optional perspective keys present as null.
- execute/cancel/recover: `{project_id, execution_id}`. Recovery is the deterministic safe operation in §19, not a caller-selected final status or supplied provider result.

No request ID/principal/server timestamps/response enter the hash. Context stores the same normalized create fields other than the typed project/plan FKs; strategy fixed to `explicit_queries`, version `1`. This is an execution recipe, not a change to the plan's search_strategy; caller remains responsible for selecting queries consistent with the plan. No algorithmic completeness claim is made.

Same **complete receipt key** plus identical normalized payload returns the saved admission DTO; same complete key plus materially different payload/hash returns IDEMPOTENCY_CONFLICT. Changing deployment, actor, project or command changes the key: the same request UUID then has independent receipt semantics, subject to that command's normal authorization/lifecycle/uniqueness checks, not an automatic payload conflict. Different scopes do not guarantee admission. Project equality, actor authentication and **current OWNER/RESEARCHER entitlement** precede write-receipt disclosure. Governance completed-grant exceptions do not apply.

Separately, S08 mandates UNIQUE(project_id,idempotency_key) for execution creation, where idempotency_key is the create request_id. **Receipt identity is not execution uniqueness identity.** A different actor/deployment has a distinct receipt key but reuse of this execution key in the same project fails non-disclosing IDEMPOTENCY_CONFLICT after current project authorization, without returning the other actor's receipt/execution. The same request UUID in a different valid project is independent under both keys. Reuse for another command is independently scoped and does not create another execution.

Admission DTO v1 is exactly `{execution_id, command_name, accepted_at, accepted_row_version}`. It certifies only that this command's described durable admission committed, not execution success. Create receipt commits in TX A-create. Execute receipt commits with first reservation, or a no-new-dispatch admission when another attempt is already active; an exact replay does not drive a loop. Cancel receipt commits with cancellation request. Recover receipt commits with its recovery outcome/decision. No receipt is written for pre-admission validation/authority/CAS failure. Post-admission interruption cannot erase the already legitimate admission receipt; zero-forbidden-effects tests distinguish it from any **new** denied effects. Snapshot/provenance queries show current outcome; admission replay never masquerades as final SUCCEEDED.

A new execute key encountering a terminal execution, a durable stop predicate, or all queries already complete returns INVALID_STATE_TRANSITION with no admission; use recover to finish pending TX C. A new cancel key while the single cancel intent is already durable returns a no-op admission without another cancellation event; terminal cancellation still denies unless it is exact receipt replay. An execute driver that discovers someone else's active reservation returns its admission and does not wait/take over. An existing driver's normal loop may finish TX C, but a new admission never reissues its prior invocation.

Cancellation replay coordinates: before C1 commits, contenders serialize on the complete key; rollback leaves no intent/receipt/version bump, and successful admission happens once. After C1 commits but before C2, exact replay returns the original admission only; it does not finalize or invoke a provider and does not claim CANCELLED. A new recover key can finish C2. After CANCELLED, exact cancel replay still returns that same admission after current entitlement. A new cancel key on a nonterminal existing intent is the no-op above; a new cancel/execute key on terminal denies with no receipt. A new **recover** key on terminal may append a no-op admission receipt referencing the existing execution/version, but changes no execution, attempt, query, result or event. Exact replay never inserts a second receipt. These are explicit command policies, not a general exemption from terminal immutability.

Orchestration normally returns the admission DTO after bounded drive. Provider failure is a persisted operational outcome, not loss of command admission. If authority is lost before response disclosure, return FORBIDDEN and disclose no DTO; if DB work exhausts retry after admission, return CONCURRENT_MODIFICATION without claiming rollback of prior phases. A subsequent authorized replay retrieves the admission; a query/recovery determines durable state. No failure is hidden as a success claim.

## 12. Authorization

Every public mutation and internal phase requires live verified HUMAN/AGENT principal, active project and membership, effective OWNER or RESEARCHER, live credential, and project scope. Reads allow established OWNER/RESEARCHER/REVIEWER/APPROVER/VIEWER with active membership/current credentials. Human and Agent use identical Application policy. Foreign-scope IDs return non-disclosing NOT_FOUND; unauthorized same-project access returns FORBIDDEN.

TX A-create and first reservation validate exact FROZEN plan, hash and closure. Every later phase checks immutable plan binding/hash; SUPERSEDED-after-start is historical, not a reason to change plan. After each required wait use TEMP-AUTH-01. Authorization at create is not permission for all future phases.

The committed reservation is the linearization point for permission to start that one bounded external invocation. Authority changing immediately afterward cannot retroactively unsend it and does not require a DB transaction spanning I/O. Every subsequent TX B, next reservation, TX C and response disclosure rechecks current authority. Loss during the call therefore denies the old caller's result persistence/finalization; no query/results/new receipt/event from that denied phase commits. Existing admitted execution/reservation is retained. It may remain RUNNING until a currently entitled actor invokes recovery. Recovery does not impersonate the old actor, revive stale credentials or promote lost in-memory results.

Already committed query/results are retrieval history, not forbidden new writes when authority later changes. An authorized recovery actor may finish TX C from those facts or mark an expired unresolved reservation UNKNOWN. Read entitlement is independent of write entitlement; a VIEWER may query but not replay a write receipt or recover. No new service principal, hidden operator bypass or autonomous sweeper is introduced.

## 13. Persistence/schema contract

### 13.1 Shared rules

All six tables have `id UUID PK`, `created_at TIMESTAMPTZ NOT NULL` (DB UTC), `created_by UUID NOT NULL FK actors(id) RESTRICT`. All columns below are NOT NULL unless marked `?`. All FKs RESTRICT; no CASCADE. Text identifiers are NFC/nonblank and bounded as above. UUID values are not provider IDs. Every FK has a B-tree leading index (including both actor attribution columns); a leading unique index may satisfy it. Canonical IDs are concrete FKs, not JSON lists. Mutable tables have `row_version INT >0 DEFAULT 1`; immutable ones do not.

Use varchar CHECK literals, not new global PostgreSQL enum types. All immutable rows and sealed attempts reject UPDATE/DELETE at DB level. Execution material is immutable from creation except executed_by's single PLANNED→RUNNING assignment. Operational status/times/failure and row_version are controlled by state guards. Triggers serialize child mutations on the execution row; outcome sealing/child append/terminal validation share that lock. Deferred guards validate complete TX B sets at commit. Direct SQL cannot mutate terminal execution facts, append provider attempts/query/result provenance to a terminal execution, append to sealed outcomes, or append execution events after terminalization. FINISHED is inserted atomically with the terminal transition, not a later event-only write. Row-version guard requires old+1 for each actual mutable-row update; Application coalesces one execution update per phase transaction.

Terminal immutability protects execution state and provenance, not an independently keyed authorized operational admission. The §11 terminal RECOVER no-op may insert an immutable receipt with the existing execution FK and admission projection, without any execution version/event/provenance change or external call. Receipt guards must permit this explicit exception; attempt/query/result/event guards must not. Existing receipts remain immutable, exact replay inserts nothing, and other new terminal commands remain governed by §11's denials. No receipt may reference an absent execution.

### 13.2 `literature_search_executions` (S08 unchanged semantic fields)

| Columns | Type / constraint |
|---|---|
| project_id; search_plan_version_id | UUID FKs projects / literature_search_plan_versions; same-project and initially FROZEN guard through plan parent. |
| strategy_id; strategy_version | TEXT; v1 `explicit_queries` / `1`; immutable. |
| status | VARCHAR(16), exact six-state CHECK. |
| requested_by; executed_by | UUID FKs actors; attribution rules §5. |
| started_at?; finished_at? | TIMESTAMPTZ; PLANNED both null; RUNNING started nonnull/finished null; terminals finished nonnull; start null only for pre-start CANCELLED; finish ≥ start when start exists. |
| execution_context | JSONB, required in this PR despite upstream allowance of null; exact closed schema below; no credentials/raw payload. |
| idempotency_key | UUID; UNIQUE(project_id,idempotency_key). |
| failure_code? | TEXT; §16 reason CHECK; SUCCEEDED/PLANNED/RUNNING null; FAILED/CANCELLED/UNKNOWN require matching reason. |
| row_version | positive INT; CAS and terminal immutability. |

Indexes: `(project_id,status,created_at,id)`, `(search_plan_version_id)`, actor FKs; unique `(project_id,id)` for scoped dependent FKs where needed.

Closed `execution_context` schema v1: `{schema_version:1,provider_id:string,provider_version:string,queries:[{query_type:"TEXT",query_text:string,perspective:string|null}],max_results:int,max_provider_attempts:int,timeout_seconds:int,execution_budget_seconds:int}`. All bounds §8–9; no additional keys. It contains no canonical object references. This is the named field explicitly permitted in S08's table, not a generic metadata escape hatch. Context is immutable planned input; observed queries are separately attributable actual invocation records, never a second editable source for planned intent.

### 13.3 `search_query_records` (S08/S09)

`literature_search_execution_id UUID FK`, `query_text TEXT`, `perspective TEXT?`, `provider_id TEXT`, `provider_version TEXT?`, `ordinal INT >=0`, `executed_at TIMESTAMPTZ`, `query_hash CHAR(64)`, `hash_scheme VARCHAR(32)='sha256-cjson-v1'`. Upstream nullable provider_version is retained, but v1 port always supplies its pinned version. UNIQUE(execution_id,ordinal), UNIQUE(execution_id,query_hash), UNIQUE(execution_id,id) using the full stored execution-column name. Lowercase-hex digest guard. Append-only; contiguous ordinals at transaction end. Each query must be linked to exactly one sealed attempt in the same execution by deferred guard. No query without an observed invocation.

Hash exactly S09:

```json
{"type":"SearchQueryRecord","material_version":1,"literature_search_execution_id":"<uuid>","provider_id":"<string>","provider_version":"<string|null>","query_text":"<normalized string>","ordinal":0}
```

`ordinal:0` illustrates an integer slot. Normalize query NFC, collapse Unicode whitespace runs to one ASCII space, trim, reject empty. No change to canonical-json-v1; perspective/response/times excluded.

### 13.4 `search_result_records` (S08 plus shared own-hash rule)

`search_query_record_id UUID FK`, `rank INT >=0`, `external_identifier TEXT?`, `title TEXT`, `url TEXT?`, `snippet TEXT?`, `provider_score NUMERIC?` finite only, `retrieved_at TIMESTAMPTZ`, shared `content_hash CHAR(64)` and `hash_scheme VARCHAR(32)='sha256-cjson-v1'`. UNIQUE(query_id,rank); contiguous rank, query FK index covered. Results may be inserted only atomically with a successful attempt seal. All results of that response have its retrieved_at; later appends/UPDATE/DELETE forbidden. Zero results is valid. No unique external_identifier/title/url constraint.

New own-hash definition D11 (requires ADR-0011 approval): hash unchanged canonical-json-v1 UTF-8 of exactly

```json
{"type":"SearchResultRecord","material_version":1,"query_hash":"<digest>","rank":0,"external_identifier":null,"title":"<NFC string>","url":null,"snippet":null,"provider_score":null}
```

Non-null optional strings replace null; non-null score is a canonical decimal string per S09, never float/NaN/Infinity. Query binding is the immutable query_hash, verified against the FK target. IDs/actors/timestamps are excluded; no provider blob. Retrieval time remains immutable provenance even though not hash material. No existing golden vector changes.

### 13.5 `literature_search_provider_attempts` (proposed supporting admission)

Reservation columns, immutable after insert: `execution_id UUID FK`, `query_index INT >=0`, `attempt_number INT >=1` (per query), `provider_request_key UUID`, `reserved_at TIMESTAMPTZ`, `deadline_at TIMESTAMPTZ`, `recovery_after TIMESTAMPTZ`. Provider identity/query/options come from the execution's immutable context and query_index. No duplicated editable query material. `provider_request_key=id`; deadline follows §10's call/execution minimum; recovery_after=deadline+30 seconds. UNIQUE(execution_id,query_index,attempt_number), UNIQUE(execution_id,provider_request_key), UNIQUE(execution_id,id). Partial UNIQUE(execution_id) WHERE status='RESERVED'. Attempt numbers contiguous from 1; query_index valid and advances only after successful prior input query. Max attempts/context budget checked under execution lock.

Outcome columns initially null unless specified: `status VARCHAR(24)` initially RESERVED; `query_record_id UUID? UNIQUE FK search_query_records`; `invoked_at TIMESTAMPTZ?`; `returned_at TIMESTAMPTZ?`; `completed_at TIMESTAMPTZ?`; `delivery_certainty VARCHAR(24)?`; `provider_request_id TEXT?`; `failure_code TEXT?`; `retry_after_seconds INT?` (0–2147483647); `warning_codes JSONB?` (closed array of unique §8 literals, not arbitrary metadata); `result_count INT? >=0`; `row_version INT`.

RESERVED requires all other outcome columns null. Seal sets status and complete outcome tuple once, row_version 1→2; completed_at is fresh DB completion time. Deferred guard requires query FK same execution, query text/provider/perspective equal context input, executed_at=invoked_at. Query is present iff invoked_at is known; recovered unobserved invocation has both null. Success requires invoked_at/returned_at/query, certainty RESPONSE_RECEIVED, null failure, exact result_count matching rows. All failures have result_count=0 and a §16 reason; only success may own result rows. Failure returned_at may be null (timeout). NOT_SENT must never carry successful results; UNKNOWN requires MAY_HAVE_BEEN_SENT. Sealed rows require warning_codes as a closed array (empty if none), delivery_certainty and completed_at; provider_request_id/Retry-After remain nullable. Orchestrator UTC invocation/return times and provider retrieved_at are provenance observations, never authorization clocks; validate invoked_at ≤ returned_at when both known and reserved_at ≤ completed_at. Do not fabricate remote timestamps from DB time.

The attempt's sealed outcome is the sole owner of delivery/error facts. A transaction cannot seal two different outcomes; exact internal reapplication compares all caller/adapter-derived outcome/query/result facts and succeeds without mutation only if identical. It reuses stored generated IDs, ordinal, completed_at and hashes, not newly generated comparison values. A late different outcome is IMMUTABLE_RECORD. No raw provider error payload is stored. Provenance reads recompute query/result hashes and reject a mismatch with PROVENANCE_CLOSURE_VIOLATION; this is not a new global hash-error policy.

### 13.6 `literature_search_execution_events` (proposed dependent event pattern)

Columns: `execution_id UUID FK`, `sequence INT >=0`, `kind VARCHAR(24)`, `attempt_id UUID?`, `prior_status VARCHAR(16)?`, `new_status VARCHAR(16)`, `prior_row_version INT?`, `new_row_version INT >0`, `occurred_at TIMESTAMPTZ`. Kind CHECK: CREATED, ATTEMPT_RESERVED, OUTCOME_RECORDED, CANCEL_REQUESTED, FINISHED. `created_by` is effect actor; no second actor field. UNIQUE(execution_id,sequence); FK `(execution_id,attempt_id)` to attempts `(execution_id,id)` when nonnull. Index attempt_id. CREATED has null prior coordinates and PLANNED/version1; attempt kinds require attempt_id, others null. State-changing and same-state events follow §6; cancellation emits a single request event per execution (partial unique index). Event sequence contiguous from 0. FINISHED unique per execution. Each mutable execution change and matching event commit together with equal row-version coordinates; no event-only fabricated state. Append-only, no own content hash (explicit operational audit exception, following accepted membership/role event pattern, not scientific material).

CANCEL_REQUESTED is C1's nonterminal intent admission; FINISHED with new_status=CANCELLED is C2's actual finalization. They cannot share one mutation coordinate or be emitted out of order. Both uniqueness guards apply under recovery races; a no-op receipt emits neither event. No event may claim terminal cancellation while execution remains PLANNED/RUNNING.

### 13.7 `literature_search_execution_command_receipts` (proposed dedicated receipt pattern)

Columns: `deployment_id TEXT`, `project_id UUID FK`, `actor_id UUID FK actors`, `command_name VARCHAR(48)` exact §11 set, `request_id UUID`, `request_hash CHAR(64)`, `hash_scheme VARCHAR(32)='sha256-cjson-v1'`, `result_execution_id UUID`, `result_dto_version SMALLINT=1`, `result_dto JSONB`, `completed_at TIMESTAMPTZ`. Unique full scope key §11; concrete composite FK `(project_id,result_execution_id)`→executions `(project_id,id)`; all result/actor FKs indexed; lower-hex hash. created_by=actor_id. DTO JSON is exactly the immutable admission projection §11, with execution ID equal typed FK and command_name equal column; not canonical provenance storage. Complete INSERT only, UPDATE/DELETE forbidden. No own content hash beyond request_hash, as in earlier receipt tables. Do not alter existing receipts.

## 14. Migration contract

Proposed single revision `0024_literature_search_execution`, parent exactly `0023a_search_plan_review_guards`; filename `migrations/versions/0024_literature_search_execution.py`. It creates only §13 tables/constraints/indexes/guards and new supporting functions. One Alembic head after upgrade. No edits through 0023a, no Phase 1 columns/hash/lifecycle changes, no new global retry/lock function semantics.

Test fresh→head; frozen Phase 1 `0018`→head; populated accepted 0023a→head preserving earlier data and durable acceptance. Downgrade to 0023a only when **all six** new tables are empty; otherwise refuse before destructive DDL. Empty downgrade/reupgrade must work. This document creates no migration. ADR-0011 and pack approval are prerequisites for its eventual authoring.

## 15. Provenance and append semantics

Typed chain: exact PlanVersion ← Execution ← Attempt → QueryRecord ← ResultRecord. Attempt.query_index references the ordered planned value inside immutable context, not a canonical object ID list. Query→execution and attempt→execution/query consistency are DB guarded. For an unobserved invocation the attempt, reservation time/deadline and planned input survive, while actual query/time remain explicitly unknown.

Authorized provenance query returns plan ID/version/hash, execution identity/attribution/status, input recipe, ordered attempts with certainty/times/errors, associated query hashes/ordinals and ordered result rows/hashes; cancellation/terminal history and receipt admissions are distinguishable. Attempts sort `(query_index,attempt_number)`, queries by ordinal, hits by rank, events by sequence. No timestamp tie determines order. Counts are derived. Repeated provider hits/retried identical queries remain visible. No canonical dedup/source resolution occurs. Terminal result count is total durable hits, which may be nonzero for FAILED/CANCELLED/UNKNOWN after an earlier query succeeded; this is explicitly partial retrieval, not SUCCEEDED.

## 16. Canonical error mapping

Pre-admission Application errors use existing `VALIDATION_ERROR`, `AUTHENTICATION_REQUIRED`, `FORBIDDEN`, `NOT_FOUND`, `INVALID_STATE_TRANSITION`, `IMMUTABLE_RECORD`, `CONCURRENT_MODIFICATION`, `IDEMPOTENCY_CONFLICT`, `PROVENANCE_CLOSURE_VIOLATION`. Reuse existing hash-verification error behavior; never invent success on a mismatch. Plan missing/foreign scope: NOT_FOUND; non-FROZEN at initial start/create: **SEARCH_PLAN_NOT_FROZEN**, specified upstream S05 §31 but not yet in ErrorCode at baseline. Unsupported/missing adapter: **ADAPTER_UNAVAILABLE**; registered version mismatch: **ADAPTER_VERSION_MISMATCH**, also upstream additions not yet implemented. No change to prior errors.

Provider outcomes are typed operational reasons (new D12 enum values, **not automatic ErrorCode additions**), stored in attempt.failure_code and terminal execution.failure_code as specified:

| Condition | Attempt / delivery | Execution when stopped | Reason |
|---|---|---|---|
| Known pre-dispatch timeout | RETRYABLE_FAILURE / NOT_SENT | FAILED if no retry remains | PROVIDER_TIMEOUT; terminal PROVIDER_RETRY_EXHAUSTED on exhaustion |
| Known 429/transient 5xx/transport not-sent | RETRYABLE_FAILURE / known certainty | FAILED on exhaustion | PROVIDER_RATE_LIMIT / PROVIDER_TRANSIENT; terminal PROVIDER_RETRY_EXHAUSTED |
| Provider auth/validation/permanent error | PERMANENT_FAILURE / known certainty | FAILED | PROVIDER_PERMANENT |
| Malformed/oversized/identity-mismatched response | PERMANENT_FAILURE / RESPONSE_RECEIVED | FAILED | PROVIDER_MALFORMED |
| Timeout/drop/cancel with uncertain remote outcome | UNKNOWN / MAY_HAVE_BEEN_SENT | UNKNOWN | PROVIDER_OUTCOME_UNKNOWN |
| Confirmed cancellation/not dispatched | CANCELLED / NOT_SENT or RESPONSE_RECEIVED | CANCELLED | CANCELLED |
| Expired reservation without durable outcome | UNKNOWN / MAY_HAVE_BEEN_SENT | UNKNOWN | RECOVERY_OUTCOME_UNKNOWN |
| Known incomplete execution stopped by recovery | no invented attempt | FAILED | RECOVERY_INTERRUPTED |
| Execution budget ends with known outcomes | no new attempt | FAILED | PROVIDER_RETRY_EXHAUSTED |

Exhaustion retains each attempt's original reason, not overwrites it. A cancellation between attempts has no fabricated cancelled attempt; execution reason CANCELLED suffices. UNKNOWN always takes precedence over cancellation/exhaustion when uncertainty exists. Sealed success plus later cancellation retains successful attempt/result facts.

TX C's deterministic derivation, only when no RESERVED attempt remains: (1) any UNKNOWN attempt → UNKNOWN using its reason; (2) durable cancel request or confirmed cancelled attempt → CANCELLED; (3) permanent/malformed attempt → FAILED using its reason; (4) every input query has success → SUCCEEDED; (5) safe retry/execution budget exhausted → FAILED/PROVIDER_RETRY_EXHAUSTED; (6) explicit recovery of otherwise incomplete known work → FAILED/RECOVERY_INTERRUPTED. Otherwise ordinary drive continues and TX C is not yet permitted. Earlier successful hits never change this state precedence. There is at most one stopping failure/unknown because new reservations after it are forbidden.

PLANNED is a separate entry case: intent present and no attempts permits only C2→CANCELLED; no intent permits no finalization and recovery leaves it PLANNED. Do not apply RUNNING's incomplete-work FAILED rule to PLANNED. Cancellation never outranks UNKNOWN or a terminal state already committed. Intent admitted before finalization wins over a known response; that response's committed provenance survives.

Provider-failure state is returned by the authorized execution query, not leaked as raw driver/provider exception. Successful admission is not provider success. DB retry exhaustion uses CONCURRENT_MODIFICATION and preserves earlier phase commits. Unexpected DB failure is a redacted internal error, never a retryable provider outcome. `EXTERNAL_RETRIEVAL_FAILED` exists in S05's vocabulary but is not needed as an extra exception for a durably recorded failed execution; do not add unused error codes.

## 17. Application and transport surface

`LiteratureSearchExecutionService` is the Application orchestrator, depending on UoW factory, current credential verifier, injected SearchCapability registry and bounded clock/cancellation/backoff utilities. Domain owns value types/state validation; persistence owns SQL/locks; adapters own provider protocol translation. No generic workflow framework.

Typed public command dataclasses follow existing naming: `CreateLiteratureSearchExecution`, `ExecuteLiteratureSearchExecution`, `CancelLiteratureSearchExecution`, `RecoverLiteratureSearchExecution`. Each includes principal, project_id, request_id; create has exactly §11 fields; other commands have execution_id. Service methods `create`, `execute`, `cancel`, `recover`; functional transport command names match §11 lowercase equivalents. Internal `reserve_attempt`, `record_provider_outcome`, `finish_execution` are not public API methods accepting arbitrary client success claims. Only the orchestrator may pass a validated provider outcome through the Application boundary. Public callers cannot submit rows/terminal status/provider-result JSON.

S05 §12 names `start_literature_search`, `record_search_query`, `record_search_result`, `finish_literature_search`. Preserve those Application use-case names as phase operations: start is the reservation/admission operation called by execute; record_query/result are internal contributions to the **same TX B**, not independently committable public writes; finish is TX C. The descriptive internal helper names above are not replacement public semantics. No such accepted callable exists at baseline; no prior API is renamed. `resolve_search_result` from that Phase-wide list is deferred, not implemented as an implicit success side effect here.

Queries: `get_literature_search_execution(project_id,execution_id)`, `list_literature_search_executions(project_id,after?,limit)`, `get_literature_search_execution_provenance(project_id,execution_id)`, each with verified principal. List limit 1–100, default 50, stable `(created_at,id)` cursor, no cross-project pagination. Projection includes row_version and partial status; never ORM entities.

HTTP paths (A2-corrected S05 §32): POST `/literature/search-executions` (201); POST `/{id}:execute`, `/{id}:cancel`, `/{id}:recover` beneath that path (202 admission); GET collection/item and `/{id}/provenance` (200). UUID `Idempotency-Key` for writes, supplied project scope, established verified-principal adapter. No `/search-runs` alias because none has been implemented/accepted. CLI group `literature-search-execution` with create/execute/cancel/recover/get/list/provenance and `--request-id`, `--project-id`; same typed DTO and canonical errors. JSON create body is §11 create payload; other write bodies exactly `{project_id}` with execution_id from route; no caller actor override. CLI multi-query input is validated JSON matching `queries`, not shell-evaluated strings.

HTTP mappings: authentication 401; forbidden 403; non-disclosing not-found 404; state/immutable/idempotency/concurrency/plan-not-frozen/adapter-version 409; validation 422; unavailable adapter 503; unexpected internal error redacted 500. Recorded provider failure/UNKNOWN remains a 200 execution read with explicit state/reason, not transport success of retrieval. HTTP disconnect requests cooperative cancellation but is not a new authenticated durable cancellation command by itself.

## 18. Concurrency requirements

Canonical order: project advisory lock → projects row → command-key lock (public commands) → plan identity/version if needed → execution row → attempt/query rows in deterministic order → membership/role/binding locks required by accepted authority helper → durable reread → fresh `clock_timestamp()` → authorization → effect. All paths, including controllers/recovery/cancellation, use the same project lock function. No DB lock is retained through I/O. Relation guards must not acquire locks in inverse order to Application paths.

Serialize each execution's allocation/terminal decisions on execution row and CAS. Duplicate execute callers cannot obtain dispatch ownership of one reservation. A committed RESERVED attempt blocks any successor even if another process has a new request key. Outcome vs recovery/cancellation/finish races have one durable winner, observed PostgreSQL waits and explicit loser result. Duplicate create race preserves one project/key execution and deterministic replay/conflict. SQLSTATE23505 is normalized by named constraint, not all-integrity-errors-as-replay. Serialization retries may use fresh transactions/backends and must reauthorize. No one-attempt requirement is imposed.

Recovery A vs recovery B, including interrupted PLANNED cancellation: both follow canonical locks and state/CAS checks. Only one transaction may seal a given RESERVED attempt or make a terminal transition; one FINISHED, no duplicate queries/results and zero recovery provider calls. A contender seeing a stale version or serialization conflict follows §9's bounded retry, then rereads the durable outcome with fresh authority; it must not replay a stale transition. When terminal is already visible, a distinct recovery key may commit only its no-op receipt; the same complete key replays one saved receipt. Retry exhaustion still returns canonical CONCURRENT_MODIFICATION; a later authorized retry observes durable state. TX B and TX C remain separate, so another recovery may legitimately perform TX C after the first sealed TX B. No requirement binds both phase wins to one worker.

This is **transactional state/CAS fencing**: outcome persistence is permitted only while the locked execution/attempt state, attempt identity and expected row versions authorize that write. Sealing or terminalization invalidates a stale writer; exact already-sealed replay is read-only, different late material rejects. It is not a distributed fencing-token, lease, ownership-generation or takeover service.

## 19. Crash/recovery matrix

`recover` never invokes a provider. With canonical locks, durable reread and fresh authority: terminal→no-op admission (only a new keyed receipt, no execution/provenance mutation); PLANNED without cancellation intent→leave PLANNED; PLANNED with committed CANCEL_REQUESTED and no attempts→C2 finalizes CANCELLED, with recovery receipt in that transaction. PLANNED with attempts is an invariant violation, not permission to dispatch or fabricate history. For RUNNING: active reservation before recovery_after→CONCURRENT_MODIFICATION/no receipt; expired reservation→TX B-recovery seals UNKNOWN then TX C; all outcomes sealed and completion predicates available→TX C; otherwise known incomplete run with no active attempt→TX C FAILED/RECOVERY_INTERRUPTED. Recovery receipt commits with its first durable recovery phase (or no-op admission), so exact replay is read-only; a new recovery request may finish an interrupted TX C. Stop predicates cannot be bypassed by execute racing recovery. Concurrency follows §18 for every branch.

| Crash point | Durable facts | Replay/recovery and visible result |
|---|---|---|
| Before TX A-create commit | Nothing, or uncertain commit acknowledgment | Same create key reads receipt or creates once; never assumes absence. No provider call. |
| After TX A-create, before reservation, no cancel intent | PLANNED + create receipt; no attempt | Same create returns admission; explicit execute may reserve. Recovery leaves PLANNED; cancel may close. No provider work from recovery. |
| After reservation commit, before provider entry | RUNNING + RESERVED; no proof whether process dispatched | Exact execute replay never redispatches. Wait until recovery_after, then UNKNOWN; conservative false uncertainty is acceptable. |
| Provider call in progress | Same reservation; possible remote work | No takeover/retry. Deadline/cooperative cancellation; after recovery deadline UNKNOWN fences late writes. |
| Provider returns, before TX B | Only reservation durable; response possibly lost | Surviving owner may persist same response with fresh authority before fencing. Process loss→UNKNOWN, never synthesize success. |
| During TX B / lost acknowledgment | Either all outcome/query/results or none | Fresh read under lock; exact sealed tuple means no-op; otherwise surviving owner retries persistence only. No response available→recovery UNKNOWN. |
| After TX B, before TX C | Complete immutable outcomes; execution still RUNNING | Authorized recover derives terminal state without provider call; or explicit new execute may continue only known-safe remaining work before recovery stops it. |
| During TX C (including C2) / lost acknowledgment | RUNNING, or PLANNED with cancellation intent, or one terminal/event | Retry transaction/read terminal under fresh authority; never repeat I/O; terminal row/event exactly once. |
| After terminal commit, before client receives response | Terminal facts, immutable admissions | Exact replay returns original admission after current entitlement; GET returns terminal facts. No external call. |
| After C1 intent/receipt commit, before C2 cancellation finalization | PLANNED, CANCEL_REQUESTED and cancel receipt durable; version bumped once; no attempts, no FINISHED | Exact cancel replay returns admission only. New authorized recovery rereads intent and finalizes CANCELLED via C2, bump/event once; no provider call is possible. Racing recoveries yield one transition/FINISHED and separately permitted no-op receipts, never duplicate protected effects. |

Crashes during backoff are the known-sealed-outcome case. No automatic background repair, lease expiry dispatcher or magical exactly-once guarantee. Missing current authority may leave work unresolved until an entitled caller recovers it; safety does not imply unattended liveness.

## 20. Acceptance matrix

The [separate matrix](PR2-04_Acceptance_Matrix_v1.0.md) has stable requirement IDs, pack/source links, expected evidence and test categories. All rows start NOT_RUN; it is not runtime evidence. The implementation must supply exact collected pytest node IDs/parameter cases for each row, then generate `verification_matrix_result.json`; a missing/skipped/failed parameter cannot yield PASS. Requirement count is derived from the rows, not copied from PR2-03.

## 21. Test plan

Proposed files/categories (not files created by this design):

- `tests/unit/test_literature_search_execution.py`: complete execution/attempt transition matrices, limits, normalization, DTO union, result/query golden hashes.
- `tests/integration/phase2/test_pr2_04_execution_application.py`: deterministic success, multiple queries, provider failure/retry/cancel/UNKNOWN, immutable admission versus live projection.
- `tests/integration/phase2/test_pr2_04_execution_persistence.py`: every §13 constraint/trigger, direct SQL invalid paths, FKs/index coverage, append/seal guards, result duplicate order, provenance retrieval/hash verification.
- `tests/integration/phase2/test_pr2_04_transaction_boundaries.py`: fake provider barrier; separate PostgreSQL observer verifies no service transaction/locks while inside provider/backoff; TX A/B/C commit trace, DB fault injection and outcome replay.
- `tests/integration/phase2/test_pr2_04_execution_recovery.py`: every §19 boundary, lost acknowledgment, late writer fence, known/uncertain timeout, interruption during retries, C1-committed/C2-interrupted cancellation and PLANNED without intent.
- `tests/integration/phase2/test_pr2_04_execution_concurrency.py`: both commit orderings for duplicate create, competing execute, cancel vs reservation/finish, outcome vs recovery, recovery vs recovery (expired RESERVED and interrupted PLANNED cancellation); observe wait/blocker/PID/SQLSTATE and durable counts. Prove PR2-04 40001/40P01 handling, retry exhaustion and unchanged historical normalization behavior.
- `tests/integration/phase2/test_pr2_04_effective_authority.py`: Human/Agent roles, non-disclosure/replay, post-wait membership and clock-only credential expiry, loss during provider call, recovery by another writer; count every DB attempt, no stale authorization reuse.
- `tests/integration/phase2/test_pr2_04_execution_idempotency.py`: every public command exact replay/conflict/scope/rollback and in-progress/failed/unknown replay.
- `tests/integration/phase2/test_pr2_04_execution_http.py` and CLI parity tests: auth, UUID/body/limit validation, command DTOs and canonical mappings; no public outcome-injection endpoint.
- `tests/integration/test_pr2_04_migration.py`: upgrade paths, unique head, empty/populated downgrade, prior data preservation.
- `tests/architecture/test_pr2_04_boundaries.py`: no provider transaction handles, direct domain persistence, later-PR objects, live activation, secrets/raw JSON or historical changes.

Provider fake has explicitly controlled entry/return/cancel/failure barriers, call log with attempt IDs, injected deterministic time/backoff, bounded waits and no hidden retry. PostgreSQL tests use real 18.x, never SQLite. Faults are test-owned; do not alter production retry counts to obtain a preferred trace. Run at least five independent parameter cases for authority contention and each ownership/recovery race; every collected case must pass. Repeated focused race runs detect flakiness; retries in Application are legitimate and fully reported, not pytest reruns hiding failures.

## 22. Host verification, evidence and security

Future exact command: `bash scripts/researchbase_host_review.sh --pr2-04-verification`. Add a mode, preserve existing modes byte-semantics; no tooling change is made by this design. Host subject is an immutable implementation candidate commit, with clean tracked worktree. Evidence directory: `artifacts/pr_evidence/PR2-04/host-review-runs/<UTC>-<pid>/`.

Required gates: environment/PostgreSQL18/version; accepted baseline lineage; Phase1 non-drift; durable PR2-02 and accepted PR2-00–03 regressions; migrations 0023/0023a preserved and 0024 upgrade/downgrade/unique-head; focused execution/domain/persistence; provider success/failure/UNKNOWN/cancel; transaction boundaries; crash recovery; idempotency; concurrency; effective authority/temporal trace; provenance/hash/ordinal; HTTP/CLI; schema/FK indexes; requirement matrix; full suite; Ruff; Pyright; raw formatter and inherited-baseline delta; git diff check. Existing formatter debt is not a new failure if changed files are formatted and new failure set is empty. Do not fix unrelated debt.

Machine-readable manifest: schema_version, run_id, UTC start/end, execution_head, accepted_baseline, design artifact digests, tracked_worktree_clean, PostgreSQL full version, migration before/after/head list, exact invocations/exit codes/artifact digests and check statuses. Preserve pytest XML plus JSON traces. No console PASS substitutes for requirement rows.

Per scenario trace: execution/plan/attempt IDs; provider query index/attempt number/key and provider ID/version; state/row-version/events; DB attempt number/backend PID/transaction identity/SQLSTATE; project blocker PID and observed wait; trusted post-lock authorization time/roles/decision; reservation/commit/provider entry/return/TX B/TX C ordering; proof DB connection/transaction closed during provider and backoff; delivery certainty/deadline/cancellation/UNKNOWN reason; counts of provider invocations, attempts, queries, results, receipts, forbidden new effects; query/result hashes and final state. Use event sequence/barriers for causal ordering, not host timestamp comparisons alone.

Matrix result rows: requirement_id, contract clause, exact expected/collected node IDs including parameters, per-case result, linked trace paths, candidate_head, status in PASS/FAIL/BLOCKED/NOT_RUN. Summary Required/PASS/FAIL/BLOCKED/NOT_RUN is calculated from rows. Full suite retains exact collected/passed/failed/errors/skipped/warnings, candidate SHA and invocation. No skipped requirement, xfail masking, absent artifact or earlier-head substitution is PASS. Environment failure is BLOCKED, never a fabricated partial green run.

Credentials come only from deployment injection into a privately configured adapter, never domain/context/attempt/receipt DTOs. A non-secret provider registration identifier may select injected credentials; no secret values, credential URLs, headers, tokens, certificate keys, or provider error text enter rows/logs/evidence/artifacts. Redact before logging, not afterward. Use synthetic sensitive canaries to test no leakage in errors, traces, XML/JSON, receipt projections and provider metadata. Do not log full request bodies, full text or copyrighted payloads. Egress is allowlisted and disabled for acceptance. Retrieved URLs/text are data; no implicit fetch/execution. Live access/license/pin review remains PR2-06's gate.

## 23. Recommended implementation ordering (not authorization)

1. Independent review/approval of this pack, matrix and ADR; record exact approved design commit. Stop if supporting-schema admission is rejected.
2. Domain/DTO/normalization/state/hash tests first; demonstrate failures; implement narrow domain types. No DB/network imports. Review complete transition/union cases.
3. Typed ports/UoW capability and deterministic fake contract tests; implement minimal SearchCapability dependency and closed DTOs only, not real providers.
4. Migration/model/constraint tests against 0023a first; implement 0024 and persistence adapter with explicit lock/seal/receipt ports. Prove upgrade/downgrade and direct-SQL failures.
5. Application TX A/admission/idempotency/authorization tests first; implement create and reserve, fresh temporal checks and deterministic lock order.
6. External-boundary/success tests first; implement orchestration, atomic TX B and independently retried TX C. Prove no connection held across I/O.
7. Failure/retry/cancellation/UNKNOWN/crash tests first; implement bounded loop, safe recovery and late-write fencing. No general scheduler.
8. Concurrency/authority tests, both race orders and every retry attempt; implement only in-scope corrections. Prove no stale grant and no duplicate invocation from DB retry.
9. Provenance/query/HTTP/CLI tests first; implement thin adapters and scope-safe projections. No ingestion/evidence endpoints.
10. Bind acceptance rows to exact test nodes; implement PR2-04 host mode/evidence validation without weakening previous gates. Run focused ladder, static/changed-file formatting, then create implementation candidate commit.
11. Run unchanged approved host invocation against committed candidate; inspect matrix and full suite; prepare closure-candidate report and STOP for an independent reviewer. Failed candidates remain auditable; remediation is a child commit, not rewritten history.

Expected future file responsibilities: `domain/literature_search_execution.py` values/state; `application/literature_search_execution.py` commands/orchestration; `application/ports.py` narrow UoW capability; `persistence/literature_search_execution_repository.py` SQL; `persistence/literature_search_execution_uow.py` scoped wrapper/factory for §9's 40P01 mapping; existing persistence models/migration registration; provider port/fake in adapter-compatible modules; existing API/CLI registration plus dedicated execution adapters; tests above; host script/matrix evidence binding. Do not normalize all repositories, expand global UoW error semantics or refactor prior services. Exact module integration follows existing layout, with no extra architectural component.

## 24. STOP conditions and adversarial review

Hard stops: rejection/unapproved ADR admission; conflict with an incorporated higher contract; need to alter accepted Phase1/PR2-00–03 semantics; new unplanned migration/aggregate/queue; live provider dependency; missing PostgreSQL runtime proof; unresolved crash/authority/receipt contradiction; test evidence inconsistent with design; requirement skip or hidden retry; implementation expanding into PR2-05/06. No code is authorized by this document.

Adversarial self-review outcomes (design analysis, not executed tests):

| Attack | Resolution incorporated |
|---|---|
| Crash after reservation but before actual send | Conservative UNKNOWN, no redispatch; reservation is not a delivery claim. |
| Lost TX B acknowledgment repeats provider | Per-phase DB retry and exact sealed-outcome comparison; never orchestration retry. |
| Two callers/restarts claim same invocation | Only new acknowledged reservation owner may call; partial unique active-attempt guard; no takeover. |
| Expired reservation recovery deadline causes replacement while old worker wakes | No replacement at all; late persistence fenced by locked state/CAS; remote uncertainty preserved. |
| Retry amplification / hidden SDK retries | One Application retry owner, per-query and execution bounds, counted adapter invocations. |
| Cancellation makes a possibly processed request look safely cancelled | Certainty dominates; unresolved cancellation is UNKNOWN. |
| Lost authority during network call | No stale TX A grant; TX B/C recheck and roll back their new effects; recovery uses current actor. |
| Replay returns RUNNING as claimed final success | Immutable admission DTO separated from current terminal projection. |
| Foreign actor collides with project-wide idempotency key | Explicit broader uniqueness conflict, no cross-actor receipt disclosure. |
| Retry collapses identical query or duplicate hits | Query hash includes ordinal; separate attempt link; result identity is query+rank, not provider ID. |
| Malformed partial response leaks canonical rows | Validate complete bounded response, atomic TX B, no salvage. |
| Result/schema vendor contamination | Closed neutral DTOs; no raw JSON; no source/evidence promotion. |
| Freeze predicate versus plan supersession during execution | FROZEN at admission/start, exact historical reference thereafter; no latest-pointer substitution. |
| Unregistered attempt metadata hidden in execution JSON | Explicit supporting-schema ADR and typed FKs, review before implementation. |
| Terminal and late outcome race | Shared execution lock, write-once seal, terminal guard and one FINISHED event. |
| Migration changes prior accepted semantics | Single additive 0024 child, empty-only downgrade, frozen regression gates. |
| C1 commits cancellation intent, then immediate crash | Exact replay remains admission only; authorized new recovery performs C2→CANCELLED without provider. |
| Two recovery callers finish interrupted cancellation or seal unresolved attempt | Canonical locks/CAS; one seal/terminal event; loser rereads, no duplicate provider/provenance. |
| Terminal execution receives another cancel/recover key | New cancel denies; new recover may add only no-op receipt; exact replay inserts nothing. |
| Same request UUID has a different receipt scope | Distinct receipt key, normal checks; independent project-wide create uniqueness still enforced. |
| Same complete receipt key carries different payload | IDEMPOTENCY_CONFLICT; no new receipt/effects. |
| 40P01 occurs in TX B or in an earlier accepted service | PR2-04 wrapper rolls back and normalizes, retry persists same outcome without provider; earlier service behavior unchanged. |
| UNKNOWN replay or late response; recovery races terminal finalization | No redispatch/reopening; locked state/CAS and unique FINISHED admit only compatible read-only/no-op results. |

## 25. Completion and freeze criteria

Design readiness requires independent review of these three artifacts and upstream sources, with P0/P1=0 and no unresolved policy-level P2; specifically approve ADR-0011's supporting schema/hash admission and D04–D12 choices. Record an immutable design commit only through the authorized design workflow. **This pack is not itself that approval.** No implementation may start until the human explicitly establishes the accepted contract and authorizes PR2-04 implementation.

Future implementation completion requires all matrix requirements PASS with no missing parameter proof; real PostgreSQL18 migration/concurrency/authority/boundary evidence; full suite failed=0/errors=0/required skips=0; static gates and zero new formatter debt; clean committed candidate; prior acceptance preserved; independent closure review still pending. Executor may report READY_FOR_INDEPENDENT_CLOSURE_REVIEW, never self-accept PR2-04. Stop before PR2-05.
