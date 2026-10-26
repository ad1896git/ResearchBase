from dataclasses import replace

import pytest
from tests.integration.phase3.intent_fixtures import _intent_env as _intent_env
from tests.integration.phase3.intent_fixtures import effect_counts, human_researcher

from researchbase.agent_runtime.application.agent_contracts import ChangeAgentAvailability
from researchbase.agent_runtime.application.agent_executions import AgentExecutionService
from researchbase.agent_runtime.application.execution_contracts import GetAgentExecution
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7
from researchbase.persistence.agent_execution_repository import SqlAlchemyExecutionRepository


def test_created_intent_through_common_application_boundary(intent_env, monkeypatch):
    env = intent_env
    result = env.intents.execute(env.intent)
    assert result.result_execution_id == env.intent.arguments.execution_id
    assert result.result_execution_event_id is not None
    assert result.resulting_revision == 1 and result.replayed is False
    dto = env.intents.get_agent_execution(
        GetAgentExecution(env.project, result.result_execution_id, env.owner)
    )
    assert dto.status == "CREATED" and dto.revision == 1 and dto.task_revision_at_creation == 3
    assert dto.events[0].reason == "Execution intent created."

    def no_new_ids():
        raise AssertionError("exact replay must not allocate IDs")

    monkeypatch.setattr(
        "researchbase.agent_runtime.application.agent_executions.new_uuid7", no_new_ids
    )
    assert env.intents.execute(env.intent) == replace(result, replayed=True)


@pytest.mark.parametrize("caller", ["human_researcher", "agent"])
def test_researcher_and_exact_agent_use_common_boundary(intent_env, caller):
    env = intent_env
    principal = (
        human_researcher(env)
        if caller == "human_researcher"
        else env.identity.resolve_agent_subject(env.provision.arguments.subject)
    )
    before = effect_counts(env)
    result = env.intents.execute(replace(env.intent, caller=principal))
    assert result.caller_actor_id == principal.actor_id
    after = effect_counts(env)
    for table in before:
        assert after[table] - before[table] == (
            1
            if table
            in {"agent_execution_instances", "agent_execution_events", "agent_command_receipts"}
            else 0
        )
    task = env.planning.service.get_research_task(
        env.owner, env.project, env.intent.arguments.research_task_id
    )
    assert task.execution_enabled is False
    assert task.row_version == 3 and task.status == "PLANNING"


@pytest.mark.parametrize(
    "case,code,task_condition",
    [
        ("stale", ErrorCode.CONCURRENT_MODIFICATION, "current"),
        ("unsealed", ErrorCode.INVALID_STATE_TRANSITION, "current"),
        ("unavailable", ErrorCode.INVALID_STATE_TRANSITION, "current"),
        ("viewer", ErrorCode.FORBIDDEN, "current"),
        ("other_agent", ErrorCode.FORBIDDEN, "current"),
        ("viewer", ErrorCode.FORBIDDEN, "stale"),
        ("other_agent", ErrorCode.FORBIDDEN, "stale"),
        ("viewer", ErrorCode.FORBIDDEN, "cancelled"),
        ("other_agent", ErrorCode.FORBIDDEN, "cancelled"),
        ("untrusted", ErrorCode.AUTHENTICATION_REQUIRED, "current"),
        ("pins", ErrorCode.FROZEN_REFERENCE_REQUIRED, "current"),
        ("bytes", ErrorCode.PROVENANCE_CLOSURE_VIOLATION, "current"),
        ("scope", ErrorCode.FORBIDDEN, "current"),
        ("unfrozen", ErrorCode.VERSION_NOT_FROZEN, "current"),
    ],
)
def test_intent_denials_preserve_closed_execution_gate(
    intent_env, case, code, monkeypatch, task_condition
):
    env = intent_env
    command = env.intent
    service = env.intents
    if task_condition == "stale":
        command = replace(command, arguments=replace(command.arguments, expected_task_revision=2))
    elif task_condition == "cancelled":
        env.planning.service.execute(
            env.owner,
            env.planning.command(
                "cancel_research_task", command.arguments.research_task_id, 3, {"reason": "done"}
            ),
        )
    if case == "stale":
        command = replace(command, arguments=replace(command.arguments, expected_task_revision=2))
    if case == "unsealed":
        task, _ = env.planning.plan()
        command = replace(
            command,
            arguments=replace(command.arguments, research_task_id=task, expected_task_revision=2),
        )
    if case == "unavailable":
        env.service.execute(
            replace(
                env.version_command,
                command_id=new_uuid7(),
                operation="change_agent_availability",
                expected_revision=1,
                arguments=ChangeAgentAvailability(
                    command.arguments.agent_version_id, "DISABLED", "test"
                ),
            )
        )
    if case == "viewer":
        command = replace(command, caller=human_researcher(env, "VIEWER"))
    if case == "other_agent":
        from tests.integration.phase3.agent_fixtures import enrollment

        other = enrollment(env)
        env.service.execute(other)
        command = replace(
            command, caller=env.identity.resolve_agent_subject(other.arguments.subject)
        )
    if case == "pins":
        service = AgentExecutionService(env.owning_factory, env.credentials, env.store)
    if case == "bytes":
        monkeypatch.setattr(env.store, "open", lambda identity: b"incorrect retained bytes")
    if case == "scope":
        project = env.identity.create_project_with_owner(
            env.owner, name="Other intent project", request_id=new_uuid7()
        )
        command = replace(command, project_id=project)
    if case == "unfrozen":
        from tests.application_compat import LegacyApplicationService

        from researchbase.application.commands import CreateArtifactVersionCommand
        from researchbase.domain.artifact import ArtifactId
        from researchbase.foundation.execution_context import ExecutionContext
        from researchbase.foundation.time import SystemClock

        with env.owning_factory() as uow:
            artifact = uow.agents.configuration(command.arguments.harness_artifact_version_id)
        draft = LegacyApplicationService(
            env.owning_factory, SystemClock(), env.store
        ).create_artifact_version(
            CreateArtifactVersionCommand(
                ArtifactId(artifact["artifact_id"]),
                b"draft",
                None,
                None,
                "text/plain",
                5,
                None,
                ExecutionContext(
                    actor_id=env.owner.actor_id, request_id=new_uuid7(), client_type="test"
                ),
            )
        )
        command = replace(
            command, arguments=replace(command.arguments, harness_artifact_version_id=draft.id)
        )
    before = effect_counts(env)
    with pytest.raises(ResearchBaseError) as exc:
        if case == "untrusted":
            command = replace(command, caller=object())
        service.execute(command)
    assert exc.value.code == code
    assert effect_counts(env) == before


