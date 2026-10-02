from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from tests.integration.pr12_support import postgres_resources
from tests.integration.test_pr12_application import seed_claim, seed_measurement, seed_project

from researchbase.application.closure import ClosureReport
from researchbase.application.commands import (
    ApplicationService,
    FreezeClaimVersionCommand,
    LinkEvidenceCommand,
    RecordStatisticalResultCommand,
    ReviseClaimCommand,
    StatisticalResultInputCommand,
)
from researchbase.application.dto import ClaimVersionReadModel, EvidenceRelationReadModel
from researchbase.domain.measurement import MeasurementId
from researchbase.domain.statistical_result import StatisticalResultId
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def resources() -> Iterator[tuple[Callable[[], ApplicationService], Engine]]:
    yield from postgres_resources()


@contextmanager
def _disabled_exact_triggers(
    connection: object,
    table: str,
    names: tuple[str, ...],
    constraint_names: tuple[str, ...] = (),
) -> Iterator[None]:
    foreign_key_triggers = tuple(
        row[0]
        for row in connection.execute(  # type: ignore[attr-defined]
            text(
                "SELECT t.tgname "
                "FROM pg_trigger AS t "
                "JOIN pg_constraint AS c ON c.oid=t.tgconstraint "
                "JOIN pg_class AS r ON r.oid=t.tgrelid "
                "JOIN pg_namespace AS n ON n.oid=r.relnamespace "
                "WHERE n.nspname='public' AND r.relname=:table "
                "AND c.conname = ANY(:constraint_names) "
                "ORDER BY t.tgname"
            ),
            {"table": table, "constraint_names": list(constraint_names)},
        )
    )
    exact_names = (*names, *foreign_key_triggers)
    for name in exact_names:
        connection.exec_driver_sql(  # type: ignore[attr-defined]
            f'ALTER TABLE public."{table}" DISABLE TRIGGER "{name}"'
        )
    try:
        yield
    finally:
        for name in reversed(exact_names):
            connection.exec_driver_sql(  # type: ignore[attr-defined]
                f'ALTER TABLE public."{table}" ENABLE TRIGGER "{name}"'
            )


def test_claim_closure_traverses_mixed_exact_historical_evidence(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, _ = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "closure-mixed")
    measurement_id = seed_measurement(service, project_id, actor_context, "closure-mixed")
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
            StatisticalResultId(statistical_result.id),
            "qualifies",
            "secondary analysis",
            current.row_version,
            actor_context,
        )
    )
    current = service.get_current_claim_version(claim.id)
    frozen = service.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, current.id, actor_context, current.row_version)
    )

    report = service.validate_claim_version(frozen.id)
    assert report.complete is True
    assert report.violations == []
    assert report.visited_count >= 8
    assert {first.id, second.id} == {item.id for item in service.list_evidence_relations(frozen.id)}

    updated_claim = service.get_claim(claim.id)
    service.revise_claim(
        ReviseClaimCommand(
            claim.id,
            "Treatment improves outcome in adults",
            {"population": "adult"},
            "historical revision",
            updated_claim.row_version,
            actor_context,
        )
    )
    historical_report = service.validate_claim_version(frozen.id)
    assert historical_report.complete is True
    assert historical_report.violations == []


