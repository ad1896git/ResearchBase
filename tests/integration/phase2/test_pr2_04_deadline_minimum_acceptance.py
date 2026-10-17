"""Execution budget, rather than call timeout, is the binding reservation deadline."""

from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from researchbase.application.literature_search_execution import (
    CreateLiteratureSearchExecution,
    ExecuteLiteratureSearchExecution,
)
from researchbase.application.literature_search_provider import FakeSearchCapability
from researchbase.persistence.literature_search_execution_uow import (
    literature_search_execution_uow_factory,
)
from tests.integration.phase2.test_pr2_03_literature_search_plan_application import (
    _AlwaysValidCredential,
)
from tests.integration.phase2.test_pr2_03_review_guards import _freeze, _setup
from tests.integration.phase2.test_pr2_04_execution_recovery import ReservedBeforeInvocation
from tests.integration.phase2.test_pr2_04_schema_coverage import A, E, V, _insert, _reject, _rows


def setup_budget_min(url):
    engine, plans, principal, project, plan, version = _setup(url)
    _freeze(engine, plans, principal, project, plan, version)
    provider = FakeSearchCapability(capability_id="provider-a")
    service = ReservedBeforeInvocation(
        literature_search_execution_uow_factory(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        ),
        provider,
        credential_verifier=_AlwaysValidCredential(),
    )
    create = CreateLiteratureSearchExecution(
        project,
        version,
        principal.actor_id,
        principal.deployment_id,
        uuid4(),
        "provider-a",
        "1",
        ("normalization evidence",),
        timeout_seconds=30,
        execution_budget_seconds=2,
        principal=principal,
    )
    admission = service.create(create)
    execution_id = UUID(admission["execution_id"])
    return engine, principal, project, provider, service, execution_id


@pytest.mark.pr204_requirements("PR204-DB-05", "PR204-DB-01")
def test_pg_application_reservation_uses_execution_budget_minimum(phase2_database_url, pr204_trace):
    engine, principal, project, provider, service, execution_id = setup_budget_min(
        phase2_database_url
    )
    try:
        service.execute(
            ExecuteLiteratureSearchExecution(
                execution_id,
                principal.actor_id,
                principal.deployment_id,
                uuid4(),
                project_id=project,
                principal=principal,
            )
        )
        rows = _rows(engine)
        execution = next(row for row in rows[E] if row["id"] == execution_id)
        attempt = next(row for row in rows[A] if row["execution_id"] == execution_id)
        assert attempt["deadline_at"] == execution["started_at"] + timedelta(seconds=2)
        assert attempt["deadline_at"] < attempt["reserved_at"] + timedelta(seconds=30)
        assert attempt["recovery_after"] == attempt["deadline_at"] + timedelta(seconds=30)
        assert provider.calls == []
        pr204_trace.record(execution=execution, attempt=attempt, provider_calls=0)
    finally:
        engine.dispose()


@pytest.mark.pr204_requirements("PR204-DB-05", "PR204-DB-01")
def test_pg_direct_reservation_cannot_exceed_execution_budget_minimum(
    phase2_database_url, pr204_trace
):
    engine, principal, _, provider, _, execution_id = setup_budget_min(phase2_database_url)

    def reserve(connection, seconds):
        at = connection.scalar(text("SELECT clock_timestamp()"))
        attempt_id = uuid4()
        connection.execute(
            text(
                f"UPDATE {E} SET status='RUNNING',started_at=:at,executed_by=:actor,"
                "row_version=2 WHERE id=:id"
            ),
            {"at": at, "actor": principal.actor_id, "id": execution_id},
        )
        _insert(
            connection,
            A,
            dict(
                id=attempt_id,
                execution_id=execution_id,
                query_index=0,
                attempt_number=1,
                provider_request_key=attempt_id,
                status="RESERVED",
                row_version=1,
                reserved_at=at,
                deadline_at=at + timedelta(seconds=seconds),
                recovery_after=at + timedelta(seconds=seconds + 30),
                created_at=at,
                created_by=principal.actor_id,
            ),
        )
        _insert(
            connection,
            V,
            dict(
                id=uuid4(),
                execution_id=execution_id,
                sequence=1,
                kind="ATTEMPT_RESERVED",
                attempt_id=attempt_id,
                prior_status="PLANNED",
                new_status="RUNNING",
                prior_row_version=1,
                new_row_version=2,
                occurred_at=at,
                created_at=at,
                created_by=principal.actor_id,
            ),
        )

    try:
        before = _rows(engine)
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                reserve(connection, 2)
                connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
            finally:
                transaction.rollback()
        assert _rows(engine) == before
        _reject(
            engine, lambda c: reserve(c, 30), "P17D5", pr204_trace, case="execution_budget_minimum"
        )
        assert provider.calls == []
    finally:
        engine.dispose()
