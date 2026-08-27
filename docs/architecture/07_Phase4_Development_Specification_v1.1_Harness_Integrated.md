# ResearchBase Phase 4 Development Specification

> **版本**：v1.0  
> **状态**：DESIGN COMPLETE / READY FOR CROSS-PHASE REVIEW  
> **日期**：2026-08-26  
> **上位设计**：`ResearchBase_全系统设计文档_架构补全版_v1.2`  
> **前置规范**：Phase 1 v1.1、Phase 2 v1.0、Phase 3 v1.0  
> **适用对象**：Tech Lead、Advanced Agent Runtime 开发人员、Research Memory/Strategy/Evaluation 开发人员、Scientific Governance 开发人员  
> **规范性**：本文件定义 Phase 4 的高级自治能力边界。Phase 4 必须建立在 Phase 1–3 全部 Exit Criteria 已通过的前提上，不得削弱 Frozen Provenance Closure、Deterministic Fact > Authority、Agent Output ≠ Canonical State、Human/Agent 共用 Application Boundary 等既有不变量。

---

# 0. Phase 4 定位

Phase 4 不是“完全自动科学家”。

Phase 4 的目标是：

> **在既有可信 Core 与受控 Scientific Agent Runtime 之上，引入可评估、可回滚、可治理的高级自治能力，使系统能够跨任务积累科研能力、自动选择研究策略、进行大规模实验探索、执行复制/新颖性/高级审稿任务，并支持长期科研计划，但仍保留明确的人类控制、预算、政策与科学事实边界。**

Phase 4 关注的不是更多 Agent 角色，而是：

```text
能力如何积累
策略如何改进
记忆如何跨任务复用
搜索如何规模化
结果如何复现/反驳
自治如何被治理
```

---

# 1. Phase 4 MUST / SHOULD / MAY / MUST NOT

## 1.1 MUST

```text
Skill Registry / SkillVersion
Skill Evaluation / Promotion / Rollback
Strategy Selection Engine
Strategy Evaluation History
Research Memory Index / MemoryItem
Cross-Task Memory Retrieval
Multi-Project Memory Policy
Long-Horizon ResearchProgram
ResearchProgramMilestone
Advanced Budget / Quota / Scheduling
Large-Scale Experiment Campaign
Campaign Branch / Batch Scheduling
ReplicationTask / ReplicationAssessment
Advanced Novelty Assessment
Advanced Reviewer Ensemble
Meta-Evaluation
Autonomy Escalation Policy
Long-Horizon Checkpointing
Kill Switch / Emergency Stop
Policy-driven capability escalation
```

## 1.2 SHOULD

```text
automatic strategy portfolio
contextual bandit / Bayesian strategy selection
skill transfer between projects with policy
agent-generated skill candidate
benchmark-driven skill acceptance
memory summarization / consolidation
experiment campaign parallelization
replication across datasets/seeds/environments
multi-reviewer consensus
scientific red-team strategy
cost-aware model routing
long-horizon planner
```

## 1.3 MAY

```text
self-improving prompt/strategy search
automatic tool composition
large-scale distributed experiment execution
cross-lab collaboration adapters
ontology-assisted memory organization
federated scientific memory
external benchmark leaderboard integration
autonomous replication campaigns
```

## 1.4 MUST NOT

```text
unreviewed self-modifying production code
self-granting higher authority
self-installing arbitrary untrusted skill
unbounded cross-project memory sharing
agent deleting adverse historical evidence
automatic publication based only on internal score
strategy optimization against hidden scientific truth labels
reward hacking by changing success criteria
permanent model/provider lock-in
scientific fact edits by memory consolidation
```

---

# 2. Phase 4 顶层架构

```text
Research Programs / Campaigns
        ↓
Long-Horizon Planner
        ↓
Strategy Selection Engine
        ↓
Skill + Capability Portfolio
        ↓
Phase 3 Scientific Agent Runtime
        ↓
Phase 1/2 Canonical Scientific State
        ↑
Research Memory / Evaluation / Replication
```

Phase 4 的核心是“Meta Layer”：

```text
how to research
what to remember
what to reuse
what to replicate
how to improve
```

而不是重新定义：

```text
what is a Run
what is a Measurement
what is a Claim
```

---

# 3. ResearchProgram

用于跨多个 ResearchTask 的长期研究目标。

```yaml
ResearchProgram:
  id: UUID
  project_id: UUID

  title: string
  objective: string

  status:
    PLANNED |
    ACTIVE |
    PAUSED |
    COMPLETED |
    TERMINATED |
    CANCELLED

  autonomy_ceiling:
    A0 | A1 | A2 | A3

  created_by: ActorId
  created_at: Instant
  started_at: Instant|null
  completed_at: Instant|null

  budget_policy_id: UUID
  memory_policy_id: UUID
  strategy_policy_id: UUID
  governance_policy_id: UUID

  row_version: int
```

