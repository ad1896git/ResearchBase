"""Independent-review counterexamples: real PostgreSQL, no mocked DB guards."""

from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Event
from time import monotonic
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from researchbase.application.commands import (
    AbandonArtifactVersionCommand,
    AbandonClaimVersionCommand,
    AbandonExperimentSpecVersionCommand,
    AbandonHypothesisVersionCommand,
    AbandonMetricDefinitionVersionCommand,
    AbandonResearchQuestionVersionCommand,
    CreateArtifactCommand,
    CreateArtifactVersionCommand,
    CreateClaimCommand,
    CreateExperimentSpecCommand,
    CreateHypothesisCommand,
    CreateMetricDefinitionCommand,
    CreateResearchQuestionCommand,
    FreezeResearchQuestionCommand,
    ReviseResearchQuestionCommand,
)
from researchbase.application.literature_search_plan import (
    CreateLiteratureSearchPlan,
    EditLiteratureSearchPlanQuestions,
    LiteratureSearchPlanService,
    TransitionLiteratureSearchPlanVersion,
)
from researchbase.domain.organization import ProjectId
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.time import SystemClock
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.application_compat import LegacyApplicationService
from tests.integration.phase2.test_pr2_01_source_identity import _authorized_service
from tests.integration.phase2.test_pr2_03_literature_search_plan_application import (
    _AlwaysValidCredential,
    _material,
    _question,
)


def _setup(url, *, migration_revision="head"):
    engine, _, _, principal, project = _authorized_service(
        url, migration_revision=migration_revision
    )
    service = LiteratureSearchPlanService(
        lambda: SqlAlchemyUnitOfWork(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        ),
        _AlwaysValidCredential(),
    )
    result = service.create(
        CreateLiteratureSearchPlan(
            principal, project, _material(UUID(int=0), language_scope=()), uuid4()
        )
    )
    return (
        engine,
        service,
        principal,
        project,
        UUID(str(result["plan_id"])),
        UUID(str(result["version_id"])),
    )


def _freeze(engine, service, principal, project, plan, version):
    _, qv, _ = _question(engine, project, principal.actor_id)
    service.add_question(
        EditLiteratureSearchPlanQuestions(principal, project, plan, version, qv, uuid4())
    )
    return service.freeze(
        TransitionLiteratureSearchPlanVersion(principal, project, plan, version, uuid4())
    )


def _legitimate_question_history(engine, project, actor):
    application = LegacyApplicationService(
        lambda: SqlAlchemyUnitOfWork(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        ),
        SystemClock(),
    )
    context = ExecutionContext(actor_id=actor, request_id=uuid4(), client_type="test")
    question = application.create_research_question(
        CreateResearchQuestionCommand(
            project,
            "How does normalization affect evidence?",
            None,
            None,
            context,
        )
    )
    first = application.freeze_research_question(
        FreezeResearchQuestionCommand(
            question.id, question.current_version_id, context, expected_row_version=1
        )
    )
    revised = application.revise_research_question(
        ReviseResearchQuestionCommand(
            question.id,
            "How does normalization affect reviewed evidence?",
            None,
            "Legitimate immutable-history successor",
            2,
            context,
        )
    )
    second = application.freeze_research_question(
        FreezeResearchQuestionCommand(
            question.id, revised.current_version_id, context, expected_row_version=1
        )
    )
    with engine.connect() as connection:
        states = dict(
            connection.execute(
                text(
                    "SELECT id,status FROM research_question_versions "
                    "WHERE research_question_id=:id"
                ),
                {"id": question.id},
            )
            .tuples()
            .all()
        )
    assert states[first.id] == "SUPERSEDED"
    assert states[second.id] == "FROZEN"
    return UUID(str(question.id)), UUID(str(first.id)), UUID(str(second.id))


