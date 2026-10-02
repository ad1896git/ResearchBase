# Phase 2 hash payload contract — R2 v1.0

**Status: design-only closure.** This document fixes literal Phase 2 hash material for the owners in Architecture Correction §4 and the Phase 2 literature-support snapshot extension. It authorizes no migration, application code, test change, or Phase 1 hash change. The R1 typed FK/field contract in `13_Phase2_Schema_Field_Contract_v1.0.md` remains authoritative only for unaffected storage fields; A18 and R2 companions govern explicit R2 corrections. Any incompatible future material change requires an ADR and a new material version; existing digests remain verifiable.

## Common encoding and types

For every template below, replace each angle-bracket token with exactly one value of its declared type; angle brackets are documentation notation and are never serialized. No template permits extra or missing keys. Hash `SHA-256(canonical-json-v1(payload).UTF8)` as 64 lowercase hex characters; persist scheme `sha256-cjson-v1`. The serializer's existing key ordering, escaping, and number rules are unchanged. Normalize human-authored Phase 2 string material to Unicode NFC **when creating material**, before storage/hash; do not modify `canonical-json-v1` or reinterpret Phase 1 bytes. Preserve meaningful whitespace except explicitly normalized query text. Reject invalid Unicode. A decimal value is a canonical decimal **string** (no exponent, unnecessary leading/trailing zeros, or `-0`); counters and ordinals are JSON integers. Date is `YYYY-MM-DD`; instant is UTC `YYYY-MM-DDTHH:MM:SS.ffffffZ`; UUID is lowercase hyphenated canonical text; digest is lowercase 64-hex; enums use persisted uppercase names. A nullable field is always present with JSON `null`. Named JSON values are thawed from FrozenJSON and validated by their stated schema before hashing, never serialized as JSON strings. An empty list is `[]`, and a nullable structured field is `null` if absent.

`R(T)` below is the literal object `{"type":"T","id":"<uuid>","content_hash":"<digest>"}`. `I(T)` is `{"type":"T","id":"<uuid>"}`. `T` is a literal type name, not a database table name. A ref's hash is checked against an immutable record or frozen-material version; status SUPERSEDED does not invalidate historical identity. For `ApprovalRequest` and `ReviewIssue`, which have no own content hash, use the ID-only shape only where specified. An exact ref cannot be replaced by `latest`, a content hash alone, or a soft `target_type/target_id`. Canonical arrays of sets reject duplicate semantic members before hashing; sorting uses Unicode code point order for normalized strings and lowercase UUID lexical order for IDs, except where a specific composite sort is given. For R refs, the sort key is `(type,id,content_hash)` unless specified otherwise. Relation, input, placement, manifest, query, and contribution ordinals are zero-based contiguous `0..N-1` JSON integers within their declared kind or parent. Authored author order alone is one-based `1..N`. Ordinals remain in payloads when declared.

All own-content payloads exclude row `id`, unlisted parent/version, created/updated/frozen/captured/decided/merged/executed times, unlisted actor attribution, status and validity projections, row version, current pointer, hash scheme, all hash fields other than explicitly embedded child binding hashes, provider responses/cache/execution context, and relation-row IDs. Binding payloads likewise exclude parent and relation-row IDs. This exclusion is exhaustive; future columns do not silently enter existing material versions. Frozen formal reads recompute and compare both own and binding hashes and verify referenced closure. `HASH_MISMATCH` and `PROVENANCE_CLOSURE_VIOLATION` are fail-closed results. Later invalidity is a derived assessment, never a mutation of frozen bytes.

## Literal payload templates

Each fenced object is the entire JSON object before canonical key ordering. Placeholders use `string`, `integer`, `boolean`, `decimal-string`, `date`, `instant`, `uuid`, `digest`, `R(Type)`, `I(Type)`, `null`, or the named closed structured form defined below. Union `R(A|B)` means exactly one of those concrete types. A list placeholder denotes an array of the specified item shape. Numeric zero and Boolean false appearing in templates identify JSON types, not mandated values.

