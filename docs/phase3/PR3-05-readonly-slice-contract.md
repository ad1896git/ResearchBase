# PR3-05 read-only slice — R1 contract

Status: R1 contract for review. The owner authorized correction of the rejected
dependencies and minimal bootstrap file admission. The three modules explicitly
named in plan §3 R1 are admitted in the existing bootstrap test; its empty-package
and activation checks remain intact. The dependency guard is unchanged. Contracts
use stdlib frozen dataclasses and a local closed source-kind vocabulary.
This inventory does not authorize R2 consumers. It does not freeze or
amend the PR3-05 draft, accept R2–R4, resolve D1/D2, or enable saving.

Authority: [slice plan §§2–5](PR3-05-readonly-slice-plan.md), the
[PR3-05 draft](../proposals/PR3-05_Context_Memory_Contract_DRAFT.md), and the
architecture/read order in [AGENTS.md](../../AGENTS.md). The owner's narrower
R1 instruction controls implementation scope and UV cache location. No new
schema, migration, dependency, exception, transport route or error enum.

## Boundary and requests

The public query protocols accept `VerifiedPrincipal` as a separate trusted
argument. Request bodies cannot supply actor identity, credentials, approval,
execution identity, grants or trusted flags. Both Human and Agent callers use
these same Application methods:

| Method | Request | Result |
| --- | --- | --- |
| `get_canonical_context_for_task` / `CanonicalContextLoader.load_for_task` | `ContextRequest` | `CanonicalContext` |
| `get_task_working_memory` | `TaskMemoryRequest` | `TaskMemoryRead` |
| `validate_promotion_context` | `PromotionContextRequest` | `PromotionContextValidation` |

`ContextRequest`: `project_id`, `task_id`, optional `step_id` (default NULL).
`TaskMemoryRequest` adds the exact `artifact_version_id`.
`PromotionContextRequest` adds `candidate_artifact_version_id`,
`candidate_content_hash`, positive `expected_task_row_version`, `target_type`
(only `RESEARCH_QUESTION_VERSION` or `HYPOTHESIS_VERSION`), and sorted unique
`canonical_basis: SourceReference[]` (maximum 256). A candidate is an artifact,
never a canonical question or hypothesis produced by this query.

All new values use stdlib frozen, slotted, keyword-only dataclasses with immutable
tuples. Constructors reject unknown fields. A local closed-type validator checks
exact declared types, literals, enums and nested frozen dataclasses recursively;
the manifest decoder also rejects unknown nested keys. Reused frozen dataclasses
are recursively checked for mutable members,
nonfinite numbers and naive timestamps. Existing safety DTOs and `TaskInput`
retain their meanings. Owning scientific text is preserved rather than subjected
to the operational memory note bound. Request/constructor validation errors must be
mapped to the existing sanitized `VALIDATION_ERROR` at the Application boundary;
raw exceptions containing input values must not be disclosed. `FrozenSource`
declares `type` explicitly; concrete subclasses check their own structured leaves
through typed attributes, without base-class discovery of subclass-only fields.

## Exact sources and canonical results

`SourceReference`: `type: InputType`, `id`, lowercase 64-hex `content_hash`,
`hash_scheme`. The latter is NULL for question, hypothesis, claim and artifact;
it is `sha256-cjson-v1` for source and manuscript. `task_input` returns the reused
`TaskInput`. No seventh task/memory source family is defined.

`InputBinding`: `id`, `task_id`, nullable `step_id`, `source`. Distinct binding
identities remain distinct even if their scientific source is equal. Bindings
sort by binding ID. `TaskContext`: `id`, `project_id`, positive `row_version`,
`plan_sealed_at`, `status`, `objective`, `selected_step_id`, sorted unique
`included_step_ids`, `bindings`. No step selection means all task steps; selecting
a step means exactly that step plus task-owned inputs. Application must check
same-task step membership, including steps with no inputs.

`ContextWarning`: `code` (STALE, INVALID, RETRACTED, CORRECTED, UNASSESSED, UNKNOWN,
SUPERSEDED), nullable entitled `source: TaskInput`, optional `assessment_id`.
`ValidityObservation`: `status` (UNASSESSED, UNKNOWN, VALID, STALE, INVALID),
`assessment_ids`, `warnings`. There is no default VALID assertion; the owning
projection supplies status. Retraction/correction remain explicit warnings
alongside source version kind. Absent assessment is UNASSESSED or UNKNOWN.

Every `CanonicalSource` variant has `type`, `reference`, `owner_id`,
`status` (FROZEN/SUPERSEDED), `frozen_at`, `validity`, and owning `closure:
ClosureReportDTO`. Variant-only fields are:

