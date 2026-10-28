"""Forward-only migration and preservation of typed legacy rows and receipts."""

import hashlib
import json
from dataclasses import replace
from datetime import timedelta

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from tests.disposable_postgres import disposable_database
from tests.integration.phase3.agent_fixtures import enrollment, register
from tests.integration.phase3.test_pr3_00_bootstrap import _catalog, _rows

NEW_TABLES = {
    "agent_tool_policies",
    "agent_tool_policy_permissions",
    "capability_invocations",
    "capability_invocation_refs",
    "capability_invocation_events",
}
TRIGGERS_SQL = """
SELECT oid,tgrelid,tgname,tgfoid,tgtype,tgdeferrable,tginitdeferred
FROM pg_trigger WHERE NOT tgisinternal ORDER BY oid
"""


def manifest(engine, label):
    rows = _rows(engine)
    print(
        label,
        "tables",
        len(rows),
        "rows",
        sum(map(len, rows.values())),
        "sha256",
        hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest(),
    )
    return rows


def check_refusal(url, engine, config):
    before = _rows(engine)
    catalog = _catalog(url)
    with pytest.raises(RuntimeError, match="forward-only"):
        command.downgrade(config, "0079_agent_identity_versions")
    assert _catalog(url) == catalog
    assert _rows(engine) == before
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0080_capability_gateway"
        )


def test_empty_base_upgrade_and_downgrade_refusal(monkeypatch):
    with disposable_database("researchbase_pr212_test_") as url:
        monkeypatch.setenv("DATABASE_URL", url)
        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
        engine = create_engine(url)
        try:
            command.upgrade(cfg, "0080_capability_gateway")
            rows = manifest(engine, "clean-0080")
            assert all(not rows[t] for t in NEW_TABLES)
            with engine.connect() as conn:
                print(
                    "POSTGRES",
                    conn.execute(text("SHOW server_version")).scalar_one(),
                    "role",
                    conn.execute(text("SELECT current_user")).scalar_one(),
                    "encoding",
                    conn.execute(text("SHOW server_encoding")).scalar_one(),
                )
            check_refusal(url, engine, cfg)
            assert ScriptDirectory.from_config(cfg).get_heads() == ["0082_experiment_search_core"]
        finally:
            engine.dispose()


def test_populated_0079_preserves_rows_receipts_triggers_and_refuses_downgrade(agents):
    from tests.integration.phase3.conftest import PlanningFixture
    from tests.integration.phase3.test_pr3_04_application import approve, bind, service

    from researchbase.agent_runtime.application.research_task import ResearchTaskService

    a = agents
    enrolled = enrollment(a)
    old_enrollment = a.service.execute(enrolled)
    reg = register(a, enrolled.arguments.actor_id)
    old_version = a.service.execute(reg)
    p = PlanningFixture(
        a.engine,
        a.factory,
        ResearchTaskService(a.factory, a.credentials, a.store),
        a.owner,
        a.project,
        a.url,
        a.store,
    )
    from tests.integration.phase3.gateway_fixtures import owning_inputs

    owning_inputs(p)
    task = p.create()
    c, old_safety = bind(p, task)
    approve(p, task, 2)
    graph = p.service.get_task_graph(a.owner, a.project, task)
    before = manifest(a.engine, "populated-0079")
    with a.engine.connect() as conn:
        triggers = [tuple(r) for r in conn.execute(text(TRIGGERS_SQL))]
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", a.url.replace("%", "%%"))
    statements = []

    def trace(conn, cursor, statement, parameters, context, many):
        statements.append(statement)

    event.listen(Engine, "before_cursor_execute", trace)
    try:
        command.upgrade(cfg, "0080_capability_gateway")
    finally:
        event.remove(Engine, "before_cursor_execute", trace)
    assert not any(
        s.lstrip().upper().startswith("UPDATE ")
        and not s.lstrip().upper().startswith("UPDATE ALEMBIC_VERSION ")
        for s in statements
    )
    with a.engine.connect() as conn:
        role = conn.execute(text("SELECT current_user")).scalar_one()
    admin = create_engine(a.url)
    try:
        with admin.begin() as conn:
            conn.execute(
                text(f"GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {role}")
            )
    finally:
        admin.dispose()
    after = manifest(a.engine, "populated-0080")
    assert set(after) - set(before) == NEW_TABLES
    added = {
        "research_task_command_receipts": {
            "result_tool_policy_id",
            "result_capability_invocation_id",
            "result_capability_event_id",
            "resulting_invocation_revision",
        },
        "research_task_events": {
            "result_tool_policy_id",
            "result_capability_invocation_id",
            "result_capability_event_id",
        },
    }
    for table, old in before.items():
        projected = []
        for row in after[table]:
            value = json.loads(row)
            for name in added.get(table, set()):
                assert value.pop(name) is None
            projected.append(value)
        assert sorted(json.dumps(r, sort_keys=True) for r in projected) == sorted(
            json.dumps(json.loads(r), sort_keys=True) for r in old
        ), table
    with a.engine.connect() as conn:
        retained = [tuple(r) for r in conn.execute(text(TRIGGERS_SQL))]
        assert all(r in retained for r in triggers)
    assert p.service.get_task_graph(a.owner, a.project, task) == graph
    assert a.service.execute(enrolled).receipt_id == old_enrollment.receipt_id
    assert a.service.execute(reg).receipt_id == old_version.receipt_id
    assert service(p).execute(a.owner, c) == replace(
        old_safety, command_result=replace(old_safety.command_result, replayed=True)
    )
    check_refusal(a.url, a.engine, cfg)
    print("retained trigger OIDs/attachments", len(triggers), "legacy result replays=3 UPDATE=0")