def test_claim_closure_traverses_all_statistical_result_inputs_and_detects_later_break(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "closure-three-inputs")
    measurement_one = seed_measurement(service, project_id, actor_context, "closure-input-one")
    measurement_two = seed_measurement(service, project_id, actor_context, "closure-input-two")
    measurement_three = seed_measurement(service, project_id, actor_context, "closure-input-three")
    order_a = (
        StatisticalResultInputCommand(measurement_one, "primary", 0),
        StatisticalResultInputCommand(measurement_two, "secondary", 1),
        StatisticalResultInputCommand(measurement_three, "tertiary", 2),
    )
    order_b = (
        StatisticalResultInputCommand(measurement_three, "tertiary", 2),
        StatisticalResultInputCommand(measurement_one, "primary", 0),
        StatisticalResultInputCommand(measurement_two, "secondary", 1),
    )

    statistical_result_a = service.record_statistical_result(
        RecordStatisticalResultCommand(
            project_id,
            "t_test",
            {"p_value": 0.01},
            {"method": "student"},
            order_a,
            actor_context,
        )
    )
    statistical_result_b = service.record_statistical_result(
        RecordStatisticalResultCommand(
            project_id,
            "t_test",
            {"p_value": 0.01},
            {"method": "student"},
            order_b,
            actor_context,
        )
    )
    expected_semantic_order = [
        (measurement_one, "primary", 0),
        (measurement_two, "secondary", 1),
        (measurement_three, "tertiary", 2),
    ]
    inputs_a = service.list_statistical_result_inputs(statistical_result_a.id)
    inputs_b = service.list_statistical_result_inputs(statistical_result_b.id)
    assert [(item.measurement_id, item.input_role, item.ordinal) for item in inputs_a] == (
        expected_semantic_order
    )
    assert [(item.measurement_id, item.input_role, item.ordinal) for item in inputs_b] == (
        expected_semantic_order
    )
    with engine.connect() as connection:
        physical_order_a = (
            connection.execute(
                text(
                    "SELECT measurement_id FROM statistical_result_inputs "
                    "WHERE statistical_result_id=:result_id ORDER BY ctid"
                ),
                {"result_id": statistical_result_a.id},
            )
            .scalars()
            .all()
        )
        physical_order_b = (
            connection.execute(
                text(
                    "SELECT measurement_id FROM statistical_result_inputs "
                    "WHERE statistical_result_id=:result_id ORDER BY ctid"
                ),
                {"result_id": statistical_result_b.id},
            )
            .scalars()
            .all()
        )
    assert physical_order_a == [measurement_one, measurement_two, measurement_three]
    assert physical_order_b == [measurement_three, measurement_one, measurement_two]

    run_ids = {
        service.get_measurement(MeasurementId(item.measurement_id)).run_id for item in inputs_a
    }
    assert len(run_ids) == 3

    def freeze_claim_with_result(
        result_id: StatisticalResultId,
    ) -> tuple[EvidenceRelationReadModel, ClaimVersionReadModel]:
        claim, version = seed_claim(service, project_id, actor_context)
        relation = service.link_evidence(
            LinkEvidenceCommand(
                claim.id,
                version.id,
                None,
                result_id,
                "supports",
                None,
                version.row_version,
                actor_context,
            )
        )
        frozen = service.freeze_claim_version(
            FreezeClaimVersionCommand(
                claim.id,
                version.id,
                actor_context,
                service.get_current_claim_version(claim.id).row_version,
            )
        )
        return relation, frozen

    relation_a, frozen_a = freeze_claim_with_result(StatisticalResultId(statistical_result_a.id))
    relation_b, frozen_b = freeze_claim_with_result(StatisticalResultId(statistical_result_b.id))

    positive_reports_a = tuple(service.validate_claim_version(frozen_a.id) for _ in range(3))
    positive_reports_b = tuple(service.validate_claim_version(frozen_b.id) for _ in range(3))
    assert positive_reports_a == (positive_reports_a[0],) * 3
    assert positive_reports_b == (positive_reports_b[0],) * 3
    assert positive_reports_a[0] == positive_reports_b[0]
    assert positive_reports_a[0].complete is True
    assert positive_reports_a[0].violations == []
    assert positive_reports_a[0].visited_count == 19
    assert relation_a.statistical_result_id == statistical_result_a.id
    assert relation_b.statistical_result_id == statistical_result_b.id

    def normalized_report(report: ClosureReport, relation_id: object) -> tuple[object, ...]:
        return (
            report.complete,
            report.visited_count,
            tuple(
                (
                    violation.code,
                    violation.object_type,
                    violation.object_id,
                    tuple(
                        "<relation_id>" if part == str(relation_id) else part
                        for part in violation.path
                    ),
                    violation.message,
                )
                for violation in report.violations
            ),
        )

    missing_measurement_id = MeasurementId(UUID("00000000-0000-0000-0000-000000000099"))
    with engine.begin() as connection:
        with _disabled_exact_triggers(
            connection,
            "statistical_result_inputs",
            ("pr17d_statistical_result_input_update", "statistical_result_inputs_immutable"),
            ("statistical_result_inputs_measurement_id_fkey",),
        ):
            for result_id in (statistical_result_a.id, statistical_result_b.id):
                updated = connection.execute(
                    text(
                        "UPDATE statistical_result_inputs SET measurement_id=:missing_id "
                        "WHERE statistical_result_id=:result_id AND ordinal=2"
                    ),
                    {"missing_id": missing_measurement_id, "result_id": result_id},
                )
                assert updated.rowcount == 1

    try:
        negative_reports_a = tuple(service.validate_claim_version(frozen_a.id) for _ in range(3))
        negative_reports_b = tuple(service.validate_claim_version(frozen_b.id) for _ in range(3))
        assert negative_reports_a == (negative_reports_a[0],) * 3
        assert negative_reports_b == (negative_reports_b[0],) * 3
        negative_a = negative_reports_a[0]
        negative_b = negative_reports_b[0]
        assert negative_a.complete is False
        assert negative_b.complete is False
        assert negative_a.visited_count == 15
        assert negative_b.visited_count == 15
        expected_path_a = [
            "claim_version",
            "evidence",
            str(relation_a.id),
            "statistical_result",
            "inputs",
            str(missing_measurement_id),
            "measurement",
        ]
        expected_path_b = [
            "claim_version",
            "evidence",
            str(relation_b.id),
            "statistical_result",
            "inputs",
            str(missing_measurement_id),
            "measurement",
        ]
        assert [item.path for item in negative_a.violations] == [expected_path_a]
        assert [item.path for item in negative_b.violations] == [expected_path_b]
        assert [item.object_id for item in negative_a.violations] == [missing_measurement_id]
        assert [item.object_id for item in negative_b.violations] == [missing_measurement_id]
        assert normalized_report(negative_a, relation_a.id) == normalized_report(
            negative_b, relation_b.id
        )
    finally:
        with engine.begin() as connection:
            with _disabled_exact_triggers(
                connection,
                "statistical_result_inputs",
                ("pr17d_statistical_result_input_update", "statistical_result_inputs_immutable"),
                ("statistical_result_inputs_measurement_id_fkey",),
            ):
                for result_id in (statistical_result_a.id, statistical_result_b.id):
                    restored = connection.execute(
                        text(
                            "UPDATE statistical_result_inputs SET measurement_id=:measurement_id "
                            "WHERE statistical_result_id=:result_id AND ordinal=2"
                        ),
                        {"measurement_id": measurement_three, "result_id": result_id},
                    )
                    assert restored.rowcount == 1


