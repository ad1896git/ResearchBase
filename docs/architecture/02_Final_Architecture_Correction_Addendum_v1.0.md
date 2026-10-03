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

# A20. Phase 2 Design R4 temporal authorization correction

`19_Phase2_Design_R4_Temporal_Authorization_Remediation_v1.0.md` is the proposed normative correction solely for expiry-sensitive Phase 2 authorization. TEMP-AUTH-01 supersedes R3 and R2 references to transaction-start time as the final expiry-sensitive decision time. Its completed-receipt replay rule supersedes R3's instruction to recheck effect authorization on an exact completed grant replay; caller authentication and receipt-scope matching still apply. All R3 canonical payloads, hash vectors, identifier provenance, publication/governance tuples and other Phase 2 contracts remain unchanged. This design correction authorizes no Phase 2 implementation, migration or PR. Only independent review of the committed R4 subject may assess readiness for human Phase 2 reauthorization.

# A21. Governance grant receipt replay read entitlement (P2 disposition)

This is a bounded policy clarification of R4's completed `ApprovalGrantConsumption` receipt replay, owned by the later governance Application read boundary. After the authenticated actor/project, command key, R3 canonical request hash and normalized command scope identify an exact durable completed receipt, returning its saved IDs/DTO also requires the caller's **current project read entitlement**: an ACTIVE membership, an effective role permitted to read that governance result, and a live verified credential, evaluated at fresh trusted time under TEMP-AUTH-01 where time-sensitive. A caller who lacks that entitlement receives `FORBIDDEN` (403) with no saved result disclosure. A caller with no valid authenticated principal receives `AUTHENTICATION_REQUIRED` (401). Receipt identity and a changed-hash `IDEMPOTENCY_CONFLICT` remain unchanged; no current grant/effect authorization is required for an allowed historical read. A denied replay never re-executes the original mutation and never starts a new one. This resolves the R4 independent review's one P2 read-entitlement ambiguity without changing R3 request material, hash vectors or R4 first-time effect semantics. PR2-00 does not implement governance grant consumption or this replay query; its pack records the boundary for the later separately authorized governance PR. For PR2-00 migration planning, A19/R3's eighth challenge table supersedes A18's historical seven-table proposal. This addendum grants no Phase 2 implementation authorization.

# A22. PR2-00 legacy-state preflight and temporal evidence clarification

This bounded clarification resolves the unspecified PR2-00 invalid-legacy-state migration preflight and makes R4 cross-expiry evidence observable. It does not change TEMP-AUTH-01 authorization semantics, Phase 1 semantics, the eight-table 0019 inventory, or the R2 actor/bootstrap/enrollment policy.

## LEGACY-STATE-01 — deterministic PR2-00 legacy-state predicate

For the 0019 migration from frozen revision `0018_current_pointer_same_parent_integrity`, define `VALID_LEGACY_STATE` as all of the following being true in the durable Phase 1 `actors` and `projects` rows before any PR2-00 DDL:

1. Every `projects.created_by` value resolves to exactly one `actors.id`.
2. Every non-NULL `actors.external_key` is unique.
3. Every actor type and project lifecycle value satisfies the frozen Phase 1 value domain.

`INVALID_LEGACY_STATE` is the complement of this predicate. The check is deterministic; it neither repairs nor rewrites rows. Migration `0019` acquires locks on `actors` and `projects` before reading these facts and fails with stable migration error code `LEGACY_STATE_INVALID` before creating Phase 2 tables or advancing the Alembic revision. In Application commands, the same detected structural contradiction maps to `ErrorCode.LEGACY_STATE_INVALID` (HTTP 409 / CLI 4). It must not proceed from a different schema revision.

These checks cover only durable identity and creator references that PR2-00 must preserve and safely interpret. The Phase 1 primary keys, `projects.created_by` foreign key, partial unique actor `external_key` index and value checks normally enforce them; the preflight independently verifies the data rather than assuming imported, restored or administratively modified databases retained those guarantees. An invalid state is not repaired by migration.

Phase 1 has no membership, OWNER, or bootstrap-root facts. Multiple actors and multiple projects are valid historical state; `projects.created_by` is attribution and grants no authority, and `external_key` is not proof of subject control. First-owner bootstrap is allowed only when both `actors` and `projects` are empty; otherwise return `BOOTSTRAP_CLOSED` without choosing a root. Legacy subject binding must name one HUMAN actor UUID and establish that binding through the R2 live proof and independent attestation; inability to prove that exact link returns `SUBJECT_BINDING_UNPROVEN`. Legacy project enrollment uses only the exact `projects.created_by` actor under the R2 checks; an ineligible creator is denied and no alternate owner is inferred. Source identifiers and later-phase state are outside this predicate.

Bootstrap and per-project legacy enrollment evaluate their applicable durable facts after acquiring their existing required table/deployment/project/actor locks and reread them under those locks. A valid but nonempty database rejects first bootstrap as `BOOTSTRAP_CLOSED`; it is not classified as invalid. An unusable or ambiguous identity proof retains `SUBJECT_BINDING_UNPROVEN`, and an ineligible legacy project creator retains `FORBIDDEN`. A structural contradiction found by the predicate returns `LEGACY_STATE_INVALID`. A failed preflight aborts before protected Phase 2 writes, events, challenge consumption, or successful bootstrap closure. Repeating the same failed request against unchanged invalid state returns the same deterministic error and creates no successful receipt or history.

## TEMP-AUTH-EVIDENCE-01 — observable cross-expiry proof

This is an evidence requirement only; TEMP-AUTH-01 retains its existing lock → durable reread → fresh post-lock `clock_timestamp()` → authorization → effect ordering. A controlled cross-expiry test must record database-derived `tx_started_at`, `expiry_at`, observed `lock_wait_started_at`, `lock_acquired_at`, and final `authorization_checked_at`, plus the outcome and persisted-effect counts. It must establish `tx_started_at < expiry_at`, `lock_wait_started_at < expiry_at`, `lock_acquired_at >= expiry_at`, and `authorization_checked_at > expiry_at` and `authorization_checked_at >= lock_acquired_at`. Synchronization must observe the database backend actually waiting on the required lock and must observe expiry before releasing that lock; sleeping before transaction start is not proof.

For any path with a second required blocking wait after a successful preliminary authorization check, a distinct controlled test must record both authorization times and the second lock wait. The second check must occur after acquisition and after expiry, be strictly later than the first check, and deny before any protected write commits. Evidence must identify the exact application path and show zero protected rows/events after denial. Test-only instrumentation may collect these timestamps; production observability fields are not required.
