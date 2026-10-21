# Phase 3 roadmap

> **Revision 2026-10-20:** Replaced the pre-exit backlog with accepted Phase 2 results, three owner-accepted gaps, B20/B23 exclusions and R4–R7 consequences; marked future schema/runtime work and retained owner TDG-3 decisions. This aligns the parked draft with actual exit evidence; implementation remains unauthorized.

**Status: DRAFT — awaiting owner approval; not authorized for implementation**

## Start here

Phase 3 adds a controlled agent runtime over the accepted Phase 1/2 system. It
coordinates research tasks, isolated coding and compute, candidate validation,
human checkpoints, and bounded experiment search. ResearchBase continues to own
scientific facts; every canonical write uses an Application Command.

**First action:** use the director-accepted Phase 2 exit of 2026-10-20, preserve
its explicit deferrals, and leave TDG-3 technology decisions to owner ADRs.
Then obtain explicit Phase 3
GO and a named PR execution pack. Approval of this roadmap alone authorizes no
code, migration, dependency activation, or external action.

**Proposed route:** bootstrap → task graph → execution and safety policies →
gateway/context/search records → sandbox and scientific roles → coding/compute
and recovery → sealed Run execution → native research strategy → bounded search
→ evaluation/security → E2E → hardening and STOP. Section 3 lists parallel waves;
migrations always merge and run serially.

**Conservative defaults:** native orchestration, one primary coding provider,
local isolated CPU compute, no default network or host access, A1/A2 operation,
human scientific freeze/release, and explicit hard budgets. Implement and test A3
within the Phase 3 scope, but enable it only under an approved bounded policy.
Keep EvoScientist and AI Scientist-v2 as method references; do not install their
runtimes merely to follow their workflow ideas.

**Three checks that matter most:**

- Phase 1 + Phase 2 exit tests continue PASS, with recorded commands and results.
- Every promoted object resolves to its task, execution, immutable harness
  fingerprint, promotion record, and ordinary scientific evidence.
- Crashes, unknown tool outcomes, budget exhaustion, rejected checkpoints, and
  failed/negative/pruned branches preserve history and stop unsafe continuation.

**Owner decisions:** deployment/sandbox, runtime/worker, coding provider and
alternate, data/model permissions, budgets, autonomy, schema allocation, and
acceptance thresholds. Recommended answers appear in section 4.

This remains a planning proposal. Phase 2 director GO on 2026-10-20 does not
authorize Phase 3 implementation.

## 1. Entry conditions and actual Phase 2 exit

Read [AGENTS.md](../../AGENTS.md),
[01 system architecture](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md),
[02 correction addendum](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md),
[03 registry](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md),
[08 compatibility](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md),
[06 Phase 3 spec](../architecture/06_Phase3_Development_Specification_v1.1_Harness_Integrated.md),
[11 TDG-2](../architecture/11_TDG2_Phase2_Technology_Decision_Gate_v1.0.md), and
[Harness specification](../harness/09_Harness_Integration_Specification_v1.0.md).
Include the final Harness Runtime Integration Addendum in 06. Prepared packages
are `PreparedSubmissionVersion`; `SubmissionVersion` means an actual external
send and remains deferred. Retrieval uses `LiteratureSearchExecution`.

The [Phase 2 exit report](../phase2/phase2_exit_report.md) records validate_exit
PASS: **16 PASS + 3 DEFERRED across 19 literal criteria**. The director's
[2026-10-20 review](../phase2/phase2_exit_review_2026-10-20.md) records integration
results of **12,523 passed, 66 skipped, 0 failed**, pyright 0 errors, ruff and
`git diff --check` clean, and one migration head. These are historical evidence,
not checks rerun for this proposal. R1–R3 corrections are reflected in the current
exit report and dependency inventory; read the review's conditional verdict
together with the subsequent director GO supplied for this task.

