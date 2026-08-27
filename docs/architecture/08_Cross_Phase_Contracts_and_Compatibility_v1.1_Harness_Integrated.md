# ResearchBase Cross-Phase Contracts and Compatibility

> **版本**：v1.0  
> **状态**：SYSTEM DESIGN CLOSURE / READY FOR FINAL REVIEW  
> **日期**：2026-08-26  
> **适用范围**：Phase 1–4 全部模块、开发团队、Agent Runtime、Adapter、数据库迁移、API、测试与发布  
> **规范性**：本文件定义跨阶段不可破坏的契约。任何后续实现若与本文件冲突，必须通过 ADR + Compatibility Review，不得由单个开发者或 Agent 静默修改。

---

# 0. 目的

本文件解决：

```text
Phase 1 给 Phase 2 什么？
Phase 2 给 Phase 3 什么？
Phase 3 给 Phase 4 什么？

哪些对象永久稳定？
哪些 API 可以扩展？
哪些字段可以加？
哪些 breaking changes 禁止？
如何迁移？
如何判断系统设计真的冻结？
```

最终目标：

> **后续开发阶段可以增加能力，但不能通过重定义过去的科学对象和 provenance 语义来“前进”。**

---

# 1. 设计层级

```text
System Architecture v1.2
        ↓
Phase 1 Spec v1.1
        ↓
Phase 2 Spec v1.0
        ↓
Phase 3 Spec v1.0
        ↓
Phase 4 Spec v1.0
        ↓
Cross-Phase Contracts v1.0
```

优先级：

1. 全系统架构原则；
2. Cross-Phase Contracts；
3. 对应 Phase Development Specification；
4. ADR；
5. 具体实现文档。

若阶段文档之间冲突，以更高层不变量和 Cross-Phase Contract 为准。

---

# 2. 永久稳定的 Canonical Scientific Core

以下对象从 Phase 1 起视为系统长期稳定核心：

```text
Project
ActorIdentity

ResearchQuestionVersion
HypothesisVersion
ExperimentSpecVersion

DatasetSnapshot
ArtifactVersion
Run

MetricDefinitionVersion
Measurement
StatisticalResult

ClaimVersion
EvidenceRelation

AuditFinding
ImpactAssessment
CorrectionRecord
```

Phase 2 扩展稳定核心：

```text
LiteratureSource
SourceVersion
LiteratureEvidence
ScientificConclusionVersion
Publication
ManuscriptVersion
InternalReviewRecord
DecisionRecord
ApprovalRequest
ApprovalDecision
ApprovalGrant
SubmissionVersion
```

Phase 3 运行时稳定核心：

```text
ResearchTask
ResearchTaskStep
AgentVersion
AgentExecutionInstance
CapabilityInvocation
HumanCheckpoint
ExecutionBudget
ExperimentSearchSession
ExperimentSearchNode
SearchDecisionRecord
```

Phase 4 Meta 层稳定对象：

```text
ResearchProgram
ResearchProgramMilestone
SkillVersion
StrategyEvaluation
MemoryItem
ExperimentCampaign
ReplicationTask
ReplicationAssessment
ReviewEnsemble
```

---

# 3. 永久稳定的语义边界

以下等式/不等式不得被后续阶段重新解释：

```text
ExperimentSpec ≠ Run
Hypothesis ≠ Claim
Claim ≠ ScientificConclusion
Dataset ≠ DatasetSnapshot
Artifact ≠ ArtifactVersion
Source ≠ LiteratureEvidence
SearchResult ≠ LiteratureEvidence
Citation ≠ ScientificSupport
Discussion ≠ Decision
Review ≠ Decision ≠ Approval
Manuscript ≠ ScientificTruth
Agent Output ≠ Canonical State
Working Memory ≠ Canonical Scientific Memory
Strategy Selection ≠ Scientific Decision
Search Score ≠ Scientific Validity
Replication Result ≠ automatic invalidation of original work
```

---

# 4. 永久稳定的全局 Invariants

