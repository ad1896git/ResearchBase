"""PR-17 historical exactness and governance propagation acceptance."""

# pyright: reportArgumentType=false, reportIndexIssue=false

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import text
from tests.e2e.support import fresh_fixture, projection, refresh_application_queries, run_workflow

from researchbase.application.commands import (
    AttachRunArtifactInputCommand,
    AttachRunDatasetInputCommand,
    CreateArtifactVersionCommand,
    CreateDatasetSnapshotCommand,
    CreateRunCommand,
    FinishRunCommand,
    FreezeArtifactVersionCommand,
    FreezeExperimentSpecCommand,
    FreezeMetricDefinitionCommand,
    FreezeResearchQuestionCommand,
    RecordMeasurementCommand,
    RecordStatisticalResultCommand,
    ReviseExperimentSpecCommand,
    ReviseMetricDefinitionCommand,
    ReviseResearchQuestionCommand,
    StartRunCommand,
    StatisticalResultInputCommand,
)
from researchbase.application.governance import (
    TransitionAuditFindingCommand,
)
from researchbase.domain.governance import (
    AuditFindingStatus,
    GovernanceTargetType,
    ImpactAssessmentConclusion,
)
from researchbase.domain.run import ArtifactInputRole, DatasetInputRole, RunStatus
from researchbase.foundation.errors import ErrorCode

pytestmark = [pytest.mark.integration, pytest.mark.phase1_golden]


def _original_rows(fixture: object, ids: object) -> dict[str, tuple[object, ...]]:
    # This test intentionally uses the public Application read models only.  The
    # broad object annotations keep this helper independent of the test fixture's
    # dataclass implementation details.
    fixture_value = fixture  # narrow through the known test support surface below
    ids_value = ids
    app = fixture_value.fresh_application()  # type: ignore[attr-defined]
    run = app.get_run(ids_value.run_id)  # type: ignore[attr-defined]
    run_dataset_inputs = app.list_run_dataset_inputs(ids_value.run_id)  # type: ignore[attr-defined]
    run_artifact_inputs = app.list_run_artifact_inputs(ids_value.run_id)  # type: ignore[attr-defined]
    measurements = [app.get_measurement(item) for item in ids_value.measurement_ids]  # type: ignore[attr-defined]
    statistical = app.get_statistical_result(ids_value.statistical_result_id)  # type: ignore[attr-defined]
    statistical_inputs = app.list_statistical_result_inputs(ids_value.statistical_result_id)  # type: ignore[attr-defined]
    claim = app.get_claim_version(ids_value.claim_version_id)  # type: ignore[attr-defined]
    evidence = app.list_evidence_relations(ids_value.claim_version_id)  # type: ignore[attr-defined]
    dataset = app.get_dataset_snapshot(ids_value.dataset_snapshot_id)  # type: ignore[attr-defined]
    artifact = app.get_artifact_version(ids_value.artifact_version_id)  # type: ignore[attr-defined]
    metric = app.get_metric_definition_version(ids_value.metric_definition_version_id)  # type: ignore[attr-defined]
    specs = app.get_experiment_spec_history(ids_value.experiment_spec_id)  # type: ignore[attr-defined]
    questions = app.get_research_question_history(ids_value.research_question_id)  # type: ignore[attr-defined]
    original_spec = next(
        item
        for item in specs
        if item.id == ids_value.experiment_spec_version_id  # type: ignore[attr-defined]
    )
    return {
        "run": (
            run.id,
            run.status,
            run.run_type,
            run.experiment_spec_version_id,
            run.inputs_sealed_at,
            run.started_at,
            run.finished_at,
            run.exit_code,
            run.failure_reason,
            tuple(
                (item.run_id, item.dataset_snapshot_id, item.role, item.ordinal)
                for item in run_dataset_inputs
            ),
            tuple(
                (item.run_id, item.artifact_version_id, item.role, item.ordinal)
                for item in run_artifact_inputs
            ),
        ),
        "measurements": tuple(
            (
                item.id,
                item.run_id,
                item.metric_definition_version_id,
                item.numeric_value,
                item.structured_value,
                item.unit,
                item.evaluation_scope,
                item.content_hash,
            )
            for item in measurements
        ),
        "statistical": (
            statistical.id,
            statistical.analysis_type,
            statistical.result_payload,
            statistical.analysis_definition,
            statistical.content_hash,
            tuple(
                (item.statistical_result_id, item.measurement_id, item.input_role, item.ordinal)
                for item in statistical_inputs
            ),
        ),
        "claim": (
            claim.id,
            claim.claim_id,
            claim.version_number,
            claim.statement,
            claim.scope,
            claim.qualification,
            claim.status,
            claim.support_set_hash,
            claim.content_hash,
        ),
        "evidence": tuple(
            (
                item.id,
                item.claim_version_id,
                item.measurement_id,
                item.statistical_result_id,
                item.relation_type,
                item.qualification,
            )
            for item in evidence
        ),
        "dataset": (
            dataset.id,
            dataset.dataset_id,
            dataset.manifest_hash,
            dataset.selection_definition,
            dataset.manifest_locator,
            dataset.content_hash,
        ),
        "artifact": (
            artifact.id,
            artifact.artifact_id,
            artifact.version_number,
            artifact.content_hash,
            artifact.locator,
            artifact.media_type,
            artifact.byte_size,
            artifact.metadata,
        ),
        "metric": (
            metric.id,
            metric.metric_definition_id,
            metric.version_number,
            metric.definition,
            metric.unit,
            metric.aggregation,
            metric.content_hash,
        ),
        "experiment_spec_version": (
            original_spec.id,
            original_spec.experiment_spec_id,
            original_spec.version_number,
            original_spec.content_hash,
            original_spec.title,
            original_spec.objective,
            original_spec.protocol,
            original_spec.planned_metrics,
            original_spec.seed_policy,
            original_spec.analysis_plan,
        ),
        "spec": tuple(
            (
                item.id,
                item.experiment_spec_id,
                item.version_number,
                item.content_hash,
                item.title,
                item.objective,
                item.protocol,
                item.planned_metrics,
                item.seed_policy,
                item.analysis_plan,
            )
            for item in specs
        ),
        "question": tuple(
            (item.id, item.content_hash, item.question_text, item.created_at) for item in questions
        ),
    }