The inspected branch head is `0075_m1_reconsideration`, defined in
[migration 0075](../../migrations/versions/0075_m1_reconsideration.py).
Phase 2 delivered source identity/frozen lineage, retrieval/result resolution,
strategy and discussion promotion, conclusion support/closure, sealed manuscript
placements, citation/support separation, review/Issue/Decision/revision,
approvals/consumption/reconsideration, prepared-package consent/freeze,
retraction impact and citation rejection. The old B01–B32 completion inventory
is retired; remaining dispositions below are carry-over inputs, not blanket gaps.

Before PR3-00 implementation: record explicit owner Phase 3 GO, TDG-3 ADRs,
the accepted baseline revision and a separately authorized PR execution pack.
Preserve Phase 1/2 scientific hashes and resolve any new P0/P1. Accepted deferrals
are not PASS and do not by themselves reopen the accepted Phase 2 exit.

## Phase 2 completion backlog

Replaced with actual exit dispositions from the
[exit report](../phase2/phase2_exit_report.md) and
[independent review R4–R7](../phase2/phase2_exit_review_2026-10-20.md).
Dependencies constrain the named behavior; no row authorizes implementation.

| Carry-over input / actual state | Consequence / dependent Phase 3 PR |
| --- | --- |
| **B28 PaperQA2 — DEFERRED, Row 6**, owner 2026-10-19 ([intake](B28_PaperQA2_Intake_Assessment_DRAFT.md)). Fake ScientificRAG evidence does not prove a real adapter. | PR3-13/15/20/22 may use only admitted existing capabilities; PaperQA2-backed paths depend on separate pinned, licensed, security-reviewed intake and real fixtures. None for PR3-00/01. |
| **AQ-S3-08 — DEFERRED, Row 5 positive G2 AGENT admission only**, owner 2026-10-20 ([decision](B30S3_Architecture_Questions_2026-10-20.md)). No Application path creates a bound AGENT. | PR3-02 must settle real agent binding through the common identity boundary; PR3-15/20/22 depend on it for positive AGENT promotion evidence. PR3-01 proves HUMAN planning and denied AGENT paths only until that separate contract is accepted; never forge bindings. None for PR3-00. |
| **Linux benchmark host — DEFERRED, Row 17 host part only**, owner 2026-10-20 ([decision](Owner_Decision_Linux_Benchmark_Host_2026-10-20.md)). All other owning assertions passed; macOS timings remain informational. | PR3-23 and any earlier deployment/performance claims depend on executed host-specific evidence. None for PR3-00/01 functionality. |
| **B20 delivered**: `NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE`, typed `ScreeningBasis`, sealed probe/result children, exact historical reads; migration `0070_b20_screening_basis` ([contract](B20_Screening_Negative_Probe_Contract_DRAFT.md)). | PR3-13/15/17 reuse the bounded negative result; do not describe it as INCONCLUSIVE-only or require reimplementation. |
| **B20 exclusions**: prospective preregistration/external search exhaustiveness; automatic query planning/provider execution; programmable criteria; failed/adverse-branch replacement; universal priority claims; source-merge deduplication; automatic selection across independent comparison roots; automatic impact propagation. | PR3-13/15/17/18 cannot infer these from B20. Any selected extension needs its own owning contract; none is a PR3-00/01 dependency. Existing search/impact commands do not imply an automatic novelty workflow. |
| **B23 delivered**: exact NoveltyAssessment reviews, issue-only `NOVELTY_REASSESSMENT` referencing precommitted direct replacements, independent re-review leaving Issues OPEN; migration `0071_b23_novelty_review` ([contract](B23_Novelty_Review_Revision_Contract_DRAFT.md)). | PR3-14/15/22 reuse these exact commands; a re-review link does not resolve an Issue. |
| **B23 exclusions**: novelty-target Decisions, NO_CHANGE, Issue disposition/blocking-concern resolution; direct PriorArtRelation/SearchCoverage review targets; assessment creation inside review/revision; Claim/source/manuscript changes as novelty results. No novelty-driven approval, READY/package gate or generic Agent runtime. | PR3-14/15/18/22 stop at admitted result/target shapes; broader novelty gates need separate approval. None for PR3-00/01. `MANUSCRIPT_CHANGE` exists for manuscript concerns through M1 (0074/0075), but remains excluded as a novelty result. |
| **R4 P3 — migrations 0041/0044**: revision guards FOR UPDATE versus reviewers FOR SHARE; correct but adds waiting. | PR3-14/15 concurrency planning and PR3-23 hardening should measure contention; no correctness blocker or permission to reorder accepted locks. None for PR3-00/01. |
| **R5 P3 — persistence/database.py**: `b04_write_timeouts` / `b05_write_timeouts` connection flags differ from SET LOCAL style. | PR3-01 must bound the first lock wait without copying inconsistent setup; PR3-23 may propose normalization in separate scope. No prerequisite fix for PR3-00/01. |
| **R6 P3 — 0074 `pr212_draft_guard`**: dead second DELETE block. | PR3-23 may remove it only in a separately scoped forward migration after 0075; never rewrite 0074. None for PR3-00/01. |
| **R7 P3 — adapters/literature_http.py**: accepted single-peer DNS pinning without fallback; timed-out lookup leaves a daemon thread. | PR3-13/15/21/23 inherit these availability/resource limits when using literature HTTP; any fallback/thread repair needs scoped security/failure evidence. None for PR3-00/01. |