```text
INV-001 One canonical fact has one owning domain.
INV-002 Formal provenance uses exact frozen/versioned references.
INV-003 Frozen/immutable scientific history cannot be silently rewritten.
INV-004 Deterministic Fact > Review/Decision/Approval/Agent.
INV-005 Formal scientific paths must satisfy Frozen Provenance Closure.
INV-006 Agent and Human use the same Application Command/Query boundary.
INV-007 External Agent/Strategy/Framework does not own scientific state.
INV-008 Failed, negative, stale and pruned scientific history remains traceable.
INV-009 Project archive does not cascade-delete scientific provenance.
INV-010 Cross-domain reverse navigation uses Query/Projection, not duplicate truth.
INV-011 External side effects remain distinct from approval and internal intent.
INV-012 Autonomy does not imply scientific/governance authority.
INV-013 Derived memory cannot override canonical scientific facts.
INV-014 Any scientific semantic change produces a new Version/new record.
INV-015 Provider/framework/vendor-specific state cannot leak into Canonical Core schema.
```

---

# 5. Phase 1 → Phase 2 Contract

Phase 2 可假设 Phase 1 提供：

```text
create/revise/freeze ResearchQuestion/Hypothesis/ExperimentSpec
create DatasetSnapshot
create/freeze ArtifactVersion
create/start/finish Run
record Measurement
record StatisticalResult
create/revise/freeze Claim
link Evidence
get Run provenance
trace Claim to Runs
get downstream impact
Frozen Provenance Closure validator
```

Phase 2 MUST NOT：

```text
change Run meaning
change Claim freeze semantics
allow Measurement update
replace DatasetSnapshot with raw path
replace ArtifactVersion with mutable file pointer
treat Citation as EvidenceRelation
```

---

# 6. Phase 2 → Phase 3 Contract

Phase 3 可假设 Phase 2 提供：

```text
LiteratureSource / SourceVersion
LiteratureSearchPlan/Run
LiteratureEvidence
ResearchBrief Artifact
ScientificConclusionVersion
ManuscriptVersion
InternalReviewRecord
DecisionRecord
Approval basic
scientific trace queries
```

Phase 3 MUST NOT：

```text
store STORM/PaperQA internal state as scientific truth
make Agent discussion equal Decision
make WritingAgent text equal Claim
allow ReviewerAgent to mutate Manuscript
make Agent memory replace LiteratureEvidence
```

---

# 7. Phase 3 → Phase 4 Contract

Phase 4 可假设 Phase 3 提供：

```text
ResearchTask
TaskGraph
AgentVersion
AgentExecution
CapabilityInvocation
CapabilityGateway
HumanCheckpoint
Budget/Termination
Working Memory
Experiment Search
Sandbox/Compute/Coding adapters
Agent evaluation
```

Phase 4 MUST NOT：

```text
bypass CapabilityGateway
self-promote Skill
self-escalate autonomy
hide failed search branches
let Memory replace canonical source
redefine AgentExecution as scientific evidence
```

---

# 8. API Compatibility Policy

Application API 分三类：

## 8.1 Stable Core API

一旦 Phase Exit 通过，以下类别视为 stable：

```text
canonical create
version create/revise/freeze
immutable record create
trace/provenance query
impact query
task execution provenance
```

Breaking changes 必须 major compatibility review。

## 8.2 Extensible API

允许新增：

```text
optional request fields
new query filters
new enum values if forward-compatible
new read-model fields
new adapters
new strategy/capability types
```

但不能改变已有字段语义。

## 8.3 Experimental API

Agent/advanced experimental endpoints 可标：

```text
experimental/*
```

只有升级为 stable 后才进入长期契约。

---

# 9. Command Compatibility

已有 Command 名称/语义不得复用成新意义。

错误：

```text
freeze_claim_version
Phase 1 = freeze statement+evidence
Phase 3 = “temporarily lock UI”
```

必须新命名。

Command 扩展 SHOULD 使用可选字段，不要求已有 caller 提供新必填字段，除非 major migration。

---

# 10. Query Compatibility

Query DTO 可以增加字段，但不得：

