from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event, local
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from researchbase.application.literature_search_plan import (
    CreateLiteratureSearchPlan,
    EditLiteratureSearchPlanQuestions,
    LiteratureSearchPlanService,
    RemoveLiteratureSearchPlanQuestion,
    TransitionLiteratureSearchPlanVersion,
    UpdateLiteratureSearchPlanDraft,
)
from researchbase.domain.literature_search_plan import FrozenResearchQuestionReference
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.persistence.literature_search_plan_repository import (
    SqlAlchemyLiteratureSearchPlanRepository,
)
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.integration.phase2.test_pr2_01_source_identity import _authorized_service
from tests.integration.phase2.test_pr2_03_literature_search_plan_application import (
    _AlwaysValidCredential,
    _material,
    _question,
)


def _setup(database_url: str):
    engine, _, _, principal, project_id = _authorized_service(database_url)
    question_id, question_version_id, question_hash = _question(
        engine, project_id, principal.actor_id
    )

    def factory():
        return SqlAlchemyUnitOfWork(
            sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        )

    service = LiteratureSearchPlanService(factory, _AlwaysValidCredential())
    created = service.create(
        CreateLiteratureSearchPlan(
            principal,
            project_id,
            _material(UUID(int=0), language_scope=("en",)),
            uuid4(),
        )
    )
    plan_id, version_id = UUID(str(created["plan_id"])), UUID(str(created["version_id"]))
    service.add_question(
        EditLiteratureSearchPlanQuestions(
            principal, project_id, plan_id, version_id, question_version_id, uuid4()
        )
    )
    reference = FrozenResearchQuestionReference(question_id, question_version_id, question_hash)
    return engine, service, principal, project_id, plan_id, version_id, question_id, reference


