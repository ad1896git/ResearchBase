# ResearchBase 全系统设计文档

> 文档状态：Phase 0 Architecture Completion v1.2 / AGENTIC RESEARCH OS ARCHITECTURE COMPLETED  
> 适用范围：ResearchBase 科研底座全系统  
> 当前 Gate：**Phase 0 STOP Gate**  
> Phase 1：**NOT STARTED**

---

## 0. 文档目的

本文档是 ResearchBase 的统一全系统设计说明，用于把 Phase 0 已冻结的架构原则、领域模型、核心 Schema、科研 provenance 链、治理边界、Agent 权限、实现计划和验收标准整合为一份可直接交给研发人员或 Codex 执行的正式设计基线。

本文档不是“功能愿望清单”。它定义的是系统在进入实现阶段之前必须保持稳定的结构性约束。除非经过显式的架构变更流程，否则 Phase 1 不得绕开本文档定义的 Canonical Object、Reference、Version、Immutability、Governance 与 Provenance 规则。

本文档与以下三个冻结文档共同构成 Phase 0 设计基线：

- `architecture.md`
- `implementation_plan.md`
- `schema_registry.md`

本文主文负责把三者整合成一套完整的“系统视图”；文末附录保留三份冻结文档的完整原文，作为细粒度规范来源。

---

## 0.1 高级架构 Review 结论与修订摘要

本次 Review 重点检查两件事：**内部逻辑是否自洽**，以及**若干中级程序员是否能按图施工而不各自发明关键规则**。

Review 结论：原文的科学 provenance 与治理哲学是成立的，但实现契约不足。修订前可评价为“架构原则完整、施工图不足”；本版通过以下修改把施工歧义收敛到可控范围。

| 编号 | 严重度 | 原问题 | 本版处理 |
|---|---|---|---|
| R-01 | P0 | `Run` 被列为 Immutable Record，但执行期间又需要状态变化 | 明确 Run 状态机：终态前可状态迁移；输入在开始运行时 seal；终态后 material fields immutable |
| R-02 | P0 | DatasetSnapshot 一处写“按需”，另一处要求 Run 必须有 deterministic input | Phase 1 统一为 Run 使用 Dataset 时必须绑定 DatasetSnapshot |
| R-03 | P0 | `FrozenReference<T>` 抽象若直接落库为多态软引用，会破坏 FK 完整性 | 规定 Domain 可用 typed ref，Persistence 主链必须用具体 FK |
| R-04 | P0 | ClaimVersion 与 EvidenceRelation 的冻结时机未定义，可能在 Claim 冻结后偷偷追加支持证据 | 增加 Draft→Frozen 规则；ClaimVersion freeze 后 EvidenceRelation 集合锁定 |
| R-05 | P1 | Phase 1 “15–20 表”与实际对象数量矛盾，且遗漏关系表 | 改为 25–30 表，并补 `run_*_inputs`、`statistical_result_inputs` |
| R-06 | P1 | ConfigurationSnapshot / EnvironmentSnapshot 有概念但没有清晰持久化方案 | Phase 1 统一作为 ArtifactVersion role 持久化 |
| R-07 | P1 | Literature、Publication、DecisionRecord 在不同章节有“必须/可选/延后”冲突 | Phase 1 主链不依赖 Publication/Decision；Literature 仅 Optional Extension |
| R-08 | P1 | 版本对象何时可编辑、何时真正 immutable 未定义 | 增加 Version Lifecycle 与 freeze point |
| R-09 | P1 | 缺少事务边界，开发者可能跨 Repository 半成功写入 | 规定一个 Application Command 一个 DB transaction |
| R-10 | P1 | 缺少 Command/Query 契约，中级程序员无法稳定拆服务 | 新增 Phase 1 Application API/CLI 施工契约 |
| R-11 | P1 | Modular Monolith 只写了目录，没有 import/dependency 规则 | 新增模块依赖规则：业务 Domain 不直接 import 其他 Domain ORM/entity implementation |
| R-12 | P1 | Hash、时间、并发更新规则未定义 | 明确 SHA-256、UTC、canonical serialization、optimistic concurrency |
| R-13 | P1 | stale / invalid / corrected 的语义边界不够明确 | 增加 validity projection 规则：事实值不改，状态由 Finding/Impact/Correction 派生 |
| R-14 | P1 | 技术栈只到“Python + relational DB”，不足以统一团队实现 | 增加参考实现 Profile：PostgreSQL + SQLAlchemy/Alembic + Pydantic + FastAPI/Typer + pytest |
| R-15 | P1 | 缺少数据库约束、删除策略和关键索引要求 | 增加 FK/UNIQUE/RESTRICT/索引基线 |
| R-16 | P1 | Phase 1A–1F 仍偏大，难以多人并行施工 | 增加 Work Package、接口所有权与合并 Gate |

**规范优先级：本文正文（含 Agentic Research OS 架构补全与 Phase 1 施工规范）为当前实施基线；附录 A/B/C 作为 Phase 0 历史冻结记录用于追溯。若附录与正文修订项冲突，以正文为准。**


## 0.1 v1.2 架构补全说明

v1.1 已经把 ResearchBase Core 修订到可以施工，但 Agent 仍主要被描述为 Actor/Authority 概念。v1.2 补充 **Agentic Scientific Research OS** 上层架构，明确 STORM/Co-STORM、PaperQA2、EvoScientist、AI Scientist-v2、Agent Laboratory、DeerFlow、OpenHands/Codex 等参考系统的定位、复用方式和 Phase Roadmap。

此次补全的核心不是把第三方项目“塞进系统”，而是定义：

```text
Reference System
→ Strategy / Capability Adapter
→ Agent Runtime
→ ResearchBase Application Command
→ Canonical Scientific State
```

因此 **Phase 1 Provenance Core 不推翻、不扩张为 Agent framework**；它只是被明确为未来所有 Human/Agent 科研行为的可信状态底座。

---

# 第一部分：系统定位与设计目标

## 1. ResearchBase 是什么

ResearchBase 是一个面向科学研究过程的 **科研 provenance、证据追踪、实验版本管理和科学结论可审计底座**。

它的首要目标不是最大化自动化，而是确保任何正式科研结果都能够回答：

1. 这个结论来自哪个 Hypothesis？
2. 对应哪个 ExperimentSpec？
3. 实际执行的是哪个 Run？
4. Run 使用的确切 Dataset 状态是什么？
5. 使用的代码、模型、配置和环境是哪一个版本？
6. Measurement 与 StatisticalResult 如何产生？
7. 哪些 Evidence 支持或反驳了 Claim？
8. Claim 在论文的哪个版本中被使用？
9. 如果上游数据、代码或统计结果后来被证明有问题，会影响哪些下游 Claim、Figure、Manuscript 和 Submission？
10. Human、Agent、Reviewer、Approver 分别做过什么，其行为是否在权限范围内？

因此，ResearchBase 的核心价值不是“AI 自动帮用户写完论文”，而是：

> **无论 Human、Agent、脚本或外部工具完成了多少科研工作，系统始终能够精确重建每一个科学断言是如何产生的。**

## 2. 系统不是什么

ResearchBase 在 Phase 1 明确不是：

- 完整论文编辑器；
- 自动投稿平台；
- 科研行政 OA 系统；
- IRB/HIPAA/GDPR 管理平台；
- 财务 ERP；
- 采购/报销系统；
- 完整 IAM/RBAC 产品；
- 全功能文献管理器；
- 自动取代 Human Reviewer 的系统；
- 微服务集群；
- 全量 CQRS/Event Sourcing 平台。

这些能力可以在未来通过扩展 Domain 或 Connector 接入，但不得反向污染科研 provenance 核心。

## 3. Phase 0 顶层设计原则

### 3.1 Deterministic Fact > Authority

确定性 canonical fact 的优先级高于 Review、Decision、Approval。

例如 canonical Measurement 为 `0.913`，论文写成 `0.931`，即使 PI 或 P4 Approver 点击通过，`0.931` 仍然是错误事实。

Authority 可以决定“允许做什么”，不能决定“现实是什么”。

### 3.2 One Canonical Source of Truth

每一个 canonical fact 必须且只能有一个 owning Domain。

其他 Domain 可以引用、查询、索引、缓存和投影，但不得建立第二套 Source of Truth。

### 3.3 Formal History Is Immutable

Run、Measurement、StatisticalResult、DecisionRecord、ApprovalDecision、ReviewRecord、SubmissionVersion 等正式历史对象不得原位改写。

修正使用：

- 新 Version；
- 新 Record；
- `CorrectionRecord`；
- `ImpactAssessment`；
- supersession / invalidation relation。

### 3.4 Formal Provenance Defaults to FrozenReference

凡是回答“当时基于什么”的关系，默认使用 `FrozenReference<T>`。

只有“现在这个长期对象当前是什么状态”的导航关系才使用 `LiveReference<T>`。

### 3.5 Frozen Provenance Closure

任何正式 Run、Claim、Decision、Approval、Submission 或 Released Scientific Package，其 material dependency graph 向下展开后，不允许出现未解析的 `latest/current`。

### 3.6 Governance Semantics Separation

五种治理概念永久分离：

```text
Review         = evaluate
Decision       = choose
Approval       = authorize
Command        = request execution
ExternalEffect = what actually changed externally
```

### 3.7 Human 与 Agent 共用同一 Research Model

系统不为 Agent 建一套平行科研对象。

Agent 与 Human 使用相同的 Project、Experiment、Evidence、Claim、Review、Decision 等对象；差异由 Authority、Accountability、Policy 和 Provenance 决定。

---

# 第二部分：总体架构

## 4. 架构形态

Phase 1 采用：

```text
Python
+
typed domain models
+
relational database
+
modular monolith
+
CLI/API first
+
append-only audit records where required
```

不采用微服务，不采用完整 Event Sourcing。

## 5. 模块结构

```text
researchbase/
├── foundation/
├── identity/
├── organization/
├── research/
├── experiment/
├── evidence/
├── literature/
├── publication/
├── governance/
├── compliance/
├── resources/
├── application/
└── persistence/
```

其中 `foundation` 是基础设施模块，其余为业务 Domain。

## 6. Domain 职责

### 6.1 foundation

拥有跨 Domain 的基础类型：

- UUIDv7
- Instant
- ContentHash
- StructuredValue
- Unit
- Money
- TemporalInterval
- SchemaVersion
- FrozenReference<T>
- LiveReference<T>
- ExternalReference

硬规则：`foundation` 不得 import 任何业务 Domain。

### 6.2 identity

回答“Actor 是谁”。

核心对象：

- ActorIdentity
- HumanActor / AgentActor / ServiceActor / ExternalActor classification
- ActorIdentifier
- AgentVersion
- AgentExecutionInstance
- AuthenticationContext

Identity 不回答“这个 Actor 是否有 P4 权限”。

### 6.3 organization

回答“Actor 属于哪里、项目边界在哪里、谁负责什么”。

核心对象：

- Organization
- Project
- Workspace
- Team
- Membership
- ResponsibilityAssignment
- OwnershipAssignment

Project 是治理 Scope，不是用于级联删除所有科研对象的父容器。

### 6.4 research

回答“研究什么、假设什么、最终主张什么”。

核心对象：

- ResearchQuestion / ResearchQuestionVersion
- Hypothesis / HypothesisVersion
- Claim / ClaimVersion
- ScientificConclusion / ScientificConclusionVersion

Hypothesis、Claim、ScientificConclusion 永久分离。

### 6.5 experiment

回答“计划怎么做”和“实际上做了什么”。

核心对象：

- ExperimentSpec / ExperimentSpecVersion
- Run
- configuration / environment provenance represented by `ArtifactVersion` roles (`configuration`, `environment_manifest`) logical concepts (Phase 1 persisted as typed ArtifactVersion roles)

不建立独立 `WorkflowRun` Canonical Entity；使用 `Run.run_type` 与 parent/child run relation。

### 6.6 evidence

回答“有什么数据、产物、Measurement 和 Statistical Evidence”。

核心对象：

- Dataset / DatasetVersion
- DatasetSnapshot
- Artifact / ArtifactVersion
- MetricDefinition / MetricDefinitionVersion
- Measurement
- StatisticalResult
- EvidenceRelation

Evidence 不拥有 Publication 生命周期。

### 6.7 literature

严格限定为文献与 prior-art，不使用宽泛的 `knowledge` Domain。

核心对象：

- LiteratureSource
- SourceVersion
- Citation relations
- PriorArtRelation
- NoveltyAssessment

### 6.8 publication

负责稿件和发表生命周期：

- Publication
- ManuscriptVersion
- SubmissionVersion
- AuthorshipSnapshot
- VenueReviewRecord
- CameraReady
- PublishedVersion

External venue review 与 Internal ResearchBase review 分离。

### 6.9 governance

横切治理 Domain：

- DecisionRecord
- ApprovalRequest
- ApprovalDecision
- ApprovalGrant
- InternalReviewRecord
- AuditFinding
- Incident
- ImpactAssessment
- Appeal
- Authority / Delegation / COI assessment

治理对象可以引用任意被治理对象，但科学 Domain 不以 Governance projection 作为 scientific truth。

### 6.10 compliance

只保留科研底座所需的最小合规边界：

- Policy / PolicyVersion
- DataZone
- EthicsProtocolVersion
- ExternalEthicsApproval
- ConsentRecord
- ProtocolDeviation

### 6.11 resources

只管理科研资源 provenance：

- Grant
- ResourcePool
- ResourceRequest
- ResourceReservation
- ResourceUsage
- CostRecord

不建设财务 ERP。

---

# 第三部分：Canonical Object Model

## 7. 四类对象

### 7.1 Long-lived Identity Entity

具有长期稳定 ID，当前状态可以演进：

- Project
- Workspace
- Organization
- ActorIdentity
- Dataset
- Artifact
- LiteratureSource
- Publication
- Grant
- ResourcePool

### 7.2 Version Identity

表示明确的业务/科学语义版本：

- ResearchQuestionVersion
- HypothesisVersion
- ClaimVersion
- ScientificConclusionVersion
- ExperimentSpecVersion
- DatasetVersion
- ArtifactVersion
- MetricDefinitionVersion
- SourceVersion
- ManuscriptVersion
- SubmissionVersion
- PolicyVersion
- AgentVersion

一旦 Frozen，不允许原位改变 material semantics。

### 7.3 Immutable Record

表示已经发生的事实或判断。`Run` 是特殊项：其执行生命周期在终态前可迁移，但输入在 RUNNING 前 seal，达到终态后 material provenance 视为 immutable：

- Run（stateful-until-terminal；terminal material state immutable）
- DatasetSnapshot
- Measurement
- StatisticalResult
- DecisionRecord
- ApprovalRequest
- ApprovalDecision
- ReviewRecord
- ImpactAssessment
- AuthorConsent

这些对象不建立 `RunVersion`、`MeasurementVersion`、`DecisionVersion` 等二次版本体系。

### 7.4 Stateful Relation / Governance Object

具有真实生命周期：

- Membership
- RoleAssignment
- ResponsibilityAssignment
- OwnershipAssignment
- Incident
- ApprovalGrant
- ResourceReservation

历史状态必须通过时态或事件保留。

## 8. 明确删除或合并的概念

为降低复杂度，Phase 0 已正式删除或收缩：

```text
WorkflowRun              → Run(run_type + parent/child)
LiteratureRecord         → LiteratureSource + SourceVersion
generic PublicationVersion → ManuscriptVersion / SubmissionVersion / PublishedVersion
DataZoneVersion          → stable DataZone + PolicyVersion（默认）
RunVersion               → 禁止
MeasurementVersion       → 禁止
StatisticalResultVersion → 禁止
DecisionVersion          → 禁止
ApprovalDecisionVersion  → 禁止
ReviewRecordVersion      → 禁止
```

---

# 第四部分：Reference 与 Provenance

## 9. FrozenReference<T>

语义：引用“当时那个确定状态”。

典型使用：

```text
Run → ExperimentSpecVersion
Run → DatasetSnapshot
Run → ArtifactVersion
Measurement → Run
ClaimVersion → Evidence
DecisionRecord → DecisionBasis
ApprovalDecision → Frozen Target
SubmissionVersion → ManuscriptVersion
Citation → SourceVersion
```

## 10. LiveReference<T>

语义：导航到长期对象当前状态。

典型使用：

```text
Project → current Workspace
Publication → current ManuscriptVersion
Artifact → current ArtifactVersion
Dataset → current DatasetVersion
AgentActor → current AgentVersion
```

LiveReference 不用于正式历史 provenance。

## 11. ExternalReference

