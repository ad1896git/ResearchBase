# ResearchBase Phase 3 Development Specification

> **版本**：v1.0  
> **状态**：DESIGN COMPLETE / READY FOR CROSS-PHASE REVIEW  
> **日期**：2026-08-26  
> **上位设计**：`ResearchBase_全系统设计文档_架构补全版_v1.2`  
> **前置规范**：`ResearchBase_Phase1_Development_Specification_v1.1`、`ResearchBase_Phase2_Development_Specification_v1.0`  
> **适用对象**：Tech Lead、Scientific Agent Runtime 开发人员、Coding/Execution Adapter 开发人员、Agent Evaluation 开发人员、Codex/Coding Agent  
> **规范性**：本文件定义 Phase 3 Scientific Agent Runtime、CapabilityGateway、Strategy Plugin、Agent Execution、自治实验循环、Coding/Execution Adapter、Memory、Budget、Recovery、Human Gate、Tree Search 和验证标准。任何 Phase 3 Agent 行为必须通过 Phase 1/2 Application Commands/Queries 读写 canonical scientific state。

---

# 0. Phase 3 目标

Phase 1 建立可信科研 Core：

```text
Hypothesis
→ ExperimentSpec
→ Run
→ Measurement / StatisticalResult
→ Claim
```

Phase 2 建立 Literature + Collaboration + Publication：

```text
LiteratureSource / SourceVersion
→ LiteratureEvidence
→ ScientificConclusion
→ ManuscriptVersion
→ Internal Review / Decision / Approval
```

Phase 3 的任务是把以上 Core 变成真正可以被多个 Scientific Agents 协同消费的 Research OS：

```text
Human Research Intent
        ↓
ResearchTask
        ↓
Scientific Orchestrator
        ↓
Strategy
        ↓
CapabilityGateway
        ↓
Specialized Agents / Tools
        ↓
Candidate Outputs
        ↓
Application Command / Query
        ↓
ResearchBase Canonical State
```

Phase 3 的核心目标：

> **构建受约束、可暂停、可恢复、可审计、可替换模型/Agent framework 的 Scientific Agent Runtime，使 Agent 能够执行“调研→假设→实验设计→代码→运行→分析→批判→写作→评审”的完整科研循环，但不得建立第二套 scientific state，也不得绕过 Human/Governance/Frozen Provenance Closure。**

---

# 1. Phase 3 MUST / SHOULD / MAY / MUST NOT

## 1.1 MUST 实现

```text
ResearchTask
ResearchTaskStep / TaskGraph
AgentVersion
AgentExecutionInstance
CapabilityInvocation
Scientific Orchestrator
CapabilityGateway
Strategy Registry / StrategyVersion
Tool/Capability Policy
Human Checkpoint
Execution Budget
Termination Policy
Retry / Recovery Policy
Agent Working Memory
Canonical Context Loader
Agent Result Promotion
CodingCapability
SandboxExecutionCapability
ComputeCapability
AnalysisCapability
Review/Critic Capability

EvoScientist-like native orchestration
Coding Agent Adapter（至少一种：Codex/OpenHands/ACP-compatible）
Execution Agent
Analysis Agent
Critic Agent
Reviewer Agent
bounded autonomous experiment loop
Experiment Search Manager
AI Scientist-v2-inspired progressive tree-search strategy
branch lineage / pruning / budget
full Agent provenance
```

## 1.2 SHOULD 实现

```text
OpenHands adapter
multiple CodingCapability providers
provider/model routing
resume from checkpoint
task pause / cancel
agent handoff
skill registry
MCP/tool adapter
sandbox snapshot
experiment branch visualization
agent evaluation harness
```

## 1.3 MAY 实现

```text
EvoScientist service adapter prototype
DeerFlow harness adapter prototype
LangGraph runtime implementation
OpenHands SDK native embedding
ACP-compatible coding agents
multi-agent debate strategy
specialized statistician agent
automated benchmark suite
```

## 1.4 MUST NOT 实现

```text
unbounded autonomous research
agent self-granting authority
agent direct DB access
agent direct ORM access
agent modifying frozen records
agent hiding failed experiments
agent deleting pruned search branches
automatic external venue submission without governance
full self-modifying production Agent runtime
unreviewed self-install of arbitrary skills/packages
cross-project memory leakage
provider-specific scientific schema
```

---

# 2. 顶层 Runtime 架构

```text
┌──────────────────────────────────────────────────────────────┐
│ Human / Research Cockpit                                     │
├──────────────────────────────────────────────────────────────┤
│ ResearchTask API / Orchestrator                              │
│   ├── Planner                                                │
│   ├── Strategy Runtime                                       │
│   ├── Human Checkpoint Manager                               │
│   ├── Budget / Termination Manager                           │
│   └── Recovery Manager                                       │
├──────────────────────────────────────────────────────────────┤
│ Specialized Agent Roles                                      │
│   Research · Hypothesis · Experiment · Code · Debug          │
│   Execution · Analysis · Critic · Writing · Reviewer         │
├──────────────────────────────────────────────────────────────┤
│ CapabilityGateway                                            │
│   Search · ScientificRAG · Coding · Sandbox · Compute        │
│   Statistics · Artifact · Writing · Review                   │
├──────────────────────────────────────────────────────────────┤
│ Phase 1/2 Application Commands / Queries                     │
├──────────────────────────────────────────────────────────────┤
│ ResearchBase Canonical Core                                  │
└──────────────────────────────────────────────────────────────┘
```

Runtime 可以用 LangGraph、DeepAgents、自研状态机或其他框架实现，但：

```text
Runtime Framework ≠ ResearchBase Domain
Runtime State     ≠ Canonical Scientific State
```

---

# 3. Reference Architecture Mapping

Phase 3 吸收三类参考系统的不同优点：

```text
EvoScientist-like
→ specialized scientific agent roles
→ plan/research/code/debug/analyze/write workflow
→ skills + persistent working memory
→ provider independence

AI Scientist-v2-like
→ Experiment Manager
→ progressive agentic tree search
→ branch exploration / refinement
→ open-ended experiment search

OpenHands-like
→ agent / tool / workspace / sandbox separation
→ secure arbitrary code execution
→ API-based agent execution
→ composable tools/prompts/contexts
```

原则：

> **借 runtime 设计，不继承其 canonical scientific state。**

---

# 4. ResearchTask

ResearchTask 是 Phase 3 的主要 workflow Aggregate。

```yaml
ResearchTask:
  id: UUID
  project_id: UUID

  task_type:
    literature_research |
    hypothesis_generation |
    experiment_design |
    experiment_execution |
    analysis |
    claim_revision |
    manuscript_drafting |
    internal_review |
    end_to_end_research |
    replication |
    other

  objective: string

  input_refs:
    research_question_version_ids[]
    hypothesis_version_ids[]
    claim_version_ids[]
    literature_source_version_ids[]
    artifact_version_ids[]
    manuscript_version_ids[]

  strategy_id: string
  strategy_version: string

  autonomy_level:
    A0 | A1 | A2 | A3

  status:
    CREATED |
    PLANNING |
    RUNNING |
    WAITING_HUMAN |
    PAUSED |
    SUCCEEDED |
    FAILED |
    CANCELLED |
    TERMINATED_BUDGET |
    TERMINATED_POLICY

  requested_by: ActorId
  created_at: Instant
  started_at: Instant|null
  finished_at: Instant|null

  budget_policy_id: UUID
  termination_policy_id: UUID
  checkpoint_policy_id: UUID

  current_step_id: UUID|null
  row_version: int
```

