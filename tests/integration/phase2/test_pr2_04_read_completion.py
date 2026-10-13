"""Frozen pack §§12/17, PR204-API-02: tied cursors and live read credentials."""

from dataclasses import replace
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from researchbase.application.literature_search_execution import LiteratureSearchExecutionService
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.literature_search_execution_repository import (
    SqlAlchemyLiteratureSearchExecutionRepository,
)
from researchbase.persistence.literature_search_execution_uow import (
    literature_search_execution_uow_factory,
)
from tests.integration.phase2.test_pr2_04_idempotency_coverage import _execution_setup, _snapshot


@pytest.fixture
def read_case(phase2_database_url):
    yield from _execution_setup(phase2_database_url)


@pytest.mark.pr204_requirements("PR204-API-02")
def test_pg_equal_created_at_cursor_uses_uuid_tie_breaker_without_loss(
    read_case, monkeypatch, pr204_trace: FactRecorder
):
    engine, service, provider, principal, project, create = read_case
    with engine.connect() as connection:
        common_time = connection.execute(text("SELECT clock_timestamp()")).scalar_one()
    # Only creation metadata is tied; authorization retains its real fresh DB clock.
    monkeypatch.setattr(
        SqlAlchemyLiteratureSearchExecutionRepository, "_database_now", lambda self: common_time
    )
    admitted = [
        UUID(service.create(replace(create, request_id=uuid4()))["execution_id"]) for _ in range(4)
    ]
    before = _snapshot(engine, project)
    assert {r["created_at"] for r in before["executions"]} == {common_time}
    expected = sorted(admitted)
    collected = []
    after = None
    for expected_id in expected:
        page = service.list(principal, project, limit=1, after=after)
        assert len(page) == 1 and UUID(page[0]["execution_id"]) == expected_id
        collected.append(expected_id)
        after = expected_id
    assert service.list(principal, project, limit=1, after=after) == []
    assert collected == expected and len(set(collected)) == 4
    assert _snapshot(engine, project) == before and provider.calls == []
    pr204_trace.record(
        common_created_at=common_time,
        expected_order=expected,
        paginated_order=collected,
        page_size=1,
        missing_or_duplicate_ids=0,
        durable_rows_unchanged=True,
        provider_calls=0,
    )


@pytest.mark.pr204_requirements("PR204-API-02", "PR204-AUTH-01")
@pytest.mark.parametrize("read", ["get", "list", "get_provenance"])
def test_pg_each_read_rechecks_clock_expired_credential_without_authority_mutation(
    read_case, read, pr204_trace: FactRecorder
):
    engine, original, provider, principal, project, create = read_case
    execution_id = UUID(original.create(create)["execution_id"])

    class ExpiringCredential:
        expiry = None

        def __init__(self):
            self.observations = []

        def is_valid(self, candidate, at):
            assert candidate == principal
            self.observations.append(at)
            return self.expiry is None or at < self.expiry

    credential = ExpiringCredential()
    service = LiteratureSearchExecutionService(
        literature_search_execution_uow_factory(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        ),
        provider,
        credential_verifier=credential,
    )
    args = (principal, project) if read == "list" else (principal, project, execution_id)
    first = getattr(service, read)(*args)
    assert first is not None and len(credential.observations) == 1
    before = _snapshot(engine, project)
    credential.expiry = credential.observations[0] + timedelta(seconds=0.05)
    with engine.connect() as connection:
        connection.execute(text("SELECT pg_sleep(0.06)"))
    with pytest.raises(ResearchBaseError) as caught:
        getattr(service, read)(*args)
    assert caught.value.code is ErrorCode.FORBIDDEN
    assert len(credential.observations) == 2
    assert credential.observations[0] < credential.expiry <= credential.observations[1]
    assert _snapshot(engine, project) == before and provider.calls == []
    pr204_trace.record(
        read=read,
        credential_expiry=credential.expiry,
        fresh_database_times=credential.observations,
        error_code=caught.value.code.value,
        durable_rows_unchanged=True,
        provider_calls=0,
    )
