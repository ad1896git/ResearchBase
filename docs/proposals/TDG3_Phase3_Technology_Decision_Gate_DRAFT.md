# ResearchBase TDG-3 — Phase 3 Technology Decision Gate DRAFT

**Status:** APPROVED by owner 2026-10-20 — all recommended options; recorded in ADR-0021
**Authority:** AGENTS.md; Final Architecture Correction Addendum A13; System Architecture; Global Registry; Cross-Phase Contracts; Phase 3 specification and Harness Integration Specification.
**Scope:** Exactly the fourteen owner decisions in Phase 3 roadmap §4. Recommendations only; no implementation, migration, dependency installation, provider activation or Phase 3 GO is authorized.

## Decision basis

Read this proposal under the precedence established by [AGENTS.md](../../AGENTS.md), [System Architecture](../architecture/01_ResearchBase_System_Architecture_v1.3_Harness_Integrated.md), [Correction Addendum](../architecture/02_Final_Architecture_Correction_Addendum_v1.0.md), [Global Registry](../architecture/03_Global_Schema_and_Contract_Registry_v1.0.md), [Cross-Phase Contracts](../architecture/08_Cross_Phase_Contracts_and_Compatibility_v1.1_Harness_Integrated.md), [Phase 3 specification](../architecture/06_Phase3_Development_Specification_v1.1_Harness_Integrated.md), and [Harness Integration Specification](../harness/09_Harness_Integration_Specification_v1.0.md). The concise decision/required-contract structure follows [TDG-2](../architecture/11_TDG2_Phase2_Technology_Decision_Gate_v1.0.md).

The planning source is [Phase 3 roadmap DRAFT](PHASE3_Roadmap_DRAFT.md), §4 (`docs/proposals/PHASE3_Roadmap_DRAFT.md`, landing in the same merge). It is a planning proposal, not a new normative repository contract. Repository baseline inspected: `286cd9ae985dcad91d3e225b4b50c5c46fadeef5`.

Section references below refer to the Phase 3 specification unless qualified. Its final **Harness Runtime Integration Addendum** repeats the number 85; references to “Harness §85.x” mean that final addendum, not the earlier reference-system pinning notes. PR identifiers use specification §79; detailed schema allocation and recovery ordering are roadmap proposals requiring approved execution packs.

All upstream facts, including exact versions/revisions, licenses, service/model terms, prices, retention policies and security properties, are **to verify at intake** unless an identified repository file proves the specific fact. Product names below identify candidates, not verified upstream capabilities or approvals. Older upstream descriptions in specification §85 are historical references, not current intake evidence. Repository requirements such as PostgreSQL 18.x are requirements, not proof of an installed version or license. No upstream installation or live verification is performed by this draft.

## Decisions

### TDG3-01 — Phase entry and first-slice gaps

**Question:** Is explicit Phase 3 GO granted, and which first PR is authorized?

**Accepted baseline:** Phase 2 was accepted on 2026-10-20 by director GO under owner delegation; see the [Phase 2 exit report](../phase2/phase2_exit_report.md) and [independent director review](../phase2/phase2_exit_review_2026-10-20.md). Its recorded owner-accepted deferrals remain explicit; Phase 2 acceptance does not grant Phase 3 GO.

**Options:** (A) Grant explicit Phase 3 GO and authorize PR3-00 only against the accepted Phase 2 baseline; (B) withhold Phase 3 GO; (C) name another first PR with its explicit authorization and prerequisites.

**Recommended option and required contract:** A: recommend PR3-00 only as the first authorized PR. Partial contract freezes cannot supply the scientific/governance boundary on which agents depend. Require accepted Phase 1/2 regression evidence, full Phase 2 E2E/hardening and exit artifacts, resolution of open P0/P1 findings, TDG-3 ADRs, and a named authorized PR pack. PreparedSubmissionVersion proves preparation, never an external send. Preserve Phase 1 hashes. Preserve the recorded owner-accepted Phase 2 deferrals; other mandatory exit rows may not be relabeled optional. Basis: Cross-Phase §§6, 42; Correction A17–A23; §§0, 81–82.

