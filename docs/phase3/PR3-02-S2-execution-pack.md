# PR3-02-S2 execution pack — planning only

Planning baseline: `d744074cfc0cf2fd1fbc6d155bea1353b6078541` (PR #12 merge), inspected 2026-10-25.
The owner authorized this document only. Implementation, contract changes, code, migrations and tests are not authorized. Only this file may be written; no commit, push or branch creation.
Checkout observation: HEAD matches the requested base; the pre-existing branch is `docs-pr302s2-pack`. Local `origin/main` is stale at `919c220f184242198d2cf4edb46ab9c163744a39`; no local `main` ref exists. No refs were changed.
Brief provenance: `docs/phase3/PR3-02-S2-authorization-brief.md` was absent from this working tree and the locally available HEAD, `origin/main` and `codex/phase3-wave3-base` trees. **No S2 brief was used.** No other lane or remote state was assumed.
Authority read order: `AGENTS.md`, applicable architecture 01 → 02 → 03 → 08 → Phase 3 specification 06 → Harness 09, then ADR-0023, PR3-02 draft, S1 evidence and prerequisite acceptance records. Structure follows `docs/phase3/PR3-03-implementation-plan.md:15–117,655–767`.
Every proposed decomposition, file allocation, test node and progression gate below is labeled **INFERRED**; it is a planning proposal, not an added contract. Source citations refer to this baseline. Historical test counts are not results of this planning turn.

## 1. Verdict and evidence

**INFERRED verdict: planning pack ready for owner review; not a frozen, implementation-ready contract.** Accepted prerequisites supply reusable components but do not themselves define S2 activation. The draft explicitly defers the enabling contract and exact schema/hash details to the later pack (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:425–431`). Open questions are isolated in §1.3; no answers are invented here.

### 1.1 Scope and non-goals

- S2 owns `create_agent_execution`, `transition_agent_execution`, `promote_agent_candidate`, their DTOs/queries, four execution/promotion tables, typed receipt extensions and execution harness binding. S1 identity/version/availability contracts remain preserved (`docs/architecture/adr/ADR-0023-pr3-02-agent-identity-versions-executions.md:11–16`; `docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:34–48`).
- The four tables are `agent_execution_instances`, `agent_execution_events`, `agent_promotion_records` and `agent_promotion_outputs`; extend existing `agent_command_receipts`, rather than add a second receipt system (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:35,203–207`).
- First promotion targets are the two existing B02 question/hypothesis DRAFT families, composed inside one UoW, with producer identity separate from promoter identity (`docs/architecture/adr/ADR-0023-pr3-02-agent-identity-versions-executions.md:14`; `docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:235–252`).
- CREATED intent requires a sealed PLANNING task and cannot advance task/step state through the closed gate. Positive running and promotion require gateway/policy integration; disabled transitions are not positive coverage (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:40–48,77–82,218–224,425`).
- Exclude scheduler, lease, worker, provider, sandbox, working-memory engine, new gateway/policy implementation, budget/checkpoint schema and scientific ownership changes; Agent success does not assert scientific Run success (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:70–75`). **INFERRED:** integrate only explicitly approved extensions to the delivered gateway/safety boundaries after Q1–Q3 are resolved; do not rebuild them.
- Exclude new fingerprint/model-policy entities, generic target references, autonomous freeze, new public ErrorCodes and broader promotion families (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:100–102,250–266,354–355,424–430`).
- Preserve historical IDs, hashes, receipts and provenance; never backfill invented executions, fingerprints or policies (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:103–105,237–238,383,410`). **INFERRED:** PR3-05 saving, D1/D2, provider disclosure, API/CLI expansion and later PRs remain outside this proposed slice unless separately scoped; PR3-04 acceptance does not cover them (`docs/phase3/PR3-04-acceptance.md:35–38`).

### 1.2 Dependencies and delivered evidence

| Dependency | File:line evidence | Consequence for planning |
| --- | --- | --- |
| Approved decisions, separate authorization | `docs/architecture/adr/ADR-0023-pr3-02-agent-identity-versions-executions.md:3–16` | D302-03..05 approve staged execution, atomic targets and the S2 table/lock allocation; they do not authorize this implementation. |
| S1 locking amendment | `docs/architecture/adr/ADR-0023-pr3-02-agent-identity-versions-executions.md:18–27` | Preserve S1 enrollment's SHARE ROW EXCLUSIVE prefix and version commands' eight-table inventory; do not apply that amendment to S2 by inference. |
| S1 delivered provenance and integration | `docs/phase3/PR3-02-S1-evidence.md:22–44,123–141,538–541` | Identity, versions, manifests and Application-only B02 Agent evidence exist. Final integration records 13,350 passed / 0 failed / 66 skipped; production verifier intake remains pending, not proven by test adapters. |
| PR3-03 final acceptance | `docs/phase3/PR3-03-evidence.md:7331–7349` | Owner ACCEPTED after PR #8; final code-head CI runs succeeded. Earlier local 14,179/66/0 counts predate later fixes and are not S2 evidence. |
| PR3-04 acceptance | `docs/phase3/PR3-04-acceptance.md:3–5,23–38` | Owner acceptance records a green-head-CI condition, run IDs on `2914208`, waiver of two director reviews, and no open P0/P1. Exact CI counts are referenced externally, not supplied here; do not invent them or extend the waiver to S2. |
| Delivered gate remains closed | `docs/phase3/PR3-03-contract-freeze.md:58–66`; `docs/phase3/PR3-04-contract-freeze.md:30–39,611–618` | Gateway is CONTRACT_FAKE; task/step execution is still disabled even with policies and approvals. **INFERRED:** acceptance is necessary but insufficient to choose S2 activation semantics. |
| Current migration chain | `migrations/versions/0079_agent_identity_versions.py:9–10`; `migrations/versions/0080_capability_gateway.py:5–6,166` | Delivered parent chain is 0078 → 0079 → 0080; invocation mode CHECK admits only CONTRACT_FAKE. No S2 migration number is reserved (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:14–17,47–48`). |
| Existing command and read boundary | `src/researchbase/agent_runtime/application/agent_versions.py:143–185,342,448–462`; `src/researchbase/persistence/uow.py:637–674,1347–1354` | Reusable S1 service, READ COMMITTED write setup, formal-read snapshot and startup-timeout factory. **INFERRED:** extend via ports, preserving existing operations. |
| Existing manifest value | `src/researchbase/agent_runtime/domain/harness_manifest.py:26–81`; `tests/unit/phase3/test_harness_manifest.py:35–68` | Closed version-1 value, ordered entries and value digest already exist. **INFERRED:** reuse them; separately freeze execution binding/retained-byte validation in Q4. |
| Gateway accounting and locks | `docs/phase3/PR3-03-contract-freeze.md:1661–1705,1770–1796`; `src/researchbase/persistence/capability_gateway_repository.py:93–131` | Delivered order places task key before Agent actor key; accounting is an identity-trusted fake seam. **INFERRED:** do not call it as an S2 public execution authorizer or concatenate lock recipes. |
| B02 owning writes and byte reads | `src/researchbase/application/strategy_candidate_promotion.py:366–422,560–618,660–758`; `src/researchbase/persistence/strategy_candidate_promotion_repository.py:46–53` | Public wrappers open/commit UoW; `_capture` opens retained bytes; repository acquires its own prefix. **INFERRED:** extract an internal composition seam and byte preflight, preserving public behavior. |
| PR3-05 read-only guard | `src/researchbase/agent_runtime/application/promotion_context.py:98–103`; `tests/integration/phase3/test_pr3_05_promotion_validation.py:21–59` | Existing validator explicitly reports unverified S2 producer provenance. **INFERRED:** it is neither promotion authorization nor proof that S2 provenance exists; any integration needs Q7 disposition. |

### 1.3 Separate owner-question list

All questions below are **INFERRED unresolved specification needs**. They require disposition before dependent implementation, not before completing this document. Already approved D302 decisions are not being reopened.

1. **Q1 — Exact execution activation:** Which task/step operations, states, autonomy levels and trusted consumer entry are authorized in S2, and how do policy, checkpoint, budget and stop rules admit/deny each execution transition? Define the concrete invocation→execution FK/mode addition and compatibility for old CONTRACT_FAKE rows. The draft delegates enabling to the later pack (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:77–82,163–165,425`); delivered packs keep execution disabled (`docs/phase3/PR3-03-contract-freeze.md:29,58–66`; `docs/phase3/PR3-04-contract-freeze.md:611–618`). No mode name, task state or activation switch is selected here.
2. **Q2 — Composed lock/receipt protocol:** How must S2's actor → task → version → execution keys and 23-table prefix compose with gateway task → actor → version ordering, safety rows, B02 keys and their receipt/task-revision effects? Freeze exact added waits/rechecks without changing accepted Phase 2 writer order (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:295–341`; `docs/phase3/PR3-03-contract-freeze.md:1664–1705,1778–1787`). This is a composition question, not a claim that standalone existing commands necessarily deadlock.
3. **Q3 — Exact persistence contract:** Approve columns, nullability/bounds, checks, indexes, composite keys, guard/function/trigger inventory, receipt result combinations and diagnostic mappings for the four tables, receipt extensions and Q1 gateway linkage. Include initial event and terminal completeness rules. The draft provides minimum material and expressly requires exact review before DDL authorization (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:193–207,226–233,427`). No SQL definitions or additional schema admissions are invented here.
4. **Q4 — Exact material and vectors:** Freeze the three command payloads/literal vectors, execution input/output digest material, result-manifest schema, summary/error bounds, harness byte-digest versus manifest-value-digest rules, and candidate selector/digest serialization. Preserve existing S1/B02/scientific domains (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:163–174,218–224,256–266,373–383`). Existing manifest value hashing alone does not specify all these execution bindings (`src/researchbase/agent_runtime/domain/harness_manifest.py:74–81`).
5. **Q5 — Transition and promotion authority:** Define the authorized HUMAN controller predicate, per-transition authority, behavior of in-flight attempts after availability/credential changes, exact AGENT_POLICY snapshot basis and replay result/event projection. Preserve entitled history, A0 denial and reserved AUTOMATIC_UNDER_POLICY (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:94–105,164–174,244–252,335–350,385–390`). Do not infer that a Human's confirmation or a fake-consumer token grants Agent execution authority.
6. **Q6 — Producer/capture attribution:** Specify the verifiable connection between the producing execution, B02 capture and selected candidate, owning-command identity, duplicate/replay identities and prevention of a new standalone attribution bypass. Equality with the captured result artifact and separate promoter identity are fixed, but cannot alone justify guessing the producer (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:165,205–207,235–252,385–390`). Preserve legacy B02 history and public semantics.
7. **Q7 — PR3-05 read-only compatibility:** Should the existing context validator remain explicitly S2-unverified, or receive a separately bounded exact-producer read extension? Its current behavior is `S2_PRODUCER_PROVENANCE_UNVERIFIED` (`src/researchbase/agent_runtime/application/promotion_context.py:98–103`). Neither choice authorizes PR3-05 saving/D1/D2 (`docs/phase3/PR3-04-acceptance.md:35–38`).
8. **Q8 — Authority record and freeze/review:** Is a missing S2 brief intended as additional authority, and what review/freeze requirements apply to the resolved S2 contract before a separate implementation authorization? ADR-0023 requires S2's own authorization; its two-review statement explicitly names S1 (`docs/architecture/adr/ADR-0023-pr3-02-agent-identity-versions-executions.md:3–5`). Attach the prerequisite acceptance evidence already referenced in §1.2; do not treat this planning authorization or PR3-04's waiver as S2 implementation approval.

## 2. Rules shared by every sub-task

The rules below restate approved source obligations; §1.3 identifies missing refinements. Future filenames and test organization are **INFERRED**.

- All command DTOs are immutable/closed; normalize NFC, validate exact IDs/digests and aware UTC. Caller is injected; result hashes are server-derived. Queries use current project read entitlement, exact IDs, stable ID order and 1–100 after-ID pages (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:147–180`).
- Execution binding is immutable: project, task/optional same-task step, version/Agent, verified inputs and harness. Terminal material and history are immutable. Version availability controls starts, not historical erasure (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:91–105`).
- Lifecycle: CREATED → RUNNING/CANCELLED; RUNNING → WAITING_TOOL/WAITING_HUMAN/SUCCEEDED/FAILED/CANCELLED; either WAITING state → RUNNING/FAILED/CANCELLED. First RUNNING sets start once; terminal sets finish once; pre-start cancellation has no start. FAILED needs existing ErrorCode/reason; SUCCEEDED needs frozen result manifest/output digest; retry creates a new execution (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:182–189`). No edge is implementation-authorized until Q1/Q5 are resolved.
- Use PostgreSQL 18, concrete RESTRICT FKs, UUIDv7, positive revisions and scoped indexes. No new execution-input table: sealed task/step typed rows remain the FK source; digest ordering is owner/type/exact ID, preserving saved hash/scheme including NULL (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:193–196,218–233`). Exact material remains Q3/Q4.
- Each write is one synchronous READ COMMITTED UoW with startup lock_timeout=10s / statement_timeout=30s. The first Application SQL takes the following ordered 23-table SHARE inventory, even for empty inputs/replay (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:268–272,295–310`):

```text
actor_subject_bindings, actors, artifact_versions, artifacts, claim_versions,
claims, hypothesis_versions, hypotheses, literature_source_project_links,
literature_sources, manuscript_versions, project_membership_events,
project_memberships, project_role_assignments, projects, publications,
research_question_versions, research_questions, source_versions,
strategy_candidate_captures, strategy_candidate_sources,
strategy_hypothesis_admissions, strategy_question_admissions
```

- Then project lock → `pr302:command` → Agent actor → task → version → execution → applicable B02 owning key; row order is actors by ID, task, steps by ID, availability, execution, B02 admissions by ID. Use transaction-scoped advisory locks; no trigger acquires advisory locks after row locks. Skip inapplicable keys; enrollment keys do not belong to S2 operations (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:226–233,312–333`). Q2 must resolve integration with delivered protocols before coding.
- After blocking waits re-read authority, credentials, scope, availability, revision and material using advancing DB time. Entitled exact replay precedes write/state/CAS checks. Verify retained bytes before the write transaction and recheck frozen DB bindings inside; no ArtifactStore/model/network/process I/O under locks (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:335–345`).
- Formal reads/explicit reconciliation use one REPEATABLE READ READ ONLY snapshot, autoflush off, no locks/writes/repair/second session. Replay returns original results/events/revisions after current read entitlement; changed material conflicts. Retry only 40001/40P01, at most three fresh whole transactions with stable IDs/material; never automatically retry 55P03/57014. Uncertain commit reconciles the original identity (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:347–350,385–397`).
- Promotion writes B02 DRAFT identity/version/admission, promotion, typed output and receipt in one UoW, forces deferred checks and commits once; rollback removes both sides. Initial output is exactly one concrete question-version XOR hypothesis-version; DRAFT scientific hash remains NULL. Human modes retain producer attribution; Agent mode requires resolved policy basis; A0 cannot promote (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:205–207,235–252`).
- **INFERRED stop rule G:** quote conflicting authority and delivered `file:line`, identify the blocked check and owner question; do not repair an unresolved contract through code. Record independent planning work and remaining dependencies. Never weaken guards, frozen vectors, governing Harness or historical migration bytes to pass a check (repository `AGENTS.md:119–123,127–155`).
- **INFERRED evidence rule:** exact commands, stdout/stderr, exit codes and observed collected/passed/failed/skipped counts accompany each future handoff. Proposed cases are not observed counts; required skips/zero selection do not pass. External check loop owns the full suite (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:401–419,432`).

**INFERRED common future gate C — NOT RUN during this planning task:**

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
git diff --check HEAD
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run alembic heads
```

**INFERRED:** require each exit 0 and exactly the separately approved next head, parented to the then-current head. No new number is fixed here. SQL constants follow existing 100-character lint rules without exemptions; use parameterized repository SQL. Follow repository disposable PostgreSQL plumbing, never an ambient database (`tests/disposable_postgres.py:1–53`; `tests/integration/phase3/agent_fixtures.py:100`).

## 3. Sub-tasks

**INFERRED sequencing and file/test allocations throughout this section. All implementation steps are NOT AUTHORIZED / NOT RUN.** Named new modules and nodes are proposals, not delivered identifiers or additional contract semantics. Node IDs in §3.8 are the minimum behavior checklist; parameterized cases expand it after owner dispositions.

### S0 — Resolve and freeze the bounded execution contract

**Goal/dependencies:** resolve Q1–Q8 against §1.2 evidence; freeze exact schema, literals, predicates, linkage, lock composition and diagnostics required before implementation (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:383,425–432`).
**Files:** this pack in the current task; any later authority amendments require separate scope. Do not edit ADR/draft/freeze records now.
**Verification/completion:** source-to-contract-to-node checklist covers every disposition; required independent reviews and separate implementation authorization are recorded. No executable verification is claimed.
**Two-round estimate/cut:** one evidence/disposition pass, one review pass; owner response time is unbounded. Cut duplicated prose only.
**Risk/stop:** treating accepted fake groundwork as a running Agent contract; G blocks S1–S7 until the dependent contract is frozen.

