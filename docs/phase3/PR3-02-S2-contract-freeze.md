# PR3-02-S2 execution pack r3 — intent-only, planning only

Baseline: `27dc60e1765b15434dda0e21544427aed0d3a21a`, inspected 2026-10-25. The sole deliverable is this new file. The original pack and r2 remain unchanged. No code, migration, test, contract, dependency definition or governing Harness edit, commit, push or branch creation is authorized by this task.

Read order: `AGENTS.md`; applicable architecture 01 → 02 → 03 → 08 → Phase 3 specification 06 → Harness specification 09 → original execution pack; then the supplied r2, answers, reviews, ADR and cited baseline implementations.

Source aliases (repository-relative unless an absolute path is given):

- **P** = `docs/phase3/PR3-02-S2-execution-pack.md`.
- **D** = `docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md`.
- **A** = `docs/architecture/adr/ADR-0023-pr3-02-agent-identity-versions-executions.md`.
- **0078** = `migrations/versions/0078_task_safety_policies.py`; **0079** = `migrations/versions/0079_agent_identity_versions.py`; **0080** = `migrations/versions/0080_capability_gateway.py`.
- **r2** = `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane220/docs/phase3/PR3-02-S2-execution-pack-r2.md`.
- **Answers** = `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/work/lane210/docs/phase3/PR3-02-S2-open-questions-answers.md`.
- **Review A** = `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/reviews/s2_r2_review_A.md`.
- **Review B** = `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/reviews/s2_r2_review_B.md`.

**FROZEN-PROPOSAL** fixes literal choices for review in this revision; it does **not** mean accepted, owner-frozen or implementation-authorized. Every proposed name, field, bound, predicate, order, mapping, DTO, test allocation and future file in a subsection/table marked FROZEN-PROPOSAL inherits that label. Source facts and the binding owner scope decision are identified separately. Digest vector outputs remain **NOT YET COMPUTED**, including retained deferred vectors.

## 1. Scope, authority and evidence

The binding owner decision is **option B: INTENT-ONLY S2**. This replaces r2's proposed enabling profile. S2 may create a CREATED execution intent for a sealed PLANNING task at its current revision, the corresponding typed initial event and receipt, and provide exact replay/reads. It does not activate an Agent. The assigned version/Agent identifies the intended actor; it proves no produced output or performed work.

This is a narrowed delivery slice of D, not completion of the full execution/promotion roadmap in D:35–44. Its successful acceptance would cover intent only. Positive RUNNING→SUCCEEDED→promotion obligations remain later work, explicitly inventoried in §2; denials cannot be reported as positive running coverage. Existing S1 and PR3-01/03/04 contracts remain unchanged.

| Baseline evidence | Consequence |
| --- | --- |
| A:3–16; D:3,35–48,77–82 | S2 needs accepted prerequisites and separate implementation authorization. The owner now limits this planning revision to intent. |
| `docs/phase3/PR3-02-S1-evidence.md:22–44,123–141,538–541` | S1 identity/version/availability and manifest values exist. Application-only test adapters do not establish production verifier intake. |
| `docs/phase3/PR3-03-evidence.md:7331–7349` | Recorded owner acceptance and final-head CI are historical PR3-03 evidence, not S2 evidence. |
| `docs/phase3/PR3-04-acceptance.md:3–5,23–38` | Acceptance is conditional on green full-suite CI at the accepted head. Run IDs `40111940781`/`40111943031` on `2914208` alone do not prove that condition fulfilled. **PR3-04 CI-green condition confirmed remains an OPEN prerequisite**; exact results/counts must be attached before S2 freeze/authorization. The PR3-04 review waiver does not transfer. |
| `docs/phase3/PR3-03-contract-freeze.md:58–66`; `docs/phase3/PR3-04-contract-freeze.md:30–39,611–618` | Accepted groundwork leaves task execution disabled. No new projection, trusted token or fixture may open it. |
| 0079:9–10; 0080:5–6,166 | Current chain ends at `0080_capability_gateway`; gateway mode remains CONTRACT_FAKE. Future head **H** is unnumbered and must follow the then-current reviewed head. |
| `docs/phase3/PR3-04-acceptance.md:35–38` | Specifically excludes S2, PR3-05 D1/D2 and full PR3-05 acceptance. It is not evidence about provider disclosure or API/CLI scope. |

FROZEN-PROPOSAL scope refinement: no new transport/API/CLI routes or provider disclosure functionality is allocated here. This is a pack choice, not a claim supported by the PR3-04 acceptance exclusions. D:70–75 supplies the separate scheduler/lease/provider/sandbox/working-memory/gateway exclusions. No new runtime dependency, fingerprint entity, scientific schema or public ErrorCode is proposed.

### Q1 — FROZEN-PROPOSAL: intent-only profile; no enabling amendment

D:77–82 states, verbatim:

> PR3-02-S2 may store CREATED execution intent for a sealed PLANNING task. It must not
> advance the task/steps or start work while PR3-01's execution gate is closed.
> Lifecycle/provenance interfaces are defined here for S2; their positive running
> and promotion cases require accepted PR3-03 gateway and PR3-04 policy integration
> before S2 implementation. No temporary switch or fixture-only production bypass
> opens that gate.

**This S2 slice does not amend D:77–82.** Option B exercises only their CREATED-intent allowance. No change to PR3-01 gates, `execution_enabled`, or the PR3-03 gateway is included. Delete r2's parallel `s2_admission` execution profile from the active proposal; no replacement start gate or S2 consumer token is introduced. A:13's staged intent decision is preserved. The owner's narrowed scope defers the full roadmap's running/promotion implementation and acceptance together.

| FROZEN-PROPOSAL operation | Admission | Sole effect |
| --- | --- | --- |
| `create_agent_execution` | Q5 `S2_INTENT_CALLER`; exact ACTIVE version and live enrolled Agent; sealed PLANNING task, current `expected_task_revision`, absent or same-task PENDING step; verified frozen input and harness bindings | One immutable CREATED intent/revision 1, one initial event, one receipt, in one UoW. Task/step state and revision unchanged. |
| Exact command replay / reconciliation | Current READ, original project/caller/command and identical normalized material | Original receipt, intent and initial event; no effects or new IDs. |
| `get_agent_execution`, `list_task_executions` | Current READ and exact project-scoped IDs; bounded page | Immutable intent and its initial history. No execution-authority conclusion. |

There are **no admitted lifecycle edges**, including CREATED→CANCELLED. RUNNING, resume, waits, completion, failure and cancellation are outside this slice. No transition or promotion command/result variant is added to the active command union. An attempted status mutation is rejected by immutable storage guards; existing reserved Application operations retain their existing closed-gate denials. Intent creation neither consumes budget nor requests/approves a checkpoint.

Autonomy is not an S2 intent admission field, authority grant or new A0/A1 execution filter. Existing task-policy consistency continues to apply wherever a checkpoint policy is already bound: autonomy must be **at or below** the checkpoint ceiling, since 0078:495 rejects only `autonomy_level > maximum_autonomy`. Equal-to-ceiling is allowed. This clarification is needed only if intent validation reads that existing task invariant; S2 does not require a policy bundle to create intent and does not add a dispatch-time autonomy predicate.

## 2. Deferred to a later separately authorized slice

Every row is **DEFERRED**, not part of the intent implementation or its acceptance. The question column preserves the exact original question identity in P:45–52. r2's detailed answers for these items are historical **FROZEN-PROPOSAL**, not defaults that may be implemented opportunistically. Later work needs its own scope, review/freeze, prerequisite evidence and explicit authorization.

| Original question | Explicitly deferred item |
| --- | --- |
| **Q1 — Exact execution activation** | `transition_agent_execution`; RUNNING; every start/resume; WAITING_TOOL/WAITING_HUMAN; SUCCEEDED/FAILED/CANCELLED, including pre-start intent cancellation; outcome attestation, retries as actual work, recovery and controller takeover. |
| **Q1 — Exact execution activation** | Any gateway spend, reservation, request/start/finish/settlement linked to S2; `AGENT_EXECUTION_FAKE`, `capability_invocations.agent_execution_id`, execution FK/mode/step/harness linkage, `S2ConsumerContext`, last-unit start integration. No changes to the PR3-03 gateway in this slice. |
| **Q1 — Exact execution activation** | Any opening/change of PR3-01 execution gates or `execution_enabled`, and any parallel `s2_admission` gate. r3 does not authorize such a future opening either. |
| **Q2 — Composed lock/receipt protocol** | S2/gateway composition and added gateway execution locks; safety dispatch/accounting integration; linked capture lock recipe; B02 owning composition keys, promotion write upgrades, cross-command receipt/effect ownership and related linked-work races. Only intent's own lock/receipt protocol remains active. |
| **Q3 — Exact persistence contract** | `agent_promotion_records`, `agent_promotion_outputs`, all their columns, keys, indexes, guards and triggers; receipt `result_promotion_id` and any output result link; transition/promotion operation shapes and receipt results. No placeholder columns or tables. |
| **Q3 — Exact persistence contract** | Invocation/capture adjuncts and trigger replacements; result/trace/memory/output/summary/error/start/finish columns and their lifecycle guards; controller storage and future-only composite execution keys. Retain only the two intent tables and intent receipt links in Q3. |
| **Q4 — Exact material and vectors** | Transition/promotion command material; candidate selectors/digests, B02 result manifests, execution output digests, summaries/errors, new-mode gateway material, promotion configuration opt-in and **AgentPromotionPolicySnapshot**. Deferred vector requirements remain NOT YET COMPUTED; none is an intent freeze dependency. |
| **Q5 — Transition and promotion authority** | Controller selection/authority, dispatch/outcome/settlement predicates, revocation during in-flight work and recovery; every promotion mode, **AGENT_POLICY authority**, approval interpretation and its snapshot basis; HUMAN_CONFIRMED/HUMAN_CREATED_FROM_CANDIDATE and AUTOMATIC_UNDER_POLICY. No policy snapshot is created by intent. |
| **Q6 — Producer/capture attribution** | All producer-attribution work: `producing_execution_id`, trusted `S2CaptureContext`, capture/invocation/output linkage, capture result validation, owning B02 command identity, no-attach/standalone-bypass guards, atomic promotion and provenance queries. Existing capture/artifact equality does not establish an S2 producer. |
| **Q6 — Producer/capture attribution** | Review A's promotion→capture same-project FK choice and owning-command receipt matching must be resolved in the later promotion pack; neither a weak FK nor a generic target is approved here. |
| **Q7 — PR3-05 read-only compatibility** | Any producer-read extension, preview authorization, saving or full PR3-05 implementation. **D1 and D2-C remain deferred**, including artifact-writer protocol work. D2-C here means PR3-05 saving, not PR3-04's separately numbered budget-extension decision. |
| **Q1/Q6 — Exact execution activation / Producer/capture attribution** | Positive RUNNING→SUCCEEDED→promotion evidence, output-XOR tests, capture/finish/cancel races, promotion rollback and scientific attribution acceptance from r2. Intent denial coverage cannot discharge them. |

