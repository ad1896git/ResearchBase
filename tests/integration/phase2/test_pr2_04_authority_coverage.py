"""Current database authority and attribution across execution phase boundaries."""

from dataclasses import replace
from uuid import UUID, uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy import text

from researchbase.application.literature_search_execution import LiteratureSearchExecutionService
from researchbase.application.phase2_identity import AssignProjectRole, CloseProjectRole
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.test_pr2_00_challenges import _service as _identity_service
from tests.integration.phase2.test_pr2_03_effective_authority import (
    _lose_owner_authority,
    _provision,
)
from tests.integration.phase2.test_pr2_04_execution_recovery import OutcomeBeforeFinalization
from tests.integration.phase2.test_pr2_04_idempotency_coverage import (
    _command,
    _execution_setup,
    _service,
    _snapshot,
)


@pytest.fixture
def execution_case(phase2_database_url):
    yield from _execution_setup(phase2_database_url)


@pytest.mark.parametrize("role", ["OWNER", "RESEARCHER", "REVIEWER", "APPROVER", "VIEWER"])
@pytest.mark.pr204_requirements("PR204-AUTH-01", "PR204-AUTH-04")
def test_pg_human_role_matrix_all_writes_and_reads(
    execution_case, phase2_database_url, role, pr204_trace: FactRecorder
):
    engine, service, provider, owner, project, create = execution_case
    identity, _, _ = _identity_service(phase2_database_url)
    target, _ = _provision(identity, owner)
    identity.assign_project_role(
        AssignProjectRole(owner, project, target.actor_id, role, "execution role coverage", uuid4())
    )
    own_create = replace(
        create,
        actor_id=target.actor_id,
        deployment_id=target.deployment_id,
        principal=target,
        request_id=uuid4(),
    )
    allowed = role in {"OWNER", "RESEARCHER"}
    baseline = _snapshot(engine, project)
    if allowed:
        admission = service.create(own_create)
    else:
        with pytest.raises(ResearchBaseError) as caught:
            service.create(own_create)
        assert caught.value.code is ErrorCode.FORBIDDEN
        assert _snapshot(engine, project) == baseline
        admission = service.create(create)
    execution_id = UUID(admission["execution_id"])
    assert service.get(target, project, execution_id)["status"] == "PLANNED"
    assert service.list(target, project)[0]["execution_id"] == str(execution_id)
    assert service.get_provenance(target, project, execution_id)["execution"][
        "execution_id"
    ] == str(execution_id)
    outcomes = {}
    # Independent execution per operation preserves the role decision from terminal policy.
    for name in ("execute", "cancel", "recover"):
        fresh = service.create(replace(create, request_id=uuid4()))
        command = _command(name, target, project, UUID(fresh["execution_id"]))
        before, calls = _snapshot(engine, project), len(provider.calls)
        if allowed:
            result = getattr(service, name)(command)
            assert result["command_name"] == f"{name.upper()}_LITERATURE_SEARCH_EXECUTION"
            outcomes[name] = result
        else:
            with pytest.raises(ResearchBaseError) as denied:
                getattr(service, name)(command)
            assert denied.value.code is ErrorCode.FORBIDDEN
            assert _snapshot(engine, project) == before and len(provider.calls) == calls
            outcomes[name] = denied.value.code.value
    pr204_trace.record(
        actor_type="HUMAN",
        actor_id=target.actor_id,
        role=role,
        write_outcomes=outcomes,
        durable_rows=_snapshot(engine, project),
        provider_calls=len(provider.calls),
    )


@pytest.mark.pr204_requirements("PR204-AUTH-01", "PR204-API-02")
def test_pg_cross_project_get_provenance_cursor_and_writes_are_non_disclosing(
    execution_case, phase2_database_url, pr204_trace: FactRecorder
):
    engine, service, provider, principal, project, create = execution_case
    execution_id = UUID(service.create(create)["execution_id"])
    identity, _, _ = _identity_service(phase2_database_url)
    foreign_project = identity.create_project_with_owner(
        principal, name="foreign execution scope", request_id=uuid4()
    )
    before = _snapshot(engine, project)
    errors = {}
    operations = {
        "get": lambda: service.get(principal, foreign_project, execution_id),
        "provenance": lambda: service.get_provenance(principal, foreign_project, execution_id),
        "cursor": lambda: service.list(principal, foreign_project, after=execution_id),
    }
    for name in ("execute", "cancel", "recover"):
        operations[name] = lambda name=name: getattr(service, name)(
            _command(name, principal, foreign_project, execution_id)
        )
    for name, operation in operations.items():
        with pytest.raises(ResearchBaseError) as caught:
            operation()
        assert caught.value.code is ErrorCode.NOT_FOUND
        assert str(execution_id) not in caught.value.message
        errors[name] = caught.value.code.value
    assert _snapshot(engine, project) == before
    assert service.list(principal, foreign_project) == [] and provider.calls == []
    pr204_trace.record(
        project_id=project,
        foreign_project_id=foreign_project,
        errors=errors,
        before=before,
        after=_snapshot(engine, project),
        provider_calls=len(provider.calls),
    )