**Before selection:** Source/revision: identify accepted Phase 2 contracts, commits, exit report and exact command/count evidence, including blocked/skipped rows. License/terms: reconcile inherited adapter approvals; unresolved upstream facts are **to verify at intake**. Transitive dependencies: compare accepted inventories and locks. Security/data exposure: close required adapter, authorization and disclosure findings. Rollback: demonstrate that denied entry leaves the accepted baseline unchanged and no Phase 3 runtime enabled.

**Dependent PRs:** PR3-00–23; this is the common entry prerequisite.

**Owner question:** Do you grant explicit Phase 3 GO, and authorize (A) PR3-00 only (recommended), (B) no PR yet, or (C) another explicitly named first PR?

### TDG3-02 — Deployment and compute

**Question:** Which deployment and compute profile starts Phase 3?

**Options:** (A) DEV_LOCAL with isolated CPU jobs and a dedicated worker; (B) TEAM_SINGLE_NODE with shared execution capacity; (C) HPC_RESEARCH/cloud scheduling with GPU access.

**Recommended option and required contract:** A. It limits operational and credential scope while exercising real submit/poll/cancel/reconcile behavior. The worker uses the sandbox selected in TDG3-03 on a dedicated execution host/VM; DEV_LOCAL does not permit generated shell on the developer host. Compute jobs are CapabilityInvocation external handles, distinct from scientific Runs. No cloud/HPC credentials or GPU scheduling initially. Other profiles must retain identical Domain/Application semantics. Basis: Correction A14–A15; §§12–14, 49–50.

**Before selection:** Source/revision: record host/VM, OS, compute adapter and image identities; upstream details are **to verify at intake**. License/terms: review host, image, scheduler and any service terms. Transitive dependencies: inventory guest packages, images and worker components. Security/data exposure: prove resource, workspace, egress and credential boundaries on the actual deployment. Rollback: stop dispatch, cancel/reconcile active jobs and retain handles/artifacts before disabling the profile.

**Dependent PRs:** PR3-00, 06–07, 09–11, 15, 18–23.

**Owner question:** Do you approve DEV_LOCAL with dedicated isolated CPU execution and no GPU or cloud credentials?

### TDG3-03 — Sandbox

**Question:** Which sandbox backend and enforceable profile may execute generated code?

**Options:** (A) Constrained Docker backend on a dedicated host/VM; (B) constrained Apptainer backend on an approved host; (C) managed sandbox API with approved disclosure terms.

**Recommended option and required contract:** A, conditional on host and intake evidence; choose B instead if that evidence better fits the approved deployment. Neither name establishes isolation. Deny host home/socket mounts, privileged execution, arbitrary host processes, network and secrets by default. Use read-only inputs, a scoped writable workspace and explicit CPU, memory, disk, process and wall-time caps. Any package installation or allowlisted egress needs policy approval. No real adapter activation until containment is demonstrated. Basis: §§12, 50–52, 76–77.

**Before selection:** Source/revision: resolve engine, host configuration, images/digests and adapter revision, all **to verify at intake**. License/terms: inspect engine, desktop/service if used, images and bundled software separately. Transitive dependencies: inventory base-image packages and privileged helpers. Security/data exposure: test escape/host/socket access, cross-project access, outbound traffic, secret enumeration and resource exhaustion. Rollback: kill/reconcile jobs, revoke execution access and quarantine affected workspaces without erasing invocation or scientific history.

**Dependent PRs:** PR3-06–11, 15, 18–23; PR3-08 defines the contract against this profile.

**Owner question:** Do you approve a constrained Docker sandbox subject to host, license and containment intake?

### TDG3-04 — Runtime framework

**Question:** Who implements recoverable orchestration, and where does its authoritative state live?

