# ruff: noqa: E501
"""Durable exact-result replay, current entitlement and transaction rollback."""

from dataclasses import replace

import pytest
from sqlalchemy import text

from researchbase.agent_runtime.application.contracts import CancelArguments
from researchbase.agent_runtime.application.research_task import ResearchTaskService
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.research_task_repository import SqlAlchemyResearchTaskRepository


def test_lost_response_and_historical_replay_precedes_cas(planning):
    cmd = planning.command()
    original = planning.service.execute(planning.principal, cmd)
    task, plan = planning.plan(cmd.task_id)
    planning.service.execute(
        planning.principal, planning.command("cancel_research_task", task, 2, {"reason": "Stop"})
    )
    replay = planning.service.execute(planning.principal, cmd)
    assert replace(replay, replayed=False) == original
    assert planning.service.replay(planning.principal, cmd) == replay
    assert (
        planning.service.get_research_task(planning.principal, planning.project, task).row_version
        == 3
    )
    # Same request with changed hash conflicts before expected revision/state checks.
    changed = replace(plan, arguments=replace(plan.arguments, edges=()))
    changed = replace(changed, expected_row_version=3)
    with pytest.raises(ResearchBaseError) as caught:
        planning.service.execute(planning.principal, changed)
    assert caught.value.code == ErrorCode.IDEMPOTENCY_CONFLICT


@pytest.mark.parametrize("change", ("objective", "task", "expected", "command_name"))
def test_changed_hash_conflicts(planning, change):
    cmd = planning.command()
    planning.service.execute(planning.principal, cmd)
    if change == "objective":
        different = replace(cmd, arguments=replace(cmd.arguments, objective="Other"))
    elif change == "task":
        from researchbase.foundation.ids import new_uuid7

        different = replace(cmd, task_id=new_uuid7())
    elif change == "expected":
        different = replace(
            cmd,
            command_name="cancel_research_task",
            expected_row_version=1,
            arguments=CancelArguments("Stop"),
        )
    else:
        different = replace(
            cmd,
            command_name="seal_task_plan",
            expected_row_version=1,
            arguments=__import__(
                "researchbase.agent_runtime.application.contracts", fromlist=["EmptyArguments"]
            ).EmptyArguments(),
        )
    with pytest.raises(ResearchBaseError) as caught:
        planning.service.execute(planning.principal, different)
    assert caught.value.code == ErrorCode.IDEMPOTENCY_CONFLICT


def test_replay_requires_current_read_entitlement(planning):
    cmd = planning.command()
    planning.service.execute(planning.principal, cmd)

    class Revoked:
        def is_valid(self, principal, at):
            return False

    service = ResearchTaskService(planning.factory, Revoked())
    for action in (service.execute, service.replay):
        with pytest.raises(ResearchBaseError) as caught:
            action(planning.principal, cmd)
        assert caught.value.code == ErrorCode.FORBIDDEN
    assert planning.service.replay(planning.principal, planning.command()) is None


@pytest.mark.parametrize(
    "point",
    (
        "research_task_steps",
        "research_task_command_receipts",
        "research_task_events",
        "research_task_receipt_step_events",
    ),
)
def test_failure_rolls_back_entire_transaction(planning, monkeypatch, point):
    task = planning.create()
    before = planning.service.get_task_graph(planning.principal, planning.project, task)
    insert = SqlAlchemyResearchTaskRepository.insert

    def fail(self, table, row):
        if table == point:
            raise RuntimeError("injected lost transaction")
        return insert(self, table, row)

    with monkeypatch.context() as patch:
        patch.setattr(SqlAlchemyResearchTaskRepository, "insert", fail)
        with pytest.raises(RuntimeError):
            planning.plan(task)
    assert planning.service.get_task_graph(planning.principal, planning.project, task) == before


def test_uncertain_commit_reconciles_without_reexecution(planning, monkeypatch):
    cmd = planning.command()
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    commit = SqlAlchemyUnitOfWork.commit

    def lost(self):
        commit(self)
        raise RuntimeError("response lost after durable commit")

    with monkeypatch.context() as patch:
        patch.setattr(SqlAlchemyUnitOfWork, "commit", lost)
        with pytest.raises(RuntimeError):
            planning.service.execute(planning.principal, cmd)
    replay = planning.service.replay(planning.principal, cmd)
    assert replay is not None and replay.replayed and replay.resulting_row_version == 1
    with planning.engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM research_task_events WHERE research_task_id=:id"),
                {"id": cmd.task_id},
            ).scalar_one()
            == 1
        )


def test_uncertain_commit_automatically_reads_exact_receipt(planning, monkeypatch):
    from researchbase.agent_runtime.ports.task_repository import UncertainTaskCommit
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    commit = SqlAlchemyUnitOfWork.commit

    def uncertain(self):
        commit(self)
        raise UncertainTaskCommit("acknowledgement lost")

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", uncertain)
    cmd = planning.command()
    result = planning.service.execute(planning.principal, cmd)
    assert result.replayed and result.resulting_row_version == 1


def test_viewer_historical_replay_needs_no_renewed_write_role(planning):
    from tests.integration.phase2.test_pr2_00_ownership import _add_owner

    from researchbase.domain.phase2_identity import VerifiedPrincipal
    from researchbase.foundation.ids import new_uuid7

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
    cmd = planning.command()
    original = planning.service.execute(principal, cmd)
    with planning.engine.begin() as conn:
        conn.execute(text("SELECT rb_phase2_lock_project(:p)"), {"p": planning.project})
        at = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
        conn.execute(
            text(
                "UPDATE project_role_assignments SET effective_until=:at,row_version=row_version+1 WHERE id=:id"
            ),
            {"id": role, "at": at},
        )
        conn.execute(
            text(
                "INSERT INTO project_role_events (id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id) VALUES (:id,:role,:actor,'CLOSED',:at,'Read only',:request)"
            ),
            {"id": new_uuid7(), "role": role, "actor": actor, "at": at, "request": new_uuid7()},
        )
        viewer = new_uuid7()
        conn.execute(
            text(
                "INSERT INTO project_role_assignments (id,membership_id,project_id,actor_id,role,effective_from,assigned_by,created_at,row_version) VALUES (:id,:membership,:project,:actor,'VIEWER',:at,:actor,:at,1)"
            ),
            {
                "id": viewer,
                "membership": membership,
                "project": planning.project,
                "actor": actor,
                "at": at,
            },
        )
        conn.execute(
            text(
                "INSERT INTO project_role_events (id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id) VALUES (:id,:role,:actor,'ASSIGNED',:at,'Read only',:request)"
            ),
            {"id": new_uuid7(), "role": viewer, "actor": actor, "at": at, "request": new_uuid7()},
        )
    replay = planning.service.execute(principal, cmd)
    assert replace(replay, replayed=False) == original
    with pytest.raises(ResearchBaseError) as caught:
        planning.service.execute(principal, planning.command())
    assert caught.value.code == ErrorCode.FORBIDDEN


@pytest.mark.parametrize("name", ("seal_task_plan", "cancel_research_task"))
def test_repeated_lifecycle_without_exact_receipt_is_denied(planning, name):
    task, _ = planning.plan()
    args = {"reason": "Stop"} if name == "cancel_research_task" else {}
    original = planning.command(name, task, 2, args)
    planning.service.execute(planning.principal, original)
    replay = planning.service.execute(planning.principal, original)
    assert replay.replayed
    with pytest.raises(ResearchBaseError) as caught:
        planning.service.execute(planning.principal, planning.command(name, task, 3, args))
    assert caught.value.code == ErrorCode.INVALID_STATE_TRANSITION
