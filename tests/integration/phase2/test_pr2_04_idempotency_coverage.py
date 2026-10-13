"""Receipt semantics checked against complete durable PostgreSQL snapshots."""

from dataclasses import replace
from uuid import UUID, uuid4

import pytest
from scripts.pr2_04_pytest_evidence import FactRecorder
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from researchbase.application.literature_search_execution import (
    CancelLiteratureSearchExecution,
    CreateLiteratureSearchExecution,
    ExecuteLiteratureSearchExecution,
    LiteratureSearchExecutionService,
    RecoverLiteratureSearchExecution,
)
from researchbase.application.literature_search_plan import CreateLiteratureSearchPlan
from researchbase.application.literature_search_provider import FakeSearchCapability
from researchbase.application.phase2_identity import AssignProjectRole
from researchbase.domain.literature_search_execution import DeliveryCertainty, SearchResponse
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.literature_search_execution_uow import (
    literature_search_execution_uow_factory,
)
from tests.integration.phase2.test_pr2_00_challenges import _service as _identity_service
from tests.integration.phase2.test_pr2_03_effective_authority import _provision
from tests.integration.phase2.test_pr2_03_literature_search_plan_application import (
    _AlwaysValidCredential,
    _material,
)
from tests.integration.phase2.test_pr2_03_review_guards import _freeze, _setup
from tests.integration.phase2.test_pr2_04_execution_recovery import ReservedBeforeInvocation

COMMANDS = {
    "execute": ExecuteLiteratureSearchExecution,
    "cancel": CancelLiteratureSearchExecution,
    "recover": RecoverLiteratureSearchExecution,
}


def _service(engine, provider, cls=LiteratureSearchExecutionService, **kwargs):
    return cls(
        literature_search_execution_uow_factory(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        ),
        provider,
        credential_verifier=_AlwaysValidCredential(),
        **kwargs,
    )


def _execution_setup(phase2_database_url):
    engine, plans, principal, project, plan, version = _setup(phase2_database_url)
    try:
        _freeze(engine, plans, principal, project, plan, version)
        provider = FakeSearchCapability(capability_id="provider-a")
        service = _service(engine, provider)
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
        yield engine, service, provider, principal, project, create
    finally:
        engine.dispose()


@pytest.fixture
def execution_case(phase2_database_url):
    yield from _execution_setup(phase2_database_url)


def _command(name, principal, project, execution_id, request_id=None):
    return COMMANDS[name](
        execution_id,
        principal.actor_id,
        principal.deployment_id,
        request_id or uuid4(),
        project_id=project,
        principal=principal,
    )


def _snapshot(engine, project):
    statements = {
        "executions": "SELECT * FROM literature_search_executions "
        "WHERE project_id=:project ORDER BY id",
        "receipts": "SELECT * FROM literature_search_execution_command_receipts "
        "WHERE project_id=:project ORDER BY id",
        "attempts": "SELECT a.* FROM literature_search_provider_attempts a "
        "JOIN literature_search_executions e ON e.id=a.execution_id "
        "WHERE e.project_id=:project ORDER BY a.id",
        "queries": "SELECT q.* FROM search_query_records q JOIN literature_search_executions e "
        "ON e.id=q.literature_search_execution_id WHERE e.project_id=:project ORDER BY q.id",
        "results": "SELECT r.* FROM search_result_records r JOIN search_query_records q "
        "ON q.id=r.search_query_record_id JOIN literature_search_executions e "
        "ON e.id=q.literature_search_execution_id WHERE e.project_id=:project ORDER BY r.id",
        "events": "SELECT v.* FROM literature_search_execution_events v "
        "JOIN literature_search_executions e ON e.id=v.execution_id "
        "WHERE e.project_id=:project ORDER BY v.id",
    }
    with engine.connect() as connection:
        return {
            name: [
                dict(row) for row in connection.execute(text(sql), {"project": project}).mappings()
            ]
            for name, sql in statements.items()
        }