Official STORM adapter, full authority/IRB/resources and actual venue submission
remain optional extensions. TDG-2 accepts roles/boundaries; it does not itself
enable providers, close B28, or decide TDG-3.

## 2. All 24 PRs

IDs below omit the `PR3-` prefix. Dependencies are proposed **hard merge/acceptance
prerequisites**, in addition to the entry gate; the spec gives broad work-package
dependencies, not this detailed DAG. Parallel means separate implementation after
shared contracts freeze, never simultaneous migration merges or early activation.
Listed peers are examples and must meet their own prerequisites.

**New schema** means **new in the owning PR3-xx**, absent from this branch,
including every field, enum, command and service allocated to that PR. It is
planned persistent structure, not a new scientific model. Yes rows use registry objects or specified operational patterns;
final field/migration allocation needs review. No rows reuse records, artifacts,
ports or config; they may not quietly add tables. HarnessFingerprint and working
memory are manifests/ArtifactVersions, not new canonical entities. Promotion
outputs and canonical ID collections use concrete FKs/typed relation rows, never
JSON or a sole `target_type + target_id` reference.

Risk shorthand in the last column:

- **M:** selected model/API and inherited literature providers; unresolved service,
  model and content terms, data disclosure, prompt injection, cost.
- **S:** sandbox engine and image; resolve engine/image/package licenses, review
  escape/host mounts, network and secret exposure.
- **C:** coding provider/SDK/protocol client; resolve exact component/service terms,
  review arbitrary commands, dependency installation and repository disclosure.
- **J:** compute scheduler/worker/broker if selected; resolve component/service
  terms, review credentials, runaway jobs, duplicate dispatch and unknown outcomes.

All licenses remain **unresolved for the future selected immutable revisions**;
these are intake risks, not current license findings. Existing PostgreSQL and
ArtifactStore are inherited infrastructure. “None” means no new external runtime
dependency. Do not add packages solely because a role exists.

