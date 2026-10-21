"""B25 integrity, exact provenance witnesses and current validity on PostgreSQL."""

# ruff: noqa: E501

from dataclasses import replace
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.b25_support import impact, place, queries
from tests.integration.phase2.test_b05_manuscript_review import (  # noqa: F401
    b04_env as _b04_env,
)
from tests.integration.phase2.test_b05_manuscript_review import (
    b05_env as _b05_env,
)
from tests.integration.phase2.test_b05_manuscript_review import (
    conclusion_env as _conclusion_env,
)
from tests.integration.phase2.test_b05_manuscript_review import (
    phase2_database_url as _phase2_database_url,
)
from tests.integration.phase2.test_b05_manuscript_review import (
    seal,
)

b04_env = _b04_env
b05_env = _b05_env
conclusion_env = _conclusion_env
phase2_database_url = _phase2_database_url

pytestmark = pytest.mark.integration


def test_empty_and_unchanged_seal(b05_env):
    env = b05_env
    sealed = seal(env)
    service, q, aq = queries(env)
    result = service.get_manuscript_validity(env[2], q)
    audit = service.get_manuscript_audit(env[3], aq)
    assert result.current_validity == "VALID"
    assert result.content_hash == sealed.content_hash
    assert result.placement_set_hash == sealed.placement_set_hash
    assert {w.node.kind for w in result.witnesses} == {"ManuscriptVersion", "ArtifactVersion"}
    assert audit.unsupported_concerns == audit.blocking_issue_ids == ()
    assert audit.validity.witnesses == result.witnesses
    assert all(w.occurrences[0].nodes[0].id == q.manuscript_version_id for w in result.witnesses)
    assert env[6].get_manuscript_version(env[2], env[1]) == sealed


@pytest.mark.parametrize("conclusion", [False, True])
@pytest.mark.parametrize(
    "kind",
    [
        "claim_version",
        "measurement",
        "metric_definition_version",
        "run",
        "experiment_spec_version",
        "artifact_version",
    ],
)
def test_upstream_witnesses_and_invalidation(b05_env, conclusion, kind):
    env = b05_env
    place(env, conclusion=conclusion)
    sealed = seal(env)
    service, q, _ = queries(env)
    before = service.get_manuscript_validity(env[2], q)
    names = {
        "claim_version": "ClaimVersion",
        "measurement": "Measurement",
        "metric_definition_version": "MetricDefinitionVersion",
        "run": "Run",
        "experiment_spec_version": "ExperimentSpecVersion",
        "artifact_version": "ArtifactVersion",
    }
    node = next(w.node for w in before.witnesses if w.node.kind == names[kind])
    impact(env, kind, node.id, "invalid")
    after = service.get_manuscript_validity(env[2], q)
    assert after.current_validity == "INVALID"
    witness = next(w for w in after.witnesses if w.node == node)
    assert witness.governance is not None
    assert witness.state == "INVALID" and witness.governance.assessment_ids
    assert after.content_hash == sealed.content_hash
    assert after.placement_set_hash == sealed.placement_set_hash
    assert all(
        w.governance is None or w.governance.state.value == "not_assessed" for w in before.witnesses
    )
    if conclusion and kind != "artifact_version":
        assert any(
            w.node.kind == "ScientificConclusionVersion" and w.state == "INVALID"
            for w in after.witnesses
        )


@pytest.mark.parametrize("order", [("stale", "invalid"), ("invalid", "stale")])
def test_invalid_dominates_in_both_placement_orders(b05_env, order):
    env = b05_env
    place(env)
    place(env, conclusion=True)
    seal(env)
    service, q, _ = queries(env)
    witnesses = service.get_manuscript_validity(env[2], q).witnesses
    claim = next(w.node for w in witnesses if w.node.kind == "ClaimVersion")
    metric = next(w.node for w in witnesses if w.node.kind == "MetricDefinitionVersion")
    impact(env, "claim_version", claim.id, order[0])
    impact(env, "metric_definition_version", metric.id, order[1])
    assert service.get_manuscript_validity(env[2], q).current_validity == "INVALID"


