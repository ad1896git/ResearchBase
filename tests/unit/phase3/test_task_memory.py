"""Public memory requests fail before opening a transaction when malformed."""

from typing import Any, cast

import pytest

from researchbase.agent_runtime.application.task_memory import TaskMemoryService
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


@pytest.mark.parametrize("optional", [False, True])
def test_malformed_request_never_opens_uow(optional):
    def forbidden():
        raise AssertionError("unexpected UoW")

    service = TaskMemoryService(forbidden, object())
    method = (
        service.get_optional_task_working_memory if optional else service.get_task_working_memory
    )
    with pytest.raises(ResearchBaseError) as caught:
        method(cast(Any, object()), cast(Any, object()))
    assert caught.value.code == ErrorCode.VALIDATION_ERROR
