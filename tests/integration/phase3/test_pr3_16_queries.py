"""Application formal reads on disposable PG18 with all production guards enabled."""

from dataclasses import asdict, replace
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event, text
from tests.integration.phase2.pr2_20_support import upgrade
from tests.integration.phase3.agent_fixtures import enrollment
from tests.integration.phase3.conftest import Credentials, PlanningFixture
from tests.integration.phase3.search_fixtures import _search_env as _search_env
from tests.integration.phase3.test_pr3_04_application import approve, bind, reserve
from tests.integration.phase3.test_pr3_16_application import frozen_references, snapshot

from researchbase.agent_runtime.application.experiment_search import ExperimentSearchService
from researchbase.agent_runtime.application.research_task import ResearchTaskService
from researchbase.agent_runtime.application.search_contracts import (
    BranchLineageRequest,
    CreateSearchArguments,
    SearchCommand,
    SearchReadRequest,
)
from researchbase.agent_runtime.services.fake_consumer import TrustedFakeConsumer
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.ids import new_uuid7
from researchbase.persistence.experiment_search_queries import SqlAlchemyExperimentSearchQueries
from researchbase.persistence.uow import SqlAlchemyUnitOfWork


@pytest.fixture
def query_env(search_env):
    env = SimpleNamespace(**vars(search_env))
    command = env.p.command(
        arguments=dict(
            task_type="OTHER",
            objective="  Exact owning goal e\u0301  ",
            strategy_id="human_guided_research",
            strategy_version="1.0.0",
        )
    )
    env.p.service.execute(env.p.principal, command)
    env.task = command.task_id
    bind(env.p, env.task)
    approve(env.p, env.task, 2)
    hypothesis, spec = frozen_references(env.p)
    env.service = ExperimentSearchService(env.p.factory, Credentials())
    env.command = SearchCommand(
        env.p.project,
        new_uuid7(),
        env.task,
        4,
        "create_search_session",
        CreateSearchArguments(new_uuid7(), hypothesis.id, spec.id),
    )
    env.session = env.service.create_search_session(env.p.principal, env.command).session_id
    env.request = SearchReadRequest(env.p.project, env.task, env.session)
    return env


def test_formal_reads_application_pg(query_env, monkeypatch):
    env = query_env
    before = snapshot(env)
    statements, begins, commits, rollbacks, configured = [], [], [], [], []
    original = SqlAlchemyUnitOfWork.begin_formal_read

    def formal(uow):
        original(uow)
        session = uow._require_session()
        configured.append(
            tuple(
                session.execute(
                    text(
                        "SELECT current_setting('transaction_isolation'),"
                        "current_setting('transaction_read_only'),current_setting('server_version_num')"
                    )
                ).one()
            )
        )

    def sql(conn, cursor, statement, parameters, context, many):
        statements.append(statement)

    def begin(conn):
        begins.append(conn)

    def commit(conn):
        commits.append(conn)

    def rollback(conn):
        rollbacks.append(conn)

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "begin_formal_read", formal)
    listeners = [
        ("before_cursor_execute", sql),
        ("begin", begin),
        ("commit", commit),
        ("rollback", rollback),
    ]
    for name, callback in listeners:
        event.listen(env.engine, name, callback)
    try:
        tree = env.service.get_experiment_search_tree(env.p.principal, env.request)
        assert len(begins) == len(rollbacks) == len(configured) == 1 and not commits
        assert configured[0][:2] == ("repeatable read", "on")
        assert int(configured[0][2]) // 10000 == 18
        assert tree.nodes == tree.run_links == ()
        assert [e.event_type for e in tree.events] == ["SESSION_CREATED"]
        assert (
            tree.session.root_hypothesis_version_id
            == env.command.arguments.root_hypothesis_version_id
        )
        assert (
            tree.session.root_experiment_spec_version_id
            == env.command.arguments.root_experiment_spec_version_id
        )
        assert tree.task_safety.task_row_version == 5
        assert not tree.task_safety.execution_enabled
        upper = "\n".join(statements).upper()
        assert all(s.lstrip().upper().startswith(("SELECT", "SHOW")) for s in statements)
        assert all(
            token not in upper
            for token in ("FOR UPDATE", "FOR SHARE", "LOCK TABLE", "PG_ADVISORY", "SAVEPOINT")
        )
    finally:
        for name, callback in listeners:
            event.remove(env.engine, name, callback)
    with env.engine.connect() as conn:
        objective = conn.execute(
            text("SELECT objective FROM research_tasks WHERE id=:id"), {"id": env.task}
        ).scalar_one()
    assert asdict(tree.session.objective_definition) == dict(
        source="RESEARCH_TASK", research_task_id=env.task, text=objective
    )
    budget = env.service.get_search_budget(env.p.principal, env.request)
    assert budget.task_safety == tree.task_safety
    with pytest.raises(ResearchBaseError) as exc:
        env.service.get_branch_lineage(
            env.p.principal, BranchLineageRequest(env.p.project, env.task, env.session, new_uuid7())
        )
    assert exc.value.code == ErrorCode.NOT_FOUND and exc.value.details is None
    assert snapshot(env) == before


