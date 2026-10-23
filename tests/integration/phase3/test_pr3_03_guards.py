"""Ordinary-role immutable and immediate guard denial, never trigger bypasses."""

from typing import Any, cast

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from tests.integration.phase3.gateway_fixtures import request_invocation, start
from tests.integration.phase3.test_pr3_00_bootstrap import _rows


@pytest.mark.parametrize(
    "table",
    [
        "agent_tool_policies",
        "agent_tool_policy_permissions",
        "capability_invocations",
        "capability_invocation_refs",
        "capability_invocation_events",
    ],
)
@pytest.mark.parametrize("mutation", ["noop", "update", "delete"])
def test_immutable_noop_update_delete(gateway, table, mutation):
    g = gateway
    request_invocation(g)
    before = _rows(g.engine)
    if mutation == "delete":
        sql = f"DELETE FROM {table}"
    elif mutation == "noop":
        sql = f"UPDATE {table} SET id=id"
    else:
        sql = f"UPDATE {table} SET id=:id"
    with g.engine.begin() as conn, pytest.raises(DBAPIError) as error:
        conn.execute(text(sql), {"id": g.args.invocation_id})
    assert cast(Any, error.value.orig).sqlstate == "23514"
    assert _rows(g.engine) == before


@pytest.mark.parametrize(
    "table",
    [
        "agent_tool_policies",
        "agent_tool_policy_permissions",
        "capability_invocations",
        "capability_invocation_refs",
        "capability_invocation_events",
    ],
)
def test_committed_receipt_append_denied(gateway, table):
    g = gateway
    request_invocation(g)
    before = _rows(g.engine)
    with g.engine.begin() as conn, pytest.raises(DBAPIError) as error:
        conn.execute(text(f"INSERT INTO {table} SELECT * FROM {table}"))
    assert cast(Any, error.value.orig).sqlstate == "23514"
    assert _rows(g.engine) == before


def test_naked_revision_denied_at_deferred_guard(gateway):
    g = gateway
    before = _rows(g.engine)
    with pytest.raises(DBAPIError) as error, g.engine.begin() as conn:
        conn.execute(
            text("UPDATE research_tasks SET row_version=row_version+1 WHERE id=:id"), {"id": g.task}
        )
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert cast(Any, error.value.orig).sqlstate == "23514"
    assert _rows(g.engine) == before


def test_second_start_and_delete_running_denied(gateway):
    g = gateway
    request_invocation(g)
    start(g)
    with g.engine.begin() as conn, pytest.raises(DBAPIError):
        conn.execute(
            text("DELETE FROM capability_invocations WHERE id=:id"), {"id": g.args.invocation_id}
        )


def test_legacy_receipt_event_and_settlement_immutable_after_gateway_finish(gateway):
    from tests.integration.phase3.gateway_fixtures import finish

    from researchbase.foundation.ids import new_uuid7

    g = gateway
    request_invocation(g)
    start(g)
    finish(g)
    before = _rows(g.engine)
    for table in (
        "research_task_command_receipts",
        "research_task_events",
        "budget_usage_records",
    ):
        with g.engine.connect() as conn:
            assert (
                conn.execute(
                    text(f"SELECT count(*) FROM {table} WHERE research_task_id=:task"),
                    {"task": g.task},
                ).scalar_one()
                > 0
            )
        for operation in ("noop", "update", "delete"):
            if operation == "delete":
                sql = f"DELETE FROM {table} WHERE research_task_id=:task"
            else:
                value = "id" if operation == "noop" else ":new_id"
                sql = f"UPDATE {table} SET id={value} WHERE research_task_id=:task"
            with g.engine.begin() as conn, pytest.raises(DBAPIError) as error:
                conn.execute(text(sql), {"task": g.task, "new_id": new_uuid7()})
            assert cast(Any, error.value.orig).sqlstate == "23514"
            assert cast(Any, error.value.orig).diag.constraint_name == "pr301_immutable"
            assert _rows(g.engine) == before
            print("LEGACY_IMMUTABLE_DENIAL", table, operation, "pr301_immutable")


