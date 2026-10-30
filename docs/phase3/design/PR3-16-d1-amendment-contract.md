# PR3-16 D1 — proposed paired bearing evaluation contract

Status: **PROPOSED for production; production activation blocked** pending commander review and the specific
proofs below. This replaces the 2026-10-27 question-only draft; historical versions
remain in version control. It is not a code authorization or an empirical result.
Authority: [ADR-0026](../../architecture/adr/ADR-0026-pr3-16-experiment-search-core.md),
[ADR-0029](../../architecture/adr/ADR-0029-pr3-16-minimal-storage-scope.md),
[ADR-0027](../../architecture/adr/ADR-0027-pr3-16-d1-node-budget-amendment.md),
[PR3-04 contract](../PR3-04-contract-freeze.md), and
[PR3-16 execution pack](../PR3-16-execution-pack-r2.md). The selections below are
proposed, not independent approval or evidence that existing code implements them. The separately accepted limited reference-only policy in O03 and O09 is subject to exact document diff review before publication; it authorizes no provisioning, implementation, revision allocation, migration apply, reference activation or production. Separate commander stage gates and actual facts are required, without duplicate user permission.

## O01 — producer and authority

Select a dedicated in-process ResearchBase core bearing-evaluation consumer, composed
at the Application root with an identity-only, nonserializable capability; never accept
a caller-provided identity, flag, GUC or remote credential as proof. The composition
owner registers exactly this implementation and evaluator digest at process startup,
performs bounded no-I/O capability identity and enabled-generation checks at admission
and settlement, and revokes by disabling that generation under the same coordination
used for fresh writes. The service operator owns restart/recovery and revocation; the
Application owns accounting. Missing registration, unsupported verifier, revoked or
mismatched generation denies. Current `FakeConsumerCapability` and
`TaskSafetyService._trusted` are fake-only, not production proof
([port](../../../src/researchbase/agent_runtime/ports/task_safety_repository.py),
[service](../../../src/researchbase/agent_runtime/application/task_safety.py)).
Concrete composition, coordination and authorized operator identity do not exist yet:
the implementation slice must establish and test them before activation, without a
new credential registry or third-party state owner.

## O02 — evidence and pure arithmetic

Inputs are frozen labeled samples, baseline and candidate predictions, protocol and
exact evaluator implementation, dataset snapshot and metric version. The following
nullable UUID columns on immutable `budget_reservations` are the proposed binding:

| Column | RESTRICT FK target | Role |
| --- | --- | --- |
| `labels_artifact_version_id` | `artifact_versions.id` | labels |
| `baseline_predictions_artifact_version_id` | `artifact_versions.id` | baseline predictions |
| `candidate_predictions_artifact_version_id` | `artifact_versions.id` | candidate predictions |
| `protocol_artifact_version_id` | `artifact_versions.id` | protocol |
| `evaluator_artifact_version_id` | `artifact_versions.id` | evaluator implementation/package manifest |
| `dataset_snapshot_id` | `dataset_snapshots.id` | dataset |
| `metric_definition_version_id` | `metric_definition_versions.id` | score definition |

Also add nullable UUID `consumer_generation`, durable attribution only, never an
authority credential. Legacy reservations have all eight columns NULL; v2 reservations
have all eight non-NULL. Enforce both shape and command ownership at deferred completion,
including direct SQL. The existing immutable reservation guard prevents UPDATE/DELETE;
usage inherits the tuple through its existing reservation FK, without copied binding.
Legacy settlement cannot settle a v2 reservation, including UNKNOWN reconciliation.
No source Run columns: an association cannot prove production of prediction bytes, and
this operation does not execute a Run. No new table or generic JSON semantic core.

At admission resolve each artifact through `artifact_versions.artifact_id` to
`artifacts.project_id`, require the task project, `status = 'FROZEN'`, nonnull
`frozen_at` and `content_hash`, and match the material hash to that stored canonical
hash using DB metadata only. Admission performs no ArtifactStore reads or byte-hash
verification; stored metadata does not prove bytes were read.
Resolve metric through `metric_definition_versions.metric_definition_id` to
`metric_definitions.project_id`; require the same project, `status = 'FROZEN'`,
nonnull `frozen_at` and `content_hash`, verify the owner's hash and require the
actual definition and policy metric to describe this score. Resolve snapshot through
`dataset_snapshots.dataset_id` to `datasets.project_id`, require the same project and
verify its `manifest_hash` and `content_hash` under the existing owner contract.
DatasetSnapshot is immutable and has no status or FROZEN field. Owner hashes retain
their existing definitions: ArtifactVersion hashes exact bytes; snapshot content hash
covers its manifest hash and selection definition. Material references those hashes;
it does not redefine them. Metric/snapshot owner-hash checks use their canonical DB
fields, without content I/O. Admission also compares the evaluator hash with the
registered composed implementation digest through bounded no-I/O checks; a matching
digest alone does not establish trust. Recheck metadata and exact binding after
waits and at deferred completion, never by reading bytes under DB locks.

Only after admission commits does the consumer read the referenced ArtifactStore
bytes and verify their exact-byte hashes against the admitted canonical hashes,
outside DB transactions/locks and before parsing or evaluation. A deterministic
byte-hash mismatch is FAILED with no score, settled by the separate attributed
settlement command with admitted counters retained; it cannot roll back or refund
admission. Uncertain completion remains UNKNOWN at full reservation. Metadata/hash
denial before admission commits instead rolls back all admission effects. Settlement
rechecks DB binding/hash identity and trusted attribution; it performs no byte I/O
and does not turn admission metadata into proof of prior byte verification.
After byte verification, exact split/group membership, vocabulary, IDs and values must match the protocol;
reject duplicates, missing, extra, unknown, inconsistent or overlapping IDs/groups.
No inference of split or alignment by row order is allowed.

For N > 0, count integer correct predictions for each model; score is candidate
correct/N minus baseline correct/N, rounded once to six decimal places using
ROUND_HALF_EVEN. Emit counts, both accuracies, delta, confusion matrices and per-class
precision/recall and macro averages; explicitly represent undefined denominators as
unavailable, never zero. Tie is zero, worse is negative. The existing safety score is
this delta, direction MAXIMIZE, bound to the same frozen metric/evaluator/protocol and
comparison scope; `streaks` compares successive scores within existing step scope,
first score establishes best, ties/worse increment no-improvement, improvements reset
it. This does not select a search node or prove generalization. Invalid evidence has
no score and no scientific output; before admission it has zero effects, and after
admission deterministic invalidity settles FAILED with no score and admitted counters
retained. Crash/uncertain completion is UNKNOWN at full reservation, never invented
success; one later final settlement may reconcile it. `settlement` and `streaks` are
specified in [task_safety.py](../../../src/researchbase/agent_runtime/domain/task_safety.py);
closed outcomes and six-place score are in
[safety_contracts.py](../../../src/researchbase/agent_runtime/application/safety_contracts.py).

For v2 reservations freeze comparison identity to task and step plus the
exact dataset, labels, baseline predictions, protocol, evaluator and metric IDs and
owner hashes (including both snapshot hashes). Candidate predictions vary. First v2
admission rejects any pre-existing legacy usage with a nonnull score in that same
step; subsequent v2 admissions and settlements must match the fixed comparison
identity. Reciprocally, fresh legacy settlement (`settle_task_budget` or
`finish_capability_invocation`) must reject a nonnull score if the same task/step has
any v2-owned reservation, even admitted/in-flight, UNKNOWN or finally settled with
no score. This applies even when the legacy reservation predates v2 admission.
Match nullable `step_id` with `IS NOT DISTINCT FROM`, including the NULL root scope.
No-score legacy accounting remains available for legacy reservations under all
existing outcome/vector/finality rules; legacy commands never settle v2 reservations.
Steps without v2 reservations retain original legacy settlement behavior.