| PR | Purpose in one sentence | Hard dependencies | Can build in parallel with | New schema | External dependency and license/security risk |
|---|---|---|---|---|---|
| PR3-00 | Establish runtime modules, empty migration plumbing and boundary tests. | Entry gate | None | No (empty bootstrap only) | None; no framework activation. |
| PR3-01 | Store research tasks and their dependency graph with commands and queries. | 00 | None in proposed waves | Yes: task/step/dependency and typed input rows | None. |
| PR3-02 | Record immutable agent versions and attributable executions and promotion history. | 01 | 04 | Yes: AgentVersion, availability, execution, AgentPromotionRecord and typed outputs | None; fingerprint resolver uses pinned manifests, not vendor state. |
| PR3-03 | Route every tool call through a policy-enforced gateway and invocation record. | 02, 04 | 05, 16 | Yes: CapabilityInvocation, AgentToolPolicy and typed refs | Optional tool/MCP SDK: C/M; tool descriptions grant no permissions. |
| PR3-04 | Enforce autonomy limits, hard budgets, termination and human checkpoints. | 01 | 02 | Yes: budget, termination policy, checkpoint | None; checkpoint cannot authorize scientific release by itself. |
| PR3-05 | Reload permitted canonical context and save rebuildable task memory as artifacts. | 02, 04 | 03, 16 | No | None; project disclosure risk through context/artifacts remains. |
| PR3-06 | Execute generated code inside constrained sandbox profiles. | 03 | 08, 12, 13, 14 | No | Chosen Docker/Apptainer/managed sandbox: S. |
| PR3-07 | Submit, poll, cancel and reconcile compute jobs without confusing jobs with Runs. | 06 | 09, 10, 17, 19 | No | Selected isolated compute backend/scheduler: S/J. |
| PR3-08 | Define the coding contract and fake adapter with artifact and semantic-edit checks. | 03, 05 | 06, 12, 13, 14 | Yes: SemanticImpactAssessment | None; fake adapter introduces no coding vendor. |
| PR3-09 | Connect one primary coding agent and retain patches, tests, commands and versions. | 06, 08 | 07, 10, 17, 19 | No | Codex or approved equivalent: C/M/S. |
| PR3-10 | Add a replaceable alternate coding adapter behind the same contract. | 06, 08 | 07, 09, 17, 19 | No | OpenHands or ACP-compatible provider: C/M/S; SHOULD, explicit deferral possible. |
| PR3-11 | Create and seal ordinary Runs from frozen inputs and collect execution outcomes. | 05, 07, 08, 09, 19 | No independent peer in proposed waves | No | Inherited coding/sandbox/compute: C/S/J; no extra framework. |
| PR3-12 | Produce analysis and statistical/artifact candidates without altering measurements. | 03, 05 | 06, 08, 13, 14 | No | Selected model/statistics capability: M; any new analysis library needs license review. |
| PR3-13 | Produce evidence-backed critiques of leakage, methods and overclaim. | 03, 05 | 06, 08, 12, 14 | No | Selected model and existing literature capabilities: M. |
| PR3-14 | Reconstruct an independent reviewer context and explicitly promote review candidates. | 03, 05 | 06, 08, 12, 13 | No | Selected reviewer model: M; no author scratchpad or approval capability. |
| PR3-15 | Orchestrate the native plan-to-review scientific workflow with human gates. | 11, 12, 13, 14, 19 | None in proposed waves | No | Inherited M/C/S/J; EvoScientist is a method reference, external adapter optional. |
| PR3-16 | Preserve search sessions, nodes, parent lineage and exact Run links. | 02, 04 | 03, 05 | Yes: search session/node/Run relation rows | None; failure/pruning never deletes history. |
| PR3-17 | Choose and record progressive tree-search actions using bounded search heuristics. | 05, 13, 16 | 07, 09, 10, 19 | Yes: SearchDecisionRecord and typed candidate-node relations | Optional selected model: M; AI Scientist-v2 is a method reference. |
| PR3-18 | Run A3 experiment loops under explicit budgets, policy and scientific gates. | 04, 15, 17, 19 | None in proposed waves | No | Inherited M/C/S/J; no new autonomous framework. |
| PR3-19 | Make background execution crash-safe through durable dispatch, leases and recovery. | 03, 04, 05 | 07, 09, 10, 17 | Yes: operational outbox/inbox/lease patterns as selected | Worker/broker only if TDG-3 selects one: J; PostgreSQL-backed default avoids new broker. |
| PR3-20 | Evaluate golden agent tasks, Skill behavior and runtime safety metrics. | 00–19 (10 accepted or explicitly deferred) | 21 | No | Inherited providers for live evals: M/C/S/J; optional eval tools require intake. |
| PR3-21 | Inject sandbox, prompt/tool, memory and privilege failures and verify containment. | 00–19 (10 accepted or explicitly deferred) | 20 | No | Chosen real sandbox/adapters: S/C/J/M; contain adversarial fixtures. |
| PR3-22 | Prove controlled research, debug, negative-result, search and review workflows end to end. | 20, 21 | None | No | Selected production-profile adapters: M/C/S/J; fakes alone cannot prove real isolation. |
| PR3-23 | Finish performance, migration compatibility, documentation and the exit evidence report. | 22; every earlier required PR accepted | None | No (repairs require explicit scope) | Inventory/review existing dependencies; no new provider by default. |

