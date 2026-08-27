# ResearchBase Phase 2 Development Specification

> **版本**：v1.0  
> **状态**：DESIGN COMPLETE / READY FOR CROSS-PHASE REVIEW  
> **日期**：2026-08-26  
> **上位设计**：`ResearchBase_全系统设计文档_架构补全版_v1.2`  
> **前置规范**：`ResearchBase_Phase1_Development_Specification_v1.1`  
> **适用对象**：Tech Lead、Literature/Publication/Governance 开发人员、Research Agent 开发人员、Codex/Coding Agent  
> **规范性**：本文件定义 Phase 2 的施工边界、数据模型、Application Contracts、Adapter Contracts、测试与 PR 顺序。Phase 2 不得破坏 Phase 1 Frozen Provenance Closure 与 canonical state ownership。

---

# 0. Phase 2 目标

Phase 1 解决：

```text
Hypothesis
→ ExperimentSpec
→ Run
→ Measurement / StatisticalResult
→ EvidenceRelation
→ Claim
```

Phase 2 在此基础上补齐：

```text
Research Question
→ Literature Research
→ SourceVersion / LiteratureEvidence
→ Research Discussion
→ ScientificConclusion
→ ManuscriptVersion
→ Internal Review / Decision / Approval
```

Phase 2 的核心目标：

> **Human + Research Agents 能围绕同一 canonical research state 完成可核验文献调研、学术讨论、科学结论构建、稿件生成和内部治理，而不让 Agent conversation、STORM/PaperQA state 或稿件文本成为第二套科学事实。**

Phase 2 结束时应具备：

```text
ResearchQuestionVersion
→ LiteratureSearchPlan
→ LiteratureSearchRun
→ LiteratureSource / SourceVersion
→ LiteratureEvidence
→ ResearchBrief
→ ScientificConclusionVersion
→ ManuscriptVersion
→ InternalReviewRecord
→ DecisionRecord
```

并与 Phase 1 主链连接：

```text
ClaimVersion → ScientificConclusionVersion → ManuscriptVersion
SourceVersion / LiteratureEvidence → ScientificConclusionVersion → ManuscriptVersion
```

# 1. Phase 2 范围

## 1.1 MUST 实现

```text
LiteratureSource
SourceVersion
Source identity resolution
LiteratureSearchPlan / LiteratureSearchRun
SearchQuery / SearchResult provenance
LiteratureEvidence
CitationRelation
ResearchBrief Artifact
STORM-like ResearchStrategy interface
PaperQA2 Capability Adapter
Academic Discussion Room prototype
ScientificConclusion / Version
Publication / ManuscriptVersion
InternalReviewRecord / ReviewIssue
DecisionRecord
basic ApprovalRequest / ApprovalDecision / ApprovalGrant
Claim-to-Manuscript placement
Literature-to-Manuscript citation placement
```

## 1.2 SHOULD 实现

```text
PriorArtRelation
NoveltyAssessment basic
SearchCoverage
AuthorResponse
RevisionAction
Manuscript semantic-change assessment
```

## 1.3 MAY 实现

```text
Co-STORM thin adapter prototype
multiple search providers
PDF/full-text extraction adapters
bibliographic metadata enrichment
citation style rendering
basic AuthorshipSnapshot
```

## 1.4 MUST NOT 实现

```text
full Scientific Agent Runtime
EvoScientist-like orchestration
AI Scientist-v2 tree search
Coding Agent orchestration
autonomous experiment loop
automatic venue submission
ExternalEffect connectors
full P0–P4 Authority Engine
full COI/Appeal
full authorship dispute
full systematic-review platform
full reference-manager replacement
microservices split
```

# 2. 核心原则

```text
LiteratureSource ≠ LiteratureEvidence
CitationPlacement ≠ ClaimSupport
STORM/PaperQA output ≠ canonical truth
Discussion ≠ Decision
Manuscript ≠ Scientific Truth
Review ≠ Decision ≠ Approval
Agent Output ≠ Canonical State
```

LiteratureEvidence 必须绑定 FROZEN SourceVersion 与 locator。STORM、PaperQA、Co-STORM 结果先作为 Candidate/Artifact/Assessment，经 Application Command 才可晋升。

# 3. 模块扩展

```text
src/researchbase/
├── literature/
│   ├── domain/{source,search,evidence,citation,novelty}.py
│   ├── application/
│   └── ports/{repositories,search_capability,scientific_rag_capability}.py
├── collaboration/
│   ├── domain/discussion.py
│   └── application/
├── publication/
│   ├── domain/{publication,manuscript,placement}.py
│   ├── application/
│   └── ports/
├── governance/
│   ├── domain/{review,decision,approval}.py
│   └── application/
├── strategies/research/{base,storm_like,human_guided}.py
└── adapters/
    ├── literature/{search,paperqa2}/
    └── research/storm/
```

仍采用 modular monolith。

# 4. Literature Core

## 4.1 LiteratureSource

```yaml
LiteratureSource:
  id: UUID
  source_kind: paper | preprint | thesis | book | web | standard | dataset_doc | other
  canonical_title: string
  primary_identifier_type: doi | arxiv | pmid | isbn | url | internal | other
  primary_identifier: string|null
  lifecycle_status: active | merged | retired
  current_version_id: UUID|null
  created_by: ActorId
  created_at: Instant
  row_version: int
```

## 4.2 SourceIdentifier

```yaml
SourceIdentifier:
  id: UUID
  literature_source_id: UUID
  identifier_type: doi | arxiv | pmid | semantic_scholar | openalex | url | isbn | other
  identifier_value: string
  normalized_value: string
  is_primary: bool
  verified_at: Instant|null
```

数据库约束：

```text
UNIQUE(identifier_type, normalized_value)
```

标题相似不得自动 merge。

## 4.3 SourceVersion

```yaml
SourceVersion:
  id: UUID
  literature_source_id: UUID
  version_number: int
  version_kind: submitted | preprint | revised_preprint | accepted | published | corrected | retracted | web_snapshot | other
  title: string
  abstract: string|null
  authors: StructuredValue
  publication_date: date|null
  venue: string|null
  external_version_label: string|null
  fulltext_artifact_version_id: UUID|null
  metadata: StructuredValue|null
  content_hash: SHA256
  status: DRAFT | FROZEN | SUPERSEDED | ABANDONED
  created_by: ActorId
  created_at: Instant
  frozen_at: Instant|null
```

Formal LiteratureEvidence 只能引用 FROZEN SourceVersion。

# 5. Literature Search

## 5.1 LiteratureSearchPlan

