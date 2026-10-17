"""Only inconclusive exact-Claim assessments and append-only chain navigation."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.novelty import (
    ExactReadQuery,
    RecordNoveltyAssessmentCommand,
    RecordSearchCoverageCommand,
)
from researchbase.domain.novelty import NoveltyOutcome
from researchbase.foundation.errors import ErrorCode, ResearchBaseError

pytest_plugins = ("tests.integration.phase2.pr2_18_fixtures",)


def test_inconclusive_chain_and_roots(novelty_env):
    e = novelty_env
    cov = e["service"].record_search_coverage(
        e["author"],
        RecordSearchCoverageCommand(
            uuid4(), e["project"], e["plan"], e["executions"], "Selected scope, no screening."
        ),
    )
    c = RecordNoveltyAssessmentCommand(
        uuid4(),
        e["project"],
        e["claim"],
        cov.id,
        NoveltyOutcome.INCONCLUSIVE,
        "Insufficient inspected coverage.",
    )
    root = e["service"].record_novelty_assessment(e["author"], c)
    successor = e["service"].record_novelty_assessment(
        e["author"],
        replace(c, id=uuid4(), supersedes_assessment_id=root.id, limitations="Corrected limits."),
    )
    independent = e["service"].record_novelty_assessment(e["author"], replace(c, id=uuid4()))
    old = e["service"].read_novelty_assessment(e["author"], ExactReadQuery(e["project"], root.id))
    assert old.superseded_by_assessment_id == successor.id
    assert successor.supersedes_assessment_id == root.id
    assert independent.supersedes_assessment_id is None
    with pytest.raises(ResearchBaseError) as error:
        e["service"].record_novelty_assessment(
            e["author"], replace(c, id=uuid4(), supersedes_assessment_id=root.id)
        )
    assert error.value.code is ErrorCode.INVALID_STATE_TRANSITION


@pytest.mark.parametrize(
    "outcome",
    [NoveltyOutcome.CLOSE_PRIOR_ART_FOUND, NoveltyOutcome.NO_CLOSE_PRIOR_ART_WITHIN_COVERAGE],
)
def test_stronger_outcome_denied_before_inputs(novelty_env, outcome):
    e = novelty_env
    c = RecordNoveltyAssessmentCommand(
        uuid4(), e["project"], e["claim"], uuid4(), outcome, "No such basis has been approved."
    )
    with pytest.raises(ResearchBaseError) as error:
        e["service"].record_novelty_assessment(e["author"], c)
    assert error.value.code is ErrorCode.INVALID_STATE_TRANSITION
    with e["engine"].connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM novelty_assessments")).scalar_one() == 0


def test_later_retraction_warns_without_rewriting_history(novelty_env):
    from uuid import UUID

    from researchbase.application.source_version import (
        CreateSourceVersion,
        SourceVersionService,
        TransitionSourceVersion,
    )
    from researchbase.domain.novelty import QualityWarning
    from researchbase.domain.source_version import (
        FrozenSourceReference,
        SourceVersionKind,
        SourceVersionMaterial,
    )
    from tests.integration.phase2.pr2_18_fixtures import add_resolution

    e = novelty_env
    add_resolution(e, e["results"][0])
    cov = e["service"].record_search_coverage(
        e["author"],
        RecordSearchCoverageCommand(
            uuid4(), e["project"], e["plan"], e["executions"], "Selected prior work."
        ),
    )
    c = RecordNoveltyAssessmentCommand(
        uuid4(),
        e["project"],
        e["claim"],
        cov.id,
        NoveltyOutcome.INCONCLUSIVE,
        "Insufficient coverage.",
    )
    before = e["service"].record_novelty_assessment(e["author"], c)
    with e["factory"]() as uow:
        old = uow.source_version.version(e["source"])
        artifact = uow.literature_evidence.artifact(
            old["fulltext_artifact_version_id"], e["project"]
        )
    versions = SourceVersionService(e["factory"], e["credentials"])
    draft = versions.create(
        CreateSourceVersion(
            e["author"],
            e["project"],
            SourceVersionMaterial(
                old["literature_source_id"],
                SourceVersionKind.RETRACTED,
                FrozenSourceReference(e["source"], old["content_hash"]),
                FrozenSourceReference(artifact["id"], artifact["content_hash"]),
                "Retraction notice",
                None,
                (),
                None,
                None,
                None,
                None,
                None,
            ),
            uuid4(),
        )
    )
    versions.freeze(
        TransitionSourceVersion(
            e["author"], e["project"], UUID(str(draft["source_version_id"])), uuid4()
        )
    )
    after = e["service"].read_novelty_assessment(e["author"], ExactReadQuery(e["project"], c.id))
    assert after.content_hash == before.content_hash
    assert after.search_coverage.content_hash == cov.content_hash
    assert after.search_coverage.resolved_source_count == 1
    assert not after.current_validity.usable_for_current_judgment
    assert QualityWarning.INPUT_CURRENTLY_UNUSABLE in after.search_coverage.quality.warnings
    assert (
        e["service"].record_novelty_assessment(e["author"], c).content_hash == before.content_hash
    )