def _legitimate_abandoned_question(engine, project, actor):
    application = LegacyApplicationService(
        lambda: SqlAlchemyUnitOfWork(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        ),
        SystemClock(),
    )
    context = ExecutionContext(actor_id=actor, request_id=uuid4(), client_type="test")
    question = application.create_research_question(
        CreateResearchQuestionCommand(
            project,
            "Which abandoned question must remain unusable?",
            None,
            None,
            context,
        )
    )
    abandoned = application.abandon_research_question_version(
        AbandonResearchQuestionVersionCommand(
            question.id,
            question.current_version_id,
            1,
            context,
        )
    )
    assert question.id != question.current_version_id
    assert abandoned.status == "ABANDONED"
    assert abandoned.row_version == 2
    with engine.connect() as connection:
        durable = (
            connection.execute(
                text(
                    "SELECT research_question_id,status,row_version "
                    "FROM research_question_versions WHERE id=:id"
                ),
                {"id": abandoned.id},
            )
            .mappings()
            .one()
        )
    assert durable == {
        "research_question_id": question.id,
        "status": "ABANDONED",
        "row_version": 2,
    }
    return UUID(str(question.id)), UUID(str(abandoned.id))


@pytest.mark.parametrize(
    ("aggregate", "table", "parent_column"),
    [
        ("research_question", "research_question_versions", "research_question_id"),
        ("hypothesis", "hypothesis_versions", "hypothesis_id"),
        ("experiment_spec", "experiment_spec_versions", "experiment_spec_id"),
        ("claim", "claim_versions", "claim_id"),
        ("artifact", "artifact_versions", "artifact_id"),
        ("metric_definition", "metric_definition_versions", "metric_definition_id"),
    ],
)
def test_abandon_commands_load_the_command_version_id(
    phase2_database_url, aggregate, table, parent_column, record_property, tmp_path
):
    engine, _, principal, project_value, _, _ = _setup(phase2_database_url)
    project = ProjectId(project_value)
    application = LegacyApplicationService(
        lambda: SqlAlchemyUnitOfWork(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        ),
        SystemClock(),
        ContentAddressedFilesystemArtifactStore(tmp_path / "artifact-store"),
    )
    context = ExecutionContext(actor_id=principal.actor_id, request_id=uuid4(), client_type="test")
    if aggregate == "research_question":
        identity = application.create_research_question(
            CreateResearchQuestionCommand(project, "Question to abandon?", None, None, context)
        )
        abandoned = application.abandon_research_question_version(
            AbandonResearchQuestionVersionCommand(
                identity.id, identity.current_version_id, 1, context
            )
        )
    elif aggregate == "hypothesis":
        identity = application.create_hypothesis(
            CreateHypothesisCommand(project, "Hypothesis to abandon", None, None, None, context)
        )
        abandoned = application.abandon_hypothesis_version(
            AbandonHypothesisVersionCommand(identity.id, identity.current_version_id, 1, context)
        )
    elif aggregate == "experiment_spec":
        identity = application.create_experiment_spec(
            CreateExperimentSpecCommand(
                project,
                None,
                "Spec to abandon",
                "Verify abandon lookup",
                {"steps": ["observe"]},
                None,
                None,
                None,
                context,
            )
        )
        abandoned = application.abandon_experiment_spec_version(
            AbandonExperimentSpecVersionCommand(
                identity.id, identity.current_version_id, 1, context
            )
        )
    elif aggregate == "claim":
        identity = application.create_claim(
            CreateClaimCommand(project, "Claim to abandon", None, None, context)
        )
        abandoned = application.abandon_claim_version(
            AbandonClaimVersionCommand(identity.id, identity.current_version_id, 1, context)
        )
    elif aggregate == "artifact":
        identity = application.create_artifact(
            CreateArtifactCommand(project, "text/plain", "Artifact to abandon", None, context)
        )
        draft = application.create_artifact_version(
            CreateArtifactVersionCommand(
                identity.id,
                b"abandon lookup proof",
                None,
                None,
                "text/plain",
                None,
                None,
                context,
            )
        )
        identity = application.get_artifact(identity.id)
        abandoned = application.abandon_artifact_version(
            AbandonArtifactVersionCommand(identity.id, draft.id, 1, context)
        )
    else:
        identity = application.create_metric_definition(
            CreateMetricDefinitionCommand(
                project,
                "Metric to abandon",
                {"kind": "count"},
                "items",
                "count",
                context,
            )
        )
        abandoned = application.abandon_metric_definition_version(
            AbandonMetricDefinitionVersionCommand(
                identity.id, identity.current_version_id, 1, context
            )
        )
    assert identity.id != identity.current_version_id
    assert abandoned.id == identity.current_version_id
    assert abandoned.status == "ABANDONED"
    assert abandoned.row_version == 2
    with engine.connect() as connection:
        durable = (
            connection.execute(
                text(
                    f"SELECT {parent_column} AS parent_id,status,row_version FROM {table} WHERE id=:id"  # noqa: E501
                ),
                {"id": abandoned.id},
            )
            .mappings()
            .one()
        )
    assert durable == {
        "parent_id": identity.id,
        "status": "ABANDONED",
        "row_version": 2,
    }
    record_property(
        "abandon_version_lookup",
        f"aggregate={aggregate};identity={identity.id};version={abandoned.id};"
        f"status={durable['status']};row_version={durable['row_version']}",
    )
    engine.dispose()


