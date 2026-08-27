# ResearchBase Phase 1 Development Specification

> **版本**：v1.1  
> **状态**：READY FOR PHASE 1 GO REVIEW  
> **日期**：2026-08-26  
> **上位设计**：`ResearchBase_全系统设计文档_架构补全版_v1.2`  
> **适用对象**：Tech Lead、3–6 名中级开发人员、Codex/Coding Agent  
> **规范性**：本文件将系统设计第十八部分转换为可直接施工的 Phase 1 工程规范。若本文件与上位设计的 Phase 1 施工细节冲突，以本文件为 Phase 1 实施解释；若涉及架构原则冲突，以上位设计为准并提交 ADR。

---

# 0. 文档目标与执行规则

本规范只解决一个问题：**开发团队拿到文档后，应当能够在不自行发明核心架构的前提下实现 Phase 1。**

Phase 1 的交付目标不是“功能很多”，而是建立可信的科研 provenance 骨架：

```text
ResearchQuestionVersion
→ HypothesisVersion
→ ExperimentSpecVersion
→ Run
→ DatasetSnapshot / ArtifactVersion
→ Measurement / StatisticalResult
→ EvidenceRelation
→ ClaimVersion
```

并支持：

```text
AuditFinding → ImpactAssessment → downstream affected ClaimVersion
```

## 0.1 MUST / SHOULD / MAY

- **MUST / MUST NOT**：不可自行偏离。
- **SHOULD / SHOULD NOT**：如需偏离，PR 中附 ADR Proposal。
- **MAY**：实现自由。
- 未定义行为：不得由开发者静默决定；提交 Architecture Question。

## 0.2 Phase 1 明确不做

Phase 1 MUST NOT 实现：

- 完整 Approval/P0–P4 Authority Engine；
- 自动投稿与 ExternalEffect；
- IRB/Consent 工作流；
- Funding/ERP；
- 完整 Publication/Reviewer/Authorship；
- 微服务拆分；
- 完整 Event Sourcing/CQRS；
- Agent 自治工作流；
- 通用多态 Object 表；
- 主链 `target_type + target_id` 软引用。

---

## 0.3 v1.1 Agent-ready Core 修订说明

v1.1 **不扩大 Phase 1 功能范围**，不要求实现 STORM、PaperQA2、EvoScientist、AI Scientist-v2、DeerFlow、OpenHands 或通用 Agent Runtime。

新增施工原则：

> **Phase 1 Core 必须同时适合作为 Human UI 和未来 Scientific Agent Runtime 的 canonical state API。**

```text
Human UI / CLI          Future Agent Runtime
      \                    /
       Application Command / Query
                  ↓
          ResearchBase Core
```

Phase 1 不实现 Agent orchestration，但不得做出迫使未来 Agent 绕过 Core、直接读取 ORM/数据库或建立第二套 scientific state 的设计。


# 1. 参考技术栈

```text
Python              3.12+
PostgreSQL          16+
SQLAlchemy          2.x
Alembic             latest compatible
Pydantic            2.x
FastAPI             current stable
Typer               current stable
pytest              current stable
pytest-postgresql / testcontainers 可二选一
ruff                lint/format
mypy or pyright     static typing
```

生产与集成验收数据库 MUST 为 PostgreSQL。SQLite 只允许局部纯 Domain 单元测试，不允许作为 Repository/constraint 集成测试替代品。

---

# 2. 仓库与目录树

Phase 1 推荐单仓库、模块化单体。目录 MUST 保持以下责任边界；可以增加文件，但不得把 Persistence/HTTP 逻辑塞入 Domain。

```text
researchbase/
├── pyproject.toml
├── alembic.ini
├── README.md
├── docs/
│   ├── architecture/
│   │   ├── system_design_v1.1.md
│   │   ├── phase1_development_spec_v1.0.md
│   │   └── adr/
│   └── api/
├── migrations/
│   ├── env.py
│   └── versions/
├── src/researchbase/
│   ├── foundation/
│   │   ├── ids.py
│   │   ├── time.py
│   │   ├── hashing.py
│   │   ├── canonical_json.py
│   │   ├── refs.py
│   │   ├── errors.py
│   │   └── types.py
│   ├── identity/
│   │   ├── domain/
│   │   └── application/
│   ├── organization/
│   │   ├── domain/
│   │   └── application/
│   ├── research/
│   │   ├── domain/
│   │   │   ├── research_question.py
│   │   │   ├── hypothesis.py
│   │   │   └── claim.py
│   │   ├── application/
│   │   │   ├── commands.py
│   │   │   ├── queries.py
│   │   │   └── services.py
│   │   └── ports/
│   │       └── repositories.py
│   ├── experiment/
│   │   ├── domain/
│   │   │   ├── experiment_spec.py
│   │   │   └── run.py
│   │   ├── application/
│   │   └── ports/
│   ├── evidence/
│   │   ├── domain/
│   │   │   ├── dataset.py
│   │   │   ├── artifact.py
│   │   │   ├── metric.py
│   │   │   ├── measurement.py
│   │   │   ├── statistical_result.py
│   │   │   └── evidence_relation.py
│   │   ├── application/
│   │   └── ports/
│   ├── governance/
│   │   ├── domain/
│   │   │   ├── audit_finding.py
│   │   │   ├── impact_assessment.py
│   │   │   └── correction.py
│   │   ├── application/
│   │   └── ports/
│   ├── persistence/
│   │   ├── db.py
│   │   ├── uow.py
│   │   ├── models/
│   │   │   ├── identity.py
│   │   │   ├── organization.py
│   │   │   ├── research.py
│   │   │   ├── experiment.py
│   │   │   ├── evidence.py
│   │   │   └── governance.py
│   │   ├── repositories/
│   │   └── mappers/
│   ├── application/
│   │   ├── command_bus.py
│   │   ├── query_bus.py
│   │   └── dto.py
│   ├── api/
│   │   ├── app.py
│   │   ├── dependencies.py
│   │   ├── errors.py
│   │   └── routes/
│   └── cli/
│       └── main.py
└── tests/
    ├── unit/
    │   ├── foundation/
    │   ├── research/
    │   ├── experiment/
    │   ├── evidence/
    │   └── governance/
    ├── integration/
    │   ├── repositories/
    │   ├── constraints/
    │   └── migrations/
    ├── architecture/
    │   ├── test_import_boundaries.py
    │   ├── test_no_soft_refs_on_main_chain.py
    │   └── test_no_scientific_cascade_delete.py
    └── e2e/
        ├── test_golden_provenance_path.py
        └── test_impact_propagation.py
```

## 2.1 Import 规则

MUST：

```text
foundation ← 可被所有模块依赖
domain     ← foundation
ports      ← domain/foundation
application← domain + ports
persistence← ports + domain + SQLAlchemy
api/cli    ← application DTO/service
```

MUST NOT：

```text
domain → persistence
domain → FastAPI/Typer
domain A → domain B 的 ORM model
foundation → 任何业务模块
HTTP route → session.commit()
CLI → SQLAlchemy repository concrete class 直接编排业务
```

跨 Domain use case 由 application service 编排。

---

# 3. 通用类型与数据库约定

## 3.1 ID

所有 canonical ID 与 version ID 使用 UUID。应用层 SHOULD 生成 UUIDv7；数据库类型使用 `uuid`。

```python
ActorId = NewType("ActorId", UUID)
ProjectId = NewType("ProjectId", UUID)
RunId = NewType("RunId", UUID)
ClaimVersionId = NewType("ClaimVersionId", UUID)
```

禁止在 Domain 中到处使用裸 `str` 代表 ID。

## 3.2 时间

- DB：`TIMESTAMPTZ`
- Python：timezone-aware `datetime`
- API：ISO-8601 UTC，例 `2026-08-26T08:00:00Z`
- 禁止 naive datetime。

## 3.3 Hash

- 算法：SHA-256。
- DB：`char(64)` 或 `varchar(64)`。
- Structured content：canonical JSON 后 hash。
- 文件 ArtifactVersion：原始 bytes hash。
- `content_hash` 不包含 `id`、`created_at`、`row_version`、current pointer。

## 3.4 Version 状态

统一：

```text
DRAFT
FROZEN
SUPERSEDED
ABANDONED
```

允许：

```text
DRAFT → FROZEN
DRAFT → ABANDONED
FROZEN → SUPERSEDED
```

禁止反向迁移。

## 3.5 Run 状态

```text
PLANNED
RUNNING
SUCCEEDED
FAILED
CANCELLED
```

允许：

```text
PLANNED → RUNNING
PLANNED → CANCELLED
RUNNING → SUCCEEDED
RUNNING → FAILED
RUNNING → CANCELLED
```

