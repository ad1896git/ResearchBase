"""PR-17 PostgreSQL atomicity and independent-UoW concurrency acceptance."""

# pyright: reportArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from sqlalchemy import text
from tests.e2e.support import FIXED_NOW, fresh_fixture, run_workflow

from researchbase.application.commands import (
    ApplicationService,
    AttachRunArtifactInputCommand,
    AttachRunDatasetInputCommand,
    CreateClaimCommand,
    CreateRunCommand,
    FreezeClaimVersionCommand,
    LinkEvidenceCommand,
    RecordStatisticalResultCommand,
    ReviseResearchQuestionCommand,
    StartRunCommand,
    StatisticalResultInputCommand,
)
from researchbase.application.governance import (
    CreateImpactAssessmentCommand,
    GovernanceService,
    ProposedImpactTarget,
    TransitionAuditFindingCommand,
)
from researchbase.domain.claim import EvidenceRelationType
from researchbase.domain.governance import (
    AuditFindingStatus,
    GovernanceTargetType,
    ImpactAssessmentConclusion,
    ImpactKind,
)
from researchbase.domain.run import ArtifactInputRole, DatasetInputRole
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.time import FixedClock
from researchbase.persistence.database import create_session_factory
from researchbase.persistence.uow import SqlAlchemyUnitOfWork

pytestmark = [pytest.mark.integration, pytest.mark.phase1_golden]


class _FailingUnitOfWork(SqlAlchemyUnitOfWork):
    def commit(self) -> None:
        self._require_session().flush()
        raise RuntimeError("controlled PR-17 rollback")


def _failing_application(fixture: object) -> ApplicationService:
    sessions = create_session_factory(fixture.engine)  # type: ignore[attr-defined]
    return ApplicationService(
        lambda: _FailingUnitOfWork(sessions),
        FixedClock(FIXED_NOW),
        fixture.application._artifact_store,  # noqa: SLF001 - accepted test composition seam
    )  # type: ignore[attr-defined]


def _failing_governance(fixture: object) -> GovernanceService:
    sessions = create_session_factory(fixture.engine)  # type: ignore[attr-defined]
    return GovernanceService(
        lambda: _FailingUnitOfWork(sessions),
        FixedClock(FIXED_NOW),
    )


def _count(fixture: object, table: str) -> int:
    with fixture.engine.connect() as connection:  # type: ignore[attr-defined]
        return int(connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())


def _race(callable_one: Callable[[], object], callable_two: Callable[[], object]) -> list[object]:
    barrier = threading.Barrier(2)

    def invoke(target: Callable[[], object]) -> object:
        barrier.wait(timeout=10)
        try:
            return target()
        except BaseException as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(invoke, callable_one), executor.submit(invoke, callable_two)]
        return [future.result(timeout=20) for future in futures]


