from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

import pytest
from tests.contracts.version_contract import VersionFixture, assert_version_contract

from researchbase.domain.experiment import (
    ExperimentSpec,
    ExperimentSpecId,
    ExperimentSpecVersion,
    ExperimentSpecVersionId,
)
from researchbase.domain.organization import ProjectId
from researchbase.domain.research import HypothesisId
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import ActorId
from researchbase.foundation.time import Clock, FixedClock
from researchbase.foundation.versioning import VersionStatus

FIXED_TIME = datetime(2026, 8, 27, 4, 0, tzinfo=UTC)


def _version(**overrides: object) -> ExperimentSpecVersion:
    values: dict[str, Any] = {
        "id": ExperimentSpecVersionId(uuid4()),
        "experiment_spec_id": ExperimentSpecId(uuid4()),
        "version_number": 1,
        "status": VersionStatus.DRAFT,
        "title": "Treatment experiment",
        "objective": "Measure treatment effect",
        "protocol": {"arms": ["control", "treatment"]},
        "planned_metrics": [{"name": "outcome"}],
        "seed_policy": {"kind": "fixed"},
        "analysis_plan": {"test": "difference-in-means"},
        "created_by": ActorId(uuid4()),
        "created_at": FIXED_TIME,
    }
    values.update(overrides)
    return ExperimentSpecVersion(**values)


def test_identity_accepts_optional_hypothesis_and_starts_without_pointer() -> None:
    spec = ExperimentSpec(
        id=ExperimentSpecId(uuid4()),
        project_id=ProjectId(uuid4()),
        hypothesis_id=None,
        created_by=ActorId(uuid4()),
        created_at=FIXED_TIME,
    )
    assert spec.current_version_id is None
    assert spec.row_version == 1


@pytest.mark.parametrize("value", ["", "   "])
def test_title_and_objective_must_not_be_blank(value: str) -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        _version(title=value)
    with pytest.raises(ValueError, match="must not be blank"):
        _version(objective=value)


@pytest.mark.parametrize("protocol", [None, {}, [], "", "   "])
def test_protocol_must_be_non_empty(protocol: object) -> None:
    with pytest.raises(ValueError, match="protocol must not be empty"):
        _version(protocol=protocol)


def test_material_payload_is_explicit_and_excludes_identity_and_metadata() -> None:
    version = _version()
    assert version.material_payload() == {
        "title": "Treatment experiment",
        "objective": "Measure treatment effect",
        "protocol": {"arms": ["control", "treatment"]},
        "planned_metrics": [{"name": "outcome"}],
        "seed_policy": {"kind": "fixed"},
        "analysis_plan": {"test": "difference-in-means"},
    }
    for excluded in {
        "id",
        "experiment_spec_id",
        "version_number",
        "status",
        "content_hash",
        "created_by",
        "created_at",
        "frozen_at",
        "row_version",
        "hypothesis_id",
        "current_version_id",
    }:
        assert excluded not in version.material_payload()


def test_freeze_reuses_pr03_semantics_and_hashes_only_material() -> None:
    frozen = _version().freeze(FixedClock(FIXED_TIME))
    assert frozen.status is VersionStatus.FROZEN
    assert frozen.content_hash is not None
    assert frozen.hash_scheme == "sha256-cjson-v1"
    assert frozen.frozen_at == FIXED_TIME

    with pytest.raises(ResearchBaseError) as raised:
        frozen.edit_material(
            title="Changed",
            objective=frozen.objective,
            protocol=frozen.protocol,
            planned_metrics=frozen.planned_metrics,
            seed_policy=frozen.seed_policy,
            analysis_plan=frozen.analysis_plan,
        )
    assert raised.value.code is ErrorCode.IMMUTABLE_RECORD


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", "A different title"),
        ("objective", "A different objective"),
        ("protocol", {"arms": ["control", "treatment"], "blinded": True}),
        ("planned_metrics", [{"name": "another-outcome"}]),
        ("seed_policy", {"kind": "random", "seed": 42}),
        ("analysis_plan", {"test": "mann-whitney"}),
    ],
)
def test_each_material_field_changes_the_frozen_hash(field: str, value: object) -> None:
    baseline = _version().freeze(FixedClock(FIXED_TIME))
    changed = _version(**{field: value}).freeze(FixedClock(FIXED_TIME))
    assert baseline.content_hash != changed.content_hash