Serialize both first v2 admission and legacy settlement under the existing task lock
and lock order; reread ownership and scored history after every wait and recheck at
deferred completion, including ordinary-role SQL. If legacy scored settlement wins,
v2 admission denies; if v2 admission wins, legacy scored settlement denies. A denial
rolls back that command's entire effect manifest. Do not repartition history or
change original v1 material/replay. Preserve existing streak ordering and mathematics. Typed schema
support alone does not enable admission; trusted composition and the remaining proofs
below are activation blockers.

## O03 — finite resources, pricing and attributable measurements

**隔离 bootstrap 例外：** O03 的实测 W 和实测剩余阶段余量仍是生产强制条件。仅在经单独授权、实际受保护 provision 的精确隔离参考部署，操作员可预先记录正整数验证 deadline W_ref、各阶段最小剩余时间、输入/输出与并发上限、CPU/内存/磁盘/PG 消耗和账单上限、锁与语句超时、总运行数及停止阈值；值由实际环境负责人根据可供应的隔离资源选定并签名或受保护记录，不能在本决议中虚构。W_ref 同时用于 reservation 的 wall_time_seconds 和 deadline_seconds；事务 epoch、task origin cap、等待消耗和超时拒绝照常适用，绝不裁剪。此处阶段余量是操作员硬停止条件，非测量结论。操作员记录须清楚标识参考用途；生产 profile 验证器拒绝参考配置，调用者不能选择或升级模式，不增加 metadata 权威标志。
每次运行实际观察全部九维，含禁止能力的实际计数；完整记录真实 wall、读取次数/字节和 commit 延迟，禁止裁剪或伪造上限内观察。超限、无法观察、期限不足、环境/来源/绑定/租约变化、锁丢失、错误权限、预算或账单阈值触及即停止新工作并撤销注册；事务未提交则回滚，已提交且超限、无法表示或无可信完整观察时保持 UNKNOWN 和全额 reservation，不重评估、不退款。若实际观察无法按现有结算规则表示，保持 UNKNOWN，记录真实观察并升级会计决议；不得用截断值结算。非 token 的 CPU/磁盘/PG 成本按可验证费率或 included/prepaid 证据单独计账；需要任务内美元总上限且现有 vector 无法表达时阻断，另作会计决议。
授权来源是实际操作员、受保护安装及受限部署/数据库权限的综合证明，非配置值。验证只走真实 consumer、真实事务与前向门控，不用 TrustedFakeConsumer。隔离 profile 不可作为生产 profile；生产仍按 O03 实测公式 `W = ceil(T_max + J_max)`、实际剩余余量及生产事实验收。所有原有 v1 合同、两个独立 reason、deadline 精确规则及 legacy 行为保持；task-event reason 可以不同于 node mutation/search-event reason，后两者相等，不引入旧 RECON374 reason 相等要求。

Select a CPU-only, local content-addressed ArtifactStore path. No network, accelerator,
subprocess, model API or provider is permitted by this registration. The engineering
profile is at most 100,000 evaluation rows, 100,000 groups, 64 classes, 256 UTF-8 bytes
per sample/group ID, 64 bytes per class, and four artifacts of at most 16 MiB each.
These are admission ceilings, not dataset facts. Enforce bytes before decode/parse,
then row/field bounds; also cap output at two 64-by-64 integer confusion matrices plus
64 per-class rows per model. Select strict UTF-8 CSV with exact headers
`sample_id,group_id,split,label` and `sample_id,prediction` for the two prediction
files; quoted fields follow Python CSV rules, extra/missing fields and NUL reject.
Protocol is a closed version-1 value with `evaluation_split`, ordered unique `classes`
and unique `{group_id,split}` entries; reject unknown fields and split/group overlap.
Require exact declared evaluation groups and all sample IDs, independent of row order.
This is an artifact byte format, not a new canonical schema. Exact refs still require O02.

| ResourceVector dimension | Reservation and final measurement rule |
| --- | --- |
| `wall_time_seconds` | Integer W derived below; final consumer value is ceiling of monotonic elapsed seconds from owning admission-command entry through evaluator completion, including waits, artifact reads, hash/parse/evaluation and internal retries. Settlement commit latency is observed separately below. |
| `agent_steps` | Exactly 1 for this admitted core evaluation operation; retain 1 on every outcome, including failure/cancel/prune/UNKNOWN. Recovery and settlement are bookkeeping, not another admitted operation. |
| `llm_calls` | Exactly 0: this path has no model client; a model call is a capability violation, not an unpriced fallback. |
| `search_calls` | Exactly 0: local artifact lookup is not literature/provider search; no search client is composed. |
| `code_iterations` | Exactly 0: executing this frozen evaluator is not modifying or iterating code. |
| `experiment_runs` | Exactly 0: no Run is created/executed; no source Run is asserted. |
| `tree_nodes` | Exactly 1, the node admitted in this transaction, retained on all outcomes. |
| `gpu_hours` | Exactly `0.000000`, conditional on CPU-only composition with no GPU library/device path; accelerator demand denies this registration. |
| `token_cost` | Exactly `0.000000` USD of token charges: no token-producing API exists in this path. This says nothing about CPU, disk, database or host charges. |

Thus the complete vector is `(W,1,0,0,0,0,1,0.000000,0.000000)` in domain field order,
not FAKE_RESOURCES. Counter measurements equal their admitted values per `settlement`;
monitor actual forbidden call/device counters and require all zero. Bind `pricing_basis`
to `bearing-local-cpu-v1:<deployment-profile-sha256>` (within the existing 512-character
limit), currency USD. The frozen deployment profile must state CPU/host, disk read,
storage and PG billing units/rates, or explicit included/prepaid status with evidence.
Those non-token costs are not expressible in `token_cost`; do not relabel them or claim
zero external cost. If the task requires a dollar cap covering them, this vector cannot
provide it: activation is blocked pending an approved accounting decision. Artifact
reads remain real I/O, metered as bytes/read count and attributed to reservation ID.

Codex implementing stage 3 must produce the actual evaluator's benchmark evidence:
implementation/hash, machine/OS/Python, CPU quota, ArtifactStore backing path/type,
input/output bytes/counts/hashes, PG version/config, lock/statement timeouts, load,
per-phase monotonic timings and process peak RSS, with all nine measured dimensions.
Run both maximum-row and maximum-byte/identifier distributions, invalid/late failures,
replay, settlement and competing lock waits; repeat at least 30 times per profile
(30 is a minimum repeatability check, not a statistical latency guarantee). Let
T_max be the largest end-to-end admitted duration and J_max the largest additional
measured scheduler/I/O/PG delay under the selected deployment load envelope. Set
`W = ceil(T_max + J_max)`; reject a nonpositive/unmeasured W. Bound admission waits
by this same deadline, and check remaining time after each wait, read and evaluation
chunk. Freeze the load envelope and measured J_max, rather than an unexplained constant margin. For new v2 admission require `deadline_seconds = resources.wall_time_seconds = W`. The receipt completion and reservation creation epoch is the database transaction timestamp; deadline is exactly that epoch plus W seconds. Reject rather than clip if it exceeds the existing task wall-time origin plus its applicable maximum: origin is the earliest reservation creation epoch, or this reservation creation epoch when it is the first. Admission waits consume this allowance; they never restart W. The database enforces the exact generated deadline, task-origin cap and current-time expiry after waits and at deferred completion. The later trusted core must additionally check the actual measured remaining-phase allowance after waits, before each read/evaluation phase and before commit. That allowance comes from the registered deployment profile, cannot be inferred from W alone, and must not be replaced by an invented constant. Missing profile denies production admission. Wall observation remains monotonic from owning command entry, including waits; current DB time owns deadline/entitlement checks, never caller time. No fresh work after deadline. Existing v1 timing/material semantics remain unchanged.
Meter file bytes and each phase against the same reservation/consumer generation.
The final usage row is frozen before its own commit: record actual admission/settlement
commit latency and total reservation lifetime in attributed operational telemetry, not
as an invented future duration in that row. W includes those benchmarked overheads;
if exact inclusive post-commit accounting is indispensable, current usage types cannot
express it and activation requires an explicit owning-accounting decision.
Overrun or lost observation cannot be settled with a fabricated capped measurement:
retain UNKNOWN/full reservation, record actual overrun in operational telemetry and
invoke existing trusted policy-stop handling. Later final settlement must still obey
`measured <= reserved`; no new refund or over-bound accounting rule is approved here.

