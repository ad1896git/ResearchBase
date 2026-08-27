from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier, Lock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

import researchbase.application.commands as commands_module
from researchbase.application.commands import (
    ApplicationService,
    CreateActorCommand,
    CreateHypothesisCommand,
    CreateProjectCommand,
    CreateResearchQuestionCommand,
    FreezeHypothesisCommand,
    FreezeResearchQuestionCommand,
    ReviseHypothesisCommand,
    ReviseResearchQuestionCommand,
    UpdateResearchQuestionDraftCommand,
)
from researchbase.domain.identity import ActorType
from researchbase.domain.organization import ProjectId
from researchbase.domain.research import (
    Hypothesis,
    HypothesisId,
    HypothesisVersionId,
    ResearchQuestion,
    ResearchQuestionId,
    ResearchQuestionVersionId,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.time import FixedClock
from researchbase.foundation.versioning import VersionStatus
from researchbase.persistence.database import create_database_engine, create_session_factory
from researchbase.persistence.repositories import (
    SqlAlchemyHypothesisRepository,
    SqlAlchemyResearchQuestionRepository,
)
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def service_factory() -> Iterator[Callable[[], ApplicationService]]:
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set; run against the real PostgreSQL service")
    engine = create_database_engine()
    sessions = create_session_factory(engine)
    clock = FixedClock(datetime(2026, 8, 27, 0, 0, tzinfo=UTC))
    try:
        yield lambda: ApplicationService(lambda: SqlAlchemyUnitOfWork(sessions), clock)
    finally:
        engine.dispose()


def context(actor_id: UUID) -> ExecutionContext:
    return ExecutionContext(actor_id=actor_id, request_id=uuid4(), client_type="test")


def seed(service: ApplicationService) -> tuple[UUID, ProjectId, ExecutionContext]:
    actor = service.create_actor(
        CreateActorCommand(ActorType.HUMAN, f"Owner-{uuid4()}", None, context(uuid4()))
    )
    actor_context = context(actor.id)
    project = service.create_project(
        CreateProjectCommand(f"Project-{uuid4()}", None, actor_context)
    )
    return actor.id, project.id, actor_context


def test_research_question_create_freeze_revise_and_history(
    service_factory: Callable[[], ApplicationService],
) -> None:
    service = service_factory()
    actor_id, project_id, actor_context = seed(service)
    created = service.create_research_question(
        CreateResearchQuestionCommand(
            project_id, "Does treatment help?", {"population": "adults"}, None, actor_context
        )
    )
    assert created.row_version == 1

    frozen = service.freeze_research_question(
        FreezeResearchQuestionCommand(created.id, created.current_version_id, actor_context, 1)
    )
    assert frozen.status is VersionStatus.FROZEN
    revised = service.revise_research_question(
        ReviseResearchQuestionCommand(
            created.id,
            "Does treatment improve outcome?",
            {"population": "adults"},
            "New evidence",
            2,
            actor_context,
        )
    )
    history = service.get_research_question_history(ResearchQuestionId(revised.id))
    assert [version.version_number for version in history] == [1, 2]
    assert [version.status for version in history] == [
        VersionStatus.SUPERSEDED,
        VersionStatus.DRAFT,
    ]
    assert history[0].question_text == "Does treatment help?"
    assert history[0].content_hash is not None
    assert revised.created_by == actor_id


def test_hypothesis_project_link_and_version_flow(
    service_factory: Callable[[], ApplicationService],
) -> None:
    service = service_factory()
    actor_id, project_id, actor_context = seed(service)
    question = service.create_research_question(
        CreateResearchQuestionCommand(project_id, "Does treatment help?", None, None, actor_context)
    )
    hypothesis = service.create_hypothesis(
        CreateHypothesisCommand(
            project_id,
            "Treatment improves outcome.",
            "increase",
            {"threshold": 0.1},
            None,
            actor_context,
            question.id,
        )
    )
    frozen = service.freeze_hypothesis(
        FreezeHypothesisCommand(hypothesis.id, hypothesis.current_version_id, actor_context, 1)
    )
    revised = service.revise_hypothesis(
        ReviseHypothesisCommand(
            hypothesis.id,
            "Treatment strongly improves outcome.",
            "increase",
            {"threshold": 0.2},
            None,
            2,
            actor_context,
        )
    )
    history = service.get_hypothesis_history(revised.id)
    assert [version.version_number for version in history] == [1, 2]
    assert history[0].status is VersionStatus.SUPERSEDED
    assert history[0].content_hash == frozen.content_hash
    assert revised.created_by == actor_id


def test_hypothesis_rejects_cross_project_research_question(
    service_factory: Callable[[], ApplicationService],
) -> None:
    service = service_factory()
    _, project_a, context_a = seed(service)
    _, project_b, context_b = seed(service)
    question = service.create_research_question(
        CreateResearchQuestionCommand(project_b, "Question", None, None, context_b)
    )
    with pytest.raises(ResearchBaseError) as raised:
        service.create_hypothesis(
            CreateHypothesisCommand(project_a, "bad", None, None, None, context_a, question.id)
        )
    assert raised.value.code is ErrorCode.REFERENTIAL_INTEGRITY_ERROR
    assert project_a != project_b


def test_stale_draft_update_is_concurrent_modification(
    service_factory: Callable[[], ApplicationService],
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    created = service.create_research_question(
        CreateResearchQuestionCommand(project_id, "Initial", None, None, actor_context)
    )
    version_id = created.current_version_id
    service.update_research_question_draft(
        UpdateResearchQuestionDraftCommand(
            created.id, version_id, "First edit", None, None, 1, actor_context
        )
    )
    with pytest.raises(ResearchBaseError) as raised:
        service.update_research_question_draft(
            UpdateResearchQuestionDraftCommand(
                created.id, version_id, "Stale edit", None, None, 1, actor_context
            )
        )
    assert raised.value.code is ErrorCode.CONCURRENT_MODIFICATION


def test_independent_uows_reject_stale_identity_pointer_updates(
    service_factory: Callable[[], ApplicationService],
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    question = service.create_research_question(
        CreateResearchQuestionCommand(project_id, "Question", None, None, actor_context)
    )
    hypothesis = service.create_hypothesis(
        CreateHypothesisCommand(project_id, "Treatment helps", None, None, None, actor_context)
    )
    engine = create_database_engine()
    sessions = create_session_factory(engine)
    try:
        with SqlAlchemyUnitOfWork(sessions) as first, SqlAlchemyUnitOfWork(sessions) as second:
            first_loaded = first.research_questions.get(question.id)
            second_loaded = second.research_questions.get(question.id)
            assert first_loaded is not None and second_loaded is not None
            first.research_questions.update_current_version(
                question.id, question.current_version_id, first_loaded.row_version
            )
            first.commit()
            with pytest.raises(ResearchBaseError) as raised:
                second.research_questions.update_current_version(
                    question.id, question.current_version_id, second_loaded.row_version
                )
            assert raised.value.code is ErrorCode.CONCURRENT_MODIFICATION
        with SqlAlchemyUnitOfWork(sessions) as first, SqlAlchemyUnitOfWork(sessions) as second:
            first_loaded = first.hypotheses.get(hypothesis.id)
            second_loaded = second.hypotheses.get(hypothesis.id)
            assert first_loaded is not None and second_loaded is not None
            first.hypotheses.update_current_version(
                hypothesis.id, hypothesis.current_version_id, first_loaded.row_version
            )
            first.commit()
            with pytest.raises(ResearchBaseError) as raised:
                second.hypotheses.update_current_version(
                    hypothesis.id, hypothesis.current_version_id, second_loaded.row_version
                )
            assert raised.value.code is ErrorCode.CONCURRENT_MODIFICATION
    finally:
        engine.dispose()


def test_research_question_create_rolls_back_identity_and_version(
    service_factory: Callable[[], ApplicationService], monkeypatch: pytest.MonkeyPatch
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    engine = create_database_engine()
    generated_ids: dict[str, UUID] = {}

    original_new_typed_id = commands_module.new_typed_id

    def capture_new_typed_id(id_type: Callable[[UUID], object]) -> object:
        generated = original_new_typed_id(id_type)
        if isinstance(generated, UUID):
            if id_type is ResearchQuestionId:
                generated_ids["parent"] = generated
            elif id_type is ResearchQuestionVersionId:
                generated_ids["version"] = generated
        return generated

    monkeypatch.setattr(commands_module, "new_typed_id", capture_new_typed_id)
    flush_observed = False

    try:
        def fail_commit(uow: SqlAlchemyUnitOfWork) -> None:
            nonlocal flush_observed
            uow._require_session().flush()
            flush_observed = True
            raise RuntimeError("forced commit failure")

        monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", fail_commit)
        with pytest.raises(RuntimeError, match="forced commit failure"):
            service.create_research_question(
                CreateResearchQuestionCommand(
                    project_id, "Atomic question", None, None, actor_context
                )
            )
        assert flush_observed
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT count(*) FROM research_questions WHERE id = :parent_id"),
                    {"parent_id": generated_ids["parent"]},
                ).scalar_one()
                == 0
            )
            assert (
                connection.execute(
                    text(
                        "SELECT count(*) FROM research_question_versions "
                        "WHERE id = :version_id AND research_question_id = :parent_id"
                    ),
                    {"version_id": generated_ids["version"], "parent_id": generated_ids["parent"]},
                ).scalar_one()
                == 0
            )
    finally:
        engine.dispose()


def test_research_question_freeze_rolls_back_version_and_pointer(
    service_factory: Callable[[], ApplicationService], monkeypatch: pytest.MonkeyPatch
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    created = service.create_research_question(
        CreateResearchQuestionCommand(project_id, "Atomic freeze", None, None, actor_context)
    )
    before_question = service.get_research_question(created.id)
    before_version = service.get_research_question_history(created.id)[0]
    before_state = (
        before_version.status,
        before_version.content_hash,
        before_version.frozen_at,
        before_version.row_version,
        before_question.current_version_id,
        before_question.row_version,
    )
    flush_observed = False

    def fail_commit(uow: SqlAlchemyUnitOfWork) -> None:
        nonlocal flush_observed
        uow._require_session().flush()
        flush_observed = True
        raise RuntimeError("forced commit failure")

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="forced commit failure"):
        service.freeze_research_question(
            FreezeResearchQuestionCommand(created.id, created.current_version_id, actor_context, 1)
        )
    assert flush_observed
    after_question = service.get_research_question(created.id)
    after_version = service.get_research_question_history(created.id)[0]
    assert (
        after_version.status,
        after_version.content_hash,
        after_version.frozen_at,
        after_version.row_version,
        after_question.current_version_id,
        after_question.row_version,
    ) == before_state


def test_hypothesis_create_rolls_back_identity_and_version(
    service_factory: Callable[[], ApplicationService], monkeypatch: pytest.MonkeyPatch
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    engine = create_database_engine()
    generated_ids: dict[str, UUID] = {}

    original_new_typed_id = commands_module.new_typed_id

    def capture_new_typed_id(id_type: Callable[[UUID], object]) -> object:
        generated = original_new_typed_id(id_type)
        if isinstance(generated, UUID):
            if id_type is HypothesisId:
                generated_ids["parent"] = generated
            elif id_type is HypothesisVersionId:
                generated_ids["version"] = generated
        return generated

    monkeypatch.setattr(commands_module, "new_typed_id", capture_new_typed_id)
    flush_observed = False

    try:
        def fail_commit(uow: SqlAlchemyUnitOfWork) -> None:
            nonlocal flush_observed
            uow._require_session().flush()
            flush_observed = True
            raise RuntimeError("forced commit failure")

        monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", fail_commit)
        with pytest.raises(RuntimeError, match="forced commit failure"):
            service.create_hypothesis(
                CreateHypothesisCommand(
                    project_id, "Atomic hypothesis", None, None, None, actor_context
                )
            )
        assert flush_observed
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT count(*) FROM hypotheses WHERE id = :parent_id"),
                    {"parent_id": generated_ids["parent"]},
                ).scalar_one()
                == 0
            )
            assert (
                connection.execute(
                    text(
                        "SELECT count(*) FROM hypothesis_versions "
                        "WHERE id = :version_id AND hypothesis_id = :parent_id"
                    ),
                    {"version_id": generated_ids["version"], "parent_id": generated_ids["parent"]},
                ).scalar_one()
                == 0
            )
    finally:
        engine.dispose()


def test_hypothesis_freeze_rolls_back_version_and_pointer(
    service_factory: Callable[[], ApplicationService], monkeypatch: pytest.MonkeyPatch
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    created = service.create_hypothesis(
        CreateHypothesisCommand(
            project_id, "Atomic hypothesis freeze", None, None, None, actor_context
        )
    )
    before_hypothesis = service.get_hypothesis(created.id)
    before_version = service.get_hypothesis_history(created.id)[0]
    before_state = (
        before_version.status,
        before_version.content_hash,
        before_version.frozen_at,
        before_version.row_version,
        before_hypothesis.current_version_id,
        before_hypothesis.row_version,
    )
    flush_observed = False

    def fail_commit(uow: SqlAlchemyUnitOfWork) -> None:
        nonlocal flush_observed
        uow._require_session().flush()
        flush_observed = True
        raise RuntimeError("forced commit failure")

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="forced commit failure"):
        service.freeze_hypothesis(
            FreezeHypothesisCommand(created.id, created.current_version_id, actor_context, 1)
        )
    assert flush_observed
    after_hypothesis = service.get_hypothesis(created.id)
    after_version = service.get_hypothesis_history(created.id)[0]
    assert (
        after_version.status,
        after_version.content_hash,
        after_version.frozen_at,
        after_version.row_version,
        after_hypothesis.current_version_id,
        after_hypothesis.row_version,
    ) == before_state


def test_application_rejects_cross_parent_current_pointer_attacks(
    service_factory: Callable[[], ApplicationService],
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    question_a = service.create_research_question(
        CreateResearchQuestionCommand(project_id, "Question A", None, None, actor_context)
    )
    question_b = service.create_research_question(
        CreateResearchQuestionCommand(project_id, "Question B", None, None, actor_context)
    )
    with pytest.raises(ResearchBaseError) as question_error:
        service.freeze_research_question(
            FreezeResearchQuestionCommand(
                question_a.id, question_b.current_version_id, actor_context, 1
            )
        )
    assert question_error.value.code is ErrorCode.REFERENTIAL_INTEGRITY_ERROR
    assert (
        service.get_research_question(question_a.id).current_version_id
        == question_a.current_version_id
    )

    hypothesis_a = service.create_hypothesis(
        CreateHypothesisCommand(project_id, "Hypothesis A", None, None, None, actor_context)
    )
    hypothesis_b = service.create_hypothesis(
        CreateHypothesisCommand(project_id, "Hypothesis B", None, None, None, actor_context)
    )
    with pytest.raises(ResearchBaseError) as hypothesis_error:
        service.freeze_hypothesis(
            FreezeHypothesisCommand(
                hypothesis_a.id, hypothesis_b.current_version_id, actor_context, 1
            )
        )
    assert hypothesis_error.value.code is ErrorCode.REFERENTIAL_INTEGRITY_ERROR
    assert (
        service.get_hypothesis(hypothesis_a.id).current_version_id
        == hypothesis_a.current_version_id
    )


def test_hypothesis_draft_update_rejects_stale_independent_uow(
    service_factory: Callable[[], ApplicationService],
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    created = service.create_hypothesis(
        CreateHypothesisCommand(project_id, "Initial hypothesis", None, None, None, actor_context)
    )
    engine = create_database_engine()
    sessions = create_session_factory(engine)
    try:
        with SqlAlchemyUnitOfWork(sessions) as first, SqlAlchemyUnitOfWork(sessions) as second:
            first_loaded = first.hypotheses.get_version(created.current_version_id)
            second_loaded = second.hypotheses.get_version(created.current_version_id)
            assert first_loaded is not None and second_loaded is not None
            first.hypotheses.update_version(
                first_loaded.edit_material(
                    statement="First hypothesis edit",
                    expected_direction=None,
                    success_criteria=None,
                    rationale=None,
                ),
                first_loaded.row_version,
            )
            first.commit()
            with pytest.raises(ResearchBaseError) as raised:
                second.hypotheses.update_version(
                    second_loaded.edit_material(
                        statement="Stale hypothesis edit",
                        expected_direction=None,
                        success_criteria=None,
                        rationale=None,
                    ),
                    second_loaded.row_version,
                )
            assert raised.value.code is ErrorCode.CONCURRENT_MODIFICATION
        assert service.get_hypothesis_history(created.id)[0].statement == "First hypothesis edit"
    finally:
        engine.dispose()


def test_concurrent_research_question_revisions_serialize_safely(
    service_factory: Callable[[], ApplicationService], monkeypatch: pytest.MonkeyPatch
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    created = service.create_research_question(
        CreateResearchQuestionCommand(project_id, "Concurrent question", None, None, actor_context)
    )
    service.freeze_research_question(
        FreezeResearchQuestionCommand(created.id, created.current_version_id, actor_context, 1)
    )
    command = ReviseResearchQuestionCommand(
        created.id, "Concurrent revision", None, None, 2, actor_context
    )
    barrier = Barrier(2)
    entry_lock = Lock()
    entered = 0
    original_get_for_update = SqlAlchemyResearchQuestionRepository.get_for_update

    def synchronized_get_for_update(
        repository: SqlAlchemyResearchQuestionRepository, question_id: ResearchQuestionId
    ) -> ResearchQuestion | None:
        nonlocal entered
        with entry_lock:
            entered += 1
        barrier.wait(timeout=10)
        return original_get_for_update(repository, question_id)

    monkeypatch.setattr(
        SqlAlchemyResearchQuestionRepository, "get_for_update", synchronized_get_for_update
    )

    def revise() -> tuple[str, object]:
        try:
            return "ok", service.revise_research_question(command)
        except ResearchBaseError as error:
            return "error", error

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(revise) for _ in range(2)]
        results = [future.result() for future in futures]
    assert entered == 2
    assert sorted(result[0] for result in results) == ["error", "ok"]
    error_result = next(result for result in results if result[0] == "error")
    assert isinstance(error_result[1], ResearchBaseError)
    assert error_result[1].code is ErrorCode.CONCURRENT_MODIFICATION
    history = service.get_research_question_history(created.id)
    assert [version.version_number for version in history] == [1, 2]
    assert service.get_research_question(created.id).current_version_id == history[1].id
    engine = create_database_engine()
    try:
        with engine.connect() as connection:
            version_rows = connection.execute(
                text(
                    "SELECT version_number FROM research_question_versions "
                    "WHERE research_question_id = :question_id ORDER BY version_number"
                ),
                {"question_id": created.id},
            ).scalars().all()
            pointer_parent = connection.execute(
                text(
                    "SELECT v.research_question_id FROM research_questions q "
                    "JOIN research_question_versions v ON v.id = q.current_version_id "
                    "WHERE q.id = :question_id"
                ),
                {"question_id": created.id},
            ).scalar_one()
        assert version_rows == [1, 2]
        assert pointer_parent == created.id
    finally:
        engine.dispose()


def test_concurrent_hypothesis_revisions_serialize_safely(
    service_factory: Callable[[], ApplicationService], monkeypatch: pytest.MonkeyPatch
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    created = service.create_hypothesis(
        CreateHypothesisCommand(
            project_id, "Concurrent hypothesis", None, None, None, actor_context
        )
    )
    service.freeze_hypothesis(
        FreezeHypothesisCommand(created.id, created.current_version_id, actor_context, 1)
    )
    command = ReviseHypothesisCommand(
        created.id, "Concurrent revision", None, None, None, 2, actor_context
    )
    barrier = Barrier(2)
    entry_lock = Lock()
    entered = 0
    original_get_for_update = SqlAlchemyHypothesisRepository.get_for_update

    def synchronized_get_for_update(
        repository: SqlAlchemyHypothesisRepository, hypothesis_id: HypothesisId
    ) -> Hypothesis | None:
        nonlocal entered
        with entry_lock:
            entered += 1
        barrier.wait(timeout=10)
        return original_get_for_update(repository, hypothesis_id)

    monkeypatch.setattr(
        SqlAlchemyHypothesisRepository, "get_for_update", synchronized_get_for_update
    )

    def revise() -> tuple[str, object]:
        try:
            return "ok", service.revise_hypothesis(command)
        except ResearchBaseError as error:
            return "error", error

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(revise) for _ in range(2)]
        results = [future.result() for future in futures]
    assert entered == 2
    assert sorted(result[0] for result in results) == ["error", "ok"]
    error_result = next(result for result in results if result[0] == "error")
    assert isinstance(error_result[1], ResearchBaseError)
    assert error_result[1].code is ErrorCode.CONCURRENT_MODIFICATION
    history = service.get_hypothesis_history(created.id)
    assert [version.version_number for version in history] == [1, 2]
    assert service.get_hypothesis(created.id).current_version_id == history[1].id
    engine = create_database_engine()
    try:
        with engine.connect() as connection:
            version_rows = connection.execute(
                text(
                    "SELECT version_number FROM hypothesis_versions "
                    "WHERE hypothesis_id = :hypothesis_id ORDER BY version_number"
                ),
                {"hypothesis_id": created.id},
            ).scalars().all()
            pointer_parent = connection.execute(
                text(
                    "SELECT v.hypothesis_id FROM hypotheses h "
                    "JOIN hypothesis_versions v ON v.id = h.current_version_id "
                    "WHERE h.id = :hypothesis_id"
                ),
                {"hypothesis_id": created.id},
            ).scalar_one()
        assert version_rows == [1, 2]
        assert pointer_parent == created.id
    finally:
        engine.dispose()