```text
把原 frozen ID 改成 current/latest
删除 provenance path
将 warning 静默升级成 success
混淆 support path 与 citation path
```

---

# 11. Enum Compatibility

新增 enum value 要求客户端能处理 unknown value。

推荐：

```text
string enums
```

不依赖数据库/客户端 ordinal。

禁止重用旧 enum value 表达新语义。

---

# 12. Database Compatibility

核心规则：

```text
additive migration preferred
no hard delete of scientific history
no destructive type change without backfill
no FK weakening for convenience
no replacement of concrete provenance FK with JSON
```

---

# 13. Migration Classes

## 13.1 Safe Additive

```text
add nullable column
add table
add index
add relation
add new enum value with compatibility
```

普通 migration review。

## 13.2 Semantic Migration

```text
split entity
merge entity
change ownership
change frozen semantics
change reference target
change meaning of field
```

必须 ADR + data migration plan + provenance audit。

## 13.3 Breaking Migration

```text
delete canonical table
rewrite historical scientific values
drop immutable history
collapse Version into mutable entity
replace exact refs with latest pointer
```

默认禁止。

---

# 14. Immutable Historical Data Policy

历史对象：

```text
Run
Measurement
StatisticalResult
FROZEN Version
DecisionRecord
ReviewRecord
ApprovalDecision
AgentExecution
SearchDecision
```

不得用普通 UPDATE 修正 material facts。

使用：

```text
new Version
new record
CorrectionRecord
ImpactAssessment
superseding relation
```

---

# 15. Reference Compatibility

Material scientific provenance：

```text
exact concrete FK / exact version ID
```

横切对象可以用：

```text
typed external locator
```

但不能成为主链唯一引用。

---

# 16. Hash Compatibility

一旦某对象 hash algorithm/material-field contract 发布：

- 算法版本必须可识别；
- 新 hash scheme 不覆盖旧 hash；
- canonical serialization 版本化；
- old content_hash 继续可验证。

建议：

```text
hash_scheme = sha256-cjson-v1
```

---

# 17. Time Compatibility

所有 canonical timestamp：

```text
UTC
timezone-aware
immutable creation timestamps
```

不得后续切换成本地时间语义。

---

# 18. Application Boundary Compatibility

未来新增：

```text
Web UI
CLI
Agent Runtime
External API
Notebook SDK
```

都必须通过 Application Command/Query。

禁止：

```text
Agent direct repository
UI direct ORM
notebook direct DB writes
```

---

# 19. Adapter Compatibility

Adapter 可以替换：

```text
STORM
PaperQA2
Codex
OpenHands
LLM provider
Search provider
Compute provider
Runtime framework
```

Canonical Core 不迁移。

Adapter upgrade 需要：

```text
version pin
compatibility test
security/license review
golden task regression
```

---

# 20. Strategy Compatibility

Strategy 可以新增/替换。

Strategy 只能影响：

```text
workflow choice
candidate generation
tool use
search policy
```

不能改变：

```text
Run semantics
Measurement semantics
Claim freeze
Evidence support
Approval semantics
```

---

# 21. Skill Compatibility

SkillVersion immutable。

Upgrade：

```text
new SkillVersion
```

历史 AgentExecution 继续引用旧版本。

---

# 22. Memory Compatibility

Memory schema可扩展，但：

```text
source_refs
trust_level
validity_status
project_scope
```

为长期稳定字段。

任何 Memory 系统替换都必须能重建 derived memory。

---

# 23. Agent Runtime Framework Compatibility

LangGraph/DeepAgents/DeerFlow/OpenHands runtime 等属于实现选择。

ResearchTask canonical state 不得仅存在框架 checkpoint。

换 runtime 后必须仍可恢复：

```text
task
steps
agent executions
capability invocations
checkpoints
budgets
search tree
```

---

# 24. Cross-Phase Error Compatibility

错误码一旦 stable：

```text
code
semantic category
retryability
```

不得静默改变。

可增加：

```text
details
metadata
new codes
```

---

# 25. Observability Compatibility

长期 correlation identifiers：

```text
request_id
correlation_id
causation_id
project_id
task_id
agent_execution_id
```