ResearchTask 不拥有 scientific objects；它只引用和编排。

---

# 5. ResearchTaskStep

```yaml
ResearchTaskStep:
  id: UUID
  research_task_id: UUID

  step_type:
    plan |
    research |
    retrieve |
    hypothesize |
    design_experiment |
    code |
    debug |
    execute |
    analyze |
    critique |
    write |
    review |
    human_checkpoint |
    promote |
    other

  status:
    PENDING |
    READY |
    RUNNING |
    WAITING |
    SUCCEEDED |
    FAILED |
    SKIPPED |
    CANCELLED

  ordinal: int
  parent_step_id: UUID|null

  agent_role: string|null
  capability_id: string|null

  input_refs: StructuredReferenceSet
  output_refs: StructuredReferenceSet

  started_at: Instant|null
  finished_at: Instant|null

  retry_count: int
  failure_code: string|null
```

复杂工作流可进一步关系化为 DAG：

```text
research_task_step_dependencies
```

禁止把所有 task graph 只存在 Agent framework checkpoint blob 里。

---

# 6. Agent Identity / Version / Execution

## 6.1 AgentVersion

Phase 1 已预留 AgentActor / AgentVersion 语义；Phase 3 正式实现：

```yaml
AgentVersion:
  id: UUID
  actor_id: UUID

  agent_role:
    planner |
    research |
    hypothesis |
    experiment_designer |
    coder |
    debugger |
    executor |
    analyst |
    critic |
    writer |
    reviewer |
    orchestrator |
    general

  runtime_type:
    native |
    langgraph |
    deepagents |
    openhands |
    external_service |
    other

  prompt_template_version: string
  model_profile_id: string
  tool_policy_version: string
  capability_set_hash: SHA256
  configuration_artifact_version_id: UUID

  content_hash: SHA256
  created_at: Instant
  status:
    ACTIVE | RETIRED | DISABLED
```

## 6.2 AgentExecutionInstance

每次 Agent 运行都必须留下 provenance：

```yaml
AgentExecutionInstance:
  id: UUID
  research_task_id: UUID
  research_task_step_id: UUID|null

  agent_version_id: UUID
  actor_id: UUID

  status:
    CREATED |
    RUNNING |
    WAITING_TOOL |
    WAITING_HUMAN |
    SUCCEEDED |
    FAILED |
    CANCELLED

  started_at: Instant
  finished_at: Instant|null

  execution_context:
    request_id
    correlation_id
    causation_id

  model_execution_summary: StructuredValue
  input_ref_hash: SHA256
  output_ref_hash: SHA256|null

  working_memory_snapshot_artifact_id: UUID|null
  trace_artifact_version_id: UUID|null

  error_code: string|null
```

Human 后续批准 Agent 输出也不得删除 execution provenance。

---

# 7. CapabilityInvocation

工具调用必须独立于 Agent execution 记录：

```yaml
CapabilityInvocation:
  id: UUID
  agent_execution_id: UUID
  research_task_id: UUID

  capability_id: string
  capability_version: string
  adapter_id: string|null
  adapter_version: string|null

  input_refs: StructuredReferenceSet
  requested_parameters_hash: SHA256

  status:
    REQUESTED |
    RUNNING |
    SUCCEEDED |
    FAILED |
    UNKNOWN_OUTCOME |
    CANCELLED

  started_at: Instant
  finished_at: Instant|null

  output_refs: StructuredReferenceSet
  result_summary: StructuredValue|null

  resource_usage: StructuredValue|null
  error_code: string|null
```

Capability invocation 的原始大日志以 ArtifactVersion 存储，不塞主表。

---

# 8. CapabilityGateway

统一接口：

```python
class CapabilityGateway(Protocol):
    def invoke(
        self,
        request: CapabilityRequest,
        context: AgentExecutionContext,
    ) -> CapabilityResult:
        ...
```

Gateway 负责：

```text
adapter lookup
policy evaluation
sandbox selection
credentials
timeout
resource limits
retry policy
provenance logging
result normalization
```

Agent 不直接实例化 vendor SDK。

---

# 9. Capability Types

Phase 3 至少：

```text
SearchCapability                  [Phase 2]
ScientificRAGCapability           [Phase 2]
CodingCapability
SandboxExecutionCapability
ComputeCapability
StatisticsCapability
ArtifactCapability
RepositoryWorkspaceCapability
WritingCapability
ReviewCapability
ModelCapability
EmbeddingCapability
```

Capability 是工具能力；Agent 是角色；Strategy 是流程。

---

# 10. CodingCapability

```python
class CodingCapability(Protocol):
    def execute_task(
        self,
        request: CodingTaskRequest,
        context: AgentExecutionContext,
    ) -> CodingTaskResult:
        ...
```

Input：

```yaml
CodingTaskRequest:
  repository_artifact_ref
  workspace_ref
  objective
  experiment_spec_version_id
  allowed_paths
  allowed_commands
  test_commands
  dependency_policy
  network_policy
  time_budget
```

Output：

```yaml
CodingTaskResult:
  patch_artifact_version_id
  source_artifact_version_id
  configuration_artifact_version_ids[]
  dependency_lock_artifact_version_id|null
  test_result_artifact_version_id
  command_log_artifact_version_id
  summary
  warnings[]
```

Formal Run 前必须形成 ArtifactVersion。

---

# 11. OpenHands / Codex Adapter Contract

推荐：

```text
CodingCapability
├── CodexAdapter
├── OpenHandsAdapter
├── ACPAdapter
└── FakeCodingAdapter
```

每个 adapter 必须：

```text
pin adapter version
record model/provider
record sandbox/runtime
record workspace commit/hash
record commands
record produced ArtifactVersions
```

Agent completion text 不是成功判据。

成功至少要求：

```text
code artifact exists
tests executed or explicitly skipped with reason
patch/hash recorded
workspace status known
```

---

# 12. Sandbox Architecture

所有 LLM-written code 默认 sandbox。

```yaml
SandboxProfile:
  id: string
  runtime:
    docker | apptainer | remote_hpc | managed_api | local_restricted

  cpu_limit
  memory_limit
  gpu_limit
  disk_limit
  time_limit

  network_policy:
    none |
    allowlist |
    unrestricted_with_approval

  filesystem_policy:
    read_only_inputs
    writable_workspace
    blocked_host_paths

  process_limit
  package_install_policy
  secrets_policy
```

默认：

```text
host filesystem access = DENY
arbitrary host process = DENY
unlimited network = DENY
secret enumeration = DENY
```

---

# 13. ComputeCapability

```python
class ComputeCapability(Protocol):
    def submit(self, request: ComputeRequest, context) -> ComputeHandle: ...
    def poll(self, handle: ComputeHandle, context) -> ComputeStatus: ...
    def cancel(self, handle: ComputeHandle, context) -> None: ...
```

可适配：

```text
local
Docker
Slurm
Kubernetes
cloud batch
HPC scheduler
```

Compute job 不等于 ResearchBase Run。

标准：

```text
ResearchBase Run
→ ComputeInvocation
→ external job
→ outcome
→ Run lifecycle update
```

---

# 14. ExecutionAgent

职责：