ResearchProgram 不拥有 scientific truth；只引用任务、里程碑和输出。

---

# 4. ResearchProgramMilestone

```yaml
ResearchProgramMilestone:
  id: UUID
  research_program_id: UUID

  milestone_type:
    literature_map |
    hypothesis_set |
    experiment_campaign |
    replication |
    manuscript |
    external_review |
    custom

  objective: string

  status:
    PENDING |
    ACTIVE |
    BLOCKED |
    SUCCEEDED |
    FAILED |
    SKIPPED

  success_criteria: StructuredValue
  output_refs: StructuredReferenceSet

  due_at: Instant|null
  created_at: Instant
```

Milestone success criteria 冻结后不能被 Agent 为“完成任务”而改写。

---

# 5. Skill Registry

Skill 是可复用科研能力包。

```yaml
Skill:
  id: UUID
  name: string
  category:
    literature |
    hypothesis |
    experiment |
    coding |
    analysis |
    review |
    replication |
    novelty |
    orchestration |
    other

  current_version_id: UUID
  lifecycle_status:
    ACTIVE | DEPRECATED | RETIRED | BLOCKED

  created_by: ActorId
  created_at: Instant
```

---

# 6. SkillVersion

```yaml
SkillVersion:
  id: UUID
  skill_id: UUID
  version_number: int

  source_type:
    builtin |
    human_authored |
    agent_generated |
    imported

  package_artifact_version_id: UUID
  manifest_artifact_version_id: UUID

  compatible_agent_roles[]
  required_capabilities[]
  required_permissions[]

  trust_level:
    TRUSTED |
    REVIEWED |
    EXPERIMENTAL |
    UNTRUSTED

  evaluation_status:
    UNTESTED |
    EVALUATED |
    ACCEPTED |
    REJECTED |
    REVOKED

  content_hash: SHA256
  created_at: Instant
```

SkillVersion 本身不自动获得执行权限。

---

# 7. Skill Candidate Generation

Agent 可以生成：

```text
SkillCandidate
```

但不能自动上线。

流程：

```text
Agent-generated candidate
→ static validation
→ sandbox test
→ benchmark evaluation
→ security review
→ human/policy approval
→ accepted SkillVersion
```

---

# 8. Skill Evaluation

```yaml
SkillEvaluation:
  id: UUID
  skill_version_id: UUID

  benchmark_suite_id: UUID
  evaluation_run_ids[]

  metrics:
    task_success
    error_rate
    hallucination_rate
    policy_violation_rate
    cost
    latency
    reproducibility

  result:
    ACCEPT |
    REJECT |
    NEEDS_REVIEW

  created_at: Instant
```

Skill acceptance 不依据单次漂亮结果。

---

# 9. Skill Rollback

生产 SkillVersion 必须可回滚：

```text
current SkillVersion
→ revoked
→ previous accepted version
```

历史 AgentExecution 仍引用实际 SkillVersion。

---

# 10. Strategy Portfolio

Phase 3 已有 Strategy Registry。

Phase 4 增加：

```yaml
StrategyPortfolio:
  id: UUID
  project_id: UUID|null
  task_type: string
  candidate_strategy_versions[]
  selection_policy_id: UUID
```

---

# 11. Strategy Evaluation History

```yaml
StrategyEvaluation:
  id: UUID
  strategy_id: string
  strategy_version: string

  task_type: string
  context_signature: StructuredValue

  task_ids[]
  success_metrics: StructuredValue
  cost_metrics: StructuredValue
  failure_modes: StructuredValue

  created_at: Instant
```

---

# 12. Strategy Selection Engine

可以按：

```text
task type
domain
available budget
privacy
data size
historical performance
failure modes
human preference
```

选策略。

```python
class StrategySelector(Protocol):
    def select(
        self,
        task_context: TaskContext,
        portfolio: StrategyPortfolio,
    ) -> StrategySelection:
        ...
```

---

# 13. Strategy Selection ≠ Scientific Decision

自动策略选择只是 workflow optimization。

```text
StrategySelection
≠ ScientificConclusion
≠ Approval
```

即使某策略过去成功率高，也不能自动证明科学结果。

---

# 14. Online Strategy Learning

Phase 4 MAY 使用：

```text
contextual bandit
Bayesian optimization
multi-armed bandit
meta-learning
```

但 reward 必须限制在：

```text
workflow quality
cost
completion
reproducibility
review defect rate
```

不得直接 reward：

```text
positive result
paper acceptance
metric improvement only
```

否则会激励 p-hacking/cherry-picking。

---

# 15. Research Memory