@pytest.mark.parametrize("gateway", ["maximum"], indirect=True)
def test_maximum_sets_exactly_once_deferred_guards(gateway, monkeypatch):
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    g = gateway
    from researchbase.persistence.capability_gateway_repository import SqlAlchemyGatewayRepository

    original = SqlAlchemyUnitOfWork.commit
    original_lock = SqlAlchemyGatewayRepository.lock_gateway
    observed, baselines = [], {}

    def counts(session):
        return dict(session.execute(text(GUARD_COUNTS_SQL)).all())

    def lock(repo, *args, **kwargs):
        original_lock(repo, *args, **kwargs)
        baselines[id(repo._session)] = counts(repo._session)

    def commit(uow):
        session = uow._require_session()
        if id(session) not in baselines:
            return original(uow)
        baseline = baselines[id(session)]
        observed.append(
            {name: count - baseline.get(name, 0) for name, count in counts(session).items()}
        )
        original(uow)

    monkeypatch.setattr(SqlAlchemyGatewayRepository, "lock_gateway", lock)
    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", commit)
    request_invocation(g)
    assert len(observed) == 2
    for counts in observed:
        assert counts == {
            "pr301_graph_final_guard": 1,
            "pr301_receipt_complete": 1,
            "pr303_validate_gateway": 1,
        }
    with g.engine.connect() as conn:
        assert (
            conn.execute(text("SELECT count(*) FROM agent_tool_policy_permissions")).scalar_one()
            == 256
        )
        assert (
            conn.execute(text("SELECT count(*) FROM capability_invocation_refs")).scalar_one()
            == 256
        )
    print("MAXIMUM_GUARDS permissions=256 refs=256", observed)


GUARD_COUNTS_SQL = """
SELECT funcname,calls FROM pg_stat_xact_user_functions
WHERE funcname IN (
    'pr301_graph_final_guard','pr301_receipt_complete','pr303_validate_gateway'
)
"""


@pytest.mark.parametrize(
    "case",
    [
        "missing_invocation",
        "missing_reservation",
        "missing_event",
        "missing_link",
        "extra_reservation",
        "wrong_reservation",
        "nullable_step",
        "missing_usage",
        "wrong_usage",
        "multiple_flush",
        "immutable_in_construction",
    ],
)
def test_full_protocol_tampering_is_atomic(gateway, monkeypatch, case):
    from tests.integration.phase3.gateway_fixtures import finish, install, request_command, revision

    from researchbase.foundation.errors import ResearchBaseError
    from researchbase.foundation.ids import new_uuid7
    from researchbase.persistence.capability_gateway_repository import SqlAlchemyGatewayRepository

    g = gateway
    step = None
    if case == "nullable_step":
        step = new_uuid7()
        c = g.p.command(
            "create_task_plan",
            g.task,
            revision(g),
            {
                "nodes": [{"step_id": str(step), "step_type": "PLAN", "ordinal": 1}],
                "edges": [],
            },
        )
        g.p.service.execute(g.owner, c)
        from dataclasses import replace

        g.registration = replace(g.registration, expected_row_version=revision(g))
    lifecycle = case in ("missing_usage", "wrong_usage", "multiple_flush")
    if lifecycle:
        request_invocation(g)
        if case != "multiple_flush":
            start(g)
    else:
        install(g)
    before = _rows(g.engine)
    insert = SqlAlchemyGatewayRepository.insert
    update = SqlAlchemyGatewayRepository.update_invocation
    missing = {
        "missing_invocation": "capability_invocations",
        "missing_reservation": "budget_reservations",
        "missing_event": "capability_invocation_events",
        "missing_link": "research_task_receipt_events",
        "missing_usage": "budget_usage_records",
    }.get(case)
    reached = []

    def tamper_insert(repo, table, row):
        if table == missing:
            reached.append(case)
            return
        if table == "budget_reservations" and case == "nullable_step":
            row = dict(row, step_id=step)
            reached.append(case)
        if table == "capability_invocations" and case == "wrong_reservation":
            row = dict(row, reservation_id=new_uuid7())
            reached.append(case)
        insert(repo, table, row)
        if table == "budget_reservations" and case == "extra_reservation":
            reached.append(case)
            insert(repo, table, dict(row, id=new_uuid7(), operation_id=new_uuid7()))
        if table == "capability_invocation_refs" and case == "immutable_in_construction":
            reached.append(case)
            repo._session.execute(
                text("UPDATE capability_invocation_refs SET id=id WHERE id=:id"), {"id": row["id"]}
            )

    def tamper_update(repo, identity, expected_revision: int, values: dict[str, Any]):
        if case == "wrong_usage":
            reached.append(case)
            values = dict(values, usage_record_id=new_uuid7())
        update(repo, identity, expected_revision, values)
        if case == "multiple_flush":
            reached.append(case)
            repo._session.flush()
            update(
                repo,
                identity,
                expected_revision + 1,
                dict(values, row_version=values["row_version"] + 1),
            )

    monkeypatch.setattr(SqlAlchemyGatewayRepository, "insert", tamper_insert)
    monkeypatch.setattr(SqlAlchemyGatewayRepository, "update_invocation", tamper_update)
    with pytest.raises(ResearchBaseError):
        if lifecycle:
            start(g) if case == "multiple_flush" else finish(g)
        else:
            g.gateway_service.request_capability_invocation(g.owner, request_command(g), g.context)
    assert reached and _rows(g.engine) == before