**Options:** (A) ResearchBase-owned small state machine and native scientific strategy; (B) thin pinned LangGraph-style runtime adapter; (C) thin external EvoScientist/DeerFlow-style service adapter.

**Recommended option and required contract:** A. Existing task, step, execution, invocation, budget and checkpoint contracts suffice without a new framework dependency. Implement native EvoScientist-like orchestration and progressive search methods; external projects remain references. A future adapter may replace scheduling mechanics, but cannot own canonical science or hold the only recoverable task state. Persist ResearchBase state through Application Services and preserve immutable execution/fingerprint provenance. Basis: §§2–3, 19–20, 54–55; Harness §§85.1–85.4, 85.7; Cross-Phase §23.

**Before selection:** Source/revision: freeze native runtime contracts and reference revisions; external runtime facts are **to verify at intake**. License/terms: review any copied reference material and any later adapter/service. Transitive dependencies: show the native plan needs no new framework and inventory inherited runtime dependencies. Security/data exposure: review dynamic execution, checkpoint loading and gateway bypass risks. Rollback: pause dispatch and restore a compatible runtime against durable ResearchBase records; never rewrite frozen scientific state or discard failed executions.

**Dependent PRs:** PR3-00–05, 15–20, 22–23.

**Owner question:** Do you approve native orchestration with no external agent runtime dependency initially?

### TDG3-05 — Queue and workers

**Question:** How will background work be dispatched and recovered?

**Options:** (A) PostgreSQL-backed dispatcher, dedicated worker, explicit leases and idempotency; (B) separate broker and worker framework behind the same ResearchBase contracts.

**Recommended option and required contract:** A; no Redis or separate broker. Use reviewed operational outbox/inbox/lease patterns with durable logical-action IDs and crash reclaim. Commit intent in one Application transaction, perform external I/O outside it, and ingest/reconcile in another. Lease expiry alone cannot prove an external job failed; fence stale workers and reconcile UNKNOWN outcomes before retry. Accept PR3-19 recovery before unattended dispatch and before dependent PR3-11/15/18 activation, despite numeric PR order. Basis: §§45–49; Correction A14.

**Before selection:** Source/revision: freeze dispatcher/lease contracts and verify deployed PostgreSQL/driver revisions, **to verify at intake**. License/terms: review inherited database/driver and proposed worker components; no broker approval is implied. Transitive dependencies: demonstrate the dispatcher reuses the accepted stack. Security/data exposure: verify least-privilege service access, duplicate delivery, stale-worker fencing, crash-after-submit and unknown-handle reconciliation. Rollback: drain or pause dispatch, reconcile in-flight work and retain inbox/outbox history; no destructive queue reset.

**Dependent PRs:** PR3-03–04 define shared contracts; PR3-07, 09–11, 15, 17–23 consume dispatch/recovery guarantees; PR3-19 owns implementation.

**Owner question:** Do you approve PostgreSQL dispatch and leases with no Redis or separate broker?

### TDG3-06 — Coding providers

**Question:** Which primary and alternate coding adapters should Phase 3 accept?

**Owner constraint (2026-10-19):** subscription quotas (for example the accounts behind the Codex CLI or Antigravity `agy` used by the development pipeline) must not be used as an LLM API backend for product features. Product adapters therefore need API-based access under service terms that permit this use; the development pipeline's CLIs are not candidates by default. **Options:** (A) one API-based primary coding adapter under API service terms (provider to be named by the owner at intake) with the alternate deferred as an explicit SHOULD deferral; (B) an API-based primary plus a narrowly scoped API-based alternate, each after separate intake; (C) fake adapter only for now, real adapters deferred until a provider and budget are approved. Identities and terms are **to verify at intake**; retain the fake adapter in every option.