Q7's existing decision itself is retained: the PR3-05 preview continues to return `S2_PRODUCER_PROVENANCE_UNVERIFIED` (`src/researchbase/agent_runtime/application/promotion_context.py:98–110`; `tests/integration/phase3/test_pr3_05_promotion_validation.py:21–59`). An intent read supplies no producer verification. Artifact-free atomic target decisions and accepted forward-head advancement are not reopened; atomic targets simply do not run in this slice.

## 3. Active intent proposals

### Q2 — FROZEN-PROPOSAL: intent locks, waits and atomic effect ownership

Sources: D:268–350,385–397. The 23-table SHARE prefix remains the deliberately broad approved S2 inventory, even though this slice makes no B02 write. Do not silently shrink or reorder it. No gateway, safety or B02 public wrapper is nested inside the intent UoW.

1. Authenticate; use an entitled read preflight to verify retained harness/configuration bytes and input pins before the write transaction. A separately requested exact replay uses the formal-read path directly. A failed new-write byte preflight must not preempt an entitled saved receipt. No model/network/process/ArtifactStore I/O is allowed under write locks.
2. Open one synchronous READ COMMITTED UoW with autoflush off and connection-startup `lock_timeout=10s`, `statement_timeout=30s`. Its first Application SQL is exactly the following SHARE statement, including replay through the write entry:

```sql
LOCK TABLE actor_subject_bindings, actors, artifact_versions, artifacts,
claim_versions, claims, hypothesis_versions, hypotheses,
literature_source_project_links, literature_sources, manuscript_versions,
project_membership_events, project_memberships, project_role_assignments,
projects, publications, research_question_versions, research_questions,
source_versions, strategy_candidate_captures, strategy_candidate_sources,
strategy_hypothesis_admissions, strategy_question_admissions IN SHARE MODE
```

3. Acquire `rb_phase2_lock_project(project_id)` → `pr302:command:<project>:<caller>:<command>` → `pr302:actor:<intended-agent>` → `pr301:task:<task>` → `pr302:version:<version>` → `pr302:execution:<execution>`. Use transaction-scoped `pg_advisory_xact_lock(hashtextextended(key,0))` and canonical lowercase UUIDs. Resolve the actor by immutable version lookup under the prefix; if absent, skip only that undeterminable actor key and reject after entitled lookup. No enrollment or B02 owning key applies.
4. Lock caller/intended-Agent actor rows FOR UPDATE in deduplicated ascending UUID order → task FOR UPDATE → task steps FOR UPDATE ascending ID → availability FOR UPDATE → intent row FOR UPDATE if present. Read sealed task/selected-step inputs under the task key. No safety, invocation or admission row-lock additions are needed. Missing intent remains protected by its execution key.
5. After **each** blocking prefix/key/row/write/constraint wait, reread durable authority and obtain fresh advancing `clock_timestamp()`. Authenticate/authorize current READ before receipt/existence/conflict disclosure. Preliminary checks may deny but do not authorize an effect before all required locks are held. Entitled equal-material replay precedes new-write state/availability/CAS checks.
6. For a new intent, recheck Q5, sealed PLANNING/PENDING scope, the exact current task revision and immutable input/harness/configuration pins. Allocate receipt/event IDs once across retries. **One write order everywhere: receipt first → intent second → initial event third → SET CONSTRAINTS ALL IMMEDIATE → fresh final authorization → single commit.** The two receipt result FKs are deferred only to permit this order. The receipt root verifies all effects. No hidden task write, policy request, artifact write, promotion or invocation is part of this transaction.

FROZEN-PROPOSAL effect counts: create = 1 intent + 1 initial event + 1 agent receipt; intent revision = 1; task receipt/event/revision delta = 0; task/step state delta = 0; gateway/reservation/usage/capture/scientific-object delta = 0. Replay/read = zero effects. Failure at any boundary rolls back all three intent effects.

Only SQLSTATE 40001/40P01 may retry, at most three fresh whole transactions with stable IDs/material and fresh authority. 55P03/57014 are bounded failures without automatic retry. Uncertain commit reconciles the original receipt identity in one REPEATABLE READ READ ONLY snapshot; an absent receipt is absence in that snapshot, not proof of global rollback. Formal queries/reconciliation use `begin_formal_read`, autoflush off, no row/advisory/SHARE locks, writes, repair or second session.

Compatibility facts, not new composition instructions: gateway's 18-table list is at `src/researchbase/persistence/research_task_repository.py:13–32`, but its **actual call path** is `capability_gateway_repository.py:104` → `task_safety_repository.py:55–68` (both under `src/researchbase/persistence/`); task→actor/version ordering follows `capability_gateway_repository.py:104–131`. Intent uses actor→task as specified by D. Test real coexistence contention; do not claim deadlock freedom or change either accepted writer. B02 already has connection startup timeouts in `src/researchbase/persistence/uow.py:1334–1349`: **reuse the existing B02 startup-timeout factory** if later linked capture is authorized, not a new timeout mechanism. No B02 factory change is proposed here.

### Q3 — FROZEN-PROPOSAL: only the intent persistence delta

H is a forward-only migration after `0080_capability_gateway` at this baseline; choose no revision number here. Only two new tables and two nullable result FKs on existing `agent_command_receipts` are proposed. All new keys/constraints/indexes/functions/triggers below are FROZEN-PROPOSAL identifiers, not delivered objects. No edits to accepted migration bytes, gateway objects, captures, B02 admissions, task/safety guards or their contracts. Populated upgrade creates no fabricated history; downgrade must refuse before DDL/data/revision changes, including on an empty database.

#### Q3.1 — FROZEN-PROPOSAL columns

Types: `uuid`; `integer`; `text`; `timestamptz` (finite, aware UTC at Application boundaries). All new table fields are NOT NULL except the two explicitly nullable fields below. No SQL defaults, identity columns or generated expressions. All new row IDs and command IDs use UUIDv7; historical references retain their existing UUID validity rules.

| Table | Exact column | Type / meaning |
| --- | --- | --- |
| agent_execution_instances | id | uuid, fresh intent ID |
| agent_execution_instances | project_id | uuid, exact project |
| agent_execution_instances | research_task_id | uuid, exact sealed task |
| agent_execution_instances | research_task_step_id | uuid **NULL**, same-task attribution scope only |
| agent_execution_instances | task_revision_at_creation | integer, accepted current task revision; never current/latest on read |
| agent_execution_instances | agent_version_id | uuid, exact immutable version |
| agent_execution_instances | actor_id | uuid, that version's intended Agent; no output attribution |
| agent_execution_instances | status | text, CREATED only |
| agent_execution_instances | revision | integer, 1 only |
| agent_execution_instances | created_at | timestamptz, receipt time |
| agent_execution_instances | input_ref_hash | text, Q4 normalized input digest |
| agent_execution_instances | input_ref_hash_scheme | text, sha256-cjson-v1 |
| agent_execution_instances | harness_artifact_version_id | uuid, exact frozen harness artifact |
| agent_execution_instances | harness_content_hash | text, retained-byte digest |
| agent_execution_instances | harness_hash_scheme | text, sha256-bytes-v1 |
| agent_execution_events | id | uuid, fresh initial event ID |
| agent_execution_events | execution_id | uuid, intent FK |
| agent_execution_events | sequence | integer, 1 only |
| agent_execution_events | prior_status | text **NULL**, always NULL for initial event |
| agent_execution_events | new_status | text, CREATED only |
| agent_execution_events | actor_id | uuid, authenticated receipt caller |
| agent_execution_events | occurred_at | timestamptz, receipt time |
| agent_execution_events | reason | text, exact server literal `Execution intent created.` |
| agent_execution_events | receipt_id | uuid, matching fresh receipt |
| agent_command_receipts (add) | result_execution_id | uuid **NULL**, intent result only |
| agent_command_receipts (add) | result_execution_event_id | uuid **NULL**, initial event result only |

The retained digests carry explicit scheme columns; there is no implicit new hash domain fixed only by prose. Existing `request_hash`/`hash_scheme` on receipts remain unchanged (0079:69–70). `task_revision_at_creation` records intent admission, not authority to use a later task revision. Full-lifecycle columns, controller/promotion/output tables and their result links are deferred in §2 rather than added empty. A later pack must review any additive evolution of these intent-only shapes.

