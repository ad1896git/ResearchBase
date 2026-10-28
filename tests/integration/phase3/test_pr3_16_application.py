"""Real Application acceptance on ordinary-role PostgreSQL with production guards."""

from dataclasses import replace

import pytest
from sqlalchemy import text
from tests.integration.phase3.conftest import Credentials
from tests.integration.phase3.search_fixtures import _search_env as _search_env
from tests.unit.phase3.test_experiment_search import pg_command

from researchbase.agent_runtime.application.experiment_search import ExperimentSearchService
from researchbase.agent_runtime.application.search_contracts import (
    AppendSearchArguments,
    CreateSearchArguments,
)
from researchbase.agent_runtime.domain.experiment_search import BranchKind
from researchbase.application.commands import (
    ApplicationService,
    CreateExperimentSpecCommand,
    CreateHypothesisCommand,
    FreezeExperimentSpecCommand,
    FreezeHypothesisCommand,
)
from researchbase.domain.experiment import ExperimentSpecId, ExperimentSpecVersionId
from researchbase.domain.organization import ProjectId
from researchbase.domain.research import HypothesisId, HypothesisVersionId
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.ids import new_uuid7
from researchbase.foundation.time import SystemClock
from researchbase.persistence.experiment_search_repository import (
    SqlAlchemyExperimentSearchRepository,
)

CREATE_EFFECT_TABLES = (
    "experiment_search_sessions",
    "experiment_search_events",
    "research_task_command_receipts",
    "research_task_events",
    "research_task_receipt_events",
)


def snapshot(env):
    """Capture every public application row, including all scientific hash columns.

    Observing the entire schema also covers provenance relations, Run seals,
    evidence, governance and safety state without maintaining a partial allowlist.
    """
    with env.engine.connect() as conn:
        tables = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' AND table_type='BASE TABLE' "
                "AND table_name <> 'alembic_version' ORDER BY table_name"
            )
        ).scalars()
        return {
            table: sorted(
                (
                    dict(row)
                    for row in conn.execute(
                        text('SELECT * FROM public."' + table.replace('"', '""') + '"')
                    ).mappings()
                ),
                key=repr,
            )
            for table in tables
        }


def assert_create_effects(before, after, task, revision):
    assert before.keys() == after.keys()
    for table in before:
        if table in CREATE_EFFECT_TABLES:
            assert len(after[table]) == len(before[table]) + 1, table
            assert all(row in after[table] for row in before[table]), table
        elif table == "research_tasks":
            prior = next(row for row in before[table] if row["id"] == task)
            current = next(row for row in after[table] if row["id"] == task)
            assert prior["row_version"] == revision
            assert current == {**prior, "row_version": revision + 1}
            expected = [
                {**row, "row_version": revision + 1} if row["id"] == task else row
                for row in before[table]
            ]
            assert after[table] == sorted(expected, key=repr)
        else:
            assert after[table] == before[table], table


def frozen_references(p):
    """Create and freeze exact owning-domain versions through public commands."""
    app = ApplicationService(p.factory, SystemClock(), p.store)
    context = ExecutionContext(
        actor_id=p.principal.actor_id, request_id=new_uuid7(), client_type="test"
    )
    hypothesis = app.create_hypothesis(
        CreateHypothesisCommand(
            ProjectId(p.project),
            "Treatment improves outcome.",
            "increase",
            {"threshold": 0.1},
            "Search root hypothesis",
            context,
        )
    )
    assert hypothesis.version_id is not None
    hv = app.freeze_hypothesis(
        FreezeHypothesisCommand(
            HypothesisId(hypothesis.id), HypothesisVersionId(hypothesis.version_id), context, 1
        )
    )
    spec = app.create_experiment_spec(
        CreateExperimentSpecCommand(
            ProjectId(p.project),
            HypothesisId(hypothesis.id),
            "Search root experiment",
            "Measure treatment effect",
            {"arms": ["control", "treatment"]},
            [{"name": "outcome"}],
            {"kind": "fixed"},
            {"test": "difference-in-means"},
            context,
        )
    )
    assert spec.version_id is not None
    sv = app.freeze_experiment_spec(
        FreezeExperimentSpecCommand(
            ExperimentSpecId(spec.id), ExperimentSpecVersionId(spec.version_id), context, 1
        )
    )
    assert hv.content_hash is not None and sv.content_hash is not None
    assert len(hv.content_hash) == len(sv.content_hash) == 64
    return hv, sv