**Recommended option and required contract:** A. Name one API-based primary for PR3-09 at intake and record PR3-10 as an explicit SHOULD deferral with its coverage limitation; exact identity, terms and fitness remain **to verify at intake**. Do not use the pipeline's subscription CLIs as product adapters. Prefer a thin replaceable integration, with no SDK embedding by default. Keep PR3-08 fake contract coverage. Record repository/workspace hashes, model/provider, commands, patch/source/configuration/lock/test artifacts and actual workspace outcome. Completion text cannot establish success; semantic edits require assessment and, when material, a new ExperimentSpecVersion. Basis: §§10–11, 36–37, 63–68, 79.

**Before selection:** Source/revision: resolve exact client/API/CLI, protocol and adapter identities, **to verify at intake**. License/terms: review executable and service terms, repository disclosure and generated-output conditions. Transitive dependencies: inspect clients, bundled runtimes and optional SDK trees. Security/data exposure: verify allowed paths/commands, install policy, upload restrictions, secrets isolation and sandbox enforcement. Rollback: disable an adapter, reconcile outstanding work and switch through a new CapabilityInvocation; retain earlier failures and fingerprints.

**Dependent PRs:** PR3-08–11, 15, 18–23; PR3-10 must be accepted or explicitly deferred with its coverage limitation.

**Owner question:** Choose (A) one API-based primary (you name the provider) with the alternate deferred (recommended), (B) API-based primary plus alternate, or (C) fake adapter only for now; the fake adapter stays in all cases.

### TDG3-07 — Models, data and credentials

**Question:** Which model profile may process which data using which credentials?

**Owner constraint (2026-10-19):** subscription quotas (for example the accounts behind the Codex CLI or Antigravity `agy` used by the development pipeline) must not be used as an LLM API backend for product features. Product adapters therefore need API-based access under service terms that permit this use; the development pipeline's CLIs are not candidates by default. **Options:** (A) One API-based model profile (owner names provider and model at intake), with the smallest permitted data class: synthetic/test fixtures only for pilots, and credentials held by the host owner outside agent workspaces; (B) other owner-named profile, data scope or credential arrangement, subject to separate approval. The existing provider/profile candidate is **to verify at intake**.

**Recommended option and required contract:** A. Start with one API-based profile named by the owner and synthetic/test fixtures only for pilots; no subscription quota is used; exact profile and provider terms are **to verify at intake**. The host owner holds credentials outside agent workspaces. Approve exact model/provider identity, data classes, project scope and allowed operations before upload. Deny cross-project sharing and provider transmission unless explicitly permitted. Inject service credentials at the trusted gateway/adapter boundary, outside agent workspaces, prompts, artifacts and logs. Record model changes in execution provenance; do not silently fall back to another provider. A service alias alone must not be represented as an immutable model revision when the provider cannot prove that mapping. Basis: §§8, 26–27, 38, 50–52; Harness §85.4.

**Before selection:** Source/revision: resolve model/profile, endpoint and adapter identity and document any reproducibility limitation, **to verify at intake**. License/terms: verify model/data rights, retention, training use, region and deletion terms. Transitive dependencies: inspect client, tokenizer and model artifacts if used. Security/data exposure: approve the data-flow matrix, redaction, project access, credential rotation and egress tests. Rollback: block upload, revoke credentials, reconcile calls and restore an approved profile without changing historical attribution.

**Dependent PRs:** PR3-02–05, 08–15, 17–23; inherited literature/model capabilities need the same scope checks.

**Owner question:** Choose (A) one API-based profile you name, synthetic/test fixtures only for pilots, API credentials held by you outside agent workspaces (recommended; to verify at intake), or (B) other explicitly named profile/data/custodian arrangement?

### TDG3-08 — Autonomy and formal gates

**Question:** What autonomy may run by default, and who freezes or releases scientific records?

**Options:** (A) A1/A2 default with human scientific freeze/release and separately enabled bounded A3; (B) bounded A3 as the deployment default under an explicit authority policy.