@pytest.mark.parametrize("name", ["create", "execute", "cancel", "recover"])
@pytest.mark.pr204_requirements("PR204-IDEM-01")
def test_pg_all_commands_exact_replay_preserves_every_durable_row(
    execution_case, name, pr204_trace: FactRecorder
):
    engine, service, provider, principal, project, create = execution_case
    admission = service.create(create)
    execution_id = UUID(admission["execution_id"])
    command = create if name == "create" else _command(name, principal, project, execution_id)
    first = admission if name == "create" else getattr(service, name)(command)
    before, calls = _snapshot(engine, project), len(provider.calls)
    replay = getattr(service, name)(command)
    after = _snapshot(engine, project)
    assert replay == first and before == after
    assert len(provider.calls) == calls
    assert set(replay) == {"execution_id", "command_name", "accepted_at", "accepted_row_version"}
    matching = [r for r in after["receipts"] if r["command_name"] == first["command_name"]]
    assert len(matching) == 1 and matching[0]["result_dto"] == first
    assert matching[0]["deployment_id"] == principal.deployment_id
    assert matching[0]["actor_id"] == principal.actor_id and matching[0]["project_id"] == project
    assert matching[0]["request_id"] == command.request_id
    pr204_trace.record(
        command=name,
        first=first,
        replay=replay,
        before=before,
        after=after,
        provider_calls_before=calls,
        provider_calls_after=len(provider.calls),
    )


@pytest.mark.parametrize("name", ["create", "execute", "cancel", "recover"])
@pytest.mark.pr204_requirements("PR204-IDEM-02")
def test_pg_all_commands_same_complete_key_changed_payload_conflicts_atomically(
    execution_case, name, pr204_trace: FactRecorder
):
    engine, service, provider, principal, project, create = execution_case
    first = service.create(create)
    second = service.create(replace(create, request_id=uuid4()))
    first_id, second_id = UUID(first["execution_id"]), UUID(second["execution_id"])
    original = create if name == "create" else _command(name, principal, project, first_id)
    if name != "create":
        getattr(service, name)(original)
    changed = (
        replace(original, queries=("different material",))
        if name == "create"
        else replace(original, execution_id=second_id)
    )
    before, calls = _snapshot(engine, project), len(provider.calls)
    with pytest.raises(ResearchBaseError) as caught:
        getattr(service, name)(changed)
    after = _snapshot(engine, project)
    assert caught.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    assert before == after and len(provider.calls) == calls
    pr204_trace.record(
        command=name,
        complete_key=[
            principal.deployment_id,
            principal.actor_id,
            project,
            f"{name.upper()}_LITERATURE_SEARCH_EXECUTION",
            original.request_id,
        ],
        original_execution=first_id,
        changed_execution=second_id,
        error_code=caught.value.code.value,
        before=before,
        after=after,
        provider_calls_before=calls,
        provider_calls_after=len(provider.calls),
    )


@pytest.mark.parametrize(
    "status", ["PLANNED", "RUNNING", "FAILED", "CANCELLED", "UNKNOWN", "SUCCEEDED"]
)
@pytest.mark.pr204_requirements("PR204-IDEM-04")
def test_pg_create_replay_in_every_operational_state_and_terminal_command_policy(
    execution_case, status, pr204_trace: FactRecorder
):
    engine, service, provider, principal, project, create = execution_case
    admission = service.create(create)
    execution_id = UUID(admission["execution_id"])
    if status == "RUNNING":
        _service(engine, provider, ReservedBeforeInvocation).execute(
            _command("execute", principal, project, execution_id)
        )
    elif status == "CANCELLED":
        service.cancel(_command("cancel", principal, project, execution_id))
    elif status in {"FAILED", "UNKNOWN", "SUCCEEDED"}:
        if status == "FAILED":
            provider.responses.append(
                SearchResponse(
                    "provider-a",
                    "1",
                    "normalization evidence",
                    "permanent-request",
                    DeliveryCertainty.RESPONSE_RECEIVED,
                    failure_code="PROVIDER_PERMANENT",
                )
            )
        elif status == "UNKNOWN":
            provider.responses.append(
                SearchResponse.uncertain(
                    provider_id="provider-a",
                    provider_version="1",
                    normalized_query="normalization evidence",
                    provider_request_id=None,
                )
            )
        service.execute(_command("execute", principal, project, execution_id))
    before, calls = _snapshot(engine, project), len(provider.calls)
    assert service.get(principal, project, execution_id)["status"] == status
    assert service.create(create) == admission
    assert _snapshot(engine, project) == before and len(provider.calls) == calls
    if status in {"FAILED", "CANCELLED", "UNKNOWN", "SUCCEEDED"}:
        for name in ("cancel", "execute"):
            with pytest.raises(ResearchBaseError) as caught:
                getattr(service, name)(_command(name, principal, project, execution_id))
            assert caught.value.code is ErrorCode.INVALID_STATE_TRANSITION
            assert _snapshot(engine, project) == before
        recover = _command("recover", principal, project, execution_id)
        recovered = service.recover(recover)
        after = _snapshot(engine, project)
        assert len(after["receipts"]) == len(before["receipts"]) + 1
        assert {k: v for k, v in before.items() if k != "receipts"} == {
            k: v for k, v in after.items() if k != "receipts"
        }
        assert (
            recovered["accepted_row_version"]
            == service.get(principal, project, execution_id)["row_version"]
        )
        assert service.recover(recover) == recovered and _snapshot(engine, project) == after
    assert len(provider.calls) == calls
    pr204_trace.record(
        status=status,
        create_admission=admission,
        before=before,
        after=_snapshot(engine, project),
        provider_calls_before=calls,
        provider_calls_after=len(provider.calls),
    )


