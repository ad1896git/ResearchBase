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
from tests.integration.phase2.test_b04_manuscript_freeze import b04_env as _b04_env

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


def test_g5_application_freeze_retains_exact_scientific_paths(b04_env):
    from uuid import UUID

    from researchbase.application.scientific_conclusion import (
        ClaimInputRequest,
        LiteratureInputRequest,
    )
    from tests.integration.phase2.test_b04_manuscript_freeze import freeze
    from tests.integration.phase2.test_pr2_11_r2_persistence import SCOPE

    service, q, actor, factory, engine, credentials, store, claim, base = b04_env
    scientific, _, evidence_service, _, reviewer, project, _, source, _, _ = base
    evidence = evidence_service.create(actor, project, source, "improved recall", uuid4())
    evidence_id = UUID(evidence["id"])
    evidence_service.review(
        reviewer, project, evidence_id, "VERIFIED", "Test-only independent inspection", uuid4()
    )
    snapshot = evidence_service.snapshot(
        actor,
        project,
        "ClaimVersion",
        claim,
        [
            {
                "evidence_id": str(evidence_id),
                "relation_type": "SUPPORTS",
                "qualification": "Test support",
            }
        ],
        uuid4(),
    )
    direct_evidence = evidence_service.create(actor, project, source, "measured effect", uuid4())
    direct_id = UUID(direct_evidence["id"])
    evidence_service.review(
        reviewer, project, direct_id, "VERIFIED", "Independent inspection", uuid4()
    )
    conclusion = scientific.create(
        actor,
        project,
        "Test synthesis",
        SCOPE,
        "MODERATE",
        None,
        (ClaimInputRequest(claim, "SUPPORTS", UUID(snapshot["id"])),),
        (LiteratureInputRequest(direct_id, "SUPPORTS"),),
        uuid4(),
    )
    scientific.freeze(actor, project, conclusion.conclusion_id, conclusion.version_id, uuid4())
    placements = ClaimPlacementService(factory, credentials, store)
    placements.add(
        actor,
        project,
        q.publication_id,
        q.manuscript_version_id,
        claim,
        None,
        "RESULTS",
        {"kind": "PARAGRAPH", "value": "p1"},
        "SUPPORTED",
        0,
        uuid4(),
    )
    placements.add(
        actor,
        project,
        q.publication_id,
        q.manuscript_version_id,
        None,
        conclusion.version_id,
        "DISCUSSION",
        {"kind": "PARAGRAPH", "value": "p2"},
        "SUPPORTED",
        0,
        uuid4(),
    )
    CitationPlacementService(factory, credentials, store).add(
        actor,
        project,
        q.publication_id,
        q.manuscript_version_id,
        source,
        "INTRO",
        {"kind": "PARAGRAPH", "value": "p1"},
        "BACKGROUND",
        0,
        uuid4(),
    )
    from hashlib import sha256

    from researchbase.application.manuscript_placement import ArtifactPlacementService
    from researchbase.foundation.hashing import sha256_canonical_json
    from tests.integration.phase2.test_pr2_10_binding_contract import _artifact

    figure_bytes = b"B30 retained exact figure"
    figure_hash = sha256(figure_bytes).hexdigest()
    figure = _artifact(factory, store, actor, project, figure_bytes, "figure")
    ArtifactPlacementService(factory, credentials, store).add(
        actor,
        project,
        q.publication_id,
        q.manuscript_version_id,
        figure,
        "RESULTS",
        {"kind": "CAPTION", "value": "f1"},
        "FIGURE",
        0,
        uuid4(),
    )
    with engine.connect() as conn:
        exact_hashes = {}
        for table, identity in (
            ("claim_versions", claim),
            ("scientific_conclusion_versions", conclusion.version_id),
            ("source_versions", source),
        ):
            exact_hashes[identity] = conn.execute(
                text(f"SELECT content_hash FROM {table} WHERE id=:id"), {"id": identity}
            ).scalar_one()
        row = (
            conn.execute(
                text("SELECT * FROM manuscript_versions WHERE id=:id"),
                {"id": q.manuscript_version_id},
            )
            .mappings()
            .one()
        )
        document_hash = conn.execute(
            text("SELECT content_hash FROM artifact_versions WHERE id=:id"),
            {"id": row["document_artifact_version_id"]},
        ).scalar_one()

    def ref(kind, identity, digest):
        return {"type": kind, "id": str(identity), "content_hash": digest}

    expected_placements = str(
        sha256_canonical_json(
            {
                "type": "ManuscriptVersionPlacementSet",
                "material_version": 1,
                "claim_placements": [
                    {
                        "target": ref(
                            "ScientificConclusionVersion",
                            conclusion.version_id,
                            exact_hashes[conclusion.version_id],
                        ),
                        "section_id": "DISCUSSION",
                        "locator": {"kind": "PARAGRAPH", "value": "p2"},
                        "rhetorical_strength": "SUPPORTED",
                        "ordinal": 0,
                    },
                    {
                        "target": ref("ClaimVersion", claim, exact_hashes[claim]),
                        "section_id": "RESULTS",
                        "locator": {"kind": "PARAGRAPH", "value": "p1"},
                        "rhetorical_strength": "SUPPORTED",
                        "ordinal": 0,
                    },
                ],
                "citation_placements": [
                    {
                        "source_version": ref("SourceVersion", source, exact_hashes[source]),
                        "section_id": "INTRO",
                        "locator": {"kind": "PARAGRAPH", "value": "p1"},
                        "citation_purpose": "BACKGROUND",
                        "ordinal": 0,
                    }
                ],
                "artifact_placements": [
                    {
                        "artifact_version": ref("ArtifactVersion", figure, figure_hash),
                        "section_id": "RESULTS",
                        "locator": {"kind": "CAPTION", "value": "f1"},
                        "artifact_role": "FIGURE",
                        "ordinal": 0,
                    }
                ],
            }
        )
    )
    expected_content = str(
        sha256_canonical_json(
            {
                "type": "ManuscriptVersion",
                "material_version": 1,
                "publication_id": str(q.publication_id),
                "document_artifact": ref(
                    "ArtifactVersion", row["document_artifact_version_id"], document_hash
                ),
                "title": row["title"],
                "abstract": row["abstract"],
                "semantic_change_class": row["semantic_change_class"],
                "placement_set_hash": expected_placements,
            }
        )
    )
    trace_service = ManuscriptScientificTraceService(factory, credentials, store)
    before = trace_service.trace(actor, project, q.publication_id, q.manuscript_version_id)
    from researchbase.persistence.manuscript_freeze_repository import B04_SNAPSHOT_TABLES
    from tests.integration.phase2.b30_observations import (
        assert_first_share,
        assert_snapshot_read,
        sql_protocol,
    )

    with sql_protocol(engine) as observed:
        frozen = freeze(service, actor, q)
    assert_first_share(observed, "LOCK TABLE " + ",".join(B04_SNAPSHOT_TABLES) + " IN SHARE MODE")
    assert (frozen.placement_set_hash, frozen.content_hash) == (
        expected_placements,
        expected_content,
    )
    assert store.verify(figure_hash) and store.open(figure_hash) == figure_bytes
    after = trace_service.trace(actor, project, q.publication_id, q.manuscript_version_id)
    assert (
        after.manuscript_status == "FROZEN" and after.manuscript_content_hash == frozen.content_hash
    )
    assert before.placements == after.placements
    assert {x.link_kind for x in after.literature_evidence} == {
        "CLAIM_SNAPSHOT",
        "CONCLUSION_INPUT",
    }
    assert after.claim_experiment_evidence and after.conclusion_claim_inputs
    assert all(
        store.verify(x.target_content_hash)
        for x in after.placements
        if x.placement_kind == "ARTIFACT"
    )
    assert {x.target_id for x in after.placements} == {claim, conclusion.version_id, source, figure}
    from researchbase.application.manuscript_freeze import ManuscriptFreezeService

    with sql_protocol(engine) as observed:
        assert (
            ManuscriptFreezeService(factory, credentials, store).get_manuscript_version(actor, q)
            == frozen
        )
        assert (
            ManuscriptScientificTraceService(factory, credentials, store).trace(
                actor, project, q.publication_id, q.manuscript_version_id
            )
            == after
        )
    assert_snapshot_read(observed)


b04_env = _b04_env
