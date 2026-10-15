"""F3 draft citation placement cannot establish scientific support."""

from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.manuscript_placement import (
    CitationPlacementService,
    ClaimPlacementService,
)
from researchbase.application.manuscript_scientific_trace import ManuscriptScientificTraceService
from tests.integration.phase2 import test_pr2_13_scientific_trace as trace_cases
from tests.integration.phase2.pr2_19_support import conclusion_env as _conclusion_env
from tests.integration.phase2.pr2_19_support import counts
from tests.integration.phase2.pr2_19_support import m3 as _m3
from tests.integration.phase2.pr2_19_support import phase2_database_url as _phase2_database_url
from tests.integration.phase2.pr2_19_support import pr219_trace_env as _pr219_trace_env

pytestmark = pytest.mark.integration


def test_citation_only_preserves_claim_hashes_and_numeric_facts(pr219_trace_env):
    base, draft_env = pr219_trace_env
    _, factory, engine, credentials, actor, project, claim, publication, draft = draft_env
    with engine.connect() as conn:
        hashes = conn.execute(
            text("SELECT content_hash,support_set_hash FROM claim_versions WHERE id=:id"),
            {"id": claim},
        ).one()
        measurements = conn.execute(text("SELECT * FROM measurements ORDER BY id")).all()
    before = counts(engine)
    citation = CitationPlacementService(factory, credentials).add(
        actor,
        project,
        publication.id,
        draft.id,
        base[7],
        "INTRO",
        {"kind": "PARAGRAPH", "value": "p1"},
        "BACKGROUND",
        0,
        uuid4(),
    )
    ClaimPlacementService(factory, credentials).add(
        actor,
        project,
        publication.id,
        draft.id,
        claim,
        None,
        "RESULTS",
        {"kind": "PARAGRAPH", "value": "p2"},
        "DESCRIPTIVE",
        0,
        uuid4(),
    )
    service = ManuscriptScientificTraceService(factory, credentials)
    trace = service.trace(actor, project, publication.id, draft.id)
    cited = next(item for item in trace.placements if item.placement_kind == "CITATION")
    assert cited.semantic == "CITATION_ONLY" and cited.target_id == base[7]
    assert trace.literature_evidence == ()
    assert len(trace.claim_experiment_evidence) == 1
    assert trace.claim_experiment_evidence[0].measurement_id is not None
    assert counts(engine) == before
    with engine.connect() as conn:
        assert (
            conn.execute(
                text("SELECT content_hash,support_set_hash FROM claim_versions WHERE id=:id"),
                {"id": claim},
            ).one()
            == hashes
        )
        assert conn.execute(text("SELECT * FROM measurements ORDER BY id")).all() == measurements
    assert (
        ManuscriptScientificTraceService(factory, credentials).trace(
            actor, project, publication.id, draft.id
        )
        == trace
    )
    assert citation is not None


def test_experiment_and_literature_trace_paths_remain_separate(
    conclusion_env, phase2_database_url, tmp_path
):
    trace_cases.test_unreviewed_contradiction_is_not_promoted_or_inferred_from_citation(
        conclusion_env, phase2_database_url, tmp_path
    )


# Register imported fixtures explicitly, matching the existing Phase 2 layout.
conclusion_env = _conclusion_env
m3 = _m3
phase2_database_url = _phase2_database_url
pr219_trace_env = _pr219_trace_env