`RUNNING` 起 material inputs sealed。

---

# 4. Phase 1 数据库：字段级规范

以下 DDL 为规范性逻辑 DDL。Alembic/SQLAlchemy 可产生等价 SQL，但约束语义 MUST 保持。

## 4.1 actors

```sql
CREATE TABLE actors (
    id UUID PRIMARY KEY,
    actor_type VARCHAR(16) NOT NULL CHECK (actor_type IN ('human','agent','service')),
    display_name VARCHAR(200) NOT NULL,
    external_key VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL,
    retired_at TIMESTAMPTZ,
    row_version INTEGER NOT NULL DEFAULT 1
);

CREATE UNIQUE INDEX uq_actors_external_key
ON actors(external_key)
WHERE external_key IS NOT NULL;
```

Phase 1 只需要最小 ActorIdentity，不做完整 IAM。

## 4.2 projects

```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    lifecycle_status VARCHAR(20) NOT NULL DEFAULT 'active'
      CHECK (lifecycle_status IN ('active','archived','retired')),
    created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL,
    row_version INTEGER NOT NULL DEFAULT 1
);
```

## 4.3 workspaces

```sql
CREATE TABLE workspaces (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    name VARCHAR(255) NOT NULL,
    locator TEXT,
    lifecycle_status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL,
    row_version INTEGER NOT NULL DEFAULT 1,
    UNIQUE(project_id, name)
);
```

## 4.4 research_questions / research_question_versions

```sql
CREATE TABLE research_questions (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    current_version_id UUID,
    created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL,
    row_version INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE research_question_versions (
    id UUID PRIMARY KEY,
    research_question_id UUID NOT NULL
      REFERENCES research_questions(id) ON DELETE RESTRICT,
    version_number INTEGER NOT NULL CHECK (version_number > 0),
    status VARCHAR(16) NOT NULL
      CHECK (status IN ('DRAFT','FROZEN','SUPERSEDED','ABANDONED')),
    question_text TEXT NOT NULL,
    scope JSONB,
    rationale TEXT,
    content_hash CHAR(64),
    created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL,
    frozen_at TIMESTAMPTZ,
    row_version INTEGER NOT NULL DEFAULT 1,
    UNIQUE(research_question_id, version_number)
);

ALTER TABLE research_questions
ADD CONSTRAINT fk_rq_current_version
FOREIGN KEY (current_version_id)
REFERENCES research_question_versions(id)
ON DELETE RESTRICT;
```

Application MUST validate `current_version_id` belongs to same `research_question_id`.

## 4.5 hypotheses / hypothesis_versions

```sql
CREATE TABLE hypotheses (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    research_question_id UUID
      REFERENCES research_questions(id) ON DELETE RESTRICT,
    current_version_id UUID,
    created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL,
    row_version INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE hypothesis_versions (
    id UUID PRIMARY KEY,
    hypothesis_id UUID NOT NULL REFERENCES hypotheses(id) ON DELETE RESTRICT,
    version_number INTEGER NOT NULL CHECK (version_number > 0),
    status VARCHAR(16) NOT NULL
      CHECK (status IN ('DRAFT','FROZEN','SUPERSEDED','ABANDONED')),
    statement TEXT NOT NULL,
    expected_direction VARCHAR(64),
    success_criteria JSONB,
    rationale TEXT,
    content_hash CHAR(64),
    created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL,
    frozen_at TIMESTAMPTZ,
    row_version INTEGER NOT NULL DEFAULT 1,
    UNIQUE(hypothesis_id, version_number)
);

ALTER TABLE hypotheses
ADD CONSTRAINT fk_hyp_current_version
FOREIGN KEY (current_version_id)
REFERENCES hypothesis_versions(id)
ON DELETE RESTRICT;
```

## 4.6 experiment_specs / experiment_spec_versions

```sql
CREATE TABLE experiment_specs (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    hypothesis_id UUID REFERENCES hypotheses(id) ON DELETE RESTRICT,
    current_version_id UUID,
    created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL,
    row_version INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE experiment_spec_versions (
    id UUID PRIMARY KEY,
    experiment_spec_id UUID NOT NULL
      REFERENCES experiment_specs(id) ON DELETE RESTRICT,
    version_number INTEGER NOT NULL CHECK (version_number > 0),
    status VARCHAR(16) NOT NULL
      CHECK (status IN ('DRAFT','FROZEN','SUPERSEDED','ABANDONED')),
    title VARCHAR(255) NOT NULL,
    objective TEXT NOT NULL,
    protocol JSONB NOT NULL,
    planned_metrics JSONB,
    seed_policy JSONB,
    analysis_plan JSONB,
    content_hash CHAR(64),
    created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL,
    frozen_at TIMESTAMPTZ,
    row_version INTEGER NOT NULL DEFAULT 1,
    UNIQUE(experiment_spec_id, version_number)
);

ALTER TABLE experiment_specs
ADD CONSTRAINT fk_spec_current_version
FOREIGN KEY (current_version_id)
REFERENCES experiment_spec_versions(id)
ON DELETE RESTRICT;
```

`Run.experiment_spec_version_id` MUST reference FROZEN version。

## 4.7 datasets

```sql
CREATE TABLE datasets (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE RESTRICT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    source_locator TEXT,
    lifecycle_status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL,
    row_version INTEGER NOT NULL DEFAULT 1
);
```

Phase 1 不强制实现 DatasetVersion。需要逻辑版本时通过 `dataset_snapshots.selection_definition` + manifest 固化实际输入；DatasetVersion 可在后续 ADR 中加入。

## 4.8 dataset_snapshots

```sql
CREATE TABLE dataset_snapshots (
    id UUID PRIMARY KEY,
    dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE RESTRICT,
    manifest_hash CHAR(64) NOT NULL,
    selection_definition JSONB NOT NULL,
    manifest_locator TEXT,
    content_hash CHAR(64) NOT NULL,
    created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL,
    UNIQUE(dataset_id, content_hash)
);
```

创建后 immutable。

## 4.9 artifacts / artifact_versions

```sql
CREATE TABLE artifacts (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE RESTRICT,
    artifact_type VARCHAR(32) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    current_version_id UUID,
    created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL,
    row_version INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE artifact_versions (
    id UUID PRIMARY KEY,
    artifact_id UUID NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT,
    version_number INTEGER NOT NULL CHECK (version_number > 0),
    status VARCHAR(16) NOT NULL
      CHECK (status IN ('DRAFT','FROZEN','SUPERSEDED','ABANDONED')),
    locator TEXT,
    media_type VARCHAR(128),
    byte_size BIGINT CHECK (byte_size IS NULL OR byte_size >= 0),
    content_hash CHAR(64) NOT NULL,
    metadata JSONB,
    created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL,
    frozen_at TIMESTAMPTZ,
    row_version INTEGER NOT NULL DEFAULT 1,
    UNIQUE(artifact_id, version_number),
    UNIQUE(artifact_id, content_hash)
);

ALTER TABLE artifacts
ADD CONSTRAINT fk_artifact_current_version
FOREIGN KEY (current_version_id)
REFERENCES artifact_versions(id)
ON DELETE RESTRICT;
```

Run 引用 ArtifactVersion 时 MUST FROZEN。

## 4.10 metric_definitions / metric_definition_versions

```sql
CREATE TABLE metric_definitions (
    id UUID PRIMARY KEY,
    project_id UUID REFERENCES projects(id) ON DELETE RESTRICT,
    name VARCHAR(255) NOT NULL,
    current_version_id UUID,
    created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL,
    row_version INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE metric_definition_versions (
    id UUID PRIMARY KEY,
    metric_definition_id UUID NOT NULL
      REFERENCES metric_definitions(id) ON DELETE RESTRICT,
    version_number INTEGER NOT NULL CHECK (version_number > 0),
    status VARCHAR(16) NOT NULL
      CHECK (status IN ('DRAFT','FROZEN','SUPERSEDED','ABANDONED')),
    definition JSONB NOT NULL,
    unit VARCHAR(64),
    aggregation VARCHAR(64),
    content_hash CHAR(64),
    created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL,
    frozen_at TIMESTAMPTZ,
    row_version INTEGER NOT NULL DEFAULT 1,
    UNIQUE(metric_definition_id, version_number)
);
```

## 4.11 runs

