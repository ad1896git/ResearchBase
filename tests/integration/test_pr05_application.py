from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from threading import Barrier, Lock
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

import researchbase.application.commands as commands_module
from researchbase.application.commands import (
    CreateActorCommand,
    CreateExperimentSpecCommand,
    CreateHypothesisCommand,
    CreateProjectCommand,
    FreezeExperimentSpecCommand,
    ReviseExperimentSpecCommand,
    UpdateExperimentSpecDraftCommand,
)
from researchbase.domain.experiment import ExperimentSpecId, ExperimentSpecVersionId
from researchbase.domain.identity import ActorType
from researchbase.domain.organization import ProjectId
from researchbase.domain.research import HypothesisId
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.time import FixedClock
from researchbase.foundation.versioning import VersionStatus
from researchbase.persistence.database import create_database_engine, create_session_factory
from researchbase.persistence.repositories import SqlAlchemyExperimentSpecRepository
from researchbase.persistence.uow import SqlAlchemyUnitOfWork
from tests.application_compat import LegacyApplicationService as ApplicationService

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
        CreateActorCommand(ActorType.HUMAN, f"SpecOwner-{uuid4()}", None, context(uuid4()))
    )
    actor_context = context(actor.id)
    project = service.create_project(
        CreateProjectCommand(f"SpecProject-{uuid4()}", None, actor_context)
    )
    return actor.id, project.id, actor_context


def spec_command(
    project_id: ProjectId, actor_context: ExecutionContext, **overrides: object
) -> CreateExperimentSpecCommand:
    values: dict[str, object] = {
        "project_id": project_id,
        "hypothesis_id": None,
        "title": "Treatment experiment",
        "objective": "Measure treatment effect",
        "protocol": {"arms": ["control", "treatment"]},
        "planned_metrics": [{"name": "outcome"}],
        "seed_policy": {"kind": "fixed"},
        "analysis_plan": {"test": "difference-in-means"},
        "context": actor_context,
    }
    values.update(overrides)
    return CreateExperimentSpecCommand(**values)  # type: ignore[arg-type]