Local feasibility evidence, 2026-10-28: an inline standard-library CPython 3.12.15
reference calculation on macOS 27.0 arm64 read four temporary synthetic files, verified
SHA256, parsed CSV/protocol, checked exact ID/group/vocabulary alignment, counted both
confusions and per-class precision/recall, and computed Decimal delta. Five repetitions
at N=100,000/C=64 used bytes `(14184401,6684391,6684391,10000385)` and took
0.556467500–0.584273417 seconds; N=25,000 with 255-byte UTF-8 IDs used
`(13146121,6471111,6471111,7300385)` and took 0.221890625–0.233306959 seconds.
For reproduction, IDs were prefix `s`/`g` + six-digit row index + repeated `é`
(28 or 124 copies); labels were str(i % 64), CSV used LF, and protocol JSON used
compact separators with ensure_ascii=False. Wrong predictions were str((i+1) % 64)
on rows i % 4 == 0 (baseline) or i % 8 == 0 (candidate).
Process peak RSS was 506,937,344 bytes, including synthetic generation. Baseline was
constructed correct on 3/4 rows and candidate on 7/8, so actual counted pairs were
`(75000,87500)` and `(18750,21875)`, delta `0.125000`. These synthetic stress fixtures
show arithmetic feasibility only; they are neither bearing research nor the deployed
evaluator benchmark. They do not establish W, cold-read latency, full 16-MiB malformed
parsing behavior, maximum memory, or production throughput.

**Precise unavailable facts blocking numeric W/activation:** there is no implemented
production evaluator/composition or selected deployment CPU quota, ArtifactStore backing
service and its latency/cancellation behavior, PG wait/load envelope, or billing rate
schedule in this repository/direction. The current synchronous [ArtifactStore port](../../../src/researchbase/foundation/artifact_store.py)
does not promise bounded I/O latency or a bounded-size read; `open()` reads all bytes.
The concrete consumer therefore needs a bounded local read adapter that rejects after
16 MiB + 1 bytes without allocating unbounded content; metadata byte_size alone is
not proof. Implementing that adapter belongs to the separately authorized code slice. Codex must obtain and measure these facts on the
selected production deployment and attach the above evidence before production stage-3 activation; the separately gated reference-only exception is defined in O03 and O09. For production, if they
remain unavailable, report each missing fact and keep admission denied. A hard wall
upper bound cannot be inferred from a cached local arithmetic timing. No dataset or
training job is needed to obtain synthetic engineering measurements.

## O04–O05 — depth, occupancy and lifetime

Root maps to NULL step or a same-task root step at depth zero; each non-root node
requires a same-task step whose parent chain depth equals node depth, with the parent
node's mapped step as its immediate parent. No synthetic steps are created. Restrict
comparison to the same step and frozen binding; reject cross-task, depth, protocol,
operation or reservation mismatches. `operation_id = node_id`, one reservation per
node. Task-wide outstanding reservations, including UNKNOWN until final settlement,
occupy the parallel limit; never infer occupancy from siblings. Perform bounded
DB metadata/value and bounded no-I/O registered evaluator digest validation before
admission commits; ArtifactStore reads and byte-hash verification only after commit,
outside locks and transaction, before parsing/evaluation, as specified in O02.
Deterministic mismatch settles FAILED without score or counter refund; uncertain
completion remains UNKNOWN at full reservation. Failure or process loss retains the reservation;
recovery reuses original IDs and must not evaluate twice concurrently.

## O06–O08 — atomic effects, stop and settlement

Add `admit_bearing_evaluation_v2` with closed typed arguments: project/task/command,
expected task revision, session/node/parent and existing append fields, exact step,
operation, reservation, frozen evidence binding, full resource vector, deadline and
reason. Material type `BearingEvaluationCommand`, material_version 2, identifies this family, includes authenticated
actor and every input/default/NULL, canonical UUIDs and exact decimals; generated
timestamps and projections are excluded. Freeze independent literal bytes/digest and
result vectors before implementation. Keep existing `ExperimentSearchCommand` and
`SafetyCommand` v1 bytes and replay unchanged. Result contains original reservation,
node, search event, task event, receipt and resulting revision IDs/values.

The closed material envelope has exactly `type`, `material_version`, `command_name`,
`project_id`, authenticated `actor_id`, `command_id`, `task_id`,
`expected_row_version`, and `arguments`. Admission arguments are exactly `session_id`,
`node_id`, `branch_kind`, `mutation_reason`, `reservation_id`, `parent_node_id`,
`hypothesis_version_id`, `experiment_spec_version_id`, `step_id`, `operation_id`,
`resources`, `observed_depth`, `observed_parallel_branches`, `deadline_seconds`,
`reason`, all seven binding IDs, `consumer_generation`, and owner hashes named
`labels_content_hash`, `baseline_predictions_content_hash`,
`candidate_predictions_content_hash`, `protocol_content_hash`, `evaluator_content_hash`,
`dataset_manifest_hash`, `dataset_content_hash`, `metric_content_hash`. `resources`
contains exactly the nine O03 vector fields. Include every NULL/default explicitly;
`operation_id = node_id`. Settlement arguments are exactly `reservation_id`, the
same seven IDs, generation and eight hashes, `measured` (the same nine fields),
`outcome`, `score`, `evaluator_version`, and `reason`. The closed observation is
those settlement fields; score and evaluator version are both NULL when no score.
Reject unknown fields and any binding/generation/hash mismatch against the original
reservation and owners. Both use `BearingEvaluationCommand`, version 2,
`sha256-cjson-v1`, canonical UUIDs and existing exact decimal serialization. Replay
returns original IDs/results and never repeats effects; changed material conflicts.
Independent literal bytes, digests and result vectors are prerequisites to code.

Proposed closed result DTO (not new receipt columns): `task_id: UUID`,
`resulting_row_version: integer`, `replayed: boolean`, `receipt_id: UUID`,
`task_event_id: UUID`, `reservation_id: UUID`, `usage_record_id: UUID | NULL`,
`search_session_id: UUID | NULL`, `search_node_id: UUID | NULL`,
`search_event_id: UUID | NULL`. Admission returns reservation and all three search
pointers, with NULL usage; settlement returns reservation and usage with all three
search pointers NULL. Receipt ID and resulting revision are from the receipt; search
pointers are its existing result columns, task event comes from the receipt/event
association, and reservation or usage comes from its unique receipt-linked effect.
The settlement reservation comes through the usage FK. No new catalog columns are
implied. Fresh and replay results retain these IDs and revision; only `replayed`
changes from false to true. The task event's `stop_budget` is a durable event field,
not a result DTO member: on admission it is true exactly for the permitted own-last-unit
case, otherwise false. See [literal proposed vectors](PR3-16-bearing-v2-material-vectors.md).

One transaction creates exactly one reservation, one PROPOSED node, one `NODE_APPENDED` search event,
one `BEARING_EVALUATION_ADMITTED` task event, one receipt and its task-event association, and increments task
revision once; it creates no usage, step event, Run, Measurement or Claim. Each effect
must reference the same task, operation and fresh receipt; any missing/extra effect or
constraint failure rolls back all. Entitlement precedes committed receipt replay;
changed material conflicts. For fresh writes recheck authority, CAS, checkpoint,
capability, deadline and stops after waits and forced constraints, excluding own
uncommitted receipt. Prior sticky or derived stop always denies. Capture pre-command
charged totals under the task lock; only if they were strictly below every applicable
positive cap and this reservation alone reaches an additive cap may the node commit
with the single task event's budget-stop flag. A pre-existing stop or competing stop
never qualifies. Session remains open; no implicit closure or later admission.