The named structured forms are also closed: `criteria = {"statements":["<string>"]}` with authored order and no blank statements; `time-range = {"from":"<date|null>","through":"<date|null>"}` with at least one bound and `from <= through` when both exist; `stopping-rule = {"rule":"<string>"}` with a nonblank explicit stopping statement; `placement-locator = {"kind":"<enum>","value":"<string>"}` where kind is `PARAGRAPH`, `SPAN`, `CAPTION`, or `ANCHOR` and value is nonblank; `source-metadata = {"journal_identifier":"<string|null>","volume":"<string|null>","issue":"<string|null>","pages":"<string|null>","license_label":"<string|null>","public_repository_label":"<string|null>"}`. An absent named form is JSON null where nullable. No extra nested keys are allowed. These shapes are R2 material schemas; changing them later requires a new material version.

### Literature and search

`SourceVersion.content_hash`:
```json
{"type":"SourceVersion","material_version":1,"literature_source_id":"<uuid>","version_kind":"<enum>","predecessor_source_version":"<R(SourceVersion)|null>","correction_basis_artifact":"<R(ArtifactVersion)|null>","title":"<string>","abstract":"<string|null>","authors":[{"name":"<string>","orcid":"<string|null>"}],"publication_date":"<date|null>","venue":"<string|null>","external_version_label":"<string|null>","fulltext_artifact":"<R(ArtifactVersion)|null>","metadata":"<source-metadata|null>"}
```
`authors` preserves published byline order; each author has exactly `name` and `orcid`. `metadata` is null if absent, otherwise exactly the six named keys; no provider objects. CORRECTED/RETRACTED require both predecessor and correction basis.

`LiteratureSearchPlanVersion.content_hash`:
```json
{"type":"LiteratureSearchPlanVersion","material_version":1,"plan_id":"<uuid>","research_question_refs":["<R(ResearchQuestionVersion)>"],"objective":"<string>","source_scope":"<enum>","inclusion_criteria":"<criteria|null>","exclusion_criteria":"<criteria|null>","time_range":"<time-range|null>","language_scope":["<string>"],"search_strategy":"<enum>","planned_providers":["<string>"],"stopping_rule":"<stopping-rule|null>"}
```
`research_question_refs` is a set sorted by `(type,id,content_hash)`; `language_scope` and `planned_providers` are normalized string sets sorted lexically. The named structured values use the closed schemas above; generic JSON is forbidden.

`SearchQueryRecord.query_hash`:
```json
{"type":"SearchQueryRecord","material_version":1,"literature_search_execution_id":"<uuid>","provider_id":"<string>","provider_version":"<string|null>","query_text":"<string>","ordinal":0}
```
`ordinal` above is an integer placeholder, not a required zero. The persisted `query_text` is the normalized query: NFC, replace every Unicode whitespace run with one ASCII space, and trim leading/trailing whitespace; reject empty result. This rule is `phase2-query-normalization-v1` and occurs before storage and hash. There is no separate persisted normalized-query column. `perspective`, raw query, result rank, time, and provider response are excluded. The execution ID binds this retrieval record; this digest is retrieval provenance, never scientific evidence.

`LiteratureEvidence.content_hash`:
```json
{"type":"LiteratureEvidence","material_version":1,"project_id":"<uuid>","source_version":"<R(SourceVersion)>","evidence_type":"<enum>","locator":{"page":"<string|null>","section":"<string|null>","paragraph":"<string|null>","figure":"<string|null>","table":"<string|null>","quote_span":"<string|null>"},"extracted_statement":"<string>","normalized_assertion":"<string|null>","extraction_method":"<enum>","confidence":"<enum>"}
```
At least one locator value is nonnull and meaningful. Review/verification status and extraction execution reference are excluded.

