"""Real PostgreSQL counterexamples for C03/C04/C05; no acceptance certification."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError

from tests.integration.phase2.test_pr2_04_execution_migration import _upgrade
from tests.integration.phase2.test_pr2_04_idempotency_coverage import _command, _execution_setup
from tests.integration.phase2.test_pr2_04_schema_coverage import (
    A,
    E,
    Q,
    V,
    _insert,
    _material,
    _rows,
)


@pytest.mark.parametrize("cancel", [False, True])
def test_c03_initial_and_prestart_cancel_attribution(phase2_database_url, cancel):
    case = _execution_setup(phase2_database_url)
    engine, service, provider, principal, project, create = next(case)
    try:
        execution = UUID(service.create(create)["execution_id"])
        if cancel:
            service.cancel(_command("cancel", principal, project, execution))
        with engine.connect() as connection:
            actor = connection.execute(
                text(f"SELECT executed_by FROM {E} WHERE id=:id"), {"id": execution}
            ).scalar_one()
        assert actor == principal.actor_id
        assert (
            next(c for c in inspect(engine).get_columns(E) if c["name"] == "executed_by")[
                "nullable"
            ]
            is False
        )
        assert provider.calls == []
    finally:
        case.close()


def test_c04_event_only_cancellation_cannot_reuse_version(phase2_database_url):
    value = _material(phase2_database_url, "reserved")
    engine = value["engine"]
    try:
        before = _rows(engine)
        execution = before[E][0]
        with pytest.raises(DBAPIError):
            with engine.begin() as connection:
                _insert(
                    connection,
                    V,
                    dict(
                        id=uuid4(),
                        execution_id=value["execution"],
                        sequence=2,
                        kind="CANCEL_REQUESTED",
                        attempt_id=None,
                        prior_status="RUNNING",
                        new_status="RUNNING",
                        prior_row_version=execution["row_version"] - 1,
                        new_row_version=execution["row_version"],
                        occurred_at=execution["started_at"],
                        created_at=execution["started_at"],
                        created_by=value["principal"].actor_id,
                    ),
                )
        assert _rows(engine) == before
    finally:
        engine.dispose()


@pytest.mark.parametrize("hits", [0, 2])
def test_c05_sealed_attempt_rejects_second_query(phase2_database_url, hits):
    value = _material(phase2_database_url, "sealed", hits)
    engine = value["engine"]
    try:
        before = _rows(engine)
        extra = dict(before[Q][0], id=uuid4(), ordinal=1, query_hash="f" * 64)
        with pytest.raises(DBAPIError):
            with engine.begin() as connection:
                _insert(connection, Q, extra)
        assert _rows(engine) == before
    finally:
        engine.dispose()


@pytest.mark.parametrize("state", ["planned", "cancelled", "running", "ambiguous", "non_null"])
def test_c03_historical_backfill_is_evidence_bound_and_atomic(phase2_database_url, state):
    from sqlalchemy.orm import sessionmaker

    from researchbase.application.literature_search_execution import CreateLiteratureSearchExecution
    from researchbase.application.literature_search_provider import FakeSearchCapability
    from researchbase.persistence.literature_search_execution_uow import (
        literature_search_execution_uow_factory,
    )
    from tests.integration.phase2.test_pr2_03_literature_search_plan_application import (
        _AlwaysValidCredential,
    )
    from tests.integration.phase2.test_pr2_03_review_guards import _freeze, _setup
    from tests.integration.phase2.test_pr2_04_execution_recovery import ReservedBeforeInvocation

    engine, plans, principal, project, plan, version = _setup(
        phase2_database_url, migration_revision="0025_pr2_04_reservation_guards"
    )
    try:
        _freeze(engine, plans, principal, project, plan, version)
        service = ReservedBeforeInvocation(
            literature_search_execution_uow_factory(
                sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
            ),
            FakeSearchCapability(capability_id="provider-a"),
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
            principal=principal,
        )
        execution = UUID(service.create(create)["execution_id"])
        if state != "non_null":
            # Simulate original 0025 NULL initialization, without changing its migration.
            with engine.begin() as connection:
                connection.execute(
                    text(f"ALTER TABLE {E} DISABLE TRIGGER trg_pr204_execution_update_guard")
                )
                connection.execute(
                    text(f"ALTER TABLE {E} DISABLE TRIGGER trg_pr204_execution_event_commit")
                )
                connection.execute(
                    text(f"UPDATE {E} SET executed_by=NULL WHERE id=:id"), {"id": execution}
                )
                connection.execute(
                    text(f"ALTER TABLE {E} ENABLE TRIGGER trg_pr204_execution_event_commit")
                )
                connection.execute(
                    text(f"ALTER TABLE {E} ENABLE TRIGGER trg_pr204_execution_update_guard")
                )
        if state == "cancelled":
            service.cancel(_command("cancel", principal, project, execution))
        elif state == "running":
            service.execute(_command("execute", principal, project, execution))
            # Deliberately damaged historical attribution; unique start evidence remains.
            with engine.begin() as connection:
                connection.execute(
                    text(f"ALTER TABLE {E} DISABLE TRIGGER trg_pr204_execution_update_guard")
                )
                connection.execute(
                    text(f"ALTER TABLE {E} DISABLE TRIGGER trg_pr204_execution_event_commit")
                )
                connection.execute(
                    text(f"UPDATE {E} SET executed_by=NULL WHERE id=:id"), {"id": execution}
                )
                connection.execute(
                    text(f"ALTER TABLE {E} ENABLE TRIGGER trg_pr204_execution_event_commit")
                )
                connection.execute(
                    text(f"ALTER TABLE {E} ENABLE TRIGGER trg_pr204_execution_update_guard")
                )
        elif state == "ambiguous":
            # A direct SQL legacy creation can lack a receipt. Missing evidence must block.
            with engine.begin() as connection:
                table = "literature_search_execution_command_receipts"
                connection.execute(
                    text(f"ALTER TABLE {table} DISABLE TRIGGER trg_pr204_receipt_immutable")
                )
                connection.execute(
                    text(f"DELETE FROM {table} WHERE result_execution_id=:id"), {"id": execution}
                )
                connection.execute(
                    text(f"ALTER TABLE {table} ENABLE TRIGGER trg_pr204_receipt_immutable")
                )
        before = _rows(engine)
        if state == "ambiguous":
            with pytest.raises(DBAPIError, match="ambiguous historical creation attribution"):
                _upgrade(phase2_database_url, "head")
            assert _rows(engine) == before
            with engine.connect() as connection:
                assert (
                    connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                    == "0025_pr2_04_reservation_guards"
                )
            assert next(c for c in inspect(engine).get_columns(E) if c["name"] == "executed_by")[
                "nullable"
            ]
        else:
            _upgrade(phase2_database_url, "head")
            after = _rows(engine)
            expected = dict(before[E][0], executed_by=principal.actor_id)
            assert after[E] == [expected]
            assert all(after[table] == before[table] for table in before if table != E)
            with pytest.raises(DBAPIError, match="downgrade requires empty execution history"):
                from alembic import command

                from tests.integration.phase2.test_pr2_04_execution_migration import _alembic

                command.downgrade(_alembic(phase2_database_url), "0025_pr2_04_reservation_guards")
            assert _rows(engine) == after
    finally:
        engine.dispose()


def test_c03_empty_upgrade_downgrade_roundtrip(phase2_database_url):
    from alembic import command
    from sqlalchemy import create_engine

    from tests.integration.phase2.test_pr2_04_execution_migration import _alembic

    _upgrade(phase2_database_url, "head")
    command.downgrade(_alembic(phase2_database_url), "0025_pr2_04_reservation_guards")
    _upgrade(phase2_database_url, "head")
    engine = create_engine(phase2_database_url)
    try:
        assert (
            next(c for c in inspect(engine).get_columns(E) if c["name"] == "executed_by")[
                "nullable"
            ]
            is False
        )
    finally:
        engine.dispose()


def test_c03_first_authorized_executor_replaces_requester_once(phase2_database_url):
    from researchbase.application.phase2_identity import AssignProjectRole
    from tests.integration.phase2.test_pr2_00_challenges import _service as identity_service
    from tests.integration.phase2.test_pr2_03_effective_authority import _provision
    from tests.integration.phase2.test_pr2_04_execution_recovery import ReservedBeforeInvocation
    from tests.integration.phase2.test_pr2_04_idempotency_coverage import _service

    case = _execution_setup(phase2_database_url)
    engine, service, provider, owner, project, create = next(case)
    try:
        identity, _, _ = identity_service(phase2_database_url)
        executor, _ = _provision(identity, owner)
        identity.assign_project_role(
            AssignProjectRole(
                owner, project, executor.actor_id, "RESEARCHER", "first executor", uuid4()
            )
        )
        execution = UUID(service.create(create)["execution_id"])
        paused = _service(engine, provider, ReservedBeforeInvocation)
        paused.execute(_command("execute", executor, project, execution))
        before = _rows(engine)
        assert before[E][0]["requested_by"] == owner.actor_id
        assert before[E][0]["executed_by"] == executor.actor_id != owner.actor_id
        assert before[A][0]["created_by"] == executor.actor_id
        with pytest.raises(DBAPIError) as caught:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        f"UPDATE {E} SET executed_by=:owner,row_version=row_version+1 WHERE id=:id"
                    ),
                    dict(owner=owner.actor_id, id=execution),
                )
        assert getattr(caught.value.orig, "sqlstate", None) == "P17D1"
        assert _rows(engine) == before and provider.calls == []
        # Initial SQL attribution cannot impersonate another existing actor either.
        wrong = dict(
            before[E][0],
            id=uuid4(),
            idempotency_key=uuid4(),
            status="PLANNED",
            row_version=1,
            started_at=None,
        )
        with pytest.raises(DBAPIError) as caught:
            with engine.begin() as connection:
                _insert(connection, E, wrong)
        assert getattr(caught.value.orig, "sqlstate", None) == "P17D5"
        assert _rows(engine) == before
    finally:
        case.close()


def test_c05_query_without_atomic_attempt_seal_is_rejected(phase2_database_url):
    value = _material(phase2_database_url, "reserved")
    engine = value["engine"]
    try:
        before = _rows(engine)
        attempt = before[A][0]
        with pytest.raises(DBAPIError) as caught:
            with engine.begin() as connection:
                _insert(
                    connection,
                    Q,
                    dict(
                        id=uuid4(),
                        literature_search_execution_id=value["execution"],
                        provider_attempt_id=attempt["id"],
                        ordinal=0,
                        query_text="normalization evidence",
                        perspective=None,
                        provider_id="provider-a",
                        provider_version="1",
                        executed_at=attempt["reserved_at"],
                        query_hash="f" * 64,
                        hash_scheme="sha256-cjson-v1",
                        created_by=value["principal"].actor_id,
                        created_at=attempt["reserved_at"],
                    ),
                )
        assert getattr(caught.value.orig, "sqlstate", None) == "P17D5"
        assert _rows(engine) == before
    finally:
        engine.dispose()