字段命名应保持稳定。

---

# 26. Security Compatibility

后续阶段只能收紧默认权限，不能静默放宽：

```text
sandbox
network
secrets
cross-project memory
external effects
skill install
```

放宽必须显式 Policy/ADR。

---

# 27. Governance Compatibility

Phase 2 basic Approval → 后续完整 Authority engine 时：

```text
ApprovalRequest
ApprovalDecision
ApprovalGrant
```

不得废弃。

完整 engine 应增加：

```text
eligibility
authority domain
scope
COI
delegation
policy
```

而不是重写历史 ApprovalDecision。

---

# 28. Publication Compatibility

Phase 2 SubmissionVersion 在后续接 venue submission 时保持不变。

新增：

```text
Command
ExternalEffect
VenueSubmissionRecord
```

而不是把 SubmissionVersion 改成“已提交状态记录”。

---

# 29. ScientificConclusion Compatibility

ScientificConclusionVersion 永远是综合科学判断。

不得后续把它降级成：

```text
manuscript paragraph
summary cache
LLM answer
```

---

# 30. Literature Compatibility

SourceVersion lineage 永久保留。

Retracted/corrected：

```text
new version/status/impact
```

不覆盖旧 version 内容。

---

# 31. ResearchTask Compatibility

ResearchTask 是 workflow orchestration identity。

Phase 4 ResearchProgram 是上层 aggregate：

```text
ResearchProgram
→ ResearchTask[]
```

不得把 ResearchTask 变成 Program。

---

# 32. Experiment Search Compatibility

Phase 3 SearchSession/Node 是具体自治搜索 lineage。

Phase 4 Campaign 是规模化调度层。

```text
Campaign
→ SearchSessions / Runs
```

不是替代。

---

# 33. Deletion Policy

默认：

```text
scientific/history: RESTRICT
operational cache: delete allowed
derived index: rebuildable
temporary sandbox: delete allowed
```

Canonical records 不物理删除，除非法规/安全强制 redaction，并保留 tombstone/audit。

---

# 34. Archival Policy

Project archive：

```text
stop new writes
retain queries/provenance
retain artifacts according retention policy
```

不级联删除。

---

# 35. Backward Read Compatibility

新版本服务 SHOULD 能读旧 Phase 数据。

如果旧字段缺失：

```text
explicit unknown/default projection
```

不能发明历史值。

---

# 36. Forward Compatibility

客户端应对：

```text
unknown enum
extra response field
new warning
```

保持容忍。

---

# 37. Versioning Policy

文档：

```text
major.minor
```

API：

```text
semantic behavior version
```

Schema：

```text
Alembic revision + schema compatibility classification
```

Adapter：

```text
adapter version + upstream version/commit
```

Agent：

```text
AgentVersion + prompt/config/model profile
```

---

# 38. ADR Trigger List

以下必须 ADR：

```text
new Canonical Entity
change Canonical ownership
change frozen semantics
change Run seal point
change Claim evidence freeze
change DatasetSnapshot rule
change ArtifactVersion semantics
introduce generic polymorphic main-chain ref
switch canonical DB technology
introduce microservices
change Application Boundary
change approval semantics
change autonomy ceiling
add new external side effect
change cross-project memory default
```

---

# 39. ADR Minimum Content

```text
context
problem
options
decision
scientific integrity impact
data migration
API compatibility
security
rollback plan
tests
affected phases
```

---

# 40. Architecture Compatibility Tests

CI 建议维护：

```text
test_phase1_core_contracts
test_phase2_literature_publication_contracts
test_phase3_agent_runtime_contracts
test_phase4_meta_contracts
test_no_main_chain_soft_reference
test_no_frozen_mutation
test_no_cross_project_memory_default
test_no_agent_direct_db
test_no_vendor_specific_core_schema
test_no_scientific_cascade_delete
```

---

# 41. Cross-Phase Golden Regression

每个 Phase 后继续跑：

## G1 Core Experiment

```text
Hypothesis → Spec → Run → Measurement → Claim
```

