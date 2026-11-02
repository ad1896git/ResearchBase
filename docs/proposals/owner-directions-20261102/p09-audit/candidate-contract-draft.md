PROPOSED / NON-NORMATIVE / NO IMPLEMENTATION AUTHORITY

# P09 minimum no-provider critic candidate — contract draft

Frozen audit checkout: `7540438a4d4c1e58af8872dc8c6c18cb07fdb2f2`. This document is an engineering design output, not a frozen scientific contract or executed critic. Parent P09 HIGH risk, P01 dependency and whole-task definition are unchanged. Only these three new Markdown files are delivered. No source, test, migration, provider, save, execution, promotion or permission change is proposed as already authorized.

Authority read order: AGENTS §1; architecture01 system/layering,02 addendum candidate-to-canonical separation,03 registry,08 compatibility,06 Phase3 §§16–17/PR3-13; ADR-0021; Harness09 §2; delivered PR3-01/02/03/04 and PR3-05 read-only slice. Historical pack headers do not supersede current source or their later evidence. Engineering authorship by a model is not a product CriticAgent run.

## 1. Scope/consumer sufficiency

OBSERVED_SOURCE: `src/researchbase/agent_runtime/application/context_contracts.py:205` supplies a frozen ClaimContext with statement, scope bytes, support-set hash and experiment trace. `:360` supplies a CanonicalContext with exact inputs, one snapshot, current safety/history and warnings. `:261` exposes verified entitled ArtifactContext bytes. These can ground a narrow preview with exact source locators; they do not expose a general ExperimentSpec/Run/Measurement/StatisticalResult DTO family or establish a train/test split or numerical statistical inference contract. A trace to Runs is not permission to invent omitted dataset contents.

PROPOSED: first target family is CLAIM_VERSION only, resolved from the selected task/step's exact entitled context. First checker is a deterministic **synthetic-fixture preview**, not a semantic natural-language or real statistical validator. A pure local fixture declares a bounded expected rule input tied to actual supplied source bytes; declared facts remain SYNTHETIC_FIXTURE, not newly verified canonical metadata. For genuine context without sufficient typed supporting evidence, emit NOT_EVALUABLE limitation rather than infer missing controls/leakage/falsehood. No text heuristic such as presence of “all” certifies an overclaim. Broader target families or real split/result parsing require their own exact contract.

UNVERIFIED: no source implementation of this proposed critic or real invocation is demonstrated. No hidden conversation/scratchpad, model memory or external literature is supporting scientific evidence. Missing required frozen dependencies fails the whole required reconstruction; missing optional rule-specific evidence means visible limitation and cannot silently narrow promised coverage.

## 2. Proposed closed input

PROPOSED in-memory typed values, not public DTO admission or generic JSON semantic core:

- Trusted principal is a separate existing authenticated Application argument; callers supply no trusted actor/approval flags. ContextRequest retains exact project/task/optional step. Reuse current entitlement and nondisclosure before any candidate diagnostics.
- Select exactly one existing CLAIM_VERSION SourceReference already present in CanonicalContext; retain its exact type/id/content_hash/hash_scheme and binding identity. No latest/current alias, free target_type+id formal provenance, or arbitrary path/URL.
- Retain task row_version, snapshot_at, selected bindings, complete owning closure, current validity and warnings separately from immutable historical content. A saved snapshot is not current authority for later writing.
- Supporting material is an ordered tuple of already entitled exact SourceReferences plus already reconstructed immutable values. Proposed explicit synthetic rule leaf variants are OverclaimFixture(asserted_count, supported_count), SplitFixture(train_ids, test_ids), ControlFixture(declared_required, supplied_controls), and ReproducibilityFixture(required_inputs, supplied_inputs, negative_result_disclosed). Each is test-only, with source-bound declaration locator; no open dictionaries, SQL, tools or callbacks. They do not claim today's CanonicalContext contains these scientific leaves.
- PROPOSED preview caps for later review: at most16 supporting refs,8 rule leaves,256 finding rows, 64KiB total candidate UTF8 material, 4096UTF8 bytes per rationale. Each split/input/control list at most256 unique bounded textual labels. These are new candidate limits, not existing gateway or canonical context limits; exceeding them rejects the preview, never truncates the required canonical graph. Error precedence and precise label codec remain pending.

## 3. Proposed closed candidate output

PROPOSED derived in-memory CandidatePreview: exact target reference + ordered supporting references; task revision/snapshot binding; checker revision pin and test-fixture digest; tuple of CandidateFinding; tuple of CoverageLimitation; producer_kind=SYNTHETIC_DETERMINISTIC_FAKE; producer_provenance_verified=false; canonical_acceptance=false; promotion_enabled=false. No new entity UUID, AgentExecution UUID, ArtifactVersion or persistence request is manufactured.