**Recommended option and required contract:** A. Implement and test A0–A3, including the required PR3-18 loop, while enabling A3 only for approved bounded tasks. Human ExperimentSpec/Claim freeze and formal release remain the default. Any automatic ExperimentSpec freeze needs explicit A3 authority policy and the ordinary owning command; A3 itself grants no authority. HumanCheckpoint controls workflow and is not an ApprovalGrant. Auditors cannot approve; no A4, self-approval or venue send. Basis: §§21–22, 28, 58, 66; Harness §85.6.

**Before selection:** Source/revision: identify exact autonomy, checkpoint and owning freeze/approval command contracts. License/terms: recheck enabled provider permissions, **to verify at intake**; policy adds no upstream entitlement. Transitive dependencies: confirm gates use existing Application/governance boundaries, with no new authority framework. Security/data exposure: prove denied operations, rejection/expiry, project isolation and non-bypassable release checks. Rollback: disable new A3 starts, stop/reconcile existing tasks and preserve checkpoints, decisions and usage.

**Dependent PRs:** PR3-01, 03–05, 11, 14–15, 18, 20–23.

**Owner question:** Do you approve A1/A2 defaults with human freeze/release and separately authorized bounded A3?

### TDG3-09 — Budget values

**Question:** What exact hard caps apply to initial pilot tasks?

**Options:** (A) The roadmap pilot caps below; (B) stricter fixture-only caps until provider/resource feasibility is established; (C) separately approved larger finite caps per task profile.

**Recommended option and required contract:** A, subject to feasibility approval; use B if accounting cannot enforce A. Caps per task: **1,800 seconds wall time; 50 agent steps; 50 model calls; 20 search calls; 3 code iterations; 5 Runs; 10 tree nodes; depth 3; 1 parallel branch; 0 GPU hours; USD 5 equivalent token-cost cap**. These are proposed policy values, not provider price facts or accepted defaults. No unlimited bound, agent-raised cap, per-branch reset or retry bypass. Aggregate all relevant invocations and reserve capacity before dispatch. Basis: §§23, 33, 41, 58, 77.

**Before selection:** Source/revision: freeze units, counter definitions, depth convention, shared-task accounting and policy hash. License/terms: provider prices, currency conversion and billing semantics are **to verify at intake**. Transitive dependencies: inventory accounting inputs; no new billing platform is implied. Security/data exposure: test concurrent reservations, retries, failed calls, unknown-cost calls and adversarial cap changes. Rollback: lower/disable future task profiles without reducing historical usage; stop/reconcile current tasks under TDG3-10. Unbounded or unavailable cost estimates block live dispatch.

**Dependent PRs:** PR3-03–04, 07, 09–11, 15–20, 22–23; PR3-21 injects overrun attempts.

**Owner question:** Do you approve the stated eleven pilot caps, including USD 5 and zero GPU hours?

### TDG3-10 — Termination and extensions

**Question:** When must execution stop, and how can a human extend it?

**Options:** (A) Stop at the first exhausted bound, with explicit human-approved new budget; (B) stop at exhaustion and require a new linked task for any continuation.

**Recommended option and required contract:** A. Also stop after **2 repeated failures** or **2 no-improvement iterations**, human stop, policy violation or defined success. Freeze improvement scoring and failure equivalence before running. Missing progress evidence cannot authorize unlimited continuation. Confidence alone is not scientific success. Cancel/reconcile active jobs, block further dispatch and retain failures, negative results and pruned branches. A new approved budget preserves original usage and termination history; terminal execution/Run material is not reopened or overwritten. Basis: §§24–25, 33, 49, 59–61, 71.

**Before selection:** Source/revision: approve stop predicates, continuation identity, cancellation deadlines and bounded in-flight overshoot per adapter before activation. License/terms: cancellation/billing guarantees are **to verify at intake**. Transitive dependencies: inspect every in-flight worker/provider cancellation path. Security/data exposure: prove rejected/expired extensions cannot restart tasks, agents cannot approve extensions, and UNKNOWN jobs reconcile before retry. Rollback: revoke continuation, terminate/reconcile workers and preserve monotonic accounting; do not erase original limits or scientific history.