用于 DOI、ORCID、GitHub URL、外部 Dataset URL 等软引用。

外部资源可能消失，因此不使用数据库硬 FK 模拟其存在性。

## 12. Frozen Provenance Closure

正式 Snapshot 的依赖图必须可完全解析至 immutable/versioned dependencies。

例如 SubmissionVersion：

```text
SubmissionVersion
  → ManuscriptVersion
  → ClaimVersion
  → EvidenceRelation
  → StatisticalResult / Measurement
  → Run
  → DatasetSnapshot
  → ArtifactVersion
  → ExperimentSpecVersion
```

这条链中不得出现 `current/latest`。

---

# 第五部分：端到端科研主链

## 13. 正常科研链

```text
ResearchQuestionVersion
        ↓
HypothesisVersion
        ↓
ExperimentSpecVersion
        ↓
Run
   ┌────┼───────────┐
   ↓    ↓           ↓
DatasetSnapshot  ArtifactVersion
        ↓
    Measurement
        ↓
 StatisticalResult
        ↓
 EvidenceRelation
        ↓
   ClaimVersion
        ↓
ScientificConclusionVersion   [按需]
        ↓
 ManuscriptVersion
        ↓
 SubmissionVersion            [Phase 2]
```

系统最核心的验收标准：

> 从任何 Formal Claim 必须能够反向追踪到 Run；从 Run 必须能够追踪到确定的数据、代码/Artifact、配置和实验定义。

## 14. ExperimentSpec 与 Run

```text
ExperimentSpec = what should be done
Run            = what actually happened
```

重新执行实验必须创建新 Run；不得创建 RunVersion。

## 15. Dataset / DatasetSnapshot

Dataset 是长期身份；DatasetVersion 表示逻辑版本。为了降低实现分支，**Phase 1 规定每个使用 Dataset 的 Run 都必须绑定 DatasetSnapshot**。Snapshot 可以只是 manifest/hash/selection rule 的轻量冻结记录，不要求复制原始数据。

因此正式 Run 绝不能只引用 `Dataset.current` 或仅依赖可变 DatasetVersion。未来若证明 content-addressed DatasetVersion 已能完全替代 Snapshot，可通过架构变更简化。

## 16. MetricDefinition / Measurement

Measurement 必须绑定确切 MetricDefinitionVersion。

若 Macro-F1 的 averaging、ignored labels、NaN handling 等变化，则创建新的 MetricDefinitionVersion。

旧 Measurement 不随 MetricDefinition 更新而变化。

## 17. StatisticalResult

StatisticalResult 是 immutable record。

统计方法改变、实现修复或分析计划改变后，生成新的 StatisticalResult，而不是覆盖旧记录。

## 18. EvidenceRelation

EvidenceRelation 建立 Evidence 与 Claim 的关系，避免 Evidence 本身知道“最终在哪篇论文使用”。

支持：

- supports
- contradicts
- qualifies
- boundary-condition
- uncertain

具体关系由 Schema Registry 约束。

---

# 第六部分：错误、审计与影响传播

## 19. 上游错误链

```text
Dataset leakage / code bug / statistical error
→ AuditFinding
→ ImpactAssessment
→ affected Run / Measurement / StatisticalResult
→ Evidence stale / invalid
→ Claim stale
→ ScientificConclusion affected
→ Manuscript / Submission impact
```

核心原则：

> 上游事实出错后，不允许通过修改论文文字、P4 Approval 或删除历史记录截断影响传播。

## 20. CorrectionRecord

Immutable scientific history 记录错误时，不通过普通 UPDATE 修改。

使用：

```text
CorrectionRecord
→ target_ref
→ prior assertion
→ corrected assertion
→ reason
→ basis
```

Current projection 可以显示修正后状态，但历史原记录仍然存在。

## 21. AuditFinding 与 Incident

二者分离：

```text
AuditFinding = 检查发现的问题
Incident     = 已经发生、需要治理响应的事件
```

AuditFinding 可升级为 Incident，但不能直接修改 canonical fact。

---

# 第七部分：Governance 与 Authority

## 22. Governance 主链

```text
Evidence / Facts
      ↓
Review / Audit
      ↓
Findings
      ↓
Impact / Assessment
      ↓
DecisionRecord
      ↓
Internal change OR Governed action
                     ↓
              ApprovalRequest
                     ↓
              ApprovalDecision
                     ↓
               ApprovalGrant
                     ↓
                  Command
                     ↓
              ExternalEffect
```

## 23. Review / Decision / Approval / Command / ExternalEffect

永久语义分离：

- Review：评价；
- Decision：选择；
- Approval：授权；
- Command：执行意图；
- ExternalEffect：外部世界实际发生的变化。

## 24. P0–P4

P0–P4 只作为 Policy Taxonomy，不实现为简单整数权限梯子。

真正权限检查依赖：

```text
AuthorityDomain
+
AuthorityRequirement
+
Role / Assignment
+
Scope
+
Policy
+
Authentication / Identity assurance
```

P3 ExternalAction 与 P4 ScientificRelease 是不同 Authority Dimension。

## 25. Multi-Authority AND Rule

如果一个动作同时受多个独立 Authority Domain 约束，必须全部满足。

例如公开敏感 Dataset 可能同时要求：

- Data Owner permission；
- Ethics approval；
- Legal/Policy requirement；
- Project P3 approval。

不能通过“存在一个更高等级的批准”覆盖其他 Authority。

## 26. Agent Authority

Agent 可以：

- 搜索；
- 分析；
- 起草；
- 执行已治理任务；
- 审计；
- 推荐。

Agent 默认不能：

- P4 self-approve；
- 通过 acting_on_behalf_of 继承 Human 的全部 Authority；
- 自己给自己 Delegation；
- approval-shop；
- 改写 deterministic facts；
- 清洗自己的 provenance。

Human 批准 Agent 输出，也不能删除 Agent 的原始贡献 provenance。

---

# 第八部分：Identity、Organization 与 Authorship 边界

## 27. Identity / Role / Authority / Credential 分离

```text
Identity       = who
Identifier     = how identified
Role           = in what capacity
Authority      = what may be authorized
Credential     = how identity is authenticated
Authentication = whether session is really that actor
```

这些概念不得合并。

## 28. AgentActor / ServiceActor 分离

```text
Human requester
→ AgentActor
→ AgentExecutionInstance
→ ServiceActor credential
→ ExternalEffect
```

外部 API 只看到 ServiceAccount，不代表 ServiceAccount 是最终行为责任主体。

## 29. Project / Workspace / Team

Project 是治理 Scope；Workspace 是工作空间；Team 是协作分组。

Project 不作为数据库父节点级联删除科研对象。

## 30. Membership / Role / Responsibility / Ownership

四者永久分离。

“负责做某件事”不意味着“有权执行某个 P3 动作”。

## 31. Authorship

Project Membership 不自动产生 Authorship。

作者系统核心链收缩为：

```text
ContributionRecord
→ AuthorshipDecision
→ AuthorshipSnapshot
→ AuthorConsent
→ SubmissionVersion
```

Agent contribution 可以完整记录，但默认不进入 Human author list。

CorrespondingAuthor 也不自动等于 P3 Submitter、P4 Approver 或 ScientificAccountable。

---

# 第九部分：Literature、Citation 与 Novelty

## 32. Literature identity

```text
LiteratureSource
→ SourceVersion
```

arXiv、conference、journal、corrected version 必须保留 version lineage。

标题相似不是自动 merge 的充分条件。

## 33. Citation 与 ClaimSupport 分离

```text
Citation ≠ ClaimSupport
```

句末 `[12]` 不自动支持整句话中的所有 Claim。

正式证据关系应尽可能绑定具体 EvidenceSpan / SourceVersion。

## 34. Novelty

Novelty Search 必须保留：

- SearchPlan；
- SearchQuery / SearchRun；
- Screening；
- PriorArtRelation；
- SearchCoverage；
- negative novelty probe。

“没搜到”永远不等于“此前不存在”。

Priority/first claim 的强度不得超过 SearchCoverage。

Phase 1 只实现 LiteratureSource / SourceVersion 基础 identity；完整 Novelty/Citation governance 延后。

---

# 第十部分：Publication 生命周期

## 35. Publication / ManuscriptVersion / SubmissionVersion

```text
Publication = 长期发表工作 identity
ManuscriptVersion = 某个具体稿件版本
SubmissionVersion = 实际送出的冻结包
```

返修不能覆盖初次投稿历史。

## 36. SubmissionVersion

必须冻结：

- ManuscriptVersion；
- Figure/Table versions；
- Claim versions；
- Citation state；
- AuthorshipSnapshot；
- scientific conclusions。

这是系统中最严格的 frozen snapshot 之一。

## 37. Reviewer feedback

External ReviewerComment 不是 ScientificTruth。

链路：

```text
ReviewerComment
→ ReviewIssue
→ Decision / Resolution
→ RevisionAction
→ new canonical objects
→ AuthorResponse
```

AuthorResponse 不能代替真正的 Experiment、Claim 或 Manuscript 修改。

## 38. Acceptance

```text
Venue Acceptance ≠ ScientificValidity
Rejection         ≠ ScientificInvalidity
```

CameraReady 不得成为 post-acceptance scientific bypass。

---

# 第十一部分：Compliance 与 Resource 边界

## 39. Ethics / Consent

本系统只保留最低必要治理能力：

```text
EthicsProtocolVersion
ExternalEthicsApproval
ConsentRecord
ProtocolDeviation
```

硬规则：

```text
DataAccess ≠ EthicalPermission
PI/P4 ≠ IRB / ExternalEthicsAuthority
Deidentification ≠ unrestricted reuse
ConsentWithdrawal ≠ automatic historical deletion
```

## 40. Resource / Funding

Resource 系统只用于科研 provenance，不建设 ERP。

核心语义：

```text
Funding ≠ ScientificAuthority
Budget ≠ Evidence
Reservation ≠ Run
ExpenseApproval ≠ ScientificApproval
Cost ≠ ScientificValidity
```

资源不足可以影响“是否重跑”，但不能让已经 invalid 的结果继续变 valid。

---

# 第十二部分：Phase 1 MVP

## 41. Phase 1 六个用户能力

Phase 1 只交付：

1. Project workspace；
2. ResearchQuestion / Hypothesis registry；
3. ExperimentSpec + Run tracking；
4. Dataset / Artifact provenance；
5. Measurement / StatisticalResult / Evidence registry；
6. Claim traceability + basic audit。

目标用户链：

```text
提出 Hypothesis
↓
定义 ExperimentSpec
↓
执行/登记 Run
↓
冻结 Dataset / Code / Config provenance
↓
产生 Measurement / StatisticalResult
↓
形成 Evidence
↓
建立 Claim
↓
反查完整证据链
```

## 42. Phase 1 必须实现的核心 Domain

- foundation
- identity（最小）
- organization/project（最小）
- research
- experiment
- evidence
- governance（AuditFinding / ImpactAssessment / CorrectionRecord 基础）

Phase 1 可选扩展（不得阻塞主链验收）：

- literature（仅 LiteratureSource / SourceVersion identity）；

Phase 2 再进入 publication、Decision/Approval/Review 等正式治理与发表生命周期。

## 43. Phase 1 延后实现

Phase 2 Candidate：

- SubmissionVersion
- ScientificConclusion full workflow
- InternalReviewRecord
- ApprovalRequest / ApprovalDecision / ApprovalGrant
- RoleAssignment / Membership / Responsibility
- CitationContext / CitationAudit
- NoveltyAssessment
- AuthorshipSnapshot / AuthorConsent
- Incident

## 44. Deferred / Interface-only

- 完整 P0–P4 Authority Engine；
- Delegation Engine；
- Appeal；
- COI workflow；
- Funding/Budget/Cost allocation；
- Ethics workflow；
- Venue submission automation；
- ExternalEffect connectors；
- 完整 RACI；
- 复杂 Organization hierarchy；
- Financial disclosure；
- 高级 Authorship dispute。

---

# 第十三部分：Phase 1 工程方案

## 45. 实现顺序

### Phase 1A — Foundation and persistence skeleton

建立：

- typed references；
- UUID/Hash/SchemaVersion；
- relational persistence；
- base repository/service boundaries；
- append-only audit support。

### Phase 1B — Research and experiment version semantics

实现：

- ResearchQuestionVersion；
- HypothesisVersion；
- ExperimentSpecVersion；
- Run lifecycle + input sealing + terminal immutability。

### Phase 1C — Dataset / Artifact provenance

实现：

- Dataset/DatasetSnapshot；
- Artifact/ArtifactVersion；
- Frozen references in Run。

### Phase 1D — Measurement and evidence

实现：

- MetricDefinitionVersion；
- Measurement；
- StatisticalResult；
- EvidenceRelation；
- ClaimVersion。

### Phase 1E — Basic audit and impact propagation

实现：

- AuditFinding；
- ImpactAssessment；
- CorrectionRecord；
- basic stale/invalid propagation；
- deterministic integrity rules。

### Phase 1F — End-to-end provenance demo

必须演示完整链：

```text
Hypothesis → ExperimentSpec → Run → Measurement → Evidence → Claim
```

并演示上游变更/错误不会污染历史 Run 和 Claim provenance。

## 46. 数据库规模与 Phase 1 参考关系模型

原设计“15–20 张核心表”的估算偏低，且漏掉 Run 多输入、StatisticalResult 多 Measurement 输入等必要关系表。为避免中级程序员自行发明不兼容的关系模型，Phase 1 施工基线调整为 **约 25–30 张核心/关系表**。表数量本身不是优化目标，语义边界和外键完整性优先。

推荐基线：

```text
actors
projects
workspaces

research_questions
research_question_versions
hypotheses
hypothesis_versions
claims
claim_versions

experiment_specs
experiment_spec_versions
runs

datasets
dataset_snapshots
artifacts
artifact_versions
run_dataset_inputs
run_artifact_inputs

metric_definitions
metric_definition_versions
measurements
statistical_results
statistical_result_inputs
evidence_relations

audit_findings
impact_assessments
correction_records
```

可选 Literature 扩展再增加：

```text
literature_sources
source_versions
```

核心科研 provenance 边必须使用具体 FK；不得为了“通用”把 `Run → DatasetSnapshot`、`Run → ArtifactVersion`、`Measurement → MetricDefinitionVersion` 等主链改成 `target_type + target_id` 的软多态引用。通用软引用只允许用于 Audit/Impact 等横切治理对象，并必须经过应用层 reference validator。

---

# 第十四部分：Phase 1 强制测试

## 47. Frozen Reference Test

修改 Dataset/Artifact/ExperimentSpec 的 current version 后，历史 Run 的 dependency 必须保持不变。

## 48. Dataset Contamination Test

Dataset 更新后，历史 Measurement 不得自动解释为基于新 Dataset。

## 49. Artifact Contamination Test

代码或配置 Artifact 更新后，历史 Run 不得跟随 latest。

## 50. No RunVersion Test

重新执行实验必须产生新 Run，禁止修改旧 Run 为“第二版”。

## 51. Measurement Immutability Test

Measurement 计算修复后必须创建新 Measurement/Correction provenance，禁止普通 UPDATE 覆盖历史科学事实。

## 52. Frozen Provenance Closure Test

Formal Claim/Run 的 material dependency graph 中不得存在 unresolved LiveReference/current/latest。

## 53. One Source of Truth Test

Project、Claim、Dataset、Publication 等不得同时维护相互矛盾的双向 canonical 集合。

## 54. Fact Precedence Test

治理状态不得把 deterministic mismatch 标成科学有效。

---

# 第十五部分：架构复杂度预算

## 55. 新 Schema 准入规则

任何新的 Canonical Schema 必须证明：

> 现有 Entity + Relation + Assessment + Snapshot + Event 无法清晰表达该概念。

否则默认：

```text
DO NOT ADD SCHEMA
```

## 56. 禁止万能抽象

禁止：

```text
Object(id, type, json_payload)
```

作为整个系统的唯一持久化模型。

也禁止把所有业务语义塞进 `metadata JSON`。

允许 `StructuredValue` 承载扩展信息，但核心 provenance 必须 typed。

## 57. Derived View 不是 Source of Truth

例如：

- current claim status；
- current authority profile；
- remaining budget；
- latest manuscript；
- dashboard metrics。

这些应由 canonical records 重新计算。

---

# 第十六部分：Phase 0 / Phase 1 Gate

## 58. Phase 0 当前状态