```sql
CREATE TABLE runs (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    experiment_spec_version_id UUID NOT NULL
      REFERENCES experiment_spec_versions(id) ON DELETE RESTRICT,
    run_type VARCHAR(32) NOT NULL DEFAULT 'experiment',
    status VARCHAR(16) NOT NULL
      CHECK (status IN ('PLANNED','RUNNING','SUCCEEDED','FAILED','CANCELLED')),
    inputs_sealed_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    exit_code INTEGER,
    failure_reason TEXT,
    created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL,
    row_version INTEGER NOT NULL DEFAULT 1,
    CHECK (
      (status = 'PLANNED' AND inputs_sealed_at IS NULL)
      OR
      (status <> 'PLANNED' AND inputs_sealed_at IS NOT NULL)
    )
);
```

Application 在创建 Run 时验证 ExperimentSpecVersion 为 FROZEN。

## 4.12 run_dataset_inputs

```sql
CREATE TABLE run_dataset_inputs (
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE RESTRICT,
    dataset_snapshot_id UUID NOT NULL
      REFERENCES dataset_snapshots(id) ON DELETE RESTRICT,
    role VARCHAR(32) NOT NULL
      CHECK (role IN ('train','validation','test','calibration','auxiliary','other')),
    ordinal INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (run_id, dataset_snapshot_id, role)
);
```

只允许 Run=PLANNED 时修改。

## 4.13 run_artifact_inputs

```sql
CREATE TABLE run_artifact_inputs (
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE RESTRICT,
    artifact_version_id UUID NOT NULL
      REFERENCES artifact_versions(id) ON DELETE RESTRICT,
    role VARCHAR(32) NOT NULL
      CHECK (role IN ('source_code','model','checkpoint','configuration',
                      'environment_manifest','script','dependency_lock','other')),
    ordinal INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (run_id, artifact_version_id, role)
);
```

`start_run` 前 Application MUST 验证所有 ArtifactVersion=FROZEN。

## 4.14 measurements

```sql
CREATE TABLE measurements (
    id UUID PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE RESTRICT,
    metric_definition_version_id UUID NOT NULL
      REFERENCES metric_definition_versions(id) ON DELETE RESTRICT,
    numeric_value DOUBLE PRECISION,
    structured_value JSONB,
    unit VARCHAR(64),
    evaluation_scope JSONB,
    content_hash CHAR(64) NOT NULL,
    created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL,
    CHECK (
      (numeric_value IS NOT NULL AND structured_value IS NULL)
      OR
      (numeric_value IS NULL AND structured_value IS NOT NULL)
    )
);
```

MUST NOT UPDATE value fields。Measurement 只能为已 seal 的 Run 创建；默认要求 Run 为 SUCCEEDED，若未来需要 RUNNING streaming metric，必须 ADR。

## 4.15 statistical_results

```sql
CREATE TABLE statistical_results (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    analysis_type VARCHAR(64) NOT NULL,
    result_payload JSONB NOT NULL,
    analysis_definition JSONB NOT NULL,
    content_hash CHAR(64) NOT NULL,
    created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL
);
```

创建后 immutable。

## 4.16 statistical_result_inputs

```sql
CREATE TABLE statistical_result_inputs (
    statistical_result_id UUID NOT NULL
      REFERENCES statistical_results(id) ON DELETE RESTRICT,
    measurement_id UUID NOT NULL
      REFERENCES measurements(id) ON DELETE RESTRICT,
    input_role VARCHAR(32) NOT NULL DEFAULT 'input',
    ordinal INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (statistical_result_id, measurement_id, input_role)
);
```

## 4.17 claims / claim_versions

```sql
CREATE TABLE claims (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    current_version_id UUID,
    created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL,
    row_version INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE claim_versions (
    id UUID PRIMARY KEY,
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE RESTRICT,
    version_number INTEGER NOT NULL CHECK (version_number > 0),
    status VARCHAR(16) NOT NULL
      CHECK (status IN ('DRAFT','FROZEN','SUPERSEDED','ABANDONED')),
    statement TEXT NOT NULL,
    scope JSONB,
    qualification TEXT,
    support_set_hash CHAR(64),
    content_hash CHAR(64),
    created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL,
    frozen_at TIMESTAMPTZ,
    row_version INTEGER NOT NULL DEFAULT 1,
    UNIQUE(claim_id, version_number)
);

ALTER TABLE claims
ADD CONSTRAINT fk_claim_current_version
FOREIGN KEY (current_version_id)
REFERENCES claim_versions(id)
ON DELETE RESTRICT;
```

## 4.18 evidence_relations

```sql
CREATE TABLE evidence_relations (
    id UUID PRIMARY KEY,
    claim_version_id UUID NOT NULL
      REFERENCES claim_versions(id) ON DELETE RESTRICT,
    measurement_id UUID REFERENCES measurements(id) ON DELETE RESTRICT,
    statistical_result_id UUID
      REFERENCES statistical_results(id) ON DELETE RESTRICT,
    relation_type VARCHAR(32) NOT NULL
      CHECK (relation_type IN ('supports','contradicts','qualifies','context')),
    qualification TEXT,
    created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL,
    CHECK (
      (measurement_id IS NOT NULL AND statistical_result_id IS NULL)
      OR
      (measurement_id IS NULL AND statistical_result_id IS NOT NULL)
    )
);

CREATE UNIQUE INDEX uq_evidence_measurement
ON evidence_relations(claim_version_id, measurement_id, relation_type)
WHERE measurement_id IS NOT NULL;

CREATE UNIQUE INDEX uq_evidence_stat
ON evidence_relations(claim_version_id, statistical_result_id, relation_type)
WHERE statistical_result_id IS NOT NULL;
```

只允许 ClaimVersion=DRAFT 时增删。freeze Claim 时同一事务计算 evidence canonical set hash。

## 4.19 audit_findings

```sql
CREATE TABLE audit_findings (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    finding_type VARCHAR(64) NOT NULL,
    severity VARCHAR(16) NOT NULL
      CHECK (severity IN ('info','minor','major','critical')),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    target_type VARCHAR(64) NOT NULL,
    target_id UUID NOT NULL,
    target_content_hash CHAR(64),
    status VARCHAR(20) NOT NULL DEFAULT 'open'
      CHECK (status IN ('open','confirmed','dismissed','resolved')),
    created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL,
    row_version INTEGER NOT NULL DEFAULT 1
);
```

这是允许 soft typed locator 的横切对象。Application validator MUST 验证目标存在并保存可获得的 frozen hash/version identity。

## 4.20 impact_assessments

```sql
CREATE TABLE impact_assessments (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    audit_finding_id UUID
      REFERENCES audit_findings(id) ON DELETE RESTRICT,
    assessment_payload JSONB NOT NULL,
    conclusion VARCHAR(32) NOT NULL
      CHECK (conclusion IN ('no_impact','stale','invalid','requires_review','unknown')),
    created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL,
    content_hash CHAR(64) NOT NULL
);
```

Assessment immutable；重新评估创建新行。

## 4.21 impact_targets

```sql
CREATE TABLE impact_targets (
    impact_assessment_id UUID NOT NULL
      REFERENCES impact_assessments(id) ON DELETE RESTRICT,
    target_type VARCHAR(64) NOT NULL,
    target_id UUID NOT NULL,
    target_content_hash CHAR(64),
    impact_kind VARCHAR(32) NOT NULL,
    PRIMARY KEY (impact_assessment_id, target_type, target_id)
);
```

## 4.22 correction_records

```sql
CREATE TABLE correction_records (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    target_type VARCHAR(64) NOT NULL,
    target_id UUID NOT NULL,
    target_content_hash CHAR(64),
    correction_type VARCHAR(32) NOT NULL,
    corrected_assertion JSONB NOT NULL,
    reason TEXT NOT NULL,
    created_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL,
    content_hash CHAR(64) NOT NULL
);
```

Correction 不 UPDATE target；current validity/read model 应用 correction projection。

---

# 5. Repository Ports

Repository interface 属于 Domain/Application port，不暴露 SQLAlchemy Session/ORM。

## 5.1 通用约束

Repository MUST：

- 返回 Domain entity/value object 或专用 read DTO；
- 不在方法内部 commit；
- 不吞掉 optimistic concurrency 冲突；
- `get_*` 找不到时返回 `None` 或统一 `NotFound`，同一代码库保持一致；
- 不提供 `delete_scientific_history()` 一类接口。

Repository MUST NOT：

- 暴露 `.query()` 给 application；
- 返回 SQLAlchemy ORM model 给 API；
- 用 generic `save(object: Any)` 替代关键领域接口。

## 5.2 UnitOfWork