```yaml
LiteratureSearchPlan:
  id: UUID
  project_id: UUID
  current_version_id: UUID

LiteratureSearchPlanVersion:
  id: UUID
  plan_id: UUID
  version_number: int
  status: VersionStatus
  research_question_refs: [FrozenReference<ResearchQuestionVersion>]
  objective: string
  source_scope: bibliographic | web | local_corpus | mixed
  inclusion_criteria: StructuredValue|null
  exclusion_criteria: StructuredValue|null
  time_range: StructuredValue|null
  language_scope: list[string]|null
  search_strategy: keyword | perspective_guided | systematic | snowball | hybrid
  planned_providers: list[string]
  stopping_rule: StructuredValue|null
  content_hash: SHA256
```

## 5.2 LiteratureSearchRun

```yaml
LiteratureSearchRun:
  id: UUID
  project_id: UUID
  search_plan_version_id: UUID
  strategy_id: string
  strategy_version: string
  status: PLANNED | RUNNING | SUCCEEDED | FAILED | CANCELLED
  started_at: Instant|null
  finished_at: Instant|null
  requested_by: ActorId
  executed_by: ActorId
  execution_context: StructuredValue|null
```

它与 Phase 1 scientific/computational `Run` 不合并。

## 5.3 SearchQueryRecord / SearchResultRecord

```yaml
SearchQueryRecord:
  id: UUID
  literature_search_run_id: UUID
  query_text: string
  perspective: string|null
  provider_id: string
  provider_version: string|null
  ordinal: int
  executed_at: Instant
  query_hash: SHA256
```

```yaml
SearchResultRecord:
  id: UUID
  search_query_record_id: UUID
  rank: int
  external_identifier: string|null
  title: string
  url: string|null
  snippet: string|null
  provider_score: decimal|null
  resolved_source_id: UUID|null
  resolved_source_version_id: UUID|null
  retrieved_at: Instant
```

SearchResult 是 retrieval provenance，不是 Evidence。

# 6. LiteratureEvidence

```yaml
LiteratureEvidence:
  id: UUID
  project_id: UUID
  source_version_id: UUID
  evidence_type: finding | method | dataset | limitation | contradiction | background | definition | prior_art | other
  locator:
    page: int|null
    section: string|null
    paragraph: string|null
    figure: string|null
    table: string|null
    quote_span: StructuredValue|null
  extracted_statement: string
  normalized_assertion: string|null
  extraction_method: human | agent | rule | imported
  extraction_execution_ref: StructuredValue|null
  confidence: high | medium | low | unknown
  review_status: unreviewed | verified | disputed | rejected
  created_by: ActorId
  created_at: Instant
  content_hash: SHA256
```

不保存大段受版权保护全文，只存必要 locator/短 span 与 normalized assertion。

LiteratureEvidenceRelation 可连接：

```text
ClaimVersion
ScientificConclusionVersion
ResearchQuestionVersion
HypothesisVersion
```

relation_type：

```text
supports | contradicts | qualifies | motivates | prior_art | contextualizes
```

主科学链优先 concrete FK。

# 7. Source Resolution

定义 `SourceResolver`：

```python
class SourceResolver(Protocol):
    def resolve(self, candidate, context: ExecutionContext) -> SourceResolutionResult: ...
```

优先：

```text
DOI → arXiv → PMID → ISBN → canonical URL → bibliographic fingerprint → unresolved
```

Source merge 必须通过 SourceMergeRecord，禁止删除历史 ID。

# 8. ResearchBrief

不新增 Canonical Entity，统一：

```text
Artifact
artifact_type = research_brief
```

ArtifactVersion metadata 记录 search plan/run、SourceVersion、strategy/version、generator provenance。ResearchBrief 不是 Evidence 本身。

# 9. STORM-like ResearchStrategy

Phase 2 MUST 提供 provider-neutral `ResearchStrategy`：

```python
class ResearchStrategy(Protocol):
    strategy_id: str
    strategy_version: str
    def prepare_plan(self, request, context) -> ResearchStrategyPlan: ...
    def execute(self, plan, capabilities, context) -> ResearchStrategyResult: ...
```

Native STORM-like Strategy：

```text
ResearchQuestion/topic
→ perspective discovery
→ perspective-guided queries
→ source-grounded Q&A
→ knowledge organization
→ ResearchBrief
```

输出：

```text
search_plan_candidate
source_candidates[]
literature_evidence_candidates[]
research_brief_candidate
open_question_candidates[]
hypothesis_candidates[]
warnings[]
execution_metadata
```

所有 candidate 通过 Application Service 晋升。

# 10. SearchCapability

```python
class SearchCapability(Protocol):
    capability_id: str
    version: str
    def search(self, request, context) -> SearchResponse: ...
```

SearchResponse 必须包含 provider/version/query/results/retrieved_at/warnings。Phase 2 SHOULD 支持至少两个 provider/test adapter，避免单一供应商绑定。

# 11. PaperQA2 ScientificRAGCapability

```python
class ScientificRAGCapability(Protocol):
    def answer(self, request, context) -> ScientificRAGResponse: ...
```

输入：

```text
question
source_version_ids[]
retrieval_constraints
```

输出：

```text
answer_candidate
evidence_candidates[]
contradictions[]
missing_evidence[]
adapter_id/version/model/provider
```

ResearchBase 保存 canonical SourceVersion/LiteratureEvidence；PaperQA 索引是 derived/cache。

安全要求：

- 禁止加载不可信 pickle/serialized index；
- cache/index 可重建；
- adapter failure 不破坏 canonical state；
- third-party index ID 不进入 Core。

# 12. Literature Application Commands

```text
register_literature_source
add_source_identifier
create_source_version
freeze_source_version

create_literature_search_plan
revise_literature_search_plan
freeze_literature_search_plan

start_literature_search
record_search_query
record_search_result
resolve_search_result
finish_literature_search

create_literature_evidence
verify_literature_evidence
dispute_literature_evidence
link_literature_evidence

create_research_brief
run_research_strategy
run_scientific_rag
```

External search/RAG 不允许长期占用 DB transaction：

```text
TX A: create RUNNING execution → commit
external I/O
TX B: persist results → commit
TX C: finish run → commit
```

# 13. Literature Queries

```text
get_literature_source
get_source_version_history
find_source_by_identifier
get_literature_search_run
get_search_provenance
get_literature_evidence
trace_literature_evidence_to_source
list_evidence_for_research_question
list_evidence_for_claim
list_contradictory_literature
get_search_coverage
```

# 14. Academic Discussion Room

Phase 2 做 prototype。

```yaml
DiscussionSession:
  id: UUID
  project_id: UUID
  topic: string
  input_refs: research_question_version_ids / claim_version_ids / source_version_ids
  status: OPEN | CLOSED | ARCHIVED
  created_by: ActorId
  created_at: Instant
```