A separate trusted `settle_bearing_evaluation_v2` command attributes its observation
to the original reservation, exact binding and consumer generation. It creates one
usage record, one `BEARING_EVALUATION_SETTLED` task event, one receipt and one
receipt/task-event association, and increments task revision once; the original
reservation is unchanged. Neither command creates steps, step events, sessions, Run
links, Runs, Measurements, Claims or Artifacts. Settlement creates no node/search event. Existing finality and outcome rules apply:
UNKNOWN retains worst case, at most one final reconciliation, no post-final score.
Recovery owner replays original command IDs after uncertain commit; no duplicate
charge or silent refund. Legacy safety commands retain v1 material/results/replay
and existing guards, with only O02's narrow reciprocal ownership/score restriction:
they cannot settle a v2 reservation, or add a legacy score to a step with any v2
reservation. No-score legacy accounting still obeys existing rules.

## O09 — closed forward-migration manifest and preservation

The historical `uv run alembic heads` observation below reported sole head
`0082_experiment_search_core`; its source parent is `0081_agent_execution_intents`.
It is not a new execution result for this draft. Recheck at dispatch, allocate the next
forward revision after 0082, and abort on drift. Do not modify 0078/0080/0081/0082.
This manifest includes the O02 binding and is the complete proposed catalog delta.
Recheck the dispatch head before allocating any revision; this document reserves none.

Exact source owners: [0077 DDL/guards](../../../migrations/versions/0077_research_task_graph.py),
[0078 DDL/GUARDS/FINAL_GUARDS](../../../migrations/versions/0078_task_safety_policies.py),
[0080 EXTENSION_03_SQL/EXTENSION_08_SQL and PR304_CHILD_GUARD_SQL/PR304_VALIDATE_SAFETY_SQL](../../../migrations/versions/0080_capability_gateway.py),
[0081 DDL/FUNCTIONS](../../../migrations/versions/0081_agent_execution_intents.py),
and [0082 SCALAR_FUNCTIONS/RECEIPTS/GUARDS/RECEIPT_COMPLETE/TRIGGERS](../../../migrations/versions/0082_experiment_search_core.py).
0081 changes execution-intent guards, not the safety/receipt functions below; 0082
replaces only inherited `pr301_receipt_complete()`. Never reconstruct current guards
from 0078 alone: 0080 adds gateway branches that must survive. Current-source SHA256:

| Migration | SHA256 |
| --- | --- |
| 0078 | `7c312389444e9edfea89f10c472462b7d2ca9c739a951c905d09140058b8c255` |
| 0080 | `b1ef6a678620acb27282eb68d08c658e7bfaad85f591ca93f298545007326561` |
| 0081 | `142c7a9061785a971d7043667041cf5368be24e38069c59900640d13c2259e52` |
| 0082 | `0166bdc1e30c9c3963c9655b6cfd7fed1cdcd0e6822a39a666de2fb7adb52470` |

Replace exactly these nine function bodies, preserving signature, owner, ACL,
SECURITY INVOKER and search_path; old-command branches retain token-equivalent SQL
except the explicitly declared reciprocal ownership/score checks below. These do
not alter original v1 material, results or committed replay:

| Function | Only permitted new branch/effect |
| --- | --- |
| `pr316_command_event(text)` | Map admission to `BEARING_EVALUATION_ADMITTED`; settlement stays outside search mapping. Existing two mappings unchanged. |
| `pr316_receipt_insert()` | New commands get UUIDv7, transaction timestamp and current authority checks; settlement uses the new authority helper to allow recovery on CANCELLED tasks. |
| `pr316_node_proof(experiment_search_nodes)` | Dispatch only the new command to fresh same-transaction reservation proof; old committed-xmin proof and unconditional `pr316_activation` denial remain literal. |
| `pr316_state(research_task_command_receipts,experiment_search_events)` | New admission requires `NODE_APPENDED`, same node/parent/depth/reason, and the new proof; old create/append cases unchanged. |
| `pr316_lineage_insert()` | Permit only new admission alongside old append in the node branch, with all existing fresh receipt/parent/scope checks and new proof; no settlement lineage effects. |
| `pr316_validate_receipt(uuid)` | Dispatch the two new commands to v2 validation before the old path; preserve old search effect counts and material reconstruction. |
| `pr304_child_guard()` | Add admission only to reservation allowlist and settlement only to usage/CANCELLED recovery allowlists. Enforce all-null legacy versus complete-v2 command ownership; reject either legacy usage command targeting v2, including UNKNOWN reconciliation. For fresh legacy usage with nonnull score, reject any v2 reservation in the same task/step under O02, including in-flight work. Retain all 0080 gateway and immutable/fresh-owner checks. |
| `pr304_validate_safety(uuid)` | Include the two names in stop recomputation. At deferred completion recheck ownership and O02's reciprocal exclusion for fresh legacy usage with nonnull score, and reject v2 admission against legacy scored history, under the existing task lock and after waits. Do not apply a new replay/material contract to historical legacy rows. Retain history order, gauges, score/finality/counter math and all old checks. Retain A2/A3 execution denial: initial v2 admission supports A0/A1 only. |
| `pr301_receipt_complete()` | Map admission/settlement to `BEARING_EVALUATION_ADMITTED`/`BEARING_EVALUATION_SETTLED`; reservation/usage counts respectively 1/0 and 0/1, no other safety/gateway effects; extend timestamp/unrelated-effect and CANCELLED-settlement checks, then v2 completeness. |

Add exactly four validators (no DML ownership, all SECURITY INVOKER, fixed
`search_path=pg_catalog,public,pg_temp`; enabled is SQL STABLE, the other three
PL/pgSQL VOLATILE): `pr316d1_enabled() RETURNS boolean`,
`pr316d1_authority(research_task_command_receipts) RETURNS void`,
`pr316d1_admission(experiment_search_nodes) RETURNS void`, and
`pr316d1_validate_receipt(uuid) RETURNS void`. Enabled returns literal false in stage 2;
stage 3 alone may replace it with true after authorized Application wiring and genuine
positive tests. Production remains subject to the measured profile and production gates; the separately gated reference-only exception is defined in O03 and O09. No caller GUC/role bypass. Authority repeats current `pr316_live`
entitlement/preheld/fresh-task checks, allowing CANCELLED only for settlement.
Admission proves same-xmin receipt/reservation/node, O04 mapping, exact vector/binding,
pre-command stop-free prefix and deadline/checkpoints, O02 DB metadata/hash identity
and no legacy scored history in the same task/step, then own-last-unit stop; it
never calls the old post-reservation `pr316_admission` which denies at equality.
V2 receipt validation reconstructs material_version 2 and all result pointers, forces
O06–O08's exact counts/no extra effects and invokes authority at deferred completion;
it also requires enabled=true. The v2 proof enforces O02 binding, shape, ownership
and comparison identity using DB metadata only; none of these validators reads or
byte-verifies ArtifactStore content.

Replace exactly seven CHECK constraints (drop/add same name, validated immediately):

| Table.constraint | New predicate branch, old rows unchanged |
| --- | --- |
| `research_task_command_receipts.pr316_command_names` | Add exactly the two v2 command names. |
| `research_task_command_receipts.research_task_command_receipts_material_version_check` | Version 2 iff either new command; all historical commands require 1. Hash scheme remains `sha256-cjson-v1`. |
| `research_task_command_receipts.pr316_receipt_shape_ck` | Admission has all three search result pointers; settlement has none; retain original create/append/other shapes. |
| `research_task_events.pr316_task_event_names` | Add exactly the two BEARING event names. |
| `research_task_events.pr316_task_event_states` | Admission preserves CREATED/PLANNING status; settlement preserves CREATED/PLANNING/CANCELLED status. |
| `research_task_events.pr316_task_event_reason` | Both require the existing nonblank NFC reason bound 1..8192. |
| `research_task_events.pr303_event_stop_kind` | Permit new events' derived stop flags; v2 validator requires admission only own-budget stop, settlement existing derived flags, no human/policy/success flags. |