#### Q3.2 — FROZEN-PROPOSAL keys and indexes

All FKs: ON UPDATE NO ACTION / ON DELETE RESTRICT, MATCH SIMPLE, NOT DEFERRABLE except the two receipt result FKs marked DID (DEFERRABLE INITIALLY DEFERRED). PK/UNIQUE constraints create same-named btree indexes.

| Literal constraint | Table and exact key/reference |
| --- | --- |
| pr302s2_exec_pk | agent_execution_instances PK(id) |
| pr302s2_exec_project_fk | project_id → projects(id) |
| pr302s2_exec_task_fk | (research_task_id, project_id) → research_tasks(id, project_id) |
| pr302s2_exec_step_fk | (research_task_id, research_task_step_id) → research_task_steps(research_task_id, id) |
| pr302s2_exec_version_fk | (agent_version_id, project_id, actor_id) → agent_versions(id, project_id, actor_id) |
| pr302s2_exec_actor_fk | actor_id → actors(id) |
| pr302s2_exec_harness_fk | harness_artifact_version_id → artifact_versions(id) |
| pr302s2_event_pk | agent_execution_events PK(id) |
| pr302s2_event_execution_uq | agent_execution_events UNIQUE(execution_id); only one initial event |
| pr302s2_event_receipt_uq | agent_execution_events UNIQUE(receipt_id) |
| pr302s2_event_execution_fk | execution_id → agent_execution_instances(id) |
| pr302s2_event_actor_fk | actor_id → actors(id) |
| pr302s2_event_receipt_fk | receipt_id → agent_command_receipts(id) |
| pr302s2_receipt_execution_fk | agent_command_receipts.result_execution_id → agent_execution_instances(id), DID |
| pr302s2_receipt_event_fk | agent_command_receipts.result_execution_event_id → agent_execution_events(id), DID |

Existing referenced composite keys are real baseline keys: 0077 (`migrations/versions/0077_research_task_graph.py`):36,64 and 0079:45. Same-project artifact scope is through `artifact_versions.artifact_id → artifacts.project_id`, validated by the guard; do not invent an ArtifactVersion project column.

| Literal additional btree index | Table(columns); predicate |
| --- | --- |
| pr302s2_exec_project_task | agent_execution_instances(project_id, research_task_id, id) |
| pr302s2_exec_task_step | agent_execution_instances(research_task_id, research_task_step_id) |
| pr302s2_exec_version | agent_execution_instances(agent_version_id, project_id, actor_id) |
| pr302s2_exec_actor | agent_execution_instances(actor_id) |
| pr302s2_exec_harness | agent_execution_instances(harness_artifact_version_id) |
| pr302s2_event_actor | agent_execution_events(actor_id) |
| pr302s2_receipt_execution_uq | UNIQUE agent_command_receipts(result_execution_id) WHERE result_execution_id IS NOT NULL |
| pr302s2_receipt_event_uq | UNIQUE agent_command_receipts(result_execution_event_id) WHERE result_execution_event_id IS NOT NULL |

The execution task-step index covers its task FK prefix; event execution/receipt unique indexes cover their FKs. No future-only invocation/promotion composite execution keys are proposed.

#### Q3.3 — FROZEN-PROPOSAL literal CHECKs and receipt shapes

Each CHECK below is row-local SQL. Cross-row checks belong to named guards in Q3.4, never to a purported CHECK. No Unicode category-C or ErrorCode-enum membership test is hidden here: the only new event text is a literal and lifecycle error/summary fields are deferred.

| Literal CHECK name | SQL predicate |
| --- | --- |
| pr302s2_exec_id_ck | `substring(id::text from 15 for 1) = '7' AND substring(id::text from 20 for 1) IN ('8','9','a','b')` |
| pr302s2_exec_status_ck | `status = 'CREATED'` |
| pr302s2_exec_revision_ck | `revision = 1` |
| pr302s2_exec_task_revision_ck | `task_revision_at_creation BETWEEN 1 AND 2147483647` |
| pr302s2_exec_time_ck | `isfinite(created_at)` |
| pr302s2_exec_hashes_ck | `input_ref_hash ~ '^[0-9a-f]{64}$' AND harness_content_hash ~ '^[0-9a-f]{64}$'` |
| pr302s2_exec_schemes_ck | `input_ref_hash_scheme = 'sha256-cjson-v1' AND harness_hash_scheme = 'sha256-bytes-v1'` |
| pr302s2_event_id_ck | `substring(id::text from 15 for 1) = '7' AND substring(id::text from 20 for 1) IN ('8','9','a','b')` |
| pr302s2_event_initial_ck | `sequence = 1 AND prior_status IS NULL AND new_status = 'CREATED'` |
| pr302s2_event_time_ck | `isfinite(occurred_at)` |
| pr302s2_event_reason_ck | `reason = 'Execution intent created.'` |
| pr302s2_receipt_operation_ck | `operation IN ('provision_project_agent','register_agent_version','change_agent_availability','create_agent_execution')` |

FROZEN-PROPOSAL `pr302s2_receipt_shape_ck` has this literal SQL predicate, preserving all existing S1 result combinations and adding only intent:

```sql
(
  operation = 'provision_project_agent'
  AND num_nonnulls(result_actor_id, result_binding_id, result_membership_id,
    result_role_assignment_id, result_binding_event_id,
    result_membership_event_id, result_role_event_id) = 7
  AND result_agent_version_id IS NULL AND result_availability_event_id IS NULL
  AND result_execution_id IS NULL AND result_execution_event_id IS NULL
  AND resulting_revision = 1
) OR (
  operation IN ('register_agent_version','change_agent_availability')
  AND num_nonnulls(result_actor_id, result_binding_id, result_membership_id,
    result_role_assignment_id, result_binding_event_id,
    result_membership_event_id, result_role_event_id) = 0
  AND result_agent_version_id IS NOT NULL AND result_availability_event_id IS NOT NULL
  AND result_execution_id IS NULL AND result_execution_event_id IS NULL
  AND ((operation = 'register_agent_version' AND resulting_revision = 1)
    OR (operation = 'change_agent_availability' AND resulting_revision >= 2))
) OR (
  operation = 'create_agent_execution'
  AND num_nonnulls(result_actor_id, result_binding_id, result_membership_id,
    result_role_assignment_id, result_binding_event_id,
    result_membership_event_id, result_role_event_id,
    result_agent_version_id, result_availability_event_id) = 0
  AND result_execution_id IS NOT NULL AND result_execution_event_id IS NOT NULL
  AND resulting_revision = 1
)
```

Only the two old receipt CHECKs for operation/result shape are replaced. Their anticipated generated names are `agent_command_receipts_operation_check` and `agent_command_receipts_check` from unnamed 0079:67–106 DDL. **Catalog confirmation NOT RUN**: H must assert actual names and exact definitions before replacing them and fail on drift. All remaining existing constraints stay intact. No promotion result column is available to make a fifth receipt shape.

#### Q3.4 — FROZEN-PROPOSAL functions, triggers and completeness

All functions use invoker privileges and `SET search_path=pg_catalog,public,pg_temp`; no dynamic target SQL, external I/O or advisory acquisition. New trigger functions take no arguments and return trigger. The helper signatures and diagnostic ownership below are exhaustive for the intent proposal; any extra function/trigger or shared-table guard requires review of a revised delta.

| Function | Responsibility |
| --- | --- |
| `pr302s2_cjson(value jsonb) RETURNS text` | New pure serializer for the Q4 null/bool/integer/string/list/object subset; exact compact UTF-8 canonical representation, sorted object keys, no jsonb::text whitespace. Reject unsupported numeric/type values with the explicit helper diagnostic in Q3.5. It does not decide domain-specific key sets. |
| `pr302s2_value_digest(value jsonb) RETURNS text` | New pure SHA-256 of UTF-8 `pr302s2_cjson`; lowercase hex; propagates serializer diagnostics, raises no separate tag. |
| `pr302s2_input_material(p_execution uuid) RETURNS jsonb` | New read helper: reconstruct Q4 input material from the exact intent and sealed task/selected-step typed rows. Missing scope/pins are explicit diagnostics, never empty successful material. |
| `pr302s2_preheld() RETURNS void` | Require READ COMMITTED and the granted ordered inventory's SHARE protection; each inserting guard also verifies its applicable advisory keys/row locks already held. Never acquire locks in a trigger. |
| `pr302s2_execution_guard()` | BEFORE INSERT only: require a fresh create receipt naming NEW.id; preheld locks; exact Q5 caller/Agent equality; sealed PLANNING/PENDING scope and task revision; ACTIVE version/live Agent; exact frozen same-project harness/config/input pins; CREATED/revision 1 and receipt creation time. Do not run a lifecycle transition graph. |
| `pr302s2_event_guard()` | BEFORE INSERT only: require fresh matching intent/receipt, exact receipt result event ID, caller/time, sequence 1/prior NULL/new CREATED and fixed reason. No late append or use of a historical receipt. |
| `pr302s2_immutable()` | Reject every UPDATE/DELETE, including no-op, on intent and event rows. |
| `pr302_receipt_guard()` | Forward replacement: explicitly dispatch by supported operation **before** applying an owner predicate. S1 operations alone use the existing HUMAN OWNER predicate and S1-specific checks. Intent uses the staged S2 caller checks described below and preheld protocol; sets advancing recorded_at. |
| `pr302_receipt_complete()` | Forward replacement: isolate S1 ownership/completeness to the three S1 operations; create-intent case validates the complete S2 predicate, request/input digests and the three-row closure below. Full S2 closure runs once per inserted S2 receipt. |