def test_create_session_application_human_and_agent_atomic_pg(search_env):
    env = search_env
    hypothesis, spec = frozen_references(env.p)
    before = snapshot(env)
    command = replace(
        pg_command(env), arguments=CreateSearchArguments(new_uuid7(), hypothesis.id, spec.id)
    )
    result = ExperimentSearchService(env.p.factory, Credentials()).create_search_session(
        env.p.principal, command
    )
    after = snapshot(env)
    assert_create_effects(before, after, env.task, command.expected_row_version)
    with env.engine.connect() as conn:
        receipt = (
            conn.execute(
                text("SELECT * FROM research_task_command_receipts WHERE command_id=:id"),
                {"id": command.command_id},
            )
            .mappings()
            .one()
        )
        session = (
            conn.execute(
                text("SELECT * FROM experiment_search_sessions WHERE id=:id"),
                {"id": result.session_id},
            )
            .mappings()
            .one()
        )
        event = (
            conn.execute(
                text("SELECT * FROM experiment_search_events WHERE id=:id"),
                {"id": result.search_event_id},
            )
            .mappings()
            .one()
        )
        link = (
            conn.execute(
                text("SELECT * FROM research_task_receipt_events WHERE receipt_id=:id"),
                {"id": receipt["id"]},
            )
            .mappings()
            .one()
        )
        assert receipt["request_hash"] == command.request_hash(env.p.principal.actor_id)
        assert receipt["result_search_session_id"] == session["id"] == result.session_id
        assert receipt["result_search_event_id"] == event["id"] == result.search_event_id
        assert link["event_id"] == result.command_result.task_event_ids[0]
        assert session["receipt_id"] == event["receipt_id"] == receipt["id"]
        assert (session["root_hypothesis_version_id"], session["root_hypothesis_content_hash"]) == (
            hypothesis.id,
            hypothesis.content_hash,
        )
        assert (
            session["root_experiment_spec_version_id"],
            session["root_experiment_spec_content_hash"],
        ) == (spec.id, spec.content_hash)
        assert result.command_result.resulting_row_version == command.expected_row_version + 1


def test_create_session_replay_and_conflict_pg(search_env):
    env = search_env
    service = ExperimentSearchService(env.p.factory, Credentials())
    command = pg_command(env)
    before = snapshot(env)
    result = service.create_search_session(env.p.principal, command)
    saved = snapshot(env)
    assert_create_effects(before, saved, env.task, command.expected_row_version)
    replay = service.create_search_session(env.p.principal, command)
    assert replay == replace(result, command_result=replace(result.command_result, replayed=True))
    assert snapshot(env) == saved
    changed = replace(command, arguments=CreateSearchArguments(new_uuid7()))
    with pytest.raises(ResearchBaseError) as exc:
        service.create_search_session(env.p.principal, changed)
    assert exc.value.code == ErrorCode.IDEMPOTENCY_CONFLICT
    assert snapshot(env) == saved

    class Revoked:
        def is_valid(self, principal, at):
            return False

    with pytest.raises(ResearchBaseError) as exc:
        ExperimentSearchService(env.p.factory, Revoked()).create_search_session(
            env.p.principal, command
        )
    assert exc.value.code in (ErrorCode.FORBIDDEN, ErrorCode.AUTHENTICATION_REQUIRED)
    assert snapshot(env) == saved


