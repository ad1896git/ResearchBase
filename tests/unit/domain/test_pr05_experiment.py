from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

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
from researchbase.foundation.hashing import sha256_canonical_json
from researchbase.foundation.ids import ActorId
from researchbase.foundation.time import Clock, FixedClock
from researchbase.foundation.versioning import VersionStatus

FIXED_TIME = datetime(2026, 8, 27, 4, 0, tzinfo=UTC)
BASE_FROZEN_AT = datetime(2026, 8, 27, 5, 0, tzinfo=UTC)

BASE_VERSION_ID = ExperimentSpecVersionId(UUID("11111111-1111-7111-8111-111111111111"))
BASE_EXPERIMENT_SPEC_ID = ExperimentSpecId(UUID("22222222-2222-7222-8222-222222222222"))
BASE_ACTOR_ID = ActorId(UUID("33333333-3333-7333-8333-333333333333"))
BASE_PROJECT_ID = ProjectId(UUID("44444444-4444-7444-8444-444444444444"))
BASE_HYPOTHESIS_ID = HypothesisId(UUID("55555555-5555-7555-8555-555555555555"))
OTHER_VERSION_ID = ExperimentSpecVersionId(UUID("66666666-6666-7666-8666-666666666666"))
OTHER_HYPOTHESIS_ID = HypothesisId(UUID("77777777-7777-7777-8777-777777777777"))

MATERIAL_FIELDS = (
    "title",
    "objective",
    "protocol",
    "planned_metrics",
    "seed_policy",
    "analysis_plan",
)
EXCLUDED_VERSION_FIELDS = (
    "id",
    "experiment_spec_id",
    "version_number",
    "status",
    "created_by",
    "created_at",
    "frozen_at",
    "row_version",
)


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


def _deterministic_version() -> ExperimentSpecVersion:
    return ExperimentSpecVersion(
        id=BASE_VERSION_ID,
        experiment_spec_id=BASE_EXPERIMENT_SPEC_ID,
        version_number=1,
        status=VersionStatus.DRAFT,
        title="Treatment experiment",
        objective="Measure treatment effect",
        protocol={"arms": ["control", "treatment"]},
        planned_metrics=[{"name": "outcome"}],
        seed_policy={"kind": "fixed"},
        analysis_plan={"test": "difference-in-means"},
        created_by=BASE_ACTOR_ID,
        created_at=FIXED_TIME,
    )


@pytest.fixture
def baseline_version() -> ExperimentSpecVersion:
    return _deterministic_version()


@pytest.fixture
def frozen_baseline_version(baseline_version: ExperimentSpecVersion) -> ExperimentSpecVersion:
    return baseline_version.freeze(FixedClock(BASE_FROZEN_AT))


@pytest.fixture
def baseline_identity() -> ExperimentSpec:
    return ExperimentSpec(
        id=BASE_EXPERIMENT_SPEC_ID,
        project_id=BASE_PROJECT_ID,
        hypothesis_id=BASE_HYPOTHESIS_ID,
        created_by=BASE_ACTOR_ID,
        created_at=FIXED_TIME,
        current_version_id=BASE_VERSION_ID,
    )


def _material_hash(version: ExperimentSpecVersion) -> str:
    return sha256_canonical_json(version.material_payload())


def _identity_material_hash(identity: ExperimentSpec, version: ExperimentSpecVersion) -> str:
    assert identity.id == version.experiment_spec_id
    return _material_hash(version)


def _changed_fields(left: object, right: object, fields: tuple[str, ...]) -> set[str]:
    return {field for field in fields if getattr(left, field) != getattr(right, field)}


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


