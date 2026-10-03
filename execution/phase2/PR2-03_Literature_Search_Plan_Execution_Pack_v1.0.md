# PR2-03 — LiteratureSearchPlan execution pack v1.0

**Status:** frozen design subject for one independent design review; implementation is not authorized until the review returns `NEW_P0_GAPS=0`, `NEW_P1_GAPS=0`, `READY_FOR_PR2_03_IMPLEMENTATION=YES`, and no unresolved P2 policy question.
**Starting accepted lineage:** PR2-00, PR2-01, SOURCE_MERGE_GOVERNANCE_BRIDGE, and PR2-02 accepted; starting HEAD `a8fd1fef2475b12c50e6f18a4aaa6d9b0e663d02`; migration head `0022_source_version_and_merge_lineage`; frozen Phase 1 semantic baseline `d2400fbeca835c89bd802a4e9d647bda01cfd115`.
**Migration parent:** `0022_source_version_and_merge_lineage`.
**Migration revision:** `0023_literature_search_plan`.

## 1. Authority and precedence

1. Frozen Phase 1 semantics and system architecture.
2. Final Architecture Correction Addendum and later accepted A18–A22 corrections.
3. Global Schema and Contract Registry and Cross-Phase Contracts.
4. Phase 2 correction and contracts 12–19, including the exact hash contract in 15 and ownership rules in 16.
5. Phase 2 Development Specification 05 for uncorrected PR boundaries and commands.
6. This pack for bounded implementation detail.
7. Human decision in the PR2-03 clarification: a draft may have zero ResearchQuestion refs; freeze requires at least one valid ResearchQuestion ref.

The cardinality rule is explicit and authoritative:

```text
DRAFT: research_question_refs >= 0
FREEZE: effective research_question_refs >= 1
```

No Phase 1 entity, hash, lifecycle, migration, or frozen baseline behavior is changed.

## 2. Purpose, dependencies, and boundary

PR2-03 provides project-scoped authoring and freezing of versioned `LiteratureSearchPlan` intent. A frozen version records its exact scientific question basis, objective, source scope, inclusion/exclusion criteria, time range, language set, search strategy, planned provider set, and stopping rule. It does not retrieve literature or assert evidence.

Dependencies are accepted PR2-00 membership, verified principal and TEMP-AUTH-01; PR2-01 source/project identity rules; accepted merge governance bridge; PR2-02 SourceVersion/source lineage; Phase 1 ResearchQuestionVersion frozen identity/hash and Phase 1 project ownership; canonical-json-v1 and sha256-cjson-v1.

### In scope

- `LiteratureSearchPlan` identity and project ownership.
- `LiteratureSearchPlanVersion` creation, DRAFT editing, exact ResearchQuestionVersion relation management, freeze, supersession, and abandonment.
- Search-plan own-content hash under contract 15, with deterministic golden vectors.
- Minimal project-scoped Application commands and queries, HTTP and CLI parity, typed DTOs and errors.
- Migration 0023 for plan/version/question-input/typed receipt persistence, FK/unique/check/index constraints and freeze/edit guards.
- Durable exact replay, changed-request conflict, rollback, scope authorization, and PostgreSQL concurrency evidence.

### Out of scope

- Any provider/API/network call, external search execution, query/result records, retries or provider credentials. Those belong to PR2-04 (`LiteratureSearchExecution` and query/result provenance).
- SearchCoverage execution linkage; it consumes PR2-04 execution records.
- LiteratureSource or SourceVersion changes; source identity, merge and lineage remain accepted PR2-01/02 state.
- LiteratureEvidence extraction/review/support, citations, prior-art or novelty assessment, RAG, STORM, discussion, conclusions, publication, governance, agent runtime, or generic schema/workflow frameworks.
- Any top-level canonical schema beyond the specified plan identity and version pair. Request receipts are operational idempotency records only.

## 3. Domain model and persistence

Use the schema names and semantic columns in contracts 12, 13 and 15:

- `literature_search_plans`: `id`, `project_id`, nullable `current_version_id`, shared creation/audit columns.
- `literature_search_plan_versions`: `id`, `plan_id`, positive `version_number`, `status`, the contract-13 fields `objective`, `source_scope`, nullable inclusion/exclusion criteria, nullable time range, nullable language scope, `search_strategy`, planned providers, nullable stopping rule, nullable content hash, nullable frozen time, and shared creation/audit columns.
- `search_plan_question_inputs`: exact `research_question_version_id` and ordinal under a plan version. Store refs as typed relational FKs; no JSON reference list or polymorphic target.
- `literature_search_plan_command_receipts`: operational immutable receipts for plan create/revise/draft-edit/question-add/question-remove/freeze/abandon commands. Columns: UUID `id`, `deployment_id`, `actor_id`, `project_id`, `command_name`, `request_id`, `request_hash CHAR(64)`, `hash_scheme`, result plan ID, nullable result plan-version ID as appropriate, `result_dto_version`, public `result_dto JSONB`, and `completed_at`. Scope uniqueness is exactly `(deployment_id, actor_id, project_id, command_name, request_id)`; all FKs RESTRICT; hash scheme is `sha256-cjson-v1`; result DTO is a replay projection only. Insert complete in the command transaction; no UPDATE/DELETE. It is not scientific truth or hash input.

All canonical FKs are `ON DELETE RESTRICT`; no scientific cascade. Keep unique `(plan_id,version_number)`, `(plan_id,id)`, same-parent current pointer, FK indexes, project/status indexes, and relation parent/target indexes. A database guard and Application check require `current_version_id` to name a FROZEN version belonging to that plan. Content/hash columns are NULL before successful freeze. Frozen material and inputs cannot be updated/deleted; a FROZEN version may only undergo the contract lifecycle transition to SUPERSEDED, preserving its material/hash/frozen time.

Each question input must point to a ResearchQuestionVersion with status FROZEN or SUPERSEDED and its exact stored content hash must verify against the Phase 1 hash contract. DRAFT and ABANDONED versions are invalid refs. A superseded exact frozen version remains historically valid; supersession alone does not invalidate the ref. There is no extra active/current ResearchQuestion lifecycle requirement because Phase 1 defines ResearchQuestion as a stable identity and frozen references bind versions. Do not add a plan-version lifecycle event table: contracts 12/13 represent these transitions with the version status/current pointer and immutable request receipt; a freeze has no separate canonical event.

Project scope is same-project. Resolve each version through its ResearchQuestion parent and require `ResearchQuestion.project_id == LiteratureSearchPlan.project_id`. Enforce this in the Application and with composite typed FK/trigger constraints where the existing schema has no direct project key on ResearchQuestionVersion. Do not permit public-source-style cross-project sharing for questions; no such sharing contract exists.

Question refs are semantically a set of ResearchQuestion identities, each bound to one exact version. A question identity may appear at most once in one plan version, even if a caller supplies two versions of it. Reject duplicates deterministically before persistence/hash. Preserve contract 13's relation columns (`plan_version_id`, `research_question_version_id`, `ordinal`): enforce exact-version and ordinal uniqueness with UNIQUE constraints and enforce identity-level uniqueness using a constraint trigger that joins the referenced ResearchQuestionVersion to its ResearchQuestion parent. This avoids adding a redundant reference field. Ordinal is storage-only and must be canonicalized from the deterministic set order on replacement/freeze; it has no semantic effect.

## 4. Lifecycle and cardinality

Use only registered version states: `DRAFT → FROZEN → SUPERSEDED`, with `DRAFT → ABANDONED`. No new state is introduced. The plan identity is stable; each successful freeze points `current_version_id` to the new frozen version and changes any prior current FROZEN version to SUPERSEDED in the same transaction. Superseded versions retain exact material, refs, hash, and `frozen_at`. Abandoning a draft leaves the current pointer unchanged.

| Operation | Source state | Target/result | Required validation and writes |
|---|---|---|---|
| Create plan | none | identity + version 1 DRAFT | Active project, OWNER/RESEARCHER write authority, valid fields; question refs may be empty. Insert identity, DRAFT version, optional valid refs and receipt atomically. |
| Revise plan | current version exists | next numbered DRAFT version | Lock plan; require current version and same project write authority; copy current frozen material/refs as initial draft when current is FROZEN/SUPERSEDED, or reject a second parallel draft; allocate next number under identity lock. No prior frozen row changes. |
| Edit draft fields / replace question refs | DRAFT | same DRAFT | Only declared version fields/refs; validate typed input and same-project/frozen question refs at write; zero refs allowed. Ref mutation and plan freeze share lock order. |
| Freeze | DRAFT | FROZEN | At final locked durable reread require at least one effective distinct ResearchQuestion identity and validate every exact ref, project scope, frozen hash and closure. Compute canonical hash; atomically freeze version, update pointer, supersede prior current version, and save receipt. No separate freeze/lifecycle event is created under the existing contract. |
| Abandon | DRAFT | ABANDONED | Owner/researcher and row-version/state check; preserve NULL hashes/frozen time; pointer unchanged. |
| Mutate inputs/material | FROZEN or SUPERSEDED | denied | Deterministic `VERSION_IMMUTABLE`/existing semantically exact error; no writes. |