### S1 — Forward migration, receipt extensions and compile gate

**Goal/dependencies:** implement only the approved four tables, typed receipt additions and forward guard replacements after S0. Preserve one head, accepted migrations and prior results; prove clean/populated upgrade and downgrade refusal (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:35,47–48,193–207,226–233,410,427`). Q1–Q3 determine any gateway/task guard delta.
**Files:** proposed `migrations/versions/<approved_next_revision>.py`, `src/researchbase/persistence/models.py`; proposed `tests/integration/phase3/test_pr3_02_s2_schema.py`, `test_pr3_02_s2_guards.py`, `test_pr3_02_s2_migration.py`; mechanical current-head consumers only as inventoried in Appendix H.
**Node-level tests:** M1–M3, D1–D4 (§3.8). Compile all new/replaced functions on an empty disposable PG18 database; validate normal-role inserts and refusals, not only text inventories.
**Verification/completion:** C plus §4 schema/guard/migration command, exit 0 and real counts; exactly approved schema delta, sole head and unchanged old rows/hashes/receipt results.
**Two-round estimate/cut:** one DDL/compile pass, one behavioral verification pass after exact SQL is approved; cut no constraints or cases.
**Risk/stop:** deferred completeness scans duplicated per child, partial receipts or loss of old operation cases. G applies; no SQL authored from minimum-table prose alone.

### S2 — Closed values, material and harness binding

**Goal/dependencies:** implement execution/promotion values and command/result/query DTOs; preserve S1 values and owning hashes; preflight frozen harness/result bytes with Q4's approved formats (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:147–189,218–224,256–266,373–383`). Depends on S0 and S1's frozen field inventory.
**Files:** proposed `src/researchbase/agent_runtime/domain/agent_execution.py`, `agent_promotion.py`, `src/researchbase/agent_runtime/application/execution_contracts.py`; narrowly extend `agent_contracts.py` where receipt unions require it; reuse `domain/harness_manifest.py:26–81`. Proposed unit files `test_agent_execution_contracts.py`, `test_agent_promotion_contracts.py` and `execution_vectors.py` under `tests/unit/phase3/`.
**Node-level tests:** U1–U4; existing `tests/unit/phase3/test_agent_version_contracts.py::test_literal_vectors` and `tests/unit/phase3/test_harness_manifest.py::test_closed_and_byte_hash_distinction` remain regression anchors.
**Verification/completion:** C and focused unit command in §4; independently specified literal vectors match exactly, unknown fields/literals fail, no existing vector changes.
**Two-round estimate/cut:** values/vectors then negative/material tests; no parser framework or schema generalization.
**Risk/stop:** confusing retained-byte digest, manifest value digest and scientific hash. G applies; unresolved Q4 blocks value/hash implementation.

