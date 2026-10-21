from dataclasses import replace

import pytest
from sqlalchemy import text
from tests.integration.phase3.agent_fixtures import enrollment, register

from researchbase.agent_runtime.application.agent_contracts import ChangeAgentAvailability
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7


def test_exact_replay_preserves_ids_time_after_retirement_and_archive(agents):
    enroll = enrollment(agents)
    admitted = agents.service.execute(enroll)
    assert replace(agents.service.execute(enroll), replayed=False) == admitted
    reg = register(agents, enroll.arguments.actor_id)
    original = agents.service.execute(reg)
    retired = replace(
        reg,
        command_id=new_uuid7(),
        operation="change_agent_availability",
        expected_revision=1,
        arguments=ChangeAgentAvailability(reg.arguments.agent_version_id, "RETIRED", "retire"),
    )
    agents.service.execute(retired)
    with agents.engine.begin() as conn:
        conn.execute(
            text("UPDATE projects SET lifecycle_status='ARCHIVED' WHERE id=:id"),
            {"id": agents.project},
        )
    assert replace(agents.service.execute(reg), replayed=False) == original
    assert replace(agents.service.replay(reg), replayed=False) == original
    with agents.engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM agent_command_receipts")).scalar_one() == 3
    with pytest.raises(ResearchBaseError) as exc:
        agents.service.execute(
            replace(reg, arguments=replace(reg.arguments, model_profile_id="other@1"))
        )
    assert exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT


@pytest.mark.parametrize("changed", ["proof", "target", "cas"])
def test_changed_material_conflict(agents, changed):
    command = enrollment(agents)
    agents.service.execute(command)
    if changed == "proof":
        other = replace(
            command,
            arguments=replace(
                command.arguments,
                enrollment_proof=replace(command.arguments.enrollment_proof, proof_sha256="d" * 64),
            ),
        )
    else:
        command = register(agents, command.arguments.actor_id)
        agents.service.execute(command)
        if changed == "target":
            other = replace(
                command, arguments=replace(command.arguments, agent_version_id=new_uuid7())
            )
        else:
            command = replace(
                command,
                command_id=new_uuid7(),
                operation="change_agent_availability",
                expected_revision=1,
                arguments=ChangeAgentAvailability(
                    command.arguments.agent_version_id, "DISABLED", "disable"
                ),
            )
            agents.service.execute(command)
            other = replace(command, expected_revision=2)
    with pytest.raises(ResearchBaseError) as exc:
        agents.service.execute(other)
    assert exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT


def test_replay_current_read_denial(agents, monkeypatch):
    command = enrollment(agents)
    agents.service.execute(command)
    monkeypatch.setattr(agents.credentials, "is_valid", lambda *args: False)
    with pytest.raises(ResearchBaseError) as exc:
        agents.service.replay(command)
    assert exc.value.code == ErrorCode.FORBIDDEN


@pytest.mark.parametrize("state,attempts", [("40001", 3), ("40P01", 3), ("55P03", 1), ("57014", 1)])
def test_whole_transaction_retry_bound_and_stable_ids(agents, monkeypatch, state, attempts):
    import psycopg
    from sqlalchemy.exc import OperationalError

    from researchbase.persistence.agent_version_repository import SqlAlchemyAgentRepository

    cmd = enrollment(agents)
    seen = []
    original = SqlAlchemyAgentRepository.insert

    def failure(self, table, row):
        saved = original(self, table, row)
        if table == "agent_command_receipts":
            seen.append(saved)
            raise OperationalError(
                "test-only fault", {}, psycopg.errors.lookup(state)("test-only fault")
            )
        return saved

    monkeypatch.setattr(SqlAlchemyAgentRepository, "insert", failure)
    with pytest.raises(ResearchBaseError) as exc:
        agents.service.execute(cmd)
    assert exc.value.code == ErrorCode.CONCURRENT_MODIFICATION
    assert len(seen) == attempts
    assert len({r["id"] for r in seen}) == 1
    assert len({r["request_hash"] for r in seen}) == 1
    assert len({r["recorded_at"] for r in seen}) == attempts
    with agents.engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM agent_command_receipts")).scalar_one() == 0


def test_uncertain_commit_reconciles_exact_receipt(agents, monkeypatch):
    from researchbase.agent_runtime.ports.agent_repository import UncertainAgentCommit
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    original = SqlAlchemyUnitOfWork.commit
    calls = []

    def lost(self):
        original(self)
        calls.append(1)
        raise UncertainAgentCommit("test lost response after durable commit")

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", lost)
    command = enrollment(agents)
    result = agents.service.execute(command)
    assert result.replayed and len(calls) == 1
    with agents.engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM agent_command_receipts")).scalar_one() == 1