An empty draft is valid, but an empty freeze is not. On an empty-freeze failure the version remains DRAFT, `frozen_at` and `content_hash` remain NULL, no freeze/lifecycle event or receipt is committed, and the plan current pointer is unchanged. A request receipt is written only for successful commands; failures roll back all command effects.

## 5. Freeze reference validity and atomicity

At final freeze validation, reread the durable relation rows after obtaining the plan/version locks; never validate only a caller or ORM in-memory collection. Require `count(distinct research_question_id) >= 1`. For every ref require: target version exists; belongs to its ResearchQuestion identity; identity belongs to the plan project; version is FROZEN or SUPERSEDED with non-null `frozen_at`; exact Phase 1 hash is present and verifies; relation is unique by ResearchQuestion identity. Missing, deleted, malformed, DRAFT, ABANDONED, cross-project, or hash-invalid refs fail closed with typed Application errors; no soft-reference fallback.

Failure mapping uses an existing semantically exact code when one exists; otherwise define only narrow PR2-03 errors: `SEARCH_PLAN_QUESTION_REQUIRED` (422 for freeze cardinality), `SEARCH_PLAN_QUESTION_INVALID` (422), `SEARCH_PLAN_QUESTION_SCOPE_MISMATCH` (403 or non-disclosing 404 per project query policy), and `SEARCH_PLAN_VERSION_IMMUTABLE` (409). Authentication, forbidden, not-found, concurrent-modification, validation, and idempotency errors retain established mappings. No error path partially freezes or discloses a foreign project's question.

## 6. Hash and canonicalization contract

Implement contract 15 literally. The complete payload is:

```json
{"type":"LiteratureSearchPlanVersion","material_version":1,"plan_id":"<lowercase-uuid>","research_question_refs":[<R(ResearchQuestionVersion)>],"objective":"<NFC string>","source_scope":"<enum>","inclusion_criteria":<criteria|null>,"exclusion_criteria":<criteria|null>,"time_range":<time-range|null>,"language_scope":["<normalized string>"],"search_strategy":"<enum>","planned_providers":["<normalized string>"],"stopping_rule":<stopping-rule|null>}
```

The displayed whitespace is explanatory; serialize with existing `canonical-json-v1` exactly. Keys are only those shown. Hash `SHA-256(canonical-json-v1(payload).UTF8)`, lowercase hex, scheme `sha256-cjson-v1`. UUIDs are lowercase canonical text, strings NFC at material creation, enums uppercase persisted literals, absent optionals are explicit JSON `null`. Validate the closed structured schemas in contract 15 before serialization; no implicit ORM fields or generic JSON enter the payload.

`research_question_refs` is a set of `R(ResearchQuestionVersion)` objects sorted by `(type,id,content_hash)`; reject duplicate ResearchQuestion identities before serialization. `language_scope` and `planned_providers` are normalized string sets: NFC, duplicate-free and lexically sorted. Criteria/time-range/stopping-rule use the exact named closed forms in contract 15. `source_scope` and `search_strategy` use the exact enum values in contracts 05/13. Row ID for the plan version, version number, timestamps, actor, status, ordinal, current pointer, receipt, hash fields, and provider/cache metadata are excluded. No provider call occurs during freeze. Include golden vectors for empty-list DRAFT hash absence, one ref and multiple refs, reordered input refs/providers/languages yielding the same digest, duplicate rejection, null-vs-empty semantics, and a meaningful material-field change yielding a different digest.

## 7. Application, authorization, idempotency, and adapters

Every write is one synchronous Application/UoW transaction. Domain code has no ORM, SQLAlchemy Session, FastAPI, Typer, provider, or network dependency. ORM objects never cross Application/API boundaries. Human and Agent use the same typed Application command boundary.

Commands: `create_literature_search_plan`, `revise_literature_search_plan`, `update_literature_search_plan_draft`, `add_literature_search_plan_question`, `remove_literature_search_plan_question`, `freeze_literature_search_plan`, and `abandon_literature_search_plan`. Updating draft material replaces the complete material tuple; it is not a partial patch. Add/remove changes one exact question binding by ResearchQuestion identity. Queries: project-scoped get/list plan and version, including draft refs and frozen hash. HTTP and CLI expose parity for these operations; writes require UUID request IDs (`Idempotency-Key` / `--request-id`) and supplied project scope. No provider execution route is added.

