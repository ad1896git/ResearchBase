from __future__ import annotations

from collections.abc import Callable
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