Phase 4 引入跨 Task 的 Research Memory。

必须区分：

```text
Canonical Memory
Derived Memory
Working Memory
Preference Memory
```

---

# 16. MemoryItem

```yaml
MemoryItem:
  id: UUID

  project_id: UUID
  source_type:
    canonical_summary |
    task_summary |
    failure_pattern |
    method_pattern |
    literature_pattern |
    code_pattern |
    review_pattern |
    preference

  source_refs: StructuredReferenceSet

  content_artifact_version_id: UUID
  embedding_ref: string|null

  trust_level:
    CANONICAL_DERIVED |
    VERIFIED_DERIVED |
    UNVERIFIED_DERIVED |
    WORKING

  validity_status:
    ACTIVE |
    STALE |
    INVALID |
    RETIRED

  created_at: Instant
  reviewed_at: Instant|null
```

MemoryItem 不能覆盖 source truth。

---

# 17. Memory Derivation

Memory 必须能追溯：

```text
MemoryItem
→ source_refs
→ canonical objects
```

Memory 更新：

```text
new MemoryItem
```

而不是改写旧事实。

---

# 18. Memory Consolidation

长期运行可以合并重复 memory。

但 consolidation 输出仍是 derived memory。

```text
canonical facts remain unchanged
```

---

# 19. Memory Retrieval

```python
class ResearchMemoryService(Protocol):
    def retrieve(
        self,
        query,
        project_scope,
        trust_filter,
        context,
    ) -> MemoryRetrievalResult:
        ...
```

返回必须含：

```text
memory item
source refs
trust
validity
project scope
```

---

# 20. Multi-Project Memory Policy

默认：

```text
project memory isolation
```

跨项目必须显式：

```text
shared scope
organization policy
cross-project grant
```

禁止无授权全局向量检索。

---

# 21. Shared Method Memory

允许共享：

```text
general debugging pattern
public literature method
generic code skill
benchmarking practice
```

不等于共享：

```text
private hypothesis
unpublished result
restricted data
proprietary manuscript
```

---

# 22. Memory Poisoning 防护

Agent-generated memory 默认 derived/unverified。

如果某 MemoryItem 来源后来 invalid：

```text
ImpactAssessment
→ MemoryItem stale/invalid
```

Agent Context Loader 必须尊重 validity。

---

# 23. Large-Scale Experiment Campaign

Phase 3 有单个 SearchSession。

Phase 4 增加：

```yaml
ExperimentCampaign:
  id: UUID
  research_program_id: UUID

  objective: string
  campaign_type:
    sweep |
    ablation |
    replication |
    robustness |
    scaling |
    search |
    mixed

  status:
    PLANNED |
    ACTIVE |
    PAUSED |
    COMPLETED |
    TERMINATED

  budget_id: UUID
  scheduling_policy_id: UUID
  created_at: Instant
```

---

# 24. ExperimentCampaignBatch

```yaml
ExperimentCampaignBatch:
  id: UUID
  campaign_id: UUID

  batch_type:
    parallel |
    staged |
    adaptive

  candidate_spec_version_ids[]
  priority: int

  status:
    PENDING |
    RUNNING |
    COMPLETED |
    FAILED |
    PARTIAL

  created_at: Instant
```

具体关系实现时使用 relation tables。

---

# 25. Campaign Scheduler

Scheduler 负责：

```text
GPU/CPU allocation
parallel branch limits
dependency ordering
budget
quota
failure backoff
priority
```

Scheduler 不决定 scientific validity。

---

# 26. Large-Scale Search Safety

必须：

```text
all Run retained
all branch lineage retained
multiple testing tracked
search objective frozen
budget hard
failure visible
negative result visible
```

---

# 27. Multiple Testing / Adaptive Search Ledger

Phase 4 必须增加：

```yaml
AdaptiveSearchLedger:
  id: UUID
  campaign_id: UUID

  tested_hypothesis_count: int
  tested_configuration_count: int
  adaptive_decision_count: int

  confirmatory_boundary: StructuredValue
  exploratory_boundary: StructuredValue

  created_at: Instant
```

避免长期搜索后把最好一次结果伪装成单次 confirmatory test。

---

# 28. ReplicationTask

```yaml
ReplicationTask:
  id: UUID
  project_id: UUID

  target_type:
    claim |
    experiment |
    paper |
    result

  target_ref: StructuredReference

  replication_type:
    exact |
    computational |
    conceptual |
    cross_dataset |
    cross_environment

  protocol_version_id: UUID
  status:
    PLANNED |
    RUNNING |
    SUCCEEDED |
    FAILED |
    INCONCLUSIVE

  created_at: Instant
```

---

# 29. ReplicationProtocol

必须冻结：

