from dataclasses import replace

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
