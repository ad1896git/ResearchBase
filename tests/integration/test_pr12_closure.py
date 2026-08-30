from __future__ import annotations

from collections.abc import Callable, Iterator
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from tests.integration.pr12_support import postgres_resources
from tests.integration.test_pr12_application import seed_claim, seed_measurement, seed_project

from researchbase.application.commands import (
    ApplicationService,
    FreezeClaimVersionCommand,
    LinkEvidenceCommand,
    RecordStatisticalResultCommand,
    ReviseClaimCommand,
    StatisticalResultInputCommand,
)
from researchbase.domain.measurement import MeasurementId
from researchbase.domain.statistical_result import StatisticalResultId
from researchbase.foundation.errors import ErrorCode

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def resources() -> Iterator[tuple[Callable[[], ApplicationService], Engine]]:
    yield from postgres_resources()


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
    statistical_result = service.record_statistical_result(
        RecordStatisticalResultCommand(
            project_id,
            "t_test",
            {"p_value": 0.01},
            {"method": "student"},
            (
                StatisticalResultInputCommand(measurement_one, "primary", 0),
                StatisticalResultInputCommand(measurement_two, "secondary", 1),
                StatisticalResultInputCommand(measurement_three, "tertiary", 2),
            ),
            actor_context,
        )
    )
    inputs = service.list_statistical_result_inputs(statistical_result.id)
    assert [(item.measurement_id, item.input_role, item.ordinal) for item in inputs] == [
        (measurement_one, "primary", 0),
        (measurement_two, "secondary", 1),
        (measurement_three, "tertiary", 2),
    ]
    run_ids = {
        service.get_measurement(MeasurementId(item.measurement_id)).run_id for item in inputs
    }
    assert len(run_ids) == 3

    claim, version = seed_claim(service, project_id, actor_context)
    relation = service.link_evidence(
        LinkEvidenceCommand(
            claim.id,
            version.id,
            None,
            StatisticalResultId(statistical_result.id),
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

    positive = service.validate_claim_version(frozen.id)
    assert positive.complete is True
    assert positive.violations == []
    assert positive.visited_count >= 1 + 1 + 1 + 1 + 3 + 3
    assert relation.statistical_result_id == statistical_result.id

    missing_measurement_id = MeasurementId(UUID("00000000-0000-0000-0000-000000000099"))
    with engine.begin() as connection:
        connection.exec_driver_sql("ALTER TABLE statistical_result_inputs DISABLE TRIGGER ALL")
        connection.execute(
            text(
                "UPDATE statistical_result_inputs SET measurement_id=:missing_id "
                "WHERE statistical_result_id=:result_id AND ordinal=2"
            ),
            {"missing_id": missing_measurement_id, "result_id": statistical_result.id},
        )
        connection.exec_driver_sql("ALTER TABLE statistical_result_inputs ENABLE TRIGGER ALL")

    try:
        negative = service.validate_claim_version(frozen.id)
        assert negative.complete is False
        missing_violations = [
            item
            for item in negative.violations
            if item.object_type == "Measurement" and item.object_id == missing_measurement_id
        ]
        assert len(missing_violations) == 1
        assert missing_violations[0].path == [
            "claim_version",
            "evidence",
            str(relation.id),
            "statistical_result",
            "inputs",
            str(missing_measurement_id),
            "measurement",
        ]
        assert [item.path for item in negative.violations] == [missing_violations[0].path]
    finally:
        with engine.begin() as connection:
            connection.exec_driver_sql("ALTER TABLE statistical_result_inputs DISABLE TRIGGER ALL")
            connection.execute(
                text(
                    "UPDATE statistical_result_inputs SET measurement_id=:measurement_id "
                    "WHERE statistical_result_id=:result_id AND ordinal=2"
                ),
                {"measurement_id": measurement_three, "result_id": statistical_result.id},
            )
            connection.exec_driver_sql("ALTER TABLE statistical_result_inputs ENABLE TRIGGER ALL")


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
        connection.execute(
            text(
                "UPDATE claim_versions SET support_set_hash=:support_hash, "
                "content_hash=:content_hash "
                "WHERE id=:id"
            ),
            {"id": frozen.id, "support_hash": "a" * 64, "content_hash": "b" * 64},
        )
        connection.exec_driver_sql(
            "ALTER TABLE claim_versions ENABLE TRIGGER claim_versions_finalized_immutable"
        )

    report = service.validate_claim_version(frozen.id)
    assert report.complete is False
    assert {item.code for item in report.violations} == {
        "SUPPORT_SET_HASH_MISMATCH",
        "CONTENT_HASH_MISMATCH",
    }
    assert [item.path for item in report.violations] == [
        ["claim_version", "content_hash"],
        ["claim_version", "support_set_hash"],
    ]

    with engine.begin() as connection:
        connection.exec_driver_sql(
            "ALTER TABLE claim_versions DISABLE TRIGGER claim_versions_finalized_immutable"
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
        connection.exec_driver_sql("ALTER TABLE evidence_relations DISABLE TRIGGER ALL")
        connection.execute(
            text("UPDATE evidence_relations SET measurement_id=:missing_id WHERE id=:relation_id"),
            {"missing_id": missing_id, "relation_id": relation.id},
        )
        connection.exec_driver_sql("ALTER TABLE evidence_relations ENABLE TRIGGER ALL")

    report = service.validate_claim_version(frozen.id)
    assert report.complete is False
    assert any(
        item.code == ErrorCode.NOT_FOUND.value
        and item.object_type == "Measurement"
        and item.object_id == missing_id
        for item in report.violations
    )

    with engine.begin() as connection:
        connection.exec_driver_sql("ALTER TABLE evidence_relations DISABLE TRIGGER ALL")
        connection.execute(
            text(
                "UPDATE evidence_relations SET measurement_id=:measurement_id WHERE id=:relation_id"
            ),
            {"measurement_id": measurement_id, "relation_id": relation.id},
        )
        connection.exec_driver_sql("ALTER TABLE evidence_relations ENABLE TRIGGER ALL")


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
        metric_version_id = connection.execute(
            text("SELECT metric_definition_version_id FROM measurements WHERE id=:measurement_id"),
            {"measurement_id": measurement_id},
        ).scalar_one()
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE metric_definition_versions SET status='DRAFT' WHERE id=:id"),
            {"id": metric_version_id},
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
            text("UPDATE metric_definition_versions SET status='FROZEN' WHERE id=:id"),
            {"id": metric_version_id},
        )