```text
target
inputs
code
environment
metrics
acceptance criteria
allowed deviations
```

---

# 30. ReplicationAssessment

```yaml
ReplicationAssessment:
  id: UUID
  replication_task_id: UUID

  result:
    replicated |
    partially_replicated |
    not_replicated |
    inconclusive

  effect_comparison: StructuredValue
  deviation_summary: text
  limitation_summary: text

  evidence_refs[]
  created_at: Instant
```

Replication failure 不自动说明原工作 fraudulent/invalid。

---

# 31. Automated Replication Agent

可以：

```text
resolve artifacts
rebuild environment
execute runs
compare metrics
detect deviations
```

但正式 Assessment 仍需 policy/human gate。

---

# 32. Advanced Novelty Evaluation

Phase 2 basic novelty。

Phase 4 可加入：

```text
semantic prior-art search
claim decomposition
citation graph traversal
cross-domain analog search
negative novelty probes
adversarial prior-art agent
```

---

# 33. Novelty Search Campaign

```yaml
NoveltySearchCampaign:
  id: UUID
  claim_version_id: UUID

  search_plan_version_ids[]
  source_version_ids[]
  strategy_versions[]

  coverage_summary
  contradiction_summary

  status:
    ACTIVE |
    COMPLETED |
    INCONCLUSIVE

  created_at: Instant
```

---

# 34. Advanced Novelty Rule

永远禁止：

```text
No result found → first ever
```

必须表达 SearchCoverage 与不确定性。

---

# 35. Reviewer Ensemble

Phase 4 可以运行多个独立 ReviewerAgent：

```text
Scientific Reviewer
Statistical Reviewer
Literature Reviewer
Reproducibility Reviewer
Adversarial Reviewer
Domain Reviewer
```

---

# 36. ReviewEnsemble

```yaml
ReviewEnsemble:
  id: UUID
  target_ref: FrozenReference
  reviewer_execution_ids[]
  aggregation_policy_id: UUID
  created_at: Instant
```

---

# 37. Review Consensus

Consensus 不能简单 majority vote。

需要区分：

```text
shared blocking issue
independent concern
contradictory assessment
uncertain
```

聚合结果只是 Review summary，不是 scientific fact。

---

# 38. Adversarial Scientific Review

高级 Reviewer 要主动攻击：

```text
data leakage
baseline weakness
hidden selection
multiple testing
citation misuse
novelty overclaim
failure to replicate
unsupported extrapolation
confounded comparison
```

---

# 39. Meta-Evaluation

Phase 4 需要评估 Agent 系统本身。

```yaml
AgentSystemEvaluation:
  id: UUID
  runtime_version
  strategy_set_hash
  skill_set_hash

  benchmark_suite_id
  metrics
  failure_modes
  safety_incidents

  created_at
```

---

# 40. Benchmark Suite

必须覆盖：

```text
literature accuracy
citation grounding
experiment reproducibility
negative-result handling
debug correctness
statistical integrity
review defect detection
budget adherence
memory isolation
prompt injection robustness
```

---

# 41. Long-Horizon Planner

ResearchProgram 可持续多天/多周。

Planner 每轮只生成有限 horizon：

```text
next N milestones / tasks
```

禁止一次生成巨大不可变计划。

---

# 42. Replanning

允许：

```text
new evidence
failed replication
budget change
human decision
review feedback
```

触发新 plan。

旧 plan/history 保留。

---

# 43. Long-Horizon Checkpoint

```yaml
ProgramCheckpoint:
  id: UUID
  research_program_id: UUID

  milestone_state_hash
  task_state_refs
  budget_snapshot
  memory_snapshot_ref
  strategy_snapshot
  open_risks
  pending_human_actions

  created_at: Instant
```

---

# 44. Kill Switch

必须支持：

```text
global emergency stop
project stop
program stop
task stop
capability stop
adapter disable
skill revoke
```

Emergency stop 优先于 Agent plan。

---

# 45. Autonomy Escalation Policy

Agent 不能自行从 A2 → A3。

```yaml
AutonomyEscalationRequest:
  id
  task/program
  current_level
  requested_level
  reason
  evidence
  budget
  risk_summary
  requested_by
  status
```

由 Human/Policy 决定。

---

# 46. Autonomy De-escalation

任何：

```text
security incident
unexpected external effect
budget anomaly
high hallucination rate
repeated closure violation
review failure
```

都可自动降低自治等级。

---

# 47. Long-Horizon Governance

每个 ResearchProgram 至少有：

```text
autonomy ceiling
budget
allowed capabilities
data scope
external effect policy
human review cadence
termination criteria
```

---

# 48. Research Program Review Cadence

例如：

```text
every milestone
every N runs
every budget threshold
every material scientific pivot
```

触发 HumanCheckpoint。

