from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError

from researchbase.application.commands import (
    ApplicationService,
    CreateActorCommand,
    CreateClaimCommand,
    CreateExperimentSpecCommand,
    CreateMetricDefinitionCommand,
    CreateProjectCommand,
    CreateRunCommand,
    FinishRunCommand,
    FreezeClaimVersionCommand,
    FreezeExperimentSpecCommand,
    FreezeMetricDefinitionCommand,
    LinkEvidenceCommand,
    RecordMeasurementCommand,
    RecordStatisticalResultCommand,
    ReviseClaimCommand,
    StartRunCommand,
    StatisticalResultInputCommand,
    UnlinkEvidenceCommand,
    UpdateClaimDraftCommand,
)
from researchbase.domain.claim import ClaimVersionId
from researchbase.domain.identity import ActorType
from researchbase.domain.measurement import MeasurementId
from researchbase.domain.organization import ProjectId
from researchbase.domain.run import RunStatus
from researchbase.domain.statistical_result import StatisticalResultId
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.time import FixedClock
from researchbase.persistence.database import create_database_engine, create_session_factory
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def resources() -> Iterator[tuple[Callable[[], ApplicationService], Engine]]:
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set; run against the real PostgreSQL service")
    engine = create_database_engine()
    sessions = create_session_factory(engine)
    clock = FixedClock(datetime(2026, 8, 30, 0, 0, tzinfo=UTC))
    try:
        yield lambda: ApplicationService(lambda: SqlAlchemyUnitOfWork(sessions), clock), engine
    finally:
        engine.dispose()


def context(actor_id: UUID) -> ExecutionContext:
    return ExecutionContext(actor_id=actor_id, request_id=uuid4(), client_type="test")


def seed_project(
    service: ApplicationService, label: str
) -> tuple[UUID, ProjectId, ExecutionContext]:
    actor = service.create_actor(
        CreateActorCommand(ActorType.HUMAN, f"{label}-{uuid4()}", None, context(uuid4()))
    )
    actor_context = context(actor.id)
    project = service.create_project(
        CreateProjectCommand(f"{label}-{uuid4()}", None, actor_context)
    )
    return actor.id, ProjectId(project.id), actor_context


def seed_measurement(
    service: ApplicationService,
    project_id: ProjectId,
    actor_context: ExecutionContext,
    label: str,
    value: float = 1.25,
) -> MeasurementId:
    metric = service.create_metric_definition(
        CreateMetricDefinitionCommand(
            project_id, f"{label}-metric-{uuid4()}", {"kind": "mean"}, "ms", "mean", actor_context
        )
    )
    assert metric.current_version_id is not None
    metric_version = service.freeze_metric_definition(
        FreezeMetricDefinitionCommand(metric.id, metric.current_version_id, actor_context, 1)
    )
    spec = service.create_experiment_spec(
        CreateExperimentSpecCommand(
            project_id,
            None,
            f"{label}-spec",
            "PR-12 closure test",
            {"steps": ["execute"]},
            None,
            None,
            None,
            actor_context,
        )
    )
    assert spec.current_version_id is not None
    frozen_spec = service.freeze_experiment_spec(
        FreezeExperimentSpecCommand(spec.id, spec.current_version_id, actor_context, 1)
    )
    run = service.create_run(CreateRunCommand(project_id, frozen_spec.id, None, actor_context))
    started = service.start_run(StartRunCommand(run.id, run.row_version, actor_context))
    finished = service.finish_run(
        FinishRunCommand(run.id, RunStatus.SUCCEEDED, 0, None, started.row_version, actor_context)
    )
    measurement = service.record_measurement(
        RecordMeasurementCommand(
            finished.id,
            metric_version.id,
            value,
            None,
            "ms",
            {"split": "test"},
            actor_context,
        )
    )
    return MeasurementId(measurement.id)


