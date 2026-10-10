"""Approved provider-origin cancellation: bound evidence, SQL fences and replay."""

from dataclasses import replace
from uuid import UUID, uuid4

import pytest
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from researchbase.application.literature_search_execution import LiteratureSearchExecutionService
from researchbase.application.literature_search_provider import (
    FakeSearchCapability,
    ProviderError,
    ProviderFailureKind,
)
from researchbase.domain.literature_search_execution import DeliveryCertainty, SearchResponse
from researchbase.foundation.errors import ResearchBaseError
from tests.integration.phase2.test_pr2_03_literature_search_plan_application import (
    _AlwaysValidCredential,
)
from tests.integration.phase2.test_pr2_04_execution_migration import _alembic, _upgrade
from tests.integration.phase2.test_pr2_04_idempotency_coverage import (
    _command,
    _execution_setup,
    _snapshot,
)
from tests.unit.phase2.test_pr2_04_provider_coverage import success

PARENT = "0027_pr2_04_hash_scheme_guards"
REVISION = "0028_provider_cancellation"


def confirmation(request):
    return SearchResponse(
        request.provider_id,
        request.provider_version,
        request.query_text,
        "confirmed-remote",
        DeliveryCertainty.RESPONSE_RECEIVED,
        failure_code="PROVIDER_CANCELLED",
        execution_id=request.execution_id,
        attempt_id=request.attempt_id,
        provider_request_key=request.provider_request_key,
    )


class ConfirmingProvider(FakeSearchCapability):
    def __init__(self, variant="valid", earlier_hits=False):
        super().__init__(capability_id="provider-a")
        self.variant, self.earlier_hits = variant, earlier_hits

    def search(self, request, context=None):
        if self.observer:
            self.observer(request)
        self.calls.append(request)
        if self.earlier_hits and request.query_index == 0:
            return success(request.query_text, "provider-a", 2)
        if self.variant in {"disconnect", "timeout", "exception"}:
            raise ProviderError(
                ProviderFailureKind.CANCELLED
                if self.variant == "exception"
                else ProviderFailureKind.UNCERTAIN,
                "PROVIDER_TIMEOUT",
            )
        response = confirmation(request)
        changes = {
            "execution": {"execution_id": uuid4()},
            "attempt": {"attempt_id": uuid4()},
            "key": {"provider_request_key": uuid4()},
            "missing": {"attempt_id": None},
            "provider": {"provider_id": "foreign"},
            "version": {"provider_version": "other"},
            "unknown": {"delivery_certainty": DeliveryCertainty.MAY_HAVE_BEEN_SENT},
            "confirmed_not_sent": {"delivery_certainty": DeliveryCertainty.NOT_SENT},
            "request_id": {"provider_request_id": None},
            "query": {"normalized_query": "foreign query"},
        }
        return replace(response, **changes.get(self.variant, {}))


@pytest.fixture
def case(phase2_database_url):
    yield from _execution_setup(phase2_database_url)


@pytest.mark.parametrize(
    "variant,expected",
    [
        ("valid", "CANCELLED"),
        ("confirmed_not_sent", "CANCELLED"),
        ("request_id", "FAILED"),
        ("query", "FAILED"),
        ("missing", "FAILED"),
        ("execution", "FAILED"),
        ("attempt", "FAILED"),
        ("key", "FAILED"),
        ("provider", "FAILED"),
        ("version", "FAILED"),
        ("unknown", "UNKNOWN"),
        ("disconnect", "UNKNOWN"),
        ("timeout", "UNKNOWN"),
        ("exception", "UNKNOWN"),
    ],
)
def test_provider_confirmation_requires_exact_invocation(case, variant, expected):
    engine, healthy, _, principal, project, create = case
    provider = ConfirmingProvider(variant)
    service = LiteratureSearchExecutionService(
        healthy._uow_factory, provider, credential_verifier=_AlwaysValidCredential()
    )
    execution = UUID(service.create(create)["execution_id"])
    execute = _command("execute", principal, project, execution)
    admission = service.execute(execute)
    rows = _snapshot(engine, project)
    assert rows["executions"][0]["status"] == expected
    assert len(provider.calls) == 1
    assert not any(e["kind"] == "CANCEL_REQUESTED" for e in rows["events"])
    assert not any(
        r["command_name"] == "CANCEL_LITERATURE_SEARCH_EXECUTION" for r in rows["receipts"]
    )
    assert sum(e["kind"] == "OUTCOME_RECORDED" for e in rows["events"]) == 1
    assert sum(e["kind"] == "FINISHED" for e in rows["events"]) == 1
    if expected == "CANCELLED":
        attempt, query = rows["attempts"][0], rows["queries"][0]
        assert attempt["status"] == "CANCELLED" and attempt["failure_code"] == "CANCELLED"
        assert attempt["query_record_id"] == query["id"]
        assert query["provider_attempt_id"] == provider.calls[0].attempt_id == attempt["id"]
        assert (
            attempt["returned_at"] is not None
            and attempt["provider_request_id"] == "confirmed-remote"
        )
    assert service.execute(execute) == admission
    assert _snapshot(engine, project) == rows and len(provider.calls) == 1
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE literature_search_executions SET status='RUNNING',"
                    "finished_at=NULL,row_version=row_version+1 WHERE id=:id"
                ),
                {"id": execution},
            )
    assert _snapshot(engine, project) == rows