```python
class UnitOfWork(Protocol):
    actors: ActorRepository
    projects: ProjectRepository
    research_questions: ResearchQuestionRepository
    hypotheses: HypothesisRepository
    experiment_specs: ExperimentSpecRepository
    runs: RunRepository
    datasets: DatasetRepository
    artifacts: ArtifactRepository
    metrics: MetricDefinitionRepository
    measurements: MeasurementRepository
    statistical_results: StatisticalResultRepository
    claims: ClaimRepository
    audits: AuditRepository

    def commit(self) -> None: ...
    def rollback(self) -> None: ...
```

Application service 使用：

```python
with uow_factory() as uow:
    ...
    uow.commit()
```

## 5.3 关键 Repository

```python
class HypothesisRepository(Protocol):
    def add(self, aggregate: Hypothesis) -> None: ...
    def get(self, hypothesis_id: HypothesisId) -> Hypothesis | None: ...
    def get_for_update(self, hypothesis_id: HypothesisId) -> Hypothesis | None: ...
    def list_versions(self, hypothesis_id: HypothesisId) -> Sequence[HypothesisVersion]: ...

class ExperimentSpecRepository(Protocol):
    def add(self, aggregate: ExperimentSpec) -> None: ...
    def get(self, spec_id: ExperimentSpecId) -> ExperimentSpec | None: ...
    def get_version(self, version_id: ExperimentSpecVersionId) -> ExperimentSpecVersion | None: ...

class RunRepository(Protocol):
    def add(self, run: Run) -> None: ...
    def get(self, run_id: RunId) -> Run | None: ...
    def get_for_update(self, run_id: RunId) -> Run | None: ...
    def add_dataset_input(self, run_id: RunId, input: RunDatasetInput) -> None: ...
    def add_artifact_input(self, run_id: RunId, input: RunArtifactInput) -> None: ...
    def list_dataset_inputs(self, run_id: RunId) -> Sequence[RunDatasetInput]: ...
    def list_artifact_inputs(self, run_id: RunId) -> Sequence[RunArtifactInput]: ...

class MeasurementRepository(Protocol):
    def add(self, measurement: Measurement) -> None: ...
    def get(self, measurement_id: MeasurementId) -> Measurement | None: ...
    def list_by_run(self, run_id: RunId) -> Sequence[Measurement]: ...

class ClaimRepository(Protocol):
    def add(self, aggregate: Claim) -> None: ...
    def get(self, claim_id: ClaimId) -> Claim | None: ...
    def get_version(self, version_id: ClaimVersionId) -> ClaimVersion | None: ...
    def add_evidence(self, relation: EvidenceRelation) -> None: ...
    def remove_evidence(self, relation_id: EvidenceRelationId) -> None: ...
    def list_evidence(self, version_id: ClaimVersionId) -> Sequence[EvidenceRelation]: ...
```

---

# 6. Domain Service / Application Service 分工

Domain entity 负责自身 invariant；Application service 负责跨 Aggregate/Repository orchestration。

示例：

```python
def start_run(cmd: StartRun, uow: UnitOfWork) -> RunDTO:
    with uow:
        run = require_run(uow.runs.get_for_update(cmd.run_id))
        spec = require_spec_version(
            uow.experiment_specs.get_version(run.experiment_spec_version_id)
        )
        if spec.status != VersionStatus.FROZEN:
            raise VersionNotFrozen(...)

        datasets = uow.runs.list_dataset_inputs(run.id)
        artifacts = uow.runs.list_artifact_inputs(run.id)

        validate_run_inputs_frozen(datasets, artifacts, uow)
        run.start(now=clock.now())   # domain state transition
        uow.runs.save(run)
        uow.commit()
        return RunDTO.from_domain(run)
```

`Run.start()` 自己负责：

- 当前状态必须 PLANNED；
- `inputs_sealed_at` 被设置；
- started_at 被设置；
- 状态变 RUNNING。

跨 Repository 检查由 application service 做。

---

# 7. DTO 规范

DTO 使用 Pydantic。DTO 不等于 Domain Entity，也不等于 ORM model。

## 7.1 Command DTO

```python
class CreateHypothesisRequest(BaseModel):
    project_id: UUID
    research_question_id: UUID | None = None
    statement: str
    expected_direction: str | None = None
    success_criteria: dict[str, Any] | None = None
    rationale: str | None = None

class CreateRunRequest(BaseModel):
    project_id: UUID
    experiment_spec_version_id: UUID
    run_type: Literal["experiment", "analysis", "preprocessing", "evaluation"] = "experiment"

class AttachDatasetInputRequest(BaseModel):
    dataset_snapshot_id: UUID
    role: Literal["train","validation","test","calibration","auxiliary","other"]
    ordinal: int = 0

class RecordMeasurementRequest(BaseModel):
    run_id: UUID
    metric_definition_version_id: UUID
    numeric_value: float | None = None
    structured_value: dict[str, Any] | list[Any] | None = None
    unit: str | None = None
    evaluation_scope: dict[str, Any] | None = None
```

Pydantic validator MUST enforce numeric/structured XOR；数据库仍保留 CHECK，不能只靠 DTO。

## 7.2 Write Response

统一 envelope：

```python
class WriteResult(BaseModel):
    id: UUID
    version_id: UUID | None = None
    content_hash: str | None = None
    row_version: int | None = None
    server_timestamp: datetime
```

## 7.3 Query DTO

```python
class RunProvenanceDTO(BaseModel):
    run_id: UUID
    status: str
    experiment_spec_version: FrozenObjectDTO
    dataset_inputs: list[RunDatasetInputDTO]
    artifact_inputs: list[RunArtifactInputDTO]
    measurements: list[MeasurementDTO]

class ClaimTraceDTO(BaseModel):
    claim_version: ClaimVersionDTO
    evidence: list[EvidenceTraceDTO]
    runs: list[RunProvenanceDTO]
    closure_complete: bool
    closure_violations: list[str]
```

Query DTO MAY denormalize；它不是 Source of Truth。

---

# 8. Command 契约

每个 Command = 一个事务。以下为 Phase 1 必须实现。

## 8.1 create_project

前置：actor 存在。  
写入：projects。  
后置：返回 project_id。  
错误：NOT_FOUND(actor), VALIDATION_ERROR。

## 8.2 create_hypothesis

一个事务创建：

```text
Hypothesis identity
+
HypothesisVersion #1 DRAFT
+
current_version_id → v1
```

不得创建没有 version 的空壳 identity。

## 8.3 revise_hypothesis

前置：

- 当前 version 必须 FROZEN 或调用者明确基于指定 version；
- 新建 version_number = max + 1；
- 旧 FROZEN version 可标记 SUPERSEDED，但其 material fields 不变。

禁止原位修改 FROZEN。

## 8.4 freeze_hypothesis_version

前置：DRAFT。  
动作：验证 material fields → canonical serialize → content_hash → FROZEN → frozen_at。  
同事务更新 identity.current_version_id。

## 8.5 create_experiment_spec / revise / freeze

同 Version 规则。freeze 时 MUST 校验：

- objective 非空；
- protocol 非空；
- 若 hypothesis_id 存在，目标存在；
- material JSON 可 canonical serialize。

## 8.6 create_dataset_snapshot

输入至少：

```text
dataset_id
selection_definition
manifest_hash
manifest_locator optional
```

计算 snapshot content hash。相同 dataset+content_hash SHOULD 幂等返回已有 snapshot。

## 8.7 create_artifact_version

对文件：

- 服务层读取/接收已经确定的 bytes hash；
- locator 与 hash 分离；
- 同 artifact + content_hash 不重复建版本，返回 DUPLICATE_CONTENT 或幂等返回，项目统一选择一种；Phase 1 推荐幂等返回已有版本。

正式 Run 使用前必须 freeze ArtifactVersion。

## 8.8 create_run

前置：ExperimentSpecVersion 存在且 FROZEN。  
初始：PLANNED，inputs_sealed_at NULL。  
不得自动启动。

## 8.9 attach_run_dataset_input / attach_run_artifact_input

前置：Run=PLANNED。  
否则：IMMUTABLE_RECORD 或 INVALID_STATE_TRANSITION。  
ArtifactVersion 必须 FROZEN；DatasetSnapshot 天然 immutable。

## 8.10 start_run

一个事务：

1. lock/optimistic check Run；
2. 确认 PLANNED；
3. 确认 ExperimentSpecVersion FROZEN；
4. 确认所有 ArtifactVersion FROZEN；
5. 检查至少满足 ExperimentSpec 所要求的输入角色（Phase 1 可先做基础 validator）；
6. 设置 inputs_sealed_at；
7. status=RUNNING；
8. started_at=now；
9. commit。

## 8.11 finish_run

输入：

```text
run_id
outcome = SUCCEEDED | FAILED | CANCELLED
exit_code optional
failure_reason optional
```