```text
validate FROZEN ExperimentSpecVersion
resolve DatasetSnapshot
resolve ArtifactVersion
create Run
seal Run inputs
invoke Compute/Sandbox
collect outputs
finish Run
record Measurement candidates
```

ExecutionAgent 不修改 ExperimentSpec。

如果运行结果发现 spec 有问题：

```text
Run FAILED / SUCCEEDED
→ Analysis/Critic
→ Decision
→ new ExperimentSpecVersion
```

---

# 15. AnalysisAgent

Input：

```text
Run
Measurement
StatisticalResult
ExperimentSpecVersion
Claim/Hypothesis context
```

Output：

```text
analysis summary Artifact
plot/table ArtifactVersions
StatisticalResult candidates
Claim candidates
limitations
anomaly warnings
```

不得修改 Measurement。

---

# 16. CriticAgent

Critic 应主动寻找：

```text
confounders
data leakage
missing baselines
statistical weakness
overclaim
alternative explanation
negative results
reproducibility problems
literature contradiction
```

Output：

```text
Assessment candidates
AuditFinding candidates
DecisionRecommendation candidates
Experiment revision candidates
```

CriticAgent != ReviewerAgent。

---

# 17. ReviewerAgent

ReviewerAgent 用于 formal/internal review。

隔离要求：

```text
authoring execution context
≠ reviewer execution context
```

至少：

- 不使用 Writer/Coder Agent 的隐藏 scratchpad；
- 输入使用 Frozen target + canonical evidence；
- reviewer prompt/version 独立记录；
- 可采用不同 model/provider；
- ReviewRecord promotion 显式。

---

# 18. Planner / Orchestrator

Orchestrator 负责：

```text
task decomposition
dependency graph
role assignment
strategy selection
budget allocation
human checkpoints
recovery
termination
```

Orchestrator 不得：

```text
invent Measurement
modify frozen object
skip required Approval
hide failed task step
```

Planner 输出是 TaskGraph candidate，写入 ResearchTaskStep 后才成为 runtime plan。

---

# 19. EvoScientist-like Native Orchestration

Phase 3 MUST 实现一个原生 scientific workflow strategy，借鉴 specialized-agent pattern：

```text
Intake
↓
PlannerAgent
↓
ResearchAgent
↓
ExperimentDesignAgent
↓
CodingAgent
↓
DebugAgent
↓
ExecutionAgent
↓
AnalysisAgent
↓
CriticAgent
↓
WritingAgent
↓
ReviewerAgent
↓
Verify / Human Gate
```

但允许动态跳转：

```text
Analysis → Debug
Critic → ExperimentDesign
Review → Writing
Review → Experiment
Research → Hypothesis
```

Workflow 状态由 ResearchTask/Step canonical runtime records 保存，不只保存在 LangGraph checkpoint。

---

# 20. Strategy Registry

```yaml
StrategyDescriptor:
  strategy_id: string
  strategy_version: string
  task_types: list
  required_capabilities: list
  autonomy_supported:
    [A0,A1,A2,A3]
  configuration_schema_version: string
  configuration_artifact_version_id: UUID
```

Phase 3 至少：

```text
human_guided_research
evoscientist_like
bounded_autonomous_experiment
progressive_tree_search
replication
internal_review
```

---

# 21. Human Autonomy Levels

沿用上位设计：

```text
A0 Suggest
A1 Draft
A2 Execute Approved Plan
A3 Bounded Autonomous Loop
```

Phase 3 不进入 A4 High Autonomy。

## A0

Agent 只建议，不创建 canonical DRAFT。

## A1

Agent 可以通过 Application Commands 创建 DRAFT object；Human 决定 freeze。

## A2

Human freeze ExperimentSpec 后 Agent 可以执行 Code/Run/Analysis。

## A3

Agent 可在明确：

```text
budget
allowed datasets
allowed code scope
allowed metrics
max branches
max iterations
network policy
termination policy
```

范围内自主迭代。

Formal release 仍需 Governance Gate。

---

# 22. HumanCheckpoint

```yaml
HumanCheckpoint:
  id: UUID
  research_task_id: UUID
  step_id: UUID|null

  checkpoint_type:
    plan_review |
    hypothesis_selection |
    experiment_approval |
    budget_extension |
    code_risk |
    claim_freeze |
    manuscript_release |
    exception

  status:
    PENDING |
    APPROVED |
    REJECTED |
    MODIFIED |
    EXPIRED

  request_payload: StructuredValue
  response_payload: StructuredValue|null

  requested_at: Instant
  responded_at: Instant|null
  responded_by: ActorId|null
```

Human response 不删除 Agent recommendation。

---

# 23. Budget Policy

自治研究必须有预算。

```yaml
ExecutionBudget:
  id: UUID

  max_wall_time_seconds
  max_agent_steps
  max_llm_calls
  max_token_cost
  max_search_calls
  max_code_iterations
  max_experiment_runs
  max_gpu_hours
  max_tree_nodes
  max_tree_depth
  max_parallel_branches

  hard_stop: bool
```

Budget usage 由 CapabilityInvocation 累积。

超预算：

```text
TERMINATED_BUDGET
```

或请求 Human extension。

---

# 24. Termination Policy

```yaml
TerminationPolicy:
  max_no_improvement_iterations
  min_progress_score
  repeated_failure_threshold
  duplicate_hypothesis_threshold
  confidence_stop_threshold
  budget_stop
  human_stop
  policy_stop
  success_condition
```

禁止：

```text
while not paper_accepted:
    continue
```

---

# 25. Recovery / Retry

错误分类：

```text
TRANSIENT_TOOL_ERROR
MODEL_ERROR
SANDBOX_ERROR
CODE_ERROR
DATA_ERROR
SCIENTIFIC_INVALIDITY
POLICY_BLOCK
HUMAN_REJECT
UNKNOWN_EXTERNAL_OUTCOME
```

Retry 只适合 transient/tool/model。

科学无效不能 retry 到“成功”为止而隐藏失败。

Recovery：

```text
retry same step
switch capability adapter
spawn debug step
rollback working workspace
create new ExperimentSpecVersion
request human
terminate branch
```

---

# 26. Agent Working Memory

分三层：

```text
Canonical Scientific Memory
= ResearchBase Core

Task Working Memory
= ResearchTask scoped

Execution Scratchpad
= one AgentExecutionInstance
```

Task Working Memory 可以包含：

```text
plan
notes
hypothesis candidates
branch scores
tool summaries
conversation condensed state
```

必须可丢失/重建。

推荐持久化为：

```text
WorkingMemorySnapshot ArtifactVersion
```

不是新的 scientific entity。

---

# 27. Canonical Context Loader

Agent 每次关键动作前必须从 Core 加载最新允许上下文：

```python
class CanonicalContextLoader(Protocol):
    def load_for_task(self, task_id, context) -> CanonicalContext: ...
```

Context 应包含：

```text
Frozen research objects
current DRAFT objects where permitted
Run/evidence trace
literature context
audit/stale/invalid status
review/decision constraints
budget/policy
```

Agent 不能只依赖 conversation history。

---

# 28. Candidate Promotion

统一：

```text
GENERATED
→ CANDIDATE
→ VALIDATED
→ PROMOTED_TO_DRAFT
→ FROZEN
```

Promotion service 示例：

```text
promote_hypothesis_candidate
promote_experiment_spec_candidate
promote_artifact_candidate
promote_measurement_candidate
promote_claim_candidate
promote_review_candidate
```