`SourceMergeRecord.content_hash`:
```json
{"type":"SourceMergeRecord","material_version":1,"losing_source":"<I(LiteratureSource)>","winning_source":"<I(LiteratureSource)>","reason":"<string>","identity_basis_artifact":"<R(ArtifactVersion)>","merged_by":"<I(ActorIdentity)>"}
```

`SearchCoverage.content_hash`:
```json
{"type":"SearchCoverage","material_version":1,"search_plan_version":"<R(LiteratureSearchPlanVersion)>","search_execution":["<I(LiteratureSearchExecution)>"],"providers":["<string>"],"query_count":0,"result_count":0,"resolved_source_count":0,"time_scope":"<time-range|null>","coverage_limitations":"<string>"}
```
Counts are nonnegative integers. Execution IDs and provider names are duplicate-free sets sorted by UUID and lexical order, respectively; the integers shown as zero are typed placeholders. `time_scope` has the same closed schema as the plan time range.

`PriorArtRelation.content_hash`:
```json
{"type":"PriorArtRelation","material_version":1,"claim_version":"<R(ClaimVersion)>","source_version":"<R(SourceVersion)>","relation":"<enum>","rationale":"<string>","literature_evidence":["<R(LiteratureEvidence)>"],"assessed_by":"<I(ActorIdentity)>"}
```
Evidence refs are a duplicate-free set sorted by UUID; each evidence must resolve to the stated source version.

`NoveltyAssessment.content_hash`:
```json
{"type":"NoveltyAssessment","material_version":1,"claim_version":"<R(ClaimVersion)>","search_coverage":"<R(SearchCoverage)>","assessment":"<enum>","limitations":"<string>","supersedes_assessment":"<R(NoveltyAssessment)|null>","assessed_by":"<I(ActorIdentity)>"}
```

### Scientific synthesis and manuscript

`LiteratureSupportSnapshot.literature_support_set_hash` is the separate Phase 2 support binding. It holds literature support for one exact frozen Phase 1 ClaimVersion, ResearchQuestionVersion, or HypothesisVersion without adding literature rows to the Phase 1 target support hash or changing Phase 1 canonical-json/hash semantics:
```json
{"type":"LiteratureSupportSnapshotSupportSet","material_version":1,"literature_inputs":[{"literature_evidence":"<R(LiteratureEvidence)>","relation_type":"<enum>","ordinal":0,"qualification":"<string|null>"}]}
```
Rows sort `(ordinal,literature_evidence.id)`; ordinal is a nonnegative integer unique within the snapshot and the same `(evidence,relation_type)` cannot repeat. An explicit empty snapshot uses `[]`; absence of a snapshot means no support assertion. The snapshot has exactly one concrete frozen scientific target FK and concrete literature-input relation rows; it is not an alternative Phase 1 version or EvidenceRelation. Relation types are SUPPORTS, CONTRADICTS, QUALIFIES, MOTIVATES, PRIOR_ART, CONTEXTUALIZES.

`LiteratureSupportSnapshot.content_hash`:
```json
{"type":"LiteratureSupportSnapshot","material_version":1,"project_id":"<uuid>","target":"<R(ClaimVersion|ResearchQuestionVersion|HypothesisVersion)>","snapshot_number":0,"previous_snapshot":"<R(LiteratureSupportSnapshot)|null>","literature_support_set_hash":"<digest>"}
```
`snapshot_number` is a positive integer and is material because it establishes the immutable sequence; predecessor is null exactly for number 1, otherwise points to the immediately prior snapshot of the same project and target. This snapshot is immutable after creation, requires frozen valid Phase 1 target closure and verified source-backed literature evidence for positive support, and is succeeded by a new snapshot if its support changes. Its own ID and timestamps are excluded.

