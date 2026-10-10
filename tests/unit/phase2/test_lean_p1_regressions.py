"""Focused F2 P1 regression counterexamples."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from researchbase.application.literature_search_execution import (
    CreateLiteratureSearchExecution,
    ExecuteLiteratureSearchExecution,
    LiteratureSearchExecutionService,
)
from researchbase.application.literature_search_provider import FakeSearchCapability
from researchbase.persistence.in_memory_literature_search_execution import (
    InMemoryExecutionUnitOfWork,
    InMemoryLiteratureSearchExecutionRepository,
)
from researchbase.persistence.literature_search_execution_repository import (
    SqlAlchemyLiteratureSearchExecutionRepository,
)


def test_c01_attempt_projection_preserves_retrieval_observation():
    retrieved = datetime(2026, 1, 1, tzinfo=UTC)
    row = SimpleNamespace(
        **dict.fromkeys(
            [
                "id",
                "execution_id",
                "query_index",
                "attempt_number",
                "provider_request_key",
                "status",
                "failure_code",
                "reserved_at",
                "deadline_at",
                "recovery_after",
                "invoked_at",
                "returned_at",
                "completed_at",
                "query_record_id",
                "delivery_certainty",
                "provider_request_id",
                "retry_after_seconds",
                "warning_codes",
                "result_count",
                "row_version",
            ]
        ),
        retrieved_at=retrieved,
    )
    session = SimpleNamespace(scalars=lambda _: SimpleNamespace(all=lambda: [row]))
    repository = SqlAlchemyLiteratureSearchExecutionRepository(session)
    assert repository.attempts(uuid4())[0].get("retrieved_at") == retrieved


@pytest.mark.parametrize("boundary", ["commit", "exit"])
@pytest.mark.parametrize("elapsed", [0.25, 2.0])
def test_c02_preparation_latency_reduces_dispatch_budget(boundary, elapsed):
    now = datetime(2026, 1, 1, tzinfo=UTC)
    seconds = 0.0
    commits = 0
    active = False

    class Repository(InMemoryLiteratureSearchExecutionRepository):
        def database_now(self):
            return now + timedelta(seconds=seconds)

    repository = Repository()

    class Uow(InMemoryExecutionUnitOfWork):
        def __enter__(self):
            nonlocal active
            active = True
            return super().__enter__()

        def commit(self):
            nonlocal seconds, commits
            super().commit()
            commits += 1
            if boundary == "commit" and commits == 3:
                seconds += elapsed

        def __exit__(self, *args):
            nonlocal seconds, active
            super().__exit__(*args)
            if boundary == "exit" and commits == 3:
                seconds += elapsed
            active = False

    observed = []

    class Provider(FakeSearchCapability):
        def search(self, request, context=None):
            assert not active
            assert context is not None
            observed.append((seconds, context.remaining_timeout_seconds))
            return super().search(request, context)

    provider = Provider()
    service = LiteratureSearchExecutionService(
        lambda: Uow(repository),
        provider,
        clock=lambda: repository.database_now(),
        monotonic=lambda: seconds,
        allow_unverified_principal=True,
    )
    actor, project = uuid4(), uuid4()
    created = service.create(
        CreateLiteratureSearchExecution(
            project,
            uuid4(),
            actor,
            "test",
            uuid4(),
            "fake",
            "1",
            ("cortex",),
            timeout_seconds=1,
            execution_budget_seconds=2,
        )
    )
    service.execute(
        ExecuteLiteratureSearchExecution(
            UUID(created["execution_id"]),
            actor,
            "test",
            uuid4(),
        )
    )
    if elapsed >= 1:
        assert observed == []
        assert provider.calls == []
    else:
        assert observed == [(elapsed, pytest.approx(1 - elapsed))]