**Dependent PRs:** PR3-04, 07, 09–11, 15, 17–23; PR3-19 supplies crash/stop reconciliation.

**Owner question:** Do you approve first-bound termination, two-failure/two-no-improvement stops and explicit human budget extensions?

### TDG3-11 — Schema and promotion allocation

**Question:** Which bounded records and PR owners implement promotion and runtime provenance?

**Options:** (A) Registry/pattern-based allocation with typed references and a staged migration plan; (B) pause affected work for an ADR if the existing patterns prove insufficient.

**Recommended option and required contract:** A; use B for a demonstrated gap, never a generic schema shortcut. Proposed allocation: PR3-01 task/step/input relations; PR3-02 AgentVersion, separate AgentAvailability, executions, immutable AgentPromotionRecord/typed outputs and fingerprint binding; PR3-03 invocations/policies plus routing/intake guards; PR3-04 budgets/checkpoints/termination; PR3-05 context/promotion validation; PR3-08 SemanticImpactAssessment; PR3-16 session/node/Run links; PR3-17 SearchDecisionRecord; PR3-19 operational outbox/inbox/leases. PR3-14 owns ReviewerContextBuilder; PR3-20 owns minimum SkillEvaluationRunner. These allocations supplement §79 and require pack approval.

Promotion record and canonical create/revise must commit in the **same Application transaction**. Formal promotion targets and canonical collections use concrete FKs/typed relation rows. No sole polymorphic locator, canonical-ID JSON array, scientific cascade delete, new top-level HarnessFingerprint/Skill/memory entity or mutable AgentVersion availability. Fingerprints are immutable values/manifests bound to executions; working memory uses ArtifactVersion roles. Freeze cross-PR FK layout before migrations; one owner/head, proposed serial order 01→02→04→03→16→08→17→19. Unresolved cycles require architecture review, never weak interim final constraints. Basis: Correction A1, A4, A10–A11; Registry §4; §§28, 70–71; Harness §85.2–85.4.

**Before selection:** Source/revision: freeze field ownership, typed targets, hash compatibility and staged migration contracts. License/terms: no new upstream admission; inherited persistence dependencies remain **to verify at intake** for selected revisions. Transitive dependencies: confirm reuse of the accepted DB/ArtifactStore stack. Security/data exposure: verify transactional promotion attribution, project consistency, immutability and RESTRICT constraints on real PostgreSQL. Rollback: require clean-install/upgrade evidence and data-preserving downgrade or explicit refusal when history would be lost; preserve accepted migrations and hashes.

**Dependent PRs:** PR3-00–05, 08, 11–20, 22–23; all consumers must follow the approved schema contracts.

**Owner question:** Do you approve the proposed PR ownership, atomic typed promotion and serial migration allocation?

### TDG3-12 — Skill/tool intake and versioning

**Question:** How do Skills, Plugins, Hooks, MCP tools and method references become executable?

**Options:** (A) Existing bounded registry, reviewed immutable executable revisions and deterministic policy exclusions; (B) add a third-party registry/runtime only after a separate boundary review and ADR where required.

**Recommended option and required contract:** A. Use RB-S01–RB-S12 and existing strategy/reference mechanisms. Skill routing must filter phase, authority, capabilities and data policy before model ranking. Keep reference-only libraries labeled references rather than executable locked dependencies. Pin production material when enabled and bind its resolved fingerprint to executions. No unreviewed install or same-execution weakening of AGENTS, Skills, policies, lock or required auditors. Changes require separate evaluation/release and a new governed execution. Basis: §§39–41; Harness §§85.3, 85.8; Harness specification §§5–7, 20–23.

**Before selection:** Source/revision: resolve authoritative sources, immutable commits/digests, scripts, instructions and approval scope, **to verify at intake**. License/terms: inspect each package, copied reference and remote service. Transitive dependencies: inventory scripts, hooks, MCP servers, images and nested installers. Security/data exposure: review tool permissions, prompt/tool injection, network/secrets access and project namespaces; tool descriptions confer no authority. Rollback: revoke routing/activation and restore an approved pinned package without rewriting historical execution fingerprints or trusting modified running sessions.