@pytest.mark.parametrize(
    "violation",
    ["initial_frozen", "current_superseded", "null_language", "frozen_edit", "frozen_input_delete"],
)
def test_direct_invalid_frozen_current_writes_rejected(
    phase2_database_url, violation, record_property
):
    engine, service, principal, project, plan, version = _setup(phase2_database_url)
    if violation != "initial_frozen":
        _freeze(engine, service, principal, project, plan, version)
    sql = {
        "initial_frozen": "INSERT INTO literature_search_plan_versions SELECT :new,id_plan,2,'FROZEN',objective,source_scope,inclusion_criteria,exclusion_criteria,time_range,language_scope,search_strategy,planned_providers,stopping_rule,:hash,hash_scheme,clock_timestamp(),created_by,created_at,row_version FROM (SELECT v.*,v.plan_id AS id_plan FROM literature_search_plan_versions v WHERE id=:id) v",  # noqa: E501
        "current_superseded": "UPDATE literature_search_plan_versions SET status='SUPERSEDED' WHERE id=:id",  # noqa: E501
        "null_language": "UPDATE literature_search_plan_versions SET language_scope=NULL WHERE id=:id",  # noqa: E501
        "frozen_edit": "UPDATE literature_search_plan_versions SET objective='changed' WHERE id=:id",  # noqa: E501
        "frozen_input_delete": "DELETE FROM search_plan_question_inputs WHERE plan_version_id=:id",
    }[violation]
    with pytest.raises(DBAPIError) as rejected:
        with engine.begin() as c:
            c.execute(text(sql), {"id": version, "new": uuid4(), "hash": "a" * 64})
    expected_code = "23514" if violation in {"initial_frozen", "current_superseded"} else "P17D1"
    assert getattr(rejected.value.orig, "sqlstate", None) == expected_code
    expected_code = "23514" if violation in {"initial_frozen", "current_superseded"} else "P17D1"
    assert getattr(rejected.value.orig, "sqlstate", None) == expected_code
    with engine.connect() as c:
        state = (
            c.execute(
                text(
                    "SELECT status,language_scope FROM literature_search_plan_versions WHERE id=:id"
                ),
                {"id": version},
            )
            .mappings()
            .one()
        )
        assert state["status"] == ("DRAFT" if violation == "initial_frozen" else "FROZEN")
        assert state["language_scope"] == []
        record_property("durable_guard_state", str(dict(state)))
    engine.dispose()


@pytest.mark.parametrize("blank", ["", " ", "\t\n", "\u2003\u0085"])
def test_objective_nonblank_database_check(phase2_database_url, blank):
    engine, _, _, _, _, version = _setup(phase2_database_url)
    with pytest.raises(DBAPIError) as rejected:
        with engine.begin() as c:
            c.execute(
                text("UPDATE literature_search_plan_versions SET objective=:blank WHERE id=:id"),
                {"blank": blank, "id": version},
            )
    assert getattr(rejected.value.orig, "sqlstate", None) == "23514"
    assert (
        getattr(getattr(rejected.value.orig, "diag", None), "constraint_name", None)
        == "ck_lspv_objective_nonblank"
    )
    engine.dispose()


def test_required_fk_leading_indexes(phase2_database_url, record_property):
    engine, *_ = _setup(phase2_database_url)
    required = {
        ("literature_search_plans", "created_by"),
        ("literature_search_plans", "current_version_id"),
        ("literature_search_plan_versions", "created_by"),
        ("literature_search_plan_command_receipts", "actor_id"),
        ("literature_search_plan_command_receipts", "project_id"),
        ("literature_search_plan_command_receipts", "result_plan_id"),
    }
    with engine.connect() as c:
        coverage = set(
            c.execute(
                text(
                    "SELECT t.relname,a.attname FROM pg_index i JOIN pg_class t ON t.oid=i.indrelid JOIN pg_class x ON x.oid=i.indexrelid JOIN pg_am am ON am.oid=x.relam JOIN pg_attribute a ON a.attrelid=t.oid AND a.attnum=i.indkey[0] WHERE i.indisvalid AND am.amname='btree'"  # noqa: E501
                )
            )
        )
        assert required <= coverage
        record_property("fk_index_coverage", str(sorted(required)))
    engine.dispose()


