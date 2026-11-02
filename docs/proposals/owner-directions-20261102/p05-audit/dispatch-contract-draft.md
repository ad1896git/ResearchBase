PROPOSED / NON-NORMATIVE / NO IMPLEMENTATION AUTHORITY

Source baseline: `7540438a4d4c1e58af8872dc8c6c18cb07fdb2f2`. This is the P05 docs-only preparation child, not a scientific contract freeze, architecture change, executable packet, facility authorization or whole-P05 completion. Parent risk stays HIGH. OBSERVED_SOURCE means inspected static code; HISTORICAL_ACCEPTANCE means a cited acceptance record, not a new test. All proposed behavior below is PROPOSED. Environment, actual backend and independent review are UNVERIFIED/UNASSIGNED_OWNER_INPUT.

# First-consumer dispatch and unknown-outcome contract candidate

## 1. Ownership/allocation

Start with **DO NOT ADD SCHEMA**. Phase3 §§45–49 recommends durable Application state, transactional dispatch and idempotency, while accepted ADR-0021 TDG3-05 selects PostgreSQL without Redis/separate broker. Reuse existing ResearchTask/Step ownership, typed CapabilityInvocation references, append-only invocation events, command receipts and reservation/usage ownership wherever their accepted contracts permit. Existing enum/event vocabularies cannot be extended by this document.

OBSERVED_SOURCE: `agent_runtime/application/agent_executions.py:1,289–317` creates a CREATED intent and initial event; it starts no work. `agent_runtime/application/capability_gateway.py:391–467` implements finite fake request/start/call/finish with replay refusing a second call. Those are existing pieces, not a delivered durable external dispatcher. `agent_runtime/domain/task_step.py:25–45` distinguishes admitted PENDING/CANCELLED from explanatory progress states; this draft grants no new state edge.

A task/step is work ownership; invocation is an admitted capability call; AgentExecution intent identifies intended execution; a backend handle identifies external work; a sealed scientific Run is owning scientific execution history. They are distinct. A handle, provider message, local pipeline ledger or model answer is never canonical scientific truth. Real Run creation/seal/result ingestion remains P12/owning Application commands.

PROPOSED allocation decision for later review: use immutable command/intent/event material plus current owning invocation projection for logical action and receipts. A claim must have an atomic compare-and-set owner/epoch. Before implementation, prove whether current accepted rows/events can represent it with typed referential closure and immutable history. If not, document the exact representational gap and obtain an owning operational schema/constraint decision. No new table/column name, generic target_type+id payload or migration is approved here. Historical evidence that gateway tables exist does not settle this allocation.

## 2. Proposed closed request/result material

PROPOSED request v1 is a typed record, not an arbitrary dictionary: project/task/step UUIDs; authenticated actor identity; existing invocation identity; original Application command identity; one stable logical action identity; exact versioned input reference tuple; request digest; exact policy/capability/adapter/registry/Harness pins; reservation identity; absolute UTC deadline; backend correlation key. An absent optional step must be explicit and justified by the eventual P06 contract. No fixture-created AgentExecution or ArtifactVersion identity fills a missing producer.

Candidate byte rule for review: domain-separated UTF-8 canonical JSON over an exact ordered field schema, SHA-256 lower-case hex digest, UUID canonical lowercase form, UTC integer microseconds, integers excluding bool, no float/NaN, explicit nulls, no unknown/duplicate keys, no implicit trimming/normalization. The field schema, ordering, text/list/byte limits and literal vectors are NOT FROZEN. Reuse an existing accepted digest helper only after proving exact compatible bytes; do not silently invent a second canonical encoding. Existing gateway FakeParameters and its 60-second bound (`gateway_contracts.py:50–110`) do not authorize P06 payloads or deadlines.

PROPOSED result/reconciliation record binds original logical action/request digest, original backend key, exact adapter/policy revision, observed handle if any, observation time, backend receipt bytes digest and bounded typed outcome/evidence references. Terminal observation differs from Application result-ingestion commit. Missing handle is explicit unknown, never synthesized. New outcome/ErrorCode literals and receipt bounds remain a later exact contract question.

Stable action identity survives transport retry, lease renewal, worker replacement and uncertain reply. A different command/request digest under the same action is a conflict; a new random ID is not a retry. Original full material and correlation key must remain durably recoverable before any external send. Existing typed reference families must resolve exact frozen, readable versions; no latest/current substitution.

## 3. Transaction and effect timeline

| Boundary | Proposed responsibility | Forbidden inference |
| --- | --- | --- |
| A | Entitled Application validates exact inputs, policy, revision and budgets | Context DTO or worker possession is not authority |
| B | One short owning TX persists original intent/correlation and authoritative reservation, then commits | Uncommitted intent does not authorize send |
| C | Short claim TX selects one current entitled owner/epoch using trusted DB time after waits | A stale local clock/expired lease does not prove old work stopped |
| D | Outside scientific TX, current owner requests the one controlled backend action with original idempotency key | A network timeout is not negative execution evidence |
| E | Separate entitled Application TX records observation/handle and original receipt closure | Provider success alone is not scientific success or settlement |
| F | Reconcile original backend key; ingest terminal result and authoritative usage separately | Local acknowledgement is not proof commit or canonical Run |