**Receipt-owner correction (Review A P2):** 0079:216–228 is an **unconditional** HUMAN OWNER check in the delivered `pr302_receipt_guard`. It is not evidence of pre-existing per-operation owner branches. The replacement must make that predicate **S1-operation-only** for `provision_project_agent`, `register_agent_version`, `change_agent_availability`. The analogous unconditional final OWNER check at 0079:458–466 in `pr302_receipt_complete` must also become S1-operation-only; preserve its existing behavior and diagnostics for S1.

The named S2 predicate is **`S2_INTENT_CALLER`** (Q5): current authenticated HUMAN OWNER/RESEARCHER, or the exact version's bound AGENT with current RESEARCHER entitlement. Receipt-first insertion means the intent does not yet exist: the receipt guard checks the predicate's durable caller/type/role/project component and fresh identity; `pr302s2_execution_guard` then checks the exact Agent/version match from NEW; the receipt root rechecks the **complete** predicate using the now-present intent. Missing intent never permits commit. The Application verifies the exact caller before receipt insertion, including local credential verification that SQL alone cannot supply. A receipt guard must not perform the old OWNER check before its S2 dispatch and thereby reject a RESEARCHER or intended Agent.

| Trigger | Table; timing/event; function |
| --- | --- |
| pr302s2_execution_insert (new) | agent_execution_instances; BEFORE INSERT; pr302s2_execution_guard |
| pr302s2_execution_immutable (new) | agent_execution_instances; BEFORE UPDATE OR DELETE; pr302s2_immutable |
| pr302s2_event_insert (new) | agent_execution_events; BEFORE INSERT; pr302s2_event_guard |
| pr302s2_event_immutable (new) | agent_execution_events; BEFORE UPDATE OR DELETE; pr302s2_immutable |
| pr302_receipt_insert (existing, function replaced) | agent_command_receipts; BEFORE INSERT; pr302_receipt_guard |
| pr302_receipt_immutable (existing, unchanged) | agent_command_receipts; BEFORE UPDATE OR DELETE; pr302_immutable |
| pr302_receipt_complete_commit (existing, function replaced) | agent_command_receipts; AFTER INSERT constraint trigger, DID; pr302_receipt_complete |

All are FOR EACH ROW. There is no child deferred completeness scan and no overlapping insert/update admission trigger. In particular, r2's `pr302s2_invocation_link_guard`/`pr302s2_invocation_link` are **not installed**, and `pr303_invocation_guard`/`pr303_validate_gateway` are **not replaced**. The overlapping gateway-trigger finding is removed from S2 scope rather than left dependent on trigger name ordering. Existing B02/safety/task guards and receipt-root firing remain unchanged.

FROZEN-PROPOSAL create receipt-root closure, after the single receipt→intent→event write order:

1. Receipt, intent and event must be fresh in the current transaction (`xmin = pg_current_xact_id()::xid`), mutually linked through the exact result IDs, and match project/caller/operation. Child guards require the fresh receipt to exist first. One create operation describes exactly these three rows; no attachment to pre-existing history.
2. Exactly one intent and one initial event belong to that receipt; event.execution_id equals result_execution_id, event.id equals result_execution_event_id, event.receipt_id equals receipt.id, sequence and both saved revisions equal 1, prior_status is NULL and new_status/status are CREATED. Event caller/time and intent creation time equal the saved receipt caller/time.
3. The full `S2_INTENT_CALLER` and fresh intent admission predicate hold after all waits. Task revision equals task_revision_at_creation; no start, task mutation or later revision is inferred. Input digest recomputes from sealed typed rows. Frozen harness/config/input pins match the Application's verified preflight and stored artifact metadata; SQL does not claim to rehash ArtifactStore bytes.
4. Reconstruct Q4 create material from receipt project/caller/command and intent fields (including task_revision_at_creation); recompute its request_hash with the existing receipt scheme. Reject contradictions, missing/extra event, projection-only/receipt-only/event-only writes and reused result links.
5. Force deferred constraints before commit and recheck live Application credentials/entitlement immediately before commit. No task receipt/event or safety/gateway/B02 write is part of the permitted effect set. Application/ordinary-role tests must compare those pre/post facts. The receipt root validates its own effects, not an invented global transaction-audit system.

#### Q3.5 — FROZEN-PROPOSAL function × diagnostic × SQLSTATE × translator

Every explicitly raised new tag has its raising function here. Tags are PostgreSQL diagnostic `CONSTRAINT` fields, not public ErrorCodes; translate by exact SQLSTATE plus known diagnostic name/context, never raw exception text. **Intent translator** below means the S2 Application/UoW path extending the existing Agent normalization at `src/researchbase/persistence/uow.py:832–861`. That extension must run before generic 23514/23505 fallbacks. No new public error enum is added.

| Raising function(s), exhaustive for this tag | Exact raised tag | SQLSTATE | Existing ErrorCode | Translating service/path |
| --- | --- | --- | --- | --- |
| pr302s2_cjson | pr302s2_value_type | **22023** | VALIDATION_ERROR | Intent translator; value_digest propagates unchanged. Direct normal-role SQL sees 22023, not a transport error. |
| pr302s2_preheld; pr302s2_execution_guard; pr302s2_event_guard; pr302_receipt_guard (S2 case) | pr302s2_preheld | 23514 | PROVENANCE_CLOSURE_VIOLATION | Intent translator |
| pr302_receipt_guard (S2 case); pr302s2_execution_guard; pr302_receipt_complete (S2 case) | pr302s2_scope | 23514 | FORBIDDEN | Intent translator; current entitlement precedes disclosure |
| pr302s2_execution_guard; pr302_receipt_complete (S2 case) | pr302s2_state | 23514 | INVALID_STATE_TRANSITION | Intent translator; unsealed/non-PLANNING task, non-PENDING selected step, unavailable version |
| pr302s2_execution_guard; pr302_receipt_complete (S2 case) | pr302s2_cas | 23514 | CONCURRENT_MODIFICATION | Intent translator; task revision mismatch after replay exclusion |
| pr302s2_execution_guard; pr302s2_input_material | pr302s2_binding | 23514 | REFERENTIAL_INTEGRITY_ERROR | Intent translator; concrete scope contradiction not already rejected by FK |
| pr302s2_execution_guard; pr302s2_input_material | pr302s2_not_frozen | 23514 | VERSION_NOT_FROZEN | Intent translator |
| pr302s2_execution_guard; pr302s2_input_material | pr302s2_unresolved | 23514 | FROZEN_REFERENCE_REQUIRED | Intent translator; unresolved immutable pin |
| pr302s2_execution_guard; pr302s2_input_material; pr302_receipt_complete (S2 case) | pr302s2_provenance | 23514 | PROVENANCE_CLOSURE_VIOLATION | Intent translator; saved hash/pin/request contradiction |
| pr302s2_execution_guard; pr302s2_event_guard | pr302s2_late_history | 23514 | IMMUTABLE_RECORD | Intent translator; historical receipt/intent attachment |
| pr302s2_execution_guard; pr302s2_event_guard; pr302_receipt_complete (S2 case) | pr302s2_completeness | 23514 | PROVENANCE_CLOSURE_VIOLATION | Intent translator; missing, extra or mismatched fresh result/history |
| pr302s2_immutable | pr302s2_immutable | 23514 | IMMUTABLE_RECORD | Intent translator |
| pr302_receipt_guard; pr302_receipt_complete, **S1 cases only** | pr302_scope | 23514 | FORBIDDEN | Existing S1 Agent translator; S1 owner behavior retained |
| pr302_receipt_guard; pr302_receipt_complete, **S1 cases only** | pr302_provenance | 23514 | PROVENANCE_CLOSURE_VIOLATION | Existing S1 Agent translator; existing version/enrollment checks retained |
| pr302_immutable (unchanged) | pr302_immutable | 23514 | IMMUTABLE_RECORD | Existing Agent translator, including shared receipt mutation |

FROZEN-PROPOSAL numeric boundary (owner decision, option B): both layers reject unsupported numeric values with the same rule. The Python layer rejects any non-integer or out-of-profile JSON number before conversion to JSONB. The SQL helper `pr302s2_cjson` rejects the same set with `ERRCODE='22023', CONSTRAINT='pr302s2_value_type'`; a normal-role direct SQL writer therefore cannot bypass the rule. Passing SQL NULL instead of an explicit JSON value, or another unsupported value to `pr302s2_cjson`, also raises `ERRCODE='22023', CONSTRAINT='pr302s2_value_type'`. The digest helper propagates that diagnostic rather than replacing it with 23514. Closed field-set/scalar validation happens before hashing; duplicate JSON keys must be rejected before jsonb conversion can discard them. Serialization is only for the normalized supported subset, not a change to the general existing serializer's float support. Independent numeric/type rejection vectors must prove Python/SQL parity: the two layers must reject the same inputs, and a PostgreSQL test must compare them as required evidence, not optional coverage.