@pytest.mark.parametrize("boundary", ["TX_B", "TX_C", "disclosure"])
@pytest.mark.pr204_requirements("PR204-AUTH-03", "PR204-IDEM-06")
def test_pg_authority_loss_denies_each_post_admission_boundary(
    execution_case, phase2_database_url, boundary, pr204_trace: FactRecorder
):
    engine, service, provider, principal, project, create = execution_case
    execution_id = UUID(service.create(create)["execution_id"])

    def lose():
        _lose_owner_authority(engine, principal, project, phase2_database_url)

    if boundary == "TX_B":
        provider.observer = lambda request: lose()
    elif boundary == "TX_C":

        class LossBeforeFinalization(LiteratureSearchExecutionService):
            def _finalize_execution(self, *args, **kwargs):
                lose()
                return super()._finalize_execution(*args, **kwargs)

        service = _service(engine, provider, LossBeforeFinalization)
    else:

        class LossBeforeDisclosure(LiteratureSearchExecutionService):
            def _drive(self, *args, **kwargs):
                result = super()._drive(*args, **kwargs)
                lose()
                return result

        service = _service(engine, provider, LossBeforeDisclosure)
    command = _command("execute", principal, project, execution_id)
    result, error = None, None
    try:
        result = service.execute(command)
    except ResearchBaseError as caught:
        error = caught
    after = _snapshot(engine, project)
    pr204_trace.record(
        boundary=boundary,
        returned_admission=result,
        error_code=error.code.value if error else None,
        durable_rows=after,
        provider_calls=len(provider.calls),
    )
    assert error is not None and error.code is ErrorCode.FORBIDDEN
    assert result is None and len(provider.calls) == 1
    execute_receipts = [r for r in after["receipts"] if r["request_id"] == command.request_id]
    assert (
        len(execute_receipts) == 1
        and execute_receipts[0]["result_dto"]["accepted_row_version"] == 2
    )
    assert len(after["attempts"]) == 1
    if boundary == "TX_B":
        assert after["attempts"][0]["status"] == "RESERVED"
        assert after["queries"] == [] and after["results"] == []
        assert after["executions"][0]["status"] == "RUNNING"
        assert {e["kind"] for e in after["events"]} == {"CREATED", "ATTEMPT_RESERVED"}
    elif boundary == "TX_C":
        assert after["attempts"][0]["status"] == "SUCCEEDED"
        assert len(after["queries"]) == 1
        assert after["executions"][0]["status"] == "RUNNING"
        assert all(e["kind"] != "FINISHED" for e in after["events"])
    for read in (
        lambda: service.get(principal, project, execution_id),
        lambda: service.get_provenance(principal, project, execution_id),
        lambda: service.list(principal, project),
    ):
        with pytest.raises(ResearchBaseError) as denied:
            read()
        assert denied.value.code is ErrorCode.FORBIDDEN
    with pytest.raises(ResearchBaseError) as replay_denied:
        service.execute(command)
    assert replay_denied.value.code is ErrorCode.FORBIDDEN
    assert _snapshot(engine, project) == after