`ScientificConclusionVersion.support_set_hash`:
```json
{"type":"ScientificConclusionVersionSupportSet","material_version":1,"claim_inputs":[{"claim_version":"<R(ClaimVersion)>","literature_support_snapshot":"<R(LiteratureSupportSnapshot)|null>","relation_type":"<enum>","ordinal":0}],"literature_inputs":[{"literature_evidence":"<R(LiteratureEvidence)>","relation_type":"<enum>","ordinal":0}]}
```
The optional snapshot is tied to its exact `claim_version`; null means no Phase 2 literature attachment for that claim input. Direct conclusion literature inputs remain separate, even if they cite the same evidence as a claim snapshot. Both arrays reject duplicate target/relation rows, have zero-based contiguous ordinals unique within their own kind, and sort `(ordinal,target.id)` within each kind; kind order is claim then literature. No relation-row IDs. Freeze requires at least one input across the arrays.

`ScientificConclusionVersion.content_hash`:
```json
{"type":"ScientificConclusionVersion","material_version":1,"scientific_conclusion_id":"<uuid>","statement":"<string>","scope":{"population":"<string|null>","conditions":"<string|null>","time_window":"<string|null>","applicability":"<string|null>"},"confidence":"<enum>","limitation_summary":"<string|null>","support_set_hash":"<digest>"}
```
The scope object always has exactly these four keys.

`ManuscriptVersion.placement_set_hash`:
```json
{"type":"ManuscriptVersionPlacementSet","material_version":1,"claim_placements":[{"target":"<R(ClaimVersion|ScientificConclusionVersion)>","section_id":"<string>","locator":"<placement-locator>","rhetorical_strength":"<enum>","ordinal":0}],"citation_placements":[{"source_version":"<R(SourceVersion)>","section_id":"<string>","locator":"<placement-locator>","citation_purpose":"<enum>","ordinal":0}],"artifact_placements":[{"artifact_version":"<R(ArtifactVersion)>","section_id":"<string>","locator":"<placement-locator>","artifact_role":"<enum>","ordinal":0}]}
```
Each array sorts `(section_id,ordinal)`, and `(kind,section_id,ordinal)` is unique across the full binding. The placement locator uses the closed schema above. Citation placement alone asserts no scientific support.

`ManuscriptVersion.content_hash`:
```json
{"type":"ManuscriptVersion","material_version":1,"publication_id":"<uuid>","document_artifact":"<R(ArtifactVersion)>","title":"<string>","abstract":"<string|null>","semantic_change_class":"<enum>","placement_set_hash":"<digest>"}
```

### Review, decision, approval, and revision

`InternalReviewRecord.content_hash`:
```json
{"type":"InternalReviewRecord","material_version":1,"project_id":"<uuid>","target":"<R(ManuscriptVersion|ClaimVersion|ScientificConclusionVersion|ArtifactVersion)>","reviewer_actor_id":"<uuid>","review_type":"<enum>","recommendation":"<enum>","summary":"<string>"}
```
`target` is the one concrete frozen target chosen by the XOR columns. For ArtifactVersion it is the ResearchBrief artifact FK. The separately stored `target_content_hash` must equal `target.content_hash`.

`DecisionRecord.basis_set_hash`:
```json
{"type":"DecisionRecordBasisSet","material_version":1,"basis":[{"target":"<R(ClaimVersion|ScientificConclusionVersion|ManuscriptVersion|InternalReviewRecord|ApprovalDecision|RevisionAction)>","ordinal":0}]}
```
Basis rows are duplicate-free by target, sorted `(target.type,target.id,target.content_hash)`; their persisted ordinal is included but does not control array order. A decision requires the basis set specified by its decision type; `ApprovalDecision` is the exact prior rejection basis and `RevisionAction` the exact completed-change basis for reconsideration. No generic target JSON.

`DecisionRecord.content_hash`:
```json
{"type":"DecisionRecord","material_version":1,"project_id":"<uuid>","decision_type":"<enum>","question":"<string>","decision":"<enum>","rationale":"<string>","decided_by":"<I(ActorIdentity)>","supersedes_decision_id":"<uuid|null>","basis_set_hash":"<digest>"}
```