Formal FROZEN 操作仍使用 Phase 1/2 freeze Commands。

---

# 29. Experiment Search Manager

Phase 3 的关键新增。

```yaml
ExperimentSearchSession:
  id: UUID
  research_task_id: UUID

  root_hypothesis_version_id: UUID|null
  root_experiment_spec_version_id: UUID|null

  strategy_id: string
  strategy_version: string

  status:
    ACTIVE |
    SUCCEEDED |
    EXHAUSTED |
    TERMINATED_BUDGET |
    CANCELLED

  budget_id: UUID
  objective_definition: StructuredValue
  scoring_policy: StructuredValue

  created_at: Instant
```

---

# 30. ExperimentSearchNode

```yaml
ExperimentSearchNode:
  id: UUID
  search_session_id: UUID
  parent_node_id: UUID|null

  depth: int
  branch_kind:
    new_direction |
    refinement |
    ablation |
    baseline |
    scale_up |
    debug |
    replication

  hypothesis_candidate_ref: StructuredReference|null
  experiment_spec_version_id: UUID|null
  run_ids: list[UUID]

  status:
    PROPOSED |
    READY |
    RUNNING |
    EVALUATED |
    PRUNED |
    FAILED |
    SELECTED |
    TERMINATED

  score: decimal|null
  score_components: StructuredValue|null
  novelty_score: decimal|null
  uncertainty: decimal|null

  created_by_execution_id: UUID
  created_at: Instant
```

run_ids 实现时用 relation table。

---

# 31. Progressive Agentic Tree Search

借鉴 AI Scientist-v2 的核心思想，但实现 ResearchBase-native Strategy。

每轮 Experiment Manager 决定：

```text
expand new direction
refine existing node
run ablation
increase fidelity
rerun for uncertainty
prune
stop
escalate human
```

决策输入：

```text
branch lineage
results
critic feedback
budget
novelty
uncertainty
failure history
diversity
```

输出：

```text
SearchDecisionRecord
```

---

# 32. SearchDecisionRecord

```yaml
SearchDecisionRecord:
  id: UUID
  search_session_id: UUID

  candidate_node_ids: list[UUID]
  selected_action: string
  selected_node_id: UUID|null

  rationale: text
  scoring_snapshot: StructuredValue
  budget_snapshot: StructuredValue

  decided_by_agent_execution_id: UUID
  created_at: Instant
  content_hash: SHA256
```

Decision 不覆盖 scientific result。

---

# 33. Tree Search Safety Invariants

```text
failed node must remain
pruned node must remain
negative result must remain
all executed Runs remain canonical
branch score is not Measurement
search score cannot rewrite Claim
no branch deletion for presentation
same ExperimentSpec material change → new Version
budget is hard bound
formal Claim requires normal EvidenceRelation
```

---

# 34. Branch Scoring

Score 可以组合：

```text
scientific performance
uncertainty reduction
novelty
replicability
cost
risk
critic assessment
diversity
```

但 score 是 search heuristic。

```text
SearchScore ≠ ScientificValidity
```

---

# 35. Experiment Fidelity Levels

Agent tree search 可以分级：

```text
F0 static/code sanity
F1 tiny subset
F2 low-cost pilot
F3 standard experiment
F4 replication/high fidelity
```

每个 fidelity 仍形成真正 Run。

不能把 F1 pilot 当成 F4 evidence 而不标 scope。

---

# 36. Coding → Execution Pipeline

标准：

```text
ExperimentSpecVersion FROZEN
↓
CodingTask
↓
CodingCapability
↓
ArtifactVersion(code/config/env)
↓
verification
↓
Run
↓
ComputeCapability
↓
Measurement
↓
Analysis
```

如果 Coding Agent 修改 ExperimentSpec material intent：

```text
STOP
→ create new ExperimentSpecVersion candidate
```

不能静默调整。

---

# 37. DebugAgent

DebugAgent 负责技术 failure：

```text
syntax
dependency
runtime error
OOM
file path
configuration mismatch
```

不负责通过修改科学目标“让结果变好”。

如果 debug 需要改变：

```text
dataset
metric
seed policy
model architecture
baseline
analysis protocol
```

必须新 ExperimentSpecVersion。

---

# 38. Model / Provider Router

```python
class ModelRouter(Protocol):
    def select(self, request: ModelRequest, context) -> ModelProfile: ...
```

可以按：

```text
agent role
task difficulty
privacy
budget
latency
context size
reasoning need
```

选模型。

模型切换必须写入 AgentExecution provenance。

---

# 39. Skills

Skill 是：

```text
prompt/tool/workflow package
```

不是 Authority。

```yaml
SkillDescriptor:
  skill_id
  version
  compatible_agent_roles
  required_capabilities
  source
  content_hash
  trust_level
```

安装：

```text
TRUSTED_BUILTIN
REVIEWED_PROJECT
UNTRUSTED_EXTERNAL
```

Phase 3 禁止 Agent 自行从 GitHub 安装并立即执行未经审核 skill。

---

# 40. MCP / Tool Integration

MCP 或类似工具协议通过 CapabilityGateway。

```text
Agent
→ CapabilityGateway
→ MCP Adapter
→ Tool
```

工具描述不能直接赋予权限。

Tool Policy 决定：

```text
read
write workspace
network
compute
external side effect
```

---

# 41. Agent Policy

```yaml
AgentToolPolicy:
  id: UUID
  version: int

  allowed_capabilities[]
  denied_capabilities[]

  filesystem_scope
  network_scope
  compute_scope
  external_effect_scope

  max_tool_calls
  max_parallel_invocations

  created_at
  content_hash
```

Phase 3 可实现轻量策略，不替代未来完整 Authority engine。

---

# 42. Agent Evaluation Harness

Agent runtime 必须可评估，不只看最终“论文好不好”。

指标：

```text
task completion
canonical promotion accuracy
hallucinated object rate
invalid command rate
closure violation rate
unnecessary experiment rate
failed-run hiding rate
budget adherence
human intervention rate
recovery success
reproducibility
review defect rate
```

Golden tasks：

```text
literature-to-hypothesis
hypothesis-to-experiment
code-and-run
debug-failure
analyze-negative-result
critic-overclaim
review-manuscript
bounded-search
```

---

# 43. Orchestrator Commands

Phase 3 MUST：

```text
create_research_task
start_research_task
pause_research_task
resume_research_task
cancel_research_task

create_task_plan
add_task_step
start_task_step
finish_task_step
fail_task_step

create_human_checkpoint
respond_human_checkpoint

create_agent_execution
finish_agent_execution
record_capability_invocation

create_working_memory_snapshot

start_experiment_search
propose_search_node
evaluate_search_node
record_search_decision
prune_search_node
select_search_node
finish_experiment_search
```

Agent-generated scientific candidates仍用 Phase 1/2 Commands。

---

# 44. Orchestrator Queries

```text
get_research_task
get_task_graph
get_task_progress
get_task_budget
get_task_agent_executions
get_agent_execution_trace
get_capability_invocations
get_current_working_memory
get_pending_human_checkpoints

get_experiment_search_tree
get_branch_lineage
get_search_budget
get_search_decision_history

get_canonical_context_for_task
get_task_scientific_outputs
```

---

# 45. Event / Queue Model

