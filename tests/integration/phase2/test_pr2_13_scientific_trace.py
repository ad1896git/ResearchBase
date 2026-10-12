"""Disposable PostgreSQL contract tests for unified manuscript scientific trace."""

from __future__ import annotations

from dataclasses import replace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from researchbase.application.manuscript_placement import (
    ArtifactPlacementService,
    CitationPlacementService,
    ClaimPlacementService,
)
from researchbase.application.manuscript_scientific_trace import ManuscriptScientificTraceService
from researchbase.application.scientific_conclusion import (
    ClaimInputRequest,
    LiteratureInputRequest,
)
from researchbase.foundation.artifact_store import ContentAddressedFilesystemArtifactStore
from researchbase.foundation.errors import ResearchBaseError
from tests.integration.phase2.test_pr2_10_binding_contract import _artifact
from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE
from tests.integration.phase2.test_pr2_13_claim_placement import _draft
from tests.integration.phase2.test_pr2_13_claim_placement import (
    conclusion_env as _conclusion_env,
)
from tests.integration.phase2.test_pr2_13_claim_placement import (
    phase2_database_url as _phase2_database_url,
)

pytest_plugins = ("tests.integration.phase2.test_m3_evidence",)
pytestmark = pytest.mark.integration
conclusion_env = _conclusion_env
phase2_database_url = _phase2_database_url


def _counts(engine):
    with engine.connect() as conn:
        return tuple(conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
                     for table in (
                         "manuscript_claim_placements", "manuscript_citation_placements",
                         "manuscript_artifact_placements", "evidence_relations",
                         "literature_evidence_review_events", "scientific_conclusion_versions",
                     ))


def test_unified_trace_exact_placements_and_experiment_path(
    conclusion_env, phase2_database_url, tmp_path,
):
    (scientific, factory, engine, credentials, principal, project, claim_id,
     publication, draft) = _draft(conclusion_env, phase2_database_url, tmp_path)
    source = conclusion_env[7]
    store = ContentAddressedFilesystemArtifactStore(tmp_path / "cas")
    artifact = _artifact(factory, store, principal, project, b"Test-only figure", "figure")
    conclusion = scientific.create(
        principal, project, "Test-only synthesis", SCOPE, "MODERATE", None,
        (ClaimInputRequest(claim_id, "SUPPORTS"),), (), uuid4(),
    )
    scientific.freeze(principal, project, conclusion.conclusion_id,
                      conclusion.version_id, uuid4())
    ClaimPlacementService(factory, credentials).add(
        principal, project, publication.id, draft.id, claim_id, None,
        "RESULTS", {"kind": "PARAGRAPH", "value": "p1"}, "DESCRIPTIVE", 0, uuid4(),
    )
    ClaimPlacementService(factory, credentials).add(
        principal, project, publication.id, draft.id, None, conclusion.version_id,
        "DISCUSSION", {"kind": "PARAGRAPH", "value": "p2"}, "SUGGESTIVE", 0, uuid4(),
    )
    CitationPlacementService(factory, credentials).add(
        principal, project, publication.id, draft.id, source,
        "INTRO", {"kind": "PARAGRAPH", "value": "p3"}, "BACKGROUND", 0, uuid4(),
    )
    ArtifactPlacementService(factory, credentials).add(
        principal, project, publication.id, draft.id, artifact,
        "RESULTS", {"kind": "CAPTION", "value": "figure 1"}, "FIGURE", 0, uuid4(),
    )
    before = _counts(engine)
    trace = ManuscriptScientificTraceService(factory, credentials).trace(
        principal, project, publication.id, draft.id
    )
    assert trace.manuscript_status == "DRAFT"
    assert trace.manuscript_content_hash is None
    assert [p.placement_kind for p in trace.placements] == [
        "ARTIFACT", "CITATION", "CLAIM", "CONCLUSION",
    ]
    assert {p.target_id for p in trace.placements} == {
        source, claim_id, conclusion.version_id, artifact,
    }
    citation = next(p for p in trace.placements if p.placement_kind == "CITATION")
    assert citation.semantic == "CITATION_ONLY"
    assert citation.target_id == source
    assert trace.conclusion_claim_inputs[0].claim_version_id == claim_id
    assert trace.conclusion_claim_inputs[0].relation_type == "SUPPORTS"
    assert len(trace.claim_experiment_evidence) == 1
    assert trace.claim_experiment_evidence[0].claim_version_id == claim_id
    assert trace.claim_experiment_evidence[0].relation_type == "SUPPORTS"
    assert trace.claim_experiment_evidence[0].measurement_id is not None
    assert trace.claim_experiment_evidence[0].run_id is not None
    assert trace.literature_evidence == ()
    assert _counts(engine) == before
    engine.dispose()
    assert ManuscriptScientificTraceService(factory, credentials).trace(
        principal, project, publication.id, draft.id
    ) == trace