### S3 — Ports, locks, storage and snapshot reads

**Goal/dependencies:** implement typed repository/UoW boundaries using the exact reviewed S2 recipe and formal-read path; prove per-wait freshness and receipt-first replay (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:295–350,385–397`). Depends on S1/S2 and Q2 disposition; reuse UoW setup at `src/researchbase/persistence/uow.py:637–674`.
**Files:** proposed `src/researchbase/agent_runtime/ports/execution_repository.py`, `src/researchbase/persistence/agent_execution_repository.py`; narrowly extend `ports/agent_repository.py`, `persistence/agent_version_repository.py`, `persistence/uow.py`. Gateway/safety port/repository changes only where Q1/Q2 approve them. Proposed `tests/unit/phase3/test_agent_execution_repository.py`.
**Node-level tests:** L1–L3 plus PG R1/R2. Record first Application SQL, all key/row waits and read SQL; fakes alone cannot prove database concurrency.
**Verification/completion:** C, focused repository nodes and PG concurrency command in §4. No locks after protected row locks except those explicitly in the frozen recipe; no nested UoW or second read snapshot.
**Two-round estimate/cut:** storage/lock implementation then traces/races; reuse existing readers instead of generic repository machinery.
**Risk/stop:** reversing actor/task order or re-entering a public gateway/B02 command; G applies, and Q2 is a predecessor gate.

### S4 — Execution creation and gated lifecycle

**Goal/dependencies:** create immutable binding/CREATED history, then the approved lifecycle with real policy/gateway integration; retain failures and partial results (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:91–105,163–169,182–189,218–233`). Requires S1–S3, Q1/Q5 and accepted prerequisite behavior.
**Files:** proposed `src/researchbase/agent_runtime/application/agent_executions.py`; narrow extensions to `application/capability_gateway.py`, `gateway_contracts.py`, `task_safety.py`, `research_task.py` and matching ports only where Q1/Q2 explicitly require them. Proposed `tests/unit/phase3/test_agent_executions.py`, `tests/integration/phase3/test_pr3_02_s2_execution.py`.
**Node-level tests:** E1–E4, U2, R1/R2. Include Human controller and bound producing Agent paths, wrong Agent denial, policy/stop/checkpoint/availability denials and positive authorized SUCCEEDED evidence.
**Verification/completion:** C and execution nodes in §4; timestamps/revisions/events match the contract and rollback leaves no partial execution history. Positive success must use the authorized integration, never forged SQL or a gate bypass (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:77–82,408–410`).
**Two-round estimate/cut:** creation/lifecycle then integration/races; estimate depends on Q1's final scope. Cut real providers and orchestration, never required positive execution coverage.
**Risk/stop:** toggling a boolean instead of defining admission, or treating execution success as scientific evidence. G applies.

### S5 — Atomic B02 promotion composition

**Goal/dependencies:** extract reusable owning validation/DRAFT writes into an internal already-open-UoW seam; verify capture bytes before S2 locks and revalidate DB bindings under locks. Preserve public signatures, B02 replay/duplicates and original hash domains (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:235–252,343–345,385–390`). Requires successful S4 execution plus Q5/Q6.
**Files:** proposed `src/researchbase/agent_runtime/application/agent_promotions.py`; narrow changes to `src/researchbase/application/strategy_candidate_promotion.py`, owning repository/port and S2 repository. Proposed `tests/unit/phase3/test_agent_promotions.py`, `tests/integration/phase3/test_pr3_02_s2_promotion.py`.
**Node-level tests:** P1–P4, D3, R2/R3; preserve existing Application-only Agent/B03 denial node `tests/integration/phase3/test_pr3_02_s1_b02_agent.py::test_positive_application_only_agent_g2_and_b03_denial` (`tests/integration/phase3/test_pr3_02_s1_b02_agent.py:31`).
**Verification/completion:** C and promotion/B02 regressions in §4. Both DRAFT families commit owning admission + promotion + one typed output + receipt together; failure injection after each write stage leaves neither side. Producer/promoter remain distinct (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:98–102,205–207,244–252`).
**Two-round estimate/cut:** seam extraction then positive/negative/rollback evidence. Cut additional target families, UI and convenience attach routes.
**Risk/stop:** nested commit or ArtifactStore I/O inherited from B02 `_write`/`_capture` (`src/researchbase/application/strategy_candidate_promotion.py:404,605–608,758`). G applies; extraction is not permission to rewrite B02's external contract.

### S6 — Queries, historical replay and bounded compatibility

**Goal/dependencies:** deliver `get_agent_execution`, `list_task_executions`, `get_agent_promotion`, `list_execution_promotions` and authorized receipt reconciliation with original IDs/events/revisions (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:167–180,347–350,385–397`). Requires S3–S5 and Q5/Q7.
**Files:** S2 service/repository/contract files above; proposed `tests/integration/phase3/test_pr3_02_s2_replay.py`. PR3-05 `application/promotion_context.py` and its tests only if Q7 explicitly scopes a read extension; otherwise preserve current behavior. No transport route inventory change is selected by this plan.
**Node-level tests:** R3–R5, U4. Cover stale expected revisions, archive/retirement, revoked read entitlement, changed material, wrong-project disclosure, lost responses and uncertain commits.
**Verification/completion:** C plus replay nodes; read traces show one coherent lock-free snapshot and no repair/duplicate output. Historical result material is distinct from current projections (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:173–180,347–350,385–390`).
**Two-round estimate/cut:** projections/reconciliation then isolation/failure checks; cut optional transport additions, not entitlement or saved-result fidelity.
**Risk/stop:** returning current state as the original result, or silently changing PR3-05's public verdict. G applies.

### S7 — Complete focused evidence and independent handoff

**Goal/dependencies:** map every approved obligation to passing nodes, carry exact evidence and unresolved dispositions; do not claim acceptance with missing required evidence or open P0/P1 (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:399–419,432`). Requires all prior gates.
**Files:** proposed `tests/architecture/test_pr3_02_s2_boundaries.py`, `tests/integration/phase3/execution_fixtures.py`, remaining S2 test files in §3.8 and future `docs/phase3/PR3-02-S2-evidence.md`. These are future allocations only; this task writes none of them.
**Node-level tests:** all §3.8 rows plus affected historical nodes. Enroll/resolve Agents through Application commands; build captures, policies and artifacts through owning boundaries, using isolated fixtures (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:138–143,407–410`).
**Verification/completion:** all focused §4 commands and C exit 0 with actual counts, PostgreSQL version/role, migration manifests, raw lock/timestamp observations, effect counts and vector results. Attach external-loop full-suite evidence when supplied; absent evidence stays PENDING. No full-suite launch by implementation agent (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:412–419`).
**Two-round estimate/cut:** complete matrix then focused reruns/evidence; CI/review latency excluded. Hand off uncovered nodes rather than deleting acceptance obligations.
**Risk/stop:** manufactured positive evidence, sleeps mistaken for lock observations, ignored required skips or premature gate success. G applies; stop after separately accepted S2 evidence.