@pytest.mark.parametrize(
    "initial",
    [
        "REQUESTED",
        "RUNNING",
        "SUCCEEDED",
        "FAILED",
        "UNKNOWN_OUTCOME",
        "CANCELLED",
    ],
)
def test_all_invalid_invocation_and_reconciliation_edges(gateway, monkeypatch, initial):
    from tests.integration.phase3.gateway_fixtures import finish, revision

    from researchbase.agent_runtime.application.gateway_contracts import (
        GatewayCommand,
        StartInvocationArguments,
    )
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from researchbase.foundation.ids import new_uuid7
    from researchbase.persistence.capability_gateway_repository import SqlAlchemyGatewayRepository

    g = gateway
    request_invocation(g)
    inv_revision = 1
    if initial != "REQUESTED":
        start(g)
        inv_revision = 2
    if initial not in ("REQUESTED", "RUNNING"):
        finish(g, initial)
        inv_revision = 3
    before = _rows(g.engine)
    statuses = {"REQUESTED", "RUNNING", "SUCCEEDED", "FAILED", "UNKNOWN_OUTCOME", "CANCELLED"}
    legal = {
        "REQUESTED": {"RUNNING", "CANCELLED"},
        "RUNNING": {"SUCCEEDED", "FAILED", "UNKNOWN_OUTCOME", "CANCELLED"},
    }
    update = SqlAlchemyGatewayRepository.update_invocation
    denied = []
    for target in sorted(statuses - legal.get(initial, set())):
        if initial not in ("REQUESTED", "RUNNING"):
            with g.engine.begin() as conn, pytest.raises(DBAPIError) as error:
                conn.execute(
                    text("""
                    UPDATE capability_invocations SET status=:target,row_version=row_version+1
                    WHERE id=:id
                """),
                    {"target": target, "id": g.args.invocation_id},
                )
            assert cast(Any, error.value.orig).sqlstate == "23514"
        else:
            reached = []

            def bad_update(repo, identity, expected, values, target=target, reached=reached):
                reached.append(target)
                return update(repo, identity, expected, dict(values, status=target))

            with monkeypatch.context() as patch:
                patch.setattr(SqlAlchemyGatewayRepository, "update_invocation", bad_update)
                with pytest.raises(ResearchBaseError):
                    start(g) if initial == "REQUESTED" else finish(g)
            assert reached == [target]
        denied.append(f"{initial}->{target}")
        assert _rows(g.engine) == before
    if initial != "REQUESTED":
        c = GatewayCommand(
            g.project,
            g.task,
            new_uuid7(),
            revision(g),
            "start_capability_invocation",
            StartInvocationArguments(g.args.invocation_id, inv_revision, "Illegal start."),
        )
        with pytest.raises(ResearchBaseError) as error:
            g.gateway_service.start_capability_invocation(g.owner, c, g.context)
        assert error.value.code == ErrorCode.INVALID_STATE_TRANSITION
        assert _rows(g.engine) == before
    if initial != "UNKNOWN_OUTCOME":
        with pytest.raises(ResearchBaseError) as error:
            finish(g, "SUCCEEDED", "RECONCILE", inv_revision)
        assert error.value.code == ErrorCode.INVALID_STATE_TRANSITION
        assert _rows(g.engine) == before
    else:
        insert = SqlAlchemyGatewayRepository.insert
        invalid = {
            "sequence": {"sequence": 3},
            "revision": {"invocation_row_version": 2},
            "prior": {"prior_status": "RUNNING"},
            "new": {"new_status": "SUCCEEDED"},
            "missing_outcome": {"reconciled_outcome": None},
            "unknown_again": {"reconciled_outcome": "UNKNOWN_OUTCOME"},
            "missing_usage": {"usage_record_id": None},
            "wrong_usage": {"usage_record_id": new_uuid7()},
        }
        for label, change in invalid.items():
            reached = []

            def bad_event(repo, table, row, change=change, reached=reached):
                if table == "capability_invocation_events":
                    reached.append(True)
                    row = dict(row, **change)
                return insert(repo, table, row)

            with monkeypatch.context() as patch:
                patch.setattr(SqlAlchemyGatewayRepository, "insert", bad_event)
                with pytest.raises(ResearchBaseError):
                    finish(g, "SUCCEEDED", "RECONCILE", 3)
            assert reached == [True] and _rows(g.engine) == before, label
        finish(g, "SUCCEEDED", "RECONCILE", 3)
        settled = _rows(g.engine)
        with pytest.raises(ResearchBaseError) as error:
            finish(g, "FAILED", "RECONCILE", 3)
        assert error.value.code == ErrorCode.INVALID_STATE_TRANSITION
        assert _rows(g.engine) == settled
    print("INVALID_LIFECYCLE_EDGES", denied)