| Variant / InputType | Additional fields |
| --- | --- |
| `QuestionContext` / RESEARCH_QUESTION_VERSION | question_text, scope_json, rationale |
| `HypothesisContext` / HYPOTHESIS_VERSION | statement, expected_direction, success_criteria_json, rationale |
| `ClaimContext` / CLAIM_VERSION | statement, scope_json, qualification, support_set_hash, experiment_trace: ClaimToRunsTraceDTO |
| `LiteratureContext` / SOURCE_VERSION | version_kind (closed strings matching the owning source vocabulary), title, abstract, authors, publication_date, venue, external_version_label, metadata, predecessor, correction_basis, fulltext |
| `ArtifactContext` / ARTIFACT_VERSION | media_type, byte_size, verified_bytes, metadata_json |
| `ManuscriptContext` / MANUSCRIPT_VERSION | title, abstract, semantic_change_class, document, placement_set_hash, placements, scientific_trace |

`SourceAuthor`: name, orcid. `SourceMetadata`: journal_identifier, volume, issue,
pages, license_label, public_repository_label; all six are nullable strings.
Literature dependency references and manuscript document use `SourceReference`;
their actual family, project access and owning closure require owning-domain
verification in R2. `owner_id` is the owning identity, never a latest pointer.

`scope_json`, `success_criteria_json`, `metadata_json` are nullable immutable
canonical UTF-8 bytes for the existing owning-domain structured leaves. They are
not an extension bag for context, policy, authority or manifest fields. Duplicate
keys, nonfinite numbers and noncanonical encoding reject. Their schemas/hashes
and bounds remain owned by the existing domains; they have no memory byte limit.

`PlacementContext`: id, kind (CLAIM/CITATION/ARTIFACT/CONCLUSION), target_id,
target_content_hash, section_id, locator_kind (PARAGRAPH/SPAN/CAPTION/ANCHOR),
locator_value, ordinal, annotation, semantic, nullable support_set_hash.
`ScientificTrace`: conclusion_claim_inputs, claim_experiment_evidence,
literature_evidence, using the delivered immutable owning trace row DTOs.
Run/evidence/conclusion traversal creates no additional task input family.
Adapters must retain complete required paths, sort relation/placement identities,
scope nodes before expansion and apply their owning value/hash/closure checks.

`CanonicalContext`: `snapshot_at`, `task`, sorted unique `sources` by (type, ID),
`safety: TaskSafetyRead`, `checkpoint_history: CheckpointHistoryRead`, `warnings`.
Every binding must resolve to the exact source/hash, source discriminants must
match, closure must be complete, and safety/history task and revision must match.
Expansion is not truncated to the memory manifest's 256-source bound. Structural
contradiction fails the query; it is not a partial-success warning. Required
artifact bytes must exist now and match raw SHA-256/size. DTO construction alone
does not prove entitlement or completeness of database traversal.

Canonical context has no memory, scratchpad or conversation field. Canonical
reviewer reconstruction therefore requires no author memory; PR3-14 reviewer
construction/execution remains future work.

## Closed operational memory format

`TaskMemoryManifest` specializes the domain `MemoryFormat` envelope with
`source_refs: SourceReference[]`. Its exact fields are `format_version` (1),
`project_scope`, `task_id`, nullable `step_id`, `created_by`, `trust_level`,
`validity_status`, `notes`, `source_refs`. Trust labels are UNVERIFIED,
SOURCE_VERIFIED, UNUSABLE; saved labels are observations only, never authority.
Validity labels use the five `ValidityObservation` statuses above. Creator is
attribution, not execution provenance or proof of an atomic save.

`notes: MemoryNotes` has exactly `plan_notes`, `candidate_notes`, `tool_summaries`,
each a tuple of NFC strings (default empty). Each string is at most 8,192 Unicode
characters. No executable, credential, private scratchpad or authority fields
exist. Instruction-like text remains inert data; consumers never execute it.

Maximum encoded manifest is 1,048,576 bytes; maximum source count is 256.
`parse_memory_manifest` rejects duplicate object keys, duplicate source identities
even with different hashes, unknown nested fields/types, nonfinite values,
malformed/noncanonical UUIDs, non-NFC notes, unsorted sources, invalid UTF-8,
noncanonical JSON and oversize content. All fields appear in canonical bytes,
including NULLs and empty note tuples encoded as arrays. Compare original bytes
to `canonical_json_bytes(memory_material(manifest))`; never normalize or rewrite
bytes to make their identity pass. Parse errors are sanitized VALIDATION_ERROR.