前置 RUNNING。  
SUCCEEDED SHOULD 要求 `finished_at`。  
terminal 后禁止输入变化。

## 8.12 record_measurement

前置：

- Run=SUCCEEDED；
- MetricDefinitionVersion=FROZEN；
- numeric/structured XOR；
- unit 与 metric definition 如有约束则兼容。

创建后 immutable。

## 8.13 record_statistical_result

一个事务创建 result + input rows。  
至少 1 个 Measurement。  
所有 Measurement 必须存在。  
跨 project 输入 Phase 1 默认禁止，除非显式 ADR。

## 8.14 create_claim

创建 Claim + ClaimVersion #1 DRAFT。

## 8.15 link_evidence

前置：

- ClaimVersion=DRAFT；
- source Measurement/StatisticalResult 存在；
- source 与 Claim 同 project（Phase 1 默认）；
- relation_type 合法。

## 8.16 freeze_claim_version

一个事务：

1. lock ClaimVersion；
2. 必须 DRAFT；
3. 读取全部 EvidenceRelation；
4. canonical sort：`source_type, source_id, relation_type, qualification`；
5. 计算 `support_set_hash`；
6. 计算 Claim content_hash，其中包含 support_set_hash；
7. status=FROZEN；
8. frozen_at；
9. 更新 Claim.current_version_id；
10. commit。

冻结后 EvidenceRelation 不可修改。

## 8.17 create_audit_finding

Application validator 根据 target_type 路由到已注册 TargetResolver。  
保存 target_id + content_hash（若有）。  
不得由 AuditFinding 直接 UPDATE target。

## 8.18 create_impact_assessment

根据 Finding 与 provenance graph 生成/接受 affected targets。  
Phase 1 允许人工/规则提供影响集合，但必须能用 Query 验证关系路径。

## 8.19 create_correction_record

只新增 CorrectionRecord。  
禁止直接修改 Measurement/StatisticalResult/terminal Run/FROZEN Version。

---

# 9. Query 契约

## 9.1 get_run_provenance(run_id)

必须返回：

```text
Run
ExperimentSpecVersion
DatasetSnapshots[]
ArtifactVersions[]
Measurements[]
```

并标识所有 frozen requirements 是否满足。

## 9.2 trace_claim_to_runs(claim_version_id)

遍历：

```text
ClaimVersion
→ EvidenceRelation
→ Measurement → Run
→ StatisticalResult → statistical_result_inputs → Measurement → Run
```

去重 Run。

继续展开：

```text
Run → ExperimentSpecVersion
Run → DatasetSnapshot[]
Run → ArtifactVersion[]
```

输出 closure violations。

## 9.3 get_downstream_impact(target)

Phase 1 至少支持：

```text
DatasetSnapshot → Run → Measurement → EvidenceRelation → ClaimVersion
ArtifactVersion → Run → Measurement → EvidenceRelation → ClaimVersion
Run → Measurement → EvidenceRelation → ClaimVersion
Measurement → EvidenceRelation → ClaimVersion
StatisticalResult → EvidenceRelation → ClaimVersion
```

这是影响分析最小闭包。

## 9.4 get_current_validity(target)

Derived projection：

```text
UNKNOWN
VALID
STALE
INVALID
CORRECTED
```

优先级由 Governance projection service 定义。Phase 1 推荐：

```text
active INVALID impact > active STALE impact > CorrectionRecord > no finding
```

但不得写回原科学事实表。

---

# 9A. Agent-ready Application Boundary（v1.1 新增，Normative）

本节不新增 Phase 1 use case，只约束现有 Command/Query，使未来 Human 与 Agent 共用同一业务边界。

## 9A.1 ExecutionContext

Application handler MUST NOT 依赖 FastAPI、CLI、STORM、EvoScientist、LangGraph、OpenHands 等调用者状态。调用上下文统一表达为：

```python
class ExecutionContext(BaseModel):
    actor_id: UUID
    request_id: UUID
    correlation_id: UUID | None = None
    causation_id: UUID | None = None
    client_type: Literal["human_ui", "cli", "agent", "service", "test"]
    client_name: str | None = None
    client_version: str | None = None
```

`client_type` 只用于 provenance、observability 与 policy，不得改变 deterministic scientific rules。

## 9A.2 Canonical ID Contract

机器接口 MUST 使用 canonical/version IDs，例如 `experiment_spec_version_id`、`dataset_snapshot_id`、`artifact_version_id`、`run_id`、`measurement_id`、`claim_version_id`。写操作 SHOULD 返回 ID、version ID、content hash、row version 和 server timestamp，而不是只返回 display text。

## 9A.3 Query Completeness

未来 Agent 必须能通过 Query 层获得 current version、version history、Run provenance/inputs、Measurements、StatisticalResult inputs、Claim evidence/trace、downstream impact 和 closure report。若必须 import ORM/SQLAlchemy model 才能完成这些任务，视为 Query boundary 缺陷。

## 9A.4 Candidate ≠ Canonical

```text
Agent/LLM output → candidate → Application Command → canonical DRAFT object
```

Agent 生成的 hypothesis 文本不是 HypothesisVersion；Coding Agent patch 也不是 Formal Run input。代码、配置、环境等必须先形成 ArtifactVersion，再 attach 到 Run。

## 9A.5 Vendor-neutral Core

Phase 1 Domain/Schema MUST NOT 出现 `storm_*`、`paperqa_*`、`evoscientist_*`、`ai_scientist_*`、`langgraph_state`、`deerflow_thread`、`openhands_session`、`codex_task_id` 等第三方专属 scientific fields。

## 9A.6 Agent 输出晋升边界

- Coding Agent output → ArtifactVersion → FROZEN → Run input。
- Dataset locator → DatasetSnapshot → Run input。
- Analysis/Critic interpretation → DRAFT ClaimVersion → EvidenceRelation → freeze。
- Conversation/working memory 永远不是 Measurement、StatisticalResult 或 Formal Claim。

## 9A.7 Architecture Contract Test

新增 `tests/architecture/test_agent_ready_application_boundary.py`，至少验证：

- application/domain 不 import FastAPI/Typer 或第三方 Agent framework；
- public Command/Query DTO 不暴露 ORM；
- Human API/CLI 使用同一 application handlers；
- Core schema 不含 vendor-specific columns；
- Run/Claim trace 无需 persistence model 即可消费。


# 10. HTTP API 最小规范

API 只是 adapter。业务规则必须在 application service。未来 Agent Adapter 与 HTTP/CLI 同级，并复用同一 Application Command/Query。

建议：

```text
POST /v1/projects
POST /v1/research-questions
POST /v1/research-questions/{id}/versions
POST /v1/research-question-versions/{id}:freeze

POST /v1/hypotheses
POST /v1/hypotheses/{id}/versions
POST /v1/hypothesis-versions/{id}:freeze

POST /v1/experiment-specs
POST /v1/experiment-specs/{id}/versions
POST /v1/experiment-spec-versions/{id}:freeze

POST /v1/datasets
POST /v1/datasets/{id}/snapshots

POST /v1/artifacts
POST /v1/artifacts/{id}/versions
POST /v1/artifact-versions/{id}:freeze

POST /v1/metric-definitions
POST /v1/metric-definitions/{id}/versions
POST /v1/metric-definition-versions/{id}:freeze

POST /v1/runs
POST /v1/runs/{id}/dataset-inputs
POST /v1/runs/{id}/artifact-inputs
POST /v1/runs/{id}:start
POST /v1/runs/{id}:finish
GET  /v1/runs/{id}/provenance

POST /v1/measurements
POST /v1/statistical-results

POST /v1/claims
POST /v1/claims/{id}/versions
POST /v1/claim-versions/{id}/evidence
POST /v1/claim-versions/{id}:freeze
GET  /v1/claim-versions/{id}/trace

POST /v1/audit-findings
POST /v1/impact-assessments
POST /v1/corrections
GET  /v1/impact/{target_type}/{target_id}
```

## 10.1 HTTP 状态映射

```text
VALIDATION_ERROR              → 422
NOT_FOUND                     → 404
INVALID_STATE_TRANSITION      → 409
VERSION_NOT_FROZEN            → 409
IMMUTABLE_RECORD              → 409
CONCURRENT_MODIFICATION       → 409
DUPLICATE_CONTENT             → 409 or 200 idempotent endpoint
REFERENTIAL_INTEGRITY_ERROR   → 409
PROVENANCE_CLOSURE_VIOLATION  → 409
```

返回统一：

```json
{
  "error": {
    "code": "INVALID_STATE_TRANSITION",
    "message": "Run must be PLANNED before start.",
    "details": {
      "run_id": "...",
      "current_status": "SUCCEEDED"
    }
  }
}
```