Add exactly the eight nullable reservation columns in O02, seven RESTRICT FKs to
the listed targets, and a validated all-null-or-all-nonnull shape CHECK; v2 deferred
validation additionally enforces command ownership, same-project/frozen/hash checks,
and reciprocal legacy ownership/score exclusion via the two amended `pr304` bodies
above. No other new/replaced/dropped catalog objects:
zero tables, indexes, triggers, UNIQUEs, NOT NULLs or other constraints. Specifically preserve every definition,
enabled flag, timing and deferrability of the 16 0082 triggers, `pr301_receipt_complete_commit`,
`pr301_task_final`, and `pr304_reservation_guard`/`pr304_usage_guard`. Preserve
`pr316_uuid7`, `pr316_reason`, `pr316_immutable`, `pr316_preheld`, `pr316_live`,
`pr316_refs`, `pr316_chain`, `pr316_admission`, `pr316_link_write_disabled`,
`pr316_effect_complete`, `pr301_task_guard`, `pr301_graph_final_guard`,
`pr301_receipt_insert_guard`, `pr304_validate_policy`, all 0080 gateway validators,
all 0081 intent guards and every remaining baseline function. The unchanged set is
the complete 0082 catalog except the nine functions and seven CHECKs above, plus the specified reservation additions;
verify it with 0082 `CATALOG` plus the richer `catalog_snapshot` in
[search fixtures](../../../tests/integration/phase3/search_fixtures.py) and the exact
[upgrade delta assertions](../../../tests/integration/phase3/test_pr3_16_migration.py).
This includes all four search tables' constraints and RESTRICT FKs, receipt FKs,
reservation/usage finality and uniqueness, `pr304_event_stop_slice`, and the link-write
denial. No schema expansion follows from naming helper functions.

Privileges: no GRANT/REVOKE/owner/default-privilege change on ANY existing object;
retain both PUBLIC and explicit role ACLs byte-for-byte, including 0082's revoked
search-table DML and all legacy command/table grants. New helpers have ordinary
invoker function EXECUTE only (PUBLIC plus owner, no SECURITY DEFINER or table grant);
assert effective ACLs explicitly, refusing unexpected deployment default grants.
The migration owner may create/replace these validators; an ordinary writer cannot
replace/enable them. No deployment writer role is supplied: retain denial if the
configured Application principal lacks existing INSERT/SELECT privileges. Test-only
roles/grants in search_fixtures are not production provisioning. Any necessary new
production grant must be separately named and reviewed; this manifest authorizes none.
A principal with existing table privileges still needs every guard and Application check.

Upgrade compares pristine/populated 0082 and forward catalogs: exactly 9 changed + 4
new functions, 7 changed CHECKs, 8 nullable columns, 7 RESTRICT FKs and one
shape CHECK, no other delta; compare old-function tokens after
removing only declared new branches and replay old literal vectors. Compare raw old
rows/hashes/seals/ACLs unchanged, and run ordinary-role partial/extra-effect attacks.
Forward migration is transactional; any failure rolls back to 0082. Once applied,
no downgrade (0082 itself is forward-only): before any v2 use an approved forward
repair restores these nine bodies and seven predicates and drops the four helpers and unused binding columns/constraints,
without data changes. After any v2 use preserve their rows/replay and add a forward
repair that first disables new admissions; never restore predicates that reject
historical v2 rows, delete receipts, or refund reservations. Recheck independent
acceptance after repair. This proposed manifest does not authorize implementation.

### Reference-only candidate migration boundary

**候选迁移边界：** 在实际 PR32 合并及唯一 head 新核对后才分配前向 revision；不修改 0083 文件及其历史定义；经授权的候选前向迁移替换参考 DB 上现有函数体以激活。候选分支及产物标识、源闭包和迁移集合须经独立审查，部署系统仅允许已记录的隔离主机、DB、writer 与 CAS 绑定运行，生产发布流程显式拒绝该候选 revision/产物。迁移执行前独立核实目标 DB 的不可混淆身份、当前唯一 head、角色及权限，迁移事务自身也须核对同一目标和绑定，任一不符即中止；精确 DB 身份只是防误操作检查，权限和受保护 provisioning 才提供授权证据。禁止通过调用方参数、GUC、临时 ALTER、禁 trigger 或直接写 v2 已提交效果绕过。已应用的参考 revision 与 source hash 冻结并保留其分支、DB 和历史，不合并 main 或生产升级线；生产另以届时 main 唯一 head 和实际生产事实授权 migration/guard delta，不携带参考身份或依赖参考 preflight，须独立真实 PG 验收，参考 gate 证明不自动转移。
参考支持范围限定为单主机、本地文件系统的可靠共享POSIX advisory lock及稳定inode、每namespace一个合作consumer进程；不得由fork worker继承authority。网络文件系统、多主机、独立mount锁视图、不可信同UID代码或绕过Application的直接数据库写入均不在该信任模型内。操作员必须记录实际拓扑、隔离及所有组合根的绑定事实；不支持或无法核实则拒绝。租约、路径与hash本身不能建立这些事实。

The existing protected operator, acting under the owner's standing delegation and within the documented trusted same-UID/cooperating-process boundary, is the actual authorization root for one isolated reference bootstrap entry root. The operator shall independently review the exact deployment artifact and manifest and create a separate protected, scoped bootstrap authorization record binding their digest, provenance, expiry, host, UID and install namespace to that one deployment. Operator startup setup alone consumes this record; callers and commands shall not select an authority source, manifest, verifier, profile, root or callable. A path, hash, UID, UUID, authenticated A2 infrastructure facts, or caller-supplied fields alone confer no authority. The operator's authorization and actual observed measurements are both required; neither substitutes for the other. No external owner service or cryptographic approval framework is implied.

Setup constructs exactly one fixed DB/store/verifier binding for the authorized root. Only that root may register; independently constructed or mismatched roots deny. Existing CLI and API roots remain unregistered and default-deny for genuine consumer work. There is no global/shared registry or authority; any additional root needs separate exact binding proof and authorization. Registration is not scientific truth and grants no principal entitlement; normal Application authentication, authorization and formal-reference checks remain mandatory.

注册须核验固定加载 callable 与实际依赖闭包、owner hash 绑定，核验独占租约和实际 DB↔CAS 跨组合根绑定；无注册、不可支持拓扑或失效均 deny。 已注册consumer必须在整个注册生存期连续持有同一稳定inode上的独占POSIX租约，包括所有在途提交及失败清理，直至撤销并完成在途工作后才可释放；不得仅在注册时检查或中途释放后重取。租约丢失、替换或所有权不确定立即fail-closed撤销并禁止新工作；已有提交按下述commit/revoke排序及receipt恢复规则处理，无可信完成观察仍保持UNKNOWN/full。commit 与 revoke 持同一进程互斥直至实际 commit 返回或失败清理；receipt 首先按现有认证/读取权限及原 key/material 重放，未知 commit 先查询已决事务 receipt。无可信完成观察保持 UNKNOWN/full，旧 generation 不赋权。

Before a transaction, the foundation installation/registration adapter shall verify the protected authorization and installation and create an in-process proof for the fixed loaded callable and binding. Freeze an explicit finite inventory for the actual installed revision: all installed first-party source under the approved package roots, the selected interpreter/runtime and all installed dependencies under its approved import roots, including native code and import locations, with observed identities and content digests. Use a controlled import environment with only those enumerated roots; resolve the fixed callable's actual module/code origin and all already loaded modules against the inventory. Potential lazy imports must already be covered by that complete installed-file inventory; this does not require executing every possible path before registration. Caller-selected code, plugin discovery, unenumerated code loading or mutable import paths are unsupported. The operator must keep that installed inventory immutable for the registration lifetime and revoke before any installation change; any observed identity/content/import mismatch or missing inventory denies or revokes before further work. Registration checks and later permitted code loading happen outside transactions; transactions use the fixed in-memory verification result and guard. This is a bounded closed-world inventory for the fixed callable, not general plugin attestation. Actual names, hashes and installation proof are recorded only after implementation and installation exist.