def seed_claim(
    service: ApplicationService,
    project_id: ProjectId,
    actor_context: ExecutionContext,
    statement: str = "Treatment improves outcome",
):
    claim = service.create_claim(
        CreateClaimCommand(project_id, statement, {"population": "adult"}, None, actor_context)
    )
    version = service.get_current_claim_version(claim.id)
    return claim, version


def test_create_freeze_revise_preserves_exact_historical_evidence(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "claim-lifecycle")
    measurement_id = seed_measurement(service, project_id, actor_context, "claim-lifecycle")
    claim, version = seed_claim(service, project_id, actor_context)

    relation = service.link_evidence(
        LinkEvidenceCommand(
            claim.id,
            version.id,
            measurement_id,
            None,
            "supports",
            "primary endpoint",
            version.row_version,
            actor_context,
        )
    )
    linked_version = service.get_current_claim_version(claim.id)
    frozen = service.freeze_claim_version(
        FreezeClaimVersionCommand(
            claim.id, linked_version.id, actor_context, linked_version.row_version
        )
    )
    evidence_before = service.list_evidence_relations(frozen.id)
    claim = service.get_claim(claim.id)

    revised_claim = service.revise_claim(
        ReviseClaimCommand(
            claim.id,
            "Treatment improves outcome in adults",
            {"population": "adult"},
            "replication",
            claim.row_version,
            actor_context,
        )
    )
    revised_version = service.get_current_claim_version(revised_claim.id)

    assert frozen.status.value == "FROZEN"
    assert evidence_before[0].id == relation.id
    assert revised_version.status.value == "DRAFT"
    assert service.list_evidence_relations(revised_version.id) == []
    assert service.get_claim_version(frozen.id).content_hash == frozen.content_hash
    assert service.get_claim_version(frozen.id).support_set_hash == frozen.support_set_hash
    assert [item.version_number for item in service.get_claim_history(claim.id)] == [1, 2]


def test_link_supports_measurement_and_statistical_result_with_same_source_different_types(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "claim-evidence")
    measurement_id = seed_measurement(service, project_id, actor_context, "claim-evidence")
    result = service.record_statistical_result(
        RecordStatisticalResultCommand(
            project_id,
            "t_test",
            {"p_value": 0.01},
            {"method": "student"},
            (StatisticalResultInputCommand(measurement_id),),
            actor_context,
        )
    )
    claim, version = seed_claim(service, project_id, actor_context)

    first = service.link_evidence(
        LinkEvidenceCommand(
            claim.id,
            version.id,
            measurement_id,
            None,
            "supports",
            None,
            version.row_version,
            actor_context,
        )
    )
    current = service.get_current_claim_version(claim.id)
    second = service.link_evidence(
        LinkEvidenceCommand(
            claim.id,
            version.id,
            None,
            result.id,
            "supports",
            None,
            current.row_version,
            actor_context,
        )
    )
    current = service.get_current_claim_version(claim.id)
    third = service.link_evidence(
        LinkEvidenceCommand(
            claim.id,
            version.id,
            measurement_id,
            None,
            "qualifies",
            None,
            current.row_version,
            actor_context,
        )
    )

    listed = service.list_evidence_relations(version.id)
    assert [item.id for item in listed] == [third.id, first.id, second.id]
    assert {item.relation_type.value for item in listed} == {"supports", "qualifies"}
    assert listed[2].statistical_result_id == StatisticalResultId(result.id)

    with pytest.raises(ResearchBaseError) as duplicate:
        service.link_evidence(
            LinkEvidenceCommand(
                claim.id,
                version.id,
                measurement_id,
                None,
                "supports",
                "different qualification",
                service.get_current_claim_version(claim.id).row_version,
                actor_context,
            )
        )
    assert duplicate.value.code is ErrorCode.VALIDATION_ERROR


