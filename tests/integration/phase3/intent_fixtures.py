"""Disposable Application-only intent prerequisites; verifier intake is test-only."""

import json
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tests.integration.phase2.pr2_20_support import upgrade
from tests.integration.phase2.test_pr2_10_binding_contract import _artifact
from tests.integration.phase3.agent_fixtures import enrollment, register
from tests.integration.phase3.conftest import PlanningFixture

from researchbase.agent_runtime.application.agent_executions import AgentExecutionService
from researchbase.agent_runtime.application.execution_contracts import (
    CreateAgentExecution,
    ExecutionCommand,
)
from researchbase.agent_runtime.application.research_task import ResearchTaskService
from researchbase.foundation.hashing import sha256_bytes
from researchbase.foundation.ids import new_uuid7
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


@pytest.fixture(name="intent_env")
def _intent_env(agents):
    env = agents
    provision = enrollment(env)
    env.service.execute(provision)
    version = register(env, provision.arguments.actor_id)
    env.service.execute(version)
    # Migrate as owning role; the accepted S1 fixture deliberately uses a normal role.
    upgrade(env.url)
    engine = create_engine(
        env.url, connect_args={"options": "-c lock_timeout=10s -c statement_timeout=30s"}
    )
    from sqlalchemy import text

    with engine.connect() as conn:
        server_version, role, database = conn.execute(
            text("SELECT current_setting('server_version'), current_user, current_database()")
        ).one()
        assert int(server_version.split(".")[0]) == 18
        print("INTENT_PG_IDENTITY", server_version, role, database)
    sessions = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    def factory():
        return SqlAlchemyUnitOfWork(sessions)

    tasks = ResearchTaskService(factory, env.credentials, env.store)
    planning = PlanningFixture(engine, factory, tasks, env.owner, env.project, env.url, env.store)
    task, _ = planning.plan()
    tasks.execute(env.owner, planning.command("seal_task_plan", task, 2))
    manifest = {
        "schema_version": 1,
        "researchbase_revision": "75d559a",
        "agent_runtime_revision": "75d559a",
        "model_profile_id": version.arguments.model_profile_id,
        "prompt_template_version": version.arguments.prompt_template_version,
        "agents_md_sha256": "a" * 64,
        "config_sha256": str(sha256_bytes(b'{"test":"configuration"}')),
        "strategy_id": "human_guided_research",
        "strategy_revision": "1.0.0",
        **{
            key: []
            for key in (
                "skills",
                "plugins",
                "adapters",
                "hooks",
                "mcp_capabilities",
                "reference_libraries",
            )
        },
    }
    harness = _artifact(
        factory,
        env.store,
        env.owner,
        env.project,
        json.dumps(manifest, ensure_ascii=False).encode(),
        "configuration",
    )
    service = AgentExecutionService(factory, env.credentials, env.store, pins=env.credentials)
    args = CreateAgentExecution(
        new_uuid7(), version.arguments.agent_version_id, task, None, 3, harness
    )
    command = ExecutionCommand(
        env.project, env.owner, new_uuid7(), "create_agent_execution", None, args
    )
    try:
        yield SimpleNamespace(
            **vars(env),
            owning_engine=engine,
            owning_factory=factory,
            intents=service,
            intent=command,
            planning=planning,
            provision=provision,
            version_command=version,
        )
    finally:
        engine.dispose()


def intent_rows(env) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    from dataclasses import fields

    from researchbase.agent_runtime.application.agent_contracts import AgentCommandResult
    from researchbase.foundation.hashing import sha256_canonical_json

    c = env.intent
    harness_hash, _, material = env.intents._preflight(c)
    receipt: dict[str, Any] = {
        f.name: None for f in fields(AgentCommandResult) if f.name.startswith("result_")
    }
    receipt.update(
        id=new_uuid7(),
        project_id=c.project_id,
        caller_actor_id=c.caller.actor_id,
        command_id=c.command_id,
        operation=c.operation,
        request_hash=c.request_hash(),
        hash_scheme="sha256-cjson-v1",
        result_execution_id=c.arguments.execution_id,
        result_execution_event_id=new_uuid7(),
        resulting_revision=1,
        recorded_at=c.caller.verified_at,
    )
    intent: dict[str, Any] = dict(
        id=c.arguments.execution_id,
        project_id=c.project_id,
        research_task_id=c.arguments.research_task_id,
        research_task_step_id=c.arguments.research_task_step_id,
        task_revision_at_creation=3,
        agent_version_id=c.arguments.agent_version_id,
        actor_id=env.provision.arguments.actor_id,
        status="CREATED",
        revision=1,
        created_at=receipt["recorded_at"],
        input_ref_hash=str(sha256_canonical_json(material)),
        input_ref_hash_scheme="sha256-cjson-v1",
        harness_artifact_version_id=c.arguments.harness_artifact_version_id,
        harness_content_hash=harness_hash,
        harness_hash_scheme="sha256-bytes-v1",
    )
    event: dict[str, Any] = dict(
        id=receipt["result_execution_event_id"],
        execution_id=intent["id"],
        sequence=1,
        prior_status=None,
        new_status="CREATED",
        actor_id=c.caller.actor_id,
        occurred_at=receipt["recorded_at"],
        reason="Execution intent created.",
        receipt_id=receipt["id"],
    )
    return receipt, intent, event


def effect_counts(env):
    from sqlalchemy import text

    tables = (
        "agent_execution_instances",
        "agent_execution_events",
        "agent_command_receipts",
        "research_tasks",
        "research_task_steps",
        "research_task_events",
        "research_task_command_receipts",
        "budget_reservations",
        "budget_usage_records",
        "capability_invocations",
        "strategy_candidate_captures",
        "artifacts",
        "artifact_versions",
    )
    with env.owning_engine.connect() as conn:
        return {
            table: conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
            for table in tables
        }


def human_researcher(env, role="RESEARCHER"):
    from datetime import UTC, datetime

    from researchbase.application.phase2_identity import (
        AssignProjectRole,
        ProvisionActor,
        ProvisioningAttestation,
        VerifiedSubject,
    )
    from researchbase.domain.phase2_identity import VerifiedPrincipal

    actor = new_uuid7()
    subject = VerifiedSubject(
        env.owner.deployment_id, "MTLS_URI", f"spiffe://test/human/{actor}", f"human-cert-{actor}"
    )
    att = ProvisioningAttestation(
        actor,
        subject.deployment_id,
        subject.subject_kind,
        subject.subject_value,
        subject.credential_id,
        env.operator,
        "e" * 64,
        "test:human-proof",
        "human intake",
    )
    env.identity.provision_actor(
        ProvisionActor(env.owner, subject, actor, "Researcher", att, new_uuid7())
    )
    env.identity.assign_project_role(
        AssignProjectRole(env.owner, env.project, actor, role, "intent test", new_uuid7())
    )
    return VerifiedPrincipal(
        actor,
        subject.deployment_id,
        subject.subject_kind,
        subject.subject_value,
        subject.credential_id,
        datetime.now(UTC),
    )