`ApprovalDecision.content_hash`:
```json
{"type":"ApprovalDecision","material_version":1,"approval_request_id":"<uuid>","target":"<R(ManuscriptVersion|ScientificConclusionVersion)>","decision":"<enum>","valid_until":"<instant|null>","requires_current_author_consent":false,"rationale":"<string>","decided_by":"<I(ActorIdentity)>"}
```
The boolean shown as false is a boolean placeholder. `target` resolves from the immutable request's XOR target and verified target hash. No free-text executable conditions are admitted.

`RevisionAction.content_hash`:
```json
{"type":"RevisionAction","material_version":1,"review_issue":"<I(ReviewIssue)|null>","decision":"<R(DecisionRecord)|null>","action_type":"<enum>","results":{"result_experiment_spec_version":"<R(ExperimentSpecVersion)|null>","result_run":"<I(Run)|null>","result_statistical_result":"<R(StatisticalResult)|null>","result_claim_version":"<R(ClaimVersion)|null>","result_scientific_conclusion_version":"<R(ScientificConclusionVersion)|null>","result_manuscript_version":"<R(ManuscriptVersion)|null>","result_source_version":"<R(SourceVersion)|null>"},"supersedes_revision_action":"<R(RevisionAction)|null>","created_by":"<I(ActorIdentity)>"}
```
At least one of issue or decision is nonnull. The `results` object always has exactly these seven keys, projected from the seven concrete `result_*_id` FK columns in Governance R2 §4. `NEW_EXPERIMENT` requires **both** ExperimentSpecVersion and Run and all others null; `ANALYSIS_CHANGE`, `CLAIM_CHANGE`, `CONCLUSION_CHANGE`, `MANUSCRIPT_CHANGE`, and `SOURCE_CHANGE` each require only their corresponding one ref; `NO_CHANGE` requires all null. These are the complete seven action shapes. Phase 1 Run has no own content hash, so `I(Run)` binds its exact UUID and a typed FK/closure guard requires that its inputs are sealed, status terminal, and its ExperimentSpecVersion equals the paired ref. StatisticalResult and the listed versions use their existing exact content hashes. There is no polymorphic soft reference.

### Authorship and prepared package

`ContributionRecord.content_hash`:
```json
{"type":"ContributionRecord","material_version":1,"publication":"<I(Publication)>","actor":"<I(ActorIdentity)>","contribution_role":"<enum>","contribution_statement":"<string>","recorded_by":"<I(ActorIdentity)>"}
```

`AuthorshipSnapshot.content_hash`:
```json
{"type":"AuthorshipSnapshot","material_version":1,"publication_id":"<uuid>","authors":[{"actor":"<I(ActorIdentity)>","ordinal":1}],"corresponding_authors":["<I(ActorIdentity)>"],"equal_contribution_groups":[["<I(ActorIdentity)>","<I(ActorIdentity)>"]],"contribution_records":[{"contribution_record":"<R(ContributionRecord)>","ordinal":0}]}
```
`authors` is the **authored order**, strictly ordinal 1..N with each actor once; the author ordinal is meaningful and hashed. `corresponding_authors` is a duplicate-free subset of authors sorted by actor UUID, regardless of persisted relation ordinal. Each equal-contribution group has at least two distinct author actors, sorts members by actor UUID, and groups sort lexicographically by their resulting ordered member UUID tuples; duplicate or overlapping groups are rejected. Persisted group ordinals are only storage coordinates and do not affect the hash. `contribution_records` preserves its own zero-based contiguous authored ordinal and hashes that ordinal. This explicitly resolves Schema Field Contract §70's “three author relation tables … in ordinal order”: authored order applies to authors; corresponding and equal-group ordinals are projected into these deterministic set orders. The only canonical storage remains typed relation rows; no actor-ID JSONB collection is stored.