@pytest.mark.parametrize("first", [0, 1], ids=["A-first", "B-first"])
def test_direct_question_identity_uniqueness_race(phase2_database_url, first, record_property):
    engine, _, principal, project, _, version = _setup(phase2_database_url)
    q, qv, other = _legitimate_question_history(engine, project, principal.actor_id)
    refs = [qv, other]
    insert = text("INSERT INTO search_plan_question_inputs VALUES (:plan,:qv,:ordinal)")
    pids = Queue()
    outcomes = {}
    attempted = {"A": False, "B": False}
    first_label = "A" if first == 0 else "B"
    second_label = "B" if first == 0 else "A"

    def loser():
        try:
            with engine.begin() as c:
                pids.put(c.execute(text("SELECT pg_backend_pid()")).scalar_one())
                attempted[second_label] = True
                c.execute(insert, {"plan": version, "qv": refs[1 - first], "ordinal": 1})
            outcomes[second_label] = "COMMITTED"
            return "COMMITTED"
        except DBAPIError as exc:
            outcomes[second_label] = getattr(exc.orig, "sqlstate", None)
            return outcomes[second_label]

    with ThreadPoolExecutor(max_workers=1) as pool:
        with engine.connect() as winner:
            tx = winner.begin()
            attempted[first_label] = True
            winner.execute(insert, {"plan": version, "qv": refs[first], "ordinal": 0})
            future = pool.submit(loser)
            try:
                pid = pids.get(timeout=10)
                deadline = monotonic() + 10
                observed = False
                while monotonic() < deadline:
                    with engine.connect() as observer:
                        observed = observer.execute(
                            text(
                                "SELECT wait_event_type='Lock' FROM pg_stat_activity WHERE pid=:pid"
                            ),
                            {"pid": pid},
                        ).scalar_one()
                    if observed:
                        break
                    Event().wait(0.01)
                assert observed, "loser must be observed waiting on a PostgreSQL lock"
            finally:
                tx.commit()
                outcomes[first_label] = "COMMITTED"
            assert future.result(timeout=10) == "23505"
    with engine.connect() as c:
        rows = c.execute(
            text(
                "SELECT i.research_question_version_id,q.research_question_id "
                "FROM search_plan_question_inputs i JOIN research_question_versions q "
                "ON q.id=i.research_question_version_id WHERE i.plan_version_id=:id"
            ),
            {"id": version},
        ).all()
        assert len(rows) == 1
        assert {row.research_question_id for row in rows} == {q}
        parent_row_version = c.execute(
            text("SELECT row_version FROM literature_search_plan_versions WHERE id=:id"),
            {"id": version},
        ).scalar_one()
        history = (
            c.execute(
                text(
                    "SELECT id,status FROM research_question_versions WHERE research_question_id=:id ORDER BY version_number"  # noqa: E501
                ),
                {"id": q},
            )
            .tuples()
            .all()
        )
        assert attempted == {"A": True, "B": True}
        record_property(
            "identity_race",
            str(
                {
                    "first": first_label,
                    "attempted": attempted,
                    "outcomes": outcomes,
                    "postgres_lock_wait": observed,
                    "durable_rows": [tuple(row) for row in rows],
                    "durable_identities": [q],
                    "parent_row_version": parent_row_version,
                    "question_history": history,
                }
            ),
        )
    engine.dispose()