---

# 49. External Collaboration Boundary

Phase 4 MAY 接：

```text
remote lab
external compute
partner repository
shared benchmark
```

但必须通过 ExternalReference + policy。

不直接跨系统共享 DB primary keys 作为唯一 identity。

---

# 50. Cross-Lab Provenance

需要：

```text
external actor identity
external artifact hash
external run/protocol reference
import timestamp
verification status
```

---

# 51. Model/Provider Portfolio

Phase 4 可以自动路由：

```text
cheap model
reasoning model
coding model
review model
local/private model
```

目标：

```text
quality / cost / privacy / latency
```

但 model score 不进入 scientific truth。

---

# 52. Cost-Aware Routing

Routing 可学习：

```text
task type → best cost-quality model
```

不得因成本自动降低 required review/governance gate。

---

# 53. Skill Self-Evolution Boundary

允许：

```text
Agent proposes improved skill
```

禁止：

```text
Agent edits production skill
→ immediately executes with new privileges
```

必须走 SkillEvaluation。

---

# 54. Strategy Self-Evolution Boundary

类似：

```text
strategy candidate
→ offline benchmark
→ comparison
→ accepted strategy version
```

生产 runtime 不能在线静默换核心策略而不记录 version。

---

# 55. Memory Self-Evolution Boundary

Memory 可以生成总结、模式和经验。

但：

```text
Memory summary
≠ Evidence
≠ Measurement
≠ Claim
```

---

# 56. Research Quality Objectives

Phase 4 的优化目标应该多目标：

```text
scientific validity
reproducibility
coverage
cost efficiency
novelty
robustness
human effort
safety
```

禁止只优化：

```text
positive metric
paper count
acceptance likelihood
```

---

# 57. Reward Hacking Defense

如果 Agent 发现“改 success criteria 更容易成功”，必须阻止。

Success criteria 属于 frozen protocol/plan 时：

```text
change → new Version + explicit reason
```

---

# 58. Scientific Goal Drift

长期 Agent 可能逐渐偏离原 ResearchQuestion。

需要 `GoalAlignmentCheck`：

```yaml
GoalAlignmentAssessment:
  program_id
  current_task
  original_objective
  alignment_score
  divergence_summary
  action:
    continue | replan | human_review | stop
```

---

# 59. Research Diversity

Tree search/strategy selection 不应 collapse 到单一方向。

可维护：

```text
method diversity
hypothesis diversity
data diversity
model diversity
```

作为 search heuristic。

---

# 60. Replication Before Promotion

对于高风险/高影响 Claim，Policy MAY 要求：

```text
independent replication
```

后才能进入正式 release gate。

---

# 61. Cross-Model Review

Formal critical review MAY 使用不同 model/provider 以降低 correlated failure。

不是强制，但建议。

---

# 62. Memory Retrieval Safety

任何 memory retrieval 输出必须同时返回：

```text
trust
validity
source refs
project scope
```

Agent 不得只拿 embedding-nearest text 无视 validity。

---

# 63. Stale Memory Propagation

上游 canonical source stale：

```text
ImpactAssessment
→ derived MemoryItems stale
```

Context Loader 默认过滤 INVALID。

---

# 64. Advanced Search / Campaign Scheduling

可以并行大量实验，但 scheduler 必须限制：

```text
GPU quota
branch quota
job count
cost
priority
```

---

# 65. Fairness Across Branches

如果只给“当前最好 branch”无限资源，会导致 premature convergence。

Scheduler SHOULD 保留 exploration budget。

---

# 66. Experiment Campaign Audit

必须回答：

```text
为什么跑这些实验
为什么没跑另一些
谁/什么策略选择了 branch
总共测试多少
停止条件是什么
```

---

# 67. Large-Scale Statistical Integrity

Campaign 中必须记录：

```text
adaptive choices
number of comparisons
exploratory vs confirmatory boundary
selection mechanism
```

---

# 68. Research Program Dashboard

Human UI SHOULD 展示：

```text
milestones
active tasks
budget
search tree
replication status
open review issues
memory health
strategy performance
risk alerts
```

UI 是 derived read model。

---

# 69. Advanced Incident Handling

Phase 4 事件：

```text
skill security issue
memory leak
provider compromised
campaign runaway
scientific integrity alert
cross-project data leak
```

进入 Incident + ImpactAssessment。

---

# 70. Emergency Containment

Incident 可以：

```text
disable adapter
revoke skill
pause program
block strategy
invalidate memory
stop campaign
```

但不删除历史。

---

# 71. Phase 4 Package Layout

```text
src/researchbase/
├── programs/
├── skills/
├── strategy_selection/
├── research_memory/
├── campaigns/
├── replication/
├── advanced_review/
├── evaluation/
└── governance/
```