---

# 11. CLI 最小规范

CLI 调用同一 Application Service：

```text
researchbase project create
researchbase hypothesis create
researchbase hypothesis freeze
researchbase spec create
researchbase spec freeze
researchbase dataset snapshot
researchbase artifact add-version
researchbase run create
researchbase run attach-dataset
researchbase run attach-artifact
researchbase run start
researchbase run finish
researchbase measurement record
researchbase stats record
researchbase claim create
researchbase claim link-evidence
researchbase claim freeze
researchbase trace claim
researchbase trace run
researchbase audit create
researchbase impact show
```

CLI 不得自行访问 ORM。

---

# 12. Frozen Provenance Closure Validator

Phase 1 MUST 实现一个明确服务，而不是只靠开发者“记住”规则。

```python
class ProvenanceClosureValidator:
    def validate_claim_version(self, claim_version_id: UUID) -> ClosureReport: ...
    def validate_run(self, run_id: UUID) -> ClosureReport: ...
```

`ClosureReport`：

```python
class ClosureViolation(BaseModel):
    code: str
    object_type: str
    object_id: UUID
    path: list[str]
    message: str

class ClosureReport(BaseModel):
    complete: bool
    visited_count: int
    violations: list[ClosureViolation]
```

## 12.1 Run closure

检查：

- ExperimentSpecVersion FROZEN；
- 所有 ArtifactVersion FROZEN；
- DatasetSnapshot 存在且 immutable；
- RUNNING/terminal Run 已 sealed；
- 不存在主链 soft reference。

## 12.2 Claim closure

检查：

- ClaimVersion FROZEN；
- support_set_hash 与当前 EvidenceRelation 集合一致；
- 每条 Evidence source 存在；
- StatisticalResult 每个 input Measurement 存在；
- Measurement 的 Run closure 完整；
- MetricDefinitionVersion FROZEN。

---

# 13. 数据库不可变性实现策略

不要只依赖程序员自律。

Phase 1 最低要求：

1. Application/Domain 禁止更新 immutable fields；
2. Repository 不暴露对应 update 方法；
3. Integration tests 对 SQL UPDATE 进行验证；
4. 可选：PostgreSQL trigger 防止 frozen/terminal material fields 更新。

推荐 Phase 1 对最关键表加 trigger：

```text
measurements
statistical_results
dataset_snapshots
```

以及：

```text
claim_versions when status != DRAFT
artifact_versions when status != DRAFT
experiment_spec_versions when status != DRAFT
```

如果团队不采用 trigger，必须用更强 integration test 证明 persistence mapper 不会产生 material UPDATE。

---

# 14. 并发与幂等

## 14.1 Optimistic concurrency

以下对象 MUST 使用 `row_version`：

```text
Project
Workspace
ResearchQuestion identity
Hypothesis identity
ExperimentSpec identity
Artifact identity
MetricDefinition identity
Claim identity
DRAFT Version
Run
AuditFinding
```

更新：

```sql
UPDATE ...
SET ..., row_version = row_version + 1
WHERE id = :id AND row_version = :expected;
```

rowcount=0 → `CONCURRENT_MODIFICATION`。

## 14.2 Idempotency

Phase 1 HTTP 可先不做全局 Idempotency-Key，但以下 SHOULD 内容幂等：

- DatasetSnapshot：dataset_id + content_hash；
- ArtifactVersion：artifact_id + content_hash；
- freeze：已 FROZEN 且 hash 一致时可返回当前结果；
- finish_run：相同 terminal outcome 可选择幂等返回；不同 outcome 必须冲突。

---

# 15. Migration 规则

每个 schema PR MUST 带 Alembic migration。

要求：

- 空库 `alembic upgrade head` 成功；
- 从上一版本 upgrade 成功；
- downgrade 若不可逆，migration 顶部明确注释；
- 禁止 migration 静默删除 scientific history；
- 新增 NOT NULL 字段时考虑已有数据 backfill；
- FK 默认 `ON DELETE RESTRICT`；
- 不使用 `ON DELETE CASCADE` 指向 scientific provenance 主链。

Migration PR 需包含 constraint integration tests。

---

# 16. 测试矩阵

## 16.1 Foundation

- UUID 类型与序列化；
- UTC datetime；
- canonical JSON 对 key order 稳定；
- SHA-256 稳定；
- Domain error code 稳定。

## 16.2 Version

每种 Version 至少：

- DRAFT 可编辑；
- DRAFT→FROZEN；
- FROZEN material edit 失败；
- FROZEN→SUPERSEDED；
- DRAFT→ABANDONED；
- 不允许 FROZEN→DRAFT；
- version_number unique；
- current pointer 属于同 parent。

## 16.3 Run

- 非 FROZEN spec 不能创建/启动；
- PLANNED 可 attach input；
- RUNNING/terminal 不能 attach；
- start 原子 seal；
- start 两次冲突；
- terminal transition 合法；
- terminal 后 material fields 不可变；
- rerun 必须新 ID。

## 16.4 Evidence

- DatasetSnapshot immutable；
- ArtifactVersion FROZEN 才能用于 Run；
- Measurement numeric/structured XOR；
- Measurement 不可 UPDATE；
- StatisticalResult input 至少 1 个；
- StatisticalResult input FK 强约束。

## 16.5 Claim

- 只给 DRAFT ClaimVersion link evidence；
- Evidence XOR；
- freeze 计算 support_set_hash；
- freeze 后不能新增/删除 evidence；
- support_set_hash tamper 能被 closure validator 检出。

## 16.6 Provenance E2E

Golden Path：

```text
create actor/project
→ question v1 freeze
→ hypothesis v1 freeze
→ spec v1 freeze
→ dataset snapshot
→ source/config/environment artifact versions freeze
→ run attach inputs
→ run start/finish
→ metric definition freeze
→ measurement
→ statistical result
→ claim draft
→ link evidence
→ claim freeze
→ trace claim
```

断言：

- closure_complete=true；
- trace 能回到 exact spec/snapshot/artifact；
- 所有 hash/ID 稳定。

## 16.7 Impact E2E

构造：

```text
ArtifactVersion(code bug)
→ Run
→ Measurement
→ ClaimVersion
```

创建 AuditFinding + ImpactAssessment 后：

- downstream query 找到 ClaimVersion；
- Measurement 值未被修改；
- validity projection=STALE/INVALID；
- historical trace 仍完整。

---

# 17. Architecture Tests

CI MUST 有自动架构测试。

至少：

```text
test_foundation_imports_no_business_modules
test_domain_does_not_import_sqlalchemy
test_domain_does_not_import_fastapi_or_typer
test_api_does_not_import_persistence_models
test_no_main_chain_polymorphic_reference
test_no_scientific_fk_on_delete_cascade
test_no_repository_commit_calls
```

可用 AST/import-linter/自定义 pytest 实现。

---

# 18. Observability 最小要求

Phase 1 不建设复杂监控，但必须有结构化日志。

每个 Application Command 日志至少：

```text
request_id
command_name
actor_id
project_id if applicable
target_id
result
duration_ms
error_code
```

不得把大型 Dataset 内容、敏感 payload、文件 bytes 写日志。

DB transaction rollback MUST 记录 command/error，不记录密码/token。

---

# 19. Security 最小要求

Phase 1 不是完整 IAM，但必须：

- API 不信任客户端传 `created_at`；
- `created_by` 来自认证/执行上下文，不从 payload 任意指定（开发模式可显式 test actor）；
- SQLAlchemy 参数化查询；
- locator 不作为 shell command 直接拼接；
- Artifact path/URI 做 schema validation；
- secrets 不进入 Artifact metadata/content hash payload；
- 不把数据库异常堆栈直接返回 API 客户端。

---

# 20. PR 施工顺序

以下顺序是规范性实施路线。若多人并行，只能在依赖满足后并行。

## PR-00：Repository Bootstrap

交付：

- `pyproject.toml`
- src layout
- ruff/type checker/pytest
- PostgreSQL test fixture
- Alembic bootstrap
- CI
- README 开发命令

Gate：

```text
lint pass
type check pass
pytest empty smoke pass
PostgreSQL connection integration pass
alembic upgrade head pass
```

## PR-01：Foundation

交付：

- typed IDs；
- clock/time；
- canonical JSON；
- SHA-256；
- error model；
- base enums；
- `ExecutionContext`（Human/CLI/Agent-neutral）；
- architecture import tests。

不建业务表。

## PR-02：Actor + Project + Workspace + UoW Skeleton

交付：