def test_confirmed_outcome_recovery_replay_and_earlier_hits(case):
    engine, healthy, _, principal, project, create = case
    provider = ConfirmingProvider(earlier_hits=True)
    captured = []

    class LostAck(BaseException):
        pass

    class Interrupted(LiteratureSearchExecutionService):
        def _persist_outcome(self, *args, **kwargs):
            result = super()._persist_outcome(*args, **kwargs)
            if args[6].failure_code == "PROVIDER_CANCELLED":
                captured.append((args, kwargs))
                raise LostAck()
            return result

    service = Interrupted(
        healthy._uow_factory, provider, credential_verifier=_AlwaysValidCredential()
    )
    execution = UUID(
        service.create(replace(create, queries=("normalization evidence", "next query")))[
            "execution_id"
        ]
    )
    with pytest.raises(LostAck):
        service.execute(_command("execute", principal, project, execution))
    before = _snapshot(engine, project)
    assert before["executions"][0]["status"] == "RUNNING"
    assert [a["status"] for a in sorted(before["attempts"], key=lambda a: a["query_index"])] == [
        "SUCCEEDED",
        "CANCELLED",
    ]
    assert len(before["results"]) == 2 and len(provider.calls) == 2
    args, kwargs = captured[0]
    ordinary = LiteratureSearchExecutionService(
        healthy._uow_factory, provider, credential_verifier=_AlwaysValidCredential()
    )
    ordinary._persist_outcome(*args, **kwargs)
    assert _snapshot(engine, project) == before
    changed = list(args)
    changed[1] = uuid4()
    with pytest.raises(ResearchBaseError):
        ordinary._persist_outcome(*changed, **kwargs)
    with pytest.raises(ResearchBaseError):
        ordinary._persist_outcome(*args, **dict(kwargs, provider_confirmation=None))
    assert _snapshot(engine, project) == before
    recovery = _command("recover", principal, project, execution)
    receipt = ordinary.recover(recovery)
    final = _snapshot(engine, project)
    assert final["executions"][0]["status"] == "CANCELLED"
    assert final["attempts"] == before["attempts"] and final["results"] == before["results"]
    assert final["queries"] == before["queries"] and len(provider.calls) == 2
    assert ordinary.recover(recovery) == receipt and _snapshot(engine, project) == final
    assert not any(e["kind"] == "CANCEL_REQUESTED" for e in final["events"])


def test_sql_status_or_code_cannot_forge_provider_confirmation(case):
    from tests.integration.phase2.test_pr2_04_execution_recovery import ReservedBeforeInvocation

    engine, healthy, provider, principal, project, create = case
    execution = UUID(healthy.create(create)["execution_id"])
    reserved = ReservedBeforeInvocation(
        healthy._uow_factory, provider, credential_verifier=_AlwaysValidCredential()
    )
    reserved.execute(_command("execute", principal, project, execution))
    before = _snapshot(engine, project)
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE literature_search_provider_attempts SET status='CANCELLED',"
                    "failure_code='CANCELLED',delivery_certainty='RESPONSE_RECEIVED',"
                    "completed_at=clock_timestamp(),result_count=0,warning_codes='[]',"
                    "row_version=2 "
                    "WHERE execution_id=:id"
                ),
                {"id": execution},
            )
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE literature_search_executions SET status='CANCELLED',"
                    "failure_code='CANCELLED',finished_at=clock_timestamp(),"
                    "row_version=row_version+1 "
                    "WHERE id=:id"
                ),
                {"id": execution},
            )
    assert _snapshot(engine, project) == before