@pytest.mark.parametrize("target", ["insert", "constraints", "final"])
def test_create_session_rollback_after_effects_pg(search_env, monkeypatch, target):
    env = search_env
    before = snapshot(env)
    original = SqlAlchemyExperimentSearchRepository._notify
    reached = []

    def notify(repo, stage):
        original(repo, stage)
        if stage.operation == target and (
            target != "insert" or stage.table == "research_task_receipt_events"
        ):
            reached.append(stage.operation)
            raise RuntimeError("injected after real storage effect")

    monkeypatch.setattr(SqlAlchemyExperimentSearchRepository, "_notify", notify)
    with pytest.raises(RuntimeError, match="injected"):
        ExperimentSearchService(env.p.factory, Credentials()).create_search_session(
            env.p.principal, pg_command(env)
        )
    assert reached == [target]
    assert snapshot(env) == before


def test_append_denied_without_d1_pg(search_env):
    env = search_env
    command = pg_command(env)
    command = replace(
        command,
        command_name="append_search_node",
        arguments=AppendSearchArguments(
            new_uuid7(), new_uuid7(), BranchKind.NEW_DIRECTION, "test", new_uuid7()
        ),
    )
    before = snapshot(env)
    with pytest.raises(ResearchBaseError) as exc:
        ExperimentSearchService(env.p.factory, Credentials()).append_search_node(
            env.p.principal, command
        )
    assert exc.value.code == ErrorCode.INVALID_STATE_TRANSITION
    assert snapshot(env) == before


def test_create_session_agent_atomic_pg(agents):
    from types import SimpleNamespace

    from sqlalchemy import create_engine
    from tests.integration.phase2.pr2_20_support import upgrade
    from tests.integration.phase3.agent_fixtures import enrollment
    from tests.integration.phase3.conftest import PlanningFixture
    from tests.integration.phase3.test_pr3_04_application import approve, bind

    from researchbase.agent_runtime.application.research_task import ResearchTaskService
    from researchbase.agent_runtime.application.search_contracts import SearchCommand

    env = agents
    enrolled = enrollment(env)
    env.service.execute(enrolled)
    principal = env.identity.resolve_agent_subject(enrolled.arguments.subject)
    upgrade(env.url, "0082_experiment_search_core")
    with env.engine.connect() as conn:
        role = conn.execute(text("SELECT current_user")).scalar_one()
    admin = create_engine(env.url)
    try:
        with admin.begin() as conn:
            conn.execute(text(f'GRANT SELECT ON ALL TABLES IN SCHEMA public TO "{role}"'))
            conn.execute(
                text(
                    "GRANT SELECT,INSERT ON experiment_search_sessions,experiment_search_events,"
                    "experiment_search_nodes,experiment_search_node_runs TO " + f'"{role}"'
                )
            )
        p = PlanningFixture(
            env.engine,
            env.factory,
            ResearchTaskService(env.factory, Credentials(), env.store),
            env.owner,
            env.project,
            env.url,
            env.store,
        )
        task = p.create()
        bind(p, task)
        approve(p, task, 2)
        hypothesis, spec = frozen_references(p)
        observer = SimpleNamespace(engine=env.engine, task=task)
        before = snapshot(observer)
        command = SearchCommand(
            env.project,
            new_uuid7(),
            task,
            4,
            "create_search_session",
            CreateSearchArguments(new_uuid7(), hypothesis.id, spec.id),
        )
        result = ExperimentSearchService(env.factory, Credentials()).create_search_session(
            principal, command
        )
        after = snapshot(observer)
        assert_create_effects(before, after, task, command.expected_row_version)
        assert result.command_result.resulting_row_version == 5
        with env.engine.connect() as conn:
            receipt = (
                conn.execute(
                    text("SELECT * FROM research_task_command_receipts WHERE command_id=:id"),
                    {"id": command.command_id},
                )
                .mappings()
                .one()
            )
            session = (
                conn.execute(
                    text("SELECT * FROM experiment_search_sessions WHERE id=:id"),
                    {"id": result.session_id},
                )
                .mappings()
                .one()
            )
            event = (
                conn.execute(
                    text("SELECT * FROM experiment_search_events WHERE id=:id"),
                    {"id": result.search_event_id},
                )
                .mappings()
                .one()
            )
            link = (
                conn.execute(
                    text("SELECT * FROM research_task_receipt_events WHERE receipt_id=:id"),
                    {"id": receipt["id"]},
                )
                .mappings()
                .one()
            )
            assert receipt["request_hash"] == command.request_hash(principal.actor_id)
            assert receipt["result_search_session_id"] == session["id"]
            assert receipt["result_search_event_id"] == event["id"]
            assert session["receipt_id"] == event["receipt_id"] == receipt["id"]
            assert session["created_by"] == principal.actor_id
            assert (
                session["root_hypothesis_version_id"],
                session["root_hypothesis_content_hash"],
            ) == (hypothesis.id, hypothesis.content_hash)
            assert (
                session["root_experiment_spec_version_id"],
                session["root_experiment_spec_content_hash"],
            ) == (spec.id, spec.content_hash)
            assert link["event_id"] == result.command_result.task_event_ids[0]
            assert (
                conn.execute(
                    text("SELECT count(*) FROM agent_versions WHERE actor_id=:id"),
                    {"id": principal.actor_id},
                ).scalar_one()
                == 0
            )
    finally:
        admin.dispose()