def test_claim_closure_detects_support_and_content_hash_tampering(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "closure-tamper")
    claim, version = seed_claim(service, project_id, actor_context)
    frozen = service.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, version.id, actor_context, version.row_version)
    )
    with engine.connect() as connection:
        original = connection.execute(
            text("SELECT support_set_hash, content_hash FROM claim_versions WHERE id=:id"),
            {"id": frozen.id},
        ).one()
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "ALTER TABLE claim_versions DISABLE TRIGGER claim_versions_finalized_immutable"
        )
        connection.exec_driver_sql(
            "ALTER TABLE claim_versions DISABLE TRIGGER pr17d_claim_version_update"
        )
        connection.execute(
            text(
                "UPDATE claim_versions SET support_set_hash=:support_hash, "
                "content_hash=:content_hash "
                "WHERE id=:id"
            ),
            {"id": frozen.id, "support_hash": "a" * 64, "content_hash": "b" * 64},
        )
        connection.exec_driver_sql(
            "ALTER TABLE claim_versions ENABLE TRIGGER pr17d_claim_version_update"
        )
        connection.exec_driver_sql(
            "ALTER TABLE claim_versions ENABLE TRIGGER claim_versions_finalized_immutable"
        )

    with pytest.raises(ResearchBaseError) as exc_info:
        service.validate_claim_version(frozen.id)
    assert exc_info.value.code is ErrorCode.REFERENTIAL_INTEGRITY_ERROR

    with engine.begin() as connection:
        connection.exec_driver_sql(
            "ALTER TABLE claim_versions DISABLE TRIGGER claim_versions_finalized_immutable"
        )
        connection.exec_driver_sql(
            "ALTER TABLE claim_versions DISABLE TRIGGER pr17d_claim_version_update"
        )
        connection.execute(
            text(
                "UPDATE claim_versions SET support_set_hash=:support_hash, "
                "content_hash=:content_hash "
                "WHERE id=:id"
            ),
            {"id": frozen.id, "support_hash": original[0], "content_hash": original[1]},
        )
        connection.exec_driver_sql(
            "ALTER TABLE claim_versions ENABLE TRIGGER pr17d_claim_version_update"
        )
        connection.exec_driver_sql(
            "ALTER TABLE claim_versions ENABLE TRIGGER claim_versions_finalized_immutable"
        )