Writes require authenticated, live verified HUMAN or AGENT principal, active project membership, and effective OWNER/RESEARCHER role in that project. Reads require active membership and a project role permitted by the established Phase 2 read policy. Same project scope and the existing source/project rules are checked before result disclosure. Any expiry-sensitive role/credential check follows TEMP-AUTH-01: acquire all required locks, reread durable state, fetch fresh PostgreSQL `clock_timestamp()`, then authorize immediately before the effect/disclosure; after any subsequent blocking wait repeat the check. Never use transaction-start `now()` as final authorization time.

Canonical command key is exactly `(deployment_id, actor_id, project_id, command_name, request_id)`. The key selects a receipt; it is not part of the request hash. Hash the closed, normalized command payload with `sha256-cjson-v1`. Same key + same hash returns the complete saved result under current authenticated project access and does not repeat the effect. Same key + different hash returns `IDEMPOTENCY_CONFLICT`; no write or receipt replacement. Same actor/deployment/request ID in another project or under another command name is a distinct key. Concurrent same-key commands yield one effect and exact replay/conflict. Rollback leaves no receipt. Preserve the accepted command semantics for each operation; a new request ID after freeze does not make mutation of frozen material permissible.

Request-hash payloads are closed and contain only these keys (all UUIDs lowercase canonical strings; nullable fields always present; request ID, actor, deployment, transport headers, result DTO, generated IDs and timestamps excluded because scope/audit or server result owns them): create `{project_id, objective, source_scope, inclusion_criteria, exclusion_criteria, time_range, language_scope, search_strategy, planned_providers, stopping_rule, research_question_version_ids}`; revise `{project_id, plan_id, base_version_id}`; update `{project_id, plan_id, version_id, objective, source_scope, inclusion_criteria, exclusion_criteria, time_range, language_scope, search_strategy, planned_providers, stopping_rule}`; add-question `{project_id, plan_id, version_id, research_question_version_id}`; remove-question `{project_id, plan_id, version_id, research_question_id}`; freeze and abandon `{project_id, plan_id, version_id}`. The create question ID set is duplicate-checked by question identity then sorted by `(ResearchQuestion identity UUID, ResearchQuestionVersion UUID)` before hashing; update has no refs because relation edits use add/remove. Structured values use contract-15 closed forms; string sets are NFC-normalized, unique and sorted. Hash each normalized object with unchanged `canonical-json-v1` UTF-8 and SHA-256, lowercase hex, `sha256-cjson-v1`.

## 8. Concurrency and deterministic lock order

All operations that can change a plan version or its question-input set, and freeze, serialize on the `literature_search_plans` identity row. Use one deterministic order for create/revise/edit/add/remove/freeze/abandon:

1. Preliminary reads only to identify project, plan/version and referenced question IDs.
2. Lock Project row.
3. Lock the command receipt key.
4. Lock LiteratureSearchPlan row.
5. Lock target LiteratureSearchPlanVersion row(s) in ascending UUID order.
6. Lock affected ResearchQuestion identities and ResearchQuestionVersion rows in ascending UUID order, then lock/reread input relation rows in `(research_question_id, research_question_version_id)` order.
7. Reread all durable state; if discovered scopes differ from locked scopes, abort/retry the whole SERIALIZABLE transaction.
8. Fetch fresh DB clock time and revalidate authority after all required waits; for any later wait, repeat reread/authorization.
9. Validate effective refs and immutable target hashes, then perform the entire edit/freeze/pointer/supersession/event/receipt write atomically.

If question removal commits before freeze obtains the final plan lock/state, freeze observes zero refs and fails. If freeze obtains the lock first and commits, a later removal sees FROZEN/SUPERSEDED and fails. If addition commits first, freeze rereads it and may succeed if all refs validate. No interleaving can commit an empty frozen plan or half-applied transition. PostgreSQL uniqueness/FKs/triggers are backstops, not substitutes for transactional validation.

## 9. Migration and rollback

