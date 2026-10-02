"""ResearchQuestion and Hypothesis domain objects owned by PR-04."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import NewType, Self
from uuid import UUID

from researchbase.domain.organization import ProjectId
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.frozen_json import freeze_json, thaw_json
from researchbase.foundation.hashing import ContentHash
from researchbase.foundation.ids import ActorId
from researchbase.foundation.time import Clock, to_utc
from researchbase.foundation.versioning import (
    VersionStatus,
    freeze_material,
    require_transition,
    validate_version_hash,
)

ResearchQuestionId = NewType("ResearchQuestionId", UUID)
ResearchQuestionVersionId = NewType("ResearchQuestionVersionId", UUID)
HypothesisId = NewType("HypothesisId", UUID)
HypothesisVersionId = NewType("HypothesisVersionId", UUID)


@dataclass(frozen=True, slots=True)
class ResearchQuestion:
    id: ResearchQuestionId
    project_id: ProjectId
    created_by: ActorId
    created_at: datetime
    current_version_id: ResearchQuestionVersionId | None = None
    row_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise TypeError("research question id must be UUID-compatible")
        if not isinstance(self.project_id, UUID):
            raise TypeError("project id must be UUID-compatible")
        if not isinstance(self.created_by, UUID):
            raise TypeError("created_by must be UUID-compatible")
        if self.current_version_id is not None and not isinstance(self.current_version_id, UUID):
            raise TypeError("current version id must be UUID-compatible")
        object.__setattr__(self, "id", ResearchQuestionId(self.id))
        object.__setattr__(self, "project_id", ProjectId(self.project_id))
        object.__setattr__(self, "created_by", ActorId(self.created_by))
        if self.current_version_id is not None:
            object.__setattr__(
                self,
                "current_version_id",
                ResearchQuestionVersionId(self.current_version_id),
            )
        object.__setattr__(self, "created_at", to_utc(self.created_at))
        _validate_row_version(self.row_version)


@dataclass(frozen=True, slots=True)
class ResearchQuestionVersion:
    id: ResearchQuestionVersionId
    research_question_id: ResearchQuestionId
    version_number: int
    status: VersionStatus
    question_text: str
    scope: object | None
    rationale: str | None
    created_by: ActorId
    created_at: datetime
    content_hash: ContentHash | None = None
    hash_scheme: str | None = None
    frozen_at: datetime | None = None
    row_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID) or not isinstance(self.research_question_id, UUID):
            raise TypeError("research question version IDs must be UUID-compatible")
        if not isinstance(self.created_by, UUID):
            raise TypeError("created_by must be UUID-compatible")
        object.__setattr__(self, "id", ResearchQuestionVersionId(self.id))
        object.__setattr__(
            self,
            "research_question_id",
            ResearchQuestionId(self.research_question_id),
        )
        object.__setattr__(self, "created_by", ActorId(self.created_by))
        object.__setattr__(self, "status", VersionStatus(self.status))
        _validate_version_number(self.version_number)
        if not isinstance(self.question_text, str) or not self.question_text.strip():
            raise ValueError("question_text must not be blank")
        if self.scope is not None:
            object.__setattr__(self, "scope", freeze_json(self.scope))
        object.__setattr__(self, "created_at", to_utc(self.created_at))
        if self.frozen_at is not None:
            object.__setattr__(self, "frozen_at", to_utc(self.frozen_at))
        normalized_hash = validate_version_hash(
            self.status,
            self.material_payload(),
            self.content_hash,
            self.hash_scheme,
            self.frozen_at,
        )
        object.__setattr__(self, "content_hash", normalized_hash)
        _validate_row_version(self.row_version)

    def material_payload(self) -> dict[str, object | None]:
        return {
            "question_text": self.question_text,
            "scope": thaw_json(self.scope) if self.scope is not None else None,
            "rationale": self.rationale,
        }

    def edit_material(
        self, *, question_text: str, scope: object | None, rationale: str | None
    ) -> Self:
        _require_draft_for_edit(self.status)
        return replace(self, question_text=question_text, scope=scope, rationale=rationale)

    def freeze(self, clock: Clock) -> Self:
        result = freeze_material(self.status, self.material_payload(), clock)
        return replace(
            self,
            status=result.status,
            content_hash=result.content_hash,
            hash_scheme=result.hash_scheme,
            frozen_at=result.frozen_at,
        )

    def transition_to(self, target: VersionStatus) -> Self:
        require_transition(self.status, target)
        return replace(self, status=target)


@dataclass(frozen=True, slots=True)
class Hypothesis:
    id: HypothesisId
    project_id: ProjectId
    created_by: ActorId
    created_at: datetime
    research_question_id: ResearchQuestionId | None = None
    current_version_id: HypothesisVersionId | None = None
    row_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID) or not isinstance(self.project_id, UUID):
            raise TypeError("hypothesis IDs must be UUID-compatible")
        if not isinstance(self.created_by, UUID):
            raise TypeError("created_by must be UUID-compatible")
        if self.research_question_id is not None and not isinstance(
            self.research_question_id, UUID
        ):
            raise TypeError("research question id must be UUID-compatible")
        if self.current_version_id is not None and not isinstance(self.current_version_id, UUID):
            raise TypeError("current version id must be UUID-compatible")
        object.__setattr__(self, "id", HypothesisId(self.id))
        object.__setattr__(self, "project_id", ProjectId(self.project_id))
        object.__setattr__(self, "created_by", ActorId(self.created_by))
        if self.research_question_id is not None:
            object.__setattr__(
                self,
                "research_question_id",
                ResearchQuestionId(self.research_question_id),
            )
        if self.current_version_id is not None:
            object.__setattr__(
                self,
                "current_version_id",
                HypothesisVersionId(self.current_version_id),
            )
        object.__setattr__(self, "created_at", to_utc(self.created_at))
        _validate_row_version(self.row_version)


@dataclass(frozen=True, slots=True)
class HypothesisVersion:
    id: HypothesisVersionId
    hypothesis_id: HypothesisId
    version_number: int
    status: VersionStatus
    statement: str
    expected_direction: str | None
    success_criteria: object | None
    rationale: str | None
    created_by: ActorId
    created_at: datetime
    content_hash: ContentHash | None = None
    hash_scheme: str | None = None
    frozen_at: datetime | None = None
    row_version: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID) or not isinstance(self.hypothesis_id, UUID):
            raise TypeError("hypothesis version IDs must be UUID-compatible")
        if not isinstance(self.created_by, UUID):
            raise TypeError("created_by must be UUID-compatible")
        object.__setattr__(self, "id", HypothesisVersionId(self.id))
        object.__setattr__(self, "hypothesis_id", HypothesisId(self.hypothesis_id))
        object.__setattr__(self, "created_by", ActorId(self.created_by))
        object.__setattr__(self, "status", VersionStatus(self.status))
        _validate_version_number(self.version_number)
        if not isinstance(self.statement, str) or not self.statement.strip():
            raise ValueError("statement must not be blank")
        if self.success_criteria is not None:
            object.__setattr__(self, "success_criteria", freeze_json(self.success_criteria))
        object.__setattr__(self, "created_at", to_utc(self.created_at))
        if self.frozen_at is not None:
            object.__setattr__(self, "frozen_at", to_utc(self.frozen_at))
        object.__setattr__(
            self,
            "content_hash",
            validate_version_hash(
                self.status,
                self.material_payload(),
                self.content_hash,
                self.hash_scheme,
                self.frozen_at,
            ),
        )
        _validate_row_version(self.row_version)

    def material_payload(self) -> dict[str, object | None]:
        return {
            "statement": self.statement,
            "expected_direction": self.expected_direction,
            "success_criteria": (
                thaw_json(self.success_criteria) if self.success_criteria is not None else None
            ),
            "rationale": self.rationale,
        }

    def edit_material(
        self,
        *,
        statement: str,
        expected_direction: str | None,
        success_criteria: object | None,
        rationale: str | None,
    ) -> Self:
        _require_draft_for_edit(self.status)
        return replace(
            self,
            statement=statement,
            expected_direction=expected_direction,
            success_criteria=success_criteria,
            rationale=rationale,
        )

    def freeze(self, clock: Clock) -> Self:
        result = freeze_material(self.status, self.material_payload(), clock)
        return replace(
            self,
            status=result.status,
            content_hash=result.content_hash,
            hash_scheme=result.hash_scheme,
            frozen_at=result.frozen_at,
        )

    def transition_to(self, target: VersionStatus) -> Self:
        require_transition(self.status, target)
        return replace(self, status=target)


def _require_draft_for_edit(status: VersionStatus) -> None:
    if status is not VersionStatus.DRAFT:
        raise ResearchBaseError(ErrorCode.IMMUTABLE_RECORD, "version material is immutable")


def _validate_version_number(value: int) -> None:
    if value < 1:
        raise ValueError("version_number must be positive")


def _validate_row_version(value: int) -> None:
    if value < 1:
        raise ValueError("row_version must be positive")
