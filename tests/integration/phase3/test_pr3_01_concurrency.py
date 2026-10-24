# ruff: noqa: E501
"""Real two-session lock waits, fresh authorization, snapshot reads and retries."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker
from tests.integration.phase3.conftest import Credentials, raw_edge

from researchbase.agent_runtime.application.research_task import ResearchTaskService
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7
from researchbase.persistence.research_task_repository import (
    SHARE_SQL,
    SqlAlchemyResearchTaskRepository,
)
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


def wait_for_lock(engine, pid, seconds=5):
    deadline = monotonic() + seconds
    while monotonic() < deadline:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT clock_timestamp(), EXISTS(SELECT 1 FROM pg_locks WHERE pid=:pid AND NOT granted)"
                ),
                {"pid": pid},
            ).one()
        if row[1]:
            return row[0]
        Event().wait(0.005)
    raise AssertionError("backend did not enter a real pg_locks wait")


def run_waiting(planning, operation, blocker, *, during=None):
    engine = create_engine(planning.url)
    statements = []
    started = Event()
    pids = []

    @event.listens_for(engine, "before_cursor_execute")
    def capture(conn, cursor, statement, params, context, many):
        if not pids:
            pids.append(conn.connection.driver_connection.info.backend_pid)
            started.set()
        statements.append(statement)

    sessions = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    service = ResearchTaskService(
        lambda: SqlAlchemyUnitOfWork(sessions), Credentials(), planning.store
    )
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(operation, service)
            assert started.wait(5)
            waited = wait_for_lock(planning.engine, pids[0])
            if during is not None:
                during(service, waited, pids[0])
            blocker.commit()
            result = future.result(timeout=10)
        assert statements[0] == SHARE_SQL
        assert "rb_phase2_lock_project" in statements[1]
        return result, waited
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "first,second",
    (
        ("seal_task_plan", "add_task_step_dependency"),
        ("cancel_research_task", "add_task_step_dependency"),
        ("add_task_step_dependency", "cancel_research_task"),
        ("add_task_step_dependency", "seal_task_plan"),
    ),
)
def test_two_session_same_revision_one_winner(planning, monkeypatch, first, second):
    task, _ = planning.plan()
    graph = planning.service.get_task_graph(planning.principal, planning.project, task)
    edge = {"predecessor_id": str(graph.nodes[0].id), "dependent_id": str(graph.nodes[1].id)}

    def cmd(name):
        return planning.command(
            name,
            task,
            2,
            edge
            if name == "add_task_step_dependency"
            else {"reason": "Stop"}
            if name == "cancel_research_task"
            else {},
        )

    held = Event()
    release = Event()
    force = SqlAlchemyResearchTaskRepository.force_constraints

    def gate(self):
        force(self)
        if not held.is_set():
            held.set()
            assert release.wait(8)

    monkeypatch.setattr(SqlAlchemyResearchTaskRepository, "force_constraints", gate)
    with ThreadPoolExecutor(max_workers=1) as pool:
        first_result = pool.submit(planning.service.execute, planning.principal, cmd(first))
        assert held.wait(5)

        class Release:
            def commit(self):
                release.set()
                first_result.result(timeout=5)

        def operation(service):
            try:
                service.execute(planning.principal, cmd(second))
            except ResearchBaseError as exc:
                return exc.code
            raise AssertionError("both commands committed")

        result, _ = run_waiting(planning, operation, Release())
    assert result == ErrorCode.CONCURRENT_MODIFICATION
    assert (
        planning.service.get_research_task(planning.principal, planning.project, task).row_version
        == 3
    )


@pytest.mark.parametrize("direct", (False, True), ids=("application", "normal-role-sql"))
def test_opposite_edges_cannot_both_commit(planning, normal_engine, direct):
    task, _ = planning.plan()
    graph = planning.service.get_task_graph(planning.principal, planning.project, task)
    a, b = [n.id for n in graph.nodes]
    engine = normal_engine if direct else planning.engine
    with Session(engine) as first:
        raw_edge(SqlAlchemyResearchTaskRepository(first), planning, task, a, b)
        if direct:
            second_engine = normal_engine
            pids = []
            ready = Event()

            @event.listens_for(second_engine, "before_cursor_execute")
            def capture(conn, *args):
                if not pids:
                    pids.append(conn.connection.driver_connection.info.backend_pid)
                    ready.set()

            try:
                with ThreadPoolExecutor(max_workers=1) as pool:

                    def opposite():
                        try:
                            with Session(second_engine) as second, second.begin():
                                raw_edge(
                                    SqlAlchemyResearchTaskRepository(second), planning, task, b, a
                                )
                        except DBAPIError as exc:
                            return getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
                        raise AssertionError("opposite edge committed")

                    future = pool.submit(opposite)
                    assert ready.wait(5)
                    wait_for_lock(planning.engine, pids[0])
                    first.commit()
                    assert future.result(timeout=10) == "pr301_validation"
            finally:
                event.remove(second_engine, "before_cursor_execute", capture)
        else:
            command = planning.command(
                "add_task_step_dependency",
                task,
                2,
                {"predecessor_id": str(b), "dependent_id": str(a)},
            )

            def operation(service):
                try:
                    service.execute(planning.principal, command)
                except ResearchBaseError as exc:
                    return exc.code
                raise AssertionError("opposite edge committed")

            result, _ = run_waiting(planning, operation, first)
            assert result == ErrorCode.CONCURRENT_MODIFICATION
    assert (
        len(planning.service.get_task_graph(planning.principal, planning.project, task).edges) == 1
    )


def test_lock_free_repeatable_read_during_writer(planning):
    task, _ = planning.plan()
    before = planning.service.get_task_graph(planning.principal, planning.project, task)
    with planning.factory() as reader:
        reader.begin_formal_read()
        initial = planning.service._graph(reader, planning.project, task)
        with planning.factory() as writer:
            writer.begin_research_task()
            repo = writer.research_tasks
            repo.lock_write(planning.project, planning.principal.actor_id, new_uuid7(), task)
            # Reads finish while all writer exclusion locks remain held.
            with ThreadPoolExecutor(max_workers=1) as pool:
                assert (
                    pool.submit(
                        planning.service.get_task_graph, planning.principal, planning.project, task
                    ).result(timeout=3)
                    == before
                )
        planning.service.execute(planning.principal, planning.command("seal_task_plan", task, 2))
        assert planning.service._graph(reader, planning.project, task) == initial
    assert (
        planning.service.get_research_task(planning.principal, planning.project, task).row_version
        == 3
    )


@pytest.mark.parametrize("wait_kind", ("share", "project", "task"))
def test_actual_wait_crosses_credential_expiry(planning, wait_kind, tmp_path):
    task = planning.create()
    command = planning.command(
        "create_task_plan",
        task,
        1,
        {"nodes": [{"step_id": str(new_uuid7()), "step_type": "PLAN", "ordinal": 1}]},
    )
    engine = create_engine(planning.url)
    pids = []
    ready = Event()
    checked = []
    acquired = []
    with planning.engine.connect() as blocker:
        if wait_kind == "share":
            blocker.execute(text("LOCK TABLE actors IN ROW EXCLUSIVE MODE"))
        elif wait_kind == "project":
            blocker.execute(text("SELECT rb_phase2_lock_project(:p)"), {"p": planning.project})
        else:
            blocker.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:k,0))"),
                {"k": f"pr301:task:{task}"},
            )
        expiry = blocker.execute(
            text("SELECT clock_timestamp()+interval '250 milliseconds'")
        ).scalar_one()

        class Expiring:
            def is_valid(self, principal, at):
                checked.append(at)
                return at < expiry

        @event.listens_for(engine, "before_cursor_execute")
        def capture(conn, *args):
            if not pids:
                pids.append(conn.connection.driver_connection.info.backend_pid)
                ready.set()

        @event.listens_for(engine, "after_cursor_execute")
        def acquired_time(conn, cursor, statement, params, context, many):
            match = (
                (wait_kind == "share" and statement == SHARE_SQL)
                or (wait_kind == "project" and "rb_phase2_lock_project" in statement)
                or (wait_kind == "task" and params.get("key") == f"pr301:task:{task}")
            )
            if match:
                with conn.connection.driver_connection.cursor() as observed:
                    acquired.append(observed.execute("SELECT clock_timestamp()").fetchone()[0])

        sessions = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        service = ResearchTaskService(
            lambda: SqlAlchemyUnitOfWork(sessions), Expiring(), planning.store
        )
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:

                def attempt():
                    try:
                        service.execute(planning.principal, command)
                    except ResearchBaseError as exc:
                        return exc.code

                future = pool.submit(attempt)
                assert ready.wait(5)
                wait_started = wait_for_lock(planning.engine, pids[0])
                with planning.engine.connect() as monitor:
                    tx = monitor.execute(
                        text("SELECT xact_start FROM pg_stat_activity WHERE pid=:pid"),
                        {"pid": pids[0]},
                    ).scalar_one()
                    while True:
                        released = monitor.execute(text("SELECT clock_timestamp()")).scalar_one()
                        if released >= expiry:
                            break
                        Event().wait(0.005)
                blocker.commit()
                assert future.result(timeout=10) == ErrorCode.FORBIDDEN
            assert tx < expiry and wait_started < expiry <= released <= acquired[-1] <= checked[-1]
            assert (
                planning.service.get_research_task(
                    planning.principal, planning.project, task
                ).row_version
                == 1
            )
            evidence = {
                "tx_started_at": str(tx),
                "expiry_at": str(expiry),
                "lock_wait_started_at": str(wait_started),
                "lock_acquired_at": str(acquired[-1]),
                "authorization_checked_at": str(checked[-1]),
                "outcome": "FORBIDDEN",
                "protected_new_rows": 0,
            }
            (tmp_path / f"{wait_kind}-expiry.txt").write_text(str(evidence))
            print("PR301_EXPIRY", wait_kind, evidence)
        finally:
            engine.dispose()


@pytest.mark.parametrize(
    "sqlstate,attempts", (("40001", 3), ("40P01", 3), ("55P03", 1), ("57014", 1))
)
def test_retry_only_transient_whole_transactions(planning, monkeypatch, sqlstate, attempts):
    import psycopg

    calls = []

    def rejected(self):
        calls.append(self)
        original = psycopg.errors.lookup(sqlstate)("private SQL credential material")
        raise DBAPIError("private SQL", {}, original)

    monkeypatch.setattr(SqlAlchemyResearchTaskRepository, "force_constraints", rejected)
    command = planning.command()
    with pytest.raises(ResearchBaseError) as caught:
        planning.service.execute(planning.principal, command)
    assert caught.value.code == ErrorCode.CONCURRENT_MODIFICATION and len(calls) == attempts
    assert len({id(r) for r in calls}) == attempts
    assert "private" not in caught.value.message
    assert planning.service.replay(planning.principal, command) is None


def test_membership_revocation_during_first_share_wait_denies_write(planning):
    from tests.integration.phase2.test_pr2_00_ownership import _add_owner

    from researchbase.domain.phase2_identity import VerifiedPrincipal

    actor = new_uuid7()
    with planning.engine.begin() as conn:
        now = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
        membership, role = _add_owner(
            conn,
            actor_id=actor,
            project_id=planning.project,
            now=now,
            event_kind="ACTIVATED",
            request_id=new_uuid7(),
        )
    principal = VerifiedPrincipal(
        actor, "test-deployment", "OS_UID", str(actor.int), f"uid:{actor.int}", now
    )
    command = planning.command()
    with planning.engine.connect() as blocker:
        blocker.execute(text("SELECT rb_phase2_lock_project(:p)"), {"p": planning.project})
        at = blocker.execute(text("SELECT clock_timestamp()")).scalar_one()
        blocker.execute(
            text(
                "UPDATE project_memberships SET status='SUSPENDED',row_version=row_version+1 WHERE id=:id"
            ),
            {"id": membership},
        )
        blocker.execute(
            text(
                "UPDATE project_role_assignments SET effective_until=:at,row_version=row_version+1 WHERE id=:id"
            ),
            {"id": role, "at": at},
        )
        blocker.execute(
            text(
                "INSERT INTO project_role_events (id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id) VALUES (:id,:role,:actor,'CLOSED',:at,'Test revocation',:request)"
            ),
            {"id": new_uuid7(), "role": role, "actor": actor, "at": at, "request": new_uuid7()},
        )
        blocker.execute(
            text(
                "INSERT INTO project_membership_events (id,membership_id,event_kind,prior_status,new_status,actor_id,occurred_at,reason,request_id) VALUES (:id,:membership,'SUSPENDED','ACTIVE','SUSPENDED',:actor,:at,'Test revocation',:request)"
            ),
            {
                "id": new_uuid7(),
                "membership": membership,
                "actor": actor,
                "at": at,
                "request": new_uuid7(),
            },
        )

        def operation(service):
            try:
                service.execute(principal, command)
            except ResearchBaseError as exc:
                return exc.code

        result, _ = run_waiting(planning, operation, blocker)
    assert result == ErrorCode.FORBIDDEN
    with planning.engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM research_tasks WHERE id=:id"), {"id": command.task_id}
            ).scalar_one()
            == 0
        )


def test_source_link_revocation_attempt_waits_for_planning_share(
    planning, normal_engine, scientific_inputs, monkeypatch
):
    command = planning.command(
        arguments={
            "task_type": "OTHER",
            "objective": "Inspect source",
            "strategy_id": "fixed",
            "strategy_version": "1",
            "inputs": [{"type": "SOURCE_VERSION", "id": str(scientific_inputs["SOURCE_VERSION"])}],
        }
    )
    held = Event()
    release = Event()
    ready = Event()
    pids = []
    force = SqlAlchemyResearchTaskRepository.force_constraints

    def gate(self):
        force(self)
        held.set()
        assert release.wait(8)

    monkeypatch.setattr(SqlAlchemyResearchTaskRepository, "force_constraints", gate)

    def capture(conn, *args):
        if not pids:
            pids.append(conn.connection.driver_connection.info.backend_pid)
            ready.set()

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            writer = pool.submit(planning.service.execute, planning.principal, command)
            assert held.wait(5)
            event.listen(normal_engine, "before_cursor_execute", capture)

            def revoke():
                try:
                    with normal_engine.begin() as conn:
                        conn.execute(
                            text("DELETE FROM literature_source_project_links WHERE project_id=:p"),
                            {"p": planning.project},
                        )
                except DBAPIError:
                    return "owning immutable link denied"
                raise AssertionError("accepted source link unexpectedly revocable")

            revoker = pool.submit(revoke)
            assert ready.wait(5)
            wait_for_lock(planning.engine, pids[0])
            release.set()
            writer.result(timeout=10)
            assert revoker.result(timeout=10) == "owning immutable link denied"
    finally:
        release.set()
        event.remove(normal_engine, "before_cursor_execute", capture)
    assert planning.service.get_research_task(
        planning.principal, planning.project, command.task_id
    ).inputs
