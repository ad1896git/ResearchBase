"""Closed read-only context contracts. Trusted principals are separate call arguments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from hashlib import sha256
from typing import Literal, cast
from uuid import UUID

from researchbase.agent_runtime.application.contracts import InputType, TaskInput
from researchbase.agent_runtime.application.safety_contracts import (
    CheckpointHistoryRead,
    TaskSafetyRead,
)
from researchbase.agent_runtime.domain.task_memory import (
    MAX_MANIFEST_BYTES,
    MAX_SOURCES,
    ClosedReadValue,
    Digest,
    MemoryFormat,
    TrustLevel,
    ValidityStatus,
    canonical_manifest_object,
    closed_value,
    memory_error,
    memory_material,
    nonnegative,
    positive,
)
from researchbase.application.manuscript_scientific_trace import (
    ClaimExperimentEvidenceTrace,
    ConclusionClaimInputTrace,
    LiteratureEvidenceTrace,
)
from researchbase.application.provenance_queries import ClaimToRunsTraceDTO, ClosureReportDTO
from researchbase.foundation.canonical_json import canonical_json_bytes
from researchbase.foundation.errors import ErrorCode


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextRequest(ClosedReadValue):
    project_id: UUID
    task_id: UUID
    step_id: UUID | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskMemoryRequest(ContextRequest):
    artifact_version_id: UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceReference(ClosedReadValue):
    type: InputType
    id: UUID
    content_hash: Digest
    hash_scheme: Literal["sha256-cjson-v1"] | None

    @property
    def task_input(self) -> TaskInput:
        return TaskInput(self.type, self.id)

    def __post_init__(self) -> None:
        ClosedReadValue.__post_init__(self)
        phase2 = self.type in {InputType.SOURCE_VERSION, InputType.MANUSCRIPT_VERSION}
        if phase2 != (self.hash_scheme is not None):
            raise ValueError("owning binding hash scheme required")


def ordered_sources(values: tuple[SourceReference, ...]) -> tuple[SourceReference, ...]:
    if len(values) > MAX_SOURCES or len({(v.type, v.id) for v in values}) != len(values):
        raise ValueError("bounded unique source set required")
    return tuple(sorted(values, key=lambda v: (v.type, str(v.id))))


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskMemoryManifest(MemoryFormat):
    source_refs: tuple[SourceReference, ...]

    def __post_init__(self) -> None:
        ClosedReadValue.__post_init__(self)
        if ordered_sources(self.source_refs) != self.source_refs:
            raise ValueError("sorted source set required")
        if len(canonical_json_bytes(memory_material(self))) > MAX_MANIFEST_BYTES:
            raise ValueError("manifest byte bound exceeded")


def parse_memory_manifest(raw: bytes) -> TaskMemoryManifest:
    """Decode an already entitled, byte-verified artifact without normalizing its bytes."""
    value = canonical_manifest_object(raw)
    try:
        result = cast(TaskMemoryManifest, closed_value(TaskMemoryManifest, value, decode=True))
        # Detect noncanonical UUID spellings as well as every nested format discrepancy.
        if canonical_json_bytes(memory_material(result)) != raw:
            raise ValueError("canonical closed manifest required")
        return result
    except (ValueError, TypeError, UnicodeError, RecursionError):
        memory_error()
        raise AssertionError("unreachable") from None


@dataclass(frozen=True, slots=True, kw_only=True)
class PromotionContextRequest(ContextRequest):
    candidate_artifact_version_id: UUID
    candidate_content_hash: Digest
    expected_task_row_version: int
    target_type: Literal["RESEARCH_QUESTION_VERSION", "HYPOTHESIS_VERSION"]
    canonical_basis: tuple[SourceReference, ...]

    def __post_init__(self) -> None:
        ClosedReadValue.__post_init__(self)
        positive(self.expected_task_row_version)
        if ordered_sources(self.canonical_basis) != self.canonical_basis:
            raise ValueError("sorted canonical basis required")


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextWarning(ClosedReadValue):
    """Only entitled observations; never include raw SQL or denied object identifiers."""

    code: Literal[
        "STALE", "INVALID", "RETRACTED", "CORRECTED", "UNASSESSED", "UNKNOWN", "SUPERSEDED"
    ]
    source: TaskInput | None
    assessment_id: UUID | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ValidityObservation(ClosedReadValue):
    status: ValidityStatus
    assessment_ids: tuple[UUID, ...] = ()
    warnings: tuple[ContextWarning, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class InputBinding(ClosedReadValue):
    """The binding ID and owner survive source deduplication."""

    id: UUID
    task_id: UUID
    step_id: UUID | None
    source: SourceReference


@dataclass(frozen=True, slots=True, kw_only=True)
class FrozenSource(ClosedReadValue):
    type: InputType
    reference: SourceReference
    owner_id: UUID
    status: Literal["FROZEN", "SUPERSEDED"]
    frozen_at: datetime
    validity: ValidityObservation
    closure: ClosureReportDTO

    def __post_init__(self) -> None:
        ClosedReadValue.__post_init__(self)
        if self.reference.type != self.type or not self.closure.complete:
            raise ValueError("complete matching frozen source required")


def _canonical_scientific_leaf(raw: bytes | None) -> None:
    """Canonical scientific leaves have their owning bounds, not the memory byte bound."""
    import json

    if raw is None:
        return

    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        result = dict(items)
        if len(result) != len(items):
            raise ValueError("duplicate structured leaf key")
        return result

    if canonical_json_bytes(json.loads(raw, object_pairs_hook=pairs)) != raw:
        raise ValueError("canonical owning structured leaf required")


@dataclass(frozen=True, slots=True, kw_only=True)
class QuestionContext(FrozenSource):
    type: Literal[InputType.RESEARCH_QUESTION_VERSION] = InputType.RESEARCH_QUESTION_VERSION
    question_text: str
    scope_json: bytes | None
    rationale: str | None

    def __post_init__(self) -> None:
        FrozenSource.__post_init__(self)
        _canonical_scientific_leaf(self.scope_json)


@dataclass(frozen=True, slots=True, kw_only=True)
class HypothesisContext(FrozenSource):
    type: Literal[InputType.HYPOTHESIS_VERSION] = InputType.HYPOTHESIS_VERSION
    statement: str
    expected_direction: str | None
    success_criteria_json: bytes | None
    rationale: str | None

    def __post_init__(self) -> None:
        FrozenSource.__post_init__(self)
        _canonical_scientific_leaf(self.success_criteria_json)


@dataclass(frozen=True, slots=True, kw_only=True)
class ClaimContext(FrozenSource):
    type: Literal[InputType.CLAIM_VERSION] = InputType.CLAIM_VERSION
    statement: str
    scope_json: bytes | None
    qualification: str | None
    support_set_hash: Digest
    experiment_trace: ClaimToRunsTraceDTO

    def __post_init__(self) -> None:
        FrozenSource.__post_init__(self)
        _canonical_scientific_leaf(self.scope_json)


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceAuthor(ClosedReadValue):
    name: str
    orcid: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceMetadata(ClosedReadValue):
    journal_identifier: str | None
    volume: str | None
    issue: str | None
    pages: str | None
    license_label: str | None
    public_repository_label: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class LiteratureContext(FrozenSource):
    type: Literal[InputType.SOURCE_VERSION] = InputType.SOURCE_VERSION
    version_kind: Literal[
        "SUBMITTED",
        "PREPRINT",
        "REVISED_PREPRINT",
        "ACCEPTED",
        "PUBLISHED",
        "CORRECTED",
        "RETRACTED",
        "WEB_SNAPSHOT",
        "OTHER",
    ]
    title: str
    abstract: str | None
    authors: tuple[SourceAuthor, ...]
    publication_date: date | None
    venue: str | None
    external_version_label: str | None
    metadata: SourceMetadata | None
    predecessor: SourceReference | None
    correction_basis: SourceReference | None
    fulltext: SourceReference | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactContext(FrozenSource):
    type: Literal[InputType.ARTIFACT_VERSION] = InputType.ARTIFACT_VERSION
    media_type: str | None
    byte_size: int
    verified_bytes: bytes
    metadata_json: bytes | None

    def __post_init__(self) -> None:
        FrozenSource.__post_init__(self)
        nonnegative(self.byte_size)
        _canonical_scientific_leaf(self.metadata_json)
        if self.reference.type != self.type or (
            len(self.verified_bytes) != self.byte_size
            or sha256(self.verified_bytes).hexdigest() != self.reference.content_hash
        ):
            raise ValueError("artifact byte identity contradiction")


@dataclass(frozen=True, slots=True, kw_only=True)
class PlacementContext(ClosedReadValue):
    id: UUID
    kind: Literal["CLAIM", "CITATION", "ARTIFACT", "CONCLUSION"]
    target_id: UUID
    target_content_hash: Digest
    section_id: str
    locator_kind: Literal["PARAGRAPH", "SPAN", "CAPTION", "ANCHOR"]
    locator_value: str
    ordinal: int
    annotation: str
    semantic: str
    support_set_hash: Digest | None

    def __post_init__(self) -> None:
        ClosedReadValue.__post_init__(self)
        nonnegative(self.ordinal)


@dataclass(frozen=True, slots=True, kw_only=True)
class ScientificTrace(ClosedReadValue):
    """Existing owning trace rows, with mutable placement locators made closed above."""

    conclusion_claim_inputs: tuple[ConclusionClaimInputTrace, ...]
    claim_experiment_evidence: tuple[ClaimExperimentEvidenceTrace, ...]
    literature_evidence: tuple[LiteratureEvidenceTrace, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ManuscriptContext(FrozenSource):
    type: Literal[InputType.MANUSCRIPT_VERSION] = InputType.MANUSCRIPT_VERSION
    title: str
    abstract: str | None
    semantic_change_class: str
    document: SourceReference
    placement_set_hash: Digest
    placements: tuple[PlacementContext, ...]
    scientific_trace: ScientificTrace


type CanonicalSource = (
    QuestionContext
    | HypothesisContext
    | ClaimContext
    | LiteratureContext
    | ArtifactContext
    | ManuscriptContext
)


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskContext(ClosedReadValue):
    id: UUID
    project_id: UUID
    row_version: int
    plan_sealed_at: datetime | None
    status: str
    objective: str
    selected_step_id: UUID | None
    included_step_ids: tuple[UUID, ...]
    bindings: tuple[InputBinding, ...]

    def __post_init__(self) -> None:
        ClosedReadValue.__post_init__(self)
        positive(self.row_version)
        if self.included_step_ids != tuple(sorted(set(self.included_step_ids), key=str)):
            raise ValueError("sorted unique included steps required")
        if self.selected_step_id is not None and self.included_step_ids != (self.selected_step_id,):
            raise ValueError("selected step scope required")
        if len({b.id for b in self.bindings}) != len(self.bindings) or self.bindings != tuple(
            sorted(self.bindings, key=lambda b: str(b.id))
        ):
            raise ValueError("sorted unique binding identities required")
        for binding in self.bindings:
            if binding.task_id != self.id or (
                binding.step_id is not None and binding.step_id not in self.included_step_ids
            ):
                raise ValueError("same-task binding owner required")


@dataclass(frozen=True, slots=True, kw_only=True)
class CanonicalContext(ClosedReadValue):
    """Memory is deliberately absent. A complete required graph is never truncated."""

    snapshot_at: datetime
    task: TaskContext
    sources: tuple[CanonicalSource, ...]
    safety: TaskSafetyRead
    checkpoint_history: CheckpointHistoryRead
    warnings: tuple[ContextWarning, ...] = ()

    def __post_init__(self) -> None:
        ClosedReadValue.__post_init__(self)
        refs = tuple(s.reference for s in self.sources)
        # Context expansion is not subject to the operational manifest's 256-source bound.
        if len({(v.type, v.id) for v in refs}) != len(refs) or refs != tuple(
            sorted(refs, key=lambda v: (v.type, str(v.id)))
        ):
            raise ValueError("sorted unique canonical sources required")
        for source in self.sources:
            if source.reference.type != source.type or not source.closure.complete:
                raise ValueError("complete matching source required")
        if any(binding.source not in refs for binding in self.task.bindings):
            raise ValueError("every binding requires its exact source")
        if (
            self.safety.task_id != self.task.id
            or self.safety.task_row_version != self.task.row_version
            or self.checkpoint_history.task_id != self.task.id
            or self.checkpoint_history.task_row_version != self.task.row_version
            or self.safety.execution_enabled
        ):
            raise ValueError("same-task non-authorizing safety projection required")


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskMemoryRead(ClosedReadValue):
    snapshot_at: datetime
    scope: ContextRequest
    artifact_version_id: UUID
    content_hash: Digest
    byte_size: int
    verified_bytes: bytes
    manifest: TaskMemoryManifest
    current_sources: tuple[CanonicalSource, ...]
    derived_trust_level: TrustLevel
    current_validity: ValidityObservation
    warnings: tuple[ContextWarning, ...] = ()

    def __post_init__(self) -> None:
        ClosedReadValue.__post_init__(self)
        nonnegative(self.byte_size)
        if self.byte_size > MAX_MANIFEST_BYTES:
            raise ValueError("manifest byte bound exceeded")
        if (
            len(self.verified_bytes) != self.byte_size
            or sha256(self.verified_bytes).hexdigest() != self.content_hash
            or parse_memory_manifest(self.verified_bytes) != self.manifest
            or self.manifest.project_scope != self.scope.project_id
            or self.manifest.task_id != self.scope.task_id
            or self.manifest.step_id != self.scope.step_id
            or tuple(s.reference for s in self.current_sources) != self.manifest.source_refs
            or self.derived_trust_level != "SOURCE_VERIFIED"
        ):
            raise ValueError("verified entitled memory result required")


@dataclass(frozen=True, slots=True, kw_only=True)
class UnusableMemory(ClosedReadValue):
    """Optional consumption only; no suspect bytes, source counts, hashes or locators."""

    code: Literal[ErrorCode.NOT_FOUND, ErrorCode.VALIDATION_ERROR]
    reason: Literal["MISSING_VERSION", "UNUSABLE_CONTENT"]

    def __post_init__(self) -> None:
        ClosedReadValue.__post_init__(self)
        if (self.code == ErrorCode.NOT_FOUND) != (self.reason == "MISSING_VERSION"):
            raise ValueError("matching unusable-memory diagnostic required")


@dataclass(frozen=True, slots=True, kw_only=True)
class PromotionFailure(ClosedReadValue):
    code: ErrorCode
    reason: Literal[
        "REVISION_MISMATCH",
        "CANDIDATE_MISMATCH",
        "BASIS_MISMATCH",
        "GATE_UNMET",
        "S2_PRODUCER_PROVENANCE_UNVERIFIED",
    ]


@dataclass(frozen=True, slots=True, kw_only=True)
class PromotionContextValidation(ClosedReadValue):
    snapshot_at: datetime
    scope: ContextRequest
    candidate: ArtifactContext
    target_type: Literal["RESEARCH_QUESTION_VERSION", "HYPOTHESIS_VERSION"]
    requested_task_row_version: int
    context: CanonicalContext
    validated_basis: tuple[SourceReference, ...]
    context_admissible: bool
    failures: tuple[PromotionFailure, ...]
    producer_provenance_verified: Literal[False] = False
    promotion_enabled: Literal[False] = False
    execution_enabled: Literal[False] = False
    provider_disclosure_granted: Literal[False] = False

    def __post_init__(self) -> None:
        ClosedReadValue.__post_init__(self)
        positive(self.requested_task_row_version)
        if not any(f.reason == "S2_PRODUCER_PROVENANCE_UNVERIFIED" for f in self.failures):
            raise ValueError("unverified S2 producer must remain explicit")
        if ordered_sources(self.validated_basis) != self.validated_basis:
            raise ValueError("sorted validated basis required")
        if self.context_admissible and (
            self.requested_task_row_version != self.context.task.row_version
            or any(f.reason != "S2_PRODUCER_PROVENANCE_UNVERIFIED" for f in self.failures)
        ):
            raise ValueError("admissible context cannot have a context failure")