```yaml
DiscussionTurn:
  id: UUID
  discussion_session_id: UUID
  ordinal: int
  actor_id: UUID
  role: human | moderator | literature_expert | method_expert | statistician | domain_critic | other
  utterance: text
  cited_source_version_ids: list[UUID]
  cited_claim_version_ids: list[UUID]
  created_at: Instant
```

正式实现优先 relation tables，不用 JSON 作为唯一引用。

Discussion 关闭/checkpoint 后生成：

```text
DiscussionTranscript ArtifactVersion
ConceptMap ArtifactVersion
ResearchSummary ArtifactVersion
```

ConceptMap 是 derived artifact。

Promotion 必须显式：

```text
promote_discussion_to_research_question
promote_discussion_to_hypothesis
promote_discussion_to_claim_draft
promote_discussion_to_decision_candidate
```


# 15. ScientificConclusion

ScientificConclusion 用于综合多个 Claim 和 LiteratureEvidence。

```yaml
ScientificConclusion:
  id: UUID
  project_id: UUID
  current_version_id: UUID
  created_by: ActorId
  created_at: Instant

ScientificConclusionVersion:
  id: UUID
  scientific_conclusion_id: UUID
  version_number: int
  status: DRAFT | FROZEN | SUPERSEDED | ABANDONED
  statement: text
  scope: StructuredValue
  confidence: strong | moderate | weak | inconclusive | mixed
  limitation_summary: text|null
  support_set_hash: SHA256|null
  content_hash: SHA256|null
  created_by: ActorId
  created_at: Instant
  frozen_at: Instant|null
```

Conclusion inputs 必须关系化：

```text
scientific_conclusion_claim_inputs
scientific_conclusion_literature_inputs
```

Claim input：

```text
conclusion_version_id
claim_version_id
relation_type
ordinal
```

Literature input：

```text
conclusion_version_id
literature_evidence_id
relation_type
ordinal
```

freeze 后 input set immutable；支持集合变化必须新建 Version。

# 16. Publication / Manuscript

## 16.1 Publication

```yaml
Publication:
  id: UUID
  project_id: UUID
  publication_type: paper | preprint | report | thesis | technical_report | other
  title: string
  lifecycle_status: drafting | internal_review | ready | submitted | accepted | published | withdrawn | archived
  current_manuscript_version_id: UUID|null
  created_by: ActorId
  created_at: Instant
  row_version: int
```

Phase 2 重点做到 internal_review/ready；SubmissionVersion 可以冻结，但不接 venue API。

## 16.2 ManuscriptVersion

```yaml
ManuscriptVersion:
  id: UUID
  publication_id: UUID
  version_number: int
  status: DRAFT | FROZEN | SUPERSEDED | ABANDONED
  document_artifact_version_id: UUID
  title: string
  abstract: string|null
  semantic_change_class: initial | editorial | scientific_minor | scientific_material
  content_hash: SHA256
  created_by: ActorId
  created_at: Instant
  frozen_at: Instant|null
```

稿件正文保存为 ArtifactVersion；ManuscriptVersion 保存业务语义和科学映射。

# 17. Manuscript Scientific Placement

## 17.1 ManuscriptClaimPlacement

```yaml
ManuscriptClaimPlacement:
  id: UUID
  manuscript_version_id: UUID
  claim_version_id: UUID|null
  scientific_conclusion_version_id: UUID|null
  section_id: string
  locator: StructuredValue
  rhetorical_strength: descriptive | suggestive | supported | strong
```

claim/conclusion 满足 XOR。

## 17.2 ManuscriptCitationPlacement

```yaml
ManuscriptCitationPlacement:
  id: UUID
  manuscript_version_id: UUID
  source_version_id: UUID
  section_id: string
  locator: StructuredValue
  citation_purpose: background | method | comparison | evidence | prior_art | dataset | other
```

CitationPlacement 只是引用位置；真正 scientific support 仍需 LiteratureEvidence relation。

## 17.3 Figure / Table

复用 ArtifactVersion：

```text
artifact_type = figure
artifact_type = table
```

ManuscriptVersion 通过 relation/placement 冻结 exact ArtifactVersion。

# 18. Writing Capability Boundary

Phase 2 可以实现基础 manuscript generation capability，但不实现完整 Phase 3 WritingAgent Runtime。

输入必须来自：

```text
Frozen ClaimVersion[]
Frozen ScientificConclusionVersion[]
Verified LiteratureEvidence[]
Frozen SourceVersion[]
Figure/Table ArtifactVersion[]
```

原则：

> **Write from canonical claims/evidence, not opaque chat memory.**

输出：

```text
Manuscript draft ArtifactVersion
placement candidates
citation candidates
```

随后通过 Application Commands：

```text
create_manuscript_version
attach claim/conclusion placements
attach citations/artifacts
freeze_manuscript_version
```

# 19. Internal Review

## 19.1 InternalReviewRecord

```yaml
InternalReviewRecord:
  id: UUID
  project_id: UUID
  target_type: manuscript_version | claim_version | scientific_conclusion_version | research_brief
  target_id: UUID
  target_content_hash: SHA256|null
  reviewer_actor_id: UUID
  review_type: scientific | statistical | literature | reproducibility | editorial | comprehensive
  recommendation: accept | minor_revision | major_revision | reject | uncertain
  summary: text
  created_at: Instant
  content_hash: SHA256
```

ReviewRecord immutable。

## 19.2 ReviewIssue

```yaml
ReviewIssue:
  id: UUID
  review_record_id: UUID
  severity: info | minor | major | blocking
  issue_type: unsupported_claim | citation | statistical | methodological | reproducibility | overclaim | contradiction | novelty | writing | other
  target_locator: StructuredValue|null
  description: text
  related_claim_version_id: UUID|null
  related_source_version_id: UUID|null
  related_run_id: UUID|null
  status: open | addressed | dismissed
```

Review 不直接修改 Target：

```text
ReviewRecord
→ ReviewIssue
→ DecisionRecord
→ RevisionAction
→ new Version
```

# 20. DecisionRecord

Phase 2 实现 basic Decision：

```yaml
DecisionRecord:
  id: UUID
  project_id: UUID
  decision_type: research | revision | publication | literature | governance
  question: text
  decision: text
  rationale: text
  decided_by: ActorId
  decided_at: Instant
  supersedes_decision_id: UUID|null
  content_hash: SHA256
```

Decision basis 优先使用 typed relation tables，不用万能 JSON。

# 21. Basic Approval

## 21.1 ApprovalRequest

```yaml
ApprovalRequest:
  id: UUID
  project_id: UUID
  target_type: manuscript_version | scientific_conclusion_version
  target_id: UUID
  target_content_hash: SHA256
  approval_purpose: internal_scientific_release | ready_for_submission
  requested_by: ActorId
  requested_at: Instant
  status: pending | decided | withdrawn
```