```text
D1-02 Schema Design              CLOSED
D1-03 Architecture Closure       CLOSED
Architecture                     FROZEN FOR REVIEW
Implementation Plan              FROZEN FOR REVIEW
Schema Registry                  FROZEN FOR REVIEW
Phase 1 Code                     NOT STARTED
Database Migration               NOT STARTED
Agent Workflow                   NOT STARTED
```

## 59. Phase 0 STOP Gate

在用户明确给出 **Phase 1 GO** 之前：

- 不创建 Phase 1 业务代码；
- 不运行数据库迁移；
- 不实现 Agent workflow；
- 不开始外部投稿/审批 Connector；
- 不擅自扩展 Canonical Schema。

## 60. Phase 1 GO 前验收清单

必须确认：

- Domain boundary 无重大歧义；
- Canonical Object ownership 明确；
- FrozenReference/LiveReference 规则明确；
- Immutable/Version semantics 明确；
- Phase 1 scope 已严格削减；
- Non-goals 清楚；
- 强制架构测试已写入实施计划；
- Codex 不会从 Phase 0 直接扩展到行政/治理大系统。

---

# 第十七部分：最终架构冻结决议

ResearchBase Phase 0 最终冻结如下：

1. 系统采用 `foundation + 10 business domains` 的 modular monolith。
2. Canonical Entity 总量严格受 Architecture Complexity Budget 约束。
3. 对象分为 Long-lived Identity、Version Identity、Immutable Record、Stateful Relation 四类。
4. FrozenReference / LiveReference / ExternalReference 成为统一引用体系。
5. Formal provenance 必须满足 Frozen Provenance Closure。
6. 每个 canonical fact 只能有一个 owning Domain。
7. `ExperimentSpec ≠ Run`。
8. `Hypothesis ≠ Claim`。
9. `Claim ≠ ScientificConclusion`。
10. `Review ≠ Decision ≠ Approval ≠ Command ≠ ExternalEffect`。
11. Run / Measurement / StatisticalResult / Decision 等历史事实采用 immutable semantics。
12. 修正不能通过普通 UPDATE 篡改科学历史。
13. Dataset / Artifact 独立于 Project 与 Publication 生命周期。
14. Project archive 不级联删除科研证据。
15. Deterministic Fact > Authority。
16. P0–P4 只是 Policy Taxonomy，不是 scalar superuser ladder。
17. 多 Authority Domain 使用 AND constraints。
18. Agent 与 Human 使用同一 canonical research model。
19. Agent 默认不得 P4 self-approval。
20. Human approval 不得清洗 Agent provenance。
21. Phase 1 只实现科研 provenance 核心链。
22. Phase 1 不建设科研行政管理平台。
23. Phase 1 使用 relational DB + modular monolith + CLI/API first。
24. Immutable semantics、FrozenReference、Provenance Graph、Deterministic Auditability 是四个最高工程优先级。
25. 新 Schema 默认拒绝，除非现有抽象无法合理表达。

---


# 第十八部分：Agentic Scientific Research OS 架构与开源能力复用策略（Normative）

本部分补全 ResearchBase 上层“科研 Agent 操作系统”架构。此前正文已经定义 Human/Agent 共用 Canonical Research Model、Agent Authority 与 Provenance 边界，但尚未回答以下施工级问题：

1. ResearchBase 为什么要接入 STORM、Co-STORM、PaperQA2、EvoScientist、AI Scientist-v2、Agent Laboratory、DeerFlow、OpenHands/Codex 等能力；
2. 哪些能力直接复用，哪些只借鉴方法，哪些明确不作为系统依赖；
3. Agent 如何读取/写入 ResearchBase，而不是形成第二套科研状态；
4. 文献调研、假设演化、实验设计、代码执行、分析、写作、审稿如何组成统一 Research OS；
5. Phase 1 的 provenance core 与 Phase 2/3 Agent Runtime 如何衔接。

本部分不改变 Phase 1 Core 的字段级施工规范，而是定义其上层目标架构和后续阶段接口。

## 81. 顶层产品定位：ResearchBase = Research OS，而不只是 Provenance Database

ResearchBase 最终目标应理解为：

> **一个以 Canonical Scientific State 和可验证 Provenance 为核心、能够接入多种科研 Agent、Coding Agent、文献检索系统和实验平台的组合式 Research OS。**

整体分为五层：

```text
┌─────────────────────────────────────────────────────────────────┐
│ Layer 4  Human / Research Interaction                           │
│         Research Cockpit · Discussion Room · Review Console     │
├─────────────────────────────────────────────────────────────────┤
│ Layer 3  Scientific Agent Runtime                               │
│         Research · Hypothesis · Experiment · Analysis · Review  │
├─────────────────────────────────────────────────────────────────┤
│ Layer 2  Capability / Strategy Adapters                         │
│         STORM · PaperQA2 · EvoScientist · AI Scientist-v2       │
│         Agent Laboratory · DeerFlow · OpenHands/Codex · Tools   │
├─────────────────────────────────────────────────────────────────┤
│ Layer 1  ResearchBase Core                                      │
│         Research · Experiment · Evidence · Claim · Provenance    │
│         Version · Audit · Governance                            │
├─────────────────────────────────────────────────────────────────┤
│ Layer 0  Infrastructure                                         │
│         PostgreSQL · Git · Artifact Store · Compute · Sandbox   │
└─────────────────────────────────────────────────────────────────┘
```

核心约束：

```text
External Research Systems provide capabilities.
ResearchBase owns scientific state.
```

第三方 Agent 系统可以生成候选内容、执行任务或提供研究方法，但不得成为 Hypothesis、Run、Measurement、Claim 等 canonical scientific truth 的唯一保存位置。

---

## 82. Reference System 不等于 Dependency

系统正式区分四种复用关系：

```text
METHOD_REFERENCE
    借鉴算法、工作流或交互机制，不运行其代码。

LIBRARY_ADAPTER
    在 ResearchBase 进程/worker 中通过稳定 Python/API interface 调用。

SERVICE_ADAPTER
    把外部系统作为独立进程、容器或远程服务调用。

FORKED_COMPONENT
    将第三方代码 fork 后作为 ResearchBase 维护组件。
```

默认策略：

> **优先 METHOD_REFERENCE / ADAPTER，慎用 FORKED_COMPONENT。**

原因：

- 开源项目会快速变化；
- License、模型、依赖和 Agent framework 可能改变；
- ResearchBase 必须保持核心资产主权；
- 第三方内部 state/schema 不应成为 ResearchBase 的 canonical schema；
- 单个开源 Agent 的失败不应破坏科研历史可追溯性。

任何将 Reference System 升级为硬 Dependency/Fork 的决定都必须经过 ADR。

---

## 83. Reference Systems Registry

截至 2026-08-26，建议维护以下正式 Reference Systems Registry。该 Registry 是架构参考清单，不意味着 Phase 1 全部安装。

| Reference System | 主要能力 | ResearchBase 借鉴/复用点 | 默认 Integration Mode | 目标层/模块 | Canonical 输出 |
|---|---|---|---|---|---|
| Stanford STORM | 多视角提问、检索、知识策展、带引用长报告 | Perspective-guided question asking、模拟专家对话、研究前结构化 | METHOD_REFERENCE，后续可 LIBRARY_ADAPTER | Research Agent / Literature Strategy | SourceVersion、LiteratureEvidence、ResearchBrief Artifact |
| Co-STORM | Human-AI 协同讨论、Moderator、动态 mind map | Academic Discussion Room、human steering、shared concept map | METHOD_REFERENCE | Research Discussion Runtime | Discussion Artifact、ResearchQuestion/Claim candidate |
| PaperQA2 | 科学文献 agentic RAG、证据检索、引用、矛盾检测 | 高精度 local-corpus scientific evidence retrieval | LIBRARY_ADAPTER / SERVICE_ADAPTER | Literature Evidence Capability | SourceVersion、Citation/Evidence candidate |
| EvoScientist | plan/research/code/debug/analyze/write 多 Agent、persistent memory、科学工作流 | Multi-agent role decomposition、research lifecycle orchestration、skill/tool extensibility | METHOD_REFERENCE；Phase 3 可 SERVICE_ADAPTER prototype | Scientific Agent Runtime | Candidate plans、ExperimentSpec/Claim candidates、AgentExecution provenance |
| AI Scientist v1 | idea→experiment→paper→review 端到端自动科研 | End-to-end lifecycle reference、自动实验闭环边界 | METHOD_REFERENCE | Autonomous Research Strategy | Candidate Hypothesis/Experiment workflow |
| AI Scientist-v2 | Experiment Manager、progressive agentic tree search、开放式实验搜索 | Hypothesis/Experiment search tree、branch evaluation、experiment-manager pattern | METHOD_REFERENCE；可实现 native Strategy | Hypothesis/Experiment Strategy | HypothesisVersion candidate、ExperimentSpecVersion candidate |
| Agent Laboratory | literature→experimentation→report、human researcher feedback | Human checkpoints、阶段式 research assistant workflow | METHOD_REFERENCE | Human-guided Orchestration Strategy | ResearchPlan、Experiment candidate、Report Artifact |
| DeerFlow 2.x | subagents、memory、sandbox、skills、MCP、agent harness | Agent harness、sandbox/tool middleware、skills/MCP integration | METHOD_REFERENCE；可评估 SERVICE_ADAPTER | Agent Runtime Infrastructure | CapabilityInvocation / AgentExecution records |
| OpenHands | 软件开发 Agent、代码修改、命令执行、sandbox/runtime | Coding Agent execution、repo workspace、command execution isolation | SERVICE_ADAPTER / optional SDK adapter | Coding Capability | ArtifactVersion、Execution log、candidate patch |
| Codex / Coding Agent | 代码理解、修改、测试、仓库级开发任务 | Experiment code generation、debug、reproduction、PR implementation | CAPABILITY_ADAPTER | Coding Capability | ArtifactVersion、Run preparation provenance |
| Git + DVC | 代码/数据资产版本 | 外部资产 locator/version integration | INFRA_ADAPTER | Artifact/Data Infrastructure | ArtifactVersion / DatasetSnapshot |
| MLflow / ClearML | 实验跟踪、metrics、run metadata | Run importer/exporter；不替代 ResearchBase scientific semantics | INFRA_ADAPTER | Experiment Infrastructure | Run/Measurement import candidates |
| LangGraph | 有状态 Agent orchestration | 可作为 Agent Runtime 实现候选，但不进入 Domain Core | IMPLEMENTATION_OPTION | Agent Runtime | 无 canonical scientific state |

Reference Systems Registry 必须包含：

```text
system_id
name
upstream_repository
upstream_version_or_commit
license
integration_mode
capabilities
ResearchBase_owner_module
canonical_output_mapping
status
last_reviewed_at
```

该 Registry 可以先作为 `docs/reference_systems.yaml` / Markdown 管理；Phase 3 若确有需要再实体化，Phase 1 不新增数据库表。

---

## 84. 当前重点 Reference System 的设计解释

### 84.1 STORM / Co-STORM：Research Strategy，而不是“报告生成器直接入库”

STORM 的价值不在于最终 Wikipedia-style article，而在于：

```text
Topic
→ discover perspectives
→ perspective-guided questions
→ source-grounded simulated expert dialogue
→ structured knowledge
→ outline/report
```

ResearchBase 应复用前半段“问题分解 + 多视角 + 有来源的知识策展”。

禁止：

```text
STORM article
→ directly treated as Evidence or ScientificConclusion
```

推荐：

```text
STORMAdapter
    ↓
RetrievedSource[]
    ↓
SourceVersion / ExternalReference
    ↓
EvidenceCandidate[]
    ↓
ResearchBrief ArtifactVersion
    ↓
Human/Agent review
    ↓
ResearchQuestion / Hypothesis candidate
```

Co-STORM 的动态 mind map 应视为 Derived View / Research Artifact，不是 Canonical Knowledge Graph。

### 84.2 PaperQA2：Literature Evidence Capability

PaperQA2 适合作为科学文献的 grounded QA/RAG 能力。

ResearchBase 不保存 PaperQA2 内部向量状态作为 canonical scientific truth。

推荐：

```text
LiteratureQuery
    ↓
PaperQA2Adapter
    ↓
Source candidates + snippets + citations
    ↓
Source resolution / verification
    ↓
SourceVersion
    ↓
LiteratureEvidenceCandidate
```

任何由 LLM summarization 生成的 Evidence 仍需保留：

```text
source_ref
page/section locator if available
retrieval_query
retrieval_time
adapter_version
model_execution provenance
```

### 84.3 EvoScientist：Multi-Agent Runtime Reference

EvoScientist 当前工作流覆盖 plan、research、code、debug、analyze、write 等 specialized agents，并强调 persistent memory、skills 和 end-to-end scientific workflow。

ResearchBase 应借鉴：

- Agent role decomposition；
- Planner 与 worker 分离；
- Code/Debug 分离；
- Data Analysis 独立于 Writing；
- Persistent research memory 的产品体验；
- skills/MCP 式可扩展能力。

但 ResearchBase MUST NOT：

- 把 EvoScientist memory 作为 canonical research history；
- 允许 EvoScientist agent 绕过 Application Commands 直接写数据库；
- 把其“write”输出直接标成 ScientificConclusion；
- 因采用其 orchestration framework 而绑定其全部 dependency tree。

推荐把 EvoScientist 视为：

```text
Reference Agent Harness
        ↓
ResearchBase Capability Gateway
        ↓
Application Command / Query
        ↓
Canonical Core
```

### 84.4 AI Scientist-v2：Experiment Search Strategy

AI Scientist-v2 的 progressive agentic tree search 和 experiment manager 适合启发开放式实验探索。

ResearchBase Native Strategy 应表达：

```text
HypothesisCandidate
        ↓
ExperimentBranch[]
        ↓
ExperimentSpecVersion candidates
        ↓
Run outcomes
        ↓
BranchEvaluation
        ↓
continue / prune / mutate
```

重要边界：

- tree-search node 不等于 Hypothesis canonical identity；
- 只有被提交到 ResearchBase 的候选才形成 DRAFT HypothesisVersion / ExperimentSpecVersion；
- 实际执行仍必须形成 sealed Run；
- branch score 不能覆盖 Measurement/StatisticalResult；
- autonomous search 不能 cherry-pick 后删除失败 branch provenance。

### 84.5 Agent Laboratory：Human-Guided Scientific Workflow

Agent Laboratory 的价值是明确把人类研究者放在 end-to-end workflow 中。

ResearchBase 应借鉴 checkpoint：

```text
Research Intake
→ Literature Review
→ Plan Review
→ Experiment
→ Result Review
→ Report/Claim Review
```

Human checkpoint 是 strategy policy，不应强耦合成所有领域实体的必选字段。

### 84.6 DeerFlow：Agent Harness / Sandbox / Skills Reference

DeerFlow 2.x 更像通用 super-agent harness，而不是科学方法本身。

值得借鉴：

- subagent delegation；
- per-task sandbox；
- skills；
- MCP/tool integration；
- memory middleware；
- agent runtime observability。

不应借鉴为：

```text
DeerFlow thread state = ResearchBase Project state
```

ResearchBase Core 必须独立于 DeerFlow/LangGraph 等 runtime。

### 84.7 OpenHands / Codex：Coding Capability

Coding Agent 是科研 OS 中的重要工具，但不是 Scientist-of-Record。

标准路径：

```text
ExperimentSpecVersion
    ↓
CodingTask
    ↓
OpenHands/Codex Adapter
    ↓
workspace/sandbox
    ↓
patch / code / config / tests
    ↓
ArtifactVersion candidates
    ↓
verification
    ↓
Run
```

Agent 生成的代码必须先成为 ArtifactVersion，之后才能作为 Run input。

禁止：

```text
Agent changed files in-place
→ run immediately
→ no artifact version recorded
```

---

## 85. Scientific Agent Runtime

ResearchBase 上层 Agent Runtime 推荐由以下 logical agents 组成。这里的 Agent 是 runtime role，不要求一个 role 对应一个独立 LLM process。

```text
Orchestrator
├── ResearchAgent
├── LiteratureEvidenceAgent
├── HypothesisAgent
├── ExperimentDesignAgent
├── CodingAgent
├── ExecutionAgent
├── AnalysisAgent
├── Scientist/CriticAgent
├── WritingAgent
└── ReviewerAgent
```

### 85.1 Orchestrator

职责：

- 根据 ResearchTask 调度 Agent；
- 维护 workflow state；
- 选择 Strategy；
- 调用 Application Query 获取 canonical state；
- 发起 candidate Command；
- 管理 human checkpoints；
- 不拥有科学 truth。

### 85.2 ResearchAgent

参考：STORM / Co-STORM。

输入：