def test_ordinal_determinism_revision_supersession_and_hash(phase2_database_url, record_property):
    from researchbase.application.literature_search_plan import (
        RemoveLiteratureSearchPlanQuestion,
        ReviseLiteratureSearchPlan,
    )

    engine, service, principal, project, plan, version = _setup(phase2_database_url)
    refs = [_question(engine, project, principal.actor_id) for _ in range(3)]
    for index in [0, 1, 2]:
        service.add_question(
            EditLiteratureSearchPlanQuestions(
                principal, project, plan, version, refs[index][1], uuid4()
            )
        )
    first = service.freeze(
        TransitionLiteratureSearchPlanVersion(principal, project, plan, version, uuid4())
    )
    revised = service.revise(ReviseLiteratureSearchPlan(principal, project, plan, version, uuid4()))
    second = UUID(str(revised["version_id"]))
    for q, _, _ in refs:
        service.remove_question(
            RemoveLiteratureSearchPlanQuestion(principal, project, plan, second, q, uuid4())
        )
    for index in [2, 0, 1]:
        service.add_question(
            EditLiteratureSearchPlanQuestions(
                principal, project, plan, second, refs[index][1], uuid4()
            )
        )
    frozen = service.freeze(
        TransitionLiteratureSearchPlanVersion(principal, project, plan, second, uuid4())
    )
    assert version != second
    assert first["content_hash"] == frozen["content_hash"]
    with engine.connect() as c:
        layouts = [
            list(
                c.execute(
                    text(
                        "SELECT research_question_version_id,ordinal FROM search_plan_question_inputs WHERE plan_version_id=:id ORDER BY ordinal"  # noqa: E501
                    ),
                    {"id": target},
                )
            )
            for target in [version, second]
        ]
        assert layouts[0] == layouts[1]
        assert [row[0] for row in layouts[0]] == sorted([ref[1] for ref in refs], key=str)
        assert (
            c.execute(
                text("SELECT current_version_id FROM literature_search_plans WHERE id=:id"),
                {"id": plan},
            ).scalar_one()
            == second
        )
        assert (
            c.execute(
                text("SELECT status FROM literature_search_plan_versions WHERE id=:id"),
                {"id": version},
            ).scalar_one()
            == "SUPERSEDED"
        )
        record_property(
            "ordinal_hash_evidence",
            f"layouts={layouts};old_hash={first['content_hash']};new_hash={frozen['content_hash']}",
        )
    engine.dispose()


def test_remediation_child_upgrade_empty_downgrade_and_unique_head(phase2_database_url):
    from alembic import command
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from sqlalchemy import create_engine

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0023_literature_search_plan")
    command.upgrade(config, "0023a_search_plan_review_guards")
    assert ScriptDirectory.from_config(config).get_heads() == ["0071_b23_novelty_review"]
    engine = create_engine(phase2_database_url)
    with engine.connect() as c:
        assert (
            c.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0023a_search_plan_review_guards"
        )
    command.downgrade(config, "0023_literature_search_plan")
    command.upgrade(config, "0023a_search_plan_review_guards")
    engine.dispose()


def test_populated_child_downgrade_refuses(phase2_database_url):
    from alembic import command
    from alembic.config import Config

    engine, *_ = _setup(phase2_database_url)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    with pytest.raises(DBAPIError, match="downgrade refused"):
        command.downgrade(config, "0023_literature_search_plan")
    engine.dispose()