@pytest.mark.pr204_requirements("PR204-AUTH-04")
def test_pg_different_current_writer_recovers_without_impersonating_initiator(
    execution_case, phase2_database_url, pr204_trace: FactRecorder
):
    engine, service, provider, initiator, project, create = execution_case
    identity, _, _ = _identity_service(phase2_database_url)
    recovery_actor, _ = _provision(identity, initiator)
    identity.assign_project_role(
        AssignProjectRole(
            initiator,
            project,
            recovery_actor.actor_id,
            "RESEARCHER",
            "authorized execution recovery",
            uuid4(),
        )
    )
    execution_id = UUID(service.create(create)["execution_id"])
    _service(engine, provider, OutcomeBeforeFinalization).execute(
        _command("execute", initiator, project, execution_id)
    )
    before, calls = _snapshot(engine, project), len(provider.calls)
    recovered = service.recover(_command("recover", recovery_actor, project, execution_id))
    after = _snapshot(engine, project)
    assert before["executions"][0]["status"] == "RUNNING"
    assert after["executions"][0]["status"] == "SUCCEEDED"
    assert after["executions"][0]["executed_by"] == initiator.actor_id
    assert after["executions"][0]["requested_by"] == initiator.actor_id
    assert after["attempts"] == before["attempts"] and after["queries"] == before["queries"]
    assert after["results"] == before["results"] and len(provider.calls) == calls == 1
    finished = [e for e in after["events"] if e["kind"] == "FINISHED"]
    assert len(finished) == 1 and finished[0]["created_by"] == recovery_actor.actor_id
    pr204_trace.record(
        initiator=initiator.actor_id,
        recovery_actor=recovery_actor.actor_id,
        admission=recovered,
        before=before,
        after=after,
        provider_calls=len(provider.calls),
    )


@pytest.mark.pr204_requirements("PR204-AUTH-04", "PR204-IDEM-01")
def test_pg_writer_demotion_to_viewer_denies_saved_receipt_disclosure_and_recovery(
    execution_case, phase2_database_url, pr204_trace: FactRecorder
):
    engine, service, provider, owner, project, create = execution_case
    identity, _, _ = _identity_service(phase2_database_url)
    target, _ = _provision(identity, owner)
    role_id = identity.assign_project_role(
        AssignProjectRole(
            owner, project, target.actor_id, "RESEARCHER", "initial execution authority", uuid4()
        )
    )
    own_create = replace(create, actor_id=target.actor_id, principal=target, request_id=uuid4())
    admission = service.create(own_create)
    execution_id = UUID(admission["execution_id"])
    identity.close_project_role(CloseProjectRole(owner, project, role_id, "demotion", uuid4()))
    identity.assign_project_role(
        AssignProjectRole(owner, project, target.actor_id, "VIEWER", "read only", uuid4())
    )
    before = _snapshot(engine, project)
    assert service.get(target, project, execution_id)["status"] == "PLANNED"
    errors = []
    for operation in (
        lambda: service.create(own_create),
        lambda: service.recover(_command("recover", target, project, execution_id)),
    ):
        with pytest.raises(ResearchBaseError) as caught:
            operation()
        assert caught.value.code is ErrorCode.FORBIDDEN
        errors.append(caught.value.code.value)
    assert _snapshot(engine, project) == before and provider.calls == []
    pr204_trace.record(
        actor_id=target.actor_id,
        errors=errors,
        before=before,
        after=_snapshot(engine, project),
        provider_calls=len(provider.calls),
    )


@pytest.mark.pr204_requirements("PR204-API-02")
def test_pg_project_scoped_pagination_is_stable_and_returns_public_projections(
    execution_case, pr204_trace: FactRecorder
):
    engine, service, provider, principal, project, create = execution_case
    ids = [service.create(replace(create, request_id=uuid4()))["execution_id"] for _ in range(5)]
    baseline = _snapshot(engine, project)
    expected = [
        str(row["id"])
        for row in sorted(baseline["executions"], key=lambda row: (row["created_at"], row["id"]))
    ]
    assert set(expected) == set(ids)
    page1 = service.list(principal, project, limit=2)
    page2 = service.list(principal, project, limit=2, after=UUID(page1[-1]["execution_id"]))
    page3 = service.list(principal, project, limit=2, after=UUID(page2[-1]["execution_id"]))
    assert [row["execution_id"] for row in page1 + page2 + page3] == expected
    assert [len(page) for page in (page1, page2, page3)] == [2, 2, 1]
    assert service.list(principal, project, limit=2) == page1
    assert service.list(principal, project, limit=100, after=UUID(expected[-1])) == []
    assert [row["execution_id"] for row in service.list(principal, project)] == expected
    projection_keys = {
        "execution_id",
        "project_id",
        "search_plan_version_id",
        "status",
        "requested_by",
        "executed_by",
        "started_at",
        "finished_at",
        "row_version",
        "failure_code",
    }
    assert all(type(row) is dict and set(row) == projection_keys for row in page1 + page2 + page3)
    for limit in (0, 101):
        with pytest.raises(ResearchBaseError) as caught:
            service.list(principal, project, limit=limit)
        assert caught.value.code is ErrorCode.VALIDATION_ERROR
    with pytest.raises(ResearchBaseError) as unknown:
        service.list(principal, project, after=uuid4())
    assert unknown.value.code is ErrorCode.NOT_FOUND
    assert baseline == _snapshot(engine, project) and provider.calls == []
    pr204_trace.record(
        expected_order=expected,
        pages=[page1, page2, page3],
        before=baseline,
        after=_snapshot(engine, project),
        provider_calls=len(provider.calls),
    )


