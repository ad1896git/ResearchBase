"""G3: fixed RAG candidate to independently verified exact evidence."""

from uuid import UUID, uuid4

import pytest

from researchbase.application.literature_evidence import LiteratureEvidenceService
from researchbase.application.scientific_rag_provider import (
    FakeScientificRAGCapability,
    SourceLocator,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.pr2_19_support import CORPUS, counts
from tests.integration.phase2.pr2_19_support import m3 as _m3
from tests.integration.phase2.pr2_19_support import phase2_database_url as _phase2_database_url
from tests.integration.phase2.pr2_19_support import pr219_candidate_env as _pr219_candidate_env
from tests.integration.phase2.pr2_19_support import pr219_evidence_env as _pr219_evidence_env
from tests.unit.phase2.test_pr2_07_scientific_rag_boundary import context, request, response

pytestmark = pytest.mark.integration


def test_retrieval_then_owning_admission_independent_human_review_restart(pr219_candidate_env):
    env, sources = pr219_candidate_env
    service, author, reviewer, project, _, hypothesis, document, engine, credentials = env
    before = counts(engine)
    provider = FakeScientificRAGCapability(
        response(
            sources[0],
            locator=SourceLocator(paragraph="1", quote_span="char:18:33"),
            excerpt="improved recall",
        )
    )
    item = provider.answer(request(sources), context()).evidence_candidates[0]
    assert CORPUS[0].split(b"\n\n")[0][18:33] == item.excerpt.encode()
    assert counts(engine) == before
    evidence = service.create(
        author,
        project,
        item.source_version_id,
        item.excerpt,
        uuid4(),
        paragraph=1,
        start=18,
        end=33,
    )
    eid = UUID(evidence["id"])
    assert evidence["artifact_version_id"] == document["artifact_version_id"]
    with pytest.raises(ResearchBaseError) as denied:
        service.review(author, project, eid, "VERIFIED", "Self verification", uuid4())
    assert denied.value.code is ErrorCode.FORBIDDEN
    assert author.actor_id != reviewer.actor_id
    reviewed = service.review(
        reviewer, project, eid, "VERIFIED", "Inspected independent fixture bytes", uuid4()
    )
    snapshot = service.snapshot(
        author,
        project,
        "HypothesisVersion",
        hypothesis,
        [
            {
                "evidence_id": evidence["id"],
                "relation_type": "SUPPORTS",
                "qualification": "Exact test passage",
            }
        ],
        uuid4(),
    )
    fresh = LiteratureEvidenceService(service._factory, credentials, service._store)
    assert fresh.get(author, project, eid) == reviewed
    assert fresh.get_snapshot(author, project, UUID(snapshot["id"])) == snapshot
    assert snapshot["relations"][0]["literature_evidence_id"] == evidence["id"]
    assert counts(engine)["literature_evidence_review_events"] == 1
    import hashlib

    from tests.integration.phase2.pr2_19_support import (
        REPORT_ROOT,
        ScenarioObservation,
        StateDelta,
        VerifiedHash,
        emit_observation,
    )

    after = counts(engine)
    emit_observation(
        ScenarioObservation(
            "G3",
            0,
            "LiteratureEvidenceService.snapshot",
            (eid, UUID(snapshot["id"])),
            None,
            tuple(StateDelta(table, before[table], after[table]) for table in before),
            (
                VerifiedHash(
                    UUID(document["artifact_version_id"]),
                    "content_hash",
                    hashlib.sha256(CORPUS[0]).hexdigest(),
                    document["content_hash"],
                ),
            ),
            (),
            (),
            (REPORT_ROOT / "focused.xml",),
        )
    )


# Register imported fixtures explicitly, matching the existing Phase 2 layout.
m3 = _m3
phase2_database_url = _phase2_database_url
pr219_candidate_env = _pr219_candidate_env
pr219_evidence_env = _pr219_evidence_env