def test_cross_project_evidence_is_rejected_and_draft_unchanged(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_one, context_one = seed_project(service, "claim-project-one")
    _, project_two, context_two = seed_project(service, "claim-project-two")
    foreign_measurement = seed_measurement(service, project_two, context_two, "foreign")
    claim, version = seed_claim(service, project_one, context_one)

    with pytest.raises(ResearchBaseError) as exc_info:
        service.link_evidence(
            LinkEvidenceCommand(
                claim.id,
                version.id,
                foreign_measurement,
                None,
                "supports",
                None,
                version.row_version,
                context_one,
            )
        )

    assert exc_info.value.code is ErrorCode.REFERENTIAL_INTEGRITY_ERROR
    assert service.list_evidence_relations(version.id) == []
    assert service.get_current_claim_version(claim.id).row_version == version.row_version


def test_cross_project_statistical_result_evidence_is_rejected(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_one, context_one = seed_project(service, "claim-stat-project-one")
    _, project_two, context_two = seed_project(service, "claim-stat-project-two")
    foreign_measurement = seed_measurement(service, project_two, context_two, "foreign-stat")
    foreign_result = service.record_statistical_result(
        RecordStatisticalResultCommand(
            project_two,
            "t_test",
            {"p_value": 0.05},
            {"method": "student"},
            (StatisticalResultInputCommand(foreign_measurement),),
            context_two,
        )
    )
    claim, version = seed_claim(service, project_one, context_one)

    with pytest.raises(ResearchBaseError) as exc_info:
        service.link_evidence(
            LinkEvidenceCommand(
                claim.id,
                version.id,
                None,
                StatisticalResultId(foreign_result.id),
                "supports",
                None,
                version.row_version,
                context_one,
            )
        )

    assert exc_info.value.code is ErrorCode.REFERENTIAL_INTEGRITY_ERROR
    assert service.list_evidence_relations(version.id) == []


@pytest.mark.parametrize(
    ("measurement_id", "statistical_result_id", "relation_type"),
    [
        (None, None, "supports"),
        (MeasurementId(UUID(int=99)), StatisticalResultId(UUID(int=100)), "supports"),
        (MeasurementId(UUID(int=99)), None, "not-a-relation"),
    ],
)
def test_evidence_application_validation_is_stable(
    resources: tuple[Callable[[], ApplicationService], Engine],
    measurement_id: MeasurementId | None,
    statistical_result_id: StatisticalResultId | None,
    relation_type: str,
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "claim-validation")
    claim, version = seed_claim(service, project_id, actor_context)

    with pytest.raises(ResearchBaseError) as exc_info:
        service.link_evidence(
            LinkEvidenceCommand(
                claim.id,
                version.id,
                measurement_id,
                statistical_result_id,
                relation_type,
                None,
                version.row_version,
                actor_context,
            )
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert service.list_evidence_relations(version.id) == []


def test_claim_version_and_relation_parent_boundaries_are_enforced(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "claim-parent")
    measurement_id = seed_measurement(service, project_id, actor_context, "claim-parent")
    claim_one, version_one = seed_claim(service, project_id, actor_context, "claim one")
    claim_two, version_two = seed_claim(service, project_id, actor_context, "claim two")

    with pytest.raises(ResearchBaseError) as freeze_error:
        service.freeze_claim_version(
            FreezeClaimVersionCommand(
                claim_one.id, version_two.id, actor_context, version_two.row_version
            )
        )
    assert freeze_error.value.code is ErrorCode.REFERENTIAL_INTEGRITY_ERROR

    with pytest.raises(ResearchBaseError) as link_error:
        service.link_evidence(
            LinkEvidenceCommand(
                claim_one.id,
                version_two.id,
                measurement_id,
                None,
                "supports",
                None,
                version_two.row_version,
                actor_context,
            )
        )
    assert link_error.value.code is ErrorCode.REFERENTIAL_INTEGRITY_ERROR

    relation = service.link_evidence(
        LinkEvidenceCommand(
            claim_two.id,
            version_two.id,
            measurement_id,
            None,
            "supports",
            None,
            version_two.row_version,
            actor_context,
        )
    )
    with pytest.raises(ResearchBaseError) as unlink_error:
        service.unlink_evidence(
            UnlinkEvidenceCommand(
                claim_one.id,
                version_one.id,
                relation.id,
                version_one.row_version,
                actor_context,
            )
        )
    assert unlink_error.value.code is ErrorCode.REFERENTIAL_INTEGRITY_ERROR
    assert service.list_evidence_relations(version_two.id) == [relation]


def test_stale_identity_and_draft_version_writers_are_rejected(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "claim-stale")
    claim, version = seed_claim(service, project_id, actor_context)
    first_version = service.get_current_claim_version(claim.id)
    second_version = service.get_current_claim_version(claim.id)

    service.update_claim_draft(
        UpdateClaimDraftCommand(
            claim.id,
            first_version.id,
            "first draft edit",
            first_version.scope,
            first_version.qualification,
            first_version.row_version,
            actor_context,
        )
    )
    with pytest.raises(ResearchBaseError) as draft_error:
        service.update_claim_draft(
            UpdateClaimDraftCommand(
                claim.id,
                second_version.id,
                "stale draft edit",
                second_version.scope,
                second_version.qualification,
                second_version.row_version,
                actor_context,
            )
        )
    assert draft_error.value.code is ErrorCode.CONCURRENT_MODIFICATION
    assert service.get_current_claim_version(claim.id).statement == "first draft edit"

    current = service.get_current_claim_version(claim.id)
    frozen = service.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, current.id, actor_context, current.row_version)
    )
    identity_one = service.get_claim(claim.id)
    identity_two = service.get_claim(claim.id)
    service.revise_claim(
        ReviseClaimCommand(
            claim.id,
            "revision one",
            frozen.scope,
            frozen.qualification,
            identity_one.row_version,
            actor_context,
        )
    )
    with pytest.raises(ResearchBaseError) as identity_error:
        service.revise_claim(
            ReviseClaimCommand(
                claim.id,
                "stale revision",
                frozen.scope,
                frozen.qualification,
                identity_two.row_version,
                actor_context,
            )
        )
    assert identity_error.value.code is ErrorCode.CONCURRENT_MODIFICATION


def test_application_rejects_cross_parent_current_pointer_update(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "claim-pointer")
    claim_one, version_one = seed_claim(service, project_id, actor_context, "claim one")
    claim_two, version_two = seed_claim(service, project_id, actor_context, "claim two")

    with pytest.raises(ResearchBaseError) as exc_info:
        service.freeze_claim_version(
            FreezeClaimVersionCommand(
                claim_one.id, version_two.id, actor_context, version_one.row_version
            )
        )
    assert exc_info.value.code is ErrorCode.REFERENTIAL_INTEGRITY_ERROR
    assert service.get_claim(claim_one.id).current_version_id == version_one.id


def test_zero_evidence_claim_freeze_is_allowed_by_frozen_spec(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "claim-empty")
    claim, version = seed_claim(service, project_id, actor_context)

    frozen = service.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, version.id, actor_context, version.row_version)
    )
    report = service.validate_claim_version(frozen.id)

    assert frozen.support_set_hash is not None
    assert frozen.content_hash is not None
    assert report.complete is True