`AuthorConsent.content_hash`:
```json
{"type":"AuthorConsent","material_version":1,"prepared_submission":"<I(PreparedSubmissionVersion)>","actor":"<I(ActorIdentity)>","consent_state":"<enum>","consent_scope":"<enum>","evidence_artifact":"<R(ArtifactVersion)|null>","prior_consent":"<R(AuthorConsent)|null>"}
```
The package is an ID-only ref because it is PREPARED at capture, avoiding a content-hash cycle. Withdrawal is a new record. Capture time is excluded.

`PreparedSubmissionVersion.package_manifest_hash`:
```json
{"type":"PreparedSubmissionVersionManifest","material_version":1,"manuscript_version":"<R(ManuscriptVersion)>","authorship_snapshot":"<R(AuthorshipSnapshot)>","items":[{"category":"<enum>","ordinal":0,"target":"<R(ArtifactVersion|SourceVersion|ClaimVersion|ScientificConclusionVersion|AuthorConsent)>"}]}
```
Categories are `FIGURE`, `TABLE`, `CITATION`, `CLAIM`, `CONCLUSION`, `AUTHOR_CONSENT`. Allowed target type respectively is ArtifactVersion, ArtifactVersion, SourceVersion, ClaimVersion, ScientificConclusionVersion, AuthorConsent. Rows sort `(category,ordinal)` using category enum text lexical order; the pair is unique. Consent rows are the exact current GRANTED consent for every author at freeze. The manuscript and authorship refs occur only in the two top-level fields, never as duplicate items.

`PreparedSubmissionVersion.content_hash`:
```json
{"type":"PreparedSubmissionVersion","material_version":1,"publication_id":"<uuid>","manuscript_version":"<R(ManuscriptVersion)>","authorship_snapshot":"<R(AuthorshipSnapshot)>","package_manifest_hash":"<digest>"}
```

### Bootstrap audit

`BootstrapRecord.content_hash`:
```json
{"type":"BootstrapRecord","material_version":1,"deployment_id":"<string>","request_id":"<uuid>","operator_credential_id":"<string>","secret_digest_id":"<string>","first_actor_id":"<uuid>","first_binding_id":"<uuid>","first_project_id":"<uuid>","first_membership_id":"<uuid>","first_role_assignment_id":"<uuid>"}
```
The secret itself and request fingerprint are excluded; the five identity UUID fields are the exact transaction-created identities.

## Hash lifecycle and compatibility

For version rows with DRAFT or PREPARED state, their own hash and each applicable binding hash **must be SQL NULL** until successful freeze; placeholder digest strings and precomputed persisted draft hashes are forbidden. A never-frozen `ABANDONED` SourceVersion, LiteratureSearchPlanVersion, ScientificConclusionVersion, or ManuscriptVersion retains null own/binding hashes and null `frozen_at`. A never-frozen `WITHDRAWN` PreparedSubmissionVersion likewise retains null own/manifest hashes and null `frozen_at`. Frozen rows require every applicable digest and `frozen_at` nonnull. After FROZEN, later SUPERSEDED or WITHDRAWN retains those exact nonnull hashes and frozen timestamp; lifecycle events/validity change, material never does. Immutable records and snapshots get their own hash at insertion; relation bindings are computed in that transaction. These rules resolve the R1 nullable-hash ambiguity and require the owning schema checks/triggers when implementation is separately authorized.

A support snapshot is the Phase 2 addition approved by ADR-0009 and specified in R2 design closure §2. It is created frozen in one transaction, so both hashes are required at insertion; there is no draft/abandoned snapshot lifecycle. No Phase 1 ClaimVersion, EvidenceRelation, canonical serializer, or frozen hash is rewritten. Conclusion claim-input binding adds an optional exact snapshot ref while the direct literature-input path remains independent. Any implementation must version the Phase 2 conclusion support material coherently so old support digests remain verifiable; frozen R1-shaped payloads cannot be silently reinterpreted as this R2 shape.

## Golden vectors

The following vectors use canonical JSON with sorted object keys, compact separators, UTF-8, and `ensure_ascii=false`; each exact compact string is the preimage. All zero UUIDs and repeated hexadecimal digits are deliberate synthetic fixtures. Hashes are SHA-256 of the shown UTF-8 bytes. A conforming implementation must match the bytes and digest, then independently verify reference closure in its integration tests. Vectors are design examples, not runtime test authorization.


