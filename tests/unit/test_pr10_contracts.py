from __future__ import annotations

from inspect import signature
from uuid import uuid4

from researchbase.application.commands import RecordMeasurementCommand
from researchbase.application.dto import MeasurementReadModel
from researchbase.application.ports import MeasurementRepository, UnitOfWork
from researchbase.domain.measurement import MeasurementId
from researchbase.domain.metric import MetricDefinitionVersionId
from researchbase.domain.run import RunId
from researchbase.foundation.execution_context import ExecutionContext


def test_record_measurement_command_has_the_frozen_input_shape() -> None:
    command = RecordMeasurementCommand(
        run_id=RunId(uuid4()),
        metric_definition_version_id=MetricDefinitionVersionId(uuid4()),
        numeric_value=1.0,
        structured_value=None,
        unit="m",
        evaluation_scope={"split": "test"},
        context=ExecutionContext(actor_id=uuid4(), request_id=uuid4(), client_type="test"),
    )

    assert command.numeric_value == 1.0
    assert command.structured_value is None


def test_measurement_read_model_exposes_only_immutable_record_fields() -> None:
    names = set(signature(MeasurementReadModel).parameters)
    assert names == {
        "id",
        "run_id",
        "metric_definition_version_id",
        "numeric_value",
        "structured_value",
        "unit",
        "evaluation_scope",
        "content_hash",
        "created_by",
        "created_at",
    }
    assert not hasattr(MeasurementRepository, "update")
    assert not hasattr(MeasurementRepository, "delete")
    assert "measurements" in UnitOfWork.__annotations__
    assert MeasurementId