def test_draft_unlink_and_non_draft_unlink_are_state_guarded(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "claim-unlink")
    measurement_id = seed_measurement(service, project_id, actor_context, "claim-unlink")
    claim, version = seed_claim(service, project_id, actor_context)
    relation = service.link_evidence(
        LinkEvidenceCommand(
            claim.id,
            version.id,
            measurement_id,
            None,
            "supports",
            None,
            version.row_version,
            actor_context,
        )
    )
    current = service.get_current_claim_version(claim.id)
    service.unlink_evidence(
        UnlinkEvidenceCommand(claim.id, version.id, relation.id, current.row_version, actor_context)
    )
    assert service.list_evidence_relations(version.id) == []

    relation = service.link_evidence(
        LinkEvidenceCommand(
            claim.id,
            version.id,
            measurement_id,
            None,
            "supports",
            None,
            service.get_current_claim_version(claim.id).row_version,
            actor_context,
        )
    )
    current = service.get_current_claim_version(claim.id)
    service.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, version.id, actor_context, current.row_version)
    )
    current = service.get_current_claim_version(claim.id)
    with pytest.raises(ResearchBaseError) as exc_info:
        service.unlink_evidence(
            UnlinkEvidenceCommand(
                claim.id, version.id, relation.id, current.row_version, actor_context
            )
        )
    assert exc_info.value.code is ErrorCode.IMMUTABLE_RECORD