| Physical constraint/error source | SQLSTATE | Intent translation |
| --- | --- | --- |
| Any Q3.2 named FK | 23503 | REFERENTIAL_INTEGRITY_ERROR; wrong-project Application denial comes first |
| Q3.3 `pr302s2_exec_status_ck` | 23514 | INVALID_STATE_TRANSITION |
| Q3.3 `pr302s2_exec_revision_ck`, `pr302s2_event_initial_ck`, `pr302s2_event_reason_ck`, `pr302s2_receipt_shape_ck` | 23514 | PROVENANCE_CLOSURE_VIOLATION |
| All remaining Q3.3 CHECKs; required-column NULL; typed conversion/range/time errors | 23514; 23502; 22P02/22003/22007/22008 | VALIDATION_ERROR |
| pr302s2_exec_pk / pr302s2_event_pk | 23505 | CONCURRENT_MODIFICATION, after entitled receipt reconciliation; no overwrite |
| pr302s2_event_execution_uq / pr302s2_event_receipt_uq / pr302s2_receipt_execution_uq / pr302s2_receipt_event_uq | 23505 | PROVENANCE_CLOSURE_VIOLATION after replay exclusion |
| Existing receipt UNIQUE(project_id, caller_actor_id, command_id) | 23505 | Reconcile exact original identity: equal material returns saved result, changed material → IDEMPOTENCY_CONFLICT |
| Transaction serialization/deadlock | 40001/40P01 | Whole-transaction retry at most three attempts; exhausted → CONCURRENT_MODIFICATION |
| Lock/statement timeout | 55P03/57014 | CONCURRENT_MODIFICATION; no automatic retry |
| Application principal/object/material checks | No SQLSTATE | Untrusted principal → AUTHENTICATION_REQUIRED; absent entitled object → NOT_FOUND; changed same-key hash → IDEMPOTENCY_CONFLICT; malformed request → VALIDATION_ERROR |

**Foreign-service translation boundary:** no S2 trigger is installed on gateway, capture or B02 admission tables in r3, and no S2 helper is called by those services. Consequently standalone `StrategyCandidatePromotionService` retains its delivered P22B1/P22B2 translation and gateway/task-safety services retain their own known-tag translations; they have **no new S2 tag path to translate in this slice**. S1 calls on the shared receipt table dispatch only to the preserved S1 predicates/diagnostics. Do not claim the current foreign translators recognize the new tags. If a later separately authorized linked path can fire an S2 guard, that pack must extend the **actual enclosing service/UoW translator** and test the exact function/tag/SQLSTATE there before enabling it. It cannot rely on a generic fallback to produce FORBIDDEN. Unexpected foreign S2 paths retain sanitized failure and are a scope defect, not implicit permission to alter PR3-03 here. No raw SQL, constraint text or credentials reach callers; unknown faults preserve existing sanitized/uncertain-commit handling.

### Q4 — FROZEN-PROPOSAL: intent material, harness and independent vectors

Sources: D:147–180,218–224,256–266,373–383. Only `create_agent_execution` is added to the S2 command union. Values/DTOs are immutable and closed; unknown keys and wrong scalar types (including bool as integer) reject. UUID strings are canonical lowercase; command/execution IDs are UUIDv7. No caller-supplied principal, computed digest, producer/controller, receipt/event ID, timestamp or trusted consumer context.

| Value | Exact material |
| --- | --- |
| AgentCommandMaterial envelope | Eight keys: `type="AgentCommandMaterial"`, `material_version=1`, `operation="create_agent_execution"`, `project_id`, authenticated injected `caller_actor_id`, `command_id`, `expected_revision=null`, `arguments`. |
| Create arguments | Six keys: `execution_id`, `agent_version_id`, `research_task_id`, `research_task_step_id` (UUID or explicit NULL), `expected_task_revision` (strict integer 1..2147483647), `harness_artifact_version_id`. Store the accepted task revision as task_revision_at_creation; do not increment it. |
| AgentExecutionInputs v1 | Six keys: `type="AgentExecutionInputs"`, `material_version=1`, `project_id`, `research_task_id`, `research_task_step_id` (explicit NULL allowed), `inputs`. Each item has exactly `owner_kind`, `owner_id`, `target_kind`, `target_id`, `content_hash`, `hash_scheme`. |
| Input item values/order | owner_kind = TASK/STEP; target_kind = RESEARCH_QUESTION_VERSION/HYPOTHESIS_VERSION/CLAIM_VERSION/SOURCE_VERSION/ARTIFACT_VERSION/MANUSCRIPT_VERSION. Include task inputs and only the selected step's inputs. Sort lexicographically by `(owner_kind,owner_id,target_kind,target_id)`; reject duplicate four-tuples before sorting. Same target under different owners stays two items. |

FROZEN-PROPOSAL hashing uses existing `canonical_json_bytes` / `sha256_canonical_json`: compact UTF-8, sorted object keys, `ensure_ascii=False`, no separator whitespace, not RFC 8785. These new closed materials contain only null/bool/integer/string/list/object values; no float field is admitted. Preserve saved input hashes and owning schemes, including explicit NULL, without invention. Current task input rows require non-NULL hashes; a synthetic NULL-hash serialization vector does not authorize an invalid DB input. Empty input set is `[]`. Sealed typed input rows remain the concrete FK truth, not the digest or JSON list.

FROZEN-PROPOSAL harness binding reuses the delivered HarnessManifest v1 (`src/researchbase/agent_runtime/domain/harness_manifest.py:26–81`), with exactly `schema_version`, `researchbase_revision`, `agent_runtime_revision`, `model_profile_id`, `prompt_template_version`, `agents_md_sha256`, `config_sha256`, `strategy_id`, `strategy_revision`, `skills`, `plugins`, `adapters`, `hooks`, `mcp_capabilities`, `reference_libraries`. Collection entries have `id`, `revision`, `content_sha256`, `ordinal`; keep S1's immutable-pin and ordinal/uniqueness rules and normalized value behavior unchanged. Resolve material executable pins; reference-only libraries stay reference-only.

Verify retained artifact byte hash and size before locks; check frozen same-project artifact/version pins inside. The saved `harness_content_hash` is the actual retained-byte SHA-256 (`sha256-bytes-v1`), distinct from the normalized manifest-value digest (`sha256-cjson-v1`); whitespace-different retained JSON may have equal normalized values but different byte hashes. `src/researchbase/foundation/hashing.py:10,26–35` defines these existing scheme names. A new harness binding needs a new intent; never update an old binding. No artifact or AGENT_POLICY snapshot is created by intent.

FROZEN-PROPOSAL independent vector ledger retains r2 IDs to prevent deferred work disappearing. Every expected-output cell remains blank and every status is **NOT YET COMPUTED**. Active vector inputs/bytes/digests or rejection expectations must be independently specified before intent freeze: publish literal fixtures and script/source identity, use an independent standard-library implementation, and do not import the proposed serializer/SQL functions or copy actual stored output as expected. Deferred vector computation belongs to §2's later slice, not an intent acceptance requirement.

| Vector | Intent disposition / literal requirement | Expected output | Status |
| --- | --- | --- | --- |
| V01 | ACTIVE: create envelope, fixed UUIDs, NULL expected_revision/step, expected_task_revision=1 | | NOT YET COMPUTED |
| V02 | DEFERRED Q1/Q4: RUNNING transition request | | NOT YET COMPUTED |
| V03 | DEFERRED Q1/Q4: SUCCEEDED result/trace/memory request | | NOT YET COMPUTED |
| V04 | DEFERRED Q4/Q6: question promotion material | | NOT YET COMPUTED |
| V05 | DEFERRED Q4/Q5: hypothesis/AGENT_POLICY promotion material | | NOT YET COMPUTED |
| V06 | DEFERRED Q4: normalized caller reason/rationale; intent uses only a server event literal | | NOT YET COMPUTED |
| V07 | ACTIVE intent subset: unknown create key, bool/float task revision, duplicate JSON keys, unsupported cjson numeric value and SQL NULL helper input; 22023 diagnostic. The SQL helper case is required and must match the Python rejection. Other text/summary rejection cases DEFERRED Q4. | | NOT YET COMPUTED |
| V08 | ACTIVE: reversed task/selected-step input order, same target under distinct owners, duplicate four-tuple rejection | | NOT YET COMPUTED |
| V09 | ACTIVE: saved NULL scheme, synthetic NULL hash, empty inputs and absent step; serialization versus DB admission distinction | | NOT YET COMPUTED |
| V10 | DEFERRED Q4/Q6: candidate ordering/selector/adaptation | | NOT YET COMPUTED |
| V11 | DEFERRED Q4/Q6: B02 envelope/capture material | | NOT YET COMPUTED |
| V12 | DEFERRED Q4: execution output/invocation digest | | NOT YET COMPUTED |
| V13 | ACTIVE: same normalized harness with different retained whitespace; separate byte/value hashes | | NOT YET COMPUTED |
| V14 | ACTIVE: harness ordinal order, changed pin, duplicate/noncontiguous ordinal, mismatched retained byte pin | | NOT YET COMPUTED |
| V15 | DEFERRED Q4/Q5: AgentPromotionPolicySnapshot | | NOT YET COMPUTED |
| V16 | DEFERRED Q1/Q4: new-mode gateway material; existing gateway material stays untouched | | NOT YET COMPUTED |
| V17 | DEFERRED Q1/Q4: FAILED/CANCELLED partial results | | NOT YET COMPUTED |
| V18 | ACTIVE regression obligation: existing S1/B02/scientific literal fixtures unchanged, no replacement digests | | NOT YET COMPUTED |

### Q5 — FROZEN-PROPOSAL: intent caller, reads and exact replay

`READ`: verified principal with currently live credential/subject binding, unretired actor, ACTIVE project membership and current OWNER/RESEARCHER/REVIEWER/APPROVER/VIEWER role. Wrong-project denial precedes disclosure. Archived projects can retain READ. Local credential verification and durable entitlement checks are separate and both required; no caller string/role in a DTO is trusted.

`S2_INTENT_CALLER`: READ plus ACTIVE project and either (a) authenticated HUMAN with current OWNER or RESEARCHER role, or (b) the exact `agent_versions.actor_id` AGENT, S1-enrolled in this project with live MTLS_URI binding and current RESEARCHER role. No other Agent, SERVICE or EXTERNAL caller may create this intent. Full create admission additionally requires live intended Agent, ACTIVE version, exact sealed PLANNING task/current revision, optional same-task PENDING step and verified input/configuration/harness pins. Authority is rechecked after waits and before effects/commit. No new controller is selected/stored; the later controller work is in §2.