Reference bootstrap supports controlled fresh startup only; it does not attest an arbitrary already-running interpreter. The protected operator must freeze and approve the selected installation before executing its fixed isolated bootstrap. The trusted bootstrap base is the local OS plus the fixed selected Python/stdlib and reviewed verifier/entrypoint; it is not selected by caller flags or arbitrary runtime-root labels. The adapter first checks the actual protected records, complete immutable file inventory and isolated import environment, rejects preloaded non-bootstrap application/dependency modules, and issues only an opaque process-local prepared context. The operator composition root then loads the one approved fixed target from that inventory, and finalizes verification against that same context. Finalization checks loaded-origin/identity and unchanged file/import state, unexpired authorization and the final uncapped observed bounds before issuing installation evidence. No raw preloaded callable, serialized context or caller assertion satisfies this order. The context is not consumer capability, principal entitlement, registration or DB/CAS binding; no new registry, worker/IPC framework, canonical schema or activation authority is created. Actual controlled-startup evidence remains required at installation/registration gates.

Before a transaction, the foundation adapter performs filesystem, installation, source and lease preflight, including observation of the protected namespace and actual CAS and lease device/inode under the existing binding and lease contract. DB identity, authenticated roles and catalog preflight I/O uses a typed repository/preflight port implemented by the persistence adapter and composed by operator startup, using the already specified PostgreSQL methods. The observations are verified against the same approved deployment binding; raw PostgreSQL observations and A2 authenticated facts are separate from, and do not establish, the operator's scoped authorization or prove source. Foundation must not import SQLAlchemy, psycopg, persistence adapters or raw DB objects. Application receives only a typed non-I/O identity-verification port and a shared commit/revoke guard; the same mutex remains held through actual commit return or failure cleanup under the existing lifetime and replay rules. Application must not perform filesystem verification or import filesystem or other adapters. Existing foundation boundary tests prohibit reverse and framework imports.

**具体候选机制和指挥官核验方法**

候选仅在 PR32 实际合并后，以实际合并的 0083 和重新核实的唯一 head 为基线，审查一个未发布的参考专用前向 revision。其同一迁移事务在任何 DDL 前 fail closed：核对受保护操作员事先批准且独立提供的精确身份记录，包括服务器/集群稳定身份、端点与端口、数据库名及 DB 标识、环境/部署身份、唯一当前 Alembic revision、连接 `session_user`/`current_user`、迁移角色及函数 owner；核对目标 DB 与 CAS 根、namespace、物理存储及组合根的一对一绑定、安装来源和独占租约。核验采用下文固定只读方法；实际环境所有者和 DBA 提供具体预期值与最小读取权限并经审查；缺字段、不可验证、歧义、不匹配、权限不足或绑定变化一律回滚拒绝。身份比较是事故防护，不是授权；受保护 provisioning、明确批准和仅可在参考环境使用的受限迁移角色共同提供授权。不能把未提供的 ID、凭据或 provision 写成既有事实。

迁移角色须可作为现有函数 owner 执行替换（或由受保护的 owner 角色执行），且不向普通应用 writer 授予函数所有权、DDL、角色切换或绕过 guard 的权限；部署凭据、网络和发布控制须实际限制该角色只能用于核准参考 DB。执行前检查 `public.pr316d1_enabled()` 的 OID、零参数 boolean 签名、owner、ACL、语言、volatility、security、search_path 和其他属性与已审查 0083 基线一致，以及原函数体为 false；不符即拒绝。唯一允许的激活 DDL 模式为：

```sql
CREATE OR REPLACE FUNCTION public.pr316d1_enabled() RETURNS boolean
LANGUAGE sql STABLE SECURITY INVOKER
SET search_path = pg_catalog, public, pg_temp AS 'SELECT true';
```

在同事务中复核原 OID、签名、owner、ACL、search_path 和全部其他函数属性未变，函数体仅从 false 变 true；否则抛错回滚。须验证实际目录属性和调用权限，不假定 SQL 文本自动保留所有属性。0083 的 deferred receipt validation 经现有 `pr316d1_validate_receipt` 调用该同一 helper，先完成既有 authority、binding、digest、安全与 deadline 等检查，再通过最后的 enabled 检查；不新增 helper 或调用链。此数据库门只解除最后的 disabled 拒绝，真实 Application command、port/adapter、注册和 verifier 及其所有检查仍必需，不能单凭 true 赋予应用信任。审查须覆盖精确 SQL、目录前后快照、权限、调用图及错误目标拒绝，真实 PG 测试证明。

候选 revision 一旦在参考 DB 应用，其 source hash、revision 和证据冻结，绝不为生产重写；保留该参考分支、DB 和迁移历史，候选分支/revision 不合并 main，也不进入生产升级线。最终生产激活另以届时实际 main 唯一 head 和实际生产事实为基线，另行授权并设计生产 migration 和 guard delta；不得把参考身份或配置写入生产迁移，也不能让生产升级链依赖参考专用 preflight。生产变更须独立真实 PG 验收，参考通过不自动转移 gate 证明。

尚缺的具体决策是：环境所有者/DBA 必须选定可验证的集群与 DB 稳定身份字段及读取方法、受限迁移角色的 owner 执行方式与部署隔离控制，以及 DB-CAS 绑定/租约的验证方法和实际值；资源所有者须提供验证限额与计费事实。政策可在这些事实尚未提供时获审，但任何未满足的 preflight 都禁止执行；不能以此声称已有 provision 或执行授权。

**具体核验方法**

固定数据库核验方法为 PostgreSQL18 内置只读接口：pg_control_system().system_identifier，加 current_database()、pg_database 的 oid/datdba、inet_server_addr()/inet_server_port()、session_user/current_user，以及 public.pr316d1_enabled() 的 pg_proc OID/owner/ACL/全部属性。实际参考值由操作员 provision 后记录，不复用现测试库的值。迁移连接本身须在同一事务、任何DDL前读取并匹配这些字段，独立预检连接仅为补充；不具备读取权限则拒绝，由DBA先明确批准最小只读权限，不自动提权。相关查询已仅在现有admin/trust测试库验证可用，不构成参考授权证明。

角色边界：独立受保护的迁移登录角色，按批准方式在迁移连接切换到函数owner角色；普通Application writer不是函数owner，无DDL、superuser、CREATEROLE/CREATEDB/REPLICATION/BYPASSRLS及切换owner权限。角色实际名称/OID、认证方式、授权和受控凭据由真实provisioning产生；不得把现有researchbase超级用户和trust连接作为实现。

文件系统/安装及DB↔CAS绑定的实地核验在迁移事务前完成，并冻结经操作员批准的绑定记录；整个DDL事务及实际COMMIT持有独占租约。事务内只核对同一DB连接上的身份/目录及内存中的冻结绑定，不临时做文件读取、hash或重新选择namespace。任何失效在允许新Application工作前拒绝注册。路径、摘要、inode或DB身份只是核验数据，授权仍来自受保护的真实操作员/部署权限。