@pytest.mark.parametrize(
    "failure",
    [
        "draft",
        "missing",
        "parent",
        "unauthenticated",
        "credential",
        "hash",
        "size",
        "bytes",
        "seal",
        "nested_missing",
    ],
)
def test_pinned_error_contract(b05_env, failure, monkeypatch):
    env = b05_env
    service, q, _ = queries(env)
    if failure != "draft":
        seal(env)
    principal: Any = env[2]
    if failure == "missing":
        q = replace(q, manuscript_version_id=uuid4())
    if failure == "parent":
        q = replace(q, publication_id=uuid4())
    if failure == "unauthenticated":
        principal = None
    if failure == "credential":
        principal = replace(principal, credential_id=str(uuid4()))
    if failure == "bytes":
        monkeypatch.setattr(env[7], "verify", lambda value: False)
    if failure in {"hash", "size", "seal"}:
        sql = {
            "hash": "UPDATE manuscript_versions SET content_hash=repeat('0',64)",
            "size": "UPDATE artifact_versions SET byte_size=byte_size+1",
            "seal": "UPDATE manuscript_versions SET hash_scheme='wrong'",
        }[failure]
        with env[5].begin() as conn:
            conn.execute(text("SET LOCAL session_replication_role='replica'"))
            if failure == "seal":
                conn.execute(
                    text(
                        "ALTER TABLE manuscript_versions DROP CONSTRAINT manuscript_versions_hash_scheme_check"
                    )
                )
            conn.execute(text(sql))
    if failure == "nested_missing":
        monkeypatch.setattr(service._trace._freeze, "verify_in_uow", lambda *a, **kw: None)
        from researchbase.persistence.manuscript_freeze_repository import (
            SqlAlchemyManuscriptFreezeRepository,
        )

        monkeypatch.setattr(SqlAlchemyManuscriptFreezeRepository, "artifact", lambda *a: None)
    expected = {
        "draft": ErrorCode.VERSION_NOT_FROZEN,
        "missing": ErrorCode.NOT_FOUND,
        "parent": ErrorCode.NOT_FOUND,
        "unauthenticated": ErrorCode.AUTHENTICATION_REQUIRED,
        "credential": ErrorCode.FORBIDDEN,
    }.get(failure, ErrorCode.PROVENANCE_CLOSURE_VIOLATION)
    with pytest.raises(ResearchBaseError) as error:
        service.get_manuscript_validity(principal, q)
    assert error.value.code == expected


@pytest.mark.parametrize("snapshot", [False, True])
@pytest.mark.parametrize("change", ["DISPUTED", "REJECTED", "UNREVIEWED", "CORRECTED", "RETRACTED"])
def test_literature_states_and_bound_snapshot_paths(b05_env, snapshot, change):
    from tests.integration.phase2.b25_support import literature_conclusion, source_transition

    env = b05_env
    evidence, support, conclusion = literature_conclusion(env, snapshot=snapshot)
    sealed = seal(env)
    service, q, aq = queries(env)
    if change in {"CORRECTED", "RETRACTED"}:
        source_transition(env, change)
    elif change == "UNREVIEWED":
        with env[5].begin() as conn:
            conn.execute(text("SET LOCAL session_replication_role='replica'"))
            conn.execute(
                text(
                    "DELETE FROM literature_evidence_review_events WHERE literature_evidence_id=:id"
                ),
                {"id": evidence},
            )
            conn.execute(
                text("UPDATE literature_evidence SET review_status='UNREVIEWED' WHERE id=:id"),
                {"id": evidence},
            )
        if not snapshot:
            # The direct-input owner requires retained verification at the freeze time.
            with pytest.raises(ResearchBaseError) as error:
                service.get_manuscript_audit(env[3], aq)
            assert error.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
            return
    else:
        literature = env[10][2]
        if change == "REJECTED":
            literature.review(env[3], q.project_id, evidence, "DISPUTED", "Later dispute", uuid4())
        literature.review(env[3], q.project_id, evidence, change, "Later verification", uuid4())
    result = service.get_manuscript_audit(env[3], aq)
    assert result.validity.current_validity == ("INVALID" if change == "RETRACTED" else "STALE")
    witness = next(w for w in result.validity.witnesses if w.node.kind == "LiteratureEvidence")
    assert witness.node.id == evidence
    assert witness.evidence_review_status == (
        "VERIFIED" if change in {"CORRECTED", "RETRACTED"} else change
    )
    path = witness.occurrences[0]
    assert path.nodes[1].id == conclusion
    if snapshot:
        assert [node.kind for node in path.nodes] == [
            "ManuscriptVersion",
            "ScientificConclusionVersion",
            "ClaimVersion",
            "LiteratureSupportSnapshot",
            "LiteratureEvidence",
        ]
        assert path.nodes[3].id == support
    assert result.unsupported_concerns == ()
    assert result.validity.content_hash == sealed.content_hash


