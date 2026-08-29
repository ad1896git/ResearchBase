from __future__ import annotations

from dataclasses import fields

from researchbase.application.commands import (
    RecordStatisticalResultCommand,
    StatisticalResultInputCommand,
)
from researchbase.application.dto import (
    StatisticalResultInputReadModel,
    StatisticalResultReadModel,
)
from researchbase.application.ports import StatisticalResultRepository, UnitOfWork
from researchbase.persistence.repositories import SqlAlchemyStatisticalResultRepository

DATACLASS_PARAMS = "__dataclass_params__"


def test_record_statistical_result_command_has_explicit_input_shape() -> None:
    assert [field.name for field in fields(RecordStatisticalResultCommand)] == [
        "project_id",
        "analysis_type",
        "result_payload",
        "analysis_definition",
        "inputs",
        "context",
    ]
    assert [field.name for field in fields(StatisticalResultInputCommand)] == [
        "measurement_id",
        "input_role",
        "ordinal",
    ]


def test_statistical_result_read_models_are_immutable_and_orm_free() -> None:
    assert all(field.name != "session" for field in fields(StatisticalResultReadModel))
    assert all(field.name != "session" for field in fields(StatisticalResultInputReadModel))
    assert getattr(StatisticalResultReadModel, DATACLASS_PARAMS).frozen is True
    assert getattr(StatisticalResultInputReadModel, DATACLASS_PARAMS).frozen is True


def test_statistical_result_repository_has_only_narrow_non_mutating_surface() -> None:
    required = {"add", "add_input", "get", "list_by_project", "list_inputs"}
    assert required <= {
        name for name in dir(StatisticalResultRepository) if not name.startswith("_")
    }
    assert not {
        "update",
        "delete",
        "save",
    } & {name for name in dir(StatisticalResultRepository) if not name.startswith("_")}
    assert not {"update", "delete", "save"} & {
        name for name in dir(SqlAlchemyStatisticalResultRepository) if not name.startswith("_")
    }
    assert "statistical_results" in UnitOfWork.__annotations__
