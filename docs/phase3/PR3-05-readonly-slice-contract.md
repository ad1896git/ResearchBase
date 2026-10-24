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

### R3 read-service composition

`TaskMemoryService.get_task_working_memory` and
`PromotionContextService.validate_promotion_context` each begin one formal read,
sample snapshot time once and call R2's `context_in_uow` on that UoW. Required
canonical reconstruction precedes optional-memory handling. The services accept
the same trusted principal boundary for Human and Agent callers.

Memory reads check exact-version project scope before the DB byte-size bound or
store access, then verify the returned bytes against the saved size/hash and the
closed manifest. Manifest project/task/step locators must match the request.
Every manifest source is reloaded with its exact saved hash/scheme before bytes
or notes are returned. Current validity combines the memory artifact and source
observations; saved trust/validity labels never replace those observations.
`get_optional_task_working_memory` returns `UnusableMemory` only for a missing
memory version or unusable local memory content. Scope denial, required canonical
failures and manifest-source failures propagate even on that optional path.

Promotion validation compares the requested revision and candidate hash, and
checks the complete selected task/step input basis. Requested basis identities
are scoped and reloaded even when another comparison has failed; denied sources
never become partial validation responses. `validated_basis` contains only exact
matching selected inputs. Missing safety-policy bindings, cancellation, recorded
stops or unsatisfied task/selected-step checkpoints produce `GATE_UNMET`.
Runtime activation prerequisites remain visible in the canonical safety read;
S2 producer provenance remains a separate mandatory unmet failure. An admissible
context still has all execution, promotion and provider-disclosure flags false.

The bootstrap admission inventory includes exactly the two plan §3 R3 modules;
its other empty-package and activation guards remain intact. These additions
enable no save, receipt, migration, lock change, provider or promotion command.
R3 names only its scoped static checks; PostgreSQL test paths and permanent
consumer acceptance coverage are allocated under R4. R3 verification does not
claim R4 or full PR3-05 acceptance.

### R2 review corrections

R2 composes the owning readers through public same-UoW entry points:
`verify_artifact_in_uow`, `verify_claim_in_uow`,
`trace_claim_to_runs_in_uow`, `source_material_in_uow`, and the existing
`verify_in_uow`, `build_in_uow` and `validity_projection_in_uow`.
`ContextDependencyVerifier` collects the existing owning traversal observations;
its private hook stays inside the owning Application module. The context adapter
scopes every dependency before invoking those readers, which retain the caller's
UoW and cannot open a second transaction. Its bounded public dependencies are
pinned by `tests/architecture/test_pr3_05_readonly_boundaries.py`. No owning hash,
closure, lifecycle, lock or write contract changes.

`TaskContextAdmission` shares the existing authorization implementation with
`ResearchTaskService`, without accepting a command factory. Canonical reads use
its public admission method. Private read-row sequences may be tuples or lists
(the protocol uses `Sequence` to match delivered adapters); public results remain
recursively immutable tuples and frozen dataclasses.

Both API and CLI `build_services` composition roots bind their configured local
ArtifactStore to the UoW and expose `ServiceBundle.canonical_context`. No new
transport route is added. Artifact-bearing reads through those real composition
roots are tested, rather than relying on a test-only factory.

Durable R2 coverage is in `tests/unit/phase3/test_canonical_context.py` and
`tests/integration/phase3/test_pr3_05_context_reads.py`. The latter uses the
existing explicitly selected disposable PostgreSQL 18 fixture, exercises all six
families and the real composition roots, and observes the actual reader session,
SQL and snapshot while a legitimate concurrent writer commits. It also tests
scope denial before store access, required descendant-byte loss/corruption,
binding contradictions, validity warnings and non-authorizing safety/expiry.
The contradictory-binding test fault-injects a read projection; it neither alters
canonical rows nor bypasses a persistence guard. These R2 checks do not accept
R3/R4, enable saving, or open the full PR3-05 gate.

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