仍可保持 modular monolith；如计算 worker 独立部署，也不等于 Domain microservices。

---

# 72. Database Increment

建议新增：

```text
research_programs
research_program_milestones
program_checkpoints

skills
skill_versions
skill_evaluations

strategy_portfolios
strategy_evaluations

memory_items
memory_item_sources
memory_policies

experiment_campaigns
experiment_campaign_batches
adaptive_search_ledgers

replication_tasks
replication_assessments

novelty_search_campaigns
review_ensembles
agent_system_evaluations

autonomy_escalation_requests
goal_alignment_assessments
```

约 20–30 张增量表。

---

# 73. Stable API

```text
POST /research-programs
POST /research-programs/{id}:start
POST /research-programs/{id}:pause
GET  /research-programs/{id}

POST /skills/candidates
POST /skills/{id}/versions/{version}:evaluate
POST /skills/{id}/versions/{version}:promote
POST /skills/{id}/versions/{version}:revoke

POST /strategy-selection:select
GET  /strategies/{id}/evaluations

POST /memory:query
POST /memory:consolidate
POST /memory/{id}:review

POST /experiment-campaigns
POST /experiment-campaigns/{id}:schedule
GET  /experiment-campaigns/{id}/audit

POST /replications
GET  /replications/{id}

POST /review-ensembles
GET  /review-ensembles/{id}

POST /autonomy-escalations
POST /autonomy-escalations/{id}:decide
```

---

# 74. Error Model

```text
SKILL_NOT_EVALUATED
SKILL_REVOKED
STRATEGY_NOT_ALLOWED
STRATEGY_EVALUATION_INSUFFICIENT
MEMORY_SCOPE_VIOLATION
MEMORY_ITEM_STALE
PROGRAM_BUDGET_EXCEEDED
PROGRAM_GOAL_DIVERGENCE
CAMPAIGN_QUOTA_EXCEEDED
REPLICATION_PROTOCOL_INVALID
AUTONOMY_ESCALATION_REQUIRED
AUTONOMY_LEVEL_NOT_ALLOWED
EMERGENCY_STOP_ACTIVE
```

---

# 75. Test Matrix

## Skills

- untrusted skill cannot execute privileged capability；
- agent-generated skill requires evaluation；
- revoke stops future use；
- historical execution retains old skill version。

## Strategy Selection

- context-aware selection；
- budget/privacy constraints；
- strategy history；
- no reward for positive-result bias；
- selection reproducible from logged context。

## Memory

- source trace；
- stale propagation；
- project isolation；
- shared memory policy；
- invalid memory filtered；
- consolidation does not alter canonical source。

## Campaign

- quota；
- branch fairness；
- adaptive ledger；
- negative result retention；
- multiple testing metadata；
- pause/resume。

## Replication

- protocol frozen；
- exact artifacts resolved；
- deviations tracked；
- assessment conservative。

## Review Ensemble

- independent executions；
- conflicting reviews retained；
- aggregation doesn't erase minority blocking concern。

## Governance

- Agent cannot self-escalate autonomy；
- kill switch stops execution；
- de-escalation on incident；
- milestone checkpoints。

---

# 76. Golden E2E

## 76.1 Skill Evolution

```text
Agent proposes skill
→ sandbox benchmark
→ evaluation
→ human/policy accept
→ SkillVersion
→ later defect
→ revoke
→ rollback
```

## 76.2 Strategy Selection

```text
Task context
→ portfolio
→ selector chooses Strategy A
→ task runs
→ evaluation recorded
→ next similar task selection updates
```

## 76.3 Memory Reuse

```text
Task A failure
→ derived failure-pattern memory
→ Task B retrieves it
→ avoids same issue
```

但 Task B scientific result still relies on its own canonical evidence.

## 76.4 Large Campaign

```text
100 candidate configs
→ staged pilot
→ prune
→ confirmatory subset
→ replication
→ final assessment
```

adaptive history complete.

## 76.5 Replication

```text
Claim
→ replication protocol
→ independent Run
→ comparison
→ ReplicationAssessment
→ impact if needed
```

---

# 77. Failure Injection

## F1 Malicious Skill

Skill tries network/secrets escalation → blocked/rejected。

## F2 Memory Poisoning

Invalid source-derived memory retrieved → validity filter blocks/warns。

## F3 Reward Hacking

Strategy improves “success rate” by weakening success criteria → invariant violation。

## F4 Campaign Cherry-Picking

Agent attempts to hide failed batches → audit detects missing lineage/history。

## F5 Autonomy Escalation

Agent requests A3 and self-approves → impossible by authority rules。

## F6 Program Drift

Tasks diverge from original objective → GoalAlignmentAssessment triggers human review。

