# ADR-0027 — PR3-16 D1 paired bearing-evaluation amendment

Status: PROPOSED for the production amendment. Separately scoped commander
authorizations below and in the companion contract do not activate production. The detailed proposed contract and blockers are in
[the D1 contract](../../phase3/design/PR3-16-d1-amendment-contract.md).

## Decision proposed 2026-10-28

Replace the earlier open-ended producer/evaluator questions with one bounded operation:
compare already-produced candidate and baseline predictions against identical frozen
labels, sample IDs and split/group protocol. Compute classification accuracy and
imbalance diagnostics deterministically. This is an operational observation, not a
scientific Measurement or Claim, a training job, a provider invocation, Run execution,
or evidence of a new physical fault. A new-fault candidate requires independent
verification in a separately authorized track. Fixture results do not establish
empirical superiority. No PR3-17 ranking or selection is authorized.

A new versioned compound Application command reserves existing task budget and appends
one PROPOSED node atomically. A trusted core consumer evaluates outside the transaction
and settles in a separate attributed command. Prior stops deny; only a stop proven to
arise from this transaction consuming its own last unit permits this node, with a
durable task stop and no implicit session closure. Preserve sticky stops, UNKNOWN
charges, current entitlement after waits, and original receipt replay. ADR-0026 and
ADR-0029 remain controlling except for the specifically proposed guard amendment.

Propose one immutable typed provenance tuple on the existing reservation: five
`ArtifactVersion` roles, one `DatasetSnapshot`, one `MetricDefinitionVersion`, and
one consumer-generation UUID for attribution only. Seven nullable RESTRICT FKs and
one nullable UUID distinguish all-null legacy reservations from complete v2 bindings.
Usage inherits the tuple through its existing reservation FK; legacy settlement must
not settle v2 reservations. Source Runs are omitted: evaluation consumes supplied
predictions and association would not prove their production. No new table or truth
owner is proposed. The companion contract specifies checks, material and catalog delta.

Admission validates typed identity, project, frozen state and stored canonical hashes
using DB metadata only, plus bounded no-I/O registered evaluator digest checks.
Stored metadata does not prove bytes were read. After admission commits, outside DB
locks and before parsing/evaluation, the consumer reads ArtifactStore bytes and
verifies their byte hashes. Deterministic mismatch settles FAILED with no score and
admitted counters retained; uncertain completion remains UNKNOWN. Metadata denial
before admission commits has zero effects. Stage 1 remains purely in memory.

Under the existing task lock, first v2 admission rejects legacy scored history in
the same step. Reciprocally, fresh legacy settlement rejects a nonnull score if that
step has any v2-owned reservation, including admitted/in-flight work. Recheck after
waits and at deferred completion so either ordering prevents mixed comparisons.
No-score legacy accounting remains available under existing rules, and legacy
settlement in steps without v2 reservations retains its behavior and v1 replay.

Production composition, registration/revocation and recovery coordination, and the
deployment resource/pricing profile still require concrete evidence and separate
acceptance before activation. No dataset or performance result is supplied here.

## Staging and compatibility

1. Concrete pure evaluator/value contract and tests, without activation.
2. Minimal forward PostgreSQL guards; admission still denied until Application wiring.
3. Atomic admission and attributed settlement with the concrete core consumer.
4. Real PostgreSQL regression/CI and independent acceptance. Commander separately
   authorizes each actual code slice after review.

Recheck the sole migration head before a forward migration after
`0082_experiment_search_core`; never edit 0078/0080/0081/0082. Preserve v1 material,
replay, guards and ACLs, all scientific hashes, and the current 10-node/3-depth/
11-event/zero-link read profile. Future writer extensions first require compatible
measured complete-response bounds. Before migration use, rollback removes only the
new forward objects; after use, preserve immutable history and use forward repair.
No deletion/refund of historical gaps or UNKNOWN outcomes is permitted.

The previous 2026-10-27 question-only draft is superseded by these selections; its
historical evidence is available in version control. This proposal is not acceptance,
implementation evidence, or permission to run a real bearing study.

## Separately reviewable Stage 1 scope

Stage 1 is only a pure in-memory paired evaluator and closed value contract. It may
be reviewed/authorized separately while this production amendment stays PROPOSED.
It performs no Artifact I/O, SQL/UoW, budget mutation, producer registration, node
admission, scientific Measurement/Claim persistence or Run execution. No deployment
pricing/vector/latency proof is inferred from its tests. O02 arithmetic and the
explicit Stage 1 bounds/undefined-value rules in the companion contract must be
closed before its source implementation; O01/O03/O04/O09 activation dependencies
remain blocking for subsequent production slices. Local probe fixtures establish
computation behavior only, never an empirical bearing diagnosis improvement.