def test_budget_projection_is_coherent_with_concurrent_commit_pg(query_env, monkeypatch):
    env = query_env
    reached = []
    original = SqlAlchemyExperimentSearchQueries.search_session

    def read(queries, identity):
        saved = original(queries, identity)
        if identity == env.session and not reached:
            reached.append(True)
            # Existing trusted safety consumer only: no tree-node spend/producer.
            TrustedFakeConsumer(env.p.factory, Credentials(), env.p.store).execute(
                env.p.principal, reserve(env.p, env.task, 5)
            )
        return saved

    monkeypatch.setattr(SqlAlchemyExperimentSearchQueries, "search_session", read)
    old = env.service.get_experiment_search_tree(env.p.principal, env.request)
    assert reached == [True]
    assert old.task_safety.task_row_version == 5
    assert old.task_safety.parallel_branches == old.task_safety.reserved.llm_calls == 0
    current = env.service.get_search_budget(env.p.principal, env.request)
    assert current.task_safety.task_row_version == 6
    assert current.task_safety.parallel_branches == current.task_safety.reserved.llm_calls == 1
    # No search read settled/refunded the outstanding reservation.
    with env.engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM budget_usage_records WHERE research_task_id=:id"),
                {"id": env.task},
            ).scalar_one()
            == 0
        )
        assert (
            conn.execute(
                text("SELECT count(*) FROM experiment_search_nodes WHERE research_task_id=:id"),
                {"id": env.task},
            ).scalar_one()
            == 0
        )


@pytest.mark.parametrize(
    "verifier",
    [
        None,
        SimpleNamespace(),
        SimpleNamespace(is_valid=lambda p, at: False),
        SimpleNamespace(is_valid=lambda p, at: 1),
    ],
)
def test_invalid_verifier_and_absent_targets_share_denial_pg(query_env, verifier):
    env = query_env
    service = ExperimentSearchService(env.p.factory, verifier)
    before = snapshot(env)
    errors = []
    for request in (env.request, replace(env.request, task_id=new_uuid7(), session_id=new_uuid7())):
        with pytest.raises(ResearchBaseError) as exc:
            service.get_experiment_search_tree(env.p.principal, request)
        assert exc.value.code == ErrorCode.FORBIDDEN and exc.value.details is None
        errors.append(str(exc.value))
    assert errors[0] == errors[1] and snapshot(env) == before


def test_read_target_scope_and_closed_denials_pg(query_env):
    env = query_env
    before = snapshot(env)
    other = env.p.create()
    for request in (
        replace(env.request, task_id=other),
        replace(env.request, session_id=new_uuid7()),
    ):
        with pytest.raises(ResearchBaseError) as exc:
            env.service.get_experiment_search_tree(env.p.principal, request)
        assert exc.value.code == ErrorCode.NOT_FOUND and exc.value.details is None
    # The only changes are the explicitly created second task's command effects.
    after = snapshot(env)
    for table in (
        "experiment_search_sessions",
        "experiment_search_nodes",
        "experiment_search_events",
        "budget_reservations",
        "budget_usage_records",
    ):
        assert before[table] == after[table]


def test_revoked_current_read_entitlement_denies_without_disclosure_pg(query_env):
    from tests.integration.phase2.test_pr2_00_ownership import _add_owner

    from researchbase.domain.phase2_identity import VerifiedPrincipal

    env = query_env
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
    assert env.service.get_experiment_search_tree(principal, env.request).session.id == env.session
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
            dict(id=new_uuid7(), role=role, actor=actor, at=at, request=new_uuid7()),
        )
    before = snapshot(env)
    messages = []
    for request in (env.request, replace(env.request, session_id=new_uuid7())):
        with pytest.raises(ResearchBaseError) as exc:
            env.service.get_experiment_search_tree(principal, request)
        assert exc.value.code == ErrorCode.FORBIDDEN and exc.value.details is None
        messages.append(str(exc.value))
    assert messages[0] == messages[1] and snapshot(env) == before


def test_agent_reads_without_version_or_execution_pg(agents):
    env = agents
    command = enrollment(env)
    env.service.execute(command)
    principal = env.identity.resolve_agent_subject(command.arguments.subject)
    upgrade(env.url, "0082_experiment_search_core")
    with env.engine.connect() as conn:
        role = conn.execute(text("SELECT current_user")).scalar_one()
    admin = create_engine(env.url)
    try:
        with admin.begin() as conn:
            conn.execute(text(f'GRANT SELECT ON ALL TABLES IN SCHEMA public TO "{role}"'))
            conn.execute(
                text(
                    "GRANT INSERT ON experiment_search_sessions,experiment_search_events "
                    f'TO "{role}"'
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
        service = ExperimentSearchService(env.factory, Credentials())
        create = SearchCommand(
            env.project,
            new_uuid7(),
            task,
            4,
            "create_search_session",
            CreateSearchArguments(new_uuid7()),
        )
        session = service.create_search_session(principal, create).session_id
        before = snapshot(SimpleNamespace(engine=env.engine))
        tree = service.get_experiment_search_tree(
            principal, SearchReadRequest(env.project, task, session)
        )
        assert tree.session.created_by == principal.actor_id
        assert tree.nodes == tree.run_links == ()
        assert not tree.task_safety.execution_enabled
        assert snapshot(SimpleNamespace(engine=env.engine)) == before
        with env.engine.connect() as conn:
            assert (
                conn.execute(
                    text("SELECT count(*) FROM agent_versions WHERE actor_id=:id"),
                    {"id": principal.actor_id},
                ).scalar_one()
                == 0
            )
            assert (
                conn.execute(
                    text("SELECT count(*) FROM agent_execution_instances WHERE actor_id=:id"),
                    {"id": principal.actor_id},
                ).scalar_one()
                == 0
            )
    finally:
        admin.dispose()
