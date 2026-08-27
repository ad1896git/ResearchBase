# ResearchBase Global Schema and Contract Registry

> **版本**：v1.0  
> **状态**：NORMATIVE NAME / OWNERSHIP / LIFECYCLE REGISTRY  
> **日期**：2026-08-26  
> **用途**：为 Phase 1–4 提供唯一实体命名、Domain Ownership、生命周期和引用类别目录。字段细节仍以对应 Phase Specification 为准。

---

# 1. Object Categories

```text
IDENTITY
VERSION
IMMUTABLE_RECORD
STATEFUL_OPERATIONAL
DERIVED_MEMORY
WORKFLOW
```

---

# 2. Phase 1 Registry

| Object | Domain | Category | Lifecycle | Formal Ref Rule |
|---|---|---|---|---|
| ActorIdentity | identity | IDENTITY | stable/retirable | Live/ID |
| Project | organization | IDENTITY | ACTIVE/ARCHIVED/RETIRED | Live |
| Workspace | organization | IDENTITY | stateful | Live |
| ResearchQuestion | research | IDENTITY | stable | Live |
| ResearchQuestionVersion | research | VERSION | DRAFT→FROZEN→SUPERSEDED/ABANDONED | Frozen |
| Hypothesis | research | IDENTITY | stable | Live |
| HypothesisVersion | research | VERSION | same | Frozen |
| ExperimentSpec | experiment | IDENTITY | stable | Live |
| ExperimentSpecVersion | experiment | VERSION | same | Frozen |
| Dataset | evidence | IDENTITY | stable | Live |
| DatasetVersion | evidence | VERSION | OPTIONAL EXTENSION | Never sufficient alone for formal Run |
| DatasetSnapshot | evidence | IMMUTABLE_RECORD | immutable | Frozen/strong FK |
| Artifact | evidence | IDENTITY | stable | Live |
| ArtifactVersion | evidence | VERSION | DRAFT→FROZEN... | Frozen |
| MetricDefinition | evidence | IDENTITY | stable | Live |
| MetricDefinitionVersion | evidence | VERSION | DRAFT→FROZEN... | Frozen |
| Run | experiment | STATEFUL_OPERATIONAL | PLANNED→RUNNING→terminal | strong FK, inputs sealed |
| Measurement | evidence | IMMUTABLE_RECORD | immutable | strong FK |
| StatisticalResult | evidence | IMMUTABLE_RECORD | immutable | strong FK |
| Claim | research | IDENTITY | stable | Live |
| ClaimVersion | research | VERSION | DRAFT→FROZEN... | Frozen |
| EvidenceRelation | evidence/research boundary | IMMUTABLE_AFTER_FREEZE | Claim DRAFT-only edits | concrete source FK |
| AuditFinding | governance | STATEFUL_OPERATIONAL | OPEN... | validated cross-cutting locator |
| ImpactAssessment | governance | IMMUTABLE_RECORD | immutable | locator/typed refs |
| CorrectionRecord | governance | IMMUTABLE_RECORD | immutable | locator + content hash |

---

# 3. Phase 2 Registry

