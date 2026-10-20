"""Re-review is exact correspondence, including rejection and uncertainty."""

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from researchbase.application.internal_review import InternalReviewService, ReviewIssueRequest
from researchbase.application.revision_action import (
    RecordConcernReReviewCommand,
    RecordNoveltyRevisionCommand,
    RevisionActionService,
)
from researchbase.foundation.errors import ErrorCode, ResearchBaseError
from tests.integration.phase2.test_b23_novelty_review import _review, _root


@pytest.mark.parametrize("recommendation", ["ACCEPT", "MINOR_REVISION", "REJECT", "UNCERTAIN"])
def test_correspondence_keeps_open_issues(novelty_env, recommendation):
    e = novelty_env
    c, root = _root(e)
    _, old = _review(e, root)
    result = e["service"].record_novelty_assessment(
        e["author"], replace(c, id=uuid4(), supersedes_assessment_id=root.id)
    )
    service = RevisionActionService(e["factory"], e["credentials"], e["literature"])
    action = service.record_novelty_revision(
        e["author"],
        RecordNoveltyRevisionCommand(uuid4(), e["project"], old.issues[0].id, result.id),
    )
    reviews = InternalReviewService(e["factory"], e["credentials"], e["literature"])
    review = reviews.create(
        e["reviewer"],
        e["project"],
        "NOVELTY_ASSESSMENT",
        result.id,
        "SCIENTIFIC",
        recommendation,
        "Independent result review.",
        (ReviewIssueRequest("MINOR", "NOVELTY", "Limitations remain."),),
        uuid4(),
    )
    command = RecordConcernReReviewCommand(e["project"], action.id, review.id)
    link = service.record_concern_re_review(e["reviewer"], command, novelty=True)
    assert link.review.issues[0].status == "OPEN"
    assert (
        service.record_concern_re_review(e["reviewer"], command, novelty=True).recorded_at
        == link.recorded_at
    )
    with e["engine"].connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM review_issues WHERE status='OPEN'")
            ).scalar_one()
            == 2
        )
        assert conn.execute(text("SELECT count(*) FROM approval_grants")).scalar_one() == 0
    with pytest.raises(ResearchBaseError) as error:
        service.record_concern_re_review(
            e["reviewer"], replace(command, internal_review_record_id=old.id), novelty=True
        )
    assert error.value.code is ErrorCode.PROVENANCE_CLOSURE_VIOLATION


@pytest.mark.parametrize(
    "case", ["legacy_protocol", "action_author", "wrong_assessment", "superseded_action"]
)
def test_correspondence_denials_have_no_effect(novelty_env, case):
    e = novelty_env
    c, root = _root(e)
    _, original = _review(e, root)
    result = e["service"].record_novelty_assessment(
        e["author"], replace(c, id=uuid4(), supersedes_assessment_id=root.id)
    )
    service = RevisionActionService(e["factory"], e["credentials"], e["literature"])
    cmd = RecordNoveltyRevisionCommand(uuid4(), e["project"], original.issues[0].id, result.id)
    action = service.record_novelty_revision(e["owner"], cmd)
    reviewer = e["owner"] if case == "action_author" else e["reviewer"]
    target = root if case == "wrong_assessment" else result
    review = InternalReviewService(e["factory"], e["credentials"], e["literature"]).create(
        reviewer,
        e["project"],
        "NOVELTY_ASSESSMENT",
        target.id,
        "SCIENTIFIC",
        "ACCEPT",
        "Exact independent review",
        (),
        uuid4(),
    )
    if case == "superseded_action":
        service.record_novelty_revision(
            e["owner"], replace(cmd, id=uuid4(), supersedes_revision_action_id=action.id)
        )
    with pytest.raises(ResearchBaseError) as error:
        service.record_concern_re_review(
            reviewer,
            RecordConcernReReviewCommand(e["project"], action.id, review.id),
            novelty=case != "legacy_protocol",
        )
    assert (
        error.value.code
        is {
            "legacy_protocol": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
            "action_author": ErrorCode.CONFLICT_OF_INTEREST,
            "wrong_assessment": ErrorCode.PROVENANCE_CLOSURE_VIOLATION,
            "superseded_action": ErrorCode.INVALID_STATE_TRANSITION,
        }[case]
    )
    with e["engine"].connect() as conn:
        assert (
            conn.execute(text("SELECT count(*) FROM revision_action_re_reviews")).scalar_one() == 0
        )
        assert (
            conn.execute(
                text("SELECT status FROM review_issues WHERE id=:id"), {"id": original.issues[0].id}
            ).scalar_one()
            == "OPEN"
        )