| FROZEN-PROPOSAL case | Outcome |
| --- | --- |
| HUMAN OWNER or HUMAN RESEARCHER satisfies full create predicate | Admit three intent effects; do not require the RESEARCHER to be an OWNER. |
| Bound version Agent RESEARCHER satisfies full create predicate | Admit the same command/effects through the common Application boundary. |
| Other Agent, revoked caller, no current role, wrong project | FORBIDDEN before receipt/existence/hash conflict disclosure; zero effects. |
| Untrusted principal | AUTHENTICATION_REQUIRED; zero effects. |
| New intent with unavailable version, task not sealed PLANNING, selected step not PENDING | INVALID_STATE_TRANSITION; zero effects. |
| New intent with stale expected_task_revision | CONCURRENT_MODIFICATION; zero effects. |
| Current READ; same project/caller/command and same normalized hash | Return original receipt/intent/event/revision 1, `replayed=true`, even after version retirement, project archive, task cancellation or task revision advance. No current write/CAS/availability gate is reapplied. |
| Current READ; same receipt identity, changed normalized material | IDEMPOTENCY_CONFLICT before new-write admission, including changed expected task revision. |
| Different caller tries to replay original caller's receipt | FORBIDDEN; command identity never impersonates the original caller. A separate entitled intent query is not replay. |
| Lost response or uncertain commit | Reconcile original identity in a single formal-read snapshot, without repair or new IDs. |
| Read after intent's future task/availability changes | Retain saved task_revision_at_creation and frozen pins; any separately labeled current facts cannot replace the saved intent. No claim to see revocation occurring after snapshot creation. |

FROZEN-PROPOSAL `AgentCommandResult` preserves existing S1 fields and adds only `result_execution_id`, `result_execution_event_id`; for intent, all S1 result links are explicit NULL, operation=create_agent_execution, resulting_revision=1, and receipt_id/recorded_at/replayed have their established meanings. No result_promotion_id/output link is introduced. `AgentExecutionDTO` contains exactly Q3.1 intent fields and the ordered initial-event DTO; it carries no result artifacts, producer claims, controller or newly computed execution-enabled projection. Existing PR3-01 `execution_enabled` remains unchanged and false. `get_agent_execution` uses project/execution ID; `list_task_executions` uses project/task, ascending intent ID, limit 1..100/default 50 and explicit nullable after_id cursor. Queries and exact receipt reconciliation use one entitled formal-read snapshot.

### Q6 — disposition: producer-attribution work is deferred

No S2 capture, output, invocation or scientific target exists to attribute. An intent's Agent/version binding describes intended work only. The complete Q6 question and every proposed adjunct/guard/mapping move to §2. Existing B02 standalone operations, hashes, receipts and public readback shapes remain unchanged. No promotion/B02 seam extraction or ArtifactStore preflight relocation is needed for intent.

### Q7 — retained decision: PR3-05 preview unchanged

Apply Answers:136–142 and the binding owner instruction. Retain the validator and `S2_PRODUCER_PROVENANCE_UNVERIFIED`; no producer-read extension. Neither a preview nor an intent authorizes promotion, saving, D1 or D2-C.

### Q8 — retained process: review, freeze and separate authorization

Apply Answers:144–150: no missing authorization brief is invented. Two independent director reviews must assess **this same r3 intent-only pack**, resolve all P0/P1, confirm prerequisites including the PR3-04 CI-green condition, record the narrowed freeze, and obtain separate explicit intent-only S2 implementation authorization. The review count comes from the answer set's owner instruction; A:3–5 literally assigns two reviews to S1 and separate prerequisites/authorization to S2. Neither review B's PASS on r2 nor a PR3-04 waiver transfers to r3. No ADR amendment to open D:77–82 is requested or implied by option B.

## 4. FROZEN-PROPOSAL implementation allocation and focused evidence

All stages, paths and test names in this section are future planning proposals, **NOT AUTHORIZED / NOT RUN** against an S2 implementation. No proposed node is an observed count. Preserve evidence of exact commands, stdout/stderr, exit code, collected/passed/failed/skipped counts, database version/role and effect counts. Required skips or zero selection do not pass a gate. Stop on authority/diff conflict, quote the exact rule and location, and revise the scoped pack rather than silently expanding it. Do not weaken governing Harness, historical migrations or frozen vectors.

The original S0–S7 identifiers remain recognizable; r2's lifecycle/capture work in S4 is removed and S5's promotion work is deferred in §2. Active order is **S0 → S1 → S2 → S3 → S4 → S6 → S7 → external check loop / independent review → owner acceptance → STOP**. Each implementation stage has one construction pass and one focused verification/remediation pass; missing evidence is a dependency, not a reason to skip the check. Review/CI/owner response time is not bounded by that allocation.

| Stage | Scope/files (FROZEN-PROPOSAL) | Checks available at this stage |
| --- | --- | --- |
| S0 | Review/freeze r3 intent scope, active independent vectors, Q3 exact delta/diagnostics, prerequisite confirmation and separate authorization. Current task writes only this pack. | Documentation checks only; does not pass implementation gates. |
| S1 | Future `migrations/versions/<H>.py`, narrow persistence models/receipt union changes, schema/guard/migration tests. Exactly two intent tables and receipt extensions. Mechanical current-head consumers only as Appendix H. | M1–M3 and G1–G2; compile all SQL on real PG18; normal-role completeness/immutability and S1 receipt compatibility. G3 Python/SQL parity waits for S2. |
| S2 | Proposed `agent_runtime/domain/agent_execution.py`, `agent_runtime/application/execution_contracts.py`, narrow `agent_contracts.py` additions; reuse existing HarnessManifest. Under `src/researchbase/`. | U1–U3 plus G3 now that both serializers exist. No service/repository tests before their files exist. |
| S3 | Proposed `agent_runtime/ports/execution_repository.py`, `persistence/agent_execution_repository.py`, narrow `persistence/uow.py` Agent translator/factory wiring; no gateway/B02 composition. Under `src/researchbase/`. | L1–L3. Actual database waits R1–R2 require S4's Application path. |
| S4 | Proposed `src/researchbase/agent_runtime/application/agent_executions.py`: create intent only, Human/Agent common boundary, atomic receipt→intent→event, no transitions. | E1–E3 and R1–R2; service unit tests; actual first-prefix/key/row waits, post-wait authority and three-effect rollback. |
| S5 | **DEFERRED Q2/Q3/Q5/Q6**, no executable step in r3. | Promotion/capture/output/AGENT_POLICY checks are not selected or counted as passing. |
| S6 | Intent queries/exact replay/reconciliation in the above proposed service/repository; no promotion query. | R3–R5; PR3-05 preview regression, read-only snapshot/entitlement evidence. |
| S7 | Proposed `tests/architecture/test_pr3_02_s2_boundaries.py`, disposable execution fixtures and future `docs/phase3/PR3-02-S2-evidence.md`. | A1, all active nodes and complete focused commands below, affected existing regressions; external loop supplies full-suite evidence. |

### FROZEN-PROPOSAL node inventory

Unit filenames below are under `tests/unit/phase3/`; PostgreSQL filenames under `tests/integration/phase3/`. None exists by virtue of this pack. Node IDs G1–G3 are schema checks and are unrelated to deferred PR3-05 design decisions D1/D2.