def test_migration_empty_roundtrip_and_populated_downgrade(case, phase2_database_url):
    engine, healthy, _, _, _, create = case
    healthy.create(create)
    # Existing valid history cannot be downgraded into the old C1-only semantics.
    with pytest.raises(DBAPIError, match="cannot downgrade populated"):
        command.downgrade(_alembic(phase2_database_url), PARENT)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "0029_metadata_observations"
        )


def test_fresh_migration_empty_roundtrip(phase2_database_url):
    _upgrade(phase2_database_url, REVISION)
    command.downgrade(_alembic(phase2_database_url), PARENT)
    _upgrade(phase2_database_url, REVISION)
    engine = create_engine(phase2_database_url)
    try:
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == REVISION
    finally:
        engine.dispose()


@pytest.mark.parametrize("stage", ["sealed", "planned"])
def test_upgrade_preserves_existing_success_and_c1_history(phase2_database_url, stage):
    from unittest.mock import patch

    from tests.integration.phase2.test_pr2_03_review_guards import _setup
    from tests.integration.phase2.test_pr2_04_schema_coverage import _material, _rows

    with patch(
        "tests.integration.phase2.test_pr2_04_schema_coverage._setup",
        side_effect=lambda url: _setup(url, migration_revision=PARENT),
    ):
        material = _material(phase2_database_url, stage)
    engine = material["engine"]
    if stage == "planned":
        material["service"].cancel(
            _command("cancel", material["principal"], material["project"], material["execution"])
        )
    try:
        before = _rows(engine)
        _upgrade(phase2_database_url, REVISION)
        assert _rows(engine) == before
    finally:
        engine.dispose()


def test_sql_complete_success_cannot_be_relabelled_as_provider_cancellation(phase2_database_url):
    from tests.integration.phase2.test_pr2_04_remaining_schema_acceptance import complete
    from tests.integration.phase2.test_pr2_04_schema_coverage import E, V, _insert, _material, _rows

    material = _material(phase2_database_url, "reserved")
    engine = material["engine"]
    try:
        with engine.begin() as connection:
            complete(connection, material)
        before = _rows(engine)
        with pytest.raises(DBAPIError) as denied:
            with engine.begin() as connection:
                at = connection.scalar(text("SELECT clock_timestamp()"))
                connection.execute(
                    text(
                        f"UPDATE {E} SET status='CANCELLED',failure_code='CANCELLED',"
                        "finished_at=:at,row_version=4 WHERE id=:id"
                    ),
                    dict(id=material["execution"], at=at),
                )
                _insert(
                    connection,
                    V,
                    dict(
                        id=uuid4(),
                        execution_id=material["execution"],
                        sequence=3,
                        kind="FINISHED",
                        attempt_id=None,
                        prior_status="RUNNING",
                        new_status="CANCELLED",
                        prior_row_version=3,
                        new_row_version=4,
                        occurred_at=at,
                        created_at=at,
                        created_by=material["principal"].actor_id,
                    ),
                )
        assert getattr(denied.value.orig, "sqlstate", None) == "P17D5"
        assert _rows(engine) == before
    finally:
        engine.dispose()


def test_invalid_historical_confirmation_blocks_migration_atomically(phase2_database_url):
    from unittest.mock import patch

    from tests.integration.phase2.test_pr2_03_review_guards import _setup
    from tests.integration.phase2.test_pr2_04_schema_coverage import A, _material, _rows

    with patch(
        "tests.integration.phase2.test_pr2_04_schema_coverage._setup",
        side_effect=lambda url: _setup(url, migration_revision=PARENT),
    ):
        material = _material(phase2_database_url, "sealed", 0)
    engine = material["engine"]
    try:
        # Deliberately corrupt this disposable legacy fixture only.
        with engine.begin() as connection:
            connection.execute(text(f"ALTER TABLE {A} DISABLE TRIGGER USER"))
            connection.execute(
                text(
                    f"UPDATE {A} SET status='CANCELLED',failure_code='CANCELLED',"
                    "provider_request_id=NULL,returned_at=NULL,retrieved_at=NULL"
                )
            )
            connection.execute(text(f"ALTER TABLE {A} ENABLE TRIGGER USER"))
        before = _rows(engine)
        with pytest.raises(DBAPIError, match="ambiguous historical provider cancellation"):
            _upgrade(phase2_database_url, REVISION)
        assert _rows(engine) == before
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == PARENT
            assert (
                connection.scalar(
                    text(
                        "SELECT count(*) FROM pg_trigger "
                        "WHERE tgname='trg_pr204_provider_cancellation_commit'"
                    )
                )
                == 0
            )
    finally:
        engine.dispose()