## 21.2 ApprovalDecision

```yaml
ApprovalDecision:
  id: UUID
  approval_request_id: UUID
  decision: approve | reject | approve_with_conditions
  conditions: StructuredValue|null
  rationale: text
  decided_by: ActorId
  decided_at: Instant
  content_hash: SHA256
```

## 21.3 ApprovalGrant

```yaml
ApprovalGrant:
  id: UUID
  approval_decision_id: UUID
  status: active | consumed | expired | revoked | stale
  scope: StructuredValue
  valid_until: Instant|null
```

Phase 2 不实现完整 P4 eligibility engine，但必须保留未来 Authority engine 接口。Approval 不能覆盖 invalid scientific fact。

# 22. Review / Revision Flow

```text
ManuscriptVersion v1 FROZEN
→ InternalReviewRecord
→ ReviewIssue[]
→ DecisionRecord
→ ManuscriptVersion v2 DRAFT
→ revisions
→ freeze v2
→ targeted re-review
```

旧 v1 永不覆盖。

可使用轻量 `RevisionAction`：

```yaml
RevisionAction:
  id: UUID
  review_issue_id: UUID|null
  decision_record_id: UUID|null
  action_type: manuscript_edit | claim_revision | new_experiment | citation_change | analysis_change | no_change
  target_ref: StructuredReference
  resulting_version_ref: StructuredReference|null
  created_at: Instant
```

# 23. SubmissionVersion

Phase 2 基础实现但不自动投稿。

```yaml
SubmissionVersion:
  id: UUID
  publication_id: UUID
  version_number: int
  manuscript_version_id: UUID
  authorship_snapshot_id: UUID|null
  package_manifest_hash: SHA256
  status: PREPARED | FROZEN | SUPERSEDED | WITHDRAWN
  created_by: ActorId
  created_at: Instant
  frozen_at: Instant|null
```

它只表示“准备送出的冻结包”，不产生 ExternalEffect。

# 24. Authorship 最小实现

为 Submission freeze，Phase 2 可实现：

```text
ContributionRecord
AuthorshipSnapshot
AuthorConsent
```

不实现复杂 dispute。

AuthorshipSnapshot 至少冻结：

```text
ordered author_actor_ids
corresponding_author_actor_ids
equal_contribution groups
contribution summary
```

# 25. Novelty / Prior Art Basic

## 25.1 PriorArtRelation

```yaml
PriorArtRelation:
  id: UUID
  claim_version_id: UUID
  source_version_id: UUID
  relation: identical | highly_similar | partial_overlap | related | contrasting | unclear
  rationale: text
  assessed_by: ActorId
  evidence_refs: list[LiteratureEvidenceId]
  created_at: Instant
```

## 25.2 SearchCoverage

```yaml
SearchCoverage:
  id: UUID
  search_plan_version_id: UUID
  search_run_ids: list[UUID]
  providers: list[string]
  query_count: int
  result_count: int
  resolved_source_count: int
  time_scope: StructuredValue
  coverage_limitations: text
  created_at: Instant
```

## 25.3 NoveltyAssessment

必须表达：

```text
no close prior art found under this search plan
```

而不是无证据声称：

```text
this is the first work ever
```

# 26. Artifact Policy

以下全部复用 Artifact/ArtifactVersion：

```text
ResearchBrief
DiscussionTranscript
ConceptMap
Manuscript document
Figure
Table
Review attachment
Search export
```

Domain entity 只持业务语义和 exact reference。

# 27. Adapter Registry

代码层定义，不新增 canonical DB table：

```python
class AdapterDescriptor(BaseModel):
    adapter_id: str
    adapter_version: str
    capability_type: str
    upstream_name: str | None
    upstream_version: str | None
    license: str | None
```

至少包含 search、paperqa2、storm adapters。

Invocation provenance SHOULD 保存：

```text
adapter_id/version
model/provider
request/correlation ID
started/finished time
artifact outputs
warnings/errors
```

# 28. STORM / Co-STORM Integration Decision

Phase 2：

```text
STORM-like native strategy = MUST
official STORM thin adapter = SHOULD prototype
Co-STORM full adapter       = MAY
```

第三方 upstream 必须 pin package/tag/commit。禁止把 STORM internal article/session state 当 canonical source/evidence store。

# 29. PaperQA2 Integration Decision

```text
ScientificRAGCapability interface = MUST
PaperQA2 adapter                   = MUST
PaperQA internal index            = derived/cache
```

Adapter 可重建 index；ResearchBase 持 canonical SourceVersion/LiteratureEvidence。

# 30. External Calls / Transactions

Search/LLM/RAG 属于外部 I/O，必须短事务：

```text
TX A create execution record → commit
external call
TX B persist candidates/results → commit
TX C finish execution → commit
```

Retry 不能制造重复 canonical source/evidence。

# 31. Error Model Extension

```text
SOURCE_IDENTITY_CONFLICT
SOURCE_VERSION_NOT_FROZEN
SEARCH_PLAN_NOT_FROZEN
SEARCH_RUN_NOT_COMPLETE
LITERATURE_EVIDENCE_UNVERIFIED
CITATION_SOURCE_NOT_FOUND
CONCLUSION_INPUT_NOT_FROZEN
MANUSCRIPT_INPUT_NOT_FROZEN
MANUSCRIPT_PLACEMENT_INVALID
REVIEW_TARGET_NOT_FROZEN
APPROVAL_TARGET_NOT_FROZEN
ADAPTER_UNAVAILABLE
ADAPTER_VERSION_MISMATCH
SOURCE_RESOLUTION_FAILED
EXTERNAL_RETRIEVAL_FAILED
```

# 32. API 最小契约

```text
POST /literature/sources
POST /literature/sources/{id}/versions
POST /literature/source-versions/{id}:freeze

POST /literature/search-plans
POST /literature/search-plan-versions/{id}:freeze
POST /literature/search-runs
POST /literature/search-runs/{id}:execute

POST /literature/evidence
POST /literature/evidence/{id}:verify
POST /literature/evidence/{id}:link

POST /research-strategies/storm-like:run
POST /scientific-rag:query

POST /discussions
POST /discussions/{id}/turns
POST /discussions/{id}:close
POST /discussions/{id}:promote

POST /scientific-conclusions
POST /scientific-conclusion-versions/{id}/claims
POST /scientific-conclusion-versions/{id}/literature-evidence
POST /scientific-conclusion-versions/{id}:freeze

POST /publications
POST /publications/{id}/manuscript-versions
POST /manuscript-versions/{id}/claim-placements
POST /manuscript-versions/{id}/citations
POST /manuscript-versions/{id}:freeze

POST /reviews
POST /reviews/{id}/issues
POST /decisions
POST /approvals/requests
POST /approvals/requests/{id}/decisions

GET /manuscript-versions/{id}/scientific-trace
GET /literature/evidence/{id}/source-trace
```

