from dataclasses import replace
from unittest.mock import Mock

import pytest
from sqlalchemy import text
from tests.integration.phase3.intent_fixtures import _intent_env as _intent_env
from tests.integration.phase3.intent_fixtures import effect_counts, human_researcher

from researchbase.agent_runtime.application.agent_contracts import ChangeAgentAvailability
from researchbase.agent_runtime.application.execution_contracts import (
    GetAgentExecution,
    ListTaskExecutions,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7
from researchbase.persistence.agent_execution_repository import SqlAlchemyExecutionRepository


@pytest.mark.parametrize("failure", ["unavailable", "mismatch"])
def test_saved_replay_precedes_retained_byte_failure(intent_env, monkeypatch, failure):
    env = intent_env
    result = env.intents.execute(env.intent)
    before = effect_counts(env)
    broken_open = Mock(
        side_effect=FileNotFoundError("retained bytes unavailable")
        if failure == "unavailable"
        else None,
        return_value=b"wrong retained bytes",
    )
    monkeypatch.setattr(env.store, "open", broken_open)
    assert env.intents.execute(env.intent) == replace(result, replayed=True)
    assert env.intents.replay(env.intent) == replace(result, replayed=True)
    broken_open.assert_not_called()

    # A new command with the same pins proves the injected byte failure is active.
    new_command = replace(
        env.intent,
        command_id=new_uuid7(),
        arguments=replace(env.intent.arguments, execution_id=new_uuid7()),
    )
    with pytest.raises(ResearchBaseError) as exc:
        env.intents.execute(new_command)
    assert exc.value.code == (
        ErrorCode.FROZEN_REFERENCE_REQUIRED
        if failure == "unavailable"
        else ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    )
    broken_open.assert_called_once()
    assert effect_counts(env) == before


def test_receipt_committed_during_failed_byte_preflight_is_replayed(intent_env, monkeypatch):
    env = intent_env
    open_bytes = env.store.open
    saved = []

    def commit_then_mismatch(locator):
        # Deterministic interleaving: the outer snapshot saw no receipt; another
        # command completes before its ArtifactStore read fails, outside write locks.
        monkeypatch.setattr(env.store, "open", open_bytes)
        saved.append(env.intents.execute(env.intent))
        return b"wrong retained bytes"

    before = effect_counts(env)
    monkeypatch.setattr(env.store, "open", commit_then_mismatch)
    result = env.intents.execute(env.intent)
    assert len(saved) == 1
    assert result == replace(saved[0], replayed=True)
    after = effect_counts(env)
    assert after == {
        table: count
        + (
            table
            in {"agent_command_receipts", "agent_execution_instances", "agent_execution_events"}
        )
        for table, count in before.items()
    }


def test_saved_intent_after_loss_and_uncertain_commit(intent_env, monkeypatch):
    from researchbase.agent_runtime.ports.agent_repository import UncertainAgentCommit
    from researchbase.persistence.uow import SqlAlchemyUnitOfWork

    env = intent_env
    original = SqlAlchemyUnitOfWork.commit

    def uncertain(uow):
        original(uow)
        raise UncertainAgentCommit("simulated lost acknowledgement")

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", uncertain)
    result = env.intents.execute(env.intent)
    assert result.replayed
    assert effect_counts(env)["agent_execution_instances"] == 1
    assert env.intents.replay(env.intent) == result


def test_saved_intent_replays_after_caller_loses_write_authority(intent_env):
    from researchbase.application.phase2_identity import AssignProjectRole, CloseProjectRole

    env = intent_env
    principal = human_researcher(env)
    command = replace(env.intent, caller=principal)
    result = env.intents.execute(command)
    with env.owning_engine.connect() as conn:
        role_id = conn.execute(
            text(
                "SELECT id FROM project_role_assignments "
                "WHERE actor_id=:actor AND project_id=:project AND role='RESEARCHER'"
            ),
            {"actor": principal.actor_id, "project": env.project},
        ).scalar_one()
    env.identity.assign_project_role(
        AssignProjectRole(
            env.owner, env.project, principal.actor_id, "VIEWER", "read only", new_uuid7()
        )
    )
    env.identity.close_project_role(
        CloseProjectRole(env.owner, env.project, role_id, "lost write authority", new_uuid7())
    )
    env.planning.service.execute(
        env.owner,
        env.planning.command(
            "cancel_research_task", command.arguments.research_task_id, 3, {"reason": "done"}
        ),
    )
    before = effect_counts(env)
    assert env.intents.execute(command) == replace(result, replayed=True)
    assert env.intents.replay(command) == replace(result, replayed=True)
    new_command = replace(
        command,
        command_id=new_uuid7(),
        arguments=replace(command.arguments, execution_id=new_uuid7()),
    )
    with pytest.raises(ResearchBaseError) as exc:
        env.intents.execute(new_command)
    assert exc.value.code == ErrorCode.FORBIDDEN
    assert effect_counts(env) == before


@pytest.mark.parametrize(
    "material_field",
    [
        "expected_task_revision",
        "harness_artifact_version_id",
        "agent_version_id",
        "research_task_step_id",
        "execution_id",
        "research_task_id",
    ],
)
def test_current_entitlement_precedes_intent_disclosure(intent_env, monkeypatch, material_field):
    env = intent_env
    result = env.intents.execute(env.intent)
    env.service.execute(
        replace(
            env.version_command,
            command_id=new_uuid7(),
            operation="change_agent_availability",
            expected_revision=1,
            arguments=ChangeAgentAvailability(
                env.intent.arguments.agent_version_id, "RETIRED", "retire"
            ),
        )
    )
    env.planning.service.execute(
        env.owner,
        env.planning.command(
            "cancel_research_task", env.intent.arguments.research_task_id, 3, {"reason": "done"}
        ),
    )
    with env.owning_engine.begin() as conn:
        conn.execute(
            text("UPDATE projects SET lifecycle_status='ARCHIVED' WHERE id=:id"),
            {"id": env.project},
        )
    before = effect_counts(env)
    assert env.intents.execute(env.intent) == replace(result, replayed=True)
    assert env.intents.replay(env.intent) == replace(result, replayed=True)
    changed = replace(
        env.intent,
        arguments=replace(
            env.intent.arguments,
            **{material_field: 4 if material_field == "expected_task_revision" else new_uuid7()},
        ),
    )
    assert changed.command_id == env.intent.command_id
    assert changed.request_hash() != env.intent.request_hash()

    def no_new_id():
        raise AssertionError("changed-material replay must not allocate IDs")

    monkeypatch.setattr(
        "researchbase.agent_runtime.application.agent_executions.new_uuid7", no_new_id
    )
    for entrypoint in (env.intents.execute, env.intents.replay):
        with pytest.raises(ResearchBaseError) as exc:
            entrypoint(changed)
        assert exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
        assert effect_counts(env) == before
        assert env.intents.replay(env.intent) == replace(result, replayed=True)
    monkeypatch.setattr(env.credentials, "is_valid", lambda principal, at: False)
    for entrypoint in (env.intents.execute, env.intents.replay):
        with pytest.raises(ResearchBaseError) as exc:
            entrypoint(changed)
        assert exc.value.code == ErrorCode.FORBIDDEN
    assert effect_counts(env) == before


def test_other_caller_cannot_replay_receipt(intent_env):
    env = intent_env
    env.intents.execute(env.intent)
    other = human_researcher(env)
    with pytest.raises(ResearchBaseError) as exc:
        env.intents.replay(replace(env.intent, caller=other))
    assert exc.value.code == ErrorCode.FORBIDDEN
    assert (
        env.intents.get_agent_execution(
            GetAgentExecution(env.project, env.intent.arguments.execution_id, other)
        ).id
        == env.intent.arguments.execution_id
    )


def test_queries_are_coherent_bounded_snapshots(intent_env, monkeypatch):
    env = intent_env
    env.intents.execute(env.intent)
    second = replace(
        env.intent,
        command_id=new_uuid7(),
        arguments=replace(env.intent.arguments, execution_id=new_uuid7()),
    )
    snapshots = []
    original = SqlAlchemyExecutionRepository.dto

    def dto(repo, row):
        with_sql = repo.one(
            "SELECT current_setting('transaction_isolation') isolation,current_setting('transaction_read_only') readonly,pg_current_snapshot()::text snapshot"  # noqa: E501
        )
        snapshots.append(with_sql)
        if len(snapshots) == 1:
            env.intents.execute(second)
        snapshots.append(
            repo.one(
                "SELECT current_setting('transaction_isolation') isolation,current_setting('transaction_read_only') readonly,pg_current_snapshot()::text snapshot"  # noqa: E501
            )
        )
        return original(repo, row)

    monkeypatch.setattr(SqlAlchemyExecutionRepository, "dto", dto)
    query = ListTaskExecutions(
        env.project, env.intent.arguments.research_task_id, env.owner, limit=1
    )
    page = env.intents.list_task_executions(query)
    assert len(page) == 1 and page[0].task_revision_at_creation == 3
    assert snapshots[0] == snapshots[1]
    assert snapshots[0]["isolation"] == "repeatable read" and snapshots[0]["readonly"] == "on"
    next_page = env.intents.list_task_executions(replace(query, after_id=page[0].id))
    assert len(next_page) == 1 and next_page[0].id == second.arguments.execution_id