@pytest.mark.parametrize(
    "invalid",
    ["missing", "draft", "abandoned", "corrupt_hash", "cross_project", "duplicate_identity"],
)
def test_question_reference_validation_matrix(phase2_database_url, invalid, record_property):
    from researchbase.foundation.errors import ErrorCode, ResearchBaseError
    from tests.integration.phase2.test_pr2_00_challenges import _service as identity_service

    engine, service, principal, project, plan, version = _setup(phase2_database_url)
    foreign = project
    if invalid == "cross_project":
        identity, _, _ = identity_service(phase2_database_url)
        foreign = identity.create_project_with_owner(
            principal, name="foreign review project", request_id=uuid4()
        )
    q, qv, _ = _question(engine, foreign, principal.actor_id)
    candidate = qv
    if invalid == "missing":
        candidate = uuid4()
    elif invalid == "abandoned":
        q, candidate = _legitimate_abandoned_question(engine, project, principal.actor_id)
    elif invalid in {"draft", "corrupt_hash", "duplicate_identity"}:
        candidate = uuid4()
        state = "FROZEN" if invalid in {"corrupt_hash", "duplicate_identity"} else "DRAFT"
        with engine.begin() as c:
            c.execute(
                text(
                    "INSERT INTO research_question_versions(id,research_question_id,version_number,status,question_text,scope,rationale,content_hash,created_by,created_at,frozen_at) SELECT :new,research_question_id,2,CAST(:state AS varchar),question_text,scope,rationale,CASE WHEN CAST(:state AS varchar)='FROZEN' THEN :hash ELSE NULL END,created_by,created_at,CASE WHEN CAST(:state AS varchar)='FROZEN' THEN frozen_at ELSE NULL END FROM research_question_versions WHERE id=:old"  # noqa: E501
                ),
                {
                    "new": candidate,
                    "old": qv,
                    "state": state,
                    "hash": "b" * 64 if invalid == "corrupt_hash" else _question_hash(engine, qv),
                },
            )
        if invalid == "duplicate_identity":
            service.add_question(
                EditLiteratureSearchPlanQuestions(principal, project, plan, version, qv, uuid4())
            )
    request = uuid4()
    with pytest.raises(ResearchBaseError) as error:
        service.add_question(
            EditLiteratureSearchPlanQuestions(principal, project, plan, version, candidate, request)
        )
    expected = (
        ErrorCode.SEARCH_PLAN_QUESTION_SCOPE_MISMATCH
        if invalid == "cross_project"
        else ErrorCode.VALIDATION_ERROR
        if invalid == "duplicate_identity"
        else ErrorCode.SEARCH_PLAN_QUESTION_INVALID
    )
    assert error.value.code is expected
    with engine.connect() as c:
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM literature_search_plan_command_receipts WHERE request_id=:id"  # noqa: E501
                ),
                {"id": request},
            ).scalar_one()
            == 0
        )
        state = (
            c.execute(
                text("SELECT status,content_hash FROM research_question_versions WHERE id=:id"),
                {"id": candidate},
            )
            .mappings()
            .one_or_none()
        )
        reference_count = c.execute(
            text(
                "SELECT count(*) FROM search_plan_question_inputs "
                "WHERE plan_version_id=:plan AND research_question_version_id=:candidate"
            ),
            {"plan": version, "candidate": candidate},
        ).scalar_one()
        assert reference_count == 0
        record_property(
            "invalid_reference",
            f"case={invalid};question_identity={q};question_version={candidate};"
            f"state={dict(state) if state else None};code={error.value.code};"
            f"receipt_count=0;reference_count={reference_count}",
        )
    engine.dispose()


def _question_hash(engine, version):
    with engine.connect() as c:
        return c.execute(
            text("SELECT content_hash FROM research_question_versions WHERE id=:id"),
            {"id": version},
        ).scalar_one()


@pytest.mark.parametrize("violation", ["initial_frozen", "current_superseded", "blank_objective"])
def test_original_0023_counterexample_and_fail_closed_upgrade(
    phase2_database_url, violation, record_property
):
    from alembic import command
    from alembic.config import Config

    engine, _, _, principal, project = _authorized_service(
        phase2_database_url, migration_revision="0023_literature_search_plan"
    )
    service = LiteratureSearchPlanService(
        lambda: SqlAlchemyUnitOfWork(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        ),
        _AlwaysValidCredential(),
    )
    draft = service.create(
        CreateLiteratureSearchPlan(
            principal, project, _material(uuid4(), language_scope=()), uuid4()
        )
    )
    plan, version = UUID(str(draft["plan_id"])), UUID(str(draft["version_id"]))
    if violation == "current_superseded":
        _freeze(engine, service, principal, project, plan, version)
    with engine.begin() as c:
        if violation == "initial_frozen":
            c.execute(
                text(
                    "INSERT INTO literature_search_plan_versions SELECT :new,plan_id,2,'FROZEN',objective,source_scope,inclusion_criteria,exclusion_criteria,time_range,language_scope,search_strategy,planned_providers,stopping_rule,:hash,hash_scheme,clock_timestamp(),created_by,created_at,row_version FROM literature_search_plan_versions WHERE id=:id"  # noqa: E501
                ),
                {"new": uuid4(), "hash": "a" * 64, "id": version},
            )
        elif violation == "current_superseded":
            c.execute(
                text("UPDATE literature_search_plan_versions SET status='SUPERSEDED' WHERE id=:id"),
                {"id": version},
            )
        else:
            c.execute(
                text("UPDATE literature_search_plan_versions SET objective=' ' WHERE id=:id"),
                {"id": version},
            )
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    with pytest.raises(DBAPIError, match="upgrade refused"):
        command.upgrade(config, "0023a_search_plan_review_guards")
    with engine.connect() as c:
        assert (
            c.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == "0023_literature_search_plan"
        )
        assert (
            c.execute(
                text(
                    "SELECT count(*) FROM pg_constraint WHERE conname='ck_lspv_objective_nonblank'"
                )
            ).scalar_one()
            == 0
        )
    record_property(
        "pre_remediation_counterexample",
        f"case={violation};original_0023_committed=True;child_upgrade=FAIL_CLOSED",
    )
    engine.dispose()