def _fresh_evidence_state(
    engine: Engine, version_id: ClaimVersionId
) -> tuple[tuple[tuple[object, ...], ...], object, object]:
    with engine.connect() as connection:
        edges = tuple(
            tuple(row)
            for row in connection.execute(
                text(
                    "SELECT id, claim_version_id, measurement_id, statistical_result_id, "
                    "relation_type, qualification FROM evidence_relations "
                    "WHERE claim_version_id=:version_id ORDER BY id"
                ),
                {"version_id": version_id},
            ).all()
        )
        support_set_hash, content_hash = connection.execute(
            text("SELECT support_set_hash, content_hash FROM claim_versions WHERE id=:version_id"),
            {"version_id": version_id},
        ).one()
    return edges, support_set_hash, content_hash


def _assert_fresh_evidence_state(
    factory: Callable[[], ApplicationService],
    engine: Engine,
    version_id: ClaimVersionId,
    expected: tuple[tuple[tuple[object, ...], ...], object, object],
) -> None:
    assert _fresh_evidence_state(engine, version_id) == expected
    assert len(factory().list_evidence_relations(version_id)) == len(expected[0])


def test_direct_sql_frozen_evidence_mutation_matrix_is_rejected(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    actor_id, project_id, actor_context = seed_project(service, "claim-sql-guard")
    measurement_id = seed_measurement(service, project_id, actor_context, "claim-sql-guard")
    second_measurement_id = seed_measurement(
        service, project_id, actor_context, "claim-sql-guard-second"
    )
    statistical_result = service.record_statistical_result(
        RecordStatisticalResultCommand(
            project_id,
            "t_test",
            {"p_value": 0.01},
            {"method": "student"},
            (StatisticalResultInputCommand(measurement_id),),
            actor_context,
        )
    )
    second_statistical_result = service.record_statistical_result(
        RecordStatisticalResultCommand(
            project_id,
            "t_test",
            {"p_value": 0.02},
            {"method": "student"},
            (StatisticalResultInputCommand(second_measurement_id),),
            actor_context,
        )
    )
    claim, version = seed_claim(service, project_id, actor_context)
    measurement_relation = service.link_evidence(
        LinkEvidenceCommand(
            claim.id,
            version.id,
            measurement_id,
            None,
            "supports",
            "measurement original",
            version.row_version,
            actor_context,
        )
    )
    current = service.get_current_claim_version(claim.id)
    statistical_relation = service.link_evidence(
        LinkEvidenceCommand(
            claim.id,
            version.id,
            None,
            StatisticalResultId(statistical_result.id),
            "qualifies",
            "statistical original",
            current.row_version,
            actor_context,
        )
    )
    _other_claim, other_version = seed_claim(service, project_id, actor_context, "other claim")
    current = service.get_current_claim_version(claim.id)
    frozen = service.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, version.id, actor_context, current.row_version)
    )

    attacks = (
        (
            "INSERT INTO evidence_relations "
            "(id, claim_version_id, measurement_id, relation_type, created_by, created_at) "
            "VALUES (:id, :version_id, :measurement_id, 'supports', :actor_id, :created_at)",
            {
                "id": uuid4(),
                "version_id": frozen.id,
                "measurement_id": second_measurement_id,
                "actor_id": actor_id,
                "created_at": datetime(2026, 8, 30, tzinfo=UTC),
            },
        ),
        (
            "INSERT INTO evidence_relations "
            "(id, claim_version_id, statistical_result_id, relation_type, created_by, created_at) "
            "VALUES (:id, :version_id, :statistical_result_id, 'context', :actor_id, :created_at)",
            {
                "id": uuid4(),
                "version_id": frozen.id,
                "statistical_result_id": second_statistical_result.id,
                "actor_id": actor_id,
                "created_at": datetime(2026, 8, 30, tzinfo=UTC),
            },
        ),
        (
            "UPDATE evidence_relations SET claim_version_id=:other_version_id "
            "WHERE id=:relation_id",
            {"other_version_id": other_version.id, "relation_id": measurement_relation.id},
        ),
        (
            "UPDATE evidence_relations SET measurement_id=:measurement_id WHERE id=:relation_id",
            {"measurement_id": second_measurement_id, "relation_id": measurement_relation.id},
        ),
        (
            "UPDATE evidence_relations SET statistical_result_id=:statistical_result_id "
            "WHERE id=:relation_id",
            {
                "statistical_result_id": second_statistical_result.id,
                "relation_id": statistical_relation.id,
            },
        ),
        (
            "UPDATE evidence_relations SET relation_type='context' WHERE id=:relation_id",
            {"relation_id": measurement_relation.id},
        ),
        (
            "UPDATE evidence_relations SET qualification='tampered' WHERE id=:relation_id",
            {"relation_id": measurement_relation.id},
        ),
        (
            "DELETE FROM evidence_relations WHERE id=:relation_id",
            {"relation_id": statistical_relation.id},
        ),
    )
    expected = _fresh_evidence_state(engine, frozen.id)
    for statement, parameters in attacks:
        with pytest.raises(DBAPIError):
            with engine.begin() as connection:
                connection.execute(text(statement), parameters)
        _assert_fresh_evidence_state(factory, engine, frozen.id, expected)