**Dependent PRs:** PR3-02–05, 08–10, 12–15, 17–23; PR3-03 owns enforcement and PR3-20 evaluates it.

**Owner question:** Do you approve reviewed immutable intake through the existing bounded Skill registry only?

### TDG3-13 — Evaluation and release thresholds

**Question:** Which measurements and predeclared thresholds establish Phase 3 acceptance?

**Options:** (A) Zero safety violations, all mandatory deterministic/golden checks passing, and fixture-specific quality/cost/recovery targets frozen before evaluation; (B) stricter deterministic-only rollout with live adapters disabled until those targets are approved.

**Recommended option and required contract:** A. Require zero direct-write, self-approval, closure, isolation, history-deletion and hard-budget violations. Every required deterministic safety check and all five §75 E2Es must pass, together with §82 and Harness §85.9; required blocked/skipped evidence is not PASS. Before PR3-20, freeze fixtures, seeds, repetitions, denominators and numeric targets for completion, promotion accuracy, hallucinated objects, invalid commands, unnecessary experiments, intervention, recovery, reproducibility and review defects. Cost must remain within TDG3-09; recovery deadlines and overshoot limits must be measurable under TDG3-10. These remaining quality/recovery numbers are **owner decisions pending**, not invented acceptance facts. No aggregate quality score can waive safety failure. Basis: §§42, 74–77, 81–82; Harness specification §20.

**Before selection:** Source/revision: hash fixtures/evaluation policy and bind results to exact runtime/model/Skill revisions; reject post-result threshold changes. License/terms: fixture/corpus and evaluator service rights are **to verify at intake**. Transitive dependencies: inventory evaluator tools and inherited live adapters. Security/data exposure: contain adversarial fixtures and test actual selected sandbox/adapters; fakes alone cannot prove isolation. Rollback: reject the release, retain failed evidence and restore approved runtime/Skill revisions without suppressing failed branches or rewriting science.

**Dependent PRs:** PR3-20–23; PR3-00–19 must expose the evidence required by their acceptance packs.

**Owner question:** Do you approve zero safety violations and predeclared fixture-specific quality, cost and recovery targets?

### TDG3-14 — Review and operational accountability

**Question:** Who reviews independently and owns migrations, security, budgets and incidents?

**Options:** (A) Separate reviewer execution with reconstructed evidence and named human operational owners; (B) an additional independent reviewer/model for higher-risk changes under the same human accountability.

**Recommended option and required contract:** A initially; use B when risk justifies it. Review uses authoritative specs, relevant canonical state, candidate/diff/artifacts and machine evidence, without author scratchpad or private reasoning. A separate reviewer execution is required by this proposed acceptance policy; a different model is optional. For this single-owner project, propose owner **eshine** as gate, budget and incident owner, retaining human accountability for migration and security. The director, **Claude Code acting under owner delegation**, is the independent reviewer and migration/security first reviewer, using a separate reviewer execution. The owner may override these assignments and designate stop/escalation coverage. Review does not confer approval authority or scientific truth. Findings use P0 BLOCKER/P1 MAJOR/P2 MINOR/P3 SUGGESTION and include location, evidence, violated rule, impact and action. Close P0/P1 before gate success. Basis: §§17, 65–66, 78, 80–82; Harness §85.5–85.6; AGENTS.md §10.

**Before selection:** Source/revision: identify reviewer execution/context manifests, owner roster, approved runbooks and gate evidence. License/terms: any reviewer provider/service remains **to verify at intake**. Transitive dependencies: inventory review tooling; a second model is not automatically trusted. Security/data exposure: verify least-privilege review access, no author scratchpad leakage, incident escalation and auditor denial of approval/direct writes. Rollback: owners can suspend dispatch, revoke credentials/Skills and reconcile jobs while preserving findings and scientific history; verify response coverage before unattended use.