@pytest.mark.parametrize(
    "boundary",
    [
        "agent_command_receipts",
        "agent_execution_instances",
        "agent_execution_events",
        "constraints",
        "credentials",
    ],
)
def test_intent_failure_rolls_back_all_three_effects(intent_env, monkeypatch, boundary):
    env = intent_env
    before = effect_counts(env)
    original = SqlAlchemyExecutionRepository.insert
    inserted = []

    def insert(repo, table, row):
        result = original(repo, table, row)
        inserted.append(table)
        if table == boundary:
            raise RuntimeError("injected after write")
        return result

    monkeypatch.setattr(SqlAlchemyExecutionRepository, "insert", insert)
    if boundary == "constraints":
        original_force = SqlAlchemyExecutionRepository.force_constraints

        def force(repo):
            original_force(repo)
            raise RuntimeError("injected after constraint closure")

        monkeypatch.setattr(SqlAlchemyExecutionRepository, "force_constraints", force)
    if boundary == "credentials":

        def valid(principal, at):
            return len(inserted) < 3

        monkeypatch.setattr(env.credentials, "is_valid", valid)
    with pytest.raises((RuntimeError, ResearchBaseError)):
        env.intents.execute(env.intent)
    assert effect_counts(env) == before


def test_selected_step_and_typed_inputs_preserve_both_owners(intent_env):
    from researchbase.foundation.hashing import sha256_canonical_json

    env = intent_env
    input_ref = {"type": "ARTIFACT_VERSION", "id": str(env.config)}
    create = env.planning.command(
        arguments={
            "task_type": "OTHER",
            "objective": "Input provenance",
            "strategy_id": "human_guided_research",
            "strategy_version": "1.0.0",
            "inputs": [input_ref],
        }
    )
    env.planning.service.execute(env.owner, create)
    selected, other = new_uuid7(), new_uuid7()
    env.planning.plan(
        create.task_id,
        nodes=[
            {"step_id": str(selected), "step_type": "PLAN", "ordinal": 1, "inputs": [input_ref]},
            {"step_id": str(other), "step_type": "PLAN", "ordinal": 2, "inputs": [input_ref]},
        ],
    )
    env.planning.service.execute(
        env.owner, env.planning.command("seal_task_plan", create.task_id, 2)
    )
    command = replace(
        env.intent,
        arguments=replace(
            env.intent.arguments, research_task_id=create.task_id, research_task_step_id=selected
        ),
    )
    result = env.intents.execute(command)
    with env.owning_factory() as uow:
        uow.begin_formal_read()
        row = uow.executions.one(
            "SELECT pr302s2_input_material(:id) AS material", id=result.result_execution_id
        )
    material = row["material"]
    assert len(material["inputs"]) == 2
    assert {item["owner_kind"] for item in material["inputs"]} == {"TASK", "STEP"}
    assert all(item["hash_scheme"] is None for item in material["inputs"])
    dto = env.intents.get_agent_execution(
        GetAgentExecution(env.project, result.result_execution_id, env.owner)
    )
    assert dto.input_ref_hash == sha256_canonical_json(material)