def test_direct_sql_superseded_and_abandoned_evidence_mutations_are_rejected(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    actor_id, project_id, actor_context = seed_project(service, "claim-final-state-guard")
    measurement_id = seed_measurement(service, project_id, actor_context, "claim-final-state-guard")

    claim, version = seed_claim(service, project_id, actor_context, "superseded")
    relation = service.link_evidence(
        LinkEvidenceCommand(
            claim.id,
            version.id,
            measurement_id,
            None,
            "supports",
            None,
            version.row_version,
            actor_context,
        )
    )
    current = service.get_current_claim_version(claim.id)
    frozen = service.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, version.id, actor_context, current.row_version)
    )
    claim = service.get_claim(claim.id)
    service.revise_claim(
        ReviseClaimCommand(
            claim.id,
            "new version",
            frozen.scope,
            frozen.qualification,
            claim.row_version,
            actor_context,
        )
    )

    def assert_non_draft_matrix(version_id: ClaimVersionId, relation_id: UUID) -> None:
        expected = _fresh_evidence_state(engine, version_id)
        attacks = (
            (
                "INSERT INTO evidence_relations "
                "(id, claim_version_id, measurement_id, relation_type, created_by, created_at) "
                "VALUES (:new_id, :version_id, :measurement_id, 'context', :actor_id, :created_at)",
                {
                    "new_id": uuid4(),
                    "version_id": version_id,
                    "measurement_id": measurement_id,
                    "actor_id": actor_id,
                    "created_at": datetime(2026, 8, 30, tzinfo=UTC),
                },
            ),
            (
                "UPDATE evidence_relations SET qualification='tampered' WHERE id=:id",
                {"id": relation_id},
            ),
            ("DELETE FROM evidence_relations WHERE id=:id", {"id": relation_id}),
        )
        for statement, parameters in attacks:
            with pytest.raises(DBAPIError):
                with engine.begin() as connection:
                    connection.execute(text(statement), parameters)
            _assert_fresh_evidence_state(factory, engine, version_id, expected)

    assert_non_draft_matrix(frozen.id, relation.id)

    abandoned_claim, abandoned_version = seed_claim(service, project_id, actor_context, "abandoned")
    abandoned_relation = service.link_evidence(
        LinkEvidenceCommand(
            abandoned_claim.id,
            abandoned_version.id,
            measurement_id,
            None,
            "supports",
            None,
            abandoned_version.row_version,
            actor_context,
        )
    )
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE claim_versions DISABLE TRIGGER ALL"))
        connection.execute(
            text("UPDATE claim_versions SET status='ABANDONED' WHERE id=:id"),
            {"id": abandoned_version.id},
        )
        connection.execute(text("ALTER TABLE claim_versions ENABLE TRIGGER ALL"))
    assert_non_draft_matrix(abandoned_version.id, abandoned_relation.id)