def test_corrected_predecessor_is_history_not_current_validity_owner(b05_env):
    from tests.integration.phase2.b25_support import literature_conclusion, source_transition

    env = b05_env
    corrected = source_transition(env, "CORRECTED")
    literature_conclusion(env, source=corrected)
    seal(env)
    service, q, _ = queries(env)
    result = service.get_manuscript_validity(env[3], q)
    sources = {w.node.id: w for w in result.witnesses if w.node.kind == "SourceVersion"}
    assert result.current_validity == "VALID"
    assert sources[corrected].state == "VALID"
    assert sources[env[10][7]].state == "STALE"
    assert sources[env[10][7]].occurrences[0].nodes[-2].id == corrected


def test_all_placements_citation_only_does_not_create_support(b05_env):
    from researchbase.application.manuscript_placement import (
        ArtifactPlacementService,
        CitationPlacementService,
    )

    env = b05_env
    q = env[1]
    CitationPlacementService(env[4], env[9]).add(
        env[2],
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        env[10][7],
        "INTRO",
        {"kind": "PARAGRAPH", "value": "p1"},
        "BACKGROUND",
        0,
        uuid4(),
    )
    document = env[6].get_manuscript_version(env[2], q).document_artifact_version_id
    ArtifactPlacementService(env[4], env[9]).add(
        env[2],
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        document,
        "APPENDIX",
        {"kind": "ANCHOR", "value": "doc"},
        "OTHER",
        0,
        uuid4(),
    )
    seal(env)
    service, _, aq = queries(env)
    result = service.get_manuscript_audit(env[3], aq)
    assert result.unsupported_concerns == ()
    assert result.trace.placements[1].semantic == "CITATION_ONLY"
    assert not any(
        w.node.kind in {"ClaimVersion", "ScientificConclusionVersion"}
        for w in result.validity.witnesses
    )


def test_ceiling_plus_one_is_rejected_before_placement_hydration(b05_env):
    env = b05_env
    seal(env)
    with env[5].begin() as conn:
        conn.execute(text("SET LOCAL session_replication_role='replica'"))
        conn.execute(
            text("""INSERT INTO manuscript_claim_placements
            (id,manuscript_version_id,claim_version_id,section_id,locator,rhetorical_strength,ordinal,created_by,created_at,row_version)
            SELECT gen_random_uuid(),:manuscript,:claim,'RESULTS','{"kind":"PARAGRAPH","value":"p"}'::jsonb,
            'SUPPORTED',n,:actor,clock_timestamp(),1 FROM generate_series(0,10000) n"""),
            {"manuscript": env[1].manuscript_version_id, "claim": env[8], "actor": env[2].actor_id},
        )
    service, q, _ = queries(env)
    with pytest.raises(ResearchBaseError, match="ceiling") as error:
        service.get_manuscript_validity(env[3], q)
    assert error.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


