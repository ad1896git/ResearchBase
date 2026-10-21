"""B06 first-slice results, verified through their owning Application services."""

from dataclasses import replace
from uuid import UUID, uuid4

import pytest
from alembic import command as alembic_command
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from researchbase.application.commands import (
    CancelRunCommand,
    CreateRunCommand,
    FinishRunCommand,
    FreezeClaimVersionCommand,
    LinkEvidenceCommand,
    RecordStatisticalResultCommand,
    ReviseClaimCommand,
    StartRunCommand,
    StatisticalResultInputCommand,
)
from researchbase.application.internal_review import ReviewIssueRequest
from researchbase.application.revision_action import RecordRevisionActionCommand
from researchbase.application.scientific_conclusion import ClaimInputRequest
from researchbase.application.source_version import (
    CreateSourceVersion,
    SourceVersionService,
    TransitionSourceVersion,
)
from researchbase.domain.organization import ProjectId
from researchbase.domain.run import RunStatus
from researchbase.domain.source_version import (
    FrozenSourceReference,
    SourceVersionKind,
    SourceVersionMaterial,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.time import SystemClock
from tests.application_compat import LegacyApplicationService
from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE
from tests.integration.phase2.test_pr2_15_decision_schema import _config
from tests.integration.phase2.test_revision_action import (
    conclusion_env,
    decision_env,
    phase2_database_url,
    revision_env,
)

pytestmark = pytest.mark.integration
# Imported fixtures must be explicitly exposed for pytest's local discovery.
_FIXTURES = (conclusion_env, decision_env, phase2_database_url, revision_env)


def _app(base):
    return LegacyApplicationService(base[1], SystemClock(), base[2]._store)


def _context(base):
    return ExecutionContext(actor_id=base[3].actor_id, request_id=uuid4(), client_type="test")


def _measurement(base):
    with base[8].connect() as conn:
        return conn.execute(
            text("SELECT measurement_id FROM evidence_relations WHERE claim_version_id=:id"),
            {"id": base[6]},
        ).scalar_one()


def _review_issue(env, target):
    base = env[-1]
    review = env[1].create(
        base[4],
        base[5],
        "CLAIM_VERSION" if target == "claim" else "SCIENTIFIC_CONCLUSION_VERSION",
        base[6] if target == "claim" else env[3].version_id,
        "SCIENTIFIC",
        "MAJOR_REVISION",
        "TEST ONLY B06 basis",
        (ReviewIssueRequest("MAJOR", "OTHER", "TEST ONLY completed response"),),
        uuid4(),
    )
    return review.issues[0].id


def _claim_successor(base):
    from researchbase.domain.claim import ClaimVersionId

    app = _app(base)
    old = app.get_claim_version(ClaimVersionId(base[6]))
    parent = app.get_claim(old.claim_id)
    app.revise_claim(
        ReviseClaimCommand(
            parent.id, "TEST ONLY B06 successor", {}, None, parent.row_version, _context(base)
        )
    )
    draft = app.get_current_claim_version(parent.id)
    app.link_evidence(
        LinkEvidenceCommand(
            parent.id,
            draft.id,
            _measurement(base),
            None,
            "supports",
            None,
            draft.row_version,
            _context(base),
        )
    )
    draft = app.get_current_claim_version(parent.id)
    return app.freeze_claim_version(
        FreezeClaimVersionCommand(parent.id, draft.id, _context(base), draft.row_version)
    ).id


def _run(base, status="SUCCEEDED"):
    with base[8].connect() as conn:
        spec = conn.execute(
            text(
                "SELECT r.experiment_spec_version_id FROM measurements m "
                "JOIN runs r ON r.id=m.run_id WHERE m.id=:id"
            ),
            {"id": _measurement(base)},
        ).scalar_one()
    app = _app(base)
    run = app.create_run(CreateRunCommand(ProjectId(base[5]), spec, None, _context(base)))
    if status == "CANCELLED":
        terminal = app.cancel_run(CancelRunCommand(run.id, run.row_version, _context(base)))
    else:
        started = app.start_run(StartRunCommand(run.id, run.row_version, _context(base)))
        terminal = app.finish_run(
            FinishRunCommand(
                started.id,
                RunStatus(status),
                0 if status == "SUCCEEDED" else 1,
                None if status == "SUCCEEDED" else "TEST ONLY failed",
                started.row_version,
                _context(base),
            )
        )
    return spec, terminal.id


def _analysis(base):
    return (
        _app(base)
        .record_statistical_result(
            RecordStatisticalResultCommand(
                ProjectId(base[5]),
                "B06 analysis",
                {"estimate": 1},
                {"method": "TEST ONLY"},
                (StatisticalResultInputCommand(_measurement(base)),),
                _context(base),
            )
        )
        .id
    )


@pytest.mark.parametrize("target", ["claim", "conclusion"])
@pytest.mark.parametrize(
    "shape", ["NEW_EXPERIMENT", "ANALYSIS_CHANGE", "CLAIM_CHANGE", "CONCLUSION_CHANGE"]
)
def test_every_scientific_combination_exact_replay_and_no_issue_effect(revision_env, target, shape):
    service, _, env, _, revised = revision_env
    base = env[-1]
    issue = _review_issue(env, target)
    values = {}
    if shape == "NEW_EXPERIMENT":
        spec, run = _run(base)
        values = {"result_experiment_spec_version_id": spec, "result_run_id": run}
    elif shape == "ANALYSIS_CHANGE":
        values = {"result_statistical_result_id": _analysis(base)}
    elif shape == "CLAIM_CHANGE":
        values = {"result_claim_version_id": _claim_successor(base)}
    else:
        values = {"result_scientific_conclusion_version_id": revised.version_id}
    request = RecordRevisionActionCommand(uuid4(), base[5], shape, issue, **values)
    with base[8].connect() as conn:
        before = conn.execute(text("SELECT count(*) FROM review_issue_events")).scalar_one()
    saved = service.record_revision_action(base[3], request)
    assert saved.result_validity == "VALID"
    assert service.record_revision_action(base[3], request) == saved
    assert service.read_revision_action(base[3], base[5], request.id) == saved
    clone = _normal_sql_clone(base, request.id)
    assert service.read_revision_action(base[3], base[5], clone).content_hash == saved.content_hash
    with base[8].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM review_issue_events")).scalar_one() == before
        assert (
            conn.execute(
                text("SELECT status FROM review_issues WHERE id=:id"), {"id": issue}
            ).scalar_one()
            == "OPEN"
        )


@pytest.mark.parametrize("status", ["FAILED", "CANCELLED"])
def test_failed_and_cancelled_runs_are_completed_history(revision_env, status):
    service, cmd, env, _, _ = revision_env
    base = env[-1]
    spec, run = _run(base, status)
    request = RecordRevisionActionCommand(
        uuid4(),
        base[5],
        "NEW_EXPERIMENT",
        cmd.review_issue_id,
        result_experiment_spec_version_id=spec,
        result_run_id=run,
    )
    saved = service.record_revision_action(base[3], request)
    assert saved.provenance[-1].type == "Run" and saved.provenance[-1].content_hash is None


def _source_response(env, target, kind):
    base = env[-1]
    literature = base[2]
    evidence = literature.create(base[3], base[5], base[7], "improved recall", uuid4())
    literature.review(
        base[4], base[5], UUID(evidence["id"]), "VERIFIED", "TEST ONLY independent review", uuid4()
    )
    snapshot = literature.snapshot(
        base[3],
        base[5],
        "ClaimVersion",
        base[6],
        [
            {
                "evidence_id": str(evidence["id"]),
                "relation_type": "SUPPORTS",
                "qualification": "TEST ONLY relevance",
            }
        ],
        uuid4(),
    )
    if target == "conclusion":
        target_version = base[0].create(
            base[3],
            base[5],
            "TEST ONLY saved source target",
            SCOPE,
            "MODERATE",
            None,
            (ClaimInputRequest(base[6], "SUPPORTS", UUID(snapshot["id"])),),
            (),
            uuid4(),
        )
        base[0].freeze(
            base[3], base[5], target_version.conclusion_id, target_version.version_id, uuid4()
        )
        review = env[1].create(
            base[4],
            base[5],
            "SCIENTIFIC_CONCLUSION_VERSION",
            target_version.version_id,
            "SCIENTIFIC",
            "MAJOR_REVISION",
            "TEST ONLY",
            (ReviewIssueRequest("MAJOR", "OTHER", "TEST ONLY"),),
            uuid4(),
        )
        issue = review.issues[0].id
    else:
        issue = _review_issue(env, target)
    correction = literature.import_document(
        base[3], base[5], b"TEST ONLY source correction", "text/plain", "TEST ONLY rights", uuid4()
    )
    with base[1]() as uow:
        old = uow.source_version.version(base[7])
    material = SourceVersionMaterial(
        old["literature_source_id"],
        SourceVersionKind(kind),
        FrozenSourceReference(old["id"], old["content_hash"]),
        FrozenSourceReference(UUID(correction["artifact_version_id"]), correction["content_hash"]),
        "TEST ONLY corrected",
        None,
        (),
        None,
        None,
        None,
        None,
        None,
    )
    sources = SourceVersionService(base[1], base[-1])
    created = sources.create(CreateSourceVersion(base[3], base[5], material, uuid4()))
    identity = UUID(str(created["source_version_id"]))
    sources.freeze(TransitionSourceVersion(base[3], base[5], identity, uuid4()))
    return RecordRevisionActionCommand(
        uuid4(), base[5], "SOURCE_CHANGE", issue, result_source_version_id=identity
    )


@pytest.mark.parametrize("target", ["claim", "conclusion"])
@pytest.mark.parametrize("kind", ["CORRECTED", "RETRACTED"])
def test_source_lineage_optional_fulltext_and_retraction_history(revision_env, target, kind):
    service, _, env, _, _ = revision_env
    base = env[-1]
    request = _source_response(env, target, kind)
    saved = service.record_revision_action(base[3], request)
    assert saved.result_validity == ("INVALID" if kind == "RETRACTED" else "VALID")
    assert service.read_revision_action(base[3], base[5], request.id) == saved
    assert service.record_revision_action(base[3], request) == saved
    clone = _normal_sql_clone(base, request.id)
    assert service.read_revision_action(base[3], base[5], clone).content_hash == saved.content_hash
    with pytest.raises(DBAPIError) as caught:
        alembic_command.downgrade(
            _config(base[8].url.render_as_string(hide_password=False)),
            "0050_b01_resolution_admission",
        )
    assert getattr(caught.value.orig, "sqlstate", None) == "P17F2"
    assert service.read_revision_action(base[3], base[5], request.id) == saved


@pytest.mark.parametrize("shape", ["NO_CHANGE", "MANUSCRIPT_CHANGE"])
def test_incomplete_result_shapes_stay_closed(revision_env, shape):
    service, cmd, env, _, _ = revision_env
    base = env[-1]
    request = RecordRevisionActionCommand(
        uuid4(),
        base[5],
        shape,
        cmd.review_issue_id,
        **({"result_manuscript_version_id": uuid4()} if shape == "MANUSCRIPT_CHANGE" else {}),
    )
    with pytest.raises(ResearchBaseError) as caught:
        service.record_revision_action(base[3], request)
    assert caught.value.code == (
        ErrorCode.DECISION_BASIS_INVALID if shape == "NO_CHANGE" else ErrorCode.NOT_FOUND
    )


@pytest.mark.parametrize("mutation", ["old_run", "wrong_spec", "unsealed", "nonterminal"])
def test_experiment_rejects_incomplete_or_unrelated_results(revision_env, mutation):
    service, cmd, env, _, _ = revision_env
    base = env[-1]
    spec, run = _run(base)
    if mutation == "old_run":
        with base[8].connect() as conn:
            run = conn.execute(
                text("SELECT run_id FROM measurements WHERE id=:id"), {"id": _measurement(base)}
            ).scalar_one()
    elif mutation == "wrong_spec":
        spec = uuid4()
    elif mutation == "unsealed":
        planned = _app(base).create_run(
            CreateRunCommand(ProjectId(base[5]), spec, None, _context(base))
        )
        run = planned.id
    else:
        with base[8].begin() as conn:
            conn.execute(text("ALTER TABLE runs DISABLE TRIGGER USER"))
            conn.execute(
                text(
                    "UPDATE runs SET "
                    + (
                        "inputs_sealed_at=NULL"
                        if mutation == "unsealed"
                        else "status='RUNNING',finished_at=NULL"
                    )
                    + " WHERE id=:id"
                ),
                {"id": run},
            )
            conn.execute(text("ALTER TABLE runs ENABLE TRIGGER USER"))
    request = RecordRevisionActionCommand(
        uuid4(),
        base[5],
        "NEW_EXPERIMENT",
        cmd.review_issue_id,
        result_experiment_spec_version_id=spec,
        result_run_id=run,
    )
    with pytest.raises(ResearchBaseError) as caught:
        service.record_revision_action(base[3], request)
    assert caught.value.code == {
        "unsealed": ErrorCode.FROZEN_REFERENCE_REQUIRED,
        "nonterminal": ErrorCode.INVALID_STATE_TRANSITION,
    }.get(
        mutation,
        ErrorCode.NOT_FOUND if mutation == "wrong_spec" else ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
    )


def _normal_sql_clone(base, identity, changes=None):
    """Normal-role structural bypass witness; saved literal hash is independent of row ID."""
    with base[8].connect() as conn:
        row = dict(
            conn.execute(text("SELECT * FROM revision_actions WHERE id=:id"), {"id": identity})
            .mappings()
            .one()
        )
    row.update(id=uuid4(), **(changes or {}))
    role = "b06_normal_" + uuid4().hex
    with base[8].begin() as conn:
        conn.execute(text(f"CREATE ROLE {role} NOLOGIN NOSUPERUSER"))
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
        conn.execute(text(f"GRANT SELECT,INSERT,UPDATE ON ALL TABLES IN SCHEMA public TO {role}"))
        conn.execute(text(f"SET LOCAL ROLE {role}"))
        keys = tuple(row)
        conn.execute(
            text(
                "INSERT INTO revision_actions ("
                + ",".join(keys)
                + ") VALUES ("
                + ",".join(":" + key for key in keys)
                + ")"
            ),
            row,
        )
        conn.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        conn.execute(text("RESET ROLE"))
        conn.execute(text(f"DROP OWNED BY {role}"))
        conn.execute(text(f"DROP ROLE {role}"))
    return row["id"]


@pytest.mark.parametrize(
    "mutation", ["unrelated", "foreign_metric", "corrupt_hash", "invalid_measurement"]
)
def test_analysis_verifies_all_inputs_and_direct_sql_scope(revision_env, mutation):
    from researchbase.application.governance import (
        CreateAuditFindingCommand,
        CreateImpactAssessmentCommand,
        GovernanceService,
        ProposedImpactTarget,
    )
    from researchbase.domain.measurement import MeasurementId
    from tests.integration.test_pr12_application import seed_measurement

    service, cmd, env, _, _ = revision_env
    base = env[-1]
    app = _app(base)
    shared = _measurement(base)
    extra = seed_measurement(app, ProjectId(base[5]), _context(base), "B06 extra input")
    inputs = (
        (StatisticalResultInputCommand(extra),)
        if mutation == "unrelated"
        else (
            StatisticalResultInputCommand(shared, ordinal=0),
            StatisticalResultInputCommand(extra, ordinal=1),
        )
    )
    result = app.record_statistical_result(
        RecordStatisticalResultCommand(
            ProjectId(base[5]),
            "B06 different analysis",
            {"estimate": 2},
            {"method": "TEST ONLY"},
            inputs,
            _context(base),
        )
    )
    if mutation == "foreign_metric":
        with base[8].begin() as conn:
            foreign = uuid4()
            conn.execute(
                text(
                    "INSERT INTO projects (id,name,created_by,created_at) "
                    "VALUES (:id,'TEST ONLY foreign metric',:actor,clock_timestamp())"
                ),
                {"id": foreign, "actor": base[3].actor_id},
            )
            metric = app.get_measurement(MeasurementId(extra)).metric_definition_version_id
            conn.execute(
                text(
                    "UPDATE metric_definitions SET project_id=:project "
                    "WHERE id=(SELECT metric_definition_id FROM metric_definition_versions "
                    "WHERE id=:id)"
                ),
                {"project": foreign, "id": metric},
            )
    elif mutation == "corrupt_hash":
        with base[8].begin() as conn:
            conn.execute(text("ALTER TABLE statistical_results DISABLE TRIGGER USER"))
            conn.execute(
                text("UPDATE statistical_results SET content_hash=:hash WHERE id=:id"),
                {"hash": "0" * 64, "id": result.id},
            )
            conn.execute(text("ALTER TABLE statistical_results ENABLE TRIGGER USER"))
    elif mutation == "invalid_measurement":
        governance = GovernanceService(base[1], SystemClock())
        finding = governance.create_audit_finding(
            CreateAuditFindingCommand(
                base[5],
                "code_bug",
                "major",
                "TEST ONLY invalid second input",
                "recheck",
                "measurement",
                extra,
                _context(base),
            )
        )
        governance.create_impact_assessment(
            CreateImpactAssessmentCommand(
                base[5],
                finding.id,
                {"basis": "TEST ONLY"},
                "invalid",
                (ProposedImpactTarget("measurement", extra, "invalid"),),
                _context(base),
            )
        )
    request = RecordRevisionActionCommand(
        uuid4(),
        base[5],
        "ANALYSIS_CHANGE",
        cmd.review_issue_id,
        result_statistical_result_id=result.id,
    )
    with pytest.raises(ResearchBaseError) as caught:
        service.record_revision_action(base[3], request)
    assert caught.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    if mutation == "foreign_metric":
        # No Application proof: independently insert an action as a normal role.
        service.record_revision_action(base[3], cmd)
        with pytest.raises(DBAPIError) as sql_failure:
            _normal_sql_clone(
                base,
                cmd.id,
                {
                    "action_type": "ANALYSIS_CHANGE",
                    "result_scientific_conclusion_version_id": None,
                    "result_statistical_result_id": result.id,
                },
            )
        assert getattr(sql_failure.value.orig, "sqlstate", None) == "P17F2"


@pytest.mark.parametrize(
    "mutation",
    ["artifact_missing", "artifact_size", "predecessor_hash", "published", "unrelated_source"],
)
def test_source_correction_complete_closure_and_relevance(revision_env, mutation):
    service, _, env, _, _ = revision_env
    base = env[-1]
    request = _source_response(env, "claim", "CORRECTED")
    with base[1]() as uow:
        source = uow.source_version.version(request.result_source_version_id)
        basis_artifact = uow.artifact_versions.get(source["correction_basis_artifact_version_id"])
    if mutation == "artifact_missing":
        base[2]._store._path_for(basis_artifact.locator).unlink()
    elif mutation == "artifact_size":
        with base[8].begin() as conn:
            conn.execute(text("ALTER TABLE artifact_versions DISABLE TRIGGER USER"))
            conn.execute(
                text("UPDATE artifact_versions SET byte_size=byte_size+1 WHERE id=:id"),
                {"id": basis_artifact.id},
            )
            conn.execute(text("ALTER TABLE artifact_versions ENABLE TRIGGER USER"))
    elif mutation == "predecessor_hash":
        with base[8].begin() as conn:
            conn.execute(text("ALTER TABLE source_versions DISABLE TRIGGER USER"))
            conn.execute(
                text(
                    "UPDATE source_versions SET title='TEST ONLY corrupted predecessor' "
                    "WHERE id=:id"
                ),
                {"id": source["predecessor_source_version_id"]},
            )
            conn.execute(text("ALTER TABLE source_versions ENABLE TRIGGER USER"))
    elif mutation == "published":
        request = replace(request, result_source_version_id=base[7])
    else:
        # Same project, no literature path from this exact reviewed target.
        request = replace(request, review_issue_id=_review_issue(env, "conclusion"))
    with pytest.raises(ResearchBaseError) as caught:
        service.record_revision_action(base[3], request)
    assert caught.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def test_forward_migration_retains_shipped_history_and_preserved_catalog(revision_env):
    service, cmd, env, _, _ = revision_env
    base = env[-1]
    config = _config(base[8].url.render_as_string(hide_password=False))
    # Start from 0044-compatible retained history, downgrade guard only, then preflight upgrade.
    saved = service.record_revision_action(base[3], cmd)
    with base[8].connect() as conn:
        before = conn.execute(
            text("SELECT * FROM revision_actions WHERE id=:id"), {"id": cmd.id}
        ).one()
        checks = conn.execute(
            text(
                "SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conrelid='revision_actions'::regclass ORDER BY conname"
            )
        ).all()
        indexes = conn.execute(
            text(
                "SELECT indexname,indexdef FROM pg_indexes "
                "WHERE tablename='revision_actions' ORDER BY indexname"
            )
        ).all()
    alembic_command.downgrade(config, "0050_b01_resolution_admission")
    alembic_command.upgrade(config, "head")
    with base[8].connect() as conn:
        assert (
            conn.execute(text("SELECT * FROM revision_actions WHERE id=:id"), {"id": cmd.id}).one()
            == before
        )
        assert (
            conn.execute(
                text(
                    "SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conrelid='revision_actions'::regclass ORDER BY conname"
                )
            ).all()
            == checks
        )
        assert (
            conn.execute(
                text(
                    "SELECT indexname,indexdef FROM pg_indexes "
                    "WHERE tablename='revision_actions' ORDER BY indexname"
                )
            ).all()
            == indexes
        )
        deferred, initial = conn.execute(
            text(
                "SELECT tgdeferrable,tginitdeferred FROM pg_trigger "
                "WHERE tgname='b06_revision_complete'"
            )
        ).one()
        assert deferred and initial
    assert service.read_revision_action(base[3], base[5], cmd.id) == saved


def test_global_artifact_metric_inputs_keep_phase1_owner_semantics(revision_env):
    from researchbase.application.commands import (
        AttachRunArtifactInputCommand,
        CreateArtifactCommand,
        CreateArtifactVersionCommand,
        CreateMetricDefinitionCommand,
        FreezeArtifactVersionCommand,
        FreezeMetricDefinitionCommand,
        RecordMeasurementCommand,
    )

    service, cmd, env, _, _ = revision_env
    base = env[-1]
    app = _app(base)
    context = _context(base)
    with base[8].connect() as conn:
        spec = conn.execute(
            text(
                "SELECT r.experiment_spec_version_id FROM measurements m "
                "JOIN runs r ON r.id=m.run_id WHERE m.id=:id"
            ),
            {"id": _measurement(base)},
        ).scalar_one()
    artifact = app.create_artifact(
        CreateArtifactCommand(None, "code", "TEST ONLY shared", None, context)
    )
    draft = app.create_artifact_version(
        CreateArtifactVersionCommand(
            artifact.id, b"TEST ONLY shared bytes", None, None, "text/plain", None, None, context
        )
    )
    frozen = app.freeze_artifact_version(
        FreezeArtifactVersionCommand(artifact.id, draft.id, context)
    )
    run = app.create_run(CreateRunCommand(ProjectId(base[5]), spec, None, context))
    edge = app.attach_run_artifact_input(
        AttachRunArtifactInputCommand(run.id, frozen.id, "source_code", 0, run.row_version, context)
    )
    started = app.start_run(StartRunCommand(run.id, edge.row_version, context))
    finished = app.finish_run(
        FinishRunCommand(run.id, RunStatus.SUCCEEDED, 0, None, started.row_version, context)
    )
    request = RecordRevisionActionCommand(
        uuid4(),
        base[5],
        "NEW_EXPERIMENT",
        cmd.review_issue_id,
        result_experiment_spec_version_id=spec,
        result_run_id=finished.id,
    )
    saved = service.record_revision_action(base[3], request)
    _normal_sql_clone(base, request.id)
    metric = app.create_metric_definition(
        CreateMetricDefinitionCommand(
            None, "TEST ONLY shared metric", {"metric": "count"}, None, None, context
        )
    )
    metric_version = app.freeze_metric_definition(
        FreezeMetricDefinitionCommand(metric.id, metric.current_version_id, context, 1)
    )
    measured = app.record_measurement(
        RecordMeasurementCommand(finished.id, metric_version.id, 1, None, None, None, context)
    )
    result = app.record_statistical_result(
        RecordStatisticalResultCommand(
            ProjectId(base[5]),
            "TEST ONLY global input analysis",
            {"estimate": 1},
            {"method": "count"},
            (
                StatisticalResultInputCommand(_measurement(base)),
                StatisticalResultInputCommand(measured.id, ordinal=1),
            ),
            context,
        )
    )
    analysis = RecordRevisionActionCommand(
        uuid4(),
        base[5],
        "ANALYSIS_CHANGE",
        cmd.review_issue_id,
        result_statistical_result_id=result.id,
    )
    service.record_revision_action(base[3], analysis)
    _normal_sql_clone(base, analysis.id)
    assert service.read_revision_action(base[3], base[5], saved.id) == saved

    with base[8].connect() as conn:
        retained = conn.execute(
            text("SELECT id,content_hash FROM revision_actions ORDER BY id")
        ).all()
    alembic_command.downgrade(
        _config(base[8].url.render_as_string(hide_password=False)), "0051_b06_revision_action"
    )
    alembic_command.upgrade(_config(base[8].url.render_as_string(hide_password=False)), "head")
    with base[8].connect() as conn:
        assert (
            conn.execute(text("SELECT id,content_hash FROM revision_actions ORDER BY id")).all()
            == retained
        )


@pytest.mark.parametrize("shape", ["SOURCE_CHANGE", "CLAIM_CHANGE"])
def test_later_invalid_sidecar_does_not_rewrite_verified_history(revision_env, shape):
    service, _, env, _, _ = revision_env
    base = env[-1]
    if shape == "SOURCE_CHANGE":
        request = _source_response(env, "claim", "CORRECTED")
        saved = service.record_revision_action(base[3], request)
    else:
        request = RecordRevisionActionCommand(
            uuid4(),
            base[5],
            shape,
            _review_issue(env, "claim"),
            result_claim_version_id=_claim_successor(base),
        )
        saved = service.record_revision_action(base[3], request)
        _source_response(env, "claim", "CORRECTED")
    with base[8].connect() as conn:
        evidence = conn.execute(
            text("SELECT id FROM literature_evidence WHERE source_version_id=:id"), {"id": base[7]}
        ).scalar_one()
    later = base[2].snapshot(
        base[3],
        base[5],
        "ClaimVersion",
        base[6],
        [
            {
                "evidence_id": str(evidence),
                "relation_type": "QUALIFIES",
                "qualification": "TEST ONLY later sidecar",
            }
        ],
        uuid4(),
    )
    # Explicit privileged corruption of a later sidecar outside this saved action's witness.
    with base[8].begin() as conn:
        conn.execute(text("ALTER TABLE literature_support_snapshots DISABLE TRIGGER USER"))
        conn.execute(
            text("UPDATE literature_support_snapshots SET content_hash=:hash WHERE id=:id"),
            {"hash": "0" * 64, "id": UUID(later["id"])},
        )
        conn.execute(text("ALTER TABLE literature_support_snapshots ENABLE TRIGGER USER"))
    assert service.record_revision_action(base[3], request) == saved
    assert service.read_revision_action(base[3], base[5], request.id) == saved


def test_replacement_snapshot_keeps_ancestor_retraction_as_history(revision_env):
    from researchbase.application.source_identity import (
        RegisterLiteratureSource,
        SourceIdentityService,
    )
    from researchbase.domain.source_identity import SourceKind

    service, _, env, _, _ = revision_env
    base = env[-1]
    _source_response(env, "claim", "RETRACTED")
    source = SourceIdentityService(base[1], base[-1]).register_literature_source(
        RegisterLiteratureSource(
            base[3], base[5], SourceKind.PAPER, "TEST ONLY replacement", uuid4()
        )
    )
    document = base[2].import_document(
        base[3],
        base[5],
        b"Replacement support is independently valid.",
        "text/plain",
        "TEST ONLY rights",
        uuid4(),
    )
    versions = SourceVersionService(base[1], base[-1])
    material = SourceVersionMaterial(
        UUID(str(source["source_id"])),
        SourceVersionKind.PUBLISHED,
        None,
        None,
        "TEST ONLY replacement",
        None,
        (),
        None,
        None,
        None,
        FrozenSourceReference(UUID(document["artifact_version_id"]), document["content_hash"]),
        None,
    )
    draft = versions.create(CreateSourceVersion(base[3], base[5], material, uuid4()))
    identity = UUID(str(draft["source_version_id"]))
    versions.freeze(TransitionSourceVersion(base[3], base[5], identity, uuid4()))
    evidence = base[2].create(base[3], base[5], identity, "Replacement support", uuid4())
    base[2].review(
        base[4], base[5], UUID(evidence["id"]), "VERIFIED", "TEST ONLY independent", uuid4()
    )
    snapshot = base[2].snapshot(
        base[3],
        base[5],
        "ClaimVersion",
        base[6],
        [
            {
                "evidence_id": evidence["id"],
                "relation_type": "SUPPORTS",
                "qualification": "TEST ONLY replacement",
            }
        ],
        uuid4(),
    )
    assert snapshot["validity"] == "VALID"
    result = base[0].create(
        base[3],
        base[5],
        "TEST ONLY corrected conclusion",
        SCOPE,
        "MODERATE",
        None,
        (ClaimInputRequest(base[6], "SUPPORTS", UUID(snapshot["id"])),),
        (),
        uuid4(),
    )
    base[0].freeze(base[3], base[5], result.conclusion_id, result.version_id, uuid4())
    request = RecordRevisionActionCommand(
        uuid4(),
        base[5],
        "CONCLUSION_CHANGE",
        _review_issue(env, "claim"),
        result_scientific_conclusion_version_id=result.version_id,
    )
    saved = service.record_revision_action(base[3], request)
    assert saved.result_validity == "VALID"
    assert service.read_revision_action(base[3], base[5], request.id) == saved
