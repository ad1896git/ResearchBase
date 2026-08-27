from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

import pytest
from tests.contracts.version_contract import assert_version_contract

from researchbase.domain.organization import ProjectId
from researchbase.domain.research import (
    Hypothesis,
    HypothesisId,
    HypothesisVersion,
    HypothesisVersionId,
    ResearchQuestion,
    ResearchQuestionId,
    ResearchQuestionVersion,
    ResearchQuestionVersionId,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import ActorId
from researchbase.foundation.time import Clock, FixedClock
from researchbase.foundation.versioning import VersionStatus

FIXED_TIME = datetime(2026, 8, 27, 4, 0, tzinfo=UTC)


def test_research_question_and_hypothesis_identities_validate_and_start_without_pointer() -> None:
    actor_id = ActorId(uuid4())
    project_id = ProjectId(uuid4())

    question = ResearchQuestion(
        id=ResearchQuestionId(uuid4()),
        project_id=project_id,
        created_by=actor_id,
        created_at=FIXED_TIME,
    )
    hypothesis = Hypothesis(
        id=HypothesisId(uuid4()),
        project_id=project_id,
        research_question_id=question.id,
        created_by=actor_id,
        created_at=FIXED_TIME,
    )

    assert question.current_version_id is None
    assert hypothesis.current_version_id is None
    assert hypothesis.research_question_id == question.id
    assert question.row_version == hypothesis.row_version == 1


@pytest.mark.parametrize("text", ["", "   "])
def test_version_material_text_cannot_be_blank(text: str) -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        ResearchQuestionVersion(
            id=ResearchQuestionVersionId(uuid4()),
            research_question_id=ResearchQuestionId(uuid4()),
            version_number=1,
            status=VersionStatus.DRAFT,
            question_text=text,
            scope=None,
            rationale=None,
            created_by=ActorId(uuid4()),
            created_at=FIXED_TIME,
        )
    with pytest.raises(ValueError, match="must not be blank"):
        HypothesisVersion(
            id=HypothesisVersionId(uuid4()),
            hypothesis_id=HypothesisId(uuid4()),
            version_number=1,
            status=VersionStatus.DRAFT,
            statement=text,
            expected_direction=None,
            success_criteria=None,
            rationale=None,
            created_by=ActorId(uuid4()),
            created_at=FIXED_TIME,
        )


def test_research_question_material_payload_is_explicit_and_excludes_metadata() -> None:
    version = _research_question_version()

    assert version.material_payload() == {
        "question_text": "Does treatment improve outcome?",
        "scope": {"population": "adults"},
        "rationale": "Prior evidence is mixed.",
    }
    assert "id" not in version.material_payload()
    assert "created_at" not in version.material_payload()
    assert "row_version" not in version.material_payload()


def test_hypothesis_material_payload_is_explicit_and_excludes_metadata() -> None:
    version = _hypothesis_version()

    assert version.material_payload() == {
        "statement": "Treatment improves outcome.",
        "expected_direction": "increase",
        "success_criteria": {"metric": "outcome", "threshold": 0.1},
        "rationale": "Mechanistic rationale.",
    }
    assert "id" not in version.material_payload()
    assert "created_at" not in version.material_payload()
    assert "row_version" not in version.material_payload()


def test_concrete_versions_reuse_pr03_freeze_hash_and_transition_semantics() -> None:
    clock = FixedClock(FIXED_TIME)
    question = _research_question_version().freeze(clock)
    hypothesis = _hypothesis_version().freeze(clock)

    assert question.status is VersionStatus.FROZEN
    assert hypothesis.status is VersionStatus.FROZEN
    assert question.content_hash is not None
    assert hypothesis.content_hash is not None
    assert question.hash_scheme == hypothesis.hash_scheme == "sha256-cjson-v1"
    assert question.frozen_at == hypothesis.frozen_at == FIXED_TIME

    with pytest.raises(ResearchBaseError) as question_error:
        question.edit_material(question_text="changed", scope=None, rationale=None)
    assert question_error.value.code is ErrorCode.IMMUTABLE_RECORD


def test_concrete_versions_reject_freeze_from_non_draft() -> None:
    clock = FixedClock(FIXED_TIME)
    question = _research_question_version().freeze(clock)
    with pytest.raises(ResearchBaseError) as error:
        question.freeze(clock)
    assert error.value.code is ErrorCode.INVALID_STATE_TRANSITION


class ResearchQuestionVersionContractAdapter:
    def __init__(self, material: object) -> None:
        material_mapping = cast(dict[str, object], material)
        self.version = ResearchQuestionVersion(
            id=ResearchQuestionVersionId(uuid4()),
            research_question_id=ResearchQuestionId(uuid4()),
            version_number=1,
            status=VersionStatus.DRAFT,
            question_text=str(material_mapping["title"]),
            scope=None,
            rationale=None,
            created_by=ActorId(uuid4()),
            created_at=FIXED_TIME,
        )
        self.non_material_metadata = {
            "id": uuid4(),
            "created_at": "2026-08-27T04:00:00Z",
            "row_version": 1,
        }

    @property
    def status(self) -> VersionStatus:
        return self.version.status

    @property
    def content_hash(self):
        return self.version.content_hash

    @property
    def hash_scheme(self):
        return self.version.hash_scheme

    @property
    def frozen_at(self):
        return self.version.frozen_at

    def edit_material(self, material: object) -> None:
        material_mapping = cast(dict[str, object], material)
        self.version = self.version.edit_material(
            question_text=str(material_mapping["title"]),
            scope=None,
            rationale=None,
        )

    def freeze(self, clock: Clock) -> None:
        self.version = self.version.freeze(clock)

    def transition_to(self, target: VersionStatus) -> None:
        self.version = self.version.transition_to(target)


class HypothesisVersionContractAdapter:
    def __init__(self, material: object) -> None:
        material_mapping = cast(dict[str, object], material)
        self.version = HypothesisVersion(
            id=HypothesisVersionId(uuid4()),
            hypothesis_id=HypothesisId(uuid4()),
            version_number=1,
            status=VersionStatus.DRAFT,
            statement=str(material_mapping["title"]),
            expected_direction=None,
            success_criteria=None,
            rationale=None,
            created_by=ActorId(uuid4()),
            created_at=FIXED_TIME,
        )
        self.non_material_metadata = {
            "id": uuid4(),
            "created_at": "2026-08-27T04:00:00Z",
            "row_version": 1,
        }

    @property
    def status(self) -> VersionStatus:
        return self.version.status

    @property
    def content_hash(self):
        return self.version.content_hash

    @property
    def hash_scheme(self):
        return self.version.hash_scheme

    @property
    def frozen_at(self):
        return self.version.frozen_at

    def edit_material(self, material: object) -> None:
        material_mapping = cast(dict[str, object], material)
        self.version = self.version.edit_material(
            statement=str(material_mapping["title"]),
            expected_direction=None,
            success_criteria=None,
            rationale=None,
        )

    def freeze(self, clock: Clock) -> None:
        self.version = self.version.freeze(clock)

    def transition_to(self, target: VersionStatus) -> None:
        self.version = self.version.transition_to(target)


@pytest.mark.parametrize(
    "factory",
    [ResearchQuestionVersionContractAdapter, HypothesisVersionContractAdapter],
)
def test_both_concrete_versions_pass_reusable_pr03_contract(factory: object) -> None:
    assert_version_contract(factory)  # type: ignore[arg-type]


def _research_question_version() -> ResearchQuestionVersion:
    return ResearchQuestionVersion(
        id=ResearchQuestionVersionId(uuid4()),
        research_question_id=ResearchQuestionId(uuid4()),
        version_number=1,
        status=VersionStatus.DRAFT,
        question_text="Does treatment improve outcome?",
        scope={"population": "adults"},
        rationale="Prior evidence is mixed.",
        created_by=ActorId(uuid4()),
        created_at=FIXED_TIME,
    )


def _hypothesis_version() -> HypothesisVersion:
    return HypothesisVersion(
        id=HypothesisVersionId(uuid4()),
        hypothesis_id=HypothesisId(uuid4()),
        version_number=1,
        status=VersionStatus.DRAFT,
        statement="Treatment improves outcome.",
        expected_direction="increase",
        success_criteria={"metric": "outcome", "threshold": 0.1},
        rationale="Mechanistic rationale.",
        created_by=ActorId(uuid4()),
        created_at=FIXED_TIME,
    )