**Dependent PRs:** PR3-00–23 for review/accountability; PR3-14 implements reviewer isolation, PR3-19 recovery, PR3-20–23 acceptance evidence.

**Owner question:** Do you accept eshine as gate/budget/incident owner and director Claude Code under owner delegation as independent reviewer and migration/security first reviewer, or override these assignments?

## Selection and activation gates

All fourteen rows remain **PENDING OWNER DECISION**. Record each answer, rationale, approver, date, exact design revision and dependent execution packs in TDG-3 ADRs before Phase 3 GO. A design selection establishes a role and boundary; enabling any external executable/service additionally requires its completed intake and relevant PR acceptance. Every selection must include source/revision, license/terms, transitive inventory, security/data-flow review and rollback evidence described above; inapplicable items require an explicit reason, never an assumed PASS.

TDG-3 selection cannot close Phase 2 gaps, weaken scientific invariants or substitute for per-PR authorization. Freeze unresolved numeric evaluation targets, sandbox resource limits and cancellation/overshoot bounds before their dependent PRs activate. A failed intake leaves that adapter disabled and returns the choice for review; it does not authorize additional infrastructure. At Phase 3 exit require the seven §82 artifacts and the final harness extension, then STOP pending separate Phase 4 GO.

Verification scope for this draft: documentation structure, local links, decision coverage and whitespace only. No implementation acceptance or gate success is claimed.

## Owner decision sheet

All answers pending; record owner/date/ADR revision on selection. This compact sheet covers the same fourteen decisions and grants no activation authority.

| ID | Proposed answer | Exact owner question |
|---|---|---|
| TDG3-01 | Phase 2 accepted; Phase 3 GO + PR3-00 only proposed | Do you grant explicit Phase 3 GO, and authorize (A) PR3-00 only (recommended), (B) no PR yet, or (C) another explicitly named first PR? |
| TDG3-02 | DEV_LOCAL; isolated CPU worker | Do you approve DEV_LOCAL with dedicated isolated CPU execution and no GPU or cloud credentials? |
| TDG3-03 | Constrained Docker; intake first | Do you approve a constrained Docker sandbox subject to host, license and containment intake? |
| TDG3-04 | Small native state machine | Do you approve native orchestration with no external agent runtime dependency initially? |
| TDG3-05 | PostgreSQL dispatch; no Redis | Do you approve PostgreSQL dispatch and leases with no Redis or separate broker? |
| TDG3-06 | One API-based primary (owner names provider); alternate deferred; fake retained; no subscription CLIs | Choose (A) API-based primary you name + alternate deferred (recommended), (B) primary + alternate, or (C) fake only for now? |
| TDG3-07 | One API-based profile you name; fixtures only; your API credentials outside workspaces; no subscription quota | Choose (A) one API-based profile you name with synthetic/test fixtures only (recommended), or (B) another named arrangement? |
| TDG3-08 | A1/A2; gated bounded A3 | Do you approve A1/A2 defaults with human freeze/release and separately authorized bounded A3? |
| TDG3-09 | Eleven stated pilot caps | Do you approve the stated eleven pilot caps, including USD 5 and zero GPU hours? |
| TDG3-10 | Hard stops; human extension | Do you approve first-bound termination, two-failure/two-no-improvement stops and explicit human budget extensions? |
| TDG3-11 | Typed atomic promotion; serial DDL | Do you approve the proposed PR ownership, atomic typed promotion and serial migration allocation? |
| TDG3-12 | Reviewed/pinned bounded registry | Do you approve reviewed immutable intake through the existing bounded Skill registry only? |
| TDG3-13 | Zero safety failures; frozen targets | Do you approve zero safety violations and predeclared fixture-specific quality, cost and recovery targets? |
| TDG3-14 | eshine ownership; director independent/first review; owner may override | Do you accept eshine as gate/budget/incident owner and director Claude Code under owner delegation as independent reviewer and migration/security first reviewer, or override these assignments? |