URL 是否带 `/v2` 是 adapter 设计，不要求破坏 Phase 1 API。

# 33. Trace Contracts

## 33.1 Manuscript Scientific Trace

```text
ManuscriptVersion
→ ClaimPlacement
→ ClaimVersion
→ EvidenceRelation
→ Measurement/StatisticalResult
→ Run

ManuscriptVersion
→ ScientificConclusionPlacement
→ Conclusion inputs
→ ClaimVersion / LiteratureEvidence

ManuscriptVersion
→ CitationPlacement
→ SourceVersion
```

输出必须区分：

```text
scientific support path
citation-only path
```

## 33.2 Literature Trace

```text
LiteratureEvidence
→ SourceVersion
→ LiteratureSource
→ SourceIdentifier
→ SearchResult
→ SearchQuery
→ LiteratureSearchRun
→ SearchPlanVersion
```

## 33.3 Review Trace

```text
ReviewIssue
→ Frozen target
→ Decision
→ RevisionAction
→ resulting Version
```

# 34. Frozen Provenance Closure Extension

Phase 2 扩展至：

```text
ScientificConclusionVersion
ManuscriptVersion
SubmissionVersion
```

ScientificConclusion closure：

- conclusion FROZEN；
- ClaimVersion inputs FROZEN；
- LiteratureEvidence 存在；
- SourceVersion FROZEN；
- support_set_hash 一致；
- Claim closure 完整。

Manuscript closure：

- manuscript FROZEN；
- document ArtifactVersion FROZEN；
- Claim/Conclusion placement 指向 FROZEN target；
- SourceVersion FROZEN；
- Figure/Table ArtifactVersion FROZEN；
- scientific target closure 完整。

Submission closure：

- SubmissionVersion FROZEN；
- Manuscript closure complete；
- AuthorshipSnapshot frozen；
- package manifest hash 一致。

# 35. Literature Quality Gate

ResearchBrief / NoveltyAssessment formal review 前至少报告：

```text
search_plan
providers
query_count
time range
source count
unresolved result count
coverage limitations
```

不得无依据声称 comprehensive/systematic/first-ever/no prior work。

Agent extraction 默认 `unreviewed`；进入重要 ScientificConclusion 的关键 LiteratureEvidence SHOULD VERIFIED。

# 36. Citation Integrity Audit

基础规则：

```text
citation source exists
source version frozen
citation locator valid
retracted source warning
citation purpose present
citation placement does not itself create scientific support
```

Source corrected/retracted：

```text
AuditFinding
→ ImpactAssessment
→ affected LiteratureEvidence
→ Conclusion / Manuscript
```

# 37. Internal Review Quality Gate

ready-for-submission internal gate 至少检查：

```text
unsupported Claim placement
overclaim
unverified literature evidence
missing citation
citation-only treated as support
stale/invalid Claim
closure violation
unresolved blocking ReviewIssue
```

# 38. Basic Approval Gate

至少要求：

```text
ManuscriptVersion FROZEN
Manuscript closure complete
no blocking ReviewIssue
required internal reviews complete
no INVALID scientific inputs
AuthorshipSnapshot available if SubmissionVersion prepared
```

这不是 external submission。

# 39. Phase 2 Database Increment

建议新增约 30–40 张 core/relation tables：

```text
literature_sources
source_identifiers
source_versions
literature_search_plans
literature_search_plan_versions
literature_search_runs
search_query_records
search_result_records
literature_evidence
literature_evidence_relations
discussion_sessions
discussion_turns
scientific_conclusions
scientific_conclusion_versions
scientific_conclusion_claim_inputs
scientific_conclusion_literature_inputs
publications
manuscript_versions
manuscript_claim_placements
manuscript_citation_placements
manuscript_artifact_placements
internal_review_records
review_issues
decision_records
decision_basis_* relations
approval_requests
approval_decisions
approval_grants
submission_versions
authorship_snapshots
author_consents
prior_art_relations
search_coverage
novelty_assessments
revision_actions
source_merge_records
```

表少不是优化目标；provenance 与 FK 语义优先。

# 40. Key Constraints

```text
UNIQUE(identifier_type, normalized_value)
UNIQUE(literature_source_id, version_number)
UNIQUE(search_plan_id, version_number)
UNIQUE(scientific_conclusion_id, version_number)
UNIQUE(publication_id, manuscript_version_number)

all material frozen FK → ON DELETE RESTRICT

ReviewRecord immutable
DecisionRecord immutable
ApprovalDecision immutable
SourceVersion FROZEN material immutable
ManuscriptVersion FROZEN material immutable
ConclusionVersion FROZEN input set immutable
```


# 41. Test Matrix

## 41.1 Source Identity

- DOI normalization；
- arXiv normalization；
- duplicate identifier resolve/reject；
- same title + different DOI 不 merge；
- source merge preserves old refs。

## 41.2 SourceVersion

- version lineage；
- FROZEN cannot edit；
- corrected/retracted source creates new version；
- LiteratureEvidence requires SourceVersion；
- source hash stable。

## 41.3 Search

- SearchPlan must freeze；
- SearchRun records strategy/provider；
- query/result provenance complete；
- provider failure isolation；
- retry does not duplicate canonical source；
- unresolved results remain unresolved, not fabricated sources。

## 41.4 PaperQA2 Adapter

- only uses requested corpus/source set；
- answer candidate not auto canonical；
- evidence locator preserved；
- untrusted serialized index not loaded；
- adapter failure isolated；
- cache/index rebuild does not alter SourceVersion identity。

## 41.5 STORM-like Strategy

- multiple perspectives generated；
- generated queries persisted；
- retrieved sources resolved；
- ResearchBrief stored as ArtifactVersion；
- no STORM-specific DB fields；
- hypothesis/open-question candidates not auto frozen；
- provider change does not alter canonical schema。

## 41.6 Discussion

- transcript preserved；
- citations reference valid SourceVersion/ClaimVersion；
- close session does not create Hypothesis automatically；
- promotion explicit；
- ConceptMap is Artifact；
- discussion text not treated as DecisionRecord。

## 41.7 ScientificConclusion

- Claim/Literature input relations；
- support_set_hash stable；
- freeze locks inputs；
- changed support requires new version；
- closure includes Phase 1 Claim closure；
- invalid Claim propagates stale/invalid result.

## 41.8 Manuscript

- Claim/Conclusion placement XOR；
- CitationPlacement does not create support；
- frozen placements immutable；
- stale Claim produces trace warning；
- figure/table exact ArtifactVersion；
- document artifact exact hash；
- revision creates new ManuscriptVersion。