def test_all_original_planning_safety_s1_saved_results_after_upgrade(agents, monkeypatch):
    from dataclasses import asdict

    from tests.integration.phase3.conftest import PlanningFixture
    from tests.integration.phase3.test_pr3_04_application import command as safety_command
    from tests.integration.phase3.test_pr3_04_application import reserve, settle

    from researchbase.agent_runtime.application.agent_contracts import ChangeAgentAvailability
    from researchbase.agent_runtime.application.research_task import ResearchTaskService
    from researchbase.agent_runtime.application.task_safety import TaskSafetyService
    from researchbase.agent_runtime.services.fake_consumer import TrustedFakeConsumer
    from researchbase.foundation.ids import new_uuid7
    from researchbase.persistence.task_safety_repository import SqlAlchemyTaskSafetyRepository

    a = agents
    p = PlanningFixture(
        a.engine,
        a.factory,
        ResearchTaskService(a.factory, a.credentials, a.store),
        a.owner,
        a.project,
        a.url,
        a.store,
    )
    planning, safety, identities = [], [], []

    def plan(c):
        planning.append((c, p.service.execute(a.owner, c)))

    create = p.command()
    plan(create)
    task = create.task_id
    nodes = [new_uuid7(), new_uuid7(), new_uuid7()]
    plan(
        p.command(
            "create_task_plan",
            task,
            1,
            {
                "nodes": [
                    {"step_id": str(nodes[0]), "step_type": "PLAN", "ordinal": 1},
                    {"step_id": str(nodes[1]), "step_type": "RESEARCH", "ordinal": 2},
                ],
                "edges": [],
            },
        )
    )
    plan(
        p.command(
            "add_task_step",
            task,
            2,
            {
                "node": {
                    "step_id": str(nodes[2]),
                    "step_type": "ANALYZE",
                    "ordinal": 3,
                },
                "predecessor_ids": [],
            },
        )
    )
    plan(
        p.command(
            "add_task_step_dependency",
            task,
            3,
            {
                "predecessor_id": str(nodes[0]),
                "dependent_id": str(nodes[2]),
            },
        )
    )
    plan(p.command("seal_task_plan", task, 4))
    plan(p.command("cancel_research_task", task, 5, {"reason": "Cancel historical plan."}))
    safety_task = p.create()
    svc = TaskSafetyService(a.factory, a.credentials, a.store)
    fake = TrustedFakeConsumer(a.factory, a.credentials, a.store)

    def safe(c, trusted=False):
        result = fake.execute(a.owner, c) if trusted else svc.execute(a.owner, c)
        safety.append((c, result, trusted))
        return result

    safe(
        safety_command(
            p,
            safety_task,
            1,
            "bind_task_policies",
            {
                "budget_id": str(new_uuid7()),
                "budget": {"pricing_basis": "fake-usd-v1"},
                "termination_policy_id": str(new_uuid7()),
                "termination": {},
                "checkpoint_policy_id": str(new_uuid7()),
                "checkpoint": {},
                "reason": "Bind history.",
            },
        )
    )
    checkpoint = new_uuid7()
    safe(
        safety_command(
            p,
            safety_task,
            2,
            "request_human_checkpoint",
            {
                "checkpoint_id": str(checkpoint),
                "step_id": None,
                "checkpoint_type": "plan_review",
                "reason": "Review history.",
            },
        )
    )
    safe(
        safety_command(
            p,
            safety_task,
            3,
            "respond_human_checkpoint",
            {
                "checkpoint_id": str(checkpoint),
                "expected_checkpoint_row_version": 1,
                "response": "APPROVED",
                "reason": "Approve history.",
            },
        )
    )
    reservation = safe(reserve(p, safety_task, 4), True)
    safe(settle(p, safety_task, 5, reservation.reservation_ids[0]), True)
    safe(
        safety_command(
            p, safety_task, 6, "evaluate_task_termination", {"reason": "Evaluate history."}
        )
    )
    enrolled = enrollment(a)
    identities.append((enrolled, a.service.execute(enrolled)))
    version = register(a, enrolled.arguments.actor_id)
    identities.append((version, a.service.execute(version)))
    disabled = replace(
        version,
        command_id=new_uuid7(),
        operation="change_agent_availability",
        expected_revision=1,
        arguments=ChangeAgentAvailability(
            version.arguments.agent_version_id,
            "DISABLED",
            "Pause historical version.",
        ),
    )
    identities.append((disabled, a.service.execute(disabled)))
    before = _rows(a.engine)
    before_graph = p.service.get_task_graph(a.owner, a.project, task)
    with a.engine.connect() as conn:
        reserved_at = conn.execute(
            text("SELECT created_at FROM budget_reservations WHERE research_task_id=:task"),
            {"task": safety_task},
        ).scalar_one()
    # snapshot_at() reads transaction_timestamp(); migration time must not consume budget.
    snapshot_at = reserved_at + timedelta(seconds=1)
    monkeypatch.setattr(SqlAlchemyTaskSafetyRepository, "snapshot_at", lambda self: snapshot_at)
    before_safety = svc.get_task_safety(a.owner, a.project, safety_task)
    assert before_safety.elapsed_wall_seconds == 1
    assert before_safety.remaining.wall_time_seconds == 1799
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", a.url.replace("%", "%%"))
    command.upgrade(config, "0080_capability_gateway")
    with a.engine.connect() as conn:
        role = conn.execute(text("SELECT current_user")).scalar_one()
    admin = create_engine(a.url)
    try:
        with admin.begin() as conn:
            conn.execute(
                text(f"GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO {role}")
            )
    finally:
        admin.dispose()
    after = _rows(a.engine)
    added = {
        "research_task_command_receipts": {
            "result_tool_policy_id",
            "result_capability_invocation_id",
            "result_capability_event_id",
            "resulting_invocation_revision",
        },
        "research_task_events": {
            "result_tool_policy_id",
            "result_capability_invocation_id",
            "result_capability_event_id",
        },
    }
    for table, old_rows in before.items():
        projected = []
        for row in after[table]:
            value = json.loads(row)
            for name in added.get(table, ()):
                assert value.pop(name) is None
            projected.append(json.dumps(value, sort_keys=True))
        assert sorted(projected) == sorted(
            json.dumps(json.loads(r), sort_keys=True) for r in old_rows
        )

    def without_replay(value):
        if isinstance(value, dict):
            return {k: without_replay(v) for k, v in value.items() if k != "replayed"}
        if isinstance(value, list | tuple):
            return [without_replay(v) for v in value]
        return value

    replay_rows = _rows(a.engine)
    for c, old in planning:
        replay = p.service.execute(a.owner, c)
        assert replay.replayed and without_replay(asdict(replay)) == without_replay(asdict(old))
    for c, old, trusted in safety:
        replay = fake.execute(a.owner, c) if trusted else svc.execute(a.owner, c)
        assert replay.command_result.replayed
        assert without_replay(asdict(replay)) == without_replay(asdict(old))
    for c, old in identities:
        replay = a.service.execute(c)
        assert replay == replace(old, replayed=True)
    assert p.service.get_task_graph(a.owner, a.project, task) == before_graph
    after_safety = svc.get_task_safety(a.owner, a.project, safety_task)
    assert after_safety == before_safety
    after_replay = _rows(a.engine)
    replay_writes = sum(len(set(replay_rows[t]) ^ set(after_replay[t])) for t in replay_rows)
    assert replay_writes == 0
    assert after_replay == after
    assert len(planning) == len(safety) == 6 and len(identities) == 3
    print(
        "ALL_LEGACY_REPLAY",
        len(planning),
        len(safety),
        len(identities),
        f"replay_writes={replay_writes}",
    )
