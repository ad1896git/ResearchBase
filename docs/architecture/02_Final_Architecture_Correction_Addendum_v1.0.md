# ResearchBase Final Architecture Correction Addendum

> **版本**：v1.0  
> **状态**：NORMATIVE PATCH TO SYSTEM DESIGN  
> **日期**：2026-08-26  
> **适用**：全系统架构 v1.2、Phase 1 v1.1、Phase 2 v1.0、Phase 3 v1.0、Phase 4 v1.0、Cross-Phase v1.0  
> **优先级**：若原文与本 Addendum 冲突，以本 Addendum 为准，直到对应主文档升版吸收修订。

---

# A1. Agent Promotion Record

Phase 3 MUST 新增 immutable `AgentPromotionRecord`，确保 Agent candidate→canonical 可追溯。

```yaml
AgentPromotionRecord:
  id: UUID
  research_task_id: UUID
  agent_execution_id: UUID
  candidate_artifact_version_id: UUID|null

  promoted_object_type: string
  promoted_object_id: UUID
  promoted_object_version_id: UUID|null
  promoted_object_content_hash: SHA256|null

  promotion_command: string
  promotion_mode:
    AGENT_POLICY |
    HUMAN_CONFIRMED |
    HUMAN_CREATED_FROM_CANDIDATE |
    AUTOMATIC_UNDER_POLICY

  promoted_by: ActorId
  promoted_at: Instant
  policy_snapshot_hash: SHA256|null
```

Promotion 与 canonical create/revise command 在同一 application transaction 中记录。

---

# A2. Execution Naming

Phase 2 全部：

```text
LiteratureSearchRun
```

重命名为：

```text
LiteratureSearchExecution
```

永久区分：

```text
Run                       scientific/computational formal execution
LiteratureSearchExecution retrieval execution
AgentExecutionInstance    agent execution
CapabilityInvocation      tool/capability execution
```

---

# A3. Formal Target References

Phase 2 ApprovalRequest 不允许 generic `target_type + target_id` 作为唯一 Formal target。

使用 concrete FK + XOR。

InternalReviewRecord 对已知 target 类型同样使用 concrete target relations/nullable FKs。

---

# A4. Reference Persistence Classes

定义：

```text
STRONG_CANONICAL_REFERENCE
OPERATIONAL_OBJECT_LOCATOR
```

Strong canonical refs：

```text
formal scientific inputs
promotion outputs
review/approval targets
replication targets
campaign Run links
```

MUST relation table / concrete FK。

Operational locator 可用于横切 trace/log/working-memory metadata，但不得承担 Frozen Provenance Closure 关键边。

---

# A5. Phase 2 Minimal Identity/Authorization

Phase 2 MUST 增：

```text
ProjectMembership
ProjectRoleAssignment
```

最小角色：

```text
OWNER
RESEARCHER
REVIEWER
APPROVER
VIEWER
```

这不是完整 P0–P4 engine。

---

# A6. ArtifactStore

Phase 1 MUST 增：

```python
class ArtifactStore(Protocol):
    def put_verified(...): ...
    def open(...): ...
    def exists(...): ...
    def verify(...): ...
```

Reference backends：

```text
DEV_LOCAL → content-addressed filesystem
TEAM/HPC  → S3-compatible
```

Artifact identity = content hash + ArtifactVersion，不是 locator。

---

# A7. DatasetVersion Status

```text
DatasetVersion = OPTIONAL EXTENSION
DatasetSnapshot = REQUIRED FORMAL DATA INPUT
```

Formal Run：

```text
Dataset → [DatasetVersion optional] → DatasetSnapshot → Run
```

禁止 Run 仅指向 mutable Dataset/current DatasetVersion。

---

# A8. Deferred Capability Profile

Phase 1–4 Core completion 不要求：

```text
full Authority/Delegation/COI/Appeal
full IRB/Consent platform
full Resource/Cost system
venue submission ExternalEffect connectors
```

这些进入独立 Optional Extension Specifications。

总架构的 Domain 边界继续保留。

---

# A9. Phase 4 Scope Split

Phase4-Core MUST：

```text
ResearchProgram/Milestone
Skill Registry/Evaluation/Rollback
Strategy Evaluation/Selection
Research Memory
Autonomy Escalation
Kill Switch
Long-Horizon Checkpoint
Meta-Evaluation
```

Capability Packs：

```text
Pack-A Scale:
  ExperimentCampaign
  AdaptiveSearchLedger

Pack-B Scientific Assurance:
  Replication
  Advanced Novelty
  Reviewer Ensemble

Pack-C Self-Improvement:
  online strategy learning
  agent-generated skill automation
  automatic tool composition
```

Pack A/B SHOULD，Pack C MAY。

---

# A10. Canonical ID Collection Persistence

文档中的任何：

```text
*_ids[]
input_refs
output_refs
source_refs
run_ids
```

只表示 conceptual cardinality。

若引用 canonical objects：

```text
MUST relation tables
```

除非字段被明确标记 `OPERATIONAL_JSON`.

---

# A11. Version Content vs Availability

推荐新增：

```text
AgentAvailability
SkillQualification
```

而：

```text
AgentVersion
SkillVersion
```

保持 material content immutable。

---

# A12. Enum Policy

Persisted canonical enum：

```text
UPPER_SNAKE_CASE
```

新值只能新增，不重用旧值表达新语义。

---

# A13. Technology Decision Gates

任何 Phase 开工前完成对应 TDG。

```text
TDG-1 Phase1:
  PostgreSQL
  ArtifactStore
  API/CLI
  deployment profile

TDG-2 Phase2:
  search providers
  fulltext extraction
  PaperQA2 pin
  STORM adapter pin

TDG-3 Phase3:
  runtime framework
  queue/worker
  sandbox
  compute
  CodingCapability

TDG-4 Phase4:
  memory/vector backend
  evaluation harness
  campaign scheduling profile
```

结果必须 ADR 化。

---

# A14. Operational Tool Effect vs Governed External Effect

```text
Operational Tool Effect
= sandbox, compute job, workspace mutation
= CapabilityInvocation + ToolPolicy + external handle/reconciliation

Governed External Effect
= publish, venue submit, release data, formal external write
= ApprovalGrant → Command → ExternalEffect
```

二者不能混用。

---

# A15. Deployment Profiles

```text
DEV_LOCAL
TEAM_SINGLE_NODE
HPC_RESEARCH
```

所有 Profile 共享同一 Domain/Application semantics。

---

# A16. Final Implementation Gate Patch

Cross-Phase Implementation Start Gate 增加：

```text
[ ] Final Correction Addendum accepted
[ ] Global Schema Registry accepted
[ ] TDG-1 completed
[ ] ArtifactStore contract accepted
[ ] Promotion provenance patch accepted
```

满足后才：

```text
IMPLEMENTATION_GO_PHASE1 = TRUE
```