- actors/projects/workspaces migrations；
- Domain models；
- repositories；
- SQLAlchemy implementations；
- UoW；
- create/get commands。

Gate：transaction rollback test。

## PR-03：Generic Version Semantics Test Harness

不是 generic version table，而是共享 Domain helper/test contract：

- VersionStatus；
- freeze helper；
- material hash contract；
- version state contract tests。

不允许做万能 Version ORM。

## PR-04：ResearchQuestion + Hypothesis

交付：

- identity/version tables；
- create/revise/freeze；
- current pointer；
- optimistic concurrency；
- history query。

## PR-05：ExperimentSpec

交付：

- tables；
- create/revise/freeze；
- frozen spec validation；
- hypothesis link。

## PR-06：Dataset + DatasetSnapshot

交付：

- datasets；
- snapshots；
- canonical manifest hash；
- immutable snapshot；
- idempotent snapshot creation。

## PR-07：Artifact + ArtifactVersion

交付：

- artifacts；
- versions；
- bytes/content hash contract；
- freeze；
- role enums 放在 Experiment input 层，不放 Artifact 本体。

## PR-08：MetricDefinition

交付：

- metric identity/version；
- freeze；
- unit/definition contract。

## PR-09：Run Core

交付：

- runs；
- run_dataset_inputs；
- run_artifact_inputs；
- attach commands；
- start/seal；
- finish；
- optimistic concurrency；
- Run closure validator v1。

这是 Phase 1 第一关键 Gate。

## PR-10：Measurement

交付：

- measurements；
- numeric/structured XOR；
- record command；
- immutability；
- run/metric frozen checks。

## PR-11：StatisticalResult

交付：

- statistical_results；
- statistical_result_inputs；
- immutable insert；
- query。

## PR-12：Claim + EvidenceRelation

交付：

- claims/claim_versions；
- evidence_relations；
- link/unlink DRAFT only；
- support_set_hash；
- freeze；
- Claim closure validator。

这是 Phase 1 第二关键 Gate。

## PR-13：Trace Queries

交付：

- get_run_provenance；
- trace_claim_to_runs；
- trace_run_to_inputs；
- closure report；
- query DTO。

要求使用专用 query service；禁止把 ORM graph 直接 JSON 化。

## PR-14：AuditFinding + ImpactAssessment + Correction

交付：

- governance tables；
- TargetResolver registry；
- downstream impact query；
- validity projection；
- immutable correction。

## PR-15：FastAPI Adapter

交付：

- `/v1` routes；
- DTO validation；
- error mapping；
- request ID；
- OpenAPI smoke tests。

API 只调用 application service。

## PR-16：Typer CLI Adapter

交付：

- 最小 CLI；
- 与 API 共用 application service；
- trace 输出可读。

## PR-17：Golden Path E2E + Failure Injection

交付：

- 完整科研链 E2E；
- API/CLI 共用 application handler contract test；
- Agent-ready application boundary architecture test；
- code bug impact E2E；
- PostgreSQL constraint tests；
- migration clean install；
- Phase 1 exit report generator。

## PR-18：Phase 1 Hardening

交付：

- 索引检查；
- query explain 基线；
- error/log cleanup；
- architecture test coverage；
- Agent-ready Core boundary audit；
- docs/API examples；
- unresolved TODO 清零或转 Phase 2 issue。

Phase 1 只有 PR-18 Gate 通过后才能申请 GO-to-Phase-2。

---

# 21. 多人并行分工

推荐 4 个工作包：

| WP | Owner | PR | 依赖 |
|---|---|---|---|
| WP-A Foundation/Persistence | Dev A / Tech Lead | 00–03 | 无 |
| WP-B Research/Experiment | Dev B | 04–05, 09 | A |
| WP-C Evidence | Dev C | 06–08, 10–12 | A；Run 接口与 B 对齐 |
| WP-D Query/Governance/API | Dev D | 13–18 | A–C public interface |

并行原则：

- PR-06/07/08 可与 PR-04/05 并行；
- PR-09 必须等待 05/06/07；
- PR-10 等待 08/09；
- PR-12 等待 10/11；
- PR-13 以后等待主链稳定。

Tech Lead 必须 owner：

```text
foundation/*
persistence/uow.py
migrations/*
Run state machine
Claim freeze semantics
ProvenanceClosureValidator
architecture tests
```

---

# 22. Code Review Checklist

每个 PR Reviewer 必查：

## Domain

- 是否把 ORM/API 逻辑放进 Domain？
- 是否新增了未批准的 Canonical Entity？
- 是否把 FROZEN/immutable 对象原位修改？
- 是否复制了第二份 Source of Truth？

## Persistence

- 主链是否 concrete FK？
- 是否错误用了 CASCADE？
- 是否缺 UNIQUE/CHECK？
- 是否用 JSON 藏了应该关系化的 provenance ID？
- migration 是否可重复从空库构建？

## Application

- 是否一个 command 一个 transaction？
- 是否 handler 自己 commit？
- 是否并发冲突被 last-write-wins？
- 是否所有 cross-domain invariant 在 service 中检查？

## API

- DTO 是否与 Domain/ORM 解耦？
- 是否暴露内部异常？
- write response 是否返回 canonical/version/hash/timestamp？

## Tests

- happy path；
- invalid transition；
- frozen mutation；
- FK violation；
- concurrency；
- provenance closure；
- migration。

---

## Agent-ready Core（v1.1）

- Application Command 是否依赖某个 UI/HTTP/Agent framework？
- Query 是否足以让未来 Agent 获取 canonical state，而无需 ORM/SQL 旁路？
- 是否使用 canonical/version ID 作为机器接口？
- 是否错误保存 conversation/agent working memory 为 scientific truth？
- 是否加入第三方 Agent 项目专属字段？
- Coding Agent 类输出是否能够通过 ArtifactVersion → Run 进入 provenance？
- Human 与未来 Agent 是否走同一 Command/Query 语义？

# 23. Definition of Done

一个功能只有满足以下条件才算 Done：

1. Domain invariant 有单测；
2. Repository 有 PostgreSQL 集成测试；
3. Migration 有 clean-install test；
4. API/CLI 若暴露则有 adapter test；
5. 错误码稳定；
6. 不破坏 architecture tests；
7. 不新增未批准 schema；
8. 文档/API 示例更新；
9. 所有 material provenance 可 trace；
10. 没有通过 JSON/soft ref 绕开 FK；
11. Application boundary 对 Human/CLI/Future Agent 保持中立；
12. 未引入 vendor-specific scientific state。

---

# 24. Phase 1 Exit Criteria

Phase 1 完成必须同时满足：

```text
[ ] PR-00～PR-18 全部合并
[ ] PostgreSQL clean migration PASS
[ ] Architecture tests PASS
[ ] Version freeze tests PASS
[ ] Run seal/terminal immutability PASS
[ ] DatasetSnapshot mandatory boundary PASS
[ ] ArtifactVersion frozen input PASS
[ ] Measurement immutability PASS
[ ] StatisticalResult input integrity PASS
[ ] Claim evidence-set freeze PASS
[ ] Frozen Provenance Closure PASS
[ ] Claim → Evidence → Run → Inputs 双向 trace PASS
[ ] AuditFinding → ImpactAssessment → affected Claim PASS
[ ] 错误注入不修改历史事实 PASS
[ ] API/CLI 共用 application service PASS
[ ] Agent-ready application boundary PASS
[ ] Core 无第三方 Agent vendor-specific scientific schema PASS
[ ] Query layer 足以支持未来 Agent canonical-state access PASS
[ ] 无 scientific ON DELETE CASCADE
[ ] 无主链 polymorphic soft ref
[ ] 无 P0/P1 架构 TODO
```

完成后生成：

```text
phase1_exit_report.md
migration_inventory.md
api_contract_snapshot.json
architecture_test_report.md
```

然后 STOP，等待 Phase 2 GO。

---

# 25. Codex 执行提示词模板

将本规范交给 Codex 时，建议每次只执行一个 PR：

```text
You are implementing ResearchBase Phase 1.

Authoritative specifications:
1. ResearchBase 全系统设计文档_架构补全版_v1.2
2. ResearchBase Phase 1 Development Specification v1.1

Implement PR-XX only.

Rules:
- Do not implement later PRs.
- Do not add new canonical entities without an Architecture Change Note.
- Preserve concrete FK provenance.
- Never mutate frozen versions or immutable scientific records.
- One application command equals one database transaction.
- PostgreSQL is the integration-test database.
- Keep Application Command/Query neutral to Human UI, CLI, and future Agent adapters.
- Do not add STORM/EvoScientist/LangGraph/OpenHands/Codex-specific scientific fields.
- Do not implement Agent Runtime or third-party research-agent integrations unless the named PR explicitly requires it.
- Add domain, integration, migration, and architecture tests required by the PR.
- At the end, produce:
  1. changed-files summary,
  2. migrations,
  3. tests executed and results,
  4. unresolved issues,
  5. explicit statement that no later PR was implemented.
Stop after PR-XX.
```

