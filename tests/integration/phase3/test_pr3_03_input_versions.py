"""Real PostgreSQL parity for heterogeneous batched exact-version reads."""

import pytest

from researchbase.foundation.ids import new_uuid7
from researchbase.persistence.research_task_queries import INPUT_FAMILIES


@pytest.mark.parametrize("out_of_scope", [False, True], ids=["scoped", "out_of_scope"])
def test_input_versions_matches_per_ref_for_all_six_families(
    planning, scientific_inputs, out_of_scope
):
    project = new_uuid7() if out_of_scope else planning.project
    refs = tuple(scientific_inputs.items())
    unknown = tuple((kind, new_uuid7()) for kind in INPUT_FAMILIES)
    with planning.factory() as uow:
        repo = uow.research_tasks
        rows = repo.input_versions(refs + unknown, project)
        assert set(rows) == set(refs)
        for key in refs:
            row = repo.input_version(*key, project)
            assert rows[key] == row
            assert row["scoped"] is (not out_of_scope)
            if key[0] in {"SOURCE_VERSION", "MANUSCRIPT_VERSION"}:
                assert row["hash_scheme"] == "sha256-cjson-v1"
        for key in unknown:
            assert repo.input_version(*key, project) is None
            assert key not in rows


def test_gateway_batched_validity_matches_shared_projection(planning, scientific_inputs):
    from sqlalchemy import event, text
    from tests.integration.phase2.test_pr2_10_binding_contract import _artifact

    from researchbase.application.governance import (
        CreateAuditFindingCommand,
        CreateCorrectionRecordCommand,
        CreateImpactAssessmentCommand,
        GovernanceService,
        ProposedImpactTarget,
        TransitionAuditFindingCommand,
    )
    from researchbase.application.governance_queries import GovernanceQueryService, ValidityState
    from researchbase.foundation.errors import ResearchBaseError
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.foundation.time import SystemClock

    service = GovernanceService(planning.factory, SystemClock())
    queries = GovernanceQueryService(planning.factory)
    context = ExecutionContext(
        actor_id=planning.principal.actor_id, request_id=new_uuid7(), client_type="test"
    )
    from tests.application_compat import LegacyApplicationService
    from tests.integration.test_pr09_application import frozen_dataset
    from tests.integration.test_pr12_application import seed_measurement

    from researchbase.application.commands import (
        RecordStatisticalResultCommand,
        StatisticalResultInputCommand,
    )
    from researchbase.domain.organization import ProjectId
    from researchbase.persistence.capability_gateway_validity import _TARGETS

    app = LegacyApplicationService(planning.factory, SystemClock(), planning.store)
    project_id = ProjectId(planning.project)
    snapshot = frozen_dataset(app, project_id, context)
    measurement = seed_measurement(app, project_id, context, "gateway-validity-parity")
    result = app.record_statistical_result(
        RecordStatisticalResultCommand(
            project_id,
            "t_test",
            {"p_value": 0.01},
            {"method": "student"},
            (StatisticalResultInputCommand(measurement),),
            context,
        )
    )
    # Follow real foreign keys from the accepted measurement to its owning chain.
    with planning.engine.connect() as conn:
        run, metric, spec = conn.execute(
            text(
                "SELECT m.run_id,m.metric_definition_version_id,r.experiment_spec_version_id "
                "FROM measurements m JOIN runs r ON r.id=m.run_id WHERE m.id=:id"
            ),
            {"id": measurement},
        ).one()
    all_targets = (
        ("experiment_spec_version", spec),
        ("dataset_snapshot", snapshot.id),
        ("run", run),
        ("metric_definition_version", metric),
        ("measurement", measurement),
        ("statistical_result", result.id),
    )
    artifact = scientific_inputs["ARTIFACT_VERSION"]
    claim = scientific_inputs["CLAIM_VERSION"]
    corrected = _artifact(
        planning.factory,
        planning.store,
        planning.principal,
        planning.project,
        b"corrected-only gateway input",
    )
    dismissed_target = _artifact(
        planning.factory,
        planning.store,
        planning.principal,
        planning.project,
        b"dismissed gateway input",
    )
    finding = service.create_audit_finding(
        CreateAuditFindingCommand(
            planning.project,
            "code_bug",
            "major",
            "Batch parity",
            "Retained evidence",
            "artifact_version",
            artifact,
            context,
        )
    )
    for conclusion in ("no_impact", "unknown", "requires_review", "stale", "invalid"):
        service.create_impact_assessment(
            CreateImpactAssessmentCommand(
                planning.project,
                finding.id,
                {"conclusion": conclusion},
                conclusion,
                (
                    ProposedImpactTarget("artifact_version", artifact, "direct"),
                    ProposedImpactTarget("artifact_version", dismissed_target, "direct"),
                ),
                context,
            )
        )
    service.create_impact_assessment(
        CreateImpactAssessmentCommand(
            planning.project,
            None,
            {"standalone": True},
            "requires_review",
            (ProposedImpactTarget("claim_version", claim, "direct"),),
            context,
        )
    )
    service.create_correction_record(
        CreateCorrectionRecordCommand(
            planning.project,
            "artifact_version",
            artifact,
            "factual",
            {"corrected": True},
            "New history",
            context,
        )
    )
    service.create_correction_record(
        CreateCorrectionRecordCommand(
            planning.project,
            "artifact_version",
            corrected,
            "factual",
            {"corrected": True},
            "Independent corrected-only history",
            context,
        )
    )
    refs = all_targets + (
        ("artifact_version", artifact),
        ("claim_version", claim),
        ("artifact_version", corrected),
        ("artifact_version", dismissed_target),
    )
    assert {kind for kind, _ in refs} == set(_TARGETS)
    # The planning fixture is deliberately at 0078; this read needs no gateway DDL.

    for dismissed in (False, True):
        if dismissed:
            service.transition_audit_finding(
                TransitionAuditFindingCommand(finding.id, "confirmed", 1, context)
            )
            service.transition_audit_finding(
                TransitionAuditFindingCommand(finding.id, "dismissed", 2, context)
            )
        statements = []

        def count(
            conn,
            cursor,
            statement,
            parameters,
            execution_context,
            executemany,
            statements=statements,
        ):
            statements.append(statement)

        with planning.factory() as uow:
            event.listen(planning.engine, "before_cursor_execute", count)
            try:
                batched = uow.gateway.input_validity_projections(planning.project, refs + refs)
            finally:
                event.remove(planning.engine, "before_cursor_execute", count)
            assert len(statements) == 2
            for kind, identity in refs:
                assert batched[kind, identity] == queries.validity_projection_in_uow(
                    uow, planning.project, kind, identity
                )
            projection = batched["artifact_version", artifact]
            assert projection.state == (
                ValidityState.NOT_ASSESSED if dismissed else ValidityState.INVALID
            )
            assert projection.correction_ids
            assert bool(projection.assessment_ids) is (not dismissed)
            corrected_view = batched["artifact_version", corrected]
            assert corrected_view.state == ValidityState.NOT_ASSESSED
            assert corrected_view.correction_ids and not corrected_view.assessment_ids
            assert not batched["artifact_version", dismissed_target].correction_ids
        for kind, identity in refs:
            for project, target in ((new_uuid7(), identity), (planning.project, new_uuid7())):
                with planning.factory() as uow:
                    with pytest.raises(ResearchBaseError) as expected:
                        queries.validity_projection_in_uow(uow, project, kind, target)
                    with pytest.raises(ResearchBaseError) as actual:
                        uow.gateway.input_validity_projections(project, ((kind, target),))
                    assert (actual.value.code, str(actual.value)) == (
                        expected.value.code,
                        str(expected.value),
                    )