@pytest.mark.pr204_requirements("PR204-IDEM-01", "PR204-IDEM-06")
def test_pg_c1_lost_response_replays_before_and_after_c2_without_finalizing(
    execution_case, pr204_trace: FactRecorder
):
    engine, service, provider, principal, project, create = execution_case
    execution_id = UUID(service.create(create)["execution_id"])

    def interrupt():
        raise RuntimeError("test interruption after committed C1")

    interrupted = _service(engine, provider, after_cancel_admission=interrupt)
    command = _command("cancel", principal, project, execution_id)
    with pytest.raises(RuntimeError, match="committed C1"):
        interrupted.cancel(command)
    before = _snapshot(engine, project)
    assert before["executions"][0]["status"] == "PLANNED"
    assert before["executions"][0]["row_version"] == 2
    assert [e["kind"] for e in sorted(before["events"], key=lambda e: e["sequence"])] == [
        "CREATED",
        "CANCEL_REQUESTED",
    ]
    admission = service.cancel(command)
    assert admission["accepted_row_version"] == 2 and _snapshot(engine, project) == before
    service.recover(_command("recover", principal, project, execution_id))
    finalized = _snapshot(engine, project)
    assert finalized["executions"][0]["status"] == "CANCELLED"
    assert finalized["executions"][0]["row_version"] == 3
    assert service.cancel(command) == admission and _snapshot(engine, project) == finalized
    assert provider.calls == []
    pr204_trace.record(
        c1=before, c2=finalized, replay_admission=admission, provider_calls=len(provider.calls)
    )


@pytest.mark.pr204_requirements("PR204-IDEM-03")
def test_pg_same_uuid_across_command_scopes_is_independent(
    execution_case, pr204_trace: FactRecorder
):
    engine, service, provider, principal, project, create = execution_case
    execution_id = UUID(service.create(create)["execution_id"])
    recovered = service.recover(
        _command("recover", principal, project, execution_id, create.request_id)
    )
    cancelled = service.cancel(
        _command("cancel", principal, project, execution_id, create.request_id)
    )
    rows = _snapshot(engine, project)
    assert len(rows["executions"]) == 1 and len(rows["receipts"]) == 3
    assert {r["command_name"] for r in rows["receipts"]} == {
        "CREATE_LITERATURE_SEARCH_EXECUTION",
        "RECOVER_LITERATURE_SEARCH_EXECUTION",
        "CANCEL_LITERATURE_SEARCH_EXECUTION",
    }
    assert all(r["request_id"] == create.request_id for r in rows["receipts"])
    assert recovered["accepted_row_version"] == 1 and cancelled["accepted_row_version"] == 2
    assert provider.calls == []
    pr204_trace.record(
        rows=rows, recovered=recovered, cancelled=cancelled, provider_calls=len(provider.calls)
    )