---

# 26. 关键实现示例

## 26.1 Claim freeze

```python
def freeze_claim_version(cmd: FreezeClaimVersion, uow: UnitOfWork) -> WriteResult:
    with uow:
        version = require_claim_version(
            uow.claims.get_version_for_update(cmd.claim_version_id)
        )
        if version.status is not VersionStatus.DRAFT:
            raise InvalidStateTransition("Only DRAFT claim version can be frozen.")

        evidence = uow.claims.list_evidence(version.id)
        support_hash = hash_evidence_set(evidence)

        version.freeze(
            support_set_hash=support_hash,
            frozen_at=clock.now(),
        )

        uow.claims.save_version(version)
        uow.claims.set_current_version(
            claim_id=version.claim_id,
            version_id=version.id,
            expected_row_version=cmd.expected_claim_row_version,
        )
        uow.commit()
        return WriteResult.from_version(version)
```

## 26.2 Evidence set hash

```python
def hash_evidence_set(relations: Sequence[EvidenceRelation]) -> str:
    material = [
        {
            "source_type": r.source_type,
            "source_id": str(r.source_id),
            "relation_type": r.relation_type,
            "qualification": r.qualification,
        }
        for r in relations
    ]
    material.sort(
        key=lambda x: (
            x["source_type"],
            x["source_id"],
            x["relation_type"],
            x["qualification"] or "",
        )
    )
    return sha256_canonical_json(material)
```

## 26.3 Run seal

```python
def start_run(cmd: StartRun, uow: UnitOfWork) -> WriteResult:
    with uow:
        run = require_run(uow.runs.get_for_update(cmd.run_id))
        if run.status is not RunStatus.PLANNED:
            raise InvalidStateTransition(...)

        spec = require_spec_version(
            uow.experiment_specs.get_version(run.experiment_spec_version_id)
        )
        require_frozen(spec)

        for item in uow.runs.list_artifact_inputs(run.id):
            require_frozen(uow.artifacts.get_version(item.artifact_version_id))

        run.start(clock.now())
        uow.runs.save(run, expected_row_version=cmd.expected_row_version)
        uow.commit()
        return WriteResult.from_run(run)
```

---

# 27. 开发团队不得自行决定的事项

出现以下问题必须提交 Architecture Question/ADR，不得直接编码：

- 是否新增 DatasetVersion；
- 是否把 Configuration/Environment 从 ArtifactVersion 拆出；
- 是否允许 RUNNING 状态记录 Measurement；
- 是否允许跨 Project Evidence；
- 是否引入 generic polymorphic reference；
- 是否增加 hard delete；
- 是否改变 Claim freeze 语义；
- 是否改变 Run input seal 时点；
- 是否用 SQLite 代替 PostgreSQL 集成测试；
- 是否引入 Kafka/Redis/Celery/微服务；
- 是否把 Governance/Approval 提前到 Phase 1；
- 是否引入 Agent workflow；
- 是否加入任何第三方 Agent framework 专属 scientific schema；
- 是否允许 Agent adapter 绕过 Application Command/Query 直接访问数据库。

---

# 28. 最终施工结论

Phase 1 的开发团队不需要重新设计 ResearchBase。团队只需要严格完成四件事：

```text
1. 正确实现 Version / Immutability
2. 正确实现 Run 输入冻结
3. 正确实现 Evidence → Claim 冻结
4. 正确实现可验证的 Provenance Trace / Impact Trace
```

如果实现过程中出现“为了方便，先把 ID 塞 JSON”“先 UPDATE frozen row”“先用 generic target_type/target_id”“先让 handler 自己 commit”等做法，应直接视为架构回归，而不是实现捷径。

**Phase 1 成功的判断标准不是接口数量，而是：给定任意一个 Frozen ClaimVersion，系统能确定性地追溯到其证据、测量、Run、ExperimentSpecVersion、DatasetSnapshot 与 ArtifactVersion；给定任意一个上游错误对象，又能确定性地找出受影响的 ClaimVersion，同时不篡改历史事实。**


# 29. v1.1 Agent-ready Core 验收结论

本修订不改变 Phase 1 的核心交付：Version/Immutability、Run input sealing、Evidence/Claim freezing、Provenance/Impact trace。

新增的是边界约束：

```text
                    ┌── Human UI
ResearchBase Core ←─┼── CLI
                    ├── Service
                    └── Future Scientific Agent Runtime
```

所有调用者汇聚到同一个 Application Command/Query boundary。Phase 2/3 接入 STORM-like ResearchStrategy、PaperQA2、EvoScientist-like orchestration、OpenHands/Codex CodingCapability 时，应主要新增 Agent Runtime、Strategy、Capability Adapter 与 execution provenance，而无需重构 Phase 1 canonical entities。

如果未来接入 Agent 时必须大规模改写 Hypothesis、ExperimentSpec、Run、DatasetSnapshot、ArtifactVersion、Measurement、StatisticalResult 或 Claim，说明 Phase 1 的 Agent-ready Core 验收失败。

---

# 27. Harness Integration Addendum — Phase 1

## 27.1 Scope Rule

Phase 1 continues to prohibit implementation of the ResearchBase Agent Runtime, autonomous scientific workflows, Skill Router, CapabilityGateway, STORM/EvoScientist runtime integration or scientific-agent canonical execution. Engineering harnesses may assist **development only**.

## 27.2 PR Engineering Harness

Every PR SHOULD execute the following bounded workflow:

```text
target PR scope
→ authoritative context pack
→ spec validation
→ implementation plan/task breakdown
→ implementation
→ PR-required tests
→ independent code review
→ architecture/invariant review
→ verification-before-completion
→ PR evidence package
→ STOP
```

Harness execution MUST NOT widen the named PR. The existing `Implement PR-XX only` rule remains controlling.

## 27.3 Phase-1 Harness Files

Phase 1 repository bootstrap MAY include engineering-governance files that do not implement product Agent Runtime:

```text
AGENTS.md
harness.lock.yaml
config/harness/engineering_policy.yaml
docs/harness/engineering_workflow.md
```

Scientific Skill routing/runtime files are deferred unless needed purely as inert design/evaluation assets and MUST NOT be wired into ResearchBase runtime during Phase 1.

## 27.4 Development Harness Fingerprint

Each PR evidence package SHOULD record a development harness fingerprint (tool/runtime revision, AGENTS.md/config hashes, pinned engineering Skill/Plugin revisions when used). This fingerprint is **development evidence**, not a new canonical scientific entity and not automatically a Run input.

If a future scientific Run materially consumes an agent-generated code/config artifact, the existing ArtifactVersion and Run input rules apply to that artifact; Phase 1 MUST NOT add a harness-specific canonical schema to accomplish this.

## 27.5 Definition of Done Extension

In addition to Section 23, a PR is Done only when:

1. target PR scope was not exceeded;
2. required engineering harness gates were executed or a documented exception exists;
3. an independent review occurred for material code;
4. completion claims are backed by machine-verifiable evidence;
5. external harness dependencies used for the PR are pinned/resolved in the evidence;
6. no harness instruction bypassed Application/Repository architecture boundaries;
7. no Agent Runtime or scientific Skill runtime leaked into Phase 1 product scope.

## 27.6 PR Evidence Package

Recommended non-canonical development evidence:

```text
pr_evidence/PR-XX/
  implementation_summary.md
  changed_files.txt
  test_report.txt
  code_review.md
  architecture_review.md
  unresolved_findings.md
  harness_fingerprint.json
```

These files support engineering auditability. They do not replace repository tests, migrations, canonical provenance, or ADRs.

## 27.7 Additional Architecture Tests

Phase 1 SHOULD add repository/CI checks where practical for:

```text
external harness dependencies are pinned
AGENTS.md/harness policy cannot authorize direct canonical DB mutation
third-party harness changes do not modify canonical schema without ADR
Phase-1 code contains no product Agent Runtime wiring
```

## 27.8 Updated Codex Execution Rule

The existing Section 25 prompt remains valid. Add:

```text
Use the repository-approved engineering harness only as a development process.
The harness does not authorize work outside PR-XX.
Do not implement ResearchBase Agent Runtime or scientific Skill routing in Phase 1.
Do not claim completion without reporting executed verification evidence.
Stop after PR-XX.
```