| Object | Domain | Category | Lifecycle | Formal Ref Rule |
|---|---|---|---|---|
| ProjectMembership | organization | STATEFUL_OPERATIONAL | ACTIVE/SUSPENDED/ENDED | concrete actor/project FK |
| ProjectRoleAssignment | organization | STATEFUL_OPERATIONAL | temporal | concrete FK |
| LiteratureSource | literature | IDENTITY | ACTIVE/MERGED/RETIRED | Live identity |
| SourceIdentifier | literature | IMMUTABLE/STATEFUL | verified | source FK |
| SourceVersion | literature | VERSION | DRAFT→FROZEN... | Frozen |
| LiteratureSearchPlan | literature | IDENTITY | stable | Live |
| LiteratureSearchPlanVersion | literature | VERSION | DRAFT→FROZEN... | Frozen |
| LiteratureSearchExecution | literature | STATEFUL_OPERATIONAL | PLANNED→terminal | plan version strong FK |
| SearchQueryRecord | literature | IMMUTABLE_RECORD | immutable | execution FK |
| SearchResultRecord | literature | IMMUTABLE_RECORD | immutable | query FK |
| LiteratureEvidence | literature | IMMUTABLE/REVIEWABLE | content immutable, verification state separate/controlled | SourceVersion strong FK |
| ResearchBrief | evidence/artifact | ArtifactVersion role | versioned artifact | Frozen artifact |
| DiscussionSession | collaboration | STATEFUL_OPERATIONAL | OPEN/CLOSED/ARCHIVED | project FK |
| DiscussionTurn | collaboration | IMMUTABLE_RECORD | append-only | session FK |
| ScientificConclusion | research | IDENTITY | stable | Live |
| ScientificConclusionVersion | research | VERSION | DRAFT→FROZEN... | Frozen input set |
| Publication | publication | IDENTITY | lifecycle | Live |
| ManuscriptVersion | publication | VERSION | DRAFT→FROZEN... | Frozen |
| InternalReviewRecord | governance | IMMUTABLE_RECORD | immutable | concrete frozen target |
| ReviewIssue | governance | STATEFUL_OPERATIONAL | OPEN/ADDRESSED/DISMISSED | review FK |
| DecisionRecord | governance | IMMUTABLE_RECORD | immutable/superseding | typed basis relations |
| ApprovalRequest | governance | IMMUTABLE_RECORD-ish | PENDING→DECIDED/WITHDRAWN | concrete frozen target |
| ApprovalDecision | governance | IMMUTABLE_RECORD | immutable | request FK |
| ApprovalGrant | governance | STATEFUL_OPERATIONAL | ACTIVE/CONSUMED/EXPIRED/REVOKED/STALE | decision FK |
| SubmissionVersion | publication | VERSION/IMMUTABLE_SNAPSHOT | PREPARED→FROZEN→SUPERSEDED | Frozen closure |
| AuthorshipSnapshot | publication | IMMUTABLE_SNAPSHOT | frozen | Submission strong FK |
| PriorArtRelation | literature | IMMUTABLE_RECORD | immutable assessment | claim/source FKs |
| SearchCoverage | literature | IMMUTABLE_ASSESSMENT | immutable | relation tables |

---

# 4. Phase 3 Registry

| Object | Domain | Category | Lifecycle | Formal Ref Rule |
|---|---|---|---|---|
| ResearchTask | agent_runtime | WORKFLOW | CREATED→...→terminal | project FK |
| ResearchTaskStep | agent_runtime | WORKFLOW | PENDING→terminal | task FK |
| AgentVersion | agent_runtime/identity | VERSION | immutable content | execution strong FK |
| AgentAvailability | agent_runtime | STATEFUL_OPERATIONAL | ACTIVE/DISABLED/RETIRED | AgentVersion FK |
| AgentExecutionInstance | agent_runtime | IMMUTABLE_AFTER_TERMINAL | CREATED→terminal | task/agent FKs |
| CapabilityInvocation | agent_runtime | STATEFUL_OPERATIONAL | REQUESTED→terminal/UNKNOWN | execution FK |
| AgentPromotionRecord | agent_runtime | IMMUTABLE_RECORD | immutable | execution FK + validated exact promoted target |
| HumanCheckpoint | agent_runtime/governance | STATEFUL_OPERATIONAL | PENDING→terminal | task FK |
| ExecutionBudget | agent_runtime | STATEFUL_POLICY | usage monotonic | task/program FK |
| TerminationPolicy | agent_runtime | VERSION/POLICY | immutable policy version | task FK |
| AgentToolPolicy | governance/runtime | VERSION/POLICY | immutable version | AgentVersion/task FK |
| ExperimentSearchSession | agent_runtime | STATEFUL_OPERATIONAL | ACTIVE→terminal | task FK |
| ExperimentSearchNode | agent_runtime | STATEFUL_OPERATIONAL | PROPOSED→terminal | session/parent FK |
| SearchDecisionRecord | agent_runtime | IMMUTABLE_RECORD | immutable | session FK |
| SemanticImpactAssessment | governance | IMMUTABLE_ASSESSMENT | immutable | target locator + proposed artifact |
| WorkingMemorySnapshot | evidence/artifact | ArtifactVersion role | immutable artifact | task/execution ref |

---

# 5. Phase 4 Registry

## Phase4-Core