```text
ResearchQuestion / topic / constraints
```

输出：

```text
ResearchBrief ArtifactVersion
Source candidates
Perspective map
Open questions
Hypothesis candidates
```

### 85.3 LiteratureEvidenceAgent

参考：PaperQA2 + bibliographic APIs。

输出必须 source-grounded，不得只返回一段无 provenance 的总结。

### 85.4 HypothesisAgent

参考：EvoScientist / AI Scientist-v2。

职责：

- generate；
- mutate；
- compare；
- prioritize；
- identify falsification conditions。

输出默认是 **candidate**。创建 Canonical HypothesisVersion 必须调用 `create_hypothesis/revise_hypothesis`。

### 85.5 ExperimentDesignAgent

将 Hypothesis candidate 转换为 ExperimentSpecVersion candidate。

必须显式考虑：

```text
dataset
split
baseline
metric
seed
statistical plan
compute constraints
failure conditions
```

### 85.6 CodingAgent

参考 OpenHands/Codex。

只能通过受控 Workspace/Sandbox 修改 code artifact，并返回 diff/commit/hash/test result。

### 85.7 ExecutionAgent

职责：

- 根据 FROZEN ExperimentSpecVersion 和 Artifact/Dataset inputs 创建/执行 Run；
- 不修改 ExperimentSpec；
- 对 executor/scheduler/cloud adapter 做 orchestration；
- 将 Run outcome 与 logs 回写 Application layer。

### 85.8 AnalysisAgent

读取 immutable Measurement / StatisticalResult，生成：

```text
analysis summary
plot Artifact
candidate interpretation
```

不得修改原 Measurement。

### 85.9 Scientist/CriticAgent

负责：

- contradiction；
- alternative explanation；
- limitation；
- missing control；
- overclaim detection；
- hypothesis update recommendation。

其输出是 Assessment/Recommendation，不是 deterministic fact。

### 85.10 WritingAgent

从 Claim–Evidence graph 生成 Manuscript candidate。

原则：

> **Write from claims/evidence, not from conversational memory.**

### 85.11 ReviewerAgent

必须与 Authoring Agent execution context 分离。

输入：

```text
Frozen manuscript/claim package
Experiment registry
Evidence graph
Audit findings
```

输出：

```text
ReviewRecord candidate
AuditFinding candidate
```

ReviewerAgent 不直接修改 Manuscript/Claim。

---

## 86. Capability Gateway

所有第三方系统通过统一 Capability Gateway 接入。

```text
Agent Runtime
    ↓
CapabilityGateway
    ├── LiteratureResearchCapability
    ├── ScientificRAGCapability
    ├── CodingCapability
    ├── SandboxExecutionCapability
    ├── ComputeCapability
    ├── StatisticalCapability
    └── WritingCapability
```

推荐 interface：

```python
class CapabilityAdapter(Protocol):
    capability_id: str
    adapter_version: str

    def execute(
        self,
        request: CapabilityRequest,
        context: ExecutionContext,
    ) -> CapabilityResult: ...
```

`CapabilityResult` 必须区分：

```text
candidate_outputs
artifact_outputs
external_refs
execution_metadata
warnings
```

任何 CapabilityResult 都不能直接成为 canonical scientific fact；必须进入对应 Application Command。

---

## 87. Strategy 与 Capability 分离

STORM 主要是一种 Research Strategy；OpenHands 是 Coding Capability。

两者不能放在同一抽象层。

正式定义：

```text
Strategy
= 怎样组织多个步骤/能力完成科研目标。

Capability
= 一个可调用的具体能力。
```

例如：

```text
STORMResearchStrategy
    uses SearchCapability
    uses LLMCapability
    uses SourceResolverCapability

EvoScientistLikeStrategy
    uses ResearchCapability
    uses CodingCapability
    uses ExecutionCapability
    uses AnalysisCapability
```

未来可实现：

```text
ResearchStrategy
├── STORMStrategy
├── SystematicReviewStrategy
├── DeepResearchStrategy
└── HumanGuidedResearchStrategy

HypothesisStrategy
├── EvolutionaryStrategy
├── TreeSearchStrategy
├── DebateStrategy
└── HumanGuidedStrategy
```

Strategy configuration 作为 ArtifactVersion / configuration 管理，不在 Phase 1 新建大量 strategy tables。

---

## 88. Canonical State Ownership Matrix

开发人员必须遵守：

| Agent/Capability Output | 是否 Canonical | Canonical Home | 写入方式 |
|---|---|---|---|
| STORM retrieved webpage | 否，candidate | literature/external source | source resolver command |
| STORM research report | Artifact | ArtifactVersion | artifact command |
| PaperQA answer | 否，candidate assessment | literature/evidence | review + evidence command |
| EvoScientist plan | 否，candidate plan | ArtifactVersion / future ResearchPlan | artifact/plan command |
| Hypothesis generated by Agent | DRAFT candidate after accepted | research | create/revise hypothesis command |
| AI Scientist experiment branch | 否 | Agent runtime state / Artifact | accepted branch → ExperimentSpec command |
| Coding Agent patch | Artifact candidate | evidence/artifact | create artifact version |
| Executed experiment | 是 | experiment | create/start/finish Run |
| Metric output | 是 | evidence | record measurement |
| Agent interpretation | 否，candidate | Claim DRAFT / assessment | create/revise Claim |
| Writing Agent manuscript | Artifact / future ManuscriptVersion | publication | publication command |
| Reviewer Agent critique | Review/Audit candidate | governance | review/audit command |

全局规则：

```text
Agent memory is not canonical scientific memory.
Conversation history is not canonical scientific state.
Third-party workflow state is not canonical project state.
```

---

## 89. Agent Memory Architecture

ResearchBase 必须区分三种 memory：

### 89.1 Canonical Scientific Memory

ResearchBase Core：

```text
HypothesisVersion
ExperimentSpecVersion
Run
Measurement
StatisticalResult
ClaimVersion
SourceVersion
ArtifactVersion
AuditFinding
...
```

最高可信层。

### 89.2 Working Agent Memory

Agent runtime 用于：

- task scratchpad；
- plan；
- tool result cache；
- discourse state；
- temporary branch tree。

可丢失，可重建，不作为 scientific truth。

### 89.3 User Preference / Long-term Assistant Memory

例如：

- preferred research style；
-常用数据集；
-模型偏好；
-写作习惯。

不得被误当成 Evidence。

Agent 开始任何高价值任务时，应首先 Query Canonical Scientific Memory，而不是只依赖 conversation/context window。

---

## 90. Research Task / Agent Execution 最小概念模型

不要求 Phase 1 落库，但 Phase 2/3 Agent Runtime 应至少支持：

```text
ResearchTask
    id
    project_ref
    task_type
    objective
    input_refs[]
    strategy_ref
    requested_by
    status

AgentExecutionInstance
    actor/agent_version
    task_ref
    started_at
    ended_at
    model/tool configuration

CapabilityInvocation
    execution_ref
    capability_id
    adapter_version
    input_refs
    output_refs
    external_request_metadata
```

`ResearchTask` 可以后续成为 workflow Aggregate；在 Phase 1 不新增。

---

## 91. Human-in-the-Loop / Human-on-the-Loop Levels

结合 Agent Laboratory、Co-STORM 与 EvoScientist 的思路，系统支持分级自治，而不是只有“全自动/全手动”。

```text
A0  Suggest
    Agent 只生成建议。

A1  Draft
    Agent 可创建 DRAFT object，但 Human 决定 freeze。

A2  Execute Approved Plan
    Agent 可执行已 FROZEN ExperimentSpec。

A3  Bounded Autonomous Loop
    Agent 可在 policy/budget 范围内生成候选→运行→分析多轮，
    但 Formal Claim/ExternalEffect 需要 Gate。

A4  High Autonomy Research
    未来研究模式；仍不得覆盖 deterministic facts/P4/hard policy。
```

自治等级是 workflow policy，不等于 P0–P4 Authority。

---

## 92. Agentic Research 主流程

完整目标流程：

```text
Human Research Intent
        ↓
ResearchTask
        ↓
ResearchAgent [STORM-like]
        ↓
LiteratureEvidenceAgent [PaperQA2-like]
        ↓
Research Landscape / Open Questions
        ↓
HypothesisAgent [EvoScientist / TreeSearch-like]
        ↓
DRAFT HypothesisVersion candidates
        ↓
Human/Policy selection
        ↓
FROZEN HypothesisVersion
        ↓
ExperimentDesignAgent
        ↓
DRAFT/FROZEN ExperimentSpecVersion
        ↓
CodingAgent [OpenHands/Codex]
        ↓
ArtifactVersion
        ↓
ExecutionAgent
        ↓
sealed Run
        ↓
Measurement / StatisticalResult
        ↓
AnalysisAgent
        ↓
Scientist/CriticAgent
        ↓
DRAFT ClaimVersion
        ↓
EvidenceRelation
        ↓
Claim freeze / Human scientific gate
        ↓
WritingAgent
        ↓
ManuscriptVersion
        ↓
ReviewerAgent
        ↓
Review / Audit / Revision
```

每一个从 Agent world 进入 Canonical Core 的箭头都必须通过 Application Command。

---

## 93. Autonomous Experiment Loop

Phase 3 建议实现受控循环：

```text
Hypothesis
    ↓
generate Experiment branches
    ↓
pre-register / freeze branch spec
    ↓
Run
    ↓
Measure
    ↓
Evaluate branch
    ↓
┌──────────────┬───────────────┬──────────────┐
prune        refine          continue       escalate human
```

要求：

- 失败 Run 不删除；
- 分支选择策略/score 保存；
- 不能只保留“成功”路径；
- 新 branch 必须形成新的 ExperimentSpecVersion；
- 结果出现后对 ExperimentSpec 的 material 修改不能回写；
- 预算/最大轮数是 hard bound；
- Formal Claim 仍从 EvidenceRelation 构建。

---

## 94. Academic Discussion Room

吸收 Co-STORM 的 collaborative discourse，但不把聊天本身当 science。

参与者：

```text
HumanResearcher
ModeratorAgent
LiteratureExpertAgent
MethodExpertAgent
StatisticianAgent
DomainCriticAgent
```

Discussion Room 输出：

```text
DiscussionTranscript ArtifactVersion
ConceptMap ArtifactVersion
OpenQuestion candidates
Hypothesis candidates
DecisionRecommendation candidates
```

只有显式 promote 后才成为 ResearchQuestion/Hypothesis/Decision canonical objects。

---

## 95. Literature Research Pipeline

目标不是“自动写综述”，而是建立可核验文献证据：

```text
Question Decomposition        [STORM-like]
        ↓
Multi-perspective queries
        ↓
Search / bibliographic APIs
        ↓
Source resolution
        ↓
Full-text / metadata retrieval
        ↓
Scientific RAG               [PaperQA2-like]
        ↓
claim/evidence extraction
        ↓
contradiction / gap analysis
        ↓
ResearchBrief + SourceVersion graph
```

建议 Phase 2 实现 Literature Core；STORM/PaperQA2 adapter 可随后接入。

---

## 96. Coding / Experiment Execution Pipeline

```text
ExperimentSpecVersion
    ↓
ImplementationTask
    ↓
CodingCapability
    ↓
Patch / files / dependency changes
    ↓
tests / lint / reproducibility checks
    ↓
ArtifactVersion(code)
ArtifactVersion(configuration)
ArtifactVersion(environment_manifest)
    ↓
Run
```

代码 Agent 的成功标准不是“它说完成了”，而是：

```text
artifact hash
tests
command log
run result
```

均可审计。

---

## 97. Agent Result Promotion

所有 Agent 输出统一遵循：

```text
GENERATED
→ CANDIDATE
→ VALIDATED
→ PROMOTED_TO_CANONICAL
```

这不是要创建万能状态表，而是 Application/Workflow 的语义协议。

典型：

```text
LLM-generated hypothesis text
    = GENERATED/CANDIDATE

create_hypothesis(...)
    = canonical DRAFT HypothesisVersion

freeze_hypothesis_version(...)
    = FROZEN canonical scientific object
```

禁止 Agent 生成文本后直接标记 FROZEN。

---

## 98. Model / Provider Independence

Agent Runtime MUST 与具体 LLM provider 解耦。

至少定义：

```text
ModelCapability
EmbeddingCapability
SearchCapability
CodingCapability
```

AgentVersion/Execution provenance 保存实际 provider/model/config。

不得把：

```text
GPT-specific response object
Claude-specific message object
LangGraph state
```

写入核心 Domain Schema。

---

## 99. Sandbox 与 Tool Safety

Coding/Execution Agent 默认在 sandbox/workspace 内运行。

必须区分：

```text
read-only research tools
workspace mutation tools
compute execution tools
external side-effect tools
```

Research Agent web search 与 Coding Agent shell execution 不应共享无限工具权限。

外部写操作仍遵守 Governance / ExternalEffect 设计。

---

## 100. 第三方开源项目升级策略

Reference System 升级不得直接升级生产环境。

流程：

```text
UpstreamRelease
    ↓
ReferenceSystemReview
    ↓
AdapterCompatibilityTest
    ↓
Security/License Review
    ↓
Golden Research Task Regression
    ↓
AdapterVersion bump
```

必须 pin：

```text
package version / git commit / container digest
```

AgentExecutionInstance 保存 adapter/version provenance。

---

## 101. License 与 Fork Policy

每个 Reference System 在集成前记录：

```text
license
redistribution constraints
model/API terms
mandatory disclosure requirements
fork maintenance cost
```

特别是自动科研系统可能包含 Responsible AI / disclosure 等非标准许可条款。

默认：

```text
METHOD_REFERENCE
```

不引入代码级 license dependency。

---

## 102. Phase Roadmap 补全

此前 Phase 1 只实现 Core 是正确的，但必须给开发人员看到后续建筑。

### Phase 1 — Trustworthy Research Core

实现：

```text
Research/Hypothesis
ExperimentSpec/Run
Dataset/Artifact
Measurement/Statistics
Evidence/Claim
Audit/Impact
Frozen Provenance Closure
```

Agent：

- 不实现通用 Agent Runtime；
- 允许最小 scripting/coding integration prototype，但不得阻塞 Phase 1 exit。

### Phase 2 — Literature + Research Collaboration + Publication Governance

建议优先：

```text
LiteratureSource / SourceVersion
Citation / LiteratureEvidence
STORM-like ResearchStrategy
PaperQA2 adapter
Academic Discussion Room prototype
ScientificConclusion
Manuscript/Publication basic lifecycle
Internal Review
Decision/Approval basic governance
```

Phase 2 的目标：

> **Human + Research Agents 能围绕同一 canonical research state 完成高质量调研、讨论和 Claim/Manuscript 构建。**

### Phase 3 — Scientific Agent Runtime

实现：

```text
ResearchTask
Agent Runtime
CapabilityGateway
Strategy plugins
EvoScientist-like orchestration
CodingAgent adapter (Codex/OpenHands)
ExecutionAgent
Analysis/Critic/Reviewer Agents
bounded autonomous experiment loop
```

可加入 AI Scientist-v2-style tree search。

### Phase 4 — Advanced Autonomous Research

按需要：

```text
self-evolving skills
agent memory optimization
automatic strategy selection
large-scale experiment search
multi-project scientific memory
advanced review/novelty/replication
```

仍受：

```text
Deterministic Fact > Agent/Authority
Frozen Provenance Closure
Human/P4/ExternalEffect governance
```

约束。

---

## 103. Phase 1 必须预留的 Agent 接口

虽然 Phase 1 不实现 Agent Runtime，但 Core API MUST 保证未来 Agent 无需直接访问数据库。

至少保留：

```text
Application Commands
Application Queries
typed DTO
Run provenance query
Claim trace query
downstream impact query
Artifact registration
Dataset snapshot
```

未来 Agent 一律使用同一 application boundary。

因此 Phase 1 开发人员必须理解：

> **他们正在建设 Agent Runtime 的 canonical state API，而不是只给 Human UI 用的 CRUD backend。**

---

## 104. Phase 1 Development Specification 的新增约束

Phase 1 PR review 增加：

1. Application Command 是否既能被 Human adapter 调用，也能被 Agent adapter 调用；
2. API 是否返回足够 deterministic IDs/hash，而不是只返回 display text；
3. 是否存在必须读取 ORM 才能让未来 Agent 工作的隐藏逻辑；
4. 是否错误地把 conversational/session state 写成 canonical scientific state；
5. 是否给某个未来 STORM/EvoScientist adapter 预埋专属字段，污染 Core；
6. Artifact/Run/Claim 是否足以接住未来 Coding/Analysis Agent 输出。