### Commander Stage 1 authorization — 2026-10-28

After independent cold review PASS/no P0/P1 at `1cf17316`, the commander accepts only
the separately scoped pure Stage 1 in-memory numerical/value contract and authorizes
its implementation plus unit/architecture tests. The review's P2 cross-reference is
corrected: end-to-end ArtifactStore/PG/resource proof belongs to Stage 3, not Stage 1.
The owner delegated this decision. ADR-0027's production amendment stays PROPOSED;
no Artifact I/O, canonical provenance binding, migration, capability registration,
budget mutation or node activation is authorized by this acceptance.


### Separately reviewable Stage 2 selection — 2026-10-28

The commander selects the exact disabled O09 catalog slice for separate review before code authorization; production remains PROPOSED. New v2 deadline_seconds equals reserved W and is reconstructed from that immutable field; exact transaction-epoch deadline must fit the existing earliest-reservation task origin cap, otherwise deny without clipping. Registered remaining-phase allowance is a later mandatory Application check, not guessed from W. Preserve the two independent existing reason owners: accounting task-event reason and node/search mutation reason may differ for v2 only, validated by a new early v2 dispatch; all legacy checks remain unchanged. No extra storage is needed and all eight frozen serializer/result examples retain their meaning. No enablement, new table, production grant or service wiring belongs to this slice. See the companion Stage2 section for exact named constraints and acceptance boundary.


### Commander disabled Stage 2 acceptance — 2026-10-28

Accept only the separately reviewed disabled schema/guard contract at8cbc9afb, after independent read-only PASS/noP0/P1. Authorize0083 forward migration, ORM binding columns and required PG18/regression/current-head checks under the exact companion manifest. Correct the prospective proof wording; no guard or new migration test has yet passed. Enablement stays literal false, no new production grants/services/registry; all unclosed production facts remain blocking and the full amendment stays PROPOSED.

### 隔离参考验证 bootstrap 决议
最终 T_max、J_max、W 和各阶段剩余余量必须来自真实正向 admission、replay、settlement、完整 I/O 与竞争负载测量；生产 profile 必须基于实际生产环境和计费事实。为了获得这些测量，允许在经实际受保护 provisioning 且经单独审查的唯一隔离参考部署上，以真实固定 consumer 和操作员记录的验证硬限额进行受限验证。该限额是 OPERATOR POLICY，不是实测生产 W、生产 profile 或信任凭据。缺少实际环境事实、验证限额或任何门控时拒绝启动和新工作。
前向迁移及候选激活仅可存在于经审查、未发布的候选分支，并仅用于核准的精确隔离参考部署；新修订号须在 PR32 实际合并后重新核对唯一迁移 head 才分配。源代码审查、发布排除及部署权限必须阻止该迁移或候选包进入生产；DB 精确身份核对仅防事故，不能证明授权。0083 文件及其历史 source definition 永久保持字面 `SELECT false`；另行明确授权的新前向迁移可仅在该参考 DB 替换现有 helper 的运行时函数体。禁止临时 ALTER、测试开关、禁用 trigger、直接播种已提交 v2 行及用 GUC 赋权。
参考验证不得满足生产 profile/type gate；不得由调用方 reference 标志、序列化 token、generation UUID、路径或 hash 赋予信任。真实 consumer 使用进程内对象身份 capability、注册和覆盖实际 commit/撤销的同一互斥；generation 只归属。Application 通过既有 port 使用唯一基础设施适配器，不能直接做文件系统 I/O。无新运行时 canonical schema、表或签名 JSON 真相源。
生产发布和激活继续阻断，直到真实 PG 正向测试、每 profile 至少 30 次完整运行及最终资源 profile、无 P0/P1 的独立审查、实际生产 writer/operator/DB-CAS 绑定、负载及计费事实全部完成并分别获接受。参考验证成果不能代替生产证据。

The commander, under the owner’s standing delegation, accepts this limited reference-only calibration policy subject to review of the exact document diff before publication. This acceptance does not authorize provisioning, implementation, revision allocation, migration apply, reference activation or production. Each requires a separate commander stage gate and actual supporting facts; no duplicate user permission is required. The full production amendment remains PROPOSED. PR32 head `de9dded06d5717bf50351998b39f3b9836fab977` merged as `e65b3b4303fab47524e9c655587bfb1fbaa1697d`; the current main baseline is `88aaf0253c2b2563cc3595acef78638f0c154a68`. Independent 404 review PASS closed the corrected 401 FAIL findings for the draft only; it was a bounded review, not a test or execution approval.
