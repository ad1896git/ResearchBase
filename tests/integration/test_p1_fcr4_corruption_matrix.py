from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace

import pytest
from sqlalchemy import Engine, text
from tests.e2e.support import WorkflowFixture, WorkflowIds, fresh_fixture, run_workflow
from tests.oracles.pr14_governance_hash_oracle import (
    correction_record_hash,
    impact_assessment_hash,
)

from researchbase.application.commands import RecordMeasurementCommand
from researchbase.domain.claim import ClaimId, ClaimVersionId
from researchbase.domain.evidence import DatasetSnapshotId
from researchbase.domain.experiment import ExperimentSpecId, ExperimentSpecVersionId
from researchbase.domain.governance import GovernanceTargetType
from researchbase.domain.measurement import MeasurementId
from researchbase.domain.metric import MetricDefinitionId, MetricDefinitionVersionId
from researchbase.domain.organization import ProjectId
from researchbase.domain.research import (
    HypothesisId,
    HypothesisVersionId,
    ResearchQuestionId,
    ResearchQuestionVersionId,
)
from researchbase.domain.run import RunId
from researchbase.domain.statistical_result import StatisticalResultId
from researchbase.foundation.errors import ErrorCode, ResearchBaseError


@dataclass(frozen=True, slots=True)
class CorruptionOwner:
    name: str
    table: str
    id_getter: Callable[[WorkflowIds], object]
    reader: Callable[[WorkflowFixture, WorkflowIds], object]
    material_assignment: str
    material_parameters: dict[str, object]
    has_hash_scheme: bool


OWNERS = (
    CorruptionOwner(
        "ResearchQuestionVersion",
        "research_question_versions",
        lambda ids: ids.research_question_version_id,
        lambda fixture, ids: fixture.application.get_research_question_version(
            ResearchQuestionVersionId(ids.research_question_version_id)
        ),
        "question_text=:material",
        {"material": "corrupt question"},
        False,
    ),
    CorruptionOwner(
        "HypothesisVersion",
        "hypothesis_versions",
        lambda ids: ids.hypothesis_version_id,
        lambda fixture, ids: fixture.application.get_hypothesis_version(
            HypothesisVersionId(ids.hypothesis_version_id)
        ),
        "statement=:material",
        {"material": "corrupt hypothesis"},
        False,
    ),
    CorruptionOwner(
        "ExperimentSpecVersion",
        "experiment_spec_versions",
        lambda ids: ids.experiment_spec_version_id,
        lambda fixture, ids: fixture.application.get_experiment_spec_version(
            ExperimentSpecVersionId(ids.experiment_spec_version_id)
        ),
        "title=:material",
        {"material": "corrupt experiment"},
        False,
    ),
    CorruptionOwner(
        "DatasetSnapshot",
        "dataset_snapshots",
        lambda ids: ids.dataset_snapshot_id,
        lambda fixture, ids: fixture.application.get_dataset_snapshot(
            DatasetSnapshotId(ids.dataset_snapshot_id)
        ),
        "selection_definition=CAST(:material AS jsonb)",
        {"material": '{"corrupt":true}'},
        False,
    ),
    CorruptionOwner(
        "MetricDefinitionVersion",
        "metric_definition_versions",
        lambda ids: ids.metric_definition_version_id,
        lambda fixture, ids: fixture.application.get_metric_definition_version(
            MetricDefinitionVersionId(ids.metric_definition_version_id)
        ),
        "definition=CAST(:material AS jsonb)",
        {"material": '{"corrupt":true}'},
        False,
    ),
    CorruptionOwner(
        "Measurement",
        "measurements",
        lambda ids: ids.measurement_ids[1],
        lambda fixture, ids: fixture.application.get_measurement(
            MeasurementId(ids.measurement_ids[1])
        ),
        "evaluation_scope=CAST(:material AS jsonb)",
        {"material": '{"corrupt":true}'},
        False,
    ),
    CorruptionOwner(
        "StatisticalResult",
        "statistical_results",
        lambda ids: ids.statistical_result_id,
        lambda fixture, ids: fixture.application.get_statistical_result(
            StatisticalResultId(ids.statistical_result_id)
        ),
        "result_payload=CAST(:material AS jsonb)",
        {"material": '{"corrupt":true}'},
        False,
    ),
    CorruptionOwner(
        "ClaimVersion",
        "claim_versions",
        lambda ids: ids.claim_version_id,
        lambda fixture, ids: fixture.application.get_claim_version(
            ClaimVersionId(ids.claim_version_id)
        ),
        "statement=:material",
        {"material": "corrupt claim"},
        False,
    ),
    CorruptionOwner(
        "ImpactAssessment",
        "impact_assessments",
        lambda ids: ids.impact_assessment_id,
        lambda fixture, ids: fixture.governance_queries.get_impact_assessment(
            ids.impact_assessment_id
        ),
        "assessment_payload=CAST(:material AS jsonb)",
        {"material": '{"corrupt":true}'},
        False,
    ),
    CorruptionOwner(
        "CorrectionRecord",
        "correction_records",
        lambda ids: ids.correction_id,
        lambda fixture, ids: fixture.governance_queries.get_correction_record(ids.correction_id),
        "corrected_assertion=CAST(:material AS jsonb)",
        {"material": '{"corrupt":true}'},
        False,
    ),
)