禁止为了未来 Agent 提前增加：

```text
storm_* tables
evoscientist_* tables
ai_scientist_* tables
langgraph_state columns
```

---

## 105. Agent Architecture Invariants

```text
AGENT-ARCH-INV-001
ResearchBase MUST own canonical scientific state; external agent frameworks MUST NOT become the canonical source of Hypothesis, Run, Measurement or Claim state.

AGENT-ARCH-INV-002
Reference System, Strategy, Capability and Adapter MUST remain distinct concepts.

AGENT-ARCH-INV-003
Third-party agent output MUST enter the canonical model only through governed Application Commands.

AGENT-ARCH-INV-004
Agent working memory/conversation history MUST NOT be treated as canonical scientific memory.

AGENT-ARCH-INV-005
Research strategies such as STORM or tree-search MAY be replaced without migrating canonical scientific state.

AGENT-ARCH-INV-006
Coding agents MUST materialize code/config/environment as ArtifactVersion before their outputs participate in a formal Run.

AGENT-ARCH-INV-007
Autonomous experiment search MUST preserve failed/pruned branch provenance and MUST NOT select only favorable outcomes.

AGENT-ARCH-INV-008
Agent interpretation/recommendation MUST remain distinct from Measurement, StatisticalResult and Formal Claim.

AGENT-ARCH-INV-009
Writing Agents SHOULD generate from canonical Claim–Evidence state rather than opaque chat memory.

AGENT-ARCH-INV-010
Reviewer Agent execution SHOULD remain independent from the authoring execution context for formal review.

AGENT-ARCH-INV-011
Agent Runtime MUST be model/provider/framework independent at the Core boundary.

AGENT-ARCH-INV-012
Agent/Capability adapter versions MUST be provenance-recorded for reproducible agent-assisted research.

AGENT-ARCH-INV-013
Phase 1 MUST NOT add vendor-specific/STORM-specific/EvoScientist-specific fields into scientific Core entities.

AGENT-ARCH-INV-014
Human/Agent interfaces MUST converge on the same Application Command/Query layer.

AGENT-ARCH-INV-015
Increasing agent autonomy MUST NOT weaken Frozen Provenance Closure, deterministic fact precedence or governance invariants.
```

---

## 106. Architecture Decision：直接集成还是自行实现

当前推荐：

```text
STORM / Co-STORM
    → 先 METHOD_REFERENCE
    → Phase 2 可做 thin adapter prototype
    → 不 fork 为 ResearchBase core

PaperQA2
    → 优先 LIBRARY_ADAPTER
    → 用于 scientific literature evidence
    → ResearchBase 保存 resolved sources/evidence provenance

EvoScientist
    → 作为 Agent Runtime / multi-agent workflow 重点参考
    → Phase 3 对比“直接 service adapter vs native ResearchBase orchestration”
    → 不以 EvoScientist repo 作为 ResearchBase 主仓库

AI Scientist-v2
    → 借 experiment manager / tree-search
    → 在 ResearchBase 上实现 native Strategy 更合适
    → 不继承其内部 scientific state schema

Agent Laboratory
    → 借 human checkpoints / staged workflow
    → 不作为硬依赖

DeerFlow
    → 借 harness/sandbox/skills/MCP 架构
    → Agent Runtime 技术选型阶段与 LangGraph/EvoScientist/OpenHands 比较

OpenHands / Codex
    → CodingCapability adapter
    → 可替换
    → 不允许它们直接写 ResearchBase DB
```

最终原则：

> **Borrow scientific workflows and agent capabilities; do not outsource scientific state ownership.**

---

## 107. Reference Sources（架构核验，2026-08-26）

本节记录当前架构补全所核验的主要 upstream。URL 用于实现阶段重新核验，不构成固定版本依赖。

- Stanford OVAL STORM / Co-STORM: `https://github.com/stanford-oval/storm`
- FutureHouse PaperQA2: `https://github.com/Future-House/paper-qa`
- EvoScientist: `https://github.com/EvoScientist/EvoScientist`
- Sakana AI Scientist v1: `https://github.com/SakanaAI/AI-Scientist`
- Sakana AI Scientist v2: `https://github.com/SakanaAI/AI-Scientist-v2`
- Agent Laboratory: `https://github.com/Point-Zheng/AgentLaboratory`
- ByteDance DeerFlow: `https://github.com/bytedance/deer-flow`
- OpenHands: `https://github.com/All-Hands-AI/OpenHands`

实现时不得只依据本文描述，必须 pin 并核验具体 upstream tag/commit/license。

---


# 第十九部分：Phase 1 可施工实现规范（Normative）\n\n本部分是本次 Review 新增的“施工图层”。它不改变前述领域哲学，而是把中级程序员最容易自行解释的地方收敛为明确契约。\n\n## 61. 参考实现技术 Profile\n\nPhase 1 默认参考栈：\n\n```text\nPython 3.12+\nPostgreSQL 16+\nSQLAlchemy 2.x\nAlembic\nPydantic 2.x\nFastAPI（HTTP API）\nTyper（CLI）\npytest\n```\n\n允许替换 Web/CLI framework，但不得替换 PostgreSQL 的关系完整性语义或削弱 typed domain model。SQLite 仅允许用于快速单元测试，不作为 Phase 1 集成验收数据库。\n\n## 62. 模块依赖与代码边界\n\n强制规则：\n\n```text\nfoundation  ← 所有模块可依赖\napplication ← 编排多个 Domain use case\npersistence ← 实现 Repository，知道 ORM/SQL\nDomain      ← 不直接调用其他 Domain 的 Repository/ORM\n```\n\n具体要求：\n\n1. Domain entity/value object 不 import SQLAlchemy model。\n2. 跨 Domain orchestration 进入 `application/` service。\n3. 跨 Domain entity 只保存 typed ID/reference，不持有对方 ORM object。\n4. `persistence/` 可以实现 concrete FK，但不得把 ORM relationship 当 Domain Source of Truth。\n5. CI 增加 import-boundary test，禁止 `foundation` 反向依赖业务模块。\n\n## 63. Version Lifecycle 与 Freeze Point\n\n所有 Version Identity 使用统一生命周期：\n\n```text\nDRAFT → FROZEN → SUPERSEDED\n  └────────────→ ABANDONED\n```\n\n规则：\n\n- DRAFT：允许编辑 material fields；\n- FROZEN：material fields immutable；\n- SUPERSEDED：存在更新版本，但旧版本继续有效作为历史 provenance；\n- ABANDONED：未进入正式 provenance 的草稿废弃；\n- 任何被 Run、Measurement、Formal Claim、Review、Submission 引用的 Version 必须先 FROZEN。\n\n对 `ClaimVersion`：EvidenceRelation 只能在 DRAFT 阶段新增/删除；freeze 时计算 `support_set_hash`，之后若证据集合变化必须创建新的 ClaimVersion。\n\n## 64. Run 状态机与输入 Seal\n\n`Run` 不再被理解为“从创建起完全 immutable”，而是 **stateful-until-terminal**：\n\n```text\nPLANNED → RUNNING → SUCCEEDED\n                 ├→ FAILED\n                 └→ CANCELLED\nPLANNED ─────────────→ CANCELLED\n```\n\n规则：\n\n1. `PLANNED` 时可添加/调整输入；\n2. `PLANNED → RUNNING` 必须原子执行 `seal_inputs()`；\n3. `RUNNING` 后 DatasetSnapshot、ArtifactVersion、ExperimentSpecVersion、run_type 等 material provenance 不可变；\n4. Terminal 状态后只有非 material operational annotations 可通过 append-only event 增加；\n5. 重跑创建新 `Run`；禁止复用旧 Run ID。\n\n## 65. Phase 1 Run Input Model\n\nRun 输入明确拆为：\n\n```text\nRun\n ├─ ExperimentSpecVersion (exactly 1)\n ├─ DatasetSnapshot      (0..N via run_dataset_inputs)\n └─ ArtifactVersion      (0..N via run_artifact_inputs)\n```\n\n`run_dataset_inputs.role` 建议枚举：\n\n```text\ntrain | validation | test | calibration | auxiliary | other\n```\n\n`run_artifact_inputs.role` 建议枚举：\n\n```text\nsource_code | model | checkpoint | configuration | environment_manifest | script | dependency_lock | other\n```\n\nConfiguration 与 Environment 在 Phase 1 **不建立独立表**，使用 `ArtifactVersion` + role 表达。\n\n## 66. DatasetSnapshot 施工规则\n\nPhase 1 规定：只要 Run 使用 Dataset，就必须创建/引用 DatasetSnapshot。\n\nSnapshot 至少包含：\n\n```text\nid\ndataset_id\noptional dataset_version_id\nmanifest_hash\nselection_definition\ncreated_at\ncreated_by\ncontent_hash\n```\n\nSnapshot 可以只保存 manifest/selection/hash，不复制实际数据。这样消除“DatasetVersion 是否足够 immutable”的双实现路径。\n\n## 67. Measurement / StatisticalResult 输入规则\n\n`Measurement` 至少绑定：\n\n```text\nrun_id\nmetric_definition_version_id\nvalue / structured_value\nunit\nevaluation_scope\ncreated_at\n```\n\nMeasurement value 创建后不可 UPDATE。\n\n`StatisticalResult` 可以汇总多个 Measurement，使用 `statistical_result_inputs`：\n\n```text\nstatistical_result_id\nmeasurement_id\ninput_role\nordinal\n```\n\n禁止把多个 Measurement ID 塞进 JSON 作为唯一 provenance。\n\n## 68. EvidenceRelation 与 Claim 冻结规则\n\nPhase 1 `EvidenceRelation` 的目标固定为 `ClaimVersion`，source 只允许：\n\n- `measurement_id`；或\n- `statistical_result_id`。\n\n两者必须满足 XOR CHECK：一行只能选择一种 source。\n\n建议字段：\n\n```text\nid\nclaim_version_id\nmeasurement_id nullable\nstatistical_result_id nullable\nrelation_type\nqualification nullable\ncreated_at\ncreated_by\n```\n\nClaimVersion freeze 后禁止新增、删除或修改其 EvidenceRelation；证据变化创建新 ClaimVersion。\n\n## 69. Domain Reference 与数据库 FK 规则\n\n`FrozenReference<T>` 是 Domain abstraction，不等于数据库里建立一个万能 polymorphic reference 表。\n\n强制规则：\n\n- 科研主链使用 concrete FK；\n- FK 默认 `ON DELETE RESTRICT`；\n- 禁止主链使用 `target_type + target_id`；\n- Governance 横切对象（例如 AuditFinding target）允许 soft typed locator，但必须由 application validator 验证目标存在，并保存 target content hash/version identity；\n- 任何 soft reference 不得承担 Frozen Provenance Closure 的唯一关键边。\n\n## 70. Transaction Boundaries\n\n原则：**一个 Application Command = 一个数据库事务**。\n\n必须原子化的典型动作：\n\n- freeze Version；\n- start Run + seal inputs；\n- finish Run；\n- create Measurement；\n- create StatisticalResult + inputs；\n- freeze ClaimVersion + lock EvidenceRelation set；\n- create AuditFinding + initial affected target refs。\n\n禁止在 HTTP handler/CLI command 中手工跨多个 repository `commit()`。Transaction/UoW 由 application layer 控制。\n\n## 71. Concurrency\n\nLong-lived Identity 的 `current_version_id`、DRAFT version 编辑和 Run 状态转换使用 optimistic concurrency。\n\n推荐：\n\n```text\nrow_version INTEGER NOT NULL\nUPDATE ... WHERE id=? AND row_version=?\n```\n\n更新行数为 0 时返回 `CONCURRENT_MODIFICATION`，调用方重新读取，不允许 last-write-wins 静默覆盖。\n\nImmutable insert 使用数据库唯一约束保证幂等/重复检测。\n\n## 72. Hash 与时间规范\n\n统一：\n\n- 时间：UTC，数据库使用 `TIMESTAMPTZ`；API 使用 ISO-8601 `Z`；\n- 内容 Hash：SHA-256；\n- 文件 ArtifactVersion：hash 原始 bytes；\n- Structured content：使用 canonical JSON（键排序、稳定数值/Unicode serialization）后 hash；\n- `content_hash` 不包含数据库 ID、`created_at`、current pointer 等非 material 字段；\n- hash algorithm 必须随记录保存或由 schema version 唯一确定。\n\n## 73. 删除、修正和 Validity Projection\n\nPhase 1 核心科学表默认：\n\n```text\nON DELETE RESTRICT\nno physical cascade delete\n```\n\n`Measurement`、`StatisticalResult`、terminal `Run` 的值不因“invalid”而修改。\n\n当前有效性通过以下记录派生：\n\n```text\nAuditFinding\nImpactAssessment\nCorrectionRecord\n```\n\n推荐 projection 状态：\n\n```text\nVALID | STALE | INVALID | CORRECTED | UNKNOWN\n```\n\n该状态是 derived view，不是原事实值的一部分。\n\n## 74. Application Command / Query 契约\n\nPhase 1 必须至少提供以下 Application Commands：\n\n```text\ncreate_project\ncreate_workspace\ncreate_research_question\nrevise_research_question\nfreeze_research_question_version\ncreate_hypothesis\nrevise_hypothesis\nfreeze_hypothesis_version\ncreate_experiment_spec\nrevise_experiment_spec\nfreeze_experiment_spec_version\nregister_dataset\ncreate_dataset_snapshot\nregister_artifact\ncreate_artifact_version\ncreate_run\nattach_run_dataset_input\nattach_run_artifact_input\nstart_run\nfinish_run\nrecord_measurement\nrecord_statistical_result\ncreate_claim\nrevise_claim\nlink_evidence\nfreeze_claim_version\ncreate_audit_finding\ncreate_impact_assessment\ncreate_correction_record\n```\n\n最低 Queries：\n\n```text\nget_project\nget_hypothesis_history\nget_experiment_spec_history\nget_run_provenance\ntrace_claim_to_runs\ntrace_run_to_inputs\nget_downstream_impact\nget_current_validity\n```\n\nCLI 与 HTTP API 都调用同一 application service，不各写一套业务逻辑。\n\n## 75. HTTP/CLI 最小接口风格\n\n不强制最终 URL，但 Phase 1 推荐：\n\n```text\nPOST /projects\nPOST /hypotheses\nPOST /hypotheses/{id}/versions\nPOST /experiment-specs\nPOST /runs\nPOST /runs/{id}:start\nPOST /runs/{id}:finish\nPOST /measurements\nPOST /statistical-results\nPOST /claims\nPOST /claims/{id}/evidence\nPOST /claims/{id}:freeze\nGET  /claims/{version_id}/trace\nGET  /runs/{id}/provenance\nGET  /objects/{type}/{id}/impact\n```\n\n所有 write response 返回 canonical ID、version ID（若有）、content hash 与 server timestamp。\n\n## 76. 标准错误模型\n\nApplication 层至少统一以下错误码：\n\n```text\nNOT_FOUND\nINVALID_STATE_TRANSITION\nVERSION_NOT_FROZEN\nIMMUTABLE_RECORD\nFROZEN_REFERENCE_REQUIRED\nPROVENANCE_CLOSURE_VIOLATION\nCONCURRENT_MODIFICATION\nDUPLICATE_CONTENT\nREFERENTIAL_INTEGRITY_ERROR\nVALIDATION_ERROR\n```\n\nHTTP adapter 再映射 400/404/409/422；Domain 不直接依赖 HTTP status。\n\n## 77. 数据库约束与索引基线\n\n至少包含：\n\n- `UNIQUE(parent_id, version_number)`：所有 version chain；\n- `UNIQUE(artifact_id, content_hash)`；\n- Run input relation `UNIQUE(run_id, target_id, role)`；\n- Statistical input `UNIQUE(statistical_result_id, measurement_id, input_role)`；\n- EvidenceRelation XOR CHECK；\n- 所有 frozen FK 使用 `ON DELETE RESTRICT`；\n- 对 `project_id`、`run_id`、`claim_version_id`、`content_hash`、`created_at` 建必要索引；\n- current version pointer 的 FK 必须指向同一 parent identity（application + constraint/test 双重保证）。\n\n## 78. Phase 1 多人并行施工包\n\n建议 4 个工作包，避免若干中级程序员同时修改核心语义：\n\n| Work Package | 负责范围 | 允许依赖 | Gate |\n|---|---|---|---|\n| WP-A Foundation/Persistence | refs、hash、UoW、migration、base repository | foundation | Architecture tests A |\n| WP-B Research/Experiment | question/hypothesis/spec/run state machines | WP-A | Version + Run tests |\n| WP-C Evidence | dataset/artifact/measurement/statistics/evidence | WP-A, WP-B public interfaces | Provenance tests |\n| WP-D Audit/API | audit/impact/correction、CLI/API、trace query | WP-A–C public interfaces | E2E tests |\n\n每个 WP 只能通过公开 application/domain interface 访问其他 WP；禁止跨包直接 import 对方 persistence model。\n\n## 79. 合并 Gate 与 Definition of Done\n\n每个 PR 至少满足：\n\n1. 对应 Domain tests；\n2. Architecture import-boundary tests；\n3. migration 可在空库 forward apply；\n4. migration rollback 或明确 irreversible note；\n5. 无主链 polymorphic soft ref；\n6. 无 immutable record UPDATE；\n7. 无 `ON DELETE CASCADE` 指向 scientific history；\n8. 新增表/Schema 若超出本规范，附 Architecture Change Note；\n9. Phase 1 architecture tests 全部持续通过。\n\n## 80. 修订后的 Phase 1 Exit Criteria\n\nPhase 1 GO-to-Phase-2 前必须完成：\n\n- WP-A～D 全部 Gate 通过；\n- `ClaimVersion → EvidenceRelation → Measurement/StatisticalResult → Run → DatasetSnapshot/ArtifactVersion/ExperimentSpecVersion` 可双向 trace；\n- Run input seal 与 terminal immutability 有数据库/服务测试；\n- Claim evidence-set freeze 有测试；\n- DatasetSnapshot mandatory boundary 有测试；\n- Frozen Provenance Closure 只遍历 concrete frozen refs 即可成功；\n- 至少一条错误注入场景可以通过 AuditFinding/ImpactAssessment 找到受影响 ClaimVersion，而不修改旧 Measurement；\n- PostgreSQL 集成测试通过；\n- Optional Literature 未完成不阻塞 Phase 1 exit。\n\n---\n\n# 附录 A：Phase 0 历史冻结版 architecture.md（审计留档）