`SourceVersion.content_hash` — `dc89646783c513cbe656a285836705bc8986e871715a837597309024eda2b8ca`

```json
{"abstract":null,"authors":[{"name":"Ana Lee","orcid":null}],"correction_basis_artifact":null,"external_version_label":null,"fulltext_artifact":null,"literature_source_id":"00000000-0000-0000-0000-000000000001","material_version":1,"metadata":null,"predecessor_source_version":null,"publication_date":"2024-01-02","title":"Café study","type":"SourceVersion","venue":null,"version_kind":"PUBLISHED"}
```

`ScientificConclusionVersion.support_set_hash` — `24b43b7434ebcc6e8ba349d4f9313277c4eefd3832adeaca16882365d94f7953`

```json
{"claim_inputs":[{"claim_version":{"content_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","id":"00000000-0000-0000-0000-000000000002","type":"ClaimVersion"},"literature_support_snapshot":null,"ordinal":0,"relation_type":"SUPPORTS"}],"literature_inputs":[],"material_version":1,"type":"ScientificConclusionVersionSupportSet"}
```

`ScientificConclusionVersion.content_hash` — `eba7398741d3591ca30451a64536ffbb6d8b6039d9a459453e9af34f9e5f631f`

```json
{"confidence":"MODERATE","limitation_summary":null,"material_version":1,"scientific_conclusion_id":"00000000-0000-0000-0000-000000000003","scope":{"applicability":null,"conditions":null,"population":"Adults","time_window":null},"statement":"Evidence supports the effect.","support_set_hash":"24b43b7434ebcc6e8ba349d4f9313277c4eefd3832adeaca16882365d94f7953","type":"ScientificConclusionVersion"}
```

`AuthorshipSnapshot.content_hash` — `3cb9fe56ea44ba2ab98c838e01946321e2302fe7f2eeff7473303d4988cc60a6`

```json
{"authors":[{"actor":{"id":"00000000-0000-0000-0000-000000000005","type":"ActorIdentity"},"ordinal":1},{"actor":{"id":"00000000-0000-0000-0000-000000000006","type":"ActorIdentity"},"ordinal":2}],"contribution_records":[{"contribution_record":{"content_hash":"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee","id":"00000000-0000-0000-0000-000000000017","type":"ContributionRecord"},"ordinal":0},{"contribution_record":{"content_hash":"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff","id":"00000000-0000-0000-0000-000000000018","type":"ContributionRecord"},"ordinal":1}],"corresponding_authors":[{"id":"00000000-0000-0000-0000-000000000006","type":"ActorIdentity"}],"equal_contribution_groups":[[{"id":"00000000-0000-0000-0000-000000000005","type":"ActorIdentity"},{"id":"00000000-0000-0000-0000-000000000006","type":"ActorIdentity"}]],"material_version":1,"publication_id":"00000000-0000-0000-0000-000000000004","type":"AuthorshipSnapshot"}
```

`PreparedSubmissionVersion.package_manifest_hash` — `1378737bf5d07edff580a8b5e13f53e9f516df69738ec81688c2fff838d40d46`

```json
{"authorship_snapshot":{"content_hash":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","id":"00000000-0000-0000-0000-000000000008","type":"AuthorshipSnapshot"},"items":[{"category":"AUTHOR_CONSENT","ordinal":0,"target":{"content_hash":"dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd","id":"00000000-0000-0000-0000-000000000009","type":"AuthorConsent"}}],"manuscript_version":{"content_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","id":"00000000-0000-0000-0000-000000000007","type":"ManuscriptVersion"},"material_version":1,"type":"PreparedSubmissionVersionManifest"}
```

`PreparedSubmissionVersion.content_hash` — `2ffff00e6620ddc0cf68c62fd54e18d8f1eb2099a640828d7f027101e5b2d32d`