@pytest.mark.parametrize(
    "table",
    [
        "agent_tool_policies",
        "agent_tool_policy_permissions",
        "capability_invocations",
        "capability_invocation_refs",
        "capability_invocation_events",
    ],
)
def test_all_immediate_guards_across_independent_flushes(gateway, monkeypatch, table):
    from tests.integration.phase3.gateway_fixtures import install, request_command

    from researchbase.foundation.errors import ResearchBaseError
    from researchbase.foundation.ids import new_uuid7
    from researchbase.persistence.capability_gateway_repository import SqlAlchemyGatewayRepository

    g = gateway
    expected = {
        "pr303_policy_insert": ("agent_tool_policies", "pr303_policy_insert_guard"),
        "pr303_policy_immutable": ("agent_tool_policies", "pr303_immutable"),
        "pr303_permission_insert": (
            "agent_tool_policy_permissions",
            "pr303_permission_insert_guard",
        ),
        "pr303_permission_immutable": ("agent_tool_policy_permissions", "pr303_immutable"),
        "pr303_invocation_write": ("capability_invocations", "pr303_invocation_guard"),
        "pr303_ref_insert": ("capability_invocation_refs", "pr303_ref_insert_guard"),
        "pr303_ref_immutable": ("capability_invocation_refs", "pr303_immutable"),
        "pr303_event_insert": ("capability_invocation_events", "pr303_event_insert_guard"),
        "pr303_event_immutable": ("capability_invocation_events", "pr303_immutable"),
    }
    with g.engine.connect() as conn:
        triggers = conn.execute(
            text("""
            SELECT t.tgname,t.tgrelid::regclass::text AS table_name,p.proname,t.tgdeferrable,
                   t.tgtype,t.oid FROM pg_trigger t JOIN pg_proc p ON p.oid=t.tgfoid
            WHERE NOT t.tgisinternal AND t.tgname LIKE 'pr303_%'
        """)
        ).all()
        assert {t.tgname: (t.table_name, t.proname) for t in triggers} == expected
        assert all(not t.tgdeferrable and t.tgtype & 1 for t in triggers)
        committed_receipt = conn.execute(
            text("""
            SELECT id FROM research_task_command_receipts WHERE research_task_id=:task
            ORDER BY resulting_row_version LIMIT 1
        """),
            {"task": g.task},
        ).scalar_one()
    registration = table in ("agent_tool_policies", "agent_tool_policy_permissions")
    if not registration:
        install(g)
    before = _rows(g.engine)
    insert = SqlAlchemyGatewayRepository.insert
    for operation in ("bad_insert", "noop", "delete"):
        reached, failures = [], []

        def tamper(repo, target, row, operation=operation, reached=reached, failures=failures):
            insert(repo, target, row)
            if target != table:
                return
            repo._session.flush()
            reached.append(table)
            try:
                if operation == "bad_insert":
                    bad: dict[str, Any] = dict(row, id=new_uuid7())
                    if table == "agent_tool_policies":
                        bad.update(created_by=g.agent_actor, version="invalid-second-policy")
                    elif table == "agent_tool_policy_permissions":
                        bad["operation"] = "latest"
                    elif table == "capability_invocations":
                        bad["reservation_id"] = new_uuid7()
                    else:
                        bad["receipt_id"] = committed_receipt
                    insert(repo, target, bad)
                elif operation == "noop":
                    repo._session.execute(
                        text(f"UPDATE {table} SET id=id WHERE id=:id"), {"id": row["id"]}
                    )
                else:
                    repo._session.execute(
                        text(f"DELETE FROM {table} WHERE id=:id"), {"id": row["id"]}
                    )
            except DBAPIError as error:
                failures.append(
                    (cast(Any, error.orig).sqlstate, cast(Any, error.orig).diag.constraint_name)
                )
                raise

        with monkeypatch.context() as patch:
            patch.setattr(SqlAlchemyGatewayRepository, "insert", tamper)
            with pytest.raises(ResearchBaseError):
                if registration:
                    install(g)
                else:
                    g.gateway_service.request_capability_invocation(
                        g.owner, request_command(g), g.context
                    )
        assert reached == [table] and failures and failures[0][0] == "23514"
        assert _rows(g.engine) == before
        print("IMMEDIATE_GUARD_DENIAL", table, operation, failures)