Phase 3 开始有长任务，可以引入后台 worker/queue，但仍不要求微服务。

推荐：

```text
API
→ PostgreSQL task state
→ worker queue
→ Runtime worker
→ Application Services
```

可选技术：

```text
Celery / Dramatiq / RQ / arq / workflow engine
```

但 canonical orchestration state 必须在 ResearchBase DB，而不是只在 broker。

---

# 46. Outbox / Inbox

若引入异步 worker，Phase 3 SHOULD 实现 transactional outbox：

```text
Application TX
→ update task state
→ insert OutboxEvent
→ commit
→ dispatcher
```

避免：

```text
DB committed
queue publish failed
```

Worker 使用 inbox/idempotency key 防重复。

---

# 47. Task Lease / Concurrency

防止两个 worker 同时执行一步：

```yaml
TaskLease:
  step_id
  worker_id
  lease_until
  heartbeat_at
```

或 DB advisory lock/`SELECT FOR UPDATE SKIP LOCKED`。

必须支持 worker crash 后 reclaim。

---

# 48. Idempotency

Phase 3 高度异步，以下必须 idempotent：

```text
start step
finish step
capability invocation result ingestion
Run creation for one search node
Artifact registration by content hash
human checkpoint response
search-node evaluation
```

Logical action ID 不能靠 HTTP request 数量。

---

# 49. Unknown Outcome

尤其 Coding/Compute/External tool：

```text
timeout ≠ failed
```

状态：

```text
UNKNOWN_OUTCOME
```

必须 reconcile：

```text
query external handle
workspace status
job status
artifact existence
```

再决定 retry。

---

# 50. Security

Phase 3 是风险显著上升阶段。

必须：

```text
sandbox code execution
resource limits
network policy
package install policy
secrets isolation
project workspace isolation
tool allowlist
human approval for dangerous operations
```

禁止：

```text
LLM-generated shell on host
mount host home read-write
cloud credentials exposed broadly
arbitrary outbound network by default
```

---

# 51. Agent Prompt Injection / Tool Injection

Research sources、README、网页、论文和 repo 内容都是 untrusted input。

必须区分：

```text
data content
tool instructions
system policy
```

网页/PDF 中“ignore previous instructions”不能改变 Agent tool policy。

Coding repo 中恶意 AGENTS/README 也必须受 workspace policy 控制。

---

# 52. Research Data Leakage

Task Context Loader 必须 project-scoped。

Agent 不得：

```text
Project A working memory
→ Project B prompt
```

除非明确 cross-project grant。

Vector/memory index 必须有 project namespace。

---

# 53. Agent Observability

至少：

```text
task_id
step_id
agent_execution_id
agent_version
strategy_id/version
capability invocation IDs
model/provider
tool calls
latency
token/cost
budget usage
human checkpoints
errors
canonical outputs
```

支持 trace：

```text
ClaimVersion
← AgentExecution
← ResearchTask
```

但 Agent provenance 不替代 Claim evidence。

---

# 54. Runtime Replay

Phase 3 SHOULD 支持“行为回放”，不是 deterministic LLM exact replay。

能重建：

```text
what task
what inputs
what AgentVersion
what strategy
what model
what tools
what artifacts
what commands
what outputs promoted
```

LLM token-level output可用 trace Artifact 保存，但不保证重算一致。

---

# 55. Agent State Snapshot

长任务 checkpoint：

```text
ResearchTask state
TaskGraph
working memory Artifact
budget
pending checkpoint
branch tree
```

不复制 scientific canonical objects，只保存 refs。

---

# 56. WritingAgent

Phase 2 已定义 Writing Capability boundary。

Phase 3 正式 Agent：

输入：

```text
canonical Claim/Conclusion
LiteratureEvidence
ManuscriptVersion
ReviewIssues
```

输出：

```text
draft Artifact
placement candidates
revision candidates
author response candidates
```

禁止从 scratchpad 编造 citation。

---

# 57. End-to-End Research Strategy

Phase 3 MUST 有一条受控完整策略：

```text
ResearchQuestion
→ Phase2 ResearchStrategy
→ Hypothesis candidates
→ Human/A1 promotion
→ ExperimentDesign
→ Coding
→ Run
→ Analysis
→ Critic
→ bounded refinement loop
→ Claim DRAFT
→ evidence linking
→ Human freeze gate
→ ScientificConclusion
→ Manuscript draft
→ Reviewer
```

默认 autonomy A1/A2。

---

# 58. Bounded Autonomous Experiment Strategy

A3：

```text
Frozen Hypothesis
↓
SearchSession
↓
propose branches
↓
freeze ExperimentSpec candidates under policy
↓
code/run/analyze
↓
score/critic
↓
expand/refine/prune
↓
termination
↓
best candidate recommendations
↓
Human scientific gate
```

Agent 可自动 freeze ExperimentSpec only if policy explicitly permits A3 experiment specification authority；否则 Human checkpoint。

---

# 59. Negative Results

Phase 3 强制：

```text
negative Run
failed hypothesis
non-significant measurement
pruned branch
```

保留。

禁止 optimize system by deleting unfavorable results。

这也是避免 autonomous p-hacking/cherry-picking 的核心。

---

# 60. Statistical Guardrails

Autonomous loop 中：

- MetricDefinition frozen；
- planned analysis优先；
- repeated testing记录；
- multiple-comparison risk提示；
- search score 与 final scientific statistic 分离；
- 允许探索性分析，但必须标 exploratory；
- confirmatory Claim 需要明确 policy。

---

# 61. Research Loop Lineage

每个 branch 必须能追：

```text
parent hypothesis
parent ExperimentSpec
reason for mutation
Coding artifacts
Run
Measurements
Critic feedback
SearchDecision
```

Lineage 不允许只保留最终 winner。

---

# 62. Experiment Mutation Types

显式分类：

```text
HYPOTHESIS_CHANGE
METHOD_CHANGE
HYPERPARAMETER_CHANGE
DATA_CHANGE
BASELINE_CHANGE
METRIC_CHANGE
ANALYSIS_CHANGE
SCALE_CHANGE
DEBUG_NON_SEMANTIC
```

其中除 `DEBUG_NON_SEMANTIC` 外通常要求新 ExperimentSpecVersion。

---

# 63. Non-semantic Debug

允许修复：

```text
path typo
syntax error
dependency pin
logging
OOM batch size only if declared non-scientific?
```

是否 material 必须由 `SemanticImpactAssessment` 判断。

如果不确定，默认 material。

---

# 64. SemanticImpactAssessment for Agent Edits

```yaml
SemanticImpactAssessment:
  id
  target_version
  proposed_change_artifact
  result:
    NON_SEMANTIC |
    SCIENTIFIC_MINOR |
    SCIENTIFIC_MATERIAL |
    UNKNOWN
  rationale
  assessed_by
  created_at
```

Phase 3 可以自动建议，但 high-impact change MAY require Human.

---

# 65. Agent Reviewer Independence

Formal review 时推荐：

```text
different AgentVersion
different execution
fresh context loader
no author scratchpad
optional different model/provider
```

Reviewer 可访问 canonical evidence和必要 manuscript，但不访问未公开 internal chain-of-thought。

---

# 66. Agent Authority

继续继承：

```text
Agent role ≠ Authority
Skill ≠ Authority
Tool availability ≠ Authority
acting_on_behalf_of ≠ permission inheritance
```

