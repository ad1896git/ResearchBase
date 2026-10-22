import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest
from sqlalchemy import create_engine, event, text
from tests.integration.phase3.agent_fixtures import enrollment, register

from researchbase.agent_runtime.application.agent_contracts import ChangeAgentAvailability
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7
from researchbase.persistence.agent_version_repository import ENROLLMENT_SQL, VERSION_SQL


def wait_for_waiters(engine, count):
    observer = create_engine(engine.url)
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        with observer.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT pid,query,wait_event,xact_start,query_start,"
                    "clock_timestamp() AS observed_at "
                    "FROM pg_stat_activity WHERE "
                    "datname=current_database() AND wait_event_type='Lock' AND query LIKE 'LOCK "
                    "TABLE actor_subject_bindings%'"
                )
            ).all()
        if len(rows) >= count:
            print("observed lock waiters", [(r.pid, r.wait_event) for r in rows])
            observer.dispose()
            return rows
        time.sleep(0.01)
    observer.dispose()
    raise AssertionError("required actual lock wait not observed")


@pytest.mark.parametrize("different_project", [False, True])
def test_two_enrollments_serialize_without_retry(agents, different_project):
    first = enrollment(agents)
    second = enrollment(agents)
    if different_project:
        project = agents.identity.create_project_with_owner(
            agents.owner, name="second enrollment project", request_id=new_uuid7()
        )
        second = enrollment(agents, project_id=project)
        second = replace(
            second,
            arguments=replace(
                second.arguments,
                enrollment_proof=replace(second.arguments.enrollment_proof, project_id=project),
            ),
        )
        agents.verifier.accepted[second.command_id] = second.material()
    statements = {}

    def trace(conn, cursor, statement, params, context, many):
        statements.setdefault(threading.get_ident(), []).append(statement)

    event.listen(agents.engine, "before_cursor_execute", trace)
    try:
        with agents.engine.connect() as holder:
            tx = holder.begin()
            holder.execute(text(ENROLLMENT_SQL))
            with ThreadPoolExecutor(2) as pool:
                jobs = [pool.submit(agents.service.execute, c) for c in (first, second)]
                wait_for_waiters(agents.engine, 2)
                released = time.monotonic()
                tx.commit()
                results = [j.result(timeout=10) for j in jobs]
                assert all(not r.replayed for r in results)
                print("both committed after release seconds", time.monotonic() - released)
        traces = [sql for tid, sql in statements.items() if tid != threading.get_ident()]
        assert len(traces) == 2
        for sql in traces:
            assert sql[:2] == [ENROLLMENT_SQL, "LOCK TABLE projects IN SHARE MODE"]
            print("enrollment first SQL", sql[:2], "attempts", sql.count(ENROLLMENT_SQL))
            assert sum(s == ENROLLMENT_SQL for s in sql) == 1
            assert not any("LOCK TABLE" in s and "artifact" in s for s in sql)
    finally:
        event.remove(agents.engine, "before_cursor_execute", trace)


def test_enrollment_blocks_version_at_first_common_table(agents):
    enrollment_command = enrollment(agents)
    agents.service.execute(enrollment_command)
    reg = register(agents, enrollment_command.arguments.actor_id)
    with agents.engine.connect() as holder:
        tx = holder.begin()
        holder.execute(text(ENROLLMENT_SQL))
        with ThreadPoolExecutor(1) as pool:
            job = pool.submit(agents.service.execute, reg)
            rows = wait_for_waiters(agents.engine, 1)
            assert rows[0].query == VERSION_SQL
            tx.commit()
            assert job.result(timeout=10).resulting_revision == 1


def test_availability_cas_one_winner(agents):
    cmd = enrollment(agents)
    agents.service.execute(cmd)
    reg = register(agents, cmd.arguments.actor_id)
    agents.service.execute(reg)
    changes = [
        replace(
            reg,
            operation="change_agent_availability",
            command_id=new_uuid7(),
            expected_revision=1,
            arguments=ChangeAgentAvailability(reg.arguments.agent_version_id, status, "CAS race"),
        )
        for status in ("DISABLED", "RETIRED")
    ]

    def execute(command):
        try:
            return agents.service.execute(command)
        except ResearchBaseError as exc:
            return exc.code

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(execute, changes))
    assert sum(r == ErrorCode.CONCURRENT_MODIFICATION for r in results) == 1
    with agents.engine.connect() as conn:
        assert (
            conn.execute(text("SELECT count(*) FROM agent_availability_events")).scalar_one() == 2
        )


@pytest.mark.parametrize("credential", ["subject", "operator", "owner"])
def test_credential_expiry_during_actual_enrollment_lock_wait(agents, monkeypatch, credential):
    command = enrollment(agents)
    acquired = []

    def acquired_prefix(conn, cursor, statement, params, context, many):
        if statement == "LOCK TABLE projects IN SHARE MODE":
            acquired.append(conn.execute(text("SELECT clock_timestamp()")).scalar_one())

    event.listen(agents.engine, "after_cursor_execute", acquired_prefix)
    with agents.engine.connect() as holder:
        tx = holder.begin()
        holder.execute(text(ENROLLMENT_SQL))
        expires = holder.execute(
            text("SELECT clock_timestamp()+interval '0.4 second'")
        ).scalar_one()
        checks = []

        def valid(principal=None, at=None, **kwargs):
            identity = principal if principal is not None else kwargs.get("subject")
            assert identity is not None
            target = (
                command.arguments.subject
                if credential == "subject"
                else agents.operator
                if credential == "operator"
                else agents.owner
            )
            checks.append(at)
            return identity.credential_id != target.credential_id or at < expires

        verifier = (
            agents.identity._subject_credential_verifier
            if credential == "subject"
            else agents.credentials
        )
        monkeypatch.setattr(verifier, "is_valid", valid)
        with ThreadPoolExecutor(1) as pool:
            future = pool.submit(agents.service.execute, command)
            rows = wait_for_waiters(agents.engine, 1)
            assert rows[0].xact_start < expires
            assert rows[0].query_start < expires
            assert rows[0].observed_at < expires
            # Observe database expiry before releasing the required lock.
            while holder.execute(text("SELECT clock_timestamp()")).scalar_one() < expires:
                time.sleep(0.01)
            acquired_after = holder.execute(text("SELECT clock_timestamp()")).scalar_one()
            tx.commit()
            with pytest.raises(ResearchBaseError) as exc:
                future.result(timeout=10)
            assert exc.value.code in {
                ErrorCode.SUBJECT_BINDING_UNPROVEN,
                ErrorCode.FORBIDDEN,
                ErrorCode.OWNER_CREDENTIAL_UNAVAILABLE,
            }
        assert checks and acquired and max(checks) >= acquired[0] >= acquired_after >= expires
    event.remove(agents.engine, "after_cursor_execute", acquired_prefix)
    with agents.engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM agent_command_receipts")).scalar_one() == 0
    print(
        "credential expiry",
        credential,
        "tx_started_at",
        rows[0].xact_start.isoformat(),
        "lock_wait_started_at",
        rows[0].query_start.isoformat(),
        "expiry_at",
        expires.isoformat(),
        "lock_acquired_at",
        acquired[0].isoformat(),
        "released_at",
        acquired_after.isoformat(),
        "authorization_checked_at",
        max(checks).isoformat(),
        "protected_receipts",
        0,
    )
