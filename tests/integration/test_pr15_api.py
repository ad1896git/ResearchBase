from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.engine import Engine
from tests.integration.test_pr14_governance_integration import _seed_graph

from researchbase.api.app import ServiceBundle, create_app
from researchbase.application.commands import ApplicationService
from researchbase.application.governance import GovernanceService
from researchbase.application.governance_queries import GovernanceQueryService
from researchbase.application.provenance_queries import ProvenanceQueryService
from researchbase.foundation.time import SystemClock
from researchbase.persistence.database import create_database_engine, create_session_factory
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def real_services() -> Iterator[tuple[ServiceBundle, Engine]]:
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set; run against PostgreSQL")
    engine = create_database_engine()
    sessions = create_session_factory(engine)

    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(sessions)

    clock = SystemClock()
    yield (
        ServiceBundle(
            ApplicationService(uow_factory, clock),
            ProvenanceQueryService(uow_factory),
            GovernanceService(uow_factory, clock),
            GovernanceQueryService(uow_factory),
        ),
        engine,
    )
    engine.dispose()


def test_real_postgresql_query_is_application_equivalent_read_only_and_sql_bounded(
    real_services: tuple[ServiceBundle, Engine],
) -> None:
    services, engine = real_services
    ids = _seed_graph(engine)
    statements: list[str] = []

    def capture(_conn: object, _cursor: object, statement: str, *_args: object) -> None:
        statements.append(statement.lstrip().split(None, 1)[0].upper())

    event.listen(engine, "before_cursor_execute", capture)
    try:
        direct = services.provenance.get_run_provenance(ids["run"])
        direct_count = len(statements)
        statements.clear()
        response = TestClient(create_app(services)).get(f"/v1/runs/{ids['run']}/provenance")
        http_count = len(statements)
    finally:
        event.remove(engine, "before_cursor_execute", capture)

    assert response.status_code == 200
    assert response.json()["run_id"] == direct.run_id
    assert response.json()["closure"]["complete"] == direct.closure.complete
    assert http_count == direct_count
    assert set(statements) <= {"SELECT"}


def test_real_postgresql_error_then_next_request_recovers(
    real_services: tuple[ServiceBundle, Engine],
) -> None:
    services, engine = real_services
    ids = _seed_graph(engine)
    client = TestClient(create_app(services))

    missing = client.get("/v1/runs/00000000-0000-0000-0000-000000000000/provenance")
    recovered = client.get(f"/v1/runs/{ids['run']}/provenance")

    assert missing.status_code == 404
    assert recovered.status_code == 200
    assert recovered.json()["run_id"] == str(ids["run"])