# ResearchBase Architecture

## 1. Purpose

ResearchBase is a research provenance and scientific traceability foundation. Its primary goal is not to maximize automation, but to guarantee that every formal scientific result, claim, decision, and publication artifact can be traced back to the exact evidence, run, dataset state, code/artifact state, configuration, and governing context from which it arose.

The architecture is intentionally designed around immutable scientific history, typed references, explicit provenance, and strict separation between scientific facts and governance authority.

## 2. Phase-0 Status

- Schema Design: CLOSED
- Architecture Closure: CLOSED
- Architecture: FROZEN FOR PHASE-0 REVIEW
- Phase 1 implementation: NOT STARTED
- Database migrations: NOT STARTED
- Agent workflows: NOT STARTED

No Phase 1 implementation may begin until the Phase 0 STOP Gate is explicitly approved.

## 3. Architectural Principles

### 3.1 Deterministic Fact Precedence

Deterministic canonical facts take precedence over review, decision, and approval states.

Authority may determine what actions are permitted. It may not redefine arithmetic, data integrity, measurement values, leakage findings, or other deterministic scientific facts.

### 3.2 One Canonical Source of Truth

Every canonical fact has exactly one owning domain. Other domains may reference, query, index, cache, or project that fact, but must not create an independent second source of truth.

### 3.3 Historical Provenance Is Immutable

Formal historical records such as Runs, Measurements, StatisticalResults, Decisions, ApprovalDecisions, ReviewRecords, and SubmissionVersions are not rewritten in place. Corrections produce explicit correction provenance or new records/versions.

### 3.4 Formal Provenance Uses Frozen References

Any relation that answers “what was this based on at that time?” uses a FrozenReference by default.

LiveReference is reserved for current-state navigation, such as a Publication pointing to its current ManuscriptVersion for UI navigation.

### 3.5 Frozen Provenance Closure

Any formal scientific or governance snapshot must resolve its material provenance dependencies to deterministic frozen versions. No unresolved `latest` or `current` dependency may remain inside a released provenance graph.

### 3.6 Governance Concepts Do Not Substitute for One Another

- Review evaluates.
- Decision chooses.
- Approval authorizes.
- Command requests execution.
- ExternalEffect records what actually changed externally.

These concepts remain distinct throughout the system.

### 3.7 Agent and Human Use the Same Research Model

Agents do not receive a parallel scientific object model. Human and Agent actors create, reference, review, and operate on the same canonical research entities. Differences are enforced through authority, accountability, provenance, and policy.

## 4. Domain Structure

ResearchBase is a modular monolith organized into one foundation module and ten business domains.

```text
researchbase/
├── foundation/
├── identity/
├── organization/
├── research/
├── experiment/
├── evidence/
├── literature/
├── publication/
├── governance/
├── compliance/
├── resources/
├── application/
└── persistence/
```

The domain split is a code and semantic boundary, not a microservice boundary.

### 4.1 foundation

Owns only cross-domain primitives:

- UUIDv7
- Instant
- ContentHash
- StructuredValue
- Unit
- Money
- TemporalInterval
- SchemaVersion
- FrozenReference<T>
- LiveReference<T>
- ExternalReference

Foundation imports no business domain.

### 4.2 identity

Owns stable actor identity and authentication provenance:

- ActorIdentity
- HumanActor / AgentActor / ServiceActor / ExternalActor classification
- ActorIdentifier
- AgentVersion
- AgentExecutionInstance
- AuthenticationContext

Identity answers “who is this actor?”, not “what are they allowed to do?”.

### 4.3 organization

Owns organizational and project scope:

- Organization
- Project
- Workspace
- Team
- Membership
- ResponsibilityAssignment
- OwnershipAssignment

Project is a governance/provenance scope, not a parent object that owns and deletes all research content.

### 4.4 research

Owns scientific propositions and conclusions:

- ResearchQuestion / ResearchQuestionVersion
- Hypothesis / HypothesisVersion
- Claim / ClaimVersion
- ScientificConclusion / ScientificConclusionVersion

Hypothesis, Claim, and ScientificConclusion remain distinct concepts.

### 4.5 experiment

Owns planned and actual execution:

- ExperimentSpec / ExperimentSpecVersion
- Run
- configuration / environment provenance represented by `ArtifactVersion` roles (`configuration`, `environment_manifest`) logical concepts (Phase 1 persisted as typed ArtifactVersion roles)

`WorkflowRun` is not a separate canonical entity. Different execution forms use `Run.run_type` and parent/child run relations.

### 4.6 evidence

Owns datasets, artifacts, metrics, measurements, and statistical evidence:

- Dataset / DatasetVersion
- DatasetSnapshot
- Artifact / ArtifactVersion
- MetricDefinition / MetricDefinitionVersion
- Measurement
- StatisticalResult
- EvidenceRelation

Evidence objects do not own publication state.

### 4.7 literature

Owns literature identity and literature-based assessments:

- LiteratureSource
- SourceVersion
- Citation relations
- Prior-art relations
- NoveltyAssessment

The domain is deliberately named `literature`, not `knowledge`, to avoid becoming a generic dumping ground for memory, RAG, ontology, and graph abstractions.

### 4.8 publication

Owns manuscript and publication lifecycle artifacts:

- Publication
- ManuscriptVersion
- SubmissionVersion
- AuthorshipSnapshot
- VenueReviewRecord
- CameraReady
- PublishedVersion

Publication external review and internal ResearchBase review remain distinct.

### 4.9 governance

Owns cross-domain governance objects:

- DecisionRecord
- ApprovalRequest
- ApprovalDecision
- ApprovalGrant
- InternalReviewRecord
- AuditFinding
- Incident
- ImpactAssessment
- Appeal
- Authority / Delegation / COI assessments

Governance may reference every governed domain, but scientific domains must not depend on governance implementation details as their source of truth.

### 4.10 compliance

Owns only the minimum compliance/ethics boundary needed by ResearchBase:

- Policy / PolicyVersion
- DataZone
- EthicsProtocolVersion
- ExternalEthicsApproval
- ConsentRecord
- ProtocolDeviation

ResearchBase is not an IRB, HIPAA, GDPR, or hospital ethics workflow platform.

### 4.11 resources

Owns research resource provenance:

- Grant
- ResourcePool
- ResourceRequest
- ResourceReservation
- ResourceUsage
- supporting Budget / Cost records

ResearchBase is not a financial ERP or accounting system.

## 5. Canonical Object Classes

ResearchBase uses four primary object classes.

### 5.1 Long-lived Identity Entities

Stable identity with evolving current state:

- Project
- Workspace
- Organization
- ActorIdentity
- Dataset
- Artifact
- LiteratureSource
- Publication
- Grant
- ResourcePool

### 5.2 Version Identities

Semantically versioned objects whose formal versions are immutable:

- ResearchQuestionVersion
- HypothesisVersion
- ClaimVersion
- ScientificConclusionVersion
- ExperimentSpecVersion
- DatasetVersion
- ArtifactVersion
- MetricDefinitionVersion
- SourceVersion
- ManuscriptVersion
- SubmissionVersion
- PolicyVersion
- AgentVersion

### 5.3 Immutable Facts / Records

Historical records that are corrected through new records or correction provenance rather than ordinary update:

- Run
- DatasetSnapshot
- Measurement
- StatisticalResult
- DecisionRecord
- ApprovalRequest
- ApprovalDecision
- ReviewRecord
- ImpactAssessment
- AuthorConsent

### 5.4 Stateful Relations / Governance Objects

Objects with real lifecycle transitions whose temporal history must remain recoverable:

- Membership
- RoleAssignment
- ResponsibilityAssignment
- OwnershipAssignment
- Incident
- ApprovalGrant
- ResourceReservation

## 6. Reference Model

### 6.1 FrozenReference<T>

Represents a specific historical object/version state.

Used for:

- Run dependencies
- Measurement provenance
- StatisticalResult provenance
- Claim support
- ScientificConclusion basis
- Decision basis
- Review target
- Approval target
- Submission contents
- Citation source versions
- Authorship snapshots
- Audit and impact targets

### 6.2 LiveReference<T>

Represents navigation to the current state of a long-lived identity.

Used for examples such as:

- Project → current Workspace
- Artifact → current ArtifactVersion
- Publication → current ManuscriptVersion
- Dataset → current DatasetVersion
- AgentActor → current AgentVersion

### 6.3 ExternalReference

Represents external identifiers or resources that do not have database-enforced referential integrity, such as DOI, ORCID, GitHub URL, or external dataset URL.

## 7. Scientific Provenance Chain

The primary scientific chain is frozen as:

```text
ResearchQuestionVersion
        ↓
HypothesisVersion
        ↓
ExperimentSpecVersion
        ↓
Run
   ┌────┼────────────┐
   ↓    ↓            ↓
DatasetSnapshot   ArtifactVersion
        ↓
Measurement
        ↓
StatisticalResult
        ↓
EvidenceRelation
        ↓
ClaimVersion
        ↓
ScientificConclusionVersion   [optional]
        ↓
ManuscriptVersion
        ↓
SubmissionVersion              [Phase 2]
```

A formal Claim must be traceable back to actual Runs and deterministic inputs. A formal Run must be traceable to frozen experiment specification, dataset state, artifact/code state, configuration, environment, and relevant method definitions.

## 8. Error and Impact Propagation

Scientific defects propagate through governed impact assessment rather than hidden mutation.

```text
AuditFinding / Incident
        ↓
ImpactAssessment
        ↓
affected Run / Measurement / StatisticalResult
        ↓
Evidence stale or invalid
        ↓
Claim affected
        ↓
ScientificConclusion affected
        ↓
Manuscript / Submission impact
```

Examples include data leakage, code bugs, metric definition errors, statistical errors, newly discovered contradictory evidence, and material prior art.

## 9. Governance Architecture

### 9.1 Global Fact Precedence Rule

```text
Deterministic canonical fact
>
Review / Decision / Approval state
```

Approval cannot make an incorrect Measurement correct. Review consensus cannot override a deterministic integrity failure.

### 9.2 Governance Chain

```text
Evidence / Facts
      ↓
Review / Audit
      ↓
Findings / Assessment
      ↓
DecisionRecord
      ↓
Internal revision OR ApprovalRequest
      ↓
ApprovalDecision
      ↓
ApprovalGrant
      ↓
Command
      ↓
ExternalEffect
```

Not every workflow requires every step, but their semantics never collapse.

### 9.3 P0–P4

P0–P4 remain policy taxonomy labels and are not implemented as a scalar superuser ladder.

Authority eligibility depends on domain, scope, role, policy, delegation, identity assurance, and context.

P3 external-action authority and P4 scientific-release authority are distinct authority dimensions.

### 9.4 Multi-authority Rule

Where independent authority domains apply, mandatory requirements compose conjunctively. One “higher” internal approval does not replace ethics, data-owner, legal, or external authority.

### 9.5 Agent Authority

Agents may draft, search, analyze, audit, recommend, and execute specifically pre-approved actions.

Agents may not:

- self-approve
- self-delegate P4
- infer broad authority from `acting_on_behalf_of`
- silently mutate scientific history
- invent provenance
- override deterministic facts

P4 formal scientific approval remains Human by default.

## 10. Versioning and Correction Rules

### 10.1 Versioned objects

ResearchQuestion, Hypothesis, Claim, ScientificConclusion, ExperimentSpec, Dataset, Artifact, MetricDefinition, LiteratureSource, Manuscript, Policy, and Agent executable definition support explicit version identity where required.

### 10.2 Immutable records

Run, Measurement, StatisticalResult, DecisionRecord, ApprovalDecision, ReviewRecord, and ImpactAssessment do not use ordinary version chains.

Examples:

- rerun → new Run, not RunVersion
- recalculation → new Measurement/StatisticalResult
- changed decision → new DecisionRecord
- re-review → new ReviewRecord

### 10.3 CorrectionRecord

Historical immutable records are not overwritten for ordinary correction. A CorrectionRecord may identify the target, prior assertion, corrected assertion, basis, actor, and timestamp while preserving the original record.

## 11. Aggregate Boundaries

Priority aggregates for implementation are:

- ProjectAggregate
- ResearchAggregate
- ExperimentAggregate
- DatasetAggregate
- ArtifactAggregate
- PublicationAggregate
- GovernanceAggregate
- IdentityAggregate

Not every schema becomes an aggregate root.

Supporting concepts are classified as:

- Value Objects
- Relation Entities
- Assignment Entities
- Assessments
- Snapshots
- Events
- Derived Views

## 12. Derived Views Are Not Sources of Truth

Examples:

- current authority profile
- latest manuscript
- current project members
- current claim status
- remaining budget
- dashboard metrics

These may be cached or materialized, but must be derivable from canonical records.

## 13. Data and Deletion Semantics

Canonical scientific/provenance records should not use broad physical cascade deletion.

Preferred mechanisms:

- logical retirement
- supersession
- tombstone
- redaction
- correction
- archival

Project archival or Publication withdrawal must not delete underlying Dataset, Run, Measurement, or Evidence history.

## 14. Implementation Shape

Phase 1 uses:

- Python
- typed domain models
- relational database
- modular monolith
- CLI/API first
- append-only audit/event records where useful

Phase 1 explicitly does not use:

- microservices
- full event sourcing / CQRS
- generic Object(id,type,json) storage
- a single universal metadata JSON as the semantic core

## 15. Architecture Complexity Budget

Any new canonical schema must demonstrate that the concept cannot be expressed clearly through an existing Entity + Relation + Assessment + Snapshot + Event combination.

Default decision for new top-level schema requests is: **do not add the schema unless justified**.

## 16. Phase 1 Architectural Focus

The four highest-priority engineering goals are:

1. Immutable and version semantics
2. FrozenReference correctness
3. Provenance graph correctness
4. Deterministic auditability

These take precedence over advanced UI, autonomous agents, workflow automation, and administrative features.

## 17. Phase 1 Non-goals

- No full manuscript editor
- No full submission system
- No automated venue submission
- No autonomous P4 scientific approval
- No full IAM/RBAC platform
- No IRB management platform
- No financial ERP
- No procurement/accounting system
- No full citation manager
- No full authorship dispute workflow
- No microservices
- No full CQRS/Event Sourcing
- No autonomous reviewer replacement

## 18. Phase-0 STOP Gate

After `architecture.md`, `implementation_plan.md`, and `schema_registry.md` are completed and reviewed, development must stop.

Phase 1 begins only after explicit approval of the Phase 0 architecture and implementation plan.

---

# 附录 B：Phase 0 历史冻结版 implementation_plan.md（审计留档）