def test_representative_commands_rollback_and_retry_without_partial_rows(tmp_path: Path) -> None:
    with fresh_fixture(tmp_path, "gsas-atomicity") as fixture:
        ids = run_workflow(fixture, "application")
        app = fixture.fresh_application()
        context = fixture.context

        result_command = RecordStatisticalResultCommand(
            ids.project_id,
            "mean-retry",
            {"mean": 1.5},
            {"method": "arithmetic"},
            (
                StatisticalResultInputCommand(ids.measurement_ids[0], "primary", 0),
                StatisticalResultInputCommand(ids.measurement_ids[1], "replicate", 1),
            ),
            context,
        )
        result_count = _count(fixture, "statistical_results")
        input_count = _count(fixture, "statistical_result_inputs")
        with pytest.raises(RuntimeError, match="controlled PR-17 rollback"):
            _failing_application(fixture).record_statistical_result(result_command)
        assert _count(fixture, "statistical_results") == result_count
        assert _count(fixture, "statistical_result_inputs") == input_count
        retry_result = app.record_statistical_result(result_command)
        assert _count(fixture, "statistical_results") == result_count + 1
        assert _count(fixture, "statistical_result_inputs") == input_count + 2
        assert (
            app.list_statistical_result_inputs(retry_result.id)[0].measurement_id
            in ids.measurement_ids
        )

        claim = app.create_claim(
            CreateClaimCommand(
                ids.project_id, "atomic claim", {"population": "test"}, None, context
            )
        )
        version = app.get_current_claim_version(claim.id)
        link = LinkEvidenceCommand(
            claim.id,
            version.id,
            ids.measurement_ids[0],
            None,
            EvidenceRelationType.SUPPORTS,
            "atomic",
            version.row_version,
            context,
        )
        with pytest.raises(RuntimeError, match="controlled PR-17 rollback"):
            _failing_application(fixture).link_evidence(link)
        assert app.list_evidence_relations(version.id) == []
        assert app.get_claim_version(version.id).row_version == version.row_version
        app.link_evidence(link)
        frozen = app.freeze_claim_version(
            FreezeClaimVersionCommand(claim.id, version.id, context, version.row_version + 1)
        )
        assert frozen.status.value == "FROZEN"
        assert len(app.list_evidence_relations(version.id)) == 1

        assessments_before = len(fixture.governance_queries.list_impact_assessments(ids.finding_id))
        assessment_command = CreateImpactAssessmentCommand(
            ids.project_id,
            ids.finding_id,
            {"atomic": True},
            ImpactAssessmentConclusion.REQUIRES_REVIEW,
            (ProposedImpactTarget(GovernanceTargetType.RUN, ids.run_id, ImpactKind.DIRECT),),
            context,
        )
        with pytest.raises(RuntimeError, match="controlled PR-17 rollback"):
            _failing_governance(fixture).create_impact_assessment(assessment_command)
        assert (
            len(fixture.governance_queries.list_impact_assessments(ids.finding_id))
            == assessments_before
        )
        retry_assessment = fixture.governance.create_impact_assessment(assessment_command)
        assert retry_assessment.id is not None
        assert (
            len(fixture.governance_queries.list_impact_assessments(ids.finding_id))
            == assessments_before + 1
        )

        run_count = _count(fixture, "runs")
        run_command = CreateRunCommand(
            ids.project_id, ids.experiment_spec_version_id, "atomic-run", context
        )
        with pytest.raises(RuntimeError, match="controlled PR-17 rollback"):
            _failing_application(fixture).create_run(run_command)
        assert _count(fixture, "runs") == run_count
        retried_run = app.create_run(run_command)
        assert _count(fixture, "runs") == run_count + 1
        assert app.get_run(retried_run.id).id == retried_run.id


def test_concurrent_version_revise_has_one_winner_and_no_partial_history(tmp_path: Path) -> None:
    with fresh_fixture(tmp_path, "gsas-concurrent-revise") as fixture:
        ids = run_workflow(fixture, "application")
        question = fixture.application.get_research_question(ids.research_question_id)
        command = ReviseResearchQuestionCommand(
            ids.research_question_id,
            "concurrent revision",
            {"population": "race"},
            "race",
            question.row_version,
            fixture.context,
        )
        results = _race(
            lambda: fixture.fresh_application().revise_research_question(command),
            lambda: fixture.fresh_application().revise_research_question(command),
        )
        successes = [item for item in results if not isinstance(item, BaseException)]
        failures = [item for item in results if isinstance(item, ResearchBaseError)]
        assert len(successes) == 1
        assert len(failures) == 1
        assert failures[0].code is ErrorCode.CONCURRENT_MODIFICATION  # type: ignore[union-attr]
        history = fixture.application.get_research_question_history(ids.research_question_id)
        assert len(history) == 2
        assert [item.version_number for item in history] == [1, 2]


