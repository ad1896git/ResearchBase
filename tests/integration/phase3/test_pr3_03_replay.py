"""Durable receipt recovery on PostgreSQL and bounded lock-free query sessions."""

from dataclasses import replace

import pytest
from sqlalchemy import event, text
from tests.integration.phase3.gateway_fixtures import (
    finish,
    measure_gateway,
    request_invocation,
    start,
)
from tests.integration.phase3.test_pr3_00_bootstrap import _rows

from researchbase.agent_runtime.ports.task_repository import UncertainTaskCommit
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


@pytest.mark.parametrize("stage", ["request", "start", "finish"])
def test_lost_response_same_hash_saved_ids_changed_material_conflicts(gateway, stage):
    g = gateway
    c, saved = request_invocation(g)
    if stage in ("start", "finish"):
        c, saved = start(g)
    if stage == "finish":
        c, saved = finish(g)
    context = replace(g.context, finish_observation=c.arguments) if stage == "finish" else g.context
    method = getattr(g.gateway_service, c.command_name)
    before = _rows(g.engine)
    recovered = method(g.owner, c, context)
    assert recovered == replace(saved, replayed=True)
    assert _rows(g.engine) == before
    changed = replace(c, arguments=replace(c.arguments, reason="Different material."))
    if stage == "finish":
        context = replace(context, finish_observation=changed.arguments)
    with pytest.raises(ResearchBaseError) as error:
        method(g.owner, changed, context)
    assert error.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    assert _rows(g.engine) == before


@pytest.mark.parametrize("stage", ["request", "start", "finish"])
def test_uncertain_committed_response_recovers_without_duplicate_effects(
    gateway, monkeypatch, stage
):
    g = gateway
    if stage == "request":
        from tests.integration.phase3.gateway_fixtures import install, request_command

        install(g)
        c = request_command(g)
    else:
        request_invocation(g)
        if stage == "finish":
            start(g)
    measured = measure_gateway(monkeypatch)
    original = SqlAlchemyUnitOfWork.commit
    commits = []

    def commit(uow):
        original(uow)
        commits.append(1)
        raise UncertainTaskCommit()

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", commit)
    if stage == "request":
        saved = g.gateway_service.request_capability_invocation(g.owner, c, g.context)
    elif stage == "start":
        _, saved = start(g)
    else:
        _, saved = finish(g)
    assert saved.replayed and len(commits) == 1
    with g.engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM capability_invocations")).scalar_one() == 1
        assert conn.execute(text("SELECT count(*) FROM budget_reservations")).scalar_one() == 1
        assert (
            conn.execute(text("SELECT count(*) FROM capability_invocation_events")).scalar_one()
            == ({"request": 1, "start": 2, "finish": 3}[stage])
        )
        assert conn.execute(text("SELECT count(*) FROM budget_usage_records")).scalar_one() == (
            int(stage == "finish")
        )
    assert measured == {"gateway_commits": 1, "fake_calls": 0}
    print("uncertain-commit", stage, measured)


@pytest.mark.parametrize("query", ["policy", "invocation", "list"])
def test_queries_one_read_only_session_without_locks_or_writes(gateway, query):
    g = gateway
    request_invocation(g)
    statements, connections, observed_options = [], set(), []

    def trace(conn, cursor, statement, params, context, many):
        statements.append(statement)
        observed_options.append(dict(conn.get_execution_options()))
        connections.add(id(conn))

    event.listen(g.engine, "before_cursor_execute", trace)
    before = _rows(g.engine)
    statements.clear()
    connections.clear()
    observed_options.clear()
    try:
        if query == "policy":
            g.gateway_service.get_agent_tool_policy(g.owner, g.project, g.policy_id)
        elif query == "invocation":
            g.gateway_service.get_capability_invocation(
                g.owner, g.project, g.task, g.args.invocation_id
            )
        else:
            g.gateway_service.list_task_capability_invocations(g.owner, g.project, g.task)
        assert len(connections) == 1
        assert not any(
            s.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE", "LOCK"))
            or "FOR UPDATE" in s
            or "pg_advisory" in s
            for s in statements
        )
        assert observed_options and all(
            o.get("postgresql_readonly") is True and o.get("isolation_level") == "REPEATABLE READ"
            for o in observed_options
        )
    finally:
        event.remove(g.engine, "before_cursor_execute", trace)
    assert _rows(g.engine) == before