A3 autonomy 只是 workflow policy，不是 P4。

---

# 67. Capability Failure Isolation

一个 adapter failure 不得使 task corrupt。

例如：

```text
OpenHands failed
→ switch CodexAdapter
```

但产生新的 CapabilityInvocation。

不得伪装成同一次成功调用。

---

# 68. Provider Lock-in Prevention

Core 不存：

```text
openai_response_id
claude_message
langgraph_checkpoint
openhands_conversation
```

为 scientific truth。

这些可作为 execution metadata/Artifact。

---

# 69. Agent Runtime Package Layout

建议：

```text
src/researchbase/
├── agent_runtime/
│   ├── domain/
│   │   ├── research_task.py
│   │   ├── task_step.py
│   │   ├── agent_execution.py
│   │   ├── capability_invocation.py
│   │   ├── checkpoint.py
│   │   ├── budget.py
│   │   └── experiment_search.py
│   ├── application/
│   ├── ports/
│   └── services/
├── strategies/
│   ├── scientific/
│   │   ├── evoscientist_like.py
│   │   ├── bounded_experiment.py
│   │   └── progressive_tree_search.py
├── capabilities/
│   ├── coding/
│   ├── compute/
│   ├── sandbox/
│   ├── analysis/
│   └── model/
└── adapters/
    ├── coding/
    │   ├── codex/
    │   ├── openhands/
    │   └── acp/
    ├── compute/
    └── runtime/
```

---

# 70. Database Increment

建议新增：

```text
research_tasks
research_task_steps
research_task_step_dependencies

agent_versions
agent_execution_instances
capability_invocations

human_checkpoints
execution_budgets
termination_policies
agent_tool_policies

experiment_search_sessions
experiment_search_nodes
experiment_search_node_runs
search_decision_records

semantic_impact_assessments

task_outbox
task_inbox
task_leases

strategy_registry / configuration may remain docs/config initially
```

约 20–30 张增量表。

---

# 71. Key DB Constraints

```text
ResearchTaskStep belongs to ResearchTask
AgentExecution belongs to task/step
CapabilityInvocation belongs to AgentExecution
SearchNode parent belongs to same SearchSession
Run relation references canonical Run
all historical execution records ON DELETE RESTRICT
HumanCheckpoint response immutable after terminal
Budget usage monotonic
SearchDecision immutable
AgentVersion content/config hash stable
```

---

# 72. API Contracts

```text
POST /research-tasks
POST /research-tasks/{id}:start
POST /research-tasks/{id}:pause
POST /research-tasks/{id}:resume
POST /research-tasks/{id}:cancel
GET  /research-tasks/{id}
GET  /research-tasks/{id}/graph
GET  /research-tasks/{id}/trace

POST /research-tasks/{id}/checkpoints
POST /human-checkpoints/{id}:respond

GET /agent-executions/{id}
GET /agent-executions/{id}/capabilities

POST /experiment-search
POST /experiment-search/{id}:step
POST /experiment-search/{id}:pause
POST /experiment-search/{id}:stop
GET  /experiment-search/{id}/tree

GET /research-tasks/{id}/budget
GET /research-tasks/{id}/canonical-context
```

Coding/Compute adapter endpoint 可以内部 worker 使用，不必公开外部 REST。

---

# 73. Error Model

新增：

```text
TASK_INVALID_STATE
TASK_BUDGET_EXCEEDED
TASK_POLICY_BLOCKED
TASK_LEASE_CONFLICT
CHECKPOINT_REQUIRED
CHECKPOINT_REJECTED
AGENT_VERSION_DISABLED
CAPABILITY_NOT_ALLOWED
CAPABILITY_FAILED
CAPABILITY_UNKNOWN_OUTCOME
SANDBOX_POLICY_VIOLATION
COMPUTE_JOB_FAILED
AGENT_OUTPUT_NOT_PROMOTABLE
SEARCH_BRANCH_INVALID
SEARCH_BUDGET_EXCEEDED
SEARCH_DUPLICATE_NODE
SEMANTIC_CHANGE_REQUIRES_NEW_VERSION
RECOVERY_NOT_ALLOWED
```

---

# 74. Test Matrix

## Task Runtime

- state transitions；
- pause/resume；
- cancellation；
- worker crash/reclaim；
- step DAG；
- no skipped dependency。

## Agent Execution

- version provenance；
- input/output hash；
- execution cannot mutate canonical objects directly；
- failure preserved；
- alternate adapter produces separate invocation。

## Capability

- policy allow/deny；
- timeout；
- retry；
- unknown outcome；
- sandbox violation；
- version pin。

## Coding

- code produces ArtifactVersion；
- tests recorded；
- no host write；
- material edit detection；
- failed code remains provenance。

## Experiment Search

- branch lineage；
- prune preserves node；
- failed Run preserved；
- budget stop；
- no repeated duplicate branch；
- scoring does not change Measurement；
- selected winner does not delete losers。

## Human Gate

- A0/A1/A2/A3 behavior；
- checkpoint required；
- reject stops/pivots；
- Agent cannot approve itself。

## Memory

- project isolation；
- scratchpad loss recoverable；
- canonical context reload；
- no chat-memory scientific truth。

---

# 75. Golden E2E

## 75.1 Hypothesis → Code → Run → Claim

```text
ResearchTask
→ ExperimentDesignAgent
→ ExperimentSpec DRAFT
→ Human freeze
→ CodingAgent
→ ArtifactVersion
→ ExecutionAgent
→ Run
→ AnalysisAgent
→ Claim candidate
→ Evidence link
→ Human freeze
```

## 75.2 Debug Loop

```text
Run FAILED
→ DebugAgent
→ non-semantic fix
→ ArtifactVersion
→ new Run
```

If material：

```text
→ new ExperimentSpecVersion
```

## 75.3 Negative Result

```text
Hypothesis
→ Run
→ no improvement
→ Critic
→ Claim candidate: no supported improvement
```

系统不得自动反复实验直到得到正结果。

## 75.4 Bounded Tree Search

```text
root
├─ branch A → Run → score
├─ branch B → Run → score
└─ branch C → fail
→ refine A
→ ablation A1
→ budget stop
→ recommendation
```

所有节点/Run 保留。

## 75.5 Reviewer Independence

```text
WritingAgent execution
→ ManuscriptVersion
→ ReviewerAgent new execution/context
→ ReviewRecord candidate
→ promote review
```

---

# 76. Failure Injection

## F1 Agent tries direct DB

Architecture test / dependency rules block。

## F2 Coding Agent attempts host access

Sandbox denies + capability invocation failed。

## F3 Agent tries to alter Measurement

Application rejects immutable record change。

## F4 Agent hides failed branch

Tree closure audit detects Run/search node missing relation or illegal deletion.

## F5 Budget overrun

Task becomes TERMINATED_BUDGET / WAITING_HUMAN for extension。

## F6 Worker crash after external compute submission

Invocation UNKNOWN_OUTCOME → reconcile external handle，not blindly resubmit。

## F7 Prompt injection in paper/repo

Untrusted text cannot alter Capability Policy/System Policy。

## F8 Cross-project memory retrieval

namespace/access check rejects。

---

# 77. Architecture Tests