def test_historical_advancement_preserves_original_exact_ids_hashes_and_closure(
    tmp_path: Path,
) -> None:
    with fresh_fixture(tmp_path, "gsas-history") as fixture:
        ids = run_workflow(fixture, "application")
        before = _original_rows(fixture, ids)
        before_queries = dict(ids.observed_queries)
        before_projection = projection(fixture, ids)
        app = fixture.fresh_application()
        context = fixture.context

        question = app.get_research_question(ids.research_question_id)
        revised_question = app.revise_research_question(
            ReviseResearchQuestionCommand(
                ids.research_question_id,
                "Does the revised protocol improve latency?",
                {"population": "test", "cohort": "later"},
                "GSAS historical revision",
                question.row_version,
                context,
            )
        )
        app.freeze_research_question(
            FreezeResearchQuestionCommand(
                ids.research_question_id,
                revised_question.current_version_id,
                context,
                1,
            )
        )

        spec = app.get_experiment_spec(ids.experiment_spec_id)
        revised_spec = app.revise_experiment_spec(
            ReviseExperimentSpecCommand(
                ids.experiment_spec_id,
                "Latency experiment v2",
                "Measure latency in a later cohort",
                {"steps": ["run", "measure", "compare"]},
                [{"metric": "latency"}],
                {"seed": 8},
                {"test": "mean", "cohort": "later"},
                spec.row_version,
                context,
            )
        )
        app.freeze_experiment_spec(
            FreezeExperimentSpecCommand(
                ids.experiment_spec_id,
                revised_spec.current_version_id,
                context,
                1,
            )
        )

        snapshot = app.create_dataset_snapshot(
            CreateDatasetSnapshotCommand(
                ids.dataset_id,
                "b" * 64,
                {"split": "test", "rows": [3, 4]},
                "cas://manifest-v2",
                context,
            )
        )
        artifact = app.create_artifact_version(
            CreateArtifactVersionCommand(
                ids.artifact_id,
                b"gsas-source-v2",
                None,
                None,
                "text/plain",
                None,
                {"language": "python", "revision": 2},
                context,
            )
        )
        artifact = app.freeze_artifact_version(
            FreezeArtifactVersionCommand(
                ids.artifact_id,
                artifact.id,
                context,
                artifact.row_version,
            )
        )
        metric = app.get_metric_definition(ids.metric_definition_id)
        revised_metric = app.revise_metric_definition(
            ReviseMetricDefinitionCommand(
                ids.metric_definition_id,
                {"kind": "median", "unit": "ms"},
                "ms",
                "median",
                metric.row_version,
                context,
            )
        )
        app.freeze_metric_definition(
            FreezeMetricDefinitionCommand(
                ids.metric_definition_id,
                revised_metric.current_version_id,
                context,
                1,
            )
        )

        later_run = app.create_run(
            CreateRunCommand(
                ids.project_id,
                revised_spec.current_version_id,
                "golden-later",
                context,
            )
        )
        later_run = app.attach_run_dataset_input(
            AttachRunDatasetInputCommand(
                later_run.id,
                snapshot.id,
                DatasetInputRole.TEST,
                0,
                later_run.row_version,
                context,
            )
        )
        later_run = app.attach_run_artifact_input(
            AttachRunArtifactInputCommand(
                later_run.id,
                artifact.id,
                ArtifactInputRole.SOURCE_CODE,
                0,
                later_run.row_version,
                context,
            )
        )
        later_run = app.start_run(StartRunCommand(later_run.id, later_run.row_version, context))
        later_run = app.finish_run(
            FinishRunCommand(
                later_run.id,
                RunStatus.SUCCEEDED,
                0,
                None,
                later_run.row_version,
                context,
            )
        )
        later_measurement = app.record_measurement(
            RecordMeasurementCommand(
                later_run.id,
                revised_metric.current_version_id,
                2.25,
                None,
                "ms",
                {"split": "test", "ordinal": 0, "cohort": "later"},
                context,
            )
        )
        app.record_statistical_result(
            RecordStatisticalResultCommand(
                ids.project_id,
                "median",
                {"median": 2.25},
                {"method": "median"},
                (StatisticalResultInputCommand(later_measurement.id, "later", 0),),
                context,
            )
        )

        after = _original_rows(fixture, ids)
        refreshed_ids = refresh_application_queries(fixture, ids)
        after_queries = dict(refreshed_ids.observed_queries)
        after_projection = projection(fixture, refreshed_ids)

    assert before_projection == after_projection
    for query_name in ("run:provenance", "claim:trace", "fresh:claim_closure", "impact:show"):
        assert after_queries[query_name] == before_queries[query_name]
    assert before["run"] == after["run"]
    assert before["measurements"] == after["measurements"]
    assert before["statistical"] == after["statistical"]
    assert before["claim"] == after["claim"]
    assert before["evidence"] == after["evidence"]
    assert before["dataset"] == after["dataset"]
    assert before["artifact"] == after["artifact"]
    assert before["metric"] == after["metric"]
    assert before["experiment_spec_version"] == after["experiment_spec_version"]
    assert [row[0] for row in after["spec"][:-1]] == [row[0] for row in before["spec"]]
    assert [row[0] for row in after["question"][:-1]] == [row[0] for row in before["question"]]
    assert after_projection["inputs"]["experiment_spec_version"] == str(
        ids.experiment_spec_version_id
    )
    assert after_projection["inputs"]["dataset_inputs"][0]["target_id"] == str(
        ids.dataset_snapshot_id
    )
    assert after_projection["inputs"]["artifact_inputs"][0]["target_id"] == str(
        ids.artifact_version_id
    )
    assert after_projection["inputs"]["metric_definition_version"] == str(
        ids.metric_definition_version_id
    )