依赖门控：BEFORE_CODING 须合同接受、基础参考基础设施身份与认证 provision 及接口审查；另有明确代码授权后核心实现方可开始，默认拒绝；不要求编码前完整安装 consumer 证明或预先分配 revision。BEFORE_MIGRATION_CODING 须核实实际基线及唯一 head、批准 revision 分配并完成依 head 的维护清单审查，另行授权迁移编码；不要求完整安装 consumer 证明；核心代码可先于分配，迁移代码不可。BEFORE_ACTIVATION_APPLY 须实现冻结，并取得实际加载来源/闭包 hash、安装、租约行为、DB-CAS 绑定证明及完整候选专属 preflight 的独立审查，另行明确授权。角色和 DB preflight 方法设计可在编码前审查；实际完整候选证据只能在代码存在后审查。缺任一条件即拒绝，任何审查或授权均不自动升级其他权限。真实 30 次测量是最终生产 profile 前置条件。

Missing actual installed manifest, loaded-code closure or binding evidence prohibits registration and activation, but does not itself prevent later bounded code work after the existing contract/interface review, infrastructure prerequisites and separate code authorization. A separately authorized positive unit proof shall use an actual protected file installation of an existing fixed evaluator/codec callable, operator setup and a real lease, and exercise registration and lifetime/revocation; a manually enabled fixture is insufficient. It makes no positive SQL or Application-write claim. Migration coding, apply, reference activation, real PostgreSQL positive admission/settlement, measurement and production acceptance remain separate gates. Preserve the existing nine-dimensional observation policy, UNKNOWN/full reservation, original receipt replay and all other contracts.

参考专用revision及部署产物不进入main/生产升级线；通用消费者代码只能在之后另经审核的生产包中按冻结来源筛选复用，不连带携入参考revision/preflight。任何新的生产迁移和实际生产部署均重新核对适用head/事实并独立验收。

## O10 — staged acceptance and evidence

1. Pure concrete parser/evaluator tests: exact paired arithmetic, class imbalance,
   tie/worse/improvement, rounding, invalid/oversized evidence and deterministic output;
   no activation or empirical performance claim.
2. Forward migration with denied activation: inspect sole head, complete catalog and
   unchanged old branches/ACLs; real PG18 negative SQL attacks and migration upgrade.
3. Wire atomic consumer and settlement only after separate authorization: real PG18
   positive/denial tests for exact effects and rollback at every flush, changed-material
   conflicts, lost-response replay, entitlement/revocation/checkpoint waits, cross-task
   references, occupancy and UNKNOWN recovery, concurrent last-unit/prior-stop races,
   settlement attribution and no extra effects. Independent v1 and v2 literal vectors
   and old-row/scientific-hash/Run-seal preservation are mandatory. Prove metadata-only
   admission with zero ArtifactStore reads under locks, post-commit byte verification
   before parsing/evaluation, deterministic mismatch FAILED/no-score with admitted
   counters retained, and uncertain completion UNKNOWN. Prove both serialized orders
   of legacy scored settlement versus first v2 admission, including an older in-flight
   legacy reservation, NULL step scope, forced constraints and post-wait rereads;
   denied commands have zero committed effects. Prove no-score legacy accounting
   remains available and steps without v2 reservations preserve legacy behavior/replay.
4. Run focused and CI regressions, measure worst-case evaluator and full read responses,
   and obtain independent review and commander acceptance with no open P0/P1. No
   ranking or search selection is implied. Current reads remain 10 nodes, depth 3,
   11 events and zero links; later writers first establish compatible measured complete
   response bounds. Future D1 implementation tests are NOT RUN by this proposal; local arithmetic
   observations in O03 are not implementation acceptance.

Open activation blockers are implementation and verification of this binding, trusted
production composition and registration/revocation coordination, recovery ownership,
and a deployment-specific measured resource/pricing profile. These remain mandatory for production; the separately gated reference-only exception is defined in O03 and O09.
Resolve these with concrete evidence before accepting a Stage2 contract or enabling
admission; absence of an actual dataset is not a reason to invent one.


## Historical verification observed 2026-10-28

The following earlier observations are preserved as historical evidence, not checks
run for D1-BIND366 or passing gates for this revised proposal.

All uv commands below used `UV_CACHE_DIR=/tmp/rb-d1362-uv UV_PYTHON_DOWNLOADS=never`.
`uv sync --locked --group dev` completed: resolved 38, prepared/installed 34 packages.
These are baseline checks for a documents-only change, not D1 implementation acceptance.

| Exact command after the uv environment prefix | Completed output / exit |
| --- | --- |
| `uv run ruff check .` | All checks passed; exit 0. |
| `uv run ruff format --check .` | 969 files already formatted; exit 0. |
| `uv run pyright` | 0 errors, 0 warnings, 0 informations; exit 0 (separate version notice). |
| `uv run alembic heads` | `0082_experiment_search_core (head)`; exit 0. |
| `uv run pytest -o addopts='' -q tests/unit/phase3/test_task_safety_contracts.py tests/unit/phase3/test_task_safety_policies.py tests/unit/phase3/test_experiment_search_contracts.py` | 120 passed in 0.24s; exit 0. |
| `uv run pytest -o addopts='' -q tests/architecture/test_pr3_16_boundaries.py` | 5 passed in 4.28s; exit 0. |
| `.venv/bin/python -u -m pytest -o addopts='' -q tests/architecture/test_pr3_16_boundaries.py tests/architecture/test_pr3_03_boundaries.py tests/architecture/test_pr3_00_boundaries.py` (direct interpreter, no uv prefix) | 78 passed in 4.98s; exit 0; includes the five D1 checks above. |
| `uv run pytest -o addopts='' -q tests/unit/phase3/test_task_budget_accounting.py` | 1 collection error in 0.16s, zero tests executed; exit 2. |
| `uv run pytest -o addopts='' -q tests/unit/architecture/test_pr12_guard.py tests/unit/architecture/test_pr14_guard.py` | 2 collection errors in 0.15s, zero tests executed; exit 2. |
| `uv run pytest -o addopts='' -q tests/integration/phase3/test_pr3_04_migration.py tests/integration/phase3/test_pr3_16_migration.py` | conftest import failed, zero PG tests executed; exit 4. |

All three failing commands report macOS `library load mig callout failed` rejecting
`pydantic_core/_pydantic_core.cpython-312-darwin.so`'s code signature. A direct psycopg
preflight also fails native-library loading, including Homebrew libpq. These are
observed environment blockers, not PASS or database evidence. No PG connection or
server-version result was obtained. Earlier broad unit/architecture attempts yielded
no completed result; the bounded commands above are the usable
results. Whole suite was not run; the external loop owns it. D1 activation remains denied.

`python3 /Users/fengwang/ResearchBase-runtime/.pipeline/bin/check_d1_362_docs.py` and
`git diff --check HEAD` pass after this revision. The supplied script checks scope,
net lines, literal ADR status and whitespace only; its “No code tests run” message
describes that script, not the independent commands recorded above.

## Stage 1 — closed pure evaluator gate, separate from activation

The first source slice takes already-decoded in-memory values: ordered unique class
vocabulary, exact evaluation split name, complete group-to-split declarations,
labeled sample records (sample_id, group_id, split, label), and baseline/candidate
prediction records (sample_id, prediction). Labels and predictions are class strings.
All labeled records must belong to the selected evaluation split; prediction ID sets
must equal the labeled ID set exactly, with no duplicates. Every used group must be
declared in that split, every declared evaluation group must be represented, and
no group may belong to multiple splits. Non-evaluation group declarations may be
retained to check declared separation; this does not prove actual training behavior.
No row-order alignment or implicit normalization/inference is allowed. Enforce O03's
100000-row/group, 64-class, 256-UTF8-byte ID and 64-byte class ceilings on these values.
Artifact byte decoding, frozen canonical provenance binding and CPU/deployment profile
are later boundaries, not silently claimed by this in-memory evaluator.

For both models, compute integer confusion counts over the same labeled rows.
Accuracy is exact correct/N; operational score is candidate accuracy minus baseline
accuracy, rendered once to six decimal places ROUND_HALF_EVEN. Compute per-class
precision TP/(TP+FP), recall TP/(TP+FN), F1 2TP/(2TP+FP+FN). A zero denominator yields
None/unavailable for that metric; F1 is calculated directly from counts, not from
rounded precision/recall. Each macro average is unavailable if any declared-class
component of that metric is unavailable; otherwise its exact arithmetic mean over
all declared classes is rendered once. Never silently omit a class or replace an
undefined denominator with zero. Preserve ordered class identity and integer counts.