Migration 0023 is the sole PR2-03 migration and must have parent exactly `0022_source_version_and_merge_lineage`, be the unique head, and add only the tables/constraints/indexes/guards in §3 plus required receipt storage. Do not edit migrations through 0022 or any Phase 1 table/hash/lifecycle. Upgrade tests: fresh database to 0023 and frozen Phase 1 revision 0018 through 0019–0022 to 0023 on PostgreSQL 18. Downgrade succeeds only while all PR2-03 canonical/receipt tables are empty; otherwise it must refuse before destructive DDL with a clear data-preservation error. Test concurrent uniqueness and frozen guards on PostgreSQL, not SQLite.

## 10. Acceptance and evidence

Required cases:

- Empty-question DRAFT creation succeeds.
- Empty-question freeze returns `SEARCH_PLAN_QUESTION_REQUIRED`, leaves DRAFT, NULL hash/time, no event/receipt/pointer change.
- Exactly one and multiple valid same-project frozen question refs freeze successfully.
- Add duplicate exact ref and add a second version of the same ResearchQuestion: deterministic reject; duplicate does not alter semantic identity/hash.
- Missing, DRAFT, ABANDONED, corrupted-hash and cross-project refs are denied at insertion and/or freeze according to the stated validation point.
- FROZEN and SUPERSEDED plan ref/material mutation is denied; valid revision produces a new version and preserves old frozen hash and refs.
- Removal-wins/freeze-loses, freeze-wins/removal-denied, and addition-wins/freeze-rereads races using PostgreSQL barriers and captured lock/final-state evidence.
- Golden hash vectors, insertion-order independence, canonical set ordering, exact null handling, and material-change digest change.
- Exact receipt replay, changed request conflict, request ID reuse across project/command scopes, concurrent same-key execution and rollback for each write command.
- Same-project ownership, active membership/role, non-disclosure, API/CLI parity, architecture import/write-path boundaries.
- Migration fresh install/0018-to-head, unique head, constraints, immutability, empty/populated downgrade behavior.
- Preserve PR2-00 temporal authorization (including no post-expiry challenge success), PR2-01 source identity, SOURCE_MERGE_GOVERNANCE_BRIDGE, PR2-02 SourceVersion/merge lineage, FORMAT-BASELINE-01, and Phase 1 non-drift.

Use the self-contained PostgreSQL 18 reviewer setup recorded in PR2-02 evidence; a pre-existing Docker container, ambient `DATABASE_URL`, or `docker-credential-desktop` is not a prerequisite. Record exact start/pack/implementation SHAs; migration graph and results; every cardinality/reference/lifecycle/idempotency/concurrency/hash case; PostgreSQL setup/version/cleanup; full suite; Ruff; Pyright; raw formatter set and formatter-baseline delta; architecture/regression results; Phase 1 non-drift; known residuals. Evidence is committed as an evidence-only child after implementation SHA exists and does not certify its own SHA. `not run` is never PASS.

## 11. Verification and review gate

Run focused tests first, then all pack-required tests and checks: PostgreSQL 18 migration and constraints; empty draft/freeze, one/many refs, duplicates, invalid/scope refs, immutable mutation and revisions; deterministic race tests; hash vectors; idempotency matrix; architecture and API/CLI parity; all accepted PR regressions and Phase 1 non-drift; full suite; Ruff; Pyright; `ruff format --check .`; formatter baseline delta; `git diff --check`.

After pack commit and clean worktree, exactly one fresh review-only context independently reads authoritative docs, accepted PR evidence, Phase 1 baseline, migration history and this pack. It returns `NEW_P0_GAPS`, `NEW_P1_GAPS`, `NEW_P2_GAPS`, and `READY_FOR_PR2_03_IMPLEMENTATION`. Attack the cardinality decision, exact ref validity/scope, hash canonicalization, frozen immutability, all concurrency interleavings, atomic failure, command replay, migration lineage, provider-execution boundary, and PR2-00/01/GOV/02 plus Phase 1 regression.

Pass: P0=0, P1=0, readiness YES, and no P2 requiring policy judgment. A narrow non-policy pack defect permits one targeted pack remediation and one new fresh reviewer. Remaining P0/P1, any policy-level P2, contradiction, lineage conflict, verification unavailable, dirty subject, Phase 1 drift, or PR2-00 residual reopening is a hard stop. Implementation begins in the main context only after pass. No implementation permission follows from pack authorship or commit alone.

## 12. Next PR boundary

PR2-04 owns `LiteratureSearchExecution`, external-call transaction patterns, query/result provenance and provider metadata. PR2-03 freezes authorized search intent only. No external provider is called by plan creation, revision, editing, query, or freeze. PR2-04 must consume an exact FROZEN plan version and must not mutate it.