Each CandidateFinding has a local ordinal (scoped only to this preview), proposed rule code, severity category, bounded rationale, tuple of exact evidence locators and suggested action. Locators are `(SourceReference, declared_field_path, start_utf8_byte, end_utf8_byte, excerpt_sha256)` over bytes actually present and verified by the owning reader. Offsets are half-open, within one named raw UTF8 field, on character boundaries, and excerpt hash binds exactly that slice. No locator resolves an arbitrary filesystem path. Field-path vocabulary and empty-slice handling need exact freeze; no reserialization/normalization of scientific bytes to make offsets fit.

Codes OVERCLAIM_CANDIDATE, SPLIT_OVERLAP_CANDIDATE, CONTROL_EVIDENCE_MISSING and REPRODUCIBILITY_EVIDENCE_MISSING, severity/limitation values and this structure are proposals, NOT public ErrorCodes or scientific schema. Absence is reported as “not supplied in this bounded fixture,” never “does not exist.” Output ordering is rule order then exact source/locator/ordinal; duplicate identical input yields identical candidate material once exact encoding/version is frozen. Snapshot timestamp and unrelated observation differences must be declared part of input if allowed to affect bytes. No generated wallclock, random IDs or mutable latest versions in deterministic content.

## 4. Minimal bounded checks

PROPOSED fixture rules (all supplied values synthetic and evidence-bound):

| Rule | Positive candidate trigger | Negative control | Limit |
|---|---|---|---|
| Overclaim | asserted_count exceeds supplied supported_count | equal/below counts produces no such finding | Does not parse or validate real scientific prose/effect sizes |
| Split leakage | exact canonical labels overlap between supplied train/test sets | disjoint sets produce no overlap finding | No claim about unseen data, aliases or other leakage |
| Missing controls | supplied controls omit a declared required control | all declared controls supplied | Declaration is not universal methodological truth |
| Reproducibility/negative results | required input absent or declared negative-result disclosure false | complete supplied input/disclosure | No claim of real reproducibility or complete result history |

Malformed or contradictory metadata is not an adverse scientific verdict: reject invalid fixture or mark unsupported real evidence NOT_EVALUABLE, with exact policy frozen later. Real confounders, statistical weakness, alternative explanations, literature contradiction and robust overclaim inference remain P09 MUST balance; these four toy rules do not satisfy full Phase3 §16.

## 5. Invocation/provenance

OBSERVED_SOURCE: `application/gateway_contracts.py:49` RequestInvocationArguments binds exact policy/capability/adapter/schema/skill/strategy/harness/parameters pins and refs. `domain/tool_policy.py:53` admits existing fake_capability/echo/fake_in_process; `domain/capability_invocation.py:31` parameter schema contains only message/outcome. `application/capability_gateway.py:434` calls finite_fake_echo. Existing gateway is lifecycle/accounting, not an arbitrary critic dispatcher.

Therefore this preview CANNOT be smuggled through echo or a caller-created AgentExecutionContext as if existing gateway already supports it. A later new pure preview port or gateway extension must receive explicit exact-scope/contract/registry/policy/accounting review first; no operation, adapter pin, schema hash, fake policy or registry entry is inserted now. Gateway remains the boundary for any eventually authorized capability invocation. This audit makes no gateway call, reservation, settlement, external effect or Run. S2 CREATED intent is not performed work (`docs/phase3/PR3-02-S2-contract-freeze.md`, §§1–2).

## 6. Acceptance/promotion separation

HISTORICAL_ACCEPTANCE: `docs/phase3/PR3-05-readonly-acceptance.md`, Owner decisions, accepts read-only reconstruction and defers durable save/replay and its lock protocol. OBSERVED_SOURCE: `application/promotion_context.py:21` is validation only; context-derived flags stay non-authorizing. A fake candidate is neither formal ReviewRecord nor Assessment/Decision/Approval and cannot alter Measurement/StatisticalResult/history. Existing typed Application commands and atomic promotion/provenance/producer/fingerprint gates would have to reauthorize and revalidate any future canonical acceptance. No self-approval, reviewer identity or historical scientific correction is inferred from this preview.

## 7. Unresolved details and gates

UNVERIFIED/UNASSIGNED_OWNER_INPUT: exact future code paths/port and import admissibility; final target choice and supporting scientific parser/schemas; exact fixture leaf type/codec/limits; severity/error precedence; exact locator field vocabulary and UTF8 byte rules; candidate digest grammar; fake marker/coverage semantics; no-persistence output policy; independently accepted sufficiency and gateway integration choice. These require exact review before source work, not silent architecture freeze here. No provider, credential, host, budget or real producer is selected.

Manual documents preparation is authorized separately. Automatic admission still requires real independently verified whole-P01-audit receipt, exact frozen audit gate and successful independently reviewed runtime54 deployment. P01 audit completion is not S2 producer completion. This child never marks P09 whole done or rewrites its dependency, risk or scope.