# ResearchBase Implementation Plan

## 1. Purpose

This plan converts the frozen Phase 0 architecture into an implementation sequence while deliberately preventing over-implementation.

The first implementation phase is a scientific provenance MVP, not a full research administration platform and not an autonomous scientist.

## 2. Mandatory Phase-0 STOP Gate

Current state:

- Architecture design: COMPLETE
- Schema design: COMPLETE
- Architecture closure audit: COMPLETE
- Phase 1 implementation: NOT STARTED

Before any Phase 1 code, migrations, agent workflow, or external connector implementation begins, the following documents must be explicitly approved:

- `architecture.md`
- `implementation_plan.md`

`schema_registry.md` is a supporting reference and should be reviewed together with them.

## 3. Phase 1 Goal

Deliver one trustworthy end-to-end research provenance workflow:

```text
ResearchQuestion / Hypothesis
        ↓
ExperimentSpec
        ↓
Run
        ↓
Frozen Dataset + Artifact provenance
        ↓
Measurement / StatisticalResult
        ↓
EvidenceRelation
        ↓
Claim
        ↓
Traceable provenance view + basic audit
```

Phase 1 succeeds when a user can reliably answer:

1. What exact experiment produced this result?
2. What exact dataset state, code/artifact version, configuration, and environment did that run use?
3. Which measurements/statistical results support this claim?
4. If an upstream input/result is invalidated, which downstream claims are affected?

## 4. Phase 1 User Capabilities

Phase 1 should expose six practical capabilities:

1. Project workspace
2. ResearchQuestion / Hypothesis registry
3. ExperimentSpec and Run tracking
4. Dataset and Artifact provenance
5. Measurement / StatisticalResult / Evidence registry
6. Claim traceability and basic audit

These capabilities should be usable through CLI/API first. A minimal UI may be added only if it does not delay provenance correctness.

## 5. Phase 1 Scope

### 5.1 Foundation

Implement:

- UUIDv7
- Instant
- ContentHash
- SchemaVersion
- FrozenReference<T>
- LiveReference<T>
- ExternalReference
- StructuredValue boundaries
- common lifecycle conventions

Required tests:

- FrozenReference resolves to exact object/version
- LiveReference navigation cannot be used inside formal frozen provenance closure
- schema_version is distinct from domain object version

### 5.2 Identity

Implement only:

- ActorIdentity
- actor_type
- basic ActorIdentifier

Do not implement full authentication, RBAC, delegation, or P0–P4 engine in Phase 1.

### 5.3 Project / Workspace

Implement:

- Project
- Workspace
- project-scoped canonical references

Do not model Project as owner of all scientific object lifecycles.

No cascade delete from Project into scientific objects.

### 5.4 Research

Implement:

- ResearchQuestion + ResearchQuestionVersion
- Hypothesis + HypothesisVersion
- Claim + ClaimVersion

ScientificConclusion may remain deferred unless required by a concrete Phase 1 workflow.

Required semantics:

- formal references use exact versions
- semantic changes create new versions
- historical versions remain immutable

### 5.5 Experiment

Implement:

- ExperimentSpec + ExperimentSpecVersion
- Run
- run_type
- optional parent_run_ref
- configuration / environment provenance represented by `ArtifactVersion` roles (`configuration`, `environment_manifest`) logical concepts (Phase 1 persisted as typed ArtifactVersion roles)

Do not create WorkflowRun, TrainingRun, EvaluationRun, or AnalysisRun canonical subclasses.

Required semantics:

- Run binds FrozenReference<ExperimentSpecVersion>
- rerun creates a new Run
- completed Run is not normally mutated
- corrections use governed correction provenance

### 5.6 Evidence

Implement:

- Dataset
- DatasetVersion only where needed
- DatasetSnapshot (**mandatory Run input boundary in Phase 1**)
- Artifact
- ArtifactVersion
- MetricDefinition + MetricDefinitionVersion
- Measurement
- StatisticalResult
- EvidenceRelation

Required semantics:

- every Phase 1 Run using datasets must bind one or more exact DatasetSnapshot rows
- Measurement is immutable
- StatisticalResult is immutable
- Measurement binds exact MetricDefinitionVersion
- ArtifactVersion uses content hash where applicable

### 5.7 Literature（Optional Phase 1 Extension）

Literature is **not a Phase 1 exit blocker**. If schedule permits after the provenance core passes, implement only:

- LiteratureSource
- SourceVersion

Do not build full citation manager, novelty workflow, screening system, or bibliographic conflict resolver in Phase 1.

### 5.8 Publication（Phase 2）

Publication is not part of the mandatory Phase 1 implementation. Phase 1 provenance demos terminate at ClaimVersion.

Publication / ManuscriptVersion / SubmissionVersion, CameraReady, review rounds, citation placement, and authorship governance begin in Phase 2.

### 5.9 Governance

Phase 1 implements only:

- AuditFinding
- ImpactAssessment
- CorrectionRecord (basic common mechanism)

Do not build the full Approval, Delegation, Appeal, COI, or authority engine.

Required semantics:

- findings do not directly mutate scientific facts
- invalidation propagates through ImpactAssessment

## 6. Phase 1 Reference Relational Model

Target approximately **25–30 core and relation tables**. The original 15–20 estimate was too low because it omitted material many-to-many provenance edges. Relational integrity takes precedence over minimizing table count.

Recommended baseline:

```text
actors
projects
workspaces

research_questions
research_question_versions
hypotheses
hypothesis_versions
claims
claim_versions

experiment_specs
experiment_spec_versions
runs

datasets
dataset_snapshots
artifacts
artifact_versions
run_dataset_inputs
run_artifact_inputs

metric_definitions
metric_definition_versions
measurements
statistical_results
statistical_result_inputs
evidence_relations

audit_findings
impact_assessments
correction_records
```

Optional Literature extension adds `literature_sources` and `source_versions`. Core provenance edges use concrete foreign keys. Generic polymorphic references are not allowed on the scientific main chain.

## 7. Implementation Sequence

### Phase 1A — Foundation and persistence skeleton

Deliver:

- project package structure
- relational persistence configuration
- UUIDv7 / timestamps / hashes
- typed object references
- migration framework
- basic repository/service boundaries

Acceptance criteria:

- foundation imports no business modules
- typed FrozenReference and LiveReference exist
- database can persist and resolve canonical IDs and versions

### Phase 1B — Research and experiment version semantics

Deliver:

- ResearchQuestion / Hypothesis / Claim version chains
- ExperimentSpec version chain
- Run entity

Acceptance criteria:

- editing a Hypothesis or ExperimentSpec creates a new version
- old Run references remain bound to the prior ExperimentSpecVersion
- rerun produces a new Run, never a RunVersion

### Phase 1C — Dataset / Artifact provenance

Deliver:

- Dataset
- DatasetSnapshot
- Artifact / ArtifactVersion
- configuration / environment provenance represented by `ArtifactVersion` roles (`configuration`, `environment_manifest`)

Acceptance criteria:

- each Run resolves exact frozen material inputs
- Dataset or Artifact current-version changes do not alter old Run provenance
- content hashes can detect material artifact changes

### Phase 1D — Measurement and evidence

Deliver:

- MetricDefinitionVersion
- Measurement
- StatisticalResult
- EvidenceRelation

Acceptance criteria:

- Claim can be traced to Measurement / StatisticalResult / Run
- changing MetricDefinition creates a new definition version
- recalculation creates new Measurement / StatisticalResult rather than mutating historical values

### Phase 1E — Basic audit and impact propagation

Deliver:

- AuditFinding
- ImpactAssessment
- simple stale/invalid impact relations or projections
- CorrectionRecord

Acceptance criteria:

- mark an upstream dataset/run/result issue and identify downstream affected evidence/claims
- no audit script directly overwrites canonical Measurement or Run history
- corrected current projections preserve original historical records

### Phase 1F — End-to-end provenance demo

Demonstrate:

```text
HypothesisVersion
→ ExperimentSpecVersion
→ Run
→ DatasetSnapshot / ArtifactVersion
→ Measurement
→ StatisticalResult
→ EvidenceRelation
→ ClaimVersion
```

The demo must prove reverse traceability from ClaimVersion to the exact Run and material inputs.

## 8. Mandatory Phase 1 Architecture Tests

The following are not optional unit-test ideas; they are architecture acceptance tests.

### 8.1 Frozen reference test

Create Run R against ExperimentSpecVersion E1. Create E2. Verify R still resolves E1.

### 8.2 Dataset contamination test

Run R uses DatasetSnapshot D1. Update Dataset current state to D2. Verify R provenance remains D1.

### 8.3 Artifact contamination test

Run R uses ArtifactVersion A1. Create A2. Verify R still resolves A1.

### 8.4 No RunVersion test

Rerunning the same ExperimentSpec creates R2, not R1 version 2.

### 8.5 Measurement immutability test

If Measurement M1 is wrong, correction/invalidation creates new canonical result/provenance without rewriting M1.

### 8.6 Frozen Provenance Closure test

Traverse all material dependencies of a formal provenance object. Fail if any unresolved `current` or `latest` dependency is encountered.

### 8.7 One source-of-truth test

Verify Project, Claim, Dataset, Publication, etc. do not store duplicated canonical reverse-navigation state as independently mutable fields.

### 8.8 Fact precedence test

A DecisionRecord or future approval-like state must not cause a deterministic audit failure to be marked scientifically correct.

## 9. Phase 1 Non-goals

Do not implement:

- full manuscript editor
- full publication submission lifecycle
- venue automation
- full citation management
- autonomous scientific approval
- full P0–P4 authority engine
- RBAC/IAM platform
- delegation engine
- appeal workflow
- COI workflow
- IRB/ethics management platform
- financial ERP
- budget/procurement/accounting
- full authorship dispute workflow
- microservices
- full CQRS/event sourcing
- autonomous reviewer replacement

## 10. Phase 2 Candidate Scope

Phase 2 may add, in priority order:

- DecisionRecord
- Publication / ManuscriptVersion / SubmissionVersion
- ScientificConclusion
- InternalReviewRecord
- ApprovalRequest / ApprovalDecision / ApprovalGrant
- RoleAssignment / Membership / ResponsibilityAssignment
- CitationContext / CitationAudit
- NoveltyAssessment
- AuthorshipSnapshot / AuthorConsent
- Incident
- richer CorrectionRecord workflows

Phase 2 must still follow the architecture complexity budget.

## 11. Deferred / Interface-only Scope

Keep architecture-compatible interfaces only for:

- complete P0–P4 authority engine
- delegation
- appeals
- advanced COI
- funding/budget/cost accounting
- ethics/IRB workflows
- external submission connectors
- full RACI
- complex organization hierarchy
- financial disclosures
- advanced authorship dispute resolution

No Phase 1 work item should depend on these being fully implemented.

## 12. Engineering Rules

### 12.1 Modular monolith

Use package boundaries, typed interfaces, repositories, and dependency tests. Do not split into services.

### 12.2 Relational database first

Use relational integrity for canonical internal references. External references remain soft.

### 12.3 No universal object table

Do not implement a single `objects(id, type, payload_json)` store as the primary domain model.

### 12.4 No semantic dumping into JSON

Structured metadata may exist, but core provenance, version, identity, and scientific relations must remain typed.

### 12.5 No cascade deletion of scientific history

Prefer retirement, supersession, archival, tombstone, correction, and redaction.

### 12.6 No premature agent layer

Agents must be built on top of trusted provenance infrastructure, not used as a substitute for it.

## 13. Implementation Deliverables

Phase 1 deliverables should include:

- source package with modular domain boundaries
- relational schema/migrations
- typed domain models
- core repositories/services
- provenance traversal API
- basic audit/impact propagation
- architecture invariant test suite
- CLI or minimal API for the six Phase 1 user capabilities
- end-to-end provenance demonstration

## 14. Phase 1 Exit Criteria

Phase 1 is complete only when all of the following pass:

1. ClaimVersion can be reverse-traced to exact Run(s).
2. Run(s) resolve deterministic DatasetSnapshot and ArtifactVersion inputs.
3. Old Run provenance is unaffected by newer dataset/artifact/spec versions.
4. Measurement and StatisticalResult history is immutable.
5. Frozen Provenance Closure test passes.
6. Upstream invalidation can identify downstream affected ClaimVersions.
7. No duplicate canonical source-of-truth relationships are introduced.
8. Architecture invariant tests pass.
9. No deferred administrative/governance system has been accidentally pulled into the MVP.

## 15. Phase 0 Review Checklist

Before approving Phase 1, confirm:

- [ ] `architecture.md` reflects intended ResearchBase philosophy.
- [ ] Phase 1 scope is small enough to implement reliably.
- [ ] Phase 1 non-goals are acceptable.
- [ ] Hypothesis / ExperimentSpec / Run / Measurement / Claim boundaries are correct.
- [ ] FrozenReference semantics are acceptable.
- [ ] Frozen Provenance Closure is accepted as a hard invariant.
- [ ] Governance is intentionally thin in Phase 1.
- [ ] No important must-have capability has been deferred accidentally.

## 16. STOP

After delivery of these Phase 0 documents, stop.

Do not begin Phase 1 implementation until explicit GO approval is given.

---

# 附录 C：Phase 0 历史冻结版 schema_registry.md（审计留档）

# ResearchBase Phase-0 Schema Registry

## 1. Purpose

This registry summarizes the canonical object classes, supporting patterns, reference rules, and major invariants frozen during Phase 0. It is intentionally more implementation-oriented than `architecture.md`, but it is not a complete database DDL.

## 2. Object Classification

### 2.1 Long-lived Identity Entities

| Object | Owning Domain | Default Navigation | Notes |
|---|---|---|---|
| Project | organization | Live | governance/provenance scope |
| Workspace | organization | Live | identity separate from storage path |
| Organization | organization | Live | hierarchy does not imply unrestricted authority |
| ActorIdentity | identity | Live | Human/Agent/Service/External classification |
| Dataset | evidence | Live | long-lived dataset identity |
| Artifact | evidence | Live | generic code/model/config/figure/report identity |
| LiteratureSource | literature | Live | stable scholarly-work identity |
| Publication | publication | Live | long-lived publication effort |
| Grant | resources | Live/Frozen | light implementation only |
| ResourcePool | resources | Live | compute/storage/service resource identity |

### 2.2 Version Identities

| Object | Owning Domain | Formal Reference Rule |
|---|---|---|
| ResearchQuestionVersion | research | Frozen |
| HypothesisVersion | research | Frozen |
| ClaimVersion | research | Frozen |
| ScientificConclusionVersion | research | Frozen |
| ExperimentSpecVersion | experiment | Frozen |
| DatasetVersion | evidence | Frozen when used formally |
| ArtifactVersion | evidence | Frozen |
| MetricDefinitionVersion | evidence | Frozen |
| SourceVersion | literature | Frozen |
| ManuscriptVersion | publication | Frozen |
| SubmissionVersion | publication | Frozen |
| PolicyVersion | compliance/governance | Frozen |
| AgentVersion | identity | Frozen in execution provenance |

### 2.3 Immutable Facts / Records

| Object | Owning Domain | Correction Semantics |
|---|---|---|
| Run | experiment | new Run / CorrectionRecord |
| DatasetSnapshot | evidence | new Snapshot |
| Measurement | evidence | new Measurement + invalidate/correct old |
| StatisticalResult | evidence | new StatisticalResult |
| DecisionRecord | governance | new DecisionRecord |
| ApprovalRequest | governance | new request if target/scope changes |
| ApprovalDecision | governance | revocation/reconsideration, not rewrite |
| InternalReviewRecord | governance | new review for re-review |
| ImpactAssessment | governance | new assessment |
| AuthorConsent | publication | new consent for new material state |

### 2.4 Stateful Relation / Governance Entities

| Object | Domain | Notes |
|---|---|---|
| Membership | organization | scoped, temporal |
| RoleAssignment | organization/governance | role != authority |
| ResponsibilityAssignment | organization | responsibility != authority |
| OwnershipAssignment | organization | ownership != authority/accountability |
| Incident | governance | lifecycle + append-only events |
| ApprovalGrant | governance | current usable authorization |
| ResourceReservation | resources | reservation != execution |

## 3. Core Phase 1 Entities

Phase 1 should concentrate on approximately the following canonical objects:

```text
ActorIdentity
Project
Workspace

ResearchQuestion
ResearchQuestionVersion
Hypothesis
HypothesisVersion
Claim
ClaimVersion

ExperimentSpec
ExperimentSpecVersion
Run

Dataset
DatasetSnapshot
Artifact
ArtifactVersion
MetricDefinition
MetricDefinitionVersion
Measurement
StatisticalResult
EvidenceRelation

LiteratureSource
SourceVersion

AuditFinding
ImpactAssessment
CorrectionRecord
```