def test_material_payload_is_explicit_and_excludes_identity_and_metadata(
    baseline_version: ExperimentSpecVersion,
) -> None:
    version = baseline_version
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
def test_each_material_field_changes_the_frozen_hash(
    baseline_version: ExperimentSpecVersion, field: str, value: object
) -> None:
    baseline = baseline_version
    changed = replace(baseline, **{field: value})
    assert _changed_fields(baseline, changed, MATERIAL_FIELDS + EXCLUDED_VERSION_FIELDS) == {field}
    assert {
        name
        for name in MATERIAL_FIELDS
        if baseline.material_payload()[name] != changed.material_payload()[name]
    } == {field}
    baseline = baseline.freeze(FixedClock(BASE_FROZEN_AT))
    changed = changed.freeze(FixedClock(BASE_FROZEN_AT))
    assert baseline.content_hash != changed.content_hash


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", OTHER_VERSION_ID),
        ("experiment_spec_id", ExperimentSpecId(UUID("88888888-8888-7888-8888-888888888888"))),
        ("version_number", 2),
        ("status", VersionStatus.SUPERSEDED),
        ("created_by", ActorId(UUID("99999999-9999-7999-8999-999999999999"))),
        ("created_at", datetime(2026, 8, 28, 4, 0, tzinfo=UTC)),
        ("frozen_at", datetime(2026, 8, 27, 6, 0, tzinfo=UTC)),
        ("row_version", 2),
    ],
)
def test_each_excluded_version_field_preserves_material_hash(
    frozen_baseline_version: ExperimentSpecVersion, field: str, value: object
) -> None:
    changed = replace(frozen_baseline_version, **{field: value})
    assert _changed_fields(frozen_baseline_version, changed, EXCLUDED_VERSION_FIELDS) == {field}
    assert frozen_baseline_version.material_payload() == changed.material_payload()
    assert _material_hash(frozen_baseline_version) == _material_hash(changed)


def test_status_is_excluded_from_material_hash(
    frozen_baseline_version: ExperimentSpecVersion,
) -> None:
    baseline = frozen_baseline_version
    changed = replace(baseline, status=VersionStatus.SUPERSEDED)
    assert _changed_fields(baseline, changed, EXCLUDED_VERSION_FIELDS) == {"status"}
    assert baseline.material_payload() == changed.material_payload()
    assert _material_hash(baseline) == _material_hash(changed)


def test_frozen_at_is_excluded_from_material_hash(
    frozen_baseline_version: ExperimentSpecVersion,
) -> None:
    baseline = frozen_baseline_version
    changed = replace(baseline, frozen_at=datetime(2026, 8, 27, 6, 0, tzinfo=UTC))
    assert _changed_fields(baseline, changed, EXCLUDED_VERSION_FIELDS) == {"frozen_at"}
    assert baseline.material_payload() == changed.material_payload()
    assert _material_hash(baseline) == _material_hash(changed)


def test_identity_current_pointer_is_excluded_from_material_hash(
    baseline_identity: ExperimentSpec, baseline_version: ExperimentSpecVersion
) -> None:
    changed_identity = replace(baseline_identity, current_version_id=OTHER_VERSION_ID)
    assert _changed_fields(
        baseline_identity,
        changed_identity,
        (
            "id",
            "project_id",
            "hypothesis_id",
            "created_by",
            "created_at",
            "current_version_id",
            "row_version",
        ),
    ) == {"current_version_id"}
    assert baseline_identity.current_version_id != changed_identity.current_version_id
    assert _identity_material_hash(baseline_identity, baseline_version) == _identity_material_hash(
        changed_identity, baseline_version
    )


def test_identity_hypothesis_link_is_excluded_from_material_hash(
    baseline_identity: ExperimentSpec, baseline_version: ExperimentSpecVersion
) -> None:
    changed_identity = replace(baseline_identity, hypothesis_id=OTHER_HYPOTHESIS_ID)
    assert _changed_fields(
        baseline_identity,
        changed_identity,
        (
            "id",
            "project_id",
            "hypothesis_id",
            "created_by",
            "created_at",
            "current_version_id",
            "row_version",
        ),
    ) == {"hypothesis_id"}
    assert baseline_identity.hypothesis_id != changed_identity.hypothesis_id
    assert _identity_material_hash(baseline_identity, baseline_version) == _identity_material_hash(
        changed_identity, baseline_version
    )


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