def test_gateway_batches_nested_scientific_input_governance(planning, scientific_inputs):
    from sqlalchemy import event

    from researchbase.agent_runtime.application.capability_gateway import CapabilityGatewayService
    from researchbase.agent_runtime.domain.capability_invocation import GatewayRef

    statements = []

    def count(conn, cursor, statement, parameters, execution_context, executemany):
        if "WITH requested(kind,id)" in statement or any(
            table in statement for table in ("impact_targets", "correction_records")
        ):
            statements.append(statement)

    service = CapabilityGatewayService(planning.factory, None)
    with planning.factory() as uow:
        rows = uow.research_tasks.input_versions(tuple(scientific_inputs.items()), planning.project)
        refs = tuple(
            GatewayRef(
                kind,
                identity,
                rows[kind, identity]["content_hash"],
                rows[kind, identity].get("hash_scheme")
                if kind in {"SOURCE_VERSION", "MANUSCRIPT_VERSION"}
                else None,
            )
            for kind, identity in scientific_inputs.items()
        )
        event.listen(planning.engine, "before_cursor_execute", count)
        try:
            service._validate_input_refs(uow, planning.project, [], refs)
        finally:
            event.remove(planning.engine, "before_cursor_execute", count)
        assert len(statements) == 2
        assert "measurements" in statements[0] and "runs" in statements[0]
        assert "experiment_spec_versions" in statements[0] and "claim_versions" in statements[0]