def test_closure_negative_cases_are_deterministic_and_positive_closure_has_no_violations(
    tmp_path: Path,
) -> None:
    with fresh_fixture(tmp_path, "gsas-closure") as fixture:
        ids = run_workflow(fixture, "application")
        valid_run = fixture.provenance.get_run_provenance(ids.run_id)
        valid_claim = fixture.provenance.get_claim_closure_report(ids.claim_version_id)
        assert valid_run.closure.complete is True
        assert valid_claim.complete is True

        missing_run = fixture.provenance._validator.validate_run(UUID(int=0))  # noqa: SLF001
        missing_claim = fixture.provenance._validator.validate_claim_version(  # noqa: SLF001
            UUID(int=0)
        )
        missing_run_again = fixture.provenance._validator.validate_run(UUID(int=0))  # noqa: SLF001

    assert missing_run.complete is False
    assert missing_run.visited_count == 0
    assert [(item.code, item.path, item.object_type) for item in missing_run.violations] == [
        (ErrorCode.NOT_FOUND.value, ["run"], "Run")
    ]
    assert missing_claim.complete is False
    assert missing_claim.visited_count == 0
    assert [(item.code, item.path, item.object_type) for item in missing_claim.violations] == [
        (ErrorCode.NOT_FOUND.value, ["claim_version"], "ClaimVersion")
    ]
    assert missing_run_again == missing_run