def test_unreviewed_contradiction_is_not_promoted_or_inferred_from_citation(
    conclusion_env, phase2_database_url, tmp_path,
):
    (scientific, factory, engine, credentials, principal, project, claim_id,
     publication, draft) = _draft(conclusion_env, phase2_database_url, tmp_path)
    evidence_service = conclusion_env[2]
    source = conclusion_env[7]
    evidence = evidence_service.create(
        principal, project, source, "improved recall", uuid4()
    )
    evidence_id = UUID(evidence["id"])
    conclusion = scientific.create(
        principal, project, "Test-only contradiction", SCOPE, "MIXED", None,
        (ClaimInputRequest(claim_id, "SUPPORTS"),),
        (LiteratureInputRequest(evidence_id, "CONTRADICTS"),), uuid4(),
    )
    scientific.freeze(principal, project, conclusion.conclusion_id,
                      conclusion.version_id, uuid4())
    ClaimPlacementService(factory, credentials).add(
        principal, project, publication.id, draft.id, None, conclusion.version_id,
        "DISCUSSION", {"kind": "SPAN", "value": "s1"}, "SUGGESTIVE", 0, uuid4(),
    )
    CitationPlacementService(factory, credentials).add(
        principal, project, publication.id, draft.id, source,
        "INTRO", {"kind": "PARAGRAPH", "value": "p1"}, "BACKGROUND", 0, uuid4(),
    )
    trace = ManuscriptScientificTraceService(factory, credentials).trace(
        principal, project, publication.id, draft.id
    )
    assert len(trace.literature_evidence) == 1
    path = trace.literature_evidence[0]
    assert path.relation_type == "CONTRADICTS"
    assert path.review_status == "UNREVIEWED"
    assert path.review_event_id is None
    assert path.evidence_id == evidence_id
    assert path.source_version_id == source
    assert len(trace.claim_experiment_evidence) == 1
    assert trace.conclusion_claim_inputs[0].relation_type == "SUPPORTS"
    with engine.connect() as conn:
        assert conn.execute(text("""SELECT count(*) FROM literature_evidence_review_events
          WHERE literature_evidence_id=:id"""), {"id": evidence_id}).scalar_one() == 0


def test_empty_duplicate_and_unauthorized_trace(
    conclusion_env, phase2_database_url, tmp_path,
):
    _, factory, engine, credentials, principal, project, claim_id, publication, draft = (
        _draft(conclusion_env, phase2_database_url, tmp_path)
    )
    service = ManuscriptScientificTraceService(factory, credentials)
    empty = service.trace(principal, project, publication.id, draft.id)
    assert empty.placements == empty.claim_experiment_evidence == ()
    with pytest.raises(ResearchBaseError):
        service.trace(replace(principal, actor_id=uuid4()), project,
                      publication.id, draft.id)
    with pytest.raises(ResearchBaseError):
        service.trace(principal, uuid4(), publication.id, draft.id)
    with pytest.raises(ResearchBaseError):
        service.trace(principal, project, publication.id, uuid4())
    place = ClaimPlacementService(factory, credentials)
    for section in ("DISCUSSION", "RESULTS"):
        place.add(principal, project, publication.id, draft.id, claim_id, None,
                  section, {"kind": "ANCHOR", "value": section},
                  "DESCRIPTIVE", 0, uuid4())
    trace = service.trace(principal, project, publication.id, draft.id)
    assert len(trace.placements) == 2
    assert len(trace.claim_experiment_evidence) == 1
    assert [p.section_id for p in trace.placements] == ["DISCUSSION", "RESULTS"]
    assert _counts(engine)[0] == 2