ScientificConclusion, Publication/Manuscript, and DecisionRecord are Phase 2 by default. LiteratureSource/SourceVersion are optional Phase 1 extensions and do not block Phase 1 exit.

## 4. Reference Types

### 4.1 FrozenReference<T>

Conceptual structure:

```yaml
FrozenReference:
  object_id: UUID
  version_id: UUID|null
  content_hash: ContentHash|null
```

Use when historical identity matters.

### 4.2 LiveReference<T>

Conceptual structure:

```yaml
LiveReference:
  object_id: UUID
```

Use for current-state navigation only.

### 4.3 ExternalReference

Use for DOI, ORCID, external URLs, provider IDs, repository URLs, external dataset identifiers, etc.

External references do not use internal FK semantics.

## 5. Frozen Provenance Closure

A formal provenance object must not contain unresolved `current` or `latest` dependencies in its material provenance graph.

Typical required frozen edges:

```text
Run → ExperimentSpecVersion
Run → DatasetSnapshot
Run → ArtifactVersion
Run → ConfigurationSnapshot
Run → EnvironmentSnapshot
Measurement → Run
Measurement → MetricDefinitionVersion
StatisticalResult → exact analysis/measurement inputs
ClaimVersion → exact EvidenceRelation inputs
DecisionRecord → exact DecisionBasis inputs
ApprovalDecision → exact frozen target
SubmissionVersion → exact ManuscriptVersion/Authorship/figures/tables/citations
```

## 6. Canonical Relationship Rules

### 6.1 No reverse mutable duplication

Avoid canonical mutable fields such as:

```text
Project.claims[]
Claim.published_in[]
Dataset.experiments[]
```

Reverse navigation should be query/projection driven.

### 6.2 One owning domain per fact

Examples:

```text
Actor identity       → identity
Project lifecycle    → organization
Hypothesis / Claim   → research
Run                  → experiment
Measurement          → evidence
Literature source    → literature
Manuscript           → publication
Decision / Approval  → governance
Consent / DataZone   → compliance
Resource usage       → resources
```

## 7. Supporting Schema Patterns

### 7.1 Relation Entity Pattern

Examples:

- EvidenceRelation
- ProjectResourceRelation
- Membership
- RoleAssignment
- OwnershipAssignment
- ResponsibilityAssignment
- CrossProjectAccessGrant
- WorkspaceAccessGrant
- CorrespondingAuthorAssignment
- ExternalIdentityLink

These may have IDs and audit provenance but are not automatically aggregate roots.

### 7.2 Assessment Pattern

Common conceptual fields:

```yaml
AssessmentProtocol:
  target_ref: FrozenReference
  assessor_ref: ActorRef
  evidence_refs: [FrozenReference]
  policy_refs: [FrozenReference]
  result: typed result
  rationale: string
  confidence: optional
  assessed_at: Instant
```

Examples:

- ImpactAssessment
- NoveltyAssessment
- AuthorshipEligibilityAssessment
- FinancialConflictAssessment
- ConsentReuseAssessment

Keep domain-specific types separate rather than implementing one universal Assessment table.

### 7.3 Assignment Pattern

Common structure:

```yaml
AssignmentProtocol:
  actor_ref
  target_ref
  assignment_type
  scope
  effective_from
  effective_until
  source_ref
  status
```

Role, Responsibility, Ownership, and ScientificAccountability may share implementation helpers but must remain semantically distinct.

### 7.4 Snapshot Pattern

Examples:

- DatasetSnapshot
- configuration / environment provenance represented by `ArtifactVersion` roles (`configuration`, `environment_manifest`) logical concepts (Phase 1 persisted as typed ArtifactVersion roles)
- AuthorshipSnapshot
- AuthorityContext

Formal snapshots are immutable once used in governed provenance.

### 7.5 Event Pattern

Examples:

- RunStarted
- RunCompleted
- ApprovalGranted
- CredentialRevoked
- ConsentWithdrawn
- SubmissionSent
- OwnershipTransferred

Phase 1 uses append-only event/audit records where useful, but does not adopt full event sourcing.

### 7.6 Derived View Pattern

Examples:

- current authority profile
- latest manuscript
- current project members
- remaining budget
- current claim status
- dashboards

Derived views are never the sole canonical source of truth.

## 8. Generic Provenance Envelope

Conceptual helper:

```yaml
ProvenanceEnvelope:
  created_by: ActorRef
  created_at: Instant
  source_refs: [Reference]
  schema_version: SemVer
  content_hash: ContentHash|null
  provenance_metadata: StructuredValue|null
```

Not every table must literally inherit every field, but provenance semantics should be consistent.

## 9. CorrectionRecord

Conceptual schema:

```yaml
CorrectionRecord:
  id: UUIDv7
  target_ref: FrozenReference
  correction_type:
    factual | metadata | computational | attribution | other
  prior_assertion: StructuredValue|null
  corrected_assertion: StructuredValue
  reason: string
  basis_refs: [FrozenReference]
  created_by: ActorRef
  created_at: Instant
```

A correction does not erase the original historical record.

## 10. Core Scientific Invariants

### SCI-001
ExperimentSpec and Run are distinct. ExperimentSpec states what should happen; Run records what actually happened.

### SCI-002
Rerun creates a new Run, never a RunVersion.

### SCI-003
Hypothesis, Claim, and ScientificConclusion remain distinct.

### SCI-004
Formal Claim support must be traceable to governed evidence.

### SCI-005
Measurement and StatisticalResult are immutable scientific records.

### SCI-006
Metric semantics are versioned through MetricDefinitionVersion.

### SCI-007
Formal Runs must resolve deterministic immutable input state.

### SCI-008
Dataset/Artifact updates must not contaminate historical Run provenance.

### SCI-009
Project archival or Publication withdrawal must not delete underlying evidence history.

## 11. Core Governance Invariants

### GOV-001
Deterministic canonical facts take precedence over Review, Decision, and Approval states.

### GOV-002
Review evaluates; Decision chooses; Approval authorizes; Command executes; ExternalEffect records external change.

### GOV-003
P0–P4 are policy taxonomy labels, not a scalar privilege ladder.

### GOV-004
Independent authority requirements compose as AND constraints.

### GOV-005
P4 scientific approval is Human by default and cannot be delegated to an Agent under default policy.

### GOV-006
`acting_on_behalf_of`, Role, ProjectOwner, CorrespondingAuthor, Reviewer, or WorkspaceManager do not implicitly transfer unrelated authority.

### GOV-007
Approval scope may be narrowed but not silently broadened.

### GOV-008
Review/Audit findings do not directly mutate scientific facts.

### GOV-009
COI and Authority are context-dependent, not global actor booleans.

### GOV-010
P3 external actions require governed logical-action/idempotency/external-effect semantics when implemented.

### GOV-011
Unknown external outcomes must be reconciled before blind retry.

### GOV-012
Approval rejection cannot be bypassed by approver shopping or materially equivalent object recreation.

### GOV-013
Approval rejection is not itself scientific invalidity.

### GOV-014
ScientificAccountability, Review responsibility, and Approval authority remain independently assignable.

## 12. Identity Invariants

- Identity != Identifier != Account != Role != Authority != Credential.
- AgentActor != ServiceActor.
- ActorIdentity != AgentExecutionInstance.
- Reviewer / Approver / PI / Owner are contextual assignments/roles, not separate Human subclasses.
- Human approval does not erase Agent provenance.
- Shared identifiers/credentials must not force fabricated Human identity attribution.

## 13. Publication Invariants

- Publication != ManuscriptVersion != SubmissionVersion.
- SubmissionVersion is a frozen record of what was actually sent externally.
- Historical submission versions are never overwritten by revisions.
- VenueReviewRecord and InternalReviewRecord remain distinct.
- Citation placement does not itself establish scientific support.
- Authorship is distinct from project membership, role, scientific accountability, and P4 approval.

Most publication governance remains Phase 2.

## 14. Resource and Compliance Boundaries

### Resources

Resource access does not imply DataZone permission. Reservation does not imply Run execution. Budget/cost does not determine scientific validity.

### Compliance

Data access does not imply ethical permission. Internal P4/PI approval does not replace IRB, data-owner, or external authority.

Both domains remain intentionally thin in early phases.

## 15. Deleted / Consolidated Concepts

The following concepts are intentionally not retained as independent canonical entities:

```text
WorkflowRun                  → Run(run_type + parent/child)
LiteratureRecord             → LiteratureSource + SourceVersion
generic PublicationVersion   → ManuscriptVersion / SubmissionVersion / PublishedVersion
DataZoneVersion              → stable DataZone + PolicyVersion by default
RunVersion                   → forbidden
MeasurementVersion           → forbidden
StatisticalResultVersion     → forbidden
DecisionVersion              → forbidden
ApprovalDecisionVersion      → forbidden
ReviewRecordVersion          → forbidden
```

## 16. Architecture Complexity Budget

Before adding any new top-level schema, answer:

1. Can an existing canonical Entity express the identity?
2. Can a Relation express the connection?
3. Can an Assessment express the judgment?
4. Can a Snapshot express the frozen state?
5. Can an Event express the change?

Only if all five are inadequate should a new canonical schema be considered.

## 17. Phase 1 Registry Freeze

Phase 1 should not expand the canonical registry unless a blocker is demonstrated and documented.

Any proposed new canonical entity during Phase 1 requires an architecture change note and explicit review against the Complexity Budget.

---

# Appendix H — Harness Integration Architecture (v1.0)

## H.1 Status and Scope

This appendix is normative for agent-assisted development and later scientific-agent execution. It does **not** reopen the canonical scientific schema, Phase-1 provenance semantics, or the Architecture Complexity Budget. The canonical architecture remains the source of truth for scientific state; the harness governs how agents work around that state.

## H.2 Four-Layer Model

```text
L4  Scientific Research Harness
    ResearchBase-owned scientific Skills / strategies / auditors

L3  Software Engineering Harness
    approved external engineering workflows, review, TDD, debugging, security

L2  Agent / Harness Runtime
    Codex Skills, Plugins, Subagents, Hooks, MCP, routing, capability policy

L1  ResearchBase Canonical System
    Domain + Application Command/Query + persistence + immutable provenance
```

**H-ARCH-INV-001** Harness state MUST NOT become a second source of canonical scientific truth.

**H-ARCH-INV-002** Skills, Plugins, Hooks, MCP servers and external harnesses MUST NOT directly mutate ResearchBase canonical persistence. All canonical writes converge on the existing Application Command boundary.

**H-ARCH-INV-003** ResearchBase architecture/safety/scientific-integrity invariants override conflicting third-party harness instructions.

## H.3 Engineering Harness vs Scientific Harness

Engineering Harness answers **how software is built and verified**: specification, planning, incremental implementation, TDD, debugging, independent review, security review, ADRs and completion evidence. Mature external harnesses SHOULD be reused where compatible.

Scientific Harness answers **how research is proposed, investigated and audited**: literature research, hypothesis scrutiny, experiment design, leakage audit, statistical audit, claim/evidence consistency, reproducibility and paper review. These capabilities are ResearchBase-owned and versioned.

A Skill is not a canonical scientific entity. A research strategy such as STORM/Co-STORM is not a Skill identity and is not a Core schema. Strategies are replaceable implementations selected by scientific Skills. EvoScientist-like systems remain workflow/runtime references or adapters, never owners of ResearchBase scientific state.

## H.4 Harness Dependency Governance

Repository-level configuration SHALL include:

```text
harness.lock.yaml
config/harness/skill_registry.yaml
config/harness/routing_policy.yaml
config/harness/capability_policy.yaml
```

Production-relevant external harness dependencies MUST be pinned to an immutable release, revision or content digest. `main`, `master`, `latest`, or an unversioned remote Skill MUST NOT be treated as a reproducible dependency.

The lock file is an engineering/reproducibility manifest, not canonical scientific state. When a harness materially participates in a Phase-3+ AgentExecution, its resolved fingerprint MUST be bound to that execution provenance.

## H.5 Harness Fingerprint

A material AgentExecution SHOULD be reconstructable from a `HarnessFingerprint` containing, where available:

```text
ResearchBase revision
Agent runtime revision
model/provider identifier
AGENTS.md content hash
config hash
Skill IDs + immutable versions/content hashes
Plugin revisions
relevant Hook revisions
MCP capability revisions
external engineering harness revisions
```

For Phase 1, coding-harness fingerprints belong to PR/development evidence only; they MUST NOT create a new scientific canonical object merely to record software-development tooling.

## H.6 Skill Registry and Routing

Every production ResearchBase Skill MUST declare at least:

```text
skill_id
version
owner
category
purpose/triggers
allowed_phases
required_inputs
produced candidate artifacts
allowed capabilities
forbidden capabilities
verification requirements
conflicts/precedence
```

Routing MUST be policy constrained rather than wholly model discretionary:

```text
Task classification
→ Phase / authority / capability filter
→ Skill candidates
→ conflict resolution
→ execution plan
→ execution
```

Instruction precedence for harness conflicts is:

```text
ResearchBase architecture & safety invariants
> scientific-integrity rules
> phase specification
> repository AGENTS.md
> ResearchBase scientific Skill
> approved external engineering Harness
> generic agent preference
```

Unresolvable conflicts STOP and create an Architecture/Engineering Question; the agent MUST NOT choose arbitrarily.

## H.7 Candidate Promotion Boundary

Scientific Skill output is candidate state by default.

```text
Skill output
→ candidate artifact/recommendation
→ validation/review
→ Application Command
→ canonical object
```

Therefore an experiment-design proposal is not an ExperimentSpecVersion; an auditor interpretation is not a StatisticalResult; a paper review is not a ScientificConclusion.

## H.8 Independent Review

Formal reviewer/auditor executions SHOULD be independent from authoring execution. Reviewer context SHOULD be reconstructed from authoritative specification, diff/artifacts, test evidence and relevant canonical state rather than inheriting the author agent's full conversational/reasoning history.

All formal findings use a common severity contract:

```text
P0 BLOCKER
P1 MAJOR
P2 MINOR
P3 SUGGESTION
```

A finding MUST be actionable and evidence-backed, including target/location, observation, violated rule or risk, impact and recommended action.

## H.9 Completion Evidence

Agent language such as `done`, `fixed`, or `all tests pass` is not evidence. Completion claims MUST be accompanied by machine-verifiable evidence appropriate to the change: tests, migration verification, architecture tests, lint/type checks, integration/E2E evidence, or explicit runtime inspection.

## H.10 Harness Evaluation and Supply Chain

ResearchBase-owned Skills MUST pass structural, trigger, behavior, regression, context/token and safety evaluation before release. Third-party Skills/Plugins/Hooks/MCP servers require source, license, revision, instruction/script and capability review before approval.

A running agent MUST NOT silently modify its own governing AGENTS.md, production Skills, routing/capability policy, harness lock, or required auditors and continue the same execution as trusted. Harness modification is a separate governed change.

## H.11 Initial Scientific Skill Registry

The initial bounded set is:

```text
RB-S01 research-question-refiner
RB-S02 literature-deep-research
RB-S03 literature-evidence-auditor
RB-S04 hypothesis-auditor
RB-S05 experiment-designer
RB-S06 experiment-protocol-auditor
RB-S07 statistical-auditor
RB-S08 result-claim-auditor
RB-S09 reproducibility-auditor
RB-S10 citation-auditor
RB-S11 paper-auditor
RB-S12 research-architecture-auditor
```

New Skills are rejected by default unless an existing Skill cannot express the trigger/responsibility cleanly through references, strategies or configuration.

## H.12 Phase Boundary

- **Phase 1:** Engineering Harness may assist implementation. No ResearchBase Agent Runtime is implemented.
- **Phase 2:** Scientific strategy layer and literature-oriented Skills may be implemented through existing Application boundaries. STORM-like strategy remains replaceable.
- **Phase 3:** Agent/Harness Runtime integration becomes canonical implementation scope: Skill routing, CapabilityGateway binding, CanonicalContext, Candidate Promotion, AgentExecution and HarnessFingerprint provenance.
- **Phase 4:** dynamic strategy/Skill selection and controlled Skill-evolution candidates may be added, but self-modification never bypasses evaluation and governed release.

## H.13 Architecture Principle

> **Borrow engineering intelligence. Own scientific methodology. Preserve canonical scientific truth.**

> **Agentic research is reproducible only when material code, data, environment and agent harness can be reconstructed.**