```text
test_agent_runtime_no_direct_persistence_write
test_capability_gateway_is_only_tool_boundary
test_agent_framework_not_domain_dependency
test_agent_memory_not_canonical_science
test_coding_output_requires_artifact_version
test_execution_requires_frozen_spec_and_inputs
test_failed_search_nodes_are_retained
test_negative_runs_are_retained
test_search_score_not_measurement
test_a3_budget_is_hard_bound
test_agent_cannot_self_approve
test_reviewer_execution_is_separate
test_project_memory_isolation
test_sandbox_default_denies_host_access
test_unknown_outcome_not_blind_retry
```

---

# 78. Work Packages

| WP | 范围 | Owner |
|---|---|---|
| WP3-A Runtime Core | ResearchTask/Step/Execution/Budget | Tech Lead + Dev A |
| WP3-B Capability Infrastructure | Gateway/Sandbox/Compute | Dev B |
| WP3-C Coding Agents | Codex/OpenHands/ACP adapters | Dev C |
| WP3-D Scientific Agents | Planner/Analysis/Critic/Reviewer | Dev D |
| WP3-E Autonomous Search | Search Manager/Tree Strategy | Tech Lead + Dev E |
| WP3-F Evaluation/Hardening | E2E/Security/Agent Bench | Dev F |

依赖：

```text
Phase1+2 stable → A
A → B
B → C/D
A+B+D → E
all → F
```

---

# 79. PR Sequence

## PR3-00 Agent Runtime Bootstrap

modules, migrations, architecture tests.

## PR3-01 ResearchTask / Step Graph

states, DAG, commands/queries.

## PR3-02 AgentVersion / Execution

version provenance, execution trace.

## PR3-03 CapabilityInvocation / Gateway

adapter-neutral tool boundary.

## PR3-04 Budget / Termination / HumanCheckpoint

A0-A3 groundwork.

## PR3-05 Working Memory / CanonicalContextLoader

project scope, Artifact snapshots.

## PR3-06 SandboxCapability

profiles, limits, policy tests.

## PR3-07 ComputeCapability

async job handles, reconciliation.

## PR3-08 CodingCapability Port + Fake Adapter

contract first.

## PR3-09 Codex Adapter

or equivalent primary coding agent.

## PR3-10 OpenHands / ACP Adapter

at least one alternate adapter SHOULD.

## PR3-11 ExecutionAgent

Run creation/seal/compute/outcome.

## PR3-12 AnalysisAgent

statistical/artifact candidates.

## PR3-13 CriticAgent

overclaim/leakage/method checks.

## PR3-14 ReviewerAgent

independent review execution.

## PR3-15 EvoScientist-like Strategy

plan/research/code/debug/analyze/write/review orchestration.

## PR3-16 Experiment Search Core

session/node/lineage.

## PR3-17 Progressive Tree Search Strategy

Experiment Manager decisions.

## PR3-18 A3 Bounded Autonomous Loop

budget/checkpoint/policy.

## PR3-19 Async Outbox/Lease/Recovery

crash-safe workers.

## PR3-20 Agent Evaluation Harness

golden tasks + metrics.

## PR3-21 Security Failure Injection

sandbox/prompt injection/memory leakage.

## PR3-22 Phase 3 E2E

end-to-end controlled research.

## PR3-23 Hardening

performance, migration, docs, exit report.

---

# 80. Code Review Checklist

## Runtime

- workflow state 是否只存在 framework checkpoint？
- ResearchTask 是否可恢复？
- AgentExecution 是否记录 AgentVersion？
- step failure 是否保留？

## Capability

- Agent 是否直接调用 vendor SDK？
- policy/sandbox 是否绕过？
- unknown outcome 是否盲 retry？
- adapter version 是否记录？

## Scientific

- candidate 是否直接 FROZEN？
- Agent 是否修改 Measurement/Run history？
- ExperimentSpec material change 是否新 Version？
- negative Run 是否保存？

## Search

- pruned/failed node 是否被删除？
- score 是否混成 scientific metric？
- budget 是否 hard？
- cherry-picking 是否可能？

## Memory

- conversation 是否被当 scientific truth？
- project namespace 是否隔离？
- canonical context 是否重新加载？

---

# 81. Phase 3 Definition of Done

1. Domain + application tests；
2. PostgreSQL integration/migration；
3. crash/recovery tests；
4. sandbox security tests；
5. Capability adapter contract tests；
6. AgentExecution provenance；
7. Candidate promotion boundary；
8. budget/termination；
9. failed/negative branch retention；
10. Phase 1/2 regression；
11. no provider-specific Core schema；
12. agent evaluation metrics；
13. threat/failure injection pass。

---

# 82. Phase 3 Exit Criteria

```text
[ ] ResearchTask resumable state PASS
[ ] AgentVersion / AgentExecution provenance PASS
[ ] CapabilityGateway policy boundary PASS
[ ] HumanCheckpoint A0-A3 semantics PASS
[ ] Budget / termination hard bounds PASS
[ ] Agent Working Memory ≠ Canonical Memory PASS
[ ] Sandbox isolation PASS
[ ] CodingCapability → ArtifactVersion PASS
[ ] ComputeCapability unknown-outcome reconciliation PASS
[ ] ExecutionAgent → sealed Run PASS
[ ] AnalysisAgent never mutates Measurement PASS
[ ] CriticAgent output candidate semantics PASS
[ ] Reviewer independent execution PASS
[ ] EvoScientist-like native orchestration PASS
[ ] Experiment Search lineage PASS
[ ] Progressive tree-search strategy PASS
[ ] failed/pruned/negative branches retained PASS
[ ] A3 bounded autonomous experiment loop PASS
[ ] Prompt/tool injection protections PASS
[ ] Cross-project memory isolation PASS
[ ] Phase 1 + Phase 2 exit tests continue PASS
```

Exit artifacts：

```text
phase3_exit_report.md
agent_runtime_inventory.md
capability_adapter_inventory.md
sandbox_security_report.md
autonomous_search_trace_demo.md
agent_evaluation_report.md
recovery_failure_injection_report.md
```

STOP，等待 Phase 4 GO。

---

# 83. Phase 3 → Phase 4 Stable Contract

Phase 4 可以增加：

```text
self-evolving skills
automatic strategy selection
multi-project scientific memory
large-scale experiment search
replication agents
advanced novelty/review
long-horizon autonomy
```

但不应重构：

```text
ResearchTask
AgentExecution
CapabilityInvocation
StrategyDescriptor
HumanCheckpoint
ExecutionBudget
ExperimentSearchSession/Node
Canonical Context boundary
Candidate Promotion boundary
```

稳定 API：

```text
create/start/pause/resume ResearchTask
invoke CapabilityGateway
load CanonicalContext
record AgentExecution
promote candidates
create/check HumanCheckpoint
query/update budget
create/evaluate search node
query branch lineage
```

---

# 84. Codex Execution Template

```text
You are implementing ResearchBase Phase 3.

Authoritative specifications:
1. ResearchBase 全系统设计文档_架构补全版_v1.2
2. ResearchBase Phase 1 Development Specification v1.1
3. ResearchBase Phase 2 Development Specification v1.0
4. ResearchBase Phase 3 Development Specification v1.0

Implement PR3-XX only.

Rules:
- Agents MUST access scientific state only through Application Commands/Queries.
- Runtime/framework state is not canonical scientific state.
- Candidate outputs are not canonical until promoted.
- Coding output must become ArtifactVersion before formal Run use.
- LLM-written code must execute in a constrained sandbox.
- Preserve failed, negative, and pruned experiment branches.
- Search score is not scientific validity.
- Respect hard budget and termination policies.
- Do not implement Phase 4 self-evolving autonomy.
- Do not allow agent self-approval.
- Preserve Phase 1/2 Frozen Provenance Closure.
- Stop after PR3-XX.

At the end report:
1. changed files,
2. migrations,
3. tests/results,
4. agent/runtime/adapter versions,
5. security implications,
6. architecture deviations,
7. unresolved issues,
8. explicit confirmation no later PR was implemented.
```