### 3.8 Node-level test inventory

**INFERRED proposed node IDs, all absent/not run at planning time.** Unit paths begin `tests/unit/phase3/`; PG paths begin `tests/integration/phase3/`. Each row names behavior, not a chosen answer to an owner question. Freeze parameter sets after Q1–Q7 dispositions.

| ID | Proposed node ID | Required observation / source |
| --- | --- | --- |
| U1 | `test_agent_execution_contracts.py::test_closed_commands_and_literal_vectors` | All three commands, explicit null/default material, NFC/order/duplicates; Q4 literals (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:147–156,373–383`). |
| U2 | `test_agent_execution_contracts.py::test_execution_transition_matrix` | Every allowed/denied pair and time/error/result requirements (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:182–189`). |
| U3 | `test_agent_execution_contracts.py::test_binding_digests_and_harness_pins` | Task+step ordering, hash/scheme NULL, changed/unresolved pins and retained-byte mismatch (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:218–224,256–266`). |
| U4 | `test_agent_promotion_contracts.py::test_closed_promotion_and_query_values` | Exact selector/owning material, no caller producer/hash injection, immutable safe DTOs and page bounds (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:153–180,240–252`). |
| L1 | `test_agent_execution_repository.py::test_ordered_s2_prefix_and_keys` | First 23-table SHARE and exact approved composed key/row order, including replay (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:268–272,295–341`); Q2. |
| L2 | `test_agent_execution_repository.py::test_fresh_checks_after_each_wait` | Advancing time and entitlement/material rechecks before writes, no I/O under locks (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:333–345`). |
| L3 | `test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot` | No locks/autoflush/writes/second session (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:347–350`). |
| M1 | `test_pr3_02_s2_migration.py::test_empty_upgrade_and_single_head` | Compile approved DDL/functions, exact delta, one head (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:47–48,410,427`). |
| M2 | `test_pr3_02_s2_migration.py::test_populated_upgrade_preserves_history` | Compare old IDs/hashes/trace and task/safety/S1/gateway saved results, no fabricated execution (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:103–105,410`). |
| M3 | `test_pr3_02_s2_migration.py::test_downgrade_refuses_before_change` | Empty/populated data/catalog/revision unchanged after refusal (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:410`). |
| D1 | `test_pr3_02_s2_schema.py::test_exact_schema_and_scoped_foreign_keys` | Q3 inventory; wrong task/step/project/actor/artifact reject (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:193–207,231,408`). |
| D2 | `test_pr3_02_s2_guards.py::test_normal_role_rejects_partial_or_mutable_history` | No-op/update/delete/late append, event/receipt/revision completeness and approved guard firing behavior (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:226–233`); Q3 defines counts. |
| D3 | `test_pr3_02_s2_schema.py::test_promotion_output_xor_and_unique_target` | Exactly one typed output, no both/neither/duplicate target or non-NULL invented DRAFT hash (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:205–207,244–246`). |
| D4 | `test_pr3_02_s2_schema.py::test_python_postgresql_material_parity` | Independent Q4 literal material and stored digests; do not copy expected values from implementation (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:373–383,406`). |
| E1 | `test_pr3_02_s2_execution.py::test_created_intent_and_immutable_binding` | Sealed PLANNING admission, same-Agent caller, initial event, no start/task advance (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:163,185–186,218–233`). |
| E2 | `test_pr3_02_s2_execution.py::test_authorized_success_through_gateway_and_policies` | Positive Application-only RUNNING→SUCCEEDED; no fixture bypass, exact result/output provenance (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:40–44,77–82,187`); Q1/Q5. |
| E3 | `test_pr3_02_s2_execution.py::test_lifecycle_denials_and_partial_results` | Wait/fail/cancel/terminal cases, policy/authority/availability denials, partial trace retention and retry new ID (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:94–97,164,182–189`); Q1/Q5. |
| E4 | `test_pr3_02_s2_execution.py::test_execution_failure_rolls_back_all_history` | Inject failure across writes/checks/commit; no partial records (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:226–233,339–341`). |
| P1 | `test_pr3_02_s2_promotion.py::test_both_draft_families_preserve_producer_and_promoter` | Human and eligible Agent promotion, exact capture/result, one typed output, NULL DRAFT hash (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:235–249`). |
| P2 | `test_pr3_02_s2_promotion.py::test_failure_on_either_side_rolls_back_both` | Every owning/admission/promotion/output/receipt failure leaves neither side; single commit (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:244–246,408`). |
| P3 | `test_pr3_02_s2_promotion.py::test_provenance_policy_and_scope_denials` | Non-SUCCEEDED, wrong capture/artifact/selector/producer/source/project; A0, missing policy and reserved mode (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:165,235–252`); Q5/Q6. |
| P4 | `test_pr3_02_s2_promotion.py::test_existing_b02_replay_and_duplicate_semantics` | Standalone behavior preserved, no S2 attribution bypass or retrospective attachment (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:103–105,237–252,385–390`). |
| R1 | `test_pr3_02_s2_concurrency.py::test_observed_wait_rechecks_expiry_and_revocation` | Actual first/key/row waits versus credential, membership, availability and source-link changes; denied command leaves zero protected effects (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:333–341,409`). |
| R2 | `test_pr3_02_s2_concurrency.py::test_promotion_upgrade_and_shared_gateway_races` | Same candidate/key/CAS and cross-protocol waits; coherent winner or sanitized bounded failure, never partial history (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:305–310,392–397,409`); Q2. |
| R3 | `test_pr3_02_s2_replay.py::test_saved_results_after_loss_and_uncertain_commit` | Same IDs/material, no duplicate effects; 40001/40P01 up to three attempts, no timeout retry (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:385–397`). |
| R4 | `test_pr3_02_s2_replay.py::test_current_entitlement_precedes_history_disclosure` | Retired/archived/stale revision reads versus revoked/wrong-caller denial and changed-hash conflict (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:335–350,385–390`). |
| R5 | `test_pr3_02_s2_replay.py::test_queries_are_coherent_bounded_snapshots` | Ordered pages/events, safe DTOs, concurrent writer cannot split the snapshot (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:167–180,347–350`). |
| A1 | `tests/architecture/test_pr3_02_s2_boundaries.py::test_common_application_boundary_and_typed_provenance` | Human/Agent parity; no runtime ORM/vendor dependency, JSON primary refs, fingerprint entity or direct scientific writes (`docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md:100–102,147–151,193–196,256–257,406`). |

## 4. Exact order and progression gates

**INFERRED:** S0 → S1 → S2 → S3 → S4 → S5 → S6 → S7 → external check loop and required independent review → owner acceptance → STOP. No downstream implementation starts without its predecessor evidence; planning completion does not pass S0's implementation gate.

**INFERRED future focused commands**, after authorization and creation of the proposed files. All are NOT RUN here. Record actual counts; no required skip or zero selection is acceptance. Configure `RB_TEST_ADMIN_URL` explicitly for local disposable PG18; fixture-controlled `DATABASE_URL` must name that disposable database. Follow existing plumbing rather than printing credentials (`tests/disposable_postgres.py:1–53`; `tests/integration/phase3/agent_fixtures.py:100`).

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
uv run pytest -o addopts='' -ra tests/unit/phase3/test_agent_execution_contracts.py tests/unit/phase3/test_agent_promotion_contracts.py tests/unit/phase3/test_agent_execution_repository.py tests/unit/phase3/test_agent_executions.py tests/unit/phase3/test_agent_promotions.py
uv run pytest -o addopts='' -ra tests/unit/phase3
uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_02_s2_schema.py tests/integration/phase3/test_pr3_02_s2_guards.py tests/integration/phase3/test_pr3_02_s2_migration.py
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_02_s2_execution.py tests/integration/phase3/test_pr3_02_s2_promotion.py
uv run pytest -o addopts='' -ra -s tests/integration/phase3/test_pr3_02_s2_concurrency.py tests/integration/phase3/test_pr3_02_s2_replay.py
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_01_*.py tests/integration/phase3/test_pr3_02_s1_*.py tests/integration/phase3/test_pr3_03_*.py tests/integration/phase3/test_pr3_04_*.py
uv run pytest -o addopts='' -ra tests/integration/phase2/test_b02_*.py tests/integration/phase2/test_b03_*.py
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_05_promotion_validation.py
```

**INFERRED evidence gate:** preserve raw outputs inside repository-local ignored temporary storage during future implementation; record migration parent/head, DB version/role, frozen-row and receipt comparisons, literal vector IDs, per-stage rollback counts and actual DB-observed waits. For expiry races record transaction/wait before expiry and acquisition/check after expiry, with a distinct check after each further wait (`docs/architecture/02_Final_Architecture_Correction_Addendum_v1.0.md:418–420`). Repeat only affected checks after fixes. Never launch the full suite; incorporate the external loop's exact commands/counts once supplied.

**INFERRED acceptance gate:** no open P0/P1, every approved case mapped to evidence, prerequisite acceptance reconciled, no unresolved contract question affecting shipped behavior. Missing CI/review stays PENDING. Do not claim provider readiness, PR3-05 saving, broader promotion or Phase 3 exit from S2 evidence.

## Appendix H — Mechanical head maintenance and compatibility risks

**INFERRED future inventory only:** derive the exact affected paths from the authorized diff, starting with `.github/workflows/ci.yml:66`, `tests/unit/test_ci_migration_head.py:12`, `tests/integration/phase3/test_pr3_02_s1_migration.py:55–56` and the prior inventory at `docs/phase3/PR3-03-implementation-plan.md:675–739`. Update active head assertions only; retain historical revision targets and byte/hash pins. Keep S1's explicit 0079 absence fixture (`tests/integration/phase3/test_pr3_02_s1_migration.py:15–32`) and gateway's historical 0079→0080 coverage (`tests/integration/phase3/test_pr3_03_migration.py:57–82,177`).

**INFERRED:** additions to old files that forbid all execution/promotion fields need narrowly reviewed S2 allowances, not removal of the guards (`tests/architecture/test_pr3_03_boundaries.py:169`; `tests/architecture/test_pr3_02_s1_boundaries.py:10`). Run the exact changed historical nodes and migration suites in addition to C; publish their final command list with actual results rather than assuming the previous head-maintenance list remains exhaustive.

| Risk (INFERRED) | Mitigation / stop condition |
| --- | --- |
| Scope expansion through activation | Q1 specifies the bounded enabling contract; stop before changing disabled execution predicates without it. |
| Cross-protocol deadlock or stale authority | Q2 freezes composition; test real waits and bounded whole-transaction retries, never widen retries to validation/timeouts. |
| Attribution laundering through B02 | Q6 freezes verifiable producer linkage; test mismatch/duplicate/legacy routes and atomic rollback. |
| New hash silently changes old truth | Q4 freezes literal bytes/digests independently; preserve S1, B02 and scientific vectors and saved history. |
| Fixture success masks production gaps | Application-only Agent enrollment, ordinary-role DML and disposable PG18; test adapters do not establish production verifier intake (`docs/phase3/PR3-02-S1-evidence.md:40–44`). |
| Evidence overstatement | Keep historical acceptance, this documentation check and future implementation results separate; external CI counts remain unavailable until supplied. |

## 5. Verification of this documentation-only task

Only `docs/phase3/PR3-02-S2-execution-pack.md` is written. No implementation, contract edits, migrations, tests, commits, pushes or branch creation are performed. The user required these two documentation checks:

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
git diff --check HEAD
test -s docs/phase3/PR3-02-S2-execution-pack.md && echo pack-present
```

Results are reported with raw output and exit codes in the planning handoff. Because the new file is untracked, `git diff --check HEAD` alone does not inspect its contents; a separate read-only line-count/trailing-whitespace check covers the file without staging it. Required size: fewer than 400 lines.
Unit, architecture, PostgreSQL and full-suite tests: **NOT RUN (documentation-only change; no affected executable suites and no test counts)**. All proposed implementation checks remain NOT RUN. Stop after the documentation evidence; implementation requires the separate authorization described above.