def test_provider_confirmation_cannot_bypass_fresh_authority(case):
    engine, healthy, _, principal, project, create = case
    provider = ConfirmingProvider()

    class Credential:
        valid = True

        def is_valid(self, principal, at):
            return self.valid

    credential = Credential()
    service = LiteratureSearchExecutionService(
        healthy._uow_factory, provider, credential_verifier=credential
    )
    execution = UUID(service.create(create)["execution_id"])
    provider.observer = lambda request: setattr(credential, "valid", False)
    with pytest.raises(ResearchBaseError) as denied:
        service.execute(_command("execute", principal, project, execution))
    assert denied.value.code.value == "FORBIDDEN"
    after = _snapshot(engine, project)
    assert after["executions"][0]["status"] == "RUNNING"
    assert after["attempts"][0]["status"] == "RESERVED"
    assert after["queries"] == after["results"] == []
    assert not any(
        e["kind"] in {"CANCEL_REQUESTED", "OUTCOME_RECORDED", "FINISHED"} for e in after["events"]
    )
    assert len(provider.calls) == 1


def test_http_cannot_submit_provider_cancellation_evidence(case):
    from tests.unit.phase2.test_pr2_04_transport_coverage import _transport

    engine, healthy, provider, principal, project, create = case
    execution = UUID(healthy.create(create)["execution_id"])
    before = _snapshot(engine, project)
    client, _, _, _, _ = _transport(healthy, principal)
    response = client.post(
        f"/literature/search-executions/{execution}:execute",
        headers={"Idempotency-Key": str(uuid4())},
        json={
            "project_id": str(project),
            "failure_code": "PROVIDER_CANCELLED",
            "attempt_id": str(uuid4()),
        },
    )
    assert response.status_code == 422
    assert _snapshot(engine, project) == before and provider.calls == []


def test_late_confirmation_cannot_overwrite_recovered_unknown(case):
    from tests.integration.phase2.test_pr2_04_fault_acceptance_completion import (
        _wait_until_recovery,
    )

    engine, healthy, _, principal, project, create = case
    provider = ConfirmingProvider()
    captured = []

    class Held(BaseException):
        pass

    class Capture(LiteratureSearchExecutionService):
        def _persist_outcome(self, *args, **kwargs):
            captured.append((args, kwargs))
            raise Held()

    service = Capture(healthy._uow_factory, provider, credential_verifier=_AlwaysValidCredential())
    execution = UUID(service.create(replace(create, timeout_seconds=1))["execution_id"])
    with pytest.raises(Held):
        service.execute(_command("execute", principal, project, execution))
    reserved = _snapshot(engine, project)
    _wait_until_recovery(engine, reserved["attempts"][0]["recovery_after"])
    ordinary = LiteratureSearchExecutionService(
        healthy._uow_factory, provider, credential_verifier=_AlwaysValidCredential()
    )
    ordinary.recover(_command("recover", principal, project, execution))
    before = _snapshot(engine, project)
    assert before["executions"][0]["status"] == "UNKNOWN"
    args, kwargs = captured[0]
    with pytest.raises(ResearchBaseError):
        ordinary._persist_outcome(*args, **kwargs)
    assert _snapshot(engine, project) == before and len(provider.calls) == 1
    assert not any(e["kind"] == "CANCEL_REQUESTED" for e in before["events"])


def test_manually_supplied_dto_without_invocation_confirmation_cannot_cancel(case):
    engine, healthy, _, principal, project, create = case
    provider = ConfirmingProvider()
    captured = []

    class Held(BaseException):
        pass

    class Capture(LiteratureSearchExecutionService):
        def _persist_outcome(self, *args, **kwargs):
            captured.append((args, kwargs))
            raise Held()

    service = Capture(healthy._uow_factory, provider, credential_verifier=_AlwaysValidCredential())
    execution = UUID(service.create(create)["execution_id"])
    with pytest.raises(Held):
        service.execute(_command("execute", principal, project, execution))
    args, kwargs = captured[0]
    result = healthy._persist_outcome(*args, **dict(kwargs, provider_confirmation=None))
    assert result[0].value == "FAILED"
    after = _snapshot(engine, project)
    assert after["executions"][0]["status"] == "RUNNING"
    assert after["attempts"][0]["status"] == "PERMANENT_FAILURE"
    assert after["attempts"][0]["failure_code"] == "PROVIDER_MALFORMED"
    assert not any(a["status"] == "CANCELLED" for a in after["attempts"])