def test_concurrent_freeze_and_audit_transition_have_stable_winner_loser(tmp_path: Path) -> None:
    with fresh_fixture(tmp_path, "gsas-concurrent-freeze") as fixture:
        ids = run_workflow(fixture, "application")
        claim = fixture.application.create_claim(
            CreateClaimCommand(ids.project_id, "race claim", None, None, fixture.context)
        )
        version = fixture.application.get_current_claim_version(claim.id)
        freeze_results = _race(
            lambda: fixture.fresh_application().freeze_claim_version(
                FreezeClaimVersionCommand(claim.id, version.id, fixture.context)
            ),
            lambda: fixture.fresh_application().freeze_claim_version(
                FreezeClaimVersionCommand(claim.id, version.id, fixture.context)
            ),
        )
        freeze_successes = [item for item in freeze_results if not isinstance(item, BaseException)]
        freeze_failures = [item for item in freeze_results if isinstance(item, ResearchBaseError)]
        assert len(freeze_successes) == 1
        assert len(freeze_failures) == 1
        assert freeze_failures[0].code in {  # type: ignore[union-attr]
            ErrorCode.INVALID_STATE_TRANSITION,
            ErrorCode.CONCURRENT_MODIFICATION,
        }
        assert fixture.application.get_current_claim_version(claim.id).status.value == "FROZEN"

        finding = fixture.governance_queries.get_audit_finding(ids.finding_id)
        assert finding is not None
        transition_results = _race(
            lambda: fixture.governance.transition_audit_finding(
                TransitionAuditFindingCommand(
                    ids.finding_id,
                    AuditFindingStatus.CONFIRMED,
                    finding.row_version,
                    fixture.context,
                )
            ),
            lambda: fixture.governance.transition_audit_finding(
                TransitionAuditFindingCommand(
                    ids.finding_id,
                    AuditFindingStatus.DISMISSED,
                    finding.row_version,
                    fixture.context,
                )
            ),
        )
        transition_successes = [
            item for item in transition_results if not isinstance(item, BaseException)
        ]
        transition_failures = [
            item for item in transition_results if isinstance(item, ResearchBaseError)
        ]
        assert len(transition_successes) == 1
        assert len(transition_failures) == 1
        assert transition_failures[0].code is ErrorCode.CONCURRENT_MODIFICATION  # type: ignore[union-attr]
        final_finding = fixture.governance_queries.get_audit_finding(ids.finding_id)
        assert final_finding is not None
        assert final_finding.status in {AuditFindingStatus.CONFIRMED, AuditFindingStatus.DISMISSED}
        assert final_finding.row_version == finding.row_version + 1


def test_concurrent_run_transition_has_one_winner_and_no_partial_overwrite(
    tmp_path: Path,
) -> None:
    with fresh_fixture(tmp_path, "gsas-concurrent-run") as fixture:
        ids = run_workflow(fixture, "application")
        app = fixture.application
        run = app.create_run(
            CreateRunCommand(
                ids.project_id,
                ids.experiment_spec_version_id,
                "transition-race",
                fixture.context,
            )
        )
        run = app.attach_run_dataset_input(
            AttachRunDatasetInputCommand(
                run.id,
                ids.dataset_snapshot_id,
                DatasetInputRole.TEST,
                0,
                run.row_version,
                fixture.context,
            )
        )
        run = app.attach_run_artifact_input(
            AttachRunArtifactInputCommand(
                run.id,
                ids.artifact_version_id,
                ArtifactInputRole.SOURCE_CODE,
                0,
                run.row_version,
                fixture.context,
            )
        )
        results = _race(
            lambda: fixture.fresh_application().start_run(
                StartRunCommand(run.id, run.row_version, fixture.context)
            ),
            lambda: fixture.fresh_application().start_run(
                StartRunCommand(run.id, run.row_version, fixture.context)
            ),
        )
        successes = [item for item in results if not isinstance(item, BaseException)]
        failures = [item for item in results if isinstance(item, ResearchBaseError)]
        assert len(successes) == 1
        assert len(failures) == 1
        assert failures[0].code is ErrorCode.CONCURRENT_MODIFICATION  # type: ignore[union-attr]
        final_run = fixture.application.get_run(run.id)
        assert final_run.status.value == "RUNNING"
        assert final_run.row_version == run.row_version + 1


def test_claim_evidence_link_and_freeze_conflict_has_valid_final_state(tmp_path: Path) -> None:
    with fresh_fixture(tmp_path, "gsas-concurrent-evidence") as fixture:
        ids = run_workflow(fixture, "application")
        claim = fixture.application.create_claim(
            CreateClaimCommand(ids.project_id, "evidence race", None, None, fixture.context)
        )
        version = fixture.application.get_current_claim_version(claim.id)
        link = LinkEvidenceCommand(
            claim.id,
            version.id,
            ids.measurement_ids[0],
            None,
            EvidenceRelationType.SUPPORTS,
            "race",
            version.row_version,
            fixture.context,
        )
        results = _race(
            lambda: fixture.fresh_application().link_evidence(link),
            lambda: fixture.fresh_application().freeze_claim_version(
                FreezeClaimVersionCommand(claim.id, version.id, fixture.context)
            ),
        )
        failures = [item for item in results if isinstance(item, ResearchBaseError)]
        assert all(
            error.code in {ErrorCode.CONCURRENT_MODIFICATION, ErrorCode.IMMUTABLE_RECORD}
            for error in failures
        )
        final_version = fixture.application.get_current_claim_version(claim.id)
        assert final_version.status.value == "FROZEN"
        assert len(fixture.application.list_evidence_relations(final_version.id)) in {0, 1}
        assert fixture.provenance.get_claim_closure_report(final_version.id).complete is True
