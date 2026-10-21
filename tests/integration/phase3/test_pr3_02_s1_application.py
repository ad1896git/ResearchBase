from dataclasses import replace
from datetime import timedelta

import pytest
from sqlalchemy import text
from tests.integration.phase3.agent_fixtures import enrollment, register

from researchbase.agent_runtime.application.agent_contracts import (
    ChangeAgentAvailability,
    GetAgentVersion,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7


def test_enroll_register_change_read(agents):
    command = enrollment(agents)
    result = agents.identity.provision_project_agent(command)
    assert result.result_actor_id == command.arguments.actor_id
    assert result.recorded_at.utcoffset() == timedelta(0)
    reg = register(agents, result.result_actor_id)
    registered = agents.service.register_agent_version(reg)
    assert registered.resulting_revision == 1
    query = GetAgentVersion(agents.project, reg.arguments.agent_version_id, agents.owner)
    view = agents.service.get_agent_version(query)
    assert view.current_availability.status == "ACTIVE"
    assert view.created_at.utcoffset() == timedelta(0)
    assert view.current_availability.changed_at.utcoffset() == timedelta(0)
    for revision, status in enumerate(("DISABLED", "ACTIVE", "RETIRED"), 1):
        change = replace(
            reg,
            command_id=new_uuid7(),
            operation="change_agent_availability",
            expected_revision=revision,
            arguments=ChangeAgentAvailability(view.id, status, "test transition"),
        )
        changed = agents.service.change_agent_availability(change)
        assert changed.resulting_revision == revision + 1
    final = agents.service.get_agent_version(query)
    assert final.content_hash == view.content_hash
    assert final.current_availability.status == "RETIRED"
    with pytest.raises(ResearchBaseError) as exc:
        agents.service.execute(
            replace(
                change,
                command_id=new_uuid7(),
                expected_revision=4,
                arguments=ChangeAgentAvailability(view.id, "ACTIVE", "invalid exit"),
            )
        )
    assert exc.value.code == ErrorCode.INVALID_STATE_TRANSITION
    with agents.engine.connect() as conn:
        times = conn.execute(
            text("SELECT recorded_at FROM agent_command_receipts WHERE id=:id"),
            {"id": result.receipt_id},
        ).scalar_one()
        assert times == result.recorded_at


@pytest.mark.parametrize("flush", range(1, 9))
def test_enrollment_failure_after_each_flush_is_atomic(agents, monkeypatch, flush):
    from researchbase.persistence.agent_version_repository import SqlAlchemyAgentRepository

    command = enrollment(agents)
    original = SqlAlchemyAgentRepository.insert
    calls = 0

    def injected(self, table, row):
        nonlocal calls
        result = original(self, table, row)
        calls += 1
        if calls == flush:
            raise RuntimeError("test-only rollback injection")
        return result

    monkeypatch.setattr(SqlAlchemyAgentRepository, "insert", injected)
    with pytest.raises(RuntimeError, match="rollback injection"):
        agents.service.execute(command)
    with agents.engine.connect() as conn:
        assert (
            conn.execute(text("SELECT count(*) FROM actors WHERE actor_type='AGENT'")).scalar_one()
            == 0
        )
        assert conn.execute(text("SELECT count(*) FROM agent_command_receipts")).scalar_one() == 0
        assert (
            conn.execute(
                text("SELECT count(*) FROM project_membership_events WHERE request_id=:id"),
                {"id": command.command_id},
            ).scalar_one()
            == 0
        )


@pytest.mark.parametrize("flush", range(1, 5))
def test_register_failure_after_each_flush_is_atomic(agents, monkeypatch, flush):
    from researchbase.persistence.agent_version_repository import SqlAlchemyAgentRepository

    command = enrollment(agents)
    agents.service.execute(command)
    reg = register(agents, command.arguments.actor_id)
    original = SqlAlchemyAgentRepository.insert
    calls = 0

    def injected(self, table, row):
        nonlocal calls
        result = original(self, table, row)
        calls += 1
        if calls == flush:
            raise RuntimeError("test-only rollback injection")
        return result

    monkeypatch.setattr(SqlAlchemyAgentRepository, "insert", injected)
    with pytest.raises(RuntimeError, match="rollback injection"):
        agents.service.execute(reg)
    with agents.engine.connect() as conn:
        for table in ("agent_versions", "agent_availability", "agent_availability_events"):
            assert conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0
        assert conn.execute(text("SELECT count(*) FROM agent_command_receipts")).scalar_one() == 1


def test_distinct_stable_versions_accept_identical_behavior(agents):
    command = enrollment(agents)
    agents.service.execute(command)
    first = register(agents, command.arguments.actor_id)
    second = replace(
        first,
        command_id=new_uuid7(),
        arguments=replace(first.arguments, agent_version_id=new_uuid7()),
    )
    agents.service.execute(first)
    agents.service.execute(second)
    with agents.engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM agent_versions")).scalar_one() == 2
        assert (
            conn.execute(
                text("SELECT count(DISTINCT content_hash) FROM agent_versions")
            ).scalar_one()
            == 1
        )