@pytest.mark.pr204_requirements("PR204-IDEM-05")
def test_pg_new_execute_key_cannot_take_over_unresolved_reservation(
    execution_case, pr204_trace: FactRecorder
):
    engine, service, provider, principal, project, create = execution_case
    execution_id = UUID(service.create(create)["execution_id"])
    stopped = _service(engine, provider, ReservedBeforeInvocation)
    first = stopped.execute(_command("execute", principal, project, execution_id))
    before = _snapshot(engine, project)
    contender = service.execute(_command("execute", principal, project, execution_id))
    after = _snapshot(engine, project)
    assert contender["accepted_row_version"] == first["accepted_row_version"] == 2
    assert len(after["receipts"]) == len(before["receipts"]) + 1
    assert {k: v for k, v in before.items() if k != "receipts"} == {
        k: v for k, v in after.items() if k != "receipts"
    }
    assert len(after["attempts"]) == 1 and after["attempts"][0]["status"] == "RESERVED"
    assert provider.calls == []
    pr204_trace.record(
        first=first,
        contender=contender,
        before=before,
        after=after,
        provider_calls=len(provider.calls),
    )


@pytest.mark.parametrize("name", ["create", "execute", "cancel", "recover"])
@pytest.mark.pr204_requirements("PR204-IDEM-02", "PR204-IDEM-01")
def test_pg_pre_admission_failure_rolls_back_all_current_phase_rows(
    execution_case, name, pr204_trace: FactRecorder
):
    engine, service, provider, principal, project, create = execution_case
    execution_id = UUID(service.create(create)["execution_id"])
    command = (
        replace(create, request_id=uuid4())
        if name == "create"
        else _command(name, principal, project, execution_id)
    )

    class InterruptBeforeReceipt(LiteratureSearchExecutionService):
        @staticmethod
        def _dto(*args, **kwargs):
            raise RuntimeError("test interruption before admission receipt")

    interrupted = _service(engine, provider, InterruptBeforeReceipt)
    before = _snapshot(engine, project)
    with pytest.raises(RuntimeError, match="before admission receipt"):
        getattr(interrupted, name)(command)
    after = _snapshot(engine, project)
    assert before == after and provider.calls == []
    # Rollback does not consume the complete key; the original request can admit normally.
    admitted = getattr(service, name)(command)
    assert admitted["command_name"] == f"{name.upper()}_LITERATURE_SEARCH_EXECUTION"
    pr204_trace.record(
        command=name,
        before=before,
        after_interruption=after,
        subsequent_admission=admitted,
        provider_calls=len(provider.calls),
    )


@pytest.mark.pr204_requirements("PR204-IDEM-03")
def test_pg_distinct_authorized_actor_scope_still_obeys_project_execution_uniqueness(
    execution_case, phase2_database_url, pr204_trace: FactRecorder
):
    engine, service, provider, principal, project, create = execution_case
    first = service.create(create)
    identity, _, _ = _identity_service(phase2_database_url)
    target, _ = _provision(identity, principal)
    identity.assign_project_role(
        AssignProjectRole(
            principal,
            project,
            target.actor_id,
            "RESEARCHER",
            "independent receipt actor scope",
            uuid4(),
        )
    )
    alternate = replace(
        create, actor_id=target.actor_id, deployment_id=target.deployment_id, principal=target
    )
    before = _snapshot(engine, project)
    with pytest.raises(ResearchBaseError) as caught:
        service.create(alternate)
    assert caught.value.code is ErrorCode.IDEMPOTENCY_CONFLICT
    assert first["execution_id"] not in caught.value.message
    assert _snapshot(engine, project) == before
    # The same request UUID may instead admit a different command under the target's valid scope.
    recovery = service.recover(
        _command("recover", target, project, UUID(first["execution_id"]), create.request_id)
    )
    rows = _snapshot(engine, project)
    assert len(rows["executions"]) == 1 and len(rows["receipts"]) == 2
    assert {r["actor_id"] for r in rows["receipts"]} == {principal.actor_id, target.actor_id}
    assert provider.calls == []
    pr204_trace.record(
        first=first,
        actor_scope=target.actor_id,
        error_code=caught.value.code.value,
        before=before,
        after=rows,
        recovery=recovery,
        provider_calls=len(provider.calls),
    )


