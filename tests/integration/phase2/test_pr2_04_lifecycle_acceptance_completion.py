"""Actual PostgreSQL complements to the frozen complete lifecycle matrix."""

from uuid import UUID

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from researchbase.application.literature_search_provider import ProviderError, ProviderFailureKind
from researchbase.domain.literature_search_execution import DeliveryCertainty
from tests.integration.phase2.test_pr2_04_execution_recovery import ReservedBeforeInvocation
from tests.integration.phase2.test_pr2_04_idempotency_coverage import (
    _command,
    _execution_setup,
    _service,
    _snapshot,
)
from tests.unit.phase2.test_pr2_04_provider_coverage import ScriptedProvider, success


@pytest.fixture
def lifecycle_case(phase2_database_url):
    yield from _execution_setup(phase2_database_url)


@pytest.mark.parametrize("source", ["SUCCEEDED", "FAILED", "UNKNOWN"])
@pytest.mark.parametrize(
    "target", ["PLANNED", "RUNNING", "SUCCEEDED", "FAILED", "UNKNOWN", "CANCELLED"]
)
@pytest.mark.pr204_requirements("PR204-DOM-01", "PR204-DB-01")
def test_pg_every_remaining_terminal_source_rejects_every_target(
    lifecycle_case, source, target, pr204_trace: FactRecorder
):
    engine, _, _, principal, project, create = lifecycle_case
    response = {
        "SUCCEEDED": success("normalization evidence", "provider-a", hits=1),
        "FAILED": ProviderError(
            ProviderFailureKind.PERMANENT,
            "PROVIDER_PERMANENT",
            delivery_certainty=DeliveryCertainty.RESPONSE_RECEIVED,
        ),
        "UNKNOWN": ProviderError(
            ProviderFailureKind.UNCERTAIN,
            "PROVIDER_TIMEOUT",
            delivery_certainty=DeliveryCertainty.MAY_HAVE_BEEN_SENT,
        ),
    }[source]
    provider = ScriptedProvider([response], "provider-a")
    service = _service(engine, provider)
    execution = UUID(service.create(create)["execution_id"])
    service.execute(_command("execute", principal, project, execution))
    before = _snapshot(engine, project)
    assert before["executions"][0]["status"] == source
    assert len(provider.calls) == 1
    with pytest.raises(DBAPIError) as caught:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE literature_search_executions SET status=:status,row_version=row_version+1 WHERE id=:id"  # noqa: E501
                ),
                {"status": target, "id": execution},
            )
    assert caught.value.orig.sqlstate == "P17D1"
    assert _snapshot(engine, project) == before
    assert len(provider.calls) == 1
    pr204_trace.record(
        source=source,
        target=target,
        sqlstate=caught.value.orig.sqlstate,
        before=before,
        after=_snapshot(engine, project),
        provider_calls=1,
    )


@pytest.mark.pr204_requirements("PR204-DOM-01", "PR204-DB-01")
def test_pg_running_cannot_rewind_to_planned(lifecycle_case, pr204_trace: FactRecorder):
    engine, _, provider, principal, project, create = lifecycle_case
    service = _service(engine, provider, ReservedBeforeInvocation)
    execution = UUID(service.create(create)["execution_id"])
    service.execute(_command("execute", principal, project, execution))
    before = _snapshot(engine, project)
    assert before["executions"][0]["status"] == "RUNNING"
    assert len(before["attempts"]) == 1 and before["attempts"][0]["status"] == "RESERVED"
    with pytest.raises(DBAPIError) as caught:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE literature_search_executions SET status='PLANNED',row_version=row_version+1 WHERE id=:id"  # noqa: E501
                ),
                {"id": execution},
            )
    assert caught.value.orig.sqlstate == "P17D4"
    assert _snapshot(engine, project) == before and provider.calls == []
    pr204_trace.record(
        source="RUNNING",
        target="PLANNED",
        sqlstate=caught.value.orig.sqlstate,
        before=before,
        after=_snapshot(engine, project),
        provider_calls=0,
    )