@pytest.mark.parametrize("affected", ["statistical_result", "dataset_snapshot", "artifact_version"])
def test_statistical_and_sealed_input_witnesses(b05_env, affected):
    from researchbase.application.commands import (
        AttachRunArtifactInputCommand,
        AttachRunDatasetInputCommand,
        CreateDatasetSnapshotCommand,
        CreateRunCommand,
        FinishRunCommand,
        FreezeClaimVersionCommand,
        LinkEvidenceCommand,
        RecordMeasurementCommand,
        RecordStatisticalResultCommand,
        RegisterDatasetCommand,
        StartRunCommand,
        StatisticalResultInputCommand,
    )
    from researchbase.domain.artifact import ArtifactVersionId
    from researchbase.domain.organization import ProjectId
    from researchbase.domain.run import RunStatus
    from researchbase.foundation.execution_context import ExecutionContext
    from researchbase.foundation.time import SystemClock
    from tests.application_compat import LegacyApplicationService
    from tests.integration.phase2.test_pr2_10_binding_contract import _artifact
    from tests.integration.test_pr12_application import seed_claim

    env = b05_env
    app = LegacyApplicationService(env[4], SystemClock(), env[7])
    project = ProjectId(env[1].project_id)
    context = ExecutionContext(actor_id=env[2].actor_id, request_id=uuid4(), client_type="test")
    with env[4]() as uow:
        old = uow.measurements.get(uow.claims.list_evidence(env[8])[0].measurement_id)
        original_run = uow.runs.get(old.run_id)
    dataset = app.register_dataset(
        RegisterDatasetCommand(project, "B25 dataset", None, None, context)
    )
    snapshot = app.create_dataset_snapshot(
        CreateDatasetSnapshotCommand(dataset.id, "a" * 64, {"split": "test"}, None, context)
    )
    artifact = _artifact(env[4], env[7], env[2], project, b"B25 run input", "other")
    run = app.create_run(
        CreateRunCommand(project, original_run.experiment_spec_version_id, "evaluation", context)
    )
    app.attach_run_dataset_input(
        AttachRunDatasetInputCommand(run.id, snapshot.id, "test", 0, 1, context)
    )
    app.attach_run_artifact_input(
        AttachRunArtifactInputCommand(run.id, ArtifactVersionId(artifact), "other", 0, 2, context)
    )
    started = app.start_run(StartRunCommand(run.id, 3, context))
    finished = app.finish_run(
        FinishRunCommand(run.id, RunStatus.SUCCEEDED, 0, None, started.row_version, context)
    )
    measurement = app.record_measurement(
        RecordMeasurementCommand(
            finished.id,
            old.metric_definition_version_id,
            1.25,
            None,
            "ms",
            {"split": "test"},
            context,
        )
    )
    result = app.record_statistical_result(
        RecordStatisticalResultCommand(
            project,
            "t_test",
            {"p": 0.01},
            {"method": "student"},
            (StatisticalResultInputCommand(measurement.id),),
            context,
        )
    )
    claim, draft = seed_claim(app, project, context)
    app.link_evidence(
        LinkEvidenceCommand(
            claim.id, draft.id, None, result.id, "supports", None, draft.row_version, context
        )
    )
    linked = app.get_current_claim_version(claim.id)
    frozen = app.freeze_claim_version(
        FreezeClaimVersionCommand(claim.id, linked.id, context, linked.row_version)
    )
    scoped_env = list(env)
    scoped_env[8] = frozen.id
    place(scoped_env)
    seal(env)
    service, q, _ = queries(env)
    before = service.get_manuscript_validity(env[3], q)
    node_id = {
        "statistical_result": result.id,
        "dataset_snapshot": snapshot.id,
        "artifact_version": artifact,
    }[affected]
    witness = next(w for w in before.witnesses if w.node.id == node_id)
    kinds = [node.kind for node in witness.occurrences[0].nodes]
    assert kinds[:3] == ["ManuscriptVersion", "ClaimVersion", "EvidenceRelation"]
    assert kinds[3] == "StatisticalResult"
    if affected != "statistical_result":
        assert kinds[4:6] == ["Measurement", "Run"]
    impact(env, affected, node_id, "invalid")
    assert service.get_manuscript_validity(env[3], q).current_validity == "INVALID"


@pytest.mark.parametrize("edge", ["predecessor", "artifact"])
def test_missing_concrete_source_edge_normalizes_to_closure(b05_env, edge, monkeypatch):
    from researchbase.persistence.source_version_repository import SqlAlchemySourceVersionRepository
    from tests.integration.phase2.b25_support import literature_conclusion, source_transition

    env = b05_env
    corrected = source_transition(env, "CORRECTED")
    literature_conclusion(env, source=corrected)
    seal(env)
    if edge == "predecessor":
        original = SqlAlchemySourceVersionRepository.version

        def version(self, identity, *args, **kwargs):
            return None if identity == env[10][7] else original(self, identity, *args, **kwargs)

        monkeypatch.setattr(SqlAlchemySourceVersionRepository, "version", version)
    else:
        monkeypatch.setattr(SqlAlchemySourceVersionRepository, "artifact_ref", lambda *args: None)
    service, q, _ = queries(env)
    with pytest.raises(ResearchBaseError) as error:
        service.get_manuscript_validity(env[3], q)
    assert error.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