## 41.9 Review / Decision / Approval

- Review immutable；
- ReviewIssue transitions；
- Review cannot mutate manuscript；
- Decision new immutable record；
- Approval target frozen；
- Approval cannot make invalid scientific input valid；
- rejection does not mutate target。

# 42. E2E Golden Paths

## 42.1 Literature-to-Conclusion

```text
ResearchQuestionVersion
→ SearchPlan freeze
→ SearchRun
→ SourceVersion
→ LiteratureEvidence verify
→ ScientificConclusion DRAFT
→ link Claim + LiteratureEvidence
→ freeze Conclusion
```

Assert closure complete。

## 42.2 STORM-like Research

```text
ResearchQuestion
→ STORM-like Strategy
→ query records
→ sources
→ ResearchBrief Artifact
→ open-question/hypothesis candidate
→ explicit promote
→ canonical DRAFT object
```

Assert no third-party/strategy state becomes canonical without command.

## 42.3 PaperQA2

```text
SourceVersion corpus
→ ScientificRAG query
→ evidence candidates
→ review
→ LiteratureEvidence
→ verify
```

## 42.4 Discussion-to-Research

```text
DiscussionSession
→ moderator/expert/human turns
→ transcript/concept map
→ hypothesis candidate
→ explicit promote
→ HypothesisVersion DRAFT
```

## 42.5 Claim-to-Manuscript

```text
ClaimVersion FROZEN
ScientificConclusionVersion FROZEN
→ Manuscript draft
→ scientific placements
→ citations
→ freeze manuscript
→ scientific trace
```

## 42.6 Review Revision

```text
Manuscript v1 FROZEN
→ Review
→ blocking issue
→ Decision
→ Manuscript v2
→ re-review
```

v1 remains unchanged.

# 43. Failure Injection

## F1 — Retracted Literature

```text
SourceVersion
→ LiteratureEvidence
→ Conclusion
→ Manuscript

later retraction/correction
→ AuditFinding
→ ImpactAssessment
→ Conclusion/Manuscript stale
```

不得修改旧 LiteratureEvidence。

## F2 — Hallucinated Citation

Research Strategy / PaperQA candidate 给出无法 resolve 的 source：

```text
candidate warning/reject
no fabricated canonical SourceVersion
```

## F3 — Citation Supports Wrong Statement

稿件存在 CitationPlacement，但没有 LiteratureEvidence support relation。

Citation Integrity Audit 必须区分 citation-only path。

## F4 — Discussion Promotion Error

Agent/Human 在 DiscussionTurn 宣称某结论成立，但未 promote/link evidence：

- 不产生 canonical Claim；
- 不进入 Manuscript scientific placement。

## F5 — Review Bypass

ReviewIssue=blocking，但 Manuscript 直接请求 ready approval：

- Approval gate MUST reject；
- 不允许 manually toggle lifecycle state 绕过。

# 44. Security / Privacy / Copyright

Literature adapters：

- API keys/secrets 不进入 Artifact；
- fulltext licensing respected；
- 不默认公开缓存受版权保护全文；
- third-party prompt payload 最小化；
- PaperQA/local index 按 project/corpus 隔离；
- retrieved HTML/PDF 视为 untrusted input；
- HTML/script content 不执行；
- locator/source metadata 与全文 bytes 分离。

Discussion：

- transcript 可能含未公开想法；
- Workspace/Project access policy 控制；
- Agent 不自动向公共搜索/LLM provider发送 proprietary data；
- external provider scope 必须可配置。

# 45. Performance Baseline

Phase 2 不建设大型搜索引擎，但 SHOULD：

- Source identifier DB lookup p95 < 100ms；
- typical Manuscript scientific trace < 2s；
- external search latency 与 DB transaction 隔离；
- vector/fulltext index 不进入 PostgreSQL canonical hot path；
- trace query 使用 read model/explicit SQL，不序列化整个 ORM graph；
- search result ingestion 支持 batch insert。

# 46. Observability

External research execution：

```text
request_id
correlation_id
project_id
strategy_id/version
adapter_id/version
provider
query_hash
latency
result_count
error_code
```

LLM/RAG SHOULD 记录：

```text
provider/model
prompt template version
token/cost summary if available
```

禁止日志泄露 secrets、受限全文和大型 prompt payload。

# 47. Work Packages

| WP | 负责范围 | Owner |
|---|---|---|
| WP2-A Literature Core | Source/Search/Evidence | Dev A |
| WP2-B Research Strategy | SearchCapability、STORM-like、PaperQA2 | Dev B |
| WP2-C Collaboration | Discussion Room / promotion | Dev C |
| WP2-D Publication | Conclusion/Manuscript/placements | Dev D |
| WP2-E Governance | Review/Decision/Approval/E2E | Tech Lead / Dev E |

依赖：

```text
Phase1 Core → A
A → B
C 可在 Phase1 Application Boundary 稳定后并行
Phase1 + A → D
D → E
```

Tech Lead MUST own：

```text
Source identity merge policy
LiteratureEvidence semantics
ScientificConclusion freeze
Manuscript scientific placement
Review/Decision/Approval boundaries
Frozen Provenance Closure extension
Adapter security policy
```

# 48. PR Sequence

## PR2-00 — Phase 2 Bootstrap

- literature/publication/collaboration modules；
- migration baseline；
- architecture tests；
- new error codes。

## PR2-01 — LiteratureSource + SourceIdentifier

- canonical identity；
- identifier normalization；
- source merge/correction policy。

## PR2-02 — SourceVersion

- version/freeze；
- fulltext Artifact reference；
- corrected/retracted lineage。

## PR2-03 — LiteratureSearchPlan

- plan/version semantics；
- freeze；
- search coverage inputs。

## PR2-04 — LiteratureSearchRun + Query/Result Provenance

- external-call transaction pattern；
- query/result records；
- provider metadata。

## PR2-05 — LiteratureEvidence

- locator；
- verification state；
- LiteratureEvidenceRelation；
- source trace。

## PR2-06 — SearchCapability

- provider-neutral port；
- test adapter；
- at least 2 real/provider adapters if practical。

## PR2-07 — ScientificRAGCapability + PaperQA2

- adapter pin；
- untrusted index protections；
- evidence candidate output；
- adapter compatibility tests。

## PR2-08 — STORM-like Native ResearchStrategy

- perspective discovery；
- query generation；
- source-grounded organization；
- ResearchBrief artifact。

## PR2-09 — Official STORM Thin Adapter Prototype

- SHOULD；
- pin package/commit；
- compare outputs with native strategy；
- no Core dependency。

If external adapter instability blocks this PR, it MAY be deferred without blocking Phase 2 exit only if native STORM-like Strategy passes all required tests.