## G2 Literature

```text
Question → Search → SourceVersion → LiteratureEvidence → Conclusion
```

## G3 Manuscript

```text
Claim/Conclusion → Manuscript → Review → Revision
```

## G4 Agent

```text
ResearchTask → AgentExecution → Capability → Candidate → Canonical
```

## G5 Autonomous Search

```text
Search tree → Runs → negative/pruned history retained
```

## G6 Memory

```text
Canonical source → derived memory → stale propagation
```

---

# 42. Release Gates

## Phase 1 GO Exit

Core provenance complete.

## Phase 2 GO Exit

Literature/publication trace complete.

## Phase 3 GO Exit

Agent runtime controlled/autonomous bounded.

## Phase 4 GO Exit

Advanced memory/skills/campaign governance complete.

## System Release Gate

必须：

```text
all phase exit tests pass
cross-phase regression pass
migration inventory complete
adapter inventory complete
security review pass
provenance closure pass
no P0/P1 architecture issue
```

---

# 43. System Freeze Categories

## FROZEN

```text
canonical object semantics
provenance rules
immutability rules
application boundary
scientific/governance distinctions
```

## EXTENSIBLE

```text
adapters
strategies
skills
read models
UI
provider integrations
benchmark suites
```

## DEFERRED

```text
microservices
global knowledge graph
full enterprise IAM
full financial ERP
full IRB platform
```

---

# 44. Final Architecture Compatibility Principle

ResearchBase 后续任何新功能都应该优先问：

```text
Can this be expressed as:
Entity?
Version?
Relation?
Assessment?
Artifact?
Event?
Strategy?
Capability?
Derived Memory?
```

只有现有范式无法表达时才新增 Canonical Schema。

---

# 45. Implementation Start Gate

所有设计完成后，开始开发前必须正式确认：

```text
[ ] System Architecture reviewed
[ ] Phase 1 Spec reviewed
[ ] Phase 2 Spec reviewed
[ ] Phase 3 Spec reviewed
[ ] Phase 4 Spec reviewed
[ ] Cross-Phase Contract reviewed
[ ] No unresolved architecture P0/P1
[ ] Phase ordering accepted
[ ] Tech stack accepted
[ ] Initial ADR registry created
```

只有满足后：

```text
IMPLEMENTATION_GO = TRUE
```

否则：

```text
IMPLEMENTATION_GO = FALSE
```

---

# 46. Recommended Development Order

开发阶段仍严格：

```text
Phase 1
STOP / review
↓
Phase 2
STOP / review
↓
Phase 3
STOP / review
↓
Phase 4
STOP / final release review
```

即使所有设计提前完成，也不建议一次实现四个 Phase。

---

# 47. Team Rule

中级程序员可以做实现决策：

```text
function decomposition
query optimization
test fixture
UI details
internal helper
```

不得自行做：

```text
canonical schema change
scientific semantics change
cross-phase contract break
frozen rule relaxation
authority relaxation
```

---

# 48. Coding Agent Rule

Codex/Coding Agent 每次 PR 必须收到：

```text
System Architecture
Current Phase Spec
Cross-Phase Contract
PR scope
```

不得只给单独 ticket 而缺少架构上下文。

---

# 49. Documentation Sync Rule

任何 ADR 导致规范变化时：

```text
ADR
→ System Architecture if affected
→ Phase Spec
→ Cross-Phase Contract if affected
→ Tests
```

禁止“代码已经变了，文档以后再补”。

---

# 50. Final Cross-Phase Invariants