**DO NOT ADD SCHEMA.** Entity + Relation + Assessment + Snapshot + Event remain
the modeling patterns. Existing scientific rows lack workflow-owned identity,
limits and delivery history; adding those semantics there would duplicate or
corrupt scientific ownership. The following are insufficiency reasons for typed
instances of existing patterns, not approval of a new canonical concept. Each
concrete table still requires its own one-line reason and owner/ADR admission in
the owning execution pack before DDL; conceptual families are not table approval.

| New in PR | Proposed structure / reason existing scientific rows are insufficient |
| --- | --- |
| PR3-01 | Task/step, dependency, typed inputs, events and receipts retain workflow identity, same-task FKs and replay history absent from scientific records; per-table reasons are in PR3-01 §5. |
| PR3-02 | Agent version/availability separate immutable behavior from availability; execution retains agent attempts distinct from Run; promotion/typed outputs bind atomic candidate attribution absent from scientific rows. |
| PR3-03 | Invocation/typed refs retain tool outcomes distinct from Run; policy retains exact tool permissions absent from scientific entities. |
| PR3-04 | Budget/termination/checkpoint retain enforceable workflow limits and responses that scientific Approvals do not represent. |
| PR3-08 | SemanticImpactAssessment instantiates Assessment for code semantic changes; scientific results cannot stand for code-change validation. |
| PR3-16 | Search session/node/Run relations retain failed/pruned branch lineage absent from individual Runs. |
| PR3-17 | SearchDecisionRecord/candidate-node relations retain heuristic branch-selection basis; scientific Decisions must not acquire search heuristic semantics. |
| PR3-19 | Operational dispatch/deduplication/lease patterns, if selected by the owner, retain delivery/crash reconciliation absent from immutable scientific Events; evaluate reuse first. |

Proposed allocation closes requirements absent from individual PR titles:
PR3-02 owns atomic promotion provenance and immutable harness fingerprint binding;
PR3-05 owns promotion validation/context services using that record; PR3-03 owns
SkillRegistryLoader/SkillRouter, RoutingPolicy, CapabilityPolicy and supply-chain
and self-modification enforcement; PR3-14 owns ReviewerContextBuilder; PR3-20 owns
minimum SkillEvaluationRunner. PR3-15 supplies planner/design/debug/writing roles
and strategy configuration. Freeze these allocations in execution packs rather
than inventing extra PRs, Skill entities, or a second scientific state store.

## 3. Proposed waves

| Wave | Work that can proceed together | Gate before the next dependent wave |
|---|---|---|
| 0 | PR3-00 | Entry conditions and empty bootstrap/boundary tests accepted. |
| 1 | PR3-01 | Task/step contracts and shared typed FK/policy interfaces frozen. |
| 2 | PR3-02 + PR3-04 | Execution/promotion/fingerprint and budget/checkpoint contracts accepted. |
| 3 | PR3-03 + PR3-05 + PR3-16 | Gateway/routing, context isolation and search lineage accepted. |
| 4 | PR3-06 + PR3-08 + PR3-12 + PR3-13 + PR3-14 | Sandbox, coding contract, candidate-only roles and independent review accepted. |
| 5 | PR3-07 + PR3-09 + PR3-10 + PR3-17 + PR3-19 | Compute/coding contracts, search decisions and durable recovery accepted. |
| 6 | PR3-11 | Frozen input → sealed Run → outcome proven, including crash reconciliation. |
| 7 | PR3-15 | Native full workflow and human gates accepted. |
| 8 | PR3-18 | Bounded A3, statistical guardrails and retention accepted. |
| 9 | PR3-20 + PR3-21 | Evaluation thresholds and security/failure matrix pass. |
| 10 | PR3-22 | All five golden E2Es and required cross-phase regressions pass. |
| 11 | PR3-23 | Exit report, inventories, migrations and owner acceptance; STOP for Phase 4 GO. |