## F7 Reviewer Collusion/Correlation

Multiple identical Reviewer executions produce same blind spot → ensemble policy can require model/prompt diversity。

---

# 78. Architecture Tests

```text
test_skill_version_cannot_self_promote
test_agent_generated_skill_requires_evaluation
test_revoked_skill_not_selectable
test_strategy_reward_not_positive_result_only
test_memory_has_source_refs
test_memory_does_not_override_canonical_state
test_cross_project_memory_policy
test_campaign_keeps_all_runs
test_adaptive_search_ledger_complete
test_replication_assessment_not_claim_override
test_review_ensemble_preserves_disagreement
test_agent_cannot_escalate_autonomy
test_kill_switch_preempts_runtime
test_goal_drift_requires_replan_or_review
```

---

# 79. Work Packages

| WP | 范围 | Owner |
|---|---|---|
| WP4-A Programs/Governance | ResearchProgram/Milestones/Autonomy | Tech Lead |
| WP4-B Skills/Strategies | Skill Registry/Strategy Selection | Dev A |
| WP4-C Memory | Research Memory/Consolidation | Dev B |
| WP4-D Campaigns | Large-scale experiment scheduling | Dev C |
| WP4-E Replication/Novelty | Replication/Novelty Campaign | Dev D |
| WP4-F Advanced Review/Evaluation | Reviewer Ensemble/Meta-Eval | Dev E |

---

# 80. PR Sequence

```text
PR4-00  Phase 4 Bootstrap
PR4-01  ResearchProgram / Milestone
PR4-02  Program Checkpoint / Long-Horizon Planner
PR4-03  Skill / SkillVersion
PR4-04  Skill Evaluation / Rollback
PR4-05  Strategy Portfolio / Evaluation
PR4-06  Strategy Selection Engine
PR4-07  Research Memory Core
PR4-08  Memory Retrieval / Validity
PR4-09  Memory Consolidation / Cross-Project Policy
PR4-10  ExperimentCampaign
PR4-11  Campaign Scheduler
PR4-12  Adaptive Search Ledger
PR4-13  ReplicationTask / Protocol
PR4-14  ReplicationAssessment / Agent
PR4-15  Advanced Novelty Campaign
PR4-16  Reviewer Ensemble
PR4-17  Meta-Evaluation
PR4-18  Autonomy Escalation / Kill Switch
PR4-19  Goal Alignment / Program Review
PR4-20  Security / Memory Poisoning Failure Injection
PR4-21  Large Campaign E2E
PR4-22  Long-Horizon Program E2E
PR4-23  Hardening / Exit Report
```

---

# 81. Code Review Checklist

## Skill

- Agent 是否自行上线 Skill？
- SkillVersion 是否 pin？
- 权限是否来自 Skill 本身？
- rollback 是否可行？

## Strategy

- selection reward 是否鼓励正结果偏置？
- 选择依据是否记录？
- model/provider 是否成为 Core schema？

## Memory

- 是否能追 canonical source？
- stale/invalid 是否过滤？
- private project 是否泄漏？
- summary 是否被当 Evidence？

## Campaign

- 所有 Run 是否保留？
- adaptive testing 是否记录？
- success criteria 是否被改？
- negative result 是否隐藏？

## Governance

- autonomy 是否越权？
- kill switch 是否真正优先？
- Program 是否可暂停/恢复？
- Goal drift 是否监控？

---

# 82. Phase 4 Definition of Done

1. Phase 1–3 regression 全部 PASS；
2. Skill candidate→evaluation→promotion→rollback；
3. Strategy selection 有历史与可解释依据；
4. Memory 全部可 source trace；
5. Memory validity propagation；
6. cross-project isolation；
7. Campaign lineage 完整；
8. adaptive search ledger；
9. replication workflow；
10. reviewer ensemble；
11. autonomy escalation policy；
12. kill switch；
13. goal drift detection；
14. failure injection；
15. no canonical schema regression。

---

# 83. Phase 4 Exit Criteria

```text
[ ] ResearchProgram long-horizon state PASS
[ ] Milestone/checkpoint PASS
[ ] Skill Registry / SkillVersion PASS
[ ] Agent-generated skill evaluation PASS
[ ] Skill revoke/rollback PASS
[ ] Strategy Portfolio / Selection PASS
[ ] Strategy reward-hacking guard PASS
[ ] Research Memory source trace PASS
[ ] Memory stale propagation PASS
[ ] Cross-project memory isolation PASS
[ ] Large Experiment Campaign PASS
[ ] Adaptive Search Ledger PASS
[ ] Replication workflow PASS
[ ] Advanced Novelty Campaign PASS
[ ] Reviewer Ensemble PASS
[ ] Meta-Evaluation PASS
[ ] Autonomy Escalation requires external decision PASS
[ ] Kill Switch PASS
[ ] Goal Alignment / Drift PASS
[ ] Phase 1–3 Exit tests continue PASS
```