def test_direct_sql_frozen_claim_version_material_is_immutable(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    actor_id, project_id, actor_context = seed_project(service, "claim-version-guard")
    claim, version = seed_claim(service, project_id, actor_context)
    frozen = service.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, version.id, actor_context, version.row_version)
    )
    other_claim, _ = seed_claim(service, project_id, actor_context, "other claim")
    attacks = (
        ("statement", "UPDATE claim_versions SET statement='tampered' WHERE id=:id", {}),
        (
            "scope",
            "UPDATE claim_versions SET scope=CAST('{}' AS jsonb) WHERE id=:id",
            {},
        ),
        ("qualification", "UPDATE claim_versions SET qualification='tampered' WHERE id=:id", {}),
        (
            "support_set_hash",
            "UPDATE claim_versions SET support_set_hash=:value WHERE id=:id",
            {"value": "a" * 64},
        ),
        (
            "content_hash",
            "UPDATE claim_versions SET content_hash=:value WHERE id=:id",
            {"value": "b" * 64},
        ),
        (
            "created_by",
            "UPDATE claim_versions SET created_by=:value WHERE id=:id",
            {"value": uuid4()},
        ),
        (
            "created_at",
            "UPDATE claim_versions SET created_at=:value WHERE id=:id",
            {"value": datetime(2026, 8, 30, 0, 0, 1, tzinfo=UTC)},
        ),
        (
            "frozen_at",
            "UPDATE claim_versions SET frozen_at=:value WHERE id=:id",
            {"value": datetime(2026, 8, 30, 0, 0, 1, tzinfo=UTC)},
        ),
        (
            "claim_id",
            "UPDATE claim_versions SET claim_id=:value WHERE id=:id",
            {"value": other_claim.id},
        ),
        (
            "version_number",
            "UPDATE claim_versions SET version_number=2 WHERE id=:id",
            {},
        ),
        (
            "status",
            "UPDATE claim_versions SET status='DRAFT' WHERE id=:id",
            {},
        ),
    )
    for _field, statement, parameters in attacks:
        with pytest.raises(DBAPIError):
            with engine.begin() as connection:
                connection.execute(text(statement), {"id": frozen.id, **parameters})

    stored = service.get_claim_version(frozen.id)
    assert stored.status.value == "FROZEN"
    assert stored.statement == frozen.statement
    assert stored.scope == frozen.scope
    assert stored.qualification == frozen.qualification
    assert stored.support_set_hash == frozen.support_set_hash
    assert stored.content_hash == frozen.content_hash
    assert stored.frozen_at == frozen.frozen_at
    assert stored.claim_id == frozen.claim_id
    assert stored.version_number == frozen.version_number
    assert stored.created_by == actor_id