def test_replay_after_current_authority_revocation_pg(search_env):
    from tests.integration.phase2.test_pr2_00_ownership import _add_owner

    from researchbase.domain.phase2_identity import VerifiedPrincipal

    env = search_env
    actor = new_uuid7()
    with env.engine.begin() as conn:
        now = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
        _, role = _add_owner(
            conn,
            actor_id=actor,
            project_id=env.p.project,
            now=now,
            event_kind="ACTIVATED",
            request_id=new_uuid7(),
        )
    principal = VerifiedPrincipal(
        actor, "test-deployment", "OS_UID", str(actor.int), f"uid:{actor.int}", now
    )
    service = ExperimentSearchService(env.p.factory, Credentials())
    command = pg_command(env)
    before = snapshot(env)
    service.create_search_session(principal, command)
    assert_create_effects(before, snapshot(env), env.task, command.expected_row_version)
    with env.engine.begin() as conn:
        conn.execute(text("SELECT rb_phase2_lock_project(:p)"), {"p": env.p.project})
        at = conn.execute(text("SELECT clock_timestamp()")).scalar_one()
        conn.execute(
            text(
                "UPDATE project_role_assignments SET effective_until=:at,"
                "row_version=row_version+1 WHERE id=:id"
            ),
            {"at": at, "id": role},
        )
        conn.execute(
            text(
                "INSERT INTO project_role_events "
                "(id,role_assignment_id,actor_id,event_kind,occurred_at,reason,request_id) "
                "VALUES (:id,:role,:actor,'CLOSED',:at,'Revoked',:request)"
            ),
            {"id": new_uuid7(), "role": role, "actor": actor, "at": at, "request": new_uuid7()},
        )
    before = snapshot(env)
    with pytest.raises(ResearchBaseError) as exc:
        service.create_search_session(principal, command)
    assert exc.value.code == ErrorCode.FORBIDDEN
    assert snapshot(env) == before


def test_stale_cas_and_wrong_scope_pg(search_env):
    env = search_env
    service = ExperimentSearchService(env.p.factory, Credentials())
    command = pg_command(env)
    before = snapshot(env)
    for invalid in (
        replace(command, expected_row_version=command.expected_row_version - 1),
        replace(command, project_id=new_uuid7()),
    ):
        with pytest.raises(ResearchBaseError):
            service.create_search_session(env.p.principal, invalid)
        assert snapshot(env) == before