## PR2-10 — Academic Discussion Room

- sessions/turns；
- transcript/concept map Artifact；
- explicit promotion。

## PR2-11 — ScientificConclusion

- identity/version；
- Claim/Literature inputs；
- support hash；
- closure validator extension。

## PR2-12 — Publication + ManuscriptVersion

- publication identity；
- manuscript Artifact；
- version lifecycle。

## PR2-13 — Manuscript Scientific Placement

- Claim/Conclusion/Citation/Artifact placements；
- scientific trace query。

## PR2-14 — Internal Review

- ReviewRecord；
- ReviewIssue；
- frozen target rules。

## PR2-15 — DecisionRecord + RevisionAction

- typed decision basis；
- immutable decision；
- revision trace。

## PR2-16 — Basic Approval

- request/decision/grant；
- frozen target；
- blocking review gate。

## PR2-17 — SubmissionVersion + Minimal Authorship

- package manifest；
- AuthorshipSnapshot；
- AuthorConsent basic；
- no ExternalEffect。

## PR2-18 — Novelty / Prior Art Basic

- SearchCoverage；
- PriorArtRelation；
- conservative NoveltyAssessment。

## PR2-19 — E2E + Failure Injection

- golden paths；
- retracted source；
- hallucinated citation；
- citation-support confusion；
- discussion promotion；
- approval bypass。

## PR2-20 — Hardening

- indexes/query plans；
- adapter/version inventory；
- migration clean install/upgrade；
- license/security notes；
- documentation；
- Phase 2 exit report。

# 49. Architecture Tests

CI MUST 新增：

```text
test_literature_source_not_evidence
test_search_result_not_evidence
test_citation_not_claim_support
test_strategy_does_not_import_persistence
test_adapter_does_not_write_db
test_no_storm_specific_core_schema
test_no_paperqa_specific_core_schema
test_discussion_not_canonical_science
test_manuscript_not_scientific_source_of_truth
test_review_does_not_mutate_target
test_decision_does_not_mutate_history
test_approval_does_not_override_invalid_fact
test_external_call_not_inside_long_db_transaction
```

# 50. Code Review Checklist

## Literature

- Source identity 是否靠稳定 identifier？
- 是否仅凭标题自动 merge？
- Evidence 是否有 SourceVersion + locator？
- SearchResult 是否误当 Evidence？
- corrected/retracted version lineage 是否保留？
- 是否复制了不必要的大段原文？

## Strategy / Adapter

- STORM/PaperQA internal state 是否进入 Core？
- candidate 是否直接 canonical？
- adapter/upstream version 是否记录？
- external call 是否占用长 transaction？
- retry 是否制造重复 canonical source/evidence？
- third-party serialized index 是否可信？

## Collaboration

- Discussion 是否被当 Decision？
- ConceptMap 是否错误成为 canonical graph？
- Promotion 是否显式？

## Publication

- Manuscript 是否引用 exact FROZEN versions？
- CitationPlacement 是否误当 support？
- Claim/Conclusion placement 是否可 trace？
- FROZEN Manuscript 是否被 UPDATE？

## Governance

- Review 是否修改 target？
- Decision 是否覆盖旧记录？
- Approval 是否接受非 FROZEN target？
- Approval 是否能绕过 INVALID input？

# 51. Definition of Done

每个 Phase 2 功能必须：

1. Domain invariant 单测；
2. PostgreSQL Repository/constraint 集成测试；
3. Migration clean-install/upgrade；
4. Adapter contract tests（如涉及）；
5. Application Command/Query 契约；
6. error codes；
7. architecture tests；
8. source/claim/manuscript trace；
9. no vendor-specific Core state；
10. upstream version/license记录；
11. Phase 1 regression tests continue PASS。

# 52. Phase 2 Exit Criteria

```text
[ ] LiteratureSource identity resolution PASS
[ ] SourceVersion lineage/freeze PASS
[ ] LiteratureSearchPlan/Run provenance PASS
[ ] LiteratureEvidence source+locator trace PASS
[ ] STORM-like Native ResearchStrategy PASS
[ ] PaperQA2 Adapter PASS
[ ] Academic Discussion explicit promotion PASS
[ ] ScientificConclusion support-set freeze PASS
[ ] ScientificConclusion Frozen Provenance Closure PASS
[ ] ManuscriptVersion scientific placement PASS
[ ] Citation ≠ ClaimSupport PASS
[ ] Internal Review → Issue → Decision → Revision PASS
[ ] Basic Approval frozen target / blocking gate PASS
[ ] SubmissionVersion package freeze PASS
[ ] Retracted-source impact propagation PASS
[ ] Hallucinated citation rejection PASS
[ ] PostgreSQL migrations/integration PASS
[ ] No STORM/PaperQA vendor-specific Core schema PASS
[ ] Phase 1 Exit tests continue PASS
```

Phase 2 exit artifacts：

```text
phase2_exit_report.md
reference_system_inventory.md
adapter_compatibility_report.md
literature_trace_demo.md
publication_trace_demo.md
migration_inventory_phase2.md
```

然后 STOP，等待 Phase 3 GO。

# 53. Phase 2 → Phase 3 Stable Contract

Phase 3 Scientific Agent Runtime 应直接消费：

```text
ResearchQuestionVersion
HypothesisVersion
LiteratureSearchPlanVersion
LiteratureSource / SourceVersion
LiteratureEvidence
ResearchBrief ArtifactVersion
ScientificConclusionVersion
ManuscriptVersion
InternalReviewRecord
DecisionRecord
```

Phase 3 不应要求重构这些 canonical objects。

稳定 Application API：

```text
run_research_strategy
run_scientific_rag
create/verify/link_literature_evidence
get_literature_context
create/revise/freeze_scientific_conclusion
create/revise/freeze_manuscript
create_review
create_decision
get_scientific_trace
```

Phase 3 可以新增 Agent Runtime / CapabilityGateway，但只能通过这些 Application boundaries 消费/产生 canonical state。

# 54. Codex Execution Template

```text
You are implementing ResearchBase Phase 2.

Authoritative specifications:
1. ResearchBase 全系统设计文档_架构补全版_v1.2
2. ResearchBase Phase 1 Development Specification v1.1
3. ResearchBase Phase 2 Development Specification v1.0

Implement PR2-XX only.

Rules:
- Preserve all Phase 1 provenance and immutability invariants.
- LiteratureSource is not LiteratureEvidence.
- SearchResult is not LiteratureEvidence.
- CitationPlacement is not scientific support.
- STORM/PaperQA outputs are candidates until promoted through Application Commands.
- Do not expose STORM/PaperQA internal state as canonical scientific state.
- Do not implement Phase 3 Agent Runtime.
- Do not implement external venue submission.
- External search/RAG calls must not hold long DB transactions.
- Use concrete FK for material provenance.
- Frozen scientific/publication versions are immutable.
- Add domain, integration, migration, adapter, architecture, and E2E tests required by the PR.
- Stop after PR2-XX.

At the end report:
1. changed files,
2. migrations,
3. tests/results,
4. adapter/upstream versions if applicable,
5. architecture decisions/deviations,
6. unresolved issues,
7. explicit confirmation that no later PR was implemented.
```