@pytest.fixture(scope="module")
def corruption_workflow(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[tuple[WorkflowFixture, WorkflowIds]]:
    path = tmp_path_factory.mktemp("p1-fcr4-corruption")
    with fresh_fixture(path, "p1-fcr4-corruption") as fixture:
        ids = run_workflow(fixture, "application")
        structured = fixture.application.record_measurement(
            RecordMeasurementCommand(
                RunId(ids.run_id),
                MetricDefinitionVersionId(ids.metric_definition_version_id),
                None,
                {"nested": {"items": [1, 2]}},
                None,
                {"split": "corruption-matrix"},
                fixture.context,
            )
        )
        yield fixture, replace(ids, measurement_ids=(ids.measurement_ids[0], structured.id))


def corrupt_and_restore(
    engine: Engine,
    owner: CorruptionOwner,
    object_id: object,
    assignment: str,
    parameters: dict[str, object],
    action: Callable[[], object],
) -> None:
    column = assignment.split("=", 1)[0].strip()
    with engine.connect() as connection:
        original = connection.execute(
            text(f"SELECT {column} FROM {owner.table} WHERE id=:id"), {"id": object_id}
        ).scalar_one()
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(f"ALTER TABLE {owner.table} DISABLE TRIGGER USER")
            connection.execute(
                text(f"UPDATE {owner.table} SET {assignment} WHERE id=:id"),
                {"id": object_id, **parameters},
            )
            connection.exec_driver_sql(f"ALTER TABLE {owner.table} ENABLE TRIGGER USER")
        with pytest.raises(ResearchBaseError) as error:
            action()
        assert error.value.code is ErrorCode.REFERENTIAL_INTEGRITY_ERROR
    finally:
        is_json = isinstance(original, dict | list)
        restore = f"{column}=CAST(:original AS jsonb)" if is_json else f"{column}=:original"
        restored = json.dumps(original) if is_json else original
        with engine.begin() as connection:
            connection.exec_driver_sql(f"ALTER TABLE {owner.table} DISABLE TRIGGER USER")
            connection.execute(
                text(f"UPDATE {owner.table} SET {restore} WHERE id=:id"),
                {"id": object_id, "original": restored},
            )
            connection.exec_driver_sql(f"ALTER TABLE {owner.table} ENABLE TRIGGER USER")


@pytest.mark.parametrize("owner", OWNERS, ids=lambda owner: owner.name)
def test_wrong_valid_shape_content_hash_fails_closed(
    corruption_workflow: tuple[WorkflowFixture, WorkflowIds], owner: CorruptionOwner
) -> None:
    fixture, ids = corruption_workflow
    corrupt_and_restore(
        fixture.engine,
        owner,
        owner.id_getter(ids),
        "content_hash=:wrong_hash",
        {"wrong_hash": "f" * 64},
        lambda: owner.reader(fixture, ids),
    )


@pytest.mark.parametrize("owner", OWNERS, ids=lambda owner: owner.name)
def test_stale_content_hash_after_material_change_fails_closed(
    corruption_workflow: tuple[WorkflowFixture, WorkflowIds], owner: CorruptionOwner
) -> None:
    fixture, ids = corruption_workflow
    corrupt_and_restore(
        fixture.engine,
        owner,
        owner.id_getter(ids),
        owner.material_assignment,
        owner.material_parameters,
        lambda: owner.reader(fixture, ids),
    )


def test_persisted_hash_scheme_vector_is_not_applicable() -> None:
    assert all(not owner.has_hash_scheme for owner in OWNERS)


def test_structured_owner_registry_is_exact() -> None:
    assert len(OWNERS) == 10
    assert sum(owner.has_hash_scheme for owner in OWNERS) == 0


def binding_corruption_fails_closed(
    engine: Engine,
    table: str,
    column: str,
    where: str,
    parameters: dict[str, object],
    action: Callable[[], object],
) -> None:
    with engine.connect() as connection:
        original = connection.execute(
            text(f"SELECT {column} FROM {table} WHERE {where}"), parameters
        ).scalar_one()
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(f"ALTER TABLE {table} DISABLE TRIGGER USER")
            connection.execute(
                text(f"UPDATE {table} SET {column}=:wrong_hash WHERE {where}"),
                {**parameters, "wrong_hash": "f" * 64},
            )
            connection.exec_driver_sql(f"ALTER TABLE {table} ENABLE TRIGGER USER")
        with pytest.raises(ResearchBaseError) as error:
            action()
        assert error.value.code is ErrorCode.REFERENTIAL_INTEGRITY_ERROR
    finally:
        with engine.begin() as connection:
            connection.exec_driver_sql(f"ALTER TABLE {table} DISABLE TRIGGER USER")
            connection.execute(
                text(f"UPDATE {table} SET {column}=:original WHERE {where}"),
                {**parameters, "original": original},
            )
            connection.exec_driver_sql(f"ALTER TABLE {table} ENABLE TRIGGER USER")


def test_claim_support_set_binding_mismatch_fails_closed(
    corruption_workflow: tuple[WorkflowFixture, WorkflowIds],
) -> None:
    fixture, ids = corruption_workflow
    binding_corruption_fails_closed(
        fixture.engine,
        "claim_versions",
        "support_set_hash",
        "id=:id",
        {"id": ids.claim_version_id},
        lambda: fixture.application.get_claim_version(ClaimVersionId(ids.claim_version_id)),
    )


def test_audit_finding_target_binding_mismatch_fails_closed(
    corruption_workflow: tuple[WorkflowFixture, WorkflowIds],
) -> None:
    fixture, ids = corruption_workflow
    binding_corruption_fails_closed(
        fixture.engine,
        "audit_findings",
        "target_content_hash",
        "id=:id",
        {"id": ids.finding_id},
        lambda: fixture.governance_queries.get_audit_finding(ids.finding_id),
    )


def test_impact_target_binding_mismatch_fails_closed(
    corruption_workflow: tuple[WorkflowFixture, WorkflowIds],
) -> None:
    fixture, ids = corruption_workflow
    with fixture.engine.connect() as connection:
        target_id = connection.execute(
            text(
                "SELECT target_id FROM impact_targets "
                "WHERE impact_assessment_id=:assessment_id ORDER BY target_id LIMIT 1"
            ),
            {"assessment_id": ids.impact_assessment_id},
        ).scalar_one()
    binding_corruption_fails_closed(
        fixture.engine,
        "impact_targets",
        "target_content_hash",
        "impact_assessment_id=:assessment_id AND target_id=:target_id",
        {"assessment_id": ids.impact_assessment_id, "target_id": target_id},
        lambda: fixture.governance_queries.get_impact_assessment(ids.impact_assessment_id),
    )


def test_correction_target_binding_mismatch_fails_closed(
    corruption_workflow: tuple[WorkflowFixture, WorkflowIds],
) -> None:
    fixture, ids = corruption_workflow
    binding_corruption_fails_closed(
        fixture.engine,
        "correction_records",
        "target_content_hash",
        "id=:id",
        {"id": ids.correction_id},
        lambda: fixture.governance_queries.get_correction_record(ids.correction_id),
    )


def test_dataset_manifest_identity_mismatch_fails_closed(
    corruption_workflow: tuple[WorkflowFixture, WorkflowIds],
) -> None:
    fixture, ids = corruption_workflow
    binding_corruption_fails_closed(
        fixture.engine,
        "dataset_snapshots",
        "manifest_hash",
        "id=:id",
        {"id": ids.dataset_snapshot_id},
        lambda: fixture.application.get_dataset_snapshot(
            DatasetSnapshotId(ids.dataset_snapshot_id)
        ),
    )


def additional_surface(
    owner: CorruptionOwner, fixture: WorkflowFixture, ids: WorkflowIds
) -> object:
    readers: dict[str, Callable[[], object]] = {
        "ResearchQuestionVersion": lambda: fixture.application.get_research_question_history(
            ResearchQuestionId(ids.research_question_id)
        ),
        "HypothesisVersion": lambda: fixture.application.get_hypothesis_history(
            HypothesisId(ids.hypothesis_id)
        ),
        "ExperimentSpecVersion": lambda: fixture.application.get_experiment_spec_history(
            ExperimentSpecId(ids.experiment_spec_id)
        ),
        "DatasetSnapshot": lambda: fixture.application.get_dataset_snapshot(
            DatasetSnapshotId(ids.dataset_snapshot_id)
        ),
        "MetricDefinitionVersion": lambda: fixture.application.get_metric_definition_history(
            MetricDefinitionId(ids.metric_definition_id)
        ),
        "Measurement": lambda: fixture.application.list_measurements_for_run(RunId(ids.run_id)),
        "StatisticalResult": lambda: fixture.application.list_statistical_results_for_project(
            ProjectId(ids.project_id)
        ),
        "ClaimVersion": lambda: fixture.application.get_current_claim_version(
            ClaimId(ids.claim_id)
        ),
        "ImpactAssessment": lambda: fixture.governance_queries.list_impact_assessments(
            ids.finding_id
        ),
        "CorrectionRecord": lambda: fixture.governance_queries.list_correction_records(
            ids.project_id,
            GovernanceTargetType.MEASUREMENT,
            ids.measurement_ids[0],
        ),
    }
    return readers[owner.name]()


@pytest.mark.parametrize("owner", OWNERS, ids=lambda owner: owner.name)
def test_wrong_hash_fails_closed_on_each_available_collection_or_current_surface(
    corruption_workflow: tuple[WorkflowFixture, WorkflowIds], owner: CorruptionOwner
) -> None:
    fixture, ids = corruption_workflow
    corrupt_and_restore(
        fixture.engine,
        owner,
        owner.id_getter(ids),
        "content_hash=:wrong_hash",
        {"wrong_hash": "e" * 64},
        lambda: additional_surface(owner, fixture, ids),
    )


def test_claim_corruption_fails_provenance_query_and_closure(
    corruption_workflow: tuple[WorkflowFixture, WorkflowIds],
) -> None:
    fixture, ids = corruption_workflow
    for action in (
        lambda: fixture.provenance.get_claim_closure_report(ids.claim_version_id),
        lambda: fixture.provenance.trace_claim_to_runs(ids.claim_version_id),
    ):
        corrupt_and_restore(
            fixture.engine,
            next(owner for owner in OWNERS if owner.name == "ClaimVersion"),
            ids.claim_version_id,
            "content_hash=:wrong_hash",
            {"wrong_hash": "d" * 64},
            action,
        )


def test_corrupt_measurement_fails_downstream_impact(
    corruption_workflow: tuple[WorkflowFixture, WorkflowIds],
) -> None:
    fixture, ids = corruption_workflow
    owner = next(owner for owner in OWNERS if owner.name == "Measurement")
    corrupt_and_restore(
        fixture.engine,
        owner,
        ids.measurement_ids[0],
        "content_hash=:wrong_hash",
        {"wrong_hash": "c" * 64},
        lambda: fixture.governance_queries.downstream_impact(
            ids.project_id, GovernanceTargetType.MEASUREMENT, ids.measurement_ids[0]
        ),
    )


def test_impact_target_binding_is_checked_after_valid_own_hash_reconstruction(
    corruption_workflow: tuple[WorkflowFixture, WorkflowIds],
) -> None:
    fixture, ids = corruption_workflow
    with fixture.engine.connect() as connection:
        assessment = (
            connection.execute(
                text("SELECT * FROM impact_assessments WHERE id=:id"),
                {"id": ids.impact_assessment_id},
            )
            .mappings()
            .one()
        )
        target_rows = (
            connection.execute(
                text(
                    "SELECT * FROM impact_targets WHERE impact_assessment_id=:id "
                    "ORDER BY target_type,target_id"
                ),
                {"id": ids.impact_assessment_id},
            )
            .mappings()
            .all()
        )
    chosen = next(row for row in target_rows if str(row["target_type"]).lower() == "measurement")
    tampered_targets = [
        {
            "target_type": str(row["target_type"]).lower(),
            "target_id": str(row["target_id"]),
            "target_content_hash": (
                "f" * 64 if row["target_id"] == chosen["target_id"] else row["target_content_hash"]
            ),
            "impact_kind": str(row["impact_kind"]).lower(),
        }
        for row in target_rows
    ]
    tampered_hash = impact_assessment_hash(
        project_id=str(assessment["project_id"]),
        audit_finding_id=str(assessment["audit_finding_id"]),
        assessment_payload=assessment["assessment_payload"],
        conclusion=str(assessment["conclusion"]).lower(),
        targets=tampered_targets,
    )
    try:
        with fixture.engine.begin() as connection:
            connection.exec_driver_sql("ALTER TABLE impact_targets DISABLE TRIGGER USER")
            connection.exec_driver_sql("ALTER TABLE impact_assessments DISABLE TRIGGER USER")
            connection.execute(
                text(
                    "UPDATE impact_targets SET target_content_hash=:wrong "
                    "WHERE impact_assessment_id=:id AND target_id=:target_id"
                ),
                {
                    "wrong": "f" * 64,
                    "id": ids.impact_assessment_id,
                    "target_id": chosen["target_id"],
                },
            )
            connection.execute(
                text("UPDATE impact_assessments SET content_hash=:hash WHERE id=:id"),
                {"hash": tampered_hash, "id": ids.impact_assessment_id},
            )
            connection.exec_driver_sql("ALTER TABLE impact_assessments ENABLE TRIGGER USER")
            connection.exec_driver_sql("ALTER TABLE impact_targets ENABLE TRIGGER USER")
        with pytest.raises(ResearchBaseError) as error:
            fixture.governance_queries.get_impact_assessment(ids.impact_assessment_id)
        assert error.value.code is ErrorCode.REFERENTIAL_INTEGRITY_ERROR
    finally:
        with fixture.engine.begin() as connection:
            connection.exec_driver_sql("ALTER TABLE impact_targets DISABLE TRIGGER USER")
            connection.exec_driver_sql("ALTER TABLE impact_assessments DISABLE TRIGGER USER")
            connection.execute(
                text(
                    "UPDATE impact_targets SET target_content_hash=:original "
                    "WHERE impact_assessment_id=:id AND target_id=:target_id"
                ),
                {
                    "original": chosen["target_content_hash"],
                    "id": ids.impact_assessment_id,
                    "target_id": chosen["target_id"],
                },
            )
            connection.execute(
                text("UPDATE impact_assessments SET content_hash=:hash WHERE id=:id"),
                {"hash": assessment["content_hash"], "id": ids.impact_assessment_id},
            )
            connection.exec_driver_sql("ALTER TABLE impact_assessments ENABLE TRIGGER USER")
            connection.exec_driver_sql("ALTER TABLE impact_targets ENABLE TRIGGER USER")


def test_correction_binding_is_checked_after_valid_own_hash_reconstruction(
    corruption_workflow: tuple[WorkflowFixture, WorkflowIds],
) -> None:
    fixture, ids = corruption_workflow
    with fixture.engine.connect() as connection:
        row = (
            connection.execute(
                text("SELECT * FROM correction_records WHERE id=:id"), {"id": ids.correction_id}
            )
            .mappings()
            .one()
        )
    tampered_hash = correction_record_hash(
        project_id=str(row["project_id"]),
        target_type=str(row["target_type"]).lower(),
        target_id=str(row["target_id"]),
        target_content_hash="f" * 64,
        correction_type=str(row["correction_type"]).lower(),
        corrected_assertion=row["corrected_assertion"],
        reason=row["reason"],
    )
    try:
        with fixture.engine.begin() as connection:
            connection.exec_driver_sql("ALTER TABLE correction_records DISABLE TRIGGER USER")
            connection.execute(
                text(
                    "UPDATE correction_records SET target_content_hash=:wrong,content_hash=:hash "
                    "WHERE id=:id"
                ),
                {"wrong": "f" * 64, "hash": tampered_hash, "id": ids.correction_id},
            )
            connection.exec_driver_sql("ALTER TABLE correction_records ENABLE TRIGGER USER")
        with pytest.raises(ResearchBaseError) as error:
            fixture.governance_queries.get_correction_record(ids.correction_id)
        assert error.value.code is ErrorCode.REFERENTIAL_INTEGRITY_ERROR
    finally:
        with fixture.engine.begin() as connection:
            connection.exec_driver_sql("ALTER TABLE correction_records DISABLE TRIGGER USER")
            connection.execute(
                text(
                    "UPDATE correction_records SET target_content_hash=:target_hash,"
                    "content_hash=:content_hash WHERE id=:id"
                ),
                {
                    "target_hash": row["target_content_hash"],
                    "content_hash": row["content_hash"],
                    "id": ids.correction_id,
                },
            )
            connection.exec_driver_sql("ALTER TABLE correction_records ENABLE TRIGGER USER")