| Object | Domain | Category | Lifecycle |
|---|---|---|---|
| ResearchProgram | programs | WORKFLOW | PLANNED→terminal |
| ResearchProgramMilestone | programs | WORKFLOW | PENDING→terminal |
| ProgramCheckpoint | programs | IMMUTABLE_RECORD | immutable |
| Skill | skills | IDENTITY | ACTIVE/DEPRECATED/RETIRED/BLOCKED |
| SkillVersion | skills | VERSION | immutable content |
| SkillQualification | skills | STATEFUL_OPERATIONAL | UNTESTED/EVALUATED/ACCEPTED/REJECTED/REVOKED |
| SkillEvaluation | skills | IMMUTABLE_ASSESSMENT | immutable |
| StrategyPortfolio | strategy | IDENTITY/CONFIG | version/config controlled |
| StrategyEvaluation | strategy | IMMUTABLE_ASSESSMENT | immutable |
| MemoryItem | research_memory | DERIVED_MEMORY | ACTIVE/STALE/INVALID/RETIRED |
| AutonomyEscalationRequest | governance | STATEFUL_OPERATIONAL | pending→decision |
| GoalAlignmentAssessment | governance | IMMUTABLE_ASSESSMENT | immutable |
| AgentSystemEvaluation | evaluation | IMMUTABLE_ASSESSMENT | immutable |

## Phase4-Pack-A Scale

```text
ExperimentCampaign
ExperimentCampaignBatch
AdaptiveSearchLedger
```

## Phase4-Pack-B Scientific Assurance

```text
ReplicationTask
ReplicationAssessment
NoveltySearchCampaign
ReviewEnsemble
```

---

# 6. Execution Naming Registry

```text
Run
  Formal scientific/computational execution.

LiteratureSearchExecution
  Literature retrieval execution.

AgentExecutionInstance
  One agent-role execution.

CapabilityInvocation
  One tool/capability call.

Compute external job
  External handle owned by CapabilityInvocation; not a new canonical *Run.
```

---

# 7. Reference Classes

## STRONG_CANONICAL_REFERENCE

Use for:

```text
formal scientific inputs
version inputs
Evidence/Claim support
Conclusion inputs
Manuscript scientific placement
Review/Approval target
Agent Promotion output
Replication target
campaign/search Run linkage
```

Persistence:

```text
concrete FK / typed relation table
```

## OPERATIONAL_OBJECT_LOCATOR

Use for:

```text
cross-cutting audit
working memory
generic diagnostics
tool trace metadata
```

Shape:

```yaml
object_type
object_id
version_id|null
content_hash|null
```

Not allowed as the sole Frozen Provenance Closure edge.

---

# 8. Canonical Collection Rule

If a specification writes:

```text
claim_version_ids[]
run_ids[]
input_refs
source_refs
```

and elements are canonical objects:

```text
Persistence MUST use relation rows.
```

JSON arrays are allowed only for derived/operational non-authoritative metadata.

---

# 9. Persisted Enum Rule

Canonical persisted enum names:

```text
UPPER_SNAKE_CASE
```

Examples:

```text
DRAFT
FROZEN
RUNNING
SUCCEEDED
ACTIVE
REVOKED
WAITING_HUMAN
TERMINATED_BUDGET
```

---

# 10. Storage Contract Registry

```text
PostgreSQL
= canonical relational state

ArtifactStore
= immutable large bytes/content-addressed artifacts

Vector/Search Index
= derived/rebuildable

Agent Runtime Checkpoint
= operational/rebuildable from ResearchTask + artifacts where possible

Sandbox Workspace
= temporary/non-canonical until ArtifactVersion registration
```

---

# 11. Deferred Capability Registry

Not required for Phase1–4 Core exit:

```text
Full Authority/Delegation/COI/Appeal Engine
Full IRB/Consent workflow
Full Grant/Resource/Cost platform
Venue Submission / Formal ExternalEffect connectors
Enterprise IAM
```

These are Optional Extension Specifications.

---

# 12. Schema Change Rule

Any object not present in this Registry requires:

```text
Architecture Change Note
or ADR if canonical
```

Renaming an object requires migration/compatibility note.

This Registry is the naming authority for implementation.