def test_populated_valid_0023_upgrade_preserves_rows(phase2_database_url):
    from alembic import command
    from alembic.config import Config

    engine, _, _, principal, project = _authorized_service(
        phase2_database_url, migration_revision="0023_literature_search_plan"
    )
    service = LiteratureSearchPlanService(
        lambda: SqlAlchemyUnitOfWork(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        ),
        _AlwaysValidCredential(),
    )
    result = service.create(
        CreateLiteratureSearchPlan(
            principal, project, _material(uuid4(), language_scope=()), uuid4()
        )
    )
    plan, version = UUID(str(result["plan_id"])), UUID(str(result["version_id"]))
    _freeze(engine, service, principal, project, plan, version)
    from tests.integration.phase2.test_pr2_03_command_matrix import _snapshot

    before = _snapshot(engine)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", phase2_database_url)
    command.upgrade(config, "0023a_search_plan_review_guards")
    assert _snapshot(engine) == before
    engine.dispose()


def test_live_schema_guard_contract(phase2_database_url, record_property):
    from sqlalchemy import inspect

    engine, *_ = _setup(phase2_database_url)
    inspector = inspect(engine)
    checks = {
        str(row["name"])
        for row in inspector.get_check_constraints("literature_search_plan_versions")
    }
    assert checks == {
        "ck_lspv_version_number",
        "ck_lspv_status",
        "ck_lspv_source_scope",
        "ck_lspv_search_strategy",
        "ck_lspv_hash_scheme",
        "ck_lspv_hash",
        "ck_lspv_freeze_fields",
        "ck_lspv_objective_nonblank",
    }
    expected_fks = {
        "literature_search_plans": {
            (("project_id",), "projects", ("id",)),
            (("created_by",), "actors", ("id",)),
            (("id", "current_version_id"), "literature_search_plan_versions", ("plan_id", "id")),
        },
        "literature_search_plan_versions": {
            (("plan_id",), "literature_search_plans", ("id",)),
            (("created_by",), "actors", ("id",)),
        },
        "search_plan_question_inputs": {
            (("plan_version_id",), "literature_search_plan_versions", ("id",)),
            (("research_question_version_id",), "research_question_versions", ("id",)),
        },
        "literature_search_plan_command_receipts": {
            (("actor_id",), "actors", ("id",)),
            (("project_id", "result_plan_id"), "literature_search_plans", ("project_id", "id")),
            (
                ("result_plan_id", "result_plan_version_id"),
                "literature_search_plan_versions",
                ("plan_id", "id"),
            ),
        },
    }
    for table, expected in expected_fks.items():
        fks = inspector.get_foreign_keys(table)
        assert {
            (tuple(fk["constrained_columns"]), fk["referred_table"], tuple(fk["referred_columns"]))
            for fk in fks
        } == expected
        assert all(fk.get("options", {}).get("ondelete") == "RESTRICT" for fk in fks)
    with engine.connect() as c:
        triggers = c.execute(
            text(
                "SELECT tgname,tgdeferrable,tginitdeferred FROM pg_trigger WHERE tgname IN ('trg_lsp_final_state','trg_lspv_final_state','trg_spqi_identity_unique') ORDER BY tgname"  # noqa: E501
            )
        ).all()
        assert [tuple(row) for row in triggers] == [
            ("trg_lsp_final_state", True, True),
            ("trg_lspv_final_state", True, True),
            ("trg_spqi_identity_unique", True, False),
        ]
    record_property(
        "schema_guard_catalog", str({"checks": sorted(checks), "constraint_triggers": triggers})
    )
    engine.dispose()


def test_valid_superseded_question_reference_freezes(phase2_database_url):
    engine, service, principal, project, plan, version = _setup(phase2_database_url)
    _, qv, _ = _legitimate_question_history(engine, project, principal.actor_id)
    service.add_question(
        EditLiteratureSearchPlanQuestions(principal, project, plan, version, qv, uuid4())
    )
    assert (
        service.freeze(
            TransitionLiteratureSearchPlanVersion(principal, project, plan, version, uuid4())
        )["status"]
        == "FROZEN"
    )
    engine.dispose()