Exit artifacts：

```text
phase4_exit_report.md
skill_registry_inventory.md
strategy_evaluation_report.md
research_memory_integrity_report.md
campaign_audit_demo.md
replication_demo.md
advanced_review_report.md
long_horizon_governance_report.md
```

然后进入系统级 Compatibility/Release Review，而不是继续增加 Phase 5。

---

# 84. Phase 4 Final Invariants

```text
P4-INV-001 Advanced autonomy MUST NOT weaken canonical scientific state ownership.
P4-INV-002 Agent-generated skills MUST NOT self-promote to trusted production use.
P4-INV-003 Skill/Strategy optimization MUST NOT reward positive scientific outcomes as the sole success metric.
P4-INV-004 Research Memory MUST remain derived and source-traceable.
P4-INV-005 Cross-project memory MUST be denied by default.
P4-INV-006 Memory consolidation MUST NOT rewrite canonical scientific facts.
P4-INV-007 Large-scale campaigns MUST retain all executed Runs and adaptive decisions.
P4-INV-008 Adaptive search MUST record exploratory/confirmatory boundaries.
P4-INV-009 Replication results MUST remain distinct from the validity status of the original work until assessed.
P4-INV-010 Reviewer ensembles MUST preserve meaningful disagreement.
P4-INV-011 Agents MUST NOT self-escalate autonomy or governance authority.
P4-INV-012 Emergency stop MUST preempt normal runtime execution.
P4-INV-013 Long-horizon programs MUST have explicit budgets, milestones, checkpoints and termination rules.
P4-INV-014 Scientific goal drift MUST be detectable and governed.
P4-INV-015 Model/provider/skill/runtime implementations MUST remain replaceable at Core boundaries.
P4-INV-016 Phase 1–3 provenance, versioning and governance invariants remain authoritative.
```

---

# 85. Phase 4 最终施工结论

Phase 4 真正交付的是：

```text
可治理的科研能力积累
+
可评估的 Skill/Strategy 自我改进
+
可信的跨任务科研记忆
+
大规模但可审计的实验搜索
+
复制与高级审稿
+
长期科研计划与停止机制
```

最终验收标准：

> **系统可以在长期、多任务、多实验环境下提升自己的科研执行效率与策略质量，但任何“学习到的经验、技能、策略、记忆”都不能凌驾于 canonical scientific facts；任何大规模自治搜索都必须保留完整实验历史和自适应选择轨迹；任何自治等级提升都必须由明确政策或 Human 决定，并且系统始终可以暂停、回滚、撤销技能和停止任务。**

---

# Harness Integration Addendum — Phase 4

## H4.1 Advanced Harness Scope

Phase 4 may extend the stable Phase-3 Harness Runtime with dynamic strategy selection, Skill composition, reusable research-method packages, replication agents, long-horizon orchestration and controlled Skill-evolution candidates. It MUST NOT redefine Phase-1/2 canonical semantics or Phase-3 AgentExecution/Candidate Promotion boundaries.

## H4.2 Skill Evolution Is Governed Release, Not Runtime Mutation

Self-improvement follows:

```text
observed failure/opportunity
→ Candidate Skill/strategy change
→ structural + behavior eval
→ benchmark/regression comparison
→ security/capability review
→ governed approval
→ immutable versioned release
→ harness.lock update
```

A live AgentExecution MUST NOT silently replace the production Skill that governs itself.

## H4.3 Dynamic Selection

Dynamic strategy/Skill selection may optimize quality, cost, latency or domain fit, but routing remains constrained by:

```text
phase
authority
capability
data zone
scientific risk
budget
required independent review
```

Optimization score never overrides hard scientific or governance constraints.

## H4.4 Cross-Project Reuse

Reusable Skills/strategies may be shared across projects only through explicitly versioned packages. Project scientific memory and confidential context remain deny-by-default; sharing a Skill implementation does not imply sharing project data or canonical memory.

## H4.5 Advanced Scientific Skill Set

The bounded v1 ResearchBase set remains the default. Phase 4 SHOULD prefer adding references/strategies/evaluations to existing Skills before creating a new top-level Skill identity.

## H4.6 Phase-4 Exit Extension

```text
[ ] evolved Skill cannot bypass evaluation/release gate PASS
[ ] dynamic routing cannot override hard capability/authority constraints PASS
[ ] cross-project Skill reuse does not leak project memory PASS
[ ] harness regression history remains reconstructable PASS
[ ] failed/negative autonomous branches remain retained PASS
[ ] HarnessFingerprint identifies released Skill/strategy versions PASS
```