def _race(database_url: str, winner: str, loser: str, record_property):
    engine, service, principal, project_id, plan_id, version_id, question_id, reference = _setup(
        database_url
    )
    addition = (
        _question(engine, project_id, principal.actor_id) if "add" in {winner, loser} else None
    )
    winner_locked = Event()
    release_winner = Event()
    loser_started = Event()
    role = local()
    original_lock_project = SqlAlchemyLiteratureSearchPlanRepository.lock_project

    def synchronized_lock(repository, locked_project_id):
        current_role = getattr(role, "name", "")
        if current_role:
            repository._session.execute(
                text("SELECT set_config('application_name', :name, true)"),
                {"name": f"rb_pr203_{current_role}_{plan_id.hex}"},
            )
        if current_role == "loser":
            loser_started.set()
        original_lock_project(repository, locked_project_id)
        if current_role == "winner" and not getattr(role, "winner_waited", False):
            role.winner_waited = True
            winner_locked.set()
            if not release_winner.wait(20):
                raise TimeoutError("winner was not released")

    def invoke(worker_role: str, operation: str):
        role.name = worker_role
        try:
            if operation == "freeze":
                return service.freeze(
                    TransitionLiteratureSearchPlanVersion(
                        principal, project_id, plan_id, version_id, uuid4()
                    )
                ), None
            if operation == "add":
                assert addition is not None
                return service.add_question(
                    EditLiteratureSearchPlanQuestions(
                        principal, project_id, plan_id, version_id, addition[1], uuid4()
                    )
                ), None
            if operation == "remove":
                return service.remove_question(
                    RemoveLiteratureSearchPlanQuestion(
                        principal, project_id, plan_id, version_id, question_id, uuid4()
                    )
                ), None
            language = None if operation == "null" else ("fr",)
            return service.update(
                UpdateLiteratureSearchPlanDraft(
                    principal,
                    project_id,
                    plan_id,
                    version_id,
                    _material(plan_id, language_scope=language),
                    uuid4(),
                )
            ), None
        except BaseException as error:  # capture both transaction outcomes for assertions
            return None, error

    try:
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(
                SqlAlchemyLiteratureSearchPlanRepository, "lock_project", synchronized_lock
            )
            with ThreadPoolExecutor(max_workers=2) as pool:
                try:
                    first = pool.submit(invoke, "winner", winner)
                    assert winner_locked.wait(10), "winner did not acquire the project lock"
                    second = pool.submit(invoke, "loser", loser)
                    assert loser_started.wait(10), "loser did not reach project lock"
                    deadline = time.monotonic() + 10
                    lock_wait_seen = False
                    while time.monotonic() < deadline:
                        with engine.connect() as connection:
                            lock_wait_seen = connection.execute(
                                text(
                                    "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                                    "WHERE application_name=:name AND wait_event_type='Lock')"
                                ),
                                {"name": f"rb_pr203_loser_{plan_id.hex}"},
                            ).scalar_one()
                        if lock_wait_seen:
                            break
                        time.sleep(0.01)
                    assert lock_wait_seen, "PostgreSQL did not report the loser waiting on a lock"
                    release_winner.set()
                    winner_result = first.result(timeout=30)
                    loser_result = second.result(timeout=30)
                finally:
                    release_winner.set()
    finally:
        release_winner.set()

    outcomes = {winner: winner_result, loser: loser_result}
    with engine.connect() as connection:
        state = (
            connection.execute(
                text(
                    "SELECT v.status,v.language_scope,v.content_hash,v.frozen_at, "
                    "p.current_version_id, "
                    "(SELECT count(*) FROM search_plan_question_inputs i "
                    "WHERE i.plan_version_id=v.id) AS ref_count "
                    "FROM literature_search_plan_versions v "
                    "JOIN literature_search_plans p ON p.id=v.plan_id WHERE v.id=:id"
                ),
                {"id": version_id},
            )
            .mappings()
            .one()
        )
        receipts = [
            dict(row)
            for row in connection.execute(
                text(
                    "SELECT command_name,request_id,request_hash,result_dto "
                    "FROM literature_search_plan_command_receipts "
                    "WHERE result_plan_version_id=:id ORDER BY completed_at"
                ),
                {"id": version_id},
            ).mappings()
        ]
    record_property(
        "race_evidence",
        json.dumps(
            {
                "winner_operation": winner,
                "loser_operation": loser,
                "postgres_lock_wait_observed": lock_wait_seen,
                "outcomes": {
                    operation: {"result": result, "error": str(error) if error else None}
                    for operation, (result, error) in outcomes.items()
                },
                "plan_id": plan_id,
                "version_id": version_id,
                "durable_state": dict(state),
                "receipts": receipts,
            },
            default=str,
            sort_keys=True,
        ),
    )
    assert not (state["status"] == "FROZEN" and state["ref_count"] == 0)
    assert not (state["status"] == "FROZEN" and state["language_scope"] is None)
    return engine, outcomes, state, plan_id, version_id, reference


@pytest.mark.parametrize("winner", ["remove", "freeze"])
def test_remove_last_question_races_freeze(
    phase2_database_url: str, winner: str, record_property
) -> None:
    loser = "freeze" if winner == "remove" else "remove"
    engine, outcomes, state, _, version_id, _ = _race(
        phase2_database_url, winner, loser, record_property
    )
    winning_value, winning_error = outcomes[winner]
    losing_value, losing_error = outcomes[loser]
    assert winning_error is None and winning_value is not None
    assert losing_value is None and isinstance(losing_error, ResearchBaseError)
    if winner == "remove":
        assert losing_error.code is ErrorCode.SEARCH_PLAN_QUESTION_REQUIRED
        assert state["status"] == "DRAFT" and state["content_hash"] is None
        assert state["current_version_id"] is None and state["ref_count"] == 0
    else:
        assert losing_error.code is ErrorCode.SEARCH_PLAN_VERSION_IMMUTABLE
        assert (
            state["status"] == "FROZEN" and state["content_hash"] == winning_value["content_hash"]
        )
        assert state["current_version_id"] == version_id and state["ref_count"] == 1
    engine.dispose()