def test_query_snapshot_coherent_while_writer_starts_and_finishes(gateway, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import get_ident

    from researchbase.persistence.capability_gateway_repository import SqlAlchemyGatewayRepository

    g = gateway
    request_invocation(g)
    reader_thread = get_ident()
    original = SqlAlchemyGatewayRepository.invocation_events
    writer_committed = []

    def events(repo, *args):
        if get_ident() == reader_thread and not writer_committed:
            with ThreadPoolExecutor(1) as pool:
                pool.submit(start, g).result(timeout=10)
                pool.submit(finish, g).result(timeout=10)
            writer_committed.append(True)
        return original(repo, *args)

    monkeypatch.setattr(SqlAlchemyGatewayRepository, "invocation_events", events)
    snapshot = g.gateway_service.get_capability_invocation(
        g.owner, g.project, g.task, g.args.invocation_id
    )
    assert writer_committed == [True]
    assert snapshot.status == "REQUESTED" and len(snapshot.events) == 1
    current = g.gateway_service.get_capability_invocation(
        g.owner, g.project, g.task, g.args.invocation_id
    )
    assert current.status == "SUCCEEDED" and len(current.events) == 3
    print("QUERY_SNAPSHOT prior=REQUESTED/1 concurrent_committed=SUCCEEDED/3")


@pytest.mark.parametrize("lost_commit", [1, 2, 3])
def test_invoke_lost_responses_each_commit_never_duplicates_fake(gateway, monkeypatch, lost_commit):
    from tests.integration.phase3.gateway_fixtures import install, revision

    from researchbase.agent_runtime.application import routing
    from researchbase.agent_runtime.application.gateway_contracts import CapabilityRequest

    g = gateway
    install(g)
    request = CapabilityRequest(new_uuid7(), new_uuid7(), new_uuid7(), revision(g), g.args)
    calls, commits, active = [], [], []
    original_fake = routing.finite_fake_echo
    original_commit = SqlAlchemyUnitOfWork.commit
    original_begin = SqlAlchemyUnitOfWork.begin_gateway_command
    original_exit = SqlAlchemyUnitOfWork.__exit__

    def begin(uow):
        original_begin(uow)
        active.append(id(uow))

    def exit_uow(uow, *args):
        try:
            return original_exit(uow, *args)
        finally:
            if id(uow) in active:
                active.remove(id(uow))

    def echo(parameters):
        assert not active
        calls.append(parameters)
        return original_fake(parameters)

    def commit(uow):
        original_commit(uow)
        commits.append(1)
        if len(commits) == lost_commit:
            raise UncertainTaskCommit()

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "begin_gateway_command", begin)
    monkeypatch.setattr(SqlAlchemyUnitOfWork, "__exit__", exit_uow)
    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", commit)
    monkeypatch.setattr(routing, "finite_fake_echo", echo)
    if lost_commit == 2:
        with pytest.raises(ResearchBaseError, match="Prior start unresolved") as error:
            g.gateway_service.invoke(request, g.context)
        assert error.value.code == ErrorCode.INVALID_STATE_TRANSITION
        before = _rows(g.engine)
        with pytest.raises(ResearchBaseError, match="Prior start unresolved"):
            g.gateway_service.invoke(request, g.context)
        assert not calls and len(commits) == 2 and _rows(g.engine) == before
    else:
        result = g.gateway_service.invoke(request, g.context)
        assert result.outcome == "SUCCEEDED" and len(commits) == 3 and len(calls) == 1
        before = _rows(g.engine)
        assert g.gateway_service.invoke(request, g.context) == result
        assert len(commits) == 3 and len(calls) == 1 and _rows(g.engine) == before
    with g.engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM budget_reservations")).scalar_one() == 1
        assert conn.execute(text("SELECT count(*) FROM capability_invocations")).scalar_one() == 1
        assert conn.execute(
            text("SELECT count(*) FROM capability_invocation_events")
        ).scalar_one() == len(commits)
        assert conn.execute(text("SELECT count(*) FROM budget_usage_records")).scalar_one() == int(
            lost_commit != 2
        )
    assert not active
    print("LOST_INVOKE_COMMIT", lost_commit, "commits", len(commits), "fake_calls", len(calls))