| ID | Proposed node | Required observation |
| --- | --- | --- |
| U1 | test_agent_execution_contracts.py::test_closed_intent_command_and_literal_vectors | Only create accepted, explicit nulls/defaults, strict scalar types, independent active Q4 vectors, helper 22023 parity. |
| U2 | test_agent_execution_contracts.py::test_intent_binding_and_harness_pins | Sealed task/selected-step set ordering/duplicate rejection; retained bytes versus normalized harness digest; unresolved/changed pins. |
| U3 | test_agent_execution_contracts.py::test_intent_query_and_receipt_shapes | Immutable typed read DTO, safe fields, original event/revision, bounded pages, no promotion/result/controller fields. |
| L1 | test_agent_execution_repository.py::test_ordered_intent_prefix_and_keys | First Application SQL exact 23-table SHARE; project/command/actor/task/version/execution order; applicable row order; no linked gateway/B02 seam. |
| L2 | test_agent_execution_repository.py::test_fresh_checks_after_each_wait | Advancing time and durable rereads after prefix/key/row/write/constraint waits; no ArtifactStore or external I/O under locks. |
| L3 | test_agent_execution_repository.py::test_formal_read_has_one_readonly_snapshot | Exactly one REPEATABLE READ READ ONLY snapshot, no locks/autoflush/writes/second session. |
| M1 | test_pr3_02_s2_migration.py::test_empty_upgrade_and_single_head | Actual baseline receipt CHECK names/definitions, exact approved catalog delta, compiled functions, sole H head/parent. |
| M2 | test_pr3_02_s2_migration.py::test_populated_upgrade_preserves_history | All old IDs/hashes/receipts/trace remain; no backfilled intent, capture link, mode or policy. |
| M3 | test_pr3_02_s2_migration.py::test_downgrade_refuses_before_change | Empty/populated refusal with no data/catalog/revision change. |
| G1 | test_pr3_02_s2_schema.py::test_exact_intent_schema_and_scoped_foreign_keys | Two tables/two receipt links only; project/task/step/actor/version/harness scope; explicit digest schemes. |
| G2 | test_pr3_02_s2_guards.py::test_normal_role_intent_closure_and_receipt_predicates | Reject partial/no-op/update/delete/late history; one receipt-root check; valid HUMAN RESEARCHER and exact Agent create; S1 still HUMAN OWNER-only, both insertion and final checks; each function/tag mapping. |
| G3 | test_pr3_02_s2_schema.py::test_python_postgresql_intent_material_parity | Literal inputs/bytes/digests and helper type-error SQLSTATE agree independently; no S1/B02/scientific hash drift. |
| E1 | test_pr3_02_s2_execution.py::test_created_intent_through_common_application_boundary | Application-enrolled Agent and entitled Human each create CREATED/revision 1 with exact task revision and initial event; zero task/gateway/scientific effects. |
| E2 | test_pr3_02_s2_execution.py::test_intent_denials_preserve_closed_execution_gate | Wrong caller/scope, stale revision, unfrozen pins, unavailable version; no transition/promotion command and unchanged PR3-01 execution_enabled/PR3-03 behavior. No new autonomy filter; if existing ceiling validated, equality remains allowed. |
| E3 | test_pr3_02_s2_execution.py::test_intent_failure_rolls_back_all_three_effects | Failure after receipt, intent, event, final constraint or credential recheck leaves zero intent/event/receipt effects. |
| R1 | test_pr3_02_s2_concurrency.py::test_observed_wait_rechecks_intent_authority | Actual first SHARE/key/row waits across credential/membership/source-link revocation and availability change; fresh checks, zero effects on denial, separate second-wait expiry proof. |
| R2 | test_pr3_02_s2_concurrency.py::test_same_command_revision_and_existing_writer_races | Same command/occupied intent/task revision races plus coexistence with unchanged task/S1/gateway/Phase 2 writers; one coherent result or bounded sanitized failure. No linked invocation or B02 promotion work. |
| R3 | test_pr3_02_s2_replay.py::test_saved_intent_after_loss_and_uncertain_commit | Original IDs/material, no duplicates; bounded 40001/40P01 retries and no automatic timeout retry. |
| R4 | test_pr3_02_s2_replay.py::test_current_entitlement_precedes_intent_disclosure | Archive/retirement/cancelled task/stale revision exact replay versus revoked/wrong-caller denial and changed-hash conflict. |
| R5 | test_pr3_02_s2_replay.py::test_queries_are_coherent_bounded_snapshots | Ordered bounded pages/initial event; concurrent writer cannot split one read snapshot; saved task revision is historical. |
| A1 | tests/architecture/test_pr3_02_s2_boundaries.py::test_intent_only_application_boundary | Human/Agent common boundary; no runtime ORM/vendor dependency, generic primary refs, gate switch, gateway/capture/promotion/controller/snapshot implementation. |

At each implementation stage run the existing static checks and only the already-implemented nodes allocated there. M1–M3/G1–G2 do not depend on Python material parity; G3 starts at S2, real Application races at S4, replay at S6, combined runs at S7. Do not invoke combined commands containing files from a later stage. Required checks deferred to a later stage of intent implementation remain required; features in §2 remain outside this slice entirely.

FROZEN-PROPOSAL complete S7 commands, after separate authorization and creation of all active files; **NOT RUN against an S2 implementation**:

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
git diff --check HEAD
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run alembic heads
uv run pytest -o addopts='' -ra tests/unit/phase3
uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_02_s2_schema.py tests/integration/phase3/test_pr3_02_s2_guards.py tests/integration/phase3/test_pr3_02_s2_migration.py
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_02_s2_execution.py
uv run pytest -o addopts='' -ra -s tests/integration/phase3/test_pr3_02_s2_concurrency.py tests/integration/phase3/test_pr3_02_s2_replay.py
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_01_*.py tests/integration/phase3/test_pr3_02_s1_*.py tests/integration/phase3/test_pr3_03_*.py tests/integration/phase3/test_pr3_04_*.py
uv run pytest -o addopts='' -ra tests/integration/phase2/test_b02_*.py tests/integration/phase2/test_b03_*.py
uv run pytest -o addopts='' -ra tests/integration/phase3/test_pr3_05_promotion_validation.py
```

Use real disposable PostgreSQL 18 and normal-role constraint tests, never SQLite or an ambient DB. Configure `RB_TEST_ADMIN_URL` through existing plumbing without printing credentials; fixtures select the disposable `DATABASE_URL` (`tests/disposable_postgres.py:1–53`; `tests/integration/phase3/agent_fixtures.py:100`). Include the exact affected historical migration/catalog nodes in Appendix H once H exists. For expiry races record transaction/wait/acquisition/authorization DB times and observe actual blocking; sleeps alone are not evidence (`docs/architecture/02_Final_Architecture_Correction_Addendum_v1.0.md:418–420`). No full-suite run by the implementing agent; attach the external loop's command/counts when supplied. No S2 acceptance or Phase 3 exit claim with missing evidence or open P0/P1.

## Appendix H — FROZEN-PROPOSAL future head maintenance

The following baseline inventory is carried from Answers:171–203. H remains an unnumbered future head, parented to `0080_capability_gateway` only if that is still the current reviewed head. These are future mechanical edits, not files authorized for this planning task. The exact catalog allowance must match this **two-table intent delta**, not r2's four-table/gateway/capture proposal. Reconfirm the inventory against the eventual authorized diff; retain historical migration targets and byte/hash pins.

| Active reference (file:line) | Update when intent implementation is authorized |
| --- | --- |
| .github/workflows/ci.yml:66 | Expected head → H (head). |
| tests/fixtures/phase2_static_baseline.json:4 | Only migration_head → H; preserve commit/type-check data. Consumer: tests/unit/phase2/test_pr2_04_static_acceptance.py:32–35. |
| tests/architecture/test_basic_approval.py:55 | Sole repository head → H. |
| tests/architecture/test_b04_boundaries.py:43 | Sole repository head → H. |
| tests/architecture/test_b20_screening_boundaries.py:32 | Sole repository head → H. |
| tests/architecture/test_b02_strategy_promotion_boundaries.py:77 | Sole repository head → H. |
| tests/architecture/test_b05_review_boundaries.py:76 | Sole repository head → H. |
| tests/architecture/test_pr3_02_s1_boundaries.py:12 | Sole repository head → H; preserve S1-specific exclusions. |
| tests/architecture/test_import_boundaries.py:198–199 | Append H filename; retain 0080. |
| tests/unit/test_task12_migration_history.py:61–65 | Append filename/expected H; retain historical SHA-256 pins. |
| tests/unit/test_batch_c_migration_history.py:42–46 | Append H and validate parent edge; retain previous 0080 child. |
| tests/unit/phase2/test_pr2_04_r8a_host_topology.py:38 | Sole repository head → H; historical topology/bytes unchanged. |
| tests/unit/phase2/test_pr2_20_inventory.py:54 | Final inventory revision → H. |
| tests/integration/phase2/test_pr2_04_execution_migration.py:73 | Repository head → H; historical DB REVISION stays. |
| tests/integration/phase2/test_pr2_04_migration_coverage.py:144,273 | Both repository-head assertions → H. |
| tests/integration/phase2/test_pr2_17_authorship_schema.py:61 | Sole repository head → H. |
| tests/integration/phase2/test_pr2_03_review_guards.py:572 | Sole repository head → H. |
| tests/integration/phase2/test_pr2_15_decision_schema.py:60 | Sole repository head → H. |
| tests/integration/phase2/test_revision_action.py:509 | Sole repository head → H. |
| tests/integration/phase3/test_pr3_00_bootstrap.py:101 | Sole repository head → H. |
| tests/integration/phase3/test_pr3_01_migration.py:37 | Repository head → H; historical upgrade stays. |
| tests/integration/phase3/test_pr3_02_s1_migration.py:56 | Repository head → H; explicit 0079 fixture/absence checks stay. |
| tests/integration/phase3/test_pr3_03_migration.py:77 | Repository head → H; test DB still targets historical 0080. |
| tests/integration/phase3/test_pr3_04_migration.py:120 | Repository head → H; historical 0078 checks stay. |

`tests/unit/test_ci_migration_head.py:12–21` reads the head dynamically; rerun unchanged rather than treating it as a hard-coded 0080 string. `tests/integration/phase2/pr2_20_support.py:32–184` and `test_pr2_20_migrations.py:187–192` require an exact named catalog delta, not a broad ignore/filter. Future changes to scope assertions at `tests/architecture/test_pr3_03_boundaries.py:169` and `test_pr3_02_s1_boundaries.py:10` must allow only the reviewed intent surfaces, never promotion/gateway linkage.

Historical references remain: `tests/integration/phase3/gateway_fixtures.py:48`; `test_pr3_03_migration.py:53,64–65,121,139,334`; `tests/unit/phase3/test_capability_gateway_repository.py:410`; 0080 revision/parent/downgrade refusal at 0080:5–6,3453–3454; the explicit 0079 fixture in `tests/integration/phase3/test_pr3_02_s1_migration.py:15–32,55`; accepted evidence/pack head statements. No file in this appendix is changed now.

## 5. Review disposition and remaining gates

This is an authoring disposition, not an independent-review verdict.

| Finding | r3 treatment |
| --- | --- |
| Review A P1: closed-gate contradiction | Q1 quotes D:77–82 and preserves them under option B; no parallel admission, RUNNING or gateway change. Full roadmap obligations moved with their implementation to §2. |
| Review A P2: receipt OWNER assumption | Q3.4 cites actual unconditional 0079:216–228 and also 458–466; both predicates become S1-operation-only. Named S2_INTENT_CALLER includes HUMAN RESEARCHER and exact bound Agent. |
| Review A P2: autonomy ceiling | Q1 uses **at or below**, cites 0078:495 and limits applicability to existing task-policy consistency; no intent dispatch policy. |
| Review A P2: diagnostics/foreign translations | Q3.5 maps each raised tag to function, SQLSTATE and service. Pure-helper errors explicitly use 22023. Foreign service paths are unchanged because their new triggers/linkage are deferred, not assumed to translate new tags. |
| Review A P2: overlapping invocation triggers | Neither S2 link trigger nor pr303 replacement is in the active delta. No name-order dependency remains. |
| Review A P2: conditional PR3-04 acceptance | CI-green fulfilment is an explicit OPEN prerequisite, not merely missing counts. |
| Review A P3: write order/owning-command receipt link | Single receipt→intent→event order; per-command match belongs to receipt-root closure. Owning B02 command linkage is deferred Q6, not asserted as an existing receipt column. |
| Review A P3: non-SQL CHECK predicates | Q3.3 contains literal row-local SQL; cross-row scope/closure lives in named guards. Lifecycle error/text fields are deferred. |
| Review A P3: digest schemes | Q3.1 stores explicit input/harness schemes; existing receipt scheme remains. |
| Review A P3: promotion→capture project FK | Explicitly deferred Q3/Q6; no promotion/capture FK is installed or accepted here. |
| Review B P2: unsupported check-result claim | §6 reports commands with observed output/exit codes; any unrecorded content check stays unevidenced. No inherited claim that a content scan passed. |
| Review B P2: baseline timings | §6 identifies this lane230 independent rerun by date/commit; distinguishes the answer-set timings and does not silently copy r2's differing numbers. |
| Review B P3: startup timeouts | Q2 names reuse of the already-existing B02 startup-timeout factory; linked capture remains deferred. |
| Review B P3: citation scope/call layer | §1 limits the acceptance citation to S2/D1/D2/full PR3-05; Q2 cites gateway's actual call path as well as its inventory. |

Open intent prerequisites are: active Q4 independent vector outputs (**NOT YET COMPUTED**); two independent reviews of r3/no open P0/P1; confirmed PR3-04 green accepted-head CI with results/counts; recorded intent-only freeze and separate implementation authorization. H's concrete revision identifier and baseline CHECK catalog confirmation remain pending before the future migration can be accepted. Proposed SQL compile/normal-role/race evidence remains NOT RUN, not DDL-readiness evidence. Production Agent verifier intake remains pending as described in `docs/phase3/PR3-02-S1-evidence.md:40–44`; unconfigured verification fails closed. No deferred feature in §2 becomes an implicit prerequisite to intent implementation.

## 6. Verification of this planning-only revision

Environment for every tooling run: `export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"`. Only this Markdown file is a source deliverable; generated ignored environment/cache state is not a code/dependency edit. The original and r2 are not edited. No commit/push/branch creation is performed.