This maximizes independence within frozen contracts rather than parallelizing
shared state changes. Fakes/fixtures and future acceptance matrices can be designed
early; they do not count as accepted implementations. Roles in wave 4 use accepted
Phase 1/2 data and gateway fakes; real Run integration follows PR3-11.

PR3-19 is deliberately earlier than PR3-11/15/18 despite its higher number.
PR3-07 may build its job port/reconciliation contract in parallel with it, but
unattended external dispatch is disabled until recovery is accepted. No async
side effect runs inside a long canonical transaction. Record intent and logical
action identity durably, call outside the transaction, then ingest/reconcile in a
new Application transaction; unknown outcome is never permission to retry blind.

**Migration lane:** no scientific `ON DELETE CASCADE`; one owner, one Alembic head, additive reviewed migrations,
no edits to accepted revisions. Proposed schema merge order is
01 → 02 → 04 → 03 → 16 → 08 → 17 → 19. Each merge verifies PostgreSQL 18 clean
install, upgrade from the accepted baseline, concrete FK/RESTRICT and immutability
constraints, and forward-only recovery. New downgrade entry points must refuse; repairs
use reviewed forward revisions, preserving accepted history. Rebase subsequent migrations after each accepted head.

Task references to policies/executions cross these PRs. Freeze the complete FK
layout before wave 2; use a reviewed staged migration plan and keep incomplete
runtime operations disabled. Do not resolve staging by soft references, fabricated
policies or weak final constraints. Schema work in parallel branches remains
unmerged until its turn; shared migration/model files have one owner. A migration
order that needs a different staging contract returns to architecture review.

## 4. Owner decisions before Phase 3 starts

These are recommendations for approval, not selections already made.

| Decision | Recommended conservative answer |
|---|---|
| Phase entry and carry-overs | Phase 2 director GO is recorded; retain the three DEFERRED dispositions and B20/B23 exclusions. Phase 3 GO and TDG-3 remain owner actions. |
| Deployment and compute | Start with DEV_LOCAL, isolated CPU-only jobs and a dedicated worker; no cloud/HPC credentials or GPU scheduling until separately reviewed. |
| Sandbox | Use a constrained container backend on a dedicated execution host/VM; deny host home/socket mounts, privileged mode, network and secrets by default; enforce CPU/memory/disk/process/time limits. Choose Docker versus Apptainer in TDG-3 after host and license/security review. |
| Runtime framework | Own a small native state machine and native EvoScientist-like strategy; defer LangGraph/DeepAgents/DeerFlow/EvoScientist service dependencies. Persist recoverable ResearchBase task state regardless of framework. |
| Queue and workers | Begin with a PostgreSQL-backed dispatcher and explicit leases/idempotency; no Redis or separate broker by default. Review PR3-19 outbox/inbox guarantees before unattended jobs. |
| Coding providers | Select one primary adapter for PR3-09; retain fake adapter tests. Prefer one narrowly scoped alternate in PR3-10 after intake; if deferred, record the SHOULD deferral and its coverage limit explicitly. No SDK embedding by default. |
| Models, data and credentials | Approve one model profile and permitted data classes first; block project sharing and provider upload unless explicitly permitted. Keep service credentials outside agent workspaces and logs. |
| Autonomy and formal gates | Default A1/A2; human ExperimentSpec/Claim freeze and formal release. Test A3 in bounded approved tasks; automatic spec freeze requires explicit A3 authority policy. No A4, self-approval or external venue send. |
| Budget values | Start pilots at 30 minutes/task, 50 agent steps, 50 model calls, 20 search calls, 3 code iterations, 5 Runs, 10 nodes, depth 3, 1 parallel branch, 0 GPU hours and a USD 5 equivalent token-cost cap. These proposed caps require owner/provider feasibility approval; no unlimited or agent-raised limit. |
| Termination and extensions | Hard-stop on the first exhausted bound; stop after 2 repeated failures or 2 no-improvement iterations. Human may explicitly approve a new budget; retain original usage and termination history. Cancel/reconcile active jobs on stop and demonstrate bounded overshoot. |
| Schema and promotion allocation | Accept only registry/pattern-based increments listed above, including immutable AgentPromotionRecord in the same transaction as canonical create/revise. Require typed promoted target FKs and availability separate from AgentVersion. No new HarnessFingerprint/Skill/memory scientific entity. |
| Skill/tool intake and versioning | Use the existing bounded Skill registry; approve each executable revision, license, scripts and capabilities, then pin it. Keep reference-only libraries marked as references. Block unreviewed install and same-execution harness weakening. |
| Evaluation and release thresholds | Require zero direct-write, self-approval, closure, isolation, history-deletion and hard-budget violations; all required deterministic safety/golden tests pass. Set quality/cost/recovery targets on fixed fixtures before PR3-20; do not invent a paper-quality success threshold after seeing results. |
| Review and operational accountability | Require separate reviewer execution/context built from specs, canonical state, diff/artifacts and test evidence; assign migration, security, budget and incident owners. Close P0/P1 before gate success. |

