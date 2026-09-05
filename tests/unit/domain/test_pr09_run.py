from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

import pytest

from researchbase.domain.experiment import ExperimentSpecVersionId
from researchbase.domain.organization import ProjectId
from researchbase.domain.run import (
    ArtifactInputRole,
    DatasetInputRole,
    Run,
    RunArtifactInput,
    RunDatasetInput,
    RunId,
    RunStatus,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import ActorId
from researchbase.foundation.time import FixedClock

NOW = datetime(2026, 8, 28, 0, 0, tzinfo=UTC)


def make_run(**overrides: object) -> Run:
    values: dict[str, object] = {
        "id": RunId(uuid4()),
        "project_id": ProjectId(uuid4()),
        "experiment_spec_version_id": ExperimentSpecVersionId(uuid4()),
        "run_type": "experiment",
        "status": RunStatus.PLANNED,
        "created_by": ActorId(uuid4()),
        "created_at": NOW,
    }
    values.update(overrides)
    return Run(**cast(dict[str, Any], values))


def test_run_starts_and_seals_inputs() -> None:
    run = make_run()
    started = run.start(FixedClock(NOW))
    assert started.status is RunStatus.RUNNING
    assert started.inputs_sealed_at == NOW
    assert started.started_at == NOW
    assert started.row_version == run.row_version


def test_planned_run_cancel_seals_inputs_and_sets_finished_at() -> None:
    run = make_run()

    cancelled = run.cancel(FixedClock(NOW))

    assert cancelled.status is RunStatus.CANCELLED
    assert cancelled.inputs_sealed_at == NOW
    assert cancelled.started_at is None
    assert cancelled.finished_at == NOW
    assert cancelled.exit_code is None
    assert cancelled.failure_reason is None


@pytest.mark.parametrize("outcome", [RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED])
def test_run_finishes_only_from_running(outcome: RunStatus) -> None:
    finished = make_run().start(FixedClock(NOW)).finish(outcome, FixedClock(NOW))
    assert finished.status is outcome
    assert finished.finished_at == NOW


def test_run_transition_errors_are_stable() -> None:
    with pytest.raises(ResearchBaseError) as direct:
        make_run().finish(RunStatus.SUCCEEDED, FixedClock(NOW))
    assert direct.value.code is ErrorCode.INVALID_STATE_TRANSITION

    terminal = make_run().start(FixedClock(NOW)).finish(RunStatus.SUCCEEDED, FixedClock(NOW))
    with pytest.raises(ResearchBaseError) as restart:
        terminal.start(FixedClock(NOW))
    assert restart.value.code is ErrorCode.INVALID_STATE_TRANSITION


def test_run_input_roles_are_closed_and_ordinal_is_non_negative() -> None:
    run_id = RunId(uuid4())
    dataset = RunDatasetInput(run_id, cast(Any, uuid4()), DatasetInputRole.TRAIN)
    artifact = RunArtifactInput(run_id, cast(Any, uuid4()), ArtifactInputRole.SOURCE_CODE)
    assert dataset.role is DatasetInputRole.TRAIN
    assert artifact.role is ArtifactInputRole.SOURCE_CODE
    with pytest.raises(ValueError):
        RunDatasetInput(run_id, cast(Any, uuid4()), cast(Any, "unknown"))
    with pytest.raises(ValueError):
        RunArtifactInput(run_id, cast(Any, uuid4()), ArtifactInputRole.MODEL, ordinal=-1)
