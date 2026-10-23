"""DB-observed gateway blocking and advancing authorization timestamps."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from time import monotonic, sleep

import pytest
from sqlalchemy import create_engine, event, text
from tests.integration.phase3.gateway_fixtures import (
    install,
    request_command,
    request_invocation,
    start,
)

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7
from researchbase.persistence.research_task_repository import SHARE_SQL
from researchbase.persistence.task_safety_repository import SqlAlchemyTaskSafetyRepository

WAITERS_SQL = """
SELECT l.pid,l.locktype,l.mode,l.relation::regclass::text AS relation,
       l.waitstart,a.xact_start,a.query,clock_timestamp() AS observed_at
FROM pg_locks l JOIN pg_stat_activity a ON a.pid=l.pid
WHERE NOT l.granted AND a.datname=current_database() AND a.pid<>pg_backend_pid()
  AND CAST(:blocker AS integer)=ANY(pg_blocking_pids(l.pid))
  AND (CAST(:pid AS integer) IS NULL OR l.pid=CAST(:pid AS integer))
  AND strpos(a.query,CAST(:query AS text))>0
ORDER BY l.waitstart
"""
ADVISORY_SQL = """
SELECT pg_advisory_xact_lock(hashtextextended(:key,0))
"""


def backend_pid(connection):
    return connection.connection.driver_connection.info.backend_pid


def observed_wait(engine, *, blocker, query, pid=None, count=1):
    blocker_id = blocker if isinstance(blocker, int) else backend_pid(blocker)
    deadline = monotonic() + 8
    observer = create_engine(engine.url)
    try:
        while monotonic() < deadline:
            with observer.connect() as conn:
                rows = conn.execute(
                    text(WAITERS_SQL),
                    {
                        "blocker": blocker_id,
                        "query": query,
                        "pid": pid,
                    },
                ).all()
            if len(rows) >= count:
                print("DB_WAIT", [dict(r._mapping) for r in rows])
                return rows[0]
            sleep(0.01)
    finally:
        observer.dispose()
    # Polling merely schedules observations; pg_locks proves blocking.
    raise AssertionError("required PostgreSQL lock waiter was not observed")


@pytest.mark.parametrize("stage", ["share", "command", "task", "actor", "version", "row"])
def test_observed_first_share_advisory_and_row_waits(gateway, stage):
    g = gateway
    install(g)
    c = request_command(g)
    keys = {
        "command": f"pr301:command:{g.project}:{g.owner.actor_id}:{c.command_id}",
        "task": f"pr301:task:{g.task}",
        "actor": f"pr302:actor:{g.agent_actor}",
        "version": f"pr302:version:{g.args.agent_version_id}",
    }
    with g.engine.connect() as holder, ThreadPoolExecutor(1) as pool:
        if stage == "share":
            holder.execute(text("LOCK TABLE actor_subject_bindings IN ROW EXCLUSIVE MODE"))
        elif stage == "row":
            holder.execute(
                text("SELECT id FROM research_tasks WHERE id=:id FOR UPDATE"), {"id": g.task}
            )
        else:
            holder.execute(text(ADVISORY_SQL), {"key": keys[stage]})
        job = pool.submit(g.gateway_service.request_capability_invocation, g.owner, c, g.context)
        waiting = observed_wait(
            g.engine,
            blocker=holder,
            query=SHARE_SQL
            if stage == "share"
            else ("research_tasks" if stage == "row" else "pg_advisory_xact_lock"),
        )
        if stage == "share":
            assert waiting.query == SHARE_SQL and waiting.mode == "ShareLock"
        elif stage == "row":
            assert "research_tasks" in waiting.query and "FOR UPDATE" in waiting.query
        else:
            assert waiting.locktype == "advisory"
        holder.commit()
        assert job.result(timeout=10).invocation_id == g.args.invocation_id


def test_wait_across_credential_expiry_uses_fresh_db_time(gateway, monkeypatch):
    g = gateway
    install(g)
    c = request_command(g)
    checked, acquired = [], []
    from threading import get_ident

    main_thread = get_ident()
    original = SqlAlchemyTaskSafetyRepository.at

    def at(repo):
        stamp = original(repo)
        checked.append(stamp)
        return stamp

    monkeypatch.setattr(SqlAlchemyTaskSafetyRepository, "at", at)
    with g.engine.connect() as holder, ThreadPoolExecutor(1) as pool:
        expiry = holder.execute(
            text("SELECT clock_timestamp()+interval '1.5 seconds'")
        ).scalar_one()
        monkeypatch.setattr(g.credentials, "is_valid", lambda principal, at: at < expiry)
        holder.execute(text(ADVISORY_SQL), {"key": f"pr301:task:{g.task}"})

        def acquired_lock(conn, cursor, statement, params, context, many):
            if get_ident() != main_thread and "pg_advisory_xact_lock" in statement:
                if params.get("key") == f"pr301:task:{g.task}":
                    acquired.append(conn.execute(text("SELECT clock_timestamp()")).scalar_one())

        event.listen(g.engine, "after_cursor_execute", acquired_lock)
        job = pool.submit(g.gateway_service.request_capability_invocation, g.owner, c, g.context)
        waiting = observed_wait(g.engine, blocker=holder, query="pg_advisory_xact_lock")
        assert waiting.xact_start < expiry and waiting.waitstart < expiry
        holder.execute(
            text("""
            SELECT pg_sleep(greatest(0,extract(epoch FROM (:expiry-clock_timestamp()))))
        """),
            {"expiry": expiry},
        )
        released = holder.execute(text("SELECT clock_timestamp()")).scalar_one()
        holder.commit()
        with pytest.raises(ResearchBaseError) as error:
            job.result(timeout=10)
        event.remove(g.engine, "after_cursor_execute", acquired_lock)
    assert acquired and checked[-1] >= acquired[-1] >= expiry
    assert error.value.code == ErrorCode.FORBIDDEN
    assert checked[-1] >= released >= expiry and checked[-1] > expiry
    with g.engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM capability_invocations")).scalar_one() == 0
    print(
        "EXPIRY",
        dict(
            tx_started_at=waiting.xact_start,
            wait_started_at=waiting.waitstart,
            expiry_at=expiry,
            acquired_at=acquired[-1],
            checked_at=checked[-1],
            released_at=released,
            effects=0,
        ),
    )


def test_two_requests_same_revision_have_one_winner(gateway):
    g = gateway
    install(g)
    commands = [request_command(g), request_command(g)]
    commands[1] = replace(
        commands[1], arguments=replace(commands[1].arguments, invocation_id=new_uuid7())
    )
    with g.engine.connect() as holder, ThreadPoolExecutor(2) as pool:
        holder.execute(text(ADVISORY_SQL), {"key": f"pr301:task:{g.task}"})
        jobs = [
            pool.submit(g.gateway_service.request_capability_invocation, g.owner, c, g.context)
            for c in commands
        ]
        observed_wait(g.engine, blocker=holder, query="pg_advisory_xact_lock")
        holder.commit()
        results = []
        for job in jobs:
            try:
                results.append(job.result(timeout=10))
            except ResearchBaseError as error:
                results.append(error)
    assert sum(isinstance(r, ResearchBaseError) for r in results) == 1
    assert next(r for r in results if isinstance(r, ResearchBaseError)).code == (
        ErrorCode.CONCURRENT_MODIFICATION
    )


def test_start_lock_timeout_never_retries(gateway):
    g = gateway
    request_invocation(g)
    attempts = []

    def trace(conn, cursor, statement, params, context, many):
        if statement == SHARE_SQL:
            attempts.append(statement)
            conn.exec_driver_sql("SET LOCAL lock_timeout='100ms'")

    event.listen(g.engine, "before_cursor_execute", trace)
    try:
        with g.engine.connect() as holder, ThreadPoolExecutor(1) as pool:
            holder.execute(text(ADVISORY_SQL), {"key": f"pr301:task:{g.task}"})
            job = pool.submit(start, g)
            with pytest.raises(ResearchBaseError) as error:
                job.result(timeout=5)
            holder.rollback()
        assert error.value.code == ErrorCode.CONCURRENT_MODIFICATION
        assert len(attempts) == 1
    finally:
        event.remove(g.engine, "before_cursor_execute", trace)


SERIALIZATION_ERROR_SQL = """
DO $$ BEGIN RAISE EXCEPTION 'S8 retry probe' USING ERRCODE='40001'; END $$
"""
DEADLOCK_ERROR_SQL = """
DO $$ BEGIN RAISE EXCEPTION 'S8 retry probe' USING ERRCODE='40P01'; END $$
"""
QUERY_TIMEOUT_ERROR_SQL = """
DO $$ BEGIN RAISE EXCEPTION 'S8 timeout probe' USING ERRCODE='57014'; END $$
"""


@pytest.mark.parametrize("state,attempt_count", [("40001", 3), ("40P01", 3), ("57014", 1)])
def test_server_error_retry_classification_and_fresh_transactions(
    gateway, monkeypatch, state, attempt_count
):
    from researchbase.persistence.capability_gateway_repository import SqlAlchemyGatewayRepository

    g = gateway
    install(g)
    transactions = []
    original = SqlAlchemyGatewayRepository.lock_gateway
    sql = {
        "40001": SERIALIZATION_ERROR_SQL,
        "40P01": DEADLOCK_ERROR_SQL,
        "57014": QUERY_TIMEOUT_ERROR_SQL,
    }[state]

    def lock(repo, *args, **kwargs):
        original(repo, *args, **kwargs)
        transactions.append(
            repo._session.execute(text("SELECT pg_current_xact_id()::text")).scalar_one()
        )
        repo._session.execute(text(sql))

    monkeypatch.setattr(SqlAlchemyGatewayRepository, "lock_gateway", lock)
    with pytest.raises(ResearchBaseError) as error:
        g.gateway_service.request_capability_invocation(g.owner, request_command(g), g.context)
    assert error.value.code == ErrorCode.CONCURRENT_MODIFICATION
    assert len(transactions) == len(set(transactions)) == attempt_count
    with g.engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM capability_invocations")).scalar_one() == 0
    print("SERVER_ERROR_RETRY", state, "fresh_transactions", transactions, "effects=0")


def test_wait_across_agent_membership_revocation_denies_before_effects(gateway):
    from researchbase.application.phase2_identity import EndProjectMembership

    g = gateway
    install(g)
    c = request_command(g)
    context = replace(g.context, principal=g.agent_principal)
    with g.engine.connect() as holder, ThreadPoolExecutor(1) as pool:
        holder.execute(text("LOCK TABLE actor_subject_bindings IN ROW EXCLUSIVE MODE"))
        job = pool.submit(
            g.gateway_service.request_capability_invocation, g.agent_principal, c, context
        )
        observed_wait(g.engine, blocker=holder, query=SHARE_SQL)
        g.identity.end_project_membership(
            EndProjectMembership(
                g.owner,
                g.project,
                g.enrollment_result.result_membership_id,
                "Revoke pending gateway entitlement.",
                new_uuid7(),
            )
        )
        holder.commit()
        with pytest.raises(ResearchBaseError) as error:
            job.result(timeout=10)
    assert error.value.code == ErrorCode.FORBIDDEN
    with g.engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM capability_invocations")).scalar_one() == 0


def test_two_tasks_same_version_wait_for_availability_writer(gateway, monkeypatch):
    from threading import Event, get_ident

    from tests.integration.phase3.test_pr3_04_application import approve, bind

    from researchbase.agent_runtime.application.agent_contracts import (
        AgentCommand,
        ChangeAgentAvailability,
    )
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    g = gateway
    install(g)
    task2 = g.p.create()
    bind(g.p, task2)
    approve(g.p, task2, 2)
    c1 = request_command(g)
    c2 = replace(
        c1,
        task_id=task2,
        command_id=new_uuid7(),
        expected_row_version=4,
        arguments=replace(g.args, invocation_id=new_uuid7()),
    )
    contexts = (g.context, replace(g.context, task_id=task2))
    writer_ready, release = Event(), Event()
    writer_pid = []
    original = SqlAlchemyUnitOfWork.commit
    main_thread = get_ident()

    def commit(uow):
        if get_ident() != main_thread and not writer_ready.is_set():
            writer_pid.append(backend_pid(uow._require_session().connection()))
            writer_ready.set()
            assert release.wait(8), "availability writer release was not signaled"
        original(uow)

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", commit)
    disabled = AgentCommand(
        g.project,
        g.owner,
        new_uuid7(),
        "change_agent_availability",
        1,
        ChangeAgentAvailability(g.args.agent_version_id, "DISABLED", "Pause fake."),
    )
    with ThreadPoolExecutor(3) as pool:
        writer = pool.submit(g.service.execute, disabled)
        assert writer_ready.wait(8)
        jobs = [
            pool.submit(g.gateway_service.request_capability_invocation, g.owner, c, ctx)
            for c, ctx in zip((c1, c2), contexts, strict=True)
        ]
        try:
            observed_wait(g.engine, blocker=writer_pid[0], query="rb_phase2_lock_project", count=2)
        finally:
            release.set()
        writer.result(timeout=10)
        for job in jobs:
            with pytest.raises(ResearchBaseError) as error:
                job.result(timeout=10)
            assert error.value.code == ErrorCode.FORBIDDEN
    with g.engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM capability_invocations")).scalar_one() == 0
    print("AVAILABILITY_RACE tasks=2 shared_agent_version=1 denied=2 effects=0")


@pytest.mark.parametrize(
    "gateway",
    [
        {"budget": {"pricing_basis": "fake-usd-v1", "max_llm_calls": 1}},
        {
            "budget": {"pricing_basis": "fake-usd-v1", "max_parallel_branches": 3},
            "max_tool_calls": 2,
            "max_parallel_invocations": 2,
        },
        {
            "budget": {"pricing_basis": "fake-usd-v1", "max_parallel_branches": 3},
            "max_parallel_invocations": 1,
        },
    ],
    indirect=True,
    ids=["last-budget-unit", "last-tool-call", "last-parallel-slot"],
)
def test_last_capacity_race_no_over_admission(gateway):
    from tests.integration.phase3.gateway_fixtures import finish

    g = gateway
    install(g)
    prior_count = 0
    if g.spec.max_tool_calls == 2:
        prior = request_command(g)
        g.gateway_service.request_capability_invocation(g.owner, prior, g.context)
        start(g)
        finish(g)
        g.args = replace(g.args, invocation_id=new_uuid7())
        prior_count = 1
    first = request_command(g)
    second = replace(
        request_command(g, invocation_id=new_uuid7()),
        expected_row_version=first.expected_row_version + 1,
    )
    with g.engine.connect() as holder, ThreadPoolExecutor(2) as pool:
        holder.execute(text(ADVISORY_SQL), {"key": f"pr301:task:{g.task}"})
        winner = pool.submit(
            g.gateway_service.request_capability_invocation, g.owner, first, g.context
        )
        waiting = observed_wait(g.engine, blocker=holder, query="pg_advisory_xact_lock")
        loser = pool.submit(
            g.gateway_service.request_capability_invocation, g.owner, second, g.context
        )
        try:
            # The second request waits behind the first's project key. Its CAS is
            # the revision the winner will commit, so contention reaches admission.
            observed_wait(g.engine, blocker=waiting.pid, query="rb_phase2_lock_project")
        finally:
            holder.commit()
        assert winner.result(timeout=10).invocation_id == g.args.invocation_id
        with pytest.raises(ResearchBaseError) as error:
            loser.result(timeout=10)
    with g.engine.connect() as conn:
        budget_calls = conn.execute(
            text("SELECT max_llm_calls FROM execution_budgets")
        ).scalar_one()
    expected = ErrorCode.INVALID_STATE_TRANSITION if budget_calls == 1 else ErrorCode.FORBIDDEN
    assert error.value.code == expected
    assert error.value.code != ErrorCode.CONCURRENT_MODIFICATION
    with g.engine.connect() as conn:
        assert (
            conn.execute(text("SELECT count(*) FROM capability_invocations")).scalar_one()
            == prior_count + 1
        )
        assert (
            conn.execute(text("SELECT count(*) FROM budget_reservations")).scalar_one()
            == prior_count + 1
        )
        assert (
            conn.execute(text("SELECT sum(llm_calls) FROM budget_reservations")).scalar_one()
            == prior_count + 1
        )
    print(
        "CAPACITY_RACE",
        first.expected_row_version,
        second.expected_row_version,
        error.value.code.value,
        str(error.value),
    )


def test_second_wait_has_its_own_fresh_expiry_check(gateway, monkeypatch):
    from threading import get_ident

    g = gateway
    install(g)
    c = request_command(g)
    main_thread = get_ident()
    acquired, checked = [], []
    with g.engine.connect() as first, g.engine.connect() as second, ThreadPoolExecutor(1) as pool:
        first.execute(text("LOCK TABLE actor_subject_bindings IN ROW EXCLUSIVE MODE"))
        second.execute(text(ADVISORY_SQL), {"key": f"pr301:task:{g.task}"})
        expiry = second.execute(text("SELECT clock_timestamp()+interval '2 seconds'")).scalar_one()

        def credential(principal, at):
            checked.append(at)
            return at < expiry

        def acquired_lock(conn, cursor, statement, params, context, many):
            if get_ident() == main_thread:
                return
            if statement == SHARE_SQL or (
                "pg_advisory_xact_lock" in statement and params.get("key") == f"pr301:task:{g.task}"
            ):
                acquired.append(conn.execute(text("SELECT clock_timestamp()")).scalar_one())

        monkeypatch.setattr(g.credentials, "is_valid", credential)
        event.listen(g.engine, "after_cursor_execute", acquired_lock)
        try:
            job = pool.submit(
                g.gateway_service.request_capability_invocation, g.owner, c, g.context
            )
            wait1 = observed_wait(g.engine, blocker=first, query=SHARE_SQL)
            assert wait1.query == SHARE_SQL
            first.commit()
            wait2 = observed_wait(
                g.engine, blocker=second, query="pg_advisory_xact_lock", pid=wait1.pid
            )
            assert wait2.pid == wait1.pid and wait2.locktype == "advisory"
            assert wait2.waitstart > wait1.waitstart
            assert (
                wait1.xact_start < expiry and wait1.waitstart < expiry and wait2.waitstart < expiry
            )
            second.execute(
                text("""
                SELECT pg_sleep(greatest(0,extract(epoch FROM (:expiry-clock_timestamp()))))
            """),
                {"expiry": expiry},
            )
            second.commit()
            with pytest.raises(ResearchBaseError) as error:
                job.result(timeout=10)
        finally:
            first.rollback()
            second.rollback()
            event.remove(g.engine, "after_cursor_execute", acquired_lock)
    assert error.value.code == ErrorCode.FORBIDDEN
    assert len(acquired) == 2 and acquired[0] < expiry <= acquired[1] <= checked[-1]
    assert any(acquired[0] <= stamp < expiry for stamp in checked)
    assert checked[-1] > expiry
    print(
        "SECOND_WAIT_EXPIRY",
        dict(
            tx_started_at=wait1.xact_start,
            first_wait_started_at=wait1.waitstart,
            first_acquired_at=acquired[0],
            second_wait_started_at=wait2.waitstart,
            acquired_at=acquired[1],
            checked_at=checked[-1],
            expiry_at=expiry,
        ),
    )


def test_each_row_wait_and_complete_db_lock_order(gateway):
    from contextlib import ExitStack
    from threading import get_ident

    from tests.integration.phase3.gateway_fixtures import revision

    from researchbase.agent_runtime.application.gateway_contracts import (
        GatewayCommand,
        StartInvocationArguments,
    )
    from researchbase.persistence.task_safety_repository import SAFETY_TABLES

    g = gateway
    node = new_uuid7()
    g.p.service.execute(
        g.owner,
        g.p.command(
            "create_task_plan",
            g.task,
            revision(g),
            {
                "nodes": [{"step_id": str(node), "step_type": "PLAN", "ordinal": 1}],
                "edges": [],
            },
        ),
    )
    g.registration = replace(g.registration, expected_row_version=revision(g))
    request_invocation(g)
    c = GatewayCommand(
        g.project,
        g.task,
        new_uuid7(),
        revision(g),
        "start_capability_invocation",
        StartInvocationArguments(g.args.invocation_id, 1, "Observe every row wait."),
    )
    tables = [
        "research_tasks",
        "research_task_steps",
        "human_checkpoints",
        "agent_availability",
        "capability_invocations",
    ]
    trace, waited = [], []
    main_thread = get_ident()

    def record(conn, cursor, statement, params, context, many):
        if get_ident() != main_thread:
            trace.append((" ".join(statement.split()), dict(params)))

    with ExitStack() as stack, ThreadPoolExecutor(1) as pool:
        holders = [stack.enter_context(g.engine.connect()) for _ in tables]
        for table, holder in zip(tables, holders, strict=True):
            field, identity = (
                ("agent_version_id", g.args.agent_version_id)
                if table == "agent_availability"
                else ("id", node)
                if table == "research_task_steps"
                else ("research_task_id", g.task)
                if table == "human_checkpoints"
                else ("id", g.args.invocation_id)
                if table == "capability_invocations"
                else ("id", g.task)
            )
            holder.execute(
                text(f"SELECT * FROM {table} WHERE {field}=:id FOR UPDATE"), {"id": identity}
            )
        event.listen(g.engine, "before_cursor_execute", record)
        try:
            job = pool.submit(g.gateway_service.start_capability_invocation, g.owner, c, g.context)
            pid = None
            for table, holder in zip(tables, holders, strict=True):
                wait = observed_wait(g.engine, blocker=holder, query=f"FROM {table}", pid=pid)
                pid = wait.pid
                waited.append((table, wait.pid, wait.waitstart))
                holder.commit()
            assert job.result(timeout=10).resulting_invocation_revision == 2
        finally:
            for holder in holders:
                holder.rollback()
            event.remove(g.engine, "before_cursor_execute", record)
    first_share = next(i for i, (sql, _) in enumerate(trace) if sql == SHARE_SQL)
    trace = trace[first_share:]
    locks = []
    for sql, params in trace:
        if sql == SHARE_SQL:
            locks.append("SHARE")
        elif "rb_phase2_lock_project" in sql:
            locks.append("project")
        elif "pg_advisory_xact_lock" in sql:
            locks.append(params["key"].split(":", 2)[0:2])
        elif "FOR UPDATE" in sql and sql.startswith("SELECT"):
            locks.append(sql.split(" FROM ")[1].split()[0])
    assert locks == [
        "SHARE",
        "project",
        ["pr301", "command"],
        ["pr301", "task"],
        ["pr302", "actor"],
        ["pr302", "version"],
        "research_tasks",
        "research_task_steps",
        "human_checkpoints",
        "agent_availability",
        "capability_invocations",
    ]
    safety_reads = [
        sql.split(" FROM ")[1].split()[0]
        for sql, _ in trace
        if sql.startswith("SELECT * FROM ") and sql.split(" FROM ")[1].split()[0] in SAFETY_TABLES
    ]
    assert safety_reads[:8] == list(SAFETY_TABLES)
    assert len({pid for _, pid, _ in waited}) == 1
    assert [stamp for _, _, stamp in waited] == sorted(stamp for _, _, stamp in waited)
    print("ROW_WAIT_ORDER", waited, "LOCK_ORDER", locks)


def change_before_waited_start(g, monkeypatch, kind):
    from threading import Event

    from tests.integration.phase3.gateway_fixtures import revision
    from tests.integration.phase3.test_pr3_00_bootstrap import _rows
    from tests.integration.phase3.test_pr3_04_application import command, service

    from researchbase.agent_runtime.application.gateway_contracts import (
        GatewayCommand,
        StartInvocationArguments,
    )
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    request_invocation(g)
    before_revision = revision(g)
    mutation = (
        g.p.command(
            "cancel_research_task", g.task, before_revision, {"reason": "Stop before start."}
        )
        if kind == "stop"
        else command(
            g.p,
            g.task,
            before_revision,
            "request_human_checkpoint",
            {
                "checkpoint_id": str(new_uuid7()),
                "step_id": None,
                "checkpoint_type": "plan_review",
                "reason": "Require a new checkpoint before start.",
            },
        )
    )
    c = GatewayCommand(
        g.project,
        g.task,
        new_uuid7(),
        before_revision + 1,
        "start_capability_invocation",
        StartInvocationArguments(g.args.invocation_id, 1, "Wait for policy change."),
    )
    ready, release = Event(), Event()
    writer_pid = []
    original = SqlAlchemyUnitOfWork.commit

    def commit(uow):
        if not ready.is_set():
            writer_pid.append(backend_pid(uow._require_session().connection()))
            ready.set()
            assert release.wait(8)
        original(uow)

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", commit)
    with ThreadPoolExecutor(2) as pool:
        writer = pool.submit(
            g.p.service.execute if kind == "stop" else service(g.p).execute, g.owner, mutation
        )
        assert ready.wait(8)
        reader = pool.submit(g.gateway_service.start_capability_invocation, g.owner, c, g.context)
        try:
            waited = observed_wait(g.engine, blocker=writer_pid[0], query="rb_phase2_lock_project")
        finally:
            release.set()
        writer.result(timeout=10)
        committed = _rows(g.engine)
        with pytest.raises(ResearchBaseError) as error:
            reader.result(timeout=10)
    assert error.value.code == ErrorCode.INVALID_STATE_TRANSITION
    assert "stale" not in str(error.value)
    assert _rows(g.engine) == committed
    assert revision(g) == before_revision + 1
    with g.engine.connect() as conn:
        row = conn.execute(text("SELECT status,start_receipt_id FROM capability_invocations")).one()
        assert tuple(row) == ("REQUESTED", None)
    print(
        "WAITED_CHANGE",
        kind,
        waited.pid,
        waited.waitstart,
        error.value.code.value,
        str(error.value),
    )


def test_stop_change_during_observed_wait(gateway, monkeypatch):
    change_before_waited_start(gateway, monkeypatch, "stop")


def test_checkpoint_change_during_observed_wait(gateway, monkeypatch):
    change_before_waited_start(gateway, monkeypatch, "checkpoint")


@pytest.mark.parametrize(
    "gateway", [{"budget": {"pricing_basis": "fake-usd-v1", "max_llm_calls": 1}}], indirect=True
)
@pytest.mark.parametrize("kind", ["prior", "additional"])
def test_exact_cap_start_with_prior_and_additional_stops(gateway, kind):
    from tests.integration.phase3.gateway_fixtures import revision
    from tests.integration.phase3.test_pr3_00_bootstrap import _rows

    g = gateway
    if kind == "prior":
        install(g)
    else:
        request_invocation(g)
    g.p.service.execute(
        g.owner,
        g.p.command(
            "cancel_research_task",
            g.task,
            revision(g),
            {
                "reason": "Historical human stop precedes the attempted admission or start.",
            },
        ),
    )
    stopped = _rows(g.engine)
    with pytest.raises(ResearchBaseError) as error:
        if kind == "prior":
            g.gateway_service.request_capability_invocation(g.owner, request_command(g), g.context)
        else:
            start(g)
    assert error.value.code == ErrorCode.INVALID_STATE_TRANSITION
    assert _rows(g.engine) == stopped
    with g.engine.connect() as conn:
        expected = int(kind == "additional")
        assert (
            conn.execute(text("SELECT count(*) FROM budget_reservations")).scalar_one() == expected
        )
        assert (
            conn.execute(
                text("SELECT count(*) FROM capability_invocation_events WHERE event_type='STARTED'")
            ).scalar_one()
            == 0
        )