def test_claim_closure_reports_missing_historical_measurement_source(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "closure-missing")
    measurement_id = seed_measurement(service, project_id, actor_context, "closure-missing")
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
    frozen = service.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, current.id, actor_context, current.row_version)
    )
    missing_id = MeasurementId(UUID("00000000-0000-0000-0000-000000000099"))
    with engine.begin() as connection:
        with _disabled_exact_triggers(
            connection,
            "evidence_relations",
            ("evidence_relations_draft_only", "pr17d_evidence_relation_update"),
            ("evidence_relations_measurement_id_fkey",),
        ):
            connection.execute(
                text(
                    "UPDATE evidence_relations SET measurement_id=:missing_id WHERE id=:relation_id"
                ),
                {"missing_id": missing_id, "relation_id": relation.id},
            )

    report = service.validate_claim_version(frozen.id)
    assert report.complete is False
    assert any(
        item.code == ErrorCode.NOT_FOUND.value
        and item.object_type == "Measurement"
        and item.object_id == missing_id
        for item in report.violations
    )

    with engine.begin() as connection:
        with _disabled_exact_triggers(
            connection,
            "evidence_relations",
            ("evidence_relations_draft_only", "pr17d_evidence_relation_update"),
            ("evidence_relations_measurement_id_fkey",),
        ):
            connection.execute(
                text(
                    "UPDATE evidence_relations SET measurement_id=:measurement_id "
                    "WHERE id=:relation_id"
                ),
                {"measurement_id": measurement_id, "relation_id": relation.id},
            )


def test_claim_closure_rejects_non_final_metric_definition_version(
    resources: tuple[Callable[[], ApplicationService], Engine],
) -> None:
    factory, engine = resources
    service = factory()
    _, project_id, actor_context = seed_project(service, "closure-metric")
    measurement_id = seed_measurement(service, project_id, actor_context, "closure-metric")
    claim, version = seed_claim(service, project_id, actor_context)
    service.link_evidence(
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
        FreezeClaimVersionCommand(claim.id, current.id, actor_context, current.row_version)
    )
    with engine.connect() as connection:
        metric_row = connection.execute(
            text(
                "SELECT mdv.id, mdv.content_hash, mdv.frozen_at "
                "FROM measurements m JOIN metric_definition_versions mdv "
                "ON mdv.id=m.metric_definition_version_id WHERE m.id=:measurement_id"
            ),
            {"measurement_id": measurement_id},
        ).one()
    metric_version_id, metric_content_hash, metric_frozen_at = metric_row
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE metric_definition_versions "
                "DISABLE TRIGGER metric_definition_versions_frozen_immutable"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE metric_definition_versions "
                "DISABLE TRIGGER pr17d_metric_definition_version_update"
            )
        )
        connection.execute(
            text(
                "UPDATE metric_definition_versions SET status='DRAFT', "
                "content_hash=NULL, frozen_at=NULL WHERE id=:id"
            ),
            {"id": metric_version_id},
        )
        connection.execute(
            text(
                "ALTER TABLE metric_definition_versions "
                "ENABLE TRIGGER pr17d_metric_definition_version_update"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE metric_definition_versions "
                "ENABLE TRIGGER metric_definition_versions_frozen_immutable"
            )
        )

    report = service.validate_claim_version(frozen.id)
    assert report.complete is False
    assert any(
        item.code == ErrorCode.VERSION_NOT_FROZEN.value
        and item.object_type == "MetricDefinitionVersion"
        for item in report.violations
    )

    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE metric_definition_versions "
                "DISABLE TRIGGER metric_definition_versions_frozen_immutable"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE metric_definition_versions "
                "DISABLE TRIGGER pr17d_metric_definition_version_update"
            )
        )
        connection.execute(
            text(
                "UPDATE metric_definition_versions SET status='FROZEN', "
                "content_hash=:content_hash, frozen_at=:frozen_at WHERE id=:id"
            ),
            {
                "id": metric_version_id,
                "content_hash": metric_content_hash,
                "frozen_at": metric_frozen_at,
            },
        )
        connection.execute(
            text(
                "ALTER TABLE metric_definition_versions "
                "ENABLE TRIGGER pr17d_metric_definition_version_update"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE metric_definition_versions "
                "ENABLE TRIGGER metric_definition_versions_frozen_immutable"
            )
        )