@pytest.mark.parametrize(
    "operation", ["get", "list", "provenance", "create", "execute", "cancel", "recover", "replay"]
)
@pytest.mark.pr204_requirements("PR204-API-02", "PR204-AUTH-01", "PR204-IDEM-01")
def test_pg_current_credential_expiry_denies_reads_writes_and_receipt_replay(
    execution_case, operation, pr204_trace: FactRecorder
):
    engine, healthy, provider, principal, project, create = execution_case
    execution_id = UUID(healthy.create(create)["execution_id"])
    observations = []

    class Expired:
        def is_valid(self, principal, at):
            observations.append(
                {"principal": principal.actor_id, "authorization_time": at, "decision": False}
            )
            return False

    service = LiteratureSearchExecutionService(
        healthy._uow_factory, provider, credential_verifier=Expired()
    )
    before = _snapshot(engine, project)
    operations = {
        "get": lambda: service.get(principal, project, execution_id),
        "list": lambda: service.list(principal, project),
        "provenance": lambda: service.get_provenance(principal, project, execution_id),
        "create": lambda: service.create(replace(create, request_id=uuid4())),
        "replay": lambda: service.create(create),
    }
    for name in ("execute", "cancel", "recover"):
        operations[name] = lambda name=name: getattr(service, name)(
            _command(name, principal, project, execution_id)
        )
    with pytest.raises(ResearchBaseError) as caught:
        operations[operation]()
    after = _snapshot(engine, project)
    pr204_trace.record(
        operation=operation,
        credential_checks=observations,
        error_code=caught.value.code.value,
        before=before,
        after=after,
        provider_calls=len(provider.calls),
    )
    assert caught.value.code is ErrorCode.FORBIDDEN
    assert observations and before == after and provider.calls == []


@pytest.mark.pr204_requirements("PR204-API-02")
def test_pg_equal_created_at_cursor_uses_uuid_tiebreak_without_duplicates_or_omissions(
    execution_case, pr204_trace: FactRecorder
):
    from unittest.mock import patch

    from researchbase.persistence.literature_search_execution_repository import (
        SqlAlchemyLiteratureSearchExecutionRepository,
    )

    engine, service, provider, principal, project, create = execution_case
    with engine.connect() as connection:
        timestamp = connection.execute(text("SELECT clock_timestamp()")).scalar_one()
    # Only execution provenance timestamps are held equal; trusted authority keeps the actual DB clock.  # noqa: E501
    with patch.object(
        SqlAlchemyLiteratureSearchExecutionRepository, "_database_now", return_value=timestamp
    ):
        identities = [
            UUID(service.create(replace(create, request_id=uuid4()))["execution_id"])
            for _ in range(5)
        ]
    expected = [str(i) for i in sorted(identities)]
    rows = []
    cursor = None
    pages = []
    while True:
        page = service.list(principal, project, limit=2, after=cursor)
        pages.append(page)
        if not page:
            break
        rows.extend(row["execution_id"] for row in page)
        cursor = UUID(page[-1]["execution_id"])
        assert len(pages) <= 4
    with engine.connect() as connection:
        stored = list(
            connection.execute(
                text(
                    "SELECT id,created_at FROM literature_search_executions WHERE project_id=:id ORDER BY created_at,id"  # noqa: E501
                ),
                {"id": project},
            ).mappings()
        )
    pr204_trace.record(
        equal_timestamp=timestamp, stored_rows=stored, pages=pages, expected_ids=expected
    )
    assert all(row["created_at"] == timestamp for row in stored)
    assert rows == expected and len(set(rows)) == 5 and provider.calls == []