For every selected external dependency, the TDG-3/ADR intake must resolve the
exact source/revision, license and service terms, transitive packages/images,
capabilities, data retention/disclosure, patching and rollback. Pin enabled
production harness material and bind its fingerprint to executions. The repository
specs are not evidence of any upstream's current license or safety.

## 5. Exit evidence and glossary

PR3-23 must report Phase 3 spec §82 **and** the final harness exit extension:
resumability, provenance, gateway policy, A0–A3/checkpoints, hard budgets, context
and memory separation, isolation, coding artifacts, compute reconciliation,
sealed Runs, candidate-only analysis/critique, independent review, native workflow,
search lineage/retention, bounded A3, injection resistance, project isolation,
routing, fingerprints, supply-chain review and self-modification guards. Phase 1
and Phase 2 exits continue PASS. Include unit/application, real PostgreSQL
integration/migration, adapter contract, crash/recovery, sandbox, security and
E2E evidence; report not-run/blocked/skipped accurately.

Deliver `phase3_exit_report.md`, `agent_runtime_inventory.md`,
`capability_adapter_inventory.md`, `sandbox_security_report.md`,
`autonomous_search_trace_demo.md`, `agent_evaluation_report.md`, and
`recovery_failure_injection_report.md`. Then STOP; Phase 4 needs separate GO.
This draft creates none of those acceptance artifacts.

| Shorthand | Plain meaning |
|---|---|
| PR / slice / wave | One scoped change / a limited portion of it / independent changes grouped for scheduling. |
| GO / gate / exit | Owner authorization to start / required acceptance check / evidence and review closing a phase. |
| TDG-3 / ADR | Phase 3 technology decision gate / recorded architecture decision with compatibility and rollback review. |
| DAG / FK / UoW / TX | Dependency graph without cycles / database foreign key / unit of work / transaction. |
| Canonical / candidate / promotion | Owning domain's accepted record / proposed output / explicit validated Application write with attribution. |
| Frozen closure / sealed Run | Exact immutable dependencies all the way down / Run inputs locked before execution. |
| AgentExecution | Short name for AgentExecutionInstance; distinct from a scientific Run and a tool invocation. |
| Capability / gateway / strategy / Skill | Tool ability / enforced tool boundary / workflow method / versioned responsibility and safety contract. |
| HarnessFingerprint | Immutable manifest identifying the effective runtime, model, policies, Skills and adapters. |
| A0 / A1 / A2 / A3 | Suggest / draft / execute approved plan / bounded autonomous loop; none grants scientific authority. |
| Outbox / inbox / lease / reconcile | Durable dispatch intent / duplicate-work guard / temporary worker ownership / determine an uncertain external outcome. |
| E2E / MCP / ACP / HPC | End-to-end test / tool protocol / coding-agent protocol / high-performance compute. |
| P0 / P1 / P2 / P3 finding | BLOCKER / MAJOR / MINOR / SUGGESTION; these severities differ from permission-policy P0–P4 labels. |
| M / S / C / J risk | Model/provider / sandbox / coding adapter / compute-worker risks defined above. |

Documentation-only revision. Future acceptance commands above are not current
execution evidence and do not establish Phase 3 GO.
