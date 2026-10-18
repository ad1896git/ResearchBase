"""Exact explanation, complete governance history, integrity and no write effects."""

from dataclasses import replace
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.finding_impact import (
    FindingImpactService,
    GetFindingManuscriptImpactQuery,
)
from researchbase.application.governance import (
    CreateAuditFindingCommand,
    CreateCorrectionRecordCommand,
    CreateImpactAssessmentCommand,
    GovernanceService,
    ProposedImpactTarget,
    TransitionAuditFindingCommand,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from researchbase.foundation.execution_context import ExecutionContext
from researchbase.foundation.time import SystemClock
from tests.integration.phase2.b25_support import (
    impact,
    literature_conclusion,
    place,
    source_transition,
)
from tests.integration.phase2.test_b05_manuscript_review import seal
from tests.integration.phase2.test_b25_manuscript_validity import (
    b04_env,
    b05_env,
    conclusion_env,
    phase2_database_url,
)

__all__ = ["b04_env", "b05_env", "conclusion_env", "phase2_database_url"]
pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration


def context(env):
    return ExecutionContext(actor_id=env[2].actor_id, request_id=uuid4(), client_type="test")


def selected(env, kind="claim_version", identity=None):
    return GovernanceService(env[4], SystemClock()).create_audit_finding(
        CreateAuditFindingCommand(
            env[1].project_id,
            "B26",
            "major",
            "Selected concern",
            "Recorded concern",
            kind,
            identity or env[8],
            context(env),
        )
    )


def assessment(env, finding, conclusion="invalid", targets=None):
    return GovernanceService(env[4], SystemClock()).create_impact_assessment(
        CreateImpactAssessmentCommand(
            env[1].project_id,
            finding.id,
            {"test": "B26"},
            conclusion,
            targets
            if targets is not None
            else (ProposedImpactTarget(finding.target_type, finding.target_id, "direct"),),
            context(env),
        )
    )


def query(env, finding):
    q = env[1]
    return FindingImpactService(env[4], env[9], env[7]), GetFindingManuscriptImpactQuery(
        q.project_id,
        finding.id,
        q.publication_id,
        q.manuscript_version_id,
    )


def counts(env):
    with env[5].connect() as conn:
        return tuple(
            conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
            for table in (
                "audit_findings",
                "impact_assessments",
                "impact_targets",
                "correction_records",
                "manuscript_versions",
                "manuscript_claim_placements",
                "literature_evidence_review_events",
            )
        )


@pytest.mark.parametrize("status", ["open", "confirmed", "resolved", "dismissed"])
@pytest.mark.parametrize(
    "conclusion", ["no_impact", "stale", "invalid", "requires_review", "unknown"]
)
def test_historical_status_conclusion_and_exact_occurrences(b05_env, status, conclusion):
    env = b05_env
    place(env, ordinal=0)
    place(env, ordinal=1)
    place(env, conclusion=True, ordinal=0)
    sealed = seal(env)
    f = selected(env)
    a = assessment(env, f, conclusion)
    service = GovernanceService(env[4], SystemClock())
    if status in {"confirmed", "resolved"}:
        f = service.transition_audit_finding(
            TransitionAuditFindingCommand(f.id, "confirmed", f.row_version, context(env))
        )
    if status in {"resolved", "dismissed"}:
        f = service.transition_audit_finding(
            TransitionAuditFindingCommand(f.id, status, f.row_version, context(env))
        )
    reader, q = query(env, f)
    before = counts(env)
    result = reader.get_finding_manuscript_impact(env[3], q)
    again = reader.get_finding_manuscript_impact(env[3], q)
    assert counts(env) == before
    assert result == replace(
        again, validity=replace(again.validity, evaluated_at=result.validity.evaluated_at)
    )
    assert result.finding == f and result.assessments == (a,)
    assert len(result.matches) == 2
    assert all(len(m.occurrences) == 3 for m in result.matches)
    assert result.validity.current_validity == (
        "VALID"
        if status == "dismissed" or conclusion == "no_impact"
        else "INVALID"
        if conclusion == "invalid"
        else "STALE"
    )
    assert result.validity.content_hash == sealed.content_hash
    assert result.validity.placement_set_hash == sealed.placement_set_hash


def test_conflicting_assessments_correction_and_unlinked_state(b05_env):
    env = b05_env
    place(env)
    seal(env)
    f = selected(env)
    first = assessment(env, f)
    second = assessment(env, f, "no_impact")
    GovernanceService(env[4], SystemClock()).create_correction_record(
        CreateCorrectionRecordCommand(
            env[1].project_id,
            f.target_type,
            f.target_id,
            "factual",
            {"note": "retained"},
            "Correction",
            context(env),
        )
    )
    other = selected(env)
    assessment(env, other, "stale")
    impact(env, "claim_version", env[8], "invalid")
    reader, q = query(env, f)
    result = reader.get_finding_manuscript_impact(env[2], q)
    assert [a.id for a in result.assessments] == [first.id, second.id]
    assert result.validity.current_validity == "INVALID"
    assert len(result.matches) == 3


@pytest.mark.parametrize("reachable", [False, True])
def test_unassessed_zero_match_is_complete_success(b05_env, reachable):
    env = b05_env
    if reachable:
        place(env)
    seal(env)
    f = selected(env)
    reader, q = query(env, f)
    result = reader.get_finding_manuscript_impact(env[2], q)
    assert result.assessments == ()
    assert len(result.matches) == int(reachable)
    assert result.validity.current_validity == "VALID"


@pytest.mark.parametrize("change", ["RETRACTED", "DISPUTED"])
def test_literature_bound_claim_validity_without_fabricated_records(b05_env, change):
    env = b05_env
    evidence, _, _ = literature_conclusion(env, snapshot=True)
    seal(env)
    f = selected(env)
    reader, q = query(env, f)
    before = reader.get_finding_manuscript_impact(env[2], q)
    initial_counts = counts(env)[:4]
    if change == "RETRACTED":
        source_transition(env, change)
    else:
        env[10][2].review(env[3], q.project_id, evidence, "DISPUTED", "Later dispute", uuid4())
    after = reader.get_finding_manuscript_impact(env[2], q)
    assert after.validity.current_validity == ("INVALID" if change == "RETRACTED" else "STALE")
    assert before.matches == after.matches and after.assessments == ()
    assert counts(env)[:4] == initial_counts


@pytest.mark.parametrize(
    "failure",
    [
        "finding",
        "foreign_finding",
        "publication",
        "manuscript",
        "draft",
        "principal",
        "credential",
        "bytes",
    ],
)
def test_root_policy_and_cas_failures(b05_env, failure, monkeypatch):
    env = b05_env
    f = selected(env)
    if failure != "draft":
        seal(env)
    reader, q = query(env, f)
    principal: Any = env[2]
    if failure in {"finding", "publication", "manuscript"}:
        q = replace(
            q,
            **{
                {
                    "finding": "finding_id",
                    "publication": "publication_id",
                    "manuscript": "manuscript_version_id",
                }[failure]: uuid4()
            },
        )
    if failure == "foreign_finding":
        with env[5].begin() as conn:
            conn.execute(text("SET LOCAL session_replication_role='replica'"))
            conn.execute(
                text("UPDATE audit_findings SET project_id=:project WHERE id=:id"),
                {"project": uuid4(), "id": f.id},
            )
    if failure == "principal":
        principal = None
    if failure == "credential":
        principal = replace(principal, credential_id=str(uuid4()))
    if failure == "bytes":
        monkeypatch.setattr(env[7], "verify", lambda *args: False)
    initial = counts(env)
    with pytest.raises(ResearchBaseError) as error:
        reader.get_finding_manuscript_impact(principal, q)
    assert error.value.code == {
        "draft": ErrorCode.VERSION_NOT_FROZEN,
        "principal": ErrorCode.AUTHENTICATION_REQUIRED,
        "credential": ErrorCode.FORBIDDEN,
        "bytes": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
    }.get(failure, ErrorCode.NOT_FOUND)
    assert counts(env) == initial


@pytest.mark.parametrize(
    "failure",
    [
        "finding_hash",
        "assessment_hash",
        "target_hash",
        "missing_target",
        "foreign_child",
        "incomplete_targets",
        "enum",
    ],
)
def test_saved_corruption_fails_closed(b05_env, failure):
    env = b05_env
    place(env)
    seal(env)
    f = selected(env)
    assessment(env, f)
    with env[5].begin() as conn:
        conn.execute(text("SET LOCAL session_replication_role='replica'"))
        sql = {
            "finding_hash": "UPDATE audit_findings SET target_content_hash=repeat('0',64)",
            "assessment_hash": "UPDATE impact_assessments SET content_hash=repeat('0',64)",
            "target_hash": "UPDATE impact_targets SET target_content_hash=repeat('0',64)",
            "missing_target": "UPDATE audit_findings SET target_id=gen_random_uuid()",
            "foreign_child": "UPDATE impact_assessments SET project_id=gen_random_uuid()",
            "incomplete_targets": "DELETE FROM impact_targets",
            "enum": "UPDATE audit_findings SET status='BROKEN'",
        }[failure]
        if failure == "enum":
            conn.execute(
                text("ALTER TABLE audit_findings DROP CONSTRAINT ck_audit_findings_status")
            )
        conn.execute(text(sql))
    reader, q = query(env, f)
    initial = counts(env)
    with pytest.raises(ResearchBaseError) as error:
        reader.get_finding_manuscript_impact(env[3], q)
    assert error.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION
    assert counts(env) == initial


def test_citation_artifact_and_retained_predecessor_navigation(b05_env):
    from researchbase.application.manuscript_placement import (
        ArtifactPlacementService,
        CitationPlacementService,
    )
    from tests.integration.phase2.b25_support import queries

    env = b05_env
    corrected = source_transition(env, "CORRECTED")
    q = env[1]
    CitationPlacementService(env[4], env[9]).add(
        env[2],
        q.project_id,
        q.publication_id,
        q.manuscript_version_id,
        corrected,
        "INTRO",
        {"kind": "PARAGRAPH", "value": "citation"},
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
        {"kind": "ANCHOR", "value": "document"},
        "OTHER",
        0,
        uuid4(),
    )
    seal(env)
    owner, vq, _ = queries(env)
    baseline = owner.get_manuscript_validity(env[3], vq)
    assert any(
        w.node.id == env[10][7] and any(n.id == corrected for n in w.occurrences[0].nodes)
        for w in baseline.witnesses
        if w.node.kind == "SourceVersion"
    )
    # The fulltext artifact retains current and predecessor citation occurrences.
    artifact = next(
        w
        for w in baseline.witnesses
        if w.node.kind == "ArtifactVersion"
        and any(any(n.id == env[10][7] for n in p.nodes) for p in w.occurrences)
    )
    f = selected(env, "artifact_version", artifact.node.id)
    a = assessment(env, f, "no_impact")
    reader, fq = query(env, f)
    result = reader.get_finding_manuscript_impact(env[3], fq)
    assert result.validity.current_validity == "VALID"
    assert all(m.occurrences == artifact.occurrences for m in result.matches)
    assert result.assessments == (a,)
    assert not any(w.node.kind == "ClaimVersion" for w in result.validity.witnesses)
    # Document has distinct root-document and explicit artifact-placement occurrences.
    document_finding = selected(env, "artifact_version", document)
    result = reader.get_finding_manuscript_impact(
        env[3], replace(fq, finding_id=document_finding.id)
    )
    assert {p.placement_kind for p in result.matches[0].occurrences} == {None, "ARTIFACT"}


@pytest.mark.parametrize("inventory", ["assessments", "targets"])
def test_database_inventory_ceiling_before_hydration(b05_env, inventory, monkeypatch):
    from researchbase.persistence.governance_repository import SqlAlchemyGovernanceRepository

    env = b05_env
    seal(env)
    f = selected(env)
    a = assessment(env, f)
    with env[5].begin() as conn:
        conn.execute(text("SET LOCAL session_replication_role='replica'"))
        if inventory == "assessments":
            conn.execute(
                text("""INSERT INTO impact_assessments
                (id,project_id,audit_finding_id,assessment_payload,conclusion,created_by,created_at,content_hash)
                SELECT gen_random_uuid(),project_id,audit_finding_id,assessment_payload,conclusion,
                    created_by,created_at,content_hash FROM impact_assessments
                CROSS JOIN generate_series(1,10000)
                WHERE id=:id"""),
                {"id": a.id},
            )
        else:
            conn.execute(
                text("""INSERT INTO impact_targets
                (impact_assessment_id,target_type,target_id,target_content_hash,impact_kind)
                SELECT :id,'RUN',gen_random_uuid(),NULL,'DIRECT' FROM generate_series(1,10000)"""),
                {"id": a.id},
            )
    monkeypatch.setattr(
        SqlAlchemyGovernanceRepository,
        "get_impact_assessment",
        lambda *args: pytest.fail("hydrated over-ceiling inventory"),
    )
    reader, q = query(env, f)
    with pytest.raises(ResearchBaseError, match="ceiling") as error:
        reader.get_finding_manuscript_impact(env[3], q)
    assert error.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


def test_unreachable_linked_target_is_still_verified(b05_env):
    env = b05_env
    seal(env)
    f = selected(env)
    assessment(env, f)
    with env[5].begin() as conn:
        conn.execute(text("SET LOCAL session_replication_role='replica'"))
        conn.execute(text("UPDATE impact_targets SET target_id=gen_random_uuid()"))
    reader, q = query(env, f)
    with pytest.raises(ResearchBaseError) as error:
        reader.get_finding_manuscript_impact(env[3], q)
    assert error.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


@pytest.mark.parametrize("paths", [5000, 5001])
def test_combined_response_budget_on_prepared_database_snapshot(b05_env, paths, monkeypatch):
    from researchbase.application.manuscript_validity import AuditOccurrence

    env = b05_env
    place(env)
    seal(env)
    f = selected(env)
    reader, q = query(env, f)
    original = reader._validity.build_in_uow

    def build(*args):
        validity = original(*args)
        witness = next(w for w in validity.witnesses if w.node.id == f.target_id)
        occurrence = witness.occurrences[0]
        # Isolate the composition's response budget from the already-tested owner visitor.
        occurrences = tuple(
            AuditOccurrence("CLAIM", uuid4(), occurrence.nodes) for _ in range(paths)
        )
        return replace(validity, witnesses=(replace(witness, occurrences=occurrences),))

    monkeypatch.setattr(reader._validity, "build_in_uow", build)
    if paths == 5000:
        result = reader.get_finding_manuscript_impact(env[3], q)
        assert (
            sum(len(w.occurrences) for w in result.validity.witnesses)
            + sum(len(m.occurrences) for m in result.matches)
            == 10000
        )
    else:
        with pytest.raises(ResearchBaseError, match="ceiling") as error:
            reader.get_finding_manuscript_impact(env[3], q)
        assert error.value.code == ErrorCode.PROVENANCE_CLOSURE_VIOLATION


@pytest.mark.parametrize("other_kind", ["unlinked", "other_finding", "empty_selected"])
def test_selected_history_does_not_claim_other_invalidity(b05_env, other_kind):
    env = b05_env
    place(env)
    seal(env)
    f = selected(env)
    if other_kind == "other_finding":
        assessment(env, selected(env))
    else:
        impact(env, "claim_version", env[8], "invalid")
    empty = assessment(env, f, "no_impact", targets=()) if other_kind == "empty_selected" else None
    reader, q = query(env, f)
    result = reader.get_finding_manuscript_impact(env[3], q)
    assert result.validity.current_validity == "INVALID"
    assert result.assessments == ((empty,) if empty else ())
    assert len(result.matches) == 1 and result.matches[0].basis == "FINDING_TARGET"