---

# 85. Reference System Pinning Notes

Phase 3 implementation 前重新 pin：

```text
EvoScientist
OpenHands SDK/runtime
primary Coding Agent API/CLI
AI Scientist-v2 reference
chosen runtime framework
MCP/tool SDK
```

架构核验时，EvoScientist current upstream 明确采用 plan、research、code、debug、analyze、write 六类 sub-agents，并提供 persistent memory、multi-provider、MCP/skills；AI Scientist-v2 当前公开描述的核心仍是 Experiment Manager 引导的 progressive agentic tree search；OpenHands V1 当前文档强调 Agent Core、tools、workspace/sandbox、agent server 分层以及 composable components。

这些是实现参考，不是 canonical schema dependency。

---

# 86. Phase 3 Invariants

```text
P3-INV-001 Agent Runtime MUST NOT own canonical scientific state.
P3-INV-002 Agent framework checkpoint MUST NOT be the only ResearchTask state.
P3-INV-003 All canonical writes MUST go through Application Commands.
P3-INV-004 All material scientific reads SHOULD go through stable Queries.
P3-INV-005 Agent output MUST remain candidate until explicit promotion.
P3-INV-006 Coding Agent output MUST become ArtifactVersion before Run.
P3-INV-007 Formal experiment execution MUST use sealed Run inputs.
P3-INV-008 Analysis/Critic Agents MUST NOT mutate Measurement/StatisticalResult history.
P3-INV-009 Failed, negative and pruned experiment branches MUST remain traceable.
P3-INV-010 Experiment search score MUST remain distinct from scientific metrics.
P3-INV-011 Autonomous loops MUST have hard budget and termination policies.
P3-INV-012 Agent autonomy level MUST remain distinct from scientific/governance Authority.
P3-INV-013 Agent MUST NOT self-approve Formal scientific release.
P3-INV-014 Reviewer Agent execution SHOULD be independent from authoring execution.
P3-INV-015 Working memory MUST remain distinct from Canonical Scientific Memory.
P3-INV-016 Project-scoped memory MUST NOT leak across projects.
P3-INV-017 LLM-written code MUST execute in a constrained sandbox by default.
P3-INV-018 Unknown external outcomes MUST be reconciled before retry.
P3-INV-019 Runtime/model/provider MUST remain replaceable at Core boundary.
P3-INV-020 Phase 1/2 Frozen Provenance Closure MUST remain intact.
```

---

# 87. Phase 3 最终施工结论

Phase 3 不是“加几个 Agent”。

真正交付的是：

```text
可恢复的科研任务运行时
+
可替换的 Capability/Agent Adapter
+
受控代码执行
+
Human/Agent 共同科研流程
+
Agent provenance
+
受预算约束的自主实验循环
+
完整实验分支 lineage
```

最终验收标准：

> **给定任意一个 Agent 产生的正式 Claim/Manuscript/Experiment 结果，系统能精确说明它属于哪个 ResearchTask、由哪个 AgentVersion、哪些 Capability 调用、哪些代码/Run/Measurement 和哪些 Human Gate 产生；给定一个自治实验搜索任务，系统能够保留全部成功、失败、负结果和被剪枝分支，并证明 Agent 没有通过删除失败实验、修改历史数据或无限重试来制造“成功”。**

---

# 85. Harness Runtime Integration Addendum — Phase 3

## 85.1 Phase-3 Responsibility

Phase 3 is the first phase that implements the general ResearchBase Harness Runtime as product capability. It binds Skills/strategies to the existing `ResearchTask`, `AgentExecution`, `CapabilityGateway`, `CanonicalContext`, `Candidate Promotion`, `ExecutionBudget` and checkpoint contracts.

## 85.2 Runtime Components

Implement, without creating a parallel scientific model:

```text
SkillRegistryLoader
SkillRouter
RoutingPolicy
CapabilityPolicy
HarnessResolver
HarnessFingerprintBuilder
ReviewerContextBuilder
SkillEvaluationRunner (minimum viable)
```

These components belong to agent/runtime infrastructure or application orchestration. They MUST NOT become owners of Hypothesis, ExperimentSpec, Run, Measurement, StatisticalResult, Claim or LiteratureEvidence.

## 85.3 Routing Contract

```text
ResearchTask
→ classify requested operation
→ load CanonicalContext
→ apply phase/authority/capability policy
→ resolve eligible Skill/strategy
→ create AgentExecution
→ invoke CapabilityGateway
→ produce candidate output
→ independent validation/review where required
→ explicit promotion
```

Model free-choice MUST NOT bypass phase, authority, capability or conflict policy.

## 85.4 HarnessFingerprint Provenance

Material AgentExecution MUST record or resolve an immutable HarnessFingerprint sufficient to identify the effective runtime policy and relevant Skills/Plugins/adapters used. At minimum, record available immutable identifiers/content hashes for:

```text
ResearchBase revision
Agent runtime/model version
AGENTS/config policy
selected Skill and strategy
Plugin/adapter revision
relevant Hook/MCP capability revision
```

The fingerprint is execution provenance, not scientific evidence by itself.

## 85.5 Independent Reviewer Context

Reviewer/Critic/Auditor executions SHOULD receive a reconstructed context built from authoritative specs, canonical state, candidate artifacts, execution evidence and relevant diffs rather than the author agent's complete private working context. This preserves the existing independent reviewer exit criterion.

## 85.6 Scientific Auditor Capability Rules

Auditors default to read/query + candidate-finding creation. They MUST NOT receive approval, direct persistence mutation or external publication capabilities merely because they can identify a defect.

## 85.7 EvoScientist Placement

EvoScientist-like behavior is evaluated as a replaceable orchestration strategy/reference:

```text
ResearchBase native orchestration
vs
thin EvoScientist-like service adapter
```

Either option must map to ResearchBase ResearchTask/AgentExecution/CapabilityInvocation/Candidate Promotion contracts. External workflow state MUST NOT replace canonical ResearchBase state.

## 85.8 Skill Supply-Chain and Self-Modification

A production Skill/Plugin/Hook/MCP dependency must be pinned and capability-reviewed. A running agent MUST NOT modify its own governing Skill, routing policy, capability policy or harness lock and continue that same execution as trusted. Such a modification becomes a separate candidate change requiring evaluation/review.

## 85.9 Phase-3 Exit Extension

Add to Section 82:

```text
[ ] Skill routing respects phase/authority/capability policy PASS
[ ] HarnessFingerprint bound to material AgentExecution PASS
[ ] Skill output defaults to candidate state PASS
[ ] auditor lacks approval/direct DB-write capability PASS
[ ] independent ReviewerContext reconstruction PASS
[ ] external Skills/Plugins pinned and supply-chain reviewed PASS
[ ] runtime self-modification cannot silently weaken governance PASS
[ ] STORM/EvoScientist/provider-specific state absent from Core schema PASS
```