`TaskMemoryRead`: snapshot_at, scope, artifact_version_id, content_hash, byte_size,
verified_bytes, manifest, current_sources, derived_trust_level, current_validity,
warnings. The result verifies exact bytes/hash/size/closed manifest/scope and
matching ordered current source references. A usable result has derived trust
SOURCE_VERIFIED; this means source identity was checked, not scientific validity.
Each current source must be reauthorized/reloaded within the same snapshot before
returning bytes or notes. Frozen memory can remain scientifically stale/invalid.

Explicit reads: missing entitled version is NOT_FOUND; missing/corrupt/malformed
bytes are VALIDATION_ERROR. Optional consumption may use `UnusableMemory` with
exact fields `code` (NOT_FOUND/VALIDATION_ERROR), `reason`
(MISSING_VERSION/UNUSABLE_CONTENT). It contains no suspect bytes or protected
metadata. This diagnostic is separate from canonical context, which can be
rebuilt independently. It never catches FORBIDDEN or hides a required canonical
failure. No lost private notes are fabricated or storage repaired.

## Promotion validation and read capabilities

`PromotionFailure`: existing `ErrorCode` plus reason (REVISION_MISMATCH,
CANDIDATE_MISMATCH, BASIS_MISMATCH, GATE_UNMET,
S2_PRODUCER_PROVENANCE_UNVERIFIED). `PromotionContextValidation`: snapshot_at,
scope, candidate: ArtifactContext, target_type, requested_task_row_version,
context, validated_basis, context_admissible, failures,
producer_provenance_verified=False, promotion_enabled=False,
execution_enabled=False, provider_disclosure_granted=False.

Context admissibility concerns the checked basis/gates only. The explicit S2
producer-provenance failure is mandatory even for admissible context. No execution
ID, persisted validation, promotion record, reservation or reusable grant is
created. Subsequent writers must independently revalidate in their transaction.
Scope denial raises sanitized FORBIDDEN without returning candidate/context or
foreign details; it is never a failure row that discloses partial context.

`ContextUnitOfWork` exposes only `begin_formal_read`, context-manager lifetime,
`research_tasks: TaskContextReadRepository`, `task_safety:
SafetyContextReadRepository`, `context_reads: ContextRepository`.
`ContextUowFactory` constructs one such UoW per public call. The first Application
SQL follows `begin_formal_read`: REPEATABLE READ READ ONLY, autoflush disabled.
Capture one `task_safety.snapshot_at()` and pass it to all projections. Reuse
delivered safety_projection/verify_saved_policies on this session.

Task read methods: authority, project_active, task, steps, inputs, input_version.
Safety read methods: snapshot_at, rows, scope_reference, events. These protocols
expose private read rows only; they never accept arbitrary caller row payloads.
Context read methods: task_context, bindings, source, validity, artifact,
verify_source; every lookup receives explicit scope/project. A returned projection
is not an access token. Adapter composition must authorize before protected
diagnostics/expansion and preserve owning-domain same-session verification.

No port inherits a write-capable repository or exposes commit, flush, locks,
save/replay, mutation, provider calls or ArtifactStore writes. Local immutable
byte reads occur after DB scope checks; global/foreign artifacts are denied.
The protocols are contracts, not wired adapters/services or PostgreSQL evidence.

## Evidence and remaining gates

R1 names no PostgreSQL test file. Its required scoped static checks plus the
owner's full static, migration-head, unit and architecture commands are reported
with current raw output and exit codes in the task response. R4 owns new contract
adversarial tests, PostgreSQL snapshot/concurrency evidence, consumer acceptance
and the durable evidence document. No whole-suite evidence is claimed here.
Stop after R1 evidence; no R2 implementation, saving or activation follows.

Current R1 revision evidence (repository-local `UV_CACHE_DIR` is
`$PWD/tmp/pr3-03-uv-cache`):

```sh
git diff --check HEAD && uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run alembic heads | grep -q '0080_capability_gateway (head)' && uv run pytest -o addopts='' -q tests/unit/phase3 tests/architecture tests/unit/architecture
```

Exit code 0. Ruff: `All checks passed!`; format: `918 files already formatted`;
Pyright: `0 errors, 0 warnings, 0 informations` (plus its tool-update notice).
Pytest: `1351 passed, 50 warnings in 28.48s`; warnings are the existing Alembic
`path_separator` deprecation. No failure or skip was reported. A separate
`uv run alembic heads` exited 0 with `0080_capability_gateway (head)`.
The R1-scoped Ruff/Pyright checks also exited 0. A local contract smoke run
exited 0 for round-trip parsing, immutability, nested-field rejection, note
bounds and typed scientific leaves. These are R1 checks, not R4 PostgreSQL or
whole-suite acceptance. R1 names no PostgreSQL suite; none was run.