The Stage 1 gate requires independent literal/golden cases for improvement/tie/worse,
class imbalance, absent classes, zero denominators, ordering/alignment, malformed and
oversized values, declared group overlap and exact rounding ties. Domain is pure and
has no ORM/transport/provider/filesystem dependencies. Source tests must distinguish
observed accuracy from generalization/significance and unknown-fault discovery.
No PG/deployment benchmark is needed to claim ONLY this pure behavior. Full O03
end-to-end measurements, typed provenance and the reviewed forward guard manifest
remain necessary before enabling a production consumer or writing any node.


## Commander Stage 1b authorization — bounded evidence bytes, 2026-10-28

Separately authorize a pure Application-layer codec for four supplied in-memory byte strings (labels, baseline predictions, candidate predictions, protocol), each at most 16 MiB, and a closed immutable tuple of four expected lowercase SHA256 digests. Reject oversize/type/hash mismatch before decode or parse. Verify exact bytes before strict UTF-8 decoding; no BOM, no normalization or inferred alignment. This is no file/network I/O, no admission, no canonical state or trust credential.

CSV uses Python csv strict parsing with exact ordered headers from O03, exact row widths, nonempty data and at most 100000 rows per table. Header duplicates/extra/missing fields and blank data rows reject. Protocol byte profile v1 has exactly three JSON keys: evaluation_split (string), classes (array of strings), groups (array of objects with exactly group_id and split strings). No version member is present; this paragraph names the artifact format. Reject duplicate JSON keys at every level, unknown keys, non-finite constants, malformed UTF-8/JSON/CSV, invalid types and depth/decoder errors with sanitized VALIDATION_ERROR. Reuse Stage1 Protocol/Group/LabeledSample/Prediction and evaluate for exact class/ID/group bounds and arithmetic; no duplicated metric implementation.

A closed immutable expected-hash value and internal evaluate_bytes entrypoint may return existing Evaluation only. Real ArtifactStore reads, bounded read adapter, production composition, accounting/SQL/node admission and empirical research remain separately blocked. The owner delegated this narrow code authorization; the production ADR remains PROPOSED. No SQL guard scaffolding is authorized by this codec scope.


## Commander Stage 1c authorization — bounded local CAS reader, 2026-10-28

Authorize an additive BoundedArtifactReader Protocol with open_bounded(identity: str, *, max_bytes: int) -> bytes and that method on the existing filesystem CAS adapter. Existing ArtifactStore Protocol/open/put/verify behavior remains unchanged. This is infrastructure support for O03, no admission or production activation. Accept existing canonical bare or sha256-prefixed lowercase digest identity, exact string type; max_bytes is exact int 1..16777216 (bool rejects). Empty content may be read within a positive capacity.

Read only a regular local CAS file, never follow a final-component symlink or block opening a FIFO/special file. Use descriptor-based validation and bounded at-most max_bytes+1 read, without trusting stat size alone; reject oversize, nonregular/corrupted content and verify exact content hash before returning bytes. Close descriptors on every outcome. CAS root and parent directories remain trusted operator-controlled infrastructure; no claim of hostile parent-directory sandboxing or hard I/O latency bound. Invalid value/size/content raises static ValueError, OS read/not-found failures retain existing low-level OSError semantics. No writes by the new method, no dependency or scientific-state changes.

Tests may compose real temporary CAS reads with the accepted pure codec to demonstrate file bytes to literal metrics. The future core consumer must still call this only after genuine atomic admission and outside DB locks; no such wiring, budget action, SQL guard scaffold or activation is authorized here.


## Commander Stage 1d authorization — pure v2 material contracts, 2026-10-28

Authorize only closed immutable Application value/command/result DTOs and actual canonical material serialization/hash computation for the two O06 v2 commands. The seven-reference/eight-hash/generation binding is typed data, not proof of frozen owner existence, authority or capability. Reproduce all eight literal UTF8 vectors exactly, flatten binding fields as specified; preserve v1 serializers/materials unchanged. Authenticated actor enters material through the same trusted-boundary convention as existing command contracts, never as a new authority flag. Reuse existing UUID/NFC/reason/integer/decimal/resource validators and canonicalization where applicable. SUCCEEDED requires paired non-NULL score/evaluator_version, with score an accuracy delta in [-1,1]; all other outcomes have neither. Original reservation-dependent checks still belong to future repository/service guards. No IO, service execution, persistence, registry, migration, budget/node mutation or activation. Closed result DTO follows O06 existing pointer/shape rules; it creates no catalog columns. This scoped code authorization does not accept the production amendment.


## Commander Stage 2 closed scope — selected 2026-10-28, pending independent review

The disabled forward-schema/guard slice may be separately authorized after independent review of this exact document head. The production amendment stays PROPOSED. O09 catalog delta remains exactly nine existing function bodies, four new validators, seven existing CHECK replacements, eight nullable binding columns, seven RESTRICT FKs and one shape CHECK. No tables/indexes/triggers/grants or later service wiring. `pr316d1_enabled()` remains literal false under every caller/GUC; no test or production writer may enable it in this slice. Confirm sole0082 head at actual dispatch before allocating0083.

Material closure: reconstruct v2 deadline_seconds from immutable reserved wall W, enforce requested duration equals W and exact stored deadline/epoch; reject shorter representational DTO requests, do not clamp and do not add another duration column. Preserve all eight golden material strings/digests.

Distinct reason ownership is intentional: v2 admission reason is the associated task-event reason; mutation_reason is the node mutation reason and its NODE_APPENDED search-event reason. These two facts may differ. New v2 receipt dispatch must occur before the legacy search validator path and invoke the v2 validator, which checks each owner, exact counts/links and both independent text values in reconstructed material. Keep search-event.reason equal to node.mutation_reason; do not apply the old task-event/search-event reason equality to this new compound command. All old v1 branches and their equality checks remain unchanged. The existing unequal-reason golden admission examples remain valid positive shape fixtures, conditional on real state/authority and later activation, not reclassified as denial fixtures. No new reason column is needed.

Name the new validated shape CHECK `pr316d1_reservation_binding_shape_ck`; name the seven new RESTRICT FKs `pr316d1_labels_av_fk`, `pr316d1_baseline_predictions_av_fk`, `pr316d1_candidate_predictions_av_fk`, `pr316d1_protocol_av_fk`, `pr316d1_evaluator_av_fk`, `pr316d1_dataset_snapshot_fk`, `pr316d1_metric_version_fk`. Their targets and all-null legacy/complete-v2 ownership are exactly O02. Current-profile score bounds/outcome pairs and material fields follow the accepted pure v2 contracts; frozen references remain canonical metadata, not a proof of byte reads, actual evaluation or trust.

This stage must prove disabled admission, forward catalog compatibility, typed binding ownership and byte reconstruction. It does not prove a production capability, measured deployment allowance, real positive Application admission, pricing, end-to-end performance or full PR3-16 completion. Those remain separately blocked; do not invent them or weaken existing guards.


### Commander Stage 2 implementation authorization — 2026-10-28

After independent read-only review PASS/no P0/P1 at8cbc9afb34a0c71699fc84f9ee9bce1740e2ba36, accept only the selected disabled Stage2 contract and authorize one forward migration, matching ORM columns, real-PG18 upgrade/catalog/negative/legacy-regression tests and exact current-head maintenance. The prospective-evidence P2 is corrected above. Sole0082 was rechecked before allocating `0083_bearing_evaluation_guards` after `0082_experiment_search_core`. No code/PG completion, positive production admission, role grant, service/registry wiring or full ADR acceptance is implied. All checks and independent final source review remain required before publication.