def test_claim_closure_reports_a_real_broken_descendant_deterministically(
    tmp_path: Path,
) -> None:
    with fresh_fixture(tmp_path, "gsas-broken-descendant") as fixture:
        ids = run_workflow(fixture, "application")
        valid = fixture.provenance.get_claim_closure_report(ids.claim_version_id)
        assert valid.complete is True

        with fixture.engine.begin() as connection:
            connection.execute(text("ALTER TABLE metric_definition_versions DISABLE TRIGGER ALL"))
            try:
                connection.execute(
                    text(
                        "UPDATE metric_definition_versions "
                        "SET status = 'DRAFT' "
                        "WHERE id = :metric_version_id"
                    ),
                    {
                        "metric_version_id": ids.metric_definition_version_id,
                    },
                )
            finally:
                connection.execute(
                    text("ALTER TABLE metric_definition_versions ENABLE TRIGGER ALL")
                )

        reports = [
            fixture.provenance.get_claim_closure_report(ids.claim_version_id) for _ in range(3)
        ]

    signatures = [
        [
            (item.code, item.object_type, item.object_id, item.path, item.message)
            for item in report.violations
        ]
        for report in reports
    ]
    assert all(report.complete is False for report in reports)
    assert signatures[0] == signatures[1] == signatures[2]
    expected_paths = [
        (
            "claim_version",
            "evidence",
            str(ids.evidence_relation_ids[1]),
            "statistical_result",
            "inputs",
            str(ids.measurement_ids[0]),
            "measurement",
            "metric_definition_version",
            "status",
        ),
        (
            "claim_version",
            "evidence",
            str(ids.evidence_relation_ids[1]),
            "statistical_result",
            "inputs",
            str(ids.measurement_ids[1]),
            "measurement",
            "metric_definition_version",
            "status",
        ),
        (
            "claim_version",
            "evidence",
            str(ids.evidence_relation_ids[0]),
            "measurement",
            "metric_definition_version",
            "status",
        ),
    ]
    assert [item[3] for item in signatures[0]] == expected_paths
    assert [item[:3] + item[4:] for item in signatures[0]] == [
        (
            ErrorCode.VERSION_NOT_FROZEN.value,
            "MetricDefinitionVersion",
            str(ids.metric_definition_version_id),
            "metric definition version is not finalized",
        )
    ] * 3
    assert all(report.visited_count == reports[0].visited_count for report in reports)
    assert reports[0].visited_count == 14


def test_governance_validity_precedence_dismissal_and_correction_are_non_mutating(
    tmp_path: Path,
) -> None:
    with fresh_fixture(tmp_path, "gsas-governance") as fixture:
        ids = run_workflow(fixture, "application")
        app = fixture.fresh_application()
        before_measurement = app.get_measurement(ids.measurement_ids[0])
        before_statistical = app.get_statistical_result(ids.statistical_result_id)
        finding = fixture.governance_queries.get_audit_finding(ids.finding_id)
        assert finding is not None
        assert finding.target_type is GovernanceTargetType.RUN
        assert finding.target_id == ids.run_id
        assessment = fixture.governance_queries.get_impact_assessment(ids.impact_assessment_id)
        assert assessment is not None
        assert assessment.conclusion is ImpactAssessmentConclusion.INVALID
        impact = fixture.governance_queries.downstream_impact(
            ids.project_id, GovernanceTargetType.RUN, ids.run_id
        )
        claim_target = next(item for item in impact if item.target_id == ids.claim_version_id)
        assert len(claim_target.paths) == 3
        assert {item.statistical_result_id for item in claim_target.paths} == {
            None,
            ids.statistical_result_id,
        }
        assert {item.statistical_input_role for item in claim_target.paths} == {
            None,
            "primary",
            "replicate",
        }

        transitioned = fixture.governance.transition_audit_finding(
            TransitionAuditFindingCommand(
                ids.finding_id,
                AuditFindingStatus.DISMISSED,
                finding.row_version,
                fixture.context,
            )
        )
        validity = fixture.governance_queries.validity_projection(
            ids.project_id, GovernanceTargetType.RUN, ids.run_id
        )
        correction = fixture.governance_queries.get_correction_record(ids.correction_id)
        assert transitioned.status is AuditFindingStatus.DISMISSED
        assert validity.state.value == "not_assessed"
        assert correction is not None
        assert correction.target_id == ids.measurement_ids[0]
        after_measurement = app.get_measurement(ids.measurement_ids[0])
        after_statistical = app.get_statistical_result(ids.statistical_result_id)

    assert before_measurement.content_hash == after_measurement.content_hash
    assert before_statistical.content_hash == after_statistical.content_hash