def test_experiment_spec_create_freeze_revise_and_history(
    service_factory: Callable[[], ApplicationService],
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    created = service.create_experiment_spec(spec_command(project_id, actor_context))
    assert created.row_version == 1
    assert created.current_version_id is not None

    frozen = service.freeze_experiment_spec(
        FreezeExperimentSpecCommand(created.id, created.current_version_id, actor_context, 1)
    )
    assert frozen.status is VersionStatus.FROZEN
    assert frozen.hash_scheme == "sha256-cjson-v1"
    revised = service.revise_experiment_spec(
        ReviseExperimentSpecCommand(
            created.id,
            "Treatment experiment revised",
            "Measure treatment effect with follow-up",
            {"arms": ["control", "treatment"], "follow_up_days": 30},
            [{"name": "outcome"}],
            {"kind": "fixed"},
            {"test": "difference-in-means"},
            2,
            actor_context,
        )
    )
    history = service.get_experiment_spec_history(ExperimentSpecId(revised.id))
    assert [item.version_number for item in history] == [1, 2]
    assert [item.status for item in history] == [VersionStatus.SUPERSEDED, VersionStatus.DRAFT]
    assert history[0].content_hash == frozen.content_hash
    assert revised.current_version_id == history[1].id


@pytest.mark.parametrize(
    "field,value",
    [("objective", ""), ("objective", "   "), ("protocol", {}), ("protocol", [])],
)
def test_freeze_rejects_invalid_material(
    service_factory: Callable[[], ApplicationService], field: str, value: object
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    created = service.create_experiment_spec(spec_command(project_id, actor_context))
    history = service.get_experiment_spec_history(created.id)
    version = history[0]
    update = UpdateExperimentSpecDraftCommand(
        created.id,
        version.id,
        version.title,
        cast(str, value) if field == "objective" else version.objective,
        value if field == "protocol" else version.protocol,
        version.planned_metrics,
        version.seed_policy,
        version.analysis_plan,
        version.row_version,
        actor_context,
    )
    with pytest.raises(ResearchBaseError) as raised:
        service.update_experiment_spec_draft(update)
    assert raised.value.code is ErrorCode.VALIDATION_ERROR


def test_hypothesis_link_requires_existence_and_same_project(
    service_factory: Callable[[], ApplicationService],
) -> None:
    service = service_factory()
    _, project_a, context_a = seed(service)
    _, project_b, context_b = seed(service)
    hypothesis_b = service.create_hypothesis(
        CreateHypothesisCommand(project_b, "Treatment helps", None, None, None, context_b)
    )
    with pytest.raises(ResearchBaseError) as raised:
        service.create_experiment_spec(
            spec_command(project_a, context_a, hypothesis_id=hypothesis_b.id)
        )
    assert raised.value.code is ErrorCode.REFERENTIAL_INTEGRITY_ERROR
    with pytest.raises(ResearchBaseError) as missing:
        service.create_experiment_spec(
            spec_command(project_a, context_a, hypothesis_id=HypothesisId(uuid4()))
        )
    assert missing.value.code is ErrorCode.NOT_FOUND


def test_hypothesis_identity_link_is_preserved_across_revise_and_freeze(
    service_factory: Callable[[], ApplicationService],
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    hypothesis = service.create_hypothesis(
        CreateHypothesisCommand(project_id, "Treatment helps", None, None, None, actor_context)
    )
    created = service.create_experiment_spec(
        spec_command(project_id, actor_context, hypothesis_id=hypothesis.id)
    )
    service.freeze_experiment_spec(
        FreezeExperimentSpecCommand(created.id, created.current_version_id, actor_context, 1)
    )
    revised = service.revise_experiment_spec(
        ReviseExperimentSpecCommand(
            created.id,
            "Revised",
            "Measure",
            {"steps": ["run"]},
            None,
            None,
            None,
            2,
            actor_context,
        )
    )
    assert service.get_experiment_spec(revised.id).hypothesis_id == hypothesis.id
    assert not hasattr(service, "relink_experiment_spec_hypothesis")


def test_create_and_revise_reject_unserializable_material_with_stable_error(
    service_factory: Callable[[], ApplicationService],
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    with pytest.raises(ResearchBaseError) as create_error:
        service.create_experiment_spec(spec_command(project_id, actor_context, protocol=object()))
    assert create_error.value.code is ErrorCode.VALIDATION_ERROR
    assert isinstance(create_error.value.__cause__, TypeError | ValueError)

    created = service.create_experiment_spec(spec_command(project_id, actor_context))
    service.freeze_experiment_spec(
        FreezeExperimentSpecCommand(created.id, created.current_version_id, actor_context, 1)
    )
    with pytest.raises(ResearchBaseError) as revise_error:
        service.revise_experiment_spec(
            ReviseExperimentSpecCommand(
                created.id,
                "Revised",
                "Measure",
                object(),
                None,
                None,
                None,
                2,
                actor_context,
            )
        )
    assert revise_error.value.code is ErrorCode.VALIDATION_ERROR
    assert isinstance(revise_error.value.__cause__, TypeError | ValueError)
    assert [item.version_number for item in service.get_experiment_spec_history(created.id)] == [1]


def test_draft_update_rejects_unserializable_material_with_stable_error(
    service_factory: Callable[[], ApplicationService],
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    created = service.create_experiment_spec(spec_command(project_id, actor_context))
    version = service.get_experiment_spec_history(created.id)[0]
    with pytest.raises(ResearchBaseError) as raised:
        service.update_experiment_spec_draft(
            UpdateExperimentSpecDraftCommand(
                created.id,
                version.id,
                version.title,
                version.objective,
                object(),
                version.planned_metrics,
                version.seed_policy,
                version.analysis_plan,
                version.row_version,
                actor_context,
            )
        )
    assert raised.value.code is ErrorCode.VALIDATION_ERROR
    assert isinstance(raised.value.__cause__, TypeError | ValueError)
    assert service.get_experiment_spec_history(created.id)[0].protocol == version.protocol


def test_freeze_rejects_unserializable_material_without_persisting_changes(
    service_factory: Callable[[], ApplicationService],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    created = service.create_experiment_spec(spec_command(project_id, actor_context))
    before_spec = service.get_experiment_spec(created.id)
    before_version = service.get_experiment_spec_history(created.id)[0]
    original = SqlAlchemyExperimentSpecRepository.get_version_for_update

    def corrupt_material(
        repository: SqlAlchemyExperimentSpecRepository, version_id: ExperimentSpecVersionId
    ):
        loaded = original(repository, version_id)
        return replace(loaded, protocol=object()) if loaded is not None else None

    monkeypatch.setattr(
        SqlAlchemyExperimentSpecRepository, "get_version_for_update", corrupt_material
    )
    with pytest.raises(ResearchBaseError) as raised:
        service.freeze_experiment_spec(
            FreezeExperimentSpecCommand(
                created.id, before_version.id, actor_context, before_version.row_version
            )
        )
    assert raised.value.code is ErrorCode.VALIDATION_ERROR
    assert isinstance(raised.value.__cause__, TypeError | ValueError)
    after_spec = service.get_experiment_spec(created.id)
    after_version = service.get_experiment_spec_history(created.id)[0]
    assert after_spec.current_version_id == before_spec.current_version_id
    assert after_spec.row_version == before_spec.row_version
    assert (
        after_version.status,
        after_version.content_hash,
        after_version.frozen_at,
        after_version.row_version,
    ) == (
        before_version.status,
        before_version.content_hash,
        before_version.frozen_at,
        before_version.row_version,
    )


def test_cross_parent_current_pointer_attack_is_rejected(
    service_factory: Callable[[], ApplicationService],
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    first = service.create_experiment_spec(spec_command(project_id, actor_context, title="A"))
    second = service.create_experiment_spec(spec_command(project_id, actor_context, title="B"))
    with pytest.raises(ResearchBaseError) as raised:
        service.freeze_experiment_spec(
            FreezeExperimentSpecCommand(first.id, second.current_version_id, actor_context, 1)
        )
    assert raised.value.code is ErrorCode.REFERENTIAL_INTEGRITY_ERROR
    assert service.get_experiment_spec(first.id).current_version_id == first.current_version_id


def test_stale_draft_update_is_rejected(
    service_factory: Callable[[], ApplicationService],
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    created = service.create_experiment_spec(spec_command(project_id, actor_context))
    version = service.get_experiment_spec_history(created.id)[0]
    service.update_experiment_spec_draft(
        UpdateExperimentSpecDraftCommand(
            created.id,
            version.id,
            "First edit",
            version.objective,
            version.protocol,
            version.planned_metrics,
            version.seed_policy,
            version.analysis_plan,
            version.row_version,
            actor_context,
        )
    )
    with pytest.raises(ResearchBaseError) as raised:
        service.update_experiment_spec_draft(
            UpdateExperimentSpecDraftCommand(
                created.id,
                version.id,
                "Stale edit",
                version.objective,
                version.protocol,
                version.planned_metrics,
                version.seed_policy,
                version.analysis_plan,
                version.row_version,
                actor_context,
            )
        )
    assert raised.value.code is ErrorCode.CONCURRENT_MODIFICATION


def test_concurrent_revisions_create_only_one_child(
    service_factory: Callable[[], ApplicationService], monkeypatch: pytest.MonkeyPatch
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    created = service.create_experiment_spec(spec_command(project_id, actor_context))
    service.freeze_experiment_spec(
        FreezeExperimentSpecCommand(created.id, created.current_version_id, actor_context, 1)
    )
    command = ReviseExperimentSpecCommand(
        created.id,
        "Concurrent revision",
        "Measure",
        {"steps": ["run"]},
        None,
        None,
        None,
        2,
        actor_context,
    )
    barrier = Barrier(2)
    lock = Lock()
    entered = 0
    original = SqlAlchemyExperimentSpecRepository.get_for_update

    def synchronized(repository: SqlAlchemyExperimentSpecRepository, spec_id: ExperimentSpecId):
        nonlocal entered
        with lock:
            entered += 1
        barrier.wait(timeout=10)
        return original(repository, spec_id)

    monkeypatch.setattr(SqlAlchemyExperimentSpecRepository, "get_for_update", synchronized)

    def revise() -> tuple[str, object]:
        try:
            return "ok", service.revise_experiment_spec(command)
        except ResearchBaseError as error:
            return "error", error

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = [future.result() for future in [executor.submit(revise), executor.submit(revise)]]
    assert entered == 2
    assert sorted(result[0] for result in results) == ["error", "ok"]
    error = next(result for result in results if result[0] == "error")[1]
    assert isinstance(error, ResearchBaseError)
    assert error.code is ErrorCode.CONCURRENT_MODIFICATION
    history = service.get_experiment_spec_history(created.id)
    assert [item.version_number for item in history] == [1, 2]
    assert all(result[0] == "ok" or isinstance(result[1], ResearchBaseError) for result in results)
    engine = create_database_engine()
    try:
        with engine.connect() as connection:
            rows = (
                connection.execute(
                    text(
                        "SELECT id, version_number, status FROM experiment_spec_versions "
                        "WHERE experiment_spec_id = :spec_id ORDER BY version_number"
                    ),
                    {"spec_id": created.id},
                )
                .mappings()
                .all()
            )
            pointer = (
                connection.execute(
                    text(
                        "SELECT s.current_version_id, s.row_version, v.experiment_spec_id "
                        "FROM experiment_specs s "
                        "JOIN experiment_spec_versions v ON v.id = s.current_version_id "
                        "WHERE s.id = :spec_id"
                    ),
                    {"spec_id": created.id},
                )
                .mappings()
                .one()
            )
        assert [(row["id"], row["version_number"], row["status"]) for row in rows] == [
            (history[0].id, 1, "SUPERSEDED"),
            (history[1].id, 2, "DRAFT"),
        ]
        assert pointer["current_version_id"] == history[1].id
        assert pointer["row_version"] == 3
        assert pointer["experiment_spec_id"] == created.id
    finally:
        engine.dispose()


def test_create_rollback_leaves_no_spec_rows(
    service_factory: Callable[[], ApplicationService], monkeypatch: pytest.MonkeyPatch
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    generated: dict[str, UUID] = {}
    original_new = commands_module.new_typed_id

    def capture(id_type: Callable[[UUID], object]) -> object:
        value = original_new(id_type)
        if isinstance(value, UUID):
            if id_type is ExperimentSpecId:
                generated["spec"] = value
            elif id_type is ExperimentSpecVersionId:
                generated["version"] = value
        return value

    monkeypatch.setattr(commands_module, "new_typed_id", capture)
    observed = False

    def fail_commit(uow: SqlAlchemyUnitOfWork) -> None:
        nonlocal observed
        uow._require_session().flush()
        observed = True
        raise RuntimeError("forced commit failure")

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="forced commit failure"):
        service.create_experiment_spec(spec_command(project_id, actor_context))
    assert observed
    engine = create_database_engine()
    try:
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT count(*) FROM experiment_specs WHERE id=:id"),
                    {"id": generated["spec"]},
                ).scalar_one()
                == 0
            )
            assert (
                connection.execute(
                    text("SELECT count(*) FROM experiment_spec_versions WHERE id=:id"),
                    {"id": generated["version"]},
                ).scalar_one()
                == 0
            )
    finally:
        engine.dispose()


def test_freeze_and_revise_roll_back_without_partial_state(
    service_factory: Callable[[], ApplicationService], monkeypatch: pytest.MonkeyPatch
) -> None:
    service = service_factory()
    _, project_id, actor_context = seed(service)
    created = service.create_experiment_spec(spec_command(project_id, actor_context))
    before_spec = service.get_experiment_spec(created.id)
    before_version = service.get_experiment_spec_history(created.id)[0]
    before_freeze_state = (
        before_version.status,
        before_version.content_hash,
        before_version.frozen_at,
        before_version.row_version,
        before_spec.current_version_id,
        before_spec.row_version,
    )

    def fail_commit(uow: SqlAlchemyUnitOfWork) -> None:
        uow._require_session().flush()
        raise RuntimeError("forced commit failure")

    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="forced commit failure"):
        service.freeze_experiment_spec(
            FreezeExperimentSpecCommand(
                created.id, before_version.id, actor_context, before_version.row_version
            )
        )
    after_failed_spec = service.get_experiment_spec(created.id)
    after_failed_version = service.get_experiment_spec_history(created.id)[0]
    assert (
        after_failed_version.status,
        after_failed_version.content_hash,
        after_failed_version.frozen_at,
        after_failed_version.row_version,
        after_failed_spec.current_version_id,
        after_failed_spec.row_version,
    ) == before_freeze_state

    monkeypatch.undo()
    frozen = service.freeze_experiment_spec(
        FreezeExperimentSpecCommand(
            created.id, before_version.id, actor_context, before_version.row_version
        )
    )
    before_revise_spec = service.get_experiment_spec(created.id)
    before_revise_history = service.get_experiment_spec_history(created.id)
    before_revise_state = (
        before_revise_spec.current_version_id,
        before_revise_spec.row_version,
        [
            (
                item.id,
                item.version_number,
                item.status,
                item.content_hash,
                item.frozen_at,
                item.row_version,
            )
            for item in before_revise_history
        ],
    )
    monkeypatch.setattr(SqlAlchemyUnitOfWork, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="forced commit failure"):
        service.revise_experiment_spec(
            ReviseExperimentSpecCommand(
                created.id,
                "Revised",
                "Measure again",
                {"steps": ["run"]},
                None,
                None,
                None,
                2,
                actor_context,
            )
        )
    monkeypatch.undo()
    after_revise_spec = service.get_experiment_spec(created.id)
    history = service.get_experiment_spec_history(created.id)
    assert (
        after_revise_spec.current_version_id,
        after_revise_spec.row_version,
        [
            (
                item.id,
                item.version_number,
                item.status,
                item.content_hash,
                item.frozen_at,
                item.row_version,
            )
            for item in history
        ],
    ) == before_revise_state
    assert history[0].content_hash == frozen.content_hash
