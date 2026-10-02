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

---

# A17. Phase 2 Design Gap Closure (normative patch)

The Phase 2 architecture correction in `12_Phase2_Architecture_and_Contract_Correction_v1.0.md` and its field contract `13_Phase2_Schema_Field_Contract_v1.0.md` are incorporated into this Addendum for Phase 2 design review. They do not authorize implementation. In particular:

- Phase 2 literature functionality is required.
- `SubmissionVersion` retains the System Architecture meaning of a package actually sent externally and is deferred to the venue-submission extension. Phase 2's frozen *prepared* package is `PreparedSubmissionVersion`; no prepared package asserts that an external send occurred.
- The Global Registry's Phase 2 object rows and the Phase 2 correction's typed provenance, bootstrap, hash/material, governance, and schema contracts govern over conflicting older Phase 2 prose.
- Phase 2 PR2-00 bootstrap/membership precedes PR2-01 source identity. Neither PR is authorized by this design patch.
- PR2-01 contains source identity and identifiers only; SourceMergeRecord and MERGED aliasing move to PR2-02 source lineage. The older Phase 2 PR2-01 merge bullet is superseded so the first literature PR remains independently reviewable.

---

# A18. Phase 2 Design Gap Closure R2 (normative design patch)

The independently rejected A17/R1 proposal is preserved as historical evidence by `artifacts/phase2_design/R1_rejected_worktree.patch` and its manifest. At R2 start the eight R1 design files were uncommitted; the shared Git index was read-only, so no committed R1 checkpoint can be asserted. A18 makes the versioned R2 documents the proposed correction for a **new independent reauthorization review**. It does not itself authorize Phase 2, PR2-00, PR2-01, migrations, provider activation or production work.

For Phase 2 only, the precedence among the overlapping design texts is: System Architecture scientific invariants and frozen Phase 1 contracts → this Addendum A18 → `14_Phase2_Design_Gap_Closure_R2_v1.0.md` → its focused companions `15_Phase2_Hash_Payload_Contract_R2_v1.0.md`, `16_Phase2_Identity_Ownership_and_Source_Contract_R2_v1.0.md`, and `17_Phase2_Governance_Publication_and_Revision_Contract_R2_v1.0.md` in their respective subject areas → A17/R1 correction and field contract for unaffected Phase 2 details → Global Registry and Cross-Phase Contracts for unaffected names and invariants → older Phase 2 prose → PR execution packs. R2 design packs may narrow scope but cannot override these documents. If two R2 companions conflict, stop and correct the design; no implementer chooses one by convenience.

A18 incorporates ADR-0008 for TDG-2 technology decisions and ADR-0009 for the bounded Phase 2 `LiteratureSupportSnapshot` schema admission. The snapshot and its `LiteratureEvidenceRelation` children own Phase 2 literature support independently of the Phase 1 Claim `support_set_hash`, Claim `content_hash`, EvidenceRelation and closure verifier. R1 wording requiring literature relations to enter a Phase 1 target support binding or be sealed by the target's freeze is superseded. Phase 1 historical hashes and semantics remain exactly as frozen.

R2 companion 15 replaces R1's descriptive Phase 2 hash material and conflicting AuthorshipSnapshot ordering. Companion 16 replaces R1's bootstrap, legacy actor enrollment, OWNER interval and PR2-01 source identifier workflow details. Companion 17 replaces R1's approval, rejection, RevisionAction, current-consent and same-Publication package details. The versioned R2 PR2-00 and PR2-01 packs refine migration `0019` and `0020` respectively; they do not authorize either PR. `SubmissionVersion` still means an actually sent external package and remains deferred. `PreparedSubmissionVersion` never proves a send, and `CitationRelation` remains a noncanonical shorthand for manuscript citation placement.

The R2 schema admission is explicit and limited. For migration `0019`, the seven typed PR2-00 tables and the guard trigger on existing `actors.retired_at` described in companion 16 and its pack replace R1's statement that 0019 installs no Phase 1 table trigger. That trigger blocks only retirement that would violate the new Phase 2 continuous OWNER invariant for an enrolled project; it does not change ActorIdentity attribution, historical retirement values or a Phase 1 scientific lifecycle. For migration `0020`, the five typed PR2-01 tables in companion 16 and its pack replace the affected R1 source-identifier fields. For later separately authorized Phase 2 migrations, A18 admits `literature_support_snapshots` and snapshot-owned `literature_evidence_relations`; `approval_request_reviews`, `decision_basis_approval_decisions`, `decision_basis_revision_actions`; the concrete approval-request rejection/reconsideration FKs, grant-consumption result FKs, seven concrete RevisionAction result FKs, and same-Publication composite keys/FKs specified in companion 17. The matching hash material is exactly companion 15. These admissions are design contracts, not migrations; no general polymorphic provenance or additional schema is implied. The invalid R1 `(project_id,status)` search-plan identity index is replaced by the two indexes named in companion 14.

---

# A19. Phase 2 Design R3 targeted correction

`18_Phase2_Design_R3_Targeted_Remediation_v1.0.md` is the proposed normative Phase 2 design correction for the five R2 blocking gaps and three listed completeness items only. It supersedes conflicting R2 text only in its explicitly named clauses. All other A18/R2 corrections, especially Claim compatibility, TDG-2, authorship order, approval-purpose policy, rejection reconsideration, PreparedSubmission closure, Publication constraints, RevisionAction results, PR2-01 receipt structure and ScientificConclusion exact-version closure, retain their A18 precedence. The new typed challenge record, identifier binding-basis fields and grant-consumption receipt fields are the bounded schema admissions stated in R3. This is a design-review subject; it authorizes no Phase 2 PR, migration, production change or provider activation. Independent review of the committed subject is required before reauthorization can be considered.