Focused baseline checks below are a **new independent lane230 rerun on 2026-10-25 at 27dc60e1765b15434dda0e21544427aed0d3a21a**, not borrowed S2 evidence. Answers:26–27 recorded 9.83 s / 21.80 s for its own unit/architecture runs. The times below are this run's observed 9.81 s / 23.28 s. r2's 9.85 s / 23.27 s are not adopted or relabeled as answer-set evidence.

| Exact command | Observed stdout/result | Exit code |
| --- | --- | --- |
| `uv sync --locked --group dev` | Resolved 38 packages; prepared/installed 34; existing lock used | 0 |
| `uv run ruff check .` | `All checks passed!` | 0 |
| `uv run ruff format --check .` | `931 files already formatted` | 0 |
| `uv run pyright` | `0 errors, 0 warnings, 0 informations`; separate newer-version notice (1.1.411 → 1.1.414), no upgrade | 0 |
| `uv run alembic heads` | `0080_capability_gateway (head)` | 0 |
| `uv run pytest -o addopts='' -ra tests/unit/phase3` | `collected 1027 items`; `1027 passed in 9.81s`; 0 failed/skipped | 0 |
| `uv run pytest -o addopts='' -ra tests/architecture tests/unit/architecture` | `collected 371 items`; `371 passed, 50 warnings in 23.28s`; 0 failed/skipped; warnings are existing Alembic path_separator deprecations | 0 |

Required documentation commands, with the specified cache environment:

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
git diff --check HEAD
test -s docs/phase3/PR3-02-S2-execution-pack-r3.md && echo r3-present
```

Observed raw output for `git diff --check HEAD` is empty (no stdout/stderr); exit code **0**. Observed raw output for `test -s docs/phase3/PR3-02-S2-execution-pack-r3.md && echo r3-present`, exit code **0**:

```text
r3-present
```

The file is untracked, so `git diff --check HEAD` alone does not inspect its content. The additional read-only content/whitespace check is:

```sh
export UV_CACHE_DIR="$PWD/tmp/pr3-03-uv-cache"
.venv/bin/python - <<'PY'
from pathlib import Path
import re
import subprocess
p = Path('docs/phase3/PR3-02-S2-execution-pack-r3.md')
s = p.read_text()
assert s.endswith('Status: DRAFT r3 (intent-only) — awaiting independent review.\n')
assert all(line == line.rstrip() for line in s.splitlines())
d = Path('docs/proposals/PR3-02_AgentVersion_Execution_Contract_DRAFT.md').read_text().splitlines()
assert '\n'.join('> ' + line for line in d[76:82]) in s
rows = [line for line in s.splitlines() if re.match(r'^\| V\d{2} \|', line)]
assert len(rows) == 18
assert all(line.split('|')[3].strip() == '' and line.split('|')[4].strip() == 'NOT YET COMPUTED' for line in rows)
assert subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], text=True) == ''
assert subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard'], text=True).splitlines() == [str(p)]
print('r3-content-check: exact D quote; 18 uncomputed blank vectors; final status; no trailing whitespace; only r3 untracked; tracked files unchanged')
PY
```

Content-check exit code: **0**. Raw output:

```text
r3-content-check: exact D quote; 18 uncomputed blank vectors; final status; no trailing whitespace; only r3 untracked; tracked files unchanged
```

An initial form of this same script used `line.startswith('| V')` without the regex import and exited **1** with `AssertionError` at `assert len(rows) == 18`: that selector also selected the `| Value |` table heading. The corrected selector above matches only numbered vector rows; no vector value was changed or computed to satisfy it.

PostgreSQL suites: **NOT RUN** for this documentation-only change; no executable/database contract is edited and no PostgreSQL suite is touched. Future S2 PostgreSQL, unit nodes, vectors and mixed-order concurrency proofs remain **NOT RUN / NOT YET COMPUTED** as applicable. Full suite: **NOT RUN by this agent**; the external loop owns that evidence. These baseline passes do not pass an S2 freeze, implementation or acceptance gate.

Status: FROZEN 2026-10-25 for the intent-only S2 slice (owner-approved). Implementation is
authorized only for the intent-only scope in section Q1; deferred items remain unauthorized.

## Freeze record

- Review: `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/reviews/s2_r3_review_A.md` — `VERDICT: PASS`.
- Review: `/Users/fengwang/Documents/ResearchBaseProject/.pipeline/logs/reviews/s2_r3_review_B.md` — `VERDICT: PASS`.
- Owner approval: Owner approved the freeze of r3 (intent-only S2).
- Source commit: `27dc60e`.
- r3 source file line count: 582.

### Refreeze 2026-10-25 (numeric boundary, option B)

Owner decision (binding): option B. Python rejects any non-integer or out-of-profile JSON number before JSONB conversion; SQL `pr302s2_cjson` rejects the same set with `ERRCODE='22023', CONSTRAINT='pr302s2_value_type'`, including for a normal-role direct SQL writer. PostgreSQL comparison of both layers' rejection of the same inputs is required evidence.

Lines changed: Q3.5 line 302 (numeric/scalar rejection paragraph); V07 line 346 (required SQL helper parity); this appended freeze record, lines 593–606. No other conflicting sentences were found; the previous Q3.5 already required SQL helper rejection but did not explicitly state the Python pre-conversion rule.

Changed sentences (old → new):

1. Old: FROZEN-PROPOSAL pure-helper errors are specified, not left implicit: passing a float/nonintegral JSON number, a numeric representation outside the closed integer profile, SQL NULL instead of an explicit JSON value, or another unsupported value to `pr302s2_cjson` raises `ERRCODE='22023', CONSTRAINT='pr302s2_value_type'`.
   New: FROZEN-PROPOSAL numeric boundary (owner decision, option B): both layers reject unsupported numeric values with the same rule. The Python layer rejects any non-integer or out-of-profile JSON number before conversion to JSONB. The SQL helper `pr302s2_cjson` rejects the same set with `ERRCODE='22023', CONSTRAINT='pr302s2_value_type'`; a normal-role direct SQL writer therefore cannot bypass the rule. Passing SQL NULL instead of an explicit JSON value, or another unsupported value to `pr302s2_cjson`, also raises `ERRCODE='22023', CONSTRAINT='pr302s2_value_type'`.
2. Old: Independent numeric/type rejection vectors must prove Python/SQL parity.
   New: Independent numeric/type rejection vectors must prove Python/SQL parity: the two layers must reject the same inputs, and a PostgreSQL test must compare them as required evidence, not optional coverage.
3. Old: ACTIVE intent subset: unknown create key, bool/float task revision, duplicate JSON keys, unsupported cjson numeric value and SQL NULL helper input; 22023 diagnostic.
   New: ACTIVE intent subset: unknown create key, bool/float task revision, duplicate JSON keys, unsupported cjson numeric value and SQL NULL helper input; 22023 diagnostic. The SQL helper case is required and must match the Python rejection.
