from dataclasses import is_dataclass
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

import pytest

from researchbase.application.commands import CreateProjectCommand
from researchbase.application.dto import ProjectReadModel
from researchbase.application.governance import (
    CreateAuditFindingCommand,
    ProposedImpactTarget,
)
from researchbase.application.governance_queries import DownstreamImpactPath
from researchbase.application.provenance_queries import RunInputDTO
from researchbase.domain.governance import GovernanceTargetType, ImpactKind
from researchbase.domain.organization import ProjectId
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext


def test_public_application_records_are_pydantic_dataclasses() -> None:
    for record in (
        CreateProjectCommand,
        ProjectReadModel,
        CreateAuditFindingCommand,
        ProposedImpactTarget,
        DownstreamImpactPath,
        RunInputDTO,
    ):
        assert is_dataclass(record)
        assert hasattr(record, "__pydantic_validator__")
        config = cast(Any, record).__pydantic_config__
        assert config["extra"] == "forbid"
        assert config["frozen"] is True
        assert config["from_attributes"] is False
        assert config["arbitrary_types_allowed"] is False
        assert config["use_enum_values"] is False


def test_public_command_preserves_positional_constructor_and_defaults() -> None:
    context = ExecutionContext(
        actor_id=uuid4(),
        request_id=uuid4(),
        client_type="test",
    )
    command = CreateProjectCommand("project", None, context)
    assert command.name == "project"
    assert command.description is None
    assert command.context is context


def test_public_dto_rejects_extra_fields_and_is_immutable() -> None:
    with pytest.raises(ResearchBaseError) as error:
        cast(Any, ProjectReadModel)(
            id=uuid4(),
            name="project",
            description=None,
            lifecycle_status="active",
            created_by=uuid4(),
            created_at=datetime(2026, 9, 14, tzinfo=UTC),
            row_version=1,
            unexpected="value",
        )

    assert error.value.code is ErrorCode.VALIDATION_ERROR

    model = cast(Any, ProjectReadModel)(
        uuid4(),
        "project",
        None,
        "active",
        ProjectId(uuid4()),
        datetime(2026, 9, 14, tzinfo=UTC),
        1,
    )
    with pytest.raises((ResearchBaseError, AttributeError, TypeError)):
        model.name = "changed"


def test_nested_governance_dto_preserves_enum_semantics() -> None:
    target = ProposedImpactTarget("run", uuid4(), "downstream")
    assert target.target_type == GovernanceTargetType.RUN.value
    assert target.impact_kind == ImpactKind.DOWNSTREAM.value