Each new Application command has its own transaction. Never keep a scientific transaction open across backend/network work. Ownership/admission rechecks must occur after lock waits and before claim or ingestion; replay first resolves the original receipt under current read entitlement. Existing gateway `invoke` is finite fake; it is not permission to substitute a real provider call.

## 4. Lease/fence proposal

PROPOSED claim scope is exact project/task/step/logical action, with one owner identity and monotonically increasing fencing epoch. Acquisition, renewal, revocation and reclaim must serialize in owning PostgreSQL transactions; trusted server time is sampled after relevant waits. TTL/heartbeat periods, exact lock ordering and claim algorithm are UNASSIGNED, not borrowed from engineering timer values. No process-local token alone grants durable unique execution right.

A renewed/reclaimed DB claim prevents new local dispatch only if the backend also enforces original action idempotency and the selected fencing contract. An old send can outlive a lease. If P06 cannot establish same-key query/reconciliation and duplicate suppression, reclaim must HOLD rather than start another job. Expiry/revoke fences new work; cancel is a request, not a confirmed stop. Never return reservation or authorize another execution merely because heartbeat disappeared.

## 5. Unknown-outcome matrix

| Failure window | Required recovery | Remains held until |
| --- | --- | --- |
| Before intent commit | Reconcile original Application receipt/digest | Definite rollback or original committed receipt is known |
| Commit reply lost | Read original receipt and reservation under current entitlement | Exact original outcome resolves; no new identity |
| Claim/dispatch marker saved, send not observed | Query original backend key; marker is not proof send happened or did not happen | Backend gives authoritative not-accepted or existing job evidence |
| Send accepted, reply/handle lost | Query original correlation key with exact backend identity | Existing job/receipt is found or authoritative safe-retry proof exists |
| Handle known, worker crashes | Poll/reconcile same handle/key; retain owner history | Terminal backend outcome and permitted ingest are known |
| Completion receipt lost | Recover exact original backend receipt and original digest | Result ingestion and accounting disposition resolve |
| Ingestion commit reply lost | Reconcile original Application receipt; do not re-dispatch | Exact original ingest/settlement is known |
| Cancel times out or late result arrives | Retain cancellation request, reconcile job and late outcome | Confirmed terminal/cancellation and ingestion policy resolve |

Absence from one read is never proof rollback/no execution. If backend history/key retention cannot resolve the original action, remain held and request owner disposition. No automatic second job, fabricated Run, expired-reservation refund or budget reset. Negative/failed scientific results are retained; retries do not erase them (Phase3 §25).

## 6. Accounting and immutable history

Reuse PR3-04 authoritative reservation/settlement and the gateway's trusted in-UoW accounting (`capability_gateway.py:127–217`); no second spend ledger. UNKNOWN retains the full reservation/charge pending entitled reconciliation. Exact eventual backend metering units, caps and settlement evidence must be reviewed against ResourceVector semantics. Neither engineering CLI quotas nor default pilot caps authorize new spend. Cancellation-requested and confirmed-cancelled evidence remain separate; late outcomes remain visible. Immutable scientific history is corrected by new events/records.

## 7. P03/P06 dependency contract

First prospective consumer is controlled CPU compute, not Coding/provider fallback. P03 is dedicated restricted Linux-container direction only: host, image/revision, mounts, UID, isolation, CPU/memory/disk/process/time bounds, secrets/network and budgets are UNASSIGNED. Mac development tests are not this scientific execution sandbox.

P06 must supply separately reviewed submit/poll/cancel/reconcile contracts, stable same-key duplicate behavior, fence support, exact negative acceptance evidence, handle/receipt retention, deterministic input/artifact pins, terminal/unknown taxonomy and metering. No infrastructure is installed here. No backend/provider/API credentials are selected. Source/source-of-truth and producer attribution remain separate. Real integration waits for accepted P03/P06 and exact implementation authorization.

## 8. Freeze questions and explicit holds

Before source: choose allocation/storage and migration necessity through owning review; freeze typed request/result bytes/bounds/vectors; action identity and receipt retention; claim/lease DB-time/lock/epoch rules; external idempotency/fence and safe-negative proof; cancellation/late outcome and accounting matrix; current-entitlement replay; exact UoW/port/adapter allowlist; real PG18 and approved P03/P06 verification facilities. No item is silently satisfied by this draft.

This preparation can reach an independently reviewed candidate only. P01 whole-audit receipt is an audit dependency, not proof full scientific execution exists. Automatic docs admission also waits for accepted live54 rollout and reviewed index activation. No parent completion, science freeze, dispatch, save, promotion or execution permission is issued.