```json
{"authorship_snapshot":{"content_hash":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","id":"00000000-0000-0000-0000-000000000008","type":"AuthorshipSnapshot"},"manuscript_version":{"content_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","id":"00000000-0000-0000-0000-000000000007","type":"ManuscriptVersion"},"material_version":1,"package_manifest_hash":"1378737bf5d07edff580a8b5e13f53e9f516df69738ec81688c2fff838d40d46","publication_id":"00000000-0000-0000-0000-000000000004","type":"PreparedSubmissionVersion"}
```

`InternalReviewRecord.content_hash` — `f974d3fad6625fe231671f5f485cc7a6ef8dc7926beba71259813fb75d3de704`

```json
{"material_version":1,"project_id":"00000000-0000-0000-0000-000000000010","recommendation":"ACCEPT","review_type":"SCIENTIFIC","reviewer_actor_id":"00000000-0000-0000-0000-000000000011","summary":"Ready.","target":{"content_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","id":"00000000-0000-0000-0000-000000000007","type":"ManuscriptVersion"},"type":"InternalReviewRecord"}
```

`DecisionRecord.basis_set_hash` — `0c9c9d2a5d207ec7c425192e42e1023c66075ae52eb2da5e26b56360bc8e3af5`

```json
{"basis":[{"ordinal":0,"target":{"content_hash":"eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee","id":"00000000-0000-0000-0000-000000000012","type":"InternalReviewRecord"}}],"material_version":1,"type":"DecisionRecordBasisSet"}
```

`DecisionRecord.content_hash` — `aa4f886f7b59baab737d7990700057fe7c2ac3751c9b546fd6f40bbab2c21cf3`

```json
{"basis_set_hash":"0c9c9d2a5d207ec7c425192e42e1023c66075ae52eb2da5e26b56360bc8e3af5","decided_by":{"id":"00000000-0000-0000-0000-000000000013","type":"ActorIdentity"},"decision":"PROCEED","decision_type":"PUBLICATION","material_version":1,"project_id":"00000000-0000-0000-0000-000000000010","question":"Proceed?","rationale":"Review complete.","supersedes_decision_id":null,"type":"DecisionRecord"}
```

`ApprovalDecision.content_hash` — `d5de0062b526e4555429d13482cf6521f39bd7ce8b72544b604f66c8fb0229de`

```json
{"approval_request_id":"00000000-0000-0000-0000-000000000014","decided_by":{"id":"00000000-0000-0000-0000-000000000015","type":"ActorIdentity"},"decision":"APPROVE","material_version":1,"rationale":"Gate passed.","requires_current_author_consent":false,"target":{"content_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","id":"00000000-0000-0000-0000-000000000007","type":"ManuscriptVersion"},"type":"ApprovalDecision","valid_until":null}
```

`LiteratureSupportSnapshot.literature_support_set_hash` — `7e961073d06b1a103712b48f1e90ffea11ff30601b209520ec1f20f83a9d8708`

```json
{"literature_inputs":[{"literature_evidence":{"content_hash":"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff","id":"00000000-0000-0000-0000-000000000016","type":"LiteratureEvidence"},"ordinal":0,"qualification":null,"relation_type":"SUPPORTS"}],"material_version":1,"type":"LiteratureSupportSnapshotSupportSet"}
```

`LiteratureSupportSnapshot.content_hash` — `f97558953b8d05604d1ca48f65af6791d8b5860af2e0b6bcb2dfd511eb0895e6`

```json
{"literature_support_set_hash":"7e961073d06b1a103712b48f1e90ffea11ff30601b209520ec1f20f83a9d8708","material_version":1,"previous_snapshot":null,"project_id":"00000000-0000-0000-0000-000000000010","snapshot_number":1,"target":{"content_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","id":"00000000-0000-0000-0000-000000000002","type":"ClaimVersion"},"type":"LiteratureSupportSnapshot"}
```