def test_unknown_replay_never_refunds_or_redispatches(gateway, monkeypatch):
    from tests.integration.phase3.gateway_fixtures import install, revision
    from tests.integration.phase3.test_pr3_04_application import service

    from researchbase.agent_runtime.application import routing
    from researchbase.agent_runtime.application.gateway_contracts import CapabilityRequest

    g = gateway
    parameters = replace(g.args.parameters, outcome="UNKNOWN_OUTCOME")
    identity, digest = g.retain(parameters.canonical_bytes())
    g.args = replace(
        g.args,
        parameters=parameters,
        parameters_artifact_version_id=identity,
        parameters_content_hash=digest,
        requested_parameters_hash=parameters.digest(),
        parameters_byte_size=len(parameters.canonical_bytes()),
    )
    install(g)
    c = CapabilityRequest(new_uuid7(), new_uuid7(), new_uuid7(), revision(g), g.args)
    original = routing.finite_fake_echo
    calls = []

    def echo(parameters):
        calls.append(parameters)
        return original(parameters)

    monkeypatch.setattr(routing, "finite_fake_echo", echo)
    result = g.gateway_service.invoke(c, g.context)
    assert result.outcome == "UNKNOWN_OUTCOME" and len(calls) == 1
    before = _rows(g.engine)
    first = service(g.p).get_task_safety(g.owner, g.project, g.task)
    for _ in range(2):
        assert g.gateway_service.invoke(c, g.context) == result
        current = service(g.p).get_task_safety(g.owner, g.project, g.task)
        assert current.reserved == first.reserved and current.consumed == first.consumed
        assert current.parallel_branches == first.parallel_branches == 1
        assert current.reserved.llm_calls == 1 and current.consumed.llm_calls == 0
        assert current.reserved.token_cost == parameters_unknown_cost()
        assert _rows(g.engine) == before and len(calls) == 1
    finish(g, "FAILED", "RECONCILE", 3)
    settled = _rows(g.engine)
    assert g.gateway_service.invoke(c, g.context) == result
    assert len(calls) == 1 and _rows(g.engine) == settled
    print("UNKNOWN_REPLAY", f"fake_calls={len(calls)}")


def parameters_unknown_cost():
    from decimal import Decimal

    return Decimal("0.125000")