# 55. Reference System Implementation Notes

Phase 2 开始施工前必须重新核验并 pin：

```text
Stanford OVAL STORM / knowledge-storm
FutureHouse paper-qa / PaperQA2
chosen Search providers
LLM/provider adapters
```

架构核验时的当前事实：

- STORM 的公开 package metadata 当前显示 `knowledge-storm` 1.1.1、MIT，并继续作为 modular knowledge curation engine；
- Co-STORM 示例支持多种 retriever，并支持 Human utterance injection；
- STORM/Co-STORM 适合作为 Strategy/Collaboration reference，而不是 canonical store；
- FutureHouse `paper-qa` 仍作为 PaperQA2 的主要 upstream；
- PaperQA issue tracker 当前存在 persisted search index 不安全反序列化相关安全议题，因此禁止加载不可信 serialized index。

具体实现不得依赖这段文字的版本号；必须在 PR2-07/09 时重新 pin tag/commit/license，并写入 `reference_system_inventory.md`。

# 56. Phase 2 Final Design Invariants

```text
P2-INV-001  LiteratureSource MUST remain distinct from LiteratureEvidence.
P2-INV-002  SearchResult MUST remain retrieval provenance, not scientific Evidence.
P2-INV-003  Formal LiteratureEvidence MUST resolve to an exact SourceVersion and meaningful locator.
P2-INV-004  CitationPlacement MUST NOT automatically create Claim support.
P2-INV-005  ResearchStrategy/Adapter internal state MUST NOT become canonical scientific state.
P2-INV-006  STORM/PaperQA-specific schema MUST NOT enter the Core.
P2-INV-007  Discussion content MUST require explicit promotion before becoming canonical research state.
P2-INV-008  ConceptMap/MindMap MUST remain derived Artifact unless separately justified by ADR.
P2-INV-009  ScientificConclusion input sets MUST freeze with the conclusion version.
P2-INV-010  ManuscriptVersion MUST reference exact frozen scientific objects and source/artifact versions.
P2-INV-011  Manuscript natural language MUST NOT become the sole source of scientific truth.
P2-INV-012  Review MUST NOT mutate its target.
P2-INV-013  Decision MUST preserve its historical basis and MUST NOT rewrite prior facts.
P2-INV-014  Approval MUST require a frozen target and MUST NOT override invalid deterministic facts.
P2-INV-015  External search/RAG calls MUST NOT hold long-running database transactions.
P2-INV-016  Corrected/retracted literature MUST preserve source version history and trigger impact propagation.
P2-INV-017  Novelty claims MUST NOT exceed documented search coverage.
P2-INV-018  Phase 2 MUST preserve every Phase 1 Frozen Provenance Closure invariant.
P2-INV-019  Phase 2 MUST expose stable Application boundaries for Phase 3 Agent Runtime.
P2-INV-020  External venue side effects remain out of scope.
```

# 57. Phase 2 最终施工结论

Phase 2 不是“自动综述工具”，而是：

```text
可追溯搜索
+
可核验文献证据
+
Human/Agent 学术协作
+
ScientificConclusion
+
Claim/Evidence-driven Manuscript
+
Internal Review / Decision / Approval
```

最终验收标准：

> **给定 ManuscriptVersion 中任意一个正式科学陈述，系统可以追溯到 Frozen Claim/ScientificConclusion，再追溯到 Phase 1 Experiment Evidence 和/或 Frozen LiteratureEvidence；给定任何被撤回、纠正或证伪的上游文献/实验对象，又可以精准找出受影响的 Conclusion/Manuscript，而不改写历史版本。**

---

# 55. Harness Integration Addendum — Phase 2

## 55.1 Scientific Strategy Layer

Phase 2 is the first phase in which selected scientific research Skills/strategies may become product capabilities, while the general Agent Runtime remains deferred to Phase 3. All such capabilities operate through the Phase-2 Application APIs and preserve canonical literature/evidence ownership.

Initial Phase-2 scientific capabilities SHOULD prioritize:

```text
RB-S01 research-question-refiner
RB-S02 literature-deep-research
RB-S03 literature-evidence-auditor
RB-S04 hypothesis-auditor
RB-S10 citation-auditor
```

They may initially be implemented as deterministic services/strategies plus thin agent-assisted adapters; they do not require the Phase-3 generic Skill Router.

## 55.2 STORM / Co-STORM Placement

STORM-like methodology is a replaceable strategy used by `literature-deep-research`, not canonical schema and not the Skill identity itself.

```text
RB-S02 literature-deep-research
  ├── baseline strategy
  ├── STORM-like native strategy
  └── optional thin external adapter
```

The existing `STORM-like Native ResearchStrategy PASS` exit gate remains authoritative. No STORM-specific Core entity/field is permitted.

## 55.3 PaperQA2 and External Research Tools

PaperQA2, scholarly APIs, MCP servers and other literature tools are capability providers. Their output remains untrusted/external until ResearchBase source identity resolution, locator verification and LiteratureEvidence creation rules succeed. Tool output alone is not canonical evidence.

## 55.4 Scientific Skill Contract

Any Phase-2 scientific Skill must declare:

```text
trigger/purpose
required canonical queries
allowed external capabilities
produced candidate artifacts
source-verification policy
termination/error behavior
required audit/evaluation
```

A Skill MUST NOT directly write Phase-2 tables. Promotion goes through existing Application Commands.

## 55.5 Source-Driven Research

External methodological, API, dataset and scholarly claims SHOULD resolve to primary/official sources when available. Search score, model confidence or citation appearance does not establish scientific truth.

## 55.6 Phase-2 Evaluation Gate

Before a production scientific Skill/strategy is enabled, validate at least:

```text
positive triggers
negative triggers
source resolution
insufficient-evidence behavior
hallucinated citation rejection
conflicting-evidence behavior
no vendor-specific Core state
Phase-1 regression
```

## 55.7 Phase-2 Exit Extension

Add to Section 52:

```text
[ ] Phase-2 scientific Skills use Application boundaries PASS
[ ] external research-tool output is not treated as canonical evidence PASS
[ ] STORM remains replaceable strategy, not Core state PASS
[ ] Skill/strategy revisions used in formal generated artifacts are identifiable PASS
[ ] scientific Skill trigger/evidence regression tests PASS
```