def test_excluded_metadata_and_identity_hypothesis_link_do_not_change_hash() -> None:
    baseline = _version().freeze(FixedClock(FIXED_TIME))
    metadata_variant = replace(
        _version(),
        id=ExperimentSpecVersionId(uuid4()),
        experiment_spec_id=ExperimentSpecId(uuid4()),
        version_number=9,
        created_by=ActorId(uuid4()),
        created_at=datetime(2026, 8, 28, 4, 0, tzinfo=UTC),
        row_version=4,
    ).freeze(FixedClock(FIXED_TIME))
    assert baseline.content_hash == metadata_variant.content_hash

    first_identity = ExperimentSpec(
        id=ExperimentSpecId(uuid4()),
        project_id=ProjectId(uuid4()),
        hypothesis_id=HypothesisId(uuid4()),
        created_by=ActorId(uuid4()),
        created_at=FIXED_TIME,
    )
    second_identity = replace(first_identity, id=ExperimentSpecId(uuid4()), hypothesis_id=None)
    assert first_identity.hypothesis_id != second_identity.hypothesis_id
    assert (
        _version(experiment_spec_id=first_identity.id).freeze(FixedClock(FIXED_TIME)).content_hash
        == _version(experiment_spec_id=second_identity.id)
        .freeze(FixedClock(FIXED_TIME))
        .content_hash
    )


def test_status_is_excluded_from_material_hash() -> None:
    draft = _version()
    frozen = draft.freeze(FixedClock(FIXED_TIME))
    superseded = frozen.transition_to(VersionStatus.SUPERSEDED)

    assert draft.freeze(FixedClock(FIXED_TIME)).content_hash == frozen.content_hash
    assert superseded.content_hash == frozen.content_hash


def test_frozen_at_is_excluded_from_material_hash() -> None:
    first = _version().freeze(FixedClock(FIXED_TIME))
    second = _version().freeze(FixedClock(datetime(2026, 8, 27, 5, 0, tzinfo=UTC)))

    assert first.frozen_at != second.frozen_at
    assert first.content_hash == second.content_hash


def test_identity_current_pointer_is_excluded_from_material_hash() -> None:
    parent_id = ExperimentSpecId(uuid4())
    first_version = _version(experiment_spec_id=parent_id, version_number=1)
    second_version = _version(experiment_spec_id=parent_id, version_number=2)
    first_identity = ExperimentSpec(
        id=ExperimentSpecId(uuid4()),
        project_id=ProjectId(uuid4()),
        hypothesis_id=None,
        created_by=ActorId(uuid4()),
        created_at=FIXED_TIME,
        current_version_id=first_version.id,
    )
    second_identity = replace(
        first_identity,
        id=ExperimentSpecId(uuid4()),
        current_version_id=second_version.id,
    )
    first_hash = first_version.freeze(FixedClock(FIXED_TIME)).content_hash
    second_hash = second_version.freeze(FixedClock(FIXED_TIME)).content_hash

    assert first_identity.current_version_id != second_identity.current_version_id
    assert first_hash == second_hash


class ExperimentSpecVersionContractAdapter:
    def __init__(self, material: object) -> None:
        mapping = cast(dict[str, object], material)
        self.version = _version(
            title=str(mapping["title"]),
            objective="Objective",
            protocol={"steps": ["run"]},
            planned_metrics=None,
            seed_policy=None,
            analysis_plan=None,
        )
        self.non_material_metadata = {"id": uuid4(), "created_at": FIXED_TIME.isoformat()}

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
        mapping = cast(dict[str, object], material)
        self.version = self.version.edit_material(
            title=str(mapping["title"]),
            objective=self.version.objective,
            protocol=self.version.protocol,
            planned_metrics=self.version.planned_metrics,
            seed_policy=self.version.seed_policy,
            analysis_plan=self.version.analysis_plan,
        )

    def freeze(self, clock: Clock) -> None:
        self.version = self.version.freeze(clock)

    def transition_to(self, target: VersionStatus) -> None:
        self.version = self.version.transition_to(target)


def test_experiment_version_passes_reusable_pr03_contract() -> None:
    assert_version_contract(
        cast(Callable[[object], VersionFixture], ExperimentSpecVersionContractAdapter)
    )