def test_list_snapshot_coherence_under_writer(gateway, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import get_ident

    from researchbase.persistence.capability_gateway_repository import SqlAlchemyGatewayRepository

    g = gateway
    request_invocation(g)
    original = SqlAlchemyGatewayRepository.invocation_page
    reader = get_ident()
    committed, statements, sessions = [], [], set()

    def trace(conn, cursor, statement, params, context, many):
        if get_ident() == reader:
            statements.append(statement)
            sessions.add(id(conn))

    def page(repo, *args):
        rows = original(repo, *args)
        if get_ident() == reader and not committed:
            with ThreadPoolExecutor(1) as pool:
                pool.submit(start, g).result(timeout=10)
                pool.submit(finish, g).result(timeout=10)
            committed.append(True)
        return rows

    monkeypatch.setattr(SqlAlchemyGatewayRepository, "invocation_page", page)
    event.listen(g.engine, "before_cursor_execute", trace)
    try:
        old = g.gateway_service.list_task_capability_invocations(g.owner, g.project, g.task)
    finally:
        event.remove(g.engine, "before_cursor_execute", trace)
    assert committed == [True] and len(sessions) == 1
    assert old.invocations[0].status == "REQUESTED" and len(old.invocations[0].events) == 1
    assert not any(
        s.lstrip().upper().startswith(("LOCK", "INSERT", "UPDATE", "DELETE"))
        or "FOR UPDATE" in s
        or "pg_advisory" in s
        for s in statements
    )
    current = g.gateway_service.list_task_capability_invocations(g.owner, g.project, g.task)
    assert current.invocations[0].status == "SUCCEEDED" and len(current.invocations[0].events) == 3
    print("LIST_SNAPSHOT prior=REQUESTED/1 concurrent_committed=SUCCEEDED/3 reader_sessions=1")


CALLBACK_BARRIER_SQL = """
SELECT pg_advisory_xact_lock(hashtextextended(:key,0))
"""
LOCK_POINTS = (
    "share",
    "project",
    "command",
    "task",
    "actor",
    "version",
    "task_row",
    "step_rows",
    "checkpoint_rows",
    "availability_row",
    "invocation_rows",
)
WRITE_POINTS = {
    "request": (
        "task_update",
        "receipt_insert",
        "reservation_insert",
        "invocation_insert",
        "refs_insert",
        "event_insert",
        "task_event_insert",
        "link_insert",
        "constraints",
    ),
    "start": (
        "task_update",
        "receipt_insert",
        "invocation_update",
        "event_insert",
        "task_event_insert",
        "link_insert",
        "constraints",
    ),
    "finish": (
        "task_update",
        "receipt_insert",
        "usage_insert",
        "invocation_update",
        "event_insert",
        "refs_insert",
        "task_event_insert",
        "link_insert",
        "constraints",
    ),
}


@pytest.mark.parametrize(
    "kind,stage",
    [(kind, point) for kind, writes in WRITE_POINTS.items() for point in (*LOCK_POINTS, *writes)],
    ids=[
        f"{kind}-{point}"
        for kind, writes in WRITE_POINTS.items()
        for point in (*LOCK_POINTS, *writes)
    ],
)
def test_entitlement_and_saved_replay_after_each_blocking_stage(gateway, monkeypatch, kind, stage):
    from concurrent.futures import ThreadPoolExecutor

    from tests.integration.phase3.gateway_fixtures import install, request_command, revision
    from tests.integration.phase3.test_pr3_03_concurrency import observed_wait

    from researchbase.agent_runtime.application.agent_contracts import (
        AgentCommand,
        ChangeAgentAvailability,
    )
    from researchbase.agent_runtime.application.capability_gateway import fake_measurement
    from researchbase.agent_runtime.application.gateway_contracts import (
        FinishInvocationArguments,
        GatewayCommand,
        StartInvocationArguments,
    )
    from researchbase.persistence.capability_gateway_repository import SqlAlchemyGatewayRepository
    from researchbase.persistence.research_task_repository import SHARE_SQL

    g = gateway
    g.args = replace(g.args, deadline_seconds=2)
    install(g)
    if kind != "request":
        requested = request_command(g)
        g.gateway_service.request_capability_invocation(g.owner, requested, g.context)
    if kind == "finish":
        start(g)
    if kind == "request":
        c = request_command(g)
        context = g.context
    elif kind == "start":
        c = GatewayCommand(
            g.project,
            g.task,
            new_uuid7(),
            revision(g),
            "start_capability_invocation",
            StartInvocationArguments(g.args.invocation_id, 1, "Saved start observation."),
        )
        context = g.context
    else:
        args = FinishInvocationArguments(
            g.args.invocation_id,
            2,
            "FINISH",
            "SUCCEEDED",
            fake_measurement("SUCCEEDED"),
            (g.args.input_refs[0],),
            None,
            None,
            "Saved finite finish.",
            None,
            "Saved finish observation.",
        )
        c = GatewayCommand(
            g.project, g.task, new_uuid7(), revision(g), "finish_capability_invocation", args
        )
        context = replace(g.context, finish_observation=args)
    method = getattr(g.gateway_service, c.command_name)
    before = _rows(g.engine)
    trace, acquisition = [], []
    armed = [True]
    barrier_key = "s8:callback:" + str(new_uuid7())
    valid = g.credentials.is_valid
    lock = SqlAlchemyGatewayRepository.lock_gateway
    insert = SqlAlchemyGatewayRepository.insert
    task_update = SqlAlchemyGatewayRepository.update_task
    invocation_update = SqlAlchemyGatewayRepository.update_invocation
    force = SqlAlchemyGatewayRepository.force_constraints
    authorize = g.gateway_service._authorize
    receipt = SqlAlchemyGatewayRepository.committed_receipt
    scoped = g.gateway_service._scoped
    invocation = SqlAlchemyGatewayRepository.invocation
    availability = SqlAlchemyGatewayRepository.agent_availability
    admit = g.gateway_service._admit
    start_admit = g.gateway_service._start_admission
    tables = {
        "research_task_command_receipts": "receipt_insert",
        "budget_reservations": "reservation_insert",
        "capability_invocations": "invocation_insert",
        "capability_invocation_refs": "refs_insert",
        "capability_invocation_events": "event_insert",
        "research_task_events": "task_event_insert",
        "research_task_receipt_events": "link_insert",
        "budget_usage_records": "usage_insert",
    }

    def point(repo, label):
        trace.append(("point", label))
        if armed[0] and label == stage:
            # A test-only lock creates an observed DB wait immediately after this
            # production operation, before its real fresh callback. It changes no
            # canonical lock, row, trigger, receipt visibility or return value.
            repo._session.execute(text(CALLBACK_BARRIER_SQL), {"key": barrier_key})
            acquisition.append(repo._session.execute(text("SELECT clock_timestamp()")).scalar_one())

    def locked(repo, *args, **kwargs):
        fresh = kwargs["after_wait"]
        seen = []

        def callback():
            label = LOCK_POINTS[len(seen)]
            seen.append(label)
            point(repo, label)
            return fresh()

        return lock(repo, *args, **dict(kwargs, after_wait=callback))

    def inserted(repo, table, row):
        result = insert(repo, table, row)
        point(repo, tables[table])
        return result

    def updated_task(repo, *args):
        result = task_update(repo, *args)
        point(repo, "task_update")
        return result

    def updated_invocation(repo, *args):
        result = invocation_update(repo, *args)
        point(repo, "invocation_update")
        return result

    def forced(repo):
        force(repo)
        point(repo, "constraints")

    def authorized(repo, *args, **kwargs):
        trace.append(("authorization", "write" if kwargs.get("write") else "read"))
        return authorize(repo, *args, **kwargs)

    def looked_up(repo, *args):
        result = receipt(repo, *args)
        trace.append(("receipt", result["id"] if result else None))
        return result

    def task_diagnostic(*args, **kwargs):
        trace.append(("diagnostic", "task_state_CAS"))
        return scoped(*args, **kwargs)

    def invocation_diagnostic(repo, *args):
        trace.append(("diagnostic", "invocation_state_CAS"))
        return invocation(repo, *args)

    def availability_diagnostic(repo, *args):
        trace.append(("diagnostic", "availability"))
        return availability(repo, *args)

    def admission_diagnostic(*args, **kwargs):
        trace.append(("diagnostic", "request_expiry_gates_caps"))
        return admit(*args, **kwargs)

    def start_diagnostic(*args, **kwargs):
        trace.append(("diagnostic", "start_expiry_gates_caps"))
        return start_admit(*args, **kwargs)

    monkeypatch.setattr(g.gateway_service, "_scoped", task_diagnostic)
    monkeypatch.setattr(g.gateway_service, "_admit", admission_diagnostic)
    monkeypatch.setattr(g.gateway_service, "_start_admission", start_diagnostic)
    monkeypatch.setattr(SqlAlchemyGatewayRepository, "invocation", invocation_diagnostic)
    monkeypatch.setattr(SqlAlchemyGatewayRepository, "agent_availability", availability_diagnostic)
    monkeypatch.setattr(SqlAlchemyGatewayRepository, "lock_gateway", locked)
    monkeypatch.setattr(SqlAlchemyGatewayRepository, "insert", inserted)
    monkeypatch.setattr(SqlAlchemyGatewayRepository, "update_task", updated_task)
    monkeypatch.setattr(SqlAlchemyGatewayRepository, "update_invocation", updated_invocation)
    monkeypatch.setattr(SqlAlchemyGatewayRepository, "force_constraints", forced)
    monkeypatch.setattr(SqlAlchemyGatewayRepository, "committed_receipt", looked_up)
    monkeypatch.setattr(g.gateway_service, "_authorize", authorized)
    with g.engine.connect() as holder, ThreadPoolExecutor(1) as pool:
        holder.execute(text(CALLBACK_BARRIER_SQL), {"key": barrier_key})
        job = pool.submit(method, g.owner, c, context)
        try:
            waiting = observed_wait(g.engine, blocker=holder, query="pg_advisory_xact_lock")
            monkeypatch.setattr(g.credentials, "is_valid", lambda principal, at: False)
        finally:
            holder.commit()
        with pytest.raises(ResearchBaseError) as error:
            job.result(timeout=10)
    assert error.value.code == ErrorCode.FORBIDDEN and _rows(g.engine) == before
    index = max(i for i, value in enumerate(trace) if value == ("point", stage))
    assert trace[index + 1] == ("authorization", "read")
    assert not any(tag == "receipt" for tag, _ in trace[index + 1 :])
    assert acquisition and acquisition[-1] >= waiting.waitstart
    armed[0] = False
    monkeypatch.setattr(g.credentials, "is_valid", valid)
    trace.clear()
    saved = method(g.owner, c, context)
    expected_points = (*LOCK_POINTS, *WRITE_POINTS[kind])
    points = [value for tag, value in trace if tag == "point"]
    assert points == list(expected_points)
    for i, (tag, _) in enumerate(trace):
        if tag == "point":
            assert trace[i + 1] == ("authorization", "read")
            assert trace[i + 2][0] == "receipt"
            # The current-xmin receipt never counts as a completed replay.
            assert trace[i + 2][1] is None
    if kind == "request":
        start(g)
    if kind != "finish":
        finish(g)
    g.p.service.execute(
        g.owner,
        g.p.command(
            "cancel_research_task",
            g.task,
            revision(g),
            {
                "reason": "Replay must precede current task state and CAS checks.",
            },
        ),
    )
    g.service.execute(
        AgentCommand(
            g.project,
            g.owner,
            new_uuid7(),
            "change_agent_availability",
            1,
            ChangeAgentAvailability(g.args.agent_version_id, "DISABLED", "Replay history."),
        )
    )
    final = _rows(g.engine)

    # All current diagnostics are now adverse. A committed receipt must win over
    # task/invocation CAS, lifecycle, reservation expiry, current availability and spend.
    def forbidden(*args, **kwargs):
        raise AssertionError("admission before saved replay")

    monkeypatch.setattr(g.gateway_service, "_admit", forbidden)
    monkeypatch.setattr(g.gateway_service, "_start_admission", forbidden)
    trace.clear()
    with g.engine.connect() as holder, ThreadPoolExecutor(1) as pool:
        holder.execute(text("LOCK TABLE actor_subject_bindings IN ROW EXCLUSIVE MODE"))
        expiry = holder.execute(
            text("SELECT deadline FROM budget_reservations WHERE operation_id=:id"),
            {"id": g.args.invocation_id},
        ).scalar_one()
        replaying = pool.submit(method, g.owner, c, context)
        wait = observed_wait(g.engine, blocker=holder, query=SHARE_SQL)
        holder.execute(
            text("""
            SELECT pg_sleep(greatest(0,extract(epoch FROM (:expiry-clock_timestamp()))))
        """),
            {"expiry": expiry},
        )
        checked = holder.execute(text("SELECT clock_timestamp()")).scalar_one()
        holder.commit()
        replayed = replaying.result(timeout=10)
    assert checked >= expiry and replayed == replace(saved, replayed=True)
    assert _rows(g.engine) == final
    marker = trace.index(("point", "share"))
    assert trace[marker + 1] == ("authorization", "read")
    assert trace[marker + 2] == ("receipt", saved.receipt_id)
    assert not any(value == ("authorization", "write") for value in trace[marker:])
    assert not any(tag == "diagnostic" for tag, _ in trace[marker:])
    trace.clear()
    monkeypatch.setattr(g.credentials, "is_valid", lambda principal, at: False)
    with pytest.raises(ResearchBaseError) as error:
        method(g.owner, c, context)
    assert error.value.code == ErrorCode.FORBIDDEN and _rows(g.engine) == final
    assert not any(tag == "receipt" for tag, _ in trace)
    print(
        "FRESH_CALLBACK",
        kind,
        stage,
        "waiter_pid",
        waiting.pid,
        "wait_started_at",
        waiting.waitstart,
        "acquired_at",
        acquisition[-1],
        "authorization_before_disclosure=True current_xmin_replay=False",
        "saved_replay_before_CAS_state_expiry_availability=True",
        "replay_waiter_pid",
        wait.pid,
    )