```text
CP-INV-001 Later phases extend earlier phases; they do not redefine earlier canonical semantics.
CP-INV-002 Every formal scientific statement remains traceable to exact experimental and/or literature evidence.
CP-INV-003 Every Agent-produced canonical object remains traceable to AgentExecution and promotion action.
CP-INV-004 Every Agent execution remains separate from scientific evidence unless its produced canonical artifacts/results explicitly enter the evidence graph.
CP-INV-005 Every autonomous experiment remains a normal Run with exact frozen inputs.
CP-INV-006 Every negative/failed/pruned execution remains historically visible.
CP-INV-007 Every derived memory item remains traceable to its source and validity.
CP-INV-008 Every external integration remains replaceable without migrating canonical scientific state.
CP-INV-009 Every governance expansion preserves historical Review/Decision/Approval semantics.
CP-INV-010 Every schema migration preserves historical provenance unless an explicit governed redaction is required.
CP-INV-011 Human and Agent callers converge on the same Application boundary.
CP-INV-012 Scientific facts cannot be made true by Authority, Agent confidence, search score, review vote or memory.
CP-INV-013 Cross-project access and memory sharing remain deny-by-default.
CP-INV-014 All long-running autonomous activity has budget, termination and kill-switch controls.
CP-INV-015 System evolution must remain auditable through ADR, migration and regression tests.
```

---

# 51. Final System Design Closure

当本文件与 Phase 1–4 Specification 全部 Review 通过后，ResearchBase 设计状态为：

```text
System Architecture            FROZEN
Phase 1 Design                 FROZEN
Phase 2 Design                 FROZEN
Phase 3 Design                 FROZEN
Phase 4 Design                 FROZEN
Cross-Phase Compatibility      FROZEN

Implementation                 NOT STARTED
```

此后进入实现不是“继续架构探索”，而是：

> **在明确兼容性契约下按阶段施工、测试、Review 和迭代。**

---

# 52. Harness Cross-Phase Contract Addendum

The following invariants are normative across all phases:

```text
H-INV-001 Harness behavior remains external to canonical scientific truth.
H-INV-002 No external Skill/Plugin/Hook/MCP server directly mutates canonical persistence.
H-INV-003 ResearchBase invariants override conflicting third-party harness instructions.
H-INV-004 Production-relevant external harness dependencies are immutably pinned/resolved.
H-INV-005 Material Phase-3+ AgentExecution is attributable to a reproducible HarnessFingerprint.
H-INV-006 Scientific Skill output is candidate state unless explicitly promoted through Application Commands.
H-INV-007 Formal reviewer/auditor execution SHOULD be independent from authoring execution.
H-INV-008 Harness changes require evaluation/regression before production release.
H-INV-009 Skill routing respects phase, authority, capability and data-policy constraints.
H-INV-010 Failed materially relevant Skill/Agent executions remain auditable.
H-INV-011 A running agent cannot silently weaken or replace its own governing harness.
H-INV-012 STORM, EvoScientist and other research methods remain replaceable strategies/adapters, not owners of canonical state.
H-INV-013 External tool/MCP output is not canonical evidence until resolved and validated by the owning ResearchBase domain.
H-INV-014 Scientific facts cannot be established solely by Skill output, model confidence, search score or reviewer consensus.
H-INV-015 Harness reproducibility is part of Agentic Research Reproducibility.
```

## 52.1 Stable Phase Ownership

```text
Phase 1: engineering harness for development only; no product Agent Runtime
Phase 2: bounded scientific strategies/Skills via existing Application APIs
Phase 3: general Harness Runtime + Skill routing + AgentExecution fingerprint binding
Phase 4: governed dynamic composition/evolution on top of Phase-3 contracts
```

Later phases MUST NOT reinterpret Phase-1 coding harness evidence as canonical scientific AgentExecution retroactively.

## 52.2 Compatibility Rule for External Harness Changes

A dependency update that may change agent behavior requires:

```text
immutable revision change
→ release/change-note review
→ capability/security review when relevant
→ harness regression benchmark
→ lock update
```

A change affecting canonical schema or Application contracts additionally requires the existing ADR/migration/compatibility process.

## 52.3 Cross-Phase Evidence Precedence

Harness logs, Skill recommendations and Agent reviews are useful provenance/evaluation records but never outrank deterministic canonical facts. Existing deterministic fact precedence remains unchanged.

## 52.4 Final Closure Rule

The Harness layer is accepted only if it can be removed/replaced without migrating canonical scientific state. Replacing a harness may require preserving historical AgentExecution/fingerprint provenance, but MUST NOT require rewriting historical scientific facts.