@pytest.mark.pr204_requirements("PR204-IDEM-03")
def test_pg_same_create_uuid_in_different_authorized_projects_is_independent(
    execution_case, phase2_database_url, pr204_trace: FactRecorder
):
    engine, service, provider, principal, project, create = execution_case
    first = service.create(create)
    identity, _, _ = _identity_service(phase2_database_url)
    other_project = identity.create_project_with_owner(
        principal, name="independent execution key", request_id=uuid4()
    )
    # Build and freeze legitimate historical plan material in the other project.
    from researchbase.application.literature_search_plan import LiteratureSearchPlanService
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    plans = LiteratureSearchPlanService(
        lambda: SqlAlchemyUnitOfWork(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        ),
        _AlwaysValidCredential(),
    )
    plan = plans.create(
        CreateLiteratureSearchPlan(
            principal, other_project, _material(UUID(int=0), language_scope=()), uuid4()
        )
    )
    plan_id, version_id = UUID(str(plan["plan_id"])), UUID(str(plan["version_id"]))
    _freeze(engine, plans, principal, other_project, plan_id, version_id)
    second = service.create(replace(create, project_id=other_project, plan_version_id=version_id))
    assert first["execution_id"] != second["execution_id"]
    rows = [_snapshot(engine, scoped) for scoped in (project, other_project)]
    assert all(len(r["executions"]) == len(r["receipts"]) == 1 for r in rows)
    assert all(r["receipts"][0]["request_id"] == create.request_id for r in rows)
    assert provider.calls == []
    pr204_trace.record(
        first=first, second=second, project_rows=rows, provider_calls=len(provider.calls)
    )


@pytest.mark.pr204_requirements("PR204-IDEM-05", "PR204-IDEM-06")
def test_pg_new_execute_resumes_only_known_safe_work_after_committed_retry_outcome(
    execution_case, pr204_trace: FactRecorder
):
    engine, service, provider, principal, project, create = execution_case
    execution_id = UUID(service.create(create)["execution_id"])
    provider.responses.append(
        SearchResponse(
            "provider-a",
            "1",
            "normalization evidence",
            "known-not-sent",
            DeliveryCertainty.NOT_SENT,
            failure_code="PROVIDER_TRANSIENT",
        )
    )

    def interrupt_backoff(delay):
        raise RuntimeError("test process loss during provider backoff")

    interrupted = _service(engine, provider, sleep=interrupt_backoff)
    command = _command("execute", principal, project, execution_id)
    with pytest.raises(RuntimeError, match="provider backoff"):
        interrupted.execute(command)
    before = _snapshot(engine, project)
    assert before["executions"][0]["status"] == "RUNNING"
    assert len(before["attempts"]) == 1 and before["attempts"][0]["status"] == "RETRYABLE_FAILURE"
    assert len(provider.calls) == 1
    replay = service.execute(command)
    assert _snapshot(engine, project) == before and len(provider.calls) == 1
    continued = service.execute(_command("execute", principal, project, execution_id))
    after = _snapshot(engine, project)
    assert after["executions"][0]["status"] == "SUCCEEDED"
    assert after["executions"][0]["started_at"] == before["executions"][0]["started_at"]
    assert (
        after["executions"][0]["execution_context"] == before["executions"][0]["execution_context"]
    )
    assert sorted(a["attempt_number"] for a in after["attempts"]) == [1, 2]
    assert len(after["queries"]) == 2 and len(provider.calls) == 2
    assert len(after["receipts"]) == len(before["receipts"]) + 1
    pr204_trace.record(
        before=before,
        replay=replay,
        continued=continued,
        after=after,
        provider_calls=len(provider.calls),
    )


@pytest.mark.pr204_requirements("PR204-CANCEL-04")
def test_pg_cooperative_token_does_not_forge_cancel_intent_and_terminal_cancel_denies(
    execution_case, pr204_trace: FactRecorder
):
    engine, service, provider, principal, project, create = execution_case
    execution_id = UUID(service.create(create)["execution_id"])
    # This is the same cooperative token supplied at the provider boundary, with no C1 command.
    provider.observer = lambda request: service._cancellation_event(execution_id).set()
    service.execute(_command("execute", principal, project, execution_id))
    before = _snapshot(engine, project)
    assert before["executions"][0]["status"] == "SUCCEEDED"
    assert all(e["kind"] != "CANCEL_REQUESTED" for e in before["events"])
    assert all(
        r["command_name"] != "CANCEL_LITERATURE_SEARCH_EXECUTION" for r in before["receipts"]
    )
    with pytest.raises(ResearchBaseError) as caught:
        service.cancel(_command("cancel", principal, project, execution_id))
    assert caught.value.code is ErrorCode.INVALID_STATE_TRANSITION
    assert _snapshot(engine, project) == before and len(provider.calls) == 1
    pr204_trace.record(
        before=before,
        after=_snapshot(engine, project),
        terminal_cancel_error=caught.value.code.value,
        provider_calls=len(provider.calls),
    )
