from typing import cast
from uuid import uuid4

import pytest
from pydantic import ValidationError

from researchbase.foundation.execution_context import ClientType, ExecutionContext


@pytest.mark.parametrize("client_type", ["human_ui", "cli", "agent", "service", "test"])
def test_execution_context_accepts_allowed_client_types(client_type: str) -> None:
    context = ExecutionContext(
        actor_id=uuid4(),
        request_id=uuid4(),
        client_type=cast(ClientType, client_type),
    )

    assert context.client_type == client_type


def test_execution_context_requires_actor_and_request_ids() -> None:
    with pytest.raises(ValidationError):
        ExecutionContext.model_validate({"client_type": "test"})


def test_execution_context_validates_uuid_fields_and_rejects_unknown_client_type() -> None:
    with pytest.raises(ValidationError):
        ExecutionContext.model_validate(
            {"actor_id": "bad", "request_id": uuid4(), "client_type": "test"}
        )
    with pytest.raises(ValidationError):
        ExecutionContext.model_validate(
            {"actor_id": uuid4(), "request_id": uuid4(), "client_type": "browser"}
        )


def test_execution_context_is_caller_neutral_and_immutable() -> None:
    context = ExecutionContext(
        actor_id=uuid4(),
        request_id=uuid4(),
        correlation_id=uuid4(),
        client_type="agent",
        client_name="test-agent",
        client_version="1.0",
    )

    assert context.model_dump()["client_type"] == "agent"
    with pytest.raises(ValidationError):
        context.client_type = "cli"