@pytest.mark.parametrize("winner", ["null", "freeze"])
def test_language_null_mutation_races_freeze(
    phase2_database_url: str, winner: str, record_property
) -> None:
    loser = "freeze" if winner == "null" else "null"
    engine, outcomes, state, plan_id, version_id, reference = _race(
        phase2_database_url, winner, loser, record_property
    )
    winning_value, winning_error = outcomes[winner]
    losing_value, losing_error = outcomes[loser]
    assert winning_error is None and winning_value is not None
    assert losing_value is None and isinstance(losing_error, ResearchBaseError)
    if winner == "null":
        assert losing_error.code is ErrorCode.SEARCH_PLAN_LANGUAGE_SCOPE_REQUIRED
        assert state["status"] == "DRAFT" and state["language_scope"] is None
        assert state["content_hash"] is None and state["current_version_id"] is None
    else:
        assert losing_error.code is ErrorCode.SEARCH_PLAN_VERSION_IMMUTABLE
        assert state["status"] == "FROZEN" and state["language_scope"] == ["en"]
        assert state["current_version_id"] == version_id
        assert (
            state["content_hash"]
            == _material(plan_id, (reference,), language_scope=("en",)).digest()
        )
        assert (
            state["content_hash"]
            != _material(version_id, (reference,), language_scope=("en",)).digest()
        )
    engine.dispose()


@pytest.mark.parametrize("winner", ["edit", "freeze"])
def test_language_edit_races_freeze_hashes_locked_durable_state(
    phase2_database_url: str, winner: str, record_property
) -> None:
    loser = "freeze" if winner == "edit" else "edit"
    engine, outcomes, state, plan_id, version_id, reference = _race(
        phase2_database_url, winner, loser, record_property
    )
    winning_value, winning_error = outcomes[winner]
    losing_value, losing_error = outcomes[loser]
    assert winning_error is None and winning_value is not None
    if winner == "edit":
        assert losing_error is None and losing_value is not None
        expected_language = ["fr"]
    else:
        assert losing_value is None and isinstance(losing_error, ResearchBaseError)
        assert losing_error.code is ErrorCode.SEARCH_PLAN_VERSION_IMMUTABLE
        expected_language = ["en"]
    assert state["status"] == "FROZEN"
    assert state["language_scope"] == expected_language
    assert state["current_version_id"] == version_id
    assert (
        state["content_hash"]
        == _material(plan_id, (reference,), language_scope=tuple(expected_language)).digest()
    )
    assert (
        state["content_hash"]
        != _material(version_id, (reference,), language_scope=tuple(expected_language)).digest()
    )
    engine.dispose()


@pytest.mark.parametrize("winner", ["add", "freeze"])
def test_addition_races_freeze_rereads_durable_refs(phase2_database_url, winner, record_property):
    loser = "freeze" if winner == "add" else "add"
    engine, outcomes, state, plan, version, _ = _race(
        phase2_database_url, winner, loser, record_property
    )
    assert outcomes[winner][1] is None
    if winner == "add":
        assert outcomes["freeze"][1] is None
        assert state["ref_count"] == 2
    else:
        assert isinstance(outcomes["add"][1], ResearchBaseError)
        assert outcomes["add"][1].code is ErrorCode.SEARCH_PLAN_VERSION_IMMUTABLE
        assert state["ref_count"] == 1
    assert state["status"] == "FROZEN"
    assert state["current_version_id"] == version
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT qv.research_question_id,qv.id,qv.content_hash "
                "FROM search_plan_question_inputs i JOIN research_question_versions qv "
                "ON qv.id=i.research_question_version_id WHERE i.plan_version_id=:id"
            ),
            {"id": version},
        ).all()
    refs = tuple(FrozenResearchQuestionReference(*row) for row in rows)
    expected = _material(plan, refs, language_scope=("en",)).digest()
    assert state["content_hash"] == expected
    record_property(
        "addition_hash",
        json.dumps(
            {
                "expected_hash": expected,
                "durable_hash": state["content_hash"],
                "durable_ref_count": len(refs),
            }
        ),
    )
    engine.dispose()
